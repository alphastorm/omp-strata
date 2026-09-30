"""Host-free materialization, hashing, and bounded subprocess helpers."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
IGNORED = {".git", "__pycache__"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def files(root: Path) -> list[Path]:
    if root.is_symlink():
        raise ValueError("workspace/tree root must not be a symlink")
    result = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"symlink is not permitted: {relative.as_posix()}")
        mode = path.stat().st_mode
        if stat.S_ISREG(mode):
            result.append(path)
        elif not stat.S_ISDIR(mode):
            raise ValueError(f"non-regular file: {relative.as_posix()}")
    return result


def hashes(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): digest(path.read_bytes()) for path in files(root)}


def tree_hash(root: Path) -> str:
    return digest(canonical(hashes(root)))


def materialize(task: dict, destination: Path, *, git=True) -> Path:
    from eval.generate_corpus import generate
    if destination.exists():
        raise ValueError("workspace destination already exists")
    shutil.copytree(EVAL / "tasks" / task["id"] / "workspace", destination,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if task["id"] == "long-context":
        generate(destination)
    if git:
        env = clean_env()
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["GIT_CONFIG_GLOBAL"] = os.devnull
        for argv in (["git", "-c", "init.templateDir=", "init", "-q"],
                     ["git", "-c", "core.autocrlf=false", "add", "--all"]):
            result = run_bounded(argv, cwd=destination, timeout=20, env=env)
            if result["returncode"] != 0:
                raise RuntimeError("fresh workspace git initialization failed")
    return destination


def clean_env() -> dict[str, str]:
    keep = {"PATH", "SYSTEMROOT", "COMSPEC", "PATHEXT", "WINDIR", "LANG", "LC_ALL", "LC_CTYPE"}
    return {key: value for key, value in os.environ.items() if key.upper() in keep}


def terminate(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def run_bounded(argv, *, cwd: Path, timeout: float, env=None, limit=1048576) -> dict:
    """Capture only a bounded tail; kill the owned group on time/output exhaustion."""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(argv, cwd=cwd, env=clean_env() if env is None else env,
                                   stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=os.name != "nt")
        deadline = time.monotonic() + max(0, timeout)
        timed_out = limited = False
        try:
            while process.poll() is None:
                timed_out = time.monotonic() >= deadline
                limited = os.fstat(output.fileno()).st_size > limit
                if timed_out or limited:
                    terminate(process)
                    break
                time.sleep(0.02)
        finally:
            if process.poll() is None:
                terminate(process)
        size = os.fstat(output.fileno()).st_size
        limited = limited or size > limit
        output.seek(max(0, size - limit))
        text = output.read(limit).decode("utf-8", errors="replace")
    return {"returncode": process.returncode, "stdout": text, "timed_out": timed_out,
            "output_limited": limited}


def visible_status(workspace: Path) -> dict:
    import re
    import sys
    result = run_bounded([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                         cwd=workspace, timeout=30)
    match = re.search(r"Ran (\d+) tests?", result["stdout"])
    if not match or result["timed_out"] or result["output_limited"]:
        raise RuntimeError("visible test suite did not complete")
    return {"status": "pass" if result["returncode"] == 0 else "fail",
            "exit_code": result["returncode"], "tests_run": int(match.group(1))}


def run_verifier(task: dict, workspace: Path, *, timeout=30) -> dict:
    import sys
    if timeout <= 2:
        return {"returncode": None, "stdout": "", "timed_out": True, "output_limited": False,
                "verdict": {"task": task["id"], "passed": False,
                            "details": {"error": "no verification time remains"}}}
    result = run_bounded([sys.executable, "-I", "-B", str(EVAL / "verifiers" / task["id"] / "verify.py"),
                          str(workspace), "--timeout", str(min(25, timeout - 2))],
                         cwd=EVAL, timeout=timeout, limit=1048576)
    try:
        lines = result["stdout"].splitlines()
        verdict = json.loads(lines[0]) if len(lines) == 1 else None
    except (ValueError, IndexError):
        verdict = None
    if not isinstance(verdict, dict) or verdict.get("task") != task["id"] or not isinstance(verdict.get("passed"), bool):
        verdict = {"task": task["id"], "passed": False, "details": {"error": "invalid verifier result"}}
    verdict["passed"] = (verdict["passed"] and result["returncode"] == 0 and
                         not result["timed_out"] and not result["output_limited"])
    return {**result, "verdict": verdict}


def apply_reference(task: dict, workspace: Path) -> None:
    patch = EVAL / "reference" / task["id"] / "solution.patch"
    result = run_bounded(["git", "-c", "core.autocrlf=false", "apply", "--", str(patch)],
                         cwd=workspace, timeout=20)
    if result["returncode"] != 0:
        raise RuntimeError(f"reference patch failed: {task['id']}: {result['stdout']}")


def inventory() -> dict[str, str]:
    pinned = {f"eval/{name}": value for name, value in hashes(EVAL).items() if name != "tasks.json"}
    pinned["scripts/evaluate.py"] = digest((ROOT / "scripts" / "evaluate.py").read_bytes())
    return pinned


def validate_manifest(manifest: dict) -> list[str]:
    errors = []
    actual = inventory()
    expected = manifest.get("files", {})
    for name in sorted(actual.keys() | expected.keys()):
        if actual.get(name) != expected.get(name):
            errors.append(f"frozen file mismatch: {name}")
    expected_ids = ["bugfix-a", "bugfix-b", "multifile-regression", "tool-loop", "long-context", "continuation"]
    if [task.get("id") for task in manifest.get("tasks", [])] != expected_ids:
        errors.append("manifest must contain the six tasks in frozen order")
        return errors
    with tempfile.TemporaryDirectory(prefix="eval-manifest-") as temporary:
        for task in manifest["tasks"]:
            workspace = materialize(task, Path(temporary) / task["id"], git=False)
            source = EVAL / "tasks" / task["id"]
            prompts = {p.name: digest(p.read_bytes()) for p in source.glob("*.md")}
            checks = {"workspace_sha256": tree_hash(workspace), "seed_tree_sha256": tree_hash(source / "workspace"),
                      "prompt_sha256": digest(canonical(prompts)),
                      "verifier_sha256": tree_hash(EVAL / "verifiers" / task["id"]),
                      "reference_sha256": tree_hash(EVAL / "reference" / task["id"])}
            for key, value in checks.items():
                if task.get(key) != value:
                    errors.append(f"{task['id']}: {key} mismatch")
            if task["id"] == "long-context" and task.get("generated_sha256") != tree_hash(workspace / "docs"):
                errors.append("long-context: generated corpus hash mismatch")
    return errors
