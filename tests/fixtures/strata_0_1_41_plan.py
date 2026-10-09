# Planning fixture from Niko1221/Strata v0.1.41 (fb58e0dbc8399662c0e47c76578c6e878b14f6cf).

# Source-faithful constants, helpers and main planning statements; consumed as AST, never imported.

# Exact out-of-lane branches and hardware probe bodies remain present; they are never executed.

HF_REVISIONS = {
    "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF": "ed59f92082b1e93c0e96d60a8b11aab089b52f09",        # 2026-09-29
    "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF": "b22d729eae29b5796f76fb70f91aef549b9fc52c",   # 2026-09-24
    "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF": "5348543e0147355ac9cbcb031184a3546350988e",  # 2026-09-29
    "unsloth/Qwen3.8-Flash-Next-GGUF": "38bb39ee97821de2c9009abb7e93950eec396e66",                   # 2026-09-30
}

LLAMA_CPP_COMMIT = "3cf03257f219afbe7334045ff7c6a06ac68c627d"

CUDA_WHEELS = ["nvidia-cublas==13.0.2.14", "nvidia-cuda-runtime==13.0.96"]

MIN_DRIVER = 580

MIN_ENGINE = (0, 1, 41)

KV_CELL_BYTES = {"q4_0": 576, "k8v4": 816}

PY_PACKAGES = ["numpy", "jinja2", "regex", "pyyaml", "tqdm", "requests", "cmake", "ninja", "pillow", "psutil"]

MODELS = {
    # the original model only for now: Swift 1.5's Q2_0 files split one layer's experts across the two shards, which
    # the pack tool (tools/iq_pack.py) cannot prepare yet (#171)
    "Q2_0": {"about": "2-bit, the fastest", "download_gb": 66.4, "ram_gb": 48, "arena_gb": 34.0, "families": ("qwen",)},
    "IQ2_XS": {"about": "2-bit i-quant, a little better quality, close in speed", "download_gb": 68.0, "ram_gb": 48,
               "arena_gb": 35.5},
    "IQ3_XXS": {"about": "3-bit i-quant, better quality, slower (more CPU work per token)", "download_gb": 75.8,
                "ram_gb": 60, "arena_gb": 42.9},
    # the original model only (Swift 1.5 has no IQ3_S): matches the full BF16 model on the published benchmarks
    "IQ3_S": {"about": "3.5-bit i-quant, the best quality (matches the full model), the slowest; needs a 64 GB PC "
                       "with little else running", "download_gb": 83.6, "ram_gb": 62, "arena_gb": 50.3,
              "families": ("qwen",)},
    # the Coder release: 256 of the 512 experts kept (the ones code, tools and vision use), IQ2_S-IQ4_XS like IQ3_S
    "IQ1_M": {"about": "the Coder's only size: half the experts, stored like IQ3_S (3.5 bits)", "download_gb": 58.4,
              "ram_gb": 32, "arena_gb": 23.4, "families": ("coder",)},
    # EXPERIMENTAL (docs/UNSLOTH_Q4.md): Unsloth's 4-bit file; its 77 GB of experts do not fit a 64 GB PC, so the engine
    # keeps a RAM budget of them (--resident-budget-gib, chosen below) and reads the rest from the GGUF on the SSD
    "UD-Q4_K_XL": {"about": "4-bit (Unsloth Dynamic), EXPERIMENTAL: the best quality, but most experts come from the "
                            "SSD on a 64 GB PC (7-8.5 tokens/s measured)", "download_gb": 111.3, "ram_gb": 48,
                   "arena_gb": 77.0, "families": ("unsloth",), "budget": True, "nvidia_only": True,
                   "experimental": True,
                   # #967: images are allowed (the same base model and image encoder as UD-IQ4_XS), with a warning:
                   # reported working by hand (#967, #971), not tested by us on this file
                   "vision": True, "vision_untested": True},
    # #621: Unsloth's UD-IQ4_XS - IQ3_S gate/up experts with IQ4_NL (43 layers) or Q8_0 (5) downs, the dense side as
    # UD-Q4_K_XL's; three shards.  A regular choice from 0.1.39 (no longer experimental).  Its 59.5 GB of experts: a
    # RAM budget of them, like UD-Q4_K_XL, but far fewer read from the SSD on a 64 GB PC and none from ~80 GB of RAM.
    # Images: the vision path has no restriction for this pack (the same base model and image encoder), so setup asks
    "UD-IQ4_XS": {"about": "~4-bit i-quant (Unsloth Dynamic), between IQ3_S and UD-Q4_K_XL in quality; on a PC with "
                           "less than ~80 GB of RAM part of its experts are read from the SSD",
                  "download_gb": 93.7, "ram_gb": 48, "arena_gb": 59.5, "families": ("unsloth",), "budget": True,
                  "shards": 3, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00003.gguf", "engine": (0, 1, 38),
                  "vision": True},
}

UNSLOTH_SHARDS = {
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf":
        (10946624, "4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082"),
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf":
        (49859583136, "3f342f1c1580473f1ee94ddd5b28206e8c07a70fa1a366f59d1d6c922919a6c9"),
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf":
        (49376141504, "56758f40269cad5cd9b0d3d6fbae0f40f6d5be6de49e4ab392dbe83157d9cbd3"),
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf":
        (12087983520, "753bda48b98ba4f1636134a90a967de1b2d3908a236c026e464777342e53510a"),
}

UNSLOTH_IQ4_XS_SHARDS = {
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf":
        (10946624, "5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf":
        (49835229856, "577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf":
        (43836407744, "d4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833"),
}

UNSLOTH_RAM_LEFT_GB = 24

CONTEXTS = [8192, 32768, 65536, 131072, 204800, 262144, 393216, 524288]

FAMILIES = {
    "qwen": {"title": "Qwen3.8-Flash-Next", "by": "Qwen; GSQ-RCO quants by ISTA-DASLab",
             "about": "the original model",
             "hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF") + "{q}/",
             "file": "Qwen3.8-Flash-Next-GSQ-RCO-{q}-0000{i}-of-00002.gguf", "tag": "",
             "mmproj_hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF"),
             "mmproj": "mmproj-Qwen3.8-Flash-Next-BF16.gguf", "name": "qwen3.8-flash-next"},
    "swift": {"title": "Swift 1.5", "by": "UkisAI's fine-tune of Qwen3.8-Flash-Next",
              "about": "thinks much shorter (-63% thinking tokens, 1.8x sooner answers by its authors' numbers)",
              "hf": hf("ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF"),
              "file": "Swift-Qwen3.8-Flash-Next-GSQ-RCO-{q}-0000{i}-of-00002.gguf", "tag": "swift-",
              "mmproj_hf": hf("ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF"),
              "mmproj": "mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf", "name": "swift-1.5",
              "license": "Swift Open License 1.0: https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF"},
    # ISTA-DASLab's expert-pruned release: half of each layer's experts removed, chosen for code, agentic tool use and
    # vision; its shard 2 (the n-gram table) and vision encoder are the original's files, shared with it
    "coder": {"title": "Qwen3.8-Flash-Next Coder", "by": "ISTA-DASLab's coding version",
              "about": "half the experts (code, tools, images kept): needs ~32 GB of RAM, faster; weaker outside coding",
              "hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF") + "{q}/",
              "file": "Qwen3.8-Flash-Next-GSQ-RCO-{q}-0000{i}-of-00002.gguf", "tag": "coder-",
              "mmproj_hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF"),
              "mmproj": "mmproj-Qwen3.8-Flash-Next-BF16.gguf", "name": "qwen3.8-flash-next-coder",
              "profile": "expert-profile-coder.bin"},
    # Unsloth's UD-IQ4_XS (three shards, #621; a regular choice from 0.1.39) and the EXPERIMENTAL UD-Q4_K_XL (four)
    # of the original model (docs/UNSLOTH_Q4.md); "experimental" and "vision" are per model (MODELS)
    "unsloth": {"title": "Qwen3.8-Flash-Next (Unsloth)", "by": "Unsloth's ~4-bit quantizations",
                "about": "UD-IQ4_XS: a 94 GB download; with less than ~80 GB of RAM part of its experts are read from "
                         "the SSD (UD-Q4_K_XL, 111 GB: experimental)",
                "hf": hf("unsloth/Qwen3.8-Flash-Next-GGUF") + "{q}/",
                "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00004.gguf", "shards": 4, "tag": "unsloth-",
                "mmproj_hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF"),
                "mmproj": "mmproj-Qwen3.8-Flash-Next-BF16.gguf", "name": "qwen3.8-flash-next-unsloth",
                "vision": False, "pack_args": ["--compat-bf16"],
                "sha256": {**UNSLOTH_SHARDS, **UNSLOTH_IQ4_XS_SHARDS}},
}

def hybrid_pool_workers(cores) -> int | None:
    """#642 (Hardin22's measurement): on a hybrid CPU the expert pool runs best on the P-cores but the host loop's one
    plus HALF of the E-cores - an E-core runs the expert kernels ~2.2x slower and each layer waits for its slowest
    part (i9-14900KF, 8P + 16E: 15 workers decoded 165 / 116 tok/s against 106 / 84 with all 23).  Only on a CPU with
    more E-cores than P-cores: on an i7-13700KF (8P + 8E, docs/AMD_HIP.md's gfx1030 report) all 15 workers decoded
    38-42 tok/s against 36 with 8, so there the engine's own count stays.  None: the engine's own default (one worker
    per physical core but the host's) stays."""
    if not cores:
        return None
    p, e = cores
    if e <= p:
        return None
    return max(1, p - 1 + e // 2)

def recommend_pool_workers(args: list) -> list:
    """`args` with setup's recommended `--pool-workers` for a hybrid CPU, unless they set one already (a calibration's
    measured count, or the user's own).  A recommendation: the config line can be edited or removed."""
    n = hybrid_pool_workers(cpu_cores())
    if n is None or "--pool-workers" in args:
        return args
    p, e = cpu_cores()
    ok(f"hybrid CPU ({p} performance + {e} efficiency cores): {n} CPU expert workers - the performance cores and half "
       "of the efficiency cores (--pool-workers in the config; START-HERE --calibrate measures it on this PC)")
    return [*args, "--pool-workers", str(n)]

def cpu_sockets():
    """(sockets, physical cores per socket); None when unknown.  Windows: the packages and cores that
    GetLogicalProcessorInformationEx lists (RelationProcessorPackage 3, RelationProcessorCore 0)."""
    try:
        if not WIN:
            return linux_sockets()
        k32 = ctypes.windll.kernel32
        counts = {}
        for rel in (0, 3):
            n = ctypes.c_ulong(0)
            k32.GetLogicalProcessorInformationEx(rel, None, ctypes.byref(n))
            if not n.value:
                return None
            buf = ctypes.create_string_buffer(n.value)
            if not k32.GetLogicalProcessorInformationEx(rel, buf, ctypes.byref(n)):
                return None
            raw, at, c = buf.raw[:n.value], 0, 0
            while at + 8 <= len(raw):
                size = struct.unpack_from("<II", raw, at)[1]
                if size <= 0:
                    break
                c += 1
                at += size
            counts[rel] = c
        return (counts[3], counts[0] // counts[3]) if counts[3] else None
    except Exception:
        return None

def two_socket_note(sockets) -> list[str]:
    """Bench #674 #707 (2-socket Xeons: 17-18 workers beat 35 by ~20%): a tip to keep the expert pool on one socket's
    cores, one fewer for the host loop.  Nothing is written to the config."""
    if not sockets or sockets[0] < 2 or sockets[1] < 3:
        return []
    n = sockets[1] - 1
    return [f"tip: this PC has {sockets[0]} CPU sockets of {sockets[1]} cores. Expert workers on the other socket have "
            f"been measured slower than fewer, local ones (35 vs 17-18 on 2-socket Xeons): try --pool-workers {n} in "
            "the config's args (START-HERE --calibrate measures it on this PC)"]

def gpu_drives_display(g) -> bool:
    """#779: True when nvidia-smi says this card has a display attached (display_active Enabled): its desktop needs
    VRAM too, and a full expert cache beside it has crashed laptops."""
    text = out(["nvidia-smi", "-i", str(g.get("index", 0)), "--query-gpu=display_active", "--format=csv,noheader"])
    return text.strip().lower() == "enabled"

def gpu_compute_mode(index: int) -> str:
    """#1445: nvidia-smi's compute mode for this card ("Default", "Exclusive_Process", "Prohibited", ...); "" when it
    does not say."""
    return out(["nvidia-smi", "-i", str(index), "--query-gpu=compute_mode", "--format=csv,noheader"]).strip()

def compute_mode_warning(index: int, mode: str) -> str | None:
    """#1445: the warning for a card that is not in the Default compute mode, or None.  In Exclusive_Process only one
    process may hold a CUDA context, so the engine, the vision encoder and the tuning run cannot share the card
    ("CUDA-capable device(s) is/are busy or unavailable"); Prohibited allows none.  A warning only: it is the
    administrator's setting, Strata never changes it."""
    if not mode or mode.lower() == "default" or mode.lower().startswith("n/a") or mode.lower().startswith("[n/a"):
        return None
    return (f"GPU {index} is in the compute mode {mode}, not Default: a second process cannot use the card while "
            "the first holds it, so the vision encoder or the tuning run can fail with \"CUDA-capable device(s) is/are "
            f"busy or unavailable\". If it does, set it back with: sudo nvidia-smi -i {index} -c DEFAULT")

def model_file(fam: dict, model: str, i: int) -> str:
    """Shard i's file name: the family's pattern, or the model's own (#621: UD-IQ4_XS has three shards, not four)."""
    return MODELS.get(model, {}).get("file", fam["file"]).format(q=model, i=i)

def model_shards(fam: dict, model: str) -> int:
    return MODELS.get(model, {}).get("shards", fam.get("shards", 2))

REMOTE_EXPERT_OPT = "--remote-expert-opt"

HELPER_CACHE_FLAGS = ("--expert-cache-device1", "--expert-cache-device2", "--expert-cache-device3")

def recommend_remote_expert_opt(cfg: dict, off: bool = False) -> None:
    """0.1.39b (#578): a config on two or more GPUs with a helper cache gets --remote-expert-opt - the helper expert caches
    (--expert-cache-device1..3) then stay complementary to the main GPU's, return their rows already weighted and skip
    the CPU's activation quantization where no expert is left to it (dual RTX 4090: +63% mixed, +132% code over the
    plain helper path).  The engine uses it only with a helper cache; a layer split runs as before.  A recommendation:
    `off` (setup's --no-remote-expert-opt) or "remote_expert_opt": false in the config keeps it out, and a single-GPU
    config is not touched."""
    if not isinstance(cfg.get("gpu"), list) or len(cfg["gpu"]) < 2:
        return
    args = cfg.setdefault("args", [])
    if off or cfg.get("remote_expert_opt") is False:
        if REMOTE_EXPERT_OPT in args:
            args.remove(REMOTE_EXPERT_OPT)
        return
    # #1352: --pipeline-windows (the first card starts the next window) is switched off by --remote-expert-opt (the
    # helper caches), so a config that asks for it keeps its pipeline: one of the two, not both (docs/MULTI_GPU.md)
    pw = args.index("--pipeline-windows") if "--pipeline-windows" in args else -1
    if pw >= 0 and pw + 1 < len(args) and args[pw + 1] != "0":
        if REMOTE_EXPERT_OPT in args:
            warn("--pipeline-windows and --remote-expert-opt are both in this config: the engine turns the pipeline off "
                 "beside the helper caches. Keep one - remove --remote-expert-opt for the pipeline "
                 "(docs/MULTI_GPU.md, #1352)")
        else:
            ok("multi-GPU: --pipeline-windows is set, so --remote-expert-opt is not added (the helper caches turn the "
               "pipeline off; docs/MULTI_GPU.md)")
        return
    # #1447: the flag acts only on the helper caches (--expert-cache-device1..3); without one the engine builds nothing
    # from it, and a plain layer split gained a flag that says "helpers" for no reason. Setup adds it only beside a
    # helper cache; a flag already in the config stays (the user's, or an earlier setup's - harmless).
    if not any(a.split("=", 1)[0] in HELPER_CACHE_FLAGS for a in args):
        return
    if REMOTE_EXPERT_OPT not in args:
        args.append(REMOTE_EXPERT_OPT)
        ok("multi-GPU: --remote-expert-opt (helper expert caches complementary to the main GPU's, #578; "
           "--no-remote-expert-opt leaves it out)")

def resident_budget_gib(model, ram, kv_ram_gb=0.0) -> int:
    """UD-Q4_K_XL: the GiB of experts the engine keeps in RAM (--resident-budget-gib): the RAM (GiB, ram_gb()) less
    24 for the OS, the engine and the file cache the other experts are read through, less a KV cache streamed to
    RAM; at most all of them, at least 8.  64 GB: 40, the measured setting (docs/UNSLOTH_Q4.md)."""
    gib = round(ram) - UNSLOTH_RAM_LEFT_GB - math.ceil(kv_ram_gb)
    return max(8, min(gib, int(MODELS[model]["arena_gb"] / 1.073741824)))

def budget_choice(model, ram, asked) -> float:
    """S4: UD-Q4_K_XL's RAM budget: --resident-budget-gib N as given, else the recommendation (resident_budget_gib).
    More than the recommendation is kept, with what it risks (the owner's rule: setup recommends, it never forces)."""
    rec = resident_budget_gib(model, ram)
    if asked is None:
        return rec
    if asked > rec:
        warn(f"a {asked:g} GiB RAM budget is more than setup recommends for this PC ({rec} GiB: the RAM less "
             f"{UNSLOTH_RAM_LEFT_GB} GB for the OS, the engine and the file cache that reads the other experts). Kept "
             "as you chose: the engine clamps it to the RAM it finds free at start (less 4 GB), and the file cache "
             "gets less room - it may be slower, or run the PC out of RAM under load")
    return int(asked) if asked == int(asked) else asked

LOW_RAM_HEADROOM_GB = 10

RESIDENT_ENGINE = (0, 1, 30)

def low_ram_needed(model, ram) -> bool:
    """The model's experts do not fit this PC's RAM with room left for the rest: they are then mapped from the pack's
    experts.bin instead of copied into RAM (the low-RAM mode)."""
    return ram < MODELS[model]["arena_gb"] + LOW_RAM_HEADROOM_GB

def low_ram_gpu_gb(model, vram_gb, ctx=32768, kv="int8") -> float:
    """About how many GB of the model's experts the GPU's cache holds: its VRAM minus ~5 GB for the dense weights,
    buffers and a 32K context's KV cache, minus the KV cache of a longer context (in VRAM in the low-RAM mode: its RAM
    has no room for KV streaming)."""
    kv_tok = 13 * KV_CELL_BYTES.get(kv, 1056)           # bytes per context token: 12 QSA layers + the draft layer
    longer = max(0, ctx - 32768) * kv_tok / 1e9
    return max(0.0, min(MODELS[model]["arena_gb"], vram_gb - 5 - longer))

def low_ram_gpu_share(model, vram_gb, ctx=32768, kv="int8") -> float:
    """About how much of the model's experts the GPU holds."""
    return low_ram_gpu_gb(model, vram_gb, ctx, kv) / MODELS[model]["arena_gb"]

def low_ram_resident(model, ram, vram_gb, ctx=32768, kv="int8") -> bool:
    """In the low-RAM mode: the experts the GPU does not hold fit the RAM with the usual room beside them, so they are
    copied into RAM once (the resident variant, `--resident-experts`) instead of being read through the OS file cache
    (plain `--mmap-experts`, which a PC this short of RAM keeps re-reading from the SSD)."""
    rest = MODELS[model]["arena_gb"] - low_ram_gpu_gb(model, vram_gb, ctx, kv)
    return ram >= rest + LOW_RAM_HEADROOM_GB

def kv_streaming_ram_gb(ctx, kv) -> float:
    """The RAM a streamed KV cache takes: ~13.7 KB per context token with 8-bit KV (1.7 GB at 128K), 10.6 KB with
    K8V4, 7.5 KB with 4-bit - 12 QSA layers + the draft layer."""
    return ctx * (13 * KV_CELL_BYTES.get(kv, 1056)) / 1e9

def ctx_ram_need(model, ctx, low_ram=False):
    """#406: the RAM (GB) setup estimates for a long context with IQ3_XXS / IQ3_S: their experts + the context's
    8-bit KV cache + 24 GB of room for everything else (the 0.1.29 arithmetic, counted).  None where the context does
    not count against RAM by this rule: the other sizes, and the low-RAM mode (its KV cache stays in VRAM)."""
    if model not in ("IQ3_XXS", "IQ3_S") or low_ram:
        return None
    return MODELS[model]["arena_gb"] + ctx * 13 * 1056 / 1e9 + 24

DRAFT_VOCAB_MIB = {"cjk": 348, "cyrillic": 193, "fr": 151, "en": 133}

SMALL_CARD_GB = 7.5

def small_card_note(ctx: int, draft_vocab: str | None) -> list[str]:
    """#496: what frees VRAM on a card under 8 GB when the start stops with "no VRAM is left for the expert cache"
    (the engine already lowers its own reserve on such a card) - a recommendation, setup changes none of it.  (The
    draft layer stays: the server needs it.)"""
    start = "START-HERE.bat --setup" if WIN else "./setup.sh"
    tips = []
    if ctx > 8192:
        tips.append("an 8K context (a smaller KV cache)")
    if draft_vocab != "en":
        tips.append(f"--draft-vocab en (a draft head of ~{DRAFT_VOCAB_MIB['en']} MiB instead of "
                    f"~{DRAFT_VOCAB_MIB[draft_vocab or 'cjk']})")
    lines = ["If the start stops with \"no VRAM is left for the expert cache\" (the engine's log says how much is "
             "short):"]
    if tips:
        lines.append(f"  run {start} again with " + " and ".join(tips) + ", or close other programs that use the GPU.")
    else:
        lines.append("  close other programs that use the GPU.")
    return lines

PARALLEL_MAX = 8

PARALLEL_SHARE = 0.2

PARALLEL_HELD = 0.5

PARALLEL_COST_NOTE = ("parallel N reduces waiting for several users but costs about 10-25% speed per request on this "
                      "card")

def parallel_slot_gb(ctx: int, kv: str, streaming: bool) -> float:
    """#465: the VRAM one batch slot's session takes: its KV cache (12 QSA layers; with KV streaming only the 32K
    positions the attention reads stay in VRAM) and the DeltaNet state (~0.17 GB).  Measured: 0.56 GiB at 32K int8."""
    kv_tok = 12 * (576 if kv == "q4_0" else 1056)
    return (min(ctx, 32768) if streaming else ctx) * kv_tok / 1e9 + 0.17

def parallel_recommend(vram_gbs, arena_gb: float, ctx: int, kv: str, streaming: bool) -> int:
    """#465: how many requests at once ("parallel") to recommend: 0 = none (one at a time).  Only where the experts
    mostly fit in VRAM - the expert cache (each card's VRAM less ~5 GB, every card of a layer split) still holds
    PARALLEL_HELD of the model's experts beside the slots' sessions, which take at most PARALLEL_SHARE of it, up to 4.
    Where the experts mostly run on the CPU a batch reads about as many experts as the requests one by one and every
    slot's VRAM is expert cache lost: measured on a 12 GB RTX 5070 (Q2_0, 32K), a request alone 11-24% slower with 2-4
    slots, 4 requests together 63 tok/s against 71 one after the other (docs/BATCHING.md)."""
    if isinstance(vram_gbs, (int, float)):
        vram_gbs = [vram_gbs]
    cache_gb = sum(max(0.0, v - 5) for v in vram_gbs)
    slot = parallel_slot_gb(ctx, kv, streaming)
    best = 0
    for n in (2, 3, 4):
        if n * slot <= PARALLEL_SHARE * cache_gb and (cache_gb - n * slot) >= PARALLEL_HELD * arena_gb:
            best = n
    return best

def parallel_note(asked: int | None, vram_gbs, arena_gb: float, ctx: int, kv: str, streaming: bool) -> list[str]:
    """#465: what setup says about "parallel": the recommendation (or, where it would cost speed, why it is left at
    one), or how the asked count compares with it (kept as asked: recommend, never force)."""
    rec = parallel_recommend(vram_gbs, arena_gb, ctx, kv, streaming)
    slot = parallel_slot_gb(ctx, kv, streaming)
    if asked is None or asked <= 1:
        if not rec:
            return [f"Several requests at once: left at one at a time - {PARALLEL_COST_NOTE} (docs/BATCHING.md)."]
        return [f"Several requests at once (opt-in): --parallel {rec} decodes up to {rec} together instead of one "
                f"after the other (each takes ~{slot:.1f} GB of VRAM from the expert cache; docs/BATCHING.md)."]
    lines = [f"parallel requests: {asked} at once (each takes ~{slot:.1f} GB of VRAM from the expert cache, "
             f"{asked * slot:.1f} GB in all)"]
    if asked > PARALLEL_MAX:
        lines.append(f"the engine runs at most {PARALLEL_MAX} at once; it will use {PARALLEL_MAX}")
    if not rec:
        lines.append(f"recommended for this card: one at a time - {PARALLEL_COST_NOTE}; kept as you chose")
    elif asked > rec:
        lines.append(f"recommended for this card: {rec} - more slots leave fewer experts in VRAM, which can make every "
                     "request slower; kept as you chose")
    return lines

PREFILL_BIG_RAM_GB = 96

PREFILL_RISK_RAM_GB = 64

HEADROOM_RAM_GB = 48

AGENT_CACHE_FREE_GB = 24

AGENT_CACHE_MIB = 8192

SMALL_VISION_VRAM_GB = 12.5

def arg_after(args, flag):
    """The value after `flag` in an argument list, or None."""
    return args[args.index(flag) + 1] if flag in args[:-1] else None

def bench_tips(args, env, ram: float, model_ram_gb: float, vram_gb: float, vision: str, win: bool) -> list[str]:
    """Recommendations from the community bench data (plan 0.1.40 item 14).  Text only: nothing here changes a
    default, the config or the engine's arguments (recommend, never force).  `ram` is this PC's RAM, `model_ram_gb`
    what the chosen model keeps in it."""
    tips = []
    cache = arg_after(args, "--expert-cache")
    if win and cache is not None and cache != "auto":
        tips.append(f"warning: --expert-cache {cache} is a fixed size. On Windows, a size that leaves almost no VRAM free "
                    "has run up to 7x slower (#780 #781); a smaller number, or auto, leaves the driver room")
    prefill = arg_after(args, "--prefill")
    if prefill == "auto:32768" and ram < PREFILL_RISK_RAM_GB:
        tips.append(f"warning: --prefill auto:32768 on {ram:.0f} GB of RAM: it ran ~3x slower than --prefill auto with "
                    "32 GB (#834 #669); it paid off (+21-35%) with 96 GB")
    elif prefill == "auto" and ram >= PREFILL_BIG_RAM_GB:
        tips.append(f"tip: with {ram:.0f} GB of RAM, --prefill auto:32768 in the config's args read prompts 21-35% "
                    "faster in community benchmarks (#433 #440 #834); not set, nothing changes")
    resident = any(a in args for a in ("--resident-experts", "--resident-budget-gib"))
    if resident and ram <= HEADROOM_RAM_GB and "STRATA_RESIDENT_HEADROOM_GIB" not in (env or {}):
        tips.append(f"tip: on a PC with {ram:.0f} GB of RAM, \"env\": {{\"STRATA_RESIDENT_HEADROOM_GIB\": \"6\"}} in the "
                    "config kept decode speed in a community benchmark and left the system 2 GiB more (#834); the "
                    "default is 4")
    if "--conversation-cache-mib" not in args and ram - model_ram_gb >= AGENT_CACHE_FREE_GB:
        tips.append(f"tip: for several agents or clients at once, --conversation-cache-mib {AGENT_CACHE_MIB} in the "
                    "config's args keeps each one's conversation; without it they were measured re-reading ~90% of "
                    "their prompts (#882 #440; docs/DETAILS.md, Multiple conversations)")
    if vision == "gpu" and 0 < vram_gb <= SMALL_VISION_VRAM_GB:
        tips.append("tip: the image encoder on the GPU makes a prompt's chunks smaller on a card this size (243 vs 750 "
                    "tok/s measured, #469); run setup again with --vision cpu to read prompts ~3x faster, at about "
                    "2-3 s per picture")
    return tips

DISPLAY_RESERVE_MIB = 1500

DESKTOP_RESERVE_MIB = 3072

def desktop_reserve_note() -> list[str]:
    """#560 #516: an AMD card that also drives a Linux desktop - with the default 700 MiB reserve the expert cache
    fills it, and when the desktop needs more VRAM amdgpu moves the cache to system RAM, where the OOM killer then ends
    the compositor.  A recommendation, setup changes nothing."""
    return [f"If this AMD card also drives your desktop and the desktop or apps crash once the model is loaded, keep "
            f"more VRAM free: ./setup.sh --vram-reserve-mib {DESKTOP_RESERVE_MIB}",
            "  (remembered for this model; the expert cache gets ~2.3 GB less, a few % of speed)"]

def derived_factor(ctx: int, trained: int = 262144) -> float:
    """The automatic extension factor: the FINAL context over the trained one, at least 1.

    Factor 1 removes the automatic expansion - the trained angles stand as they are - but it is not a
    switch for rope as a whole: an explicitly chosen method's settings keep their defined behavior.
    """
    return max(1.0, float(ctx) / float(trained))

def resolve_rope(ctx: int, scaling, scale, trained: int = 262144):
    """The rope config for the context ACTUALLY SERVED: (scaling, scale); scaling None = no scaling flags.

    An explicit --rope-scaling/--rope-scale always wins - a user-supplied factor is kept verbatim even
    when a reduction changed the context.  Past the trained range an omitted method defaults to yarn -
    llama.cpp's extension method: the trained angles survive on the high-frequency pairs and the
    magnitude correction keeps the attention temperature - and an omitted factor is derived from the
    final context (final / trained, at least 1), as is an explicitly chosen method's missing factor
    inside the trained range: factor 1, the trained angles, no expansion.  An explicit none is refused
    past the trained range (the setup will not configure a run it knows is out of spec) rather than
    silently overridden.
    """
    if ctx <= trained:
        if scale is not None and scaling in (None, "none"):
            raise ValueError("--rope-scale needs --rope-scaling linear or yarn (the chosen context fits the "
                             "trained 262144, so there is nothing to scale)")
        if scaling in (None, "none"):
            return None, None          # the stock model, by choice or by default
        return scaling, scale if scale is not None else derived_factor(ctx, trained)
    if scaling == "none":
        raise ValueError(f"a {ctx // 1024}K context is past the model's trained 262144, and --rope-scaling none "
                         "keeps the stock angles there - the model has never seen those positions, so the setup "
                         "refuses the combination instead of quietly overriding it. Pick --rope-scaling yarn or "
                         "linear, or rerun with --context 262144 or lower")
    return scaling or "yarn", scale if scale is not None else derived_factor(ctx, trained)

def main() -> int:
    need = min(d["ram_gb"] for d in MODELS.values())
    if MODELS[model].get("budget"):
        # Unsloth's UD-Q4_K_XL: a RAM budget of experts, the rest from the GGUF on the SSD - not the low-RAM mode (no
        # experts.bin: it would be another 77 GB on the disk), and one GPU (the budget mode has no layer split) unless
        # the RAM holds the GGUFs and 24 GB more: then several, without the budget, if asked for (#498)
        if MODELS[model].get("experimental"):
            warn(f"{model} is EXPERIMENTAL (docs/UNSLOTH_Q4.md): most of its experts are read from the SSD while it "
                 "answers, so it is several times slower than the 2-3-bit models; quality checked against llama.cpp")
        if hip and MODELS[model].get("nvidia_only"):
            # #429 (jkuepker): checked before the 111 GB download.  The HIP engine has no prompt kernels for its
            # Q4_K / Q5_K experts (STRATA_MMQ_KQUANTS is CUDA-only) and it has not been run on AMD: asked, not refused
            confirm_risk(f"{model} has not been run on AMD cards yet: its prompt kernels are NVIDIA-only, so on "
                         f"{gpu_name(gpu)} long prompts read much more slowly, and it may not work at all",
                         bool(a.model), a.yes, f"{model} is NVIDIA-only so far", "choose one of the 2-3-bit models, "
                         f"or --model {model} --yes to try it on AMD anyway", "  Try it anyway?")
            warn(f"installing {model} on an AMD card, as you chose (please report how it runs)")
        if ram < MODELS[model]["ram_gb"]:
            confirm_risk(f"{model} needs {MODELS[model]['ram_gb']} GB of RAM or more; this PC has {ram:.0f} GB: "
                         f"its RAM budget would be {resident_budget_gib(model, ram)} GiB, so nearly every expert is "
                         "read from the SSD while it answers (very slow), and it may run out of RAM",
                         bool(a.model), a.yes, f"{model} needs {MODELS[model]['ram_gb']} GB of RAM or more; this PC "
                         f"has {ram:.0f} GB", f"choose one of the 2-3-bit models, or --model {model} --yes to "
                         "install it anyway", "  Install it anyway?")
            warn(f"installing {model} with {ram:.0f} GB of RAM, as you chose")
        budget = budget_choice(model, ram, a.resident_budget_gib)
        if multi and not unsloth_together(a, model, ram, gpu, chosen):
            multi, sel, chosen = [], [gpu["index"]], [gpu]
        q4_split = bool(multi)                         # #498: on several GPUs without the RAM budget
        if not q4_split:
            ok(f"RAM budget: {budget:g} GiB of {model}'s experts in RAM, the rest read from the model files on the SSD")
        if a.low_ram not in ("auto", "off"):
            warn(f"--low-ram {a.low_ram} does not apply to {model}: it always reads part of its experts from the files")
    elif a.resident_budget_gib is not None:
        warn(f"--resident-budget-gib is for UD-Q4_K_XL and UD-IQ4_XS: {model} keeps all of its experts in RAM or in "
             "the low-RAM mode")
    q2_avx = model == "Q2_0" and avx512 and family == "qwen"
    need = to_fetch + (2 if mtp_have else 8) + \
        (40 if q2_avx and not pack_bin else 0) + (1 if vision != "none" else 0) + \
        (MODELS[model]["arena_gb"] + 1 if low_ram and not q2_avx and not pack_bin else 0)
    args = ["--pack", str(pack), "--native", str(shards[0]), *(["--ple-gguf", str(ple)] if len(shards) <= 2 else []),
            "--expert-profile", str(ROOT / "data" / fam.get("profile", "expert-profile.bin")), "--expert-cache", "auto",
            "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5", "--mtp", str(rt),
            "--max-context", str(ctx)]
    if scaling is not None:     # the resolved config: explicit flags as given, or the automatic yarn+factor
        args += ["--rope-scaling", scaling, "--rope-scale", f"{rope_scale:g}"]
    if ctx > 8192:
        args += ["--kv", kv]
    if resident and a.low_ram != "resident" and engine_ver < RESIDENT_ENGINE:
        resident = False                               # an engine from before --resident-experts would refuse it
        ok(f"low-RAM mode: engine {meta.get('version')} has no resident variant yet; the experts are read through "
           "the OS file cache (run setup again after the next engine update)")
    if low_ram:   # the experts from the pack's experts.bin: the ones the GPU does not hold copied into RAM, or mapped
        args += ["--resident-experts" if resident else "--mmap-experts"]
    disk = None if is_wsl() else rotational_disk(ple)  # #605 (WSL's virtual disk says rotational)
    if disk:
        tensor = next((t for t in GGUFFile(ple).tensors if t.name == "per_layer_token_embd.weight"), None)
        size = getattr(tensor, "expected_bytes", lambda: None)()
        table_gb = size / 1e9 if size else 28.8
        if ram >= MODELS[model]["ram_gb"] + table_gb + 4:
            args += ["--ple-io", "ram"]
            ok(f"the model is on a rotational disk ({disk}): its {table_gb:.0f} GB n-gram table is kept in RAM "
               "(--ple-io ram) - read from the disk at random, it can stall prompts for minutes (#605)")
        else:
            warn(f"the model is on a rotational disk ({disk}): its n-gram table is read from it at random, which can "
                 f"stall prompts for minutes (#605). An SSD is recommended; with ~{table_gb:.0f} GB more RAM, "
                 "--ple-io ram in the config's args keeps the table in RAM instead")
    kv_ram_gb = kv_streaming_ram_gb(ctx, kv)      # the branches below are kv_streaming_wanted, with its messages
    stream_fits = ram >= MODELS[model]["ram_gb"] + kv_ram_gb + 1
    if is_wsl() and ctx >= 65536:
        ok("WSL: KV streaming off (the driver pins only about 1 GB of RAM); the KV cache stays in VRAM")
        if a.kv_streaming == "on":
            warn("--kv-streaming on: WSL cannot stream the KV cache (its RAM copy must be pinned, and the driver pins "
                 "only about 1 GB there): off")
    elif ctx >= 65536 and a.kv_streaming == "off":
        ok("KV streaming off, as you chose (--kv-streaming off): the KV cache stays in VRAM")
    elif ctx >= 65536 and (stream_fits or a.kv_streaming == "on"):
        args += ["--kv-resident", "32768"]
        ok(f"KV streaming on: the context's KV cache lives in RAM ({kv_ram_gb:.1f} GB), more experts fit in VRAM")
        if not stream_fits:
            warn(f"KV streaming needs ~{kv_ram_gb:.1f} GB of RAM beside the ~{MODELS[model]['ram_gb']} GB {model} "
                 f"uses; this PC has {ram:.0f}. Kept as you chose (--kv-streaming on): it may page or run out of RAM "
                 "under load")
        if q4_split:                                   # #498: no budget to take it out of
            pass
        elif budget is not None and a.resident_budget_gib is None:   # its RAM comes out of the experts' budget
            budget = resident_budget_gib(model, ram, kv_ram_gb)
            ok(f"RAM budget: {budget} GiB (less the KV cache's RAM)")
        elif budget is not None and budget > resident_budget_gib(model, ram, kv_ram_gb):
            warn(f"the KV cache's {kv_ram_gb:.1f} GB of RAM come on top of your {budget:g} GiB RAM budget (setup "
                 f"would take them out of it: {resident_budget_gib(model, ram, kv_ram_gb)} GiB); kept as you chose")
    elif ctx >= 65536:   # #620: say why, so a regenerated config that lost --kv-resident is not a surprise
        ok(f"KV streaming off: it needs ~{kv_ram_gb:.1f} GB of RAM beside the ~{MODELS[model]['ram_gb']} GB {model} "
           f"uses, and this PC has {ram:.0f}; the KV cache stays in VRAM (fewer cached experts). --kv-streaming on "
           "turns it on anyway")
    elif a.kv_streaming == "on":
        warn("--kv-streaming on: a context under 64K is not streamed (the attention's window holds all of it): off")
    if budget is not None and not q4_split:   # UD-Q4_K_XL: the experts read from the GGUF in place, the most-used N
        args += ["--resident-budget-gib", f"{budget:g}"]   # GiB kept in RAM (#498: a layer split has no budget)
    if vision != "none":
        args += ["--vision", "--vram-reserve-mib", str(VISION[vision]["reserve_mib"])]
        if vision == "gpu" and a.vram_reserve_mib is None and 0 < gpu.get("vram_gb", 0.0) <= 12.5:
            # a tip only (recommend, never force): on a 12 GB card the encoder's 700 MiB can leave ~200 MiB free
            print(f"  tip: images on a {gpu['vram_gb']:.0f} GB card can leave little VRAM free; if a request stalls, "
                  f"run setup again with --vram-reserve-mib {VISION_GPU_SMALL_RESERVE_MIB}")
    if a.vram_reserve_mib is not None:                 # #493: VRAM left free for other programs (only when given)
        if "--vram-reserve-mib" in args:
            i = args.index("--vram-reserve-mib") + 1
            if vision == "gpu" and a.vram_reserve_mib < int(args[i]):
                warn(f"--vram-reserve-mib {a.vram_reserve_mib}: the image encoder on the GPU needs ~{args[i]} MiB of "
                     "it; kept as you chose (it may run out of VRAM when it reads a picture)")
            args[i] = str(a.vram_reserve_mib)
        else:
            args += ["--vram-reserve-mib", str(a.vram_reserve_mib)]
        ok(f"VRAM kept free for other programs: {a.vram_reserve_mib} MiB (--vram-reserve-mib; the expert cache takes "
           "that much less)")
    if not multi and 0 < gpu.get("vram_gb", 0.0) < SMALL_CARD_GB:
        # #496: on a 6 GB card the expert cache can get no room at all; the engine lowers its own reserve when that
        # is what it takes, and says what is short when even that is not enough.  Setup only says what helps.
        for line in small_card_note(ctx, draft_vocab):   # a recommendation: nothing changes
            say("  " + line)
    elif hip and a.vram_reserve_mib is None and linux_desktop():
        for line in desktop_reserve_note():              # #560 #516: a recommendation: nothing changes
            say("  " + line)
    if not hip and not multi and a.vram_reserve_mib is None and gpu_drives_display(gpu):
        say("  tip: this card drives a display. If the PC freezes or the screen goes black once the model is loaded "
            f"(#779), keep more VRAM free: run setup again with --vram-reserve-mib {DISPLAY_RESERVE_MIB}")   # a tip only
    if not hip:
        for gi in ([g for g in multi] if multi else [gpu.get("index", 0)]):
            gi = gi["index"] if isinstance(gi, dict) else gi
            w = compute_mode_warning(gi, gpu_compute_mode(gi))
            if w:
                warn(w)                                   # #1445: a warning only, never a refusal
    if esp is not None:
        # the package's profile, with llama.cpp's flags (the engine takes the same ones)
        args += ["--control-vector-scaled", f"{esp}:1.0", "--control-vector-layer-range", "4", "44",
                 "--cvec-mode", "project", "--cvec-dir", "per-layer"]
    cfg = {"exe": str(eng / EXE), "args": args, "cwd": str(ROOT), "tokenizer": str(pack / "tokenizer"),
           "model_name": f"{fam['name']}-{model.lower()}", "log": str(ROOT / f"strata-{tag.lower()}.log"),
           "lib_dirs": lib_dirs, "port": port}
    if cuda_tk == 12:                                  # the experimental CUDA 12 engine (engine-cuda12/)
        cfg["cuda"] = 12
    if hip:
        cfg["backend"] = "hip"
        # the dense prompt GEMMs through hipBLASLt with kernels measured on this GPU generation (tools/hip; +40-60%
        # prompt speed on the 7900 XTX): only a table for this card's arch AND the installed hipBLASLt version (the
        # engine refuses any other one and falls back to plain hipBLAS)
        table = hipblaslt_table(gpu["arch"], lib_dirs, meta.get("hipblaslt_version"))
        if table:
            cfg["env"] = {"STRATA_HIPBLASLT_TUNING": str(table)}
        if GFX1103_OPT_IN and gfx_arch_is(gpu["arch"], "gfx1103") and not WIN:
            # the 780M's KFD queues are evicted (a GPU reset) while transparent huge pages move the pinned expert arena
            cfg.setdefault("env", {})["STRATA_NO_ARENA_THP"] = "1"
        if resident:   # ROCm: large page-locked host allocations can fail or be slow for the CPU; keep the copy pageable
            cfg.setdefault("env", {})["STRATA_RESIDENT_PIN"] = "0"
    if gpu["count"] > 1 or a.gpu is not None:
        cfg["gpu"] = gpu["index"]                      # the engine is told this card (issue #51)
        cfg["gpus_asked"] = True                       # chosen at setup: not asked again at start
    if multi:                                          # a layer split across these cards (the server adds the flag)
        cfg["gpu"] = multi
        cfg["layer_split"] = a.layer_split or "auto"
        ok(f"layer split across GPUs {multi} ({cfg['layer_split']})")
        recommend_remote_expert_opt(cfg, off=a.no_remote_expert_opt)
    if a.host:
        cfg["host"] = a.host
    if a.api_key:
        cfg["api_key"] = a.api_key
    if draft_vocab:
        cfg["draft_vocab"] = draft_vocab
    if a.browser is not None:                          # #609: only when given (else an earlier choice is carried over)
        cfg["open_browser"] = a.browser
    streaming = "--kv-resident" in args
    if a.parallel is not None:
        if a.parallel >= 2:
            cfg["parallel"] = a.parallel
            for i, line in enumerate(parallel_note(a.parallel, [g.get("vram_gb", 0.0) for g in chosen],
                                                   MODELS[model]["arena_gb"], ctx, kv, streaming)):
                (ok if i == 0 else warn)(line)
        else:
            cfg["parallel"] = 1
            ok("parallel requests: one at a time (--parallel 1)")
    if vision != "none":
        old_cfg = ROOT / f"strata-{tag.lower()}.json"
        vt = vision_tokens(a.vision_tokens, vision, old_cfg if old_cfg.is_file() else adopted)
        cfg["vision"] = {"exe": str(eng / VEXE), "mmproj": str(mmproj), "model": str(shards[0]),
                         "gpu": vision == "gpu", "max_tokens": vt}
        if vision == "cpu":
            cfg["vision"]["threads"] = max(1, (os.cpu_count() or 8) // 2)
    elif a.vision_tokens is not None:
        warn("--vision-tokens: images are off for this model, so it is not used")
    cfg_path = ROOT / f"strata-{tag.lower()}.json"
    cal = setup_calibration(cfg, hip)                  # #566: Linux HIP too; the tuning is offered on NVIDIA only
    if cal is not None:
        sys.path.insert(0, str(ROOT / "tools"))
        import calibrate as CAL
        cfg["args"] = CAL.apply(cfg["args"], cal.get("settings") or {})
        ok("the settings tuned for this PC earlier are used" + (f" ({cal['date']})" if cal.get("date") else ""))
    else:                                              # #642: measured counts (a calibration) win over the rule
        cfg["args"] = recommend_pool_workers(cfg["args"])
        for line in two_socket_note(cpu_sockets()):    # bench tips: text only, the config is not touched
            say("  " + line)

