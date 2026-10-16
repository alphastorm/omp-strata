"""Task-set evaluator: the agent sandbox contract, the task fairness gate and run bookkeeping."""
import contextlib
import importlib.util
import io
import json
import os
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


class RunPrecheckTests(unittest.TestCase):
    """Real local fixtures must pass the fairness gate before a run touches any host."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.task_root = self.root / "taskset"
        self.out = self.root / "results"
        self.arms_path = self.root / "arms.json"
        self.activate = [sys.executable, "-c", "pass"]
        self.arms = {
            "agent_path": str(Path(sys.executable).parent) + os.pathsep + "/usr/bin:/bin",
            "agent_env": {"EVAL_FIXTURE": "offline"}, "sandbox_deny": [str(self.root / "denied")],
            "hosts": {"h": {"order": ["a"]}}, "arms": {"a": {"placements": ["p"], "model": "m"}},
            "placements": {"p": {"host": "h", "activate": self.activate, "key_file": "unused"}}}
        self.arms_path.write_text(json.dumps(self.arms))
        patches = {
            "load_arms": {"side_effect": taskset.read_json},
            # Keep materialization, reference application and the verifier real on every test platform.
            "sandboxed": {"side_effect": lambda argv, profile: argv},
            "verify": {"wraps": taskset.verify},
            "sandbox_profile": {"wraps": taskset.sandbox_profile},
            "run_bounded": {"wraps": taskset.run_bounded},
            "take_pid_file": {"wraps": taskset.take_pid_file},
            "HOST_LOCKS": {"new": self.root / "host-locks"},
            "read_key": {"return_value": "k" * 32},
            "Tunnel": {},
            "run_attempt": {"side_effect": self.attempt},
        }
        self.mocks = {}
        for name, options in patches.items():
            patcher = mock.patch.object(taskset, name, **options)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)
        self.mocks["Tunnel"].return_value.alive.return_value = True
        self.mocks["Tunnel"].return_value.ensure.return_value = {"models": ["m"]}
        pool = mock.patch.object(taskset.concurrent.futures, "ThreadPoolExecutor",
                                 wraps=taskset.concurrent.futures.ThreadPoolExecutor)
        self.pool = pool.start()
        self.addCleanup(pool.stop)

    def make_task(self, task_id, *, answer="42", seed=None, track="private", verifier=None):
        directory = self.task_root / "tasks" / task_id
        (directory / "workspace" / "out").mkdir(parents=True)
        (directory / "reference" / "out").mkdir(parents=True)
        if seed is not None:
            (directory / "workspace" / "answer.txt").write_text(seed)
        (directory / "reference" / "answer.txt").write_text(answer)
        (directory / "prompt.md").write_text("Write 42 in answer.txt.\n")
        code = ('import os, pathlib\n'
                'assert os.environ["EVAL_FIXTURE"] == "offline"\n'
                'answer = pathlib.Path("answer.txt")\n'
                'ok = answer.is_file() and answer.read_text() == "42"\n'
                'if not ok: print("wrong fixture answer\\nsecond detail\\nthird detail\\nfourth detail")\n'
                'raise SystemExit(0 if ok else 1)\n')
        (directory / "task.json").write_text(json.dumps({
            "id": task_id, "track": track, "workspace": {"kind": "dir"},
            "budget": {"wall_seconds": 60, "tool_calls": 5},
            "verify": verifier or {"kind": "commands", "commands": [[sys.executable, "-c", code]],
                                    "timeout_seconds": 30}}))

    def attempt(self, ctx, arm, task, names, endpoint):
        record = {"passed": True, "agent_wall_ms": 0, "abort_reason": None, "tool_calls": 0}
        directory = ctx.out / arm / task
        directory.mkdir(parents=True)
        (directory / "result.json").write_text(json.dumps(record))
        return record

    def run_main(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            status = taskset.main(["run", "--taskset", str(self.task_root), "--arms", str(self.arms_path),
                                   "--out", str(self.out), *extra])
        events = [json.loads(line) for line in (self.out / "run.log").read_text().splitlines()]
        return status, events

    def assert_no_dispatch(self):
        self.mocks["take_pid_file"].assert_not_called()
        self.mocks["Tunnel"].assert_not_called()
        self.mocks["run_attempt"].assert_not_called()
        self.assertFalse(any(call.args[0] == self.activate for call in self.mocks["run_bounded"].call_args_list))

    def test_a_failing_selected_reference_stops_before_host_side_effects(self):
        self.make_task("fair")
        self.make_task("wrong-reference", answer="41")
        self.make_task("unselected")
        status, events = self.run_main("--task", "fair", "--task", "wrong-reference")
        self.assertNotEqual(status, 0)
        self.assertEqual([event["event"] for event in events], ["run_start", "precheck_failed"])
        self.assertFalse(events[0]["skip_precheck"])
        self.assertEqual(events[-1]["tasks"], ["wrong-reference"])
        self.assertEqual(events[-1]["details"][0]["reference"]["detail"],
                         ["wrong fixture answer", "second detail", "third detail"])
        self.assertCountEqual([call.args[1]["id"] for call in self.mocks["verify"].call_args_list],
                              ["fair", "fair", "wrong-reference", "wrong-reference"])
        self.assert_no_dispatch()

    def test_a_passing_precheck_uses_the_run_environment_then_dispatches(self):
        self.make_task("fair")
        self.make_task("unselected", answer="41")
        status, events = self.run_main("--task", "fair")
        self.assertEqual(status, 0)
        self.assertEqual([event["event"] for event in events],
                         ["run_start", "precheck_ok", "activate", "attempt_start", "attempt_end", "run_end"])
        self.assertFalse(events[0]["skip_precheck"])
        self.assertEqual(events[1]["tasks"], 1)
        self.assertGreaterEqual(events[1]["wall_ms"], 0)
        self.pool.assert_called_once_with(max_workers=4)
        self.mocks["run_attempt"].assert_called_once()
        ctx = self.mocks["run_attempt"].call_args.args[0]
        self.assertEqual(ctx.agent_path, self.arms["agent_path"])
        self.assertEqual(ctx.agent_env, self.arms["agent_env"])
        self.assertEqual(ctx.deny, [Path(self.arms["sandbox_deny"][0]), self.task_root, self.out])
        self.assertEqual(self.mocks["verify"].call_count, 2)
        for call in self.mocks["verify"].call_args_list:
            self.assertIs(call.args[0], ctx)
            self.assertEqual(call.args[1]["id"], "fair")
        for call in self.mocks["sandbox_profile"].call_args_list:
            self.assertEqual(call.kwargs["deny"], ctx.deny)

    def test_skip_precheck_dispatches_and_records_the_opt_out(self):
        self.make_task("wrong-reference", answer="41")
        status, events = self.run_main("--skip-precheck")
        self.assertEqual(status, 0)
        self.assertTrue(events[0]["skip_precheck"])
        self.assertFalse(any(event["event"].startswith("precheck_") for event in events))
        self.mocks["verify"].assert_not_called()
        self.mocks["run_attempt"].assert_called_once()
        self.assertTrue(any(call.args[0] == self.activate for call in self.mocks["run_bounded"].call_args_list))

    def test_a_check_error_is_logged_without_skipping_other_selected_checks(self):
        self.make_task("invalid", track="unknown")
        self.make_task("fair")
        status, events = self.run_main("--task", "invalid", "--task", "fair")
        self.assertNotEqual(status, 0)
        self.assertEqual(events[-1]["event"], "precheck_failed")
        self.assertEqual(events[-1]["tasks"], ["invalid"])
        self.assertIn("EvalError: invalid: invalid task", events[-1]["details"][0]["error"])
        self.assertEqual(self.mocks["verify"].call_count, 2)
        self.assert_no_dispatch()

    def test_a_verifier_error_is_a_precheck_failure(self):
        self.make_task("broken-verifier", verifier={
            "kind": "script", "argv": [sys.executable, "-c", "print('invalid verdict')"]})
        status, events = self.run_main()
        self.assertNotEqual(status, 0)
        self.assertEqual(events[-1]["event"], "precheck_failed")
        self.assertEqual(events[-1]["tasks"], ["broken-verifier"])
        self.assertTrue(events[-1]["details"][0]["reference"]["verifier_error"])
        self.assert_no_dispatch()

    def test_a_seed_that_already_passes_is_rejected(self):
        self.make_task("lenient", seed="42")
        status, events = self.run_main()
        self.assertNotEqual(status, 0)
        self.assertEqual(events[-1]["event"], "precheck_failed")
        self.assertTrue(events[-1]["details"][0]["seed"]["passed"])
        self.assert_no_dispatch()

    def test_check_keeps_its_reports_parallelism_and_summary(self):
        self.make_task("fair")
        self.make_task("wrong-reference", answer="41")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = taskset.main(["check", "--taskset", str(self.task_root), "--arms", str(self.arms_path),
                                   "--task", "fair", "--task", "wrong-reference", "--jobs", "2"])
        reports = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(status, 1)
        self.assertEqual([report["task"] for report in reports[:-1]], ["fair", "wrong-reference"])
        self.assertEqual([report["ok"] for report in reports[:-1]], [True, False])
        self.assertEqual(reports[-1], {"checked": 2, "failed": 1})
        self.assertEqual(reports[1]["reference"]["detail"],
                         "wrong fixture answer\nsecond detail\nthird detail\nfourth detail\n")
        self.pool.assert_called_once_with(max_workers=2)
        self.assert_no_dispatch()


class SharedRunTests(unittest.TestCase):
    """Several `run` invocations (one per host) share one output tree through claim files and host locks."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.locks = self.out / "host-locks"
        patcher = mock.patch.object(taskset, "HOST_LOCKS", self.locks)
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def test_a_host_another_run_is_using_is_left_alone(self):
        # A second run on the same GPU would share its engine, or switch it in the middle of an attempt.
        arms = {"hosts": {"h": {"order": ["a"]}}, "arms": {"a": {"placements": ["p"], "model": "m"}},
                "placements": {"p": {"host": "h", "activate": ["true"], "key_file": "unused"}}}
        self.locks.mkdir()
        (self.locks / "h.lock").write_text(json.dumps({"pid": os.getppid()}))  # live, and not this run
        attempts = []
        with mock.patch.object(taskset, "run_attempt", lambda *args: attempts.append(args)), \
                contextlib.redirect_stdout(io.StringIO()):
            taskset.Scheduler(SimpleNamespace(out=self.out, arms=arms), ["t1"], ["a"]).host_worker("h")
        self.assertEqual(attempts, [])
        self.assertFalse((self.out / "a" / ".t1.claim").exists())
        self.assertEqual(json.loads((self.locks / "h.lock").read_text())["pid"], os.getppid())


class RunExitStatusTests(unittest.TestCase):
    """The run status reflects result files, not the scheduler's depleted work queue."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / "results"
        task = self.root / "taskset" / "tasks" / "t1"
        task.mkdir(parents=True)
        (task / "prompt.md").write_text("Write the answer.\n")
        (task / "task.json").write_text(json.dumps({
            "id": "t1", "track": "private", "workspace": {"kind": "dir"},
            "budget": {"wall_seconds": 60, "tool_calls": 5},
            "verify": {"kind": "commands"}}))
        self.key = self.root / "key"
        self.arms = {
            "hosts": {"h": {"order": ["a"]}},
            "arms": {"a": {"placements": ["p"], "model": "m"}},
            "placements": {"p": {"host": "h", "activate": ["unused"], "key_file": str(self.key)}}}
        self.thread_errors = []
        for patcher in (
                mock.patch.object(taskset, "HOST_LOCKS", self.root / "host-locks"),
                mock.patch.object(taskset, "load_arms", return_value=self.arms),
                mock.patch.object(taskset, "run_bounded", return_value={"returncode": 0}),
                mock.patch.object(threading, "excepthook", side_effect=self.thread_errors.append)):
            patcher.start()
            self.addCleanup(patcher.stop)
        tunnel = mock.patch.object(taskset, "Tunnel")
        self.tunnel = tunnel.start().return_value
        self.addCleanup(tunnel.stop)
        self.tunnel.ensure.return_value = {"models": ["m"]}
        self.tunnel.alive.return_value = True

    def write_key(self):
        self.key.write_text("k" * 32)
        self.key.chmod(0o600)

    def run_main(self):
        with contextlib.redirect_stdout(io.StringIO()):
            status = taskset.main(["run", "--skip-precheck", "--taskset", str(self.root / "taskset"),
                                   "--arms", str(self.root / "arms.json"), "--out", str(self.out)])
        events = [json.loads(line) for line in (self.out / "run.log").read_text().splitlines()]
        return status, events

    def assert_missing_result(self, status, events):
        self.assertFalse((self.out / "a" / "t1" / "result.json").exists())
        self.assertNotEqual(status, 0, "run exited 0 without the scheduled attempt's result")
        self.assertEqual(events[-1]["event"], "run_end")
        self.assertEqual(events[-1]["missing_results"], {"a": ["t1"]})
        self.assertFalse((self.out / "a" / ".t1.claim").exists())
        self.assertEqual(self.thread_errors, [])

    def test_missing_key_before_dispatch_fails_the_run_and_logs_the_pair(self):
        with mock.patch.object(taskset, "run_attempt") as attempt:
            status, events = self.run_main()
        attempt.assert_not_called()
        self.assert_missing_result(status, events)
        errors = [event for event in events if event.get("error")]
        self.assertEqual(len(errors), 1)
        self.assertEqual((errors[0]["arm"], errors[0]["task"]), ("a", "t1"))
        self.assertIn("FileNotFoundError", errors[0]["error"])

    def test_harness_exception_during_attempt_fails_the_run(self):
        self.write_key()
        with mock.patch.object(taskset, "run_attempt", side_effect=RuntimeError("harness failed")) as attempt:
            status, events = self.run_main()
        attempt.assert_called_once()
        self.assert_missing_result(status, events)
        errors = [event for event in events if event["event"] == "attempt_error"]
        self.assertEqual([(event["arm"], event["task"]) for event in errors], [("a", "t1")])
        self.assertIn("RuntimeError", errors[0]["error"])

    def failed_attempt(self, ctx, arm, task, names, endpoint):
        record = {"passed": False, "agent_wall_ms": 0, "abort_reason": None, "tool_calls": 0}
        directory = ctx.out / arm / task
        directory.mkdir(parents=True)
        (directory / "result.json").write_text(json.dumps(record))
        return record

    def test_failed_verification_with_a_result_still_exits_zero(self):
        self.write_key()
        with mock.patch.object(taskset, "run_attempt", side_effect=self.failed_attempt) as attempt:
            status, events = self.run_main()
        attempt.assert_called_once()
        self.assertEqual(status, 0)
        self.assertEqual(events[-1]["missing_results"], {})
        self.assertEqual(self.thread_errors, [])

    def test_a_live_claim_elsewhere_is_still_missing_until_its_result_exists(self):
        claim = self.out / "a" / ".t1.claim"
        claim.parent.mkdir(parents=True)
        claim.write_text(json.dumps({"pid": os.getpid()}))
        with mock.patch.object(taskset, "run_attempt") as attempt:
            status, events = self.run_main()
        attempt.assert_not_called()
        self.assertNotEqual(status, 0)
        self.assertEqual(events[-1]["unscheduled"], {})
        self.assertEqual(events[-1]["missing_results"], {"a": ["t1"]})
        self.assertTrue(claim.is_file())  # Do not release another worker's claim.
        self.assertEqual(self.thread_errors, [])

    def test_finished_attempt_is_not_rerun(self):
        result = self.out / "a" / "t1" / "result.json"
        result.parent.mkdir(parents=True)
        result.write_text('{"passed": false}\n')
        with mock.patch.object(taskset, "run_attempt") as attempt:
            status, events = self.run_main()
        attempt.assert_not_called()
        self.assertEqual(status, 0)
        self.assertEqual(events[-1]["missing_results"], {})
        self.assertEqual(result.read_text(), '{"passed": false}\n')

    def test_an_endpoint_failure_retries_only_once_and_keeps_the_second_result(self):
        self.write_key()
        self.tunnel.alive.return_value = False
        with mock.patch.object(taskset, "run_attempt", side_effect=self.failed_attempt) as attempt:
            status, events = self.run_main()
        self.assertEqual(attempt.call_count, 2)
        self.assertEqual(status, 0)
        self.assertEqual(events[-1]["missing_results"], {})
        self.assertEqual(sum(event["event"] == "attempt_infra_retry" for event in events), 1)
        self.assertEqual(len(list((self.out / "a").glob("t1.infra-*/result.json"))), 1)
        self.assertEqual(self.thread_errors, [])

    def test_unexpected_post_attempt_failure_is_logged_with_the_pair(self):
        self.write_key()
        self.tunnel.ensure.side_effect = [{"models": ["m"]}, RuntimeError("endpoint check failed")]
        with mock.patch.object(taskset, "run_attempt", side_effect=self.failed_attempt):
            status, events = self.run_main()
        self.assertEqual(status, 0)  # The attempt produced its result before the endpoint check failed.
        self.assertEqual(events[-1]["missing_results"], {})
        errors = [event for event in events if event.get("error")]
        self.assertEqual([(event["arm"], event["task"]) for event in errors], [("a", "t1")])
        self.assertFalse((self.out / "a" / ".t1.claim").exists())
        self.assertEqual(self.thread_errors, [])


class GenericEndpointTests(unittest.TestCase):
    def test_every_role_goes_to_the_one_local_endpoint_with_the_arms_limits(self):
        profile = taskset.load_profile(ROOT / "profiles" / "win11-rtx4090-iq3s-131k-strata0.1.38-omp18.5.0.json")
        arm = {"api": "openai-completions", "provider": "llamacpp-a", "model": "ling-fin-q4",
               "key_env": "EVAL_LLAMACPP_KEY", "_profile": profile,
               "model_entry": {"contextWindow": 60000, "maxTokens": 8192, "reasoning": False,
                               "compat": {"supportsReasoningEffort": False}}}
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            ctx = SimpleNamespace(agent_path="/usr/bin:/bin", agent_env={}, omp_binary=Path(directory) / "omp")
            argv, env = taskset.omp_launch(ctx, arm, {"local_port": 18400}, home, "k" * 32)
            agent = home / ".omp" / "profiles" / taskset.OMP_PROFILE / "agent"
            settings = json.loads((agent / "config.yml").read_text())
            models = json.loads((agent / "models.yml").read_text())
        self.assertEqual(set(settings["modelRoles"].values()), {"llamacpp-a/ling-fin-q4"})
        self.assertEqual(argv[argv.index("--model") + 1], "llamacpp-a/ling-fin-q4")
        (provider, entry), = models["providers"].items()
        self.assertEqual((provider, entry["baseUrl"], entry["apiKey"]),
                         ("llamacpp-a", "http://127.0.0.1:18400/v1", "EVAL_LLAMACPP_KEY"))
        model = entry["models"][0]
        self.assertEqual((model["id"], model["contextWindow"], model["maxTokens"], model["reasoning"]),
                         ("ling-fin-q4", 60000, 8192, False))
        # Overrides merge into the compat block; flags the arm leaves alone keep Strata's values.
        self.assertEqual((model["compat"]["supportsReasoningEffort"], model["compat"]["maxTokensField"]),
                         (False, "max_tokens"))
        self.assertEqual(env["EVAL_LLAMACPP_KEY"], "k" * 32)
        self.assertNotIn("STRATA_API_KEY", env)


class FleetTranscriptTests(unittest.TestCase):
    def test_compaction_drops_only_tool_progress(self):
        lines = ['{"type":"message_end","message":{"role":"assistant","content":[]}}',
                 '{"type":"tool_execution_update","toolCallId":"c1","toolName":"task","partial":"x"}',
                 '{"type":"tool_execution_end","toolCallId":"c1","result":"tool_execution_update"}',
                 '{"type":"message_end","message":{"role":"toolResult","content":[]}}']
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "phase-1.events.jsonl"
            events.write_text("\n".join(lines) + "\n")
            taskset.drop_progress_events(events)
            self.assertEqual(events.read_text().splitlines(), [lines[0], lines[2], lines[3]])


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
