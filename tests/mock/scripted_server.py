"""Test-only Strata-shaped HTTP/SSE server and bounded real-OMP harness.

No production import uses this module. All requests and synthetic credentials
stay in the test process or its disposable integration root.
"""
from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from omp_strata.layout import Layout
from omp_strata.ompcfg import install_profile_config, isolated_env, omp_argv
from omp_strata.profile import load as load_profile
from omp_strata.transcript import find_sessions, load, summarize, tool_cycles
from tests.candidate import PROFILE as PROFILE_PATH


@dataclass
class ToolCall:
    name: str
    arguments: dict | str
    id: str = field(default_factory=lambda: "call_" + secrets.token_hex(12))
    fragment_size: int = 7
    closing_fragment: str = ""


@dataclass
class ResponseSpec:
    text: str = "Fixture complete."
    reasoning: str = "Checking the fixture."
    calls: list[ToolCall] = field(default_factory=list)
    status: int = 200
    fault: str | None = None  # drop, malformed, in_band, stall
    finish_reason: str | None = None
    split_utf8: bool = False
    prompt_tokens: int = 120
    completion_tokens: int = 45
    cached_tokens: int = 80
    headers: dict[str, str] = field(default_factory=dict)


class ScriptedServer:
    def __init__(self, scenario: list[ResponseSpec], *, model: str):
        self.scenario = list(scenario)
        self.model = model
        self.requests: list[dict] = []
        self.condition = threading.Condition()
        self.closed = threading.Event()
        self.split_writes = 0
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def _record(self, body):
                with owner.condition:
                    owner.requests.append({"method": self.command, "path": self.path,
                                           "headers": dict(self.headers), "body": body,
                                           "arrival_time": time.monotonic()})
                    owner.condition.notify_all()

            def _json(self, status, value, headers=None):
                data = json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._record(None)
                if self.path == "/v1/models":
                    self._json(200, {"object": "list", "data": [{"id": owner.model, "object": "model"}]})
                else:
                    self._json(404, {"error": {"message": "unknown fixture route"}})

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                try:
                    body = json.loads(raw)
                except ValueError:
                    self._record(None)
                    self._json(400, {"error": {"message": "invalid JSON"}})
                    return
                self._record(body)
                if self.path != "/v1/chat/completions":
                    self._json(404, {"error": {"message": "unknown fixture route"}})
                    return
                with owner.condition:
                    spec = owner.scenario.pop(0) if owner.scenario else ResponseSpec(status=500)
                if spec.status != 200:
                    self._json(spec.status, {"error": {"type": "server_error" if spec.status >= 500 else "invalid_request_error",
                                                     "message": f"scripted HTTP {spec.status}"}}, spec.headers)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                response_id = "chatcmpl-" + secrets.token_hex(12)

                def write(data, split=False):
                    if split:
                        index = next((i for i, byte in enumerate(data) if byte >= 0xC0), None)
                        if index is not None:
                            self.wfile.write(data[:index + 1])
                            self.wfile.flush()
                            time.sleep(0.015)
                            self.wfile.write(data[index + 1:])
                            self.wfile.flush()
                            owner.split_writes += 1
                            return
                    self.wfile.write(data)
                    self.wfile.flush()

                def chunk(delta, finish=None, usage=False, split=False):
                    value = {"id": response_id, "object": "chat.completion.chunk", "created": 1775000000,
                             "model": owner.model,
                             "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
                    if usage:
                        value["usage"] = {"prompt_tokens": spec.prompt_tokens,
                                          "completion_tokens": spec.completion_tokens,
                                          "total_tokens": spec.prompt_tokens + spec.completion_tokens,
                                          "prompt_tokens_details": {"cached_tokens": spec.cached_tokens}}
                        value["timings"] = {"cache_n": spec.cached_tokens, "prompt_n": spec.prompt_tokens - spec.cached_tokens,
                                            "predicted_n": spec.completion_tokens, "prompt_ms": 10, "predicted_ms": 20}
                    write(("data: " + json.dumps(value, ensure_ascii=False) + "\n\n").encode(), split)

                try:
                    write(b": keep-alive\n\n")
                    chunk({"role": "assistant", "content": ""})
                    if spec.fault == "stall":
                        owner.closed.wait(45)
                        return
                    if spec.reasoning:
                        chunk({"reasoning_content": spec.reasoning})
                    if spec.text:
                        chunk({"content": spec.text}, split=spec.split_utf8)
                    for index, call in enumerate(spec.calls):
                        chunk({"tool_calls": [{"index": index, "id": call.id, "type": "function",
                                               "function": {"name": call.name, "arguments": ""}}]})
                        arguments = call.arguments if isinstance(call.arguments, str) else json.dumps(call.arguments)
                        for offset in range(0, len(arguments), call.fragment_size):
                            chunk({"tool_calls": [{"index": index, "function": {
                                "arguments": arguments[offset:offset + call.fragment_size]}}]})
                        if call.closing_fragment:
                            chunk({"tool_calls": [{"index": index, "function": {"arguments": call.closing_fragment}}]})
                    if spec.fault == "drop":
                        self.connection.shutdown(socket.SHUT_RDWR)
                        return
                    if spec.fault == "malformed":
                        write(b"data: {definitely-not-json}\n\n")
                        write(b"data: [DONE]\n\n")
                        return
                    if spec.fault == "in_band":
                        write(b'data: {"error":{"type":"server_error","message":"scripted engine failure"}}\n\n')
                        write(b"data: [DONE]\n\n")
                        return
                    chunk({}, spec.finish_reason or ("tool_calls" if spec.calls else "stop"), usage=True)
                    write(b"data: [DONE]\n\n")
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass  # Cancellation deliberately closes a live response.

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}/v1"

    @property
    def posts(self):
        with self.condition:
            return [r for r in self.requests if r["method"] == "POST"]

    def wait_for_requests(self, count=1, timeout=15):
        with self.condition:
            return self.condition.wait_for(lambda: len(self.requests) >= count, timeout)

    def close(self):
        self.closed.set()
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def wire_fields(request):
    body = request["body"]
    return {"max_tokens": body.get("max_tokens"), "reasoning_effort": body.get("reasoning_effort"),
            "stream_options": body.get("stream_options"),
            "tools": [tool["function"]["name"] for tool in body.get("tools", [])],
            "tool_choice": body.get("tool_choice"), "tool_choice_present": "tool_choice" in body,
            "parallel_tool_calls_present": "parallel_tool_calls" in body}


class OmpTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_OMP_BINARY")
        if not value or not Path(value).is_file():
            raise unittest.SkipTest("set OMP_STRATA_OMP_BINARY to the fetched stock OMP binary")
        cls.binary = Path(value).resolve()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="omp-strata-test-")
        self.addCleanup(self.temporary.cleanup)
        self.layout = Layout(Path(self.temporary.name) / "integration", load_profile(PROFILE_PATH))
        self.repo = Path(self.temporary.name) / "fixture"
        self.repo.mkdir()
        self.api_key = secrets.token_urlsafe(24)
        self.env = isolated_env(self.layout, api_key=self.api_key)
        subprocess.run(["git", "init", "--quiet", self.repo], env=self.env, stdin=subprocess.DEVNULL,
                       capture_output=True, check=True, timeout=10)
        self.processes = []
        self.addCleanup(self._stop_processes)

    def _stop_processes(self):
        for process in self.processes:
            if process.poll() is None:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            process.communicate(timeout=5)

    def server(self, scenario):
        server = ScriptedServer(scenario, model=self.layout.profile.data["strata"]["model_name"])
        self.addCleanup(server.close)
        install_profile_config(self.layout, base_url=server.base_url)
        return server

    def start_omp(self, *, extra=(), env=None, max_time="25s", prompt="Complete the fixture task."):
        argv = omp_argv(self.layout, binary=self.binary,
                        extra=["-p", "--mode", "json", "--max-time", max_time, "--auto-approve",
                               "--tools", "read,write,bash", *extra, prompt])
        process = subprocess.Popen(argv, cwd=self.repo, env=self.env if env is None else env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", start_new_session=os.name == "posix")
        self.processes.append(process)
        return process

    def finish_omp(self, process, *, timeout=35):
        stdout, stderr = process.communicate(timeout=timeout)
        events = []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                events.append(event)
        messages = [e["message"] for e in events if e.get("type") == "message_end"
                    and isinstance(e.get("message"), dict)]
        return {"returncode": process.returncode, "events": events, "messages": messages,
                "stderr": stderr, "stdout": stdout}

    def run_omp(self, **kwargs):
        return self.finish_omp(self.start_omp(**kwargs))

    def session(self):
        sessions = find_sessions(self.layout.omp_home)
        self.assertTrue(sessions, "stock OMP must persist a session")
        return max(sessions, key=lambda path: path.stat().st_mtime_ns)

    def assert_success(self, result, text=None):
        self.assertEqual(result["returncode"], 0, result["stderr"][-1800:])
        assistants = [m for m in result["messages"] if m.get("role") == "assistant"]
        self.assertTrue(assistants, result["stderr"][-1800:])
        self.assertEqual(assistants[-1]["stopReason"], "stop")
        if text is not None:
            self.assertEqual("".join(b.get("text", "") for b in assistants[-1]["content"]
                                     if b.get("type") == "text"), text)
        return summarize(self.session())

    def assert_failure(self, result):
        assistants = [m for m in result["messages"] if m.get("role") == "assistant"]
        self.assertFalse(any(m.get("stopReason") == "stop" for m in assistants), "fault became a completed turn")
        self.assertTrue(result["returncode"] != 0 or any(m.get("stopReason") in ("error", "aborted")
                                                       for m in assistants), result["stderr"][-1800:])
        sessions = find_sessions(self.layout.omp_home)
        for path in sessions:
            self.assertNotIn("stop", summarize(path)["stopReasons"])

    def assert_cut_call_not_run(self, path, result):
        """G04: a tool call whose arguments were cut off never runs. The client may fail the turn, or answer the call
        with an error result and let the model continue, as it does after a length cut (`finish_reason: length`)."""
        self.assertFalse(path.exists(), "the cut-off tool call ran")
        if result["returncode"] == 0:
            cycles = tool_cycles(load(self.session()))
            self.assertTrue(cycles and all(c["result_found"] and c["is_error"] for c in cycles),
                            "the cut-off call completed without an error result")
