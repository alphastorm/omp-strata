"""The lifecycle's closed state table, defined beside lifecycle.ROWS and walked here.

The walk crosses everything the code can write (install record, run record state and flags) with everything the
process table can show (which recorded processes live, unrecorded processes of the root, a pid reused by a stranger,
a failed read, the port), using a process world kept in memory, and checks that status, start and
idle_generation act on one verdict and recovery advice passes structural stop admission and that every row of the closed table is reached.
"""
from __future__ import annotations

import ast
from collections import Counter
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
    def test_state_table_references_do_not_name_a_missing_document_section(self):
        for path in (Path(lifecycle.__file__), Path(__file__)):
            with self.subTest(path=path.name):
                self.assertNotIn("Lifecycle" + " states", path.read_text())

    def test_each_closed_row_has_a_reason_at_its_definition(self):
        source = Path(lifecycle.__file__).read_text()
        definition = next(node for node in ast.parse(source).body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "ROWS" for target in node.targets))
        for row in definition.value.elts:
            with self.subTest(row=ast.literal_eval(row)):
                self.assertTrue(source.splitlines()[row.lineno - 1].partition("#")[2].strip())

    @staticmethod
    def legacy_reader_uses():
        """Syntactic inventory; reflection, an edited allowlist and a differently
        expressed semantic duplicate are outside it.
        """
        root = Path(lifecycle.__file__).parent.parent
        legacy = {"_open", "_parents", "_ps", "_proc_stat", "_proc_children", "info", "matches",
                  "children", "descendants", "terminate", "memory", "process_memory", "table"}
        uses = Counter()
        for directory in ("omp_strata", "scripts"):
            for path in (root / directory).rglob("*.py"):
                tree = ast.parse(path.read_text())
                relative = path.relative_to(root).as_posix()
                bindings = {name: f"procs.{name}" for name in legacy} if relative == "omp_strata/procs.py" else {}
                def reader_binding(name):
                    return name in ("procs", "process_table") or name.startswith("procs.")
                def bind(alias, name):
                    name = name.removeprefix("omp_strata.").removeprefix("lifecycle.")
                    previous = bindings.get(alias)
                    if previous is not None and previous != name and (reader_binding(previous) or reader_binding(name)):
                        raise AssertionError(f"{relative}: conflicting reader binding for {alias}")
                    bindings[alias] = name
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            bind(alias.asname or alias.name.split(".")[0], alias.name if alias.asname else alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module in ("omp_strata.procs", "procs") and any(a.name == "*" for a in node.names):
                            raise AssertionError(f"{relative}: reader star imports are not permitted")
                        for alias in node.names:
                            bind(alias.asname or alias.name, ".".join(filter(None, (node.module, alias.name))))
                def qualified(node):
                    if isinstance(node, ast.Name):
                        return bindings.get(node.id, node.id).removeprefix("omp_strata.").removeprefix("lifecycle.")
                    if isinstance(node, ast.Attribute):
                        return f"{qualified(node.value)}.{node.attr}".removeprefix("lifecycle.")
                    return ""
                assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
                for _ in range(len(assignments) + 1):
                    changed = False
                    for node in assignments:
                        name = qualified(node.value)
                        for target in node.targets:
                            if isinstance(target, ast.Name) and reader_binding(name) \
                                    and bindings.get(target.id) != name:
                                bind(target.id, name)
                                changed = True
                    if not changed:
                        break
                assert not changed, f"ambiguous legacy aliases in {relative}"
                for node in assignments:
                    for target in node.targets:
                        if isinstance(target, ast.Name) and reader_binding(bindings.get(target.id, "")):
                            bind(target.id, qualified(node.value))
                parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
                class Inventory(ast.NodeVisitor):
                    scope = ()
                    def visit_FunctionDef(self, node):
                        self.scope += (node.name,)
                        if node.name == "running":
                            uses[relative, ".".join(self.scope), "running"] += 1
                        self.generic_visit(node)
                        self.scope = self.scope[:-1]
                    visit_AsyncFunctionDef = visit_FunctionDef
                    visit_ClassDef = visit_FunctionDef
                    def generic_visit(self, node):
                        name = qualified(node)
                        reader = name.removeprefix("procs.") if name.startswith("procs.") else None
                        if name == "process_table":
                            reader = "process_table"
                        if name == "running" or name.endswith(".running"):
                            reader = "running"
                        if name == "procs" and not isinstance(parents.get(node), ast.Attribute):
                            reader = "module escape"
                        if isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load) \
                                and (reader in legacy or reader in ("running", "module escape", "process_table")):
                            uses[relative, ".".join(self.scope) or "<module>", reader] += 1
                        super().generic_visit(node)
                Inventory().visit(tree)
        return uses

    def test_inventory_rejects_independent_legacy_decisions(self):
        source_path = Path(lifecycle.__file__)
        original = Path.read_text
        shadow = ("def unrelated_record_reader(path):\n"
                  "    from omp_strata.common import read_json as census\n"
                  "    return census(path)\n")
        for expression, imports, extra in (
                ("procs.matches(read_json(layout.run_record).get('server'))", "", ""),
                ("peek(read_json(layout.run_record).get('server'))", "from omp_strata.procs import matches as peek\n", ""),
                ("readers.matches(read_json(layout.run_record).get('server'))", "from omp_strata import procs as readers\n", ""),
                ("matches(read_json(layout.run_record).get('server'))", "from omp_strata.procs import *\n", ""),
                ("procs.table().identified", "", ""),
                ("process_table().identified", "", ""),
                ("running(layout)", "", ""),
                ("getattr(procs, 'matches')(read_json(layout.run_record).get('server'))", "", ""),
                ("census().identified", "from omp_strata.procs import table as census\n", shadow),
                ("census().identified", "from omp_strata.lifecycle import process_table as census\n", shadow)):
            with self.subTest(expression=expression, imports=imports):
                def text(path, *args, **kwargs):
                    value = original(path, *args, **kwargs)
                    return value + f"\n{imports}\ndef scratch_fifth_idle(layout):\n    return not {expression}\n{extra}" if path == source_path else value
                with patch.object(Path, "read_text", autospec=True, side_effect=text), self.assertRaises(AssertionError) as failure:
                    self.test_the_five_lifecycle_consumers_share_one_verdict()
                if extra:
                    self.assertRegex(str(failure.exception), r"omp_strata/lifecycle\.py.*\bcensus\b")

    def test_the_five_lifecycle_consumers_share_one_verdict(self):
        expected = {lifecycle: {"status", "start", "idle_generation", "stop"}, cli: {"cmd_install"}}
        for module, names in expected.items():
            with self.subTest(module=module.__name__):
                tree = ast.parse(Path(module.__file__).read_text())
                callers = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)
                           and any(isinstance(call, ast.Call)
                                   and (isinstance(call.func, ast.Name) and call.func.id == "verdict"
                                        or isinstance(call.func, ast.Attribute) and call.func.attr == "verdict")
                                   for call in ast.walk(node))}
                self.assertEqual(names, callers)
        retained = {
            "omp_strata/lifecycle.py": {
                "process_table": ({"table": 1}, "One accounted census boundary for the verdict; no admission decision."),
                "verdict": ({"process_table": 1}, "The sole classifier reads one census for status and admission."),
                "serve": ({"info": 4}, "Capture wrapper/server identities at publication, not root admission."),
                "start": ({"info": 1, "memory": 1}, "Record launcher identity; RAM gate runs after verdict admission."),
                "doctor": ({"matches": 1, "memory": 1}, "Diagnostic port ownership and RAM checks, not idle admission."),
                "capture_startup_gpu_order": ({"matches": 4, "descendants": 2}, "Existing live stage-order evidence capture."),
                "owned_job_processes": ({"info": 1}, "Identify members of the readiness job snapshot."),
                "_finish_start.processes": ({"matches": 1, "descendants": 1}, "Existing post-launch readiness, not admission."),
                "status": ({"descendants": 1}, "Engine health only after server-live; never proves idle."),
                "_verifiable": ({"matches": 1}, "Shape-checked recorded cleanup when census evidence is unreadable."),
                "stop._stop": ({"terminate": 1}, "Terminate only the current verdict's cleanup identities."),
                "stop._stop.gone": ({"process_table": 1}, "Positive absence/reuse recheck, never root admission."),
            },
            "omp_strata/ompcfg.py": {
                "_native_cache_busy": ({"table": 1}, "Linux native-cache retirement only; not server admission."),
            },
            "omp_strata/procs.py": {
                "_proc_children": ({"_proc_stat": 1}, "Legacy procfs child reader."),
                "_ps": ({"_proc_stat": 1}, "Legacy fallback when ps is absent."),
                "children": ({"_parents": 1, "_proc_children": 1}, "Legacy platform child readers."),
                "descendants": ({"children": 1, "info": 2}, "Legacy descendant walk."),
                "info": ({"_open": 1, "_parents": 1, "_ps": 1}, "Legacy identity readers."),
                "matches": ({"info": 1}, "Legacy individual comparison; verdict does not use it."),
                "process_memory": ({"_open": 1}, "Legacy resource observation, not identity comparison."),
                "table": ({"info": 1}, "Reader piece uses Windows identity lookup inside accounted snapshot."),
                "terminate": ({"_open": 1, "info": 6}, "Legacy termination primitives on both platforms."),
            },
            "scripts/gpu_inventory.py": {
                "inventory": ({"memory": 1}, "Machine inventory, not root admission."),
            },
            "scripts/realhost_gates.py": {
                "SlotWatch.run": ({"table": 1, "descendants": 1}, "Observe the gate's live client tree before a worker is reparented."),
                "SlotWatch.finish": ({"table": 2}, "Check client exit and recheck a worker that disappeared during inspection."),
                "Sampler._sample_once": ({"memory": 1}, "Existing resource sampling."),
                "g10": ({"memory": 1}, "Existing resource gate."),
                "g15": ({"terminate": 2}, "Existing realhost engine fault injection, outside this piece."),
                "g20": ({"matches": 1}, "Unmigrated cleanup gate; no-match still means no leftover (#94)."),
                "kill_tree": ({"descendants": 1, "info": 1, "terminate": 2}, "Existing gate cleanup, outside this piece."),
                "server_tree": ({"matches": 1, "descendants": 1}, "Unmigrated gate tree; no-match still means empty (#94)."),
                "status_json": ({"running": 3}, "Local HTTP metrics count, not the retired root running() decision."),
                "tree_memory": ({"process_memory": 1}, "Existing process resource sampling."),
                "watch_tree": ({"descendants": 1}, "Existing gate process-tree sampling."),
            },
        }
        expected = Counter()
        for path, owners in retained.items():
            for owner, (readers, reason) in owners.items():
                self.assertTrue(reason)
                expected.update({(path, owner, reader): count for reader, count in readers.items()})
        self.assertEqual(expected, self.legacy_reader_uses())


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
        self.stop_changed_cells = self.base_order_exceptions = 0
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
        self.assertEqual(3956, combinations)
        self.assertEqual(320, self.base_order_exceptions, "only vouched child precedence may change base order")
        self.combinations, self.seconds = combinations, time.monotonic() - started
        print(f"\nstate-table walk: {combinations} combinations, {self.stop_changed_cells} runtime-signal expectations changed, {self.base_order_exceptions} base-order child-precedence exceptions in {self.seconds:.1f} s", file=sys.stderr)
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
        # Runtime-only membership prevents completion, but is never authority to signal.
        # Advice still offers structurally admitted cleanup, not a promise of completion.
        runtime_only = {proc.pid for role, proc in verdict.live.items() if role.startswith("unrecorded[")}
        selected = {proc.pid for role, proc in verdict.live.items() if not role.startswith("unrecorded[")}
        admitted_stop = lifecycle._stop_custody_refusal(verdict.run) is None
        self.stop_changed_cells += bool(runtime_only and admitted_stop)
        from tests.unit.test_lifecycle_stop import BaseStopOrderWalk
        base = BaseStopOrderWalk.base_order(run, world)
        review_live = verdict.live if readable else {
            role: world[identity["pid"]] for role, identity in lifecycle.recorded_processes(run)
            if identity and identity["pid"] in world and native_matches(world[identity["pid"]], identity) is not None}
        reviewed = [proc.pid for role, proc in BaseStopOrderWalk.reviewed_order(review_live, verdict.under)
                    if not role.startswith("unrecorded[")]
        selected_world = {proc.pid: proc for role, proc in review_live.items() if not role.startswith("unrecorded[")}
        terminated.clear()
        recorded_alive = {proc.pid for role, identity in lifecycle.recorded_processes(run)
                          if identity and (proc := world.get(int(identity["pid"]))) is not None
                          and native_matches(proc, identity) is not None}
        try:
            lifecycle.stop(self.layout, log=lambda line: None)
            refused = False
        except lifecycle.LifecycleError as exc:
            refused = True
            refusal = str(exc)
        advises = any("run `stop`" in problem for problem in verdict.problems)
        self.assertFalse(refused and advises and not runtime_only, verdict)
        if admitted_stop:
            self.assertEqual(reviewed, terminated, "recorded/descendant sequence differs from reviewed 502fc31f")
            base_recorded = [p.pid for p in base if p.pid in recorded_alive]
            # Stable base order, subject only to child-before-recorded-ancestor precedence.
            precedes = set()
            for child in recorded_alive:
                parent = selected_world[child].ppid
                while parent in selected_world:
                    if parent in recorded_alive:
                        precedes.add((child, parent))
                    parent = selected_world[parent].ppid
            expected = []
            pending = list(base_recorded)
            while pending:
                first = next(pid for pid in pending if not any(
                    child in pending and parent == pid for child, parent in precedes))
                expected.append(first)
                pending.remove(first)
            self.base_order_exceptions += expected != base_recorded
            self.assertEqual(expected, [pid for pid in terminated if pid in recorded_alive], verdict)
            self.assertLessEqual(set(terminated) - {p.pid for p in base},
                                 {p.pid for role, p in verdict.live.items() if role.startswith("descendant[")})
            if readable:
                self.assertEqual(selected, set(terminated), verdict)
                for pid in runtime_only:
                    self.assertTrue(refused)
                    self.assertEqual(1, refusal.count(f"pid {pid}"), refusal)
        if refused:
            self.assertTrue(verdict.row in STOP_REFUSES or (token and not lifecycle.WINDOWS) or runtime_only, verdict)
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
        self.assertIsNone(result)
        self.assertIn("pid 20; end it by hand", str(failure))
        self.assertEqual({12}, set(self.ended))

    def test_job_scan_proves_empty_after_census_cleanup_not_before(self):
        self.world()
        self.missing_job = True
        self.job.scan.side_effect = lambda *args, **kwargs: dict(self.processes)
        for token in ("unproved", "proved"):
            with self.subTest(token=token), patch.object(lifecycle, "WINDOWS", True):
                self.configure(token=token)
                result, failure = self.stop_result()
                self.assertIsNone(result)
                self.assertIn("pid 20; end it by hand", str(failure))
                self.assertEqual({12}, set(self.ended))

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
                self.assertEqual({12}, set(self.ended))
                self.assertIn("pid 20; end it by hand", str(failure))
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
                self.assertNotIn(20, self.ended)
                self.assertIn("pid 20; end it by hand", str(failure))
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
        seen, cases = set(), 0
        for windows, missing, token, state, unpublished, alive in itertools.product(
                (False, True), (False, True), ("none", "unproved", "proved"),
                ("launching", "starting", "ready", "stop_incomplete"), (False, True), (False, True)):
            with self.subTest(case=(windows, missing, token, state, unpublished, alive)), \
                    patch.object(lifecycle, "WINDOWS", windows):
                cases += 1
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
                _, cleanup_failure = self.stop_result()
                if alive and failure is None:
                    self.assertIn("pid 20; end it by hand", str(cleanup_failure))
                    self.assertNotIn(20, self.ended)
                else:
                    self.assertFalse(advises and cleanup_failure, texts)
                if state == "ready" and alive and not unpublished:
                    self.assertTrue(any("outside its recorded trees" in text for text in report["problems"]))
        self.assertIn("server-live", seen)
        self.assertEqual(192, cases)

    def test_extended_product_preserves_admission_properties(self):
        self.world()
        faults = ("valid", "corrupt", "io", "null", "list", "scalar")
        failures, cases, changed, started = [], 0, 0, time.monotonic()
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
                    self.reads.clear()
                    result, failure = self.stop_result()
                    if 20 in self.ended:
                        raise AssertionError("runtime-only process was signalled")
                    if alive and lifecycle._stop_custody_refusal(root.run) is None:
                        selection_reads = schedule[:2] if token == "none" or run_kind != "valid" else schedule[1:]
                        changed += any(selection_reads)
                    if result and not (self.reads and self.reads[-1] == (True, {})):
                        raise AssertionError("stopped without a final read empty census")
                    if result and not (valid and all(schedule)):
                        raise AssertionError("stopped despite failed evidence")
                except Exception as exc:
                    if len(failures) < 12:
                        failures.append((case, type(exc).__name__, str(exc)))
        print(f"\nextended evidence walk: {cases} combinations, {changed} runtime-signal expectations changed in {time.monotonic() - started:.2f} s", file=sys.stderr)
        self.assertEqual(16128, cases)
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
                _, cleanup_failure = self.stop_result()
                if row in ("server-live", "orphans"):
                    self.assertIn("pid 20; end it by hand", str(cleanup_failure))
                    self.assertNotIn(20, self.ended)
                else:
                    self.assertFalse(advises and cleanup_failure, texts)
                cases += 1
        for rows in seen.values():
            self.assertEqual(set(lifecycle.ROWS), rows)
        print(f"\nadvice row table: {cases} cases, all rows on both platform flags", file=sys.stderr)
        self.assertEqual(52, cases)


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
        """Reissue runtime-only numbers between census observations, never via a stop signal."""
        engine = str(self.layout.strata / "engine" / "strata")
        original = {10: ident(10, 1, engine), 11: ident(11, 10, engine)}
        world = dict(reversed(list(original.items()))) if reverse else dict(original)
        snapshots = []
        issued = 0

        def table():
            nonlocal issued
            if snapshots and event != "none" and issued < generations:
                issued += 1
                previous = original[reused_pid]
                created = str(int(previous.created) + 100 * issued) if event == "creation" else previous.created
                exe = f"{engine}-{issued}" if event == "executable" else engine
                world[reused_pid] = procs.ProcInfo(reused_pid, 1, created, exe)
            snapshots.append(dict(world))
            return complete_table(world)

        atomic_write_json(self.layout.run_record, dict(self.install, state="ready"))
        with patch.object(lifecycle, "process_table", side_effect=table), \
                patch.object(procs, "terminate") as terminate, \
                patch.object(lifecycle, "port_in_use", return_value=False):
            with self.assertRaises(lifecycle.LifecycleError) as failure:
                lifecycle.stop(self.layout, log=lambda line: None)
            after = lifecycle.verdict(self.layout)
        terminate.assert_not_called()
        self.assertEqual({10, 11}, set(world))
        self.assertEqual({10, 11}, {proc.pid for proc in after.live.values()})
        self.assertFalse(after.idle or after.quiescent)
        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])
        for pid in (10, 11):
            # Same counter + changed image is UNKNOWN, not proof of a replacement.
            unknown_images = generations if event == "executable" and pid == reused_pid else 0
            self.assertEqual(1 + unknown_images, str(failure.exception).count(f"pid {pid}"))
            if unknown_images:
                for generation in range(generations + 1):
                    name = "strata" + (f"-{generation}" if generation else "")
                    self.assertEqual(1, str(failure.exception).count(f"{name} pid {pid}"))
        if event != "none":
            self.assertNotEqual(original[reused_pid], snapshots[1][reused_pid])
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
        self.assertEqual(24, cases)
        print(f"\nstop identity walk: {cases} schedules, {snapshots} snapshots in "
              f"{time.monotonic() - started:.3f} s", file=sys.stderr)


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
                    elif point == 8:
                        with self.assertRaises(lifecycle.LifecycleError) as failure:
                            lifecycle.stop(layout, log=lambda line: None)
                        survivor = identities[-1]
                        self.assertIsNotNone(procs.matches(survivor.as_dict()))
                        self.assertEqual(1, str(failure.exception).count(f"pid {survivor.pid}"))
                        self.assertIn("by hand", str(failure.exception))
                        self.assertFalse(lifecycle.verdict(layout).idle)
                        self.assertEqual("stop_incomplete", read_json(layout.run_record)["state"])
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
        self.assertEqual(9, point + 1)
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
