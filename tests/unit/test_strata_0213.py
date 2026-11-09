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
from omp_strata.profile import ENGINE_ENV_GROUPS, load, validate
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
