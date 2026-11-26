"""Exercise reviewed Strata v0.2.22 plans and literal source contracts without stock imports."""
import ast
import json
import unittest

from omp_strata.profile import engine_env_group_values, start_path_sources
from scripts import upstream_watch as watch
from tests.unit.test_upstream_watch_0216 import FIXTURES, fixture


class StockPlan0222(unittest.TestCase):
    def plan(self, version="22", *, source=None, config=None, **options):
        return watch.stock_plan(
            fixture("plan.py", version) if source is None else source, **({
                "family": "coder", "model": "IQ1_M", "ram": 45, "vram": 31.8, "context": 131072,
                "engine_version": (0, 1, 69 if version == "22" else 62),
                "strata_tag": f"v0.2.{version}",
                "setup_config_source": fixture("setup_config.py", version) if config is None else config,
            } | options))

    def test_stock_projection_keeps_each_lanes_config_and_repins_only_coder(self):
        pro = dict(family="qwen", model="IQ3_S", context=262144, ram=192, vram=95.5,
                   parallel=4, cpu_cores=(8, 16), kv_streaming="off")
        inventory = json.loads((FIXTURES / "strata_0_1_42_gpu_inventory.json").read_text())
        pair = dict(family="qwen", model="IQ3_S", context=262144, ram=128, vram=None,
                    gpu_roles={0: "main", 1: "helper"}, layer_split="24", gpu_inventory=inventory)
        for lane, options in (("131K", {}), ("262K", {"context": 262144, "kv_streaming": "off"}),
                              ("PRO", pro), ("pair", pair)):
            with self.subTest(lane=lane):
                old, new = self.plan("16", **options), self.plan(**options)
                for field in ("setup_args", "config_keys", "expected_engine_flags", "model_files"):
                    self.assertEqual(old[field], new[field])
                self.assertFalse({"env", "drafting", "ui_budget_work_gib", "shape_title"} & set(new["config_keys"]))
                self.assertNotIn("--conversation-cache-mib", new["expected_engine_flags"])
                self.assertNotIn("--short-read", new["expected_engine_flags"])
                if new["setup_args"]["family"] == "coder":
                    self.assertNotEqual(old["model_url"], new["model_url"])
                    self.assertIn("/bba88856f8c3c0c9e40e45f82d05e228b814ac43/", new["model_url"])
                else:
                    self.assertEqual(old["model_url"], new["model_url"])

    def test_new_setup_review_still_refuses_drift_in_skipped_or_projected_code(self):
        source = fixture("plan.py", "22")
        for before, after, error in (
            ("canonical=q2_avx", "canonical=True", "staged-input path"),
            ("p.parent if p.is_file() else p", "p", "staged-input path"),
            ("return min(total, float(free))", "return float(free)", "effective_vram_gb"),
            ("cfg.pop(WORK_BUDGET_KEY, None)                 # a RAM budget",
             'cfg.pop("env", None)                 # a RAM budget', "carry_user_args"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(watch.Incomplete, error):
                self.plan(source=source.replace(before, after))
        with self.assertRaisesRegex(watch.Incomplete, "setup_config module"):
            self.plan(config=fixture("setup_config.py", "16"))


class Sm86Table0222(unittest.TestCase):
    cpp_path = "src/core/nv_defaults.cpp"
    hdr_path = "include/strata/core/nv_defaults.hpp"

    def review(self, *, source=None, header=None, vram=24 * 1024, version="22"):
        engine = "0.1.69" if version == "22" else "0.1.62"
        inputs = {self.cpp_path: fixture("nv_defaults.cpp", version) if source is None else source}
        if version == "22":
            inputs[self.hdr_path] = fixture("nv_defaults.hpp", "22") if header is None else header
        expected = engine_env_group_values(engine)["sm86_table"]
        watch._check_engine_env_table(f"0.2.{version}", "sm86_table", expected, inputs, vram)
        return watch.SM86_EXTRACTORS[f"0.2.{version}"](inputs[self.cpp_path], inputs.get(self.hdr_path, ""), vram)

    def test_projects_conditional_hit_switch_only_on_the_reviewed_revision(self):
        current = self.review()
        self.assertEqual(18, len(current))
        self.assertEqual("1", current["STRATA_VERIFY_DEVICE_HITS"])
        self.assertFalse({"STRATA_ADAPT_NOWAIT", "STRATA_ADAPT_FETCH"} & current.keys())
        self.assertEqual(8, len(self.review(version="16")))
        self.assertNotIn("STRATA_VERIFY_DEVICE_HITS", self.review(version="16"))
        source = fixture("nv_defaults.cpp", "22").replace("mj == 8", "mj\t== /* { ignored } */ 8", 1)
        self.assertEqual(current, self.review(source=source))

    def test_refuses_changed_literals_and_unreviewed_control_flow(self):
        source = fixture("nv_defaults.cpp", "22")
        for before, after in (
            ('{"STRATA_ADAPT_LAG", "2"}', '{"STRATA_ADAPT_LAG", "3"}'),
            ('{"STRATA_CPU_IQ_ALL_EXACT1", "1"}', '{"STRATA_ADAPT_NOWAIT", "1"}'),
            ('{"STRATA_CPU_IQ_ALL_EXACT1", "1"}', '{"STRATA_ADAPT_LAG", "2"}'),
            ("> kAdaptFetchMaxVramBytes", ">= kAdaptFetchMaxVramBytes"),
            ('"STRATA_VERIFY_DEVICE_HITS", "1"});', '"STRATA_VERIFY_DEVICE_HITS", "1"}); t.clear();'),
            ("return nv_default_env(major, minor, defaults026, 0);",
             "return nv_default_env(major, minor, defaults026, 24ull << 30);"),
            ("return vram_bytes <= kAdaptFetchLowVramBytes;", "return true;"),
            ("\n    return t;\n}", "\n    t.clear();\n    return t;\n}"),
        ):
            with self.subTest(change=before), self.assertRaises(watch.Incomplete):
                self.review(source=source.replace(before, after, 1))

    def test_refuses_the_exact_16_gib_boundary_or_a_changed_header(self):
        with self.assertRaisesRegex(watch.Incomplete, "over 16 GiB"):
            self.review(vram=16 * 1024)
        self.assertEqual(18, len(self.review(vram=16 * 1024 + 1)))
        header = fixture("nv_defaults.hpp", "22").replace("16ull << 30", "24ull << 30")
        with self.assertRaises(watch.Incomplete):
            self.review(header=header)


class StockStartReview0222(unittest.TestCase):
    def test_watch_and_installed_start_share_the_same_source_boundary(self):
        review = watch.SERVER_REVIEWS["0.2.22"]
        reviewed = {"serve/server.py", *review["sources"], *review["blobs"],
                    *(path for path, _ in review["modules"].values())}
        self.assertEqual({f"terminal/{path}" for path in reviewed}, set(start_path_sources("0.1.69")))

    def test_rejects_stock_start_constant_drift_even_with_a_reviewed_module(self):
        server = ("CONVERSATION_CACHE_MIN_TOKENS_DEFAULT = 1024\n"
                  "def child_env(cfg):\n"
                  "    if pw is not None and 'OMP_NUM_THREADS' not in env:\n"
                  "        env['OMP_NUM_THREADS'] = str(pw)\n")
        speed = 'ENGINE_START_DEFAULTS: dict[str, str] = {"STRATA_ROUTE_TAIL_SKIP": "0"}'
        cache = "ENGINE_AUTO_CAP_MIB = 8192\nCEILING_MIB = 131072\nSTEP_MIB = 256\nSHARE_OF_TOTAL = 0.25"

        def review(server=server, speed=speed, cache=cache):
            tree = ast.parse(server)
            watch._review_stock_start_constants(tree, tree.body[1], {
                "strata_control/speed_switches.py": ast.parse(speed),
                "strata_control/conversation_cache_size.py": ast.parse(cache),
            })

        review()
        for kwargs, error in (
            ({"speed": speed.replace('"0"', '"7"')}, "ENGINE_START_DEFAULTS"),
            ({"server": server.replace("1024", "512")}, "MIN_TOKENS_DEFAULT"),
            ({"server": server.replace("OMP_NUM_THREADS", "OTHER_NUM_THREADS")}, "pool-worker"),
            ({"cache": cache.replace("8192", "4096")}, "ENGINE_AUTO_CAP_MIB"),
            ({"cache": cache.replace("131072", "65536")}, "CEILING_MIB"),
            ({"cache": cache.replace("256", "512")}, "STEP_MIB"),
            ({"cache": cache.replace("0.25", "0.5")}, "SHARE_OF_TOTAL"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(watch.Incomplete, error):
                review(**kwargs)
