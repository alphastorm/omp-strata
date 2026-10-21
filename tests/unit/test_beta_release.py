"""Owner-selected release metadata only; no binary downloads or host access."""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json, read_json, release_version
from scripts import campaign, upstream_watch as watch
from tests.unit import test_upstream_watch
from tests.unit.test_upstream_watch import FixtureTransport

ROOT = Path(__file__).resolve().parents[2]
TAG = "v0.2.0-beta"
COMMIT = "3d1fb48090e8f2cefc22d7b5845fb7f5b71f33fa"
TAG_OBJECT = "b73dbce3edb8dac72a5642f46d1273197008fc4d"
RELEASE_ID = 417326565
BASE = watch.GITHUB + "/repos/" + watch.REPOS["strata"]
COMPONENTS = (
    (656392166, "strata-control-0.1.45.3-windows-x86_64.zip", 72019100,
     "b783c80a77f4f3928d00387062c8b2fdd528d5cb9a400aacf4da5bcf3a2468f2"),
    (656404728, "strata-engine-0.1.45.3-windows-x86_64-cuda-cuda13.tar.gz", 579788606,
     "1b3845ecc3a46644ddc11e5296ab3d35026dbf650041c53657c43874682d1559"),
    (656401254, "strata-engine-0.1.45.3-windows-x86_64-cuda-cuda12.tar.gz", 818382624,
     "909ef954f93dcc9a5a3e756b6ac7836b9731b10f0fbe6e22ae316a1ede3da1f7"),
)


def fixture(tag=TAG, identifier=RELEASE_ID):
    assets = [{"id": aid, "name": name, "size": size, "digest": "sha256:" + digest,
               "state": "uploaded",
               "browser_download_url": f"https://github.com/Niko1221/Strata/releases/download/{tag}/{name}"}
              for aid, name, size, digest in COMPONENTS]
    # Missing publisher digests are inventory facts, never executable artifact pins.
    assets.append({"id": 4, "name": "notes.txt", "size": 12, "digest": None, "state": "uploaded",
                   "browser_download_url": f"https://github.com/Niko1221/Strata/releases/download/{tag}/notes.txt"})
    release = {"id": identifier, "tag_name": tag, "draft": False, "prerelease": False,
               "immutable": False, "published_at": "2026-10-19T13:52:01Z", "assets": assets}
    responses = {
        BASE + "/releases/tags/" + tag: (release, {}),
        BASE + f"/releases/{identifier}": (copy.deepcopy(release), {}),
        BASE + f"/releases/{identifier}/assets?per_page=100": (assets, {}),
        BASE + "/git/ref/tags/" + tag: ({"object": {"type": "tag", "sha": TAG_OBJECT}}, {}),
        BASE + "/git/tags/" + TAG_OBJECT: ({"sha": TAG_OBJECT, "tag": tag,
                                          "object": {"type": "commit", "sha": COMMIT}}, {}),
    }
    return watch.API(FixtureTransport(responses)), responses


def discover(api):
    return watch.discover_release(api, watch.REPOS["strata"], TAG, allow_prerelease=True)


class BetaParsingTests(unittest.TestCase):
    def test_checked_in_beta_campaign_is_only_frozen_metadata(self):
        record = campaign.validate(read_json(ROOT / "releases/campaigns/v0.2.0-beta.json"))
        self.assertEqual((TAG, RELEASE_ID, TAG_OBJECT, COMMIT),
                         tuple(record[k] for k in ("tag", "release_id", "tag_object_sha", "peeled_commit")))
        self.assertEqual((33, 5), (len(record["assets"]), len(record["hosts"])))
        self.assertTrue(record["prerelease"])
        self.assertFalse(record["github_prerelease"])
        self.assertFalse(record["github_immutable"])
        self.assertTrue(all(row["status"] == "pending" and not row["result_refs"] for row in record["hosts"]))
        for identifier, name, size, digest in COMPONENTS:
            asset = next(a for a in record["assets"] if a["name"] == name)
            self.assertEqual((identifier, size, digest), (asset["id"], asset["bytes"], asset["sha256"]))

    def test_beta_numbers_parse_without_claiming_stability(self):
        self.assertEqual((0, 2, 0), release_version(TAG))
        self.assertLess(watch.version(TAG), watch.version("v0.2.0"))
        self.assertLess(watch.version("v0.1.45.3"), watch.version(TAG))
        self.assertIsNone(release_version("../v0.2.0-beta"))

    def test_default_report_ignores_beta_even_when_github_calls_it_stable(self):
        report = test_upstream_watch.WatchReport(methodName="test_numeric_newer_equal_older_releases_use_newest_pin")
        report.setUp()
        self.addCleanup(report.doCleanups)
        report.responses[report.strata_url] = ([{
            "tag_name": TAG, "draft": False, "prerelease": False,
            "html_url": "https://github.com/Niko1221/Strata/releases/tag/" + TAG,
            "published_at": "2026-10-19T13:52:01Z",
        }], {})
        result = report.report()
        self.assertEqual((True, 0), (result["complete"], result["exit_code"]))
        self.assertEqual([], result["releases"]["strata"]["newer"])
        self.assertEqual("prerelease", result["releases"]["strata"]["skipped"][0]["reason"])
        (report.root / "profiles/beta.json").write_text(json.dumps(
            {"strata": {"tag": TAG}, "omp": {"tag": "v18.4.10"}}))
        (report.root / "releases/beta").mkdir()
        (report.root / "releases/beta/manifest.json").write_text(json.dumps({"status": "qualified"}))
        self.assertEqual("v0.1.34", report.report()["releases"]["strata"]["pinned"])


class BetaInventoryTests(unittest.TestCase):
    def test_opt_in_freezes_tag_and_complete_publisher_inventory(self):
        api, _ = fixture()
        snapshot = discover(api)
        self.assertEqual((TAG, RELEASE_ID, TAG_OBJECT, COMMIT),
                         tuple(snapshot[k] for k in ("tag", "release_id", "tag_object_sha", "peeled_commit")))
        self.assertTrue(snapshot["prerelease"])
        self.assertFalse(snapshot["github_prerelease"])
        self.assertFalse(snapshot["github_immutable"])
        self.assertEqual(4, len(snapshot["assets"]))
        for identifier, name, size, digest in COMPONENTS:
            asset = next(a for a in snapshot["assets"] if a["name"] == name)
            self.assertEqual((identifier, size, digest), (asset["id"], asset["bytes"], asset["sha256"]))
        unhashed = next(a for a in snapshot["assets"] if a["name"] == "notes.txt")
        self.assertIsNone(unhashed["sha256"])
        self.assertTrue(unhashed["url"].endswith("/notes.txt"))

    def test_beta_requires_explicit_opt_in_independent_of_github_flag(self):
        api, _ = fixture()
        result = watch.discover_release(api, watch.REPOS["strata"], TAG)
        self.assertEqual({"state": "skipped", "tag": TAG, "reason": "prerelease"}, result)

    def test_release_id_endpoint_must_agree_with_tag_endpoint(self):
        api, responses = fixture()
        responses[BASE + f"/releases/{RELEASE_ID}"][0]["published_at"] = "2026-10-19T14:00:00Z"
        with self.assertRaisesRegex(watch.Incomplete, "changed|identity"):
            discover(api)

    def test_paginated_assets_require_complete_matching_inventory(self):
        api, responses = fixture()
        endpoint = BASE + f"/releases/{RELEASE_ID}/assets?per_page=100"
        assets = responses[endpoint][0]
        next_url = endpoint + "&page=2"
        responses[endpoint] = (assets[:2], {"link": f'<{next_url}>; rel="next"'})
        responses[next_url] = (assets[2:], {})
        self.assertEqual(4, len(discover(api)["assets"]))
        responses[next_url] = ([], {})
        with self.assertRaisesRegex(watch.Incomplete, "incomplete|changed"):
            discover(api)
        responses[endpoint] = (assets * 25, {})
        with self.assertRaisesRegex(watch.Incomplete, "full API page"):
            discover(api)

    def test_invalid_asset_ids_duplicates_digests_and_urls_are_refused(self):
        for key, value in (("id", None), ("id", True), ("size", 0),
                           ("digest", "sha512:abc"), ("browser_download_url", "https://example.com/other")):
            api, responses = fixture()
            for url in (BASE + "/releases/tags/" + TAG, BASE + f"/releases/{RELEASE_ID}"):
                responses[url][0]["assets"][0][key] = value
            responses[BASE + f"/releases/{RELEASE_ID}/assets?per_page=100"][0][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(watch.Incomplete):
                discover(api)

    def test_duplicate_asset_names_and_ids_are_refused(self):
        for key in ("name", "id"):
            api, responses = fixture()
            for url in (BASE + "/releases/tags/" + TAG, BASE + f"/releases/{RELEASE_ID}"):
                rows = responses[url][0]["assets"]
                rows[1][key] = rows[0][key]
            rows = responses[BASE + f"/releases/{RELEASE_ID}/assets?per_page=100"][0]
            rows[1][key] = rows[0][key]
            with self.subTest(key=key), self.assertRaisesRegex(watch.Incomplete, "duplicated"):
                discover(api)

    def test_moving_tag_during_discovery_is_refused(self):
        api, _ = fixture()
        get = api.get
        calls = []

        def moving(url):
            data, headers = get(url)
            if "/git/ref/" in url:
                calls.append(url)
                if len(calls) > 1:
                    return {"object": {"type": "commit", "sha": "c" * 40}}, headers
            return data, headers

        with patch.object(api, "get", side_effect=moving), self.assertRaisesRegex(watch.Incomplete, "changed"):
            discover(api)

    def test_component_selection_requires_explicit_variant_not_app_version(self):
        snapshot = discover(fixture()[0])
        for variant in ("cuda12", "cuda13"):
            selected = watch.select_strata_assets(snapshot, platform="windows-x86_64", backend="cuda", variant=variant)
            self.assertEqual("components", selected["layout"])
            self.assertEqual("0.1.45.3", selected["component_version"])
            self.assertNotIn("control", selected)
            self.assertTrue(selected["engine"]["name"].endswith(f"cuda-{variant}.tar.gz"))
        for options in ({}, {"variant": "cuda11"}, {"platform": "windows-arm64", "variant": "cuda13"}):
            with self.subTest(options=options), self.assertRaises(watch.Incomplete):
                watch.select_strata_assets(snapshot, **options)

    def test_existing_single_zip_selection_is_preserved(self):
        snapshot = discover(fixture()[0])
        legacy = {"id": 10, "name": "strata-windows-x64.zip", "bytes": 123, "sha256": "a" * 64,
                  "url": "https://github.com/Niko1221/Strata/releases/download/v0.1.45/strata-windows-x64.zip"}
        snapshot["assets"] = [legacy]
        selected = watch.select_strata_assets(snapshot)
        self.assertEqual(("single-zip", legacy), (selected["layout"], selected["engine"]))

    def test_unhashed_inventory_is_not_an_executable_pin(self):
        snapshot = discover(fixture()[0])
        unhashed = next(asset for asset in snapshot["assets"] if asset["sha256"] is None)
        with self.assertRaisesRegex(watch.Incomplete, "no complete immutable pin"):
            watch.artifact_pin(snapshot, unhashed)

    def test_control_count_and_version_never_affect_engine_selection(self):
        for versions in ([], ["0.1.46"], ["0.1.46", "0.1.46.1", "0.1.46.2", "0.1.46.3"]):
            snapshot = discover(fixture()[0])
            snapshot["assets"] = [a for a in snapshot["assets"] if not a["name"].startswith("strata-control-")]
            snapshot["assets"] += [{"name": f"strata-control-{v}-windows-x86_64.zip"} for v in versions]
            with self.subTest(versions=versions):
                self.assertEqual("0.1.45.3", watch.select_strata_assets(snapshot, variant="cuda13")["component_version"])

    def test_missing_duplicate_and_multiple_engine_versions_are_refused(self):
        for kind in ("missing", "duplicate", "another-version"):
            snapshot = discover(fixture()[0])
            engine = next(a for a in snapshot["assets"] if "cuda13" in a["name"])
            if kind == "missing":
                snapshot["assets"].remove(engine)
            else:
                extra = dict(engine)
                if kind == "another-version":
                    extra["name"] = extra["name"].replace("0.1.45.3", "0.1.46")
                snapshot["assets"].append(extra)
            with self.subTest(kind=kind), self.assertRaisesRegex(watch.Incomplete, "missing or ambiguous"):
                watch.select_strata_assets(snapshot, variant="cuda13")

    def test_stable_component_check_supports_only_explicit_cuda13_without_archive_io(self):
        with tempfile.TemporaryDirectory() as folder:
            for variant, supported in (("cuda13", True), ("cuda12", False)):
                with self.subTest(variant=variant), patch.object(watch, "inspect_archive") as inspect:
                    result = watch.draft(fixture("v0.2.1")[0], Path(folder), None, strata_tag="v0.2.1",
                                         omp_tag=None, profile_id=None, strata_src=None, check=True, variant=variant)
                self.assertEqual(supported, result["install_supported"])
                inspect.assert_not_called()
                if supported:
                    self.assertIn("archive, source and dependency review still applies", result["install_note"])
            self.assertEqual([], list(Path(folder).iterdir()))


class BetaCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        stable = read_json(ROOT / "releases/campaigns/v0.1.45.json")
        # Rows in each state; the committed record's later coalescing into a newer stable release is not part of this
        # fixture.
        for row, status in zip(stable["hosts"], ("running", "failed", "qualified", "pending", "queued")):
            row.pop("superseded_by", None)
            row["disposition_notes"] = [n for n in row["disposition_notes"] if "coalesced into" not in n]
            row["status"] = status
        stable["status"] = "running"
        self.stable_path = campaign.campaign_path(self.root, stable["tag"])
        atomic_write_json(self.stable_path, stable)
        self.stable_bytes = self.stable_path.read_bytes()
        rows = campaign.host_rows(ROOT, TAG)
        self.builder = patch.object(campaign, "host_rows", return_value=rows)
        self.builder.start()
        self.addCleanup(self.builder.stop)

    def open(self, api=None, **options):
        return campaign.open_campaign(api or fixture()[0], self.root, TAG, allow_prerelease=True, **options)

    def test_opt_in_uses_new_schema_and_never_supersedes_any_stable_rows(self):
        record = self.open()
        self.assertEqual(2, record["schema_version"])
        self.assertTrue(record["prerelease"])
        self.assertEqual([], campaign.validate(record)["hosts"][0]["result_refs"])
        self.assertEqual(self.stable_bytes, self.stable_path.read_bytes())
        path = campaign.campaign_path(self.root, TAG)
        before = path.read_bytes()
        self.open()
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(self.stable_bytes, self.stable_path.read_bytes())
        # Reopening a stable campaign cannot use the numerically newer beta to coalesce its pending rows.
        campaign.coalesce(self.root, campaign.campaigns(self.root))
        self.assertEqual(self.stable_bytes, self.stable_path.read_bytes())
        self.assertEqual(before, path.read_bytes())

    def test_beta_schema_requires_prerelease_and_complete_asset_fields(self):
        record = self.open()
        for remove in ("prerelease", "github_prerelease", "github_immutable"):
            changed = copy.deepcopy(record)
            changed.pop(remove)
            with self.subTest(remove=remove), self.assertRaises(ValueError):
                campaign.validate(changed)
        changed = copy.deepcopy(record)
        changed["prerelease"] = False
        with self.assertRaises(ValueError):
            campaign.validate(changed)
        for remove in ("id", "url", "sha256", "bytes"):
            changed = copy.deepcopy(record)
            changed["assets"][0].pop(remove)
            with self.subTest(remove=remove), self.assertRaises(ValueError):
                campaign.validate(changed)

    def test_moved_tag_replaced_removed_assets_refuse_without_rewriting_evidence(self):
        self.open()
        path = campaign.campaign_path(self.root, TAG)
        before = path.read_bytes()
        for kind in ("tag", "asset-id", "missing", "digest", "published"):
            api, responses = fixture()
            if kind == "tag":
                responses[BASE + "/git/tags/" + TAG_OBJECT][0]["object"]["sha"] = "c" * 40
            else:
                releases = [responses[BASE + "/releases/tags/" + TAG][0],
                            responses[BASE + f"/releases/{RELEASE_ID}"][0]]
                if kind == "published":
                    for release in releases:
                        release["published_at"] = "2026-10-19T14:00:00Z"
                else:
                    assets = copy.deepcopy(responses[BASE + f"/releases/{RELEASE_ID}/assets?per_page=100"][0])
                    if kind == "missing":
                        assets.pop()
                    else:
                        assets[0]["id" if kind == "asset-id" else "digest"] = 100 if kind == "asset-id" else "sha256:" + "f" * 64
                    for release in releases:
                        release["assets"] = assets
                    responses[BASE + f"/releases/{RELEASE_ID}/assets?per_page=100"] = (assets, {})
            with self.subTest(kind=kind), self.assertRaisesRegex(watch.Incomplete, "moved tag or changed"):
                self.open(api)
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(self.stable_bytes, self.stable_path.read_bytes())

    def test_check_prints_frozen_inventory_without_writes(self):
        with patch.object(campaign, "ROOT", self.root), patch.object(campaign, "API", return_value=fixture()[0]), \
                patch.object(campaign, "auth_token", return_value=None), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            code = campaign.main(["open", "--release", TAG, "--allow-prerelease", "--check"])
        self.assertEqual(0, code)
        self.assertEqual(RELEASE_ID, json.loads(stdout.getvalue())["release_id"])
        self.assertFalse(campaign.campaign_path(self.root, TAG).exists())
        self.assertEqual(self.stable_bytes, self.stable_path.read_bytes())

    def test_watch_metadata_check_needs_no_source_checkout_or_profile(self):
        with patch.object(watch, "ROOT", self.root), patch.object(watch, "API", return_value=fixture()[0]), \
                patch.object(watch, "auth_token", return_value=None), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            code = watch.main(["draft", "--release", TAG, "--allow-prerelease", "--check", "--variant", "cuda13"])
        self.assertEqual(0, code)
        result = json.loads(stdout.getvalue())
        self.assertEqual(COMMIT, result["source_release"]["peeled_commit"])
        self.assertEqual("components", result["assets"]["layout"])
        self.assertFalse(result["install_supported"])
        self.assertFalse((self.root / "profiles").exists())

    def test_watch_metadata_check_also_refuses_drift_against_frozen_campaign(self):
        self.open()
        api, responses = fixture()
        responses[BASE + "/git/tags/" + TAG_OBJECT][0]["object"]["sha"] = "c" * 40
        with patch.object(watch, "ROOT", self.root), patch.object(watch, "API", return_value=api), \
                patch.object(watch, "auth_token", return_value=None), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            code = watch.main(["draft", "--release", TAG, "--allow-prerelease", "--check", "--variant", "cuda13"])
        self.assertEqual(2, code)
        self.assertIn("moved tag or changed", json.loads(stdout.getvalue())["error"])

    def test_campaign_cli_refuses_to_claim_a_runnable_beta_draft(self):
        for flags in ([], ["--allow-prerelease"]):
            with patch.object(campaign, "ROOT", self.root), patch.object(campaign, "API", return_value=fixture()[0]), \
                    patch.object(campaign, "auth_token", return_value=None), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = campaign.main(["open", "--release", TAG, *flags])
            self.assertEqual(2, code)
            self.assertIn("docs/UPSTREAM-BETA.md", json.loads(stdout.getvalue())["reason"])
        self.assertTrue(campaign.campaign_path(self.root, TAG).exists())
        self.assertEqual(self.stable_bytes, self.stable_path.read_bytes())

    def test_watch_refuses_component_profile_before_reading_source_or_writing(self):
        for allow in (False, True):
            with self.subTest(allow=allow), self.assertRaises(watch.Incomplete) as caught:
                watch.draft(fixture()[0], self.root, Path("unused.json"), strata_tag=TAG, omp_tag="v18.10.1",
                            profile_id="fixture-beta", strata_src=Path("unused-source"),
                            allow_prerelease=allow, variant="cuda13")
            self.assertIn("beta component drafting is refused" if allow else "--allow-prerelease", str(caught.exception))
        self.assertFalse((self.root / "profiles").exists())
        self.assertFalse((self.root / "releases/fixture-beta").exists())


if __name__ == "__main__":
    unittest.main()
