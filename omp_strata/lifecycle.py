"""Minimal lifecycle for one stock Strata server: keygen, doctor, start, serve (wrapper), status, stop.

No daemon of our own: `start` launches a detached `serve` wrapper that reads the private key file, starts stock
`serve/server.py` on loopback with the key in its environment, and records owned process identities in
`<root>/state/run.json`. `stop` only ever terminates processes whose PID, creation time and executable still match
that record. A server already on the port is never adopted.
Experiment commands, detached wrappers and servers share a token-keyed Windows
Job Object: suspended creation, no breakaway, kill-on-close, and independent CIM
tree verification. Parent exit never proves tree exit. Unknown trees refuse
custody release; non-Windows experiment custody is explicitly unsupported.
"""

from __future__ import annotations

import csv
import contextlib
import ctypes
import io
import json
import os
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree

from . import dflash2, dsv41, fetch, nvfp4, procs
from .common import (IntegrityError, atomic_write_bytes, atomic_write_json, canonical_json, flag_pairs, read_json,
                     release_version, sha256_bytes, sha256_file, utc_now, verified_ok)
from .install import InstallError, SECRET_ENV_MARKERS, verify_generated
from .layout import Layout, host_platform
from .profile import GPU_MODEL_ARCH, engine_env_groups, engine_env_union, runtime_build_labels

Log = Callable[[str], None]
WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000
GPU_IDLE_MIB = 1500
EXPERIMENT_LAUNCH_ENV = "OMP_STRATA_EXPERIMENT_LAUNCH"
TREE_TOKEN_ENV = "OMP_STRATA_TREE_TOKEN"
# Verbatim engine 0.1.55 startup forms observed in the reviewed feature arms.
SELF_COMMIT_LINE = re.compile(r"strata verify: batch windows of up to \d+ sequences \(layers \[\d+, \d+\)\), "
                              r"one-row windows keep their rows")
# Only source-reviewed stock lines belong here; groups without a stock line retain delivery-only proof.
ENGINE_ENV_GROUP_EVIDENCE: dict[str, dict] = {
    "qsa_split_attn": {"on": (), "refuse": ("qsa_decode_attn_split:", "strata verify: batch windows of up to"),
                       "cite": "src/kernels/cuda/qsa_prompt_attn.cu:2424-2427; src/core/verify.cpp:4000-4001"},
}
KV_STREAMING_LINE = re.compile(r"^strata generate: KV streaming: ", re.MULTILINE)
KV_GROW_LINE = re.compile(r"strata generate: elastic K/V: \d+ of \d+ cells in VRAM \(\d+\.\d+ of \d+\.\d+ GiB\); "
                          r"the expert cache \(\d+ slots\) gives the K/V room below slot \d+ as the context grows")


class LifecycleError(RuntimeError):
    pass


class MissingProcessJob(LifecycleError):
    """The named kernel object is gone, not inaccessible or unqueryable."""

class _JobLimits(ctypes.Structure):
    _fields_ = [("user_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                ("flags", ctypes.c_uint32), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t),
                ("active", ctypes.c_uint32), ("affinity", ctypes.c_size_t),
                ("priority", ctypes.c_uint32), ("scheduling", ctypes.c_uint32)]


class _ExtendedJobLimits(ctypes.Structure):
    _fields_ = [("basic", _JobLimits), ("io", ctypes.c_uint64 * 6),
                ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]


def _job_kernel():
    """Lazy binding: importing the driver never opens a kernel handle or launches a process."""
    if not WINDOWS:
        raise LifecycleError("process-tree verification unsupported on this platform")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    handle, dword, ptr = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p
    signatures = {
        "CreateJobObjectW": (handle, [ptr, ctypes.c_wchar_p]),
        "OpenJobObjectW": (handle, [dword, ctypes.c_int, ctypes.c_wchar_p]),
        "SetInformationJobObject": (ctypes.c_int, [handle, ctypes.c_int, ptr, dword]),
        "QueryInformationJobObject": (ctypes.c_int, [handle, ctypes.c_int, ptr, dword, ptr]),
        "AssignProcessToJobObject": (ctypes.c_int, [handle, handle]),
        "IsProcessInJob": (ctypes.c_int, [handle, handle, ptr]),
        "TerminateJobObject": (ctypes.c_int, [handle, dword]),
        "CloseHandle": (ctypes.c_int, [handle]),
        "GetCurrentProcess": (handle, []),
        "DuplicateHandle": (ctypes.c_int, [handle, handle, handle, ptr, dword, ctypes.c_int, dword]),
        "ResumeThread": (dword, [handle]),
        "GetLastError": (dword, []),
    }
    for name, (result, args) in signatures.items():
        function = getattr(kernel, name)
        function.restype, function.argtypes = result, args
    return kernel


class ProcessJob:
    """One exact launch token, one non-breakaway job, one driver-owned handle.

    Stop terminates the job before checking its empty membership AND a separate CIM
    token observation. A dead wrapper is never evidence of an empty tree.
    Handles are not inherited or handed off to another owner.
    """
    def __init__(self, token, *, kernel=None, existing=False):
        if not re.fullmatch(r"[0-9a-f]{32}", token):
            raise LifecycleError("invalid process-tree launch token")
        self.token = token
        self.kernel = kernel if kernel is not None else _job_kernel()
        self.handle = None
        self.pending_process = None
        self.verified_empty = False
        self.observed = {}
        name = "Local\\omp-strata-" + token
        if existing:
            self.handle = self.kernel.OpenJobObjectW(0x1F003F, False, name)
        else:
            self.handle = self.kernel.CreateJobObjectW(None, name)
            if self.handle and self.kernel.GetLastError() == 183:
                self.close()
                raise LifecycleError("process-tree launch token already exists")
        if not self.handle:
            if existing and self.kernel.GetLastError() == 2:
                raise MissingProcessJob("process-tree job was destroyed")
            raise LifecycleError("process-tree job unavailable")
        if not existing:
            limits = _ExtendedJobLimits()
            limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE; neither breakaway flag is enabled.
            if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                self.close()
                raise LifecycleError("cannot set process-tree job limits")

    def close(self):
        if self.handle:
            if not self.kernel.CloseHandle(self.handle):
                raise LifecycleError("cannot close process-tree job")
            self.handle = None

    def assign(self, process_handle):
        member = ctypes.c_int()
        if not self.kernel.IsProcessInJob(process_handle, self.handle, ctypes.byref(member)):
            raise LifecycleError("cannot verify process-tree job membership")
        if member.value:
            return
        if not self.kernel.AssignProcessToJobObject(self.handle, process_handle):
            raise LifecycleError("cannot assign owned process to non-breakaway job")

    def pids(self):
        # Growth between queries is allowed, but truncation is never an empty-tree proof.
        capacity = 64
        while capacity <= 65536:
            class Pids(ctypes.Structure):
                _fields_ = [("assigned", ctypes.c_uint32), ("count", ctypes.c_uint32),
                            ("items", ctypes.c_size_t * capacity)]
            values = Pids()
            ok = self.kernel.QueryInformationJobObject(self.handle, 3, ctypes.byref(values),
                                                       ctypes.sizeof(values), None)
            if ok and values.count <= capacity and values.assigned == values.count:
                return set(values.items[:values.count])
            if self.kernel.GetLastError() not in (0, 234):
                break
            capacity *= 2
        raise LifecycleError("process-tree membership enumeration unavailable")

    def enumerate_tree(self, timeout=30):
        """Independent token-keyed CIM identities, including members with dead parents.

        Native job membership supplies attribution for descendants that do not copy
        Python's command line. The token is also in each owned Python child's argv
        and inherited environment. CIM is independently required, never best-effort.
        """
        return self.scan(self.token, self.pids(), self.observed, remaining_members=self.pids, timeout=timeout)

    @staticmethod
    def snapshot(token, pids, timeout=30):
        # Query only this exact token and job-observed PIDs, never the incumbent census.
        if not re.fullmatch(r"[0-9a-f]{32}", token):
            raise LifecycleError("invalid process-tree launch token")
        if timeout <= 0:
            raise LifecycleError("process-tree verification budget exhausted")
        query = "CommandLine LIKE '%omp_strata_tree=" + token + "%'"
        query += "".join(" OR ProcessId=" + str(pid) for pid in sorted(pids))
        script = ("$ErrorActionPreference='Stop'; $p=@(Get-CimInstance Win32_Process -Filter \"ProcessId <> $PID AND (" + query +
                  ")\" | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine); "
                  "ConvertTo-Json -Compress -Depth 3 -InputObject $p")
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout, check=True)
        rows = json.loads(result.stdout)
        if not isinstance(rows, list):
            raise LifecycleError("process-tree CIM enumeration unavailable")
        indexed = {}
        for row in rows:
            if (not isinstance(row, dict) or type(row.get("ProcessId")) is not int
                    or type(row.get("ParentProcessId")) is not int
                    or row["ProcessId"] < 0 or row["ParentProcessId"] < 0
                    or row["ProcessId"] in indexed):
                raise LifecycleError("process-tree CIM enumeration incomplete")
            indexed[row["ProcessId"]] = row
        return indexed


    @staticmethod
    def scan(token, members, observed, *, remaining_members=None, timeout=30):
        indexed = ProcessJob.snapshot(token, members | observed.keys(), timeout=timeout)
        missing = members - indexed.keys()
        # A member can exit while PowerShell starts. Non-breakaway membership
        # proves that a missing member which also left the job actually exited.
        current = remaining_members() if remaining_members is not None else members
        if missing & current:
            raise LifecycleError("process-tree CIM membership snapshot incomplete")
        members &= current  # Do not adopt a reused pid that left this non-breakaway job during CIM.
        marker = re.compile(r"(?<![\w=])omp_strata_tree=" + token + r"(?!\w)")
        owned = {pid: row for pid, row in indexed.items()
                 if pid in members or marker.search(row.get("CommandLine") or "")
                 or pid in observed and observed[pid] == row.get("CreationDate")}
        if any(not isinstance(row.get("CreationDate"), str) or not row["CreationDate"] for row in owned.values()):
            raise LifecycleError("owned process-tree creation identity unavailable")
        if any(pid in observed and not row.get("CreationDate") for pid, row in indexed.items()):
            raise LifecycleError("observed process-tree creation identity unavailable")
        # Descendants cannot break away; native membership is their denominator.
        # Do not infer ownership from parent PIDs or inspect unrelated processes.
        observed.update({pid: row["CreationDate"] for pid, row in owned.items()})
        return owned

    def stop(self, timeout=30):
        deadline = time.monotonic() + max(0, timeout)
        if self.handle is None:
            if not self.verified_empty or self.scan(
                    self.token, set(), self.observed, timeout=deadline - time.monotonic()):
                raise LifecycleError("closed process-tree custody is unverified")
            if time.monotonic() > deadline:
                raise LifecycleError("process-tree proof exceeded cleanup deadline")
            return
        member = ctypes.c_int()
        if not self.kernel.IsProcessInJob(self.kernel.GetCurrentProcess(), self.handle, ctypes.byref(member)):
            raise LifecycleError("cannot establish cleanup caller job membership")
        if member.value:
            raise LifecycleError("job member cannot verify its own termination; driver cleanup required")
        # Snapshot failure must not skip the best available native tree termination.
        snapshot_error = None
        try:
            self.enumerate_tree(timeout=deadline - time.monotonic())
        except Exception as exc:
            snapshot_error = exc
        if self.pending_process is not None and self.pending_process.handle is not None:
            self.pending_process.kill()
        if not self.kernel.TerminateJobObject(self.handle, 1):
            raise LifecycleError("process-tree job termination failed")
        if self.pending_process is not None and self.pending_process.handle is not None:
            self.pending_process.wait(timeout=max(0, deadline - time.monotonic()))
        while self.pids():
            if time.monotonic() >= deadline:
                raise LifecycleError("process-tree job did not empty within stop budget")
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        if snapshot_error:
            raise LifecycleError("process-tree verification unavailable; retain custody") from snapshot_error
        if self.enumerate_tree(timeout=deadline - time.monotonic()):
            raise LifecycleError("owned process-tree survivors; retain custody")
        if time.monotonic() > deadline:
            raise LifecycleError("process-tree proof exceeded cleanup deadline")
        self.verified_empty = True
        self.close()


    def spawn(self, argv, *, stdout, stderr, env, cwd=None, stdin=None, timeout=30):
        """CPython 3.13 native suspended creation: assign before the first child instruction."""
        deadline = time.monotonic() + timeout
        import _winapi
        import msvcrt
        with open(os.devnull, "rb") as null:
            handles = []
            try:
                for stream in (stdin if stdin is not None else null, stdout, stderr):
                    duplicate = ctypes.c_void_p()
                    if not self.kernel.DuplicateHandle(self.kernel.GetCurrentProcess(),
                            msvcrt.get_osfhandle(stream.fileno()), self.kernel.GetCurrentProcess(),
                            ctypes.byref(duplicate), 0, True, 2):
                        raise LifecycleError("cannot duplicate command output handle")
                    handles.append(duplicate.value)
                startup = subprocess.STARTUPINFO(dwFlags=0x100, hStdInput=handles[0],
                    hStdOutput=handles[1], hStdError=handles[2], lpAttributeList={"handle_list": handles})
                marked = [argv[0], "-X", "omp_strata_tree=" + self.token, *argv[1:]]
                process, thread, pid, _tid = _winapi.CreateProcess(
                    argv[0], subprocess.list2cmdline(marked), None, None, True,
                    CREATE_NO_WINDOW | 0x4, {**env, TREE_TOKEN_ENV: self.token},
                    str(cwd) if cwd is not None else None, startup)
            finally:
                for handle in handles:
                    self.kernel.CloseHandle(handle)
        child = _JobProcess(process, pid, argv)
        self.pending_process = child  # Retain even if assignment or pre-resume cleanup fails.
        try:
            self.assign(process)
            if self.kernel.ResumeThread(thread) == 0xFFFFFFFF:
                raise LifecycleError("cannot resume job-owned command")
        except BaseException:
            _winapi.TerminateProcess(process, 1)
            child.wait(timeout=max(0, deadline - time.monotonic()))
            raise
        finally:
            _winapi.CloseHandle(thread)
        return child




class _JobProcess:
    def __init__(self, handle, pid, args):
        self.handle, self.pid, self.args = handle, pid, args
        self.returncode = None

    def poll(self):
        import _winapi
        if self.returncode is None and _winapi.WaitForSingleObject(self.handle, 0) == 0:
            self.returncode = _winapi.GetExitCodeProcess(self.handle)
            _winapi.CloseHandle(self.handle)
            self.handle = None
        return self.returncode

    def wait(self, timeout=None):
        import _winapi
        if self.poll() is None:
            result = _winapi.WaitForSingleObject(self.handle, 0xFFFFFFFF if timeout is None else int(timeout * 1000))
            if result == 258:
                raise subprocess.TimeoutExpired(self.args, timeout)
            if result != 0:
                raise LifecycleError("cannot wait for job-owned command")
        return self.poll()

    def detach(self):
        import _winapi
        _winapi.CloseHandle(self.handle)
        self.handle = None

    def kill(self):
        import _winapi
        if self.poll() is None:
            _winapi.TerminateProcess(self.handle, 1)


# ------------------------------------------------------------------------------------------------ lock
class _DirectoryInfo(ctypes.Structure):
    _fields_ = [("attributes", ctypes.c_uint32), ("times", ctypes.c_uint32 * 6),
                ("volume", ctypes.c_uint32), ("size_high", ctypes.c_uint32),
                ("size_low", ctypes.c_uint32), ("links", ctypes.c_uint32),
                ("index_high", ctypes.c_uint32), ("index_low", ctypes.c_uint32)]


def _directory_kernel():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    kernel.GetFileInformationByHandle.argtypes = [ctypes.c_void_p, ctypes.POINTER(_DirectoryInfo)]
    kernel.GetFileInformationByHandle.restype = ctypes.c_int
    return kernel


def _directory_info(kernel, handle):
    info = _DirectoryInfo()
    if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
        raise LifecycleError("candidate directory handle identity unavailable")
    if not info.attributes & 0x10 or info.attributes & 0x400:
        raise LifecycleError("candidate directory is a reparse point or not a directory")
    return info.volume, (info.index_high << 32) | info.index_low


def directory_identity(path):
    """No pathname stat on Windows: identity and reparse attributes come from the same handle."""
    if os.name != "nt":
        try:
            info = path.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISDIR(info.st_mode):
            raise LifecycleError("candidate directory is a reparse point or not a directory")
        return info.st_dev, info.st_ino
    kernel = _directory_kernel()
    handle = kernel.CreateFileW(str(path), 0, 3, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.get_last_error()
        if error in (2, 3):
            return None
        raise ctypes.WinError(error)
    try:
        return _directory_info(kernel, handle)
    finally:
        kernel.CloseHandle(handle)


def assert_operator_directory(path):
    """Strict start-time ACL assertion; even privileged foreign write ACEs refuse.

    The model and non-claims are declared in docs/OPERATIONS.md#threat-model.
    This is an observation, never an ACL repair or elevation.
    """
    if os.name != "nt":
        raise LifecycleError("operator ACL assertion requires native Windows")
    script = (
        "$ErrorActionPreference='Stop';"
        "$p=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
        "$a=Get-Acl -LiteralPath $p;"
        "$raw=[System.Security.AccessControl.RawSecurityDescriptor]::new($a.GetSecurityDescriptorBinaryForm(),0);"
        "$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "$owner=$a.GetOwner([System.Security.Principal.SecurityIdentifier]).Value;"
        "$rules=@($a.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier])|"
        "ForEach-Object { @{sid=$_.IdentityReference.Value; rights=[int64]$_.FileSystemRights;"
        "allow=($_.AccessControlType -eq 'Allow')} });"
        "@{operator=$sid;owner=$owner;rules=$rules;null_dacl=($null -eq $raw.DiscretionaryAcl)}|"
        "ConvertTo-Json -Compress -Depth 4")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            input=json.dumps(str(path)), capture_output=True, text=True, check=True, timeout=30)
    acl = json.loads(result.stdout)
    # Includes child deletion, ownership/DACL mutation and generic write/all.
    write_mask = 0x500D0156
    if (not isinstance(acl.get("operator"), str) or not acl["operator"].startswith("S-1-")
            or acl.get("owner") != acl["operator"] or not isinstance(acl.get("rules"), list)
            or acl.get("null_dacl") is not False
            or any(rule.get("allow") is True and rule.get("sid") != acl["operator"]
                   and (int(rule["rights"]) & write_mask) for rule in acl["rules"])):
        raise LifecycleError("candidate directory ACL is not operator-only")


@contextlib.contextmanager
def directory_fence(path: Path, identities: dict):
    """Pin every path component before a pathname-based lock can touch it.

    Native Windows opens each directory itself (never its reparse target), with
    DELETE sharing denied, from the volume root down. Once checked, a component
    cannot be replaced until the fence exits. POSIX fixtures use no-follow openat
    and yield the pinned parent fd for the lock open, even if a directory moves.
    """
    with contextlib.ExitStack() as pins:
        parent_fd = None
        kernel = _directory_kernel() if os.name == "nt" else None
        for component in reversed((path, *path.parents)):
            expected = identities.get(component)
            created = False
            try:
                if kernel is not None:
                    handle = kernel.CreateFileW(str(component), 0, 3, None, 3, 0x02200000, None)
                    if handle == ctypes.c_void_p(-1).value:
                        raise ctypes.WinError(ctypes.get_last_error())
                    pins.callback(kernel.CloseHandle, handle)
                    identity = _directory_info(kernel, handle)
                else:
                    fd = os.open(component.name if parent_fd is not None else component,
                                 os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                    pins.callback(os.close, fd)
                    parent_fd = fd
                    info = os.fstat(fd)
                    identity = info.st_dev, info.st_ino
            except FileNotFoundError:
                if expected is not None:
                    raise LifecycleError("candidate directory identity disappeared") from None
                created = True
                # The already-pinned parent makes this creation candidate-local.
                if kernel is not None:
                    component.mkdir()
                    handle = kernel.CreateFileW(str(component), 0, 3, None, 3, 0x02200000, None)
                    if handle == ctypes.c_void_p(-1).value:
                        raise ctypes.WinError(ctypes.get_last_error())
                    pins.callback(kernel.CloseHandle, handle)
                    identity = _directory_info(kernel, handle)
                else:
                    os.mkdir(component.name, dir_fd=parent_fd)
                    fd = os.open(component.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                    pins.callback(os.close, fd)
                    parent_fd = fd
                    info = os.fstat(fd)
                    identity = info.st_dev, info.st_ino
            if (component in identities and expected is None and not created
                    or expected is not None and identity != expected):
                raise LifecycleError("candidate directory identity changed")
            identities[component] = identity
        yield parent_fd


class FileLock:
    """Exclusive lock; ordinary admission is non-blocking, owned cleanup may wait a bounded interval."""

    def __init__(self, path: Path, *, timeout: float = 0, parent_fd: int | None = None):
        self.path = path
        self.timeout = timeout
        self.parent_fd = parent_fd
        self.fd: int | None = None

    def __enter__(self) -> "FileLock":
        if self.parent_fd is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        else:
            self.fd = os.open(self.path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600,
                              dir_fd=self.parent_fd)
        deadline = time.monotonic() + self.timeout
        try:
            while True:
                try:
                    if WINDOWS:
                        import msvcrt
                        os.lseek(self.fd, 0, os.SEEK_SET)
                        msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]  # Windows-only
                    else:
                        import fcntl
                        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    left = deadline - time.monotonic()
                    if left <= 0:
                        raise LifecycleError("another lifecycle command holds the integration lock") from None
                    time.sleep(min(0.1, left))
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise
        return self

    def __exit__(self, *exc: object) -> None:
        if self.fd is not None:
            try:
                if WINDOWS:
                    import msvcrt
                    os.lseek(self.fd, 0, os.SEEK_SET)
                    msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]  # Windows-only
            finally:
                os.close(self.fd)
                self.fd = None


# ------------------------------------------------------------------------------------------------ key
def keygen(layout: Layout) -> Path:
    """Create the private API key file once (32 random bytes, URL-safe); never prints the key."""
    path = layout.key_file
    if path.exists():
        read_key(layout)
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(path, (secrets.token_urlsafe(32) + "\n").encode("ascii"))
    restrict_to_user(path)
    return path


def restrict_to_user(path: Path) -> None:
    if WINDOWS:
        user = os.environ.get("USERNAME")
        if not user:
            raise LifecycleError("cannot determine the Windows user to restrict the key file to")
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"], check=True,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        path.chmod(0o600)


def read_key(layout: Layout) -> str:
    try:
        key = layout.key_file.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        raise LifecycleError("no API key file; run `keygen` first") from None
    if len(key) < 32:
        raise LifecycleError("the API key file is blank or too short; refusing to start an unauthenticated server")
    return key


# ------------------------------------------------------------------------------------------------ http
def http_json(url: str, *, key: str | None = None, timeout: float = 5.0) -> tuple[int, object]:
    headers = {"User-Agent": "omp-strata-lifecycle"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        body, status = exc.read(), exc.code
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, None
    try:
        return status, json.loads(body)
    except ValueError:
        return status, None


def base_url(layout: Layout) -> str:
    srv = layout.profile.data["server"]
    return f"http://{srv['listen_host']}:{srv['port']}"


# ------------------------------------------------------------------------------------------------ host facts
def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        if s.connect_ex((host, port)) == 0:
            return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if WINDOWS:
            s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", 0xFFFFFFFB), 1)
        try:
            s.bind((host, port))
        except OSError:
            return True
    return False


def parse_gpu_csv(text: str, fields: tuple[str, ...]) -> list[dict[str, str]]:
    """Strict nvidia-smi CSV rows; callers decide which unsupported fields may remain missing."""
    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error as exc:
        raise ValueError("malformed nvidia-smi CSV") from exc
    if not rows or any(len(row) != len(fields) for row in rows):
        raise ValueError("missing or malformed nvidia-smi CSV columns")
    return [dict(zip(fields, (value.strip() for value in row))) for row in rows]


def canonical_pci_bus_id(value: str) -> str:
    """Normalize NVIDIA's four/eight-digit domain and uppercase BDF to the profile form."""
    match = re.fullmatch(r"([0-9a-fA-F]{4}|[0-9a-fA-F]{8}):([0-9a-fA-F]{2}):([01][0-9a-fA-F])\.([0-7])", value)
    if not match:
        raise ValueError("invalid PCI bus ID")
    domain, bus, device, function = match.groups()
    return f"{domain.zfill(8)}:{bus}:{device}.{function}".lower()


def gpu_processes(xml_text: str, *, strict: bool = True) -> list[dict]:
    """pid and type of every process `nvidia-smi -q -x` lists. Type "C" is a compute-only process (another runtime);
    "G" and "C+G" are graphics clients: under WDDM every desktop process drawing on a display-attached GPU."""
    root = ElementTree.fromstring(xml_text)
    if not strict:
        # The scalar lane keeps its established observation policy; multi-card qualification is strict.
        return [{"pid": int(pid), "type": (p.findtext("type") or "").strip() or "C"}
                for p in root.iter("process_info") if (pid := (p.findtext("pid") or "").strip()).isdigit()]
    cards = root.findall("gpu")
    if root.tag != "nvidia_smi_log" or len(cards) != 1:
        raise ValueError("expected one indexed GPU in process XML")
    listing = cards[0].find("processes")
    if listing is None or (listing.text or "").strip():
        raise ValueError("GPU process list unavailable")
    out, seen = [], set()
    for p in listing:
        if p.tag != "process_info":
            raise ValueError("unknown GPU process record")
        pid = (p.findtext("pid") or "").strip()
        if not pid.isdigit() or int(pid) <= 0 or int(pid) in seen:
            raise ValueError("invalid or duplicate GPU process PID")
        seen.add(int(pid))
        out.append({"pid": int(pid), "type": (p.findtext("type") or "").strip() or "unknown"})
    return out


def gpu_facts(index: int, *, multi_gpu: bool = False) -> dict:
    """Keep scalar probes unchanged; the multi-card lane explicitly requests strict indexed identity facts."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, **({"reason": "nvidia-smi unavailable"} if multi_gpu else {})}
    if not multi_gpu:
        q = subprocess.run([exe, "-i", str(index), "--query-gpu=name,memory.total,memory.used,driver_version",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           timeout=30)
        listing = subprocess.run([exe, "-i", str(index), "-q", "-x"], capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, timeout=60)
        if q.returncode != 0 or not q.stdout.strip():
            return {"available": False}
        name, total, used, driver = [x.strip() for x in q.stdout.strip().splitlines()[0].split(",")]
        try:
            processes = gpu_processes(listing.stdout, strict=False)
        except ElementTree.ParseError:
            processes = [{"pid": -1, "type": "unreadable"}]
        compute = [p for p in processes if p["type"] not in ("G", "C+G")]
        return {"available": True, "name": name, "memory_total_mib": int(float(total)),
                "memory_used_mib": int(float(used)), "driver": driver, "compute_apps": len(compute),
                "graphics_apps": len(processes) - len(compute), "processes": processes}
    fields = ("index", "name", "pci.bus_id", "memory.total", "memory.used", "compute_cap", "driver_version", "display_active")
    try:
        q = subprocess.run([exe, "-i", str(index), "--query-gpu=" + ",".join(fields),
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=30)
        listing = subprocess.run([exe, "-i", str(index), "-q", "-x"], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, timeout=60)
        if q.returncode or listing.returncode:
            raise ValueError("nvidia-smi facts or process query failed")
        rows = parse_gpu_csv(q.stdout, fields)
        if len(rows) != 1:
            raise ValueError("expected one indexed GPU CSV row")
        row = rows[0]
        if not row["index"].isdigit() or int(row["index"]) != index:
            raise ValueError("GPU index mismatch")
        if not row["name"] or not re.fullmatch(r"\d+(?:\.\d+)*", row["driver_version"]):
            raise ValueError("missing GPU name or driver")
        if not all(row[f].isdigit() for f in ("memory.total", "memory.used")):
            raise ValueError("GPU memory unavailable")
        total, used = int(row["memory.total"]), int(row["memory.used"])
        if total <= 0 or used > total or not re.fullmatch(r"[1-9]\d*\.\d", row["compute_cap"]):
            raise ValueError("invalid GPU capacity or architecture")
        display = {"Enabled": True, "Disabled": False}.get(row["display_active"])
        if display is None:
            raise ValueError("display-active observation unavailable")
        bus = canonical_pci_bus_id(row["pci.bus_id"])
        processes = gpu_processes(listing.stdout)
    except (OSError, subprocess.SubprocessError, ValueError, ElementTree.ParseError) as exc:
        return {"available": False, "reason": str(exc)}
    attached = None
    try:
        attachment = subprocess.run([exe, "-i", str(index), "--query-gpu=index,display_attached",
                                     "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=30)
        if attachment.returncode == 0:
            rows = parse_gpu_csv(attachment.stdout, ("index", "display_attached"))
            if len(rows) == 1 and rows[0]["index"].isdigit() and int(rows[0]["index"]) == index:
                attached = {"Yes": True, "No": False}.get(rows[0]["display_attached"])
    except (OSError, subprocess.SubprocessError, ValueError):
        pass  # Missing physical attachment is a qualification problem, never inferred from display_active.
    compute = [p for p in processes if p["type"] not in ("G", "C+G")]
    return {"available": True, "gpu_index": index, "name": row["name"], "memory_total_mib": total,
            "memory_used_mib": used, "driver": row["driver_version"], "compute_apps": len(compute),
            "arch": row["compute_cap"].replace(".", ""), "pci_bus_id": bus, "display_active": display,
            "display_attached": attached,
            "graphics_apps": len(processes) - len(compute), "processes": processes}


def gpu_busy(gpu: dict, display_attached: bool) -> str | None:
    """Why the GPU is not free for this integration, or None. Graphics clients are tolerated only on a GPU the profile
    declares display-attached (their VRAM still counts against GPU_IDLE_MIB); a compute process never is."""
    if not gpu.get("available"):
        return None
    if (gpu["memory_used_mib"] >= GPU_IDLE_MIB or gpu["compute_apps"]
            or (gpu["graphics_apps"] and not display_attached)):
        return (f"{gpu['memory_used_mib']} MiB used, {gpu['compute_apps']} compute process(es), "
                f"{gpu['graphics_apps']} graphics client(s)")
    return None


def card_observations(profile, *, owned_pids=None) -> list[dict]:
    """Profile-ordered facts and occupancy. None checks idle; a PID set checks an active owned engine.

    Ownership must come from an identity-verified server tree. WDDM per-process VRAM is not inferred by subtraction.
    """
    observations = []
    for card in profile.gpu_requirements:
        index = card["gpu_index"]
        gpu = gpu_facts(index, multi_gpu=True) if profile.multi_gpu else gpu_facts(index)
        problems = []
        row = {"gpu_index": index, "gpu_model": gpu.get("name"), "arch": gpu.get("arch"),
               "pci_bus_id": gpu.get("pci_bus_id"), "memory_total_mib": gpu.get("memory_total_mib"),
               "memory_used_mib": gpu.get("memory_used_mib"), "driver_version": gpu.get("driver"),
               "display_active": gpu.get("display_active"), "owned_count": None,
               "foreign_compute_count": None, "graphics_client_count": None, "problems": problems}
        observations.append(row)
        if not gpu.get("available"):
            problems.append("GPU facts unavailable: " + gpu.get("reason", "nvidia-smi unavailable"))
            continue
        for key, actual in (("gpu_index", gpu.get("gpu_index")), ("gpu_model", gpu.get("name")),
                            ("arch", gpu.get("arch")), ("pci_bus_id", gpu.get("pci_bus_id"))):
            if card[key] is not None and actual != card[key]:
                problems.append(f"{key} does not match profile")
        if gpu["memory_total_mib"] < card["min_gpu_vram_mib"]:
            problems.append("VRAM below profile floor")
        if int(gpu["driver"].split(".")[0]) < profile.data["host"]["min_driver_major"]:
            problems.append("driver below profile floor")
        if profile.multi_gpu:
            if type(gpu.get("display_attached")) is not bool:
                problems.append("physical display_attached observation unavailable")
            elif gpu["display_attached"] != card["display_attached"]:
                problems.append("physical display_attached does not match profile")
        if gpu.get("display_active") and not card["display_attached"]:
            problems.append("display active on a non-display card")
        owned = owned_pids if owned_pids is not None else set()
        foreign = [p for p in gpu["processes"] if p["pid"] not in owned]
        graphics = sum(p["type"] in ("G", "C+G") for p in foreign)
        row.update(owned_count=sum(p["pid"] in owned for p in gpu["processes"]),
                   foreign_compute_count=len(foreign) - graphics, graphics_client_count=graphics)
        if owned_pids is None:
            busy = gpu_busy(gpu, card["display_attached"])
            if busy:
                problems.append("GPU in use: " + busy + "; its owner must release it first")
        else:
            if not row["owned_count"]:
                problems.append("owned engine not observed on card")
            if row["foreign_compute_count"] or graphics and not card["display_attached"]:
                problems.append("foreign GPU owner observed")
    return observations


# Stock releases whose layer-split staging (serve/server.py gpu_list, layer_split_value and ordered_gpus: the bodies
# vendored in tests/fixtures/strata_0_1_42_ordered_gpus.py) and startup messages were reviewed against
# parse_stage_order and _layer_boundaries. Add a release only after that review: an unreviewed one leaves every
# multi-GPU start degraded, and every gate refuses it.
# v0.2.1 app / 0.1.46 engine: identical ordered_gpus and layer-boundary/pipeline message writers.
# v0.2.3 app / 0.1.48 engine (#48): ordered_gpus adds only stock roles' early return (the configured order, no
# message) and a HIP-only built-in-graphics branch; the message writers are identical. Measured on the RTX 4090 +
# RTX 3090 pair (2026-10-23, docs/MEASUREMENTS.md): every start of the default, roles and split-32 drafts parsed
# complete with the order and boundaries those settings give.
# v0.2.7 app / 0.1.52 engine: gpu_list, layer_split_value, layer_split_of, ordered_gpus and engine_args are
# AST-identical to v0.2.3; child_env adds only DeepSeek- and HIP-guarded branches; the stage and layer-split message
# formats are unchanged. Measured on the RTX 4090 + RTX 3090 pair (2026-10-28, docs/MEASUREMENTS.md): both starts of
# the roles draft parsed complete, RTX 3090 first and RTX 4090 last, layers 0-23 / 24-47 (auto K=24).
# v0.2.8 app / 0.1.54 engine: gpu_list, layer_split_value, layer_split_of, ordered_gpus, engine_args and child_env are
# AST-identical to v0.2.7; the stage and layer-split message formats are unchanged. Measured on the RTX 4090 + RTX 3090
# pair (2026-10-30, docs/MEASUREMENTS.md): all four starts of the roles PLE-direct and stock-residency drafts parsed
# complete, RTX 3090 first and RTX 4090 last, layers 0-23 / 24-47 (auto K=24).
# v0.2.9 app / 0.1.55 engine: gpu_list, layer_split_value, layer_split_of, ordered_gpus, engine_args and the server's
# parse_engine_stage_line are AST-identical to v0.2.8; child_env adds only parallel_stack_env and gdn_stack_env, both
# no-ops off Linux (parallel_stack_platform). Measured on the RTX 4090 + RTX 3090 pair (2026-11-02,
# docs/MEASUREMENTS.md): all three v0.2.9 starts of the version A/B parsed complete, RTX 3090 first and RTX 4090 last,
# layers 0-23 / 24-47 (pinned split 24).
# v0.2.10 app / 0.1.56 engine: gpu_list, layer_split_value, layer_split_of, ordered_gpus, child_env and
# parse_engine_stage_line are AST-identical to v0.2.9; engine_args now applies stock drafting and vram_fit at every
# start, which leave a layer split's argv unchanged (fit_start returns early on a split; --pipeline-windows keeps the
# MTP); the stage, layer-split, dense-weight and expert-cache message formats are identical between engine builds
# 99866a47a2b8 and 06698c674. Measured on the RTX 4090 + RTX 3090 pair (2026-11-03, docs/MEASUREMENTS.md): the env86g
# measurement start parsed complete, RTX 3090 first and RTX 4090 last, layers 0-23 / 24-47 (pinned split 24).
# v0.2.11 app / 0.1.57 engine: gpu_list, layer_split_value, layer_split_of, ordered_gpus, child_env, engine_args and
# parse_engine_stage_line are AST-identical to v0.2.10, and so are the server's card-order writers; the Windows CUDA 13
# build 0bdcef4682c5 keeps 0.1.56's stage, layer-split, dense-weight and expert-cache formats (it only adds the
# short-of-memory walk lines, refused by start verification). Measured on the RTX 4090 + RTX 3090 pair (2026-11-06,
# docs/MEASUREMENTS.md): the df2 measurement start parsed complete, RTX 3090 first and RTX 4090 last, layers 0-23 /
# 24-47 (pinned split 24), one engine generation, expert caches 19.41 / 17.90 GiB.
# v0.2.12 app / 0.1.58 engine: gpu_list, layer_split_value, layer_split_of, ordered_gpus, child_env and engine_args are
# AST-identical to v0.2.11, and so are the server's card-order writers and the stage, layer-split, dense-weight and
# expert-cache formats (Windows CUDA 13 build 8a42a9457db6; its engine source differs from the tag only by a
# pre-sm_70 branch in qsa_select.cu). Measured on the RTX 4090 + RTX 3090 pair (2026-11-07, docs/MEASUREMENTS.md): the
# df2 measurement start parsed complete, RTX 3090 first and RTX 4090 last, layers 0-23 / 24-47 (pinned split 24),
# one engine generation, expert caches 19.40 / 17.90 GiB.
# v0.2.13 app / 0.1.59 engine: gpu_list, layer_split_value, layer_split_of, ordered_gpus and parse_engine_stage_line
# are AST-identical to v0.2.12; child_env only drops the Linux-only launcher env stacks and engine_args only adds the
# drafting fetch hint, neither touching card order, and the engine's stage, layer-split, dense-weight and expert-cache
# messages are unchanged (Windows CUDA 13 build 712fec6b4297; its sources equal the tag's). Measured on the RTX 4090 +
# RTX 3090 pair (2026-11-09, docs/MEASUREMENTS.md): the env86gt measurement start parsed complete (kept_configured),
# RTX 3090 first and RTX 4090 last, layers 0-23 / 24-47 (pinned split 24), one engine generation, expert caches
# 19.40 / 17.90 GiB.
# The native child_env/engine_args boundary is exercised in test_stage_order_stock; this does not qualify auto K.
STAGE_ORDER_REVIEWED_ENGINES = frozenset({"0.1.42", "0.1.43", "0.1.43.1", "0.1.44.1", "0.1.46", "0.1.48", "0.1.52",
                                          "0.1.54", "0.1.55", "0.1.56", "0.1.57", "0.1.58", "0.1.59"})
# v0.2.11's server prints through a bounded console queue (serve/nonblocking_out.py) that flushes a line's text and
# its newline separately, so a capture taken at readiness may briefly end mid-line.
CONSOLE_QUEUE_SINCE = (0, 1, 57)


def parse_stage_order(log_text: str, configured: list[int]) -> dict:
    """Parse a complete reviewed stock startup interval, never infer from partial/unknown messages."""
    result = {"configured": list(configured), "staged": None, "event": "unavailable", "messages": [],
              "complete": False, "reason": None}
    if (len(configured) < 2 or any(type(i) is not int or i < 0 for i in configured)
            or len(set(configured)) != len(configured)):
        result["reason"] = "invalid configured GPU order"
        return result
    if log_text and not log_text.endswith("\n"):
        result["reason"] = "truncated startup output"
        return result
    reorder = re.compile(r'\[strata\] layer split: card order (\d+(?:,\d+)+) '
                         r'\(the faster card last; "gpu_order": "as_given" keeps (\d+(?:,\d+)+), #1352\)')
    keep = re.compile(r"\[strata\] layer split: keeping card order (\d+(?:,\d+)+) - the faster card has "
                      r"less VRAM than the one the split ends on \(\d+ vs \d+ MiB, #1576\)")
    events = set()
    for line in log_text.splitlines():
        if "[strata] layer split:" not in line:
            continue
        result["messages"].append(line)
        match = reorder.fullmatch(line)
        if match:
            staged = tuple(map(int, match[1].split(",")))
            original = list(map(int, match[2].split(",")))
            event = "reordered"
            valid = original == configured and list(staged) != configured
        else:
            match = keep.fullmatch(line)
            if not match:
                result["reason"] = "unknown stage-order message"
                return result
            staged = tuple(map(int, match[1].split(",")))
            event = "kept_1576"
            valid = list(staged) == configured
        if not valid or sorted(staged) != sorted(configured):
            result["reason"] = "stage-order message contradicts configured GPUs"
            return result
        events.add((event, staged))
    if len(events) > 1:
        result["reason"] = "contradictory stage-order messages"
        return result
    event, staged = next(iter(events)) if events else ("kept_configured", tuple(configured))
    result.update(staged=list(staged), event=event, complete=True)
    return result


def _engine_log_path(layout: Layout) -> Path:
    """Stock opens config.log relative to the server's cwd (the pinned source root)."""
    value = read_json(layout.strata_config).get("log")
    if not isinstance(value, str) or not value.strip():
        raise LifecycleError("generated config must name the engine log for multi-GPU startup capture")
    path = (layout.strata / value).resolve()
    if not path.is_relative_to(layout.root.resolve()) or path.exists() and not path.is_file():
        raise LifecycleError("generated engine log must resolve to a file inside the integration root")
    return path


def _startup_log_interval(layout: Layout, run: dict, field: str, allowed_root: Path) -> tuple[str, dict]:
    path = (layout.root / run[field]).resolve()
    if not path.is_relative_to(allowed_root.resolve()):
        raise ValueError(f"{field}: startup log outside allowed integration directory")
    offset = run.get(field + "_start_offset")
    if type(offset) is not int or offset < 0:
        raise ValueError(f"{field}: startup log interval unavailable")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if before.st_size <= offset:
            raise ValueError(f"{field}: startup log interval missing or truncated")
        stream.seek(offset)
        raw = stream.read(before.st_size - offset)
        after = os.fstat(stream.fileno())
    current = path.stat()
    if (len(raw) != before.st_size - offset or after.st_size < before.st_size
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)):
        raise ValueError(f"{field}: startup log changed during capture")
    return raw.decode("utf-8"), {"path": run[field], "start": offset, "end": before.st_size}


def _settled_startup_interval(layout: Layout, run: dict, field: str, allowed_root: Path, *, wait_s: float = 2.0,
                              step_s: float = 0.1) -> tuple[str, dict]:
    """Read a startup interval, giving a console-queued line up to wait_s to reach its newline."""
    deadline = time.monotonic() + wait_s
    while True:
        text, interval = _startup_log_interval(layout, run, field, allowed_root)
        if text.endswith("\n") or time.monotonic() >= deadline:
            return text, interval
        time.sleep(step_s)


def _layer_boundaries(log_text: str, staged: list[int]) -> list[dict]:
    """Require one consistent, contiguous owned layer range for every CUDA stage in this engine interval."""
    if not log_text.endswith("\n"):
        raise ValueError("truncated engine startup output")
    boundary = re.compile(r"strata generate: layer split: CUDA(\d+) runs layers (\d+)-(\d+)"
                          r"(?:, expert cache \d+ slots \((\d+(?:\.\d+)?) GiB\), "
                          r"\d+ of its \d+ profiled pairs; slot 0 verified)?")
    primary_cache = re.compile(r"strata generate: expert cache \d+ slots, (\d+(?:\.\d+)?) GiB of VRAM; policy is")
    boundaries, cache_lines = {}, set()
    starts = 0
    for line in log_text.splitlines():
        if line.startswith("[strata] ") and " engine started: " in line:
            starts += 1
        if "strata generate: layer split: CUDA" in line and "runs layers" in line:
            match = boundary.fullmatch(line)
            if not match:
                raise ValueError("unknown engine layer-boundary syntax")
            index = int(match[1])
            if index in boundaries and boundaries[index][0] != line:
                raise ValueError("contradictory engine layer boundaries")
            row = {"cuda_index": index, "first_layer": int(match[2]), "last_layer": int(match[3])}
            if match[4] is not None:
                row["expert_cache_gib"] = float(match[4])
            boundaries[index] = (line, row)
        if primary_cache.fullmatch(line):
            cache_lines.add(line)
    if starts > 1:
        raise ValueError("multiple engine generations in startup interval")
    if len(cache_lines) > 1:
        raise ValueError("contradictory primary expert cache observations")
    if set(boundaries) != set(range(len(staged))):
        raise ValueError("engine layer boundaries missing or unexpected CUDA stages")
    result, next_layer = [], 0
    for index, physical in enumerate(staged):
        row = boundaries[index][1]
        if row["first_layer"] != next_layer or row["last_layer"] < row["first_layer"]:
            raise ValueError("engine layer boundaries are not contiguous ascending ranges from layer 0")
        row["gpu_index"] = physical
        next_layer = row["last_layer"] + 1
        result.append(row)
    if cache_lines:
        value = float(primary_cache.fullmatch(next(iter(cache_lines)))[1])
        if "expert_cache_gib" in result[0] and result[0]["expert_cache_gib"] != value:
            raise ValueError("contradictory primary expert cache observations")
        result[0]["expert_cache_gib"] = value
    return result


def capture_startup_gpu_order(layout: Layout) -> dict:
    """Bind complete owned startup output to the recorded engine generation; persist only at start, not status."""
    run = read_json(layout.run_record)
    configured = list(layout.profile.gpu_indices)
    split = layout.profile.data["strata"]["setup_args"].get("layer_split", "auto")
    observation = {"configured": configured, "staged": None, "event": "unavailable", "messages": [],
                   "complete": False, "reason": None, "layer_split": split, "layer_boundaries": []}
    try:
        if str(layout.profile.data["strata"]["engine_version"]).lstrip("v") not in STAGE_ORDER_REVIEWED_ENGINES:
            raise ValueError("stage-order inference requires a reviewed stock Strata release")
        engine = procs.matches(run.get("engine"))
        server = procs.matches(run.get("server"))
        if engine is None or server is None or run.get("state") != "ready":
            raise ValueError("owned ready engine identity unavailable")
        engines = [p for p in procs.descendants(server.pid) if Path(p.exe).name.lower().startswith("strata")]
        if len(engines) != 1 or engines[0].as_dict() != engine.as_dict():
            raise ValueError("engine generation changed before capture")
        version = release_version(str(layout.profile.data["strata"]["engine_version"]))
        read = (_settled_startup_interval if version is not None and version >= CONSOLE_QUEUE_SINCE
                else _startup_log_interval)
        text, interval = read(layout, run, "log", layout.logs)
        parsed = parse_stage_order(text, configured)
        observation.update(parsed)
        observation["log_interval"] = interval
        if not parsed["complete"]:
            raise ValueError(parsed["reason"])
        if split != "auto" and parsed["staged"] != configured:
            raise ValueError("engine stage order differs from configured GPUs for the pinned manual split")
        engine_text, engine_interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        observation["engine_log_interval"] = engine_interval
        boundaries = _layer_boundaries(engine_text, parsed["staged"])
        if split != "auto" and [row["first_layer"] for row in boundaries[1:]] != [int(split)]:
            raise ValueError(f"engine layer boundaries differ from the pinned manual split {split}")
        if procs.matches(run["engine"]) is None or procs.matches(run["server"]) is None:
            raise ValueError("engine generation changed during capture")
        engines = [p for p in procs.descendants(server.pid) if Path(p.exe).name.lower().startswith("strata")]
        if len(engines) != 1 or engines[0].as_dict() != engine.as_dict():
            raise ValueError("engine generation changed during capture")
        observation.update(engine_identity=engine.as_dict(),
                           engine_instance_sha256=sha256_bytes(canonical_json(engine.as_dict())),
                           layer_boundaries=boundaries)
    except (OSError, ValueError, KeyError) as exc:
        observation.update(staged=None, event="unavailable", complete=False, reason=str(exc))
    latest = read_json(layout.run_record)
    if any(latest.get(key) != run.get(key) for key in ("engine", "server", "requested_utc", "state")):
        observation.update(staged=None, event="unavailable", complete=False,
                           reason="run generation changed during capture")
    latest["gpu_stage_order"] = observation
    atomic_write_json(layout.run_record, latest)
    return observation


def doctor(layout: Layout) -> dict:
    """Read-only inspection; returns {'ok': bool, 'checks': [...]} with redacted, actionable messages."""
    p = layout.profile.data
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str, blocking: bool = True) -> None:
        checks.append({"check": name, "ok": ok, "detail": detail, "blocking": blocking})

    host = p["host"]
    plat = host_platform()
    want_os = {"windows": "windows-x64", "linux": "linux-x64"}[host["os"]]
    check("platform", plat == want_os, f"{plat} (profile expects {want_os})")
    check("python", sys.version_info >= (3, 11), f"tool Python {sys.version.split()[0]}")
    check("git", shutil.which("git") is not None, "git on PATH" if shutil.which("git") else "git missing")
    mem = procs.memory()
    gib = 1 << 30
    if mem["total"]:
        check("ram_total", mem["total"] / gib >= host["min_total_ram_gib"],
              f"{mem['total'] / gib:.1f} GiB total (needs {host['min_total_ram_gib']})")
        check("ram_available", mem["available"] / gib >= host["min_available_ram_gib_at_start"],
              f"{mem['available'] / gib:.1f} GiB available now (start needs "
              f"{host['min_available_ram_gib_at_start']})", blocking=False)
    for card in layout.profile.gpu_requirements:
        index = card["gpu_index"]
        suffix = f".{index}" if layout.profile.multi_gpu else ""
        gpu = gpu_facts(index, multi_gpu=True) if layout.profile.multi_gpu else gpu_facts(index)
        if gpu.get("available"):
            check("gpu_model" + suffix, gpu["name"] == card["gpu_model"], f"GPU {index}: {gpu['name']}")
            check("gpu_vram" + suffix, gpu["memory_total_mib"] >= card["min_gpu_vram_mib"], f"{gpu['memory_total_mib']} MiB")
            check("driver" + suffix, int(gpu["driver"].split(".")[0]) >= host["min_driver_major"], f"driver {gpu['driver']}")
            if layout.profile.multi_gpu:
                for field in ("gpu_index", "arch", "pci_bus_id"):
                    check(field + suffix, gpu.get(field) == card[field], f"{field}: {gpu.get(field)}")
                check("display_active" + suffix, not gpu["display_active"] or card["display_attached"],
                      f"display active: {gpu['display_active']}")
            busy = gpu_busy(gpu, card["display_attached"])
            check("gpu_idle" + suffix, busy is None, f"{busy}; another runtime must be stopped by its owner first" if busy
                  else f"idle ({gpu['graphics_apps']} display client(s))" if gpu["graphics_apps"] else "idle",
                  blocking=False)
        else:
            check("gpu" + suffix, False, gpu.get("reason", "nvidia-smi unavailable") if layout.profile.multi_gpu
                  else "nvidia-smi unavailable")
    layout.root.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(layout.root).free / gib
    # The floor includes stock's input download, not only space still needed after a verified fetch or hard-link.
    # Size is sufficient for space accounting; fetch/install remain responsible for SHA-256 identity.
    root = layout.root.resolve()
    present = 0
    for item in fetch.plan(layout, platform=want_os, only={"model", "dflash2", "engine", "llama"}):
        try:
            if item.dest.resolve().is_relative_to(root) and item.dest.is_file() and item.dest.stat().st_size == item.bytes:
                present += item.bytes
        except OSError:
            continue
    check("disk", free + present / gib >= host["min_free_disk_gib"],
          f"{free:.1f} GiB free + {present / gib:.1f} GiB present pinned inputs at the integration root "
          f"(needs {host['min_free_disk_gib']} GiB)")
    srv = p["server"]
    busy = port_in_use(srv["listen_host"], srv["port"])
    owned = procs.matches((read_json(layout.run_record) if layout.run_record.exists() else {}).get("server"))
    check("port", not busy or owned is not None,
          f"{srv['listen_host']}:{srv['port']} " + ("held by this integration" if owned else
                                                    "occupied by an unrelated process" if busy else "free"),
          blocking=False)
    check("key_file", layout.key_file.exists(), "present" if layout.key_file.exists() else "run keygen",
          blocking=False)
    rec = read_json(layout.install_record) if layout.install_record.exists() else None
    check("installed", bool(rec) and rec.get("profile_fingerprint") == layout.profile.fingerprint,
          "install record matches this profile" if rec and rec.get("profile_fingerprint") ==
          layout.profile.fingerprint else "not installed for this profile", blocking=False)
    real_appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Strata"
    if WINDOWS:
        check("user_strata_settings", True, "a per-user %APPDATA%\\Strata exists (left untouched)"
              if real_appdata.exists() else "no per-user %APPDATA%\\Strata (this tool never creates one)",
              blocking=False)
        real_localappdata = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        real_runtime = real_localappdata / "Strata/runtime/.activity.lock"
        check("user_strata_runtime", True, "a per-user Strata runtime activity lock exists (left untouched)"
              if real_runtime.exists() else "no per-user Strata runtime activity lock (left untouched)",
              blocking=False)
    return {"ok": all(c["ok"] for c in checks if c["blocking"]), "checks": checks}


# ------------------------------------------------------------------------------------------------ identity
def verify_install_fast(layout: Layout) -> dict:
    """Recheck the install record against disk before a start: small files are rehashed, shards by cached proof."""
    if not layout.install_record.exists():
        raise LifecycleError("not installed; run install first")
    rec = read_json(layout.install_record)
    if rec.get("profile_fingerprint") != layout.profile.fingerprint:
        raise LifecycleError("the install was made for a different profile fingerprint; reinstall or switch back")
    root = layout.root.resolve()
    shards = {layout.model_file(f).resolve().relative_to(root).as_posix(): f for f in
              layout.profile.data["model"]["files"]}
    drift = []
    for rel, want in rec["identity"]["files"].items():
        path = root / rel
        if rel in shards:
            if not verified_ok(path, want["bytes"], want["sha256"]):
                drift.append(rel)
            continue
        if not path.is_file() or path.stat().st_size != want["bytes"] or sha256_file(path) != want["sha256"]:
            drift.append(rel)
    if sha256_file(layout.strata_config) != rec["identity"]["config_file_sha256"]:
        drift.append(layout.strata_config.name)
    verify_generated(layout)
    shared = read_json(layout.shared_settings) if layout.shared_settings.exists() else {}
    if shared != {}:
        drift.append(layout.shared_settings.name)
    if drift:
        raise LifecycleError("runtime inputs drifted from the install record: " + ", ".join(sorted(drift)[:12]))
    return rec


def server_argv(layout: Layout) -> list[str]:
    srv = layout.profile.data["server"]
    return [str(layout.venv_python), str(layout.strata / "serve" / "server.py"), "--engine", "strata", "--config",
            str(layout.strata_config), "--port", str(srv["port"]), "--host", srv["listen_host"]]


def server_env(layout: Layout, key: str) -> dict[str, str]:
    # Inherited STRATA_* variables are engine and server tuning/debug knobs (v0.1.31 alone added 16): a setting changes
    # only through a new profile, so none passes through; owned key/runtime values are set explicitly below.
    env = {k: v for k, v in os.environ.items()
           if not any(m in k.upper() for m in SECRET_ENV_MARKERS) and not k.upper().startswith(("STRATA_", "DS4_"))
           and k.upper() not in ("CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER")}
    env["APPDATA"] = str(layout.appdata)
    env["XDG_CONFIG_HOME"] = str(layout.appdata)
    if layout.profile.pins_runtime_dir:
        env["STRATA_RUNTIME_DIR"] = str(layout.strata_runtime.resolve())
        env["LOCALAPPDATA"] = str(layout.localappdata.resolve())
    env["PYTHONIOENCODING"] = "utf-8"
    env[layout.profile.data["server"]["api_key_env"]] = key
    return env


# ------------------------------------------------------------------------------------------------ serve
def serve(layout: Layout, *, log_path: Path, launch_id: str) -> int:
    """Foreground wrapper (normally launched detached by `start`): key -> env -> stock server.py child.

    The wrapper has no console of its own when detached, so its own failures go to the server log too."""
    experimental = bool(os.environ.get(TREE_TOKEN_ENV))
    if not experimental:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    with (directory_fence(log_path.parent, {}) if experimental else contextlib.nullcontext()), \
            open(log_path, "xb" if experimental else "ab", buffering=0) as out:
        with FileLock(layout.lock_file, timeout=120):
            record = read_json(layout.run_record) if layout.run_record.exists() else {}
            if (not launch_id or record.get("launch_id") != launch_id or record.get("state") != "launching"
                    or record.get("profile_fingerprint") != layout.profile.fingerprint):
                raise LifecycleError("serve generation changed or stopped before launch")
            child = None
            try:
                if record.get("tree_token"):
                    # Verify membership before ANY server spawn. The driver keeps
                    # the owning handle until its tree is proved dead.
                    job = ProcessJob(record["tree_token"], existing=True)
                    try:
                        job.assign(job.kernel.GetCurrentProcess())
                    finally:
                        job.close()
                key = read_key(layout)
                me = procs.info(os.getpid(), ppid=os.getppid()) if experimental else procs.info(os.getpid())
                if me is None:
                    raise LifecycleError("serve wrapper identity unavailable")
                # Publish custody before spawn. If child publication AND cleanup fail,
                # stop must not mistake an unknown child lifetime for an idle request.
                record.update({"wrapper": me.as_dict(), "state": "starting", "unpublished_child": True})
                atomic_write_json(layout.run_record, record)
                flags = CREATE_NO_WINDOW if WINDOWS else 0
                argv, env = server_argv(layout), server_env(layout, key)
                if record.get("tree_token"):
                    env[TREE_TOKEN_ENV] = record["tree_token"]
                    argv[1:1] = ["-X", "omp_strata_tree=" + record["tree_token"]]
                child = subprocess.Popen(argv, cwd=layout.strata, env=env,
                                         stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                         creationflags=flags, start_new_session=not WINDOWS)
                server = procs.info(child.pid, ppid=os.getpid()) if experimental else procs.info(child.pid)
                if server is None:
                    raise LifecycleError("server identity unavailable after spawn")
                record.update({"server": server.as_dict(), "unpublished_child": False,
                               "serve_started_utc": utc_now()})
                atomic_write_json(layout.run_record, record)
            except (Exception, KeyboardInterrupt) as exc:
                # Keep the root lock until the unpublished child's lifetime ends.
                # The Popen handle owns this tree even if identity lookup/write failed.
                if child is not None:
                    if child.poll() is not None:
                        # A dead redirector/parent is not evidence that its children
                        # died. Never signal a possibly reused PID or clear custody.
                        raise LifecycleError("unpublished child tree is unknown after parent exit") from exc
                    if WINDOWS:
                        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=30, check=True)
                    else:
                        os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=30)
                out.write(f"[omp-strata] serve wrapper failed: {type(exc).__name__}: {exc}\n".encode("utf-8"))
                record.update({"state": "exited", "exit_code": -1, "unpublished_child": False,
                               "wrapper_error": type(exc).__name__})
                atomic_write_json(layout.run_record, record)
                raise
        rc = child.wait()
    with FileLock(layout.lock_file, timeout=120):
        record = read_json(layout.run_record)
        if (record.get("launch_id") == launch_id and record.get("server") and server
                and record["server"] == server.as_dict() and record.get("state") in ("starting", "ready")):
            record.update({"state": "exited", "exit_code": rc, "exited_utc": utc_now()})
            atomic_write_json(layout.run_record, record)
    return rc


def _launch_detached(argv: list[str], *, cwd: Path, log: Path, job_token: str | None = None) -> None:
    if WINDOWS and job_token:
        # The start command already belongs to the driver's launch job. Direct
        # creation inherits it; no WMI broker can dispatch a late unowned wrapper.
        job = ProcessJob(job_token, existing=True)
        try:
            with directory_fence(log.parent, {}), open(log, "xb") as out:
                child = job.spawn(argv, stdout=out, stderr=out, env=os.environ, cwd=cwd)
                child.detach()
        finally:
            job.close()
    elif WINDOWS:
        line = subprocess.list2cmdline(argv)
        script = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="
                  + _ps_quote(line) + "; CurrentDirectory=" + _ps_quote(str(cwd)) + "}; "
                  "if ($r.ReturnValue -ne 0) { exit 1 }; $r.ProcessId")
        out = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
        if out.returncode != 0:
            raise LifecycleError(f"could not launch the serve wrapper: {out.stderr.strip()[:300]}")
    else:
        with open(log, "ab") as f:
            subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT,
                             start_new_session=True)


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


# ------------------------------------------------------------------------------------------------ verdict
# The one decision of what a root is: the closed table in docs/OPERATIONS.md ("Lifecycle states"). `status` renders
# it, `start` admits only an idle root, and `install` and `idle_generation` require it quiescent; recovery advice
# shares stop's structural admission. The qualification launcher admits only IDLE_STATES.
IDLE_STATES = ("not_installed", "stopped", "failed")
ROWS = ("unreadable-record", "unreadable-table", "custody-unknown", "launch-pending", "launch-abandoned", "launch-unrecorded",
        "wrapper-publishing", "mismatched", "server-live", "orphans", "job-unproved", "port-held", "idle")
CUSTODY_REFUSAL = "unpublished child lifetime is unknown; retain custody for reconciliation"
PENDING_REFUSAL = "pending launch already owns this root"


@dataclass
class Verdict:
    row: str
    state: str
    problems: list[str] = field(default_factory=list)
    # Every process of the root found alive, recorded or not.
    live: dict[str, procs.ProcInfo] = field(default_factory=dict)
    # Readable evidence, no process/launch, proved custody and a free port: install and idle_generation admission.
    quiescent: bool = False
    refusal: str | None = None  # why `start` must not act; None exactly when the root is idle
    details: dict = field(default_factory=dict)
    run: dict = field(default_factory=dict)
    # pid -> the recorded role whose current tree it was found in (server first, then wrapper, then the rest).
    under: dict[int, str] = field(default_factory=dict)

    @property
    def idle(self) -> bool:
        return self.state in IDLE_STATES


def process_table() -> procs.ProcessTable:
    """The one process-table read a verdict rests on."""
    return procs.table()


def recorded_processes(run: dict) -> list[tuple[str, object]]:
    """Roles actually recorded, including malformed values for the verdict to reject.

    Released _finish_start writes engine=None to mean no recorded engine; no other role has that null meaning.
    A record states which roles a run recorded, not which processes exist. Never-recorded processes are found,
    if at all, by the runtime-root census. An empty server_tree is a valid collection with no members.
    """
    roles = [(role, run[role]) for role in ("wrapper", "server", "engine")
             if role in run and not (role == "engine" and run[role] is None)]
    tree = run.get("server_tree", [])
    if isinstance(tree, list):
        roles.extend((f"server_tree[{index}]", identity) for index, identity in enumerate(tree))
    else:
        roles.append(("server_tree", tree))
    return roles


def runs_from(exe: str, base: Path) -> bool:
    """True when the normalized absolute executable or its resolution lies inside the runtime."""
    if not exe or not os.path.isabs(exe):
        return False
    exe = os.path.normpath(exe)
    if os.pardir in Path(exe).parts:
        return False
    base = os.path.abspath(base)
    prefixes = {os.path.normcase(os.path.join(path, "")) for path in (base, os.path.realpath(base))}
    return any(os.path.normcase(path).startswith(prefix)
               for path in (exe, os.path.realpath(exe)) for prefix in prefixes)


def _alive(identity: object, table: procs.ProcessTable) -> procs.ProcInfo | None:
    if not procs.valid_identity(identity) or table.observe(identity) is not procs.Presence.SAME:
        return None
    return table.identified[identity["pid"]]


def _descendants(table: dict[int, procs.ProcInfo],
                 live: dict[str, procs.ProcInfo]) -> tuple[dict[str, procs.ProcInfo], dict[int, str]]:
    """The current descendants of the live recorded processes, deepest first, read from the same table, and for each
    process reached the role whose tree it lies in (the server's tree first, then the wrapper's, then the rest)."""
    children: dict[int, list[procs.ProcInfo]] = {}
    for proc in table.values():
        children.setdefault(proc.ppid, []).append(proc)
    recorded = {proc.pid for proc in live.values()}
    order: list[procs.ProcInfo] = []
    under: dict[int, str] = {}
    for role in sorted(live, key=lambda role: {"server": 0, "wrapper": 1}.get(role, 2)):
        if live[role].pid in under:
            continue
        frontier = [live[role]]
        while frontier:
            parent = frontier.pop(0)
            for child in children.get(parent.pid, []):
                # Creation-order checks belong to the reader; traverse only the edges it vouched for.
                if child.pid in under:
                    continue
                under[child.pid] = role
                frontier.append(child)
                if child.pid not in recorded:
                    order.append(child)
    return {f"descendant[{proc.pid}]": proc for proc in reversed(order)}, under


def _unrecorded(layout: Layout, table: dict[int, procs.ProcInfo], known: dict) -> dict[str, procs.ProcInfo]:
    """Processes of the root its record does not name: whatever executes a file inside the root's runtime
    (`runtime/strata`: the engine, the DSV41 engine, the llama.cpp tools, the venv interpreter). A process running
    from elsewhere is not counted; that is the declared residual."""
    pids = {proc.pid for proc in known.values()} | {os.getpid()}
    return {f"unrecorded[{proc.pid}]": proc for proc in table.values()
            if proc.pid not in pids and runs_from(proc.exe, layout.strata)}




def _describe(live: dict[str, procs.ProcInfo]) -> str:
    return ", ".join(f"{role} {Path(p.exe).name} pid {p.pid}" for role, p in sorted(live.items()))


def _stop_custody_refusal(run: dict) -> str | None:
    """Structural stop admission, shared by the action and all recovery advice."""
    if run.get("tree_token") and not WINDOWS:
        return "reconcile it on its Windows host"
    if run.get("unpublished_child") and not run.get("tree_token"):
        return CUSTODY_REFUSAL
    return None


def _stop_advice(run: dict) -> str:
    return _stop_custody_refusal(run) or "run `stop` for this root"


def _read_record(path: Path) -> object:
    """Read verdict evidence without allowing a duplicate role key to erase an earlier identity."""
    def unique_roles(pairs):
        record = {}
        for key, value in pairs:
            if key in ("wrapper", "server", "engine", "launcher", "server_tree") and key in record:
                raise ValueError("duplicated process role")
            record[key] = value
        return record
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_roles)


def verdict(layout: Layout) -> Verdict:
    """The root's row in the closed state table, first match wins (docs/OPERATIONS.md, "Lifecycle states")."""
    errors = []

    def record(path: Path, name: str, absent):
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                raise ValueError("record entry is not a regular file")
            value = _read_record(path)
        except FileNotFoundError:
            try:
                path.lstat()  # A broken link is still evidence, not an absent directory entry.
            except FileNotFoundError:
                return absent
            except OSError:
                pass
            value = None
        except (OSError, ValueError):
            value = None
        if not isinstance(value, dict):
            errors.append(name)
            return absent
        return value

    run = record(layout.run_record, "run", {})
    install = record(layout.install_record, "install", None)
    recorded = recorded_processes(run)
    try:
        table = process_table()
    except procs.TableUnavailable as exc:
        table, unavailable = None, str(exc)
        live, owned, under = {}, {}, {}
    else:
        live = {role: proc for role, identity in recorded if (proc := _alive(identity, table))}
        descendants, under = _descendants(table.identified, live)
        known = {**live, **descendants}
        owned = {**known, **_unrecorded(layout, table.identified, known)}
    # A launcher is launch evidence, not runtime ownership; consult it during launch and before quiescence.
    active_launcher = run.get("state") == "launching" or not owned
    identities = [*recorded, ("launcher", run["launcher"])] if active_launcher and "launcher" in run else recorded
    malformed = [role for role, identity in identities if not procs.valid_identity(identity)]
    if malformed and "run" not in errors:
        errors.append("run")
    details = {"unreadable_records": errors} if errors else {}
    if malformed:
        details["unreadable_roles"] = malformed
    problems = [f"{name} record unreadable; reconcile this root by hand" for name in errors]
    if table is None:
        message = f"process census unavailable: {unavailable}; custody unknown, so the root is not reported idle (retry `status`)"
        return Verdict("unreadable-table", "degraded", [*problems, message],
                       refusal="; ".join([*problems, message]), run=run, details=details)
    found = {"details": {**details, **({"live": sorted(owned)} if owned else {})}, "run": run, "under": under,
             "refusal": f"integration-owned processes already running ({', '.join(sorted(owned))}); {_stop_advice(run)}"}
    unknown = [(role, identity["pid"]) for role, identity in identities
               if procs.valid_identity(identity) and table.observe(identity) is procs.Presence.UNKNOWN]
    if unknown:
        names = ", ".join(f"{role} pid {pid}" for role, pid in unknown)
        message = (f"cannot prove absence or PID reuse for {names}; custody unknown, so the root is not reported idle. "
                   "Inspect each PID and reconcile custody by hand; a confirmed-stale run record must be cleared "
                   f"by hand ({layout.run_record}) before retrying `status`")
        return Verdict("unreadable-table", "degraded", [*problems, message], owned,
                       **{**found, "refusal": "; ".join([*problems, message]),
                          "details": {**found["details"], "unidentified_records": [role for role, _ in unknown]}})
    if errors:
        return Verdict("unreadable-record", "degraded", problems, owned,
                       **{**found, "refusal": "; ".join(problems)})
    state = run.get("state")
    stopper = _stop_advice(run)
    if run.get("unpublished_child"):
        if state == "starting" and "wrapper" in live:
            return Verdict("wrapper-publishing", "starting",
                           [f"launch in progress: its wrapper (pid {live['wrapper'].pid}) is publishing its server"],
                           owned, **{**found, "refusal": CUSTODY_REFUSAL,
                                     "details": {**found["details"], "pending": True}})
        return Verdict("custody-unknown", "degraded",
                       [f"the serve wrapper's child was never recorded and its lifetime is unknown; {stopper}"],
                       owned, **{**found, "refusal": CUSTODY_REFUSAL})
    if state == "launching":
        pending = {**found, "refusal": f"{PENDING_REFUSAL}; {stopper} before replacement",
                   "details": {**found["details"], "pending": True}}
        if "launcher" not in run:
            return Verdict("launch-unrecorded", "degraded",
                           [f"launch pending: its start command identity is not recorded; a dispatched wrapper may "
                            f"still be waiting for the root lock; {stopper} to fence it"], owned, **pending)
        launcher = _alive(run["launcher"], table)
        if launcher is not None:
            return Verdict("launch-pending", "starting",
                           [f"launch pending: its start command (pid {launcher.pid}) has not handed over to its "
                            "wrapper"], owned, **pending)
        return Verdict("launch-abandoned", "degraded",
                       ["launch abandoned before its wrapper published: its start command is gone and a dispatched "
                        f"wrapper may still be waiting for the root lock; {stopper} to fence it"], owned, **pending)
    # Custody and the port precede every row that can be quiescent, including a different installed profile.
    if not owned:
        token = run.get("tree_token")
        if token and not (state == "stopped" and run.get("tree_verified_empty") == token):
            message = f"process-tree generation not proved empty; {stopper}"
            return Verdict("job-unproved", "degraded", [message], refusal=message, run=run)
        srv = layout.profile.data["server"]
        try:
            occupied = port_in_use(srv["listen_host"], srv["port"])
        except OSError as exc:
            message = (f"configured port {srv['listen_host']}:{srv['port']} unreadable ({exc}); "
                       "inspect the listener on this host, then retry `status` before start or install")
            return Verdict("port-held", "degraded", [message], refusal=message, run=run)
        if occupied:
            # Reuse the platform listener query; import lazily because remote's errors derive from LifecycleError.
            from .remote import RemoteError, listener_pids
            try:
                pids = listener_pids(srv["port"])
                holder = "PID " + ", ".join(map(str, sorted(pids))) if pids else "PID unavailable"
            except RemoteError:
                holder = "PID unavailable (inspect the listener on this host)"
            message = (f"{srv['listen_host']}:{srv['port']} is occupied; ownership unproved, so treating its holder "
                       "as a process this integration does not own; refusing to start or adopt it. "
                       f"End the holder ({holder}) or change the port before start or install")
            return Verdict("port-held", "degraded", [message], refusal=message, run=run)
    if install is not None and install.get("profile_fingerprint") != layout.profile.fingerprint:
        if not owned:
            found["refusal"] = "the install was made for a different profile fingerprint; reinstall or switch back"
        return Verdict("mismatched", "mismatched", ["install record belongs to another profile fingerprint"], owned,
                       quiescent=not owned, **found)
    if owned:
        remain = f"({_describe(owned)}); {stopper}"
        if install is None:
            return Verdict("orphans", "degraded", [f"install record missing while owned processes remain {remain}"],
                           owned, **found)
        if "server" not in live:
            return Verdict("orphans", "degraded", [f"server process gone while other owned processes remain {remain}"],
                           owned, **found)
        if run.get("runtime_identity_sha256") != install.get("runtime_identity_sha256"):
            return Verdict("server-live", "mismatched", ["running server was started from another install identity"],
                           owned, **found)
        if state == "starting":
            return Verdict("server-live", "starting", [], owned, **found)
        if state == "stop_incomplete":
            return Verdict("server-live", "degraded", [f"an earlier stop did not end {remain}"], owned, **found)
        # `status` decides healthy or degraded from the authenticated checks.
        return Verdict("server-live", "healthy", [], owned, **found)
    if install is None:
        return Verdict("idle", "not_installed", quiescent=True, run=run)
    if state == "exited" and run.get("exit_code") not in (0, None):
        return Verdict("idle", "failed", quiescent=True, run=run,
                       details={"exit_code": run.get("exit_code"), "log": run.get("log")})
    return Verdict("idle", "stopped", quiescent=True, run=run)


def idle_generation(layout: Layout, *, expected: str | None = None, timeout: float = 30) -> str:
    """Caller holds the installation lock through this check and all admitted effects. The candidate path requires
    a quiescent root whose prior generation, if any, is a process-tree job proved empty."""
    root = verdict(layout)
    current = root.run
    if root.row == "unreadable-record" or layout.run_record.exists() and not current:
        reason = root.refusal or "run record is empty; reconcile this root by hand"
        raise LifecycleError(f"partial candidate generation record: {reason}")
    if not root.quiescent:
        raise LifecycleError(f"prior candidate generation unproved: {root.refusal}")
    generation = sha256_bytes(canonical_json(current))
    if expected is not None and generation != expected:
        raise LifecycleError("candidate admission generation changed")
    if current and (current.get("state") != "stopped" or not current.get("tree_token")
            or current.get("tree_verified_empty") != current["tree_token"]
            or ProcessJob.scan(current["tree_token"], set(), {}, timeout=timeout)):
        raise LifecycleError("prior candidate generation unproved: process-tree custody is not proved empty; "
                             "retain custody for reconciliation")
    return generation


def runtime_checks(layout: Layout, key: str, *, deadline: float | None = None) -> dict:
    """Authenticated identity checks; a 200 from /health alone proves nothing."""
    def request(url, **kwargs):
        if deadline is None:
            return http_json(url, **kwargs)
        left = deadline - time.monotonic()
        if left <= 0:
            raise LifecycleError("runtime observation deadline exceeded")
        result = http_json(url, timeout=min(5, left), **kwargs)
        if time.monotonic() >= deadline:
            raise LifecycleError("runtime observation deadline exceeded")
        return result
    p = layout.profile.data
    url = base_url(layout)
    problems = []
    st, health = request(url + "/health")
    if st != 200 or not isinstance(health, dict):
        return {"ready": False, "problems": [f"/health {st}"]}
    if health.get("api_key") is not True:
        problems.append("server reports authentication disabled")
    if health.get("model") != p["strata"]["model_name"]:
        problems.append(f"/health model {health.get('model')!r}")
    if health.get("max_context") != p["strata"]["setup_args"]["context"]:
        problems.append(f"/health max_context {health.get('max_context')}")
    if health.get("loaded") is False:                      # reported since v0.1.30: unloaded (idle unload) or died
        problems.append("/health reports the engine not loaded")
    deepseek = dsv41.is_pinned(p)
    if deepseek and any(health.get(k) != v for k, v in
                       (("loaded", True), ("status", "ok"), ("service", "strata"), ("images", False))):
        problems.append("/health does not confirm the loaded text-only DeepSeek service")
    st_anon, _ = request(url + "/v1/models")
    if st_anon != 401:
        problems.append(f"unauthenticated /v1/models returned {st_anon}, expected 401")
    st, models = request(url + "/v1/models", key=key)
    ids = [m.get("id") for m in (models or {}).get("data", [])] if isinstance(models, dict) else []
    if st != 200 or ids != [p["strata"]["model_name"]]:
        problems.append(f"/v1/models {st} {ids}")
    st, props = request(url + "/props", key=key)
    props = props if isinstance(props, dict) else {}
    n_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
    if st != 200 or n_ctx != p["strata"]["setup_args"]["context"]:
        problems.append(f"/props {st} n_ctx={n_ctx}")
    build = props.get("build_info")
    if (build or deepseek) and build not in runtime_build_labels(p["strata"]):
        problems.append(f"/props build_info {build!r}")
    model_path = props.get("model_path")
    native = nvfp4.is_local(p["model"])
    expected_path = (dsv41.pack_dir(layout) if deepseek else nvfp4.engine_paths(layout)["--native"] if native
                     else layout.model_file(p["model"]["files"][0])).resolve()
    if (native or deepseek) and (not isinstance(model_path, str) or not model_path.strip()):
        problems.append("/props model_path is missing or invalid")
    elif model_path and Path(model_path).resolve() != expected_path:
        problems.append("/props model_path is not the pinned DeepSeek pack" if deepseek else
                        "/props model_path is not the pinned prepared dense GGUF" if native
                        else "/props model_path is not the pinned first shard")
    st, shared = request(url + "/settings", key=key)
    if st != 200 or shared != {"shared": False, "defaults": {}}:
        problems.append(f"/settings {st}: shared settings are not the frozen empty defaults")
    return {"ready": not problems, "problems": problems, "health": health, "build_info": build,
            "modalities": props.get("modalities"), "n_ctx": n_ctx}


def _check_pipeline_windows(layout: Layout) -> None:
    """Require stock's decode-capable ON line in this start's engine-log interval, never an older generation's."""
    run = read_json(layout.run_record)
    try:
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.pipeline_windows: {exc}") from exc
    on = re.compile(r"strata serve: --pipeline-windows 2: two verifiers per stage, \d+ stages overlap across windows"
                    r" \(decode too; the GDN (?:snapshots beside the window|snapshot on the critical path)\)")
    observed = None
    for line in text.splitlines():
        if line.startswith("strata generate: --pipeline-windows 2 is off:"):
            raise LifecycleError(f"strata.pipeline_windows: {line}")
        if line.startswith("strata serve: --pipeline-windows 2:"):
            if not on.fullmatch(line):
                raise LifecycleError(f"strata.pipeline_windows: decode-capable pipeline not confirmed: {line}")
            observed = line
    if observed is None:
        raise LifecycleError("strata.pipeline_windows: decode-capable ON line absent from this start's engine-log interval")
    run["pipeline_windows"] = {"log_line": observed, "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


def _check_ple_io(layout: Layout) -> None:
    """Refuse a conflicting residency-policy choice in this start, without guessing a positive direct-read line."""
    try:
        run = read_json(layout.run_record)
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.ple_io: {exc}") from exc
    for choice in re.finditer(r"--ple-io (\S+) chosen by the residency policy", text):
        mode = choice.group(1)
        if mode != "direct":
            raise LifecycleError(f"strata.ple_io: residency policy chose {mode!r}, expected 'direct'")
    observed = None
    for probe in re.finditer(r"PLE direct read probe: \d+ rows/s \([a-z]+\)", text):
        observed = probe.group(0)
    run["ple_io"] = {"direct_read_probe": observed, "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


def _check_batch_mtp(layout: Layout) -> None:
    """Require stock's slot-drafter ON line in this start, refusing every explicit off line."""
    try:
        run = read_json(layout.run_record)
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.batch_mtp: {exc}") from exc
    # engine 0.1.54 (src/program/generate.cpp ~6300): "--batch-mtp: 4 slot drafters on CUDA0 (50 MiB of private K/V state
    # and buffers each, sharing the solo drafter's weights); 83.57 GiB free there"
    on = re.compile(r"strata generate: --batch-mtp: \d+ slot drafters on CUDA\d+ \([^\r\n]*\); [0-9.]+ GiB free there")
    observed = None
    for line in text.splitlines():
        if line.startswith("strata generate: WARNING: --batch-mtp is off:"):
            raise LifecycleError(f"strata.batch_mtp: {line}")
        if on.fullmatch(line):
            observed = line
    if observed is None:
        raise LifecycleError("strata.batch_mtp: ON line absent from this start's engine-log interval")
    run["batch_mtp"] = {"log_line": observed, "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


# Stock v0.2.10 strata_control/drafting.py:414-431; unchanged MTP notes at v0.2.11 c3b3f503.
# SHORT_OF_VRAM is an off note (already refused), never an admitted MTP reason.
MTP_START_LINES = frozenset(f"[strata] Drafting: MTP ({reason})" for reason in (
    "DFlash2 didn't fit", "DFlash2 isn't available in this mode", "DFlash2 is for Qwen3.8-Flash-Next only",
    "the DFlash2 drafter isn't downloaded yet", "DFlash2 isn't available on this graphics card",
    "the MTP drafter isn't downloaded yet", "no drafter is downloaded yet",
))
DRAFTING_REFUSALS = (
    # v0.2.10 serve/server.py:3517-3519, 3538; v0.2.11 also uses off for its no-drafter retry.
    "[strata] drafting: DFlash2", "[strata] Drafting: DFlash2", "[strata] Drafting: off",
    "DFlash2 didn't start", '"mtp": false',
    # Engine build 06698c674, src/program/generate.cpp:11172, 19717.
    "strata serve: DFlash2 drafter on", "strata generate: DFlash2 drafter on",
)
START_FALLBACK_LINES_0_1_56 = {
    # v0.2.10 strata_control/vram_fit.py:91 (NOTE_SLOW), printed by serve/server.py:3528-3529.
    "vram_fit": "short of GPU memory: more is read from RAM and the SSD, expect it to be slower",
    # Engine build 06698c674, src/program/generate.cpp:7323-7325 (#4846).
    "arena_ram": "strata generate: not enough RAM for the expert arena (",
    # Same source:6736-6737, the fixed suffix after the measured memory sizes.
    "mtp_dropped": "this start runs without the draft layer (decode is slower; STRATA_MTP_KEEP=1 keeps it)",
    # Same source:7609-7610, the fixed suffix after the loan's slot count.
    "small_cache_loan": "prompts are read in smaller chunks, expect them to be slower",
    # Same source:7699-7700, the fixed prefix before the output-head size.
    "host_output_head": "strata generate: short of GPU memory: the cache had no room, so the output head (",
}
# Stock v0.2.11 c3b3f503: generate.cpp:8499,7071,6526; server.py:1284; mmq_kq_loader.cpp:67.
# All 17 short-memory literals (16 in generate.cpp, one in native_head.cpp) describe degraded walk steps.
START_FALLBACK_LINES_0_1_57 = START_FALLBACK_LINES_0_1_56 | {
    "split_host_output_head": ": the cache would have no room, so the output head (",
    "drafter_dropped": "this start runs without a drafter (decode is slower; STRATA_MTP_KEEP=1 keeps it)",
    "kv_window": "strata generate: short of GPU memory: the KV window is ",
    "nodraft_retry": "the engine ended before it was ready because a card was short of memory",
    "kquant_kernels_missing": "strata: K-quant prompt kernels (STRATA_MMQ_KQ=1): ",
    "spill_walk": "strata generate: short of GPU memory: ",
}
START_FALLBACK_LINES = {(0, 1, 56): START_FALLBACK_LINES_0_1_56, (0, 1, 57): START_FALLBACK_LINES_0_1_57}


def start_fallback_lines(engine_version: str) -> dict[str, str]:
    """Select the engine's reviewed diagnostics without changing qualified rollback checks."""
    version = release_version(engine_version)
    for since in sorted(START_FALLBACK_LINES, reverse=True):
        if version is not None and version >= since:
            return START_FALLBACK_LINES[since]
    return {}


# Stock v0.2.13 serve/server.py:3812; drafting.py:759-779,1151-1159 owns card window/confidence.
DFLASH2_SERVER_ON = re.compile(
    r"\[strata\] drafting: DFlash2 alone \(--draft dflash2, --draft-conf (?P<confidence>"
    + "|".join(re.escape(value) for value in dflash2.DRAFT_CONF_VALUES) + r")\)")
# Stock v0.2.13 src/program/generate.cpp:11780-11783 (serve, no MTP fallback).
DFLASH2_ENGINE_ON = re.compile(
    r"strata serve: DFlash2 drafter on \((?P<pack>.+), graphs captured in \d+ ms\); "
    r"windows up to (?P<window>\d+) tokens; no MTP layer is loaded \(--draft-fallback none\)"
    r"(?:; layer split: the drafter is on CUDA(?P<stage>\d+) \(last stage\), "
    r"the other stages' taps are gathered onto it)?")
# Same release src/core/dflash2.cpp:400-401.
DFLASH2_SELECTOR_ON = "strata dflash2: selector codebooks: Q4_0 rows (about 174 MiB less than bf16)"
# Stock v0.2.13 src/program/generate.cpp:7264-7266,11800.
BATCH_DF2_ON = re.compile(
    r"strata generate: STRATA_BATCH_DF2: (?P<n>\d+) slot drafters on CUDA(?P<dev>\d+) "
    r"\((?P<mib>\d+) MiB of private K/V ring and buffers each, sharing the solo drafter's pack\); "
    r"\d+\.\d{2} GiB free there")
BATCH_DF2_READY = re.compile(
    r"strata serve: STRATA_BATCH_DF2: (?P<n>\d+) slot drafters ready "
    r"\(batch windows carry each slot's token and its spare-row drafts\)")
# Same source:7256,11796,11798: clone allocation, binding or graph preparation failed.
BATCH_DF2_SLOT_FAILURE = re.compile(r"STRATA_BATCH_DF2: slot \d+")
DFLASH2_REFUSALS = (
    "[strata] Drafting:", "DFlash2 didn't start", '"mtp": false',
    # v0.2.10 serve/server.py:1225-1226; 06698c674 generate.cpp:11161-11165,19717-19721.
    "the engine ended before it was ready with the DFlash2 drafter",
    "strata serve: --draft dflash2:", "--draft-fallback none: no MTP is loaded, so the start ends here",
    "strata generate: DFlash2 drafter on", "DFlash2 did not start and no MTP is loaded",
    # v0.2.13 generate.cpp:6893,7268,11802.
    "STRATA_BATCH_DF2 is off", "STRATA_BATCH_DF2 (the slots' DFlash2 drafts) is off",
)


def _dflash2_start(layout, server_text, engine_text):
    for text in (server_text, engine_text):
        for line in text.splitlines():
            if any(marker in line for marker in DFLASH2_REFUSALS) or BATCH_DF2_SLOT_FAILURE.search(line):
                raise ValueError(line)
    server_lines = [line for line in server_text.splitlines() if "[strata] drafting:" in line]
    if len(server_lines) != 1 or (server := DFLASH2_SERVER_ON.fullmatch(server_lines[0])) is None:
        raise ValueError("exactly one stock DFlash2 server ON line required")
    engine_lines = [line for line in engine_text.splitlines() if "DFlash2 drafter on" in line]
    if len(engine_lines) != 1 or (engine := DFLASH2_ENGINE_ON.fullmatch(engine_lines[0])) is None:
        raise ValueError("exactly one stock DFlash2 serve ON line without MTP required")
    if ("DFlash2 drafter on" in server_text or "[strata] drafting:" in engine_text):
        raise ValueError("DFlash2 ON evidence is in the wrong output stream")
    pin = layout.profile.data["model"]["dflash2_source"]
    runtime = dflash2.runtime_file(pin)
    pack = layout.dflash2_dir / runtime["file"]
    actual = Path(engine["pack"])
    if not actual.is_absolute():
        actual = layout.strata / actual
    if actual.resolve() != pack.resolve():
        raise ValueError("DFlash2 runtime pack path differs from the profile")
    profile = layout.profile
    host, strata = profile.data["host"], profile.data["strata"]
    arch = None if profile.multi_gpu else GPU_MODEL_ARCH.get(host.get("gpu_model"))
    big_blackwell = (not profile.multi_gpu and arch == "120"
                     and host["min_gpu_vram_mib"] * 1024**2 >= 48_000_000_000)
    wide = (release_version(strata["engine_version"]) or ()) >= dflash2.BIG_BLACKWELL_SINCE and big_blackwell
    allowed = dflash2.expected_draft_confs(profile.data)
    if server["confidence"] not in allowed:
        raise ValueError(f"DFlash2 --draft-conf {server['confidence']} differs from the "
                         f"profile-specific --draft-conf choices {sorted(allowed)}")
    if layout.profile.multi_gpu:
        if engine["stage"] != str(len(layout.profile.gpu_indices) - 1):
            raise ValueError("DFlash2 must draft on the last CUDA stage")
    elif engine["stage"] is not None:
        raise ValueError("DFlash2 named a layer split on a single-card profile")
    # Prompt lookup widens six to eight before the engine's per-card cap. The split has no sm_120 cap.
    window = 6 if not profile.multi_gpu and arch == "120" and not wide else 8
    if int(engine["window"]) != window:
        raise ValueError(f"DFlash2 must report stock's profile-specific window of {window} tokens")
    selector = [line for line in engine_text.splitlines() if "selector codebooks:" in line]
    wanted = [DFLASH2_SELECTOR_ON] if pin["runtime_pack"] == "selq4" else []
    if selector != wanted or "selector codebooks:" in server_text:
        raise ValueError("DFlash2 selector ON evidence differs from the runtime_pack pin")
    starts = [line for line in engine_text.splitlines() if line.startswith("[strata] ") and " engine started: " in line]
    if len(starts) != 1:
        raise ValueError("exactly one engine generation required for a DFlash2 start")
    observation = {"mode": "dflash2", "server_line": server_lines[0], "engine_line": engine_lines[0],
                   "draft_conf": server["confidence"],
                   "draft_conf_source": "profile" if "drafting_args" in strata else "stock",
                   "selector_line": selector[0] if selector else None, "window_tokens": int(engine["window"]),
                   "pack": pack.resolve().relative_to(layout.root.resolve()).as_posix(), "pack_sha256": runtime["sha256"],
                   "pack_kind": "tuned" if dflash2.is_tuned(pin) else "standard"}
    if "STRATA_BATCH_DF2:" in server_text:
        raise ValueError("DFlash2 slot evidence is in the wrong output stream")
    slot_lines = [line for line in engine_text.splitlines() if "STRATA_BATCH_DF2:" in line]
    parallel = layout.profile.data["strata"]["setup_args"].get("parallel")
    if parallel is not None:
        on = [match for line in slot_lines if (match := BATCH_DF2_ON.fullmatch(line)) is not None]
        ready = [match for line in slot_lines if (match := BATCH_DF2_READY.fullmatch(line)) is not None]
        if len(slot_lines) != 2 or len(on) != 1 or len(ready) != 1:
            raise ValueError("exactly one stock DFlash2 slot ON line and READY line required")
        if int(on[0]["n"]) != parallel or int(ready[0]["n"]) != parallel:
            raise ValueError("DFlash2 slot drafter counts differ from setup_args.parallel")
        observation["slot_drafters"] = {"count": parallel, "cuda": int(on[0]["dev"]), "mib_each": int(on[0]["mib"]),
                                        "on_line": on[0][0], "ready_line": ready[0][0]}
    elif slot_lines:
        raise ValueError("DFlash2 slot lines on a profile without batch slots")
    return observation


def _check_dsv41_start(layout: Layout) -> None:
    try:
        run = read_json(layout.run_record)
        server_text, server_interval = _startup_log_interval(layout, run, "log", layout.logs)
        engine_text, engine_interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        observation = dsv41.start_evidence(server_text, engine_text)
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"stock DeepSeek start: {exc}") from exc
    run["dsv41_start"] = {**observation, "log_interval": server_interval, "engine_log_interval": engine_interval}
    atomic_write_json(layout.run_record, run)


def _check_drafting(layout: Layout) -> None:
    """Require the pinned drafter for one owned start interval; stock Auto must stay on MTP."""
    try:
        run = read_json(layout.run_record)
        server_text, server_interval = _startup_log_interval(layout, run, "log", layout.logs)
        engine_text, engine_interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        if dflash2.is_pinned(layout.profile.data):
            observation = _dflash2_start(layout, server_text, engine_text)
            run["drafting"] = {**observation, "log_interval": server_interval, "engine_log_interval": engine_interval}
            atomic_write_json(layout.run_record, run)
            return
        observed = None
        for text in (server_text, engine_text):
            for line in text.splitlines():
                if any(marker in line for marker in DRAFTING_REFUSALS):
                    raise ValueError(line)
                if "[strata] Drafting:" in line:
                    if line not in MTP_START_LINES or observed is not None:
                        raise ValueError("unknown or repeated stock drafting note: " + line)
                    observed = line
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"stock drafting: {exc}") from exc
    run["drafting"] = {"mode": "mtp", "server_line": observed,
                        "log_interval": server_interval, "engine_log_interval": engine_interval}
    atomic_write_json(layout.run_record, run)


def _check_start_fallbacks(layout: Layout) -> None:
    """Refuse stock's slower RAM/VRAM start alternatives in either output stream of this launch."""
    try:
        run = read_json(layout.run_record)
        server_text, server_interval = _startup_log_interval(layout, run, "log", layout.logs)
        engine_text, engine_interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        engine_version = layout.profile.data["strata"]["engine_version"]
        markers = start_fallback_lines(engine_version)
        for text in (server_text, engine_text):
            for line in text.splitlines():
                if any(marker in line for marker in markers.values()):
                    raise ValueError(line)
        version = release_version(engine_version)
        new_path = version is not None and version >= (0, 1, 57)
        generations = sum(line.startswith("[strata] ") and " engine started: " in line
                          for line in engine_text.splitlines())
        if new_path and generations > 1:
            raise ValueError("multiple engine generations")
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"stock start fallback: {exc}") from exc
    run["start_fallbacks"] = {"checked": list(markers),
                              **({"generations": generations} if new_path else {}),
                              "log_interval": server_interval, "engine_log_interval": engine_interval}
    atomic_write_json(layout.run_record, run)


def _record_prefill_ceiling(layout: Layout) -> None:
    """Observe stock's bare-auto NVIDIA ceiling/RAM-guard lines, never gate on their presence or values."""
    strata = layout.profile.data["strata"]
    version = release_version(strata["engine_version"])
    if (version is None or version < (0, 1, 57)
            or flag_pairs(strata["expected_engine_flags"]).get("--prefill") != "auto"):
        return
    run = read_json(layout.run_record)
    text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
    run["prefill_ceiling"] = {"lines": [line for line in text.splitlines()
                                       if line.startswith("strata generate: NVIDIA: ")],
                              "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


def _check_trim_stage_weights(layout: Layout) -> None:
    """Require exactly one dense-weight range per stage, matching this start's manual layer split."""
    try:
        run = read_json(layout.run_record)
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        ignored = "strata generate: --trim-stage-weights needs a layer split across GPUs (ignored)"
        if ignored in text.splitlines():
            raise ValueError(ignored)
        boundaries = _layer_boundaries(text, list(layout.profile.gpu_indices))
        split = int(layout.profile.data["strata"]["setup_args"]["layer_split"])
        expected = [(0, split - 1), (split, boundaries[-1]["last_layer"])]
        if [(row["first_layer"], row["last_layer"]) for row in boundaries] != expected:
            raise ValueError(f"engine layer boundaries differ from the pinned manual split {split}")
        dense = re.compile(r"strata generate: layer split: CUDA(\d+) loads the dense weights of layers (\d+)-(\d+) only")
        lines, ranges = {}, {}
        for line in text.splitlines():
            if line.startswith("strata generate: layer split: CUDA") and "loads the dense weights" in line:
                match = dense.fullmatch(line)
                if match is None:
                    raise ValueError("unknown dense-weight layer-range syntax")
                index = int(match[1])
                if index in ranges:
                    raise ValueError(f"more than one dense-weight line for CUDA{index}")
                lines[index], ranges[index] = line, (int(match[2]), int(match[3]))
        if ranges != dict(enumerate(expected)):
            raise ValueError(f"dense-weight layer ranges do not match the pinned manual split {split}: {ranges}")
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.trim_stage_weights: {exc}") from exc
    run["trim_stage_weights"] = {"log_lines": [lines[i] for i in range(len(expected))],
                                  "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


def _check_engine_env(layout: Layout) -> None:
    """Re-prove config delivery and each group's reviewed evidence in this start's engine-log interval."""
    try:
        run = read_json(layout.run_record)
        strata = layout.profile.data["strata"]
        groups = engine_env_groups(strata["engine_env"])
        if groups is None:
            raise ValueError("engine_env is not a union of complete reviewed stock groups")
        env = engine_env_union(strata)
        if read_json(layout.strata_config).get("env") != env:
            raise ValueError("config env != the profile's pinned setup_env and engine_env union")
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        lines = text.splitlines()
        group_evidence = {}
        for group in sorted(groups):
            evidence = ENGINE_ENV_GROUP_EVIDENCE.get(group)
            if evidence is None:
                group_evidence[group] = {"proof": "delivery"}
                continue
            for line in lines:
                if any(marker in line for marker in evidence.get("refuse", ())):
                    raise ValueError(f"{group}: {line}")
            observed_lines = []
            for pattern in evidence.get("on", ()):
                matches = [line for line in lines if pattern.fullmatch(line)]
                if len(matches) != 1:
                    raise ValueError(f"{group}: expected exactly one engine-log line matching {pattern.pattern!r}")
                observed_lines.extend(matches)
            group_evidence[group] = {"lines": observed_lines, "cite": evidence["cite"]}
        observed = None
        if "STRATA_BATCH_SELF_COMMIT" in env:
            for line in lines:
                if line.startswith("strata verify: batch windows of up to "):
                    if not SELF_COMMIT_LINE.fullmatch(line):
                        raise ValueError("batch self-commit not confirmed: " + line)
                    observed = line
            if observed is None:
                raise ValueError("batch self-commit line absent from this start's engine-log interval")
        server_sha = sha256_file(layout.strata / "serve/server.py")
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.engine_env: {exc}") from exc
    run["engine_env"] = {"config_env_sha256": sha256_bytes(canonical_json(env)), "names": sorted(env),
                         "server_source_sha256": server_sha, "batch_self_commit_line": observed,
                         "engine_log_interval": interval, "groups": sorted(groups),
                         "group_evidence": group_evidence}
    atomic_write_json(layout.run_record, run)


def _check_kv_streaming_off(layout: Layout) -> None:
    """Stock emits a streaming line only for streamed KV; non-streaming has no positive startup line."""
    try:
        run = read_json(layout.run_record)
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        if KV_STREAMING_LINE.search(text):
            raise ValueError("KV streaming line present despite the off pin")
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.setup_args.kv_streaming: {exc}") from exc
    run["kv_streaming"] = {"mode": "off", "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


def _check_kv_grow(layout: Layout) -> None:
    """Require the engine's elastic-K/V ON line in this start, never an earlier generation."""
    try:
        run = read_json(layout.run_record)
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        observed = None
        for line in text.splitlines():
            if line.startswith("strata generate: elastic K/V:"):
                if not KV_GROW_LINE.fullmatch(line):
                    raise ValueError("unknown elastic K/V startup line: " + line)
                observed = line
        if observed is None:
            raise ValueError("elastic K/V line absent from this start's engine-log interval")
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.kv_grow: {exc}") from exc
    run["kv_grow"] = {"log_line": observed, "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


def start(layout: Layout, *, tool_argv: list[str], log: Log, timeout: int | None = None,
          expected_idle_generation: str | None = None) -> dict:
    p = layout.profile.data
    srv = p["server"]
    experimental = bool(os.environ.get(EXPERIMENT_LAUNCH_ENV))
    if experimental and (not WINDOWS or layout.profile.multi_gpu
            or os.environ.get(TREE_TOKEN_ENV) != os.environ[EXPERIMENT_LAUNCH_ENV]
            or expected_idle_generation is None):
        raise LifecycleError("candidate start requires its controller-reserved native job")
    with FileLock(layout.lock_file):
        if expected_idle_generation is not None:
            idle_generation(layout, expected=expected_idle_generation)
        root = verdict(layout)
        if not root.idle:
            raise LifecycleError(root.refusal)
        rec = verify_install_fast(layout)
        if dflash2.is_pinned(p) and dflash2.tuned_aware(p["strata"]["engine_version"]):
            try:
                dflash2.check_folder(layout.dflash2_dir, p["model"]["dflash2_source"])
            except IntegrityError as exc:
                raise LifecycleError(f"stock DFlash2 folder: {exc}") from exc
        key = read_key(layout)
        if experimental:
            # Physical GPU readiness belongs to the controller's reservation receipt.
            # Never inspect unrelated GPU processes on this candidate-only path.
            pass
        elif layout.profile.multi_gpu:
            cards = card_observations(layout.profile)
            problems = [f"GPU {card['gpu_index']}: {problem}" for card in cards for problem in card["problems"]]
            if problems:
                raise LifecycleError("; ".join(problems))
        else:
            gpu = gpu_facts(p["host"]["gpu_index"])
            busy = gpu_busy(gpu, bool(p["host"].get("display_attached", False)))
            if busy:
                raise LifecycleError(f"GPU {p['host']['gpu_index']} is in use ({busy}); its owner must release it first")
        mem = procs.memory()
        need = p["host"]["min_available_ram_gib_at_start"] * (1 << 30)
        if mem["available"] and mem["available"] < need:
            raise LifecycleError(f"only {mem['available'] / (1 << 30):.1f} GiB RAM available; the profile needs "
                                 f"{p['host']['min_available_ram_gib_at_start']} GiB at start")
        if layout.profile.pins_runtime_dir:
            layout.strata_runtime.mkdir(parents=True, exist_ok=True)
            layout.localappdata.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        log_path = layout.logs / f"server-{stamp}.log"
        capture = {}
        # Every start-time engine-log check must capture the new interval before launch.
        if (layout.profile.multi_gpu or any(field in p["strata"] for field in ("ple_io", "batch_mtp", "engine_env", "kv_grow", "drafting"))
                or p["strata"]["setup_args"].get("kv_streaming") == "off" or layout.profile.start_path_reviewed):
            engine_log = _engine_log_path(layout)
            capture = {"log_start_offset": log_path.stat().st_size if log_path.exists() else 0,
                       "engine_log": engine_log.relative_to(layout.root.resolve()).as_posix(),
                       "engine_log_start_offset": engine_log.stat().st_size if engine_log.exists() else 0}
        launch_id = secrets.token_hex(16)
        # The launcher's own identity lets a later reader tell a pending launch from one whose start was killed.
        launcher = procs.info(os.getpid())
        atomic_write_json(layout.run_record, {
            "schema_version": 1, "profile_id": layout.profile.id, "profile_fingerprint": layout.profile.fingerprint,
            "runtime_identity_sha256": rec["runtime_identity_sha256"], "port": srv["port"],
            "requested_utc": utc_now(), "state": "launching", "launch_id": launch_id,
            **({"launcher": launcher.as_dict()} if launcher is not None else {}),
            "log": log_path.relative_to(layout.root).as_posix(),
            **({"experiment_launch_id": os.environ[EXPERIMENT_LAUNCH_ENV]} if os.environ.get(EXPERIMENT_LAUNCH_ENV) else {}),
            **({"tree_token": os.environ[EXPERIMENT_LAUNCH_ENV]}
               if WINDOWS and os.environ.get(EXPERIMENT_LAUNCH_ENV) else {}),
            **capture})
        argv = [*tool_argv, "serve", "--profile", str(layout.profile.path.resolve()), "--root", str(layout.root),
                "--log", str(log_path), "--launch-id", launch_id]
        t0 = time.monotonic()
    # The detached wrapper must take this lock to verify its bound request before creating a server.
    try:
        _launch_detached(argv, cwd=layout.root, log=layout.logs / f"serve-{stamp}.log",
                         job_token=os.environ.get(EXPERIMENT_LAUNCH_ENV) if WINDOWS else None)
        return _finish_start(layout, launch_id=launch_id, key=key, t0=t0, timeout=timeout, log=log)
    except (Exception, KeyboardInterrupt):
        # Every dispatch/readiness/publication failure converges here, including
        # malformed nested HTTP JSON. Never clean up a replacement generation.
        with FileLock(layout.lock_file, timeout=120):
            current = read_json(layout.run_record)
            if current.get("launch_id") == launch_id:
                stop(layout, log=log, locked=True)
        raise


def owned_job_processes(job, timeout):
    """Resolve only native job members; no Toolhelp parent/descendant census."""
    rows = job.enumerate_tree(timeout=timeout)
    members = job.pids()
    result = {}
    for pid in members:
        row = rows.get(pid)
        if row is None:
            raise LifecycleError("readiness job membership changed during observation")
        proc = procs.info(pid, ppid=row["ParentProcessId"])
        if proc is not None:
            result[pid] = proc
    if job.pids() != members:
        raise LifecycleError("readiness job membership changed during observation")
    return result


def _finish_start(layout: Layout, *, launch_id: str, key: str, t0: float,
                  timeout: int | None, log: Log) -> dict:
    p = layout.profile.data
    srv = p["server"]
    deadline = t0 + (timeout or srv["ready_timeout_s"])
    experiment_token = read_json(layout.run_record).get("experiment_launch_id")
    def processes(run):
        if not experiment_token:
            server = procs.matches(run.get("server"))
            return server, procs.descendants(server.pid) if server else []
        token = run.get("tree_token")
        if token != experiment_token or run.get("experiment_launch_id") != experiment_token:
            raise LifecycleError("readiness candidate job identity changed")
        job = ProcessJob(token, existing=True)
        try:
            owned = owned_job_processes(job, deadline - time.monotonic())
        finally:
            job.close()
        recorded = run.get("server") or {}
        server = owned.get(recorded.get("pid"))
        if server and (server.created != recorded.get("created")
                       or server.exe.lower() != recorded.get("exe", "").lower()):
            server = None
        return server, [p for pid, p in owned.items() if pid != recorded.get("pid")]
    result: dict = {"ready": False, "problems": ["not started"]}
    while time.monotonic() < deadline:
        time.sleep(2)
        run = read_json(layout.run_record)
        if run.get("launch_id") != launch_id:
            raise LifecycleError("start generation changed during readiness")
        if run.get("state") in ("exited", "stopped", "stop_incomplete"):
            break
        if not run.get("server"):
            continue
        if processes(run)[0] is None:
            break
        result = runtime_checks(layout, key, deadline=deadline)
        if result["ready"]:
            break
    with FileLock(layout.lock_file, timeout=120):
        run = read_json(layout.run_record)
        if run.get("launch_id") != launch_id:
            raise LifecycleError("start generation changed before readiness publication")
        server, tree = processes(run)
        if not result.get("ready") or server is None or run.get("state") not in ("starting", "ready"):
            log("readiness failed: " + "; ".join(result.get("problems", ["server exited"])))
            raise LifecycleError("Strata did not become ready: " + "; ".join(result.get("problems", ["exited"])))
        engines = [e for e in tree if Path(e.exe).name.lower().startswith("strata")]
        if experiment_token and len(engines) != 1:
            raise LifecycleError("owned candidate engine identity unavailable after readiness")
        engine = engines[0] if engines else None
        run.update({"state": "ready", "ready_utc": utc_now(), "ready_s": round(time.monotonic() - t0, 1),
                    "engine": engine.as_dict() if engine else None, "build_info": result.get("build_info"),
                    "server_tree": [p.as_dict() for p in tree]})
        atomic_write_json(layout.run_record, run)
        if layout.profile.multi_gpu:
            cards = card_observations(layout.profile, owned_pids={server.pid, *(p.pid for p in tree)})
            problems = [f"GPU {card['gpu_index']}: {problem}" for card in cards for problem in card["problems"]]
            if engine is None:
                problems.append("owned engine identity unavailable after readiness")
            if problems:
                raise LifecycleError("GPU ownership changed during launch: " + "; ".join(problems))
        stage = capture_startup_gpu_order(layout) if layout.profile.multi_gpu else None
        if "pipeline_windows" in p["strata"]:
            _check_pipeline_windows(layout)
        if "ple_io" in p["strata"]:
            _check_ple_io(layout)
        if "batch_mtp" in p["strata"]:
            _check_batch_mtp(layout)
        if layout.profile.start_path_reviewed:
            if dsv41.is_pinned(p):
                _check_dsv41_start(layout)
            else:
                _check_drafting(layout)
                _check_start_fallbacks(layout)
                _record_prefill_ceiling(layout)
        if "trim_stage_weights" in p["strata"]:
            _check_trim_stage_weights(layout)
        if "engine_env" in p["strata"]:
            _check_engine_env(layout)
        if p["strata"]["setup_args"].get("kv_streaming") == "off":
            _check_kv_streaming_off(layout)
        if "kv_grow" in p["strata"]:
            _check_kv_grow(layout)
        return {"state": "degraded" if stage and not stage["complete"] else "healthy", "ready_s": run["ready_s"], "port": srv["port"],
                "engine_found": engine is not None, "log": run["log"],
                **({"cards": cards, "gpu_stage_order": stage} if layout.profile.multi_gpu else {})}


# ------------------------------------------------------------------------------------------------ status / stop
def status(layout: Layout) -> dict:
    root = verdict(layout)
    if root.row != "server-live" or root.state != "healthy":
        report = {"state": root.state, **({"problems": root.problems} if root.problems else {}), **root.details}
        if root.state in ("stopped", "failed") and layout.profile.multi_gpu:
            report["cards"] = card_observations(layout.profile)
        return report
    run, live = root.run, root.live
    try:
        key = read_key(layout)
    except LifecycleError as exc:
        return {"state": "degraded", "problems": [str(exc)]}
    checks = runtime_checks(layout, key)
    problems = list(checks.get("problems", []))
    server = live["server"]
    tree = procs.descendants(server.pid)
    if run.get("engine") and not any(Path(p.exe).name.lower().startswith("strata") for p in tree):
        problems.append("no engine process under the server (stock Strata restarts it on the next request)")
    stray = {role: p for role, p in live.items() if role.startswith("unrecorded[")}
    if stray:
        problems.append(f"processes of this root outside its recorded trees ({_describe(stray)}); {_stop_advice(run)}")
    extra = {}
    if layout.profile.multi_gpu:
        cards = card_observations(layout.profile, owned_pids={server.pid, *(p.pid for p in tree)})
        problems.extend(f"GPU {card['gpu_index']}: {problem}" for card in cards for problem in card["problems"])
        stage = dict(run.get("gpu_stage_order") or {})
        current_engines = [p for p in tree if Path(p.exe).name.lower().startswith("strata")]
        if (not stage.get("complete") or len(current_engines) != 1
                or current_engines[0].as_dict() != stage.get("engine_identity")):
            stage.update(complete=False, staged=None, event="unavailable",
                         reason="startup stage order unavailable for current engine generation")
            problems.append(stage["reason"])
        extra = {"cards": cards, "gpu_stage_order": stage}
    state = "healthy" if not problems else "degraded"
    return {"state": state, "problems": problems, "live": sorted(live), "ready_s": run.get("ready_s"),
            "started_utc": run.get("ready_utc"), **extra}






def stop(layout: Layout, *, log: Log, locked: bool = False, job: ProcessJob | None = None) -> dict:
    def _stop() -> dict:
        if not layout.run_record.exists():
            extra = {"cards": card_observations(layout.profile), "owned_gpus_released": None} if layout.profile.multi_gpu else {}
            return {"state": "stopped", "stopped": [], **extra}
        run = read_json(layout.run_record)
        custody_refusal = _stop_custody_refusal(run)
        if custody_refusal:
            raise LifecycleError(custody_refusal)
        tree_stopped = False
        if (run.get("tree_token") and run.get("state") == "stopped"
                and run.get("tree_verified_empty") == run["tree_token"]):
            if not WINDOWS or ProcessJob.scan(run["tree_token"], set(), {}):
                raise LifecycleError("stopped process-tree verification unavailable or surviving")
            tree_stopped = True
        if run.get("tree_token") and not tree_stopped:
            run["state"] = "stop_incomplete"  # Fence every delayed wrapper before native effects.
            atomic_write_json(layout.run_record, run)
            try:
                owned_job = job or ProcessJob(run["tree_token"], existing=True)
            except MissingProcessJob:
                # Windows destroys a kill-on-close job after its last handle and
                # associated processes are gone. ERROR_ACCESS_DENIED is not this
                # proof. Independently reject marked or recorded survivors.
                recorded = [run.get(role) for role in ("wrapper", "server", "engine")]
                recorded += run.get("server_tree", [])
                if (not WINDOWS or any(procs.matches(identity) for identity in recorded)
                        or ProcessJob.scan(run["tree_token"], set(), {})):
                    raise LifecycleError("destroyed job still has survivors or unavailable verification")
            else:
                if owned_job.token != run["tree_token"]:
                    raise LifecycleError("process-tree generation changed")
                try:
                    owned_job.stop(layout.profile.data["server"]["stop_timeout_s"])
                except BaseException:
                    if job is None:
                        owned_job.close()
                    raise
            tree_stopped = True
        timeout = layout.profile.data["server"]["stop_timeout_s"]
        stopped, refused = [], []
        # Owned roots are the recorded wrapper and server (identity-verified). Their CURRENT descendants are owned
        # too (the real interpreter behind the venv redirector, and any engine the server restarted), so each
        # verified root is stopped with its subtree, deepest first; a PID that no longer matches is never touched.
        targets: list[tuple[str, procs.ProcInfo]] = []
        for role in ("server", "wrapper"):
            root = procs.matches(run.get(role))
            if root is None:
                continue
            targets += [(f"{role}-descendant", d) for d in procs.descendants(root.pid)]
            targets.append((role, root))
        for rec in [run.get("engine"), *run.get("server_tree", [])]:
            orphan = procs.matches(rec)
            if orphan is not None and all(orphan.pid != t.pid for _, t in targets):
                targets.insert(0, ("orphan", orphan))
        done: set[int] = set()
        for role, proc in targets:
            if proc.pid in done:
                continue
            done.add(proc.pid)
            try:
                if procs.terminate(proc, timeout):
                    stopped.append(f"{role}:{Path(proc.exe).name}")
                else:
                    refused.append(f"{role} {Path(proc.exe).name} did not exit within {timeout}s")
            except PermissionError as exc:
                refused.append(str(exc))
        run.update({"state": "stopped" if not refused else "stop_incomplete", "stopped_utc": utc_now(),
                    "unpublished_child": False})
        if tree_stopped and not refused:
            run["tree_verified_empty"] = run["tree_token"]
        atomic_write_json(layout.run_record, run)
        srv = layout.profile.data["server"]
        deadline = time.monotonic() + timeout
        while port_in_use(srv["listen_host"], srv["port"]) and time.monotonic() < deadline:
            time.sleep(0.5)
        if refused:
            raise LifecycleError("; ".join(refused))
        extra = {}
        if layout.profile.multi_gpu:
            recorded = {r["pid"] for r in [run.get("engine"), *run.get("server_tree", [])] if r}
            cards = card_observations(layout.profile, owned_pids=done | recorded)
            released = all(card["owned_count"] == 0 for card in cards)
            extra = {"cards": cards, "owned_gpus_released": released}
        return {"state": "stopped", "stopped": stopped, **extra}

    if locked:
        return _stop()
    with FileLock(layout.lock_file):
        return _stop()


def ensure_healthy(layout: Layout) -> str:
    st = status(layout)
    if st["state"] != "healthy":
        raise LifecycleError(f"Strata is {st['state']}: " + "; ".join(st.get("problems", [])))
    return read_key(layout)


def tool_argv() -> list[str]:
    """How to re-invoke this tool (for the detached wrapper): the current interpreter plus scripts/omp_strata.py."""
    flags = ["-I", "-S", "-B"] if os.environ.get(EXPERIMENT_LAUNCH_ENV) else []
    return [sys.executable, *flags, str(Path(__file__).resolve().parent.parent / "scripts" / "omp_strata.py")]



__all__ = ["FileLock", "IDLE_STATES", "InstallError", "LifecycleError", "Verdict", "doctor", "ensure_healthy", "keygen",
           "read_key", "serve", "start", "status", "stop", "tool_argv", "verdict"]
