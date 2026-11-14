"""Stop selection, evidence and ordering in accounted host-free process worlds."""
import itertools
from unittest.mock import patch

from omp_strata import lifecycle, procs
from omp_strata.common import atomic_write_json, read_json
from tests.unit.test_lifecycle_evidence import EvidenceFixture, complete_table, native_matches


class UnidentifiedRoleStopWalk(EvidenceFixture):
    def test_unknown_recorded_role_never_completes_stop(self):
        import itertools
        cases = 0
        for role, state in itertools.product(("wrapper", "server", "engine", "server_tree[0]", "launcher"),
                (None, "launching", "starting", "ready", "exited", "stopped", "stop_incomplete")):
            with self.subTest(role=role, state=state):
                run = dict(self.install, state=state)
                process = self.process()
                if role == "server_tree[0]":
                    run["server_tree"] = [process.as_dict()]
                else:
                    run[role] = process.as_dict()
                atomic_write_json(self.layout.run_record, run)
                with patch.object(lifecycle, "process_table", return_value=complete_table(unidentified={20})), \
                        patch.object(procs, "matches", return_value=None), patch.object(procs, "terminate") as terminate:
                    with self.assertRaisesRegex(lifecycle.LifecycleError, "cannot prove absence or PID reuse"):
                        lifecycle.stop(self.layout, log=lambda line: None, locked=True)
                    terminate.assert_not_called()
                saved = read_json(self.layout.run_record)
                self.assertEqual("stop_incomplete", saved["state"])
                self.assertNotIn("tree_verified_empty", saved)
                cases += 1
        self.assertEqual(35, cases)


class UncertainCleanupTests(EvidenceFixture):
    def test_unknown_roles_retain_identified_cleanup(self):
        cases = 0
        for role in ("wrapper", "server", "engine", "server_tree[0]", "launcher"):
            with self.subTest(role=role):
                self.ended.clear()
                unknown = self.process(owned=False).as_dict()
                run = {"state": "launching" if role == "launcher" else "ready"}
                run["server_tree" if role == "server_tree[0]" else role] = [unknown] if role == "server_tree[0]" else unknown
                self.world = {77: self.process(pid=77)}
                atomic_write_json(self.layout.run_record, run)
                with patch.object(lifecycle, "process_table", side_effect=lambda: complete_table(self.world, unidentified={20})), \
                        patch.object(procs, "matches", return_value=None), \
                        patch.object(procs, "terminate", side_effect=self.terminate):
                    with self.assertRaisesRegex(lifecycle.LifecycleError, "cannot prove absence or PID reuse") as failure:
                        lifecycle.stop(self.layout, log=None, locked=True)
                self.assertIn(role, str(failure.exception))
                self.assertIn("pid 20", str(failure.exception))
                self.assertEqual([77], [p.pid for p in self.ended])
                self.assertEqual({}, self.world)
                saved = read_json(self.layout.run_record)
                self.assertEqual("stop_incomplete", saved["state"])
                self.assertNotIn("tree_verified_empty", saved)
                cases += 1
        self.assertEqual(5, cases)

    def test_malformed_roles_never_reach_individual_fallback(self):
        good = self.process(pid=77, owned=False)
        bads = ({}, "bad identity", {"pid": "20", "created": "20", "exe": "/foreign/engine"},
                {"pid": 20, "created": "20"})
        cases = 0
        for role, bad in zip(("wrapper", "server", "engine", "server_tree[0]"), bads):
            with self.subTest(role=role):
                self.ended.clear()
                self.world = {77: good}
                run = {"state": "ready", "server" if role != "server" else "wrapper": good.as_dict()}
                run["server_tree" if role == "server_tree[0]" else role] = [bad] if role == "server_tree[0]" else bad
                atomic_write_json(self.layout.run_record, run)
                before = self.layout.run_record.read_bytes()
                def matches(record):
                    self.assertTrue(procs.valid_identity(record), "malformed role reached native reader")
                    return native_matches(self.world.get(record["pid"]), record)
                with patch.object(lifecycle, "process_table", side_effect=procs.TableUnavailable("fixture unavailable")), \
                        patch.object(procs, "matches", side_effect=matches), \
                        patch.object(procs, "terminate", side_effect=self.terminate):
                    with self.assertRaises(lifecycle.LifecycleError):
                        lifecycle.stop(self.layout, log=None, locked=True)
                self.assertEqual([77], [p.pid for p in self.ended])
                self.assertEqual(before, self.layout.run_record.read_bytes())
                cases += 1
        self.assertEqual(4, cases)

    def test_last_owner_cleanup_activates_uncertain_launcher(self):
        self.world = {77: self.process(pid=77)}
        atomic_write_json(self.layout.run_record, {"state": "ready", "launcher": self.process(owned=False).as_dict()})
        with patch.object(lifecycle, "process_table", side_effect=lambda: complete_table(self.world, unidentified={20})), \
                patch.object(procs, "terminate", side_effect=self.terminate):
            self.assertEqual("orphans", lifecycle.verdict(self.layout).row)
            with self.assertRaisesRegex(lifecycle.LifecycleError, "launcher pid 20"):
                lifecycle.stop(self.layout, log=None, locked=True)
        self.assertEqual([77], [p.pid for p in self.ended])
        self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])


class StopOrderWalk(EvidenceFixture):
    def test_outside_intermediary_does_not_grant_ownership_or_order(self):
        ancestor = self.process(pid=50)
        outsider = procs.ProcInfo(51, 50, "51", "/outside/helper")
        server = procs.ProcInfo(20, 51, "20", "/outside/server")
        self.world = {50: ancestor, 51: outsider, 20: server}
        atomic_write_json(self.layout.run_record, {"state": "ready", "server": server.as_dict()})
        with patch.object(procs, "terminate", side_effect=self.terminate):
            result = lifecycle.stop(self.layout, log=None, locked=True)
            final = lifecycle.verdict(self.layout)
        self.assertEqual([50, 20], [p.pid for p in self.ended])
        self.assertEqual({51: outsider}, self.world)
        self.assertEqual(("stopped", {}), (result["state"], final.live))

    def test_entire_vouched_tree_precedes_its_ancestors(self):
        cases = 0
        for reverse, uncertain, tree_reverse in itertools.product((False, True), repeat=3):
            with self.subTest(reverse=reverse, uncertain=uncertain, tree_reverse=tree_reverse):
                self.ended.clear()
                edges = {10: 1, 50: 0 if uncertain else 10, 20: 50, 30: 20, 40: 30, 60: 20, 70: 1}
                rows = [procs.ProcInfo(pid, parent, str(pid), str(self.layout.strata / f"p{pid}"))
                        for pid, parent in edges.items()]
                self.world = {p.pid: p for p in (reversed(rows) if reverse else rows)}
                tree = [self.world[30].as_dict(), self.world[60].as_dict()]
                run = {"state": "ready", "wrapper": self.world[10].as_dict(), "server": self.world[20].as_dict(),
                       "engine": self.world[40].as_dict(), "server_tree": list(reversed(tree)) if tree_reverse else tree}
                atomic_write_json(self.layout.run_record, run)
                def end(proc, timeout):
                    self.assertEqual("stop_incomplete", read_json(self.layout.run_record)["state"])
                    return self.terminate(proc, timeout)
                with patch.object(procs, "terminate", side_effect=end):
                    result = lifecycle.stop(self.layout, log=None, locked=True)
                self.assertEqual("stopped", result["state"])
                self.assertEqual(set(edges), {p.pid for p in self.ended})
                positions = {p.pid: index for index, p in enumerate(self.ended)}
                for child in edges:
                    parent = edges[child]
                    while parent in edges:
                        self.assertLess(positions[child], positions[parent], (child, parent, positions))
                        parent = edges[parent]
                self.assertEqual({}, self.world)
                cases += 1
        self.assertEqual(8, cases)
