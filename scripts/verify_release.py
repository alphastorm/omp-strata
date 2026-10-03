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
from omp_strata.profile import _client_route, load, load_route
from omp_strata.receipts import REPO, gate_inventory, receipt_time, schema_errors, validate_receipt


def _verify_g25(receipt: dict, release_root: Path, profile) -> list[str]:
    """Verify the reviewed release-local export, not private runtime paths."""
    from omp_strata.comparison import (canonical, plan_digest, scheduled_slots, sha256,
                                       validate_plan, validate_summary, validate_window)

    errors = []
    records = {}
    root = release_root.resolve()
    try:
        for ref in receipt["evidence"]:
            path = (root / ref["path_or_ref"]).resolve()
            if not path.is_relative_to(root):
                errors.append("G25: evidence escapes release directory")
                continue
            if not path.is_file():
                errors.append("G25: evidence missing")
                continue
            if sha256_file(path) != ref["sha256"]:
                errors.append("G25: evidence sha256 mismatch")
                continue
            if ref["kind"] in ("comparison_plan", "paired_summary", "window_aggregate", "verifier_aggregate"):
                records.setdefault(ref["kind"], []).append((read_json(path), ref["sha256"]))
        if errors:
            return errors
        plan = records["comparison_plan"][0][0]
        paired = records["paired_summary"][0][0]
        windows = records["window_aggregate"]
        verifier = records["verifier_aggregate"][0][0]
        errors.extend("G25: " + error for error in validate_plan(plan))
        if errors:
            return errors
        errors.extend("G25: " + error for error in validate_summary(paired, plan))
        for window, _ in windows:
            errors.extend("G25: " + error for error in validate_window(window, plan))
        if errors:
            return errors
        comparison = receipt["comparison"]
        if plan["comparison_id"] != comparison["comparison_id"]:
            errors.append("G25: comparison_id mismatch")
        if (plan["strata"]["profile_fingerprint"] != profile.fingerprint
                or plan["strata"]["profile_id"] != profile.id):
            errors.append("G25: plan Strata profile fingerprint or id mismatch")
        omp = plan["omp"]
        artifact = profile.data["omp"]["artifacts"].get(omp["platform"], {})
        if (omp["sha256"] != comparison["omp_binary_sha256"]
                or omp["sha256"] != artifact.get("sha256")
                or omp["bytes"] != artifact.get("bytes")
                or omp["version"] != profile.data["omp"]["version"]):
            errors.append("G25: OMP binary pin mismatch")
        if plan["ninfer"]["manifest_sha256"] != comparison["ninfer_manifest_sha256"]:
            errors.append("G25: NInfer manifest pin mismatch")
        if (paired["execution_boundary"] != "evaluation" or paired["complete"] is not True
                or paired["aborts"] or paired["claims"]["engine_only_comparison"] is not False
                or plan["claims"]["engine_only_comparison"] is not False):
            errors.append("G25: incomplete, aborted, mock or engine-only comparison")
        window_hashes = {window["window"]: digest for window, digest in windows}
        if (len(window_hashes) != 6
                or window_hashes != {ref["window"]: ref["sha256"] for ref in paired["windows"]}):
            errors.append("G25: window aggregate bindings mismatch")
        attempts = {}
        host = {key: plan["host"][key] for key in
                ("label", "os", "os_build", "gpu_model", "vram_mib", "driver", "power_policy", "clock_policy")}
        if paired.get("host") != host:
            errors.append("G25: summary host identity mismatch")
        for window, _ in windows:
            if window.get("host") != host:
                errors.append("G25: window host identity mismatch")
            if (window["execution_boundary"] != "evaluation" or window["status"] != "complete"
                    or window["exclusive_gpu"] is not True or window["abort_reason"] is not None):
                errors.append("G25: window is not complete exclusive evaluation evidence")
            for attempt in window["attempts"]:
                key = (window["arm"], attempt["task_id"], attempt["attempt_number"])
                if key in attempts:
                    errors.append("G25: duplicate window attempt")
                attempts[key] = attempt["sha256"]
        expected = {}
        verdicts = {}
        for pair in paired["pairs"]:
            for arm in ("strata", "ninfer"):
                key = (arm, pair["task_id"], pair["attempt_number"])
                expected[key] = pair[arm + "_sha256"]
                verdicts[key] = pair["outcome"] in ("both_pass", arm + "_only")
        if len(attempts) != 36 or attempts != expected:
            errors.append("G25: paired attempt/window bindings mismatch")
        ordered = [ref["sha256"] for ref in paired["windows"]] + [
            expected[(slot["arm"], slot["task_id"], slot["attempt_number"])] for slot in scheduled_slots()]
        if paired["ordered_records_sha256"] != sha256(canonical(ordered)):
            errors.append("G25: ordered record digest mismatch")
        if (type(verifier["schema_version"]) is not int or verifier["schema_version"] != 1
                or verifier["record_type"] != "verifier_aggregate"
                or verifier["comparison_id"] != comparison["comparison_id"]
                or verifier["plan_sha256"] != plan_digest(plan)):
            errors.append("G25: verifier aggregate identity mismatch")
        verified = {}
        for row in verifier["attempts"]:
            key = (row["arm"], row["task_id"], row["attempt_number"])
            if (key in verified or type(row["verified_pass"]) is not bool
                    or type(row["attempt_number"]) is not int):
                errors.append("G25: duplicate or invalid verifier outcome")
            verified[key] = row["attempt_sha256"]
            if row["verified_pass"] != verdicts.get(key):
                errors.append("G25: verifier outcome mismatch")
        if len(verified) != 36 or verified != expected:
            errors.append("G25: verifier aggregate must retain all 36 outcomes")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
        errors.append("G25: evidence malformed or unavailable")
    return errors


def verify(manifest_path: Path, *, require_ready: bool = False) -> dict:
    errors = []
    summary = {"status": "invalid", "gates": {}, "errors": errors}
    try:
        manifest = read_json(manifest_path)
        errors.extend(schema_errors(manifest, read_json(REPO / "schemas/manifest.schema.json")))
        if errors:
            return summary
        summary["status"] = manifest["status"]
        is_route = manifest.get("kind") == "client-route"
        profile = (load_route if is_route else load)(manifest_path.parent / manifest["profile"]["path"])
        if manifest["profile"]["fingerprint"] != profile.fingerprint:
            errors.append("profile fingerprint mismatch")
        if manifest["candidate_id"] != profile.id:
            errors.append("candidate_id does not match profile_id")
        expected_capabilities = ({name: name == "remote_client" for name in manifest["capabilities"]}
                                 if is_route else profile.data["capabilities"])
        if manifest["capabilities"] != expected_capabilities:
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
        if is_route:
            inventory = {"G23": {**inventory["G23"], "required": "always"}}
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
                    if gid == "G25" and receipt["status"] == "pass":
                        errors.extend(_verify_g25(receipt, manifest_path.parent, profile))
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
            if manifest["capabilities"][capability] and by_id.get(gid, {}).get("status") != "pass" and (not is_route or require_ready):
                errors.append(f"{capability}: requires {gid} pass")
        if require_ready:
            if is_route:
                for server in profile.servers.values():
                    result = verify(REPO / "releases" / server.id / "manifest.json", require_ready=True)
                    if result["errors"]:
                        errors.append("route server profile is not independently qualified: " + server.id)
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
    profile = (load_route if manifest.get("kind") == "client-route" else load)(manifest_path.parent / manifest["profile"]["path"])
    ledger_path = manifest_path.parent / manifest["qualification"]["ledger"]
    ledger = read_json(ledger_path)
    if manifest["candidate_id"] != profile.id or ledger["profile_id"] != profile.id:
        raise ValueError("candidate identity mismatch; cannot rebind a different profile")
    ledger["profile_fingerprint"] = profile.fingerprint
    atomic_write_json(ledger_path, ledger)
    manifest["profile"]["fingerprint"] = profile.fingerprint
    manifest["qualification"]["ledger_sha256"] = sha256_file(ledger_path)
    atomic_write_json(manifest_path, manifest)


def refresh_route_draft(manifest_path: Path, *, bindings_example: Path | None = None) -> None:
    """Re-pin only an unmeasured draft; any receipt/status history makes it immutable."""
    manifest = read_json(manifest_path)
    if manifest.get("kind") != "client-route" or manifest.get("status") != "draft":
        raise ValueError("only an unmeasured client-route draft can be refreshed")
    route_path = manifest_path.parent / manifest["profile"]["path"]
    data = read_json(route_path)
    ledger_path = manifest_path.parent / manifest["qualification"]["ledger"]
    ledger = read_json(ledger_path)
    if (data.get("status") != "draft" or data.get("profile_id") != manifest["candidate_id"]
            or ledger.get("profile_id") != data["profile_id"]
            or any(g.get("status") != "not_run" or g.get("receipts") or g.get("receipt_paths") for g in ledger["gates"])
            or any((manifest_path.parent / "receipts").glob("*.json"))):
        raise ValueError("draft refresh refuses any measured route or receipt history")
    for member in data["members"]:
        server = load(REPO / "profiles" / (member["server_profile"] + ".json"))
        member["server_fingerprint"] = server.fingerprint
    route = _client_route(route_path, data)
    bindings = read_json(bindings_example) if bindings_example is not None else None
    if bindings is not None:
        if bindings.get("route_id") != route.id:
            raise ValueError("bindings example belongs to another route")
        public = {m["label"]: m for m in data["members"]}
        if {m["label"] for m in bindings["members"]} != set(public):
            raise ValueError("bindings example members do not match")
        for member in bindings["members"]:
            member.update(public[member["label"]])
        bindings.update(route_fingerprint=route.fingerprint, roles=data["roles"])
    atomic_write_json(route_path, data)
    ledger["profile_fingerprint"] = route.fingerprint
    atomic_write_json(ledger_path, ledger)
    manifest["profile"]["fingerprint"] = route.fingerprint
    manifest["qualification"]["ledger_sha256"] = sha256_file(ledger_path)
    atomic_write_json(manifest_path, manifest)
    if bindings is not None:
        atomic_write_json(bindings_example, bindings)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--rebind", action="store_true",
                        help="refresh profile/ledger hashes, then verify; stale receipts remain invalid")
    parser.add_argument("--refresh-route-draft", action="store_true", help="re-pin an unmeasured draft route to its server fingerprints")
    parser.add_argument("--bindings-example", type=Path, help="refresh a neutral route bindings example too")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.refresh_route_draft:
        try:
            refresh_route_draft(args.manifest, bindings_example=args.bindings_example)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"draft refresh refused ({type(exc).__name__})", file=sys.stderr)
            return 1
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
