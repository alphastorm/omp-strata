#!/usr/bin/env python3
"""Comparison-only evaluation of a private task set through stock OMP running on this (macOS) client.

One attempt per (task, arm): a fresh workspace, an isolated OMP HOME, the pinned stock OMP in print/json mode
under `sandbox-exec` (writes only inside the attempt directory, private trees unreadable, loopback-only
network), reaching the arm's engine through an owned SSH loopback tunnel. The verifier runs afterwards, also
sandboxed, outside the agent's reach. Task sets are private directories; their CONTRACT.md defines the
format. Engine switching is delegated to the operator commands named in the private arms file.

This tool never changes launch-omp routing, an engine installation or a qualification ledger, and its
results are not gate evidence. Raw attempts (workspaces, transcripts) stay in the private output directory.

  check       per task: the untouched seed fails its verifier and the reference passes (no model)
  pull-keys   copy each placement's API key over SSH into a user-only client file (never printed)
  run         schedule attempts across hosts (resumable); results in <out>/<arm>/<task>/result.json
  summarize   pass rates per arm/track/family, paired comparisons (exact McNemar), timing
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from math import comb
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate import EventCounts, run_phase  # noqa: E402  frozen G24 primitives, imported unchanged
from eval.support import run_bounded  # noqa: E402
from omp_strata.common import atomic_write_json, read_json, sha256_file, utc_now  # noqa: E402
from omp_strata.ompcfg import (CHAT_ROLES, CONTEXT_SAFETY_TOKENS, OMP_PROFILE,  # noqa: E402
                               install_profile_config, isolated_env, omp_argv, render_config_yml, render_models_yml)
from omp_strata.profile import load as load_profile  # noqa: E402
from omp_strata.remote import SSH_OWNERSHIP, tunnel_argv, validate_key, write_private  # noqa: E402

DEFAULT_AGENT_PATH = "/opt/homebrew/opt/python@3.13/libexec/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
TOOLS = "read,bash,edit,write,grep,glob"
# Subagents run in the background; print mode ends with the lead's turn unless the lead can block on them.
FLEET_TOOLS = ",task,wait"
CAPS = {"max_event_bytes": 64 * 1024 * 1024, "max_stderr_bytes": 1024 * 1024, "total_output_tokens": 2_000_000}
FLEET_MAX_EVENT_BYTES = 1024 * 1024 * 1024
# Never readable by an agent or a verifier, whatever the arms file adds.
PRIVATE_HOME_TREES = (".ssh", ".gnupg", ".aws", ".omp", ".config", ".docker", ".kube", ".netrc", ".npmrc",
                      ".git-credentials", "Library/Keychains", "Library/Mail", "Library/Messages")
GIT_ENV = {"GIT_AUTHOR_NAME": "eval", "GIT_AUTHOR_EMAIL": "eval@example.com", "GIT_COMMITTER_NAME": "eval",
           "GIT_COMMITTER_EMAIL": "eval@example.com", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
# One worker at a time per GPU host, across `run` invocations: a second would share its engine or switch it.
HOST_LOCKS = Path(tempfile.gettempdir()) / "eval-taskset-hosts"


class EvalError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ tasks
def task_ids(taskset: Path) -> list[str]:
    return sorted(p.parent.name for p in (taskset / "tasks").glob("*/task.json"))


def load_task(taskset: Path, task_id: str) -> dict:
    directory = taskset / "tasks" / task_id
    task = read_json(directory / "task.json")
    workspace, verify, budget = task.get("workspace", {}), task.get("verify", {}), task.get("budget", {})
    problems = []
    if task.get("id") != task_id or task.get("track") not in ("private", "dev"):
        problems.append("id/track")
    if workspace.get("kind") not in ("dir", "golden"):
        problems.append("workspace.kind")
    if verify.get("kind") not in ("script", "commands"):
        problems.append("verify.kind")
    if not all(isinstance(budget.get(k), int) and budget[k] > 0 for k in ("wall_seconds", "tool_calls")):
        problems.append("budget")
    if not (directory / "prompt.md").is_file():
        problems.append("prompt.md")
    if problems:
        raise EvalError(f"{task_id}: invalid task ({', '.join(problems)})")
    task["dir"] = directory
    return task


def clone_tree(source: Path, destination: Path) -> None:
    # APFS clonefile: an instant copy-on-write tree, so every attempt owns its node_modules.
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", "-c", "-R", str(source), str(destination)], check=True, stdin=subprocess.DEVNULL)


def copy_into(source: Path, destination: Path, *, skip=()) -> None:
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if relative.as_posix() in skip or not path.is_file():
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def materialize(taskset: Path, task: dict, workspace: Path) -> Path:
    spec = task["workspace"]
    if spec["kind"] == "dir":
        workspace.mkdir(parents=True)
        copy_into(task["dir"] / "workspace", workspace)
        if spec.get("golden_ref"):
            clone_tree(taskset / "golden-src", workspace / "golden")
        out = workspace / "out"
        if out.exists() and any(out.iterdir()):
            raise EvalError(f"{task['id']}: workspace/out must start empty")
        out.mkdir(exist_ok=True)
        # inputs/ stays mode-writable so a copy of an input is an ordinary file; the agent's sandbox denies writes
        # to it (a read-only mount, not read-only bits), and the guard fails the attempt if anything changed.
        return workspace
    clone_tree(taskset / "golden-src", workspace)
    base = spec.get("base", "HEAD")
    if base != "HEAD":
        git = ["git", "--git-dir", str(taskset / "golden.git")]
        added = subprocess.run(git + ["diff", "--no-renames", "--name-only", "--diff-filter=A", base, "HEAD"],
                               check=True, capture_output=True, text=True).stdout.split()
        for name in added:
            (workspace / name).unlink(missing_ok=True)
        archive = subprocess.run(git + ["archive", "--format=tar", base], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(workspace)], input=archive, check=True)
    copy_into(task["dir"] / "workspace", workspace)
    for name in spec.get("delete", []):
        target = workspace / name
        shutil.rmtree(target) if target.is_dir() else target.unlink(missing_ok=True)
    env = {**os.environ, **GIT_ENV}
    for argv in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-qm", "task start", "--no-gpg-sign"]):
        subprocess.run(argv, cwd=workspace, env=env, check=True, stdin=subprocess.DEVNULL, capture_output=True)
    return workspace


def apply_reference(task: dict, workspace: Path) -> None:
    reference = task["dir"] / "reference"
    copy_into(reference, workspace, skip={"DELETED.txt"})
    deleted = reference / "DELETED.txt"
    if deleted.is_file():
        for name in deleted.read_text().split():
            (workspace / name).unlink(missing_ok=True)


def tree_digest(root: Path) -> str:
    entries = sorted((p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
                     for p in root.rglob("*") if p.is_file())
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()


def guard_state(task: dict, workspace: Path) -> dict:
    if task["workspace"]["kind"] == "dir":
        inputs = workspace / "inputs"
        return {"inputs": tree_digest(inputs) if inputs.is_dir() else None}
    return {name: sha256_file(workspace / name) if (workspace / name).is_file() else None
            for name in task["verify"].get("protected", [])}


def tampered(task: dict, workspace: Path, before: dict) -> str | None:
    after = guard_state(task, workspace)
    changed = sorted(name for name in before if before[name] != after.get(name))
    if not changed:
        return None
    return "inputs_modified" if task["workspace"]["kind"] == "dir" else "protected_modified:" + ",".join(changed)


# ------------------------------------------------------------------------------------------------ sandbox
def _sbpl(path: Path) -> str:
    return json.dumps(str(path))


def sandbox_profile(writable: Path, *, readable=(), deny=(), read_only=()) -> str:
    home = Path.home()
    lines = ["(version 1)", "(allow default)"]
    lines += [f"(deny file-read* file-write* (subpath {_sbpl(home / name)}))" for name in PRIVATE_HOME_TREES]
    lines += [f"(deny file-read* file-write* (subpath {_sbpl(Path(path))}))" for path in deny]
    lines.append(f"(deny file-write* (subpath {_sbpl(home)}))")
    lines += [f"(allow file-read* (subpath {_sbpl(Path(path))}))" for path in readable]
    lines.append(f"(allow file-read* file-write* (subpath {_sbpl(writable)}))")
    # Path canonicalization (realpath, `pnpm --dir`) stats every ancestor; metadata only, never directory listings.
    ancestors = sorted({parent for path in (writable, *readable) for parent in Path(path).parents})
    lines += [f"(allow file-read-metadata (literal {_sbpl(parent)}))" for parent in ancestors]
    lines += [f"(deny file-write* (subpath {_sbpl(Path(path))}))" for path in read_only]
    lines += ["(deny network-outbound)", '(allow network-outbound (remote ip "localhost:*"))']
    return "\n".join(lines) + "\n"


def sandboxed(argv: list[str], profile: Path) -> list[str]:
    return ["/usr/bin/sandbox-exec", "-f", str(profile), *argv]


# ------------------------------------------------------------------------------------------------ verify
def verify(ctx: SimpleNamespace, task: dict, workspace: Path, scratch: Path) -> dict:
    spec, started = task["verify"], time.monotonic()
    home = scratch / "verify-home"
    home.mkdir(parents=True, exist_ok=True)
    env = {"PATH": ctx.agent_path, "HOME": str(home), "LANG": "en_US.UTF-8", "NO_COLOR": "1", "CI": "1",
           **ctx.agent_env, "WORKSPACE": str(workspace), "TASK_DIR": str(task["dir"]),
           "GOLDEN_SRC": str(ctx.taskset / "golden-src")}
    profile = scratch / "verify.sb"
    profile.write_text(sandbox_profile(scratch, readable=[task["dir"], ctx.taskset / "golden-src"], deny=ctx.deny))
    timeout = spec.get("timeout_seconds", 300 if spec["kind"] == "commands" else 120)
    if spec["kind"] == "script":
        result = run_bounded(sandboxed(list(spec["argv"]), profile), cwd=task["dir"], timeout=timeout, env=env,
                             limit=262144)
        lines = [line for line in result["stdout"].splitlines() if line.strip()]
        try:
            verdict = json.loads(lines[-1])
            if result["returncode"] != 0 or not isinstance(verdict.get("passed"), bool):
                raise ValueError
        except (IndexError, ValueError, AttributeError):
            return {"passed": False, "verifier_error": True, "returncode": result["returncode"],
                    "timed_out": result["timed_out"], "tail": result["stdout"][-2000:],
                    "wall_ms": round((time.monotonic() - started) * 1000)}
        # A verifier may report hundreds of checks; keep the failures, which explain a verdict, ahead of passes.
        checks = verdict.get("checks", [])
        checks = [c for c in checks if not c.get("passed")] + [c for c in checks if c.get("passed")]
        return {"passed": verdict["passed"], "score": verdict.get("score"), "checks": checks[:50],
                "checks_total": len(checks), "returncode": 0, "wall_ms": round((time.monotonic() - started) * 1000)}
    for name in spec.get("hidden", []):
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(task["dir"] / "hidden" / name, target)
    commands, passed = [], True
    for argv in spec["commands"]:
        remaining = timeout - (time.monotonic() - started)
        result = run_bounded(sandboxed(list(argv), profile), cwd=workspace, timeout=max(1, remaining), env=env,
                             limit=262144)
        ok = result["returncode"] == 0 and not result["timed_out"]
        commands.append({"argv": argv, "returncode": result["returncode"], "timed_out": result["timed_out"],
                         "tail": "" if ok else result["stdout"][-3000:]})
        passed &= ok
        if not ok:
            break
    return {"passed": passed, "score": sum(c["returncode"] == 0 for c in commands) / len(spec["commands"]),
            "commands": commands, "wall_ms": round((time.monotonic() - started) * 1000)}


def check_one(ctx: SimpleNamespace, task_id: str) -> dict:
    task = load_task(ctx.taskset, task_id)
    scratch_root = ctx.taskset / ".check"
    scratch_root.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=scratch_root))
    try:
        report: dict = {"task": task_id}
        for label, solve in (("seed", False), ("reference", True)):
            scratch = tmp / label
            workspace = materialize(ctx.taskset, task, scratch / "workspace")
            before = guard_state(task, workspace)
            if solve:
                apply_reference(task, workspace)
            problem = tampered(task, workspace, before) if not solve else None
            verdict = verify(ctx, task, workspace, scratch)
            report[label] = {"passed": verdict["passed"] and problem is None,
                             "verifier_error": verdict.get("verifier_error", False),
                             "detail": verdict.get("tail") or next((c["tail"] for c in verdict.get("commands", [])
                                                                    if c["tail"]), "")[-1500:]}
        report["ok"] = (not report["seed"]["passed"] and not report["seed"]["verifier_error"]
                        and report["reference"]["passed"])
        return report
    finally:
        # inputs/ is made read-only for the agent; restore write permission so the scratch tree can be removed.
        subprocess.run(["chmod", "-R", "u+w", str(tmp)], check=False)
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------------------------------------ arms
def load_arms(path: Path) -> dict:
    arms = read_json(path)
    single = {name: arm for name, arm in arms["arms"].items() if arm.get("kind", "single") == "single"}
    for name, arm in single.items():
        if arm["api"] not in ("openai-completions", "openai-responses"):
            raise EvalError(f"arm {name}: unsupported api")
        arm["_profile"] = load_profile(Path(arm["profile"]))
        for placement in arm["placements"]:
            if placement not in arms["placements"]:
                raise EvalError(f"arm {name}: unknown placement {placement}")
    for name, arm in arms["arms"].items():
        if name in single:
            continue
        # A fleet: one lead plus stock subagent types, each a single arm at one of its placements.
        members = [arm["lead"], *arm["agents"].values()]
        if arm.get("kind") != "fleet" or any(m["arm"] not in single or m["placement"] not in single[m["arm"]]["placements"]
                                             for m in members):
            raise EvalError(f"arm {name}: a fleet names single arms at their own placements")
        arm["placements"] = list(dict.fromkeys(m["placement"] for m in members))
        arm["_profile"] = single[arm["lead"]["arm"]]["_profile"]
    binary = Path(arms["omp_binary"])
    pin = arms["arms"][next(iter(arms["arms"]))]["_profile"].omp_artifact("darwin-arm64")
    if binary.stat().st_size != pin["bytes"] or sha256_file(binary) != pin["sha256"]:
        raise EvalError("stock OMP binary differs from the profile pin")
    return arms


def read_key(path: Path) -> str:
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise EvalError(f"key file must be a user-only regular file: {path.name}")
    return validate_key(path.read_bytes())


def pull_keys(arms: dict) -> None:
    for name, placement in arms["placements"].items():
        remote = PureWindowsPath(placement["key_remote_path"])
        script = ("$ErrorActionPreference='Stop';[Console]::Out.Write([IO.File]::ReadAllText('"
                  + str(remote).replace("'", "''") + "'))")
        command = "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + \
            base64.b64encode(script.encode("utf-16le")).decode("ascii")
        result = subprocess.run(["ssh", "-o", "BatchMode=yes", *SSH_OWNERSHIP, placement["ssh"], command],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        if result.returncode:
            raise EvalError(f"{name}: key transfer failed (rc={result.returncode})")
        write_private(Path(placement["key_file"]), (validate_key(result.stdout) + "\n").encode("ascii"))
        print(json.dumps({"placement": name, "key": "written"}))


def http_status(url: str, key: str | None = None, timeout: float = 10) -> tuple[int, object]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"} if key else {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (OSError, ValueError):
        return 0, None


OWNED_TUNNELS: list["Tunnel"] = []


class Tunnel:
    """An owned `ssh -L` child for one placement; restarted when it dies."""

    def __init__(self, placement: dict, log):
        self.placement, self.log, self.process = placement, log, None
        OWNED_TUNNELS.append(self)

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def ensure(self, key: str, model: str) -> dict:
        port = self.placement["local_port"]
        if not self.alive():
            self.close()
            self.process = subprocess.Popen(tunnel_argv(self.placement["ssh"], port, self.placement["remote_port"]),
                                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL, start_new_session=True)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                with socket.socket() as probe:
                    if probe.connect_ex(("127.0.0.1", port)) == 0:
                        break
                if not self.alive():
                    raise EvalError(f"tunnel to {self.placement['ssh']} exited")
                time.sleep(0.5)
        status, models = http_status(f"http://127.0.0.1:{port}/v1/models", key)
        data = models.get("data", []) if isinstance(models, dict) else []
        ids = sorted(str(m.get("id")) for m in data if isinstance(m, dict))
        if status != 200 or model not in ids:
            raise EvalError(f"endpoint on {self.placement['ssh']} not serving {model} (HTTP {status}, models {ids})")
        return {"models": ids}

    def close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


# ------------------------------------------------------------------------------------------------ attempts
def ninfer_entry(arm: dict, profile, base_url: str, key_env: str) -> dict:
    """NInfer's documented Responses provider, rendered as the G25 adapter renders it."""
    return {"baseUrl": base_url, "api": "openai-responses", "apiKey": key_env, "authHeader": True, "models": [{
        "id": arm["model"], "name": arm.get("display_name", arm["model"]), "api": "openai-responses",
        "reasoning": True, "thinking": {"mode": "effort", "efforts": ["low", "medium", "xhigh"]}, "input": ["text"],
        "supportsTools": True, "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": profile.data["omp"]["context_window"] - CONTEXT_SAFETY_TOKENS,
        "maxTokens": profile.data["omp"]["max_tokens"],
        "compat": {"includeEncryptedReasoning": False, "supportsReasoningSummary": False,
                   "supportsImageDetailOriginal": False}}]}


def write_omp_config(home: Path, settings: dict, models: dict) -> None:
    directory = home / ".omp" / "profiles" / OMP_PROFILE / "agent"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config.yml").write_text(json.dumps(settings, indent=2) + "\n")
    (directory / "models.yml").write_text(json.dumps(models, indent=2) + "\n")


def agent_env(ctx: SimpleNamespace, layout, key: str) -> dict:
    env = isolated_env(layout, api_key=key)
    env["PATH"] = ctx.agent_path
    env.update(ctx.agent_env)
    return env


def omp_launch(ctx: SimpleNamespace, arm: dict, placement: dict, home: Path, key: str) -> tuple[list[str], dict]:
    profile = arm["_profile"]
    layout = SimpleNamespace(profile=profile, omp_home=home)
    home.mkdir(parents=True)
    env = agent_env(ctx, layout, key)
    base_url = f"http://127.0.0.1:{placement['local_port']}/v1"
    argv = omp_argv(layout, binary=ctx.omp_binary, extra=[])
    if arm["api"] == "openai-completions":
        install_profile_config(layout, base_url=base_url)
        return argv, env
    provider, key_env = arm["provider"], arm["key_env"]
    env.pop("STRATA_API_KEY")
    env.update({key_env: key, "PI_OPENAI_STATEFUL": "1"})
    settings = json.loads(render_config_yml(profile))
    route = provider + "/" + arm["model"]
    settings["modelRoles"] = {role: route for role in CHAT_ROLES}
    settings["providers"]["maxInFlightRequests"] = {provider: 1}
    write_omp_config(home, settings, {"providers": {provider: ninfer_entry(arm, profile, base_url, key_env)}})
    argv[argv.index("--model") + 1] = route
    return argv, env


def fleet_launch(ctx: SimpleNamespace, arm: dict, home: Path, keys: dict[str, str]) -> tuple[list[str], dict]:
    """A lead plus stock subagent types on other hosts, assigned the way a fleet route assigns them: the lead
    takes every chat role except task/advisor/judge, which go to the `task` agent's model."""
    profile = arm["_profile"]
    layout = SimpleNamespace(profile=profile, omp_home=home)
    home.mkdir(parents=True)
    env = agent_env(ctx, layout, keys[arm["lead"]["placement"]])
    env.pop("STRATA_API_KEY")
    providers, routes = {}, {}
    for name in arm["placements"]:
        placement = ctx.arms["placements"][name]
        member = ctx.arms["arms"][next(m["arm"] for m in (arm["lead"], *arm["agents"].values())
                                       if m["placement"] == name)]
        base_url = f"http://127.0.0.1:{placement['local_port']}/v1"
        key_env = "EVAL_" + placement["host"].upper().replace("-", "_") + "_KEY"
        env[key_env] = keys[name]
        if member["api"] == "openai-completions":
            provider, model = "strata-" + placement["host"], member["_profile"].data["strata"]["model_name"]
            entry = json.loads(render_models_yml(member["_profile"], base_url=base_url))["providers"]["strata-local"]
            entry["apiKey"] = key_env
        else:
            provider, model = member["provider"], member["model"]
            entry = ninfer_entry(member, profile, base_url, key_env)
            env["PI_OPENAI_STATEFUL"] = "1"
        providers[provider] = entry
        routes[name] = provider + "/" + model
    lead = routes[arm["lead"]["placement"]]
    agents = {agent: routes[member["placement"]] for agent, member in arm["agents"].items()}
    worker = agents.get("task", lead)
    settings = json.loads(render_config_yml(profile))
    settings["modelRoles"] = {role: worker if role in ("task", "advisor", "judge") else lead for role in CHAT_ROLES}
    settings["providers"]["maxInFlightRequests"] = {provider: 1 for provider in providers}
    settings["task"] = {"agentModelOverrides": agents}
    write_omp_config(home, settings, {"providers": providers})
    argv = omp_argv(layout, binary=ctx.omp_binary, extra=[])
    argv[argv.index("--model") + 1] = lead
    return argv, env


def redact(directory: Path, secret: str) -> int:
    hits, needle = 0, secret.encode("ascii")
    for path in directory.rglob("*"):
        parts = path.relative_to(directory).parts
        if "node_modules" in parts or "golden" in parts[:2] or not path.is_file() or path.is_symlink():
            continue
        try:
            if path.stat().st_size > CAPS["max_event_bytes"]:
                continue
            data = path.read_bytes()
        except OSError:
            # Agent tools leave files they made unreadable (e.g. permission tests in their temp dir); the key
            # never reaches those, since OMP holds it only in its environment.
            continue
        if needle in data:
            path.write_bytes(data.replace(needle, b"[redacted-key]"))
            hits += 1
    return hits


def drop_progress_events(events: Path) -> None:
    """Keep a fleet transcript small: tool progress snapshots (a running subagent's grow with its transcript)
    repeat what the final tool results and the subagents' own sessions record."""
    kept = events.with_suffix(".compact")
    with events.open("rb") as source, kept.open("wb") as target:
        for line in source:
            if not line.startswith(b'{"type":"tool_execution_update"'):
                target.write(line)
    kept.replace(events)


def run_attempt(ctx: SimpleNamespace, arm_name: str, task_id: str, placement_names: list[str], endpoint: dict) -> dict:
    arm = ctx.arms["arms"][arm_name]
    placements = {name: ctx.arms["placements"][name] for name in placement_names}
    task = load_task(ctx.taskset, task_id)
    attempt = ctx.out / arm_name / task_id
    if attempt.exists():
        attempt.rename(attempt.with_name(f"{task_id}.interrupted-{int(time.time())}"))
    attempt.mkdir(parents=True)
    keys = {name: read_key(Path(placement["key_file"])) for name, placement in placements.items()}
    workspace = materialize(ctx.taskset, task, attempt / "workspace")
    before = guard_state(task, workspace)
    fleet = arm.get("kind") == "fleet"
    if fleet:
        argv, env = fleet_launch(ctx, arm, attempt / "omp-home", keys)
    else:
        (name, placement), = placements.items()
        argv, env = omp_launch(ctx, arm, placement, attempt / "omp-home", keys[name])
    profile = attempt / "agent.sb"
    profile.write_text(sandbox_profile(attempt, readable=[ctx.omp_binary.parent], deny=ctx.deny,
                                       read_only=[workspace / "inputs"]))
    wall = task["budget"]["wall_seconds"]
    prompt = (task["dir"] / "prompt.md").read_text(encoding="utf-8")
    if arm.get("prompt_suffix"):
        # The owner's own words appended to every request, e.g. asking a fleet lead to use its subagents.
        prompt = prompt.rstrip("\n") + "\n\n" + arm["prompt_suffix"]
    extra = ["-p", "--mode", "json", "--auto-approve", "--max-time", f"{wall}s",
             "--session-dir", str(attempt / "sessions"), "--tools", TOOLS + (FLEET_TOOLS if fleet else ""), prompt]
    if arm.get("append_system_prompt"):
        # An arm-wide instruction, as the owner's own system-prompt addition would be (e.g. when to delegate).
        extra[:0] = ["--append-system-prompt", arm["append_system_prompt"]]
    (attempt / "sessions").mkdir()
    counts, started_utc, started = EventCounts(), utc_now(), time.monotonic()
    budget = {**CAPS, "tool_calls": task["budget"]["tool_calls"]}
    if fleet:
        # The lead's stream also carries each running subagent's progress snapshots, which grow with that
        # subagent's transcript; the solo cap would end a delegating attempt on volume alone.
        budget["max_event_bytes"] = FLEET_MAX_EVENT_BYTES
    phase = run_phase(sandboxed(argv + extra, profile), workspace=workspace, env=env, directory=attempt, phase=1,
                      deadline=started + wall + 20, budget=budget, counts=counts)
    agent_ms = round((time.monotonic() - started) * 1000)
    if fleet:
        drop_progress_events(Path(phase["events"]))
    problem = tampered(task, workspace, before)
    verdict = {"passed": False, "skipped": problem} if problem else verify(ctx, task, workspace, attempt)
    record = {
        "schema_version": 1, "task": task_id, "track": task["track"], "family": task.get("family"),
        "difficulty": task.get("difficulty"), "arm": arm_name, "placement": ",".join(placement_names),
        "host": ",".join(p["host"] for p in placements.values()), "started_utc": started_utc,
        "passed": bool(verdict["passed"]),
        "score": verdict.get("score"), "tamper": problem, "verifier_error": verdict.get("verifier_error", False),
        "abort_reason": phase["abort_reason"], "exit_code": phase["exit_code"], "completed": phase["completed"],
        "agent_wall_ms": agent_ms, "verify_wall_ms": verdict.get("wall_ms"), "tool_calls": counts.tool_calls,
        "assistant_messages": counts.assistants,
        "output_tokens": counts.output_tokens if counts.output_usage_known and counts.assistants else None,
        "protocol_errors": counts.summary(), "endpoint": endpoint, "verifier": verdict,
    }
    record["redacted_files"] = sum(redact(attempt, key) for key in keys.values())
    atomic_write_json(attempt / "result.json", record)
    return record


# ------------------------------------------------------------------------------------------------ scheduling
def take_pid_file(path: Path) -> bool:
    """Create `path` exclusively for this process; one whose process is gone is taken over."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                os.kill(int(json.loads(path.read_text())["pid"]), 0)
                return False  # a live run owns it
            except PermissionError:
                return False
            except (ProcessLookupError, ValueError, KeyError, TypeError, OSError):
                path.unlink(missing_ok=True)  # its run is gone
                continue
        with os.fdopen(fd, "w") as stream:
            json.dump({"pid": os.getpid(), "utc": utc_now()}, stream)
        return True
    return False


class Scheduler:
    def __init__(self, ctx: SimpleNamespace, tasks: list[str], arm_names: list[str]):
        self.ctx, self.lock = ctx, threading.Lock()
        self.pending = {arm: [t for t in tasks if not (ctx.out / arm / t / "result.json").exists()] for arm in arm_names}
        self.log_path = ctx.out / "run.log"
        self.retries: dict[tuple[str, str], int] = {}

    def log(self, **fields) -> None:
        line = json.dumps({"utc": utc_now(), **fields})
        with self.lock:
            with self.log_path.open("a") as stream:
                stream.write(line + "\n")
        print(line, flush=True)

    def _claim_path(self, arm: str, task: str) -> Path:
        return self.ctx.out / arm / f".{task}.claim"

    def _take(self, arm: str, task: str) -> bool:
        """An exclusive claim file lets several `run` invocations (e.g. on different hosts) share an arm."""
        return take_pid_file(self._claim_path(arm, task))

    def claim(self, arm: str) -> str | None:
        with self.lock:
            while self.pending.get(arm):
                task = self.pending[arm].pop(0)
                if not (self.ctx.out / arm / task / "result.json").exists() and self._take(arm, task):
                    return task
            return None

    def unclaim(self, arm: str, task: str) -> None:
        self._claim_path(arm, task).unlink(missing_ok=True)

    def release(self, arm: str, task: str) -> None:
        self.unclaim(arm, task)
        with self.lock:
            self.pending[arm].insert(0, task)

    def endpoints(self, arm: dict, names: list[str], tunnels: dict) -> dict:
        """Open (or reuse) each placement's tunnel and check that it serves the expected model."""
        arms, found = self.ctx.arms, {}
        for name in names:
            placement = arms["placements"][name]
            member = arm if arm.get("kind") != "fleet" else arms["arms"][next(
                m["arm"] for m in (arm["lead"], *arm["agents"].values()) if m["placement"] == name)]
            model = member.get("model") or member["_profile"].data["strata"]["model_name"]
            tunnel = tunnels.setdefault(name, Tunnel(placement, self.log))
            found[name] = tunnel.ensure(read_key(Path(placement["key_file"])), model)
        return found

    def placements(self, host: str, arm: dict) -> list[str]:
        return (arm["placements"] if arm.get("kind") == "fleet"
                else [next(p for p in arm["placements"] if self.ctx.arms["placements"][p]["host"] == host)])

    def host_worker(self, host: str) -> None:
        """One worker per host (or per fleet, which spans several hosts); it walks its arms in order."""
        arms, active, tunnels, locks = self.ctx.arms, set(), {}, []
        order = [name for name in arms["hosts"][host]["order"] if name in self.pending]
        try:
            for gpu_host in sorted({arms["placements"][p]["host"] for name in order
                                    for p in self.placements(host, arms["arms"][name])}):
                lock = HOST_LOCKS / f"{gpu_host}.lock"
                if not take_pid_file(lock):
                    self.log(host=host, event="host_stopped", error=f"{gpu_host} is in use by another run")
                    return
                locks.append(lock)
            for arm_name in order:
                arm = arms["arms"][arm_name]
                names = self.placements(host, arm)
                while (task := self.claim(arm_name)) is not None:
                    try:
                        for name in names:
                            if name not in active:
                                self.log(host=host, event="activate", placement=name)
                                result = run_bounded(arms["placements"][name]["activate"], cwd=ROOT, timeout=1500,
                                                     env=dict(os.environ))
                                if result["returncode"] != 0:
                                    raise EvalError(f"activate {name} failed: {result['stdout'][-500:]}")
                                # Activation stops every other engine on that host.
                                same_host = arms["placements"][name]["host"]
                                active = {a for a in active if arms["placements"][a]["host"] != same_host} | {name}
                        endpoint = self.endpoints(arm, names, tunnels)
                    except EvalError as exc:
                        self.release(arm_name, task)
                        self.log(host=host, event="host_stopped", error=str(exc))
                        return
                    self.log(host=host, event="attempt_start", arm=arm_name, task=task)
                    try:
                        record = run_attempt(self.ctx, arm_name, task, names, endpoint)
                    except Exception as exc:  # noqa: BLE001 - one harness failure must not stop the batch
                        self.unclaim(arm_name, task)
                        self.log(host=host, event="attempt_error", arm=arm_name, task=task,
                                 error=f"{type(exc).__name__}: {exc}"[:500])
                        continue
                    try:
                        # endpoints() reopens a dead tunnel, which would hide a connection the attempt lost.
                        if lost := [name for name in names if not tunnels[name].alive()]:
                            raise EvalError(f"tunnel to {', '.join(lost)} closed during the attempt")
                        self.endpoints(arm, names, tunnels)
                    except EvalError as exc:
                        # The endpoint failed during or right after the attempt: an infrastructure fault, not a
                        # model result. Keep the attempt for inspection and rerun it once on re-activated engines.
                        active = set()
                        if self.retries.get((arm_name, task), 0) < 1:
                            self.retries[(arm_name, task)] = self.retries.get((arm_name, task), 0) + 1
                            attempt = self.ctx.out / arm_name / task
                            attempt.rename(attempt.with_name(f"{task}.infra-{int(time.time())}"))
                            self.release(arm_name, task)
                            self.log(host=host, event="attempt_infra_retry", arm=arm_name, task=task, error=str(exc))
                            continue
                    self.unclaim(arm_name, task)
                    self.log(host=host, event="attempt_end", arm=arm_name, task=task, passed=record["passed"],
                             agent_s=round(record["agent_wall_ms"] / 1000), abort=record["abort_reason"],
                             tools=record["tool_calls"])
        finally:
            for tunnel in tunnels.values():
                tunnel.close()
            for lock in locks:
                lock.unlink(missing_ok=True)


# ------------------------------------------------------------------------------------------------ summary
def mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarize(out: Path) -> dict:
    results = {}
    for path in sorted(out.glob("*/*/result.json")):
        record = read_json(path)
        # Only <out>/<arm>/<task>/ is scored; attempts moved aside (`.infra-*`, `.interrupted-*`) are kept to inspect.
        if (path.parent.parent.name, path.parent.name) == (record["arm"], record["task"]):
            results.setdefault(record["arm"], {})[record["task"]] = record
    report = {"arms": {}, "pairs": []}
    for arm, records in sorted(results.items()):
        rows = list(records.values())
        def rate(selected):
            return {"passed": sum(r["passed"] for r in selected), "n": len(selected)}
        walls = [r["agent_wall_ms"] / 1000 for r in rows]
        report["arms"][arm] = {
            "all": rate(rows),
            "tracks": {t: rate([r for r in rows if r["track"] == t]) for t in sorted({r["track"] for r in rows})},
            "families": {f: rate([r for r in rows if r["family"] == f]) for f in sorted({r["family"] for r in rows})},
            "difficulty": {d: rate([r for r in rows if r["difficulty"] == d])
                           for d in sorted({str(r["difficulty"]) for r in rows})},
            "median_agent_s": round(statistics.median(walls), 1) if walls else None,
            "total_agent_s": round(sum(walls)),
            "output_tokens": sum(r["output_tokens"] or 0 for r in rows),
            "aborts": {k: sum(r["abort_reason"] == k for r in rows) for k in sorted({str(r["abort_reason"]) for r in rows})},
            "harness_issues": sum(bool(r["verifier_error"]) or bool(r["tamper"]) for r in rows),
        }
    names = sorted(results)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            common = sorted(set(results[a]) & set(results[b]))
            both = sum(results[a][t]["passed"] and results[b][t]["passed"] for t in common)
            only_a = sum(results[a][t]["passed"] and not results[b][t]["passed"] for t in common)
            only_b = sum(results[b][t]["passed"] and not results[a][t]["passed"] for t in common)
            report["pairs"].append({"a": a, "b": b, "n": len(common), "both": both, "a_only": only_a,
                                    "b_only": only_b, "neither": len(common) - both - only_a - only_b,
                                    "mcnemar_p": round(mcnemar_p(only_a, only_b), 4)})
    return report


# ------------------------------------------------------------------------------------------------ main
def context(args, arms=None) -> SimpleNamespace:
    taskset = Path(args.taskset).expanduser().resolve()
    deny = [Path(p).expanduser() for p in (arms or {}).get("sandbox_deny", [])]
    # Hidden material and every other attempt are unreadable to the agent; only the attempt itself is writable.
    deny += [taskset]
    if getattr(args, "out", None):
        deny.append(Path(args.out).expanduser().resolve())
    return SimpleNamespace(taskset=taskset, arms=arms, deny=deny,
                           agent_path=(arms or {}).get("agent_path", DEFAULT_AGENT_PATH),
                           # Tool settings the sandbox needs (e.g. a package manager that must not go online).
                           agent_env=dict((arms or {}).get("agent_env", {})),
                           omp_binary=Path(arms["omp_binary"]) if arms and "omp_binary" in arms else None,
                           out=Path(args.out).expanduser().resolve() if getattr(args, "out", None) else None)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("--taskset", required=True)
    check.add_argument("--task", action="append", help="task id (repeatable; default: all)")
    check.add_argument("--jobs", type=int, default=4)
    check.add_argument("--arms", help="arms file whose agent_path/agent_env/sandbox_deny the verifier uses")
    keys = commands.add_parser("pull-keys")
    keys.add_argument("--arms", required=True)
    run = commands.add_parser("run")
    run.add_argument("--taskset", required=True)
    run.add_argument("--arms", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--task", action="append", help="task id (repeatable; default: all)")
    run.add_argument("--arm", action="append", help="arm name (repeatable; default: all)")
    run.add_argument("--host", action="append", help="host to use (repeatable; default: all)")
    summary = commands.add_parser("summarize")
    summary.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "summarize":
        print(json.dumps(summarize(Path(args.out).expanduser()), indent=2))
        return 0
    if args.command == "pull-keys":
        pull_keys(read_json(Path(args.arms).expanduser()))
        return 0
    if args.command == "check":
        ctx = context(args, read_json(Path(args.arms).expanduser()) if args.arms else None)
        ids = args.task or task_ids(ctx.taskset)
        failures = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for report in pool.map(lambda t: check_one(ctx, t), ids):
                failures += not report["ok"]
                print(json.dumps(report), flush=True)
        print(json.dumps({"checked": len(ids), "failed": failures}))
        return 1 if failures else 0
    arms = load_arms(Path(args.arms).expanduser())
    ctx = context(args, arms)
    ctx.out.mkdir(parents=True, exist_ok=True)
    tasks = args.task or task_ids(ctx.taskset)
    for task in tasks:
        load_task(ctx.taskset, task)
    scheduler = Scheduler(ctx, tasks, args.arm or list(arms["arms"]))
    hosts = args.host or list(arms["hosts"])
    threads = [threading.Thread(target=scheduler.host_worker, args=(host,), name=host) for host in hosts]
    scheduler.log(event="run_start", tasks=len(tasks), arms=list(scheduler.pending), hosts=hosts)
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    left = {arm: len(items) for arm, items in scheduler.pending.items() if items}
    scheduler.log(event="run_end", unscheduled=left)
    return 1 if left else 0


def _terminate(signum, _frame) -> None:
    # Tunnels run in their own sessions, so a killed runner would orphan them. Attempts left without
    # result.json are renamed `.interrupted-*` and rerun by the next `run`.
    for tunnel in OWNED_TUNNELS:
        tunnel.close()
    os._exit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT, _terminate)
    raise SystemExit(main())
