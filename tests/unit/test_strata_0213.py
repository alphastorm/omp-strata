"""Stock v0.2.13 admission boundaries; no installer, server or GPU execution."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from omp_strata import dflash2, engine_component
from omp_strata.profile import ENGINE_ENV_GROUPS, UNSLOTH_RESIDENT_SETUP_ENV, load, unsloth_resident_setup_env, validate
from scripts import upstream_watch as watch

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests/fixtures"


def fixture(name):
    return (FIXTURES / ("strata_0_2_13_" + name)).read_text()


class Stock0213Fixtures(unittest.TestCase):
    def test_source_payloads_match_their_recorded_digests(self):
        files = sorted(FIXTURES.glob("strata_0_2_13_*"))
        self.assertEqual(10, len(files))
        for path in files:
            with self.subTest(path=path.name):
                marker = b"// " if path.suffix == ".cpp" else b"# "
                header, payload = path.read_bytes().split(marker + b"Stock payload follows.\n", 1)
                hashes = dict(line.removeprefix(marker).split(b": ", 1) for line in header.splitlines()
                              if b" SHA-256: " in line)
                self.assertEqual(hashes[b"Payload SHA-256"].decode(), hashlib.sha256(payload).hexdigest())
                self.assertRegex(hashes[b"Source SHA-256"].decode(), r"^[0-9a-f]{64}$")
                if path.suffix == ".py":
                    ast.parse(payload)

    def test_runtime_requirements_and_packer_are_unchanged_from_v0212(self):
        for name in ("requirements.txt", "requirements_monitor.txt", "dflash2_pack.py"):
            previous = (FIXTURES / ("strata_0_2_12_" + name)).read_text()
            self.assertEqual(previous.split("# Stock payload follows.\n", 1)[1],
                             fixture(name).split("# Stock payload follows.\n", 1)[1])


class Stock0213Plan(unittest.TestCase):
    def plan(self, source=None, **options):
        return watch.stock_plan(fixture("plan.py") if source is None else source,
                                **({"family": "coder", "model": "IQ1_M", "context": 131072,
                                    "ram": 47.15475845336914, "vram": 31.8427734375,
                                    "engine_version": (0, 1, 59),
                                    "setup_config_source": fixture("setup_config.py")} | options))

    def test_current_lane_setup_outputs_match_v0212(self):
        from tests.unit.test_strata_0212 import Stock0212Plan
        previous = Stock0212Plan()
        inventory = json.loads((FIXTURES / "strata_0_1_42_gpu_inventory.json").read_text())
        pair = {"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 127.68849182128906,
                "vram": None, "gpu_inventory": inventory, "gpu_roles": {0: "main", 1: "helper"},
                "layer_split": "24"}
        pro = {"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 191.69942092895508,
               "vram": 95.5927734375, "parallel": 4, "cpu_cores": (8, 16),
               "kv_streaming": "off", "gpu_arch": "120"}
        for options in ({}, {"context": 262144, "kv_streaming": "off"}, pro, pair):
            with self.subTest(options=options):
                old, new = previous.plan(**options), self.plan(**options)
                for key in ("setup_args", "expected_engine_flags", "config_keys", "model_files", "model_url",
                            "host", "thresholds", "stock_tips", "stock_default_recommendation"):
                    self.assertEqual(old[key], new[key], key)
                self.assertNotIn("env", new["config_keys"])
                self.assertNotIn("shape_title", new["config_keys"])

    def test_missing_changed_or_mixed_seam_refuses(self):
        for config in (None, fixture("setup_config.py") + "\nchanged = True\n",
                       fixture("setup_config.py").replace("a = inp.a", "a = inp.chosen", 1)):
            with self.subTest(config=config is None), self.assertRaises(watch.Incomplete):
                self.plan(setup_config_source=config)
        with self.assertRaisesRegex(watch.Incomplete, "module or caller changed"):
            self.plan(fixture("plan.py").replace("a=a, adopted=adopted", "a=adopted, adopted=adopted", 1))

    def test_changed_feed_shape_and_write_guards_refuse(self):
        tree = ast.parse(fixture("plan.py"))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        shape = next(n for n in main.body if isinstance(n, ast.If)
                     and ast.unparse(n.test) == "fam.get('shape')")
        shape.test = ast.Constant(True)
        with self.assertRaises(watch.Incomplete):
            self.plan(ast.unparse(ast.fix_missing_locations(tree)))
        for before, after in (
            ('if not a.family and not a.yes and FEED_MODELS is None:',
             'if not a.family and FEED_MODELS is None:'),
            ('if fam.get("feed") and fam.get("drafter") == "none" and a.mtp is None:',
             'if fam.get("feed") and a.mtp is None:'),
            ('SHAPE_ENGINE: dict = {}', 'SHAPE_ENGINE: dict = {"shape": "q4_lite"}'),
            ('if SHAPE_ENGINE.get("title") and SHAPE_ENGINE.get("shape") and cfg.get("exe")',
             'if SHAPE_ENGINE.get("title") and cfg.get("exe")'),
        ):
            with self.subTest(before=before), self.assertRaises(watch.Incomplete):
                source = fixture("plan.py").replace(before, after, 1)
                self.assertNotEqual(fixture("plan.py"), source)
                self.plan(source)

    def test_neutral_profile_io_is_not_in_generic_vocabulary(self):
        with self.assertRaisesRegex(watch.Incomplete, "new call"):
            watch.pure_exec(ast.parse("neutral_profile_if_other_shape(1)").body, {})

    def test_unsloth_setup_env_tracks_engine_owned_hc_q8_without_admitting_budget_planning(self):
        namespace = {}
        watch.run_reviewed(ast.parse(fixture("plan.py")), ("unsloth_default_env",), namespace)
        for model in UNSLOTH_RESIDENT_SETUP_ENV:
            with self.subTest(model=model):
                self.assertEqual(UNSLOTH_RESIDENT_SETUP_ENV[model],
                                 unsloth_resident_setup_env(model, "0.1.58"))
                expected = namespace["unsloth_default_env"]("unsloth", model, False, False)
                self.assertEqual(expected, unsloth_resident_setup_env(model, "0.1.59"))
                self.assertNotIn("STRATA_HC_Q8", expected)
        with self.assertRaisesRegex(watch.Incomplete, "Unsloth budget planning is unreviewed"):
            self.plan(family="unsloth", model="UD-Q4_K_XL", context=262144, ram=192, vram=96,
                      parallel=4, cpu_cores=(8, 16))
