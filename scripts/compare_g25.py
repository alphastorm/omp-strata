#!/usr/bin/env python3
"""G25 comparison-only orchestration; never installs, starts or modifies an engine."""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.support import EVAL, inventory, materialize, run_bounded, run_verifier, validate_manifest
from scripts.evaluate import EventCounts, run_phase, snapshot, save_changes
from omp_strata.comparison import (
    ABORT_REASONS, ARMS, ArmAdapter, ComparisonError, canonical, file_sha256, harness_identity,
    load_bindings, load_plan, new_plan, pilot_contract_digest, plan_digest, read_json, schedule,
    sha256, summarize_records, validate_attempt, validate_host_observation, validate_plan,
    validate_summary, validate_window, verify_omp_binary,
)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def publish(path: Path, data, *, exclusive=True):
    """Durably write a complete JSON object, without ever replacing a published result."""
    payload = canonical(data) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending")
    try:
        with temporary.open("xb") as stream:
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            # Hard-link publication is atomic and refuses a destination created by a racer.
            os.link(temporary, path)
            temporary.unlink()
        else:
            os.replace(temporary, path)
    except FileExistsError as exc:
        raise ComparisonError("refusing to overwrite an existing result or interrupted publication") from exc


def assert_runtime(plan):
    if harness_identity() != dict(plan["harness"]):
        raise ComparisonError("harness_modified")
    manifest = read_json(EVAL / "tasks.json")
    if file_sha256(EVAL / "tasks.json") != plan["evaluation"]["manifest_sha256"] or inventory() != manifest["files"]:
        raise ComparisonError("frozen_evaluation_modified")


def artifact(path, root):
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ComparisonError("unsafe_workspace")
    return {"path": path.relative_to(root).as_posix(), "sha256": file_sha256(path)}


def undispatched(plan, task, *, arm, window, number, reason, status="undispatched"):
    fields = ("task_wall_ms", "reported_output_tokens", "request_wall_ms", "server_time_ms", "tool_calls", "compactions",
              "config_sha256", "models_sha256", "verifier_exit_code")
    return {"schema_version": 1, "record_type": "attempt", "comparison_id": plan["comparison_id"],
            "plan_sha256": plan_digest(plan), "arm": arm, "window": window, "task_id": task["id"],
            "attempt_number": number, "status": status, "verified_pass": False, "abort_reason": reason,
            "omp_binary_sha256": plan["omp"]["sha256"],
            **{key: task[key] for key in ("workspace_sha256", "prompt_sha256", "verifier_sha256")},
            **{field: None for field in fields}, "missing_reasons": {field: reason for field in fields},
            "phases": [], "protocol_errors": {}, "timeout": reason == "comparison_wall_cap", "oom_observed": False,
            "unsafe_workspace": reason == "unsafe_workspace", "verifier": {"task": task["id"], "passed": False},
            "transcripts": [], "artifacts": [], "endpoint": None,
            "timing_boundary": "monotonic materialization through verifier completion",
            "request_timing_method": "not independently observed", "server_timing_method": "not independently observed"}


def run_comparison_attempt(adapter: ArmAdapter, task, number, *, plan, window, directory, batch_deadline, dispatch_guard=None):
    """The only attempt implementation, including continuation and all frozen G24 caps."""
    assert_runtime(plan)
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    budget = task["budget"]
    deadline = min(batch_deadline, started + budget["wall_seconds"])
    record = undispatched(plan, task, arm=adapter.arm, window=window, number=number, reason="interrupted", status="incomplete")
    publish(directory / "incomplete.json", record)
    try:
        workspace = materialize(task, directory / "workspace")
        before = snapshot(workspace)
        launch = adapter.prepare(directory / "client")
        if launch.endpoint.get("arm") != adapter.arm or any(launch.endpoint.get(key) != plan[adapter.arm][field]
               for key, field in (("api", "api"), ("provider", "provider"), ("model", "model_id"))):
            raise ComparisonError("wrong_endpoint_identity")
        if not launch.home.resolve().is_relative_to(directory.resolve()):
            raise ComparisonError("unsafe_workspace")
        sessions = directory / "sessions"
        sessions.mkdir()
        counts, phases, abort, unsafe = EventCounts(), [], None, False
        for phase in range(1, task["phases"] + 1):
            assert_runtime(plan)
            if phase > 1 and dispatch_guard is not None:
                dispatch_guard()
            remaining = deadline - time.monotonic() - 30
            if remaining <= 0:
                abort = "timeout"
                break
            prompt_name = "prompt.md" if phase == 1 else "followup.md"
            prompt = (EVAL / "tasks" / task["id"] / prompt_name).read_text(encoding="utf-8")
            extra = ["-p", "--mode", "json", "--auto-approve", "--max-time", f"{max(1, math.floor(remaining))}s",
                     "--session-dir", str(sessions), "--tools", "read,bash,edit,write,grep,glob"]
            if phase > 1:
                extra.append("--continue")
            extra.append(prompt)
            phase_result = run_phase(launch.argv + extra, workspace=workspace, env=launch.env,
                                     directory=directory, phase=phase, deadline=deadline - 30,
                                     budget=budget, counts=counts)
            phase_result["events"] = Path(phase_result["events"]).relative_to(directory).as_posix()
            phase_result["stderr"] = Path(phase_result["stderr"]).relative_to(directory).as_posix()
            phases.append(phase_result)
            if phase_result["abort_reason"] or phase_result["exit_code"] != 0 or not phase_result["completed"]:
                abort = phase_result["abort_reason"] or "client_failure"
                break
            if phase < task["phases"]:
                try:
                    if snapshot(workspace) != before:
                        abort = "phase_one_not_read_only"
                        break
                except (OSError, ValueError):
                    abort, unsafe = "unsafe_workspace", True
                    break
                if not counts.calibration_observed:
                    abort = "phase_one_missing_calibration_tool_result"
                    break
                for name in task["remove_between_phases"]:
                    (workspace / name).unlink()
        try:
            save_changes(before, workspace, directory)
        except (OSError, ValueError):
            unsafe, abort = True, "unsafe_workspace"
        try:
            assert_runtime(plan)
        except ComparisonError as exc:
            unsafe, abort = True, str(exc)
        if unsafe:
            verifier = {"verdict": {"task": task["id"], "passed": False}, "returncode": None}
        else:
            verifier = run_verifier(task, workspace, timeout=min(30, max(0, deadline - time.monotonic())))
        elapsed = (time.monotonic() - started) * 1000
        timed_out = abort == "timeout" or elapsed > budget["wall_seconds"] * 1000 or verifier.get("timed_out", False)
        errors, compactions, transcripts = counts.summary(), 0, []
        for path in sorted(sessions.rglob("*.jsonl")):
            try:
                if path.is_symlink() or path.stat().st_size > budget["max_event_bytes"]:
                    raise ValueError("unsafe transcript")
                for line in path.read_text(encoding="utf-8").splitlines():
                    entry = json.loads(line)
                    if not isinstance(entry, dict):
                        raise ValueError("invalid transcript record")
                    compactions += entry.get("type") == "compaction"
                transcripts.append(artifact(path, directory))
            except (OSError, ValueError):
                errors["invalid_transcript"] = errors.get("invalid_transcript", 0) + 1
        if not transcripts:
            errors["missing_transcript"] = 1
        # Neither keys nor arbitrary environment values are written into records or error messages.
        secrets = [value.encode() for key, value in launch.env.items() if key.endswith("API_KEY") and value]
        paths = [path for path in directory.rglob("*") if path.is_file() and not path.is_symlink()
                 and "workspace" not in path.relative_to(directory).parts and "client" not in path.relative_to(directory).parts]
        for path in paths:
            if path.stat().st_size <= budget["max_event_bytes"] and any(secret in path.read_bytes() for secret in secrets):
                # Exposure is retained as a failure, but the credential-bearing artifact is removed.
                path.write_text("[credential-bearing artifact withheld]\n", encoding="utf-8")
                abort = "credential_exposure"
        passed = (verifier["verdict"]["passed"] and not abort and not timed_out and not any(errors.values())
                  and len(phases) == task["phases"])
        missing = {"request_wall_ms": "not independently observed", "server_time_ms": "not independently observed"}
        output_tokens = counts.output_tokens if counts.output_usage_known and counts.assistants else None
        if output_tokens is None:
            missing["reported_output_tokens"] = "provider did not report complete assistant output usage"
        if verifier["returncode"] is None:
            missing["verifier_exit_code"] = "verification refused or had no remaining time"
        record.update(status="complete", verified_pass=bool(passed), abort_reason=abort, timeout=timed_out,
                      task_wall_ms=round(elapsed, 3), tool_calls=counts.tool_calls, protocol_errors=errors,
                      phases=phases, compactions=compactions, reported_output_tokens=output_tokens,
                      oom_observed=counts.oom, unsafe_workspace=unsafe, verifier=verifier["verdict"],
                      verifier_exit_code=verifier["returncode"], config_sha256=launch.config_sha256,
                      models_sha256=launch.models_sha256, transcripts=[artifact(directory / ref["path"], directory) for ref in transcripts],
                      endpoint=launch.endpoint, missing_reasons=missing,
                      artifacts=[artifact(path, directory) for path in paths if path.name != "incomplete.json"])
        issues = validate_attempt(record, plan)
        if issues:
            raise ComparisonError("invalid attempt record: " + "; ".join(issues))
        publish(directory / "result.json", record)
        return record
    except BaseException:
        # A crash leaves explicit failed/incomplete state, never a successful placeholder.
        record.update(status="incomplete", verified_pass=False, abort_reason="interrupted")
        record["task_wall_ms"] = round((time.monotonic() - started) * 1000, 3)
        record["missing_reasons"].pop("task_wall_ms", None)
        publish(directory / "incomplete.json", record, exclusive=False)
        raise


def observe_host(bindings, plan, arm):
    result = run_bounded(bindings["host_probe_argv"] + ["--arm", arm], cwd=Path(bindings["comparison_root"]),
                         timeout=min(60, plan["schedule"]["switch_timeout_seconds"]), limit=262144)
    if result["returncode"] != 0 or result["timed_out"] or result["output_limited"]:
        raise ComparisonError("observation_unavailable")
    try:
        observation = json.loads(result["stdout"])
    except ValueError as exc:
        raise ComparisonError("observation_unavailable") from exc
    issues = validate_host_observation(observation, plan, arm)
    if issues:
        raise ComparisonError(next((reason for reason in ABORT_REASONS if reason in issues), "observation_unavailable"))
    return observation


def _endpoint_preflight(adapter, plan):
    identity = adapter.preflight()
    if not isinstance(identity, dict) or any(identity.get(key) != plan[adapter.arm][field]
               for key, field in (("api", "api"), ("provider", "provider"), ("model", "model_id"))):
        raise ComparisonError("wrong_endpoint_identity")
    return identity


def _window_base(plan, row, boundary):
    return {"schema_version": 1, "record_type": "window", "comparison_id": plan["comparison_id"],
            "plan_sha256": plan_digest(plan), "window": row["window"], "arm": row["arm"],
            "attempt_number": row["attempt_number"], "status": "incomplete", "execution_boundary": boundary,
            "started_utc": utc_now(), "ended_utc": None, "omp_binary_sha256": plan["omp"]["sha256"],
            "identities": {arm: dict(plan[arm]) for arm in ARMS}, "endpoint_checks": [],
            "host": {key: plan["host"][key] for key in ("label", "os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy")},
            "exclusive_gpu": False, "observations": [], "startup_ms": None, "switch_ms": None,
            "attempts": [], "abort_reason": "interrupted", "consecutive_oom": {arm: 0 for arm in ARMS},
            "missing_reasons": {"startup_ms": "window not observed", "switch_ms": "window not observed"}}


def _safe_reason(exc):
    # Adapter exceptions can carry local paths; only the closed safety vocabulary reaches records/stdout.
    message = str(exc)
    return next((reason for reason in ABORT_REASONS if message == reason or message.startswith(reason + ":")), "wrong_endpoint_identity")


def run_window(plan, bindings, adapter, number, *, observer=observe_host, pilot=False):
    row = schedule()[number - 1]
    if number not in range(1, 7) or adapter.arm != row["arm"]:
        raise ComparisonError("invalid window/adapter selection")
    root = Path(bindings["comparison_root"])
    root.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(root, 0o700)
    target = root / (f"pilot-{adapter.arm}" if pilot else f"window-{number}")
    if target.exists():
        raise ComparisonError("refusing to overwrite or resume an existing window")
    previous = None
    if not pilot and number > 1:
        previous = read_json(root / f"window-{number - 1}" / "window.json")
        if previous.get("status") != "complete" or validate_window(previous, plan):
            raise ComparisonError("previous window is not finalized")
    if not pilot:
        errors = validate_plan(plan, finalized=True)
        if errors:
            raise ComparisonError("; ".join(errors))
        if plan["pilot"]["execution_boundary"] != bindings["execution_boundary"]:
            raise ComparisonError("pilot and scored execution boundaries differ")
    # mkdir is the exclusive, non-resumable window reservation; even a kill before publication remains occupied.
    try:
        target.mkdir()
    except FileExistsError as exc:
        raise ComparisonError("window already reserved") from exc
    record = _window_base(plan, row, bindings["execution_boundary"])
    if previous:
        record["consecutive_oom"] = dict(previous["consecutive_oom"])
    publish(target / "window.json", record)
    tasks = {task["id"]: task for task in read_json(EVAL / "tasks.json")["tasks"]}
    abort = previous.get("abort_reason") if previous else None
    results = []
    def dispatch_guard():
        assert_runtime(plan)
        verify_omp_binary(Path(bindings["omp_binary"]), plan)
        record["observations"].append(observer(bindings, plan, adapter.arm))
        record["endpoint_checks"].append(_endpoint_preflight(adapter, plan))
    try:
        campaign_path = root / "campaign.json"
        if pilot:
            deadline = time.monotonic() + 6 * 900 + 300
        else:
            if number == 1:
                publish(campaign_path, {"comparison_id": plan["comparison_id"], "plan_sha256": plan_digest(plan),
                                       "started_utc": utc_now(), "started_monotonic": time.monotonic()})
            campaign = read_json(campaign_path)
            if campaign.get("plan_sha256") != plan_digest(plan):
                raise ComparisonError("harness_modified")
            elapsed = time.monotonic() - campaign["started_monotonic"]
            utc_elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(campaign["started_utc"])).total_seconds()
            if elapsed < 0 or abs(elapsed - utc_elapsed) > 30:
                raise ComparisonError("host_state_drift")
            deadline = campaign["started_monotonic"] + plan["schedule"]["total_wall_seconds"]
        for task_id in row["task_order"]:
            if not abort:
                try:
                    if time.monotonic() >= deadline:
                        raise ComparisonError("comparison_wall_cap")
                    assert_runtime(plan)
                    verify_omp_binary(Path(bindings["omp_binary"]), plan)
                    observation = observer(bindings, plan, adapter.arm)
                    record["observations"].append(observation)
                    record["exclusive_gpu"] = True
                    if len(record["observations"]) == 1:
                        record.update(startup_ms=observation["startup_ms"], switch_ms=observation["switch_ms"], missing_reasons={})
                        if number == 1 and not pilot:
                            # The first operator switch predates this invocation; later switches
                            # are already inside the persistent monotonic campaign interval.
                            overhead = observation["switch_ms"] / 1000
                            campaign["started_monotonic"] -= overhead
                            campaign["started_utc"] = (datetime.fromisoformat(campaign["started_utc"]) - timedelta(seconds=overhead)).isoformat()
                            campaign["initial_window_switch_ms"] = observation["switch_ms"]
                            publish(campaign_path, campaign, exclusive=False)
                            deadline -= overhead
                    record["endpoint_checks"].append(_endpoint_preflight(adapter, plan))
                    if time.monotonic() >= deadline:
                        raise ComparisonError("comparison_wall_cap")
                except (ComparisonError, OSError) as exc:
                    abort = _safe_reason(exc)
            task = tasks[task_id]
            destination = target / task_id
            if abort:
                attempt = undispatched(plan, task, arm=adapter.arm, window=number, number=row["attempt_number"], reason=abort)
                publish(destination / "result.json", attempt)
            else:
                try:
                    attempt = run_comparison_attempt(adapter, task, row["attempt_number"], plan=plan,
                                                     window=number, directory=destination, batch_deadline=deadline,
                                                     dispatch_guard=dispatch_guard)
                except (ComparisonError, OSError, ValueError) as exc:
                    abort = _safe_reason(exc)
                    attempt = (read_json(destination / "incomplete.json") if (destination / "incomplete.json").is_file()
                               else undispatched(plan, task, arm=adapter.arm, window=number, number=row["attempt_number"], reason=abort, status="incomplete"))
                    attempt["abort_reason"] = abort
                    publish(destination / "result.json", attempt)
                if attempt["abort_reason"] in ABORT_REASONS:
                    abort = attempt["abort_reason"]
                streak = record["consecutive_oom"][adapter.arm]
                record["consecutive_oom"][adapter.arm] = streak + 1 if attempt["oom_observed"] else 0
                if record["consecutive_oom"][adapter.arm] >= 2:
                    abort = "consecutive_oom"
            results.append(attempt)
            record["attempts"].append({"task_id": task_id, "attempt_number": row["attempt_number"],
                                       "sha256": file_sha256(destination / "result.json")})
            publish(target / "window.json", record, exclusive=False)
        if not abort:
            try:
                assert_runtime(plan)
                record["observations"].append(observer(bindings, plan, adapter.arm))
            except (ComparisonError, OSError) as exc:
                abort = _safe_reason(exc)
        record.update(status="complete", ended_utc=utc_now(), abort_reason=abort)
        issues = validate_window(record, plan)
        if issues:
            raise ComparisonError("invalid window record")
        publish(target / "window.json", record, exclusive=False)
        if pilot:
            pilot_record = {"schema_version": 1, "record_type": "pilot", "comparison_id": plan["comparison_id"],
                            "arm": adapter.arm, "scored": False, "execution_boundary": bindings["execution_boundary"],
                            "pilot_contract_sha256": pilot_contract_digest(plan), "window_sha256": file_sha256(target / "window.json"),
                            "completed_attempts": len(results), "abort_reason": abort,
                            "verified_passes": sum(attempt["verified_pass"] for attempt in results)}
            publish(target / "pilot.json", pilot_record)
        return record
    except BaseException:
        record.update(status="incomplete", ended_utc=utc_now(), abort_reason="interrupted")
        publish(target / "window.json", record, exclusive=False)
        raise


def summarize(plan, root, *, reuse=False):
    windows, attempts = [], []
    for number in range(1, 7):
        directory = root / f"window-{number}"
        window = read_json(directory / "window.json")
        if validate_window(window, plan):
            raise ComparisonError("invalid window record")
        windows.append(window)
        for ref in window.get("attempts", []):
            path = directory / ref["task_id"] / "result.json"
            if file_sha256(path) != ref["sha256"]:
                raise ComparisonError("attempt result bytes changed")
            attempt = read_json(path)
            for item in attempt.get("artifacts", []) + attempt.get("transcripts", []):
                private = path.parent / item["path"]
                if private.is_symlink() or not private.resolve().is_relative_to(path.parent.resolve()) or file_sha256(private) != item["sha256"]:
                    raise ComparisonError("private artifact hash mismatch or path escape")
            attempts.append(attempt)
    summary = summarize_records(plan, windows, attempts)
    errors = validate_summary(summary, plan)
    if errors:
        raise ComparisonError("; ".join(errors))
    verifier = {"schema_version": 1, "record_type": "verifier_aggregate", "comparison_id": plan["comparison_id"],
                "plan_sha256": plan_digest(plan), "attempts": [
                    {"arm": row["arm"], "task_id": row["task_id"], "attempt_number": row["attempt_number"],
                     "attempt_sha256": sha256(canonical(row) + b"\n"), "verified_pass": row["verified_pass"]} for row in attempts]}
    for name, value in (("paired-summary.json", summary), ("verifier-aggregate.json", verifier)):
        path = root / name
        if reuse and path.is_file():
            if path.read_bytes() != canonical(value) + b"\n":
                raise ComparisonError("published summary or verifier aggregate changed")
        else:
            publish(path, value)
    return summary, windows, verifier


def export_reviewed(plan, summary, windows, verifier, destination, acknowledgement):
    if acknowledgement != "I reviewed all public comparison artifacts":
        raise ComparisonError("human review acknowledgement required for export")
    from omp_strata.comparison import _public_errors
    public = [("comparison-plan.json", plan), ("paired-summary.json", summary), ("verifier-aggregate.json", verifier)]
    public.extend((f"window-{row['window']}.json", row) for row in windows)
    for _, value in public:
        if _public_errors(value):
            raise ComparisonError("public export contains private data")
    if destination.exists():
        raise ComparisonError("refusing to overwrite an export")
    destination.mkdir(parents=True)
    for name, value in public:
        publish(destination / name, value)
    publish(destination / "export-review.json", {"schema_version": 1, "comparison_id": plan["comparison_id"],
                "reviewed_utc": utc_now(), "acknowledgement": acknowledgement,
                "files": {name: file_sha256(destination / name) for name, _ in public}})


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate identities without any model call")
    validate.add_argument("--plan", type=Path, required=True)
    validate.add_argument("--bindings", type=Path)
    validate.add_argument("--draft", action="store_true")
    init = commands.add_parser("init-plan", help="create a new immutable draft or freeze reviewed pilots")
    init.add_argument("--identities", type=Path, required=True)
    init.add_argument("--comparison-id")
    init.add_argument("--output", type=Path, required=True)
    init.add_argument("--finalize", action="store_true")
    init.add_argument("--pilot-root", type=Path)
    for name in ("pilot", "run-window"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--plan", type=Path, required=True)
        cmd.add_argument("--bindings", type=Path, required=True)
        if name == "pilot":
            cmd.add_argument("--arm", choices=ARMS, required=True)
        else:
            cmd.add_argument("--window", type=int, choices=range(1, 7), required=True)
    summary = commands.add_parser("summarize", help="validate all evidence and calculate paired results; no model calls")
    summary.add_argument("--plan", type=Path, required=True)
    summary.add_argument("--root", type=Path, required=True)
    summary.add_argument("--export", type=Path)
    summary.add_argument("--review-ack")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init-plan":
            identities = read_json(args.identities)
            if args.finalize:
                plan = identities
                if plan.get("state") != "draft" or not args.pilot_root:
                    raise ComparisonError("finalize requires the reviewed draft and both private pilot records")
                errors = validate_plan(plan, finalized=False, check_runtime=True)
                if errors:
                    raise ComparisonError("; ".join(errors))
                pilots = {}
                for arm in ARMS:
                    path = args.pilot_root / f"pilot-{arm}" / "pilot.json"
                    pilot = read_json(path)
                    if (pilot.get("arm") != arm or pilot.get("scored") is not False or pilot.get("completed_attempts") != 6
                            or pilot.get("abort_reason") or pilot.get("pilot_contract_sha256") != pilot_contract_digest(plan)
                            or file_sha256(path.parent / "window.json") != pilot.get("window_sha256")):
                        raise ComparisonError("pilot is incomplete, aborted or bound to a different plan/harness")
                    pilots[arm] = pilot
                if pilots["strata"]["execution_boundary"] != pilots["ninfer"]["execution_boundary"]:
                    raise ComparisonError("pilot execution boundaries differ")
                plan["state"] = "frozen"
                plan["pilot"] = {**{f"{arm}_sha256": file_sha256(args.pilot_root / f"pilot-{arm}" / "pilot.json") for arm in ARMS},
                                 "execution_boundary": pilots["strata"]["execution_boundary"]}
            else:
                if not args.comparison_id:
                    raise ComparisonError("--comparison-id is required for a new plan")
                plan = new_plan(identities, args.comparison_id)
            errors = validate_plan(plan, finalized=args.finalize)
            if errors:
                raise ComparisonError("; ".join(errors))
            publish(args.output, plan)
            print(json.dumps({"comparison_id": plan["comparison_id"], "state": plan["state"], "plan_sha256": plan_digest(plan)}))
            return 0
        plan = load_plan(args.plan, finalized=not getattr(args, "draft", False) and args.command != "pilot")
        if args.command == "validate":
            assert_runtime(plan)
            issues = validate_manifest(read_json(EVAL / "tasks.json"))
            if issues:
                raise ComparisonError("frozen_evaluation_modified")
            if args.bindings:
                bindings = load_bindings(args.bindings, plan)
                verify_omp_binary(Path(bindings["omp_binary"]), plan)
            print(json.dumps({"valid": True, "plan_sha256": plan_digest(plan)}))
            return 0
        if args.command == "summarize":
            summary, windows, verifier = summarize(plan, args.root, reuse=bool(args.export))
            if args.export:
                export_reviewed(plan, summary, windows, verifier, args.export, args.review_ack)
            print(json.dumps({"complete": summary["complete"], "execution_boundary": summary["execution_boundary"], "claims": summary["claims"]}))
            return 0 if summary["complete"] else 1
        bindings = load_bindings(args.bindings, plan)
        if args.command == "pilot":
            # A draft may leave identities unresolved for editing, but dispatch never may.
            check = dict(plan)
            check.update(state="frozen", pilot={"strata_sha256": "0" * 64, "ninfer_sha256": "0" * 64,
                                                "execution_boundary": bindings["execution_boundary"]})
            errors = validate_plan(check, finalized=True)
            if errors:
                raise ComparisonError("; ".join(errors))
            number = 1 if args.arm == "strata" else 2
        else:
            number = args.window
        from omp_strata.comparison_ompcfg import StrataArm, NInferArm
        adapter = (StrataArm if schedule()[number - 1]["arm"] == "strata" else NInferArm)(plan, bindings)
        result = run_window(plan, bindings, adapter, number, pilot=args.command == "pilot")
        print(json.dumps({"window": result["window"], "status": result["status"], "abort_reason": result["abort_reason"]}))
        return 0 if not result["abort_reason"] else 1
    except (ComparisonError, OSError, ValueError, KeyError, TypeError):
        # No user-supplied path, key, endpoint text or provider error can leak through the CLI.
        print("G25 refused: invalid, changed, unsafe or incomplete comparison evidence; inspect private records.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("G25 interrupted; the reserved window remains incomplete and cannot be resumed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
