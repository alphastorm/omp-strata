"""Stock v0.2.11 admission boundaries; source-only, with no installer or GPU execution."""
from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

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
