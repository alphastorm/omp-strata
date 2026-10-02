"""Public contract and matched-batch arithmetic, using synthetic evidence only."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from omp_strata.comparison import (
    ARMS, ComparisonError, DEFAULT_CLAIM_POLICY, TASK_IDS, canonical, claim_decision,
    load_bindings, load_plan, new_plan, plan_digest, read_json, schedule, scheduled_slots, sha256,
    summarize_records, validate_attempt, validate_host_observation, validate_plan,
    validate_summary, validate_window,
)
from scripts.compare_g25 import _window_base, undispatched


def comparison_plan(profile=None):
    if profile is None:
        from omp_strata.profile import load
        from tests.candidate import CANDIDATE, REPO
        profile = load(REPO / "profiles" / (CANDIDATE + ".json"))
    pin = profile.data["omp"]["artifacts"]["windows-x64"]
    identities = {
        "omp": {"platform": "windows-x64", "version": profile.data["omp"]["version"], "bytes": pin["bytes"], "sha256": pin["sha256"]},
        "strata": {"profile_id": profile.id, "profile_fingerprint": profile.fingerprint,
                   "release_manifest_sha256": "1" * 64, "runtime_identity_sha256": "2" * 64,
                   "model_id": profile.data["strata"]["model_name"], "model_identity_sha256": "3" * 64,
                   "quantization": profile.data["model"]["quantization"], "api": "openai-completions", "provider": "strata-local"},
        "ninfer": {"lane": "rtx4090-native", "release_id": "synthetic-release", "manifest_sha256": "4" * 64,
                   "runtime_identity_sha256": "5" * 64, "config_identity_sha256": "6" * 64,
                   "model_identity_sha256": "7" * 64, "model_id": "qwen3.8-27b", "quantization": "synthetic-quant",
                   "api": "openai-responses", "provider": "ninfer-native-4090"},
        "host": {"label": "rtx4090-win-a", "os": "Windows", "os_build": "synthetic-build", "gpu_model": "RTX 4090",
                 "vram_mib": 24576, "driver": "synthetic-driver", "power_policy": "fixed", "clock_policy": "stock",
                 "min_ram_gib": 128, "min_available_ram_gib": 32, "min_commit_headroom_gib": 16, "min_disk_gib": 20},
    }
    plan = new_plan(identities, "synthetic-g25")
    plan.update(state="frozen", pilot={"strata_sha256": "8" * 64, "ninfer_sha256": "9" * 64, "execution_boundary": "evaluation"})
    return plan


def observation_fixture(plan, arm):
    return {"host": {key: plan["host"][key] for key in ("label", "os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy")},
            "ram_gib": 128, "available_ram_gib": 64, "commit_headroom_gib": 32, "disk_gib": 100,
            "gpu_owners": [arm], "process_condition": "process-cold", "file_cache_condition": "warm",
            "startup_ms": 3000, "switch_ms": 4000, "network_observation_sha256": "b" * 64,
            "route_escape": False, "credential_exposure": False, "controller_ok": True, "missing_reasons": {}}


def attempt_fixture(plan, slot, *, passed=True, wall=100):
    from omp_strata.comparison import ROOT
    tasks = read_json(ROOT / "eval/tasks.json")["tasks"]
    task = next(task for task in tasks if task["id"] == slot["task_id"])
    row = undispatched(plan, task, arm=slot["arm"], window=slot["window"], number=slot["attempt_number"], reason="synthetic")
    row.update(status="complete", verified_pass=passed, abort_reason=None, task_wall_ms=wall, reported_output_tokens=5,
               tool_calls=1, compactions=0, config_sha256="c" * 64, models_sha256="d" * 64,
               verifier={"task": task["id"], "passed": passed}, verifier_exit_code=0 if passed else 1,
               transcripts=[{"path": "sessions/synthetic.jsonl", "sha256": "e" * 64}],
               phases=[{"phase": phase, "wall_ms": 10, "exit_code": 0, "completed": True, "abort_reason": None}
                       for phase in range(1, task["phases"] + 1)],
               missing_reasons={"request_wall_ms": "not observed", "server_time_ms": "not observed"})
    return row


def assemble_fixture(plan, attempts):
    windows = []
    for scheduled in schedule():
        window = _window_base(plan, scheduled, "evaluation")
        window.update(status="complete", ended_utc="2026-10-02T00:01:00+00:00", abort_reason=None, exclusive_gpu=True,
                      startup_ms=3000, switch_ms=4000, missing_reasons={},
                      observations=[observation_fixture(plan, scheduled["arm"])] * 7)
        window["attempts"] = [{"task_id": attempt["task_id"], "attempt_number": attempt["attempt_number"],
                               "sha256": sha256(canonical(attempt) + b"\n")}
                              for attempt in attempts if attempt["window"] == scheduled["window"]]
        windows.append(window)
    return windows, summarize_records(plan, windows, attempts)


def comparison_fixture(profile=None):
    """Shared synthetic release evidence. Never a real-host qualification fixture."""
    plan = comparison_plan(profile)
    attempts = [attempt_fixture(plan, slot) for slot in scheduled_slots()]
    windows, summary = assemble_fixture(plan, attempts)
    return plan, windows, summary


class ComparisonContractTests(unittest.TestCase):
    def test_all_slots_are_paired_with_counterbalanced_rotations(self):
        rows = schedule()
        self.assertEqual([row["arm"] for row in rows], ["strata", "ninfer", "ninfer", "strata", "strata", "ninfer"])
        self.assertEqual([row["task_order"] for row in rows], [list(TASK_IDS), list(TASK_IDS),
                         list(TASK_IDS[2:] + TASK_IDS[:2]), list(TASK_IDS[2:] + TASK_IDS[:2]),
                         list(TASK_IDS[4:] + TASK_IDS[:4]), list(TASK_IDS[4:] + TASK_IDS[:4])])
        slots = scheduled_slots()
        self.assertEqual(len(slots), 36)
        for task in TASK_IDS:
            for number in range(1, 4):
                self.assertEqual({slot["arm"] for slot in slots if slot["task_id"] == task and slot["attempt_number"] == number}, set(ARMS))

    def test_plan_is_deeply_immutable_and_digest_ignores_file_whitespace(self):
        plan = comparison_plan()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
            loaded = load_plan(path)
            self.assertEqual(loaded.sha256, plan_digest(plan))
            with self.assertRaises(TypeError):
                loaded["omp"]["sha256"] = "a" * 64
            self.assertEqual(loaded.as_dict(), plan)

    def test_unresolved_identity_private_fields_and_changed_budget_refused(self):
        base = comparison_plan()
        for apply in (lambda p: p["ninfer"].update(runtime_identity_sha256=None),
                      lambda p: p["ninfer"].update(model_id="unresolved"),
                      lambda p: p["omp"].update(api_key="forbidden"),
                      lambda p: p["host"].update(os_build="/private/installation"),
                      lambda p: p["evaluation"]["budgets"]["bugfix-a"].update(tool_calls=41),
                      lambda p: p["claims"].update(engine_only_comparison=True)):
            plan = copy.deepcopy(base)
            apply(plan)
            self.assertTrue(validate_plan(plan))
        self.assertEqual(validate_plan(base), [])

    def test_failures_stay_in_denominator_and_pairs_are_keyed_not_zipped(self):
        plan = comparison_plan()
        rows = [attempt_fixture(plan, slot, passed=slot["arm"] == "strata" and slot["task_id"] != "bugfix-a") for slot in scheduled_slots()]
        windows, summary = assemble_fixture(plan, rows)
        again = summarize_records(plan, list(reversed(windows)), list(reversed(rows)))
        self.assertEqual(summary, again)
        self.assertEqual(summary["arms"]["strata"]["verified_passes"], 15)
        self.assertEqual(summary["arms"]["ninfer"]["failed_attempts"], 18)
        self.assertEqual(summary["outcome_counts"], {"both_pass": 0, "strata_only": 15, "ninfer_only": 0, "both_fail": 3})
        self.assertEqual(summary["arms"]["ninfer"]["all_attempt_wall_ms"], 1800)
        self.assertEqual(validate_summary(summary, plan), [])
        with self.assertRaises(ComparisonError):
            summarize_records(plan, windows, rows[:-1] + [rows[0]])

    def test_missing_timing_is_not_imputed_and_cannot_win_speed_claim(self):
        plan = comparison_plan()
        rows = [attempt_fixture(plan, slot, passed=slot["task_id"] != "bugfix-a") for slot in scheduled_slots()]
        rows[0].update(task_wall_ms=None)
        rows[0]["missing_reasons"]["task_wall_ms"] = "clock sample unavailable"
        windows, summary = assemble_fixture(plan, rows)
        self.assertIsNone(summary["arms"]["strata"]["all_attempt_wall_ms"])
        self.assertEqual(summary["arms"]["strata"]["observed_attempt_wall_ms"], 1700)
        self.assertFalse(summary["claims"]["faster_joint_successes"])
        rows[0]["missing_reasons"].pop("task_wall_ms")
        self.assertTrue(validate_attempt(rows[0], plan))

    def test_complete_batch_claims_require_no_safety_abort_or_host_free_boundary(self):
        plan, windows, summary = comparison_fixture()
        self.assertIsNotNone(summary["claims"]["factual_sentence"])
        rows = [attempt_fixture(plan, slot) for slot in scheduled_slots()]
        windows[0]["abort_reason"] = "route_escape"
        aborted = summarize_records(plan, windows, rows)
        self.assertFalse(aborted["complete"])
        self.assertIsNone(aborted["claims"]["factual_sentence"])
        windows, _ = assemble_fixture(plan, rows)
        for window in windows:
            window["execution_boundary"] = "host_free"
        self.assertIsNone(summarize_records(plan, windows, rows)["claims"]["factual_sentence"])

    def test_claim_thresholds_and_just_outside_boundaries(self):
        plan = comparison_plan()
        def decision(delta=3, joint=12, ratio=.8, total_ratio=1, complete=True, strata_only=3, ninfer_only=0):
            arms = {"strata": {"verified_passes": 12 + delta, "all_attempt_wall_ms": 1800 * total_ratio},
                    "ninfer": {"verified_passes": 12, "all_attempt_wall_ms": 1800}}
            return claim_decision(plan, complete=complete, arms=arms,
                                  outcome_counts={"strata_only": strata_only, "ninfer_only": ninfer_only}, joint_ratios=[ratio] * joint)
        self.assertTrue(decision()["higher_verified_completion_count"])
        self.assertFalse(decision(delta=2)["higher_verified_completion_count"])
        self.assertFalse(decision(strata_only=2, ninfer_only=2)["higher_verified_completion_count"])
        self.assertTrue(decision()["faster_joint_successes"])
        for values in ({"joint": 11}, {"ratio": .8000001}, {"total_ratio": 1.0000001}, {"complete": False}):
            self.assertFalse(decision(**values)["faster_joint_successes"])
        self.assertTrue(decision(joint=13, ratio=.79, total_ratio=.99)["faster_joint_successes"])

    def test_window_and_summary_tampering_is_rejected(self):
        plan, windows, summary = comparison_fixture()
        self.assertEqual(validate_window(windows[0], plan), [])
        windows[0]["attempts"] = windows[0]["attempts"][:-1]
        self.assertTrue(validate_window(windows[0], plan))
        summary["claims"]["engine_only_comparison"] = True
        self.assertTrue(validate_summary(summary, plan))

    def test_missing_or_wrongly_typed_record_boundaries_are_refused(self):
        plan, windows, summary = comparison_fixture()
        del windows[0]["consecutive_oom"]
        self.assertTrue(validate_window(windows[0], plan))
        attempt = attempt_fixture(plan, scheduled_slots()[0])
        attempt["window"] = True
        self.assertTrue(validate_attempt(attempt, plan))
        del summary["execution_boundary"]
        self.assertTrue(validate_summary(summary, plan))

    def test_host_safety_floors_ownership_and_switch_deadline(self):
        plan = comparison_plan()
        valid = observation_fixture(plan, "strata")
        self.assertEqual(validate_host_observation(valid, plan, "strata"), [])
        for field, value, reason in (("available_ram_gib", 31.999, "host_state_drift"),
                                     ("gpu_owners", ["strata", "ninfer"], "concurrent_gpu_owner"),
                                     ("switch_ms", 300001, "switch_failure"),
                                     ("route_escape", True, "route_escape"),
                                     ("credential_exposure", True, "credential_exposure")):
            observation = copy.deepcopy(valid)
            observation[field] = value
            self.assertIn(reason, validate_host_observation(observation, plan, "strata"))

    def test_private_bindings_enforce_installation_boundaries_and_owner_permissions(self):
        plan = comparison_plan()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            comparison = root / "comparison"
            comparison.mkdir()
            bindings = {"schema_version": 1, "comparison_id": plan["comparison_id"],
                        "comparison_root": str(comparison), "omp_binary": str(root / "omp"),
                        "execution_boundary": "host_free", "host_probe_argv": ["read-only-probe"]}
            (root / "omp").write_text("synthetic", encoding="utf-8")
            for arm in ARMS:
                install = root / arm
                install.mkdir()
                binding = {"root": str(install), "port": 12345, "key_file": str(install / "key"),
                           "manifest": str(root / (arm + "-manifest.json"))}
                binding.update({"profile": str(root / "profile.json")} if arm == "strata" else
                               {"controller": str(install / "controller"), "state_root": str(install / "state"),
                                "status_file": str(comparison / "status.json")})
                for name, value in binding.items():
                    if name not in {"root", "port", "state_root"}:
                        Path(value).write_text("{}", encoding="utf-8")
                bindings[arm] = binding
            path = comparison / "bindings.json"
            path.write_bytes(canonical(bindings))
            path.chmod(0o600)
            self.assertEqual(load_bindings(path, plan), bindings)
            bindings["strata"]["key_file"] = str(root / "foreign-key")
            (root / "foreign-key").write_text("not-a-real-key", encoding="utf-8")
            path.write_bytes(canonical(bindings))
            with self.assertRaises(ComparisonError):
                load_bindings(path, plan)


if __name__ == "__main__":
    unittest.main()
