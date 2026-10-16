import copy
import json
from pathlib import Path
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
        with self.assertRaisesRegex(loop.ExperimentError, "unstarted_matching_blocked"):
            loop.validate(retry, releases=self.releases)
        retry["retry_of"] = "f" * 64
        with self.assertRaisesRegex(loop.ExperimentError, "retry_receipt_missing"):
            loop.validate(retry, releases=self.releases)

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
