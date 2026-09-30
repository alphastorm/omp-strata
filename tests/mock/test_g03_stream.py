"""G03: real stock OMP consumes Strata-shaped streaming responses and runs its tools."""
import json
import unittest

from omp_strata.transcript import load, tool_cycles
from tests.mock.scripted_server import OmpTestCase, ResponseSpec, ToolCall, wire_fields


class StreamGate(OmpTestCase):
    def assert_route(self, server, summary, count):
        self.assertEqual(len(server.posts), count)
        self.assertEqual(summary["providers"], ["strata-local"])
        self.assertEqual(summary["apis"], ["openai-completions"])
        self.assertEqual(summary["models"], [self.layout.profile.data["strata"]["model_name"]])
        self.assertTrue(summary["tool_ids_well_formed"])
        self.assertTrue(summary["tool_ids_unique"])
        self.assertEqual(summary["orphan_results"], [])
        self.assertEqual(summary["calls_without_results"], [])
        for request in server.posts:
            self.assertEqual(request["path"], "/v1/chat/completions")
            self.assertEqual(request["headers"]["Authorization"], "Bearer " + self.api_key)
        self.assertEqual(summary["stopReasons"][-1], "stop")

    def test_utf8_split_reasoning_usage_and_wire(self):
        text = "The café result is λ = 7."
        server = self.server([ResponseSpec(text=text, split_utf8=True)])
        result = self.run_omp(extra=["--thinking", "medium"])
        summary = self.assert_success(result, text)
        self.assert_route(server, summary, 1)
        self.assertEqual(server.split_writes, 1)
        assistant = next(m for m in result["messages"] if m.get("role") == "assistant")
        self.assertIn("Checking the fixture.", "".join(b.get("thinking", "") for b in assistant["content"]))
        self.assertEqual(summary["usage"], {"input": 40, "output": 45, "cacheRead": 80,
                                            "cacheWrite": 0, "totalTokens": 165, "reasoningTokens": 0})
        fields = wire_fields(server.posts[0])
        self.assertEqual(fields["max_tokens"], self.layout.profile.data["omp"]["max_tokens"])
        self.assertEqual(fields["stream_options"], {"include_usage": True})
        self.assertEqual(set(fields["tools"]), {"read", "write", "bash"})
        self.assertFalse(fields["tool_choice_present"])
        self.assertFalse(fields["parallel_tool_calls_present"])
        print("G03 wire " + json.dumps(fields, sort_keys=True))

    def test_multiple_fragmented_reads_round_trip(self):
        files = {"alpha.txt": "alpha fixture payload\n", "beta.txt": "beta fixture payload\n"}
        for name, text in files.items():
            (self.repo / name).write_text(text, encoding="utf-8")
        calls = [ToolCall("read", {"i": "Reading fixture", "path": name}, fragment_size=2) for name in files]
        server = self.server([ResponseSpec(text="", calls=calls), ResponseSpec(text="Both files inspected.")])
        summary = self.assert_success(self.run_omp(), "Both files inspected.")
        self.assert_route(server, summary, 2)
        messages = server.posts[1]["body"]["messages"]
        results = {m["tool_call_id"]: m for m in messages if m["role"] == "tool"}
        for call in calls:
            self.assertRegex(call.id, r"^call_[0-9a-f]{24}$")
            self.assertIn(files[call.arguments["path"]].strip(), results[call.id]["content"])
        cycles = tool_cycles(load(self.session()))
        self.assertEqual({c["id"] for c in cycles}, {c.id for c in calls})
        self.assertTrue(all(c["result_found"] and not c["is_error"] for c in cycles))

    def test_write_changes_file_exactly(self):
        path = self.repo / "answer.py"
        path.write_text("answer = -1\n", encoding="utf-8")
        desired = "answer = 42\n"
        call = ToolCall("write", {"i": "Correcting fixture", "path": "answer.py", "content": desired})
        server = self.server([ResponseSpec(text="", calls=[call]), ResponseSpec(text="Correction applied.")])
        summary = self.assert_success(self.run_omp(), "Correction applied.")
        self.assert_route(server, summary, 2)
        self.assertEqual(path.read_bytes(), desired.encode())
        cycle, = tool_cycles(load(self.session()))
        self.assertEqual(cycle["id"], call.id)
        self.assertTrue(cycle["result_found"])
        self.assertFalse(cycle["is_error"])
        self.assertTrue(any(m.get("tool_call_id") == call.id for m in server.posts[1]["body"]["messages"]))

    def test_bash_runs_fixture_unittest_and_returns_output(self):
        (self.repo / "test_answer.py").write_text(
            "import unittest\nclass Answer(unittest.TestCase):\n"
            "    def test_arithmetic(self):\n        self.assertEqual(6 * 7, 42)\n", encoding="utf-8")
        call = ToolCall("bash", {"i": "Testing fixture", "command": "python3 -m unittest -v", "timeout": 10})
        server = self.server([ResponseSpec(text="", calls=[call]), ResponseSpec(text="Fixture tests passed.")])
        summary = self.assert_success(self.run_omp(), "Fixture tests passed.")
        self.assert_route(server, summary, 2)
        result = next(m for m in server.posts[1]["body"]["messages"] if m.get("tool_call_id") == call.id)
        self.assertIn("test_arithmetic", result["content"])
        self.assertIn("Ran 1 test", result["content"])
        self.assertIn("OK", result["content"])
        self.assertFalse(tool_cycles(load(self.session()))[0]["is_error"])

    def test_thinking_wire_levels(self):
        # Stock OMP's OpenAI dialect maps off to the lowest effort for this
        # declared ladder; xhigh is clamped to its highest advertised level.
        observed = {}
        for level, expected in (("off", "low"), ("low", "low"), ("medium", "medium"),
                                ("high", "high"), ("xhigh", "high")):
            with self.subTest(level=level):
                server = self.server([ResponseSpec(text="Observed.")])
                self.assert_success(self.run_omp(extra=["--thinking", level]), "Observed.")
                self.assertEqual(len(server.posts), 1)
                observed[level] = server.posts[0]["body"].get("reasoning_effort")
                self.assertEqual(observed[level], expected)
        print("G03 reasoning_effort " + json.dumps(observed, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
