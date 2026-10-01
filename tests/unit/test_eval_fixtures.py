"""Behavioral solvability and anti-tamper checks for the frozen evaluation."""
import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from eval.support import EVAL, ROOT, apply_reference, files, materialize, run_verifier, validate_manifest, visible_status
from tests.candidate import PROFILE as CANDIDATE_PROFILE

spec = importlib.util.spec_from_file_location("evaluation_harness", ROOT / "scripts" / "evaluate.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class EvalFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((EVAL / "tasks.json").read_text(encoding="utf-8"))

    def test_frozen_manifest_matches_all_files_and_generated_output(self):
        self.assertEqual(validate_manifest(self.manifest), [])

    def test_each_seed_fails_and_reference_solves_unchanged_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            for task in self.manifest["tasks"]:
                with self.subTest(task=task["id"]):
                    workspace = materialize(task, Path(directory) / task["id"])
                    self.assertEqual(visible_status(workspace), task["preexisting_visible_tests"])
                    seed = run_verifier(task, workspace)
                    self.assertEqual(seed["returncode"], 1, seed)
                    self.assertFalse(seed["verdict"]["passed"])
                    apply_reference(task, workspace)
                    solved = run_verifier(task, workspace)
                    self.assertTrue(solved["verdict"]["passed"], solved)

    def test_edited_visible_tests_cannot_make_a_candidate_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            for task in self.manifest["tasks"]:
                with self.subTest(task=task["id"]):
                    workspace = materialize(task, Path(directory) / task["id"])
                    apply_reference(task, workspace)
                    visible = next((workspace / "tests").glob("test_*.py"))
                    visible.write_text("import unittest\n", encoding="utf-8")
                    result = run_verifier(task, workspace)
                    self.assertFalse(result["verdict"]["passed"])
                    self.assertIn("integrity_errors", result["verdict"]["details"])

    def test_deleted_immutable_contract_is_not_accepted(self):
        task = next(item for item in self.manifest["tasks"] if item["id"] == "multifile-regression")
        with tempfile.TemporaryDirectory() as directory:
            workspace = materialize(task, Path(directory) / "workspace")
            apply_reference(task, workspace)
            (workspace / "sku.py").unlink()
            result = run_verifier(task, workspace)
            self.assertFalse(result["verdict"]["passed"])
            self.assertIn("integrity_errors", result["verdict"]["details"])

    def test_continuation_remains_solvable_without_the_instrument(self):
        task = next(item for item in self.manifest["tasks"] if item["id"] == "continuation")
        with tempfile.TemporaryDirectory() as directory:
            workspace = materialize(task, Path(directory) / "workspace")
            apply_reference(task, workspace)
            for name in task["remove_between_phases"]:
                (workspace / name).unlink()
            self.assertTrue(run_verifier(task, workspace)["verdict"]["passed"])

    def test_model_visible_tree_excludes_grading_and_reference_material(self):
        with tempfile.TemporaryDirectory() as directory:
            for task in self.manifest["tasks"]:
                workspace = materialize(task, Path(directory) / task["id"], git=False)
                names = [path.relative_to(workspace).as_posix().lower() for path in files(workspace)]
                self.assertFalse(any(any(term in name for term in ["verifier", "reference", "solution.patch", "hidden.py"])
                                     for name in names), task["id"])
                self.assertFalse((workspace / "generate_corpus.py").exists())


class EvaluationSupervisorTests(unittest.TestCase):
    def test_tool_cap_kills_process_before_later_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "should-not-exist"
            program = ("import json,time,pathlib\n"
                       "for n in range(3):\n"
                       " print(json.dumps({'type':'message_end','message':{'role':'assistant','content':["
                       "{'type':'toolCall','id':str(n),'name':'bash','arguments':{'command':'true'}}],"
                       "'usage':{'output':1},'stopReason':'toolUse'}}),flush=True)\n"
                       "time.sleep(5)\n"
                       f"pathlib.Path({str(marker)!r}).write_text('escaped')\n")
            counts = harness.EventCounts()
            budget = {"tool_calls": 2, "total_output_tokens": 100, "max_event_bytes": 65536, "max_stderr_bytes": 4096}
            result = harness.run_phase([sys.executable, "-u", "-c", program], workspace=root,
                                       env=None, directory=root, phase=1, deadline=time.monotonic() + 3,
                                       budget=budget, counts=counts)
            self.assertEqual(result["abort_reason"], "tool_call_cap")
            self.assertFalse(marker.exists())
            self.assertNotEqual(result["exit_code"], 0)

    def test_wall_timeout_bounds_a_silent_client(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            budget = {"tool_calls": 40, "total_output_tokens": 100, "max_event_bytes": 65536, "max_stderr_bytes": 4096}
            result = harness.run_phase([sys.executable, "-c", "import time; time.sleep(10)"],
                                       workspace=root, env=None, directory=root, phase=1,
                                       deadline=time.monotonic() + 0.3, budget=budget, counts=harness.EventCounts())
            self.assertEqual(result["abort_reason"], "timeout")
            self.assertLess(result["wall_ms"], 3000)


class StockClientContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_OMP_BINARY")
        if not value or not Path(value).is_file():
            raise unittest.SkipTest("set OMP_STRATA_OMP_BINARY to the fetched stock OMP binary for continuation smoke")
        cls.binary = Path(value).resolve()

    def test_fresh_client_resumes_calibration_after_instrument_removal(self):
        import copy
        import secrets
        from dataclasses import replace
        from omp_strata.layout import Layout
        from omp_strata.profile import load
        from tests.mock.scripted_server import ScriptedServer, ResponseSpec, ToolCall

        profile = load(CANDIDATE_PROFILE)
        manifest = json.loads((EVAL / "tasks.json").read_text(encoding="utf-8"))
        task = next(task for task in manifest["tasks"] if task["id"] == "continuation")
        with tempfile.TemporaryDirectory(prefix="eval-stock-") as directory:
            root = Path(directory)
            reference = materialize(task, root / "reference")
            apply_reference(task, reference)
            fixed_source = (reference / "scheduler.py").read_text(encoding="utf-8")
            scenario = [ResponseSpec(text="", calls=[ToolCall("bash", {
                            "i": "Reading calibration", "command": f'"{sys.executable}" -B phase1/probe.py', "timeout": 10})]),
                        ResponseSpec(text="CALIBRATION shift=23 width=11 tie=largest-sequence"),
                        ResponseSpec(text="", calls=[ToolCall("write", {
                            "i": "Applying calibration", "path": "scheduler.py", "content": fixed_source})]),
                        ResponseSpec(text="Calibrated scheduler repaired.")]
            server = ScriptedServer(scenario, model=profile.data["strata"]["model_name"])
            try:
                data = copy.deepcopy(profile.data)
                data["server"]["port"] = server.httpd.server_port
                layout = Layout(root=root, profile=replace(profile, data=data))
                result = harness.run_attempt(task, 1, layout=layout, binary=self.binary,
                                             key=secrets.token_urlsafe(32), directory=root / "out",
                                             work=root / "work", between_phases=None,
                                             batch_deadline=time.monotonic() + 60)
                self.assertTrue(result["verified_pass"], result)
                self.assertEqual(result["tool_calls"], 2)
                self.assertEqual([phase["exit_code"] for phase in result["phases"]], [0, 0])
                self.assertFalse((Path(result["workspace"]) / "phase1" / "readings.csv").exists())
                replay = server.posts[2]["body"]["messages"]
                self.assertTrue(any(message.get("role") == "tool" and
                                    "CALIBRATION shift=23 width=11" in str(message.get("content"))
                                    for message in replay), "phase-1 tool result was not replayed after client restart")
                self.assertEqual(len(result["transcript_paths"]), 1)
            finally:
                server.close()


if __name__ == "__main__":
    unittest.main()
