import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.check_public_hygiene import scan

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check_public_hygiene.py"


def synthetic_home():
    return "/" + "Users/" + "synthetic-person/private"


class HygieneTests(unittest.TestCase):
    def test_generic_sensitive_patterns(self):
        cases = {
            "home-path": [synthetic_home(), "/" + "home/" + "synthetic-person/file",
                          "C:" + "\\Users\\" + "synthetic-person\\file",
                          "C:" + "/Users/" + "synthetic-person/file",
                          json.dumps("C:" + "\\Users\\" + "synthetic-person\\file")],
            "private-ipv4": [".".join(map(str, octets)) for octets in
                             ((10, 1, 2, 3), (172, 16, 0, 1), (172, 31, 255, 254),
                              (192, 168, 1, 2), (100, 64, 0, 1), (100, 127, 255, 254))],
            "tailnet-ipv6": ["fd7a:" + "115c:a1e0:" + "1234::1"],
            "tailnet-domain": ["synthetic" + ".ts.net"],
            "email": ["synthetic-person" + "@" + "private.invalid"],
            "private-key": ["-----BEGIN " + "OPENSSH PRIVATE KEY-----"],
            "ssh-public-key": [kind + " " + "AAAA" + "a" * 60 for kind in ("ssh-ed25519", "ssh-rsa")],
            "token": [prefix + "A" * 40 for prefix in ("ghp_", "github_pat_", "hf_", "sk-", "xoxb-", "xox-")]
                     + ["AKIA" + "A" * 16, "Bearer " + "a" * 30],
            "gpu-uuid": ["GPU-" + "a" * 8 + "-" + "b" * 4],
            "mac-address": [":".join(["ab"] * 6), "-".join(["ab"] * 6)],
            "windows-sid": ["S-" + "1-5-21-123456789-123456789-123456789-1001"],
            "ssh-fingerprint": ["SHA256:" + "a" * 43],
        }
        for rule, samples in cases.items():
            for text in samples:
                with self.subTest(rule=rule):
                    self.assertIn((2, rule), scan(("safe\n" + text).encode()))

    def test_benign_placeholders_networks_emails_and_binary(self):
        benign = ["/" + "Users/<user>/file", "/" + "home/<name>/file",
                  "C:" + "\\Users\\<username>\\file", "127.0.0.1", "0.0.0.0",
                  ".".join(map(str, (172, 15, 0, 1))), ".".join(map(str, (100, 128, 0, 1))),
                  "git@github.com", "noreply@github.com", "person@example.com"]
        benign.append("--hash=sha256:" + "a" * 64)
        self.assertEqual([], scan("\n".join(benign).encode()))
        self.assertEqual([], scan(b"\0" + synthetic_home().encode()))
        self.assertEqual([(1, "private-denylist")], scan(b"SYNTHETIC-private-word", ["synthetic-private-word"]))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.env.pop("OMP_STRATA_HYGIENE_DENYLIST", None)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.com")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], env=self.env,
                              capture_output=True, check=True, timeout=15)

    def run_scanner(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=self.repo,
                              env=env or self.env, capture_output=True, text=True, timeout=20)

    def test_staged_blobs_not_worktree_and_masked_output(self):
        secret = synthetic_home()
        path = self.repo / "content.txt"
        path.write_text(secret)
        self.git("add", "content.txt")
        path.write_text("safe worktree")
        staged = self.run_scanner("--staged")
        self.assertEqual(1, staged.returncode)
        self.assertIn("content.txt:1: home-path [MASKED]", staged.stdout)
        self.assertNotIn(secret, staged.stdout + staged.stderr)
        self.assertEqual(0, self.run_scanner().returncode)

    def test_default_scans_untracked_but_not_ignored(self):
        (self.repo / ".gitignore").write_text("ignored.txt\n")
        (self.repo / "ignored.txt").write_text(synthetic_home())
        self.assertEqual(0, self.run_scanner().returncode)
        (self.repo / "untracked.txt").write_text(synthetic_home())
        self.assertEqual(1, self.run_scanner().returncode)

    def test_history_finds_deleted_blob(self):
        path = self.repo / "history.txt"
        path.write_text(synthetic_home())
        self.git("add", "history.txt")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "synthetic fixture")
        path.write_text("clean current content")
        self.git("add", "history.txt")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "clean fixture")
        self.assertEqual(0, self.run_scanner().returncode)
        history = self.run_scanner("--history")
        self.assertEqual(1, history.returncode)
        self.assertIn("home-path [MASKED]", history.stdout)
        self.assertNotIn(synthetic_home(), history.stdout + history.stderr)

    def test_denylist_explicit_environment_default_and_missing(self):
        path = self.repo / "content.txt"
        path.write_text("PRIVATE-" + "SYNTHETIC-HOST")
        denylist = self.root / "denylist.txt"
        denylist.write_text("# comment\nprivate-synthetic-host\n")
        self.assertEqual(1, self.run_scanner("--denylist", denylist).returncode)
        env = dict(self.env, OMP_STRATA_HYGIENE_DENYLIST=str(denylist))
        self.assertEqual(1, self.run_scanner(env=env).returncode)
        default = self.home / ".config/omp-strata/hygiene-denylist.txt"
        default.parent.mkdir(parents=True)
        default.write_bytes(denylist.read_bytes())
        self.assertEqual(1, self.run_scanner().returncode)
        self.assertEqual(2, self.run_scanner("--denylist", self.root / "missing").returncode)
        result = self.run_scanner("--denylist", denylist, path)
        self.assertEqual(1, result.returncode)
        self.assertNotIn(path.read_text(), result.stdout + result.stderr)

    def test_filenames_and_explicit_binary(self):
        name = "synthetic" + ".ts.net"
        (self.repo / name).write_text("benign")
        result = self.run_scanner()
        self.assertEqual(1, result.returncode)
        self.assertIn("[masked-path]", result.stdout)
        self.assertNotIn(name, result.stdout)
        binary = self.repo / "binary.dat"
        binary.write_bytes(b"\0" + synthetic_home().encode())
        self.assertEqual(0, self.run_scanner(binary).returncode)
        self.assertEqual(2, self.run_scanner(self.root / "missing.txt").returncode)
