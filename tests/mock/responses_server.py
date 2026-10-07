"""Test-only loopback Responses SSE peer for the unmodified stock OMP client.

No NInfer runtime code or session-extension assumptions are used. The fixture
records the actual request; continuation may use previous_response_id or input
replay. Every generated id stays stable from added through done/completed.
"""
from __future__ import annotations

import json
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tests.mock.scripted_server import ResponseSpec


class ResponsesServer:
    def __init__(self, scenario: list[ResponseSpec], *, model: str, api_key: str,
                 identity: dict | None = None):
        self.scenario = list(scenario)
        self.model = model
        self.api_key = api_key
        self.identity = dict(identity or {})
        self.requests = []
        self.completed = {}
        self.protocol_errors = []
        self.split_writes = 0
        self.condition = threading.Condition()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def record(self, body):
                with owner.condition:
                    owner.requests.append({"method": self.command, "path": self.path,
                                           "headers": dict(self.headers), "body": body})
                    owner.condition.notify_all()

            def send_json(self, status, value):
                payload = json.dumps(value).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def authorized(self):
                if self.headers.get("Authorization") == "Bearer " + owner.api_key:
                    return True
                self.send_json(401, {"error": {"type": "authentication_error", "message": "unauthorized"}})
                return False

            def do_GET(self):
                self.record(None)
                if not self.authorized():
                    return
                if self.path == "/v1/models":
                    self.send_json(200, {"object": "list", "data": [{"id": owner.model, "object": "model"}]})
                elif self.path == "/v1/ninfer/status":
                    self.send_json(200, {"status": "ok", "identity": owner.identity})
                else:
                    self.send_json(404, {"error": {"message": "unknown fixture route"}})

            def do_POST(self):
                try:
                    body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                except (ValueError, UnicodeError):
                    self.send_json(400, {"error": {"message": "invalid JSON"}})
                    return
                self.record(body)
                if not self.authorized():
                    return
                error = owner.validate(self.path, body)
                if error:
                    owner.protocol_errors.append(error)
                    self.send_json(400, {"error": {"message": error}})
                    return
                with owner.condition:
                    spec = owner.scenario.pop(0) if owner.scenario else ResponseSpec(status=400)
                if spec.status != 200:
                    self.send_json(spec.status, {"error": {"type": "invalid_request_error",
                                                         "message": f"scripted HTTP {spec.status}"}})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                try:
                    self.stream(spec)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass  # Cancellation and truncation deliberately close the stream.

            def stream(self, spec):
                response_id = "resp_" + secrets.token_hex(12)
                response = {"id": response_id, "object": "response", "status": "in_progress",
                            "created_at": int(time.time()), "model": owner.model, "output": [],
                            "error": None, "incomplete_details": None, "usage": None}
                sequence = 0
                split = False

                def event(kind, **fields):
                    nonlocal sequence, split
                    data = {"type": kind, "sequence_number": sequence, **fields}
                    sequence += 1
                    raw = ("event: " + kind + "\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")
                    # Split a multibyte code point across separate socket writes, not
                    # merely across two valid Unicode JSON/SSE strings.
                    offset = next((i + 1 for i, byte in enumerate(raw) if byte >= 0xC0), None)
                    if spec.split_utf8 and not split and offset is not None:
                        self.wfile.write(raw[:offset])
                        self.wfile.flush()
                        time.sleep(0.01)
                        self.wfile.write(raw[offset:])
                        owner.split_writes += 1
                        split = True
                    else:
                        self.wfile.write(raw)
                    self.wfile.flush()

                event("response.created", response=dict(response))
                event("response.in_progress", response=dict(response))
                for index, call in enumerate(spec.calls):
                    item = {"id": "fc_" + secrets.token_hex(12), "type": "function_call",
                            "call_id": call.id, "name": call.name, "arguments": "", "status": "in_progress"}
                    event("response.output_item.added", output_index=index, item=dict(item))
                    args = (call.arguments if isinstance(call.arguments, str)
                            else json.dumps(call.arguments, ensure_ascii=False))
                    for offset in range(0, len(args), call.fragment_size):
                        event("response.function_call_arguments.delta", output_index=index, item_id=item["id"],
                              delta=args[offset:offset + call.fragment_size])
                    if spec.fault == "drop":
                        self.connection.shutdown(socket.SHUT_RDWR)
                        return
                    item.update(arguments=args, status="completed")
                    event("response.function_call_arguments.done", output_index=index, item_id=item["id"], arguments=args)
                    event("response.output_item.done", output_index=index, item=dict(item))
                    response["output"].append(item)
                if spec.text:
                    index = len(response["output"])
                    item = {"id": "msg_" + secrets.token_hex(12), "type": "message", "role": "assistant",
                            "status": "in_progress", "content": []}
                    part = {"type": "output_text", "text": "", "annotations": []}
                    event("response.output_item.added", output_index=index, item=dict(item))
                    event("response.content_part.added", output_index=index, item_id=item["id"], content_index=0, part=part)
                    for offset in range(0, len(spec.text), 7):
                        event("response.output_text.delta", output_index=index, item_id=item["id"], content_index=0,
                              delta=spec.text[offset:offset + 7])
                    if spec.fault == "drop":
                        self.connection.shutdown(socket.SHUT_RDWR)
                        return
                    part = {**part, "text": spec.text}
                    item.update(status="completed", content=[part])
                    event("response.output_text.done", output_index=index, item_id=item["id"], content_index=0, text=spec.text)
                    event("response.content_part.done", output_index=index, item_id=item["id"], content_index=0, part=part)
                    event("response.output_item.done", output_index=index, item=item)
                    response["output"].append(item)
                response.update(status="completed", usage={
                    "input_tokens": spec.prompt_tokens, "output_tokens": spec.completion_tokens,
                    "input_tokens_details": {"cached_tokens": spec.cached_tokens},
                    "output_tokens_details": {"reasoning_tokens": 0},
                    "total_tokens": spec.prompt_tokens + spec.completion_tokens,
                })
                with owner.condition:
                    owner.completed[response_id] = dict(response)
                event("response.completed", response=response)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    def validate(self, path, body):
        if path != "/v1/responses":
            return "only the Responses endpoint is allowed"
        if not isinstance(body, dict) or body.get("model") != self.model or body.get("stream") is not True:
            return "expected the selected model and streamed Responses"
        if not isinstance(body.get("input"), list) or not all(isinstance(item, dict) for item in body["input"]):
            return "Responses input must be typed items"
        for tool in body.get("tools", []):
            if (not isinstance(tool, dict) or tool.get("type") != "function"
                    or not isinstance(tool.get("name"), str) or not isinstance(tool.get("parameters"), dict)):
                return "expected native Responses function tool definitions"
        previous = body.get("previous_response_id")
        if previous is not None and previous not in self.completed:
            return "previous_response_id must name a completed response in this fresh fixture"
        for item in body["input"]:
            if item.get("type") == "function_call_output":
                if not isinstance(item.get("call_id"), str) or not isinstance(item.get("output"), (str, list)):
                    return "function_call_output must carry typed call id and result"
        return None

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}/v1"

    @property
    def posts(self):
        with self.condition:
            return [request for request in self.requests if request["method"] == "POST"]

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
