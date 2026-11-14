"""Dormancy proof: original function bodies and generated native-boundary behavior."""
import ast
import io
import itertools
from pathlib import Path
from types import SimpleNamespace
import unittest

from omp_strata import procs
from tests.unit.frozen_procs_main import SOURCE


def functions(source):
    tree = ast.parse(source)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found["shared", node.name] = node
        elif isinstance(node, ast.ClassDef) and node.name == "ProcInfo":
            found["shared", "as_dict"] = next(n for n in node.body if isinstance(n, ast.FunctionDef))
        elif isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "WINDOWS":
            for platform, body in (("windows", node.body), ("posix", node.orelse)):
                found.update({(platform, n.name): n for n in body if isinstance(n, ast.FunctionDef)})
    return found


def namespace(source, windows):
    nodes = [node for (platform, _), node in functions(source).items()
             if platform in ("shared", "windows" if windows else "posix")]
    result = dict(vars(procs), WINDOWS=windows)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<frozen-or-current-procs>", "exec"), result)
    return result


class Boundary:
    def __init__(self, site="ppid", value="10", mode="ordinary"):
        self.site, self.value, self.mode = site, value, mode
        self.events, self.alive, self.tick, self.index, self.error = [], True, 0, 0, 18

    def field(self, site, default):
        return self.value if self.site == site else default

    def clock(self):
        self.tick += 1
        return self.tick

    def kill(self, pid, sig):
        self.events.append(("kill", pid, int(sig)))
        if not self.alive:
            raise ProcessLookupError("gone")
        if sig:
            self.alive = False

    def exists(self, path):
        self.events.append(("exists", path))
        return self.mode != "missing-link"

    def link(self, path):
        self.events.append(("readlink", path))
        if self.mode == "denied-link":
            raise PermissionError("unreadable link")
        pid = path.split("/")[2]
        return "/native/" + pid + ("\udcff" if self.mode == "surrogate" else "\ufffd" if self.mode == "replacement" else "")

    def listdir(self, path):
        self.events.append(("listdir", path))
        return ["10", self.field("directory", "11")]

    def run(self, argv, **kwargs):
        self.events.append(("run", tuple(argv), kwargs.get("errors", "strict")))
        if self.mode == "missing-ps":
            raise FileNotFoundError("ps absent")
        if "-p" in argv:
            pid = argv[-1]
            ppid = self.field("ppid", "1" if pid == "10" else "10")
            text = ppid + " Fri Nov 13 12:34:56 2026 /native/" + pid
        else:
            text = self.field("child", "11") + " 10\n"
        raw = text.encode() + (b"\xff" if self.mode == "bad-bytes" else b"")
        return SimpleNamespace(stdout=raw.decode("utf-8", errors=kwargs.get("errors", "strict")), returncode=0)

    def open(self, path, **kwargs):
        self.events.append(("open", path, kwargs.get("encoding"), kwargs.get("errors", "strict")))
        if self.mode == "denied-file":
            raise PermissionError("unreadable file")
        if path.endswith("/stat"):
            pid = path.split("/")[2]
            fields = ["S", self.field("stat-ppid", "1" if pid == "10" else "10"), *(["0"] * 17), "100"]
            text = pid + " (native) " + " ".join(fields)
        elif path == "/proc/meminfo":
            text = "MemTotal: " + self.field("total", "100") + "\nMemAvailable: " + self.field("available", "50") + "\n"
            if self.site == "memory-line":
                text += self.value + "\n"
        else:
            text = "VmRSS: " + self.field("rss", "10") + "\nVmHWM: " + self.field("peak", "20") + "\n"
        raw = text.encode("utf-8")
        return io.StringIO(raw.decode(kwargs.get("encoding", "utf-8"), errors=kwargs.get("errors", "strict")))

    def snapshot(self, *_):
        self.events.append(("snapshot",))
        self.index = 0
        return None if self.mode == "snapshot-failed" else 900

    def enumerate(self, handle, entry):
        self.events.append(("enumerate", self.index))
        if self.mode == "first-failed" or self.index == 1 and self.mode == "partial-walk":
            self.error = 5
            return False
        if self.index == 2:
            self.error = 18
            return False
        entry.th32ProcessID, entry.th32ParentProcessID = (10, 1) if self.index == 0 else (11, 10)
        entry.szExeFile = "native"
        self.index += 1
        return True

    def close(self, handle):
        self.events.append(("close", handle))
        self.error = 0

    def get_error(self):
        self.events.append(("last-error",))
        return self.error

    def open_process(self, access, inherit, pid):
        self.events.append(("open-process", access, pid))
        return None if self.mode == "open-failed" else pid

    def exit_code(self, handle, code):
        code.value = 259 if self.alive and self.mode != "exited" else 0
        return True

    def times(self, handle, created, *_):
        created.dwHighDateTime, created.dwLowDateTime = 0, 100 + handle
        return self.mode != "time-failed"

    def image(self, handle, flags, buf, size):
        buf.value = "/native/" + str(handle)
        return self.mode != "image-failed"

    def memory(self, value):
        value.ullTotalPhys, value.ullAvailPhys = 100, 50
        value.ullTotalPageFile, value.ullAvailPageFile = 200, 150
        return True

    def process_memory(self, handle, value, size):
        value.WorkingSetSize, value.PeakWorkingSetSize = 10, 20
        value.PagefileUsage, value.PeakPagefileUsage = 30, 40
        return self.mode != "memory-failed"

    def terminate(self, handle, code):
        self.events.append(("terminate", handle, code))
        self.alive = False

    def globals(self):
        import subprocess
        return dict(
            os=SimpleNamespace(kill=self.kill, path=SimpleNamespace(exists=self.exists), readlink=self.link,
                               listdir=self.listdir, getpid=lambda: 10),
            subprocess=SimpleNamespace(run=self.run, SubprocessError=subprocess.SubprocessError, DEVNULL=subprocess.DEVNULL), open=self.open,
            time=SimpleNamespace(monotonic=self.clock, sleep=lambda seconds: self.events.append(("sleep", seconds))),
            _k32=SimpleNamespace(CreateToolhelp32Snapshot=self.snapshot, Process32FirstW=self.enumerate,
                                Process32NextW=self.enumerate, CloseHandle=self.close, OpenProcess=self.open_process,
                                GetExitCodeProcess=self.exit_code, GetProcessTimes=self.times,
                                QueryFullProcessImageNameW=self.image, GlobalMemoryStatusEx=self.memory,
                                K32GetProcessMemoryInfo=self.process_memory, TerminateProcess=self.terminate,
                                WaitForSingleObject=lambda handle, timeout: 0),
            ctypes=SimpleNamespace(sizeof=lambda value: 1, byref=lambda value: value,
                                   create_unicode_buffer=lambda size: SimpleNamespace(value=""), get_last_error=self.get_error),
            wintypes=SimpleNamespace(HANDLE=lambda value=0: SimpleNamespace(value=value),
                                    DWORD=lambda value=0: SimpleNamespace(value=value),
                                    FILETIME=lambda: SimpleNamespace(dwHighDateTime=0, dwLowDateTime=0)),
            PROCESSENTRY32W=SimpleNamespace, MEMORYSTATUSEX=SimpleNamespace, PROCESS_MEMORY_COUNTERS=SimpleNamespace,
            TH32CS_SNAPPROCESS=2, ERROR_NO_MORE_FILES=18, PROCESS_QUERY_LIMITED_INFORMATION=4096,
            PROCESS_TERMINATE=1, SYNCHRONIZE=1048576, STILL_ACTIVE=259)


def outcome(function, args, kwargs):
    try:
        return "result", function(*args, **kwargs)
    except Exception as exc:
        return "exception", type(exc)


class LegacyDormancyWalk(unittest.TestCase):
    def test_every_original_function_body_is_byte_identical(self):
        current = Path(procs.__file__).read_text()
        actual = functions(current)
        baseline_class = next(n for n in ast.parse(SOURCE).body if isinstance(n, ast.ClassDef) and n.name == "ProcInfo")
        current_class = next(n for n in ast.parse(current).body if isinstance(n, ast.ClassDef) and n.name == "ProcInfo")
        self.assertEqual(ast.dump(baseline_class, include_attributes=False), ast.dump(current_class, include_attributes=False))
        for key, node in functions(SOURCE).items():
            with self.subTest(function=key):
                self.assertEqual(ast.get_source_segment(SOURCE, node), ast.get_source_segment(current, actual[key]))

    def test_generated_native_boundaries_match_frozen_main(self):
        current = Path(procs.__file__).read_text()
        values = ("", "0", "1", "10", "-1", "+1", "1_0", "١", "²", " 12", "+12", "١٢", "1 ", "x", "1:2")
        modes = ("ordinary", "missing-ps", "bad-bytes", "missing-link", "denied-link", "denied-file", "surrogate", "replacement")
        sites = ("ppid", "stat-ppid", "directory", "child", "total", "available", "rss", "peak", "memory-line")
        count, exercised = 0, set()
        for windows in (False, True):
            before, after = namespace(SOURCE, windows), namespace(current, windows)
            record = procs.ProcInfo(10, 1, "110" if windows else "Fri Nov 13 12:34:56 2026", "/native/10")
            queries = [("info", (10,), {}), ("children", (1 if windows else 10,), {}),
                       ("terminate", (record, 0), {}), ("memory", (), {}), ("process_memory", (10,), {}),
                       ("matches", (record.as_dict(),), {}), ("matches", (None,), {}),
                       ("descendants", (10,), {}), ("as_dict", (record,), {})]
            if windows:
                queries += [("_open", (10, 4096), {}), ("_parents", (), {}), ("info", (10,), {"ppid": 999})]
                cases = (("ppid", "10", mode) for mode in ("ordinary", "snapshot-failed", "first-failed", "partial-walk",
                                                            "open-failed", "exited", "time-failed", "image-failed", "memory-failed"))
            else:
                queries += [("_ps", (10,), {}), ("_proc_stat", (10,), {}), ("_proc_children", (10,), {}),
                            ("info", (0,), {}), ("info", (-1,), {})]
                cases = itertools.product(sites, values, modes)
            for site, value, mode in cases:
                for name, args, kwargs in queries:
                    with self.subTest(windows=windows, site=site, value=value, mode=mode, function=name):
                        left, right = Boundary(site, value, mode), Boundary(site, value, mode)
                        before.update(left.globals())
                        after.update(right.globals())
                        actual_args = args
                        if not windows and mode in ("surrogate", "replacement") and name in ("terminate", "matches") and args[0]:
                            exe = record.exe + ("\udcff" if mode == "surrogate" else "\ufffd")
                            actual = procs.ProcInfo(record.pid, record.ppid, record.created, exe)
                            actual_args = (actual.as_dict(),) if name == "matches" else (actual, 0)
                        expected, observed = outcome(before[name], actual_args, kwargs), outcome(after[name], actual_args, kwargs)
                        if expected[0] == "exception":
                            self.assertNotIn(expected[1], (AttributeError, NameError), "incomplete fake native boundary")
                        count += 1
                        exercised.add(("shared" if name in ("matches", "descendants", "as_dict") else
                                       "windows" if windows else "posix", name))
                        self.assertEqual(expected, observed)
                        self.assertEqual(left.events, right.events)
        self.assertEqual(set(functions(SOURCE)), exercised)
        self.assertEqual(15228, count)

    def test_frozen_boundaries_exercise_the_required_examples(self):
        stamp = "Fri Nov 13 12:34:56 2026"
        cases = ((False, "ppid", "-1", "ordinary", "_ps", (10,), ("result", (-1, stamp, "/native/10"))),
                 (False, "ppid", "10", "bad-bytes", "_ps", (10,), ("exception", UnicodeDecodeError)),
                 (False, "total", "x", "ordinary", "memory", (), ("exception", ValueError)),
                 (False, "total", "", "ordinary", "memory", (), ("exception", IndexError)),
                 (False, "child", "+1", "ordinary", "children", (10,), ("result", [1])),
                 (False, "directory", "١", "ordinary", "_proc_children", (10,), ("result", [1])),
                 (True, "ppid", "10", "partial-walk", "_parents", (), ("result", {10: (1, "native")})),
                 (True, "ppid", "10", "partial-walk", "children", (1,), ("result", [10])))
        for windows, site, value, mode, name, args, expected in cases:
            with self.subTest(windows=windows, site=site, value=value, mode=mode, function=name):
                baseline = namespace(SOURCE, windows)
                baseline.update(Boundary(site, value, mode).globals())
                self.assertEqual(expected, outcome(baseline[name], args, {}))

    def test_windows_ancestry_numeric_inputs_match_frozen_main(self):
        current = Path(procs.__file__).read_text()
        values = ("-1", "+1", "1_0", "١", "²", " 12", "+12", "١٢", "", "x")
        for value, target in itertools.product(values, (10, 11)):
            with self.subTest(value=value, target=target):
                outputs = []
                for source in (SOURCE, current):
                    ns = namespace(source, True)
                    world = {10: procs.ProcInfo(10, 1, value if target == 10 else "10", "/parent"),
                             11: procs.ProcInfo(11, 10, value if target == 11 else "12", "/child")}
                    ns.update(info=world.get, children=lambda pid: [11] if pid == 10 else [])
                    outputs.append(outcome(ns["descendants"], (10,), {}))
                self.assertEqual(outputs[0], outputs[1])
