"""The lifecycle's closed state table, walked (docs/OPERATIONS.md, "Lifecycle states").

The walk crosses everything the code can write (install record, run record state and flags) with everything the
process table can show (which recorded processes live, unrecorded processes of the root, a pid reused by a stranger,
a failed read, the port), using a process world kept in memory, and checks that status, start, stop and
idle_generation act on one verdict and that every row of the closed table is reached.
"""
from __future__ import annotations

import ast
import contextlib
import itertools
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata import cli, lifecycle, nvfp4, procs, remote
from omp_strata.common import atomic_write_json, read_json
from omp_strata.layout import Layout
from omp_strata.profile import Profile
from tests.candidate import PROFILE
from tests.mock.test_remote_support import free_port
from tests.unit.test_profile import single_gpu_data

FULL = ("wrapper", "server", "engine", "server_tree")
TOKEN = "a" * 32
# Rows whose `stop` refuses on this platform: custody unknown, a publishing wrapper, an unreadable record, and (off
# Windows) any process-tree record. An unreadable table ends verified recorded processes, then refuses.
STOP_REFUSES = {"unreadable-record", "custody-unknown", "wrapper-publishing", "unreadable-table"}


class Admitted(Exception):
    """`start` passed every root check and reached the install check."""


def ident(pid: int, ppid: int, exe: str) -> procs.ProcInfo:
    return procs.ProcInfo(pid, ppid, f"created-{pid}", exe)


class StateTableWalk(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        data = single_gpu_data()
        data["server"].update(port=free_port(), stop_timeout_s=0)
        self.layout = Layout(Path(directory) / "root", Profile(PROFILE, data))
        self.layout.run_record.parent.mkdir(parents=True, exist_ok=True)
        engine = str(self.layout.strata / "engine" / "strata")
        self.p = {"launcher": ident(10, 1, "/tools/python3"), "wrapper": ident(11, 1, "/tools/python3"),
                  "server": ident(12, 11, "/tools/python3"), "server_tree": ident(13, 12, "/usr/bin/python3"),
                  "engine": ident(14, 13, engine)}
        self.engine_exe = engine

    def record(self, template):
        fingerprint = self.layout.profile.fingerprint
        base = {"profile_fingerprint": fingerprint, "runtime_identity_sha256": "a" * 64, "launch_id": "walked"}
        full: dict = {role: self.p[role].as_dict() for role in ("wrapper", "server", "engine")}
        full["server_tree"] = [self.p["server_tree"].as_dict()]
        return {
            "absent": (None, ()),
            "unreadable": ("{", ()),
            "launching": (dict(base, state="launching", launcher=self.p["launcher"].as_dict()), ("launcher",)),
            "publishing": (dict(base, state="starting", unpublished_child=True, wrapper=full["wrapper"]),
                           ("wrapper",)),
            "starting": (dict(base, state="starting", wrapper=full["wrapper"], server=full["server"]),
                         ("wrapper", "server")),
            "ready": (dict(base, state="ready", **full), FULL),
            "exited-0": (dict(base, state="exited", exit_code=0, **full), FULL),
            "exited-1": (dict(base, state="exited", exit_code=1, **full), FULL),
            "stopped": (dict(base, state="stopped", **full), FULL),
            "stop_incomplete": (dict(base, state="stop_incomplete", **full), FULL),
            "job-ready": (dict(base, state="ready", tree_token=TOKEN, **full), FULL),
            "job-stopped": (dict(base, state="stopped", tree_token=TOKEN, tree_verified_empty=TOKEN, **full), FULL),
        }[template]

    def write(self, path, value):
        if value is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")

    @staticmethod
    def owners(world, alive_roles, p, runtime_pids):
        """Ground truth, independent of the verdict: recorded processes alive, their current descendants, and every
        process running the root's runtime. A launcher is not a process of the root; it only makes a launch pending."""
        roots = {p[role].pid for role in alive_roles if role != "launcher"}
        found, frontier = set(roots), list(roots)
        while frontier:
            parent = frontier.pop()
            for proc in world.values():
                if proc.ppid == parent and proc.pid not in found:
                    found.add(proc.pid)
                    frontier.append(proc.pid)
        return found | runtime_pids

    def test_every_combination_lands_in_one_row_and_every_consumer_acts_on_it(self):
        world: dict[int, procs.ProcInfo] = {}
        readable = {"value": True}
        port = {"held": False}
        terminated: list[int] = []

        def table():
            if not readable["value"]:
                raise procs.TableUnavailable("fixture process table unreadable")
            return dict(world)

        def matches(recorded):
            proc = world.get(int(recorded["pid"])) if recorded else None
            return proc if proc is not None and procs.same_identity(proc, recorded) else None

        def terminate(proc, timeout):
            terminated.append(proc.pid)
            world.pop(proc.pid, None)
            return True

        def fast_write(path, value):
            Path(path).write_text(json.dumps(value), encoding="utf-8")

        def not_installed(_layout):
            raise Admitted

        patches = (
            patch.object(lifecycle, "process_table", side_effect=table),
            patch.object(lifecycle.procs, "matches", side_effect=matches),
            patch.object(lifecycle.procs, "terminate", side_effect=terminate),
            patch.object(lifecycle.procs, "descendants",
                         side_effect=lambda pid: [proc for proc in world.values() if proc.ppid == pid]),
            patch.object(lifecycle, "port_in_use", side_effect=lambda *args: port["held"]),
            patch.object(remote, "listener_pids", return_value={99}),
            patch.object(lifecycle, "read_key", return_value="x" * 32),
            patch.object(lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}),
            patch.object(lifecycle, "verify_install_fast", side_effect=not_installed),
            patch.object(lifecycle.ProcessJob, "scan", return_value={}),
            patch.object(lifecycle, "atomic_write_json", side_effect=fast_write),
        )
        for active in patches:
            self.enterContext(active)
        installs = {"absent": None, "this": {"profile_fingerprint": self.layout.profile.fingerprint,
                                             "runtime_identity_sha256": "a" * 64},
                    "other": {"profile_fingerprint": "0" * 64, "runtime_identity_sha256": "a" * 64},
                    "stale": {"profile_fingerprint": self.layout.profile.fingerprint,
                              "runtime_identity_sha256": "b" * 64}}
        templates = ("absent", "unreadable", "launching", "publishing", "starting", "ready", "exited-0", "exited-1",
                     "stopped", "stop_incomplete", "job-ready", "job-stopped")
        seen_rows, combinations, started = set(), 0, time.monotonic()
        for template in templates:
            record, roles = self.record(template)
            for alive in itertools.product((False, True), repeat=len(roles)):
                alive_roles = {role for role, up in zip(roles, alive) if up}
                for install, extra, can_read, held in itertools.product(
                        installs, ("none", "engine", "helper", "reused"), (True, False), (False, True)):
                    if not can_read and (extra != "none" or held):
                        continue  # An unread table hides processes and port alike: one case covers it.
                    if extra == "reused" and "wrapper" in alive_roles:
                        continue  # The wrapper's pid is taken by the wrapper itself.
                    combinations += 1
                    world.clear()
                    world.update({self.p[role].pid: self.p[role] for role in alive_roles})
                    parent = next((self.p[role].pid for role in ("server_tree", "server") if role in alive_roles), 1)
                    if extra == "engine":  # an engine nobody recorded, e.g. restarted by the server tree
                        world[20] = ident(20, parent, self.engine_exe)
                    elif extra == "helper":  # a helper outside the runtime, under the server if it lives
                        world[21] = ident(21, self.p["server"].pid if "server" in alive_roles else 1, "/usr/bin/helper")
                    elif extra == "reused":  # a stranger now holding the recorded wrapper's pid
                        world[11] = procs.ProcInfo(11, 1, "created-other", "/tools/python3")
                    readable["value"], port["held"] = can_read, held
                    self.write(self.layout.install_record, installs[install])
                    self.write(self.layout.run_record, record)
                    runtime = {pid for pid, proc in world.items() if proc.exe == self.engine_exe}
                    truth = self.owners(world, alive_roles, self.p, runtime)
                    case = (template, sorted(alive_roles), install, extra, can_read, held)
                    with self.subTest(case=case):
                        seen_rows.add(self.check(record, truth, readable["value"], held, installs[install], world,
                                                 terminated))
        self.combinations, self.seconds = combinations, time.monotonic() - started
        print(f"\nstate-table walk: {combinations} combinations in {self.seconds:.1f} s", file=sys.stderr)
        self.assertEqual(set(lifecycle.ROWS), seen_rows)  # Every row of the closed table is reachable.

    def check(self, record, truth, readable, held, install, world, terminated):
        run = record if isinstance(record, dict) else {}
        verdict = lifecycle.verdict(self.layout)
        # I6: every combination is in exactly one row of the closed table.
        self.assertIn(verdict.row, lifecycle.ROWS)
        token = run.get("tree_token")
        expected_idle = (readable and isinstance(record, (dict, type(None))) and not truth
                         and run.get("state") != "launching" and not run.get("unpublished_child")
                         and (not token or (run.get("state") == "stopped" and run.get("tree_verified_empty") == token))
                         and not held and (install is None or install["profile_fingerprint"]
                                           == self.layout.profile.fingerprint))
        # I1: idle exactly when no process of the root is alive, no launch is pending, custody is known, the table
        # was read and nothing else holds the port.
        self.assertEqual(expected_idle, verdict.idle, verdict)
        if readable and verdict.row not in ("unreadable-record",):
            self.assertEqual(truth, {proc.pid for proc in verdict.live.values()}, verdict)
        # I4: the status document carries the verdict, and its state is idle exactly when the verdict is.
        reported = lifecycle.status(self.layout)
        self.assertEqual(verdict.idle, reported["state"] in lifecycle.IDLE_STATES, reported)
        if not (verdict.row == "server-live" and verdict.state == "healthy"):
            self.assertEqual(verdict.state, reported["state"])
        # I3: start passes its root checks exactly when the verdict is idle, and refuses with the verdict's reason.
        admitted = None
        try:
            lifecycle.start(self.layout, tool_argv=[sys.executable], log=lambda line: None)
        except Admitted:
            admitted = True
        except lifecycle.LifecycleError as exc:
            admitted = False
            self.assertEqual(verdict.refusal, str(exc))
        self.assertEqual(verdict.idle, admitted)
        try:
            lifecycle.idle_generation(self.layout)
            accepted = True
        except lifecycle.LifecycleError:
            accepted = False
        self.assertTrue(not accepted or verdict.quiescent, verdict)
        self.assertTrue(not accepted or not run or (run.get("tree_verified_empty") == token and token), verdict)
        # I2: stop ends exactly the verdict's live set; I5: no status problem advises a stop that refuses.
        terminated.clear()
        recorded_alive = {proc.pid for role, identity in lifecycle.recorded_processes(run)
                          if identity and (proc := world.get(int(identity["pid"]))) is not None
                          and procs.same_identity(proc, identity)}
        try:
            lifecycle.stop(self.layout, log=lambda line: None)
            refused = False
        except lifecycle.LifecycleError:
            refused = True
        advises = any("run `stop`" in problem for problem in verdict.problems)
        self.assertFalse(refused and advises, verdict)
        if refused:
            self.assertTrue(verdict.row in STOP_REFUSES or (token and not lifecycle.WINDOWS), verdict)
            if verdict.row == "unreadable-table":
                self.assertLessEqual(set(terminated), recorded_alive)
                if isinstance(record, dict) and not run.get("unpublished_child") and not token:
                    self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])
            return verdict.row
        self.assertEqual({proc.pid for proc in verdict.live.values()}, set(terminated), verdict)
        after = lifecycle.verdict(self.layout)
        self.assertEqual({}, after.live, after)
        self.assertNotIn(after.row, ("launch-pending", "launch-abandoned"), after)
        self.assertTrue(after.idle or after.state == "mismatched" or after.row == "port-held", after)
        return verdict.row


class EvidenceAndCustodyWalk(unittest.TestCase):
    """Cross evidence failures, later observations and native custody without native effects."""
    setUp = StateTableWalk.setUp

    def world(self):
        self.records, self.processes = {}, {}
        self.reads, self.ended = [], []
        self.schedule = (True, True, True)
        self.replace = self.held = self.missing_job = False
        self.later_record = None
        self.layout.run_record.touch()
        self.layout.install_record.touch()

        def load(path):
            if self.later_record and len(self.reads) == 1 and path == self.later_record[0]:
                self.records[path] = self.later_record[1]
            value = self.records[path]
            if isinstance(value, Exception):
                raise value
            return json.loads(value)

        def save(path, value):
            self.records[path] = json.dumps(value)

        def table():
            index = len(self.reads)
            readable = self.schedule[min(index, 2)]
            if index == 1 and self.replace:
                self.processes[20] = procs.ProcInfo(20, 1, "replacement", self.engine_exe)
            self.reads.append((readable, dict(self.processes)))
            if not readable:
                raise procs.TableUnavailable("fixture census unavailable")
            return dict(self.processes)

        def terminate(proc, timeout):
            self.ended.append(proc.pid)
            self.processes.pop(proc.pid, None)
            return True

        def job(token, **kwargs):
            if self.missing_job:
                raise lifecycle.MissingProcessJob("fixture job gone")
            return SimpleNamespace(token=token, stop=lambda timeout: None, close=lambda: None)

        for active in (
                patch.object(lifecycle, "read_json", side_effect=load),
                patch.object(lifecycle, "atomic_write_json", side_effect=save),
                patch.object(lifecycle, "process_table", side_effect=table),
                patch.object(procs, "terminate", side_effect=terminate),
                patch.object(procs, "matches", side_effect=lambda rec: self.processes.get(rec["pid"]) if rec else None),
                patch.object(procs, "descendants", return_value=[]),
                patch.object(lifecycle, "port_in_use", side_effect=lambda *args: self.held),
                patch.object(remote, "listener_pids", return_value={99}),
                patch.object(lifecycle, "read_key", return_value="x" * 32),
                patch.object(lifecycle, "runtime_checks", return_value={"problems": []}),
                patch.object(lifecycle, "verify_install_fast", side_effect=Admitted),
                patch.object(lifecycle, "FileLock", return_value=contextlib.nullcontext())):
            self.enterContext(active)
        self.job = self.enterContext(patch.object(lifecycle, "ProcessJob", side_effect=job))
        self.job.scan.return_value = {}

    def configure(self, run_kind="valid", install_kind="valid", token="none", alive=True, held=False):
        self.reads.clear()
        self.ended.clear()
        self.processes.clear()
        self.held = held
        install = {"profile_fingerprint": self.layout.profile.fingerprint, "runtime_identity_sha256": "a" * 64}
        run = dict(install, state="ready", server=self.p["server"].as_dict())
        if token != "none":
            run["tree_token"] = TOKEN
        if token == "proved":
            run.update(state="stopped", tree_verified_empty=TOKEN)
        if alive:
            self.processes[12] = self.p["server"]
            self.processes[20] = ident(20, 1, self.engine_exe)
        faults = {"corrupt": "{", "io": PermissionError("fixture record unreadable"),
                  "null": "null", "list": "[]", "scalar": "42"}
        self.records[self.layout.run_record] = faults.get(run_kind, json.dumps(run))
        if install_kind == "other":
            install["profile_fingerprint"] = "other"
        self.records[self.layout.install_record] = faults.get(install_kind, json.dumps(install))
        return run

    def stop_result(self):
        try:
            return lifecycle.stop(self.layout, log=lambda line: None), None
        except lifecycle.LifecycleError as exc:
            return None, exc

    def test_stop_requires_its_last_census_to_be_read_and_empty(self):
        self.world()
        for schedule in ((False, True, True), (True, False, True), (True, True, False)):
            with self.subTest(schedule=schedule), patch.object(lifecycle, "WINDOWS", True):
                self.configure(token="unproved")
                self.schedule, self.replace = schedule, True
                result, failure = self.stop_result()
                self.assertIsNone(result)
                self.assertIsNotNone(failure)
                saved = json.loads(self.records[self.layout.run_record])
                self.assertEqual("stop_incomplete", saved["state"])
                self.assertNotIn("tree_verified_empty", saved)

    def test_missing_windows_job_does_not_hide_census_cleanup(self):
        self.world()
        self.configure(token="unproved")
        self.missing_job = True
        with patch.object(lifecycle, "WINDOWS", True):
            result, failure = self.stop_result()
        self.assertIsNone(failure)
        self.assertEqual("stopped", result["state"])
        self.assertEqual({12, 20}, set(self.ended))

    def test_mismatched_install_never_bypasses_retained_job_proof(self):
        self.world()
        for token in ("unproved", "proved"):
            with self.subTest(token=token):
                self.configure(install_kind="other", token=token, alive=False)
                self.assertEqual(token == "proved", lifecycle.verdict(self.layout).quiescent)

    def test_job_scan_proves_empty_after_census_cleanup_not_before(self):
        self.world()
        self.missing_job = True
        self.job.scan.side_effect = lambda *args, **kwargs: dict(self.processes)
        for token in ("unproved", "proved"):
            with self.subTest(token=token), patch.object(lifecycle, "WINDOWS", True):
                self.configure(token=token)
                result, failure = self.stop_result()
                self.assertIsNone(failure)
                self.assertEqual("stopped", result["state"])
                self.assertEqual({12, 20}, set(self.ended))

    def test_relative_executable_never_acquires_ownership_from_cwd(self):
        self.world()
        self.configure(alive=False)
        self.layout.strata.mkdir(parents=True)
        self.processes[99] = ident(99, 1, "python")
        with contextlib.chdir(self.layout.strata):
            root = lifecycle.verdict(self.layout)
            result, failure = self.stop_result()
        self.assertEqual({}, root.live)
        self.assertEqual([], self.ended)
        self.assertIsNone(failure)
        self.assertEqual("stopped", result["state"])

    def test_record_faults_block_admission_but_preserve_available_cleanup(self):
        self.world()
        for which, kind in itertools.product(("run", "install"), ("corrupt", "io", "null", "list", "scalar")):
            with self.subTest(record=which, fault=kind):
                self.configure(**{which + "_kind": kind})
                root = lifecycle.verdict(self.layout)
                self.assertEqual("unreadable-record", root.row)
                self.assertFalse(root.quiescent or root.idle)
                self.reads.clear()
                result, failure = self.stop_result()
                self.assertIsNone(result)
                self.assertIsNotNone(failure)
                self.assertIn(20, self.ended)
                if which == "install":
                    self.assertIn(12, self.ended)

    def test_port_holder_outside_census_blocks_install_and_names_pid(self):
        self.world()
        self.configure(alive=False, held=True)
        self.processes[99] = ident(99, 1, "/base/python")
        root = lifecycle.verdict(self.layout)
        self.assertEqual({}, root.live)
        self.assertFalse(root.quiescent)
        self.assertIn("99", root.refusal)
        self.assertIn("change the port", root.refusal)
        with patch.object(cli, "_layout", return_value=self.layout), patch.object(cli.install_mod, "install") as install:
            with self.assertRaises(lifecycle.LifecycleError):
                cli.cmd_install(SimpleNamespace(idle_generation=None))
            install.assert_not_called()

    def test_record_failure_after_cleanup_never_publishes_success_or_overwrites_bad_run(self):
        self.world()
        for which, value in itertools.product(("run", "install"), ("{", "null", "[]", PermissionError("unreadable"))):
            with self.subTest(record=which, value=value):
                self.configure()
                path = self.layout.run_record if which == "run" else self.layout.install_record
                self.later_record = (path, value)
                result, failure = self.stop_result()
                self.assertIsNone(result)
                self.assertIsNotNone(failure)
                self.assertEqual({12, 20}, set(self.ended))
                self.assertEqual(value, self.records[path])
                if which == "install":
                    self.assertEqual("stop_incomplete", json.loads(self.records[self.layout.run_record])["state"])

    def test_a_still_counted_identity_is_not_an_empty_final_census(self):
        self.world()
        self.configure()
        with patch.object(procs, "terminate", return_value=True):
            result, failure = self.stop_result()
        self.assertIsNone(result)
        self.assertIn("still alive after stop", str(failure))

    def test_unavailable_listener_pid_is_not_permission_to_install(self):
        self.world()
        self.configure(alive=False, held=True)
        with patch.object(remote, "listener_pids", side_effect=remote.RemoteError("unavailable")):
            root = lifecycle.verdict(self.layout)
        self.assertFalse(root.quiescent or root.idle)
        self.assertIn("PID unavailable", root.refusal)
        self.assertIn("change the port", root.refusal)

    def test_advice_on_both_platforms_including_healthy_stray_status(self):
        self.world()
        seen = set()
        for windows, missing, token, state, unpublished, alive in itertools.product(
                (False, True), (False, True), ("none", "unproved", "proved"),
                ("launching", "starting", "ready", "stop_incomplete"), (False, True), (False, True)):
            with self.subTest(case=(windows, missing, token, state, unpublished, alive)), \
                    patch.object(lifecycle, "WINDOWS", windows):
                run = self.configure(token=token, alive=alive)
                run.update(state=state, unpublished_child=unpublished)
                self.records[self.layout.run_record] = json.dumps(run)
                self.missing_job = missing
                root = lifecycle.verdict(self.layout)
                report = lifecycle.status(self.layout)
                seen.add(root.row)
                texts = [root.refusal or "", *root.problems, *report.get("problems", [])]
                advises = any("run `stop`" in text or "use stop" in text or "status/stop" in text
                              or "`stop` ends" in text for text in texts)
                self.reads.clear()
                _, failure = self.stop_result()
                self.assertFalse(advises and failure, texts)
                if state == "ready" and alive and not unpublished:
                    self.assertTrue(any("outside its recorded trees" in text for text in report["problems"]))
        self.assertIn("server-live", seen)

    def test_extended_product_preserves_all_three_properties(self):
        self.world()
        faults = ("valid", "corrupt", "io", "null", "list", "scalar")
        failures, cases, started = [], 0, time.monotonic()
        for run_kind, install_kind, token, windows, missing, alive, held, schedule in itertools.product(
                faults, (*faults, "other"), ("none", "unproved", "proved"), (False, True), (False, True),
                (False, True), (False, True), tuple(itertools.product((False, True), repeat=3))):
            cases += 1
            with patch.object(lifecycle, "WINDOWS", windows):
                self.configure(run_kind, install_kind, token, alive, held)
                self.schedule, self.replace, self.missing_job = schedule, alive, missing
                case = (run_kind, install_kind, token, windows, missing, alive, held, schedule)
                try:
                    root = lifecycle.verdict(self.layout)
                    valid = run_kind == "valid" and install_kind in ("valid", "other")
                    if root.quiescent and not (valid and schedule[0] and token != "unproved" and not held):
                        raise AssertionError("quiescent without complete evidence, custody or port proof")
                    texts = [root.refusal or "", *root.problems]
                    advises = any("run `stop`" in t or "use stop" in t or "status/stop" in t for t in texts)
                    self.reads.clear()
                    result, failure = self.stop_result()
                    if result and not (self.reads and self.reads[-1] == (True, {})):
                        raise AssertionError("stopped without a final read empty census")
                    # Advice uses the same initial evidence; later failures are not the same state.
                    if advises and failure and all(schedule):
                        raise AssertionError("advised stop refuses the same state")
                except Exception as exc:
                    if len(failures) < 12:
                        failures.append((case, type(exc).__name__, str(exc)))
        print(f"\nextended evidence walk: {cases} combinations in {time.monotonic() - started:.2f} s", file=sys.stderr)
        self.assertEqual([], failures)


class StopIdentityWalk(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        data = single_gpu_data()
        data["server"].update(port=free_port(), stop_timeout_s=0)
        self.layout = Layout(Path(directory), Profile(PROFILE, data))
        self.install = {"profile_fingerprint": self.layout.profile.fingerprint,
                        "runtime_identity_sha256": "a" * 64}
        atomic_write_json(self.layout.install_record, self.install)

    def walk(self, event, reverse=False, reused_pid=10, generations=1):
        """Termination can re-issue an ended PID, not just delete a process from a fixed world."""
        engine = str(self.layout.strata / "engine" / "strata")
        original = {10: ident(10, 1, engine), 11: ident(11, 10, engine)}
        world = dict(reversed(list(original.items()))) if reverse else dict(original)
        ended, snapshots = [], []
        issued = 0

        def table():
            snapshots.append(dict(world))
            return dict(world)

        def terminate(proc, timeout):
            nonlocal issued
            self.assertEqual(proc, world.pop(proc.pid), "stop tried to terminate a stale identity")
            ended.append(proc)
            if not world and event != "none" and issued < generations:
                issued += 1
                previous = original[reused_pid]
                created = f"{previous.created}-generation-{issued}" if event == "creation" else previous.created
                exe = f"{engine}-{issued}" if event == "executable" else engine
                world[reused_pid] = procs.ProcInfo(reused_pid, 1, created, exe)
            return True

        atomic_write_json(self.layout.run_record, dict(self.install, state="ready"))
        with patch.object(lifecycle, "process_table", side_effect=table), \
                patch.object(procs, "terminate", side_effect=terminate), \
                patch.object(lifecycle, "port_in_use", return_value=False):
            result, failure = None, None
            try:
                result = lifecycle.stop(self.layout, log=lambda line: None)
            except lifecycle.LifecycleError as exc:
                failure = exc
            after = lifecycle.verdict(self.layout)
        self.assertFalse(result and result["state"] == "stopped" and after.live,
                         f"stop reported stopped while the verdict still counts {after.live}")
        if event != "none":
            self.assertNotEqual(original[reused_pid], snapshots[1][reused_pid])
        exhausted = event != "none" and generations == 2
        self.assertEqual(exhausted, failure is not None)
        self.assertEqual(exhausted, bool(after.live))
        self.assertEqual("stop_incomplete" if exhausted else "stopped", read_json(self.layout.run_record)["state"])
        self.assertEqual(2 + (event != "none"), len(ended))
        if exhausted:
            self.assertIn("still alive after stop", str(failure))
        else:
            self.assertTrue(after.idle)
        return len(snapshots)

    def test_stop_never_reports_stopped_while_a_reused_pid_is_still_counted(self):
        for event in ("creation", "executable"):
            with self.subTest(identity_change=event):
                self.walk(event)

    def test_stop_identity_walk_reissues_ended_pids_between_passes(self):
        started, snapshots, cases = time.monotonic(), 0, 0
        for event, reverse, pid, generations in itertools.product(
                ("none", "creation", "executable"), (False, True), (10, 11), (1, 2)):
            with self.subTest(event=event, reverse=reverse, pid=pid, generations=generations):
                snapshots += self.walk(event, reverse, pid, generations)
                cases += 1
        print(f"\nstop identity walk: {cases} schedules, {snapshots} snapshots in "
              f"{time.monotonic() - started:.3f} s", file=sys.stderr)


class WindowsSnapshotIdentityTests(unittest.TestCase):
    def setUp(self):
        # Execute the unchanged Windows function body without loading kernel32 on this host. Its snapshot and
        # identity-query boundaries are fakes; table's attribution policy is the production code.
        source = ast.parse(Path(procs.__file__).read_text())
        branch = next(node for node in source.body
                      if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "WINDOWS")
        function = next(node for node in branch.body if isinstance(node, ast.FunctionDef) and node.name == "table")
        self.namespace = dict(vars(procs))
        exec(compile(ast.Module(body=[function], type_ignores=[]), procs.__file__, "exec"), self.namespace)
        self.table = self.namespace["table"]
        self.cutoff = 116444736000000000 + 1234567890
        self.events = []
        self.namespace["time"] = SimpleNamespace(time_ns=self.clock)

    def clock(self):
        self.events.append("clock")
        return 123456789000

    def snapshot(self):
        self.events.append("snapshot")
        return {11: (10, "old-child.exe")}

    def queried(self, created):
        self.namespace["_snapshot"] = self.snapshot
        self.namespace["info"] = lambda pid, *, ppid: procs.ProcInfo(pid, ppid, str(created), "/unrelated/python")
        return self.table()

    def test_a_reused_pid_created_after_the_snapshot_is_not_attributed_to_the_old_parent(self):
        parent = procs.ProcInfo(10, 1, str(self.cutoff - 10), "/root/server")
        table = {10: parent, **self.queried(self.cutoff + 1)}
        with patch.object(procs, "WINDOWS", True):
            descendants, _ = lifecycle._descendants(table, {"server": parent})
        self.assertNotIn("descendant[11]", descendants,
                         "a new unrelated process inherited the old snapshot row's parent")
        self.assertNotIn(11, table)
        self.assertEqual(["clock", "snapshot"], self.events)

    def test_snapshot_creation_boundary_keeps_before_and_equal_but_not_later_identities(self):
        for delta in (-1, 0, 1):
            with self.subTest(filetime_ticks_from_snapshot=delta):
                self.assertEqual(delta <= 0, 11 in self.queried(self.cutoff + delta))


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


class StagingPreflightReadOnlyTests(unittest.TestCase):
    def test_preflight_only_reads_for_absent_unprepared_and_prepared_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            data = single_gpu_data()
            data["model"]["conversion"] = nvfp4.conversion_pin(next(iter(nvfp4.RECIPES.values()))[0])
            layout = Layout(Path(directory) / "root", Profile(PROFILE, data))

            def snapshot():
                return {str(path.relative_to(layout.root)): path.read_bytes() if path.is_file() else None
                        for path in layout.root.rglob("*")} if layout.root.exists() else None

            with patch.object(nvfp4.shutil, "disk_usage", return_value=SimpleNamespace(free=10**15)):
                for state in ("absent", "unprepared", "prepared"):
                    with self.subTest(state=state):
                        if state == "unprepared":
                            layout.root.mkdir()
                            (layout.root / "retained").write_bytes(b"unchanged")
                        elif state == "prepared":
                            base = nvfp4.prepared_dir(layout)
                            for name in ("dense.gguf", "ple-nvfp4.gguf", "pack/experts.bin", "pack/dense.bin",
                                         "pack/index.txt", "pack/native_experts.txt", "pack/tokenizer/vocab.json",
                                         "mtp/rt/experts.bin", "mtp/rt/draft_vocab.bin"):
                                path = base / name
                                path.parent.mkdir(parents=True, exist_ok=True)
                                path.write_bytes(b"fixture")
                            atomic_write_json(base / "conversion-receipt.json", {
                                "input_fingerprint": lifecycle.sha256_bytes(lifecycle.canonical_json(data["model"])),
                                "recipe_commit": data["model"]["conversion"]["recipe_commit"],
                                "recipe_sha256": data["model"]["conversion"]["recipe_sha256"],
                                "weight_manifest_sha256": nvfp4.MANIFEST_SHA256,
                                "files": nvfp4.output_manifest(layout)})
                        before = snapshot()
                        nvfp4.staging_preflight(layout)
                        self.assertEqual(before, snapshot())


def interruption_driver(root, data, point, role):
    """Run the real writer in a killable process; only host checks and the stock server are substitutes."""
    layout = Layout(Path(root), Profile(PROFILE, data))

    def wait_for(name):
        deadline = time.monotonic() + 15
        while not (layout.root / name).exists():
            if time.monotonic() >= deadline:
                raise RuntimeError(f"interruption driver timed out waiting for {name}")
            time.sleep(0.01)

    def hold():
        (layout.root / "held").touch()
        wait_for("release")

    real_write, real_info = lifecycle.atomic_write_json, procs.info

    def write(path, value):
        state = value.get("state")
        if role == "start" and point == 0 and state == "launching":
            hold()
        real_write(path, value)
        if role == "start" and ((point == 1 and state == "launching") or (point == 6 and state == "ready")):
            hold()
        if role == "serve" and ((point == 3 and value.get("unpublished_child"))
                               or (point == 5 and value.get("server") and state == "starting")
                               or (point == 8 and state == "exited")):
            hold()

    def info(pid, **kwargs):
        result = real_info(pid, **kwargs)
        if role == "serve" and pid != os.getpid():
            (layout.root / "server.pid").write_text(str(pid))
            if point == 4:
                hold()
        return result

    def dispatch(argv, **kwargs):
        atomic_write_json(layout.root / "dispatch.json", {"launch_id": argv[-1]})
        wait_for("dispatched")
        if point in (2, 3, 4, 5, 8):
            (layout.root / "launcher-held").touch()
            wait_for("launcher-release")

    def health(*args, **kwargs):
        if point == 7:
            raise lifecycle.LifecycleError("injected readiness failure")
        return {"ready": True, "problems": []}

    real_terminate = procs.terminate

    def terminate(proc, timeout):
        if point == 7:
            hold()  # The real failure cleanup entered stop, before its first process effect.
        return real_terminate(proc, timeout)

    with patch.object(lifecycle, "atomic_write_json", side_effect=write), \
            patch.object(procs, "info", side_effect=info), \
            patch.object(lifecycle, "read_key", return_value="x" * 32):
        if role == "serve":
            if point == 2:
                (layout.root / "wrapper-waiting").touch()
                wait_for("wrapper-release")
            engine = layout.strata / "engine" / "strata"
            argv = ["/bin/sh", "-c", '"$1" -c "import time; time.sleep(600)" & echo $! > "$2"; wait',
                    "stub-server", str(engine), str(layout.root / "engine.pid")]
            with patch.object(lifecycle, "server_argv", return_value=argv):
                try:
                    lifecycle.serve(layout, log_path=layout.logs / "server.log",
                                    launch_id=read_json(layout.root / "dispatch.json")["launch_id"])
                except lifecycle.LifecycleError as exc:
                    (layout.root / "refused").write_text(str(exc))
                    raise
        else:
            with patch.object(lifecycle, "verify_install_fast", return_value=read_json(layout.install_record)), \
                    patch.object(lifecycle, "gpu_facts", return_value={}), \
                    patch.object(lifecycle, "gpu_busy", return_value=None), \
                    patch.object(procs, "memory", return_value={"available": 1 << 40}), \
                    patch.object(lifecycle, "_launch_detached", side_effect=dispatch), \
                    patch.object(lifecycle, "runtime_checks", side_effect=health), \
                    patch.object(procs, "terminate", side_effect=terminate):
                lifecycle.start(layout, tool_argv=[sys.executable], log=lambda line: None)


@unittest.skipIf(procs.WINDOWS, "POSIX interruption drivers; native Windows is unexercised")
class InterruptionWalk(unittest.TestCase):
    def wait_for(self, predicate, detail):
        deadline = time.monotonic() + 15
        while not predicate():
            if time.monotonic() >= deadline:
                self.fail(f"timed out waiting for {detail}")
            time.sleep(0.01)

    def test_every_interruption_preserves_a_nonidle_verdict_until_custody_is_resolved(self):
        started = time.monotonic()
        for point, expected in enumerate(("idle", "launch-abandoned", "launch-abandoned", "custody-unknown",
                                          "custody-unknown", "server-live", "server-live", "server-live", "orphans")):
            with self.subTest(point=f"P{point}"), tempfile.TemporaryDirectory() as directory:
                data = single_gpu_data()
                data["server"].update(port=free_port(), stop_timeout_s=2)
                layout = Layout(Path(directory) / "root", Profile(PROFILE, data))
                layout.strata.mkdir(parents=True)
                engine = layout.strata / "engine" / "strata"
                engine.parent.mkdir()
                shutil.copy(procs.info(os.getpid()).exe, engine)
                atomic_write_json(layout.install_record, {
                    "profile_fingerprint": layout.profile.fingerprint, "runtime_identity_sha256": "a" * 64})
                atomic_write_json(layout.strata_config, {"log": str(layout.root.resolve() / "engine.log")})
                children, identities = [], []
                killed = set()

                def spawn(role):
                    code = ("import json,sys; from tests.unit.test_lifecycle_states import interruption_driver; "
                            "interruption_driver(sys.argv[1],json.loads(sys.argv[2]),int(sys.argv[3]),sys.argv[4])")
                    output = open(layout.root / (role + ".log"), "wb")
                    try:
                        child = subprocess.Popen([sys.executable, "-c", code, str(layout.root), json.dumps(data),
                                                  str(point), role], stdin=subprocess.DEVNULL,
                                                 stdout=output, stderr=subprocess.STDOUT)
                    finally:
                        output.close()
                    children.append(child)
                    threading.Thread(target=child.wait, daemon=True).start()
                    return child

                def marker(name):
                    def ready():
                        if (layout.root / name).exists():
                            return True
                        for child in children:
                            if child not in killed and child.poll() is not None:
                                logs = "\n".join(path.read_text() for path in layout.root.glob("*.log"))
                                self.fail(f"P{point} driver exited before {name}:\n{logs}")
                        return False
                    self.wait_for(ready, f"P{point} {name}")

                def kill(child):
                    killed.add(child)
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=5)

                def observe(row):
                    verdict = lifecycle.verdict(layout)
                    self.assertIn(verdict.row, lifecycle.ROWS)
                    self.assertEqual(row, verdict.row, verdict)
                    self.assertEqual(point == 0, verdict.idle, verdict)
                    if verdict.idle:
                        self.assertFalse(verdict.live)
                        self.assertFalse(verdict.details.get("pending"))
                    return verdict

                try:
                    launcher = spawn("start")
                    wrapper = None
                    if point >= 2:
                        marker("dispatch.json")
                        wrapper = spawn("serve")
                        (layout.root / "dispatched").touch()
                    if point == 2:
                        marker("wrapper-waiting")
                        marker("launcher-held")
                        observe("launch-pending")
                    elif point == 8:
                        marker("launcher-held")
                        marker("server.pid")
                    else:
                        marker("held")
                    if point in (3, 4):
                        observe("wrapper-publishing")
                    if point >= 4:
                        marker("engine.pid")
                        for name in ("server", "engine"):
                            pid = int((layout.root / (name + ".pid")).read_text())
                            self.wait_for(lambda: (proc := procs.info(pid)) is not None
                                          and (name != "engine" or proc.exe == str(engine)), f"{name} exec")
                            identities.append(procs.info(pid))
                    if point == 1:
                        observe("launch-pending")
                    kill(launcher)
                    if point in (3, 4, 5):
                        kill(wrapper)
                    if point == 8:
                        os.kill(identities[0].pid, signal.SIGKILL)
                        marker("held")  # serve published the real child exit.
                        kill(wrapper)
                    verdict = observe(expected)
                    print(f"\nP{point}: {verdict.row} ({verdict.state}), idle={verdict.idle}", file=sys.stderr)
                    if point == 2:
                        lifecycle.stop(layout, log=lambda line: None)
                        (layout.root / "wrapper-release").touch()
                        wrapper.wait(timeout=5)
                        self.assertNotEqual(0, wrapper.returncode)
                        self.assertIn("generation changed or stopped", (layout.root / "refused").read_text())
                        self.assertEqual("idle", lifecycle.verdict(layout).row)
                        self.assertFalse((layout.root / "server.pid").exists())
                        print("P2 fenced: idle; late wrapper refused without spawning", file=sys.stderr)
                    elif point in (3, 4):
                        with self.assertRaisesRegex(lifecycle.LifecycleError, "unpublished child"):
                            lifecycle.stop(layout, log=lambda line: None)
                    elif point >= 5:
                        lifecycle.stop(layout, log=lambda line: None)
                        self.assertTrue(lifecycle.verdict(layout).idle)
                finally:
                    # Deepest first: the shell reaps its engine, serve reaps the shell, and our waiters reap drivers.
                    for proc in reversed(identities):
                        if procs.matches(proc.as_dict()):
                            self.assertTrue(procs.terminate(proc, 2), f"leftover process {proc}")
                    for child in reversed(children):
                        kill(child)
                    for proc in identities:
                        self.assertIsNone(procs.matches(proc.as_dict()), f"leftover process {proc}")
        print(f"\ninterruption walk: P0-P8 in {time.monotonic() - started:.2f} s", file=sys.stderr)


@unittest.skipIf(procs.WINDOWS, "POSIX process fixture; native Windows is unexercised")
class CensusResidualTests(unittest.TestCase):
    def test_an_unrecorded_process_outside_the_runtime_is_not_counted_or_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            data = single_gpu_data()
            data["server"]["port"] = free_port()
            layout = Layout(Path(directory), Profile(PROFILE, data))
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            try:
                # The child has no recorded ancestor, executes outside the runtime and does not hold its port.
                before = lifecycle.verdict(layout)
                self.assertEqual("idle", before.row)
                self.assertEqual({}, before.live)
                self.assertEqual([], lifecycle.stop(layout, log=lambda line: None)["stopped"])
                self.assertIsNone(child.poll())
                self.assertFalse(layout.run_record.exists())
            finally:
                child.kill()
                child.wait(timeout=5)
            self.assertIsNone(procs.info(child.pid))


if __name__ == "__main__":
    unittest.main()
