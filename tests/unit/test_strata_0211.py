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
