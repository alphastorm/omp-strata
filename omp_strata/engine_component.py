"""Stock Strata engine component tarballs (v0.2.1+): inspect them and stage one into the native engine folder.

A component release ships its engine as `strata-engine-<version>-<platform>-<backend>-<variant>.tar.gz`, every file at
the archive root, plus `engine-component.json` listing each other file's bytes and SHA-256. Stock native setup.py (its
packaged-Control mode off) still asks for the old single zip, but takes its "ready-made engine already installed" path
when `engine/` already holds BUILD.json and strata.exe of a sufficient version. omp-strata therefore stages the verified
files there itself before setup runs; setup downloads and compiles nothing.

Trust: the archive is pinned by the publisher's SHA-256, the profile pins the raw manifest's SHA-256 and BUILD.json's
identity, and every member is checked against the manifest. The manifest's ed25519 signature is not verified, and no
signed feed, Control package or updater state is consumed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
from pathlib import Path
from typing import IO

from .common import CHUNK, IntegrityError, sha256_file, verify_file

MANIFEST = "engine-component.json"
BUILD = "BUILD.json"
ENTRYPOINT = "strata.exe"
MAX_MEMBERS = 32
MAX_JSON_BYTES = 1 << 20
MAX_TOTAL_BYTES = 4 << 30
PIN_KEYS = ("format", "platform", "backend", "variant", "manifest_sha256", "build_id", "build_source", "build_commit")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PLAIN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def archive_name(version: str, platform: str, backend: str, variant: str) -> str:
    return f"strata-engine-{version}-{platform}-{backend}-{variant}.tar.gz"


def _strict_json(data: bytes, what: str) -> dict:
    def no_duplicates(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise IntegrityError(f"{what}: duplicate JSON keys")
        return dict(pairs)
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, ValueError) as exc:
        raise IntegrityError(f"{what}: not strict UTF-8 JSON ({exc})") from None
    if not isinstance(value, dict):
        raise IntegrityError(f"{what}: a JSON object is required")
    return value


def _members(tar: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    """Every archive member: regular files at the root only, plain unique names, bounded sizes."""
    out: dict[str, tarfile.TarInfo] = {}
    folded: set[str] = set()
    total = 0
    for info in tar:
        if len(out) >= MAX_MEMBERS:
            raise IntegrityError(f"engine archive has more than {MAX_MEMBERS} members")
        name = info.name
        if not info.isreg() or info.issparse():
            raise IntegrityError(f"engine archive member {name!r} is not a regular file")
        if not PLAIN_NAME.match(name) or name.casefold() in folded:
            raise IntegrityError(f"engine archive member name {name!r} is not a unique top-level file name")
        total += info.size
        if total > MAX_TOTAL_BYTES:
            raise IntegrityError("engine archive unpacks to more than the bounded size")
        out[name] = info
        folded.add(name.casefold())
    return out


def _read_small(tar: tarfile.TarFile, info: tarfile.TarInfo) -> bytes:
    if info.size > MAX_JSON_BYTES:
        raise IntegrityError(f"{info.name}: larger than {MAX_JSON_BYTES} bytes")
    handle = tar.extractfile(info)
    if handle is None:
        raise IntegrityError(f"{info.name}: unreadable")
    return handle.read()


def _copy_hashed(src: IO[bytes], dst: IO[bytes] | None, size: int) -> str:
    h, left = hashlib.sha256(), size
    while left:
        block = src.read(min(CHUNK, left))
        if not block:
            raise IntegrityError("engine archive member ended early")
        h.update(block)
        if dst is not None:
            dst.write(block)
        left -= len(block)
    return h.hexdigest()


def _manifest_files(manifest: dict, *, platform: str, backend: str, variant: str) -> dict[str, dict]:
    """The manifest's identity checks; returns its file table keyed by name."""
    want = {"schema_version": 2, "id": "strata-engine", "platform": platform, "backend": backend, "variant": variant,
            "entrypoint": ENTRYPOINT}
    for key, value in want.items():
        if manifest.get(key) != value:
            raise IntegrityError(f"{MANIFEST}: {key} {manifest.get(key)!r} != {value!r}")
    if not isinstance(manifest.get("version"), str) or not VERSION.match(manifest["version"]):
        raise IntegrityError(f"{MANIFEST}: version must be a numeric release version")
    if not isinstance(manifest.get("build_id"), str) or not manifest["build_id"]:
        raise IntegrityError(f"{MANIFEST}: build_id required")
    if manifest.get("min_runtime") is not None:
        raise IntegrityError(f"{MANIFEST}: a min_runtime needs the packaged Control runtime, which this lane never uses")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        raise IntegrityError(f"{MANIFEST}: files list required")
    files: dict[str, dict] = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"} or not isinstance(row["path"], str)
                or not PLAIN_NAME.match(row["path"]) or row["path"] in (MANIFEST,) or row["path"] in files
                or not isinstance(row["sha256"], str) or not SHA256.match(row["sha256"])
                or type(row["bytes"]) is not int or row["bytes"] < 0):
            raise IntegrityError(f"{MANIFEST}: malformed or duplicate file entry {row!r}")
        files[row["path"]] = row
    for name in (ENTRYPOINT, BUILD):
        if name not in files:
            raise IntegrityError(f"{MANIFEST}: {name} is not listed")
    return files


def _build_checks(build: dict, version: str) -> None:
    if build.get("version") != version:
        raise IntegrityError(f"{BUILD}: version {build.get('version')!r} != the component's {version!r}")
    source, commit = build.get("source"), build.get("commit")
    if not isinstance(source, str) or not source or source == "local":
        raise IntegrityError(f"{BUILD}: source {source!r} is not a published build")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise IntegrityError(f"{BUILD}: commit {commit!r} is not a source revision")
    if build.get("backend", "cuda") == "hip":
        raise IntegrityError(f"{BUILD}: a HIP engine is outside this CUDA lane")


def inspect_archive(archive: Path, artifact: dict, *, platform: str = "windows-x86_64", backend: str = "cuda",
                    variant: str = "cuda13") -> dict:
    """Verify a component tarball against its artifact pin and its own manifest, without writing anything.

    Returns {"engine_version", "pin" (the profile's strata.engine_component), "build", "archs", "min_driver"}."""
    verify_file(archive, artifact["bytes"], artifact["sha256"], source=artifact.get("sha256_source", "artifact pin"),
                deep=True, log=lambda _line: None)
    with tarfile.open(archive, "r:gz") as tar:
        members = _members(tar)
        if MANIFEST not in members:
            raise IntegrityError(f"engine archive has no {MANIFEST}")
        raw = _read_small(tar, members[MANIFEST])
        manifest = _strict_json(raw, MANIFEST)
        files = _manifest_files(manifest, platform=platform, backend=backend, variant=variant)
        if set(members) != set(files) | {MANIFEST}:
            raise IntegrityError("engine archive members differ from its manifest: "
                                 + ", ".join(sorted(set(members) ^ (set(files) | {MANIFEST}))))
        build = None
        for name, row in files.items():
            info = members[name]
            if info.size != row["bytes"]:
                raise IntegrityError(f"{name}: {info.size} bytes, the manifest says {row['bytes']}")
            handle = tar.extractfile(info)
            if handle is None:
                raise IntegrityError(f"{name}: unreadable")
            if name == BUILD:
                data = _read_small(tar, info)
                digest = hashlib.sha256(data).hexdigest()
                build = _strict_json(data, BUILD)
            else:
                digest = _copy_hashed(handle, None, info.size)
            if digest != row["sha256"]:
                raise IntegrityError(f"{name}: sha256 {digest}, the manifest says {row['sha256']}")
    version = manifest["version"]
    assert build is not None
    _build_checks(build, version)
    if artifact.get("file") != archive_name(version, platform, backend, variant):
        raise IntegrityError(f"artifact file {artifact.get('file')!r} does not name component {version} {variant}")
    pin = {"format": "tar.gz", "platform": platform, "backend": backend, "variant": variant,
           "manifest_sha256": hashlib.sha256(raw).hexdigest(), "build_id": manifest["build_id"],
           "build_source": build["source"], "build_commit": build["commit"]}
    return {"engine_version": version, "pin": pin, "build": build, "archs": manifest.get("archs"),
            "min_driver": manifest.get("min_driver")}


def verify_tree(directory: Path, pin: dict, *, engine_version: str) -> dict:
    """A staged engine folder holds exactly the pinned component's files and nothing else; returns its BUILD.json."""
    if directory.is_symlink() or not directory.is_dir():
        raise IntegrityError(f"{directory} is not a plain directory")
    raw = (directory / MANIFEST).read_bytes() if (directory / MANIFEST).is_file() else b""
    if hashlib.sha256(raw).hexdigest() != pin["manifest_sha256"]:
        raise IntegrityError(f"{directory / MANIFEST} is not the pinned manifest")
    files = _manifest_files(_strict_json(raw, MANIFEST), platform=pin["platform"], backend=pin["backend"],
                            variant=pin["variant"])
    present = {}
    for entry in directory.iterdir():
        if entry.is_symlink() or not entry.is_file():
            raise IntegrityError(f"{entry} is not a regular file")
        present[entry.name] = entry
    if set(present) != set(files) | {MANIFEST}:
        raise IntegrityError(f"{directory} differs from the pinned component: "
                             + ", ".join(sorted(set(present) ^ (set(files) | {MANIFEST}))))
    for name, row in files.items():
        path = present[name]
        if path.stat().st_size != row["bytes"] or sha256_file(path) != row["sha256"]:
            raise IntegrityError(f"{path} differs from the pinned component")
    build = _strict_json((directory / BUILD).read_bytes(), BUILD)
    _build_checks(build, engine_version)
    if (build["source"], build["commit"]) != (pin["build_source"], pin["build_commit"]):
        raise IntegrityError(f"{BUILD}: {build['source']}/{build['commit']} is not the pinned build")
    return build


def stage(archive: Path, directory: Path, artifact: dict, pin: dict, *, engine_version: str) -> dict:
    """Put the pinned component's files into `directory` (the native engine folder) and return its BUILD.json.

    An exact earlier staging is reused; anything else already there is refused, never repaired or merged. Files are
    written into a sibling temporary folder and the folder is renamed into place only after every file matched."""
    if directory.exists() and any(directory.iterdir()):
        return verify_tree(directory, pin, engine_version=engine_version)
    found = inspect_archive(archive, artifact, platform=pin["platform"], backend=pin["backend"],
                            variant=pin["variant"])
    if found["engine_version"] != engine_version or found["pin"] != {k: pin.get(k) for k in PIN_KEYS}:
        raise IntegrityError("engine archive does not match the profile's engine_component pin")
    tmp = directory.with_name(f".{directory.name}.staging-{os.getpid()}")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = _members(tar)
            files = _manifest_files(_strict_json(_read_small(tar, members[MANIFEST]), MANIFEST),
                                    platform=pin["platform"], backend=pin["backend"], variant=pin["variant"])
            for name, info in members.items():
                handle = tar.extractfile(info)
                if handle is None:
                    raise IntegrityError(f"{name}: unreadable")
                with open(tmp / name, "xb") as out:
                    digest = _copy_hashed(handle, out, info.size)
                if name in files and digest != files[name]["sha256"]:
                    raise IntegrityError(f"{name}: changed between inspection and staging")
        verify_tree(tmp, pin, engine_version=engine_version)
        if directory.exists():
            directory.rmdir()            # empty: checked above
        directory.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp, directory)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return verify_tree(directory, pin, engine_version=engine_version)
