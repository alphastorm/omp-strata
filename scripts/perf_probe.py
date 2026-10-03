#!/usr/bin/env python3
"""Compare profile variants on their own GPU host; never starts or changes the server.

  python scripts/perf_probe.py --profile profiles/<id>.json --root <integration-root>
  python scripts/perf_probe.py --profile profiles/<id>.json --root <integration-root> \
      --depths 0,8K,32K,64K,100K --warm-depth 32K --max-tokens 512 --timeout 600

K means 1024 tokens. Depth is the target total rendered input (0 means the minimal
instruction). The authenticated count_tokens endpoint counts the same single-user,
thinking-disabled template without warming inference. Inputs are capped at window
minus output allowance minus Strata's 8-token slack. Actual usage is authoritative.
Each cold-prefix input starts with an independent nonce; the warm repeat deliberately
reuses one exact input immediately. This is live prefix reuse, NOT process-cold or
restart restoration. Even unique inputs share the unavoidable chat-template tokens.

TTFT is dispatch to first content OR reasoning delta, excluding comments/empty deltas.
Client delta gaps are reported as inter-output-event p50/p95; they are NOT token
latencies (MTP and UTF-8/parser buffering can batch tokens). True inter-token latency
is unavailable. Prefill/decode rates use server timings only, never client wall time.
MTP acceptance uses /metrics totals deltas; an exclusive idle server is required.
Queue wait is a /status queued>0 polling interval, with lower/upper bounds, excluding
unobserved transport time. It is not TTFT minus server prefill. Two requests must
complete and queuing must be observed, otherwise the run fails rather than inventing
an exact wait. Increase --max-tokens if the first request finishes before polling.

One JSON record goes to stdout and <root>/evidence/perf-<id>/result.json; a short table
goes to stderr. No prompts, responses, keys or raw endpoint bodies are retained.
Exit 1: protocol/identity failure; 124: bounded request timeout; 2: invalid arguments.
No GPU qualification gate or release ledger is changed by this exploratory probe.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import math
import secrets
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata import lifecycle
from omp_strata.common import atomic_write_json, utc_now
from omp_strata.layout import Layout
from omp_strata.profile import load

INSTRUCTION = "Write a complete Python thread-safe LRU cache with TTL, statistics and unit tests. Output code only."


class ProtocolError(RuntimeError):
    pass


def metric(name, value, unit, boundary, method):
    return dict(name=name, value=value, unit=unit, boundary=boundary,
                method=method if value is not None else "unavailable")


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * fraction
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


class Client:
    def __init__(self, base, key, model, timeout):
        url = urlsplit(base)
        if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1") or url.path
                or url.username or url.password or url.query or url.fragment):
            raise ProtocolError("only the profile's loopback HTTP server is permitted")
        self.host, self.port = url.hostname, url.port
        self.key, self.model, self.timeout = key, model, timeout

    def request(self, path, body=None, stream=False):
        """A timer interrupts even trickling responses: timeout is total, not inactivity."""
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        expired = threading.Event()
        active_socket = None

        def abort():
            expired.set()
            sock = active_socket or connection.sock
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        timer = threading.Timer(self.timeout, abort)
        timer.daemon = True
        started = time.monotonic()
        timer.start()
        try:
            connection.request("POST" if body is not None else "GET", path,
                               json.dumps(body).encode() if body is not None else None,
                               {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
            active_socket = connection.sock
            response = connection.getresponse()
            if response.status != 200:
                raise ProtocolError(f"HTTP {response.status} on {path}")
            if stream:
                if response.getheader("Content-Type", "").split(";")[0] != "text/event-stream":
                    raise ProtocolError("chat response is not SSE")
                result = self.consume(response, started)
            else:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise ProtocolError("oversized JSON response")
                result = json.loads(raw)
                if not isinstance(result, dict) or "error" in result:
                    raise ProtocolError("invalid JSON response")
            if expired.is_set():
                raise TimeoutError
            return result
        except (OSError, http.client.HTTPException, ValueError, ProtocolError) as exc:
            if expired.is_set() or isinstance(exc, (TimeoutError, socket.timeout)):
                raise TimeoutError("request deadline exceeded") from None
            raise ProtocolError("invalid or interrupted HTTP response") from None
        finally:
            timer.cancel()
            connection.close()

    def consume(self, response, started):
        times, first_event, first_reasoning, first_text = [], None, None, None
        usage, timings, finish, data = None, {}, None, []
        while True:
            raw = response.readline(1024 * 1024 + 1)
            if not raw or len(raw) > 1024 * 1024:
                raise ProtocolError("SSE ended without a valid final response")
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
                continue
            if line or not data:
                continue
            payload, data = "\n".join(data), []
            now = (time.monotonic() - started) * 1000
            if payload == "[DONE]":
                if finish not in ("stop", "length") or usage is None or not times:
                    raise ProtocolError("missing content, finish reason or usage")
                break
            event = json.loads(payload)
            if not isinstance(event, dict) or "error" in event:
                raise ProtocolError("invalid SSE event")
            if first_event is None:
                first_event = now
            choices = event.get("choices")
            if not isinstance(choices, list) or len(choices) > 1:
                raise ProtocolError("invalid SSE choices")
            for choice in choices:
                if not isinstance(choice, dict) or not isinstance(choice.get("delta"), dict):
                    raise ProtocolError("invalid SSE delta")
                delta = choice["delta"]
                for key in ("content", "reasoning_content"):
                    if delta.get(key) is not None and not isinstance(delta[key], str):
                        raise ProtocolError("invalid text delta")
                if delta.get("tool_calls"):
                    raise ProtocolError("unexpected tool call")
                if delta.get("content") or delta.get("reasoning_content"):
                    times.append(now)
                if delta.get("content") and first_text is None:
                    first_text = now
                if delta.get("reasoning_content") and first_reasoning is None:
                    first_reasoning = now
                if choice.get("finish_reason") is not None:
                    finish = choice["finish_reason"]
            if event.get("usage") is not None:
                usage = event["usage"]
                if not isinstance(usage, dict) or any(not number(usage.get(k)) for k in ("prompt_tokens", "completion_tokens")):
                    raise ProtocolError("invalid usage")
            if event.get("timings") is not None:
                timings = event["timings"]
                if not isinstance(timings, dict):
                    raise ProtocolError("invalid timings")
        gaps = [b - a for a, b in zip(times, times[1:])]
        metrics = [metric(name, value, "ms", boundary, "monotonic_wall_clock") for name, value, boundary in (
            ("request_wall_ms", now, "dispatch to valid final SSE response"),
            ("ttft_ms", times[0], "dispatch to first nonempty content or reasoning delta"),
            ("first_event_ms", first_event, "dispatch to first JSON SSE event, excluding comments"),
            ("first_reasoning_ms", first_reasoning, "dispatch to first nonempty reasoning delta"),
            ("first_visible_text_ms", first_text, "dispatch to first nonempty content delta"))]
        for p in (50, 95):
            metrics.append(metric(f"inter_output_event_latency_p{p}_ms", percentile(gaps, p / 100), "ms",
                                  "gaps between content/reasoning SSE events; not individual tokens", "calculated"))
            metrics.append(metric(f"inter_token_latency_p{p}_ms", None, "ms",
                                  "individual engine token timestamps are not exposed", "unavailable"))
        for name, count, duration in (("prefill_tokens_s", "prompt_n", "prompt_ms"),
                                       ("decode_tokens_s", "predicted_n", "predicted_ms")):
            n, ms = timings.get(count), timings.get(duration)
            if n is not None and not number(n) or ms is not None and not number(ms):
                raise ProtocolError("invalid server timing")
            metrics.append(metric(name, n * 1000 / ms if number(n) and number(ms) and ms > 0 else None,
                                  "tokens/s", f"server timings {count} / {duration}; excludes client wall time", "calculated"))
            metrics.append(metric(duration, ms, "ms", "engine-reported timing", "server_reported"))
        details = usage.get("prompt_tokens_details") or {}
        if not isinstance(details, dict):
            raise ProtocolError("invalid token details")
        cached = details.get("cached_tokens")
        if cached is not None and not number(cached):
            raise ProtocolError("invalid cached token count")
        for name, value in (("prompt_tokens", usage["prompt_tokens"]), ("completion_tokens", usage["completion_tokens"]),
                            ("cached_tokens", cached)):
            metrics.append(metric(name, value, "tokens", "server response usage", "server_reported"))
        return {"finish_reason": finish, "complete": True, "metrics": metrics}

    def count(self, text):
        result = self.request("/v1/messages/count_tokens", {"model": self.model,
                              "messages": [{"role": "user", "content": text}], "thinking": {"type": "disabled"}})
        count = result.get("input_tokens")
        if type(count) is not int or count <= 0:
            raise ProtocolError("invalid token count")
        return count

    def chat(self, text, max_tokens):
        return self.request("/v1/chat/completions", {"model": self.model, "stream": True,
                            "stream_options": {"include_usage": True}, "temperature": 0,
                            "reasoning_effort": "none", "max_tokens": max_tokens,
                            "messages": [{"role": "user", "content": text}]}, stream=True)


def value(row, name):
    return next(m["value"] for m in row["metrics"] if m["name"] == name)


def prompt_for(client, depth, budget):
    # Nonce is the first user bytes, before any shared instruction or filler.
    head = secrets.token_hex(16) + "\n"
    tail = "\n" + INSTRUCTION
    base = client.count(head + tail)
    if base > budget:
        raise ProtocolError("output allowance leaves no room for the minimal prompt")
    target = min(max(base, depth), budget)
    lo, hi = 0, target
    # Repeated simple words provide bounded, deterministic filler; never estimate tokens from bytes.
    best, tokens = head + tail, base
    while lo <= hi:
        mid = (lo + hi) // 2
        text = head + " datum" * mid + tail
        count = client.count(text)
        if count <= target:
            best, tokens, lo = text, count, mid + 1
        else:
            hi = mid - 1
    return best, tokens, target


def acceptance(before, after, expected):
    old, new = before.get("totals"), after.get("totals")
    if not isinstance(old, dict) or not isinstance(new, dict):
        raise ProtocolError("missing metrics totals")
    if not number(old.get("requests")) or not number(new.get("requests")) or new["requests"] - old["requests"] != expected:
        raise ProtocolError("metrics request delta mismatch; use an exclusive idle server")
    counts = []
    for key in ("drafts_offered", "drafts_accepted"):
        a, b = old.get(key), new.get(key)
        if a is None or b is None:
            counts.append(None)
        elif not number(a) or not number(b) or b < a:
            raise ProtocolError("invalid draft counter delta")
        else:
            counts.append(b - a)
    offered, accepted = counts
    if offered is not None and accepted is not None and accepted > offered:
        raise ProtocolError("accepted drafts exceed offered drafts")
    return [metric("mtp_" + name, count, "tokens", "exclusive /metrics totals delta", "calculated")
            for name, count in zip(("drafts_offered", "drafts_accepted"), counts)] + [
        metric("mtp_acceptance", accepted / offered if offered and accepted is not None else None,
               "ratio", "accepted / offered draft counter deltas; zero offers is unavailable", "calculated")]


def queue_pair(client, first, second, max_tokens):
    before = client.request("/metrics")
    deadline = time.monotonic() + client.timeout
    samples = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(client.chat, first, max_tokens)
        while not client.request("/status").get("busy"):
            if a.done() or time.monotonic() >= deadline:
                raise ProtocolError("first queue request did not stay active")
            time.sleep(0.01)
        dispatched = time.monotonic()
        b = pool.submit(client.chat, second, max_tokens)
        while not b.done():
            start = time.monotonic()
            status = client.request("/status")
            end = time.monotonic()
            queued = status.get("queued")
            if type(queued) is not int or queued < 0 or queued > 1:
                raise ProtocolError("invalid or nonexclusive queue state")
            samples.append((start, end, queued))
            if time.monotonic() >= deadline:
                raise TimeoutError("queue deadline exceeded")
            time.sleep(0.01)
        rows = [a.result(), b.result()]
    queued = [i for i, (_, _, n) in enumerate(samples) if n == 1]
    if not queued:
        raise ProtocolError("queuing not observed; increase output allowance")
    first_i, last_i = queued[0], queued[-1]
    # Each response brackets an observation at some unknown instant inside its GET.
    lower = max(0, samples[last_i][0] - samples[first_i][1]) * 1000
    upper_end = samples[last_i + 1][1] if last_i + 1 < len(samples) else time.monotonic()
    upper = (upper_end - dispatched) * 1000
    rows[1]["metrics"] += [metric("queue_wait_lower_ms", lower, "ms", "observed queued interval, conservative lower bound", "monotonic_wall_clock"),
                           metric("queue_wait_upper_ms", upper, "ms", "dispatch to first poll after queue clears, upper bound", "monotonic_wall_clock")]
    return {"requests": rows, "both_complete": True, "queued_observed": True,
            "metrics": acceptance(before, client.request("/metrics"), 2)}


def run(layout, depths, warm_depth, max_tokens, timeout):
    profile = layout.profile
    window = profile.data["strata"]["setup_args"]["context"]
    budget = window - max_tokens - 8
    client = Client(lifecycle.base_url(layout), lifecycle.read_key(layout), profile.data["strata"]["model_name"], timeout)
    health = client.request("/health")
    if health.get("status") != "ok" or health.get("max_context") != window or health.get("model") != client.model or health.get("api_key") is not True or health.get("loaded") is False:
        raise ProtocolError("health does not match the authenticated loaded profile")
    status = client.request("/status")
    if status.get("busy") is not False or status.get("queued") != 0:
        raise ProtocolError("server must be idle and exclusive")
    rows = []
    for depth in dict.fromkeys([*depths, warm_depth]):
        text, actual, target = prompt_for(client, depth, budget)
        for label in (["unique_prefix", "warm_repeat"] if depth == warm_depth else ["unique_prefix"]):
            before = client.request("/metrics")
            row = client.chat(text, max_tokens)
            if value(row, "prompt_tokens") != actual or actual > budget:
                raise ProtocolError("count_tokens and completion usage disagree")
            row.update(scenario=label, requested_depth=depth, capped_target=target)
            row["metrics"] += acceptance(before, client.request("/metrics"), 1)
            rows.append(row)
    first, _, _ = prompt_for(client, 0, budget)
    second, _, _ = prompt_for(client, 0, budget)
    return {"samples": rows, "queue": queue_pair(client, first, second, max_tokens),
            "context_window": window, "max_tokens": max_tokens}


def depth_arg(text):
    try:
        value = int(text[:-1]) * 1024 if text.lower().endswith("k") else int(text)
        if not 0 <= value <= 1048576:
            raise ValueError
        return value
    except ValueError:
        raise argparse.ArgumentTypeError("depth must be 0..1048576 tokens, optionally suffixed K") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--depths", default="0,8K,32K,64K,100K")
    parser.add_argument("--warm-depth", type=depth_arg, default=32768)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args(argv)
    try:
        depths = [depth_arg(d) for d in args.depths.split(",")]
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if not 1 <= len(depths) <= 32 or not 0 < args.timeout <= 3600 or args.max_tokens <= 0:
        parser.error("use 1..32 depths, positive output allowance and timeout in (0, 3600]")
    record = dict(schema_version=1, run_id="perf-" + secrets.token_hex(8), timestamp_utc=utc_now(),
                  purpose="variant-selection measurement; not a qualification receipt", status="error")
    try:
        profile = load(args.profile)
        record.update(profile_id=profile.id, identity_fingerprint=profile.fingerprint)
        layout = Layout(args.root.resolve(), profile)
        if args.max_tokens + 8 >= profile.data["strata"]["setup_args"]["context"]:
            raise ProtocolError("output allowance exceeds context window")
        record.update(run(layout, depths, args.warm_depth, args.max_tokens, args.timeout), status="complete")
        rc = 0
    except TimeoutError:
        record["error"] = "request deadline exceeded"
        rc = 124
    except (ProtocolError, ValueError, OSError, lifecycle.LifecycleError):
        # Deliberately do not print arbitrary exception text: endpoint bodies and paths may be private.
        record["error"] = "protocol, profile, key or server-state failure"
        rc = 1
    atomic_write_json(args.root.resolve() / "evidence" / record["run_id"] / "result.json", record)
    print(json.dumps(record, allow_nan=False))
    print("scenario       input   TTFT ms   prefill tok/s   decode tok/s   MTP acceptance", file=sys.stderr)
    for row in record.get("samples", []):
        fields = [value(row, name) for name in ("prompt_tokens", "ttft_ms", "prefill_tokens_s", "decode_tokens_s", "mtp_acceptance")]
        print(row["scenario"] + "  " + "  ".join("unavailable" if v is None else f"{v:.2f}" for v in fields), file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
