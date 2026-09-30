#!/usr/bin/env python3
"""Shortest real stock-OMP -> stock-Strata typed-tool tracer (milestone M1; gate G11 evidence when run 3x).

Per run, in a fresh disposable git fixture under <root>/work/:
  turn 1  OMP reads calc.py/test_calc.py/NONCE.txt, fixes calc.py with an edit tool, runs the tests with its shell
          tool and reports the result and the nonce;
  between NONCE.txt is rotated on disk, so turn 2 can only answer from the transcript;
  turn 2  a new OMP process continues the same session (`--continue`) and must return the original nonce without
          calling tools.
An immutable verifier (pristine tests copied from outside the workspace) decides the code fix; the transcript
decides protocol validity (typed tool ids, argument JSON, result association, stop reasons, provider route).
Raw material stays under <root>/evidence/<run_id>/; stdout carries only the derived, scrubbed summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from omp_strata import hostrun, lifecycle, transcript  # noqa: E402
from omp_strata.layout import Layout, default_root  # noqa: E402
from omp_strata.profile import load  # noqa: E402

CALC = '''"""Tiny arithmetic helpers used by the tracer fixture."""


def add(a, b):
    """Return the sum of a and b."""
    return a - b


def mul(a, b):
    """Return the product of a and b."""
    return a * b
'''

TESTS = '''import unittest

from calc import add, mul


class CalcTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-4, 4), 0)

    def test_mul(self):
        self.assertEqual(mul(3, 4), 12)


if __name__ == "__main__":
    unittest.main()
'''

TURN1 = ("This repository has a failing unit test. Use your tools: read calc.py, test_calc.py and NONCE.txt; fix "
         "the bug in calc.py with an edit (do not modify test_calc.py); run `python -m unittest -v` in the "
         "repository with your shell tool; then reply with exactly one line: "
         "`RESULT: <number of tests run> tests <passed|failed>; NONCE: <exact contents of NONCE.txt>`.")
TURN2 = ("Do not call any tools. Answer only from this conversation: what exact string did NONCE.txt contain when "
         "you read it, and how many tests ran? Reply with exactly one line: `NONCE: <value>; TESTS: <n>`.")
ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{6,128}$")


def verify_fix(workspace: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        shutil.copyfile(workspace / "calc.py", t / "calc.py")
        (t / "test_calc.py").write_text(TESTS, encoding="utf-8", newline="\n")
        p = subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=t, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=120)
    return {"passed": p.returncode == 0, "exit_code": p.returncode,
            "tests_ran": int(m.group(1)) if (m := re.search(r"Ran (\d+) test", p.stderr)) else None}


def session_for(layout: Layout, workspace: Path) -> Path | None:
    for path in sorted(transcript.find_sessions(layout.omp_home), key=lambda p: p.stat().st_mtime, reverse=True):
        entries = transcript.load(path)
        header = next((e for e in entries if e.get("type") == "session"), {})
        if Path(str(header.get("cwd", ""))).resolve() == workspace.resolve():
            return path
    return None


def one_run(layout: Layout, key: str, index: int, max_time_s: int, thinking: str | None) -> dict:
    run_id = hostrun.new_run_id(f"tracer{index}")
    ev = hostrun.evidence_dir(layout, run_id)
    ws = layout.work / run_id
    nonce = "TRACER-" + secrets.token_hex(6).upper()
    hostrun.git_fixture(ws, {"calc.py": CALC, "test_calc.py": TESTS, "NONCE.txt": nonce + "\n"})
    tests_sha = hashlib.sha256((ws / "test_calc.py").read_bytes()).hexdigest()
    before = hostrun.strata_metrics(layout, key).get("totals", {})

    t1 = hostrun.run_omp(layout, TURN1, cwd=ws, out_dir=ev, name="turn1", max_time_s=max_time_s,
                         thinking=thinking, key=key)
    fix = verify_fix(ws)
    rotated = "ROTATED-" + secrets.token_hex(6).upper()
    (ws / "NONCE.txt").write_text(rotated + "\n", encoding="utf-8")
    t2 = hostrun.run_omp(layout, TURN2, cwd=ws, out_dir=ev, name="turn2", max_time_s=max_time_s,
                         continue_session=True, thinking=thinking, key=key)
    after = hostrun.strata_metrics(layout, key).get("totals", {})

    session = session_for(layout, ws)
    summary = transcript.summarize(session) if session else {}
    cycles = transcript.tool_cycles(transcript.load(session)) if session else []
    # tool calls issued after the second user prompt belong to turn 2
    entries = transcript.load(session) if session else []
    user_idx = [i for i, e in enumerate(entries) if e.get("type") == "message"
                and (e.get("message") or {}).get("role") == "user"]
    turn2_calls = 0
    if len(user_idx) >= 2:
        for e in entries[user_idx[1]:]:
            msg = e.get("message") or {}
            if msg.get("role") == "assistant":
                turn2_calls += sum(1 for c in msg.get("content", []) if c.get("type") == "toolCall")
    names = [c["name"] for c in cycles]
    edited = any(c["name"] in ("edit", "write", "multiedit", "patch") and not c["is_error"] for c in cycles)
    shelled = any(c["name"] in ("bash", "shell", "exec") and not c["is_error"] for c in cycles)
    t2_text = t2.final_text() or last_assistant_text(entries)
    protocol = {
        "turn1_exit": t1.exit_code, "turn2_exit": t2.exit_code,
        "timed_out": t1.timed_out or t2.timed_out,
        "session_found": session is not None,
        "tool_calls": len(cycles), "tool_names": names,
        "ids_well_formed_unique": bool(cycles) and all(ID_RE.match(c["id"] or "") for c in cycles)
        and len({c["id"] for c in cycles}) == len(cycles),
        "all_calls_have_results": all(c["result_found"] for c in cycles),
        "arguments_are_objects": all(isinstance(c["arguments"], dict) for c in cycles),
        "edit_tool_succeeded": edited, "shell_tool_succeeded": shelled,
        "turn2_tool_calls": turn2_calls,
        "providers": summary.get("providers"), "apis": summary.get("apis"), "models": summary.get("models"),
        "stop_reasons": summary.get("stopReasons"),
    }
    task = {
        "verifier": fix,
        "tests_file_unchanged": hashlib.sha256((ws / "test_calc.py").read_bytes()).hexdigest() == tests_sha,
        "turn2_has_original_nonce": nonce in t2_text,
        "turn2_has_rotated_nonce": rotated in t2_text,
    }
    usage = summary.get("usage", {})
    cache = {
        "omp_cache_read_tokens": usage.get("cacheRead"),
        "omp_input_tokens": usage.get("input"),
        "strata_requests_delta": _delta(before, after, "requests"),
        "strata_prompt_tokens_delta": _delta(before, after, "prompt_tokens"),
        "strata_reused_tokens_delta": _delta(before, after, "reused"),
    }
    protocol_ok = (t1.exit_code == 0 and t2.exit_code == 0 and not protocol["timed_out"]
                   and protocol["session_found"] and protocol["ids_well_formed_unique"]
                   and protocol["all_calls_have_results"] and protocol["arguments_are_objects"]
                   and protocol["edit_tool_succeeded"] and protocol["shell_tool_succeeded"]
                   and protocol["turn2_tool_calls"] == 0
                   and set(protocol["providers"] or []) == {"strata-local"}
                   and set(protocol["apis"] or []) == {"openai-completions"})
    task_ok = fix["passed"] and task["tests_file_unchanged"] and task["turn2_has_original_nonce"] \
        and not task["turn2_has_rotated_nonce"]
    result = {"run_id": run_id, "protocol_pass": protocol_ok, "task_pass": task_ok, "protocol": protocol,
              "task": task, "cache": cache,
              "timing_ms": {"turn1_wall": t1.wall_ms, "turn2_wall": t2.wall_ms}}
    hostrun.write_raw(ev, "summary.json", result)
    if session:
        shutil.copyfile(session, ev / "session.jsonl")
    return result


def _delta(before: dict, after: dict, key: str):
    if key in before and key in after:
        return after[key] - before[key]
    return None


def last_assistant_text(entries: list[dict]) -> str:
    for e in reversed(entries):
        msg = e.get("message") or {}
        if e.get("type") == "message" and msg.get("role") == "assistant":
            text = "".join(c.get("text", "") for c in msg.get("content", []) if c.get("type") == "text")
            if text:
                return text
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--root")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--max-time", type=int, default=900, help="per OMP invocation, seconds")
    ap.add_argument("--thinking", choices=["off", "low", "medium", "high"], help="default: model default")
    a = ap.parse_args()
    layout = Layout(root=Path(a.root).resolve() if a.root else default_root().resolve(), profile=load(Path(a.profile)))
    key = lifecycle.ensure_healthy(layout)
    results = [one_run(layout, key, i + 1, a.max_time, a.thinking) for i in range(a.runs)]
    print(json.dumps({"runs": results, "all_protocol_pass": all(r["protocol_pass"] for r in results),
                      "all_task_pass": all(r["task_pass"] for r in results)}, indent=2))
    return 0 if all(r["protocol_pass"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
