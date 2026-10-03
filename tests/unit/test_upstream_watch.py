"""Metadata fixtures and disposable git histories; no network, installers or GPU runtime."""
from __future__ import annotations

import copy
import json
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
        for tag, code in (("v0.1.9", 0), ("v0.1.34", 0), ("v0.1.36", 3)):
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

    def test_annotated_tag_and_missing_asset_refused(self):
        repo, tag = watch.REPOS["strata"], "v0.1.36"
        responses = {
            f"{watch.GITHUB}/repos/{repo}/git/ref/tags/{tag}": ({"object": {"type": "tag", "sha": "a" * 40}}, {}),
            f"{watch.GITHUB}/repos/{repo}/releases/tags/{tag}": ({**release(tag), "id": 1}, {}),
            f"{watch.GITHUB}/repos/{repo}/releases/1/assets?per_page=100": ([], {})}
        api = watch.API(FixtureTransport(responses))
        with self.assertRaisesRegex(watch.Incomplete, "annotated tags refused"):
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
        with self.assertRaisesRegex(watch.Incomplete, "unreviewed config keys"):
            watch.stock_plan((self.src / "setup.py").read_text(), family="coder", model="IQ1_M", context=131072, ram=64, vram=24)

    def test_plan_refuses_degradation_and_keeps_large_context(self):
        with self.assertRaisesRegex(watch.Incomplete, "low-RAM"):
            watch.stock_plan(SETUP, family="coder", model="IQ1_M", context=131072, ram=32, vram=24)
        with self.assertRaisesRegex(watch.Incomplete, "degrades"):
            watch.stock_plan(SETUP, family="coder", model="IQ1_M", context=131072, ram=34, vram=24)
        plan = watch.stock_plan(SETUP, family="coder", model="IQ1_M", context=262144, ram=192, vram=24)
        flags = plan["expected_engine_flags"]
        self.assertEqual("262144", flags[flags.index("--max-context") + 1])
        self.assertEqual(37, plan["host"]["min_total_ram_gib"])
        self.assertEqual(36, plan["host"]["min_available_ram_gib_at_start"])
        self.assertNotIn("--rope-scaling", flags)
        with self.assertRaisesRegex(watch.Incomplete, "new call"):
            watch.stock_plan(SETUP.replace('cfg_path = ROOT', 'danger()\n    cfg_path = ROOT'),
                             family="coder", model="IQ1_M", context=131072, ram=64, vram=24)

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
