"""Record entry and attribution boundaries with no host census or process effects."""
from pathlib import Path
import contextlib
import itertools
import os
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


_native_matches = procs.matches


def native_matches(process, recorded):
    """Exercise the unchanged individual-reader comparison with only its native lookup substituted."""
    with patch.object(procs, "info", return_value=process):
        return _native_matches(recorded)


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

    def process(self, pid=20, created="20", owned=True):
        return procs.ProcInfo(pid, 1, created, str(self.layout.strata / "engine") if owned else "/foreign/engine")

    def terminate(self, proc, timeout):
        current = self.world.get(proc.pid)
        if current and native_matches(current, proc.as_dict()) is None:
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
                    rows[process.pid] = self.process(created="21", owned=False)
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


class RecoveryAdviceTests(EvidenceFixture):
    def stop_fake(self):
        with patch.object(lifecycle, "WINDOWS", False), patch.object(procs, "WINDOWS", False), \
                patch.object(procs, "info", side_effect=lambda pid: self.world.get(pid)), \
                patch.object(procs, "descendants", return_value=[]) as descendants, \
                patch.object(procs, "terminate", side_effect=self.terminate):
            result = lifecycle.stop(self.layout, log=None, locked=True)
        return result, descendants

    def assert_manual(self, advice, *pids):
        for pid in pids:
            self.assertIn(f"pid {pid}", advice)
        for action in ("inspect", "end", "by hand", "`status`"):
            self.assertIn(action, advice)
        self.assertNotIn("run `stop`", advice)

    def test_stop_does_not_resolve_an_unrecorded_runtime_survivor(self):
        for recorded in (False, True):
            with self.subTest(recorded=recorded):
                self.world[77] = self.process(pid=77)
                self.layout.run_record.unlink(missing_ok=True)
                if recorded:
                    atomic_write_json(self.layout.run_record, {"state": "exited"})
                before = lifecycle.verdict(self.layout)
                result, _ = self.stop_fake()
                self.assertEqual("stopped", result["state"])
                self.assertEqual([], self.ended)
                root = lifecycle.verdict(self.layout)
                self.assertEqual("orphans", root.row)
                self.assertFalse(root.quiescent)
                self.assert_manual(root.refusal, 77)
                self.assert_manual(before.refusal, 77)

    def test_engine_and_tree_member_children_are_not_selected_by_legacy_stop(self):
        for role in ("engine", "server_tree"):
            with self.subTest(role=role):
                parent = self.process(owned=False)
                child = procs.ProcInfo(77, parent.pid, "77", str(self.layout.strata / "child"))
                self.world = {parent.pid: parent, child.pid: child}
                run = {"state": "exited", role: [parent.as_dict()] if role == "server_tree" else parent.as_dict()}
                atomic_write_json(self.layout.run_record, run)
                before = lifecycle.verdict(self.layout)
                _, descendants = self.stop_fake()
                descendants.assert_not_called()
                self.assertEqual({77}, set(self.world))
                self.assert_manual(lifecycle.verdict(self.layout).refusal, 77)
                self.assert_manual(before.refusal, 77)

    def test_deleted_image_comparison_does_not_promise_legacy_stop_can_select_the_tree(self):
        for role in ("server", "wrapper"):
            for deleted_side in ("live", "recorded"):
                with self.subTest(role=role, deleted_side=deleted_side), patch.object(procs, "WINDOWS", False):
                    parent = self.process(owned=False)
                    recorded = parent.as_dict()
                    if deleted_side == "live":
                        parent = procs.ProcInfo(parent.pid, parent.ppid, parent.created, parent.exe + " (deleted)")
                    else:
                        recorded["exe"] += " (deleted)"
                    child = procs.ProcInfo(77, parent.pid, "77", str(self.layout.strata / "child"))
                    self.world = {parent.pid: parent, child.pid: child}
                    atomic_write_json(self.layout.run_record, {"state": "exited", role: recorded})
                    before = lifecycle.verdict(self.layout)
                    _, descendants = self.stop_fake()
                    descendants.assert_not_called()
                    self.assertEqual({20, 77}, set(self.world))
                    self.assert_manual(lifecycle.verdict(self.layout).refusal, 20, 77)
                    self.assert_manual(before.refusal, 20, 77)

    def test_authenticated_status_does_not_recommend_stop_for_a_stray(self):
        server = self.process(owned=False)
        self.world = {server.pid: server, 77: self.process(pid=77)}
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": server.as_dict()})
        with patch.object(lifecycle, "read_key", return_value="key"), \
                patch.object(lifecycle, "runtime_checks", return_value={"problems": []}), \
                patch.object(procs, "descendants", return_value=[]):
            status = lifecycle.status(self.layout)
        self.assertEqual("degraded", status["state"])
        self.assert_manual("; ".join(status["problems"]), 77)

    def test_ordinary_recorded_server_retains_effective_stop_advice(self):
        server = self.process(owned=False)
        self.world[server.pid] = server
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": server.as_dict()})
        self.assertIn("run `stop`", lifecycle.verdict(self.layout).refusal)
        self.stop_fake()
        self.assertTrue(lifecycle.verdict(self.layout).quiescent)


class SharedGateExecutionWalk(EvidenceFixture):
    def test_stop_executes_the_structural_gate_before_any_effect(self):
        token = "a" * 32
        cases = 0
        for windows, has_token, unpublished, state, proof in itertools.product(
                (False, True), (False, True), (False, True), ("exited", "stopped"), (False, True)):
            with self.subTest(windows=windows, token=has_token, unpublished=unpublished, state=state, proof=proof):
                cases += 1
                run = {"state": state, "unpublished_child": unpublished}
                if has_token:
                    run["tree_token"] = token
                if proof:
                    run["tree_verified_empty"] = token
                atomic_write_json(self.layout.run_record, run)
                refused = has_token and not windows or unpublished and not has_token
                with patch.object(lifecycle, "WINDOWS", windows), patch.object(lifecycle, "ProcessJob") as job, \
                        patch.object(procs, "info", side_effect=AssertionError("unexpected native lookup")), \
                        patch.object(procs, "descendants", side_effect=AssertionError("unexpected native walk")), \
                        patch.object(procs, "terminate", side_effect=AssertionError("unexpected native signal")):
                    job.return_value.token = token
                    job.scan.return_value = {}
                    if refused:
                        with self.assertRaises(lifecycle.LifecycleError) as failure:
                            lifecycle.stop(self.layout, log=None, locked=True)
                        expected = "Windows host" if has_token else "unpublished child lifetime is unknown"
                        self.assertIn(expected, str(failure.exception))
                        self.assertEqual(run, read_json(self.layout.run_record))
                        job.assert_not_called()
                        job.scan.assert_not_called()
                    else:
                        result = lifecycle.stop(self.layout, log=None, locked=True)
                        self.assertEqual("stopped", result["state"])
                        if has_token and not (state == "stopped" and proof):
                            job.assert_called_once_with(token, existing=True)
                            job.return_value.stop.assert_called_once_with(0)
                        else:
                            job.assert_not_called()
                        if has_token and state == "stopped" and proof:
                            job.scan.assert_called_once_with(token, set(), {})
                        else:
                            job.scan.assert_not_called()
        self.assertEqual(32, cases)

    def test_quiescent_candidate_requires_a_fresh_scan_with_and_without_generation_fence(self):
        token = "a" * 32
        run = {"state": "stopped", "tree_token": token, "tree_verified_empty": token}
        generation = lifecycle.sha256_bytes(lifecycle.canonical_json(run))
        for fenced, outcome in itertools.product((False, True), ("empty", "survivor", "error")):
            with self.subTest(fenced=fenced, outcome=outcome), patch.object(lifecycle, "WINDOWS", True):
                atomic_write_json(self.layout.run_record, run)
                self.assertTrue(lifecycle.verdict(self.layout).quiescent)
                with patch.object(lifecycle.ProcessJob, "scan", return_value={} if outcome == "empty" else {77: {}},
                                  side_effect=lifecycle.LifecycleError("fake scan error") if outcome == "error" else None) as scan:
                    if outcome == "empty":
                        self.assertEqual(generation, lifecycle.idle_generation(
                            self.layout, expected=generation if fenced else None, timeout=2.75))
                    else:
                        with self.assertRaises(lifecycle.LifecycleError) as failure:
                            lifecycle.idle_generation(self.layout, expected=generation if fenced else None, timeout=2.75)
                        self.assertIn("fake scan error" if outcome == "error" else "custody is not proved empty",
                                      str(failure.exception))
                    scan.assert_called_once_with(token, set(), {}, timeout=2.75)
                self.assertEqual(run, read_json(self.layout.run_record))


class LaunchingRecoveryWalk(EvidenceFixture):
    stop_fake = RecoveryAdviceTests.stop_fake
    assert_manual = RecoveryAdviceTests.assert_manual
    FENCE = "run `stop` for this root to fence the dispatched wrapper so it cannot start a server"
    MANUAL = ("inspect and end these processes by hand "
              "(unrecorded[77] engine pid 77, unrecorded[78] python pid 78); then run `status` for this root")
    COMBINED_PREFIX = FENCE + " (do not rely on it to end the listed processes); "
    COMBINED = COMBINED_PREFIX + MANUAL
    ROWS = ("launch-unrecorded", "launch-pending", "launch-abandoned")

    def launching(self, row, *, survivors=True, token=False):
        self.world.clear()
        run = {"state": "launching", "launch_id": "old-launch",
               "profile_fingerprint": self.layout.profile.fingerprint}
        launcher = self.process(owned=False)
        if row != "launch-unrecorded":
            run["launcher"] = launcher.as_dict()
        if row == "launch-pending":
            self.world[launcher.pid] = launcher
        if token:
            run["tree_token"] = "a" * 32
        if survivors:
            self.world[77] = self.process(pid=77)
            self.world[78] = procs.ProcInfo(78, 1, "78", str(self.layout.strata / "python"))
        atomic_write_json(self.layout.run_record, run)
        return run

    def test_launch_rows_publish_exact_advice_with_structural_custody_first(self):
        for row, survivors, token, windows in itertools.product(self.ROWS, (False, True), (False, True), (False, True)):
            with self.subTest(row=row, survivors=survivors, token=token, windows=windows), \
                    patch.object(lifecycle, "WINDOWS", windows):
                self.launching(row, survivors=survivors, token=token)
                expected = "reconcile it on its Windows host" if token and not windows else self.COMBINED if survivors else self.FENCE
                root = lifecycle.verdict(self.layout)
                self.assertEqual(row, root.row)
                self.assertTrue(root.problems[0].endswith("; " + expected), root.problems)
                self.assertEqual("pending launch already owns this root; " + expected + " before replacement", root.refusal)
                if token and not windows:
                    self.assertNotIn("`stop`", root.refusal)
                    self.assertNotIn("by hand", root.refusal)

    def test_stop_fences_late_wrapper_before_manual_survivor_cleanup(self):
        for row in self.ROWS:
            with self.subTest(row=row):
                self.launching(row)
                before = lifecycle.verdict(self.layout)
                self.stop_fake()
                self.assertEqual("stopped", read_json(self.layout.run_record)["state"])
                with patch.dict(os.environ, {lifecycle.TREE_TOKEN_ENV: ""}), \
                        patch.object(lifecycle, "FileLock", return_value=contextlib.nullcontext()), \
                        patch.object(lifecycle, "read_key", side_effect=AssertionError("must fence before key")) as key, \
                        patch.object(procs, "info", side_effect=AssertionError("must fence before identity")) as info, \
                        patch.object(lifecycle, "ProcessJob", side_effect=AssertionError("must fence before job")) as job, \
                        patch.object(lifecycle.subprocess, "Popen", side_effect=AssertionError("must not start server")) as spawn:
                    with self.assertRaisesRegex(lifecycle.LifecycleError, "serve generation changed or stopped before launch"):
                        lifecycle.serve(self.layout, log_path=self.layout.logs / "late-wrapper.log", launch_id="old-launch")
                    for native in (key, info, job, spawn):
                        native.assert_not_called()
                self.assertTrue({77, 78}.issubset(self.world))
                orphan = lifecycle.verdict(self.layout)
                self.assertEqual("orphans", orphan.row)
                self.assert_manual(orphan.refusal, 77, 78)
                self.assertIn(self.COMBINED, before.refusal)
                for pid in (77, 78):
                    self.world.pop(pid)
                empty = lifecycle.verdict(self.layout)
                self.assertEqual(("idle", "stopped", True, True),
                                 (empty.row, empty.state, empty.idle, empty.quiescent))

    def test_manual_cleanup_alone_does_not_fence_a_launch(self):
        for row in self.ROWS:
            with self.subTest(row=row):
                self.launching(row)
                for pid in (77, 78):
                    self.world.pop(pid)
                root = lifecycle.verdict(self.layout)
                self.assertEqual(row, root.row)
                self.assertFalse(root.idle or root.quiescent)
                self.assertEqual("launching", read_json(self.layout.run_record)["state"])
                self.assertEqual("pending launch already owns this root; " + self.FENCE + " before replacement", root.refusal)

    def test_unpublished_without_token_precedes_every_launch_row(self):
        for row in self.ROWS:
            with self.subTest(row=row):
                run = self.launching(row)
                atomic_write_json(self.layout.run_record, {**run, "unpublished_child": True})
                root = lifecycle.verdict(self.layout)
                self.assertEqual("custody-unknown", root.row)
                self.assertEqual("unpublished child lifetime is unknown; retain custody for reconciliation", root.refusal)

    def test_waiting_wrapper_is_counted_only_inside_the_ownership_boundary(self):
        for inside in (False, True):
            with self.subTest(inside=inside):
                self.launching("launch-unrecorded", survivors=False)
                exe = str(self.layout.strata / "python") if inside else "/outside/python"
                self.world[78] = procs.ProcInfo(78, 1, "78", exe)
                root = lifecycle.verdict(self.layout)
                self.assertEqual({"unrecorded[78]"} if inside else set(), set(root.live))

    def test_stop_can_end_a_deleted_image_candidate_in_a_mixed_launch_list(self):
        run = self.launching("launch-unrecorded", survivors=False)
        server = self.process(owned=False)
        server = procs.ProcInfo(server.pid, server.ppid, server.created, server.exe + " (deleted)")
        self.world = {server.pid: server, 77: self.process(pid=77)}
        atomic_write_json(self.layout.run_record, {**run, "server": server.as_dict()})
        expected = (self.COMBINED_PREFIX + "inspect and end these processes by hand "
                    "(server engine (deleted) pid 20, unrecorded[77] engine pid 77); then run `status` for this root")
        with patch.object(procs, "WINDOWS", False):
            before = lifecycle.verdict(self.layout)
            self.stop_fake()
            after = lifecycle.verdict(self.layout)
        self.assertEqual({77}, set(self.world))
        self.assertEqual(["20"], [proc.created for proc in self.ended])
        self.assertEqual("orphans", after.row)
        self.assertEqual({"unrecorded[77]"}, set(after.live))
        self.assert_manual(after.refusal, 77)
        self.assertNotIn("pid 20", after.refusal)
        self.assertIn(expected, before.refusal)
        self.assertTrue(before.problems[0].endswith("; " + expected), before.problems)
