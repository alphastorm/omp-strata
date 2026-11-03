"""Pinned inputs and offline preparation for stock Strata's DFlash2 drafter."""
from __future__ import annotations

from .common import is_sha256

# Stock Strata v0.2.10 strata_control/drafting.py:239-265,538, with stock's names.
REPO = "incoai/Qwen3.8-Flash-Next-DFlash2"
REVISION = "a22a1744e85c17364dcc54a6a420af7135d4c7f6"
LICENSE = "Apache-2.0"
FILES = (
    ("config.json", 1236, "2409575986f9ea24d455343eb469c0e6940def5edab1d1be503bb8eb4cc3b1b9"),
    ("model.safetensors", 1206140008, "d6723f2a359eaf33ec0c95f22ae8edda896774020c552296a85e1913b4d3186f"),
)
PACK_NAME = "qwen3.8-flash-next-dflash2.q4_0.pack"
PACK_BYTES = 522458112
PACK_SHA256 = "cda40d62d0eb8f37ed6e272142641a1d2f0de4a32f9e14d0416e7a71534849f1"
CONVERTED_NAME = "qwen3.8-flash-next-dflash2.q4_0-selq4.pack"
CONVERTED_BYTES = 339694592
CONVERTED_SHA256 = "4a42b98220ea7880664002c8edda1563aecbae754b762a2e2f31b2b91ee93ecd"
VOCAB_NAME = "draft_vocab.bin"
FOLDER = "dflash2"
PACKS = {
    "q4_0": {"file": PACK_NAME, "bytes": PACK_BYTES, "sha256": PACK_SHA256},
    "selq4": {"file": CONVERTED_NAME, "bytes": CONVERTED_BYTES, "sha256": CONVERTED_SHA256},
}
MARK_SELQ4 = b"selector codebooks: Q4_0 rows"
MARK_ON = b"DFlash2 drafter on"
MARK_VOCAB = b"--mtp-draft-vocab FILE (or --mtp DIR"


def is_pinned(data):
    return data.get("strata", {}).get("drafting") == "dflash2"


def source_url(entry):
    return f"https://huggingface.co/{REPO}/resolve/{REVISION}/{entry['path']}"


def validate_source(model):
    from .profile import _check_artifact

    problems = []
    source = model.get("dflash2_source")
    where = "model.dflash2_source"
    keys = {"repository", "revision", "license", "kind", "files", "packs", "runtime_pack", "vocab_sha256"}
    if not isinstance(source, dict) or set(source) != keys:
        return [f"{where}: exactly {sorted(keys)} required"]
    for key, want in (("repository", REPO), ("revision", REVISION), ("license", LICENSE), ("kind", "locally-packed")):
        if source[key] != want:
            problems.append(f"{where}.{key}: differs from reviewed stock DFlash2")
    files = source["files"]
    if not isinstance(files, list) or len(files) != len(FILES):
        problems.append(f"{where}.files: the two reviewed stock source files required")
    else:
        for i, (entry, expected) in enumerate(zip(files, FILES)):
            _check_artifact(problems, f"{where}.files[{i}]", entry, need_url=False)
            if (not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256", "sha256_source"}
                    or tuple(entry.get(k) for k in ("path", "bytes", "sha256")) != expected):
                problems.append(f"{where}.files[{i}]: differs from reviewed stock DFlash2")
    if source["packs"] != PACKS:
        problems.append(f"{where}.packs: differs from reviewed stock DFlash2")
    if not isinstance(source["runtime_pack"], str) or source["runtime_pack"] not in PACKS:
        problems.append(f"{where}.runtime_pack: q4_0 or selq4 required")
    if not is_sha256(source["vocab_sha256"]):
        problems.append(f"{where}.vocab_sha256: SHA-256 of stock data/draft_vocab.bin required")
    return problems
