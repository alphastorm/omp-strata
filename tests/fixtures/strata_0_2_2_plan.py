# Planning fixture extracted from stock Niko1221/Strata v0.2.2 setup.py.
# Tag target: 011c9e600a93bbc9fd451c563501b5831c32bbca.
# Source-faithful AST nodes, never imported; no installer or hardware probe is executed.

def home() -> Path:
    """Where an install writes (see above). A function, not a constant, so ROOT stays the one thing a caller can point elsewhere."""
    return _CONTROL_HOME or ROOT

HF_REVISIONS = {
    "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF": "ed59f92082b1e93c0e96d60a8b11aab089b52f09",        # 2026-09-29
    "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF": "99bb8f7f95c7aa7b24a36a7786a4f657b30f5d3d",   # 2026-10-07 (adds IQ3_S)
    "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF": "5348543e0147355ac9cbcb031184a3546350988e",  # 2026-09-29
    "unsloth/Qwen3.8-Flash-Next-GGUF": "38bb39ee97821de2c9009abb7e93950eec396e66",                   # 2026-09-30
    "unsloth/Qwen3.6-35B-A3B-MTP-GGUF": "5bc3e238d916f48a861bac2f8a1990a0e9b7e98d",                  # 2026-10-12
    "agentionai/Qwen3.8-Flash-Next-Gyro-GGUF": "1ada08422e404aca51ab9df665f089f34c419c6b",           # 2026-10-13
}

LLAMA_CPP_COMMIT = "3cf03257f219afbe7334045ff7c6a06ac68c627d"

CUDA_WHEELS = ["nvidia-cublas==13.0.2.14", "nvidia-cuda-runtime==13.0.96"]

MIN_DRIVER = 580                       # CUDA 13.0

MIN_ENGINE = (0, 1, 46)                # versions compare all numbers; v0.1.46: the 0.2 release engine (UPDATE.bat and setup fetch it from the signed feed, #3469 #3437); v0.1.45: Qwen3.6 parallel requests and pictures, fixes #2346 #2372 #2396; v0.1.44.1: CPUs without AVX2 start again (#2324: an illegal instruction before main in the NVFP4 CPU rows), the CUDA 12.0/12.1 toolkits build (#2322), a crashed engine start is named instead of retried as a GPU runtime start, Mac M2 (#2323); v0.1.44: UD-Q4/Q5/Q6_K_XL and Q8_0 Unsloth files in setup (K-quant experts, MMQ prompt library strata_kq), NVFP4 packs, Qwen3.6-35B-A3B, Intel Arc A-series kernels, the pipelined-decode and latency work; v0.1.43.1: the adaptive overlap no longer collapses decode on pinned-host desktops (#1964 #1975), Windows PLE mmap stall (#1984), pinned prompt uploads (#1996), the I/O watchdog allowance; v0.1.43: adaptive-tier copies overlap on CUDA, P100 (sm_60) kernel tables, RDNA4 (gfx1200/gfx1201) defaults (route tail skip, measured PCIe share, 16K prompt chunks, fused IQ3 prompt experts); v0.1.42.1: the GGUF-in-place file tier on Windows unmaps every shard, dual-socket starts judge each NUMA node and STRATA_DROP_CACHE_ON_EXIT, tools/strata_bench.py; v0.1.42: STRATA_ROUTE_TAIL_SKIP=7 default on CUDA (+13-16% decode), the AMD 2-GPU checkpoint fix (H13), Phase 2 fixes and opt-ins; v0.1.41.1 (folded into 0.1.42): the #1576 card order, #1616 stage size, #1595 CPU share, #1630/#1607 Windows HIP chunk cap and commit-limit warning, #1603 parallel-request bookkeeping; v0.1.41: CPU prefill share on by default (NVIDIA, chunks < 1024), --batch-groups auto, the file tier read in batches on Windows, Pascal decode fix, per-arch tables; v0.1.40.3: the #1357 MTP router guard, the #1376 Windows HIP cache floor, #461 runtime DLLs, Intel A750 first-request fix; v0.1.40.2: F4 verify windows, the Linux file tier (#1194), the stager wait (#1057), #1264/#1201/#1139 fixes, opt-in CPU share (#1282), Intel Arc; v0.1.40: --resident-experts on a layer split with the split+resident variant (#848), --kv k8v4 with KV streaming (#711); v0.1.39: the #577 file-tier regression fixed, the OpenAI Responses API (#451, Codex), a reply stuck on one token ended (#606), the head before the arena (#620), effort_position (#458), --vram-reserve hot resize opt-in (#533), PR batch; v0.1.38: prompts faster (one gather per expert group #372, the first chunk's PLE rows beside layer 0 #374, DeltaNet three heads per thread #413), --kv q4_0 prompts on tensor cores (#452), Q5_0 experts on the GPU (#473), IQ4_XS on AVX-2 (#415), unbuffered expert loading on Windows (#357 #362), --peer-device (#531), a 6 GB card starts (#496), PR batch; v0.1.37: a silent engine is restarted (#481), Windows AMD counts the desktop's VRAM (#380 #377 #497), a steadier PCIe probe (#485), fixes #496 #495 #498 #505 #493; v0.1.36: a cancelled prompt logged as read so far (#471), the draft-head hint (#474), UPDATE.bat (#475), --expert-profile-save (#477); v0.1.35: Windows AMD uses its bundled HIP runtime (#468 #461), the low-RAM resident mode on Windows 32 GB (#467), fixes #460 #459 #446 #447 #457 #448 #444; v0.1.34: AMD on Windows (a ready-made HIP engine), an MCP server for AI assistants (tools/strata_mcp.py), a shorter README; v0.1.33: a portable image encoder again (#411 #412), setup recommends instead of forcing (#406 #403 #364 #384), fixes #352 #365 #369 #371 #375 #393 #408 #414; v0.1.32: split prompts faster (#340), AMD router +12%, Unsloth Q4 in setup, faster Q4 prompts, #326/#327/#342/#344 fixes, PR batch; v0.1.31: Unsloth UD-Q4_K_XL (experimental), GGUF-in-place low-RAM mode, Windows GGUF load 2x, server race + tokenizer fixes, AMD intrinsics; v0.1.30: short prompts faster (streaming from 1024 tokens), resident low-RAM variant, multi-GPU session carve, RDNA4; v0.1.29: sampled answers faster (split top-k), #154 correctness fixes; v0.1.28: the expert cache reserves the draft head, a cancelled request no longer fails the next; v0.1.27: RTX 20 (sm_75) in the ready-made engine, the HIP build without CUDA headers; v0.1.26: the draft layer's prompt pass in batches; v0.1.25: faster prompts (grouping off the copy engine, fused hyper-connection kernels), AMD HIP backend, --kv k8v4; v0.1.24: long prompts faster (QSA select on tensor cores); v0.1.23: image requests honor sampling, 8 GB cards start, batched verify window; v0.1.22: faster prompts (tensor-core attention), multi-GPU across images/steering/KV streaming; v0.1.21: multi-GPU layer split (--gpus); v0.1.20: system-prompt checkpoint, PCIe probe, hit rate; v0.1.19: penalties

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

UNSLOTH_RAM_LEFT_GB = 24        # RAM beside the budget: the OS, the engine, and the file cache the rest is read through

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
    "unsloth": {"title": "Qwen3.8-Flash-Next (Unsloth)", "by": "Unsloth's 4- to 8-bit quantizations",
                "about": "UD-IQ4_XS, UD-Q4_K_XL, UD-Q5_K_XL, UD-Q6_K_XL or Q8_0 (94 to 188 GB downloads): every expert in "
                         "RAM from ~80 GB (UD-IQ4_XS) to ~136 GB (Q8_0) of RAM, else part of them read from the SSD",
                "hf": hf("unsloth/Qwen3.8-Flash-Next-GGUF") + "{q}/",
                "file": "Qwen3.8-Flash-Next-{q}-0000{i}-of-00004.gguf", "shards": 4, "tag": "unsloth-",
                "mmproj_hf": hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF"),
                "mmproj": "mmproj-Qwen3.8-Flash-Next-BF16.gguf", "name": "qwen3.8-flash-next-unsloth",
                "vision": True, "pack_args": ["--compat-bf16"],
                "sha256": {**UNSLOTH_SHARDS, **UNSLOTH_IQ4_XS_SHARDS, **UNSLOTH_BIG_SHARDS}},
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

POOL_WORKERS_CAP = 32

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

SPLIT_MIN_VRAM_GB = 8                                   # a card sharing a model holds the dense weights and its own

def gpu_problem(g, together=False):
    """Why Strata cannot use this card, in plain words (None: it can)."""
    if int(g["arch"]) < 75 and not (sm60_card(g["arch"]) and experimental_sm60()):
        return (f"not supported - older than the RTX 20 series (compute capability {cc(g)}; Strata needs 7.5 or "
                "newer" + ("; experimental: choose it with --gpu " + str(g["index"]) + " (the CUDA 12 engine, "
                          "docs/OLDER_GPUS.md)" if sm60_card(g["arch"]) else "") + ")")
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

def choose_gpus(a, found) -> list:
    """Which cards this install uses: --gpus / --gpu, or asked when two or more can share the model (the two best
    together recommended), else the supported card with the most VRAM.  Returns their numbers, in the engine order, the Main card last when roles are chosen."""
    if a.gpus:
        sel = parse_gpus(a.gpus, found)
        check_gpus(sel, found, yes=a.yes, named=str(a.gpus).strip().lower() != "all")
        return sel
    if a.gpu is not None:
        check_gpus([a.gpu], found)
        return [a.gpu]
    single = sorted([g for g in found if gpu_problem(g) is None], key=lambda x: (-round(x["vram_gb"]), x["index"]))
    if not single:
        gpu_table(found)
        fail("none of your GPUs can run Strata", "it needs an NVIDIA RTX 20 series or newer (compute capability 7.5+)")
    can = together_ok(found)
    if not can:
        return [single[0]["index"]]
    return choose_roles(a, found)

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

def low_ram_vram(g) -> float:
    """The GPU memory the low-RAM mode may count as room beside the RAM: a discrete card's VRAM; an APU's BIOS
    carve-out only (its shared memory is the RAM itself)."""
    return g.get("dedicated_gb", 0.0) if g.get("uma") else g["vram_gb"]

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

def unsloth_default_env(family: str, model: str, hip: bool, in_budget: bool) -> dict:
    """0.1.44 (owner, review-quants.md section 5): the run-config "env" setup writes for Unsloth's files.
    STRATA_MMQ_KQ=1 (the K-quant MMQ prompt kernels) for UD-Q5_K_XL and UD-Q6_K_XL, where its prompt-path KL is equal
    or better than the FP16 path's; UD-Q4_K_XL keeps it opt-in.  STRATA_HC_Q8=1 on CUDA for the UD-* files (the
    GGUF's own Q8_0 hyper-connection projections, closer to the file and faster; the GSQ-RCO packs are untouched).
    STRATA_ROUTE_TAIL_SKIP=0 where every expert is in RAM (the skip costs KL there); the RAM-budget mode keeps it."""
    env = {}
    if family != "unsloth":
        return env
    if model in ("UD-Q5_K_XL", "UD-Q6_K_XL"):
        env["STRATA_MMQ_KQ"] = "1"
    if not hip and model.startswith("UD-"):
        env["STRATA_HC_Q8"] = "1"
    if not in_budget:
        env["STRATA_ROUTE_TAIL_SKIP"] = "0"
    return env

def menu_families(hip: bool) -> list:
    """The families the model menu lists, in menu order.  The NVFP4 packs run on NVIDIA cards only (the AMD and Intel
    engines have no NVFP4 kernels), so on those the menu does not offer them; `--family nvfp4` still says why not."""
    return [f for f in FAMILIES if not (hip and FAMILIES[f].get("ready"))]

LOW_RAM_HEADROOM_GB = 10   # RAM beside the experts: the OS, the engine's other buffers, the server

RESIDENT_ENGINE = (0, 1, 30)   # the first engine with --resident-experts (the low-RAM mode's resident variant)

def low_ram_needed(model, ram) -> bool:
    """The model's experts do not fit this PC's RAM with room left for the rest: they are then mapped from the pack's
    experts.bin instead of copied into RAM (the low-RAM mode)."""
    return ram < MODELS[model]["arena_gb"] + LOW_RAM_HEADROOM_GB

MTP_VRAM_GB = 1.0

def low_ram_gpu_gb(model, vram_gb, ctx=32768, kv="int8", mtp=True) -> float:
    """About how many GB of the model's experts the GPU's cache holds: its VRAM minus ~5 GB for the dense weights,
    buffers and a 32K context's KV cache, minus the KV cache of a longer context (in VRAM in the low-RAM mode: its RAM
    has no room for KV streaming), minus ~1 GB for the draft layer (MTP) when it is on."""
    kv_tok = 13 * KV_CELL_BYTES.get(kv, 1056)           # bytes per context token: 12 QSA layers + the draft layer
    longer = max(0, ctx - 32768) * kv_tok / 1e9
    return max(0.0, min(MODELS[model]["arena_gb"], vram_gb - 5 - (MTP_VRAM_GB if mtp else 0.0) - longer))

def low_ram_gpu_share(model, vram_gb, ctx=32768, kv="int8", mtp=True) -> float:
    """About how much of the model's experts the GPU holds."""
    return low_ram_gpu_gb(model, vram_gb, ctx, kv, mtp) / MODELS[model]["arena_gb"]

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
    return ["args " + f for f in dict.fromkeys(g[0] for g in user_args.groups(mine) if g[0].startswith("--"))]

def engine_exe(eng: Path) -> str:
    """The `exe` of a run config: the engine component in the app, else the engine binary's path."""
    return "component:strata-engine" if CONTROL else str(eng / EXE)

def write_setup_config(cfg_path: Path, cfg: dict, source: Path | None = None, explicit: list[str] | None = None) -> None:
    """#629: setup's run config, written over an earlier one for the same model without losing what the user added
    to it: the keys setup does not write are carried over (carry_over), and the earlier file is kept as
    strata-<model>.json.bak when it changes.  `source`: an earlier install's config to carry the keys over from when
    this folder has none yet (a copy set up like the last one).  A line says what was kept, one what was not."""
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

DRAFT_VOCAB_MIB = {"cjk": 348, "cyrillic": 193, "fr": 151, "en": 133}   # the draft head's VRAM per subset (IQ3_S: the largest)

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

PREFILL_BIG_RAM_GB = 96        # bench #433 #440 #834 #669: --prefill auto:32768 +21-35% at 96 GB, ~3x slower at 32 GB

PREFILL_RISK_RAM_GB = 64       # below this an explicit auto:32768 is warned about

HEADROOM_RAM_GB = 48           # bench #834: STRATA_RESIDENT_HEADROOM_GIB=6 on a PC with this much RAM or less

AGENT_CACHE_FREE_GB = 24       # bench #882 #440: RAM left beside the model for the conversation cache

AGENT_CACHE_MIB = 8192

SMALL_VISION_VRAM_GB = 12.5    # bench #469: the GPU image encoder shrinks the prompt chunks on cards up to 12 GB

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

DISPLAY_RESERVE_MIB = 1500     # #779: the tip for an NVIDIA card that also drives a display

DESKTOP_RESERVE_MIB = 3072     # #560 #516: what kept a KDE/Wayland desktop alive beside a full expert cache

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

def main():
    need = min(d["ram_gb"] for d in MODELS.values() if not d.get("mem_total"))   # Gyro counts VRAM + RAM: not a RAM floor
    fams = menu_families(hip)
    tier = tier_pick(ram, low_ram_vram(gpu))
    rec_fam = STRIX_HALO_FAMILY if strix_halo_recommends(gpu, ram) and STRIX_HALO_FAMILY in fams else tier[0] if tier and tier[0] in fams else fams[0]
    names = [m for m in MODELS if family in MODELS[m].get("families", ("qwen", "swift"))]
    names.sort(key=lambda m: bool(MODELS[m].get("experimental")))   # an experimental size last, never the default
    installed = installed_size(family, names, have)
    rec = str(names.index(installed or recommended_size(family, names, ram, low_ram_vram(gpu))) + 1)
    small = min(x["vram_gb"] for x in chosen)         # each card keeps its layers' KV of the whole context
    rec_ctx = 32768 if small < 14 else 65536 if small < 20 else 131072
    rec_ctx = min(rec_ctx, ram_ctx(model, ram, low_ram))
    q2_avx = model == "Q2_0" and avx512 and family == "qwen"
    prep_gb = MODELS[model].get("prepare_gb", 0.0) if ready and MODELS[model].get("prepare") and \
        not prepared_done(model, models_dir) else 0.0
    margin = 2 if mtp_have else 8                      # working room: a guess, not bytes that will be written
    real = to_fetch + prep_gb + \
        (40 if q2_avx and not pack_bin else 0) + (1 if vision != "none" else 0) + \
        (MODELS[model]["arena_gb"] + 1 if low_ram and not q2_avx and not pack_bin else 0)
    need = real + margin
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
    args = [*model_args,
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
    if low_ram and ready:
        # NVFP4 (68 GB of experts) on a PC whose RAM does not hold them: the RAM-budget mode, as Unsloth's files - the
        # most-used experts outside VRAM pinned within RAM less 24 GB, the rest read from experts.bin.  Mapped
        # (--mmap-experts) on a 64 GB Windows PC, the experts it read stayed in the engine's working set: free RAM
        # fell to 0.6 GB on the RTX 5070 PC (2026-10-13), where the budget mode kept 22 GB free
        rb = resident_budget_gib(model, ram)
        args += ["--resident-budget-gib", str(rb)]
        ok(f"low-RAM mode: {rb} GiB of {model}'s experts kept in RAM (the most used), the rest read from the pack's "
           "experts.bin on the SSD as needed")
    elif low_ram:   # the experts from the pack's experts.bin: the ones the GPU does not hold copied into RAM, or mapped
        args += ["--resident-experts" if resident else "--mmap-experts"]
    disk = None if is_wsl() else rotational_disk(ple)  # #605 (WSL's virtual disk says rotational)
    if disk:
        tensor = None if ready else next((t for t in GGUFFile(ple).tensors if t.name == "per_layer_token_embd.weight"), None)
        size = ple.stat().st_size if ready else getattr(tensor, "expected_bytes", lambda: None)()
        table_gb = size / 1e9 if size else 28.8
        if ram >= MODELS[model]["ram_gb"] + table_gb + 4:
            args += ["--ple-io", "ram"]
            ok(f"the model is on a rotational disk ({disk}): its {table_gb:.0f} GB n-gram table is kept in RAM "
               "(--ple-io ram) - read from the disk at random, it can stall prompts for minutes (#605)")
        else:
            warn(f"the model is on a rotational disk ({disk}): its n-gram table is read from it at random, which can "
                 f"stall prompts for minutes (#605). An SSD is recommended; with ~{table_gb:.0f} GB more RAM, "
                 "--ple-io ram in the config's args keeps the table in RAM instead")
    elif not low_ram and ple_ram_platform_ok():
        # 147-verify: on an SSD too, a PC with RAM to spare keeps the n-gram table in RAM: a new prompt's first chunk then
        # does not wait for its table rows (65,536 random SSD reads at 4K tokens).  RTX PRO 5000 (Linux, NVMe, fresh engine
        # per prompt, 3 rounds, the same bits): prompt 4K 1298 -> 1059 ms (-18%), 20K 4644 -> 4223 ms (-9%), 98K 20447 ->
        # 20027 ms (-2%), decode +0.8%.  On a card whose prompt is slow (R9700) the read hides behind layer 0 and nothing
        # changes.  It costs the table's size in RAM, so only with 16 GB to spare beyond the model's own need; a smaller PC
        # keeps reading from the SSD as before.
        try:
            tensor = None if ready else next((t for t in GGUFFile(ple).tensors if t.name == "per_layer_token_embd.weight"), None)
            size = ple.stat().st_size if ready else getattr(tensor, "expected_bytes", lambda: None)()
        except Exception:
            size = None
        table_gb = size / 1e9 if size else 28.8
        if ram >= MODELS[model]["ram_gb"] + table_gb + 16:
            args += ["--ple-io", "ram"]
            ok(f"{ram:.0f} GB of RAM: the {table_gb:.0f} GB n-gram table is kept in RAM (--ple-io ram), so a new prompt does "
               "not wait for its rows from the SSD (a 4K prompt about 18% sooner on a fast card); remove --ple-io ram from "
               "the config's args to read it from the SSD instead")
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
        args += ["--resident-budget-gib", f"{budget:g}"]   # GiB kept in RAM (#498: a layer split had no budget)
        if gpu.get("uma") and "--expert-cache" in args:
            # #1715: the cache and the budget draw on the same RAM: a number that leaves the OS its room, not `auto`
            slots = uma_expert_cache(model, ram, budget, kv_ram_gb if "--kv-resident" in args else 0.0)
            if slots is not None:
                args[args.index("--expert-cache") + 1] = str(slots)
                ok(f"expert cache: {slots} slots (not auto): this GPU shares the RAM with the {budget:g} GiB budget, "
                   f"so setup leaves {UNSLOTH_RAM_LEFT_GB} GB of the RAM for the OS and the desktop (#1715). "
                   "--expert-cache N in the config's args sets it")
            else:
                warn(f"this GPU shares the RAM, and the {budget:g} GiB RAM budget leaves almost none for the expert "
                     "cache: it stays on auto, which may take the room the OS needs (#1715). A smaller "
                     "--resident-budget-gib leaves room")
    if vision != "none":
        args += ["--vision"]
        if VISION[vision]["reserve_mib"]:
            args += ["--vram-reserve-mib", str(VISION[vision]["reserve_mib"])]
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
    if not multi and family == "unsloth" and 0 < gpu.get("vram_gb", 0.0) <= UD_FIT_CARD_GB:
        # a card of about 8 GB: the config setup would write may not start (measured on an A750).  Pick the least
        # harmful one that fits and say so; what the user chose with --context / --kv / --vram-reserve-mib is kept
        res_arg = int(args[args.index("--vram-reserve-mib") + 1]) if "--vram-reserve-mib" in args[:-1] else None
        vg = gpu["vram_gb"]
        rt_mib = unsloth_runtime_mib(gpu)
        fits = unsloth_vram_slack_mib(vg, ctx, kv, UD_FIT_ENGINE_RESERVE_MIB if res_arg is None else res_arg, True,
                                      rt_mib) >= UD_FIT_MIN_SLACK_MIB
        plan = None
        if not fits:
            plan = unsloth_small_card_plan(vg, ctx, kv, res_arg, ctx_fixed=bool(a.context), kv_fixed=bool(a.kv),
                                           runtime_mib=rt_mib)
            if plan is not None:
                nctx, nkv, nmtp, slack = plan
                changes = []
                if nctx != ctx:
                    args[args.index("--max-context") + 1] = str(nctx)
                    changes.append(f"context {ctx} -> {nctx}")
                    ctx = nctx
                if nkv != kv:
                    if "--kv" in args[:-1]:
                        args[args.index("--kv") + 1] = nkv
                    else:
                        args += ["--kv", nkv]
                    changes.append(f"KV cache {kv} -> {nkv}")
                    kv = nkv
                if not nmtp and "--mtp" in args[:-1]:
                    i = args.index("--mtp")
                    del args[i:i + 2]
                    changes.append("no MTP draft layer on the GPU (about 0.8 GB more for the expert cache; decode is slower)")
                warn(f"with the usual settings {model} would not start on this {vg:.0f} GB card (setup's estimate: no VRAM "
                     "left for the expert cache). Setup chose the least harmful start that fits: " + ", ".join(changes)
                     + ". A bigger context, 8-bit KV or the draft layer need a card with more VRAM (or "
                     "--vram-reserve-mib 0, which leaves nothing for other programs).")
        for line in unsloth_small_card_lines(model, vg, plan, fits):
            warn(line)
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
    cfg = {"exe": engine_exe(eng), "args": args, "cwd": str(ROOT), "tokenizer": str(pack / "tokenizer"),
           "model_name": f"{fam['name']}-{model.lower()}", "log": str(home() / f"strata-{tag.lower()}.log"),
           "lib_dirs": lib_dirs, "port": port}
    if cuda_tk == 12:                                  # the experimental CUDA 12 engine (engine-cuda12/)
        cfg["cuda"] = 12
    if (uenv := unsloth_default_env(family, model, hip, in_budget)):
        cfg["env"] = uenv
    if hip:
        cfg["backend"] = "hip"
        # the dense prompt GEMMs through hipBLASLt with kernels measured on this GPU generation (tools/hip; +40-60%
        # prompt speed on the 7900 XTX): only a table for this card's arch AND the installed hipBLASLt version (the
        # engine refuses any other one and falls back to plain hipBLAS)
        if CONTROL:
            pass    # the app's engine is a package: the server picks its tuning/ table for the card when it starts (strata_control/hipblaslt_tuning.py)
        else:
            table = hipblaslt_table(gpu["arch"], lib_dirs, meta.get("hipblaslt_version"), [eng / "tuning"])
            if table:
                cfg["env"] = {"STRATA_HIPBLASLT_TUNING": str(table)}
        if GFX1103_OPT_IN and gfx_arch_is(gpu["arch"], "gfx1103") and not WIN:
            # the 780M's KFD queues are evicted (a GPU reset) while transparent huge pages move the pinned expert arena
            cfg.setdefault("env", {})["STRATA_NO_ARENA_THP"] = "1"
            # the exact gfx1151 speed switches measured on this chip (GFX1103_SWITCHES): the engine has no arch defaults
            # for gfx1103, so setup writes them into the config.  They are setup's own (SETUP_ENV), so a re-run refreshes
            # them and turning the opt-in off takes them out again.
            cfg.setdefault("env", {}).update(GFX1103_SWITCHES)
        if GFX1150_OPT_IN and gfx_arch_is(gpu["arch"], "gfx1150"):
            # the exact gfx1151 speed switches measured on this chip (GFX1150_SWITCHES): the engine has no arch defaults
            # for gfx1150, so setup writes them into the config.  They are setup's own (SETUP_ENV), so a re-run refreshes
            # them and turning the opt-in off takes them out again.
            cfg.setdefault("env", {}).update(GFX1150_SWITCHES)
        # RDNA2 (gfx103x): the prompt's FP16 GEMMs through rocBLAS's best kernel per shape (tools/hip/tune_rocblas;
        # the GDN input projection 6x faster below 1,152 tokens on a 6900 XT).  The ids are valid for one rocBLAS
        # build, which only the engine can read, so setup points it at the directory and the engine picks the file
        # <arch>-rocblas-<version>.txt for its own library, or runs the default kernels and says so in its log.
        rocblas_tables = sorted(p.name for p in (ROOT / "tools" / "hip").glob(f"{gpu['arch']}-rocblas-*.txt"))
        if rocblas_tables:
            cfg.setdefault("env", {})["STRATA_ROCBLAS_TUNING"] = str(ROOT / "tools" / "hip")
            ok(f"rocBLAS tuning tables for {gpu['arch']}: {', '.join(rocblas_tables)} (the engine takes the one of its rocBLAS build)")
        if resident:   # ROCm: large page-locked host allocations can fail or be slow for the CPU; keep the copy pageable
            cfg.setdefault("env", {})["STRATA_RESIDENT_PIN"] = "0"
    if gpu["count"] > 1 or a.gpu is not None:
        cfg["gpu"] = gpu["index"]                      # the engine is told this card (issue #51)
        cfg["gpus_asked"] = True                       # chosen at setup: not asked again at start
    if multi:                                          # a layer split across these cards (the server adds the flag)
        cfg["gpu"] = multi
        cfg["layer_split"] = a.layer_split or "auto"
        if getattr(a, "_roles", None):                 # roles chosen: the card list is Main last, in this order, and the server keeps it
            cfg["gpu_order"] = "as_given"
        ok(f"layer split across GPUs {multi} ({cfg['layer_split']})")
        recommend_remote_expert_opt(cfg, off=a.no_remote_expert_opt)
    if getattr(a, "_roles", None):                     # the roles themselves (strata_control/gpu_roles.py); "gpu" above is their mirror
        final = cfg["gpu"] if isinstance(cfg.get("gpu"), list) else [cfg["gpu"]]      # what the checks above left (a model that cannot share keeps one card)
        main = final[-1]
        cfg["gpu_roles"] = {str(i): ("main" if i == main else "helper" if i in final else "off") for i in sorted(set(a._roles) | set(final))}
        cfg["gpus_asked"] = True
        cfg.pop("gpu_none", None)
        if isinstance(cfg.get("gpu"), list) and len(final) > 1:
            cfg["gpu_order"] = "as_given"
    if a.replicas is not None and a.replicas >= 2:      # data-parallel replicas (serve/replicas.py), opt-in
        cards = multi if multi else []
        if not cards or len(cards) % a.replicas:
            warn(f"--replicas {a.replicas}: needs the chosen GPUs ({cards or 'one'}) to divide into {a.replicas} equal "
                 "groups; not set (choose the cards with --gpu 0,1,2,3, or write the groups into the config: "
                 '"replicas": [{"gpus": [0, 1]}, {"gpus": [2, 3]}])')
        else:
            cfg["replicas"] = a.replicas
            per = len(cards) // a.replicas
            ok(f"{a.replicas} replicas of {per} GPU(s) each: {' | '.join(','.join(map(str, cards[i * per:(i + 1) * per])) for i in range(a.replicas))}")
            if per > 1 and a.layer_split not in (None, "auto"):
                warn("--layer-split is one engine's value; with replicas every group would get it: leave it at auto")
            if (os.cpu_count() or 0) < 8 * a.replicas:
                warn("each replica loads its own copy of the model into RAM and runs its own host threads: check the RAM")
    if a.host:
        cfg["host"] = a.host
    if a.api_key:
        cfg["api_key"] = a.api_key
    if draft_vocab:
        cfg["draft_vocab"] = draft_vocab
    if a.browser is not None:                          # #609: only when given (else an earlier choice is carried over)
        cfg["open_browser"] = a.browser
    if a.mtp is not None:                              # written only when given (else an earlier choice is carried over)
        if a.mtp == "off":
            cfg["mtp"] = False
            removed = draft_layer.apply(cfg)
            ok("the draft layer (MTP) is off for this model" + (f" ({' '.join(removed)} left out)" if removed else "") +
               ": less graphics memory and RAM, slower words per second. `--mtp on` turns it back on")
        else:
            cfg["mtp"] = True                          # explicit, so carry_over does not bring an earlier false back
            ok("the draft layer (MTP) is on")
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
        old_cfg = home() / f"strata-{tag.lower()}.json"
        vt = vision_tokens(a.vision_tokens, vision, old_cfg if old_cfg.is_file() else adopted)
        cfg["vision"] = {"exe": str(eng / VEXE), "mmproj": str(mmproj),     # the text model, opened vocab-only:
                         "model": str(ready_paths(model, models_dir)["dense"] if ready else shards[0]),
                         "gpu": vision == "gpu", "max_tokens": vt}
        if reader is not None:                          # AMD: the HIP reader with the CPU reader behind it, or the CPU reader
            from strata_control import vision_reader as VR
            cfg["vision"] = VR.vision_section(reader, cfg["vision"])
        if vision == "cpu":
            cfg["vision"]["threads"] = vision_threads()
    elif a.vision_tokens is not None:
        warn("--vision-tokens: images are off for this model, so it is not used")
    if a.images:                                       # only when given: else an earlier "images" is carried over
        cfg["images"] = setup_images(a, gpu, hip, Path(a.models_dir))
    cfg_path = home() / f"strata-{tag.lower()}.json"
    if cal is not None:
        sys.path.insert(0, str(ROOT / "tools"))
        import calibrate as CAL
        cfg["args"] = CAL.apply(cfg["args"], cal.get("settings") or {})
        if "env" in cal:                               # a calibration from before the env step leaves "env" as it is
            cfg["env"] = CAL.apply_env(cfg.get("env"), cal["env"])
        ok("the settings tuned for this PC earlier are used" + (f" ({cal['date']})" if cal.get("date") else ""))
    else:                                              # #642: measured counts (a calibration) win over the rule
        cfg["args"] = recommend_pool_workers(cfg["args"])
        for line in pool_workers_note(cfg["args"]):
            warn(line)
        for line in two_socket_note(cpu_sockets()):    # bench tips: text only, the config is not touched
            say("  " + line)
    write_setup_config(cfg_path, cfg, adopted if adopted is not None and adopted.name == cfg_path.name else None, explicit_args(a))
