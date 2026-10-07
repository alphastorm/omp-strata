"""Comparison route isolation, immutable pins and authenticated identity refusals."""
from __future__ import annotations

import copy
import json
import os
import secrets
import sys
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from omp_strata.common import canonical_json, record_verified, sha256_bytes, sha256_file
from omp_strata.comparison import ComparisonError, ComparisonPlan
from omp_strata.comparison_ompcfg import NInferArm, StrataArm
from omp_strata.install import runtime_identity
from omp_strata.layout import Layout, host_platform
from omp_strata.ompcfg import CHAT_ROLES, DISCOVERY_OFF, OMP_PROFILE, inflight_limit
from omp_strata.profile import Profile, load
from tests.candidate import PROFILE
from tests.mock.responses_server import ResponsesServer
from tests.mock.scripted_server import ScriptedServer


def comparison_fixture(root: Path, *, binary: Path | None = None, lane="rtx4090-native"):
    """Private synthetic installation bindings, with real profile pins for real OMP."""
    profile = load(PROFILE)
    data = copy.deepcopy(profile.data)
    if binary is None:
        binary = root / "stock-omp-fixture"
        binary.write_bytes(b"not executed: stock-client-pin-fixture")
        data["omp"]["artifacts"][host_platform()].update(bytes=binary.stat().st_size,
                                                        sha256=sha256_bytes(binary.read_bytes()))
    # Small synthetic engine/model bytes exercise installed-identity checking,
    # never claim a stock engine or GGUF. The real OMP artifact pin is unchanged.
    for entry in data["model"]["files"]:
        payload = ("synthetic model " + entry["path"]).encode()
        entry.update(bytes=len(payload), sha256=sha256_bytes(payload))
    profile_path = root / "profile.json"
    profile_path.write_text(json.dumps(data), encoding="utf-8")
    profile = Profile(profile_path, data)
    provider, model = {"rtx3090-native": ("ninfer-native-3090", "q38-ninfer"),
                       "rtx4090-native": ("ninfer-native-4090", "qwen3.8-27b"),
                       "rtx5090-docker-local": ("ninfer-beta", "q38-ninfer")}[lane]
    artifact = profile.omp_artifact(host_platform())
    plan = {
        "omp": {"platform": host_platform(), "version": profile.data["omp"]["version"],
                "bytes": artifact["bytes"], "sha256": artifact["sha256"]},
        "strata": {"profile_id": profile.id, "profile_fingerprint": profile.fingerprint,
                   "model_id": profile.data["strata"]["model_name"], "api": "openai-completions", "provider": "strata-local"},
        "ninfer": {"lane": lane, "model_id": model,
                   "api": "openai-responses", "provider": provider, "release_id": "native-fixture-release",
                   "runtime_identity_sha256": "1" * 64, "config_identity_sha256": "2" * 64,
                   "model_identity_sha256": "3" * 64},
    }
    bindings = {"comparison_root": str(root / "comparison"), "omp_binary": str(binary)}
    keys = {}
    for arm in ("strata", "ninfer"):
        installed = root / (arm + "-installation")
        installed.mkdir()
        key_file = installed / "key"
        keys[arm] = secrets.token_urlsafe(32)
        key_file.write_text(keys[arm], encoding="ascii")
        key_file.chmod(0o600)
        bindings[arm] = {"root": str(installed), "key_file": str(key_file), "port": 18082}
    bindings["strata"]["profile"] = str(profile.path)
    layout = Layout(Path(bindings["strata"]["root"]), profile)
    for entry in profile.data["model"]["files"]:
        path = layout.model_file(entry)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("synthetic model " + entry["path"]).encode())
        record_verified(path, entry["bytes"], entry["sha256"], "synthetic fixture")
    engine = layout.strata / "engine" / ("strata.exe" if os.name == "nt" else "strata")
    engine.parent.mkdir(parents=True)
    engine.write_bytes(b"synthetic engine, never executed")
    for directory in (layout.data / "pack", layout.data / "mtp"):
        directory.mkdir(parents=True)
        (directory / "fixture.bin").write_bytes(b"synthetic runtime input")
    shard = str(layout.model_file(profile.data["model"]["files"][0]))
    cfg = {"model_name": profile.data["strata"]["model_name"], "host": "127.0.0.1", "exe": str(engine),
           "args": [*profile.data["strata"]["expected_engine_flags"], "--pack", str(layout.data / "pack"),
                    "--mtp", str(layout.data / "mtp"), "--native", shard, "--ple-gguf", shard,
                    "--expert-profile", str(layout.strata / "data" / "fixture.json")]}
    if profile.data["strata"]["setup_args"].get("parallel"):  # stock setup --parallel N writes its batch slots
        cfg["parallel"] = profile.data["strata"]["setup_args"]["parallel"]
    layout.strata_config.write_text(json.dumps(cfg), encoding="utf-8")
    layout.shared_settings.write_text("{}\n", encoding="utf-8")
    identity = runtime_identity(layout, cfg)
    runtime_hash = sha256_bytes(canonical_json(identity))
    layout.state.mkdir()
    layout.install_record.write_text(json.dumps({"profile_fingerprint": profile.fingerprint, "identity": identity,
                                                "runtime_identity_sha256": runtime_hash}), encoding="utf-8")
    plan["strata"].update(runtime_identity_sha256=runtime_hash,
                          model_identity_sha256=sha256_bytes(canonical_json(profile.data["model"])))
    manifests = {
        "strata": {"profile": {"fingerprint": profile.fingerprint}, "install": {"runtime_identity_sha256": runtime_hash}},
        "ninfer": {"components": {"ninfer_variants": [{
            "id": lane.replace("-native", "-windows-native"),
            "server_binary_sha256": plan["ninfer"]["runtime_identity_sha256"],
            "configuration_sha256": plan["ninfer"]["config_identity_sha256"],
            "model_artifact_sha256": plan["ninfer"]["model_identity_sha256"],
        }]}},
    }
    if lane == "rtx5090-docker-local":
        plan["ninfer"]["image_digest"] = "sha256:" + "4" * 64
        manifests["ninfer"] = {
            "release": plan["ninfer"]["release_id"],
            "components": {"ninfer": {"oci_manifest_digest": plan["ninfer"]["image_digest"],
                                      "server_binary_sha256": plan["ninfer"]["runtime_identity_sha256"]},
                           "model": {"artifact_sha256": plan["ninfer"]["model_identity_sha256"]}},
            "runtime_identity": {"public_model_id": model, "deployment_profile": "synthetic-docker-profile",
                                 "configuration_sha256": plan["ninfer"]["config_identity_sha256"]},
        }
    for arm, document in manifests.items():
        path = root / (arm + "-manifest.json")
        path.write_bytes(canonical_json(document))
        bindings[arm]["manifest"] = str(path)
        plan[arm]["release_manifest_sha256" if arm == "strata" else "manifest_sha256"] = sha256_file(path)
    status = {"endpoint_state": "ready", **{
        name: plan["ninfer"][name] for name in ("release_id", "runtime_identity_sha256", "config_identity_sha256", "model_identity_sha256")
    }}
    if lane == "rtx5090-docker-local":
        status.update(running=True, image_digest=plan["ninfer"]["image_digest"], container_id="5" * 64,
                      started_at="2020-01-01T00:00:00Z", deployment_profile="synthetic-docker-profile",
                      publications=[{"host_ip": "0.0.0.0", "host_port": bindings["ninfer"]["port"],
                                     "container_port": 8080, "protocol": "tcp"}])
        status_file = root / "docker-probe-output.json"
        script = root / "docker-probe.py"
        script.write_text("import json, sys\nfrom datetime import datetime, timezone\nfrom pathlib import Path\n"
                          "status = json.loads(Path(sys.argv[1]).read_text())\n"
                          "status.setdefault('observed_at', datetime.now(timezone.utc).isoformat())\n"
                          "print(json.dumps(status))\n", encoding="utf-8")
        bindings["ninfer"]["docker_identity_probe_argv"] = [sys.executable, str(script), str(status_file)]
    else:
        status_file = root / "native-status.json"
        bindings["ninfer"]["status_file"] = str(status_file)
    status_file.write_text(json.dumps(status), encoding="utf-8")
    return plan, bindings, keys


def native_identity(plan):
    native = plan["ninfer"]
    return {"binary_sha256": native["runtime_identity_sha256"], "config_sha256": native["config_identity_sha256"],
            "model_artifact_sha256": native["model_identity_sha256"], "source_dirty": False,
            **({"deployment_profile": "synthetic-docker-profile", "model_id": "qwen3.8-27b"}
               if native["lane"] == "rtx5090-docker-local" else {})}


class ComparisonConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="g25-adapter-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.plan, self.bindings, self.keys = comparison_fixture(self.root)
        self.comparison = Path(self.bindings["comparison_root"])

    def arm(self, arm, **kwargs):
        return {"strata": StrataArm, "ninfer": NInferArm}[arm](self.plan, self.bindings, **kwargs)

    def documents(self, launch):
        directory = launch.home / ".omp" / "profiles" / OMP_PROFILE / "agent"
        return tuple(json.loads((directory / (name + ".yml")).read_text(encoding="utf-8")) for name in ("config", "models"))

    def test_each_arm_attempt_has_a_fresh_home_and_no_installation_writes(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        homes = []
        for arm in ("strata", "ninfer"):
            for attempt in (1, 2):
                launch = self.arm(arm).prepare(self.comparison / arm / str(attempt))
                homes.append(launch.home)
                self.assertTrue(launch.home.is_relative_to(self.comparison))
                self.assertEqual(Path(launch.env["HOME"]), launch.home)
                self.assertEqual(launch.argv[0], self.bindings["omp_binary"])
                config, models = self.documents(launch)
                route = self.plan[arm]["provider"] + "/" + self.plan[arm]["model_id"]
                self.assertEqual(config["modelRoles"], dict.fromkeys(CHAT_ROLES, route))
                self.assertEqual(list(models["providers"]), [self.plan[arm]["provider"]])
                self.assertFalse(config["retry"]["enabled"])
                self.assertFalse(config["retry"]["modelFallback"])
                self.assertTrue(all(flag in launch.argv for flag in DISCOVERY_OFF))
                slots = inflight_limit(self.arm(arm).profile) if arm == "strata" else 1  # NInfer: one sequence
                self.assertEqual(config["providers"]["maxInFlightRequests"], {self.plan[arm]["provider"]: slots})
        self.assertEqual(len(set(homes)), 4)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertTrue(all(path in before or path.is_relative_to(self.comparison)
                            for path in self.root.rglob("*") if path.is_file()))
        with self.assertRaisesRegex(ComparisonError, "fresh"):
            self.arm("ninfer").prepare(self.comparison / "ninfer" / "1")

    def test_native_model_ids_and_capabilities_follow_each_documented_lane(self):
        for lane, provider, model in (("rtx3090-native", "ninfer-native-3090", "q38-ninfer"),
                                      ("rtx4090-native", "ninfer-native-4090", "qwen3.8-27b")):
            self.plan["ninfer"].update(lane=lane, provider=provider, model_id=model)
            launch = self.arm("ninfer").prepare(self.comparison / lane)
            _, models = self.documents(launch)
            config = models["providers"][provider]
            declared, = config["models"]
            self.assertEqual((config["api"], config["apiKey"], config["authHeader"]),
                             ("openai-responses", "NINFER_NATIVE_API_KEY", True))
            self.assertEqual((declared["id"], declared["input"], declared["supportsTools"]), (model, ["text"], True))
            self.assertEqual(declared["compat"], {"includeEncryptedReasoning": False, "supportsReasoningSummary": False})
            self.assertEqual(config["baseUrl"], "http://127.0.0.1:18082/v1")
            self.assertEqual(launch.env["PI_OPENAI_STATEFUL"], "1")
        for field, value in (("lane", "rtx5090-native"), ("model_id", "other"), ("provider", "cloud"), ("api", "openai-completions")):
            saved = self.plan["ninfer"][field]
            self.plan["ninfer"][field] = value
            with self.subTest(field=field), self.assertRaises(ComparisonError):
                self.arm("ninfer")
            self.plan["ninfer"][field] = saved

    def test_loaded_immutable_plan_prepares_without_mutating_pins(self):
        frozen = ComparisonPlan(MappingProxyType({name: MappingProxyType(value) for name, value in self.plan.items()}), "0" * 64)
        for cls in (StrataArm, NInferArm):
            launch = cls(frozen, self.bindings).prepare(self.comparison / cls.arm)
            self.assertEqual(launch.endpoint["model"], frozen[cls.arm]["model_id"])
        self.assertEqual(frozen.as_dict(), self.plan)

    def test_environment_allowlist_scrubs_provider_keys_and_model_overrides(self):
        hostile = {name: "must-not-leak" for name in (
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "STRATA_API_KEY", "NINFER_NATIVE_API_KEY", "PI_MODEL", "PI_SMOL_MODEL",
            "PI_OPENAI_STATEFUL", "PI_CONFIG", "OMP_PROFILE", "NODE_OPTIONS", "BASH_ENV", "SSH_AUTH_SOCK", "LC_AUTH_TOKEN")}
        hostile.update(PATH="fixture-bin", LANG="C.UTF-8", LC_ALL="C.UTF-8")
        for arm in ("strata", "ninfer"):
            launch = self.arm(arm, base_env=hostile).prepare(self.comparison / arm)
            self.assertEqual(launch.env["PATH"], "fixture-bin")
            self.assertEqual(launch.env["LC_ALL"], "C.UTF-8")
            allowed = {"STRATA_API_KEY"} if arm == "strata" else {"NINFER_NATIVE_API_KEY", "PI_OPENAI_STATEFUL"}
            self.assertTrue(set(hostile).intersection(launch.env) <= allowed | {"PATH", "LANG", "LC_ALL"})
            self.assertNotIn("must-not-leak", launch.env.values())
            self.assertEqual(launch.env["STRATA_API_KEY" if arm == "strata" else "NINFER_NATIVE_API_KEY"], self.keys[arm])
            public = json.dumps([launch.argv, launch.endpoint, *self.documents(launch)])
            self.assertNotIn(self.keys[arm], public)

    def test_missing_blank_unsafe_keys_refused_before_writes(self):
        for arm in ("strata", "ninfer"):
            path = Path(self.bindings[arm]["key_file"])
            for key in ("", " \n\t", "short", "a" * 32 + "\ninjected"):
                path.write_text(key, encoding="ascii")
                with self.subTest(arm=arm, key=repr(key)), self.assertRaisesRegex(ComparisonError, "key"):
                    self.arm(arm).prepare(self.comparison / arm)
                self.assertFalse(self.comparison.exists())
            path.unlink()
            with self.assertRaisesRegex(ComparisonError, "key"):
                self.arm(arm).preflight()
            path.write_text(self.keys[arm], encoding="ascii")
            path.chmod(0o600)
            if os.name != "nt":
                path.chmod(0o644)
                with self.assertRaisesRegex(ComparisonError, "user-only"):
                    self.arm(arm).prepare(self.comparison / arm)
                path.chmod(0o600)
        self.assertFalse(self.comparison.exists())

    def test_same_pin_is_required_for_both_arms_and_rehashed_on_each_attempt(self):
        for arm in ("strata", "ninfer"):
            bad = copy.deepcopy(self.plan)
            bad["omp"]["sha256"] = "f" * 64
            with self.subTest(arm=arm), self.assertRaisesRegex(ComparisonError, "same.*pin"):
                {"strata": StrataArm, "ninfer": NInferArm}[arm](bad, self.bindings).prepare(self.comparison / arm)
        binary = Path(self.bindings["omp_binary"])
        self.arm("strata").prepare(self.comparison / "first")
        binary.write_bytes(b"x" * binary.stat().st_size)
        with self.assertRaisesRegex(ComparisonError, "SHA-256"):
            self.arm("ninfer").prepare(self.comparison / "second")
        binary.write_bytes(b"short")
        with self.assertRaisesRegex(ComparisonError, "size"):
            self.arm("strata").prepare(self.comparison / "third")
        self.assertFalse((self.comparison / "second").exists())
        self.assertFalse((self.comparison / "third").exists())

    def test_existing_launcher_override_refusals_apply_to_both_arms(self):
        for arm in ("strata", "ninfer"):
            for flag in ("--model", "--models", "--profile", "--provider", "--api-key", "--base-url", "--config",
                         "--config-dir", "--models-file", "--smol", "--slow", "--plan", "--extensions", "--skills", "-e"):
                for extra in ((flag, "other"), (flag + "=other",)):
                    with self.subTest(arm=arm, extra=extra), self.assertRaises(ComparisonError):
                        self.arm(arm, extra=extra).prepare(self.comparison / arm)
        self.assertFalse(self.comparison.exists())

    def test_writes_cannot_escape_the_comparison_root(self):
        for arm in ("strata", "ninfer"):
            adapter = self.arm(arm)
            for path in (self.comparison, self.root / "outside", self.comparison / ".." / "outside"):
                with self.subTest(arm=arm, path=path.name), self.assertRaises(ComparisonError):
                    adapter.prepare(path)
        self.comparison.mkdir()
        (self.comparison / "linked").symlink_to(Path(self.bindings["ninfer"]["root"]), target_is_directory=True)
        with self.assertRaises(ComparisonError):
            self.arm("ninfer").prepare(self.comparison / "linked" / "attempt")
        bad = copy.deepcopy(self.bindings)
        bad["comparison_root"] = str(Path(bad["ninfer"]["root"]) / "work")
        with self.assertRaisesRegex(ComparisonError, "separate"):
            NInferArm(self.plan, bad)
        for port in (0, 65536, True, "http://example.com/v1"):
            self.bindings["ninfer"]["port"] = port
            with self.assertRaises(ComparisonError):
                self.arm("ninfer")

    def test_strata_preflight_authenticates_model_build_and_context(self):
        profile = load(Path(self.bindings["strata"]["profile"]))
        for changes, good in (({}, True), ({"model": "wrong"}, False), ({"engine_version": "0.0.0"}, False),
                              ({"context": 8192}, False), ({"api_key": "wrong" * 8}, False)):
            args = {"model": self.plan["strata"]["model_id"], "api_key": self.keys["strata"],
                    "engine_version": profile.data["strata"]["engine_version"],
                    "context": profile.data["strata"]["setup_args"]["context"], **changes}
            server = ScriptedServer([], **args)
            self.addCleanup(server.close)
            self.bindings["strata"]["port"] = server.httpd.server_port
            with self.subTest(changes=tuple(changes)):
                if good:
                    self.assertEqual(self.arm("strata").preflight()["context"], args["context"])
                else:
                    with self.assertRaises(ComparisonError):
                        self.arm("strata").preflight()
        self.assertFalse(self.comparison.exists())

    def test_strata_installed_pins_and_changed_bytes_refuse_before_http(self):
        with patch("omp_strata.comparison_ompcfg._http_json", side_effect=AssertionError("identity drift reached HTTP")):
            for field in ("runtime_identity_sha256", "model_identity_sha256", "release_manifest_sha256"):
                saved = self.plan["strata"][field]
                self.plan["strata"][field] = "f" * 64
                with self.subTest(field=field), self.assertRaises(ComparisonError):
                    self.arm("strata").preflight()
                self.plan["strata"][field] = saved
            layout = Layout(Path(self.bindings["strata"]["root"]), load(Path(self.bindings["strata"]["profile"])))
            model = layout.model_file(layout.profile.data["model"]["files"][0])
            model.write_bytes(b"changed model bytes")
            with self.assertRaisesRegex(ComparisonError, "installed"):
                self.arm("strata").preflight()
        self.assertFalse(self.comparison.exists())

    def test_native_manifest_changed_bytes_and_wrong_lane_refuse_before_http(self):
        path = Path(self.bindings["ninfer"]["manifest"])
        document = json.loads(path.read_bytes())
        with patch("omp_strata.comparison_ompcfg._http_json", side_effect=AssertionError("manifest drift reached HTTP")):
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ComparisonError, "pinned bytes"):
                self.arm("ninfer").preflight()
            document["components"]["ninfer_variants"][0]["id"] = "rtx3090-windows-native"
            path.write_bytes(canonical_json(document))
            self.plan["ninfer"]["manifest_sha256"] = sha256_file(path)
            with self.assertRaisesRegex(ComparisonError, "selected native"):
                self.arm("ninfer").preflight()
        self.assertFalse(self.comparison.exists())

    def test_ninfer_preflight_refuses_stale_status_and_authenticated_runtime_drift(self):
        server = ResponsesServer([], model=self.plan["ninfer"]["model_id"], api_key=self.keys["ninfer"],
                                 identity=native_identity(self.plan))
        self.addCleanup(server.close)
        self.bindings["ninfer"]["port"] = server.httpd.server_port
        result = self.arm("ninfer").preflight()
        self.assertEqual(result["runtime_identity_sha256"], self.plan["ninfer"]["runtime_identity_sha256"])
        server.identity["binary_sha256"] = "f" * 64
        with self.assertRaisesRegex(ComparisonError, "served"):
            self.arm("ninfer").preflight()
        status = Path(self.bindings["ninfer"]["status_file"])
        status.write_text(json.dumps({"endpoint_state": "ready"}), encoding="utf-8")
        with self.assertRaisesRegex(ComparisonError, "absent, unresolved"):
            self.arm("ninfer").preflight()
        status.unlink()
        with self.assertRaisesRegex(ComparisonError, "Status capture"):
            self.arm("ninfer").preflight()
        self.assertNotIn(self.keys["ninfer"], json.dumps(result))
        self.assertFalse(self.comparison.exists())


class DockerComparisonConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="g25-docker-adapter-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.plan, self.bindings, self.keys = comparison_fixture(self.root, lane="rtx5090-docker-local")
        self.server = ResponsesServer([], model="q38-ninfer", api_key=self.keys["ninfer"],
                                      identity=native_identity(self.plan))
        self.addCleanup(self.server.close)
        self.bindings["ninfer"]["port"] = self.server.httpd.server_port
        self.probe_path = Path(self.bindings["ninfer"]["docker_identity_probe_argv"][-1])
        self.probe = json.loads(self.probe_path.read_text())
        self.probe["publications"][0]["host_port"] = self.server.httpd.server_port
        self.write_probe(self.probe)

    def write_probe(self, value):
        self.probe_path.write_text(json.dumps(value), encoding="utf-8")

    def arm(self):
        return NInferArm(self.plan, self.bindings)

    def test_docker_preflight_and_isolated_documented_route(self):
        result = self.arm().preflight()
        self.assertEqual(result["image_digest"], self.plan["ninfer"]["image_digest"])
        self.assertEqual(result["publications"], [{"address_scope": "ipv4-wildcard", "container_port": 8080,
                                                "host_port": self.server.httpd.server_port, "protocol": "tcp"}])
        from omp_strata.comparison import _public_errors
        self.assertEqual(_public_errors(result), [])
        self.assertEqual(result["internal_model_id"], "qwen3.8-27b")
        self.assertEqual(result["model"], "q38-ninfer")
        launch = self.arm().prepare(Path(self.bindings["comparison_root"]) / "docker-attempt")
        directory = launch.home / ".omp" / "profiles" / OMP_PROFILE / "agent"
        models = json.loads((directory / "models.yml").read_text())
        config = json.loads((directory / "config.yml").read_text())
        provider = models["providers"]["ninfer-beta"]
        self.assertEqual(provider["api"], "openai-responses")
        self.assertEqual(provider["apiKey"], "NINFER_BETA_API_KEY")
        self.assertEqual(provider["baseUrl"], f"http://127.0.0.1:{self.server.httpd.server_port}/v1")
        self.assertEqual(launch.env["NINFER_BETA_API_KEY"], self.keys["ninfer"])
        self.assertNotIn("NINFER_NATIVE_API_KEY", launch.env)
        self.assertEqual(config["modelRoles"], dict.fromkeys(CHAT_ROLES, "ninfer-beta/q38-ninfer"))
        self.assertEqual(launch.argv[launch.argv.index("--model") + 1], "ninfer-beta/q38-ninfer")
        self.assertNotIn(self.keys["ninfer"], json.dumps([result, models, config, launch.argv]))

    def test_docker_probe_refuses_unestablished_or_stale_container(self):
        mutations = [("image_digest", "sha256:" + "f" * 64), ("running", False), ("running", None),
                     ("endpoint_state", "starting"), ("release_id", "other-release"),
                     ("container_id", ""), ("started_at", None), ("started_at", "2999-01-01T00:00:00Z"),
                     ("observed_at", "2000-01-01T00:00:00Z"),
                     ("deployment_profile", "wrong-profile"), ("model_identity_sha256", "f" * 64)]
        for field, value in mutations:
            candidate = copy.deepcopy(self.probe)
            candidate[field] = value
            self.write_probe(candidate)
            with self.subTest(field=field), self.assertRaisesRegex(ComparisonError, "Docker identity probe"):
                self.arm().preflight()
        self.probe_path.unlink()
        with self.assertRaisesRegex(ComparisonError, "Docker identity probe"):
            self.arm().preflight()

    def test_docker_publication_must_reach_only_the_bound_client_port(self):
        for field, value in (("host_port", 1), ("host_port", str(self.server.httpd.server_port)),
                             ("host_ip", "192.0.2.1"), ("host_ip", "::"),
                             ("container_port", 1), ("protocol", "udp")):
            candidate = copy.deepcopy(self.probe)
            candidate["publications"][0][field] = value
            self.write_probe(candidate)
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ComparisonError, "Docker identity probe"):
                self.arm().preflight()
        for publications in ([], None):
            self.write_probe({**self.probe, "publications": publications})
            with self.assertRaisesRegex(ComparisonError, "Docker identity probe"):
                self.arm().preflight()

    def test_docker_manifest_binds_image_release_config_and_model_before_probe(self):
        manifest_path = Path(self.bindings["ninfer"]["manifest"])
        original = json.loads(manifest_path.read_text())
        for keys, value in ((("components", "ninfer", "oci_manifest_digest"), "sha256:" + "f" * 64),
                            (("components", "ninfer", "server_binary_sha256"), "f" * 64),
                            (("components", "model", "artifact_sha256"), "f" * 64),
                            (("runtime_identity", "configuration_sha256"), "f" * 64),
                            (("runtime_identity", "public_model_id"), "wrong-model"),
                            (("release",), "wrong-release")):
            manifest = copy.deepcopy(original)
            target = manifest
            for part in keys[:-1]:
                target = target[part]
            target[keys[-1]] = value
            manifest_path.write_bytes(canonical_json(manifest))
            self.plan["ninfer"]["manifest_sha256"] = sha256_file(manifest_path)
            with self.subTest(field=keys), patch("omp_strata.comparison_ompcfg.run_bounded", side_effect=AssertionError("probe ran")):
                with self.assertRaisesRegex(ComparisonError, "manifest"):
                    self.arm().preflight()

    def test_docker_authentication_and_served_identity_fail_closed(self):
        for field, value in (("source_dirty", True), ("source_dirty", None), ("binary_sha256", "f" * 64),
                             ("config_sha256", "f" * 64), ("model_artifact_sha256", "f" * 64),
                             ("deployment_profile", "old-profile")):
            self.server.identity = {**native_identity(self.plan), field: value}
            with self.subTest(field=field), self.assertRaisesRegex(ComparisonError, "served"):
                self.arm().preflight()
        self.server.identity = native_identity(self.plan)
        self.server.model = "wrong-model"
        with self.assertRaisesRegex(ComparisonError, "model identity"):
            self.arm().preflight()
        self.server.model = "q38-ninfer"
        self.server.api_key = "other" * 8
        with self.assertRaisesRegex(ComparisonError, "model identity"):
            self.arm().preflight()

    def test_docker_probe_never_receives_secrets_or_shell_argv(self):
        original = self.bindings["ninfer"]["docker_identity_probe_argv"]
        for argv in (original + [self.keys["ninfer"]], original + ["--api-key=other-secret"],
                     ["powershell.exe", "-EncodedCommand", "opaque"], ["sh", "-c", "echo unsafe"]):
            self.bindings["ninfer"]["docker_identity_probe_argv"] = argv
            with self.subTest(argv=argv[:1]), patch("omp_strata.comparison_ompcfg.run_bounded", side_effect=AssertionError("probe ran")):
                with self.assertRaisesRegex(ComparisonError, "secrets or inline shell") as caught:
                    self.arm().preflight()
            self.assertNotIn(self.keys["ninfer"], str(caught.exception))


if __name__ == "__main__":
    unittest.main()
