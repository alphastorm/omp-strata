"""Minimal lifecycle for one stock Strata server: keygen, doctor, start, serve (wrapper), status, stop.

No daemon of our own: `start` launches a detached `serve` wrapper that reads the private key file, starts stock
`serve/server.py` on loopback with the key in its environment, and records owned process identities in
`<root>/state/run.json`. `stop` only ever terminates processes whose PID, creation time and executable still match
that record. A server already on the port is never adopted.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree

from . import procs
from .common import (atomic_write_bytes, atomic_write_json, canonical_json, engine_labels, read_json,
                     sha256_bytes, sha256_file, utc_now, verified_ok)
from .install import InstallError, SECRET_ENV_MARKERS, verify_generated
from .layout import Layout, host_platform

Log = Callable[[str], None]
WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000
GPU_IDLE_MIB = 1500


class LifecycleError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ lock
class FileLock:
    """Exclusive, non-blocking lock for install/start/stop; released on exit or process death."""

    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if WINDOWS:
                import msvcrt
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]  # Windows-only
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.fd)
            self.fd = None
            raise LifecycleError("another lifecycle command holds the integration lock") from None
        return self

    def __exit__(self, *exc: object) -> None:
        if self.fd is not None:
            try:
                if WINDOWS:
                    import msvcrt
                    os.lseek(self.fd, 0, os.SEEK_SET)
                    msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]  # Windows-only
            finally:
                os.close(self.fd)
                self.fd = None


# ------------------------------------------------------------------------------------------------ key
def keygen(layout: Layout) -> Path:
    """Create the private API key file once (32 random bytes, URL-safe); never prints the key."""
    path = layout.key_file
    if path.exists():
        read_key(layout)
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(path, (secrets.token_urlsafe(32) + "\n").encode("ascii"))
    restrict_to_user(path)
    return path


def restrict_to_user(path: Path) -> None:
    if WINDOWS:
        user = os.environ.get("USERNAME")
        if not user:
            raise LifecycleError("cannot determine the Windows user to restrict the key file to")
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"], check=True,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        path.chmod(0o600)


def read_key(layout: Layout) -> str:
    try:
        key = layout.key_file.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        raise LifecycleError("no API key file; run `keygen` first") from None
    if len(key) < 32:
        raise LifecycleError("the API key file is blank or too short; refusing to start an unauthenticated server")
    return key


# ------------------------------------------------------------------------------------------------ http
def http_json(url: str, *, key: str | None = None, timeout: float = 5.0) -> tuple[int, object]:
    headers = {"User-Agent": "omp-strata-lifecycle"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        body, status = exc.read(), exc.code
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, None
    try:
        return status, json.loads(body)
    except ValueError:
        return status, None


def base_url(layout: Layout) -> str:
    srv = layout.profile.data["server"]
    return f"http://{srv['listen_host']}:{srv['port']}"


# ------------------------------------------------------------------------------------------------ host facts
def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        if s.connect_ex((host, port)) == 0:
            return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if WINDOWS:
            s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", 0xFFFFFFFB), 1)
        try:
            s.bind((host, port))
        except OSError:
            return True
    return False


def parse_gpu_csv(text: str, fields: tuple[str, ...]) -> list[dict[str, str]]:
    """Strict nvidia-smi CSV rows; callers decide which unsupported fields may remain missing."""
    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error as exc:
        raise ValueError("malformed nvidia-smi CSV") from exc
    if not rows or any(len(row) != len(fields) for row in rows):
        raise ValueError("missing or malformed nvidia-smi CSV columns")
    return [dict(zip(fields, (value.strip() for value in row))) for row in rows]


def canonical_pci_bus_id(value: str) -> str:
    """Normalize NVIDIA's four/eight-digit domain and uppercase BDF to the profile form."""
    match = re.fullmatch(r"([0-9a-fA-F]{4}|[0-9a-fA-F]{8}):([0-9a-fA-F]{2}):([01][0-9a-fA-F])\.([0-7])", value)
    if not match:
        raise ValueError("invalid PCI bus ID")
    domain, bus, device, function = match.groups()
    return f"{domain.zfill(8)}:{bus}:{device}.{function}".lower()


def gpu_processes(xml_text: str, *, strict: bool = True) -> list[dict]:
    """pid and type of every process `nvidia-smi -q -x` lists. Type "C" is a compute-only process (another runtime);
    "G" and "C+G" are graphics clients: under WDDM every desktop process drawing on a display-attached GPU."""
    root = ElementTree.fromstring(xml_text)
    if not strict:
        # The scalar lane keeps its established observation policy; multi-card qualification is strict.
        return [{"pid": int(pid), "type": (p.findtext("type") or "").strip() or "C"}
                for p in root.iter("process_info") if (pid := (p.findtext("pid") or "").strip()).isdigit()]
    cards = root.findall("gpu")
    if root.tag != "nvidia_smi_log" or len(cards) != 1:
        raise ValueError("expected one indexed GPU in process XML")
    listing = cards[0].find("processes")
    if listing is None or (listing.text or "").strip():
        raise ValueError("GPU process list unavailable")
    out, seen = [], set()
    for p in listing:
        if p.tag != "process_info":
            raise ValueError("unknown GPU process record")
        pid = (p.findtext("pid") or "").strip()
        if not pid.isdigit() or int(pid) <= 0 or int(pid) in seen:
            raise ValueError("invalid or duplicate GPU process PID")
        seen.add(int(pid))
        out.append({"pid": int(pid), "type": (p.findtext("type") or "").strip() or "unknown"})
    return out


def gpu_facts(index: int, *, multi_gpu: bool = False) -> dict:
    """Keep scalar probes unchanged; the multi-card lane explicitly requests strict indexed identity facts."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, **({"reason": "nvidia-smi unavailable"} if multi_gpu else {})}
    if not multi_gpu:
        q = subprocess.run([exe, "-i", str(index), "--query-gpu=name,memory.total,memory.used,driver_version",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           timeout=30)
        listing = subprocess.run([exe, "-i", str(index), "-q", "-x"], capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, timeout=60)
        if q.returncode != 0 or not q.stdout.strip():
            return {"available": False}
        name, total, used, driver = [x.strip() for x in q.stdout.strip().splitlines()[0].split(",")]
        try:
            processes = gpu_processes(listing.stdout, strict=False)
        except ElementTree.ParseError:
            processes = [{"pid": -1, "type": "unreadable"}]
        compute = [p for p in processes if p["type"] not in ("G", "C+G")]
        return {"available": True, "name": name, "memory_total_mib": int(float(total)),
                "memory_used_mib": int(float(used)), "driver": driver, "compute_apps": len(compute),
                "graphics_apps": len(processes) - len(compute), "processes": processes}
    fields = ("index", "name", "pci.bus_id", "memory.total", "memory.used", "compute_cap", "driver_version", "display_active")
    try:
        q = subprocess.run([exe, "-i", str(index), "--query-gpu=" + ",".join(fields),
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=30)
        listing = subprocess.run([exe, "-i", str(index), "-q", "-x"], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, timeout=60)
        if q.returncode or listing.returncode:
            raise ValueError("nvidia-smi facts or process query failed")
        rows = parse_gpu_csv(q.stdout, fields)
        if len(rows) != 1:
            raise ValueError("expected one indexed GPU CSV row")
        row = rows[0]
        if not row["index"].isdigit() or int(row["index"]) != index:
            raise ValueError("GPU index mismatch")
        if not row["name"] or not re.fullmatch(r"\d+(?:\.\d+)*", row["driver_version"]):
            raise ValueError("missing GPU name or driver")
        if not all(row[f].isdigit() for f in ("memory.total", "memory.used")):
            raise ValueError("GPU memory unavailable")
        total, used = int(row["memory.total"]), int(row["memory.used"])
        if total <= 0 or used > total or not re.fullmatch(r"[1-9]\d*\.\d", row["compute_cap"]):
            raise ValueError("invalid GPU capacity or architecture")
        display = {"Enabled": True, "Disabled": False}.get(row["display_active"])
        if display is None:
            raise ValueError("display-active observation unavailable")
        bus = canonical_pci_bus_id(row["pci.bus_id"])
        processes = gpu_processes(listing.stdout)
    except (OSError, subprocess.SubprocessError, ValueError, ElementTree.ParseError) as exc:
        return {"available": False, "reason": str(exc)}
    attached = None
    try:
        attachment = subprocess.run([exe, "-i", str(index), "--query-gpu=index,display_attached",
                                     "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=30)
        if attachment.returncode == 0:
            rows = parse_gpu_csv(attachment.stdout, ("index", "display_attached"))
            if len(rows) == 1 and rows[0]["index"].isdigit() and int(rows[0]["index"]) == index:
                attached = {"Yes": True, "No": False}.get(rows[0]["display_attached"])
    except (OSError, subprocess.SubprocessError, ValueError):
        pass  # Missing physical attachment is a qualification problem, never inferred from display_active.
    compute = [p for p in processes if p["type"] not in ("G", "C+G")]
    return {"available": True, "gpu_index": index, "name": row["name"], "memory_total_mib": total,
            "memory_used_mib": used, "driver": row["driver_version"], "compute_apps": len(compute),
            "arch": row["compute_cap"].replace(".", ""), "pci_bus_id": bus, "display_active": display,
            "display_attached": attached,
            "graphics_apps": len(processes) - len(compute), "processes": processes}


def gpu_busy(gpu: dict, display_attached: bool) -> str | None:
    """Why the GPU is not free for this integration, or None. Graphics clients are tolerated only on a GPU the profile
    declares display-attached (their VRAM still counts against GPU_IDLE_MIB); a compute process never is."""
    if not gpu.get("available"):
        return None
    if (gpu["memory_used_mib"] >= GPU_IDLE_MIB or gpu["compute_apps"]
            or (gpu["graphics_apps"] and not display_attached)):
        return (f"{gpu['memory_used_mib']} MiB used, {gpu['compute_apps']} compute process(es), "
                f"{gpu['graphics_apps']} graphics client(s)")
    return None


def card_observations(profile, *, owned_pids=None) -> list[dict]:
    """Profile-ordered facts and occupancy. None checks idle; a PID set checks an active owned engine.

    Ownership must come from an identity-verified server tree. WDDM per-process VRAM is not inferred by subtraction.
    """
    observations = []
    for card in profile.gpu_requirements:
        index = card["gpu_index"]
        gpu = gpu_facts(index, multi_gpu=True) if profile.multi_gpu else gpu_facts(index)
        problems = []
        row = {"gpu_index": index, "gpu_model": gpu.get("name"), "arch": gpu.get("arch"),
               "pci_bus_id": gpu.get("pci_bus_id"), "memory_total_mib": gpu.get("memory_total_mib"),
               "memory_used_mib": gpu.get("memory_used_mib"), "driver_version": gpu.get("driver"),
               "display_active": gpu.get("display_active"), "owned_count": None,
               "foreign_compute_count": None, "graphics_client_count": None, "problems": problems}
        observations.append(row)
        if not gpu.get("available"):
            problems.append("GPU facts unavailable: " + gpu.get("reason", "nvidia-smi unavailable"))
            continue
        for key, actual in (("gpu_index", gpu.get("gpu_index")), ("gpu_model", gpu.get("name")),
                            ("arch", gpu.get("arch")), ("pci_bus_id", gpu.get("pci_bus_id"))):
            if card[key] is not None and actual != card[key]:
                problems.append(f"{key} does not match profile")
        if gpu["memory_total_mib"] < card["min_gpu_vram_mib"]:
            problems.append("VRAM below profile floor")
        if int(gpu["driver"].split(".")[0]) < profile.data["host"]["min_driver_major"]:
            problems.append("driver below profile floor")
        if profile.multi_gpu:
            if type(gpu.get("display_attached")) is not bool:
                problems.append("physical display_attached observation unavailable")
            elif gpu["display_attached"] != card["display_attached"]:
                problems.append("physical display_attached does not match profile")
        if gpu.get("display_active") and not card["display_attached"]:
            problems.append("display active on a non-display card")
        owned = owned_pids if owned_pids is not None else set()
        foreign = [p for p in gpu["processes"] if p["pid"] not in owned]
        graphics = sum(p["type"] in ("G", "C+G") for p in foreign)
        row.update(owned_count=sum(p["pid"] in owned for p in gpu["processes"]),
                   foreign_compute_count=len(foreign) - graphics, graphics_client_count=graphics)
        if owned_pids is None:
            busy = gpu_busy(gpu, card["display_attached"])
            if busy:
                problems.append("GPU in use: " + busy + "; its owner must release it first")
        else:
            if not row["owned_count"]:
                problems.append("owned engine not observed on card")
            if row["foreign_compute_count"] or graphics and not card["display_attached"]:
                problems.append("foreign GPU owner observed")
    return observations


# Stock releases whose layer-split staging (serve/server.py gpu_list, layer_split_value and ordered_gpus: the bodies
# vendored in tests/fixtures/strata_0_1_42_ordered_gpus.py) and startup messages were reviewed against
# parse_stage_order and _layer_boundaries. Add a release only after that review: an unreviewed one leaves every
# multi-GPU start degraded, and every gate refuses it.
STAGE_ORDER_REVIEWED_ENGINES = frozenset({"0.1.42", "0.1.43", "0.1.43.1", "0.1.44.1"})


def parse_stage_order(log_text: str, configured: list[int]) -> dict:
    """Parse a complete reviewed stock startup interval, never infer from partial/unknown messages."""
    result = {"configured": list(configured), "staged": None, "event": "unavailable", "messages": [],
              "complete": False, "reason": None}
    if (len(configured) < 2 or any(type(i) is not int or i < 0 for i in configured)
            or len(set(configured)) != len(configured)):
        result["reason"] = "invalid configured GPU order"
        return result
    if log_text and not log_text.endswith("\n"):
        result["reason"] = "truncated startup output"
        return result
    reorder = re.compile(r'\[strata\] layer split: card order (\d+(?:,\d+)+) '
                         r'\(the faster card last; "gpu_order": "as_given" keeps (\d+(?:,\d+)+), #1352\)')
    keep = re.compile(r"\[strata\] layer split: keeping card order (\d+(?:,\d+)+) - the faster card has "
                      r"less VRAM than the one the split ends on \(\d+ vs \d+ MiB, #1576\)")
    events = set()
    for line in log_text.splitlines():
        if "[strata] layer split:" not in line:
            continue
        result["messages"].append(line)
        match = reorder.fullmatch(line)
        if match:
            staged = tuple(map(int, match[1].split(",")))
            original = list(map(int, match[2].split(",")))
            event = "reordered"
            valid = original == configured and list(staged) != configured
        else:
            match = keep.fullmatch(line)
            if not match:
                result["reason"] = "unknown stage-order message"
                return result
            staged = tuple(map(int, match[1].split(",")))
            event = "kept_1576"
            valid = list(staged) == configured
        if not valid or sorted(staged) != sorted(configured):
            result["reason"] = "stage-order message contradicts configured GPUs"
            return result
        events.add((event, staged))
    if len(events) > 1:
        result["reason"] = "contradictory stage-order messages"
        return result
    event, staged = next(iter(events)) if events else ("kept_configured", tuple(configured))
    result.update(staged=list(staged), event=event, complete=True)
    return result


def _engine_log_path(layout: Layout) -> Path:
    """Stock opens config.log relative to the server's cwd (the pinned source root)."""
    value = read_json(layout.strata_config).get("log")
    if not isinstance(value, str) or not value.strip():
        raise LifecycleError("generated config must name the engine log for multi-GPU startup capture")
    path = (layout.strata / value).resolve()
    if not path.is_relative_to(layout.root.resolve()) or path.exists() and not path.is_file():
        raise LifecycleError("generated engine log must resolve to a file inside the integration root")
    return path


def _startup_log_interval(layout: Layout, run: dict, field: str, allowed_root: Path) -> tuple[str, dict]:
    path = (layout.root / run[field]).resolve()
    if not path.is_relative_to(allowed_root.resolve()):
        raise ValueError(f"{field}: startup log outside allowed integration directory")
    offset = run.get(field + "_start_offset")
    if type(offset) is not int or offset < 0:
        raise ValueError(f"{field}: startup log interval unavailable")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if before.st_size <= offset:
            raise ValueError(f"{field}: startup log interval missing or truncated")
        stream.seek(offset)
        raw = stream.read(before.st_size - offset)
        after = os.fstat(stream.fileno())
    current = path.stat()
    if (len(raw) != before.st_size - offset or after.st_size < before.st_size
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)):
        raise ValueError(f"{field}: startup log changed during capture")
    return raw.decode("utf-8"), {"path": run[field], "start": offset, "end": before.st_size}


def _layer_boundaries(log_text: str, staged: list[int]) -> list[dict]:
    """Require one consistent, contiguous owned layer range for every CUDA stage in this engine interval."""
    if not log_text.endswith("\n"):
        raise ValueError("truncated engine startup output")
    boundary = re.compile(r"strata generate: layer split: CUDA(\d+) runs layers (\d+)-(\d+)"
                          r"(?:, expert cache \d+ slots \((\d+(?:\.\d+)?) GiB\), "
                          r"\d+ of its \d+ profiled pairs; slot 0 verified)?")
    primary_cache = re.compile(r"strata generate: expert cache \d+ slots, (\d+(?:\.\d+)?) GiB of VRAM; policy is")
    boundaries, cache_lines = {}, set()
    starts = 0
    for line in log_text.splitlines():
        if line.startswith("[strata] ") and " engine started: " in line:
            starts += 1
        if "strata generate: layer split: CUDA" in line and "runs layers" in line:
            match = boundary.fullmatch(line)
            if not match:
                raise ValueError("unknown engine layer-boundary syntax")
            index = int(match[1])
            if index in boundaries and boundaries[index][0] != line:
                raise ValueError("contradictory engine layer boundaries")
            row = {"cuda_index": index, "first_layer": int(match[2]), "last_layer": int(match[3])}
            if match[4] is not None:
                row["expert_cache_gib"] = float(match[4])
            boundaries[index] = (line, row)
        if primary_cache.fullmatch(line):
            cache_lines.add(line)
    if starts > 1:
        raise ValueError("multiple engine generations in startup interval")
    if len(cache_lines) > 1:
        raise ValueError("contradictory primary expert cache observations")
    if set(boundaries) != set(range(len(staged))):
        raise ValueError("engine layer boundaries missing or unexpected CUDA stages")
    result, next_layer = [], 0
    for index, physical in enumerate(staged):
        row = boundaries[index][1]
        if row["first_layer"] != next_layer or row["last_layer"] < row["first_layer"]:
            raise ValueError("engine layer boundaries are not contiguous ascending ranges from layer 0")
        row["gpu_index"] = physical
        next_layer = row["last_layer"] + 1
        result.append(row)
    if cache_lines:
        value = float(primary_cache.fullmatch(next(iter(cache_lines)))[1])
        if "expert_cache_gib" in result[0] and result[0]["expert_cache_gib"] != value:
            raise ValueError("contradictory primary expert cache observations")
        result[0]["expert_cache_gib"] = value
    return result


def capture_startup_gpu_order(layout: Layout) -> dict:
    """Bind complete owned startup output to the recorded engine generation; persist only at start, not status."""
    run = read_json(layout.run_record)
    configured = list(layout.profile.gpu_indices)
    observation = {"configured": configured, "staged": None, "event": "unavailable", "messages": [],
                   "complete": False, "reason": None, "layer_split": "auto", "layer_boundaries": []}
    try:
        if str(layout.profile.data["strata"]["engine_version"]).lstrip("v") not in STAGE_ORDER_REVIEWED_ENGINES:
            raise ValueError("stage-order inference requires a reviewed stock Strata release")
        engine = procs.matches(run.get("engine"))
        server = procs.matches(run.get("server"))
        if engine is None or server is None or run.get("state") != "ready":
            raise ValueError("owned ready engine identity unavailable")
        engines = [p for p in procs.descendants(server.pid) if Path(p.exe).name.lower().startswith("strata")]
        if len(engines) != 1 or engines[0].as_dict() != engine.as_dict():
            raise ValueError("engine generation changed before capture")
        text, interval = _startup_log_interval(layout, run, "log", layout.logs)
        parsed = parse_stage_order(text, configured)
        observation.update(parsed)
        observation["log_interval"] = interval
        if not parsed["complete"]:
            raise ValueError(parsed["reason"])
        engine_text, engine_interval = _startup_log_interval(layout, run, "engine_log", layout.root)
        observation["engine_log_interval"] = engine_interval
        boundaries = _layer_boundaries(engine_text, parsed["staged"])
        if procs.matches(run["engine"]) is None or procs.matches(run["server"]) is None:
            raise ValueError("engine generation changed during capture")
        engines = [p for p in procs.descendants(server.pid) if Path(p.exe).name.lower().startswith("strata")]
        if len(engines) != 1 or engines[0].as_dict() != engine.as_dict():
            raise ValueError("engine generation changed during capture")
        observation.update(engine_identity=engine.as_dict(),
                           engine_instance_sha256=sha256_bytes(canonical_json(engine.as_dict())),
                           layer_boundaries=boundaries)
    except (OSError, ValueError, KeyError) as exc:
        observation.update(staged=None, event="unavailable", complete=False, reason=str(exc))
    latest = read_json(layout.run_record)
    if any(latest.get(key) != run.get(key) for key in ("engine", "server", "requested_utc", "state")):
        observation.update(staged=None, event="unavailable", complete=False,
                           reason="run generation changed during capture")
    latest["gpu_stage_order"] = observation
    atomic_write_json(layout.run_record, latest)
    return observation


def doctor(layout: Layout) -> dict:
    """Read-only inspection; returns {'ok': bool, 'checks': [...]} with redacted, actionable messages."""
    p = layout.profile.data
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str, blocking: bool = True) -> None:
        checks.append({"check": name, "ok": ok, "detail": detail, "blocking": blocking})

    host = p["host"]
    plat = host_platform()
    want_os = {"windows": "windows-x64", "linux": "linux-x64"}[host["os"]]
    check("platform", plat == want_os, f"{plat} (profile expects {want_os})")
    check("python", sys.version_info >= (3, 11), f"tool Python {sys.version.split()[0]}")
    check("git", shutil.which("git") is not None, "git on PATH" if shutil.which("git") else "git missing")
    mem = procs.memory()
    gib = 1 << 30
    if mem["total"]:
        check("ram_total", mem["total"] / gib >= host["min_total_ram_gib"],
              f"{mem['total'] / gib:.1f} GiB total (needs {host['min_total_ram_gib']})")
        check("ram_available", mem["available"] / gib >= host["min_available_ram_gib_at_start"],
              f"{mem['available'] / gib:.1f} GiB available now (start needs "
              f"{host['min_available_ram_gib_at_start']})", blocking=False)
    for card in layout.profile.gpu_requirements:
        index = card["gpu_index"]
        suffix = f".{index}" if layout.profile.multi_gpu else ""
        gpu = gpu_facts(index, multi_gpu=True) if layout.profile.multi_gpu else gpu_facts(index)
        if gpu.get("available"):
            check("gpu_model" + suffix, gpu["name"] == card["gpu_model"], f"GPU {index}: {gpu['name']}")
            check("gpu_vram" + suffix, gpu["memory_total_mib"] >= card["min_gpu_vram_mib"], f"{gpu['memory_total_mib']} MiB")
            check("driver" + suffix, int(gpu["driver"].split(".")[0]) >= host["min_driver_major"], f"driver {gpu['driver']}")
            if layout.profile.multi_gpu:
                for field in ("gpu_index", "arch", "pci_bus_id"):
                    check(field + suffix, gpu.get(field) == card[field], f"{field}: {gpu.get(field)}")
                check("display_active" + suffix, not gpu["display_active"] or card["display_attached"],
                      f"display active: {gpu['display_active']}")
            busy = gpu_busy(gpu, card["display_attached"])
            check("gpu_idle" + suffix, busy is None, f"{busy}; another runtime must be stopped by its owner first" if busy
                  else f"idle ({gpu['graphics_apps']} display client(s))" if gpu["graphics_apps"] else "idle",
                  blocking=False)
        else:
            check("gpu" + suffix, False, gpu.get("reason", "nvidia-smi unavailable") if layout.profile.multi_gpu
                  else "nvidia-smi unavailable")
    layout.root.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(layout.root).free / gib
    check("disk", free >= host["min_free_disk_gib"], f"{free:.0f} GiB free at the integration root")
    srv = p["server"]
    busy = port_in_use(srv["listen_host"], srv["port"])
    owned = procs.matches((read_json(layout.run_record) if layout.run_record.exists() else {}).get("server"))
    check("port", not busy or owned is not None,
          f"{srv['listen_host']}:{srv['port']} " + ("held by this integration" if owned else
                                                    "occupied by an unrelated process" if busy else "free"),
          blocking=False)
    check("key_file", layout.key_file.exists(), "present" if layout.key_file.exists() else "run keygen",
          blocking=False)
    rec = read_json(layout.install_record) if layout.install_record.exists() else None
    check("installed", bool(rec) and rec.get("profile_fingerprint") == layout.profile.fingerprint,
          "install record matches this profile" if rec and rec.get("profile_fingerprint") ==
          layout.profile.fingerprint else "not installed for this profile", blocking=False)
    real_appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Strata"
    if WINDOWS:
        check("user_strata_settings", True, "a per-user %APPDATA%\\Strata exists (left untouched)"
              if real_appdata.exists() else "no per-user %APPDATA%\\Strata (this tool never creates one)",
              blocking=False)
    return {"ok": all(c["ok"] for c in checks if c["blocking"]), "checks": checks}


# ------------------------------------------------------------------------------------------------ identity
def verify_install_fast(layout: Layout) -> dict:
    """Recheck the install record against disk before a start: small files are rehashed, shards by cached proof."""
    if not layout.install_record.exists():
        raise LifecycleError("not installed; run install first")
    rec = read_json(layout.install_record)
    if rec.get("profile_fingerprint") != layout.profile.fingerprint:
        raise LifecycleError("the install was made for a different profile fingerprint; reinstall or switch back")
    root = layout.root.resolve()
    shards = {layout.model_file(f).resolve().relative_to(root).as_posix(): f for f in
              layout.profile.data["model"]["files"]}
    drift = []
    for rel, want in rec["identity"]["files"].items():
        path = root / rel
        if rel in shards:
            if not verified_ok(path, want["bytes"], want["sha256"]):
                drift.append(rel)
            continue
        if not path.is_file() or path.stat().st_size != want["bytes"] or sha256_file(path) != want["sha256"]:
            drift.append(rel)
    if sha256_file(layout.strata_config) != rec["identity"]["config_file_sha256"]:
        drift.append(layout.strata_config.name)
    verify_generated(layout)
    shared = read_json(layout.shared_settings) if layout.shared_settings.exists() else {}
    if shared != {}:
        drift.append(layout.shared_settings.name)
    if drift:
        raise LifecycleError("runtime inputs drifted from the install record: " + ", ".join(sorted(drift)[:12]))
    return rec


def server_argv(layout: Layout) -> list[str]:
    srv = layout.profile.data["server"]
    return [str(layout.venv_python), str(layout.strata / "serve" / "server.py"), "--engine", "strata", "--config",
            str(layout.strata_config), "--port", str(srv["port"]), "--host", srv["listen_host"]]


def server_env(layout: Layout, key: str) -> dict[str, str]:
    # Inherited STRATA_* variables are engine and server tuning/debug knobs (v0.1.31 alone added 16): a setting changes
    # only through a new profile, so none passes through; the key is set explicitly below.
    env = {k: v for k, v in os.environ.items()
           if not any(m in k.upper() for m in SECRET_ENV_MARKERS) and not k.upper().startswith("STRATA_")
           and k.upper() not in ("CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER")}
    env["APPDATA"] = str(layout.appdata)
    env["XDG_CONFIG_HOME"] = str(layout.appdata)
    env["PYTHONIOENCODING"] = "utf-8"
    env[layout.profile.data["server"]["api_key_env"]] = key
    return env


# ------------------------------------------------------------------------------------------------ serve
def serve(layout: Layout, *, log_path: Path) -> int:
    """Foreground wrapper (normally launched detached by `start`): key -> env -> stock server.py child.

    The wrapper has no console of its own when detached, so its own failures go to the server log too."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab", buffering=0) as out:
        try:
            key = read_key(layout)
            me = procs.info(os.getpid())
            flags = CREATE_NO_WINDOW if WINDOWS else 0
            child = subprocess.Popen(server_argv(layout), cwd=layout.strata, env=server_env(layout, key),
                                     stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                     creationflags=flags, start_new_session=not WINDOWS)
            server = procs.info(child.pid)
            record = read_json(layout.run_record) if layout.run_record.exists() else {}
            record.update({"wrapper": me.as_dict() if me else None, "server": server.as_dict() if server else None,
                           "state": "starting", "serve_started_utc": utc_now()})
            atomic_write_json(layout.run_record, record)
        except Exception as exc:  # noqa: BLE001 - recorded for the operator, then re-raised
            out.write(f"[omp-strata] serve wrapper failed: {type(exc).__name__}: {exc}\n".encode("utf-8"))
            record = read_json(layout.run_record) if layout.run_record.exists() else {}
            record.update({"state": "exited", "exit_code": -1, "wrapper_error": type(exc).__name__})
            atomic_write_json(layout.run_record, record)
            raise
        rc = child.wait()
    record = read_json(layout.run_record)
    if record.get("server") and server and record["server"]["pid"] == server.pid:
        record.update({"state": "exited", "exit_code": rc, "exited_utc": utc_now()})
        atomic_write_json(layout.run_record, record)
    return rc


def _launch_detached(argv: list[str], *, cwd: Path, log: Path) -> None:
    if WINDOWS:
        line = subprocess.list2cmdline(argv)
        script = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="
                  + _ps_quote(line) + "; CurrentDirectory=" + _ps_quote(str(cwd)) + "}; "
                  "if ($r.ReturnValue -ne 0) { exit 1 }; $r.ProcessId")
        out = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
        if out.returncode != 0:
            raise LifecycleError(f"could not launch the serve wrapper: {out.stderr.strip()[:300]}")
    else:
        with open(log, "ab") as f:
            subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT,
                             start_new_session=True)


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


# ------------------------------------------------------------------------------------------------ start
def running(layout: Layout) -> dict[str, procs.ProcInfo]:
    rec = read_json(layout.run_record) if layout.run_record.exists() else {}
    live = {}
    for role in ("wrapper", "server", "engine"):
        p = procs.matches(rec.get(role))
        if p is not None:
            live[role] = p
    return live


def runtime_checks(layout: Layout, key: str) -> dict:
    """Authenticated identity checks; a 200 from /health alone proves nothing."""
    p = layout.profile.data
    url = base_url(layout)
    problems = []
    st, health = http_json(url + "/health")
    if st != 200 or not isinstance(health, dict):
        return {"ready": False, "problems": [f"/health {st}"]}
    if health.get("api_key") is not True:
        problems.append("server reports authentication disabled")
    if health.get("model") != p["strata"]["model_name"]:
        problems.append(f"/health model {health.get('model')!r}")
    if health.get("max_context") != p["strata"]["setup_args"]["context"]:
        problems.append(f"/health max_context {health.get('max_context')}")
    if health.get("loaded") is False:                      # reported since v0.1.30: unloaded (idle unload) or died
        problems.append("/health reports the engine not loaded")
    st_anon, _ = http_json(url + "/v1/models")
    if st_anon != 401:
        problems.append(f"unauthenticated /v1/models returned {st_anon}, expected 401")
    st, models = http_json(url + "/v1/models", key=key)
    ids = [m.get("id") for m in (models or {}).get("data", [])] if isinstance(models, dict) else []
    if st != 200 or ids != [p["strata"]["model_name"]]:
        problems.append(f"/v1/models {st} {ids}")
    st, props = http_json(url + "/props", key=key)
    props = props if isinstance(props, dict) else {}
    n_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
    if st != 200 or n_ctx != p["strata"]["setup_args"]["context"]:
        problems.append(f"/props {st} n_ctx={n_ctx}")
    build = props.get("build_info")
    if build and build not in {f"Strata {label}" for label in engine_labels(p["strata"]["engine_version"])}:
        problems.append(f"/props build_info {build!r}")
    model_path = props.get("model_path")
    shard1 = layout.model_file(p["model"]["files"][0]).resolve()
    if model_path and Path(model_path).resolve() != shard1:
        problems.append("/props model_path is not the pinned first shard")
    st, shared = http_json(url + "/settings", key=key)
    if st != 200 or shared != {"shared": False, "defaults": {}}:
        problems.append(f"/settings {st}: shared settings are not the frozen empty defaults")
    return {"ready": not problems, "problems": problems, "health": health, "build_info": build,
            "modalities": props.get("modalities"), "n_ctx": n_ctx}


def _check_pipeline_windows(layout: Layout) -> None:
    """Require stock's decode-capable ON line in this start's engine-log interval, never an older generation's."""
    run = read_json(layout.run_record)
    try:
        text, interval = _startup_log_interval(layout, run, "engine_log", layout.root)
    except (OSError, ValueError, KeyError) as exc:
        raise LifecycleError(f"strata.pipeline_windows: {exc}") from exc
    on = re.compile(r"strata serve: --pipeline-windows 2: two verifiers per stage, \d+ stages overlap across windows"
                    r" \(decode too; the GDN (?:snapshots beside the window|snapshot on the critical path)\)")
    observed = None
    for line in text.splitlines():
        if line.startswith("strata generate: --pipeline-windows 2 is off:"):
            raise LifecycleError(f"strata.pipeline_windows: {line}")
        if line.startswith("strata serve: --pipeline-windows 2:"):
            if not on.fullmatch(line):
                raise LifecycleError(f"strata.pipeline_windows: decode-capable pipeline not confirmed: {line}")
            observed = line
    if observed is None:
        raise LifecycleError("strata.pipeline_windows: decode-capable ON line absent from this start's engine-log interval")
    run["pipeline_windows"] = {"log_line": observed, "engine_log_interval": interval}
    atomic_write_json(layout.run_record, run)


def start(layout: Layout, *, tool_argv: list[str], log: Log, timeout: int | None = None) -> dict:
    p = layout.profile.data
    srv = p["server"]
    with FileLock(layout.lock_file):
        rec = verify_install_fast(layout)
        key = read_key(layout)
        live = running(layout)
        if live:
            raise LifecycleError(f"integration-owned processes already running ({', '.join(live)}); use status/stop")
        if port_in_use(srv["listen_host"], srv["port"]):
            raise LifecycleError(f"{srv['listen_host']}:{srv['port']} is occupied by a process this integration "
                                 "does not own; refusing to start or adopt it")
        if layout.profile.multi_gpu:
            cards = card_observations(layout.profile)
            problems = [f"GPU {card['gpu_index']}: {problem}" for card in cards for problem in card["problems"]]
            if problems:
                raise LifecycleError("; ".join(problems))
        else:
            gpu = gpu_facts(p["host"]["gpu_index"])
            busy = gpu_busy(gpu, bool(p["host"].get("display_attached", False)))
            if busy:
                raise LifecycleError(f"GPU {p['host']['gpu_index']} is in use ({busy}); its owner must release it first")
        mem = procs.memory()
        need = p["host"]["min_available_ram_gib_at_start"] * (1 << 30)
        if mem["available"] and mem["available"] < need:
            raise LifecycleError(f"only {mem['available'] / (1 << 30):.1f} GiB RAM available; the profile needs "
                                 f"{p['host']['min_available_ram_gib_at_start']} GiB at start")
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        log_path = layout.logs / f"server-{stamp}.log"
        capture = {}
        if layout.profile.multi_gpu:
            engine_log = _engine_log_path(layout)
            capture = {"log_start_offset": log_path.stat().st_size if log_path.exists() else 0,
                       "engine_log": engine_log.relative_to(layout.root.resolve()).as_posix(),
                       "engine_log_start_offset": engine_log.stat().st_size if engine_log.exists() else 0}
        atomic_write_json(layout.run_record, {
            "schema_version": 1, "profile_id": layout.profile.id, "profile_fingerprint": layout.profile.fingerprint,
            "runtime_identity_sha256": rec["runtime_identity_sha256"], "port": srv["port"],
            "requested_utc": utc_now(), "state": "launching", "log": log_path.relative_to(layout.root).as_posix(),
            **capture})
        argv = [*tool_argv, "serve", "--profile", str(layout.profile.path.resolve()), "--root", str(layout.root),
                "--log", str(log_path)]
        t0 = time.monotonic()
        _launch_detached(argv, cwd=layout.root, log=layout.logs / f"serve-{stamp}.log")
        deadline = t0 + (timeout or srv["ready_timeout_s"])
        result: dict = {"ready": False, "problems": ["not started"]}
        while time.monotonic() < deadline:
            time.sleep(2)
            run = read_json(layout.run_record)
            if run.get("state") == "exited":
                break
            if not run.get("server"):
                continue
            if procs.matches(run["server"]) is None:
                break
            result = runtime_checks(layout, key)
            if result["ready"]:
                break
        run = read_json(layout.run_record)
        server = procs.matches(run.get("server"))
        if not result.get("ready") or server is None:
            log("readiness failed: " + "; ".join(result.get("problems", ["server exited"])))
            stop(layout, log=log, locked=True)
            raise LifecycleError("Strata did not become ready: " + "; ".join(result.get("problems", ["exited"])))
        tree = procs.descendants(server.pid)
        engine = next((e for e in tree if Path(e.exe).name.lower().startswith("strata")), None)
        run.update({"state": "ready", "ready_utc": utc_now(), "ready_s": round(time.monotonic() - t0, 1),
                    "engine": engine.as_dict() if engine else None, "build_info": result.get("build_info"),
                    "server_tree": [p.as_dict() for p in tree]})
        atomic_write_json(layout.run_record, run)
        if layout.profile.multi_gpu:
            cards = card_observations(layout.profile, owned_pids={server.pid, *(p.pid for p in tree)})
            problems = [f"GPU {card['gpu_index']}: {problem}" for card in cards for problem in card["problems"]]
            if engine is None:
                problems.append("owned engine identity unavailable after readiness")
            if problems:
                stop(layout, log=log, locked=True)
                raise LifecycleError("GPU ownership changed during launch: " + "; ".join(problems))
        stage = capture_startup_gpu_order(layout) if layout.profile.multi_gpu else None
        if "pipeline_windows" in p["strata"]:
            try:
                _check_pipeline_windows(layout)
            except LifecycleError:
                stop(layout, log=log, locked=True)
                raise
        return {"state": "degraded" if stage and not stage["complete"] else "healthy", "ready_s": run["ready_s"], "port": srv["port"],
                "engine_found": engine is not None, "log": run["log"],
                **({"cards": cards, "gpu_stage_order": stage} if layout.profile.multi_gpu else {})}


# ------------------------------------------------------------------------------------------------ status / stop
def status(layout: Layout) -> dict:
    if not layout.install_record.exists():
        return {"state": "not_installed"}
    rec = read_json(layout.install_record)
    if rec.get("profile_fingerprint") != layout.profile.fingerprint:
        return {"state": "mismatched", "problems": ["install record belongs to another profile fingerprint"]}
    run = read_json(layout.run_record) if layout.run_record.exists() else {}
    live = running(layout)
    if not live:
        occupancy = {"cards": card_observations(layout.profile)} if layout.profile.multi_gpu else {}
        if run.get("state") == "exited" and run.get("exit_code") not in (0, None):
            return {"state": "failed", "exit_code": run.get("exit_code"), "log": run.get("log"), **occupancy}
        return {"state": "stopped", **occupancy}
    if run.get("runtime_identity_sha256") != rec.get("runtime_identity_sha256"):
        return {"state": "mismatched", "problems": ["running server was started from another install identity"]}
    if "server" not in live:
        return {"state": "degraded", "problems": ["server process gone while other owned processes remain"],
                "live": sorted(live)}
    if run.get("state") in ("launching", "starting"):
        return {"state": "starting", "live": sorted(live)}
    try:
        key = read_key(layout)
    except LifecycleError as exc:
        return {"state": "degraded", "problems": [str(exc)]}
    checks = runtime_checks(layout, key)
    problems = list(checks.get("problems", []))
    server = live["server"]
    tree = procs.descendants(server.pid)
    if run.get("engine") and not any(Path(p.exe).name.lower().startswith("strata") for p in tree):
        problems.append("no engine process under the server (stock Strata restarts it on the next request)")
    extra = {}
    if layout.profile.multi_gpu:
        cards = card_observations(layout.profile, owned_pids={server.pid, *(p.pid for p in tree)})
        problems.extend(f"GPU {card['gpu_index']}: {problem}" for card in cards for problem in card["problems"])
        stage = dict(run.get("gpu_stage_order") or {})
        current_engines = [p for p in tree if Path(p.exe).name.lower().startswith("strata")]
        if (not stage.get("complete") or len(current_engines) != 1
                or current_engines[0].as_dict() != stage.get("engine_identity")):
            stage.update(complete=False, staged=None, event="unavailable",
                         reason="startup stage order unavailable for current engine generation")
            problems.append(stage["reason"])
        extra = {"cards": cards, "gpu_stage_order": stage}
    state = "healthy" if not problems else "degraded"
    return {"state": state, "problems": problems, "live": sorted(live), "ready_s": run.get("ready_s"),
            "started_utc": run.get("ready_utc"), **extra}


def stop(layout: Layout, *, log: Log, locked: bool = False) -> dict:
    def _stop() -> dict:
        if not layout.run_record.exists():
            extra = {"cards": card_observations(layout.profile), "owned_gpus_released": None} if layout.profile.multi_gpu else {}
            return {"state": "stopped", "stopped": [], **extra}
        run = read_json(layout.run_record)
        timeout = layout.profile.data["server"]["stop_timeout_s"]
        stopped, refused = [], []
        # Owned roots are the recorded wrapper and server (identity-verified). Their CURRENT descendants are owned
        # too (the real interpreter behind the venv redirector, and any engine the server restarted), so each
        # verified root is stopped with its subtree, deepest first; a PID that no longer matches is never touched.
        targets: list[tuple[str, procs.ProcInfo]] = []
        for role in ("server", "wrapper"):
            root = procs.matches(run.get(role))
            if root is None:
                continue
            targets += [(f"{role}-descendant", d) for d in procs.descendants(root.pid)]
            targets.append((role, root))
        for rec in [run.get("engine"), *run.get("server_tree", [])]:
            orphan = procs.matches(rec)
            if orphan is not None and all(orphan.pid != t.pid for _, t in targets):
                targets.insert(0, ("orphan", orphan))
        done: set[int] = set()
        for role, proc in targets:
            if proc.pid in done:
                continue
            done.add(proc.pid)
            try:
                if procs.terminate(proc, timeout):
                    stopped.append(f"{role}:{Path(proc.exe).name}")
                else:
                    refused.append(f"{role} {Path(proc.exe).name} did not exit within {timeout}s")
            except PermissionError as exc:
                refused.append(str(exc))
        run.update({"state": "stopped" if not refused else "stop_incomplete", "stopped_utc": utc_now()})
        atomic_write_json(layout.run_record, run)
        srv = layout.profile.data["server"]
        deadline = time.monotonic() + timeout
        while port_in_use(srv["listen_host"], srv["port"]) and time.monotonic() < deadline:
            time.sleep(0.5)
        if refused:
            raise LifecycleError("; ".join(refused))
        extra = {}
        if layout.profile.multi_gpu:
            recorded = {r["pid"] for r in [run.get("engine"), *run.get("server_tree", [])] if r}
            cards = card_observations(layout.profile, owned_pids=done | recorded)
            released = all(card["owned_count"] == 0 for card in cards)
            extra = {"cards": cards, "owned_gpus_released": released}
        return {"state": "stopped", "stopped": stopped, **extra}

    if locked:
        return _stop()
    with FileLock(layout.lock_file):
        return _stop()


def ensure_healthy(layout: Layout) -> str:
    st = status(layout)
    if st["state"] != "healthy":
        raise LifecycleError(f"Strata is {st['state']}: " + "; ".join(st.get("problems", [])))
    return read_key(layout)


def tool_argv() -> list[str]:
    """How to re-invoke this tool (for the detached wrapper): the current interpreter plus scripts/omp_strata.py."""
    return [sys.executable, str(Path(__file__).resolve().parent.parent / "scripts" / "omp_strata.py")]



__all__ = ["FileLock", "InstallError", "LifecycleError", "doctor", "ensure_healthy", "keygen", "read_key",
           "serve", "start", "status", "stop", "tool_argv"]
