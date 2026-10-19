"""File-backed campaign restart/replay and metadata fixtures; never admits a host."""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json, read_json, release_version
from scripts import campaign
from scripts.upstream_watch import API, GITHUB, Incomplete, REPOS
from tests.unit.test_upstream_watch import FixtureTransport

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "releases/campaigns/v0.1.45.json"


def fixture_api(tag="v0.1.45", identifier=415634879, commit="a" * 40, **changes):
    assets = [{"id": 1, "name": "strata-windows-x64.zip", "digest": "sha256:" + "b" * 64,
               "size": 1234, "state": "uploaded",
               "browser_download_url": f"https://github.com/Niko1221/Strata/releases/download/{tag}/strata-windows-x64.zip"}]
    release = {"id": identifier, "tag_name": tag, "draft": False, "prerelease": False,
               "immutable": False, "published_at": "2026-10-17T06:53:17Z", "assets": assets, **changes}
    base = GITHUB + "/repos/" + REPOS["strata"]
    responses = {
        base + "/releases/tags/" + tag: (release, {}),
        base + f"/releases/{identifier}": (copy.deepcopy(release), {}),
        base + f"/releases/{identifier}/assets?per_page=100": (assets, {}),
        base + "/git/ref/tags/" + tag: ({"object": {"type": "commit", "sha": commit}}, {}),
    }
    return API(FixtureTransport(responses)), responses


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.hosts = campaign.host_rows(ROOT, "v0.1.45")
        self.row_builder = patch.object(campaign, "host_rows", return_value=copy.deepcopy(self.hosts))
        self.row_builder.start()
        self.addCleanup(self.row_builder.stop)

    def open(self, tag="v0.1.45", identifier=415634879, **changes):
        api, _ = fixture_api(tag, identifier, **changes)
        # Each generation gets distinct, convention-preserving profile ids.
        with patch.object(campaign, "host_rows", return_value=[{
            **copy.deepcopy(row), "profile_id": row["profile_id"].replace("strata0.1.45-", "strata" + tag[1:] + "-")
        } for row in self.hosts]):
            return campaign.open_campaign(api, self.root, tag)

    def test_duplicate_open_is_byte_stable_and_preserves_discovery_time(self):
        first = self.open()
        path = campaign.campaign_path(self.root, first["tag"])
        before = path.read_bytes()
        second = self.open()
        self.assertEqual(first, second)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(1, len(campaign.campaigns(self.root)))

    def test_restart_reload_keeps_independent_host_progress_and_receipts(self):
        record = self.open()
        profile = record["hosts"][0]["profile_id"]
        campaign.set_host(self.root, record["tag"], profile, "queued")
        campaign.set_host(self.root, record["tag"], profile, "running")
        restored = campaign.campaigns(Path(str(self.root)))[0]
        self.assertEqual("running", restored["status"])
        self.assertEqual("running", restored["hosts"][0]["status"])
        self.assertEqual("pending", restored["hosts"][1]["status"])
        reopened = self.open()
        self.assertEqual(restored, reopened)

    def test_newer_release_coalesces_pending_only(self):
        record = self.open()
        record["hosts"][0]["status"] = "running"
        record["hosts"][1]["status"] = "qualified"
        record["hosts"][1]["result_refs"] = ["releases/kept/manifest.json"]
        record["hosts"][1]["restored_state_ref"] = "releases/kept/restoration.json"
        record["hosts"][2]["status"] = "queued"
        record["status"] = "running"
        atomic_write_json(campaign.campaign_path(self.root, record["tag"]), record)
        protected = copy.deepcopy(record["hosts"][:3])
        self.open("v0.1.46", 415634880)
        previous, newer = campaign.campaigns(self.root)
        self.assertEqual(protected, previous["hosts"][:3])
        self.assertTrue(all(row["superseded_by"] == "v0.1.46" for row in previous["hosts"][3:]))
        self.assertEqual("running", previous["status"])
        self.assertEqual("pending", newer["status"])
        self.assertIn("coalesced", previous["hosts"][-1]["disposition_notes"][-1])

    def test_completed_campaign_is_never_modified(self):
        record = self.open()
        for row in record["hosts"]:
            row["status"] = "qualified"
        record["status"] = "complete"
        path = campaign.campaign_path(self.root, record["tag"])
        atomic_write_json(path, record)
        before = path.read_bytes()
        self.open("v0.1.46", 415634880)
        self.assertEqual(before, path.read_bytes())

    def test_all_pending_campaign_becomes_superseded_and_cannot_admit(self):
        old = self.open()
        self.open("v0.1.46", 415634880)
        previous = campaign.campaigns(self.root)[0]
        self.assertEqual("superseded", previous["status"])
        with self.assertRaisesRegex(ValueError, "immutable"):
            campaign.set_host(self.root, old["tag"], old["hosts"][0]["profile_id"], "queued")

    def test_interrupted_coalescing_converges_on_duplicate_open(self):
        self.open()
        original = campaign.atomic_write_json
        calls = []

        def interrupt(path, record):
            calls.append(record["tag"])
            if len(calls) == 2:
                raise OSError("interrupted after new campaign persisted")
            original(path, record)

        with patch.object(campaign, "atomic_write_json", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.open("v0.1.46", 415634880)
        self.assertEqual(2, len(campaign.campaigns(self.root)))
        self.open("v0.1.46", 415634880)
        self.assertEqual("superseded", campaign.campaigns(self.root)[0]["status"])

    def test_moved_tag_changed_assets_or_release_id_refuses_without_writes(self):
        self.open()
        path = campaign.campaign_path(self.root, "v0.1.45")
        before = path.read_bytes()
        for changes in ({"commit": "c" * 40}, {"identifier": 5}, {"published_at": "2026-10-17T07:00:00Z"}):
            api, _ = fixture_api(**changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(Incomplete, "moved tag or changed"):
                campaign.open_campaign(api, self.root, "v0.1.45")
        api, responses = fixture_api()
        for url, (payload, _) in responses.items():
            if "/releases/" in url:
                rows = payload["assets"] if isinstance(payload, dict) else payload
                rows[0]["digest"] = "sha256:" + "d" * 64
        with self.assertRaisesRegex(Incomplete, "changed release/assets"):
            campaign.open_campaign(api, self.root, "v0.1.45")
        self.assertEqual(before, path.read_bytes())

    def test_incomplete_metadata_is_unavailable_and_does_not_create_campaign(self):
        for changes in ({"assets": []}, {"draft": None}, {"prerelease": None}, {"published_at": None}):
            api, _ = fixture_api(**changes)
            with self.subTest(changes=changes), self.assertRaises(Incomplete):
                campaign.open_campaign(api, self.root, "v0.1.45")
        self.assertEqual([], campaign.campaigns(self.root))

    def test_incomplete_asset_endpoint_is_unavailable(self):
        api, responses = fixture_api()
        responses[GITHUB + "/repos/" + REPOS["strata"] + "/releases/415634879/assets?per_page=100"] = ([], {})
        with self.assertRaisesRegex(Incomplete, "unavailable"):
            campaign.open_campaign(api, self.root, "v0.1.45")

    def test_draft_and_prerelease_are_explicit_skips(self):
        for field in ("draft", "prerelease"):
            api, _ = fixture_api(**{field: True})
            self.assertEqual({"state": "skipped", "tag": "v0.1.45", "reason": field},
                             campaign.open_campaign(api, self.root, "v0.1.45"))
        self.assertEqual([], campaign.campaigns(self.root))

    def test_invalid_host_transition_and_missing_evidence_are_refused(self):
        record = self.open()
        profile = record["hosts"][0]["profile_id"]
        with self.assertRaisesRegex(ValueError, "invalid host transition"):
            campaign.set_host(self.root, record["tag"], profile, "qualified")
        campaign.set_host(self.root, record["tag"], profile, "queued")
        campaign.set_host(self.root, record["tag"], profile, "running")
        with self.assertRaisesRegex(ValueError, "verified release manifest"):
            campaign.set_host(self.root, record["tag"], profile, "qualified")
        with self.assertRaisesRegex(ValueError, "repository-relative"):
            campaign.set_host(self.root, record["tag"], profile, "failed", result="../private.json")
        campaign.set_host(self.root, record["tag"], profile, "blocked", note="Waiting for host owner")
        with self.assertRaisesRegex(ValueError, "invalid host transition"):
            campaign.set_host(self.root, record["tag"], profile, "running")
        campaign.set_host(self.root, record["tag"], profile, "queued")

    def test_ready_qualification_uses_existing_verifier_and_restoration_reference(self):
        record = self.open()
        profile = record["hosts"][0]["profile_id"]
        campaign.set_host(self.root, record["tag"], profile, "queued")
        campaign.set_host(self.root, record["tag"], profile, "running")
        result = f"releases/{profile}/manifest.json"
        restored = f"releases/{profile}/restoration.json"
        atomic_write_json(self.root / result, {"candidate_id": profile, "status": "qualified"})
        atomic_write_json(self.root / restored, {"restored": True})
        with patch.object(campaign, "verify", return_value={"status": "qualified", "errors": ["failed gate"]}):
            with self.assertRaisesRegex(ValueError, "ready qualified"):
                campaign.set_host(self.root, record["tag"], profile, "qualified", result=result, restored_state=restored)
        with patch.object(campaign, "verify", return_value={"status": "qualified", "errors": []}) as verifier:
            done = campaign.set_host(self.root, record["tag"], profile, "qualified", result=result, restored_state=restored)
            verifier.assert_called_once_with((self.root / result).resolve(), require_ready=True)
        self.assertEqual([result], done["hosts"][0]["result_refs"])
        self.assertEqual(restored, done["hosts"][0]["restored_state_ref"])

    def test_cli_unavailable_exit_is_not_success(self):
        with patch.object(campaign, "ROOT", self.root), patch.object(campaign, "auth_token", return_value=None), \
                patch.object(campaign, "open_campaign", side_effect=Incomplete("partial response")), \
                patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(4, campaign.main(["open", "--release", "v0.1.45"]))
        self.assertEqual("unavailable", json.loads(stdout.getvalue())["state"])


class CampaignContractTests(unittest.TestCase):
    def test_seed_matches_contract_and_known_release_facts(self):
        record = campaign.validate(read_json(SEED))
        self.assertEqual(415634879, record["release_id"])
        self.assertEqual("477ac13cbe8e582c20484871ce459d20d82df09d", record["peeled_commit"])
        self.assertEqual("2026-10-17T06:53:17Z", record["published_at"])
        self.assertEqual(4, len(record["assets"]))
        self.assertEqual(5, len(record["hosts"]))
        self.assertTrue(all(row["status"] in campaign.TRANSITIONS for row in record["hosts"]))

    def test_predecessors_come_from_qualified_manifests_not_profile_draft_flags(self):
        rows = campaign.host_rows(ROOT, "v0.1.45")
        self.assertEqual(5, len(rows))
        for row in rows:
            self.assertEqual("qualified", read_json(ROOT / row["predecessor"]["manifest"])["status"])
            self.assertEqual("v18.10.1", row["predecessor"]["omp_tag"])
            expected = "v0.1.43.1" if row["host"] == "rtx3090-win-a" else "v0.1.44.1"
            self.assertEqual(expected, row["predecessor"]["strata_tag"])
        pair = next(row for row in rows if row["host"] == "rtx3090-win-a")
        self.assertIn("strata0.1.44.1-omp18.10.1/manifest.json", pair["disposition_notes"][-1])
        self.assertIn("Negative evidence", pair["disposition_notes"][-1])

    def test_stable_version_grammar_including_four_part_hotfix(self):
        for tag, parts in (("v0.1.44.1", (0, 1, 44, 1)), ("0.1.45", (0, 1, 45)), ("v18.10.1", (18, 10, 1))):
            self.assertEqual(parts, release_version(tag))
        self.assertLess(campaign.version("v0.1.44"), campaign.version("v0.1.44.1"))
        self.assertLess(campaign.version("v0.1.44.1"), campaign.version("v0.1.45"))
        for tag in ("v0.1.45-rc1", "v0.1", "v0.1.44.1.2", "../v0.1.45"):
            self.assertIsNone(release_version(tag))
            with self.assertRaises(Incomplete):
                campaign.campaign_path(ROOT, tag)


if __name__ == "__main__":
    unittest.main()
