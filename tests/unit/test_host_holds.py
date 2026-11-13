"""Experiment-loop host holds and candidate-root isolation; no Windows host or GPU effects."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import experiment_loop as loop


class HoldAndRootTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory).resolve()
        self.locks = self.root / "locks"

    def test_only_matching_claim_may_adopt_and_old_owner_cannot_release(self):
        path = self.locks / "fixture-host.lock"
        with loop.host_lock("fixture-host", self.locks, claim_id="claim-a") as original:
            self.assertEqual("claim-a", json.loads(path.read_bytes())["claim_id"])
            before = path.read_bytes()
            for claim in ("claim-b", None):
                with self.subTest(claim=claim), self.assertRaisesRegex(loop.ExperimentError, "claim_mismatch"):
                    with loop.adopt_host_lock("fixture-host", claim, self.locks):
                        self.fail("foreign adoption")
                self.assertEqual(before, path.read_bytes())
            with loop.adopt_host_lock("fixture-host", "claim-a", self.locks) as adopted:
                with self.assertRaisesRegex(loop.ExperimentError, "identity_changed"):
                    original()
                self.assertTrue(path.exists())
                adopted()
            self.assertFalse(path.exists())

    def test_manual_holds_cannot_be_adopted_and_exceptions_retain_hold(self):
        path = self.locks / "fixture-host.lock"
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            with loop.host_lock("fixture-host", self.locks):
                raise RuntimeError("fixture")
        before = path.read_bytes()
        with self.assertRaisesRegex(loop.ExperimentError, "claim_mismatch"):
            with loop.adopt_host_lock("fixture-host", "claim-a", self.locks):
                self.fail("manual hold adoption")
        with self.assertRaisesRegex(loop.ExperimentError, "host_lock_owned"):
            with loop.host_lock("fixture-host", self.locks, claim_id="claim-a"):
                self.fail("occupied hold")
        self.assertEqual(before, path.read_bytes())

    def test_only_a_persistent_hold_of_the_same_claim_is_adopted(self):
        # The evaluator's own worker lock shares this path; a matching claim alone does not make it a hold.
        path = self.locks / "fixture-host.lock"
        self.locks.mkdir(parents=True)
        for hold in ({"pid": 1, "utc": "fixture", "claim_id": "claim-a", "persistent_hold": False},
                     {"pid": 1, "utc": "fixture", "claim_id": "claim-a"},
                     {"pid": 1, "utc": "fixture", "claim_id": "claim-a", "persistent_hold": "true"}):
            path.write_text(json.dumps(hold), encoding="utf-8")
            before = path.read_bytes()
            with self.subTest(hold=hold), self.assertRaisesRegex(loop.ExperimentError, "claim_mismatch"):
                with loop.adopt_host_lock("fixture-host", "claim-a", self.locks):
                    self.fail("non-persistent lock adoption")
            self.assertEqual(before, path.read_bytes())

    def test_unreadable_holds_are_refused_not_adopted_or_removed(self):
        path = self.locks / "fixture-host.lock"
        self.locks.mkdir(parents=True)
        for content in (b"", b"123", b"[]", b'{"claim_id"'):
            path.write_bytes(content)
            with self.subTest(content=content), self.assertRaisesRegex(loop.ExperimentError, "host_lock_unreadable"):
                with loop.adopt_host_lock("fixture-host", "claim-a", self.locks):
                    self.fail("unreadable hold adoption")
            self.assertEqual(content, path.read_bytes())
        path.unlink()
        with loop.host_lock("fixture-host", self.locks, claim_id="claim-a") as release:
            for content in (b"", b"123"):
                path.write_bytes(content)
                with self.subTest(release=content), self.assertRaisesRegex(loop.ExperimentError, "host_lock_unreadable"):
                    release()
                self.assertEqual(content, path.read_bytes())

    def test_interrupted_hold_creation_publishes_no_partial_hold(self):
        path = self.locks / "fixture-host.lock"
        def partial(owner, stream, *args, **kwargs):
            stream.write('{"pid": ')
            raise KeyboardInterrupt
        with patch.object(loop.json, "dump", side_effect=partial), self.assertRaises(KeyboardInterrupt):
            with loop.host_lock("fixture-host", self.locks, claim_id="claim-a"):
                self.fail("partial hold admitted")
        self.assertFalse(path.exists())
        self.assertEqual(["fixture-host.guard"], sorted(p.name for p in self.locks.iterdir()))
        with loop.host_lock("fixture-host", self.locks, claim_id="claim-a") as release:
            self.assertEqual("claim-a", json.loads(path.read_bytes())["claim_id"])
            release()
        self.assertFalse(path.exists())

    def test_incumbent_overlap_is_refused_before_isolation_scan(self):
        incumbent = self.root / "incumbent"
        for candidate in (incumbent, incumbent / "candidate", self.root):
            with self.subTest(candidate=candidate), patch.object(loop.nvfp4, "assert_isolated_tree") as scan, \
                    self.assertRaisesRegex(loop.ExperimentError, "root_overlap"):
                loop.candidate_root_guard(candidate, incumbent)
            scan.assert_not_called()
        isolated = self.root / "candidate"
        self.assertEqual(isolated, loop.candidate_root_guard(isolated, incumbent))
        incumbent.mkdir()
        alias = self.root / "incumbent-alias"
        alias.symlink_to(incumbent, target_is_directory=True)
        with self.assertRaisesRegex(loop.ExperimentError, "root_overlap"):
            loop.candidate_root_guard(incumbent / "candidate", alias)


if __name__ == "__main__":
    unittest.main()
