from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from scripts.fanout_proof import run_fanout


class FanoutTimeoutTests(unittest.TestCase):
    def test_versioned_wait_budget_and_operator_override(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            for version, timeout, expected in (("18.18.3", None, 180), ("19.0.0", None, 305), ("19.0.0", 17, 17)):
                route = SimpleNamespace(main=SimpleNamespace(data={"omp": {"version": version}}),
                                        data={"agents": {"scout": "local"}, "members": []})
                session = SimpleNamespace(route=route, run=Mock(side_effect=RuntimeError("captured")))
                with self.assertRaisesRegex(RuntimeError, "captured"):
                    run_fanout(session, binary=work / "omp", work=work, scouts=1, timeout=timeout)
                argv, = session.run.call_args.args
                self.assertEqual(argv[argv.index("--max-time") + 1], f"{expected}s")
                self.assertEqual(session.run.call_args.kwargs["timeout"], expected + 10)
