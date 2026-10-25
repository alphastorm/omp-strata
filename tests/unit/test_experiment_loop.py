"""Candidate-only controller contract and accounting; no Windows host or GPU effects."""

import importlib
import itertools
import json
import os
import contextlib
import subprocess
import sys
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata import cli, install, lifecycle
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
    atomic_write_json(root / "baseline-manifest.json", {"baseline": loop.freeze_arm(BASELINE)})
    jobs = {"wo2": {"path": "requests.json", "sha256": sha256_file(root / "requests.json"),
                    "request_count": counts[0], "repetitions_per_arm": 2, "matched_requests_per_arm": counts[0] * 2},
            "g24": {"tasks": [{"id": f"g24-{n}"} for n in range(counts[1])],
                    "attempts_per_task": 3, "denominator_per_arm": counts[1] * 3},
            "golden": {"tasks": [{"id": f"golden-{n}"} for n in range(counts[2])],
                       "tasks_per_arm": counts[2], "repetitions_per_arm": 1,
                       "files_manifest": "golden-files.json",
                       "files_manifest_sha256": sha256_file(root / "golden-files.json")}}
    jobs["loop_manifest_sha256"] = sha256_file(root / "baseline-manifest.json")
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
                "baseline_manifest": str(root / "baseline-manifest.json"),
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
        cutoff = loop.WINDOW_SECONDS - loop.RETURN_SECONDS - loop.CLEANUP_SECONDS + 1
        times = iter([0, 0, 0, cutoff])
        result = loop.report(self.run_trial(clock=lambda: next(times, cutoff)))
        self.assertEqual("partial", result["status"])
        self.assertEqual(0, result["attempted"])
        self.assertEqual(6, result["planned_attempts"])

    def test_elapsed_cleanup_budget_never_releases_hold(self):
        times = iter([0, 0, 0, 20000])
        result = loop.report(self.run_trial(clock=lambda: next(times, 20000)))
        self.assertEqual("cleanup_failed", result["status"])
        self.assertFalse(result["custody_released"])
        self.assertTrue((self.locks / "fixture-host.lock").exists())

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
        def spawn(argv, *, stdout, stderr, env, timeout):
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

    def test_nested_candidate_alias_refuses_before_effects(self):
        root = self.root / "candidate"
        root.mkdir()
        (root / "runtime").symlink_to(self.root / "inputs", target_is_directory=True)
        with patch.object(loop.sys, "platform", "win32"), self.assertRaisesRegex(
                ValueError, "reparse"):
            loop.HostAdapter(self.manifest, self.bindings | {"candidate_root": str(root)})

    def test_retained_baseline_must_match_frozen_baseline_manifest(self):
        path = Path(self.bindings["retained_baseline_evidence"])
        retained = json.loads(path.read_bytes())
        retained["baseline_profile_fingerprint"] = "f" * 64
        atomic_write_json(path, retained)
        self.manifest["candidate_only_against"] = sha256_file(path)
        # The original job manifest binds the baseline experiment manifest.
        original = self.root / "baseline-manifest.json"
        atomic_write_json(original, {"baseline": loop.freeze_arm(CANDIDATE)})
        jobs_path = Path(self.bindings["job_manifest"])
        jobs = json.loads(jobs_path.read_bytes())
        jobs["loop_manifest_sha256"] = sha256_file(original)
        atomic_write_json(jobs_path, jobs)
        self.manifest["job_manifest_sha256"] = sha256_file(jobs_path)
        retained["inputs"]["manifest_sha256"] = self.manifest["job_manifest_sha256"]
        atomic_write_json(path, retained)
        self.manifest["candidate_only_against"] = sha256_file(path)
        self.bindings["baseline_manifest"] = str(original)
        with self.assertRaisesRegex(loop.ExperimentError, "baseline"):
            loop.load_inputs(self.manifest, self.bindings)

    def test_all_execution_dependencies_are_frozen(self):
        required = {"omp_strata/common.py", "omp_strata/comparison.py", "omp_strata/receipts.py",
                    "omp_strata/ompcfg.py", "omp_strata/engine_component.py", "eval/support.py"}
        self.assertTrue(required <= set(loop.HARNESS_FILES), sorted(required - set(loop.HARNESS_FILES)))

    def test_install_does_not_extend_expired_budget_for_keygen(self):
        with patch.object(loop.sys, "platform", "win32"):
            adapter = loop.HostAdapter(self.manifest, self.bindings)
        calls = []
        now = [0]
        def command(arm, script, args, timeout):
            calls.append(args[0])
            now[0] = 11
        adapter.command = command
        with patch.object(loop.nvfp4, "staging_preflight"), \
                patch.object(loop.time, "monotonic", side_effect=lambda: now[0]), self.assertRaises(loop.ExperimentError):
            adapter.install(self.manifest, 10)
        self.assertEqual(["install"], calls)

    def test_cleanup_subtracts_lock_time_from_native_budget(self):
        with patch.object(loop.sys, "platform", "win32"):
            adapter = loop.HostAdapter(self.manifest, self.bindings)
        root = adapter.layouts["candidate"].root
        adapter.check_root(create=True)
        now, waits = [0.0], []
        class SlowLock(MemoryLock):
            def __enter__(self):
                now[0] += 9
                return self
        job = SimpleNamespace(token="a" * 32, handle=1, verified_empty=False)
        def stopped(timeout=30):
            waits.append(timeout)
            now[0] += timeout
            job.handle = None
            job.verified_empty = True
        job.stop = stopped
        adapter.launch_jobs["candidate"] = job
        adapter.launch_requests["candidate"] = {"experiment_launch_id": job.token}
        with patch.object(lifecycle, "FileLock", SlowLock), patch.object(loop.time, "monotonic", side_effect=lambda: now[0]):
            adapter.cleanup(10)
        self.assertLessEqual(now[0], 10)
        self.assertTrue(waits and max(waits) <= 1)

    def test_runner_replacement_after_verification_cannot_change_executed_bytes(self):
        with patch.object(loop.sys, "platform", "win32"):
            adapter = loop.HostAdapter(self.manifest, self.bindings)
        path = Path(self.bindings["runner"])
        original = path.read_bytes()
        seen = {}
        def command(arm, script, args, timeout, **kwargs):
            path.write_bytes(b"# changed concurrently\n")
            source = kwargs.get("source")
            seen["bytes"] = source if source is not None else Path(script).read_bytes()
            return {}
        adapter.command = command
        adapter.run_job({"family": "WO2", "job": "request-0"}, 1, 10)
        self.assertEqual(original, seen["bytes"])

    def test_runner_snapshot_reaches_child_without_path_reopen(self):
        with patch.object(loop.sys, "platform", "win32"):
            adapter = loop.HostAdapter(self.manifest, self.bindings)
        adapter.reservation = lambda **kwargs: 1
        captured = {}
        def spawn(argv, *, stdout, stderr, env, stdin, timeout):
            captured.update(source=stdin.read(), argv=argv)
            stdout.write(b'{"status":"complete"}')
            return SimpleNamespace(poll=lambda: 0, returncode=0, wait=lambda timeout: None)
        job = SimpleNamespace(spawn=spawn, stop=lambda timeout: None)
        with patch.object(lifecycle, "ProcessJob", return_value=job):
            adapter.command("candidate", self.bindings["runner"], [], 10, source=b"frozen-source")
        self.assertEqual(b"frozen-source", captured["source"])
        self.assertEqual(["-I", "-S", "-B", "-c"], captured["argv"][1:5])
        self.assertIn("sys.stdin.buffer.read()", captured["argv"][5])

    def native_adapter(self):
        with patch.object(loop.sys, "platform", "win32"):
            adapter = loop.HostAdapter(self.manifest, self.bindings)
        adapter.reservation = lambda **kwargs: 1
        adapter.check_root(create=True)
        return adapter

    def ready_adapter(self):
        adapter = self.native_adapter()
        layout = adapter.layouts["candidate"]
        record = {"requested_utc": "fixture", "profile_fingerprint": layout.profile.fingerprint,
                  "wrapper": {"pid": 100}, "server": {"pid": 101}, "state": "ready",
                  "runtime_identity_sha256": "fixture"}
        atomic_write_json(layout.run_record, record)
        atomic_write_json(layout.install_record, {
            "runtime_identity_sha256": "fixture", "profile_fingerprint": layout.profile.fingerprint})
        adapter.owned_runs["candidate"] = {k: record[k] for k in ("requested_utc", "profile_fingerprint", "wrapper", "server")}
        return adapter

    def test_guard_propagates_budget_and_refuses_late_native_or_http_result(self):
        for delayed in ("native", "http", "neither"):
            with self.subTest(delayed=delayed):
                adapter = self.ready_adapter()
                now, budgets = [0.0], []
                def enumerate_tree(timeout):
                    budgets.append(timeout)
                    now[0] += 2 if delayed == "native" else 0.2
                    return {101: {}}
                def checks(layout, key, *, deadline):
                    budgets.append(deadline - now[0])
                    now[0] += 2 if delayed == "http" else 0.2
                    return {"ready": True}
                adapter.launch_jobs["candidate"] = SimpleNamespace(pids=lambda: {101}, enumerate_tree=enumerate_tree)
                with patch.object(loop.time, "monotonic", side_effect=lambda: now[0]), \
                        patch.object(lifecycle, "read_key", return_value="fixture"), \
                        patch.object(lifecycle, "runtime_checks", side_effect=checks):
                    if delayed == "neither":
                        adapter.guard("candidate", 1)
                    else:
                        with self.assertRaisesRegex(loop.ExperimentError, "max_wall_time"):
                            adapter.guard("candidate", 1)
                self.assertTrue(all(0 < b <= 1 for b in budgets))

    def test_runtime_http_calls_share_deadline_and_late_success_fails(self):
        adapter = self.ready_adapter()
        now, budgets = [0.0], []
        def http(url, *, timeout, **kwargs):
            budgets.append(timeout)
            now[0] = 2
            return 200, {}
        with patch.object(lifecycle.time, "monotonic", side_effect=lambda: now[0]), \
                patch.object(lifecycle, "http_json", side_effect=http), \
                self.assertRaisesRegex(lifecycle.LifecycleError, "deadline"):
            lifecycle.runtime_checks(adapter.layouts["candidate"], "fixture", deadline=1)
        self.assertEqual([1], budgets)

    def test_cleanup_refuses_replaced_root_before_opening_foreign_lock(self):
        adapter = self.native_adapter()
        root = adapter.layouts["candidate"].root
        root.rename(root.with_name("displaced"))
        root.mkdir()
        events = []
        adapter.launch_jobs["candidate"] = SimpleNamespace(stop=lambda timeout: events.append("native"), verified_empty=True)
        with patch.object(lifecycle, "FileLock") as lock, self.assertRaisesRegex(loop.ExperimentError, "cleanup_unproved"):
            adapter.cleanup(10)
        lock.assert_not_called()
        self.assertEqual(["native"], events)
        self.assertEqual([], list(root.iterdir()))

    def test_cutoff_defers_native_stop_until_root_fenced_cleanup_with_proof_budget(self):
        for launching in (False, True):
            with self.subTest(launching=launching):
                adapter = self.native_adapter()
                layout = adapter.layouts["candidate"]
                now, events = [0.0], []
                child = SimpleNamespace(poll=lambda: None, wait=lambda timeout: events.append(("wait", timeout)))
                job = SimpleNamespace(token="a" * 32, verified_empty=False)
                def spawn(*args, **kwargs):
                    now[0] = 2
                    if launching:
                        atomic_write_json(layout.run_record, {
                            "experiment_launch_id": job.token, "profile_fingerprint": layout.profile.fingerprint,
                            "state": "launching", "tree_token": job.token})
                    return child
                def stopped(timeout):
                    if launching:
                        self.assertEqual("stop_incomplete", json.loads(layout.run_record.read_bytes())["state"])
                    events.append(("proof_then_terminate", timeout))
                    job.verified_empty = True
                job.spawn, job.stop = spawn, stopped
                class FencedLock(MemoryLock):
                    def __enter__(self):
                        events.append(("root_lock", None))
                        return self
                original_fence = lifecycle.directory_fence
                @contextlib.contextmanager
                def fence(*args, **kwargs):
                    with original_fence(*args, **kwargs) as fd:
                        events.append(("root_fence", None))
                        yield fd
                if launching:
                    adapter.launch_jobs["candidate"] = job
                    adapter.launch_requests["candidate"] = {
                        "experiment_launch_id": job.token, "profile_fingerprint": layout.profile.fingerprint}
                with patch.object(lifecycle, "ProcessJob", return_value=job), \
                        patch.object(loop.time, "monotonic", side_effect=lambda: now[0]), \
                        patch.object(lifecycle, "FileLock", FencedLock), \
                        patch.object(lifecycle, "directory_fence", side_effect=fence):
                    with self.assertRaisesRegex(loop.ExperimentError, "max_wall_time"):
                        adapter.command("candidate", "omp_strata.py", ["start" if launching else "install"], 1)
                    self.assertFalse(any(event[0] == "proof_then_terminate" for event in events))
                    events.clear()
                    adapter.cleanup(10)
                self.assertEqual("root_fence", events[0][0])
                self.assertIn(("proof_then_terminate", 10), events)
                if launching:
                    self.assertLess(events.index(("root_lock", None)), events.index(("proof_then_terminate", 10)))
                else:
                    self.assertLess(events.index(("proof_then_terminate", 10)), events.index(("root_lock", None)))
                self.assertEqual({}, adapter.owned_commands)

    def test_command_recomputes_wait_after_guard(self):
        adapter = self.native_adapter()
        now = [0]
        child = SimpleNamespace(poll=lambda: None, wait=lambda **kwargs: self.fail("stale wait budget"))
        job = SimpleNamespace(spawn=lambda *args, **kwargs: child)
        adapter.guard = lambda *args: now.__setitem__(0, 2)
        with patch.object(lifecycle, "ProcessJob", return_value=job), \
                patch.object(loop.time, "monotonic", side_effect=lambda: now[0]), \
                self.assertRaisesRegex(loop.ExperimentError, "max_wall_time"):
            adapter.command("candidate", "omp_strata.py", ["install"], 1, monitor=True)
        self.assertIn(adapter.layouts["candidate"].root, adapter.owned_commands)

    def test_snapshot_executes_cli_and_imports_without_checkout_or_pythonpath(self):
        checkout = self.root / "checkout"
        files = {"scripts/omp_strata.py": b"import module; print(module.VALUE)\n", "module.py": b"VALUE='frozen'\n"}
        for name, raw in files.items():
            path = checkout / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        manifest = {"harness_files": {name: loop.sha256(raw) for name, raw in files.items()},
                    "runner_sha256": self.manifest["runner_sha256"]}
        with patch.object(loop, "ROOT", checkout), \
                loop.harness_snapshot(manifest, self.bindings, self.root / "sealed") as receipt:
            for name in files:
                (checkout / name).write_bytes(b"raise AssertionError('mutable checkout executed')\n")
            snapshot = Path(receipt["root"])
            code = "import sys,runpy;sys.path.insert(0,sys.argv[1]);runpy.run_path(sys.argv[2],run_name='__main__')"
            child = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(snapshot),
                                    str(snapshot / "scripts/omp_strata.py")],
                                   env={**os.environ, "PYTHONPATH": str(checkout)}, cwd=checkout,
                                   text=True, capture_output=True, check=True)
            self.assertEqual("frozen\n", child.stdout)
            self.assertEqual(manifest["harness_files"]["module.py"], receipt["files"]["module.py"])

    def test_real_snapshot_imports_and_validates_without_checkout_search_path(self):
        with loop.harness_snapshot(self.manifest, self.bindings, self.root / "real-snapshot") as receipt:
            code = ("import sys,json;sys.path.insert(0,sys.argv[1]);"
                    "from scripts.experiment_loop import validate;print(validate(json.load(sys.stdin)))")
            child = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, receipt["root"]],
                                   input=json.dumps(self.manifest), text=True, capture_output=True, check=True)
            self.assertEqual(loop.experiment_key(self.manifest), child.stdout.strip())
            direct = subprocess.run([sys.executable, "-I", "-S", "-B",
                                     str(Path(receipt["root"]) / "scripts/omp_strata.py"), "--help"],
                                    text=True, capture_output=True, check=True)
            self.assertIn("install", direct.stdout)

    def test_root_swap_at_lock_entry_never_opens_foreign_lock(self):
        adapter = self.native_adapter()
        layout = adapter.layouts["candidate"]
        layout.state.mkdir(parents=True, exist_ok=True)
        foreign = self.root / "foreign"
        foreign.mkdir()
        original = lifecycle.FileLock
        class SwappingLock(original):
            def __enter__(self):
                layout.root.rename(layout.root.with_name("old-candidate"))
                layout.root.symlink_to(foreign, target_is_directory=True)
                return super().__enter__()
        with patch.object(lifecycle, "FileLock", SwappingLock), self.assertRaises(loop.ExperimentError):
            adapter.cleanup(10)
        self.assertFalse((foreign / layout.lock_file.relative_to(layout.root)).exists())

    def test_failed_job_creation_before_spawn_does_not_strand_custody(self):
        adapter = self.native_adapter()
        with patch.object(lifecycle, "ProcessJob", side_effect=lifecycle.LifecycleError("job creation refused")):
            with self.assertRaises(lifecycle.LifecycleError):
                adapter.command("candidate", "omp_strata.py", ["install"], 10)
        self.assertEqual({}, adapter.owned_commands)
        adapter.cleanup(10)

    def test_installer_lock_holder_is_terminated_before_lock_wait_spends_proof_budget(self):
        adapter = self.native_adapter()
        layout = adapter.layouts["candidate"]
        owner = lifecycle.FileLock(layout.lock_file)
        owner.__enter__()
        self.addCleanup(owner.__exit__)
        now, budgets = [0.0], []
        def stop(timeout):
            budgets.append(timeout)
            owner.__exit__()
            if timeout <= 0:
                raise lifecycle.LifecycleError("proof budget exhausted")
        job = SimpleNamespace(stop=stop, verified_empty=True)
        adapter.owned_commands[layout.root] = {"job": job, "child": None}
        with patch.object(lifecycle.time, "monotonic", side_effect=lambda: now[0]), \
                patch.object(lifecycle.time, "sleep", side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)):
            adapter.cleanup(3)
        self.assertTrue(budgets and budgets[0] > 0)
        self.assertEqual({}, adapter.owned_commands)

    def test_idle_fence_survives_keygen_and_both_start_gaps(self):
        for cut in ("keygen", "before_start", "start"):
            with self.subTest(cut=cut):
                local = self.bindings | {"candidate_root": str(self.root / ("candidate-" + cut))}
                with patch.object(loop.sys, "platform", "win32"):
                    adapter = loop.HostAdapter(self.manifest, local)
                adapter.reservation = lambda **kwargs: 1
                layout = adapter.layouts["candidate"]
                reached = []
                class Effect(Exception):
                    pass
                def effect(*args, **kwargs):
                    reached.append("effect")
                    raise Effect
                def competing():
                    atomic_write_json(layout.run_record, {
                        "state": "stopped", "tree_token": "b" * 32, "tree_verified_empty": "b" * 32,
                        "launch_id": "competing", "profile_fingerprint": layout.profile.fingerprint})
                def command(arm, script, args, timeout, **kwargs):
                    if args[0] == "install":
                        return {}
                    if args[0] == "keygen":
                        if cut != "keygen":
                            return {}
                        competing()
                        parsed = cli.build_parser().parse_args([*args, "--profile", str(layout.profile.path),
                                                               "--root", str(layout.root)])
                        return cli.cmd_keygen(parsed)
                    competing()
                    parsed = cli.build_parser().parse_args([*args, "--profile", str(layout.profile.path),
                                                           "--root", str(layout.root)])
                    return cli.cmd_start(parsed)
                adapter.command = command
                with patch.object(loop.nvfp4, "staging_preflight"), \
                        patch.object(lifecycle, "keygen", side_effect=effect), \
                        patch.object(lifecycle, "verify_install_fast", side_effect=effect), \
                        patch.object(lifecycle, "running", return_value={}), \
                        patch.object(lifecycle.ProcessJob, "scan", return_value={}), \
                        patch.object(lifecycle, "_job_kernel", return_value=KernelStub()):
                    try:
                        adapter.install(self.manifest, 10)
                        if cut == "before_start":
                            competing()
                        adapter.start("candidate", 10)
                    except (Effect, loop.ExperimentError, lifecycle.LifecycleError):
                        pass
                self.assertEqual([], reached)

    def test_attempt_rechecks_candidate_generation_after_short_runner_exit(self):
        def run_job(job, attempt, timeout):
            result = FakeAdapter.run_job(self.adapter, job, attempt, timeout)
            self.adapter.failure = "guard"
            return result
        self.adapter.run_job = run_job
        result = loop.report(self.run_trial())
        self.assertEqual(0, result["completed"])

    def test_guard_rechecks_generation_after_http(self):
        adapter = self.ready_adapter()
        layout = adapter.layouts["candidate"]
        adapter.launch_jobs["candidate"] = SimpleNamespace(pids=lambda: {101}, enumerate_tree=lambda **kwargs: {101: {}})
        def changed(*args, **kwargs):
            record = json.loads(layout.run_record.read_bytes())
            record["requested_utc"] = "replacement"
            atomic_write_json(layout.run_record, record)
            return {"ready": True}
        with patch.object(lifecycle, "read_key", return_value="fixture"), \
                patch.object(lifecycle, "runtime_checks", side_effect=changed), \
                self.assertRaisesRegex(loop.ExperimentError, "identity_lost"):
            adapter.guard("candidate", 10)

    def test_cleanup_enforces_actual_slice_and_wall_clock_return_deadline(self):
        for cut in ("slice", "wall"):
            with self.subTest(cut=cut):
                now = [0.0]
                wall = [self.adapter.state["resources"]["observed_utc"]]
                def cleanup(timeout):
                    if cut == "slice":
                        now[0] += loop.CLEANUP_SECONDS + 1
                    else:
                        wall[0] += loop.WINDOW_SECONDS - loop.RETURN_SECONDS + 1
                self.adapter.failure = "install"
                self.adapter.cleanup = cleanup
                directory = loop.run(self.manifest, self.adapter, bindings=self.bindings,
                                     evidence_dir=self.evidence / cut, lock_directory=self.locks / cut,
                                     clock=lambda: now[0], wall_clock=lambda: wall[0])
                self.assertFalse(loop.report(directory)["custody_released"])

    def test_bootstrap_refuses_drift_before_snapshot_and_preserves_reason(self):
        Path(self.bindings["retained_baseline_evidence"]).write_text("{}")
        control = self.root / "controller.json"
        atomic_write_json(control, reservation())
        with patch.object(loop, "CONTROL_STATE", control), patch.object(loop.sys, "platform", "win32"), \
                patch.object(lifecycle, "port_in_use", return_value=False), \
                patch.object(loop.subprocess, "run", return_value=SimpleNamespace(returncode=1)), \
                self.assertRaisesRegex(loop.ExperimentError, "digest_mismatch"):
            loop.run_frozen(self.manifest, self.bindings, self.evidence)
        self.assertFalse(self.evidence.exists())

    def test_bootstrap_native_job_contains_worker_lifetime(self):
        control = self.root / "controller.json"
        atomic_write_json(control, reservation())
        spawned = []
        def spawn(argv, **kwargs):
            spawned.append(argv)
            kwargs["stdout"].write(b'{"status":"complete"}')
            return SimpleNamespace(wait=lambda **kwargs: 0, returncode=0)
        job = SimpleNamespace(spawn=spawn, stop=lambda timeout: None, close=lambda: None)
        with patch.object(loop, "CONTROL_STATE", control), patch.object(loop.sys, "platform", "win32"), \
                patch.object(lifecycle, "port_in_use", return_value=False), \
                patch.object(loop, "HOST_LOCKS", self.locks), \
                patch.object(lifecycle, "ProcessJob", return_value=job), \
                patch.object(loop.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout='{"status":"complete"}')):
            loop.run_frozen(self.manifest, self.bindings, self.evidence)
        self.assertEqual(1, len(spawned), "ordinary subprocess does not contain worker lifetime")

    def test_isolation_scan_tolerates_disappearing_workload_temporaries(self):
        entry = SimpleNamespace(stat=lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError("removed temporary")))
        with patch.object(loop.nvfp4.os, "scandir", return_value=contextlib.nullcontext(iter([entry]))):
            loop.nvfp4.assert_isolated_tree(self.root)

    def test_bootstrap_refuses_cleanup_reserve_and_future_receipts_before_snapshot(self):
        control = self.root / "controller.json"
        state = reservation()
        observed = state["resources"]["observed_utc"]
        atomic_write_json(control, state)
        for now in (observed - 1, observed + loop.WINDOW_SECONDS - loop.RETURN_SECONDS - 1):
            with self.subTest(now=now), patch.object(loop, "CONTROL_STATE", control), \
                    patch.object(loop.sys, "platform", "win32"), patch.object(loop, "HOST_LOCKS", self.locks), \
                    patch.object(lifecycle, "port_in_use", return_value=False), \
                    patch.object(loop.time, "time", return_value=now), \
                    patch.object(loop, "harness_snapshot") as snapshot, \
                    self.assertRaisesRegex(loop.ExperimentError, "window_expired"):
                loop.run_frozen(self.manifest, self.bindings, self.evidence)
            snapshot.assert_not_called()
        self.assertFalse(self.evidence.exists())

    def test_bootstrap_interruption_closes_native_job_before_returning(self):
        kernel = KernelStub()
        def spawn(job, argv, **kwargs):
            for pid in (100, 101, 102):
                kernel.live[pid] = object()
                kernel.members[pid] = kernel.handles[job.handle]
            raise KeyboardInterrupt
        with patch.object(lifecycle, "_job_kernel", return_value=kernel), \
                patch.object(lifecycle.ProcessJob, "spawn", spawn), \
                patch.object(lifecycle.subprocess, "run", side_effect=kernel.cim), \
                self.assertRaises(KeyboardInterrupt):
            loop.snapshot_worker_command({}, self.root, 10)
        self.assertEqual({}, kernel.live)
        self.assertEqual({}, kernel.handles)
        self.assertIn(("limits", 0x2000), kernel.events)

    def test_worker_preserves_closed_error_reason(self):
        payload = {"manifest": self.manifest,
                   "bindings": self.bindings | {"harness_snapshot": {"root": str(loop.ROOT)}},
                   "evidence_dir": str(self.evidence)}
        with patch.object(loop, "HostAdapter", side_effect=loop.ExperimentError("candidate_root_replaced")), \
                patch("builtins.print") as printed:
            loop.frozen_worker(payload)
        self.assertEqual({"error": "candidate_root_replaced"}, json.loads(printed.call_args.args[0]))

    def test_native_directory_fence_pins_ancestors_without_delete_sharing(self):
        opened, closed = [], []
        class Call:
            def __init__(self, fn):
                self.fn = fn
            def __call__(self, *args):
                return self.fn(*args)
        def create(path, access, sharing, security, disposition, flags, template):
            opened.append((path, sharing, flags))
            return len(opened)
        kernel = SimpleNamespace(CreateFileW=Call(create), CloseHandle=Call(lambda handle: closed.append(handle) or 1))
        expected = {p: loop.HostAdapter.path_identity(p) for p in (self.root, *self.root.parents)}
        with patch.object(lifecycle.os, "name", "nt"), \
                patch.object(lifecycle.ctypes, "WinDLL", return_value=kernel, create=True):
            with lifecycle.directory_fence(self.root, expected) as fd:
                self.assertIsNone(fd)
                self.assertEqual([], closed)
        self.assertEqual([str(p) for p in reversed((self.root, *self.root.parents))], [r[0] for r in opened])
        self.assertTrue(all(sharing == 3 and flags == 0x02200000 for _, sharing, flags in opened))
        self.assertEqual(list(range(len(opened), 0, -1)), closed)

    def test_directory_fence_refuses_unexpected_creation_of_absent_root(self):
        root = self.root / "appeared"
        expected = {p: loop.HostAdapter.path_identity(p) for p in (root, *root.parents)}
        root.mkdir()
        with self.assertRaisesRegex(lifecycle.LifecycleError, "identity changed"):
            with lifecycle.directory_fence(root, expected):
                self.fail("adopted a root created by another operation")

    def test_experimental_start_skips_gpu_census_but_ordinary_start_keeps_it(self):
        adapter = self.native_adapter()
        layout = adapter.layouts["candidate"]
        for experimental in (False, True):
            layout.run_record.unlink(missing_ok=True)
            env = ({lifecycle.EXPERIMENT_LAUNCH_ENV: "a" * 32, lifecycle.TREE_TOKEN_ENV: "a" * 32}
                   if experimental else {})
            with self.subTest(experimental=experimental), patch.dict(os.environ, env, clear=True), \
                    patch.object(lifecycle, "WINDOWS", experimental), \
                    patch.object(lifecycle, "FileLock", MemoryLock), \
                    patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "fixture"}), \
                    patch.object(lifecycle, "read_key", return_value="fixture"), \
                    patch.object(lifecycle, "running", return_value={}), \
                    patch.object(lifecycle, "port_in_use", return_value=False), \
                    patch.object(lifecycle, "gpu_facts", return_value={}) as census, \
                    patch.object(lifecycle, "gpu_busy", return_value=None), \
                    patch.object(lifecycle.procs, "memory", return_value={"available": 0}), \
                    patch.object(lifecycle, "_launch_detached"), \
                    patch.object(lifecycle, "_finish_start", return_value={"state": "healthy"}):
                lifecycle.start(layout, tool_argv=[], log=lambda _: None,
                                expected_idle_generation=lifecycle.idle_generation(layout) if experimental else None)
                self.assertEqual(0 if experimental else 1, census.call_count)


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
    def __init__(self, manifest, bindings, kernel, cut, parent_exits, publication, preexisting="none"):
        self.manifest, self.bindings = manifest, bindings
        self.lock_id = "fixture-host"
        self.state, self.port_open = reservation(), False
        self.kernel, self.cut, self.parent_exits, self.publication = kernel, cut, parent_exits, publication
        self.events = []
        root = Path(bindings["candidate_root"])
        root.mkdir(parents=True)
        self.layouts = {"candidate": SimpleNamespace(root=root, run_record=root / "run.json", lock_file=root / "lock",
            install_record=root / "install.json",
            profile=SimpleNamespace(fingerprint=manifest["candidate"]["profile_fingerprint"], multi_gpu=False,
                                    data=manifest["candidate"]["config"] | {"model": manifest["candidate"]["model"]}))}
        self.owned_runs, self.launch_requests, self.launch_jobs, self.owned_commands = {}, {}, {}, {}
        self.admission_generation = None
        self.root_identities = {p: self.path_identity(p) for p in (root, *root.parents)}
        atomic_write_json(self.layouts["candidate"].install_record, {
            "profile_fingerprint": manifest["candidate"]["profile_fingerprint"], "runtime_identity_sha256": "fixture"})
        if preexisting != "none":
            atomic_write_json(self.layouts["candidate"].run_record, {
                "state": "launching" if preexisting == "pending" else "ready",
                "profile_fingerprint": self.layouts["candidate"].profile.fingerprint,
                "wrapper": {"pid": 900}, "launch_id": "prior-generation"})
            kernel.live[900] = object()  # Outside this invocation's job; never adopt/kill it.

    reservation = FakeAdapter.reservation

    def command(self, arm, script, args, timeout, **kwargs):
        self.events.append(args[0])
        if args[0] == "start":
            path = self.layouts[arm].run_record
            if path.exists() and json.loads(path.read_bytes()).get("state") == "launching":
                raise loop.ExperimentError("pending_launch")
            token = kwargs["env"][lifecycle.EXPERIMENT_LAUNCH_ENV]
            job = self.launch_jobs[arm]
            record = {"experiment_launch_id": token, "launch_id": token,
                      "requested_utc": "fixture", "profile_fingerprint": self.layouts[arm].profile.fingerprint,
                      "state": "launching", "tree_token": token, "runtime_identity_sha256": "fixture"}
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
        root = Path(directory).resolve()
        manifest, bindings = bundle(root / "inputs")
        schedules = itertools.product(("ready", "unreserved", "draining", "port_open"),
            (None, "install", "start", "guard", "run_job", "cleanup", "proof", "reservation_lost"),
            (False, True), ("published", "pending"), ("none", "live", "pending"))
        for index, (control, cut, exited, publication, preexisting) in enumerate(schedules):
            kernel = KernelStub()
            local = bindings | {"candidate_root": str(root / str(index) / "candidate")}
            host = ModelHost(manifest, local, kernel, cut, exited, publication, preexisting)
            if control == "unreserved": host.state["reserved"] = False
            if control == "draining": host.state["phase"] = "Draining"
            if control == "port_open": host.port_open = True
            failure = None
            try:
                with patch.object(lifecycle, "_job_kernel", return_value=kernel), \
                        patch.object(lifecycle, "FileLock", MemoryLock), \
                        patch.object(lifecycle, "WINDOWS", True), \
                        patch.object(lifecycle.subprocess, "run", kernel.cim), \
                        patch.object(lifecycle.procs, "matches", side_effect=lambda identity:
                            SimpleNamespace(pid=900) if identity and identity.get("pid") == 900 else None), \
                        patch.object(loop.nvfp4, "staging_preflight"), \
                        patch.object(lifecycle, "read_key", return_value="fixture"), \
                        patch.object(lifecycle, "runtime_checks", side_effect=lambda *args, **kwargs: {
                            "ready": 101 in kernel.live}), \
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
                if preexisting != "none" and host.events:
                    failure = "effect_before_candidate_root_admission"
                if cut is None and control == "ready" and preexisting == "none" and not exited and publication == "published" and result["status"] != "complete":
                    failure = "reserved_stopped_did_not_run"
            except loop.ExperimentError:
                if control == "ready" or host.events:
                    failure = "unexpected_refusal_or_effect"
            results.append({"schedule": [control, cut, exited, publication, preexisting], "counterexample": failure})
    return results


def successor_schedules():
    """Production admission/dispatch cuts omitted by the parked model, before and after closure."""
    results = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        manifest, bindings = bundle(root / "inputs")
        for competing in ("none", "pending", "live", "stopped"):
            local = bindings | {"candidate_root": str(root / competing)}
            with patch.object(loop.sys, "platform", "win32"):
                adapter = loop.HostAdapter(manifest, local)
            layout = adapter.layouts["candidate"]
            events = []
            class EffectBoundary(Exception):
                pass
            def fetch_boundary(*args, **kwargs):
                events.append("fetch")
                raise EffectBoundary
            def command(arm, script, args, timeout):
                events.append("idle_returned")
                if competing != "none":
                    atomic_write_json(layout.run_record, {
                        "state": "launching" if competing == "pending" else competing,
                        "profile_fingerprint": layout.profile.fingerprint,
                        "tree_token": "a" * 32, "tree_verified_empty": "a" * 32,
                        "launch_id": "competing-generation"})
                    events.append("competing_" + competing)
                parsed = cli.build_parser().parse_args([*args, "--profile", str(layout.profile.path),
                                                        "--root", str(layout.root)])
                cli.cmd_install(parsed)
            adapter.command = command
            with patch.object(lifecycle, "running", return_value={}), \
                    patch.object(lifecycle.ProcessJob, "scan", return_value={}), \
                    patch.object(loop.nvfp4, "staging_preflight"), \
                    patch.object(install.fetch_mod, "fetch", side_effect=fetch_boundary):
                try:
                    adapter.install(manifest, 10)
                except (EffectBoundary, loop.ExperimentError, lifecycle.LifecycleError):
                    pass
            failed = ("fetch" in events) != (competing == "none")
            results.append({"schedule": ["idle", competing, "installer_lock", "fetch"],
                            "events": events, "counterexample": "generation_crossed_install" if failed else None})
        for target in ("scripts/omp_strata.py", "omp_strata/cli.py", "eval/support.py", "private/runner.py"):
            # A tiny real Python closure avoids altering the working tree or executing a workload.
            checkout = root / ("checkout-" + target.replace("/", "-"))
            sources = {"scripts/omp_strata.py": b"import omp_strata.cli\n",
                       "omp_strata/cli.py": b"VALUE = 'frozen'\n",
                       "eval/support.py": b"VALUE = 'frozen'\n"}
            for name, raw in sources.items():
                path = checkout / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            private = root / ("runner-" + target.replace("/", "-") + ".py")
            private.write_bytes(b"import eval.support\n")
            frozen = {"harness_files": {name: loop.sha256(raw) for name, raw in sources.items()},
                      "runner_sha256": sha256_file(private)}
            snapshotter = getattr(loop, "harness_snapshot", None)
            with patch.object(loop, "ROOT", checkout):
                context = (snapshotter(frozen, {"runner": str(private)}, root / ("snapshot-" + target.replace("/", "-")))
                           if snapshotter else contextlib.nullcontext(None))
                with context as receipt:
                    original = private if target == "private/runner.py" else checkout / target
                    expected = original.read_bytes()
                    original.write_bytes(b"VALUE = 'changed after entry check'\n")
                    executed = (Path(receipt["root"]) / target if receipt else original).read_bytes()
                    results.append({"schedule": ["entry_digest", "snapshot", "mutate_" + target, "execute"],
                                    "counterexample": "mutable_execution_source" if executed != expected else None})
    return results


class ControllerModelTests(unittest.TestCase):
    def test_candidate_window_interleavings(self):
        rows = model_schedules()
        failures = [row for row in rows if row["counterexample"]]
        self.assertEqual(384, len(rows))
        self.assertEqual([], failures)

    def test_successor_admission_and_execution_interleavings(self):
        rows = successor_schedules()
        self.assertEqual(8, len(rows))
        self.assertEqual([], [row for row in rows if row["counterexample"]])


def review_schedules():
    names = ("root_swap_at_lock_entry_never_opens_foreign_lock",
             "failed_job_creation_before_spawn_does_not_strand_custody",
             "installer_lock_holder_is_terminated_before_lock_wait_spends_proof_budget",
             "idle_fence_survives_keygen_and_both_start_gaps",
             "attempt_rechecks_candidate_generation_after_short_runner_exit",
             "guard_rechecks_generation_after_http",
             "cleanup_enforces_actual_slice_and_wall_clock_return_deadline",
             "bootstrap_refuses_drift_before_snapshot_and_preserves_reason",
             "bootstrap_native_job_contains_worker_lifetime",
             "isolation_scan_tolerates_disappearing_workload_temporaries")
    rows = []
    for name in names:
        case = DriverTests("test_" + name)
        result = unittest.TestResult()
        case.run(result)
        rows.append({"schedule": name, "counterexample": bool(result.errors or result.failures),
                     "errors": [text for _, text in result.errors + result.failures]})
    return rows


if __name__ == "__main__":
    rows = model_schedules() + successor_schedules() + review_schedules()
    failures = [row for row in rows if row["counterexample"]]
    print(json.dumps({"schedules": len(rows), "counterexamples_after": len(failures), "failures": failures}))
    raise SystemExit(bool(failures))
