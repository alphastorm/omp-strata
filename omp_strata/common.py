"""Small stdlib helpers shared by the lifecycle, qualification and verification tools."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

HEX64 = frozenset("0123456789abcdef")
USER_AGENT = "omp-strata-fetch/0.1"
CHUNK = 8 << 20


class IntegrityError(RuntimeError):
    """Bytes on disk do not match the pinned expectation."""


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX64


def sha256_file(path: Path, *, progress: Callable[[int], None] | None = None) -> str:
    h = hashlib.sha256()
    done = 0
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
            done += len(block)
            if progress is not None:
                progress(done)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    """Stable serialization used for every fingerprint: sorted keys, no whitespace, UTF-8."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def within(root: Path, candidate: Path) -> bool:
    """True when `candidate`, with every symlink resolved, stays inside `root` (also resolved)."""
    root_r = root.resolve()
    try:
        candidate.resolve().relative_to(root_r)
    except ValueError:
        return False
    return True


def safe_child(root: Path, relative: str) -> Path:
    """Join a relative, forward-slash path under root, refusing absolute paths, drive letters and traversal."""
    if not relative or relative.startswith(("/", "\\")) or ":" in relative:
        raise ValueError(f"not a safe relative path: {relative!r}")
    parts = relative.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"not a safe relative path: {relative!r}")
    path = root.joinpath(*parts)
    if not within(root, path.parent if not path.exists() else path):
        raise ValueError(f"path escapes {root}: {relative!r}")
    return path


def _verified_marker(dest: Path) -> Path:
    return dest.with_name(dest.name + ".verified.json")


def verified_ok(dest: Path, size: int, sha256: str) -> bool:
    """A previous full-hash verification still describes these bytes (same size and mtime)."""
    marker = _verified_marker(dest)
    if not dest.is_file() or not marker.is_file():
        return False
    try:
        rec = read_json(marker)
        st = dest.stat()
    except (OSError, ValueError):
        return False
    return (rec.get("sha256") == sha256 and rec.get("bytes") == size == st.st_size
            and rec.get("mtime_ns") == st.st_mtime_ns)


def record_verified(dest: Path, size: int, sha256: str, source: str) -> None:
    st = dest.stat()
    atomic_write_json(_verified_marker(dest), {"bytes": size, "sha256": sha256, "mtime_ns": st.st_mtime_ns,
                                                "verified_utc": utc_now(), "source": source})


def verify_file(dest: Path, size: int, sha256: str, *, source: str, deep: bool = False,
                log: Callable[[str], None] = print) -> None:
    """Size + SHA-256 check with a cached full-hash result; `deep` forces a rehash."""
    if not dest.is_file():
        raise IntegrityError(f"missing: {dest.name}")
    actual_size = dest.stat().st_size
    if actual_size != size:
        raise IntegrityError(f"{dest.name}: {actual_size} bytes, expected {size}")
    if not deep and verified_ok(dest, size, sha256):
        return
    log(f"hashing {dest.name} ({size / 1e9:.2f} GB)")
    actual = sha256_file(dest)
    if actual != sha256:
        raise IntegrityError(f"{dest.name}: sha256 {actual}, expected {sha256}")
    record_verified(dest, size, sha256, source)


def download_verified(url: str, dest: Path, size: int, sha256: str, *, source: str,
                      log: Callable[[str], None] = print, retries: int = 30, timeout: float = 60.0) -> Path:
    """Resumable download into `<dest>.partial`; promoted to `dest` only after size and SHA-256 match.

    Already-verified bytes are reused without network access. A size overrun or hash mismatch discards the
    partial file and raises, so an unverified file is never left under the final name.
    """
    if not url.startswith("https://"):
        raise ValueError(f"refusing non-HTTPS artifact URL: {url}")
    if not is_sha256(sha256) or size <= 0:
        raise ValueError(f"incomplete pin for {dest.name}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        verify_file(dest, size, sha256, source=source, log=log)
        return dest
    partial = dest.with_name(dest.name + ".partial")
    have = partial.stat().st_size if partial.exists() else 0
    if have > size:
        partial.unlink()
        have = 0
    attempt = 0
    last_log = 0.0
    while have < size:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": f"bytes={have}-"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(partial, "ab") as out:
                if have and resp.status != 206:
                    out.seek(0)
                    out.truncate()
                    have = 0
                while True:
                    block = resp.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
                    have += len(block)
                    if have > size:
                        break
                    now = time.monotonic()
                    if now - last_log > 15:
                        last_log = now
                        log(f"{dest.name}: {have / 1e9:.2f}/{size / 1e9:.2f} GB")
            if have > size:
                partial.unlink(missing_ok=True)
                raise IntegrityError(f"{dest.name}: server sent more than the pinned {size} bytes")
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            attempt += 1
            if attempt > retries:
                raise
            log(f"{dest.name}: transfer interrupted ({exc}); retry {attempt}/{retries}")
            time.sleep(min(60, 2 * attempt))
            have = partial.stat().st_size if partial.exists() else 0
    log(f"hashing {dest.name}")
    actual = sha256_file(partial)
    if actual != sha256:
        partial.unlink(missing_ok=True)
        raise IntegrityError(f"{dest.name}: sha256 {actual}, expected {sha256}; partial discarded")
    os.replace(partial, dest)
    record_verified(dest, size, sha256, source)
    log(f"verified {dest.name}")
    return dest


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr, flush=True)
