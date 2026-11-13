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
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

TOOLING = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLING))
from omp_strata.ompcfg import drop_native_cache  # noqa: E402
from omp_strata import dsv41  # noqa: E402
from omp_strata.common import atomic_write_json, read_json  # noqa: E402

STEPS = ("install", "keygen", "start", "g10", "tracer", "g12", "g13", "g14", "g14q", "g15", "g16",
         "g17", "g18", "g18l", "g19", "g20", "pilot", "eval", "quickstart", "g21", "stop")

# Measured steps select a gate; the first supplies its publication receipt name.
GATE_STEPS = {
    "G10": ("g10",), "G11": ("tracer",), "G12": ("g12",), "G13": ("g13",),
    "G14": ("g14", "g14q"), "G15": ("g15",), "G16": ("g16",),
    "G17": ("g17",), "G18": ("g18l", "g18"), "G19": ("g19",),
    "G20": ("g20",), "G21": ("g21",), "G24": ("eval", "pilot"),
    "G26": ("quickstart",),
}
# G24 passes on its scored batch alone (the pilot is reported when present); G26 also needs setup rows
# from this summary, not an earlier installation run. quickstart emits quickstart-tests itself; it is not
# a selectable launch step.
SAME_RUN_STEPS = {**GATE_STEPS, "G24": ("eval",), "G26": (*GATE_STEPS["G26"], "install", "start")}
# `omp_strata.py status` states with no live owned process (not installed, stopped, exited): a root a launch may enter.
IDLE_STATES = ("not_installed", "stopped", "failed")


def step_timeout(step, *, deepseek=False):
    default = 7200 if step == "install" else 10800 if step in ("pilot", "eval") else 3600
    return dsv41.STEP_TIMEOUTS.get(step, default) if deepseek else default


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
    parser.add_argument("--run-id", help="one-shot run identity; permanently fences this candidate root "
                                         "(an unnamed run takes the same fence and releases it on a handled exit)")
    parser.add_argument("--from", dest="first", choices=(*STEPS, "perf"), default=STEPS[0])
    parser.add_argument("--only", help="comma-separated steps, executed in canonical order")
    parser.add_argument("--keep-running", action="store_true", help="skip the final stop")
    parser.add_argument("--dry-run", action="store_true", help="print argv without creating files or processes")
    parser.add_argument("--diagnostic", action="store_true", help="allow partial gates that will not publish")
    args = parser.parse_args()
    if args.run_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", args.run_id):
        parser.error("invalid --run-id")
    order = (*STEPS[:-1], "perf", "stop") if args.first == "perf" or "perf" in (args.only or "").split(",") else STEPS
    only = set(args.only.split(",")) if args.only is not None else set(order)
    if only - set(order):
        parser.error("unknown steps: " + ", ".join(sorted(only - set(order))))
    selected = [step for step in order[order.index(args.first):] if step in only and step != "stop"]
    selected_steps, partial = set(selected), []
    for gate, steps in GATE_STEPS.items():
        if not selected_steps.intersection(steps):
            continue
        missing = [step for step in SAME_RUN_STEPS[gate] if step not in selected_steps]
        if missing:
            partial.append(f"{gate}: missing same-run steps: " + ", ".join(missing))
    if partial and not args.diagnostic:
        parser.error("; ".join(partial) + ". Select complete gates or use --diagnostic for a partial run.")
    for detail in partial:
        print(detail + "; will not publish", file=sys.stderr, flush=True)
    root, profile = Path(args.root).resolve(), Path(args.profile).resolve()
    began = datetime.now(timezone.utc)
    stamp = args.run_id or began.strftime("%Y%m%dT%H%M%S%fZ")
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
            # G20's untouched-~/.omp baseline is this run's start: a shared host's other tenants may use the user's
            # default OMP home between exclusive holds, before this run began.
            extra = (["--deep"] if step == "g10" else ["--runs", *tracer_ids] if step == "g12"
                     else ["--since", f"{began.timestamp():.3f}"] if step == "g20" else [])
            return command("realhost_gates", step, *common, *extra)
        if step == "tracer":
            return command("tracer", *common, "--runs", "3",
                           *(["--max-time", str(dsv41.INVOCATION_TIMEOUT_S)] if deepseek else []))
        if step in ("pilot", "eval"):
            out = root / "eval" / (stamp + ("-pilot" if step == "pilot" else "-scored"))
            return command("evaluate", *common, "--attempts", "1" if step == "pilot" else "3",
                           "--out", str(out), "--between-phases", hook, *(["--pilot"] if step == "pilot" else []))
        if step == "quickstart":
            return command("omp_strata", "launch-omp", *common, "--", "-p", "--auto-approve",
                           "Run the tests and fix the failing one.")
        return command("omp_strata", step, *common)

    if args.dry_run:
        deepseek = profile.is_file() and dsv41.is_pinned(read_json(profile))
        tracer_ids = ["<tracer-run-1>", "<tracer-run-2>", "<tracer-run-3>"]
        for step in selected + ([] if args.keep_running else ["stop"]):
            print(step + ": " + json.dumps(argv_for(step)))
        return 0
    # The root's one admission point, taken by every launch mode through an exclusive link; there is no
    # separate occupancy pre-check. A named run keeps it; an unnamed run releases it on every handled exit.
    fence = root / "state" / "requalify-run.json"
    result_path = evidence / "result.json"
    admission = None
    # Admission is complete only once this launch, holding the fence, has found no earlier run evidence it may not
    # share and created its own evidence directory. Nothing acts on the root before that.
    owned = checked = attempted = made = refused = False
    clear = False  # Its pre-launch status reported the root idle: only then may it stop what it starts.
    # What that status read reported: its state (None when the read failed or could not be parsed) and exit code.
    status_state = status_rc = None
    rc, failed, completed = 1, False, False
    error = None
    deepseek = False

    def admit(*, recovering: bool) -> bool:
        """Complete admission under the fence; False is a refusal that leaves everything but the fence untouched."""
        nonlocal checked, attempted, made, refused
        if not checked:
            # Every run needs its own directory name; a named run also needs a root without earlier run evidence.
            if evidence.exists() or args.run_id is not None and any((root / "evidence").glob("requalify-*")):
                refused = True
                return False
            checked = True
        interrupted_mkdir, attempted = attempted, True
        try:
            evidence.mkdir(parents=True)  # Exclusive: never adopt another run's directory.
        except FileExistsError:
            # Recovery only: after the check under the fence, an empty directory is this launch's own mkdir that an
            # interrupt cut off before it was recorded.
            if not (recovering and interrupted_mkdir) or any(evidence.iterdir()):
                refused = True
                return False
        made = True
        return True

    def save() -> None:
        atomic_write_json(summary, rows)

    def fixture() -> None:
        from tracer import CALC, TESTS, hostrun
        hostrun.git_fixture(workspace, {"calc.py": CALC, "test_calc.py": TESTS})

    def run(step: str, argv: list[str], *, cwd: Path = TOOLING, prepare=None) -> tuple[dict, dict]:
        prefix = evidence / f"{len(rows) + 1:02d}-{step}"
        row = {"step": step, "argv": argv, "rc": None, "started_utc": utc_now(), "seconds": 0,
               "run_id": None, "pass_observed": None, "cwd": str(cwd)}
        if "--out" in argv:
            row["out"] = argv[argv.index("--out") + 1]
        timeout = step_timeout(step, deepseek=deepseek)
        started, interrupted = time.monotonic(), False
        rows.append(row)
        save()  # An interrupted launch is an attempted step, not an absent one.
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
        save()
        if interrupted:
            raise KeyboardInterrupt
        return row, result

    try:
        fence.parent.mkdir(parents=True, exist_ok=True)
        admission = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".requalify-admission-",
                                               dir=fence.parent, delete=False)
        json.dump({"run_id": args.run_id, "summary": str(summary)}, admission)
        admission.flush()
        os.fsync(admission.fileno())
        admission.close()
        try:
            os.link(admission.name, fence)
        except FileExistsError:
            print("qualification refused: candidate root already holds a run (state/requalify-run.json); "
                  "without its live process that run's progress is unknown", file=sys.stderr)
            return 2
        owned = True
        if not admit(recovering=False):
            print("qualification refused: candidate root already holds a run's evidence", file=sys.stderr)
            return 2
        # First post-admission effect: publish the explicit non-terminal state.
        atomic_write_json(result_path, {"schema_version": 1, "run_id": args.run_id, "rc": None,
                                       "failed": False, "completed": False, "steps": [], "finished_utc": None})
        save()
        deepseek = profile.is_file() and dsv41.is_pinned(read_json(profile))
        # The launch proceeds only when the status read reports an idle state. Anything else is refused before any
        # step can install over, start beside or stop what is there: a live runtime, a root installed for another
        # profile, and a status that failed or could not be parsed.
        status_row, reported = run("status-before-launch", command("omp_strata", "status", *common))
        status_rc = status_row["rc"]
        if "error" not in status_row and isinstance(reported.get("state"), str):
            status_state = reported["state"]
        if status_state not in IDLE_STATES:
            rc, error = 2, "root_not_idle"
            print(f"qualification refused: candidate root is not idle (status: {status_state or 'unreadable'})",
                  file=sys.stderr)
            return rc
        clear = True
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
        completed = all(any(row["step"] == step for row in rows) for step in selected)
        rc = int(failed)
    except KeyboardInterrupt:
        rc = 130
    except Exception as exc:
        error = type(exc).__name__
        rc = 1
    finally:
        try:
            if not owned and admission is not None:
                # A handled signal can arrive after link() creates the fence but
                # before it returns. File identity proves this invocation owns it.
                try:
                    owned = os.path.samefile(admission.name, fence)
                except FileNotFoundError:
                    pass
            if owned and not made and not refused:
                # An interrupt arrived before admission completed: decide it here exactly as the protected region would
                # have. Admitted, the run writes a result recording that no step ran; refused, it touches nothing.
                try:
                    if not admit(recovering=True):
                        print("qualification refused: candidate root already holds a run's evidence", file=sys.stderr)
                except Exception as exc:
                    error = type(exc).__name__
            # Nothing below acts on the root unless this launch completed admission.
            if made:
                try:
                    if clear and not args.keep_running:
                        stopped, _ = run("stop", argv_for("stop"))
                        failed |= bool(stopped["rc"])
                        if rc == 0 and failed:
                            rc = 1
                except KeyboardInterrupt:
                    rc, completed = 130, False
                except Exception as exc:
                    error = type(exc).__name__
                    rc, completed = 1, False
                finally:
                    # Both files, always: the summary has no rows when no step ran, and equals the result's steps.
                    save()
                    atomic_write_json(result_path, {
                        "schema_version": 1, "run_id": args.run_id, "rc": rc,
                        "failed": failed or rc != 0, "completed": completed and rc not in (130, 143),
                        "selected_steps": selected + ([] if args.keep_running else ["stop"]),
                        "steps": rows, "error": error, "status_state": status_state, "status_rc": status_rc,
                        "finished_utc": utc_now()})
            # Reached only after any due terminal result is written: an unnamed run, or a launch that did not complete
            # admission, releases the fence it owns. A named run's fence stays; so does any whose finalization failed.
            if owned and (args.run_id is None or not made):
                try:
                    if os.path.samefile(admission.name, fence):
                        fence.unlink()
                except FileNotFoundError:
                    pass
        finally:
            if admission is not None:
                admission.close()
                Path(admission.name).unlink(missing_ok=True)
    return rc


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
