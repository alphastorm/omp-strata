#!/usr/bin/env python3
"""Verify profile, ledger and receipt bindings; readiness is an explicit stronger check.

Manifest references are relative to its directory; receipt references are relative
 to the ledger directory. Hashes cover exact file bytes, except canonical profile identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata.common import atomic_write_json, read_json, sha256_file
from omp_strata.profile import load
from omp_strata.receipts import REPO, gate_inventory, receipt_time, schema_errors, validate_receipt


def verify(manifest_path: Path, *, require_ready: bool = False) -> dict:
    errors = []
    summary = {"status": "invalid", "gates": {}, "errors": errors}
    try:
        manifest = read_json(manifest_path)
        errors.extend(schema_errors(manifest, read_json(REPO / "schemas/manifest.schema.json")))
        if errors:
            return summary
        summary["status"] = manifest["status"]
        profile = load(manifest_path.parent / manifest["profile"]["path"])
        if manifest["profile"]["fingerprint"] != profile.fingerprint:
            errors.append("profile fingerprint mismatch")
        if manifest["candidate_id"] != profile.id:
            errors.append("candidate_id does not match profile_id")
        if manifest["capabilities"] != profile.data["capabilities"]:
            errors.append("capabilities do not mirror profile")
        for name in ("durable_engine_state", "multi_tenant"):
            if manifest["capabilities"][name]:
                errors.append(f"capabilities.{name}: never supported")

        ledger_path = manifest_path.parent / manifest["qualification"]["ledger"]
        if sha256_file(ledger_path) != manifest["qualification"]["ledger_sha256"]:
            errors.append("ledger sha256 mismatch")
        ledger = read_json(ledger_path)
        if ledger.get("profile_fingerprint") != profile.fingerprint or ledger.get("profile_id") != profile.id:
            errors.append("ledger profile identity mismatch")
        inventory = gate_inventory()
        gates = ledger.get("gates")
        if not isinstance(gates, list) or any(not isinstance(g, dict) for g in gates):
            errors.append("ledger gates must be objects")
            return summary
        ids = [g.get("id") for g in gates]
        if len(set(ids)) != len(ids) or set(ids) != set(inventory):
            errors.append("ledger gate inventory is incomplete, duplicated or unknown")
        run_ids = set()
        for gate in gates:
            gid = gate.get("id")
            spec = inventory.get(gid)
            if spec is None:
                continue
            for field in ("execution_boundary", "required", "key"):
                if gate.get(field) != spec[field]:
                    errors.append(f"{gid}: gate {field} changed")
            status = gate.get("status")
            if status not in ("not_run", "pass", "fail", "blocked", "not_applicable"):
                errors.append(f"{gid}: invalid status")
            refs = gate.get("receipts")
            if not isinstance(refs, list):
                errors.append(f"{gid}: missing receipt history")
                continue
            if any(not isinstance(r, dict) or set(r) != {"path", "sha256"} for r in refs):
                errors.append(f"{gid}: malformed receipt reference")
                continue
            if gate.get("receipt_paths") != [r["path"] for r in refs]:
                errors.append(f"{gid}: receipt_paths/history mismatch")
            newest = None
            for ref in refs:
                try:
                    path = ledger_path.parent / ref["path"]
                    if sha256_file(path) != ref["sha256"]:
                        errors.append(f"{gid}: receipt sha256 mismatch")
                    receipt = read_json(path)
                    receipt_errors = validate_receipt(receipt)
                    errors.extend(f"{gid}: {e}" for e in receipt_errors)
                    if receipt_errors:
                        continue
                    if receipt["run_id"] in run_ids:
                        errors.append(f"{gid}: duplicate run_id")
                    run_ids.add(receipt["run_id"])
                    if receipt["gate_id"] != gid:
                        errors.append(f"{gid}: receipt gate_id mismatch")
                    if receipt["identity_fingerprint"] != profile.fingerprint:
                        errors.append(f"{gid}: receipt fingerprint mismatch")
                    if receipt["profile_id"] not in (None, profile.id):
                        errors.append(f"{gid}: receipt profile_id mismatch")
                    if receipt["execution_boundary"] != spec["execution_boundary"]:
                        errors.append(f"{gid}: receipt execution_boundary mismatch")
                    if newest is None or receipt_time(receipt) >= receipt_time(newest):
                        newest = receipt
                except (OSError, ValueError, TypeError):
                    errors.append(f"{gid}: receipt missing or unreadable")
            if newest is not None and status != newest["status"]:
                errors.append(f"{gid}: status differs from newest receipt")
            if newest is None and status != "not_run":
                errors.append(f"{gid}: status has no receipt")
            condition = spec["required"]
            cap = condition.removeprefix("when:")
            enabled = (manifest["claims"]["comparative_claims"] if cap == "comparative_claims"
                       else manifest["capabilities"].get(cap, False))
            required = condition == "always" or enabled
            if status == "not_applicable" and required:
                errors.append(f"{gid}: not_applicable requires disabled optional capability/claim")
            if require_ready and required and status != "pass":
                errors.append(f"{gid}: required gate is {status}")
        summary["gates"] = dict(Counter(g.get("status", "invalid") for g in gates))
        by_id = {g.get("id"): g for g in gates}
        for capability, gid in (("vision", "G22"), ("remote_client", "G23")):
            if manifest["capabilities"][capability] and by_id.get(gid, {}).get("status") != "pass":
                errors.append(f"{capability}: requires {gid} pass")
        if require_ready:
            if manifest["status"] != "qualified":
                errors.append(f"status {manifest['status']}: qualified required")
            if manifest["blockers"]:
                errors.append("blockers remain: " + "; ".join(manifest["blockers"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Avoid printing file contents or absolute private paths from parse/OS errors.
        errors.append(f"manifest/profile/ledger invalid or unavailable ({type(exc).__name__})")
    return summary


def rebind(manifest_path: Path) -> None:
    """Refresh explicit bindings without rewriting any receipt or its historical identity."""
    manifest = read_json(manifest_path)
    profile = load(manifest_path.parent / manifest["profile"]["path"])
    ledger_path = manifest_path.parent / manifest["qualification"]["ledger"]
    ledger = read_json(ledger_path)
    if manifest["candidate_id"] != profile.id or ledger["profile_id"] != profile.id:
        raise ValueError("candidate identity mismatch; cannot rebind a different profile")
    ledger["profile_fingerprint"] = profile.fingerprint
    atomic_write_json(ledger_path, ledger)
    manifest["profile"]["fingerprint"] = profile.fingerprint
    manifest["qualification"]["ledger_sha256"] = sha256_file(ledger_path)
    atomic_write_json(manifest_path, manifest)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--rebind", action="store_true",
                        help="refresh profile/ledger hashes, then verify; stale receipts remain invalid")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.rebind:
        try:
            rebind(args.manifest)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"rebind refused ({type(exc).__name__})", file=sys.stderr)
            return 1
    result = verify(args.manifest, require_ready=args.require_ready)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"status: {result['status']}; gates: {json.dumps(result['gates'], sort_keys=True)}")
        for error in result["errors"]:
            print(error)
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
