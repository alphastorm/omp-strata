"""Process identity without `ps`: minimal containers only carry /proc."""
import os
import subprocess
import sys
import unittest
from unittest.mock import mock_open, patch

from omp_strata import procs

LINUX_PROC = sys.platform.startswith("linux") and os.path.exists("/proc/self/stat")


def no_ps(*args, **kwargs):
    raise FileNotFoundError(2, "No such file or directory: 'ps'")


@unittest.skipUnless(LINUX_PROC, "needs Linux /proc")
class ProcFallbackTests(unittest.TestCase):
    def test_identity_comes_from_proc_when_ps_is_missing(self):
        with patch.object(procs.subprocess, "run", side_effect=no_ps):
            me = procs.info(os.getpid())
        self.assertIsNotNone(me)
        self.assertEqual(os.getppid(), me.ppid)
        self.assertTrue(me.created.startswith("starttime:"))
        self.assertTrue(me.created.removeprefix("starttime:").isdigit())
        self.assertEqual(os.readlink("/proc/self/exe"), me.exe)

    def test_identity_is_stable_distinguishes_processes_and_lists_children(self):
        with patch.object(procs.subprocess, "run", side_effect=no_ps):
            first, second = procs.info(os.getpid()), procs.info(os.getpid())
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                kid = procs.info(child.pid)
                self.assertIsNotNone(kid)
                self.assertEqual(os.getpid(), kid.ppid)
                self.assertIn(child.pid, procs.children(os.getpid()))
                self.assertEqual(first, second)
                self.assertNotEqual(first.created, kid.created)
            finally:
                child.kill()
                child.wait()
            self.assertIsNone(procs.info(child.pid))

    def test_missing_pid_and_malformed_stat_are_none(self):
        self.assertIsNone(procs._proc_stat(2 ** 22 + 1))
        with patch("builtins.open", mock_open(read_data="1 (python) R")):
            self.assertIsNone(procs._proc_stat(1))


if __name__ == "__main__":
    unittest.main()
