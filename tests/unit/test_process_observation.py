"""Closed comparison cells and source-specific uncertainty, without host process effects."""
import io
import itertools
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata import procs
from tests.unit import test_process_table as fixtures
from tests.unit.test_process_table import SnapshotSource, windows_reader


class ComparisonCells(unittest.TestCase):
    def observe(self, live_stamp, recorded_stamp, live_exe="/engine", recorded_exe="/engine", windows=False):
        with patch.object(procs, "WINDOWS", windows), patch.object(procs.os, "getpid", return_value=10):
            table = procs._checked_table({10: procs.ProcInfo(10, 0, "1", "/self"),
                                          11: procs.ProcInfo(11, 0, live_stamp, live_exe)}, set())
            return table.observe({"pid": 11, "created": recorded_stamp, "exe": recorded_exe})

    def test_equal_stamp_equal_executable_is_same(self):
        for stamp in ("101", "starttime:101", "calendar text", "opaque"):
            self.assertIs(procs.Presence.SAME, self.observe(stamp, stamp))

    def test_equal_procfs_stamp_after_reboot_is_indistinguishable(self):
        # There is no boot identity in the record: a replacement can repeat all three fields.
        previous_boot = procs.ProcInfo(57, 1, "starttime:1234", "/runtime/engine")
        current_boot = procs.ProcessTable({57: procs.ProcInfo(57, 1, "starttime:1234", "/runtime/engine")}, set())
        with patch.object(procs, "WINDOWS", False):
            self.assertIs(procs.Presence.SAME, current_boot.observe(previous_boot.as_dict()))

    def test_missing_live_stamp_is_unknown(self):
        self.assertIs(procs.Presence.UNKNOWN, self.observe("", "starttime:102", recorded_exe="/other"))

    def test_equal_stamp_changed_executable_is_unknown(self):
        for stamp in ("101", "starttime:101", "calendar text", "opaque"):
            self.assertIs(procs.Presence.UNKNOWN, self.observe(stamp, stamp, recorded_exe="/other"))

    def test_distinct_counter_stamps_prove_reuse(self):
        for prefix, same_exe in itertools.product(("", "starttime:"), (False, True)):
            self.assertIs(procs.Presence.OTHER,
                          self.observe(prefix + "101", prefix + "102", recorded_exe="/engine" if same_exe else "/other"))

    def test_different_unordered_stamps_same_executable_are_unknown(self):
        pairs = (("Fri Nov 13 10:00:00 2026", "Fri Nov 13 18:00:00 2026"),
                 ("101", "starttime:101"), ("opaque", "other opaque"))
        for left, right in pairs:
            self.assertIs(procs.Presence.UNKNOWN, self.observe(left, right))

    def test_different_unordered_stamps_changed_executable_are_unknown(self):
        for left, right in (("calendar A", "calendar B"), ("101", "starttime:101"), ("opaque", "other")):
            self.assertIs(procs.Presence.UNKNOWN, self.observe(left, right, recorded_exe="/other"))

    def test_in_place_exec_with_rerendered_calendar_stamp_is_unknown(self):
        self.assertIs(procs.Presence.UNKNOWN, self.observe(
            "Fri Nov 13 18:00:00 2026", "Fri Nov 13 10:00:00 2026",
            live_exe="/runtime/new-engine", recorded_exe="/runtime/old-engine"))

    def test_ps_and_procfs_records_are_unknown_in_both_directions(self):
        for reverse, same_exe in itertools.product((False, True), repeat=2):
            stamps = ("Fri Nov 13 10:00:00 2026", "starttime:101")
            with self.subTest(reverse=reverse, same_exe=same_exe):
                self.assertIs(procs.Presence.UNKNOWN, self.observe(
                    *(stamps[::-1] if reverse else stamps), recorded_exe="/engine" if same_exe else "/other"))

    def test_leading_zero_stamp_is_unrecognised(self):
        for prefix, reverse in itertools.product(("", "starttime:"), (False, True)):
            stamps = (prefix + "00101", prefix + "101")
            self.assertIs(procs.Presence.UNKNOWN, self.observe(*(stamps[::-1] if reverse else stamps)))

    def test_comparison_cells_partition_the_generated_domain(self):
        stamps = (("101", "windows"), ("102", "windows"), ("starttime:101", "procfs"), ("starttime:102", "procfs"),
                  ("Fri Nov 13 10:00:00 2026", None), ("Fri Nov 13 18:00:00 2026", None),
                  ("opaque", None), ("00101", None), ("starttime:00101", None))
        outcomes = (procs.Presence.SAME, procs.Presence.UNKNOWN, procs.Presence.OTHER,
                    procs.Presence.UNKNOWN, procs.Presence.UNKNOWN)
        cases, reached = 0, set()
        executables = ("/engine", "/other", "/ENGINE", "/runtime/\ufffdengine", " (deleted)")
        for (left, family_left), (right, family_right), live_exe, recorded_exe, windows in itertools.product(
                stamps, stamps, executables, executables, (False, True)):
            with self.subTest(left=left, right=right, live_exe=live_exe, recorded_exe=recorded_exe, windows=windows):
                cases += 1
                live_text = live_exe.lower() if windows else live_exe.removesuffix(" (deleted)")
                recorded_text = recorded_exe.lower() if windows else recorded_exe.removesuffix(" (deleted)")
                readable = all(text and "\ufffd" not in text for text in (live_text, recorded_text))
                if not readable:
                    self.assertIs(procs.Presence.UNKNOWN,
                                  self.observe(left, right, live_exe, recorded_exe, windows))
                    reached.add("unreadable")
                    continue
                same_stamp = left == right
                same_exe = live_text == recorded_text
                counter = family_left is not None and family_left == family_right
                cells = (same_stamp and same_exe, same_stamp and not same_exe,
                         not same_stamp and counter,
                         not same_stamp and not counter and same_exe,
                         not same_stamp and not counter and not same_exe)
                self.assertEqual(1, sum(cells))
                cell = cells.index(True)
                reached.add(cell)
                self.assertIs(outcomes[cell], self.observe(left, right, live_exe, recorded_exe, windows))
        self.assertEqual(4050, cases)
        self.assertEqual(set(range(5)) | {"unreadable"}, reached)


@unittest.skipIf(procs.WINDOWS, "POSIX executable-link boundary; native Windows is unexercised")
class ProcfsExecutableTests(unittest.TestCase):
    def test_procfs_rows_require_the_kernel_executable_link(self):
        text = "10 1 Fri Nov 13 12:34:56 2026 /self\n11 10 Fri Nov 13 12:34:56 2026 /fallback/engine\n"
        for error in (FileNotFoundError("gone but not reaped"), PermissionError("non-dumpable")):
            with self.subTest(error=type(error).__name__), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", side_effect=lambda p: p == "/proc" or p == "/proc/10/exe"), \
                    patch.object(procs.os, "readlink", side_effect=lambda p: "/self" if p == "/proc/10/exe" else self.fail_link(error)):
                table = procs.parse_ps_table(text)
                self.assertEqual({11}, table.unidentified)
                self.assertNotIn(11, table.identified)
                self.assertIs(procs.Presence.UNKNOWN, table.observe({"pid": 11, "created": "Fri Nov 13 12:34:56 2026",
                                                                   "exe": "/runtime/engine"}))

    @staticmethod
    def fail_link(error):
        raise error

    def test_replaced_running_binary_keeps_its_identity(self):
        stamp = "Fri Nov 13 12:34:56 2026"
        for live_deleted, recorded_deleted in itertools.product((False, True), repeat=2):
            with self.subTest(live_deleted=live_deleted, recorded_deleted=recorded_deleted), \
                    patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os.path, "exists", return_value=True), \
                    patch.object(procs.os, "readlink", side_effect=lambda p: "/self" if p == "/proc/10/exe" else
                                 "/runtime/engine" + (" (deleted)" if live_deleted else "")):
                table = procs.parse_ps_table(f"10 1 {stamp} /self\n11 10 {stamp} engine\n")
                self.assertIs(procs.Presence.SAME, table.observe({"pid": 11, "created": stamp,
                    "exe": "/runtime/engine" + (" (deleted)" if recorded_deleted else "")}))

    def test_unlinked_image_comm_record_is_conservative(self):
        stamp = "Fri Nov 13 10:00:00 2026"
        for comm, rerendered in itertools.product(("/runtime/engine", "engine"), (False, True)):
            with self.subTest(comm=comm, rerendered=rerendered), \
                    patch.object(procs.os, "kill"), patch.object(procs, "_ps", return_value=(1, stamp, comm)), \
                    patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", side_effect=lambda path: path == "/proc"), \
                    patch.object(procs.os, "readlink", side_effect=lambda path:
                                 "/self" if path == "/proc/10/exe" else "/runtime/engine (deleted)") as link:
                # main's unchanged info() keeps comm when exists follows an unlinked image's dangling link.
                recorded = procs.info(11)
                self.assertEqual(comm, recorded.exe)
                link.assert_not_called()
                live_stamp = "Fri Nov 13 18:00:00 2026" if rerendered else stamp
                table = procs.parse_ps_table(f"10 1 {stamp} /self\n11 1 {live_stamp} {comm}\n")
                self.assertEqual("/runtime/engine (deleted)", table.identified[11].exe)
                expected = procs.Presence.SAME if comm == "/runtime/engine" and not rerendered else procs.Presence.UNKNOWN
                self.assertIs(expected, table.observe(recorded.as_dict()))


@unittest.skipIf(procs.WINDOWS, "POSIX procfs boundary; native Windows is unexercised")
class ProcfsSnapshotTests(unittest.TestCase):
    def test_procfs_identity_rechecks_start_stamp_after_link(self):
        first = (1, "starttime:100", "engine")
        cases = ((first, True), ((99, "starttime:100", "renamed"), True),
                 ((1, "starttime:200", "replacement"), False), (None, False))
        for after, stable in cases:
            events, reads = [], {}

            def stat(pid):
                events.append(("stat", pid))
                reads[pid] = reads.get(pid, 0) + 1
                return (0, "starttime:1", "self") if pid == 10 else first if reads[pid] == 1 else after

            def link(path):
                pid = int(path.split("/")[2])
                events.append(("link", pid))
                return "/self" if pid == 10 else "/runtime/engine"

            with self.subTest(after=after), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os, "listdir", return_value=["10", "11"]), \
                    patch.object(procs, "_table_proc_stat", side_effect=stat), \
                    patch.object(procs.os, "readlink", side_effect=link):
                table = procs._proc_table()
                self.assertEqual(set() if stable else {11}, table.unidentified)
                self.assertEqual({10, 11} if stable else {10}, set(table.identified))
                recorded = {"pid": 11, "created": "starttime:100" if stable else "starttime:200", "exe": "/runtime/engine"}
                self.assertIs(procs.Presence.SAME if stable else procs.Presence.UNKNOWN, table.observe(recorded))
                self.assertEqual([("stat", 10), ("link", 10), ("stat", 10),
                                  ("stat", 11), ("link", 11), ("stat", 11)], events)


@unittest.skipIf(procs.WINDOWS, "POSIX ps boundary; native Windows is unexercised")
class PsRowShapeTests(unittest.TestCase):
    def test_ps_creation_tokens_have_lstart_shape(self):
        invalid = ("bad bad bad bad bad /engine",
                   "Fri Nov 13 12:34:56 /runtime/path with spaces/engine",
                   "123 Nov 13 12:34:56 2026 /engine",
                   "Fri 11 13 12:34:56 2026 /engine",
                   "Fri Nov x 12:34:56 2026 /engine",
                   "Fri Nov 123 12:34:56 2026 /engine",
                   "Fri Nov 13 1:34:56 2026 /engine",
                   "Fri Nov 13 12:3:56 2026 /engine",
                   "Fri Nov 13 12:34:5 2026 /engine",
                   "Fri Nov 13 12-34-56 2026 /engine",
                   "Fri Nov 13 12:34:56 26 /engine",
                   "Fri Nov 13 12:34:56 20x6 /engine")
        valid = ("Freitag Mär 13 12:34:56 2026 /runtime/path with spaces/engine",
                 "Fri Nov  3 12:34:56 2026 /runtime/path with spaces/engine")
        for row in (*invalid, *valid):
            with self.subTest(row=row), patch.object(procs.os, "getpid", return_value=10), \
                    patch.object(procs.os.path, "exists", return_value=False):
                table = procs.parse_ps_table("10 1 Fri Nov 13 12:34:56 2026 /self\n11 1 " + row + "\n")
                self.assertEqual({11} if row in invalid else set(), table.unidentified)
                self.assertEqual({10} if row in invalid else {10, 11}, set(table.identified))
                if row in valid:
                    self.assertEqual("/runtime/path with spaces/engine", table.identified[11].exe)


class DuplicateSnapshot(SnapshotSource):
    def __init__(self, pids):
        super().__init__(count=len(pids))
        self.pids = pids

    def row(self, entry):
        index = self.index
        present = super().row(entry)
        if present:
            entry.th32ProcessID = self.pids[index]
        return present


@unittest.skipIf(procs.WINDOWS, "POSIX sources and fake Windows are walked together")
class DuplicatePidWalk(unittest.TestCase):
    def test_every_source_marks_duplicate_pids_unidentified(self):
        cases = 0
        for source, duplicate_self, reverse in itertools.product(("windows", "ps", "procfs"), (False, True), (False, True)):
            with self.subTest(source=source, duplicate_self=duplicate_self, reverse=reverse), \
                    patch.object(procs.os, "getpid", return_value=10):
                cases += 1
                pids = [10, 11, 10 if duplicate_self else 11]
                if reverse:
                    pids.reverse()
                if source == "windows":
                    load = windows_reader(DuplicateSnapshot(pids), fixtures.SnapshotBoundaryTests.cutoff - 20_000_000)
                elif source == "ps":
                    text = "".join(f"{pid} 1 Fri Nov 13 12:34:56 2026 /engine\n" for pid in pids)
                    load = lambda: procs.parse_ps_table(text)
                else:
                    load = procs._proc_table
                def stat_file(path, **kwargs):
                    return io.StringIO("10 (engine) S 1 " + "0 " * 17 + "100")
                with patch.object(procs.os.path, "exists", return_value=source == "procfs"), \
                        patch.object(procs.os, "listdir", return_value=[str(pid) for pid in pids]), \
                        patch.object(procs.os, "readlink", return_value="/engine"), patch("builtins.open", side_effect=stat_file):
                    if duplicate_self:
                        with self.assertRaises(procs.TableUnavailable):
                            load()
                    else:
                        table = load()
                        self.assertEqual({11}, table.unidentified)
                        self.assertNotIn(11, table.identified)
        self.assertEqual(12, cases)


class ParentClockTests(unittest.TestCase):
    @unittest.skipIf(procs.WINDOWS, "POSIX ps boundary; native Windows is unexercised")
    def test_ps_daylight_saving_repeat_keeps_the_real_parent(self):
        text = "10 1 Sun Nov 1 01:50:00 2026 /parent\n11 10 Sun Nov 1 01:10:00 2026 /child\n"
        with patch.object(procs.os, "getpid", return_value=10), patch.object(procs.os.path, "exists", return_value=False):
            self.assertEqual(10, procs.parse_ps_table(text).identified[11].ppid)

    def test_windows_reuse_inside_capture_walk_clock_gap_clears_parent(self):
        source = SnapshotSource(count=2)
        base = fixtures.SnapshotBoundaryTests.cutoff
        reader = windows_reader(source, base + 10_000_000)
        def clock():
            after_capture = "snapshot" in source.events
            source.events.append("clock")
            return 123456789000 + (3_000_000_000 if after_capture else 0)
        reader.__globals__["time"] = SimpleNamespace(time_ns=clock)
        reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(
            pid, ppid, str(base - 20_000_000 if pid == 10 else base + 10_000_000), "/engine")
        table = reader()
        self.assertEqual(0, table.identified[11].ppid)
        self.assertLess(source.events.index("clock"), source.events.index("snapshot"))

    def test_windows_creation_granularity_margin_is_conservative(self):
        for delta in (-10_000_001, -10_000_000, -9_999_999, -1, 0, 1):
            with self.subTest(delta=delta):
                source = SnapshotSource(count=2)
                base = fixtures.SnapshotBoundaryTests.cutoff
                reader = windows_reader(source, base + delta)
                reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(
                    pid, ppid, str(base - 20_000_000 if pid == 10 else base + delta), "/engine")
                self.assertEqual(0 if delta >= -10_000_000 else 1, reader().identified[11].ppid)


class ObservationPortabilityTests(unittest.TestCase):
    def test_posix_boundaries_are_skipped_on_windows(self):
        namespace = {"__name__": "observation_windows_boundaries", "__file__": __file__}
        with patch.object(procs, "WINDOWS", True), patch.dict(procs.__dict__):
            for name in ("parse_ps_table", "_proc_table", "_table_proc_stat", "_table_identity"):
                procs.__dict__.pop(name, None)
            exec(compile(Path(__file__).read_text(), __file__, "exec"), namespace)
            loader = unittest.TestLoader()
            suite = unittest.TestSuite(loader.loadTestsFromTestCase(namespace[name]) for name in
                                       ("ProcfsExecutableTests", "ProcfsSnapshotTests", "PsRowShapeTests", "DuplicatePidWalk"))
            suite.addTest(namespace["ParentClockTests"]("test_ps_daylight_saving_repeat_keeps_the_real_parent"))
            count = suite.countTestCases()
            result = unittest.TestResult()
            suite.run(result)
        self.assertEqual([], result.errors)
        self.assertEqual([], result.failures)
        self.assertEqual(count, len(result.skipped))
