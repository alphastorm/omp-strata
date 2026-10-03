#!/usr/bin/env python3
"""Client-side G23: auth, tunnel latency/drop, transcript resume and server restart.

Restart commands are explicit private JSON argv arrays. No remote command is
invented, no shell is used, and raw client transcripts stay under the client root.
"""
from __future__ import annotations

import argparse
import copy
import http.client
import json
from pathlib import Path
import secrets
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata.common import atomic_write_json, sha256_file
from omp_strata.layout import Layout
from omp_strata.lifecycle import FileLock
from omp_strata.ompcfg import CHAT_ROLES
from omp_strata.profile import ClientRoute, load_route
from omp_strata.receipts import make_receipt, write_receipt
from omp_strata.remote import (OwnedProcess, RemoteError, RemoteInterrupted, RemoteSession, TunnelHTTPConnection, client_key_path, http_json,
                               defer_interrupts, guard_client_root, interrupt_scope, load_bindings, preflight, read_client_key,
                               verify_client_binary, write_client_key)
from omp_strata.transcript import find_sessions, load, summarize


def streamed_ttft(profile, local_port: int, key: str, *, owner, timeout: float = 120) -> float:
    connection = TunnelHTTPConnection("127.0.0.1", local_port, owner=owner, timeout=timeout)
    payload = {"model": profile.data["strata"]["model_name"], "messages": [{"role": "user", "content": "Reply with READY."}],
               "stream": True, "max_tokens": 128}
    first, done = None, False
    try:
        connection.connect()
        started = time.monotonic()
        connection.request("POST", "/v1/chat/completions", json.dumps(payload), {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise RemoteError("tunnel TTFT request was refused")
        while line := response.readline():
            if time.monotonic() - started > timeout:
                raise RemoteError("tunnel TTFT request exceeded its deadline")
            if not line.startswith(b"data: "):
                continue
            if line.strip() == b"data: [DONE]":
                done = True
                break
            value = json.loads(line[6:])
            if value.get("error"):
                raise RemoteError("tunnel TTFT stream returned an error")
            for choice in value.get("choices", []):
                delta = choice.get("delta", {})
                if first is None and (delta.get("content") or delta.get("reasoning_content")):
                    first = time.monotonic() - started
        if first is None or not done:
            raise RemoteError("tunnel TTFT stream did not complete")
        return first
    except (OSError, ValueError, http.client.HTTPException):
        raise RemoteError("tunnel TTFT stream failed") from None
    finally:
        connection.close()


def _answer(entries):
    messages = [e["message"] for e in entries if e.get("type") == "message" and e.get("message", {}).get("role") == "assistant"]
    if not messages or messages[-1].get("stopReason") != "stop":
        return None
    content = messages[-1].get("content", [])
    return "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()


def _turn(session, binary, work, name, prompt, *, resume=False, timeout=180, drop=False):
    work.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path = work / (name + ".jsonl"), work / (name + ".stderr")
    extra = ["-p", "--mode", "json", "--no-tools", "--max-time", f"{int(timeout)}s"]
    if resume:
        extra.append("--continue")
    extra.append(prompt)
    stop = threading.Event()
    dropped = threading.Event()

    def cut_after_token():
        offset = 0
        pending = b""
        while not stop.wait(0.01):
            try:
                with stdout_path.open("rb") as stream:
                    stream.seek(offset)
                    chunk = stream.read()
            except FileNotFoundError:
                continue
            offset += len(chunk)
            pending += chunk
            lines = pending.split(b"\n")
            pending = lines.pop()
            for line in lines:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                update = event.get("assistantMessageEvent", {})
                if event.get("type") == "message_update" and update.get("type") in ("text_delta", "thinking_delta"):
                    dropped.set()
                    session.tunnels[0].close()
                    return

    watcher = threading.Thread(target=cut_after_token, daemon=True) if drop else None
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        if watcher:
            watcher.start()
        try:
            code = session.run(extra, binary=binary, cwd=work, stdout=stdout, stderr=stderr, timeout=timeout + 10)
        except RemoteError:
            if not drop or not dropped.is_set():
                raise
            code = 1
        finally:
            stop.set()
            if watcher:
                watcher.join(timeout=5)
    paths = find_sessions(session.layout.omp_home)
    if len(paths) != 1:
        raise RemoteError("probe did not retain exactly one authoritative transcript")
    entries = load(paths[0])
    audit = summarize(paths[0])
    allowed = {"strata-" + label for label in session.route.servers}
    if set(audit["providers"]) - allowed or audit["orphan_results"]:
        raise RemoteError("probe transcript escaped its route or lost a tool result")
    if drop:
        if not dropped.is_set() or code == 0:
            raise RemoteError("tunnel drop was not observed as a failed in-flight turn")
    elif code != 0 or _answer(entries) is None:
        raise RemoteError("stock OMP turn failed")
    return {"seconds": time.monotonic() - started, "entries": entries, "answer": _answer(entries), "path": paths[0]}


def probe_member(session, *, binary, work, restart, timeout=180):
    member = session.route.data["members"][0]
    label = member["label"]
    profile = session.route.servers[label]
    key = session.keys[label]
    owner = session.tunnel(label)
    url = f"http://127.0.0.1:{member['local_port']}"
    # Missing client credentials must be refused before a tunnel or OMP home is created.
    empty_root = work / "missing-key"
    try:
        with RemoteSession(session.route, empty_root, session.bindings, ssh=session.ssh):
            raise RemoteError("missing key unexpectedly accepted")
    except RemoteError as exc:
        if "pull-key" not in str(exc) or (empty_root / "omp").exists():
            raise RemoteError("missing-key launch did not fail before OMP") from None
    if http_json(url + "/v1/models")[0] != 401 or http_json(url + "/v1/models", key=secrets.token_urlsafe(32), owner=owner)[0] != 401:
        raise RemoteError("remote endpoint did not refuse missing and wrong keys")
    try:
        preflight(profile, member["local_port"], secrets.token_urlsafe(32), owner=owner)
    except RemoteError as exc:
        if "401" not in str(exc):
            raise
    else:
        raise RemoteError("wrong-key preflight accepted")
    rtts = []
    for _ in range(3):
        start = time.monotonic()
        if http_json(url + "/health")[0] != 200:
            raise RemoteError("tunnel health RTT request failed")
        rtts.append(time.monotonic() - start)
    ttft = streamed_ttft(profile, member["local_port"], key, owner=owner, timeout=timeout)
    nonce = "RECALL_" + secrets.token_hex(12)
    initial = _turn(session, binary, work, "initial", f"Remember this exact nonce for later turns: {nonce}. Reply only with that nonce.", timeout=timeout)
    if initial["answer"] != nonce:
        raise RemoteError("initial exact-nonce response failed")
    resumed = _turn(session, binary, work, "client-restart", "Repeat only the nonce I asked you to remember.", resume=True, timeout=timeout)
    if resumed["answer"] != nonce or resumed["path"] != initial["path"]:
        raise RemoteError("client restart did not recover the intended transcript nonce")
    dropped = _turn(session, binary, work, "tunnel-drop", "Write a long numbered list of 2000 distinct integers, one per line. Continue until the list is complete.", resume=True, timeout=timeout, drop=True)
    if dropped["entries"][:len(resumed["entries"])] != resumed["entries"]:
        raise RemoteError("tunnel drop damaged the previously persisted transcript")
    session.tunnels[0].open()
    preflight(profile, member["local_port"], key, owner=owner)
    reopened = _turn(session, binary, work, "tunnel-reopen", "Ignore the interrupted list. Repeat only the original remembered nonce.", resume=True, timeout=timeout)
    if reopened["answer"] != nonce or reopened["path"] != initial["path"]:
        raise RemoteError("tunnel reopen did not resume the transcript")
    status, before = http_json(url + "/metrics", key=key, owner=owner)
    since = before.get("totals", {}).get("since") if status == 200 and isinstance(before, dict) else None
    if not isinstance(since, (int, float)):
        raise RemoteError("server instance timestamp unavailable; cannot prove a restart")
    restart()
    deadline = time.monotonic() + timeout
    changed = False
    while time.monotonic() < deadline:
        try:
            preflight(profile, member["local_port"], key, owner=owner)
            status, after = http_json(url + "/metrics", key=key, owner=owner)
            new_since = after.get("totals", {}).get("since") if status == 200 and isinstance(after, dict) else None
            if isinstance(new_since, (int, float)) and new_since != since:
                changed = True
                break
        except RemoteError:
            pass
        time.sleep(0.2)
    if not changed:
        raise RemoteError("operator command did not produce a new healthy server instance")
    final = _turn(session, binary, work, "server-and-client-restart", "Repeat only the original remembered nonce.", resume=True, timeout=timeout)
    if final["answer"] != nonce or final["path"] != initial["path"]:
        raise RemoteError("server/client restart did not replay the authoritative transcript")
    return {"missing_key_refused_before_launch": True, "wrong_key_http_status": 401,
            "health_rtt_seconds": rtts, "ttft_seconds": ttft, "tunnel_drop_failed_turn": True,
            "transcript_preserved": True, "client_restart_recall": True, "server_instance_changed": True,
            "server_restart_recall": True, "cold_replay_allowed": True,
            "resume_seconds": {"client": resumed["seconds"], "tunnel": reopened["seconds"], "server": final["seconds"]}}


def restart_command(argv: list[str], timeout: float):
    if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v or "\0" in v for v in argv):
        raise RemoteError("restart command must be a private nonempty JSON argv array")
    import subprocess
    child = None
    try:
        with defer_interrupts():
            child = OwnedProcess(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            code = child.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RemoteError("operator restart command timed out") from None
        if code:
            raise RemoteError("operator restart command failed")
    finally:
        if child is not None:
            child.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--restart-commands", type=Path, required=True, help="private JSON object: member label -> explicit argv array")
    parser.add_argument("--output", type=Path, required=True, help="new directory under the client root")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--host-free", action="store_true", help="mock evidence cannot pass G23")
    args = parser.parse_args(argv)
    route, root = load_route(args.profile), args.root.resolve()
    bindings = load_bindings(args.bindings, route)
    commands = json.loads(args.restart_commands.read_text())
    if not isinstance(commands, dict) or set(commands) != set(route.servers):
        parser.error("restart commands must cover every route member")
    if not args.output.resolve().is_relative_to(root):
        parser.error("raw evidence must stay under the client root")
    layout = Layout(root, route.main)
    guard_client_root(layout, route)
    with interrupt_scope(), FileLock(layout.state / "client.lock"):
        guard_client_root(layout, route, record=True)
        args.output.mkdir(parents=True, exist_ok=False)
    results = {}
    status = "not_run" if args.host_free else "pass"
    try:
        verify_client_binary(Layout(root, route.main))
        with interrupt_scope():
            for member in route.data["members"]:
                label = member["label"]
                data = {**copy.deepcopy(route.data), "members": [member], "roles": {r: label for r in CHAT_ROLES}, "agents": {}}
                member_route = ClientRoute(route.path, data, {label: route.servers[label]})
                run_root = args.output / label
                run_layout = Layout(run_root, member_route.main)
                guard_client_root(run_layout, member_route)
                with FileLock(run_layout.state / "client.lock"):
                    guard_client_root(run_layout, member_route, record=True)
                    write_client_key(client_key_path(run_root, label), read_client_key(client_key_path(root, label), bindings[label]), bindings[label])
                    with RemoteSession(member_route, run_root, {label: bindings[label]}) as session:
                        results[label] = probe_member(session, binary=Layout(root, route.main).omp_binary(), work=run_root / "work",
                                                      restart=lambda: restart_command(commands[label], args.timeout), timeout=args.timeout)
    except (RemoteError, OSError, ValueError, RemoteInterrupted):
        status = "fail"
    evidence = args.output / "summary.json"
    atomic_write_json(evidence, results)
    metrics = [dict(name=label + ".tunnel_ttft", value=result["ttft_seconds"], unit="seconds", boundary="client through SSH tunnel",
                    method="monotonic_wall_clock") for label, result in results.items()]
    receipt = make_receipt(gate_id="G23", status=status, execution_boundary="host_free" if args.host_free else "real_host",
                           implementation_commit=args.implementation_commit, profile_id=route.id, identity_fingerprint=route.fingerprint,
                           expected="Every route member refuses bad auth, survives tunnel/client/server restart via intact transcript replay, and reports tunnel timing.",
                           observed="All member scenarios completed." if status in ("pass", "not_run") else "A member scenario failed; raw diagnostics remain private.",
                           evidence=[dict(kind="test_report", path_or_ref="summary.json", sha256=sha256_file(evidence), scrubbed=True)], metrics=metrics,
                           limitations=["Tunnel TTFT includes server work. No direct-path baseline or SSH-only overhead is inferred.",
                                        "Proxy environment is defense in depth, not an OS egress firewall.",
                                        "Host-free runs never satisfy a real-host gate; cold transcript re-prefill is expected."])
    write_receipt(args.output, receipt)
    print(json.dumps({"status": status, "members_completed": len(results)}))
    return int(status == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
