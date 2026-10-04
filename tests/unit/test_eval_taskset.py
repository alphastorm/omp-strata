"""Task-set evaluator: the agent sandbox contract and the task fairness gate (macOS sandbox-exec)."""
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("eval_taskset", ROOT / "scripts" / "eval_taskset.py")
taskset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(taskset)

SANDBOX = sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").exists()
VERIFY = """import json, os, pathlib
out = pathlib.Path(os.environ["WORKSPACE"]) / "out" / "answer.txt"
ok = out.is_file() and out.read_text().strip() == "42"
print(json.dumps({"passed": ok, "score": float(ok), "checks": []}))
"""


def run_sandboxed(profile: Path, script: str, cwd: Path) -> int:
    return subprocess.run(taskset.sandboxed([sys.executable, "-c", script], profile), cwd=cwd,
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=60).returncode


@unittest.skipUnless(SANDBOX, "macOS sandbox-exec required")
class SandboxContractTests(unittest.TestCase):
    def setUp(self):
        # Mirrors a run: the task set and the output tree are denied as wholes; the attempt inside is writable.
        self.tmp = Path(tempfile.mkdtemp(dir=Path.home() / "Library" / "Caches")).resolve()
        task_dir = self.tmp / "taskset" / "tasks" / "t1"
        (task_dir / "workspace" / "inputs").mkdir(parents=True)
        (task_dir / "workspace" / "inputs" / "data.csv").write_text("a,b\n")
        (task_dir / "hidden").mkdir()
        (task_dir / "hidden" / "expected.json").write_text("{}")
        self.hidden = task_dir / "hidden" / "expected.json"
        self.attempt = self.tmp / "runs" / "arm" / "t1"
        task = {"id": "t1", "dir": task_dir, "workspace": {"kind": "dir"}}
        self.workspace = taskset.materialize(self.tmp / "taskset", task, self.attempt / "workspace")
        self.profile = self.attempt / "agent.sb"
        self.profile.write_text(taskset.sandbox_profile(self.attempt, deny=[self.tmp / "taskset", self.tmp / "runs"],
                                                        read_only=[self.workspace / "inputs"]))

    def tearDown(self):
        subprocess.run(["rm", "-rf", str(self.tmp)], check=False)

    def test_tools_can_resolve_the_workspace_path(self):
        # pnpm --dir and node's realpathSync resolve strictly, statting every ancestor (here inside denied trees).
        self.assertEqual(run_sandboxed(self.profile, "import os; os.path.realpath(os.getcwd(), strict=True)",
                                       self.workspace), 0)

    def test_inputs_are_read_only_but_copies_are_ordinary_files(self):
        self.assertNotEqual(run_sandboxed(self.profile, "open('inputs/data.csv', 'a').write('x')", self.workspace), 0)
        self.assertNotEqual(run_sandboxed(self.profile, "import os; os.chmod('inputs/data.csv', 0o600)",
                                          self.workspace), 0)
        copy = ("import shutil; shutil.copy2('inputs/data.csv', 'out/data.csv'); "
                "open('out/data.csv', 'a').write('c,d\\n')")
        self.assertEqual(run_sandboxed(self.profile, copy, self.workspace), 0)
        self.assertEqual((self.workspace / "inputs" / "data.csv").read_text(), "a,b\n")

    def test_hidden_material_and_paths_outside_the_attempt_are_unreachable(self):
        self.assertNotEqual(run_sandboxed(self.profile, f"open({str(self.hidden)!r}).read()", self.workspace), 0)
        self.assertNotEqual(run_sandboxed(self.profile, f"open({str(self.tmp / 'escape.txt')!r}, 'w')",
                                          self.workspace), 0)
        self.assertFalse((self.tmp / "escape.txt").exists())

    def test_loopback_is_reachable(self):
        server = socket.create_server(("127.0.0.1", 0))
        port = server.getsockname()[1]
        threading.Thread(target=lambda: server.accept()[0].close(), daemon=True).start()
        try:
            self.assertEqual(run_sandboxed(self.profile, f"import socket; socket.create_connection(('127.0.0.1', {port}), 5)",
                                           self.workspace), 0)
        finally:
            server.close()


@unittest.skipUnless(SANDBOX, "macOS sandbox-exec required")
class FairnessGateTests(unittest.TestCase):
    def make_task(self, root: Path, task_id: str, *, reference_answer: str, verify: str = VERIFY) -> None:
        directory = root / "tasks" / task_id
        (directory / "workspace" / "inputs").mkdir(parents=True)
        (directory / "workspace" / "inputs" / "question.txt").write_text("What is six times seven?\n")
        (directory / "reference" / "out").mkdir(parents=True)
        (directory / "reference" / "out" / "answer.txt").write_text(reference_answer)
        (directory / "prompt.md").write_text("Answer inputs/question.txt in out/answer.txt.\n")
        (directory / "verify.py").write_text(verify)
        (directory / "task.json").write_text(json.dumps({
            "id": task_id, "track": "private", "family": "test", "difficulty": "easy", "summary": "test",
            "workspace": {"kind": "dir"}, "budget": {"wall_seconds": 60, "tool_calls": 5},
            "verify": {"kind": "script", "argv": [sys.executable, "verify.py"], "timeout_seconds": 30}}))

    def test_gate_accepts_a_fair_task_and_rejects_unfair_ones(self):
        with tempfile.TemporaryDirectory(dir=Path.home() / "Library" / "Caches") as directory:
            root = Path(directory).resolve()
            self.make_task(root, "fair", reference_answer="42\n")
            self.make_task(root, "wrong-reference", reference_answer="41\n")
            # A verifier the untouched seed already satisfies cannot tell a solved task from an unsolved one.
            self.make_task(root, "lenient", reference_answer="42\n",
                           verify='import json; print(json.dumps({"passed": True, "score": 1.0, "checks": []}))\n')
            ctx = taskset.context(SimpleNamespace(taskset=str(root), out=None))
            self.assertTrue(taskset.check_one(ctx, "fair")["ok"])
            self.assertFalse(taskset.check_one(ctx, "wrong-reference")["ok"])
            self.assertFalse(taskset.check_one(ctx, "lenient")["ok"])


class PairedStatisticsTests(unittest.TestCase):
    def test_exact_mcnemar(self):
        self.assertEqual(taskset.mcnemar_p(0, 0), 1.0)
        self.assertEqual(taskset.mcnemar_p(3, 3), 1.0)
        self.assertAlmostEqual(taskset.mcnemar_p(0, 5), 0.0625)
        self.assertAlmostEqual(taskset.mcnemar_p(1, 9), 0.021484375)
        self.assertEqual(taskset.mcnemar_p(2, 8), taskset.mcnemar_p(8, 2))


if __name__ == "__main__":
    unittest.main()
