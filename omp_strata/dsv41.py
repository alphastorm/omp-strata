"""The narrowly reviewed stock DeepSeek-V4.1-Flash comparison family (Strata v0.2.11)."""
from __future__ import annotations

from .common import IntegrityError, verify_file

FAMILY = "deepseek41"
MODEL = "IST-DAS-2.25bpw"
MODEL_NAME = "deepseek-v4.1-flash"
TAG = "v0.2.11"
COMMIT = "c3b3f5035506f3e966f1b4b7b188aeaabae92f1d"
ENGINE_VERSION = "0.1.57"
CONTEXTS = (131072, 262144)
READY_SECONDS = 3600
USER_ARGS = ["--experts", "6"]
ENGINE_ENV = {"STRATA_DS4_SLOT_KEEP": "0", "STRATA_DS4_AUTO_PIN": "0"}
ISTA_REPO = "ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF"
ISTA_REVISION = "cb02422c900df489cea5833e8a92171224059b3c"
UNSLOTH_REPO = "unsloth/DeepSeek-V4.1-Flash-1017-GGUF"
UNSLOTH_REVISION = "8a6ec9cf118e785a362ea94ee123c61c70553be6"
# Stock setup.py DSV41_ISTA_FILES / DSV41_FILES at the immutable app commit, original four-shard layout only.
FILES = (
    (ISTA_REPO, ISTA_REVISION, "DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XS-00001-of-00004.gguf", 39535776992,
     "4c65307992ab586c527ca1f6f64062aa96a33b23c02b7fed103f45f75e854798"),
    (ISTA_REPO, ISTA_REVISION, "DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XS-00002-of-00004.gguf", 39494617536,
     "933461a974fcccee741bf2f9798201e72ab4aa3f8a952be56f849896ca6ea30e"),
    (ISTA_REPO, ISTA_REVISION, "DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XS-00003-of-00004.gguf", 39423838496,
     "bbf91fa346a85ebaf32dd4fd5c456b534d780d381e54f46ac90783a481373240"),
    (ISTA_REPO, ISTA_REVISION, "DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XS-00004-of-00004.gguf", 36771591232,
     "e5b2f8781fab688cd4bc3bc7a69651b5dbb90ed94965657c6bead8bb4774f3cf"),
    (ISTA_REPO, ISTA_REVISION, "DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf", 110595290816,
     "eb19f30d368d393784e1fc54fdfaffc427ebb2110bf3762fdf5a8fbb9a2d740a"),
    (UNSLOTH_REPO, UNSLOTH_REVISION, "UD-Q8_K_XL/DeepSeek-V4.1-Flash-1017-UD-Q8_K_XL-00001-of-00009.gguf", 5780589,
     "cc15d470afcb030558bbc4d8e2ccd840182e2e95de1a95198138efe63a5fd99f"),
    (UNSLOTH_REPO, UNSLOTH_REVISION, "dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf", 7976914240,
     "6ba6ac1b331c540691a209e7fc97dec2a24e295acb1e755c84c7d24a4373927a"),
)
FILE_KEYS = ("repository", "revision", "path", "bytes", "sha256")
PACKAGE_PREFIX = "strata-dsv41"
PACKAGE_NAME = f"{PACKAGE_PREFIX}-{ENGINE_VERSION}-windows-x86_64-cuda-cuda13.tar.gz"
PACKAGE = {"file": PACKAGE_NAME, "bytes": 422613464,
           "sha256": "bc1cbecc7553c3022e369bc1e0ed4f360ea26daf5dfc386dd0dde75be417941e",
           "sha256_source": "GitHub release asset digest for Niko1221/Strata v0.2.11",
           "url": f"https://github.com/Niko1221/Strata/releases/download/{TAG}/{PACKAGE_NAME}"}
FORBIDDEN_STRATA = frozenset({"engine_component", "setup_env", "calibration", "stock_tips", "ple_io", "batch_mtp",
                             "kv_grow", "pipeline_windows", "drafting", "budget_plan", "trim_stage_weights",
                             "conversion_lock", "parallel"})
FORBIDDEN_FLAGS = ("--parallel", "--mtp", "--native", "--ple-gguf", "--kv", "--kv-resident", "--pool-workers",
                   "--mmap-experts", "--ssd-cache", "--profile-readonly", "--skip-tensors", "--dense-override")
PACK_MUTABLE_FILES = frozenset({"expert-profile.bin", "pack-source.json"})


def is_pinned(data):
    return data.get("strata", {}).get("setup_args", {}).get("family") == FAMILY


def stock_flags(context):
    return ["--max-context", str(context), "--eos", "1", "--vision", "off", "--dspark", "auto", "--dspark-conf", "0.65"]


def model_files():
    return [dict(zip(FILE_KEYS, row), sha256_source="Stock Strata v0.2.11 setup.py DSV41_ISTA_FILES / DSV41_FILES")
            for row in FILES]


def validate(data):
    from .engine_component import PIN_KEYS
    from .profile import _check_artifact, _check_engine_component, _check_python_lock

    problems = []
    strata, host, model = (data.get(k) or {} for k in ("strata", "host", "model"))
    setup = strata.get("setup_args") or {}
    expected = {"family": FAMILY, "model": MODEL, "context": setup.get("context"), "vision": "no", "gpu": 0}
    if setup != expected or type(setup.get("gpu")) is not int:
        problems.append("strata.setup_args: DeepSeek requires exactly family, model, context, vision no, gpu 0")
    if type(setup.get("context")) is not int or setup["context"] not in CONTEXTS:
        problems.append(f"strata.setup_args.context: DeepSeek reviewed contexts {CONTEXTS}")
    if (host.get("os"), host.get("route"), host.get("gpu_index"), host.get("gpu_model")) != (
            "windows", "native-windows", 0, "NVIDIA RTX PRO 6000 Blackwell Workstation Edition") or "gpus" in host:
        problems.append("host: DeepSeek requires one native Windows RTX PRO 6000 at gpu_index 0")
    for key, want in (("tag", TAG), ("commit", COMMIT), ("engine_version", ENGINE_VERSION),
                      ("model_name", MODEL_NAME), ("user_args", USER_ARGS), ("engine_env", ENGINE_ENV)):
        if strata.get(key) != want:
            problems.append(f"strata.{key}: differs from reviewed DeepSeek value")
    if FORBIDDEN_STRATA & strata.keys():
        problems.append(f"strata: unreviewed DeepSeek options {sorted(FORBIDDEN_STRATA & strata.keys())}")
    if strata.get("expected_engine_flags") != stock_flags(setup.get("context")):
        problems.append("strata.expected_engine_flags: exact stock DeepSeek flags required")
    forbidden = strata.get("forbidden_engine_flags")
    if (not isinstance(forbidden, list) or not all(isinstance(f, str) for f in forbidden)
            or not set(FORBIDDEN_FLAGS) <= set(forbidden) or set(forbidden) & set(stock_flags(setup.get("context")))):
        problems.append("strata.forbidden_engine_flags: reviewed DeepSeek refusals required, no stock flag overlap")
    arts = strata.get("artifacts") or {}
    if set(arts) != {"dsv41_package"}:
        problems.append("strata.artifacts: only dsv41_package, never Qwen engine/llama archives")
    package = arts.get("dsv41_package")
    _check_artifact(problems, "strata.artifacts.dsv41_package", package)
    if not isinstance(package, dict) or any(package.get(k) != v for k, v in PACKAGE.items() if k != "sha256_source"):
        problems.append("strata.artifacts.dsv41_package: differs from the reviewed release package")
    component = strata.get("dsv41_component")
    if not isinstance(component, dict) or set(component) != set(PIN_KEYS) | {"version"}:
        problems.append("strata.dsv41_component: component pin and its own version required")
    else:
        if component["version"] != ENGINE_VERSION:
            problems.append("strata.dsv41_component.version: differs from the reviewed package")
        _check_engine_component(problems, {k: component[k] for k in PIN_KEYS}, strata, host,
                                name="dsv41_component", artifact_key="dsv41_package", prefix=PACKAGE_PREFIX)
    _check_python_lock(problems, strata.get("python_lock"), data.get("status"))
    if set(model) != {"variant", "quantization", "license", "files"} or (model.get("variant"), model.get("quantization")) != (FAMILY, "IQ2_XS"):
        problems.append("model: DeepSeek per-file sources only, variant deepseek41 and quantization IQ2_XS")
    files = model.get("files")
    if not isinstance(files, list) or len(files) != len(FILES):
        problems.append("model.files: exact reviewed four-shard set, Engram, metadata and DSpark required")
    else:
        for i, (entry, row) in enumerate(zip(files, FILES)):
            _check_artifact(problems, f"model.files[{i}]", entry, need_url=False)
            if (not isinstance(entry, dict) or set(entry) != set(FILE_KEYS) | {"sha256_source"}
                    or tuple(entry.get(k) for k in FILE_KEYS) != row):
                problems.append(f"model.files[{i}]: differs from reviewed DeepSeek pin (six-shard layout not admitted)")
    if (data.get("server") or {}).get("ready_timeout_s") != READY_SECONDS:
        problems.append("server.ready_timeout_s: DeepSeek needs stock engine_ready_s 3600")
    if (data.get("omp") or {}).get("max_tokens") != 32768:
        problems.append("omp.max_tokens: DeepSeek requires 32768")
    return problems


def pack_dir(layout):
    return layout.data / "packs" / f"{MODEL_NAME}-{MODEL.lower()}"


def verify_inputs(layout, *, log):
    """Stock warns and accepts wrong own-files: independently hash every input before letting it run."""
    if layout.models_dir.exists():
        allowed = {row[2].rsplit("/", 1)[-1] for row in FILES}
        extra = {p.name for p in layout.models_dir.glob("*.gguf")} - allowed
        if extra:
            raise IntegrityError(f"DeepSeek models directory holds unreviewed GGUF files: {sorted(extra)}")
    for entry in layout.profile.data["model"]["files"]:
        verify_file(layout.model_file(entry), entry["bytes"], entry["sha256"], source=entry["sha256_source"],
                    deep=True, log=log)
    verify_file(layout.dsv41_package, PACKAGE["bytes"], PACKAGE["sha256"], source=PACKAGE["sha256_source"], deep=True, log=log)
