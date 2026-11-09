"""The narrowly reviewed stock DeepSeek-V4.1-Flash comparison family (Strata v0.2.11)."""
from __future__ import annotations

import json
import re

from .common import IntegrityError, verify_file

FAMILY = "deepseek41"
MODEL = "IST-DAS-2.25bpw"
MODEL_NAME = "deepseek-v4.1-flash"
TAG = "v0.2.11"
COMMIT = "c3b3f5035506f3e966f1b4b7b188aeaabae92f1d"
ENGINE_VERSION = "0.1.57"
CONTEXTS = (131072, 262144)
READY_SECONDS = 3600
INVOCATION_TIMEOUT_S = 3600
# Comparison-only upper bounds, not throughput or completion claims. Startup includes the stock 3600 s ready wait.
STEP_TIMEOUTS = {"install": 28800, "start": 3900, "tracer": 21600, "g18": 21600, "g18l": 21600,
                 "pilot": 54000, "eval": 54000}
USER_ARGS = ["--experts", "6"]
EFFORT_WIRE = {"low": 50, "medium": 62, "high": 75}
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
COMPONENT_ID = "strata-engine"  # Stock's common component schema; the entrypoint distinguishes this package.
ENTRYPOINT = "strata-dsv41.exe"
COMPONENT_MAX_MEMBERS = 8
COMPONENT_MAX_TOTAL_BYTES = 1 << 30
PACKAGE_NAME = f"{PACKAGE_PREFIX}-{ENGINE_VERSION}-windows-x86_64-cuda-cuda13.tar.gz"
PACKAGE = {"file": PACKAGE_NAME, "bytes": 422613464,
           "sha256": "bc1cbecc7553c3022e369bc1e0ed4f360ea26daf5dfc386dd0dde75be417941e",
           "sha256_source": "GitHub release asset digest for Niko1221/Strata v0.2.11",
           "url": f"https://github.com/Niko1221/Strata/releases/download/{TAG}/{PACKAGE_NAME}"}
# Manifest/build id from the release-pinned feed (b993f0d9…); BUILD fields read from the asset's first tar member.
# The full archive and its actual manifest must still match these pins before stock setup can run.
COMPONENT = {"format": "tar.gz", "platform": "windows-x86_64", "backend": "cuda", "variant": "cuda13",
             "manifest_sha256": "d0ebc5660e8fbaea64e0949400b36d7b410f087d7112a350214531f7fab15272",
             "build_id": "975eaab2bb40+dsv41+cuda13.0", "build_source": "f-0211-rc 975eaab2b",
             "build_commit": "975eaab2bb40", "version": ENGINE_VERSION}
FORBIDDEN_STRATA = frozenset({"engine_component", "setup_env", "calibration", "stock_tips", "ple_io", "batch_mtp",
                             "kv_grow", "pipeline_windows", "drafting", "budget_plan", "trim_stage_weights",
                             "conversion_lock", "parallel", "drafting_args"})
FORBIDDEN_FLAGS = ("--parallel", "--mtp", "--native", "--ple-gguf", "--kv", "--kv-resident", "--pool-workers",
                   "--mmap-experts", "--ssd-cache", "--profile-readonly", "--skip-tensors", "--dense-override")
PACK_MUTABLE_FILES = frozenset({"expert-profile.bin", "pack-source.json"})
SETUP_AST = "22396a173a1b5562a0909180eacb907a8e427671b7c033fe53f1874489b321de"
SETUP_FUNCTIONS = {
    "install_dsv41": "08f85a37cd5aaa04d2e15e5dde3ac59f73b46ca510d74fed27e313d8b119c3e1",
    "get_dsv41_engine": "28f9aa25cd5a4c85cf1b4d1d2b49bb495b5226cc87e82842666624eef09da1c9",
    "dsv41_pack_cmd": "254f5b3489bebc29e9a2aa418a375d9ac400b2f5a55c2e1963da742c0fd61997",
    "dsv41_smoke": "eaff9fb79a453e3322b784e640176536cfb0502c201a220e1a806ddbec04512c",
    "write_setup_config": "309ae7a7af6b22a77fb0acba3f89b42fb3af3a2f33229bd5343156f21123e3f6",
    "write_config": "875c4111fb44d7659fa40daf85d440ea08961a55b3b8e5500b01b0d91ac7b959",
}
CONFIG_KEYS = frozenset({"exe", "args", "cwd", "tokenizer", "model_name", "arch", "log", "lib_dirs", "port",
                         "engine_ready_s", "gpu", "gpus_asked", "host", "args_written", "user_args", "env"})
# ds4_model.cu:14820-14822 reports INFO engine=ds4-0.1; server.py:1318-1319 prefers it over BUILD.json.
BUILD_LABELS = frozenset({"Strata ds4-0.1"})
SERVER_AST = "5adad3a40bb9b795aa37cf72c8e5d3cc9dfdd2ec5e6e2184cc678774bff56247"
SERVER_SOURCES = {
    "strata_control/dsv41_flags.py": "ff68ffffe6134390472727b89e537df91a15d696f0404ca656a7bdcc089b64e3",
    "strata_control/dsv41_context.py": "b8d0e324677c3e8e0e629aaa392fea5688fb3dffd4c24711bd448971196bbc1e",
    "strata_control/engine_component.py": "8ad74ef804e659dcca335c61c25ed45fbc1fa250a27d29e56cc7049375fcc779",
    "strata_control/user_args.py": "625e4282ba491b97cd8073a9c687acc90023ecb115233cd123eb6a36b7b717ae",
    "serve/dsml.py": "c460f8802f2901596ec4eb2323f409466664020517be8424835db619d62d658f",
    "serve/frontend.py": "ae6941b38daf020f0f122dd52239e254b5369069ff2493183d8caca9a54992c3",
}
TEMPLATE = "serve/fixtures/deepseek41/chat_template.jinja"
TEMPLATE_SHA256 = "06cada875e3a04665f9cf47deae9ef32e16ede2c6511205a4031c8b48140d01b"
# Stock ds4_model.cu:2845-2846,2884,5882-5883,6011,6430-6449. Unknown decisions deliberately fail closed.
EXPERTS_LINE = "ds4: experts per word: 6 (full quality)"
DSPARK_DECLINED = re.compile(
    r"ds4: DSpark not loaded: the routed experts \((?P<experts>\d+) GB\) are far more than the GPU holds "
    r"\((?P<gpu>\d+) GB\), where its verify rounds read 3\.3x a token's bytes and gain nothing "
    r"\(--dspark on loads it anyway\)")
COPY_ALL = re.compile(
    r"ds4: --mmap-experts auto: the CPU lane's experts \(\d+\.\d GB\) fit the RAM this process can get "
    r"\(\d+\.\d GB beside \d+ GB for the rest\): copied in at load, no demand store "
    r"\(--mmap-experts on keeps them in place\)")
COPIED = re.compile(
    r"ds4: (?P<copied>\d+) of the CPU lane's (?P<total>\d+) experts copied into RAM "
    r"\(\d+\.\d GB, \d+ NUMA parts?\) in \d+\.\d s")
PLACEMENT = re.compile(
    r"ds4: CUDA0 layers \[0, 39\] \+ head: weights \d+\.\d{2} GB, experts \d+\.\d{2} GB "
    r"\((?P<gpu>\d+) of (?P<total>\d+) in VRAM\), caches \d+\.\d{2} GB, \d+ MiB free")
CPU_LANE = re.compile(
    r"ds4: (?P<total>\d+) routed experts on the CPU lane \(\d+\.\d GB\): (?P<copied>\d+) copied into RAM "
    r"\(\d+ NUMA parts\), the rest in place in the model's files; \d+ threads")


def is_pinned(data):
    return data.get("strata", {}).get("setup_args", {}).get("family") == FAMILY


def stock_flags(context):
    return ["--max-context", str(context), "--eos", "1", "--vision", "off", "--dspark", "auto", "--dspark-conf", "0.65"]


def setup_argv(layout):
    setup, server = (layout.profile.data[k] for k in ("strata", "server"))
    args = setup["setup_args"]
    return [str(layout.venv_python), "setup.py", "--family", FAMILY, "--model", MODEL,
            "--context", str(args["context"]), "--vision", "no", "--gpu", str(args["gpu"]),
            "--data-dir", str(layout.data), "--gguf-dir", str(layout.models_dir),
            "--dsv41-package", str(layout.dsv41_package), "--port", str(server["port"]),
            "--host", server["listen_host"], "--yes", "--no-start"]


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
            "windows", "native-windows", 0, "NVIDIA RTX PRO 6000 Blackwell Workstation Edition") or (
            "gpus" in host or type(host.get("gpu_index")) is not int):
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
    if component != COMPONENT:
        problems.append("strata.dsv41_component: differs from the reviewed DeepSeek manifest/build pin")
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
    server = data.get("server") or {}
    if server.get("listen_host") != "127.0.0.1" or server.get("port") != 18090:
        problems.append("server: DeepSeek reviewed listener is 127.0.0.1:18090")
    if (data.get("omp") or {}).get("max_tokens") != 32768:
        problems.append("omp.max_tokens: DeepSeek requires 32768")
    return problems


def pack_dir(layout):
    return layout.data / "packs" / f"{MODEL_NAME}-{MODEL.lower()}"


def component_format():
    from .engine_component import ComponentFormat
    return ComponentFormat(component_id=COMPONENT_ID, entrypoint=ENTRYPOINT, prefix=PACKAGE_PREFIX,
                           max_members=COMPONENT_MAX_MEMBERS, max_total_bytes=COMPONENT_MAX_TOTAL_BYTES)


def inspect_package(layout):
    from . import engine_component
    found = engine_component.inspect_archive(layout.dsv41_package, layout.profile.data["strata"]["artifacts"]["dsv41_package"],
                                              format=component_format())
    if {**found["pin"], "version": found["engine_version"]} != layout.profile.data["strata"]["dsv41_component"]:
        raise IntegrityError("DeepSeek package differs from its separate component pin")
    return found


def verify_engine_tree(layout):
    from . import engine_component
    pin = layout.profile.data["strata"]["dsv41_component"]
    return engine_component.verify_tree(layout.dsv41_engine_dir, pin, engine_version=pin["version"],
                                        format=component_format())


APPLY_USER_ARGS = """
import json, sys
from pathlib import Path
import setup
path = Path(sys.argv[1])
cfg = json.loads(path.read_text(encoding="utf-8-sig"))
pin = json.loads(sys.argv[2])
if "user_args" in cfg and cfg["user_args"] != pin:
    raise SystemExit("stock config has user arguments beyond the reviewed user_args pin")
cfg["user_args"] = pin
setup.write_config(path, cfg)
"""


def apply_user_args(layout, *, run, env, log):
    run([str(layout.venv_python), "-c", APPLY_USER_ARGS, str(layout.strata_config), json.dumps(USER_ARGS)],
        cwd=layout.strata, env=env, log=log, timeout=600)


def verify_generated(layout, cfg):
    """Exact stock text-only, single-card config plus the two reviewed config-only opt-ins."""
    from pathlib import Path

    strata, server = (layout.profile.data[k] for k in ("strata", "server"))
    pack, engine = pack_dir(layout).resolve(), layout.dsv41_engine_dir.resolve()
    problems = []
    if set(cfg) != CONFIG_KEYS:
        problems.append(f"config keys differ from reviewed DeepSeek: {sorted(set(cfg) ^ CONFIG_KEYS)}")
    args = ["--pack", str(pack), *stock_flags(strata["setup_args"]["context"])]
    # A setup re-run over an installed root puts the pinned user_args back over the generated args (stock setup.py
    # carry_user_args: user_args.merge, then stamp). Both are stock's own states; every start merges the same way.
    if cfg.get("args") not in (args, args + USER_ARGS) or cfg.get("args_written") != cfg.get("args"):
        problems.append("args / args_written differ from stock DeepSeek pack and flags")
    for key, want in (("arch", FAMILY), ("model_name", MODEL_NAME), ("user_args", USER_ARGS), ("env", ENGINE_ENV),
                      ("engine_ready_s", READY_SECONDS), ("gpu", 0), ("gpus_asked", True),
                      ("port", server["port"]), ("host", server["listen_host"])):
        if cfg.get(key) != want or key in ("gpu", "port", "engine_ready_s") and type(cfg.get(key)) is not int:
            problems.append(f"{key} differs from reviewed DeepSeek config")
    for key, expected in (("exe", engine / ENTRYPOINT), ("cwd", layout.strata.resolve()),
                          ("tokenizer", pack / "tokenizer"), ("log", layout.strata_config.with_suffix(".log").resolve())):
        actual = cfg.get(key)
        if not isinstance(actual, str) or Path(actual).resolve() != expected:
            problems.append(f"{key} is not the stock isolated DeepSeek path")
    if cfg.get("lib_dirs") != [str(engine)]:
        problems.append("lib_dirs must be exactly the separate DeepSeek package directory")
    try:
        geometry = (pack / "ds4.txt").read_text(encoding="utf-8").splitlines()
        directories = [line.removeprefix("model_dir ") for line in geometry if line.startswith("model_dir ")]
        if directories != [str(layout.models_dir.resolve())]:
            problems.append("DeepSeek ds4.txt model_dir differs from the verified input directory")
        rows = [line.split(" ", 2) for line in (pack / "tensors.txt").read_text(encoding="utf-8").splitlines()
                if line.startswith("file ")]
        paths = [(layout.models_dir / row[2]).resolve() for row in rows]
        expected = {layout.model_file(entry).resolve() for i, entry in enumerate(layout.profile.data["model"]["files"])
                    if i != 5}  # the metadata-only Unsloth shard supplies geometry, never tensors
        if (len(rows) != len(expected) or {row[1] for row in rows} != {str(i) for i in range(len(expected))}
                or set(paths) != expected):
            problems.append("DeepSeek tensors.txt does not name exactly the verified four-shard/Engram/DSpark inputs")
    except (OSError, ValueError, IndexError) as exc:
        problems.append(f"DeepSeek pack source map unreadable: {exc}")
    return problems


def check_pack_info(layout, *, run, env, log):
    import os
    result = run([str(layout.dsv41_engine_dir / ENTRYPOINT), "--pack-info", "--pack", str(pack_dir(layout))],
                 cwd=layout.strata, env={**env, "PATH": str(layout.dsv41_engine_dir) + os.pathsep + env.get("PATH", "")},
                 capture=True, log=log, timeout=300)
    text = (result.stdout or "") + (result.stderr or "")
    if "MISSING" in text or "all present" not in text:
        raise IntegrityError("DeepSeek --pack-info did not confirm every packed input present")


def verify_inputs(layout, *, log):
    """Stock warns and accepts wrong own-files: independently hash every input before letting it run."""
    if layout.models_dir.exists():
        allowed = {row[2].rsplit("/", 1)[-1] for row in FILES}
        extra = {p.name for p in layout.models_dir.glob("*.gguf")} - allowed
        if extra:
            raise IntegrityError(f"DeepSeek models directory holds unreviewed GGUF files: {sorted(extra)}")
    # Stock searches this default shared directory before --gguf-dir and accepts local files by size.
    shared = layout.data / "models" / f"{MODEL_NAME}-shared"
    if shared.exists() and any(shared.iterdir()):
        raise IntegrityError("DeepSeek stock shared directory must be empty; all verified inputs belong beside the shards")
    for entry in layout.profile.data["model"]["files"]:
        verify_file(layout.model_file(entry), entry["bytes"], entry["sha256"], source=entry["sha256_source"],
                    deep=True, log=log)
    verify_file(layout.dsv41_package, PACKAGE["bytes"], PACKAGE["sha256"], source=PACKAGE["sha256_source"], deep=True, log=log)


def start_evidence(server_text, engine_text):
    """One explicit six-expert start; all CPU-lane experts copied, DSpark's auto decline corroborated."""
    lines = engine_text.splitlines()
    starts = [line for line in lines if line.startswith("[strata] ") and " engine started: " in line]
    if len(starts) != 1:
        raise ValueError("DeepSeek requires exactly one engine generation")
    if any(marker in server_text for marker in ("ds4: experts per word:", "ds4: DSpark", "ds4: CUDA")):
        raise ValueError("DeepSeek engine evidence appeared in the server stream")
    for line in [*server_text.splitlines(), *lines]:
        if ("ds4: RAM store:" in line or "ds4: --ssd-cache:" in line or "do not all fit the RAM" in line
                or "ds4 slots: folder " in line or "ds4 slots: wrote " in line):
            raise ValueError("DeepSeek degraded placement or disk cache: " + line)
    def single(marker, pattern):
        candidates = [line for line in lines if marker in line]
        if len(candidates) != 1 or (match := pattern.fullmatch(candidates[0])) is None:
            raise ValueError("DeepSeek missing, repeated or unrecognised start evidence: " + marker)
        return match
    experts = single("ds4: experts per word:", re.compile(re.escape(EXPERTS_LINE)))
    dspark = single("ds4: DSpark", DSPARK_DECLINED)
    if int(dspark["experts"]) <= 1.5 * int(dspark["gpu"]):
        raise ValueError("DeepSeek DSpark decline inconsistent with stock auto threshold")
    copy_all = single("copied in at load, no demand store", COPY_ALL)
    copied = single("experts copied into RAM", COPIED)
    placement = single("ds4: CUDA", PLACEMENT)
    cpu = single("routed experts on the CPU lane", CPU_LANE)
    total, gpu = int(placement["total"]), int(placement["gpu"])
    count = int(cpu["total"])
    if (total != 15360 or not 0 < gpu < total or count != total - gpu or count != int(cpu["copied"])
            or count != int(copied["total"]) or count != int(copied["copied"])):
        raise ValueError("DeepSeek placement does not prove every non-VRAM expert copied into RAM")
    return {"experts_per_word": 6, "dspark": "auto-declined", "gpu_experts": gpu, "cpu_experts": count,
            "cpu_lane": "copy-all", "disk_conversation_cache": False,
            "lines": [m[0] for m in (experts, dspark, copy_all, copied, placement, cpu)],
            "reasoning_effort_wire": dict(EFFORT_WIRE)}
