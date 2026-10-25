"""The single admitted ModelOpt FP4-Local input format; no runtime or route promotion."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import stat

from .common import IntegrityError, atomic_write_json, canonical_json, read_json, sha256_bytes, sha256_file, verified_ok, verify_file

FORMAT = "modelopt-fp4-local"
REPOSITORY = "nvidia/Qwen3.8-Flash-Next-FP4-Local"
REVISION = "b9ce18a6887e18c089fdea8509a33e63429a3300"
MANIFEST_SHA256 = "5fa166bbb1cf25adda455117563efa72a2072272001f459eedece131ffc913e1"
RECIPE_COMMIT = "8183c6b67162340c09b67360860177c577a65f2e"
RECIPE_SHA256 = "7ac34c7823275606bced9877ef5a7e78ad6d27bb9d3d12884526d510766548ae"
REQUIREMENTS_SHA256 = "baa4614ac499af7b2676cff5b5eb3f5d78570a764a75dbf368f5621ffced2bb2"
CHECKPOINT_AST_SHA256 = "dd16118393091b08b786586ab793fe6bbca3449854885d6dee08b58bce15e6f7"
CHECKPOINT_FILES_SHA256 = "5423b3ddec96580a89c51b5be6a51fae460570e9b74d035cb65a4f25df34e5cb"
PREPARATION_BYTES = 110_000_000_000


def assert_isolated_tree(root):
    """Never follow candidate-local aliases into another installation."""
    def check(info):
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise IntegrityError("candidate tree contains a reparse point")
    try:
        check(root.lstat())
    except FileNotFoundError:
        return
    pending = [root]
    while pending:
        try:
            entries = os.scandir(pending.pop())
        except FileNotFoundError:
            continue  # A workload can remove a temporary directory during a scan.
        with entries as items:
            for entry in items:
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                check(info)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(entry.path))


def is_local(model):
    return model.get("format") == FORMAT


def checkpoint_dir(layout):
    return layout.models_dir / REPOSITORY.replace("/", "--")


def prepared_dir(layout):
    return checkpoint_dir(layout) / "prepared"


def conversion_python(layout):
    base = layout.root / "runtime/nvfp4-conversion"
    return base / ("Scripts/python.exe" if layout.venv_python.suffix == ".exe" else "bin/python")


def engine_paths(layout):
    base = prepared_dir(layout)
    return {"--pack": base / "pack", "--native": base / "dense.gguf",
            "--native-dense-gguf": base / "dense.gguf", "--ple-gguf": base / "ple-nvfp4.gguf",
            "--mtp": base / "mtp/rt"}


def disk_preflight(layout):
    """No mkdir, download, conversion or service action occurs before the staging floor passes."""
    artifact_bytes = sum(row["bytes"] for row in layout.profile.data["model"]["files"])
    anchor = layout.root
    while not anchor.exists():
        if anchor.parent == anchor:
            raise IntegrityError("NVFP4 staging refused: filesystem anchor does not exist")
        anchor = anchor.parent
    free = shutil.disk_usage(anchor).free
    remaining = sum(row["bytes"] for row in layout.profile.data["model"]["files"]
                    if not verified_ok(layout.model_file(row), row["bytes"], row["sha256"]))
    required = remaining + max(artifact_bytes, PREPARATION_BYTES)
    observation = {"artifact_bytes": artifact_bytes, "remaining_download_bytes": remaining,
                   "free_bytes": free, "required_free_bytes": required,
                   "admitted": free >= required}
    if not observation["admitted"]:
        raise IntegrityError(f"NVFP4 staging refused: {free} bytes free; require {required} "
                             "(fresh inputs require at least 2x checkpoint)")
    return observation


def validate_conversion(model):
    try:
        files = sorted((row["path"], row["bytes"], row["sha256"]) for row in model["files"])
    except (KeyError, TypeError):
        return False
    return (model.get("conversion") == conversion_pin()
            and sha256_bytes(canonical_json(files)) == CHECKPOINT_FILES_SHA256)


def conversion_pin():
    return {"recipe_commit": RECIPE_COMMIT, "recipe_sha256": RECIPE_SHA256,
            "requirements_sha256": REQUIREMENTS_SHA256, "manifest_sha256": MANIFEST_SHA256,
            "extra_disk_bytes": PREPARATION_BYTES}


def output_manifest(layout):
    base = prepared_dir(layout)
    required = [base / "dense.gguf", base / "ple-nvfp4.gguf", base / "pack/experts.bin",
                base / "pack/dense.bin", base / "pack/index.txt", base / "pack/native_experts.txt",
                base / "pack/tokenizer/vocab.json", base / "mtp/rt/experts.bin",
                base / "mtp/rt/draft_vocab.bin"]
    if any(not path.is_file() or path.stat().st_size <= 0 for path in required):
        raise IntegrityError("NVFP4 preparation lacks required runtime outputs")
    return {path.relative_to(base).as_posix(): {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(base.rglob("*")) if path.is_file() and path.name != "conversion-receipt.json"}


def verify_prepared(layout):
    receipt = read_json(prepared_dir(layout) / "conversion-receipt.json")
    model = layout.profile.data["model"]
    if (receipt.get("input_fingerprint") != sha256_bytes(canonical_json(model))
            or receipt.get("recipe_commit") != RECIPE_COMMIT
            or receipt.get("recipe_sha256") != RECIPE_SHA256
            or receipt.get("weight_manifest_sha256") != MANIFEST_SHA256
            or receipt.get("files") != output_manifest(layout)):
        raise IntegrityError("NVFP4 converted inputs or outputs drifted")
    return receipt


def staging_preflight(layout):
    assert_isolated_tree(layout.root)
    if (prepared_dir(layout) / "conversion-receipt.json").exists():
        return verify_prepared(layout)
    return disk_preflight(layout)


def prepare(layout, *, run, env, log):
    """Pinned stock CPU conversion, never setup's online preparation or a GPU process."""
    model = layout.profile.data["model"]
    tool = layout.strata / "tools/nvfp4_local_pack.py"
    if sha256_file(tool) != RECIPE_SHA256 or sha256_file(layout.strata / "requirements-nvfp4-local.txt") != REQUIREMENTS_SHA256:
        raise IntegrityError("NVFP4 conversion recipe changed")
    for entry in model["files"]:
        verify_file(layout.model_file(entry), entry["bytes"], entry["sha256"], source=entry["sha256_source"], log=log)
    index = layout.model_file(next(row for row in model["files"] if row["path"] == "model.safetensors.index.json"))
    if sha256_file(index) != MANIFEST_SHA256:
        raise IntegrityError("NVFP4 weight manifest changed")
    if (prepared_dir(layout) / "conversion-receipt.json").exists():
        return verify_prepared(layout)
    # Marks alone never authorize reuse after an interrupted/foreign conversion.
    if prepared_dir(layout).exists() and any(prepared_dir(layout).iterdir()):
        raise IntegrityError("unreceipted NVFP4 preparation exists; reconcile it before reuse")
    disk_preflight(layout)
    cpu_env = {**env, "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    run([str(conversion_python(layout)), str(tool), "prepare", "--model", str(checkpoint_dir(layout)),
         "--out", str(prepared_dir(layout))], cwd=layout.strata, env=cpu_env, log=log, timeout=6 * 3600)
    # Stock setup.refresh_draft_vocab installs this pinned default even with --no-start.
    # Include it before sealing; setup must not introduce a previously unreceipted runtime input.
    shutil.copyfile(layout.strata / "data/draft_vocab.bin", prepared_dir(layout) / "mtp/rt/draft_vocab.bin")
    receipt = {"input_fingerprint": sha256_bytes(canonical_json(model)), "recipe_commit": RECIPE_COMMIT,
               "recipe_sha256": RECIPE_SHA256, "weight_manifest_sha256": MANIFEST_SHA256,
               "files": output_manifest(layout)}
    atomic_write_json(prepared_dir(layout) / "conversion-receipt.json", receipt)
    return receipt
