"""Cross-protocol timing and failure boundaries; no real-host qualification."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from scripts import probe_g25_speed as probe


def sse(event, name=None):
    return ((f"event: {name}\n" if name else "") + "data: " + json.dumps(event) + "\n\n").encode()


def chat(delta=None, finish=None, **extra):
    return {"choices": [{"delta": delta or {}, "finish_reason": finish}], **extra}


def fixture(arm, usage=True):
    if arm == "strata":
        return (b": keepalive\r\n\r\n" + sse(chat({"role": "assistant"}))
                + sse(chat({"reasoning_content": "reason"})) + sse(chat({"content": "answer"}))
                + sse(chat(finish="length", timings={"prompt_n": 80, "prompt_ms": 40,
                                                      "predicted_n": 12, "predicted_ms": 60}))
                + (sse({"choices": [], "usage": {"prompt_tokens": 80, "completion_tokens": 12}}) if usage else b"")
                + b"data: [DONE]\n\n")
    return (sse({"type": "response.created"})
            + sse({"delta": "reason"}, "response.reasoning_text.delta")
            + sse({"type": "response.output_text.delta", "delta": "answer"})
            + sse({"type": "response.completed", "response": {"status": "completed", **(
                {"usage": {"input_tokens": 80, "output_tokens": 12}} if usage else {})}}))


@contextlib.contextmanager
def peer(payload, status=200, delay=0, models=("fixture",)):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append({"path": self.path, "authorization": self.headers.get("Authorization")})
            body = json.dumps({"object": "list", "data": [{"id": m, "object": "model"} for m in models]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            requests.append({"path": self.path, "authorization": self.headers.get("Authorization"),
                             "body": json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
            self.send_response(status)
            self.send_header("Content-Type", "text/event-stream")
            if status == 302:
                self.send_header("Location", "http://127.0.0.1:1/forbidden")
            self.end_headers()
            try:
                if delay:
                    # Keep sending data: a socket-inactivity timeout alone would not work.
                    end = time.monotonic() + delay
                    while time.monotonic() < end:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        time.sleep(.01)
                self.wfile.write(payload)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class ProbeSpeedTests(unittest.TestCase):
    def consume(self, arm, payload, ticks):
        measurement = probe.Measurement(arm, 10)
        measurement.consume(io.BytesIO(payload), iter(ticks).__next__)
        return measurement.result(15)

    def test_both_protocols_ignore_empty_events_and_time_reasoning_first(self):
        for arm in ("strata", "ninfer"):
            with self.subTest(arm=arm):
                row = self.consume(arm, fixture(arm), [10.1, 11, 13, 14, 14.1, 14.2])
                self.assertEqual(row["metrics"]["ttft_ms"]["value"], 1000)
                self.assertEqual(row["metrics"]["first_visible_text_ms"]["value"], 3000)
                self.assertEqual(row["metrics"]["output_tokens_s"]["value"], 6)
                self.assertEqual(row["metrics"]["wall_ms"]["value"], 5000)
                self.assertEqual(row["metrics"]["prompt_tokens"]["value"], 80)
                self.assertEqual(row["metrics"]["completion_tokens"]["value"], 12)
                self.assertEqual(row["output_events"], 2)
                if arm == "strata":
                    self.assertEqual(row["server_timings"]["decode_tokens_s"]["value"], 200)
                    self.assertEqual(row["server_timings"]["prefill_tokens_s"]["value"], 2000)

    def test_missing_usage_and_single_or_simultaneous_events_are_not_rates(self):
        for arm in ("strata", "ninfer"):
            with self.subTest(arm=arm):
                row = self.consume(arm, fixture(arm, usage=False), [10.1, 11, 13, 14, 14.1])
                self.assertEqual(row["status"], "ok")
                self.assertEqual(row["metrics"]["output_tokens_s"],
                                 {"value": None, "reason": "missing completion usage"})
                self.assertIsNone(row["metrics"]["prompt_tokens"]["value"])
        m = probe.Measurement("ninfer", 10)
        m.tokens({"input_tokens": 2, "output_tokens": 10})
        m.output(None, "reason", 11)
        self.assertEqual(m.result(12)["metrics"]["output_tokens_s"]["reason"], "fewer than two output events")
        self.assertEqual(m.result(12)["metrics"]["first_visible_text_ms"]["reason"], "no visible text delta")
        m.output("visible", None, 11)
        self.assertEqual(m.result(12)["metrics"]["output_tokens_s"]["reason"], "nonpositive output interval")

    def test_responses_terminal_output_cap_is_measurable_but_other_incomplete_fails(self):
        for reason in ("max_output_tokens", "content_filter"):
            payload = (sse({"type": "response.output_text.delta", "delta": "text"}) + sse({
                "type": "response.incomplete", "response": {"status": "incomplete",
                "incomplete_details": {"reason": reason}, "usage": {"input_tokens": 9, "output_tokens": 10}}}))
            if reason == "max_output_tokens":
                row = self.consume("ninfer", payload, [11, 12])
                self.assertEqual(row["finish_reason"], "incomplete")
                self.assertEqual(row["metrics"]["completion_tokens"]["value"], 10)
            else:
                with self.assertRaises(probe.ProtocolError):
                    self.consume("ninfer", payload, [11, 12])

    def test_protocol_failures_never_become_successful_samples(self):
        cases = [
            ("strata", b"data: not-json\n\n"),
            ("strata", sse({"error": {"message": "private response"}})),
            ("strata", sse(chat({"content": 12}))),
            ("strata", sse(chat(finish="tool_calls"))),
            ("strata", b"data: [DONE]\n\n"),
            ("ninfer", sse({"type": "response.failed", "response": {"status": "failed", "error": {"message": "private response"}}})),
            ("ninfer", sse({"type": "response.output_text.delta", "delta": "partial"})),
            ("ninfer", sse({"type": "response.completed", "response": {"usage": {"input_tokens": -1}}})),
        ]
        for arm, payload in cases:
            with self.subTest(arm=arm, payload=payload):
                with self.assertRaises(probe.ProtocolError) as caught:
                    self.consume(arm, payload, [11, 12])
                self.assertNotIn("private response", str(caught.exception))

    def test_multiline_crlf_and_bounded_aggregate_events(self):
        raw = b': comment\r\nevent: response.output_text.delta\r\ndata: {"delta":\r\ndata: "hello"}\r\n\r\n'
        event = next(probe.sse_events(io.BytesIO(raw), lambda: 3))
        self.assertEqual(event, ("response.output_text.delta", {"delta": "hello"}, 3))
        with patch.object(probe, "MAX_EVENT", 32):
            with self.assertRaisesRegex(probe.ProtocolError, "size limit"):
                list(probe.sse_events(io.BytesIO(b"data: x\n" * 8 + b"\n")))
        with patch.object(probe, "MAX_STREAM", 32):
            with self.assertRaisesRegex(probe.ProtocolError, "size limit"):
                list(probe.sse_events(io.BytesIO(b": ping\n\n" * 8)))

    def test_failed_samples_are_excluded_from_median_but_depth_stays_failed(self):
        good = self.consume("ninfer", fixture("ninfer"), [10.1, 11, 13, 14])
        failed = probe.Measurement("ninfer", 10).result(20, "transport failure")
        summary = probe.summarize([good, failed])
        self.assertEqual((summary["status"], summary["succeeded"], summary["failed"]), ("error", 1, 1))
        self.assertEqual(summary["metrics"]["wall_ms"]["value"], 5000)
        self.assertEqual(summary["metrics"]["wall_ms"]["samples"], 1)
        self.assertIsNone(probe.summarize([failed])["metrics"]["ttft_ms"]["value"])

    def test_paired_prompt_bytes_and_distinct_request_prefixes(self):
        prompts = [probe.prompt_for("shared-set", depth, rep, 512) for depth in (0, 8192) for rep in range(3)]
        self.assertEqual(len({p.split("\n")[0] for p in prompts}), 6)
        self.assertEqual(prompts[3], probe.prompt_for("shared-set", 8192, 0, 512))
        self.assertNotEqual(prompts[3].split("\n")[0], probe.prompt_for("fresh-set", 8192, 0, 512).split("\n")[0])
        a = probe.request_body("strata", "model-a", prompts[3], 512)
        b = probe.request_body("ninfer", "model-b", prompts[3], 512)
        self.assertEqual(a["messages"][0]["content"].encode(), b["input"][0]["content"][0]["text"].encode())

    def test_cli_key_file_auth_without_key_argv_or_output_and_ignores_proxies(self):
        key = "fixture-secret-never-on-command-line"
        for arm, route in (("strata", "/v1/chat/completions"), ("ninfer", "/v1/responses")):
            with self.subTest(arm=arm), tempfile.TemporaryDirectory() as tmp, peer(fixture(arm)) as (endpoint, requests):
                key_file, result_file = Path(tmp) / "key", Path(tmp) / "result.json"
                key_file.write_text(key)
                argv = ["--arm", arm, "--endpoint", endpoint, "--key-file", str(key_file), "--model", "fixture",
                        "--out", str(result_file), "--depths", "0", "--reps", "1", "--summary"]
                self.assertNotIn(key, " ".join(argv))
                out, err = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:1", "HTTP_PROXY": "http://127.0.0.1:1", "NO_PROXY": ""}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    self.assertEqual(probe.main(argv), 0)
                record = json.loads(result_file.read_text())
                self.assertEqual([r["path"] for r in requests], ["/v1/models", route])
                self.assertEqual({r["authorization"] for r in requests}, {"Bearer " + key})
                self.assertEqual(record["status"], "ok")
                self.assertNotIn(key, result_file.read_text() + out.getvalue() + err.getvalue())
                if os.name == "posix":
                    self.assertEqual(result_file.stat().st_mode & 0o777, 0o600)

    def test_cli_refuses_a_model_the_endpoint_does_not_serve_before_any_sample(self):
        with tempfile.TemporaryDirectory() as tmp, peer(fixture("ninfer"), models=("qwen3.8-27b",)) as (endpoint, requests):
            key_file, result_file = Path(tmp) / "key", Path(tmp) / "result.json"
            key_file.write_text("fixture-key")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
                probe.main(["--arm", "ninfer", "--endpoint", endpoint, "--key-file", str(key_file),
                            "--model", "q38-ninfer", "--out", str(result_file), "--depths", "0", "--reps", "1"])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("'qwen3.8-27b'", err.getvalue())
            self.assertEqual([r["path"] for r in requests], ["/v1/models"])
            self.assertFalse(result_file.exists())

    def test_redirects_errors_and_total_deadlines_are_not_hidden(self):
        for status, delay, expected in ((302, 0, "HTTP 302"), (503, 0, "HTTP 503"), (200, .4, "deadline")):
            with self.subTest(status=status), peer(fixture("ninfer"), status=status, delay=delay) as (endpoint, requests):
                client = probe.Client("ninfer", endpoint, "fixture", "model", .12)
                row = client.request("prompt", 12)
                self.assertEqual(row["status"], "error")
                self.assertIn(expected, row["error"])
                self.assertEqual(len(requests), 1)
                self.assertLess(row["metrics"]["wall_ms"]["value"], 1500)
        for endpoint in ("http://example.com:8000", "http://127.0.0.1:8000/v1", "http://user:secret@127.0.0.1:8000"):
            with self.assertRaises(probe.ProtocolError):
                probe.Client("strata", endpoint, "fixture", "model", 1)


if __name__ == "__main__":
    unittest.main()
