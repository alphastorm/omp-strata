"""Real-host helpers shared by the tracer, gate runner and evaluation: run stock OMP in the isolated profile
against the verified local Strata server, snapshot server counters, and keep raw evidence under the root.

Raw material (event streams, transcripts, server logs) never leaves `<root>/evidence/<run_id>/`; public receipts
carry only derived facts (counts, ids well-formed, verifier results, timings) chosen by the caller.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import lifecycle
from .common import atomic_write_json, utc_now
from .layout import Layout


@dataclass
class OmpRun:
    argv_summary: list[str]
    exit_code: int
    wall_ms: float
    events_path: Path
    stderr_path: Path
    timed_out: bool
    events: list[dict] = field(default_factory=list)

    def final_text(self) -> str:
        """Text of the last assistant message in the event stream (print-mode json)."""
        for ev in reversed(self.events):
            msg = ev.get("message") if isinstance(ev, dict) else None
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                parts = [c.get("text", "") for c in msg.get("content", []) if isinstance(c, dict)
                         and c.get("type") == "text"]
                if parts:
                    return "".join(parts)
        return ""


def new_run_id(prefix: str) -> str:
    return f"{prefix}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(3)}"


def evidence_dir(layout: Layout, run_id: str) -> Path:
    d = layout.root / "evidence" / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_omp(layout: Layout, prompt: str, *, cwd: Path, out_dir: Path, name: str, max_time_s: int = 900,
            continue_session: bool = False, thinking: str | None = None, extra: list[str] | None = None,
            key: str | None = None, base_url: str | None = None, overrides: dict | None = None) -> OmpRun:
    """One print-mode OMP invocation (stdin closed; json events captured to a file).

    The isolated profile config is rewritten for every run, so `base_url`/`overrides` apply to this run only."""
    from . import ompcfg                                   # lazy: only real/mock client paths need it

    key = key if key is not None else lifecycle.read_key(layout)
    ompcfg.install_profile_config(layout, base_url=base_url, overrides=overrides)
    env = ompcfg.isolated_env(layout, api_key=key)
    args = ["-p", "--mode", "json", "--auto-approve", "--max-time", f"{max_time_s}s"]
    if continue_session:
        args.append("--continue")
    if thinking:
        args += ["--thinking", thinking]
    args += list(extra or [])
    args.append(prompt)
    argv = ompcfg.omp_argv(layout, extra=args)
    events_path = out_dir / f"{name}.events.jsonl"
    stderr_path = out_dir / f"{name}.stderr.txt"
    t0 = time.monotonic()
    timed_out = False
    with open(events_path, "wb") as out, open(stderr_path, "wb") as err:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        try:
            rc = proc.wait(timeout=max_time_s + 120)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            rc = proc.wait()
    wall_ms = (time.monotonic() - t0) * 1000
    events = []
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    summary = [a for a in argv[1:] if a.startswith("-")]
    return OmpRun(argv_summary=summary, exit_code=rc, wall_ms=round(wall_ms, 1), events_path=events_path,
                  stderr_path=stderr_path, timed_out=timed_out, events=events)


def strata_metrics(layout: Layout, key: str) -> dict:
    """Server counters (authenticated /metrics); 'totals' carries requests, prompt tokens and reused tokens."""
    st, body = lifecycle.http_json(lifecycle.base_url(layout) + "/metrics", key=key, timeout=10)
    return body if st == 200 and isinstance(body, dict) else {}


def git_fixture(path: Path, files: dict[str, str]) -> Path:
    """A fresh disposable git repository with the given files committed (no hooks, no remotes)."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    for rel, text in files.items():
        f = path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8", newline="\n")
    env = dict(os.environ, GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@example.com",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@example.com")
    for cmd in (["git", "init", "-q"], ["git", "-c", "core.autocrlf=false", "add", "-A"],
                ["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "fixture"]):
        subprocess.run(cmd, cwd=path, env=env, check=True, stdin=subprocess.DEVNULL, capture_output=True)
    return path


def write_raw(out_dir: Path, name: str, value: object) -> Path:
    path = out_dir / name
    atomic_write_json(path, value)
    return path


__all__ = ["OmpRun", "evidence_dir", "git_fixture", "new_run_id", "run_omp", "strata_metrics", "utc_now",
           "write_raw"]
