#!/usr/bin/env python3
"""Explicitly started, fenced native release runner; publication belongs to the control plane."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omp_strata import lifecycle, procs
from omp_strata.common import atomic_write_bytes, atomic_write_json, canonical_json, sha256_file
from omp_strata.layout import Layout
from omp_strata.profile import load
from scripts import campaign, experiment_loop, requalify, upstream_watch

STAGES = ("prepare", "source_check", "host_preflight", "incumbent_stop", "qualify",
          "candidate_stop", "restore", "settle", "verify", "ledger")
FILE_MAX = 2 * 1024 * 1024
BUNDLE_MAX = 8 * 1024 * 1024
WIRE_COMMIT = "7d9093928c941bca4b2929f5d8efbf3218487192"
VARIABLE_PATHS = (
    "/profile_id", "/description", "/status", "/strata/tag", "/strata/commit",
    "/strata/engine_version", "/strata/artifacts/engine_archive",
    "/strata/engine_component/build_commit", "/strata/engine_component/build_id",
    "/strata/engine_component/build_source", "/strata/engine_component/manifest_sha256",
    "/omp/tag", "/omp/version", "/omp/source_commit", "/omp/artifacts",
    "/model/dflash2_source/files/0/sha256_source", "/model/dflash2_source/files/1/sha256_source",
    "/model/dflash2_source/tuned/tag", "/model/dflash2_source/tuned/url",
    "/model/dflash2_source/tuned/sha256_source", "/host_floors/min_free_disk_gib/predecessor",
)


class Refused(ValueError):
    pass


class Unreachable(RuntimeError):
    pass


class StaleFence(Refused):
    pass


class ControllerUnavailable(RuntimeError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return digest(canonical_json(value))


def invariant_digest(profile):
    value = copy.deepcopy(profile)
    for pointer in VARIABLE_PATHS:
        parts, node = pointer[1:].split("/"), value
        try:
            for part in parts[:-1]:
                node = node[int(part)] if isinstance(node, list) else node[part]
            if isinstance(node, dict):
                node.pop(parts[-1], None)
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return fingerprint(value)


def candidate_digest(spec):
    value = copy.deepcopy(spec)
    for role in ("engine", "client"):
        value[role].pop("observation_event_id", None)
    return fingerprint(value)


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refused("duplicate_json_key")
            result[key] = value
        return result

    def invalid(value):
        raise Refused("nonfinite_json")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    json.dumps(value, allow_nan=False)
    return value


def document(path):
    return parse(Path(path).read_bytes())


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise Refused("timezone_required")
    return result.timestamp()


def bounded(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(FILE_MAX + 1)
    if len(raw) > FILE_MAX:
        raise Refused("evidence_file_too_large")
    return raw


def encoded(raw):
    if len(raw) > FILE_MAX:
        raise Refused("evidence_file_too_large")
    return base64.b64encode(raw).decode("ascii")


def evidence_bundle(release):
    """Collect the manifest's hash closure, not unrelated files in the release directory."""
    release = Path(release)
    manifest_raw = bounded(release / "manifest.json")
    manifest = parse(manifest_raw)
    files, total = {}, len(manifest_raw)

    def add(ref, expected):
        nonlocal total
        path = PurePosixPath(ref)
        if (str(path) != ref or path.is_absolute() or ".." in path.parts or "\\" in ref or ":" in ref
                or not (ref == "qualification.json" or path.parts[0] in ("receipts", "evidence"))):
            raise Refused("evidence_path_refused")
        target = release / ref
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
               for p in (target, *target.parents)):
            raise Refused("evidence_alias_refused")
        raw = bounded(target)
        if digest(raw) != expected:
            raise Refused("evidence_hash_mismatch")
        if ref not in files:
            files[ref] = encoded(raw)
            total += len(raw)
            if len(files) > 100 or total > BUNDLE_MAX:
                raise Refused("evidence_bundle_too_large")
        return raw

    ledger = parse(add(manifest["qualification"]["ledger"], manifest["qualification"]["ledger_sha256"]))
    for gate in ledger["gates"]:
        for link in gate["receipts"]:
            receipt = parse(add(link["path"], link["sha256"]))
            for evidence in receipt.get("evidence", []):
                if evidence.get("sha256"):
                    add(evidence["path_or_ref"], evidence["sha256"])
    return encoded(manifest_raw), files


def export_once(release, build):
    """Rebuild from a retained pre-export snapshot and reconcile an interrupted local swap."""
    release = Path(release)
    before = release.with_name("." + release.name + "-runner-input")
    previous = release.with_name("." + release.name + "-runner-previous")
    if previous.exists() and not release.exists():
        previous.rename(release)
    if not before.exists():
        with tempfile.TemporaryDirectory(prefix=".runner-input-", dir=release.parent) as temporary:
            staged = Path(temporary) / "input"
            shutil.copytree(release, staged)
            staged.rename(before)

    def inventory(directory):
        result = {}
        for path in directory.rglob("*"):
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise Refused("export_alias_refused")
            if path.is_file():
                result[path.relative_to(directory).as_posix()] = sha256_file(path)
        return result

    with tempfile.TemporaryDirectory(prefix=".runner-export-", dir=release.parent) as temporary:
        # Keep the manifest's ../../profiles reference at the native release depth.
        staged = Path(temporary)
        shutil.copytree(before, staged, dirs_exist_ok=True)
        build(staged)
        expected, current = inventory(staged), inventory(release)
        if current == expected:
            return
        if current != inventory(before):
            raise Refused("local_export_conflict")
        if previous.exists():
            shutil.rmtree(previous)
        release.rename(previous)
        try:
            staged.rename(release)
        except BaseException:
            previous.rename(release)
            raise
        shutil.rmtree(previous)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Refused("control_plane_redirect_refused")


class HTTP:
    def __init__(self, origin, token_file, *, opener=None):
        url = urllib.parse.urlsplit(origin)
        if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise Refused("control_plane_origin_required")
        try:
            private = ipaddress.ip_address(url.hostname or "").is_loopback
        except ValueError:
            private = False
        if url.scheme != "https" and not (url.scheme == "http" and private):
            raise Refused("control_plane_https_required")
        self.origin, self.token_file = origin.rstrip("/"), Path(token_file)
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def post(self, path, body):
        if not re.fullmatch(
                r"/api/project-loops/(release-runner/next-action|release-runs/[A-Z0-9]{26}/reports"
                r"|fleet-claims/[A-Z0-9]{26}/(?:usage|release))", path):
            raise Refused("control_plane_route_refused")
        token = self.token_file.read_text(encoding="ascii").strip()
        if not token or any(ch.isspace() for ch in token):
            raise Refused("invalid_token_file")
        request = urllib.request.Request(self.origin + path, data=canonical_json(body), method="POST",
                                         headers={"Authorization": "Bearer " + token,
                                                  "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise Refused("control_plane_response_too_large")
                return parse(raw)
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                raise StaleFence("control_plane_conflict") from None
            if exc.code >= 500 or exc.code == 429:
                raise Unreachable("control_plane_unavailable") from None
            raise Refused("control_plane_request_refused") from None
        except (OSError, urllib.error.URLError, TimeoutError):
            raise Unreachable("control_plane_unavailable") from None


def command(argv, cwd, *, timeout=120, heartbeat=None):
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if heartbeat is None:
        result = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=timeout, env=environment)
        if result.returncode:
            raise Refused("native_command_failed")
        return result.stdout
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 env=environment)
        deadline = time.monotonic() + timeout
        try:
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise Refused("native_command_timeout")
                try:
                    rc = child.wait(timeout=min(120, left))
                    break
                except subprocess.TimeoutExpired:
                    heartbeat()
            if rc:
                raise Refused("native_command_failed")
            out.seek(0)
            return out.read()
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


def tooling_identity(root, expected, run=command):
    if not re.fullmatch(r"[0-9a-f]{40}", expected or ""):
        raise Refused("unrecorded_tooling")
    head = run(["git", "rev-parse", "HEAD"], root).decode().strip()
    dirty = run(["git", "status", "--porcelain", "--untracked-files=all"], root)
    if head != expected or dirty.strip():
        raise Refused("dirty_or_unrecorded_tooling")
    return head


class Native:
    """Fixed native commands. Tests inject this boundary, the controller and the launcher."""
    def __init__(self, tooling, config, *, run=command):
        self.tooling, self.config, self.run = Path(tooling), config, run
        if self.tooling.resolve() != ROOT:
            raise Refused("executing_tooling_checkout_mismatch")

    def tool(self, work, name, args, *, timeout=120, heartbeat=None):
        self.run(["git", "diff", "--exit-code", "HEAD", "--", "scripts", "omp_strata"], work)
        if self.run(["git", "ls-files", "--others", "--exclude-standard", "--", "scripts", "omp_strata"], work).strip():
            raise Refused("unrecorded_native_tooling")
        return self.run([sys.executable, "-B", str(Path(work) / "scripts" / (name + ".py")), *map(str, args)],
                        work, timeout=timeout, heartbeat=heartbeat)

    def worktree(self, path, commit):
        path = Path(path)
        if not path.exists():
            self.run(["git", "worktree", "add", "--detach", str(path), commit], self.tooling)
        elif self.run(["git", "rev-parse", "HEAD"], path).decode().strip() != commit:
            raise Refused("worktree_commit_mismatch")

    def prepare(self, work, spec):
        # API(token=None) is explicit: campaign.main would consult ambient credential helpers.
        api = upstream_watch.API(token=None)
        record = campaign.open_campaign(api, work, spec["engine"]["tag"], omp_tag=spec["client"]["tag"])
        row = next((r for r in record["hosts"] if r["profile_id"] == spec["candidate_id"]), None)
        if row is None:
            raise Refused("candidate_not_in_native_campaign")
        for role, snapshot in (("engine", record), ("client", record["omp_release"])):
            frozen = spec[role]
            assets = [{"name": a["name"], "size": a["bytes"], "digest": "sha256:" + a["sha256"]}
                      for a in snapshot["assets"]]
            if (snapshot["peeled_commit"] != frozen["commit_sha"]
                    or sorted(assets, key=lambda a: a["name"]) != sorted(frozen["assets"], key=lambda a: a["name"])):
                raise Refused("source_changed")
        predecessor = work / "profiles" / (row["predecessor"]["profile_id"] + ".json")
        original = document(predecessor)
        options = {}
        if "engine_component" in original["strata"]:
            selected = upstream_watch.select_strata_assets(record, variant="cuda13")
            options.update(variant="cuda13", engine_archive=self.asset(
                spec["engine"], next(a for a in spec["engine"]["assets"]
                                     if a["name"] == selected["engine"]["name"])))
        if "gpus" in original["host"]:
            options["gpu_inventory"] = self.config["gpu_inventory"]
            setup = original["strata"]["setup_args"]
            if "gpu_roles" in setup:
                options["gpu_roles"] = {int(key): value for key, value in setup["gpu_roles"].items()}
            else:
                options["gpus"] = setup["gpus"]
            options["layer_split"] = setup.get("layer_split")
        upstream_watch.draft(api, work, predecessor, strata_tag=spec["engine"]["tag"],
                             omp_tag=spec["client"]["tag"], profile_id=spec["candidate_id"],
                             strata_src=Path(self.config["strata_source"]), **options)
        return {"predecessor_id": row["predecessor"]["profile_id"],
                "predecessor_manifest_sha256": sha256_file(work / row["predecessor"]["manifest"]),
                "campaign_path": campaign.campaign_path(work, spec["engine"]["tag"],
                                                       spec["client"]["tag"]).relative_to(work).as_posix()}

    def asset(self, source, asset):
        name = asset["name"]
        if Path(name).name != name or "/" in name or "\\" in name:
            raise Refused("asset_name_refused")
        expected = asset["digest"].removeprefix("sha256:")
        path = Path(self.config["cache"]) / expected / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            url = source["repository_url"].removesuffix(".git") + "/releases/download/"
            url += urllib.parse.quote(source["tag"], safe="") + "/" + urllib.parse.quote(name, safe="")
            partial = path.with_suffix(path.suffix + ".partial")
            try:
                with urllib.request.urlopen(url, timeout=120) as response, partial.open("xb") as out:
                    count = 0
                    while chunk := response.read(1024 * 1024):
                        count += len(chunk)
                        if count > asset["size"]:
                            raise Refused("asset_size_mismatch")
                        out.write(chunk)
                if partial.stat().st_size != asset["size"] or sha256_file(partial) != expected:
                    raise Refused("asset_digest_mismatch")
                partial.replace(path)
            finally:
                partial.unlink(missing_ok=True)
        if path.stat().st_size != asset["size"] or sha256_file(path) != expected:
            raise Refused("asset_digest_mismatch")
        return path

    def campaign_status(self, work, spec, status, **kwargs):
        return campaign.set_host(work, spec["engine"]["tag"], spec["candidate_id"], status,
                                 omp_tag=spec["client"]["tag"], **kwargs)

    def fetch(self, work, profile, root, *, heartbeat):
        args = ["--profile", profile, "--root", root]
        self.tool(work, "omp_strata", ["fetch", *args], timeout=7200, heartbeat=heartbeat)
        self.tool(work, "omp_strata", ["verify", *args, "--deep"], timeout=7200, heartbeat=heartbeat)

    def stop_candidate(self, work, profile, root):
        layout = Layout(Path(root), load(profile))
        if not layout.install_record.exists():
            return not lifecycle.port_in_use(*self.port(profile))
        self.tool(work, "omp_strata", ["stop", "--profile", profile, "--root", root], timeout=120)
        result = parse(self.tool(work, "omp_strata", ["status", "--profile", profile, "--root", root]))
        record = document(layout.run_record)
        return (result["state"] == "stopped" and record["state"] == "stopped"
                and not lifecycle.running(layout) and not lifecycle.port_in_use(*self.port(profile)))

    @staticmethod
    def port(profile):
        server = document(profile)["server"]
        return server["listen_host"], server["port"]

    def incumbent(self):
        profile = Path(self.config["incumbent_profile"])
        layout = Layout(Path(self.config["incumbent_root"]), load(profile))
        status = parse(self.tool(self.tooling, "omp_strata",
                                ["status", "--profile", profile, "--root", layout.root]))
        install, run = document(layout.install_record), document(layout.run_record)
        identity = {"profile_id": install["profile_id"], "profile_fingerprint": install["profile_fingerprint"],
                    "runtime_identity_sha256": install["runtime_identity_sha256"],
                    "config_file_sha256": install["identity"]["config_file_sha256"],
                    "run_generation": run["launch_id"]}
        if identity["profile_fingerprint"] != layout.profile.fingerprint:
            raise Refused("incumbent_profile_mismatch")
        return identity, status["state"] == "healthy", lifecycle.port_in_use(*self.port(profile))

    def export(self, work, profile, root, commit):
        # The native root already has the pull_run layout. No SSH or second raw copy is needed.
        from scripts import publish_run
        def build(stage):
            plan = publish_run.build_plan(pulled=root, profile_path=profile,
                                          host_label=self.config["public_host_label"], root_path=str(root),
                                          implementation_commit=commit, host_had_strata=True,
                                          release_dir=stage)
            publish_run.publish(plan)
        export_once(work / "releases" / document(profile)["profile_id"], build)

    def verify(self, work, profile):
        path = work / "releases" / document(profile)["profile_id"] / "manifest.json"
        from scripts.verify_release import verify
        return not verify(path, require_ready=True)["errors"]


class Controller:
    def __init__(self, executable, host, *, run=command):
        self.executable, self.host, self.run = str(executable), host, run

    def call(self, verb):
        if verb not in ("status", "use", "return"):
            raise Refused("controller_verb_refused")
        try:
            raw = self.run([self.executable, verb, self.host], ROOT, timeout=120)
            result = requalify.last_object(raw.decode("utf-8"))
            if verb == "status" and not result:
                raise Refused("controller_receipt_missing")
            return result
        except (OSError, Refused, subprocess.SubprocessError):
            raise ControllerUnavailable("controller_unavailable") from None


class Launcher:
    def __init__(self, *, run=command):
        self.run = run

    @staticmethod
    def wrapper(root, run_id):
        return Path(root) / "logs" / (run_id + ".launch.ps1")

    def live(self, root, run_id):
        if os.name != "nt":
            raise Refused("native_windows_launcher_required")
        wrapper = str(self.wrapper(root, run_id)).replace("'", "''")
        script = ("@(Get-CimInstance Win32_Process | Where-Object {"
                  "$_.Name -eq 'powershell.exe' -and $_.CommandLine.Contains('" + wrapper
                  + "') } | Select-Object -ExpandProperty ProcessId) | ConvertTo-Json -Compress")
        raw = self.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                       base64.b64encode(script.encode("utf-16le")).decode()], ROOT)
        pids = parse(raw) if raw.strip() else []
        if isinstance(pids, int):
            pids = [pids]
        return [process for pid in pids if (process := procs.info(pid)) is not None]

    def launch(self, work, profile, root, run_id):
        if os.name != "nt":
            raise Refused("native_windows_launcher_required")
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        args = [sys.executable, "-B", work / "scripts/requalify.py", "--profile", profile,
                "--root", root, "--run-id", run_id]
        invocation = "& " + " ".join(map(quote, args))
        raw = self.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                       "-File", str(work / "scripts/windows/launch-detached.ps1"),
                       "-WorkingDirectory", str(work), "-Log", str(Path(root) / "logs" / (run_id + ".log")),
                       "-Command", invocation], work)
        return parse(raw)

    def stop(self, root, run_id):
        for process in self.live(root, run_id):
            tree = procs.descendants(process.pid)
            procs.terminate(process, timeout=30)
            for child in reversed(tree):
                procs.terminate(child, timeout=30)
        return not self.live(root, run_id)


class Runner:
    def __init__(self, config, transport, native, controller, launcher, *,
                 identity=tooling_identity, clock=time.time, hold_directory=experiment_loop.HOST_LOCKS):
        self.config, self.transport = config, transport
        self.native, self.controller, self.launcher = native, controller, launcher
        self.identity, self.clock = identity, clock
        self.directory = Path(config["state_directory"])
        self.path = self.directory / "runner.json"
        self.holds = Path(hold_directory)
        self.state: dict[str, Any] = document(self.path) if self.path.exists() else {}
        self.release_hold = None

    def save(self):
        atomic_write_json(self.path, self.state)

    def supported(self):
        if self.config.get("incumbent_kind") != "strata":
            raise Refused("unsupported_incumbent_kind")
        if self.config.get("controller_kind") != "fleet":
            raise Refused("unsupported_controller_kind")

    def lock(self):
        return lifecycle.FileLock(self.holds / (self.config["native_host"] + ".release-runner"))

    def profile(self):
        return Path(self.state["native_refs"]["worktree"]) / "profiles" / (self.state["spec"]["candidate_id"] + ".json")

    def root(self):
        return Path(self.state["native_refs"]["candidate_root"])

    def work(self):
        return Path(self.state["native_refs"]["worktree"])

    def poll(self):
        self.supported()
        commit = self.identity(Path(self.config["tooling"]), self.config["tooling_commit"])
        request = {"schema_version": "carrythrough.release-runner-poll.v1",
                   "runner": self.config["runner"], "adapter": "omp-strata.v1",
                   "tooling_commit": commit, "tooling_dirty": False,
                   "resources": [{"resource_id": self.config["resource_id"],
                                  "available": True,
                                  "free_disk_bytes": shutil.disk_usage(self.directory.parent).free}]}
        try:
            action = self.transport.post("/api/project-loops/release-runner/next-action", request)
        except Unreachable:
            self.cleanup()
            raise
        if action.get("action") is None:
            return min(120, max(1, action["retry_after_seconds"]))
        self.accept(action)
        try:
            cached = self.state["completed"].get(self.key(action))
            if cached:
                self.report(action, **cached)
            else:
                getattr(self, "handle_" + action["action"])(action)
        except Unreachable:
            self.cleanup()
            raise
        except ControllerUnavailable:
            self.cleanup()
            self.report(action, None, "failed", "controller_unavailable")
        return 30

    @staticmethod
    def key(action):
        return action["action"] + ":" + str(action["stage_attempt"])

    def accept(self, action):
        stage, spec = action["action"], action["spec"]
        if stage not in STAGES:
            raise Refused("unsupported_action:" + str(stage))
        if (not re.fullmatch(r"[A-Z0-9]{26}", action["run_id"])
                or type(action["claim_generation"]) is not int or action["claim_generation"] < 1
                or not re.fullmatch(r"[0-9a-f]{64}", action["claim_token"])
                or type(action["stage_attempt"]) is not int or action["stage_attempt"] < 1):
            raise Refused("invalid_action_fence")
        if timestamp(action["lease_expires_at"]) <= self.clock():
            raise StaleFence("expired_action")
        host = spec["host"]
        if any(host[field] != self.config[field] for field in ("host", "native_host", "resource_id", "runner")):
            raise Refused("action_binding_mismatch")
        if (spec["adapter"] != "omp-strata.v1" or spec["recipe"]["resource_id"] != host["resource_id"]
                or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,255}", spec["candidate_id"])):
            raise Refused("candidate_binding_mismatch")
        if host["restoration_ref"] != self.config["restoration_ref"]:
            raise Refused("restoration_binding_mismatch")
        if self.state.get("run_id") == action["run_id"]:
            if self.state["spec"] != spec:
                raise Refused("frozen_spec_changed")
            previous = self.state["action"]
            if (action["claim_generation"] < previous["claim_generation"]
                    or action["claim_generation"] == previous["claim_generation"]
                    and action["claim_token"] != previous["claim_token"]):
                raise StaleFence("stale_action")
        elif self.state.get("claim_id") and not self.state.get("settled"):
            raise Refused("prior_run_unsettled")
        claim = action["claim"]
        if stage in STAGES[2:8] and claim is None:
            raise Refused("custody_claim_required")
        receipt = None
        if claim:
            raw = base64.b64decode(action["admission_receipt_b64"], validate=True)
            receipt = parse(raw)
            expected = {"schema_version": "carrythrough.fleet-claim.v1",
                        "host": host["host"], "resource_id": host["resource_id"],
                        "variant_id": spec["candidate_id"], "trial_manifest_sha256": digest(raw),
                        "restoration_ref": host["restoration_ref"]}
            if any(claim.get(key) != value for key, value in expected.items()):
                raise Refused("claim_binding_mismatch")
            candidate = receipt["candidate"]
            if (receipt["run_id"] != action["run_id"] or receipt["host"] != host
                    or receipt["claim"]["claim_id"] != claim["claim_id"]
                    or candidate["candidate_id"] != spec["candidate_id"]
                    or candidate["candidate_sha256"] != candidate_digest(spec)
                    or candidate["profile_sha256"] != action["profile_sha256"]
                    or candidate["recipe_id"] != spec["recipe"]["recipe_id"]
                    or candidate["recipe_invariant_sha256"] not in spec["recipe"]["invariant_sha256"]
                    or receipt["runtime"]["tooling_commit"] != self.config["tooling_commit"]
                    or receipt["runtime"]["runner"] != self.config["runner"]
                    or receipt["runtime"]["tooling_repository"] != "alphastorm/omp-strata"
                    or receipt["sources"] != [{"role": role, **spec[role]} for role in ("engine", "client")]):
                raise Refused("admission_binding_mismatch")
            if self.state.get("claim_id") not in (None, claim["claim_id"]):
                if not self.state.get("settled"):
                    raise Refused("claim_replacement_refused")
            if not re.fullmatch(r"[A-Z0-9]{26}", claim["claim_id"]):
                raise Refused("invalid_claim_id")
        if self.state.get("run_id") != action["run_id"]:
            self.state = {"run_id": action["run_id"], "claim_id": None, "spec": spec,
                          "completed": {}, "native_refs": {}, "mutated": False}
        self.state.update(action=action, stage=stage)
        self.state["native_refs"].setdefault("worktree", str(self.directory / "work" / action["run_id"]))
        if claim:
            if self.state.get("claim_id") != claim["claim_id"]:
                self.state.update(claim_id=claim["claim_id"], settled=False)
            self.state["receipt"] = receipt
            atomic_write_json(self.directory / "claims" / (claim["claim_id"] + ".json"), claim)
        self.save()
        if claim and not self.state.get("settled"):
            self.hold()

    def hold(self):
        if self.release_hold:
            return
        host, claim = self.config["native_host"], self.state["claim_id"]
        path = self.holds / (host + ".lock")
        manager = (experiment_loop.adopt_host_lock(host, claim, self.holds) if path.exists()
                   else experiment_loop.host_lock(host, self.holds, claim_id=claim))
        with manager as release:
            self.release_hold = release

    def report(self, action, facts, status="succeeded", failure_class=None, observed_at=None):
        if facts is None and (status != "failed" or failure_class not in (
                "runner_lost", "host_interrupted", "controller_unavailable")):
            raise Refused("absent_stage_facts_refused")
        if facts is not None and facts.get("stage") != action["action"]:
            raise Refused("report_stage_mismatch")
        record = {"facts": facts, "status": status, "failure_class": failure_class,
                  "observed_at": observed_at or utc(self.clock())}
        if status != "progress":
            self.state["completed"][self.key(action)] = record
        self.state["pending_report"] = {"stage": action["action"], **record}
        self.save()
        body = {"schema_version": "carrythrough.release-runner-report.v1",
                "claim_generation": action["claim_generation"], "claim_token": action["claim_token"],
                "stage": action["action"], "stage_attempt": action["stage_attempt"], **record}
        view = self.transport.post("/api/project-loops/release-runs/" + action["run_id"] + "/reports", body)
        current = view["run"]
        if current["id"] != action["run_id"] or current["claim_generation"] != action["claim_generation"]:
            raise StaleFence("report_response_fence_changed")
        self.state.pop("pending_report", None)
        self.save()
        return current

    def permission(self, action, facts):
        current = self.report(action, facts, "progress")
        if (current["state"] != "active" or current["stage"] != action["action"]
                or current["stage_attempt"] != action["stage_attempt"]):
            raise StaleFence("stage_no_longer_assigned")
        if self.clock() >= timestamp(current["lease_expires_at"]):
            raise StaleFence("report_response_lease_expired")
        if self.clock() >= timestamp(action["stage_deadline_at"]):
            raise Refused("stage_deadline_elapsed")

    def handle_prepare(self, action):
        self.native.worktree(self.work(), self.config["tooling_commit"])
        refs = self.native.prepare(self.work(), action["spec"])
        raw = bounded(self.profile())
        profile = parse(raw)
        if invariant_digest(profile) not in action["spec"]["recipe"]["invariant_sha256"]:
            raise Refused("recipe_invariant_changed")
        self.state["native_refs"].update(refs)
        self.save()
        self.report(action, {"stage": "prepare", "profile_b64": encoded(raw), **refs})

    def handle_source_check(self, action):
        assets = []
        for role in ("engine", "client"):
            source = action["spec"][role]
            for asset in source["assets"]:
                path = self.native.asset(source, asset)
                if sha256_file(path) != asset["digest"].removeprefix("sha256:") or path.stat().st_size != asset["size"]:
                    raise Refused("asset_digest_mismatch")
                if asset["name"].endswith(".tar.gz"):
                    from omp_strata.engine_component import inspect_archive
                    inspect_archive(path, {"sha256": sha256_file(path), "bytes": path.stat().st_size,
                                           "file": asset["name"]})
                    layout = "tar.gz"
                elif zipfile.is_zipfile(path):
                    with zipfile.ZipFile(path) as archive:
                        if archive.testzip() or not archive.namelist():
                            raise Refused("unrecognized_asset_layout")
                    layout = "zip"
                else:
                    with path.open("rb") as stream:
                        magic = stream.read(4)
                    if magic[:2] == b"MZ" or magic == b"\x7fELF" or magic in (
                            b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
                        layout = "executable"
                    else:
                        raise Refused("unrecognized_asset_layout")
                assets.append({"role": role, "name": asset["name"], "sha256": sha256_file(path),
                               "bytes": path.stat().st_size, "layout": layout})
        self.report(action, {"stage": "source_check", "assets": assets})

    def handle_host_preflight(self, action):
        status = self.controller.call("status")
        resources = status["resources"]
        facts = {"stage": "host_preflight", "native_host": status["host"],
                 "gpu_uuids": [gpu["uuid"] for gpu in resources["gpus"]],
                 "gpu_models": [gpu["model"] for gpu in resources["gpus"]],
                 "idle": resources["unexplained_compute"] == [],
                 "other_tenant": status["reserved"],
                 "free_disk_bytes": shutil.disk_usage(Path(self.config["candidates"]).parent).free,
                 "checkpoint_bytes": shutil.disk_usage(Path(self.config["checkpoint_directory"])).free}
        self.report(action, facts)

    def handle_incumbent_stop(self, action):
        identity, healthy, port = self.native.incumbent()
        generation = identity.pop("run_generation")
        old = self.state.get("incumbent_identity")
        facts = {"stage": "incumbent_stop", "identity": identity,
                 "reservation_receipt": None, "stopped": False}
        mismatch = (identity["profile_id"] != self.config["restoration_ref"]
                    or old is not None and old != identity)
        if old is None:
            self.state["incumbent_identity"] = identity
            self.state["incumbent_launch_before"] = generation
            self.save()
        self.permission(action, facts)
        if mismatch:
            raise Refused("incumbent_mismatch")
        if self.state["mutated"]:
            receipt = self.controller.call("status")
            experiment_loop.check_reservation(receipt, {"host": self.config["host"],
                                                       "generation": receipt["generation"],
                                                       "gpu_uuids": self.config["gpu_uuids"]})
            if port:
                raise Refused("incumbent_stop_unresolved")
            self.state.update(stop_receipt=receipt, stopped_at=receipt["resources"]["observed_utc"])
            self.save()
            self.report(action, {**facts, "reservation_receipt": receipt, "stopped": True})
            return
        if not healthy or not port:
            raise Refused("incumbent_mismatch")
        # Intent is persisted before the controller could stop anything.
        self.state["mutated"] = True
        self.state["mutation_started_at"] = utc(self.clock())
        self.save()
        self.controller.call("use")
        receipt = self.controller.call("status")
        binding = {"host": self.config["host"], "generation": receipt["generation"],
                   "gpu_uuids": self.config["gpu_uuids"]}
        stopped_at = experiment_loop.check_reservation(receipt, binding)
        _, _, listening = self.native.incumbent()
        if listening:
            raise Refused("incumbent_port_open")
        self.state.update(stop_receipt=receipt, stopped_at=stopped_at)
        self.save()
        self.report(action, {**facts, "reservation_receipt": receipt, "stopped": True})

    def qualify_facts(self, phase):
        refs = self.state["native_refs"]
        self.observe_candidate_launch()
        evidence = self.root() / "evidence" / ("requalify-" + refs["native_run_id"])
        summary = evidence / "summary.json"
        rows = document(summary) if summary.exists() else []
        gates = {}
        for gate, steps in requalify.SAME_RUN_STEPS.items():
            selected = [row for row in rows if row["step"] in steps]
            if selected:
                gates[gate] = ("fail" if any(row.get("rc") not in (0, None) or row.get("pass_observed") is False
                                           for row in selected) else
                               "pass" if set(steps) <= {row["step"] for row in selected}
                               and all(row.get("rc") == 0 and row.get("pass_observed") is not False
                                       for row in selected) else "blocked")
        size = sum(p.stat().st_size for p in self.root().rglob("*") if p.is_file() and not p.is_symlink())
        return {"stage": "qualify", "evidence_name": "requalify-" + refs["native_run_id"],
                "launch_id": refs["native_run_id"], "phase": phase,
                "steps": [row["step"] for row in rows], "gates": gates,
                "summary_sha256": sha256_file(summary) if summary.exists() else None,
                "candidate_root_bytes": size, "provider_calls": 0}

    def observe_candidate_launch(self):
        refs = self.state["native_refs"]
        run = self.root() / "state/run.json"
        if run.exists():
            launch = document(run).get("launch_id")
            if launch:
                launches = refs.setdefault("candidate_launch_ids", [])
                if launch not in launches:
                    launches.append(launch)
                    self.save()

    def handle_qualify(self, action):
        refs = self.state["native_refs"]
        if not self.state.get("stop_receipt") or self.state.get("restoration"):
            raise Refused("incumbent_stop_unproved")
        native_id = action["run_id"] + "-a" + str(action["stage_attempt"])
        root = Path(self.config["candidates"]) / native_id
        experiment_loop.candidate_root_guard(root, self.config["incumbent_root"], source_root=self.work())
        if action["profile_sha256"] != sha256_file(self.profile()):
            raise Refused("candidate_profile_changed")
        if refs.get("native_run_id") not in (None, native_id):
            raise Refused("qualification_attempt_changed")
        refs.update(candidate_root=str(root), native_run_id=native_id)
        self.save()
        fence = root / "state/requalify-run.json"
        result = root / "evidence" / ("requalify-" + native_id) / "result.json"
        if fence.exists() and document(fence).get("run_id") != native_id:
            raise Refused("native_fence_mismatch")
        if result.exists():
            terminal = document(result)
            if terminal["run_id"] != native_id:
                raise Refused("native_result_mismatch")
            if terminal.get("finished_utc") is not None and type(terminal.get("rc")) is int:
                refs.update(result_sha256=sha256_file(result), result_error=terminal.get("error"))
                self.save()
                passed = terminal["rc"] == 0 and terminal["completed"] and not terminal["failed"]
                self.report(action, self.qualify_facts("finished"), "succeeded" if passed else "failed",
                            None if passed else "candidate_failed")
                return
        live = self.launcher.live(root, native_id)
        if live:
            refs["last_phase"] = "running"
            self.save()
            self.report(action, self.qualify_facts("running"), "progress")
            return
        # Depends on requalify's persistent fence: absence of a terminal result is not a resumable run.
        if fence.exists() or refs.get("launch_intent"):
            refs["result_error"] = "native process died without finalizing; progress unknown"
            self.save()
            facts = self.qualify_facts(refs.get("last_phase", "launching"))
            self.report(action, facts, "failed", "runner_lost")
            return
        self.native.campaign_status(self.work(), action["spec"], "queued")
        self.native.campaign_status(self.work(), action["spec"], "running")
        facts = self.qualify_facts("launching")
        self.permission(action, facts)
        self.native.fetch(self.work(), self.profile(), root,
                          heartbeat=lambda: self.permission(action, self.qualify_facts("launching")))
        self.permission(action, self.qualify_facts("launching"))
        refs.update(launch_intent=True, last_phase="launching")
        self.save()
        refs["launch_receipt"] = self.launcher.launch(self.work(), self.profile(), root, native_id)
        refs["last_phase"] = "running"
        self.save()
        self.report(action, self.qualify_facts("running"), "progress")

    def stop_candidate(self):
        refs = self.state["native_refs"]
        if "candidate_root" not in refs:
            return True
        experiment_loop.candidate_root_guard(self.root(), self.config["incumbent_root"], source_root=self.work())
        self.observe_candidate_launch()
        if not self.launcher.stop(self.root(), refs["native_run_id"]):
            return False
        stopped = self.native.stop_candidate(self.work(), self.profile(), self.root())
        status = self.controller.call("status")
        resources = status["resources"]
        return (stopped and resources["unexplained_compute"] == []
                and all(0 <= gpu["used_mib"] < experiment_loop.READY_MAX_MIB for gpu in resources["gpus"]))

    def handle_candidate_stop(self, action):
        stopped = self.state.get("candidate_stopped") or self.stop_candidate()
        self.state["candidate_stopped"] = stopped
        self.save()
        self.report(action, {"stage": "candidate_stop", "stopped": stopped},
                    "succeeded" if stopped else "failed", None if stopped else "controller_unavailable")

    def restore(self):
        if self.state.get("restoration"):
            return self.state["restoration"]
        identity, verified, generation = {}, False, None
        try:
            if self.state["mutated"]:
                if not self.state.get("candidate_stopped"):
                    raise Refused("candidate_cleanup_unproved")
                self.controller.call("return")
            identity, healthy, port = self.native.incumbent()
            generation = identity.pop("run_generation")
            status = self.controller.call("status")
            before = self.state.get("incumbent_identity")
            if before is None and not self.state["mutated"]:
                self.state["incumbent_identity"] = before = identity
                self.state["incumbent_launch_before"] = generation
            prior_launch = self.state.get("incumbent_launch_before")
            lineage = (bool(generation) and generation != prior_launch
                       and generation not in self.state["native_refs"].get("candidate_launch_ids", []))
            if not self.state["mutated"]:
                lineage = bool(generation) and generation == prior_launch
            verified = (lineage and healthy and port and identity == before and status["reserved"] is False
                        and status["admission_open"] is True and status["host"] == self.config["host"])
        except (Refused, ControllerUnavailable, OSError, KeyError, subprocess.SubprocessError):
            verified = False
        public = {"schema_version": 1, "verified": verified, "host": self.config["public_host_label"],
                  "profile_id": identity.get("profile_id"),
                  "profile_fingerprint": identity.get("profile_fingerprint"),
                  "runtime_identity_sha256": identity.get("runtime_identity_sha256"),
                  "config_file_sha256": identity.get("config_file_sha256"),
                  "incumbent_launch_before": self.state.get("incumbent_launch_before"),
                  "incumbent_launch_after": generation,
                  "candidate_launch_ids": self.state["native_refs"].get("candidate_launch_ids", []),
                  "checked_at": utc(self.clock())}
        relative = "releases/" + self.state["spec"]["candidate_id"] + "/restored-state.json"
        atomic_write_json(self.work() / relative, public)
        facts = {"stage": "restore", "verified": verified, "identity": identity,
                 "restored_state_ref": relative, "restored_state_sha256": sha256_file(self.work() / relative)}
        self.state.update(restoration=facts, restored_at=self.clock(), incumbent_launch_after=generation)
        self.save()
        return facts

    def handle_restore(self, action):
        facts = self.restore()
        self.report(action, facts, "succeeded" if facts["verified"] else "failed",
                    None if facts["verified"] else "restoration_failed")

    def cleanup(self):
        if not self.state.get("claim_id") or self.state.get("settled") or not self.state.get("mutated"):
            return
        self.hold()
        try:
            self.state["candidate_stopped"] = self.stop_candidate()
        except (Refused, ControllerUnavailable, OSError, KeyError, subprocess.SubprocessError):
            self.state["candidate_stopped"] = False
        self.save()
        self.restore()

    def handle_settle(self, action):
        if not self.state.get("settled"):
            facts = self.restore()
            claim = action["claim"]
            if "usage" not in self.state:
                start = max(math.ceil(timestamp(claim["acquired_at"])),
                            math.ceil(self.state.get("stopped_at", timestamp(
                                self.state.get("mutation_started_at", claim["acquired_at"])))))
                end = max(start, math.ceil(self.state["restored_at"]))
                mutated = self.state["mutated"]
                if not mutated:
                    end = start
                failed = any(row["status"] == "failed" for row in self.state["completed"].values())
                self.state["usage"] = {
                    "schema_version": "carrythrough.fleet-usage.v1", "claim_id": claim["claim_id"],
                    "started_at": utc(start), "ended_at": utc(end),
                    "gpu_seconds": (end - start) * action["spec"]["host"]["gpu_count"],
                    "outcome": "aborted" if end == start else "failed" if failed else "passed",
                    "restoration": {"verified": facts["verified"], "incumbent_ref": claim["restoration_ref"],
                                    "evidence_sha256": facts["restored_state_sha256"]},
                    "evidence_paths": [facts["restored_state_ref"]]}
                self.save()
            path = "/api/project-loops/fleet-claims/" + claim["claim_id"]
            usage_view = self.transport.post(path + "/usage", self.state["usage"])
            if facts["verified"]:
                body = ({} if self.state["mutated"] else
                        {"no_mutation_verified": True, "evidence_sha256": facts["restored_state_sha256"]})
                view = self.transport.post(path + "/release", body)
                if (view["claim"]["claim_id"] != claim["claim_id"]
                        or view["state"] not in ("released", "released_unstarted")
                        or view["restoration_verified"] is not True):
                    raise Refused("release_not_accepted")
                self.hold()
                assert self.release_hold is not None
                self.release_hold()
                self.release_hold = None
                self.state["settled"] = True
                self.save()
            elif usage_view["state"] != "restoration_failed":
                raise Refused("failed_restoration_not_recorded")
        self.report(action, {"stage": "settle"})

    def handle_verify(self, action):
        if not self.state.get("settled") and self.state.get("restoration", {}).get("verified", True):
            raise Refused("custody_not_settled")
        if self.state["native_refs"].get("result_sha256") and not self.state.get("exported"):
            self.native.export(self.work(), self.profile(), self.root(), self.config["tooling_commit"])
            self.state["exported"] = True
            self.save()
        manifest, files = evidence_bundle(self.work() / "releases" / action["spec"]["candidate_id"])
        verified = self.native.verify(self.work(), self.profile())
        verified = (verified and self.state.get("restoration", {}).get("verified", False)
                    and not any(row["status"] == "failed" for row in self.state["completed"].values()))
        self.state["verify_ok"] = verified
        self.save()
        self.report(action, {"stage": "verify", "manifest_b64": manifest, "evidence_files": files,
                             "verify_ok": verified})

    def handle_ledger(self, action):
        status = "qualified" if self.state.get("verify_ok") and self.state.get("settled") else "blocked"
        self.native.campaign_status(self.work(), action["spec"], status,
                                    result="releases/" + action["spec"]["candidate_id"] + "/manifest.json",
                                    restored_state=self.state.get("restoration", {}).get("restored_state_ref"),
                                    note=None if status == "qualified" else "Qualification or restoration unproved.")
        path = self.state["native_refs"]["campaign_path"]
        self.report(action, {"stage": "ledger", "campaign_path": path,
                             "campaign_sha256": sha256_file(self.work() / path)})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="private native binding file")
    parser.add_argument("--token-file", type=Path, required=True, help="owner bearer file; not a token argument")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    config = document(args.config)
    if set(config.get("controller", {})) != {"executable"}:
        raise Refused("controller_configuration_refused")
    native = Native(config["tooling"], config)
    runner = Runner(config, HTTP(config["control_plane_origin"], args.token_file), native,
                    Controller(config["controller"]["executable"], config["host"]), Launcher())
    with runner.lock():
        try:
            while True:
                try:
                    delay = runner.poll()
                except Unreachable:
                    delay = 30
                except StaleFence:
                    delay = 1
                except (Refused, OSError, KeyError, subprocess.SubprocessError):
                    runner.cleanup()
                    raise
                if args.once:
                    return 0
                time.sleep(delay)
        except (KeyboardInterrupt, SystemExit):
            runner.cleanup()
            raise


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        raise SystemExit(main())
    except (Refused, OSError, KeyError, subprocess.SubprocessError):
        print("release runner refused; retained state and custody require inspection", file=sys.stderr)
        raise SystemExit(2)
