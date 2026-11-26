# Stock Niko1221/Strata v0.2.22 terminal/setup.py (planner inputs and complete main excerpt); read as data only.
# Source SHA-256: d4c4eb8e68bea535fd77dd6daea7a7929e3cc05d392f266d15d7d7425e901768
# Payload SHA-256: 84dd71173a962c1c5249bfd158be5b84deb2b38db81d8ad76a3df8adcf127f97
# Stock payload follows.
def home() -> Path:
    """Where an install writes (see above). A function, not a constant, so ROOT stays the one thing a caller can point elsewhere."""
    return _CONTROL_HOME or ROOT

HF_REVISIONS = {
    "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF": "ed59f92082b1e93c0e96d60a8b11aab089b52f09",        # 2026-09-29
    "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF": "99bb8f7f95c7aa7b24a36a7786a4f657b30f5d3d",   # 2026-10-07 (adds IQ3_S)
    "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF": "bba88856f8c3c0c9e40e45f82d05e228b814ac43",  # 2026-10-19 (the new expert-pruned shard 1)
    "unsloth/Qwen3.8-Flash-Next-GGUF": "38bb39ee97821de2c9009abb7e93950eec396e66",                   # 2026-09-30
    "unsloth/Qwen3.6-35B-A3B-MTP-GGUF": "5bc3e238d916f48a861bac2f8a1990a0e9b7e98d",                  # 2026-10-12
    "agentionai/Qwen3.8-Flash-Next-Gyro-GGUF": "1ada08422e404aca51ab9df665f089f34c419c6b",           # 2026-10-13
}

def model_alias(name: str) -> str:
    """A --model name as setup keeps it (the DeepSeek sets' second spellings were the only aliases; DeepSeek is no longer offered)."""
    return name

LLAMA_CPP_COMMIT = "3cf03257f219afbe7334045ff7c6a06ac68c627d"

CUDA_WHEELS = ["nvidia-cublas==13.0.2.14", "nvidia-cuda-runtime==13.0.96"]

MIN_DRIVER = 580                       # CUDA 13.0

MIN_ENGINE = (0, 1, 46)                # versions compare all numbers; v0.1.60: engine changes since v0.2.13.1 (git log 628f74955..HEAD); v0.1.59: engine changes since v0.2.12 (git log 146df3c46..HEAD); v0.1.58: engine rounds 0215-0217 (tuned drafters, the file-tier re-check, prefill and Q5_0 fixes; git log c3b3f5035..HEAD); v0.1.46: the 0.2 release engine (UPDATE.bat and setup fetch it from the signed feed, #3469 #3437); v0.1.45: Qwen3.6 parallel requests and pictures, fixes #2346 #2372 #2396; v0.1.44.1: CPUs without AVX2 start again (#2324: an illegal instruction before main in the NVFP4 CPU rows), the CUDA 12.0/12.1 toolkits build (#2322), a crashed engine start is named instead of retried as a GPU runtime start, Mac M2 (#2323); v0.1.44: UD-Q4/Q5/Q6_K_XL and Q8_0 Unsloth files in setup (K-quant experts, MMQ prompt library strata_kq), NVFP4 packs, Qwen3.6-35B-A3B, Intel Arc A-series kernels, the pipelined-decode and latency work; v0.1.43.1: the adaptive overlap no longer collapses decode on pinned-host desktops (#1964 #1975), Windows PLE mmap stall (#1984), pinned prompt uploads (#1996), the I/O watchdog allowance; v0.1.43: adaptive-tier copies overlap on CUDA, P100 (sm_60) kernel tables, RDNA4 (gfx1200/gfx1201) defaults (route tail skip, measured PCIe share, 16K prompt chunks, fused IQ3 prompt experts); v0.1.42.1: the GGUF-in-place file tier on Windows unmaps every shard, dual-socket starts judge each NUMA node and STRATA_DROP_CACHE_ON_EXIT, tools/strata_bench.py; v0.1.42: STRATA_ROUTE_TAIL_SKIP=7 default on CUDA (+13-16% decode), the AMD 2-GPU checkpoint fix (H13), Phase 2 fixes and opt-ins; v0.1.41.1 (folded into 0.1.42): the #1576 card order, #1616 stage size, #1595 CPU share, #1630/#1607 Windows HIP chunk cap and commit-limit warning, #1603 parallel-request bookkeeping; v0.1.41: CPU prefill share on by default (NVIDIA, chunks < 1024), --batch-groups auto, the file tier read in batches on Windows, Pascal decode fix, per-arch tables; v0.1.40.3: the #1357 MTP router guard, the #1376 Windows HIP cache floor, #461 runtime DLLs, Intel A750 first-request fix; v0.1.40.2: F4 verify windows, the Linux file tier (#1194), the stager wait (#1057), #1264/#1201/#1139 fixes, opt-in CPU share (#1282), Intel Arc; v0.1.40: --resident-experts on a layer split with the split+resident variant (#848), --kv k8v4 with KV streaming (#711); v0.1.39: the #577 file-tier regression fixed, the OpenAI Responses API (#451, Codex), a reply stuck on one token ended (#606), the head before the arena (#620), effort_position (#458), --vram-reserve hot resize opt-in (#533), PR batch; v0.1.38: prompts faster (one gather per expert group #372, the first chunk's PLE rows beside layer 0 #374, DeltaNet three heads per thread #413), --kv q4_0 prompts on tensor cores (#452), Q5_0 experts on the GPU (#473), IQ4_XS on AVX-2 (#415), unbuffered expert loading on Windows (#357 #362), --peer-device (#531), a 6 GB card starts (#496), PR batch; v0.1.37: a silent engine is restarted (#481), Windows AMD counts the desktop's VRAM (#380 #377 #497), a steadier PCIe probe (#485), fixes #496 #495 #498 #505 #493; v0.1.36: a cancelled prompt logged as read so far (#471), the draft-head hint (#474), UPDATE.bat (#475), --expert-profile-save (#477); v0.1.35: Windows AMD uses its bundled HIP runtime (#468 #461), the low-RAM resident mode on Windows 32 GB (#467), fixes #460 #459 #446 #447 #457 #448 #444; v0.1.34: AMD on Windows (a ready-made HIP engine), an MCP server for AI assistants (tools/strata_mcp.py), a shorter README; v0.1.33: a portable image encoder again (#411 #412), setup recommends instead of forcing (#406 #403 #364 #384), fixes #352 #365 #369 #371 #375 #393 #408 #414; v0.1.32: split prompts faster (#340), AMD router +12%, Unsloth Q4 in setup, faster Q4 prompts, #326/#327/#342/#344 fixes, PR batch; v0.1.31: Unsloth UD-Q4_K_XL (experimental), GGUF-in-place low-RAM mode, Windows GGUF load 2x, server race + tokenizer fixes, AMD intrinsics; v0.1.30: short prompts faster (streaming from 1024 tokens), resident low-RAM variant, multi-GPU session carve, RDNA4; v0.1.29: sampled answers faster (split top-k), #154 correctness fixes; v0.1.28: the expert cache reserves the draft head, a cancelled request no longer fails the next; v0.1.27: RTX 20 (sm_75) in the ready-made engine, the HIP build without CUDA headers; v0.1.26: the draft layer's prompt pass in batches; v0.1.25: faster prompts (grouping off the copy engine, fused hyper-connection kernels), AMD HIP backend, --kv k8v4; v0.1.24: long prompts faster (QSA select on tensor cores); v0.1.23: image requests honor sampling, 8 GB cards start, batched verify window; v0.1.22: faster prompts (tensor-core attention), multi-GPU across images/steering/KV streaming; v0.1.21: multi-GPU layer split (--gpus); v0.1.20: system-prompt checkpoint, PCIe probe, hit rate; v0.1.19: penalties

KV_CELL_BYTES = {"q4_0": 576, "k8v4": 816}

PY_PACKAGES = ["numpy", "jinja2", "regex", "pyyaml", "tqdm", "requests", "pillow", "psutil"]

NVFP4_GPTQ_REPO = "Maximilian228/Qwen3.8-Flash-Next-NVFP4-GPTQ-Strata"     # Qwen's BF16 experts by GPTQ (the fork)

NVFP4_NVIDIA_REPO = "Maximilian228/Qwen3.8-Flash-Next-NVIDIA-NVFP4-Strata"  # nvidia/Qwen3.8-Flash-Next-NVFP4, converted

NVFP4_FP4LOCAL_REPO = "nvidia/Qwen3.8-Flash-Next-FP4-Local"   # NVIDIA's QAD checkpoint (ModelOpt safetensors), prepared here

NVFP4_ENGINE = (0, 1, 44)

FP4LOCAL_ENGINE = (0, 1, 45)

GYRO_ENGINE = (0, 1, 45, 1)

GYRO_FILES = {
    "Qwen3.8-Flash-Next-Gyro-S-TQ1_0.gguf":
        (58487015808, "c6ea1b08ca312f99095b27588ba35976b53f948268e7f91e7761926aa01d9c87"),
    "Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf":
        (91965774272, "7aa36d15131d255179ab6c87fa9c9f81a0b541fc9e81e959d4c3e29eb20feb5f"),
}

CODER_FILES = {
    "Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf":
        (29608446496, "bfa3644db4adfff072fc946c20994f2909d2cf89879d83f80a4c811d4016c211"),
    "Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf":
        (28800138432, "316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113"),
    "mmproj-Qwen3.8-Flash-Next-BF16.gguf":
        (907543008, "b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0"),
}

UNSLOTH_V31_REVISION = "d96201194f103c906994f283f504209dc8d2a10c"          # 2026-11-04

UNSLOTH_V31_IQ4_XS = "UD-IQ4_XS-v31"      # the catalog name of the new UD-IQ4_XS (its files on the Hub have the pinned one's names, with four shards instead of three)

UNSLOTH_V31_ENGINE = (0, 1, 57)       # the engine that ships with these sets (i-quant experts with Q2_0 / IQ4_NL / Q5_0 downs, a Q6_K dense side)

MODELS = {
    # the original model only for now: Swift 1.5's Q2_0 files split one layer's experts across the two shards, which
    # the pack tool (tools/iq_pack.py) cannot prepare yet (#171)
    "Q2_0": {"about": "2-bit, the fastest", "download_gb": 66.4, "ram_gb": 48, "arena_gb": 34.0, "families": ("qwen",)},
    "IQ2_XS": {"about": "2-bit i-quant, a little better quality, close in speed", "download_gb": 68.0, "ram_gb": 48,
               "arena_gb": 35.5},
    "IQ3_XXS": {"about": "3-bit i-quant, better quality, slower (more CPU work per token)", "download_gb": 75.8,
                "ram_gb": 60, "arena_gb": 42.9},
    # matches the full BF16 model on the published benchmarks; Swift 1.5 got an IQ3_S tier of its own (#1651)
    "IQ3_S": {"about": "3.5-bit i-quant, the best quality (matches the full model), the slowest; needs a 64 GB PC "
                       "with little else running", "download_gb": 83.6, "ram_gb": 62, "arena_gb": 50.3},
    # the Coder release: 256 of the 512 experts kept (the ones code, tools and vision use), IQ2_S-IQ4_XS like IQ3_S
    "IQ1_M": {"about": "the Coder's only size: half the experts, stored like IQ3_S (3.5 bits)", "download_gb": 58.4,
              "ram_gb": 32, "arena_gb": 23.4, "families": ("coder",)},
    # #621: Unsloth's UD-IQ4_XS - IQ3_S gate/up experts with IQ4_NL (43 layers) or Q8_0 (5) downs, the dense side as
    # UD-Q4_K_XL's; three shards.  A regular choice from 0.1.39 (no longer experimental).  Its 59.5 GB of experts: a
    # RAM budget of them, like UD-Q4_K_XL, but far fewer read from the SSD on a 64 GB PC and none from ~80 GB of RAM.
    # Images: the vision path has no restriction for this pack (the same base model and image encoder), so setup asks
    "UD-IQ4_XS": {"about": "~4-bit i-quant (Unsloth Dynamic), between IQ3_S and UD-Q4_K_XL in quality; on a PC with "
                           "less than ~80 GB of RAM part of its experts are read from the SSD",
                  "download_gb": 93.7, "ram_gb": 48, "arena_gb": 59.5, "families": ("unsloth",), "budget": True,
                  "shards": 3, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00003.gguf", "engine": (0, 1, 38),
                  "vision": True},
    # Unsloth's 4-bit file (docs/UNSLOTH_Q4.md); experimental until MODEL-UPDATE Phase 2.  Its 77 GB of experts stay in
    # RAM from ~94 GB of RAM (unsloth_budget); on a 64 GB PC the engine keeps a RAM budget of them
    # (--resident-budget-gib, chosen below) and reads the rest from the GGUF on the SSD.  It runs on AMD too (R9700:
    # the quality yardstick and the decode/prompt numbers in docs/QUANTS.md), so it is no longer NVIDIA-only (#429).
    "UD-Q4_K_XL": {"about": "4-bit (Unsloth Dynamic): K-quant experts, between UD-IQ4_XS and UD-Q5_K_XL in quality",
                   "download_gb": 111.3, "ram_gb": 48, "arena_gb": 77.0, "families": ("unsloth",), "budget": True,
                   # #967 / MODEL-UPDATE: images run end to end with this file (CUDA: RTX A4000, GPU encoder; HIP:
                   # R9700, CPU encoder; the test picture's text and shapes as the IQ3_XXS pack answers them)
                   "vision": True},
    # MODEL-UPDATE: Unsloth's larger files (docs/QUANTS.md).  The same GGUF-in-place mode: every expert in RAM where it
    # fits with UNSLOTH_RESIDENT_BESIDE_GB more (unsloth_budget), else a RAM budget of them and the rest read from the
    # SSD while it answers - so "ram_gb" is the all-in-RAM need, and below it setup asks first (default no).  Their
    # shards 2 (the head) and 3 (the 54 GB Q8_0 PLE table) are the same bytes in all three files.  UD-Q5_K_XL and
    # UD-Q6_K_XL need the Q6_K expert kernels every engine has from MODEL-UPDATE Phase 1 on (Q5: layer 2's gate/up).
    "UD-Q5_K_XL": {"about": "5-bit (Unsloth Dynamic): Q5_K experts with Q8_0 downs, close to Q8_0 in quality",
                   "download_gb": 158.3, "ram_gb": 108, "arena_gb": 98.4, "families": ("unsloth",), "budget": True,
                   "shards": 6, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00006.gguf", "engine": (0, 1, 44),
                   "vision": True},
    "UD-Q6_K_XL": {"about": "6-bit (Unsloth Dynamic): Q6_K experts with Q8_0 downs",
                   "download_gb": 169.2, "ram_gb": 118, "arena_gb": 109.2, "families": ("unsloth",), "budget": True,
                   "shards": 6, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00006.gguf", "engine": (0, 1, 44),
                   "vision": True},
    "Q8_0": {"about": "8-bit, the reference quality (every expert Q8_0); for a 192 GB PC",
             "download_gb": 188.2, "ram_gb": 136, "arena_gb": 128.3, "families": ("unsloth",), "budget": True,
             "shards": 6, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00006.gguf", "engine": (0, 1, 38),
             "vision": True},
    # Round 0214: Unsloth's v3.1 sets (revision UNSLOTH_V31_REVISION, pins UNSLOTH_V31_SHARDS): i-quant / Q2_0 experts, the last shard is the n-gram table
    # (IQ4_NL, 28.8 GB, in a shard of its own); "quant" is the name on the Hub (folder and file names).  The about lines come with the wording commit.
    # download_gb / arena_gb: the pinned shard sizes and the routed experts' bytes (tests/fixtures/unsloth_v31); ram_gb: the RAM-budget floor of UD-Q4_K_XL.
    "UD-IQ1_M": {"about": "~1-bit (Unsloth Dynamic v3.1), the smallest download", "download_gb": 68.0, "ram_gb": 48, "arena_gb": 34.8, "families": ("unsloth",), "budget": True,
                 "shards": 3, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00003.gguf", "quant": "UD-IQ1_M",
                 "revision": UNSLOTH_V31_REVISION, "engine": UNSLOTH_V31_ENGINE, "vision": True, "uma_pool_auto": True},
    "UD-Q2_0": {"about": "2-bit (Unsloth Dynamic v3.1)", "download_gb": 70.5, "ram_gb": 48, "arena_gb": 37.4, "families": ("unsloth",), "budget": True,
                "shards": 3, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00003.gguf", "quant": "UD-Q2_0",
                "revision": UNSLOTH_V31_REVISION, "engine": UNSLOTH_V31_ENGINE, "vision": True, "uma_pool_auto": True},
    "UD-IQ2_XS": {"about": "2-bit i-quant (Unsloth Dynamic v3.1)", "download_gb": 75.8, "ram_gb": 48, "arena_gb": 42.3, "families": ("unsloth",), "budget": True,
                  "shards": 3, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00003.gguf", "quant": "UD-IQ2_XS",
                  "revision": UNSLOTH_V31_REVISION, "engine": UNSLOTH_V31_ENGINE, "vision": True, "uma_pool_auto": True},
    "UD-Q2_K_XL": {"about": "2-bit (Unsloth Dynamic v3.1) with some 3-bit experts", "download_gb": 79.6, "ram_gb": 48, "arena_gb": 46.0, "families": ("unsloth",), "budget": True,
                   "shards": 4, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00004.gguf", "quant": "UD-Q2_K_XL",
                   "revision": UNSLOTH_V31_REVISION, "engine": UNSLOTH_V31_ENGINE, "vision": True, "uma_pool_auto": True},
    "UD-IQ3_XXS": {"about": "3-bit i-quant (Unsloth Dynamic v3.1)", "download_gb": 83.6, "ram_gb": 48, "arena_gb": 50.3, "families": ("unsloth",), "budget": True,
                   "shards": 4, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00004.gguf", "quant": "UD-IQ3_XXS",
                   "revision": UNSLOTH_V31_REVISION, "engine": UNSLOTH_V31_ENGINE, "vision": True, "uma_pool_auto": True},
    "UD-Q3_K_XL": {"about": "3-bit (Unsloth Dynamic v3.1) with some 4-bit experts", "download_gb": 89.5, "ram_gb": 48, "arena_gb": 56.2, "families": ("unsloth",), "budget": True,
                   "shards": 4, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00004.gguf", "quant": "UD-Q3_K_XL",
                   "revision": UNSLOTH_V31_REVISION, "engine": UNSLOTH_V31_ENGINE, "vision": True, "uma_pool_auto": True},
    # the v3.1 UD-IQ4_XS is another file from the pinned UD-IQ4_XS (345 of 1224 tensors changed type; four shards): its own name
    UNSLOTH_V31_IQ4_XS: {"about": "~4-bit i-quant (Unsloth Dynamic v3.1), a newer file than UD-IQ4_XS with other tensor types", "download_gb": 93.7, "ram_gb": 48, "arena_gb": 60.4, "families": ("unsloth",), "budget": True,
                         "shards": 4, "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00004.gguf", "quant": "UD-IQ4_XS",
                         "revision": UNSLOTH_V31_REVISION, "engine": UNSLOTH_V31_ENGINE, "vision": True, "uma_pool_auto": True},
    # MODEL-UPDATE Phase 4: NVFP4 experts, ready-made packs (NVFP4_REPOS).  63.3 GiB (68.0 GB) of experts in the
    # pack's experts.bin; the low-RAM mode reads them from there on a PC whose RAM does not hold them.  NVIDIA only
    # (the HIP and SYCL engines have no NVFP4 kernels).  Images: both packs keep Qwen's vision tower unquantized, so the
    # original's image encoder (ISTA's mmproj, the same file as for every Flash-Next model) reads pictures for them;
    # checked end to end on an RTX 5070 and an RTX 3060 against IQ3_XXS's answers on the same picture.
    # Gyro (agentionai): "ram_gb" is the memory the weights need in total, VRAM and RAM together ("mem_total"): Gyro-S
    # 27.6 GB, Gyro-M 35 GB (the rest of the download is the n-gram table, read from the SSD).  Neither is anyone's
    # default: setup and the MCP server mention them where the other sizes do not fit.  Images: the same mmproj as every
    # Flash-Next model; strata-vision reads only the vocabulary and header of the Gyro GGUF (tools/vision/gguf_meta.h),
    # whose TQK6 / TQK7 tensors llama.cpp does not know.
    "Gyro-S": {"about": "the smallest option, for PCs with little memory (27.6 GB of VRAM + RAM together); lower quality "
                        "than the 2-3-bit sizes, and the 2-bit Q2_0 decodes faster",
               "download_gb": 58.5, "ram_gb": 27.6, "arena_gb": 25.8, "families": ("gyro",), "mem_total": True,
               "file": "Qwen3.8-Flash-Next-Gyro-S-TQ1_0.gguf", "shards": 1, "engine": GYRO_ENGINE, "vision": True},
    "Gyro-M": {"about": "about IQ3_XXS quality with about 20% less GPU memory (35 GB of VRAM + RAM together); decodes "
                        "about 16-21% slower than Q2_0 on 12 GB cards",
               "download_gb": 92.0, "ram_gb": 35.0, "arena_gb": 32.1, "families": ("gyro",), "mem_total": True,
               "file": "Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf", "shards": 1, "engine": GYRO_ENGINE, "vision": True},
    "NVFP4": {"about": "best quality of the NVFP4 versions (GPTQ, sergqwer's strata-nvfp4 pack); RTX 50 has FP4 tensor cores, "
                       "other NVIDIA cards run it at 8-bit precision", "download_gb": 128.0, "ram_gb": 80, "arena_gb": 68.0,
              "families": ("nvfp4",), "nvidia_only": True, "vision": True, "repo": NVFP4_GPTQ_REPO,
              "engine": NVFP4_ENGINE,
              "license": "Qwen Community License 1.0 (Qwen3.8-Flash-Next's): https://huggingface.co/Qwen/Qwen3.8-Flash-Next"},
    "NVFP4-NVIDIA": {"about": "NVIDIA's own NVFP4 checkpoint (plain rounding), converted by sergqwer; the same size "
                              "and speed as NVFP4", "download_gb": 128.0, "ram_gb": 80, "arena_gb": 68.0,
                     "families": ("nvfp4",), "nvidia_only": True, "vision": True, "repo": NVFP4_NVIDIA_REPO,
                     "engine": NVFP4_ENGINE,
                     "license": "NVIDIA Open Model License (Licensed by NVIDIA Corporation under the NVIDIA Open Model "
                                "License) with Qwen3.8-Flash-Next's Qwen Community License 1.0: "
                                "https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4"},
    "NVFP4-QAD": {"about": "NVIDIA's FP4, trained for FP4 (NVIDIA's Qwen3.8-Flash-Next-FP4-Local) - slightly faster on short prompts; "
                           "a 102 GB download that this PC turns into a Strata pack once (about 20-40 minutes, 110 GB more disk); "
                           "RTX 50 cards have FP4 tensor cores, other NVIDIA cards run it at 8-bit precision. It reads pictures (the shared Qwen3.8-Flash-Next encoder)",
                  "download_gb": 102.2, "prepare_gb": 110.0, "ram_gb": 80, "arena_gb": 68.0,
                  "families": ("nvfp4",), "nvidia_only": True, "vision": True, "repo": NVFP4_FP4LOCAL_REPO,
                  "prepare": "fp4-local", "engine": FP4LOCAL_ENGINE,
                  "license": "NVIDIA Open Model Agreement (Licensed by NVIDIA Corporation under the NVIDIA Open Model "
                             "Agreement) with Qwen3.8-Flash-Next's Qwen Community License 1.0: "
                             "https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local"},
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

UNSLOTH_BIG_SHARDS = {
    "Qwen3.8-Flash-Next-UD-Q5_K_XL-00001-of-00006.gguf":
        (10946618, "610922cdb1afe1094e95d7a3e86b12ee33317ebbf7320ac9344e21b6ae4bb69f"),
    "Qwen3.8-Flash-Next-UD-Q5_K_XL-00002-of-00006.gguf":
        (682434912, "494ca4ed3dbf97bc28da88af3890b8877b9032f909812d00c0526a9ca5e91d2e"),
    "Qwen3.8-Flash-Next-UD-Q5_K_XL-00003-of-00006.gguf":
        (54400261312, "34efd79a80a1ce540a517a5d56171924b66ce1c38b04c904f17ad6d8ef17cf20"),
    "Qwen3.8-Flash-Next-UD-Q5_K_XL-00004-of-00006.gguf":
        (49990245824, "9ee6bbe462e6830864382d629101490625b1c95afa15492b7ad550c7bed2dd13"),
    "Qwen3.8-Flash-Next-UD-Q5_K_XL-00005-of-00006.gguf":
        (49882416192, "0b2437f661f584030cb5aeb8fb1bb70f6422518a6746bfcc0304167c7b6b8beb"),
    "Qwen3.8-Flash-Next-UD-Q5_K_XL-00006-of-00006.gguf":
        (3320101792, "55dd96c5ad0863b06b6393151b9ad0ac727b8d58a62e02a296ca5d5ddbfee4a3"),
    "Qwen3.8-Flash-Next-UD-Q6_K_XL-00001-of-00006.gguf":
        (10946624, "8bdc6bad55b6699f46f60708829932ff4018d7ac9bd309c388534fa31753bdb7"),
    "Qwen3.8-Flash-Next-UD-Q6_K_XL-00002-of-00006.gguf":
        (682434912, "494ca4ed3dbf97bc28da88af3890b8877b9032f909812d00c0526a9ca5e91d2e"),
    "Qwen3.8-Flash-Next-UD-Q6_K_XL-00003-of-00006.gguf":
        (54400261312, "34efd79a80a1ce540a517a5d56171924b66ce1c38b04c904f17ad6d8ef17cf20"),
    "Qwen3.8-Flash-Next-UD-Q6_K_XL-00004-of-00006.gguf":
        (49814108512, "0ea4b599880a5a52fcd9c188ba1443f646c69c96571904ddbd6a79246a01a997"),
    "Qwen3.8-Flash-Next-UD-Q6_K_XL-00005-of-00006.gguf":
        (49419317344, "9948e81ae8368144b135a7403d8c0f2cf9a6c2f9f692313865855b2832e696c9"),
    "Qwen3.8-Flash-Next-UD-Q6_K_XL-00006-of-00006.gguf":
        (14838313984, "e4ae255234f42b18012f6d6eec5bf615b57479b7e0a0233c47436a321ffeec3f"),
    "Qwen3.8-Flash-Next-Q8_0-00001-of-00006.gguf":
        (10946624, "2dabcbb53ca537a7947bc7d20414fd464eeaf4d66d43021b5b2556cc87544ad2"),
    "Qwen3.8-Flash-Next-Q8_0-00002-of-00006.gguf":
        (682434912, "494ca4ed3dbf97bc28da88af3890b8877b9032f909812d00c0526a9ca5e91d2e"),
    "Qwen3.8-Flash-Next-Q8_0-00003-of-00006.gguf":
        (54400261312, "34efd79a80a1ce540a517a5d56171924b66ce1c38b04c904f17ad6d8ef17cf20"),
    "Qwen3.8-Flash-Next-Q8_0-00004-of-00006.gguf":
        (49446841216, "bfa634025fabbd2658bf7694bc80b90e571699c768723f844c934c7ef06c691a"),
    "Qwen3.8-Flash-Next-Q8_0-00005-of-00006.gguf":
        (49668930400, "232a8f14cc0fa4262e7efe8593774b136fe40909e39c7a020342ddaa27259a97"),
    "Qwen3.8-Flash-Next-Q8_0-00006-of-00006.gguf":
        (34015618784, "538a93bca918064983409a41187ad4c68640f9aced6f29564da8f551bf86d7a5"),
}

UNSLOTH_V31_SHARDS = {
    "Qwen3.8-Flash-Next-UD-IQ1_M-00001-of-00003.gguf":
        (10946618, "b0d883bb9464021f31074145af74bfc2aa2d4bf0cf506f26f6f5107f4ca6ce17"),
    "Qwen3.8-Flash-Next-UD-IQ1_M-00002-of-00003.gguf":
        (39196009888, "bddcd79634ccddbb2e0951345c73c6ae8bd7b12594f55a2a529474701757391e"),
    "Qwen3.8-Flash-Next-UD-IQ1_M-00003-of-00003.gguf":
        (28800138432, "05716382c280d999b81afff92b2d527fadbfd926ac225ffdc273f2d1d13331c6"),
    "Qwen3.8-Flash-Next-UD-Q2_0-00001-of-00003.gguf":
        (10946618, "38803c4e8d13077165aa9854502b3d4e7fef750e72a21d27a38ee42089f96ad6"),
    "Qwen3.8-Flash-Next-UD-Q2_0-00002-of-00003.gguf":
        (41738806688, "57af20207d5f18fa72fba503806d98d65f58ba3982fe55c89c6ed6e691471acc"),
    "Qwen3.8-Flash-Next-UD-Q2_0-00003-of-00003.gguf":
        (28800138432, "05716382c280d999b81afff92b2d527fadbfd926ac225ffdc273f2d1d13331c6"),
    "Qwen3.8-Flash-Next-UD-IQ2_XS-00001-of-00003.gguf":
        (10946618, "91e8dc8f1428ce25d48fd1f711e4bf1f42215c5bac0f32eeb5608e6ec7ae91e9"),
    "Qwen3.8-Flash-Next-UD-IQ2_XS-00002-of-00003.gguf":
        (47021008288, "11a67c82f54a9edf683d6b708062de78d803921a18a6cb2bf1dd55949b4ef9bd"),
    "Qwen3.8-Flash-Next-UD-IQ2_XS-00003-of-00003.gguf":
        (28800138432, "05716382c280d999b81afff92b2d527fadbfd926ac225ffdc273f2d1d13331c6"),
    "Qwen3.8-Flash-Next-UD-Q2_K_XL-00001-of-00004.gguf":
        (10946618, "297e174dc185f2bf3ab1856461059cb8a05aa741bc27edf42461cde87e5420af"),
    "Qwen3.8-Flash-Next-UD-Q2_K_XL-00002-of-00004.gguf":
        (49732486272, "a4782511810bb61bd6b3236607a0aad05b1bfa04b90356defd202bb17e7db16d"),
    "Qwen3.8-Flash-Next-UD-Q2_K_XL-00003-of-00004.gguf":
        (1037181344, "4dffc4a1cea7ad484f2d5c711b747840e459b040b636cc8ddaa524d01e60662e"),
    "Qwen3.8-Flash-Next-UD-Q2_K_XL-00004-of-00004.gguf":
        (28800138432, "5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36"),
    "Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00004.gguf":
        (10946618, "9d5644b371ffac921427c8021cc7242dab8e3ba37d7b48d1e79fe3770fbf9915"),
    "Qwen3.8-Flash-Next-UD-IQ3_XXS-00002-of-00004.gguf":
        (49946027488, "aacaff3bdb9032c2c3be428167930809735f65d3cfb204eba07d85e421e7ddf4"),
    "Qwen3.8-Flash-Next-UD-IQ3_XXS-00003-of-00004.gguf":
        (4869325888, "ef8f14e790ab471b363f146d5e8664eefbaf03e5776f317a1fb96a2bc7707b07"),
    "Qwen3.8-Flash-Next-UD-IQ3_XXS-00004-of-00004.gguf":
        (28800138432, "5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36"),
    "Qwen3.8-Flash-Next-UD-Q3_K_XL-00001-of-00004.gguf":
        (10946618, "7666000ba91eb5527f8e12e0414de36766dc82a082876337f7827c2caa859143"),
    "Qwen3.8-Flash-Next-UD-Q3_K_XL-00002-of-00004.gguf":
        (49742117248, "e954cb3044ae087a003ce8cc1631c9d40fe15ae64a8befcf4aa06457848c647c"),
    "Qwen3.8-Flash-Next-UD-Q3_K_XL-00003-of-00004.gguf":
        (10911746208, "fcce26b1e5e6e54559a7e7c2f8d6e37067ec695ff1f14bce662810bde78abe1f"),
    "Qwen3.8-Flash-Next-UD-Q3_K_XL-00004-of-00004.gguf":
        (28800138432, "5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00004.gguf":
        (10946618, "93ff23a08e5cd7501f24fa16f5b415d5807d0175e04edd3ed6a7a41b601a4eef"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00004.gguf":
        (49604491008, "13d5dc8b93d039e4cfade5a9af7037f10c97f7ec4e53f75bd2e9ae34aae54aeb"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00004.gguf":
        (15256783680, "f6b9b5934908a2043732269dd740155d0f921d0763a1dcdd3452246311651f87"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00004-of-00004.gguf":
        (28800138432, "5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36"),
}

UNSLOTH_Q4_V31_SHARDS = {
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf":
        (10946618, "acc44040f74d0e55fb89c3967056cce5dbda1bcc52e909c3ba6fc72b5e9c0858"),
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf":
        (49720539552, "45792ae869072d8229384c51c7c73dd959e191505252b41dd71852d9746f5ce4"),
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf":
        (32803030176, "8c76e79d444b16a663d9c8db54e585ed3b1da13eebd2619c37b0c355da803c82"),
    "Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf":
        (28800138432, "5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36"),
}

UNSLOTH_RAM_LEFT_GB = 24        # RAM beside the budget where the 17 below was not measured: a layer split's need (unsloth_split_need_gb) and a unified-memory GPU (the cache and the budget share the RAM)

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
    # Unsloth's UD-IQ4_XS (three shards, #621), UD-Q4_K_XL (four), UD-Q5_K_XL, UD-Q6_K_XL and Q8_0 (six) of the original
    # model (docs/QUANTS.md): regular choices since f-quants; the shard count and "vision" are per model (MODELS)
    "unsloth": {"title": "Qwen3.8-Flash-Next (Unsloth)", "by": "Unsloth's 1- to 8-bit quantizations",
                "about": "UD-IQ1_M, UD-Q2_0, UD-IQ2_XS, UD-Q2_K_XL, UD-IQ3_XXS, UD-Q3_K_XL, UD-IQ4_XS, UD-IQ4_XS-v31, UD-Q4_K_XL, UD-Q5_K_XL, UD-Q6_K_XL or Q8_0 (68 to 188 GB downloads): every expert in "
                         "RAM from ~50 GB (UD-IQ1_M) to ~136 GB (Q8_0) of RAM, else part of them read from the SSD",
                "hf": hf("unsloth/Qwen3.8-Flash-Next-GGUF") + "{q}/",
                "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00004.gguf", "shards": 4, "tag": "unsloth-",
                "mmproj_hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF"),
                "mmproj": "mmproj-Qwen3.8-Flash-Next-BF16.gguf", "name": "qwen3.8-flash-next-unsloth",
                "vision": True, "pack_args": ["--compat-bf16"],
                "sha256": {**UNSLOTH_V31_SHARDS, **UNSLOTH_SHARDS, **UNSLOTH_IQ4_XS_SHARDS, **UNSLOTH_BIG_SHARDS},
                "sha256_alt": {n: (pin,) for n, pin in UNSLOTH_Q4_V31_SHARDS.items()}},
    # MODEL-UPDATE Phase 4: the original model with NVFP4 experts, as ready-made packs (NVFP4_REPOS): the files come
    # as the engine reads them (no GGUF to pack), each size has its own repository ("repo" in MODELS)
    # agentionai's Gyro quantizations (see GYRO_FILES): after the regular families, never the default
    "gyro": {"title": "Qwen3.8-Flash-Next (Gyro)", "by": "Gyro quantizations by agentionai",
             "about": "Gyro-S (27.6 GB of memory) and Gyro-M (35 GB): the smallest sizes, for PCs with little memory; "
                      "58 and 92 GB downloads (the files include the n-gram table)",
             "hf": hf("agentionai/Qwen3.8-Flash-Next-Gyro-GGUF"), "file": "Qwen3.8-Flash-Next-{q}.gguf", "shards": 1,
             "tag": "gyro-", "name": "qwen3.8-flash-next-gyro", "vision": True, "pack_args": ["--compat-bf16"],
             "mmproj_hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF"), "mmproj": "mmproj-Qwen3.8-Flash-Next-BF16.gguf",
             "sha256": GYRO_FILES,
             "license": "Qwen Community License 1.0 (Qwen3.8-Flash-Next's; the Gyro files are agentionai's quantization): "
                        "https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-GGUF"},
    "nvfp4": {"title": "Qwen3.8-Flash-Next (NVFP4)", "by": "NVFP4 packs by sergqwer (strata-nvfp4)",
              "about": "4-bit NVFP4 experts, NVIDIA cards; a 128 GB download, ~80 GB of RAM to keep every expert in RAM",
              "tag": "nvfp4-", "name": "qwen3.8-flash-next-nvfp4", "ready": True,
              "mmproj_hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF"), "mmproj": "mmproj-Qwen3.8-Flash-Next-BF16.gguf",
              "mmproj_sha256": (907543008, "b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0")},
}

def own_files_in(folder) -> None:
    """Strata writes nothing beside the person's own model files (lane NET item 5): their finish marks are kept in marks/ (_kept_mark)."""
    try:
        p = Path(folder).expanduser().resolve()
        _OWN_DIRS.append(p.parent if p.is_file() else p)
    except OSError:
        p = Path(folder).expanduser()
        _OWN_DIRS.append(p.parent if p.is_file() else p)

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
    n = min(n, POOL_WORKERS_CAP)   # setup never writes a big worker count (see plan_pool_workers)
    p, e = cpu_cores()
    ok(f"hybrid CPU ({p} performance + {e} efficiency cores): {n} CPU expert workers - the performance cores and half "
       "of the efficiency cores (--pool-workers in the config; START-HERE --calibrate measures it on this PC)")
    return [*args, "--pool-workers", str(n)]

def two_socket_note(sockets) -> list[str]:
    """Bench #674 #707 (2-socket Xeons: 17-18 workers beat 35 by ~20%): a tip to keep the expert pool on one socket's
    cores, one fewer for the host loop.  Nothing is written to the config."""
    if not sockets or sockets[0] < 2 or sockets[1] < 3:
        return []
    n = sockets[1] - 1
    return [f"tip: this PC has {sockets[0]} CPU sockets of {sockets[1]} cores. Expert workers on the other socket have "
            f"been measured slower than fewer, local ones (35 vs 17-18 on 2-socket Xeons): try --pool-workers {n} in "
            "the config's args (START-HERE --calibrate measures it on this PC)"]

POOL_WORKERS_CAP = 32

def is_gb10(g) -> bool:
    """A DGX Spark's GPU: the GB10 (compute capability 12.1), on arm64 Linux, with the CPU's memory as its own. The part the Spark settings
    below were measured on (docs/DGX_SPARK_LINUX.md); any other unified-memory NVIDIA GPU gets the ordinary settings."""
    return isinstance(g, dict) and bool(g.get("uma")) and str(g.get("arch")) == "121" and is_arm64() and sys.platform.startswith("linux")

def effective_vram_gb(g) -> float:
    """Usable VRAM of card `g`: when `free_gb` was reported by nvidia-smi (#6662), use min(vram_gb, free_gb)
    so cards held by the desktop/browser/another process don't over-pick tiers; otherwise fall back to vram_gb."""
    if not isinstance(g, dict):
        return 0.0
    total = float(g.get("vram_gb") or 0.0)
    free = g.get("free_gb")
    if isinstance(free, (int, float)) and not isinstance(free, bool) and free >= 0.0 and not g.get("uma"):
        return min(total, float(free))
    return total

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

SPLIT_MIN_VRAM_GB = 8                                   # a card sharing a model holds the dense weights and its own

def gpu_problem(g, together=False):
    """Why Strata cannot use this card, in plain words (None: it can)."""
    if int(g["arch"]) < 75 and not (sm60_card(g["arch"]) and experimental_sm60()):
        return (f"not supported - older than the RTX 20 series (compute capability {cc(g)}; Strata needs 7.5 or "
                "newer" + ("; experimental: choose it with --gpu " + str(g["index"]) + " (the CUDA 12 engine, "
                          "docs/OLDER_GPUS.md)" if sm60_card(g["arch"]) else
                          "; Maxwell only runs from a source build, docs/OLDER_GPUS.md" if maxwell_card(g["arch"]) else "") + ")")
    if together and g["vram_gb"] < SPLIT_MIN_VRAM_GB - 0.5:
        return (f"not supported together with other GPUs - {g['vram_gb']:.0f} GB of VRAM (a card sharing the model "
                f"needs {SPLIT_MIN_VRAM_GB} GB or more)")
    return None

def gpu_rank(g):
    """The order cards share a model in: the newest generation first (it gets the first layers and most of the
    work), then the most VRAM."""
    return (-int(g["arch"]), -round(g["vram_gb"]), g["index"])

def together_ok(found) -> list:
    """The cards that can share one model, in the order they would (empty if fewer than two)."""
    ok_ = sorted([g for g in found if gpu_problem(g, together=True) is None], key=gpu_rank)
    return ok_ if len(ok_) >= 2 else []

def model_file(fam: dict, model: str, i: int) -> str:
    """Shard i's file name: the family's pattern, or the model's own (#621: UD-IQ4_XS has three shards, not four).  {q} is the
    name on the Hub ("quant"; the catalog name of the v3.1 UD-IQ4_XS is another)."""
    return MODELS.get(model, {}).get("file", fam["file"]).format(q=model_quant(model), i=i)

def model_quant(model: str) -> str:
    """The name of the model's files and folder on the Hub: the catalog name, except where a catalog name had to differ (UNSLOTH_V31_IQ4_XS)."""
    return MODELS.get(model, {}).get("quant", model)

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
    if len(gpu_sel(cfg.get("gpu"))) < 2:
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

WORK_BUDGET_KEY = "ui_budget_work_gib"     # run config: the RAM budget (GiB) the app's "Leave 20% for my work" runs with, when it differs from the --resident-budget-gib in args

def work_budget_key(cfg: dict, work, asked=None) -> None:
    """0.2.17: write (or leave out) WORK_BUDGET_KEY.  `work` is resident_budget_gib(..., work=True) for a budget setup chose by its rule.  The key is
    left out when the person asked for the budget (`asked`: --resident-budget-gib N, theirs in every mode), when the args hold no budget (a layer
    split, every expert in RAM, a mode of its own) and when the two numbers are the same (a unified-memory GPU: 24 in both)."""
    cfg.pop(WORK_BUDGET_KEY, None)
    args = cfg.get("args")
    have = flag_value(args, "--resident-budget-gib") if isinstance(args, list) else None
    if work is None or asked is not None or have is None:
        return
    try:
        if float(have) == float(work):
            return
    except ValueError:
        return
    cfg[WORK_BUDGET_KEY] = int(work)

def gguf_py_env() -> dict:
    """The environment the preparation tools get for the GGUF library: STRATA_GGUF_PY only when the user named a gguf-py folder (then the tools
    use llama.cpp's gguf-py instead of tools/strata_gguf.py); empty by default, so the tools use their own."""
    own = os.environ.get("STRATA_GGUF_PY")
    return {"STRATA_GGUF_PY": str(gguf_py_dir())} if own and (Path(own) / "gguf").is_dir() else {}

def llama_override():
    """A llama.cpp checkout named by STRATA_GGML_DIR (an override of the vendored ggml, kept for two releases), else None: the engine then builds
    from third_party/strata-ggml and nothing is downloaded."""
    own = os.environ.get("STRATA_GGML_DIR")
    return Path(own) if own and (Path(own) / "ggml" / "CMakeLists.txt").exists() else None

def get_llama_cpp():
    """Kept for callers that still name it: the llama.cpp override tree (STRATA_GGML_DIR) or None. Nothing is downloaded any more."""
    return llama_override()

def low_ram_vram(g) -> float:
    """The GPU memory the low-RAM mode may count as room beside the RAM: a discrete card's usable VRAM
    (respecting free_gb when known, #6662); an APU's BIOS carve-out only (its shared memory is the RAM itself)."""
    return g.get("dedicated_gb", 0.0) if g.get("uma") else effective_vram_gb(g)

RECOMMENDED_SIZES = {"qwen": ("IQ3_S",), "swift": ("IQ3_S",), "unsloth": ("UD-Q4_K_XL", "UD-IQ4_XS")}   # owner's pick, 0.1.44

def mem_have(model: str, ram: float, vram: float = 0.0) -> float:
    """The memory this PC offers a model, in the unit of its MODELS "ram_gb": RAM, or for a "mem_total" model (Gyro) the
    VRAM and the RAM together."""
    return ram + vram if MODELS[model].get("mem_total") else ram

MEMORY_TIERS = ((62.0, "qwen", "IQ3_S"), (46.0, "qwen", "IQ3_XXS"), (38.0, "swift", "IQ2_XS"))

TIER_SYSTEM_RESERVE_GB = 5.0

def tier_pick(ram: float, vram: float = 0.0):
    """(family, size) for this PC's RAM + VRAM by MEMORY_TIERS, or None below the lowest tier (then the older rules pick:
    Gyro-S, or the Coder).  With less RAM than the size's own figure the low-RAM mode starts by itself and the model is
    slower.  A recommendation: every size stays a choice."""
    for floor, fam, m in MEMORY_TIERS:
        if ram + vram - TIER_SYSTEM_RESERVE_GB >= floor:
            return fam, m
    return None

def recommended_size(family: str, names: list, ram: float, vram: float = 0.0) -> str:
    """The size the menu pre-selects (and --yes takes): the memory tier's size (RAM + VRAM, MEMORY_TIERS) when this
    family has it, else the family's recommended size when this PC's RAM fits it (UD-Q4_K_XL before UD-IQ4_XS), else
    the largest size that fits, else the first.  Recommend, never force: every other size stays a choice."""
    tier = tier_pick(ram, vram)
    if tier and tier[1] in names and family in ("qwen", "swift"):
        return tier[1]
    for m in RECOMMENDED_SIZES.get(family, ()):
        if m in names and mem_have(m, ram, vram) >= MODELS[m]["ram_gb"]:
            return m
    fitting = [m for m in names if mem_have(m, ram, vram) >= MODELS[m]["ram_gb"]]
    if fitting:
        return max(fitting, key=lambda m: MODELS[m]["download_gb"])
    return "UD-IQ4_XS" if family == "unsloth" and "UD-IQ4_XS" in names else names[0]

def installed_size(family: str, names: list, have: list) -> str | None:
    """0.1.44.1: the size of this family that is already installed (the most recently used config first), or None.  Setup
    run again (SETUP.bat, --setup) pre-selects it: the 0.1.44 recommendation (IQ3_S, about 15% slower than IQ3_XXS and
    7 GB more RAM) is for a first install, and Enter must not move an installed model to another size."""
    for c in have:
        try:
            ch = choices_from_config(c)
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            continue
        if ch.get("family") == family and ch.get("model") in names:
            return ch["model"]
    return None

def unsloth_default_env(family: str, model: str, hip: bool, in_budget: bool, arch: str = "") -> dict:
    """0.1.44 (owner, review-quants.md section 5): the run-config "env" setup writes for Unsloth's files.
    STRATA_MMQ_KQ=1 (the K-quant MMQ prompt kernels) for UD-Q5_K_XL and UD-Q6_K_XL, where its prompt-path KL is equal
    or better than the FP16 path's; UD-Q4_K_XL keeps it opt-in here (the Linux gfx12 engine takes it by itself since 0.2.10.1).
    STRATA_HC_Q8 on CUDA for the UD-* files is the ENGINE's default now (it sees the Q8_0 hyper-connection projections in the GGUF); setup
    writes nothing for it.
    STRATA_ROUTE_TAIL_SKIP=0 in every Unsloth config (0.2.17, owner 11-19: the tail skip is Off by default; users saw lower quality).  Before 0.2.17 setup
    wrote it only where every expert is in RAM and not on Linux gfx12; the RAM-budget mode and Linux gfx12 ran the engine's own default (rank 7).
    The ``in_budget`` and ``arch`` arguments are kept for the callers and no longer change anything.  Every engine start also sets an unset
    STRATA_ROUTE_TAIL_SKIP to 0 (serve/server.py child_env), so the other families and the configs made before 0.2.17 start Off too.  The way to
    turn it on is STRATA_ROUTE_TAIL_SKIP=7 (the app's Expert settings, ``strata launch --set STRATA_ROUTE_TAIL_SKIP=7``); a setup run again keeps
    a value the person put there (carry_over)."""
    env = {}
    if family != "unsloth":
        return env
    if model in ("UD-Q5_K_XL", "UD-Q6_K_XL"):
        env["STRATA_MMQ_KQ"] = "1"
    env["STRATA_ROUTE_TAIL_SKIP"] = "0"
    return env

def menu_families(hip: bool) -> list:
    """The families the model menu lists, in menu order.  The NVFP4 packs run on NVIDIA cards only (the AMD and Intel
    engines have no NVFP4 kernels), so on those the menu does not offer them; `--family nvfp4` still says why not."""
    return [f for f in FAMILIES if not (hip and FAMILIES[f].get("ready"))]

LOW_RAM_HEADROOM_GB = 10   # RAM beside the experts (GiB, as ram_gb() counts): the OS, the engine's other buffers, the server

RESIDENT_ENGINE = (0, 1, 30)   # the first engine with --resident-experts (the low-RAM mode's resident variant)

def low_ram_needed(model, ram) -> bool:
    """The model's experts do not fit this PC's RAM with room left for the rest: they are then mapped from the pack's
    experts.bin instead of copied into RAM (the low-RAM mode)."""
    return ram_short_of_arena(ram, MODELS[model]["arena_gb"])

def ram_short_of_arena(ram_gib, arena_gb, headroom_gib=LOW_RAM_HEADROOM_GB) -> bool:
    """True when `ram_gib` (GiB, as ram_gb() returns it) is less than an expert arena of `arena_gb` (GB of 10^9
    bytes, as MODELS gives it) plus the headroom (GiB): both sides counted in GiB."""
    return ram_gib < arena_gb * 1e9 / 2**30 + headroom_gib

MTP_VRAM_GB = 1.0

def low_ram_gpu_gb(model, vram_gb, ctx=32768, kv="int8", mtp=True) -> float:
    """About how many GB of the model's experts the GPU's cache holds: its VRAM minus ~5 GB for the dense weights,
    buffers and a 32K context's KV cache, minus the KV cache of a longer context (in VRAM in the low-RAM mode: its RAM
    has no room for KV streaming), minus ~1 GB for the draft layer (MTP) when it is on."""
    kv_tok = 13 * KV_CELL_BYTES.get(kv, 1056)           # bytes per context token: 12 QSA layers + the draft layer
    longer = max(0, ctx - 32768) * kv_tok / 1e9
    return max(0.0, min(MODELS[model]["arena_gb"], vram_gb - 5 - (MTP_VRAM_GB if mtp else 0.0) - longer))

def low_ram_resident(model, ram, vram_gb, ctx=32768, kv="int8", mtp=True) -> bool:
    """In the low-RAM mode: the experts the GPU does not hold fit the RAM with the usual room beside them, so they are
    copied into RAM once (the resident variant, `--resident-experts`) instead of being read through the OS file cache
    (plain `--mmap-experts`, which a PC this short of RAM keeps re-reading from the SSD)."""
    rest = MODELS[model]["arena_gb"] - low_ram_gpu_gb(model, vram_gb, ctx, kv, mtp)
    return ram >= rest + LOW_RAM_HEADROOM_GB

def kv_streaming_ram_gb(ctx, kv) -> float:
    """The RAM a streamed KV cache takes: ~13.7 KB per context token with 8-bit KV (1.7 GB at 128K), 10.6 KB with
    K8V4, 7.5 KB with 4-bit - 12 QSA layers + the draft layer."""
    return ctx * (13 * KV_CELL_BYTES.get(kv, 1056)) / 1e9

def kv_streaming_need_gb(model, ctx, kv) -> float:
    """The RAM a PC needs before setup streams this model's KV cache on its own (`--kv-streaming on` skips the test):
    the smaller of two numbers.  (1) The model's all-in-RAM need (`ram_gb`) + the KV cache + 1 GB: the experts all fit
    and the cache comes on top.  (2) The experts (`arena_gb`) + LOW_RAM_HEADROOM_GB beside them (the line
    `low_ram_needed` draws) + the KV cache: a small card holds so few experts that the engine's RAM copy is the
    rest, and the KV's RAM then comes out of that copy (or out of the OS file cache when the arena does not fit),
    not on top of it.  KV-128 (phaseA-tests/gh-sweep-1031/KV-128.md), IQ3_S on a 12 GB card at 128K, 45 GiB of RAM
    for the engine (Linux mimic): streaming gave 756 -> 1,267 expert slots and a 32K prompt in 12-17 s instead of
    21-34 s, with the RAM the engine used unchanged (RAM budget 31 -> 29 GiB); on the owner's RTX 5070 (R5070's
    run) 924 -> 1,585 slots, a 32K prompt 130 -> 79 s, the RAM copy 30.8 -> 28.9 GiB, no paging.  Rule (1) alone
    asked 64.8 GB of a PC that reads 63.1 and left the KV in VRAM.
    #6354: Unsloth budget-mode quants subtract KV RAM from --resident-budget-gib, so streaming works cleanly from
    16 GB RAM up (keeping 12 GB OS headroom + KV RAM)."""
    kv_gb = kv_streaming_ram_gb(ctx, kv)
    m = MODELS[model]
    if m.get("budget"):
        return max(16.0, LOW_RAM_HEADROOM_GB + kv_gb + 4.0)
    return min(m["ram_gb"] + kv_gb + 1, m["arena_gb"] + LOW_RAM_HEADROOM_GB + kv_gb)

def ctx_ram_need(model, ctx, low_ram=False):
    """#406: the RAM (GB) setup estimates for a long context with IQ3_XXS / IQ3_S: their experts + the context's
    8-bit KV cache + 24 GB of room for everything else (the 0.1.29 arithmetic, counted).  None where the context does
    not count against RAM by this rule: the other sizes, and the low-RAM mode (its KV cache stays in VRAM)."""
    if model not in ("IQ3_XXS", "IQ3_S") or low_ram:
        return None
    return MODELS[model]["arena_gb"] + ctx * 13 * 1056 / 1e9 + 24

def ram_ctx(model, ram, low_ram=False) -> int:
    """#406: the longest context the RAM rule recommends: 128K, or longer where the estimate fits this PC's RAM.  It
    is part of the recommended default (the smaller of it and the GPU's rule); a longer choice is kept, with a note.
    The 200K menu step is never the recommendation (#608)."""
    # 204800 (#608) is a menu step between 128K and 256K, never the recommendation: where 256K does not fit, 128K stays
    return max(c for c in CONTEXTS if c <= 131072 or (c != 204800 and (ctx_ram_need(model, c, low_ram) or 0) <= ram))

def data_folder(requested: str | None, move: bool = False, yes: bool = True, set_default: bool = False) -> tuple:
    """(the data folder, folders that still hold model files and are used where they are).

    A --data-dir that names a NEW folder never moves anything by itself.  When model files already exist elsewhere,
    the person is asked: keep them where they are and use the new folder for new downloads (the answer with --yes
    or when nobody can answer), or move them in (`move`, --move-data, or the answer "move").  Only a move, or
    --set-default-data-dir, or a PC with no model files anywhere, changes the remembered data folder.  Without
    --data-dir the model files of this folder and of earlier Strata folders on the same drive are gathered into the
    remembered data folder and their configs point there (that is the data folder's own job)."""
    settings = load_settings()
    remembered = Path(settings["data_dir"]) if settings.get("data_dir") else (strata_folder() if home() == ROOT else home()).parent / "Strata-data"
    dest = Path(requested).expanduser().resolve() if requested else remembered
    from strata_control import folders
    bad = folders.problem(dest)
    if bad and requested:
        fail(folders.without_nothing_changed(bad)[:400], "Nothing was downloaded or changed, and the folder was not saved as your data folder.")
    if bad and settings.get("data_dir"):                # an unusable folder saved earlier: go back to the default and say so; never keep it
        warn(f"The data folder saved before cannot be used ({bad[0]}) Using {(strata_folder() if home() == ROOT else home()).parent / 'Strata-data'} instead.")
        remembered = dest = (strata_folder() if home() == ROOT else home()).parent / "Strata-data"
        settings = {k: v for k, v in settings.items() if k != "data_dir"}
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:                                # e.g. no write access next to the Strata folder
        warn(f"cannot use {dest} for the model files ({e}): keeping them in {home()}")
        dest = home()
    elsewhere = []
    # #198: the data folder remembered before (a --data-dir to a new place) is a source too, and so is a Strata-data
    # folder nested in any of them (an install that kept its models one level down)
    sources = [home(), *other_installs(settings)]
    if settings.get("data_dir") and not same_folder(Path(settings["data_dir"]), dest):
        sources.append(Path(settings["data_dir"]))
    sources += [f / "Strata-data" for f in list(sources) if not same_folder(f / "Strata-data", dest)]
    if requested and not same_folder(dest, remembered):
        sources.append(remembered)
        # a different folder than the one in use: nothing is moved unless the person says so
        held = []
        for folder in dict.fromkeys(sources):
            if not same_folder(folder, dest) and has_data(folder) and not any(same_folder(folder, h) for h in held):
                held.append(folder)
        movable = [f for f in held if same_drive(f, dest)]
        if movable and not move and not yes:
            gb = sum(library_size_gb(f) for f in movable)
            say()
            size = f"{gb:.0f} GB" if gb >= 10 else f"{gb:.1f} GB"
            say(f"  Your models are in {', '.join(str(f) for f in movable)} ({size}).")
            say(f"  keep) leave them there and use {dest} only for new downloads")
            say(f"  move) move your {size} of models to {dest}")
            move = ask(f"Move your {size} of models to the new folder, or use the new folder only for new downloads?",
                       ["keep", "move"], "keep", False) == "move"
        if held and not move:
            for folder in held:
                say(f"  Models you already have in {folder} stay there; new downloads go to {dest}.")
            if set_default:
                save_settings({**settings, "data_dir": str(dest)})
            return dest, held
        if not held:
            move = True                                 # nothing to lose track of: the new folder becomes the default
    seen = set()
    for folder in sources:
        key = os.path.normcase(str(folder))
        if key in seen:
            continue
        seen.add(key)
        if same_folder(folder, dest) or not has_data(folder):
            continue
        if not same_drive(folder, dest):
            elsewhere.append(folder)                    # another drive: used where it is (no 70 GB copy)
            continue
        # the downloads merge file by file (the same file wherever it came from); a prepared pack or MTP layer moves
        # whole or not at all, so two copies are never mixed
        if (folder / "models").is_dir():
            move_into(folder / "models", dest / "models")
        for item in [*((folder / "packs").glob("*") if (folder / "packs").is_dir() else []), folder / "mtp"]:
            rel = item.relative_to(folder)
            if item.exists() and not (dest / rel).exists():
                move_into(item, dest / rel)
        for d in ("packs",):
            try:
                (folder / d).rmdir()                    # empty now
            except OSError:
                pass
        for c in model_config_files(folder):
            repoint_config(c, folder, dest)
        if has_data(folder):
            elsewhere.append(folder)                    # in use, or a copy the data folder already has
            warn(f"some model files are still in {folder} (in use, or already in {dest})")
        else:
            ok(f"model files from {folder} moved to {dest} (a new copy of Strata finds them there)")
    installs = [str(home())] + [p for p in settings.get("installs", [])
                                if p != str(home()) and Path(p).is_dir() and not in_trash(p)]
    save_settings({**settings, "data_dir": str(dest), "installs": installs[:20]})
    return dest, elsewhere

def data_folder_for(a) -> tuple:
    """data_folder() with the answers on the command line (--data-dir, --move-data, --yes, --set-default-data-dir)."""
    return data_folder(getattr(a, "data_dir", None), getattr(a, "move_data", False), bool(getattr(a, "yes", True)),
                       getattr(a, "set_default_data_dir", False))

def explicit_args(a) -> list[str]:
    """The engine options this run's command line sets that the person keeps from now on (user_args): --vram-reserve-mib."""
    n = getattr(a, "vram_reserve_mib", None)
    return ["--vram-reserve-mib", str(n)] if n is not None else []

def carry_user_args(old: dict, cfg: dict, explicit: list[str] | None = None) -> list[str]:
    """#3216 #3215 #3270: the engine options the person set by hand in the earlier run config are put back over the
    generated ones, and recorded in the new one's "user_args" (strata_control/user_args.py).  They are the earlier
    "user_args", the options of "args" that differ from "args_written" (hand edits), for a config with no "args_written"
    the options its args had and the new ones do not (control vectors, --spec, ...) and an explicit --vram-reserve-mib of
    the earlier file.  `explicit`: options given on this run's command line, which win.  The names kept are returned."""
    nargs = cfg.get("args")
    if not isinstance(nargs, list):
        return []
    mine = user_args.capture(old, SETUP_CHOICE_FLAGS)
    oargs = old.get("args")
    if user_args.WRITTEN_KEY not in old and isinstance(oargs, list):
        have = {user_args.flag_of(g) for g in user_args.groups(mine)}
        mine += user_args.flat([g for g in user_args.groups(user_args.dropped_by_setup(oargs, nargs, setup_flags(), SETUP_CHOICE_FLAGS))
                                if user_args.flag_of(g) not in have])
        reserve = flag_value(oargs, "--vram-reserve-mib")   # an old file: the reserve it names, unless it is the vision default or the app's own
        vis = isinstance(old.get("vision"), dict)
        if reserve is not None and reserve.isdigit() and not (vis and int(reserve) == VISION["gpu"]["reserve_mib"])                 and "ui_resource_baseline" not in old and "--vram-reserve-mib" not in mine:
            mine += ["--vram-reserve-mib", reserve]
    for g in user_args.groups(explicit or []):
        mine = user_args.merge(mine, g)
    if not mine:
        user_args.stamp(cfg, [])
        return []
    cfg["args"] = user_args.merge(nargs, mine)
    user_args.stamp(cfg, mine)
    if flag_value(mine, "--resident-budget-gib") is not None:
        cfg.pop(WORK_BUDGET_KEY, None)                 # a RAM budget of the person's: theirs in every mode, no second number for the app to swap in
    return ["args " + f for f in dict.fromkeys(g[0] for g in user_args.groups(mine) if g[0].startswith("--"))]

def flag_value(args: list, flag: str):
    """The value after `flag` in an argument list, or None."""
    for i, a in enumerate(args[:-1]):
        if a == flag:
            return str(args[i + 1])
    return None

SHAPE_ENGINE: dict = {}       # the model-shape engine the chosen model runs on: {"shape": "q4_lite"} (strata_control/shape_engine.py); empty: the Strata engine

def engine_exe(eng: Path) -> str:
    """The `exe` of a run config: the engine component in the app, else the engine binary's path. A model of its own shape names that shape's engine
    (unless locally compiled via `--build`, in which case its local binary path is written)."""
    if SHAPE_ENGINE.get("local_exe"):
        return str(SHAPE_ENGINE["local_exe"])
    if SHAPE_ENGINE.get("shape"):
        from strata_control import shape_engine
        return shape_engine.reference(SHAPE_ENGINE["shape"])
    return "component:strata-engine" if CONTROL else str(eng / EXE)

def write_setup_config(cfg_path: Path, cfg: dict, source: Path | None = None, explicit: list[str] | None = None, after_carry=None) -> None:
    """#629: setup's run config, written over an earlier one for the same model without losing what the user added
    to it: the keys setup does not write are carried over (carry_over), and the earlier file is kept as
    strata-<model>.json.bak when it changes.  `source`: an earlier install's config to carry the keys over from when
    this folder has none yet (a copy set up like the last one).  A line says what was kept, one what was not."""
    if SHAPE_ENGINE.get("title") and SHAPE_ENGINE.get("shape") and cfg.get("exe") == engine_component.REFERENCE_PREFIX + "strata-" + SHAPE_ENGINE["shape"].replace("_", "-"):
        cfg["shape_title"] = SHAPE_ENGINE["title"]                  # the engine's refusal at a start names the model, not the geometry (strata_control/shape_engine.py)
    old_path = cfg_path if cfg_path.is_file() else source
    old = None
    if old_path is not None and old_path.is_file():
        try:
            old = json.loads(old_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            pass
        if not isinstance(old, dict):
            old = None
    kept = carry_over(old, cfg, explicit) if old is not None else []
    if old is None:
        carry_user_args({}, cfg, explicit)              # a first install: only what this run's command line sets (nothing to report as kept)
    if after_carry is not None:                        # a check of the finished argument list (the person's own options are in it now)
        after_carry(cfg)
    user_args.stamp(cfg)                               # args_written: what setup wrote, for the next hand-edit check
    if "images" in cfg and cfg["images"] is None:      # --images no (or not downloaded): no image section
        cfg.pop("images")
    bak = None
    if cfg_path.is_file() and old != cfg:
        bak = cfg_path.with_name(cfg_path.name + ".bak")
        try:
            shutil.copyfile(cfg_path, bak)
        except OSError as e:
            warn(f"could not keep a copy of the earlier {cfg_path.name} ({e.strerror or e})")
            bak = None
    write_config(cfg_path, cfg)
    if kept:
        ok(f"kept from your earlier {old_path.name}: " + ", ".join(kept))
    if bak is not None:
        dropped = args_dropped(old, cfg) if old is not None else []
        say(f"  the earlier run config is kept as {bak.name}" + (
            f"; engine options it had that this one has not (setup chooses those): {' '.join(dropped)}"
            if dropped else ""))

def find_in(roots: list, rel: str):
    """The first of roots/rel that exists."""
    for r in roots:
        if (r / rel).exists():
            return r / rel
    return None

def ple_ram_platform_ok() -> bool:
    """147-verify: --ple-io ram for a PC with RAM to spare was measured on Linux only (Windows locks pages differently and
    WSL pins little), so only there."""
    return not WIN and not is_wsl()

def gpu_sel(value) -> list:
    """A config's "gpu" as a list of card numbers: 0, [0, 2] or the string form "0,2" (which serve splits
    the same way).  [] when it names none.  Without this, a string "0,1" reached gpu_info() whole and
    calibrate died with "there is no GPU 0,1" on a dual-GPU config."""
    if value is None or value == "":
        return []
    items = value if isinstance(value, (list, tuple)) else str(value).split(",")
    sel = []
    for x in items:
        x = str(x).strip()
        if x == "":
            continue
        sel.append(int(x) if x.isdigit() else x)
    return sel

OLD_LAYOUT_FILES = ("strata-*.json", "strata-*.log", "run-*.bat", "run-*.sh", "build-strata*.bat")

OLD_LAYOUT_DIRS = ("models", "packs", "mtp", ".strata-mcp", "engine-sycl", "engine-cuda12", ".rocm-win")

ENGINE_SOURCE_ENTRIES = {"src", "include", "cmake", "metal", "sycl", "spark", "third_party", "tests", "bench", "CMakeLists.txt",
                         "CMakePresets.json"}

TERMINAL_ENTRIES = ("strata.py", "setup.py", "serve", "strata_cli", "strata_control", "tools", "data", "ref", "bin", ".venv")

def move_over_old_layout() -> list:
    """MAP-0215 Q7: the first run of a clone after its pull to the 0.2.16 layout carries setup's state from the clone's root into
    terminal/, once: the run configs, logs and run scripts, the model and pack folders, the MCP state, and the engine that setup put
    in engine/ (which is the engine's source folder now; its source entries stay).  The paths inside the moved run configs and run
    scripts are changed to the new places.  Nothing is moved when terminal/ has a run config of its own, and nothing is replaced.
    START-HERE.bat / setup.sh move .venv before Python starts.  Returns the (old, new) pairs moved."""
    old = ROOT.parent
    if ROOT.name != "terminal" or not (old / "engine" / "CMakeLists.txt").is_file() or any(ROOT.glob("strata-*.json")):
        return []
    pairs = []
    for pat in OLD_LAYOUT_FILES:
        pairs += [(f, ROOT / f.name) for f in sorted(old.glob(pat)) if f.is_file()]
    pairs += [(old / d, ROOT / d) for d in OLD_LAYOUT_DIRS if (old / d).is_dir()]
    eng = old / "engine"
    if not (ROOT / "engine").exists():
        pairs += [(e, ROOT / "engine" / e.name) for e in sorted(eng.iterdir())
                  if e.name not in ENGINE_SOURCE_ENTRIES and not e.name.startswith(("build", "."))]
    moved = []
    for src, dst in pairs:
        if dst.exists():
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            # a rename only, never a copy: models/ and packs/ hold hundreds of GB. A rename that fails (another disk, files in use)
            # leaves the entry where it is, with the warning; the old place keeps working for the files a config names.
            os.rename(src, dst)
            moved.append((src, dst))
        except OSError as e:
            warn(f"{src} could not be moved to {dst}: {e}")
    if not moved:
        return []
    swaps = sorted({(str(a), str(b)) for a, b in moved} | {(str(old / n), str(ROOT / n)) for n in TERMINAL_ENTRIES}
                   | ({(str(eng), str(ROOT / "engine"))} if any(a.parent == eng for a, _ in moved) else set()),
                   key=lambda ab: -len(ab[0]))

    def rebase(text: str) -> str:
        for a, b in swaps:
            for sa, sb in ((a, b), (a.replace("\\", "/"), b.replace("\\", "/"))):
                text = re.sub(re.escape(sa) + r"(?=$|[\\/\"'\s;,])", lambda _m, sb=sb: sb, text)
        return text

    def walk(v):
        return rebase(v) if isinstance(v, str) else [walk(x) for x in v] if isinstance(v, list) else \
            {k: walk(x) for k, x in v.items()} if isinstance(v, dict) else v
    for _, dst in moved:
        if dst.is_file() and dst.name.startswith("strata-") and dst.suffix == ".json":
            try:
                data = json.loads(dst.read_text(encoding="utf-8-sig"))
                dst.write_text(json.dumps(walk(data), indent=2) + "\n", encoding="utf-8")
            except (OSError, ValueError) as e:
                warn(f"{dst}: the paths in it could not be updated: {e}")
        elif dst.is_file() and dst.name.startswith("run-"):
            try:
                dst.write_bytes(rebase(dst.read_bytes().decode("utf-8", "surrogateescape")).encode("utf-8", "surrogateescape"))
            except OSError as e:
                warn(f"{dst}: the paths in it could not be updated: {e}")
    say(f"  Strata's folders were rearranged in this version: your settings and engine moved from {old} into {ROOT}.")
    return moved

DRAFT_VOCAB_MIB = {"cjk": 348, "cyrillic": 193, "fr": 151, "en": 133, "latin": 203, "arabic": 161}   # the draft head's VRAM per subset (IQ3_S: the largest)

SMALL_CARD_GB = 7.5            # #496: a card under 8 GB gets a tip (an 8 GB card lists 7.99)

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

PARALLEL_MAX = 8               # #465: the engine's batch window holds at most 8 requests

PARALLEL_SHARE = 0.2           # #465: the slots' sessions may take this share of the VRAM the expert cache would hold

PARALLEL_HELD = 0.5            # #465: ... and only where the cache still holds this share of the experts beside them

PARALLEL_COST_NOTE = ("parallel N reduces waiting for several users but costs about 10-25% speed per request on this "
                      "card")

PARALLEL_CELL_BYTES = 1850     # VRAM per context cell beyond 32K a session keeps in any KV mode (QSA indexer rows,

PARALLEL_PIN_SHARE = 0.75      # share of the RAM the expert arena plus every session's pinned K/V may take: measured on

def _parallel_kv_tok(kv: str) -> int:
    # 12 layers: the measured pin (12.38 GiB at 1M int8), not the 13 of kv_streaming_ram_gb
    return 12 * KV_CELL_BYTES.get(kv, 1056)

def parallel_slot_gb(ctx: int, kv: str, streaming: bool) -> float:
    """#465: the VRAM one batch slot's session takes: its KV cache (12 QSA layers; with KV streaming only the 32K
    positions the attention reads stay in VRAM), the DeltaNet state (~0.17 GB) and the per-cell rows every session
    sizes on the whole context.  Measured: 0.56 GiB at 32K int8; with KV streaming, 0.95 GiB at 262K and 2.27 GiB at
    1M (RTX 5090, 15/11/2026)."""
    kv_cells = min(ctx, 32768) if streaming else ctx
    return (kv_cells * _parallel_kv_tok(kv) + max(0, ctx - 32768) * PARALLEL_CELL_BYTES) / 1e9 + 0.17

def parallel_pinned_gb(ctx: int, kv: str) -> float:
    """The RAM one session pins with KV streaming: the host copy of its whole K/V (12.38 GiB at 1M int8, measured).
    The server's own session and every slot each pin one.  Callers apply it only when streaming."""
    return ctx * _parallel_kv_tok(kv) / 1e9

def parallel_ram_fits(n: int, ram_gb: float | None, arena_gb: float, ctx: int, kv: str, streaming: bool) -> bool:
    """Whether the expert arena plus the pinned K/V of the server's session and n slots stay within PARALLEL_PIN_SHARE
    of the RAM (ram_gb is in GiB, the arena and the pins in GB).
    Measured on 125.6 GiB with the 50.3 GB IQ3_S arena at 1M: 8 slots stopped the engine (pinning refused at 99 GiB),
    4 slots started with 8 GiB free and half the arena unpinned, every request 3-4x slower.  ram_gb None: not known."""
    if ram_gb is None or not streaming:
        return True
    pinned_gib = (arena_gb + (n + 1) * parallel_pinned_gb(ctx, kv)) * 1e9 / 2**30
    return pinned_gib <= PARALLEL_PIN_SHARE * ram_gb

def parallel_recommend(vram_gbs, arena_gb: float, ctx: int, kv: str, streaming: bool,
                       ram_gb: float | None = None) -> int:
    """#465: how many requests at once ("parallel") to recommend: 0 = none (one at a time).  Only where the experts
    mostly fit in VRAM - the expert cache (each card's VRAM less ~5 GB, every card of a layer split) still holds
    PARALLEL_HELD of the model's experts beside the slots' sessions, which take at most PARALLEL_SHARE of it, up to 4.
    Where the experts mostly run on the CPU a batch reads about as many experts as the requests one by one and every
    slot's VRAM is expert cache lost: measured on a 12 GB RTX 5070 (Q2_0, 32K), a request alone 11-24% slower with 2-4
    slots, 4 requests together 63 tok/s against 71 one after the other (docs/BATCHING.md).  With KV streaming each
    slot also pins its whole K/V in RAM, so the count must fit there too (parallel_ram_fits)."""
    if isinstance(vram_gbs, (int, float)):
        vram_gbs = [vram_gbs]
    cache_gb = sum(max(0.0, v - 5) for v in vram_gbs)
    slot = parallel_slot_gb(ctx, kv, streaming)
    best = 0
    for n in (2, 3, 4):
        if n * slot <= PARALLEL_SHARE * cache_gb and (cache_gb - n * slot) >= PARALLEL_HELD * arena_gb \
                and parallel_ram_fits(n, ram_gb, arena_gb, ctx, kv, streaming):
            best = n
    return best

def parallel_note(asked: int | None, vram_gbs, arena_gb: float, ctx: int, kv: str, streaming: bool,
                  ram_gb: float | None = None) -> list[str]:
    """#465: what setup says about "parallel": the recommendation (or, where it would cost speed, why it is left at
    one), or how the asked count compares with it (kept as asked: recommend, never force)."""
    rec = parallel_recommend(vram_gbs, arena_gb, ctx, kv, streaming, ram_gb)
    slot = parallel_slot_gb(ctx, kv, streaming)
    pinned = parallel_pinned_gb(ctx, kv) if streaming else 0.0
    ram_bound = rec == 0 and parallel_recommend(vram_gbs, arena_gb, ctx, kv, streaming) >= 2
    ram_words = (f"Each extra request at once would need about {pinned:.1f} GB of RAM at this context length, more than this PC has free "
                 "next to the model")                  # wording approved by the coordinator 11-16 (#6046)
    if asked is None or asked <= 1:
        if not rec:
            if ram_bound:
                return [f"Several requests at once: off (one at a time). {ram_words} (see docs/BATCHING.md)."]
            return [f"Several requests at once: left at one at a time - {PARALLEL_COST_NOTE} (docs/BATCHING.md)."]
        return [f"Several requests at once (opt-in): --parallel {rec} decodes up to {rec} together instead of one "
                f"after the other (each takes ~{slot:.1f} GB of VRAM from the expert cache; docs/BATCHING.md)."]
    lines = [f"parallel requests: {asked} at once (each takes ~{slot:.1f} GB of VRAM from the expert cache, "
             f"{asked * slot:.1f} GB in all" + (f"; each also needs ~{pinned:.1f} GB of RAM" if pinned else "") + ")"]
    if asked > PARALLEL_MAX:
        lines.append(f"the engine runs at most {PARALLEL_MAX} at once; it will use {PARALLEL_MAX}")
    if not rec:
        lines.append(f"recommended for this card: one at a time. {ram_words}; kept as you chose" if ram_bound else
                     f"recommended for this card: one at a time - {PARALLEL_COST_NOTE}; kept as you chose")
    elif asked > rec:
        lines.append(f"recommended for this card: {rec} - more slots leave fewer experts in VRAM, which can make every "
                     "request slower; kept as you chose")
    return lines

PREFILL_BIG_RAM_GB = 96        # bench #433 #440 #834 #669: --prefill auto:32768 +21-35% at 96 GB, ~3x slower at 32 GB

PREFILL_RISK_RAM_GB = 64       # below this an explicit auto:32768 is warned about

HEADROOM_RAM_GB = 48           # bench #834: STRATA_RESIDENT_HEADROOM_GIB=6 on a PC with this much RAM or less

AGENT_CACHE_FREE_GB = 24       # bench #882 #440: RAM left beside the model for the conversation cache

AGENT_CACHE_MIB = 8192

SMALL_VISION_VRAM_GB = 12.5    # bench #469: the GPU image encoder shrinks the prompt chunks on cards up to 12 GB

def arg_after(args, flag):
    """The value after `flag` in an argument list, or None."""
    return args[args.index(flag) + 1] if flag in args[:-1] else None

def bare_auto_is_32768(gpu, args, env) -> bool:
    """Round 0212 (owner 11-03): the engine gives a bare `--prefill auto` a 32768-token ceiling on one NVIDIA card of compute capability 8.0 or up, and on
    7.0 (Volta; include/strata/core/nv_chunk.hpp `nv_chunk_card_ok`, called from generate.cpp); Turing (7.5) and Pascal (6.x) keep 8192.  STRATA_NV_CHUNK=0
    or STRATA_DEFAULTS=026 (the config's env or this process's) keep 8192, and a layer split reads 8192-token chunks.  `gpu` is the one card the config
    runs on (the engine sees only the cards CUDA_VISIBLE_DEVICES names, so for a mixed PC the lowest of those decides, which is this card)."""
    arch = str((gpu or {}).get("arch", ""))
    if not arch.isdigit() or len(arch) < 2:
        return False
    major, minor = int(arch[:-1]), int(arch[-1])     # "70" -> 7.0, "86" -> 8.6, "120" -> 12.0
    if not (major >= 8 or (major == 7 and minor == 0)):
        return False
    if any(a in (args or []) for a in ("--gpus", "--layer-split")):
        return False
    e = dict(env or {})
    nv_chunk = e.get("STRATA_NV_CHUNK", os.environ.get("STRATA_NV_CHUNK"))
    defaults = e.get("STRATA_DEFAULTS", os.environ.get("STRATA_DEFAULTS"))
    if (nv_chunk is not None and str(nv_chunk).startswith(("0", "16"))) or str(defaults) in ("026", "0.2.6", "v0.2.6"):
        return False
    return True

def bench_tips(args, env, ram: float, model_ram_gb: float, vram_gb: float, vision: str, win: bool, gpu=None) -> list[str]:
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
    elif prefill == "auto" and ram >= PREFILL_BIG_RAM_GB and not bare_auto_is_32768(gpu, args, env):   # already the default there (round 0212)
        tips.append(f"tip: with {ram:.0f} GB of RAM, --prefill auto:32768 in the config's args read prompts 21-35% "
                    "faster in community benchmarks (#433 #440 #834); not set, nothing changes")
    resident = any(a in args for a in ("--resident-experts", "--resident-budget-gib"))
    if resident and ram <= HEADROOM_RAM_GB and "STRATA_RESIDENT_HEADROOM_GIB" not in (env or {}):
        tips.append(f"tip: on a PC with {ram:.0f} GB of RAM, \"env\": {{\"STRATA_RESIDENT_HEADROOM_GIB\": \"6\"}} in the "
                    "config kept decode speed in a community benchmark and left the system 2 GiB more (#834); the "
                    "default is 4")
    if vision == "gpu" and 0 < vram_gb <= SMALL_VISION_VRAM_GB:
        tips.append("tip: the image encoder on the GPU makes a prompt's chunks smaller on a card this size (243 vs 750 "
                    "tok/s measured, #469); run setup again with --vision cpu to read prompts ~3x faster, at about "
                    "2-3 s per picture")
    return tips

DISPLAY_RESERVE_MIB = 1500     # #779: the tip for an NVIDIA card that also drives a display

DESKTOP_RESERVE_MIB = 3072     # #560 #516: what kept a KDE/Wayland desktop alive beside a full expert cache

def desktop_reserve_note() -> list[str]:
    """#560 #516: an AMD card that also drives a Linux desktop - with the default 700 MiB reserve the expert cache
    fills it, and when the desktop needs more VRAM amdgpu moves the cache to system RAM, where the OOM killer then ends
    the compositor.  A recommendation, setup changes nothing."""
    return [f"If this AMD card also drives your desktop and the desktop or apps crash once the model is loaded, keep "
            f"more VRAM free: ./setup.sh --vram-reserve-mib {DESKTOP_RESERVE_MIB}",
            "  (remembered for this model; the expert cache gets ~2.3 GB less, a few % of speed)"]

def auto_drafter(a, family: str, fam: dict, model: str, hip: bool, gpu: dict, mtp_here: bool, canonical: bool = False) -> str | None:
    """P14 (0.2.16): the drafter a fresh setup uses when the person named none (no --drafter, no --mtp): the Terminal's Auto rule
    (strata_control/drafting.py choice_of, the one `strata launch` and the app use), not a copy of it. "dflash2" when Auto means DFlash2 on this
    computer and the MTP layer is not on disk yet, so the ~5 GB MTP download is skipped and the 1.2 GB DFlash2 drafter is fetched instead (a P100 got the
    5 GB layer from setup while the Terminal's Auto picks DFlash2 there). None in every other case: the MTP layer is already here (nothing to save), a
    drafter was named, or Auto means the MTP; setup then goes on as before. ``canonical``: step 6 builds the canonical pack (Q2_0 on a CPU with AVX-512), which
    the engine's DFlash2 refuses ("it needs a native pack", #7090): Auto is the MTP then, and the layer is fetched. Never raises."""
    if getattr(a, "drafter", None) or a.mtp is not None or mtp_here:
        return None
    try:
        from strata_control import drafting
        backend, archs = drafting.hardware_for("hip" if hip else "cuda")
        pick = drafting.choice_of("auto", model_name=f"{fam['name']}-{model.lower()}", family=family, backend=backend, archs=archs,
                                  vram_mib=float(gpu.get("vram_gb") or 0) * 1024 or None, canonical=canonical)
        return "dflash2" if pick == "dflash2" else None
    except Exception:                                  # noqa: BLE001 - a rule that cannot be read leaves setup as it was
        return None

def derived_factor(ctx: int, trained: int = 262144) -> float:
    """The automatic extension factor: the FINAL context over the trained one, at least 1.

    Factor 1 removes the automatic expansion - the trained angles stand as they are - but it is not a
    switch for rope as a whole: an explicitly chosen method's settings keep their defined behavior.
    """
    return max(1.0, float(ctx) / float(trained))

def resolve_rope(ctx: int, scaling, scale, trained: int = 262144):
    """The rope config for the context ACTUALLY SERVED: (scaling, scale); scaling None = no scaling flags.

    An explicit --rope-scaling/--rope-scale always wins - a valid user-supplied factor is kept verbatim even
    when a reduction changed the context.  Past the trained range an omitted method defaults to yarn -
    llama.cpp's extension method: the trained angles survive on the high-frequency pairs and the
    magnitude correction keeps the attention temperature - and an omitted factor is derived from the
    final context (final / trained, at least 1), as is an explicitly chosen method's missing factor
    inside the trained range: factor 1, the trained angles, no expansion.  An explicit none is refused
    past the trained range (the setup will not configure a run it knows is out of spec) rather than
    silently overridden.
    """
    if scale is not None and (not math.isfinite(scale) or scale < 1.0):
        raise ValueError("--rope-scale must be a finite value >= 1, e.g. --rope-scale 4")
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

def pool_workers_note(args, layout=None) -> list[str]:
    """A plain warning when the config's `--pool-workers` is above what this CPU uses well.  Recommend, never force: the
    count stays as it is and the engine runs with it."""
    if "--pool-workers" not in args:
        return []
    try:
        asked = int(args[args.index("--pool-workers") + 1])
    except (IndexError, ValueError):
        return []
    hybrid = cpu_cores() if layout is None else None
    logical, cores = layout or cpu_core_layout()
    rec = plan_pool_workers(logical, cores, hybrid=hybrid)
    if asked <= rec:
        return []
    why = ("more than this PC has CPU threads" if asked + 1 > logical else
           "more than its physical cores" if cores and asked + 1 > sum(cores) else
           "more than the cores of one CPU socket" if len(cores) > 1 and asked + 1 > cores[0] else
           "more than the memory bandwidth can feed")
    return [f"the config asks for {asked} CPU expert workers, {why}: extra workers can make Strata slower. Recommended: "
            f"--pool-workers {rec} (or remove the setting: the engine picks that by itself). It stays as you set it."]


def main() -> int:
    try:                                               # the engine programs setup runs start no debugger on a user's machine (strata_control/childenv.py)
        from strata_control.childenv import quiet_crash_env
        quiet_crash_env()
    except Exception:
        pass
    try:                                               # files made by a run as administrator still belong to the user
        from strata_control import private_files as _pf
        _pf.adopt_user_defaults()
    except Exception:
        pass
    _peek = lambda flag: next((v.split("=", 1)[1] if v.startswith(flag + "=") else sys.argv[i + 2] if i + 2 < len(sys.argv) else None   # noqa: E731
                               for i, v in enumerate(sys.argv[1:]) if v == flag or v.startswith(flag + "=")), None)
    from strata_control import retired
    if retired.is_name(_peek("--family")) or (_peek("--model") and retired.is_name(_peek("--model"))
                                              and (not _peek("--family") or retired.is_name(_peek("--family")))):
        say("  " + retired.NOT_OFFERED)                # DeepSeek: no longer offered (strata_control/retired.py)
        return 2
    _hy4_ask = _peek("--family") in HY4_FAMILIES or bool(_peek("--model") and model_alias(_peek("--model")) in HY4_FAMILIES["hy4-flash"]["models"])
    _ink_ask = _peek("--family") in INKLING_FAMILIES or bool(_peek("--model") and model_alias(_peek("--model")) in INKLING_FAMILIES["inkling-2-mini"]["models"])
    if sys.platform == "darwin" and not CONTROL and not _hy4_ask and not _ink_ask:       # a Mac: metal/setup_mac.py (the Metal engine); the app (Control mode), Hy4-Flash and Inkling-2-Mini go on below.
        return mac_setup(sys.argv[1:])                 # (after the retired names above, so a Mac gets the same sentence and exit 2, M1 11-16)
    if (_peek("--family") and _peek("--family") not in {**FAMILIES, **OWN_PATH_FAMILIES, **HY4_FAMILIES, **INKLING_FAMILIES}) \
            or (_peek("--model") and not _peek("--family") and model_alias(_peek("--model")) not in MODELS
                and not any(model_alias(_peek("--model")) in f["models"] for f in {**OWN_PATH_FAMILIES, **HY4_FAMILIES, **INKLING_FAMILIES}.values())):
        feed_models_setup(_peek("--feed"))             # a name the built-in tables do not know may be a model of the signed feed
        if _peek("--family") in FEED_UNAVAILABLE:
            fail(f"{FEED_UNAVAILABLE[_peek('--family')]['title']} is {FEED_UNAVAILABLE[_peek('--family')]['reason']}")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", choices=list(FAMILIES) + list(PREVIEW_FAMILIES) + list(HY4_FAMILIES) + list(INKLING_FAMILIES),
                    help="qwen = Qwen3.8-Flash-Next, swift = Swift 1.5, qwen36 = Qwen3.6-35B-A3B (pictures with --vision, "
                         "several requests at once with --parallel; docs/QWEN36.md), hy4-flash = Tencent Hy4-Flash (SQ-64 / SQ-96 / SQ-128), "
                         "inkling-2-mini = Thinking Machines Inkling-2-Mini (SQ-20 / SQ-15 / SQ-10)")
    ap.add_argument("--model", type=model_alias, choices=list(dict.fromkeys([*MODELS, *(m for f in PREVIEW_FAMILIES.values()
                                                                       for m in f["models"]), *(m for f in HY4_FAMILIES.values() for m in f["models"]),
                                                                       *(m for f in INKLING_FAMILIES.values() for m in f["models"])])))
    ap.add_argument("--context", type=int)
    ap.add_argument("--rope-scaling", choices=["none", "linear", "yarn"],
                    help="the RoPE extension for a context past the model's trained 262144: linear (position "
                         "interpolation) or yarn - llama.cpp's types. Omitted with a scaled context, the setup "
                         "picks yarn; 'none' is refused for such a context")
    ap.add_argument("--rope-scale", type=float,
                    help="the extension factor, finite and >= 1 (default: the final context over the trained "
                         "262144, at least 1 - 1.5 for 384K, 2 for 512K, 1 inside the trained range)")
    ap.add_argument("--kv", choices=["int8", "q4_0", "k8v4", "fp16", "fp8", "k8v8"],
                    help="KV cache precision above 8K context: int8 (default), q4_0 (half the memory, a little less "
                         "precise) k8v4 (hybrid: INT8 K + 4-bit V, 816 B/cell) or fp16 (16-bit, twice the memory of int8)")
    ap.add_argument("--vision", choices=["yes", "no", "none", "gpu", "cpu"],
                    help="let the model read images (on by default where the model can; yes = the best reader for this card: the CPU "
                         "under 24 GB of VRAM, the GPU from 24 GB, any make; gpu / cpu = that reader; no = text only)")
    ap.add_argument("--vision-tokens", type=int, metavar="N",
                    help="the most image tokens a picture becomes (default 1024 with the encoder on the GPU, 300 on "
                         "the CPU): more reads small text and charts better, and takes longer to encode; remembered "
                         "for this model")
    # image generation (Qwen-Image): in preview, not offered in setup or --help; the options still work (docs/IMAGES.md)
    ap.add_argument("--images", choices=["qwen-image", "no"],
                    help=argparse.SUPPRESS)
    ap.add_argument("--image-quant", choices=["Q4_K_M", "Q6_K", "Q8_0"],
                    help=argparse.SUPPRESS)
    ap.add_argument("--image-backend", choices=["cuda", "hip", "vulkan", "cpu"],
                    help=argparse.SUPPRESS)
    ap.add_argument("--image-native", choices=["on", "off"],
                    help=argparse.SUPPRESS)
    ap.add_argument("--image-noise", choices=["on", "off"],
                    help=argparse.SUPPRESS)
    ap.add_argument("--image-vae", choices=["on", "off"],
                    help=argparse.SUPPRESS)
    ap.add_argument("--image-gpu-policy", choices=["auto", "keep", "shrink", "unload"],
                    help=argparse.SUPPRESS)
    ap.add_argument("--experimental-speed-projection", metavar="on|off|GGUF",
                    help="EXPERIMENTAL, off by default: the control vector in data/experimental-speed-projection "
                         "(or another GGUF) as a projection on layers 4-44; see docs/DETAILS.md")
    ap.add_argument("--port", type=int, help="the server's port (default: the one the install was set up with, 8080 for a new one)")
    ap.add_argument("--gpu", help="one GPU, numbered as nvidia-smi numbers them (AMD: as setup lists them) (default: asked when several can be "
                                  "used; with --setup it is saved, when starting it is for that start only)")
    ap.add_argument("--gpus", help="several GPUs sharing one model, as nvidia-smi numbers them (AMD: as setup lists "
                                   "them): \"0,2\", or \"all\" (every card that can); Strata puts the faster card last, "
                                   "and the last card is the Main one. Saved, also when starting (see docs/MULTI_GPU.md)")
    ap.add_argument("--gpu-roles", metavar="LIST", help="a role for each GPU: main, helper or off, e.g. 1=main,0=helper (cards you do not "
                                                        "name are off). Main does the last steps of every answer. Saved (docs/MULTI_GPU.md)")
    ap.add_argument("--layer-split", help="with --gpus: where each later GPU's layers start (\"18\", \"16,32\"), one "
                                          "rising number per GPU after the first - not layers per card; default "
                                          "auto, placed from each GPU's free VRAM")
    ap.add_argument("--no-remote-expert-opt", action="store_true",
                    help="with two or more GPUs: leave out --remote-expert-opt, which setup adds there (#578)")
    ap.add_argument("--host", help="where the server listens: 127.0.0.1 = this PC only (default), 0.0.0.0 = all IPv4 "
                                   "interfaces, :: = all IPv6 interfaces (issue #26; an --api-key is recommended)")
    ap.add_argument("--api-key", help="require this key from clients (recommended with --host 0.0.0.0 or --host ::); "
                                      "several keys: key1,key2")
    ap.add_argument("--no-browser", dest="browser", action="store_false", default=None,
                    help="do not open the chat page in the browser when the model is ready (for a harness or an app "
                         "that uses the API; remembered for this model, also in run-<model>.bat/.sh)")
    ap.add_argument("--browser", dest="browser", action="store_true",
                    help="open the chat page again when the model is ready (the default; undoes --no-browser)")
    ap.add_argument("--data-dir", help="where the model files go (~70-120 GB): default Strata-data next to this folder, "
                                       "remembered for every Strata folder on this PC")
    ap.add_argument("--move-data", action="store_true",
                    help="with --data-dir: move the model files already on this PC into the new folder (without it nothing "
                         "is moved: the old files stay usable and the new folder gets the new downloads)")
    ap.add_argument("--set-default-data-dir", action="store_true",
                    help="with --data-dir: remember the new folder as the data folder without moving anything")
    ap.add_argument("--models-dir", help="where the GGUF files go (default: <data folder>/models)")
    ap.add_argument("--dsv41-package", metavar="FILE", help=argparse.SUPPRESS)      # DeepSeek's: answered with retired.NOT_OFFERED
    ap.add_argument("--feed", metavar="URL|DIR",
                    help="where the signed update feed is: default STRATA_UPDATE_FEED, a remembered https feed, "
                         "or the release's (as `strata update --feed`; a folder is a local test feed)")
    ap.add_argument("--gguf-dir", help="use GGUF files you already have (a folder with every shard: "
                                       "<name>-00001-of-0000N.gguf ... -0000N-of-0000N.gguf)")
    ap.add_argument("--yes", action="store_true", help="accept the recommended answers")
    ap.add_argument("--setup", action="store_true", help="install another model or change settings")
    ap.add_argument("--no-start", action="store_true", help="install only, do not start the model")
    ap.add_argument("--output", choices=("human", "jsonl"), default="human",
                    help="jsonl: one JSON object per line on stdout (step, ok, warning, progress, error, done) for a program that installs "
                         "a model; the usual text goes to stderr. Use it with --yes --no-start")
    ap.add_argument("--update", action="store_true",
                    help="update the installed engine, Python packages and model settings as a start would, without "
                         "starting the model; in a git clone it gets the newest code first (git pull)")
    ap.add_argument("--rollback-engine", action="store_true",
                    help="put back the engine an update replaced (kept in engine/.previous), and keep the current one there")
    ap.add_argument("--build", action="store_true", help="compile the engine instead of using the ready-made one")
    ap.add_argument("--source", choices=SOURCES, default=None,
                    help="where the model files come from: auto (default: Hugging Face), huggingface or modelscope "
                         "(mainland China: the same files, checked against ModelScope's published SHA-256; "
                         "STRATA_SOURCE)")
    ap.add_argument("--prepare-pack", metavar="PACK_DIR",
                    help="only build the pack of the GGUF files in --gguf-dir into PACK_DIR (what `strata launch` runs for an Intel Arc card): "
                         "fetches llama.cpp's gguf-py by itself, runs tools/iq_pack.py, changes nothing else")
    ap.add_argument("--inspect", nargs="+", metavar=("SOURCE", "VARIANT"),
                    help="what a GGUF is and whether Strata runs it, from its headers only (no download): a file, a "
                         "folder, a URL, ms:owner/repo (ModelScope) or hf:owner/repo, and optionally a variant name")
    ap.add_argument("--cuda", choices=["12", "13", "auto"], default=os.environ.get("STRATA_CUDA") or None,
                    help="NVIDIA: the CUDA toolkit of this model's engine. auto (default): CUDA 13, the ready-made "
                         "engine; CUDA 12 (experimental) when a chosen card is older than CUDA 13 supports (Pascal, "
                         "Volta). 12 also runs with an older driver (Windows 528+, Linux 525+). docs/OLDER_GPUS.md")
    ap.add_argument("--prebuilt", default=os.environ.get("STRATA_PREBUILT_URL", PREBUILT_URL),
                    help="where the ready-made engine is (a URL folder or a local folder)")
    ap.add_argument("--check", action="store_true", help="only check this PC and exit")
    ap.add_argument("--calibrate", action="store_true",
                    help="tune the engine's settings for this PC (about 15-30 minutes, longer on a slow card), then start the model")
    ap.add_argument("--draft-vocab", choices=list(DRAFT_VOCABS),
                    help="the draft layer's tokens: cjk = with Chinese, Japanese and Korean (default), en = English "
                         "and code only (~110 MiB less VRAM, English answers 1-2%% faster), cyrillic = English, code "
                         "and the Cyrillic script (Russian: 26%% more tokens a second), fr = English, "
                         "code and French (French answers: 18%% more drafts accepted), latin = English, code and "
                         "the Latin-script languages (German, Spanish, French, Polish: 8-12%% more tokens a "
                         "second). Without this setting Strata picks cyrillic or latin by itself from the "
                         "languages of this computer, and keeps the default when one of them is Chinese, "
                         "Japanese or Korean")
    ap.add_argument("--low-ram", choices=["auto", "on", "off", "resident", "mmap"], default="auto",
                    help="read the model's experts from one file in its folder instead of copying them all into RAM "
                         "(for a PC with a big GPU and little RAM); auto: when the experts would not fit the RAM. In "
                         "this mode the experts the GPU does not hold are copied into RAM once when they fit (resident), "
                         "else read through the OS file cache (mmap); resident / mmap force one of the two")
    ap.add_argument("--resident-budget-gib", type=float, metavar="N",
                    help="UD-Q4_K_XL, UD-IQ4_XS: the GiB of its experts kept in RAM (default: the RAM less 17 GB, 47 on 64 GB; "
                         "more is kept as you choose, with a note)")
    ap.add_argument("--vram-reserve-mib", type=int, metavar="N",
                    help="VRAM in MiB the engine leaves free for other programs (a game, another model; the engine's "
                         "default: 700); the expert cache takes that much less")
    ap.add_argument("--peer-reserve-mib", type=int, metavar="N",
                    help="Qwen3.6-35B-A3B on two GPUs (--gpus): VRAM in MiB the second-card expert tier (--peer-device) "
                         "leaves free there (the engine's default: 600)")
    ap.add_argument("--mtp", choices=["on", "off"],
                    help="the draft layer (MTP): off starts the model without it, which frees about 1 GB of graphics memory "
                         "for the expert cache and takes less RAM, at the price of speed; it is kept in the run config "
                         "(\"mtp\": false) and a later setup run does not undo it. on: back to the default")
    ap.add_argument("--drafter", choices=["mtp", "dflash2", "dfly2", "dspark", "off"],
                    help="which drafter this model will use. dflash2: the MTP draft layer's ~5 GB are not downloaded (the DFlash2 drafter is fetched by `strata drafting fetch`); "
                         "the arguments keep the --mtp folder so a later switch to the MTP works. mtp (the default): the draft layer is fetched as before. Nothing is written about it "
                         "in the run config: the choice is its \"drafting\" key")
    ap.add_argument("--parallel", type=int, metavar="N",
                    help="up to N requests decode together (batch slots, opt-in; default: one at a time, the others "
                         "wait). Each slot takes VRAM from the expert cache; setup says what it recommends")
    ap.add_argument("--replicas", type=int, metavar="N",
                    help="several GPUs: run N independent engines, each on its own equal group of the chosen cards (2 "
                         "replicas on 4 cards = two 2-card engines), requests spread over them (opt-in; more total "
                         "throughput for a model that fits fewer cards; each replica holds its own copy of the model)")
    ap.add_argument("--replica-profile", action="store_true", default=False,
                    help="two or more GPUs, Qwen3.8 IQ3_S/IQ3_XXS/Q2_0: one engine per card behind the server instead of one "
                         "layer split, the experts shared in RAM, the batch switches on (opt-in; about 1.8 times the "
                         "throughput at 8-16 requests at once on 4 Radeon AI PRO R9700; needs about 61 GB of RAM for 2 "
                         "engines and 66 GB for 4; a layer split you chose, replicas or --parallel always win)")
    ap.add_argument("--kv-streaming", choices=["auto", "on", "off"], default="auto",
                    help="from a 64K context: keep the KV cache in RAM and only the attention's window in VRAM (more "
                         "experts fit on the GPU); auto: when the RAM has room for it")
    ap.add_argument("--backend", choices=["cuda", "hip", "sycl"],
                    help="cuda = NVIDIA (default), hip = AMD RX 7900 / 7800 / 7700 XT, RX 9060 XT / 9070 / AI PRO R9700 on "
                         "Linux or Windows (chosen by itself when the PC has no NVIDIA card Strata can use), "
                         "sycl = Intel Arc, EXPERIMENTAL: Linux, built from source (docs/INTEL_ARC.md)")
    ap.add_argument("--skip-build", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.output == "jsonl":
        jsonl_start()
    move_over_old_layout()                             # a clone's first run after its pull to the 0.2.16 layout (Q7)
    if a.update:                                       # Q6: the newest code first (UPDATE.bat / update.sh did the git pull before 0.2.16)
        pulled = update_pull(sys.argv[1:])
        if pulled is not None:
            return pulled
    if getattr(a, "gguf_dir", None):                   # the person's own files: their finish marks go to Strata's marks/, never beside them
        own_files_in(a.gguf_dir)
    if getattr(a, "dsv41_package", None):              # DeepSeek's engine package: no longer offered (strata_control/retired.py)
        say("  " + retired.NOT_OFFERED)
        return 2
    if a.model and a.model not in MODELS and a.family not in PREVIEW_FAMILIES and a.family not in HY4_FAMILIES and a.family not in INKLING_FAMILIES:
        ap.error(f"--model {a.model} is a size of " + ", ".join(f"--family {f}" for f, d in {**PREVIEW_FAMILIES, **HY4_FAMILIES, **INKLING_FAMILIES}.items()
                                                              if a.model in d["models"]))
    if a.source:
        os.environ["STRATA_SOURCE"] = a.source
    if a.prepare_pack:                                 # an Intel Arc card: the model's pack, nothing else (no engine, no download of the model)
        return prepare_pack_only(a)
    if a.inspect:                                      # headers only: nothing is installed
        sys.exit(subprocess.run([sys.executable, str(ROOT / "tools" / "strata_inspect.py"), *a.inspect[:2]]).returncode)
    if sys.platform == "darwin":
        if a.family in HY4_FAMILIES or (not a.family and a.model in HY4_FAMILIES["hy4-flash"]["models"]):
            return mac_hy4_setup(a)
        if a.family in INKLING_FAMILIES or (not a.family and a.model in INKLING_FAMILIES["inkling-2-mini"]["models"]):
            return mac_inkling_setup(a)
        if CONTROL:           # the app on a Mac: model files only; the Metal engine is a component
            return mac_control_setup(a)
    if a.backend == "sycl":                            # Intel Arc: the app / Terminal's installer mode prepares the files and writes the config; a checkout builds from source
        if CONTROL:
            return intel_control_setup(a)
        return sycl_setup(sys.argv[1:])
    if a.resident_budget_gib is not None and not a.resident_budget_gib > 0:
        ap.error("--resident-budget-gib takes a number of GiB above 0, e.g. --resident-budget-gib 32")
    if a.vision_tokens is not None and a.vision_tokens < 1:
        ap.error("--vision-tokens takes a number of image tokens, 1 or more, e.g. --vision-tokens 768")
    if a.vram_reserve_mib is not None and a.vram_reserve_mib < 0:
        ap.error("--vram-reserve-mib takes a number of MiB, 0 or more, e.g. --vram-reserve-mib 2048")
    if a.gpu is not None:                             # --gpu 0,2 means --gpus 0,2 (a user tried it: issue report)
        if "," in a.gpu:
            a.gpus, a.gpu = a.gpus or a.gpu, None
        elif a.gpu.strip().isdigit():
            a.gpu = int(a.gpu)
        else:
            ap.error(f"--gpu takes a GPU number as nvidia-smi numbers them, e.g. --gpu 1 (or --gpus 0,2), not {a.gpu!r}")
    a._roles = None
    if a.gpu_roles:
        if a.gpu is not None or a.gpus:
            ap.error("use --gpu-roles (a role for each card) or --gpu / --gpus (which cards), not both")
        from strata_control import gpu_roles as GR
        try:
            named = GR.parse_roles(a.gpu_roles)
        except ValueError as e:
            ap.error(f"--gpu-roles: {e}")
        on = [i for i, r in named.items() if r != "off"]
        if not on:
            ap.error("--gpu-roles: setup needs at least one card that is Main or Helper")
        mains = [i for i, r in named.items() if r == "main"] or [sorted(on)[-1]]
        helpers = sorted(i for i in on if i != mains[0])
        a._roles_explicit = True
        a._roles = {**{i: "off" for i in named}, **{i: "helper" for i in helpers}, mains[0]: "main"}
        order = helpers + [mains[0]]
        if len(order) > 1:
            a.gpus = ",".join(str(i) for i in order)
        else:
            a.gpu = order[0]
    _fams = {**OWN_PATH_FAMILIES, **HY4_FAMILIES, **INKLING_FAMILIES}
    say("Strata - " + (_fams[a.family]["title"] if a.family in _fams else "Qwen3.8-Flash-Next")
        + " on a normal PC (a GPU + system RAM + CPU)")
    have = installed_configs()
    if a.update or not (a.setup or a.model or a.family or a.check or a.no_start or a.calibrate or a.rollback_engine):
        from strata_control import retired
        for c in retired_configs():                    # DeepSeek: named, left as it is
            say("  " + retired.left_as_is(retired.title(None, c)))
    # A plain start of an installed model finds everything where it already is: it creates, moves and copies nothing
    # (the model paths are in the run config; the data folder is the one settings.json remembers).  Setting up, checking,
    # tuning and updating look for and gather the model files (data_folder).
    plain_start = bool(have) and not (a.setup or a.model or a.family or a.check or a.no_start or a.update
                                      or a.calibrate or a.rollback_engine or a.data_dir)
    models_dir_given = a.models_dir is not None
    data, elsewhere = data_folder_in_place() if plain_start else data_folder_for(a)   # the model files
    roots = [data, *elsewhere]
    if a.models_dir is None:
        a.models_dir = str(data / "models")

    if a.rollback_engine:                              # #670
        return rollback_engine(12 if a.cuda == "12" else 13)

    # ---- 0. already installed: just start it
    if a.update:                                       # #475: START-HERE.bat --update / ./setup.sh --update - never starts the model
        return update_install(have, a)
    explicit = a.setup or a.model or a.family or a.check or a.no_start
    adopted = None                                     # #629: the earlier install this copy is set up like
    if not have and not explicit:                      # a new copy of Strata (an update unzipped elsewhere): set it
        prev = previous_config(elsewhere, load_settings())   # up like the last one, from the files already here
        if prev is not None:
            ch = choices_from_config(prev)
            if ch["model"]:
                say(f"  Found your earlier install in {prev.parent} ({prev.stem[len('strata-'):]}): setting up this "
                    "copy the same way - the model files are reused, nothing big is downloaded.")
                a.family, a.model, a.context = ch["family"], ch["model"], a.context or ch["context"]
                adopted = prev
                a.kv = a.kv or ch["kv"]
                a.vision = a.vision or ch["vision"]
                a.experimental_speed_projection = a.experimental_speed_projection or ch["esp"]
                a.host, a.api_key = a.host or ch["host"], a.api_key or ch["api_key"]
                a.port = a.port or ch["port"]
                if a.vram_reserve_mib is None:          # #493: an explicit reserve set up before
                    a.vram_reserve_mib = ch.get("vram_reserve_mib")
                if a.cuda is None and ch.get("cuda") == 12:   # the experimental CUDA 12 engine, as before
                    a.cuda = "12"
                if isinstance(ch.get("gpu"), list):     # a layer split: set up across the same cards again
                    a.gpus = a.gpus or ",".join(str(g) for g in ch["gpu"])
                    a.layer_split = a.layer_split or ch.get("layer_split")
                else:
                    a.gpu = a.gpu if a.gpu is not None else ch.get("gpu")
                a.yes = True
    global GPU_PICK, OLD_GPUS
    # starting an installed model: --gpus 0,2 (or all) saves those cards for it and starts on them (it used to start
    # on the first one alone unless given with --setup), --gpu N runs this start on one card; neither: the saved
    # choice, and asked once when the PC has cards that could share the model
    run_gpu = start_gpus(a.gpus) or a.gpu
    port = a.port or 8080                              # a new install's port (issue #32: --port for an existing one)
    if a.calibrate and (a.setup or a.check or not have):    # #2036: said, not dropped
        why = ("--setup" if a.setup else "--check" if a.check else "no model is installed yet")
        warn(f"--calibrate does nothing with {why}: it tunes a model that is already installed. Run setup first, "
             "then " + ("START-HERE.bat" if WIN else "./setup.sh") + " --calibrate [--model NAME]")
    if have and not (a.setup or a.check) and (a.calibrate or not (a.model or a.family or a.no_start)):
        given = [f for f, v in (("--kv", a.kv), ("--context", a.context), ("--vision", a.vision)) if v is not None]
        if given:                                      # said, not dropped (as --calibrate above, #2036)
            warn(f"{', '.join(given)} only apply when a model is set up: this start keeps its saved settings. To "
                 "change them: " + ("START-HERE.bat" if WIN else "./setup.sh") + " --setup --model NAME "
                 + " ".join(given) + " ...")
    if have and a.calibrate and not (a.setup or a.check):
        targets = calibration_targets(have, a.model, a.family)
        if not targets:                                # #2036: --model names a model that is not installed
            names = ", ".join(sorted({choices_from_config(c)["model"] or c.stem for c in have}))
            fail(f"--calibrate: {a.model or a.family} is not installed (installed: {names})",
                 "calibrate an installed model, or set this one up first without --calibrate")
        have = targets
        engine_update_note()
        pick_cfg = have[0]
        if len(have) > 1:
            say()
            for i, c in enumerate(have, 1):
                say(f"  {i}) {json.loads(c.read_text(encoding='utf-8-sig')).get('model_name', c.stem)}")
            pick_cfg = have[int(ask("Tune which one?", [str(i) for i in range(1, len(have) + 1)], "1", a.yes)) - 1]
        if not calibrate_config(pick_cfg):             # #447: said again where it is not lost above the start
            say()
            warn("this PC is NOT tuned: the tuning failed (the reason is above); the model "
                 + ("keeps" if a.no_start else "starts with") + " the default settings")
        return 0 if a.no_start else start(pick_cfg, a.port, run_gpu, yes=a.yes, layer_split=a.layer_split,
                     keep={"host": a.host, "api_key": a.api_key, "draft_vocab": a.draft_vocab,
                           "vram_reserve_mib": a.vram_reserve_mib, "open_browser": a.browser})
    if have and not (a.setup or a.model or a.family or a.check or a.no_start):
        engine_update_note()
        if len(have) == 1:
            return start(have[0], a.port, run_gpu, yes=a.yes, layer_split=a.layer_split,
                     keep={"host": a.host, "api_key": a.api_key, "draft_vocab": a.draft_vocab,
                           "vram_reserve_mib": a.vram_reserve_mib, "open_browser": a.browser})
        say()
        for i, c in enumerate(have, 1):
            say(f"  {i}) {json.loads(c.read_text(encoding='utf-8-sig')).get('model_name', c.stem)}")
        say(f"  {len(have) + 1}) install another model / change settings")
        pick = int(ask("Which one?", [str(i) for i in range(1, len(have) + 2)], "1", a.yes))
        if pick <= len(have):
            return start(have[pick - 1], a.port, run_gpu, yes=a.yes, layer_split=a.layer_split,
                     keep={"host": a.host, "api_key": a.api_key, "draft_vocab": a.draft_vocab,
                           "vram_reserve_mib": a.vram_reserve_mib, "open_browser": a.browser})
        data, elsewhere = data_folder_for(a)      # "install another model": now the model files are gathered
        roots = [data, *elsewhere]
        if not models_dir_given:
            a.models_dir = str(data / "models")

    # ---- 1. the PC
    step(1, "checking your PC")
    found = gpus()
    amd = amd_gpus()
    amd_ok = [g for g in amd if amd_problem(g) is None]
    # older NVIDIA GPUs (Pascal / Volta): the experimental CUDA 12 engine, when chosen (docs/OLDER_GPUS.md)
    OLD_GPUS = OLD_GPUS or old_gpus_opt_in(found, named_gpus(a.gpu, a.gpus), a.cuda,
                                           other=bool(amd_ok) or a.backend == "hip")
    if OLD_GPUS and a.backend != "hip":
        warn(f"older NVIDIA GPUs (Pascal / Volta) can be used ({OLD_GPUS}): experimental, through a second engine "
             "built with CUDA 12 (docs/OLDER_GPUS.md)")
    nv_ok = any(gpu_problem(g) is None for g in found)
    if not nv_ok and not amd_ok and a.backend != "hip" and maxwell_note(found):    # #3218: a warning with the way forward
        warn(maxwell_note(found))
    hip = a.backend == "hip" or (a.backend is None and not nv_ok and bool(amd_ok))
    if a.backend is None and nv_ok and amd_ok:
        # both kinds of card: asked (a first run on such a PC used to take NVIDIA without mentioning the Radeon)
        say()
        say("  This PC has NVIDIA and AMD cards Strata can use:")
        say("  1) NVIDIA: " + ", ".join(f"{g['name']} ({g['vram_gb']:.0f} GB)" for g in found if gpu_problem(g) is None)
            + "   (recommended)")
        say("  2) AMD: " + ", ".join(f"{g['name']} ({g['vram_gb']:.0f} GB{', unified memory' if g.get('uma') else ''})"
                               for g in amd_ok)
            + f"   ({'the ready-made AMD engine' if WIN else 'compiled here'}, pictures on"
              " - docs/AMD_HIP.md)")
        say("  One engine drives the cards of one make: a model is never split across NVIDIA and AMD cards, and two models at the same")
        say("  time, one on each, is not supported yet.")
        from strata_control import gpu_fit
        bigger = gpu_fit.other_vendor_note([{**g, "vendor": "nvidia", "usable": gpu_problem(g) is None} for g in found] +
                                           [{**g, "vendor": "amd", "usable": True} for g in amd_ok], "nvidia")
        if bigger:
            say("  " + bigger)
        hip = ask("Which cards?", ["1", "2"], "1", a.yes or a.check) == "2"
        if a.check and not hip:
            say(f"  (the AMD card: {'START-HERE.bat' if WIN else './setup.sh'} --backend hip)")
    cuda_tk = 13                                       # NVIDIA: the toolkit of this model's engine (cuda_choice)
    if hip:                                            # AMD: compiled here; Windows: ready-made
        say("  Your AMD GPUs:" if amd else "  No AMD GPU found (" + ("Windows lists no AMD display adapter)." if WIN
                                                                   else "the amdgpu driver's KFD topology is empty)."))
        for g in amd:
            say(f"    GPU {g['index']}: {g['name']}, {amd_mem_text(g)} - " + (amd_problem(g) or "can be used"))
        if not WIN:                                    # WSL: the Linux HIP engines hang there; a warning, the run goes on
            from strata_control.engine_component import wsl_amd_note
            wsl_note = wsl_amd_note("hip", wsl=is_wsl())
            if wsl_note:
                warn(wsl_note)
        usable = [g for g in amd if amd_problem(g) is None]
        if not WIN and (amd or amd_pci_devices()):     # a warning only: recommend, never force
            acc = amd_device_access_problem()
            if acc:
                warn(acc)
        if not amd and not WIN:                        # the KFD topology is empty: name a Strix Halo the kernel sees
            for d in amd_pci_devices():
                if d["pci_id"] in STRIX_HALO_PCI_IDS:
                    say(f"    The kernel lists an AMD Strix Halo (PCI 1002:{d['pci_id']:04x}) but /dev/kfd's topology is "
                        "empty: ROCm cannot use it yet (docs/STRIX_HALO.md: the amdgpu driver and /dev/kfd access, "
                        "your user in the render and video groups)")
        if not usable:
            fail("no AMD GPU Strata can use", f"the AMD backend runs on {AMD_CARDS}")
        if a.gpus:                                     # a layer split / expert-parallel across these cards (roles: Main is last)
            chosen = amd_parse_gpus(a.gpus, amd)
            gpu = chosen[-1] if getattr(a, "_roles", None) else chosen[0]
        elif a.gpu is not None:
            gpu = next((g for g in usable if g["index"] == a.gpu), None)
            if gpu is None:
                fail(f"AMD GPU {a.gpu} cannot be used", "use one of: " + ", ".join(f"--gpu {g['index']}" for g in usable))
            chosen = [gpu]
        else:
            gpu = min(usable, key=amd_rank)            # a discrete card before an APU, then the most memory
            chosen = [gpu]
            if len(usable) > 1 and any(g.get("uma") for g in usable) != all(g.get("uma") for g in usable):
                others = [g for g in usable if g is not gpu]
                say(f"  Using GPU {gpu['index']} ({gpu['name']}); setup recommends the card with its own memory over "
                    "the APU's shared memory. To use another: "
                    + ", ".join(f"--gpu {g['index']} ({g['name']})" for g in others))
        # the engine is compiled for every chosen card's architecture
        gpu = {**gpu, "count": len(amd), "archs": sorted({g["arch"] for g in chosen})}
        chosen = [gpu if g["index"] == gpu["index"] else g for g in chosen]
        sel = [g["index"] for g in chosen]
        multi = sel if len(sel) > 1 else []
        a.gpu = gpu["index"] if len(amd) > 1 else a.gpu
        if multi:
            ok("GPUs: " + " + ".join(gpu_name(x) for x in chosen) + " together (the model's layers are split across them)")
        ok(f"GPU: {gpu['name']}, {amd_mem_text(gpu) if gpu.get('uma') else format(gpu['vram_gb'], '.1f') + ' GB VRAM'}, "
           f"{gpu['arch']} (AMD: docs/{'STRIX_HALO' if is_strix_halo(gpu) else 'AMD_HIP'}.md)")
        if WIN and str(gpu.get("arch") or "").startswith("gfx12"):   # only a pointer; no default changes
            say("  If Windows resets the AMD driver (VIDEO_ENGINE_TIMEOUT_DETECTED, flicker, the engine dies mid-answer): "
                "docs/TROUBLESHOOTING.md, \"Windows AMD: the driver resets\"")
        if gpu.get("uma"):
            for line in igpu_notes(gpu, ram_gb()):
                (warn if line.startswith("!") else say)(line.lstrip("!"))
        for line in unused_apu_notes(chosen, amd, ram_gb()):
            (warn if line.startswith("!") else say)(line.lstrip("!"))
        for line in rdna2_notes(gpu):
            say(line)
    else:
        if not found:
            fail("no NVIDIA GPU found (nvidia-smi did not answer)",
                 "install the NVIDIA driver from https://www.nvidia.com/drivers and restart the PC"
                 + (f"; AMD ({', '.join(AMD_ARCHS)}): --backend hip" if amd else ""))
        if len(found) > 1 or gpu_problem(found[0]) is not None:
            gpu_table(found)
        sel = choose_gpus(a, found)                    # asked when two or more cards can share the model
        multi = sel if len(sel) > 1 else []
        a.gpu = sel[-1] if getattr(a, "_roles", None) else sel[0]   # the main GPU: the checks and the sizing below are its (roles: Main is last)
        GPU_PICK = a.gpu
        gpu = gpu_info(a.gpu)
        chosen = [gpu_info(i) for i in sel]
        gpu["archs"] = sorted({x["arch"] for x in chosen})  # the engine needs code for every one of them
        if multi:
            ok("GPUs: " + " + ".join(gpu_name(x) for x in chosen) + " together (the model's layers are split across them)")
        ok(f"GPU: {gpu['name']}, " + (f"unified memory ({gpu['vram_gb']:.0f} GB usable by the GPU)" if gpu.get("uma") else f"{gpu['vram_gb']:.1f} GB VRAM")
           + f", compute capability {cc(gpu)}, driver {gpu['driver']}")
        cuda_tk, why = cuda_choice(gpu["archs"], a.cuda, driver_major(gpu))   # one engine per model: its oldest card decides
        if why:
            (warn if cuda_tk == 13 or str(a.cuda) == "12" else ok)(f"CUDA {cuda_tk}: {why}")
        min_driver = CUDA12_COMPAT_DRIVER if cuda_tk == 12 else MIN_DRIVER
        if driver_major(gpu) < min_driver:
            fail(f"the NVIDIA driver is too old ({gpu['driver']}; {min_driver} or newer is needed)"
                 + ("" if cuda_tk == 12 else f" (the CUDA 12 engine package needs {cuda12_min_driver()[1]} or newer, {cuda12_min_driver()[2]})"),
                 "update it with the NVIDIA App or from https://www.nvidia.com/drivers, restart, and run this again")
        if cuda_tk == 12:
            cuda12_min_driver(feed=True)                   # the CUDA 12 package's driver floor: the installed package, else the signed feed (#4247)
            if note := cuda12_driver_warning(driver_major(gpu)):
                warn(note)
    if gpu["vram_gb"] < 11:
        warn("less than 12 GB of " + ("GPU memory (this APU's carve-out + shared memory)" if gpu.get("uma") else "VRAM")
             + ": Strata will run, but most experts stay on the CPU and it will be slow")
    ram = ram_gb()
    cpu, avx2, avx512 = cpu_info()
    need = min(d["ram_gb"] for d in MODELS.values() if not d.get("mem_total"))   # Gyro counts VRAM + RAM: not a RAM floor
    low_ok = low_ram_fits("IQ1_M", ram, low_ram_vram(gpu)) and a.low_ram != "off"   # the smallest model, mapped
    if ram < need - 4 and not a.check and not low_ok:
        # every model keeps ALL its experts in RAM (23+ GB); VRAM only holds a copy of the most-used ones, so a
        # bigger GPU does not lower this.  The owner's rule: a stop by default, a risk the user can take (--model
        # with --yes, or y)
        confirm_risk(f"RAM: {ram:.0f} GB - the smallest model (the Coder) needs about {need} GB: Strata keeps all of "
                     "the model's experts in RAM (23-50 GB, whatever the GPU), so the OS will page them from disk. "
                     "Expect it to be very slow, and it may not start at all.", bool(a.model), a.yes,
                     f"RAM: {ram:.0f} GB - the smallest model (the Coder) needs about {need} GB",
                     "Strata keeps all of the model's experts in RAM (23-50 GB, whatever the GPU) and the GPU holds a "
                     "copy of the most-used ones: it needs 32 GB of RAM or more (48 GB for the full model); --model "
                     "NAME --yes installs one anyway")
        warn(f"going on with {ram:.0f} GB of RAM, as you chose")
    ram_msg = (f"RAM: {ram:.0f} GB" if ram >= need - 4 else f"RAM: {ram:.0f} GB (less than the {need} GB the smallest model needs)"
               + ("; the GPU's VRAM makes up for it (the low-RAM mode)" if ram < need - 4 and low_ok else ""))
    (ok if ram >= need - 4 or low_ok else warn)(ram_msg)       # #977: a RAM below every model's floor is not [ok]
    pf = page_file_gb()
    if pf is not None and pf < 4:
        warn(page_file_advice(pf, page_file_setting()))
    ok(f"CPU: {cpu} ({'ARM64' if is_arm64() else 'AVX-512' if avx512 else 'AVX2' if avx2 else 'no AVX2'})")
    # (a unified-memory GPU - a DGX Spark's GB10 - is on the CPU's own link, not PCIe: nvidia-smi's "1.0 x1" there means nothing)
    link = None if hip or gpu.get("uma") else pcie_link(int(gpu.get("index", 0)))
    if link is not None:
        line, problem = pcie_lines(link)
        ok(line)
        if problem:
            warn(problem)
    floor = cpu_floor(avx2)
    if floor == "unsupported":
        fail("this CPU has neither AVX2 nor SSE4.2; Strata needs at least SSE4.2 (Intel Nehalem, 2008, or newer)")
    if is_arm64():
        # DGX Spark / GB10 (#3622): the engine is the linux-aarch64 package of the signed feed when the release has one, else compiled here
        # (spark/build_engine.sh). A warning, not a stop.
        warn("ARM64 CPU (a DGX Spark): the CPU's share of the experts runs on ggml-cpu's NEON kernels. Tested: Qwen3.8-Flash-Next IQ3_S and "
             "the NVFP4 pack, on one DGX Spark (GB10). The Q2_0 and Gyro packs need the x86 kernels and do not "
             "run on this CPU")
    elif not avx2:
        # #394 #595 #623: the ready-made engine is AVX2; an older CPU gets one compiled here, whose CPU experts run on
        # ggml-cpu's kernels for this CPU.  Experimental: measured only on newer CPUs with the older path forced, and by
        # users on a few Xeons.  A warning, not a stop.
        warn(f"this CPU has no AVX2: Strata support for it is EXPERIMENTAL and slow. Setup compiles the engine on this "
             f"PC for {'AVX' if floor == 'avx' else 'SSE4.2'} (STRATA_ISA_FLOOR={floor}; 10-20 minutes, once), and the "
             "CPU's share of the experts runs on ggml-cpu's kernels, a few times slower than on an AVX2 CPU. "
             "See \"Older CPUs\" in docs/INSTALL.md")
        if hip and WIN:
            fail("the older-CPU engine is compiled from source, and setup compiles the AMD engine on Linux only",
                 "use Linux for an AMD card on this CPU, or an NVIDIA card")
        a.build = True
    if a.check:
        say()
        any_fits = False
        for m, d in MODELS.items():
            verdict = ("EXPERIMENTAL, " if d.get("experimental") else "") + model_fit_label(m, ram, gpu)
            if d.get("budget") and hip and d.get("nvidia_only"):   # #429: not run on AMD yet
                verdict += " - NVIDIA only so far, untested on AMD"
            if hip and d.get("repo"):                  # the ready-made NVFP4 packs: no AMD kernels at all
                verdict = "NVIDIA only (the AMD engine has no NVFP4 kernels)"
            else:
                any_fits = any_fits or (model_fit_label(m, ram, gpu) == "fits" and not d.get("mem_total"))
            say(f"  {m:8s} needs ~{model_files_gb(m):.0f} GB of RAM + VRAM: {verdict}")
        if not any_fits:
            # #977: every size says "does not fit", so the verdict says so too (and the exit code, for scripts). It only
            # reports: --model NAME --yes still installs one anyway.
            say(f"\nThis PC cannot run Strata yet: no model size fits {ram:.0f} GB of RAM (the smallest needs about "
                f"{need} GB). --model NAME --yes installs one anyway, slowly.")
            return 1
        say("\nThis PC can run Strata. Run it again without --check to install.")
        return 0

    # ---- 2. the questions
    step(2, "your choices")
    if a.gguf_dir and not (a.family and a.model):     # P13: the files in --gguf-dir name the model: nothing to ask when they name exactly one
        named = gguf_dir_choices(Path(a.gguf_dir), a.family, a.model)
        if len(named) == 1:
            a.family, a.model = named[0]
            say(f"  The files in {a.gguf_dir} are {FAMILIES[a.family]['title']} {a.model}: using them (no question to answer).")
    if not a.family and not a.yes and FEED_MODELS is None:
        feed_models_setup(getattr(a, "feed", None))    # the signed feed's models, listed after the built-in ones (nothing happens when it has none)
    fams = menu_families(hip)
    feed_late = [f for f in fams if FAMILIES[f].get("feed")]       # models of the signed feed come last in the list (none: nothing here changes)
    fams = [f for f in fams if f not in feed_late]
    if a.family:
        family = a.family
    else:
        tier = tier_pick(ram, low_ram_vram(gpu))
        cyan, reset = menu_colour("36")
        rec_fam = STRIX_HALO_FAMILY if strix_halo_recommends(gpu, ram) and STRIX_HALO_FAMILY in fams else             tier[0] if tier and tier[0] in fams else fams[0]
        for i, f in enumerate(fams, 1):
            d = FAMILIES[f]
            say(f"  {i}) {cyan}{d['title']:20s}{reset} {d['by']} - {d['about']}" + ("   [experimental]" if d.get("experimental") else "")
                + family_menu_note(f, hip, gpu, avx2, avx512)
                + (f"   (recommended for Strix Halo: {STRIX_HALO_MODEL})" if f == rec_fam and rec_fam != fams[0] else ""))
        rest = [*(f for f in OWN_PATH_FAMILIES if not OWN_PATH_FAMILIES[f].get("feed")),
                *(f for f in OWN_PATH_FAMILIES if OWN_PATH_FAMILIES[f].get("feed")), *feed_late,
                *(f for f in HY4_FAMILIES if hy4_offered(a)),
                *(f for f in INKLING_FAMILIES if inkling_offered(a))]
        for j, f in enumerate(rest, len(fams) + 1):    # families with an engine path of their own
            d = {**FAMILIES, **OWN_PATH_FAMILIES, **HY4_FAMILIES, **INKLING_FAMILIES}[f]
            say(f"  {j}) {cyan}{d['title']:20s}{reset} {d['by']} - {d['about']}   [new]" + (f"   ({FEED_UNAVAILABLE[f]['reason']})" if f in FEED_UNAVAILABLE else ""))
        for u in FEED_UNAVAILABLE.values():            # a feed model this engine does not run: said, never offered (unless the owner's rule allows it, above)
            if not u.get("allowed"):
                say(f"  -) {u['title']:20s} {u['by']} - {u['reason']}")
        allf = fams + rest
        if tier_note(ram, low_ram_vram(gpu)) and rec_fam == "swift":
            say("  " + tier_note(ram, low_ram_vram(gpu)))
        family = allf[int(ask("Which model?", [str(i) for i in range(1, len(allf) + 1)],
                              str(allf.index(rec_fam) + 1), a.yes)) - 1]
    if family in OWN_PATH_FAMILIES:                    # Qwen3.6: its own engine path, its own steps 2-7
        return install_own_path(a, family, gpu, hip, amd, cuda_tk, multi, port, ram, adopted)
    if family in HY4_FAMILIES:                         # Hy4-Flash: its own engine program (strata-hy4), its own files, its own steps 2-7
        return install_hy4_flash(a, family, gpu, hip, amd, cuda_tk, multi, port, ram, adopted)
    if family in INKLING_FAMILIES:                     # Inkling-2-Mini: its own engine program (strata-inkling), its own files, its own steps 2-7
        return install_inkling2(a, family, gpu, hip, amd, cuda_tk, multi, port, ram, adopted)
    fam = FAMILIES[family]
    SHAPE_ENGINE.clear()
    if fam.get("shape"):                               # a feed model of its own shape: its own engine component (strata_control/shape_engine.py)
        SHAPE_ENGINE["shape"], SHAPE_ENGINE["title"] = fam["shape"], fam.get("title")
    if fam.get("ready") and hip:
        # not a risk the user could take: the HIP engine has no NVFP4 expert kernels at all, so it would not start
        fail(f"{fam['title']} runs on NVIDIA cards only: the AMD engine has no NVFP4 kernels",
             "UD-IQ4_XS is about the same size and runs on AMD: --family unsloth --model UD-IQ4_XS")
    if fam.get("ready") and a.gguf_dir:
        warn(f"--gguf-dir does not apply to {fam['title']}: its files are ready-made packs, not GGUF shards")
        a.gguf_dir = None
    ok(f"model: {fam['title']}")
    if fam.get("feed") and fam.get("drafter") == "none" and a.mtp is None:
        a.mtp = "off"                                  # the feed says this model has no draft layer: the Flash-Next one (fetched below for every qwen4exp model) is not its own
        a.feed_no_drafter = True                       # and no drafter at its starts either: the run config says "drafting": "off" (setup_config; APP-LIN 0.2.14)
        say("  The model list says this model has no draft layer (MTP), so none is fetched or used.")
    if fam.get("ready") and nvfp4_cpu_note(avx2, avx512):   # #2347: a note (the AVX2 rows work), not a refusal
        warn(nvfp4_cpu_note(avx2, avx512))
    if fam.get("license"):
        say(f"  Its license: {fam['license']}")
    say()
    names = [m for m in MODELS if family in MODELS[m].get("families", ("qwen", "swift"))]
    names.sort(key=lambda m: bool(MODELS[m].get("experimental")))   # an experimental size last, never the default
    if a.model and a.model not in names:
        # #444: say which family has that size, and (with --gguf-dir) which files Strata can run at all
        elsewhere_fams = [f for f in FAMILIES if f in MODELS[a.model].get("families", ("qwen", "swift"))]
        fail(f"{fam['title']} has no {a.model} model file", "choose one of: " + ", ".join(names)
             + (f" (or {a.model}: " + ", ".join(f"--family {f} --model {a.model}" for f in elsewhere_fams) + ")"
                if elsewhere_fams else "")
             + (f".\n       {SUPPORTED_GGUFS}" if a.gguf_dir else ""))
    installed = installed_size(family, names, have)
    for i, m in enumerate(names, 1):
        d = MODELS[m]
        fit = f"   <- {model_fit_label(m, ram, gpu)}"          # "fits" or "may run slower": the weight files against the RAM and the card's memory together
        if d.get("mem_total"):             # Gyro: the download includes the n-gram table, the memory figure does not
            say(f"  {i}) {m}{size_tag(family, m, installed)} {d['about']}; download {d['download_gb']:.1f} GB "
                f"(the n-gram table is in the file), memory {d['ram_gb']} GB{fit}")
            continue
        if d.get("budget"):
            keeps = (f"~{resident_budget_gib(m, ram, uma=bool((gpu or {}).get('uma')))} GB" if unsloth_budget(m, ram, gpu, a.resident_budget_gib)
                     else "all")
            say(f"  {i}) {m}{size_tag(family, m, installed)} {d['about']}; download {d['download_gb']:.0f} GB, keeps {keeps} of its "
                f"{d['arena_gb']:.0f} GB of experts in RAM{fit}")
            continue
        magenta, reset = menu_colour("35")
        label = f"{magenta}{m:8s}{reset}"
        say(f"  {i}) {label}{size_tag(family, m, installed)} {d['about']}; download {d['download_gb']:.0f} GB, uses ~{d['arena_gb']:.0f} GB of RAM{fit}")
    rec = str(names.index(installed or recommended_size(family, names, ram, low_ram_vram(gpu))) + 1)
    model = a.model or names[int(ask("Which size?", [str(i) for i in range(1, len(names) + 1)], rec, a.yes)) - 1]
    budget, q4_split = None, False
    in_budget = bool(MODELS[model].get("budget")) and unsloth_budget(model, ram, gpu, a.resident_budget_gib)
    if MODELS[model].get("budget"):
        # Unsloth's files: every expert in RAM where they fit with UNSLOTH_RESIDENT_BESIDE_GB beside them (Phase 2,
        # unsloth_budget), as ISTA's.  Else a RAM budget of experts, the rest from the GGUF on the SSD - not the low-RAM
        # mode (no experts.bin: it would be another 77 GB on the disk), and one GPU (the budget mode had no layer split)
        # unless the RAM holds the GGUFs and 24 GB more: then several, without the budget, if asked for (#498).  #642:
        # from RESIDENT_SPLIT_ENGINE several GPUs, when asked for, keep the budget (unsloth_together)
        if MODELS[model].get("experimental"):
            warn(f"{model} is EXPERIMENTAL (docs/UNSLOTH_Q4.md)" + (
                 ": most of its experts are read from the SSD while it answers, so it is several times slower than the "
                 "2-3-bit models" if in_budget else "") + "; quality checked against llama.cpp")
        if hip and MODELS[model].get("nvidia_only"):
            # #429 (jkuepker): checked before the 111 GB download.  The HIP engine has no prompt kernels for its
            # Q4_K / Q5_K experts and it has not been run on AMD: asked, not refused
            confirm_risk(f"{model} has not been run on AMD cards yet: its prompt kernels are NVIDIA-only, so on "
                         f"{gpu_name(gpu)} long prompts read much more slowly, and it may not work at all",
                         bool(a.model), a.yes, f"{model} is NVIDIA-only so far", "choose one of the 2-3-bit models, "
                         f"or --model {model} --yes to try it on AMD anyway", "  Try it anyway?")
            warn(f"installing {model} on an AMD card, as you chose (please report how it runs)")
        if ram < MODELS[model]["ram_gb"] and model_fit_label(model, ram, gpu) != "fits":
            have = resident_budget_gib(model, ram, uma=bool((gpu or {}).get("uma")))
            total = int(MODELS[model]["arena_gb"] / 1.073741824)
            confirm_risk(f"{model} needs {MODELS[model]['ram_gb']} GB of RAM or more; this PC has {ram:.0f} GB: "
                         f"it would keep {have} GiB of its {total} GiB of experts in RAM and read the other "
                         f"{total - have} GiB from the SSD while it answers (single-digit tokens/s on most SSDs), and "
                         "it may run out of RAM", bool(a.model), a.yes,
                         f"{model} needs {MODELS[model]['ram_gb']} GB of RAM or more; this PC has {ram:.0f} GB",
                         f"choose a smaller size, or --model {model} --yes to install it anyway", "  Install it anyway?")
            warn(f"installing {model} with {ram:.0f} GB of RAM, as you chose")
        if in_budget:
            budget = budget_choice(model, ram, a.resident_budget_gib, uma=bool((gpu or {}).get("uma")))
            if multi and not unsloth_together(a, model, ram, fallback_card(a, gpu, chosen), chosen):
                gpu = fallback_card(a, gpu, chosen)
                multi, sel, chosen = [], [gpu["index"]], [gpu]
            q4_split = bool(multi) and not resident_split()   # #498: on several GPUs without the RAM budget (#642: kept)
            if not q4_split:
                ok(f"RAM budget: {budget:g} GiB of {model}'s experts in RAM, the rest read from the model files on the SSD")
        else:
            ok(f"all {MODELS[model]['arena_gb']:.0f} GB of {model}'s experts in RAM (they and "
               f"{UNSLOTH_RESIDENT_BESIDE_GB} GiB more fit this PC's {ram:.0f} GB; --resident-budget-gib N keeps only "
               "N GiB of them)")
        if a.low_ram not in ("auto", "off"):
            warn(f"--low-ram {a.low_ram} does not apply to {model}: it always reads part of its experts from the files")
    elif a.resident_budget_gib is not None:
        warn(f"--resident-budget-gib is for UD-Q4_K_XL and UD-IQ4_XS: {model} keeps all of its experts in RAM or in "
             "the low-RAM mode")
    low_ram = low_ram_wanted(model, ram, a.low_ram)
    # #642: the engines from RESIDENT_SPLIT_ENGINE run the low-RAM mode on the chosen cards as on one (decided below)
    if low_ram and multi and not resident_split() and not low_ram_together(a, model, ram, fallback_card(a, gpu, chosen), chosen):
        gpu = fallback_card(a, gpu, chosen)
        multi, sel, chosen = [], [gpu["index"]], [gpu]
    # (the low-RAM mode's variant is decided once the context is known, below; on several GPUs it is the mapped one
    # before RESIDENT_SPLIT_ENGINE, #642)
    if MODELS[model].get("mem_total"):
        if mem_have(model, ram, gpu["vram_gb"]) < MODELS[model]["ram_gb"]:   # recommend, never force: a warning
            warn(f"{model} needs {MODELS[model]['ram_gb']} GB of VRAM and RAM together; this PC has "
                 f"{mem_have(model, ram, gpu['vram_gb']):.0f} GB ({ram:.0f} GB RAM + {gpu['vram_gb']:.0f} GB VRAM): it "
                 "may be slow, run out of memory or not start")
    elif not low_ram and budget is None and ram < MODELS[model]["ram_gb"] - 4:
        confirm_paging(model, ram, a.low_ram, a.yes, bool(a.model))
    ok(f"size: {model}")
    from strata_control import gpu_fit
    _q4 = gpu_fit.strix_q4_stall_note(model, [gpu] if isinstance(gpu, dict) else (gpu or []))   # REMOVE with the Strix stall fix (see gpu_fit.STRIX_Q4_NOTE)
    if _q4:
        warn(_q4)
    if MODELS[model].get("license"):                   # the ready-made packs: each size has its own license
        say(f"  Its license: {MODELS[model]['license']}")
    tag = fam["tag"] + model                           # names of the pack, config and start script
    small = min(x["vram_gb"] for x in chosen)         # each card keeps its layers' KV of the whole context
    rec_ctx = 131072                                   # 128K on every card (owner, 2026-11-01); a card it leaves little room on is warned about below, never lowered
    # #406: the RAM rule is part of the recommendation (the smaller of the two), no longer a cap over the user's choice
    rec_ctx = min(rec_ctx, ram_ctx(model, ram, low_ram))
    if a.context:
        ctx = a.context
    else:
        say()
        say("  Context length = how much text the model can see at once (your chat, files, tool output).")
        say("  Longer needs more VRAM for it, so fewer experts fit on the GPU:")
        for i, c in enumerate(CONTEXTS, 1):
            need_c = ctx_ram_need(model, c, low_ram)
            note = ("   (recommended for your GPU)" if c == rec_ctx else "") + \
                   ("   (experimental: setup adds rope scaling)" if c > 262144 else "") + \
                   (f"   (needs ~{need_c:.0f} GB RAM, this PC has {ram:.0f}: may run out of memory)"
                    if c > 131072 and need_c is not None and need_c > ram else "")
            say(f"  {i}) {c // 1024}K tokens{note}")
        ctx = CONTEXTS[int(ask("Context?", [str(i) for i in range(1, len(CONTEXTS) + 1)],
                               str(CONTEXTS.index(rec_ctx) + 1), a.yes)) - 1]
    # #406 #364: a context past the RAM rule (an explicit --context, a pick in the list, or the earlier install's) is
    # kept, with what it risks.  It used to become 128K: users ran 256K fine where setup's estimate said no.
    need_gb = ctx_ram_need(model, ctx, low_ram)
    if need_gb is not None and ram < need_gb and ctx > 131072:
        warn(f"{ctx // 1024}K with {model} needs ~{need_gb:.0f} GB of RAM by setup's estimate "
             f"({MODELS[model]['arena_gb']:.0f} GB of experts + the context + room for the rest); this PC has "
             f"{ram:.0f}. Kept as you chose: it may be slower or run out of RAM under load. {rec_ctx // 1024}K is the "
             "recommended size.")
    scaling = a.rope_scaling
    if ctx > 262144 and scaling is None and not a.yes:
        # the interactive path: one question, yarn preselected (llama.cpp's extension method, recall-tested
        # here at 512K).  With --yes nothing prints: resolve_rope takes yarn below and the ok() line says so.
        say()
        say(f"  A {ctx // 1024}K context runs the model past its trained 262,144 positions: the rotary angles")
        say("  get rescaled (llama.cpp's RoPE extension). yarn keeps the trained angles on the high-frequency")
        say("  pairs and corrects the magnitudes; linear shrinks every angle. Override any time with")
        say("  --rope-scaling.")
        scaling = ask("RoPE extension method?", ["yarn", "linear"], "yarn", a.yes)
    try:
        scaling, rope_scale = resolve_rope(ctx, scaling, a.rope_scale)
    except ValueError as e:
        fail(str(e))
    if scaling is not None:
        origin = ("final context / trained 262144; override with --rope-scale" if a.rope_scale is None
                  else "as requested")
        ok(f"rope scaling: {scaling}, factor {rope_scale:g} ({origin})")
    ok(f"context: {ctx} tokens")
    # the KV cache (the model's memory of the conversation): 8-bit, or 4-bit after a Hadamard rotation (PR #21).
    # Track 6A + #6354: default to int8 KV on <= 12.5 GB GPUs (all models), on <= 16.5 GB GPUs (all Unsloth quants at
    # any context: avoids 21-23% 16K/32K prompt slowdown and preserves 400+ VRAM expert slots), and on <= 24.5 GB GPUs
    # at >= 64K context.
    _vram_kv = float((gpu or {}).get("vram_gb") or 0.0)
    _is_unsloth_kv = bool(MODELS.get(model, {}).get("budget"))
    _low_vram_kv = (0 < _vram_kv <= 12.5) or (_is_unsloth_kv and ((0 < _vram_kv <= 16.5) or (0 < _vram_kv <= 24.5 and ctx >= 65536)))
    kv = (a.kv or "int8") if (ctx > 8192 or _low_vram_kv) else (a.kv or "fp16")
    if ctx > 8192 and not a.kv and not a.yes:
        say()
        say("  KV cache precision (the model's memory of the conversation):")
        say("  1) 8-bit   (recommended: what every published number was measured with)")
        say("  2) 4-bit   half the memory (about 4% faster at 128K), but measurably less precise on long")
        say("             documents; long-context lookups (needle tests) still pass")
        kv = ["int8", "q4_0"][int(ask("KV cache?", ["1", "2"], "1", a.yes)) - 1]
    if ctx > 8192:
        ok(f"KV cache: {KV_WORDS.get(kv, kv)}")
    if MODELS[model].get("vision", fam.get("vision")) is False:     # UD-IQ4_XS: images, unlike UD-Q4_K_XL
        vision = "none"
        if a.vision not in (None, "no", "none"):
            warn(f"images are not available with {model} yet: off")
    elif hip:
        # Unsloth's files on AMD: pictures on by default, the reader by the 24 GB rule (hip_vision; docs/QUANTS.md)
        vision = hip_vision(a.vision if a.vision is not None or not images_default(model, family, ram, gpu)
                            else "yes", float((gpu or {}).get("vram_gb") or 0.0))
    elif a.vision:
        vision = flash_vision_encoder(a.vision, gpu) if a.vision != "no" else "none"
        vision = "none" if vision in ("no", "none") else vision
    else:
        small = 0 < float(gpu.get("vram_gb") or 0.0) < IMAGES_GPU_ENCODER_MIN_VRAM_GB
        say()
        say("  Images: the model can also read pictures (screenshots, photos, scanned pages). This adds a 0.9 GB")
        if small:
            say("  download. On a card under 24 GB the encoder runs on the CPU (a few seconds per picture, nothing taken")
            say("  from the GPU, pictures read at up to 300 tokens; --vision-tokens 1024 for more detail): the GPU")
            say("  encoder keeps ~1.4 GB of VRAM free, which costs 3-5% of text speed on 16 GB cards (measured) and")
            say("  more on some PCs. --vision gpu if you want pictures in under a second.")
        else:
            say("  download and keeps ~1.4 GB of VRAM free for the image encoder, so text is a few % slower.")
        # on by default wherever the model can read pictures (the reader by the 24 GB rule)
        default = "y" if images_default(model, family, ram, gpu) else "n"
        vision = flash_vision_encoder("yes", gpu) if ask("Do you want images?", ["y", "n"], default, a.yes) == "y" else "none"
    ok("images: " + {"none": "off", "gpu": "on", "cpu": "on (encoder on the CPU)"}[vision])
    if vision != "none" and MODELS[model].get("vision_untested"):
        warn(f"images with {model} are untested: users report them working, but we have not run this file with "
             "images (#967); tell us if the answers look wrong")
    # The low-RAM mode's two variants.  resident: the experts the GPU's cache does not hold (and, as far as RAM allows,
    # the ones the prompt path borrows cache room from) are copied from the pack's experts.bin into RAM once, so
    # nothing is read from the SSD while it answers (engine 0.1.30, --resident-experts; the engine falls back to mmap
    # with a warning when they do not fit the RAM it finds free).  mmap: they are read through the OS file cache.
    # The GPU's share: its VRAM less the dense weights and buffers, this context's KV cache and the image encoder's room.
    resident = False
    if low_ram and not fam.get("ready"):               # NVFP4's packs: the RAM-budget mode instead (step 7)
        arena = MODELS[model]["arena_gb"]
        vram = low_ram_vram(gpu) - (VISION[vision]["reserve_mib"] / 1024 if vision != "none" else 0)
        with_mtp = a.mtp != "off"                       # the draft layer's ~1 GB comes out of the expert cache
        share = low_ram_gpu_share(model, vram, ctx, kv, with_mtp)
        rest = arena - low_ram_gpu_gb(model, vram, ctx, kv, with_mtp)
        resident = a.low_ram == "resident" or (a.low_ram != "mmap" and low_ram_resident(model, ram, vram, ctx, kv, with_mtp))
        if multi:      # every chosen card's share (the image encoder on the main one); #364 #384: the mapped variant
            held = min(arena, low_ram_gpu_gb(model, vram, ctx, kv, with_mtp) +
                       sum(low_ram_gpu_gb(model, low_ram_vram(x), ctx, kv, with_mtp) for x in chosen[1:]))
            share, rest = held / arena, arena - held
            # #642: the resident variant on a split, by the same rule as on one card - what no card holds fits the RAM
            resident = resident_split() and (a.low_ram == "resident" or
                                             (a.low_ram != "mmap" and ram >= rest + LOW_RAM_HEADROOM_GB))
            if resident:
                ok(f"low-RAM mode on {len(chosen)} GPUs: they hold ~{100 * share:.0f}% of {model}'s experts "
                   f"({arena:.0f} GB) and the other ~{rest:.0f} GB stay in RAM ({ram:.0f} GB), read once from a copy "
                   "in the model folder")
            else:
                ok(f"low-RAM mode on {len(chosen)} GPUs: {model}'s experts ({arena:.0f} GB) are read from the model "
                   f"folder through the OS file cache instead of a copy in RAM ({ram:.0f} GB); the GPUs hold "
                   f"~{100 * share:.0f}% of them")
                if share < 0.6:
                    warn("most of the experts are read from the SSD while it answers: expect it to be much slower "
                         "than with enough RAM (a faster SSD and a smaller size help)")
        elif resident:
            ok(f"low-RAM mode: the GPU holds ~{100 * share:.0f}% of {model}'s experts ({arena:.0f} GB) and the other "
               f"~{rest:.0f} GB stay in RAM ({ram:.0f} GB), read once from a copy in the model folder")
        else:
            ok(f"low-RAM mode: {model}'s experts ({arena:.0f} GB) are read from the model folder through the OS file "
               f"cache instead of a copy in RAM ({ram:.0f} GB); the GPU holds ~{100 * share:.0f}% of them")
            if share < 0.6:
                warn("most of the experts are read from the SSD while it answers: expect it to be much slower than "
                     "with enough RAM (a faster SSD and a smaller size help)")
    # EXPERIMENTAL: the experimental-speed-projection control vector (data/experimental-speed-projection), off unless
    # chosen here; with it loaded, the web app and the API switch it off per request
    esp = None
    esp_choice = (a.experimental_speed_projection or "").strip()
    if family in ("qwen", "coder"):                   # the Coder: the same model's residual stream
        if not esp_choice:
            say()
            say("  EXPERIMENTAL - speed projection: a small control vector applied while the model runs (layers 4-44).")
            say("  It changes how the model answers: its package describes it as a refusal-direction projection (the")
            say("  model declines far fewer requests). Off unless you choose it; when on, the web app can switch it off")
            say("  per chat. Details: data/experimental-speed-projection/README.md")
            esp_choice = "on" if ask("Turn on the experimental speed projection?", ["y", "n"], "n", a.yes) == "y" else "off"
        if esp_choice.lower() not in ("off", "no", "n", "0"):
            esp = ESP_VECTOR if esp_choice.lower() in ("on", "yes", "y", "1") else Path(esp_choice).expanduser().resolve()
            if not esp.is_file():
                fail(f"the experimental speed projection's vector is missing: {esp}")
        ok("experimental speed projection: " + ("ON (experimental)" if esp else "off"))
    elif esp_choice.lower() not in ("", "off", "no", "n", "0"):
        warn("the experimental speed projection is made for the original Qwen3.8-Flash-Next, not Swift 1.5: left off"
             if family == "swift" else f"the experimental speed projection is not tested with {model}: left off")
    ready = bool(fam.get("ready"))                     # NVFP4: ready-made packs (NVFP4_REPOS), no GGUF shards
    if ready:
        models_dir = Path(a.models_dir)
        for r in elsewhere:                            # already downloaded and checked in a Strata folder elsewhere
            if all(ready_verified(ready_where(r / "models", f), f[5]) for f in ready_needed(model, r / "models")):
                models_dir = r / "models"
                ok(f"model files found in {models_dir}")
                break
        shards = [ready_where(models_dir, f) for f in ready_files(model)]
    else:
        models_dir = Path(a.gguf_dir) if a.gguf_dir else Path(a.models_dir) / tag
        shards = gguf_dir_shards(models_dir, fam, model) if a.gguf_dir else \
            [models_dir / model_file(fam, model, i) for i in range(1, model_shards(fam, model) + 1)]
    problem = gguf_dir_problem(models_dir, shards[0], fam, model) if a.gguf_dir else None
    if problem:                                        # #444: files Strata cannot run, or another choice's files
        fail(*problem)
    if not ready and not a.gguf_dir and not all(sh.exists() and done(sh) for sh in shards):
        for r in elsewhere:                            # already downloaded in a Strata folder on another drive
            cand = [r / "models" / tag / sh.name for sh in shards]
            if all(c.exists() and done(c) for c in cand):
                models_dir, shards = cand[0].parent, cand
                ok(f"model files found in {models_dir}")
                break
    mark_whole_unless_pinned([] if ready else shards, model_hf(fam, model) if fam.get("hf") else None, bool(a.gguf_dir))   # #173: a whole file copied in by hand has no finish mark
    have_model = all(ready_verified(ready_where(models_dir, f), f[5]) for f in ready_needed(model, models_dir)) if ready else \
        all(s.exists() and (done(s) or a.gguf_dir) for s in shards)
    # #425 (jctaborda): a download that resumes needs room only for what is still missing - the finished shards and
    # the .part files already on the disk count
    on_disk = sum(f.stat().st_size for s in shards for f in (s, s.with_name(s.name + ".part")) if f.is_file()) / 1e9
    to_fetch = 0 if a.gguf_dir or have_model else max(MODELS[model]["download_gb"] - on_disk, 0)
    if ready and not have_model and MODELS[model].get("prepare") and prepared_done(model, models_dir):
        to_fetch = sum(f[4] for f in ready_needed(model, models_dir)
                       if not ready_verified(ready_where(models_dir, f), f[5])) / 1e9   # the small files only
    # count only what step 6 will still write: a pack whose experts.bin is already there (the AVX-512 Q2_0
    # conversion, or the low-RAM mode's copy) and an existing MTP draft layer need no new room
    pack_now = find_in(roots, f"packs/{tag.lower()}") or data / "packs" / tag.lower()
    pack_bin = ready or ((pack_now / "experts.bin").exists() and (pack_now / "index.txt").exists())   # ready: in the download
    mtp_have = find_in(roots, "mtp/rt/experts.bin") is not None
    q2_avx = model == "Q2_0" and avx512 and family == "qwen"
    if not ready and (picked := auto_drafter(a, family, fam, model, hip, gpu, mtp_have, canonical=q2_avx)):      # P14: the Terminal's Auto rule, not always the 5 GB layer
        a.drafter, a.drafter_auto = picked, True
    if q2_avx and not ready and getattr(a, "drafter", None) == "dflash2":     # #7090: step 6 builds the canonical pack, which DFlash2 refuses (also when the app or --drafter named it)
        warn("DFlash2 needs a native pack, and the AVX-512 Q2_0 pack of this CPU is not one: the MTP draft layer is used instead")
        a.drafter, a.drafter_auto = None, False
    prep_gb = MODELS[model].get("prepare_gb", 0.0) if ready and MODELS[model].get("prepare") and \
        not prepared_done(model, models_dir) else 0.0
    margin = 2 if mtp_have else 8                      # working room: a guess, not bytes that will be written
    mtp_fetch = 5.2 if (not mtp_have and not ready and a.mtp != "off" and getattr(a, "drafter", None) != "dflash2") else 0.0      # the draft layer's tensors step 6 fetches (strata_control.discovery.MTP_FETCH_GB)
    copy_gb = MODELS[model]["arena_gb"] + 1 if low_ram and not q2_avx and not pack_bin else 0      # the low-RAM mode's copy of the experts (goes to the data folder's packs)
    real = to_fetch + prep_gb + mtp_fetch + \
        (40 if q2_avx and not pack_bin else 0) + (1 if vision != "none" else 0) + copy_gb
    need = real + margin
    free_now = free_gb(models_dir)
    problem = disk_room_problem(models_dir, pack_now, real - copy_gb, copy_gb,
                                (f" ({on_disk:.0f} GB of the model is already there)" if on_disk >= 1 and not have_model else ""))
    if problem:
        fail(*problem, kind="no_space", path=str(models_dir), free_bytes=int(free_now * 1e9), needed_bytes=int(need * 1e9))
    if free_now < need:
        warn(f"little free disk space in {models_dir}: {free_now:.0f} GB free for about {real:.0f} GB of files. "
             "Setup goes on and should fit; free up space if it stops")

    # ---- 3. python packages
    step(3, "Python packages")
    pip_install(runtime_packages(),
                "numpy, jinja2, regex, pyyaml, tqdm, requests, pillow, psutil, textual (the screens)")

    # ---- 4. the engine
    step(4, "the Strata engine")
    llama, eng, meta, lib_dirs, gpu, vision = engine_step(a, gpu, hip, amd, cuda_tk, vision)
    reader = None
    if hip and vision != "none":                       # AMD: the engine folder's reader (GPU, else CPU), settled now the engine is known
        vision, reader = hip_reader(eng, vision, gpu)
    if (ready or family == "gyro") and meta.get("source") != "local" and \
            tuple(int(x) for x in str(meta.get("version", "0")).split(".")[:4] if x.isdigit()) < MODELS[model]["engine"]:
        # a ready-made engine from before NVFP4 / Gyro cannot read these experts: one compiled from this source can
        warn(f"the ready-made engine {meta.get('version')} has no {'NVFP4' if ready else 'Gyro'} experts yet: compiling "
             "the engine from this source")
        eng = build_engine(gpu, vision, a.yes, llama, toolkit=cuda_tk)
        meta = json.loads((eng / "BUILD.json").read_text(encoding="utf-8"))
        lib_dirs = meta.get("lib_dirs") or meta.get("cuda_dirs") or cuda_lib_dirs(cuda_tk)
    engine_ver = tuple(int(x) for x in str(meta.get("version", "0")).split(".")[:4] if x.isdigit())
    need_engine = MODELS[model].get("engine", UNSLOTH_ENGINE)
    # checked before the 94-188 GB download
    if (MODELS[model].get("budget") or family == "gyro") and engine_ver < need_engine:
        fail(f"{model} needs engine {'.'.join(map(str, need_engine))} or newer; this one is {meta.get('version')}",
             "update Strata (or compile the engine with --build) and run setup again")
    ok("engine: the engine component (looked up when the model loads)" if CONTROL else f"engine: {eng / EXE}")

    # ---- 5. the model files
    step(5, f"downloading {fam['title']} {model}")
    if ready:                                          # pinned files of the pack's repository, each SHA-256-checked
        say(f"  The model files go in {models_dir / MODELS[model]['repo'].replace('/', '--')}")
        if model_source() == "modelscope":
            warn("these packs are on Hugging Face only: downloading them from " + hf_endpoint())
        ready_fetch(model, models_dir)
    elif not a.gguf_dir:
        missing = [s.name for s in shards if not (s.exists() and done(s))]
        if missing:                                    # #495: files downloaded by hand go here, or --gguf-dir
            say(f"  The model files go in {models_dir}")
            say(f"  Files you already have: put them here with their original names ({', '.join(missing)}), or use "
                "--gguf-dir <their folder>.")
            if model_source() == "modelscope":
                say(f"  Downloading from ModelScope ({ms_endpoint()}); --source huggingface downloads from Hugging Face")
                warn("ModelScope serves the repositories' current files, not the pinned revisions: each file is checked "
                     "against the SHA-256 ModelScope itself publishes (self-attested); the MTP tensors against the "
                     "pinned checkpoint's own hashes")
            elif hf_endpoint() != HF_DEFAULT:
                say(f"  Downloading from {hf_endpoint()} (HF_ENDPOINT)")
        for s in shards:
            if s.exists() and done(s):
                ok(f"{s.name} already downloaded")
                continue
            # the original's shard 2 is the same file for all its sizes and the Coder: reuse one that is already here
            other = [p for p in Path(a.models_dir).glob("*/Qwen3.8-Flash-Next-GSQ-RCO-*-00002-of-00002.gguf") if done(p)]
            if family in ("qwen", "coder") and s.name.endswith("00002-of-00002.gguf") and other and not s.exists():
                try:
                    os.link(other[0], s)
                    mark(s)
                    ok(f"{s.name} shared with {other[0].parent.name} (identical file)")
                    continue
                except OSError:
                    pass
            download(model_hf(fam, model) + s.name, s)
    if not ready:
        check_shards(shards)
    for s in ([] if ready else shards):                # the Unsloth files: pinned sizes and SHA-256
        if s.name in fam.get("sha256", {}):
            verify_sha256(s, *fam_pin(fam, s), own=bool(a.gguf_dir))
    ok("model files present")
    mmproj = Path(a.models_dir) / fam.get("mmproj", MMPROJ)
    if not mmproj.exists():                            # an earlier install's copy (the same file for every family)
        mmproj = find_in(roots, f"models/{fam.get('mmproj', MMPROJ)}") or mmproj      # a feed model without a picture reader has no fam["mmproj"]
    if vision != "none":
        # the person's own folder (or the one above it) has the pinned picture file: used where it is ('near'); a verified Unsloth mmproj-F16.gguf they
        # already have is used when no pinned file is anywhere ('alt'); else the pinned file is downloaded
        pin = fam.get("mmproj_sha256") or ISTA_FILES.get(fam["mmproj"]) or (None, None)
        kind, mmproj = resolve_reader(fam["mmproj"], mmproj, a.models_dir, roots, a.gguf_dir, pin[0], pin[1])
        if kind == "fetch":
            download(fam["mmproj_hf"] + fam["mmproj"], mmproj, "vision encoder")
        if fam.get("mmproj_sha256") and kind not in ("alt", "renamed"):   # the NVFP4 family pins it by size and SHA-256 too
            verify_sha256(mmproj, *fam["mmproj_sha256"])
        ok(f"vision encoder: {mmproj}" + (" (Unsloth's mmproj-F16.gguf, SHA-256 checked)" if kind == "alt" else " (SHA-256 checked)" if kind == "renamed" else ""))
        if vision == "cpu" and "BF16" in mmproj.name:       # a tip only (recommend, never force; #625)
            say("       tip: on the CPU a Q8_0 copy of this encoder is a third smaller and about as exact (embedding "
                "cosine 0.999 vs BF16); see 'A Q8_0 encoder' in docs/DETAILS.md")

    # ---- 6. the pack and the MTP draft layer
    step(6, "preparing the model for Strata")
    pack = find_in(roots, f"packs/{tag.lower()}") or data / "packs" / tag.lower()
    env = dict(os.environ, **gguf_py_env())
    prepared = bool(ready and MODELS[model].get("prepare"))
    if prepared and not prepared_done(model, models_dir):
        say("  NVIDIA's checkpoint is turned into a Strata pack on this PC (once; 20-40 minutes, reads the 102 GB, writes about")
        say(f"  {MODELS[model]['prepare_gb']:.0f} GB). Nothing of NVIDIA's weights leaves this PC.")
        ensure_nvfp4_local_packages()
        run([sys.executable, str(ROOT / "tools" / "nvfp4_local_pack.py"), "prepare",
             "--model", str(ready_where(models_dir, ("src", MODELS[model]["repo"], "", "", 0, ""))),
             "--out", str(prepared_dir(model, models_dir))], env=env)
        ok("prepared; the downloaded checkpoint is no longer needed and can be deleted to get its 102 GB back: "
           + str(ready_where(models_dir, ("src", MODELS[model]["repo"], "", "", 0, ""))))
    if ready:                                          # the downloaded pack folder is the pack, experts.bin included
        pack = ready_paths(model, models_dir)["pack"]
    elif model == "Q2_0" and avx512 and family == "qwen":
        # the Q2_0 experts repacked for the AVX-512 kernel (the measured speed): a one-time ~40 GB conversion
        if not (pack / "index.txt").exists() or not (pack / "experts.bin").exists():   # index.txt is written last
            say("  Converting the Q2_0 experts for the AVX-512 kernel (one time, ~40 GB written, 2-5 min) ...")
            run([sys.executable, str(ROOT / "tools" / "strata_pack.py"), "build", "--gguf", str(shards[0]),
                 "--out", str(pack), "--skip-hash", "--force"], env=env)   # --force: #634 refuses an occupied pack
            run([sys.executable, str(ROOT / "tools" / "pack_index.py"), "--pack", str(pack)], env=env)
        if not (pack / "tokenizer" / "vocab.json").exists():
            run([sys.executable, str(ROOT / "tools" / "strata_tokenizer.py"), "--gguf", str(shards[0]),
                 "--out", str(pack)], env=env)   # writes <pack>/tokenizer/
    elif not (pack / "native_experts.txt").exists() or not (pack / "tokenizer" / "vocab.json").exists():
        # every tensor as the GGUF stores it; the experts are read from the GGUF at start (seconds to build)
        # (UD-Q4_K_XL: --compat-bf16 - its Q8_0 hyper-connection projections become BF16, the form the engine reads)
        run([sys.executable, str(ROOT / "tools" / "iq_pack.py"), "--gguf", str(shards[0]), "--out", str(pack),
             *fam.get("pack_args", [])], env=env)
    if low_ram and not ready and not (pack / "experts.bin").exists():
        say(f"  Writing the experts into one file for the low-RAM mode (one time, {MODELS[model]['arena_gb']:.0f} GB) ...")
        run([sys.executable, str(ROOT / "tools" / "iq_pack.py"), "--gguf", str(shards[0]), "--out", str(pack),
             "--experts-bin", *fam.get("pack_args", [])], env=env)       # #3193: Gyro needs --compat-bf16 here too
    ok(f"model prepared: {pack}")
    mtp = ready_paths(model, models_dir)["mtp"] if prepared else \
        (find_in(roots, "mtp/rt/experts.bin") or data / "mtp/rt/experts.bin").parent.parent
    rt = mtp / "rt"
    corrupt = (rt / "experts.bin").exists() and not prepared and mtp_corrupt(mtp, env)
    if corrupt:
        warn("some MTP tensors are not the checkpoint's (a download mirror that ignored range requests, #327): "
             "fetching them again and rebuilding the draft layer")
    if getattr(a, "drafter_auto", False) and not (rt / "experts.bin").exists() and not fetch_dflash2_drafter(data, fam, model, hip, gpu):
        a.drafter = None                               # P14: the DFlash2 drafter could not be had: the MTP layer, as before (never no drafter)
    if a.mtp == "off" and not (rt / "experts.bin").exists():
        ok("the draft layer (MTP) is off: its ~5 GB are not downloaded (`--mtp on` fetches it later)")   # round 8, N3
    elif getattr(a, "drafter", None) == "dflash2" and not (rt / "experts.bin").exists():
        ok("DFlash2 is the drafter: the MTP draft layer's ~5 GB are not downloaded (choosing the MTP later fetches it once)")
        provide_dflash2_vocab(data, a.draft_vocab or saved_draft_vocab(home() / f"strata-{tag.lower()}.json") or "cjk")
    elif corrupt or not (rt / "experts.bin").exists():
        say("  The MTP draft layer (speculative decoding, ~2x faster output) comes from the original Qwen checkpoint:")
        say("  only its ~5 GB of MTP tensors are downloaded.")
        if fetch_mtp(mtp, env) is not False:               # (False: offline, nothing to pack)
            run([sys.executable, str(ROOT / "tools" / "mtp_pack.py"), "--src", str(mtp), "--experts", "q2_0",
                 "--out", str(mtp / "mtp-q2_0.gguf")], env=env)
            run([sys.executable, str(ROOT / "tools" / "mtp_rt.py"), "--gguf", str(mtp / "mtp-q2_0.gguf"), "--out", str(rt)],
                env=env)
    # a setup run again without --draft-vocab keeps the subset this model's config chose before (cyrillic, fr, en)
    draft_vocab = a.draft_vocab or saved_draft_vocab(home() / f"strata-{tag.lower()}.json")
    if (rt / "experts.bin").exists():
        refresh_draft_vocab(rt, draft_vocab or "cjk")
        ok(f"MTP draft layer: {rt}")
    refresh_dflash2_vocab(data, draft_vocab or "cjk")        # an existing DFlash2 copy follows the choice too
    for line in draft_vocab_note(gpu.get("vram_gb", 0.0), draft_vocab):   # #474: a recommendation, nothing changes
        say("  " + line)

    # ---- 7. the start script
    step(7, "writing the start script")
    sys.path.insert(0, str(ROOT / "tools"))
    from gguf_reader import GGUFFile                   # the PLE table's shard: shard 2 (original) or 1 (Swift)
    if ready:   # the dense GGUF as --native and --native-dense-gguf (--native alone would look for a second shard),
        rp = ready_paths(model, models_dir)            # the FP8 n-gram table, the BF16 token embedding
        ple = rp["ple"]
        model_args = ["--pack", str(pack), "--native", str(rp["dense"]), "--native-dense-gguf", str(rp["dense"]),
                      "--ple-gguf", str(ple), *(["--embd-gguf", str(rp["embd"])] if "embd" in rp else [])]
    else:
        ple = next((s for s in shards if any(t.name == "per_layer_token_embd.weight" for t in GGUFFile(s).tensors)), None)
        if ple is None:
            fail("the model has no per_layer_token_embd tensor (is this a Qwen3.8-Flash-Next GGUF?)")
        # (a 4-shard file: the engine finds the PLE table's shard itself from shard 1, the measured setup)
        model_args = ["--pack", str(pack), "--native", str(shards[0]),
                      *(["--ple-gguf", str(ple)] if len(shards) <= 2 else [])]
    from strata_control import setup_config            # the seam: the lines that built the run config live in strata_control/setup_config.py
    _built = setup_config.config_for(setup_config.SetupInputs(
        a=a, adopted=adopted, chosen=chosen, cuda_tk=cuda_tk, draft_vocab=draft_vocab, eng=eng, engine_ver=engine_ver, esp=esp, fam=fam, family=family, gpu=gpu, hip=hip, in_budget=in_budget, lib_dirs=lib_dirs, low_ram=low_ram, meta=meta, mmproj=mmproj, model=model, model_args=model_args, models_dir=models_dir, multi=multi, pack=pack, ple=ple, port=port, q4_split=q4_split, ram=ram, reader=reader, ready=ready, rope_scale=rope_scale, rt=rt, scaling=scaling, shards=shards, tag=tag, vision=vision, ctx=ctx, kv=kv, resident=resident, budget=budget, GGUFFile=GGUFFile), sys.modules[__name__])
    cfg, cfg_path, cal, args, ctx, kv, resident = (_built.cfg, _built.cfg_path, _built.cal, _built.args, _built.ctx, _built.kv, _built.resident)
    write_setup_config(cfg_path, cfg, adopted if adopted is not None and adopted.name == cfg_path.name else None, explicit_args(a),
                       after_carry=(lambda c: uma_cache_guard(c, model, gpu)) if gpu.get("uma") else None)
    script = write_run_script(tag, cfg_path, port, cfg.get("open_browser") is not False)
    # offered only when someone answers: --yes installs and adopted earlier installs are not held up by it
    # P12: Skip is the default, as in the Terminal's first launch (T5): a person who presses Enter all the way does not wait 15-30 minutes
    if cal is None and not hip and not a.no_start and not a.yes and ask(TUNE_QUESTION.format(again=setup_command()), ["y", "n"], "n", a.yes, shown=TUNE_DEFAULT_SHOWN) == "y":
        tuned = calibrate_config(cfg_path)
    else:
        tuned = None                                   # not asked for: nothing to repeat below
    ok(f"start script: {script.name}")

    say()
    say("All set.")
    say(f"  API (OpenAI):     http://127.0.0.1:{port}/v1   (any API key; model name: anything)")
    say(f"  API (Anthropic):  http://127.0.0.1:{port}/v1/messages")
    if a.host and a.host not in ("127.0.0.1", "localhost"):
        say(f"  Other devices:    the server window prints this PC's address (http://<IP>:{port}/)"
            + ("" if a.api_key else " - no API key set: anyone on your network can use it"))
    say(f"  Next time:        just run {'START-HERE.bat' if WIN else './setup.sh'} (or {script.name}) - it starts right away")
    if vision != "none":
        say("  Images:           send them in the chat page, in chat.py (/image <path>) or over the API")
    if cfg.get("images"):
        say(f"  Image generation: POST http://127.0.0.1:{port}/v1/images/generations (OpenAI's images API)")
    if a.parallel is None:                             # #465: the opt-in, said once (nothing changes)
        for line in parallel_note(None, [g.get("vram_gb", 0.0) for g in chosen], MODELS[model]["arena_gb"], ctx, kv,
                                  "--kv-resident" in cfg["args"], ram):
            say("  " + line)
    if tuned is False:                                 # #447: a failed tuning is repeated here, not only above
        say("  Tuning:           FAILED (the reason is above): the default settings stay - "
            f"{'START-HERE.bat' if WIN else './setup.sh'} --calibrate tries again")
    if a.no_start:
        return 0
    # offered only when someone answers (--yes asks nothing), default no; the benchmark starts its own server and stops it
    if not a.yes and sys.stdin.isatty() and ask(
            "Run a quick benchmark now? It measures this install for about 10 minutes and writes a report you can share "
            f"(later: {'BENCH.bat' if WIN else './bench.sh'})", ["y", "n"], "n", a.yes) == "y":
        subprocess.call([sys.executable, str(ROOT / "tools" / "strata_bench.py"), "--config", str(cfg_path), "--port", str(port)])
    return start(cfg_path, port)
