#!/usr/bin/env python3
"""Frozen, comparison-only experiments; run on the GPU host through launch-detached.ps1.

Private bindings: {"roots": {"baseline": "...", "candidate": "..."},
"host_lock_id": "..."}. Use the SAME lock id as eval_taskset on this machine.
The candidate must have its own root. No defaults change and no real work is routed.
--quiesce-incumbent opts into a claimed warm-baseline stop after external serving fence/drain.
Failed restoration retains the physical claim for operator reconciliation, never stale-lock takeover.
Only aggregate perf_probe output is public; raw child output stays in the host root.
A performance-only experiment can recommend more evaluation, never adoption.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omp_strata import lifecycle, procs
from omp_strata.common import atomic_write_json, sha256_file, utc_now
from omp_strata.comparison import canonical, read_json, sha256
from omp_strata.layout import Layout
from omp_strata.profile import load
from omp_strata.receipts import schema_errors
from scripts.eval_taskset import HOST_LOCKS
from scripts.publish_run import Scrubber, encoded, private_denylist
from scripts.requalify import last_object

RELEASES = ROOT / "releases/experiments"
HARNESS_FILES = ("scripts/experiment_loop.py", "scripts/perf_probe.py", "scripts/eval_taskset.py",
                 "omp_strata/lifecycle.py", "omp_strata/profile.py", "omp_strata/install.py",
                 "omp_strata/remote.py", "omp_strata/nvfp4.py", "omp_strata/fetch.py",
                 "omp_strata/layout.py", "schemas/experiment-manifest.schema.json")
METRICS = ["ttft_ms", "prefill_tokens_s", "decode_tokens_s", "queue_wait_lower_ms", "queue_wait_upper_ms"]
HOST_PROFILES = {"rtx5090-win-a": "NVIDIA GeForce RTX 5090",
                 "rtxpro6000-win-a": "NVIDIA RTX PRO 6000 Blackwell Workstation Edition"}


class ExperimentError(ValueError):
    """Closed public-safe reason, never raw subprocess output."""


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


def identity_key(manifest):
    # Repetitions, narrative, timestamps, and workload changes cannot bypass deduplication.
    arm = manifest["candidate"]
    return sha256(canonical({k: v for k, v in arm.items() if k not in ("profile_id", "profile_fingerprint")}))


def experiment_key(manifest):
    identity = identity_key(manifest)
    return sha256(canonical({"identity": identity, "retry_of": manifest["retry_of"]})) if "retry_of" in manifest else identity


def new_manifest(baseline, candidate, *, repetitions=3, rationale, host_profile=None, retry_of=None,
                 resume_candidate=False):
    a, b = freeze_arm(baseline), freeze_arm(candidate)
    role = host_profile or next(role for role, gpu in HOST_PROFILES.items() if gpu == a["config"]["host"]["gpu_model"])
    manifest = {"schema_version": 1, "host_role": role, "rationale": rationale,
            "baseline": a, "candidate": b, "restoration_target": a,
            "harness_files": {p: sha256_file(ROOT / p) for p in HARNESS_FILES},
            "workload": {"kind": "perf_probe", "id": "unique-prefix-warm-queue-v1",
                         "depths": [0, 8192, 32768, 65536, 102400], "warm_depth": 32768,
                         "max_tokens": 512, "request_timeout_s": 600},
            "repetitions": repetitions, "metrics": METRICS.copy(),
            "stop_conditions": {"max_wall_time_s": 3600, "max_failures": 1,
                                "abort_on_gpu_busy": True, "abort_on_competing_tenant": True,
                                "abort_on_disk_floor": True,
                                "disk_floor_gib": max(a["config"]["host"]["min_free_disk_gib"],
                                                      b["config"]["host"]["min_free_disk_gib"])}}
    if retry_of is not None:
        manifest["retry_of"] = retry_of
    if resume_candidate:
        manifest["resume_candidate"] = True
    return manifest


def retry_receipt(retry_of, releases):
    """Load a prior receipt structurally; never surface its bytes, path or a structural exception.

    Historical manifests satisfy the schema but are not re-frozen against today's checkout,
    and their own retry_of ancestors are not admitted recursively.
    """
    previous = releases / retry_of
    if not previous.is_dir():
        raise ExperimentError("retry_receipt_missing")
    try:
        prior, measured, restored = (read_json(previous / (name + ".json"))
                                     for name in ("manifest", "measurements", "restoration"))
    except (OSError, ValueError):
        raise ExperimentError("retry_receipt_unreadable") from None
    if schema_errors(prior, read_json(ROOT / "schemas/experiment-manifest.schema.json")):
        raise ExperimentError("retry_receipt_malformed")
    # A matching candidate copied under another receipt key cannot authorize a retry.
    if experiment_key(prior) != retry_of:
        raise ExperimentError("retry_receipt_key_mismatch")
    rows = measured.get("baseline"), measured.get("candidate")
    if (not isinstance(measured.get("status"), str) or not all(isinstance(arm, list) for arm in rows)
            or not isinstance(restored.get("status"), str) or "serving" not in restored
            or not isinstance(restored["serving"], (bool, type(None)))
            or any(not isinstance(row, dict) or type(row.get("repetition")) is not int
                   or not isinstance(row.get("result"), dict) for arm in rows for row in arm)):
        raise ExperimentError("retry_receipt_malformed")
    return prior, measured, restored


def validate(manifest, *, releases=RELEASES, dedupe=True):
    errors = schema_errors(manifest, read_json(ROOT / "schemas/experiment-manifest.schema.json"))
    if errors:
        raise ExperimentError("invalid_manifest_schema")
    for name in ("baseline", "candidate", "restoration_target"):
        if manifest[name] != freeze_arm(manifest[name]["profile_id"]):
            raise ExperimentError("frozen_profile_drift")
        if manifest[name]["config"]["host"]["gpu_model"] != HOST_PROFILES[manifest["host_role"]]:
            raise ExperimentError("host_profile_mismatch")
    if manifest["restoration_target"] != manifest["baseline"]:
        raise ExperimentError("restoration_must_match_predecessor")
    if manifest["baseline"] == manifest["candidate"]:
        raise ExperimentError("identical_arms")
    if manifest["harness_files"] != {p: sha256_file(ROOT / p) for p in HARNESS_FILES}:
        raise ExperimentError("frozen_harness_drift")
    work, stop = manifest["workload"], manifest["stop_conditions"]
    if (manifest["repetitions"] > 20 or stop["max_wall_time_s"] > 86400 or stop["max_failures"] > 20
            or work["request_timeout_s"] > 3600 or len(work["depths"]) > 32):
        raise ExperimentError("unbounded_experiment")
    window = min(manifest[a]["config"]["setup_args"]["context"] for a in ("baseline", "candidate"))
    if max(*work["depths"], work["warm_depth"]) + work["max_tokens"] + 8 >= window:
        raise ExperimentError("workload_exceeds_common_context")
    if stop["disk_floor_gib"] < max(manifest[a]["config"]["host"]["min_free_disk_gib"] for a in ("baseline", "candidate")):
        raise ExperimentError("disk_floor_below_profile")
    if "retry_of" in manifest:
        prior, measured, restored = retry_receipt(manifest["retry_of"], releases)
        blocked = (measured["status"] == "blocked" and not measured["baseline"] and not measured["candidate"]
                   and restored["status"] == "not_required")
        failed = (measured["status"] == "failed" and restored["status"] == "restored"
                  and restored["serving"] is True)
        if (identity_key(prior) != identity_key(manifest) or prior["baseline"] != manifest["baseline"]
                or not (blocked or failed)):
            raise ExperimentError("retry_requires_matching_blocked_or_restored_failed_trial")
        # Old baseline rows may not silently cross a frozen tooling change; a full retry may.
        if manifest.get("resume_candidate") and (
                not failed or measured["candidate"] or prior["workload"] != manifest["workload"]
                or prior["repetitions"] != manifest["repetitions"]
                or prior["harness_files"] != manifest["harness_files"]
                or [r["repetition"] for r in measured["baseline"]] != list(range(1, manifest["repetitions"] + 1))
                or any(r["result"].get("status") != "complete" for r in measured["baseline"])):
            raise ExperimentError("resume_requires_complete_baseline_and_unstarted_candidate")
    elif manifest.get("resume_candidate"):
        raise ExperimentError("resume_requires_retry_receipt")
    key = experiment_key(manifest)
    if dedupe and (releases / key).exists():
        raise ExperimentError("duplicate_identity")
    Scrubber("<private-root>", denylist=private_denylist()).check(encoded(manifest))
    return key


def aggregate_only(value):
    """Raw material is never a public experiment result, even if it has no private terms."""
    if isinstance(value, dict):
        return {k: aggregate_only(v) for k, v in value.items()
                if k not in {"raw_log", "raw_logs", "stdout", "stderr", "transcript", "prompts", "responses"}}
    if isinstance(value, list):
        return [aggregate_only(v) for v in value]
    return value


def public_write(path, value, scrubber):
    # Scrub *before* creating a public file; hygiene errors never leak the refused bytes.
    safe = json.loads(scrubber.scrub(encoded(aggregate_only(value))))
    atomic_write_json(path, safe)


@contextlib.contextmanager
def host_lock(lock_id, directory=HOST_LOCKS):
    if not isinstance(lock_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", lock_id):
        raise ExperimentError("invalid_lock_id")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (lock_id + ".lock")
    # Same name and PID record as eval_taskset. Never steal a stale/ambiguous claim:
    # os.kill(pid, 0), used by that macOS scheduler, is not a safe Windows liveness probe.
    try:
        stream = path.open("x", encoding="utf-8")
    except FileExistsError:
        raise ExperimentError("host_lock_owned") from None
    owner = {"pid": os.getpid(), "utc": utc_now()}
    claim = {"retain": False}
    try:
        with stream:
            json.dump(owner, stream)
        yield claim
    finally:
        if path.exists() and read_json(path) == owner:
            if claim["retain"]:
                atomic_write_json(path, {**owner, "restoration_hold": True})
            else:
                path.unlink()


ADMISSION_FLAGS = ("reachable", "gpu_idle", "ram_above_floor", "disk_above_floor", "no_competing_tenant",
                   "predecessor_matches", "doctor_ok")


def check_preconditions(observation):
    failures = [name for name in ADMISSION_FLAGS if observation.get(name) is not True]
    if failures:
        raise ExperimentError("precondition:" + ",".join(failures))


def run(manifest, adapter, *, releases=RELEASES, lock_directory=HOST_LOCKS, clock=time.monotonic,
        quiesce_incumbent=False):
    key = validate(manifest, releases=releases)
    directory = releases / key
    directory.mkdir(parents=True, exist_ok=False)
    started = clock()
    deadline = started + manifest["stop_conditions"]["max_wall_time_s"]
    measurements = {"status": "running", "started_utc": utc_now(), "preconditions": [], "baseline": [], "candidate": []}
    failures = []
    restoration = {"status": "not_required", "reason": "no_lifecycle_mutation", "serving": None}
    mutated = False

    def save():
        measurements["wall_time_s"] = round(clock() - started, 3)
        for name, data in (("manifest", manifest), ("measurements", measurements), ("failures", failures),
                           ("restoration", restoration)):
            public_write(directory / (name + ".json"), data, adapter.scrubber)

    def remaining():
        value = deadline - clock()
        if value <= 0:
            raise ExperimentError("max_wall_time")
        return value

    def observe():
        observation = adapter.precondition(manifest, remaining())
        observation["host_lock_acquired"] = True
        measurements["preconditions"].append(observation)
        save()
        check_preconditions(observation)

    def settle(after_arm):
        observations = adapter.settle(remaining())
        measurements.setdefault("ram_settle", []).append({"after_arm": after_arm, **observations})
        save()

    try:
        with host_lock(adapter.lock_id, lock_directory) as claim:
            try:
                if quiesce_incumbent:
                    # Stopping a warm predecessor is already a lifecycle mutation, even if stop raises.
                    # The adapter must fence/drain owned serving before returning from this handoff.
                    mutated = True
                    measurements["incumbent_handoff"] = {"mode": "loop_quiesce_requested", "status": "pending"}
                    save()
                    handoff_started = clock()
                    measurements["incumbent_handoff"] = adapter.quiesce(manifest, remaining())
                    measurements["incumbent_handoff"]["wall_time_s"] = round(clock() - handoff_started, 3)
                    save()
                if manifest.get("resume_candidate"):
                    settle("preserved_baseline")
                observe()
                # Restoration owns its independent bounded budget, even after the trial wall cap.
                mutated = True
                adapter.install(manifest, remaining())
                if manifest.get("resume_candidate"):
                    prior = retry_receipt(manifest["retry_of"], releases)[1]
                    measurements["baseline"] = [dict(copy.deepcopy(row), source_experiment=manifest["retry_of"])
                                                for row in prior["baseline"]]
                    measurements["baseline_source_experiment"] = manifest["retry_of"]
                for arm in (("candidate",) if manifest.get("resume_candidate") else ("baseline", "candidate")):
                    observe()
                    load_started = clock()
                    adapter.start(arm, remaining())
                    measurements.setdefault("cold_load", []).append(
                        {"arm": arm, "wall_time_s": round(clock() - load_started, 3),
                         "transcript_replay_required": True})
                    save()
                    for repetition in range(manifest["repetitions"]):
                        remaining()
                        try:
                            adapter.guard(arm, remaining())
                            result = adapter.probe(arm, manifest["workload"], remaining())
                            measurements[arm].append({"repetition": repetition + 1, "result": result})
                            if result.get("status") != "complete":
                                raise ExperimentError("probe_failed")
                        except ExperimentError as exc:
                            failures.append({"arm": arm, "repetition": repetition + 1, "reason": str(exc)})
                            save()
                            if str(exc) != "probe_failed" or len(failures) >= manifest["stop_conditions"]["max_failures"]:
                                raise ExperimentError("stop_condition") from None
                        save()
                    adapter.stop(arm, remaining())
                    if arm == "baseline":
                        settle(arm)
                measurements["status"] = "failed" if failures else "complete"
            except (Exception, KeyboardInterrupt) as exc:
                reason = str(exc) if isinstance(exc, ExperimentError) else type(exc).__name__
                failures.append({"reason": reason})
                measurements["status"] = "failed" if mutated else "blocked"
            finally:
                if mutated:
                    restore_started = clock()
                    try:
                        restoration = adapter.restore(manifest)
                        if restoration.get("serving") is not True:
                            measurements["status"] = "restoration_failed"
                    except (Exception, KeyboardInterrupt) as exc:
                        restoration = {"status": "failed", "serving": False, "reason": type(exc).__name__}
                        measurements["status"] = "restoration_failed"
                    if restoration.get("serving") is not True:
                        # Never turn failed/unknown restoration into a fresh launch opportunity.
                        claim["retain"] = True
                    measurements["restoration_wall_time_s"] = round(clock() - restore_started, 3)
                save()
    except ExperimentError as exc:
        measurements["status"] = "blocked"
        failures.append({"reason": str(exc)})
        save()
    return directory


def utc_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def validate_observation(observation):
    """Supplied operator data is checked before any field is used; the reason never echoes its content."""
    if (not isinstance(observation, dict)
            or any(type(observation.get(name)) is not bool for name in ADMISSION_FLAGS)
            or not utc_timestamp(observation.get("timestamp_utc"))
            or type(observation.get("wall_time_s")) not in (int, float)
            or not math.isfinite(observation["wall_time_s"]) or observation["wall_time_s"] < 0):
        raise ExperimentError("invalid_observation")


def record_blocked(manifest, observation, *, releases=RELEASES):
    """Publish a read-only operator observation, never turn supplied data into start authority.

    Every refusal (observation, manifest, scrubber) happens before the experiment-key directory is
    created, so rejected input never consumes the identity. The directory is created exclusively; an
    existing one, including a concurrent writer's, is never overwritten or removed.
    """
    validate_observation(observation)
    try:
        check_preconditions(observation)
    except ExperimentError as exc:
        reason = str(exc)
    else:
        raise ExperimentError("observation_does_not_establish_blocker")
    key = validate(manifest, releases=releases)
    directory = releases / key
    scrubber = Scrubber("<private-root>", denylist=private_denylist())
    records = {
        "manifest": manifest,
        "measurements": {"status": "blocked", "started_utc": observation["timestamp_utc"],
                         "wall_time_s": observation["wall_time_s"], "preconditions": [observation],
                         "baseline": [], "candidate": [],
                         "missing_reason": "preconditions refused; neither arm started"},
        "failures": [{"reason": reason}],
        "restoration": {"status": "not_required", "serving": None,
                        "reason": "read_only_preflight; no lifecycle mutation or GPU experiment",
                        "observed_predecessor": observation.get("observed_predecessor")},
    }
    # Validate every public byte before reserving the identity or publishing any of the four files.
    safe = {name: json.loads(scrubber.scrub(encoded(aggregate_only(data)))) for name, data in records.items()}
    releases.mkdir(parents=True, exist_ok=True)
    try:
        directory.mkdir()
    except FileExistsError:
        raise ExperimentError("duplicate_identity") from None
    for name, data in safe.items():
        atomic_write_json(directory / (name + ".json"), data)
    return directory


class HostAdapter:
    """Native Windows host worker. Launch detached; SSH never owns its lifetime."""
    def __init__(self, manifest, bindings):
        if sys.platform != "win32":
            raise ExperimentError("run_requires_native_windows_detached_worker")
        self.lock_id = bindings["host_lock_id"]
        roots = [Path(bindings["roots"][arm]).absolute() for arm in ("baseline", "candidate")]
        for root in roots:
            if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (root, *root.parents)):
                raise ExperimentError("root_reparse_point")
            if root == Path.home() or root in Path.home().parents or root == ROOT or root in ROOT.parents:
                raise ExperimentError("unsafe_integration_root")
        self.layouts = {arm: Layout(Path(bindings["roots"][arm]).resolve(),
                                   load(ROOT / "profiles" / (manifest[arm]["profile_id"] + ".json")))
                        for arm in ("baseline", "candidate")}
        a, b = (self.layouts[k].root for k in ("baseline", "candidate"))
        if a == b or a in b.parents or b in a.parents or any(p.is_symlink() for p in (a, b)):
            raise ExperimentError("candidate_root_not_isolated")
        candidate = self.layouts["candidate"]
        if candidate.install_record.exists() and read_json(candidate.install_record).get("profile_fingerprint") != candidate.profile.fingerprint:
            raise ExperimentError("candidate_root_owned_by_another_profile")
        self.scrubber = Scrubber(str(a), private=[str(b), self.lock_id], denylist=private_denylist())
        self.disk_floor = manifest["stop_conditions"]["disk_floor_gib"]
        self.disk_floors = {"baseline": self.layouts["baseline"].profile.data["host"]["min_free_disk_gib"],
                            "candidate": self.disk_floor}
        self.ram_floor = max(layout.profile.data["host"]["min_available_ram_gib_at_start"]
                             for layout in self.layouts.values())

    def quiesce(self, manifest, timeout):
        """Explicit warm handoff under run's physical claim; external serving must already be fenced/drained."""
        layout = self.layouts["baseline"]
        record = read_json(layout.install_record)
        if record.get("profile_fingerprint") != manifest["restoration_target"]["profile_fingerprint"]:
            raise ExperimentError("warm_incumbent_identity_mismatch")
        self.guard("baseline", timeout)
        self.restoration_runtime_identity = record["runtime_identity_sha256"]
        self.stop("baseline", timeout)
        return {"mode": "loop_quiesced_warm", "profile_id": layout.profile.id,
                "profile_fingerprint": layout.profile.fingerprint,
                "runtime_identity_sha256": self.restoration_runtime_identity,
                "cold_load_and_transcript_replay_required": True}

    def settle(self, timeout, *, clock=time.monotonic, sleep=time.sleep):
        started = clock()
        budget = min(90, timeout)
        observations = []
        while True:
            available = procs.memory()["available"] / (1 << 30)
            elapsed = clock() - started
            ready = available >= self.ram_floor
            observations.append({"elapsed_s": round(elapsed, 3), "ram_available_gib": available,
                                 "ram_above_floor": ready})
            if ready or elapsed >= budget:
                return {"status": "ready" if ready else "below_floor", "budget_s": budget,
                        "ram_floor_gib": self.ram_floor, "poll_interval_s": 5, "observations": observations}
            sleep(min(5, budget - elapsed))

    def precondition(self, manifest, timeout):
        import shutil
        a, b = (self.layouts[k] for k in ("baseline", "candidate"))
        doctors = [lifecycle.doctor(layout) for layout in (a, b)]
        gpu = lifecycle.gpu_facts(0)
        memory = procs.memory()
        ram = max(layout.profile.data["host"]["min_available_ram_gib_at_start"] for layout in (a, b))
        disks = {arm: {"available_gib": shutil.disk_usage(layout.root).free / (1 << 30),
                       "floor_gib": self.disk_floors[arm]} for arm, layout in self.layouts.items()}
        disk = min(row["available_gib"] for row in disks.values())
        record = read_json(a.install_record) if a.install_record.exists() else {}
        display = bool(a.profile.data["host"].get("display_attached", False))
        busy = lifecycle.gpu_busy(gpu, display)
        return {"timestamp_utc": utc_now(), "reachable": True, "doctor_ok": all(d["ok"] for d in doctors),
                "doctor_checks": [[{"check": c["check"], "ok": c["ok"]} for c in d["checks"]] for d in doctors],
                "gpu_idle": bool(gpu.get("available")) and busy is None,
                "gpu_model": gpu.get("name"), "gpu_memory_total_mib": gpu.get("memory_total_mib"),
                "gpu_memory_used_mib": gpu.get("memory_used_mib"),
                "gpu_processes": gpu.get("processes"), "display_attached": display,
                "ram_available_gib": memory["available"] / (1 << 30), "ram_floor_gib": ram,
                "ram_above_floor": memory["available"] / (1 << 30) >= ram,
                "disk_available_gib": disk, "disk_floor_gib": self.disk_floor,
                "disk_above_floor": all(row["available_gib"] >= row["floor_gib"] for row in disks.values()),
                "disk_by_arm": disks,
                "no_competing_tenant": gpu.get("available") is True and busy is None
                    and not lifecycle.port_in_use("127.0.0.1", a.profile.data["server"]["port"]),
                "predecessor_matches": record.get("profile_fingerprint") == manifest["baseline"]["profile_fingerprint"]}

    def command(self, arm, script, args, timeout, *, monitor=False):
        layout = self.layouts[arm]
        private = layout.root / "evidence" / "experiments"
        private.mkdir(parents=True, exist_ok=True)
        prefix = private / str(time.time_ns())
        argv = [sys.executable, str(ROOT / "scripts" / script), *args,
                "--profile", str(layout.profile.path), "--root", str(layout.root)]
        # Child files are private, bounded by the same timeout; no raw exception reaches releases.
        with prefix.with_suffix(".out").open("wb") as out, prefix.with_suffix(".err").open("wb") as err:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
            end = time.monotonic() + timeout
            try:
                while child.poll() is None:
                    left = end - time.monotonic()
                    if left <= 0:
                        raise ExperimentError("max_wall_time")
                    if monitor:
                        self.guard(arm, left)
                    try:
                        child.wait(timeout=min(2, left))
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                if child.poll() is None:
                    # Owned child tree only, including install's setup children. Lifecycle's detached
                    # server is stopped separately by restore, not by this kill.
                    subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    child.wait(timeout=30)
        result = last_object(prefix.with_suffix(".out").read_text(encoding="utf-8", errors="replace"))
        if child.returncode and not (script == "perf_probe.py" and result.get("status") == "error"):
            raise ExperimentError("child_failed")
        return result

    def install(self, manifest, timeout):
        started = time.monotonic()
        self.command("candidate", "omp_strata.py", ["install"], timeout)
        self.command("candidate", "omp_strata.py", ["keygen"], max(1, timeout - (time.monotonic() - started)))

    def start(self, arm, timeout):
        return self.command(arm, "omp_strata.py", ["start", "--timeout", str(max(1, int(timeout)))], timeout)

    def stop(self, arm, timeout):
        return self.command(arm, "omp_strata.py", ["stop"], timeout)

    def guard(self, arm, timeout):
        import shutil
        layout = self.layouts[arm]
        if shutil.disk_usage(layout.root).free / (1 << 30) < self.disk_floors[arm]:
            raise ExperimentError("disk_floor")
        if lifecycle.status(layout).get("state") != "healthy":
            raise ExperimentError("runtime_identity_lost")
        owned = {p.pid for p in lifecycle.running(layout).values()}
        gpu = lifecycle.gpu_facts(0)
        display = bool(layout.profile.data["host"].get("display_attached", False))
        processes = gpu.get("processes") or []
        if (not gpu.get("available") or not any(p["pid"] in owned for p in processes)
                or any(p["pid"] not in owned and not (display and p["type"] in ("G", "C+G"))
                       for p in processes)):
            raise ExperimentError("competing_tenant_or_gpu_unavailable")

    def probe(self, arm, workload, timeout):
        return self.command(arm, "perf_probe.py", ["--depths", ",".join(map(str, workload["depths"])),
            "--warm-depth", str(workload["warm_depth"]), "--max-tokens", str(workload["max_tokens"]),
            "--timeout", str(min(timeout, workload["request_timeout_s"]))], timeout, monitor=True)

    def restore(self, manifest):
        stops = []
        for arm in ("candidate", "baseline"):
            try:
                self.stop(arm, 120)
                stops.append({"arm": arm, "stopped": True})
            except Exception:
                stops.append({"arm": arm, "stopped": False})
        # start's own GPU/RAM/port admission refuses foreign occupancy; never kill a foreign owner.
        self.start("baseline", 900)
        gate = self.command("baseline", "realhost_gates.py", ["g10"], 300)
        healthy = lifecycle.status(self.layouts["baseline"]).get("state") == "healthy"
        record = read_json(self.layouts["baseline"].install_record)
        expected_runtime = getattr(self, "restoration_runtime_identity", None)
        identity_matches = (record.get("profile_fingerprint") == manifest["restoration_target"]["profile_fingerprint"]
                            and (expected_runtime is None or record.get("runtime_identity_sha256") == expected_runtime))
        serving = healthy and gate.get("pass_observed") is True and identity_matches
        return {"status": "restored" if serving else "failed", "serving": serving,
                "profile_id": manifest["restoration_target"]["profile_id"],
                "profile_fingerprint": manifest["restoration_target"]["profile_fingerprint"],
                "runtime_identity_sha256": record.get("runtime_identity_sha256"),
                "installed_identity_matches": identity_matches,
                "stops": stops, "gate": {k: gate.get(k) for k in ("gate", "run_id", "pass_observed")},
                "state": "healthy" if healthy else "unhealthy"}


def report(directory, *, engine_only=False):
    manifest = read_json(directory / "manifest.json")
    a, b = manifest["baseline"], manifest["candidate"]
    changed = [k for k in ("source", "model", "quantization", "template", "protocol", "engine", "harness", "config") if a[k] != b[k]]
    confounders = [k for k in changed if k not in ("engine", "source")]
    if engine_only and confounders:
        raise ExperimentError("engine_only_claim_refused")
    measured = read_json(directory / "measurements.json")
    restoration = read_json(directory / "restoration.json")
    failures = json.loads((directory / "failures.json").read_text())
    return {"key": experiment_key(manifest), "identity": identity_key(manifest),
            "status": measured["status"], "changed": changed,
            "engine_only_comparison": not confounders and "engine" in changed,
            "recommendation": "hold", "reason": "performance alone cannot establish task quality or justify adoption",
            "next_action": "resolve preconditions before another authorized trial" if measured["status"] == "blocked"
                           else "pair task quality, failures and latency before considering adoption",
            "wall_time_s": measured["wall_time_s"],
            "completed_repetitions": {arm: sum(row["result"].get("status") == "complete" for row in measured[arm])
                                      for arm in ("baseline", "candidate")},
            "baseline_source_experiment": measured.get("baseline_source_experiment"),
            "incumbent_handoff": measured.get("incumbent_handoff"),
            "cold_load": measured.get("cold_load", []),
            "restoration_wall_time_s": measured.get("restoration_wall_time_s"),
            "failures": len(failures), "restoration": restoration,
            "unavailable": ["task quality (perf_probe does not score correctness)", "true inter-token latency"]}


def propose_next(directory, candidate, *, releases=RELEASES):
    prior = read_json(directory / "manifest.json")
    result = report(directory)
    manifest = new_manifest(prior["baseline"]["profile_id"], candidate,
                            repetitions=prior["repetitions"],
                            rationale="Proposed only: " + result["next_action"] + "; compare the explicitly selected pinned alternative.")
    key = validate(manifest, releases=releases)
    queue = {"schema_version": 1, "automatic_execution": False,
             "based_on": experiment_key(prior), "trials": [{"key": key, "manifest": manifest}]}
    public_write(releases / "queue.json", queue, Scrubber("<private-root>", denylist=private_denylist()))
    return queue


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--manifest", type=Path)
    plan.add_argument("--baseline")
    plan.add_argument("--candidate")
    plan.add_argument("--rationale")
    plan.add_argument("--repetitions", type=int, default=3)
    plan.add_argument("--host-profile", choices=HOST_PROFILES)
    plan.add_argument("--retry-of", help="Receipt key of a matching blocked or successfully restored failed trial")
    plan.add_argument("--resume-candidate", action="store_true",
                      help="Reuse a restored failed trial's complete baseline, with explicit provenance")
    plan.add_argument("--out", type=Path)
    execute = sub.add_parser("run")
    execute.add_argument("--manifest", required=True, type=Path)
    execute.add_argument("--bindings", required=True, type=Path)
    execute.add_argument("--quiesce-incumbent", action="store_true",
                         help="Stop the verified warm baseline only under the host claim; serving must be fenced/drained")
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--manifest", required=True, type=Path)
    preflight.add_argument("--bindings", required=True, type=Path)
    blocked = sub.add_parser("record-blocked")
    blocked.add_argument("--manifest", required=True, type=Path)
    blocked.add_argument("--observation", required=True, type=Path)
    for name in ("report", "next"):
        command = sub.add_parser(name)
        command.add_argument("--directory", required=True, type=Path)
        if name == "report":
            command.add_argument("--engine-only", action="store_true")
        else:
            command.add_argument("--candidate", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            if not args.manifest and not all((args.baseline, args.candidate, args.rationale)):
                parser.error("plan requires --manifest or --baseline, --candidate and --rationale")
            manifest = read_json(args.manifest) if args.manifest else new_manifest(
                args.baseline, args.candidate, repetitions=args.repetitions, rationale=args.rationale,
                host_profile=args.host_profile, retry_of=args.retry_of, resume_candidate=args.resume_candidate)
            if args.manifest and (args.host_profile or args.retry_of or args.resume_candidate):
                parser.error("--host-profile, --retry-of and --resume-candidate require profile-based planning")
            key = validate(manifest)
            if args.out:
                if args.out.exists():
                    raise ExperimentError("plan_output_exists")
                public_write(args.out, manifest, Scrubber("<private-root>", denylist=private_denylist()))
            result = {"key": key, "manifest": manifest}
        elif args.command == "preflight":
            manifest = read_json(args.manifest)
            validate(manifest, dedupe=False)
            started = time.monotonic()
            result = HostAdapter(manifest, read_json(args.bindings)).precondition(manifest, 120)
            result["wall_time_s"] = round(time.monotonic() - started, 3)
        elif args.command == "run":
            manifest = read_json(args.manifest)
            validate(manifest)
            directory = run(manifest, HostAdapter(manifest, read_json(args.bindings)),
                            quiesce_incumbent=args.quiesce_incumbent)
            result = report(directory)
        elif args.command == "record-blocked":
            result = report(record_blocked(read_json(args.manifest), read_json(args.observation)))
        elif args.command == "report":
            result = report(args.directory, engine_only=args.engine_only)
        else:
            result = propose_next(args.directory, args.candidate)
        print(json.dumps(result, indent=2, allow_nan=False))
        return int(args.command == "run" and result["status"] != "complete")
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc) if isinstance(exc, ExperimentError) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
