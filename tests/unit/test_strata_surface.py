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
from types import SimpleNamespace
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
    tree = ast.parse(source)
    assignments = {n.targets[0].id: n.value for n in tree.body if isinstance(n, ast.Assign)
                   and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
    found: dict[str, set[str]] = {}
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
        for name in [n for n in methods if n.startswith("do_")]:
            paths = found.setdefault(name[3:], set())
            pending, seen, aliases = [name], set(), {}
            while pending:
                node = methods[pending.pop()]
                if node.name in seen:
                    continue
                seen.add(node.name)
                paths.update(compared_paths(node))
                # v0.2.1 still accepts /v1/v1/messages through a literal alias map before POST dispatch.
                # Inventory aliases, never classify them as authenticated/safe just because the target is known.
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                            and isinstance(sub.targets[0], ast.Name) and sub.targets[0].id == "path"
                            and isinstance(sub.value, ast.Call) and isinstance(sub.value.func, ast.Attribute)
                            and sub.value.func.attr == "get" and isinstance(sub.value.func.value, ast.Name)
                            and [ast.dump(a) for a in sub.value.args] == [ast.dump(ast.Name(id="path", ctx=ast.Load()))] * 2):
                        mapping = ast.literal_eval(assignments[sub.value.func.value.id])
                        if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                               for k, v in mapping.items()):
                            raise ValueError("route alias map is not literal strings")
                        aliases.update(mapping)
                pending += [sub.func.attr for sub in ast.walk(node)
                            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "self"
                            and sub.func.attr in methods and not sub.func.attr.startswith("do_")]
            paths.update(alias for alias, target in aliases.items() if target in paths)
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
        cls.source = (Path(value) / "serve" / "server.py").read_text(encoding="utf-8")
        cls.routes = routes(cls.source)

    def test_g13_probes_every_get_route(self):
        served = {path or "/" for path in self.routes["GET"]}       # "/" is "" once the server strips the slash
        version = load_profile(PROFILE).data["strata"]["engine_version"]
        probed = {*gates.g13_protected_get(version), *gates.G13_PUBLIC_GET, *gates.G13_PUBLIC_STATIC, *gates.G13_ABSENT_GET}
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

    def test_stock_image_endpoints_return_404_without_an_image_configuration(self):
        tree = ast.parse(self.source)
        image = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_images"), None)
        if image is None:
            self.skipTest("stock releases before v0.1.44 have no image-generation handler")
        files = next(n for n in ast.walk(tree) if isinstance(n, ast.If) and isinstance(n.test, ast.Call)
                     and isinstance(n.test.func, ast.Attribute) and n.test.func.attr == "startswith"
                     and any(isinstance(a, ast.Constant) and a.value == "/v1/images/files/" for a in n.test.args))
        # Execute the source's unconfigured branches only: no Service constructor, IO, model or GPU runtime.
        file_handler = ast.FunctionDef(name="unconfigured_file", args=image.args, body=[files],
                                       decorator_list=[], returns=None, type_params=[])
        namespace = {"svc": SimpleNamespace(images=None), "path": "/v1/images/files/00000000000000000000000000000000.png"}
        module = ast.fix_missing_locations(ast.Module(body=[image, file_handler], type_ignores=[]))
        exec(compile(module, "<stock-unconfigured-images>", "exec"), namespace)
        responses = []
        handler = SimpleNamespace(_json=lambda status, body: responses.append((status, body)))
        namespace["_images"](handler, {})
        namespace["unconfigured_file"](handler, {})
        self.assertEqual([404, 404], [status for status, _ in responses])
        self.assertEqual("images_not_set_up", responses[0][1]["error"]["code"])


class RouteCensus(unittest.TestCase):
    def test_literal_aliases_remain_visible_without_classification(self):
        source = (
            "ALIASES = {'/v1/v1/messages': '/v1/messages', '/unused': '/absent'}\n"
            "class Handler:\n"
            "    def do_POST(self):\n"
            "        self._post()\n"
            "    def _post(self):\n"
            "        path = ALIASES.get(path, path)\n"
            "        if path == '/v1/messages':\n"
            "            self.send()\n")
        self.assertEqual({"POST": {"/v1/messages", "/v1/v1/messages"}}, routes(source))
        with self.assertRaises(ValueError):
            routes(source.replace("'/v1/messages', '/unused': '/absent'", "None, '/unused': '/absent'"))

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


class G13UnconfiguredImages(unittest.TestCase):
    def test_generation_keeps_the_existing_missing_and_wrong_key_matrix(self):
        requests = []
        def http(method, url, *, key=None, body=None):
            requests.append((method, url, key, body))
            return 401, {}
        with patch.object(gates, "http", side_effect=http):
            matrix = gates.g13_key_only_post("http://127.0.0.1:18090", "wrong-fixture")
        self.assertEqual({"none": 401, "wrong": 401}, matrix["POST /v1/images/generations"])
        self.assertEqual([None, "wrong-fixture"], [key for _, url, key, _ in requests if url.endswith("/v1/images/generations")])

    def test_absence_probes_use_a_file_endpoint_and_an_empty_authorized_post(self):
        requests = []
        def http(method, url, *, key=None, body=None):
            requests.append((method, url, key, body))
            return 404, {}
        with patch.object(gates, "http", side_effect=http):
            absent = gates.g13_absent_routes("http://127.0.0.1:18090", "correct-fixture")
        self.assertEqual(404, absent["/v1/images/files/"])
        self.assertEqual(404, absent["POST /v1/images/generations"])
        self.assertIn(("GET", "http://127.0.0.1:18090/v1/images/files/00000000000000000000000000000000.png",
                       "correct-fixture", None), requests)
        self.assertIn(("POST", "http://127.0.0.1:18090/v1/images/generations", "correct-fixture", {}), requests)


class G13VersionGate(unittest.TestCase):
    def test_a_new_get_route_is_probed_only_from_its_release(self):
        # An older server answers an unrouted GET with 404 before any key check, which G13 would score as unenforced.
        self.assertNotIn("/config", gates.g13_protected_get("0.1.38"))
        self.assertIn("/config", gates.g13_protected_get("0.1.39"))
        self.assertIn("/config", gates.g13_protected_get("0.1.40"))
        self.assertEqual(set(gates.G13_PROTECTED_GET) - {"/config", "/metrics/prometheus", "/v1/telemetry"},
                         set(gates.g13_protected_get("0.1.34")))

    def test_telemetry_get_is_protected_only_from_the_020_beta_engine(self):
        # v0.1.45 serves no /v1/telemetry; v0.2.0-beta (engine 0.1.45.3) and v0.2.1 (0.1.46) do.
        for version, probed in (("0.1.45", False), ("0.1.45.3", True), ("0.1.46", True)):
            with self.subTest(version=version):
                self.assertEqual(probed, "/v1/telemetry" in gates.g13_protected_get(version))

    def test_prometheus_get_is_protected_only_from_0142(self):
        previous = ("/v1/models", "/models", "/props", "/metrics", "/settings", "/slots", "/v1/status", "/status",
                    "/mcp", "/config")
        for version in ("0.1.40.3", "0.1.41"):
            self.assertEqual(gates.g13_protected_get(version), previous)
        for version in ("0.1.42", "0.1.43"):
            self.assertEqual(gates.g13_protected_get(version), previous + ("/metrics/prometheus",))

    def test_g13_probes_prometheus_with_the_existing_key_matrix(self):
        url = "http://127.0.0.1:18090"
        for version, expected in (("0.1.41", []), ("0.1.42", [None, "wrong-fixture", "wrong-fixture", "correct-fixture"])):
            with self.subTest(version=version):
                requests = []

                def http(method, target, *, key=None, x_api_key=False, **kwargs):
                    if method == "POST":
                        raise RuntimeError("GET probes complete")
                    if target == url + "/metrics/prometheus":
                        requests.append((key, x_api_key))
                    return (200 if key == "correct-fixture" else 401), {}

                layout = SimpleNamespace(profile=SimpleNamespace(data={"strata": {"engine_version": version}}))
                with patch.object(gates, "base", return_value=url), \
                     patch.object(gates.secrets, "token_urlsafe", return_value="fixture"), \
                     patch.object(gates, "http", side_effect=http):
                    with self.assertRaisesRegex(RuntimeError, "GET probes complete"):
                        gates.g13(layout, "correct-fixture", Path("evidence"))
                self.assertEqual([key for key, _ in requests], expected)
                if expected:
                    self.assertEqual([x_api_key for _, x_api_key in requests], [False, False, True, False])


if __name__ == "__main__":
    unittest.main()
