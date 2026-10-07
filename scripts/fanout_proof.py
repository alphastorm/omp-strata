#!/usr/bin/env python3
"""Compare stock OMP task fan-out on one Strata provider and an authenticated fleet.

Server histories are observations, not inferred parallelism from client wall time.
This is supplemental G23 evidence; it alone cannot qualify auth/drop/restart behavior.
"""
from __future__ import annotations

import argparse

import copy
import json
import math
from pathlib import Path
import re
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata.common import atomic_write_json, sha256_file
from omp_strata.lifecycle import FileLock
from omp_strata.layout import Layout
from omp_strata.ompcfg import CHAT_ROLES
from omp_strata.profile import ClientRoute, load_route
from omp_strata.receipts import make_receipt, write_receipt
from omp_strata.remote import (RemoteError, RemoteSession, client_key_path, http_json, interrupt_scope,
                               guard_client_root, load_bindings, read_client_key, verify_client_binary, write_client_key)
from omp_strata.transcript import find_sessions, load, summarize, tool_cycles


def metrics_snapshot(member: dict, key: str, owner) -> dict:
    before = time.time()
    status, value = http_json(f"http://127.0.0.1:{member['local_port']}/metrics?requests=all", key=key, owner=owner)
    after = time.time()
    if status != 200 or not isinstance(value, dict):
        raise RemoteError("authenticated Strata request history is unavailable (requires Strata >=0.1.35)")
    try:
        count = value["totals"]["requests"]
        server_time = value["time"]
        rows = value["requests"]
        if type(count) is not int or count < 0 or not isinstance(rows, list) or not math.isfinite(server_time):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise RemoteError("Strata metrics has an invalid request-history shape") from None
    return {"count": count, "rows": rows, "offset": server_time - (before + after) / 2,
            "clock_uncertainty": (after - before) / 2, "since": value.get("totals", {}).get("since")}


def new_intervals(before: dict, after: dict) -> list[tuple[float, float]]:
    count = after["count"] - before["count"]
    if after["since"] != before["since"] or count < 0:
        raise RemoteError("server restarted during fan-out; history is not comparable")
    if count > len(after["rows"]):
        raise RemoteError("Strata request-history retention overflowed during proof")
    intervals = []
    for row in after["rows"][:count]:
        try:
            start, duration = row["time"], row["duration_s"]
            if isinstance(start, bool) or isinstance(duration, bool) or not math.isfinite(start) or not math.isfinite(duration) or duration < 0:
                raise ValueError
            if row.get("finish") not in ("stop", "length", "tool_calls", "done", "eos", "end"):
                # Stock Strata's normal native completion is `stop`; faults must not count as throughput.
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise RemoteError("invalid or failed request in fan-out history") from None
        # Convert server wall clocks using the metrics sample midpoint, rather than assuming synchronized hosts.
        start -= after["offset"]
        intervals.append((start, start + duration))
    return sorted(intervals)


def overlap(intervals) -> dict:
    events = sorted((point, delta) for start, end in intervals for point, delta in ((start, 1), (end, -1)) if end > start)
    active = peak = 0
    seconds = 0.0
    prior = None
    for point, delta in events:
        if prior is not None and active > 1:
            seconds += point - prior
        active += delta
        peak = max(peak, active)
        prior = point
    return {"peak_active": peak, "overlap_seconds": seconds}


def delivered_results(entries: list[dict]) -> dict:
    """Only completed task-result envelopes count, never prompt/assignment echoes."""
    delivered = {}
    for entry in entries:
        message = entry.get("message", {})
        if entry.get("type") == "custom_message" and entry.get("customType") == "async-result":
            content = entry.get("content", [])
        elif message.get("role") == "toolResult" and message.get("toolName") in ("task", "wait"):
            content = message.get("content", [])
        else:
            continue
        text = content if isinstance(content, str) else "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
        for match in re.finditer(r'<task-result\b(?P<attrs>[^>]*)>.*?<output>\s*(?P<out>.*?)\s*</output>\s*</task-result>', text, re.S):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', match["attrs"]))
            if attrs.get("status") != "completed":
                continue
            try:
                value = json.loads(match["out"])
            except ValueError:
                continue
            if isinstance(value, dict):
                delivered[attrs.get("id")] = value
    return delivered


def run_fanout(session: RemoteSession, *, binary: Path, work: Path, scouts: int, timeout: float = 180) -> dict:
    if not 1 <= scouts <= 32:
        raise RemoteError("scouts must be in 1..32")
    agents = list(session.route.data["agents"])
    if not agents:
        raise RemoteError("fan-out route must name at least one custom scout agent")
    work.mkdir(parents=True, exist_ok=True)
    expected = {f"Scout{i + 1}": "SCOUT_" + secrets.token_hex(8) for i in range(scouts)}
    assignments = [{"name": name, "agent": agents[i % len(agents)],
                    "task": f"Use yield with data {{\"answer\":\"{answer}\"}}. Do not call any other tool.",
                    "solutionSpace": "Synthetic read-only fan-out fixture; return only the assigned answer."}
                   for i, (name, answer) in enumerate(expected.items())]
    prompt = ("Call task exactly once with the following tasks concurrently, not one by one. "
              "Wait for every completed result before your final reply. Do not fabricate a scout result.\n" + json.dumps(assignments))
    before = {m["label"]: metrics_snapshot(m, session.keys[m["label"]], session.tunnel(m["label"])) for m in session.route.data["members"]}
    start = time.monotonic()
    stdout_path, stderr_path = work / "omp.jsonl", work / "omp.stderr"
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        code = session.run(["-p", "--mode", "json", "--auto-approve", "--tools", "task,wait", "--max-time", f"{int(timeout)}s", prompt],
                           binary=binary, cwd=work, stdout=stdout, stderr=stderr, timeout=timeout + 10)
    wall = time.monotonic() - start
    sessions = find_sessions(session.layout.omp_home)
    if code != 0 or len(sessions) != 1:
        raise RemoteError("stock OMP fan-out did not finish one intact session")
    entries = load(sessions[0])
    summary = summarize(sessions[0])
    calls = [c for c in tool_cycles(entries) if c["name"] == "task" and c["result_found"] and not c["is_error"]]
    if len(calls) != 1 or len(calls[0]["arguments"].get("tasks", [])) != scouts:
        raise RemoteError("stock OMP did not dispatch the requested single task batch")
    actual_tasks = calls[0]["arguments"]["tasks"]
    if {t.get("name"): t.get("agent") for t in actual_tasks} != {t["name"]: t["agent"] for t in assignments}:
        raise RemoteError("stock OMP changed the requested scout-to-provider assignment")
    delivered = delivered_results(entries)
    if any(delivered.get(name, {}).get("answer") != answer for name, answer in expected.items()):
        raise RemoteError("not every scout result was delivered intact to the parent transcript")
    allowed = {"strata-" + m["label"] for m in session.route.data["members"]}
    if set(summary["providers"]) - allowed or summary["stopReasons"][-1:] != ["stop"]:
        raise RemoteError("fan-out transcript failed its route/completion audit")
    providers = {}
    intervals = []
    for member in session.route.data["members"]:
        label = member["label"]
        after = metrics_snapshot(member, session.keys[label], session.tunnel(label))
        rows = new_intervals(before[label], after)
        intervals.extend(rows)
        providers["strata-" + label] = {"requests": len(rows), "intervals_unix_seconds": rows,
                                       "clock_uncertainty_seconds": after["clock_uncertainty"], **overlap(rows)}
    return {"wall_seconds": wall, "scouts": scouts, "delivered_results": scouts, "providers": providers,
            "combined": overlap(intervals), "parent_provider": summary["providers"],
            "timestamp_fields": {"start": "requests[].time", "end": "time + duration_s", "duration_resolution_seconds": 0.1},
            "limitations": ["No other clients may use these servers during the proof.",
                            "Strata durations are rounded to 0.1 s; clock offsets are estimated from metrics RTT, not clock synchronization."]}


def comparison(route: ClientRoute, root: Path, bindings: dict, *, scouts: int, output: Path, timeout=180) -> dict:
    layout = Layout(root, route.main)
    guard_client_root(layout, route)
    with FileLock(layout.state / "client.lock"):
        guard_client_root(layout, route, record=True)
    binary = Layout(root, route.main).omp_binary()
    verify_client_binary(Layout(root, route.main))
    main = route.data["roles"]["default"]
    result = {}
    for mode in ("single", "fleet"):
        data = copy.deepcopy(route.data)
        if mode == "single":
            data["members"] = [m for m in data["members"] if m["label"] == main]
            data["roles"] = {role: main for role in CHAT_ROLES}
            data["agents"] = {agent: main for agent in data["agents"]}
        run_route = ClientRoute(route.path, data, {m["label"]: route.servers[m["label"]] for m in data["members"]})
        run_root = output / mode
        run_layout = Layout(run_root, run_route.main)
        guard_client_root(run_layout, run_route)
        with FileLock(run_layout.state / "client.lock"):
            guard_client_root(run_layout, run_route, record=True)
            for member in data["members"]:
                label = member["label"]
                write_client_key(client_key_path(run_root, label), read_client_key(client_key_path(root, label), bindings[label]), bindings[label])
            with RemoteSession(run_route, run_root, {label: bindings[label] for label in run_route.servers}) as session:
                result[mode] = run_fanout(session, binary=binary, work=run_root / "work", scouts=scouts, timeout=timeout)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True, help="public client-route JSON")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--fleet", type=Path, required=True, help="private bindings JSON")
    parser.add_argument("--scouts", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--output", type=Path, required=True, help="new private evidence directory")
    parser.add_argument("--implementation-commit")
    parser.add_argument("--host-free", action="store_true", help="mock evidence only; never passes G23")
    args = parser.parse_args(argv)
    route = load_route(args.profile)
    if not args.output.resolve().is_relative_to(args.root.resolve()):
        parser.error("raw evidence must stay under the client root")
    layout = Layout(args.root.resolve(), route.main)
    guard_client_root(layout, route)
    with interrupt_scope(), FileLock(layout.state / "client.lock"):
        guard_client_root(layout, route, record=True)
        args.output.mkdir(parents=True, exist_ok=False)
    result = {}
    try:
        with interrupt_scope():
            result = comparison(route, args.root.resolve(), load_bindings(args.fleet, route), scouts=args.scouts,
                                output=args.output, timeout=args.timeout)
        status, observed = ("not_run" if args.host_free else "blocked"), "Both stock task batches delivered every scout result; request intervals recorded."
    except (RemoteError, OSError, ValueError):
        status, observed = "fail", "Fan-out proof failed; raw diagnostics remain under the private evidence root."
    evidence = args.output / "summary.json"
    atomic_write_json(evidence, result)
    receipt = make_receipt(gate_id="G23", status=status, execution_boundary="host_free" if args.host_free else "real_host",
                           implementation_commit=args.implementation_commit, profile_id=route.id, identity_fingerprint=route.fingerprint,
                           expected="One-provider and fleet task batches deliver every scout with measured server request overlap.",
                           observed=observed, reason="Supplemental fan-out does not replace the complete auth/drop/restart G23 probe.",
                           evidence=[dict(kind="test_report", path_or_ref="summary.json", sha256=sha256_file(evidence), scrubbed=True)],
                           limitations=["No GPU, throughput or real-host qualification follows from a host-free run."])
    write_receipt(args.output, receipt)
    print(json.dumps({"status": status, "results": result}, indent=2))
    return int(status == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
