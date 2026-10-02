"""Exercise the real shared runner with a local Python executable, never a GPU host."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from omp_strata.comparison import ArmLaunch, ComparisonError, ROOT, canonical, file_sha256, harness_identity, read_json, schedule
from scripts import compare_g25
from tests.unit.test_comparison import comparison_plan, observation_fixture

FAKE_CLIENT = r'''
import json, os, signal, subprocess, sys, time
from pathlib import Path
root = Path(os.environ["G25_TEST_SOURCE"])
sys.path.insert(0, str(root))
from eval.support import apply_reference
args = sys.argv[1:]
mode = os.environ.get("G25_TEST_MODE", "solve")
workspace = Path.cwd()
task_id = workspace.parent.name
manifest = json.loads((root / "eval/tasks.json").read_text())
task = next(task for task in manifest["tasks"] if task["id"] == task_id)
sessions = Path(args[args.index("--session-dir") + 1])
if mode == "interrupt":
    os.kill(os.getppid(), signal.SIGINT)
    time.sleep(60)
if mode == "timeout":
    time.sleep(60)
if mode == "oom":
    print("out of memory", file=sys.stderr)
    raise SystemExit(1)
if mode != "missing-transcript":
    with (sessions / "session.jsonl").open("a") as stream:
        stream.write(json.dumps({"type":"message"}) + "\n")
if mode == "tool-cap":
    print(json.dumps({"type":"message_end", "message":{"role":"assistant", "usage":{"output":1},
          "content":[{"type":"toolCall", "id":str(i), "arguments":{}} for i in range(41)]}}), flush=True)
    time.sleep(60)
if task_id == "continuation" and "--continue" not in args:
    print(json.dumps({"type":"message_end", "message":{"role":"assistant", "usage":{"output":2},
          "content":[{"type":"toolCall", "id":"calibration", "arguments":{}}]}}))
    print(json.dumps({"type":"message_end", "message":{"role":"toolResult", "toolCallId":"calibration",
          "content":[{"type":"text", "text":"CALIBRATION shift=23 width=11 tie=largest-sequence"}]}}))
else:
    if mode != "verifier-fail":
        apply_reference(task, workspace)
    message = {"role":"assistant", "content":[{"type":"text","text":"Complete."}], "stopReason":"stop"}
    if mode != "missing-usage":
        message["usage"] = {"output":3}
    print(json.dumps({"type":"message_end", "message":message}))
print(json.dumps({"type":"agent_end"}), flush=True)
'''


class FakeAdapter:
    def __init__(self, arm, plan, executable, mode="solve"):
        self.arm, self.plan, self.executable, self.mode = arm, plan, executable, mode
        self.preflights = 0
        self.prepares = 0

    def preflight(self):
        self.preflights += 1
        return {"arm": self.arm, "api": self.plan[self.arm]["api"], "provider": self.plan[self.arm]["provider"],
                "model": self.plan[self.arm]["model_id"], "port": 12345}

    def prepare(self, root):
        self.prepares += 1
        root.mkdir(parents=True)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(root), "USERPROFILE": str(root),
               "G25_TEST_SOURCE": str(ROOT), "G25_TEST_MODE": self.mode}
        if "SYSTEMROOT" in os.environ:
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        return ArmLaunch([sys.executable, str(self.executable)], env, root, "a" * 64, "b" * 64, self.preflight())


class ComparisonRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fake = self.root / "client.py"
        self.fake.write_text(FAKE_CLIENT, encoding="utf-8")
        self.plan = comparison_plan()
        self.plan["omp"].update(bytes=Path(sys.executable).stat().st_size, sha256=file_sha256(Path(sys.executable)))
        self.plan["pilot"]["execution_boundary"] = "host_free"
        self.bindings = {"comparison_root": str(self.root / "run"), "omp_binary": sys.executable, "execution_boundary": "host_free"}
        self.tasks = read_json(ROOT / "eval/tasks.json")["tasks"]

    def observe(self, bindings, plan, arm):
        return observation_fixture(plan, arm)

    def adapter(self, arm="strata", mode="solve"):
        return FakeAdapter(arm, self.plan, self.fake, mode)

    def attempt(self, mode="solve", task=0, remaining=900):
        return compare_g25.run_comparison_attempt(self.adapter(mode=mode), self.tasks[task], 1, plan=self.plan,
                    window=1, directory=self.root / mode / self.tasks[task]["id"], batch_deadline=time.monotonic() + remaining)

    def test_same_real_attempt_path_solves_both_arms_and_continuation(self):
        for arm, window in (("strata", 1), ("ninfer", 2)):
            result = compare_g25.run_comparison_attempt(self.adapter(arm), self.tasks[5], 1, plan=self.plan,
                window=window, directory=self.root / arm / "continuation", batch_deadline=time.monotonic() + 900)
            self.assertTrue(result["verified_pass"], result)
            self.assertEqual(len(result["phases"]), 2)
            self.assertEqual(result["tool_calls"], 1)
            self.assertGreater(result["task_wall_ms"], sum(phase["wall_ms"] for phase in result["phases"]))
            self.assertEqual(result["verifier_exit_code"], 0)
            self.assertIsNone(result["request_wall_ms"])

    def test_tool_and_monotonic_wall_caps_fail_without_hanging(self):
        tools = self.attempt("tool-cap")
        self.assertFalse(tools["verified_pass"])
        self.assertEqual(tools["abort_reason"], "tool_call_cap")
        wall = self.attempt("timeout", remaining=30.2)
        self.assertFalse(wall["verified_pass"])
        self.assertTrue(wall["timeout"])
        self.assertLess(wall["task_wall_ms"], 3000)

    def test_verifier_failure_missing_transcript_and_usage_are_not_hidden(self):
        failed = self.attempt("verifier-fail")
        self.assertFalse(failed["verified_pass"])
        self.assertEqual(failed["verifier_exit_code"], 1)
        missing = self.attempt("missing-transcript")
        self.assertFalse(missing["verified_pass"])
        self.assertEqual(missing["protocol_errors"]["missing_transcript"], 1)
        usage = self.attempt("missing-usage")
        self.assertTrue(usage["verified_pass"])
        self.assertIsNone(usage["reported_output_tokens"])
        self.assertIn("reported_output_tokens", usage["missing_reasons"])

    def test_full_schedule_retains_all_36_slots_then_summary_never_calls_model(self):
        for row in schedule():
            adapter = self.adapter(row["arm"])
            window = compare_g25.run_window(self.plan, self.bindings, adapter, row["window"], observer=self.observe)
            self.assertEqual(window["status"], "complete")
            self.assertIsNone(window["abort_reason"])
            self.assertEqual([ref["task_id"] for ref in window["attempts"]], row["task_order"])
        with patch.object(compare_g25, "run_phase", side_effect=AssertionError("summary must not dispatch")):
            summary, windows, verifier = compare_g25.summarize(self.plan, Path(self.bindings["comparison_root"]))
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["outcome_counts"]["both_pass"], 18)
        self.assertEqual(len(verifier["attempts"]), 36)
        self.assertEqual(summary["arms"]["strata"]["verified_passes"], 18)
        self.assertIsNone(summary["claims"]["factual_sentence"])
        with self.assertRaises(ComparisonError):
            compare_g25.summarize(self.plan, Path(self.bindings["comparison_root"]))
        exported = self.root / "exported"
        compare_g25.export_reviewed(self.plan, summary, windows, verifier, exported, "I reviewed all public comparison artifacts")
        for ref in summary["windows"]:
            self.assertEqual(file_sha256(exported / f"window-{ref['window']}.json"), ref["sha256"])

    def test_refuses_previous_unfinalized_overwrite_and_resume(self):
        with self.assertRaises(ComparisonError):
            compare_g25.run_window(self.plan, self.bindings, self.adapter("ninfer"), 2, observer=self.observe)
        first = compare_g25.run_window(self.plan, self.bindings, self.adapter(), 1, observer=self.observe)
        digest = file_sha256(Path(self.bindings["comparison_root"]) / "window-1/window.json")
        with self.assertRaises(ComparisonError):
            compare_g25.run_window(self.plan, self.bindings, self.adapter(), 1, observer=self.observe)
        self.assertEqual(file_sha256(Path(self.bindings["comparison_root"]) / "window-1/window.json"), digest)
        self.assertEqual(len(first["attempts"]), 6)

    @unittest.skipIf(os.name == "nt", "SIGINT injection exercises POSIX process-group cleanup")
    def test_client_interruption_leaves_explicit_incomplete_nonresumable_window(self):
        with self.assertRaises(KeyboardInterrupt):
            compare_g25.run_window(self.plan, self.bindings, self.adapter(mode="interrupt"), 1, observer=self.observe)
        root = Path(self.bindings["comparison_root"])
        window = read_json(root / "window-1/window.json")
        self.assertEqual(window["status"], "incomplete")
        self.assertEqual(window["abort_reason"], "interrupted")
        self.assertFalse(read_json(root / "window-1/bugfix-a/incomplete.json")["verified_pass"])
        with self.assertRaises(ComparisonError):
            compare_g25.run_window(self.plan, self.bindings, self.adapter("ninfer"), 2, observer=self.observe)
        with self.assertRaises(ComparisonError):
            compare_g25.run_window(self.plan, self.bindings, self.adapter(), 1, observer=self.observe)

    def test_two_consecutive_ooms_abort_all_future_dispatch_and_retain_denominator(self):
        adapter = self.adapter(mode="oom")
        first = compare_g25.run_window(self.plan, self.bindings, adapter, 1, observer=self.observe)
        self.assertEqual(adapter.prepares, 2)
        self.assertEqual(first["abort_reason"], "consecutive_oom")
        self.assertEqual(len(first["attempts"]), 6)
        for row in schedule()[1:]:
            future = self.adapter(row["arm"])
            compare_g25.run_window(self.plan, self.bindings, future, row["window"], observer=self.observe)
            self.assertEqual(future.prepares, 0)
        summary, _, _ = compare_g25.summarize(self.plan, Path(self.bindings["comparison_root"]))
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["arms"]["strata"]["failed_attempts"], 18)
        self.assertIsNone(summary["arms"]["strata"]["all_attempt_wall_ms"])

    def test_harness_drift_refuses_dispatch_and_atomic_publication_refuses_existing_bytes(self):
        adapter = self.adapter()
        self.plan["harness"]["scripts/compare_g25.py"] = "0" * 64
        window = compare_g25.run_window(self.plan, self.bindings, adapter, 1, observer=self.observe)
        self.assertEqual(window["abort_reason"], "harness_modified")
        self.assertEqual(adapter.prepares, 0)
        path = self.root / "result.json"
        compare_g25.publish(path, {"value": 1})
        with self.assertRaises(ComparisonError):
            compare_g25.publish(path, {"value": 2})
        self.assertEqual(read_json(path), {"value": 1})

    def test_init_validate_and_failed_finalize_use_real_cli(self):
        identities = self.root / "identities.json"
        identities.write_bytes(canonical(self.plan))
        draft = self.root / "draft.json"
        prefix = [sys.executable, str(ROOT / "scripts/compare_g25.py")]
        init = subprocess.run(prefix + ["init-plan", "--identities", str(identities), "--comparison-id", "cli-smoke", "--output", str(draft)], capture_output=True, text=True)
        self.assertEqual(init.returncode, 0, init.stderr)
        checked = subprocess.run(prefix + ["validate", "--plan", str(draft), "--draft"], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertTrue(json.loads(checked.stdout)["valid"])
        refused = subprocess.run(prefix + ["init-plan", "--identities", str(draft), "--output", str(self.root / "frozen.json"), "--finalize", "--pilot-root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2)
        self.assertFalse((self.root / "frozen.json").exists())

    def test_both_unscored_pilots_are_required_and_freeze_the_exact_reviewed_draft(self):
        self.plan.update(state="draft", pilot=None)
        draft = self.root / "draft.json"
        compare_g25.publish(draft, self.plan)
        for arm, number in (("strata", 1), ("ninfer", 2)):
            compare_g25.run_window(self.plan, self.bindings, self.adapter(arm), number, observer=self.observe, pilot=True)
        frozen = self.root / "frozen.json"
        with contextlib.redirect_stdout(io.StringIO()):
            status = compare_g25.main(["init-plan", "--identities", str(draft), "--output", str(frozen),
                                       "--finalize", "--pilot-root", self.bindings["comparison_root"]])
        self.assertEqual(status, 0)
        result = read_json(frozen)
        self.assertEqual(result["state"], "frozen")
        for arm in ("strata", "ninfer"):
            self.assertEqual(result["pilot"][arm + "_sha256"],
                             file_sha256(Path(self.bindings["comparison_root"]) / ("pilot-" + arm) / "pilot.json"))
        self.assertFalse((Path(self.bindings["comparison_root"]) / "campaign.json").exists())

    def test_g24_dry_run_remains_frozen_and_solves_all_six_original_tasks(self):
        manifest = read_json(ROOT / "eval/tasks.json")
        self.assertEqual(file_sha256(ROOT / "scripts/evaluate.py"), manifest["files"]["scripts/evaluate.py"])
        result = subprocess.run([sys.executable, str(ROOT / "scripts/evaluate.py"), "--dry-run"], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        reports = [json.loads(line) for line in result.stdout.splitlines()]
        expected = [{"task": task["id"], "passed": True, "seed_passed": False, "reference_passed": True,
                     "visible_seed": task["preexisting_visible_tests"], "workspace_size": task["workspace_size"]}
                    for task in manifest["tasks"]]
        self.assertEqual(reports, expected)


if __name__ == "__main__":
    unittest.main()
