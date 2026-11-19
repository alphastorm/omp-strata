"""Host-free child_env proof against the pinned frontend supplied by dev-env."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

from omp_strata import install
from omp_strata.install import APPLY_SERVER_CHOICES, sibling_installs
from omp_strata.layout import Layout
from omp_strata.lifecycle import DFLASH2_SLOT_LINE, DFLASH2_VOCAB_LINE
from omp_strata.profile import engine_env_group_values, load
from scripts.upstream_watch import RUNTIME_TRANSITIVE_0_2_7, lock_pins, requirement_pins


ENGINES = {"d2f096475817d4666c364c820b0ca830f751cfc5": "0.1.59",
           "64524fb9fc82222ddce554c0643b64f056ec8366": "0.1.62"}
PROOF = r'''
import json
import os
import sys
from unittest.mock import patch

from serve import server

pinned = json.loads(sys.argv[1])
cfg = {"backend": "cuda", "args": [], "env": pinned}
with patch.dict(os.environ, {key: "ambient value" for key in pinned}, clear=True):
    actual = server.child_env(cfg)
print(json.dumps({key: actual[key] for key in pinned}))
'''


class StockEngineEnvProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_STRATA_SRC")
        if not value or not Path(value).is_dir():
            raise unittest.SkipTest("set OMP_STRATA_STRATA_SRC through dev-env to the pinned checkout")
        cls.source = Path(value).resolve()
        cls.python = os.environ.get("OMP_STRATA_STRATA_PYTHON", sys.executable)
        result = subprocess.run(["git", "-C", str(cls.source), "rev-parse", "HEAD"], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise AssertionError("OMP_STRATA_STRATA_SRC is not a readable pinned checkout")
        cls.version = ENGINES.get(result.stdout.strip())
        if cls.version is None:
            raise unittest.SkipTest("this proof needs the v0.2.13 or v0.2.16 pin")

    def test_candidate_groups_pass_through_stock_child_env_unchanged(self):
        groups = engine_env_group_values(self.version)
        for candidate in ("spec_cost", "qsa_split_attn", "sm86_table"):
            pinned = groups["gdn_stack"] | groups[candidate]
            with self.subTest(candidate=candidate):
                result = subprocess.run([self.python, "-c", PROOF, json.dumps(pinned)], cwd=self.source,
                                        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(pinned, json.loads(result.stdout))

    def test_terminal_setup_reinstall_carries_pinned_call_policy(self):
        if self.version != "0.1.62":
            self.skipTest("the call policy requires v0.2.16")
        # Exercise stock's real reinstall/backup/carry_over path, not a stand-in config merger.
        reinstall = ("from pathlib import Path; import setup, sys; "
                     "setup.write_setup_config(Path(sys.argv[1]), {'args': [], 'model_name': sys.argv[2]})")
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "strata-profile.json"
            for code, arg in ((reinstall, "first"), (APPLY_SERVER_CHOICES, '{"undeclared_tool_calls":"call"}'),
                              (reinstall, "second")):
                result = subprocess.run([self.python, "-c", code, str(cfg), arg], cwd=self.source,
                                        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
            for file, model in ((cfg, "second"), (cfg.with_suffix(".json.bak"), "first")):
                saved = json.loads(file.read_text(encoding="utf-8-sig"))
                self.assertEqual((model, "call", []),
                                 (saved["model_name"], saved["undeclared_tool_calls"], saved["args_written"]))

    def test_first_terminal_setup_can_stamp_every_locked_runtime_requirement_offline(self):
        if self.version != "0.1.62":
            self.skipTest("terminal setup starts with v0.2.16")
        with tempfile.TemporaryDirectory() as tmp:
            layout = Layout(Path(tmp).resolve(), load(Path(os.environ["OMP_STRATA_PROFILE"])))
            mtp = layout.data / "mtp/rt/experts.bin"
            mtp.parent.mkdir(parents=True)
            mtp.touch()
            # Capture the actual setup environment, not build_env's defaults or the test process environment.
            with (patch.dict(os.environ, {"STRATA_NO_ACQUIRE": "1"}),
                  patch.object(install, "sibling_installs", return_value=[]),
                  patch.object(install, "run", return_value=subprocess.CompletedProcess([], 0, stdout="")) as runner):
                install.run_setup(layout, log=lambda _: None)
            env = runner.call_args.kwargs["env"]
            self.assertEqual("1", env["PIP_NO_INDEX"])
            # Exercise stock through its pip boundary; do not install Windows wheels on the dev-env host.
            probe = """
import json, sys
from unittest.mock import patch
import setup
from strata_control import acquisition
packages = setup.runtime_packages()
with patch.object(sys, "prefix", sys.argv[1]), patch.object(setup, "run") as pip:
    setup.pip_install(packages, "runtime packages")
    pip.assert_called_once()
    argv = pip.call_args.args[0]
    assert argv[:3] == [sys.executable, "-m", "pip"] and argv[-len(packages):] == packages
    print(json.dumps(acquisition.is_forbidden()))
"""
            stamp = layout.root / ".strata-pip.json"
            self.assertFalse(stamp.exists())
            result = subprocess.run([self.python, "-c", probe, str(layout.root)], cwd=self.source, env=env,
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIs(json.loads(result.stdout.splitlines()[-1]), False)
            need = requirement_pins(json.loads(stamp.read_text()), python=(3, 13), platform="win32")
            self.assertEqual("8.2.8", need["textual"])
            locked = lock_pins(install.python_lock_path(layout).read_text())
            for package, version in (need | RUNTIME_TRANSITIVE_0_2_7).items():
                with self.subTest(package=package):
                    self.assertEqual(version, locked.get(package))

    def test_terminal_slot_and_default_vocabulary_lines_match_stock(self):
        if self.version != "0.1.62":
            self.skipTest("these announcements start with v0.2.16")
        emit = ("from pathlib import Path; from strata_control import drafting as d; "
                "print('[strata]', d.SLOT_DRAFTS_LINE); print('[strata] drafting:', "
                "d.auto_vocab({}, [], Path('draft_vocab.bin'), d.FORM_FILE, signals={'ui': ['en-US']})[1])")
        result = subprocess.run([self.python, "-c", emit], cwd=self.source, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([DFLASH2_SLOT_LINE, DFLASH2_VOCAB_LINE], result.stdout.splitlines())

    def test_terminal_sibling_scan_and_model_marks_follow_the_control_root(self):
        if self.version != "0.1.62":
            self.skipTest("terminal installs start with v0.2.16")
        with tempfile.TemporaryDirectory() as tmp:
            layout = Layout(Path(tmp).resolve(), load(Path(os.environ["OMP_STRATA_PROFILE"])))
            if not layout.terminal_layout:
                self.fail("stock source and dev-env profile disagree")
            layout.control_root.mkdir(parents=True)
            # Load tracked stock code from the selected dev-env but point its ROOT at the isolated test install.
            # Stock documents ROOT as the single overridable base; none of its settings or marks touch the checkout.
            src = str(self.source)
            (layout.control_root / "setup.py").write_text(
                f"import sys; from pathlib import Path; sys.path.insert(0, {src!r})\n"
                f"exec(compile((Path({src!r})/'setup.py').read_bytes(), __file__, 'exec'))\nROOT = Path.cwd()\n")
            settings = layout.appdata / ("Strata" if os.name == "nt" else "strata") / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"installs": [str(layout.control_root)]}))
            with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(self.python)):
                self.assertEqual([], sibling_installs(layout, log=lambda _: None))
                other = layout.strata.parent / "Strata-sibling/Strata-nested"
                other.mkdir(parents=True)
                (other / "setup.py").touch()
                self.assertEqual([other], sibling_installs(layout, log=lambda _: None))
                stale = layout.root / "old-install"
                settings.write_text(json.dumps({"installs": [str(stale)]}))
                self.assertEqual({other, stale}, set(sibling_installs(layout, log=lambda _: None)))
            model = layout.models_dir / "tiny.gguf"
            model.parent.mkdir(parents=True)
            model.touch()
            result = subprocess.run([self.python, "-c", "import setup, sys; from pathlib import Path; "
                                     "p=Path(sys.argv[1]); setup.own_files_in(p.parent); setup.mark(p, 'complete')",
                                     str(model)], cwd=layout.control_root, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(["complete"], [p.read_text() for p in (layout.control_root / "marks").glob("*.done")])
            self.assertFalse((model.parent / "tiny.gguf.done").exists())


if __name__ == "__main__":
    unittest.main()
