"""Stock v0.1.42 ordered_gpus prints a line for every order it changes and for the #1576 keep, so a complete startup
log with no such line means the configured order: parse_stage_order must recover exactly what stock staged."""
import contextlib
import ast
import io
import inspect
import itertools
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata.lifecycle import STAGE_ORDER_REVIEWED_ENGINES, parse_stage_order
from omp_strata.profile import load
from tests.fixtures import strata_0_1_42_ordered_gpus as stock
from tests.fixtures import strata_0_2_1_server as current
from tests.fixtures import strata_0_2_3_server_order as v023

PROFILES = Path(__file__).resolve().parents[2] / "profiles"


def staged_by_stock(cfg, scores, vrams):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        staged = stock.ordered_gpus(cfg, scores=scores, vrams=vrams)
    return staged, out.getvalue()


class StockOrderedGpusProof(unittest.TestCase):
    def test_v021_order_bodies_match_the_exhaustive_stock_proof(self):
        # Tag 90767252 app / engine 0.1.46: all three bodies are identical, not just the example pair's result.
        for name in ("gpu_list", "layer_split_value", "ordered_gpus"):
            with self.subTest(name=name):
                self.assertEqual(ast.dump(ast.parse(inspect.getsource(getattr(stock, name)))),
                                 ast.dump(ast.parse(inspect.getsource(getattr(current, name)))))
        self.assertIn("0.1.46", STAGE_ORDER_REVIEWED_ENGINES)

    def test_v021_native_start_keeps_gpu_mapping_auto_split_and_pipeline_flag(self):
        cfg = {"gpu": [0, 1], "layer_split": "auto",
               "args": ["--mtp", "pinned/mtp", "--spec", "4", "--spec-min-p", "0.5", "--pipeline-windows", "2"]}
        # No user_args, mtp=false, vision, offline or HIP opt-in in these profiles. Inject only measured-card seams.
        for vrams, expected in (({0: 24564, 1: 24576}, "0,1"), ({0: 24576, 1: 24576}, "1,0")):
            with self.subTest(vrams=vrams), \
                    patch.object(current, "gpu_speed_scores", return_value={0: 150, 1: 100}, create=True), \
                    patch.object(current, "gpu_vram_mib", return_value=vrams, create=True), \
                    patch.object(current, "draft_layer", SimpleNamespace(is_off=current.is_off), create=True), \
                    patch.dict(current.os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
                env = current.child_env(cfg)
                self.assertEqual(("PCI_BUS_ID", expected), (env["CUDA_DEVICE_ORDER"], env["CUDA_VISIBLE_DEVICES"]))
                self.assertEqual(cfg["args"] + ["--layer-split", "auto"], current.engine_args(cfg))

    def test_parser_recovers_every_stock_staging_decision(self):
        events = set()
        for configured in ([0, 1], [1, 0], [2, 0, 1]):
            n = len(configured)
            manual = ",".join(str(24 + 12 * i) for i in range(n - 1))
            variants = ({}, {"gpu_order": "as_given"}, {"layer_split": manual},
                        {"args": ["--layer-split", manual]}, {"args": ["--peer-device", "1"]})
            for speed in itertools.product((100, 104, 150), repeat=n):
                for vram in itertools.product((24564, 24576, 32768), repeat=n):
                    for extra in variants:
                        cfg = {"gpu": list(configured), "layer_split": "auto", **extra}
                        scores, vrams = dict(zip(configured, speed)), dict(zip(configured, vram))
                        staged, log = staged_by_stock(cfg, scores, vrams)
                        parsed = parse_stage_order(log, configured)
                        with self.subTest(cfg=cfg, scores=scores, vrams=vrams):
                            self.assertTrue(parsed["complete"], parsed)
                            self.assertEqual(staged, parsed["staged"])
                            if staged != configured:
                                self.assertEqual("reordered", parsed["event"])
                            elif log:
                                self.assertEqual("kept_1576", parsed["event"])
                            else:
                                self.assertEqual("kept_configured", parsed["event"])
                        events.add(parsed["event"])
        # The grid reaches every branch: a reorder, the #1576 keep, and the silent keeps (within 5%, opt-outs).
        self.assertEqual({"reordered", "kept_1576", "kept_configured"}, events)

    def test_unmeasured_cards_keep_the_configured_order_silently(self):
        staged, log = staged_by_stock({"gpu": [0, 1], "layer_split": "auto"}, {0: 150}, None)
        self.assertEqual(("", [0, 1]), (log, staged))
        self.assertEqual([0, 1], parse_stage_order(log, [0, 1])["staged"])

    def test_this_host_pair_is_reordered_only_when_the_4090_measures_faster(self):
        # Stock setup writes the 4090 first ([0, 1] here); auto staging moves the faster card last.
        staged, log = staged_by_stock({"gpu": [0, 1], "layer_split": "auto"}, {0: 150, 1: 100}, {0: 24564, 1: 24576})
        self.assertEqual([0, 1], staged)
        self.assertEqual("kept_1576", parse_stage_order(log, [0, 1])["event"])
        staged, log = staged_by_stock({"gpu": [0, 1], "layer_split": "auto"}, {0: 150, 1: 100}, {0: 24576, 1: 24576})
        self.assertEqual([1, 0], staged)
        self.assertEqual("reordered", parse_stage_order(log, [0, 1])["event"])

    def test_v023_pair_variants_stage_the_card_each_profile_pins_last(self):
        # This pair: the 4090 (card 0, SMs x clock 128 x 3105) reports 12 MiB less than the 3090 (card 1, 82 x 2115).
        scores, vrams = {0: 128 * 3105, 1: 82 * 2115}, {0: 24564, 1: 24576}
        variants = (
            ("stock default: #1576 keeps the 3090 last", {"gpu": [0, 1], "layer_split": "auto"}, [0, 1], "kept_1576"),
            ("--gpu-roles 0=main,1=helper: the 4090 last, never re-sorted",
             {"gpu": [1, 0], "layer_split": "auto", "gpu_order": "as_given", "gpu_roles": {"0": "main", "1": "helper"}},
             [1, 0], "kept_configured"),
            ("--layer-split 32: the configured order", {"gpu": [0, 1], "layer_split": "32"}, [0, 1], "kept_configured"))
        for name, cfg, configured, event in variants:
            with self.subTest(variant=name):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    staged = v023.ordered_gpus(cfg, scores=scores, vrams=vrams)
                parsed = parse_stage_order(out.getvalue(), configured)  # configured: the profile's host.gpus order
                self.assertEqual(configured, staged)
                self.assertEqual((True, event, staged), (parsed["complete"], parsed["event"], parsed["staged"]))
        # A hand-edited mirror ("gpu" no longer the roles' order) is stock's legacy rule again, not the roles.
        edited = {"gpu": [0, 1], "layer_split": "auto", "gpu_order": "as_given", "gpu_roles": {"0": "main", "1": "helper"}}
        self.assertFalse(v023.gpu_roles_active(edited))

    def test_every_multi_gpu_profile_runs_a_reviewed_stock_release(self):
        # An unreviewed release leaves every multi-GPU start degraded and every gate refuses it on the host
        # (0.1.43 pair, 2026-10-12): review its staging bodies and startup messages first, then admit it.
        for path in sorted(PROFILES.glob("*.json")):
            profile = load(path)
            if profile.multi_gpu:
                with self.subTest(profile=path.name):
                    version = str(profile.data["strata"]["engine_version"]).lstrip("v")
                    self.assertIn(version, STAGE_ORDER_REVIEWED_ENGINES)


if __name__ == "__main__":
    unittest.main()
