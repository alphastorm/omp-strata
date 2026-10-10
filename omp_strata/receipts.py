"""Hash-bound, append-only qualification receipts; mocks never qualify hardware gates."""
from __future__ import annotations

import math
import os
import re
import uuid
from datetime import datetime
from pathlib import Path, PurePosixPath

from .common import atomic_write_json, read_json, sha256_file, utc_now

REPO = Path(__file__).resolve().parents[1]


def schema_errors(value, schema: dict, where: str = "$") -> list[str]:
    """Validate the JSON Schema vocabulary used by our two checked-in contracts."""
    errors = []
    kinds = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
             "string": lambda x: isinstance(x, str), "null": lambda x: x is None,
             "boolean": lambda x: isinstance(x, bool),
             "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
             "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)}
    types = schema.get("type")
    if types and not any(kinds[t](value) for t in ([types] if isinstance(types, str) else types)):
        return [f"{where}: invalid type"]
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        errors.append(f"{where}: invalid constant")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: invalid enum value")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}.{key}: required")
        for key, item in value.items():
            if key in props:
                errors.extend(schema_errors(item, props[key], f"{where}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{where}.{key}: unknown property")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: too few items")
        for i, item in enumerate(value):
            errors.extend(schema_errors(item, schema.get("items", {}), f"{where}[{i}]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{where}: empty string")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: invalid format")
        if schema.get("format") == "date-time":
            try:
                if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", value):
                    raise ValueError
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{where}: valid UTC timestamp ending Z required")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value) or value < schema.get("minimum", -math.inf):
            errors.append(f"{where}: invalid number")
    for sub in schema.get("allOf", []):
        errors.extend(schema_errors(value, sub, where))
    if "if" in schema and not schema_errors(value, schema["if"], where):
        errors.extend(schema_errors(value, schema.get("then", {}), where))
    return errors


def gate_inventory() -> dict[str, dict]:
    return {g["id"]: g for g in read_json(REPO / "docs/handoff/2026-09-30/acceptance_matrix.json")["gates"]}


def validate_receipt(receipt: dict) -> list[str]:
    errors = schema_errors(receipt, read_json(REPO / "schemas/receipt.schema.json"))
    if errors:
        return errors
    gate = gate_inventory()[receipt["gate_id"]]
    if receipt["status"] == "pass" and receipt["execution_boundary"] != gate["execution_boundary"]:
        errors.append("execution_boundary: cannot pass a gate across a different evidence boundary")
    for metric in receipt["metrics"]:
        if metric["value"] is None and metric["method"] != "unavailable":
            errors.append(f"metrics.{metric['name']}: null requires method unavailable")
    for key in ("run_id", "expected", "observed", "reason", "profile_id"):
        if isinstance(receipt.get(key), str) and not receipt[key].strip():
            errors.append(f"{key}: blank string")
    if receipt["gate_id"] == "G25" and receipt["status"] == "pass":
        kinds = {"comparison_plan": 1, "paired_summary": 1,
                 "window_aggregate": 6, "verifier_aggregate": 1}
        evidence = receipt["evidence"]
        for kind, count in kinds.items():
            if sum(ref["kind"] == kind for ref in evidence) != count:
                errors.append(f"G25: requires {count} {kind} evidence references")
        paths = set()
        for ref in evidence:
            path = ref["path_or_ref"]
            parts = PurePosixPath(path)
            if (parts.is_absolute() or ".." in parts.parts or "\\" in path
                    or ":" in path or path != parts.as_posix() or path == "."):
                errors.append("G25: evidence path must be release-relative without traversal")
            if path in paths:
                errors.append("G25: duplicate evidence path")
            paths.add(path)
            if ref["sha256"] is None or ref["scrubbed"] is not True:
                errors.append("G25: evidence must be hashed and scrubbed")
        comparison = receipt["comparison"]
        for kind, key in (("comparison_plan", "plan_sha256"),
                          ("paired_summary", "paired_summary_sha256")):
            for ref in evidence:
                if ref["kind"] == kind and ref["sha256"] != comparison[key]:
                    errors.append(f"G25: {kind} hash differs from comparison binding")
        if not any(item.strip() for item in receipt["limitations"]):
            errors.append("G25: explicit comparison limitations required")
    return errors


def validate_gpu_qualification(record: dict, profile, *, gate: str,
                               runtime_identity_sha256: str | None, metrics=(),
                               require_complete: bool = False) -> list[str]:
    """Validate the scrubbed multi-card resource export, without changing receipt schemas.

    Coverage is separate from success: a complete observation can report foreign
    compute or unreleased memory. Passing receipts must additionally satisfy the
    gate conditions and agree with the record's indexed metrics.
    """
    if not profile.multi_gpu or gate not in ("G10", "G20", "G21"):
        return ["gpu_qualification: multi-card G10/G20/G21 profile required"]

    def obj(properties):
        return dict(type="object", properties=properties, required=list(properties),
                    additionalProperties=False)

    count = dict(type="integer", minimum=0)
    observed_count = dict(type=["integer", "null"], minimum=0)
    boolean = dict(type="boolean")
    text = dict(type="string", minLength=1)
    digest = dict(type="string", pattern="^[0-9a-f]{64}$")
    identity = {"gpu_index": count, "gpu_model": text, "arch": text,
                "pci_bus_id": text, "display_attached": boolean}
    snapshot = obj({key: observed_count for key in
                    ("memory_used_mib", "owned_count", "foreign_compute_count")})
    fields = {
        "G10": dict(memory_total_mib=observed_count, driver_version=dict(type=["string", "null"], minLength=1),
                    memory_used_mib=observed_count, owned_count=observed_count,
                    foreign_compute_count=observed_count, graphics_client_count=observed_count,
                    exclusive=boolean),
        "G20": dict(before_stop=snapshot, after_stop=snapshot, after_restart=snapshot,
                    released=boolean, restarted_owned=boolean),
        "G21": dict(peak_used_mib=observed_count, samples=count, unavailable_samples=count),
    }[gate]
    order = obj(dict(configured=dict(type="array", items=count, minItems=2),
                     staged=dict(type=["array", "null"], items=count, minItems=2),
                     event=dict(enum=["reordered", "kept_1576", "kept_configured", "unavailable"]),
                     complete=boolean))
    properties = dict(schema_version=dict(const=1), record_type=dict(const="gpu_qualification"),
                      gate=dict(const=gate), profile_id=text, profile_fingerprint=digest,
                      runtime_identity_sha256=digest, cards=dict(type="array", items=obj(identity | fields)),
                      stage_order=dict(type="null") if gate == "G21" else order,
                      complete=boolean, missing=dict(type="array", items=text))
    if gate == "G21":
        properties.update(gpu_used_mib_sum_peak=observed_count,
                          min_available_ram_mib=dict(type=["number", "null"], minimum=0))
    errors = schema_errors(record, obj(properties), "gpu_qualification")
    if errors:
        return errors
    for key, expected in (("profile_id", profile.id), ("profile_fingerprint", profile.fingerprint),
                          ("runtime_identity_sha256", runtime_identity_sha256)):
        if record[key] != expected:
            errors.append(f"gpu_qualification: {key} binding mismatch")
    requirements = profile.gpu_requirements
    cards = record["cards"]
    indices = [card["gpu_index"] for card in cards]
    if indices != [card["gpu_index"] for card in requirements] or len(set(indices)) != len(indices):
        errors.append("gpu_qualification: complete unique card coverage in profile order required")
        return errors
    for card, required in zip(cards, requirements):
        if any(card[key] != required[key] for key in identity):
            errors.append(f"gpu_qualification: gpu.{card['gpu_index']} identity mismatch")
    complete = record["complete"]
    if complete and record["missing"]:
        errors.append("gpu_qualification: complete record has missing observations")
    if require_complete and not complete:
        errors.append("gpu_qualification: passing receipt requires complete record")
    stage = record["stage_order"]
    if stage is not None:
        staged = stage["staged"]
        if stage["configured"] != indices:
            errors.append("gpu_qualification: configured stage order mismatch")
        if staged is not None and (len(staged) != len(indices) or set(staged) != set(indices)):
            errors.append("gpu_qualification: staged order must cover every card exactly once")
        if stage["complete"] != (staged is not None and stage["event"] != "unavailable"):
            errors.append("gpu_qualification: inconsistent stage-order completeness")
        if (stage["event"] in ("kept_1576", "kept_configured") and staged != indices
                or stage["event"] == "reordered" and staged == indices):
            errors.append("gpu_qualification: stage-order event disagrees with order")
        if complete and not stage["complete"]:
            errors.append("gpu_qualification: complete startup stage order required")
    expected_metrics = {}
    optional_metrics = {}
    for card, required in zip(cards, requirements):
        prefix = f"gpu.{card['gpu_index']}"
        if gate == "G10":
            expected_metrics[prefix + ".memory_total_mib"] = card["memory_total_mib"]
            optional_metrics[prefix + ".memory_used_mib"] = card["memory_used_mib"]
            observed = [card[key] for key in fields if key != "exclusive"]
            if complete and any(value is None for value in observed):
                errors.append(f"{prefix}: complete G10 observations required")
            driver = card["driver_version"]
            if require_complete and (not isinstance(driver, str)
                    or not re.fullmatch(r"\d+(?:\.\d+)*", driver)
                    or int(driver.split(".")[0]) < profile.data["host"]["min_driver_major"]):
                errors.append(f"{prefix}: G10 driver floor condition failed")
            if require_complete and (card["memory_total_mib"] is None
                    or card["memory_total_mib"] < required["min_gpu_vram_mib"]
                    or not card["owned_count"] or card["foreign_compute_count"] != 0
                    or not card["exclusive"]
                    or not card["display_attached"] and card["graphics_client_count"] != 0):
                errors.append(f"{prefix}: G10 capacity, ownership or exclusivity condition failed")
            if (card["memory_used_mib"] is not None and card["memory_total_mib"] is not None
                    and card["memory_used_mib"] > card["memory_total_mib"]):
                errors.append(f"{prefix}: used memory exceeds capacity")
        elif gate == "G20":
            from .lifecycle import GPU_IDLE_MIB

            snapshots = [card[key] for key in ("before_stop", "after_stop", "after_restart")]
            if complete and any(value is None for snap in snapshots for value in snap.values()):
                errors.append(f"{prefix}: complete G20 snapshots required")
            before, stopped, restarted = snapshots
            optional_metrics[prefix + ".memory_used_mib_after_stop"] = stopped["memory_used_mib"]
            if require_complete and (not before["owned_count"] or not restarted["owned_count"]
                    or stopped["owned_count"] != 0 or stopped["memory_used_mib"] is None
                    or stopped["memory_used_mib"] >= GPU_IDLE_MIB
                    or any(snap["foreign_compute_count"] != 0 for snap in snapshots)
                    or not card["released"] or not card["restarted_owned"]):
                errors.append(f"{prefix}: G20 release, restart or exclusivity condition failed")
        else:
            expected_metrics[prefix + ".peak_used_mib"] = card["peak_used_mib"]
            if (card["peak_used_mib"] is None) != (card["samples"] == 0):
                errors.append(f"{prefix}: peak disagrees with sample coverage")
            if complete and (card["samples"] == 0 or card["unavailable_samples"] != 0):
                errors.append(f"{prefix}: complete G21 sample coverage required")
    if gate == "G21":
        peak = record["gpu_used_mib_sum_peak"]
        expected_metrics["gpu.sum.peak_used_mib"] = peak
        if complete and (peak is None or record["min_available_ram_mib"] is None):
            errors.append("gpu_qualification: complete GPU sum and RAM observations required")
        peaks = [card["peak_used_mib"] for card in cards]
        if peak is not None and all(value is not None for value in peaks) and peak > sum(peaks):
            errors.append("gpu_qualification: simultaneous sum exceeds per-card peaks")
    allowed_metrics = expected_metrics | optional_metrics
    seen = set()
    for metric in metrics:
        name = metric["name"]
        if metric["value"] is None and metric["method"] != "unavailable":
            errors.append(f"metrics.{name}: null requires method unavailable")
        if name.startswith("gpu."):
            if name in seen or name not in allowed_metrics:
                errors.append(f"metrics.{name}: duplicate or unexpected GPU metric")
            elif (metric["value"] != allowed_metrics[name] or metric["unit"] != "MiB"
                  or type(metric["value"]) is bool):
                errors.append(f"metrics.{name}: GPU resource record disagreement")
            seen.add(name)
        elif gate == "G21" and name == "min_available_ram_serving":
            ram = record["min_available_ram_mib"]
            if (name in seen or metric["value"] != (None if ram is None else ram * 1024**2)
                    or metric["unit"] != "bytes"):
                errors.append(f"metrics.{name}: RAM resource record disagreement")
            seen.add(name)
    if not set(expected_metrics).issubset(seen):
        errors.append("gpu_qualification: complete indexed receipt metrics required")
    return errors


def make_receipt(*, gate_id: str, status: str, execution_boundary: str, expected: str, observed: str,
                 implementation_commit: str | None = None, profile_id: str | None = None,
                 identity_fingerprint: str | None = None, evidence=(), metrics=(), limitations=(),
                 retry_history=(), reason: str | None = None, run_id: str | None = None,
                 timestamp_utc: str | None = None, gate_title: str | None = None,
                 gate_key: str | None = None, comparison: dict | None = None) -> dict:
    receipt = dict(schema_version=1, run_id=run_id or uuid.uuid4().hex, gate_id=gate_id, status=status,
                   execution_boundary=execution_boundary, timestamp_utc=timestamp_utc or utc_now(),
                   implementation_commit=implementation_commit, profile_id=profile_id,
                   identity_fingerprint=identity_fingerprint, expected=expected, observed=observed,
                   evidence=list(evidence), metrics=list(metrics), limitations=list(limitations),
                   retry_history=list(retry_history))
    for key, value in (("reason", reason), ("gate_title", gate_title), ("gate_key", gate_key),
                       ("comparison", comparison)):
        if value is not None:
            receipt[key] = value
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("; ".join(errors))
    return receipt


def write_receipt(directory: Path, receipt: dict) -> Path:
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("; ".join(errors))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", receipt["run_id"]):
        raise ValueError("run_id: unsafe filename")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (receipt["run_id"] + ".json")
    # Exclusive creation keeps a repeated run from overwriting its previous evidence.
    import json
    with path.open("x", encoding="utf-8") as out:
        out.write(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return path


def receipt_time(receipt: dict) -> datetime:
    return datetime.fromisoformat(receipt["timestamp_utc"].replace("Z", "+00:00"))


def update_ledger(ledger_path: Path, receipt_path: Path) -> None:
    ledger = read_json(ledger_path)
    receipt = read_json(receipt_path)
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("; ".join(errors))
    if receipt["identity_fingerprint"] != ledger["profile_fingerprint"]:
        raise ValueError("receipt profile fingerprint mismatch")
    if receipt["profile_id"] not in (None, ledger["profile_id"]):
        raise ValueError("receipt profile_id mismatch")
    gate = next((g for g in ledger["gates"] if g["id"] == receipt["gate_id"]), None)
    if gate is None or receipt["execution_boundary"] != gate["execution_boundary"]:
        raise ValueError("receipt gate boundary mismatch")
    newest = None
    for existing_gate in ledger["gates"]:
        for ref in existing_gate["receipts"]:
            path = ledger_path.parent / ref["path"]
            if sha256_file(path) != ref["sha256"]:
                raise ValueError("existing receipt hash mismatch")
            prior = read_json(path)
            if validate_receipt(prior):
                raise ValueError("invalid existing receipt")
            if prior["run_id"] == receipt["run_id"]:
                raise ValueError("duplicate run_id")
            if existing_gate is gate and (newest is None or receipt_time(prior) >= receipt_time(newest)):
                newest = prior
    relative = Path(os.path.relpath(receipt_path.resolve(), ledger_path.parent.resolve())).as_posix()
    gate["receipts"].append({"path": relative, "sha256": sha256_file(receipt_path)})
    gate["receipt_paths"].append(relative)
    if newest is None or receipt_time(receipt) >= receipt_time(newest):
        gate["status"] = receipt["status"]
        gate["note"] = receipt.get("reason")
    atomic_write_json(ledger_path, ledger)
