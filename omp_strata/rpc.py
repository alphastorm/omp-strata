"""One long-lived stock OMP process in RPC mode (newline-delimited JSON on stdin/stdout).

Used where a gate needs the *client* to survive something else (an engine restart) inside one OMP process.
Protocol shape follows the pinned OMP 18.4.0 RPC mode as exercised by alphastorm/omp-ninfer
`scripts/stock_omp_session_proof.py` (adapted, not copied): wait for `ready`, send
`{"id", "type": "prompt", "message"}`, read the matching `response`, then wait for `agent_end`.
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from pathlib import Path

from .layout import Layout


class RpcOmp:
    def __init__(self, layout: Layout, *, cwd: Path, stderr_path: Path, key: str, continue_session: bool = False,
                 thinking: str | None = None, ready_timeout: float = 120):
        from . import ompcfg

        ompcfg.install_profile_config(layout)
        env = ompcfg.isolated_env(layout, api_key=key)
        extra = ["--mode", "rpc", "--auto-approve"]
        if continue_session:
            extra.append("--continue")
        if thinking:
            extra += ["--thinking", thinking]
        argv = ompcfg.omp_argv(layout, extra=extra)
        self._stderr = open(stderr_path, "wb")
        self.proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self._stderr, text=True, encoding="utf-8", bufsize=1)
        self.events: queue.Queue = queue.Queue()
        self.log: list[str] = []
        threading.Thread(target=self._pump, daemon=True).start()
        self._next = 0
        self.wait_for(lambda e: e.get("type") == "ready", ready_timeout)

    def _pump(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self.events.put(json.loads(line))
            except ValueError:
                self.events.put({"type": "_unparsed"})
        self.events.put({"type": "_eof"})

    def wait_for(self, predicate, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                event = self.events.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                break
            kind = event.get("type")
            self.log.append(str(kind))
            if kind == "_eof":
                raise RuntimeError(f"omp exited (rc={self.proc.poll()}); last events {self.log[-6:]}")
            if predicate(event):
                return event
        raise TimeoutError(f"no matching RPC event within {timeout}s; last events {self.log[-8:]}")

    def command(self, kind: str, timeout: float = 120, **fields) -> dict:
        self._next += 1
        rid = str(self._next)
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps({"id": rid, "type": kind, **fields}) + "\n")
        self.proc.stdin.flush()
        resp = self.wait_for(lambda e: e.get("type") == "response" and e.get("id") == rid, timeout)
        if resp.get("success") is False:
            raise RuntimeError(f"{kind} refused: {json.dumps(resp)[:300]}")
        return resp

    def send_prompt(self, text: str) -> float:
        """Submit a prompt and return once OMP acknowledges it (the run continues; see `wait_end`)."""
        t0 = time.monotonic()
        self.command("prompt", message=text)
        return t0

    def wait_end(self, t0: float, timeout: float = 900) -> dict:
        end = self.wait_for(lambda e: e.get("type") == "agent_end", timeout)
        answer, stop, usage = "", None, None
        for message in reversed(end.get("messages") or []):
            if message.get("role") == "assistant":
                answer = "".join(p.get("text", "") for p in message.get("content") or []
                                 if isinstance(p, dict) and p.get("type") == "text").strip()
                stop = message.get("errorMessage") or message.get("stopReason")
                usage = message.get("usage")
                break
        return {"answer": answer, "stop": stop, "usage": usage, "wall_ms": round((time.monotonic() - t0) * 1000, 1)}

    def prompt(self, text: str, timeout: float = 900) -> dict:
        return self.wait_end(self.send_prompt(text), timeout)

    def state(self) -> dict:
        data = self.command("get_state").get("data") or {}
        return {"session_id": data.get("sessionId"), "session_file": data.get("sessionFile"),
                "message_count": data.get("messageCount")}

    def branch_points(self) -> list[dict]:
        """User messages that can start a branch: [{entryId, text}]."""
        return (self.command("get_branch_messages").get("data") or {}).get("messages") or []

    def branch(self, entry_id: str) -> dict:
        """Branch the session before the given user message (stock OMP keeps the original history)."""
        return self.command("branch", entryId=entry_id).get("data") or {}

    def close(self) -> int:
        if self.proc.stdin is not None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        try:
            rc = self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            rc = self.proc.wait()
        self._stderr.close()
        return rc
