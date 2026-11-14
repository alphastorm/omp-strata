"""Closed comparison cells and source-specific uncertainty, without host process effects."""
import io
import itertools
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

    def test_different_unordered_stamps_changed_executable_prove_reuse(self):
        for left, right in (("calendar A", "calendar B"), ("101", "starttime:101"), ("opaque", "other")):
            self.assertIs(procs.Presence.OTHER, self.observe(left, right, recorded_exe="/other"))

    def test_leading_zero_stamp_is_unrecognised(self):
        for prefix, reverse in itertools.product(("", "starttime:"), (False, True)):
            stamps = (prefix + "00101", prefix + "101")
            self.assertIs(procs.Presence.UNKNOWN, self.observe(*(stamps[::-1] if reverse else stamps)))

    def test_comparison_cells_partition_the_generated_domain(self):
        stamps = (("101", "windows"), ("102", "windows"), ("starttime:101", "procfs"), ("starttime:102", "procfs"),
                  ("Fri Nov 13 10:00:00 2026", None), ("Fri Nov 13 18:00:00 2026", None),
                  ("opaque", None), ("00101", None), ("starttime:00101", None))
        outcomes = (procs.Presence.SAME, procs.Presence.UNKNOWN, procs.Presence.OTHER,
                    procs.Presence.UNKNOWN, procs.Presence.OTHER)
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
