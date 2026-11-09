"""Host-free v0.2.13 child_env proof against the checkout supplied by dev-env."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from omp_strata.profile import ENGINE_ENV_GROUPS


STOCK_COMMIT = "d2f096475817d4666c364c820b0ca830f751cfc5"
PROOF = r'''
import json
import os
import sys
from unittest.mock import patch

from serve import server

pinned = json.loads(sys.argv[1])
cfg = {"backend": "cuda", "args": [], "env": pinned}
with patch.dict(os.environ, {key: "ambient value" for key in pinned}, clear=True):
    actual = server.child_env(cfg)
print(json.dumps({key: actual[key] for key in pinned}))
'''


class StockEngineEnvProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_STRATA_SRC")
        if not value or not Path(value).is_dir():
            raise unittest.SkipTest("set OMP_STRATA_STRATA_SRC through dev-env to the pinned v0.2.13 checkout")
        cls.source = Path(value).resolve()
        cls.python = os.environ.get("OMP_STRATA_STRATA_PYTHON", sys.executable)
        result = subprocess.run(["git", "-C", str(cls.source), "rev-parse", "HEAD"], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise AssertionError("OMP_STRATA_STRATA_SRC is not a readable pinned checkout")
        if result.stdout.strip() != STOCK_COMMIT:
            raise unittest.SkipTest("this proof needs the v0.2.13 pin; dev-env selects its profile's commit")

    def test_candidate_groups_pass_through_stock_child_env_unchanged(self):
        for candidate in ({"STRATA_SPEC_COST": "1"}, {"STRATA_QSA_SPLIT_ATTN": "1"}):
            pinned = ENGINE_ENV_GROUPS["gdn_stack"] | candidate
            with self.subTest(candidate=candidate):
                result = subprocess.run([self.python, "-c", PROOF, json.dumps(pinned)], cwd=self.source,
                                        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(pinned, json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
