"""Stock v0.1.42 ordered_gpus prints a line for every order it changes and for the #1576 keep, so a complete startup
log with no such line means the configured order: parse_stage_order must recover exactly what stock staged."""
import contextlib
import io
import itertools
from pathlib import Path
import unittest

from omp_strata.lifecycle import STAGE_ORDER_REVIEWED_ENGINES, parse_stage_order
from omp_strata.profile import load
from tests.fixtures import strata_0_1_42_ordered_gpus as stock

PROFILES = Path(__file__).resolve().parents[2] / "profiles"


def staged_by_stock(cfg, scores, vrams):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        staged = stock.ordered_gpus(cfg, scores=scores, vrams=vrams)
    return staged, out.getvalue()


class StockOrderedGpusProof(unittest.TestCase):
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
