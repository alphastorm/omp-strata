"""Pinned artifact materialization: download or reuse, then verify size and SHA-256 before use."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .common import IntegrityError, download_verified, verify_file
from .layout import Layout, host_platform


@dataclass(frozen=True)
class Item:
    name: str
    url: str
    dest: Path
    bytes: int
    sha256: str
    source: str


def plan(layout: Layout, *, platform: str | None = None, only: set[str] | None = None) -> list[Item]:
    p = layout.profile.data
    plat = platform or host_platform()
    items: list[Item] = []
    omp = layout.profile.omp_artifact(plat)
    items.append(Item("omp", omp["url"], layout.omp_binary(plat), omp["bytes"], omp["sha256"], omp["sha256_source"]))
    if plat != "darwin-arm64":                       # the Strata runtime never runs on macOS
        eng = p["strata"]["artifacts"]["engine_archive"]
        if plat == "windows-x64":
            items.append(Item("engine", eng["url"], layout.engine_archive, eng["bytes"], eng["sha256"],
                              eng["sha256_source"]))
        ll = p["strata"]["artifacts"]["llama_cpp_archive"]
        items.append(Item("llama", ll["url"], layout.llama_archive, ll["bytes"], ll["sha256"], ll["sha256_source"]))
        for f in p["model"]["files"]:
            items.append(Item("model", layout.profile.model_url(f), layout.model_file(f), f["bytes"], f["sha256"],
                              f["sha256_source"]))
    if only:
        items = [i for i in items if i.name in only]
    return items


def required_space(items: list[Item]) -> int:
    """Bytes still to download (reused, verified files need none; a partial file counts only its remainder)."""
    need = 0
    for i in items:
        if i.dest.is_file() and i.dest.stat().st_size == i.bytes:
            continue
        partial = i.dest.with_name(i.dest.name + ".partial")
        have = partial.stat().st_size if partial.exists() else 0
        need += max(0, i.bytes - have)
    return need


def fetch(layout: Layout, *, platform: str | None = None, only: set[str] | None = None,
          log: Callable[[str], None] = print, check_space: bool = True) -> list[Item]:
    items = plan(layout, platform=platform, only=only)
    if check_space:
        need = required_space(items)
        layout.root.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(layout.root).free
        if need > free:
            raise IntegrityError(f"insufficient disk: need {need / 1e9:.1f} GB more, {free / 1e9:.1f} GB free")
    for item in items:
        download_verified(item.url, item.dest, item.bytes, item.sha256, source=item.source, log=log)
        if item.name == "omp" and not item.dest.name.endswith(".exe"):
            item.dest.chmod(0o755)               # verified bytes; the client must be runnable in place
    return items


def verify(layout: Layout, *, platform: str | None = None, deep: bool = False,
           log: Callable[[str], None] = print) -> list[str]:
    problems = []
    for item in plan(layout, platform=platform):
        try:
            verify_file(item.dest, item.bytes, item.sha256, source=item.source, deep=deep, log=log)
        except IntegrityError as exc:
            problems.append(str(exc))
    return problems
