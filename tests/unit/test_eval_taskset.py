"""Task-set evaluator: the agent sandbox contract, the task fairness gate and run bookkeeping."""
import contextlib
import importlib.util
import io
import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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

    def test_a_verdict_keeps_the_checks_that_failed(self):
        # Big verifiers report hundreds of checks; the record must still name the ones that failed.
        verify = ('import json; checks = [{"name": f"c{i}", "passed": i != 70} for i in range(80)]\n'
                  'print(json.dumps({"passed": False, "score": 79 / 80, "checks": checks}))\n')
        with tempfile.TemporaryDirectory(dir=Path.home() / "Library" / "Caches") as directory:
            root = Path(directory).resolve()
            self.make_task(root, "many-checks", reference_answer="42\n", verify=verify)
            ctx = taskset.context(SimpleNamespace(taskset=str(root), out=None))
            task = taskset.load_task(ctx.taskset, "many-checks")
            workspace = taskset.materialize(ctx.taskset, task, root / "attempt" / "workspace")
            verdict = taskset.verify(ctx, task, workspace, root / "attempt")
        self.assertIn({"name": "c70", "passed": False}, verdict["checks"])
        self.assertEqual(verdict["checks_total"], 80)


class SharedRunTests(unittest.TestCase):
    """Several `run` invocations (one per host) share one output tree through claim files."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def scheduler(self, tasks: list[str]):
        return taskset.Scheduler(SimpleNamespace(out=self.out), tasks, ["arm"])

    def test_concurrent_runs_never_take_the_same_attempt(self):
        first, second = self.scheduler(["t1", "t2"]), self.scheduler(["t1", "t2"])
        self.assertEqual(first.claim("arm"), "t1")
        self.assertEqual(second.claim("arm"), "t2")
        self.assertIsNone(second.claim("arm"))  # t1 belongs to the live first run

    def test_an_attempt_finished_elsewhere_is_not_rerun(self):
        # A rerun would rename the finished attempt aside and replace its result.
        first, second = self.scheduler(["t1"]), self.scheduler(["t1"])
        self.assertEqual(first.claim("arm"), "t1")
        (self.out / "arm" / "t1").mkdir()
        (self.out / "arm" / "t1" / "result.json").write_text("{}")
        first.unclaim("arm", "t1")
        self.assertIsNone(second.claim("arm"))

    def test_a_killed_runs_claim_is_taken_over(self):
        child = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True,
                               text=True, check=True)
        (self.out / "arm").mkdir()
        (self.out / "arm" / ".t1.claim").write_text(json.dumps({"pid": int(child.stdout)}))
        self.assertEqual(self.scheduler(["t1"]).claim("arm"), "t1")

    def test_a_connection_lost_during_an_attempt_reruns_it_instead_of_scoring_it(self):
        key = self.out / "key"
        key.write_text("k" * 32)
        key.chmod(0o600)
        arms = {"hosts": {"h": {"order": ["a"]}}, "arms": {"a": {"placements": ["p"], "model": "m"}},
                "placements": {"p": {"host": "h", "activate": ["true"], "key_file": str(key)}}}
        scheduler = taskset.Scheduler(SimpleNamespace(out=self.out, arms=arms), ["t1"], ["a"])
        tunnels, attempts = [], []

        class FakeTunnel:  # the ssh -L child: ensure() (re)opens it, as the real one does
            def __init__(self, placement, log):
                self.up = False
                tunnels.append(self)

            def alive(self):
                return self.up

            def ensure(self, key, model):
                self.up = True
                return {"models": [model]}

            def close(self):
                self.up = False

        def attempt(ctx, arm, task, names, endpoint):
            attempts.append(task)
            (self.out / arm / task).mkdir(parents=True)
            if len(attempts) == 1:
                tunnels[0].up = False  # the agent's stream breaks; the engine itself stays healthy
            return {"passed": len(attempts) > 1, "agent_wall_ms": 0, "abort_reason": None, "tool_calls": 0}

        with mock.patch.object(taskset, "Tunnel", FakeTunnel), mock.patch.object(taskset, "run_attempt", attempt), \
                contextlib.redirect_stdout(io.StringIO()):
            scheduler.host_worker("h")
        self.assertEqual(attempts, ["t1", "t1"])
        self.assertTrue(any(p.name.startswith("t1.infra-") for p in (self.out / "a").iterdir()))
        ends = [json.loads(line) for line in (self.out / "run.log").read_text().splitlines()]
        self.assertEqual([e["passed"] for e in ends if e["event"] == "attempt_end"], [True])


class RedactionTests(unittest.TestCase):
    def test_unreadable_files_left_by_the_agent_do_not_abort_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            (attempt / "events.jsonl").write_text('{"key": "sk-test-123"}')
            locked = attempt / "locked.ts"
            locked.write_text("x")
            locked.chmod(0)
            try:
                self.assertEqual(taskset.redact(attempt, "sk-test-123"), 1)
            finally:
                locked.chmod(0o600)
            self.assertNotIn("sk-test-123", (attempt / "events.jsonl").read_text())


class PairedStatisticsTests(unittest.TestCase):
    def test_exact_mcnemar(self):
        self.assertEqual(taskset.mcnemar_p(0, 0), 1.0)
        self.assertEqual(taskset.mcnemar_p(3, 3), 1.0)
        self.assertAlmostEqual(taskset.mcnemar_p(0, 5), 0.0625)
        self.assertAlmostEqual(taskset.mcnemar_p(1, 9), 0.021484375)
        self.assertEqual(taskset.mcnemar_p(2, 8), taskset.mcnemar_p(8, 2))


class SummaryTests(unittest.TestCase):
    def test_attempts_moved_aside_are_not_scored(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)

            def record(arm, dirname, passed):
                (out / arm / dirname).mkdir(parents=True)
                (out / arm / dirname / "result.json").write_text(json.dumps({
                    "arm": arm, "task": "t1", "passed": passed, "track": "dev", "family": "f", "difficulty": "hard",
                    "agent_wall_ms": 1000, "output_tokens": 1, "abort_reason": None, "verifier_error": False,
                    "tamper": None}))

            record("a", "t1", True)
            record("a", "t1.infra-1", False)  # an infrastructure fault kept for inspection, then rerun
            record("b", "t1.infra-1", False)  # its rerun has not finished yet
            arms = taskset.summarize(out)["arms"]
            self.assertEqual(sorted(arms), ["a"])
            self.assertEqual(arms["a"]["all"], {"passed": 1, "n": 1})



if __name__ == "__main__":
    unittest.main()
