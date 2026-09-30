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

WINDOWS = sys.platform == "win32"


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    ppid: int
    created: str          # opaque, stable creation stamp (Windows FILETIME ticks, POSIX start time)
    exe: str

    def as_dict(self) -> dict:
        return asdict(self)


if WINDOWS:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]  # Windows-only branch
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_TERMINATE = 0x0001
    SYNCHRONIZE = 0x00100000
    TH32CS_SNAPPROCESS = 0x00000002

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

    def _parents() -> dict[int, tuple[int, str]]:
        snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        out: dict[int, tuple[int, str]] = {}
        if snap in (None, wintypes.HANDLE(-1).value):
            return out
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = _k32.Process32FirstW(snap, ctypes.byref(entry))
            while ok:
                out[int(entry.th32ProcessID)] = (int(entry.th32ParentProcessID), entry.szExeFile)
                ok = _k32.Process32NextW(snap, ctypes.byref(entry))
        finally:
            _k32.CloseHandle(snap)
        return out

    def info(pid: int) -> ProcInfo | None:
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
                                 stdin=subprocess.DEVNULL, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
        if not out:
            return None
        parts = out.split()
        # ppid, then lstart (5 fields: Dow Mon DD HH:MM:SS YYYY), then the command path
        return int(parts[0]), " ".join(parts[1:6]), " ".join(parts[6:])

    def info(pid: int) -> ProcInfo | None:
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
        ppid, created, comm = row
        exe = comm
        link = f"/proc/{pid}/exe"
        if os.path.exists(link):
            try:
                exe = os.readlink(link)
            except OSError:
                pass
        return ProcInfo(pid=pid, ppid=ppid, created=created, exe=exe)

    def children(pid: int) -> list[int]:
        try:
            out = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return []
        kids = []
        for line in out.splitlines():
            p, _, pp = line.strip().partition(" ")
            if pp.strip() == str(pid):
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
                    if k == "MemTotal":
                        total = int(v.split()[0]) * 1024
                    elif k == "MemAvailable":
                        avail = int(v.split()[0]) * 1024
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
                        out[fields[k]] = int(v.split()[0]) * 1024
        except OSError:
            return {}
        return out


def matches(recorded: dict | None) -> ProcInfo | None:
    """The live process for a recorded identity, or None when it is gone or the PID now belongs to another."""
    if not recorded:
        return None
    live = info(int(recorded["pid"]))
    if live is None:
        return None
    same_exe = live.exe.lower() == recorded["exe"].lower() if WINDOWS else live.exe == recorded["exe"]
    return live if live.created == recorded["created"] and same_exe else None


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
                if WINDOWS and int(child.created) < int(parent.created):
                    continue
                out.append(child)
                nxt.append(child)
        frontier = nxt
    return list(reversed(out))
