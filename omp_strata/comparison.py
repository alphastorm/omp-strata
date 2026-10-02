"""Frozen G25 identities, scheduling, evidence arithmetic and fail-closed validation.

No engine lifecycle or model calls live here. Installation paths and secrets belong
only to private bindings, never to the immutable public-capable plan.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
from collections import Counter
from collections.abc import Mapping, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

ROOT = Path(__file__).resolve().parents[1]
TASK_IDS = ("bugfix-a", "bugfix-b", "multifile-regression", "tool-loop", "long-context", "continuation")
ARMS = ("strata", "ninfer")
HARNESS_FILES = ("scripts/compare_g25.py", "omp_strata/comparison.py", "omp_strata/comparison_ompcfg.py")
ABORT_REASONS = ("frozen_evaluation_modified", "harness_modified", "wrong_endpoint_identity",
                 "concurrent_gpu_owner", "route_escape", "credential_exposure", "unsafe_workspace",
                 "controller_failure", "switch_failure", "host_state_drift", "consecutive_oom",
                 "comparison_wall_cap", "interrupted", "observation_unavailable")
DEFAULT_CLAIM_POLICY = {
    "min_completion_delta": 3, "min_joint_successes": 12,
    "max_median_task_wall_ratio": 0.80, "max_all_attempt_wall_ratio": 1.0,
    "completion_wording": "higher verified completion count in this batch",
    "speed_wording": "faster on jointly successful paired attempts in this batch",
}
CONFOUNDERS = ("engine", "model", "quantization", "API/client-adapter", "matched scheduled attempts, not seed-controlled trials")
SHA = re.compile(r"[0-9a-f]{64}\Z")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,119}\Z")


class ComparisonError(ValueError):
    """Refuse a comparison whose identity, boundary or evidence is not established."""


@dataclass(frozen=True)
class ArmLaunch:
    argv: list[str]
    env: dict[str, str]
    home: Path
    config_sha256: str
    models_sha256: str
    endpoint: dict


class ArmAdapter(Protocol):
    arm: str

    def preflight(self) -> dict: ...

    def prepare(self, attempt_root: Path) -> ArmLaunch: ...


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def canonical(value) -> bytes:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    from omp_strata.common import sha256_file
    return sha256_file(path)


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class ComparisonPlan(Mapping):
    _data: Mapping
    sha256: str

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self) -> Iterator:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def as_dict(self) -> dict:
        return _plain(self._data)


def plan_digest(plan) -> str:
    return sha256(canonical(plan))


def pilot_contract_digest(plan) -> str:
    return plan_digest({key: value for key, value in plan.items() if key not in {"state", "pilot"}})


def read_json(path: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ComparisonError("duplicate JSON object key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ComparisonError("non-finite JSON number")

    try:
        result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                            parse_constant=invalid_constant)
    except (OSError, ValueError) as exc:
        raise ComparisonError("cannot read valid comparison JSON") from exc
    if not isinstance(result, dict):
        raise ComparisonError("comparison JSON must be an object")
    return result


def schedule() -> list[dict]:
    return [{"window": i + 1, "arm": arm, "attempt_number": i // 2 + 1,
             "task_order": list(TASK_IDS[(i // 2) * 2:] + TASK_IDS[:(i // 2) * 2])}
            for i, arm in enumerate(("strata", "ninfer", "ninfer", "strata", "strata", "ninfer"))]


def scheduled_slots() -> list[dict]:
    return [{"window": window["window"], "arm": window["arm"],
             "attempt_number": window["attempt_number"], "task_id": task}
            for window in schedule() for task in window["task_order"]]


def frozen_evaluation() -> dict:
    manifest_path = ROOT / "eval/tasks.json"
    manifest = read_json(manifest_path)
    return {"evaluation_version": manifest["evaluation_version"], "manifest_sha256": file_sha256(manifest_path),
            "evaluator_sha256": file_sha256(ROOT / "scripts/evaluate.py"), "task_ids": list(TASK_IDS),
            "attempts_per_task": 3, "budgets": {task["id"]: task["budget"] for task in manifest["tasks"]}}


def harness_identity() -> dict:
    return {name: file_sha256(ROOT / name) for name in HARNESS_FILES}


def _public_errors(value, prefix="") -> list[str]:
    errors = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else key
            if re.search(r"(?:api_key|password|secret|hostname|serial|uuid|private_path|key_file)", key, re.I):
                errors.append(f"{name}: private field is forbidden")
            errors.extend(_public_errors(item, name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            errors.extend(_public_errors(item, prefix))
    elif isinstance(value, str):
        if (re.search(r"(?:^|\s)(?:/|~[/\\]|[A-Za-z]:[\\/])", value)
                or re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b|https?://|Bearer\s|sk-[A-Za-z0-9]", value)
                or "\\" in value or "@" in value):
            errors.append(f"{prefix}: public data contains an address, credential or private path")
    return errors


def _keys(obj, required, name, errors, optional=()):
    if not isinstance(obj, Mapping):
        errors.append(f"{name}: object required")
        return False
    missing = set(required) - set(obj)
    extra = set(obj) - set(required) - set(optional)
    if missing or extra:
        errors.append(f"{name}: unexpected or missing fields ({', '.join(sorted(missing | extra))})")
    return True


def _hash(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _number(value, minimum=0):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= minimum


def validate_plan(plan, *, finalized=True, check_runtime=False) -> list[str]:
    errors = _public_errors(plan)
    required = {"schema_version", "comparison_id", "comparison_class", "state", "evaluation", "omp", "strata",
                "ninfer", "host", "schedule", "claim_policy", "claims", "harness", "pilot"}
    if not _keys(plan, required, "plan", errors):
        return errors
    if plan.get("schema_version") != 1 or plan.get("comparison_class") != "same_host_product_route":
        errors.append("unsupported comparison schema or class")
    if not isinstance(plan.get("comparison_id"), str) or not SAFE_ID.fullmatch(plan["comparison_id"]):
        errors.append("comparison_id must be a neutral safe identifier")
    if plan.get("state") not in {"draft", "frozen"} or (finalized and plan.get("state") != "frozen"):
        errors.append("a frozen plan is required")
    if plan.get("claims") != {"engine_only_comparison": False}:
        errors.append("engine_only_comparison must remain false")
    if _plain(plan.get("evaluation")) != frozen_evaluation():
        errors.append("evaluation must exactly match the frozen G24 tasks and budgets")
    omp = plan.get("omp", {})
    if not isinstance(omp, Mapping):
        return errors + ["omp: object required"]
    if _keys(omp, ("platform", "version", "bytes", "sha256"), "omp", errors):
        if finalized and (not _hash(omp.get("sha256")) or type(omp.get("bytes")) is not int or omp["bytes"] <= 0):
            errors.append("OMP executable size and hash must be resolved")
    for arm in ARMS:
        fields = {"model_id", "model_identity_sha256", "quantization", "runtime_identity_sha256", "api", "provider"}
        fields |= ({"profile_id", "profile_fingerprint", "release_manifest_sha256"} if arm == "strata" else
                   {"lane", "release_id", "manifest_sha256", "config_identity_sha256"})
        identity = plan.get(arm, {})
        if not _keys(identity, fields, arm, errors):
            continue
        api = "openai-completions" if arm == "strata" else "openai-responses"
        lane = identity.get("lane")
        provider = "strata-local" if arm == "strata" else {"rtx3090-native": "ninfer-native-3090",
                    "rtx4090-native": "ninfer-native-4090"}.get(lane if isinstance(lane, str) else None)
        if identity.get("api") != api or provider is None or identity.get("provider") != provider:
            errors.append(f"{arm}: only the selected documented native route is permitted")
        if finalized:
            for key in fields:
                value = identity.get(key)
                if key.endswith("sha256") or key == "profile_fingerprint":
                    valid = _hash(value)
                else:
                    valid = isinstance(value, str) and bool(value.strip()) and value.lower() not in {"unknown", "tbd", "unresolved"}
                if not valid:
                    errors.append(f"{arm}.{key}: resolved identity required")
    if finalized:
        for key in ("platform", "version"):
            if not isinstance(omp.get(key), str) or not omp[key].strip() or omp[key].lower() in {"unknown", "tbd", "unresolved"}:
                errors.append(f"omp.{key}: resolved identity required")
    host = plan.get("host", {})
    host_fields = ("label", "os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy",
                   "min_ram_gib", "min_available_ram_gib", "min_commit_headroom_gib", "min_disk_gib")
    if _keys(host, host_fields, "host", errors):
        if host.get("label") not in {"rtx3090-win-a", "rtx4090-win-a", "rtx5090-win-a"}:
            errors.append("host.label must be a neutral documented label")
        for key in host_fields[1:]:
            value = host.get(key)
            if key.startswith("min_") or key == "vram_mib":
                if not _number(value) or (key in {"min_ram_gib", "vram_mib"} and value == 0):
                    errors.append(f"host.{key}: measured requirement must be numeric")
            elif finalized and (not isinstance(value, str) or not value.strip() or value.lower() in {"unknown", "tbd"}):
                errors.append(f"host.{key}: resolved identity required")
    expected_schedule = {"windows": schedule(), "total_wall_seconds": 40000,
                         "switch_timeout_seconds": 300, "abort_policy": list(ABORT_REASONS)}
    if _plain(plan.get("schedule")) != expected_schedule:
        errors.append("schedule must be the frozen S-N-N-S-S-N schedule and abort policy")
    policy = plan.get("claim_policy", {})
    if _keys(policy, DEFAULT_CLAIM_POLICY, "claim_policy", errors):
        for key in ("min_completion_delta", "min_joint_successes"):
            if type(policy.get(key)) is not int or policy[key] < DEFAULT_CLAIM_POLICY[key]:
                errors.append(f"claim_policy.{key}: cannot weaken the predeclared threshold")
        for key in ("max_median_task_wall_ratio", "max_all_attempt_wall_ratio"):
            if not _number(policy.get(key)) or not 0 < policy[key] <= DEFAULT_CLAIM_POLICY[key]:
                errors.append(f"claim_policy.{key}: cannot weaken the predeclared threshold")
        for key in ("completion_wording", "speed_wording"):
            if policy.get(key) != DEFAULT_CLAIM_POLICY[key]:
                errors.append(f"claim_policy.{key}: wording is limited to this batch")
    harness = plan.get("harness", {})
    if not isinstance(harness, Mapping) or set(harness) != set(HARNESS_FILES) or not all(_hash(v) for v in harness.values()):
        errors.append("all comparison harness hashes are required")
    elif check_runtime and _plain(harness) != harness_identity():
        errors.append("comparison harness hash drift")
    pilot = plan.get("pilot")
    if finalized:
        if not isinstance(pilot, Mapping) or set(pilot) != {"strata_sha256", "ninfer_sha256", "execution_boundary"}:
            errors.append("both non-scored pilot records must be bound before freezing")
        elif not all(_hash(pilot.get(f"{arm}_sha256")) for arm in ARMS) or pilot.get("execution_boundary") not in {"host_free", "evaluation"}:
            errors.append("invalid pilot identity or boundary")
    elif pilot is not None:
        errors.append("draft plan cannot claim frozen pilots")
    return errors


def load_plan(path: Path, *, finalized=True, check_runtime=False) -> ComparisonPlan:
    data = read_json(Path(path))
    errors = validate_plan(data, finalized=finalized, check_runtime=check_runtime)
    if errors:
        raise ComparisonError("; ".join(errors))
    return ComparisonPlan(_freeze(data), plan_digest(data))


def new_plan(identities: Mapping, comparison_id: str) -> dict:
    return {"schema_version": 1, "comparison_id": comparison_id, "comparison_class": "same_host_product_route",
            "state": "draft", "evaluation": frozen_evaluation(),
            **{key: _plain(identities[key]) for key in ("omp", "strata", "ninfer", "host")},
            "schedule": {"windows": schedule(), "total_wall_seconds": 40000, "switch_timeout_seconds": 300,
                         "abort_policy": list(ABORT_REASONS)}, "claim_policy": dict(DEFAULT_CLAIM_POLICY),
            "claims": {"engine_only_comparison": False}, "harness": harness_identity(), "pilot": None}


def load_bindings(path: Path, plan) -> dict:
    path = Path(path)
    data = read_json(path)
    errors = []
    if os.name != "nt" and path.stat().st_mode & 0o077:
        errors.append("private bindings must be owner-only (mode 0600)")
    if not _keys(data, ("schema_version", "comparison_id", "comparison_root", "omp_binary", "strata", "ninfer",
                       "host_probe_argv", "execution_boundary"), "bindings", errors):
        raise ComparisonError("; ".join(errors))
    if data.get("schema_version") != 1 or data.get("comparison_id") != plan["comparison_id"]:
        errors.append("bindings comparison identity mismatch")
    if data.get("execution_boundary") not in {"host_free", "evaluation"}:
        errors.append("bindings execution boundary is required")
    for key in ("comparison_root", "omp_binary"):
        if not isinstance(data.get(key), str) or not Path(data[key]).is_absolute():
            errors.append(f"bindings.{key} must be an absolute private path")
    probe = data.get("host_probe_argv")
    if not isinstance(probe, list) or not probe or not all(isinstance(v, str) and v for v in probe):
        errors.append("bindings.host_probe_argv must name a read-only host observation command")
    for arm in ARMS:
        fields = {"root", "key_file", "port", "profile", "manifest"} if arm == "strata" else {"root", "key_file", "port", "controller", "state_root", "status_file", "manifest"}
        binding = data.get(arm, {})
        if not _keys(binding, fields, arm, errors):
            continue
        if type(binding.get("port")) is not int or not 0 < binding["port"] < 65536:
            errors.append(f"{arm}: invalid loopback port")
        for key in fields - {"port"}:
            if not isinstance(binding.get(key), str) or not Path(binding[key]).is_absolute():
                errors.append(f"{arm}.{key}: absolute private path required")
        if any(not isinstance(binding.get(key), str) for key in fields - {"port"}):
            continue
        root = Path(binding["root"]).resolve()
        for key in fields - {"port", "root", "profile", "status_file", "manifest"}:
            if not Path(binding[key]).resolve().is_relative_to(root):
                errors.append(f"{arm}.{key}: path escapes declared installation")
        if not root.is_dir():
            errors.append(f"{arm}: declared installation is absent")
        for key in fields - {"port", "root", "state_root"}:
            if not Path(binding[key]).is_file():
                errors.append(f"{arm}.{key}: required private file is absent")
    if not errors:
        comparison_root = Path(data["comparison_root"]).resolve()
        if comparison_root.is_relative_to(ROOT) or ROOT.is_relative_to(comparison_root):
            errors.append("private comparison artifacts must be outside the repository")
        homes = [Path.home() / ".omp", *[Path(data[arm]["root"]).resolve() for arm in ARMS]]
        if any(comparison_root == forbidden or comparison_root.is_relative_to(forbidden) or forbidden.is_relative_to(comparison_root)
               for forbidden in homes):
            errors.append("comparison root must be separate from both installations and default OMP HOME")
        if not Path(data["omp_binary"]).is_file():
            errors.append("pinned OMP binary is absent")
        if not Path(data["ninfer"]["status_file"]).resolve().is_relative_to(comparison_root):
            errors.append("normalized read-only Status capture must live in the private comparison root")
    if errors:
        raise ComparisonError("; ".join(errors))
    return data


def verify_omp_binary(path: Path, plan) -> None:
    if path.stat().st_size != plan["omp"]["bytes"] or file_sha256(path) != plan["omp"]["sha256"]:
        raise ComparisonError("wrong_endpoint_identity: pinned OMP executable changed")


def missing_value(record, field, errors, *, minimum=0):
    value = record.get(field)
    reasons = record.get("missing_reasons", {})
    if field not in record:
        errors.append(f"{field}: explicit measurement or null required")
    elif value is None:
        if not isinstance(reasons, Mapping) or not isinstance(reasons.get(field), str) or not reasons[field].strip():
            errors.append(f"{field}: null requires a missingness reason")
    elif not _number(value, minimum):
        errors.append(f"{field}: nonnegative finite measurement required")
    elif field in reasons:
        errors.append(f"{field}: present value cannot have a missingness reason")


def validate_host_observation(observation, plan, arm) -> list[str]:
    errors = _public_errors(observation)
    required = {"host", "ram_gib", "available_ram_gib", "commit_headroom_gib", "disk_gib", "gpu_owners",
                "process_condition", "file_cache_condition", "startup_ms", "switch_ms", "network_observation_sha256",
                "route_escape", "credential_exposure", "controller_ok", "missing_reasons"}
    if not _keys(observation, required, "observation", errors):
        return errors
    if not isinstance(observation.get("missing_reasons"), Mapping):
        return errors + ["observation missing_reasons must be an object"]
    host_fields = ("label", "os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy")
    expected = {key: plan["host"][key] for key in host_fields}
    if observation.get("host") != expected:
        errors.append("host_state_drift")
    for field in ("ram_gib", "available_ram_gib", "commit_headroom_gib", "disk_gib"):
        value = observation.get(field)
        if not _number(value) or value < plan["host"][f"min_{field}"]:
            errors.append("host_state_drift")
    if observation.get("gpu_owners") != [arm]:
        errors.append("concurrent_gpu_owner")
    if observation.get("process_condition") != "process-cold" or observation.get("file_cache_condition") not in {"cold", "warm", "unknown"}:
        errors.append("host_state_drift")
    if observation.get("file_cache_condition") == "unknown" and not observation.get("missing_reasons", {}).get("file_cache_condition"):
        errors.append("file cache missingness reason required")
    for field in ("startup_ms", "switch_ms"):
        missing_value(observation, field, errors)
        if observation.get(field) is None:
            errors.append("switch_failure")
    if _number(observation.get("switch_ms")) and observation["switch_ms"] > plan["schedule"]["switch_timeout_seconds"] * 1000:
        errors.append("switch_failure")
    if not _hash(observation.get("network_observation_sha256")):
        errors.append("observation_unavailable")
    for flag, reason, expected_value in (("route_escape", "route_escape", False),
                                        ("credential_exposure", "credential_exposure", False),
                                        ("controller_ok", "controller_failure", True)):
        if observation.get(flag) is not expected_value:
            errors.append(reason)
    return list(dict.fromkeys(errors))


def _base_record(record, plan, kind):
    if not isinstance(record, Mapping):
        return ["record must be an object"]
    from omp_strata.receipts import schema_errors
    schema = read_json(ROOT / "schemas/comparison.schema.json")["$defs"][kind]
    errors = schema_errors(_plain(record), schema)
    if record.get("schema_version") != 1 or record.get("record_type") != kind:
        errors.append("unsupported record type/version")
    if record.get("comparison_id") != plan["comparison_id"] or record.get("plan_sha256") != plan_digest(plan):
        errors.append("record plan identity mismatch")
    return errors


def validate_attempt(record, plan) -> list[str]:
    errors = _base_record(record, plan, "attempt")
    if errors:
        return errors
    slot = {key: record.get(key) for key in ("task_id", "attempt_number", "arm", "window")}
    if slot not in scheduled_slots():
        errors.append("attempt does not occupy a scheduled slot")
    if record.get("status") not in {"complete", "incomplete", "undispatched"} or type(record.get("verified_pass")) is not bool:
        errors.append("attempt status/verdict required")
    for field in ("task_wall_ms", "reported_output_tokens", "request_wall_ms", "server_time_ms", "tool_calls", "compactions"):
        missing_value(record, field, errors)
    manifest = read_json(ROOT / "eval/tasks.json")
    task = next((item for item in manifest["tasks"] if item["id"] == record.get("task_id")), None)
    if task:
        for key in ("workspace_sha256", "prompt_sha256", "verifier_sha256"):
            if record.get(key) != task[key]:
                errors.append(f"attempt frozen {key} mismatch")
    if record.get("omp_binary_sha256") != plan["omp"]["sha256"]:
        errors.append("attempt OMP hash mismatch")
    for key in ("config_sha256", "models_sha256"):
        if record.get(key) is None:
            if not record.get("missing_reasons", {}).get(key):
                errors.append(f"{key}: null requires reason")
        elif not _hash(record[key]):
            errors.append(f"{key}: hash required")
    protocol = record.get("protocol_errors")
    if not isinstance(protocol, Mapping) or not all(type(v) is int and v >= 0 for v in protocol.values()):
        errors.append("protocol error counts required")
        protocol = {"invalid": 1}
    phases = record.get("phases", [])
    if not isinstance(phases, (list, tuple)):
        errors.append("phase records required")
        phases = []
    else:
        for phase in phases:
            if not isinstance(phase, Mapping) or not _number(phase.get("wall_ms")):
                errors.append("valid phase timing required")
    if not isinstance(record.get("verifier"), Mapping) or not isinstance(record.get("transcripts"), (list, tuple)) or not isinstance(record.get("artifacts"), (list, tuple)):
        return errors + ["verifier and artifact records are required"]
    if errors:
        return errors
    for flag in ("timeout", "oom_observed", "unsafe_workspace"):
        if type(record.get(flag)) is not bool:
            errors.append(f"{flag}: observed boolean required")
    if record.get("verified_pass"):
        valid = (record.get("status") == "complete" and not record.get("abort_reason") and not record.get("timeout")
                 and not record.get("unsafe_workspace") and not any(protocol.values())
                 and record.get("verifier", {}).get("passed") is True and record.get("verifier_exit_code") == 0
                 and task and len(phases) == task["phases"] and bool(record.get("transcripts"))
                 and _number(record.get("task_wall_ms")) and record["task_wall_ms"] <= task["budget"]["wall_seconds"] * 1000
                 and _number(record.get("tool_calls")) and record["tool_calls"] <= task["budget"]["tool_calls"]
                 and (record.get("reported_output_tokens") is None or record["reported_output_tokens"] <= task["budget"]["total_output_tokens"])
                 and all(phase.get("exit_code") == 0 and phase.get("completed") is True and not phase.get("abort_reason") for phase in phases))
        if not valid:
            errors.append("verified_pass violates the frozen G24 verifier/budget/protocol boundary")
    if record.get("status") != "complete" and (record.get("verified_pass") or not record.get("abort_reason")):
        errors.append("incomplete/undispatched attempts must retain a failed outcome and reason")
    for ref in record.get("artifacts", []) + record.get("transcripts", []):
        if not isinstance(ref, Mapping) or not _hash(ref.get("sha256")) or not isinstance(ref.get("path"), str):
            errors.append("private artifact reference needs path and hash")
        elif Path(ref["path"]).is_absolute() or ".." in Path(ref["path"]).parts or "\\" in ref["path"]:
            errors.append("private artifact reference escapes its attempt")
    return errors


def validate_window(record, plan) -> list[str]:
    errors = _base_record(record, plan, "window")
    if errors:
        return errors
    number = record.get("window")
    expected = next((row for row in schedule() if row["window"] == number), None)
    if expected is None:
        return errors + ["invalid window number"]
    if record.get("arm") != expected["arm"] or record.get("attempt_number") != expected["attempt_number"]:
        errors.append("window schedule identity mismatch")
    if record.get("status") not in {"complete", "incomplete"}:
        errors.append("invalid window status")
    if record.get("execution_boundary") not in {"evaluation", "host_free"}:
        errors.append("window execution boundary required")
    if record.get("omp_binary_sha256") != plan["omp"]["sha256"]:
        errors.append("window OMP hash mismatch")
    host_fields = ("label", "os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy")
    if record.get("host") != {key: plan["host"][key] for key in host_fields}:
        errors.append("window host identity differs from the plan")
    observations = record.get("observations", [])
    if not isinstance(observations, (list, tuple)):
        errors.append("window observations must be a sequence")
        observations = []
    for observation in observations:
        errors.extend(validate_host_observation(observation, plan, expected["arm"]))
    refs = record.get("attempts", [])
    if not isinstance(refs, (list, tuple)) or not all(isinstance(row, Mapping) for row in refs):
        return errors + ["attempt references required"]
    if [row.get("task_id") for row in refs] != expected["task_order"][:len(refs)] or len(refs) > 6:
        errors.append("window attempt references are out of order or duplicated")
    for row in refs:
        if not _hash(row.get("sha256")) or row.get("attempt_number") != expected["attempt_number"]:
            errors.append("window attempt hash/number mismatch")
    if record.get("status") == "complete":
        if len(refs) != 6:
            errors.append("finalized window needs all six outcomes, including failures")
        if record.get("exclusive_gpu") is not True and not record.get("abort_reason"):
            errors.append("complete window lacks exclusive GPU observation")
        if not record.get("ended_utc"):
            errors.append("complete window needs an end timestamp")
        if not record.get("abort_reason") and len(observations) < 7:
            errors.append("complete exclusive window needs a pre-dispatch observation for each attempt and a final observation")
    elif not record.get("abort_reason"):
        errors.append("incomplete window must state why it is incomplete")
    for field in ("startup_ms", "switch_ms"):
        missing_value(record, field, errors)
    for arm in ARMS:
        if record.get("identities", {}).get(arm) != _plain(plan[arm]):
            errors.append("window route/runtime identity mismatch")
    return errors


def claim_decision(plan, *, complete, arms, outcome_counts, joint_ratios) -> dict:
    policy = plan["claim_policy"]
    strata, ninfer = arms["strata"], arms["ninfer"]
    median_ratio = statistics.median(joint_ratios) if joint_ratios else None
    all_known = all(arms[arm]["all_attempt_wall_ms"] is not None for arm in ARMS)
    higher = bool(complete and strata["verified_passes"] - ninfer["verified_passes"] >= policy["min_completion_delta"]
                  and outcome_counts["strata_only"] > outcome_counts["ninfer_only"])
    faster = bool(complete and len(joint_ratios) >= policy["min_joint_successes"]
                  and median_ratio <= policy["max_median_task_wall_ratio"] and all_known
                  and strata["all_attempt_wall_ms"] <= ninfer["all_attempt_wall_ms"] * policy["max_all_attempt_wall_ratio"])
    factual = None
    if complete:
        factual = (f"On the fixed 18-attempt-per-arm, same-host batch ({plan['host']['label']}), Strata completed "
                   f"{strata['verified_passes']}/18 and NInfer completed {ninfer['verified_passes']}/18; failures remain "
                   f"in both denominators. Strata: {plan['strata']['model_id']}, {plan['strata']['quantization']}, "
                   f"{plan['strata']['api']}; NInfer: {plan['ninfer']['model_id']}, {plan['ninfer']['quantization']}, "
                   f"{plan['ninfer']['api']}.")
    return {"engine_only_comparison": False, "factual_sentence": factual,
            "higher_verified_completion_count": higher, "faster_joint_successes": faster,
            "completion_sentence": f"Strata had {policy['completion_wording']}." if higher else None,
            "speed_sentence": f"Strata was {policy['speed_wording']}." if faster else None,
            "joint_timed_successes": len(joint_ratios), "median_task_wall_ratio": median_ratio,
            "missing_reasons": {"median_task_wall_ratio": "no jointly successful timed pairs"} if median_ratio is None else {}}


def summarize_records(plan, windows: list[dict], attempts: list[dict]) -> dict:
    if len(windows) != 6 or sorted(w.get("window", 0) for w in windows) != list(range(1, 7)):
        raise ComparisonError("summarize requires all six distinct window records")
    windows = sorted(windows, key=lambda row: row["window"])
    errors = [error for window in windows for error in validate_window(window, plan)]
    errors.extend(error for attempt in attempts for error in validate_attempt(attempt, plan))
    by_slot = {(row["task_id"], row["attempt_number"], row["arm"]): row for row in attempts}
    if len(attempts) != 36 or len(by_slot) != 36:
        errors.append("all 36 scheduled outcomes are required; duplicates cannot replace failures")
    for window in windows:
        for ref in window["attempts"]:
            attempt = by_slot.get((ref["task_id"], ref["attempt_number"], window["arm"]))
            if attempt is None or sha256(canonical(attempt) + b"\n") != ref["sha256"]:
                errors.append("window attempt-result hash mismatch")
    if errors:
        raise ComparisonError("; ".join(errors))
    pairs, ratios = [], []
    outcomes = Counter({key: 0 for key in ("both_pass", "strata_only", "ninfer_only", "both_fail")})
    for number in range(1, 4):
        for task_id in TASK_IDS:
            strata, ninfer = (by_slot[(task_id, number, arm)] for arm in ARMS)
            outcome = ("both_pass" if strata["verified_pass"] and ninfer["verified_pass"] else
                       "strata_only" if strata["verified_pass"] else "ninfer_only" if ninfer["verified_pass"] else "both_fail")
            outcomes[outcome] += 1
            valid = (strata["status"] == ninfer["status"] == "complete" and
                     _number(strata["task_wall_ms"]) and _number(ninfer["task_wall_ms"]))
            delta = strata["task_wall_ms"] - ninfer["task_wall_ms"] if valid else None
            ratio = strata["task_wall_ms"] / ninfer["task_wall_ms"] if valid and ninfer["task_wall_ms"] > 0 else None
            if outcome == "both_pass" and ratio is not None:
                ratios.append(ratio)
            pairs.append({"task_id": task_id, "attempt_number": number,
                          "strata_sha256": sha256(canonical(strata) + b"\n"), "ninfer_sha256": sha256(canonical(ninfer) + b"\n"),
                          "outcome": outcome, "task_wall_delta_ms": delta, "task_wall_ratio": ratio,
                          "missing_reasons": {**({"task_wall_delta_ms": "incomplete or unavailable task timing"} if delta is None else {}),
                                              **({"task_wall_ratio": "incomplete, unavailable or zero denominator timing"} if ratio is None else {})}})
    arms = {}
    for arm in ARMS:
        rows = [row for row in attempts if row["arm"] == arm]
        times = [row["task_wall_ms"] for row in rows if row["task_wall_ms"] is not None]
        success_times = [row["task_wall_ms"] for row in rows if row["verified_pass"]]
        missing = 18 - len(times)
        arms[arm] = {"scheduled_attempts": 18, "verified_passes": sum(row["verified_pass"] for row in rows),
                     "failed_attempts": sum(not row["verified_pass"] for row in rows),
                     "all_attempt_wall_ms": sum(times) if not missing else None,
                     "observed_attempt_wall_ms": sum(times) if times else None, "missing_wall_attempts": missing,
                     "success_only_median_wall_ms": statistics.median(success_times) if success_times else None,
                     "protocol_errors": dict(sum((Counter(row["protocol_errors"]) for row in rows), Counter())),
                     "interventions": sum(row["status"] != "complete" or bool(row["abort_reason"]) for row in rows),
                     "missing_reasons": {**({"all_attempt_wall_ms": f"{missing} scheduled attempts have unavailable timing"} if missing else {}),
                                         **({"observed_attempt_wall_ms": "no attempt timing observed"} if not times else {}),
                                         **({"success_only_median_wall_ms": "no verified successes"} if not success_times else {})}}
    resources, cache_conditions = {}, {}
    for arm in ARMS:
        observed = [sample for window in windows if window["arm"] == arm for sample in window.get("observations", [])]
        values = {field + "_minimum": min(sample[field] for sample in observed) if observed else None
                  for field in ("ram_gib", "available_ram_gib", "commit_headroom_gib", "disk_gib")}
        resources[arm] = {**values, "samples": len(observed), "method": "operator read-only host probe",
                          "missing_reasons": {field: "no host sample observed" for field, value in values.items() if value is None}}
        cache_conditions[arm] = sorted({sample["file_cache_condition"] for sample in observed})
    aborts = [{"window": w["window"], "reason": w["abort_reason"]} for w in windows if w.get("abort_reason")]
    hosts_match = all(w.get("host") == windows[0].get("host") for w in windows)
    boundary = windows[0]["execution_boundary"]
    complete = (not aborts and hosts_match and all(w["status"] == "complete" and w.get("exclusive_gpu") is True
                                                 and w["execution_boundary"] == boundary for w in windows))
    refs = [{"window": w["window"], "sha256": sha256(canonical(w) + b"\n")} for w in windows]
    ordered = [ref["sha256"] for ref in refs] + [sha256(canonical(by_slot[(s["task_id"], s["attempt_number"], s["arm"])]) + b"\n") for s in scheduled_slots()]
    return {"schema_version": 1, "record_type": "paired_summary", "comparison_id": plan["comparison_id"],
            "plan_sha256": plan_digest(plan), "comparison_class": "same_host_product_route",
            "execution_boundary": boundary, "complete": complete, "attempts_per_arm": 18, "paired_attempts": 18,
            "scheduled_attempts": 36, "pairs": pairs, "outcome_counts": dict(outcomes), "windows": refs,
            "ordered_records_sha256": sha256(canonical(ordered)), "arms": arms, "host": windows[0].get("host"),
            "aborts": aborts, "confounders": list(CONFOUNDERS), "resources": resources,
            "cache": {"file_cache_conditions": cache_conditions, "server_cache_hits": None,
                      "method": "operator process/file-cache observation; no server cache counter measurement",
                      "missing_reasons": {"server_cache_hits": "not independently observed"}},
            "claims": claim_decision(plan, complete=complete and boundary == "evaluation", arms=arms,
                                     outcome_counts=outcomes, joint_ratios=ratios)}


def validate_summary(record, plan) -> list[str]:
    errors = _base_record(record, plan, "paired_summary")
    if errors:
        return errors
    if record.get("comparison_class") != "same_host_product_route" or record.get("attempts_per_arm") != 18 or record.get("paired_attempts") != 18 or record.get("scheduled_attempts") != 36:
        errors.append("summary must retain the complete fixed denominator")
    pairs = record.get("pairs", [])
    if not isinstance(pairs, (list, tuple)) or not all(isinstance(row, Mapping) for row in pairs):
        return errors + ["summary paired records must be objects"]
    expected = {(task, number) for task in TASK_IDS for number in range(1, 4)}
    if len(pairs) != 18 or {(row.get("task_id"), row.get("attempt_number")) for row in pairs} != expected:
        errors.append("summary requires 18 unique matched task/attempt pairs")
    counts = Counter({name: 0 for name in ("both_pass", "strata_only", "ninfer_only", "both_fail")})
    ratios = []
    for row in pairs:
        if row.get("outcome") not in counts or not all(_hash(row.get(f"{arm}_sha256")) for arm in ARMS):
            errors.append("invalid paired outcome or artifact identity")
            continue
        counts[row["outcome"]] += 1
        if row["outcome"] == "both_pass" and _number(row.get("task_wall_ratio")):
            ratios.append(row["task_wall_ratio"])
    if dict(counts) != record.get("outcome_counts"):
        errors.append("paired outcome arithmetic mismatch")
    refs = record.get("windows", [])
    if not isinstance(refs, (list, tuple)) or not all(isinstance(row, Mapping) for row in refs):
        return errors + ["summary window references must be objects"]
    if len(refs) != 6 or [row.get("window") for row in refs] != list(range(1, 7)) or not all(_hash(row.get("sha256")) for row in refs):
        errors.append("summary must bind six ordered window hashes")
    if not _hash(record.get("ordered_records_sha256")):
        errors.append("ordered record digest required")
    elif len(pairs) == 18 and len(refs) == 6:
        paired = {(row.get("task_id"), row.get("attempt_number")): row for row in pairs}
        if set(paired) == expected:
            ordered = [row.get("sha256") for row in refs] + [paired[(slot["task_id"], slot["attempt_number"])].get(slot["arm"] + "_sha256") for slot in scheduled_slots()]
            if record["ordered_records_sha256"] != sha256(canonical(ordered)):
                errors.append("ordered record digest mismatch")
    host_fields = ("label", "os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy")
    if record.get("host") != {key: plan["host"][key] for key in host_fields}:
        errors.append("summary host identity differs from the plan")
    arms = record.get("arms", {})
    if not isinstance(arms, Mapping) or not all(isinstance(arms.get(arm), Mapping) for arm in ARMS):
        return errors + ["summary arm aggregates are required"]
    for arm in ARMS:
        aggregate = arms.get(arm, {})
        passes = counts["both_pass"] + counts[f"{arm}_only"]
        if aggregate.get("verified_passes") != passes or aggregate.get("failed_attempts") != 18 - passes or aggregate.get("scheduled_attempts") != 18:
            errors.append("arm completion arithmetic mismatch")
        for field in ("all_attempt_wall_ms", "observed_attempt_wall_ms", "success_only_median_wall_ms"):
            missing_value(aggregate, field, errors)
    if not record.get("confounders") or any(item not in record["confounders"] for item in CONFOUNDERS):
        errors.append("confounders cannot be omitted")
    if record.get("complete") and record.get("aborts"):
        errors.append("aborted comparison cannot be complete")
    resources = record.get("resources", {})
    if not isinstance(resources, Mapping) or not all(isinstance(resources.get(arm), Mapping) for arm in ARMS):
        errors.append("resource aggregates and provenance are required")
    else:
        for aggregate in resources.values():
            for field in ("ram_gib_minimum", "available_ram_gib_minimum", "commit_headroom_gib_minimum", "disk_gib_minimum"):
                missing_value(aggregate, field, errors)
            if not aggregate.get("method"):
                errors.append("resource sampling method required")
    cache = record.get("cache", {})
    if not isinstance(cache, Mapping):
        errors.append("cache observation provenance is required")
    else:
        missing_value(cache, "server_cache_hits", errors)
        if not cache.get("method"):
            errors.append("cache observation method required")
    if not errors:
        expected_claims = claim_decision(plan, complete=record.get("complete") is True and record.get("execution_boundary") == "evaluation",
                                         arms=arms, outcome_counts=counts, joint_ratios=ratios)
        if record.get("claims") != expected_claims:
            errors.append("claims exceed or differ from the frozen claim policy")
    return errors
