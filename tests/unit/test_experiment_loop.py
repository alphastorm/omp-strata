import copy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json, sha256_file
from scripts import eval_taskset, experiment_loop as loop
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

    def quiesce(self, manifest, timeout):
        self.event("quiesce")
        return {"mode": "loop_quiesced_warm", "profile_fingerprint": manifest["baseline"]["profile_fingerprint"]}

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
        self.restored_profile = manifest["restoration_target"]["profile_id"]
        self.event("restore")
        return {"status": "restored" if self.restore_serving else "failed", "serving": self.restore_serving,
                "profile_id": self.restored_profile,
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

    def test_opt_in_warm_handoff_runs_under_claim_and_is_receipted(self):
        original = self.adapter.quiesce
        def quiesce(manifest, timeout):
            self.assertTrue((self.locks / (self.adapter.lock_id + ".lock")).is_file())
            return original(manifest, timeout)
        self.adapter.quiesce = quiesce
        directory = loop.run(self.manifest, self.adapter, releases=self.releases,
                             lock_directory=self.locks, quiesce_incumbent=True)
        self.assertEqual(self.adapter.events[0], "quiesce")
        self.assertEqual(self.read(directory, "measurements")["incumbent_handoff"]["mode"], "loop_quiesced_warm")
        self.assertTrue(self.read(directory, "restoration")["serving"])
        self.assertFalse((self.locks / (self.adapter.lock_id + ".lock")).exists())

    def test_quiesce_failure_is_already_a_mutation_and_always_restores(self):
        self.adapter.fail_at = "quiesce"
        directory = loop.run(self.manifest, self.adapter, releases=self.releases,
                             lock_directory=self.locks, quiesce_incumbent=True)
        self.assertEqual(self.adapter.events, ["quiesce", "restore"])
        self.assertEqual(self.read(directory, "measurements")["status"], "failed")
        self.assertTrue(self.read(directory, "restoration")["serving"])

    def test_per_arm_disk_floor_keeps_qualified_baseline_on_its_own_drive(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.disk_floor = 206
        adapter.disk_floors = {"baseline": 91, "candidate": 206}
        record = self.root / "incumbent.json"
        record.write_text(json.dumps({"profile_fingerprint": self.manifest["baseline"]["profile_fingerprint"]}))
        adapter.layouts = {arm: SimpleNamespace(root=self.root / arm, install_record=record,
            profile=SimpleNamespace(data={"host": {"min_available_ram_gib_at_start": 8,
                                                    "min_free_disk_gib": floor}}))
                           for arm, floor in adapter.disk_floors.items()}
        adapter.layouts["restoration_target"] = adapter.layouts["baseline"]
        adapter.disk_floors["restoration_target"] = adapter.disk_floors["baseline"]
        with patch.object(loop.lifecycle, "doctor", return_value={"ok": True, "checks": []}), \
                patch.object(loop.lifecycle, "gpu_facts", return_value={"available": True}), \
                patch.object(loop.lifecycle, "gpu_busy", return_value=None), \
                patch.object(loop.lifecycle, "port_in_use", return_value=False), \
                patch.object(loop.procs, "memory", return_value={"available": 100 * (1 << 30)}), \
                patch.object(shutil, "disk_usage", side_effect=lambda root: SimpleNamespace(
                    free=(153 if root.name == "baseline" else 1000) * (1 << 30))):
            for layout in adapter.layouts.values():
                layout.profile.data["server"] = {"port": 18090}
            observed = adapter.precondition(self.manifest, 120)
        self.assertTrue(observed["disk_above_floor"])
        self.assertEqual(91, observed["disk_by_arm"]["baseline"]["floor_gib"])
        self.assertEqual(206, observed["disk_by_arm"]["candidate"]["floor_gib"])

    def test_failed_restoration_retains_the_physical_claim_for_reconciliation(self):
        self.adapter.restore_serving = False
        directory = self.run_trial()
        self.assertEqual(self.read(directory, "measurements")["status"], "restoration_failed")
        self.assertTrue((self.locks / (self.adapter.lock_id + ".lock")).is_file())

    def test_taskset_scheduler_cannot_steal_a_dead_failed_restoration_hold(self):
        from scripts import eval_taskset
        self.adapter.restore_serving = False
        self.run_trial()
        path = self.locks / (self.adapter.lock_id + ".lock")
        before = path.read_bytes()
        with patch.object(eval_taskset.os, "kill", side_effect=ProcessLookupError):
            self.assertFalse(eval_taskset.take_pid_file(path))
        self.assertEqual(before, path.read_bytes())
        self.assertIs(json.loads(before)["persistent_hold"], True)

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
        self.assertFalse(self.releases.exists())
        observation["gpu_idle"] = False
        with patch.object(loop, "HostAdapter", side_effect=AssertionError("adapter")), \
                patch.object(loop, "host_lock", side_effect=AssertionError("host_lock")), \
                patch.object(loop, "lifecycle", None):
            directory = loop.record_blocked(self.manifest, observation, releases=self.releases)
        measurements = self.read(directory, "measurements")
        self.assertEqual((measurements["baseline"], measurements["candidate"]), ([], []))
        self.assertEqual((measurements["started_utc"], measurements["wall_time_s"]), ("2026-10-16T00:00:00Z", 2.0))
        self.assertEqual(measurements["status"], "blocked")
        self.assertEqual(self.read(directory, "failures"), [{"reason": "precondition:gpu_idle"}])
        restoration = self.read(directory, "restoration")
        self.assertEqual(restoration["status"], "not_required")
        self.assertIsNone(restoration["serving"])

    def blocked_observation(self, **changes):
        observation = admitted()
        observation.update(gpu_idle=False, timestamp_utc="2026-10-16T00:00:00Z", wall_time_s=2.0)
        observation.update(changes)
        return observation

    def assert_blocked_refused(self, observation, reason="invalid_observation"):
        key = loop.identity_key(self.manifest)
        with self.assertRaises(loop.ExperimentError) as caught:
            loop.record_blocked(self.manifest, observation, releases=self.releases)
        self.assertEqual(str(caught.exception), reason)
        # Refusal happens before the identity is reserved: no directory and no public bytes.
        self.assertFalse((self.releases / key).exists())
        self.assertEqual(list(self.releases.rglob("*")) if self.releases.exists() else [], [])

    def test_record_blocked_refuses_malformed_observations_before_creating_a_directory(self):
        cases = [None, [], "gpu_idle=false", self.blocked_observation(timestamp_utc=None)]
        for name in loop.ADMISSION_FLAGS:
            missing = self.blocked_observation()
            del missing[name]
            cases += [missing, self.blocked_observation(**{name: "false"}),
                      self.blocked_observation(**{name: 0}), self.blocked_observation(**{name: None})]
        for timestamp in ("2026-10-16T00:00:00", "2026-10-16T02:00:00+02:00", "not a time", "",
                          "2026-13-01T00:00:00Z", 1760572800):
            cases.append(self.blocked_observation(timestamp_utc=timestamp))
        for duration in (-0.001, True, False, float("nan"), float("inf"), float("-inf"), "2.0", None):
            cases.append(self.blocked_observation(wall_time_s=duration))
        missing = self.blocked_observation()
        del missing["wall_time_s"]
        cases.append(missing)
        for observation in cases:
            with self.subTest(observation=observation):
                self.assert_blocked_refused(observation)
        # An absent flag is invalid input, never evidence of a measured blocker; all-true still refuses.
        self.assert_blocked_refused(self.blocked_observation(gpu_idle=True), "observation_does_not_establish_blocker")
        observation = self.blocked_observation(timestamp_utc="2026-10-16T00:00:00+00:00", wall_time_s=0)
        directory = loop.record_blocked(self.manifest, observation, releases=self.releases)
        self.assertEqual(self.read(directory, "measurements")["wall_time_s"], 0)

    def test_record_blocked_scrubber_refusal_leaves_identity_unconsumed(self):
        key = loop.identity_key(self.manifest)
        with patch.object(loop, "private_denylist", return_value=["denied-fixture"]):
            with self.assertRaises(PublicationError) as caught:
                loop.record_blocked(self.manifest, self.blocked_observation(note="denied-fixture"),
                                    releases=self.releases)
            self.assertNotIn("denied-fixture", str(caught.exception))
            self.assertFalse((self.releases / key).exists())
            self.assertEqual(list(self.releases.rglob("*")) if self.releases.exists() else [], [])
            directory = loop.record_blocked(self.manifest, self.blocked_observation(note="corrected"),
                                            releases=self.releases)
        self.assertEqual(directory.name, key)
        self.assertEqual({p.name for p in directory.iterdir()},
                         {"manifest.json", "measurements.json", "failures.json", "restoration.json"})

    def test_record_blocked_never_overwrites_or_removes_an_existing_receipt(self):
        first = loop.record_blocked(self.manifest, self.blocked_observation(), releases=self.releases)
        original = {p.name: p.read_bytes() for p in first.iterdir()}
        with self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.record_blocked(self.manifest, self.blocked_observation(gpu_idle=True, doctor_ok=False),
                                releases=self.releases)
        self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()}, original)
        shutil.rmtree(first)
        # Another writer wins the exclusive creation after validation; its directory stays untouched.
        real = loop.Scrubber

        class RacingScrubber(real):
            def scrub(inner, data):
                if not first.exists():
                    first.mkdir(parents=True)
                    (first / "measurements.json").write_bytes(b'{"writer": "other"}')
                return real.scrub(inner, data)

        with patch.object(loop, "Scrubber", RacingScrubber), \
                self.assertRaisesRegex(loop.ExperimentError, "duplicate_identity"):
            loop.record_blocked(self.manifest, self.blocked_observation(), releases=self.releases)
        self.assertEqual([p.name for p in first.iterdir()], ["measurements.json"])
        self.assertEqual((first / "measurements.json").read_bytes(), b'{"writer": "other"}')

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
        adapter.disk_floors = {"baseline": 1}
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


class FleetClaimTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.evidence = self.root / "private-trials"
        self.locks = self.root / "locks"
        self.manifest = loop.new_manifest(BASELINE, CANDIDATE, repetitions=2, rationale="Claim fixture.")
        self.manifest["restoration_target"] = loop.freeze_arm(NEXT)
        self.raw = json.dumps(self.manifest, indent=2).encode()
        now = datetime.now(timezone.utc)
        self.claim = {
            "schema_version": "carrythrough.fleet-claim.v1", "claim_id": "fixture-claim",
            "project_key": "fleet-lab", "policy_generation": 6, "policy_sha256": "a" * 64,
            "resource_id": "fixture-host:rtx5090", "host": "fixture-host",
            "variant_id": CANDIDATE, "trial_manifest_sha256": loop.sha256(self.raw),
            "repetitions": 2, "max_seconds": 3600,
            "acquired_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=2)).isoformat(), "owner": "fixture-owner",
            "restoration_ref": NEXT,
        }
        self.bindings = {"host": "fixture-host", "resource_id": "fixture-host:rtx5090",
                         "host_role": "rtx5090-win-a", "host_lock_id": "rtx5090-win-a"}
        self.adapter = FakeAdapter()

    def run_claim(self, **kwargs):
        return loop.run(self.manifest, self.adapter, claim=self.claim, bindings=self.bindings,
                        manifest_bytes=self.raw, releases=self.evidence, lock_directory=self.locks, **kwargs)

    def usage(self, directory):
        return json.loads((directory.parent / "usage.json").read_text())

    def test_valid_claim_restores_claim_incumbent_and_writes_bound_usage(self):
        directory = self.run_claim()
        usage = self.usage(directory)
        self.assertEqual(usage["schema_version"], "carrythrough.fleet-usage.v1")
        self.assertEqual(usage["claim_id"], self.claim["claim_id"])
        self.assertEqual(usage["outcome"], "passed")
        self.assertTrue(usage["restoration"]["verified"])
        self.assertEqual(usage["restoration"]["incumbent_ref"], NEXT)
        self.assertEqual(self.adapter.restored_profile, NEXT)
        self.assertEqual(usage["restoration"]["evidence_sha256"], sha256_file(directory / "restoration.json"))
        self.assertEqual(sha256_file(directory / "manifest.json"), self.claim["trial_manifest_sha256"])
        self.assertGreaterEqual(usage["gpu_seconds"], 0)
        self.assertLessEqual(usage["started_at"], usage["ended_at"])
        self.assertEqual(directory.parent.name, self.claim["claim_id"])
        for path in usage["evidence_paths"]:
            self.assertTrue((directory.parent / path).is_file())
        self.assertFalse(list(self.locks.glob("*.lock")))
        self.assertTrue((self.locks / "claims" / "fixture-claim.json").is_file())

    def test_every_claim_field_is_required_and_malformed_values_refuse_before_adapter(self):
        invalid = [None, [], {}, {**self.claim, "unknown": True}]
        for field in self.claim:
            missing = self.claim.copy()
            del missing[field]
            invalid.append(missing)
            invalid.append({**self.claim, field: None})
        for field in ("claim_id", "project_key", "resource_id", "host", "variant_id", "owner", "restoration_ref"):
            for bad in ("", " ", "../escape", "line\nbreak", 123):
                invalid.append({**self.claim, field: bad})
        for field in ("policy_sha256", "trial_manifest_sha256"):
            for bad in ("a" * 63, "G" * 64, True):
                invalid.append({**self.claim, field: bad})
        for field in ("policy_generation", "repetitions", "max_seconds"):
            for bad in (0, -1, True, "3", 1.5, float("inf")):
                invalid.append({**self.claim, field: bad})
        for field in ("acquired_at", "expires_at"):
            for bad in ("2026-10-23", "2026-10-23T01:00:00", "not-a-date"):
                invalid.append({**self.claim, field: bad})
        valid = self.claim
        for claim in invalid:
            with self.subTest(claim=claim):
                self.claim = claim
                with self.assertRaises(loop.ExperimentError):
                    self.run_claim()
                self.assertEqual(self.adapter.events, [])
                self.assertFalse(self.evidence.exists())
        self.claim = valid

    def test_expired_future_mismatched_or_over_budget_claims_refuse_before_adapter(self):
        for changes in (
            {"expires_at": "2020-01-01T00:00:00Z"},
            {"acquired_at": "2099-01-01T00:00:00Z"},
            {"host": "other-host"}, {"resource_id": "fixture-host:rtxpro6000"},
            {"variant_id": BASELINE}, {"repetitions": 1}, {"max_seconds": 3599},
            {"trial_manifest_sha256": "f" * 64}, {"restoration_ref": BASELINE},
        ):
            with self.subTest(changes=changes):
                original = self.claim
                self.claim = {**original, **changes}
                with self.assertRaises(loop.ExperimentError):
                    self.run_claim()
                self.claim = original
                self.assertEqual(self.adapter.events, [])
                self.assertFalse(self.evidence.exists())

    def test_manifest_hash_is_exact_bytes_not_canonical_json(self):
        self.claim["trial_manifest_sha256"] = loop.sha256(loop.canonical(self.manifest))
        with self.assertRaisesRegex(loop.ExperimentError, "manifest"):
            self.run_claim()
        self.assertEqual(self.adapter.events, [])

    def test_modified_manifest_object_cannot_reuse_authorized_file_hash(self):
        self.manifest["rationale"] = "Not the authorized bytes."
        with self.assertRaisesRegex(loop.ExperimentError, "manifest"):
            self.run_claim()
        self.assertEqual(self.adapter.events, [])

    def test_restoration_failure_or_exception_writes_failed_usage_and_retains_mutex(self):
        for failure in ("not-serving", "restore"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                self.evidence = Path(tmp) / "trials"
                self.locks = Path(tmp) / "locks"
                self.adapter = FakeAdapter()
                self.adapter.restore_serving = False
                self.adapter.fail_at = failure
                directory = self.run_claim()
                usage = self.usage(directory)
                self.assertEqual(usage["outcome"], "failed")
                self.assertFalse(usage["restoration"]["verified"])
                lock = self.locks / (self.adapter.lock_id + ".lock")
                original = lock.read_bytes()
                with self.assertRaisesRegex(loop.ExperimentError, "host_lock_owned"):
                    with loop.host_lock(self.adapter.lock_id, self.locks):
                        self.fail("failed restoration lock must never be stolen")
                self.assertEqual(lock.read_bytes(), original)

    def test_claim_is_consumed_once_even_with_a_different_evidence_directory(self):
        self.run_claim()
        self.evidence = self.root / "second-trials"
        self.adapter.events.clear()
        directory = self.run_claim()
        self.assertEqual(self.adapter.events, [])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")

    def test_wall_cap_aborts_trial_but_preserves_restoration_budget_and_usage(self):
        now = [0]
        original = self.adapter.install
        def install(manifest, timeout):
            original(manifest, timeout)
            now[0] = 3600
        original_restore = self.adapter.restore
        def restore(manifest):
            now[0] += 30
            return original_restore(manifest)
        self.adapter.install, self.adapter.restore = install, restore
        directory = self.run_claim(clock=lambda: now[0])
        self.assertEqual(self.adapter.events, ["precondition", "install", "restore"])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")
        self.assertEqual(self.usage(directory)["gpu_seconds"], 3630)
        self.assertTrue(self.usage(directory)["restoration"]["verified"])

    def test_unattended_without_claim_refuses_before_adapter(self):
        self.manifest["restoration_target"] = self.manifest["baseline"]
        with self.assertRaisesRegex(loop.ExperimentError, "claim_required"):
            loop.run(self.manifest, self.adapter, unattended=True, releases=self.evidence)
        self.assertEqual(self.adapter.events, [])
        with patch.object(loop, "HostAdapter", side_effect=AssertionError("adapter")):
            result = loop.main(["run", "--unattended", "--manifest", "absent.json",
                                "--bindings", "absent-bindings.json"])
        self.assertEqual(result, 1)

    def test_claim_evidence_cannot_enter_release_ledgers(self):
        self.evidence = loop.RELEASES
        with self.assertRaisesRegex(loop.ExperimentError, "private"):
            self.run_claim()
        self.assertEqual(self.adapter.events, [])

    def test_cli_consumes_claim_and_rejects_expiry_before_constructing_adapter(self):
        manifest, claim, bindings = (self.root / (name + ".json") for name in ("manifest", "claim", "bindings"))
        manifest.write_bytes(self.raw)
        atomic_write_json(claim, self.claim)
        atomic_write_json(bindings, self.bindings)
        argv = ["run", "--manifest", str(manifest), "--claim", str(claim),
                "--bindings", str(bindings), "--evidence-dir", str(self.evidence)]
        real_run = loop.run
        def run(*args, **kwargs):
            return real_run(*args, **kwargs, lock_directory=self.locks)
        with patch.object(loop, "HostAdapter", return_value=self.adapter), \
                patch.object(loop, "run", side_effect=run), redirect_stdout(io.StringIO()):
            self.assertEqual(loop.main(argv), 0)
        self.assertEqual(self.adapter.restored_profile, NEXT)
        self.claim["expires_at"] = "2020-01-01T00:00:00Z"
        atomic_write_json(claim, self.claim)
        with patch.object(loop, "HostAdapter", side_effect=AssertionError("adapter")), redirect_stdout(io.StringIO()):
            self.assertEqual(loop.main(argv), 1)

    def test_claim_expiry_limits_dispatch_but_not_cleanup(self):
        now = [0]
        self.claim["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
        original = self.adapter.install
        def install(manifest, timeout):
            self.assertLessEqual(timeout, 10)
            original(manifest, timeout)
            now[0] = 11
        self.adapter.install = install
        directory = self.run_claim(clock=lambda: now[0])
        self.assertEqual(self.adapter.events, ["precondition", "install", "restore"])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")
        self.assertTrue(self.usage(directory)["restoration"]["verified"])

    def test_serving_without_matching_incumbent_and_g10_never_unlocks(self):
        for changes in ({"profile_id": BASELINE}, {"gate": {"gate": "G10", "pass_observed": False}},
                        {"gate": {"gate": "G11", "pass_observed": True}}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                self.evidence, self.locks = Path(tmp) / "trials", Path(tmp) / "locks"
                self.adapter = FakeAdapter()
                original = self.adapter.restore
                self.adapter.restore = lambda manifest: {**original(manifest), **changes}
                directory = self.run_claim()
                self.assertEqual(self.usage(directory)["outcome"], "failed")
                self.assertFalse(self.usage(directory)["restoration"]["verified"])
                self.assertTrue(list(self.locks.glob("*.lock")))

    def test_preconditions_refuse_without_mutation_or_fabricated_restoration(self):
        self.adapter.observation["no_competing_tenant"] = False
        directory = self.run_claim()
        self.assertEqual(self.adapter.events, ["precondition"])
        self.assertEqual(self.usage(directory)["outcome"], "aborted")
        self.assertEqual(self.usage(directory)["gpu_seconds"], 0)
        self.assertFalse(self.usage(directory)["restoration"]["verified"])

    def test_adapter_restores_bound_root_and_only_stops_started_generations(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.owned_runs = {}
        events = []
        adapter.layouts = {}
        for arm in ("baseline", "candidate", "restoration_target"):
            root = self.root / arm
            root.mkdir()
            adapter.layouts[arm] = SimpleNamespace(
                root=root, run_record=root / "run.json", lock_file=root / "state.lock",
                profile=SimpleNamespace(fingerprint=self.manifest[arm]["profile_fingerprint"]))
        def command(arm, script, args, timeout, **kwargs):
            events.append((arm, script, args[0]))
            if args[0] == "start":
                atomic_write_json(adapter.layouts[arm].run_record, {
                    "requested_utc": "2026-10-23T00:00:00Z",
                    "profile_fingerprint": adapter.layouts[arm].profile.fingerprint,
                    "runtime_identity_sha256": "a" * 64,
                    "wrapper": {"pid": 101, "created": "fixture"}, "server": {"pid": 102, "created": "fixture"}})
            return {"gate": "G10", "pass_observed": True, "run_id": "g10-20261024T000000Z-abcdef",
                    "profile_fingerprint": adapter.layouts[arm].profile.fingerprint,
                    "runtime_identity_sha256": "a" * 64}
        adapter.command = command
        with patch.object(loop.lifecycle, "running", return_value={}), \
                patch.object(loop.lifecycle, "stop", return_value={"state": "stopped"}) as stop, \
                patch.object(loop.lifecycle, "status", return_value={"state": "healthy"}):
            # A never-started baseline/candidate is not our process merely because the root is bound.
            adapter.stop("baseline", 120)
            stop.assert_not_called()
            adapter.start("candidate", 120)
            result = adapter.restore(self.manifest)
            self.assertTrue(result["serving"])
            self.assertEqual(result["profile_id"], NEXT)
            target = adapter.layouts["restoration_target"]
            self.assertTrue(target.run_record.with_name("g10.json").exists(),
                            "a private receipt alone cannot bind the installed restoration's G10")
            bound_g10 = json.loads(target.run_record.with_name("g10.json").read_text())
            self.assertEqual(bound_g10["g10_run_id"], result["gate"]["run_id"])
            self.assertEqual(bound_g10["run"], adapter.owned_runs["restoration_target"])
            self.assertEqual(bound_g10["runtime_identity_sha256"], "a" * 64)
            self.assertEqual(stop.call_count, 1)
            self.assertIs(stop.call_args.args[0], adapter.layouts["candidate"])
            self.assertEqual(events, [("candidate", "omp_strata.py", "start"),
                                      ("restoration_target", "omp_strata.py", "start"),
                                      ("restoration_target", "realhost_gates.py", "g10")])
            self.assertNotIn("candidate", adapter.owned_runs)
            # Even a legitimate root restarted by somebody else is not this trial's generation.
            record = adapter.layouts["restoration_target"].run_record
            changed = json.loads(record.read_text())
            changed["server"]["pid"] = 999
            atomic_write_json(record, changed)
            with self.assertRaisesRegex(loop.ExperimentError, "owned_generation_changed"):
                adapter.stop("restoration_target", 120)
            self.assertEqual(stop.call_count, 1)

    def test_adapter_refuses_preexisting_runtime_without_claiming_or_stopping_it(self):
        adapter = object.__new__(loop.HostAdapter)
        adapter.owned_runs = {}
        adapter.layouts = {"baseline": SimpleNamespace()}
        with patch.object(loop.lifecycle, "running", return_value={"server": object()}), \
                patch.object(loop.lifecycle, "stop", side_effect=AssertionError("foreign stop")):
            with self.assertRaisesRegex(loop.ExperimentError, "root_already_running"):
                adapter.start("baseline", 120)
            self.assertEqual(adapter.stop("baseline", 120)["state"], "not_owned")
            self.assertEqual(adapter.owned_runs, {})

    def test_warm_handoff_adopts_only_the_bound_generation_under_the_root_lock(self):
        adapter = object.__new__(loop.HostAdapter)
        root = self.root / "warm"
        root.mkdir()
        profile = self.manifest["restoration_target"]
        layout = SimpleNamespace(root=root, install_record=root / "install.json", run_record=root / "run.json",
                                 lock_file=root / "lifecycle.lock",
                                 profile=SimpleNamespace(id=profile["profile_id"], fingerprint=profile["profile_fingerprint"]))
        generation = {"requested_utc": "2026-10-24T00:00:00Z", "profile_fingerprint": profile["profile_fingerprint"],
                      "wrapper": {"pid": 101, "created": "fixture"}, "server": {"pid": 102, "created": "fixture"}}
        atomic_write_json(layout.install_record, {"profile_fingerprint": profile["profile_fingerprint"],
                                                  "runtime_identity_sha256": "b" * 64})
        atomic_write_json(layout.run_record, generation)
        adapter.layouts = {"restoration_target": layout}
        adapter.owned_runs = {}
        adapter.guard = lambda arm, timeout: None
        def stopped(target, **kwargs):
            self.assertTrue(layout.lock_file.exists())
            self.assertIs(target, layout)
            self.assertIs(kwargs["locked"], True)
            return {"state": "stopped"}
        with patch.object(loop.lifecycle, "stop", side_effect=stopped) as stop:
            adapter.warm_incumbent = None
            with self.assertRaisesRegex(loop.ExperimentError, "binding_required"):
                adapter.quiesce(self.manifest, 120)
            adapter.warm_incumbent = {"runtime_identity_sha256": "b" * 64, "run": copy.deepcopy(generation)}
            adapter.warm_incumbent["run"]["server"]["pid"] = 999
            with self.assertRaisesRegex(loop.ExperimentError, "identity_mismatch"):
                adapter.quiesce(self.manifest, 120)
            self.assertEqual(adapter.owned_runs, {})
            stop.assert_not_called()
            adapter.warm_incumbent["run"] = generation
            receipt = adapter.quiesce(self.manifest, 120)
            self.assertEqual(receipt["mode"], "loop_quiesced_warm")
            self.assertEqual(receipt["runtime_identity_sha256"], "b" * 64)
            self.assertEqual(stop.call_count, 1)
            self.assertEqual(adapter.owned_runs, {})

    def test_candidate_cannot_alias_the_claim_incumbent_root(self):
        roots = {arm: str(self.root.resolve() / arm) for arm in ("baseline", "candidate")}
        self.bindings["roots"] = {**roots, "restoration_target": roots["candidate"]}
        with patch.object(loop.sys, "platform", "win32"), \
                self.assertRaisesRegex(loop.ExperimentError, "incumbent_root_not_isolated"):
            loop.HostAdapter(self.manifest, self.bindings, claim=self.claim)

    def test_evaluator_cannot_reclaim_failed_restoration_mutex_after_worker_exit(self):
        self.adapter.restore_serving = False
        self.run_claim()
        path = self.locks / (self.adapter.lock_id + ".lock")
        original = path.read_bytes()
        with patch.object(eval_taskset.os, "kill", side_effect=ProcessLookupError):
            self.assertFalse(eval_taskset.take_pid_file(path))
        self.assertEqual(path.read_bytes(), original)

    def test_evaluator_keeps_ambiguous_owners_but_reclaims_ordinary_dead_workers(self):
        path = self.root / "ordinary.lock"
        for raw in ('', '{"pid":', '[]', '{"pid":"invalid"}'):
            with self.subTest(raw=raw):
                path.write_text(raw)
                with patch.object(eval_taskset.os, "kill", side_effect=AssertionError("ambiguous PID")):
                    self.assertFalse(eval_taskset.take_pid_file(path))
                self.assertEqual(path.read_text(), raw)
        path.write_text('{"pid":12345}')
        with patch.object(eval_taskset.os, "kill", side_effect=ProcessLookupError):
            self.assertTrue(eval_taskset.take_pid_file(path))


if __name__ == "__main__":
    unittest.main()
