"""Stock v0.2.12 admission boundaries; source-only, without installer or GPU execution."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from omp_strata import dflash2, engine_component, hostrun
from omp_strata.profile import ENGINE_ENV_GROUPS, load, validate
from scripts import upstream_watch as watch

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests/fixtures"


def fixture(name):
    return (FIXTURES / ("strata_0_2_12_" + name)).read_text()


class Stock0212Fixtures(unittest.TestCase):
    def test_source_payloads_match_their_recorded_digests(self):
        files = sorted(FIXTURES.glob("strata_0_2_12_*"))
        self.assertEqual(7, len(files))
        for path in files:
            with self.subTest(path=path.name):
                header, payload = path.read_bytes().split(b"# Stock payload follows.\n", 1)
                hashes = dict(line.removeprefix(b"# ").split(b": ", 1) for line in header.splitlines()
                              if b" SHA-256: " in line)
                self.assertEqual(hashes[b"Payload SHA-256"].decode(), hashlib.sha256(payload).hexdigest())
                self.assertRegex(hashes[b"Source SHA-256"].decode(), r"^[0-9a-f]{64}$")
                if path.suffix == ".py":
                    ast.parse(payload)

    def test_runtime_requirements_are_unchanged_from_v0211(self):
        for name in ("requirements.txt", "requirements_monitor.txt"):
            previous = (FIXTURES / ("strata_0_2_11_" + name)).read_text()
            self.assertEqual(previous.split("# Stock payload follows.\n", 1)[1],
                             fixture(name).split("# Stock payload follows.\n", 1)[1])


class Stock0212Plan(unittest.TestCase):
    def plan(self, source=None, **options):
        return watch.stock_plan(fixture("plan.py") if source is None else source,
                                **({"family": "coder", "model": "IQ1_M", "context": 131072,
                                    "ram": 47.15475845336914, "vram": 31.8427734375,
                                    "engine_version": (0, 1, 58)} | options))

    def test_current_lane_plans_keep_their_setup_flags_shards_and_floors(self):
        previous = (FIXTURES / "strata_0_2_11_plan.py").read_text()
        inventory = json.loads((FIXTURES / "strata_0_1_42_gpu_inventory.json").read_text())
        pair = {"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 127.68849182128906,
                "vram": None, "gpu_inventory": inventory, "gpu_roles": {0: "main", 1: "helper"},
                "layer_split": "24"}
        pro = {"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 191.69942092895508,
               "vram": 95.5927734375, "parallel": 4, "cpu_cores": (8, 16),
               "kv_streaming": "off", "gpu_arch": "120"}
        for options in ({}, {"context": 262144, "kv_streaming": "off"}, pro, pair):
            with self.subTest(options=options):
                old, new = self.plan(previous, **options), self.plan(**options)
                for key in ("setup_args", "expected_engine_flags", "config_keys", "model_files", "model_url",
                            "host", "thresholds", "stock_tips"):
                    self.assertEqual(old[key], new[key], key)

    def test_changed_unreachable_budget_statement_still_refuses(self):
        tree = ast.parse(fixture("plan.py"))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        branch = next(n for n in main.body if isinstance(n, ast.If)
                      and ast.dump(n.test) == ast.dump(ast.parse(
                          "budget is not None and not q4_split", mode="eval").body))
        branch.body.append(ast.Pass())
        with self.assertRaisesRegex(watch.Incomplete, "new call in stock setup planning"):
            self.plan(ast.unparse(ast.fix_missing_locations(tree)))

    def test_uma_expert_cache_is_not_in_the_generic_call_vocabulary(self):
        with self.assertRaisesRegex(watch.Incomplete, "new call in stock setup planning"):
            watch.pure_exec(ast.parse("uma_expert_cache(1)").body, {})


class Stock0212Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = fixture("server_engine_path.py")
        cls.sources = {"strata_control/drafting.py": fixture("drafting.py")}
        previous = watch.SERVER_REVIEWS["0.2.11"]
        for path in (dict(previous["modules"].values()) | previous["sources"]):
            if path not in cls.sources:
                cls.sources[path] = (FIXTURES / ("strata_0_2_11_" + Path(path).name)).read_text()
        cls.modules = {path: watch.reviewed_hash(ast.parse(source)) for path, source in cls.sources.items()}

    def test_full_review_keeps_the_previous_closure_imports_and_other_modules(self):
        for groups in ((), tuple(watch.ENGINE_ENV_GROUPS)):
            self.assertEqual("0.2.12", watch.server_pinned_path_review(self.source, groups,
                                                                     module_digests=self.modules))
        previous, current = watch.SERVER_REVIEWS["0.2.11"], watch.SERVER_REVIEWS["0.2.12"]
        for key in ("roots", "functions", "imports", "sources"):
            self.assertEqual(previous[key], current[key], key)
        self.assertEqual(previous["modules"] | {
            "drafting": ("strata_control/drafting.py", self.modules["strata_control/drafting.py"])},
                         current["modules"])

    def test_changed_missing_or_mixed_sources_refuse(self):
        for path in self.modules:
            for modules in ({p: h for p, h in self.modules.items() if p != path},
                            self.modules | {path: "0" * 64}):
                with self.subTest(path=path), self.assertRaisesRegex(watch.Incomplete, "engine environment/argv"):
                    watch.server_pinned_path_review(self.source, (), module_digests=modules)

    def test_ambiguous_review_refuses(self):
        with patch.dict(watch.SERVER_REVIEWS, {"duplicate": copy.deepcopy(watch.SERVER_REVIEWS["0.2.12"])}):
            with self.assertRaises(watch.Incomplete):
                watch.server_pinned_path_review(self.source, (), module_digests=self.modules)

    def test_source_review_binds_the_app_to_engine_0158(self):
        with patch.object(watch, "git_blob", side_effect=lambda src, commit, path: self.sources.get(path)), \
                patch.object(watch, "git", return_value=self.source):
            self.assertEqual("0.2.12", watch.source_server_review(None, "pinned", "0.1.58", ()))
            with self.assertRaisesRegex(watch.Incomplete, "review 0.2.12 is for engine 0.1.58, not 0.1.57"):
                watch.source_server_review(None, "pinned", "0.1.57", ())


class Stock0212DFlash2(unittest.TestCase):
    def pins(self, *, fetch_source=None, server_key="0.2.12"):
        from tests.unit.test_component_engine import NAME, members, write_archive
        from tests.unit.test_upstream_watch import FixtureTransport

        sources = {"strata_control/drafting.py": fixture("drafting.py"),
                   "strata_control/drafting_fetch.py": fixture("drafting_fetch.py") if fetch_source is None
                   else fetch_source, "tools/dflash2_pack.py": fixture("dflash2_pack.py")}
        metadata = {"sha": dflash2.REVISION, "cardData": {"license": "apache-2.0"}, "siblings": [
            {"rfilename": name, "size": size,
             **({"lfs": {"size": size, "sha256": sha}} if name.endswith(".safetensors") else {})}
            for name, size, sha in dflash2.FILES]}
        url = f"{watch.HF}/api/models/{dflash2.REPO}/revision/{dflash2.REVISION}?blobs=true"
        api = watch.API(FixtureTransport({url: (metadata, {})}), allow_github=False)
        def source(_src, operation, spec, **kwargs):
            path = spec.split(":", 1)[1]
            return b"shipped vocabulary" if path == "data/draft_vocab.bin" else sources[path]
        with tempfile.TemporaryDirectory() as directory, patch.object(watch, "git", side_effect=source):
            archive = Path(directory) / NAME
            pin = write_archive(archive, members(payload={
                "strata.exe": b"\0".join((dflash2.MARK_ON, dflash2.MARK_VOCAB, dflash2.MARK_SELQ4))}))
            return watch.dflash2_pins(api, None, "a" * 40, archive, pin,
                                     server_key=server_key, strata_tag="v" + server_key)

    def test_v0212_stock_modules_keep_the_locally_packed_pin(self):
        pins = self.pins()
        self.assertEqual([], dflash2.validate_source({"dflash2_source": pins}))
        self.assertEqual("locally-packed", pins["kind"])
        self.assertEqual("selq4", pins["runtime_pack"])
        self.assertTrue(all(p["sha256_source"].startswith("Stock v0.2.12 drafting.FILES;") for p in pins["files"]))

    def test_fetch_module_changes_are_release_specific_and_fail_closed(self):
        with self.assertRaisesRegex(watch.Incomplete, "stock DFlash2 module changed"):
            self.pins(fetch_source=fixture("drafting_fetch.py") + "\nchanged = True\n")
        with self.assertRaisesRegex(watch.Incomplete, "stock DFlash2 module changed"):
            self.pins(server_key="0.2.11")


class Stock0212Engine(unittest.TestCase):
    def test_published_component_manifests_bind_engine_0158(self):
        manifest_raw = (FIXTURES / "engine_0_1_58_engine-component.json").read_bytes()
        build_raw = (FIXTURES / "engine_0_1_58_BUILD.json").read_bytes()
        self.assertEqual("d4964abd777ce53e518abf78f0af1882ad779a225550e1480a2267486ea055a0",
                         hashlib.sha256(manifest_raw).hexdigest())
        manifest, build = json.loads(manifest_raw), json.loads(build_raw)
        files = engine_component._manifest_files(manifest, platform="windows-x86_64", backend="cuda",
                                                  variant="cuda13")
        engine_component._build_checks(build, "0.1.58")
        self.assertEqual(files["BUILD.json"]["sha256"], hashlib.sha256(build_raw).hexdigest())
        self.assertEqual(240, files["BUILD.json"]["bytes"])
        self.assertEqual("8a42a9457db6+cuda13.0", manifest["build_id"])
        self.assertEqual(("f-0212-rc", "8a42a9457db6"), (build["source"], build["commit"]))

    def test_reviewed_environment_groups_keep_all_three_lane_unions(self):
        from tests.unit.test_profile import EngineEnvProfileTests
        # Lead's 0.1.58 source review: all 20 variables retain meaning/default; nv_defaults.cpp is unchanged.
        # Stock 146df3c4 src/core/nv_defaults.cpp:31-39; serve/server.py:4269-4272,4321.
        fixture_case = EngineEnvProfileTests()
        for groups, pair in ((("gdn_stack",), False), (("parallel_stack", "gdn_stack"), False),
                             (("sm86_table", "gdn_stack"), True)):
            data = fixture_case.data(pair)
            data["strata"]["engine_version"] = "0.1.58"
            data["strata"]["setup_args"]["parallel"] = 4
            data["strata"]["engine_env"] = {k: v for group in groups for k, v in ENGINE_ENV_GROUPS[group].items()}
            with self.subTest(groups=groups):
                self.assertEqual([], validate(data))

    def test_defaults_note_preserves_the_reviewed_chunk_and_fallback_accounting(self):
        for multi in (False, True):
            note = watch.engine_defaults_note("0.1.58", multi_gpu=multi, ple_io="direct")
            self.assertIsNotNone(note)
            for text in ("Stock engine 0.1.58", "60 s", "Linux-only", "no drafter",
                         "8192-token chunks" if multi else "32768-token chunks"):
                with self.subTest(multi=multi, text=text):
                    self.assertIn(text, note)


class Stock0212Timing(unittest.TestCase):
    def test_history_and_totals_preserve_unknown_legs(self):
        from scripts import realhost_gates as gates
        from types import SimpleNamespace

        layout = SimpleNamespace(profile=SimpleNamespace(data={"server": {"listen_host": "127.0.0.1",
                                                                          "port": 18090}}))
        records = [{"time": 2, "prompt_ms": None, "decode_ms": None, "decode_tok_s": None}]
        with patch.object(gates, "http", return_value=(200, {"requests": records})):
            history = gates.engine_requests(layout, "fixture", since=1)
        for key in ("prompt_ms", "decode_ms", "decode_tok_s"):
            self.assertIsNone(history[0][key])
        totals = {"totals": {"decode_ms": None, "generated": None}}
        with patch.object(hostrun.lifecycle, "http_json", return_value=(200, totals)):
            self.assertEqual(totals, hostrun.strata_metrics(layout, "fixture"))

    def test_receipts_label_new_accounting_without_inventing_unknown_durations(self):
        from scripts import publish_run

        profile = load(REPO / "profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json")
        profile.data["strata"]["tag"] = "v0.2.12"
        for gate in ("G15", "G16", "G17"):
            _, metrics, limitations = publish_run.gate_details(gate, {}, {}, "fixture", profile, {})
            self.assertTrue(all(m["value"] is None and m["method"] == "unavailable" for m in metrics))
            self.assertTrue(any("slot-admission DONE" in text for text in limitations))
