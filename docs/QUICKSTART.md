# Quickstart

Stock Oh My Pi (OMP) 18.16.0 runs against a local stock Strata v0.2.11 server (or v0.2.10 on the RTX 5090 131K
alternative). Pick the profile for your host; the same commands work with any of them, and every profile keeps its own
integration root and ledger.

| Host | Current qualified profile | Qualified rollback |
|---|---|---|
| RTX PRO 6000 | `profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json`: stock Strata v0.2.11 (engine 0.1.57), Qwen3.8-Flash-Next IQ3_S at the model's trained 262,144-token context with every expert in VRAM, four batch slots with per-slot stock DFlash2 drafters (`strata.drafting: "dflash2"`, one 85 MiB slot drafter per slot, `--spec 6`, no `--batch-mtp`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files), direct per-layer embedding (PLE) reads (`--ple-io direct`, `strata.ple_io: "direct"`), KV in VRAM (`--kv-streaming off`, `setup_args.kv_streaming: "off"`, 78 GiB available-RAM start floor), stock `parallel_stack` and `gdn_stack` in `strata.engine_env`, conversation parking (the engine's 8,192 MiB cache) and bare `--prefill auto` (32,768-token ceiling) | `profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json`: the same v0.2.11 + OMP 18.16.0 settings with per-slot multi-token prediction (MTP, `--batch-mtp`, `strata.batch_mtp: true`) |
| RTX 5090 (**default**) | `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0.json`: stock Strata v0.2.11 (engine 0.1.57), Coder IQ1_M at 262,144 tokens, KV in VRAM (`--kv-streaming off`, `setup_args.kv_streaming: "off"`), elastic KV growth (`--kv-grow`, `strata.kv_grow: true`), stock `gdn_stack` in `strata.engine_env` (34 GiB available-RAM start floor; requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller) | `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0.json`: the same family on stock Strata v0.2.10 (engine 0.1.56) + OMP 18.16.0 |
| RTX 5090 (qualified alternative) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json`: stock Strata v0.2.10 (engine 0.1.56), Coder IQ1_M at 131,072 tokens (34 GiB available-RAM start floor; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; stays on v0.2.10 after `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0.json` failed G15 twice) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0.json` |
| RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) | `profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0.json`: stock Strata v0.2.11 (engine 0.1.57) + OMP 18.16.0, IQ3_S at 262,144 tokens across both cards, stock roles (`--gpu-roles 0=main,1=helper`, RTX 4090 as Main staged last), manual layer split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, `strata.trim_stage_weights: true`), stock DFlash2 drafter alone (`strata.drafting: "dflash2"`, `--draft dflash2 --draft-fallback none`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; drops `--pipeline-windows 2`), no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`, `strata.ple_io: "direct"`), engine `sm_86` default table (`sm86_table`) and stock `gdn_stack` in `strata.engine_env`, engine's 8,192 MiB automatic conversation cache | `profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0.json`: the same DFlash2 family on stock Strata v0.2.10 (engine 0.1.56) + OMP 18.16.0 (with `profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0.json` kept as an older qualified MTP alternative) |

- On the RTX PRO 6000 (`rtxpro6000-win-a`), `strata.ple_io: "direct"` (`--ple-io direct`,
  [OPERATIONS.md](OPERATIONS.md#stock-ple-direct-reads)) reads the 26.8 GiB PLE table from the model file on SSD
  instead of locking it in RAM at start, `strata.drafting: "dflash2"`
  ([UPSTREAM.md](UPSTREAM.md#stock-dflash2-batch-slot-arm-v0211--0157)) gives each of the four batch slots its own
  85 MiB DFlash2 drafter (`--spec 6`, no `--batch-mtp`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2`
  files with `STRATA_NO_ACQUIRE=1`), `setup_args.kv_streaming: "off"` (`--kv-streaming off`, 78 GiB available-RAM start
  floor) keeps KV in VRAM without `--kv-resident 32768`, and `strata.engine_env` pins stock `serve/server.py`'s
  Linux-only nine-switch `parallel_stack` and two-switch `gdn_stack`
  ([UPSTREAM.md](UPSTREAM.md#strata-v0211-setup-and-start-path-review-engine-0157)). Against its v0.2.11 batch-MTP
  rollback ([measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160)), single-request decode
  rose +20-26% (`1.201` at depth 0, `1.258` at 8K, `1.203` at 32K, `1.142` at 100K, `1.216` on warm 32K) with TTFT ~1.0,
  while concurrent short-request throughput/latency (`w2/c2` total `0.885` and per-request `0.794`, TPOT `1.242`;
  `w2/c4` total `0.937`, TPOT `1.089`; latency +7-20%; `4 × 32K` `0.995`) and output-burst spacing (longest gap +12%,
  p95 inter-event gap +7-12%) missed the 5% rule, which the owner overrode (`"Override: qualify DFlash2 as PRO current"`),
  and the requalification chain at `b812df9` (`f3a8a77`, with complete G15 rerun in `637b616`) measured 31.0-35.7 s
  restart readiness (G16 31.0 s, G20 31.0 s, G21 35.7 s), 83.55 GiB G10 Windows commit headroom (127.14 GiB available RAM)
  of a 219.70 GiB limit, and G24 15/18 (pilot 5/6, batch wall 627 s). Its v0.2.11 batch-MTP rollback
  (`strata.batch_mtp: true`, `--batch-mtp`, [OPERATIONS.md](OPERATIONS.md#stock-per-slot-mtp); qualified under the owner's
  override of its 3 of 100 `w2/c2` A/B misses against v0.2.10 driven by baseline block A3's 8.86 ms TPOT and 0.253 s gap)
  measured 30.9-31.4 s chain restart readiness (G16 31.1 s, G20 30.9 s, G21 31.4 s), 81.73 GiB G10 Windows commit headroom
  (127.23 GiB available RAM; 83.05 / 129.12 GiB on v0.2.10) of a 219.70 GiB limit, and G24 16/18 (pilot 5/6, batch wall
  549 s). GDN tensor-core numerics are not bit-exact upstream, and engine
  env pins are reviewed per engine release (`ENGINE_ENV_REVIEWED_ENGINES`, engines `0.1.55`, `0.1.56` and `0.1.57`), so
  the next engine needs a fresh review. The v0.2.11 PRO `UD-Q4_K_XL` screen
  (`profiles/win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0.json`,
  slower than the v0.2.11 IQ3_S profile in every measured workload: single-request decode 0.85-0.91x, total throughput
  0.73-0.84x) and v0.2.9 PRO model candidates
  (`profiles/win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0.json`,
  `profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0.json` and
  `profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0.json`) stay comparison-only
  drafts.
- On the pair, pinning manual `strata.setup_args.layer_split: "24"` (the layer the automatic planner chose),
  `strata.trim_stage_weights: true` (`--trim-stage-weights`, [OPERATIONS.md](OPERATIONS.md#stock-stage-weight-trim)),
  `strata.ple_io: "direct"` (`--ple-io direct`, keeping the 26.8 GiB PLE table on direct SSD reads and the engine's
  8,192 MiB automatic conversation cache enabled), `strata.engine_env` `sm86_table` + `gdn_stack`, and stock DFlash2
  drafting alone (`strata.drafting: "dflash2"`,
  `--draft dflash2 --draft-model <root>\data\dflash2\qwen3.8-flash-next-dflash2.q4_0-selq4.pack --draft-fallback none --draft-conf 0.35 --draft-vocab <root>\data\dflash2\draft_vocab.bin`,
  packed offline during `install` by stock `tools/dflash2_pack.py` from pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744e85c17364dcc54a6a420af7135d4c7f6` `config.json` and
  `model.safetensors`, with `STRATA_NO_ACQUIRE=1` and no silent MTP fallback;
  [UPSTREAM.md](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)) drops `--pipeline-windows 2` and sizes the expert caches
  at 19.41 GiB on the RTX 3090 and 17.90 GiB on the RTX 4090 on engine 0.1.57 (vs 19.41 / 18.31 GiB on the v0.2.10 `df2`
  rollback and 19.14 / 17.75 GiB on the v0.2.10 `pw2` `env86g` MTP alternative). In three paired cold starts against its
  v0.2.10 `df2` rollback, `w1` / `w3` throughput was `1.008` / `0.999`, TTFT was ~`1.0`, TPOT was `0.98-0.99`, decode
  was `0.966-1.022` and prefill was `0.988-1.062`, while 4 of 88 checks missed on burstiness only (`w1` longest gap
  p50/p95/max `1.125-1.126`, depth-0 p95 inter-event gap `1.096`); after the owner overrode those misses (`"Override:
  run the main chain"`), the requalification chain at `772a418` (`ba574d5`) and complete G13 rerun at `611c342`
  (`3144675`) passed all 14 measured gates (G10 28.70 GiB commit headroom of 135.69 GiB and 66.35 GiB available RAM,
  G16/G20/G21 40.5 / 40.5 / 40.8 s, G17 near-limit task 61.1 s, G24 15/18, pilot 5/6, batch wall 896 s), keeping the
  qualified v0.2.10 `df2` DFlash2 profile (G10 27.51 GiB commit headroom and 65.65 GiB available RAM, G16/G20/G21
  43.1 / 43.2 / 43.4 s, G17 near-limit task 59.0 s, G24 17/18, batch wall 916 s) as its rollback and the v0.2.10 `pw2`
  `env86g` MTP profile as an older qualified alternative. The measurement-only v0.2.8 stock-residency roles draft
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0.json`),
  the held v0.2.7 roles draft (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2.json`,
  PLE in RAM, cache off, 1.03 GiB commit headroom; [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)),
  the unmeasured v0.2.7 default-split draft, the default and split-32 v0.2.3 drafts and the v0.1.44.1 pair release
  remain draft, not qualified ([decision](DECISION.md)).
- On the RTX 5090 (`rtx5090-win-a`),
  `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0.json` is the default, pinning
  `setup_args.kv_streaming: "off"` (`--kv-streaming off`), `strata.kv_grow: true` (`--kv-grow`) and `strata.engine_env`
  `gdn_stack` (v0.2.11 vs v0.2.10 A/B: `w1` 512/512 throughput `1.011`, TTFT `0.970`, decode `0.965-1.008`, prefill
  `0.988-1.138`, 100K TTFT `0.969`, while `w3` 32K single-request throughput `0.917`, TTFT p50 `1.097` and TPOT p50
  `1.051` missed from engine 0.1.57's 32,768-token bare `--prefill auto` chunks and was overridden by the owner as
  `"Override: accept it, run the chains"`), with a 34 GiB available-RAM start floor and a 4,352 MiB automatic
  conversation cache (rolling back to
  `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0.json`; the unpinned-GDN v0.2.9
  fallback `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0.json` stays an uninstalled
  draft). Operating condition: the host's Docker Desktop and WSL, which run its production NInfer container, must be
  stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script or returned
  through the owner's fleet controller (a WSL-up start was refused at 7.3 GiB available RAM while another of the
  owner's agents held host memory; untested on an idle host). The 131K profile
  (`profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json`, rolling back to
  `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0.json`; 34 GiB start floor) stays the qualified
  alternative for running with Docker Desktop and WSL up (the production container stopped by the fleet controller),
  because `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0.json` failed G15 twice and is not qualified.
- Display placement is part of the pair's profile: the earlier `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9`
  requires moving the display back to the RTX 3090.
- Single-card RTX 3090 profiles are not rollbacks while both cards are installed: they name GPU 0, now the RTX 4090.
  The Coder IQ1_M profile on v0.1.40.3 with OMP 18.8.4 stays qualified for single-card RTX 3090 hosts, and the fourth
  tuple's profiles (stock Strata v0.1.34 + stock OMP 18.4.10) remain qualified single-card rollbacks and stay
  qualified on the single-card RTX 4090.
- [Compatibility](COMPATIBILITY.md) lists every profile. Other operating systems, models and context sizes are
  unqualified.

<details>
<summary>Earlier qualified tuples and profile lineage</summary>

- **RTX PRO 6000:** earlier qualified history starts with the v0.2.10 + OMP 18.16.0 `kvvram-envpg` profile
  (`slots4-batchmtp-pledirect-kvvram-envpg-parking`), then the v0.2.9 + OMP 18.15.0 `kvvram-envpg` and batch-MTP +
  PLE-direct base (`slots4-batchmtp-pledirect-parking`) profiles, then the v0.2.8 + OMP 18.14.0 batch-MTP + PLE-direct
  (`slots4-batchmtp-pledirect-parking`), PLE-direct (`slots4-pledirect-parking`) and `slots4-parking` profiles, then the
  262K `slots4-parking` choices on v0.2.7 + OMP 18.13.2, then v0.2.3 + OMP
  18.12.6 (seven old v0.2.3-v0.2.9 IQ3_S host roots on the PRO were pruned on 2026-11-06 with the owner's approval),
  then v0.2.1, v0.1.44.1, v0.1.43.1 and v0.1.43 with OMP 18.10.1, v0.1.42 with OMP 18.8.9, then v0.1.41 with
  OMP 18.8.6 at 262K and 131K, then stock Strata v0.1.40.3 with OMP 18.8.4, then OMP 18.8.3, and before them
  `profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json`, without those three choices.
- **RTX 5090:** the v0.2.9 + OMP 18.15.0 262K `kvvram-kvgrow-envg` and 262K base (`coder-iq1m-262k`) profiles, v0.2.8 +
  OMP 18.14.0 (262K and 131K), v0.2.7 + OMP 18.13.2 (262K and 131K),
  v0.2.3 + OMP 18.12.6 (131K and 262K; host integration roots removed on 2026-11-02 with the owner's approval),
  v0.2.1 + OMP 18.10.1 (131K and 262K; host integration roots removed on 2026-10-28), v0.1.44.1 + OMP 18.10.1 (131K and
  262K), v0.1.43.1 + OMP 18.10.1, v0.1.43 + OMP 18.10.1, v0.1.42 + OMP 18.8.9, v0.1.41 + OMP 18.8.6 and v0.1.40.3 + OMP
  18.8.4 are retained as earlier qualified history.
- **RTX 4090 + RTX 3090 pair (`rtx3090-win-a`):** the v0.2.10 + OMP 18.16.0 `pw2` `env86g` MTP profile
  (`pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking`), the v0.2.9 + OMP 18.15.0 `env86g`
  (`roles-split24-trimweights-pledirect-env86g-parking`) and split-24 trim + PLE-direct base
  (`roles-split24-trimweights-pledirect-parking`) profiles, the v0.2.8 + OMP 18.14.0 split-24 trim + PLE-direct
  (`roles-split24-trimweights-pledirect-parking`; three v0.2.8/v0.2.9 pair roots were pruned on 2026-11-06 with the
  owner's approval) and initial PLE-direct (`roles-pledirect-parking`) stock-roles
  profiles, the v0.2.7 + OMP 18.13.2 PLE-direct stock-roles profile, the v0.2.3 + OMP 18.12.6
  stock-roles profile, the v0.2.1 default-split profile (host root removed on 2026-10-28), the v0.1.43.1 and v0.1.43
  262K parking profiles and the v0.1.42 262K parking and 131K display-on-RTX-4090 profiles stay earlier qualified
  history before `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` (display on the RTX 3090).
</details>

## Requirements

- Windows 11 x64 with an NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB, sm_120) that no other program
  computes on; it may drive the display. Tested driver 616.92.
- At least 96 GiB RAM with **78 GiB available when starting** (same on the v0.2.11 `batchmtp` rollback and the v0.2.10
  and v0.2.9 `kvvram-envpg` profiles; 74 GiB on the earlier v0.2.9 batch-MTP + PLE-direct base profile), and a page
  file: the running engine holds about 56.0 GB resident and commits about 133.4 GB on the current v0.2.11 `df2`
  profile (56.0 GB resident and 134.8 GB committed on the v0.2.11 `batchmtp` rollback and v0.2.10 `kvvram-envpg`
  profile; 56.1 GB resident and 134.9 GB committed on v0.2.9 `kvvram-envpg`; 73.7 GB resident and 136.6 GB committed on
  the v0.2.9 and v0.2.8 batch-MTP + PLE-direct streamed-KV profiles; 101.3 GB resident and 135.1 GB committed on v0.2.8
  `slots4-parking` where the 26.8 GiB PLE table is locked in RAM), including up to 8,192 MiB of parked conversations
  (RAM + page file).
- About 98.7 GB free disk for the DFlash2 integration root (the current PRO `df2` root measured 98.7 GB, 83.6 GB of
  it model shards; 96.7 GB on the v0.2.11 `batchmtp` rollback); `doctor` wants 93 GiB free on the current `df2` profile
  (91 GiB on the `batchmtp` rollback).
- Python 3.13 via the `py` launcher, Git for Windows, and network access to GitHub and Hugging Face for the
  one-time download. Inference itself needs no network.
- Measured install and start timings: G26 records the guarded install and launch example in a new integration root
  alongside earlier tuples, not on a fresh OS (see [the measurements](MEASUREMENTS.md)). On the current v0.2.11 `df2`
  profile, G26 ran on an already prepared root (`install` 25.8 s, `start` 56.3 s; 21.6 s and 52.9 s on the v0.2.11
  `batchmtp` rollback; 22.0 s and 50.3 s on v0.2.10; first `install` in a new root on v0.2.8 batch-MTP took 1,063.2 s
  and `start` 58.3 s); measured restarts took 31.0-35.7 s (G16 31.0 s, G20 31.0 s, G21 35.7 s; 30.9-31.4 s on the
  v0.2.11 `batchmtp` rollback with G16 31.1 s, G20 30.9 s and G21 31.4 s; 31.0-31.3 s on v0.2.10 and v0.2.9
  `kvvram-envpg`, 35.1-39.7 s on the v0.2.9 base profile and 35.5-51.5 s on v0.2.8 batch-MTP).

The other qualified profiles (alongside the PRO's 98.7 GB `df2` and 96.7 GB `batchmtp` roots, the RTX 5090 roots of Strata v0.2.11 and v0.2.10 + OMP 18.16.0
each took 70.9 GB for the 262K `kvvram-kvgrow-envg` default and the 131K alternative, the current display-on-RTX-4090
262K pair `df2` DFlash2 roots on v0.2.11 and v0.2.10 each took 97.8 GB while the `v0.2.10` `env86g` (`pw2`) alternative
and earlier `v0.2.9` / `v0.2.8` roots each took 95.7 GB, the single-card RTX 3090 root of v0.1.40.3 + OMP 18.8.4 took
69 GB, and the fourth tuple's low-RAM root 99 GB on the RTX 4090; `doctor` wants 93 GiB free on the current `df2` PRO
and pair profiles, 91 GiB on the PRO `batchmtp` rollback and `pw2` pair alternative, and 90 GiB on the RTX 5090 and
earlier profiles):

| Profile | GPU | RAM: total / available at start | Ready after `start` |
|---|---|---|---|
| `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0` | RTX 4090 + RTX 3090, 24 GB each, display on RTX 4090 | 86 / 78 GiB, plus a page file (28.70 GiB commit headroom of 135.69 GiB serving in G10 on `v0.2.11` `df2`, 27.51 GiB on the v0.2.10 `df2` rollback, 27.54 GiB on the v0.2.10 `pw2` alternative) | 40.5-40.8 s on measured chain restarts (G16 40.5 s, G20 40.5 s, G21 40.8 s; 43.1-43.4 s on the v0.2.10 `df2` rollback); G26 start wall 52.6 s (install 37.0 s on an already prepared root; 74.3 s and 33.1 s on the v0.2.10 `df2` rollback; 820.3 s first install on v0.2.8) |
| `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0` (default) | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 64.5 GB; requires Docker Desktop and WSL stopped on the host) | 18.5-19.3 s on measured restarts (G16 18.5 s, G20 19.0 s, G21 19.3 s; 19.2-19.5 s on the v0.2.10 rollback); G26 start wall 22.3 s (install 11.9 s on an already prepared root; 22.4 s and 11.7 s on v0.2.10; 365.6 s first install on v0.2.8) |
| `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` (qualified alternative; stays on v0.2.10) | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 64.8 GB; starts with Docker Desktop and WSL running) | 18.7-18.9 s on measured restarts (G16 18.7 s, G20 18.7 s, G21 18.9 s; 16.1-26.8 s on the v0.2.9 rollback); G26 start wall 36.2 s (install 10.7 s on an already prepared root; 297.8 s first install on v0.2.8) |
| `win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` | RTX 3090, 24 GB | 60 / 34 GiB | 17-19 s |
| `win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10` (fourth tuple) | RTX 4090, 24 GB, stock low-RAM mode | 30 / 16 GiB | about 15 s |
## Install and start

Run from a checkout of this repository (PowerShell). The integration root is dedicated to this tool; nothing is
written to `%APPDATA%\Strata` or to your normal OMP configuration.

```powershell
git clone https://github.com/alphastorm/omp-strata.git "$env:USERPROFILE\src\omp-strata"
Set-Location "$env:USERPROFILE\src\omp-strata"
$prof = "profiles\win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json"
$root = "$env:USERPROFILE\omp-strata-0.2.11-omp18.16.0-df2-kvvram-envpg-262k"   # one root per candidate; never reuse another candidate's root

py -3 scripts\omp_strata.py validate --profile $prof               # profile pins and budgets, no host access
py -3 scripts\omp_strata.py doctor   --profile $prof --root $root  # read-only host and install inspection
py -3 scripts\omp_strata.py fetch    --profile $prof --root $root  # ~86 GB, resumable, SHA-256 verified before use
py -3 scripts\omp_strata.py install  --profile $prof --root $root  # unmodified stock setup.py, local verified inputs
py -3 scripts\omp_strata.py keygen   --profile $prof --root $root  # private API key file, never printed
py -3 scripts\omp_strata.py start    --profile $prof --root $root  # 127.0.0.1:18090, key required, ~31.0-35.7 s to ready on restarts (56.3 s in G26)
py -3 scripts\omp_strata.py status   --profile $prof --root $root
```

`start` returns once authenticated identity checks pass (model id, 262,144-token context, `Strata 0.1.57` — the
v0.2.11 engine component version, not `0.2.11` — and unauthenticated requests refused). It refuses to start when the
port is taken by anything it does not own, when another program uses the GPU (a display is allowed), or when less than
78 GiB RAM is available.

## Use OMP

`launch-omp` runs the pinned stock OMP binary with the isolated `omp-strata` profile: every model role pinned to
the local Strata model, up to four requests at once (the server's batch slots), extension/skill/rule discovery off,
speculative compaction off, provider credentials scrubbed from the environment, and the Strata key passed privately.
Run it from the project you want to work on:

```powershell
Set-Location C:\path\to\your\project
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json" --root "$env:USERPROFILE\omp-strata-0.2.11-omp18.16.0-df2-kvvram-envpg-262k"
```

Arguments after `--` go to OMP, for example a non-interactive turn:

```powershell
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json" --root "$env:USERPROFILE\omp-strata-0.2.11-omp18.16.0-df2-kvvram-envpg-262k" -- -p --auto-approve "Run the tests and fix the failing one."
```
Flags that would change the provider, model, profile, configuration or extension loading are refused.

## Stop

```powershell
py -3 scripts\omp_strata.py stop --profile $prof --root $root
```

`stop` terminates only processes whose PID, creation time and executable match what `start` recorded (the wrapper,
the server and everything currently beneath it, deepest first) and is safe to repeat. To remove the integration
completely, stop it and delete the integration root.

See `docs/OPERATIONS.md` for restarts, logs and failure handling, and `docs/SECURITY.md` for what is and is not
isolated.
