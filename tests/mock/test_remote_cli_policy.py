"""Every new value-taking CLI option requires a routing-policy disposition."""
import re
import subprocess
import unittest

from omp_strata.layout import Layout
from omp_strata.ompcfg import FORBIDDEN_OMP_OPTIONS, LauncherError, isolated_env, omp_argv
import tests.mock.test_remote_client as fixtures


class RemoteCliPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RemoteClientTests.setUpClass()

    def test_native_parser_rejects_glued_clustered_and_abbreviated_policy_options(self):
        f = fixtures.RemoteClientTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        environment = isolated_env(Layout(f.root, f.profile), api_key=f.key)
        help_result = subprocess.run([str(f.binary), "--help"], stdin=subprocess.DEVNULL, capture_output=True,
                                     text=True, timeout=20, cwd=f.root, env=environment)
        self.assertEqual(0, help_result.returncode)
        known = set(re.findall(r"--[\w-]+", help_result.stdout)) | FORBIDDEN_OMP_OPTIONS
        prefixes = {"--ext", "--extens", "--mod", "--prof"}
        for option in FORBIDDEN_OMP_OPTIONS:
            if not option.startswith("--"):
                continue
            prefix = option[:-1]
            while prefix in known:
                prefix = prefix[:-1]
            prefixes.add(prefix)
        value = str(f.root / "untrusted-extension.js")
        probes = []
        for option in sorted(FORBIDDEN_OMP_OPTIONS):
            if not option.startswith("--"):
                probes.extend([[option + value], ["-p" + option[1:], value]])
        probes.extend([prefix, value] for prefix in sorted(prefixes))
        probes.extend([prefix + "=" + value] for prefix in sorted(prefixes))
        for arguments in probes:
            with self.subTest(arguments=arguments):
                result = subprocess.run([str(f.binary), *arguments, "-p", "--max-time", "2s", "fixture"],
                                        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10,
                                        cwd=f.root, env=environment)
                self.assertEqual(2, result.returncode, "the native parser must reject rather than interpret the policy escape")
                self.assertIn("unknown flag", (result.stdout + result.stderr).lower())

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
