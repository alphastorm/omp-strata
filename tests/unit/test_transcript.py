"""Consumer-visible session evidence invariants, including damaged history."""
import json
import tempfile
import unittest
from pathlib import Path

from omp_strata.transcript import find_sessions, load, summarize, tool_cycles


def entry(message):
    return {"type": "message", "message": message}


def assistant(calls=(), **extra):
    return entry({"role": "assistant", "provider": "strata-local", "model": "fixture", "api": "openai-completions",
                  "content": [{"type": "toolCall", "id": call_id, "name": name, "arguments": {"path": "fixture.txt"}}
                              for call_id, name in calls], "stopReason": "toolUse" if calls else "stop", **extra})


def result(call_id, name="read", text="fixture payload", is_error=False):
    return entry({"role": "toolResult", "toolCallId": call_id, "toolName": name,
                  "content": [{"type": "text", "text": text}], "isError": is_error})


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.directory = self.home / ".omp" / "profiles" / "omp-strata" / "agent" / "sessions" / "fixture"
        self.directory.mkdir(parents=True)
        self.path = self.directory / "session.jsonl"

    def save(self, entries):
        self.path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

    def test_parallel_calls_associate_by_id_and_name_not_result_order(self):
        entries = [assistant([("call_a", "read"), ("call_b", "bash")]),
                   result("call_b", "bash", "test failed", True), result("call_a"), assistant()]
        self.save(entries)
        cycles = tool_cycles(load(self.path))
        self.assertEqual(cycles, [
            {"id": "call_a", "name": "read", "arguments": {"path": "fixture.txt"}, "result_text": "fixture payload",
             "is_error": False, "result_found": True},
            {"id": "call_b", "name": "bash", "arguments": {"path": "fixture.txt"}, "result_text": "test failed",
             "is_error": True, "result_found": True},
        ])
        summary = summarize(self.path)
        self.assertEqual(summary["stopReasons"], ["toolUse", "stop"])
        self.assertEqual(summary["tool_errors"], 1)
        self.assertEqual(summary["orphan_results"], [])
        self.assertEqual(summary["calls_without_results"], [])

    def test_orphan_duplicate_wrong_name_and_missing_results_remain_visible(self):
        self.save([result("before"), assistant([("call_a", "read"), ("call_b", "read")]),
                   result("call_a", "bash"), result("call_a"), result("call_a"),
                   assistant([("call_a", "read"), ("invalid id", "read")])])
        summary = summarize(self.path)
        self.assertEqual(summary["orphan_results"], ["before", "call_a", "call_a"])
        self.assertEqual(summary["calls_without_results"], ["call_b", "call_a", "invalid id"])
        self.assertFalse(summary["tool_ids_unique"])
        self.assertFalse(summary["tool_ids_well_formed"])

    def test_usage_includes_auxiliary_calls_without_counting_them_as_chat_turns(self):
        self.save([{"type": "title", "title": "fixture", "pad": " "}, {"type": "session", "version": 3},
                   assistant(usage={"input": 10, "output": 4, "cacheRead": 20, "totalTokens": 34}),
                   {"type": "model_usage", "provider": "strata-local", "model": "fixture", "api": "openai-completions",
                    "usage": {"input": 3, "output": 2, "cacheRead": 5, "cacheWrite": 1, "totalTokens": 11,
                              "reasoningTokens": 2}}])
        summary = summarize(self.path)
        self.assertEqual(summary["assistant_count"], 1)
        self.assertEqual(summary["providers"], ["strata-local"])
        self.assertEqual(summary["models"], ["fixture"])
        self.assertEqual(summary["apis"], ["openai-completions"])
        self.assertEqual(summary["usage"], {"input": 13, "output": 6, "cacheRead": 25, "cacheWrite": 1,
                                            "totalTokens": 45, "reasoningTokens": 2})

    def test_jsonl_damage_is_not_silently_reported_as_a_success(self):
        for text in ('{"type":"session"}\n{"type":', '{"type":"session"}\n[]\n'):
            self.path.write_text(text, encoding="utf-8")
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "line 2"):
                summarize(self.path)

    def test_finding_sessions_ignores_other_profiles_and_artifact_json(self):
        self.save([assistant()])
        unrelated = self.home / ".omp" / "agent" / "sessions" / "elsewhere.jsonl"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("{}\n", encoding="utf-8")
        (self.directory / "metadata.json").write_text("{}", encoding="utf-8")
        artifacts = self.directory / "session"
        artifacts.mkdir()
        (artifacts / "tool-output.jsonl").write_text("{}\n", encoding="utf-8")
        self.assertEqual(find_sessions(self.home), [self.path])
        self.assertEqual(find_sessions(self.home / "absent"), [])


if __name__ == "__main__":
    unittest.main()
