"""Host-free process reader boundaries; native Windows is not qualified here."""
import ast
import itertools
from pathlib import Path
import subprocess
import symtable
from types import SimpleNamespace
import unittest
from unittest.mock import mock_open, patch

from omp_strata import procs
from tests.unit.frozen_procs_main import SOURCE


class LegacyStructureTests(unittest.TestCase):
    def setUp(self):
        self.current = Path(procs.__file__).read_text()

    def preserved_lines(self):
        current = iter(enumerate(self.current.splitlines(keepends=True), 1))
        preserved = set()
        for number, line in enumerate(SOURCE.splitlines(keepends=True), 1):
            match = next((position for position, text in current if text == line), None)
            self.assertIsNotNone(match, f"baseline line {number} removed or altered: {line!r}")
            preserved.add(match)
        return preserved

    @staticmethod
    def bound_names(source):
        scope = symtable.symtable(source, "<process-structure>", "exec")
        return {symbol.get_name() for symbol in scope.get_symbols()
                if symbol.is_assigned() or symbol.is_imported()}

    def inserted_bindings(self):
        preserved = self.preserved_lines()
        inserted = []

        def walk(node):
            if isinstance(node, ast.stmt) and node.lineno not in preserved:
                inserted.append(node)
                return
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return
            for child in ast.iter_child_nodes(node):
                walk(child)

        walk(ast.parse(self.current))
        return self.bound_names(ast.unparse(ast.Module(body=inserted, type_ignores=[])))

    def test_baseline_lines_are_preserved_in_order(self):
        self.preserved_lines()

    def test_insertions_do_not_rebind_baseline_names(self):
        self.assertEqual(set(), self.inserted_bindings() & self.bound_names(SOURCE))

    def test_insertions_do_not_bind_unbound_legacy_globals(self):
        reads = set()

        def walk(scope):
            if scope.get_type() == "function":
                reads.update(symbol.get_name() for symbol in scope.get_symbols()
                             if symbol.is_global() and symbol.is_referenced())
            for child in scope.get_children():
                walk(child)

        walk(symtable.symtable(SOURCE, "<frozen-process-structure>", "exec"))
        self.assertEqual(set(), self.inserted_bindings() & (reads - self.bound_names(SOURCE)))

    def test_every_original_function_body_is_byte_identical(self):
        def functions(source):
            found = {}
            for node in ast.parse(source).body:
                if isinstance(node, ast.FunctionDef):
                    found["shared", node.name] = node
                elif isinstance(node, ast.ClassDef) and node.name == "ProcInfo":
                    found["shared", "as_dict"] = next(n for n in node.body if isinstance(n, ast.FunctionDef))
                elif isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "WINDOWS":
                    for platform, body in (("windows", node.body), ("posix", node.orelse)):
                        found.update({(platform, n.name): n for n in body if isinstance(n, ast.FunctionDef)})
            return found

        baseline = functions(SOURCE)
        actual = functions(self.current)
        self.assertEqual(18, len(baseline))
        baseline_class = next(n for n in ast.parse(SOURCE).body if isinstance(n, ast.ClassDef) and n.name == "ProcInfo")
        current_class = next(n for n in ast.parse(self.current).body if isinstance(n, ast.ClassDef) and n.name == "ProcInfo")
        self.assertEqual(ast.dump(baseline_class, include_attributes=False), ast.dump(current_class, include_attributes=False))
        for key, node in baseline.items():
            with self.subTest(function=key):
                self.assertEqual(ast.get_source_segment(SOURCE, node), ast.get_source_segment(self.current, actual[key]))


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

    def test_precapture_clock_keeps_intervening_identity_with_unknown_parent(self):
        source = SnapshotSource(count=1)
        rows = windows_reader(source, self.cutoff)().identified
        self.assertEqual({10}, set(rows))
        # Pre-capture sampling closes the PID-reuse gap; readable young identities still remain accounted for.
        self.assertEqual(0, rows[10].ppid)
        self.assertLess(source.events.index("clock"), source.events.index("snapshot"))

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
                table = windows_reader(source, self.cutoff - 10_000_000 + delta, readable, self_readable, exe)
                length = {"none": count, "first": 0, "after-first": min(1, count), "after-last": count}[position]
                if position != "none" and error != 18 or not length or not self_readable:
                    with self.assertRaises(procs.TableUnavailable):
                        table()
                else:
                    expected = {pid: procs.ProcInfo(pid, 0 if delta >= 0 else 1,
                                                   str(self.cutoff - 10_000_000 + delta), exe)
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
        stamps = (("Fri Nov 13 12:34:56 2026", "Fri Nov 13 12:34:57 2026"),
                  ("starttime:101", "starttime:102"))
        for (live_stamp, recorded_stamp), exe in itertools.product(stamps, ("", "/runtime/\ufffdengine", " (deleted)")):
            with self.subTest(stamps=(live_stamp, recorded_stamp), exe=repr(exe)), patch.object(procs, "WINDOWS", False):
                current = procs.ProcInfo(11, 1, live_stamp, "/runtime/engine")
                snapshot = procs.ProcessTable({11: current}, set())
                record = dict(current.as_dict(), created=recorded_stamp, exe=exe)
                self.assertEqual("cannot-say", snapshot.observe(record).value)


@unittest.skipIf(procs.WINDOWS, "POSIX ps boundary; native Windows is unexercised")
class ProcessTableTests(unittest.TestCase):
    def test_same_executable_pid_reuse_inside_one_second_is_not_distinguished(self):
        # Declared POSIX limit: ps lstart cannot distinguish these two lifetimes.
        text = "987654321 1 Fri Nov 13 12:34:56 2026 /fixture/python\n"
        with patch.object(procs.os, "getpid", return_value=987654321), patch.object(procs.os.path, "exists", return_value=False):
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
                    patch.object(procs.os.path, "exists", return_value=False), self.assertRaises(procs.TableUnavailable):
                procs.parse_ps_table(own + bad + "\n")

    def test_procfs_accounts_for_every_enumerated_pid(self):
        with patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os, "listdir", return_value=["10", "11", "sys"]), \
                patch.object(procs, "_table_proc_stat", side_effect=lambda pid: (1, "starttime:1", "/self") if pid == 10 else None), \
                patch.object(procs.os, "readlink", return_value="/self"):
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
                        reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(cutoff + 1), "/other") if pid != 10 or own else None
                else:
                    text = "10 1 Fri Nov 13 12:34:56 2026 /self\n" if own else ""
                    live_stamp = "Fri Nov 13 12:34:57 2026" if outcome == "another-process" else created
                    text += "11 unknown\n" if outcome == "cannot-say" else "11 1 " + live_stamp + " " + ("/other" if outcome == "another-process" else exe) + "\n"
                    reader = lambda: procs.parse_ps_table(text)
                if not own:
                    with self.assertRaises(procs.TableUnavailable):
                        reader()
                else:
                    expected = "cannot-say" if not windows and outcome == "another-process" else outcome
                    self.assertEqual(expected, reader().observe(record).value)
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


    def test_table_proc_stat_identity_refuses_an_unreadable_parent(self):
        for bad in self.bad:
            fields = ["S", bad, *("0" for _ in range(17)), "123"]
            with self.subTest(field=bad), patch("builtins.open", mock_open(read_data="11 (engine) " + " ".join(fields))):
                self.assertIsNone(procs._table_proc_stat(11))


    def test_procfs_table_only_enumerates_ascii_pid_names(self):
        for bad in self.bad:
            with self.subTest(field=bad), patch.object(procs.os, "listdir", return_value=[bad, "10"]), \
                    patch.object(procs, "_table_proc_stat", return_value=(1, "starttime:1", "/self")), \
                    patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os, "readlink", return_value="/self"):
                self.assertEqual({10}, set(procs._proc_table().identified))


    def test_windows_creation_text_is_unknown_not_an_integer_escape(self):
        cutoff = SnapshotBoundaryTests.cutoff
        for bad in self.bad:
            reader = windows_reader(SnapshotSource(count=2), cutoff)
            reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(cutoff) if pid == 10 else bad, "/engine")
            with self.subTest(field=bad):
                snapshot = reader()
                self.assertEqual({11}, snapshot.unidentified)



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
                        reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, "102", "/other")
                    snapshot = reader()
                else:
                    text = f"10 1 {stamp} /self\n"
                    if outcome == "cannot-say":
                        text += "11 unknown\n"
                    elif outcome != "not-enumerated":
                        live_stamp = "Fri Nov 13 12:34:57 2026" if outcome == "another-process" else stamp
                        text += f"11 1 {live_stamp} " + ("/other" if outcome == "another-process" else "/runtime/engine") + "\n"
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
                        expected = "cannot-say" if not windows and outcome == "another-process" else outcome
                        self.assertEqual(expected, snapshot.observe(record).value)
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
                        return str(SnapshotBoundaryTests.cutoff - 20_000_000 + offset)
                    if source == "procfs":
                        return f"starttime:{100 + offset}"
                    return f"Fri Nov 13 12:34:{56 + offset} 2026"
                world = {parent_pid: procs.ProcInfo(parent_pid, 0, stamp(0), "/outside/parent"),
                         child_pid: procs.ProcInfo(child_pid, parent_pid, stamp(delta), "/outside/child"),
                         other_pid: procs.ProcInfo(other_pid, 0, stamp(0), "/outside/other")}
                order = [child_pid, parent_pid, other_pid] if child_first else [parent_pid, child_pid, other_pid]
                if source == "windows":
                    native = OrderedSnapshotSource({pid: world[pid].ppid for pid in order})
                    reader = windows_reader(native, SnapshotBoundaryTests.cutoff - 20_000_000)
                    reader.__globals__["info"] = lambda pid, *, ppid: world[pid]
                    snapshot = reader()
                elif source == "procfs":
                    with patch.object(procs.os, "listdir", return_value=list(map(str, order))), \
                            patch.object(procs, "_table_proc_stat", side_effect=lambda pid: (world[pid].ppid, world[pid].created, world[pid].exe)), \
                            patch.object(procs.os, "readlink", side_effect=lambda path: world[int(path.split("/")[2])].exe):
                        snapshot = procs._proc_table()
                else:
                    snapshot = procs.parse_ps_table("\n".join(
                        f"{pid} {world[pid].ppid} {world[pid].created} {world[pid].exe}" for pid in order))
                expected = dict(world)
                if delta < 0 and source != "ps":
                    old = world[child_pid]
                    expected[child_pid] = procs.ProcInfo(old.pid, 0, old.created, old.exe)
                self.assertEqual(expected, snapshot.identified)
                self.assertEqual(set(), snapshot.unidentified)
                for row in world.values():
                    self.assertEqual("same", snapshot.observe(row.as_dict()).value)
        self.assertEqual(54, cases)
