#!/usr/bin/env python3
"""Discover one frozen Strata release; track, but never run, each host's qualification.

Usage: python3 scripts/campaign.py open --release v0.1.45
       python3 scripts/campaign.py status [--release v0.1.45]
       python3 scripts/campaign.py set-host --release v0.1.45 --profile ID --status queued

Exit 0 = recorded/read, 2 = refused, 4 = unavailable metadata (never no update).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata.common import atomic_write_json, prerelease_tag, read_json, utc_now
from omp_strata.receipts import schema_errors
from scripts.upstream_watch import (API, Incomplete, REPOS, assert_same_release, auth_token,
                                   discover_release, version)
from scripts.verify_release import verify

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/release-campaign.schema.json"
# Lanes, not version pins. Only qualified release manifests select their predecessors.
# One row per lane. A lane lists its stock variants' profile families (each a profile of its own, AGENTS.md); its
# predecessor is the newest qualified profile across them, and the next candidate keeps that variant.
LANES = (
    (("win11-rtxpro6000-iq3s-262k-slots4-parking",), "rtxpro6000-win-a", "server"),
    (("win11-rtx5090-coder-iq1m-131k",), "rtx5090-win-a", "server"),
    (("win11-rtx5090-coder-iq1m-262k",), "rtx5090-win-a", "server"),
    (("win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking"),
     "rtx3090-win-a", "server"),
    (("client-rtxpro6000-262k",), "mac-studio-client", "client-route"),
)
TRANSITIONS = {
    "pending": {"queued", "blocked"}, "queued": {"running", "blocked"},
    "running": {"qualified", "failed", "blocked"}, "failed": {"queued", "blocked"},
    "blocked": {"queued"}, "qualified": set(),
}


def state(hosts):
    live = [row for row in hosts if "superseded_by" not in row]
    if not live:
        return "superseded"
    if all(row["status"] == "qualified" for row in live):
        return "complete"
    return "running" if any(row["status"] in ("running", "qualified", "failed") for row in live) else "pending"


def validate(record):
    errors = schema_errors(record, read_json(SCHEMA))
    if errors:
        raise ValueError("invalid campaign: " + "; ".join(errors))
    if len({a["name"] for a in record["assets"]}) != len(record["assets"]):
        raise ValueError("duplicate campaign asset")
    if record["schema_version"] == 2:
        if len({a["id"] for a in record["assets"]}) != len(record["assets"]):
            raise ValueError("duplicate campaign asset id")
        if record["prerelease"] != (prerelease_tag(record["tag"]) or record["github_prerelease"]):
            raise ValueError("campaign prerelease classification does not match its source")
        for asset in record["assets"]:
            expected = f"https://github.com/{record['repository']}/releases/download/{record['tag']}/{asset['name']}"
            if asset["url"] != expected:
                raise ValueError("campaign asset URL does not match its source")
    if len({h["profile_id"] for h in record["hosts"]}) != len(record["hosts"]):
        raise ValueError("duplicate campaign host profile")
    if record["status"] != state(record["hosts"]):
        raise ValueError("campaign status does not match its host rows")
    for row in record["hosts"]:
        if "superseded_by" in row and (row["status"] != "pending" or record.get("prerelease", False)
                or prerelease_tag(row["superseded_by"]) or version(row["superseded_by"]) <= version(record["tag"])):
            raise ValueError("only pending host rows may be superseded by a newer release")
    return record


def campaign_path(root, tag):
    version(tag)  # Also prevents a tag from becoming a path traversal.
    return root / "releases" / "campaigns" / (tag + ".json")


def campaigns(root):
    records = [validate(read_json(path)) for path in sorted((root / "releases/campaigns").glob("*.json"))]
    return sorted(records, key=lambda record: version(record["tag"]))


def host_rows(root, tag, candidate_omp=None):
    """One pending row per lane, named from its newest qualified predecessor; `candidate_omp` moves every candidate
    to that stock OMP tag (each row still records its predecessor's own OMP pin)."""
    if candidate_omp is not None:
        version(candidate_omp)  # A stable release tag only; it becomes part of every candidate id.
    rows = []
    for families, host, kind in LANES:
        choices = []
        folder = "routes" if kind == "client-route" else "profiles"
        for family in families:
            for path in (root / folder).glob(family + "-strata*.json"):
                profile = read_json(path)
                identifier = profile["profile_id"]
                if not re.fullmatch(re.escape(family) + r"-strata[0-9.]+-omp[0-9.]+", identifier):
                    continue
                manifest_ref = f"releases/{identifier}/manifest.json"
                manifest = read_json(root / manifest_ref)
                if manifest.get("candidate_id") != identifier:
                    raise ValueError("predecessor manifest/profile identity mismatch")
                if manifest.get("status") != "qualified":
                    continue
                server = profile if kind == "server" else read_json(
                    root / "profiles" / (profile["members"][0]["server_profile"] + ".json"))
                strata_tag, omp_tag = server["strata"]["tag"], server["omp"]["tag"]
                choices.append(((version(strata_tag), version(omp_tag)), identifier, manifest_ref, strata_tag, omp_tag,
                                family))
        if not choices:
            raise ValueError(f"no qualified predecessor for {families[0]}")
        _, identifier, manifest_ref, strata_tag, omp_tag, family = max(choices)
        if version(strata_tag) >= version(tag):
            raise ValueError(f"{family}: campaign release must be newer than qualified predecessor")
        candidate_id = (f"{family}-strata{tag.removeprefix('v')}"
                        f"-omp{(candidate_omp or omp_tag).removeprefix('v')}")
        notes = ["Prepared only; OP11 requires the host owner's window, a new reviewed profile and restoration evidence."]
        if family.endswith("262k") and host == "rtx5090-win-a":
            notes.append("Opt-in only; the 131K lane remains the default. Run sequentially on the same GPU.")
        if kind == "client-route":
            notes.append("Wait for the PRO server's qualification; independent G23, not requalify.py, consumes this route.")
        if host == "rtx3090-win-a":
            negative = ("releases/" + family + "-strata0.1.44.1-omp18.10.1/manifest.json")
            if (root / negative).is_file():
                notes.append("Negative evidence (draft, not a qualified predecessor): " + negative
                             + "; automatic split regression, Strata#2463. Preserve the 0.1.43.1 rollback.")
        rows.append({"profile_id": candidate_id, "host": host, "kind": kind,
                     "predecessor": {"profile_id": identifier, "strata_tag": strata_tag,
                                     "omp_tag": omp_tag, "manifest": manifest_ref},
                     "status": "pending", "result_refs": [], "restored_state_ref": None,
                     "disposition_notes": notes})
    return rows


def coalesce(root, records):
    """Replay-safe after interruption: persisted newer discovery settles older pending rows only."""
    records = [record for record in records if not record.get("prerelease", False)]
    if not records:
        return
    newest = records[-1]
    for record in records[:-1]:
        if record["status"] in ("complete", "superseded"):
            continue
        changed = False
        for row in record["hosts"]:
            if row["status"] == "pending" and "superseded_by" not in row:
                row["superseded_by"] = newest["tag"]
                row["disposition_notes"].append("Pending qualification coalesced into " + newest["tag"])
                changed = True
        if changed:
            record["status"] = state(record["hosts"])
            atomic_write_json(campaign_path(root, record["tag"]), validate(record))


def open_campaign(api, root, tag, *, allow_prerelease=False, check=False, omp_tag=None):
    snapshot = discover_release(api, REPOS["strata"], tag, allow_prerelease=allow_prerelease)
    if snapshot.get("state") == "skipped":
        return snapshot
    records = campaigns(root)
    existing = next((record for record in records if record["tag"] == tag), None)
    if existing is not None:
        assert_same_release(existing, snapshot)
        record = existing
    else:
        if any(record["release_id"] == snapshot["release_id"] for record in records):
            raise Incomplete("release id reused with another tag; frozen campaigns were not modified")
        record = {"schema_version": 2, **snapshot, "discovered_at": utc_now(), "status": "pending",
                  "hosts": host_rows(root, tag, omp_tag), "disposition_notes": [
                      "Discovery is not qualification, host admission, promotion or a default-runtime switch."]}
        validate(record)
        if not check:
            atomic_write_json(campaign_path(root, tag), record)
        records.append(record)
        records.sort(key=lambda item: version(item["tag"]))
    if not check and not snapshot["prerelease"]:
        coalesce(root, records)
    return record


def evidence_path(root, ref):
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts or "\\" in ref or ":" in ref:
        raise ValueError("evidence references must be public repository-relative paths")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("evidence reference is unavailable or outside repository")
    return resolved


def lane_variant(row_id, candidate_id):
    """True when `candidate_id` names another stock variant of `row_id`'s lane at the same Strata and OMP release."""
    pattern = r"(.+)(-strata[0-9.]+-omp[0-9.]+)"
    row, other = re.fullmatch(pattern, row_id), re.fullmatch(pattern, candidate_id or "")
    return bool(row and other and row[2] == other[2] and row[1] != other[1]
                and any(row[1] in families and other[1] in families for families, _, _ in LANES))


def set_host(root, tag, profile_id, status, *, result=None, restored_state=None, note=None):
    record = validate(read_json(campaign_path(root, tag)))
    row = next((row for row in record["hosts"] if row["profile_id"] == profile_id), None)
    if row is None:
        raise ValueError("profile is not a member of this campaign")
    if "superseded_by" in row or record["status"] == "complete":
        raise ValueError("superseded/complete campaign evidence is immutable")
    if status != row["status"] and status not in TRANSITIONS[row["status"]]:
        raise ValueError(f"invalid host transition: {row['status']} -> {status}")
    if result:
        path = evidence_path(root, result)
    if restored_state:
        evidence_path(root, restored_state)
    selected = profile_id
    if status == "qualified":
        if not result or not (restored_state or row["restored_state_ref"]):
            raise ValueError("qualified requires a verified release manifest and restored-state reference")
        manifest = read_json(path)
        checked = verify(path, require_ready=True)
        selected = manifest.get("candidate_id")
        if ((selected != profile_id and not lane_variant(profile_id, selected))
                or checked["status"] != "qualified" or checked["errors"]):
            raise ValueError("result is not this profile's ready qualified release manifest")
    if status in ("failed", "blocked") and not (result or note):
        raise ValueError("failed/blocked requires a result or disposition note")
    row["status"] = status
    if result and result not in row["result_refs"]:
        row["result_refs"].append(result)
    if restored_state:
        row["restored_state_ref"] = restored_state
    if selected != profile_id:  # the owner qualified another stock variant of this lane: the row now names it
        row["profile_id"] = selected
        note = (note + " " if note else "") + f"Qualified stock variant {selected} in place of the prepared {profile_id}."
    if note and note not in row["disposition_notes"]:
        row["disposition_notes"].append(note)
    record["status"] = state(record["hosts"])
    atomic_write_json(campaign_path(root, tag), validate(record))
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    opening = commands.add_parser("open")
    opening.add_argument("--release", required=True)
    opening.add_argument("--allow-prerelease", action="store_true", help="explicit owner-selected beta metadata intake")
    opening.add_argument("--check", action="store_true", help="print inventory without writing or coalescing campaigns")
    opening.add_argument("--omp-tag", help="stock OMP tag for every candidate (default: each predecessor's own)")
    status = commands.add_parser("status")
    status.add_argument("--release")
    update = commands.add_parser("set-host")
    update.add_argument("--release", required=True)
    update.add_argument("--profile", required=True)
    update.add_argument("--status", required=True, choices=tuple(TRANSITIONS))
    update.add_argument("--result")
    update.add_argument("--restored-state")
    update.add_argument("--note")
    args = parser.parse_args(argv)
    try:
        if args.command == "open":
            result = open_campaign(API(token=auth_token()), ROOT, args.release, allow_prerelease=args.allow_prerelease,
                                   check=args.check, omp_tag=args.omp_tag)
            if prerelease_tag(args.release):
                note = ("Beta metadata only; runnable component-profile drafts are not supported; "
                        "see docs/UPSTREAM-BETA.md.")
                if result.get("state") == "skipped":
                    print(json.dumps({"state": "refused", "reason": "--allow-prerelease is required. " + note}))
                    return 2
                if not args.check:
                    print(json.dumps({"state": "blocked", "reason": note, "campaign": result}, indent=2))
                    return 2
                result = {**result, "check": True, "install_supported": False, "install_note": note}
        elif args.command == "status":
            result = (validate(read_json(campaign_path(ROOT, args.release))) if args.release else campaigns(ROOT))
        else:
            result = set_host(ROOT, args.release, args.profile, args.status, result=args.result,
                              restored_state=args.restored_state, note=args.note)
    except Incomplete as exc:
        print(json.dumps({"state": "unavailable", "reason": str(exc)}))
        return 4
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"state": "refused", "reason": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
