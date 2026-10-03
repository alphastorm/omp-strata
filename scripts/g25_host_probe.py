#!/usr/bin/env python3
"""Fresh Windows G25 observation; only private evidence files are written.

Minimal inspection config: host.label, host.display_attached, comparison_root.
A dispatch also needs both arm roots/key_files/ports, status_argv for Strata and
native NInfer, and the driver's current switch record. Docker additionally needs
explicit gpu_process_names and docker_identity_probe_argv; that fresh probe must
include network_connections (or supply docker_network_probe_argv). Connections
use pid/local_address/local_port/remote_address/remote_port/state fields.
Missing observations are null with reasons, never synthetic safety passes.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import ipaddress
import json
import math
import os
import subprocess

import time
import uuid
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree


class HostError(ValueError):
    """A private host prerequisite is absent or unsafe."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise HostError("JSON object required")
    return value


def remaining(deadline, cap=60):
    value = min(cap, deadline - time.monotonic())
    if value <= 0:
        raise HostError("observation deadline expired")
    return value


def run_argv(argv, *, deadline, env=None):
    if not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v for v in argv):
        raise HostError("nonempty argv array required")
    if Path(argv[0]).suffix.lower() in {".bat", ".cmd"}:
        raise HostError("batch files require shell parsing and are not supported")
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", env=env,
                                timeout=remaining(deadline), check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        raise HostError("host command failed or exceeded its deadline") from None
    if result.returncode or len(result.stdout) > 4 * 1024 * 1024:
        raise HostError("host command failed or exceeded its output boundary")
    return result.stdout.lstrip("\ufeff").strip()


def powershell(script, *, deadline, values=None):
    env = dict(os.environ)
    env.update(values or {})
    source = ("$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; "
              "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); " + script)
    return run_argv(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-EncodedCommand", base64.b64encode(source.encode("utf-16le")).decode()],
                    env=env, deadline=deadline)


def private_directory(path, *, deadline):
    path = Path(path)
    if path.is_symlink():
        raise HostError("private directory cannot be a link")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)
        return
    powershell("$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User; "
               "$acl=[Security.AccessControl.DirectorySecurity]::new(); "
               "$acl.SetOwner($sid); $acl.SetAccessRuleProtection($true,$false); "
               "$rule=[Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl',"
               "'ContainerInherit,ObjectInherit','None','Allow'); $acl.AddAccessRule($rule); "
               "Set-Acl -LiteralPath $env:G25_PRIVATE_PATH -AclObject $acl",
               deadline=deadline, values={"G25_PRIVATE_PATH": str(path.resolve())})


def write_private(path, value, *, exclusive=False):
    path = Path(path)
    payload = canonical(value) + b"\n"
    if exclusive:
        with path.open("xb") as stream:
            if os.name != "nt":
                os.chmod(path, 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        return
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".pending")
    write_private(temporary, value, exclusive=True)
    os.replace(temporary, path)


INVENTORY_PS = r"""
$os=Get-CimInstance Win32_OperatingSystem
$cs=Get-CimInstance Win32_ComputerSystem
$drive=Get-PSDrive -Name $env:G25_DISK_DRIVE -PSProvider FileSystem
$processes=@(Get-CimInstance Win32_Process | ForEach-Object {
    @{pid=[int]$_.ProcessId; parent_pid=[int]$_.ParentProcessId; name=$_.Name;
      executable=$_.ExecutablePath; command_line=$_.CommandLine;
      created=if($_.CreationDate){$_.CreationDate.ToUniversalTime().ToString('o')}else{$null}}
})
$network=@(Get-NetTCPConnection | ForEach-Object {
    @{pid=[int]$_.OwningProcess; local_address=$_.LocalAddress; local_port=[int]$_.LocalPort;
      remote_address=$_.RemoteAddress; remote_port=[int]$_.RemotePort; state=[string]$_.State}
})
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$known={param($t) ([Security.Principal.SecurityIdentifier]::new([Security.Principal.WellKnownSidType]::$t,$null)).Value}
$allowed=@($sid,(& $known 'LocalSystemSid'),(& $known 'BuiltinAdministratorsSid'))
$private=@{}
foreach($path in @($env:G25_KEY_PATHS | ConvertFrom-Json)) {
    if(-not $path){continue}
    $acl=Get-Acl -LiteralPath $path
    $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    $ok=$rules.Count -gt 0
    foreach($rule in $rules){
        if($rule.AccessControlType -eq 'Allow' -and
           $allowed -notcontains $rule.IdentityReference.Value){$ok=$false}
    }
    $private[$path]=$ok
}
$power=(& powercfg.exe /getactivescheme | Out-String).Trim()
if($LASTEXITCODE -ne 0){throw 'power policy unavailable'}
@{os_build=([string]$os.Version+' build '+[string]$os.BuildNumber);
  boot_id=$os.LastBootUpTime.ToUniversalTime().ToString('o');
  ram_gib=[double]$cs.TotalPhysicalMemory/1GB;
  available_ram_gib=[double]$os.FreePhysicalMemory/1MB;
  commit_headroom_gib=[double]$os.FreeVirtualMemory/1MB;
  disk_gib=[double]$drive.Free/1GB; power=$power;
  processes=$processes; connections=$network; private_keys=$private} | ConvertTo-Json -Depth 6 -Compress
"""


def collect_windows(config, *, deadline):
    if os.name != "nt":
        raise HostError("the real host probe requires Windows")
    disk = Path(config["comparison_root"]).resolve().drive.rstrip(":")
    paths = [config[arm]["key_file"] for arm in ("strata", "ninfer")
             if config.get(arm, {}).get("key_file")]
    return json.loads(powershell(INVENTORY_PS, deadline=deadline,
                                values={"G25_DISK_DRIVE": disk, "G25_KEY_PATHS": json.dumps(paths)}))


def collect_gpu(config, *, deadline):
    prefix = [config.get("nvidia_smi", "nvidia-smi.exe"), "-i", str(config.get("gpu_index", 0))]
    rows = list(csv.reader(run_argv(prefix + ["--query-gpu=name,memory.total,memory.used,driver_version",
                                             "--format=csv,noheader,nounits"], deadline=deadline).splitlines()))
    if len(rows) != 1 or len(rows[0]) != 4:
        raise HostError("one selected GPU observation required")
    name, total, used, driver = [value.strip() for value in rows[0]]
    xml = ElementTree.fromstring(run_argv(prefix + ["-q", "-x"], deadline=deadline))
    gpu = xml.find("gpu")
    if gpu is None:
        raise HostError("GPU process observation unavailable")
    processes = [{"pid": int(p.findtext("pid")), "type": p.findtext("type") or "unknown",
                  "name": p.findtext("process_name") or ""} for p in gpu.findall("processes/process_info")]
    # Current frequencies/pstate are load-dependent, not a stable clock policy.
    clocks = {name: {node.tag: (node.text or "").strip() for node in gpu.findall(name + "/*")}
              for name in ("applications_clocks", "default_applications_clocks")}
    if not all(clocks.values()):
        raise HostError("GPU application clock policy unavailable")
    power = gpu.findtext("gpu_power_readings/current_power_limit") or gpu.findtext("power_readings/power_limit")
    return {"name": name, "total_mib": int(float(total)), "used_mib": float(used), "driver": driver,
            "clock_policy": canonical(clocks).decode(), "power_limit": power, "processes": processes}


def _inside(executable, root):
    if not executable or not root:
        return False
    try:
        return PureWindowsPath(executable).is_relative_to(PureWindowsPath(root))
    except ValueError:
        return False


def process_arm(process, config, docker=None):
    executable = process.get("executable")
    for arm in ("strata", "ninfer"):
        if _inside(executable, config.get(arm, {}).get("root")):
            return arm
    ninfer = config.get("ninfer", {})
    declared = {name.casefold() for name in ninfer.get("gpu_process_names", [])}
    if (docker and docker.get("running") is True and docker.get("endpoint_state") == "ready"
            and process.get("name", "").casefold() in declared):
        return "ninfer"
    return None


def classify_owners(gpu_processes, processes, config, docker=None):
    by_pid = {p["pid"]: p for p in processes}
    owners, identities = set(), []
    for gpu in gpu_processes:
        if config.get("host", {}).get("display_attached") and gpu["type"] in {"G", "C+G"}:
            continue
        process = by_pid.get(gpu["pid"], {"pid": gpu["pid"], "name": gpu.get("name", "")})
        arm = process_arm(process, config, docker)
        # A graphics-only process on a declared headless GPU is not an engine.
        if gpu["type"] in {"G", "C+G"}:
            arm = None
        owners.add(arm or "unrelated")
        identities.append({"pid": gpu["pid"], "created": process.get("created"), "arm": arm})
    return sorted(owners), sorted(identities, key=lambda item: item["pid"])


def network_snapshot(facts, config, docker=None):
    processes = facts["processes"]
    owned = {p["pid"] for p in processes if process_arm(p, config, docker)
             or (config.get("omp_binary") and p.get("executable", "")
                 and PureWindowsPath(p["executable"]) == PureWindowsPath(config["omp_binary"]))}
    # Include tool subprocesses, not just the client executable itself.
    while True:
        expanded = owned | {p["pid"] for p in processes if p["parent_pid"] in owned}
        if expanded == owned:
            break
        owned = expanded
    connections = [row for row in facts["connections"] if row["pid"] in owned]
    if docker is not None:
        extra = docker.get("network_connections")
        if not isinstance(extra, list):
            raise HostError("Docker engine network observation unavailable")
        connections += extra
    non_loopback = []
    for row in connections:
        remote = ipaddress.ip_address(row["remote_address"].split("%", 1)[0])
        if remote.version == 6 and remote.ipv4_mapped:
            remote = remote.ipv4_mapped
        if row["state"].casefold() not in {"listen", "bound", "closed"} and not (remote.is_loopback or remote.is_unspecified):
            non_loopback.append({key: row[key] for key in
                                 ("pid", "local_address", "local_port", "remote_address", "remote_port", "state")})
    return {"boot_id": facts["boot_id"], "observed_ns": time.time_ns(),
            "connections": sorted(non_loopback, key=lambda row: canonical(row)), "owned_pids": sorted(owned)}


def switch_measurements(record, *, arm, comparison_id, boot_id, processes, docker=None):
    if (record.get("arm") != arm or record.get("comparison_id") != comparison_id
            or record.get("boot_id") != boot_id or record.get("ready_processes") != processes
            or not processes or any(p.get("created") is None or p.get("arm") != arm for p in processes)):
        raise HostError("current cold process identity not established")
    stamps = [record.get(name) for name in ("stop_started_ns", "startup_started_ns", "ready_ns")]
    if any(type(value) is not int or value < 0 for value in stamps) or stamps != sorted(stamps):
        raise HostError("invalid switch measurement ordering")
    if stamps[-1] > time.monotonic_ns():
        raise HostError("switch monotonic epoch changed")
    startup, switch = (stamps[2] - stamps[1]) / 1e6, (stamps[2] - stamps[0]) / 1e6
    if switch > 300000 or not math.isfinite(switch):
        raise HostError("switch exceeded the frozen boundary")
    if docker is not None and arm == "ninfer":
        if record.get("docker_generation") != [docker.get("container_id"), docker.get("started_at")]:
            raise HostError("Docker process generation changed")
    return startup, switch


def controller_status(config, arm, *, deadline):
    binding = config.get(arm, {})
    argv = binding.get("docker_identity_probe_argv") if binding.get("lane") == "rtx5090-docker-local" else binding.get("status_argv")
    if not argv:
        raise HostError("read-only controller status argv required")
    value = json.loads(run_argv(argv, deadline=deadline))
    if not isinstance(value, dict):
        raise HostError("controller JSON object required")
    return value


def controller_ready(value, arm, config):
    if arm == "strata":
        return value.get("state") == "healthy"
    if config.get("ninfer", {}).get("lane") == "rtx5090-docker-local":
        return value.get("running") is True and value.get("endpoint_state") == "ready"
    return (value.get("endpoint_state") == "ready" and value.get("process_state") == "running"
            and value.get("gpu_owner", {}).get("status") == "ok")


def empty_observation(label):
    return {"host": {"label": label, **{name: None for name in
             ("os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy")}},
            **{name: None for name in ("ram_gib", "available_ram_gib", "commit_headroom_gib", "disk_gib",
               "startup_ms", "switch_ms", "network_observation_sha256", "route_escape", "credential_exposure")},
            "gpu_owners": [], "process_condition": "unknown", "file_cache_condition": "unknown",
            "controller_ok": False, "missing_reasons": {"file_cache_condition": "filesystem cache not independently measured"}}


def observe(config, arm, *, deadline=None):
    deadline = deadline or time.monotonic() + 55
    observation = empty_observation(config.get("host", {}).get("label"))
    reasons = observation["missing_reasons"]
    try:
        facts = collect_windows(config, deadline=deadline)
        gpu = collect_gpu(config, deadline=deadline)
        observation["host"].update(os="windows", os_build=facts["os_build"], gpu_model=gpu["name"],
                                   vram_mib=gpu["total_mib"], driver=gpu["driver"],
                                   power_policy=facts["power"] + "; GPU limit " + str(gpu["power_limit"]),
                                   clock_policy=gpu["clock_policy"])
        for field in ("ram_gib", "available_ram_gib", "commit_headroom_gib", "disk_gib"):
            observation[field] = facts[field]
        docker = None
        status = None
        try:
            status = controller_status(config, arm, deadline=deadline)
            observation["controller_ok"] = controller_ready(status, arm, config)
        except (HostError, ValueError):
            reasons["controller_ok"] = "controller observation unavailable"
        if config.get("ninfer", {}).get("lane") == "rtx5090-docker-local" and arm == "ninfer":
            docker = status or {}
            network_argv = config["ninfer"].get("docker_network_probe_argv")
            if network_argv:
                docker["network_connections"] = json.loads(run_argv(network_argv, deadline=deadline))["connections"]
        owners, identities = classify_owners(gpu["processes"], facts["processes"], config, docker)
        observation["gpu_owners"] = owners
        root = Path(config["comparison_root"])
        try:
            record = read_json(root / "state" / "current-switch.json")
            if (root / "state" / (record["step"] + ".finished.json")).exists() or (
                    root / "state" / (record["step"] + "-transition-failure.json")).exists():
                raise HostError("switch record is not for an active window")
            reservation = read_json(root / "state" / (record["step"] + ".reserved.json"))
            if reservation["nonce"] != record["reservation_nonce"]:
                raise HostError("switch reservation mismatch")
            startup, switch = switch_measurements(record, arm=arm, comparison_id=config.get("comparison_id"),
                                                  boot_id=facts["boot_id"], processes=identities, docker=docker)
            observation.update(startup_ms=startup, switch_ms=switch, process_condition="process-cold")
        except (OSError, KeyError, ValueError):
            for field in ("startup_ms", "switch_ms", "process_condition"):
                reasons[field] = "no valid current-window cold-start record"
        snapshot = network_snapshot(facts, config, docker)
        directory = root / "network-observations"
        private_directory(directory, deadline=deadline)
        path = directory / (uuid.uuid4().hex + ".json")
        write_private(path, snapshot, exclusive=True)
        observation["network_observation_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        observation["route_escape"] = bool(snapshot["connections"])
        keys = [config.get(owner, {}).get("key_file") for owner in ("strata", "ninfer")]
        if all(keys):
            secrets = [Path(key).read_text(encoding="ascii").strip() for key in keys]
            if not all(32 <= len(key) <= 512 for key in secrets):
                raise HostError("invalid private key files")
            command_lines = [p.get("command_line") for p in facts["processes"]
                             if p["pid"] in snapshot["owned_pids"]]
            if any(line is None for line in command_lines):
                reasons["credential_exposure"] = "owned process command line unavailable"
            else:
                observation["credential_exposure"] = (not all(facts["private_keys"].get(key) for key in keys)
                    or any(key in line for key in secrets for line in command_lines))
        else:
            reasons["credential_exposure"] = "both private key paths required for exposure checks"
    except (OSError, ValueError, KeyError, TypeError, ElementTree.ParseError):
        reasons["observation"] = "mandatory host observation unavailable"
    for name, value in observation.items():
        if value is None and name not in reasons:
            reasons[name] = "not observed"
    return observation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("strata", "ninfer"), required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = read_json(args.config)
        observation = observe(config, args.arm)
    except (OSError, ValueError):
        observation = empty_observation(None)
        observation["missing_reasons"]["observation"] = "private config unavailable"
    print(canonical(observation).decode())
    return 0 if "observation" not in observation["missing_reasons"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
