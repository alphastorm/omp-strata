"""Host-free process reader boundaries; native Windows is not qualified here."""
import ast
import itertools
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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


def windows_reader(source, created, readable=True, self_readable=True):
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
                     info=lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(created), "/runtime/engine")
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
        for count, position, error, readable, delta, self_readable in itertools.product(
                (0, 1, 3), ("none", "first", "after-first", "after-last"), (18, 5),
                (False, True), (-1, 0, 1), (False, True)):
            with self.subTest(case=(count, position, error, readable, delta, self_readable)):
                cases += 1
                source = SnapshotSource(count, position, error)
                table = windows_reader(source, self.cutoff + delta, readable, self_readable)
                length = {"none": count, "first": 0, "after-first": min(1, count), "after-last": count}[position]
                if position != "none" and error != 18 or not length or not self_readable:
                    with self.assertRaises(procs.TableUnavailable):
                        table()
                else:
                    expected = {pid: procs.ProcInfo(pid, 0 if delta > 0 else 1,
                                                   str(self.cutoff + delta), "/runtime/engine")
                                for pid in range(10, 10 + length) if pid == 10 or readable}
                    snapshot = table()
                    self.assertEqual(expected, snapshot.identified)
                    self.assertEqual(set(range(10, 10 + length)) - expected.keys(), snapshot.unidentified)
                self.assertLess(source.events.index("error"), source.events.index("close"))
        self.assertEqual(288, cases)

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

    def test_unreadable_executable_is_unknown_even_with_readable_creation_time(self):
        for exe in ("/runtime/\ufffdengine", "/runtime/\udcffengine", ""):
            with self.subTest(exe=repr(exe)), patch.object(procs.os.path, "exists", return_value=True), \
                    patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os, "readlink", side_effect=lambda path: "/fixture/self" if path == "/proc/10/exe" else exe):
                snapshot = procs.parse_ps_table("10 1 Fri Nov 13 12:34:56 2026 self\n"
                                               "11 1 Fri Nov 13 12:34:56 2026 engine\n")
                self.assertEqual({11}, snapshot.unidentified)
                record = procs.ProcInfo(11, 1, "Fri Nov 13 12:34:56 2026", "/old/engine").as_dict()
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
        for windows, outcome, own in itertools.product((False, True), ("same", "another-process", "not-enumerated", "cannot-say"), (False, True)):
            with self.subTest(windows=windows, outcome=outcome, self_readable=own), \
                    patch.object(procs, "WINDOWS", windows), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", return_value=False):
                pid = 99 if outcome == "not-enumerated" else 11
                created = str(cutoff) if windows else "Fri Nov 13 12:34:56 2026"
                record = procs.ProcInfo(pid, 1, created, "/runtime/engine").as_dict()
                if windows:
                    reader = windows_reader(SnapshotSource(count=2), cutoff, outcome != "cannot-say", own)
                    if outcome == "another-process":
                        reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(cutoff), "/other") if pid != 10 or own else None
                else:
                    text = "10 1 Fri Nov 13 12:34:56 2026 /self\n" if own else ""
                    text += "11 unknown\n" if outcome == "cannot-say" else "11 1 Fri Nov 13 12:34:56 2026 " + ("/other" if outcome == "another-process" else "/runtime/engine") + "\n"
                    reader = lambda: procs.parse_ps_table(text)
                if not own:
                    with self.assertRaises(procs.TableUnavailable):
                        reader()
                else:
                    self.assertEqual(outcome, reader().observe(record).value)
                cases += 1
        self.assertEqual(16, cases)
