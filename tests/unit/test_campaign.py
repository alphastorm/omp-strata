"""File-backed campaign restart/replay and metadata fixtures; never admits a host."""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json, read_json, release_version
from scripts import campaign
from scripts.upstream_watch import API, GITHUB, Incomplete, REPOS
from tests.unit.test_upstream_watch import FixtureTransport

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "releases/campaigns/v0.1.45.json"


def repository_before(folder: Path, tag: str) -> Path:
    """Copy what `host_rows` reads into `folder`: each lane's profiles and routes (with a route's server profile) and
    their release manifests, wherever the server pins a Strata release older than `tag`.

    `host_rows` picks each lane's newest qualified predecessor, so rows built from the live repository change meaning,
    and refuse an older tag, as soon as a newer release qualifies; historical fixtures need the repository as it stood.
    """
    limit = campaign.version(tag)
    for families, _, kind in campaign.LANES:
        for path in (p for family in families
                     for p in (ROOT / ("routes" if kind == "client-route" else "profiles")).glob(family + "-strata*.json")):
            pins = read_json(path)
            server = path if kind == "server" else ROOT / "profiles" / (pins["members"][0]["server_profile"] + ".json")
            if campaign.version(read_json(server)["strata"]["tag"]) >= limit:
                continue
            for source in {path, server}:
                for item in (source, ROOT / "releases" / source.stem / "manifest.json"):
                    if item.is_file():
                        target = folder / item.relative_to(ROOT)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(item.read_bytes())
    return folder


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
        self.hosts = campaign.host_rows(repository_before(self.root / "repository", "v0.1.45"), "v0.1.45")
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
        manifest_bytes = (self.root / result).read_bytes()
        with patch.object(campaign, "verify", return_value={"status": "qualified", "errors": []}) as verifier:
            done = campaign.set_host(self.root, record["tag"], profile, "qualified", result=result, restored_state=restored)
            verifier.assert_called_once_with((self.root / result).resolve(), require_ready=True)
        self.assertEqual([result], done["hosts"][0]["result_refs"])
        self.assertEqual(restored, done["hosts"][0]["restored_state_ref"])
        self.assertEqual(done, read_json(campaign.campaign_path(self.root, record["tag"])))
        self.assertEqual(manifest_bytes, (self.root / result).read_bytes())

    def test_qualifying_another_stock_variant_of_the_lane_renames_its_row(self):
        record = self.open()
        prepared = next(row["profile_id"] for row in record["hosts"] if row["host"] == "rtx3090-win-a")
        variant = prepared.replace("-disp4090-parking-", "-disp4090-roles-parking-")
        campaign.set_host(self.root, record["tag"], prepared, "queued")
        campaign.set_host(self.root, record["tag"], prepared, "running")
        restored = "releases/pair/restored-state.json"
        atomic_write_json(self.root / restored, {"restored": True})
        other_lane = next(row["profile_id"] for row in record["hosts"] if row["host"] == "rtxpro6000-win-a")
        with patch.object(campaign, "verify", return_value={"status": "qualified", "errors": []}):
            for wrong in (variant.replace("strata0.1.45-", "strata0.1.46-"), other_lane):
                with self.subTest(wrong=wrong), self.assertRaisesRegex(ValueError, "ready qualified"):
                    atomic_write_json(self.root / f"releases/{wrong}/manifest.json", {"candidate_id": wrong})
                    campaign.set_host(self.root, record["tag"], prepared, "qualified",
                                      result=f"releases/{wrong}/manifest.json", restored_state=restored)
            result = f"releases/{variant}/manifest.json"
            atomic_write_json(self.root / result, {"candidate_id": variant, "status": "qualified"})
            done = campaign.set_host(self.root, record["tag"], prepared, "qualified", result=result,
                                     restored_state=restored)
        row = next(row for row in done["hosts"] if row["host"] == "rtx3090-win-a")
        self.assertEqual((variant, "qualified", [result]), (row["profile_id"], row["status"], row["result_refs"]))
        self.assertIn(f"in place of the prepared {prepared}", row["disposition_notes"][-1])

    def test_cli_unavailable_exit_is_not_success(self):
        with patch.object(campaign, "ROOT", self.root), patch.object(campaign, "auth_token", return_value=None), \
                patch.object(campaign, "open_campaign", side_effect=Incomplete("partial response")), \
                patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(4, campaign.main(["open", "--release", "v0.1.45"]))
        self.assertEqual("unavailable", json.loads(stdout.getvalue())["state"])


class CampaignIntakeCoalescingTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = repository_before(Path(directory), "v0.1.45")

    def open_single(self, tag, identifier, *, omp_tag=None):
        return campaign.open_campaign(fixture_api(tag, identifier)[0], self.root, tag, omp_tag=omp_tag)

    def open_tuple(self, tag="v0.1.45", identifier=415634879, omp_tag="v18.20.0", *, omp_commit="d" * 40,
                   omp_sha256="e" * 64):
        engine = campaign.discover_release(fixture_api(tag, identifier)[0], REPOS["strata"], tag)
        omp = copy.deepcopy(engine)
        omp.update(repository=REPOS["omp"], release_id=52, tag=omp_tag, peeled_commit=omp_commit,
                   assets=[dict(id=1, name="omp-windows-x64.exe", bytes=12, sha256=omp_sha256,
                                url=f"https://github.com/{REPOS['omp']}/releases/download/{omp_tag}/omp-windows-x64.exe")])
        def discover(api, repo, selected_tag, **kwargs):
            return copy.deepcopy(omp if repo == REPOS["omp"] else engine)
        with patch.object(campaign, "discover_release", side_effect=discover):
            return campaign.open_campaign(None, self.root, tag, omp_tag=omp_tag)

    def interrupted_pair(self, *, newer_schema=2, newer_omp=None):
        older = self.open_single("v0.1.45", 415634879)
        older_path = campaign.campaign_path(self.root, older["tag"])
        older_bytes = older_path.read_bytes()
        if newer_schema == 3:
            newer = self.open_tuple("v0.1.46", 415634880, newer_omp or "v18.22.0")
        else:
            newer = self.open_single("v0.1.46", 415634880)
            if newer_omp:
                # A schema-2 campaign opened with another client pin by the historical opener.
                for row in newer["hosts"]:
                    row["profile_id"] = row["profile_id"].rsplit("-omp", 1)[0] + "-omp" + newer_omp[1:]
                atomic_write_json(campaign.campaign_path(self.root, newer["tag"]), campaign.validate(newer))
        # The newer discovery persisted, but older pending rows were not settled before interruption.
        older_path.write_bytes(older_bytes)
        return {path: path.read_bytes() for path in (self.root / "releases/campaigns").glob("*.json")}, newer

    def persisted_tuple(self, tag, identifier):
        writes = []
        original = campaign.atomic_write_json
        def persist(path, value):
            writes.append((path, value["status"]))
            original(path, value)
        with patch.object(campaign, "atomic_write_json", side_effect=persist):
            return self.open_tuple(tag, identifier), writes

    def assert_tuple_superseded_at_birth(self, *, same_engine=False):
        before, newer = self.interrupted_pair(newer_schema=3, newer_omp="v18.22.0")
        tag, identifier = ("v0.1.46", 415634880) if same_engine else ("v0.1.45", 415634879)
        record, writes = self.persisted_tuple(tag, identifier)
        self.assertEqual(3, record["schema_version"])
        self.assertEqual("superseded", record["status"])
        self.assertEqual({newer["tag"] + "+omp18.22.0"}, {row["superseded_by"] for row in record["hosts"]})
        path = campaign.campaign_path(self.root, tag, "v18.20.0")
        self.assertEqual([(path, "superseded")], writes)
        self.assertEqual(record, read_json(path))
        self.assertEqual(before, {old: old.read_bytes() for old in before})
        with self.assertRaisesRegex(ValueError, "immutable"):
            campaign.set_host(self.root, tag, record["hosts"][0]["profile_id"], "queued", omp_tag="v18.20.0")
        frozen = {file: file.read_bytes() for file in (self.root / "releases/campaigns").glob("*.json")}
        with patch.object(campaign, "atomic_write_json", side_effect=AssertionError("replay must not write")):
            self.assertEqual(record, self.open_tuple(tag, identifier))
        self.assertEqual(frozen, {file: file.read_bytes() for file in frozen})

    def assert_tuple_birth_ignores_single_tag_campaigns(self, *, same_engine=False):
        # A newer single-tag campaign is another generation: never compared with, superseding or rewritten by tuples.
        before, _ = self.interrupted_pair(newer_schema=2, newer_omp="v18.22.0")
        tag, identifier = ("v0.1.46", 415634880) if same_engine else ("v0.1.45", 415634879)
        record, writes = self.persisted_tuple(tag, identifier)
        path = campaign.campaign_path(self.root, tag, "v18.20.0")
        self.assertEqual((3, "pending"), (record["schema_version"], record["status"]))
        self.assertEqual([(path, "pending")], writes)
        self.assertEqual(record, read_json(path))
        self.assertEqual(before, {old: old.read_bytes() for old in before})
        newest = self.open_tuple("v0.1.47", 415634881, "v18.22.0")
        self.assertEqual("pending", newest["status"])
        self.assertEqual({"v0.1.47+omp18.22.0"}, {row["superseded_by"] for row in read_json(path)["hosts"]})
        self.assertEqual(before, {old: old.read_bytes() for old in before})

    def test_tuple_birth_ignores_newer_single_tag_campaign(self):
        self.assert_tuple_birth_ignores_single_tag_campaigns()

    def test_tuple_intake_preserves_legacy_when_newest_is_schema_three(self):
        self.assert_tuple_superseded_at_birth()

    def test_tuple_birth_ignores_single_tag_campaign_with_equal_engine_tag(self):
        self.assert_tuple_birth_ignores_single_tag_campaigns(same_engine=True)

    def test_tuple_birth_compares_client_when_newer_tuple_engine_tag_is_equal(self):
        self.assert_tuple_superseded_at_birth(same_engine=True)

    def test_single_tag_replay_still_settles_interrupted_historical_rows(self):
        before, _ = self.interrupted_pair()
        older_path = campaign.campaign_path(self.root, "v0.1.45")
        newer_path = campaign.campaign_path(self.root, "v0.1.46")
        self.open_single("v0.1.46", 415634880)
        previous = read_json(older_path)
        self.assertEqual("superseded", previous["status"])
        self.assertEqual({"v0.1.46"}, {row["superseded_by"] for row in previous["hosts"]})
        self.assertEqual(before[newer_path], newer_path.read_bytes())
        frozen = self.files()
        with patch.object(campaign, "atomic_write_json", side_effect=AssertionError("settled replay must not write")):
            self.open_single("v0.1.46", 415634880)
            # Naming the single-tag campaign's own client is another identity for its tuple: refused by name.
            with self.assertRaisesRegex(ValueError, re.escape("v0.1.46.json already records the same release tuple")):
                self.open_single("v0.1.46", 415634880, omp_tag="v18.10.1")
        self.assertEqual(frozen, self.files())

    def files(self):
        return {path: path.read_bytes() for path in (self.root / "releases/campaigns").glob("*.json")}

    def test_single_tag_intake_refuses_a_tuple_already_recorded_as_a_tuple_campaign(self):
        self.open_tuple("v0.1.45", 415634879, "v18.10.1")
        before = self.files()
        with self.assertRaisesRegex(ValueError, re.escape("v0.1.45+omp18.10.1.json")):
            self.open_single("v0.1.45", 415634879)
        self.assertEqual(before, self.files())
        self.assertFalse(campaign.campaign_path(self.root, "v0.1.45").exists())

    def test_tuple_intake_refuses_a_tuple_already_recorded_as_a_single_tag_campaign(self):
        single = self.open_single("v0.1.45", 415634879)
        before = self.files()
        with self.assertRaisesRegex(ValueError, re.escape("v0.1.45.json")):
            self.open_tuple("v0.1.45", 415634879, "v18.10.1")
        with self.assertRaisesRegex(ValueError, re.escape("v0.1.45.json")):
            campaign.set_host(self.root, "v0.1.45", single["hosts"][0]["profile_id"], "queued", omp_tag="v18.10.1")
        self.assertEqual(before, self.files())
        self.assertEqual("v0.1.45+omp18.10.1.json", campaign.campaign_path(self.root, "v0.1.45", "v18.10.1").name)

    def test_completed_single_tag_campaign_survives_later_tuple_intake_and_coalescing(self):
        legacy = self.open_single("v0.1.45", 415634879)
        for row in legacy["hosts"]:
            row.update(status="qualified", result_refs=["releases/kept/manifest.json"],
                       restored_state_ref="releases/kept/restored-state.json")
        legacy["status"] = "complete"
        legacy_path = campaign.campaign_path(self.root, "v0.1.45")
        atomic_write_json(legacy_path, campaign.validate(legacy))
        frozen = legacy_path.read_bytes()
        self.open_tuple("v0.1.45", 415634879, "v18.20.0")
        self.open_tuple("v0.1.46", 415634880, "v18.22.0")
        self.assertEqual(frozen, legacy_path.read_bytes())
        self.assertEqual("superseded", read_json(campaign.campaign_path(self.root, "v0.1.45", "v18.20.0"))["status"])
        # A tuple file aliasing the single-tag tuple, as an earlier opener could leave, makes intake refuse.
        directory = self.enterContext(tempfile.TemporaryDirectory())
        aliasing, self.root = self.root, repository_before(Path(directory), "v0.1.45")
        self.open_tuple("v0.1.45", 415634879, "v18.10.1")
        alias = campaign.campaign_path(self.root, "v0.1.45", "v18.10.1")
        self.root = aliasing
        campaign.campaign_path(self.root, "v0.1.45", "v18.10.1").write_bytes(alias.read_bytes())
        before = self.files()
        with self.assertRaisesRegex(ValueError, "same release tuple"):
            self.open_tuple("v0.1.47", 415634881, "v18.23.0")
        self.assertEqual(before, self.files())
        self.assertEqual(frozen, legacy_path.read_bytes())

    def test_single_tag_intake_never_coalesces_tuple_campaigns(self):
        legacy = self.open_single("v0.1.45", 415634879)
        self.open_tuple("v0.1.46", 415634880, "v18.22.0")
        tuple_path = campaign.campaign_path(self.root, "v0.1.46", "v18.22.0")
        legacy_path = campaign.campaign_path(self.root, "v0.1.45")
        before = self.files()
        self.assertEqual(legacy, self.open_single("v0.1.45", 415634879))
        self.assertEqual(before, self.files())
        self.open_single("v0.1.47", 415634881)
        self.assertEqual(before[tuple_path], tuple_path.read_bytes())
        previous = read_json(legacy_path)
        self.assertEqual("superseded", previous["status"])
        self.assertEqual({"v0.1.47"}, {row["superseded_by"] for row in previous["hosts"]})

    def test_tuple_intake_compares_only_tuple_campaigns(self):
        self.open_tuple("v0.1.45", 415634879, "v18.20.0")
        self.open_single("v0.1.46", 415634880)
        older_path = campaign.campaign_path(self.root, "v0.1.45", "v18.20.0")
        legacy_path = campaign.campaign_path(self.root, "v0.1.46")
        self.assertEqual("pending", read_json(older_path)["status"])
        legacy_bytes = legacy_path.read_bytes()
        record = self.open_tuple("v0.1.45", 415634879, "v18.22.0")
        self.assertEqual("pending", record["status"])
        previous = read_json(older_path)
        self.assertEqual("superseded", previous["status"])
        self.assertEqual({"v0.1.45+omp18.22.0"}, {row["superseded_by"] for row in previous["hosts"]})
        self.assertEqual(legacy_bytes, legacy_path.read_bytes())

    def test_single_tag_intake_is_born_superseded_and_returns_its_durable_state(self):
        self.open_single("v0.1.46", 415634880)
        path = campaign.campaign_path(self.root, "v0.1.45")
        checked = campaign.open_campaign(fixture_api("v0.1.45", 415634879)[0], self.root, "v0.1.45", check=True)
        self.assertEqual("superseded", checked["status"])
        self.assertEqual({"v0.1.46"}, {row["superseded_by"] for row in checked["hosts"]})
        self.assertFalse(path.exists())
        writes = []
        original = campaign.atomic_write_json
        def persist(target, value):
            writes.append((target, value["status"]))
            original(target, value)
        with patch.object(campaign, "atomic_write_json", side_effect=persist):
            record = self.open_single("v0.1.45", 415634879)
        self.assertEqual([(path, "superseded")], writes)
        self.assertEqual(record, read_json(path))

    def test_replay_returns_the_state_coalescing_wrote(self):
        self.interrupted_pair()
        record = self.open_single("v0.1.45", 415634879)
        self.assertEqual("superseded", record["status"])
        self.assertEqual(read_json(campaign.campaign_path(self.root, "v0.1.45")), record)

    def test_tuple_campaigns_sharing_a_client_tag_must_agree_on_its_frozen_identity(self):
        self.open_tuple("v0.1.45", 415634879, "v18.20.0")
        before = self.files()
        for changes in ({"omp_commit": "f" * 40}, {"omp_sha256": "0" * 64}):
            with self.subTest(changes=changes), self.assertRaisesRegex(Incomplete, "moved tag or changed"):
                self.open_tuple("v0.1.46", 415634880, "v18.20.0", **changes)
            self.assertEqual(before, self.files())
        self.assertEqual("pending", self.open_tuple("v0.1.46", 415634880, "v18.20.0")["status"])

    def test_qualified_tuple_host_update_binds_the_frozen_client_identity(self):
        record = self.open_tuple("v0.1.45", 415634879, "v18.20.0")
        profile = next(row["profile_id"] for row in record["hosts"] if row["host"] == "rtxpro6000-win-a")
        for status in ("queued", "running"):
            campaign.set_host(self.root, "v0.1.45", profile, status, omp_tag="v18.20.0")
        restored = "releases/restored-state.json"
        atomic_write_json(self.root / restored, {"restored": True})
        omp, asset = record["omp_release"], record["omp_release"]["assets"][0]
        result = f"releases/{profile}/manifest.json"
        def write_result(commit, sha256):
            atomic_write_json(self.root / f"releases/{profile}/profile.json", {"profile_id": profile, "omp": {
                "tag": "v18.20.0", "source_commit": commit, "artifacts": {"windows-x64": {
                    "url": asset["url"], "file": asset["name"], "bytes": asset["bytes"], "sha256": sha256}}}})
            atomic_write_json(self.root / result, {"candidate_id": profile, "status": "qualified",
                                                   "profile": {"path": "profile.json"}})
        path = campaign.campaign_path(self.root, "v0.1.45", "v18.20.0")
        with patch.object(campaign, "verify", return_value={"status": "qualified", "errors": []}):
            for commit, sha256 in (("f" * 40, asset["sha256"]), (omp["peeled_commit"], "0" * 64)):
                write_result(commit, sha256)
                before = path.read_bytes()
                with self.subTest(commit=commit, sha256=sha256), self.assertRaisesRegex(ValueError, "frozen client"):
                    campaign.set_host(self.root, "v0.1.45", profile, "qualified", result=result,
                                      restored_state=restored, omp_tag="v18.20.0")
                self.assertEqual(before, path.read_bytes())
            write_result(omp["peeled_commit"], asset["sha256"])
            done = campaign.set_host(self.root, "v0.1.45", profile, "qualified", result=result,
                                     restored_state=restored, omp_tag="v18.20.0")
        self.assertEqual("qualified", next(row for row in done["hosts"] if row["profile_id"] == profile)["status"])


class CampaignContractTests(unittest.TestCase):
    def test_same_engine_new_omp_opens_tuple_and_preserves_completed_campaign_bytes(self):
        original = ROOT / "releases/campaigns/v0.2.13.json"
        before = original.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            root = repository_before(Path(folder), "v0.2.14")
            target = root / original.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(before)
            engine = read_json(target)
            omp = {key: value for key, value in engine.items() if key in (
                "repository", "release_id", "tag", "peeled_commit", "tag_object_sha", "assets",
                "published_at", "prerelease", "github_prerelease", "github_immutable")}
            omp.update(repository=REPOS["omp"], release_id=52, tag="v18.20.0", peeled_commit="d" * 40)
            omp["assets"] = [dict(id=1, name="omp-windows-x64.exe", bytes=12, sha256="e" * 64,
                                 url=f"https://github.com/{REPOS['omp']}/releases/download/v18.20.0/omp-windows-x64.exe")]
            def discover(api, repo, tag, **kwargs):
                return copy.deepcopy(omp if repo == REPOS["omp"] else engine)
            with patch.object(campaign, "discover_release", side_effect=discover):
                first = campaign.open_campaign(None, root, "v0.2.13", omp_tag="v18.20.0")
                path = root / "releases/campaigns/v0.2.13+omp18.20.0.json"
                frozen = path.read_bytes()
                self.assertEqual(first, campaign.open_campaign(None, root, "v0.2.13", omp_tag="v18.20.0"))
                self.assertEqual(frozen, path.read_bytes())
                self.assertEqual(engine, campaign.open_campaign(None, root, "v0.2.13"))
                # The completed single-tag campaign already records this tuple: a second identity is refused by name.
                with self.assertRaisesRegex(ValueError, re.escape("v0.2.13.json already records the same release")):
                    campaign.open_campaign(None, root, "v0.2.13", omp_tag="v18.18.3")
                self.assertFalse((root / "releases/campaigns/v0.2.13+omp18.18.3.json").exists())
                omp["peeled_commit"] = "f" * 40
                with self.assertRaisesRegex(Incomplete, "changed release"):
                    campaign.open_campaign(None, root, "v0.2.13", omp_tag="v18.20.0")
            self.assertEqual(3, first["schema_version"])
            self.assertEqual("v18.20.0", first["omp_tag"])
            self.assertEqual("d" * 40, first["omp_release"]["peeled_commit"])
            self.assertTrue(all(row["profile_id"].endswith("-strata0.2.13-omp18.20.0") for row in first["hosts"]))
            self.assertTrue(all(row["predecessor"]["strata_tag"] == "v0.2.13" for row in first["hosts"]))
            profile = first["hosts"][0]["profile_id"]
            campaign.set_host(root, "v0.2.13", profile, "queued", omp_tag="v18.20.0")
            self.assertEqual(before, target.read_bytes())
            self.assertEqual(before, original.read_bytes())

    def test_tuple_predecessor_must_be_strictly_newer_and_single_tag_stays_strict(self):
        with tempfile.TemporaryDirectory() as folder:
            root = repository_before(Path(folder), "v0.2.14")
            for engine, omp in (("v0.2.13", "v18.18.3"), ("v0.2.13", "v18.18.0"),
                                ("v0.2.12", "v18.20.0"), ("v0.2.13", None)):
                with self.subTest(engine=engine, omp=omp), self.assertRaisesRegex(ValueError, "newer"):
                    campaign.host_rows(root, engine, omp)
            self.assertEqual(5, len(campaign.host_rows(root, "v0.2.13", "v18.20.0")))

    def test_tuple_coalescing_orders_client_versions_and_preserves_legacy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            legacy = read_json(ROOT / "releases/campaigns/v0.2.13.json")
            for row in legacy["hosts"]:
                row.update(status="pending", result_refs=[], restored_state_ref=None)
            legacy["status"] = "pending"
            legacy_path = campaign.campaign_path(root, legacy["tag"])
            atomic_write_json(legacy_path, legacy)
            before = legacy_path.read_bytes()
            records = []
            for omp in ("v18.19.0", "v18.20.0"):
                record = copy.deepcopy(legacy)
                snapshot = {key: record[key] for key in (
                    "repository", "release_id", "tag", "peeled_commit", "tag_object_sha", "assets",
                    "published_at", "prerelease", "github_prerelease", "github_immutable")}
                snapshot.update(repository=REPOS["omp"], tag=omp)
                for asset in snapshot["assets"]:
                    asset["url"] = f"https://github.com/{REPOS['omp']}/releases/download/{omp}/{asset['name']}"
                record = copy.deepcopy(legacy)
                record.update(schema_version=3, omp_tag=omp, omp_release=snapshot)
                for row in record["hosts"]:
                    row["profile_id"] = row["profile_id"].rsplit("-omp", 1)[0] + "-omp" + omp[1:]
                    row["status"] = "pending"
                record["status"] = "pending"
                atomic_write_json(campaign.campaign_path(root, record["tag"], omp), campaign.validate(record))
                records.append(record)
            campaign.coalesce(root, sorted([legacy, *records], key=campaign.campaign_tuple), records[-1])
            previous = read_json(campaign.campaign_path(root, legacy["tag"], "v18.19.0"))
            self.assertEqual("superseded", previous["status"])
            self.assertEqual({"v0.2.13+omp18.20.0"}, {row["superseded_by"] for row in previous["hosts"]})
            self.assertEqual(before, legacy_path.read_bytes())

    def test_seed_matches_contract_and_known_release_facts(self):
        record = campaign.validate(read_json(SEED))
        self.assertEqual(415634879, record["release_id"])
        self.assertEqual("477ac13cbe8e582c20484871ce459d20d82df09d", record["peeled_commit"])
        self.assertEqual("2026-10-17T06:53:17Z", record["published_at"])
        self.assertEqual(4, len(record["assets"]))
        self.assertEqual(5, len(record["hosts"]))
        self.assertTrue(all(row["status"] in campaign.TRANSITIONS for row in record["hosts"]))

    def test_predecessors_come_from_qualified_manifests_not_profile_draft_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            before = repository_before(Path(folder), "v0.1.45")
            rows = campaign.host_rows(before, "v0.1.45")
            manifests = [read_json(before / row["predecessor"]["manifest"]) for row in rows]
        self.assertEqual(5, len(rows))
        self.assertEqual(["qualified"] * 5, [manifest["status"] for manifest in manifests])
        for row in rows:
            self.assertEqual("v18.10.1", row["predecessor"]["omp_tag"])
            expected = "v0.1.43.1" if row["host"] == "rtx3090-win-a" else "v0.1.44.1"
            self.assertEqual(expected, row["predecessor"]["strata_tag"])
        pair = next(row for row in rows if row["host"] == "rtx3090-win-a")
        self.assertIn("strata0.1.44.1-omp18.10.1/manifest.json", pair["disposition_notes"][-1])
        self.assertIn("Negative evidence", pair["disposition_notes"][-1])

    def test_an_omp_tag_names_every_candidate_without_changing_predecessors(self):
        with tempfile.TemporaryDirectory() as folder:
            before = repository_before(Path(folder), "v0.1.45")
            rows = campaign.host_rows(before, "v0.1.45", "v18.12.6")
            for bad in ("v18.12", "v18.12.6-rc1", "../v18.12.6"):
                with self.subTest(tag=bad), self.assertRaises(Incomplete):
                    campaign.host_rows(before, "v0.1.45", bad)
        self.assertEqual(5, len(rows))
        for row in rows:
            self.assertTrue(row["profile_id"].endswith("-strata0.1.45-omp18.12.6"), row["profile_id"])
            self.assertEqual("v18.10.1", row["predecessor"]["omp_tag"])

    def test_a_newer_qualified_stock_variant_becomes_its_lanes_predecessor(self):
        default = "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1"
        roles = "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.1.44.1-omp18.10.1"
        with tempfile.TemporaryDirectory() as folder:
            before = repository_before(Path(folder), "v0.1.45")
            pins = read_json(before / f"profiles/{default}.json")
            pins["profile_id"], pins["strata"]["tag"] = roles, "v0.1.44.1"
            atomic_write_json(before / f"profiles/{roles}.json", pins)
            for status, expected in (("draft", default), ("qualified", roles)):
                atomic_write_json(before / f"releases/{roles}/manifest.json", {"candidate_id": roles, "status": status})
                pair = next(row for row in campaign.host_rows(before, "v0.1.45") if row["host"] == "rtx3090-win-a")
                with self.subTest(status=status):
                    self.assertEqual(expected, pair["predecessor"]["profile_id"])
                    self.assertEqual(expected.split("-strata")[0] + "-strata0.1.45-omp18.10.1", pair["profile_id"])

    def test_at_one_release_a_lane_prefers_its_later_listed_variant(self):
        """Variants qualified at the same Strata and OMP release rank by LANES order, not by profile-id spelling: by
        spelling, PLE direct alone ("...-pledirect-...") would outrank the per-slot MTP variant the owner made current."""
        base = "win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0"
        variants = ("win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0",
                    "win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0")
        with tempfile.TemporaryDirectory() as folder:
            before = repository_before(Path(folder), "v0.2.9")
            pins = read_json(before / f"profiles/{base}.json")
            for identifier in variants:
                atomic_write_json(before / f"profiles/{identifier}.json", {**pins, "profile_id": identifier})
                atomic_write_json(before / f"releases/{identifier}/manifest.json",
                                  {"candidate_id": identifier, "status": "qualified"})
            pro = next(row for row in campaign.host_rows(before, "v0.2.9") if row["host"] == "rtxpro6000-win-a")
        self.assertEqual(variants[1], pro["predecessor"]["profile_id"])
        self.assertEqual(variants[1].replace("strata0.2.8", "strata0.2.9"), pro["profile_id"])

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
