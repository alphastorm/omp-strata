"""G13 probes every route the pinned stock server answers (its serve/server.py, read with `ast`).

A Strata release that adds a route fails here, host-free, until G13 classifies it: protected (probed with every key),
key-only (controls; missing and wrong keys only), public, public static files, or absent (opt-in features install
rejects). Without `OMP_STRATA_STRATA_SRC` (set by `dev-env`) the check skips, like the composed frontend tests.
"""

from __future__ import annotations

import ast
import os
import subprocess
import unittest
from pathlib import Path

from omp_strata.profile import load as load_profile
from scripts import realhost_gates as gates
from tests.candidate import PROFILE


def routes(source: str) -> dict[str, set[str]]:
    """HTTP method -> the path literals its `do_<METHOD>` handler compares `path` with (`==`, `in`, `startswith`).

    A prefix test joined with a request predicate (`path.startswith("/v1/") and self._foreign_page()`, Strata v0.1.38's
    cross-site guard, checked after authentication) rejects requests; it is a guard, not a route.
    """
    found: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("do_")):
            continue
        paths = found.setdefault(node.name[3:], set())
        guards = {id(value) for sub in ast.walk(node) if isinstance(sub, ast.BoolOp) and isinstance(sub.op, ast.And)
                  and any(isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                          and isinstance(v.func.value, ast.Name) and v.func.value.id == "self" for v in sub.values)
                  for value in sub.values}
        for sub in ast.walk(node):
            if isinstance(sub, ast.Compare) and isinstance(sub.left, ast.Name) and sub.left.id == "path":
                for comparator in sub.comparators:
                    values = comparator.elts if isinstance(comparator, ast.Tuple) else [comparator]
                    paths.update(v.value for v in values if isinstance(v, ast.Constant) and isinstance(v.value, str))
            elif (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "startswith"
                  and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "path" and id(sub) not in guards):
                paths.update(a.value for a in sub.args if isinstance(a, ast.Constant) and isinstance(a.value, str))
    return found


class StrataSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_STRATA_SRC")
        if not value or not Path(value).is_dir():
            raise unittest.SkipTest("set OMP_STRATA_STRATA_SRC to the pinned Strata source checkout")
        result = subprocess.run(["git", "-C", value, "rev-parse", "HEAD"], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)
        if result.returncode or result.stdout.strip() != load_profile(PROFILE).data["strata"]["commit"]:
            raise AssertionError("OMP_STRATA_STRATA_SRC is not the profile's pinned commit")
        cls.routes = routes((Path(value) / "serve" / "server.py").read_text(encoding="utf-8"))

    def test_g13_probes_every_get_route(self):
        served = {path or "/" for path in self.routes["GET"]}       # "/" is "" once the server strips the slash
        probed = {*gates.G13_PROTECTED_GET, *gates.G13_PUBLIC_GET, *gates.G13_PUBLIC_STATIC, *gates.G13_ABSENT_GET}
        self.assertEqual([], sorted(served - probed))

    def test_g13_probes_every_post_route(self):
        probed = {*gates.G13_PROTECTED_POST, *gates.G13_KEY_ONLY_POST}
        self.assertEqual([], sorted(self.routes["POST"] - probed))

    def test_g13_covers_every_method(self):
        # GET and POST are inventoried above; OPTIONS (v0.1.32+, every path, no key) is G13's CORS preflight
        self.assertLessEqual(set(self.routes), {"GET", "POST", "OPTIONS"})


if __name__ == "__main__":
    unittest.main()
