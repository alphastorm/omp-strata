"""Metadata fixtures and disposable git histories; no network, installers or GPU runtime."""
from __future__ import annotations

import copy
import argparse
import ast
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from omp_strata.common import flag_pairs, sha256_bytes
from omp_strata.profile import load
from scripts import upstream_watch as watch
from scripts.verify_release import verify

REPO = Path(__file__).resolve().parents[2]
PARENT = REPO / "profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10.json"
MODEL_REPO = "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF"
REVISION = "c" * 40
MTP_REVISION = "de4b8e4d43b917e7706784d8bb445c9af86a3540"
SETUP = '''
MIN_ENGINE = (0, 1, 34)
MIN_DRIVER = 580
CUDA_WHEELS = ["cuda==1"]
PY_PACKAGES = ["numpy"]
LLAMA_CPP_COMMIT = "3cf03257f219afbe7334045ff7c6a06ac68c627d"
HF_REVISIONS = {MODEL_REPO: REVISION}
MODELS = {"IQ1_M": {"arena_gb": 23.4, "ram_gb": 32, "download_gb": 58.4, "families": ("coder",)}}
LOW_RAM_HEADROOM_GB = 10
RESIDENT_ENGINE = (0, 1, 30)
CONTEXTS = [131072, 262144]
FAMILIES = {"coder": {"hf": hf(MODEL_REPO) + "{q}/", "file": "model-{q}-{i}.gguf", "tag": "coder-", "name": "coder"}}
def low_ram_needed(model, ram):
    return ram < MODELS[model]["arena_gb"] + LOW_RAM_HEADROOM_GB
def low_ram_gpu_gb(model, vram_gb, ctx=32768, kv="int8"):
    return max(0, vram_gb - 5)
def low_ram_resident(model, ram, vram_gb, ctx=32768, kv="int8"):
    return ram >= MODELS[model]["arena_gb"] - low_ram_gpu_gb(model, vram_gb) + LOW_RAM_HEADROOM_GB
def ctx_ram_need(model, ctx, low_ram=False):
    return None
def derived_factor(ctx, trained=262144):
    return max(1, float(ctx) / float(trained))
def resolve_rope(ctx, scaling, scale):
    return None, None
def main():
    need = to_fetch + 8
    args = ["--pack", str(pack), "--native", str(shards[0]), "--ple-gguf", str(ple),
            "--expert-profile", str(ROOT / "profile.bin"), "--expert-cache", "auto", "--prefill", "auto",
            "--spec", "4", "--spec-min-p", "0.5", "--mtp", str(rt), "--max-context", str(ctx), "--kv", kv]
    kv_ram_gb = ctx * 13 * 1056 / 1e9
    stream_fits = ram >= MODELS[model]["ram_gb"] + kv_ram_gb + 1
    if stream_fits:
        args += ["--kv-resident", "32768"]
    cfg = {"exe": str(eng / EXE), "args": args, "cwd": str(ROOT), "tokenizer": str(pack / "tokenizer"),
           "model_name": fam["name"] + "-" + model.lower(), "log": str(ROOT / "strata.log"),
           "lib_dirs": lib_dirs, "port": port, "host": a.host, "gpu": gpu["index"], "gpus_asked": True}
    cfg_path = ROOT / "strata.json"
    raise RuntimeError("main must never run")
'''.replace("MODEL_REPO", repr(MODEL_REPO)).replace(": REVISION}", ": " + repr(REVISION) + "}")
SERVER = '''
class Handler:
    def do_GET(self):
        if path == "/health": pass
    def do_POST(self):
        if path in ("/v1/chat/completions",): pass
'''


class FixtureTransport:
    def __init__(self, responses):
        self.responses = responses
        self.seen = []

    def __call__(self, url, headers):
        self.seen.append((url, dict(headers)))
        value = self.responses[url]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


def release(tag):
    return {"tag_name": tag, "draft": False, "prerelease": False,
            "html_url": "https://github.com/example/project/releases/tag/" + tag, "published_at": "2026-10-02T00:00:00Z"}


class WatchReport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "profiles").mkdir()
        for number, strata in enumerate(("v0.1.30", "v0.1.34")):
            (self.root / "profiles" / f"{number}.json").write_text(json.dumps(
                {"strata": {"tag": strata}, "omp": {"tag": "v18.4.10"}}))
        self.responses = {f"{watch.GITHUB}/repos/{repo}/releases?per_page=100": ([release(tag)], {})
                          for repo, tag in ((watch.REPOS["strata"], "v0.1.34"), (watch.REPOS["omp"], "v18.4.10"))}
        self.strata_url = f"{watch.GITHUB}/repos/{watch.REPOS['strata']}/releases?per_page=100"

    def report(self, tracked=()):
        return watch.report(watch.API(FixtureTransport(self.responses)), self.root, {"tracked": tracked})

    def test_numeric_newer_equal_older_releases_use_newest_pin(self):
        # Strata's hotfix releases have a fourth number (v0.1.40.1): newer than their base, older than the next.
        for tag, code in (("v0.1.9", 0), ("v0.1.34", 0), ("v0.1.33.9", 0), ("v0.1.34.1", 3), ("v0.1.36", 3)):
            with self.subTest(tag=tag):
                self.responses[self.strata_url] = ([release(tag)], {})
                result = self.report()
                self.assertEqual(code, result["exit_code"])
                self.assertEqual("v0.1.34", result["releases"]["strata"]["pinned"])
                self.assertEqual([tag] if code == 3 else [], [r["tag"] for r in result["releases"]["strata"]["newer"]])

    def test_closed_unmerged_pr_is_not_rejection(self):
        entry = {"repository": watch.REPOS["strata"], "kind": "pulls", "number": 231, "state": "open"}
        self.responses[f"{watch.GITHUB}/repos/{entry['repository']}/pulls/231"] = ({"state": "closed", "merged": False}, {})
        result = self.report([entry])
        self.assertEqual("closed-unmerged (check maintainer commit)", result["tracked"][0]["state"])
        self.assertEqual(3, result["exit_code"])

    def test_failed_or_truncated_api_is_incomplete_even_with_news_elsewhere(self):
        for response in (([release("v0.1.36")] * 100, {}), OSError("offline"), ({"message": "rate limit"}, {})):
            with self.subTest(response_type=type(response).__name__):
                self.responses[self.strata_url] = response
                self.assertEqual((False, 4), (self.report()["complete"], self.report()["exit_code"]))

    def test_missing_pr_merge_state_is_incomplete(self):
        entry = {"repository": watch.REPOS["strata"], "kind": "pulls", "number": 231, "state": "open"}
        self.responses[f"{watch.GITHUB}/repos/{entry['repository']}/pulls/231"] = ({"state": "closed"}, {})
        self.assertEqual(4, self.report([entry])["exit_code"])

    def test_paginated_release_news_in_later_page_is_not_lost(self):
        next_url = self.strata_url + "&page=2"
        self.responses[self.strata_url] = ([release("v0.1.30")], {"link": f'<{next_url}>; rel="next"'})
        self.responses[next_url] = ([release("v0.1.36")], {})
        self.assertEqual(["v0.1.36"], [r["tag"] for r in self.report()["releases"]["strata"]["newer"]])
        self.responses[next_url] = OSError("partial list")
        self.assertEqual(4, self.report()["exit_code"])

    def test_transport_rejects_short_body_and_never_sends_github_token_to_hf(self):
        class ShortResponse:
            headers = {"Content-Length": "80"}
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, _): return b"[]"
        with patch.object(watch.urllib.request, "urlopen", return_value=ShortResponse()):
            with self.assertRaises(watch.Incomplete):
                watch.urllib_transport(self.strata_url, {})
        url = watch.HF + "/api/models/example/model"
        transport = FixtureTransport({url: ({"sha": REVISION}, {})})
        watch.API(transport, token="fixture-only").get(url)
        self.assertNotIn("Authorization", transport.seen[0][1])

    def test_lightweight_and_annotated_tag_commit_pins_and_missing_asset(self):
        repo, tag = watch.REPOS["strata"], "v0.1.36"
        ref_url = f"{watch.GITHUB}/repos/{repo}/git/ref/tags/{tag}"
        tag_url = f"{watch.GITHUB}/repos/{repo}/git/tags/{'a' * 40}"
        responses = {
            ref_url: ({"object": {"type": "commit", "sha": "b" * 40}}, {}),
            f"{watch.GITHUB}/repos/{repo}/releases/tags/{tag}": ({**release(tag), "id": 1}, {}),
            f"{watch.GITHUB}/repos/{repo}/releases/1/assets?per_page=100": ([], {})}
        api = watch.API(FixtureTransport(responses))
        self.assertEqual(("b" * 40, None), api.commit(repo, tag))
        responses[ref_url] = ({"object": {"type": "tag", "sha": "a" * 40}}, {})
        annotated = {"sha": "a" * 40, "tag": tag, "object": {"type": "commit", "sha": "b" * 40}}
        responses[tag_url] = (annotated, {})
        self.assertEqual(("b" * 40, "a" * 40), api.commit(repo, tag))
        for object_type in ("tag", "tree", "blob"):
            with self.subTest(object_type=object_type):
                responses[tag_url] = (dict(annotated, object={"type": object_type, "sha": "b" * 40}), {})
                with self.assertRaisesRegex(watch.Incomplete, "commit target is invalid"):
                    api.commit(repo, tag)
        for changed in (dict(annotated, tag="v0.1.35"), dict(annotated, sha="c" * 40),
                        dict(annotated, object={"type": "commit", "sha": "missing"})):
            responses[tag_url] = (changed, {})
            with self.assertRaisesRegex(watch.Incomplete, "identity or commit target is invalid"):
                api.commit(repo, tag)
        with self.assertRaisesRegex(watch.Incomplete, "missing or duplicated"):
            api.assets(repo, tag, ["strata-windows-x64.zip"])


class LocalSource(unittest.TestCase):
    """Git is used only to construct the explicitly requested disposable source-history fixture."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "source"
        self.src.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.com")
        self.git("config", "user.name", "Fixture")
        (self.src / "serve").mkdir()
        (self.src / "tools").mkdir()
        (self.src / "setup.py").write_text(SETUP)
        (self.src / "serve/server.py").write_text(SERVER)
        (self.src / "tools/mtp_fetch.py").write_text(f'PINNED_REVISION = "{MTP_REVISION}"\nSHA256 = {{"mtp.tensor": "abc"}}\n')
        (self.src / "tools/calibrate.py").write_text(
            'DEFAULTS = {"--pcie-frac": None, "--spec-min-p": "0.5", "--pool-workers": None}   # stock v0.1.36\n')
        (self.src / "requirements.txt").write_text("numpy==1\n")
        self.old = self.commit("v0.1.34")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.src), *args], capture_output=True, text=True,
                              check=True, stdin=subprocess.DEVNULL).stdout.strip()

    def commit(self, tag):
        self.git("add", ".")
        self.git("commit", "-q", "--allow-empty", "-m", "fixture")
        self.git("tag", tag)
        return self.git("rev-parse", "HEAD")

    def test_checklist_unchanged_and_changes_are_distinguished(self):
        unchanged = watch.checklist(self.src, "v0.1.34", "v0.1.34")
        self.assertEqual({}, unchanged["changed_constants"])
        self.assertTrue(unchanged["requirements_unchanged"])
        self.assertFalse(unchanged["config_keys_changed"])
        self.assertFalse(unchanged["routes_changed"])
        self.assertEqual({}, unchanged["lost_routes"])
        (self.src / "setup.py").write_text(SETUP.replace("(0, 1, 34)", "(0, 1, 36)")
                                          .replace('cfg_path = ROOT', 'cfg["new_setting"] = True\n    cfg_path = ROOT'))
        (self.src / "requirements.txt").write_text("numpy==2\n")
        (self.src / "serve/server.py").write_text(SERVER.replace('"/health"', '"/new-route"') + '\nENV = "STRATA_NEW_KNOB"\n')
        self.commit("v0.1.36")
        changed = watch.checklist(self.src, "v0.1.34", "v0.1.36")
        self.assertEqual({"MIN_ENGINE"}, set(changed["changed_constants"]))
        self.assertFalse(changed["requirements_unchanged"])
        self.assertTrue(changed["config_keys_changed"])
        self.assertTrue(changed["routes_changed"])
        self.assertEqual(["STRATA_NEW_KNOB"], changed["new_env_names"])
        self.assertEqual({"GET": ["/new-route"]}, changed["candidate"]["unclassified_routes"])
        self.assertEqual({"GET": ["/health"]}, changed["lost_routes"])
        with self.assertRaisesRegex(watch.Incomplete, "unreviewed config keys"):
            watch.stock_plan((self.src / "setup.py").read_text(), family="coder", model="IQ1_M", context=131072, ram=64, vram=24)

    def test_plan_refuses_degradation_and_keeps_large_context(self):
        with self.assertRaisesRegex(watch.Incomplete, "low-RAM"):
            watch.stock_plan(SETUP, family="coder", model="IQ1_M", context=131072, ram=32, vram=24)
        plan = watch.stock_plan(SETUP, family="coder", model="IQ1_M", context=262144, ram=192, vram=24)
        flags = plan["expected_engine_flags"]
        self.assertEqual("262144", flags[flags.index("--max-context") + 1])
        self.assertEqual(37, plan["host"]["min_total_ram_gib"])
        self.assertEqual(36, plan["host"]["min_available_ram_gib_at_start"])
        self.assertNotIn("--rope-scaling", flags)
        with self.assertRaisesRegex(watch.Incomplete, "new call"):
            watch.stock_plan(SETUP.replace('cfg_path = ROOT', 'danger()\n    cfg_path = ROOT'),
                             family="coder", model="IQ1_M", context=131072, ram=64, vram=24)

    def test_report_completes_stock_0141_planning(self):
        (self.src / "setup.py").write_text((REPO / "tests/fixtures/strata_0_1_41_plan.py").read_text())
        self.commit("v0.1.41")
        responses = {f"{watch.GITHUB}/repos/{repo}/releases?per_page=100": ([release(tag)], {})
                     for repo, tag in ((watch.REPOS["strata"], "v0.1.41"), (watch.REPOS["omp"], "v18.8.6"))}
        result = watch.report(watch.API(FixtureTransport(responses)), REPO, {"tracked": []},
                              strata_src=self.src, pinned_tag="v0.1.34", strata_tag="v0.1.41")
        self.assertTrue(result["complete"], result["errors"])
        self.assertIn(result["exit_code"], (0, 3))
        self.assertEqual(sorted(watch.GENERATED_CONFIG_KEYS), result["checklist"]["candidate"]["generated_config_keys"])

    def prepare_draft(self):
        self.new = self.commit("v0.1.36")
        self.product = self.root / "product"
        (self.product / "profiles").mkdir(parents=True)
        (self.product / "releases").mkdir()
        (self.product / "locks").mkdir()
        matrix_dir = self.product / "docs/handoff/2026-09-30"
        matrix_dir.mkdir(parents=True)
        matrix_dir.joinpath("acceptance_matrix.json").write_bytes((REPO / "docs/handoff/2026-09-30/acceptance_matrix.json").read_bytes())
        data = copy.deepcopy(load(PARENT).data)
        data["profile_id"] = "fixture-predecessor"
        data["strata"]["commit"] = self.old
        lock = data["strata"]["python_lock"]["path"]
        (self.product / lock).write_bytes((REPO / lock).read_bytes())
        self.parent = self.product / "profiles/fixture-predecessor.json"
        self.parent.write_text(json.dumps(data))
        self.responses = {}
        for repo, tag, commit, rid, names in (
                (watch.REPOS["strata"], "v0.1.36", self.new, 1, ["strata-windows-x64.zip"]),
                (watch.REPOS["omp"], "v18.4.12", "d" * 40, 2, ["omp-windows-x64.exe", "omp-darwin-arm64", "omp-linux-x64"])):
            self.responses[f"{watch.GITHUB}/repos/{repo}/git/ref/tags/{tag}"] = ({"object": {"type": "commit", "sha": commit}}, {})
            self.responses[f"{watch.GITHUB}/repos/{repo}/releases/tags/{tag}"] = ({**release(tag), "id": rid}, {})
            assets = [{"name": name, "size": 12345, "digest": "sha256:" + "b" * 64,
                       "browser_download_url": f"https://github.com/{repo}/releases/download/{tag}/{name}"} for name in names]
            self.responses[f"{watch.GITHUB}/repos/{repo}/releases/{rid}/assets?per_page=100"] = (assets, {})
        shards = [{"path": f"IQ1_M/model-IQ1_M-{i}.gguf", "size": 100 + i,
                   "lfs": {"size": 100 + i, "oid": str(i) * 64}} for i in (1, 2)]
        self.responses[f"{watch.HF}/api/models/{MODEL_REPO}/tree/{REVISION}/IQ1_M?limit=100"] = (shards, {})
        self.responses[f"{watch.HF}/api/models/Qwen/Qwen3.8-Flash-Next/revision/{MTP_REVISION}"] = ({"sha": MTP_REVISION}, {})

    def make_draft(self):
        return watch.draft(watch.API(FixtureTransport(self.responses)), self.product, self.parent,
                           strata_tag="v0.1.36", omp_tag="v18.4.12", profile_id="fixture-draft", strata_src=self.src,
                           context=262144, ram=192, vram=24)

    def test_draft_binds_fresh_ledger_and_never_overwrites(self):
        self.prepare_draft()
        parent_bytes = self.parent.read_bytes()
        result = self.make_draft()
        manifest = self.product / result["manifest"]
        ledger = json.loads(manifest.with_name("qualification.json").read_text())
        profile = load(self.product / result["profile"])
        self.assertEqual("draft", profile.data["status"])
        self.assertEqual(261120, result["omp_declared_context"])
        self.assertEqual(profile.fingerprint, ledger["profile_fingerprint"])
        self.assertFalse(ledger["execution_performed"])
        self.assertEqual({"not_run"}, {g["status"] for g in ledger["gates"]})
        self.assertTrue(all(g["receipts"] == [] and g["receipt_paths"] == [] for g in ledger["gates"]))
        self.assertEqual([], verify(manifest)["errors"])
        self.assertIn("status draft: qualified required", verify(manifest, require_ready=True)["errors"])
        digest = sha256_bytes(manifest.read_bytes())
        with self.assertRaisesRegex(watch.Incomplete, "already exists"):
            self.make_draft()
        self.assertEqual(digest, sha256_bytes(manifest.read_bytes()))
        self.assertEqual(parent_bytes, self.parent.read_bytes())

    def test_annotated_tag_draft_pins_peeled_commit_and_refuses_local_mismatch(self):
        self.prepare_draft()
        repo, tag, tag_sha = watch.REPOS["strata"], "v0.1.36", "a" * 40
        self.responses[f"{watch.GITHUB}/repos/{repo}/git/ref/tags/{tag}"] = (
            {"object": {"type": "tag", "sha": tag_sha}}, {})
        tag_url = f"{watch.GITHUB}/repos/{repo}/git/tags/{tag_sha}"
        self.responses[tag_url] = ({"sha": tag_sha, "tag": tag,
                                    "object": {"type": "commit", "sha": "e" * 40}}, {})
        with self.assertRaisesRegex(watch.Incomplete, "local candidate tag differs"):
            self.make_draft()
        self.assertFalse((self.product / "profiles/fixture-draft.json").exists())
        self.assertFalse((self.product / "releases/fixture-draft").exists())
        self.responses[tag_url][0]["object"]["sha"] = self.new
        result = self.make_draft()
        profile = load(self.product / result["profile"])
        self.assertEqual(self.new, profile.data["strata"]["commit"])
        self.assertEqual("d" * 40, profile.data["omp"]["source_commit"])
        self.assertEqual({"strata": tag_sha}, result["tag_object_shas"])

    def test_draft_preserves_every_predecessor_floor_and_raises_stock_requirement(self):
        self.prepare_draft()
        predecessor = load(self.parent).data["host"]
        result = self.make_draft()
        host = load(self.product / result["profile"]).data["host"]
        for key, value in predecessor.items():
            if key.startswith("min_"):
                with self.subTest(floor=key):
                    self.assertGreaterEqual(host[key], value)
        self.assertEqual((45, 36, 90), (host["min_total_ram_gib"],
                                      host["min_available_ram_gib_at_start"], host["min_free_disk_gib"]))
        self.assertEqual({"predecessor": 45, "setup": 37, "selected": 45},
                         result["host_floors"]["min_total_ram_gib"])
        self.assertEqual({"predecessor": 34, "setup": 36, "selected": 36},
                         result["host_floors"]["min_available_ram_gib_at_start"])
        self.assertEqual({"predecessor": 90, "setup": 62, "selected": 90},
                         result["host_floors"]["min_free_disk_gib"])

    def test_missing_pin_creates_no_profile_or_ledger(self):
        self.prepare_draft()
        self.responses[f"{watch.GITHUB}/repos/{watch.REPOS['omp']}/releases/2/assets?per_page=100"][0][0].pop("digest")
        with self.assertRaisesRegex(watch.Incomplete, "complete immutable pin"):
            self.make_draft()
        self.assertFalse((self.product / "profiles/fixture-draft.json").exists())
        self.assertFalse((self.product / "releases/fixture-draft").exists())

    def prepare_v42_multi_gpu_draft(self):
        (self.src / "setup.py").write_text((REPO / "tests/fixtures/strata_0_1_41_plan.py").read_text())
        self.old = self.commit("v0.1.35")
        self.prepare_draft()
        source = (REPO / "tests/fixtures/strata_0_1_42_plan.py").read_text()
        (self.src / "setup.py").write_text(source)
        (self.src / "tools/calibrate.py").write_text(
            'DEFAULTS = {"--pcie-frac": None, "--spec-min-p": "0.5", "--pool-workers": None,\n'
            '            "--adapt-every": None, "--adapt-swaps": None, "--adapt-decay": None}\n')
        commit = self.commit("v0.1.42")
        data = json.loads(self.parent.read_text())
        data["host"].update(gpu_model="NVIDIA GeForce RTX 3090", min_gpu_vram_mib=25000,
                            display_attached=True, min_total_ram_gib=100)
        self.parent.write_text(json.dumps(data))
        for repo, tag, pin, rid, names in (
                (watch.REPOS["strata"], "v0.1.42", commit, 42, ["strata-windows-x64.zip"]),
                (watch.REPOS["omp"], "v18.8.9", "d" * 40, 89,
                 ["omp-windows-x64.exe", "omp-darwin-arm64", "omp-linux-x64"])):
            self.responses[f"{watch.GITHUB}/repos/{repo}/git/ref/tags/{tag}"] = (
                {"object": {"type": "commit", "sha": pin}}, {})
            self.responses[f"{watch.GITHUB}/repos/{repo}/releases/tags/{tag}"] = ({**release(tag), "id": rid}, {})
            self.responses[f"{watch.GITHUB}/repos/{repo}/releases/{rid}/assets?per_page=100"] = (
                [{"name": name, "size": 12345, "digest": "sha256:" + "b" * 64,
                  "browser_download_url": f"https://github.com/{repo}/releases/download/{tag}/{name}"}
                 for name in names], {})
        inventory_path = REPO / "tests/fixtures/strata_0_1_42_gpu_inventory.json"
        plan = watch.stock_plan(source, family="coder", model="IQ1_M", context=131072, ram=128,
                                gpu_inventory=json.loads(inventory_path.read_text()), gpus="all")
        revision = watch.literal_constants(source, ("HF_REVISIONS",))["HF_REVISIONS"][MODEL_REPO]
        self.responses[f"{watch.HF}/api/models/{MODEL_REPO}/tree/{revision}/IQ1_M?limit=100"] = (
            [{"path": "IQ1_M/" + name, "size": 100 + i, "lfs": {"size": 100 + i, "oid": str(i) * 64}}
             for i, name in enumerate(plan["model_files"], 1)], {})
        options = dict(strata_tag="v0.1.42", omp_tag="v18.8.9", profile_id="fixture-two-gpu",
                       strata_src=self.src, ram=128, gpu_inventory=inventory_path, gpus="all")
        api = watch.API(FixtureTransport(self.responses))
        return source, api, options, plan

    def test_draft_keeps_only_the_predecessors_stock_tip_subset(self):
        _, api, options, plan = self.prepare_v42_multi_gpu_draft()
        seeded = watch.draft(api, self.product, self.parent, **options, stock_tips=True)
        predecessor = load(self.product / seeded["profile"])
        both = {"--conversation-cache-mib": "8192", "--prefill": "auto:32768"}
        parking = {"--conversation-cache-mib": "8192"}
        for name, pinned, ram, expected, dropped, total, extra in (
                ("parking", parking, 128, parking, [], 56, 8),
                ("both", both, 128, both, [], 96, 8),
                ("drop-prefill", both, 75, parking, ["--prefill"], 56, 8),
                ("drop-all", parking, 45, {}, ["--conversation-cache-mib"], 0, 0)):
            with self.subTest(name=name):
                data = copy.deepcopy(predecessor.data)
                data["strata"]["stock_tips"] = pinned
                data["strata"]["expected_engine_flags"] = watch.tipped_flags(plan["expected_engine_flags"], pinned)
                predecessor.path.write_text(json.dumps(data))
                parent_bytes = predecessor.path.read_bytes()
                result = watch.draft(api, self.product, predecessor.path,
                                     **dict(options, profile_id="fixture-tips-" + name, ram=ram), stock_tips=True)
                profile = load(self.product / result["profile"])
                self.assertEqual(expected, profile.data["strata"].get("stock_tips", {}))
                self.assertEqual(watch.tipped_flags(plan["expected_engine_flags"], expected),
                                 profile.data["strata"]["expected_engine_flags"])
                self.assertEqual(dropped, result["dropped_stock_tips"])
                self.assertEqual({"min_total_ram_gib": total, "extra_available_ram_gib": extra},
                                 result["planning"]["tips_ram"])
                self.assertEqual(plan["host"]["min_available_ram_gib_at_start"] + extra,
                                 result["host_floors"]["min_available_ram_gib_at_start"]["setup"])
                self.assertEqual(parent_bytes, predecessor.path.read_bytes())

    def test_pipeline_windows_draft_pins_and_carries_the_option(self):
        _, api, options, _ = self.prepare_v42_multi_gpu_draft()
        result = watch.draft(api, self.product, self.parent, **options, pipeline_windows=2)
        profile = load(self.product / result["profile"])
        self.assertEqual(2, profile.data["strata"]["pipeline_windows"])
        flags = profile.data["strata"]["expected_engine_flags"]
        self.assertEqual("2", flag_pairs(flags)["--pipeline-windows"])
        self.assertEqual(1, flags.count("--pipeline-windows"))
        self.assertIn("--pipeline-windows 2", profile.data["description"])
        pinned_bytes = profile.path.read_bytes()
        later = watch.draft(api, self.product, profile.path, **dict(options, profile_id="fixture-later-pipeline"))
        carried = load(self.product / later["profile"])
        self.assertEqual(2, carried.data["strata"]["pipeline_windows"])
        self.assertEqual(flags, carried.data["strata"]["expected_engine_flags"])
        self.assertEqual(pinned_bytes, profile.path.read_bytes())

    def test_pipeline_windows_draft_refuses_single_card_and_batch_slots(self):
        _, api, options, _ = self.prepare_v42_multi_gpu_draft()
        single = {k: v for k, v in options.items() if k not in {"gpu_inventory", "gpus"}}
        for overrides in (single | {"vram": 24}, options | {"parallel": 4}):
            with self.subTest(overrides=overrides), self.assertRaisesRegex(watch.Incomplete, "pipeline_windows"):
                watch.draft(api, self.product, self.parent, **overrides, pipeline_windows=2)
        self.assertFalse((self.product / "profiles/fixture-two-gpu.json").exists())
        self.assertFalse((self.product / "releases/fixture-two-gpu").exists())

    def test_v42_multi_gpu_draft_preserves_model_floors_and_creates_only_fresh_evidence(self):
        source, api, options, plan = self.prepare_v42_multi_gpu_draft()
        parent_bytes = self.parent.read_bytes()
        with self.assertRaisesRegex(watch.Incomplete, "without scalar"):
            watch.draft(api, self.product, self.parent, **options, vram=24)
        result = watch.draft(api, self.product, self.parent, **options)
        profile = load(self.product / result["profile"])
        self.assertEqual((1, 0), profile.gpu_indices)
        self.assertEqual([24576, 25000], [card["min_gpu_vram_mib"] for card in profile.gpu_requirements])
        self.assertEqual(100, profile.data["host"]["min_total_ram_gib"])
        for key in ("gpu_index", "gpu_model", "min_gpu_vram_mib", "display_attached"):
            self.assertNotIn(key, profile.data["host"])
        manifest_path = self.product / result["manifest"]
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        self.assertIsNone(manifest["install"]["runtime_identity_sha256"])
        self.assertEqual([], manifest["install"]["generated_files"])
        ledger = json.loads(manifest_path.with_name("qualification.json").read_text())
        self.assertFalse(ledger["execution_performed"])
        self.assertTrue(all(g["status"] == "not_run" and not g["receipts"] and not g["receipt_paths"]
                            for g in ledger["gates"]))
        with self.assertRaisesRegex(watch.Incomplete, "already exists"):
            watch.draft(api, self.product, self.parent, **options)
        self.assertEqual(manifest_bytes, manifest_path.read_bytes())
        self.assertEqual(parent_bytes, self.parent.read_bytes())

        # Compose calibration measured on the pair with both stock opt-ins, without a second draft/install.
        settings = {"--pcie-frac": "0.20", "--spec-min-p": "0.70", "--pool-workers": "6",
                    "--adapt-every": "1", "--adapt-swaps": "160", "--adapt-decay": "0.97"}
        calibration = self.root / "calibrate.json"
        calibration.write_text(json.dumps({"settings": settings, "report": {"tok_s": 80.0}}))
        combined_options = dict(options, profile_id="fixture-two-gpu-stock", ram=127.68, parallel=4, stock_tips=True,
                                calibration=calibration, calibration_host="fixture-win-a", calibration_date="2026-10-10")
        combined = load(self.product / watch.draft(api, self.product, profile.path, **combined_options)["profile"])
        self.assertEqual([1, 0], combined.data["strata"]["setup_args"]["gpus"])
        self.assertEqual("auto", combined.data["strata"]["setup_args"]["layer_split"])
        self.assertEqual(4, combined.data["strata"]["setup_args"]["parallel"])
        tips = {"--conversation-cache-mib": "8192", "--prefill": "auto:32768"}
        self.assertEqual(tips, combined.data["strata"]["stock_tips"])
        expected = watch.tipped_flags(watch.calibrated_flags(plan["expected_engine_flags"], settings), tips)
        self.assertEqual(expected, combined.data["strata"]["expected_engine_flags"])
        self.assertEqual(profile.fingerprint, combined.data["strata"]["calibration"]["source_fingerprint"])
        slots_plan = watch.stock_plan(source, family="coder", model="IQ1_M", context=131072, ram=127.68,
                                     gpu_inventory=json.loads(options["gpu_inventory"].read_text()), gpus="all", parallel=4, tips=True)
        self.assertEqual(max(profile.data["host"]["min_total_ram_gib"], slots_plan["host"]["min_total_ram_gib"], 96),
                         combined.data["host"]["min_total_ram_gib"])
        self.assertEqual(max(profile.data["host"]["min_available_ram_gib_at_start"],
                             slots_plan["host"]["min_available_ram_gib_at_start"] + 8),
                         combined.data["host"]["min_available_ram_gib_at_start"])
        for overrides, error in (({"parallel": 5}, "recommended for this card: 4"),
                                 ({"context": 262144}, "different install")):
            with self.subTest(overrides=overrides), self.assertRaisesRegex(watch.Incomplete, error):
                watch.draft(api, self.product, profile.path, **dict(combined_options,
                            profile_id="fixture-two-gpu-refused", **overrides))
        self.assertFalse((self.product / "profiles/fixture-two-gpu-refused.json").exists())

    def test_changed_requirements_refuses_lock_reuse(self):
        self.prepare_draft()
        (self.src / "requirements.txt").write_text("numpy==2\n")
        self.new = self.commit("v0.1.37")
        repo = watch.REPOS["strata"]
        self.responses[f"{watch.GITHUB}/repos/{repo}/git/ref/tags/v0.1.37"] = ({"object": {"type": "commit", "sha": self.new}}, {})
        with self.assertRaisesRegex(watch.Incomplete, "requirements.txt changed"):
            watch.draft(watch.API(FixtureTransport(self.responses)), self.product, self.parent,
                        strata_tag="v0.1.37", omp_tag="v18.4.12", profile_id="fixture-draft", strata_src=self.src)
        self.assertFalse((self.product / "profiles/fixture-draft.json").exists())

    def test_calibrated_draft_pins_stock_settings_on_the_measured_profile_only(self):
        self.prepare_draft()
        measured = self.product / self.make_draft()["profile"]
        result = self.root / "calibrate-result.json"

        def calibrated(settings, source=measured, profile_id="fixture-calibrated", **overrides):
            result.write_text(json.dumps({"settings": settings, "report": {"tok_s": 74.4}}))
            return watch.draft(watch.API(FixtureTransport(self.responses)), self.product, source,
                               strata_tag="v0.1.36", omp_tag="v18.4.12", profile_id=profile_id, strata_src=self.src,
                               ram=192, vram=24, calibration=result, calibration_host="rtx3090-win-a",
                               calibration_date="2026-10-03", **overrides)

        profile = load(self.product / calibrated({"--pcie-frac": "0.20", "--spec-min-p": "0.70"})["profile"])
        base = load(measured).data["strata"]["expected_engine_flags"]
        i = base.index("--spec-min-p")
        self.assertEqual(base[:i] + base[i + 2:] + ["--pcie-frac", "0.20", "--spec-min-p", "0.70"],
                         profile.data["strata"]["expected_engine_flags"])
        self.assertEqual(load(measured).fingerprint, profile.data["strata"]["calibration"]["source_fingerprint"])
        for settings, source, overrides, error in (
                ({}, measured, {}, "kept every default"),
                ({"--pcie-frac": "0.35"}, profile.path, {}, "uncalibrated profile"),
                ({"--pcie-frac": "0.35"}, measured, {"context": 131072}, "different install")):
            with self.subTest(error=error):
                with self.assertRaisesRegex(watch.Incomplete, error):
                    calibrated(settings, source, "fixture-refused", **overrides)
                self.assertFalse((self.product / "profiles/fixture-refused.json").exists())
                self.assertFalse((self.product / "releases/fixture-refused").exists())


class StockBudgetPlan(unittest.TestCase):
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_36_plan.py").read_text()

    def plan(self, ram=127.69):
        return watch.stock_plan(self.source, family="unsloth", model="UD-Q4_K_XL",
                                context=131072, ram=ram, vram=24)

    def test_stock_budget_cap_and_kv_streaming_at_both_ram_sizes(self):
        original = watch.pure_exec
        namespace = {}
        def capture(nodes, ns):
            original(nodes, ns)
            namespace.update(ns)
        with patch.object(watch, "pure_exec", side_effect=capture):
            plan = self.plan()
        # Stock's 64 GiB example is the pre-KV budget; 131K streams another 1.8 GB to RAM.
        self.assertEqual(40, namespace["resident_budget_gib"]("UD-Q4_K_XL", 64))
        self.assertEqual(71, namespace["resident_budget_gib"]("UD-Q4_K_XL", 127.69))
        self.assertEqual(71, plan["budget_plan"]["resident_budget_gib"])
        self.assertEqual(38, self.plan(64)["budget_plan"]["resident_budget_gib"])
        for p in (plan, self.plan(64)):
            flags = p["expected_engine_flags"]
            self.assertEqual("32768", flags[flags.index("--kv-resident") + 1])
            self.assertFalse({"--mmap-experts", "--resident-experts", "--experts"} & set(flags))

    def test_start_floors_preserve_the_budget_and_stock_headroom(self):
        plan = self.plan()
        self.assertEqual({"min_total_ram_gib": 97, "min_available_ram_gib_at_start": 97,
                          "min_free_disk_gib": 112, "min_driver_major": 580}, plan["host"])
        self.assertEqual(71, self.plan(plan["host"]["min_total_ram_gib"])["budget_plan"]["resident_budget_gib"])
        self.assertEqual(70, self.plan(96)["budget_plan"]["resident_budget_gib"])
        self.assertEqual(1.799356416, plan["budget_plan"]["kv_ram_gb"])
        self.assertEqual(119.3, plan["thresholds"]["fresh_disk_gb"])

    def test_stock_four_shard_pins_must_match_hf_lfs(self):
        plan = self.plan()
        repo = "unsloth/Qwen3.8-Flash-Next-GGUF"
        revision = "38bb39ee97821de2c9009abb7e93950eec396e66"
        url = f"{watch.HF}/api/models/{repo}/tree/{revision}/UD-Q4_K_XL?limit=100"
        rows = [{"path": "UD-Q4_K_XL/" + name, "size": size, "lfs": {"size": size, "oid": digest}}
                for name, (size, digest) in plan["model_hashes"].items()]
        api = watch.API(FixtureTransport({url: (rows, {})}))
        got_repo, got_revision, files = watch.hf_files(api, plan)
        self.assertEqual((repo, revision), (got_repo, got_revision))
        self.assertEqual(plan["model_files"], [f["path"].split("/")[-1] for f in files])
        self.assertEqual(111334654784, sum(f["bytes"] for f in files))
        for row in rows:
            with self.subTest(shard=row["path"]):
                digest = row["lfs"]["oid"]
                row["lfs"]["oid"] = "0" * 64
                with self.assertRaisesRegex(watch.Incomplete, "differs from pinned"):
                    watch.hf_files(api, plan)
                row["lfs"]["oid"] = digest
        rows[0]["size"] += 1
        rows[0]["lfs"]["size"] += 1
        with self.assertRaisesRegex(watch.Incomplete, "differs from pinned"):
            watch.hf_files(api, plan)


class StockCurrentPlan(unittest.TestCase):
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_38_plan.py").read_text()

    def plan(self, source=None, *, family="qwen", model="IQ3_XXS"):
        return watch.stock_plan(self.source if source is None else source, family=family, model=model,
                                context=131072, ram=191.7, vram=24)

    def test_native_windows_default_and_budget_variants_keep_stock_memory_modes(self):
        standard = self.plan()
        self.assertEqual("qwen3.8-flash-next-iq3_xxs", standard["model_name"])
        self.assertIsNone(standard["budget_plan"])
        flags = flag_pairs(standard["expected_engine_flags"])
        self.assertEqual("131072", flags["--max-context"])
        self.assertEqual("int8", flags["--kv"])
        self.assertEqual("32768", flags["--kv-resident"])
        self.assertNotIn("--resident-budget-gib", flags)
        self.assertNotIn("--vram-reserve-mib", flags)
        budget = self.plan(family="unsloth", model="UD-Q4_K_XL")
        self.assertEqual("71", flag_pairs(budget["expected_engine_flags"])["--resident-budget-gib"])
        self.assertEqual(191.7, budget["budget_plan"]["ram_gib"])
        self.assertEqual(97, budget["host"]["min_available_ram_gib_at_start"])

    def test_advisory_helpers_and_unreachable_branches_still_reject_side_effects(self):
        # Even a call inside an unselected small-card/HIP branch must be reviewed before execution.
        for before, after in (("tips.append(", "open("),
                              ("say(", "download("),
                              ("for line in small_card_note(ctx, draft_vocab):", "for line in [1, 2]:")):
            with self.subTest(after=after):
                with self.assertRaisesRegex(watch.Incomplete, "review required"):
                    self.plan(self.source.replace(before, after))

    def test_stock_non_streamed_q2_default_and_streaming_ram_boundary(self):
        for ram, streaming, total, available in ((47.2, False, 44, 44), (50.8, True, 51, 50)):
            with self.subTest(ram=ram):
                plan = watch.stock_plan(self.source, family="qwen", model="Q2_0", context=131072,
                                        ram=ram, vram=32)
                flags = flag_pairs(plan["expected_engine_flags"])
                self.assertEqual(streaming, "--kv-resident" in flags)
                self.assertEqual("131072", flags["--max-context"])
                self.assertEqual("int8", flags["--kv"])
                self.assertEqual("off", plan["setup_args"]["low_ram"])
                self.assertEqual(total, plan["host"]["min_total_ram_gib"])
                self.assertEqual(available, plan["host"]["min_available_ram_gib_at_start"])
                self.assertFalse({"--mmap-experts", "--resident-experts"} & flags.keys())
        with self.assertRaisesRegex(watch.Incomplete, "low-RAM"):
            watch.stock_plan(self.source, family="qwen", model="Q2_0", context=131072, ram=43.9, vram=32)


class StockRelease0139Plan(unittest.TestCase):
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_39_plan.py").read_text()

    def plan(self, source=None, *, family="qwen", model="IQ3_S"):
        return watch.stock_plan(self.source if source is None else source, family=family, model=model,
                                context=131072, ram=127.69, vram=24)

    def test_reviewed_native_windows_flags_and_floors_are_stock(self):
        expected = ["--expert-cache", "auto", "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
                    "--max-context", "131072", "--kv", "int8", "--kv-resident", "32768"]
        for family, model, total, available, disk in (("qwen", "IQ3_S", 77, 64, 86),
                                                       ("coder", "IQ1_M", 35, 34, 62),
                                                       ("unsloth", "UD-Q4_K_XL", 97, 97, 112)):
            with self.subTest(model=model):
                plan = self.plan(family=family, model=model)
                self.assertEqual(expected + (["--resident-budget-gib", "71"] if family == "unsloth" else []),
                                 plan["expected_engine_flags"])
                self.assertEqual({"min_total_ram_gib": total, "min_available_ram_gib_at_start": available,
                                  "min_free_disk_gib": disk, "min_driver_major": 580}, plan["host"])
                self.assertEqual(sorted(watch.GENERATED_CONFIG_KEYS), plan["config_keys"])
                self.assertEqual("off", plan["setup_args"]["low_ram"])
                self.assertEqual("no", plan["setup_args"]["vision"])

    def test_cpu_topology_toolkit_and_windows_disk_are_fixed_not_ambient(self):
        original, namespace = watch.pure_exec, {}
        def capture(nodes, ns):
            original(nodes, ns)
            namespace.update(ns)
        with patch.object(watch.os, "cpu_count", side_effect=AssertionError("ambient CPU read")), \
                patch.object(watch, "pure_exec", side_effect=capture):
            plan = self.plan()
        self.assertIsNone(namespace["cpu_cores"]())
        self.assertEqual(13, namespace["cuda_tk"])
        self.assertIsNone(namespace["rotational_disk"](Path("unused.gguf")))
        self.assertEqual(15, namespace["hybrid_pool_workers"]((8, 16)))
        self.assertIsNone(namespace["hybrid_pool_workers"]((8, 8)))
        args = ["--spec", "4"]
        self.assertIs(args, namespace["recommend_pool_workers"](args))
        self.assertFalse({"--pool-workers", "--ple-io", "--remote-expert-opt"} & set(plan["expected_engine_flags"]))

    def test_a_hybrid_cpu_topology_plans_stock_pool_workers(self):
        # Stock #642: performance cores - 1 + half the efficiency cores, only with more efficiency than performance.
        for cores, workers in (((8, 16), "15"), ((6, 8), "9"), ((8, 8), None), (None, None)):
            with self.subTest(cores=cores):
                plan = watch.stock_plan(self.source, family="qwen", model="IQ3_S", context=131072, ram=127.69,
                                        vram=24, cpu_cores=cores)
                self.assertEqual(workers, flag_pairs(plan["expected_engine_flags"]).get("--pool-workers"))

    def test_unsloth_iq4_xs_literal_and_model_specific_shards_are_handled(self):
        pins = watch.literal_constants(self.source, ("UNSLOTH_IQ4_XS_SHARDS",))["UNSLOTH_IQ4_XS_SHARDS"]
        self.assertEqual(3, len(pins))
        self.assertEqual(93682584224, sum(size for size, digest in pins.values()))
        plan = self.plan(family="unsloth", model="UD-IQ4_XS")
        self.assertEqual(list(pins), plan["model_files"])
        self.assertEqual(pins, {name: plan["model_hashes"][name] for name in plan["model_files"]})
        self.assertEqual("55", flag_pairs(plan["expected_engine_flags"])["--resident-budget-gib"])
        # The checklist's Coder lane must still evaluate FAMILIES' merged Unsloth shard table.
        self.assertEqual("qwen3.8-flash-next-coder-iq1_m", self.plan(family="coder", model="IQ1_M")["model_name"])
        changed = self.source.replace("UNSLOTH_IQ4_XS_SHARDS = {", "UNSLOTH_IQ4_XS_SHARDS = read_shards() or {")
        with self.assertRaisesRegex(watch.Incomplete, "setup constant UNSLOTH_IQ4_XS_SHARDS is no longer literal"):
            self.plan(changed)

    def test_unreviewed_calls_io_environment_and_loops_still_refuse(self):
        for statement in ("download()", "import os", "pack.read_text()", 'os.environ.get("STRATA_CUDA")',
                          "subprocess.run([])", "for item in [1, 2]:\n        say(str(item))",
                          "items = [item for item in (1, 2)]"):
            with self.subTest(statement=statement):
                changed = self.source.replace("    if scaling is not None:",
                                              "    " + statement + "\n    if scaling is not None:")
                with self.assertRaisesRegex(watch.Incomplete, "review required"):
                    self.plan(changed)
        changed = self.source.replace("n = hybrid_pool_workers(cpu_cores())", "n = detect_workers()")
        with self.assertRaisesRegex(watch.Incomplete, "new call"):
            self.plan(changed)

    def test_exact_excluded_branches_refuse_drift_or_a_reachable_guard(self):
        for before, after in (("GGUFFile(ple)", "open(ple)"),
                              ("old_cfg.is_file()", "old_cfg.read_text()"),
                              ("if a.parallel is not None:\n", "if a.parallel is not None:\n"
                               "        for item in [1, 2]:\n            say(str(item))\n"),
                              ("disk = None if is_wsl() else rotational_disk(ple)", "disk = 'rotational'")):
            with self.subTest(after=after):
                with self.assertRaisesRegex(watch.Incomplete, "unreviewed|review required"):
                    self.plan(self.source.replace(before, after))

    def test_post_config_worker_recommendation_refuses_new_work(self):
        for before, after in (("cfg[\"args\"] = recommend_pool_workers(cfg[\"args\"])",
                               "cfg[\"args\"] = detect_workers(cfg[\"args\"] )"),
                              ("cfg[\"args\"] = recommend_pool_workers(cfg[\"args\"])",
                               "cfg[\"args\"] = recommend_pool_workers(cfg[\"args\"])\n        download()")):
            with self.subTest(after=after):
                with self.assertRaisesRegex(watch.Incomplete, "review required"):
                    self.plan(self.source.replace(before, after))

    def test_unreviewed_config_keys_are_not_admitted(self):
        changed = self.source.replace("    cfg_path = ROOT /", "    cfg[\"parallel\"] = 1\n    cfg_path = ROOT /")
        with self.assertRaisesRegex(watch.Incomplete, "unreviewed config keys"):
            self.plan(changed)


class StockRelease01401Plan(unittest.TestCase):
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_40_1_plan.py").read_text()
        self.predecessor = load(REPO / "profiles/win11-rtxpro6000-iq3s-131k-strata0.1.39-omp18.5.0.json").data

    def plan(self, source=None, *, model="IQ3_S", kv="int8"):
        host = self.predecessor["host"]
        return watch.stock_plan(self.source if source is None else source, family="qwen", model=model,
                                context=131072, ram=host["min_total_ram_gib"],
                                vram=host["min_gpu_vram_mib"] / 1024, kv=kv, cpu_cores=tuple(host["cpu_cores"]))

    def test_pro_flags_and_floors_follow_stock_with_the_predecessor_host_inputs(self):
        plan = self.plan()
        self.assertEqual(["--expert-cache", "auto", "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
                          "--max-context", "131072", "--kv", "int8", "--kv-resident", "32768",
                          "--pool-workers", "15"], plan["expected_engine_flags"])
        self.assertEqual({"min_total_ram_gib": 77, "min_available_ram_gib_at_start": 64,
                          "min_free_disk_gib": 86, "min_driver_major": 580}, plan["host"])
        self.assertEqual(self.predecessor["strata"]["setup_args"], plan["setup_args"])
        self.assertEqual(self.predecessor["strata"]["model_name"], plan["model_name"])
        self.assertEqual(sorted(watch.GENERATED_CONFIG_KEYS), plan["config_keys"])

    def test_advisory_probes_are_fixed_and_never_execute_hardware_helpers(self):
        original, namespace = watch.pure_exec, {}
        def capture(nodes, ns):
            original(nodes, ns)
            namespace.update(ns)
        # The fixture retains stock gpu_drives_display/cpu_sockets bodies, but neither is loaded or executed.
        with patch.object(watch.subprocess, "run", side_effect=AssertionError("hardware probe executed")) as probe, \
                patch.object(watch.os, "cpu_count", side_effect=AssertionError("ambient CPU read")), \
                patch.object(watch, "pure_exec", side_effect=capture):
            plan = self.plan()
        probe.assert_not_called()
        self.assertFalse(namespace["gpu_drives_display"]({"index": 0}))
        self.assertIsNone(namespace["cpu_sockets"]())
        self.assertEqual(1500, namespace["DISPLAY_RESERVE_MIB"])
        self.assertEqual([], namespace["two_socket_note"](None))
        self.assertIn("--pool-workers 17", namespace["two_socket_note"]((2, 18))[0])
        self.assertNotIn("--vram-reserve-mib", plan["expected_engine_flags"])
        self.assertFalse(any("drives a display" in note or "CPU sockets" in note for note in plan["notes"]))

    def test_streamed_kv_uses_the_reviewed_literal_byte_counts(self):
        for kv, kv_ram in (("int8", 1.799356416), ("q4_0", 0.981467136)):
            with self.subTest(kv=kv):
                plan = self.plan(kv=kv)
                self.assertAlmostEqual(62 + kv_ram + 1, plan["thresholds"]["kv_streaming_from"])
                flags = flag_pairs(plan["expected_engine_flags"])
                self.assertEqual(kv, flags["--kv"])
                self.assertEqual("32768", flags["--kv-resident"])

    def test_fresh_disk_inputs_and_stock_q2_choice_do_not_probe_existing_files_or_cpu_flags(self):
        original, namespace = watch.pure_exec, {}
        def capture(nodes, ns):
            original(nodes, ns)
            namespace.update(ns)
        for model, q2_avx, fresh_disk in (("IQ3_S", False, 91.6), ("Q2_0", True, 114.4)):
            with self.subTest(model=model), patch.object(watch, "pure_exec", side_effect=capture):
                plan = self.plan(model=model)
                self.assertFalse(namespace["pack_bin"])
                self.assertFalse(namespace["mtp_have"])
                self.assertTrue(namespace["avx512"])
                self.assertEqual(q2_avx, namespace["q2_avx"])
                self.assertAlmostEqual(fresh_disk, plan["thresholds"]["fresh_disk_gb"])

    def test_new_constants_must_remain_literal(self):
        for before, after in (("KV_CELL_BYTES = {", "KV_CELL_BYTES = read_kv_bytes() or {"),
                              ("DISPLAY_RESERVE_MIB = 1500", "DISPLAY_RESERVE_MIB = read_display_reserve()")):
            with self.subTest(before=before), self.assertRaisesRegex(watch.Incomplete, "no longer literal"):
                self.plan(self.source.replace(before, after))

    def test_new_helper_and_disk_arithmetic_refuse_unreviewed_calls_io_and_environment(self):
        for call in ("download()", "pack.read_text()", 'os.environ.get("STRATA_KV")'):
            for before, after in (("return ctx * (13 * KV_CELL_BYTES", f"return {call} or ctx * (13 * KV_CELL_BYTES"),
                                  ("n = sockets[1] - 1", f"n = {call} or sockets[1] - 1"),
                                  ('q2_avx = model == "Q2_0"', f'q2_avx = {call} or model == "Q2_0"')):
                with self.subTest(call=call, before=before), \
                        self.assertRaisesRegex(watch.Incomplete, "review required"):
                    self.plan(self.source.replace(before, after))

    def test_fixed_advisory_calls_refuse_drift_into_config_work_or_other_callers(self):
        display = "    if not hip and not multi and a.vram_reserve_mib is None and gpu_drives_display(gpu):"
        sockets = "        for line in two_socket_note(cpu_sockets()):"
        for before, after in ((display, display + '\n        args += ["--vram-reserve-mib", "1500"]'),
                              (sockets, sockets + '\n            cfg["args"] += ["--pool-workers", "99"]')):
            with self.subTest(before=before), self.assertRaisesRegex(watch.Incomplete, "review required"):
                self.plan(self.source.replace(before, after))
        for call in ("gpu_drives_display(gpu)", "cpu_sockets()"):
            with self.subTest(call=call), self.assertRaisesRegex(watch.Incomplete, "review required"):
                self.plan(self.source.replace("    if scaling is not None:",
                                              f"    args += [str({call})]\n    if scaling is not None:"))

    def test_new_advisory_output_and_loops_still_refuse_io_or_environment_reads(self):
        sockets = "        for line in two_socket_note(cpu_sockets()):"
        for statement in ("download()", "pack.read_text()", 'os.environ.get("STRATA_CPU")'):
            with self.subTest(statement=statement), self.assertRaisesRegex(watch.Incomplete, "review required"):
                self.plan(self.source.replace(sockets, sockets + f"\n            {statement}"))
        changed = self.source.replace("two_socket_note(cpu_sockets())", "[1, 2]")
        with self.assertRaisesRegex(watch.Incomplete, "loop is unreviewed"):
            self.plan(changed)


class StockRelease01402Plan(unittest.TestCase):
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_40_2_plan.py").read_text()
        self.predecessor = load(REPO / "profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.1-omp18.5.0.json").data

    def plan(self, source=None, *, model="IQ3_S", kv="int8"):
        host = self.predecessor["host"]
        return watch.stock_plan(self.source if source is None else source, family="qwen", model=model,
                                context=131072, ram=host["min_total_ram_gib"],
                                vram=host["min_gpu_vram_mib"] / 1024, kv=kv, cpu_cores=tuple(host["cpu_cores"]))

    def test_pro_flags_and_floors_match_the_predecessor_stock_plan(self):
        plan = self.plan()
        predecessor_plan = self.plan((REPO / "tests/fixtures/strata_0_1_40_1_plan.py").read_text())
        for field in ("expected_engine_flags", "host", "setup_args", "model_name", "config_keys"):
            with self.subTest(field=field):
                self.assertEqual(predecessor_plan[field], plan[field])
        self.assertEqual(self.predecessor["strata"]["expected_engine_flags"], plan["expected_engine_flags"])
        # The predecessor profile keeps a conservative 90 GiB disk floor; stock still plans 86 GiB.
        self.assertEqual({"min_total_ram_gib": 77, "min_available_ram_gib_at_start": 64,
                          "min_free_disk_gib": 86, "min_driver_major": 580}, plan["host"])
        self.assertEqual(self.predecessor["strata"]["setup_args"], plan["setup_args"])
        self.assertEqual(self.predecessor["strata"]["model_name"], plan["model_name"])
        self.assertEqual(sorted(watch.GENERATED_CONFIG_KEYS), plan["config_keys"])

    def test_hip_only_gfx1103_branch_is_admitted_but_never_executed(self):
        original, namespace = watch.pure_exec, {}
        def capture(nodes, ns):
            original(nodes, ns)
            namespace.update(ns)
        with patch.object(watch, "pure_exec", side_effect=capture):
            plan = self.plan()
        self.assertFalse(namespace["hip"])
        self.assertTrue(namespace["WIN"])
        # Neither name is loaded: a successful plan proves the HIP guard short-circuits the new branch.
        self.assertNotIn("gfx_arch_is", namespace)
        self.assertNotIn("GFX1103_OPT_IN", namespace)
        self.assertNotIn("STRATA_NO_ARENA_THP", namespace["cfg"].get("env", {}))
        self.assertNotIn("env", plan["config_keys"])

    def test_gfx1103_branch_still_refuses_unreviewed_io_environment_and_subprocess_calls(self):
        branch = '        if GFX1103_OPT_IN and gfx_arch_is(gpu["arch"], "gfx1103") and not WIN:'
        for call in ("download()", "pack.read_text()", 'os.environ.get("STRATA_EXPERIMENTAL_GFX1103")',
                     'subprocess.run(["probe"])'):
            for after in (f"        {call}\n" + branch, branch + f"\n            {call}"):
                with self.subTest(call=call, after=after), self.assertRaisesRegex(watch.Incomplete, "review required"):
                    self.plan(self.source.replace(branch, after))


class StockRelease01403Plan(unittest.TestCase):
    """Stock setup's opt-ins on the PRO host: batch slots (`--parallel N`) and its printed host recommendations."""
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_40_3_plan.py").read_text()
        self.host = load(REPO / "profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json").data["host"]

    def plan(self, source=None, *, ram=191.69, vram=None, **options):
        return watch.stock_plan(self.source if source is None else source, family="qwen", model="IQ3_S",
                                context=131072, ram=ram, cpu_cores=tuple(self.host["cpu_cores"]),
                                vram=self.host["min_gpu_vram_mib"] / 1024 if vram is None else vram, **options)

    def test_slots_only_up_to_stocks_recommendation_for_the_card(self):
        plan = self.plan(parallel=4)
        self.assertEqual(4, plan["setup_args"]["parallel"])
        self.assertEqual(sorted(watch.GENERATED_CONFIG_KEYS | {"parallel"}), plan["config_keys"])
        # The server, not setup, turns "parallel" into the engine's --batch: setup's own flags are unchanged.
        self.assertEqual(self.plan()["expected_engine_flags"], plan["expected_engine_flags"])
        for slots, vram, warning in ((5, None, "recommended for this card: 4"), (9, None, "at most 8"),
                                     (2, 24, "recommended for this card: one at a time")):
            with self.subTest(slots=slots, vram=vram), self.assertRaisesRegex(watch.Incomplete, warning):
                self.plan(parallel=slots, vram=vram)

    def test_printed_recommendations_follow_stocks_ram_thresholds(self):
        cache, prefill = {"--conversation-cache-mib": "8192"}, {"--prefill": "auto:32768"}
        # The cache tip needs 24 GB beside IQ3_S's 62; the prefill tip 96 GB in all.
        for ram, tips in ((85.9, {}), (86, cache), (95.9, cache), (96, cache | prefill)):
            with self.subTest(ram=ram):
                self.assertEqual(tips, self.plan(ram=ram, tips=True)["stock_tips"])
        self.assertEqual({"min_total_ram_gib": 96, "extra_available_ram_gib": 8}, self.plan(tips=True)["tips_ram"])

    def test_changed_slot_or_recommendation_code_needs_review(self):
        for old, new, option in (("AGENT_CACHE_MIB} in the", "AGENT_CACHE_MIB * 2} in the", {"tips": True}),
                                 ('cfg["parallel"] = a.parallel', 'cfg["parallel"] = a.parallel + 1', {"parallel": 4}),
                                 ("PARALLEL_SHARE * cache_gb", "cache_gb", {"parallel": 4})):
            with self.subTest(new=new), self.assertRaisesRegex(watch.Incomplete, "review required"):
                self.plan(self.source.replace(old, new), **option)


class StockRelease0141Plan(unittest.TestCase):
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_41_plan.py").read_text()

    def plan(self, source=None):
        return watch.stock_plan(self.source if source is None else source, family="coder", model="IQ1_M",
                                context=131072, ram=64, vram=24)

    def test_compute_mode_probe_is_fixed_and_pure_warning_handles_unknown_default_and_restricted_modes(self):
        original, namespace = watch.pure_exec, {}
        def capture(nodes, ns):
            original(nodes, ns)
            namespace.update(ns)
        with patch.object(watch.subprocess, "run", side_effect=AssertionError("hardware probe executed")) as probe, \
                patch.object(watch, "pure_exec", side_effect=capture):
            plan = self.plan()
        probe.assert_not_called()
        self.assertEqual("Default", namespace["gpu_compute_mode"](0))
        warning = namespace["compute_mode_warning"]
        for mode in ("", "Default", "default", "N/A", "[N/A]"):
            with self.subTest(mode=mode):
                self.assertIsNone(warning(0, mode))
        for mode in ("Exclusive_Process", "Prohibited"):
            with self.subTest(mode=mode):
                self.assertIn(f"GPU 0 is in the compute mode {mode}, not Default", warning(0, mode))
        self.assertNotIn("out", namespace)
        self.assertNotIn("env", plan["config_keys"])

    def test_compute_mode_advisory_refuses_new_config_work_other_callers_and_io(self):
        block = "w = compute_mode_warning(gi, gpu_compute_mode(gi))"
        for before, after in ((block, block + '\n            args += ["--spec", "1"]'),
                              (block, block + "\n            pack.read_text()"),
                              ("    if scaling is not None:",
                               "    args.append(gpu_compute_mode(0))\n    if scaling is not None:"),
                              ('    if not mode or mode.lower()', '    if pack.read_text() or not mode or mode.lower()')):
            with self.subTest(after=after), self.assertRaisesRegex(watch.Incomplete, "review required"):
                self.plan(self.source.replace(before, after))

    def test_remote_cache_comprehension_is_admitted_only_as_the_exact_reviewed_helper(self):
        for before, after in (('a.split("=", 1)[0]', 'a.split("=", 1)[-1]'),
                              ('    if scaling is not None:',
                               '    args.append(str(any(a for a in args)))\n    if scaling is not None:')):
            with self.subTest(after=after), self.assertRaisesRegex(watch.Incomplete, "review required"):
                self.plan(self.source.replace(before, after))


class StockRelease0142Plan(unittest.TestCase):
    def setUp(self):
        self.source = (REPO / "tests/fixtures/strata_0_1_42_plan.py").read_text()
        self.inventory = json.loads((REPO / "tests/fixtures/strata_0_1_42_gpu_inventory.json").read_text())

    def plan(self, source=None, **options):
        return watch.stock_plan(self.source if source is None else source,
                                **({"family": "coder", "model": "IQ1_M", "context": 131072, "ram": 128,
                                    "gpu_inventory": self.inventory, "gpus": "all"} | options))

    def test_single_card_keeps_explicit_model_and_exposes_stock_host_default(self):
        plan = self.plan(gpu_inventory=None, gpus=None, vram=24)
        self.assertEqual(0, plan["setup_args"]["gpu"])
        self.assertNotIn("gpus", plan["host"])
        self.assertEqual(sorted(watch.GENERATED_CONFIG_KEYS), plan["config_keys"])
        self.assertEqual(("coder", "IQ1_M"), (plan["setup_args"]["family"], plan["setup_args"]["model"]))
        default = plan["stock_default_recommendation"]
        self.assertEqual(("qwen", "IQ3_XXS", 131072),
                         (default["family"], default["model"], default["context"]))
        self.assertTrue(any("informational" in note for note in plan["notes"]))
        for ram, expected in ((59.9, "Q2_0"), (60, "IQ3_XXS")):
            with self.subTest(ram=ram):
                self.assertEqual(expected, self.plan(ram=ram)["stock_default_recommendation"]["model"])

    def test_two_cards_follow_stock_order_and_plain_layer_split(self):
        original = copy.deepcopy(self.inventory)
        plan = self.plan()
        self.assertEqual([1, 0], plan["setup_args"]["gpus"])
        self.assertEqual("auto", plan["setup_args"]["layer_split"])
        self.assertNotIn("gpu", plan["setup_args"])
        self.assertNotIn("--remote-expert-opt", plan["expected_engine_flags"])
        self.assertNotIn("--layer-split", plan["expected_engine_flags"])  # the server emits this
        self.assertEqual(sorted(watch.GENERATED_CONFIG_KEYS | {"layer_split"}), plan["config_keys"])
        self.assertEqual(["NVIDIA GeForce RTX 4090", "NVIDIA GeForce RTX 3090"],
                         [card["gpu_model"] for card in plan["host"]["gpus"]])
        self.assertEqual([False, True], [card["display_attached"] for card in plan["host"]["gpus"]])
        self.assertEqual({"gpu_index", "gpu_model", "arch", "pci_bus_id", "min_gpu_vram_mib", "display_attached"},
                         set(plan["host"]["gpus"][0]))
        self.assertEqual(original, self.inventory)
        self.assertEqual(plan, self.plan(gpus=[1, 0]))

    def test_non_stock_explicit_order_is_refused_with_stock_order(self):
        with self.assertRaisesRegex(watch.Incomplete, r"stock order: \[1, 0\]"):
            self.plan(gpus=[0, 1])

    def test_scalar_and_multi_inputs_cannot_be_mixed_or_partial(self):
        for options in ({"gpu": 0}, {"vram": 24}, {"gpus": None}, {"gpu_inventory": None}):
            with self.subTest(options=options), self.assertRaises(watch.Incomplete):
                self.plan(**options)

    def test_inventory_types_uniqueness_membership_and_small_cards_fail_closed(self):
        for key, value in (("index", True), ("index", -1), ("arch", "sm_89"), ("arch", "60"),
                           ("vram_mib", True), ("vram_mib", 24576.0), ("vram_mib", 12 * 1024),
                           ("display_attached", None), ("pci_bus_id", "00000000:GG:00.0")):
            cards = copy.deepcopy(self.inventory)
            cards[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(watch.Incomplete):
                self.plan(gpu_inventory=cards)
        for cards in ([self.inventory[0], self.inventory[0]], self.inventory[:1]):
            with self.subTest(cards=cards), self.assertRaises(watch.Incomplete):
                self.plan(gpu_inventory=cards)
        for selection in ([0, 0], [1, 2], [True, 0], [1], "0,1"):
            with self.subTest(selection=selection), self.assertRaises(watch.Incomplete):
                self.plan(gpus=selection)

    def test_every_selected_card_and_fixed_opt_ins_reach_stock_assembly(self):
        original, namespace = watch.pure_exec, {}
        def capture(nodes, ns):
            original(nodes, ns)
            namespace.update(ns)
        with patch.object(watch.subprocess, "run", side_effect=AssertionError("hardware probe executed")), \
                patch.object(watch, "pure_exec", side_effect=capture):
            self.plan()
        self.assertEqual([1, 0], namespace["multi"])
        self.assertEqual([1, 0], [g["index"] for g in namespace["chosen"]])
        self.assertEqual(2, namespace["gpu"]["count"])
        self.assertEqual(1, namespace["a"].gpu)
        self.assertEqual("auto", namespace["a"].layer_split)
        self.assertFalse(namespace["a"].no_remote_expert_opt)
        self.assertIsNone(namespace["a"].replicas)
        self.assertEqual("Default", namespace["gpu_compute_mode"](0))

    def test_slots_use_both_cards_and_reserve_each_streamed_session_not_each_arena(self):
        one = self.plan(gpu_inventory=None, gpus=None, vram=24)
        kv_ram = 131072 * 13 * 1056 / 1e9
        for slots in (None, 4):
            with self.subTest(slots=slots):
                plan = self.plan(parallel=slots)
                sessions = 2 * (slots or 1)
                extra = (sessions - 1) * kv_ram
                self.assertAlmostEqual(extra, plan["thresholds"]["extra_streamed_session_ram_gib"])
                self.assertEqual(math.ceil(32 + sessions * kv_ram + 1), plan["host"]["min_total_ram_gib"])
                self.assertEqual(math.ceil(32 + sessions * kv_ram), plan["host"]["min_available_ram_gib_at_start"])
                self.assertEqual(one["thresholds"]["arena_gb"], plan["thresholds"]["arena_gb"])
                self.assertEqual(one["host"]["min_free_disk_gib"], plan["host"]["min_free_disk_gib"])
                self.assertEqual(one["expected_engine_flags"], plan["expected_engine_flags"])
                self.assertTrue(any("conservative" in note for note in plan["notes"]))
        self.assertEqual(4, self.plan(parallel=4)["setup_args"]["parallel"])
        with self.assertRaisesRegex(watch.Incomplete, "recommended for this card: 4"):
            self.plan(parallel=5)
        with self.assertRaisesRegex(watch.Incomplete, "one at a time"):
            self.plan(gpu_inventory=None, gpus=None, vram=24, model="IQ3_S", family="qwen", parallel=4)
        self.assertEqual(4, self.plan(model="IQ3_S", family="qwen", parallel=4)["setup_args"]["parallel"])
        with self.assertRaisesRegex(watch.Incomplete, "conservative"):
            self.plan(ram=35)

    def test_no_streaming_means_no_extra_session_reservation(self):
        plan = self.plan(context=32768)
        self.assertNotIn("--kv-resident", plan["expected_engine_flags"])
        self.assertEqual(0, plan["thresholds"]["extra_streamed_session_ram_gib"])

    def test_new_reviewed_helpers_and_unreachable_branches_refuse_ast_mutations(self):
        for name in ("gpu_rank", "gpu_problem", "together_ok", "ram_ctx", "recommend_remote_expert_opt"):
            tree = ast.parse(self.source)
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            node.body.append(ast.Pass())
            with self.subTest(helper=name), self.assertRaisesRegex(watch.Incomplete, "review required"):
                self.plan(ast.unparse(ast.fix_missing_locations(tree)))
        for before, after in (('cfg["replicas"] = a.replicas', 'cfg["replicas"] = a.replicas + 1'),
                              ('if a.replicas is not None and a.replicas >= 2:', 'if True:'),
                              ('slots = uma_expert_cache(', 'slots = unknown_cache('),
                              ('if budget is not None and not q4_split:', 'if True:'),
                              ('if ram >= 60 and "IQ3_XXS" in names', 'if ram >= 61 and "IQ3_XXS" in names'),
                              ('cfg["gpu"] = multi', 'cfg["gpu"] = multi[::-1]'),
                              ('cfg["layer_split"] = a.layer_split or "auto"', 'cfg["layer_split"] = "manual"')):
            self.assertIn(before, self.source)
            with self.subTest(after=after), self.assertRaises(watch.Incomplete):
                self.plan(self.source.replace(before, after))

    def test_old_lane_and_v42_unreviewed_modes_are_refused(self):
        for options in ({"ram": 32}, {"model": "UD-Q4_K_XL", "family": "qwen"}):
            with self.subTest(options=options), self.assertRaises(watch.Incomplete):
                self.plan(**options)
        with self.assertRaisesRegex(watch.Incomplete, "v0.1.42"):
            self.plan((REPO / "tests/fixtures/strata_0_1_41_plan.py").read_text())

    def test_cli_selection_and_complete_inventory_document(self):
        with patch.object(watch, "auth_token", return_value=None), \
                patch.object(watch, "draft", return_value={}) as draft, \
                patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            code = watch.main(["draft", "--from", "profile.json", "--strata-tag", "v0.1.42",
                               "--omp-tag", "v18.8.9", "--id", "fixture-pair", "--strata-src", "source",
                               "--gpu-inventory", "inventory.json", "--gpus", "1,0"])
        self.assertEqual(0, code)
        self.assertEqual(Path("inventory.json"), draft.call_args.kwargs["gpu_inventory"])
        self.assertEqual([1, 0], draft.call_args.kwargs["gpus"])
        self.assertIsNone(draft.call_args.kwargs["vram"])
        self.assertEqual("all", watch.gpus_arg("all"))
        self.assertEqual([1, 0], watch.gpus_arg("1,0"))
        for value in ("0", "1,-1", "1,,0", "0,1,", "ALL"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                watch.gpus_arg(value)
        rows = [{**card, "memory_total_mib": card["vram_mib"], "driver_version": "580.00"}
                for card in self.inventory]
        document = {"schema_version": 1, "complete": True, "missing": [], "gpus": rows}
        self.assertEqual(self.inventory, watch.inventory_cards(document))
        for change in ({"complete": False}, {"schema_version": True}, {"gpus": None}):
            with self.subTest(change=change), self.assertRaises(watch.Incomplete):
                watch.inventory_cards(document | change)
        # The inventory command reports a host without advisory PCIe fields as complete, with those gaps in missing.
        advisory = document | {"missing": ["GPU 0.pcie_gen_current: unavailable"]}
        self.assertEqual(self.inventory, watch.inventory_cards(advisory))

    def test_cli_passes_pipeline_windows_to_the_draft(self):
        with patch.object(watch, "auth_token", return_value=None), \
                patch.object(watch, "draft", return_value={}) as draft, \
                patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            code = watch.main(["draft", "--from", "profile.json", "--strata-tag", "v0.1.42",
                               "--omp-tag", "v18.8.9", "--id", "fixture-pair", "--strata-src", "source",
                               "--gpu-inventory", "inventory.json", "--gpus", "all", "--pipeline-windows", "2"])
        self.assertEqual(0, code)
        self.assertEqual(2, draft.call_args.kwargs["pipeline_windows"])


class StockRopePlan(unittest.TestCase):
    def test_contexts_past_the_trained_length_take_stock_yarn_and_stream_their_kv(self):
        source = (REPO / "tests/fixtures/strata_0_1_36_plan.py").read_text()
        # Total-RAM floor: stock's KV-streaming threshold, the Coder's 32 GB + context x 13 x 1056 B + 1 GB.
        for context, scale, min_total in ((262144, None, 37), (393216, "1.5", 39), (524288, "2", 41)):
            with self.subTest(context=context):
                plan = watch.stock_plan(source, family="coder", model="IQ1_M", context=context, ram=127.69, vram=24)
                pairs = flag_pairs(plan["expected_engine_flags"])
                self.assertEqual(("yarn", scale) if scale else (None, None),
                                 (pairs.get("--rope-scaling"), pairs.get("--rope-scale")))
                self.assertEqual("32768", pairs["--kv-resident"])
                self.assertEqual(min_total, plan["host"]["min_total_ram_gib"])


if __name__ == "__main__":
    unittest.main()
