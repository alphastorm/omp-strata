"""Pure launcher boundaries; CLI/schema integration is exercised by the mock gates."""
import json
import secrets
import tempfile
import unittest
from pathlib import Path

from omp_strata.layout import Layout
from omp_strata.ompcfg import (EGRESS_GUARD_NO_PROXY, EGRESS_GUARD_PROXY, LauncherError, install_profile_config,
                               CHAT_ROLES, install_route_config, isolated_env, omp_argv, render_config_yml, render_models_yml)
from omp_strata.profile import ClientRoute, load

from tests.candidate import PROFILE


class OmpConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = Layout(Path(temporary.name) / "integration", load(PROFILE))

    def test_missing_blank_key_refused_before_creating_home(self):
        for value in (None, "", " ", "\t\n"):
            with self.subTest(value=value), self.assertRaises(LauncherError):
                isolated_env(self.layout, api_key=value, base_env={})
        self.assertFalse(self.layout.root.exists())

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

    def test_config_overrides_merge_without_mutating_caller(self):
        override = {"compaction": {"thresholdTokens": 2000}, "retry": {"maxRetries": 0}}
        value = json.loads(render_config_yml(self.layout.profile, overrides=override))
        self.assertFalse(value["retry"]["enabled"])
        self.assertFalse(value["retry"]["modelFallback"])
        self.assertEqual(value["compaction"]["thresholdTokens"], 2000)
        self.assertEqual(override, {"compaction": {"thresholdTokens": 2000}, "retry": {"maxRetries": 0}})

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
        registry = {"retry.enabled", "retry.modelFallback", "retry.fallbackRevertPolicy",
                    "startup.checkUpdate", "providers.maxInFlightRequests", "modelRoles",
                    "enabledProviders", "disabledProviders", "mcp.enableProjectConfig",
                    "telemetry.otlpExportEnabled", "dev.autoqa", "dev.autoqaConsent", "task.agentModelOverrides"}
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


if __name__ == "__main__":
    unittest.main()
