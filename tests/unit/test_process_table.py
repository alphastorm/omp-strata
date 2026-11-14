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


def windows_reader(source, created, readable=True):
    """Execute production Windows readers, substituting only native/clock/identity boundaries."""
    tree = ast.parse(Path(procs.__file__).read_text())
    branch = next(node for node in tree.body if isinstance(node, ast.If)
                  and isinstance(node.test, ast.Name) and node.test.id == "WINDOWS")
    bodies = [node for node in branch.body if isinstance(node, ast.FunctionDef)
              and node.name in ("_snapshot", "table")]
    namespace = dict(vars(procs), _k32=source, TH32CS_SNAPPROCESS=2, ERROR_NO_MORE_FILES=18,
                     PROCESSENTRY32W=SimpleNamespace,
                     wintypes=SimpleNamespace(HANDLE=lambda value: SimpleNamespace(value=value)),
                     ctypes=SimpleNamespace(sizeof=lambda value: 1, byref=lambda value: value,
                                            get_last_error=source.get_last_error))

    def clock():
        source.events.append("clock")
        return 123456789000

    namespace.update(time=SimpleNamespace(time_ns=clock),
                     info=lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(created), "/runtime/engine")
                     if readable else None)
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
        rows = windows_reader(SnapshotSource(count=1), self.cutoff + 1)()
        self.assertIn(10, rows)
        self.assertEqual(0, rows[10].ppid)

    def test_snapshot_precedes_clock_so_intervening_process_is_not_hidden(self):
        source = SnapshotSource(count=1)
        rows = windows_reader(source, self.cutoff)()
        self.assertEqual({10}, set(rows))
        self.assertLess(source.events.index("snapshot"), source.events.index("clock"))

    def test_finite_snapshot_walk_is_complete_or_unavailable(self):
        # An EOF is the source's authoritative end, including an empty snapshot; another error is not.
        cases = 0
        for count, position, error, readable, delta in itertools.product(
                (0, 1, 3), ("none", "first", "after-first", "after-last"), (18, 5),
                (False, True), (-1, 0, 1)):
            with self.subTest(case=(count, position, error, readable, delta)):
                cases += 1
                source = SnapshotSource(count, position, error)
                table = windows_reader(source, self.cutoff + delta, readable)
                if position != "none" and error != 18:
                    with self.assertRaises(procs.TableUnavailable):
                        table()
                else:
                    length = {"none": count, "first": 0, "after-first": min(1, count),
                              "after-last": count}[position]
                    expected = {pid: procs.ProcInfo(pid, 0 if delta > 0 else 1,
                                                   str(self.cutoff + delta), "/runtime/engine")
                                for pid in range(10, 10 + length) if readable}
                    self.assertEqual(expected, table())
                self.assertLess(source.events.index("error"), source.events.index("close"))
        self.assertEqual(144, cases)


@unittest.skipIf(procs.WINDOWS, "POSIX decoder boundary")
class ProcessTextTests(unittest.TestCase):
    def test_undecodable_process_name_is_replaced_not_fatal(self):
        raw = b"987654321 1 Fri Nov 13 12:34:56 2026 /fixture/\xffengine\n"

        def run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, raw.decode("utf-8", errors=kwargs.get("errors", "strict")))

        with patch.object(procs.subprocess, "run", side_effect=run), patch.object(procs.os.path, "exists", return_value=False):
            rows = procs.table()
        self.assertEqual("", rows[987654321].exe)  # A replacement-decoded path cannot authorize path ownership.

    def test_unreadable_path_retains_identity_but_cannot_supply_path_ownership(self):
        for exe in ("/runtime/\ufffdengine", "/runtime/\udcffengine"):
            with self.subTest(exe=repr(exe)), patch.object(procs.os.path, "exists", return_value=True), \
                    patch.object(procs.os, "readlink", return_value=exe):
                row = procs.parse_ps_table("987654321 1 Fri Nov 13 12:34:56 2026 engine\n")[987654321]
                self.assertEqual("", row.exe)
                self.assertEqual("Fri Nov 13 12:34:56 2026", row.created)


@unittest.skipIf(procs.WINDOWS, "POSIX ps boundary; native Windows is unexercised")
class ProcessTableTests(unittest.TestCase):
    def test_same_executable_pid_reuse_inside_one_second_is_not_distinguished(self):
        # Declared POSIX limit: ps lstart cannot distinguish these two lifetimes.
        text = "987654321 1 Fri Nov 13 12:34:56 2026 /fixture/python\n"
        first = procs.parse_ps_table(text)[987654321]
        replacement = procs.parse_ps_table(text)[987654321]
        self.assertTrue(procs.same_identity(replacement, first.as_dict()))

    def test_malformed_ps_rows_are_left_out_without_losing_valid_rows(self):
        text = ("987654321 1 Fri Nov 13 12:34:56 2026 /fixture/path with spaces/python\n"
                "truncated\n"
                "not-a-pid 1 Fri Nov 13 12:34:56 2026 /fixture/python\n"
                "987654320 not-a-parent Fri Nov 13 12:34:56 2026 /fixture/python\n")
        self.assertEqual({987654321: procs.ProcInfo(987654321, 1, "Fri Nov 13 12:34:56 2026",
                                                   "/fixture/path with spaces/python")}, procs.parse_ps_table(text))

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
                                            text=True, stdin=subprocess.DEVNULL, timeout=10)
