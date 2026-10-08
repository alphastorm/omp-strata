#!/usr/bin/env python3
"""Publish a locally pulled requalify run without contacting a host.

Only measured gates are generated. Baseline, host-free and not-applicable receipts
remain the operator's responsibility; qualification/publication decisions are not changed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata.common import atomic_write_json, is_sha256, read_json, sha256_bytes, sha256_file
from omp_strata.layout import Layout
from omp_strata.profile import load
from omp_strata.receipts import REPO as CONTRACT_REPO, gate_inventory, make_receipt, schema_errors, update_ledger, write_receipt
from scripts.check_public_hygiene import scan
from scripts.verify_release import verify

REPO = Path(__file__).resolve().parents[1]
# The first step supplies the receipt name. Both cancellation/compaction probes
# belong to a single gate; a missing companion is not a passing combined gate.
GATE_STEPS = {
    "G10": ("g10",), "G11": ("tracer",), "G12": ("g12",), "G13": ("g13",),
    "G14": ("g14", "g14q"), "G15": ("g15",), "G16": ("g16",),
    "G17": ("g17",), "G18": ("g18l", "g18"), "G19": ("g19",),
    "G20": ("g20",), "G21": ("g21",), "G24": ("eval", "pilot"),
    "G26": ("quickstart",),
}
ROW_FIELDS = ("step", "rc", "run_id", "pass_observed", "started_utc", "seconds",
              "tests_pass_after", "error")


class PublicationError(ValueError):
    """A refusal whose message contains no private input."""


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def json_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from json_strings(item)


def private_denylist() -> list[str]:
    configured = os.environ.get("OMP_STRATA_HYGIENE_DENYLIST")
    path = Path(configured) if configured else Path.home() / ".config/omp-strata/hygiene-denylist.txt"
    if not path.is_file():
        if configured:
            raise PublicationError("configured hygiene denylist unavailable")
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


class Scrubber:
    def __init__(self, root_path: str, private=(), denylist=()):
        if not root_path.strip() or any(not term.strip() for term in private):
            raise PublicationError("root path and private terms must be nonblank")
        slash = re.sub(r"\\+", "/", root_path).rstrip("/")
        # A path may be in JSON inside a JSON string. Matching separator runs
        # covers raw, escaped, forward-slash and mixed Windows spellings.
        self.root_pattern = re.compile(r"[\\/]+".join(re.escape(part) for part in slash.split("/")), re.I)
        self.private = tuple(private)
        self.denylist = tuple(denylist) + self.private

    def check(self, data: bytes, *, is_json=True) -> None:
        texts = [data.decode("utf-8")]
        if is_json:
            texts.extend(json_strings(json.loads(data)))
        for text in texts:
            if scan(text.encode(), self.denylist) or self.root_pattern.search(text):
                raise PublicationError("public hygiene refused content (matches withheld)")

    def scrub(self, data: bytes) -> bytes:
        text = data.decode("utf-8-sig")
        text = self.root_pattern.sub("<root>", text)
        for term in sorted(self.private, key=len, reverse=True):
            text = re.sub(re.escape(term), "<redacted>", text, flags=re.IGNORECASE)
        result = text.encode("utf-8")
        # Checking decoded strings also catches escaped private terms and addresses.
        self.check(result)
        return result


def number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def at(value, path: str):
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
    return value


def measured(values, operation):
    values = [value for value in values if number(value)]
    return operation(values) if values else None


def row_time(row: dict) -> str:
    value = datetime.fromisoformat(row["started_utc"].replace("Z", "+00:00"))
    if value.utcoffset() != timedelta(0):
        raise PublicationError("runner timestamps must be UTC")
    seconds = row.get("seconds", 0)
    if not number(seconds) or seconds < 0:
        raise PublicationError("invalid runner elapsed time")
    return (value + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def stamp(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%Y%m%dT%H%M%SZ")


def safe_name(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise PublicationError("unsafe public filename or label")
    return value


def public_row(row: dict) -> dict:
    # argv/cwd and raw stdout/stderr are not publication evidence.
    return {key: row[key] for key in ROW_FIELDS if key in row}


def row_pass(row: dict) -> bool:
    return type(row.get("rc")) is int and row["rc"] == 0 and row.get("pass_observed") is True


def resource_values(result: dict) -> dict:
    engines = [item for item in result.get("server_tree_memory", [])
               if item.get("process", "").lower() == "strata.exe"]
    samples = result.get("gate_results", [])
    return {
        "engine_peak_working_set": measured((item.get("peak_working_set") for item in engines), max),
        "engine_peak_private_commit": measured((item.get("peak_private") for item in engines), max),
        "gpu_memory_used_peak": measured((item.get("peak_gpu_used_mib") for item in samples), max),
        "min_available_ram_serving": measured((item.get("min_available_ram_bytes") for item in samples), min),
        "disk_root_total": result.get("disk_total_bytes"),
        "completed_requests_logged": result.get("log_scan", {}).get("completed_requests_logged",
                                                                    at(result, "log_scan.completed_requests_done_lines")),
        "first_ready": at(result, "startup.first_start.ready_s"),
        "current_ready": result.get("current_ready_s"),
    }


def resource_complete(result: dict) -> bool:
    values = resource_values(result)
    required = ("engine_peak_working_set", "engine_peak_private_commit", "gpu_memory_used_peak",
                "min_available_ram_serving", "disk_root_total", "current_ready")
    failures = ("engine_error_lines", "found_dead_and_restarted", "requests_ended_disconnect",
                "requests_ended_error", "stopped_mid_request")
    return (all(number(values[key]) and values[key] >= 0 for key in required)
            and all(number(at(result, "engine_events." + key)) for key in failures))


def evaluation_complete(batch: dict, tasks: list[str]) -> bool:
    summary, attempts, metadata = batch["summary"], batch["attempts"], batch["batch"]
    expected = [(task, attempt) for attempt in range(1, 4) for task in tasks]
    actual = [(item.get("task"), item.get("attempt")) for item in attempts]
    # A failed task is evidence, not a failed reporting gate. Undispatched entries
    # or missing verifier outcomes do not establish the six-by-three experiment.
    return bool(len(tasks) == 6 and actual == expected
                and metadata.get("order", [list(pair) for pair in expected]) == [list(pair) for pair in expected]
                and summary.get("scored") is True and summary.get("pilot") is False
                and metadata.get("scored") is True and metadata.get("pilot") is False
                and metadata.get("scheduled_attempts") == len(expected)
                and not summary.get("harness_drift") and not metadata.get("harness_drift")
                and summary.get("denominator") == len(expected)
                and summary.get("scheduled_attempts") == len(expected)
                and summary.get("completion_count") == sum(item.get("verified_pass") is True for item in attempts)
                and summary.get("completion_rate") == summary.get("completion_count") / len(expected)
                and all(not item.get("not_started") and isinstance(item.get("verified_pass"), bool)
                        and type(item.get("attempt")) is int
                        and isinstance(item.get("verifier_pass"), bool)
                        and at(item, "verifier.passed") is item.get("verifier_pass")
                        and (not item["verified_pass"] or (item["verifier_pass"] and not item.get("abort_reason") and not item.get("timeout")))
                        and isinstance(item.get("timeout"), bool) for item in attempts))


def gate_details(gid: str, result: dict, companion: dict, host_label: str,
                 profile, g10: dict) -> tuple[str, list[dict], list[str]]:
    metrics, statements, limitations = [], [], []
    boundary = "real_host " + host_label

    def metric(name, value, unit, method="server_reported", where=None):
        metrics.append(dict(name=name, value=value if number(value) else None, unit=unit,
                            boundary=where or boundary, method=method if number(value) else "unavailable"))

    def fields(label, source, paths):
        parts = []
        for title, path in paths:
            value = at(source, path)
            rendered = "unavailable" if value is None else json.dumps(value, ensure_ascii=False, sort_keys=True)
            parts.append(f"{title}: {rendered}")
        statements.append(label + ": " + "; ".join(parts) + ".")

    def direct(source, specs):
        for name, path, unit, method in specs:
            metric(name, at(source, path), unit, method)

    if gid == "G10":
        direct(result, [("gpu_memory_used_serving", "gpu.memory_used_mib", "MiB", "resource_sampler"),
                        ("gpu_memory_total", "gpu.memory_total_mib", "MiB", "resource_sampler"),
                        *[(key, key, "bytes", "resource_sampler") for key in
                          ("ram_total_bytes", "ram_available_bytes", "commit_limit_bytes", "commit_available_bytes", "disk_free_bytes")],
                        ("deep_verification_wall", "deep_artifact_verification.seconds", "s", "monotonic_wall_clock"),
                        ("gpu_display_clients", "gpu_display_clients", "count", "resource_sampler")])
        fields("Serving identity and preflight", result, [("build", "build_info"), ("status", "status"),
               ("ready", "runtime_ready"), ("context", "n_ctx"), ("vision", "modalities.vision"),
               ("runtime problems", "runtime_problems"), ("deep pinned verification", "deep_artifact_verification"),
               ("owned listener", "listener_owned"), ("loopback only", "listener_loopback_only"),
               ("exclusive GPU", "gpu_exclusive"), ("compute PIDs owned", "gpu_compute_pids_owned"),
               ("GPU", "gpu"), ("foreign compute processes", "gpu_foreign_compute_processes"),
               ("display clients", "gpu_display_clients"), ("available RAM bytes", "ram_available_bytes"),
               ("available commit bytes", "commit_available_bytes")])
        limitations.append("Serving-state RAM and GPU observations include Strata itself, not pre-start headroom.")
        if result.get("pip_freeze_sha256") is None:
            limitations.append("This probe has no pip-freeze digest; the install record is a separate identity boundary.")
    elif gid == "G11":
        runs = result.get("runs", [])
        metric("protocol_passes", sum(r.get("protocol_pass") is True for r in runs), "count", "external_verifier")
        metric("task_passes", sum(r.get("task_pass") is True for r in runs), "count", "external_verifier")
        for index, run in enumerate(runs, 1):
            metric(f"run{index}_turn1_wall", at(run, "timing_ms.turn1_wall"), "ms", "monotonic_wall_clock")
            metric(f"run{index}_tool_calls", at(run, "protocol.tool_calls"), "count", "external_verifier")
            fields(f"Tracer run {index}", run, [("protocol pass", "protocol_pass"), ("task pass", "task_pass"),
                   ("tool calls", "protocol.tool_calls"), ("unique IDs", "protocol.ids_well_formed_unique"),
                   ("object arguments", "protocol.arguments_are_objects"), ("all results", "protocol.all_calls_have_results"),
                   ("original nonce recalled", "task.turn2_has_original_nonce"),
                   ("rotated nonce recalled", "task.turn2_has_rotated_nonce"), ("continuation tool calls", "protocol.turn2_tool_calls")])
    elif gid == "G12":
        metric("continuations_with_reuse", result.get("continuations_with_reuse"), "count")
        reused = []
        for index, run_id in enumerate(result.get("runs", []), 1):
            requests = result.get("per_request", {}).get(run_id, [])
            reuse = measured((r.get("cacheRead") for r in requests), sum)
            prompts = measured((r["cacheRead"] + r["input"] for r in requests
                                if number(r.get("cacheRead")) and number(r.get("input"))), sum)
            metric(f"run{index}_engine_reused_tokens", reuse, "tokens")
            metric(f"run{index}_engine_prompt_tokens", prompts, "tokens")
            reused.append(reuse)
        metric("engine_reused_tokens", measured(reused, sum), "tokens")
        fields("Controlled continuations", result, [("total", "continuations"), ("with prefix reuse", "continuations_with_reuse"),
               ("protocol and task outcomes", "run_results")])
        limitations.append("Live prefix reuse only; engine restart requires re-prefill.")
    elif gid == "G13":
        for name in ("non_loopback_events", "events_attributed"):
            metric("etw_events_attributed" if name == "events_attributed" else name,
                   at(result, "egress_probe." + name), "count", "external_verifier", "ETW kernel-network bounded probe")
        for key in ("dead_endpoint", "wrong_key"):
            metric(key + "_failure_wall", at(result, key + "_omp.wall_ms"), "ms", "monotonic_wall_clock")
        fields("Authentication and routing", result, [("protected routes enforced", "protected_routes_enforced"),
               ("correct key accepted", "protected_routes_correct_key_ok"), ("absent opt-in routes", "absent_routes"),
               ("CORS preflight", "cors_preflight"), ("launcher refusals", "launcher_refusals"),
               ("wrong-key client", "wrong_key_omp"), ("dead-endpoint client", "dead_endpoint_omp"),
               ("ETW probe", "egress_probe"), ("route census", "route_census"), ("settings unchanged", "settings_unchanged")])
        limitations.append("ETW is a bounded observation, not a firewall or OS sandbox; loopback discovery is not external egress.")
    elif gid == "G14":
        direct(result, [("generating_cancel_to_idle", "client_killed_while_generating.server_idle_after_ms", "ms", "monotonic_wall_clock"),
                        ("queued_drop_then_active_drop_to_idle", "queued_client_cancelled.idle_after_ms", "ms", "monotonic_wall_clock")])
        followups = [at(companion, scenario + "." + request) for scenario in
                     ("queued_drop_then_generating_drop", "queued_drop_generating_completes")
                     for request in ("first_long_request", "second_long_request")]
        metric("g14q_long_requests_after_queued_disconnect_ok", sum(isinstance(r, dict) and r.get("status") == 200 for r in followups),
               "count", "external_verifier")
        fields("Cancellation and side effects", result, [("generating client", "client_killed_while_generating"),
               ("queued cancellation", "queued_client_cancelled"), ("append after resume", "side_effect_then_client_loss"),
               ("failed-tool recovery", "failed_tool_then_valid_turn")])
        fields("Queued-drop regressions", companion, [("control", "control_drop_generating_only"),
               ("active completion", "queued_drop_generating_completes"), ("active drop", "queued_drop_then_generating_drop")])
    elif gid == "G15":
        for key in ("idle_kill", "mid_generation_kill"):
            direct(result, [(key + "_recall_wall", key + ".recall_wall_ms", "ms", "monotonic_wall_clock"),
                            (key + "_prompt_tokens", key + ".engine_records.0.prompt_tokens", "tokens", "server_reported"),
                            (key + "_prompt_ms", key + ".engine_records.0.prompt_ms", "ms", "server_reported")])
        fields("Surviving-client recovery", result, [("same session", "same_session"), ("idle kill", "idle_kill"),
               ("mid-generation kill", "mid_generation_kill"), ("explicit client abort", "client_abort_control")])
        limitations.append("Transcript replay rebuilds live state; durable engine-state restoration is not claimed.")
    elif gid == "G16":
        direct(result, [("server_restart_ready", "server_restart.ready_s", "s", "monotonic_wall_clock"),
                        ("client_restart_recall", "t2_client_restart.wall_ms", "ms", "monotonic_wall_clock"),
                        ("combined_restart_recall", "t3_client_and_server_restart.wall_ms", "ms", "monotonic_wall_clock"),
                        ("combined_restart_prefill", "t3_client_and_server_restart.engine_records.0.prompt_ms", "ms", "server_reported")])
        runs = ("append runs", "append_runs") if "append_runs" in result else ("append calls", "append_calls")
        fields("Session resume", result, [("client-only", "t2_client_restart"), ("combined restart", "t3_client_and_server_restart"),
               ("server ready seconds", "server_restart.ready_s"), runs, ("remaining log lines", "log_lines")])
        limitations.append("Restart readiness and transcript replay are distinct timing boundaries.")
    elif gid == "G17":
        direct(result, [("cold_prefill", "boundary.cold_prefill_ms", "ms", "server_reported"),
                        ("boundary_prompt_tokens", "boundary.prompt_tokens", "tokens", "server_reported"),
                        ("near_limit_peak_prompt_tokens", "near_limit.peak_prompt_tokens", "tokens", "server_reported"),
                        ("max_wire_prompt_plus_cap", "near_limit.max_wire_prompt_plus_cap", "tokens", "calculated"),
                        ("near_limit_cold_prefill", "near_limit.engine_requests.0.prompt_ms", "ms", "server_reported"),
                        ("near_limit_task_wall", "near_limit.wall_ms", "ms", "monotonic_wall_clock")])
        tokens, elapsed = at(result, "boundary.prompt_tokens"), at(result, "boundary.cold_prefill_ms")
        metric("cold_prefill_rate", tokens * 1000 / elapsed if number(tokens) and number(elapsed) and elapsed > 0 else None,
               "tokens/s", "calculated")
        fields("Context boundary", result, [("context", "context"), ("slack", "ctx_slack"), ("fit and overflow", "boundary"),
               ("near-limit prompt peak", "near_limit.peak_prompt_tokens"), ("wire prompt plus cap", "near_limit.max_wire_prompt_plus_cap"),
               ("facts retained", "near_limit.facts_written"), ("tool follow-up", "near_limit.tool_follow_up"),
               ("compactions", "near_limit.compactions"), ("client overflow", "omp_overflow")])
        limitations.append("Output caps reserve budgets; they do not count generated output tokens.")
    elif gid == "G18":
        for prefix, source in (("production", result), ("reduced", companion)):
            metric(prefix + "_compactions", source.get("compactions"), "count", "external_verifier")
            metric(prefix + "_compaction_tokens_before", measured(source.get("compaction_tokens_before", []), max), "tokens")
            fields(prefix.capitalize() + " compaction", source, [("count", "compactions"), ("tokens before", "compaction_tokens_before"),
                   ("tokens after", "compaction_tokens_after"), ("final verification", "final"),
                   ("missing tool results", "calls_without_results"), ("providers", "providers")])
        metric("production_compaction_tokens_after", at(result, "compaction_tokens_after.0"), "tokens")
        metric("peak_engine_prompt_tokens", result.get("peak_engine_prompt_tokens"), "tokens")
        metric("long_session_wall", result.get("wall_s"), "s", "monotonic_wall_clock")
        fields("Production workload", result, [("configuration", "configuration"), ("document turns", "doc_turns"),
               ("engine prompt peak", "peak_engine_prompt_tokens")])
        fields("Reduced configuration", companion, [("threshold", "threshold_tokens"), ("keep recent", "keep_recent_tokens")])
        limitations.append("Reported compaction tokens and engine-tokenized prompt counts use different boundaries.")
    elif gid == "G19":
        requests = at(result, "interleave.per_request_a") or []
        metric("shared_prefix_reused", measured((r.get("cacheRead") for r in requests if r.get("cacheRead")), min), "tokens")
        metric("interleaved_continuation_uncached_tokens", at(result, "interleave.per_request_a.2.input"), "tokens")
        fields("Interleaving", result, [("A continuation", "interleave.a2_correct"), ("B continuation", "interleave.b2_correct"),
               ("resumed A", "interleave.a3_resume_correct"), ("branch isolation", "branch")])
        fields("Controlled A continuation", result, [("reused tokens", "interleave.per_request_a.2.cacheRead"),
               ("uncached tokens", "interleave.per_request_a.2.input")])
        limitations.append("Single-user correctness only; no hostile-tenant isolation claim.")
    elif gid == "G20":
        direct(result, [("restart_ready", "restart.ready_s", "s", "monotonic_wall_clock"),
                        ("restart_wall", "restart.wall_s", "s", "monotonic_wall_clock"),
                        ("gpu_memory_after_stop", "gpu_after_stop.memory_used_mib", "MiB", "resource_sampler")])
        fields("Lifecycle", result, [("port released", "port_released"), ("orphans", "orphans_after_stop"),
               ("repeated stop", "repeat_stop"), ("second start refusal", "second_start_refused"), ("restart", "restart"),
               ("smoke nonce", "smoke_after_restart"), ("GPU after stop", "gpu_after_stop"),
               ("scheduled task states unchanged", "scheduled_task_states_unchanged"), ("unrelated host state", "host_state_after")])
        limitations.append("Scheduled task names are private; only their recorded counts and equality are exported.")
    elif gid == "G21":
        for name, value in resource_values(result).items():
            unit = "s" if name in ("first_ready", "current_ready") else "MiB" if name == "gpu_memory_used_peak" else "count" if name == "completed_requests_logged" else "bytes"
            metric(name, value, unit, "monotonic_wall_clock" if unit == "s" else "resource_sampler")
        metric("expert_load_rate", None, "GB/s", "unavailable")
        fields("Resource and failure record", result, [("engine lifetime peaks", "server_tree_memory"),
               ("root disk bytes", "disk_total_bytes"), ("current readiness seconds", "current_ready_s"),
               ("first startup", "startup"), ("engine failure counts", "engine_events"), ("log scan", "log_scan")])
        values = resource_values(result)
        fields("Cross-gate samples", values, [("GPU peak MiB", "gpu_memory_used_peak"), ("minimum available RAM bytes", "min_available_ram_serving")])
        limitations.extend(["Lifetime process peaks describe the surviving tree; sampling can miss transient peaks.",
                            "Fault-probe disconnects and deliberate engine kills are retained, not an indefinite stability claim."])
    elif gid == "G24":
        summary, attempts = result["scored_batch"]["summary"], result["scored_batch"]["attempts"]
        walls = [a["task_wall_ms"] for a in attempts if number(a.get("task_wall_ms"))]
        direct(summary, [("verified_passes", "completion_count", "count", "external_verifier"),
                         ("scheduled_attempts", "denominator", "count", "calculated"),
                         ("completion_rate", "completion_rate", "ratio", "calculated"),
                         ("batch_wall", "total_wall_ms", "ms", "monotonic_wall_clock"),
                         ("failed_attempt_wall_total", "failed_attempt_wall_ms", "ms", "monotonic_wall_clock")])
        metric("task_wall_median_all_attempts", statistics.median(walls) if walls else None, "ms", "calculated")
        metric("task_wall_max_all_attempts", max(walls) if walls else None, "ms", "monotonic_wall_clock")
        metric("pilot_verified_passes", at(result, "pilot_non_scored.summary.completion_count"), "count", "external_verifier")
        totals = Counter(a.get("task") for a in attempts)
        passes = Counter(a.get("task") for a in attempts if a.get("verified_pass") is True)
        statements.append("Scored attempts: " + ", ".join(f"{task} {passes[task]}/{total}" for task, total in totals.items()) + ".")
        fields("Scored batch", summary, [("verified passes", "completion_count"), ("denominator", "denominator"),
               ("harness drift", "harness_drift"), ("abort reason", "batch_abort_reason"), ("batch wall ms", "total_wall_ms")])
        statements.append(f"All {len(attempts)} recorded attempts are exported, including "
                          f"{sum(a.get('verified_pass') is not True for a in attempts)} unsuccessful attempts and "
                          f"{sum(a.get('timeout') is True for a in attempts)} timeouts.")
        hooks = [a.get("between_phases_exit_code") for a in attempts if a.get("task") == "continuation"]
        statements.append("Continuation restart-hook exit codes: " + json.dumps(hooks) + ".")
        outcomes = [{key: attempt.get(key) for key in ("task", "attempt", "omp_exit_code", "abort_reason", "timeout",
                                                      "protocol_errors", "compactions", "verifier_pass")}
                    for attempt in attempts if not attempt.get("verified_pass")]
        statements.append("Unsuccessful attempt outcomes: " + json.dumps(outcomes, ensure_ascii=False, sort_keys=True) + ".")
        protocol = measured((sum(value for value in a["protocol_errors"].values() if number(value))
                             if isinstance(a.get("protocol_errors"), dict) else a.get("protocol_errors") for a in attempts), sum)
        fields("Attempt counters", {"protocol_errors": protocol, "compactions": measured((a.get("compactions") for a in attempts), sum)},
               [("protocol errors", "protocol_errors"), ("compactions", "compactions")])
        if result.get("pilot_non_scored"):
            fields("Separate non-scored pilot", result["pilot_non_scored"]["summary"], [("passes", "completion_count"), ("denominator", "denominator")])
        limitations.extend(["Six synthetic tasks with three scored attempts each; bounded usefulness evidence, not a comparative benchmark.",
                            "Evaluation isolation is not an OS sandbox. No account or sandbox claim is inferred from these files.",
                            "The task named long-context is not the approximately 100K capacity probe; G17/G18 provide that boundary.",
                            "Evaluation resource peaks and cold-start measurements are unavailable when the batch records them as null."])
    elif gid == "G26":
        steps = result["steps"]
        direct(steps, [("fetch_wall", "fetch.wall_s", "s", "monotonic_wall_clock"),
                       ("install_wall", "install.wall_s", "s", "monotonic_wall_clock"),
                       ("first_start_wall", "start.wall_s", "s", "monotonic_wall_clock"),
                       ("first_start_ready", "start.ready_s", "s", "monotonic_wall_clock"),
                       ("quickstart_example_wall", "launch_omp_example.wall_s", "s", "monotonic_wall_clock"),
                       ("quickstart_tests_wall", "quickstart_tests.wall_s", "s", "monotonic_wall_clock")])
        statements.append(result["fresh_root"])
        fields("Documented command sequence", steps, [("install", "install"), ("start", "start"),
               ("tracer", "tracer"), ("example", "launch_omp_example"), ("independent tests", "quickstart_tests"), ("final stop", "stop")])
        fields("Installed identity", result["install_record"], [("profile", "profile_id"), ("runtime digest", "runtime_identity_sha256")])
        limitations.append("The runner automates documented commands; a new integration root is not a clean-OS installation study.")
    if profile.data["host"].get("display_attached"):
        count = g10.get("gpu_display_clients")
        limitations.append("Display-attached GPU; " + (f"{count} graphics clients recorded by G10." if number(count)
                                                     else "graphics-client count unavailable in G10."))
    flags = profile.data["strata"]["expected_engine_flags"]
    if "--resident-experts" in flags:
        limitations.append("Low-RAM resident variant: experts not held by the GPU reside in RAM; KV remains in VRAM, without KV streaming.")
    elif "--kv-resident" in flags:
        limitations.append("Profile enables KV streaming with an explicitly bounded resident KV window; not the low-RAM resident-expert variant.")
    return " ".join(statements), metrics, limitations


def build_plan(*, pulled: Path, profile_path: Path, host_label: str, root_path: str,
               private=(), implementation_commit: str, host_had_strata=False,
               release_dir: Path | None = None, denylist=None) -> dict:
    profile = load(profile_path)
    release = release_dir or REPO / "releases" / safe_name(profile.id)
    scrubber = Scrubber(root_path, private, private_denylist() if denylist is None else denylist)
    safe_name(host_label)
    scrubber.check(host_label.encode(), is_json=False)
    if not re.fullmatch(r"[0-9a-f]{40}", implementation_commit):
        raise PublicationError("implementation commit must be a full lowercase commit SHA")
    original = {name: (release / name).read_bytes() for name in ("manifest.json", "qualification.json")}
    for data in original.values():
        scrubber.check(data)
    manifest, ledger = (json.loads(original[name]) for name in ("manifest.json", "qualification.json"))
    if (manifest["candidate_id"] != profile.id or ledger["profile_id"] != profile.id
            or ledger["profile_fingerprint"] != profile.fingerprint
            or manifest["profile"]["fingerprint"] != profile.fingerprint):
        raise PublicationError("release profile identity mismatch")
    if verify(release / "manifest.json")["errors"]:
        raise PublicationError("existing release bindings are invalid; verify the draft first")
    summaries = sorted((pulled / "evidence").glob("requalify-*/summary.json"))
    if len(summaries) != 1:
        raise PublicationError("pull must contain exactly one requalify summary")
    rows = read_json(summaries[0])
    if not isinstance(rows, list) or not rows:
        raise PublicationError("runner summary must contain rows")
    by_step = {}
    for row in rows:
        step = safe_name(row["step"])
        if step in by_step:
            raise PublicationError("duplicate runner step; separate the runs before publication")
        row_time(row)
        by_step[step] = row
    install = json.loads(scrubber.scrub((pulled / "state/install-record.json").read_bytes()))
    if install.get("profile_id") != profile.id or install.get("profile_fingerprint") != profile.fingerprint:
        raise PublicationError("install record profile identity mismatch")
    identity = install["identity"]
    layout = Layout(root=Path("/"), profile=profile)
    generated = [dict(path_label=path, sha256=entry["sha256"]) for path, entry in sorted(identity["files"].items())]
    for path, key, note in ((layout.strata_config, "config_file_sha256", "stock setup.py output; absolute paths are root-specific"),
                            (layout.shared_settings, "shared_settings_sha256", "empty shared settings")):
        generated.append(dict(path_label=path.relative_to(layout.root).as_posix() + f" ({note})", sha256=identity[key]))
    manifest["install"] = dict(generated_files=generated, runtime_identity_sha256=install["runtime_identity_sha256"])
    if not is_sha256(install["runtime_identity_sha256"]) or any(not is_sha256(item["sha256"]) for item in generated):
        raise PublicationError("install record contains an invalid identity digest")
    evidence, results, ids = {}, {}, {}

    def add_evidence(run_id, data):
        safe_name(run_id)
        path = "evidence/" + run_id + ".json"
        scrubbed = scrubber.scrub(data)
        if path in evidence and evidence[path] != scrubbed:
            raise PublicationError("conflicting evidence run identifiers")
        evidence[path] = scrubbed
        return json.loads(scrubbed)

    def check_identity(result):
        for key, expected in (("profile_fingerprint", profile.fingerprint), ("profile_sha256", profile.fingerprint),
                              ("profile_id", profile.id), ("profile", profile.id),
                              ("runtime_identity_sha256", install["runtime_identity_sha256"])):
            if key in result and result[key] != expected:
                raise PublicationError("result identity differs from the selected installed profile")

    for step, row in by_step.items():
        run_ids = row.get("run_id")
        run_ids = run_ids if isinstance(run_ids, list) else [run_ids] if run_ids else []
        loaded = []
        for run_id in run_ids:
            safe_name(run_id)
            path = pulled / "evidence" / run_id / "result.json"
            if step == "tracer" and not path.is_file():
                path = path.with_name("summary.json")
            raw = path.read_bytes()
            result = json.loads(scrubber.scrub(raw))
            if result.get("run_id") != run_id:
                raise PublicationError("result run identifier differs from runner summary")
            check_identity(result)
            loaded.append(result)
            if step != "tracer":
                add_evidence(run_id, raw)
        if step == "tracer" and loaded:
            run_id = "g11-" + run_ids[0]
            result = dict(runs=loaded, all_protocol_pass=all(r.get("protocol_pass") is True for r in loaded),
                          all_task_pass=all(r.get("task_pass") is True for r in loaded))
            results[step] = add_evidence(run_id, encoded(result))
            ids[step] = run_id
        elif len(loaded) == 1:
            results[step], ids[step] = loaded[0], run_ids[0]
        elif len(loaded) > 1:
            raise PublicationError("only tracer steps may report several run identifiers")
        elif step in {s for steps in GATE_STEPS.values() for s in steps} - {"eval", "pilot", "quickstart"}:
            run_id = step + "-" + stamp(row_time(row))
            results[step] = add_evidence(run_id, encoded(dict(runner=public_row(row))))
            ids[step] = run_id

    batches = {}
    for step in ("pilot", "eval"):
        if step not in by_step:
            continue
        row = by_step[step]
        if not row.get("out"):
            raise PublicationError("evaluation row must name its mirrored output directory")
        name = safe_name(str(row["out"]).replace("\\", "/").rstrip("/").split("/")[-1])
        directory = pulled / "eval" / name
        summary = read_json(directory / "summary.json")
        metadata = read_json(directory / "batch.json")
        attempts = [json.loads(line) for line in (directory / "attempts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        check_identity(summary)
        check_identity(metadata)
        batches[step] = dict(summary=summary, batch=metadata, attempts=attempts)
    if "eval" in batches:
        result = dict(scored_batch=batches["eval"], implementation_commit=implementation_commit,
                      between_phases_hook=batches["eval"]["summary"].get("between_phases_hook"))
        if "pilot" in batches:
            result["pilot_non_scored"] = {key: batches["pilot"][key] for key in ("summary", "attempts")}
        ids["eval"] = "g24-scored-" + stamp(row_time(by_step["eval"]))
        results["eval"] = add_evidence(ids["eval"], encoded(result))
    if "quickstart" in by_step:
        end = row_time(by_step.get("stop", by_step["quickstart"]))
        ids["quickstart"] = "g26-" + ("second-root-" if host_had_strata else "fresh-root-") + stamp(end)
        steps = {}
        for step, name in (("fetch", "fetch"), ("install", "install"), ("start", "start"),
                           ("quickstart", "launch_omp_example"), ("quickstart-tests", "quickstart_tests"), ("stop", "stop")):
            if step in by_step:
                row = by_step[step]
                steps[name] = dict(exit=row.get("rc"), wall_s=row.get("seconds"))
        steps["launch_omp_example"]["project_tests_pass_after"] = by_step.get("quickstart-tests", {}).get("rc") == 0
        if "tracer" in results:
            runs = results["tracer"].get("runs", [])
            steps["tracer"] = dict(runs=len(runs), protocol_pass=sum(run.get("protocol_pass") is True for run in runs),
                                   task_pass=sum(run.get("task_pass") is True for run in runs))
        ready = at(results.get("g21", {}), "startup.first_start.ready_s")
        if ready is not None and "start" in steps:
            steps["start"]["ready_s"] = ready
        result = dict(host=host_label, checkout=dict(commit=implementation_commit, kind="tooling commit supplied by operator"),
                      fresh_root=("New integration root on a host that keeps earlier integration roots; not a fresh OS." if host_had_strata
                                  else "New integration root on a host that had never had Strata; not a fresh OS."),
                      install_record=install, runner_steps=[public_row(row) for row in rows], steps=steps)
        results["quickstart"] = add_evidence(ids["quickstart"], encoded(result))

    receipts, inventory = [], gate_inventory()
    for gid, steps in GATE_STEPS.items():
        if steps[0] not in by_step and not any(step in by_step for step in steps[1:]):
            continue
        # A pilot alone does not represent a scored evaluation.
        if gid == "G24" and "eval" not in results:
            continue
        main_step = next(step for step in steps if step in results)
        result = results[main_step]
        companion = next((results[s] for s in steps if s != main_step and s in results), {})
        passed = all(step in by_step and row_pass(by_step[step]) for step in steps)
        reason = None
        if gid == "G11":
            passed = passed and result.get("all_protocol_pass") is True and result.get("all_task_pass") is True
        elif gid == "G21":
            passed = by_step[main_step].get("rc") == 0 and resource_complete(result)
            reason = "Measurement-only probe: pass requires recorded resource peaks, startup and engine-failure counts, not pass_observed."
        elif gid == "G24":
            tasks = [task["id"] for task in read_json(REPO / "eval/tasks.json")["tasks"]]
            passed = evaluation_complete(result["scored_batch"], tasks)
            reason = "Complete independently verified reporting is the gate; failed tasks remain in the scored denominator."
        elif gid == "G26":
            passed = passed and all(by_step.get(step, {}).get("rc") == 0 for step in ("install", "start", "quickstart-tests"))
        if gid == "G18" and main_step != "g18l":
            result, companion = {}, result
        elif gid == "G14" and main_step != "g14":
            result, companion = {}, result
        observed, metrics, limitations = gate_details(gid, result, companion, host_label, profile, results.get("g10", {}))
        row_facts = ", ".join(f"{step} rc={by_step[step].get('rc')}, pass_observed={by_step[step].get('pass_observed')}"
                              for step in steps if step in by_step)
        observed += " Runner: " + row_facts + "."
        missing = [step for step in steps if step not in by_step]
        if missing:
            observed += " Unrun companion steps: " + ", ".join(missing) + "."
        refs = [dict(kind="redacted_log", path_or_ref="evidence/" + ids[step] + ".json", scrubbed=True,
                     sha256=sha256_bytes(evidence["evidence/" + ids[step] + ".json"]))
                for step in steps if step in ids and step != "pilot"]
        spec = inventory[gid]
        receipt = make_receipt(gate_id=gid, status="pass" if passed else "fail", execution_boundary=spec["execution_boundary"],
                               expected=spec["pass_condition"], observed=observed, gate_key=spec["key"], gate_title=spec["title"],
                               implementation_commit=implementation_commit, profile_id=profile.id, identity_fingerprint=profile.fingerprint,
                               run_id=ids[main_step], timestamp_utc=result.get("utc") or row_time(by_step[main_step]), evidence=refs,
                               metrics=metrics, limitations=limitations, reason=reason)
        scrubber.check(encoded(receipt))
        receipts.append(receipt)
    if not receipts:
        raise PublicationError("summary has no publishable gate observations")
    existing_ids = {read_json(release / ref["path"])["run_id"] for gate in ledger["gates"] for ref in gate["receipts"]}
    for receipt in receipts:
        if receipt["run_id"] in existing_ids or (release / "receipts" / (receipt["run_id"] + ".json")).exists():
            raise PublicationError("receipt already exists; publication is append-only")
    for path, data in evidence.items():
        existing = release / path
        if existing.exists() and existing.read_bytes() != data:
            raise PublicationError("existing evidence differs; publication is append-only")
    scrubber.check(encoded(manifest))
    if schema_errors(manifest, read_json(CONTRACT_REPO / "schemas/manifest.schema.json")):
        raise PublicationError("planned manifest does not satisfy the release schema")
    return dict(release=release, receipts=receipts, evidence=evidence, manifest=manifest,
                original=original, scrubber=scrubber)


def publish(plan: dict, *, dry_run=False) -> None:
    if dry_run:
        return
    release = plan["release"]
    # Validate the complete staged release before touching the operator's draft.
    # Staging is a sibling so manifest-relative profile paths keep their meaning.
    with tempfile.TemporaryDirectory(prefix=".publish-", dir=release.parent) as temporary:
        stage = Path(temporary)
        shutil.copytree(release, stage, dirs_exist_ok=True)
        for path, data in plan["evidence"].items():
            destination = stage / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                destination.write_bytes(data)
        for receipt in plan["receipts"]:
            path = write_receipt(stage / "receipts", receipt)
            update_ledger(stage / "qualification.json", path)
        ledger = read_json(stage / "qualification.json")
        ledger["execution_performed"] = True
        atomic_write_json(stage / "qualification.json", ledger)
        manifest = dict(plan["manifest"])
        manifest["qualification"] = dict(manifest["qualification"], ledger_sha256=sha256_file(stage / "qualification.json"))
        atomic_write_json(stage / "manifest.json", manifest)
        for name in ("qualification.json", "manifest.json"):
            plan["scrubber"].check((stage / name).read_bytes())
        if verify(stage / "manifest.json")["errors"]:
            raise PublicationError("staged release verification failed; draft unchanged")
        if any((release / name).read_bytes() != data for name, data in plan["original"].items()):
            raise PublicationError("release changed while planning; draft unchanged")
        backup = stage.with_name(stage.name + "-previous")
        release.rename(backup)
        try:
            stage.rename(release)
        except BaseException:
            backup.rename(release)
            raise
        shutil.rmtree(backup)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pulled", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--host-label", required=True)
    parser.add_argument("--root-path", required=True, help="private host root, used only for scrubbing")
    parser.add_argument("--private", action="append", default=[], metavar="TERM")
    parser.add_argument("--implementation-commit", required=True, metavar="SHA")
    parser.add_argument("--host-had-strata", action="store_true", help="record a second integration root, not a first Strata installation")
    parser.add_argument("--dry-run", action="store_true", help="validate and print the plan without writing any files")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(pulled=args.pulled, profile_path=args.profile, host_label=args.host_label,
                          root_path=args.root_path, private=args.private, implementation_commit=args.implementation_commit,
                          host_had_strata=args.host_had_strata)
        publish(plan, dry_run=args.dry_run)
        print("Dry-run plan (no files written):" if args.dry_run else "Published measured gate receipts:")
        for receipt in plan["receipts"]:
            print(f"{receipt['gate_id']} {receipt['status']:4} {receipt['run_id']} ({len(receipt['evidence'])} evidence files)")
        print(f"Manifest: {len(plan['manifest']['install']['generated_files'])} generated-file bindings; ledger hash refreshed on publication.")
        print("Operator decisions unchanged: status, blockers, publication_authorized.")
        print("Manual receipts remain: G00, G01-G06, G22, G23, G25; no receipts inherited.")
        return 0
    except PublicationError as exc:
        print("publication refused: " + str(exc), file=sys.stderr)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        # OS/parser exceptions can embed private absolute paths and source bytes.
        print(f"publication refused: invalid or unavailable input ({type(exc).__name__}); details withheld", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
