import copy
from pathlib import Path
import tempfile
import unittest

from omp_strata.common import atomic_write_json, read_json, sha256_file
from omp_strata.receipts import gate_inventory, make_receipt, update_ledger, validate_receipt, write_receipt


def receipt(**changes):
    values = dict(gate_id="G01", status="pass", execution_boundary="host_free",
                  expected="Invalid identities are rejected", observed="Changed hash rejected",
                  implementation_commit="a" * 40, profile_id="synthetic-profile",
                  identity_fingerprint="b" * 64,
                  evidence=[dict(kind="test_report", path_or_ref="report.json", sha256="c" * 64, scrubbed=True)])
    values.update(changes)
    return make_receipt(**values)


class ReceiptTests(unittest.TestCase):
    def test_pass_and_unavailable_metrics(self):
        data = receipt(metrics=[dict(name="cache", value=None, unit="tokens", boundary="engine", method="unavailable")])
        self.assertEqual([], validate_receipt(data))
        data["metrics"][0]["method"] = "server_reported"
        self.assertTrue(validate_receipt(data))

    def test_pass_requires_evidence_and_exact_identities(self):
        for changes in ({"evidence": []}, {"implementation_commit": None},
                        {"implementation_commit": "a" * 39}, {"identity_fingerprint": None},
                        {"identity_fingerprint": "g" * 64}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                receipt(**changes)
        for boundary, gate in (("real_host", "G10"), ("evaluation", "G24")):
            with self.subTest(boundary=boundary), self.assertRaises(ValueError):
                receipt(gate_id=gate, execution_boundary=boundary, profile_id=None)

    def test_mock_cannot_pass_hardware_or_evaluation(self):
        for gate in ("G11", "G24"):
            for boundary in ("source", "host_free"):
                with self.subTest(gate=gate, boundary=boundary), self.assertRaises(ValueError):
                    receipt(gate_id=gate, execution_boundary=boundary)

    def test_blocked_and_not_applicable_require_nonblank_reasons(self):
        for status in ("blocked", "not_applicable"):
            for reason in (None, "", "  "):
                with self.subTest(status=status, reason=reason), self.assertRaises(ValueError):
                    receipt(status=status, reason=reason)
            self.assertEqual([], validate_receipt(receipt(status=status, reason="Unavailable hardware")))

    def test_timestamp_type_and_unknown_fields(self):
        for value in ("2026-09-30T12:00:00+00:00", "2026-02-30T00:00:00Z", "yesterday"):
            with self.subTest(timestamp=value), self.assertRaises(ValueError):
                receipt(timestamp_utc=value)
        data = receipt()
        data["schema_version"] = True
        self.assertTrue(validate_receipt(data))
        data = receipt()
        data["evidence"][0]["secret"] = "unexpected"
        self.assertTrue(validate_receipt(data))
        data = receipt()
        data["metrics"] = [dict(name="wall", value=float("nan"), unit="ms", boundary="request", method="calculated")]
        self.assertTrue(validate_receipt(data))

    def test_append_only_history_newest_timestamp_wins_and_runs_unique(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = dict(profile_id="synthetic-profile", profile_fingerprint="b" * 64,
                          gates=[dict(copy.deepcopy(g), receipts=[]) for g in gate_inventory().values()])
            path = root / "qualification.json"
            atomic_write_json(path, ledger)
            first = write_receipt(root, receipt(run_id="first", timestamp_utc="2026-09-30T10:00:00Z"))
            update_ledger(path, first)
            later = write_receipt(root, receipt(run_id="later", status="fail", timestamp_utc="2026-09-30T11:00:00Z"))
            update_ledger(path, later)
            old = write_receipt(root, receipt(run_id="older", timestamp_utc="2026-09-30T09:00:00Z"))
            update_ledger(path, old)
            gate = next(g for g in read_json(path)["gates"] if g["id"] == "G01")
            self.assertEqual("fail", gate["status"])
            self.assertEqual(["first.json", "later.json", "older.json"], gate["receipt_paths"])
            self.assertEqual(sha256_file(first), gate["receipts"][0]["sha256"])
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "duplicate run_id"):
                update_ledger(path, first)
            self.assertEqual(before, path.read_bytes())
            with self.assertRaises(FileExistsError):
                write_receipt(root, read_json(first))
            first.write_text("{}")
            next_receipt = write_receipt(root, receipt(run_id="newest"))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                update_ledger(path, next_receipt)
            self.assertEqual(before, path.read_bytes())

    def test_receipt_filename_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_receipt(Path(tmp), receipt(run_id="../escape"))
