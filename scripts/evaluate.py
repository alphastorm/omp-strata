#!/usr/bin/env python3
"""Run the frozen six-task evaluation; dry-run needs only Python and Git."""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import queue
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.support import (EVAL, apply_reference, canonical, digest, files, hashes, inventory,
                          materialize, run_bounded, run_verifier, terminate, validate_manifest, visible_status)


class EventCounts:
    """Count authoritative toolCall blocks, not repeated stream/turn/agent snapshots."""
    def __init__(self):
        self.calls = set()
        self.tool_calls = 0
        self.results = set()
        self.errors = Counter()
        self.output_tokens = 0
        self.output_usage_known = True
        self.assistants = 0
        self.completed = False
        self.calibration_observed = False
        self.oom = False

    def observe(self, event):
        if not isinstance(event, dict):
            self.errors["invalid_json_events"] += 1
            return
        if event.get("type") == "agent_end":
            self.completed = True
        if event.get("type") != "message_end":
            return
        message = event.get("message", {})
        if not isinstance(message, dict):
            self.errors["invalid_json_events"] += 1
            return
        role = message.get("role")
        if role == "assistant":
            self.assistants += 1
            usage = message.get("usage", {}).get("output")
            if isinstance(usage, (int, float)) and not isinstance(usage, bool) and usage >= 0:
                self.output_tokens += usage
            else:
                self.output_usage_known = False
            if message.get("stopReason") == "error":
                self.errors["stop_reason_error"] += 1
                self.oom |= bool(re.search(r"out of memory|bad_alloc|allocation failed", str(message), re.I))
            if message.get("stopReason") == "aborted":
                self.errors["stop_reason_aborted"] += 1
            for block in message.get("content", []):
                if not isinstance(block, dict) or block.get("type") != "toolCall":
                    continue
                self.tool_calls += 1
                call_id = block.get("id")
                if not isinstance(call_id, str) or not call_id:
                    self.errors["malformed_tool_ids"] += 1
                    call_id = f"invalid-{len(self.calls)}"
                if call_id in self.calls:
                    self.errors["duplicate_tool_ids"] += 1
                self.calls.add(call_id)
                if not isinstance(block.get("arguments"), dict):
                    self.errors["malformed_arguments"] += 1
        elif role == "toolResult":
            call_id = message.get("toolCallId")
            if not isinstance(call_id, str) or call_id not in self.calls:
                self.errors["orphan_results"] += 1
            else:
                self.results.add(call_id)
            text = "\n".join(block.get("text", "") for block in message.get("content", [])
                             if isinstance(block, dict) and block.get("type") == "text")
            if "CALIBRATION shift=23 width=11 tie=largest-sequence" in text and not message.get("isError"):
                self.calibration_observed = True
            if message.get("isError") and re.search(r"(?:invalid|malformed).*(?:argument|json)", text, re.I):
                self.errors["malformed_arguments"] += 1

    def summary(self):
        names = ["malformed_arguments", "orphan_results", "stop_reason_error", "stop_reason_aborted",
                 "duplicate_tool_ids", "malformed_tool_ids", "invalid_json_events"]
        return {**{name: self.errors[name] for name in names},
                "calls_without_results": len(self.calls - self.results)}


def run_phase(argv, *, workspace, env, directory, phase, deadline, budget, counts):
    """Stream stdout through a bounded queue so the wall/tool/output caps can interrupt OMP."""
    events_path = directory / f"phase-{phase}.events.jsonl"
    stderr_path = directory / f"phase-{phase}.stderr.txt"
    messages = queue.Queue(maxsize=64)
    stop_reader = threading.Event()
    bytes_seen = 0
    reason = None
    start = time.monotonic()
    counts.completed = False
    with events_path.open("wb") as output, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(argv, cwd=workspace, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=stderr, start_new_session=os.name != "nt")

        def read_lines():
            try:
                while not stop_reader.is_set():
                    line = process.stdout.readline(budget["max_event_bytes"] + 1)
                    while not stop_reader.is_set():
                        try:
                            messages.put(line, timeout=0.1)
                            break
                        except queue.Full:
                            continue
                    if not line:
                        break
            except (OSError, ValueError):
                pass

        reader = threading.Thread(target=read_lines, daemon=True)
        reader.start()
        try:
            ended = False
            while not ended:
                if time.monotonic() >= deadline:
                    reason = "timeout"
                    break
                if os.fstat(stderr.fileno()).st_size > budget["max_stderr_bytes"]:
                    reason = "stderr_output_cap"
                    break
                try:
                    line = messages.get(timeout=min(0.1, max(0.001, deadline - time.monotonic())))
                except queue.Empty:
                    if process.poll() is not None and not reader.is_alive():
                        break
                    continue
                if not line:
                    ended = True
                    continue
                bytes_seen += len(line)
                if bytes_seen > budget["max_event_bytes"]:
                    output.write(line[:max(0, budget["max_event_bytes"] - (bytes_seen - len(line)))])
                    reason = "event_output_cap"
                    break
                output.write(line)
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    counts.errors["invalid_json_events"] += 1
                    continue
                counts.observe(event)
                if counts.tool_calls > budget["tool_calls"]:
                    reason = "tool_call_cap"
                    break
                if counts.output_tokens > budget["total_output_tokens"]:
                    reason = "token_output_cap"
                    break
            if reason:
                terminate(process)
            else:
                try:
                    process.wait(timeout=max(0.01, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    reason = "timeout"
                    terminate(process)
        finally:
            stop_reader.set()
            if process.poll() is None:
                terminate(process)
            process.stdout.close()
            reader.join(timeout=2)
    if process.returncode and time.monotonic() >= deadline - 1:
        reason = reason or "timeout"
    if stderr_path.stat().st_size > budget["max_stderr_bytes"]:
        with stderr_path.open("r+b") as stream:
            stream.truncate(budget["max_stderr_bytes"])
        reason = reason or "stderr_output_cap"
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    counts.oom |= bool(re.search(r"out of memory|bad_alloc|allocation failed", stderr_text, re.I))
    return {"phase": phase, "exit_code": process.returncode, "abort_reason": reason,
            "completed": counts.completed, "wall_ms": round((time.monotonic() - start) * 1000, 3),
            "events": str(events_path), "stderr": str(stderr_path), "event_bytes": min(bytes_seen, budget["max_event_bytes"])}


def snapshot(workspace):
    paths = files(workspace)
    if len(paths) > 4096 or sum(path.stat().st_size for path in paths) > 8 * 1024 * 1024:
        raise ValueError("unsafe workspace: exceeds file-count or byte ceiling")
    return {path.relative_to(workspace).as_posix(): path.read_bytes() for path in paths}


def save_changes(before, workspace, directory):
    after = snapshot(workspace)
    patch = []
    changes = []
    for name in sorted(before.keys() | after.keys()):
        old, new = before.get(name), after.get(name)
        if old == new:
            continue
        changes.append({"file": name, "before": digest(old) if old is not None else None,
                        "after": digest(new) if new is not None else None})
        if new is not None:
            target = directory / "changed-files" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(new)
        try:
            old_text = (old or b"").decode("utf-8").splitlines(keepends=True)
            new_text = (new or b"").decode("utf-8").splitlines(keepends=True)
            patch.extend(difflib.unified_diff(old_text, new_text,
                         fromfile=f"a/{name}" if old is not None else "/dev/null",
                         tofile=f"b/{name}" if new is not None else "/dev/null"))
        except UnicodeDecodeError:
            patch.append(f"Binary change: {name}\n")
    (directory / "candidate.patch").write_text("".join(patch), encoding="utf-8", newline="\n")
    (directory / "changes.json").write_bytes(canonical(changes) + b"\n")


def dry_run(manifest):
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("; ".join(errors))
    reports = []
    with tempfile.TemporaryDirectory(prefix="eval-dry-") as temporary:
        for task in manifest["tasks"]:
            workspace = materialize(task, Path(temporary) / task["id"])
            before = visible_status(workspace)
            seed = run_verifier(task, workspace)
            apply_reference(task, workspace)
            solved = run_verifier(task, workspace)
            passed = (not seed["verdict"]["passed"] and seed["returncode"] == 1 and
                      solved["verdict"]["passed"] and before == task["preexisting_visible_tests"])
            report = {"task": task["id"], "passed": passed, "seed_passed": seed["verdict"]["passed"],
                      "reference_passed": solved["verdict"]["passed"], "visible_seed": before,
                      "workspace_size": task["workspace_size"]}
            if not passed:
                report.update(seed_details=seed["verdict"], reference_details=solved["verdict"])
            reports.append(report)
            print(json.dumps(report))
    return 0 if all(report["passed"] for report in reports) else 1


def run_attempt(task, number, *, layout, binary, key, directory, work, between_phases, batch_deadline):
    from omp_strata import ompcfg
    budget = task["budget"]
    directory.mkdir(parents=True)
    started = time.monotonic()
    deadline = min(batch_deadline, started + budget["wall_seconds"])
    candidate = work / f"{task['id']}-{number}"
    workspace = materialize(task, candidate / "workspace")
    before = snapshot(workspace)
    client = replace(layout, root=candidate / "client")
    config = ompcfg.install_profile_config(client)
    env = ompcfg.isolated_env(client, api_key=key)
    sessions = directory / "sessions"
    sessions.mkdir()
    counts = EventCounts()
    phases = []
    abort = None
    unsafe = False
    hook = None
    expected_inventory = runtime_identity()
    for phase in range(1, task["phases"] + 1):
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
        phase_result = run_phase(ompcfg.omp_argv(client, extra=extra, binary=binary), workspace=workspace,
                                 env=env, directory=directory, phase=phase, deadline=deadline - 30,
                                 budget=budget, counts=counts)
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
            if between_phases:
                hook = run_bounded(shlex.split(between_phases), cwd=workspace,
                                   env=env, timeout=min(120, max(0, deadline - time.monotonic() - 30)))
                (directory / "between-phases.txt").write_text(hook["stdout"], encoding="utf-8")
                if hook["returncode"] != 0 or hook["timed_out"] or hook["output_limited"]:
                    abort = "between_phases_failure"
                    break
    try:
        save_changes(before, workspace, directory)
    except (OSError, ValueError):
        unsafe = True
        abort = "unsafe_workspace"
    if runtime_identity() != expected_inventory:
        unsafe, abort = True, "frozen_evaluation_modified"
        verifier = {"verdict": {"task": task["id"], "passed": False,
                               "details": {"error": "refusing modified verifier"}}, "returncode": None}
    elif unsafe:
        verifier = {"verdict": {"task": task["id"], "passed": False,
                               "details": {"error": "unsafe workspace"}}, "returncode": None}
    else:
        verifier = run_verifier(task, workspace, timeout=min(30, max(0, deadline - time.monotonic())))
    elapsed = (time.monotonic() - started) * 1000
    timed_out = abort == "timeout" or elapsed > budget["wall_seconds"] * 1000 or verifier.get("timed_out", False)
    transcript_paths = sorted(str(path) for path in sessions.rglob("*.jsonl"))
    errors = counts.summary()
    compactions = 0
    for path in transcript_paths:
        try:
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                compactions += entry.get("type") == "compaction"
        except (OSError, ValueError):
            errors["invalid_transcript"] = errors.get("invalid_transcript", 0) + 1
    if not transcript_paths:
        errors["missing_transcript"] = 1
    passed = (verifier["verdict"]["passed"] and not abort and not timed_out and not any(errors.values())
              and len(phases) == task["phases"])
    result = {"task": task["id"], "attempt": number, "verified_pass": bool(passed),
              "verifier_pass": verifier["verdict"]["passed"], "timeout": timed_out,
              "abort_reason": abort, "tool_calls": counts.tool_calls, "protocol_errors": errors,
              "task_wall_ms": round(elapsed, 3), "omp_exit_code": phases[-1]["exit_code"] if phases else None,
              "transcript_path": transcript_paths[0] if len(transcript_paths) == 1 else None,
              "transcript_paths": transcript_paths, "phases": phases, "compactions": compactions,
              "reported_output_tokens": counts.output_tokens if counts.output_usage_known else None,
              "oom_observed": counts.oom, "unsafe_workspace": unsafe,
              "verifier": verifier["verdict"], "verifier_exit_code": verifier["returncode"],
              "between_phases_exit_code": hook["returncode"] if hook else None,
              "config_sha256": config["config_sha256"], "models_sha256": config["models_sha256"],
              "workspace": str(workspace)}
    (directory / "result.json").write_bytes(canonical(result) + b"\n")
    return result


def runtime_identity():
    return {**inventory(), "eval/tasks.json": digest((EVAL / "tasks.json").read_bytes())}


def undispatched(task, attempt, reason):
    return {"task": task["id"], "attempt": attempt, "verified_pass": False, "verifier_pass": False,
            "not_started": True, "abort_reason": reason, "timeout": reason == "batch_wall_cap",
            "tool_calls": None, "protocol_errors": None, "task_wall_ms": None, "omp_exit_code": None,
            "transcript_path": None, "transcript_paths": [], "verifier_exit_code": None}


def real_run(args, manifest):
    try:
        from omp_strata import ompcfg
        from omp_strata.layout import Layout, host_platform
        from omp_strata.lifecycle import read_key
        from omp_strata.profile import load
    except ImportError as exc:
        raise ValueError("real mode requires omp_strata.ompcfg and the completed lifecycle modules") from exc
    if not all((args.root, args.profile, args.out)):
        raise ValueError("real mode requires --root, --profile, and --out")
    if args.attempts != 3 and not args.pilot:
        raise ValueError("a scored batch requires exactly three attempts per task")
    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    if not out.is_relative_to(root) or out == root or root.is_relative_to(ROOT):
        raise ValueError("use a dedicated integration root outside the repository and --out beneath that root")
    if out.exists():
        raise ValueError("--out must be new; earlier attempts are never overwritten")
    drift = validate_manifest(manifest)
    if drift and not args.pilot:
        raise ValueError("scored run refused: " + "; ".join(drift))
    profile = load(Path(args.profile))
    if profile.data["omp"]["max_tokens"] != manifest["tasks"][0]["budget"]["max_output_tokens_per_response"]:
        raise ValueError("profile output cap differs from the frozen evaluation cap")
    layout = Layout(root=root, profile=profile)
    key = os.environ.get("STRATA_API_KEY") or read_key(layout)
    if not key.strip():
        raise ValueError("missing/blank STRATA_API_KEY")
    binary = layout.omp_binary()
    artifact = profile.omp_artifact(host_platform())
    from omp_strata.common import sha256_file
    if not binary.is_file() or binary.stat().st_size != artifact["bytes"] or sha256_file(binary) != artifact["sha256"]:
        raise ValueError("pinned stock OMP binary is absent or mismatched; fetch it into this integration root")
    out.mkdir(parents=True)
    run_id = out.name
    work = layout.work / ("eval-" + run_id)
    if work.exists():
        raise ValueError("evaluation workspace batch already exists")
    work.mkdir(parents=True)
    start = time.monotonic()
    frozen_identity = runtime_identity()
    batch_deadline = start + manifest["batch_wall_seconds"]
    results = []
    stopped = None
    oom_streak = 0
    schedule = [(task, attempt) for attempt in range(1, args.attempts + 1) for task in manifest["tasks"]]
    metadata = {"pilot": args.pilot, "scored": not args.pilot, "profile": profile.id,
                "profile_sha256": profile.fingerprint, "manifest_sha256": digest(canonical(manifest)),
                "harness_drift": drift, "scheduled_attempts": len(schedule),
                "order": [[task["id"], attempt] for task, attempt in schedule],
                "isolation_boundary": "isolated environment/worktree; NOT an OS sandbox; use a restricted account/container",
                "between_phases_hook": bool(args.between_phases)}
    (out / "batch.json").write_bytes(canonical(metadata) + b"\n")
    with (out / "attempts.jsonl").open("x", encoding="utf-8") as stream:
        for task, attempt in schedule:
            if time.monotonic() >= batch_deadline:
                stopped = stopped or "batch_wall_cap"
            if not stopped and runtime_identity() != frozen_identity:
                stopped = "frozen_evaluation_modified"
            if stopped:
                result = undispatched(task, attempt, stopped)
            else:
                attempt_start = time.monotonic()
                try:
                    result = run_attempt(task, attempt, layout=layout, binary=binary, key=key,
                                         directory=out / f"{task['id']}-{attempt}", work=work,
                                         between_phases=args.between_phases, batch_deadline=batch_deadline)
                except (OSError, ValueError, RuntimeError) as exc:
                    result = undispatched(task, attempt, "harness_error")
                    result.update(not_started=False, error_type=type(exc).__name__,
                                  error=str(exc).replace(key, "[redacted]"),
                                  task_wall_ms=round((time.monotonic() - attempt_start) * 1000, 3))
                    stopped = "harness_error"
                oom_streak = oom_streak + 1 if result.get("oom_observed") else 0
                if result.get("unsafe_workspace"):
                    stopped = "unsafe_workspace"
                if oom_streak >= 2:
                    stopped = "repeated_oom"
            results.append(result)
            stream.write(json.dumps(result) + "\n")
            stream.flush()
            print(json.dumps({key: result.get(key) for key in ("task", "attempt", "verified_pass", "abort_reason", "task_wall_ms")}))
    completed = sum(item["verified_pass"] for item in results)
    summary = {**metadata, "completion_count": completed, "denominator": len(schedule),
               "completion_rate": completed / len(schedule), "batch_abort_reason": stopped,
               "total_wall_ms": round((time.monotonic() - start) * 1000, 3),
               "failed_attempt_wall_ms": round(sum(item.get("task_wall_ms") or 0 for item in results
                                                   if not item["verified_pass"]), 3),
               "success_only_wall_ms": [item["task_wall_ms"] for item in results if item["verified_pass"]],
               "cold_startup_ms": None, "peak_ram_bytes": None, "peak_vram_bytes": None,
               "cache_reuse": None, "actual_tokenized_long_context_input": None}
    (out / "summary.json").write_bytes(canonical(summary) + b"\n")
    print(json.dumps({key: summary[key] for key in ("pilot", "completion_count", "denominator", "completion_rate", "batch_abort_reason")}))
    return 0 if completed == len(schedule) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--profile")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--out")
    parser.add_argument("--pilot", action="store_true", help="non-scored pilot; permits manifest drift, recorded in batch identity")
    parser.add_argument("--between-phases", help="shell-style argv string, executed without a shell between continuation phases")
    args = parser.parse_args(argv)
    try:
        if args.attempts < 1:
            raise ValueError("--attempts must be positive")
        manifest = json.loads((EVAL / "tasks.json").read_text(encoding="utf-8"))
        return dry_run(manifest) if args.dry_run else real_run(args, manifest)
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
