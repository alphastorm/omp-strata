from pathlib import Path
import tempfile
import os
import subprocess
import sys
from types import SimpleNamespace
import unittest

from scripts.eval_taskset import TasksetEventCounts, agent_env, sandbox_profile, sandboxed


class EvalV19Tests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "darwin", "requires macOS sandbox-exec")
    def test_agent_can_dial_only_its_own_slot_socket(self):
        import socket
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root = Path(tmp)
            layout = SimpleNamespace(omp_home=root / "home", profile=SimpleNamespace(data={"omp": {"version": "19.2.1"}}))
            ctx = SimpleNamespace(agent_path=os.environ["PATH"], agent_env={"OMP_DAEMON_DIR": "/foreign",
                                                                          "OMP_DAEMON_TCP": "localhost:9"})
            env = agent_env(ctx, layout, "fixture")
            self.assertNotIn("OMP_DAEMON_TCP", env)
            directory = Path(env["OMP_DAEMON_DIR"])
            self.assertTrue(directory.is_relative_to(layout.omp_home))
            directory.mkdir()
            endpoint = directory / "daemon.sock"
            profile = root / "agent.sb"
            profile.write_text(sandbox_profile(root, slot_socket=endpoint))
            for path, allowed in ((endpoint, True), (directory / "other.sock", False)):
                with socket.socket(socket.AF_UNIX) as listener:
                    listener.bind(str(path))
                    listener.listen()
                    client = [sys.executable, "-c", "import socket,sys; socket.socket(socket.AF_UNIX).connect(sys.argv[1])", str(path)]
                    proc = subprocess.run(sandboxed(client, profile), stdin=subprocess.DEVNULL, capture_output=True)
                    self.assertEqual(proc.returncode == 0, allowed, proc.stderr)
            layout.omp_home = root / ("x" * 100)
            with self.assertRaisesRegex(ValueError, "shorter --out"):
                agent_env(ctx, layout, "fixture")

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
            for version, expected in (("18.18.3", ""), ("19.0.0", "0.169.0"), ("19.2.1", "0.169.0")):
                layout = SimpleNamespace(omp_home=Path(home), profile=SimpleNamespace(data={"omp": {"version": version}}))
                self.assertEqual(agent_env(ctx, layout, "fixture")["PI_AI_CODEX_CLIENT_VERSION"], expected)
