#!/usr/bin/env python3
"""List literal QUICKSTART block hashes or statically check its CLI/profile references.

Addresses are exact Markdown heading text plus a zero-based block index. Only
parsing is performed: no shell, lifecycle dispatch, network, or host inspection.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omp_strata.cli import build_parser
from omp_strata.profile import load

HEADING = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")
PROFILE = re.compile(r"(?<![\w.-])profiles[/\\]([A-Za-z0-9][A-Za-z0-9.-]*\.json)\b")
SCRIPT = re.compile(r"(?:^|[/\\])scripts[/\\]omp_strata\.py$")
ASSIGN = re.compile(r"^\s*(?:export\s+)?(\$?[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")
VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))(?![\w:])")


@dataclass(frozen=True)
class Block:
    heading: str
    index: int
    language: str
    text: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def address(self) -> str:
        return f"{self.heading}[{self.index}]"


def parse_blocks(text: str) -> list[Block]:
    """Preserve all body bytes, including CRLF; reject ambiguous addresses."""
    lines = text.splitlines(keepends=True)
    blocks = []
    counts: dict[str, int] = {}
    heading = None
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        match = HEADING.fullmatch(line)
        if match:
            heading = match[1]
            if heading in counts:
                raise ValueError(f"duplicate heading: {heading}")
            counts[heading] = 0
        fence = FENCE.fullmatch(line)
        if fence:
            if heading is None:
                raise ValueError("fenced block has no heading")
            marker, language = fence.groups()
            end = re.compile(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$")
            j = i + 1
            while j < len(lines) and not end.fullmatch(lines[j].rstrip("\r\n")):
                j += 1
            if j == len(lines):
                raise ValueError(f"unclosed fence under heading: {heading}")
            blocks.append(Block(heading, counts[heading], language.strip(), "".join(lines[i + 1:j])))
            counts[heading] += 1
            i = j
        i += 1
    return blocks


def extract(doc: Path, heading: str, index: int = 0) -> Block:
    for block in parse_blocks(doc.read_bytes().decode("utf-8")):
        if (block.heading, block.index) == (heading, index):
            return block
    raise ValueError(f"no fenced block {index} under heading: {heading}")


def tokens(line: str, *, powershell: bool) -> list[str]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    # Backslashes are path separators in PowerShell, not shell escape characters.
    if powershell:
        lexer.escape = ""
    return list(lexer)


def profile_path(value: str, root: Path) -> Path:
    match = PROFILE.search(value)
    if not match or match.end() != len(value):
        raise ValueError("profile argument must resolve to a literal profiles/*.json reference")
    return root / "profiles" / match[1]


def check(text: str, root: Path = ROOT) -> dict:
    blocks = parse_blocks(text)
    errors: list[str] = []
    profiles = {root / "profiles" / m[1] for m in PROFILE.finditer(text)}
    variables: dict[str, str] = {}
    commands = 0
    parser = build_parser()
    for block in blocks:
        powershell = block.language.lower() in ("powershell", "pwsh", "ps1")
        # A continuation changes parsing only; block hashes always use the literal bytes.
        continuation = r"`\r?\n" if powershell else r"\\\r?\n"
        body = re.sub(continuation, "", block.text)
        for line in body.splitlines():
            assignment = ASSIGN.fullmatch(line)
            try:
                if assignment:
                    values = tokens(assignment[2], powershell=powershell)
                    key = assignment[1].lstrip("$")
                    # Unsupported expressions invalidate earlier values instead of reusing stale ones.
                    variables.pop(key, None)
                    if len(values) == 1:
                        variables[key] = VARIABLE.sub(lambda m: variables.get(m[1] or m[2], m[0]), values[0])
                    continue
                if "omp_strata.py" not in line:
                    continue
                words = tokens(line, powershell=powershell)
                for i, word in enumerate(words):
                    if not SCRIPT.search(word):
                        continue
                    commands += 1
                    end = next((j for j in range(i + 1, len(words)) if words[j] in (";", "&&", "||", "|")), len(words))
                    argv = [VARIABLE.sub(lambda m: variables.get(m[1] or m[2], m[0]), w)
                            for w in words[i + 1:end]]
                    output = io.StringIO()
                    with redirect_stderr(output), redirect_stdout(output):
                        try:
                            args = parser.parse_args(argv)
                        except SystemExit:
                            raise ValueError("CLI arguments rejected: " + output.getvalue().strip().split("\n")[-1]) from None
                    # Deliberately never call args.func: parsing must remain host-free.
                    if getattr(args, "profile", None) is not None:
                        profiles.add(profile_path(args.profile, root))
            except ValueError as exc:
                errors.append(f"{block.address}: {exc}")
    for path in sorted(profiles):
        try:
            load(path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"profiles/{path.name}: invalid or unavailable ({type(exc).__name__})")
    if not commands:
        errors.append("no scripts/omp_strata.py invocations found")
    return {"blocks": len(blocks), "commands": commands, "profiles": len(profiles), "errors": errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="list heading/index addresses and literal SHA-256 hashes")
    mode.add_argument("--check", action="store_true", help="parse CLI arguments and validate referenced profiles; never execute")
    parser.add_argument("--doc", type=Path, default=ROOT / "docs/QUICKSTART.md")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository containing referenced profiles")
    args = parser.parse_args(argv)
    try:
        text = args.doc.read_bytes().decode("utf-8")
        if args.list:
            print(json.dumps([{"heading": b.heading, "index": b.index, "language": b.language, "sha256": b.sha256}
                              for b in parse_blocks(text)], indent=2))
            return 0
        result = check(text, args.root)
        print(json.dumps(result, indent=2))
        return int(bool(result["errors"]))
    except (OSError, ValueError) as exc:
        print(f"Documented route rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
