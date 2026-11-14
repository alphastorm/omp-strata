"""Record entry and attribution boundaries with no host census or process effects."""
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata import cli, lifecycle, procs, remote
from omp_strata.common import atomic_write_json, read_json
from omp_strata.layout import Layout
from omp_strata.profile import Profile
from tests.candidate import PROFILE
from tests.unit.test_profile import single_gpu_data


def complete_table(rows=(), *, unidentified=()):
    """A reader-contract value: every fake enumerated PID is accounted for, including readable self."""
    import os
    identified = dict(rows)
    identified.setdefault(os.getpid(), procs.ProcInfo(os.getpid(), 0, "0", "/host-free/reader"))
    return procs._checked_table(identified, set(unidentified))


class EvidenceFixture(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        data = single_gpu_data()
        data["server"].update(port=65432, stop_timeout_s=0)
        self.layout = Layout(Path(directory), Profile(PROFILE, data))
        self.world, self.ended = {}, []
        self.layout.run_record.parent.mkdir(parents=True, exist_ok=True)
        self.install = {"profile_fingerprint": self.layout.profile.fingerprint}
        atomic_write_json(self.layout.install_record, self.install)
        self.enterContext(patch.object(lifecycle, "process_table", side_effect=lambda: complete_table(self.world)))
        self.enterContext(patch.object(lifecycle, "port_in_use", return_value=False))

    def process(self, pid=20, created="old", owned=True):
        return procs.ProcInfo(pid, 1, created, str(self.layout.strata / "engine") if owned else "/foreign/engine")

    def terminate(self, proc, timeout):
        current = self.world.get(proc.pid)
        if current and not procs.same_identity(current, proc.as_dict()):
            raise PermissionError("pid now belongs to another process")
        self.ended.append(proc)
        self.world.pop(proc.pid, None)
        return True


class RecordEntryTests(EvidenceFixture):
    def test_dangling_record_link_is_unreadable_not_absent(self):
        for path in (self.layout.run_record, self.layout.install_record):
            with self.subTest(record=path.name):
                path.unlink(missing_ok=True)
                path.symlink_to(path.parent / "missing-record-target")
                root = lifecycle.verdict(self.layout)
                self.assertEqual("unreadable-record", root.row)
                self.assertFalse(root.idle or root.quiescent)
                with patch.object(cli, "_layout", return_value=self.layout), patch.object(cli.install_mod, "install") as install:
                    with self.assertRaises(lifecycle.LifecycleError):
                        cli.cmd_install(SimpleNamespace(idle_generation=None))
                    install.assert_not_called()
                path.unlink()


class AttributionQuestionTests(EvidenceFixture):
    def test_parent_segments_cannot_attribute_a_path_outside_runtime(self):
        self.world[20] = procs.ProcInfo(20, 1, "old", str(self.layout.strata / ".." / "foreign" / "engine"))
        self.assertEqual({}, lifecycle.verdict(self.layout).live)

    def test_listener_command_errors_are_wrapped_and_never_admit(self):
        errors = (OSError("denied"), subprocess.TimeoutExpired("lsof", 5),
                  subprocess.CalledProcessError(1, "lsof"), ValueError("bad owner"),
                  UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid"))
        for error in errors:
            with self.subTest(error=type(error).__name__), patch.object(lifecycle, "port_in_use", return_value=True), \
                    patch.object(remote.sys, "platform", "darwin"), patch.object(remote.subprocess, "run", side_effect=error):
                root = lifecycle.verdict(self.layout)
                self.assertEqual("port-held", root.row)
                self.assertFalse(root.idle or root.quiescent)
                self.assertIn("PID unavailable", root.refusal)


class EvidenceEntryWalk(EvidenceFixture):
    def test_each_record_entry_kind_is_absent_readable_or_unreadable(self):
        import os
        kinds = ("absent", "file", "link", "dangling", "directory", "loop", "fifo")
        cases = 0
        for path in (self.layout.run_record, self.layout.install_record):
            for kind in kinds:
                with self.subTest(record=path.name, kind=kind):
                    path.unlink(missing_ok=True)
                    target = path.with_name(path.name + ".target")
                    target.write_text("{}")
                    if kind == "file":
                        path.write_text("{}")
                    elif kind == "link":
                        path.symlink_to(target)
                    elif kind == "dangling":
                        path.symlink_to(path.with_name("absent-target"))
                    elif kind == "directory":
                        path.mkdir()
                    elif kind == "loop":
                        path.symlink_to(path)
                    elif kind == "fifo":
                        if not hasattr(os, "mkfifo"):
                            continue
                        os.mkfifo(path)
                    try:
                        def load(record):
                            if kind == "fifo" and record == path:
                                self.fail("nonregular evidence was opened")
                            return read_json(record)
                        with patch.object(lifecycle, "_read_record", side_effect=load):
                            root = lifecycle.verdict(self.layout)
                        unreadable = kind not in ("absent", "file", "link")
                        self.assertEqual(unreadable, root.row == "unreadable-record")
                        self.assertEqual(not unreadable, root.quiescent)
                        cases += 1
                    finally:
                        if kind == "directory":
                            path.rmdir()
                        else:
                            path.unlink(missing_ok=True)
        self.assertEqual(14 if hasattr(os, "mkfifo") else 12, cases)


class SnapshotAncestryTests(EvidenceFixture):
    def test_unknown_parent_blocks_ancestry_without_hiding_runtime_identity(self):
        from tests.unit.test_process_table import SnapshotSource, windows_reader
        cutoff = 116444736000000000 + 1234567890
        reader = windows_reader(SnapshotSource(count=1), cutoff + 1)
        reader.__globals__["info"] = lambda pid, *, ppid: procs.ProcInfo(
            pid, ppid, str(cutoff + 1), str(self.layout.strata / "engine"))
        parent = procs.ProcInfo(1, 0, str(cutoff - 10), "/outside/server")
        self.world.update({1: parent, **reader().identified})
        atomic_write_json(self.layout.run_record, dict(self.install, state="ready", server=parent.as_dict()))
        with patch.object(procs, "WINDOWS", True):
            root = lifecycle.verdict(self.layout)
        self.assertEqual(0, self.world[10].ppid)
        self.assertNotIn(10, root.under)
        self.assertNotIn("descendant[10]", root.live)
        self.assertIn("unrecorded[10]", root.live)
        self.assertFalse(root.idle or root.quiescent)


class UnidentifiedRoleWalk(EvidenceFixture):
    def test_every_recorded_role_obeys_the_four_reader_outcomes_in_every_state(self):
        import itertools
        import time
        began = time.monotonic()
        cases = 0
        states = (None, "launching", "starting", "ready", "exited", "stopped", "stop_incomplete")
        roles = ("wrapper", "server", "engine", "server_tree[0]", "launcher")
        for role, state, outcome, mismatch in itertools.product(
                roles, states, ("same", "another-process", "not-enumerated", "cannot-say"), (False, True)):
            with self.subTest(role=role, state=state, outcome=outcome, mismatched=mismatch):
                process = self.process(owned=False)
                run = dict(self.install, state=state)
                if role == "server_tree[0]":
                    run["server_tree"] = [process.as_dict()]
                else:
                    run[role] = process.as_dict()
                atomic_write_json(self.layout.run_record, run)
                atomic_write_json(self.layout.install_record,
                                  dict(self.install, profile_fingerprint="another") if mismatch else self.install)
                rows = {process.pid: process} if outcome == "same" else {}
                if outcome == "another-process":
                    rows[process.pid] = self.process(created="replacement", owned=False)
                # Unreadable unrelated system PIDs do not supply ownership evidence for every root.
                unknown = {999, process.pid} if outcome == "cannot-say" else {999}
                with patch.object(lifecycle, "process_table", return_value=complete_table(rows, unidentified=unknown)):
                    root = lifecycle.verdict(self.layout)
                    self.assertEqual(outcome == "cannot-say", root.row == "unreadable-table")
                    owned = outcome == "same" and role != "launcher"
                    self.assertEqual({process.pid} if owned else set(), {p.pid for p in root.live.values()})
                    self.assertEqual(not owned and state != "launching" and outcome != "cannot-say", root.quiescent)
                    if outcome == "cannot-say":
                        self.assertFalse(root.idle)
                        self.assertEqual([role], root.details["unidentified_records"])
                        self.assertEqual("degraded", lifecycle.status(self.layout)["state"])
                        with patch.object(lifecycle, "verify_install_fast", side_effect=AssertionError("admitted")):
                            with self.assertRaises(lifecycle.LifecycleError):
                                lifecycle.start(self.layout, tool_argv=["fixture"], log=None)
                        with patch.object(lifecycle.ProcessJob, "scan", side_effect=AssertionError("admitted")):
                            with self.assertRaises(lifecycle.LifecycleError):
                                lifecycle.idle_generation(self.layout)
                        with patch.object(cli, "_layout", return_value=self.layout), patch.object(cli.install_mod, "install") as install:
                            with self.assertRaises(lifecycle.LifecycleError):
                                cli.cmd_install(SimpleNamespace(idle_generation=None))
                            install.assert_not_called()
                cases += 1
        self.assertEqual(280, cases)
        print(f"recorded-role reader-outcome model: {cases} cases in {time.monotonic() - began:.3f}s")
