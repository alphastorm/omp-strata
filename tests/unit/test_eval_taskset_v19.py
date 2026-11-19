from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts.eval_taskset import TasksetEventCounts, agent_env


class EvalV19Tests(unittest.TestCase):
    def test_taskset_pause_is_not_completion(self):
        for marker in ({}, {"isTerminal": True}):
            counts = TasksetEventCounts()
            counts.observe({"type": "agent_end", "isTerminal": False})
            self.assertFalse(counts.completed)
            counts.observe({"type": "agent_end", **marker})
            self.assertTrue(counts.completed)

    def test_arm_environment_cannot_override_v19_codex_pin(self):
        with tempfile.TemporaryDirectory() as home:
            ctx = SimpleNamespace(agent_path="bin", agent_env={"PI_AI_CODEX_CLIENT_VERSION": ""})
            for version, expected in (("18.18.3", ""), ("19.0.0", "0.169.0")):
                layout = SimpleNamespace(omp_home=Path(home), profile=SimpleNamespace(data={"omp": {"version": version}}))
                self.assertEqual(agent_env(ctx, layout, "fixture")["PI_AI_CODEX_CLIENT_VERSION"], expected)
