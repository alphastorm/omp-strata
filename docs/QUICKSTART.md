# Quickstart

Stock Oh My Pi (OMP) 18.18.3 runs against a local stock Strata v0.2.13 server. Pick the profile for your host; the same
commands work with any of them, and every profile keeps its own integration root and ledger.

| Host | Current qualified profile | Qualified rollback |
|---|---|---|
| RTX PRO 6000 | `profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json`: stock Strata v0.2.13 (engine 0.1.59), Qwen3.8-Flash-Next IQ3_S at the model's trained 262,144-token context with every expert in VRAM, four batch slots with per-slot stock DFlash2 drafters (`strata.drafting: "dflash2"`, one 85 MiB slot drafter per slot, window 8 `--spec 8`, engine cap 8, written at every start by stock `drafting.apply` rather than into the config, no `--batch-mtp`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; qualified non-current alternate: `profiles/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json`, pinning stock's tuned `qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack` release asset via `model.dflash2_source.tuned`, which stock v0.2.13 runs at `--draft-conf 0.55` on this card), direct per-layer embedding (PLE) reads (`--ple-io direct`, `strata.ple_io: "direct"`), KV in VRAM (`--kv-streaming off`, `setup_args.kv_streaming: "off"`, 78 GiB available-RAM start floor), stock `parallel_stack` and `gdn_stack` in `strata.engine_env`, conversation parking (the engine's 8,192 MiB cache) and bare `--prefill auto` (32,768-token ceiling) | `profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0.json`: the same standard-pack DFlash2 family on stock Strata v0.2.12 (engine 0.1.58) + OMP 18.18.0 (not the tuned-pack alternate) |
| RTX 5090 (**default**) | `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3.json`: stock Strata v0.2.13 (engine 0.1.59), Coder IQ1_M at 262,144 tokens, KV in VRAM (`--kv-streaming off`, `setup_args.kv_streaming: "off"`), elastic KV growth (`--kv-grow`, `strata.kv_grow: true`), stock `gdn_stack` in `strata.engine_env` (34 GiB available-RAM start floor; requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller) | `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0.json`: the same family on stock Strata v0.2.12 (engine 0.1.58) + OMP 18.18.0 |
| RTX 5090 (qualified alternatives) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3.json`: stock Strata v0.2.13 (engine 0.1.59), Coder IQ1_M at 131,072 tokens (34 GiB available-RAM start floor; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; qualified following the same window's passing 262K A/B, as in v0.2.12); qualified non-current alternate: `profiles/win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3.json`, full-model Qwen3.8-Flash-Next IQ3_S at 131,072 tokens in stock low-RAM resident mode (`--resident-experts`, stock's planner pick for this host: `11,616` expert slots in VRAM at `22.04 GiB` and `29.77 GiB` of experts page-locked in RAM; 36 GiB available-RAM and 138 GiB free-disk floors; the Coder stays the default) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0.json`: 131K Coder on stock Strata v0.2.12 (engine 0.1.58) + OMP 18.18.0 (the full-model IQ3_S 131K low-RAM profile is a qualified alternate, not the rollback) |
| RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) | `profiles/win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3.json`: stock Strata v0.2.13 (engine 0.1.59) + OMP 18.18.3, IQ3_S at 262,144 tokens across both cards, stock roles (`--gpu-roles 0=main,1=helper`, RTX 4090 as Main staged last), manual layer split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, `strata.trim_stage_weights: true`), stock DFlash2 drafter alone (`strata.drafting: "dflash2"`, `--draft dflash2 --draft-fallback none`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; drops `--pipeline-windows 2`) with `strata.drafting_args: {"--draft-conf": "0.5"}` (written to stock `user_args` with stock `write_config`), no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`, `strata.ple_io: "direct"`), engine `sm_86` default table (`sm86_table`), stock `gdn_stack` and exact two-pass QSA block selection (`select_two_pass`, `STRATA_SELECT_TWO_PASS=1`) in `strata.engine_env`, engine's 8,192 MiB automatic conversation cache (the id omits `-parking` only to stay within 120 characters and keeps the same stock tips) | `profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0.json`: the v0.2.12 + OMP 18.18.0 two-pass DFlash2 profile at stock `--draft-conf 0.35` (with the v0.2.12 `env86g`, v0.2.11 and v0.2.10 `df2` profiles and the v0.2.10 `pw2` `env86g` MTP profile kept in earlier qualified history) |

- On the RTX PRO 6000 (`rtxpro6000-win-a`), `strata.ple_io: "direct"` (`--ple-io direct`,
  [OPERATIONS.md](OPERATIONS.md#stock-ple-direct-reads)) reads the 26.8 GiB PLE table from the model file on SSD
  instead of locking it in RAM at start, `strata.drafting: "dflash2"`
  ([UPSTREAM.md](UPSTREAM.md#big-blackwell-dflash2-defaults)) gives each of the four batch slots its own 85 MiB DFlash2
  drafter (window 8 `--spec 8`, engine cap 8 — was window 6 in v0.2.12, written by stock `drafting.apply` at every start rather than into the config — no `--batch-mtp`, packed offline from pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` files with `STRATA_NO_ACQUIRE=1`), `setup_args.kv_streaming: "off"`
  (`--kv-streaming off`, 78 GiB available-RAM start floor) keeps KV in VRAM without `--kv-resident 32768`, and
  `strata.engine_env` pins stock's nine-switch `parallel_stack` and two-switch `gdn_stack` (moved into the engine as
  Linux-only defaults in v0.2.13, so Windows groups stay explicit and checked against the engine's tables;
  [UPSTREAM.md](UPSTREAM.md#strata-v0213-setup-and-start-path-review-engine-0159)). Against its v0.2.12 DFlash2 rollback
  ([measurements](MEASUREMENTS.md)), 11 of 90 paired cold-start checks missed from stock v0.2.13's DFlash2 window 8 on
  this card (inter-output-event latency p95 `1.171-1.188` at every depth, `w2/c1` largest gap p95 `1.173`, `w2/c4` TTFT
  p95 `1.118`, `w2/c4` TPOT max `1.067`; throughput `0.986-0.999`, per-request `0.964-1.015`, TTFT p50 `1.009-1.036`,
  TPOT p50 `0.981-1.033`, server decode reported `0.958-1.015`), which the owner overrode (`"Override the base as
  current, and also qualify the tuned pack as an alternate"`), and the requalification chain (`2af52b8`) passed every
  gate including G15, G17 and G18L, with G24 15/18 (`tool-loop` 0/3, as v0.2.12). Its qualified non-current alternate on
  the same tuple,
  `profiles/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json`,
  pins stock's tuned DFlash2 release asset (`qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack`, 339,694,592 bytes,
  SHA-256 `4df2e5ab…664c`) as `model.dflash2_source.tuned`, which stock v0.2.13 runs at `--draft-conf 0.55` instead of
  `0.35` on one `sm_120` card of 48 GB or more ([UPSTREAM.md](UPSTREAM.md#big-blackwell-dflash2-defaults)): it missed 15
  of 90 checks against v0.2.12 on the same window-8 burstiness (inter-output p95 `1.169-1.172`, `w2/c1` largest gap p95
  `2.151`, `w2/c4` TTFT p50 `1.129`) with `w2/c2` per-request `1.084` and TPOT p50 `0.928`, qualified as an alternate
  under the owner's decision, and passed every gate in its requalification chain (`8ab88b0`, G24 15/18 with `tool-loop`
  1/3). Its rollback is the qualified v0.2.12 DFlash2 profile
  (`profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0.json`, not the
  tuned-pack alternate; 31.1-31.3 s chain restart readiness with G16 31.1 s, G20 31.2 s and G21 31.3 s, 83.13 GiB G10
  commit headroom with 126.94 GiB available RAM, and G24 15/18, pilot 6/6, batch wall 522 s; the v0.2.12 `df2tuned`
  alternate at 31.0-31.4 s readiness and 83.24 GiB commit headroom and the v0.2.11 `df2` and `batchmtp` profiles move to
  earlier qualified history). GDN tensor-core numerics are not bit-exact upstream, and engine env pins are reviewed per
  engine release (`ENGINE_ENV_REVIEWED_ENGINES`, engines `0.1.55`, `0.1.56`, `0.1.57`, `0.1.58` and `0.1.59`), so the
  next engine needs a fresh review. The v0.2.13 standard-pack `--draft-conf 0.55` arm
  (`profiles/win11-rtxpro6000-iq3s-262k-slots4-df2conf055-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json`,
  withdrawn before install because the window-8 burstiness is not a confidence effect; `"Not qualified"` at `b2e9730`),
  the v0.2.12 two-pass arm
  (`profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0.json`,
  `STRATA_SELECT_TWO_PASS=1`, which passed its 200K cold TTFT bar at `0.978` against `0.98` but missed 3 of 96 checks on
  four-request TTFT p50 `1.114` and two-request TPOT p95 `1.056` / max `1.076`; owner: `"Keep the base"`), the v0.2.11
  RTX PRO 6000 quality-first comparison drafts — one-slot `IQ3_S`
  (`profiles/win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json`), one-slot
  Unsloth `UD-Q5_K_XL`
  (`profiles/win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json`) and
  six-expert `DeepSeek-V4.1-Flash-1017` `IQ2_XS`
  (`profiles/win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0.json`) — the v0.2.11 four-slot
  `UD-Q4_K_XL` speed screen
  (`profiles/win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0.json`, slower than
  the v0.2.11 four-slot IQ3_S batch-MTP profile in every measured workload: single-request decode 0.85-0.91x, total
  throughput 0.73-0.84x) and the v0.2.9 model candidates
  (`profiles/win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0.json`,
  `profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0.json` and
  `profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0.json`) stay drafts, not
  qualified ([decision](DECISION.md)).
- On the pair, pinning manual `strata.setup_args.layer_split: "24"` (the layer the automatic planner chose),
  `strata.trim_stage_weights: true` (`--trim-stage-weights`, [OPERATIONS.md](OPERATIONS.md#stock-stage-weight-trim)),
  `strata.ple_io: "direct"` (`--ple-io direct`, keeping the 26.8 GiB PLE table on direct SSD reads and the engine's
  8,192 MiB automatic conversation cache enabled), `strata.engine_env` `sm86_table` + `gdn_stack` + `select_two_pass`
  (`STRATA_SELECT_TWO_PASS=1`, exact two-pass QSA block selection for long prompts;
  [UPSTREAM.md](UPSTREAM.md#stock-engine-opt-in-groups-v0212--0158)), stock DFlash2 drafting alone
  (`strata.drafting: "dflash2"`, packed offline during `install` by stock `tools/dflash2_pack.py` from pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744e85c17364dcc54a6a420af7135d4c7f6` `config.json` and
  `model.safetensors`, with `STRATA_NO_ACQUIRE=1` and no silent MTP fallback;
  [UPSTREAM.md](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)), and `strata.drafting_args: {"--draft-conf": "0.5"}`
  (stock's slot-step value for the pair's per-card slots, which stock cannot compute on a split, written to stock
  `user_args` with stock `write_config` so the start's server line shows `--draft-conf 0.5`;
  [UPSTREAM.md](UPSTREAM.md#reviewed-dflash2-confidence-pins)) drops `--pipeline-windows 2` (19.40 GiB expert cache on
  the RTX 3090 and 17.90 GiB on the RTX 4090 on engine 0.1.58, vs 19.41 / 17.90 GiB on v0.2.11 `df2`, 19.41 / 18.31 GiB
  on v0.2.10 `df2` and 19.14 / 17.75 GiB on v0.2.10 `pw2` `env86g`). After engine 0.1.59's stage order was measured and
  admitted (`6eb9f05`), the `--draft-conf 0.5` profile passed all 96 plain checks against v0.2.12 (targeted cold decode
  `1.021` `[1.020, 1.049, 0.993]`, neutral with one pair below `1.00`; throughput `1.016` / `0.998`, per-request `1.027`
  / `0.993`, TTFT p50 `1.005` / `1.001`, TPOT p50 `0.973` / `1.009`; decode 100K `1.061`, warm 32K `1.054`, 32K `1.044`)
  and, after `fb8740a` fixed `install` verification for stock v0.2.13 setup re-runs carrying `user_args` into `args`
  (`carry_user_args`), passed every gate in its requalification chain at `7c2d25e` (`440fa1b`: G15, G17, G18 and G18L
  pass, G24 16/18 with `tool-loop` 1/3) under `"Run the --draft-conf 0.5 main; it becomes current if every gate
  passes"`, becoming the pair's current profile with the qualified v0.2.12 `env86gt` two-pass DFlash2 profile
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0.json`:
  G10 28.21 GiB commit headroom of 135.69 GiB and 65.74 GiB available RAM, G16/G20/G21 55.4 / 55.3 / 55.5 s, G17
  near-limit task 57.7 s, G24 15/18, pilot 6/6, batch wall 968 s) as its rollback. The v0.2.13 `env86gt` draft
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3.json`,
  which missed 6 of 96 checks on one 32K request: `w3/c1` TPOT p50 `1.054`, p95 `1.069`, max `1.070`; largest gap p50
  `1.119`, p95 `1.239`, max `1.252`), the v0.2.13 `STRATA_QSA_SPLIT_ATTN` draft
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3.json`,
  which missed 2 of 96 checks on `w1` largest gap p95 `1.075` / max `1.092` with targeted cold decode `1.003 < 1.02`;
  both blocked with `"Not qualified"` at `b2e9730`), the v0.2.12 W4A8 draft
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0.json`,
  `STRATA_IQ4_W4A8=2` in `iq4nl_w4a8`, which missed its A/B with cold-TTFT geomean `1.000` over 8K/32K/100K against the
  required `0.98`, 32K decode `0.917` `[0.926, 0.932, 0.894]`, server decode time `1.089` and single-request max
  inter-token gap p50 `1.153` `[1.027, 1.378, 1.084]`), the measurement-only v0.2.8 stock-residency roles draft
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0.json`),
  the held v0.2.7 roles draft (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2.json`,
  PLE in RAM, cache off, 1.03 GiB commit headroom; [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)),
  the unmeasured v0.2.7 default-split draft, the default and split-32 v0.2.3 drafts and the v0.1.44.1 pair release
  remain draft, not qualified ([decision](DECISION.md)).
- On the RTX 5090 (`rtx5090-win-a`),
  `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3.json` is the default, pinning
  `setup_args.kv_streaming: "off"` (`--kv-streaming off`), `strata.kv_grow: true` (`--kv-grow`) and `strata.engine_env`
  `gdn_stack` (passed all 88 checks in its v0.2.13 vs v0.2.12 A/B: throughput `w1 1.006` / `w3 0.995`, per-request
  `1.024` / `0.975`, TTFT p50 `0.989` / `1.002`, TPOT p50 `0.975` / `1.023`, cold decode `0.986-1.018`, prefill
  `0.998-1.075`; every gate passed including G15 and G18L, G24 16/18 with `tool-loop` 1/3 at `d3c96fb`), with a 34 GiB
  available-RAM start floor, rolling back to
  `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0.json` (4,096 MiB automatic
  conversation cache in G19; the v0.2.13 `STRATA_SPEC_COST` draft
  `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3.json` missed 3 of 88 and 2 of 88
  checks with targeted cold decode `1.012 < 1.02` and was not adopted, and the v0.2.13 full-model IQ3_S 262K low-RAM
  screen `profiles/win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3.json` refused its first
  start on a missing elastic K/V line, so both stay drafts at `b2e9730`, alongside the v0.2.12 two-pass draft
  `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0.json` and the uninstalled v0.2.9
  fallback `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0.json`). Operating condition: the
  host's Docker Desktop and WSL, which run its production NInfer container, must be stopped; after WSL restarts, that
  container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller (a
  WSL-up start was refused at 7.3 GiB available RAM while another of the owner's agents held host memory; untested on an
  idle host). The 131K Coder profile
  (`profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3.json`, rolling back to
  `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0.json`; 34 GiB start floor) is the current 131K
  alternative for running with Docker Desktop and WSL up (the production container stopped by the fleet controller): it
  followed the 262K pass without a separate A/B (as in v0.2.12) and passed every gate (`d0c2e28`, G24 16/18). The
  full-model IQ3_S 131K low-RAM resident profile
  (`profiles/win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3.json`, `--resident-experts`, stock's planner pick for
  this host: `11,616` expert slots in VRAM `22.04 GiB`, `29.77 GiB` of experts page-locked in RAM; 36 GiB available-RAM
  and 138 GiB free-disk floors) is a qualified non-current alternate (`6e2dda2`, every gate passed including G15, G17,
  G18 and G18L, G24 16/18 with `tool-loop` 1/3, after deleting five superseded RTX 5090 roots freeing `C:` from `98.1`
  to `156.6 GiB`; the Coder stays the default).
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

- **RTX PRO 6000:** earlier qualified history starts with the v0.2.12 + OMP 18.18.0 `df2tuned` tuned-pack alternate
  (`slots4-df2tuned-pledirect-kvvram-envpg-parking`), then the v0.2.11 + OMP 18.16.0 `df2` DFlash2
  (`slots4-df2-pledirect-kvvram-envpg-parking`) and `batchmtp` `kvvram-envpg`
  (`slots4-batchmtp-pledirect-kvvram-envpg-parking`) profiles, then the v0.2.10 + OMP 18.16.0 `kvvram-envpg` profile
  (`slots4-batchmtp-pledirect-kvvram-envpg-parking`), then the v0.2.9 + OMP 18.15.0 `kvvram-envpg` and batch-MTP +
  PLE-direct base (`slots4-batchmtp-pledirect-parking`) profiles, then the v0.2.8 + OMP 18.14.0 batch-MTP + PLE-direct
  (`slots4-batchmtp-pledirect-parking`), PLE-direct (`slots4-pledirect-parking`) and `slots4-parking` profiles, then the
  262K `slots4-parking` choices on v0.2.7 + OMP 18.13.2, then v0.2.3 + OMP
  18.12.6 (seven old v0.2.3-v0.2.9 IQ3_S host roots on the PRO were pruned on 2026-11-06 with the owner's approval),
  then v0.2.1, v0.1.44.1, v0.1.43.1 and v0.1.43 with OMP 18.10.1, v0.1.42 with OMP 18.8.9, then v0.1.41 with
  OMP 18.8.6 at 262K and 131K, then stock Strata v0.1.40.3 with OMP 18.8.4, then OMP 18.8.3, and before them
  `profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json`, without those three choices.
- **RTX 5090:** the v0.2.11 + OMP 18.16.0 262K `kvvram-kvgrow-envg` profile, the v0.2.10 + OMP 18.16.0 262K
  `kvvram-kvgrow-envg` and 131K profiles (five superseded RTX 5090 roots were deleted on 2026-11-09 with the owner's
  approval), the v0.2.9 + OMP 18.15.0 262K `kvvram-kvgrow-envg`, 262K base (`coder-iq1m-262k`) and 131K profiles,
  v0.2.8 + OMP 18.14.0 (262K and 131K), v0.2.7 + OMP 18.13.2 (262K and 131K),
  v0.2.3 + OMP 18.12.6 (131K and 262K; host integration roots removed on 2026-11-02 with the owner's approval),
  v0.2.1 + OMP 18.10.1 (131K and 262K; host integration roots removed on 2026-10-28), v0.1.44.1 + OMP 18.10.1 (131K and
  262K), v0.1.43.1 + OMP 18.10.1, v0.1.43 + OMP 18.10.1, v0.1.42 + OMP 18.8.9, v0.1.41 + OMP 18.8.6 and v0.1.40.3 + OMP
  18.8.4 are retained as earlier qualified history.
- **RTX 4090 + RTX 3090 pair (`rtx3090-win-a`):** the v0.2.12 + OMP 18.18.0 `df2` `env86g` DFlash2 base profile
  (`df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking`), the v0.2.11 and v0.2.10 + OMP 18.16.0 `df2`
  `env86g` DFlash2 profiles (`df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking`), the v0.2.10 + OMP
  18.16.0 `pw2` `env86g` MTP profile (`pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking`), the v0.2.9 +
  OMP 18.15.0 `env86g`
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
- At least 96 GiB RAM with **78 GiB available when starting** (same on the v0.2.13 `df2tuned` alternate, the v0.2.12 `df2`
  rollback and `df2tuned` alternate, the v0.2.11 `df2` and `batchmtp` profiles and the v0.2.10 and v0.2.9 `kvvram-envpg`
  profiles; 74 GiB on the earlier v0.2.9 batch-MTP + PLE-direct base profile), and a page file: the running engine holds
  about 56.2 GB resident and commits about 133.6 GB on the v0.2.12 `df2` rollback (56.2 GB resident and 133.5 GB
  committed on the v0.2.12 `df2tuned` alternate; 56.0 GB resident and 133.4 GB committed on v0.2.11 `df2`; 56.0 GB
  resident and 134.8 GB committed on the v0.2.11 `batchmtp` and v0.2.10 `kvvram-envpg` profiles; 56.1 GB resident and
  134.9 GB committed on v0.2.9 `kvvram-envpg`; 73.7 GB resident and 136.6 GB committed on the v0.2.9 and v0.2.8
  batch-MTP + PLE-direct streamed-KV profiles; 101.3 GB resident and 135.1 GB committed on v0.2.8 `slots4-parking` where
  the 26.8 GiB PLE table is locked in RAM), including up to 8,192 MiB of parked conversations (RAM + page file).
- About 98.8 GB free disk for the DFlash2 integration root (the PRO v0.2.12 `df2` root measured 98.8 GB, 83.6 GB of it
  model shards; 99.4 GB on the v0.2.12 `df2tuned` alternate; 98.7 GB on v0.2.11 `df2`; 96.7 GB on v0.2.11 `batchmtp`);
  `doctor` wants 93 GiB free on the current `df2` profile and its v0.2.12 `df2` rollback (94 GiB on the `df2tuned`
  alternate, 91 GiB on v0.2.11 `batchmtp`).
- Python 3.13 via the `py` launcher, Git for Windows, and network access to GitHub and Hugging Face for the
  one-time download. Inference itself needs no network.
- Measured install and start timings: G26 records the guarded install and launch example in a new integration root
  alongside earlier tuples, not on a fresh OS (see [the measurements](MEASUREMENTS.md)). On the v0.2.12 `df2` rollback,
  G26 ran on an already prepared root (`install` 25.6 s, `start` 54.2 s; 33.1 s and 38.9 s on the v0.2.12 `df2tuned`
  alternate; 25.8 s and 56.3 s on v0.2.11 `df2`; 21.6 s and 52.9 s on v0.2.11 `batchmtp`; 22.0 s and 50.3 s on v0.2.10;
  first `install` in a new root on v0.2.8 batch-MTP took 1,063.2 s and `start` 58.3 s); measured restarts on v0.2.12 took
  31.1-31.3 s (G16 31.1 s, G20 31.2 s, G21 31.3 s; 31.0-31.4 s on the v0.2.12 `df2tuned` alternate with G16 31.1 s,
  G20 31.0 s and G21 31.4 s; 31.0-35.7 s on v0.2.11 `df2` with G16 31.0 s, G20 31.0 s and G21 35.7 s; 30.9-31.4 s on
  v0.2.11 `batchmtp`; 31.0-31.3 s on v0.2.10 and v0.2.9 `kvvram-envpg`, 35.1-39.7 s on the v0.2.9 base profile and
  35.5-51.5 s on v0.2.8 batch-MTP).

The other qualified profiles (alongside the PRO's 98.8 GB `df2`, 99.4 GB `df2tuned`, 98.7 GB v0.2.11 `df2` and 96.7 GB
v0.2.11 `batchmtp` roots, the RTX 5090 Coder roots of Strata v0.2.12 + OMP 18.18.0 and v0.2.11 / v0.2.10 + OMP 18.16.0
each took 70.9 GB for the 262K `kvvram-kvgrow-envg` default and the 131K alternative, the display-on-RTX-4090 262K pair
`df2` DFlash2 roots on v0.2.12 `env86gt` and `env86g`, v0.2.11 and v0.2.10 each took 97.8 GB while the `v0.2.10` `env86g`
(`pw2`) alternative and earlier `v0.2.9` / `v0.2.8` roots each took 95.7 GB, the single-card RTX 3090 root of v0.1.40.3 +
OMP 18.8.4 took 69 GB, and the fourth tuple's low-RAM root 99 GB on the RTX 4090; `doctor` wants 138 GiB free on the RTX
5090 full-model IQ3_S 131K low-RAM alternate, 94 GiB on the PRO `df2tuned` alternate, 93 GiB on the current `df2` PRO
and `df2conf05` pair profiles, 91 GiB on the PRO `batchmtp` and `pw2` pair profiles, and 90 GiB on the RTX 5090 Coder
and earlier profiles):

| Profile | GPU | RAM: total / available at start | Ready after `start` |
|---|---|---|---|
| `win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3` | RTX 4090 + RTX 3090, 24 GB each, display on RTX 4090 | 86 / 78 GiB, plus a page file (28.21 GiB commit headroom of 135.69 GiB serving in G10 on the `v0.2.12` `env86gt` rollback, 28.18 GiB on `v0.2.12` `env86g`, 28.70 GiB on `v0.2.11` `df2`, 27.51 GiB on `v0.2.10` `df2`, 27.54 GiB on `v0.2.10` `pw2`) | 55.3-55.5 s on measured `v0.2.12` `env86gt` chain restarts (G16 55.4 s, G20 55.3 s, G21 55.5 s; 55.2-55.6 s on `v0.2.12` `env86g`; 40.5-40.8 s on `v0.2.11` `df2`); G26 start wall 67.0 s on `v0.2.12` `env86gt` (install 33.4 s on an already prepared root; 67.0 s and 33.2 s on `v0.2.12` `env86g`; 52.6 s and 37.0 s on `v0.2.11` `df2`; 820.3 s first install on v0.2.8) |
| `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` (default) | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 64.6 GB on the `v0.2.12` rollback; requires Docker Desktop and WSL stopped on the host) | 19.1-19.3 s on measured `v0.2.12` restarts (G16 19.2 s, G20 19.1 s, G21 19.3 s; 18.5-19.3 s on `v0.2.11`); G26 start wall 22.4 s on `v0.2.12` (install 12.7 s on an already prepared root; 22.3 s and 11.9 s on v0.2.11; 365.6 s first install on v0.2.8) |
| `win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3` (qualified alternative) | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 64.7 GB on the `v0.2.12` rollback; starts with Docker Desktop and WSL running) | 16.6-18.9 s on measured `v0.2.12` restarts (G16 16.6 s, G20 16.6 s, G21 18.9 s; 18.7-18.9 s on `v0.2.10`); G26 start wall 36.0 s on `v0.2.12` (install 12.7 s on an already prepared root; 36.2 s and 10.7 s on v0.2.10; 297.8 s first install on v0.2.8) |
| `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3` (qualified non-current alternate) | RTX 5090, 32 GB, stock low-RAM resident mode | 45 / 36 GiB, plus a page file (`11,616` expert slots in VRAM at `22.04 GiB`, `29.77 GiB` of experts page-locked in RAM; 138 GiB free-disk floor) | every gate passed in its `v0.2.13` requalify chain (`6e2dda2`) |
| `win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` | RTX 3090, 24 GB | 60 / 34 GiB | 17-19 s |
| `win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10` (fourth tuple) | RTX 4090, 24 GB, stock low-RAM mode | 30 / 16 GiB | about 15 s |
## Install and start

Run from a checkout of this repository (PowerShell). The integration root is dedicated to this tool; nothing is
written to `%APPDATA%\Strata` or to your normal OMP configuration.

```powershell
git clone https://github.com/alphastorm/omp-strata.git "$env:USERPROFILE\src\omp-strata"
Set-Location "$env:USERPROFILE\src\omp-strata"
$prof = "profiles\win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json"
$root = "$env:USERPROFILE\omp-strata-0.2.13-omp18.18.3-df2-kvvram-envpg-262k"   # one root per candidate; never reuse another candidate's root

py -3 scripts\omp_strata.py validate --profile $prof               # profile pins and budgets, no host access
py -3 scripts\omp_strata.py doctor   --profile $prof --root $root  # read-only host and install inspection
py -3 scripts\omp_strata.py fetch    --profile $prof --root $root  # ~86 GB, resumable, SHA-256 verified before use
py -3 scripts\omp_strata.py install  --profile $prof --root $root  # unmodified stock setup.py, local verified inputs
py -3 scripts\omp_strata.py keygen   --profile $prof --root $root  # private API key file, never printed
py -3 scripts\omp_strata.py start    --profile $prof --root $root  # 127.0.0.1:18090, key required, ~31.1-31.3 s to ready on v0.2.12 restarts (54.2 s in G26)
py -3 scripts\omp_strata.py status   --profile $prof --root $root
```

`start` returns once authenticated identity checks pass (model id, 262,144-token context, `Strata 0.1.59` — the
v0.2.13 engine component version, not `0.2.13` — and unauthenticated requests refused). It refuses to start when the
port is taken by anything it does not own, when another program uses the GPU (a display is allowed), or when less than
78 GiB RAM is available.

## Use OMP

`launch-omp` runs the pinned stock OMP binary with the isolated `omp-strata` profile: every model role pinned to
the local Strata model, up to four requests at once (the server's batch slots), extension/skill/rule discovery off,
background self-update and the setup wizard off (`update.auto: false`, `startup.checkUpdate: false`,
`startup.setupWizard: false`), speculative compaction off, provider credentials scrubbed from the environment, and the
Strata key passed privately. Run it from the project you want to work on:

```powershell
Set-Location C:\path\to\your\project
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json" --root "$env:USERPROFILE\omp-strata-0.2.13-omp18.18.3-df2-kvvram-envpg-262k"
```

Arguments after `--` go to OMP, for example a non-interactive turn:

```powershell
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json" --root "$env:USERPROFILE\omp-strata-0.2.13-omp18.18.3-df2-kvvram-envpg-262k" -- -p --auto-approve "Run the tests and fix the failing one."
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
