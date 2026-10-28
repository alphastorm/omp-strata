"""Candidate profile loading and semantic validation (gate G01).

A profile is the single nonsecret source of truth for one candidate: host expectations, the stock Strata setup
choices, every pinned artifact and the OMP route. Validation rejects anything that could let an unpinned,
placeholder or contradictory value reach an install or a launch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import canonical_json, flag_pairs, is_sha256, read_json, release_version, sha256_bytes

SENTINEL = re.compile(r"(?i)\b(RESOLVE_[A-Z0-9_]*|TODO|TBD|FIXME|CHANGEME|PLACEHOLDER|XXX+)\b|<[a-z_ -]+>")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
PROFILE_ID = re.compile(r"[a-z0-9][a-z0-9.-]{2,119}")
STATUSES = ("draft", "candidate", "qualified")
CONTEXTS = (8192, 32768, 65536, 131072, 262144, 393216, 524288)   # stock setup.py CONTEXTS
# The model's trained length (stock setup's derived_factor). Past it stock setup adds yarn rope scaling with the
# factor context / TRAINED_CONTEXT, an experimental upstream feature; inside it, no rope flags.
TRAINED_CONTEXT = 262144
KV_FORMATS = ("int8", "q4_0", "k8v4")
LOOPBACK = ("127.0.0.1", "::1")
PLATFORMS = ("windows-x64", "darwin-arm64", "linux-x64")
# Capabilities this integration can never claim in v0.1, whatever the evidence.
NEVER_CLAIMED = ("durable_engine_state", "multi_tenant")
# Capabilities that stay off until their own optional gate (G22/G23) is designed and passed.
OPTIONAL_OFF = ("vision", "remote_client")
TUNING_FLAGS = ("--pcie-frac", "--pool-workers", "--spec-min-p-tuned",
                "--adapt-every", "--adapt-swaps", "--adapt-decay")
# Stock tools/calibrate.py DEFAULTS: the flags setup's calibration sets, and what each returns to when a calibration
# keeps the default (None: no flag, the engine's own choice). A profile pins kept values in strata.calibration.
CALIBRATION_DEFAULTS = {"--pcie-frac": None, "--spec-min-p": "0.5", "--pool-workers": None,
                        "--adapt-every": None, "--adapt-swaps": None, "--adapt-decay": None}
CALIBRATION_VALUES = {"--pcie-frac": re.compile(r"0\.\d\d|1\.00"), "--spec-min-p": re.compile(r"0\.\d\d"),
                      "--pool-workers": re.compile(r"[1-9]\d{0,2}"), "--adapt-every": re.compile(r"1"),
                      "--adapt-swaps": re.compile(r"80|160"), "--adapt-decay": re.compile(r"0\.97")}
# Stock setup v0.1.39+ (#642) writes --pool-workers on a hybrid CPU with more efficiency than performance cores:
# max(1, P - 1 + E // 2) for host.cpu_cores [P, E], physical cores as its cpu_cores() counts them.
HYBRID_POOL_SINCE = (0, 1, 39)
# Engine 0.1.52's automatic RAM PLE residency advises "--ple-io direct forces them" for direct SSD reads.
PLE_RESIDENCY_SINCE = (0, 1, 52)
# Stock setup `--parallel N` (#465, v0.1.38+) writes the config's "parallel": N batch slots; the engine runs at most
# PARALLEL_MAX together. The draft admits only a count stock setup does not warn about for the planned card.
PARALLEL_MAX = 8
# Stock setup's printed host recommendations (bench_tips, v0.1.40+): engine flags it tells the user to add to the
# config's args, with its values. A profile may pin exactly these; install adds them to stock setup's config.
STOCK_TIPS = {"--conversation-cache-mib": "8192", "--prefill": "auto:32768"}
CONVERSATION_CACHE_FLAGS = ("--conversation-cache-mib", "--conversation-cache-slots", "--conversation-cache-min-free-mib")


def stock_pool_workers(host: dict, engine_version: Any) -> str | None:
    """Stock setup's --pool-workers recommendation for this host and engine version; None when it writes none."""
    cores = host.get("cpu_cores")
    version = release_version(str(engine_version))
    if (version is None or version < HYBRID_POOL_SINCE or not isinstance(cores, list)
            or len(cores) != 2 or not all(type(c) is int and c > 0 for c in cores)):
        return None
    p, e = cores
    return str(max(1, p - 1 + e // 2)) if e > p else None


def gpu_requirements(host: dict) -> tuple[dict, ...]:
    """Fresh ordered card requirements, without inventing legacy architecture or bus identity."""
    if "gpus" in host:
        return tuple(dict(card) for card in host["gpus"])
    return ({"gpu_index": host["gpu_index"], "gpu_model": host["gpu_model"],
             "min_gpu_vram_mib": host["min_gpu_vram_mib"],
             "display_attached": host.get("display_attached", False), "arch": None, "pci_bus_id": None},)


class ProfileError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Profile:
    path: Path
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.data["profile_id"]

    @property
    def fingerprint(self) -> str:
        """SHA-256 over the canonical profile content (the nonsecret candidate identity)."""
        return sha256_bytes(canonical_json(self.data))

    def omp_artifact(self, platform: str) -> dict[str, Any]:
        return self.data["omp"]["artifacts"][platform]

    @property
    def gpu_requirements(self) -> tuple[dict, ...]:
        return gpu_requirements(self.data["host"])

    @property
    def gpu_indices(self) -> tuple[int, ...]:
        return tuple(card["gpu_index"] for card in self.gpu_requirements)

    @property
    def multi_gpu(self) -> bool:
        return "gpus" in self.data["host"]

    @property
    def keeps_conversations(self) -> bool:
        """The profile pins keeping a conversation beside the active one: batch slots or stock's parking tip."""
        strata = self.data["strata"]
        return ((strata["setup_args"].get("parallel") or 1) > 1
                or "--conversation-cache-mib" in (strata.get("stock_tips") or {}))

    @property
    def parks_automatically(self) -> bool:
        """Engine 0.1.48+ without --conversation-cache-mib sizes its conversation cache from the RAM free after load
        and leaves it off when too little is free (Strata #3493): only the running engine knows which it chose."""
        strata = self.data["strata"]
        engine = tuple(int(n) for n in str(strata["engine_version"]).lstrip("v").split("."))
        return engine >= (0, 1, 48) and "--conversation-cache-mib" not in strata["expected_engine_flags"]

    def model_url(self, file_entry: dict[str, Any]) -> str:
        m = self.data["model"]
        return f"https://huggingface.co/{m['repository']}/resolve/{m['revision']}/{file_entry['path']}"


def _walk_strings(value: Any, path: str = ""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(value, str):
        yield path, value


def _check_artifact(problems: list[str], where: str, art: Any, *, need_url: bool = True) -> None:
    if not isinstance(art, dict):
        problems.append(f"{where}: missing artifact pin")
        return
    if need_url:
        url = art.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            problems.append(f"{where}.url: must be an https URL")
        elif "/latest/" in url or "/resolve/main/" in url:
            problems.append(f"{where}.url: mutable reference ({url}) is not a pin")
    size = art.get("bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        problems.append(f"{where}.bytes: must be a positive integer")
    if not is_sha256(art.get("sha256")):
        problems.append(f"{where}.sha256: must be 64 lowercase hex characters")
    if not isinstance(art.get("sha256_source"), str) or not art["sha256_source"].strip():
        problems.append(f"{where}.sha256_source: record where the expected digest came from")


def _calibration_settings(problems: list[str], cal: Any) -> dict[str, str]:
    """strata.calibration: what stock tools/calibrate.py kept on the measured install, with its provenance."""
    if cal is None:
        return {}
    settings = cal.get("settings") if isinstance(cal, dict) else None
    if not isinstance(settings, dict) or not settings:
        problems.append("strata.calibration.settings: the nonempty settings stock calibration kept (when it keeps "
                        "every default, the uncalibrated profile already is the calibrated one)")
        return {}
    for flag, value in settings.items():
        pattern = CALIBRATION_VALUES.get(flag)
        if pattern is None or not isinstance(value, str) or not pattern.fullmatch(value):
            problems.append(f"strata.calibration.settings: {flag} {value!r} is not a stock calibration setting")
    adapt = tuple(settings.get(f) for f in ("--adapt-every", "--adapt-swaps", "--adapt-decay"))
    if adapt not in ((None, None, None), ("1", "80", "0.97"), ("1", "160", "0.97")):
        problems.append("strata.calibration.settings: adaptive tier must be a complete stock calibration candidate")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,40}", str(cal.get("measured_on"))):
        problems.append("strata.calibration.measured_on: the public label of the host it was measured on")
    if not re.fullmatch(r"\d{4}-\d\d-\d\d", str(cal.get("date"))):
        problems.append("strata.calibration.date: the measurement date, YYYY-MM-DD")
    if not isinstance(cal.get("source_profile"), str) or not is_sha256(cal.get("source_fingerprint")):
        problems.append("strata.calibration: source_profile and source_fingerprint of the measured install")
    if not isinstance(cal.get("report"), dict):
        problems.append("strata.calibration.report: stock calibrate.py's report")
    return {k: v for k, v in settings.items() if k in CALIBRATION_VALUES}


def _check_engine_component(problems: list[str], comp: Any, strata: dict, host: dict) -> None:
    """strata.engine_component: a stock engine tarball staged into the native engine folder before stock setup
    (omp_strata/engine_component.py). The engine is versioned apart from the app tag; the raw manifest's SHA-256 binds
    its file table, BUILD.json's source and commit bind the build."""
    keys = ("format", "platform", "backend", "variant", "manifest_sha256", "build_id", "build_source", "build_commit")
    if not isinstance(comp, dict) or set(comp) != set(keys):
        problems.append(f"strata.engine_component: exactly {list(keys)} required")
        return
    for key, want in (("format", "tar.gz"), ("platform", "windows-x86_64"), ("backend", "cuda"), ("variant", "cuda13")):
        if comp[key] != want:
            problems.append(f"strata.engine_component.{key}: only {want!r} (native Windows CUDA 13) is reviewed")
    if not is_sha256(comp["manifest_sha256"]):
        problems.append("strata.engine_component.manifest_sha256: SHA-256 of the raw engine-component.json")
    if not isinstance(comp["build_id"], str) or not comp["build_id"].strip():
        problems.append("strata.engine_component.build_id: the manifest's build_id")
    if not isinstance(comp["build_source"], str) or comp["build_source"] in ("", "local"):
        problems.append("strata.engine_component.build_source: BUILD.json's source of a published build")
    if not re.fullmatch(r"[0-9a-f]{7,40}", str(comp["build_commit"])):
        problems.append("strata.engine_component.build_commit: BUILD.json's commit")
    tag, version = str(strata.get("tag", "")), str(strata.get("engine_version", ""))
    if release_version(tag) is None or tag.endswith("-beta"):
        problems.append("strata.tag: a component engine needs a stable release tag")
    if release_version(version) is None or version.endswith("-beta"):
        problems.append("strata.engine_version: the component's own numeric version, never the app tag")
    file = f"strata-engine-{version}-{comp['platform']}-{comp['backend']}-{comp['variant']}.tar.gz"
    art = (strata.get("artifacts") or {}).get("engine_archive") or {}
    if art.get("file") != file or art.get("url") != f"https://github.com/Niko1221/Strata/releases/download/{tag}/{file}":
        problems.append(f"strata.artifacts.engine_archive: must be {file} of release {tag}")
    if host.get("os") != "windows":
        problems.append("host.os: the component engine lane is native Windows only")


def validate(data: Any, *, require_status: str | None = None) -> list[str]:
    """Return every problem found; an empty list means the profile is usable for install/launch."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["profile: must be a JSON object"]
    if data.get("schema_version") != 1:
        problems.append("schema_version: must be 1")
    pid = data.get("profile_id")
    if not isinstance(pid, str) or not PROFILE_ID.fullmatch(pid):
        problems.append("profile_id: 3-120 lowercase letters, digits, dots and dashes")
    status = data.get("status")
    if status not in STATUSES:
        problems.append(f"status: one of {STATUSES}")
    elif require_status and STATUSES.index(status) < STATUSES.index(require_status):
        problems.append(f"status: {status} is below the required {require_status}")
    for where, text in _walk_strings(data):
        if SENTINEL.search(text) and not where.endswith("sha256_source"):
            problems.append(f"{where}: unresolved sentinel or placeholder in {text!r}")

    host = data.get("host") or {}
    if host.get("os") not in ("windows", "linux"):
        problems.append("host.os: windows or linux (macOS has no Strata GPU runtime)")
    multi_gpu = "gpus" in host
    for key in ((() if multi_gpu else ("min_gpu_vram_mib",)) + ("min_total_ram_gib", "min_available_ram_gib_at_start", "min_driver_major",
                "min_free_disk_gib")):
        v = host.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
            problems.append(f"host.{key}: positive number required")
    if not isinstance(host.get("display_attached", False), bool):
        problems.append("host.display_attached: true or false (whether the GPU also drives a display)")
    cores = host.get("cpu_cores")
    if cores is not None and not (isinstance(cores, list) and len(cores) == 2
                                  and all(type(c) is int and c > 0 for c in cores)):
        problems.append("host.cpu_cores: [performance, efficiency] physical cores of a hybrid CPU, or absent")

    server = data.get("server") or {}
    if server.get("listen_host") not in LOOPBACK:
        problems.append("server.listen_host: loopback only (127.0.0.1 or ::1)")
    port = server.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not 1024 < port < 65536:
        problems.append("server.port: an unprivileged TCP port")
    if server.get("api_key_env") != "STRATA_API_KEY":
        problems.append("server.api_key_env: must be STRATA_API_KEY (stock Strata's environment key)")
    if server.get("shared_settings") != "empty":
        problems.append("server.shared_settings: only 'empty' (frozen stock defaults) is supported")
    for key in ("ready_timeout_s", "stop_timeout_s"):
        v = server.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 3600:
            problems.append(f"server.{key}: 1..3600 seconds")

    strata = data.get("strata") or {}
    if not HEX40.match(str(strata.get("commit", ""))):
        problems.append("strata.commit: full 40-hex commit required")
    if not str(strata.get("repository", "")).startswith("https://"):
        problems.append("strata.repository: https URL required")
    setup = strata.get("setup_args") or {}
    if multi_gpu:
        allowed_setup = {"family", "model", "context", "kv", "vision", "experimental_speed_projection",
                         "low_ram", "gpus", "layer_split", "parallel", "gpu_roles"}
        if set(setup) - allowed_setup:
            problems.append(f"strata.setup_args: unreviewed multi-GPU options {sorted(set(setup) - allowed_setup)}")
        scalar = {"gpu_index", "gpu_model", "min_gpu_vram_mib", "display_attached"} & host.keys()
        if scalar:
            problems.append(f"host.gpus: scalar GPU fields must be absent: {sorted(scalar)}")
        cards = host["gpus"]
        if not isinstance(cards, list) or len(cards) < 2:
            problems.append("host.gpus: at least two card requirements required")
            cards = []
        indices, buses = [], []
        fields = {"gpu_index", "gpu_model", "arch", "pci_bus_id", "min_gpu_vram_mib", "display_attached"}
        for i, card in enumerate(cards):
            where = f"host.gpus[{i}]"
            if not isinstance(card, dict):
                problems.append(f"{where}: card object required")
                continue
            if set(card) != fields:
                problems.append(f"{where}: exactly {sorted(fields)} required")
            index = card.get("gpu_index")
            if type(index) is not int or index < 0:
                problems.append(f"{where}.gpu_index: nonnegative integer required")
            else:
                indices.append(index)
            model = card.get("gpu_model")
            if not isinstance(model, str) or not model.startswith("NVIDIA ") or not model.strip():
                problems.append(f"{where}.gpu_model: exact NVIDIA model name required")
            arch = card.get("arch")
            if not isinstance(arch, str) or not re.fullmatch(r"[1-9]\d{1,2}", arch) or int(arch) < 75:
                problems.append(f"{where}.arch: CUDA 13-compatible architecture required (75 or newer)")
            bus = card.get("pci_bus_id")
            if not isinstance(bus, str) or not re.fullmatch(r"[0-9a-f]{8}:[0-9a-f]{2}:[01][0-9a-f]\.[0-7]", bus):
                problems.append(f"{where}.pci_bus_id: canonical lowercase PCI BDF required")
            else:
                buses.append(bus)
            if type(card.get("min_gpu_vram_mib")) is not int or card["min_gpu_vram_mib"] <= 0:
                problems.append(f"{where}.min_gpu_vram_mib: positive integer required")
            if type(card.get("display_attached")) is not bool:
                problems.append(f"{where}.display_attached: boolean required")
        if len(set(indices)) != len(indices) or len(set(buses)) != len(buses):
            problems.append("host.gpus: indices and PCI bus IDs must be unique")
        selected = setup.get("gpus")
        if (not isinstance(selected, list) or any(type(i) is not int for i in selected)
                or selected != indices or len(indices) != len(cards)):
            problems.append("strata.setup_args.gpus: must equal host.gpus indices in order")
        if "gpu" in setup:
            problems.append("strata.setup_args.gpu: absent for multi-GPU")
        if host.get("os") != "windows":
            problems.append("host.os: multi-GPU requires native Windows NVIDIA")
        if setup.get("low_ram") != "off":
            problems.append("strata.setup_args: multi-GPU requires low_ram off")
        split = setup.get("layer_split")
        # Stock "auto", or one manual split point (the second card's first layer) for two cards in stock order.
        if split != "auto" and not (isinstance(split, str) and re.fullmatch(r"[1-9][0-9]?", split)
                                    and len(indices) == 2 and "gpu_roles" not in setup):
            problems.append("strata.setup_args.layer_split: 'auto', or one manual split point for two cards")
        roles = setup.get("gpu_roles")
        if roles is not None:
            # Stock --gpu-roles: the engine takes the Helpers by card number, then the Main card last; setup writes
            # that list as "gpu" with "gpu_order": "as_given", so setup_args.gpus is exactly that mirror.
            expected = ({str(i): "helper" for i in sorted(indices[:-1])} | {str(indices[-1]): "main"}
                        if indices else {})
            if not isinstance(roles, dict) or roles != expected or indices[:-1] != sorted(indices[:-1]):
                problems.append("strata.setup_args.gpu_roles: one Main card last and Helpers by card number, "
                                "matching setup_args.gpus")
        forbidden_keys = {"gpu_order", "replicas", "skip_split", "no_layer_split", "peer_device", "peer_experts",
                          "remote_expert_opt", "no_remote_expert_opt", "helper", "helpers", "helper_cache",
                          "reserve", "reserve_mib", "reserve_vram", "env", "backend", "cuda"}
        for where, block in (("host", host), ("strata", strata), ("strata.setup_args", setup)):
            if forbidden_keys & block.keys():
                problems.append(f"{where}: unreviewed multi-GPU topology/tuning {sorted(forbidden_keys & block.keys())}")
        if ("budget_plan" in strata
                or (setup.get("family"), setup.get("model")) == ("unsloth", "UD-Q4_K_XL")):
            problems.append("strata: budget lanes are not supported for multi-GPU")
    else:
        if "gpus" in setup or "layer_split" in setup or "gpu_roles" in setup:
            problems.append("strata.setup_args: single-GPU requires scalar gpu, no layer_split and no gpu_roles")
        if type(host.get("gpu_index")) is not int or host["gpu_index"] < 0:
            problems.append("host.gpu_index: nonnegative integer required")
        if not isinstance(host.get("gpu_model"), str) or not host["gpu_model"].strip():
            problems.append("host.gpu_model: nonblank model required")
        if type(setup.get("gpu")) is not int or setup.get("gpu") != host.get("gpu_index"):
            problems.append("strata.setup_args.gpu: must equal host.gpu_index")
    ctx = setup.get("context")
    if ctx not in CONTEXTS:
        problems.append(f"strata.setup_args.context: one of stock setup's {CONTEXTS}")
    if setup.get("kv") not in KV_FORMATS:
        problems.append(f"strata.setup_args.kv: one of {KV_FORMATS}")
    if setup.get("vision") not in ("no", "none"):
        problems.append("strata.setup_args.vision: text-only profiles require 'no' until G22 exists")
    if setup.get("experimental_speed_projection") != "off":
        problems.append("strata.setup_args.experimental_speed_projection: must be off")
    if setup.get("low_ram") not in ("on", "off"):
        problems.append("strata.setup_args.low_ram: explicit on/off (auto would depend on the host's free RAM)")
    for key in ("family", "model"):
        if not isinstance(setup.get(key), str) or not setup[key]:
            problems.append(f"strata.setup_args.{key}: required")
    parallel = setup.get("parallel")
    if parallel is not None and (type(parallel) is not int or not 2 <= parallel <= PARALLEL_MAX):
        problems.append(f"strata.setup_args.parallel: absent (one request at a time) or 2..{PARALLEL_MAX} batch slots")
    pipeline_pinned = "pipeline_windows" in strata
    if pipeline_pinned:
        if type(strata["pipeline_windows"]) is not int or strata["pipeline_windows"] != 2:
            problems.append("strata.pipeline_windows: exactly the integer 2 required")
        if not multi_gpu or not isinstance(host.get("gpus"), list) or len(host["gpus"]) < 2:
            problems.append("strata.pipeline_windows: requires a multi-card layer-split profile")
        if type(parallel) is int and parallel >= 2:
            problems.append("strata.pipeline_windows: incompatible with strata.setup_args.parallel >= 2 (batch slots)")
    ple_pinned = "ple_io" in strata
    if ple_pinned:
        if strata["ple_io"] != "direct":
            problems.append("strata.ple_io: exactly 'direct' required (stock --ple-io direct)")
        version = release_version(str(strata.get("engine_version")))
        if version is None or version < PLE_RESIDENCY_SINCE:
            problems.append("strata.ple_io: engine 0.1.52 or newer required "
                            "(the automatic RAM PLE residency it replaces)")
    tips = strata.get("stock_tips")
    if tips is not None and (not isinstance(tips, dict) or not tips
                             or any(STOCK_TIPS.get(f) != v for f, v in tips.items())):
        problems.append(f"strata.stock_tips: a nonempty subset of stock setup's recommendations {STOCK_TIPS}")
        tips = None
    flags = strata.get("expected_engine_flags") or []
    if not isinstance(flags, list) or not flags or not all(isinstance(f, str) for f in flags):
        problems.append("strata.expected_engine_flags: nonempty list of strings")
    else:
        pairs = flag_pairs(flags)
        if pipeline_pinned:
            if pairs.get("--pipeline-windows") != "2" or flags.count("--pipeline-windows") != 1:
                problems.append("strata.pipeline_windows: expected_engine_flags must pin --pipeline-windows 2 exactly once")
        elif "--pipeline-windows" in pairs:
            problems.append("strata.pipeline_windows: --pipeline-windows only as this pinned field")
        if ple_pinned:
            if pairs.get("--ple-io") != "direct" or flags.count("--ple-io") != 1:
                problems.append("strata.ple_io: expected_engine_flags must pin --ple-io direct exactly once")
        elif pairs.get("--ple-io") == "direct":
            problems.append("strata.ple_io: --ple-io direct only as this pinned field")
        if multi_gpu and any(f.startswith(("--layer-split", "--batch", "--peer-", "--remote-expert",
                                            "--reserve", "--gpu-order", "--replica")) for f in pairs):
            problems.append("strata.expected_engine_flags: runtime split/batch and helper/tuning flags are not setup flags")
        if pairs.get("--max-context") != str(ctx):
            problems.append("strata.expected_engine_flags: --max-context must equal setup_args.context")
        if isinstance(ctx, int) and ctx > 8192 and pairs.get("--kv") != setup.get("kv"):
            problems.append("strata.expected_engine_flags: --kv must equal setup_args.kv")
        scaled = isinstance(ctx, int) and ctx > TRAINED_CONTEXT
        rope = ("yarn", f"{ctx / TRAINED_CONTEXT:g}") if scaled else (None, None)
        if (pairs.get("--rope-scaling"), pairs.get("--rope-scale")) != rope:
            problems.append("strata.expected_engine_flags: rope scaling must be stock setup's "
                            + (f"yarn {rope[1]}" if rope[0] else "none") + f" for a {ctx}-token context")
        variant = {"--mmap-experts", "--resident-experts"} & set(flags)
        budget_model = setup.get("family") == "unsloth" and setup.get("model") == "UD-Q4_K_XL"
        if budget_model:
            plan = strata.get("budget_plan") or {}
            budget = plan.get("resident_budget_gib") if isinstance(plan, dict) else None
            if type(budget) is not int or budget <= 0 or pairs.get("--resident-budget-gib") != str(budget):
                problems.append("strata.expected_engine_flags: --resident-budget-gib must equal the positive "
                                "integer in strata.budget_plan.resident_budget_gib")
            if setup.get("low_ram") != "off" or variant or "--experts" in pairs:
                problems.append("strata.expected_engine_flags: budget models map GGUF experts in place; "
                                "low_ram must be off without --mmap-experts, --resident-experts or --experts")
        elif "--resident-budget-gib" in pairs or strata.get("budget_plan") is not None:
            problems.append("strata.expected_engine_flags: --resident-budget-gib is only for stock budget models")
        if setup.get("low_ram") == "off" and variant:
            problems.append(f"strata.expected_engine_flags: {sorted(variant)} contradict low_ram off")
        if setup.get("low_ram") == "on" and len(variant) != 1:
            problems.append("strata.expected_engine_flags: low_ram on needs exactly one of --mmap-experts or "
                            "--resident-experts (stock setup's variant)")
        calibration = strata.get("calibration")
        settings = _calibration_settings(problems, calibration)
        stock_pool = stock_pool_workers(host, strata.get("engine_version"))
        for f in TUNING_FLAGS:
            if f == "--pool-workers" and stock_pool is not None:
                if calibration is not None:
                    problems.append("strata.calibration on a hybrid CPU is unreviewed: stock setup and calibrate "
                                    "both set --pool-workers")
                elif pairs.get(f) != stock_pool:
                    problems.append(f"strata.expected_engine_flags: --pool-workers must be stock setup's hybrid-CPU "
                                    f"recommendation {stock_pool} for host.cpu_cores")
            elif f in pairs and f not in settings:
                problems.append(f"strata.expected_engine_flags: calibration/tuning flag {f} must stay off unless "
                                "strata.calibration pins it")
        if calibration is not None:
            for f, default in CALIBRATION_DEFAULTS.items():
                if pairs.get(f) != settings.get(f, default):
                    problems.append(f"strata.expected_engine_flags: {f} must be stock calibration's "
                                    f"{settings.get(f, default)!r}")
        for f, value in (tips or {}).items():
            if pairs.get(f) != value:
                problems.append(f"strata.expected_engine_flags: {f} must be the pinned stock tip {value!r}")
        for f in CONVERSATION_CACHE_FLAGS:
            if f in pairs and f not in (tips or {}):
                problems.append(f"strata.expected_engine_flags: {f} only as stock setup's pinned tip (strata.stock_tips)")
        if pairs.get("--prefill", "auto") != "auto" and "--prefill" not in (tips or {}):
            problems.append("strata.expected_engine_flags: --prefill other than stock setup's auto only as its pinned tip")
    forbidden = strata.get("forbidden_engine_flags") or []
    if not isinstance(forbidden, list):
        problems.append("strata.forbidden_engine_flags: list required")
    elif isinstance(flags, list) and set(forbidden) & set(flags):
        problems.append("strata.forbidden_engine_flags overlaps expected_engine_flags")
    if not isinstance(strata.get("model_name"), str) or not strata.get("model_name"):
        problems.append("strata.model_name: the exact served model id is required")
    arts = strata.get("artifacts") or {}
    for key in ("engine_archive", "llama_cpp_archive"):
        _check_artifact(problems, f"strata.artifacts.{key}", arts.get(key))
    component = strata.get("engine_component")
    if component is not None:
        _check_engine_component(problems, component, strata, host)
    lock = strata.get("python_lock")
    if not isinstance(lock, dict):
        problems.append("strata.python_lock: {path, python, sha256} required (hash-locked setup.py packages)")
    else:
        lp = lock.get("path")
        if not isinstance(lp, str) or not lp.startswith("locks/") or ".." in lp.split("/"):
            problems.append("strata.python_lock.path: a repository path under locks/")
        if not re.fullmatch(r"3\.\d{1,2}", str(lock.get("python", ""))):
            problems.append("strata.python_lock.python: the interpreter minor version the lock was resolved for")
        if lock.get("sha256") is None:
            if status != "draft":
                problems.append("strata.python_lock.sha256: only a draft profile may leave the lock unresolved")
        elif not is_sha256(lock.get("sha256")):
            problems.append("strata.python_lock.sha256: 64 hex characters")

    model = data.get("model") or {}
    if model.get("format") is not None:
        from . import nvfp4
        if (not nvfp4.is_local(model) or model.get("repository") != nvfp4.REPOSITORY
                or model.get("revision") != nvfp4.REVISION or model.get("quantization") != "NVFP4-QAD"
                or model.get("variant") != "nvfp4" or not nvfp4.validate_conversion(model)
                or (setup.get("family"), setup.get("model")) != ("nvfp4", "NVFP4-QAD")
                or multi_gpu or host.get("gpu_model") != "NVIDIA RTX PRO 6000 Blackwell Workstation Edition"
                or host.get("os") != "windows"):
            problems.append("model.format: only the pinned PRO NVFP4-QAD local conversion is admitted")
        conversion_lock = strata.get("conversion_lock") or {}
        if (conversion_lock.get("path") != "locks/strata-nvfp4-local-cp313-win_amd64.txt"
                or not is_sha256(conversion_lock.get("sha256"))):
            problems.append("strata.conversion_lock: hash-locked Windows FP4 conversion dependencies required")
    elif setup.get("family") == "nvfp4":
        problems.append("model.format: NVFP4 requires an explicit pinned conversion format")
    if not isinstance(model.get("repository"), str) or "/" not in model.get("repository", ""):
        problems.append("model.repository: owner/name required")
    if not HEX40.match(str(model.get("revision", ""))):
        problems.append("model.revision: immutable 40-hex revision required (not a branch)")
    files = model.get("files")
    if not isinstance(files, list) or not files:
        problems.append("model.files: every required shard must be pinned")
    else:
        seen = set()
        for i, f in enumerate(files):
            _check_artifact(problems, f"model.files[{i}]", f, need_url=False)
            p = f.get("path") if isinstance(f, dict) else None
            if not isinstance(p, str) or p.startswith("/") or ".." in p.split("/"):
                problems.append(f"model.files[{i}].path: relative repository path required")
            elif p in seen:
                problems.append(f"model.files[{i}].path: duplicate")
            else:
                seen.add(p)
    mtp = model.get("mtp_source") or {}
    if not HEX40.match(str(mtp.get("revision", ""))):
        problems.append("model.mtp_source.revision: immutable 40-hex revision required")
    tms = mtp.get("tensor_manifest_sha256")
    if tms is not None and not is_sha256(tms):
        problems.append("model.mtp_source.tensor_manifest_sha256: null or 64 hex")

    omp = data.get("omp") or {}
    if not HEX40.match(str(omp.get("source_commit", ""))):
        problems.append("omp.source_commit: full 40-hex commit required")
    arts = omp.get("artifacts") or {}
    if not arts:
        problems.append("omp.artifacts: at least the host platform's stock binary must be pinned")
    for plat, art in arts.items():
        if plat not in PLATFORMS:
            problems.append(f"omp.artifacts.{plat}: unknown platform")
        _check_artifact(problems, f"omp.artifacts.{plat}", art)
    for key, want in (("profile_name", "omp-strata"), ("provider_id", "strata-local")):
        if omp.get(key) != want:
            problems.append(f"omp.{key}: must be {want!r}")
    cw, mt = omp.get("context_window"), omp.get("max_tokens")
    if not isinstance(cw, int) or isinstance(cw, bool) or cw != ctx:
        problems.append("omp.context_window: must equal the configured Strata context")
    if not isinstance(mt, int) or isinstance(mt, bool) or mt < 1024:
        problems.append("omp.max_tokens: at least 1024")
    elif isinstance(cw, int) and mt > cw // 2:
        problems.append("omp.max_tokens: output reserve larger than half the context leaves no usable prompt")

    caps = data.get("capabilities") or {}
    for key in NEVER_CLAIMED:
        if caps.get(key) is not False:
            problems.append(f"capabilities.{key}: must be false in v0.1")
    for key in OPTIONAL_OFF:
        if caps.get(key) is not False:
            problems.append(f"capabilities.{key}: must stay false until its optional gate passes")
    if caps.get("vision") is False and setup.get("vision") not in ("no", "none"):
        problems.append("capabilities.vision false but setup enables the encoder")
    if not caps.get("text") or not caps.get("typed_tools"):
        problems.append("capabilities: text and typed_tools are the reason this profile exists")
    return problems


def load(path: Path, *, require_status: str | None = None) -> Profile:
    data = read_json(path)
    problems = validate(data, require_status=require_status)
    if problems:
        raise ProfileError(problems)
    return Profile(path=path, data=data)


@dataclass(frozen=True)
class ClientRoute:
    """A client identity references server profiles; it never copies their installs or evidence."""
    path: Path
    data: dict[str, Any]
    servers: dict[str, Profile]

    @property
    def id(self) -> str:
        return self.data["profile_id"]

    @property
    def fingerprint(self) -> str:
        return sha256_bytes(canonical_json(self.data))

    @property
    def main(self) -> Profile:
        return self.servers[self.data["roles"]["default"]]


def load_route(path: Path, *, profiles_dir: Path | None = None) -> ClientRoute:
    """Load a public route, resolving exact immutable server pins from the profile directory."""
    return _client_route(path, read_json(path), profiles_dir=profiles_dir)


def _client_route(path: Path, data: dict, *, profiles_dir: Path | None = None) -> ClientRoute:
    from .ompcfg import CHAT_ROLES
    from .receipts import schema_errors

    repo = Path(__file__).resolve().parents[1]
    problems = schema_errors(data, read_json(repo / "schemas/client-route.schema.json"))
    if problems:
        raise ProfileError(problems)
    members = data["members"]
    labels = [m["label"] for m in members]
    if len(set(labels)) != len(labels):
        problems.append("route members: duplicate label")
    ports = [m["local_port"] for m in members]
    if len(set(ports)) != len(ports) or any(not 1 <= p <= 65535 for p in ports):
        problems.append("route members: distinct ports in 1..65535 required")
    if set(data["roles"]) != set(CHAT_ROLES):
        problems.append("route roles: every chat role must be explicitly pinned")
    if any(not isinstance(label, str) or label not in labels for label in [*data["roles"].values(), *data["agents"].values()]):
        problems.append("route roles/agents: unknown member")
    if any(not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name) for name in data["agents"]):
        problems.append("route agents: safe lowercase names required")
    if {"task", "scout"}.intersection(data["agents"]):
        problems.append("route agents: task and scout are reserved stock definitions")
    if problems:
        raise ProfileError(problems)
    servers = {}
    for member in members:
        server = load((profiles_dir or repo / "profiles") / (member["server_profile"] + ".json"))
        if server.fingerprint != member["server_fingerprint"]:
            problems.append("route member server fingerprint mismatch")
        servers[member["label"]] = server
    pins = {canonical_json(server.data["omp"]["artifacts"]) for server in servers.values()}
    if len(pins) != 1:
        problems.append("route members must use the same pinned OMP client")
    if problems:
        raise ProfileError(problems)
    return ClientRoute(path, data, servers)
