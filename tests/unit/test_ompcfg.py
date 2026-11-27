"""Pure launcher boundaries; CLI/schema integration is exercised by the mock gates."""
import hashlib
import io
import json
import mmap
import os
import secrets
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path

from omp_strata import ompcfg, procs
from omp_strata.common import release_version
from omp_strata.layout import Layout
from omp_strata.ompcfg import (EGRESS_GUARD_NO_PROXY, EGRESS_GUARD_PROXY, LauncherError, install_profile_config,
                               CHAT_ROLES, drop_native_cache, install_route_config, isolated_env, omp_argv,
                               render_config_yml, render_models_yml, route_argv)
from omp_strata.profile import ClientRoute, Profile, load, load_route

from tests.candidate import PROFILE
from tests.unit.test_profile import single_gpu_data


def rollback_renders(repo, root):
    """Hash sorted (filename, config bytes, models bytes, normalized env) frames, independently per category."""
    result = {}
    for kind in ("profiles", "routes"):
        digest = hashlib.sha256()
        count = 0
        for path in sorted((repo / kind).glob("*.json")):
            route = load_route(path) if kind == "routes" else None
            profile = route.main if route else load(path)
            if release_version(profile.data["omp"]["version"]) >= (19, 2, 0):
                continue
            layout = Layout(root, profile)
            installed = install_route_config(layout, route) if route else install_profile_config(layout)
            env = isolated_env(layout, api_key="fixture", base_env={"PATH": "bin", "PI_AI_CODEX_CLIENT_VERSION": "bad"})
            if os.name != "nt":
                for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
                    if env.pop(name.lower()) != env[name]:
                        raise AssertionError("mismatched POSIX proxy spellings")
            for name, value in env.items():
                if Path(value).is_absolute() and Path(value).is_relative_to(root):
                    env[name] = "<root>/" + Path(value).relative_to(root).as_posix()
            for frame in (path.name.encode(), installed["config"].read_bytes(), installed["models"].read_bytes(),
                          json.dumps(env, sort_keys=True).encode()):
                digest.update(frame + b"\0")
            count += 1
        result[kind] = {"count": count, "sha256": digest.hexdigest()}
    return result


class OmpConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = Layout(Path(temporary.name) / "integration", load(PROFILE))

    def test_all_rollback_config_model_and_env_bytes_match_pre_admission(self):
        repo = Path(__file__).resolve().parents[2]
        golden = json.loads((repo / "tests/fixtures/omp-rollback-renders.json").read_text())
        self.assertEqual(golden["renders"], rollback_renders(repo, self.layout.root.resolve()))

    def test_offline_is_only_a_literal_on_v19_routes(self):
        profile = self.layout.profile
        profile.data["omp"]["version"] = "19.0.0"
        route = ClientRoute(self.layout.root / "route.json", {"members": [{"label": "lead"}],
                            "roles": {"default": "lead"}}, {"lead": profile})
        binary = self.layout.root / "client"
        for arg in ("--offline", "--offline=true"):
            with self.assertRaisesRegex(LauncherError, "subagents"):
                route_argv(self.layout, route, binary=binary, extra=[arg])
        self.assertEqual(route_argv(self.layout, route, binary=binary, extra=["--", "--offline"])[-2:],
                         ["--", "--offline"])
        self.assertEqual(omp_argv(self.layout, binary=binary, extra=["--offline"])[-1], "--offline")

    def test_missing_blank_key_refused_before_creating_home(self):
        for value in (None, "", " ", "\t\n"):
            with self.subTest(value=value), self.assertRaises(LauncherError):
                isolated_env(self.layout, api_key=value, base_env={})
        self.assertFalse(self.layout.root.exists())

    def test_native_cache_is_dropped_from_both_locations_and_nothing_else(self):
        home = self.layout.omp_home
        addons = [home / ".omp" / "natives" / "18.5.0" / "pi_natives.darwin-arm64.node",
                  home / ".local" / "share" / "omp" / "natives" / "18.5.0" / "pi_natives.linux-x64.node"]
        kept = [home / ".omp" / "profiles" / "omp-strata" / "agent" / "config.yml",
                home / ".local" / "share" / "omp" / "sessions" / "s.jsonl"]
        for path in addons + kept:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x")
        drop_native_cache(home, version="19.0.0")
        self.assertFalse((home / ".omp" / "natives").exists())
        self.assertFalse((home / ".local" / "share" / "omp" / "natives").exists())
        self.assertTrue(all(path.is_file() for path in kept))
        drop_native_cache(home, version="19.0.0")  # nothing left to remove is not an error

    def test_native_cache_symlink_out_of_home_is_never_followed(self):
        shared = self.layout.root / "shared-natives"
        (shared / "18.5.0").mkdir(parents=True)
        (shared / "18.5.0" / "pi_natives.node").write_bytes(b"x")
        (self.layout.omp_home / ".omp").mkdir(parents=True)
        (self.layout.omp_home / ".omp" / "natives").symlink_to(shared, target_is_directory=True)
        drop_native_cache(self.layout.omp_home, version="19.0.0")
        self.assertTrue((shared / "18.5.0" / "pi_natives.node").is_file())

    def test_slot_worker_must_exit_before_its_natives_are_removed(self):
        home = self.layout.omp_home
        # OMP 19.2.1's layout on Windows roots (2026-11-27): one level deeper than the version directory. Missing it
        # skipped the wait, so every requalify removed the last attempt's addon under its worker (WinError 5).
        addon = home / ".omp/natives/19.2.1/embedded-b11b531cef3cbd5e/pi_natives.win32-x64-baseline.node"
        addon.parent.mkdir(parents=True)
        addon.write_bytes(b"fixture")
        with patch("omp_strata.ompcfg._native_cache_busy", return_value=True), \
             patch("omp_strata.ompcfg.time.monotonic", side_effect=[0, 10]):
            with self.assertRaisesRegex(RuntimeError, "worker survived"):
                drop_native_cache(home, version="19.2.1", binary=self.layout.omp_binary())
        self.assertTrue(addon.is_file())
        with patch("omp_strata.ompcfg._native_cache_busy", side_effect=[True, False]) as users, \
             patch("omp_strata.ompcfg.time.sleep"):
            drop_native_cache(home, version="19.2.1", binary=self.layout.omp_binary())
        self.assertEqual(users.call_count, 2)
        self.assertFalse(addon.exists())

    def test_linux_shared_binary_is_not_a_user_of_every_attempts_addon(self):
        binary = self.layout.omp_binary()
        addon = self.layout.omp_home / ".omp/natives/19.2.1/pi_natives.node"
        addon.parent.mkdir(parents=True)
        addon.touch()
        ino = addon.stat().st_ino
        # Both clients share the pinned image. The recorded path may be an alias or contain spaces;
        # neither a matching filename nor an inode number on another device identifies our addon.
        rows = procs.ProcessTable({pid: procs.ProcInfo(pid, 1, str(pid), str(binary.resolve()))
                                   for pid in (41, 42)}, set())
        def maps(device, inode, name):
            return f"7f00-8f00 r-xp 00000000 {device} {inode} {name}\n".encode()
        other = maps("08:01", ino + 1, str(addon)) + maps("08:02", ino, str(addon))
        for mapping, expected in ((other, False), (maps("08:01", ino, "/alias of file (deleted)"), True),
                                  (FileNotFoundError(), False), (PermissionError(), RuntimeError),
                                  (b"unparseable\n", RuntimeError)):
            with self.subTest(mapping=mapping), patch.object(ompcfg.sys, "platform", "linux"), \
                 patch.object(ompcfg, "os", SimpleNamespace(name="posix", major=lambda _: 8, minor=lambda _: 1)), \
                 patch.object(procs, "table", return_value=rows), patch.object(Path, "is_file", return_value=True), \
                 patch.object(Path, "open", side_effect=[io.BytesIO(other),
                              mapping if isinstance(mapping, Exception) else io.BytesIO(mapping)]) as opened:
                if expected is RuntimeError:
                    with self.assertRaisesRegex(RuntimeError, "addon census unavailable"):
                        ompcfg._native_cache_busy(binary, [addon])
                else:
                    self.assertIs(ompcfg._native_cache_busy(binary, [addon]), expected)
                self.assertEqual(opened.call_count, 2)

    @unittest.skipUnless(sys.platform.startswith("linux"), "exercises real procfs mappings")
    def test_only_the_mapped_linux_attempt_is_retained(self):
        home = self.layout.omp_home
        addon = home / ".omp/natives/19.2.1/pi_natives.node"
        addon.parent.mkdir(parents=True)
        addon.write_bytes(b"addon")
        other = home / "other.node"
        other.write_bytes(b"other")
        # The test runner remains alive with the very same executable across all three observations.
        with addon.open("rb") as own, other.open("rb") as foreign, \
             mmap.mmap(foreign.fileno(), 0, access=mmap.ACCESS_READ):
            with mmap.mmap(own.fileno(), 0, access=mmap.ACCESS_READ):
                self.assertTrue(ompcfg._native_cache_busy(Path(sys.executable), [addon]))
            self.assertFalse(ompcfg._native_cache_busy(Path(sys.executable), [addon]))
            self.assertTrue(ompcfg._native_cache_busy(Path(sys.executable), [other]))

    def test_environment_only_preserves_essentials_and_isolates_all_roots(self):
        secret = secrets.token_urlsafe(24)
        names = ["OPENAI_API_KEY", "SAMPLE_API_KEY", "EXAMPLE_TOKEN", "EXAMPLE_SECRET", "OMP_PROFILE",
                 "PI_CONFIG", "ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "AWS_PROFILE", "GOOGLE_APPLICATION_CREDENTIALS",
                 "AZURE_ID", "HF_HOME", "GH_CONFIG_DIR", "GITHUB_ENV", "HTTP_PROXY", "OTEL_EXPORTER_OTLP_ENDPOINT",
                 "NODE_OPTIONS", "BASH_ENV", "SSH_AUTH_SOCK", "LC_AUTH_TOKEN"]
        base = {name: secret for name in names}
        base.update(PATH="fixture-bin", SystemRoot="fixture-system", LANG="C.UTF-8", LC_ALL="C.UTF-8")
        env = isolated_env(self.layout, api_key=secret, base_env=base)
        self.assertEqual(env["STRATA_API_KEY"], secret)
        self.assertEqual(env["PATH"], "fixture-bin")
        self.assertEqual(env["SystemRoot"], "fixture-system")
        self.assertEqual(env["LANG"], "C.UTF-8")
        self.assertEqual(env["LC_ALL"], "C.UTF-8")
        guarded = {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}
        for name in names:
            if name in guarded:
                self.assertNotEqual(env[name], secret, "an inherited proxy must never reach the client")
            else:
                self.assertNotIn(name, env)
            self.assertEqual(base[name], secret, "the caller's environment must not be mutated")
        # Non-loopback HTTP(S) goes to a closed loopback port; loopback (the Strata route) stays direct.
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            self.assertEqual(env[name], EGRESS_GUARD_PROXY)
        self.assertEqual(env["NO_PROXY"], EGRESS_GUARD_NO_PROXY)
        self.assertIn("127.0.0.1", env["NO_PROXY"].split(","))
        for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP",
                     "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
            self.assertTrue(Path(env[name]).is_relative_to(self.layout.omp_home.resolve()))
            self.assertTrue(Path(env[name]).is_dir())

    def test_route_and_discovery_override_flags_are_refused(self):
        flags = ("--model", "--models", "--profile", "--alias", "--provider", "--api-key", "--base-url",
                 "--config", "--config-file", "--models-file", "--smol", "--slow", "--plan",
                 "--prewalk-into", "--plan-yolo-into", "--extension", "--trusted-extension", "--hook",
                 "--plugin-dir", "--skills", "--from-claude", "--from-codex", "-e")
        for flag in flags:
            for extra in ([flag, "other"], [flag + "=other"]):
                with self.subTest(extra=extra), self.assertRaises(LauncherError):
                    omp_argv(self.layout, extra=extra)

    def test_literal_prompt_after_separator_is_not_an_override(self):
        extra = ["-p", "--", "--model", "is just prompt text"]
        argv = omp_argv(self.layout, extra=extra, platform="linux-x64")
        self.assertEqual(argv[-len(extra):], extra)
        self.assertEqual(argv[0], str(self.layout.omp_binary("linux-x64")))

    def test_cost_threshold_flags_preserve_the_pinned_route_and_discovery_policy(self):
        baseline = omp_argv(self.layout, extra=[], platform="linux-x64")
        for extra in (["--warn-cost", "0.5", "--max-cost", "1"],
                      ["--warn-cost=0.5", "--max-cost=1"]):
            with self.subTest(extra=extra):
                self.assertEqual(baseline + extra, omp_argv(self.layout, extra=extra, platform="linux-x64"))

    def test_config_overrides_merge_without_mutating_caller(self):
        override = {"compaction": {"thresholdTokens": 2000}, "retry": {"maxRetries": 0}}
        value = json.loads(render_config_yml(self.layout.profile, overrides=override))
        self.assertFalse(value["retry"]["enabled"])
        self.assertFalse(value["retry"]["modelFallback"])
        self.assertEqual(value["compaction"]["thresholdTokens"], 2000)
        self.assertEqual(override, {"compaction": {"thresholdTokens": 2000}, "retry": {"maxRetries": 0}})

    def test_v19_disables_background_requests_services_and_foreign_discovery(self):
        for version in ("18.18.0", "18.18.3", "19.0.0", "19.2.1"):
            with self.subTest(version=version):
                profile = self.layout.profile
                data = {**profile.data, "omp": {**profile.data["omp"], "version": version}}
                layout = Layout(self.layout.root, Profile(profile.path, data))
                settings = json.loads(render_config_yml(layout.profile))
                discovery = set(settings["disabledProviders"])
                foreign = {"ssh-json", "ssh-config", "custom-context"}
                env = isolated_env(layout, api_key="fixture", base_env={
                    "PI_AI_CODEX_CLIENT_VERSION": "999.0.0", "OMP_DAEMON_TCP": "localhost:1234"})
                self.assertNotIn("OMP_DAEMON_TCP", env)
                if release_version(version) >= (19, 0, 0):
                    self.assertEqual(settings["composer"], {"predictions": False})
                    self.assertEqual(settings["launch"], {"enabled": False})
                    self.assertEqual(settings["spelling"], {"autocomplete": "off"})
                    self.assertNotIn("ssh", discovery)
                    self.assertLessEqual(foreign, discovery)
                    self.assertEqual(env["PI_AI_CODEX_CLIENT_VERSION"], "0.169.0")
                else:
                    self.assertTrue({"composer", "launch", "spelling"}.isdisjoint(settings))
                    self.assertIn("ssh", discovery)
                    self.assertTrue(foreign.isdisjoint(discovery))
                    self.assertNotIn("PI_AI_CODEX_CLIENT_VERSION", env)

    def test_local_and_route_configs_disable_updates_and_the_setup_wizard(self):
        profile = self.layout.profile
        route = ClientRoute(self.layout.root / "route.json", {
            "members": [{"label": "worker", "local_port": 18091}],
            "roles": {role: "worker" for role in CHAT_ROLES}, "agents": {}}, {"worker": profile})
        for text in (render_config_yml(profile), install_route_config(self.layout, route)["config"].read_text()):
            settings = json.loads(text)
            self.assertEqual({"auto": False}, settings["update"])
            self.assertEqual({"checkUpdate": False, "setupWizard": False}, settings["startup"])

    def test_remote_or_credential_bearing_urls_are_refused(self):
        for url in ("https://example.invalid/v1", "http://0.0.0.0:8095/v1", "http://localhost:8095/v1",
                    "http://127.0.0.1:8095/v1?key=value", "http://name:password@127.0.0.1:8095/v1"):
            with self.subTest(url=url), self.assertRaises(LauncherError):
                render_models_yml(self.layout.profile, base_url=url)
        self.assertFalse(self.layout.root.exists())

    def test_declared_window_leaves_room_for_strata_slack_and_omp_estimate_error(self):
        # Strata refuses prompt + max_tokens + 8 > n_ctx; stock OMP's fitted cap overshot the declared window by
        # 21 tokens on the real route (G17). The declared window must stay below the engine's by more than both.
        document = json.loads(render_models_yml(self.layout.profile, base_url="http://127.0.0.1:8095/v1"))
        declared = document["providers"]["strata-local"]["models"][0]["contextWindow"]
        engine = self.layout.profile.data["strata"]["setup_args"]["context"]
        self.assertGreater(engine - declared, 8 + 21)
        self.assertGreater(declared, self.layout.profile.data["omp"]["max_tokens"])

    def test_emitted_models_have_only_verified_schema_keys(self):
        # Stock 18.4.0 accepts unknown compat properties silently. Guard our
        # emitted surface independently: 401778d models-config-schema-bundle.ts
        # OpenAICompatFields:39, ModelThinkingSchema:123, ModelDefinitionSchema:191,
        # ProviderConfigSchema:327. Invalid known values are also tried against
        # the real binary in G02; this catches misspellings it would ignore.
        document = json.loads(render_models_yml(self.layout.profile, base_url="http://127.0.0.1:8095/v1"))
        self.assertLessEqual(document.keys(), {"providers"})
        self.assertEqual(set(document["providers"]), {"strata-local"})
        provider = document["providers"]["strata-local"]
        self.assertLessEqual(provider.keys(), {"baseUrl", "api", "apiKey", "authHeader", "models"})
        for model in provider["models"]:
            self.assertLessEqual(model.keys(), {"id", "name", "reasoning", "thinking", "input", "supportsTools",
                                               "cost", "contextWindow", "maxTokens", "compat"})
            self.assertLessEqual(model["thinking"].keys(), {"mode", "efforts"})
            self.assertLessEqual(model["cost"].keys(), {"input", "output", "cacheRead", "cacheWrite"})
            self.assertLessEqual(model["compat"].keys(), {"supportsStore", "supportsDeveloperRole",
                "supportsMultipleSystemMessages", "maxTokensField", "supportsUsageInStreaming",
                "supportsReasoningEffort", "thinkingFormat", "supportsStrictMode"})

    def test_emitted_settings_have_only_verified_registry_keys(self):
        # 401778d has domain settings, not settings-schema.ts: config/model-settings.ts,
        # session/settings.ts, session/context-settings.ts:196, modes/settings.ts,
        # mcp/settings.ts, tools/settings.ts
        # and telemetry-settings.ts. G02 additionally checks effective values.
        # Remote task.agentModelOverrides is exercised with stock 18.4.6/.8/.10/.12.
        # compaction.asyncEnabled: session/context-settings.ts in every pinned release, 18.4.0 to 18.8.0.
        # update.auto and startup.setupWizard: b5a6b2f7 modes/settings.ts, suppressing interactive update offers.
        registry = {"retry.enabled", "retry.modelFallback", "retry.fallbackRevertPolicy",
                    "update.auto", "startup.checkUpdate", "startup.setupWizard",
                    "providers.maxInFlightRequests", "compaction.asyncEnabled", "modelRoles",
                    "enabledProviders", "disabledProviders", "mcp.enableProjectConfig",
                    "telemetry.otlpExportEnabled", "dev.autoqa", "dev.autoqaConsent", "task.agentModelOverrides",
                    "composer.predictions", "launch.enabled", "spelling.autocomplete"}
        def check(value, prefix=""):
            for key, child in value.items():
                dotted = f"{prefix}.{key}" if prefix else key
                if dotted in registry:
                    continue
                self.assertTrue(any(name.startswith(dotted + ".") for name in registry),
                                f"unknown pinned setting: {dotted}")
                self.assertIsInstance(child, dict, f"unknown pinned setting: {dotted}")
                check(child, dotted)
        check(json.loads(render_config_yml(self.layout.profile)))
        profile = self.layout.profile
        route = ClientRoute(self.layout.root / "route.json", {
            "members": [{"label": "worker", "local_port": 18091}],
            "roles": {role: "worker" for role in CHAT_ROLES}, "agents": {}}, {"worker": profile})
        check(json.loads(install_route_config(self.layout, route)["config"].read_text()))

    def test_inflight_limit_is_each_servers_batch_slots(self):
        # OMP may send a server as many requests at once as it has batch slots (stock setup --parallel), else one.
        def server(slots):
            data = single_gpu_data()
            data["strata"]["setup_args"].pop("parallel", None)
            if slots:
                data["strata"]["setup_args"]["parallel"] = slots
            return Profile(self.layout.profile.path, data)

        def limits(text):
            return json.loads(text)["providers"]["maxInFlightRequests"]

        plain, slotted = server(None), server(4)
        self.assertEqual({"strata-local": 1}, limits(render_config_yml(plain)))
        self.assertEqual({"strata-local": 4}, limits(render_config_yml(slotted)))
        route = ClientRoute(self.layout.root / "route.json", {
            "members": [{"label": "lead", "local_port": 18091}, {"label": "worker", "local_port": 18092}],
            "roles": {role: "worker" if role == "task" else "lead" for role in CHAT_ROLES}, "agents": {}},
            {"lead": plain, "worker": slotted})
        self.assertEqual({"strata-lead": 1, "strata-worker": 4},
                         limits(install_route_config(self.layout, route)["config"].read_text()))


if __name__ == "__main__":
    unittest.main()
