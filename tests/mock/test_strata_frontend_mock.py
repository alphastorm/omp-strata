"""Real pinned Strata frontend + its MockEngine + real stock OMP; no GPU claims."""
import copy
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from omp_strata.layout import Layout
from omp_strata.ompcfg import install_profile_config
from omp_strata.profile import Profile, load as load_profile
from omp_strata.transcript import load, summarize, tool_cycles
from tests.mock.scripted_server import OmpTestCase, PROFILE_PATH

# Strata#211/#231 (v0.1.31): an announced tool call the output ends inside stays unfinished - its JSON is not closed
# and the answer does not end in "tool_calls". Earlier releases closed the JSON and reported a complete call.
STRATA_REPORTS_UNFINISHED_CALLS = tuple(
    int(x) for x in load_profile(PROFILE_PATH).data["strata"]["engine_version"].split(".")) >= (0, 1, 31)


def qwen_call(name, **arguments):
    body = "".join(f"<parameter={key}>\n{value}\n</parameter>\n" for key, value in arguments.items())
    return f"</think>\n\n<tool_call>\n<function={name}>\n{body}</function>\n</tool_call>"


class StrataFrontendMock(OmpTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        value = os.environ.get("OMP_STRATA_STRATA_SRC")
        if not value or not Path(value).is_dir():
            raise unittest.SkipTest("set OMP_STRATA_STRATA_SRC to the pinned Strata source checkout")
        cls.source = Path(value).resolve()
        cls.python = os.environ.get("OMP_STRATA_STRATA_PYTHON", sys.executable)
        result = subprocess.run(["git", "-C", str(cls.source), "rev-parse", "HEAD"],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
        expected = load_profile(PROFILE_PATH).data["strata"]["commit"]
        if result.returncode or result.stdout.strip() != expected:
            raise AssertionError("OMP_STRATA_STRATA_SRC is not the profile's pinned commit")

    def start_frontend(self, scripts, *, max_tokens=1024):
        # MockEngine has a 32768-byte-token context, not the production context.
        # This explicit test-only budget avoids pretending its tokenizer is Qwen.
        data = copy.deepcopy(self.layout.profile.data)
        data["omp"].update(max_tokens=max_tokens, context_window=32768)
        self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, data))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        config = self.layout.root / "mock-strata.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({"model_name": data["strata"]["model_name"]}), encoding="utf-8")
        argv = [self.python, "-m", "serve.server", "--engine", "mock", "--port", str(port),
                "--host", "127.0.0.1", "--config", str(config),
                "--tokenizer", str(self.layout.root / "absent-mock-tokenizer")]
        for script in scripts:
            argv.extend(["--script", script])
        env = dict(self.env, PYTHONDONTWRITEBYTECODE="1")
        process = subprocess.Popen(argv, cwd=self.source, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   encoding="utf-8", start_new_session=os.name == "posix")
        self.processes.append(process)
        base = f"http://127.0.0.1:{port}/v1"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail("stock Strata frontend failed to start; provision its upstream requirements and set "
                          "OMP_STRATA_STRATA_PYTHON: " + stderr[-1600:])
            try:
                request = urllib.request.Request(base + "/models", headers={"Authorization": "Bearer " + self.api_key})
                with opener.open(request, timeout=0.5) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError):
                time.sleep(0.025)
        else:
            self.fail("stock Strata MockEngine frontend did not become ready in 10 seconds")
        install_profile_config(self.layout, base_url=base)
        return base, opener

    def run_frontend_omp(self, **kwargs):
        return self.run_omp(extra=["--system-prompt", "Complete the fixture using the specified tools."], **kwargs)

    def test_text_turn_through_authenticated_real_frontend(self):
        self.start_frontend(["</think>\n\nHello from stock Strata."])
        summary = self.assert_success(self.run_frontend_omp(), "Hello from stock Strata.")
        self.assertEqual(summary["providers"], ["strata-local"])
        self.assertEqual(summary["apis"], ["openai-completions"])

    def test_wrong_key_returns_401_and_no_successful_turn(self):
        base, opener = self.start_frontend(["</think>\n\nThis must not be generated."])
        wrong_key = self.api_key + "-wrong"
        request = urllib.request.Request(base + "/chat/completions", data=b'{"messages":[]}',
                                         headers={"Authorization": "Bearer " + wrong_key,
                                                  "Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            opener.open(request, timeout=5)
        self.assertEqual(caught.exception.code, 401)
        caught.exception.close()
        self.assert_failure(self.run_frontend_omp(env=dict(self.env, STRATA_API_KEY=wrong_key)))

    def test_qwen_xml_typed_read_cycle(self):
        (self.repo / "frontend.txt").write_text("frontend fixture payload\n", encoding="utf-8")
        self.start_frontend([qwen_call("read", i="Reading fixture", path="frontend.txt"),
                             "</think>\n\nFrontend tool cycle complete."])
        summary = self.assert_success(self.run_frontend_omp(), "Frontend tool cycle complete.")
        cycles = tool_cycles(load(self.session()))
        self.assertEqual(len(cycles), 1)
        self.assertRegex(cycles[0]["id"], r"^call_[0-9a-f]{24}$")
        self.assertEqual(cycles[0]["name"], "read")
        self.assertIn("frontend fixture payload", cycles[0]["result_text"])
        self.assertTrue(cycles[0]["result_found"])
        self.assertFalse(cycles[0]["is_error"])
        self.assertEqual(summary["stopReasons"], ["toolUse", "stop"])
        self.assertEqual(summary["calls_without_results"], [])

    def cutoff_probe(self, *, token_limit):
        prefix = ("</think>\n\n<tool_call>\n<function=write>\n"
                  "<parameter=i>Writing fixture</parameter>\n"
                  "<parameter=path>frontend-partial.txt</parameter>\n<parameter=content>")
        script = prefix + ("partial-content-" * 100 if token_limit else "partial content")
        limit = 256 if token_limit else 1024
        base, opener = self.start_frontend([script, script, "</think>\n\nFollow-up after partial tool."], max_tokens=limit)
        # Capture the real frontend's SSE directly, without inserting a proxy in
        # OMP's route. The repeated script then drives OMP on the next request.
        body = {"model": self.layout.profile.data["strata"]["model_name"], "stream": True,
                "messages": [{"role": "user", "content": "Run the fixture tool."}], "max_tokens": limit,
                "tools": [{"type": "function", "function": {"name": "write", "parameters": {
                    "type": "object", "properties": {key: {"type": "string"} for key in ("i", "path", "content")},
                    "required": ["i", "path", "content"]}}}]}
        request = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Authorization": "Bearer " + self.api_key,
                                                  "Content-Type": "application/json"})
        with opener.open(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
        chunks = [json.loads(line[6:]) for line in raw.splitlines()
                  if line.startswith("data: ") and line != "data: [DONE]"]
        deltas = [call for chunk in chunks for choice in chunk.get("choices", [])
                  for call in choice.get("delta", {}).get("tool_calls", [])]
        arguments = "".join(call.get("function", {}).get("arguments", "") for call in deltas)
        try:
            parsed = json.loads(arguments)
        except ValueError:
            parsed = None                       # left unterminated by the server (Strata v0.1.31+)
        finish = [choice["finish_reason"] for chunk in chunks for choice in chunk.get("choices", [])
                  if choice.get("finish_reason")]
        self.assertIn("frontend-partial.txt", arguments)
        self.assertIn("data: [DONE]", raw)
        result = self.run_frontend_omp()
        path = self.repo / "frontend-partial.txt"
        summary = summarize(self.session())
        print("G04 composed cutoff " + json.dumps({"token_limit": token_limit, "wire_finish": finish,
              "wire_arguments_valid": parsed is not None,
              "closing_fragment": deltas[-1].get("function", {}).get("arguments"),
              "side_effect": path.exists(), "exit": result["returncode"], "stopReasons": summary["stopReasons"]}))
        return result, path, parsed, finish, summary

    def test_token_limit_inside_qwen_tool_body(self):
        result, path, parsed, finish, summary = self.cutoff_probe(token_limit=True)
        self.assertEqual(finish, ["length"])
        self.assertFalse(path.exists(), "a length-truncated Qwen call executed a side effect")
        cycle, = tool_cycles(load(self.session()))
        self.assertTrue(cycle["result_found"])
        self.assertTrue(cycle["is_error"])
        self.assertEqual(summary["stopReasons"], ["length", "stop"])
        self.assert_success(result, "Follow-up after partial tool.")

    def test_model_stop_inside_qwen_tool_body_is_not_reported_as_complete(self):
        """Strata half of G04 (#211): the wire must not present an unfinished call as a complete one."""
        _, _, parsed, finish, _ = self.cutoff_probe(token_limit=False)
        self.assertNotIn("tool_calls", finish)
        self.assertIsNone(parsed, "the server closed the unfinished call's JSON")

    if not STRATA_REPORTS_UNFINISHED_CALLS:
        test_model_stop_inside_qwen_tool_body_is_not_reported_as_complete = unittest.expectedFailure(
            test_model_stop_inside_qwen_tool_body_is_not_reported_as_complete)

    @unittest.expectedFailure
    def test_model_stop_inside_qwen_tool_body(self):
        """Composed G04: stock OMP must not execute the unfinished call, whatever the server reports."""
        result, path, parsed, finish, summary = self.cutoff_probe(token_limit=False)
        self.assert_cut_call_not_run(path, result)


if __name__ == "__main__":
    unittest.main()
