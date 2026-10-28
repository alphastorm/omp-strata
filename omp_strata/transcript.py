"""Read stock OMP session JSONL; never replay or mutate its authoritative history."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_TOOL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_USAGE = ("input", "output", "cacheRead", "cacheWrite", "totalTokens", "reasoningTokens")
_CONVERSATION_TYPES = {"message", "custom_message", "branch_summary", "reset_boundary"}


def find_sessions(omp_home: Path) -> list[Path]:
    """One authoritative file per conversation; only OMP's explicit continuation links join copies."""
    directory = omp_home / ".omp" / "profiles" / "omp-strata" / "agent" / "sessions"
    # Artifact directories beside a session may themselves contain JSONL; only
    # immediate children of OMP's encoded-cwd buckets are session transcripts.
    paths = sorted(directory.glob("*/*.jsonl")) if directory.is_dir() else []
    entries = {path: load(path) for path in paths}
    headers = {path: _header(rows) for path, rows in entries.items()}
    by_id = {}
    for path, header in headers.items():
        session_id = header.get("id")
        if isinstance(session_id, str) and session_id:
            key = (path.parent, session_id)
            if key in by_id:
                raise ValueError("duplicate session id in one profile bucket")
            by_id[key] = path
    families = {}
    ancestors = {}
    for path in paths:
        chain, current = set(), path
        while True:
            if current in chain:
                raise ValueError("cyclic session continuation links")
            chain.add(current)
            parent_id = headers[current].get("continuationOf")
            if not parent_id:
                root = (current.parent, headers[current].get("id") or current)
                break
            if not isinstance(parent_id, str):
                raise ValueError("invalid session continuation link")
            parent = by_id.get((current.parent, parent_id))
            if parent is None:
                root = (current.parent, parent_id)
                break
            current = parent
        ancestors[path] = chain - {path}
        families.setdefault(root, []).append(path)
    selected = []
    for copies in families.values():
        if len(copies) == 1:
            selected.append(copies[0])
            continue
        activity = {path: _activity(entries[path]) for path in copies}
        # A continuation carrying an ancestor's newest turn supersedes that ancestor,
        # even when both copies have the same last-turn timestamp.
        remaining = [path for path in copies if not any(
            path in ancestors[copy] and activity[path][1] is not None
            and any(row.get("type") != "session" and row.get("id") == activity[path][1]
                    for row in entries[copy]) for copy in copies if copy != path)]
        newest_time = max(activity[path][0] for path in remaining)
        newest = [path for path in remaining if activity[path][0] == newest_time]
        if len(newest) != 1:
            raise ValueError("ambiguous session continuations: no unique newest conversation turn")
        selected.append(newest[0])
    return sorted(selected)


def _header(entries: list[dict]) -> dict:
    return next((entry for entry in entries if entry.get("type") == "session"), {})


def _activity(entries: list[dict]) -> tuple[datetime, str | None]:
    # OMP 18.13.2 session-listing.ts lastActivity: idle usage, compaction and
    # session_exit writes do not advance the conversation. Never use file mtime.
    for entry in reversed(entries):
        if entry.get("type") not in _CONVERSATION_TYPES:
            continue
        custom_type = (entry.get("customType") if entry.get("type") == "custom_message"
                       else (entry.get("message") or {}).get("customType"))
        if custom_type == "eval-state-context":
            continue
        timestamp = _timestamp(entry.get("timestamp"))
        if timestamp is not None:
            return timestamp, entry.get("id")
    return _timestamp(_header(entries).get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc), None


def _timestamp(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def session_for(omp_home: Path, workspace: Path) -> Path | None:
    """Select this run's workspace conversation, refusing unrelated same-workspace sessions."""
    matches = []
    for path in find_sessions(omp_home):
        cwd = _header(load(path)).get("cwd")
        if cwd and Path(cwd).resolve() == workspace.resolve():
            matches.append(path)
    if len(matches) > 1:
        raise ValueError("ambiguous independent sessions for the requested workspace")
    return matches[0] if matches else None


def continues_session(previous: Path, current: Path) -> bool:
    """A changed file is the same conversation only through continuationOf, never parentSession alone."""
    if previous == current:
        return True
    if previous.parent != current.parent:
        return False
    headers = [_header(load(path)) for path in current.parent.glob("*.jsonl")]
    by_id = {}
    for header in headers:
        session_id = header.get("id")
        if isinstance(session_id, str) and session_id:
            if session_id in by_id:
                raise ValueError("duplicate session id in one profile bucket")
            by_id[session_id] = header
    target = _header(load(previous)).get("id")
    header, seen = _header(load(current)), set()
    while header.get("continuationOf"):
        parent_id = header["continuationOf"]
        if not isinstance(parent_id, str) or parent_id in seen:
            raise ValueError("invalid or cyclic session continuation links")
        if target and parent_id == target:
            return True
        seen.add(parent_id)
        header = by_id.get(parent_id, {})
    return False


def load(path: Path) -> list[dict]:
    entries = []
    with path.open(encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid session JSON at line {number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"session entry at line {number} must be an object")
            entries.append(value)
    return entries


def _messages(entries):
    for entry in entries:
        if entry.get("type") == "message" and isinstance(entry.get("message"), dict):
            yield entry["message"]


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(block["text"] for block in content
                     if isinstance(block, dict) and isinstance(block.get("text"), str))


def _cycles(entries) -> tuple[list[dict], list[str]]:
    cycles = []
    orphan_results = []
    for message in _messages(entries):
        if message.get("role") == "assistant":
            for block in message.get("content", []):
                if not isinstance(block, dict) or block.get("type") != "toolCall":
                    continue
                cycles.append({"id": block.get("id"), "name": block.get("name"),
                               "arguments": block.get("arguments"), "result_text": "",
                               "is_error": None, "result_found": False})
        elif message.get("role") == "toolResult":
            call_id = message.get("toolCallId")
            matching = next((cycle for cycle in cycles
                             if cycle["id"] == call_id and cycle["name"] == message.get("toolName")
                             and not cycle["result_found"]), None)
            if matching is None:
                orphan_results.append(call_id)
            else:
                matching.update(result_found=True, is_error=bool(message.get("isError")),
                                result_text=_text(message.get("content")))
    return cycles, orphan_results


def tool_cycles(entries) -> list[dict]:
    return _cycles(entries)[0]


def summarize(path: Path) -> dict:
    entries = load(path)
    assistants = [message for message in _messages(entries) if message.get("role") == "assistant"]
    # OMP accounts auxiliary/compaction model calls separately. Include their
    # route and usage, but do not invent extra conversational assistant turns.
    model_calls = assistants + [entry for entry in entries if entry.get("type") == "model_usage"]
    usage = {key: sum(call.get("usage", {}).get(key, 0) or 0 for call in model_calls) for key in _USAGE}
    cycles, orphans = _cycles(entries)
    ids = [cycle["id"] for cycle in cycles]
    valid_ids = all(isinstance(value, str) and _TOOL_ID.fullmatch(value) for value in ids)
    unique_ids = len({value for value in ids if isinstance(value, str)}) == len(ids)
    return {
        "assistant_count": len(assistants),
        "stopReasons": [message.get("stopReason") for message in assistants],
        "providers": sorted({call["provider"] for call in model_calls if call.get("provider")}),
        "models": sorted({call["model"] for call in model_calls if call.get("model")}),
        "apis": sorted({call["api"] for call in model_calls if call.get("api")}),
        "usage": usage,
        "tool_ids_well_formed": bool(valid_ids), "tool_ids_unique": unique_ids,
        "orphan_results": orphans,
        "calls_without_results": [cycle["id"] for cycle in cycles if not cycle["result_found"]],
        "tool_count": len(cycles),
        "tool_errors": sum(cycle["is_error"] is True for cycle in cycles),
    }
