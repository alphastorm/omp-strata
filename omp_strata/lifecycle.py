"""Minimal lifecycle for one stock Strata server: keygen, doctor, start, serve (wrapper), status, stop.

No daemon of our own: `start` launches a detached `serve` wrapper that reads the private key file, starts stock
`serve/server.py` on loopback with the key in its environment, and records owned process identities in
`<root>/state/run.json`. `stop` only ever terminates processes whose PID, creation time and executable still match
that record. A server already on the port is never adopted.
"""

from __future__ import annotations

import json
import os
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

from . import procs
from .common import atomic_write_bytes, atomic_write_json, read_json, sha256_file, utc_now, verified_ok
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


def gpu_facts(index: int) -> dict:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False}
    q = subprocess.run([exe, "-i", str(index), "--query-gpu=name,memory.total,memory.used,driver_version",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=30)
    apps = subprocess.run([exe, "-i", str(index), "--query-compute-apps=pid,used_memory",
                           "--format=csv,noheader,nounits"], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=30)
    if q.returncode != 0 or not q.stdout.strip():
        return {"available": False}
    name, total, used, driver = [x.strip() for x in q.stdout.strip().splitlines()[0].split(",")]
    owners = [line.strip() for line in apps.stdout.splitlines() if line.strip()]
    return {"available": True, "name": name, "memory_total_mib": int(float(total)),
            "memory_used_mib": int(float(used)), "driver": driver, "compute_apps": len(owners)}


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
    gpu = gpu_facts(host["gpu_index"])
    if gpu.get("available"):
        check("gpu_model", gpu["name"] == host["gpu_model"], f"GPU {host['gpu_index']}: {gpu['name']}")
        check("gpu_vram", gpu["memory_total_mib"] >= host["min_gpu_vram_mib"], f"{gpu['memory_total_mib']} MiB")
        check("driver", int(gpu["driver"].split(".")[0]) >= host["min_driver_major"], f"driver {gpu['driver']}")
        idle = gpu["memory_used_mib"] < GPU_IDLE_MIB and gpu["compute_apps"] == 0
        check("gpu_idle", idle, f"{gpu['memory_used_mib']} MiB used, {gpu['compute_apps']} compute app(s); "
              "another runtime must be stopped by its owner first" if not idle else "idle", blocking=False)
    else:
        check("gpu", False, "nvidia-smi unavailable")
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
    env = {k: v for k, v in os.environ.items() if not any(m in k.upper() for m in SECRET_ENV_MARKERS)}
    env.pop("STRATA_DEBUG", None)
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
    if build and build != f"Strata {p['strata']['engine_version']}":
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
        gpu = gpu_facts(p["host"]["gpu_index"])
        if gpu.get("available") and (gpu["memory_used_mib"] >= GPU_IDLE_MIB or gpu["compute_apps"]):
            raise LifecycleError(f"GPU {p['host']['gpu_index']} is in use ({gpu['memory_used_mib']} MiB, "
                                 f"{gpu['compute_apps']} compute app(s)); its owner must release it first")
        mem = procs.memory()
        need = p["host"]["min_available_ram_gib_at_start"] * (1 << 30)
        if mem["available"] and mem["available"] < need:
            raise LifecycleError(f"only {mem['available'] / (1 << 30):.1f} GiB RAM available; the profile needs "
                                 f"{p['host']['min_available_ram_gib_at_start']} GiB at start")
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        log_path = layout.logs / f"server-{stamp}.log"
        atomic_write_json(layout.run_record, {
            "schema_version": 1, "profile_id": layout.profile.id, "profile_fingerprint": layout.profile.fingerprint,
            "runtime_identity_sha256": rec["runtime_identity_sha256"], "port": srv["port"],
            "requested_utc": utc_now(), "state": "launching", "log": log_path.relative_to(layout.root).as_posix()})
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
        return {"state": "healthy", "ready_s": run["ready_s"], "port": srv["port"],
                "engine_found": engine is not None, "log": run["log"]}


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
        if run.get("state") == "exited" and run.get("exit_code") not in (0, None):
            return {"state": "failed", "exit_code": run.get("exit_code"), "log": run.get("log")}
        return {"state": "stopped"}
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
    if run.get("engine") and not any(Path(p.exe).name.lower().startswith("strata")
                                     for p in procs.descendants(server.pid)):
        problems.append("no engine process under the server (stock Strata restarts it on the next request)")
    state = "healthy" if not problems else "degraded"
    return {"state": state, "problems": problems, "live": sorted(live), "ready_s": run.get("ready_s"),
            "started_utc": run.get("ready_utc")}


def stop(layout: Layout, *, log: Log, locked: bool = False) -> dict:
    def _stop() -> dict:
        if not layout.run_record.exists():
            return {"state": "stopped", "stopped": []}
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
        return {"state": "stopped", "stopped": stopped}

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
