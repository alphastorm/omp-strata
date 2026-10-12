"""pull_run.py must pull the run its log names, never a different one."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import pull_run

ROOT = r"C:\roots\omp-strata-x"
RUN_1 = ROOT + r"\evidence\requalify-20261012T170136045450Z\summary.json"
RUN_2 = ROOT + r"\evidence\requalify-20261012T180551964043Z\summary.json"


class PullRunLogTests(unittest.TestCase):
    def pull(self, log_text: str) -> str:
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(pull_run, "powershell", return_value=log_text) as shell, \
                mock.patch.object(pull_run.subprocess, "run") as tar:
            with self.assertRaises(SystemExit) as raised:
                pull_run.main(["--host", "h", "--root", ROOT, "--log", ROOT + "\\logs\\chain-x-requalify.log",
                               "--dest", str(Path(tmp) / "dest")])
            shell.assert_called_once()
            tar.assert_not_called()
            return str(raised.exception)

    def test_a_log_a_rerun_appended_to_is_refused_instead_of_pulling_its_first_run(self):
        # 2026-10-12: a corrected pair rerun under the same chain item appended its summary line to the first
        # run's log, and reading only the first line pulled the failed first run.
        message = self.pull(RUN_1 + "\r\n" + RUN_2 + "\r\n")
        self.assertIn("names 2 requalify runs", message)

    def test_a_log_whose_first_line_is_not_a_summary_is_refused(self):
        message = self.pull("Traceback (most recent call last):\r\n" + RUN_1 + "\r\n")
        self.assertIn("first line does not name a summary", message)


if __name__ == "__main__":
    unittest.main()
