#!/usr/bin/env python3
"""Comparison-only, client-observed speed probe; never changes an engine or gate.

Run once per exclusive engine window. Reuse the first JSON's prompt_set with
--prompt-set on the other arm for byte-identical inputs (including nonce).
Each depth/repetition has its own prefix. A new comparison must use a new set.
Depth is nominal: K = 1024 repetitions of perf_probe's single-word ' datum'
filler, plus a small nonce/instruction overhead; actual server usage is authoritative.
No tokenizer equivalence, process-cold state, or absence of shared template cache
is claimed. Output rate includes reasoning tokens and is client-observed, not
server decode throughput or individual-token latency. No raw output is retained.

Example: python scripts/probe_g25_speed.py --arm strata --endpoint http://127.0.0.1:18090
    --key-file <private-key-file> --model <served-id> --out <private-result.json> --summary
Exit 1 means at least one failed request; 2 means invalid configuration, including a
--model that the endpoint's authenticated GET /v1/models does not list (checked before any sample).
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import os
import secrets
import socket
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

MAX_EVENT = 1024 * 1024
MAX_STREAM = 64 * 1024 * 1024
METRICS = ("ttft_ms", "first_visible_text_ms", "output_tokens_s", "wall_ms",
           "prompt_tokens", "completion_tokens")


class ProtocolError(RuntimeError):
    """Only locally authored, secret-free messages may enter the result."""


def metric(value, reason):
    return {"value": value, "reason": reason if value is None else None}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def prompt_for(prompt_set, depth, rep, max_output):
    nonce = hashlib.sha256(f"{prompt_set}:{depth}:{rep}".encode()).hexdigest()[:32]
    return (nonce + "\n" + " datum" * depth + "\nIgnore the filler above. "
            f"Write exactly {max(1, max_output // 2)} words explaining how to implement a thread-safe "
            "Python LRU cache with TTL and test it. Output only the explanation.")


def request_body(arm, model, prompt, max_output):
    body = {"model": model, "stream": True, "temperature": 0}
    if arm == "strata":
        body.update(messages=[{"role": "user", "content": prompt}], max_tokens=max_output,
                    stream_options={"include_usage": True}, reasoning_effort="none")
    else:
        # omp-ninfer examples/windows-native/models.fragment.yml selects Responses.
        # Its scripts/concurrency_probe.py uses input, max_output_tokens and store;
        # no durable session, continuation, or encrypted reasoning is needed here.
        body.update(input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                    max_output_tokens=max_output, store=False, reasoning={"effort": "low"})
    return body


def sse_events(response, clock=time.monotonic):
    """Bound both aggregate event and stream bytes, including comments/unknown fields."""
    data, name, size, total = [], "", 0, 0
    while True:
        raw = response.readline(MAX_EVENT + 1)
        if not raw:
            raise ProtocolError("SSE ended without a terminal event")
        size += len(raw)
        total += len(raw)
        if size > MAX_EVENT or total > MAX_STREAM:
            raise ProtocolError("SSE size limit exceeded")
        try:
            line = raw.decode("utf-8").rstrip("\r\n")
        except UnicodeError:
            raise ProtocolError("invalid SSE encoding") from None
        if not line:
            if data:
                payload = "\n".join(data)
                if payload == "[DONE]":
                    yield "[DONE]", {}, clock()
                else:
                    try:
                        event = json.loads(payload)
                    except (ValueError, RecursionError):
                        raise ProtocolError("invalid SSE JSON") from None
                    if not isinstance(event, dict):
                        raise ProtocolError("invalid SSE object")
                    kind = name or event.get("type", "")
                    if not isinstance(kind, str):
                        raise ProtocolError("invalid SSE event type")
                    yield kind, event, clock()
            data, name, size = [], "", 0
        elif not line.startswith(":"):
            field, _, value = line.partition(":")
            if field == "data":
                data.append(value.removeprefix(" "))
            elif field == "event":
                name = value.removeprefix(" ")


class Measurement:
    def __init__(self, arm, started):
        self.arm, self.started = arm, started
        self.first = self.last = self.visible = None
        self.events = 0
        self.usage = None
        self.timings = {}
        self.finish = None

    def output(self, text, reasoning, now):
        if any(value is not None and not isinstance(value, str) for value in (text, reasoning)):
            raise ProtocolError("invalid text delta")
        if text or reasoning:
            self.first = now if self.first is None else self.first
            self.last = now
            self.events += 1
        if text and self.visible is None:
            self.visible = now

    def tokens(self, usage):
        if usage is None:
            return
        names = ("prompt_tokens", "completion_tokens") if self.arm == "strata" else ("input_tokens", "output_tokens")
        if not isinstance(usage, dict):
            raise ProtocolError("invalid usage")
        if any(usage.get(k) is not None and (type(usage[k]) is not int or usage[k] < 0) for k in names):
            raise ProtocolError("invalid token count")
        self.usage = dict(zip(("prompt_tokens", "completion_tokens"), (usage.get(k) for k in names)))

    def consume(self, response, clock=time.monotonic):
        for kind, event, now in sse_events(response, clock):
            if event.get("error") is not None or kind == "error":
                raise ProtocolError("server reported an SSE error")
            if self.arm == "strata":
                if kind == "[DONE]":
                    if self.finish not in ("stop", "length"):
                        raise ProtocolError("missing or unsuccessful chat finish reason")
                    return
                choices = event.get("choices", [])
                if not isinstance(choices, list) or len(choices) > 1:
                    raise ProtocolError("invalid chat choices")
                for choice in choices:
                    if not isinstance(choice, dict) or not isinstance(choice.get("delta", {}), dict):
                        raise ProtocolError("invalid chat delta")
                    delta = choice.get("delta", {})
                    if delta.get("tool_calls"):
                        raise ProtocolError("unexpected tool call")
                    self.output(delta.get("content"), delta.get("reasoning_content"), now)
                    if choice.get("finish_reason") is not None:
                        finish = choice["finish_reason"]
                        if finish not in ("stop", "length"):
                            raise ProtocolError("unsuccessful chat finish reason")
                        self.finish = finish
                self.tokens(event.get("usage"))
                if event.get("timings") is not None:
                    timing = event["timings"]
                    if not isinstance(timing, dict):
                        raise ProtocolError("invalid server timings")
                    for key in ("prompt_n", "prompt_ms", "predicted_n", "predicted_ms"):
                        if timing.get(key) is not None:
                            if not number(timing[key]):
                                raise ProtocolError("invalid server timing")
                            self.timings[key] = timing[key]
            else:
                if kind in ("response.output_text.delta", "response.reasoning_text.delta",
                            "response.reasoning.delta", "response.reasoning_summary_text.delta"):
                    delta = event.get("delta")
                    self.output(delta if kind == "response.output_text.delta" else None,
                                delta if kind != "response.output_text.delta" else None, now)
                elif kind in ("response.completed", "response.incomplete", "response.failed", "response.cancelled"):
                    doc = event.get("response")
                    if not isinstance(doc, dict):
                        raise ProtocolError("invalid terminal response")
                    self.tokens(doc.get("usage"))
                    finish = doc.get("status", kind.removeprefix("response."))
                    if finish not in ("completed", "incomplete", "failed", "cancelled"):
                        raise ProtocolError("invalid response status")
                    self.finish = finish
                    if doc.get("error") is not None:
                        raise ProtocolError("server reported a response error")
                    # A deliberate output cap is measurable, not a successful full answer.
                    capped = (kind == "response.incomplete" and self.finish == "incomplete"
                              and isinstance(doc.get("incomplete_details"), dict)
                              and doc["incomplete_details"].get("reason") == "max_output_tokens")
                    if not (kind == "response.completed" and self.finish == "completed") and not capped:
                        raise ProtocolError("unsuccessful terminal response")
                    return
                elif kind == "[DONE]":
                    raise ProtocolError("missing Responses terminal event")

    def result(self, ended, error=None):
        usage = self.usage or {}
        completion = usage.get("completion_tokens")
        reason = ("missing completion usage" if completion is None else
                  "fewer than two output events" if self.events < 2 else
                  "nonpositive output interval" if self.last <= self.first else None)
        rate = completion / (self.last - self.first) if reason is None else None
        values = {
            "ttft_ms": metric((self.first - self.started) * 1000 if self.first is not None else None, "no output delta"),
            "first_visible_text_ms": metric((self.visible - self.started) * 1000 if self.visible is not None else None, "no visible text delta"),
            "output_tokens_s": metric(rate, reason),
            "wall_ms": metric((ended - self.started) * 1000, None),
            **{k: metric(usage.get(k), "missing server usage") for k in ("prompt_tokens", "completion_tokens")},
        }
        row = {"status": "error" if error else "ok", "error": error, "finish_reason": self.finish,
               "output_events": self.events, "metrics": values}
        if self.arm == "strata":
            timings = {k: metric(self.timings.get(k), "server timing not reported")
                       for k in ("prompt_n", "prompt_ms", "predicted_n", "predicted_ms")}
            for label, count, duration in (("prefill_tokens_s", "prompt_n", "prompt_ms"),
                                           ("decode_tokens_s", "predicted_n", "predicted_ms")):
                n, ms = self.timings.get(count), self.timings.get(duration)
                timings[label] = metric(n * 1000 / ms if n is not None and ms else None,
                                        "missing count or positive server duration")
            row["server_timings"] = timings
        return row


class Client:
    def __init__(self, arm, endpoint, key, model, timeout):
        url = urlsplit(endpoint)
        if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1") or not url.port
                or url.path not in ("", "/") or url.username or url.password or url.query or url.fragment):
            raise ProtocolError("endpoint must be a loopback HTTP origin with explicit port")
        self.arm, self.host, self.port = arm, url.hostname, url.port
        self.key, self.model, self.timeout = key, model, timeout

    def served_models(self):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=min(self.timeout, 30))
        try:
            connection.request("GET", "/v1/models", headers={"Authorization": "Bearer " + self.key})
            response = connection.getresponse()
            if response.status != 200:
                raise ProtocolError(f"GET /v1/models returned HTTP {response.status}")
            rows = json.loads(response.read(MAX_EVENT)).get("data")
            ids = [row.get("id") for row in rows] if isinstance(rows, list) else []
            if not ids or not all(isinstance(i, str) and i for i in ids):
                raise ProtocolError("GET /v1/models listed no model ids")
            return ids
        except (OSError, http.client.HTTPException, ValueError, AttributeError):
            raise ProtocolError("GET /v1/models failed") from None
        finally:
            connection.close()

    def request(self, prompt, max_output):
        # HTTPConnection ignores ambient proxies and never follows redirects.
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        body = json.dumps(request_body(self.arm, self.model, prompt, max_output)).encode()
        path = "/v1/chat/completions" if self.arm == "strata" else "/v1/responses"
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

        measurement = Measurement(self.arm, time.monotonic())
        timer = threading.Timer(self.timeout, abort)
        timer.daemon = True
        timer.start()
        status, error = None, None
        try:
            connection.request("POST", path, body, {"Authorization": "Bearer " + self.key,
                               "Content-Type": "application/json", "Accept": "text/event-stream"})
            active_socket = connection.sock
            response = connection.getresponse()
            status = response.status
            if status != 200:
                raise ProtocolError(f"HTTP {status}" + ("; redirects are not followed" if 300 <= status < 400 else ""))
            if response.getheader("Content-Type", "").split(";")[0].strip().lower() != "text/event-stream":
                raise ProtocolError("expected text/event-stream")
            measurement.consume(response)
        except ProtocolError as exc:
            error = str(exc)
        except (OSError, http.client.HTTPException, ValueError):
            error = "request timeout" if expired.is_set() else "HTTP transport failure"
        finally:
            timer.cancel()
            connection.close()
        if expired.is_set():
            error = "request deadline exceeded"
        row = measurement.result(time.monotonic(), error)
        row["http_status"] = status
        return row


def summarize(rows):
    good = [row for row in rows if row["status"] == "ok"]
    summary = {"status": "ok" if len(good) == len(rows) else "error", "requests": len(rows),
               "succeeded": len(good), "failed": len(rows) - len(good), "metrics": {}}
    for name in METRICS:
        values = [r["metrics"][name]["value"] for r in good if r["metrics"][name]["value"] is not None]
        summary["metrics"][name] = {**metric(statistics.median(values) if values else None,
                                            "no successful samples with this metric"), "samples": len(values)}
    return summary


def depth_arg(value):
    try:
        n = int(value[:-1]) * 1024 if value.lower().endswith("k") else int(value)
        if not 0 <= n <= 1048576:
            raise ValueError
        return n
    except ValueError:
        raise argparse.ArgumentTypeError("depth must be 0..1048576, optionally suffixed K") from None


def write_private(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".speed-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", choices=("strata", "ninfer"), required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--key-file", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--depths", default="0,8K,32K,100K")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--max-output", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--prompt-set", help="reuse across paired arms; omit for a fresh comparison")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    try:
        depths = [depth_arg(d) for d in args.depths.split(",")]
        if not 1 <= len(depths) <= 32 or len(set(depths)) != len(depths):
            raise ProtocolError("use 1..32 distinct depths")
        if not 1 <= args.reps <= 100 or not 1 <= args.max_output <= 1048576 or not 0 < args.timeout <= 3600:
            raise ProtocolError("invalid repetitions, output cap or timeout")
        if args.out.resolve() == args.key_file.resolve():
            raise ProtocolError("output must not overwrite the key file")
        key = args.key_file.read_text(encoding="utf-8").strip()
        if not key or len(key) > 4096 or not key.isascii() or any(c.isspace() for c in key):
            raise ProtocolError("key file must contain a nonblank single ASCII token")
        client = Client(args.arm, args.endpoint, key, args.model, args.timeout)
    except (OSError, ValueError, argparse.ArgumentTypeError, ProtocolError):
        parser.exit(2, "invalid probe configuration or unreadable key file\n")
    try:
        served = client.served_models()
    except ProtocolError as exc:
        parser.exit(2, f"model check failed: {exc}\n")
    if args.model not in served:
        parser.exit(2, f"the endpoint does not serve model {args.model[:80]!r}; it serves "
                    + ", ".join(repr(i[:80]) for i in served[:4]) + "\n")
    prompt_set = args.prompt_set or secrets.token_hex(16)
    record = {"schema_version": 1, "purpose": "comparison only; not a qualification receipt",
              "engine_only_comparison": False, "arm": args.arm, "endpoint": args.endpoint,
              "model": args.model, "prompt_set": prompt_set, "depths": depths,
              "depth_unit": "nominal filler words; K=1024; actual usage includes template and instruction",
              "reps": args.reps, "max_output": args.max_output, "timeout": args.timeout,
              "samples": [], "summaries": []}
    for depth in depths:
        rows = []
        for rep in range(args.reps):
            prompt = prompt_for(prompt_set, depth, rep, args.max_output)
            row = client.request(prompt, args.max_output)
            row.update(depth=depth, rep=rep, prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
            rows.append(row)
            record["samples"].append(row)
        record["summaries"].append({"depth": depth, **summarize(rows)})
    record["status"] = "ok" if all(r["status"] == "ok" for r in record["samples"]) else "error"
    try:
        write_private(args.out, record)
    except OSError:
        print("cannot write private result", file=sys.stderr)
        return 1
    if args.summary:
        print("depth  ok/total  TTFT ms  visible ms  output tok/s  wall ms")
        for summary in record["summaries"]:
            values = [summary["metrics"][k]["value"] for k in METRICS[:4]]
            print(f"{summary['depth']:6}  {summary['succeeded']}/{summary['requests']}  "
                  + "  ".join("n/a" if v is None else f"{v:.2f}" for v in values))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
