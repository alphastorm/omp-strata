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
                                   client_matches, discover_release, version)
from scripts.verify_release import verify

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/release-campaign.schema.json"
# Lanes, not version pins. Only qualified release manifests select their predecessors.
# One row per lane. A lane lists its stock variants' profile families (each a profile of its own, AGENTS.md); its
# predecessor is the newest qualified profile across them, and the next candidate keeps that variant. Several qualified
# variants at the same Strata and OMP release rank by this order, the lane's current variant last.
LANES = (
    (("win11-rtxpro6000-iq3s-262k-slots4-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-batchmtp-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-df2conf055-pledirect-kvvram-envpg-parking",
      "win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking"),
     "rtxpro6000-win-a", "server"),
    # IQ3_S low-RAM families rank below the Coder: the 131K one is a qualified non-current alternate (owner,
    # 2026-11-09), the 262K one a draft screen, so neither becomes a lane's predecessor while the Coder qualifies.
    (("win11-rtx5090-iq3s-131k-lowram", "win11-rtx5090-coder-iq1m-131k"), "rtx5090-win-a", "server"),
    (("win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg",
      "win11-rtx5090-coder-iq1m-262k", "win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow",
      "win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt",
      "win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc",
      "win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg"), "rtx5090-win-a", "server"),
    (("win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw",
      "win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking",
      "win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts",
      "win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt",
      "win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt"),
     "rtx3090-win-a", "server"),
    (("client-rtxpro6000-262k", "client-rtxpro6000-262k-batchmtp-pledirect",
      "client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg", "client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg",
      "client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt", "client-rtxpro6000-262k-df2-pledirect-kvvram-envpg"),
     "mac-studio-client", "client-route"),
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
    if record["schema_version"] >= 2:
        if len({a["id"] for a in record["assets"]}) != len(record["assets"]):
            raise ValueError("duplicate campaign asset id")
        if record["prerelease"] != (prerelease_tag(record["tag"]) or record["github_prerelease"]):
            raise ValueError("campaign prerelease classification does not match its source")
        for asset in record["assets"]:
            expected = f"https://github.com/{record['repository']}/releases/download/{record['tag']}/{asset['name']}"
            if asset["url"] != expected:
                raise ValueError("campaign asset URL does not match its source")
    if record["schema_version"] == 3:
        omp = record["omp_release"]
        if (omp["tag"] != record["omp_tag"] or omp["prerelease"]
                or omp["github_prerelease"] or prerelease_tag(omp["tag"])):
            raise ValueError("campaign OMP snapshot must match its stable OMP tag")
        if len({a["id"] for a in omp["assets"]}) != len(omp["assets"]) or len(
                {a["name"] for a in omp["assets"]}) != len(omp["assets"]):
            raise ValueError("duplicate OMP campaign asset")
        for asset in omp["assets"]:
            if asset["url"] != f"https://github.com/{REPOS['omp']}/releases/download/{omp['tag']}/{asset['name']}":
                raise ValueError("OMP campaign asset URL does not match its source")
        if any(not row["profile_id"].endswith("-omp" + record["omp_tag"].removeprefix("v"))
               for row in record["hosts"]):
            raise ValueError("campaign host OMP tag mismatch")
    if len({h["profile_id"] for h in record["hosts"]}) != len(record["hosts"]):
        raise ValueError("duplicate campaign host profile")
    if record["status"] != state(record["hosts"]):
        raise ValueError("campaign status does not match its host rows")
    for row in record["hosts"]:
        if "superseded_by" in row:
            target = row["superseded_by"].split("+omp")
            newer = ((version(target[0]), version(target[1])) > campaign_tuple(record)
                     if len(target) == 2 else version(target[0]) > version(record["tag"]))
            if row["status"] != "pending" or record.get("prerelease", False) or prerelease_tag(target[0]) or not newer:
                raise ValueError("only pending host rows may be superseded by a newer release tuple")
    return record


def campaign_client(record):
    """The client tag a campaign's tuple orders by: its frozen OMP tag, else its newest host row's own pin."""
    return record.get("omp_tag") or max((row["profile_id"].rsplit("-omp", 1)[1] for row in record["hosts"]),
                                        key=version)


def campaign_tuple(record):
    return version(record["tag"]), version(campaign_client(record))


def campaign_path(root, tag, omp_tag=None):
    """The identity alone names the file: `<tag>.json` without a client tag, `<tag>+omp<ver>.json` with one."""
    version(tag)  # Also prevents a tag from becoming a path traversal.
    if omp_tag is None:
        return root / "releases" / "campaigns" / (tag + ".json")
    version(omp_tag)
    return root / "releases" / "campaigns" / (tag + "+omp" + omp_tag.removeprefix("v") + ".json")


def refuse_alias(root, records, tag, omp_tag, key):
    """One file per release tuple: another identity that already records `key` is named, never redirected to."""
    path = campaign_path(root, tag, omp_tag)
    for prior in records:
        other = campaign_path(root, prior["tag"], prior.get("omp_tag"))
        if other != path and campaign_tuple(prior) == key:
            raise ValueError(f"{other.name} already records the same release tuple as {path.name}; refused")


def campaigns(root):
    records = []
    for path in sorted((root / "releases/campaigns").glob("*.json")):
        record = validate(read_json(path))
        if path != campaign_path(root, record["tag"], record.get("omp_tag")):
            raise ValueError(f"{path.name} does not hold the campaign its name identifies")
        refuse_alias(root, records, record["tag"], record.get("omp_tag"), campaign_tuple(record))
        records.append(record)
    return sorted(records, key=campaign_tuple)


def host_rows(root, tag, candidate_omp=None):
    """One pending row per lane, named from its newest qualified predecessor; `candidate_omp` moves every candidate
    to that stock OMP tag (each row still records its predecessor's own OMP pin)."""
    if candidate_omp is not None:
        version(candidate_omp)  # A stable release tag only; it becomes part of every candidate id.
    rows = []
    for families, host, kind in LANES:
        choices = []
        folder = "routes" if kind == "client-route" else "profiles"
        for rank, family in enumerate(families):
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
                choices.append(((version(strata_tag), version(omp_tag)), rank, identifier, manifest_ref, strata_tag,
                                omp_tag, family))
        if not choices:
            raise ValueError(f"no qualified predecessor for {families[0]}")
        _, _, identifier, manifest_ref, strata_tag, omp_tag, family = max(choices)
        if ((version(tag), version(candidate_omp or omp_tag)) <= (version(strata_tag), version(omp_tag))
                or candidate_omp is None and version(strata_tag) >= version(tag)):
            raise ValueError(f"{family}: campaign release tuple must be newer than qualified predecessor")
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


def tuple_generation(record):
    """Tuple campaigns (schema 3) and historical single-tag campaigns are never compared with each other."""
    return record["schema_version"] == 3


def _supersede_pending(record, newest):
    successor = newest["tag"] + ("+omp" + newest["omp_tag"].removeprefix("v") if tuple_generation(newest) else "")
    changed = False
    for row in record["hosts"]:
        if row["status"] == "pending" and "superseded_by" not in row:
            row["superseded_by"] = successor
            row["disposition_notes"].append("Pending qualification coalesced into " + successor)
            changed = True
    if changed:
        record["status"] = state(record["hosts"])
    return changed


def _newest_stable(records, intake):
    return next((prior for prior in reversed(records) if not prior.get("prerelease", False)
                 and tuple_generation(prior) == tuple_generation(intake)), None)


def coalesce(root, records, intake=None):
    """Settle older pending rows within the intake record's generation (default: the newest stable record's)."""
    stable = [record for record in records if not record.get("prerelease", False)]
    if not stable:
        return
    newest = _newest_stable(stable, intake or stable[-1])
    if newest is None:
        return
    for record in stable:
        if (record is newest or tuple_generation(record) != tuple_generation(newest)
                or record["status"] in ("complete", "superseded")):
            continue
        if _supersede_pending(record, newest):
            atomic_write_json(campaign_path(root, record["tag"], record.get("omp_tag")), validate(record))


def open_campaign(api, root, tag, *, allow_prerelease=False, check=False, omp_tag=None):
    snapshot = discover_release(api, REPOS["strata"], tag, allow_prerelease=allow_prerelease)
    if snapshot.get("state") == "skipped":
        return snapshot
    records = campaigns(root)
    path = campaign_path(root, tag, omp_tag)
    # The returned record is the object coalescing settles, so the caller sees its durable state.
    existing = next((prior for prior in records if campaign_path(root, prior["tag"], prior.get("omp_tag")) == path),
                    None)
    if existing is None and omp_tag is not None:  # Refused by name before client discovery or predecessor checks.
        refuse_alias(root, records, tag, omp_tag, (version(tag), version(omp_tag)))
    for prior in records:
        if prior["tag"] == tag:
            assert_same_release(prior, snapshot)
    omp_snapshot = None
    if omp_tag is not None:
        omp_snapshot = discover_release(api, REPOS["omp"], omp_tag)
        if omp_snapshot.get("state") == "skipped":
            raise Incomplete("campaign requires a stable published OMP release")
        # Every tuple campaign naming this client froze one identity, whichever engine it pairs with.
        for prior in records:
            if tuple_generation(prior) and version(prior["omp_tag"]) == version(omp_tag):
                assert_same_release(prior["omp_release"], omp_snapshot)
    if existing is not None:
        record = existing
    else:
        if any(record["release_id"] == snapshot["release_id"] and record["tag"] != tag for record in records):
            raise Incomplete("release id reused with another tag; frozen campaigns were not modified")
        record = {"schema_version": 2, **snapshot, "discovered_at": utc_now(), "status": "pending",
                  "hosts": host_rows(root, tag, omp_tag), "disposition_notes": [
                      "Discovery is not qualification, host admission, promotion or a default-runtime switch."]}
        if omp_snapshot is not None:
            record.update(schema_version=3, omp_tag=omp_tag, omp_release=omp_snapshot)
        else:
            refuse_alias(root, records, tag, None, campaign_tuple(record))
        if not snapshot["prerelease"]:
            newest = _newest_stable(records, record)
            if newest is not None and campaign_tuple(record) < campaign_tuple(newest):
                _supersede_pending(record, newest)  # Its first durable state must already be non-admissible.
        validate(record)
        if not check:
            atomic_write_json(path, record)
        records.append(record)
        records.sort(key=campaign_tuple)
    if not check and not snapshot["prerelease"]:
        coalesce(root, records, record)
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


def candidate_clients(root, profile_path):
    """The OMP pins a candidate runs: its own, or each client-route member server profile's."""
    profile = read_json(profile_path)
    if profile.get("kind") != "client-route":
        return [profile["omp"]]
    return [read_json(root / "profiles" / (member["server_profile"] + ".json"))["omp"]
            for member in profile["members"]]


def set_host(root, tag, profile_id, status, *, result=None, restored_state=None, note=None, omp_tag=None):
    campaign_file = campaign_path(root, tag, omp_tag)
    record = validate(read_json(campaign_file)) if campaign_file.is_file() or omp_tag is None else None
    single = campaign_path(root, tag)
    siblings = [validate(read_json(other)) for other in (single, *sorted(single.parent.glob(tag + "+omp*.json")))
                if other != campaign_file and other.is_file()]
    refuse_alias(root, siblings, tag, omp_tag,
                 campaign_tuple(record) if record is not None else (version(tag), version(omp_tag)))
    if record is None:
        record = validate(read_json(campaign_file))
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
        if tuple_generation(record) and not all(
                client.get("tag") == record["omp_tag"]
                and client_matches(record["omp_release"], client.get("source_commit"), client.get("artifacts"))
                for client in candidate_clients(root, path.parent / manifest["profile"]["path"])):
            raise ValueError("result's OMP client differs from the campaign's frozen client snapshot")
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
    atomic_write_json(campaign_file, validate(record))
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
    status.add_argument("--omp-tag")
    update = commands.add_parser("set-host")
    update.add_argument("--release", required=True)
    update.add_argument("--profile", required=True)
    update.add_argument("--status", required=True, choices=tuple(TRANSITIONS))
    update.add_argument("--result")
    update.add_argument("--restored-state")
    update.add_argument("--note")
    update.add_argument("--omp-tag")
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
            if args.omp_tag and not args.release:
                raise ValueError("--omp-tag requires --release")
            result = (validate(read_json(campaign_path(ROOT, args.release, args.omp_tag)))
                      if args.release else campaigns(ROOT))
        else:
            result = set_host(ROOT, args.release, args.profile, args.status, result=args.result,
                              restored_state=args.restored_state, note=args.note, omp_tag=args.omp_tag)
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
