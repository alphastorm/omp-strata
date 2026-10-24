#!/usr/bin/env python3
"""Read release notes/model-card metadata into a recommendation-only candidate ledger.

No assets, model weights, installs, services or scheduler entries are touched. Run daily by hand:
    python3 scripts/discover_candidates.py
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omp_strata.common import atomic_write_bytes, canonical_json, sha256_bytes
from scripts.upstream_watch import API, GITHUB, HF, Incomplete, auth_token

LEDGER = ROOT / "docs/candidates/ledger.jsonl"
ACTIVE_LIMIT = 3
GITHUB_SOURCES = {
    "Niko1221/Strata": ("strata-024", "parked", "Serial quality challenger only after a productive service; DeepSeek is not admitted."),
    "jpezzulli/sglang-rtxpro6000": ("penny-royal", "conditional", "Consider only after useful jobs expose a serving bottleneck; no trial tonight."),
    "ashhart/TensorFold": ("tensorfold", "conditional", "Qualify the actual route and format; native Windows requires a source build; no trial tonight."),
}
HF_SOURCES = {
    "nvidia/Qwen3.8-Flash-Next-FP4-Local": ("nvfp4-qad", "watch", "The explicitly pinned challenger alone may be staged; a newly discovered revision is not admitted."),
    "Qwen/Qwen3-ASR-1.7B": ("ocr-asr", "watch", "Only against an admitted audio task, licensing, coverage and citation contract; no GPU ASR service tonight."),
    "Qwen/Qwen3-ForcedAligner-0.6B": ("ocr-asr", "watch", "Five-minute/11-language alignment envelope; no speaker identity claim or GPU ASR service tonight."),
}
REQUIRED = {"candidate_id", "source_url", "pinned_revision", "date", "license", "relevant_change",
            "expected_task_benefit", "required_host", "estimated_evaluation_cost", "disposition", "admission_decision"}
DISPOSITIONS = {"active", "conditional", "parked", "watch", "promoted", "rejected", "deferred"}
SHA40 = re.compile(r"[0-9a-f]{40}\Z")


def identity(row):
    return row["source_url"], row["pinned_revision"]


def validate_rows(rows):
    latest = {}
    for row in rows:
        if (not isinstance(row, dict) or REQUIRED - row.keys()
                or not SHA40.fullmatch(str(row.get("pinned_revision", "")))
                or row.get("disposition") not in DISPOSITIONS
                or not str(row.get("source_url", "")).startswith("https://")
                or any(not row.get(key) for key in REQUIRED)):
            raise Incomplete("invalid candidate ledger record")
        latest[identity(row)] = row
    # One revision can have later disposition receipts; distinct active revisions consume distinct slots.
    if sum(row["disposition"] == "active" for row in latest.values()) > ACTIVE_LIMIT:
        raise Incomplete("active candidate limit exceeded (maximum 3)")
    return rows


def read_ledger(path):
    if not path.exists():
        return []
    try:
        return validate_rows([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])
    except (ValueError, TypeError, KeyError):
        raise Incomplete("unreadable candidate ledger") from None


def commit_for_tag(api, repo, tag):
    """Peel arbitrary release tag names (including pennyroyal-vN), never target_commitish."""
    data, _ = api.get(f"{GITHUB}/repos/{repo}/git/ref/tags/{quote(tag, safe='')}")
    obj = data.get("object", {})
    if obj.get("type") == "tag":
        tag_data, _ = api.get(f"{GITHUB}/repos/{repo}/git/tags/{obj.get('sha')}")
        if tag_data.get("sha") != obj.get("sha") or tag_data.get("tag") != tag:
            raise Incomplete("release tag identity mismatch")
        obj = tag_data.get("object", {})
    if obj.get("type") != "commit" or not SHA40.fullmatch(str(obj.get("sha", ""))):
        raise Incomplete("release has no immutable commit")
    return obj["sha"]


def record(candidate, source, revision, date, license_name, change, decision, disposition, metadata, observed):
    return {"candidate_id": candidate, "source_url": source, "pinned_revision": revision,
            "date": date[:10], "license": license_name, "relevant_change": change,
            "expected_task_benefit": "Recommendation only: review source-linked changes against an observed task gap.",
            "required_host": "rtxpro6000-win-a" if candidate != "ocr-asr" else "An explicitly admitted document/audio worker route",
            "estimated_evaluation_cost": {"metadata_gpu_host_seconds": 0, "gpu_evaluation": "Not admitted by discovery; estimate before manual activation."},
            "disposition": disposition, "admission_decision": decision, "observed_at": observed,
            "metadata_sha256": sha256_bytes(canonical_json(metadata))}


def discover(api, *, observed=None):
    observed = observed or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []
    for repo, (candidate, disposition, decision) in GITHUB_SOURCES.items():
        releases, _ = api.get(f"{GITHUB}/repos/{repo}/releases?per_page=5")
        if not isinstance(releases, list):
            raise Incomplete("release metadata is not a list")
        # Deliberately bounded news window, not a claim to enumerate the entire upstream history.
        for release in releases:
            if release.get("draft") or release.get("prerelease"):
                continue
            tag = release["tag_name"]
            revision = commit_for_tag(api, repo, tag)
            license_data, _ = api.get(f"{GITHUB}/repos/{repo}/license?ref={revision}")
            license_name = (license_data.get("license") or {}).get("spdx_id", "NOASSERTION")
            body = release.get("body") or "No release notes; manual source review required."
            row = record(candidate, release["html_url"], revision, release["published_at"], license_name,
                         f"{tag}: {body[:1200]}", decision, disposition,
                         {"release": release, "license": license_data}, observed)
            rows.append(row)
    for repo, (candidate, disposition, decision) in HF_SOURCES.items():
        data, _ = api.get(f"{HF}/api/models/{repo}")
        revision = data.get("sha")
        if data.get("id") != repo or not SHA40.fullmatch(str(revision)):
            raise Incomplete("model metadata lacks its immutable revision")
        # Model-card frontmatter is cardData; bind README's git blob without downloading any file.
        tree, _ = api.get(f"{HF}/api/models/{repo}/tree/{revision}?recursive=false&expand=false")
        cards = [entry for entry in tree if entry.get("path") == "README.md" and entry.get("type") == "file"]
        if len(cards) != 1 or not SHA40.fullmatch(str(cards[0].get("oid", ""))):
            raise Incomplete("model card metadata missing")
        card = data.get("cardData") or {}
        license_name = card.get("license_name") or card.get("license") or "NOASSERTION"
        row = record(candidate, f"{HF}/{repo}", revision, data["lastModified"], license_name,
                     f"Model card {cards[0]['oid']}; {json.dumps(card, sort_keys=True)}", decision, disposition,
                     {"card": card, "card_blob": cards[0]["oid"], "revision": revision}, observed)
        row["model_card_blob"] = cards[0]["oid"]
        rows.append(row)
    return validate_rows(rows)


def merge_rows(existing, discovered):
    validate_rows(existing)
    validate_rows(discovered)
    known = {identity(row) for row in existing}
    added = []
    for row in discovered:
        if identity(row) not in known:
            added.append(row)
            known.add(identity(row))
    return validate_rows([*existing, *added]), len(added)


def update_ledger(path, discovered, *, dry_run=False):
    if dry_run:
        return merge_rows(read_ledger(path), discovered)[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    try:
        stream = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise Incomplete("candidate ledger is locked; reconcile the writer, never steal its lock") from None
    try:
        with stream:
            rows, added = merge_rows(read_ledger(path), discovered)
            if added:
                atomic_write_bytes(path, b"".join(canonical_json(row) + b"\n" for row in rows))
            return added
    finally:
        lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = discover(API(token=auth_token()))
        added = update_ledger(args.ledger, rows, dry_run=args.dry_run)
        print(json.dumps({"discovered": len(rows), "added": added, "active_limit": ACTIVE_LIMIT,
                          "dry_run": args.dry_run, "automatic_deployment": False, "weight_downloads": 0}))
        return 0
    except (Incomplete, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc) if isinstance(exc, Incomplete) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
