#!/usr/bin/env python3
"""Run one stock tuple's real-host qualification sequence on the GPU host.

Launch detached with the host's process launcher and redirect this script's output to
one file. Its first line names summary.json; follow that atomically updated file for
progress and retain the adjacent stdout/stderr files as private evidence. Fetch the
candidate and acquire its GPU window first. This runner never restores another tenant.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TOOLING = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLING))
from omp_strata.ompcfg import drop_native_cache  # noqa: E402

STEPS = ("install", "keygen", "start", "g10", "tracer", "g12", "g13", "g14", "g14q", "g15", "g16",
         "g17", "g18", "g18l", "g19", "g20", "pilot", "eval", "quickstart", "g21", "stop")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def last_object(text: str) -> dict:
    """Read multiline JSON amid logs without mistaking a nested object for the result."""
    decoder, result, end = json.JSONDecoder(), {}, 0
    for match in re.finditer(r"\{", text):
        if match.start() < end:
            continue
        try:
            value, end = decoder.raw_decode(text, match.start())
        except ValueError:
            continue
        if isinstance(value, dict):
            result = value
    return result


def observed(result: dict) -> tuple:
    run_id, passed = result.get("run_id"), result.get("pass_observed")
    if "all_protocol_pass" in result:
        run_id = [run["run_id"] for run in result["runs"]]
        passed = result["all_protocol_pass"] and result["all_task_pass"]
    elif "completion_count" in result and "denominator" in result:
        passed = result["denominator"] > 0 and result["completion_count"] == result["denominator"]
    return run_id, passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--from", dest="first", choices=(*STEPS, "perf"), default=STEPS[0])
    parser.add_argument("--only", help="comma-separated steps, executed in canonical order")
    parser.add_argument("--keep-running", action="store_true", help="skip the final stop")
    parser.add_argument("--dry-run", action="store_true", help="print argv without creating files or processes")
    args = parser.parse_args()
    order = (*STEPS[:-1], "perf", "stop") if args.first == "perf" or "perf" in (args.only or "").split(",") else STEPS
    only = set(args.only.split(",")) if args.only is not None else set(order)
    if only - set(order):
        parser.error("unknown steps: " + ", ".join(sorted(only - set(order))))
    selected = [step for step in order[order.index(args.first):] if step in only and step != "stop"]
    root, profile = Path(args.root).resolve(), Path(args.profile).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = root / "evidence" / ("requalify-" + stamp)
    summary = evidence / "summary.json"
    workspace = root / "work" / ("quickstart-" + stamp)
    common = ["--profile", str(profile), "--root", str(root)]
    rows, tracer_ids = [], []
    print(summary, flush=True)

    def command(tool: str, *extra: str) -> list[str]:
        return [sys.executable, str(TOOLING / "scripts" / (tool + ".py")), *extra]

    restart = command("omp_strata", "restart", *common)
    # evaluate uses POSIX shlex.split even on Windows; quote backslashes accordingly.
    hook = shlex.join(restart)

    def argv_for(step: str) -> list[str]:
        if step == "perf":
            return command("perf_probe", *common)
        if step.startswith("g"):
            extra = ["--deep"] if step == "g10" else ["--runs", *tracer_ids] if step == "g12" else []
            return command("realhost_gates", step, *common, *extra)
        if step == "tracer":
            return command("tracer", *common, "--runs", "3")
        if step in ("pilot", "eval"):
            out = root / "eval" / (stamp + ("-pilot" if step == "pilot" else "-scored"))
            return command("evaluate", *common, "--attempts", "1" if step == "pilot" else "3",
                           "--out", str(out), "--between-phases", hook, *(["--pilot"] if step == "pilot" else []))
        if step == "quickstart":
            return command("omp_strata", "launch-omp", *common, "--", "-p", "--auto-approve",
                           "Run the tests and fix the failing one.")
        return command("omp_strata", step, *common)

    if args.dry_run:
        tracer_ids = ["<tracer-run-1>", "<tracer-run-2>", "<tracer-run-3>"]
        for step in selected + ([] if args.keep_running else ["stop"]):
            print(step + ": " + json.dumps(argv_for(step)))
        return 0
    evidence.mkdir(parents=True)

    def save() -> None:
        temporary = summary.with_suffix(".tmp")
        temporary.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        temporary.replace(summary)

    def fixture() -> None:
        from tracer import CALC, TESTS, hostrun
        hostrun.git_fixture(workspace, {"calc.py": CALC, "test_calc.py": TESTS})

    def run(step: str, argv: list[str], *, cwd: Path = TOOLING, prepare=None) -> tuple[dict, dict]:
        prefix = evidence / f"{len(rows) + 1:02d}-{step}"
        row = {"step": step, "argv": argv, "rc": None, "started_utc": utc_now(), "seconds": 0,
               "run_id": None, "pass_observed": None, "cwd": str(cwd)}
        if "--out" in argv:
            row["out"] = argv[argv.index("--out") + 1]
        timeout = 7200 if step == "install" else 10800 if step in ("pilot", "eval") else 3600
        started, interrupted = time.monotonic(), False
        with prefix.with_suffix(".out").open("wb") as out, prefix.with_suffix(".err").open("wb") as err:
            try:
                if prepare:
                    prepare()
                row["rc"] = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                           timeout=timeout).returncode
            except (OSError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
                interrupted = isinstance(exc, KeyboardInterrupt)
                row["rc"] = 130 if interrupted else 124 if isinstance(exc, subprocess.TimeoutExpired) else 1
                row["error"] = type(exc).__name__ + ": " + str(exc)
                err.write((row["error"] + "\n").encode("utf-8"))
        result = last_object(prefix.with_suffix(".out").read_text(encoding="utf-8", errors="replace"))
        row["run_id"], row["pass_observed"] = observed(result)
        row["seconds"] = round(time.monotonic() - started, 3)
        if step == "start" and row["rc"]:
            row["stop_reason"] = "start failed; remaining qualification steps were not run"
        rows.append(row)
        save()
        if interrupted:
            raise KeyboardInterrupt
        return row, result

    save()
    failed = False
    try:
        # Resumed G12 consumes the newest three tracer receipts in this candidate root.
        if "g12" in selected and "tracer" not in selected:
            tracer_ids = [p.parent.name for p in sorted((root / "evidence").glob("tracer*/summary.json"),
                                                       key=lambda p: p.stat().st_mtime)[-3:]]
        for step in selected:
            if order.index(step) > order.index("start"):
                health, state = run("status-before-" + step, command("omp_strata", "status", *common))
                if health["rc"] or state.get("state") != "healthy":
                    run("restart-before-" + step, restart)
            row, result = run(step, argv_for(step), cwd=workspace if step == "quickstart" else TOOLING,
                              prepare=fixture if step == "quickstart" else None)
            if step == "tracer":
                tracer_ids = row["run_id"] or []
            if step in ("pilot", "eval"):
                # The frozen evaluator (pinned in eval/tasks.json) leaves each attempt's fresh client HOME with
                # stock OMP's ~175 MB extracted native addon; drop those caches once it has exited.
                for home in (root / "work").glob("eval-*/*/client/omp/home"):
                    drop_native_cache(home)
            if step == "quickstart":
                tests, _ = run("quickstart-tests", [sys.executable, "-m", "unittest", "-v"], cwd=workspace)
                row["tests_pass_after"] = tests["rc"] == 0
                row["pass_observed"] = row["rc"] == 0 and row["tests_pass_after"]
                save()
            failed |= bool(row["rc"]) or row["pass_observed"] is False
            if step == "start" and row["rc"]:
                break
    except KeyboardInterrupt:
        return 130
    finally:
        if not args.keep_running:
            stopped, _ = run("stop", argv_for("stop"))
            failed |= bool(stopped["rc"])
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
