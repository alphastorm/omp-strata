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
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata.common import atomic_write_json, read_json, utc_now
from omp_strata.receipts import schema_errors
from scripts.upstream_watch import API, GITHUB, Incomplete, REPOS, auth_token, version
from scripts.verify_release import verify

ROOT = Path(__file__).resolve().parents[1]
# Lanes, not version pins. Only qualified release manifests select their predecessors.
LANES = (
    ("win11-rtxpro6000-iq3s-262k-slots4-parking", "rtxpro6000-win-a", "server"),
    ("win11-rtx5090-coder-iq1m-131k", "rtx5090-win-a", "server"),
    ("win11-rtx5090-coder-iq1m-262k", "rtx5090-win-a", "server"),
    ("win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking", "rtx3090-win-a", "server"),
    ("client-rtxpro6000-262k", "mac-studio-client", "client-route"),
)
TRANSITIONS = {
    "pending": {"queued", "blocked"}, "queued": {"running", "blocked"},
    "running": {"qualified", "failed", "blocked"}, "failed": {"queued", "blocked"},
    "blocked": {"queued"}, "qualified": set(),
}
FROZEN = ("repository", "release_id", "tag", "peeled_commit", "tag_object_sha", "assets", "published_at")


def frozen_assets(rows):
    if not isinstance(rows, list) or not rows:
        raise Incomplete("release assets unavailable")
    assets, names = [], set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("name"), str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", row["name"])
                or row["name"] in names or not isinstance(row.get("digest"), str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", row["digest"])
                or type(row.get("size")) is not int or row["size"] <= 0
                or row.get("state") != "uploaded"):
            raise Incomplete("release asset identity/digest/size unavailable or duplicated")
        names.add(row["name"])
        assets.append({key: row[key] for key in ("name", "digest", "size")})
    return sorted(assets, key=lambda asset: asset["name"])


def discover(api, tag):
    release, _ = api.get(f"{GITHUB}/repos/{REPOS['strata']}/releases/tags/{quote(tag, safe='')}")
    if (not isinstance(release, dict) or release.get("tag_name") != tag
            or type(release.get("draft")) is not bool or type(release.get("prerelease")) is not bool
            or type(release.get("id")) is not int or release["id"] <= 0):
        raise Incomplete("release identity/flags unavailable")
    if release["draft"] or release["prerelease"]:
        return {"state": "skipped", "tag": tag, "reason": "draft" if release["draft"] else "prerelease"}
    version(tag)
    published = release.get("published_at")
    if schema_errors(published, {"type": "string", "format": "date-time"}):
        raise Incomplete("release publication time unavailable")
    assets = frozen_assets(api.pages(
        f"{GITHUB}/repos/{REPOS['strata']}/releases/{release['id']}/assets?per_page=100"))
    if frozen_assets(release.get("assets")) != assets:
        raise Incomplete("release asset listing is incomplete or changed during discovery")
    commit, tag_object = api.commit(REPOS["strata"], tag)
    return {"repository": REPOS["strata"], "release_id": release["id"], "tag": tag,
            "peeled_commit": commit, "tag_object_sha": tag_object,
            "assets": assets, "published_at": published}


def state(hosts):
    live = [row for row in hosts if "superseded_by" not in row]
    if not live:
        return "superseded"
    if all(row["status"] == "qualified" for row in live):
        return "complete"
    return "running" if any(row["status"] in ("running", "qualified", "failed") for row in live) else "pending"


def validate(record):
    errors = schema_errors(record, read_json(ROOT / "schemas/release-campaign.schema.json"))
    if errors:
        raise ValueError("invalid campaign: " + "; ".join(errors))
    if len({a["name"] for a in record["assets"]}) != len(record["assets"]):
        raise ValueError("duplicate campaign asset")
    if len({h["profile_id"] for h in record["hosts"]}) != len(record["hosts"]):
        raise ValueError("duplicate campaign host profile")
    if record["status"] != state(record["hosts"]):
        raise ValueError("campaign status does not match its host rows")
    for row in record["hosts"]:
        if "superseded_by" in row and (row["status"] != "pending"
                or version(row["superseded_by"]) <= version(record["tag"])):
            raise ValueError("only pending host rows may be superseded by a newer release")
    return record


def campaign_path(root, tag):
    version(tag)  # Also prevents a tag from becoming a path traversal.
    return root / "releases" / "campaigns" / (tag + ".json")


def campaigns(root):
    records = [validate(read_json(path)) for path in sorted((root / "releases/campaigns").glob("*.json"))]
    return sorted(records, key=lambda record: version(record["tag"]))


def host_rows(root, tag):
    rows = []
    for family, host, kind in LANES:
        choices = []
        folder = "routes" if kind == "client-route" else "profiles"
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
            choices.append(((version(strata_tag), version(omp_tag)), identifier, manifest_ref, strata_tag, omp_tag))
        if not choices:
            raise ValueError(f"no qualified predecessor for {family}")
        _, identifier, manifest_ref, strata_tag, omp_tag = max(choices)
        if version(strata_tag) >= version(tag):
            raise ValueError(f"{family}: campaign release must be newer than qualified predecessor")
        candidate_id = f"{family}-strata{tag.removeprefix('v')}-omp{omp_tag.removeprefix('v')}"
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


def open_campaign(api, root, tag):
    snapshot = discover(api, tag)
    if snapshot.get("state") == "skipped":
        return snapshot
    records = campaigns(root)
    existing = next((record for record in records if record["tag"] == tag), None)
    if existing is not None:
        if any(existing[key] != snapshot[key] for key in FROZEN):
            raise Incomplete("moved tag or changed release/assets: frozen campaign was not modified")
        record = existing
    else:
        if any(record["release_id"] == snapshot["release_id"] for record in records):
            raise Incomplete("release id reused with another tag; frozen campaigns were not modified")
        record = {"schema_version": 1, **snapshot, "discovered_at": utc_now(), "status": "pending",
                  "hosts": host_rows(root, tag), "disposition_notes": [
                      "Discovery is not qualification, host admission, promotion or a default-runtime switch."]}
        atomic_write_json(campaign_path(root, tag), validate(record))
        records.append(record)
        records.sort(key=lambda item: version(item["tag"]))
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
    if status == "qualified":
        if not result or not (restored_state or row["restored_state_ref"]):
            raise ValueError("qualified requires a verified release manifest and restored-state reference")
        manifest = read_json(path)
        checked = verify(path, require_ready=True)
        if manifest.get("candidate_id") != profile_id or checked["status"] != "qualified" or checked["errors"]:
            raise ValueError("result is not this profile's ready qualified release manifest")
    if status in ("failed", "blocked") and not (result or note):
        raise ValueError("failed/blocked requires a result or disposition note")
    row["status"] = status
    if result and result not in row["result_refs"]:
        row["result_refs"].append(result)
    if restored_state:
        row["restored_state_ref"] = restored_state
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
            result = open_campaign(API(token=auth_token()), ROOT, args.release)
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
