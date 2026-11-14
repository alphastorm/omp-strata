"""Host-free process reader boundaries; native Windows is not qualified here."""
import ast
import itertools
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import mock_open, patch

from omp_strata import procs


class SnapshotSource:
    """Toolhelp-shaped source with an observable thread-local error and handle close."""
    def __init__(self, count=3, position="none", error=5):
        self.count, self.position, self.error = count, position, error
        self.index, self.last_error = 0, 0
        self.events = []

    def CreateToolhelp32Snapshot(self, flags, pid):
        self.events.append("snapshot")
        return 7

    def row(self, entry):
        stop = {"first": 0, "after-first": min(1, self.count), "after-last": self.count}.get(self.position)
        if self.index == stop or self.index >= self.count:
            self.last_error = self.error if self.index == stop else 18
            return False
        entry.th32ProcessID, entry.th32ParentProcessID = 10 + self.index, 1
        entry.szExeFile = "engine.exe"
        self.index += 1
        return True

    def Process32FirstW(self, handle, entry):
        return self.row(entry)

    def Process32NextW(self, handle, entry):
        return self.row(entry)

    def CloseHandle(self, handle):
        self.events.append("close")
        self.last_error = 123  # Reading the error after close would lose the walk's outcome.

    def get_last_error(self):
        self.events.append("error")
        return self.last_error


def windows_reader(source, created, readable=True, self_readable=True, exe="/runtime/engine"):
    """Execute production Windows readers, substituting only native/clock/identity boundaries."""
    tree = ast.parse(Path(procs.__file__).read_text())
    branch = next(node for node in tree.body if isinstance(node, ast.If)
                  and isinstance(node.test, ast.Name) and node.test.id == "WINDOWS")
    bodies = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_checked_table"]
    bodies += [node for node in branch.body if isinstance(node, ast.FunctionDef)
               and node.name in ("_snapshot", "table")]
    namespace = dict(vars(procs), _k32=source, TH32CS_SNAPPROCESS=2, ERROR_NO_MORE_FILES=18,
                     PROCESSENTRY32W=SimpleNamespace,
                     wintypes=SimpleNamespace(HANDLE=lambda value: SimpleNamespace(value=value)),
                     ctypes=SimpleNamespace(sizeof=lambda value: 1, byref=lambda value: value,
                                            get_last_error=source.get_last_error))

    def clock():
        source.events.append("clock")
        return 123456789000

    namespace.update(time=SimpleNamespace(time_ns=clock), os=SimpleNamespace(getpid=lambda: 10),
                     info=lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(created), exe)
                     if (self_readable if pid == 10 else readable) else None)
    exec(compile(ast.Module(body=bodies, type_ignores=[]), procs.__file__, "exec"), namespace)
    return namespace["table"]


class SnapshotBoundaryTests(unittest.TestCase):
    cutoff = 116444736000000000 + 1234567890

    def test_next_entry_error_never_returns_a_partial_table(self):
        source = SnapshotSource(position="after-first")
        with self.assertRaises(procs.TableUnavailable):
            windows_reader(source, self.cutoff)()
        self.assertLess(source.events.index("error"), source.events.index("close"))

    def test_later_identity_is_kept_with_unknown_parent(self):
        rows = windows_reader(SnapshotSource(count=1), self.cutoff + 1)().identified
        self.assertIn(10, rows)
        self.assertEqual(0, rows[10].ppid)

    def test_snapshot_precedes_clock_so_intervening_process_is_not_hidden(self):
        source = SnapshotSource(count=1)
        rows = windows_reader(source, self.cutoff)().identified
        self.assertEqual({10}, set(rows))
        self.assertLess(source.events.index("snapshot"), source.events.index("clock"))

    def test_finite_snapshot_walk_is_complete_or_unavailable(self):
        # EOF defines the source end; an empty walk or missing self identity cannot prove completeness.
        cases = 0
        for count, position, error, kind, delta, self_readable in itertools.product(
                (0, 1, 3), ("none", "first", "after-first", "after-last"), (18, 5),
                ("ordinary", "lossless", "unreadable"), (-1, 0, 1), (False, True)):
            with self.subTest(case=(count, position, error, kind, delta, self_readable)):
                cases += 1
                readable = kind != "unreadable"
                exe = "/runtime/engine\udcff" if kind == "lossless" else "/runtime/engine"
                source = SnapshotSource(count, position, error)
                table = windows_reader(source, self.cutoff + delta, readable, self_readable, exe)
                length = {"none": count, "first": 0, "after-first": min(1, count), "after-last": count}[position]
                if position != "none" and error != 18 or not length or not self_readable:
                    with self.assertRaises(procs.TableUnavailable):
                        table()
                else:
                    expected = {pid: procs.ProcInfo(pid, 0 if delta > 0 else 1,
                                                   str(self.cutoff + delta), exe)
                                for pid in range(10, 10 + length) if pid == 10 or readable}
                    snapshot = table()
                    self.assertEqual(expected, snapshot.identified)
                    self.assertEqual(set(range(10, 10 + length)) - expected.keys(), snapshot.unidentified)
                self.assertLess(source.events.index("error"), source.events.index("close"))
        self.assertEqual(432, cases)

    def test_empty_windows_snapshot_is_unavailable(self):
        with self.assertRaises(procs.TableUnavailable):
            windows_reader(SnapshotSource(count=0), self.cutoff)()

    def test_enumerated_unreadable_pid_is_not_reported_absent(self):
        snapshot = windows_reader(SnapshotSource(count=2), self.cutoff, readable=False)()
        self.assertIn(11, getattr(snapshot, "unidentified", ()), "enumerated unreadable PID was reported absent")
        self.assertEqual("cannot-say", snapshot.observe(procs.ProcInfo(11, 1, str(self.cutoff), "/engine").as_dict()).value)


@unittest.skipIf(procs.WINDOWS, "POSIX decoder boundary")
class ProcessTextTests(unittest.TestCase):
    def test_undecodable_process_name_is_replaced_not_fatal(self):
        raw = (b"10 1 Fri Nov 13 12:34:56 2026 /fixture/self\n"
               b"987654321 1 Fri Nov 13 12:34:56 2026 /fixture/\xffengine\n")

        def run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, raw.decode("utf-8", errors=kwargs.get("errors", "strict")))

        with patch.object(procs.subprocess, "run", side_effect=run), patch.object(procs.os.path, "exists", return_value=False), \
                patch.object(procs.os, "getpid", return_value=10):
            snapshot = procs.table()
        self.assertEqual({987654321}, snapshot.unidentified)
        self.assertNotIn(987654321, snapshot.identified)

    def test_executable_fidelity_determines_table_identity(self):
        created = "Fri Nov 13 12:34:56 2026"
        for windows, exe in itertools.product((False, True), ("/runtime/engine", "/runtime/\udcffengine", "/runtime/\ufffdengine", "")):
            with self.subTest(windows=windows, exe=repr(exe)), patch.object(procs.os.path, "exists", return_value=True), \
                    patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os, "readlink", side_effect=lambda path: "/fixture/self" if path == "/proc/10/exe" else exe):
                if windows:
                    stamp = str(SnapshotBoundaryTests.cutoff)
                    reader = windows_reader(SnapshotSource(count=2), SnapshotBoundaryTests.cutoff)
                    reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, stamp, "/fixture/self" if pid == 10 else exe)
                    snapshot = reader()
                else:
                    stamp = created
                    snapshot = procs.parse_ps_table(f"10 1 {created} self\n11 1 {created} engine\n")
                lossless = bool(exe) and "\ufffd" not in exe
                self.assertEqual(set() if lossless else {11}, snapshot.unidentified)
                record = procs.ProcInfo(11, 1, stamp, exe).as_dict()
                self.assertEqual("same" if lossless else "cannot-say", snapshot.observe(record).value)

    def test_lossy_recorded_executable_never_claims_pid_reuse(self):
        stamp = "Fri Nov 13 12:34:56 2026"
        current = procs.ProcInfo(11, 1, stamp, "/runtime/engine")
        with patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os.path, "exists", return_value=False):
            snapshot = procs.parse_ps_table(f"10 1 {stamp} /self\n11 1 {stamp} /runtime/engine\n")
        for exe in ("", "/runtime/\ufffdengine"):
            with self.subTest(exe=repr(exe)):
                record = dict(current.as_dict(), exe=exe)
                self.assertEqual("cannot-say", snapshot.observe(record).value)


@unittest.skipIf(procs.WINDOWS, "POSIX ps boundary; native Windows is unexercised")
class ProcessTableTests(unittest.TestCase):
    def test_same_executable_pid_reuse_inside_one_second_is_not_distinguished(self):
        # Declared POSIX limit: ps lstart cannot distinguish these two lifetimes.
        text = "987654321 1 Fri Nov 13 12:34:56 2026 /fixture/python\n"
        with patch.object(procs.os, "getpid", return_value=987654321):
            first = procs.parse_ps_table(text).identified[987654321]
            replacement = procs.parse_ps_table(text)
        self.assertEqual("same", replacement.observe(first.as_dict()).value)

    def test_malformed_rows_preserve_pid_uncertainty_or_refuse_the_table(self):
        own = "10 1 Fri Nov 13 12:34:56 2026 /fixture/path with spaces/self\n"
        for bad in ("11", "11 not-a-parent Fri Nov 13 12:34:56 2026 /fixture/python"):
            with self.subTest(row=bad), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", return_value=False):
                snapshot = procs.parse_ps_table(own + bad + "\n")
                self.assertEqual({11}, snapshot.unidentified)
                self.assertEqual({10}, set(snapshot.identified))
                self.assertEqual("/fixture/path with spaces/self", snapshot.identified[10].exe)
        for bad in ("truncated", "not-a-pid 1 Fri Nov 13 12:34:56 2026 /fixture/python"):
            with self.subTest(row=bad), patch.object(procs.os, "getpid", return_value=10), \
                    self.assertRaises(procs.TableUnavailable):
                procs.parse_ps_table(own + bad + "\n")

    def test_procfs_accounts_for_every_enumerated_pid(self):
        with patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os, "listdir", return_value=["10", "11", "sys"]), \
                patch.object(procs, "_proc_stat", side_effect=lambda pid: (1, "starttime:1", "/self") if pid == 10 else None), \
                patch.object(procs.os.path, "exists", return_value=False):
            snapshot = procs._proc_table()
        self.assertEqual({10}, set(snapshot.identified))
        self.assertEqual({11}, snapshot.unidentified)

    def test_failed_timed_out_or_empty_ps_is_unavailable_not_an_empty_census(self):
        cases = (("failed", subprocess.CompletedProcess(["ps"], 1, "", "denied")),
                 ("timed out", subprocess.TimeoutExpired(["ps"], 10)),
                 ("empty", subprocess.CompletedProcess(["ps"], 0, "", "")))
        for name, result in cases:
            with self.subTest(case=name), patch.object(procs.subprocess, "run") as run:
                if isinstance(result, Exception):
                    run.side_effect = result
                else:
                    run.return_value = result
                with self.assertRaises(procs.TableUnavailable):
                    procs.table()
                run.assert_called_once_with(["ps", "-A", "-o", "pid=,ppid=,lstart=,comm="], capture_output=True,
                                            text=True, errors="replace", stdin=subprocess.DEVNULL, timeout=10)


@unittest.skipIf(procs.WINDOWS, "POSIX fake boundary runs alongside fake Toolhelp on this host")
class RecordedObservationWalk(unittest.TestCase):
    def test_four_recorded_outcomes_and_self_readability_on_both_sources(self):
        cases = 0
        cutoff = SnapshotBoundaryTests.cutoff
        for windows, outcome, own, exe in itertools.product((False, True), ("same", "another-process", "not-enumerated", "cannot-say"), (False, True), ("/runtime/engine", "/runtime/engine\udcff")):
            with self.subTest(windows=windows, outcome=outcome, self_readable=own, exe=repr(exe)), \
                    patch.object(procs, "WINDOWS", windows), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", return_value=False):
                pid = 99 if outcome == "not-enumerated" else 11
                created = str(cutoff) if windows else "Fri Nov 13 12:34:56 2026"
                record = procs.ProcInfo(pid, 1, created, exe).as_dict()
                if windows:
                    reader = windows_reader(SnapshotSource(count=2), cutoff, outcome != "cannot-say", own, exe)
                    if outcome == "another-process":
                        reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(cutoff), "/other") if pid != 10 or own else None
                else:
                    text = "10 1 Fri Nov 13 12:34:56 2026 /self\n" if own else ""
                    text += "11 unknown\n" if outcome == "cannot-say" else "11 1 Fri Nov 13 12:34:56 2026 " + ("/other" if outcome == "another-process" else exe) + "\n"
                    reader = lambda: procs.parse_ps_table(text)
                if not own:
                    with self.assertRaises(procs.TableUnavailable):
                        reader()
                else:
                    self.assertEqual(outcome, reader().observe(record).value)
                cases += 1
        self.assertEqual(32, cases)


@unittest.skipIf(procs.WINDOWS, "POSIX source readers are substituted, not run on a native Windows host")
class NumericSourceTests(unittest.TestCase):
    bad = ("²", "١", "-1", "+1", "1_0")

    def test_only_ascii_decimal_fields_are_accepted(self):
        for text, expected in (("", False), ("0", True), ("00", True), ("42", True),
                               ("²", False), ("١", False), ("-1", False), ("+1", False),
                               (" 1", False), ("1 ", False), ("1.0", False), ("1_0", False)):
            with self.subTest(field=text):
                self.assertEqual(expected, procs._ascii_decimal(text))

    def test_ps_table_numeric_failures_are_unavailable_or_unidentified(self):
        own = "10 1 Fri Nov 13 12:34:56 2026 /self\n"
        for bad in self.bad:
            with self.subTest(field=bad), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", return_value=False):
                with self.assertRaises(procs.TableUnavailable):
                    procs.parse_ps_table(own + f"{bad} 1 Fri Nov 13 12:34:56 2026 /engine\n")
                snapshot = procs.parse_ps_table(own + f"11 {bad} Fri Nov 13 12:34:56 2026 /engine\n")
                self.assertEqual({11}, snapshot.unidentified)

    def test_single_ps_identity_refuses_an_unreadable_parent(self):
        for bad in self.bad:
            with self.subTest(field=bad), patch.object(procs.subprocess, "run", return_value=
                    subprocess.CompletedProcess(["ps"], 0, f"{bad} Fri Nov 13 12:34:56 2026 /engine")):
                self.assertIsNone(procs._ps(11))

    def test_single_proc_stat_identity_refuses_an_unreadable_parent(self):
        for bad in self.bad:
            fields = ["S", bad, *("0" for _ in range(17)), "123"]
            with self.subTest(field=bad), patch("builtins.open", mock_open(read_data="11 (engine) " + " ".join(fields))):
                self.assertIsNone(procs._proc_stat(11))

    def test_child_readers_do_not_convert_nondecimal_pids(self):
        for bad in self.bad:
            with self.subTest(field=bad), patch.object(procs.os, "listdir", return_value=[bad, "11"]), \
                    patch.object(procs, "_proc_stat", return_value=(1, "starttime:1", "engine")):
                self.assertEqual([11], procs._proc_children(1))
            with self.subTest(field=bad, source="ps"), patch.object(procs.subprocess, "run", return_value=
                    subprocess.CompletedProcess(["ps"], 0, f"{bad} 1\n11 1\n")):
                self.assertEqual([11], procs.children(1))

    def test_procfs_table_only_enumerates_ascii_pid_names(self):
        for bad in self.bad:
            with self.subTest(field=bad), patch.object(procs.os, "listdir", return_value=[bad, "10"]), \
                    patch.object(procs, "_proc_stat", return_value=(1, "starttime:1", "/self")), \
                    patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os.path, "exists", return_value=False):
                self.assertEqual({10}, set(procs._proc_table().identified))

    def test_proc_memory_readers_leave_bad_numeric_fields_unknown(self):
        for bad in self.bad:
            with self.subTest(field=bad), patch("builtins.open", mock_open(read_data=f"MemTotal: {bad} kB\nMemAvailable: {bad} kB\n")):
                self.assertEqual({"total": 0, "available": 0, "commit_limit": 0, "commit_available": 0}, procs.memory())
            with self.subTest(field=bad, source="status"), patch("builtins.open", mock_open(read_data=f"VmRSS: {bad} kB\n")):
                self.assertEqual({}, procs.process_memory(11))

    def test_windows_creation_text_is_unknown_not_an_integer_escape(self):
        cutoff = SnapshotBoundaryTests.cutoff
        for bad in self.bad:
            reader = windows_reader(SnapshotSource(count=2), cutoff)
            reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(cutoff) if pid == 10 else bad, "/engine")
            with self.subTest(field=bad):
                snapshot = reader()
                self.assertEqual({11}, snapshot.unidentified)

    def test_windows_ancestry_never_converts_unreadable_creation_text(self):
        for bad, target in itertools.product(self.bad, (1, 2)):
            world = {1: procs.ProcInfo(1, 0, bad if target == 1 else "1", "/root"),
                     2: procs.ProcInfo(2, 1, bad if target == 2 else "2", "/child")}
            with self.subTest(field=bad, pid=target), patch.object(procs, "WINDOWS", True), \
                    patch.object(procs, "info", side_effect=world.get), \
                    patch.object(procs, "children", side_effect=lambda pid: [2] if pid == 1 else []):
                self.assertEqual([], procs.descendants(1))


# Verbatim function bodies from main 2db275e2c08bbb2717504b9af2352c6f0f5a2529, dedented only.
# The finite comparison substitutes OS/query boundaries, never the identity or traversal implementation.
_MAIN_SINGLE_PROCESS = r'''
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
    ppid, created, comm = row
    exe = comm
    link = f"/proc/{pid}/exe"
    if os.path.exists(link):
        try:
            exe = os.readlink(link)
        except OSError:
            pass
    return ProcInfo(pid=pid, ppid=ppid, created=created, exe=exe)

def matches(recorded: dict | None) -> ProcInfo | None:
    """The live process for a recorded identity, or None when it is gone or the PID now belongs to another."""
    if not recorded:
        return None
    live = info(int(recorded["pid"]))
    if live is None:
        return None
    same_exe = live.exe.lower() == recorded["exe"].lower() if WINDOWS else live.exe == recorded["exe"]
    return live if live.created == recorded["created"] and same_exe else None

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
        if pp.strip() == str(pid):
            kids.append(int(p))
    return kids

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
'''


@unittest.skipIf(procs.WINDOWS, "POSIX single-process identity compatibility")
class LegacyIdentityWalk(unittest.TestCase):
    def test_surrogate_escaped_record_still_matches_and_info_preserves_its_path(self):
        expected = procs.ProcInfo(11, 1, "created", "/runtime/engine\udcff")
        with patch.object(procs.os, "kill"), patch.object(procs, "_ps", return_value=(1, "created", "/comm")), \
                patch.object(procs.os.path, "exists", return_value=True), \
                patch.object(procs.os, "readlink", return_value=expected.exe):
            with self.subTest(reader="info"):
                self.assertEqual(expected, procs.info(11))
            with self.subTest(reader="matches"):
                self.assertEqual(expected, procs.matches(expected.as_dict()))

    def test_single_process_readers_are_result_identical_to_main_on_finite_inputs(self):
        cases = 0
        rows = {10: (1, "created-10", "/comm/root"), 11: (10, "created-11", "/comm/child")}
        for kind in ("ordinary", "surrogate", "replacement", "missing-link", "unreadable-link"):
            suffix = {"surrogate": "\udcff", "replacement": "\ufffd"}.get(kind, "")

            def readlink(path):
                if kind == "unreadable-link":
                    raise PermissionError("link unreadable")
                return "/native/engine-" + path.split("/")[2] + suffix

            with patch.object(procs.os, "kill"), patch.object(procs, "_ps", side_effect=rows.get), \
                    patch.object(procs.os.path, "exists", return_value=kind != "missing-link"), \
                    patch.object(procs.os, "readlink", side_effect=readlink), \
                    patch.object(procs.subprocess, "run", return_value=subprocess.CompletedProcess(
                        ["ps"], 0, "10 1\n11 10\n")):
                namespace = dict(vars(procs))
                exec(compile(_MAIN_SINGLE_PROCESS, "main-2db275e2-procs.py", "exec"), namespace)
                baseline = SimpleNamespace(**{name: namespace[name] for name in ("info", "matches", "children", "descendants")})
                self.assertEqual([11], baseline.children(10))
                self.assertEqual([baseline.info(11)], baseline.descendants(10))
                queries = [("info", (pid,), kwargs) for pid in (10, 11) for kwargs in ({}, {"ppid": 99})]
                queries += [("matches", (baseline.info(pid).as_dict(),), {}) for pid in (10, 11)]
                queries += [("children", (pid,), {}) for pid in (10, 11)]
                queries += [("descendants", (10,), {})]
                for name, args, kwargs in queries:
                    with self.subTest(kind=kind, reader=name, args=args):
                        self.assertEqual(getattr(baseline, name)(*args, **kwargs), getattr(procs, name)(*args, **kwargs))
                    cases += 1
        self.assertEqual(45, cases)


class OrderedSnapshotSource(SnapshotSource):
    def __init__(self, parents):
        super().__init__(count=len(parents))
        self.parents = list(parents.items())

    def row(self, entry):
        index = self.index
        present = super().row(entry)
        if present:
            entry.th32ProcessID, entry.th32ParentProcessID = self.parents[index]
        return present


@unittest.skipIf(procs.WINDOWS, "POSIX sources and fake Windows are walked together")
class RecordedIdentityShapeWalk(unittest.TestCase):
    def test_malformed_records_are_never_absent_reused_or_an_exception(self):
        from types import MappingProxyType
        cases = 0
        for windows, outcome in itertools.product((False, True), ("same", "another-process", "not-enumerated", "cannot-say")):
            with patch.object(procs, "WINDOWS", windows), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", return_value=False):
                stamp = "101" if windows else "Fri Nov 13 12:34:56 2026"
                valid = procs.ProcInfo(11, 1, stamp, "/runtime/engine").as_dict()
                if windows:
                    reader = windows_reader(SnapshotSource(count=1 if outcome == "not-enumerated" else 2), 101,
                                            readable=outcome != "cannot-say")
                    if outcome == "another-process":
                        reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, stamp, "/other")
                    snapshot = reader()
                else:
                    text = f"10 1 {stamp} /self\n"
                    if outcome == "cannot-say":
                        text += "11 unknown\n"
                    elif outcome != "not-enumerated":
                        text += f"11 1 {stamp} " + ("/other" if outcome == "another-process" else "/runtime/engine") + "\n"
                    snapshot = procs.parse_ps_table(text)
                malformed = [None, False, True, 0, 1, 1.5, "", "record", [], ["pid"], ()]
                malformed += [{k: v for k, v in valid.items() if k != missing} for missing in ("pid", "created", "exe")]
                for field, values in (
                        ("pid", (None, {}, [], False, True, 11.0, 11.5, "11", "bad", "", -1, 0)),
                        ("created", (None, {}, [], False, True, 101, 101.5, "")),
                        ("exe", (None, {}, [], False, True, 101, 101.5, ""))):
                    malformed += [dict(valid, **{field: value}) for value in values]
                self.assertEqual(42, len(malformed))
                for record in malformed:
                    cases += 1
                    with self.subTest(windows=windows, source=outcome, record=record):
                        self.assertEqual("cannot-say", snapshot.observe(record).value)
                for record in (valid, MappingProxyType(valid), dict(valid, ppid=None, extra=[])):
                    cases += 1
                    with self.subTest(windows=windows, source=outcome, valid=record):
                        self.assertEqual(outcome, snapshot.observe(record).value)
        self.assertEqual(360, cases)


@unittest.skipIf(procs.WINDOWS, "POSIX sources and fake Windows are walked together")
class ParentCreationOrderWalk(unittest.TestCase):
    def test_comparable_birth_order_vouches_for_edges_including_self(self):
        cases = 0
        for source, delta, child_first, self_role in itertools.product(
                ("windows", "procfs", "ps"), (-1, 0, 1), (False, True), ("parent", "child", "outside")):
            cases += 1
            with self.subTest(source=source, delta=delta, child_first=child_first, self_role=self_role), \
                    patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os.path, "exists", return_value=False):
                parent_pid = 10 if self_role == "parent" else 11
                child_pid = 10 if self_role == "child" else 12 if self_role == "outside" else 11
                other_pid = ({10, 11, 12} - {parent_pid, child_pid}).pop()
                def stamp(offset):
                    if source == "windows":
                        return str(SnapshotBoundaryTests.cutoff - 100 + offset)
                    if source == "procfs":
                        return f"starttime:{100 + offset}"
                    return f"Fri Nov 13 12:34:{56 + offset} 2026"
                world = {parent_pid: procs.ProcInfo(parent_pid, 0, stamp(0), "/outside/parent"),
                         child_pid: procs.ProcInfo(child_pid, parent_pid, stamp(delta), "/outside/child"),
                         other_pid: procs.ProcInfo(other_pid, 0, stamp(0), "/outside/other")}
                order = [child_pid, parent_pid, other_pid] if child_first else [parent_pid, child_pid, other_pid]
                if source == "windows":
                    native = OrderedSnapshotSource({pid: world[pid].ppid for pid in order})
                    reader = windows_reader(native, SnapshotBoundaryTests.cutoff - 100)
                    reader.__globals__["info"] = lambda pid, *, ppid: world[pid]
                    snapshot = reader()
                elif source == "procfs":
                    with patch.object(procs.os, "listdir", return_value=list(map(str, order))), \
                            patch.object(procs, "_proc_stat", side_effect=lambda pid: (world[pid].ppid, world[pid].created, world[pid].exe)):
                        snapshot = procs._proc_table()
                else:
                    snapshot = procs.parse_ps_table("\n".join(
                        f"{pid} {world[pid].ppid} {world[pid].created} {world[pid].exe}" for pid in order))
                expected = dict(world)
                if delta < 0:
                    old = world[child_pid]
                    expected[child_pid] = procs.ProcInfo(old.pid, 0, old.created, old.exe)
                self.assertEqual(expected, snapshot.identified)
                self.assertEqual(set(), snapshot.unidentified)
                for row in world.values():
                    self.assertEqual("same", snapshot.observe(row.as_dict()).value)
        self.assertEqual(54, cases)
