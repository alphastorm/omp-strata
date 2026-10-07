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
from unittest.mock import patch

from omp_strata.profile import load as load_profile
from scripts import realhost_gates as gates
from tests.candidate import PROFILE


def routes(source: str) -> dict[str, set[str]]:
    """HTTP method -> the path literals its `do_<METHOD>` handler compares `path` with (`==`, `in`, `startswith`),
    including the same-class methods the handler delegates to through `self.<name>(...)` (Strata v0.1.40.2 moved
    POST dispatch into `_post`, called from a `do_POST` that only catches malformed bodies).

    A prefix test joined with a request predicate (`path.startswith("/v1/") and self._foreign_page()`, Strata v0.1.38's
    cross-site guard, checked after authentication) rejects requests; it is a guard, not a route.
    """
    found: dict[str, set[str]] = {}
    for cls in (n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ClassDef)):
        methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
        for name in [n for n in methods if n.startswith("do_")]:
            paths = found.setdefault(name[3:], set())
            pending, seen = [name], set()
            while pending:
                node = methods[pending.pop()]
                if node.name in seen:
                    continue
                seen.add(node.name)
                paths.update(compared_paths(node))
                pending += [sub.func.attr for sub in ast.walk(node)
                            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "self"
                            and sub.func.attr in methods and not sub.func.attr.startswith("do_")]
    return found


def compared_paths(node: ast.FunctionDef) -> set[str]:
    paths = set()
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
    return paths


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

    def test_census_finds_every_route_g13_protects(self):
        # The two checks above pass on an empty census: v0.1.40.2 moved POST dispatch out of do_POST, and a census
        # that missed it found no POST route at all.
        version = load_profile(PROFILE).data["strata"]["engine_version"]
        self.assertLessEqual(set(gates.G13_PROTECTED_POST), self.routes["POST"])
        self.assertLessEqual(set(gates.g13_protected_get(version)), {path or "/" for path in self.routes["GET"]})


class RouteCensus(unittest.TestCase):
    def test_routes_follow_handler_delegation_within_the_class(self):
        source = (
            "class Handler:\n"
            "    def do_POST(self):\n"
            "        try:\n"
            "            self._post()\n"
            "        except ValueError:\n"
            "            self._json(400)\n"
            "    def _post(self):\n"
            "        if path == '/v1/chat/completions':\n"
            "            self._json(200)\n"
            "        elif path.startswith('/slots/'):\n"
            "            self._json(200)\n"
            "    def _json(self, status):\n"
            "        pass\n"
            "    def do_GET(self):\n"
            "        if path in ('/health', '/v1/models'):\n"
            "            self._json(200)\n")
        self.assertEqual({"POST": {"/v1/chat/completions", "/slots/"}, "GET": {"/health", "/v1/models"}},
                         routes(source))


class G13KeyOnlyPost(unittest.TestCase):
    def test_slot_controls_probe_only_missing_and_wrong_keys_and_keep_the_observed_status(self):
        url = "http://127.0.0.1:18090"
        wrong = "wrong-fixture"
        for wrong_status in (401, 200):
            with self.subTest(wrong_status=wrong_status):
                requests = []
                def http(method, target, *, key=None, body=None):
                    self.assertIn(key, (None, wrong))
                    requests.append((method, target, key, body))
                    return (wrong_status if target == url + "/slots/0" and key == wrong else 401), {}
                with patch.object(gates, "http", side_effect=http):
                    matrix = gates.g13_key_only_post(url, wrong)
                self.assertEqual({"none": 401, "wrong": wrong_status}, matrix["POST /slots/"])
                self.assertEqual([("POST", url + "/slots/0", None, {}), ("POST", url + "/slots/0", wrong, {})],
                                 [r for r in requests if r[1] == url + "/slots/0"])


class G13VersionGate(unittest.TestCase):
    def test_a_new_get_route_is_probed_only_from_its_release(self):
        # An older server answers an unrouted GET with 404 before any key check, which G13 would score as unenforced.
        self.assertNotIn("/config", gates.g13_protected_get("0.1.38"))
        self.assertIn("/config", gates.g13_protected_get("0.1.39"))
        self.assertIn("/config", gates.g13_protected_get("0.1.40"))
        self.assertEqual(set(gates.G13_PROTECTED_GET) - {"/config"}, set(gates.g13_protected_get("0.1.34")))


if __name__ == "__main__":
    unittest.main()
