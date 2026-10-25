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
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omp_strata import lifecycle, nvfp4
from omp_strata.common import IntegrityError
from omp_strata.common import atomic_write_bytes, atomic_write_json, sha256_file, utc_now
from omp_strata.comparison import canonical, read_json, sha256
from omp_strata.layout import Layout
from omp_strata.profile import load
from omp_strata.receipts import schema_errors
from scripts.eval_taskset import HOST_LOCKS
from scripts.requalify import last_object

def harness_files():
    # Include transitive execution dependencies, not a hand-maintained import subset.
    code = tuple(sorted(p.relative_to(ROOT).as_posix()
                        for directory in ("omp_strata", "scripts", "eval")
                        for p in (ROOT / directory).rglob("*.py")))
    data = tuple(sorted(p.relative_to(ROOT).as_posix()
                        for directory, suffix in (("profiles", "*.json"), ("schemas", "*.json"), ("locks", "*.txt"))
                        for p in (ROOT / directory).glob(suffix)))
    return code + data


HARNESS_FILES = harness_files()
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
             "harness_files": {p: sha256_file(ROOT / p) for p in harness_files()},
             "max_window_seconds": WINDOW_SECONDS, "return_budget_seconds": RETURN_SECONDS}
    if job_subset is not None:
        value["job_subset"] = job_subset
        value["job_subset_sha256"] = sha256(canonical(job_subset))
    validate(value)
    return value


def validate(manifest, *, sources=None):
    schema = (parse_manifest_bytes(sources["schemas/experiment-manifest.schema.json"]) if sources is not None
              else read_json(ROOT / "schemas/experiment-manifest.schema.json"))
    if schema_errors(manifest, schema):
        raise ExperimentError("invalid_manifest_schema")
    for arm in ("baseline", "candidate"):
        if manifest[arm] != freeze_arm(manifest[arm]["profile_id"]):
            raise ExperimentError("frozen_profile_drift")
        if manifest[arm]["config"]["host"]["gpu_model"] != HOST_PROFILES[manifest["host_role"]]:
            raise ExperimentError("host_profile_mismatch")
    if manifest["baseline"] == manifest["candidate"]:
        raise ExperimentError("identical_arms")
    digests = ({p: sha256(sources[p]) for p in harness_files()} if sources is not None
               else {p: sha256_file(ROOT / p) for p in harness_files()})
    if manifest["harness_files"] != digests:
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


@contextlib.contextmanager
def harness_snapshot(manifest, bindings, directory, *, sources=None):
    """Read/hash once, then execute only the per-window copy, never the checkout.

    Windows read handles deny WRITE and DELETE sharing until the worker exits:
    neither in-place edits nor path replacement can change an imported module.
    The pinned interpreter/stdlib is outside the harness. Private runners are
    operator-reviewed, self-contained scripts importing only that runtime and
    the copied harness, not arbitrary private sibling modules.
    """
    if sources is None:
        sources = capture_harness(manifest, bindings)
    directory = Path(directory).absolute()
    with contextlib.ExitStack() as handles:
        handles.enter_context(lifecycle.directory_fence(directory, {directory: None}))
        for name, raw in sources.items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ExperimentError("invalid_snapshot_path")
            path = directory / relative
            handles.enter_context(lifecycle.directory_fence(path.parent, {}))
            with path.open("xb") as stream:
                stream.write(raw)
            path.chmod(0o444)
            if os.name == "nt":
                import ctypes
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                              ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
                kernel.CreateFileW.restype = ctypes.c_void_p
                kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel.CloseHandle.restype = ctypes.c_int
                handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
                if handle == ctypes.c_void_p(-1).value:
                    raise ExperimentError("snapshot_seal_failed")
                handles.callback(kernel.CloseHandle, handle)
        receipt = {"root": str(directory), "source_root": str(ROOT),
                   "files": {name: sha256(raw) for name, raw in sources.items()}}
        yield receipt


def capture_harness(manifest, bindings):
    sources = {name: frozen_file(ROOT / name, digest) for name, digest in manifest["harness_files"].items()}
    sources["private/runner.py"] = frozen_file(bindings["runner"], manifest["runner_sha256"])
    return sources


def window_left(manifest, observed, wall_clock=None):
    now = (wall_clock or time.time)()
    left = min(manifest["max_window_seconds"] - manifest["return_budget_seconds"],
               observed + manifest["max_window_seconds"] - manifest["return_budget_seconds"] - now)
    if left <= CLEANUP_SECONDS or observed > now:
        raise ExperimentError("reservation_window_expired")
    return left


def snapshot_worker_command(payload, snapshot, timeout):
    # Only this bootstrap owns the outer non-breakaway kill-on-close job. If it
    # dies, the worker and every nested candidate job die with it, before they
    # can outlive the snapshot seals. No child inherits or opens this job handle.
    bootstrap = ("import json,sys; sys.path.insert(0,sys.argv[1]); "
                 "from scripts.experiment_loop import frozen_worker; "
                 "frozen_worker(json.load(sys.stdin))")
    end = time.monotonic() + timeout
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        source.write(json.dumps(payload).encode())
        source.seek(0)
        job = lifecycle.ProcessJob(os.urandom(16).hex())
        try:
            child = job.spawn([sys.executable, "-I", "-S", "-B", "-c", bootstrap, str(snapshot)],
                              stdin=source, stdout=out, stderr=err, env=os.environ, cwd=snapshot,
                              timeout=HostAdapter.left(end))
            child.wait(timeout=HostAdapter.left(end))
        finally:
            try:
                job.stop(max(0, min(CLEANUP_SECONDS, end - time.monotonic())))
            finally:
                job.close()
        out.seek(0)
        result = parse_manifest_bytes(out.read())
        if "error" in result:
            raise ExperimentError(result["error"])
        if child.returncode:
            raise ExperimentError("frozen_worker_failed")
        return result


def run_frozen(manifest, bindings, evidence_dir):
    """Bootstrap only; every host-effecting driver/module runs in the sealed child."""
    if sys.platform != "win32":
        raise ExperimentError("run_requires_native_windows_detached_worker")
    # Reject extra/missing paths before opening the capture set.
    if set(manifest["harness_files"]) != set(harness_files()):
        raise ExperimentError("frozen_harness_drift")
    sources = capture_harness(manifest, bindings)
    validate(manifest, sources=sources)
    load_inputs(manifest, bindings, runner_source=sources["private/runner.py"])
    adapter = HostAdapter(manifest, bindings)  # Root/binding validation is read-only.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", adapter.lock_id):
        raise ExperimentError("invalid_lock_id")
    if (HOST_LOCKS / (adapter.lock_id + ".lock")).exists():
        raise ExperimentError("host_lock_owned")
    observed = check_reservation(parse_manifest_bytes(CONTROL_STATE.read_bytes()), bindings["controller"])
    srv = manifest["baseline"]["config"]["server"]
    if lifecycle.port_in_use(srv["listen_host"], srv["port"]):
        raise ExperimentError("incumbent_port_open")
    left = window_left(manifest, observed)
    evidence_dir = Path(evidence_dir).absolute()
    if evidence_dir == ROOT or ROOT in evidence_dir.parents:
        raise ExperimentError("private_evidence_required")
    # Validate the private output parent before creating any snapshot artifacts.
    parent = evidence_dir
    while not parent.exists():
        parent = parent.parent
    lifecycle.assert_operator_directory(parent)
    snapshot = evidence_dir / (experiment_key(manifest) + "-g" + str(bindings["controller"]["generation"])
                               + "-harness-" + os.urandom(8).hex())
    with harness_snapshot(manifest, bindings, snapshot, sources=sources) as receipt:
        frozen_bindings = {**bindings, "runner": str(snapshot / "private/runner.py"), "harness_snapshot": receipt}
        payload = {"manifest": manifest, "bindings": frozen_bindings, "evidence_dir": str(evidence_dir)}
        return snapshot_worker_command(payload, snapshot, min(left, window_left(manifest, observed)))


def frozen_worker(payload):
    try:
        manifest, bindings = payload["manifest"], payload["bindings"]
        if ROOT != Path(bindings["harness_snapshot"]["root"]):
            raise ExperimentError("snapshot_execution_root_mismatch")
        result = report(run(manifest, HostAdapter(manifest, bindings), bindings=bindings,
                            evidence_dir=payload["evidence_dir"]))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result = {"error": str(exc) if isinstance(exc, ExperimentError) else type(exc).__name__}
    print(json.dumps(result, allow_nan=False))


def load_inputs(manifest, bindings, *, runner_source=None):
    """Freeze private primary evidence and the original denominators before any host effect."""
    raw = frozen_file(bindings["retained_baseline_evidence"], manifest["candidate_only_against"])
    retained = parse_manifest_bytes(raw)
    job_path = Path(bindings["job_manifest"])
    job_raw = frozen_file(job_path, manifest["job_manifest_sha256"])
    jobs = parse_manifest_bytes(job_raw)
    baseline_raw = frozen_file(bindings["baseline_manifest"], jobs["loop_manifest_sha256"])
    if parse_manifest_bytes(baseline_raw).get("baseline") != manifest["baseline"]:
        raise ExperimentError("retained_baseline_identity_mismatch")
    if runner_source is None:
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
    return {"retained_raw": raw, "job_raw": job_raw, "baseline_raw": baseline_raw, "inventory": inventory,
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
    with stream:
        json.dump(owner, stream)
    def release():
        if not path.exists() or read_json(path) != owner:
            raise ExperimentError("host_lock_identity_changed")
        path.unlink()
    # Release is an explicit, fallible effect, before evidence claims success.
    # Any exceptional path before that point retains the persistent hold.
    yield release


def run(manifest, adapter, *, bindings, evidence_dir, lock_directory=HOST_LOCKS,
        clock=time.monotonic, wall_clock=time.time):
    key = validate(manifest)
    inputs = load_inputs(manifest, bindings)
    evidence_dir = Path(evidence_dir).absolute()
    if evidence_dir == ROOT or ROOT in evidence_dir.parents:
        raise ExperimentError("private_evidence_required")
    # No evidence directories, locks, installs or launches on an unreserved host.
    observed = adapter.reservation(require_closed_port=True)
    left = window_left(manifest, observed, wall_clock)
    started, deadline = clock(), clock() + left - CLEANUP_SECONDS
    directory = evidence_dir / (key + "-g" + str(bindings["controller"]["generation"]))
    with lifecycle.directory_fence(directory, {directory: None}):
        return _run_admitted(manifest, adapter, bindings, directory, lock_directory, clock, wall_clock,
                             inputs, observed, started, deadline)


def _run_admitted(manifest, adapter, bindings, directory, lock_directory, clock, wall_clock,
                  inputs, observed, started, deadline):
    atomic_write_bytes(directory / "retained-baseline-evidence.json", inputs["retained_raw"])
    atomic_write_bytes(directory / "job-manifest.json", inputs["job_raw"])
    atomic_write_bytes(directory / "baseline-manifest.json", inputs["baseline_raw"])
    atomic_write_json(directory / "manifest.json", manifest)
    measured = {"status": "running", "comparison_only": True, "started_utc": utc_now(),
                "harness_snapshot": bindings.get("harness_snapshot"),
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
                        adapter.guard("candidate", remaining())
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
                cleanup_started = clock()
                cleanup_left = min(CLEANUP_SECONDS, deadline + CLEANUP_SECONDS - cleanup_started,
                    observed + manifest["max_window_seconds"] - manifest["return_budget_seconds"] - wall_clock())
                adapter.cleanup(max(0, cleanup_left))
                if (cleanup_left < 0 or clock() > cleanup_started + max(0, cleanup_left)
                        or wall_clock() > observed + manifest["max_window_seconds"] - manifest["return_budget_seconds"]):
                    raise ExperimentError("cleanup_deadline_exceeded")
                measured["candidate_tree_dead"] = True
            except (Exception, KeyboardInterrupt) as exc:
                measured["status"] = "cleanup_failed"
                measured["failures"].append(type(exc).__name__)
            # This releases only our persistent local lock, never controller state.
            eligible = (measured["candidate_tree_dead"]
                and all(r.get("result", {}).get("external_clients_stopped") is True
                        for r in measured["attempts"] if r["family"] == "golden-1"))
            if eligible:
                try:
                    lease()
                    measured["custody_released"] = True
                except (Exception, KeyboardInterrupt) as exc:
                    measured["status"] = "cleanup_failed"
                    measured["failures"].append("hold_removal_" + type(exc).__name__)
            measured["local_hold"] = None if measured["custody_released"] else str(
                lock_directory / (adapter.lock_id + ".lock"))
            save()
            atomic_write_json(directory / "comparison.json", report(directory))
    return directory


class HostAdapter:
    """Native worker under docs/OPERATIONS.md#threat-model; no hostile-operator claim."""
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
        source_root = Path(bindings.get("harness_snapshot", {}).get("source_root", ROOT))
        if (root.parent == root or root == home or root in home.parents
                or root == source_root or source_root in root.parents
                or root in source_root.parents and source_root != root / "tooling"
                or root == ROOT or ROOT in root.parents):
            raise ExperimentError("unsafe_integration_root")
        try:
            nvfp4.assert_isolated_tree(root)
        except IntegrityError:
            raise ExperimentError("candidate_tree_reparse_point") from None
        layout = Layout(root, load(ROOT / "profiles" / (manifest["candidate"]["profile_id"] + ".json")))
        if layout.install_record.exists() and read_json(layout.install_record).get("profile_fingerprint") != layout.profile.fingerprint:
            raise ExperimentError("candidate_root_owned_by_another_profile")
        self.layouts = {"candidate": layout}
        self.owned_runs, self.launch_requests, self.launch_jobs, self.owned_commands = {}, {}, {}, {}
        self.admission_generation = None
        self.root_identities = {p: self.path_identity(p) for p in (root, *root.parents, layout.state,
                                                                root / "evidence", layout.logs)}
        # Bind existing output directories to the isolation scan, not their later path targets.
        for output in (root / "evidence", layout.logs):
            self.root_identities.update({p: self.path_identity(p) for p in output.rglob("*") if p.is_dir()})
        self.assert_acl()

    @staticmethod
    def path_identity(path):
        return lifecycle.directory_identity(path)

    def assert_acl(self):
        layout = self.layouts["candidate"]
        parent = layout.root.parent
        while not parent.exists():
            parent = parent.parent
        for path in (parent, layout.root, layout.state, layout.root / "evidence"):
            if path.exists():
                lifecycle.assert_operator_directory(path)

    def check_root(self, *, create=False):
        root = self.layouts["candidate"].root
        for path, identity in self.root_identities.items():
            if self.path_identity(path) != identity or path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise ExperimentError("candidate_root_replaced")
        if create and any(self.path_identity(p) is None for p in
                          (self.layouts["candidate"].state, root / "evidence")):
            for path in (self.layouts["candidate"].state, root / "evidence"):
                with lifecycle.directory_fence(path, self.root_identities):
                    pass
            self.assert_acl()
        for path, identity in self.root_identities.items():
            if self.path_identity(path) != identity:
                raise ExperimentError("candidate_root_replaced")

    @contextlib.contextmanager
    def root_fence(self):
        self.check_root()
        layout = self.layouts["candidate"]
        with lifecycle.directory_fence(layout.lock_file.parent, self.root_identities) as parent_fd:
            self.check_root()
            yield parent_fd

    @contextlib.contextmanager
    def output_fence(self, path):
        """Pin all output components through creation and use; never resolve away aliases."""
        with lifecycle.directory_fence(path, self.root_identities) as parent_fd:
            yield parent_fd

    @contextlib.contextmanager
    def root_lock(self, deadline):
        with self.root_fence() as parent_fd:
            with lifecycle.FileLock(self.layouts["candidate"].lock_file,
                                    timeout=max(0, deadline - time.monotonic()), parent_fd=parent_fd):
                self.check_root()
                yield

    @staticmethod
    def left(deadline):
        value = deadline - time.monotonic()
        if value <= 0:
            raise ExperimentError("max_wall_time")
        return value

    def require_idle(self, layout, deadline, *, locked=False):
        self.check_root(create=not locked)
        with contextlib.nullcontext() if locked else self.root_lock(deadline):
            self.check_root()
            try:
                return lifecycle.idle_generation(layout, expected=self.admission_generation,
                                                 timeout=max(0, deadline - time.monotonic()))
            except lifecycle.LifecycleError:
                raise ExperimentError("prior_candidate_generation_unproved") from None

    def reservation(self, *, require_closed_port=False):
        observed = check_reservation(parse_manifest_bytes(CONTROL_STATE.read_bytes()), self.bindings["controller"])
        if require_closed_port:
            srv = self.manifest["baseline"]["config"]["server"]
            if lifecycle.port_in_use(srv["listen_host"], srv["port"]):
                raise ExperimentError("incumbent_port_open")
        return observed

    def command(self, arm, script, args, timeout, *, monitor=False, env=None, source=None):
        end = time.monotonic() + timeout
        self.reservation()
        layout = self.layouts[arm]
        root = layout.root
        self.check_root(create=True)
        if root in self.owned_commands:
            raise ExperimentError("command_cleanup_unresolved")
        private = root / "evidence/experiments"
        prefix = private / str(time.time_ns())
        argv = [sys.executable, "-I", "-S", "-B", str(ROOT / "scripts" / script), *args,
                "--profile", str(layout.profile.path), "--root", str(root)]
        with self.root_fence(), self.output_fence(private), self.output_fence(layout.logs), \
                contextlib.ExitStack() as streams:
            # Admission commands must still see precisely the generation they admitted.
            # Workload commands instead run under guard's owned running generation.
            if self.admission_generation is not None and not monitor:
                self.require_idle(layout, end)
            out = streams.enter_context(prefix.with_suffix(".out").open("xb"))
            err = streams.enter_context(prefix.with_suffix(".err").open("xb"))
            launch_options = {}
            if source is not None:
                # An anonymous open file transports the verified snapshot, not a mutable pathname.
                code = streams.enter_context(tempfile.TemporaryFile())
                code.write(source)
                code.seek(0)
                bootstrap = ("import sys; p=sys.argv.pop(1); sys.argv[0]=p; "
                             f"sys.path.insert(0,{str(ROOT)!r}); "
                             "exec(compile(sys.stdin.buffer.read(),p,'exec'),"
                             "{'__name__':'__main__','__file__':p})")
                argv[4:5] = ["-c", bootstrap, argv[4]]
                launch_options["stdin"] = code
            launching = script == "omp_strata.py" and args[0] == "start"
            job = self.launch_jobs[arm] if launching else lifecycle.ProcessJob(os.urandom(16).hex())
            owned = self.owned_commands[root] = {"child": None, "job": job}
            try:
                self.left(end)
                child = owned["child"] = job.spawn(argv, stdout=out, stderr=err,
                                                   env={**os.environ, **(env or {})},
                                                   timeout=self.left(end), **launch_options)
                while child.poll() is None:
                    left = end - time.monotonic()
                    if left <= 0:
                        raise ExperimentError("max_wall_time")
                    self.reservation()
                    if monitor:
                        self.guard(arm, left)
                    try:
                        child.wait(timeout=min(2, self.left(end)))
                    except subprocess.TimeoutExpired:
                        pass
            except BaseException:
                # Retain the command and job for root-fenced cleanup's reserved
                # proof budget. Never stop(0) before pending cancellation/proof.
                raise
            else:
                child = owned["child"]
                if not launching:
                    job.stop(self.left(end))
                child.wait(timeout=self.left(end))
                del self.owned_commands[root]
            self.check_root()
            self.reservation()
        result = last_object(prefix.with_suffix(".out").read_text(encoding="utf-8", errors="replace"))
        if child.returncode:
            raise ExperimentError("child_failed")
        return result

    def install(self, manifest, timeout):
        started = time.monotonic()
        layout = self.layouts["candidate"]
        self.check_root()
        if nvfp4.is_local(layout.profile.data["model"]):
            nvfp4.staging_preflight(layout)
        generation = self.admission_generation = self.require_idle(layout, started + timeout)
        self.command("candidate", "omp_strata.py", ["install", "--idle-generation", generation],
                     self.left(started + timeout))
        self.command("candidate", "omp_strata.py", ["keygen", "--idle-generation", generation],
                     self.left(started + timeout))

    def start(self, arm, timeout):
        deadline = time.monotonic() + timeout
        self.reservation(require_closed_port=True)
        layout = self.layouts[arm]
        if layout.root in self.owned_commands:
            raise ExperimentError("command_cleanup_unresolved")
        if arm in self.launch_requests or arm in self.launch_jobs:
            raise ExperimentError("launch_cleanup_unresolved")
        generation = self.require_idle(layout, deadline)
        launch_id = os.urandom(16).hex()
        job = lifecycle.ProcessJob(launch_id)
        self.launch_requests[arm] = {"experiment_launch_id": launch_id,
                                    "profile_fingerprint": layout.profile.fingerprint}
        self.launch_jobs[arm] = job
        captured = False
        result = self.command(arm, "omp_strata.py", ["start", "--idle-generation", generation,
                              "--timeout", str(max(1, int(self.left(deadline))))],
                              self.left(deadline), env={lifecycle.EXPERIMENT_LAUNCH_ENV: launch_id})
        with self.root_lock(deadline):
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
        deadline = time.monotonic() + timeout
        owned = self.owned_runs.get(arm)
        request = self.launch_requests.get(arm)
        layout = self.layouts[arm]
        self.check_root()
        if not layout.root.exists() and not (owned or request or self.owned_commands or self.launch_jobs):
            return
        command = self.owned_commands.get(layout.root)
        job = self.launch_jobs.get(arm)
        with self.root_fence() as parent_fd:
            # An installer holds FileLock throughout its effects. Terminate and
            # prove that non-launch job under the directory fence BEFORE waiting
            # on its lock. Launch wrappers instead need root-locked cancellation.
            if command and (job is None or command.get("job") is not job):
                command["job"].stop(self.left(deadline))
                if command.get("child"):
                    command["child"].wait(timeout=max(0, deadline - time.monotonic()))
                del self.owned_commands[layout.root]
                command = None
            with lifecycle.FileLock(layout.lock_file, timeout=max(0, deadline - time.monotonic()),
                                    parent_fd=parent_fd):
                self.check_root()
                current = read_json(layout.run_record) if layout.run_record.exists() else {}

                def finish_launch_command():
                    if command and job is not None and command["job"] is job:
                        if command.get("child"):
                            command["child"].wait(timeout=max(0, deadline - time.monotonic()))
                        self.owned_commands.pop(layout.root, None)

                if request is not None and any(current.get(k) != v for k, v in request.items()):
                    if job:
                        job.stop(max(0, deadline - time.monotonic()))
                        finish_launch_command()
                        del self.launch_jobs[arm]
                    if owned is not None:
                        raise ExperimentError("owned_generation_changed")
                    self.require_idle(layout, deadline, locked=True)
                    del self.launch_requests[arm]
                    return
                if owned is None and request is None:
                    self.require_idle(layout, deadline, locked=True)
                    return
                if owned is not None and any(current.get(k) != v for k, v in owned.items()):
                    raise ExperimentError("owned_generation_changed")
                if job is None or current.get("tree_token") != job.token:
                    raise ExperimentError("candidate_job_generation_unproved")
                current["state"] = "stop_incomplete"
                atomic_write_json(layout.run_record, current)
                job.stop(max(0, deadline - time.monotonic()))
                current.update(state="stopped", unpublished_child=False, tree_verified_empty=job.token,
                               stopped_utc=utc_now())
                atomic_write_json(layout.run_record, current)
                finish_launch_command()
                self.launch_jobs.pop(arm, None)
                self.owned_runs.pop(arm, None)
                self.launch_requests.pop(arm, None)

    def guard(self, arm, timeout):
        deadline = time.monotonic() + timeout
        with self.root_fence():
            self._guard(arm, deadline)

    def _guard(self, arm, deadline):
        self.left(deadline)
        self.reservation()
        self.check_root()
        layout = self.layouts[arm]
        current = read_json(layout.run_record)
        installed = read_json(layout.install_record)
        owned = self.owned_runs.get(arm)
        if (not owned or any(current.get(k) != v for k, v in owned.items())
                or current.get("state") != "ready"
                or current.get("runtime_identity_sha256") != installed.get("runtime_identity_sha256")
                or installed.get("profile_fingerprint") != layout.profile.fingerprint):
            raise ExperimentError("runtime_identity_lost")
        job = self.launch_jobs[arm]
        if not job.pids() or not job.enumerate_tree(timeout=self.left(deadline)):
            raise ExperimentError("candidate_job_identity_lost")
        self.left(deadline)
        if not lifecycle.runtime_checks(layout, lifecycle.read_key(layout), deadline=deadline).get("ready"):
            raise ExperimentError("runtime_identity_lost")
        self.left(deadline)
        if read_json(layout.run_record) != current:
            raise ExperimentError("runtime_identity_lost")
        self.reservation()
        self.left(deadline)

    def run_job(self, job, attempt, timeout):
        runner = Path(self.bindings["runner"]).resolve()
        source = frozen_file(runner, self.manifest["runner_sha256"])
        frozen_file(self.bindings["job_manifest"], self.manifest["job_manifest_sha256"])
        return self.command("candidate", str(runner), [
            "--job-manifest", str(Path(self.bindings["job_manifest"]).resolve()),
            "--job-manifest-sha256", self.manifest["job_manifest_sha256"],
            "--family", job["family"], "--job", job["job"], "--attempt", str(attempt),
            "--timeout", str(timeout)], timeout, monitor=True, source=source)

    def cleanup(self, timeout):
        deadline = time.monotonic() + timeout
        errors = []
        try:
            self.stop("candidate", timeout)
        except BaseException as exc:
            errors.append(exc)
        # A changed record or unavailable root lock must not skip native cleanup.
        jobs = [*self.launch_jobs.values(), *(v["job"] for v in self.owned_commands.values() if v["job"])]
        for job in jobs:
            try:
                job.stop(max(0, deadline - time.monotonic()))
            except BaseException as exc:
                errors.append(exc)
        if errors or self.launch_requests or self.owned_commands or any(not j.verified_empty for j in jobs):
            raise ExperimentError("candidate_cleanup_unproved")


def report(directory):
    manifest = read_json(directory / "manifest.json")
    measured = read_json(directory / "measurements.json")
    jobs = parse_manifest_bytes(frozen_file(directory / "job-manifest.json", manifest["job_manifest_sha256"]))
    baseline_manifest = parse_manifest_bytes(frozen_file(
        directory / "baseline-manifest.json", jobs["loop_manifest_sha256"]))
    if baseline_manifest.get("baseline") != manifest["baseline"]:
        raise ExperimentError("retained_baseline_identity_mismatch")
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
            "harness_snapshot": measured.get("harness_snapshot"),
            "candidate_only_against": manifest["candidate_only_against"],
            "job_manifest_sha256": manifest["job_manifest_sha256"],
            "baseline_manifest_sha256": jobs["loop_manifest_sha256"],
            "job_subset": manifest.get("job_subset"), "job_subset_sha256": manifest.get("job_subset_sha256"),
            "planned_jobs": len(rows), "selected_jobs": len(measured["selected"]),
            "planned_attempts": sum(r["planned_attempts_per_arm"] for r in rows),
            "selected_attempts": sum(r["planned_attempts_per_arm"] for r in measured["selected"]),
            "attempted": len(measured["attempts"]),
            "completed": sum(r["status"] == "complete" for r in measured["attempts"]),
            "candidate_tree_dead": measured["candidate_tree_dead"], "custody_released": measured["custody_released"],
            "local_hold": measured.get("local_hold"),
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
    for name in ("candidate-only-against", "job-manifest", "baseline-manifest", "runner", "out"):
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
                                "job_manifest": args.job_manifest, "baseline_manifest": args.baseline_manifest,
                                "runner": args.runner})
            atomic_write_json(args.out, result)
        elif args.command == "run":
            manifest = parse_manifest_bytes(args.manifest.read_bytes())
            bindings = parse_manifest_bytes(args.bindings.read_bytes())
            result = run_frozen(manifest, bindings, args.evidence_dir)
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
