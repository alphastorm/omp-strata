"""Process identity, enumeration and termination without third-party packages.

An owned process is identified by PID plus creation time plus executable path; a PID alone is never enough to
signal anything (PIDs are reused). Windows uses kernel32 through ctypes; POSIX uses /proc or `ps`.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from enum import Enum

WINDOWS = sys.platform == "win32"


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    ppid: int
    created: str          # opaque, stable creation stamp (Windows FILETIME ticks, POSIX start time)
    exe: str

    def as_dict(self) -> dict:
        return asdict(self)


class TableUnavailable(OSError):
    """The process table could not be read as a whole, so no process may be taken to be absent."""


def _ascii_decimal(value: str) -> bool:
    """Native numeric text contains ASCII decimal digits only, never signs or Unicode numerals."""
    return value.isascii() and value.isdecimal()


class Presence(Enum):
    SAME = "same"
    OTHER = "another-process"
    ABSENT = "not-enumerated"
    UNKNOWN = "cannot-say"


@dataclass(frozen=True)
class ProcessTable:
    """Every enumerated PID is identified or unidentified; only `observe` compares recorded identities.

    A readable creation stamp without a readable executable is unidentified, not a placeholder row and never
    evidence of another process. Its parent edge is conservatively unavailable too. Single-process `matches`
    keeps its existing behavior (it cannot distinguish an unreadable identity from a gone process).
    """
    identified: dict[int, ProcInfo]
    unidentified: set[int]

    def observe(self, recorded: dict) -> Presence:
        """Closed outcomes: same process, another process, not enumerated, or enumerated but cannot say."""
        pid = int(recorded["pid"])
        if pid in self.unidentified:
            return Presence.UNKNOWN
        proc = self.identified.get(pid)
        if proc is None:
            return Presence.ABSENT
        if not proc.created or not proc.exe or not recorded.get("created") or not recorded.get("exe"):
            return Presence.UNKNOWN
        return Presence.SAME if same_identity(proc, recorded) else Presence.OTHER


def _checked_table(identified: dict[int, ProcInfo], unidentified: set[int]) -> ProcessTable:
    if os.getpid() not in identified:
        raise TableUnavailable("process table lacks the reader's own identity")
    return ProcessTable(identified, unidentified)


if WINDOWS:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]  # Windows-only branch
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_TERMINATE = 0x0001
    SYNCHRONIZE = 0x00100000
    TH32CS_SNAPPROCESS = 0x00000002
    ERROR_NO_MORE_FILES = 18

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    _k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                ctypes.POINTER(wintypes.DWORD)]
    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    _k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    _k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    _k32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    STILL_ACTIVE = 259

    def _open(pid: int, access: int):
        h = _k32.OpenProcess(access, False, pid)
        return h or None

    def _snapshot() -> dict[int, tuple[int, str]]:
        snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap in (None, wintypes.HANDLE(-1).value):
            raise TableUnavailable(f"process snapshot failed (error {ctypes.get_last_error()})")
        out: dict[int, tuple[int, str]] = {}
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = _k32.Process32FirstW(snap, ctypes.byref(entry))
            while ok:
                out[int(entry.th32ProcessID)] = (int(entry.th32ParentProcessID), entry.szExeFile)
                ok = _k32.Process32NextW(snap, ctypes.byref(entry))
            error = ctypes.get_last_error()  # Capture the failing First/Next call before CloseHandle.
            if error != ERROR_NO_MORE_FILES:
                raise TableUnavailable(f"process snapshot enumeration failed (error {error})")
        finally:
            _k32.CloseHandle(snap)
        return out

    def _parents() -> dict[int, tuple[int, str]]:
        try:
            return _snapshot()
        except TableUnavailable:
            return {}

    def table() -> ProcessTable:
        """Account for every snapshot PID, with our own identity readable, or raise TableUnavailable.

        Protected or vanished identities are unidentified, not absent. A later readable identity is retained with
        unknown parent (0), never joined to the snapshot's old parent. Backward-adjusted UTC and native Windows
        behavior remain unqualified; tests substitute the native boundaries.
        """
        # Both are UTC system time: time_ns uses the Unix epoch; GetProcessTimes uses 100 ns since 1601.
        # A later-created process may have reused the snapshot's PID and must not inherit its old parent.
        snapshot = _snapshot()
        snapshot_at = time.time_ns() // 100 + 116444736000000000
        out: dict[int, ProcInfo] = {}
        unidentified: set[int] = set()
        for pid, (ppid, _) in snapshot.items():
            proc = info(pid, ppid=ppid)
            if proc is not None and _ascii_decimal(proc.created) and proc.exe:
                out[pid] = (ProcInfo(proc.pid, 0, proc.created, proc.exe)
                            if int(proc.created) > snapshot_at else proc)
            else:
                unidentified.add(pid)
        return _checked_table(out, unidentified)

    def info(pid: int, *, ppid: int | None = None) -> ProcInfo | None:
        h = _open(pid, PROCESS_QUERY_LIMITED_INFORMATION)
        if h is None:
            return None
        try:
            code = wintypes.DWORD()
            if _k32.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != STILL_ACTIVE:
                return None
            ct, et, kt, ut = (wintypes.FILETIME() for _ in range(4))
            if not _k32.GetProcessTimes(h, ctypes.byref(ct), ctypes.byref(et), ctypes.byref(kt), ctypes.byref(ut)):
                return None
            created = str((ct.dwHighDateTime << 32) | ct.dwLowDateTime)
            size = wintypes.DWORD(32768)
            buf = ctypes.create_unicode_buffer(size.value)
            exe = buf.value if _k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)) else ""
        finally:
            _k32.CloseHandle(h)
        if ppid is None:
            ppid = _parents().get(pid, (0, ""))[0]
        return ProcInfo(pid=pid, ppid=ppid, created=created, exe=exe)

    def children(pid: int) -> list[int]:
        return [p for p, (pp, _) in _parents().items() if pp == pid and p != pid]

    def terminate(proc: ProcInfo, timeout: float) -> bool:
        """TerminateProcess after re-checking identity; True when the process is gone."""
        current = info(proc.pid)
        if current is None:
            return True
        if (current.created, current.exe.lower()) != (proc.created, proc.exe.lower()):
            raise PermissionError(f"pid {proc.pid} is now another process; refusing to terminate it")
        h = _open(proc.pid, PROCESS_TERMINATE | SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION)
        if h is None:
            return info(proc.pid) is None
        try:
            _k32.TerminateProcess(h, 1)
            return _k32.WaitForSingleObject(h, int(timeout * 1000)) == 0
        finally:
            _k32.CloseHandle(h)

    def memory() -> dict[str, int]:
        st = MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        _k32.GlobalMemoryStatusEx(ctypes.byref(st))
        return {"total": st.ullTotalPhys, "available": st.ullAvailPhys, "commit_limit": st.ullTotalPageFile,
                "commit_available": st.ullAvailPageFile}

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    _k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                                             wintypes.DWORD]

    def process_memory(pid: int) -> dict[str, int]:
        """Current and lifetime-peak working set and private commit of one process (bytes); {} when unreadable."""
        h = _open(pid, PROCESS_QUERY_LIMITED_INFORMATION | 0x0010)  # PROCESS_VM_READ
        if h is None:
            return {}
        try:
            c = PROCESS_MEMORY_COUNTERS()
            c.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            if not _k32.K32GetProcessMemoryInfo(h, ctypes.byref(c), c.cb):
                return {}
            return {"working_set": c.WorkingSetSize, "peak_working_set": c.PeakWorkingSetSize,
                    "private": c.PagefileUsage, "peak_private": c.PeakPagefileUsage}
        finally:
            _k32.CloseHandle(h)

else:
    def _ps(pid: int) -> tuple[int, str, str] | None:
        try:
            out = subprocess.run(["ps", "-o", "ppid=,lstart=,comm=", "-p", str(pid)], capture_output=True, text=True,
                                 errors="replace", stdin=subprocess.DEVNULL, timeout=10).stdout.strip()
        except FileNotFoundError:
            # No `ps` binary (minimal containers): the identity comes from /proc instead.
            return _proc_stat(pid)
        except (OSError, subprocess.SubprocessError):
            return None
        if not out:
            return None
        parts = out.split()
        # ppid, then lstart (5 fields: Dow Mon DD HH:MM:SS YYYY), then the command path
        if not _ascii_decimal(parts[0]):
            return None
        return int(parts[0]), " ".join(parts[1:6]), " ".join(parts[6:])

    def _proc_stat(pid: int) -> tuple[int, str, str] | None:
        """`(ppid, created, comm)` from /proc/<pid>/stat: the creation stamp is the kernel start
        time in clock ticks since boot, stable for the process's life and never reused within a boot."""
        try:
            with open(f"/proc/{pid}/stat", encoding="ascii", errors="replace") as f:
                stat = f.read()
        except OSError:
            return None
        # The command name sits in parentheses and may itself contain spaces or parentheses.
        start, end = stat.find("("), stat.rfind(")")
        if start < 0 or end < start:
            return None
        comm = stat[start + 1:end]
        fields = stat[end + 2:].split()  # field 3 (state) onward
        if len(fields) < 20 or not _ascii_decimal(fields[1]):
            return None
        return int(fields[1]), f"starttime:{fields[19]}", comm

    def _proc_children(pid: int) -> list[int]:
        kids = []
        try:
            entries = os.listdir("/proc")
        except OSError:
            return []
        for entry in entries:
            if not _ascii_decimal(entry):
                continue
            child_pid = int(entry)
            row = _proc_stat(child_pid)
            if row is not None and row[0] == pid:
                kids.append(child_pid)
        return kids

    def _identity(pid: int, ppid: int, created: str, comm: str) -> ProcInfo:
        exe = comm
        link = f"/proc/{pid}/exe"
        if os.path.exists(link):
            try:
                exe = os.readlink(link)
            except OSError:
                pass
        # Replacement text (or readlink's undecodable surrogate bytes) is not an attributable executable path.
        if "\ufffd" in exe or any(0xD800 <= ord(char) <= 0xDFFF for char in exe):
            exe = ""
        return ProcInfo(pid=pid, ppid=ppid, created=created, exe=exe)

    def info(pid: int, *, ppid: int | None = None) -> ProcInfo | None:
        if pid <= 0:
            return None
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            pass
        row = _ps(pid)
        if row is None:
            return None
        return _identity(pid, *row)

    def parse_ps_table(text: str) -> ProcessTable:
        """Account for every nonblank ps row; a missing PID makes the entire observation unavailable."""
        out: dict[int, ProcInfo] = {}
        unidentified: set[int] = set()
        for line in text.splitlines():
            parts = line.split()
            if not parts:
                continue
            if not _ascii_decimal(parts[0]):
                raise TableUnavailable("process table row has no recoverable PID")
            pid = int(parts[0])
            if len(parts) < 8 or not _ascii_decimal(parts[1]):
                unidentified.add(pid)
                continue
            proc = _identity(pid, int(parts[1]), " ".join(parts[2:7]), " ".join(parts[7:]))
            if proc.created and proc.exe:
                out[pid] = proc
            else:
                unidentified.add(pid)
        for pid in unidentified:
            out.pop(pid, None)
        return _checked_table(out, unidentified)

    def _proc_table() -> ProcessTable:
        try:
            entries = os.listdir("/proc")
        except OSError as exc:
            raise TableUnavailable(f"process table unreadable: {exc}") from None
        out, unidentified = {}, set()
        for entry in entries:
            if not _ascii_decimal(entry):
                continue
            pid = int(entry)
            try:
                row = _proc_stat(pid)
                proc = _identity(pid, *row) if row is not None else None
            except (OSError, ValueError):
                proc = None
            if proc is not None and proc.created and proc.exe:
                out[pid] = proc
            else:
                unidentified.add(pid)
        return _checked_table(out, unidentified)

    def table() -> ProcessTable:
        """Account for every PID and require our own readable identity, or raise TableUnavailable.

        Undecodable text is replaced; an unreadable executable makes its PID unidentified, not another process.
        Ordinary ps stamps resolve to one second (issue #92); the procfs fallback does not change that limit.
        """
        try:
            done = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,lstart=,comm="], capture_output=True, text=True,
                                  errors="replace", stdin=subprocess.DEVNULL, timeout=10)
        except FileNotFoundError:
            return _proc_table()
        except (OSError, subprocess.SubprocessError) as exc:
            raise TableUnavailable(f"process table unreadable: {exc}") from None
        if done.returncode != 0:
            raise TableUnavailable(f"process table unreadable: ps exited {done.returncode}")
        return parse_ps_table(done.stdout)

    def children(pid: int) -> list[int]:
        try:
            out = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, timeout=10).stdout
        except FileNotFoundError:
            return _proc_children(pid)
        except (OSError, subprocess.SubprocessError):
            return []
        kids = []
        for line in out.splitlines():
            p, _, pp = line.strip().partition(" ")
            if pp.strip() == str(pid) and _ascii_decimal(p):
                kids.append(int(p))
        return kids

    def terminate(proc: ProcInfo, timeout: float) -> bool:
        current = info(proc.pid)
        if current is None:
            return True
        if (current.created, current.exe) != (proc.created, proc.exe):
            raise PermissionError(f"pid {proc.pid} is now another process; refusing to signal it")
        os.kill(proc.pid, signal.SIGTERM)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if info(proc.pid) is None:
                return True
            time.sleep(0.2)
        again = info(proc.pid)
        if again is not None and (again.created, again.exe) == (proc.created, proc.exe):
            os.kill(proc.pid, signal.SIGKILL)
            time.sleep(0.5)
        return info(proc.pid) is None

    def memory() -> dict[str, int]:
        total = avail = 0
        try:
            with open("/proc/meminfo", encoding="ascii") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    if k not in ("MemTotal", "MemAvailable"):
                        continue
                    parts = v.split()
                    if not parts or not _ascii_decimal(parts[0]):
                        continue
                    if k == "MemTotal":
                        total = int(parts[0]) * 1024
                    elif k == "MemAvailable":
                        avail = int(parts[0]) * 1024
        except OSError:
            pass
        return {"total": total, "available": avail, "commit_limit": 0, "commit_available": 0}

    def process_memory(pid: int) -> dict[str, int]:
        """Current and peak resident set of one process (bytes, Linux /proc); {} elsewhere or when unreadable."""
        fields = {"VmRSS": "working_set", "VmHWM": "peak_working_set"}
        out: dict[str, int] = {}
        try:
            with open(f"/proc/{pid}/status", encoding="ascii") as f:
                for line in f:
                    k, _, v = line.partition(":")
                    if k in fields:
                        parts = v.split()
                        if parts and _ascii_decimal(parts[0]):
                            out[fields[k]] = int(parts[0]) * 1024
        except OSError:
            return {}
        return out


def same_identity(live: ProcInfo, recorded: dict) -> bool:
    """True when a live process is the recorded one: same creation time and executable (case-blind on Windows)."""
    same_exe = live.exe.lower() == recorded["exe"].lower() if WINDOWS else live.exe == recorded["exe"]
    return live.created == recorded["created"] and same_exe


def matches(recorded: dict | None) -> ProcInfo | None:
    """The live process for a recorded identity, or None when it is gone or the PID now belongs to another."""
    if not recorded:
        return None
    live = info(int(recorded["pid"]))
    return live if live is not None and same_identity(live, recorded) else None


def descendants(pid: int) -> list[ProcInfo]:
    """Every live descendant of pid, deepest first (so a tree can be stopped bottom-up).

    On Windows a venv `python.exe` is a redirector that runs the base interpreter as a child, so the real stock
    server and its engine sit one and two levels below the recorded server process. A child must also have been
    created after its parent: Windows keeps a dead parent's PID in the child record, and PIDs are reused."""
    root = info(pid)
    if root is None:
        return []
    out: list[ProcInfo] = []
    frontier = [root]
    seen = {pid}
    while frontier:
        nxt = []
        for parent in frontier:
            for c in children(parent.pid):
                if c in seen:
                    continue
                seen.add(c)
                child = info(c)
                if child is None or child.ppid != parent.pid:
                    continue
                if WINDOWS and (not _ascii_decimal(child.created) or not _ascii_decimal(parent.created)
                                or int(child.created) < int(parent.created)):
                    continue
                out.append(child)
                nxt.append(child)
        frontier = nxt
    return list(reversed(out))
