"""Public-safe evidence and immutable route ledger contracts."""
import copy
from pathlib import Path
import tempfile
import unittest

from omp_strata.common import atomic_write_json, read_json, sha256_file
from omp_strata.receipts import make_receipt, validate_receipt
from omp_strata.remote import RemoteError
from scripts.fanout_proof import delivered_results, new_intervals, overlap
from scripts.verify_release import refresh_route_draft, verify

REPO = Path(__file__).resolve().parents[2]
ROUTE = "client-rtxpro6000-strata0.1.41-omp18.8.6"
# A draft server profile that is never qualified (its RTX 4090 was removed).
UNQUALIFIED_SERVER = "win11-rtx4090-coder-iq1m-131k-strata0.1.36-omp18.4.12"


class RemoteEvidenceTests(unittest.TestCase):
    def test_overlap_counts_service_intervals_not_serial_elapsed_time(self):
        self.assertEqual({"peak_active": 1, "overlap_seconds": 0}, overlap([(1, 2), (2, 3)]))
        self.assertEqual({"peak_active": 3, "overlap_seconds": 2}, overlap([(1, 4), (2, 5), (3, 3.5)]))

    def test_history_binds_instance_and_refuses_overflow_or_faults(self):
        before = {"count": 5, "since": 100}
        after = {"count": 6, "since": 100, "offset": 10, "rows": [{"time": 20, "duration_s": 2, "finish": "stop"}]}
        self.assertEqual([(10, 12)], new_intervals(before, after))
        for key, value in (("count", 7), ("since", 101), ("rows", [{"time": 20, "duration_s": -1, "finish": "stop"}]),
                           ("rows", [{"time": 20, "duration_s": 2, "finish": "disconnect"}])):
            with self.subTest(key=key), self.assertRaises(RemoteError):
                new_intervals(before, {**after, key: value})

    def test_delivery_requires_completed_result_not_assignment_echo(self):
        result = '<task-result id="ScoutOne" agent="scout" status="completed"><output>{"answer":"CORRECT"}</output></task-result>'
        user = lambda text: {"type": "message", "message": {"role": "user", "content": text}}
        self.assertEqual({}, delivered_results([user("Assignment: return CORRECT")]))
        delivery = lambda text: {"type": "custom_message", "customType": "async-result", "content": text}
        self.assertEqual({}, delivered_results([user(result)]), "user prompt echoes cannot count as delivery")
        self.assertEqual({}, delivered_results([delivery(result.replace('status="completed"', 'status="failed"'))]))
        self.assertEqual({"ScoutOne": {"answer": "CORRECT"}}, delivered_results([delivery(result)]))
        self.assertEqual({}, delivered_results([{"message": {"role": "assistant", "content": result}}]), "a parent cannot invent delivery")

    def test_host_free_receipt_cannot_pass_real_host_g23(self):
        kwargs = dict(gate_id="G23", execution_boundary="host_free", profile_id="fixture-route", identity_fingerprint="a" * 64,
                      implementation_commit="b" * 40, expected="Every remote scenario passes", observed="Scripted fixtures only",
                      evidence=[dict(kind="test_report", path_or_ref="summary.json", sha256="c" * 64, scrubbed=True)])
        self.assertEqual([], validate_receipt(make_receipt(status="not_run", **kwargs)))
        with self.assertRaisesRegex(ValueError, "execution_boundary"):
            make_receipt(status="pass", **kwargs)


class ClientRouteLedgerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.route_path = self.root / "route.json"
        self.manifest_path = self.root / "manifest.json"
        self.ledger_path = self.root / "qualification.json"
        self.data = read_json(REPO / "routes" / (ROUTE + ".json"))
        self.manifest = read_json(REPO / "releases" / ROUTE / "manifest.json")
        self.ledger = read_json(REPO / "releases" / ROUTE / "qualification.json")
        self.manifest["profile"]["path"] = "route.json"
        atomic_write_json(self.route_path, self.data)
        atomic_write_json(self.ledger_path, self.ledger)
        self.manifest["qualification"]["ledger_sha256"] = sha256_file(self.ledger_path)
        atomic_write_json(self.manifest_path, self.manifest)

    def test_unqualified_route_is_valid_but_g23_and_servers_block_readiness(self):
        self.assertEqual([], verify(self.manifest_path)["errors"])
        errors = verify(self.manifest_path, require_ready=True)["errors"]
        self.assertTrue(any("G23: required gate is not_run" in error for error in errors))
        self.assertFalse(any("server profile is not independently qualified" in error for error in errors),
                         "the route's server is qualified on its own ledger")
        self.assertFalse(any("G10: required gate" in error for error in errors), "local evidence is not copied to the client ledger")
        self.data["members"][0]["server_profile"] = UNQUALIFIED_SERVER
        atomic_write_json(self.route_path, self.data)
        refresh_route_draft(self.manifest_path)
        self.assertEqual([], verify(self.manifest_path)["errors"])
        errors = verify(self.manifest_path, require_ready=True)["errors"]
        self.assertTrue(any("server profile is not independently qualified: " + UNQUALIFIED_SERVER in error
                            for error in errors))

    def test_draft_refresh_rebinds_server_change_without_receipt_inheritance(self):
        self.data["members"][0]["server_fingerprint"] = "f" * 64
        atomic_write_json(self.route_path, self.data)
        self.assertTrue(verify(self.manifest_path)["errors"])
        refresh_route_draft(self.manifest_path)
        self.assertEqual([], verify(self.manifest_path)["errors"])
        self.assertEqual("not_run", read_json(self.ledger_path)["gates"][0]["status"])
        self.assertEqual([], read_json(self.ledger_path)["gates"][0]["receipts"])

    def test_measured_route_cannot_be_refreshed_or_downgraded(self):
        for field, value in (("receipts", [{"path": "old.json", "sha256": "a" * 64}]), ("status", "fail")):
            with self.subTest(field=field):
                ledger = copy.deepcopy(self.ledger)
                ledger["gates"][0][field] = value
                atomic_write_json(self.ledger_path, ledger)
                before = [p.read_bytes() for p in (self.route_path, self.manifest_path, self.ledger_path)]
                with self.assertRaisesRegex(ValueError, "receipt history"):
                    refresh_route_draft(self.manifest_path)
                self.assertEqual(before, [p.read_bytes() for p in (self.route_path, self.manifest_path, self.ledger_path)])


if __name__ == "__main__":
    unittest.main()
