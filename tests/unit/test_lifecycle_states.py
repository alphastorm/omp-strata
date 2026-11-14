"""The lifecycle's closed state table, walked (docs/OPERATIONS.md, "Lifecycle states").

The walk crosses everything the code can write (install record, run record state and flags) with everything the
process table can show (which recorded processes live, unrecorded processes of the root, a pid reused by a stranger,
a failed read, the port), using a process world kept in memory, and checks that status, start and
idle_generation act on one verdict and recovery advice passes structural stop admission and that every row of the closed table is reached.
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
from tests.unit.test_lifecycle_evidence import complete_table, native_matches
from tests.unit.test_profile import single_gpu_data

FULL = ("wrapper", "server", "engine", "server_tree")
TOKEN = "a" * 32
# Rows whose `stop` refuses on this platform: custody unknown, a publishing wrapper, an unreadable record, and (off
# Windows) any process-tree record. An unreadable table ends verified recorded processes, then refuses.
STOP_REFUSES = {"unreadable-record", "custody-unknown", "wrapper-publishing", "unreadable-table"}


class Admitted(Exception):
    """`start` passed every root check and reached the install check."""


class VerdictConsumerInventory(unittest.TestCase):
    def test_inventory_rejects_independent_legacy_decisions(self):
        source_path = Path(lifecycle.__file__)
        original = Path.read_text
        for expression, imports in (
                ("procs.matches(read_json(layout.run_record).get('server'))", ""),
                ("peek(read_json(layout.run_record).get('server'))", "from omp_strata.procs import matches as peek\n"),
                ("readers.matches(read_json(layout.run_record).get('server'))", "from omp_strata import procs as readers\n"),
                ("running(layout)", ""),
                ("getattr(procs, 'matches')(read_json(layout.run_record).get('server'))", "")):
            with self.subTest(expression=expression):
                def text(path, *args, **kwargs):
                    value = original(path, *args, **kwargs)
                    return value + f"\n{imports}\ndef scratch_fifth_idle(layout):\n    return not {expression}\n" if path == source_path else value
                with patch.object(Path, "read_text", autospec=True, side_effect=text), self.assertRaises(AssertionError):
                    self.test_the_four_admission_and_status_callers_share_one_verdict()

    def test_the_four_admission_and_status_callers_share_one_verdict(self):
        expected = {lifecycle: {"status", "start", "idle_generation"}, cli: {"cmd_install"}}
        for module, names in expected.items():
            with self.subTest(module=module.__name__):
                tree = ast.parse(Path(module.__file__).read_text())
                callers = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)
                           and any(isinstance(call, ast.Call)
                                   and (isinstance(call.func, ast.Name) and call.func.id == "verdict"
                                        or isinstance(call.func, ast.Attribute) and call.func.attr == "verdict")
                                   for call in ast.walk(node))}
                self.assertEqual(names, callers)


def ident(pid: int, ppid: int, exe: str) -> procs.ProcInfo:
    return procs.ProcInfo(pid, ppid, str(pid), exe)


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
            "launch-unrecorded": (dict(base, state="launching"), ()),
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
            return complete_table(world)

        def matches(recorded):
            proc = world.get(int(recorded["pid"])) if recorded else None
            return native_matches(proc, recorded)

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
        templates = ("absent", "unreadable", "launching", "launch-unrecorded", "publishing", "starting", "ready", "exited-0", "exited-1",
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
                        world[11] = procs.ProcInfo(11, 1, "10011", "/tools/python3")
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
                self.processes[20] = procs.ProcInfo(20, 1, "10020", self.engine_exe)
            self.reads.append((readable, dict(self.processes)))
            if not readable:
                raise procs.TableUnavailable("fixture census unavailable")
            return complete_table(self.processes)

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
                patch.object(lifecycle, "_read_record", side_effect=load),
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


    def test_mismatched_install_never_bypasses_retained_job_proof(self):
        self.world()
        for token in ("unproved", "proved"):
            with self.subTest(token=token):
                self.configure(install_kind="other", token=token, alive=False)
                self.assertEqual(token == "proved", lifecycle.verdict(self.layout).quiescent)


    def test_relative_executable_never_acquires_ownership_from_cwd(self):
        self.world()
        self.configure(alive=False)
        self.layout.strata.mkdir(parents=True)
        self.processes[99] = ident(99, 1, "python")
        with contextlib.chdir(self.layout.strata):
            root = lifecycle.verdict(self.layout)
        self.assertEqual({}, root.live)

    def test_record_faults_block_admission_but_preserve_available_cleanup(self):
        self.world()
        for which, kind in itertools.product(("run", "install"), ("corrupt", "io", "null", "list", "scalar")):
            with self.subTest(record=which, fault=kind):
                self.configure(**{which + "_kind": kind})
                root = lifecycle.verdict(self.layout)
                self.assertEqual("unreadable-record", root.row)
                self.assertFalse(root.quiescent or root.idle)

                self.assertIn("unrecorded[20]", root.live)

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
                failure = lifecycle._stop_custody_refusal(root.run)
                self.assertFalse(advises and failure, texts)
                if state == "ready" and alive and not unpublished:
                    self.assertTrue(any("outside its recorded trees" in text for text in report["problems"]))
        self.assertIn("server-live", seen)

    def test_extended_product_preserves_admission_properties(self):
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
                    if advises and lifecycle._stop_custody_refusal(root.run):
                        raise AssertionError("advised stop fails structural admission")
                except Exception as exc:
                    if len(failures) < 12:
                        failures.append((case, type(exc).__name__, str(exc)))
        print(f"\nextended evidence walk: {cases} combinations in {time.monotonic() - started:.2f} s", file=sys.stderr)
        self.assertEqual([], failures)

    def test_advice_table_reaches_every_row_on_both_platform_flags(self):
        self.world()
        seen = {False: set(), True: set()}
        cases = 0
        for windows, missing, row in itertools.product((False, True), (False, True), lifecycle.ROWS):
            with self.subTest(windows=windows, missing_job=missing, row=row), \
                    patch.object(lifecycle, "WINDOWS", windows):
                self.schedule = (row != "unreadable-table",) * 3
                self.missing_job = missing
                run = self.configure(run_kind="null" if row == "unreadable-record" else "valid",
                                     install_kind="other" if row == "mismatched" else "valid",
                                     token="unproved" if row == "job-unproved" else "none",
                                     alive=row in ("server-live", "orphans"), held=row == "port-held")
                if row in ("launch-pending", "launch-abandoned", "launch-unrecorded"):
                    run["state"] = "launching"
                    if row != "launch-unrecorded":
                        run["launcher"] = self.p["launcher"].as_dict()
                    if row == "launch-pending":
                        self.processes[10] = self.p["launcher"]
                if row in ("wrapper-publishing", "custody-unknown"):
                    run.update(state="starting", unpublished_child=True)
                    if row == "wrapper-publishing":
                        run["wrapper"] = self.p["wrapper"].as_dict()
                        self.processes[11] = self.p["wrapper"]
                if row == "orphans":
                    run.pop("server")
                if row != "unreadable-record":
                    self.records[self.layout.run_record] = json.dumps(run)
                root = lifecycle.verdict(self.layout)
                self.assertEqual(row, root.row)
                seen[windows].add(root.row)
                texts = [root.refusal or "", *root.problems, *lifecycle.status(self.layout).get("problems", [])]
                advises = any("run `stop`" in t or "use stop" in t or "status/stop" in t or "`stop` ends" in t
                              for t in texts)
                if any("reinstall" in t for t in texts):
                    with patch.object(cli, "_layout", return_value=self.layout), \
                            patch.object(cli.install_mod, "install", side_effect=Admitted):
                        with self.assertRaises(Admitted):
                            cli.cmd_install(SimpleNamespace(idle_generation=None))
                self.reads.clear()
                failure = lifecycle._stop_custody_refusal(root.run)
                self.assertFalse(advises and failure, texts)
                cases += 1
        for rows in seen.values():
            self.assertEqual(set(lifecycle.ROWS), rows)
        print(f"\nadvice row table: {cases} cases, all rows on both platform flags", file=sys.stderr)


class StagingPreflightReadOnlyTests(unittest.TestCase):
    def test_preflight_only_reads_for_absent_unprepared_and_prepared_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            data = single_gpu_data()
            data["model"]["format"] = nvfp4.FORMAT
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


if __name__ == "__main__":
    unittest.main()
