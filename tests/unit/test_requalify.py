"""Host-free launch checks use the runner's real argument handling."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import publish_run, requalify


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
