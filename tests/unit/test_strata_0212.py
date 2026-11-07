"""Stock v0.2.12 admission boundaries; source-only, without installer or GPU execution."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest

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
