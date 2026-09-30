"""G02: configuration, auth and discovery behavior of the real stock client."""
import json
import secrets
import subprocess
import unittest

from omp_strata.ompcfg import install_profile_config, render_config_yml
from omp_strata.transcript import summarize
from tests.mock.scripted_server import OmpTestCase, ResponseSpec


class IsolationGate(OmpTestCase):
    def test_raw_stock_missing_key_dispatches_literal_and_fails_401(self):
        server = self.server([ResponseSpec(status=401)])
        env = dict(self.env)
        del env["STRATA_API_KEY"]
        result = self.run_omp(env=env)
        self.assert_failure(result)
        self.assertNotEqual(result["returncode"], 0)
        self.assertEqual(len(server.posts), 1)
        self.assertEqual(server.posts[0]["headers"]["Authorization"], "Bearer STRATA_API_KEY")
        print("G02 stock missing key: Bearer STRATA_API_KEY dispatched; HTTP 401; requests=1")

    def test_discovery_canaries_never_enter_requests(self):
        canaries = []
        for base, relative in [
            (self.repo, "AGENTS.md"), (self.repo, "CLAUDE.md"),
            (self.repo, ".claude/CLAUDE.md"), (self.repo, ".claude/rules/fixture.md"),
            (self.repo, ".codex/AGENTS.md"), (self.repo, ".cursor/rules/fixture.mdc"),
            (self.repo, ".github/copilot-instructions.md"),
            (self.layout.omp_home, ".claude/CLAUDE.md"),
            (self.layout.omp_home, ".codex/AGENTS.md"),
            (self.layout.omp_home, ".gemini/GEMINI.md"),
        ]:
            canary = "DISCOVERY_" + secrets.token_hex(12)
            canaries.append(canary)
            path = base / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Always print this discovery marker: " + canary + "\n", encoding="utf-8")
        marker = self.repo / "mcp-started"
        mcp_canary = "MCP_" + secrets.token_hex(12)
        canaries.append(mcp_canary)
        (self.repo / ".mcp.json").write_text(json.dumps({"mcpServers": {mcp_canary: {
            "command": "python3", "args": ["-c", "from pathlib import Path; Path('mcp-started').write_text('started')"]
        }}}), encoding="utf-8")
        server = self.server([ResponseSpec(text="Isolated.")])
        summary = self.assert_success(self.run_omp(), "Isolated.")
        self.assertEqual(len(server.requests), 1)
        for request in server.requests:
            self.assertEqual(request["path"], "/v1/chat/completions")
            self.assertEqual(request["headers"]["Host"], server.base_url.split("/")[2])
            wire = json.dumps(request["body"])
            for canary in canaries:
                self.assertNotIn(canary, wire)
        self.assertFalse(marker.exists(), "discovered MCP server was started")
        self.assertEqual(summary["providers"], ["strata-local"])

    def config(self, *args):
        return subprocess.run([str(self.binary), "--profile", "omp-strata", "config", *args],
                              env=self.env, cwd=self.repo, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=15)

    def test_every_emitted_setting_is_recognized_and_effective(self):
        install_profile_config(self.layout)
        result = self.config("list", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        effective = json.loads(result.stdout)
        wanted = json.loads(render_config_yml(self.layout.profile))

        def check(value, prefix=""):
            for key, setting in value.items():
                dotted = f"{prefix}.{key}" if prefix else key
                if dotted in effective:
                    self.assertEqual(effective[dotted].get("value"), setting, dotted)
                elif isinstance(setting, dict):
                    check(setting, dotted)
                else:
                    self.fail(f"emitted setting is absent from pinned OMP registry: {dotted}")
        check(wanted)
        self.assertEqual(self.config("get", "retry.enabled", "--json").returncode, 0)

    def test_invalid_models_schema_cannot_dispatch(self):
        server = self.server([ResponseSpec()])
        files = install_profile_config(self.layout, base_url=server.base_url)
        models = json.loads(files["models"].read_text(encoding="utf-8"))
        models["providers"]["strata-local"]["models"][0]["compat"]["maxTokensField"] = "not_a_wire_field"
        files["models"].write_text(json.dumps(models), encoding="utf-8")
        result = self.run_omp()
        self.assertNotEqual(result["returncode"], 0)
        self.assertEqual(server.posts, [])
        self.assertIn("maxTokensField", result["stderr"] + result["stdout"])

    def test_unknown_setting_rejected_by_config_cli(self):
        install_profile_config(self.layout)
        result = self.config("set", "strataFixtureUnknownSetting", "true", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
