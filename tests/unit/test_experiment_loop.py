"""Candidate-only controller contract and accounting; no Windows host or GPU effects."""

import importlib
import itertools
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata import lifecycle
from omp_strata.common import atomic_write_json, sha256_file
from scripts import experiment_loop as loop
from tests.unit.test_process_jobs import KernelStub

BASELINE = "win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6"
CANDIDATE = "win11-rtxpro6000-nvfp4-qad-262k-slots4-strata0.2.3-omp18.12.6"


def reservation():
    return {"schema_version": 1, "host": "fixture-host", "generation": 7,
            "reserved": True, "admission_open": False, "phase": "Ready for you",
            "blockers": [], "jobs": {}, "service": {"generation": 6},
            "resources": {"ready": True, "blockers": [], "unexplained_compute": [],
                          "observed_generation": 7, "observed_utc": time.time(),
                          "gpus": [{"uuid": "fixture-gpu", "used_mib": 200}]}}


def bundle(root, *, full=False):
    root.mkdir(parents=True)
    counts = (14, 6, 60) if full else (1, 1, 1)
    requests = {"repetitions_per_arm": 2, "requests": [{"id": f"request-{n}"} for n in range(counts[0])]}
    atomic_write_json(root / "requests.json", requests)
    atomic_write_json(root / "golden-files.json", {"fixture": "frozen"})
    jobs = {"wo2": {"path": "requests.json", "sha256": sha256_file(root / "requests.json"),
                    "request_count": counts[0], "repetitions_per_arm": 2, "matched_requests_per_arm": counts[0] * 2},
            "g24": {"tasks": [{"id": f"g24-{n}"} for n in range(counts[1])],
                    "attempts_per_task": 3, "denominator_per_arm": counts[1] * 3},
            "golden": {"tasks": [{"id": f"golden-{n}"} for n in range(counts[2])],
                       "tasks_per_arm": counts[2], "repetitions_per_arm": 1,
                       "files_manifest": "golden-files.json",
                       "files_manifest_sha256": sha256_file(root / "golden-files.json")}}
    atomic_write_json(root / "jobs.json", jobs)
    rows = [{"family": family, "job": row["id"], "planned_attempts_per_arm": attempts,
             "baseline": {"attempted": attempts, "passed": attempts, "charged_wall_s": 12.25,
                          "notes": "retained, not contemporaneous"}}
            for family, seq, attempts in (("WO2", requests["requests"], 2), ("G24", jobs["g24"]["tasks"], 3),
                                          ("golden-1", jobs["golden"]["tasks"], 1)) for row in seq]
    atomic_write_json(root / "retained.json", {"inputs": {"manifest_sha256": sha256_file(root / "jobs.json")}, "rows": rows})
    (root / "runner.py").write_text("# Deterministic fixture; never executed.\n")
    bindings = {"candidate_root": str(root / "candidate"), "host_lock_id": "fixture-host",
                "controller": {"host": "fixture-host", "generation": 7, "gpu_uuids": ["fixture-gpu"]},
                "retained_baseline_evidence": str(root / "retained.json"),
                "job_manifest": str(root / "jobs.json"), "runner": str(root / "runner.py")}
    manifest = loop.new_manifest(BASELINE, CANDIDATE, rationale="Host-free candidate contract",
        retained_evidence=root / "retained.json", job_manifest=root / "jobs.json", runner=root / "runner.py")
    return manifest, bindings


class FakeAdapter:
    def __init__(self, manifest, bindings):
        self.manifest, self.bindings = manifest, bindings
        self.state, self.port_open = reservation(), False
        self.lock_id, self.events = "fixture-host", []
        self.alive = False
        self.failure = None

    def reservation(self, *, require_closed_port=False):
        result = loop.check_reservation(self.state, self.bindings["controller"])
        if require_closed_port and self.port_open:
            raise loop.ExperimentError("incumbent_port_open")
        return result

    def event(self, event):
        self.events.append(event)
        if self.failure == event:
            raise loop.ExperimentError("injected_" + event)

    def install(self, manifest, timeout):
        self.event("install")

    def start(self, arm, timeout):
        assert arm == "candidate"
        self.alive = True
        self.event("start")

    def guard(self, arm, timeout):
        assert arm == "candidate"
        self.reservation()
        self.event("guard")

    def run_job(self, job, attempt, timeout):
        self.event("run_job")
        return {"family": job["family"], "job": job["job"], "attempt": attempt,
                "status": "complete", "passed": True, "external_clients_stopped": True,
                "job_manifest_sha256": self.manifest["job_manifest_sha256"]}

    def cleanup(self, timeout):
        self.event("cleanup")
        self.alive = False


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.manifest, self.bindings = bundle(self.root / "inputs")
        self.adapter = FakeAdapter(self.manifest, self.bindings)
        self.evidence, self.locks = self.root / "evidence", self.root / "locks"

    def run_trial(self, **kwargs):
        return loop.run(self.manifest, self.adapter, bindings=self.bindings, evidence_dir=self.evidence,
                        lock_directory=self.locks, **kwargs)

    def test_full_inventory_reuses_retained_rows_without_baseline_execution(self):
        self.manifest, self.bindings = bundle(self.root / "full", full=True)
        self.adapter = FakeAdapter(self.manifest, self.bindings)
        directory = self.run_trial()
        result = loop.report(directory)
        self.assertEqual((80, 106, 106, 106), (result["planned_jobs"], result["planned_attempts"], result["attempted"], result["completed"]))
        retained = json.loads(Path(self.bindings["retained_baseline_evidence"]).read_bytes())
        self.assertEqual([r["baseline"] for r in retained["rows"]], [r["baseline"] for r in result["rows"]])
        self.assertTrue(all(r["baseline_provenance"]["kind"] == "retained" for r in result["rows"]))
        self.assertTrue(result["comparison_only"])
        self.assertTrue(result["candidate_tree_dead"])
        self.assertEqual("hold", result["recommendation"])
        self.assertFalse(self.adapter.alive)
        self.assertFalse((self.locks / "fixture-host.lock").exists())
        self.assertEqual(self.adapter.events.count("start"), 1)

    def test_controller_refusals_precede_every_effect(self):
        for change in ({"reserved": False}, {"phase": "Draining"}, {"phase": "Reserved"},
                       {"admission_open": True}, {"generation": 8}, {"jobs": {"job": {"state": "admitted"}}},
                       {"recovery_hold": "unknown"}, {"supervisor_transaction": {}}, {"blockers": ["unknown"]}):
            with self.subTest(change=change):
                self.adapter.state = reservation() | change
                with self.assertRaises(loop.ExperimentError):
                    self.run_trial()
        self.adapter.state = reservation()
        self.adapter.port_open = True
        with self.assertRaisesRegex(loop.ExperimentError, "port_open"):
            self.run_trial()
        self.assertEqual([], self.adapter.events)
        self.assertFalse(self.evidence.exists())
        self.assertFalse(self.locks.exists())

    def test_physical_receipt_is_required_not_reserved_inference(self):
        for change in ({"ready": False}, {"observed_generation": 6}, {"observed_utc": None},
                       {"gpus": []}, {"gpus": [{"uuid": "fixture-gpu", "used_mib": 1500}]},
                       {"unexplained_compute": [{"pid": 9}]}, {"blockers": ["running"]}):
            with self.subTest(change=change):
                state = reservation()
                state["resources"].update(change)
                with self.assertRaises(loop.ExperimentError):
                    loop.check_reservation(state, self.bindings["controller"])

    def test_retained_and_runner_drift_refuse_before_adapter(self):
        for key in ("retained_baseline_evidence", "job_manifest", "runner"):
            path = Path(self.bindings[key]); original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(key=key), self.assertRaisesRegex(loop.ExperimentError, "digest_mismatch"):
                self.run_trial()
            path.write_bytes(original)
        self.assertEqual(self.adapter.events, [])
        self.assertFalse(self.evidence.exists())

    def test_subset_keeps_full_denominator_and_digest(self):
        self.manifest["job_subset"] = ["WO2/request-0"]
        self.manifest["job_subset_sha256"] = loop.sha256(loop.canonical(self.manifest["job_subset"]))
        result = loop.report(self.run_trial())
        self.assertEqual((3, 1, 6, 2, 2), (result["planned_jobs"], result["selected_jobs"],
                         result["planned_attempts"], result["selected_attempts"], result["attempted"]))
        self.assertEqual([2, 0, 0], [r["candidate"]["attempted"] for r in result["rows"]])

    def test_missing_retained_row_is_unavailable_never_fabricated(self):
        path = Path(self.bindings["retained_baseline_evidence"])
        retained = json.loads(path.read_bytes()); retained["rows"].pop()
        atomic_write_json(path, retained)
        self.manifest["candidate_only_against"] = sha256_file(path)
        result = loop.report(self.run_trial())
        self.assertIsNone(result["rows"][-1]["baseline"])
        self.assertEqual("unavailable", result["rows"][-1]["baseline_provenance"]["kind"])

    def test_attempt_is_persisted_before_guard_and_not_counted_complete(self):
        def refuse_guard(*args):
            measured = json.loads(next(self.evidence.rglob("measurements.json")).read_bytes())
            self.assertEqual("attempted", measured["attempts"][0]["status"])
            raise loop.ExperimentError("guard")
        self.adapter.guard = refuse_guard
        result = loop.report(self.run_trial())
        self.assertEqual((6, 1, 0), (result["planned_attempts"], result["attempted"], result["completed"]))
        self.assertEqual("attempted", result["rows"][0]["candidate"]["attempts"][0]["status"])
        self.assertFalse(self.adapter.alive)

    def test_unproved_cleanup_retains_physical_hold(self):
        self.adapter.failure = "cleanup"
        result = loop.report(self.run_trial())
        self.assertEqual("cleanup_failed", result["status"])
        self.assertFalse(result["custody_released"])
        self.assertTrue((self.locks / "fixture-host.lock").exists())

    def test_unsettled_external_client_retains_hold_even_after_candidate_death(self):
        self.manifest["job_subset"] = ["golden-1/golden-0"]
        self.manifest["job_subset_sha256"] = loop.sha256(loop.canonical(self.manifest["job_subset"]))
        self.adapter.failure = "run_job"
        result = loop.report(self.run_trial())
        self.assertTrue(result["candidate_tree_dead"])
        self.assertFalse(result["custody_released"])
        self.assertTrue((self.locks / "fixture-host.lock").exists())

    def test_window_cutoff_preserves_return_and_cleanup_budget(self):
        observed = self.adapter.state["resources"]["observed_utc"]
        with self.assertRaisesRegex(loop.ExperimentError, "window_expired"):
            self.run_trial(wall_clock=lambda: observed + loop.WINDOW_SECONDS - loop.RETURN_SECONDS)
        self.assertEqual([], self.adapter.events)
        times = iter([0, 0, 0, 20000, 20000, 20000, 20000])
        result = loop.report(self.run_trial(clock=lambda: next(times, 20000)))
        self.assertEqual("partial", result["status"])
        self.assertEqual(0, result["attempted"])
        self.assertEqual(6, result["planned_attempts"])

    def test_old_lifecycle_manifest_and_flags_are_removed(self):
        for obsolete in ("restoration_target", "resume_candidate", "retry_of"):
            changed = dict(self.manifest, **{obsolete: True})
            with self.assertRaises(loop.ExperimentError):
                loop.validate(changed)
        for symbol in ("recustody_incumbent", "load_fleet_controller", "verify_legacy_release"):
            self.assertFalse(hasattr(loop, symbol))
        for symbol in ("restore", "quiesce", "process_census", "verify_incumbent_artifacts"):
            self.assertFalse(hasattr(loop.HostAdapter, symbol))
        self.assertFalse(hasattr(lifecycle.ProcessJob, "handoff"))

    def test_native_adapter_has_only_candidate_layout_and_checks_fixed_receipt(self):
        with patch.object(loop.sys, "platform", "win32"):
            adapter = loop.HostAdapter(self.manifest, self.bindings)
        self.assertEqual({"candidate"}, set(adapter.layouts))
        with patch.object(Path, "read_bytes", return_value=json.dumps(reservation()).encode()), \
                patch.object(lifecycle, "port_in_use", return_value=False) as port:
            adapter.reservation(require_closed_port=True)
        port.assert_called_once_with("127.0.0.1", self.manifest["baseline"]["config"]["server"]["port"])

    def test_roots_reject_aliases_and_protected_paths_before_profile_load(self):
        roots = [Path.home(), Path.home().parent, loop.ROOT, loop.ROOT / "child"]
        linked = self.root / "linked"; linked.symlink_to(self.root / "inputs", target_is_directory=True)
        roots.append(linked)
        for root in roots:
            with self.subTest(root=root), patch.object(loop.sys, "platform", "win32"), \
                    patch.object(loop, "load") as load, self.assertRaises(loop.ExperimentError):
                loop.HostAdapter(self.manifest, self.bindings | {"candidate_root": str(root)})
            load.assert_not_called()

    def test_exact_native_tooling_child_remains_allowed(self):
        root = self.root / "native"
        profile = loop.load(loop.ROOT / "profiles" / (CANDIDATE + ".json"))
        with patch.object(loop.sys, "platform", "win32"), patch.object(loop, "ROOT", root / "tooling"), \
                patch.object(loop, "load", return_value=profile):
            adapter = loop.HostAdapter(self.manifest, self.bindings | {"candidate_root": str(root)})
        self.assertEqual(root, adapter.layouts["candidate"].root)

    def test_import_has_no_native_or_controller_effects(self):
        with patch.object(lifecycle, "_job_kernel", side_effect=AssertionError("kernel")), \
                patch.object(lifecycle.subprocess, "run", side_effect=AssertionError("subprocess")), \
                patch.object(lifecycle, "port_in_use", side_effect=AssertionError("port")):
            importlib.reload(loop)

    def test_pending_start_cannot_be_overwritten_by_another_start(self):
        root = self.root / "pending"
        root.mkdir()
        layout = SimpleNamespace(run_record=root / "run.json", lock_file=root / "lock",
                                 profile=SimpleNamespace(data={"server": {}}))
        atomic_write_json(layout.run_record, {"state": "launching", "launch_id": "existing"})
        before = layout.run_record.read_bytes()
        with patch.object(lifecycle, "verify_install_fast") as verify, self.assertRaisesRegex(
                lifecycle.LifecycleError, "pending launch"):
            lifecycle.start(layout, tool_argv=[], log=lambda _: None)
        verify.assert_not_called()
        self.assertEqual(before, layout.run_record.read_bytes())

    def test_command_overrides_only_child_environment_and_proves_tree_on_error(self):
        with patch.object(loop.sys, "platform", "win32"):
            adapter = loop.HostAdapter(self.manifest, self.bindings)
        adapter.reservation = lambda **kwargs: 1
        events = []
        captured = {}
        def spawn(argv, *, stdout, stderr, env):
            captured.update(env)
            stdout.write(b'{"status":"failed"}')
            return SimpleNamespace(poll=lambda: 1, returncode=1, wait=lambda timeout: None)
        job = SimpleNamespace(spawn=spawn, stop=lambda timeout: events.append("proved_dead"))
        original = dict(os.environ)
        with patch.object(lifecycle, "ProcessJob", return_value=job), self.assertRaisesRegex(
                loop.ExperimentError, "child_failed"):
            adapter.command("candidate", "omp_strata.py", ["install"], 10, env={"CHILD_ONLY": "yes"})
        self.assertEqual(original, dict(os.environ))
        self.assertEqual("yes", captured["CHILD_ONLY"])
        self.assertEqual(["proved_dead"], events)
        self.assertEqual({}, adapter.owned_commands)


class MemoryLock:
    """Single-thread model boundary; the production root-lock policy remains exercised elsewhere."""
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class ModelHost(loop.HostAdapter):
    """Only OS observations/dispatch are in memory. Start/stop/cleanup/run are production."""
    def __init__(self, manifest, bindings, kernel, cut, parent_exits, publication):
        self.manifest, self.bindings = manifest, bindings
        self.lock_id = "fixture-host"
        self.state, self.port_open = reservation(), False
        self.kernel, self.cut, self.parent_exits, self.publication = kernel, cut, parent_exits, publication
        self.events = []
        root = Path(bindings["candidate_root"])
        root.mkdir(parents=True)
        self.layouts = {"candidate": SimpleNamespace(root=root, run_record=root / "run.json", lock_file=root / "lock",
            profile=SimpleNamespace(fingerprint=manifest["candidate"]["profile_fingerprint"], multi_gpu=False,
                                    data=manifest["candidate"]["config"]))}
        self.owned_runs, self.launch_requests, self.launch_jobs, self.owned_commands = {}, {}, {}, {}
        self.disk_floors = {"candidate": 0}

    reservation = FakeAdapter.reservation

    def command(self, arm, script, args, timeout, **kwargs):
        self.events.append(args[0])
        if args[0] == "start":
            token = kwargs["env"][lifecycle.EXPERIMENT_LAUNCH_ENV]
            job = self.launch_jobs[arm]
            record = {"experiment_launch_id": token, "launch_id": token,
                      "requested_utc": "fixture", "profile_fingerprint": self.layouts[arm].profile.fingerprint,
                      "state": "launching", "tree_token": token}
            for pid in (100, 101, 102):
                self.kernel.live[pid] = object()
                self.kernel.members[pid] = self.kernel.handles[job.handle]
            if self.publication == "published":
                record.update(wrapper={"pid": 100}, server={"pid": 101}, state="ready")
            if self.parent_exits:
                self.kernel.live.pop(100)
                self.kernel.live.pop(101)
            atomic_write_json(self.layouts[arm].run_record, record)
        if self.cut == args[0]:
            raise loop.ExperimentError("injected_failure")
        return {}

    def guard(self, arm, timeout):
        self.events.append("guard")
        if self.cut == "reservation_lost":
            self.state["reserved"] = False
        self.reservation()
        if self.cut == "guard":
            raise loop.ExperimentError("injected_failure")
        return super().guard(arm, timeout)

    def run_job(self, job, attempt, timeout):
        self.events.append("run_job")
        if self.cut == "run_job":
            raise loop.ExperimentError("injected_failure")
        return FakeAdapter.run_job(self, job, attempt, timeout)

    def event(self, event):
        pass

    def cleanup(self, timeout):
        if self.cut == "cleanup":
            self.kernel.fail = "terminate"
        if self.cut == "proof":
            self.kernel.fail = "enumerate"
        return super().cleanup(timeout)


def model_schedules():
    results = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest, bindings = bundle(root / "inputs")
        schedules = itertools.product(("ready", "unreserved", "draining", "port_open"),
            (None, "install", "start", "guard", "run_job", "cleanup", "proof", "reservation_lost"),
            (False, True), ("published", "pending"))
        for index, (control, cut, exited, publication) in enumerate(schedules):
            kernel = KernelStub()
            local = bindings | {"candidate_root": str(root / str(index) / "candidate")}
            host = ModelHost(manifest, local, kernel, cut, exited, publication)
            if control == "unreserved": host.state["reserved"] = False
            if control == "draining": host.state["phase"] = "Draining"
            if control == "port_open": host.port_open = True
            failure = None
            try:
                with patch.object(lifecycle, "_job_kernel", return_value=kernel), \
                        patch.object(lifecycle, "FileLock", MemoryLock), \
                        patch.object(lifecycle, "WINDOWS", True), \
                        patch.object(lifecycle.subprocess, "run", kernel.cim), \
                        patch.object(lifecycle.procs, "matches", return_value=None), \
                        patch.object(lifecycle, "status", side_effect=lambda _: {
                            "state": "healthy" if 101 in kernel.live else "exited"}), \
                        patch.object(lifecycle, "port_in_use", return_value=False):
                    result_dir = loop.run(manifest, host, bindings=local, evidence_dir=root / str(index) / "evidence",
                                          lock_directory=root / str(index) / "locks")
                result = loop.report(result_dir)
                if result["custody_released"] and kernel.live:
                    failure = "released_with_candidate_survivor"
                if control != "ready" and host.events:
                    failure = "effect_without_reservation"
                if result["candidate_tree_dead"] and kernel.live:
                    failure = "false_tree_death"
                if cut is None and control == "ready" and not exited and publication == "published" and result["status"] != "complete":
                    failure = "reserved_stopped_did_not_run"
            except loop.ExperimentError:
                if control == "ready" or host.events:
                    failure = "unexpected_refusal_or_effect"
            results.append({"schedule": [control, cut, exited, publication], "counterexample": failure})
    return results


class ControllerModelTests(unittest.TestCase):
    def test_candidate_window_interleavings(self):
        rows = model_schedules()
        failures = [row for row in rows if row["counterexample"]]
        self.assertEqual(128, len(rows))
        self.assertEqual([], failures)


if __name__ == "__main__":
    rows = model_schedules()
    failures = [row for row in rows if row["counterexample"]]
    print(json.dumps({"schedules": len(rows), "counterexamples_after": len(failures), "failures": failures}))
    raise SystemExit(bool(failures))
