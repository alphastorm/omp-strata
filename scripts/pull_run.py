#!/usr/bin/env python3
"""Copy one requalify run's publication inputs from the Windows GPU host over SSH.

Run on the client machine after scripts/requalify.py has finished on the host. The run log's first line names the
run's summary, and the log must name no other run; this copies that summary, the install record, each step's result
(a tracer run's summary) and each evaluation's summary, batch and attempts into DEST with the root's relative layout,
which is the directory scripts/publish_run.py reads with --pulled. Nothing on the host changes. The copies are
unscrubbed: keep DEST private and let publish_run.py scrub what it publishes.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile


def powershell(host: str, script: str) -> str:
    body = ("$ProgressPreference='SilentlyContinue'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
            + script)
    encoded = base64.b64encode(body.encode("utf-16le")).decode()
    r = subprocess.run(["ssh", host, "powershell -NoProfile -NonInteractive -EncodedCommand " + encoded],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise SystemExit(f"{host}: exit {r.returncode}: {r.stderr[-800:]}")
    return r.stdout


def run_paths(summary: str, rows: list[dict]) -> list[str]:
    """Root-relative files that publish_run.py reads for the run whose summary is SUMMARY."""
    paths = [summary, "state/install-record.json"]
    for row in rows:
        ids = row.get("run_id")
        for run_id in ids if isinstance(ids, list) else [ids] if ids else []:
            paths.append(f"evidence/{run_id}/{'summary' if row['step'] == 'tracer' else 'result'}.json")
        if row.get("out"):
            name = str(row["out"]).replace("\\", "/").rstrip("/").split("/")[-1]
            paths += [f"eval/{name}/{file}" for file in ("summary.json", "batch.json", "attempts.jsonl")]
    return paths


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True, help="ssh destination of the GPU host")
    parser.add_argument("--root", required=True, help="the integration root on the host")
    parser.add_argument("--log", required=True, help="the requalify.py output log on the host")
    parser.add_argument("--dest", required=True, type=Path, help="a new or empty local directory")
    args = parser.parse_args(argv)
    if args.dest.exists() and any(args.dest.iterdir()):
        raise SystemExit(f"{args.dest} is not empty; publish_run.py needs exactly one run per directory")
    root = args.root.rstrip("\\")
    lines = [line.strip() for line in powershell(args.host, f"Get-Content -LiteralPath '{args.log}'").splitlines()]
    run = re.compile(re.escape(root) + r"\\evidence\\requalify-[^\\]+\\summary\.json", re.IGNORECASE)
    named = [line for line in lines if run.fullmatch(line)]
    if not lines or lines[0] not in named:
        raise SystemExit(f"the log's first line does not name a summary under {root}")
    if len(named) != 1:
        # A rerun under the same chain item appends its summary line; reading only the first pulled the earlier run.
        raise SystemExit(f"the log names {len(named)} requalify runs (a rerun appended to it); pass a log naming one run")
    summary = named[0]
    rows = json.loads(powershell(args.host, f"Get-Content -LiteralPath '{summary}' -Raw"))
    paths = run_paths(summary[len(root) + 1:].replace("\\", "/"), rows)
    r = subprocess.run(["ssh", args.host, f'tar -cf - -C "{root}" ' + " ".join(f'"{path}"' for path in paths)],
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=600)
    if r.returncode:
        raise SystemExit(f"{args.host}: tar exit {r.returncode}: {r.stderr.decode(errors='replace')[-800:]}")
    args.dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        tar.extractall(args.dest, filter="data")
    print(json.dumps({"summary": paths[0], "files": len(paths), "steps": [
        (row["step"], row.get("rc"), row.get("pass_observed")) for row in rows
        if not row["step"].startswith("status-before")]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
