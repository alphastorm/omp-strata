"""Role-schema, released-writer null and reader-edge contracts; host-free."""
import itertools
import json
from unittest.mock import patch

from omp_strata import cli, lifecycle, procs
from omp_strata.common import atomic_write_json
from types import SimpleNamespace
from tests.unit.test_lifecycle_evidence import EvidenceFixture, complete_table


class RecordedRoleShapeWalk(EvidenceFixture):
    def test_present_roles_are_never_silently_absent(self):
        states = (None, "launching", "starting", "ready", "exited", "stopped", "stop_incomplete")
        forms = ("omitted", "null", "empty", "not-object", "missing-pid", "missing-created", "missing-exe",
                 "wrong-pid", "wrong-created", "wrong-exe", "duplicate-null-valid", "duplicate-valid-null", "valid")
        cases = 0
        identity = self.process(created="20").as_dict()
        survivor = self.process(pid=77, created="77")
        for role, state, windows, form, remaining in itertools.product(
                ("wrapper", "server", "engine", "launcher", "server_tree[0]"), states, (False, True), forms, (False, True)):
            with self.subTest(role=role, state=state, windows=windows, form=form, remaining=remaining), \
                    patch.object(lifecycle, "WINDOWS", windows), patch.object(procs, "WINDOWS", windows):
                cases += 1
                self.world.clear()
                if remaining:
                    self.world[survivor.pid] = survivor
                run = {} if state is None else {"state": state}
                key = "server_tree" if role == "server_tree[0]" else role
                value = dict(identity)
                if form == "null":
                    value = None
                elif form == "empty":
                    value = {}
                elif form == "not-object":
                    value = "not an identity"
                elif form.startswith("missing-"):
                    value.pop(form.removeprefix("missing-"))
                elif form.startswith("wrong-"):
                    field = form.removeprefix("wrong-")
                    value[field] = "20" if field == "pid" else 101
                if form != "omitted":
                    run[key] = [value] if key == "server_tree" else value
                if form.startswith("duplicate-"):
                    good = [identity] if key == "server_tree" else identity
                    run[key] = None if form == "duplicate-null-valid" else good
                    second = good if form == "duplicate-null-valid" else None
                    text = json.dumps(run)[:-1] + "," + json.dumps(key) + ":" + json.dumps(second) + "}"
                else:
                    text = json.dumps(run)
                self.layout.run_record.write_text(text)
                invalid = form not in ("omitted", "valid") and not (role == "engine" and form == "null")
                root = lifecycle.verdict(self.layout)
                self.assertEqual(invalid, root.row == "unreadable-record")
                self.assertEqual({77} if remaining else set(), {p.pid for p in root.live.values()})
                if invalid:
                    self.assertFalse(root.idle or root.quiescent)
                    self.assertIn("run", root.details["unreadable_records"])
                    if state == "stopped" and not windows and not remaining:
                        with self.assertRaises(lifecycle.LifecycleError):
                            lifecycle.start(self.layout, tool_argv=["fixture"], log=lambda _: None)
                        with patch.object(cli, "_layout", return_value=self.layout), \
                                patch.object(cli.install_mod, "install") as install:
                            with self.assertRaises(lifecycle.LifecycleError):
                                cli.cmd_install(SimpleNamespace(idle_generation=None))
                            install.assert_not_called()
                        with self.assertRaises(lifecycle.LifecycleError):
                            lifecycle.idle_generation(self.layout)
                else:
                    self.assertEqual(not remaining and state != "launching", root.quiescent)
        self.assertEqual(1820, cases)

    def test_server_tree_collection_requires_a_list_of_identities(self):
        for value in (None, {}, "", 0, [None], [{}], []):
            with self.subTest(value=value):
                atomic_write_json(self.layout.run_record, {"state": "stopped", "server_tree": value})
                root = lifecycle.verdict(self.layout)
                self.assertEqual(value != [], root.row == "unreadable-record")
                self.assertEqual(value == [], root.quiescent)

    def test_released_engine_null_is_identical_to_an_omitted_role(self):
        for state, alive in itertools.product(("starting", "ready", "exited", "stopped", "stop_incomplete"), (False, True)):
            with self.subTest(state=state, alive=alive):
                server = self.process(created="20")
                self.world.clear()
                if alive:
                    self.world[server.pid] = server
                run = {"state": state, "server": server.as_dict(), "server_tree": []}
                atomic_write_json(self.layout.run_record, run)
                before = lifecycle.verdict(self.layout)
                atomic_write_json(self.layout.run_record, {**run, "engine": None})
                after = lifecycle.verdict(self.layout)
                self.assertEqual((before.row, before.state, before.quiescent, before.live, before.details),
                                 (after.row, after.state, after.quiescent, after.live, after.details))


class LauncherEvidenceTests(EvidenceFixture):
    def test_missing_gone_and_unidentified_launcher_have_distinct_reasons(self):
        launcher = self.process(created="20", owned=False)
        for kind, expected in (("missing", "launch-unrecorded"), ("gone", "launch-abandoned"),
                               ("unidentified", "unreadable-table")):
            with self.subTest(kind=kind):
                run = {"state": "launching"}
                if kind != "missing":
                    run["launcher"] = launcher.as_dict()
                atomic_write_json(self.layout.run_record, run)
                unknown = {launcher.pid} if kind == "unidentified" else set()
                with patch.object(lifecycle, "process_table", return_value=complete_table(unidentified=unknown)):
                    root = lifecycle.verdict(self.layout)
                    self.assertEqual(expected, root.row)
                    self.assertFalse(root.idle or root.quiescent)
                    message = " ".join(root.problems)
                    if kind == "missing":
                        self.assertIn("identity is not recorded", message)
                    if kind != "gone":
                        self.assertNotIn("is gone", message)


class VouchedParentEdgeWalk(EvidenceFixture):
    def test_verdict_consumes_only_reader_vouched_edges(self):
        cases = 0
        for source, delta, windows in itertools.product(("windows", "procfs", "ps"), (-1, 0, 1), (False, True)):
            with self.subTest(source=source, delta=delta, windows=windows), patch.object(procs, "WINDOWS", windows):
                cases += 1
                if source == "windows":
                    stamps = "100", str(100 + delta)
                elif source == "procfs":
                    stamps = "starttime:100", "starttime:" + str(100 + delta)
                else:
                    stamps = "Fri Nov 13 12:34:56 2026", f"Fri Nov 13 12:34:{56 + delta:02d} 2026"
                parent = procs.ProcInfo(20, 1, stamps[0], "/outside/python")
                child = procs.ProcInfo(21, 20, stamps[1], "/outside/helper")
                atomic_write_json(self.layout.run_record, {"server": parent.as_dict()})
                table = complete_table({20: parent, 21: child})
                table = procs._checked_table(table.identified, table.unidentified)
                with patch.object(lifecycle, "process_table", return_value=table):
                    root = lifecycle.verdict(self.layout)
                self.assertEqual({20, 21} if delta >= 0 else {20}, {p.pid for p in root.live.values()})
                self.assertEqual(delta >= 0, 21 in root.under)
        self.assertEqual(18, cases)
