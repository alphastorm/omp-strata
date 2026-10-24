"""Recorded GitHub/HF metadata only: no model files, host access, service or scheduler."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import discover_candidates as discovery
from scripts.upstream_watch import API, Incomplete

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/candidate_metadata.json"


class RecordedMetadata(unittest.TestCase):
    def setUp(self):
        self.responses = json.loads(FIXTURE.read_text())["responses"]
        self.seen = []

    def transport(self, url, headers):
        self.seen.append((url, dict(headers)))
        return copy.deepcopy(self.responses[url]), {}

    def discover(self):
        return discovery.discover(API(self.transport, token="fixture"), observed="2026-10-24T00:00:00Z")

    def test_named_sources_resolve_immutable_metadata_without_assets(self):
        rows = self.discover()
        self.assertEqual(6, len(rows))
        self.assertTrue(all(discovery.SHA40.fullmatch(row["pinned_revision"]) for row in rows))
        self.assertEqual(3, sum("model_card_blob" in row for row in rows))
        self.assertTrue(all(row["disposition"] != "active" for row in rows))
        for url, headers in self.seen:
            self.assertNotIn("/resolve/", url)
            self.assertNotIn("/download/", url)
            self.assertNotIn("/assets", url)
            if url.startswith(discovery.HF):
                self.assertNotIn("Authorization", headers)
            else:
                self.assertEqual("Bearer fixture", headers["Authorization"])
        penny = next(row for row in rows if row["candidate_id"] == "penny-royal")
        self.assertEqual("742cbc5d6ea466d60280392e2dc232fa3079adfa", penny["pinned_revision"])
        self.assertEqual("Apache-2.0", penny["license"])

    def test_annotated_tag_is_peeled_not_the_release_branch(self):
        url = discovery.GITHUB + "/repos/ashhart/TensorFold/git/ref/tags/v1.1.3"
        self.responses[url] = {"object": {"type": "tag", "sha": "a" * 40}}
        self.responses[discovery.GITHUB + "/repos/ashhart/TensorFold/git/tags/" + "a" * 40] = {
            "sha": "a" * 40, "tag": "v1.1.3", "object": {"type": "commit", "sha": "36415df4f76e4458e82d0fa729ecb28e287ebf38"}}
        row = next(row for row in self.discover() if row["candidate_id"] == "tensorfold")
        self.assertEqual("36415df4f76e4458e82d0fa729ecb28e287ebf38", row["pinned_revision"])

    def test_missing_revision_or_card_fails_before_ledger_write(self):
        url = discovery.HF + "/api/models/Qwen/Qwen3-ASR-1.7B"
        for key, value in (("sha", "main"), ("id", "other/model")):
            with self.subTest(key=key):
                previous = self.responses[url][key]
                self.responses[url][key] = value
                with self.assertRaises(Incomplete):
                    self.discover()
                self.responses[url][key] = previous
        revision = self.responses[url]["sha"]
        self.responses[discovery.HF + f"/api/models/Qwen/Qwen3-ASR-1.7B/tree/{revision}?recursive=false&expand=false"] = []
        with self.assertRaisesRegex(Incomplete, "card metadata missing"):
            self.discover()

    def test_repeat_is_idempotent_and_never_reactivates_rejected_pin(self):
        rows = self.discover()
        existing = copy.deepcopy(rows)
        existing[0]["disposition"] = "rejected"
        merged, count = discovery.merge_rows(existing, rows + rows)
        self.assertEqual(0, count)
        self.assertEqual(existing, merged)
        self.assertEqual("rejected", merged[0]["disposition"])

    def test_three_active_pins_cap_and_disposition_receipts(self):
        rows = self.discover()
        for row in rows[:3]:
            row["disposition"] = "active"
        discovery.validate_rows(rows)
        rows[3]["disposition"] = "active"
        with self.assertRaisesRegex(Incomplete, "maximum 3"):
            discovery.validate_rows(rows)
        receipt = dict(rows[0], disposition="rejected")
        discovery.validate_rows([*rows, receipt])

    def test_atomic_update_dry_run_and_contending_writer(self):
        rows = self.discover()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            self.assertEqual(6, discovery.update_ledger(path, rows, dry_run=True))
            self.assertFalse(path.exists())
            self.assertEqual(6, discovery.update_ledger(path, rows))
            before = path.read_bytes()
            self.assertEqual(0, discovery.update_ledger(path, rows))
            self.assertEqual(before, path.read_bytes())
            lock = path.with_suffix(".jsonl.lock")
            lock.write_text("other writer")
            with self.assertRaisesRegex(Incomplete, "locked"):
                discovery.update_ledger(path, rows)
            self.assertEqual("other writer", lock.read_text())
            self.assertEqual(before, path.read_bytes())

    def test_partial_discovery_cannot_publish_a_partial_daily_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text("unchanged\n")
            with patch.object(discovery, "LEDGER", path), patch.object(discovery, "API", side_effect=Incomplete("offline")):
                self.assertEqual(1, discovery.main(["--ledger", str(path)]))
            self.assertEqual("unchanged\n", path.read_text())

    def test_seed_retains_six_packet_admission_decisions(self):
        rows = discovery.read_ledger(discovery.LEDGER)
        seed = rows[:6]
        self.assertEqual(["nvfp4-qad", "penny-royal", "tensorfold", "strata-024", "upstream-models-quants", "ocr-asr"],
                         [row["candidate_id"] for row in seed])
        self.assertEqual(["active", "conditional", "conditional", "parked", "watch", "watch"],
                         [row["disposition"] for row in seed])
