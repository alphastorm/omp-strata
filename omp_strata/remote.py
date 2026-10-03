"""Authenticated loopback SSH routes, owned by one foreground client launcher.

No SSH daemon, request proxy, key in argv, or server installation on the client.
Private SSH configuration remains an operator trust boundary (including ProxyCommand).
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from . import lifecycle, ompcfg
from .common import atomic_write_json, read_json, verify_file
from .layout import Layout, host_platform
from .profile import ClientRoute


# A user SSH config must not turn this foreground child into a detached/persistent master.
SSH_OWNERSHIP = ("-o", "ControlMaster=no", "-o", "ControlPath=none", "-o", "ForkAfterAuthentication=no")


class RemoteError(lifecycle.LifecycleError):
    """A public-safe failure: never includes SSH output or response bodies."""


class RemoteInterrupted(BaseException):
    def __init__(self, signum):
        self.signum = signum


class RemoteCleanupError(RemoteError):
    def __init__(self, failures):
        self.failures = tuple(failures)
        super().__init__(f"cleanup failed for {len(self.failures)} owned resource(s); failed handles retained")


@dataclass
class _InterruptState:
    depth: int = 0
    pending: int | None = None
    unwinding: bool = False

    def deliver(self):
        if self.pending is not None and not self.depth and not self.unwinding:
            self.unwinding = True
            raise RemoteInterrupted(self.pending)


_signals = threading.local()


@contextmanager
def interrupt_scope():
    """Defer interruption through ownership publication and all resource teardown."""
    if getattr(_signals, "state", None) is not None:
        yield
        return
    state = _signals.state = _InterruptState()
    saved = {}

    def interrupt(signum, _frame):
        if state.pending is None:
            state.pending = signum
        state.deliver()

    for signum in (signal.SIGINT, signal.SIGTERM):
        saved[signum] = signal.signal(signum, interrupt)
    try:
        yield
    finally:
        for signum, handler in saved.items():
            signal.signal(signum, handler)
        _signals.state = None


@contextmanager
def defer_interrupts():
    # Python dispatches process signals only on the main thread. Watcher threads
    # use the process lock, not a second installation of signal handlers.
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    state = getattr(_signals, "state", None)
    if state is None:
        with interrupt_scope(), defer_interrupts():
            yield
        return
    state.depth += 1
    failed = False
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        state.depth -= 1
        if not failed:
            state.deliver()


def destination(value: str) -> str:
    # OpenSSH interprets its destination through config; prohibit shell syntax as well as options.
    if not isinstance(value, str) or not re.fullmatch(r"(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise RemoteError("SSH destination must be a single alias or user@host, not an option or shell expression")
    return value


def port(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 65535:
        raise RemoteError("SSH ports must be integers in 1..65535")
    return value


def tunnel_argv(alias: str, local_port: int, remote_port: int, *, ssh: str = "ssh") -> list[str]:
    return [*([ssh] if isinstance(ssh, str) else ssh), "-NT", "-o", "ExitOnForwardFailure=yes", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3", "-o", "BatchMode=yes", *SSH_OWNERSHIP, "-L",
            f"127.0.0.1:{port(local_port)}:127.0.0.1:{port(remote_port)}", destination(alias)]


class _WindowsJob:
    """Kill-on-close job; assign a suspended child before any ProxyCommand can fork."""
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c = c
        self.k = c.WinDLL("kernel32", use_last_error=True)

        class Basic(c.Structure):
            _fields_ = [("process_time", c.c_int64), ("job_time", c.c_int64), ("flags", w.DWORD),
                        ("min_working", c.c_size_t), ("max_working", c.c_size_t), ("active", w.DWORD),
                        ("affinity", c.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class Io(c.Structure):
            _fields_ = [(name, c.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

        class Extended(c.Structure):
            _fields_ = [("basic", Basic), ("io", Io), ("process_memory", c.c_size_t),
                        ("job_memory", c.c_size_t), ("peak_process", c.c_size_t), ("peak_job", c.c_size_t)]

        self.k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.k.CreateJobObjectW.restype = w.HANDLE
        self.k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        self.k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.k.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.k.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
            self.close()
            raise RemoteError("cannot establish Windows child-process containment")

    def assign(self, process):
        if not self.k.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise RemoteError("cannot contain the Windows child process")
        nt = self.c.WinDLL("ntdll")
        nt.NtResumeProcess.argtypes = [self.c.c_void_p]
        nt.NtResumeProcess.restype = self.c.c_long
        if nt.NtResumeProcess(int(process._handle)) != 0:
            raise RemoteError("cannot resume the contained Windows child process")

    def close(self):
        if getattr(self, "handle", None):
            if not self.k.CloseHandle(self.handle):
                raise RemoteError("cannot close the Windows process-containment job")
            self.handle = None


def _signal_owned_group(process, signum: int) -> None:
    pgid = process.pid
    if process.returncode is not None:
        # A reaped leader no longer reserves its PID. A new process at that PID
        # cannot belong to our old group; live descendants still reserve the PGID.
        try:
            os.kill(pgid, 0)
        except ProcessLookupError:
            pass
        except PermissionError:
            return
        else:
            return
    try:
        os.killpg(pgid, signum)
    except ProcessLookupError:
        return
    except PermissionError as error:
        # Darwin can report EPERM instead of ESRCH for a group containing only zombies.
        # Do not turn a real permission failure against a live process into successful cleanup.
        if sys.platform != "darwin":
            raise
        try:
            snapshot = subprocess.run(["ps", "-A", "-o", "pgid=,stat="], stdin=subprocess.DEVNULL,
                                      capture_output=True, text=True, timeout=5)
            rows = [line.split() for line in snapshot.stdout.splitlines() if line.strip()]
            if snapshot.returncode or any(len(row) != 2 for row in rows):
                raise error
            if any(not state.startswith("Z") for group, state in rows if group == str(pgid)):
                raise error
        except (OSError, subprocess.SubprocessError):
            raise error from None


class OwnedProcess:
    def __init__(self, argv: list[str], **kwargs):
        self.process = None
        self.job = None
        self._lock = threading.RLock()
        self._killed = False
        try:
            with defer_interrupts():
                if os.name == "nt":
                    self.job = _WindowsJob()
                    kwargs["creationflags"] = kwargs.get("creationflags", 0) | 0x4  # CREATE_SUSPENDED
                else:
                    kwargs["start_new_session"] = True
                self.process = subprocess.Popen(argv, **kwargs)
                if self.job:
                    self.job.assign(self.process)
        except BaseException:
            self.close()
            raise

    def kill_now(self):
        """Stop execution immediately; leave the handle published for later reaping."""
        with defer_interrupts(), self._lock:
            if self.process is None or self._killed:
                return
            if self.job:
                self.job.close()
            elif os.name == "nt":
                self.process.kill()
            else:
                _signal_owned_group(self.process, signal.SIGKILL)
            self._killed = True

    def close(self):
        with defer_interrupts(), self._lock:
            process = self.process
            if process is None:
                if self.job:
                    self.job.close()
                return
            if self.job:
                self.job.close()  # includes descendants even when their parent already exited
            elif not self._killed:
                _signal_owned_group(process, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.kill_now()
                process.wait(timeout=5)
            if os.name != "nt":
                _signal_owned_group(process, signal.SIGKILL)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
            self.process = None
            self.job = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def validate_key(raw: bytes) -> str:
    try:
        key = raw.decode("ascii").strip()
    except UnicodeError:
        raise RemoteError("API key transfer returned invalid key material") from None
    if not 32 <= len(key) <= 512 or not all(33 <= ord(ch) <= 126 for ch in key):
        raise RemoteError("API key is blank, short or malformed; refusing client launch")
    return key


def write_private(path: Path, data: bytes) -> None:
    """Restrict an empty temporary file before putting any secret bytes into it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".private-", dir=path.parent)
    tmp = Path(temporary)
    try:
        lifecycle.restrict_to_user(tmp)
        with os.fdopen(fd, "wb") as out:
            fd = -1
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if fd != -1:
            os.close(fd)
        tmp.unlink(missing_ok=True)


def key_provenance_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def _key_provenance(binding: Binding, key: str) -> dict:
    return {"alias": binding.alias, "remote_root": binding.remote_root, "remote_platform": binding.remote_platform,
            "key_sha256": hashlib.sha256(key.encode("ascii")).hexdigest()}


def write_client_key(path: Path, key: str, binding: Binding) -> None:
    key = validate_key(key.encode("ascii"))
    # The digest makes a partially replaced pair fail closed, rather than
    # attributing a newly fetched key to the previous endpoint.
    write_private(path, (key + "\n").encode("ascii"))
    write_private(key_provenance_path(path), json.dumps(_key_provenance(binding, key)).encode())


def read_client_key(path: Path, binding: Binding) -> str:
    try:
        if path.is_symlink():
            raise RemoteError("client key must not be a symlink")
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise RemoteError("client key permissions must be user-only (0600)")
        raw = path.read_bytes()
    except OSError:
        raise RemoteError("no readable client API key; run pull-key first") from None
    key = validate_key(raw)
    provenance = key_provenance_path(path)
    try:
        if provenance.is_symlink() or (os.name != "nt" and provenance.stat().st_mode & 0o077):
            raise ValueError
        if read_json(provenance) != _key_provenance(binding, key):
            raise ValueError
    except (OSError, ValueError, TypeError):
        raise RemoteError("binding changed since pull-key; run pull-key again") from None
    return key


def key_argv(alias: str, remote_root: str, remote_platform: str, *, ssh: str = "ssh") -> list[str]:
    destination(alias)
    if not isinstance(remote_root, str) or not remote_root or any(ord(c) < 32 for c in remote_root):
        raise RemoteError("remote root must be a nonblank absolute path without control characters")
    if remote_platform == "windows":
        root = PureWindowsPath(remote_root)
        if not root.is_absolute():
            raise RemoteError("remote Windows root must be absolute")
        path = str(root / "state" / "strata-api-key").replace("'", "''")
        script = "$ErrorActionPreference='Stop';[Console]::Out.Write([IO.File]::ReadAllText('" + path + "'))"
        command = "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + base64.b64encode(script.encode("utf-16le")).decode("ascii")
    elif remote_platform == "posix":
        root = PurePosixPath(remote_root)
        if not root.is_absolute():
            raise RemoteError("remote POSIX root must be absolute")
        command = "cat -- " + shlex.quote(str(root / "state" / "strata-api-key"))
    else:
        raise RemoteError("remote platform must be windows or posix")
    return [*([ssh] if isinstance(ssh, str) else ssh), "-o", "BatchMode=yes", *SSH_OWNERSHIP, alias, command]


def pull_key(alias: str, remote_root: str, remote_platform: str, path: Path, *, ssh: str = "ssh", timeout: float = 30) -> None:
    argv = key_argv(alias, remote_root, remote_platform, ssh=ssh)
    child = None
    try:
        try:
            with defer_interrupts():
                child = OwnedProcess(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            raw, _ = child.process.communicate(timeout=timeout)
            if child.process.returncode:
                raise RemoteError("SSH key transfer failed; check the private binding and host key trust")
        finally:
            if child is not None:
                child.close()
        key = validate_key(raw)
        write_client_key(path, key, Binding(path.stem, alias, remote_root, remote_platform))
    except (OSError, subprocess.TimeoutExpired):
        raise RemoteError("SSH key transfer or private key installation failed; run pull-key again") from None


def verify_request_owner(url: str, owner: Tunnel) -> None:
    parsed = urlsplit(url)
    if (owner is None or parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.port != owner.local_port or parsed.username or parsed.password):
        raise RemoteError("authenticated request does not match its owned loopback tunnel")
    owner.verify_listener()


class TunnelHTTPConnection(http.client.HTTPConnection):
    """Authorize the accepted peer of this socket before HTTP can send a byte."""
    def __init__(self, host, port=None, *, owner: Tunnel, **kwargs):
        super().__init__(host, port, **kwargs)
        if owner is None or self.host != "127.0.0.1" or self.port != owner.local_port:
            raise RemoteError("authenticated request does not match its owned loopback tunnel")
        self.owner = owner

    def connect(self):
        if self._tunnel_host is not None:
            raise RemoteError("authenticated request does not match its owned loopback tunnel")
        super().connect()
        try:
            self.owner.verify_peer(self.sock)
        except BaseException:
            self.close()
            raise


def http_json(url: str, *, key: str | None = None, owner: Tunnel | None = None, timeout: float = 5) -> tuple[int, object]:
    # No ambient proxy and no redirect: never forward the bearer key to another origin.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None
    class TunnelHandler(urllib.request.HTTPHandler):
        def http_open(self, request):
            return self.do_open(lambda host, **kwargs: TunnelHTTPConnection(host, owner=owner, **kwargs), request)
    handlers = [urllib.request.ProxyHandler({}), NoRedirect()]
    if key is not None:
        verify_request_owner(url, owner)
        handlers.append(TunnelHandler())
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key} if key else {})
    try:
        with urllib.request.build_opener(*handlers).open(req, timeout=timeout) as resp:
            code, raw = resp.status, resp.read(1 << 20)
    except urllib.error.HTTPError as exc:
        code, raw = exc.code, b""
        exc.close()
    except (OSError, urllib.error.URLError, TimeoutError):
        return 0, None
    try:
        return code, json.loads(raw)
    except ValueError:
        return code, None


def preflight(profile, local_port: int, key: str, *, owner: Tunnel) -> dict:
    """Public health followed by authenticated exact identity; no server body reaches an error."""
    url = f"http://127.0.0.1:{port(local_port)}"
    verify_request_owner(url, owner)
    st, health = http_json(url + "/health")
    if st != 200 or not isinstance(health, dict):
        raise RemoteError("tunnel endpoint health check failed; server stopped or unavailable")
    p = profile.data
    if health.get("api_key") is not True or health.get("loaded") is False:
        raise RemoteError("remote server is unauthenticated or not loaded")
    if health.get("model") != p["strata"]["model_name"] or health.get("max_context") != p["strata"]["setup_args"]["context"]:
        raise RemoteError("remote server health identity does not match the pinned server profile")
    st, _ = http_json(url + "/v1/models")
    if st != 401:
        raise RemoteError("remote server did not refuse missing authentication")
    st, models = http_json(url + "/v1/models", key=key, owner=owner)
    if st == 401:
        raise RemoteError("remote server refused the client API key (HTTP 401)")
    rows = models.get("data") if isinstance(models, dict) else None
    if st != 200 or not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict) or rows[0].get("id") != p["strata"]["model_name"]:
        raise RemoteError("authenticated model identity check failed")
    st, props = http_json(url + "/props", key=key, owner=owner)
    if (st != 200 or not isinstance(props, dict) or props.get("build_info") != "Strata " + p["strata"]["engine_version"]
            or (props.get("default_generation_settings") or {}).get("n_ctx") != p["strata"]["setup_args"]["context"]):
        raise RemoteError("authenticated engine identity does not match the pinned server profile")
    st, settings = http_json(url + "/settings", key=key, owner=owner)
    if st != 200 or settings != {"shared": False, "defaults": {}}:
        raise RemoteError("remote shared settings are not the pinned empty defaults")
    return {"model": p["strata"]["model_name"], "engine_version": p["strata"]["engine_version"]}


@dataclass(frozen=True)
class Binding:
    label: str
    alias: str
    remote_root: str
    remote_platform: str


def load_bindings(path: Path, route: ClientRoute, *, alias: str | None = None) -> dict[str, Binding]:
    try:
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise ValueError
        data = read_json(path)
        if set(data) != {"route_id", "route_fingerprint", "members", "roles"}:
            raise ValueError
        if data["route_id"] != route.id or data["route_fingerprint"] != route.fingerprint or data["roles"] != route.data["roles"]:
            raise ValueError
        expected = {m["label"]: m for m in route.data["members"]}
        result = {}
        for member in data["members"]:
            public = {k: member[k] for k in ("label", "server_profile", "server_fingerprint", "local_port")}
            if public != expected.get(member["label"]) or member["label"] in result:
                raise ValueError
            if set(member) != set(public) | {"alias", "remote_root", "remote_platform"}:
                raise ValueError
            key_argv(member["alias"], member["remote_root"], member["remote_platform"])
            result[member["label"]] = Binding(member["label"], member["alias"], member["remote_root"], member["remote_platform"])
        if set(result) != set(expected):
            raise ValueError
        if alias is not None and (len(result) != 1 or next(iter(result.values())).alias != destination(alias)):
            raise ValueError
        return result
    except (OSError, ValueError, KeyError, TypeError):
        raise RemoteError("private bindings do not match the public route identity") from None


def client_key_path(root: Path, label: str) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", label):
        raise RemoteError("invalid member label")
    return root / "state" / "keys" / (label + ".key")


def _linux_tcp_pids(local_port: int, *, peer_port: int | None = None, proc_root: Path = Path("/proc")) -> set[int]:
    inodes = {}
    addresses = {"tcp": "0100007F", "tcp6": "0000000000000000FFFF00000100007F"}
    for table, accepted in addresses.items():
        path = proc_root / "net" / table
        if table == "tcp6" and not path.exists():
            continue  # IPv6 can be disabled in the kernel.
        for line in path.read_text(encoding="ascii").splitlines()[1:]:
            fields = line.split()
            if len(fields) < 10:
                raise ValueError("incomplete TCP ownership table")
            address, number = fields[1].split(":")
            if peer_port is None:
                matches = fields[3] == "0A" and int(number, 16) == local_port
            else:
                remote_address, remote_number = fields[2].split(":")
                matches = (fields[3] == "01" and address == accepted and remote_address == accepted
                           and int(number, 16) == local_port and int(remote_number, 16) == peer_port)
            # Inode 0: the kernel queued this connection but no process has accepted it yet, so nothing owns it.
            if matches and fields[9] != "0":
                inodes[fields[9]] = int(fields[7])
    owners, seen = set(), set()
    for process in proc_root.iterdir():
        if not process.name.isdecimal():
            continue
        try:
            if process.stat().st_uid not in inodes.values():
                continue
            for fd in (process / "fd").iterdir():
                try:
                    target = os.readlink(fd)
                except (FileNotFoundError, ProcessLookupError):
                    continue  # An unrelated descriptor/process can disappear during enumeration.
                if target.startswith("socket:[") and target.endswith("]"):
                    inode = target[8:-1]
                    if inode in inodes:
                        owners.add(int(process.name))
                        seen.add(inode)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            # Vanished, or a descriptor table this user may not read. Skipping it cannot authorize anything:
            # a socket owned only by such a process stays unattributed and the query refuses below.
            continue
    if set(inodes) != seen:
        raise ValueError("unattributed listener")
    return owners


def _query_owner_pids(argv, *, lsof=False, peer_name=None, allow_empty=False) -> set[int]:
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
    lines = result.stdout.splitlines()
    if result.returncode or (not lines and not allow_empty):
        raise ValueError("socket ownership query failed")
    owners = set()
    current_pid, has_file, needs_name = None, False, False
    for line in lines:
        value = line.strip()
        if not lsof:
            if not value.isdecimal() or int(value) <= 0:
                raise ValueError("invalid socket owner")
            owners.add(int(value))
        elif value.startswith("p"):
            if needs_name or (current_pid is not None and not has_file) or not value[1:].isdecimal() or int(value[1:]) <= 0:
                raise ValueError("incomplete process record")
            current_pid, has_file = int(value[1:]), False
        elif value.startswith("f") and value[1:].isdecimal() and current_pid is not None and not needs_name:
            # lsof emits f records even when only p (or pn) was requested.
            has_file = True
            if peer_name is None:
                owners.add(current_pid)
            else:
                needs_name = True
        elif value.startswith("n") and needs_name:
            needs_name = False
            if value[1:] == peer_name and current_pid != os.getpid():
                owners.add(current_pid)
        else:
            raise ValueError("unexpected socket ownership record")
    if lsof and (not has_file or needs_name):
        raise ValueError("incomplete socket ownership query")
    return owners


def listener_pids(local_port: int) -> set[int]:
    """A failed or incomplete platform ownership query never authorizes a bearer."""
    port(local_port)
    try:
        if sys.platform == "linux":
            return _linux_tcp_pids(local_port)
        if sys.platform == "darwin":
            argv = ["/usr/sbin/lsof", "-nP", "-a", f"-iTCP:{local_port}", "-sTCP:LISTEN", "-Fp"]
        elif os.name == "nt":
            argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                    "$ErrorActionPreference='Stop';Get-NetTCPConnection "
                    f"-LocalPort {local_port} -State Listen -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess"]
        else:
            raise ValueError("unsupported listener ownership platform")
        return _query_owner_pids(argv, lsof=sys.platform == "darwin")
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as exc:
        raise RemoteError("cannot verify the loopback listener owner; refusing to send credentials "
                          f"({type(exc).__name__})") from None


def peer_pids(local_port: int, peer_port: int) -> set[int]:
    """Own the server half of this established loopback connection, not a port sample."""
    port(local_port)
    port(peer_port)
    try:
        if sys.platform == "linux":
            return _linux_tcp_pids(local_port, peer_port=peer_port)
        if sys.platform == "darwin":
            argv = ["/usr/sbin/lsof", "-nP", "-a", f"-iTCP@127.0.0.1:{peer_port}", "-Fpn"]
            return _query_owner_pids(argv, lsof=True, peer_name=f"127.0.0.1:{local_port}->127.0.0.1:{peer_port}")
        if os.name == "nt":
            # Only "no such connection" (not accepted yet) is an empty answer; any other failure refuses.
            argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                    "$ErrorActionPreference='Stop';try{Get-NetTCPConnection -LocalAddress 127.0.0.1 "
                    f"-LocalPort {local_port} -RemoteAddress 127.0.0.1 -RemotePort {peer_port} "
                    "-State Established | Select-Object -ExpandProperty OwningProcess}"
                    "catch{if($_.CategoryInfo.Category -ne 'ObjectNotFound'){throw}}"]
            return _query_owner_pids(argv, allow_empty=True)
        raise ValueError("unsupported socket ownership platform")
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as exc:
        raise RemoteError(f"authenticated request does not match its owned loopback tunnel ({type(exc).__name__})") from None


class Tunnel:
    def __init__(self, binding: Binding, local_port: int, remote_port: int, *, ssh="ssh", on_exit=None):
        self.binding, self.local_port, self.remote_port, self.ssh = binding, local_port, remote_port, ssh
        self.child = None
        self.watcher = None
        self.on_exit = on_exit
        self.watch_error = None

    def _watch(self, child, process):
        process.wait()
        if self.on_exit is not None:
            try:
                self.on_exit(self, child)
            except BaseException as exc:
                self.watch_error = exc

    def verify_listener(self):
        child = self.child
        process = child.process if child else None
        if process is None or process.poll() is not None:
            raise RemoteError("SSH tunnel is not alive; refusing to send credentials")
        owners = listener_pids(self.local_port)
        if owners != {process.pid} or process.poll() is not None:
            raise RemoteError("loopback listener is not owned exclusively by the SSH child; refusing credentials")

    def verify_peer(self, connection, *, accept_timeout: float = 1.0):
        child = self.child
        process = child.process if child else None
        if process is None or process.poll() is not None:
            raise RemoteError("SSH tunnel is not alive; refusing to send credentials")
        local, peer = connection.getsockname(), connection.getpeername()
        if local[0] != "127.0.0.1" or peer != ("127.0.0.1", self.local_port):
            raise RemoteError("authenticated request does not match its owned loopback tunnel")
        # connect() returns once the kernel queues the connection; until the listener accepts it no process owns
        # the server half. Wait briefly only while there is no owner; any owner but the live SSH child refuses.
        deadline = time.monotonic() + accept_timeout
        owners = peer_pids(self.local_port, local[1])
        while not owners and time.monotonic() < deadline:
            time.sleep(0.01)
            owners = peer_pids(self.local_port, local[1])
        if owners != {process.pid} or process.poll() is not None:
            raise RemoteError("authenticated request does not match its owned loopback tunnel")

    def open(self, timeout: float = 15):
        if self.child is not None:
            raise RemoteError("tunnel still has an owned child; finish closing it before reopening")
        # Match OpenSSH reuse semantics: a closed forward can leave TIME_WAIT connections.
        # They are not a listener and must not prevent deliberate transcript resume.
        with socket.socket() as probe:
            if os.name == "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", self.local_port))
            except OSError:
                raise RemoteError("client tunnel port is occupied; refusing to adopt an existing listener") from None
        try:
            with defer_interrupts():
                self.child = OwnedProcess(tunnel_argv(self.binding.alias, self.local_port, self.remote_port, ssh=self.ssh),
                                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.watch_error = None
                self.watcher = threading.Thread(target=self._watch, args=(self.child, self.child.process), daemon=True)
                self.watcher.start()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.child.process.poll() is not None:
                    raise RemoteError("SSH tunnel exited before readiness; check private SSH configuration")
                try:
                    with socket.create_connection(("127.0.0.1", self.local_port), timeout=0.1):
                        self.verify_listener()
                        return self
                except OSError:
                    time.sleep(0.03)
            raise RemoteError("SSH tunnel readiness timed out")
        except OSError:
            self.close()
            raise RemoteError("SSH tunnel could not start; check the SSH executable and private configuration") from None
        except BaseException:
            self.close()
            raise

    def close(self):
        with defer_interrupts():
            if self.child is not None:
                self.child.close()
                if self.watcher is not None:
                    self.watcher.join(timeout=5)
                    if self.watcher.is_alive():
                        raise RemoteError("SSH exit watcher did not finish; tunnel handle retained")
                self.child = None
                self.watcher = None

    @property
    def alive(self):
        child = self.child
        process = child.process if child else None
        return process is not None and process.poll() is None


class RemoteSession:
    def __init__(self, route: ClientRoute, root: Path, bindings: dict[str, Binding], *, ssh="ssh"):
        self.route, self.root, self.bindings, self.ssh = route, root, bindings, ssh
        self.layout = Layout(root, route.main)
        self.tunnels: list[Tunnel] = []
        self.keys: dict[str, str] = {}
        self.omp_child = None
        self._process_lock = threading.RLock()
        self._lost = threading.Event()
        self._closed = False

    def tunnel(self, label: str) -> Tunnel:
        return next(tunnel for tunnel in self.tunnels if tunnel.binding.label == label)

    def _tunnel_exited(self, tunnel, child):
        with self._process_lock:
            if tunnel.child is child:
                self._lost.set()
                if self.omp_child is not None:
                    self.omp_child.kill_now()

    def _close_omp(self):
        with defer_interrupts(), self._process_lock:
            if self.omp_child is not None:
                self.omp_child.close()
                self.omp_child = None

    def __enter__(self):
        try:
            # Read every key before starting any network process or materializing an OMP home.
            guard_client_root(self.layout, self.route)
            self.keys = {m["label"]: read_client_key(client_key_path(self.root, m["label"]), self.bindings[m["label"]])
                         for m in self.route.data["members"]}
            for member in self.route.data["members"]:
                profile = self.route.servers[member["label"]]
                tunnel = Tunnel(self.bindings[member["label"]], member["local_port"], profile.data["server"]["port"],
                                ssh=self.ssh, on_exit=self._tunnel_exited)
                self.tunnels.append(tunnel)
                tunnel.open()
                preflight(profile, member["local_port"], self.keys[member["label"]], owner=tunnel)
            return self
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *_):
        with defer_interrupts():
            self._closed = True
            failures = []
            for close in [self._close_omp, *(tunnel.close for tunnel in reversed(self.tunnels))]:
                try:
                    close()
                except BaseException as exc:
                    failures.append(exc)
            self.keys.clear()
            if failures:
                raise RemoteCleanupError(failures)

    def run(self, extra: list[str], *, binary: Path | None = None, cwd: Path | None = None,
            stdout=None, stderr=None, stdin=subprocess.DEVNULL, timeout: float | None = None) -> int:
        for tunnel in self.tunnels:
            tunnel.verify_listener()
        ompcfg.install_route_config(self.layout, self.route)
        main_label = self.route.data["roles"]["default"]
        env = ompcfg.isolated_env(self.layout, api_key=self.keys[main_label])
        env.update({ompcfg.route_key_env(label): key for label, key in self.keys.items()})
        argv = ompcfg.route_argv(self.layout, self.route, extra=extra, binary=binary)
        deadline = time.monotonic() + timeout if timeout is not None else None
        try:
            with defer_interrupts(), self._process_lock:
                if self._closed or self.omp_child is not None or not all(t.alive for t in self.tunnels):
                    raise RemoteError("client session is closed, disconnected, or still owns an OMP process")
                # A deliberately reopened and reverified tunnel may start a new turn.
                self._lost.clear()
                self.omp_child = OwnedProcess(argv, env=env, cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr)
                process = self.omp_child.process
            while process.poll() is None:
                if deadline is not None and time.monotonic() >= deadline:
                    raise RemoteError("bounded OMP proof exceeded its timeout")
                if self._lost.wait(0.05) or not all(t.alive for t in self.tunnels):
                    self.omp_child.kill_now()
                    raise RemoteError("SSH tunnel disconnected; OMP killed immediately; in-flight turn lost; resume the saved transcript explicitly")
            if self._lost.is_set() or not all(t.alive for t in self.tunnels):
                raise RemoteError("SSH tunnel disconnected; OMP killed immediately; in-flight turn lost; resume the saved transcript explicitly")
            return process.returncode
        finally:
            self._close_omp()


def verify_client_binary(layout: Layout) -> None:
    artifact = layout.profile.omp_artifact(host_platform())
    try:
        verify_file(layout.omp_binary(), artifact["bytes"], artifact["sha256"], source=artifact["sha256_source"], log=lambda _: None)
    except (OSError, RuntimeError):
        raise RemoteError("pinned client binary is missing or invalid; run fetch --only omp with this route and root") from None


def guard_client_root(layout: Layout, route: ClientRoute, *, record: bool = False) -> None:
    identity_path = layout.state / "client-route.json"
    identity = {"profile_id": route.id, "fingerprint": route.fingerprint}
    try:
        if layout.install_record.exists() or (identity_path.exists() and read_json(identity_path) != identity):
            raise ValueError
    except (OSError, ValueError):
        raise RemoteError("client root belongs to a different route or server installation; use a new root") from None
    if record and not identity_path.exists():
        atomic_write_json(identity_path, identity)


def launch(route: ClientRoute, root: Path, bindings: dict[str, Binding], extra: list[str], *, stdin=None) -> int:
    layout = Layout(root, route.main)
    guard_client_root(layout, route)
    with interrupt_scope(), lifecycle.FileLock(layout.state / "client.lock"):
        guard_client_root(layout, route)
        # Refuse absent keys even when the binary is absent; no network side effects precede this check.
        for member in route.data["members"]:
            read_client_key(client_key_path(root, member["label"]), bindings[member["label"]])
        verify_client_binary(layout)
        guard_client_root(layout, route, record=True)
        with RemoteSession(route, root, bindings) as session:
            return session.run(extra, stdin=stdin)
