"""Stock v0.2.12 admission boundaries; source-only, without installer or GPU execution."""
from __future__ import annotations

import ast
import hashlib
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
