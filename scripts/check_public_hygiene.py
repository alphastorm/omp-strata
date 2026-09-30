#!/usr/bin/env python3
"""Scan public candidate bytes, staged blobs, or all reachable history; never echo matches."""
from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import re
import subprocess
import sys

PLACEHOLDERS = {"<user>", "<username>", "<name>", "<home>", "<redacted>"}
PATTERNS = {
    "home-path": r"(?:/(?:Users|home)/|[A-Za-z]:[\\/]+Users[\\/]+)([^\\/\s\"'`:,;]+)",
    "tailnet-ipv6": r"fd7a:" + r"115c:a1e0:[0-9a-f:]*",
    "tailnet-domain": r"\b(?:[a-z0-9-]+\.)+ts\.net\b",
    "email": r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[a-z]{2,}\b",
    "private-key": r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----",
    "ssh-public-key": r"\bssh-(?:ed25519|rsa)\s+AAAA[A-Za-z0-9+/=]*",
    "token": r"\b(?:ghp_|github_pat_|hf_)[A-Za-z0-9_]{12,}|\bsk-[A-Za-z0-9_-]{16,}|\bxox[a-z]?-[A-Za-z0-9-]{12,}|\bAKIA[A-Z0-9]{16}\b|\bBearer\s+[A-Za-z0-9._~+/-]{20,}=*",
    "gpu-uuid": r"\bGPU-[0-9a-f]{8}-[0-9a-f-]+\b",
    "mac-address": r"(?<![0-9a-f:])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![0-9a-f:])|(?<![0-9a-f-])(?:[0-9a-f]{2}-){5}[0-9a-f]{2}(?![0-9a-f-])",
    "windows-sid": r"\bS-1-\d+(?:-\d+){2,}\b",
    "ssh-fingerprint": r"\bSHA256:[A-Za-z0-9+/]{43}=?(?![A-Za-z0-9+/=])",
}
RULES = {key: re.compile(pattern, re.I) for key, pattern in PATTERNS.items()}
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
NETWORKS = tuple(ipaddress.ip_network((base, prefix)) for base, prefix in
                 ((10 << 24, 8), ((172 << 24) + (16 << 16), 12),
                  ((192 << 24) + (168 << 16), 16), ((100 << 24) + (64 << 16), 10)))


def scan(data: bytes, denylist=()) -> list[tuple[int, str]]:
    if b"\0" in data[:8192]:
        return []
    findings = set()
    for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
        for rule, pattern in RULES.items():
            for match in pattern.finditer(line):
                if rule == "home-path" and match.group(1).lower() in PLACEHOLDERS:
                    continue
                if rule == "email":
                    email = match.group().lower()
                    if email in ("git@github.com", "noreply@github.com") or email.endswith("@example.com"):
                        continue
                findings.add((number, rule))
        for match in IPV4.finditer(line):
            try:
                addr = ipaddress.ip_address(match.group())
            except ValueError:
                continue
            if any(addr in net for net in NETWORKS):
                findings.add((number, "private-ipv4"))
        if any(term.casefold() in line.casefold() for term in denylist):
            findings.add((number, "private-denylist"))
    return sorted(findings)


def git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], input=input, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True, timeout=120).stdout


def candidates(root: Path, *, staged=False, history=False):
    if staged:
        names = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z").split(b"\0")
        for raw in filter(None, names):
            name = os.fsdecode(raw)
            yield name, git(root, "show", ":" + name)
    elif history:
        objects = git(root, "rev-list", "--objects", "--all").splitlines()
        ids = [line.split(b" ", 1)[0] for line in objects]
        names = {line.split(b" ", 1)[0]: os.fsdecode(line.split(b" ", 1)[1])
                 for line in objects if b" " in line}
        if not ids:
            return
        data = git(root, "cat-file", "--batch", input=b"\n".join(ids) + b"\n")
        offset = 0
        while offset < len(data):
            end = data.index(b"\n", offset)
            oid, kind, size = data[offset:end].split()
            start = end + 1
            offset = start + int(size) + 1
            if kind == b"blob":
                yield names.get(oid, "blob") + "@" + oid[:12].decode(), data[start:offset - 1]
    else:
        names = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0")
        for raw in sorted(set(filter(None, names))):
            name = os.fsdecode(raw)
            path = root / name
            if path.is_symlink():
                yield name, os.readlink(path).encode()
            elif path.is_file():
                yield name, path.read_bytes()


def display_path(name: str, denylist) -> str:
    # Paths themselves may contain personal data; mask the entire label in that case.
    if scan(name.encode(), denylist):
        return "[masked-path]"
    return name.replace("\n", "?").replace("\r", "?")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--history", action="store_true")
    parser.add_argument("--denylist", type=Path)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    if args.paths and (args.staged or args.history):
        parser.error("explicit paths cannot be combined with git modes")
    denyfile = args.denylist
    if denyfile is None:
        configured = os.environ.get("OMP_STRATA_HYGIENE_DENYLIST")
        denyfile = Path(configured) if configured else Path.home() / ".config/omp-strata/hygiene-denylist.txt"
    try:
        if denyfile.is_file():
            denylist = [line.strip() for line in denyfile.read_text().splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
        elif args.denylist or os.environ.get("OMP_STRATA_HYGIENE_DENYLIST"):
            print("error: configured denylist unavailable", file=sys.stderr)
            return 2
        else:
            denylist = []
            print("warning: no private denylist found; generic rules only", file=sys.stderr)
        if args.paths:
            files = []
            for path in args.paths:
                if not path.exists() and not path.is_symlink():
                    raise FileNotFoundError
                files.extend(sorted(path.rglob("*")) if path.is_dir() else [path])
            sources = ((str(path), os.readlink(path).encode() if path.is_symlink() else path.read_bytes())
                       for path in files if path.is_file() or path.is_symlink())
        else:
            root = Path(os.fsdecode(git(Path.cwd(), "rev-parse", "--show-toplevel")).strip())
            sources = candidates(root, staged=args.staged, history=args.history)
        count = 0
        for name, data in sources:
            found = scan(data, denylist)
            found.extend((1, rule) for _, rule in scan(name.encode(), denylist))
            for line, rule in sorted(set(found)):
                print(f"{display_path(name, denylist)}:{line}: {rule} [MASKED]")
                count += 1
        return int(count > 0)
    except (OSError, subprocess.SubprocessError, ValueError):
        print("error: could not read candidate content", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
