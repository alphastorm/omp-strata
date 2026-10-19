import copy
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json
from scripts import experiment_loop as loop
from scripts.publish_run import PublicationError, Scrubber

BASELINE = "win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1"
CANDIDATE = "win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1"
NEXT = "win11-rtx5090-coder-iq1m-131k-strata0.1.43.1-omp18.10.1"
PRO_BASELINE = "win11-rtxpro6000-coder-iq1m-131k-strata0.1.44.1-omp18.10.1"
PRO_CANDIDATE = "win11-rtxpro6000-coder-iq1m-262k-strata0.1.44.1-omp18.10.1"


def admitted():
    return dict(reachable=True, gpu_idle=True, ram_above_floor=True, disk_above_floor=True,
                no_competing_tenant=True, predecessor_matches=True, doctor_ok=True)


class FakeAdapter:
    def __init__(self):
        self.lock_id = "rtx5090-win-a"
        self.scrubber = Scrubber("D:/private-root", private=["fixture-host", "192.0.2.55"])
        self.events = []
        self.observation = admitted()
        self.fail_at = None
        self.restore_serving = True
        self.result = {"status": "complete", "samples": [], "queue": {"both_complete": True}}

    def event(self, name):
        self.events.append(name)
        if name == self.fail_at:
            raise loop.ExperimentError("probe_failed")

    def precondition(self, manifest, timeout):
        self.event("precondition")
        return self.observation.copy()

    def install(self, manifest, timeout):
        self.event("install")

    def start(self, arm, timeout):
        self.event("start:" + arm)

    def stop(self, arm, timeout):
        self.event("stop:" + arm)

    def settle(self, timeout):
        self.event("settle")
        return {"status": "ready", "observations": []}

    def guard(self, arm, timeout):
        self.event("guard:" + arm)

    def probe(self, arm, workload, timeout):
        self.event("probe:" + arm)
        return copy.deepcopy(self.result)

    def restore(self, manifest):
        self.event("restore")
        return {"status": "restored" if self.restore_serving else "failed", "serving": self.restore_serving,
                "gate": {"gate": "G10", "pass_observed": self.restore_serving}}


class ExperimentLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.releases = self.root / "experiments"
        self.locks = self.root / "locks"
        self.manifest = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Compare qualified context variants.")
        self.adapter = FakeAdapter()

    def run_trial(self):
        return loop.run(self.manifest, self.adapter, releases=self.releases, lock_directory=self.locks)

    def read(self, directory, name):
        return json.loads((directory / (name + ".json")).read_text())

    def test_healthy_admission_runs_both_arms_and_restores(self):
        directory = self.run_trial()
        measurements = self.read(directory, "measurements")
        self.assertEqual(measurements["status"], "complete")
        for arm in ("baseline", "candidate"):
            self.assertEqual([r["repetition"] for r in measurements[arm]], [1, 2])
            self.assertEqual(self.adapter.events.count("probe:" + arm), 2)
        self.assertLess(self.adapter.events.index("stop:baseline"), self.adapter.events.index("start:candidate"))
        self.assertEqual(self.adapter.events[-1], "restore")
        self.assertTrue(self.read(directory, "restoration")["gate"]["pass_observed"])
        self.assertFalse(list(self.locks.glob("*.lock")))
        self.assertEqual(set(p.name for p in directory.iterdir()),
                         {"manifest.json", "measurements.json", "failures.json", "restoration.json"})

    def test_dedupe_refuses_replay_even_with_different_workload_or_repetitions(self):
        self.run_trial()
        self.manifest["repetitions"] = 3
        self.manifest["workload"]["depths"] = [0]
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.validate(self.manifest, releases=self.releases)
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            self.run_trial()
        self.assertEqual(self.adapter.events.count("install"), 1)

    def test_all_preconditions_are_fail_closed_without_any_lifecycle_mutation(self):
        for name in admitted():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                adapter = FakeAdapter()
                adapter.observation[name] = False
                directory = loop.run(self.manifest, adapter, releases=Path(tmp) / "releases", lock_directory=self.locks)
                self.assertEqual(adapter.events, ["precondition"])
                self.assertEqual(self.read(directory, "measurements")["status"], "blocked")
                self.assertEqual(self.read(directory, "restoration")["status"], "not_required")
                self.assertIn(name, self.read(directory, "failures")[0]["reason"])
        with self.assertRaises(loop.ExperimentError):
            loop.check_preconditions({})

    def test_live_lock_owner_is_not_stolen_or_unlinked(self):
        self.locks.mkdir()
        path = self.locks / (self.adapter.lock_id + ".lock")
        path.write_text('{"pid": 12345}')
        directory = self.run_trial()
        self.assertEqual(self.adapter.events, [])
        self.assertEqual(path.read_text(), '{"pid": 12345}')
        self.assertEqual(self.read(directory, "failures")[0]["reason"], "host_lock_owned")

    def test_restore_runs_on_install_start_probe_stop_failure(self):
        for failure in ("install", "start:baseline", "probe:baseline", "stop:baseline", "start:candidate", "probe:candidate"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                adapter = FakeAdapter()
                adapter.fail_at = failure
                directory = loop.run(self.manifest, adapter, releases=Path(tmp), lock_directory=self.locks)
                self.assertEqual(adapter.events[-1], "restore")
                self.assertTrue(self.read(directory, "restoration")["serving"])
                self.assertTrue(self.read(directory, "failures"))
                self.assertEqual(self.read(directory, "measurements")["status"], "failed")

    def test_wall_limit_stops_dispatch_but_does_not_skip_restoration(self):
        now = [0]
        original = self.adapter.install
        def install(manifest, timeout):
            original(manifest, timeout)
            now[0] = manifest["stop_conditions"]["max_wall_time_s"]
        self.adapter.install = install
        directory = loop.run(self.manifest, self.adapter, releases=self.releases,
                             lock_directory=self.locks, clock=lambda: now[0])
        self.assertEqual(self.adapter.events, ["precondition", "install", "restore"])
        self.assertEqual(self.read(directory, "failures")[0]["reason"], "max_wall_time")
        self.assertTrue(self.read(directory, "restoration")["serving"])

    def test_failure_budget_preserves_results_and_stops_exactly_at_limit(self):
        self.manifest["stop_conditions"]["max_failures"] = 2
        self.adapter.result["status"] = "error"
        directory = self.run_trial()
        data = self.read(directory, "measurements")
        self.assertEqual(len(data["baseline"]), 2)
        self.assertEqual(data["candidate"], [])
        self.assertEqual(self.adapter.events.count("probe:baseline"), 2)
        self.assertEqual(self.adapter.events[-1], "restore")

    def test_restoration_failure_is_not_reported_as_success(self):
        self.adapter.restore_serving = False
        directory = self.run_trial()
        self.assertEqual(self.read(directory, "measurements")["status"], "restoration_failed")
        self.assertFalse(self.read(directory, "restoration")["serving"])
        self.assertEqual(loop.report(directory)["recommendation"], "hold")

    def test_report_refuses_context_model_quant_and_protocol_confounding(self):
        directory = self.run_trial()
        self.assertFalse(loop.report(directory)["engine_only_comparison"])
        with self.assertRaisesRegex(loop.ExperimentError, "engine_only_claim_refused"):
            loop.report(directory, engine_only=True)
        for key, value in (("model", {"repository": "other/model"}), ("quantization", "Q2_0"),
                           ("protocol", "openai-responses")):
            changed = copy.deepcopy(self.manifest)
            changed["candidate"] = copy.deepcopy(changed["baseline"])
            changed["candidate"]["engine"] = "0.1.44.2"
            changed["candidate"][key] = value
            atomic_write_json(directory / "manifest.json", changed)
            with self.subTest(key=key), self.assertRaisesRegex(loop.ExperimentError, "engine_only_claim_refused"):
                loop.report(directory, engine_only=True)

    def test_throughput_alone_never_adopts(self):
        self.adapter.result["samples"] = [{"metrics": [{"name": "decode_tokens_s", "value": 1000000}]}]
        directory = self.run_trial()
        self.assertEqual(loop.report(directory)["recommendation"], "hold")

    def test_scrub_applies_before_publication(self):
        self.adapter.observation["fixture"] = "fixture-host at 192.0.2.55 under D:/private-root/evidence"
        self.adapter.result["raw_log"] = "unpublished raw text without a private identifier"
        directory = self.run_trial()
        text = (directory / "measurements.json").read_text()
        for private in ("fixture-host", "192.0.2.55", "D:/private-root"):
            self.assertNotIn(private, text)
        self.assertIn("<redacted>", text)
        self.assertIn("<root>", text)
        self.assertNotIn("raw_log", text)
        self.assertNotIn("unpublished raw text", text)
        unsafe = self.root / "unsafe.json"
        with self.assertRaises(PublicationError):
            loop.public_write(unsafe, {"unreviewed": "unreviewed-fixture"},
                              Scrubber("D:/private-root", denylist=["unreviewed-fixture"]))
        self.assertFalse(unsafe.exists())

    def test_frozen_profile_and_harness_drift_refuse(self):
        self.manifest["candidate"]["config"]["setup_args"]["context"] = 524288
        with self.assertRaisesRegex(loop.ExperimentError, "frozen_profile_drift"):
            loop.validate(self.manifest, releases=self.releases)
        self.manifest = loop.new_manifest(BASELINE, CANDIDATE, rationale="fixture")
        self.manifest["harness_files"]["scripts/perf_probe.py"] = "0" * 64
        with self.assertRaisesRegex(loop.ExperimentError, "frozen_harness_drift"):
            loop.validate(self.manifest, releases=self.releases)

    def test_manifest_limits_and_safety_flags_are_enforced(self):
        cases = [("repetitions", 0), ("repetitions", 21), ("repetitions", True)]
        for key, value in cases:
            with self.subTest(value=value):
                manifest = copy.deepcopy(self.manifest)
                manifest[key] = value
                with self.assertRaises(loop.ExperimentError):
                    loop.validate(manifest, releases=self.releases)
        for key in ("abort_on_gpu_busy", "abort_on_competing_tenant", "abort_on_disk_floor"):
            manifest = copy.deepcopy(self.manifest)
            manifest["stop_conditions"][key] = False
            with self.assertRaises(loop.ExperimentError):
                loop.validate(manifest, releases=self.releases)
        self.manifest["workload"]["depths"] = [131072 - 512 - 8]
        with self.assertRaisesRegex(loop.ExperimentError, "workload_exceeds_common_context"):
            loop.validate(self.manifest, releases=self.releases)

    def test_unknown_fields_and_restoration_mismatch_refuse(self):
        self.manifest["shell"] = "not executable authority"
        with self.assertRaisesRegex(loop.ExperimentError, "invalid_manifest_schema"):
            loop.validate(self.manifest, releases=self.releases)
        del self.manifest["shell"]
        self.manifest["restoration_target"] = self.manifest["candidate"]
        with self.assertRaisesRegex(loop.ExperimentError, "restoration_must_match_predecessor"):
            loop.validate(self.manifest, releases=self.releases)

    def test_next_queues_one_frozen_distinct_trial_without_execution(self):
        directory = self.run_trial()
        events = self.adapter.events.copy()
        queue = loop.propose_next(directory, NEXT, releases=self.releases)
        self.assertFalse(queue["automatic_execution"])
        self.assertEqual(len(queue["trials"]), 1)
        queued = queue["trials"][0]
        self.assertEqual(loop.validate(queued["manifest"], releases=self.releases), queued["key"])
        self.assertNotEqual(queued["key"], loop.identity_key(self.manifest))
        self.assertEqual(events, self.adapter.events)
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.propose_next(directory, CANDIDATE, releases=self.releases)

    def test_record_blocked_is_not_a_mock_measurement_or_authorization(self):
        observation = admitted()
        observation.update(timestamp_utc="2026-10-16T00:00:00Z", wall_time_s=2.0)
        with self.assertRaisesRegex(loop.ExperimentError, "observation_does_not_establish_blocker"):
            loop.record_blocked(self.manifest, observation, releases=self.releases)
        observation["gpu_idle"] = False
        directory = loop.record_blocked(self.manifest, observation, releases=self.releases)
        self.assertEqual(self.read(directory, "measurements")["baseline"], [])
        self.assertIsNone(self.read(directory, "restoration")["serving"])
        self.assertEqual(self.read(directory, "measurements")["status"], "blocked")

    def test_blocked_retry_preserves_original_and_has_one_append_only_attempt(self):
        self.adapter.observation["gpu_idle"] = False
        prior = self.run_trial()
        original = (prior / "measurements.json").read_bytes()
        retry = loop.new_manifest(BASELINE, CANDIDATE, rationale="Owner released the GPU.",
                                  retry_of=prior.name)
        key = loop.validate(retry, releases=self.releases)
        self.assertNotEqual(key, prior.name)
        self.adapter.observation["gpu_idle"] = True
        directory = loop.run(retry, self.adapter, releases=self.releases, lock_directory=self.locks)
        self.assertEqual(self.read(directory, "measurements")["status"], "complete")
        self.assertEqual((prior / "measurements.json").read_bytes(), original)
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.validate(retry, releases=self.releases)

    def test_retry_refuses_completed_or_mismatched_trial(self):
        prior = self.run_trial()
        retry = loop.new_manifest(BASELINE, CANDIDATE, rationale="fixture", retry_of=prior.name)
        with self.assertRaisesRegex(loop.ExperimentError, "matching_blocked_or_restored_failed"):
            loop.validate(retry, releases=self.releases)
        retry["retry_of"] = "f" * 64
        with self.assertRaisesRegex(loop.ExperimentError, "retry_receipt_missing"):
            loop.validate(retry, releases=self.releases)

    def test_candidate_resume_preserves_measured_baseline_provenance(self):
        self.adapter.fail_at = "start:candidate"
        prior = self.run_trial()
        adapter = FakeAdapter()
        manifest = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Retry the unstarted arm.",
                                     retry_of=prior.name, resume_candidate=True)
        directory = loop.run(manifest, adapter, releases=self.releases, lock_directory=self.locks)
        measured = self.read(directory, "measurements")
        self.assertEqual(measured["status"], "complete")
        self.assertEqual(measured["baseline_source_experiment"], prior.name)
        self.assertEqual([r["source_experiment"] for r in measured["baseline"]], [prior.name] * 2)
        self.assertNotIn("start:baseline", adapter.events)
        self.assertEqual(adapter.events.count("probe:candidate"), 2)
        self.assertTrue(self.read(directory, "restoration")["serving"])
        manifest["repetitions"] = 3
        with self.assertRaisesRegex(loop.ExperimentError, "complete_baseline"):
            loop.validate(manifest, releases=self.releases)

    # Synthetic receipts only: these exercise retry admission, never real-host restoration or performance.
    def restored_failure(self):
        self.adapter.fail_at = "start:candidate"
        return self.run_trial()

    def receipt_copy(self, prior, name=None, edit=None):
        """Copy a synthetic receipt into fresh releases and optionally rewrite one of its files."""
        releases = Path(tempfile.mkdtemp(dir=self.root))
        shutil.copytree(prior, releases / (name or prior.name))
        if edit:
            edit(releases / (name or prior.name))
        return releases

    def assert_refused_before_mutation(self, manifest, releases, reason):
        before = sorted(p.name for p in releases.iterdir())
        adapter = FakeAdapter()
        with self.assertRaisesRegex(loop.ExperimentError, reason) as caught:
            loop.run(manifest, adapter, releases=releases, lock_directory=self.locks)
        self.assertEqual(adapter.events, [])
        self.assertEqual(sorted(p.name for p in releases.iterdir()), before)
        return str(caught.exception)

    def test_retry_refuses_matching_receipt_copied_under_another_key(self):
        self.adapter.observation["gpu_idle"] = False
        prior = self.run_trial()
        alias = "e" * 64
        releases = self.receipt_copy(prior, alias)
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=alias)
        self.assert_refused_before_mutation(retry, releases, "retry_receipt_key_mismatch")

    def test_restored_failure_retry_remains_eligible_and_keeps_receipt_bytes(self):
        prior = self.restored_failure()
        original = {p.name: p.read_bytes() for p in prior.iterdir()}
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=prior.name)
        directory = loop.run(retry, FakeAdapter(), releases=self.releases, lock_directory=self.locks)
        self.assertEqual(self.read(directory, "measurements")["status"], "complete")
        self.assertEqual({p.name: p.read_bytes() for p in prior.iterdir()}, original)

    def test_malformed_retry_receipts_refuse_with_closed_public_safe_reason(self):
        prior = self.restored_failure()
        marker = "private-receipt-marker"

        def write(name, text):
            return lambda d: (d / (name + ".json")).write_text(text)

        def rewrite(name, change):
            def edit(d):
                data = json.loads((d / (name + ".json")).read_text())
                change(data)
                (d / (name + ".json")).write_text(json.dumps(data))
            return edit

        cases = {
            "missing_measurements": lambda d: (d / "measurements.json").unlink(),
            "missing_restoration": lambda d: (d / "restoration.json").unlink(),
            "malformed_json": write("measurements", '{"status": "' + marker),
            "duplicate_key": write("restoration", '{"status": "restored", "status": "' + marker + '"}'),
            "non_object_measurements": write("measurements", json.dumps([marker])),
            "non_object_restoration": write("restoration", json.dumps(marker)),
            "manifest_schema": rewrite("manifest", lambda m: m.update(shell=marker)),
            "manifest_missing_field": rewrite("manifest", lambda m: m.pop("harness_files")),
            "missing_status": rewrite("measurements", lambda m: m.pop("status")),
            "non_string_status": rewrite("measurements", lambda m: m.update(status=[marker])),
            "missing_arm": rewrite("measurements", lambda m: m.pop("candidate")),
            "non_list_arm": rewrite("measurements", lambda m: m.update(baseline={"1": marker})),
            "non_object_row": rewrite("measurements", lambda m: m.update(baseline=[marker])),
            "row_missing_result": rewrite("measurements", lambda m: m["baseline"][0].pop("result")),
            "row_string_result": rewrite("measurements", lambda m: m["baseline"][0].update(result=marker)),
            "row_string_repetition": rewrite("measurements", lambda m: m["baseline"][0].update(repetition="1")),
            "row_boolean_repetition": rewrite("measurements", lambda m: m["baseline"][0].update(repetition=True)),
            "missing_restoration_status": rewrite("restoration", lambda m: m.pop("status")),
            "missing_serving": rewrite("restoration", lambda m: m.pop("serving")),
            "non_boolean_serving": rewrite("restoration", lambda m: m.update(serving=marker)),
        }
        for case, edit in cases.items():
            for resume in (False, True):
                with self.subTest(case=case, resume=resume):
                    releases = self.receipt_copy(prior, edit=edit)
                    retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                              retry_of=prior.name, resume_candidate=resume)
                    reason = self.assert_refused_before_mutation(retry, releases, "^retry_receipt_")
                    self.assertNotIn(marker, reason)
                    self.assertNotIn(str(self.root), reason)
                    self.assertNotIn("json", reason)

    def test_missing_fields_are_never_synthesized_into_restoration(self):
        prior = self.restored_failure()
        releases = self.receipt_copy(prior, edit=lambda d: (d / "restoration.json").write_text(
            json.dumps({"status": "restored", "serving": None})))
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=prior.name)
        self.assert_refused_before_mutation(retry, releases, "matching_blocked_or_restored_failed")

    def test_running_and_restoration_failed_trials_remain_ineligible(self):
        prior = self.restored_failure()
        for status in ("running", "complete", "restoration_failed"):
            with self.subTest(status=status):
                def edit(d, status=status):
                    data = json.loads((d / "measurements.json").read_text())
                    data["status"] = status
                    (d / "measurements.json").write_text(json.dumps(data))
                releases = self.receipt_copy(prior, edit=edit)
                retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                          retry_of=prior.name)
                self.assert_refused_before_mutation(retry, releases, "matching_blocked_or_restored_failed")

    def test_candidate_resume_refuses_baseline_measured_by_another_harness(self):
        prior = self.restored_failure()
        path = prior / "manifest.json"
        data = json.loads(path.read_text())
        data["harness_files"]["scripts/perf_probe.py"] = "0" * 64
        path.write_text(json.dumps(data))
        original = {p.name: p.read_bytes() for p in prior.iterdir()}
        resume = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                   retry_of=prior.name, resume_candidate=True)
        self.assert_refused_before_mutation(resume, self.releases, "complete_baseline")
        # The explicit full retry may use newly frozen tooling; it re-measures both arms.
        retry = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture", retry_of=prior.name)
        adapter = FakeAdapter()
        directory = loop.run(retry, adapter, releases=self.releases, lock_directory=self.locks)
        self.assertEqual(adapter.events.count("probe:baseline"), 2)
        self.assertNotIn("baseline_source_experiment", self.read(directory, "measurements"))
        self.assertEqual({p.name: p.read_bytes() for p in prior.iterdir()}, original)

    def test_candidate_resume_refuses_incomplete_or_misnumbered_baseline(self):
        prior = self.restored_failure()
        row = json.loads((prior / "measurements.json").read_text())["baseline"][0]

        def rows(*numbers, status="complete"):
            return [dict(copy.deepcopy(row), repetition=n, result=dict(row["result"], status=status))
                    for n in numbers]

        cases = {"duplicate": rows(1, 1), "missing": rows(1), "reordered": rows(2, 1),
                 "out_of_range": rows(1, 3), "zero_based": rows(0, 1), "extra": rows(1, 2, 3),
                 "incomplete": rows(1, 2, status="error"),
                 "result_without_status": [dict(r, result={}) for r in rows(1, 2)]}
        for case, baseline in cases.items():
            with self.subTest(case=case):
                def edit(d, baseline=baseline):
                    data = json.loads((d / "measurements.json").read_text())
                    data["baseline"] = baseline
                    (d / "measurements.json").write_text(json.dumps(data))
                releases = self.receipt_copy(prior, edit=edit)
                resume = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                           retry_of=prior.name, resume_candidate=True)
                self.assert_refused_before_mutation(resume, releases, "complete_baseline")

        def candidate_row(d):
            data = json.loads((d / "measurements.json").read_text())
            data["candidate"] = rows(1)
            (d / "measurements.json").write_text(json.dumps(data))
        resume = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="fixture",
                                   retry_of=prior.name, resume_candidate=True)
        self.assert_refused_before_mutation(resume, self.receipt_copy(prior, edit=candidate_row), "complete_baseline")
        for change in ({"repetitions": 3}, {"workload": dict(resume["workload"], depths=[0])}):
            with self.subTest(change=sorted(change)):
                changed = dict(copy.deepcopy(resume), **change)
                self.assert_refused_before_mutation(changed, self.receipt_copy(prior), "complete_baseline")

    def test_ram_settle_is_bounded_and_never_lowers_the_floor(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.ram_floor = 36
        now = [0]
        def sleep(seconds):
            now[0] += seconds
        with patch.object(loop.procs, "memory", return_value={"available": 35 * (1 << 30)}):
            result = adapter.settle(900, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(result["status"], "below_floor")
        self.assertEqual(now[0], 90)
        self.assertEqual(result["ram_floor_gib"], 36)
        now[0] = 0
        with patch.object(loop.procs, "memory", side_effect=[{"available": 35 * (1 << 30)},
                                                            {"available": 36 * (1 << 30)}]):
            result = adapter.settle(20, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(now[0], 5)

    def test_pro_host_profile_is_frozen_and_mismatched_gpu_refuses(self):
        manifest = loop.new_manifest(PRO_BASELINE, PRO_CANDIDATE, rationale="Same Coder context comparison.",
                                     host_profile="rtxpro6000-win-a")
        loop.validate(manifest, releases=self.releases)
        self.assertEqual(manifest["baseline"]["config"]["host"]["min_gpu_vram_mib"], 97000)
        manifest["host_role"] = "rtx5090-win-a"
        with self.assertRaisesRegex(loop.ExperimentError, "host_profile_mismatch"):
            loop.validate(manifest, releases=self.releases)

    def test_display_clients_are_tolerated_but_foreign_compute_is_not(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.disk_floor = 1
        layout = SimpleNamespace(root=self.root, profile=SimpleNamespace(data={"host": {"display_attached": True}}))
        adapter.layouts = {"baseline": layout}
        gpu = {"available": True, "processes": [{"pid": 10, "type": "C"}, {"pid": 20, "type": "G"}]}
        with patch.object(loop.lifecycle, "status", return_value={"state": "healthy"}), \
             patch.object(loop.lifecycle, "running", return_value={"server": SimpleNamespace(pid=10)}), \
             patch.object(loop.lifecycle, "gpu_facts", return_value=gpu):
            adapter.guard("baseline", 10)
            gpu["processes"][1]["type"] = "C"
            with self.assertRaisesRegex(loop.ExperimentError, "competing_tenant"):
                adapter.guard("baseline", 10)

    def test_host_adapter_refuses_non_windows_without_lifecycle_calls(self):
        with patch.object(loop.sys, "platform", "darwin"), self.assertRaisesRegex(loop.ExperimentError, "native_windows"):
            loop.HostAdapter(self.manifest, {})


if __name__ == "__main__":
    unittest.main()
