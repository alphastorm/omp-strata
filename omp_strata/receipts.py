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
