#!/usr/bin/env python3
"""Private, non-resumable G25 preparation and supported-controller window driver.

Config (all paths absolute): comparison_id, comparison_root, initial_owner
(strata/ninfer/none), host {label, display_attached, min_ram_gib,
min_available_ram_gib, min_commit_headroom_gib, min_disk_gib}, strata
{root, profile, manifest, key_file, port}, ninfer {lane, root, manifest,
key_file, port, quantization, controller, state_root}. Optional omp_binary,
python, gpu_index, nvidia_smi, gpu_release_mib (at most 1500).
Each arm accepts start_argv/stop_argv/status_argv. Stock native defaults are
constructed when omitted. Docker replaces controller/state_root with explicit
start_argv/stop_argv/docker_identity_probe_argv/gpu_process_names. Its identity
probe must also observe network_connections, or set docker_network_probe_argv.
Prepare requires the selected NInfer lane already authenticated and ready; it
never starts an engine. Both installations and manifests must already verify.
Config changes, interrupted reservations and failed steps require a new root.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    from scripts import g25_host_probe as probe
except ModuleNotFoundError:  # The read-only smoke can copy just these two scripts.
    import g25_host_probe as probe

HostError = probe.HostError
ARMS = ("strata", "ninfer")
WINDOW_ARMS = ("strata", "ninfer", "ninfer", "strata", "strata", "ninfer")
HASH_FIELDS = {"runtime_identity_sha256": "binary_sha256", "config_identity_sha256": "config_sha256",
               "model_identity_sha256": "model_artifact_sha256"}


def config_load(path):
    config = probe.read_json(path)
    from omp_strata.comparison import SAFE_ID, validate_docker_probe_argv
    from omp_strata.layout import Layout
    from omp_strata.profile import load
    if not SAFE_ID.fullmatch(config.get("comparison_id", "")):
        raise HostError("safe comparison id required")
    if config.get("initial_owner") not in (*ARMS, "none"):
        raise HostError("explicit initial owner required")
    for field in ("comparison_root",):
        if not Path(config[field]).is_absolute():
            raise HostError("absolute private paths required")
    for arm in ARMS:
        for field in ("root", "manifest", "key_file", *(("profile",) if arm == "strata" else ())):
            if not Path(config[arm][field]).is_absolute():
                raise HostError("absolute installed paths required")
        port = config[arm]["port"]
        if type(port) is not int or not 1 <= port <= 65535:
            raise HostError("valid loopback port required")
    profile = load(Path(config["strata"]["profile"]))
    layout = Layout(Path(config["strata"]["root"]), profile)
    config.setdefault("omp_binary", str(layout.omp_binary().resolve()))
    config.setdefault("python", sys.executable)
    base = [config["python"], str(ROOT / "scripts" / "omp_strata.py")]
    for action in ("start", "stop", "status"):
        config["strata"].setdefault(action + "_argv", [*base, action, "--profile", config["strata"]["profile"],
                                                     "--root", config["strata"]["root"]])
        if config["ninfer"]["lane"] != "rtx5090-docker-local":
            config["ninfer"].setdefault(action + "_argv", ["powershell.exe", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-File", config["ninfer"]["controller"], "-Action", action.title(),
                "-StateRoot", config["ninfer"]["state_root"]])
    if not 0 < config.get("gpu_release_mib", 1500) <= 1500:
        raise HostError("GPU release threshold must be at most 1500 MiB")
    root = Path(config["comparison_root"]).resolve()
    forbidden = (ROOT, Path.home() / ".omp", *(Path(config[arm]["root"]).resolve() for arm in ARMS))
    if any(root == item or root.is_relative_to(item) or item.is_relative_to(root) for item in forbidden):
        raise HostError("private comparison root must be separate from repository, installs and default HOME")
    for arm in ARMS:
        binding = config[arm]
        for action in ("start", "stop"):
            argv = binding.get(action + "_argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v for v in argv):
                raise HostError("each arm requires explicit argv lifecycle commands")
        for field, argv in binding.items():
            if field.endswith("_argv"):
                for owner in ARMS:
                    key = Path(config[owner]["key_file"]).read_text(encoding="ascii").strip()
                    validate_docker_probe_argv(argv, key=key)
    return config


def http_json(port, path, key, *, deadline):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                    headers={"Authorization": "Bearer " + key} if key else {})
    try:
        with opener.open(request, timeout=probe.remaining(deadline, 5)) as response:
            raw = response.read((1 << 20) + 1)
            if len(raw) > 1 << 20:
                raise HostError("endpoint response exceeds its boundary")
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        return code, None
    except (OSError, urllib.error.URLError, ValueError):
        return 0, None


def endpoint_status(config, arm, *, deadline):
    binding = config[arm]
    key = Path(binding["key_file"]).read_text(encoding="ascii").strip()
    if not 32 <= len(key) <= 512 or not all(33 <= ord(ch) <= 126 for ch in key):
        raise HostError("private engine key unavailable")
    anonymous, _ = http_json(binding["port"], "/v1/models", None, deadline=deadline)
    code, models = http_json(binding["port"], "/v1/models", key, deadline=deadline)
    if arm == "strata":
        model = probe.read_json(binding["profile"])["strata"]["model_name"]
    else:
        model = "qwen3.8-27b" if binding["lane"] == "rtx4090-native" else "q38-ninfer"
    rows = models.get("data") if isinstance(models, dict) else None
    if not (anonymous == 401 and code == 200 and isinstance(rows, list) and len(rows) == 1
            and isinstance(rows[0], dict) and rows[0].get("id") == model):
        raise HostError("authenticated model readiness not established")
    if arm == "ninfer":
        code, live = http_json(binding["port"], "/v1/ninfer/status", key, deadline=deadline)
        if code != 200 or not isinstance(live, dict) or live.get("status") != "ok":
            raise HostError("authenticated NInfer status unavailable")
        return live
    return models


def native_capture(config, controller, live):
    if not probe.controller_ready(controller, "ninfer", config):
        raise HostError("native controller does not report ready")
    identity = live.get("identity", {})
    if identity.get("source_dirty") is not False:
        raise HostError("clean native served identity required")
    normalized = {"release_id": controller["release_id"], "endpoint_state": "ready",
                  **{field: identity.get(wire) for field, wire in HASH_FIELDS.items()}}
    from omp_strata.common import is_sha256
    if not normalized["release_id"] or not all(is_sha256(normalized[field]) for field in HASH_FIELDS):
        raise HostError("native served identity is incomplete")
    return normalized


def capture_ninfer(config, *, deadline, destination):
    controller = probe.controller_status(config, "ninfer", deadline=deadline)
    live = endpoint_status(config, "ninfer", deadline=deadline)
    probe.write_private(destination, {"controller": controller, "authenticated_status": live}, exclusive=True)
    if config["ninfer"]["lane"] == "rtx5090-docker-local":
        if not probe.controller_ready(controller, "ninfer", config):
            raise HostError("Docker controller does not report ready")
        return controller
    status = native_capture(config, controller, live)
    probe.write_private(Path(config["comparison_root"]) / "state" / "ninfer-status.json", status)
    return status


def prepare(config):
    from omp_strata.common import canonical_json, sha256_bytes, sha256_file
    from omp_strata.comparison import load_bindings, new_plan, validate_plan, verify_omp_binary
    from omp_strata.comparison_ompcfg import NInferArm
    from omp_strata.layout import Layout, host_platform
    from omp_strata.lifecycle import verify_install_fast
    from omp_strata.profile import load
    root = Path(config["comparison_root"])
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    deadline = time.monotonic() + 180
    probe.private_directory(root, deadline=deadline)
    state = root / "state"
    state.mkdir(mode=0o700)
    # Preserve inputs before any external inspection; a partial prepare is retained.
    probe.write_private(state / "host-config.json", config, exclusive=True)
    binding = config["strata"]
    profile = load(Path(binding["profile"]))
    installed = verify_install_fast(Layout(Path(binding["root"]), profile))
    manifest = probe.read_json(binding["manifest"])
    runtime_hash = sha256_bytes(canonical_json(installed["identity"]))
    if (installed["runtime_identity_sha256"] != runtime_hash
            or manifest["install"]["runtime_identity_sha256"] != runtime_hash
            or manifest["profile"]["fingerprint"] != profile.fingerprint):
        raise HostError("Strata installed and release identities differ")
    platform = host_platform()
    pin = profile.omp_artifact(platform)
    status = capture_ninfer(config, deadline=deadline, destination=state / "prepare-ninfer-capture.json")
    native = config["ninfer"]
    docker = native["lane"] == "rtx5090-docker-local"
    facts = probe.collect_windows(config, deadline=deadline)
    gpu = probe.collect_gpu(config, deadline=deadline)
    owners, _ = probe.classify_owners(gpu["processes"], facts["processes"], config, status if docker else None)
    if owners != [config["initial_owner"]]:
        raise HostError("observed initial GPU owner differs from the declared owner")
    if not all(facts["private_keys"].get(config[arm]["key_file"]) for arm in ARMS):
        raise HostError("installed engine key ACL is not private")
    host = {"label": config["host"]["label"], "os": "windows", "os_build": facts["os_build"],
            "gpu_model": gpu["name"], "vram_mib": gpu["total_mib"], "driver": gpu["driver"],
            "power_policy": probe.power_policy(facts, gpu),
            "clock_policy": gpu["clock_policy"], **{name: config["host"][name] for name in
                ("min_ram_gib", "min_available_ram_gib", "min_commit_headroom_gib", "min_disk_gib")}}
    for name in ("ram_gib", "available_ram_gib", "commit_headroom_gib", "disk_gib"):
        if facts[name] < host["min_" + name]:
            raise HostError("host below predeclared floor")
    identities = {"omp": {"platform": platform, "version": profile.data["omp"]["version"],
                           "bytes": pin["bytes"], "sha256": pin["sha256"]},
        "strata": {"profile_id": profile.id, "profile_fingerprint": profile.fingerprint,
                   "release_manifest_sha256": sha256_file(Path(binding["manifest"])),
                   "runtime_identity_sha256": runtime_hash,
                   "model_id": profile.data["strata"]["model_name"],
                   "model_identity_sha256": sha256_bytes(canonical_json(profile.data["model"])),
                   "quantization": profile.data["model"]["quantization"],
                   "api": "openai-completions", "provider": "strata-local"},
        "ninfer": {"lane": native["lane"], "release_id": status["release_id"],
                   "manifest_sha256": sha256_file(Path(native["manifest"])),
                   **{name: status[name] for name in HASH_FIELDS}, "quantization": native["quantization"],
                   "api": "openai-responses", "provider": "ninfer-beta" if docker else
                   "ninfer-native-" + native["lane"].split("-")[0].removeprefix("rtx"),
                   "model_id": "qwen3.8-27b" if native["lane"] == "rtx4090-native" else "q38-ninfer"},
        "host": host}
    if docker:
        identities["ninfer"]["image_digest"] = status["image_digest"]
    native_fields = ("root", "key_file", "port", "manifest", "docker_identity_probe_argv") if docker else (
        "root", "key_file", "port", "manifest", "controller", "state_root")
    bindings = {"schema_version": 1, "comparison_id": config["comparison_id"], "comparison_root": str(root),
                "omp_binary": config["omp_binary"], "execution_boundary": "evaluation",
                "strata": {name: binding[name] for name in ("root", "key_file", "port", "profile", "manifest")},
                "ninfer": {name: native[name] for name in native_fields},
                "host_probe_argv": [config["python"], str(Path(probe.__file__).resolve()), "--config",
                                    str(state / "host-config.json")]}
    if not docker:
        bindings["ninfer"]["status_file"] = str(state / "ninfer-status.json")
    plan = new_plan(identities, config["comparison_id"])
    if validate_plan(plan, finalized=False):
        raise HostError("prepared public identities do not match the comparison contract")
    verify_omp_binary(Path(config["omp_binary"]), plan)
    probe.write_private(root / "identities.json", identities, exclusive=True)
    probe.write_private(state / "bindings.json", bindings, exclusive=True)
    load_bindings(state / "bindings.json", plan)
    NInferArm(plan, bindings).preflight()
    probe.write_private(root / "comparison-draft.json", plan, exclusive=True)


def reserve_step(root, step):
    reservation = {"step": step, "nonce": uuid.uuid4().hex, "reserved_ns": time.time_ns()}
    try:
        probe.write_private(root / "state" / (step + ".reserved.json"), reservation, exclusive=True)
    except FileExistsError:
        raise HostError("reserved steps can never be rerun") from None
    return reservation


def release_gpu(config, *, deadline):
    while True:
        gpu = probe.collect_gpu(config, deadline=deadline)
        graphics = config["host"].get("display_attached", False)
        owners = [p for p in gpu["processes"] if not graphics or p["type"] not in {"G", "C+G"}]
        if not owners and gpu["used_mib"] < config.get("gpu_release_mib", 1500):
            return
        time.sleep(min(1, probe.remaining(deadline)))


def lifecycle(config, arm, action, *, deadline, log):
    # run_argv uses no shell, so neither executable paths nor arguments are code. A stop/start command may use the whole
    # switch budget (the caller's deadline): stopping a container lane includes waiting for its VM to return RAM.
    output = probe.run_argv(config[arm][action + "_argv"], deadline=deadline, cap=300)
    probe.write_private(log, {"action": action, "output": output}, exclusive=True)


def transition(config, arm, step, reservation, plan, bindings):
    from omp_strata.comparison import validate_host_observation
    from omp_strata.comparison_ompcfg import NInferArm, StrataArm
    root = Path(config["comparison_root"])
    state = root / "state"
    prior = state / "current-switch.json"
    previous = probe.read_json(prior)["arm"] if prior.exists() else config["initial_owner"]
    stop_started = time.monotonic_ns()
    deadline = time.monotonic() + 300
    started = False
    try:
        if previous != "none":
            lifecycle(config, previous, "stop", deadline=deadline, log=state / (step + "-stop.json"))
        release_gpu(config, deadline=deadline)
        startup_started = time.monotonic_ns()
        started = True  # Even a start command that times out can have launched a child.
        lifecycle(config, arm, "start", deadline=deadline, log=state / (step + "-start.json"))
        while True:
            try:
                endpoint_status(config, arm, deadline=deadline)
                status = probe.controller_status(config, arm, deadline=deadline)
                if not probe.controller_ready(status, arm, config):
                    raise HostError("controller is not ready")
                break
            except HostError:
                time.sleep(min(1, probe.remaining(deadline)))
        ready = time.monotonic_ns()
        if ready - stop_started > 300_000_000_000:
            raise HostError("switch timeout")
        if arm == "ninfer":
            capture_ninfer(config, deadline=deadline, destination=state / (step + "-ninfer-capture.json"))
        adapter = StrataArm(plan, bindings) if arm == "strata" else NInferArm(plan, bindings)
        adapter.preflight()
        facts = probe.collect_windows(config, deadline=deadline)
        gpu = probe.collect_gpu(config, deadline=deadline)
        docker = status if arm == "ninfer" and config["ninfer"]["lane"] == "rtx5090-docker-local" else None
        owners, processes = probe.classify_owners(gpu["processes"], facts["processes"], config, docker)
        if owners != [arm]:
            raise HostError("target does not exclusively own the GPU")
        record = {"comparison_id": config["comparison_id"], "step": step, "arm": arm,
                  "reservation_nonce": reservation["nonce"], "boot_id": facts["boot_id"],
                  "stop_started_ns": stop_started, "startup_started_ns": startup_started, "ready_ns": ready,
                  "ready_processes": processes}
        if docker:
            record["docker_generation"] = [docker["container_id"], docker["started_at"]]
        startup, switch = probe.switch_measurements(record, arm=arm, comparison_id=config["comparison_id"],
                                                   boot_id=facts["boot_id"], processes=processes, docker=docker)
        record.update(startup_ms=startup, switch_ms=switch)
        probe.write_private(state / (step + "-switch.json"), record, exclusive=True)
        probe.write_private(prior, record)
        observation = probe.observe(config, arm)
        probe.write_private(state / (step + "-observation.json"), observation, exclusive=True)
        if validate_host_observation(observation, plan, arm):
            raise HostError("fresh host safety observation refused dispatch")
    except BaseException:
        cleanup = {"stop_attempted": started, "gpu_released": False}
        if started:
            cleanup_deadline = time.monotonic() + 60
            try:
                lifecycle(config, arm, "stop", deadline=cleanup_deadline,
                          log=state / (step + "-cleanup-stop.json"))
                release_gpu(config, deadline=cleanup_deadline)
                cleanup["gpu_released"] = True
            except (HostError, OSError, ValueError):
                pass
        probe.write_private(state / (step + "-transition-failure.json"), cleanup, exclusive=True)
        raise


def compare(config, args):
    argv = [config["python"], str(ROOT / "scripts" / "compare_g25.py"), *args]
    return subprocess.run(argv, stdin=subprocess.DEVNULL, shell=False, check=False,
                          cwd=config["comparison_root"]).returncode


def run_step(config, step):
    from omp_strata.comparison import load_bindings, load_plan
    root = Path(config["comparison_root"])
    state = root / "state"
    steps = ["pilot-strata", "pilot-ninfer", *[f"window-{i}" for i in range(1, 7)]]
    index = steps.index(step)
    if index:
        previous = state / (steps[index - 1] + ".finished.json")
        if not previous.exists() or probe.read_json(previous).get("returncode") != 0:
            raise HostError("a successful finalized predecessor is required")
    reservation = reserve_step(root, step)
    pilot = step.startswith("pilot-")
    arm = step.removeprefix("pilot-") if pilot else WINDOW_ARMS[int(step.removeprefix("window-")) - 1]
    plan_path = root / ("comparison-draft.json" if pilot else "comparison-plan.json")
    plan = load_plan(plan_path, finalized=not pilot, check_runtime=True)
    bindings_path = state / "bindings.json"
    bindings = load_bindings(bindings_path, plan)
    transition(config, arm, step, reservation, plan, bindings)
    args = ["pilot" if pilot else "run-window", "--plan", str(plan_path), "--bindings", str(bindings_path)]
    args += ["--arm", arm] if pilot else ["--window", step.removeprefix("window-")]
    code = compare(config, args)  # Exactly once; ordinary failures are not retried.
    probe.write_private(state / (step + ".finished.json"), {"returncode": code}, exclusive=True)
    return code


def run(config, *, step=None, sequence=None):
    root = Path(config["comparison_root"])
    state = root / "state"
    if probe.read_json(state / "host-config.json") != config:
        raise HostError("prepared private configuration changed; use a new comparison root")
    lock = state / "active-driver.json"
    try:
        probe.write_private(lock, {"pid": os.getpid(), "nonce": uuid.uuid4().hex}, exclusive=True)
    except FileExistsError:
        raise HostError("another or interrupted driver owns this comparison") from None
    completed = False
    try:
        if step:
            result = run_step(config, step)
        else:
            result = 0
            for name in ("pilot-strata", "pilot-ninfer"):
                result = run_step(config, name)
                if result:
                    break
            if not result:
                result = compare(config, ["init-plan", "--identities", str(root / "comparison-draft.json"),
                    "--output", str(root / "comparison-plan.json"), "--finalize", "--pilot-root", str(root)])
            if not result:
                result = compare(config, ["validate", "--plan", str(root / "comparison-plan.json"),
                                          "--bindings", str(state / "bindings.json")])
            if not result:
                for number in range(1, 7):
                    result = run_step(config, f"window-{number}")
                    if result:
                        break
        completed = True
        return result
    finally:
        if completed:
            lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        command = sub.add_parser(name)
        command.add_argument("--config", type=Path, required=True)
        if name == "run":
            action = command.add_mutually_exclusive_group(required=True)
            action.add_argument("--step", choices=["pilot-strata", "pilot-ninfer", *[f"window-{i}" for i in range(1, 7)]])
            action.add_argument("--sequence", choices=["all"])
    args = parser.parse_args(argv)
    try:
        config = config_load(args.config)
        if args.command == "prepare":
            prepare(config)
            return 0
        return run(config, step=args.step, sequence=args.sequence)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        # The operator needs the reason; this stderr goes to the private host log, never into published evidence.
        print(f"G25 host prerequisite or transition failed ({type(exc).__name__}: {exc}); private evidence and "
              "reservations retained", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("G25 host driver interrupted; reservation retained", file=sys.stderr)
        return 130


if __name__ == "__main__":
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
