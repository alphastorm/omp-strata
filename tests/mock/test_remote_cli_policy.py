"""Every new value-taking CLI option requires a routing-policy disposition."""
import re
import subprocess
import unittest

from omp_strata.layout import Layout
from omp_strata.ompcfg import LauncherError, isolated_env, omp_argv
import tests.mock.test_remote_client as fixtures


class RemoteCliPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RemoteClientTests.setUpClass()

    def test_pinned_help_has_no_unreviewed_value_option_or_short_alias(self):
        f = fixtures.RemoteClientTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        layout = Layout(f.root, f.profile)
        result = subprocess.run([str(f.binary), "--help"], stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, timeout=20, env=isolated_env(layout, api_key=f.key))
        self.assertEqual(0, result.returncode, result.stderr)
        # These affect prompts, trusted workspace/storage, display, effort or approval;
        # none chooses a provider/model/config or explicitly loads code extensions.
        allowed = {"--goal", "--system-prompt", "--system-prompt-template", "--append-system-prompt",
                   "--cwd", "--mode", "--add-dir", "-r", "--resume", "--session-dir", "--tools",
                   "--thinking", "--service-tier", "--export", "--max-time", "--approval-mode"}
        pattern = re.compile(r"^\s*((?:--[\w-]+|-[A-Za-z])(?:,\s*(?:--[\w-]+|-[A-Za-z]))*)"
                             r"(?:=|\s+)(<[^>]+>|\[[^]]+\])\s*(.*)$")
        seen, unreviewed = set(), []
        for line in result.stdout.splitlines():
            match = pattern.match(line)
            if not match:
                continue
            flags = re.findall(r"--[\w-]+|-[A-Za-z]", match[1])
            for flag in flags:
                seen.add(flag)
                try:
                    omp_argv(layout, extra=[flag, "fixture"], binary=f.binary)
                except LauncherError:
                    continue
                if flag not in allowed:
                    unreviewed.append(flag + ": " + match[3])
        self.assertLessEqual({"--model", "--profile", "--extension", "-e"}, seen,
                             "the help parser must see the pinned routing options and short aliases")
        self.assertEqual([], unreviewed, "new value-taking flags need an explicit launcher-policy review")


if __name__ == "__main__":
    unittest.main()
