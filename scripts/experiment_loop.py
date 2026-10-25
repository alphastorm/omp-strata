#!/usr/bin/env python3
"""Frozen, comparison-only experiments; run on the GPU host through launch-detached.ps1.

Private bindings: {"roots": {"baseline": "...", "candidate": "..."},
"host_lock_id": "..."}. Use the SAME lock id as eval_taskset on this machine.
The candidate must have its own root. No defaults change and no real work is routed.
--quiesce-incumbent opts into a claimed warm-baseline stop after external serving fence/drain.
Failed restoration retains the physical claim for operator reconciliation, never stale-lock takeover.
Only aggregate perf_probe output is public; raw child output stays in the host root.
A performance-only experiment can recommend more evaluation, never adoption.

Unattended runs require --claim, a trusted carrythrough.fleet-claim.v1 document
delivered by the controller (not a self-issued permission or a signed token).
Use --unattended to fail closed if an automation command omits --claim. The
attended proposal queue keeps automatic_execution:false. Plan --restoration-ref
to freeze the claim's incumbent profile, which need not be the baseline arm.
Claims bind the exact manifest FILE bytes, not a reserialized JSON digest.
Private bindings additionally require host, resource_id, host_role and
roots.restoration_target. These are operator-installed host identity bindings,
not values copied from an incoming claim. All controllers must use the same
host_lock_id; the on-host mutex is NOT the cross-controller fleet lease.
Warm handoff additionally requires bindings.warm_incumbent: the installed runtime
identity and exact requested_utc/profile_fingerprint/wrapper/server run generation.
No current process is adopted merely because its profile/root looks familiar.

--evidence-dir must be private, outside releases/. A claim writes
<evidence-dir>/<claim_id>/<experiment-key>/ plus sibling usage.json. Nothing is
published or promoted. Candidate roots remain distinct from baseline/incumbent
roots. Claims are consumed once in HOST_LOCKS/claims/<claim_id>.json even if
the evidence destination changes. Never delete a failed-restoration lock or
replay a consumed claim; the controller/operator must reconcile the retained
evidence and incumbent first. The mutex records persistent_hold:true so the
evaluator cannot reclaim it merely because the worker PID exited. Only verified G10 serving restoration permits
normal unlock after mutation. Cleanup has its own bounded safety budget even
after claim expiry; gpu_seconds conservatively includes trial and restoration
wall time, not sampled GPU utilization. Unmutated refusals report aborted, zero
GPU seconds and unverified restoration; they cannot release the fleet lease.

Ownership: child trees are identified by this worker's Popen handles; detached
servers and pending requests are tracked from this worker's start dispatch,
by its launch marker, exact run.json token and wrapper/server identities. Stop
checks that generation under lifecycle's root lock; lifecycle additionally
checks PID, creation time and executable before terminating a recorded tree.
An identity-less request is cancelled under that lock before restoration can
release custody; a delayed detached wrapper cannot turn a stopped request into a
server. Probe attempts are saved before guard/probe effects, including interrupted
attempts with no result. Such a candidate cannot use baseline-only resume.
Owned cleanup/capture waits boundedly for the wrapper's root lock; ordinary
admission remains non-blocking. Failed command-tree termination retains its
Popen ownership and prevents a successful stop even before run.json exists.
An unpublished child with a dead parent, failed tree kill or unknown lifetime
requires explicit reconciliation: neither stop nor a new start may erase it.
Unbound pre-existing or replaced generations are never stopped. An explicit warm
handoff adopts only its operator-bound generation under the same root lock. Unrelated incumbent
tenants must be released/restored by their controller: this adapter restores
only the explicitly bound, installed Strata profile and never evicts a tenant.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import runpy
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omp_strata import lifecycle, procs
from omp_strata.common import atomic_write_bytes, atomic_write_json, sha256_file, utc_now
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
                 "omp_strata/layout.py", "omp_strata/cli.py", "schemas/experiment-manifest.schema.json")
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
                 resume_candidate=False, restoration_ref=None):
    a, b = freeze_arm(baseline), freeze_arm(candidate)
    role = host_profile or next(role for role, gpu in HOST_PROFILES.items() if gpu == a["config"]["host"]["gpu_model"])
    manifest = {"schema_version": 1, "host_role": role, "rationale": rationale,
            "baseline": a, "candidate": b,
            "restoration_target": freeze_arm(restoration_ref) if restoration_ref else a,
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
    if "probe_attempts" in measured and (
            not isinstance(measured["probe_attempts"], list)
            or any(not isinstance(row, dict) or row.get("arm") not in ("baseline", "candidate")
                   or type(row.get("repetition")) is not int for row in measured["probe_attempts"])):
        raise ExperimentError("retry_receipt_malformed")
    return prior, measured, restored


def validate(manifest, *, releases=RELEASES, dedupe=True, restoration_ref=None):
    errors = schema_errors(manifest, read_json(ROOT / "schemas/experiment-manifest.schema.json"))
    if errors:
        raise ExperimentError("invalid_manifest_schema")
    for name in ("baseline", "candidate", "restoration_target"):
        if manifest[name] != freeze_arm(manifest[name]["profile_id"]):
            raise ExperimentError("frozen_profile_drift")
        if manifest[name]["config"]["host"]["gpu_model"] != HOST_PROFILES[manifest["host_role"]]:
            raise ExperimentError("host_profile_mismatch")
    if restoration_ref is not None and manifest["restoration_target"]["profile_id"] != restoration_ref:
        raise ExperimentError("claim_restoration_mismatch")
    if restoration_ref is None and manifest["restoration_target"] != manifest["baseline"]:
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
                or "probe_attempts" not in measured
                or any(row["arm"] == "candidate" for row in measured.get("probe_attempts", []))
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


def parse_manifest_bytes(raw):
    """Parse the same bytes that the claim hashes, rejecting duplicate keys."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ExperimentError("invalid_manifest_json")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (TypeError, ValueError):
        raise ExperimentError("invalid_manifest_json") from None


def claim_time(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)", value):
        raise ExperimentError("invalid_claim_timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ExperimentError("invalid_claim_timestamp") from None


def validate_claim(claim, manifest, raw, bindings, *, now=None):
    schema = read_json(ROOT / "schemas/experiment-manifest.schema.json")
    if schema_errors(manifest, schema):
        raise ExperimentError("invalid_manifest_schema")
    if schema_errors(claim, schema["$defs"]["fleetClaim"]):
        raise ExperimentError("invalid_claim_schema")
    if any(isinstance(v, str) and (len(v) > 512 or v != v.strip()) for v in claim.values()):
        raise ExperimentError("invalid_claim_field")
    if claim["repetitions"] > 100 or claim["max_seconds"] > 86400:
        raise ExperimentError("invalid_claim_limit")
    now = now or datetime.now(timezone.utc)
    acquired, expires = (claim_time(claim[k]) for k in ("acquired_at", "expires_at"))
    if acquired > now or expires <= acquired or expires <= now:
        raise ExperimentError("claim_expired_or_not_acquired")
    if not isinstance(bindings, dict) or any(
            bindings.get(k) != claim[k] for k in ("host", "resource_id")):
        raise ExperimentError("claim_host_resource_mismatch")
    if bindings.get("host_role") != manifest["host_role"]:
        raise ExperimentError("claim_host_profile_mismatch")
    if claim["variant_id"] != manifest["candidate"]["profile_id"]:
        raise ExperimentError("claim_variant_mismatch")
    if (manifest["repetitions"] > claim["repetitions"]
            or manifest["stop_conditions"]["max_wall_time_s"] > claim["max_seconds"]):
        raise ExperimentError("claim_budget_exceeded")
    if not isinstance(raw, bytes) or sha256(raw) != claim["trial_manifest_sha256"]:
        raise ExperimentError("claim_manifest_hash_mismatch")
    if parse_manifest_bytes(raw) != manifest:
        raise ExperimentError("claim_manifest_content_mismatch")
    if manifest["restoration_target"]["profile_id"] != claim["restoration_ref"]:
        raise ExperimentError("claim_restoration_mismatch")
    return expires


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
    owner = {"pid": os.getpid(), "utc": utc_now(), "persistent_hold": True}
    lease = {"release": False}
    try:
        with stream:
            json.dump(owner, stream)
        yield lease
    finally:
        if lease["release"] and path.exists() and read_json(path) == owner:
            path.unlink()


ADMISSION_FLAGS = ("reachable", "gpu_idle", "ram_above_floor", "disk_above_floor", "no_competing_tenant",
                   "predecessor_matches", "doctor_ok")


def check_preconditions(observation):
    failures = [name for name in ADMISSION_FLAGS if observation.get(name) is not True]
    if failures:
        raise ExperimentError("precondition:" + ",".join(failures))


def run(manifest, adapter, *, releases=RELEASES, lock_directory=HOST_LOCKS, clock=time.monotonic,
        claim=None, bindings=None, manifest_bytes=None, unattended=False, quiesce_incumbent=False):
    if unattended and claim is None:
        raise ExperimentError("claim_required")
    expires = None
    if claim is not None:
        expires = validate_claim(claim, manifest, manifest_bytes, bindings)
        if (releases.resolve() == (ROOT / "releases").resolve()
                or (ROOT / "releases").resolve() in releases.resolve().parents):
            raise ExperimentError("claim_requires_private_evidence")
    key = validate(manifest, releases=releases, dedupe=claim is None,
                   restoration_ref=claim["restoration_ref"] if claim else None)
    parent = releases / claim["claim_id"] if claim else releases
    if claim:
        parent.mkdir(parents=True, exist_ok=False)
    directory = parent / key
    directory.mkdir(parents=True, exist_ok=False)
    started = clock()
    mutation_started = None
    deadline = started + manifest["stop_conditions"]["max_wall_time_s"]
    if expires:
        deadline = min(deadline, started + (expires - datetime.now(timezone.utc)).total_seconds())
    measurements = {"status": "running", "started_utc": utc_now(), "preconditions": [], "baseline": [], "candidate": [],
                    "planned_repetitions": {arm: manifest["repetitions"] for arm in ("baseline", "candidate")},
                    "probe_attempts": []}
    failures = []
    restoration = {"status": "not_required", "reason": "no_lifecycle_mutation", "serving": None}
    mutated = False
    aborted = False

    def restored():
        return (restoration.get("status") == "restored" and restoration.get("serving") is True
                and (not claim or (restoration.get("profile_id") == claim["restoration_ref"]
                     and restoration.get("gate", {}).get("gate", "").lower() == "g10"
                     and restoration.get("gate", {}).get("pass_observed") is True)))

    def save():
        measurements["wall_time_s"] = round(clock() - started, 3)
        for name, data in (("manifest", manifest), ("measurements", measurements), ("failures", failures),
                           ("restoration", restoration)):
            path = directory / (name + ".json")
            if claim:
                if name == "manifest":
                    atomic_write_bytes(path, manifest_bytes)
                else:
                    atomic_write_json(path, aggregate_only(data))
            else:
                public_write(path, data, adapter.scrubber)

    def save_usage():
        if claim:
            outcome = ("failed" if mutated and not restored() else
                       "aborted" if aborted or not mutated else
                       "passed" if measurements["status"] == "complete" else "failed")
            atomic_write_json(parent / "usage.json", {
                "schema_version": "carrythrough.fleet-usage.v1", "claim_id": claim["claim_id"],
                "started_at": measurements["started_utc"], "ended_at": utc_now(),
                "gpu_seconds": max(0, clock() - mutation_started) if mutation_started is not None else 0,
                "outcome": outcome,
                "restoration": {"verified": restored(), "incumbent_ref": claim["restoration_ref"],
                                "evidence_sha256": sha256_file(directory / "restoration.json")},
                "evidence_paths": [f"{key}/{name}.json" for name in
                                   ("manifest", "measurements", "failures", "restoration")]})

    def remaining():
        value = deadline - clock()
        if value <= 0 or (expires and datetime.now(timezone.utc) >= expires):
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
        # Exit the physical claim before releasing the restoration receipt's lifecycle lock.
        with contextlib.ExitStack() as custody, host_lock(adapter.lock_id, lock_directory) as lease:
            try:
                if claim:
                    if adapter.lock_id != bindings.get("host_lock_id"):
                        raise ExperimentError("claim_host_lock_mismatch")
                    validate_claim(claim, manifest, manifest_bytes, bindings)
                    claims = lock_directory / "claims"
                    claims.mkdir(exist_ok=True)
                    try:
                        with (claims / (claim["claim_id"] + ".json")).open("x", encoding="utf-8") as stream:
                            json.dump(claim, stream)
                    except FileExistsError:
                        raise ExperimentError("claim_already_consumed") from None
                if quiesce_incumbent:
                    # The stop is covered by this physical lease and by restoration even if it raises.
                    mutated = True
                    mutation_started = clock()
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
                if mutation_started is None:
                    mutation_started = clock()
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
                            attempt = {"arm": arm, "repetition": repetition + 1, "status": "dispatched"}
                            measurements["probe_attempts"].append(attempt)
                            save()
                            adapter.guard(arm, remaining())
                            result = adapter.probe(arm, manifest["workload"], remaining())
                            measurements[arm].append({"repetition": repetition + 1, "result": result})
                            attempt["status"] = result.get("status", "error")
                            if result.get("status") != "complete":
                                raise ExperimentError("probe_failed")
                        except ExperimentError as exc:
                            attempt["status"] = "failed"
                            aborted = aborted or str(exc) == "max_wall_time"
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
                aborted = aborted or isinstance(exc, KeyboardInterrupt) or reason == "max_wall_time"
                failures.append({"reason": reason})
                measurements["status"] = "failed" if mutated else "blocked"
            finally:
                if mutated:
                    restore_started = clock()
                    try:
                        restoration = adapter.restore(manifest, custody=custody)
                        if not restored():
                            measurements["status"] = "restoration_failed"
                    except (Exception, KeyboardInterrupt) as exc:
                        restoration = {"status": "failed", "serving": False, "reason": type(exc).__name__}
                        measurements["status"] = "restoration_failed"
                    measurements["restoration_wall_time_s"] = round(clock() - restore_started, 3)
                save()
                save_usage()
                lease["release"] = not mutated or restored()
    except ExperimentError as exc:
        measurements["status"] = "blocked"
        failures.append({"reason": str(exc)})
        save()
        save_usage()
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
    def __init__(self, manifest, bindings, *, claim=None):
        if sys.platform != "win32":
            raise ExperimentError("run_requires_native_windows_detached_worker")
        self.lock_id = bindings["host_lock_id"]
        arms = ("baseline", "candidate", "restoration_target") if claim else ("baseline", "candidate")
        if not isinstance(bindings.get("roots"), dict) or any(
                not isinstance(bindings["roots"].get(arm), str) or not bindings["roots"][arm].strip()
                for arm in arms):
            raise ExperimentError("missing_integration_root")
        roots = [Path(bindings["roots"][arm]).absolute() for arm in arms]
        home = Path.home().resolve()
        for root in roots:
            if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (root, *root.parents)):
                raise ExperimentError("root_reparse_point")
            root = root.resolve()
            if (root.parent == root or root == home or root in home.parents or root == ROOT or ROOT in root.parents
                    or root in ROOT.parents and ROOT != root / "tooling"):
                raise ExperimentError("unsafe_integration_root")
        self.layouts = {arm: Layout(Path(bindings["roots"][arm]).resolve(),
                                   load(ROOT / "profiles" / (manifest[arm]["profile_id"] + ".json")))
                        for arm in arms}
        if not claim:
            self.layouts["restoration_target"] = self.layouts["baseline"]
        a, b = (self.layouts[k].root for k in ("baseline", "candidate"))
        if a == b or a in b.parents or b in a.parents or any(p.is_symlink() for p in (a, b)):
            raise ExperimentError("candidate_root_not_isolated")
        candidate = self.layouts["candidate"]
        if candidate.install_record.exists() and read_json(candidate.install_record).get("profile_fingerprint") != candidate.profile.fingerprint:
            raise ExperimentError("candidate_root_owned_by_another_profile")
        incumbent = self.layouts["restoration_target"]
        c = incumbent.root
        if (c == b or c in b.parents or b in c.parents
                or c != a and (c in a.parents or a in c.parents)
                or c == a and incumbent.profile.fingerprint != self.layouts["baseline"].profile.fingerprint):
            raise ExperimentError("incumbent_root_not_isolated")
        self.scrubber = Scrubber(str(a), private=[str(b), str(c), self.lock_id], denylist=private_denylist())
        self.owned_runs = {}
        self.launch_requests = {}
        self.launch_jobs = {}
        self.owned_commands = {}
        self.warm_incumbent = bindings.get("warm_incumbent")
        self.disk_floor = manifest["stop_conditions"]["disk_floor_gib"]
        self.disk_floors = {arm: self.disk_floor if arm == "candidate" else layout.profile.data["host"]["min_free_disk_gib"]
                            for arm, layout in self.layouts.items()}
        self.ram_floor = max(layout.profile.data["host"]["min_available_ram_gib_at_start"]
                             for layout in self.layouts.values())

    def process_census(self):
        # Null rows require explicit operator review in IncumbentArtifacts,
        # not the older process-name heuristic used by ordinary job cleanup.
        rows = lifecycle.ProcessJob.snapshot(complete=True, allow_null=True, observers=self.census_observers)
        self.latest_process_census = list(rows.values())
        if os.getpid() in rows:
            self.census_observers.append(rows[os.getpid()])
        return rows

    def port_census(self, ports):
        return lifecycle.incumbent_port_owners(ports)

    def verify_incumbent_artifacts(self, artifacts, legacy, *, allow_legacy=False):
        """No ancestry guess: every reference is job-contained, explicitly legacy, or refused."""
        jobs = tuple(self.launch_jobs.values())
        before = set().union(*(job.pids() for job in jobs))
        rows = self.process_census()
        owners = self.port_census(artifacts.ports)
        current = self.process_census()
        after = set().union(*(job.pids() for job in jobs))
        owned = before & after
        if os.getpid() not in rows or os.getpid() not in current:
            raise lifecycle.CensusRefusal("driver observer missing from census", [
                {"pid": os.getpid(), "references": ["missing_driver_observer"]}])
        changed = [{"pid": pid, "references": ["changed_census_identity"]}
                   for pid, row in current.items() if rows.get(pid) != row]
        if changed:
            raise lifecycle.CensusRefusal("artifact census changed during port observation", changed)
        allowed = owned | (set(legacy.rows) if allow_legacy else set())
        for snapshot in (rows, current):
            exonerated = artifacts.verify(snapshot, owners, allowed, observer_pid=os.getpid())
            legacy.reconcile(snapshot, owned=owned)
        return {"non_owned_references": 0, "process_snapshot": list(current.values()),
                "port_owners": {str(port): sorted(pids) for port, pids in owners.items()},
                "owned_job_pids": sorted(owned), "exonerated_null": exonerated,
                "observers": list(self.census_observers),
                "verified_utc": utc_now()}

    def quiesce(self, manifest, timeout):
        """Explicit warm handoff under run's physical claim; external serving must already be fenced/drained."""
        binding = self.warm_incumbent
        fields = ("requested_utc", "profile_fingerprint", "wrapper", "server")
        if (not isinstance(binding, dict) or not isinstance(binding.get("run"), dict)
                or set(binding["run"]) != set(fields) or not all(binding["run"].values())
                or not binding.get("runtime_identity_sha256")):
            raise ExperimentError("warm_incumbent_binding_required")
        layout = self.layouts["restoration_target"]
        with lifecycle.FileLock(layout.lock_file):
            record = read_json(layout.install_record)
            current = read_json(layout.run_record)
            if (record.get("profile_fingerprint") != manifest["restoration_target"]["profile_fingerprint"]
                    or record.get("runtime_identity_sha256") != binding["runtime_identity_sha256"]
                    or any(current.get(key) != binding["run"][key] for key in fields)):
                raise ExperimentError("warm_incumbent_identity_mismatch")
            self.guard("restoration_target", timeout)
            if not current.get("tree_token"):
                raise ExperimentError("legacy_incumbent_requires_recustody")
            self.launch_jobs["restoration_target"] = lifecycle.ProcessJob(current["tree_token"], existing=True)
            self.restoration_runtime_identity = record["runtime_identity_sha256"]
            # Explicitly adopt ONLY the operator-bound generation, under the same lock stop checks.
            self.owned_runs["restoration_target"] = dict(binding["run"])
            self.stop("restoration_target", timeout, locked=True)
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
        incumbent = self.layouts["restoration_target"]
        doctors = [lifecycle.doctor(layout) for layout in (a, b, incumbent)]
        gpu = lifecycle.gpu_facts(0)
        memory = procs.memory()
        ram = max(layout.profile.data["host"]["min_available_ram_gib_at_start"] for layout in (a, b))
        disks = {arm: {"available_gib": shutil.disk_usage(layout.root).free / (1 << 30),
                       "floor_gib": self.disk_floors[arm]} for arm, layout in self.layouts.items()}
        disk = min(row["available_gib"] for row in disks.values())
        record = read_json(a.install_record) if a.install_record.exists() else {}
        restored_record = read_json(incumbent.install_record) if incumbent.install_record.exists() else {}
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
                "predecessor_matches": record.get("profile_fingerprint") == manifest["baseline"]["profile_fingerprint"]
                    and restored_record.get("profile_fingerprint") == manifest["restoration_target"]["profile_fingerprint"]}

    def command(self, arm, script, args, timeout, *, monitor=False, env=None):
        layout = self.layouts[arm]
        root = layout.root
        if root in self.owned_commands:
            raise ExperimentError("command_cleanup_unresolved")
        private = layout.root / "evidence" / "experiments"
        private.mkdir(parents=True, exist_ok=True)
        prefix = private / str(time.time_ns())
        argv = [sys.executable, str(ROOT / "scripts" / script), *args,
                "--profile", str(layout.profile.path), "--root", str(layout.root)]
        # Child files are private, bounded by the same timeout; no raw exception reaches releases.
        with prefix.with_suffix(".out").open("wb") as out, prefix.with_suffix(".err").open("wb") as err:
            owned = self.owned_commands[root] = {"child": None, "job": None}
            launching = script == "omp_strata.py" and args[0] == "start"
            job = owned["job"] = (self.launch_jobs[arm] if launching
                                  else lifecycle.ProcessJob(os.urandom(16).hex()))
            child = job.spawn(argv, stdout=out, stderr=err, env={**os.environ, **(env or {})})
            owned["child"] = child
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
                    try:
                        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       timeout=30, check=True)
                    finally:
                        if not launching:
                            job.stop(30)
                        child.wait(timeout=30)
                        del self.owned_commands[root]
                else:
                    # All exit codes have the same mechanical tree proof. Structured
                    # probe errors consume their budget, not an unbounded custody hold.
                    if not launching:
                        job.stop(30)
                    del self.owned_commands[root]
        result = last_object(prefix.with_suffix(".out").read_text(encoding="utf-8", errors="replace"))
        if child.returncode and not (script == "perf_probe.py" and result.get("status") == "error"):
            raise ExperimentError("child_failed")
        return result

    def install(self, manifest, timeout):
        started = time.monotonic()
        self.command("candidate", "omp_strata.py", ["install"], timeout)
        self.command("candidate", "omp_strata.py", ["keygen"], max(1, timeout - (time.monotonic() - started)))

    def start(self, arm, timeout):
        layout = self.layouts[arm]
        if layout.root in self.owned_commands:
            raise ExperimentError("command_cleanup_unresolved")
        if arm in self.launch_requests or arm in self.launch_jobs:
            raise ExperimentError("launch_cleanup_unresolved")
        if lifecycle.running(layout):
            raise ExperimentError("root_already_running")
        launch_id = os.urandom(16).hex()
        # Keep responsibility even if the command is killed or the first capture
        # cannot acquire the wrapper's lock. No process identity is inferred here.
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

    def stop(self, arm, timeout, *, locked=False):
        owned = self.owned_runs.get(arm)
        request = self.launch_requests.get(arm)
        layout = self.layouts[arm]
        # Check and stop under the SAME root lock: a concurrent restart cannot
        # replace run.json between our generation check and lifecycle's stop.
        with contextlib.nullcontext() if locked else lifecycle.FileLock(layout.lock_file, timeout=timeout):
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
                # A refused start/foreign replacement is not ours to stop. Its
                # token also invalidates our old detached wrapper.
                if job:
                    job.stop(min(30, timeout))
                    finish_launch_command()
                    del self.launch_jobs[arm]
                del self.launch_requests[arm]
                if command_error:
                    raise ExperimentError("command_cleanup_unresolved") from command_error
                return {"state": "not_owned", "stopped": []}
            if owned is None and request is None:
                if command_error:
                    raise ExperimentError("command_cleanup_unresolved") from command_error
                return {"state": "not_owned", "stopped": []}
            if owned is not None and any(current.get(k) != v for k, v in owned.items()):
                raise ExperimentError("owned_generation_changed")
            private = layout.root / "evidence" / "experiments"
            private.mkdir(parents=True, exist_ok=True)
            with (private / (str(time.time_ns()) + "-stop.log")).open("w", encoding="utf-8") as log:
                result = lifecycle.stop(layout, log=lambda line: log.write(line + "\n"), locked=True, job=job)
            # A request may fail before run.json exists. Its empty native job still
            # requires independent verification and closure.
            if job and job.handle:
                job.stop(min(30, timeout))
            finish_launch_command()
            self.launch_jobs.pop(arm, None)
            self.owned_runs.pop(arm, None)
            self.launch_requests.pop(arm, None)
            if command_error:
                raise ExperimentError("command_cleanup_unresolved") from command_error
            return result

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

    def restore(self, manifest, *, custody):
        with contextlib.ExitStack() as pending_custody:
            try:
                result = HostAdapter._restore(self, manifest, custody=pending_custody)
                if result["serving"]:
                    custody.enter_context(pending_custody.pop_all())
                    return result
            except (Exception, KeyboardInterrupt):
                pending_custody.close()
                self.stop("restoration_target", 120)
                raise
            pending_custody.close()
            self.stop("restoration_target", 120)
            return result

    def _restore(self, manifest, *, custody):
        stops = []
        for arm in ("candidate", "baseline"):
            try:
                self.stop(arm, 120)
                stops.append({"arm": arm, "stopped": True})
            except Exception:
                stops.append({"arm": arm, "stopped": False})
        # start's own GPU/RAM/port admission refuses foreign occupancy; never kill a foreign owner.
        self.start("restoration_target", 900)
        gate = self.command("restoration_target", "realhost_gates.py", ["g10"], 300)
        target = self.layouts["restoration_target"]
        expected_runtime = getattr(self, "restoration_runtime_identity", None)
        record, identity_matches = {}, None
        # Caller retains this lock through evidence/usage publication AND physical claim release.
        custody.enter_context(lifecycle.FileLock(target.lock_file, timeout=120))
        owned = self.owned_runs.get("restoration_target")
        current = read_json(target.run_record)
        if not owned or any(current.get(key) != value for key, value in owned.items()):
            raise ExperimentError("owned_generation_changed")
        if current.get("state") != "ready":
            raise ExperimentError("restoration_not_ready")
        healthy = lifecycle.status(target).get("state") == "healthy"
        current = read_json(target.run_record)
        if any(current.get(key) != value for key, value in owned.items()):
            raise ExperimentError("owned_generation_changed")
        if current.get("state") != "ready":
            raise ExperimentError("restoration_not_ready")
        if expected_runtime is not None:
            record = read_json(target.install_record)
            identity_matches = (record.get("profile_fingerprint") == manifest["restoration_target"]["profile_fingerprint"]
                                and record.get("runtime_identity_sha256") == expected_runtime)
        serving = (healthy and gate.get("pass_observed") is True and all(stop["stopped"] for stop in stops)
                   and identity_matches is not False)
        if serving:
            runtime = current.get("runtime_identity_sha256")
            if (gate.get("gate") != "G10"
                    or not re.fullmatch(r"g10-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}", str(gate.get("run_id", "")))
                    or not re.fullmatch(r"[0-9a-f]{64}", str(runtime))
                    or gate.get("profile_fingerprint") != current["profile_fingerprint"]
                    or gate.get("runtime_identity_sha256") != runtime):
                raise ExperimentError("restoration_g10_identity_mismatch")
            self.launch_jobs["restoration_target"].handoff(current["wrapper"])
            # Written by this restoration step, not by a private adoption-receipt formatter.
            atomic_write_json(target.run_record.with_name("g10.json"), {
                "schema_version": 1, "gate": "G10", "g10_run_id": gate["run_id"],
                "pass_observed": True, "utc": utc_now(), "run": owned,
                "profile_fingerprint": current["profile_fingerprint"],
                "runtime_identity_sha256": runtime})
        return {"status": "restored" if serving else "failed", "serving": serving,
                "profile_id": manifest["restoration_target"]["profile_id"],
                "profile_fingerprint": manifest["restoration_target"]["profile_fingerprint"],
                "runtime_identity_sha256": record.get("runtime_identity_sha256"),
                "installed_identity_matches": identity_matches,
                "stops": stops, "gate": {k: gate.get(k) for k in ("gate", "run_id", "pass_observed")},
                "state": "healthy" if healthy else "unhealthy"}


def verify_legacy_release(adapter, artifacts, legacy):
    """One-time physical cutover proof; never generalizes legacy PID custody into a job proof."""
    layout = adapter.layouts["restoration_target"]
    srv = layout.profile.data["server"]
    if lifecycle.port_in_use(srv["listen_host"], srv["port"]) or lifecycle.running(layout):
        raise ExperimentError("legacy_process_or_port_survives")
    gpu = lifecycle.gpu_facts(layout.profile.data["host"]["gpu_index"])
    memory = gpu.get("memory_used_mib")
    if (gpu.get("available") is not True or type(memory) not in (int, float)
            or not math.isfinite(memory) or memory < 0 or memory >= lifecycle.GPU_IDLE_MIB
            or lifecycle.gpu_busy(gpu, bool(layout.profile.data["host"].get("display_attached", False))) is not None):
        raise ExperimentError("legacy_vram_release_unverified")
    rows = legacy.verify_absent()
    return {"port_closed": True, "vram_released": True, "gpu_memory_used_mib": memory,
            "model_processes": 0, "process_snapshot_count": len(rows), "verified_utc": utc_now(),
            "artifact_custody": adapter.verify_incumbent_artifacts(artifacts, legacy)}


def load_fleet_controller(path, host):
    """Use the installed controller's existing mutex, bindings and adopt-restoration contract."""
    if sys.platform != "win32":
        raise ExperimentError("recustody_requires_native_windows")
    module = runpy.run_path(str(path.resolve(strict=True)), run_name="omp_strata_recustody_controller")
    return module["Controller"](module["Store"](module["PROGRAM"] / "state"),
                                module["HostAdapter"](module["host_binding"](host)))


def recustody_incumbent(manifest, adapter, control, *, host, generation, root, receipt,
                       manifest_bytes, go, lock_directory=HOST_LOCKS, exonerate_null=()):
    """Operator-only legacy stop -> physical proof -> ordinary restore -> controller adoption.

    The existing fleet mutex stays held and paused throughout; the ordinary host
    lease stays held on every post-stop failure. This executes no candidate arm,
    install, fetch or trial and cannot reopen fleet admission.
    """
    if not go:
        raise ExperimentError("recustody_requires_explicit_go")
    if not lifecycle.WINDOWS:
        raise ExperimentError("recustody_requires_native_windows")
    if parse_manifest_bytes(manifest_bytes) != manifest:
        raise ExperimentError("recustody_manifest_bytes_mismatch")
    layout = adapter.layouts["restoration_target"]
    root, receipt = Path(root).resolve(), Path(receipt).resolve()
    if (root != layout.root or control.adapter.kind != "strata"
            or control.adapter.layout.root.resolve() != root
            or control.adapter.layout.profile.fingerprint != layout.profile.fingerprint
            or manifest["restoration_target"]["profile_id"] != layout.profile.id):
        raise ExperimentError("recustody_incumbent_root_mismatch")
    if (not receipt.is_relative_to(root / "evidence") or receipt.is_relative_to(RELEASES.resolve())
            or receipt.exists() or receipt.with_suffix(".failure.json").exists()):
        raise ExperimentError("recustody_requires_new_private_receipt")
    with control.store.locked():
        state = control.store.read()
        if (state.get("host") != host or type(generation) is not int or state.get("generation") != generation
                or state.get("paused") is not True or state.get("reserved") is not False
                or state.get("admission_open") is not False or state.get("jobs") != {}
                or state.get("blockers") != [] or state.get("phase") != "Fleet"
                or "supervisor_transaction" in state or "recovery_hold" in state):
            raise ExperimentError("recustody_requires_idle_paused_fleet_generation")
        prior = (state.get("service") or {}).get("identity")
        active = control.adapter.active_requests().get("count")
        if (not prior or control.adapter.current() != prior or not control.adapter.ready()
                or type(active) is not int or active != 0):
            raise ExperimentError("recustody_incumbent_not_drained_or_bound")
        mutated = False
        proof = None
        before_artifacts = None
        adapter.census_observers = []
        adapter.latest_process_census = []
        with contextlib.ExitStack() as custody, host_lock(adapter.lock_id, lock_directory) as lease:
            lease["release"] = True  # Admission refusal before stop has no runtime effects.
            try:
                with lifecycle.FileLock(layout.lock_file, timeout=120):
                    run = read_json(layout.run_record)
                    installed = lifecycle.verify_install_fast(layout)
                    binding = adapter.warm_incumbent
                    fields = ("requested_utc", "profile_fingerprint", "wrapper", "server")
                    if (not isinstance(binding, dict) or not isinstance(binding.get("run"), dict)
                            or set(binding["run"]) != set(fields) or not all(binding["run"].values())
                            or any(run.get(key) != binding["run"][key] for key in fields)
                            or run.get("tree_token")
                            or prior != control.adapter.current()
                            or prior.get("profile_fingerprint") != layout.profile.fingerprint
                            or installed.get("runtime_identity_sha256") != binding.get("runtime_identity_sha256")
                            or prior.get("runtime_identity_sha256") != binding.get("runtime_identity_sha256")):
                        raise ExperimentError("recustody_legacy_generation_mismatch")
                    adapter.restoration_runtime_identity = installed["runtime_identity_sha256"]
                    artifacts = lifecycle.IncumbentArtifacts(layout, exonerate_null)
                    legacy = custody.enter_context(lifecycle.LegacyProcessTree(
                        binding["run"], snapshot=adapter.process_census))
                    before_artifacts = adapter.verify_incumbent_artifacts(artifacts, legacy, allow_legacy=True)
                    mutated, lease["release"] = True, False
                    lifecycle.stop(layout, log=lambda _line: None, locked=True)
                    proof = verify_legacy_release(adapter, artifacts, legacy)
                # The real restoration path owns fresh start, G10, installed binding,
                # exact readiness recheck and duplicated job-handle handoff.
                restored = adapter.restore(manifest, custody=custody)
                if not restored.get("serving"):
                    raise ExperimentError("recustody_restoration_failed")
                # Restore/G10 can create processes too. A fresh complete process
                # and port census is mandatory before adoption or lease release.
                after_artifacts = adapter.verify_incumbent_artifacts(artifacts, legacy)
                owned = adapter.owned_runs["restoration_target"]
                gate_id = restored["gate"]["run_id"]
                gate_path = layout.root / "evidence" / gate_id / "result.json"
                row = {"schema_version": "omp-strata.restoration-adoption.v1",
                    "operation": "recustody-incumbent", "host": host, "generation": generation,
                    "experiment_key": experiment_key(manifest), "trial_manifest_sha256": sha256(manifest_bytes),
                    "profile_id": layout.profile.id, "profile_fingerprint": layout.profile.fingerprint,
                    "runtime_identity_sha256": adapter.restoration_runtime_identity,
                    "prior_service_identity": prior, "restored_service_identity": control.adapter.current(),
                    "loop_owned_run": {**owned, "g10_run_id": gate_id},
                    "g10": {"result_path": str(gate_path), "sha256": sha256_file(gate_path)},
                    "physical_release": proof, "artifact_custody_before": before_artifacts,
                    "artifact_custody": after_artifacts, "emitted_utc": utc_now()}
                atomic_write_json(receipt, row)
                # Windows' existing controller mutex is recursive on this same
                # thread. Adoption revalidates the installed G10 and exact current
                # generation without opening admission or issuing a new lease.
                adopted = control.adopt_restoration(generation, str(receipt))
                if (adopted.get("paused") is not True or adopted.get("admission_open") is not False
                        or adopted.get("generation") != generation
                        or adopted.get("service", {}).get("identity") != row["restored_service_identity"]):
                    raise ExperimentError("recustody_controller_handoff_unverified")
                lease["release"] = True
                return row
            except (Exception, KeyboardInterrupt) as exc:
                atomic_write_json(receipt.with_suffix(".failure.json"), {
                    "schema_version": "omp-strata.recustody-failure.v1", "host": host,
                    "generation": generation, "physical_release": proof,
                    "artifact_custody_before": before_artifacts,
                    "observers": adapter.census_observers,
                    "process_snapshot": adapter.latest_process_census,
                    "requested_null_exonerations": list(exonerate_null),
                    "custody_retained": mutated, "stop_begun": mutated,
                    "reason": str(exc), "error_type": type(exc).__name__,
                    "observations": getattr(exc, "observations", [{"error": str(exc)}]), "utc": utc_now()})
                raise


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
            "planned_repetitions": {arm: manifest["repetitions"] for arm in ("baseline", "candidate")},
            "attempted_repetitions": {arm: (sum(row["arm"] == arm for row in measured["probe_attempts"])
                                            if "probe_attempts" in measured else None)
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
    plan.add_argument("--restoration-ref", help="Freeze the incumbent profile required by a future fleet claim")
    plan.add_argument("--out", type=Path)
    execute = sub.add_parser("run")
    execute.add_argument("--manifest", required=True, type=Path)
    execute.add_argument("--bindings", required=True, type=Path)
    execute.add_argument("--quiesce-incumbent", action="store_true",
                         help="Stop the verified warm baseline only under the host claim; serving must be fenced/drained")
    execute.add_argument("--claim", type=Path, help="Trusted carrythrough.fleet-claim.v1 document")
    execute.add_argument("--unattended", action="store_true", help="Require --claim; never execute the attended queue")
    execute.add_argument("--evidence-dir", type=Path, help="Private evidence parent (required with --claim)")
    recustody = sub.add_parser("recustody-incumbent",
                              help="One-time operator migration of the paused legacy incumbent into native job custody")
    for name in ("manifest", "bindings", "controller", "root", "receipt"):
        recustody.add_argument("--" + name, required=True, type=Path)
    recustody.add_argument("--generation", required=True, type=int)
    recustody.add_argument("--exonerate-null", action="append", default=[], metavar="PID:NAME",
                          help="Reviewed null command/executable row only; never a readable row or incumbent port owner")
    recustody.add_argument("--go", action="store_true", help="Explicitly authorize the same-incumbent stop/restore")
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
                host_profile=args.host_profile, retry_of=args.retry_of, resume_candidate=args.resume_candidate,
                restoration_ref=args.restoration_ref)
            if args.manifest and (args.host_profile or args.retry_of or args.resume_candidate):
                parser.error("--host-profile, --retry-of and --resume-candidate require profile-based planning")
            key = validate(manifest, restoration_ref=args.restoration_ref)
            if args.out:
                if args.out.exists():
                    raise ExperimentError("plan_output_exists")
                public_write(args.out, manifest, Scrubber("<private-root>", denylist=private_denylist()))
            result = {"key": key, "manifest": manifest}
        elif args.command == "recustody-incumbent":
            if not args.go:
                raise ExperimentError("recustody_requires_explicit_go")
            raw = args.manifest.read_bytes()
            manifest = parse_manifest_bytes(raw)
            validate(manifest, dedupe=False, restoration_ref=manifest["restoration_target"]["profile_id"])
            bindings = read_json(args.bindings)
            try:
                control = load_fleet_controller(args.controller, bindings["host"])
                row = recustody_incumbent(manifest, HostAdapter(manifest, bindings, claim=True), control,
                    host=bindings["host"], generation=args.generation, root=args.root, receipt=args.receipt,
                    manifest_bytes=raw, go=args.go, exonerate_null=args.exonerate_null)
            except Exception as exc:
                raise ExperimentError("recustody_failed_" + type(exc).__name__) from exc
            result = {"status": "restored", "receipt": str(args.receipt), "profile_id": row["profile_id"],
                      "fleet_paused": True, "candidate_executed": False}
        elif args.command == "preflight":
            manifest = read_json(args.manifest)
            validate(manifest, dedupe=False)
            started = time.monotonic()
            result = HostAdapter(manifest, read_json(args.bindings)).precondition(manifest, 120)
            result["wall_time_s"] = round(time.monotonic() - started, 3)
        elif args.command == "run":
            if args.unattended and not args.claim:
                raise ExperimentError("claim_required")
            if args.claim and not args.evidence_dir:
                raise ExperimentError("claim_requires_private_evidence")
            if args.evidence_dir and not args.claim:
                raise ExperimentError("claim_required")
            raw = args.manifest.read_bytes()
            manifest = parse_manifest_bytes(raw)
            bindings = read_json(args.bindings)
            claim = read_json(args.claim) if args.claim else None
            if claim is not None:
                validate_claim(claim, manifest, raw, bindings)
            validate(manifest, dedupe=claim is None, restoration_ref=claim["restoration_ref"] if claim else None)
            directory = run(manifest, HostAdapter(manifest, bindings, claim=claim),
                            claim=claim, bindings=bindings, manifest_bytes=raw,
                            unattended=args.unattended, releases=args.evidence_dir or RELEASES,
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
