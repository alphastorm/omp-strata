"""Stock v0.2.11 admission boundaries; source-only, with no installer or GPU execution."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata import install, lifecycle
from omp_strata.layout import Layout
from omp_strata.profile import Profile
from scripts import upstream_watch as watch

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests/fixtures"


def fixture(name):
    return (FIXTURES / ("strata_0_2_11_" + name)).read_text()


class Stock0211Fixtures(unittest.TestCase):
    def test_source_payloads_match_their_recorded_digests(self):
        files = sorted(FIXTURES.glob("strata_0_2_11_*"))
        self.assertEqual(14, len(files))
        for path in files:
            with self.subTest(path=path.name):
                header, payload = path.read_bytes().split(b"# Stock payload follows.\n", 1)
                digest = next(line.split(b": ", 1)[1] for line in header.splitlines()
                              if line.startswith(b"# Payload SHA-256: ")).decode()
                self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
                source_digest = next(line.split(b": ", 1)[1] for line in header.splitlines()
                                     if line.startswith(b"# Source SHA-256: ")).decode()
                self.assertRegex(source_digest, r"^[0-9a-f]{64}$")
                if path.suffix == ".py":
                    ast.parse(payload)


class Stock0211Plan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = fixture("plan.py")

    def plan(self, source=None, **options):
        return watch.stock_plan(self.source if source is None else source,
                                **({"family": "coder", "model": "IQ1_M", "context": 131072,
                                    "ram": 47.15475845336914, "vram": 31.8427734375,
                                    "engine_version": (0, 1, 57)} | options))

    def test_models_aliases_are_literal(self):
        models = watch.literal_constants(self.source, ("MODELS",))["MODELS"]
        self.assertEqual((0, 1, 57), models["UD-IQ4_XS-v31"]["engine"])

    def test_nonliteral_models_alias_is_refused(self):
        tree = ast.parse(self.source)
        alias = next(n for n in tree.body if watch.assigned(n, "UNSLOTH_V31_ENGINE"))
        alias.value = ast.parse("tuple((0, 1, 57))", mode="eval").body
        changed = ast.unparse(ast.fix_missing_locations(tree))
        with self.assertRaisesRegex(watch.Incomplete, "MODELS is no longer literal"):
            watch.literal_constants(changed, ("MODELS",))

    def test_unsloth_default_env_has_the_reviewed_native_values(self):
        ns = {"WIN": True}
        watch.run_reviewed(ast.parse(self.source), ("unsloth_default_env",), ns)
        self.assertEqual({}, ns["unsloth_default_env"]("qwen", "IQ3_S", False, False))
        self.assertEqual({"STRATA_HC_Q8": "1", "STRATA_ROUTE_TAIL_SKIP": "0"},
                         ns["unsloth_default_env"]("unsloth", "UD-Q4_K_XL", False, False))

    def test_changed_unsloth_default_env_is_refused(self):
        tree = ast.parse(self.source)
        helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unsloth_default_env")
        helper.body.append(ast.Pass())
        with self.assertRaisesRegex(watch.Incomplete, "unsloth_default_env is missing or changed"):
            watch.run_reviewed(tree, ("unsloth_default_env",), {"WIN": True})

    def test_families_statement_keeps_existing_families_and_four_alternate_shards(self):
        class FamiliesReady(Exception):
            pass
        captured = {}
        original = watch.pure_exec
        def stop_after_families(nodes, ns):
            if "FAMILIES" in ns:
                captured.update(ns)
                raise FamiliesReady
            return original(nodes, ns)
        with patch.object(watch, "pure_exec", side_effect=stop_after_families):
            with self.assertRaises(FamiliesReady):
                self.plan()
        self.assertEqual(4, len(captured["FAMILIES"]["unsloth"]["sha256_alt"]))
        previous = (FIXTURES / "strata_0_2_10_plan.py").read_text()
        ns = watch.literal_constants(previous, ("HF_REVISIONS", "UNSLOTH_SHARDS", "UNSLOTH_IQ4_XS_SHARDS",
                                                "UNSLOTH_BIG_SHARDS", "GYRO_FILES"))
        ns["hf"] = lambda repo: f"{watch.HF}/{repo}/resolve/{ns['HF_REVISIONS'][repo]}/"
        families = next(n for n in ast.parse(previous).body if watch.assigned(n, "FAMILIES"))
        watch.pure_exec([families], ns)
        for family in ("qwen", "coder"):
            self.assertEqual(ns["FAMILIES"][family], captured["FAMILIES"][family])

    def test_changed_families_comprehension_is_not_generally_executable(self):
        tree = ast.parse(self.source)
        families = next(n for n in tree.body if watch.assigned(n, "FAMILIES"))
        comprehension = next(n for n in ast.walk(families) if isinstance(n, ast.DictComp))
        comprehension.generators[0].ifs.append(ast.Constant(True))
        with self.assertRaisesRegex(watch.Incomplete, "planning loop is unreviewed"):
            self.plan(ast.unparse(ast.fix_missing_locations(tree)))

    def test_model_helpers_keep_iq3s_and_iq1m_shard_names(self):
        class HelpersReady(Exception):
            pass
        captured = {}
        original = watch.pure_exec
        def stop_after_helpers(nodes, ns):
            original(nodes, ns)
            if nodes and all(isinstance(n, ast.FunctionDef) for n in nodes) and "model_file" in ns:
                captured.update(ns)
                raise HelpersReady
        with patch.object(watch, "pure_exec", side_effect=stop_after_helpers):
            with self.assertRaises(HelpersReady):
                self.plan()
        previous = (FIXTURES / "strata_0_2_10_plan.py").read_text()
        for family, model, options in (
                ("coder", "IQ1_M", {}),
                ("qwen", "IQ3_S", {"context": 262144, "ram": 192, "vram": 95.5,
                                   "parallel": 4, "cpu_cores": (8, 16)})):
            fam = captured["FAMILIES"][family]
            count = captured["model_shards"](fam, model)
            actual = [captured["model_file"](fam, model, i) for i in range(1, count + 1)]
            self.assertEqual(self.plan(previous, family=family, model=model, **options)["model_files"], actual)

    def test_per_model_revision_or_quant_is_refused_before_lane_planning(self):
        with self.assertRaisesRegex(watch.Incomplete, "per-model Hub revision/quant"):
            self.plan(family="unsloth", model="UD-IQ3_XXS")
        for value in ({"revision": "a" * 40}, {"quant": "IQ1_M-other"}):
            tree = ast.parse(self.source)
            models = next(n for n in tree.body if watch.assigned(n, "MODELS"))
            index = next(i for i, k in enumerate(models.value.keys)
                         if isinstance(k, ast.Constant) and k.value == "IQ1_M")
            models.value.values[index].keys.append(ast.Constant(next(iter(value))))
            models.value.values[index].values.append(ast.Constant(next(iter(value.values()))))
            with self.subTest(value=value), self.assertRaisesRegex(watch.Incomplete, "per-model Hub revision/quant"):
                self.plan(ast.unparse(ast.fix_missing_locations(tree)))

    def test_changed_model_helpers_are_refused(self):
        for name in ("model_file", "model_quant"):
            tree = ast.parse(self.source)
            helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            helper.body.append(ast.Pass())
            with self.subTest(name=name), self.assertRaisesRegex(watch.Incomplete, "missing or changed"):
                watch.run_reviewed(tree, ("model_quant", "model_file"), {})

    def test_checklist_plan_reaches_the_split_disk_estimate(self):
        plan = self.plan(ram=45, vram=32000 / 1024, reviewed=False)
        self.assertEqual("IQ1_M", plan["setup_args"]["model"])
        self.assertGreater(plan["host"]["min_free_disk_gib"], 0)

    def test_existing_lane_plans_and_floors_are_unchanged(self):
        previous = (FIXTURES / "strata_0_2_10_plan.py").read_text()
        inventory = json.loads((FIXTURES / "strata_0_1_42_gpu_inventory.json").read_text())
        pair = {"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 127.68849182128906,
                "vram": None, "gpu_inventory": inventory, "gpu_roles": {0: "main", 1: "helper"},
                "layer_split": "24"}
        for options in ({}, {"context": 262144}, {"context": 262144, "kv_streaming": "off"}, pair):
            with self.subTest(options=options):
                old, new = self.plan(previous, **options), self.plan(**options)
                for key in ("setup_args", "expected_engine_flags", "config_keys", "model_files", "model_url",
                            "host", "thresholds"):
                    self.assertEqual(old[key], new[key], key)

    def test_changed_copy_estimate_is_refused(self):
        tree = ast.parse(self.source)
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        copy_gb = next(n for n in main.body if watch.assigned(n, "copy_gb"))
        copy_gb.value = ast.Constant(1)
        with self.assertRaisesRegex(watch.Incomplete, "split disk estimate changed"):
            self.plan(ast.unparse(ast.fix_missing_locations(tree)))

    def pro_plan(self, source=None, **options):
        return self.plan(source, **({"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 192,
                                    "vram": 95.5, "parallel": 4, "cpu_cores": (8, 16),
                                    "tips": {"--prefill": "auto:32768"}} | options))

    def test_pro_bare_auto_drops_the_old_tip(self):
        plan = self.pro_plan(gpu_arch="120")
        self.assertEqual({}, plan["stock_tips"])
        self.assertEqual({"min_total_ram_gib": 0, "extra_available_ram_gib": 0}, plan["tips_ram"])
        flags = plan["expected_engine_flags"]
        self.assertEqual("auto", flags[flags.index("--prefill") + 1])
        with patch.dict(os.environ, watch.NV_CHUNK_ENV_PROBE):
            self.assertEqual(plan, self.pro_plan(gpu_arch="120"))

    def test_pre_ampere_card_still_gets_the_prefill_tip(self):
        self.assertEqual({"--prefill": "auto:32768"}, self.pro_plan(gpu_arch="75")["stock_tips"])

    def test_tips_need_reviewed_single_card_architecture(self):
        with self.assertRaisesRegex(watch.Incomplete, "reviewed compute capability"):
            self.pro_plan()

    def test_predecessor_keeps_seven_argument_tips(self):
        previous = (FIXTURES / "strata_0_2_10_plan.py").read_text()
        self.assertEqual({"--prefill": "auto:32768"}, self.pro_plan(previous)["stock_tips"])


class Stock0211Dependencies(unittest.TestCase):
    LOCK = "locks/strata-python-cp313-win_amd64-strata0.2.11.txt"

    def review(self, lock=None):
        current = fixture("plan.py")
        previous = (FIXTURES / "strata_0_2_10_plan.py").read_text()
        constants = watch.literal_constants(current, watch.CONSTANTS)
        prior = watch.literal_constants(previous, watch.CONSTANTS)
        files = {"old:requirements.txt": fixture("previous_requirements.txt"),
                 "new:requirements.txt": fixture("requirements.txt"),
                 "old:requirements-monitor.txt": fixture("previous_requirements_monitor.txt"),
                 "new:requirements-monitor.txt": fixture("requirements_monitor.txt")}
        with patch.object(watch, "git", side_effect=lambda _, op, path: files[path]):
            return watch.dependency_review(None, "old", "new", constants, prior, new_lock=lock,
                                           source=current, prior_source=previous)

    def test_changed_pillow_needs_the_new_exact_lock(self):
        text = (REPO / self.LOCK).read_text()
        result = self.review((self.LOCK, text, "3.13"))
        self.assertEqual("new-lock", result["status"])
        self.assertEqual(["pillow 12.3.0 -> 13.0.0"], result["changed"])
        self.assertEqual(26, result["pins"])
        with self.assertRaisesRegex(watch.Incomplete, "requirements.txt changed"):
            self.review()

    def test_stale_pillow_or_extra_lock_pin_is_refused(self):
        text = (REPO / self.LOCK).read_text()
        previous = (REPO / "locks/strata-python-cp313-win_amd64-strata0.2.7.txt").read_text()
        for changed in (previous, text + f"extra==1 --hash=sha256:{'0' * 64}\n"):
            with self.subTest(lock=changed[-90:]), self.assertRaises(watch.Incomplete):
                self.review((self.LOCK, changed, "3.13"))


class Stock0211Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = fixture("server_engine_path.py")
        cls.sources = {path: fixture(Path(path).name) for path in (
            "strata_control/drafting.py", "strata_control/vram_fit.py", "strata_control/draft_layer.py",
            "serve/nonblocking_out.py", "strata_control/runtime.py", "strata_control/paths.py")}
        cls.modules = {path: watch.reviewed_hash(ast.parse(source)) for path, source in cls.sources.items()}

    def test_full_v0211_review_matches_uniquely(self):
        for groups in ((), tuple(watch.ENGINE_ENV_GROUPS)):
            self.assertEqual("0.2.11", watch.server_pinned_path_review(self.source, groups,
                                                                     module_digests=self.modules))

    def test_mixed_or_changed_modules_and_missing_sources_are_refused(self):
        old_drafting = watch.SERVER_REVIEWS["0.2.10"]["modules"]["drafting"]
        for modules in (self.modules | {old_drafting[0]: old_drafting[1]},
                        self.modules | {"strata_control/runtime.py": watch.reviewed_hash(ast.parse("changed = 1"))},
                        {path: digest for path, digest in self.modules.items() if path != "serve/nonblocking_out.py"}):
            with self.subTest(modules=modules), self.assertRaisesRegex(watch.Incomplete, "engine environment/argv path"):
                watch.server_pinned_path_review(self.source, (), module_digests=modules)

    def test_nodraft_retry_is_a_reviewed_root(self):
        tree = ast.parse(self.source)
        helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "nodraft_retry_args")
        helper.body.append(ast.Pass())
        with self.assertRaises(watch.Incomplete):
            watch.server_pinned_path_review(ast.unparse(ast.fix_missing_locations(tree)), (),
                                            module_digests=self.modules)

    def test_ambiguous_full_review_is_refused(self):
        with patch.dict(watch.SERVER_REVIEWS, {"duplicate": copy.deepcopy(watch.SERVER_REVIEWS["0.2.11"])}):
            with self.assertRaises(watch.Incomplete):
                watch.server_pinned_path_review(self.source, (), module_digests=self.modules)

    def test_source_review_binds_the_app_to_its_engine(self):
        with patch.object(watch, "git_blob", side_effect=lambda src, commit, path: self.sources.get(path)), \
                patch.object(watch, "git", return_value=self.source):
            self.assertEqual("0.2.11", watch.source_server_review(None, "pinned", "0.1.57", ()))
            with self.assertRaisesRegex(watch.Incomplete, "review 0.2.11 is for engine 0.1.57, not 0.1.56"):
                watch.source_server_review(None, "pinned", "0.1.56", ())


class Stock0211Sources(unittest.TestCase):
    def test_0157_runtime_identity_selects_all_nine_start_sources(self):
        profile = Profile(Path("fixture.json"), {"strata": {"engine_version": "0.1.57"}})
        sources = install.runtime_sources(profile)
        self.assertEqual(9, len(sources))
        self.assertEqual(("serve/nonblocking_out.py", "strata_control/sysinfo.py", "strata_control/targets.py",
                          "strata_control/runtime.py", "strata_control/paths.py"), sources[4:])

    def test_0156_source_selection_is_byte_identical(self):
        profile = Profile(Path("fixture.json"), {"strata": {"engine_version": "0.1.56"}})
        self.assertEqual(("serve/server.py", "strata_control/drafting.py",
                          "strata_control/vram_fit.py", "strata_control/draft_layer.py"),
                         install.runtime_sources(profile))


class Stock0211RuntimeBoundary(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.profile = Profile(Path("fixture.json"), {"strata": {"engine_version": "0.1.57"},
                                                     "server": {"api_key_env": "STRATA_API_KEY"}})
        self.layout = Layout(self.base / "integration", self.profile)

    def test_both_environments_replace_ambient_runtime_and_localappdata(self):
        ambient = {"STRATA_RUNTIME_DIR": str(self.base / "foreign-runtime"),
                   "LOCALAPPDATA": str(self.base / "foreign-localappdata")}
        with patch.dict(os.environ, ambient):
            server = lifecycle.server_env(self.layout, "fixture-key")
            build = install.build_env(self.layout, {"STRATA_RUNTIME_DIR": ambient["STRATA_RUNTIME_DIR"]})
        for env in (server, build):
            self.assertEqual(str((self.layout.state / "strata-runtime").resolve()), env["STRATA_RUNTIME_DIR"])
            self.assertTrue(Path(env["STRATA_RUNTIME_DIR"]).is_absolute())
            self.assertEqual(str((self.layout.root / "localappdata").resolve()), env["LOCALAPPDATA"])
            # Stock's separate procs writer uses state_base, not STRATA_RUNTIME_DIR.
            tree = ast.parse(fixture("paths.py"))
            helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "state_base")
            ns = {"Path": Path, "os": SimpleNamespace(environ=env, name="nt")}
            exec(compile(ast.Module(body=[helper], type_ignores=[]), "<stock-state-base>", "exec"), ns)
            self.assertEqual(self.layout.root.resolve() / "localappdata/Strata", ns["state_base"]())
        self.assertTrue((self.layout.state / "strata-runtime").is_dir())
        self.assertTrue((self.layout.root / "localappdata").is_dir())
        self.assertFalse((self.base / "foreign-runtime").exists())
        self.assertFalse((self.base / "foreign-localappdata").exists())

    def test_0156_environments_keep_the_qualified_boundary(self):
        self.profile.data["strata"]["engine_version"] = "0.1.56"
        ambient = {"STRATA_RUNTIME_DIR": str(self.base / "foreign-runtime"),
                   "LOCALAPPDATA": str(self.base / "foreign-localappdata")}
        with patch.dict(os.environ, ambient):
            environments = (lifecycle.server_env(self.layout, "fixture-key"), install.build_env(self.layout))
        for env in environments:
            self.assertNotIn("STRATA_RUNTIME_DIR", env)
            self.assertEqual(ambient["LOCALAPPDATA"], env["LOCALAPPDATA"])
        self.assertFalse((self.layout.state / "strata-runtime").exists())

    def test_doctor_reports_the_user_activity_lock_without_touching_it(self):
        from tests.unit.test_profile import single_gpu_data
        data = single_gpu_data()
        data["strata"]["engine_version"] = "0.1.57"
        layout = Layout(self.layout.root, Profile(Path("fixture.json"), data))
        user_local = self.base / "user-local"
        lock = user_local / "Strata/runtime/.activity.lock"
        lock.parent.mkdir(parents=True)
        lock.write_bytes(b"untouched user lease")
        with patch.dict(os.environ, {"LOCALAPPDATA": str(user_local)}), \
                patch.object(lifecycle, "WINDOWS", True), \
                patch.object(lifecycle, "host_platform", return_value="windows-x64"), \
                patch.object(lifecycle.procs, "memory", return_value={"total": 0, "available": 0}), \
                patch.object(lifecycle, "gpu_facts", return_value={"available": False}), \
                patch.object(lifecycle, "port_in_use", return_value=False), \
                patch.object(lifecycle.procs, "matches", return_value=None):
            checks = lifecycle.doctor(layout)["checks"]
        check = next(c for c in checks if c["check"] == "user_strata_runtime")
        self.assertFalse(check["blocking"])
        self.assertTrue(check["ok"])
        self.assertIn("left untouched", check["detail"])
        self.assertEqual(b"untouched user lease", lock.read_bytes())
