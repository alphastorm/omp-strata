"""Authenticated loopback SSH routes, owned by one foreground client launcher.

No SSH daemon, request proxy, key in argv, or server installation on the client.
Private SSH configuration remains an operator trust boundary (including ProxyCommand).
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
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
import time
import urllib.error
import urllib.request

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


@contextmanager
def interrupt_scope():
    """Turn handled termination into stack unwinding, so every child is reaped."""
    saved = {}
    interrupted = False

    def interrupt(signum, _frame):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise RemoteInterrupted(signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        saved[signum] = signal.signal(signum, interrupt)
    try:
        yield
    finally:
        for signum, handler in saved.items():
            signal.signal(signum, handler)


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
            self.k.CloseHandle(self.handle)
            self.handle = None


def _signal_owned_group(pgid: int, signum: int) -> None:
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
        try:
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

    def close(self):
        process = self.process
        if process is None:
            if self.job:
                self.job.close()
            return
        if self.job:
            self.job.close()  # includes descendants even when their parent already exited
        else:
            _signal_owned_group(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                process.kill()
            else:
                _signal_owned_group(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        if os.name != "nt":
            # A ProxyCommand can ignore TERM after ssh has exited; reap the entire session group.
            _signal_owned_group(process.pid, signal.SIGKILL)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        self.process = None

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


def read_client_key(path: Path) -> str:
    try:
        if path.is_symlink():
            raise RemoteError("client key must not be a symlink")
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise RemoteError("client key permissions must be user-only (0600)")
        raw = path.read_bytes()
    except OSError:
        raise RemoteError("no readable client API key; run pull-key first") from None
    return validate_key(raw)


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
    try:
        with OwnedProcess(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as child:
            raw, _ = child.process.communicate(timeout=timeout)
            if child.process.returncode:
                raise RemoteError("SSH key transfer failed; check the private binding and host key trust")
        key = validate_key(raw)
        write_private(path, (key + "\n").encode("ascii"))
    except (OSError, subprocess.TimeoutExpired):
        raise RemoteError("SSH key transfer unavailable or timed out; no key was installed") from None


def http_json(url: str, *, key: str | None = None, timeout: float = 5) -> tuple[int, object]:
    # No ambient proxy and no redirect: never forward the bearer key to another origin.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key} if key else {})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(req, timeout=timeout) as resp:
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


def preflight(profile, local_port: int, key: str) -> dict:
    """Public health followed by authenticated exact identity; no server body reaches an error."""
    url = f"http://127.0.0.1:{port(local_port)}"
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
    st, models = http_json(url + "/v1/models", key=key)
    if st == 401:
        raise RemoteError("remote server refused the client API key (HTTP 401)")
    rows = models.get("data") if isinstance(models, dict) else None
    if st != 200 or not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict) or rows[0].get("id") != p["strata"]["model_name"]:
        raise RemoteError("authenticated model identity check failed")
    st, props = http_json(url + "/props", key=key)
    if (st != 200 or not isinstance(props, dict) or props.get("build_info") != "Strata " + p["strata"]["engine_version"]
            or (props.get("default_generation_settings") or {}).get("n_ctx") != p["strata"]["setup_args"]["context"]):
        raise RemoteError("authenticated engine identity does not match the pinned server profile")
    st, settings = http_json(url + "/settings", key=key)
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


class Tunnel:
    def __init__(self, binding: Binding, local_port: int, remote_port: int, *, ssh="ssh"):
        self.binding, self.local_port, self.remote_port, self.ssh = binding, local_port, remote_port, ssh
        self.child = None

    def open(self, timeout: float = 15):
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
            self.child = OwnedProcess(tunnel_argv(self.binding.alias, self.local_port, self.remote_port, ssh=self.ssh),
                                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.child.process.poll() is not None:
                    raise RemoteError("SSH tunnel exited before readiness; check private SSH configuration")
                try:
                    with socket.create_connection(("127.0.0.1", self.local_port), timeout=0.1):
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
        child, self.child = self.child, None
        if child:
            child.close()

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

    def __enter__(self):
        try:
            # Read every key before starting any network process or materializing an OMP home.
            self.keys = {m["label"]: read_client_key(client_key_path(self.root, m["label"])) for m in self.route.data["members"]}
            for member in self.route.data["members"]:
                profile = self.route.servers[member["label"]]
                tunnel = Tunnel(self.bindings[member["label"]], member["local_port"], profile.data["server"]["port"], ssh=self.ssh)
                self.tunnels.append(tunnel)
                tunnel.open()
                preflight(profile, member["local_port"], self.keys[member["label"]])
            return self
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *_):
        for tunnel in reversed(self.tunnels):
            tunnel.close()
        self.keys.clear()

    def run(self, extra: list[str], *, binary: Path | None = None, cwd: Path | None = None,
            stdout=None, stderr=None, stdin=subprocess.DEVNULL, timeout: float | None = None) -> int:
        ompcfg.install_route_config(self.layout, self.route)
        main_label = self.route.data["roles"]["default"]
        env = ompcfg.isolated_env(self.layout, api_key=self.keys[main_label])
        env.update({ompcfg.route_key_env(label): key for label, key in self.keys.items()})
        argv = ompcfg.route_argv(self.layout, self.route, extra=extra, binary=binary)
        deadline = time.monotonic() + timeout if timeout is not None else None
        with OwnedProcess(argv, env=env, cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr) as child:
            while child.process.poll() is None:
                if deadline is not None and time.monotonic() >= deadline:
                    raise RemoteError("bounded OMP proof exceeded its timeout")
                if not all(t.alive for t in self.tunnels):
                    # Give stock OMP the closed transport first; then interrupt to flush its transcript.
                    try:
                        child.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        if os.name != "nt":
                            child.process.send_signal(signal.SIGINT)
                            try:
                                child.process.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                pass
                    raise RemoteError("SSH tunnel disconnected; OMP stopped without fallback; resume the same transcript explicitly")
                time.sleep(0.05)
            return child.process.returncode


def verify_client_binary(layout: Layout) -> None:
    artifact = layout.profile.omp_artifact(host_platform())
    try:
        verify_file(layout.omp_binary(), artifact["bytes"], artifact["sha256"], source=artifact["sha256_source"], log=lambda _: None)
    except (OSError, RuntimeError):
        raise RemoteError("pinned client binary is missing or invalid; run fetch --only omp with this route and root") from None


def launch(route: ClientRoute, root: Path, bindings: dict[str, Binding], extra: list[str], *, stdin=None) -> int:
    layout = Layout(root, route.main)
    with interrupt_scope(), lifecycle.FileLock(layout.state / "client.lock"):
        identity_path = layout.state / "client-route.json"
        identity = {"profile_id": route.id, "fingerprint": route.fingerprint}
        if layout.install_record.exists() or (identity_path.exists() and read_json(identity_path) != identity):
            raise RemoteError("client root belongs to a different route or server installation; use a new root")
        # Refuse absent keys even when the binary is absent; no network side effects precede this check.
        for member in route.data["members"]:
            read_client_key(client_key_path(root, member["label"]))
        verify_client_binary(layout)
        atomic_write_json(identity_path, identity)
        with RemoteSession(route, root, bindings) as session:
            return session.run(extra, stdin=stdin)
