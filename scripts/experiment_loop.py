#!/usr/bin/env python3
"""Candidate-only experiments under a lead-owned fleet reservation.

The controller owns the incumbent. This driver reads its authoritative reservation
receipt and checks the incumbent port is closed; it never opens an incumbent root,
starts/stops/adopts an incumbent, writes G10, or releases a controller reservation.
Only the candidate and its frozen workload-runner children enter our Windows jobs.
All evidence and bindings are private. Importing this module has no host effects.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omp_strata import lifecycle
from omp_strata.common import atomic_write_bytes, atomic_write_json, sha256_file, utc_now
from omp_strata.comparison import canonical, read_json, sha256
from omp_strata.layout import Layout
from omp_strata.profile import load
from omp_strata.receipts import schema_errors
from scripts.eval_taskset import HOST_LOCKS
from scripts.requalify import last_object

HARNESS_FILES = ("scripts/experiment_loop.py", "scripts/eval_taskset.py", "scripts/evaluate.py",
                 "omp_strata/lifecycle.py", "omp_strata/procs.py", "omp_strata/profile.py",
                 "omp_strata/install.py", "omp_strata/remote.py", "omp_strata/nvfp4.py",
                 "omp_strata/fetch.py", "omp_strata/layout.py", "omp_strata/cli.py",
                 "schemas/experiment-manifest.schema.json")
HOST_PROFILES = {"rtx5090-win-a": "NVIDIA GeForce RTX 5090",
                 "rtxpro6000-win-a": "NVIDIA RTX PRO 6000 Blackwell Workstation Edition"}
CONTROL_STATE = Path(r"C:\ProgramData\OMP\windows-hosts\state\fleet-control.json")
WINDOW_SECONDS = 12600
RETURN_SECONDS = 1800
CLEANUP_SECONDS = 120
READY_MAX_MIB = 1500


class ExperimentError(ValueError):
    """Closed reason; never include private child output."""


def freeze_arm(profile_id):
    if not isinstance(profile_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]+", profile_id):
        raise ExperimentError("invalid_profile_id")
    profile = load(ROOT / "profiles" / (profile_id + ".json"))
    p = profile.data
    if (profile.multi_gpu or p["host"]["gpu_model"] not in HOST_PROFILES.values()
            or p["host"]["os"] != "windows" or p["host"]["route"] != "native-windows"):
        raise ExperimentError("unsupported_host_profile")
    return {"profile_id": profile.id, "profile_fingerprint": profile.fingerprint,
            "source": {"strata": p["strata"]["commit"], "omp": p["omp"]["source_commit"]},
            "model": p["model"], "quantization": p["model"]["quantization"],
            "template": {"source_commit": p["strata"]["commit"], "model_name": p["strata"]["model_name"]},
            "protocol": "openai-completions", "engine": p["strata"]["engine_version"],
            "harness": p["omp"],
            "artifacts": {**p["strata"]["artifacts"], "python_lock": p["strata"]["python_lock"]},
            "config": {"setup_args": p["strata"]["setup_args"],
                       "expected_engine_flags": p["strata"]["expected_engine_flags"],
                       "strata": p["strata"], "server": p["server"], "host": p["host"]}}


def parse_manifest_bytes(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ExperimentError("duplicate_json_key")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (TypeError, ValueError):
        raise ExperimentError("invalid_manifest_json") from None


def experiment_key(manifest):
    return sha256(canonical(manifest))


def new_manifest(baseline, candidate, *, rationale, retained_evidence, job_manifest, runner, job_subset=None):
    a, b = freeze_arm(baseline), freeze_arm(candidate)
    value = {"schema_version": 2, "comparison_only": True, "rationale": rationale,
             "host_role": next(k for k, v in HOST_PROFILES.items() if v == b["config"]["host"]["gpu_model"]),
             "baseline": a, "candidate": b,
             "candidate_only_against": sha256_file(retained_evidence),
             "job_manifest_sha256": sha256_file(job_manifest), "runner_sha256": sha256_file(runner),
             "harness_files": {p: sha256_file(ROOT / p) for p in HARNESS_FILES},
             "max_window_seconds": WINDOW_SECONDS, "return_budget_seconds": RETURN_SECONDS}
    if job_subset is not None:
        value["job_subset"] = job_subset
        value["job_subset_sha256"] = sha256(canonical(job_subset))
    validate(value)
    return value


def validate(manifest):
    if schema_errors(manifest, read_json(ROOT / "schemas/experiment-manifest.schema.json")):
        raise ExperimentError("invalid_manifest_schema")
    for arm in ("baseline", "candidate"):
        if manifest[arm] != freeze_arm(manifest[arm]["profile_id"]):
            raise ExperimentError("frozen_profile_drift")
        if manifest[arm]["config"]["host"]["gpu_model"] != HOST_PROFILES[manifest["host_role"]]:
            raise ExperimentError("host_profile_mismatch")
    if manifest["baseline"] == manifest["candidate"]:
        raise ExperimentError("identical_arms")
    if manifest["harness_files"] != {p: sha256_file(ROOT / p) for p in HARNESS_FILES}:
        raise ExperimentError("frozen_harness_drift")
    subset = manifest.get("job_subset")
    if (subset is None) != ("job_subset_sha256" not in manifest):
        raise ExperimentError("invalid_job_subset")
    if subset is not None and (len(set(subset)) != len(subset)
            or sha256(canonical(subset)) != manifest["job_subset_sha256"]):
        raise ExperimentError("invalid_job_subset")
    return experiment_key(manifest)


def frozen_file(path, digest):
    raw = Path(path).read_bytes()
    if sha256(raw) != digest:
        raise ExperimentError("frozen_input_digest_mismatch")
    return raw


def load_inputs(manifest, bindings):
    """Freeze private primary evidence and the original denominators before any host effect."""
    raw = frozen_file(bindings["retained_baseline_evidence"], manifest["candidate_only_against"])
    retained = parse_manifest_bytes(raw)
    job_path = Path(bindings["job_manifest"])
    job_raw = frozen_file(job_path, manifest["job_manifest_sha256"])
    jobs = parse_manifest_bytes(job_raw)
    frozen_file(bindings["runner"], manifest["runner_sha256"])
    if retained.get("inputs", {}).get("manifest_sha256") != manifest["job_manifest_sha256"]:
        raise ExperimentError("retained_job_manifest_mismatch")
    wo2 = jobs["wo2"]
    # Basenames only: private companion inputs cannot escape the frozen bundle.
    for name in (wo2["path"], jobs["golden"]["files_manifest"]):
        if Path(name).name != name or name in ("", ".", ".."):
            raise ExperimentError("invalid_bundle_path")
    requests = parse_manifest_bytes(frozen_file(job_path.parent / wo2["path"], wo2["sha256"]))
    frozen_file(job_path.parent / jobs["golden"]["files_manifest"], jobs["golden"]["files_manifest_sha256"])
    if (len(requests["requests"]) != wo2["request_count"]
            or requests["repetitions_per_arm"] != wo2["repetitions_per_arm"]
            or wo2["matched_requests_per_arm"] != wo2["request_count"] * wo2["repetitions_per_arm"]
            or len(jobs["golden"]["tasks"]) != jobs["golden"]["tasks_per_arm"]
            or len(jobs["g24"]["tasks"]) * jobs["g24"]["attempts_per_task"] != jobs["g24"]["denominator_per_arm"]):
        raise ExperimentError("frozen_denominator_mismatch")
    inventory = []
    for family, rows, repetitions in (("WO2", requests["requests"], wo2["repetitions_per_arm"]),
            ("G24", jobs["g24"]["tasks"], jobs["g24"]["attempts_per_task"]),
            ("golden-1", jobs["golden"]["tasks"], jobs["golden"]["repetitions_per_arm"])):
        if type(repetitions) is not int or not 1 <= repetitions <= 20:
            raise ExperimentError("unbounded_job_repetitions")
        for row in rows:
            if not isinstance(row.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", row["id"]):
                raise ExperimentError("invalid_job_id")
            inventory.append({"family": family, "job": row["id"], "planned_attempts_per_arm": repetitions})
    ids = [row["family"] + "/" + row["job"] for row in inventory]
    if len(set(ids)) != len(ids) or not inventory or len(inventory) > 1000:
        raise ExperimentError("invalid_job_inventory")
    baseline = {}
    for row in retained["rows"]:
        key = row["family"] + "/" + row["job"]
        if key in baseline or key not in ids or not isinstance(row.get("baseline"), dict):
            raise ExperimentError("invalid_retained_rows")
        expected = inventory[ids.index(key)]["planned_attempts_per_arm"]
        if row.get("planned_attempts_per_arm") != expected:
            raise ExperimentError("retained_denominator_mismatch")
        baseline[key] = copy.deepcopy(row["baseline"])
    subset = manifest.get("job_subset", ids)
    if not set(subset) <= set(ids):
        raise ExperimentError("unknown_subset_job")
    return {"retained_raw": raw, "job_raw": job_raw, "inventory": inventory,
            "selected": [row for row in inventory if row["family"] + "/" + row["job"] in subset],
            "baseline": baseline}


def check_reservation(state, binding):
    """Consume fleet status's actual Ready-for-you receipt, not its early Reserved event.

    Controller resources.ready is issued only after exact-generation stop and GPU
    UUID/VRAM checks. We consume that proof; no independent incumbent inspection.
    """
    generation = binding.get("generation")
    resources = state.get("resources", {})
    if (type(generation) is not int or generation <= 0 or state.get("schema_version") != 1
            or state.get("host") != binding.get("host") or state.get("generation") != generation
            or state.get("reserved") is not True or state.get("admission_open") is not False
            or state.get("phase") != "Ready for you" or state.get("blockers") != []
            or "recovery_hold" in state or "supervisor_transaction" in state
            or resources.get("ready") is not True or resources.get("blockers") != []
            or resources.get("unexplained_compute") != []
            or resources.get("observed_generation") != generation
            or not isinstance(state.get("jobs"), dict)
            or any(j.get("state") not in ("drained", "cancelled") for j in state["jobs"].values())):
        raise ExperimentError("controller_reservation_not_ready")
    expected = binding.get("gpu_uuids")
    gpus = resources.get("gpus")
    observed = resources.get("observed_utc")
    service_generation = (state.get("service") or {}).get("generation")
    if (not isinstance(expected, list) or not expected or len(set(expected)) != len(expected)
            or not isinstance(gpus, list) or len(gpus) != len(expected)
            or {g.get("uuid") for g in gpus} != set(expected)
            or any(type(g.get("used_mib")) is not int or not 0 <= g["used_mib"] < READY_MAX_MIB for g in gpus)
            or type(service_generation) is not int or not 0 < service_generation <= generation
            or type(observed) not in (float, int) or not math.isfinite(observed) or observed <= 0):
        raise ExperimentError("controller_stop_receipt_invalid")
    return observed


@contextlib.contextmanager
def host_lock(lock_id, directory=HOST_LOCKS):
    if not isinstance(lock_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", lock_id):
        raise ExperimentError("invalid_lock_id")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (lock_id + ".lock")
    try:
        stream = path.open("x", encoding="utf-8")
    except FileExistsError:
        raise ExperimentError("host_lock_owned") from None
    owner = {"pid": os.getpid(), "utc": utc_now(), "persistent_hold": True}
    lease = {"release": False}
    try:
        with stream:
            json.dump(owner, stream)
        yield lease
    finally:
        if lease["release"] and path.exists() and read_json(path) == owner:
            path.unlink()


def run(manifest, adapter, *, bindings, evidence_dir, lock_directory=HOST_LOCKS,
        clock=time.monotonic, wall_clock=time.time):
    key = validate(manifest)
    inputs = load_inputs(manifest, bindings)
    evidence_dir = Path(evidence_dir).resolve()
    if evidence_dir == ROOT or ROOT in evidence_dir.parents:
        raise ExperimentError("private_evidence_required")
    # No evidence directories, locks, installs or launches on an unreserved host.
    observed = adapter.reservation(require_closed_port=True)
    left = min(manifest["max_window_seconds"] - manifest["return_budget_seconds"],
               observed + manifest["max_window_seconds"] - manifest["return_budget_seconds"] - wall_clock())
    if left <= CLEANUP_SECONDS or observed > wall_clock():
        raise ExperimentError("reservation_window_expired")
    started, deadline = clock(), clock() + left - CLEANUP_SECONDS
    directory = evidence_dir / (key + "-g" + str(bindings["controller"]["generation"]))
    directory.mkdir(parents=True, exist_ok=False)
    atomic_write_bytes(directory / "retained-baseline-evidence.json", inputs["retained_raw"])
    atomic_write_bytes(directory / "job-manifest.json", inputs["job_raw"])
    atomic_write_json(directory / "manifest.json", manifest)
    measured = {"status": "running", "comparison_only": True, "started_utc": utc_now(),
                "controller_generation": bindings["controller"]["generation"],
                "controller_observed_utc": observed, "return_deadline_utc": observed + manifest["max_window_seconds"],
                "return_budget_seconds": manifest["return_budget_seconds"],
                "baseline_execution": "external_retained_evidence", "attempts": [], "failures": [],
                "inventory": inputs["inventory"], "selected": inputs["selected"],
                "candidate_tree_dead": False, "custody_released": False}
    def save():
        measured["wall_time_s"] = max(0, clock() - started)
        atomic_write_json(directory / "measurements.json", measured)
    def remaining():
        left = min(deadline - clock(), observed + manifest["max_window_seconds"]
                   - manifest["return_budget_seconds"] - CLEANUP_SECONDS - wall_clock())
        if left <= 0:
            raise ExperimentError("max_wall_time")
        return left
    save()
    with host_lock(adapter.lock_id, lock_directory) as lease:
        try:
            adapter.reservation(require_closed_port=True)
            adapter.install(manifest, remaining())
            adapter.reservation(require_closed_port=True)
            load_started = clock()
            adapter.start("candidate", remaining())
            measured["cold_load_wall_s"] = clock() - load_started
            save()
            for job in inputs["selected"]:
                for attempt in range(1, job["planned_attempts_per_arm"] + 1):
                    remaining()
                    row = {"family": job["family"], "job": job["job"], "attempt": attempt,
                           "status": "attempted", "started_utc": utc_now()}
                    measured["attempts"].append(row)
                    save()  # Persist the denominator before guard or runner effects.
                    t0 = clock()
                    try:
                        adapter.guard("candidate", remaining())
                        result = adapter.run_job(job, attempt, remaining())
                        expected = {"family": job["family"], "job": job["job"], "attempt": attempt,
                                    "job_manifest_sha256": manifest["job_manifest_sha256"]}
                        if (not isinstance(result, dict) or any(result.get(k) != v for k, v in expected.items())
                                or result.get("status") not in ("complete", "failed")
                                or type(result.get("passed")) is not bool
                                or result.get("external_clients_stopped") is not True):
                            raise ExperimentError("runner_result_unbound")
                        row.update(status=result["status"], result=result)
                    finally:
                        row["charged_wall_s"] = max(0, clock() - t0)
                        save()
            measured["status"] = "complete" if all(r["status"] == "complete" for r in measured["attempts"]) else "failed"
        except (Exception, KeyboardInterrupt) as exc:
            measured["status"] = "partial"
            measured["failures"].append(str(exc) if isinstance(exc, ExperimentError) else type(exc).__name__)
        finally:
            try:
                adapter.cleanup(CLEANUP_SECONDS)
                measured["candidate_tree_dead"] = True
            except (Exception, KeyboardInterrupt) as exc:
                measured["status"] = "cleanup_failed"
                measured["failures"].append(type(exc).__name__)
            # This releases only our persistent local lock, never controller state.
            measured["custody_released"] = (measured["candidate_tree_dead"]
                and all(r.get("result", {}).get("external_clients_stopped") is True
                        for r in measured["attempts"] if r["family"] == "golden-1"))
            save()
            atomic_write_json(directory / "comparison.json", report(directory))
            lease["release"] = measured["custody_released"]
    return directory


class HostAdapter:
    """Native candidate worker; all host effects require a controller reservation."""
    def __init__(self, manifest, bindings):
        if sys.platform != "win32":
            raise ExperimentError("run_requires_native_windows_detached_worker")
        self.manifest, self.bindings = manifest, bindings
        self.lock_id = bindings["host_lock_id"]
        root_text = bindings["candidate_root"]
        root = Path(root_text)
        if not root.is_absolute():
            raise ExperimentError("absolute_candidate_root_required")
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (root, *root.parents)):
            raise ExperimentError("root_reparse_point")
        root = root.resolve()
        home = Path.home().resolve()
        if (root.parent == root or root == home or root in home.parents or root == ROOT or ROOT in root.parents
                or root in ROOT.parents and ROOT != root / "tooling"):
            raise ExperimentError("unsafe_integration_root")
        layout = Layout(root, load(ROOT / "profiles" / (manifest["candidate"]["profile_id"] + ".json")))
        if layout.install_record.exists() and read_json(layout.install_record).get("profile_fingerprint") != layout.profile.fingerprint:
            raise ExperimentError("candidate_root_owned_by_another_profile")
        self.layouts = {"candidate": layout}
        self.owned_runs, self.launch_requests, self.launch_jobs, self.owned_commands = {}, {}, {}, {}
        self.disk_floors = {"candidate": layout.profile.data["host"]["min_free_disk_gib"]}

    def reservation(self, *, require_closed_port=False):
        observed = check_reservation(parse_manifest_bytes(CONTROL_STATE.read_bytes()), self.bindings["controller"])
        if require_closed_port:
            srv = self.manifest["baseline"]["config"]["server"]
            if lifecycle.port_in_use(srv["listen_host"], srv["port"]):
                raise ExperimentError("incumbent_port_open")
        return observed

    def command(self, arm, script, args, timeout, *, monitor=False, env=None):
        self.reservation()
        layout = self.layouts[arm]
        root = layout.root
        if root in self.owned_commands:
            raise ExperimentError("command_cleanup_unresolved")
        private = root / "evidence/experiments"
        private.mkdir(parents=True, exist_ok=True)
        prefix = private / str(time.time_ns())
        argv = [sys.executable, str(ROOT / "scripts" / script), *args,
                "--profile", str(layout.profile.path), "--root", str(root)]
        with prefix.with_suffix(".out").open("wb") as out, prefix.with_suffix(".err").open("wb") as err:
            owned = self.owned_commands[root] = {"child": None, "job": None}
            launching = script == "omp_strata.py" and args[0] == "start"
            job = owned["job"] = (self.launch_jobs[arm] if launching else lifecycle.ProcessJob(os.urandom(16).hex()))
            try:
                child = owned["child"] = job.spawn(argv, stdout=out, stderr=err, env={**os.environ, **(env or {})})
                end = time.monotonic() + timeout
                while child.poll() is None:
                    left = end - time.monotonic()
                    if left <= 0:
                        raise ExperimentError("max_wall_time")
                    self.reservation()
                    if monitor:
                        self.guard(arm, left)
                    try:
                        child.wait(timeout=min(2, left))
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                child = owned["child"]
                if not launching or child is None or child.poll() is None:
                    job.stop(30)
                if child is not None:
                    child.wait(timeout=30)
                del self.owned_commands[root]
        result = last_object(prefix.with_suffix(".out").read_text(encoding="utf-8", errors="replace"))
        if child.returncode:
            raise ExperimentError("child_failed")
        return result

    def install(self, manifest, timeout):
        started = time.monotonic()
        self.command("candidate", "omp_strata.py", ["install"], timeout)
        self.command("candidate", "omp_strata.py", ["keygen"], max(1, timeout - (time.monotonic() - started)))

    def start(self, arm, timeout):
        self.reservation(require_closed_port=True)
        layout = self.layouts[arm]
        if layout.root in self.owned_commands:
            raise ExperimentError("command_cleanup_unresolved")
        if arm in self.launch_requests or arm in self.launch_jobs:
            raise ExperimentError("launch_cleanup_unresolved")
        if lifecycle.running(layout):
            raise ExperimentError("root_already_running")
        launch_id = os.urandom(16).hex()
        self.launch_requests[arm] = {"experiment_launch_id": launch_id,
                                    "profile_fingerprint": layout.profile.fingerprint}
        self.launch_jobs[arm] = lifecycle.ProcessJob(launch_id)
        captured = False
        try:
            result = self.command(arm, "omp_strata.py", ["start", "--timeout", str(max(1, int(timeout)))], timeout,
                                  env={lifecycle.EXPERIMENT_LAUNCH_ENV: launch_id})
        finally:
            with lifecycle.FileLock(layout.lock_file, timeout=120):
                current = read_json(layout.run_record) if layout.run_record.exists() else {}
                request = self.launch_requests[arm]
                if all(current.get(k) == v for k, v in request.items()):
                    request.update({k: current.get(k) for k in ("launch_id", "requested_utc")})
                    captured = bool(current.get("requested_utc") and current.get("launch_id") and current.get("server"))
                    if captured:
                        self.owned_runs[arm] = {k: current.get(k) for k in
                                               ("requested_utc", "profile_fingerprint", "wrapper", "server")}
        if not captured:
            raise ExperimentError("start_generation_unverified")
        return result

    def stop(self, arm, timeout):
        owned = self.owned_runs.get(arm)
        request = self.launch_requests.get(arm)
        layout = self.layouts[arm]
        # The root lock cancels even an identity-less pending request before release.
        with lifecycle.FileLock(layout.lock_file, timeout=timeout):
            current = read_json(layout.run_record) if layout.run_record.exists() else {}
            command = self.owned_commands.get(layout.root)
            command_error = None
            job = self.launch_jobs.get(arm)

            def finish_launch_command():
                if command and job is not None and command.get("job") is job:
                    if command.get("child"):
                        command["child"].wait(timeout=30)
                    self.owned_commands.pop(layout.root, None)

            if command and (job is None or command.get("job") is not job):
                try:
                    if command.get("job") is None:
                        raise ExperimentError("command_cleanup_unresolved")
                    command["job"].stop(30)
                    if command.get("child"):
                        command["child"].wait(timeout=30)
                    del self.owned_commands[layout.root]
                except Exception as exc:
                    command_error = exc
            if request is not None and any(current.get(k) != v for k, v in request.items()):
                if owned is not None:
                    raise ExperimentError("owned_generation_changed")
                if job:
                    job.stop(min(30, timeout))
                    finish_launch_command()
                    del self.launch_jobs[arm]
                del self.launch_requests[arm]
                if command_error:
                    raise ExperimentError("command_cleanup_unresolved") from command_error
                return
            if owned is None and request is None:
                if command_error:
                    raise ExperimentError("command_cleanup_unresolved") from command_error
                return
            if owned is not None and any(current.get(k) != v for k, v in owned.items()):
                raise ExperimentError("owned_generation_changed")
            lifecycle.stop(layout, log=lambda _: None, locked=True, job=job)
            if job and job.handle:
                job.stop(min(30, timeout))
            finish_launch_command()
            self.launch_jobs.pop(arm, None)
            self.owned_runs.pop(arm, None)
            self.launch_requests.pop(arm, None)
            if command_error:
                raise ExperimentError("command_cleanup_unresolved") from command_error

    def guard(self, arm, timeout):
        self.reservation()
        layout = self.layouts[arm]
        if shutil.disk_usage(layout.root).free / (1 << 30) < self.disk_floors[arm]:
            raise ExperimentError("disk_floor")
        if lifecycle.status(layout).get("state") != "healthy":
            raise ExperimentError("runtime_identity_lost")
        job = self.launch_jobs[arm]
        if not job.pids() or not job.enumerate_tree():
            raise ExperimentError("candidate_job_identity_lost")

    def run_job(self, job, attempt, timeout):
        runner = Path(self.bindings["runner"]).resolve()
        frozen_file(runner, self.manifest["runner_sha256"])
        frozen_file(self.bindings["job_manifest"], self.manifest["job_manifest_sha256"])
        return self.command("candidate", str(runner), [
            "--job-manifest", str(Path(self.bindings["job_manifest"]).resolve()),
            "--job-manifest-sha256", self.manifest["job_manifest_sha256"],
            "--family", job["family"], "--job", job["job"], "--attempt", str(attempt),
            "--timeout", str(timeout)], timeout, monitor=True)

    def cleanup(self, timeout):
        errors = []
        try:
            self.stop("candidate", timeout)
        except BaseException as exc:
            errors.append(exc)
        # A changed record or unavailable root lock must not skip native cleanup.
        jobs = [*self.launch_jobs.values(), *(v["job"] for v in self.owned_commands.values() if v["job"])]
        for job in jobs:
            try:
                job.stop(min(30, timeout))
            except BaseException as exc:
                errors.append(exc)
        if errors or self.launch_requests or self.owned_commands or any(not j.verified_empty for j in jobs):
            raise ExperimentError("candidate_cleanup_unproved")


def report(directory):
    manifest = read_json(directory / "manifest.json")
    measured = read_json(directory / "measurements.json")
    retained = parse_manifest_bytes(frozen_file(directory / "retained-baseline-evidence.json", manifest["candidate_only_against"]))
    baseline = {r["family"] + "/" + r["job"]: r["baseline"] for r in retained["rows"]}
    rows = []
    for job in measured["inventory"]:
        key = job["family"] + "/" + job["job"]
        attempts = [r for r in measured["attempts"] if (r["family"], r["job"]) == (job["family"], job["job"])]
        rows.append({**job, "baseline": copy.deepcopy(baseline.get(key)),
                     "baseline_provenance": {"kind": "retained" if key in baseline else "unavailable",
                                             "sha256": manifest["candidate_only_against"]},
                     "candidate": {"attempted": len(attempts),
                                   "completed": sum(r["status"] == "complete" for r in attempts),
                                   "passed": sum(r.get("result", {}).get("passed") is True for r in attempts),
                                   "attempts": attempts}})
    return {"schema_version": 2, "comparison_only": True, "status": measured["status"],
            "candidate_only_against": manifest["candidate_only_against"],
            "job_manifest_sha256": manifest["job_manifest_sha256"],
            "job_subset": manifest.get("job_subset"), "job_subset_sha256": manifest.get("job_subset_sha256"),
            "planned_jobs": len(rows), "selected_jobs": len(measured["selected"]),
            "planned_attempts": sum(r["planned_attempts_per_arm"] for r in rows),
            "selected_attempts": sum(r["planned_attempts_per_arm"] for r in measured["selected"]),
            "attempted": len(measured["attempts"]),
            "completed": sum(r["status"] == "complete" for r in measured["attempts"]),
            "candidate_tree_dead": measured["candidate_tree_dead"], "custody_released": measured["custody_released"],
            "rows": rows, "failures": measured["failures"], "recommendation": "hold",
            "timing_caveats": ["Incumbent rows are copied from an earlier retained window, not rerun or contemporaneous.",
                "Candidate cold load and transcript replay are charged separately; no uninterrupted warm-only claim.",
                "All attempted, failed, interrupted and unscheduled work remains in the frozen denominators.",
                "Runner wall includes client/replay/verifier overhead; family metrics are not interchangeable.",
                "The controller alone returns the incumbent. Its reserved return budget is not measured driver execution."],
            "cold_load_wall_s": measured.get("cold_load_wall_s"), "wall_time_s": measured["wall_time_s"],
            "return_deadline_utc": measured["return_deadline_utc"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    for name in ("baseline", "candidate", "rationale"):
        plan.add_argument("--" + name, required=True)
    for name in ("candidate-only-against", "job-manifest", "runner", "out"):
        plan.add_argument("--" + name, required=True, type=Path)
    plan.add_argument("--job-subset", type=Path, help="Lead-selected JSON list of family/job ids; omitted means all jobs")
    execute = sub.add_parser("run")
    for name in ("manifest", "bindings", "evidence-dir"):
        execute.add_argument("--" + name, required=True, type=Path)
    show = sub.add_parser("report")
    show.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            if args.out.exists():
                raise ExperimentError("plan_output_exists")
            result = new_manifest(args.baseline, args.candidate, rationale=args.rationale,
                retained_evidence=args.candidate_only_against, job_manifest=args.job_manifest, runner=args.runner,
                job_subset=json.loads(args.job_subset.read_bytes()) if args.job_subset else None)
            load_inputs(result, {"retained_baseline_evidence": args.candidate_only_against,
                                "job_manifest": args.job_manifest, "runner": args.runner})
            atomic_write_json(args.out, result)
        elif args.command == "run":
            manifest = parse_manifest_bytes(args.manifest.read_bytes())
            bindings = parse_manifest_bytes(args.bindings.read_bytes())
            result = report(run(manifest, HostAdapter(manifest, bindings), bindings=bindings, evidence_dir=args.evidence_dir))
        else:
            result = report(args.directory)
        print(json.dumps(result, indent=2, allow_nan=False))
        return int(args.command == "run" and result["status"] != "complete")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc) if isinstance(exc, ExperimentError) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
