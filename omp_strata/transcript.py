"""Read stock OMP session JSONL; never replay or mutate its authoritative history."""
from __future__ import annotations

import json
import re
from pathlib import Path

_TOOL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_USAGE = ("input", "output", "cacheRead", "cacheWrite", "totalTokens", "reasoningTokens")


def find_sessions(omp_home: Path) -> list[Path]:
    directory = omp_home / ".omp" / "profiles" / "omp-strata" / "agent" / "sessions"
    # Artifact directories beside a session may themselves contain JSONL; only
    # immediate children of OMP's encoded-cwd buckets are session transcripts.
    return sorted(directory.glob("*/*.jsonl")) if directory.is_dir() else []


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
