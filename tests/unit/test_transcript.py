"""Consumer-visible session evidence invariants, including damaged history."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from omp_strata import transcript
from omp_strata.transcript import find_sessions, load, summarize, tool_cycles
from scripts import realhost_gates, remote_gates


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

    def session_copy(self, name, session_id, entries, *, continuation=None, parent=None):
        path = self.directory / (name + ".jsonl")
        header = {"type": "session", "version": 3, "id": session_id, "cwd": str(self.home / "work"),
                  "timestamp": "2026-10-28T10:00:00.000Z"}
        if continuation:
            header.update(continuationOf=continuation, parentSession=continuation)
        elif parent:
            header["parentSession"] = parent
        path.write_text("\n".join(json.dumps(e) for e in [header, *entries]) + "\n", encoding="utf-8")
        return path

    def turn(self, entry_id, minute):
        return dict(assistant(), id=entry_id, timestamp=f"2026-10-28T10:{minute:02d}:00.000Z")

    def linked_copies(self):
        first_turn = self.turn("turn-one", 1)
        original = self.session_copy("original", "original-id", [
            first_turn, {"type": "session_exit", "timestamp": "2026-10-28T11:00:00.000Z"}])
        continued = self.session_copy("continued", "continued-id", [
            first_turn, self.turn("turn-two", 2)], continuation="original-id")
        os.utime(original, (2_000_000_000, 2_000_000_000))
        os.utime(continued, (1_999_999_000, 1_999_999_000))
        return original, continued

    def test_linked_session_uses_newest_turn_not_a_later_parent_exit_or_mtime(self):
        _, continued = self.linked_copies()
        self.assertEqual([continued], find_sessions(self.home))
        layout = SimpleNamespace(omp_home=self.home)
        self.assertEqual(continued, realhost_gates.session_for(layout, self.home / "work"))

    def test_links_are_transitive_but_deliberate_forks_are_separate_conversations(self):
        _, continued = self.linked_copies()
        newest = self.session_copy("newest", "newest-id", [self.turn("turn-three", 3)],
                                   continuation="continued-id")
        fork = self.session_copy("fork", "fork-id", [self.turn("fork-turn", 4)], parent="original-id")
        self.assertEqual(sorted([newest, fork]), find_sessions(self.home))
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            transcript.session_for(self.home, self.home / "work")
        self.assertTrue(transcript.continues_session(continued, newest))
        self.assertFalse(transcript.continues_session(continued, fork))

    def test_equal_turn_time_prefers_a_linked_descendant_holding_the_same_turn(self):
        first = self.turn("same-turn", 1)
        self.session_copy("original", "original-id", [first])
        continued = self.session_copy("continued", "continued-id", [first], continuation="original-id")
        self.assertEqual([continued], find_sessions(self.home))

    def test_divergent_equal_time_copies_fail_closed(self):
        self.session_copy("original", "original-id", [self.turn("original-turn", 1)])
        self.session_copy("continued", "continued-id", [self.turn("different-turn", 1)],
                          continuation="original-id")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            find_sessions(self.home)

    def test_cycles_and_duplicate_session_ids_fail_closed(self):
        original = self.session_copy("original", "original-id", [self.turn("original-turn", 1)],
                                     continuation="continued-id")
        self.session_copy("continued", "continued-id", [self.turn("continued-turn", 2)],
                          continuation="original-id")
        with self.assertRaisesRegex(ValueError, "cyclic"):
            find_sessions(self.home)
        original.unlink()
        self.session_copy("duplicate", "continued-id", [self.turn("duplicate-turn", 3)])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            find_sessions(self.home)

    def test_remote_turn_accepts_linked_copies_and_checks_the_requested_workspace(self):
        _, continued = self.linked_copies()
        unrelated = self.home / ".omp" / "profiles" / "omp-strata" / "agent" / "sessions" / "other"
        unrelated.mkdir()
        (unrelated / "other.jsonl").write_text(json.dumps(
            {"type": "session", "id": "other-id", "cwd": str(self.home / "other-work")}) + "\n",
            encoding="utf-8")
        session = SimpleNamespace(layout=SimpleNamespace(omp_home=self.home),
                                  route=SimpleNamespace(servers={"local": None}), run=lambda *args, **kwargs: 0)
        observed = remote_gates._turn(session, Path("fixture-omp"), self.home / "work", "fixture", "Reply.")
        self.assertEqual(continued, observed["path"])

    def test_remote_history_preservation_allows_only_linked_header_changes(self):
        first = self.turn("turn-one", 1)
        original = self.session_copy("original", "original-id", [first])
        continued = self.session_copy("continued", "continued-id", [first, self.turn("turn-two", 2)],
                                      continuation="original-id")
        before = {"path": original, "entries": load(original)}
        after = {"path": continued, "entries": load(continued)}
        self.assertTrue(remote_gates._preserves_session(before, after))
        fork = self.session_copy("fork", "fork-id", [first, self.turn("fork-turn", 3)], parent="original-id")
        self.assertFalse(remote_gates._preserves_session(before, {"path": fork, "entries": load(fork)}))
        after["entries"] = [after["entries"][0], self.turn("changed-first-turn", 1)]
        self.assertFalse(remote_gates._preserves_session(before, after))


if __name__ == "__main__":
    unittest.main()
