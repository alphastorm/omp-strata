"""Candidate profile loading and semantic validation (gate G01).

A profile is the single nonsecret source of truth for one candidate: host expectations, the stock Strata setup
choices, every pinned artifact and the OMP route. Validation rejects anything that could let an unpinned,
placeholder or contradictory value reach an install or a launch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import canonical_json, flag_pairs, is_sha256, read_json, sha256_bytes

SENTINEL = re.compile(r"(?i)\b(RESOLVE_[A-Z0-9_]*|TODO|TBD|FIXME|CHANGEME|PLACEHOLDER|XXX+)\b|<[a-z_ -]+>")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
STATUSES = ("draft", "candidate", "qualified")
CONTEXTS = (8192, 32768, 65536, 131072, 262144)          # stock setup.py CONTEXTS
KV_FORMATS = ("int8", "q4_0", "k8v4")
LOOPBACK = ("127.0.0.1", "::1")
PLATFORMS = ("windows-x64", "darwin-arm64", "linux-x64")
# Capabilities this integration can never claim in v0.1, whatever the evidence.
NEVER_CLAIMED = ("durable_engine_state", "multi_tenant")
# Capabilities that stay off until their own optional gate (G22/G23) is designed and passed.
OPTIONAL_OFF = ("vision", "remote_client")
TUNING_FLAGS = ("--pcie-frac", "--pool-workers", "--spec-min-p-tuned", "--adapt-every")


class ProfileError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Profile:
    path: Path
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.data["profile_id"]

    @property
    def fingerprint(self) -> str:
        """SHA-256 over the canonical profile content (the nonsecret candidate identity)."""
        return sha256_bytes(canonical_json(self.data))

    def omp_artifact(self, platform: str) -> dict[str, Any]:
        return self.data["omp"]["artifacts"][platform]

    def model_url(self, file_entry: dict[str, Any]) -> str:
        m = self.data["model"]
        return f"https://huggingface.co/{m['repository']}/resolve/{m['revision']}/{file_entry['path']}"


def _walk_strings(value: Any, path: str = ""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(value, str):
        yield path, value


def _check_artifact(problems: list[str], where: str, art: Any, *, need_url: bool = True) -> None:
    if not isinstance(art, dict):
        problems.append(f"{where}: missing artifact pin")
        return
    if need_url:
        url = art.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            problems.append(f"{where}.url: must be an https URL")
        elif "/latest/" in url or "/resolve/main/" in url:
            problems.append(f"{where}.url: mutable reference ({url}) is not a pin")
    size = art.get("bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        problems.append(f"{where}.bytes: must be a positive integer")
    if not is_sha256(art.get("sha256")):
        problems.append(f"{where}.sha256: must be 64 lowercase hex characters")
    if not isinstance(art.get("sha256_source"), str) or not art["sha256_source"].strip():
        problems.append(f"{where}.sha256_source: record where the expected digest came from")


def validate(data: Any, *, require_status: str | None = None) -> list[str]:
    """Return every problem found; an empty list means the profile is usable for install/launch."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["profile: must be a JSON object"]
    if data.get("schema_version") != 1:
        problems.append("schema_version: must be 1")
    pid = data.get("profile_id")
    if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,80}", pid or ""):
        problems.append("profile_id: lowercase letters, digits, dots and dashes")
    status = data.get("status")
    if status not in STATUSES:
        problems.append(f"status: one of {STATUSES}")
    elif require_status and STATUSES.index(status) < STATUSES.index(require_status):
        problems.append(f"status: {status} is below the required {require_status}")
    for where, text in _walk_strings(data):
        if SENTINEL.search(text) and not where.endswith("sha256_source"):
            problems.append(f"{where}: unresolved sentinel or placeholder in {text!r}")

    host = data.get("host") or {}
    if host.get("os") not in ("windows", "linux"):
        problems.append("host.os: windows or linux (macOS has no Strata GPU runtime)")
    for key in ("min_gpu_vram_mib", "min_total_ram_gib", "min_available_ram_gib_at_start", "min_driver_major",
                "min_free_disk_gib"):
        v = host.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
            problems.append(f"host.{key}: positive number required")
    if not isinstance(host.get("display_attached", False), bool):
        problems.append("host.display_attached: true or false (whether the GPU also drives a display)")

    server = data.get("server") or {}
    if server.get("listen_host") not in LOOPBACK:
        problems.append("server.listen_host: loopback only (127.0.0.1 or ::1)")
    port = server.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not 1024 < port < 65536:
        problems.append("server.port: an unprivileged TCP port")
    if server.get("api_key_env") != "STRATA_API_KEY":
        problems.append("server.api_key_env: must be STRATA_API_KEY (stock Strata's environment key)")
    if server.get("shared_settings") != "empty":
        problems.append("server.shared_settings: only 'empty' (frozen stock defaults) is supported")
    for key in ("ready_timeout_s", "stop_timeout_s"):
        v = server.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 3600:
            problems.append(f"server.{key}: 1..3600 seconds")

    strata = data.get("strata") or {}
    if not HEX40.match(str(strata.get("commit", ""))):
        problems.append("strata.commit: full 40-hex commit required")
    if not str(strata.get("repository", "")).startswith("https://"):
        problems.append("strata.repository: https URL required")
    setup = strata.get("setup_args") or {}
    ctx = setup.get("context")
    if ctx not in CONTEXTS:
        problems.append(f"strata.setup_args.context: one of stock setup's {CONTEXTS}")
    if setup.get("kv") not in KV_FORMATS:
        problems.append(f"strata.setup_args.kv: one of {KV_FORMATS}")
    if setup.get("vision") not in ("no", "none"):
        problems.append("strata.setup_args.vision: text-only profiles require 'no' until G22 exists")
    if setup.get("experimental_speed_projection") != "off":
        problems.append("strata.setup_args.experimental_speed_projection: must be off")
    if setup.get("low_ram") not in ("on", "off"):
        problems.append("strata.setup_args.low_ram: explicit on/off (auto would depend on the host's free RAM)")
    for key in ("family", "model"):
        if not isinstance(setup.get(key), str) or not setup[key]:
            problems.append(f"strata.setup_args.{key}: required")
    flags = strata.get("expected_engine_flags") or []
    if not isinstance(flags, list) or not flags or not all(isinstance(f, str) for f in flags):
        problems.append("strata.expected_engine_flags: nonempty list of strings")
    else:
        pairs = flag_pairs(flags)
        if pairs.get("--max-context") != str(ctx):
            problems.append("strata.expected_engine_flags: --max-context must equal setup_args.context")
        if isinstance(ctx, int) and ctx > 8192 and pairs.get("--kv") != setup.get("kv"):
            problems.append("strata.expected_engine_flags: --kv must equal setup_args.kv")
        variant = {"--mmap-experts", "--resident-experts"} & set(flags)
        if setup.get("low_ram") == "off" and variant:
            problems.append(f"strata.expected_engine_flags: {sorted(variant)} contradict low_ram off")
        if setup.get("low_ram") == "on" and len(variant) != 1:
            problems.append("strata.expected_engine_flags: low_ram on needs exactly one of --mmap-experts or "
                            "--resident-experts (stock setup's variant)")
        for f in TUNING_FLAGS:
            if f in flags:
                problems.append(f"strata.expected_engine_flags: calibration/tuning flag {f} must stay off")
    forbidden = strata.get("forbidden_engine_flags") or []
    if not isinstance(forbidden, list):
        problems.append("strata.forbidden_engine_flags: list required")
    elif isinstance(flags, list) and set(forbidden) & set(flags):
        problems.append("strata.forbidden_engine_flags overlaps expected_engine_flags")
    if not isinstance(strata.get("model_name"), str) or not strata.get("model_name"):
        problems.append("strata.model_name: the exact served model id is required")
    arts = strata.get("artifacts") or {}
    for key in ("engine_archive", "llama_cpp_archive"):
        _check_artifact(problems, f"strata.artifacts.{key}", arts.get(key))
    lock = strata.get("python_lock")
    if not isinstance(lock, dict):
        problems.append("strata.python_lock: {path, python, sha256} required (hash-locked setup.py packages)")
    else:
        lp = lock.get("path")
        if not isinstance(lp, str) or not lp.startswith("locks/") or ".." in lp.split("/"):
            problems.append("strata.python_lock.path: a repository path under locks/")
        if not re.fullmatch(r"3\.\d{1,2}", str(lock.get("python", ""))):
            problems.append("strata.python_lock.python: the interpreter minor version the lock was resolved for")
        if lock.get("sha256") is None:
            if status != "draft":
                problems.append("strata.python_lock.sha256: only a draft profile may leave the lock unresolved")
        elif not is_sha256(lock.get("sha256")):
            problems.append("strata.python_lock.sha256: 64 hex characters")

    model = data.get("model") or {}
    if not isinstance(model.get("repository"), str) or "/" not in model.get("repository", ""):
        problems.append("model.repository: owner/name required")
    if not HEX40.match(str(model.get("revision", ""))):
        problems.append("model.revision: immutable 40-hex revision required (not a branch)")
    files = model.get("files")
    if not isinstance(files, list) or not files:
        problems.append("model.files: every required shard must be pinned")
    else:
        seen = set()
        for i, f in enumerate(files):
            _check_artifact(problems, f"model.files[{i}]", f, need_url=False)
            p = f.get("path") if isinstance(f, dict) else None
            if not isinstance(p, str) or p.startswith("/") or ".." in p.split("/"):
                problems.append(f"model.files[{i}].path: relative repository path required")
            elif p in seen:
                problems.append(f"model.files[{i}].path: duplicate")
            else:
                seen.add(p)
    mtp = model.get("mtp_source") or {}
    if not HEX40.match(str(mtp.get("revision", ""))):
        problems.append("model.mtp_source.revision: immutable 40-hex revision required")
    tms = mtp.get("tensor_manifest_sha256")
    if tms is not None and not is_sha256(tms):
        problems.append("model.mtp_source.tensor_manifest_sha256: null or 64 hex")

    omp = data.get("omp") or {}
    if not HEX40.match(str(omp.get("source_commit", ""))):
        problems.append("omp.source_commit: full 40-hex commit required")
    arts = omp.get("artifacts") or {}
    if not arts:
        problems.append("omp.artifacts: at least the host platform's stock binary must be pinned")
    for plat, art in arts.items():
        if plat not in PLATFORMS:
            problems.append(f"omp.artifacts.{plat}: unknown platform")
        _check_artifact(problems, f"omp.artifacts.{plat}", art)
    for key, want in (("profile_name", "omp-strata"), ("provider_id", "strata-local")):
        if omp.get(key) != want:
            problems.append(f"omp.{key}: must be {want!r}")
    cw, mt = omp.get("context_window"), omp.get("max_tokens")
    if not isinstance(cw, int) or isinstance(cw, bool) or cw != ctx:
        problems.append("omp.context_window: must equal the configured Strata context")
    if not isinstance(mt, int) or isinstance(mt, bool) or mt < 1024:
        problems.append("omp.max_tokens: at least 1024")
    elif isinstance(cw, int) and mt > cw // 2:
        problems.append("omp.max_tokens: output reserve larger than half the context leaves no usable prompt")

    caps = data.get("capabilities") or {}
    for key in NEVER_CLAIMED:
        if caps.get(key) is not False:
            problems.append(f"capabilities.{key}: must be false in v0.1")
    for key in OPTIONAL_OFF:
        if caps.get(key) is not False:
            problems.append(f"capabilities.{key}: must stay false until its optional gate passes")
    if caps.get("vision") is False and setup.get("vision") not in ("no", "none"):
        problems.append("capabilities.vision false but setup enables the encoder")
    if not caps.get("text") or not caps.get("typed_tools"):
        problems.append("capabilities: text and typed_tools are the reason this profile exists")
    return problems


def load(path: Path, *, require_status: str | None = None) -> Profile:
    data = read_json(path)
    problems = validate(data, require_status=require_status)
    if problems:
        raise ProfileError(problems)
    return Profile(path=path, data=data)
