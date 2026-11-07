"""Pinned inputs and offline preparation for stock Strata's DFlash2 drafter."""
from __future__ import annotations

import os

from .common import IntegrityError, flag_pairs, is_sha256, prerelease_tag, read_json, release_version, sha256_file, verify_file

# Stock Strata v0.2.10 strata_control/drafting.py:192-216,561, with stock's names.
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

# Stock Strata v0.2.12 strata_control/drafting.py:230-249 and data/dflash2-tuned/.
TUNED_REPOSITORY = "Niko1221/Strata"
TUNED_NAME = "qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack"
TUNED_BYTES = 339694592
TUNED_SHA256 = "4df2e5ab2b47c064afbe662e16e4f06569877125c2d0e2123a4ac755266c664c"
TUNED_BF16_NAME = "qwen3.8-flash-next-dflash2.strata1.q4_0-bf16sel.pack"
TUNED_BASE = f"{REPO} revision {REVISION}"
TUNED_LICENSE_FOLDER = "data/dflash2-tuned"
TUNED_LICENSE = {"LICENSE": "LICENSE-dflash2-tuned", "NOTICE.md": "NOTICE-dflash2-tuned.md"}
TUNED_LICENSE_SHA256 = {
    "LICENSE-dflash2-tuned": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    "NOTICE-dflash2-tuned.md": "223fbe3ae8482b2fb51c2f8da61d08bb21a0830cb71aba4bbfe01316ba7afd89",
}
TUNED_SINCE = (0, 1, 58)
TUNED_RELEASE_SINCE = (0, 2, 12)
TUNED_CARDS = frozenset({"NVIDIA RTX PRO 6000 Blackwell Workstation Edition"})
TUNED_FAMILY_FILES = frozenset({
    TUNED_NAME, TUNED_NAME + ".ok", TUNED_BF16_NAME, TUNED_BF16_NAME + ".ok",
    *TUNED_LICENSE.values(), ".tuned-feed-miss",
})


def is_pinned(data):
    return data.get("strata", {}).get("drafting") == "dflash2"


def is_tuned(pin):
    return isinstance(pin, dict) and "tuned" in pin


def runtime_file(pin):
    return pin["tuned"] if is_tuned(pin) else pin["packs"][pin["runtime_pack"]]


def tuned_aware(engine_version):
    version = release_version(str(engine_version))
    return version is not None and version >= TUNED_SINCE


def source_url(entry):
    return f"https://huggingface.co/{REPO}/resolve/{REVISION}/{entry['path']}"


def validate_source(model):
    from .profile import _check_artifact

    problems = []
    source = model.get("dflash2_source")
    where = "model.dflash2_source"
    keys = {"repository", "revision", "license", "kind", "files", "packs", "runtime_pack", "vocab_sha256"}
    if is_tuned(source):
        keys.add("tuned")
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
    if is_tuned(source):
        where += ".tuned"
        tuned = source["tuned"]
        keys = {"tag", "url", "file", "bytes", "sha256", "sha256_source", "license", "base", "license_files"}
        if not isinstance(tuned, dict) or set(tuned) != keys:
            problems.append(f"{where}: exactly {sorted(keys)} required")
            return problems
        _check_artifact(problems, where, tuned)
        if tuple(tuned[k] for k in ("file", "bytes", "sha256")) != (TUNED_NAME, TUNED_BYTES, TUNED_SHA256):
            problems.append(f"{where}: file, bytes and sha256 differ from reviewed stock tuned DFlash2")
        tag = str(tuned["tag"])
        version = release_version(tag)
        if version is None or version < TUNED_RELEASE_SINCE or prerelease_tag(tag):
            problems.append(f"{where}.tag: stable v0.2.12 or newer required")
        if tuned["url"] != f"https://github.com/{TUNED_REPOSITORY}/releases/download/{tag}/{TUNED_NAME}":
            problems.append(f"{where}.url: must be the pinned flat stock release asset")
        for key, want in (("license", LICENSE), ("base", TUNED_BASE), ("license_files", TUNED_LICENSE_SHA256)):
            if tuned[key] != want:
                problems.append(f"{where}.{key}: differs from reviewed stock tuned DFlash2")
    return problems


def validate_tuned(data):
    strata, host = data.get("strata") or {}, data.get("host") or {}
    pin = (data.get("model") or {}).get("dflash2_source")
    if not is_tuned(pin):
        return []
    setup = strata.get("setup_args") or {}
    predicates = (
        (tuned_aware(strata.get("engine_version")),
         "requires engine 0.1.58 or newer (stock v0.2.12 tuned pack)"),
        ("gpus" not in host, "stock never uses the tuned pack on several cards"),
        (host.get("gpu_model") in TUNED_CARDS, "only a reviewed one-card host reaches stock's resident boundary"),
        ((setup.get("family"), setup.get("model"), strata.get("model_name")) ==
         ("qwen", "IQ3_S", "qwen3.8-flash-next-iq3_s"),
         "only the qwen IQ3_S set (stock cuda 'resident' iq3_s) is reviewed"),
        (strata.get("engine_component") is not None, "requires a CUDA engine component"),
        (flag_pairs(strata.get("expected_engine_flags") or []).get("--expert-cache") == "auto",
         "requires --expert-cache auto (stock sizes residency from the one card)"),
        (pin.get("runtime_pack") == "selq4",
         "requires runtime_pack selq4 (the tuned file has Q4_0 selector codebooks)"),
    )
    return [f"model.dflash2_source.tuned: {message}" for passes, message in predicates if not passes]


CHECK_ENGINE = """
import sys
from strata_control import drafting
if drafting.engine_reads_selector_q4(sys.argv[1]) != (sys.argv[2] == "selq4"):
    raise SystemExit("DFlash2 runtime_pack differs from the staged stock engine's selector support")
"""
PROVIDE_VOCAB = """
import sys
from strata_control import drafting
if drafting.provide_vocab(sys.argv[1]) is None:
    raise SystemExit("stock DFlash2 vocabulary copy failed")
"""
CONVERTED_OK = """
import sys
from strata_control import drafting
if not drafting.converted_ok(sys.argv[1]):
    raise SystemExit("stock DFlash2 converted pack refused")
"""


def _pack_ok(path, pin):
    return path.is_file() and path.stat().st_size == pin["bytes"] and sha256_file(path) == pin["sha256"]


def _no_leftovers(folder):
    if (folder / "src").exists() or any(p.name.endswith((".partial", ".tmp", ".part")) for p in folder.rglob("*")):
        raise IntegrityError("DFlash2 preparation has leftover src/ or partial files; reconcile them before reuse")


def prepare(layout, *, run, env, log):
    """Use only stock's offline packer and local helpers; never drafting_fetch.ensure()."""
    pin = layout.profile.data["model"]["dflash2_source"]
    for entry in pin["files"]:
        verify_file(layout.dflash2_file(entry), entry["bytes"], entry["sha256"],
                    source=entry["sha256_source"], deep=True, log=log)
    folder = layout.dflash2_dir
    _no_leftovers(folder)
    folder.mkdir(parents=True, exist_ok=True)
    offline = {**env, "STRATA_NO_ACQUIRE": "1"}
    python = str(layout.venv_python)
    exe = layout.strata / "engine/strata.exe"
    run([python, "-c", CHECK_ENGINE, str(exe), pin["runtime_pack"]],
        cwd=layout.strata, env=offline, log=log, timeout=600)
    tool = str(layout.strata / "tools/dflash2_pack.py")
    inputs = {entry["path"]: layout.dflash2_file(entry) for entry in pin["files"]}
    prepared = {}

    def make_pack(name):
        spec = pin["packs"][name]
        target = folder / spec["file"]
        if not _pack_ok(target, spec):
            partial = target.with_name(target.name + ".partial")
            # Stock v0.2.10 tools/dflash2_pack.py:4-5,257-265: positional inputs and --convert-selector.
            args = ([str(inputs["model.safetensors"]), str(inputs["config.json"]), str(partial), "--q4_0"]
                    if name == "q4_0" else
                    ["--convert-selector", str(folder / pin["packs"]["q4_0"]["file"]), str(partial)])
            try:
                run([python, tool, *args], cwd=layout.strata, env=offline, log=log, timeout=3600)
                if not _pack_ok(partial, spec):
                    raise IntegrityError(f"DFlash2 {name} output differs from the pinned size or SHA-256")
                os.replace(partial, target)
            finally:
                partial.unlink(missing_ok=True)
        prepared[name] = spec["sha256"]

    make_pack("q4_0")
    run([python, "-c", PROVIDE_VOCAB, str(layout.data)],
        cwd=layout.strata, env=offline, log=log, timeout=600)
    vocab = folder / VOCAB_NAME
    if not vocab.is_file() or sha256_file(vocab) != pin["vocab_sha256"]:
        raise IntegrityError("DFlash2 stock vocabulary differs from its pinned SHA-256")
    if pin["runtime_pack"] == "selq4":
        make_pack("selq4")
        run([python, "-c", CONVERTED_OK, str(layout.data)],
            cwd=layout.strata, env=offline, log=log, timeout=600)
        target = folder / pin["packs"]["selq4"]["file"]
        marker = target.with_name(target.name + ".ok")
        info = target.stat()
        if not marker.is_file() or read_json(marker) != {
                "size": info.st_size, "mtime_ns": info.st_mtime_ns, "sha256": pin["packs"]["selq4"]["sha256"]}:
            raise IntegrityError("DFlash2 stock converted_ok marker is absent or stale")
    _no_leftovers(folder)
    return {"runtime_pack": pin["runtime_pack"], "packs": prepared, "vocab_sha256": pin["vocab_sha256"]}
