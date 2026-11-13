"""Host-free launch checks use the runner's real argument handling."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import publish_run, requalify
from omp_strata.common import read_json


class RequalifyExecutionTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory) / "candidate"

    def invoke(self, *options, process=None):
        argv = ["requalify", "--profile", str(self.root / "profile.json"),
                "--root", str(self.root), *options]
        with patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()), \
                patch.object(requalify.subprocess, "run", side_effect=process or self.process):
            return requalify.main()

    @staticmethod
    def process(argv, **kwargs):
        kwargs["stdout"].write(b'{"state":"healthy","pass_observed":true}')
        return subprocess.CompletedProcess(argv, 0)

    def result(self, run_id):
        return read_json(self.root / "evidence" / ("requalify-" + run_id) / "result.json")

    def test_run_id_fences_same_and_other_runs_without_overwriting_results(self):
        self.assertEqual(0, self.invoke("--run-id", "fixture-a1", "--only", "install,start"))
        result = self.result("fixture-a1")
        self.assertTrue(result["completed"])
        self.assertEqual(0, result["rc"])
        self.assertEqual(["install", "start", "stop"], [row["step"] for row in result["steps"]])
        self.assertTrue(all(row["rc"] == 0 for row in result["steps"]))
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for extra in (("--run-id", "fixture-a1"), ("--run-id", "another-a1"), ()):
            with self.subTest(extra=extra):
                self.assertEqual(2, self.invoke(*extra, "--only", "install"))
                self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_existing_manual_run_fences_named_launch(self):
        self.assertEqual(0, self.invoke("--only", "install"))
        self.assertEqual(2, self.invoke("--run-id", "fixture-a1", "--only", "install"))
        self.assertEqual(1, len(list((self.root / "evidence").glob("requalify-*"))))

    def test_start_failure_records_skipped_sequence_and_final_stop(self):
        def failed_start(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1 if "start" in argv else 0)
        self.assertEqual(1, self.invoke("--run-id", "failed", "--only", "install,start,g10", process=failed_start))
        result = self.result("failed")
        self.assertFalse(result["completed"])
        self.assertTrue(result["failed"])
        self.assertEqual(["install", "start", "stop"], [row["step"] for row in result["steps"]])
        self.assertEqual([0, 1, 0], [row["rc"] for row in result["steps"]])

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
            self.assertEqual([step_rc, 0], [row["rc"] for row in result["steps"]])
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
        self.assertEqual(["stop"], [row["step"] for row in self.result("invalid")["steps"]])


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
