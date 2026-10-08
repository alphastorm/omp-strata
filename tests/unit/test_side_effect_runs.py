"""G14 and G16 count how often stock OMP ran the fixture's side-effecting script, from the session transcript.

The count must be runs, not mentions: on 2026-10-08 the RTX PRO 6000's G16 failed because the model read append.py
before running it once (log.txt had one line), and the gate counted the read as a second run.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import realhost_gates as gates


class SideEffectRuns(unittest.TestCase):
    def session(self, calls: list[tuple[str, dict]]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "session.jsonl"
        entries = []
        for index, (name, arguments) in enumerate(calls):
            call_id = f"call_{index:024x}"
            entries.append({"type": "message", "message": {
                "role": "assistant", "stopReason": "toolUse",
                "content": [{"type": "toolCall", "id": call_id, "name": name, "arguments": arguments}]}})
            entries.append({"type": "message", "message": {
                "role": "toolResult", "toolCallId": call_id, "toolName": name,
                "content": [{"type": "text", "text": "ok"}], "isError": False}})
        path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")
        return path

    def test_inspecting_the_script_is_not_running_it(self):
        session = self.session([("read", {"path": "append.py"}), ("bash", {"command": "cat append.py"}),
                                ("glob", {"path": "."}), ("bash", {"command": "python append.py"}),
                                ("read", {"path": "NONCE.txt"})])
        self.assertEqual(gates.count_runs(session, "append.py"), 1)

    def test_every_python_invocation_of_the_script_counts(self):
        session = self.session([("bash", {"command": "python append.py"}),
                                ("bash", {"command": "py -u .\\append.py && type log.txt"}),
                                ("bash", {"command": "C:\\Python313\\python.exe \"append.py\""}),
                                ("bash", {"command": "python3 ./append.py"}),
                                ("bash", {"command": "python3.13 -u append.py"})])
        self.assertEqual(gates.count_runs(session, "append.py"), 5)

    def test_a_similarly_named_script_is_not_this_script(self):
        session = self.session([("bash", {"command": "python append.pyc"}),
                                ("bash", {"command": "python not_append.py"})])
        self.assertEqual(gates.count_runs(session, "append.py"), 0)

    def test_no_session_has_no_runs(self):
        self.assertEqual(gates.count_runs(None, "append.py"), 0)


if __name__ == "__main__":
    unittest.main()
