"""Host-free launch checks use the runner's real argument handling."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import runpy
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scripts import publish_run, requalify
from omp_strata.common import atomic_write_json, read_json


class RequalifyExecutionTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory) / "candidate"
        self.live = False  # The stub runtime: `start`/`restart` make it live, `stop` ends it.

    def invoke(self, *options, process=None):
        argv = ["requalify", "--profile", str(self.root / "profile.json"),
                "--root", str(self.root), *options]
        with patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()), \
                patch.object(requalify.subprocess, "run", side_effect=process or self.process):
            return requalify.main()

    def process(self, argv, **kwargs):
        command = argv[2] if len(argv) > 2 else None
        if command in ("start", "restart"):
            self.live = True
        elif command == "stop":
            self.live = False
        state = "healthy" if self.live or command != "status" else "stopped"
        kwargs["stdout"].write(json.dumps({"state": state, "pass_observed": True}).encode())
        return subprocess.CompletedProcess(argv, 0)

    def files(self):
        return {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def interrupt_after_link(self):
        original = requalify.os.link
        def link(source, target):
            original(source, target)
            raise KeyboardInterrupt
        return patch.object(requalify.os, "link", side_effect=link)

    def result(self, run_id):
        return read_json(self.root / "evidence" / ("requalify-" + run_id) / "result.json")

    def test_run_id_fences_same_and_other_runs_without_overwriting_results(self):
        self.assertEqual(0, self.invoke("--run-id", "fixture-a1", "--only", "install,start"))
        result = self.result("fixture-a1")
        self.assertTrue(result["completed"])
        self.assertEqual(0, result["rc"])
        self.assertEqual(["status-before-launch", "install", "start", "stop"], [row["step"] for row in result["steps"]])
        self.assertTrue(all(row["rc"] == 0 for row in result["steps"]))
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for extra in (("--run-id", "fixture-a1"), ("--run-id", "another-a1"), ()):
            with self.subTest(extra=extra):
                self.assertEqual(2, self.invoke(*extra, "--only", "install"))
                self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_first_post_admission_write_is_explicitly_nonterminal(self):
        writes = []
        original = requalify.atomic_write_json
        def record(path, value):
            writes.append((path, value))
            original(path, value)
        with patch.object(requalify, "atomic_write_json", side_effect=record):
            self.assertEqual(0, self.invoke("--run-id", "initial", "--only", "install"))
        path, initial = writes[0]
        self.assertEqual(self.root.resolve() / "evidence/requalify-initial/result.json", path)
        self.assertIsNone(initial["rc"])
        self.assertFalse(initial["completed"])
        self.assertEqual([], initial["steps"])
        self.assertEqual(0, self.result("initial")["rc"])

    def test_earliest_post_admission_interrupt_records_terminal_result(self):
        calls = []
        with self.interrupt_after_link():
            self.assertEqual(130, self.invoke("--run-id", "admission", "--only", "install",
                                              process=lambda argv, **_kw: calls.append(argv)))
        result = self.result("admission")
        self.assertEqual(130, result["rc"])
        self.assertTrue(result["failed"])
        self.assertFalse(result["completed"])
        self.assertEqual([], calls)
        self.assertEqual([], result["steps"])  # No step ran, so there is nothing to stop.
        self.assertIsNotNone(result["finished_utc"])
        self.assertTrue((self.root / "state/requalify-run.json").is_file())

    def test_unnamed_interrupt_before_admission_completes_records_result_and_releases_fence(self):
        calls = []
        with self.interrupt_after_link():
            self.assertEqual(130, self.invoke("--only", "install",
                                              process=lambda argv, **_kw: calls.append(argv)))
        self.assertEqual([], calls)
        self.assertFalse((self.root / "state/requalify-run.json").exists())
        [result] = list((self.root / "evidence").glob("requalify-*/result.json"))
        self.assertEqual((130, [], False), (read_json(result)["rc"], read_json(result)["steps"],
                                            read_json(result)["completed"]))
        self.assertEqual([], list(self.root.rglob(".requalify-admission-*")))

    def test_unnamed_keep_running_releases_fence_while_its_runtime_runs(self):
        calls = []
        def observe(argv, **kwargs):
            calls.append(argv[2])
            return self.process(argv, **kwargs)
        self.assertEqual(0, self.invoke("--only", "install,start", "--keep-running", process=observe))
        self.assertEqual(["status", "install", "start"], calls)  # No final stop: its runtime is left running.
        self.assertFalse((self.root / "state/requalify-run.json").exists())
        # A named launch is then refused by the earlier evidence, an unnamed one by the live runtime.
        self.assertEqual(2, self.invoke("--run-id", "later-a1", "--only", "install", process=observe))
        self.assertEqual(["status", "install", "start"], calls)
        self.assertEqual(2, self.invoke("--only", "install", process=observe))
        self.assertEqual(["status", "install", "start", "status"], calls)
        self.assertTrue(self.live)
        self.assertFalse((self.root / "state/requalify-run.json").exists())

    def test_sigterm_at_admission_uses_cli_handler_and_finalizes(self):
        original_link = requalify.os.link
        original_handler = signal.getsignal(signal.SIGTERM)
        def terminate_after_link(source, target):
            original_link(source, target)
            signal.raise_signal(signal.SIGTERM)
        try:
            with patch("sys.argv", ["requalify", "--profile", str(self.root / "profile.json"),
                                   "--root", str(self.root), "--run-id", "termination", "--only", "install"]), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                    patch.object(requalify.subprocess, "run", side_effect=self.process), \
                    patch.object(requalify.os, "link", side_effect=terminate_after_link), \
                    self.assertRaises(SystemExit) as exited:
                runpy.run_path(requalify.__file__, run_name="__main__")
            self.assertEqual(130, exited.exception.code)
        finally:
            signal.signal(signal.SIGTERM, original_handler)
        result = self.result("termination")
        self.assertEqual(130, result["rc"])
        self.assertTrue(result["failed"])
        self.assertFalse(result["completed"])

    def test_post_admission_initialization_exception_finalizes(self):
        original = requalify.atomic_write_json
        first = True
        def fail_initial(path, value):
            nonlocal first
            if first:
                first = False
                raise RuntimeError("initial result interrupted")
            original(path, value)
        with patch.object(requalify, "atomic_write_json", side_effect=fail_initial):
            self.assertEqual(1, self.invoke("--run-id", "setup-error", "--only", "install"))
        result = self.result("setup-error")
        self.assertEqual(1, result["rc"])
        self.assertEqual("RuntimeError", result["error"])
        self.assertFalse(result["completed"])
        self.assertEqual([], result["steps"])  # Before its pre-launch status no step ran: nothing to stop.

    def test_racing_foreign_admission_is_refused_without_rewriting_it(self):
        fence = self.root / "state/requalify-run.json"
        foreign = {"run_id": "foreign", "summary": str(self.root / "evidence/requalify-foreign/summary.json")}
        def another_process_wins(_source, target):
            atomic_write_json(target, foreign)
            raise FileExistsError
        with patch.object(requalify.os, "link", side_effect=another_process_wins), \
                patch.object(requalify, "atomic_write_json", side_effect=AssertionError("must not overwrite")):
            self.assertEqual(2, self.invoke("--run-id", "ours", "--only", "install",
                                           process=lambda *_args, **_kw: self.fail("must not launch")))
        self.assertEqual(foreign, read_json(fence))
        self.assertFalse((self.root / "evidence/requalify-ours").exists())
        self.assertEqual([], list(self.root.rglob(".requalify-admission-*")))

    def test_interrupted_named_launch_never_bypasses_its_evidence_check(self):
        calls = []
        def observe(argv, **kwargs):
            calls.append(argv[2])
            return self.process(argv, **kwargs)
        for same_name in (False, True):
            # An earlier unnamed run left its evidence and a kept-running runtime.
            self.root, self.live = self.root.parent / ("same" if same_name else "other"), False
            self.assertEqual(0, self.invoke("--only", "install,start", "--keep-running", process=observe))
            earlier = next((self.root / "evidence").glob("requalify-*"))
            run_id = earlier.name.removeprefix("requalify-") if same_name else "fixture-a1"
            before, launched = self.files(), list(calls)
            with self.subTest(same_name=same_name), self.interrupt_after_link():
                self.assertEqual(130, self.invoke("--run-id", run_id, "--only", "install", process=observe))
                self.assertEqual(launched, calls)  # Neither a step nor the final stop.
                self.assertEqual(before, self.files())
                self.assertEqual([earlier], list((self.root / "evidence").glob("requalify-*")))
                self.assertFalse((self.root / "state/requalify-run.json").exists())
                self.assertEqual([], list(self.root.rglob(".requalify-admission-*")))

    def test_launch_refuses_a_root_with_a_live_runtime_before_any_step(self):
        for options in (("--run-id", "live-a1"), ()):
            self.root = self.root.parent / ("named" if options else "unnamed")
            self.live, calls = True, []  # A runtime this launch did not start, e.g. a kept-running earlier run.
            def observe(argv, **kwargs):
                calls.append(argv[2])
                return self.process(argv, **kwargs)
            with self.subTest(named=bool(options)):
                self.assertEqual(2, self.invoke(*options, process=observe))
                self.assertEqual(["status"], calls)  # No install, keygen, start or stop against it.
                self.assertTrue(self.live)
                result = read_json(next((self.root / "evidence").glob("requalify-*/result.json")))
                self.assertEqual((2, "live_runtime", False), (result["rc"], result["error"], result["completed"]))
                self.assertEqual(["status-before-launch"], [row["step"] for row in result["steps"]])
                self.assertEqual(bool(options), (self.root / "state/requalify-run.json").exists())

    def test_only_a_root_without_a_live_runtime_is_launched(self):
        for state, launched in (("not_installed", True), ("stopped", True), ("failed", True), ("starting", False),
                                ("healthy", False), ("degraded", False), ("mismatched", False), (None, False)):
            self.root = self.root.parent / str(state)
            calls = []
            def answer(argv, **kwargs):
                calls.append(argv[2])
                if argv[2] == "status":
                    kwargs["stdout"].write(json.dumps({} if state is None else {"state": state}).encode())
                    return subprocess.CompletedProcess(argv, 0 if state in ("not_installed", "stopped") else 1)
                return self.process(argv, **kwargs)
            with self.subTest(state=state):
                self.assertEqual(0 if launched else 2, self.invoke("--run-id", "state", "--only", "install",
                                                                     process=answer))
                self.assertEqual(["status", "install", "stop"] if launched else ["status"], calls)

    def test_every_interrupt_between_link_and_first_step_acts_only_after_admission(self):
        # Each factory call arms one fresh interrupt.
        def at_path(method, matches, *, after=False):
            def arm():
                real, fired = getattr(Path, method), []
                def wrapper(path, *args, **kwargs):
                    if fired or not matches(path):
                        return real(path, *args, **kwargs)
                    fired.append(path)
                    if after:
                        real(path, *args, **kwargs)
                    raise KeyboardInterrupt
                return patch.object(Path, method, wrapper)
            return arm
        def at_write(number):
            def arm():
                real, calls = requalify.atomic_write_json, []
                def wrapper(path, value):
                    calls.append(path)
                    if len(calls) == number:
                        raise KeyboardInterrupt
                    real(path, value)
                return patch.object(requalify, "atomic_write_json", side_effect=wrapper)
            return arm
        directory = lambda path: path.parent.name == "evidence" and path.name.startswith("requalify-")  # noqa: E731
        # Before admission completes the finalizer decides it; after, it stops only once the root proved clear.
        points = (("link", self.interrupt_after_link, "admission"),
                  ("check", at_path("exists", directory), "admission"),
                  ("mkdir", at_path("mkdir", directory), "admission"),
                  ("mkdir-done", at_path("mkdir", directory, after=True), "admission"),
                  ("initial-result", at_write(1), "admitted"),
                  ("summary", at_write(2), "admitted"),
                  ("profile", at_path("is_file", lambda path: path.name == "profile.json"), "admitted"),
                  ("status", contextlib.nullcontext, "admitted"),
                  ("first-step", at_write(5), "clear"))
        for name, interrupt, stage in points:
            for options in (("--run-id", "point-a1"), ()):
                self.root = self.root.parent / (name + ("-named" if options else "-unnamed"))
                calls = []
                def observe(argv, **kwargs):
                    calls.append(argv[2])
                    if name == "status" and argv[2] == "status":
                        raise KeyboardInterrupt
                    return self.process(argv, **kwargs)
                with self.subTest(point=name, named=bool(options)), interrupt():
                    self.assertEqual(130, self.invoke(*options, "--only", "install", process=observe))
                    self.assertEqual({"admission": [], "admitted": ["status"] if name == "status" else [],
                                      "clear": ["status", "stop"]}[stage], calls)
                    [result] = list((self.root / "evidence").glob("requalify-*/result.json"))
                    result = read_json(result)
                    self.assertEqual((130, False), (result["rc"], result["completed"]))
                    self.assertIsNotNone(result["finished_utc"])
                    self.assertEqual({"admission": [], "admitted": ["status-before-launch"] if name == "status" else [],
                                      "clear": ["status-before-launch", "install", "stop"]}[stage],
                                     [row["step"] for row in result["steps"]])
                    self.assertEqual(bool(options), (self.root / "state/requalify-run.json").exists())
                    self.assertEqual([], list(self.root.rglob(".requalify-admission-*")))
        # With earlier run evidence a named launch interrupted before its check is refused and touches nothing.
        for name, interrupt, _ in points[:2]:
            self.root, self.live = self.root.parent / (name + "-earlier"), False
            self.assertEqual(0, self.invoke("--only", "install,start", "--keep-running"))
            before, calls = self.files(), []
            with self.subTest(point=name, earlier=True), interrupt():
                self.assertEqual(130, self.invoke("--run-id", "point-a1", "--only", "install",
                                                  process=lambda argv, **_kw: calls.append(argv)))
            self.assertEqual([], calls)
            self.assertEqual(before, self.files())
            self.assertFalse((self.root / "state/requalify-run.json").exists())

    def test_unfinalized_fence_refuses_relaunch_without_success_or_overwrite(self):
        for initial_result in (False, True):
            self.root = self.root.parent / ("nonterminal" if initial_result else "absent")
            fence = self.root / "state/requalify-run.json"
            result = self.root / "evidence/requalify-abandoned/result.json"
            atomic_write_json(fence, {"run_id": "abandoned", "summary": str(result.with_name("summary.json"))})
            if initial_result:
                atomic_write_json(result, {"schema_version": 1, "run_id": "abandoned", "rc": None,
                                          "failed": False, "completed": False, "steps": [], "finished_utc": None})
            before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
            with self.subTest(initial_result=initial_result), \
                    patch.object(requalify, "atomic_write_json", side_effect=AssertionError("must not rewrite")):
                for run_id in ("abandoned", "another"):
                    self.assertEqual(2, self.invoke("--run-id", run_id, "--only", "install",
                                                   process=lambda *_args, **_kw: self.fail("must not launch")))
                self.assertEqual(2, self.invoke("--only", "install",
                                               process=lambda *_args, **_kw: self.fail("must not launch")))
            self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
            if initial_result:
                self.assertIsNone(read_json(result)["rc"])
                self.assertFalse(read_json(result)["completed"])
            else:
                self.assertFalse(result.exists())

    def test_existing_manual_run_fences_named_launch(self):
        self.assertEqual(0, self.invoke("--only", "install"))
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        calls = []
        self.assertEqual(2, self.invoke("--run-id", "fixture-a1", "--only", "install",
                                        process=lambda argv, **_kw: calls.append(argv)))
        self.assertEqual([], calls)
        self.assertEqual(1, len(list((self.root / "evidence").glob("requalify-*"))))
        # The refused named launch released the fence it took to check the evidence.
        self.assertFalse((self.root / "state/requalify-run.json").exists())
        self.assertEqual([], list(self.root.rglob(".requalify-admission-*")))
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def race(self, first, second):
        """Pause `first` at its first filesystem effect after the occupancy pre-check, then launch `second`."""
        argv = {name: ["--profile", str(self.root / "profile.json"), "--root", str(self.root), *options,
                       "--only", "install"] for name, options in (("first", first), ("second", second))}
        at_window, resume, second_running, second_continue = (threading.Event() for _ in range(4))
        paused, calls, codes = [], [], {}
        real_mkdir, real_parse = Path.mkdir, requalify.argparse.ArgumentParser.parse_args
        def window(path, *args, **kwargs):
            if threading.current_thread().name == "first" and not paused:
                paused.append(path)
                at_window.set()
                resume.wait(30)
            return real_mkdir(path, *args, **kwargs)
        def process(command, **kwargs):
            name = threading.current_thread().name
            calls.append(name)
            if name == "second" and not second_running.is_set():
                second_running.set()
                second_continue.wait(30)
            return self.process(command, **kwargs)
        def parse(parser, args=None, namespace=None):
            return real_parse(parser, argv[threading.current_thread().name], namespace)
        def launch():
            try:
                codes[threading.current_thread().name] = requalify.main()
            except BaseException as exc:  # Reported by the caller's assertions.
                codes[threading.current_thread().name] = repr(exc)
        threads = {name: threading.Thread(target=launch, name=name) for name in ("first", "second")}
        with patch.object(Path, "mkdir", window), \
                patch.object(requalify.argparse.ArgumentParser, "parse_args", parse), \
                patch.object(requalify.subprocess, "run", side_effect=process), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                threads["first"].start()
                self.assertTrue(at_window.wait(30))
                threads["second"].start()
                deadline = time.monotonic() + 30
                while not second_running.is_set() and threads["second"].is_alive() and time.monotonic() < deadline:
                    second_running.wait(0.01)
                resume.set()
                threads["first"].join(30)
            finally:
                resume.set()
                second_continue.set()
                for thread in threads.values():
                    if thread.ident is not None:
                        thread.join(30)
        return paused, calls, codes

    def test_named_and_unnamed_launches_admit_exactly_one_in_either_order(self):
        for first, second in ((("--run-id", "race-a1"), ()), ((), ("--run-id", "race-a1"))):
            self.root = self.root.parent / ("named-first" if first else "unnamed-first")
            with self.subTest(first="named" if first else "unnamed"):
                paused, calls, codes = self.race(first, second)
                self.assertEqual(1, len(paused))
                self.assertEqual(1, len(set(calls)), calls)
                self.assertEqual([0, 2], sorted(codes.values(), key=str), codes)
                self.assertEqual(1, len(list((self.root / "evidence").glob("requalify-*"))))

    def test_unnamed_runs_hold_the_admission_point_only_while_running(self):
        fence = self.root / "state/requalify-run.json"
        held = []
        def observe(argv, **kwargs):
            held.append(read_json(fence) if fence.exists() else None)
            return self.process(argv, **kwargs)
        for _ in range(2):
            self.assertEqual(0, self.invoke("--only", "install", process=observe))
            self.assertFalse(fence.exists())
        self.assertEqual(2, len(list((self.root / "evidence").glob("requalify-*"))))
        self.assertEqual(6, len(held))  # status, install and stop, twice.
        self.assertTrue(all(row is not None and row["run_id"] is None for row in held), held)
        # A forced death leaves the unnamed holder's fence: no launch mode may assume it is gone.
        atomic_write_json(fence, {"run_id": None, "summary": "abandoned"})
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        for extra in ((), ("--run-id", "after-death")):
            with self.subTest(extra=extra):
                self.assertEqual(2, self.invoke(*extra, "--only", "install",
                                               process=lambda *_args, **_kw: self.fail("must not launch")))
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_manual_evidence_directory_stays_exclusive_before_admission(self):
        mkdir = Path.mkdir
        occupied, calls = None, []
        def competing_directory(path, *args, **kwargs):
            nonlocal occupied
            if path.parent == self.root.resolve() / "evidence" and path.name.startswith("requalify-"):
                occupied = path
                mkdir(path, parents=True, exist_ok=True)
                (path / "foreign.log").write_bytes(b"retained")
            return mkdir(path, *args, **kwargs)
        with patch.object(Path, "mkdir", competing_directory), \
                patch.object(requalify, "atomic_write_json", side_effect=AssertionError("must not rewrite")):
            self.assertEqual(2, self.invoke("--only", "install", process=lambda argv, **_kw: calls.append(argv)))
        self.assertEqual([], calls)
        self.assertIsNotNone(occupied)
        self.assertEqual([occupied / "foreign.log"], list(occupied.iterdir()))
        self.assertEqual(b"retained", (occupied / "foreign.log").read_bytes())
        # A refusal at admission: the unnamed run releases its fence without a result.
        self.assertFalse((self.root / "state/requalify-run.json").exists())
        self.assertEqual([], list(self.root.rglob(".requalify-admission-*")))

    def test_start_failure_records_skipped_sequence_and_final_stop(self):
        def failed_start(argv, **kwargs):
            if "start" in argv:
                return subprocess.CompletedProcess(argv, 1)
            return self.process(argv, **kwargs)
        self.assertEqual(1, self.invoke("--run-id", "failed", "--only", "install,start,g10", process=failed_start))
        result = self.result("failed")
        self.assertFalse(result["completed"])
        self.assertTrue(result["failed"])
        self.assertEqual(["status-before-launch", "install", "start", "stop"], [row["step"] for row in result["steps"]])
        self.assertEqual([0, 0, 1, 0], [row["rc"] for row in result["steps"]])

    def test_completed_gate_failure_is_not_a_successful_result(self):
        def failed_gate(argv, **kwargs):
            if "g10" in argv:
                kwargs["stdout"].write(b'{"pass_observed":false}')
                return subprocess.CompletedProcess(argv, 0)
            return self.process(argv, **kwargs)
        self.assertEqual(1, self.invoke("--run-id", "gate-failed", "--only", "g10", process=failed_gate))
        result = self.result("gate-failed")
        self.assertEqual(1, result["rc"])
        self.assertTrue(result["failed"])
        self.assertTrue(result["completed"])
        self.assertFalse(next(row for row in result["steps"] if row["step"] == "g10")["pass_observed"])

    def test_interrupt_timeout_and_launch_error_always_record_result_and_cleanup(self):
        for error, expected, step_rc in ((KeyboardInterrupt(), 130, 130),
                                         (subprocess.TimeoutExpired(["fixture"], 1), 1, 124),
                                         (OSError("fixture"), 1, 1)):
            run_id = type(error).__name__
            self.root = self.root.parent / run_id
            def interrupted(argv, **kwargs):
                if "install" in argv:
                    raise error
                return self.process(argv, **kwargs)
            self.assertEqual(expected, self.invoke("--run-id", run_id, "--only", "install", process=interrupted))
            result = self.result(run_id)
            self.assertEqual(expected, result["rc"])
            self.assertEqual([0, step_rc, 0], [row["rc"] for row in result["steps"]])
            self.assertEqual(expected != 130, result["completed"])
            self.assertIsNotNone(result["finished_utc"])

    def test_cleanup_interrupt_is_incomplete_and_retains_fence(self):
        def interrupted_stop(argv, **kwargs):
            if "stop" in argv:
                raise KeyboardInterrupt
            return self.process(argv, **kwargs)
        self.assertEqual(130, self.invoke("--run-id", "cleanup", "--only", "install", process=interrupted_stop))
        self.assertFalse(self.result("cleanup")["completed"])
        self.assertEqual(130, self.result("cleanup")["steps"][-1]["rc"])
        self.assertEqual(2, self.invoke("--run-id", "cleanup", "--only", "install"))

    def test_invalid_profile_json_still_emits_terminal_result(self):
        self.root.mkdir()
        (self.root / "profile.json").write_text("{", encoding="utf-8")
        self.assertEqual(1, self.invoke("--run-id", "invalid", "--only", "install"))
        self.assertEqual("JSONDecodeError", self.result("invalid")["error"])
        self.assertEqual([], self.result("invalid")["steps"])  # The profile is read before the pre-launch status.


class RequalifySelectionTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory) / "qualification"

    def invoke(self, *options, dry_run=True):
        argv = ["requalify", "--profile", "profile.json", "--root", str(self.root), *options]
        if dry_run:
            argv.append("--dry-run")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
                patch.object(Path, "mkdir", side_effect=AssertionError("launch check must not create files")), \
                patch.object(requalify.subprocess, "run", side_effect=AssertionError("launch check must not run processes")):
            try:
                code = requalify.main()
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def assert_refused(self, options, gate, *missing):
        for dry_run in (False, True):
            with self.subTest(options=options, dry_run=dry_run):
                code, stdout, stderr = self.invoke(*options, dry_run=dry_run)
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertIn(gate, stderr)
                for step in missing:
                    self.assertIn(step, stderr)
                self.assertIn("--diagnostic", stderr)

    def test_g18_without_g18l_is_refused_before_work(self):
        self.assert_refused(("--only", "start,g18,stop"), "G18", "g18l")

    def test_quickstart_requires_install_in_the_same_run(self):
        self.assert_refused(("--only", "start,quickstart,stop"), "G26", "install")

    def test_from_g10_requires_install_and_start_in_the_same_run(self):
        self.assert_refused(("--from", "g10"), "G26", "install", "start")

    def test_all_multi_probe_gates_require_their_companions(self):
        for step, gate, missing in (("g14", "G14", "g14q"), ("g14q", "G14", "g14"),
                                    ("g18l", "G18", "g18"), ("pilot", "G24", "eval")):
            self.assert_refused(("--only", step), gate, missing)

    def test_from_filters_only_before_checking_completeness(self):
        self.assert_refused(("--from", "g18l", "--only", "start,g18,g18l,stop"), "G18", "g18")

    def test_quickstart_requires_start_even_when_install_is_selected(self):
        self.assert_refused(("--only", "install,quickstart,stop"), "G26", "start")

    def test_diagnostic_accepts_the_partial_regression_selections(self):
        cases = ((("--only", "start,g18,stop"), "G18", ("g18l",)),
                 (("--only", "start,quickstart,stop"), "G26", ("install",)),
                 (("--from", "g10"), "G26", ("install", "start")))
        for options, gate, missing in cases:
            with self.subTest(options=options):
                code, stdout, stderr = self.invoke(*options, "--diagnostic")
                self.assertEqual(code, 0)
                self.assertEqual(len(stderr.splitlines()), 1)
                self.assertIn(gate, stderr)
                self.assertIn("will not publish", stderr)
                for step in missing:
                    self.assertIn(step, stderr)
                self.assertTrue(stdout.splitlines()[0].endswith("summary.json"))
                self.assertIn("stop: ", stdout)
                self.assertNotIn("will not publish", stdout)

    def test_every_partial_gate_is_reported(self):
        for diagnostic in (False, True):
            with self.subTest(diagnostic=diagnostic):
                extra = ("--diagnostic",) if diagnostic else ()
                code, stdout, stderr = self.invoke("--only", "g14,g18,quickstart", *extra)
                self.assertEqual(code, 0 if diagnostic else 2)
                for gate, missing in (("G14", "g14q"), ("G18", "g18l"), ("G26", "install, start")):
                    self.assertIn(gate, stderr)
                    self.assertIn(missing, stderr)
                if diagnostic:
                    self.assertEqual(sum("will not publish" in line for line in stderr.splitlines()), 3)
                    self.assertIn("quickstart: ", stdout)
                else:
                    self.assertEqual(stdout, "")

    def test_default_complete_gates_and_setup_only_are_accepted(self):
        for options in ((), ("--only", "start,g18,g18l,stop"), ("--only", "start,g10,stop"),
                        ("--only", "install,keygen,start,stop"), ("--only", "install,start,quickstart,stop"),
                        ("--only", "g14,g14q"), ("--only", "pilot,eval"), ("--only", "start,eval,stop")):
            with self.subTest(options=options):
                code, stdout, stderr = self.invoke(*options)
                self.assertEqual(code, 0)
                self.assertEqual(stderr, "")
                self.assertTrue(stdout.splitlines()[0].endswith("summary.json"))
                self.assertIn("stop: ", stdout)

    def test_publisher_and_runner_share_the_gate_definitions(self):
        self.assertIs(publish_run.GATE_STEPS, requalify.GATE_STEPS)
        self.assertIs(publish_run.SAME_RUN_STEPS, requalify.SAME_RUN_STEPS)


if __name__ == "__main__":
    unittest.main()
