"""G12/G17: near OMP's compaction threshold the client sends the engine only the agent's own turns.

Stock OMP compacts speculatively once a session enters the band below its compaction threshold: it sends the same
model a background summary request. Strata serves one sequence, and the integration allows one in-flight request,
so on the PRO (G17, 2026-10-07) that request held the agent's next turn for 17 s and replaced the 105K-token live
prefix the turn would have reused. The rendered configuration must keep that request off the wire.
"""
import json
import unittest

from omp_strata.ompcfg import CONTEXT_SAFETY_TOKENS, install_profile_config
from tests.mock.scripted_server import OmpTestCase, ResponseSpec, ScriptedServer, ToolCall


class SpeculativeCompactionGate(OmpTestCase):
    def test_turn_inside_the_speculation_band_sends_no_summary_request(self):
        window = self.layout.profile.data["omp"]["context_window"] - CONTEXT_SAFETY_TOKENS
        # Stock OMP's default threshold is 85 % of the window and speculation starts 12.5 % of the threshold below
        # it (at least 8,192 tokens): 80 % of the window is inside that band and below the threshold.
        near = int(window * 0.80)
        (self.repo / "notes.txt").write_text("fixture notes\n", encoding="utf-8")

        def respond(body):
            roles = [message.get("role") for message in body["messages"]]
            if "tool" not in roles:
                return ResponseSpec(text="", calls=[ToolCall("read", {"i": "Reading notes", "path": "notes.txt"})],
                                    prompt_tokens=near, cached_tokens=0, completion_tokens=40)
            if roles[-1] == "tool":
                return ResponseSpec(text="Notes read.", prompt_tokens=near + 60, cached_tokens=near,
                                    completion_tokens=10)
            return ResponseSpec(text="Summary of the session.", prompt_tokens=near, cached_tokens=0,
                                completion_tokens=200)

        server = ScriptedServer([], model=self.layout.profile.data["strata"]["model_name"], response_factory=respond)
        self.addCleanup(server.close)
        install_profile_config(self.layout, base_url=server.base_url)
        summary = self.assert_success(self.run_omp(), "Notes read.")
        roles = [[message.get("role") for message in post["body"]["messages"]] for post in server.posts]
        print("G17 speculation " + json.dumps({"near_tokens": near, "posts": len(roles),
                                               "last_roles": [r[-1] for r in roles]}))
        self.assertEqual(summary["stopReasons"], ["toolUse", "stop"])
        self.assertEqual(len(roles), 2, "a request other than the agent's two turns reached the engine")
        self.assertNotIn("tool", roles[0])
        self.assertEqual(roles[1][-1], "tool")


if __name__ == "__main__":
    unittest.main()
