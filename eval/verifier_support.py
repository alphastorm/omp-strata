"""Immutable tests run in a separate interpreter, never copied into the workspace."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from support import digest, files, run_bounded


def integrity(verifier: Path, workspace: Path) -> list[str]:
    pin = json.loads((verifier / "immutable.json").read_text(encoding="utf-8"))
    errors = []
    try:
        files(workspace)
    except (ValueError, OSError) as exc:
        return [str(exc)]
    for name, expected in pin["files"].items():
        path = workspace / name
        if not path.exists() and name in pin.get("removable_between_phases", []):
            continue
        if not path.is_file() or digest(path.read_bytes()) != expected:
            errors.append(f"immutable file changed or missing: {name}")
    return errors


def main(verifier: Path) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--timeout", type=float, default=25)
    args = parser.parse_args()
    workspace = args.workspace.absolute()
    task = verifier.name
    details = {}
    try:
        errors = integrity(verifier, workspace)
        if errors:
            details["integrity_errors"] = errors
            passed = False
        else:
            result = run_bounded([sys.executable, "-I", "-B", str(verifier.parents[1] / "verifier_child.py"),
                                  str(verifier / "hidden.py"), str(workspace)],
                                 cwd=verifier, timeout=min(25, max(0, args.timeout)), limit=65536)
            details = {"tests": result["stdout"].strip(), "exit_code": result["returncode"],
                       "timeout": result["timed_out"], "output_limit": result["output_limited"]}
            errors = integrity(verifier, workspace)
            if errors:
                details["integrity_errors"] = errors
            passed = (result["returncode"] == 0 and not result["timed_out"] and
                      not result["output_limited"] and not errors and '"completed": true' in result["stdout"])
    except (OSError, ValueError) as exc:
        passed = False
        details = {"error": str(exc)}
    print(json.dumps({"task": task, "passed": passed, "details": details}, ensure_ascii=True))
    return 0 if passed else 1
