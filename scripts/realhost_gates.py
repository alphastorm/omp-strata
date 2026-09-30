#!/usr/bin/env python3
"""Real-host acceptance probes for the local route (run ON the GPU host, against the running integration).

Each subcommand writes <root>/evidence/<run_id>/result.json and prints it: derived facts only (counts, statuses,
timings, token counts, booleans). Raw material (event streams, sessions, ETW traces) stays in the evidence
directory and never enters the repository. A result is an observation for a receipt; `pass_observed` is the
probe's own reading of the gate condition, never a substitute for review.

  g10  host preflight, pinned identity, loopback listener, exclusive GPU ownership, measured headroom
  g12  engine-reported prefix reuse on same-session continuations (tracer run ids as input)
  g13  auth matrix, launcher key refusal, wrong key, dead endpoint, ETW egress observation, route census
  g14  cancellation while generating and while queued, client loss, no duplicate side effect, failed tool
  g14q minimal reproduction of the stale-cancel engine exit after a queued client disconnects
  g15  engine killed idle and mid-generation under one surviving RPC-mode OMP client
  g16  client restart, then client plus full server restart, on one persisted session
  g17  tokenizer-measured context boundary, near-limit tool follow-up, explicit overflow
  g18  real OMP compaction at a reduced threshold, then a typed tool turn that needs a pre-compaction fact
  g18l long-session compaction at the production threshold, then the same typed tool turn
  g19  A-B-A interleaving, resume by session file, and an RPC branch canary
  g20  lifecycle stop/start/restart, orphans, preservation of unrelated host state
  g21  resource and stability record (disk, peak memory, startup, engine failures)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from omp_strata import hostrun, lifecycle, procs, transcript  # noqa: E402
from omp_strata.layout import Layout, default_root  # noqa: E402
from omp_strata.profile import load  # noqa: E402

WINDOWS = sys.platform == "win32"
DEVNULL = subprocess.DEVNULL
CTX_SLACK = 8  # stock serve/server.py: prompt + max_tokens + 8 must fit the engine context (verified by g17)


# ------------------------------------------------------------------------------------------------ helpers
def http(method: str, url: str, *, key: str | None = None, body: dict | None = None, x_api_key: bool = False,
         timeout: float = 30) -> tuple[int, object]:
    import urllib.error
    import urllib.request

    headers = {"User-Agent": "omp-strata-gates"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if key is not None:
        if x_api_key:
            headers["x-api-key"] = key
        else:
            headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, st = r.read(), r.status
    except urllib.error.HTTPError as e:
        raw, st = e.read(), e.code
    except (OSError, TimeoutError) as e:
        return 0, str(e)
    try:
        return st, json.loads(raw)
    except ValueError:
        return st, raw[:200].decode("utf-8", "replace")


def base(layout: Layout) -> str:
    return lifecycle.base_url(layout)


def status_json(layout: Layout) -> dict:
    _, body = http("GET", base(layout) + "/status", timeout=5)
    return body if isinstance(body, dict) else {}


def wait_status(layout: Layout, predicate, timeout: float) -> tuple[dict, bool]:
    deadline = time.monotonic() + timeout
    s: dict = {}
    while time.monotonic() < deadline:
        s = status_json(layout)
        if predicate(s):
            return s, True
        time.sleep(0.25)
    return s, False


def engine_requests(layout: Layout, key: str, since: float) -> list[dict]:
    """Stock Strata's per-request records (engine-side truth) that started at or after `since` (host clock)."""
    st, body = http("GET", base(layout) + "/metrics?requests=all", key=key, timeout=10)
    rows = body.get("requests", []) if st == 200 and isinstance(body, dict) else []
    keep = ("finish", "prompt_tokens", "reused", "output_tokens", "prompt_ms", "decode_ms", "decode_tok_s",
            "duration_s")
    return [{k: r.get(k) for k in keep} for r in sorted(rows, key=lambda r: r.get("time") or 0)
            if (r.get("time") or 0) >= since]


def server_tree(layout: Layout) -> list[procs.ProcInfo]:
    run = json.loads(layout.run_record.read_text()) if layout.run_record.exists() else {}
    server = procs.matches(run.get("server"))
    return ([server] + procs.descendants(server.pid)) if server else []


def engine_proc(layout: Layout) -> procs.ProcInfo | None:
    return next((p for p in server_tree(layout) if Path(p.exe).name.lower().startswith("strata")), None)


def tree_memory(layout: Layout) -> list[dict]:
    return [{"process": Path(p.exe).name, **procs.process_memory(p.pid)} for p in server_tree(layout)]


def session_for(layout: Layout, workspace: Path) -> Path | None:
    for path in sorted(transcript.find_sessions(layout.omp_home), key=lambda p: p.stat().st_mtime, reverse=True):
        header = next((e for e in transcript.load(path) if e.get("type") == "session"), {})
        if header.get("cwd") and Path(str(header["cwd"])).resolve() == workspace.resolve():
            return path
    return None


def assistant_usages(session: Path | None) -> list[dict]:
    rows = []
    for e in (transcript.load(session) if session else []):
        m = e.get("message") or {}
        if e.get("type") == "message" and m.get("role") == "assistant":
            u = m.get("usage") or {}
            rows.append({"stop": m.get("stopReason"), "input": u.get("input"), "cacheRead": u.get("cacheRead"),
                         "output": u.get("output"), "provider": m.get("provider")})
    return rows


def count_calls(session: Path | None, needle: str) -> int:
    cycles = transcript.tool_cycles(transcript.load(session)) if session else []
    return sum(1 for c in cycles if needle in json.dumps(c.get("arguments")))


def kill_tree(pid: int) -> None:
    for p in procs.descendants(pid):
        try:
            procs.terminate(p, 10)
        except PermissionError:
            pass
    root = procs.info(pid)
    if root is not None:
        procs.terminate(root, 10)


def is_loopback(addr: str) -> bool:
    a = addr.strip().strip("[]").lower()
    return a.startswith("127.") or a in ("::1", "0:0:0:0:0:0:0:1") or a.startswith("::ffff:127.")


class Sampler:
    """GPU memory and available system RAM every `period` seconds while a gate runs."""

    def __init__(self, period: float = 2.0):
        self.period = period
        self.peak = {"gpu_used_mib": 0, "min_available_ram_bytes": None}
        self.samples = 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, stdin=DEVNULL, timeout=20).stdout.split()
                if out:
                    self.peak["gpu_used_mib"] = max(self.peak["gpu_used_mib"], int(float(out[0])))
                avail = procs.memory()["available"]
                cur = self.peak["min_available_ram_bytes"]
                self.peak["min_available_ram_bytes"] = avail if cur is None else min(cur, avail)
                self.samples += 1
            except Exception:  # noqa: BLE001 - sampling must never break a gate run
                pass
            self._stop.wait(self.period)

    def __enter__(self) -> "Sampler":
        self._t.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._t.join(timeout=30)


class NetTrace:
    """Test-scoped observation of every TCP/UDP event the kernel attributes to chosen processes (ETW provider
    Microsoft-Windows-Kernel-Network, via logman/tracerpt). Observation only: no firewall rule or global network
    policy is created or changed. Requires an elevated session; otherwise `started` is False and says why."""

    def __init__(self, ev: Path, name: str):
        self.etl = ev / f"{name}.etl"
        self.session = f"omp-strata-net-{secrets.token_hex(4)}"
        self.started = False
        self.error: str | None = None

    def __enter__(self) -> "NetTrace":
        r = subprocess.run(["logman", "start", self.session, "-p", "Microsoft-Windows-Kernel-Network",
                            "0xffffffffffffffff", "0xff", "-o", str(self.etl), "-ets"],
                           capture_output=True, text=True, stdin=DEVNULL, timeout=60)
        self.started = r.returncode == 0
        if not self.started:
            self.error = (r.stdout + r.stderr).strip()[-300:]
        return self

    def __exit__(self, *exc: object) -> None:
        if self.started:
            subprocess.run(["logman", "stop", self.session, "-ets"], capture_output=True, stdin=DEVNULL, timeout=60)

    def attribute(self, pids: set[int], raw_out: Path) -> dict:
        if not self.started:
            return {"method": "etw-kernel-network", "started": False, "error": self.error}
        import xml.etree.ElementTree as ET

        xml = self.etl.with_suffix(".xml")
        subprocess.run(["tracerpt", str(self.etl), "-o", str(xml), "-of", "XML", "-y"], capture_output=True,
                       stdin=DEVNULL, timeout=900)
        total = attributed = 0
        remote: dict[str, int] = {}
        loopback_ports: dict[str, int] = {}
        for _, el in ET.iterparse(xml, events=("end",)):
            if not el.tag.endswith("}Event"):
                continue
            total += 1
            # tracerpt pads numeric fields with spaces ("PID=   29652"); strip every value before use
            data = {d.get("Name"): (d.text or "").strip() for d in el.iter() if d.tag.endswith("}Data")}
            pid = data.get("PID", "")
            if pid.isdigit() and int(pid) in pids:
                attributed += 1
                for k in ("daddr", "saddr"):
                    a = data.get(k)
                    if a and not is_loopback(a):
                        remote[a] = remote.get(a, 0) + 1
                if is_loopback(data.get("daddr", "")) and data.get("dport"):
                    loopback_ports[data["dport"]] = loopback_ports.get(data["dport"], 0) + 1
            el.clear()
        xml.unlink(missing_ok=True)
        hostrun.write_raw(raw_out.parent, raw_out.name, {"non_loopback": remote, "pids": sorted(pids)})
        return {"method": "etw-kernel-network", "started": True, "events_total": total,
                "events_attributed": attributed, "non_loopback_endpoints": len(remote),
                "non_loopback_events": sum(remote.values()), "loopback_dport_events": loopback_ports,
                "conclusive": attributed > 0}


def watch_tree(proc: subprocess.Popen, pids: set[int]) -> None:
    while proc.poll() is None:
        pids.update(p.pid for p in procs.descendants(proc.pid))
        time.sleep(0.2)


def omp_popen(layout: Layout, key: str, cwd: Path, out: Path, args: list[str], overrides: dict | None = None):
    from omp_strata import ompcfg

    ompcfg.install_profile_config(layout, overrides=overrides)
    env = ompcfg.isolated_env(layout, api_key=key)
    argv = ompcfg.omp_argv(layout, extra=args)
    f = open(out, "wb")
    return subprocess.Popen(argv, cwd=cwd, env=env, stdin=DEVNULL, stdout=f, stderr=subprocess.STDOUT), f


def filler(n_lines: int, facts: dict[int, str], seed: int) -> str:
    rng = random.Random(seed)
    vocab = ["river", "stone", "lantern", "harbor", "meadow", "copper", "signal", "orchard", "glacier", "cinder",
             "violet", "anchor", "saddle", "thistle", "compass", "ember", "quarry", "falcon", "ledger", "prism"]
    lines = []
    for i in range(1, n_lines + 1):
        lines.append(facts[i] if i in facts else f"{i:06d} " + " ".join(rng.choice(vocab) for _ in range(12)) + ".")
    return "\n".join(lines) + "\n"


def nonce_fixture(layout: Layout, tag: str) -> tuple[Path, str]:
    nonce = f"{tag.upper()}-" + secrets.token_hex(5).upper()
    ws = hostrun.git_fixture(layout.work / f"{tag}-{secrets.token_hex(3)}", {"NONCE.txt": nonce + "\n"})
    return ws, nonce


SEED = "Read NONCE.txt with your read tool and reply with exactly `NONCE: <contents>`."
RECALL = ("Do not call any tools. From this conversation only: what exact string did NONCE.txt contain when you "
          "read it earlier? Reply with exactly `NONCE: <value>`.")
APPEND_PY = ("import pathlib\np = pathlib.Path('log.txt')\n"
             "p.write_text((p.read_text() if p.exists() else '') + 'ran\\n')\nprint('appended')\n")


# ------------------------------------------------------------------------------------------------ gates
def g10(layout: Layout, key: str, ev: Path, deep: bool) -> dict:
    from omp_strata import fetch as fetch_mod

    doc = lifecycle.doctor(layout)
    st = lifecycle.status(layout)
    rt = lifecycle.runtime_checks(layout, key)
    port = layout.profile.data["server"]["port"]
    tree = server_tree(layout)
    tree_pids = {p.pid for p in tree}
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, stdin=DEVNULL,
                         timeout=60).stdout
    listeners = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
            listeners.append((parts[1], int(parts[4])))
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                          capture_output=True, text=True, stdin=DEVNULL, timeout=30).stdout.strip().splitlines()
    app_pids = [int(r.split(",")[0]) for r in apps if r.strip() and r.split(",")[0].strip().isdigit()]
    gpu = lifecycle.gpu_facts(layout.profile.data["host"]["gpu_index"])
    mem = procs.memory()
    t0 = time.monotonic()
    deep_problems = fetch_mod.verify(layout, deep=True, log=lambda _m: None) if deep else None
    record = json.loads(layout.install_record.read_text())
    import shutil

    result = {
        "doctor_ok": doc["ok"], "doctor_failed": [c.get("check") for c in doc.get("checks", []) if not c.get("ok")],
        "status": st["state"], "runtime_ready": rt["ready"], "runtime_problems": rt["problems"],
        "build_info": rt.get("build_info"), "n_ctx": rt.get("n_ctx"), "modalities": rt.get("modalities"),
        "listeners": [{"local": l, "owned": pid in tree_pids} for l, pid in listeners],
        "listener_loopback_only": bool(listeners) and all(l.startswith("127.0.0.1:") for l, _ in listeners),
        "listener_owned": bool(listeners) and all(pid in tree_pids for _, pid in listeners),
        "gpu": {k: gpu.get(k) for k in ("name", "memory_total_mib", "memory_used_mib", "driver")},
        "gpu_compute_pids_owned": [pid in tree_pids for pid in app_pids],
        "gpu_exclusive": all(pid in tree_pids for pid in app_pids),
        "ram_total_bytes": mem["total"], "ram_available_bytes": mem["available"],
        "commit_limit_bytes": mem["commit_limit"], "commit_available_bytes": mem["commit_available"],
        "disk_free_bytes": shutil.disk_usage(layout.root).free,
        "deep_artifact_verification": None if deep_problems is None else {"ok": deep_problems == [],
                                                                           "problems": len(deep_problems),
                                                                           "seconds": round(time.monotonic() - t0)},
        "runtime_identity_sha256": record["runtime_identity_sha256"],
        "pip_freeze_sha256": record.get("pip_freeze_sha256"),
        "server_tree": [Path(p.exe).name for p in tree],
    }
    result["pass_observed"] = bool(doc["ok"] and st["state"] == "healthy" and rt["ready"]
                                   and result["listener_loopback_only"] and result["listener_owned"]
                                   and result["gpu_exclusive"] and app_pids
                                   and (deep_problems is None or deep_problems == []))
    return result


def g12(layout: Layout, key: str, ev: Path, runs: list[str]) -> dict:
    per = {}
    for rid in runs:
        s = layout.root / "evidence" / rid / "session.jsonl"
        per[rid] = assistant_usages(s) if s.exists() else None
    continuations = [r for rows in per.values() if rows for r in rows[1:]]
    nonzero = [r for r in continuations if (r.get("cacheRead") or 0) > 0]
    summaries = {}
    for rid in runs:
        f = layout.root / "evidence" / rid / "summary.json"
        if f.exists():
            s = json.loads(f.read_text())
            summaries[rid] = {"protocol_pass": s.get("protocol_pass"), "task_pass": s.get("task_pass")}
    return {"runs": list(per), "per_request": per, "run_results": summaries, "continuations": len(continuations),
            "continuations_with_reuse": len(nonzero),
            "pass_observed": (len(nonzero) >= 3 and len(nonzero) == len(continuations)
                              and all(v["protocol_pass"] and v["task_pass"] for v in summaries.values())
                              and len(summaries) == len(runs))}


def route_census(layout: Layout) -> dict:
    providers, models, apis, sessions = set(), set(), set(), 0
    for path in transcript.find_sessions(layout.omp_home):
        s = transcript.summarize(path)
        sessions += 1
        providers.update(s["providers"])
        models.update(s["models"])
        apis.update(s["apis"])
    return {"sessions": sessions, "providers": sorted(providers), "models": sorted(models), "apis": sorted(apis)}


def g13(layout: Layout, key: str, ev: Path) -> dict:
    from omp_strata import ompcfg

    url = base(layout)
    wrong = "wrong-" + secrets.token_urlsafe(24)
    matrix = {}
    for path in ["/v1/models", "/models", "/props", "/metrics", "/settings", "/slots", "/v1/status", "/mcp"]:
        matrix[f"GET {path}"] = {"none": http("GET", url + path)[0], "wrong": http("GET", url + path, key=wrong)[0],
                                 "wrong_x_api_key": http("GET", url + path, key=wrong, x_api_key=True)[0],
                                 "correct": http("GET", url + path, key=key)[0]}
    chat = {"model": "any", "messages": [{"role": "user", "content": "Reply with OK."}], "max_tokens": 8,
            "reasoning_effort": "none", "stream": False}
    anth = {"model": "any", "max_tokens": 8, "messages": [{"role": "user", "content": "Reply with OK."}]}
    for path, body in (("/v1/chat/completions", chat), ("/v1/messages", anth)):
        matrix[f"POST {path}"] = {"none": http("POST", url + path, body=body)[0],
                                  "wrong": http("POST", url + path, key=wrong, body=body)[0],
                                  "wrong_x_api_key": http("POST", url + path, key=wrong, body=body, x_api_key=True)[0],
                                  "correct": http("POST", url + path, key=key, body=body, timeout=120)[0]}
    # the one mutating control route: only unauthenticated/wrong attempts (a correct POST would change settings)
    matrix["POST /settings"] = {"none": http("POST", url + "/settings", body={"temperature": 2})[0],
                                "wrong": http("POST", url + "/settings", key=wrong, body={"temperature": 2})[0]}
    public = {p: http("GET", url + p)[0] for p in ["/health", "/status", "/"]}
    enforced = all(v["none"] == 401 and v["wrong"] == 401 and v.get("wrong_x_api_key", 401) == 401
                   for v in matrix.values())
    correct_ok = all(v.get("correct", 200) == 200 for v in matrix.values())
    settings_after = http("GET", url + "/settings", key=key)[1]

    refusals = {}
    for label, candidate in (("missing", None), ("empty", ""), ("blank", "   ")):
        try:
            ompcfg.isolated_env(layout, api_key=candidate)
            refusals[label] = "accepted"
        except ompcfg.LauncherError:
            refusals[label] = "refused_before_launch"

    ws = hostrun.git_fixture(layout.work / f"g13-{secrets.token_hex(3)}", {"README.md": "fixture\n"})
    since = time.time()
    wrong_run = hostrun.run_omp(layout, "Reply with OK.", cwd=ws, out_dir=ev, name="wrong-key", max_time_s=90,
                                key=wrong)
    served_for_wrong = engine_requests(layout, key, since)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        dead_port = s.getsockname()[1]
    dead_run = hostrun.run_omp(layout, "Reply with OK.", cwd=ws, out_dir=ev, name="dead-endpoint", max_time_s=90,
                               key=key, base_url=f"http://127.0.0.1:{dead_port}/v1")
    ompcfg.install_profile_config(layout)  # restore the real endpoint for every later run

    # Egress observation over a typed tool turn and a continuation that forces an OMP compaction (the auxiliary
    # summarization path), with the production launcher environment.
    ws2 = hostrun.git_fixture(layout.work / f"g13b-{secrets.token_hex(3)}", {"note.txt": "egress probe\n"})
    pids = {p.pid for p in server_tree(layout)}
    compact = {"compaction": {"enabled": True, "thresholdTokens": 6_000, "keepRecentTokens": 1_000}}
    exits = []
    with NetTrace(ev, "egress") as trace:
        for name, args, overrides in (
                ("egress-tool", ["-p", "--mode", "json", "--auto-approve", "--max-time", "300s",
                                 "Read note.txt with your read tool, then run `git status --short` with your shell "
                                 "tool, and reply with the first word of note.txt."], None),
                ("egress-compaction", ["-p", "--mode", "json", "--auto-approve", "--max-time", "600s", "--continue",
                                       "Reply with just OK."], compact)):
            proc, f = omp_popen(layout, key, ws2, ev / f"{name}.events.jsonl", args, overrides=overrides)
            pids.add(proc.pid)
            watch_tree(proc, pids)
            exits.append(proc.wait())
            f.close()
    ompcfg.install_profile_config(layout)
    egress = trace.attribute(pids, ev / "egress.detail.json")
    sess2 = session_for(layout, ws2)
    compactions = sum(1 for e in (transcript.load(sess2) if sess2 else []) if e.get("type") == "compaction")
    census = route_census(layout)
    result = {
        "auth_matrix": matrix, "public_routes": public, "protected_routes_enforced": enforced,
        "protected_routes_correct_key_ok": correct_ok,
        "settings_unchanged": settings_after == {"shared": False, "defaults": {}},
        "launcher_refusals": refusals,
        "wrong_key_omp": {"exit": wrong_run.exit_code, "wall_ms": wrong_run.wall_ms,
                          "engine_requests": len(served_for_wrong)},
        "dead_endpoint_omp": {"exit": dead_run.exit_code, "wall_ms": dead_run.wall_ms,
                              "timed_out": dead_run.timed_out},
        "egress_probe": {"exits": exits, "compactions_observed": compactions, **egress},
        "route_census": census,
    }
    result["pass_observed"] = bool(
        enforced and correct_ok and result["settings_unchanged"]
        and set(refusals.values()) == {"refused_before_launch"}
        and wrong_run.exit_code != 0 and not served_for_wrong and dead_run.exit_code != 0
        and exits == [0, 0] and compactions >= 1
        and egress.get("conclusive") and egress.get("non_loopback_endpoints") == 0
        and census["providers"] == ["strata-local"] and len(census["models"]) == 1)
    return result


class RawStream:
    """A raw streaming chat request whose socket we can drop at will (a drain thread keeps TCP flowing)."""

    def __init__(self, layout: Layout, key: str, prompt: str, max_tokens: int, drain: bool = True):
        body = json.dumps({"model": "any", "stream": True, "max_tokens": max_tokens, "reasoning_effort": "none",
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        self.sock = socket.create_connection(("127.0.0.1", layout.profile.data["server"]["port"]), timeout=900)
        self.sock.sendall(b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                          b"Content-Type: application/json\r\n" + f"Authorization: Bearer {key}\r\n"
                          f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
        self.received = 0
        if drain:
            threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self) -> None:
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    return
                self.received += len(chunk)
        except OSError:
            return

    def drop(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


def g14(layout: Layout, key: str, ev: Path) -> dict:
    out: dict = {}
    busy_gen = lambda n: (lambda s: bool(s.get("busy")) and (s.get("generated") or 0) > n)  # noqa: E731
    idle = lambda s: not s.get("busy") and not s.get("queued")  # noqa: E731

    # (a) the client dies mid-generation (abrupt transport loss from the server's point of view)
    ws = hostrun.git_fixture(layout.work / f"g14a-{secrets.token_hex(3)}", {"README.md": "fixture\n"})
    since = time.time()
    proc, f = omp_popen(layout, key, ws, ev / "g14a.events.jsonl",
                        ["-p", "--mode", "json", "--thinking", "low", "--max-time", "600s",
                         "Without using any tools, write a very long essay (at least 3000 words) about the history "
                         "of bridges, in many sections."])
    s_busy, ok_busy = wait_status(layout, busy_gen(80), 240)
    t_kill = time.monotonic()
    kill_tree(proc.pid)
    proc.wait(timeout=60)
    f.close()
    _, went_idle = wait_status(layout, idle, 120)
    idle_ms = round((time.monotonic() - t_kill) * 1000)
    reqs = engine_requests(layout, key, since)
    out["client_killed_while_generating"] = {
        "was_generating": ok_busy, "generated_at_kill": s_busy.get("generated"), "server_idle": went_idle,
        "server_idle_after_ms": idle_ms if went_idle else None,
        "engine_finish": [r["finish"] for r in reqs], "engine_output_tokens": [r["output_tokens"] for r in reqs]}

    # (c) a completed side effect, then the client dies during the following generation; resume must not rerun it
    ws3 = hostrun.git_fixture(layout.work / f"g14c-{secrets.token_hex(3)}", {"append.py": APPEND_PY})
    proc, f = omp_popen(layout, key, ws3, ev / "g14c.events.jsonl",
                        ["-p", "--mode", "json", "--auto-approve", "--thinking", "low", "--max-time", "600s",
                         "Run `python append.py` exactly once with your shell tool. After it succeeds, write a very "
                         "long essay (at least 2000 words) about logging, without calling any more tools."])
    deadline = time.monotonic() + 420
    while time.monotonic() < deadline and not (ws3 / "log.txt").exists() and proc.poll() is None:
        time.sleep(0.25)
    side_effect_seen = (ws3 / "log.txt").exists()
    _, gen_after = wait_status(layout, busy_gen(60), 240)
    kill_tree(proc.pid)
    proc.wait(timeout=60)
    f.close()
    wait_status(layout, idle, 120)
    lines_before = (ws3 / "log.txt").read_text().count("ran") if side_effect_seen else 0
    resumed = hostrun.run_omp(layout, "Continue from where you stopped. Do not run append.py again. Read log.txt "
                              "with your read tool and reply with its number of lines as `LINES: <n>`.", cwd=ws3,
                              out_dir=ev, name="g14c-resume", max_time_s=420, continue_session=True, key=key)
    lines_after = (ws3 / "log.txt").read_text().count("ran") if (ws3 / "log.txt").exists() else 0
    sess3 = session_for(layout, ws3)
    appends = count_calls(sess3, "append.py")
    out["side_effect_then_client_loss"] = {
        "side_effect_seen": side_effect_seen, "killed_during_generation": gen_after,
        "log_lines_before_resume": lines_before, "log_lines_after_resume": lines_after,
        "append_calls_in_transcript": appends, "resume_exit": resumed.exit_code,
        "resume_reports_one_line": "LINES: 1" in resumed.final_text().replace("**", "")}

    # (d) a tool fails, then the turn still completes validly
    ws4 = hostrun.git_fixture(layout.work / f"g14d-{secrets.token_hex(3)}", {"README.md": "fixture\n"})
    failing = hostrun.run_omp(layout, "Run `python -c \"import sys; sys.exit(3)\"` with your shell tool exactly once, "
                              "then report its exit code as `EXIT: <n>`.", cwd=ws4, out_dir=ev, name="g14d",
                              max_time_s=420, key=key)
    sess4 = session_for(layout, ws4)
    out["failed_tool_then_valid_turn"] = {"exit": failing.exit_code,
                                          "reported": "EXIT: 3" in failing.final_text().replace("**", ""),
                                          "stops": [r["stop"] for r in assistant_usages(sess4)]}

    # (b) last, because its aftermath is itself under test: one request generating, a second queued behind it;
    # the queued client disconnects, then the first; then five ordinary requests must all be served normally
    engine_before = engine_proc(layout)
    since = time.time()
    a = RawStream(layout, key, "Count from 1 to 3000, one number per line, nothing else.", 8000)
    _, a_busy = wait_status(layout, busy_gen(20), 180)
    b = RawStream(layout, key, "Say hello.", 32, drain=False)
    _, queued = wait_status(layout, lambda s: (s.get("queued") or 0) >= 1, 30)
    b.drop()
    time.sleep(2)
    g1 = status_json(layout).get("generated") or 0
    time.sleep(3)
    s2 = status_json(layout)
    a_continued = bool(s2.get("busy")) and (s2.get("generated") or 0) > g1
    t_drop = time.monotonic()
    a.drop()
    _, drained = wait_status(layout, idle, 180)
    drain_ms = round((time.monotonic() - t_drop) * 1000)
    follow_ups = []
    for i in range(5):
        st, resp = http("POST", base(layout) + "/v1/chat/completions", key=key, timeout=300,
                        body={"model": "any", "max_tokens": 16, "reasoning_effort": "none", "stream": False,
                              "messages": [{"role": "user", "content": f"Reply with the single word READY{i}."}]})
        text = ((resp.get("choices") or [{}])[0].get("message") or {}).get("content", "") \
            if isinstance(resp, dict) and st == 200 else ""
        err = (resp.get("error") or {}).get("message", "")[:160] if isinstance(resp, dict) and resp.get("error") else None
        follow_ups.append({"status": st, "correct": f"READY{i}" in (text or "").upper(), "error": err})
    engine_after = engine_proc(layout)
    reqs = engine_requests(layout, key, since)
    out["queued_client_cancelled"] = {
        "first_generating": a_busy, "queued_observed": queued, "first_continued_after_queued_drop": a_continued,
        "idle_after_first_dropped": drained, "idle_after_ms": drain_ms if drained else None,
        "follow_up_requests": follow_ups,
        "engine_restarted_during_follow_ups": bool(engine_before and engine_after
                                                   and engine_after.pid != engine_before.pid),
        "engine_records": [{"finish": r["finish"], "output_tokens": r["output_tokens"]} for r in reqs]}
    c, q, s3, d = (out["client_killed_while_generating"], out["queued_client_cancelled"],
                   out["side_effect_then_client_loss"], out["failed_tool_then_valid_turn"])
    out["pass_observed"] = bool(c["was_generating"] and c["server_idle"] and q["queued_observed"]
                                and q["first_continued_after_queued_drop"] and q["idle_after_first_dropped"]
                                and all(x["status"] == 200 and x["correct"] for x in q["follow_up_requests"])
                                and not q["engine_restarted_during_follow_ups"]
                                and s3["side_effect_seen"] and s3["log_lines_before_resume"] == 1
                                and s3["log_lines_after_resume"] == 1 and s3["append_calls_in_transcript"] == 1
                                and s3["resume_exit"] == 0 and d["exit"] == 0 and d["reported"])
    return out


def g14q(layout: Layout, key: str, ev: Path) -> dict:
    """Minimal reproduction for the stale-cancel defect first seen in G14 attempt 1: after a queued request's
    client disconnects, the next long-prompt request fails with engine `ERR cancelled` and the engine exits."""
    busy_gen = lambda n: (lambda s: bool(s.get("busy")) and (s.get("generated") or 0) > n)  # noqa: E731
    idle = lambda s: not s.get("busy") and not s.get("queued")  # noqa: E731
    long_prompt = filler(350, {}, seed=1400) + "\n\nReply with the single word OK."  # ~8K tokens, several chunks

    def probe(label: str) -> dict:
        eng = engine_proc(layout)
        r = chat_raw(layout, key, long_prompt + f" ({label})", 8)
        after = engine_proc(layout)
        return {"status": r["status"], "error": (r["error"] or "")[:120] or None,
                "prompt_tokens": r["prompt_tokens"],
                "engine_replaced": bool(eng and after and eng.pid != after.pid) or (eng is not None and after is None)}

    def scenario(queue_b: bool, drop_a: bool) -> dict:
        wait_status(layout, idle, 120)
        a = RawStream(layout, key, "Count from 1 to 3000, one number per line, nothing else.", 400 if not drop_a else 8000)
        _, generating = wait_status(layout, busy_gen(20), 180)
        queued = False
        if queue_b:
            b = RawStream(layout, key, "Say hello.", 32, drain=False)
            _, queued = wait_status(layout, lambda s: (s.get("queued") or 0) >= 1, 30)
            b.drop()
            time.sleep(2)
        if drop_a:
            a.drop()
        wait_status(layout, idle, 300)
        if not drop_a:
            a.drop()
        first = probe("first")
        second = probe("second")
        return {"a_generating": generating, "b_queued": queued, "first_long_request": first,
                "second_long_request": second}

    out = {"control_drop_generating_only": scenario(queue_b=False, drop_a=True),
           "queued_drop_then_generating_drop": scenario(queue_b=True, drop_a=True),
           "queued_drop_generating_completes": scenario(queue_b=True, drop_a=False)}
    out["pass_observed"] = all(v["first_long_request"]["status"] == 200 and v["second_long_request"]["status"] == 200
                               for v in out.values() if isinstance(v, dict))
    return out


def g15(layout: Layout, key: str, ev: Path) -> dict:
    from omp_strata.rpc import RpcOmp

    essay = ("Without using any tools, write a very long essay (at least 3000 words) about {topic}, in many sections.")
    ws, nonce = nonce_fixture(layout, "g15")
    result: dict = {}
    omp = RpcOmp(layout, cwd=ws, stderr_path=ev / "g15.stderr.txt", key=key)
    try:
        seed = omp.prompt(SEED, timeout=600)
        state1 = omp.state()
        (ws / "NONCE.txt").write_text("ROTATED-" + secrets.token_hex(5).upper() + "\n")
        # 1. engine dies while idle; the next request makes stock Strata start it again
        eng = engine_proc(layout)
        killed_idle = bool(eng) and procs.terminate(eng, 30)
        since = time.time()
        r1 = omp.prompt(RECALL, timeout=900)
        new_eng = engine_proc(layout)
        reqs1 = engine_requests(layout, key, since)
        # 2. control: the client aborts a generation (no engine death): same interrupted-turn transcript shape
        t0 = omp.send_prompt(essay.format(topic="canals"))
        _, gen_c = wait_status(layout, lambda s: bool(s.get("busy")) and (s.get("generated") or 0) > 60, 300)
        omp.command("abort")
        aborted = omp.wait_end(t0, timeout=300)
        rc_ctl = omp.prompt(RECALL, timeout=900)
        # 3. engine dies mid-generation; the turn must end as an error, not a false completion
        t0 = omp.send_prompt(essay.format(topic="lighthouses"))
        _, generating = wait_status(layout, lambda s: bool(s.get("busy")) and (s.get("generated") or 0) > 60, 300)
        eng2 = engine_proc(layout)
        killed_mid = bool(eng2) and procs.terminate(eng2, 30)
        cut = omp.wait_end(t0, timeout=300)
        since = time.time()
        r2 = omp.prompt(RECALL, timeout=900)
        r3 = omp.prompt(RECALL, timeout=900)  # diagnostic only: does a second continuation recover?
        reqs2 = engine_requests(layout, key, since)
        state2 = omp.state()
    finally:
        rc = omp.close()

    def stop_of(r: dict) -> str | None:
        s = r["stop"]
        return s if not isinstance(s, str) or len(s) < 40 else s[:60]

    result.update({
        "seed": {"stop": stop_of(seed), "has_nonce": nonce in seed["answer"]},
        "idle_kill": {"engine_killed": killed_idle, "engine_restarted": bool(eng and new_eng and new_eng.pid != eng.pid),
                      "recall_stop": stop_of(r1), "recall_has_nonce": nonce in r1["answer"],
                      "recall_wall_ms": r1["wall_ms"], "engine_records": reqs1},
        "client_abort_control": {"was_generating": gen_c, "aborted_turn_stop": stop_of(aborted),
                                 "recall_stop": stop_of(rc_ctl), "recall_has_nonce": nonce in rc_ctl["answer"]},
        "mid_generation_kill": {"was_generating": generating, "engine_killed": killed_mid,
                                "cut_turn_stop": stop_of(cut), "cut_turn_not_completed": cut["stop"] != "stop",
                                "recall_stop": stop_of(r2), "recall_has_nonce": nonce in r2["answer"],
                                "second_recall_stop": stop_of(r3), "second_recall_has_nonce": nonce in r3["answer"],
                                "recall_wall_ms": r2["wall_ms"], "engine_records": reqs2},
        "same_session": bool(state1.get("session_id")) and state1.get("session_id") == state2.get("session_id"),
        "client_exit": rc,
    })
    result["pass_observed"] = bool(
        nonce in seed["answer"] and killed_idle and nonce in r1["answer"] and r1["stop"] == "stop"
        and generating and killed_mid and cut["stop"] != "stop" and nonce in r2["answer"] and r2["stop"] == "stop"
        and result["same_session"])
    return result


def g16(layout: Layout, key: str, ev: Path, tool: list[str]) -> dict:
    ws = hostrun.git_fixture(layout.work / f"g16-{secrets.token_hex(3)}", {"append.py": APPEND_PY})
    nonce = "G16-" + secrets.token_hex(5).upper()
    (ws / "NONCE.txt").write_text(nonce + "\n")
    t1 = hostrun.run_omp(layout, "Run `python append.py` exactly once with your shell tool, then read NONCE.txt with "
                         "your read tool and reply with exactly `NONCE: <contents>`.", cwd=ws, out_dir=ev,
                         name="g16-t1", max_time_s=600, key=key)
    (ws / "NONCE.txt").write_text("ROTATED\n")
    t2 = hostrun.run_omp(layout, RECALL, cwd=ws, out_dir=ev, name="g16-t2-client-restart", max_time_s=600,
                         continue_session=True, key=key)
    stopped = lifecycle.stop(layout, log=lambda _m: None)
    started = lifecycle.start(layout, tool_argv=tool, log=lambda _m: None)
    since = time.time()
    t3 = hostrun.run_omp(layout, RECALL, cwd=ws, out_dir=ev, name="g16-t3-client-and-server-restart",
                         max_time_s=900, continue_session=True, key=key)
    reqs = engine_requests(layout, key, since)
    sess = session_for(layout, ws)
    appends = count_calls(sess, "append.py")
    lines = (ws / "log.txt").read_text().count("ran") if (ws / "log.txt").exists() else 0
    return {"t1": {"exit": t1.exit_code, "has_nonce": nonce in t1.final_text()},
            "t2_client_restart": {"exit": t2.exit_code, "has_nonce": nonce in t2.final_text(), "wall_ms": t2.wall_ms},
            "server_restart": {"stopped": stopped.get("stopped"), "ready_s": started.get("ready_s"),
                               "engine_found": started.get("engine_found")},
            "t3_client_and_server_restart": {"exit": t3.exit_code, "has_nonce": nonce in t3.final_text(),
                                             "wall_ms": t3.wall_ms, "engine_records": reqs},
            "per_request": assistant_usages(sess), "append_calls": appends, "log_lines": lines,
            "pass_observed": bool(t1.exit_code == 0 and nonce in t1.final_text() and t2.exit_code == 0
                                  and nonce in t2.final_text() and t3.exit_code == 0 and nonce in t3.final_text()
                                  and appends == 1 and lines == 1 and started.get("state") == "healthy")}


def chat_raw(layout: Layout, key: str, content: str, max_tokens: int) -> dict:
    t0 = time.monotonic()
    st, body = http("POST", base(layout) + "/v1/chat/completions", key=key, timeout=3600,
                    body={"model": "any", "max_tokens": max_tokens, "stream": False, "reasoning_effort": "none",
                          "messages": [{"role": "user", "content": content}]})
    usage = body.get("usage") if isinstance(body, dict) else None
    err = (body.get("error") or {}).get("message") if isinstance(body, dict) and body.get("error") else None
    return {"status": st, "prompt_tokens": (usage or {}).get("prompt_tokens"),
            "cached_tokens": ((usage or {}).get("prompt_tokens_details") or {}).get("cached_tokens"),
            "completion_tokens": (usage or {}).get("completion_tokens"), "error": err,
            "wall_ms": round((time.monotonic() - t0) * 1000)}


def g17(layout: Layout, key: str, ev: Path) -> dict:
    from omp_strata import ompcfg

    ctx = layout.profile.data["strata"]["setup_args"]["context"]
    max_out = layout.profile.data["omp"]["max_tokens"]
    q = "\n\nReply with the single word OK."
    # 1. calibrate with the engine's own tokenizer (usage.prompt_tokens; max_tokens=1)
    c0 = chat_raw(layout, key, q.strip(), 1)
    c1 = chat_raw(layout, key, filler(1000, {}, seed=1701) + q, 1)
    per_line = (c1["prompt_tokens"] - c0["prompt_tokens"]) / 1000
    # 2. exact server boundary on a ~100K-token prompt (fresh seed, so the first request is a cold prefill)
    n = int((100_000 - c0["prompt_tokens"]) / per_line)
    big = filler(n, {}, seed=1702) + q
    probe = chat_raw(layout, key, big, 1)
    p = probe["prompt_tokens"]
    fit = chat_raw(layout, key, big, ctx - CTX_SLACK - p)
    over = chat_raw(layout, key, big, ctx - CTX_SLACK - p + 1)
    boundary = {"prompt_tokens": p, "cold_prefill_ms": probe["wall_ms"],
                "fit": {"max_tokens": ctx - CTX_SLACK - p, "status": fit["status"], "cached": fit["cached_tokens"]},
                "over": {"max_tokens": ctx - CTX_SLACK - p + 1, "status": over["status"],
                         "never_truncated_message": "never truncated" in (over["error"] or "")}}
    # 3. OMP near-limit typed tool follow-up with the production configuration. Stock OMP fits each request's
    # max_tokens to the room it estimates is left, so the wire cap is sampled from /status, not assumed.
    overhead = 7_300  # stock OMP system prompt + tool schemas measured on this route (~7.0K) plus instructions
    target_first = 105_000  # below stock OMP's default compaction threshold (131,072 - 19,660 = 111,412)
    lines = int((target_first - overhead) / per_line)
    fa, fb = "ALPHA-" + secrets.token_hex(4).upper(), "OMEGA-" + secrets.token_hex(4).upper()
    corpus = filler(lines, {40: f"The first access code is {fa}.", lines - 12: f"The last access code is {fb}."},
                    seed=1703)
    ws = hostrun.git_fixture(layout.work / f"g17-{secrets.token_hex(3)}", {"corpus.txt": corpus})
    wire: list[tuple[int, int]] = []
    stop_sampling = threading.Event()

    def sample_wire() -> None:  # (prompt_tokens, max_tokens) of each request while it is being served
        while not stop_sampling.is_set():
            s = status_json(layout)
            if s.get("busy") and s.get("prompt_tokens") and s.get("max_tokens"):
                pair = (int(s["prompt_tokens"]), int(s["max_tokens"]))
                if pair not in wire:
                    wire.append(pair)
            stop_sampling.wait(0.1)

    sampler = threading.Thread(target=sample_wire, daemon=True)
    sampler.start()
    since = time.time()
    # stock OMP reads each `@file` MESSAGES argument as one path: the attachment must be its own argv element
    near = hostrun.run_omp(layout, "Using only the attached file, find the first access code and the last access "
                           "code. Then create answer.txt containing exactly those two codes on two lines, using your "
                           "write tool, and reply DONE.", cwd=ws, out_dir=ev, name="g17-near", extra=["@corpus.txt"],
                           max_time_s=1800, key=key)
    stop_sampling.set()
    sampler.join(timeout=10)
    near_reqs = engine_requests(layout, key, since)
    answer = (ws / "answer.txt").read_text() if (ws / "answer.txt").exists() else ""
    sess = session_for(layout, ws)
    rows = assistant_usages(sess)
    compacted = sum(1 for e in (transcript.load(sess) if sess else []) if e.get("type") == "compaction")
    peak = max((r["prompt_tokens"] for r in near_reqs), default=0)
    # 4. OMP overflow with the production configuration: one attached prompt that cannot fit even the minimum
    # 1,024-token output cap stock OMP will request, so Strata must refuse it explicitly
    over_lines = int((ctx + 5_000 - overhead) / per_line)
    ws2 = hostrun.git_fixture(layout.work / f"g17o-{secrets.token_hex(3)}",
                              {"corpus.txt": filler(over_lines, {}, seed=1704)})
    since = time.time()
    t_over = hostrun.run_omp(layout, "Summarize the attached file in one sentence.", cwd=ws2, out_dir=ev,
                             name="g17-overflow", extra=["@corpus.txt"], max_time_s=900, key=key)
    over_reqs = engine_requests(layout, key, since)
    over_sess = session_for(layout, ws2)
    events_text = t_over.events_path.read_text(encoding="utf-8", errors="replace")
    ompcfg.install_profile_config(layout)
    result = {
        "context": ctx, "omp_max_tokens": max_out, "ctx_slack": CTX_SLACK,
        "tokens_per_filler_line": round(per_line, 3), "calibration_base_prompt_tokens": c0["prompt_tokens"],
        "boundary": boundary,
        "near_limit": {"engine_requests": near_reqs, "wire_prompt_and_max_tokens": wire,
                       "peak_prompt_tokens": peak,
                       "max_wire_prompt_plus_cap": max((p + m for p, m in wire), default=None),
                       "exit": near.exit_code, "facts_written": fa in answer and fb in answer,
                       "tool_follow_up": len(near_reqs) >= 2, "stops": [r["stop"] for r in rows],
                       "compactions": compacted, "wall_ms": near.wall_ms},
        "omp_overflow": {"exit": t_over.exit_code, "engine_requests_served": len(over_reqs),
                         "stops": [r["stop"] for r in assistant_usages(over_sess)],
                         "error_surfaced": "never truncated" in events_text or "exceeds the context" in events_text,
                         "wall_ms": t_over.wall_ms},
    }
    result["pass_observed"] = bool(
        fit["status"] == 200 and over["status"] == 400 and boundary["over"]["never_truncated_message"]
        and near.exit_code == 0 and fa in answer and fb in answer and len(near_reqs) >= 2 and peak >= 100_000
        and wire and all(p + m + CTX_SLACK <= ctx for p, m in wire)
        and t_over.exit_code != 0 and not over_reqs and result["omp_overflow"]["error_surfaced"])
    return result


def g18(layout: Layout, key: str, ev: Path) -> dict:
    threshold = 12_000
    overrides = {"compaction": {"enabled": True, "thresholdTokens": threshold, "keepRecentTokens": 2_000}}
    fact = "KEEP-" + secrets.token_hex(4).upper()
    files = {f"part{i}.txt": filler(150, {3: f"Section {i} marker."}, seed=180 + i) for i in range(1, 7)}
    files["calc.py"] = "def add(a, b):\n    return a - b\n"
    ws = hostrun.git_fixture(layout.work / f"g18-{secrets.token_hex(3)}", files)
    runs = [hostrun.run_omp(layout, f"Remember this project code for later: {fact}. Reply with just OK.", cwd=ws,
                            out_dir=ev, name="g18-t0", max_time_s=600, key=key, overrides=overrides)]
    for i in range(1, 7):
        runs.append(hostrun.run_omp(layout, f"Read part{i}.txt with your read tool and reply with its last line "
                                    "number only.", cwd=ws, out_dir=ev, name=f"g18-t{i}", max_time_s=600,
                                    continue_session=True, key=key, overrides=overrides))
    final = hostrun.run_omp(layout, "Fix the bug in calc.py with your edit tool so that add returns the sum, then reply "
                            "with exactly `CODE: <the project code I asked you to remember>`.", cwd=ws, out_dir=ev,
                            name="g18-final", max_time_s=900, continue_session=True, key=key, overrides=overrides)
    sess = session_for(layout, ws)
    entries = transcript.load(sess) if sess else []
    compactions = [e for e in entries if e.get("type") == "compaction"]
    aux = [e for e in entries if e.get("type") == "model_usage"]
    fixed = "a + b" in (ws / "calc.py").read_text()
    s = transcript.summarize(sess) if sess else {}
    return {"threshold_tokens": threshold, "keep_recent_tokens": 2_000, "compactions": len(compactions),
            "compaction_tokens_before": [c.get("tokensBefore") for c in compactions],
            "auxiliary_calls": [{"provider": m.get("provider"), "model": m.get("model")} for m in aux],
            "providers": s.get("providers"), "tool_count": s.get("tool_count"),
            "calls_without_results": len(s.get("calls_without_results") or []),
            "turn_exits": [r.exit_code for r in runs],
            "final": {"exit": final.exit_code, "calc_fixed": fixed, "fact_retained": fact in final.final_text(),
                      "wall_ms": final.wall_ms},
            "pass_observed": bool(compactions and final.exit_code == 0 and fixed and fact in final.final_text()
                                  and s.get("providers") == ["strata-local"]
                                  and all(m.get("provider") == "strata-local" for m in aux)
                                  and all(r.exit_code == 0 for r in runs))}


def g18l(layout: Layout, key: str, ev: Path) -> dict:
    """Long-session compaction with the production configuration (the profile claims long sessions): a session
    grows through ordinary read-tool turns past stock OMP's default threshold, compacts, and must still finish
    a typed tool turn that needs a fact from before the compaction."""
    fact = "KEEP-" + secrets.token_hex(4).upper()
    n_docs = 20
    files = {f"doc{i:02d}.txt": filler(280, {5: f"Document {i} marker."}, seed=1800 + i) for i in range(1, n_docs + 1)}
    files["calc.py"] = "def add(a, b):\n    return a - b\n"
    ws = hostrun.git_fixture(layout.work / f"g18l-{secrets.token_hex(3)}", files)
    since = time.time()
    runs = [hostrun.run_omp(layout, f"Remember this project code for later: {fact}. Reply with just OK.", cwd=ws,
                            out_dir=ev, name="g18l-t00", max_time_s=600, key=key)]
    for i in range(1, n_docs + 1):
        runs.append(hostrun.run_omp(layout, f"Read all of doc{i:02d}.txt with your read tool and reply with its last "
                                    "line number only.", cwd=ws, out_dir=ev, name=f"g18l-t{i:02d}", max_time_s=600,
                                    continue_session=True, key=key))
        sess = session_for(layout, ws)
        if sess and any(e.get("type") == "compaction" for e in transcript.load(sess)) and i >= 3:
            break  # compacted at the production threshold: the long-session transition happened
    final = hostrun.run_omp(layout, "Fix the bug in calc.py with your edit tool so that add returns the sum, then reply "
                            "with exactly `CODE: <the project code I asked you to remember>`.", cwd=ws, out_dir=ev,
                            name="g18l-final", max_time_s=900, continue_session=True, key=key)
    reqs = engine_requests(layout, key, since)
    sess = session_for(layout, ws)
    entries = transcript.load(sess) if sess else []
    compactions = [e for e in entries if e.get("type") == "compaction"]
    fixed = "a + b" in (ws / "calc.py").read_text()
    s = transcript.summarize(sess) if sess else {}
    return {"configuration": "production (no overrides)", "doc_turns": len(runs) - 1,
            "compactions": len(compactions),
            "compaction_tokens_before": [c.get("tokensBefore") for c in compactions],
            "compaction_tokens_after": [c.get("tokensAfter") for c in compactions],
            "peak_engine_prompt_tokens": max((r["prompt_tokens"] for r in reqs), default=None),
            "engine_request_finishes": sorted({r["finish"] for r in reqs}),
            "providers": s.get("providers"), "tool_count": s.get("tool_count"),
            "calls_without_results": len(s.get("calls_without_results") or []),
            "turn_exits": [r.exit_code for r in runs],
            "final": {"exit": final.exit_code, "calc_fixed": fixed, "fact_retained": fact in final.final_text(),
                      "wall_ms": final.wall_ms},
            "pass_observed": bool(compactions and final.exit_code == 0 and fixed and fact in final.final_text()
                                  and s.get("providers") == ["strata-local"]
                                  and all(r.exit_code == 0 for r in runs)
                                  and min(c.get("tokensBefore") or 0 for c in compactions) > 100_000)}


def g19(layout: Layout, key: str, ev: Path) -> dict:
    from omp_strata.rpc import RpcOmp

    wa, na = nonce_fixture(layout, "g19a")
    wb, nb = nonce_fixture(layout, "g19b")
    a1 = hostrun.run_omp(layout, SEED, cwd=wa, out_dir=ev, name="a1", key=key)
    b1 = hostrun.run_omp(layout, SEED, cwd=wb, out_dir=ev, name="b1", key=key)
    (wa / "NONCE.txt").write_text("ROTATED-A\n")
    (wb / "NONCE.txt").write_text("ROTATED-B\n")
    a2 = hostrun.run_omp(layout, RECALL, cwd=wa, out_dir=ev, name="a2", continue_session=True, key=key)
    b2 = hostrun.run_omp(layout, RECALL, cwd=wb, out_dir=ev, name="b2", continue_session=True, key=key)
    sa = session_for(layout, wa)
    a3 = hostrun.run_omp(layout, RECALL, cwd=wa, out_dir=ev, name="a3-resume", extra=["--resume", str(sa)],
                         key=key) if sa else None
    # branch canary: a fact added after the branch point must not exist on the branch
    wc, nc = nonce_fixture(layout, "g19c")
    codeword = "CW-" + secrets.token_hex(4).upper()
    omp = RpcOmp(layout, cwd=wc, stderr_path=ev / "g19c.stderr.txt", key=key)
    try:
        c1 = omp.prompt(SEED, timeout=600)
        c2 = omp.prompt(f"Remember this codeword: {codeword}. Reply with just OK.", timeout=600)
        original = omp.state()
        point = next((m for m in omp.branch_points() if codeword in (m.get("text") or "")), None)
        branched = omp.branch(point["entryId"]) if point else {}
        branch_state = omp.state()
        c3 = omp.prompt("Do not call any tools. Reply with exactly `NONCE: <the NONCE.txt contents you read>; "
                        "CODEWORD: <the codeword I gave you, or NONE if I never gave one>`.", timeout=600)
    finally:
        omp.close()
    orig_text = Path(original["session_file"]).read_text(encoding="utf-8") if original.get("session_file") else ""
    ta, tb, tc = a2.final_text(), b2.final_text(), c3["answer"]
    a3t = a3.final_text() if a3 else ""
    result: dict = {
        "interleave": {"a2_correct": na in ta and nb not in ta, "b2_correct": nb in tb and na not in tb,
                       "a3_resume_correct": na in a3t and nb not in a3t,
                       "exits": [a1.exit_code, b1.exit_code, a2.exit_code, b2.exit_code, a3.exit_code if a3 else None],
                       "per_request_a": assistant_usages(sa), "per_request_b": assistant_usages(session_for(layout, wb))},
        "branch": {"seed_ok": nc in c1["answer"], "codeword_turn_stop": c2["stop"], "branch_point_found": bool(point),
                   "branched": bool(branched) and not branched.get("cancelled"),
                   "new_session_file": branch_state.get("session_file") != original.get("session_file"),
                   "branch_has_nonce": nc in tc, "branch_lacks_codeword": codeword not in tc,
                   "original_keeps_codeword": codeword in orig_text},
    }
    i, br = result["interleave"], result["branch"]
    result["pass_observed"] = bool(i["a2_correct"] and i["b2_correct"] and i["a3_resume_correct"]
                                   and all(x == 0 for x in i["exits"]) and br["seed_ok"] and br["branched"]
                                   and br["branch_has_nonce"] and br["branch_lacks_codeword"]
                                   and br["original_keeps_codeword"])
    return result


def host_state(layout: Layout) -> dict:
    """Unrelated host state the integration must leave alone (derived facts only)."""
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    appdata = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
    omp_dir = home / ".omp"
    newest = 0.0
    if omp_dir.is_dir():
        for p in omp_dir.rglob("*"):
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                pass
    root_created = layout.root.stat().st_ctime
    tasks = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-ScheduledTask | Where-Object TaskName -like 'OMP-*' | "
                            "ForEach-Object { $_.TaskName + '=' + $_.State }"],
                           capture_output=True, text=True, stdin=DEVNULL, timeout=120).stdout.split()
    return {"stock_strata_appdata_absent": not (appdata / "Strata").exists(),
            "user_omp_dir_untouched_since_root_created": newest < root_created,
            "scheduled_task_states": sorted(tasks)}


def g20(layout: Layout, key: str, ev: Path, tool: list[str]) -> dict:
    before_state = host_state(layout)
    before = lifecycle.status(layout)
    tree_before = server_tree(layout)
    s1 = lifecycle.stop(layout, log=lambda _m: None)
    after_stop = lifecycle.status(layout)
    leftovers = [Path(p.exe).name for p in tree_before if procs.matches(p.as_dict()) is not None]
    srv = layout.profile.data["server"]
    port_free = not lifecycle.port_in_use(srv["listen_host"], srv["port"])
    gpu_after_stop = lifecycle.gpu_facts(layout.profile.data["host"]["gpu_index"])
    s2 = lifecycle.stop(layout, log=lambda _m: None)
    t0 = time.monotonic()
    started = lifecycle.start(layout, tool_argv=tool, log=lambda _m: None)
    wall = round(time.monotonic() - t0, 1)
    healthy = lifecycle.status(layout)
    refused = None
    try:
        lifecycle.start(layout, tool_argv=tool, log=lambda _m: None)
    except lifecycle.LifecycleError as exc:
        refused = str(exc)[:120]
    ws, nonce = nonce_fixture(layout, "g20")
    smoke = hostrun.run_omp(layout, SEED, cwd=ws, out_dir=ev, name="g20-smoke", max_time_s=600, key=key)
    after_state = host_state(layout)
    return {"before": before["state"], "stopped": s1.get("stopped"), "after_stop": after_stop["state"],
            "orphans_after_stop": leftovers, "port_released": port_free,
            "gpu_after_stop": {"memory_used_mib": gpu_after_stop.get("memory_used_mib"),
                               "compute_apps": gpu_after_stop.get("compute_apps")},
            "repeat_stop": s2.get("state"), "restart": {"ready_s": started.get("ready_s"), "wall_s": wall,
                                                       "engine_found": started.get("engine_found")},
            "after_restart": healthy["state"], "second_start_refused": refused,
            "smoke_after_restart": {"exit": smoke.exit_code, "has_nonce": nonce in smoke.final_text()},
            "host_state_before": before_state, "host_state_after": after_state,
            "pass_observed": bool(before["state"] == "healthy" and after_stop["state"] == "stopped" and not leftovers
                                  and port_free and s2.get("state") == "stopped" and healthy["state"] == "healthy"
                                  and refused and smoke.exit_code == 0 and nonce in smoke.final_text()
                                  and before_state == after_state and after_state["stock_strata_appdata_absent"]
                                  and after_state["user_omp_dir_untouched_since_root_created"])}


def g21(layout: Layout, key: str, ev: Path) -> dict:
    def size(p: Path) -> int:
        if p.is_file():
            return p.stat().st_size
        total = 0
        for f in p.rglob("*"):
            try:
                if f.is_file() and not f.is_symlink():
                    total += f.stat().st_size
            except OSError:
                pass
        return total

    disk = {d.name: size(d) for d in sorted(layout.root.iterdir()) if d.name not in ("evidence",)}
    results = []
    for f in sorted((layout.root / "evidence").glob("*/result.json")):
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        results.append({"gate": r.get("gate"), "pass_observed": r.get("pass_observed"),
                        "error": bool(r.get("error")), "peak_gpu_used_mib": (r.get("resources") or {}).get("gpu_used_mib"),
                        "min_available_ram_bytes": (r.get("resources") or {}).get("min_available_ram_bytes")})
    logs = sorted(layout.logs.glob("server-*.log"))
    text = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in logs)
    engine_events = {  # stock serve/server.py messages; induced kills (G15) are included and named in the receipt
        "stopped_mid_request": text.count("the engine stopped unexpectedly"),
        "found_dead_and_restarted": text.count("the engine had stopped"),
        "engine_error_lines": text.count("the engine reported an error"),
        "requests_ended_error": text.count("(error, cancel="),
        "requests_ended_disconnect": text.count("(disconnect, cancel="),
    }
    run = json.loads(layout.run_record.read_text()) if layout.run_record.exists() else {}
    return {"disk_bytes": disk, "disk_total_bytes": sum(disk.values()), "server_tree_memory": tree_memory(layout),
            "current_ready_s": run.get("ready_s"), "gate_results": results, "server_logs": len(logs),
            "engine_events": engine_events, "pass_observed": None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gate", choices=["g10", "g12", "g13", "g14", "g14q", "g15", "g16", "g17", "g18", "g18l", "g19",
                                     "g20", "g21"])
    ap.add_argument("--profile", required=True)
    ap.add_argument("--root")
    ap.add_argument("--deep", action="store_true", help="g10: rehash every pinned artifact")
    ap.add_argument("--runs", nargs="*", default=[], help="g12: tracer run ids")
    a = ap.parse_args()
    layout = Layout(root=Path(a.root).resolve() if a.root else default_root().resolve(), profile=load(Path(a.profile)))
    key = lifecycle.ensure_healthy(layout)
    run_id = hostrun.new_run_id(a.gate)
    ev = hostrun.evidence_dir(layout, run_id)
    tool = lifecycle.tool_argv()
    t0 = time.monotonic()
    result: dict = {}
    with Sampler() as sampler:
        try:
            if a.gate == "g10":
                result = g10(layout, key, ev, a.deep)
            elif a.gate == "g12":
                result = g12(layout, key, ev, a.runs)
            elif a.gate in ("g16", "g20"):
                result = globals()[a.gate](layout, key, ev, tool)
            else:
                result = globals()[a.gate](layout, key, ev)
        except Exception as exc:  # noqa: BLE001 - a crashed probe is a recorded failure, never a silent pass
            result = {"error": f"{type(exc).__name__}: {exc}"[:600], "traceback_tail": traceback.format_exc()[-1500:],
                      "pass_observed": False}
    result.update({"run_id": run_id, "gate": a.gate.upper(), "utc": hostrun.utc_now(),
                   "wall_s": round(time.monotonic() - t0, 1), "resources": sampler.peak,
                   "resource_samples": sampler.samples, "server_tree_memory_end": tree_memory(layout),
                   "profile_fingerprint": layout.profile.fingerprint,
                   "runtime_identity_sha256": json.loads(layout.install_record.read_text())["runtime_identity_sha256"]})
    hostrun.write_raw(ev, "result.json", result)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
