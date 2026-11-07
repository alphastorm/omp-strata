# Decision (2026-11-06)

Scope: stock Oh My Pi (OMP) → stock Strata on Windows 11, single user per host over authenticated local loopback,
plus the separately qualified Mac Studio SSH local-forward route to the RTX PRO 6000.

| Host or route | Current qualified selection | Tuple, model and context | Qualified rollback |
|---|---|---|---|
| `rtxpro6000-win-a` (RTX PRO 6000; default candidate in `tests/candidate.py`) | `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` | Strata v0.2.11 (engine 0.1.57) + OMP 18.16.0; Qwen3.8-Flash-Next IQ3_S at the trained 262,144-token context, every expert in VRAM, four batch slots with per-slot stock DFlash2 drafters (`strata.drafting: "dflash2"`, one 85 MiB slot drafter per slot, `--spec 6`, no `--batch-mtp`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; +20-26% single-request decode vs `v0.2.11` batch-MTP, qualified under the owner's override of its concurrent short-request throughput/latency and output-burst A/B misses), direct per-layer embedding (PLE) reads (`--ple-io direct`, `strata.ple_io: "direct"`), KV in VRAM (`--kv-streaming off`, `setup_args.kv_streaming: "off"`, 78 GiB available-RAM start floor), stock server `parallel_stack` and `gdn_stack` in `strata.engine_env`, conversation parking (8,192 MiB automatic cache) and bare `--prefill auto` (32,768-token ceiling); the `v0.2.11` quality-first one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and six-expert `DeepSeek V4.1-Flash IQ2_XS` drafts, the `v0.2.11` four-slot `UD-Q4_K_XL` screen and the `v0.2.9` `UD-IQ4_XS` / `NVFP4-QAD` model candidates stay comparison-only drafts | `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` (per-slot MTP `--batch-mtp` on v0.2.11 + OMP 18.16.0) |
| `rtx5090-win-a` (RTX 5090, **default**) | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0` | Strata v0.2.11 (engine 0.1.57) + OMP 18.16.0 and Coder IQ1_M at 262,144 tokens (default; KV in VRAM via `setup_args.kv_streaming: "off"`, elastic KV growth `--kv-grow` via `strata.kv_grow: true`, stock `gdn_stack` in `strata.engine_env`; 34 GiB available RAM at start; automatic conversation cache on at 4,352 MiB; qualified under the owner's override of its 32K-prompt single-request `w3` A/B miss from engine 0.1.57's 32,768-token bare `--prefill auto` chunk ceiling; the host's Docker Desktop and WSL, which run its production NInfer container, must be stopped, and after WSL restarts that container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller) | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` |
| `rtx5090-win-a` (RTX 5090, qualified alternative) | `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` | Strata v0.2.10 (engine 0.1.56) + OMP 18.16.0; Qwen3.8-Flash-Next Coder IQ1_M at 131,072 tokens (34 GiB available RAM at start; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; stays on `v0.2.10` after the `v0.2.11` 131K draft failed G15 twice) | `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0` |
| `rtx3090-win-a` (RTX 4090 + RTX 3090 pair, display on RTX 4090) | `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0` | Strata v0.2.11 (engine 0.1.57) + OMP 18.16.0; Qwen3.8-Flash-Next IQ3_S at the trained 262,144-token context, stock roles (RTX 4090 as Main), manual split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, `strata.trim_stage_weights: true`; 19.41 / 17.90 GiB expert caches on v0.2.11 `df2` vs 19.41 / 18.31 GiB on v0.2.10 `df2` rollback and 19.14 / 17.75 GiB on v0.2.10 `pw2` alternative), stock DFlash2 drafter alone (`strata.drafting: "dflash2"`, `--draft dflash2 --draft-fallback none`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; drops `--pipeline-windows 2`; qualified under the owner's override of its `w1` and depth-0 output-burst A/B misses), no batch slots, direct PLE reads (`--ple-io direct`, `strata.ple_io: "direct"`), engine `sm_86` default table (`sm86_table`) and stock `gdn_stack` in `strata.engine_env`, engine's 8,192 MiB automatic conversation cache; the `v0.2.8` stock-residency roles draft stays measurement-only | `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0` (with `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0` kept as an older qualified MTP alternative) |
| Mac Studio SSH client route to `rtxpro6000-win-a` | `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` | Stock OMP 18.16.0 over foreground `launch-omp` SSH local forward to the PRO's v0.2.11 262K four-slot DFlash2 profile (`df2`); independent G23 pass | `client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` (pins the PRO's v0.2.11 batch-MTP rollback; G23 passed) |

**What the current set accepts and what is not authorized:**

- **Quality-first comparison on the PRO keeps the four-slot `IQ3_S` DFlash2 incumbent (2026-11-06–07):** the three PRO
  quality-first drafts — one-slot `IQ3_S`
  (`win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`), one-slot Unsloth
  `UD-Q5_K_XL` (`win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`), and
  six-expert `DeepSeek-V4.1-Flash-1017` ISTA-DASLab `IQ2_XS` on stock `strata-dsv41` `0.1.57`
  (`win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0`, four-shard inputs, DSpark `auto` declined at
  load, one conversation, disk-slot persistence off) — inherit no receipts and change no current lane. On 22 frozen
  private coding tasks (`16` hard + `6` base, latency treated as a practical constraint rather than a `<= 2x`
  warm-turn/agent-time bar or the 5% same-model version non-regression rule, pre-registered `+3` paired-net replacement
  threshold), neither candidate beat the four-slot `IQ3_S` DFlash2 incumbent (`21/22` vs `20/22` on `UD-Q5_K_XL`, and
  `5/7` on `DeepSeek IQ2_XS` when the owner stopped its trial after `7` of `22` tasks, its best reachable paired net
  being `-1`), and the owner kept four batch slots (`"Skip second trials"`, `"We don't need to artificially restrict it
  to 1 session, C=4 is fine."`;
  [2026-11-07 update](#update-2026-11-07-quality-first-comparison-on-the-pro-keeps-the-four-slot-iq3_s-incumbent),
  [DeepSeek admission](UPSTREAM.md#deepseek-v41-flash-comparison-admission),
  [Qwen one-slot admissions](UPSTREAM.md#pro-quality-first-one-slot-comparison-admissions)). Other DeepSeek sets,
  six-shard layouts, vision, `--parallel` on DeepSeek and OMP config-rendering changes stay out of scope.
- **The PRO pins four-slot stock DFlash2 drafting alongside stock parallel and GDN engine environment stacks, KV in VRAM and direct PLE reads on Strata v0.2.11 + OMP 18.16.0:**
  on `rtxpro6000-win-a`, `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`
  is current (`tests/candidate.py` `CURRENT`, `"Override: qualify DFlash2 as PRO current"`), rolling back to its
  qualified `v0.2.11` batch-MTP sibling
  `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` (the `v0.2.10`
  `kvvram-envpg` and `v0.2.9` profiles move to earlier qualified history; seven old `v0.2.3–v0.2.9` IQ3_S host roots were
  pruned on 2026-11-06 with the owner's approval freeing `E:` from `115.5` to `202.5 GiB`). In addition to
  `strata.ple_io: "direct"` (`--ple-io direct`, reading the 26.8 GiB PLE table from the model file on SSD),
  `setup_args.kv_streaming: "off"` (`--kv-streaming off`, keeping KV in VRAM and dropping `--kv-resident 32768`; 78 GiB
  available-RAM start floor), `strata.engine_env` with stock `serve/server.py`'s Linux-only nine-switch parallel-slot
  stack (`PARALLEL_STACK_ENV`) and two-switch GDN tensor-core prompt stack (`GDN_STACK_CUDA`), and bare `--prefill auto`
  (engine `0.1.57`'s 32,768-token ceiling), it pins `strata.drafting: "dflash2"` on all four batch slots
  ([UPSTREAM.md](UPSTREAM.md#stock-dflash2-batch-slot-arm-v0211--0157): one 85 MiB slot drafter per slot under
  `STRATA_BATCH_DF2`, `70.22 GiB` free VRAM at start, `--spec 6`, no `--batch-mtp`, packed offline from pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` files with `STRATA_NO_ACQUIRE=1`; 93 GiB free-disk floor). Across three paired
  cold starts against its `v0.2.11` batch-MTP sibling
  ([measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160)), single-request decode rose +20–26%
  (`1.201` at depth 0, `1.258` at 8K, `1.203` at 32K, `1.142` at 100K, `1.216` on warm 32K, meeting the owner's +3%
  bar) with TTFT ~1.0, while 35 of 100 checks missed on concurrent short-request (`w2` 1,000-token) throughput and
  latency (`w2/c2` total throughput `0.885` and per-request `0.794`, TPOT `1.242`; `w2/c4` total `0.937`, TPOT `1.089`;
  latency +7–20%; `4 × 32K` `0.995`) and output-burst spacing (one-request longest gap +12%, p95 inter-event gap
  +7–12%); the owner overrode those misses on 2026-11-06 (~05:10Z: `"Override: qualify DFlash2 as PRO current"`), and
  its requalification chain (`06:05–06:34Z` at `b812df9`, published in `f3a8a77`, with an owner-approved complete G15
  rerun `06:41–06:44Z` at `b812df9` in `637b616` after the initial G15's first post-kill recall wrote the interrupted
  11,178-token essay) passed all 14 measured gates: 31.0 / 31.0 / 35.7 s restart readiness in G16 / G20 / G21 (G15
  rerun kill recall 29.2–29.3 s), 127.14 GiB available RAM and 83.55 GiB Windows commit headroom of a 219.70 GiB limit
  in G10 (GPU memory 73,496 MiB), 8,192 MiB automatic conversation cache (32 parks in G19), and G24 **15/18**
  (`tool-loop` `0/3`, others `3/3`, pilot **5/6**, batch wall `627.3 s`). Its qualified `v0.2.11` batch-MTP rollback
  (`strata.batch_mtp: true`, `--batch-mtp`; overridden at ~03:45Z as `"Override: chain + route, then arms"` after
  missing 3 of 100 checks vs `v0.2.10` at `w2/c2` driven by baseline block `A3`'s `8.86 ms` TPOT and `0.253 s` gap)
  measured 31.1 / 30.9 / 31.4 s restart readiness in G16 / G20 / G21 (G15 kill recall 44.5–45.4 s), 127.23 GiB available
  RAM and 81.73 GiB Windows commit headroom of a 219.70 GiB limit in G10 (GPU memory 74,918 MiB), 8,192 MiB automatic
  conversation cache (35 parks in G19), and G24 **16/18** (pilot **5/6**, batch wall `549.4 s`). Risks: GDN tensor-core
  prompt numerics are not bit-exact upstream, four-slot DFlash2
  trades concurrent short-request throughput (-6 to -12% total, -8 to -21% per-request) and burst spacing (+7 to +12%)
  for +20–26% single-request decode, and `strata.engine_env` and batch-slot DFlash2 pins are reviewed per engine release
  (`ENGINE_ENV_REVIEWED_ENGINES`, engines `0.1.55`, `0.1.56` and `0.1.57`;
  [UPSTREAM.md](UPSTREAM.md#strata-v0211-setup-and-start-path-review-engine-0157)), so the next engine release requires a
  fresh source review.
- **The RTX 5090 262K default pins the GDN stack, KV in VRAM and elastic KV growth on Strata v0.2.11 + OMP 18.16.0, while the 131K alternative stays on Strata v0.2.10 + OMP 18.16.0:**
  on `rtx5090-win-a`, `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0` is the host's default,
  rolling back to its `v0.2.10` `kvvram-kvgrow-envg` predecessor
  `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` (the `v0.2.9` `kvvram-kvgrow-envg` and base
  profiles move to earlier qualified history). It pins `strata.engine_env` `gdn_stack` (`GDN_STACK_CUDA`),
  `setup_args.kv_streaming: "off"` (`--kv-streaming off`, 34 GiB available-RAM start floor) and `strata.kv_grow: true`
  (`--kv-grow`), passing `v0.2.11` vs `v0.2.10` A/B on `w1` 512/512 throughput (`1.011`), TTFT (`0.970`), decode
  (`0.965–1.008`), prefill (`0.988–1.138`) and 100K TTFT (`0.969`) while missing 11 of 88 checks on the 32K-prompt
  single-request `w3` workload (`agg_tps` `0.917 [0.915, 0.924, 0.911]`, TTFT p50 `1.097 [1.099, 1.092, 1.100]`, TPOT
  p50 `1.051`) because engine `0.1.57`'s bare `--prefill auto` chunks prompts at up to 32,768 tokens on this card where
  `v0.2.10` used `8192` (`A` blocks 4.36–4.39 s TTFT and 25.2–25.6 tok/s vs `B` blocks 4.77–4.83 s and 23.0–23.4 tok/s;
  overridden by the owner on 2026-11-06 as `"Override: accept it, run the chains"`), sizing a 4,352 MiB automatic
  conversation cache in G19 (17 parks; G10 13.47 GiB available RAM and 20.30 GiB commit headroom of 85.15 GiB;
  G16/G20/G21 restart readiness 18.5–19.3 s; G24 17/18, pilot 6/6, batch wall 843.1 s). Operating condition is unchanged:
  the host's Docker Desktop and WSL (which run its production NInfer container) must be stopped, and after WSL restarts
  that container is recreated by the owner's pinned relaunch script or returned through the owner's fleet controller (a
  WSL-up start was refused at 7.3 GiB available RAM while another of the owner's agents held host memory; untested on an
  idle host). The unpinned-GDN `v0.2.9` fallback `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0`
  was prepared and never installed (draft). The 131K profile (`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`,
  rolling back to `v0.2.9` 131K; `v0.2.8` 131K is earlier qualified history) stays on `v0.2.10` for running with Docker
  Desktop and WSL up (the production container stopped by the fleet controller; 34 GiB start floor; G16/G20/G21
  18.7–18.9 s, 3,584 MiB cache, G24 16/18, pilot 6/6, batch wall 741.7 s) because the `v0.2.11` 131K draft
  (`win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`) failed G15 twice after the mid-generation engine kill (first
  rewriting the interrupted 8,028-token essay on the first recall in the main chain, and then ending both recalls in
  OMP's thinking-loop guard without the nonce in the owner-approved short-window G15 rerun) and is not qualified.
- **The pair pins stock DFlash2 drafting alone alongside stock roles with the RTX 4090 as Main, manual split 24 with stage weight trim, direct PLE reads, and the engine's `sm_86` default table and GDN stack on Strata v0.2.11 + OMP 18.16.0:**
  on `rtx3090-win-a`,
  `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`
  is current (`"Override: run the main chain"`), rolling back to its qualified `v0.2.10` `df2` DFlash2 predecessor
  `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
  (while the `v0.2.10` `pw2` `env86g` MTP profile
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
  remains qualified as an older alternative, and `v0.2.9` `env86g`, `v0.2.9` split-24 trim + PLE-direct base, `v0.2.8`
  split-24 trim, `v0.2.8` `roles-pledirect` and `v0.2.7` PLE-direct stay earlier qualified history; three `v0.2.8`/`v0.2.9`
  pair host roots were pruned on 2026-11-06 with the owner's approval freeing `C:` from `94.8` to `128.7 GiB`). It pins
  `--gpu-roles 0=main,1=helper`, `strata.setup_args.layer_split: "24"` (the layer the automatic planner chose),
  `strata.trim_stage_weights: true` (`--trim-stage-weights`, so each card loads only its own stage's dense weights:
  771 and 988 MiB instead of 1,466 and 2,019 MiB), `strata.ple_io: "direct"` (`--ple-io direct` on engine 0.1.57, keeping
  the 26.8 GiB PLE table on direct SSD reads so the engine's 8,192 MiB automatic conversation cache stays enabled),
  `strata.engine_env` with the engine's `sm_86` default table (`sm86_table`;
  [Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313)) and stock `gdn_stack` (`GDN_STACK_CUDA`), and
  stock DFlash2 drafting alone (`strata.drafting: "dflash2"`,
  `--draft dflash2 --draft-model <root>\data\dflash2\qwen3.8-flash-next-dflash2.q4_0-selq4.pack --draft-fallback none --draft-conf 0.35 --draft-vocab <root>\data\dflash2\draft_vocab.bin`,
  packed offline during `install` by stock `tools/dflash2_pack.py` from pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744e85c17364dcc54a6a420af7135d4c7f6` `config.json` and
  `model.safetensors`, with `STRATA_NO_ACQUIRE=1` and no silent MTP fallback;
  [UPSTREAM.md](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)). On engine 0.1.57 (which reserves 256 MiB plus an extra
  DFlash2 reserve on the last stage), the expert caches are 19.41 GiB on the RTX 3090 and 17.90 GiB on the RTX 4090 (vs
  19.41 / 18.31 GiB on `v0.2.10` `df2` and 19.14 / 17.75 GiB on `v0.2.10` `pw2`). In three paired cold starts against
  `v0.2.10` `df2`, `w1` / `w3` throughput was `1.008` / `0.999`, TTFT was ~`1.0`, TPOT was `0.98–0.99`, decode was
  `0.966–1.022` and prefill was `0.988–1.062`, while missing 4 of 88 checks on output-burst metrics (`w1` longest gap
  p50/p95/max `1.125–1.126`, depth-0 p95 inter-event gap `1.096`); the owner overrode those misses on 2026-11-06
  (~03:45Z: `"Override: run the main chain"`), the requalification chain (03:47–04:30Z, tooling `772a418`, published in
  `ba574d5`) and complete G13 rerun at `611c342` (04:32–04:37Z, published in `3144675`) passed all 14 measured gates with
  `[strata] drafting: DFlash2 alone (--draft dflash2, --draft-conf 0.35)` on every start (G10 `28.70 GiB` commit headroom
  of `135.69 GiB` and `66.35 GiB` available RAM; G16/G20/G21 `40.5 / 40.5 / 40.8 s`; G17 near-limit task `61.1 s`; G19
  `8,192 MiB` cache, 12 parks; G24 **15/18**, `tool-loop` `0/3`, others `3/3`, pilot `5/6`, batch wall `896.4 s`), and
  the qualified `v0.2.10` `df2` profile (G10 `27.51 GiB` commit headroom and `65.65 GiB` available RAM; G16/G20/G21
  `43.1 / 43.2 / 43.4 s`; G17 near-limit task `59.0 s`; G24 `17/18`, pilot `5/6`, batch wall `915.6 s`) stays its
  rollback. Stated risks: GDN numerics are not bit-exact, DFlash2 output arrives in up to 6-token verified bursts (and a
  conversation whose context rows were not drafted by DFlash2 drafts poorly on its first rounds while keeping the same
  answers), and the engine-env and DFlash2 pins need a fresh source review at the next engine release. The
  measurement-only v0.2.8 stock-residency draft
  (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`), the held v0.2.7 roles draft
  (PLE in RAM, cache off, 1.03 GiB commit headroom) and the unmeasured v0.2.7 default-split draft stay unqualified.
- **Integration qualification ≠ task quality ≠ runtime comparison ≠ default replacement:** each local ledger's
  21 pass and 3 not applicable (G22, G23 and G25) establishes integration correctness within stated limits, not
  perfection on coding tasks (G24 scored 15/18 on the PRO DFlash2 current profile, 16/18 on the PRO
  `v0.2.11` batch-MTP rollback, 17/18 on the RTX 5090 262K `v0.2.11` default, 16/18 on the RTX 5090 131K `v0.2.10`
  alternative, and 15/18 on the pair `v0.2.11` DFlash2 current profile, versus 16–18/18 on their `v0.2.10` and 14/18 on
  their `v0.2.9` rollbacks, with task failures retained in the denominator) and not runtime superiority.
- **Follow-up work packages (status):** the PRO `v0.2.11` quality-first comparison drafts
  (`win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`,
  `win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0` and
  `win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0`) stay comparison-only drafts after the
  2026-11-06–07 22-task comparison kept the four-slot `IQ3_S` DFlash2 incumbent, the PRO `v0.2.11` `UD-Q4_K_XL`
  comparison screen
  (`win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0`: slower than the `v0.2.11`
  four-slot IQ3_S batch-MTP profile in every measured workload: single-request decode 0.85–0.91x, total throughput
  0.73–0.84x) and the PRO `v0.2.9` model candidates (`win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0`
  and `win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0`, plus their Mac Studio routes) stay
  comparison-only drafts while a 30-task Terminal-Bench comparison has not run, and the `v0.2.11` RTX 5090 131K profile
  (`win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`) stays an unqualified draft after failing G15 twice.
- **G25 kept NInfer:** paired single-GPU G25 runs on 2026-10-03 met neither frozen superiority threshold (more
  completions or faster joint successes), so NInfer stays where it runs and no host switched its default runtime.
- **Boundaries that remain fixed:** no cloud fallback (every chat role routes to the pinned Strata provider); no
  durable engine state (after any engine restart OMP replays and cold-prefills the transcript); client routes
  inherit no server evidence and qualify no fleet or other client platform; each profile keeps its own root and
  ledger without repairing or replacing earlier ledgers; and qualification does not authorize a default switch or
  release publication.

<details>
<summary>Earlier qualified lineage and single-card / display rollback restrictions</summary>

The current rollbacks keep the same models, contexts and display placement as their current profiles: on the PRO and
the Mac Studio route, their 2026-11-06 Strata v0.2.11 with OMP 18.16.0 batch-MTP siblings
(`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` and
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`); on the RTX 5090 262K default and the
pair, their 2026-11-03 Strata v0.2.10 with OMP 18.16.0 predecessors (`coder-iq1m-262k-kvvram-kvgrow-envg` on the RTX 5090
and `df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking` on the pair, with the `v0.2.10` `pw2` `env86g` MTP
profile kept as an older qualified pair alternative); and on the RTX 5090 131K alternative (which stays on `v0.2.10`),
its 2026-11-02 Strata v0.2.9 with OMP 18.15.0 predecessor (`coder-iq1m-131k`).
Earlier history stays qualified in its own roots and ledgers: the 2026-11-03 Strata v0.2.10 with OMP 18.16.0 PRO and
Studio route profiles (`slots4-batchmtp-pledirect-kvvram-envpg-parking` and
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0`); the v0.2.9 with OMP 18.15.0 profiles
(`slots4-batchmtp-pledirect-kvvram-envpg-parking` and `slots4-batchmtp-pledirect-parking` on the PRO,
`coder-iq1m-262k-kvvram-kvgrow-envg` and `coder-iq1m-262k` on the RTX 5090,
`roles-split24-trimweights-pledirect-env86g-parking` and `roles-split24-trimweights-pledirect-parking` on the pair, and
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0` and
`client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0` on the Studio route); v0.2.8 with OMP 18.14.0 on the
PRO (`slots4-batchmtp-pledirect-parking`, `slots4-pledirect-parking` and `slots4-parking`), the RTX 5090
(`coder-iq1m-262k` and `coder-iq1m-131k`), the pair (`roles-split24-trimweights-pledirect-parking` and
`roles-pledirect-parking`), and the Studio route (`client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0` and
`client-rtxpro6000-262k-strata0.2.8-omp18.14.0`);
v0.2.7 with OMP 18.13.2 on all three hosts (the PRO `slots4-parking`, the RTX 5090 262K and 131K
profiles, and the pair `roles-pledirect-parking`) and the Studio route; v0.2.3 with OMP 18.12.6 on all three hosts
(including both the 131K and 262K RTX 5090 profiles, whose host integration roots were removed on 2026-11-02 with the
owner's approval, and the PRO and pair `v0.2.3–v0.2.9` superseded roots pruned on 2026-11-06 with the owner's approval,
plus the pair's stock-roles profile
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6`) and the Studio route; v0.2.1 with
OMP 18.10.1 on all three hosts and the Studio route (on 2026-10-28 the v0.2.1 integration roots were removed on every
host, so v0.2.1 profiles are earlier qualified history in their ledgers, no longer installed rollbacks); v0.1.44.1 with
OMP 18.10.1 on the PRO and RTX 5090 (including the 262K profile) and v0.1.43.1 on the pair; the PRO and RTX 5090
profiles on v0.1.43.1 and v0.1.43 with OMP 18.10.1, and the pair's v0.1.43 profile; each host's same 262K or 131K
profile on Strata v0.1.42 with OMP 18.8.9, then on the pair,
`win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9` keeps the same display placement on the RTX 4090,
while the earlier `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` requires moving the display back to the
RTX 3090. On the PRO and RTX 5090, earlier history stays qualified: on the PRO, Strata v0.1.41 with OMP 18.8.6 and the
same choices at 262,144 tokens, then at 131,072 tokens, then Strata v0.1.40.3 with OMP 18.8.4, then OMP 18.8.3, and
before it OMP 18.8.0 with Strata v0.1.40.2; on the RTX 5090, Strata v0.1.41 with OMP 18.8.6 and the same Coder IQ1_M,
then Strata v0.1.40.3 with OMP 18.8.4, then the fourth tuple (OMP 18.4.10, Strata v0.1.34, Coder IQ1_M), which also
remains the qualified record of the RTX 4090 in stock low-RAM mode (`rtx4090-win-a`). The single-card RTX 3090 profiles,
`win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` and the fourth tuple's, stay qualified for single-card RTX
3090 hosts, but are not rollbacks on `rtx3090-win-a` while both cards are installed: those profiles name GPU 0, now the
RTX 4090. On the Mac Studio, the 0.2.10 `kvvram-envpg`, 0.2.9 `kvvram-envpg` and batch-MTP base, 0.2.8 batch-MTP and
`slots4-parking`, 0.2.7, 0.2.3, 0.2.1, 0.1.44.1, 0.1.43.1, 0.1.43 and 0.1.42 262K routes and the 0.1.41 131K route
remain earlier qualified history.

</details>

| Date | What was decided | Section |
|---|---|---|
| 2026-11-07 | Quality-first comparison on `rtxpro6000-win-a` keeps the four-slot `IQ3_S` DFlash2 incumbent (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`, re-verified at `f9f9680`: 21 pass, 3 not applicable) and its Mac Studio route (`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`, G23 pass) unchanged: on 22 frozen private tasks (`16` hard + `6` base, one attempt per arm via `scripts/eval_taskset.py`, pre-registered `+3` paired-net replacement bar), the incumbent passed `21/22` (`215.4 s` median, `5,498.6 s` total, 1 critical mid-run empty reply on a passing task, capping any candidate's paired net at `+1`), one-slot Unsloth `UD-Q5_K_XL` passed `20/22` (`278.9 s` median, `6,437.9 s` total, paired net `-1`, exact sign test `p = 1.0`, median wall ratio `1.26`), and six-expert `DeepSeek-V4.1-Flash-1017` `IQ2_XS` on stock `strata-dsv41` `0.1.57` passed `5/7` before the owner stopped its trial after `7` of `22` tasks (`"Let's be pragmatic: Yes, it's safe to stop now."`; paired net `-2` over those `7`, `p = 0.5`, median wall ratio `3.9`, best reachable net `-1`); owner decisions `"Skip second trials"` and `"We don't need to artificially restrict it to 1 session, C=4 is fine."` keep four slots current and leave one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and six-expert `DeepSeek IQ2_XS` as comparison-only drafts (unscreened `UD-Q6_K_XL`, `Q8_0` and one-slot `UD-Q4_K_XL` drafts dropped at `80431b2` and `f9f9680`) | [Update, 2026-11-07: quality-first comparison on the PRO keeps the four-slot IQ3_S incumbent](#update-2026-11-07-quality-first-comparison-on-the-pro-keeps-the-four-slot-iq3_s-incumbent) |
| 2026-11-06 | Strata v0.2.11 (engine 0.1.57) + OMP 18.16.0 qualifies on the PRO (four-slot DFlash2 `df2` current at +20–26% single-request decode, G24 15/18, G15 rerun pass at `b812df9`, under the owner's override `"Override: qualify DFlash2 as PRO current"`, with the qualified v0.2.11 batch-MTP profile at G24 16/18 under `"Override: chain + route, then arms"` as its rollback), the RTX 5090 262K default (`kvvram-kvgrow-envg`, G24 17/18, under `"Override: accept it, run the chains"` for engine 0.1.57's 32,768-token bare `--prefill auto` `w3` A/B miss, with v0.2.10 as rollback), the pair DFlash2 (`df2`, G24 15/18, G13 note fix `611c342` + rerun, under `"Override: run the main chain"`, with v0.2.10 `df2` as rollback and v0.2.10 `pw2` `env86g` MTP as an older alternative), and the Studio route (`df2` current, G23 pass + `ROUTE OK` smoke at `b812df9`, with the v0.2.11 batch-MTP route at G23 pass + `ROUTE OK` smoke as its rollback; `01b4d9b`, CI matrix `69de6d2`), while the RTX 5090 131K alternative stays on v0.2.10 after the v0.2.11 131K draft failed G15 twice (including the owner-approved short-window G15 rerun), the PRO `UD-Q4_K_XL` screen (slower than the v0.2.11 IQ3_S profile in every measured workload: single-request decode 0.85–0.91x, total throughput 0.73–0.84x) stays comparison-only, and seven old PRO and three old pair roots are pruned with the owner's approval | [Update, 2026-11-06: v0.2.11 + OMP 18.16.0 on the PRO, RTX 5090 262K, pair and Studio route; 131K stays on v0.2.10](#update-2026-11-06-strata-v0211-with-omp-18160-qualifies-on-the-pro-rtx-5090-262k-pair-and-studio-route-131k-stays-on-v0210) |
| 2026-11-03 | Strata v0.2.10 (engine 0.1.56) + OMP 18.16.0 qualifies on every host and the Studio route under the 5% non-regression rule and sub-1 ms / first-SSE-frame resolution floor (`8a2c9ec`, CI matrix `f115173`): RTX 5090 262K (`kvvram-kvgrow-envg`, G24 18/18) and 131K (G24 16/18) qualify with v0.2.9 as rollback; PRO (`kvvram-envpg`, G24 16/18, G14 prompt fix `7971a1a` + rerun) and Studio route (`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0`, G23 pass + `ROUTE OK` smoke) qualify under the owner's override (`"Override: chain + G23"`) of the PRO concurrent short-prompt TTFT A/B miss (`w2/c2` p50 `1.052` / p95 `1.136`, `w2/c4` p50 `1.326`) with v0.2.9 as rollback; pair DFlash2 arm (`df2`, `strata.drafting: "dflash2"`, dropping `--pipeline-windows 2`; +8.2% to +13.6% cold decode vs `env86g` v0.2.10, meeting the +3% bar; chain at `837bc89`, published in `1f2d483`, G24 17/18, pilot 5/6, 915.6 s vs 1,044.7 s, G16/G20/G21 43.1/43.2/43.4 s) qualifies and becomes current under the owner's override (`"Run chain, make DFlash2 current"`) of its 6-token-window inter-event gap and queued-prefill A/B misses, with the qualified pair `env86g` (`pw2`) v0.2.10 profile (G24 16/18, G20 baseline fix `837bc89` + rerun) as its rollback; no upstream issue filed now | [Update, 2026-11-03: v0.2.10 + OMP 18.16.0 on every host and the Studio route](#update-2026-11-03-strata-v0210-with-omp-18160-qualifies-on-every-host-and-the-studio-route) |
| 2026-11-03 (morning) | Under the owner's override (`"Yes approved: Yes, if you approve an override. There's nothing in the pair profile to fix."`) of the `w1` 512/512 single-request A/B miss (`1.039` vs `>= 1.05`), the pair `v0.2.9` `env86g` tuning profile (`roles-split24-trimweights-pledirect-env86g-parking`, pinning `sm86_table` + `gdn_stack` in `strata.engine_env`) passes its 14-gate requalification chain (`d0a1254`; G24 15/18, pilot 5/6, 821.8 s vs 974.9 s; G16/G20/G21 43.5/43.6/43.9 s vs 55.4/55.5/55.6 s) and qualifies and becomes current (PR #74, CI run 41597184710 at `6b972fa`, receipts `1f699b4`, qualification `8bbf9a8`, CI matrix `98d8c32`), with the 2026-11-02 `v0.2.9` pair base profile as its rollback (`v0.2.8` split-24 trim moves to earlier qualified history) | [Update, 2026-11-02 (evening) and 2026-11-03: v0.2.9 tuning profiles and Studio route](#update-2026-11-02-evening-the-v029-tuning-profiles-on-the-pro-and-rtx-5090-and-the-studios-tuned-route-qualify) |
| 2026-11-02 (evening) | Stock v0.2.9 tuning profiles on the PRO (`kvvram-envpg`) and RTX 5090 262K (`kvvram-kvgrow-envg`) and the Studio's tuned route qualify and become current (`"Qualify and make current"`, PR #73, CI run 41499865044, commit `b802d5f`), with the 2026-11-02 v0.2.9 base profiles as rollbacks; pair `env86g` variant missed the 512/512 single-request A/B bar (`1.039` vs `>= 1.05`) before the owner overrode that bar (qualified 2026-11-03 above); PRO `UD-IQ4_XS` and `NVFP4-QAD` model candidates stay comparison-only drafts | [Update, 2026-11-02 (evening): v0.2.9 tuning profiles and Studio route](#update-2026-11-02-evening-the-v029-tuning-profiles-on-the-pro-and-rtx-5090-and-the-studios-tuned-route-qualify) |
| 2026-11-02 | Strata v0.2.9 + OMP 18.15.0 qualifies on the PRO (batch-MTP + PLE-direct), RTX 5090 (262K default and 131K alternative), pair (split-24 trim + PLE-direct) and Studio route (`"Push, PR, qualify on green CI"`, PR #72, CI run 41457827645, commit `4bb634d`); v0.2.8 is the rollback across all lanes; v0.2.3 RTX 5090 roots removed; feature-arm pins and UD-IQ4_XS / NVFP4-QAD Terminal-Bench preparation approved as follow-up work packages | [Update, 2026-11-02: v0.2.9 + OMP 18.15.0 on every host and the Studio route](#update-2026-11-02-strata-v029-with-omp-18150-qualifies-on-every-host-and-the-studio-route) |
| 2026-10-31 | Stock v0.2.8 tuning profiles and Studio route qualify (`"Qualify all; make PRO batch-MTP and pair trim current"`): PRO batch-MTP + PLE-direct (`--batch-mtp --ple-io direct`) becomes current with PLE-direct as qualified alternative and yesterday's `slots4-parking` as rollback; pair split-24 stage-weight trim + PLE-direct (`--layer-split 24 --trim-stage-weights --ple-io direct`) becomes current with yesterday's `roles-pledirect` as rollback; Studio route `client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0` qualifies with G23 and becomes current with yesterday's `v0.2.8` route as rollback | [Update, 2026-10-31: v0.2.8 tuning profiles and Studio route](#update-2026-10-31-stock-v028-tuning-profiles-and-the-studio-batch-mtp-route-qualify) |
| 2026-10-30 | Strata v0.2.8 + OMP 18.14.0 qualifies on the PRO, RTX 5090 (262K becomes the default; 131K stays the qualified alternative), pair PLE-direct and Studio route; v0.2.7 is the rollback across all lanes; G10 listener check fixed for Windows build 26300.9818 (`f9e8c74`); Strata#4518 fix measured on Windows | [Update, 2026-10-30: v0.2.8 + OMP 18.14.0 and RTX 5090 262K default](#update-2026-10-30-strata-v028-with-omp-18140-qualifies-on-every-host-and-the-studio-route-the-rtx-5090-262k-profile-becomes-its-default) |
| 2026-10-28 (afternoon) | Pair PLE-direct (`--ple-io direct`) and RTX 5090 262K opt-in (with Docker Desktop and WSL stopped) qualify on Strata v0.2.7 + OMP 18.13.2; v0.2.3 is the rollback across all lanes; v0.2.1 host roots pruned; pair PLE-in-RAM issue filed as [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518) | [Update, 2026-10-28 (afternoon): pair PLE-direct and 5090 262K qualify](#update-2026-10-28-afternoon-the-pairs-ple-direct-and-rtx-5090-262k-strata-v027-profiles-qualify) |
| 2026-10-28 | Morning post-landing correction (superseded for the pair's current selection above): pair v0.2.7 roles returned to draft on measured commit headroom | [Update, 2026-10-28: pair commit-headroom hold](#update-2026-10-28-post-landing-correction--the-pair-stays-on-v023-roles) |
| 2026-10-28 | Initial Strata v0.2.7 + OMP 18.13.2 qualification on the PRO, RTX 5090 131K, pair roles and Studio route (pair and 5090 262K dispositions superseded above); pair default-split draft held | [Initial update, 2026-10-28: qualified selections and held drafts](#update-2026-10-28-strata-v027-with-omp-18132-qualified-selections-and-held-drafts) |
| 2026-10-23 | Mac Studio route `client-rtxpro6000-262k-strata0.2.3-omp18.12.6` qualifies with G23 | [Update, 2026-10-23: Mac Studio route for v0.2.3](#update-2026-10-23-the-mac-studio-client-route-qualifies-for-the-pros-v023-profile) |
| 2026-10-23 | Strata v0.2.3 + OMP 18.12.6 qualifies on the PRO, the RTX 5090 (131K default, 262K opt-in) and the pair, which moves to stock roles with the RTX 4090 as Main | [Update, 2026-10-23: v0.2.3 on every host](#update-2026-10-23-strata-v023-with-omp-18126-qualifies-on-every-host) |
| 2026-10-21 | Mac Studio route `client-rtxpro6000-262k-strata0.2.1-omp18.10.1` qualifies with G23 | [Update, 2026-10-21: Mac Studio route for v0.2.1](#update-2026-10-21-the-mac-studio-client-route-qualifies-for-the-pros-v021-profile) |
| 2026-10-21 | Strata v0.2.1 + OMP 18.10.1 qualifies on the PRO, the RTX 5090 (131K default, 262K opt-in) and the pair; the pair accepted although slower | [Update, 2026-10-21: v0.2.1 on every host](#update-2026-10-21-strata-v021-with-omp-18101-qualifies-on-every-host) |
| 2026-10-15 | RTX 5090 Coder 262K (`…-strata0.1.44.1-omp18.10.1`) qualifies as opt-in; 131K stays current/default | [Update, 2026-10-15: RTX 5090 Coder 262K](#update-2026-10-15-rtx-5090-coder-262k-qualifies-as-opt-in-not-the-default) |
| 2026-10-14 | Mac Studio route `client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1` qualifies with G23 | [Update, 2026-10-14: Mac Studio route for v0.1.44.1](#update-2026-10-14-the-mac-studio-client-route-qualifies-for-the-pros-v01441-profile) |
| 2026-10-14 | Strata v0.1.44.1 + OMP 18.10.1 qualifies on PRO and RTX 5090; pair held on v0.1.43.1 over split regression | [Update, 2026-10-14: v0.1.44.1 on PRO and 5090; pair stays v0.1.43.1](#update-2026-10-14-strata-v01441-with-omp-18101-qualifies-on-the-pro-and-rtx-5090-the-pair-stays-on-v01431) |
| 2026-10-13 | Mac Studio route `client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1` qualifies (now rollback) | [Update, 2026-10-13: Mac Studio route for v0.1.43.1](#update-2026-10-13-the-mac-studio-client-route-qualifies-for-the-pros-v01431-profile) |
| 2026-10-13 | Strata v0.1.43.1 + OMP 18.10.1 qualifies on all three hosts (still current on pair; PRO/5090 rollback) | [Update, 2026-10-13: v0.1.43.1 on all three hosts](#update-2026-10-13-strata-v01431-with-omp-18101-qualifies-on-all-three-hosts) |
| 2026-10-12 | Mac Studio route `client-rtxpro6000-262k-strata0.1.43-omp18.10.1` qualifies | [Update, 2026-10-12: Mac Studio route for v0.1.43](#update-2026-10-12-the-mac-studio-client-route-qualifies-for-the-pros-v0143-profile) |
| 2026-10-12 | Strata v0.1.43 + OMP 18.10.1 qualifies on all three hosts (still the pair's rollback) | [Update, 2026-10-12: v0.1.43 on all three hosts](#update-2026-10-12-strata-v0143-with-omp-18101-qualifies-on-all-three-hosts) |
| 2026-10-12 | Mac Studio route `client-rtxpro6000-262k-strata0.1.42-omp18.8.9` qualifies | [Update, 2026-10-12: Mac Studio route for v0.1.42 262K](#update-2026-10-12-the-mac-studio-client-route-qualifies-for-the-pros-current-262k-profile) |
| 2026-10-11 | Pair qualifies at 262K with 8 GiB conversation parking on v0.1.42 + OMP 18.8.9 | [Update, 2026-10-11: pair at 262K with parking](#update-2026-10-11-the-pair-qualifies-at-262k-with-stock-conversation-parking) |
| 2026-10-11 | Pair qualifies at 131K with display on RTX 4090 on v0.1.42 + OMP 18.8.9 | [Update, 2026-10-11: pair with display on RTX 4090 (131K)](#update-2026-10-11-the-pair-qualifies-with-the-display-on-the-rtx-4090-131k-rollback) |
| 2026-10-11 | Strata v0.1.42 + OMP 18.8.9 qualifies on RTX PRO 6000 (262K) and RTX 5090 (131K) | [Update, 2026-10-11: v0.1.42 on PRO and RTX 5090](#update-2026-10-11-strata-v0142-with-omp-1889-qualifies-on-the-rtx-pro-6000-and-rtx-5090) |
| 2026-10-11 | Pair qualifies at 131K with pipeline windows 2 and display on RTX 3090 | [Update, 2026-10-11: pair with display on RTX 3090](#update-2026-10-11-the-pair-with-the-display-on-the-rtx-3090-qualifies-predecessor) |
| 2026-10-10 | RTX PRO 6000 qualifies at 262K context on Strata v0.1.41 + OMP 18.8.6 | [Update, 2026-10-10: PRO at 262K](#update-2026-10-10-the-rtx-pro-6000-qualifies-at-262k-context) |
| 2026-10-09 | PRO v0.1.41 + OMP 18.8.6 passes 23/30 on Terminal-Bench 2.1; profiles unchanged | [Update, 2026-10-09: PRO Terminal-Bench 23/30](#update-2026-10-09-on-terminal-bench-the-pros-strata-v0141-profile-passes-23-of-30) |
| 2026-10-09 | First Mac Studio remote client route (`client-rtxpro6000-strata0.1.41-omp18.8.6`) qualifies | [Update, 2026-10-09: PRO remote route from Mac](#update-2026-10-09-the-rtx-pro-6000-is-qualified-for-remote-use-from-a-mac) |
| 2026-10-09 | Strata v0.1.41 + OMP 18.8.6 qualifies on RTX 5090 | [Update, 2026-10-09: v0.1.41 on RTX 5090](#update-2026-10-09-strata-v0141-with-omp-1886-qualifies-on-the-rtx-5090) |
| 2026-10-08 | Strata v0.1.41 + OMP 18.8.6 qualifies on RTX PRO 6000 (131K) | [Update, 2026-10-08 (night): v0.1.41 on PRO](#update-2026-10-08-night-strata-v0141-with-omp-1886-qualifies-on-the-rtx-pro-6000) |
| 2026-10-08 | Strata v0.1.40.3 + OMP 18.8.4 qualifies on RTX PRO 6000, RTX 5090 and single-card RTX 3090 | [Update, 2026-10-08: v0.1.40.3 + OMP 18.8.4 on three GPUs](#update-2026-10-08-strata-v01403-with-omp-1884-qualifies-on-the-rtx-pro-6000-rtx-5090-and-rtx-3090) |
| 2026-10-07 | RTX PRO 6000 qualifies with four batch slots, parking and 32K chunks on v0.1.40.3 + OMP 18.8.3 | [Update, 2026-10-07 (evening): PRO slots and parking](#update-2026-10-07-evening-the-rtx-pro-6000-qualifies-with-batch-slots-and-conversation-parking) |
| 2026-10-07 | First RTX PRO 6000 qualification on v0.1.40.2 + OMP 18.8.0, with `compaction.asyncEnabled: false` | [Update, 2026-10-07 (later): PRO v0.1.40.2 + OMP 18.8.0](#update-2026-10-07-later-the-rtx-pro-6000-tuple-qualifies-with-omps-speculative-compaction-off) |
| 2026-10-07 | UD-Q4_K_XL ties IQ3_S (19/30) on Terminal-Bench; IQ3_S stays the PRO's model | [Update, 2026-10-07: UD-Q4_K_XL vs IQ3_S on Terminal-Bench](#update-2026-10-07-on-terminal-bench-the-largest-stock-build-ties-iq3_s-iq3_s-stays-the-pros-model) |
| 2026-10-06 | IQ3_S passes 55/60 private tasks on PRO; UD-Q4_K_XL costs prompt speed | [Update, 2026-10-06 (later): IQ3_S stays on PRO](#update-2026-10-06-later-iq3_s-stays-the-pros-model-the-largest-stock-build-costs-prompt-speed) |
| 2026-10-06 | RTX PRO 6000 runs IQ3_S 2.2-2.3x faster than RTX 4090 with all experts in VRAM | [Update, 2026-10-06: PRO vs RTX 4090 on IQ3_S](#update-2026-10-06-an-rtx-pro-6000-runs-iq3_s-22-23x-faster-than-the-rtx-4090-every-expert-in-vram) |
| 2026-10-05 | Strata v0.1.39 decodes faster on RTX 3090; hybrid-CPU `--pool-workers 15` within noise | [Update, 2026-10-05: Strata v0.1.39 vs v0.1.38](#update-2026-10-05-strata-v0139-decodes-faster-on-the-rtx-3090-its-hybrid-cpu-change-shows-no-clear-gain) |
| 2026-10-04 | Private 60-task evaluation: IQ3_S (58/60) where RAM holds it, Coder IQ1_M on 47 GiB RTX 5090 | [Update, 2026-10-04: Flash-Next vs 27B on 60-task set](#update-2026-10-04-on-the-owners-kind-of-work-flash-next-beats-the-27b) |
| 2026-10-03 | Paired G25 comparison against NInfer: keep NInfer, switch nothing; do not port durability | [Update, 2026-10-03: Strata against NInfer (G25)](#update-2026-10-03-strata-against-ninfer--keep-ninfer-switch-nothing) |
| 2026-10-03 | Fourth tuple (Strata v0.1.34 + OMP 18.4.10) qualifies on RTX 5090, RTX 3090 and RTX 4090 low-RAM | [Update, 2026-10-03: fourth tuple qualifies](#update-2026-10-03-the-fourth-tuple-qualifies-on-three-gpus) |
| 2026-10-03 | Stock calibration keeps Coder defaults; IQ3_S on RTX 3090 pins `--pcie-frac 0.20 --spec-min-p 0.70` draft | [Update, 2026-10-03: stock calibration](#update-2026-10-03-stratas-own-calibration-changes-nothing-for-the-coder) |
| 2026-10-03 | RTX 3090 128 GB long-context drafts: 262K trained context and 524K experimental YaRN | [Update, 2026-10-03: longer RTX 3090 contexts](#update-2026-10-03-longer-contexts-for-the-coder-on-the-rtx-3090) |
| 2026-10-02 | RTX 3090 128 GB model comparison: IQ3_S unlocked by RAM, Coder kept for coding, UD-Q4_K_XL rejected | [Update, 2026-10-02: RTX 3090 128 GB model selection](#update-2026-10-02-which-model-the-rtx-3090-should-run-with-128-gb) |
| 2026-10-01 | Third tuple (Strata v0.1.31 + OMP 18.4.8) draft runs on RTX 3090 and RTX 4090; only OMP half of G04 open | [Update, later on 2026-10-01: third tuple on 24 GB hosts](#update-later-on-2026-10-01-the-third-tuple-on-two-24-gb-hosts) |
| 2026-10-01 | Original second-candidate assessment: integration readiness, usefulness and engine-state durability | [1. Integration readiness](#1-integration-readiness-working-candidate-one-upstream-blocker-left) · [2. Usefulness](#2-usefulness-keep-as-an-optional-local-coding-backend) · [3. Durability](#3-further-investment-in-engine-state-durability-not-justified-now) |

## Update, 2026-11-07: quality-first comparison on the PRO keeps the four-slot IQ3_S incumbent

- **Owner decisions (pre-registered rule and verbatim answers, 2026-11-06–07).**
  - Pre-registered quality-first scope and decision rule (set before any candidate outcome): test whether a
    higher-fidelity model on `rtxpro6000-win-a` beats the qualified four-slot `IQ3_S` DFlash2 incumbent
    (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`, fingerprint
    `bc2c503183b7800e`) on the owner's coding work when latency is only a practical constraint, using 22 frozen tasks
    from the private task set (`16` hard + `6` base, each task's own budgets, one attempt per task and arm via
    `scripts/eval_taskset.py` through real stock OMP `18.16.0` sessions over an SSH loopback tunnel, after a fairness
    check before trial 1); run a second trial for the top two arms only if their trial-1 pass counts are within 2
    passes, and replace the incumbent only when a candidate achieves a paired net of at least **`+3`** passes with a
    critical-failure count no more than the incumbent's count **`+ 2`** (otherwise the incumbent stays). Screen Unsloth
    `UD-Q5_K_XL` (one slot) and `DeepSeek-V4.1-Flash-1017` ISTA-DASLab `IQ2_XS` (all six routed experts, stock
    `strata-dsv41` `0.1.57`) alongside the incumbent's one-slot form; keep one-slot `UD-Q4_K_XL` only as a fallback if
    `UD-Q5_K_XL` failed fit or fell below ~`127 tok/s` 32K decode, and leave `UD-Q6_K_XL` and `Q8_0` unscreened.
  - Verbatim owner decisions during and after trial 1 (2026-11-07):
    - Second trials: `"Skip second trials"` — the incumbent failed one task in trial 1 (`21/22`), so no candidate could
      exceed `+1` paired net.
    - One-slot vs four-slot `IQ3_S` (`404.4` vs `379.7 tok/s` single-request 32K decode): `"We don't need to
      artificially restrict it to 1 session, C=4 is fine."`
    - Stopping the DeepSeek trial after `7` of `22` tasks, when both of its misses were tasks the incumbent passed and its
      best reachable paired net was `-1`: `"Let's be pragmatic: Yes, it's safe to stop now."`
- **Unchanged current selection and comparison-only drafts (`e4741c9`–`f9f9680`).**
  - **Current and rollback selections stay unchanged** (re-verified at `f9f9680`): on `rtxpro6000-win-a`,
    `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` (21 pass, 3 not
    applicable;
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json))
    and the Mac Studio route
    `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` (G23 pass;
    [ledger](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json))
    stay current, rolling back to their qualified `v0.2.11` batch-MTP siblings
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` and
    `client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` (stock OMP `18.17.0`, released
    `2026-11-06T05:12:54Z`, was out of scope of this comparison).
  - **Comparison-only drafts retained (`releases/<id>/`, every gate `not_run`, no CI or campaign row):**
    - One-slot incumbent form:
      [`win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`](../profiles/win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json)
      (fingerprint `ab60b81c833c3839`, `83,617,662,656` model bytes;
      [ledger](../releases/win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0/qualification.json)).
    - One-slot Unsloth `UD-Q5_K_XL`:
      [`win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`](../profiles/win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json)
      (fingerprint `81cd556548451fe3`, `158,286,406,650` model bytes at `unsloth/Qwen3.8-Flash-Next-GGUF` revision
      `38bb39ee97821de2c9009abb7e93950eec396e66`;
      [ledger](../releases/win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0/qualification.json);
      [Qwen one-slot admissions](UPSTREAM.md#pro-quality-first-one-slot-comparison-admissions)).
    - Six-expert `DeepSeek-V4.1-Flash-1017` ISTA-DASLab `IQ2_XS`:
      [`win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0`](../profiles/win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0.json)
      (fingerprint `51642761f608b94c`, `273,803,809,901` model bytes across seven pinned files, separate package
      `strata-dsv41-0.1.57-windows-x86_64-cuda-cuda13.tar.gz` `422,613,464` bytes, SHA-256
      `bc1cbecc7553c3022e369bc1e0ed4f360ea26daf5dfc386dd0dde75be417941e`;
      [ledger](../releases/win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0/qualification.json);
      [DeepSeek admission](UPSTREAM.md#deepseek-v41-flash-comparison-admission)).
  - **Untested Qwen quantizations (dropped unscreened at `80431b2` and `f9f9680`):** one-slot `UD-Q4_K_XL` (draft
    fingerprint `811590f6eaa867b9`, `111,334,654,784` bytes; not needed after `UD-Q5_K_XL` passed fit and speed),
    `UD-Q6_K_XL` and `Q8_0` were not screened or evaluated on tasks. Stock Strata
    [`docs/QUANTS.md` at `v0.2.11`](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/docs/QUANTS.md)
    reports teacher-forced accuracy against `Q8_0` (`4.052` perplexity) on one AMD machine — **not task quality** — at
    `94.61%` same top token / `0.033` mean KL / `4.020` perplexity (`UD-Q6_K_XL`), `94.55%` / `0.038` / `4.024`
    (`UD-Q5_K_XL`), `93.09%` / `0.056` / `4.068` (`UD-Q4_K_XL`), and `87.69%` / `0.144` / `4.097` (`IQ3_S`); stock
    [`docs/DETAILS.md` at `v0.2.11`](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/docs/DETAILS.md)
    reports n-gram (`PLE` / Engram) table mean KL against `BF16` at `0.0125` (`Q8_0`) vs `0.0146` (`IQ4_NL`) with
    perplexity within `1%` either way (`UD-Q5_K_XL` and larger already carry the `Q8_0` table, and a separate `Q8_0`
    n-gram table for `UD-Q4_K_XL` is not a stock setup choice).
- **Screens, 22-task trial 1 and long-session checks**
  ([measurements](MEASUREMENTS.md#quality-first-comparison-on-the-pro-2026-11-06-stock-strata-v0211-stock-omp-18160)):
  - **Screens (`rtxpro6000-win-a`, 3/3 typed-tool tracers on each draft, single-sample `perf` per depth):** against the
    incumbent's `v0.2.11` DFlash2 single-request reference (`379.7 tok/s` decode and `9,165 tok/s` prefill at 32K, TTFT
    `3.62 s` / `11.04 s` at 32K / 100K), one-slot `IQ3_S` started in `71 s` and decoded at `404.4 tok/s` at 32K
    (`8,610 tok/s` prefill, TTFT `3.86 s` / `11.56 s`, `58,278 MiB` GPU, `129.3 GiB` min available RAM, `99.42 GiB`
    commit headroom, `8,192 MiB` cache); one-slot `UD-Q5_K_XL` started in `85.7 s`, passed unrecorded `g14`/`g14q`
    screen checks (ledger stays `not_run`), and decoded at `296.7 tok/s` at 32K (`7,712 tok/s` prefill, TTFT `4.29 s` /
    `12.83 s`, `22,209` of `24,576` experts in `82.80 GiB` VRAM at `98.4–99.9%` decode hit rate, `95,794 MiB` GPU,
    `83.6 GiB` min available RAM, `17.12 GiB` commit headroom, `5,888 MiB` cache, K-quant prompt kernels active); and
    six-expert `DeepSeek IQ2_XS` started in `54.8 s`, passed unrecorded `g14`/`g14q` screen checks (ledger stays
    `not_run`), and decoded at `45.7 tok/s` at 32K (`2,655 tok/s` prefill, TTFT `12.4 s` / `32.4 s`, DSpark declined
    under `auto`, `9,344` of `15,360` experts in `91.05 GB` VRAM, `6,016` CPU-lane experts copied into `58.4 GB` RAM, no
    disk slots, `95,692 MiB` GPU, `114.0 GiB` min available RAM, `52.70 GiB` commit headroom, server-logged thinking cap
    `24,576` of `32,768` tokens under stock OMP `18.16.0` `reasoning_effort: "high"` = template value `75`).
  - **Trial 1 (`scripts/eval_taskset.py`, 22 tasks = 16 hard + 6 base):** the four-slot `IQ3_S` DFlash2 incumbent passed
    **21/22** (`215.4 s` median agent time, `5,498.6 s` total, `1` critical mid-run empty reply on a task that passed,
    `0` aborts, `0` protocol errors); one-slot `UD-Q5_K_XL` passed **20/22** (`278.9 s` median, `6,437.9 s` total, `0`
    critical, `0` aborts, `0` protocol errors; paired with the incumbent: both `19`, incumbent-only `2`, candidate-only
    `1`, neither `0`, net **`-1`**, exact sign test `p = 1.0`, median wall ratio `1.26`, both misses hidden-verifier
    failures); and six-expert `DeepSeek IQ2_XS` passed **`5/7`** before the owner stopped its trial after `7` of `22`
    tasks (`1,259.0 s` median, `11,174.5 s` total over the `7`, `1` critical: a passing attempt reached its task time
    budget, so OMP's deadline abort ended its last turn with exit `1` and one `stop_reason_aborted` protocol counter;
    `0` runner aborts; paired with the incumbent over those `7`: both `5`, incumbent-only `2`, candidate-only `0`, net
    **`-2`**, exact sign test `p = 0.5`, median wall ratio `3.9`, both misses hidden-verifier failures on tasks the
    incumbent passed, so its best reachable net over `22` tasks was `-1`; the interrupted eighth attempt is unscored).
  - **Long sessions on the incumbent (client reconnect on every turn):** `L64` (`9` docs, `64,341` peak prompt, `2/2`
    recall, `21.7 s`), `L128` (`18` docs, `125,557` peak prompt, `3/3` recall, `43.8 s`), `L200` (`29` docs, `199,621`
    peak prompt, `4/4` recall, `72.2 s`) and `LC` (`33` docs, `219,899` peak prompt, compaction `222,486 -> 25,396`,
    `4/4` recall, `122.6 s`) all passed their final edit (including code from turn 1 after compaction).
- **Final client checks and restoration (2026-11-07).** Across the exclusive owner-granted window series on
  `rtxpro6000-win-a`, the host's optical character recognition (OCR) tenant containers were left exited as found. In the
  last window, run from the Mac Studio with no serving engine and the GPU idle, the launcher on the qualified route failed
  explicitly (`tunnel endpoint health check failed; server stopped or unavailable`, exit `4`). The qualified four-slot
  `IQ3_S` DFlash2 server was then started through its supported controller. A typed tool turn and a forced-compaction
  turn through the route (exits `0`/`0`, `2` compactions, only the route's provider and model) showed only loopback
  flows from OMP, and the only non-loopback flow was the SSH forward's own connection to the host (`nettop` 1 s samples,
  process attribution by `ps` ancestry). A launcher smoke answered `ROUTE OK`, and the server was left serving
  (`healthy`) as the current selection. The comparison roots were deleted afterwards at the owner's request.

## Update, 2026-11-06: Strata v0.2.11 with OMP 18.16.0 qualifies on the PRO, RTX 5090 262K, pair and Studio route; 131K stays on v0.2.10

- **Owner decisions (verbatim answers and approvals, 2026-11-06).**
  - Scope, arms, acceptance rule and root pruning: qualify every lane (`rtxpro6000-win-a`, `rtx5090-win-a` 262K default
    and 131K alternative, `rtx3090-win-a` pair) and the Mac Studio route on stock Strata `v0.2.11` (engine `0.1.57`) +
    stock OMP `18.16.0`; add two PRO arms — a four-slot DFlash2 profile
    (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`, pinning
    `strata.drafting: "dflash2"` with `--parallel 4` and dropping `--batch-mtp`, with a pre-registered **+3% decode**
    bar against `v0.2.11` batch-MTP) and a comparison-only `UD-Q4_K_XL` prompt-kernel screen
    (`win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0`; not chosen: a 5090
    `STRATA_NV_CHUNK=0` contingency and a PRO `UD-IQ4_XS` requalification); make a lane current when every gate passes
    and no paired cold-start A/B metric regresses more than **5%** (`throughput/decode >= 0.95`, `latency <= 1.05`),
    with first-SSE-frame timings and latencies under 1 ms reported below the resolution floor rather than gated; and
    prune seven superseded `v0.2.3–v0.2.9` IQ3_S roots on `rtxpro6000-win-a` (`E:` `115.5 → 202.5 GiB` free) and three
    superseded `v0.2.8`/`v0.2.9` roots on `rtx3090-win-a` (`C:` `94.8 → 128.7 GiB` free).
  - Version A/B overrides (~03:45Z):
    - PRO `v0.2.11` vs `v0.2.10` (`batch-MTP` `kvvram-envpg`, `"Override: chain + route, then arms"`): 3 of 100 gated
      checks missed (`17` below resolution), all at two concurrent short requests (`w2` `c=2`: per-request throughput
      p50 `0.923 [0.987, 0.979, 0.813]`, TPOT p50 `1.070 [1.013, 1.022, 1.182]`, longest gap p50 `1.232 [1.020, 1.055,
      1.736]`), driven by the third baseline block `A3` (`TPOT` p50 `8.86 ms` and longest gap `0.253 s`, against
      `10.4–10.6 ms` and `0.43–0.49 s` in every other `A` and `B` block, while `B` blocks matched `A1/A2` within ~1–2%
      and aggregate throughput `0.983–1.011`, decode `0.975–1.011`, TTFT ~`1.00` and prefill `0.997–1.029` passed).
    - RTX 5090 262K `v0.2.11` vs `v0.2.10` (`kvvram-kvgrow-envg`, `"Override: accept it, run the chains"`): 11 of 88
      gated checks missed (`13` below resolution), all on the 32K-prompt single-request `w3` workload (`agg_tps` `0.917
      [0.915, 0.924, 0.911]`, `window_s` `1.091`, `ttft_p50` `1.097 [1.099, 1.092, 1.100]`, `ttft_p95/max` `1.097`,
      `tpot_p50` `1.051`, `tpot_p95/max` `1.052`, `latency_p50/p95/max` `1.091`) because engine `0.1.57`'s bare
      `--prefill auto` chunks prompts at up to 32,768 tokens on this card where `v0.2.10` printed `prompt chunk auto:
      8192` (`A` blocks TTFT `4.36–4.39 s` and `25.2–25.6 tok/s`, `B` blocks `4.77–4.83 s` and `23.0–23.4 tok/s`), while
      `w1` throughput `1.011`, TTFT `0.970`, decode `0.965–1.008`, prefill `0.988–1.138` and 100K TTFT `0.969` passed.
    - Pair DFlash2 `v0.2.11` vs `v0.2.10` (`df2`, `"Override: run the main chain"`): 4 of 88 gated checks missed (`13`
      below resolution), burstiness only (`w1/c1/max_gap_p50/p95/max` `1.125 / 1.126 / 1.126`, `A` `33–43 ms` vs `B`
      `41 ms`, and `perf/unique_prefix/0/inter_output_event_latency_p95_ms` `1.096`), while `w1` throughput `1.008`,
      `w3` `0.999`, TTFT `0.939–1.016` (`0.985–1.016` on cold unique prefixes, `0.939` on warm 32K), TPOT `0.981–0.987`, decode `0.966–1.022` and prefill `0.988–1.062` passed.
  - PRO four-slot DFlash2 override and RTX 5090 131K G15 rerun (~05:10Z):
    - PRO four-slot DFlash2 (`df2` vs `v0.2.11` `batchmtp`, `"Override: qualify DFlash2 as PRO current"`): after the
      four-slot DFlash2 arm met the owner's +3% decode bar on single requests (**+20.1%** at depth 0, `1.201`;
      **+25.8%** at 8K, `1.258`; **+20.3%** at 32K, `1.203`; **+14.2%** at 100K, `1.142`; **+21.6%** on warm 32K,
      `1.216`; TTFT `0.942–1.029`) while missing 35 of 100 checks on concurrent short-request throughput/latency
      (`w2/c2` total throughput `0.885` and per-request `0.794`, TPOT `1.242`; `w2/c4` total `0.937` and per-request
      `0.919`, TPOT `1.089`; latency +7–20%; `4 × 32K` `0.995`) and output-burst spacing (one-request longest gap
      `1.124–1.129`, p95 inter-event gap `1.072–1.122`), the owner approved qualifying DFlash2 as PRO current (and
      drafting and qualifying its Studio route), with `v0.2.11` batch-MTP (and its Studio route) as the qualified
      rollback.
    - RTX 5090 131K G15 rerun (~05:10Z, `"Rerun G15 in a short WSL-down window"`) and PRO DFlash2 G15 rerun (~06:40Z,
      `"Rerun G15 once on the PRO"`): after the 131K main chain failed G15 (first recall after mid-generation engine
      kill rewrote the interrupted 8,028-token essay despite `"Do not write the essay"`, while the diagnostic second
      recall returned the nonce), the owner approved one complete G15 rerun (`start, g15, stop`) in a short WSL-down
      window; that rerun also failed (both recalls after the mid-generation kill ended in OMP's thinking-loop guard
      without the nonce), so the `v0.2.11` 131K profile is not qualified and the 131K lane keeps its `v0.2.10` profile.
      On the PRO DFlash2 chain (`06:05–06:34Z`), every gate passed except G15 (where the first recall after the
      mid-generation engine kill wrote the interrupted 11,178-token essay without the nonce, while the diagnostic second
      recall returned the nonce at 126 tokens); the owner approved one complete G15 rerun (`06:41–06:44Z`, `start, g15,
      stop`), which passed with both post-kill recalls returning the nonce (58 and 28 tokens).
    - Qualification and CI matrix (`01b4d9b`, `69de6d2`): commit `01b4d9b` qualifies the four `v0.2.11` server profiles
      and both `v0.2.11` Studio routes (keeping the campaign PRO and Studio route rows on the batch-MTP profile/route
      with notes naming DFlash2 as current, ranking the PRO `slots4-df2` and Studio `df2` route families last in
      `campaign.py` `LANES`, and leaving [`releases/campaigns/v0.2.11.json`](../releases/campaigns/v0.2.11.json) status `running` because the 131K row is `failed`), and
      `69de6d2` updates `.github/workflows/ci.yml` to these current and rollback server profiles.
- **Qualified selections and rollbacks (`cf0100b`–`69de6d2`).** Stock Strata `v0.2.11` (annotated tag
  `4a4160162e4a402e082f41aa0a88e6eed629d913` → commit `c3b3f5035506f3e966f1b4b7b188aeaabae92f1d`, published
  `2026-11-05T12:49:59Z`, release `435171031`), Windows CUDA 13 engine component `0.1.57` (`0bdcef4682c5+cuda13.0`,
  `strata-engine-0.1.57-windows-x86_64-cuda-cuda13.tar.gz`, `627,812,560` bytes, SHA-256
  `0cdf191f0fb39b90edbb902f4d096b90f2ee90a4542deb8aef24985b22407c0f`, engine source identical to the tag), Python
  wheel lock `locks/strata-python-cp313-win_amd64-strata0.2.11.txt` (Pillow `13.0.0`), and stock OMP `18.16.0`
  (`650f3a108229ee11bf68ba3377f4e8c3391cd424`;
  [UPSTREAM.md](UPSTREAM.md#strata-v0211-setup-and-start-path-review-engine-0157)):
  - PRO (`rtxpro6000-win-a`) **current** (four-slot stock DFlash2 drafters):
    `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` (fingerprint
    `bc2c503183b7800efa12ecd1103072bcc963d5baef1be5bd9e183c7415468e24`;
    [manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json)),
    `tests/candidate.py` `CURRENT`, rolling back to its qualified `v0.2.11` batch-MTP sibling
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` (fingerprint
    `c24c86c739b0a57cbbfe8c5418ca711200399b389e8ee133487afdc979d68238`;
    [manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json);
    the `v0.2.10` `kvvram-envpg` profile moves to earlier qualified history).
  - RTX 5090 (`rtx5090-win-a`) 262K **default**:
    `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0` (fingerprint
    `fcd6086ac97e88a510292d93e69490b277db87bffbcdf4172c8c3449a1d8e427`;
    [manifest](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/qualification.json)),
    rolling back to `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` (the `v0.2.9`
    `kvvram-kvgrow-envg` profile moves to earlier qualified history).
  - RTX 5090 (`rtx5090-win-a`) 131K **qualified alternative** (stays on `v0.2.10`):
    `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` (fingerprint
    `4e1877a9e638609235bc592984a49ce2e9d1b8d31f7a5f4adef581177414160c`;
    [manifest](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/qualification.json)), rolling back to
    `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0` (the `v0.2.11` 131K draft
    `win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`, fingerprint
    `39fadbbebd8e4b90a1106dc97500c41249d1db374e43fda964c73a95246078b9`,
    [ledger](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/qualification.json), failed G15 twice and
    remains `draft`).
  - RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) **current** (stock DFlash2 drafter):
    `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`
    (fingerprint `576dd271abfcbc881ba245580e3cd373db0d0d2649129d5f7a3d2ad3262a2020`;
    [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/qualification.json)),
    rolling back to its qualified `v0.2.10` `df2` DFlash2 predecessor
    `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
    (while `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
    remains qualified as an older MTP alternative).
  - Mac Studio → PRO route **current**:
    [`routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json`](../routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json)
    (route fingerprint `3709b6a90c57b73aa03c7f3da14a1edefe1fc577b7b77cec1cd5780f34d6848e`;
    [manifest](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/manifest.json),
    [ledger](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json)),
    whose member `rtxpro6000-win-a` pins the PRO `v0.2.11` `df2` profile and `members[0].server_fingerprint`
    `bc2c503183b7800efa12ecd1103072bcc963d5baef1be5bd9e183c7415468e24` on local port `18191`, rolling back to
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json)
    (route fingerprint `0d5b7688efbdafb048462334253470b48d7651eb2a55b1d633708caf519b152c`, pinning the PRO `v0.2.11`
    batch-MTP rollback `c24c86c739b0a57cbbfe8c5418ca711200399b389e8ee133487afdc979d68238`;
    [manifest](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/manifest.json),
    [ledger](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json);
    the `0.2.10` `kvvram-envpg` route moves to earlier qualified history).
- **Paired cold-start A/Bs, gates, kept failures, and G24 coding evaluation**
  ([measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160)):
  - **PRO four-slot DFlash2 current (`b812df9`, published in `f3a8a77` and `637b616`) and batch-MTP rollback (`9c6318b`, published in `8b97dc4`):**
    on the PRO four-slot DFlash2 chain (`06:05–06:34Z`, `b812df9`, start logging `drafting: DFlash2 alone`,
    `STRATA_BATCH_DF2: 4 slot drafters on CUDA0 (85 MiB ...)`, `70.22 GiB` free VRAM, and `4 slot drafters ready`), G10–G14,
    G16–G21, G24 and G26 passed on the first run (G10 `127.14 GiB` available RAM and `83.55 GiB` commit headroom of
    `219.70 GiB`, `73,496 MiB` GPU memory; G13 `0` non-loopback / `4,916` ETW events, `2` compactions; G16 / G20 / G21
    `31.0 / 31.0 / 35.7 s`, lowest available RAM `118.67 GiB` in G18L; G17 100K cold prefill `10,847 ms` and near-limit
    task `26.1 s`; G19 `8,192 MiB` cache, 32 parks; G24 **15/18**, `tool-loop` `0/3`, others `3/3`, pilot **5/6**, batch
    wall `627.259 s`; G26 `install` `25.801 s`, `start` `56.277 s`). In G15, the initial attempt
    ([`g15-20261106T061220Z-57a97f.json`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g15-20261106T061220Z-57a97f.json))
    failed because after the mid-generation engine kill the first recall wrote the interrupted essay (`11,178` output
    tokens, no nonce), while the diagnostic second recall returned the nonce (`126` tokens) and the idle-kill recall and
    client-abort control both passed; the owner-approved complete G15 rerun (`06:41–06:44Z`, `start, g15, stop` at
    `b812df9`,
    [`g15-20261106T064239Z-02cfa4.json`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g15-20261106T064239Z-02cfa4.json))
    passed with the cut turn ending as an error and both post-kill recalls returning the nonce (`58` and `28` output
    tokens, `29.3 s` and `29.2 s` recall walls). Across `v0.2.11`, this first recall after the mid-generation kill
    failed in 3 of 6 G15 runs (RTX 5090 131K twice and PRO DFlash2 once) and passed in the other three (PRO batch-MTP,
    RTX 5090 262K, pair DFlash2), with identical cut-turn stop text across versions. On the `v0.2.11` batch-MTP
    rollback chain (`9c6318b`), all 14 measured gates passed on the first run (G10 `127.23 GiB` available RAM and
    `81.73 GiB` commit headroom of `219.70 GiB`, `74,918 MiB` GPU memory; G13 `0` non-loopback / `9,365` ETW events; G15
    kill recall `45.4` and `44.5 s`; G16 / G20 / G21 `31.1 / 30.9 / 31.4 s`, lowest available RAM `118.42 GiB` in G18L;
    G17 near-limit task `25.8 s`; G19 `8,192 MiB` cache, 35 parks; G24 **16/18**, `tool-loop` `1/3`, others `3/3`, pilot
    **5/6**, batch wall `549.360 s`; G26 `install` `21.603 s`, `start` `52.855 s`). On the comparison-only PRO
    `UD-Q4_K_XL` screen (`win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0`,
    four shards, `111,334,654,784` bytes fetched and verified on `E:` with `86.6 GiB` free after the screen; engine
    `0.1.57` printed `a model with K-quant experts (Unsloth UD-Q4/Q5/Q6_K_XL) reads its prompt on llama.cpp's MMQ
    kernels` and loaded `strata_kq.dll (STRATA_MMQ_KQ=1)`, so the K-quant prompt kernels were active on Windows), the
    report-only three-pair cold-start screen (`06:45–07:24Z`, `tuple-0211-pro-udq4-20261106T064547Z-20261106T0724Z`)
    against the `v0.2.11` IQ3_S batch-MTP profile was slower in every measured workload: `B/A` by depth (`0 / 8K / 32K /
    100K`) was cold single-request TTFT `1.243 / 1.267 / 1.195 / 1.168`, prefill `0.799 / 0.789 / 0.835 / 0.855` and
    decode `0.899 / 0.915 / 0.883 / 0.848` (Rule-4 decode at 32K `0.883`; warm 32K repeat TTFT `1.003`, prefill `0.961`,
    decode `0.894`), total output throughput `w2` `c1 0.844`, `c2 0.766`, `c4 0.731` and `w3` `c4 0.815`, TTFT p50 `w2`
    `c1 1.211`, `c2 1.235`, `c4 2.490` and `w3` `c4 1.188`, and TPOT p50 `w2` `c1 1.159`, `c2 1.308`, `c4 1.324` and `w3`
    `c4 1.216`; it stays comparison-only (never a main chain or current profile, with no CI or campaign row, and any
    switch would still need Terminal-Bench).
  - **RTX 5090 262K default and 131K kept G15 failures (`9c6318b`, published in `8b4d24a` and `8f94b85`):** on the 262K
    default chain, all 14 measured gates passed (G10 `13.47 GiB` available RAM and `20.30 GiB` commit headroom of
    `85.15 GiB`, `30,776 MiB` GPU memory; G13 `0` non-loopback / `6,493` ETW events; G15 kill recall `18.3` and `17.9 s`;
    G16 / G20 / G21 `18.5 / 19.0 / 19.3 s`, lowest available RAM `8.57 GiB` in G18L; G17 100K cold prefill `11,769 ms`
    and near-limit task `29.3 s`; G19 `4,352 MiB` cache, 17 parks; G24 **17/18**, `tool-loop` `2/3`, others `3/3`, pilot
    **6/6**, batch wall `843.136 s`; G26 `install` `11.880 s`, `start` `22.331 s`). On the `v0.2.11` 131K draft, G10–G14,
    G16–G21, G24 (**15/18**, `tool-loop` `0/3`, pilot **6/6**, batch wall `758.318 s`) and G26 (`install` `12.356 s`,
    `start` `35.926 s`) passed, while G15 failed in the main chain
    ([receipt](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/receipts/g15-20261106T042306Z-1bd536.json))
    and again in the owner-approved complete rerun
    ([receipt](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/receipts/g15-20261106T051727Z-74b8db.json));
    both failures are retained and 131K stays on `v0.2.10`.
  - **Pair DFlash2 (`772a418`, published in `ba574d5`) and G13 rerun (`611c342`, published in `3144675`):** after the
    pair `df2` measurement start confirmed engine `0.1.57` stage order `[1, 0]` (`19.41 / 17.90 GiB` expert caches on the
    RTX 3090 / RTX 4090 at pinned split 24; admitted to `STAGE_ORDER_REVIEWED_ENGINES` in `772a418`), the requalification
    chain passed G10–G12 and G14–G26 (G10 `66.35 GiB` available RAM and `28.70 GiB` commit headroom of `135.69 GiB`,
    `[22,892, 23,000] MiB` GPU memory on cards `1, 0`; G15 kill recall `46.9` and `44.3 s`; G16 / G20 / G21 `40.5 / 40.5 / 40.8 s`,
    lowest available RAM `57.63 GiB` in G18L; G17 100K cold prefill `25,946 ms` and near-limit task `61.1 s`; G19
    `8,192 MiB` cache, 12 parks; G24 **15/18**, `tool-loop` `0/3`, others `3/3`, pilot **5/6**, batch wall `896.425 s`;
    G26 `install` `37.002 s`, `start` `52.578 s`). In G13, the initial attempt
    ([receipt](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/receipts/g13-20261106T035408Z-94c443.json))
    failed only because OMP declined the forced compaction six times (`"would not reduce context"`) after the gate's
    one-line tool note left ~200 tokens of history; commit `611c342` grew the note to 160 lines (~3K tokens, above OMP's
    1,000-token `keepRecentTokens`), and the complete rerun (`start, g13, stop`,
    [receipt](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/receipts/g13-20261106T043454Z-8c6c25.json))
    passed with two compactions and `0` non-loopback events among `3,436` attributed ETW events.
  - **Host-free receipts (`G00–G06`, `fba7d65`) and Studio → PRO routes G23:** `G00` and `G06` bind to `d2877e3` and
    hosted CI run `42168098090` on pull request #77, and `G01–G05` bind to the 1,015-test host-free suite at `d2877e3`.
    On the Studio `v0.2.11` DFlash2 current route (`06:34–06:37Z`), G23 passed at `b812df9`
    ([receipt](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/receipts/89cd7d3991b843d195f2d1b4624e00ac.json),
    published in `f3a8a77`): missing key refused before launch, wrong key 401, health RTT `6.0–10.1 ms`, stream TTFT
    **0.270 s**, tunnel drop failing the in-flight turn with prior transcript preserved, nonce recall from transcript
    replay after tunnel reopen (`1.83 s`), client restart (`1.11 s`) and verified server restart (`2.34 s`, changed
    server instance) all true, plus a one-turn `launch-omp` smoke answering `ROUTE OK` with owned stop; on the Studio
    `v0.2.11` batch-MTP rollback route, G23 passed at `9c6318b`
    ([receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/receipts/4fc016a3ebff4f41b89bd69189b938e0.json),
    published in `8b97dc4`): RTT `5.3–6.5 ms`, stream TTFT **0.174 s**, recalls `2.24 / 1.10 / 2.30 s`, and `ROUTE OK`
    smoke.
- **Restorations.**
  - RTX 5090 ([262K restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/restored-state.json),
    [131K restored-state](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/restored-state.json)):
    three WSL-down fleet windows (production NInfer down about `02:49–03:30Z` for install + A/B, where `fleet return`
    failed closed with `docker.exe exited 128`, the owner's pinned relaunch recreated the container, retired controller
    state was kept, and the host commissioned at generation `1` with health `200`; about `03:47–04:56Z` for both chains,
    returning via `fleet return` at generation `3`; and about `05:14–05:25Z` for the 131K G15 rerun, returning via
    `fleet return` at generation `5` with health `200`, tasks `Ready` and pause markers removed after the host supervisor
    reprovisioned the lane distro's WSL integration before each return).
  - PRO ([DFlash2 server](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/restored-state.json),
    [DFlash2 route](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/restored-state.json),
    [batch-MTP server](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/restored-state.json),
    [batch-MTP route](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/restored-state.json)):
    across the five qualification host-lock windows (`02:49–03:26Z` version A/B, `03:47–04:17Z` batch-MTP chain + route
    G23, `04:17–04:53Z` DFlash2 install + A/B, `06:05–06:37Z` DFlash2 chain + route G23, `06:40–06:44Z` DFlash2 G15
    rerun; `96af37e`), the pruning host-lock window (`05:01–05:02Z`, pruning seven old IQ3_S roots with the owner's
    approval, `E:` `115.5 → 202.5 GiB` free), and the two `UD-Q4_K_XL` host-lock windows (`05:02–06:05Z` download stopped
    before install when the download fell from ~35 MB/s to 2.8 MB/s, with the remaining shards fetched by a separate
    fetch-only process `06:08–06:35Z` beside the DFlash2 chain window, and `06:45–07:24Z` install + comparison screen,
    leaving the `UD-Q4_K_XL` root installed on `E:` with `86.6 GiB` free), every window began and ended idle with both
    optical character recognition (OCR) tenant containers exited as found, no user signed in, and all `omp-strata` roots
    stopped with GPU at `433 MiB` idle
    (`178.4–179.1 GiB` available RAM).
  - Pair ([DFlash2 restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/restored-state.json)):
    four exclusive host-lock windows (stage-order measurement `02:45–03:07Z`, version A/B `03:17–03:37Z`, DFlash2 chain
    `03:47–04:30Z`, complete G13 rerun `04:32–04:37Z`), after pruning three `v0.2.8`/`v0.2.9` roots with the owner's
    approval (`C:` `94.8 → 128.7 GiB` free); each start and end census found no user session, no engine process and idle
    GPUs (`186 MiB` on the display-attached RTX 4090 and `0 MiB` on the RTX 3090, `120.7–120.9 GiB` available RAM).

## Update, 2026-11-03: Strata v0.2.10 with OMP 18.16.0 qualifies on every host and the Studio route

- **Owner decisions (verbatim answers and approvals, 2026-11-03).**
  - Scope, DFlash2 arm and acceptance rule: qualify every lane (`rtxpro6000-win-a`, `rtx5090-win-a` 262K default and
    131K alternative, `rtx3090-win-a` pair) and the Mac Studio route on stock Strata `v0.2.10` (engine `0.1.56`) + stock
    OMP `18.16.0`, including one WSL-down fleet window on `rtx5090-win-a`; add a pair DFlash2 arm
    (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`,
    pinning `strata.drafting: "dflash2"` and dropping `--pipeline-windows 2`) with a pre-registered **+3% decode** bar
    against `env86g` `v0.2.10`; make a lane current when every gate passes and no paired cold-start A/B metric regresses
    more than **5%** (`throughput/decode >= 0.95`, `latency <= 1.05`); and file no upstream issue now.
  - Measurement resolution floor (2026-11-03): first-SSE-frame timings and latencies under 1 ms are reported, not gated
    (sub-millisecond resolution floor); each lane's strict first verdict is retained beside its final verdict (`strict
    first verdict pass=False` on the PRO, RTX 5090 262K and pair `env86g` version A/Bs; after applying the resolution
    floor, `final verdict pass=True` on RTX 5090 262K and pair `env86g`, `pass=False` on the PRO and on the pair DFlash2
    vs `env86g` A/B).
  - PRO concurrent-TTFT override (~19:50Z: `"Override: chain + G23"`): after the PRO `v0.2.10` vs `v0.2.9` `kvvram-envpg`
    paired cold-start A/B raised decode +3.9% to +6.2% with aggregate throughput parity (`w2` `0.969–1.008`, `w3` `1.032`)
    and identical startup lines (`24,576` expert-cache slots, prompt path borrows `5,542`), but missed the 5% rule on
    concurrent short-prompt (`w2` 1,000-token) TTFT (`w2/c2` TTFT p50 `1.052` and p95 `1.136`, per-pair p95
    `1.127 / 1.137 / 1.144`; `w2/c4` TTFT p50 `1.326`, per-pair `1.559 / 1.524 / 0.981`, while `w2/c4` TTFT p95 was
    `0.988` and `w3/c4` 32K TTFT p50/p95 was `0.976 / 0.968`), the owner overrode that regression so the PRO chain and
    Studio route G23 proceed; the regression is accepted and recorded, not hidden.
  - Pair DFlash2 burstiness override (~21:28Z: `"Run chain, make DFlash2 current"`): after the pair DFlash2 (`df2`) vs
    `env86g` (`pw2`) `v0.2.10` paired cold-start A/B met the owner's +3% decode bar at every depth (**+8.2%** at 8K,
    `1.082`; **+9.3%** at 100K, `1.093`; **+10.1% / +13.6% / +7.7%** at `0 / 32K / warm-32K`; `1.104 / 1.164` on queue
    requests 0 / 1; TTFT at 8K–100K `0.955–0.980`; `w1` throughput `1.001`, `w3` `1.033`) while missing the 5% rule on
    output-burst metrics (`w3` longest stall between tokens `max_gap` p50/p95/max `1.112 / 1.078 / 1.075`, p95 gap between
    output events `1.122–1.170` at every depth, a queued request's prefill `0.802` / prompt time `1.227`, and empty-prompt
    TTFT `1.052`, caused by DFlash2 emitting verified windows of up to 6 tokens so output arrives in larger bursts), the
    owner approved running the DFlash2 requalification chain and making DFlash2 current on the pair, with `env86g` `v0.2.10`
    (`pw2`) as its qualified rollback.
- **Qualified selections and rollbacks (`e8dffe9`–`f115173`).** Stock Strata `v0.2.10` (annotated tag
  `db0500a53119a349fa44497099d6e28a83ded34a` → commit `ffa80d73133ea5c548aefe57889a16e8085a938f`, published
  `2026-11-02T23:52:47Z`, release `432079269`), Windows CUDA 13 engine component `0.1.56` (`06698c674673+cuda13.0`,
  `strata-engine-0.1.56-windows-x86_64-cuda-cuda13.tar.gz`, `627,806,827` bytes, SHA-256
  `5336671c55bc1b819d076104608522147227001d1711378f35ea5d524bc866ec`), and stock OMP `18.16.0`
  (`650f3a108229ee11bf68ba3377f4e8c3391cd424`, request path byte-identical to `18.15.0`;
  [UPSTREAM.md](UPSTREAM.md#strata-v0210-setup-review-component-engine)):
  - PRO (`rtxpro6000-win-a`) **current**:
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0` (fingerprint
    `29464f66c3d4e692d7fe779507f492d48044b7d27f610abaa0ec387da5e6535a`;
    [manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/qualification.json)),
    `tests/candidate.py` `CURRENT`, rolling back to
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0` (the `v0.2.9`
    `slots4-batchmtp-pledirect-parking` base profile moves to earlier qualified history).
  - RTX 5090 (`rtx5090-win-a`) 262K **default**:
    `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` (fingerprint
    `9e7738f3a3e20a2eddd34e4da95c38cca6df50025e6fdbee8f82685847359563`;
    [manifest](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/qualification.json)),
    rolling back to `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0` (the `v0.2.9`
    `coder-iq1m-262k` base profile moves to earlier qualified history).
  - RTX 5090 (`rtx5090-win-a`) 131K **qualified alternative**:
    `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` (fingerprint
    `4e1877a9e638609235bc592984a49ce2e9d1b8d31f7a5f4adef581177414160c`;
    [manifest](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/qualification.json)), rolling back to
    `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0` (`v0.2.8` 131K moves to earlier qualified history).
  - RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) **current** (stock DFlash2 drafter):
    `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
    (fingerprint `555d7d258e11af0b9818d51c79fd461a90a2643c3d73ff222a7e60f267535082`;
    [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/qualification.json)),
    rolling back to its qualified `v0.2.10` `pw2` `env86g` MTP sibling
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
    (fingerprint `546036d88eb5d9439c8c107dfcfb6c17f04bfe69fdba9757b41e21a880c1ac61`;
    [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/manifest.json),
    [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/qualification.json);
    the `v0.2.9` `env86g` and `v0.2.9` split-24 trim + PLE-direct base profiles move to earlier qualified history).
  - Mac Studio → PRO route **current**:
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0.json)
    (route fingerprint `976f9208ad60adcb3f2b0db71146d9e26ae585af786b437066d788f0bcfd93f9`;
    [manifest](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/manifest.json),
    [ledger](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/qualification.json)),
    whose member `rtxpro6000-win-a` pins the PRO `v0.2.10` `kvvram-envpg` profile and `members[0].server_fingerprint`
    `29464f66c3d4e692d7fe779507f492d48044b7d27f610abaa0ec387da5e6535a` on local port `18191`, rolling back to
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0.json)
    (the `0.2.9` batch-MTP + PLE-direct base route moves to earlier qualified history).
- **Paired cold-start A/Bs, gates, kept failures with complete-gate reruns, and G24 coding evaluation**
  ([measurements](MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160)):
  - **RTX 5090 262K (`v0.2.10` vs `v0.2.9` `kvvram-kvgrow-envg`):** passed (`final verdict pass=True`, `strict first
    verdict pass=False` on 13 sub-resolution metrics; `w1` 512/512 throughput `1.033 [1.051, 1.025, 1.022]`, `w3` 32K
    `1.013`, decode `+1.2%` to `+3.6%`, TTFT `0.936–1.020`, cold-start ready `31.2–35.2 s` vs `20.1–25.2 s`). In the
    requalification chain at `9a06ec1` (`08e7032`), G24 scored **18/18** (pilot **5/6**, batch wall `738.713 s`; vs
    `17/18`, pilot `5/6`, `791.111 s` on `v0.2.9`); G16 / G20 / G21 restart readiness was **19.3 / 19.2 / 19.5 s** (lowest
    available RAM `7.82 GiB` in G18L); G10 measured `13.41 GiB` available RAM and `20.31 GiB` commit headroom of
    `85.15 GiB`; G19 sized a `4,352 MiB` automatic conversation cache (22 parks); and G26 passed (`install` `11.686 s`,
    `start` `22.394 s`). On the 131K alternative (`08e7032`), G24 scored **16/18** (`tool-loop` `1/3`, others `3/3`; pilot
    **6/6**, batch wall `741.670 s`; vs `14/18`, pilot `5/6`, `763 s` on `v0.2.9`), with G16 / G20 / G21 readiness
    **18.7 / 18.7 / 18.9 s**, `3,584 MiB` cache (29 parks), G10 `11.52 GiB` available RAM and `18.56 GiB` commit headroom,
    and G26 `install` `10.744 s` / `start` `36.210 s`.
  - **Pair `env86g` (`pw2`, `v0.2.10` vs `v0.2.9`) and stage-order admission (`7b338d9`):** after the pair `env86g`
    measurement start confirmed engine `0.1.56` automatic stage order `[1, 0]` (RTX 3090 first on layers `0–23`, RTX 4090
    last on layers `24–47` at pinned split 24, one engine generation; admitted to `STAGE_ORDER_REVIEWED_ENGINES` in
    `7b338d9`), the paired cold-start A/B passed (`final verdict pass=True`, `strict first verdict pass=False` on 13
    sub-resolution metrics; `w1` throughput `1.020 [1.017, 1.015, 1.028]`, `w3` `1.009 [1.013, 1.010, 1.004]`, TTFT
    `0.979–1.000`, decode `0.996–1.036`, `45.1 s` to ready on all three `v0.2.10` blocks). In the requalification chain at
    `7b338d9` (`9d01e33`), G20 initially failed only on `user_omp_dir_untouched_since_root_created`
    ([receipt](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/receipts/g20-20261103T191639Z-c63bb9.json),
    `55.4 s` restart ready) because another tenant's stock OMP wrote the host user's `~/.omp` between our exclusive holds;
    `837bc89` baselined that check at the requalify run start, and the complete-gate rerun (`start`, `g20`, `stop`,
    [receipt](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/receipts/g20-20261103T204350Z-559436.json),
    published in `e300b27`) passed at **43.2 s** restart ready (G16 `55.3 s`, G21 `55.7 s`; G10 `65.37 GiB` available RAM
    and `27.54 GiB` commit headroom of `135.69 GiB`; G17 near-limit task `59.9 s`; G19 `8,192 MiB` cache, 32 parks; G24
    **16/18**, `tool-loop` `1/3`, others `3/3`, pilot **5/6**, batch wall `1,044.723 s`; G26 `install` `27.021 s`, `start`
    `66.812 s`).
  - **PRO (`v0.2.10` vs `v0.2.9` `kvvram-envpg`) and G14 rerun (`7971a1a`):** under the owner's concurrent-TTFT override,
    the requalification chain at `9a06ec1` (`e300b27`) passed G10–G13 and G15–G26 (G10 `129.12 GiB` available RAM and
    `83.05 GiB` commit headroom of `219.70 GiB`; G16 / G20 / G21 `31.1 / 31.0 / 31.3 s`; G17 near-limit task `25.9 s`;
    G19 `8,192 MiB` cache, 30 parks; G24 **16/18**, `tool-loop` `1/3`, others `3/3`, pilot **5/6**, batch wall `569.579 s`;
    G26 `install` `22.011 s`, `start` `50.268 s`). In G14, the initial attempt
    ([receipt](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/receipts/g14-20261103T201019Z-78990a.json))
    failed because the third slot-filling stream read its trailing `"(3)"` as `"count to 3"` and stopped after 6 tokens,
    so the fifth request was served instead of queued; `7971a1a` led the prompt with its stream label, and the
    complete-gate rerun (`start`, `g14`, `g14q`, `stop`,
    [receipt](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/receipts/g14-20261103T213214Z-9417d2.json),
    published in `8b534b8`) passed (`88 ms` generating cancel to idle, `263 ms` queued-drop-then-active-drop to idle,
    `4/4` `g14q`).
  - **Pair DFlash2 (`df2` vs `pw2` `env86g`, both `v0.2.10`):** in three paired cold starts against `pw2` `env86g`
    (`45.0–45.1 s` to ready, `65.65–65.66 GiB` available RAM at ready, `31.4 GiB` startup commit headroom of `135.7 GiB`),
    beat the owner's +3% decode bar at every depth (**+8.2%** at 8K, `1.082 [1.091, 1.080, 1.075]`; **+9.3%** at 100K,
    `1.093 [1.144, 1.076, 1.062]`; **+10.1% / +13.6% / +7.7%** at `0 / 32K / warm-32K`; `1.104 / 1.164` on queue requests
    0 / 1; TTFT at 8K–100K `0.955–0.980`; `w1` throughput `1.001`, `w3` `1.033`), while missing the 5% rule on
    output-burst metrics (`w3` max inter-token gap p50/p95/max `1.112 / 1.078 / 1.075`, p95 inter-event gap `1.122–1.170`
    at every depth, queued prefill `0.802` / prompt time `1.227`, and empty-prompt TTFT `1.052`) because DFlash2 emits
    verified windows of up to 6 tokens. Under the owner's burstiness override (`"Run chain, make DFlash2 current"`), the
    requalification chain on 2026-11-03 (21:45–22:28Z, tooling `837bc89`, published in `1f2d483`, qualified in `8a2c9ec`)
    passed all 14 measured gates, with every start logging stock's
    `[strata] drafting: DFlash2 alone (--draft dflash2, --draft-conf 0.35)` and `strata serve: DFlash2 drafter on`: G24
    scored **17/18** (pilot **5/6**, batch wall **915.637 s** vs `1,044.723 s` on the `pw2` `env86g` rollback; miss:
    `tool-loop` x1 on attempt 3 at `62.1 s`, every other task `3/3`); restart readiness G16 / G20 / G21 was
    **43.1 / 43.2 / 43.4 s** (vs `55.3 / 43.2 / 55.7 s` on `pw2` and `43.5 / 43.6 / 43.9 s` on `v0.2.9` `env86g`; G15
    kill recall `49.0 / 49.2 s` vs `63.2 / 57.7 s` on `pw2`; G17 100K cold prefill `25,910 ms`, `3,860.7 tok/s`, and
    near-limit task **59.0 s** vs `26,765 ms` and `59.9 s` on `pw2`); G10 measured **65.65 GiB** available RAM (minimum
    sampled `65.61 GiB`) and **27.51 GiB** commit headroom of `135.69 GiB` (`[22,892, 23,418] MiB` GPU memory on cards
    `1, 0` vs `65.37 / 65.35 / 27.54 GiB` and `[22,762, 23,160] MiB` on `pw2`); G13 recorded `0` non-loopback events among
    `2,981` attributed ETW events (`9,344` on `pw2`); G19 kept the **8,192 MiB** automatic conversation cache (`25` parks
    in `kept_conversation`, `15` in `automatic_conversation_cache`; kept-conversation `a2` `456 ms` at `20,680 / 20,700`
    reused tokens vs `7,695 ms` cold `a1`; lowest available RAM `56.87 GiB` in G18L vs `56.62 GiB` on `pw2`); G21 measured
    `60.1 GB` peak working set, `109.8 GB` peak private commit and `97.8 GB` root disk (`95.7 GB` on `pw2`); and G26
    passed (`install` `33.144 s`, `start` `74.292 s` vs `27.021 s` and `66.812 s` on `pw2`).
  - **Host-free receipts (`G00–G06`, `6e795bb` on PRO, RTX 5090 262K/131K and pair `pw2`; `1f2d483` on pair `df2`):**
    `G00` and `G06` bind to `74c0ff1` on the four initial `v0.2.10` profiles and `428e1a7` on the pair `df2` profile, and
    `G01–G05` bind to the 948-test host-free suite at `8b534b8` (`29` skipped on the two pair profiles, `4` skipped on
    each single-GPU lane; qualified in `8a2c9ec`, CI matrix updated in `f115173`).
  - **Studio → PRO route G23:** passed on 2026-11-03 at implementation `9a06ec1`
    ([receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/receipts/2a07609cb1f0410fa8d650ec59ee891f.json),
    published in `e300b27`): missing key refused before launch, wrong key 401, health RTT 21.9–24.4 ms, stream TTFT
    **0.219 s**, tunnel drop and reopen (0.82 s), client restart (0.67 s) and verified server restart (1.41 s, changed
    server instance) recovery all true, plus a one-turn `launch-omp` smoke answering `ROUTE OK` with owned stop.
- **Restorations.**
  - RTX 5090 ([262K restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/restored-state.json),
    [131K restored-state](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/restored-state.json)):
    ran one WSL-down fleet window (production NInfer down about 17:54–19:36Z); when the fleet return script failed closed
    after the host supervisor restarted Docker Desktop and provisioned WSL integration at 19:32Z, the owner's pinned
    relaunch recreated the production container with the same image and configuration, retired controller state was kept,
    and the host recommissioned in `Fleet` at generation 1 with authenticated health 200 and `unless-stopped` restart
    policy.
  - PRO ([server](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/restored-state.json),
    [route](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/restored-state.json)):
    across three exclusive host-lock windows (install + A/B 17:53–18:29Z, requalify chain + Studio G23 20:05–20:48Z, G14
    rerun 21:31–21:33Z), both unrelated optical character recognition (OCR) tenant containers stayed exited as found; no
    console user session before or after; all Strata processes stopped, GPU at 433 MiB idle (179.5 GiB available RAM).
  - Pair ([`env86g`](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/restored-state.json),
    [DFlash2](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/restored-state.json)):
    six exclusive host-lock windows (stage-order measurement 17:55–18:19Z, `env86g` A/B 18:26–18:46Z, `env86g` chain
    18:53–19:41Z, DFlash2 install + A/B 19:47–20:27Z, `env86g` G20 rerun 20:41–20:45Z, DFlash2 chain 21:44–22:29Z),
    serialized with another tenant's exclusive GPU work between them; each start and end census found no user session,
    no engine process and idle GPUs (180 / 0 MiB at the end, 120.2 GiB available RAM), with both `v0.2.10` roots
    stopped.

## Update, 2026-11-02 (evening): the v0.2.9 tuning profiles on the PRO and RTX 5090 and the Studio's tuned route qualify

- **Owner decisions (verbatim answers, 2026-11-02).**
  - Window and preparation approvals: `"All three hosts"` for tuning and `"Prepare both for Terminal-Bench"` for the two
    PRO model candidates (~12:15Z), and `"When the kit is ready today"` for the `rtx5090-win-a` window (~15:20Z).
  - Qualification and default selection (~21:50Z) and pair override (~23:20Z): `"Qualify and make current"` for the PRO
    variant, its Mac Studio route and the RTX 5090 262K variant, with the 2026-11-02 `v0.2.9` base profiles as their
    rollbacks. For the pair variant, the owner initially pre-authorized qualification (~21:50Z: `"Qualify it in the same
    sweep"`) conditional on passing every pre-registered A/B bar; after it missed the single-request `w1` 512/512 bar
    (`1.039` vs `>= 1.05`) while passing every decode and TTFT bar, the owner overrode that one bar (~23:20Z: `"Yes
    approved: Yes, if you approve an override. There's nothing in the pair profile to fix."`) and approved running the
    requalification chain on 2026-11-03 so the real gates decide.
- **Qualified selections, rollbacks and drafts (`7411d03`, `cbe3ada`, `61250a9`, `e347fb6`, `f3fed60`, `e281687`, `acd7549`, `2804c1d`, `d05f660`, `343fab3`, `b802d5f`, `b770db0`; pair override `d0a1254`, `f7f82aa`, `6b972fa`, `1f699b4`, `8bbf9a8`, `98d8c32`).**
  Same component tuple as the morning 2026-11-02 qualification: stock Strata `v0.2.9` (engine `0.1.55`) with stock OMP
  `18.15.0`; every change is a stock engine or setup option pinned in a new profile id:
  - PRO (`rtxpro6000-win-a`) **current**:
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0` (fingerprint
    `c18797cf221bccc0d86dc0af3e3c9c082990b0b3949b39f32b9701b1ddbcaa89`;
    [manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/qualification.json)),
    now `tests/candidate.py` `CURRENT`. Pins the 2026-11-02 PRO 262K `slots4-batchmtp-pledirect-parking` choices plus
    `strata.engine_env` with stock `serve/server.py`'s Linux-only nine-switch parallel-slot stack (`PARALLEL_STACK_ENV`)
    and two-switch GDN tensor-core prompt stack (`GDN_STACK_CUDA`), and `setup_args.kv_streaming: "off"`
    (`--kv-streaming off`, keeping KV in VRAM and dropping `--kv-resident 32768`; 78 GiB available-RAM start floor).
  - PRO **rollback**: `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0` (the morning
    2026-11-02 `v0.2.9` base profile; the `v0.2.8` batch-MTP profile moves to earlier qualified history in its ledger).
  - RTX 5090 (`rtx5090-win-a`) 262K **default**:
    `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0` (fingerprint
    `d28141f5a51d668194ad41b59f3239811a09f923a6914bd4dd73717ae8e44c57`;
    [manifest](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/qualification.json)).
    Pins the 2026-11-02 RTX 5090 262K choices plus `strata.engine_env` `gdn_stack` (`GDN_STACK_CUDA`),
    `setup_args.kv_streaming: "off"` (`--kv-streaming off`, lowering the setup-derived available-RAM start floor from
    36 GiB to 34 GiB) and `strata.kv_grow: true` (`--kv-grow`). Operating condition unchanged: Docker Desktop and WSL
    (which run the production NInfer container) must be stopped, and after WSL restarts that container is recreated by
    the owner's pinned relaunch script and re-registered with the owner's fleet controller (a WSL-up start was refused
    at 7.3 GiB available RAM while another of the owner's agents held host memory; untested on an idle host).
  - RTX 5090 262K **rollback**: `win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0` (the morning 2026-11-02 `v0.2.9`
    base profile; the `v0.2.8` 262K profile moves to earlier qualified history in its ledger). The unpinned-GDN fallback
    draft `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0` (fingerprint
    `884d940cdba61b52e4201a821f87982045891a00620490704e54f9e95c462b4d`) was prepared and never installed. The 131K
    qualified alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`, rolling back to
    `win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`) is unchanged.
  - RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) **current** (qualified 2026-11-03 under the owner's override):
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`
    (fingerprint `45363f01e58127f3065340c861da826e868d7624737c13d1a89370fda5ffab3f`;
    [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/qualification.json)).
    Pins the 2026-11-02 pair `roles-split24-trimweights-pledirect-parking` choices plus `strata.engine_env` with the
    engine's `sm_86` default table (`sm86_table`, skipped by default on the mixed `sm_86` + `sm_89` pair;
    [Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313)) and stock `gdn_stack` (`GDN_STACK_CUDA`).
  - Pair **rollback**:
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`
    (the morning 2026-11-02 `v0.2.9` base profile; the `v0.2.8` split-24 trim profile
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`
    leaves the CI matrix and moves to earlier qualified history in its ledger).
  - Mac Studio → PRO route **current**:
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0.json)
    (route fingerprint `eb9ed6b98add6c219e5c14ca4048fe1ed86443c4931b1618ea88732de18718fc`;
    [manifest](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/qualification.json)),
    whose member `rtxpro6000-win-a` pins the PRO current profile and `members[0].server_fingerprint`
    `c18797cf221bccc0d86dc0af3e3c9c082990b0b3949b39f32b9701b1ddbcaa89` on local port `18191`, rolling back to
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0.json)
    (which pins the PRO `v0.2.9` base rollback; the `0.2.8` batch-MTP route moves to earlier qualified history).
  - PRO model candidates:
    `win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0` and
    `win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0` (with stock PLE in RAM on the hard-disk
    root via `--ple-io stock`) and their Mac Studio routes (`client-rtxpro6000-262k-ud-iq4xs-strata0.2.9-omp18.15.0`
    and `client-rtxpro6000-262k-nvfp4qad-strata0.2.9-omp18.15.0`) stay comparison-only drafts; a 30-task Terminal-Bench
    comparison is prepared and has not run.
  - Campaign [`releases/campaigns/v0.2.9.json`](../releases/campaigns/v0.2.9.json) stays as recorded (`complete`),
    `scripts/campaign.py` `LANES` lists the new current variants last (`f3fed60`), and the CI `suite` matrix (`b770db0`,
    updated in `98d8c32` for the pair `env86g` current and `v0.2.9` base rollback rows) runs the eight current and
    rollback server profiles.
  - Risks: GDN tensor-core prompt numerics are not bit-exact upstream, and `strata.engine_env` pins are reviewed per
    engine release (`ENGINE_ENV_REVIEWED_ENGINES`, engine `0.1.55` only;
    [UPSTREAM.md](UPSTREAM.md#stock-engine-environment-v029--0155)), so the next engine needs a fresh review.
- **Cold-start A/B against the v0.2.9 base, gates and G24 coding evaluation.** Each new server ledger has **21 pass, 3 not applicable**
  (G22, G23, G25), with 0 timeouts and 0 protocol counters
  ([measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150)):
  - **PRO (`slots4-batchmtp-pledirect-kvvram-envpg`):** in three paired cold starts against the `v0.2.9` base, total
    output at 1,000-token prompts (`w2`) rose **+11.3%** at 1 request (`1.113`, 135.82 vs 122.02 tok/s), **+29.3%** at 2
    (`1.293`, 139.32 vs 107.81 tok/s) and **+34.8%** at 4 (`1.348 [1.316, 1.376]`, 156.09 vs 115.81 tok/s), `4 × 32K`
    (`w3`) rose **+13.1%** (`1.131`), single-request TTFT p95 dropped **-19.6%** (`0.804`, 0.439 vs 0.546 s), cold
    decode stayed at `1.000` (depth 0) and **+2.2%** (`1.022`, 326.56 vs 319.56 tok/s at 100K), and stock greedy output
    matched the base byte-for-byte in every block (`ALL IDENTICAL`). In the requalification chain at `acd7549`, G24
    scored **16/18** (pilot **5/6**, batch wall 631.201 s; misses: `tool-loop` x2 on attempts 1 and 3, tying 16/18,
    pilot 5/6, 576.248 s on the `v0.2.9` base rollback); restart readiness G16 / G20 / G21 was **31.0 / 31.0 / 31.3 s**
    (base 35.1 / 35.1 / 39.7 s; G15 kill recall 45.4 / 44.7 s vs 49.4 / 48.7 s); G10 measured **129.57 GiB** available
    RAM and **83.35 GiB** commit headroom of 219.70 GiB (base 112.58 / 81.28 GiB; GPU 74,906 MiB vs 59,712 MiB); G19
    kept the 8,192 MiB automatic conversation cache (34 parks); and G26 passed (`install` 21.3 s, `start` 53.1 s).
  - **RTX 5090 262K (`coder-iq1m-262k-kvvram-kvgrow-envg`):** in three paired cold starts against the `v0.2.9` base with
    Docker Desktop and WSL stopped, cold TTFT dropped **-8.6%** at 32K (`0.914`, 3,924.72 vs 4,291.73 ms) and **-8.9%**
    at 100K (`0.911`, 12,488.78 vs 13,708.09 ms), 100K decode was **-2.7%** (`0.973`, 240.23 vs 246.79 tok/s, above its
    `0.97` bar), 512/512 single-request output (`w1`) rose **+2.5%** (`1.025`), and 32K output (`w3`) rose **+8.4%**
    (`1.084`). After `acd7549` fixed reinstall carry-over of stock config `env` entries, the requalification chain at
    `acd7549` scored G24 **17/18** (pilot **5/6**, batch wall 791.111 s; miss: `tool-loop` x1 on attempt 2, versus
    16/18, pilot 6/6, 840.387 s on the `v0.2.9` base rollback); G16 / G20 / G21 restart readiness was
    **18.7 / 18.6 / 18.9 s** (base 16.6 / 16.7 / 16.8 s; lowest available RAM 8.61 GiB in G17 vs 6.56 GiB on the base);
    G10 measured **13.35 GiB** available RAM and **20.10 GiB** commit headroom of 85.15 GiB (base 10.55 / 17.55 GiB);
    G19 sized a **4,352 MiB** automatic conversation cache (23 parks, vs 3,072 MiB on the base); and G26 passed
    (`install` 12.4 s, `start` 23.9 s).
  - **Pair variant (`roles-split24-trimweights-pledirect-env86g`, qualified 2026-11-03 under the owner's override):**
    in three paired cold starts against the `v0.2.9` base, passed cold decode (**+6.5%** at 8K, `1.065`; **+11.4%** at
    100K, `1.114`) and every TTFT bar (`0.948–0.996`), while missing the pre-registered 512/512 single-request (`w1`)
    bar (`1.039 [1.033, 1.045]` vs `>= 1.05`). After the owner overrode that one bar on 2026-11-02 (~23:20Z), the
    requalification chain on 2026-11-03 (06:45–07:27Z, tooling `d0a1254`, published in `f7f82aa`) passed all 14
    measured gates: G24 scored **15/18** (pilot **5/6**, batch wall **821.8 s** vs 974.9 s on the `v0.2.9` base
    rollback; misses: `tool-loop` x3 on attempts 1, 2 and 3, matching the base's 15/18 with `tool-loop` x3 and pilot
    5/6); restart readiness G16 / G20 / G21 was **43.5 / 43.6 / 43.9 s** (base 55.4 / 55.5 / 55.6 s; G15 kill recall
    50.1 / 47.1 s vs 63.5 / 58.9 s; G17 100K cold prefill 26,582 ms and near-limit task 59.8 s vs 26,865 ms and
    60.4 s); G10 measured **65.68 GiB** available RAM (minimum sampled 65.62 GiB) and **27.77 GiB** commit headroom of
    135.69 GiB (base 65.67 / 65.64 / 27.74 GiB; GPUs 22,762 / 23,166 MiB on both); G19 kept the **8,192 MiB** automatic
    conversation cache (23 parks vs 20; kept-conversation `a2` 499 ms vs 7,899 ms cold `a1`, base 466 ms vs 7,950 ms;
    lowest available RAM 56.47 GiB in G18L vs 56.96 GiB); and G26 passed (`install` 29.7 s, `start` 70.4 s vs 25.9 s and
    54.5 s on the base).
  - **Host-free receipts (`G00–G06`, `343fab3` on PRO and RTX 5090; `1f699b4` on the pair):** `G00` binds to `f3fed60`;
    on the PRO and RTX 5090, `G01–G05` bind to the 903-test host-free suite at `d05f660` (`4` skips on each single-GPU
    lane) and `G06` cites green PR #73
    [CI run 41499865044](https://github.com/alphastorm/omp-strata/actions/runs/41499865044) at `d05f660`; on the pair
    `env86g` profile, `G01–G05` bind to the 903-test host-free suite at `6b972fa` (`29` skipped) and `G06` cites green
    PR #74 [CI run 41597184710](https://github.com/alphastorm/omp-strata/actions/runs/41597184710) at `6b972fa`
    (qualified in `8bbf9a8`).
  - **Studio → PRO route G23:** passed on 2026-11-02 at implementation `acd7549`
    ([receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/receipts/e433de1953c844e1a8fcd7f3fefe48a0.json)):
    missing key refused before launch, wrong key 401, health RTT 5.5–6.3 ms, stream TTFT **0.172 s** (vs 0.206 s on the
    `v0.2.9` base route), tunnel drop and reopen (0.81 s), client restart (0.67 s) and verified server restart (1.40 s,
    new server instance) recovery all true.
- **Restorations.**
  - PRO ([server](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/restored-state.json),
    [route](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/restored-state.json)):
    both OCR containers stayed exited as found; no signed-in user before or after; variant and model-candidate roots
    stopped, port 18090 closed, GPU at 433 MiB idle (180.5 GiB available RAM).
  - RTX 5090 ([restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/restored-state.json)):
    after the 15:53Z reservation joined a reservation another of the owner's agents had taken at 15:51Z (window scripts
    now require an unreserved controller phase before reserving and refuse a joined reservation), the production NInfer
    container was down 15:51Z / 15:53Z–17:01Z, then recreated and recommissioned in the `Fleet` controller phase at
    generation 1 with authenticated health 200 and `unless-stopped` restart policy at 17:03Z.
  - Pair ([restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/restored-state.json)):
    across both the A/B window (2026-11-02 21:45–22:24Z) and the requalification chain window (2026-11-03 06:44–07:28Z,
    after another of the owner's workloads held the host lock 22:25–06:44Z), no user session before or after either
    window; variant root stopped after each window, port 18090 closed, GPUs at 186 MiB on the display-attached RTX
    4090 and 0 MiB on the RTX 3090 (120.3–120.4 GiB available RAM).

## Update, 2026-11-02: Strata v0.2.9 with OMP 18.15.0 qualifies on every host and the Studio route

- **Owner decisions (verbatim answers and approvals, 2026-11-02).**
  - Window and screen approvals: tuple `v0.2.9` + `18.15.0` (`"latest stable of both"`); PRO
    `"Full: A/B + chain + arms + G23"` (the host's two unrelated optical character recognition (OCR) containers left
    exited as found); pair window scheduled before the owner's queued NInfer job on `rtx3090-win-a`; RTX 5090
    `"Tonight"` window after the owner's NInfer window with Docker Desktop and WSL stopped and production NInfer
    downtime authorized; comparison-only model screens for `UD-IQ4_XS` on the PRO
    and pair, `NVFP4-QAD` on the PRO, and `DeepSeek V4.1 IST-DAS 2.25` on the PRO.
  - Qualification and follow-up approvals: `"Push, PR, qualify on green CI"` (PR #72; hosted
    [CI run 41457827645](https://github.com/alphastorm/omp-strata/actions/runs/41457827645); qualification commit
    `4bb634d`), removing the `v0.2.3` RTX 5090 integration roots on `rtx5090-win-a`, and follow-up work packages (not
    part of the current profiles) to pin the comparison-only `v0.2.9` feature-arm winners on all three hosts and prepare
    `UD-IQ4_XS` and `NVFP4-QAD` for his Terminal-Bench run.
- **Qualified selections and rollbacks (`6fec79d`, `8002c77`, `276bbaa`, `4bb634d`, `fa57d8c`).** All five `v0.2.9`
  (engine `0.1.55`) + OMP `18.15.0` candidates qualify and become current, rolling back to their `v0.2.8` (engine
  `0.1.54`) + OMP `18.14.0` predecessors (`v0.2.7` + OMP `18.13.2` on the RTX 5090 and the earlier `v0.2.8` variants on
  the PRO, pair and Studio route move to earlier qualified history):
  - PRO (`rtxpro6000-win-a`) **current**:
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0` (fingerprint
    `00bc4e0d5370c9f8438dedc095668c7c03cf57605262f6fad2e2aea390d4bc79`;
    [manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json)),
    now `tests/candidate.py` `CURRENT`, rolling back to
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0`.
  - RTX 5090 (`rtx5090-win-a`) **default**:
    `win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0` (fingerprint
    `bf4f1a94783ec0dd4fa2835bff79f135254bfe2a3d1eef1329b54692cdd2c580`;
    [manifest](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/qualification.json)), rolling back to
    `win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0`. Requires Docker Desktop and WSL stopped for its unchanged
    36 GiB start floor, with the production NInfer container recreated and re-registered after WSL restarts.
  - RTX 5090 (`rtx5090-win-a`) **qualified alternative**:
    `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0` (fingerprint
    `82c7d990060408e7be7847a8087eeeea2a8676fd812d172188037ba3f0a0e9f0`;
    [manifest](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/qualification.json)), rolling back to
    `win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`.
  - RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) **current**:
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`
    (fingerprint `f047ce69d596a00b1776292187fa2d13e98c682654c323487d069c09cfe73527`;
    [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json)),
    rolling back to
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`.
  - Mac Studio → PRO route **current**:
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0.json)
    (route fingerprint `d647865808eb4bb148977a9478f47e39bac1366680758691598f6f87420bc34a`;
    [manifest](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/manifest.json),
    [ledger](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/qualification.json)), whose
    member `rtxpro6000-win-a` pins the PRO `v0.2.9` current profile and `members[0].server_fingerprint`
    `00bc4e0d5370c9f8438dedc095668c7c03cf57605262f6fad2e2aea390d4bc79` on local port `18191`, rolling back to
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0.json)
    (the `0.2.8` `slots4-parking` route moves to earlier qualified history).
  - Campaign [`releases/campaigns/v0.2.9.json`](../releases/campaigns/v0.2.9.json) is `complete` across all five rows
    (`4bb634d`), and the CI `suite` matrix (`fa57d8c`) runs the eight current `v0.2.9` and rollback `v0.2.8` server
    profiles.
- **Version A/B, gates and G24 coding evaluation per lane versus v0.2.8.** Cold-start version A/B (`A B B A A B`, where
  `A` is the `v0.2.8` current root and `B` is the `v0.2.9` root) showed `par_analyze` aggregate output `tok/s` `B/A`
  ratios of **0.996–1.012** on the PRO, **0.999–1.001** on the RTX 5090 262K and **1.003** on the pair, with overlapping
  `perf_probe` TTFT and decode ranges (the initial ready-time gap on the freshly installed PRO and RTX 5090 roots came
  from cold Windows file cache and disappeared once file-cache-warm: 35.1 s in G16/G20 on the PRO and 16.6–16.8 s in
  G16/G20/G21 on the RTX 5090 262K). Every current server ledger has **21 pass, 3 not applicable** (G22, G23, G25), with
  0 timeouts and 0 protocol counters
  ([measurements](MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150)):
  - **PRO (`slots4-batchmtp-pledirect`):** G24 scored **16/18** (pilot **5/6**, batch wall 576.248 s; misses:
    `tool-loop` x2 on attempts 2 and 3) versus **15/18** (pilot 6/6, 634.630 s) on `v0.2.8`; main chain at tooling
    `6fec79d`, G10 112.58 GiB available RAM and 81.28 GiB commit headroom of 219.70 GiB, G16/G20 restart readiness
    35.1 s (G21 39.7 s), G19 8,192 MiB cache (28 parks), G26 in a second root (`install` 21.4 s, `start` 56.9 s).
  - **RTX 5090 262K (default):** G24 scored **16/18** (pilot **6/6**, batch wall 840.387 s; misses: `tool-loop` x2 on
    attempts 1 and 2) versus **17/18** (pilot 6/6, 864.890 s) on `v0.2.8`; main chain at `6fec79d` with Docker Desktop
    and WSL stopped, G10 10.55 GiB available RAM and 17.55 GiB commit headroom of 85.15 GiB, G16/G20/G21 restart
    readiness 16.6–16.8 s (lowest available RAM 6.56 GiB in G17), G19 3,072 MiB cache (21 parks), G26 (`install` 10.9 s,
    `start` 19.8 s).
  - **RTX 5090 131K (qualified alternative):** G24 scored **14/18** (pilot **5/6**, batch wall 762.536 s; misses:
    `tool-loop` x3, `bugfix-a` x1 on attempt 2) versus **18/18** (pilot 5/6, 967.658 s) on `v0.2.8`; main chain at
    `6fec79d` (ran in the same Docker Desktop/WSL-stopped window as the 262K chain; the profile's 34 GiB start floor
    also allows starting with Docker Desktop and WSL running), G10 12.03 GiB available RAM and 18.78 GiB commit headroom
    of 85.15 GiB, G16/G20/G21 restart readiness 26.8 / 16.1 / 16.3 s (lowest available RAM 7.52 GiB in G17), G19
    3,840 MiB cache (31 parks), G26 (`install` 12.0 s, `start` 35.4 s).
  - **Pair (`roles-split24-trimweights-pledirect`):** G24 scored **15/18** (pilot **5/6**, batch wall 974.881 s; misses:
    `tool-loop` x3) versus **15/18** (pilot 5/6, 941.725 s) on `v0.2.8`; main chain at `8002c77` after admitting engine
    `0.1.55`'s stage order, G10 65.67 GiB available RAM and 27.74 GiB commit headroom of 135.69 GiB, G16/G20/G21 restart
    readiness 55.4–55.6 s (45.1 s in the A/B blocks), G17 near-limit task wall 60.4 s, G19 8,192 MiB cache (30 parks),
    G26 (`install` 25.9 s, `start` 54.5 s).
  - **Host-free receipts (`G00–G06`, `276bbaa`):** `G00` binds to `6fec79d`, `G01–G05` bind to the 866-test host-free
    suite at `2ccea3c` (`4` skips on each single-GPU lane, `29` on the pair), and `G06` cites green PR #72
    [CI run 41457827645](https://github.com/alphastorm/omp-strata/actions/runs/41457827645) at `2ccea3c`.
  - **Studio → PRO route G23:** passed on 2026-11-02 at implementation `6fec79d`
    ([receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/receipts/0042355d187c480780d38e7e3ee9b5ee.json)):
    missing key refused before launch, wrong key 401, health RTT 5.7–8.5 ms, stream TTFT 0.206 s, tunnel drop and
    reopen (0.91 s), client restart (1.04 s) and verified server restart (1.51 s, new server instance) recovery all
    true.
- **Admissions, comparison-only feature arms and PRO model screens.** Commit `7ea7f12` admits `v0.2.9`'s multi-GPU
  setup-planning block (slicing off the unreachable replica-profile and HIP four-card sub-statements and checking the
  replica guard against `install.scrubbed_env`); `2a4aae9` pins the NVFP4 conversion recipe per profile and admits
  `v0.2.7+`'s `tools/nvfp4_local_pack.py` (`0fbbf068`); and `8002c77` admits engine `0.1.55`'s stage order after all six
  pair A/B starts parsed `kept_configured` (RTX 3090 first on layers 0–23, RTX 4090 last on layers 24–47 at pinned
  manual split 24). In comparison-only feature arms on the `v0.2.9` roots, enabling stock's Linux-gated parallel stack,
  GDN tensor-core stack and `--kv-streaming off` together on the PRO raised four-concurrent `w2` throughput +35%,
  `4 × 32K` +15% and prefill +15–18% while cutting 32K–100K TTFT 13% and ready time 14% (+17 GiB available RAM); on the
  RTX 5090 262K, GDN cut 8K–100K TTFT 7–9% and `--kv-streaming off --kv-grow` freed +3.25 GiB available RAM at ready; and
  on the pair, setting the engine's `sm_86` defaults + GDN via config `env` raised `w1` +10% and decode +6–14%
  ([Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313)). On the PRO model screens, `UD-IQ4_XS`
  (273.1 tok/s at 32K, warm turn 1.21 s vs 1.085 s on IQ3_S, 1.115×, quality 2/2) and `NVFP4-QAD` served with PLE in RAM
  (307.4 tok/s at 32K, warm turn 1.96 s vs 1.015 s, 1.931×, quality 2/2; its `--ple-io direct` draft profile
  `win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0` was placement-limited on an HDD
  volume and stays an unqualified draft) entered rule 4 of the model-selection plan (32K decode $\ge 25\text{ tok/s}$
  and median warm 32K tool turn $\le 2\times$ same-window IQ3_S), while `DeepSeek V4.1 IST-DAS 2.25` (41.7 tok/s, warm
  turn 9.08 s, 6.801×) did not ([details](MEASUREMENTS.md#model-screens-on-the-pro)). Pinning the feature-arm winners and
  preparing `UD-IQ4_XS` and `NVFP4-QAD` for the owner's Terminal-Bench run are follow-up work packages.
- **Restorations.**
  - PRO ([server](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/restored-state.json),
    [route](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/restored-state.json)): both OCR
    containers already exited and left as found; no signed-in user before or after; every `v0.2.9` root and comparison
    engine stopped, port 18090 closed, GPU at 433 MiB idle (180.9 GiB available RAM).
  - Pair ([restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/restored-state.json)):
    no user session before or after; `v0.2.9` and `v0.2.8` roots stopped, port 18090 closed, GPUs at 186 MiB on the
    display-attached RTX 4090 and 0 MiB on the RTX 3090 (120.6 GiB available RAM).
  - RTX 5090 ([262K](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/restored-state.json),
    [131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/restored-state.json)): production NInfer
    container down 06:48–08:34Z (UTC, 2026-11-02); recreated by the owner's pinned relaunch script after WSL restart,
    stuck controller state retired (kept), commissioned at a new controller generation at 08:38Z with authenticated
    health 200 and `unless-stopped` restart policy; `v0.2.3` integration roots removed with the owner's approval.

## Update, 2026-10-31: stock v0.2.8 tuning profiles and the Studio batch-MTP route qualify

- **Owner decisions (verbatim answers, 2026-10-31).**
  - Window and admission approvals: `"Draft, then run pair arms"`, `"run everything on the PRO and approved"`,
    `"PRO: admit --batch-mtp + requalify"`, and `"Pair: admit trim + requalify"`.
  - Qualification and default selection: `"Qualify all; make PRO batch-MTP and pair trim current"`.
- **Qualified selections and rollbacks (`0e4912c`, `610be03`, `1afe412`).** Same component tuple as 2026-10-30: stock
  Strata `v0.2.8` (engine `0.1.54`) with stock OMP `18.14.0`; every change is a stock Strata option pinned in a new
  profile id:
  - PRO (`rtxpro6000-win-a`) **current**:
    `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0` (fingerprint
    `9f4a2da58a71a25236c54e177659295a662fcb477a73d868de8133650ffd96ff`;
    [manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json)),
    now `tests/candidate.py` `CURRENT`. Pins yesterday's PRO 262K `slots4-parking` choices plus `--ple-io direct`
    (`strata.ple_io: "direct"`, reading the 26.8 GiB PLE table from the model file instead of making it RAM-resident at
    start) and `--batch-mtp` (`strata.batch_mtp: true`, admitted at `c4956ef`: each of the 4 batch slots gets its own
    MTP drafter state, sharing the drafter weights; stock's own app enables `--batch-mtp` for one card of 24 GB+ with
    2+ slots in `apps/host/server/native-parallel.mjs`, while stock setup never writes it).
  - PRO (`rtxpro6000-win-a`) **qualified alternative**:
    `win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0` (fingerprint
    `0c5ba5d66d825ca7a68fe7b198ffef0bf586de0abdddb9c368753aef31a21837`;
    [manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json)),
    pinning PLE direct reads only (`strata.ple_io: "direct"`, without `--batch-mtp`).
  - PRO **rollback**: `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0` (yesterday's 2026-10-30
    current profile; its root stays installed; the `v0.2.7` PRO profile moves to earlier qualified history in its
    ledger).
  - RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) **current**:
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`
    (fingerprint `d35781251f4535919b54571def7c36b86cb150f264a82552ae2eefd8be344752`;
    [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json)).
    Pins yesterday's pair `roles-pledirect` choices plus stock's manual split point 24 (the layer the automatic planner
    chose; `strata.setup_args.layer_split: "24"` beside the unchanged stock roles `--gpu-roles 0=main,1=helper`, RTX
    4090 as Main staged last) and `--trim-stage-weights` (`strata.trim_stage_weights: true`, admitted at `c35254b`: each
    card loads only its own stage's dense weights).
  - Pair **rollback**: `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`
    (yesterday's 2026-10-30 current profile; the `v0.2.7` pair PLE-direct profile moves to earlier qualified history in
    its ledger).
  - RTX 5090 (`rtx5090-win-a`): unchanged (`win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0` default and
    `win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0` qualified alternative, rolling back to their `v0.2.7`
    predecessors).
  - Mac Studio → PRO route **current**:
    [`routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0.json`](../routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0.json)
    (route fingerprint `9dfafc293621e80a7ba8129a652449da465223d8b1d46b84fa9d50728ace8d74`;
    [manifest](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0/qualification.json)), whose
    member `rtxpro6000-win-a` pins the PRO current profile and `members[0].server_fingerprint`
    `9f4a2da58a71a25236c54e177659295a662fcb477a73d868de8133650ffd96ff` on local port `18191`, rolling back to
    [`routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json`](../routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json)
    (which pins the PRO `slots4-parking` rollback; the `0.2.7` route moves to earlier qualified history).
  - Campaign [`releases/campaigns/v0.2.8.json`](../releases/campaigns/v0.2.8.json) stays as recorded (`complete`),
    `scripts/campaign.py` `LANES` ranks variants qualified at the same release by lane order with the current variant
    last (`610be03`), and the CI `suite` matrix (`1afe412`) runs all nine current, qualified-alternative and rollback
    server profiles.
- **Gates, G24 coding evaluation and headline measurements.** Each new server ledger has **21 pass, 3 not applicable**
  (G22, G23, G25), with 0 timeouts and 0 protocol counters
  ([measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v028-2026-10-31-stock-omp-18140)):
  - **PRO batch-MTP + PLE-direct (current) and PLE-direct (alternative):** G24 scored **15/18** on each (pilot **6/6**
    on each; batch walls 634.630 s on batch-MTP and 569.254 s on PLE-direct; every miss is `tool-loop`'s known
    exact-money assertion, against 16/18, pilot 5/6, 788.171 s on yesterday's `slots4-parking` rollback; G24 cannot
    rank them). Headline wins: restart readiness G20 **35.0 s** (PLE direct) / **51.5 s** (batch-MTP) versus 88.2 s on
    `slots4-parking`; G16 **51.4 s** on both versus 85.6 s; G15 kill recall **49.5 / 49.2 s** (PLE direct) and
    **49.9 / 50.6 s** (batch-MTP) versus 92.5 / 84.9 s; G10 Windows commit headroom **81.29 GiB** (batch-MTP) and
    **82.79–82.91 GiB** (PLE direct) versus 55.37 GiB of 219.70 GiB; G26 in a new root on batch-MTP (`install`
    1,063.2 s, `start` 58.3 s vs 97.6 s). In back-to-back arms on the qualified root, `--batch-mtp` raised total output
    **+22.5%** at 2 concurrent requests (218.1–219.9 vs 177.6–179.1 tok/s), **+8%** at 4 × 2K (238.7–241.6 vs
    220.1–225.0 tok/s) and **+40%** summed decode at 4 × 40K prompts (288.6 vs 202.1–206.7 tok/s), neutral with one
    request. The first PLE-direct chain at `a92801a` stopped at start before any gate (`strata.ple_io: 'engine_log'`:
    single-card engine log was not captured); `2ae400d` fixed it with a regression test, a start and G10 probe passed
    before the full `2ae400d` chain (`fb31b6a`, `2531ae8`), and the batch-MTP chain ran at `d594b5f`.
  - **Pair split-24 trim + PLE-direct (current):** G24 scored **15/18** (pilot **5/6**, batch wall 941.725 s; misses:
    `tool-loop` x3, tying 15/18, pilot 5/6, 926.029 s on yesterday's `roles-pledirect` rollback). Headline wins: in
    arms on the qualified root, `--layer-split 24 --trim-stage-weights` grew each card's expert cache by **+1.8 GiB**
    (**19.15 / 17.76 GiB** on RTX 3090 / RTX 4090 vs 17.35 / 16.01 GiB), cut time to first token **-12%** at 32K–100K
    (10.1 / 17.8 / 27.5 s at 32K / 64K / 100K vs 11.4 / 20.1–20.4 / 31.0–31.7 s) with decode flat at 8K/100K, and cut
    gate G17's near-limit task wall to **60.8 s** versus 67.0 s (G16 / G20 restart readiness 43.1 / 44.2 s vs 43.7 /
    44.2 s; G10 commit headroom 27.84 GiB of 135.69 GiB; G26 in a new root: `install` 820.3 s, `start` 59.0 s; chain at
    `d594b5f`).
  - **Host-free receipts (G00–G06):** G01–G05 bind to the 857-test host-free suite at `681d504` (`2bf516a`), and G06
    cites green PR #70 [CI run 41224900293](https://github.com/alphastorm/omp-strata/actions/runs/41224900293) at
    `681d504`.
  - **Studio → PRO route G23:** passed on 2026-10-31 at implementation `610be03`
    ([receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0/receipts/ef6fcbc23ead437dae827704ce4d632f.json)):
    missing key refused before launch, wrong key 401, health RTT 5.1–8.8 ms, stream TTFT 0.278 s, tunnel drop and
    reopen (0.88 s), client restart (0.66 s) and verified server restart (1.62 s, changed server instance) recovery all
    true, and a one-turn `launch-omp` smoke answered `"ROUTE OK"`.
- **Restorations.**
  - PRO ([batch-MTP](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0/restored-state.json),
    [PLE-direct](../releases/win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0/restored-state.json),
    [route](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0/restored-state.json)): both OCR
    containers were already exited before the first window and left as found; no signed-in user before or after; both
    new `v0.2.8` roots stopped and port 18090 closed (GPU at 433 MiB logon screen).
  - Pair ([restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0/restored-state.json)):
    empty console session logged off at 13:25Z before the knob arms to free the login-screen desktop's 1,740 MiB on the
    RTX 4090; after: no user session, split-24 trim root stopped, port 18090 closed, GPUs at 186 MiB on the
    display-attached RTX 4090 and 0 MiB on the RTX 3090.

## Update, 2026-10-30: Strata v0.2.8 with OMP 18.14.0 qualifies on every host and the Studio route; the RTX 5090 262K profile becomes its default

- **Owner decisions (verbatim answers, 2026-10-30).**
  - Window approvals: PRO `"Run now, leave OCR as found"`; RTX 5090 `"131K + 262K with Docker/WSL down"`; pair
    `"Sign out now: both variants, then the main chain"`; G10 diagnostic `"Run the diagnostic now"`.
  - `"Which v0.2.8 + OMP 18.14.0 candidates should I qualify and land on PR #69?"` → `"PRO, 5090 131K, pair, route"`.
  - `"RTX 5090 262K opt-in: rerun G10 with Docker/WSL stopped ..., or keep the opt-in on v0.2.7?"` →
    `"Let's make it the default we want the bgiger context"`.
- **Qualified selections and the RTX 5090 default switch.** All five `v0.2.8` (engine `0.1.54`) + OMP `18.14.0`
  candidates qualify and become current, rolling back to their `v0.2.7` (engine `0.1.52`) + OMP `18.13.2`
  predecessors (`v0.2.3` + OMP `18.12.6` moves to earlier qualified history):
  - PRO (`rtxpro6000-win-a`):
    `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0`
    ([manifest](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/qualification.json)), now
    `tests/candidate.py` `CURRENT`.
  - RTX 5090 (`rtx5090-win-a`) **default**:
    `win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0`
    ([manifest](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/qualification.json)), rolling back to
    `win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2`. Operating condition (unchanged): 36 GiB available-RAM
    start floor; the host's Docker Desktop and WSL (which run its production NInfer container) must be stopped; after
    WSL restarts, that container must be recreated by the owner's pinned relaunch script and re-registered with the
    owner's fleet controller.
  - RTX 5090 (`rtx5090-win-a`) **qualified alternative**:
    `win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`
    ([manifest](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/qualification.json)), rolling back to
    `win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2`. Keeps its 34 GiB start floor and starts with Docker
    Desktop and WSL running (production container stopped by the fleet controller); qualified, no longer the default.
  - RTX 4090 + RTX 3090 pair (`rtx3090-win-a`):
    `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`
    ([manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json)),
    rolling back to `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`.
  - Mac Studio → PRO route:
    [`routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json`](../routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json)
    ([manifest](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/manifest.json),
    [ledger](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/qualification.json)), rolling back to
    `routes/client-rtxpro6000-262k-strata0.2.7-omp18.13.2.json`.
  - Campaign [`releases/campaigns/v0.2.8.json`](../releases/campaigns/v0.2.8.json) is `complete` across all five rows,
    and the CI `suite` matrix runs the eight current and rollback server profiles.
- **Gates and G24 coding evaluation per lane versus v0.2.7.** Every current server ledger has **21 pass, 3 not
  applicable** (G22, G23, G25), with 0 timeouts and 0 protocol counters:
  - **PRO:** G24 scored **16/18** (pilot **5/6**, batch wall 788.171 s; misses: tool-loop x2) versus **15/18** on
    `v0.2.7`; main chain at tooling `278e53c`, operator receipts at `4853ab3` (833 tests, 4 skips; green PR #69
    [CI run 40989725083](https://github.com/alphastorm/omp-strata/actions/runs/40989725083) at `4853ab3`).
  - **RTX 5090 262K (default):** G24 scored **17/18** (pilot **6/6**, batch wall 864.890 s; miss: tool-loop x1) versus
    **16/18** on `v0.2.7`; main chain at `278e53c` (where G10 failed on the listener check below), G10 rerun pass and
    operator receipts at `f9e8c74` (835 tests, 4 skips; green
    [CI run 40996143852](https://github.com/alphastorm/omp-strata/actions/runs/40996143852) at `f9e8c74`, Docker
    Desktop and WSL stopped).
  - **RTX 5090 131K (alternative):** G24 scored **18/18** (pilot **5/6**, batch wall 967.658 s; all six tasks 3/3)
    versus **16/18** on `v0.2.7`; main chain at `278e53c` (ran in the Docker Desktop/WSL-stopped window; G10 failed
    there), G10 rerun pass at `f9e8c74` with Docker Desktop and WSL running, and operator receipts at `f9e8c74`.
  - **Pair PLE-direct:** G24 scored **15/18** (pilot **5/6**, batch wall 926.029 s; misses: tool-loop x3) versus
    **17/18** on `v0.2.7`; main chain and operator receipts at `4853ab3` (833 tests, 29 skips) after engine `0.1.54`
    stage-order admission.
  - **Studio → PRO route G23:** passed at `4853ab3`
    ([receipt](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/receipts/e0d2532492834f928703268e14bdd7b9.json)):
    missing key refused before launch, wrong key 401, health RTT 6.1–6.7 ms, stream TTFT 0.199 s, tunnel drop and
    reopen (0.85 s), client restart (0.75 s) and verified server restart (1.65 s) recovery all true.
- **G10 listener check on Windows build 26300.9818 (`f9e8c74`).** On `rtx5090-win-a` (which installed the 2026-10
  Windows 11 preview update, build 26300.9818, on 2026-10-29; the PRO and pair hosts run 26300.9711), both main chains
  at `278e53c` passed every gate except G10, where `netstat` stopped listing the serving listener on
  `127.0.0.1:18090` and printed closing loopback connections as `LISTENING` rows owned by PID 0 while the server
  answered every request (reproduced on the host with a plain `ThreadingHTTPServer`: 0 of 20 checks in `netstat` versus
  20 of 20 checks in `GetExtendedTcpTable`'s listener class, which reported the listener's state as `FIN_WAIT1`). Commit
  `f9e8c74`
  reads `GetExtendedTcpTable`'s listener class while keeping ownership and loopback rules unchanged; both G10 reruns
  passed ([131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/receipts/g10-20261030T032320Z-cd9473.json)
  with Docker/WSL up, [262K](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/receipts/g10-20261030T033442Z-92efcf.json)
  with Docker/WSL stopped), and the failed main-chain G10 receipts remain in the ledgers
  ([details](MEASUREMENTS.md#rtx-5090-g10s-listener-check-on-windows-build-263009818)).
- **Pair stage order, the Strata#4518 measurement on Windows, and why the pair keeps PLE direct.** Engine `0.1.54`'s
  stage order was admitted at `4853ab3` after all 4 starts across the PLE-direct candidate and the measurement-only
  stock-residency draft (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`,
  [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0/manifest.json))
  parsed complete: RTX 3090 first on layers 0–23 with a 17.35 GiB expert cache, RTX 4090 last on layers 24–47 with
  16.01 GiB (auto K=24). On the stock-residency draft, [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)'s
  upstream fix locked the 26.8 GiB PLE table (33.9–34.0 s), then gave the lock back on both starts and sized the
  automatic conversation cache at **4,864 MiB** (106–112 s to ready), against **8,192 MiB** and 61–63 s to ready
  (43.7–44.4 s on chain restarts, **27.9 GiB** G10 commit headroom of 135.7 GiB) with `--ple-io direct` at matching
  100K-token TTFT (31.2 s with PLE direct versus 30.9 s with stock residency;
  [details](MEASUREMENTS.md#rtx-4090--rtx-3090-stage-order-and-strata4518-on-engine-0154)). The pair therefore keeps
  `--ple-io direct`, and the stock-residency draft stays unqualified.
- **Restorations.**
  - PRO ([server](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/restored-state.json),
    [route](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/restored-state.json)): OCR containers already
    exited and left as found; console signed out before and after; fleet-managed Strata lane not running and untouched.
  - Pair ([restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/restored-state.json)):
    owner's console session signed out at window start with his consent; after: no session, GPUs at 185 MiB on the display-attached RTX 4090 and 0 MiB on the RTX 3090.
  - RTX 5090 ([262K](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/restored-state.json),
    [131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/restored-state.json)): production NInfer
    container down 01:24–02:40Z, 02:49–02:56Z, 03:13–03:24Z and 03:32–03:39Z (UTC, 2026-10-30). Both Docker/WSL-down
    windows ended with the container recreated by the owner's pinned relaunch script and re-registered with the fleet
    controller (stuck controller state retired, kept); the two WSL-up windows returned the same container.
    Authenticated health 200 after each.
  [Measurements and methods](MEASUREMENTS.md#strata-v028-windows-2026-10-30-stock-omp-18140).

## Update, 2026-10-28 (afternoon): the pair's PLE-direct and RTX 5090 262K Strata v0.2.7 profiles qualify

- **Owner decisions (verbatim answers, 2026-10-28).**
  - `"File the Strata issue I drafted about the RAM table switching off the conversation cache and eating commit headroom?"` → `"Yes"`. Filed upstream as [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518).
  - `"Let two-GPU profiles keep that table on disk, then requalify the pair on v0.2.7?"` → `"Yes"`.
  - `"Run the 5090 262K qualification with Docker/WSL stopped?"` → `"Yes"`.
  - `"Keep or delete the PRO's 256 GiB of DeepSeek files, and prune the v0.2.1 installs?"` → `"Keep for now and then prune old"` (private host housekeeping; the v0.2.1 integration roots were deleted on every host, so v0.2.1 profiles are earlier qualified history in their ledgers, no longer installed rollbacks).
  - `"Qualify the reruns and land PR #68?"` → `"Qualify both and land"`.
- **The pair qualifies on v0.2.7 with direct PLE reads; v0.2.3 roles is the rollback.**
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`
  ([manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/manifest.json),
  [ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/qualification.json))
  pins `strata.ple_io: "direct"` (stock engine flag `--ple-io direct` on engine 0.1.52, keeping the 26.8 GiB PLE
  table on direct SSD reads instead of automatic RAM residency; profile IDs now allow 3–120 characters, and an
  engine flag is used because launch strips inherited `STRATA_*` variables and multi-GPU profiles refuse `env`
  overrides). In the 2026-10-28 18:35–19:22Z requalification run on a fresh root (model shards linked from the
  v0.2.3 roles root) at tooling `7f7b16d`, every measured gate (G10–G21, G24, G26) and operator receipt (G00–G06
  at `8c1ae59`: 827 tests, 29 skips, no failures; green PR #68
  [CI run 40745659264](https://github.com/alphastorm/omp-strata/actions/runs/40745659264) at `f3ba668`) passed
  (21 pass, 3 not applicable: G22, G23, G25). With the engine serving,
  [G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/evidence/g10-20261028T183648Z-4f70e0.json)
  measured **27.3 GiB** (`29,328,113,664 B`) Windows commit headroom of a **135.7 GiB** (`145,695,096,832 B`)
  commit limit and **65.1 GiB** (`69,902,020,608 B`) available RAM (versus 1.03 GiB on the held v0.2.7 roles draft
  and 27.3 GiB on v0.2.3 roles). Across all 16 starts of this root (main chain plus a perf pass), every start
  logged `PLE direct read probe: N rows/s (fine)`, none logged a residency-policy line, and every start sized the
  automatic conversation cache at **8,192 MiB** (up to 4 parked conversations; 20 parks during G19). G24 scored
  **17/18** (pilot **5/6**, batch wall 1,029.479 s; tool-loop 2/3, every other task 3/3), versus 14/18 on v0.2.3
  roles and 13/18 on the held v0.2.7 roles draft. Its rollback is
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6`. The profile was drafted
  against the v0.2.7 campaign's frozen release inventory; upstream later added its 0.2.7.1 assets (Control 0.1.53,
  ARM64 and macOS DeepSeek packages) to the same GitHub release while the pinned Windows CUDA 13 engine asset
  remained unchanged.
- **The RTX 5090 262K opt-in qualifies on v0.2.7; v0.2.3 262K is the rollback, and 131K stays the default.**
  `win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2`
  ([manifest](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/manifest.json),
  [ledger](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/qualification.json)) reran on
  2026-10-28 17:04–17:30Z on the same root as the failed morning run at tooling `1914e84`, with the host's Docker
  Desktop and WSL stopped. Every measured gate and G00–G06 (818 tests, 4 skips at `1914e84`; green
  [CI run 40745659264](https://github.com/alphastorm/omp-strata/actions/runs/40745659264)) passed (21 pass, 3 not
  applicable); the morning's failed receipts stay in the ledger. With Docker Desktop and WSL stopped, the host has
  **39.8 GiB** available RAM against the profile's unchanged **36 GiB** start floor, whereas with the production
  NInfer VM resident the host shows **35.7–36.2 GiB** and starts and restarts refuse. Operating condition: the
  host's Docker Desktop and WSL, which also run its production NInfer container, must be stopped; after WSL
  restarts that container must be recreated (same image and configuration; the qualified v0.2.3 262K rollback has
  the same constraint now because the newer NInfer VM is larger). With the engine serving, G10 measured
  **9.98 GiB** (`10,720,952,320 B`) available RAM and **6.92 GiB** (`7,427,244,032 B`) commit headroom of a
  **75.2 GiB** (`80,696,807,424 B`) commit limit; G16 restart reached readiness in **16.7 s** (lowest available RAM
  during G16: **8.46 GiB**); and G19 had the automatic conversation cache on at **1,792 MiB** with **16 parks**
  (v0.2.3 262K: cache off). G24 scored **16/18** (pilot **5/6**, batch wall 755.239 s; tool-loop 1/3, every other
  task 3/3), versus 14/18 on v0.2.3 262K and 15/18 on v0.2.1. Its rollback is
  `win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6`.
- **Held drafts, campaign completion and restoration.** The pair's v0.2.7 roles draft
  ([manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2/manifest.json),
  PLE in RAM) stays a held draft; its blocker records that the PLE-direct variant cleared it for the lane. The
  pair's v0.2.7 default-split draft
  ([manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.7-omp18.13.2/manifest.json))
  stays unmeasured. In [`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json), the qualified pair row
  was renamed to the PLE-direct variant before the RTX 5090 262K row qualified, completing the v0.2.7 campaign
  across all five rows (`status: "complete"`). Restoration is recorded in
  [pair PLE-direct](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/restored-state.json)
  (stopped at 185 MiB on the display-attached RTX 4090 and 0 MiB on the RTX 3090, signed out) and
  [RTX 5090 262K](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/restored-state.json)
  (production NInfer container recreated with the same image and configuration after WSL restarted, returning
  authenticated health 200). [Measurements and methods](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132).

## Update, 2026-10-28: post-landing correction — the pair stays on v0.2.3 roles

**Historical morning record; the pair's current selection, its rollback (now v0.2.3 roles after v0.2.1 integration
roots were removed), and the RTX 5090 262K opt-in are superseded by the afternoon qualification above, while the
v0.2.7 roles draft (PLE in RAM) itself stays held.**

- **Lead decision under the owner's overnight authority.** After PR #66 landed at
  `0162b67f4bf47d812da5045227366069a8b02c8e`, the lead returns the pair's current selection to
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6`, whose qualified root
  is intact. Its rollback remains `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.1-omp18.10.1`
  (default split), as before PR #66. The owner's authority is unchanged: "You have exclusive access to the fleet
  overnight just FYI so authorized to do whatever". This corrects the initial pair qualification below, not the
  PRO, RTX 5090 131K default or independently qualified Studio route.
- **Measured blocker, not a failed-gate rewrite.** The pair's v0.2.7 roles
  [manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2/manifest.json)
  returns to **draft**. With the engine serving, its
  [G10 record](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2/evidence/g10-20261028T102119Z-7ef761.json)
  has **1,109,463,040 B (1.03 GiB)** Windows commit available, against
  [v0.2.3 roles' G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6/evidence/g10-20261023T135342Z-801f98.json)
  **29,320,192,000 B (27.3 GiB)** at the same **145,695,096,832 B (135.7 GiB)** commit limit. A later v0.2.7
  pair bench independently sampled **0.632–1.331 GiB** headroom. These are observations, not proof of an
  allocation failure; integration gate passes do not make that narrow margin acceptable for the current selection.
  All receipts and the 21-pass, 3-not-applicable qualification ledger remain unchanged as evidence.
- **Cause and clearance.** Engine 0.1.52's per-layer embedding (PLE) residency policy locks the **26.8 GiB**
  table in RAM and leaves the automatic conversation cache off on this 128 GB host. A throwaway
  `STRATA_PLE_AUTO_RAM=0` arm on the same v0.2.7 root restored the **8,192 MiB** cache, with 100K-token TTFT
  **31.15 s versus 30.40 s** for stock residency. Multi-GPU profiles cannot set engine environment overrides,
  and inherited `STRATA_*` variables are scrubbed; this arm is not a selectable qualified profile. Clear the hold
  with an engine fix, or a profile capability that keeps the PLE table on direct reads for multi-GPU profiles,
  followed by measured requalification showing adequate commit headroom and conversation caching. No page-file,
  RAM-floor or environment workaround is authorized by this correction.
- **Unaffected lanes.** The PRO's v0.2.7 G10 retains **53,679,923,200 B (53.7 GB)** commit headroom; the RTX 5090
  131K root does not lock the PLE table because the policy declines on its 47 GiB host. Both current profiles and
  the Studio→PRO route remain qualified on v0.2.7. The RTX 5090 262K opt-in stays on v0.2.3 for its separate
  startup-RAM blocker. [Measurements and methods](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132).
- **Campaign tooling limit.** `scripts/campaign.py` makes `qualified` terminal (`TRANSITIONS["qualified"]` is
  empty), so `set-host` cannot change the pair row to `blocked`. The
  [v0.2.7 campaign](../releases/campaigns/v0.2.7.json) retains its landing-time row and restoration reference;
  this dated decision and the current release manifest record the correction, as the per-lane decision precedent
  in PR #27 does. `verify_release.py` permits a draft with measured receipts and requires no new restored-state
  note for this metadata correction. No receipts, ledger or restoration evidence are deleted or rewritten.

## Update, 2026-10-28: Strata v0.2.7 with OMP 18.13.2 qualified selections and held drafts

**Landing-time record; the pair's qualification and current/rollback selection are superseded by the
post-landing correction above.** The other lane decisions and all measured evidence remain unchanged.

- **Authority and lead disposition.** On 2026-10-28 the owner asked to "qualify across the fleet (with the latest
  OMP version)", then authorized "You have exclusive access to the fleet overnight just FYI so authorized to do
  whatever" and "Including logging out - just do it without asking me". Under that authority, the qualification
  lead selects the PRO, RTX 5090 131K default, pair stock-roles profile and Studio route above as qualified, with
  no manifest blockers. This is a per-lane evidence decision, not blanket approval of every draft or a
  default-runtime replacement.
- **The three server ledgers have 21 pass and 3 not applicable** (G22, G23 and G25). The PRO main run passes;
  the RTX 5090 131K main G15 failure remains beside its passing same-root rerun; the pair's complete
  `requalify-20261028T101905772830Z` main run passes every measured gate at tooling `15c7426` ([measurements](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132)).
  Ledgers: [PRO](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2/qualification.json),
  [RTX 5090 131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2/qualification.json),
  [pair roles](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2/qualification.json).
- **Quality is bounded, not inferred from integration passes.** G24 scored PRO **15/18** versus v0.2.3's 17/18,
  RTX 5090 131K **16/18** versus 17/18, and pair roles **13/18** versus 14/18 (pair pilot **6/6**).
  The lead accepts these recorded task failures for integration qualification; all unsuccessful attempts remain
  in the denominator. No engine-only comparison, quality superiority or cause for the score changes is claimed.
- **The pair's conversation cache is explicitly off.** Engine 0.1.52 locked the **26.8 GiB PLE table in RAM**
  and left its automatic conversation cache disabled on this host; the published G19 evidence reports
  `automatic_conversation_cache.enabled: false` and `budget_mib: 0`. G19 tests transcript behavior against that
  engine-reported state rather than requiring parking the engine left disabled. The profile's historical
  `parking` name is not a guarantee of an enabled cache. This is consistent with qualifying the v0.2.3 RTX 5090
  262K opt-in with the engine's cache off. No cache size, RAM floor or stock default was overridden to get a pass.
- **The Studio route qualifies independently.** Its [G23 ledger](../releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/qualification.json)
  passes from tooling `15c7426` (`scripts/remote_gates.py`); the `launch-omp` smoke returned 0. Missing key was
  refused before launch, wrong key returned 401, health RTT was 8.0–41.4 ms and tunnel stream TTFT 0.316 s.
  A tunnel drop failed the turn with the prior transcript preserved; recall passed after tunnel reopen
  (1.04 s), client restart (0.78 s) and verified server restart (1.60 s, changed instance). TTFT includes server
  work, not SSH-only overhead, and cold transcript re-prefill is expected.
- **Held drafts are not qualified.** The [RTX 5090 262K draft](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/manifest.json)
  remains blocked on host RAM headroom: restarts saw 35.x GiB against the unchanged 36 GiB floor
  (G16 evidence: 35.8 GiB), with failed later gates. The v0.2.3 262K profile stays the qualified opt-in with its v0.2.1
  rollback. The [pair default-split measurement draft](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.7-omp18.13.2/manifest.json)
  was stopped during download: no start or measurement ran and the roles profile's evidence does not apply to it.
- **Restoration is recorded, not inferred from qualification.** On the PRO, both OCR tenant containers were
  already exited and the fleet-managed Strata lane already down by owner decision; both stay as found. The
  v0.2.7 root is stopped, port 18090 closed, the GPU is about 600 MiB display-only, and the owner's initially
  signed-in console is signed out for him to sign in himself. On the RTX 5090, `fleet use` reserved the owner's
  production NInfer container at 08:20Z (Ready, generation 6); `fleet return` restored the same container at
  10:19Z (generation 7, authenticated health 200, GPU 30.4 GB). His disconnected session was signed out at
  08:21Z. The pair had no user session before or after, stayed signed out all night and ended at 180 MiB on the display-attached RTX 4090 and 0 MiB on the RTX 3090.
  Route G23 ran inside the PRO window and its v0.2.7 server root was stopped afterwards. Records:
  [PRO](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2/restored-state.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2/restored-state.json),
  [pair](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2/restored-state.json),
  [route](../releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/restored-state.json).
- **Rollbacks and campaign.** The three current server profiles and current route roll back to their v0.2.3
  predecessors; the qualified RTX 5090 262K opt-in stays on v0.2.3. The
  [v0.2.7 campaign](../releases/campaigns/v0.2.7.json) records four qualified rows with release/restoration
  references and the 262K row blocked. It is not a fully qualified five-row campaign. Earlier profiles,
  receipts and roots remain independent; no NInfer default or shared OMP installation changes.

## Update, 2026-10-23: the Mac Studio client route qualifies for the PRO's v0.2.3 profile

- **The owner qualified `client-rtxpro6000-262k-strata0.2.3-omp18.12.6` as the Studio's current route.** Ask
  answered on 2026-10-23: "Run G23; qualify if it passes". Stock OMP 18.12.6 reaches
  `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6` through the SSH local forward owned by foreground
  `launch-omp`. Its independent ledger has G23 passing, no manifest blockers, and `verify_release.py --require-ready`
  passes. [Ledger](../releases/client-rtxpro6000-262k-strata0.2.3-omp18.12.6/qualification.json).
- **G23 passed from the Mac Studio client on 2026-10-23 at `de60693`.** Missing key refused before launch, wrong key
  refused with 401, health RTT 4.6-5.2 ms and stream TTFT 0.171 s through the tunnel. A tunnel drop failed the turn
  in flight with the prior transcript preserved; nonce recall passed after tunnel reopen (0.77 s), client restart
  (0.71 s) and verified server restart (2.67 s, changed server instance). The first attempt stopped before G23: the
  private engine switcher still listed a pruned PRO root and could not stop it; it now skips a placement whose root
  is gone.
- **`client-rtxpro6000-262k-strata0.2.1-omp18.10.1` is its qualified rollback**, pinned to the PRO's v0.2.1 262K
  rollback. Every route keeps its own identity and ledger and inherits no server evidence.

## Update, 2026-10-23: Strata v0.2.3 with OMP 18.12.6 qualifies on every host

- **The owner qualified all four server profiles and selected them as current.** Ask answered on 2026-10-23:
  "Qualify all three" (PRO, RTX 5090 131K and 262K opt-in) and, for the pair, "Rerun; qualify if it passes" after
  choosing "Roles chain (4090 Main)". Each ledger has 21 pass and 3 not applicable (G22, G23 and G25), the manifests
  have no blockers, and `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6/qualification.json),
  [RTX 5090, 131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.3-omp18.12.6/qualification.json),
  [RTX 5090, 262K opt-in](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6/qualification.json),
  [RTX 4090 + RTX 3090, roles](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6/qualification.json).
- **Engine 0.1.48 sizes its own conversation cache** (Strata#3493), so profiles no longer pin stock's 8 GiB parking
  tip. It chose 8,192 MiB on the PRO and the pair, 1,024-1,280 MiB on the RTX 5090 131K root and none on the 262K
  root; G19 follows the engine's report. Stock plans, model pins and RAM floors are otherwise unchanged; the PRO and
  pair disk floors rise from 90 to 91 GiB for the MTP drafter fetch ([UPSTREAM.md](UPSTREAM.md)).
- **The pair moves to stock roles.** Engine 0.1.48's stage order was admitted after measuring the default, roles and
  split-32 drafts on the pair ([#48](https://github.com/alphastorm/omp-strata/issues/48),
  [measurements](MEASUREMENTS.md#strata-v023-windows-2026-10-23-stock-omp-18126)); the owner
  picked roles with the RTX 4090 as Main. The default and split-32 drafts stay unqualified measurement profiles.
- **Scored evaluation (G24):** PRO 17/18 (v0.2.1: 17/18), RTX 5090 131K 17/18 (17/18), 262K 14/18 (15/18), pair 14/18
  (v0.2.1: 16/18). Task failures remain counted.
- **Retained failures:** each beside its passing rerun on fixed tooling. The PRO's G10 rehash counted one artifact
  problem while the server ran, unnamed by the old record and not reproduced with the server stopped; the RTX 5090
  131K G20 compared scheduled tasks' run states while two of the host's own tasks ran; the 262K G19 expected
  parking the engine had left off; the pair's G18 final answer lost the remembered code after compaction at 222K
  tokens and kept it on the same-root rerun.
- **Rollbacks:** each host's previous current profile, v0.2.1 with OMP 18.10.1 (the pair's default-variant
  profile). No earlier receipt is inherited or replaced.
- Qualification is integration correctness, not a claim that every coding task passes, runtime superiority,
  or a default-runtime replacement decision. The Mac route requires its own independent G23 qualification.

## Update, 2026-10-21: the Mac Studio client route qualifies for the PRO's v0.2.1 profile

- **The owner qualified `client-rtxpro6000-262k-strata0.2.1-omp18.10.1` as the Studio's current route.**
  Ask answered on 2026-10-21 at approximately 02:29Z: "Qualify PRO, 5090 131K, 262K opt-in and route".
  Stock OMP 18.10.1 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1` through the SSH local
  forward owned by foreground `launch-omp`. Its independent ledger has G23 passing, no manifest blockers,
  and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.2.1-omp18.10.1/qualification.json).
- **G23 passed from the Mac Studio client on 2026-10-21 at `3f52b65`.** Missing key refused before launch,
  wrong key refused with 401, health RTT 4.7-5.1 ms and stream TTFT 0.171 s through the tunnel. A tunnel drop
  failed the turn in flight with the prior transcript preserved; nonce recall passed after tunnel reopen
  (0.81 s), client restart (0.68 s) and verified server restart (1.16 s, changed server instance).
  TTFT includes server work, not SSH-only overhead; cold transcript re-prefill is expected.
- **`client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1` is its qualified rollback**, pinned to the PRO's
  v0.1.44.1 262K rollback. The 0.1.43.1, 0.1.43 and 0.1.42 262K routes and the 0.1.41 131K route remain earlier
  qualified history. Every route keeps its own identity and ledger and inherits no server evidence.

## Update, 2026-10-21: Strata v0.2.1 with OMP 18.10.1 qualifies on every host

- **The owner qualified all four server profiles and selected them as current.** Ask answered on 2026-10-21 at
  approximately 02:29Z: "Qualify PRO, 5090 131K, 262K opt-in and route" and, for the pair, "Qualify 0.2.1 anyway".
  Each ledger has 21 pass and 3 not applicable (G22, G23 and G25), the manifests have no blockers, and
  `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1/qualification.json),
  [RTX 5090, 131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.1-omp18.10.1/qualification.json),
  [RTX 5090, 262K opt-in](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.1-omp18.10.1/qualification.json),
  [RTX 4090 + RTX 3090](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.1-omp18.10.1/qualification.json).
- **v0.2.1 ships its engine as a component.** It publishes no `strata-windows-x64.zip`; each profile pins the CUDA 13
  engine tarball (engine 0.1.46, versioned apart from the app) and its manifest identity, and `install` stages the
  verified files where stock setup reuses them ([OPERATIONS.md](OPERATIONS.md#upgrades)). Stock setup plans, model pins,
  engine flags and host floors are unchanged from each predecessor; the generated config adds only `args_written`.
- **Scored evaluation (G24):** PRO 17/18 (v0.1.44.1: 15/18), RTX 5090 131K 17/18 (15/18), 262K 15/18 (15/18), pair 16/18
  (v0.1.43.1: 15/18). Task failures remain counted.
- **Retained failures:** G17 failed on every host's main run because v0.2.0-beta made stock's server shorten a
  one-token-over `max_tokens` to the room left instead of answering 400; a prompt that alone leaves no room is still
  refused. G17 now expects that and passed on each host's rerun. G18 failed once on the RTX 5090 131K run (the final
  turn after compaction neither fixed the file nor recalled the fact) and passed on its same-root rerun. Both failures
  stay in the ledgers beside the newer passes.
- **The pair is slower than its rollback, accepted by the owner.** The automatic split moves to layers 0-24 / 25-47
  (v0.1.43.1: 0-31 / 32-47; the unqualified v0.1.44.1: 0-44 / 45-47). Back to back on the same host: decode 141-158
  against 170-201 tok/s, prompt reading at 64K-100K tokens 2,838-2,853 against 3,508-3,594 tok/s, 100K-token TTFT
  36.0 s against 28.6 s. Upstream closed Strata#2463 without a change to the link pricing.
- **Rollbacks:** each host's previous current profile (v0.1.44.1 on the PRO and RTX 5090, including the 262K opt-in;
  v0.1.43.1 on the pair). No earlier receipt is inherited or replaced.
- Qualification is integration correctness, not a claim that every coding task passes, runtime superiority,
  or a default-runtime replacement decision. The Mac route requires its own independent G23 qualification.

## Update, 2026-10-15: RTX 5090 Coder 262K qualifies as opt-in, not the default

- **The owner chose "Qualify as opt-in profile"** on 2026-10-15 at approximately 22:45Z for
  `win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1`. The RTX 5090's 131K profile remains current/default;
  no default profile, client route or `tests/candidate.py` CURRENT changes.
- **The opt-in ledger has 21 pass and 3 not applicable**, with G22, G23 and G25 disabled. Same stock Strata
  v0.1.44.1, stock OMP 18.10.1 and model pins as the 131K profile; configured context and provider window rise
  to 262,144 tokens, and available RAM required at startup rises from 34 to 36 GiB. It keeps its own root and
  [ledger](../releases/win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1/qualification.json).
- **G26's earlier failure remains recorded.** The original main run omitted installation from its summary;
  a same-root install/start/quickstart rerun passed with the same bound runtime identity. G24 scored 15/18
  and pilot 5/6, matching the 131K release; tool-loop remains 0/3 scored and 0/1 pilot.
  [Measurements](MEASUREMENTS.md). Qualification establishes integration correctness, not better task quality
  or runtime superiority, and does not authorize a default switch or release publication.

## Update, 2026-10-14: the Mac Studio client route qualifies for the PRO's v0.1.44.1 profile

- **The owner qualified `client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1` as the Studio's current route.**
  Ask answered on 2026-10-14 at approximately 15:30Z: "Qualify PRO, 5090, route; pair stays 0.1.43.1".
  Stock OMP 18.10.1 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1` through the SSH local
  forward owned by foreground `launch-omp`. Its independent ledger has G23 passing, no manifest blockers,
  and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1/qualification.json).
- **G23 passed from the Mac Studio client on 2026-10-14 at `78a26bf`.** Missing key refused before launch,
  wrong key refused with 401, health RTT 4.8-5.2 ms and stream TTFT 0.189 s through the tunnel. A tunnel drop
  failed the turn in flight with the prior transcript preserved; nonce recall passed after tunnel reopen
  (0.76 s), client restart (0.78 s) and verified server restart (1.35 s, changed server instance).
  TTFT includes server work, not SSH-only overhead; cold transcript re-prefill is expected.
- **`client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1` is its qualified rollback**, pinned to the PRO's
  v0.1.43.1 262K rollback. The 0.1.43 and 0.1.42 262K routes and the 0.1.41 131K route remain earlier
  qualified history. Every route keeps its own identity and ledger and inherits no server evidence.

## Update, 2026-10-14: Strata v0.1.44.1 with OMP 18.10.1 qualifies on the PRO and RTX 5090; the pair stays on v0.1.43.1

- **The owner qualified the PRO and RTX 5090 profiles and selected them as current.** Ask answered on
  2026-10-14 at approximately 15:30Z: "Qualify PRO, 5090, route; pair stays 0.1.43.1".
  Each ledger has 21 pass and 3 not applicable (G22, G23 and G25, with those capabilities or claims off),
  the manifests have no blockers, and `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1/qualification.json).
- **Their v0.1.43.1 + OMP 18.10.1 profiles are the qualified rollbacks.** Stock setup plans, model pins,
  engine flags and host floors are unchanged; each release keeps its own root and ledger. No earlier receipt
  is inherited or replaced, and task failures remain counted.
- **The RTX 4090 + RTX 3090 pair stays qualified and current on v0.1.43.1 with OMP 18.10.1.** Its
  v0.1.44.1 release is not qualified: the automatic layer split moves from layers 0-31 / 32-47 to 0-44 / 45-47
  on the RTX 4090 / RTX 3090. Measured back to back on the same host, decode falls from 184-206 to 148-154 tok/s
  and prompt reading to 0.52-0.77x; 100K-token TTFT is 55.0 s against 28.6 s. Its v0.1.43 rollback is unchanged.
  [Current pair ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1/qualification.json).
- Qualification is integration correctness, not a claim that every coding task passes, runtime superiority,
  or a default-runtime replacement decision. The Mac route requires its own independent G23 qualification.

## Update, 2026-10-13: the Mac Studio client route qualifies for the PRO's v0.1.43.1 profile

([REMOTE.md](REMOTE.md))

- **The owner qualified `client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1` as the Studio's current route.** Stock
  OMP 18.10.1 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1` through an SSH local
  forward owned by the foreground `launch-omp`. The independent ledger has G23 passing, the manifest has no
  blockers, and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1/qualification.json).
- **G23 passed from the Mac Studio client on 2026-10-13 at `d2fac61`.** Missing key refused before launch,
  wrong key refused with 401, health RTT 5.2-13.5 ms and stream TTFT 0.191 s through the tunnel. A tunnel drop
  failed the turn in flight with the transcript intact; the nonce was recalled after tunnel reopen (0.76 s),
  client restart (0.91 s) and verified server restart (1.39 s, changed server instance). A one-turn route smoke
  answered `ROUTE OK` (operator run context). TTFT includes server work, not SSH-only overhead.
- **`client-rtxpro6000-262k-strata0.1.43-omp18.10.1` is its rollback**, pinned to the PRO's v0.1.43
  262K rollback. Its G23 on 2026-10-12 recorded RTT 4.6-5.3 ms, TTFT 0.195 s, tunnel reopen 1.41 s, client
  restart 1.79 s and server restart 2.18 s. The 0.1.42 262K route and 0.1.41 131K route remain earlier
  qualified history. Every route keeps its own root, identity and ledger and inherits no server evidence.

## Update, 2026-10-13: Strata v0.1.43.1 with OMP 18.10.1 qualifies on all three hosts

([MEASUREMENTS.md](MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-13-stock-strata-v01431-stock-omp-18101))

- **The owner qualified all three profiles and selected them as current.** Each ledger has 21 pass and
  3 not applicable (G22, G23 and G25, with their capabilities or claims off), and
  `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43.1-omp18.10.1/qualification.json),
  [RTX 4090 + RTX 3090, 262K and parking](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1/qualification.json).
- **Only stock Strata's engine/archive and source pin move, to v0.1.43.1 (`a0116b2`).** Stock OMP 18.10.1
  (`5d0aaff`), the model pins, llama.cpp archive, Python lock, stock setup plans, engine flags and host floors
  are unchanged from v0.1.43. G00 records the quoted `</tool_call>` fix (#2026), fenced JSON tool-call recovery
  (#2037), prompt-loan fix (#2090), warning-only PLE direct-read probe (#1984), Windows watchdog disk-read
  allowance, pinned bounce buffers (#1996) and low-VRAM warning (#2065). All these Qwen3.8-Flash-Next packs
  carry the n-gram table. Batch-slot refusal handling (#1994) reaches only the PRO's four slots; parking
  progress (#2049) reaches the PRO and pair. Windows NVIDIA decode defaults remain unchanged. Upstream reports
  answers byte-identical to v0.1.43 apart from a quoted `</tool_call>`; that is an upstream report, not a
  measured answer-parity result from these runs.
- **All three hosts passed every measured gate in their first full run at `d2fac61`.** The PRO scored 15/18
  (tool-loop 0/3), against v0.1.43's 16/18 (1/3); its pilot passed 6/6 against 4/6, without the earlier OMP
  thinking-loop abort. The RTX 5090 scored 15/18 (tool-loop 0/3) and pilot 5/6, unchanged. Its full G18
  (g18 + g18l) passed the first time, with five reduced-threshold compactions; the rollback's original failed
  G18, rate probes and passing full rerun remain recorded.
- **The pair's G10 stage order is complete (`kept_1576`, both cards in configured order).** Scored 15/18
  against v0.1.43 run 2's 16/18: multifile-regression 2/3 and tool-loop 1/3; pilot 5/6 on both. The failed
  multifile-regression attempt records one malformed-arguments counter despite OMP exiting 0 and its verifier
  passing; the evaluator counts that attempt as unsuccessful. Client execution failures are zero in the new
  scored batches and pilots. Protocol counters are zero except that one pair scored attempt; qualification
  retains it, rather than claiming every counter or coding task passed.
- **Timing remains bounded run evidence, not a runtime-superiority claim.** The PRO's scored batch took
  555 s against 590 s. The RTX 5090 took 858 s against 658 s while doing more work
  (315 versus 277 tool calls, 154,887 versus 107,725 reported output tokens); batch wall per reported output
  token is 5.5 versus 6.1 ms, not isolated decode latency. The pair's reduced G18 took 125.4 s with six
  compactions against 44.7 s with one; G16/G21 readiness remains 54.7/55.0 s on both tuples. G26 first-start
  wall is 65.747 s; the runner's restart before G16 is about 70 s (about 69 s on v0.1.43 run 2), a different
  boundary from G16's verified-readiness metric. No new file-cache cause is inferred.
- **Hosted CI on PR #26 passed 26/26 at `d2fac61`.**
  [38328220748](https://github.com/alphastorm/omp-strata/actions/runs/38328220748) is the G06 audit's run.
  Each host's v0.1.43 + OMP 18.10.1 profile is its rollback; v0.1.42 and earlier qualified profiles keep their
  own roots and ledgers as history. The Mac Studio route followed in its own same-day G23 update above;
  local ledgers qualify no client route.
  Qualification is integration correctness, not task quality or a default-runtime replacement decision.

## Update, 2026-10-12: the Mac Studio client route qualifies for the PRO's v0.1.43 profile

([REMOTE.md](REMOTE.md))

- **The owner qualified `client-rtxpro6000-262k-strata0.1.43-omp18.10.1` as the Studio's current route.** Stock
  OMP 18.10.1 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1` through an SSH local
  forward owned by the foreground `launch-omp`. The route's independent ledger has G23 passing, its manifest has no
  blockers, and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.1.43-omp18.10.1/qualification.json).
- **G23 passed from the same Mac Studio client on 2026-10-12**, in one operator window on the PRO whose other GPU
  tenant yielded and was restored. The run refused a missing key before launch and a wrong key with 401, measured
  health RTT 4.6-5.3 ms and stream TTFT 0.195 s through the tunnel, failed the turn in flight when the tunnel
  dropped while preserving the transcript, and recalled the nonce after tunnel reopen (1.41 s), client restart
  (1.79 s) and verified server restart (2.18 s). A one-turn `launch-omp` through the route answered as asked. TTFT
  includes server work; this is not an SSH-only overhead claim.
- **`client-rtxpro6000-262k-strata0.1.42-omp18.8.9` is the route's rollback**, with the PRO's v0.1.42 262K
  profile; `client-rtxpro6000-strata0.1.41-omp18.8.6` stays qualified for the PRO's earlier 131K profile. Each
  route keeps its own ledger and inherits no server evidence.
- **`fix(remote)`:** with bindings that match the route, a `--remote` naming anything but the bound SSH alias now
  fails with that reason instead of the false "private bindings do not match the public route identity".

## Update, 2026-10-12: Strata v0.1.43 with OMP 18.10.1 qualifies on all three hosts

([MEASUREMENTS.md](MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-12-stock-strata-v0143-stock-omp-18101))

- **The owner qualified all three profiles and selected them as current.** Each ledger has 21 pass and
  3 not applicable (G22, G23 and G25, with their capabilities or claims off), and
  `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43-omp18.10.1/qualification.json),
  [RTX 4090 + RTX 3090, 262K and parking](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43-omp18.10.1/qualification.json).
- **Stock Strata v0.1.43 (`7695859`) and stock OMP 18.10.1 (`5d0aaff`) replace only the upstream pins.**
  Each release's G00 source audit records unchanged model pins, llama.cpp archive, Python lock and stock setup
  plan. The pair's host RAM floors are 86 GiB total and 78 GiB available at start, following stock setup's
  conversation-cache tip; its v0.1.42 262K profile had retained its 131K predecessor's 78/66 GiB floors.
  On Windows/NVIDIA, v0.1.43 keeps v0.1.42's decode defaults; G00 records the NaN guard, parallel expert reads,
  tail-skip change and request-timing fixes, not a runtime-superiority claim. For this provider the audited
  host-free multi-turn/tool/reasoning/forced-compaction capture has byte-identical OMP request bodies on
  18.10.1 and 18.8.9; that is a bounded capture, not a claim about every OMP request.
- **The PRO passed every measured gate in one run at `f6fa4d0`.** Scored evaluation 16/18, unchanged from
  v0.1.42; pilot 4/6 against 5/6. The pilot failed tool-loop and one bugfix-b attempt: the latter ended on OMP's
  thinking-loop detector, a client-side abort, not an engine failure. Both remain counted.
- **The RTX 5090's first run at `f6fa4d0` passed every measured gate except G18.** Its final fact-retention
  reply ended at `CODE: KEEP` with a normal stop, although its reasoning named the whole code. G00 records
  repeated G18 probes outside qualification runs: v0.1.43 passed 4/5 then 10/10; v0.1.42 passed 5/5 then 9/10,
  failing the same way. Both rates are 14/15, a pre-existing behavior of this IQ1_M model on this gate, not
  a new-release failure rate. One full G18 rerun (g18 and g18l) at `8bb1d54` passed and is the newest receipt;
  the failed receipt stays. Scored evaluation 15/18 (tool-loop 0/3) against v0.1.42's 16/18; pilot 5/6 on both.
- **The pair's first run at `f6fa4d0` failed G10-G21 and G26 on an integration admission error.** Lifecycle
  admitted multi-GPU stage-order inference only for v0.1.42 and reported the engine degraded: "startup stage
  order unavailable". `967086e` reviewed v0.1.43's unchanged stock `gpu_list`, `layer_split_value` and
  `ordered_gpus` digest and admitted it; a real start parses complete, layers 0-31 on the RTX 4090 and 32-47 on
  the RTX 3090. A host-free test now requires every multi-GPU profile to pin a reviewed release. Run 2 at
  `967086e` passed every measured gate, scored 16/18 against v0.1.42's 15/18, pilot 5/6 and quickstart pass.
  Both runs' receipts stay published; the newest receipt wins, without erasing the first run.
- **The pair's slower restart readiness is a measured host file-cache effect, not an engine change.** Receipts
  record 54.7-55.0 s against v0.1.42's 40.7-43.0 s. The operator's inspection of private engine startup logs
  records every start from G15 onward reading the 51.1 GiB expert pack unbuffered at 2.33-2.95 GiB/s, versus
  7.33-8.02 GiB/s through the Windows file cache before G15. The v0.1.42 root also read unbuffered on 2 of its
  12 starts on 2026-10-11. These are engine-log observations, not G21 load-rate metrics; the logs stay private,
  and no cause for the cache eviction is claimed. Single-GPU G16 readiness is unchanged within these runs:
  PRO 20.6 → 20.1 s, RTX 5090 12.1 → 11.6 s.
- **Hosted CI on PR #24 passed at each implementation checkpoint.**
  [38212474606](https://github.com/alphastorm/omp-strata/actions/runs/38212474606) at `f6fa4d0`,
  [38288518084](https://github.com/alphastorm/omp-strata/actions/runs/38288518084) at `967086e`, and
  [38294442014](https://github.com/alphastorm/omp-strata/actions/runs/38294442014) at `9729fb7`.
  Besides the stage-order fix, `9729fb7` makes `pull_run.py` refuse a requalify log naming more than one run.
- **Each host's v0.1.42 + OMP 18.8.9 profile is its rollback.** Earlier qualified profiles keep their own roots
  and ledgers as history. The Mac Studio client route followed the same day in its own update (above).
  Qualification is integration correctness, not task quality or a runtime-superiority decision.

## Update, 2026-10-12: the Mac Studio client route qualifies for the PRO's current 262K profile

([REMOTE.md](REMOTE.md))

- **The owner qualified `client-rtxpro6000-262k-strata0.1.42-omp18.8.9` as the Studio's current route.** Stock
  OMP 18.8.9 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9` through an SSH local
  forward owned by the foreground `launch-omp`. The route's independent ledger has G23 passing, its manifest
  has no blockers, and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.1.42-omp18.8.9/qualification.json).
- **G23 passed twice from the same Mac Studio client on 2026-10-11.** Both runs refused a missing key before
  launch and a wrong key with 401, recorded stream TTFT 0.196 s through the tunnel, failed the turn in flight
  when the tunnel dropped while preserving the transcript, and recalled the nonce after tunnel reopen
  (0.78-0.80 s), client restart (0.72-0.79 s) and verified server restart (1.35-1.48 s). TTFT includes server work,
  not an SSH-only overhead measurement. No new host run or receipt was needed for this qualification.
- **The 0.1.41 route remains qualified for the PRO's 131K rollback profile.**
  `client-rtxpro6000-strata0.1.41-omp18.8.6`, its server profile and both routes' pins and receipts stay unchanged.
  Each server retains its independent qualification; neither route qualifies a fleet or another client platform.

## Update, 2026-10-11: the pair qualifies at 262K with stock conversation parking

- **The owner selected 262K plus parking as current on `rtx3090-win-a`.** The new
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9` ledger has 21 pass and
  3 not applicable (G22, G23 and G25); `verify_release.py --require-ready` passes.
  [Ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9/qualification.json).
- **One root, one raw canonical run, no inherited receipts.** The unchanged runner completed install, start,
  G10-G21, the frozen evaluation and G26 on the profile's probe installation, whose fingerprint and generated
  files match. G26's install/start/QUICKSTART/tests all pass in that same summary. Stock flags and gate tolerances
  did not change; the RTX PRO 6000 remains the default candidate.
- **Only context and stock conversation parking change from the 131K display-on-RTX-4090 profile.** The same
  pins, layer split and pipeline windows 2 run at 262,144 tokens with `--conversation-cache-mib 8192`; no batch
  slots, calibration or prefill-chunk override. G19 restored 20,672 tokens after an intervening conversation,
  with a 491 ms follow-up. This is not an exact-output fidelity claim: the initial strict token-parity probe
  failed and a diagnostic live repeat itself differed. Those results remain separate from qualification.
- **Failures remain counted.** Pilot 5/6, scored 15/18, tool-loop 0/3; its exact-money verifier failures remain
  in the denominator. G24 passed the complete reporting experiment, not every coding task. Pre-G16 status
  returned 1, the runner restart returned 0 and G16 passed. The closing census found the root stopped, no
  engine or listener, and GPU memory back to 182/0 MiB.
- **The qualified 131K display-on-RTX-4090 profile is the rollback.** Its root and ledger stay unchanged.

## Update, 2026-10-11: the pair qualifies with the display on the RTX 4090 (131K rollback)

- **The owner qualified `win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9`.** It is now the 131K rollback on `rtx3090-win-a`; its ledger has 21 pass and 3 not applicable (G22, G23 and G25), and `verify_release.py --require-ready` passes. Ledger:
  [RTX 4090 + RTX 3090, display on RTX 4090](../releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9/qualification.json).
- **Only display placement changes.** Pins, IQ3_S at 131,072 tokens, stock layer split and pipeline windows 2 stay
  unchanged. The RTX 4090 is display-attached; the RTX 3090 is not. The original startup refusal at 1,601 MiB of
  display-GPU memory remains recorded; no ownership guard or tuning flag changed.
- **Failures remain in the evidence.** The continuation's degraded pre-G16 status was recovered by the runner
  restart, then G16 passed. Its first G26 receipt failed because that raw summary had no install row. A later
  install/start/quickstart/stop run on the same root passed G26 in one summary with the unchanged manifest
  runtime identity; no raw summaries were combined. The scored evaluation was 14/18, pilot 5/6, against 15/18
  and 6/6 on the display-on-RTX-3090 predecessor; all failed attempts count.
- **The predecessor remains qualified, not current.** Rollback to the display-on-RTX-3090 pw2 profile requires
  restoring that display placement. Single-card RTX 3090 profiles still do not apply while both cards are installed.

## Update, 2026-10-11: Strata v0.1.42 with OMP 18.8.9 qualifies on the RTX PRO 6000 and RTX 5090

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-at-262k-and-rtx-5090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889))

- **The owner qualified both profiles.** Each ledger has 21 pass and 3 not applicable (G22, G23 and G25, with their
  capabilities or claims off), and `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.42-omp18.8.9/qualification.json).
- **Only Strata and OMP change, and every measured gate passed on its first run.** The model pins, the llama.cpp
  archive, the Python lock and the stock setup plans are the v0.1.41 profiles', which are now their rollbacks. All
  three hosts' current profiles are on this tuple.
- **The coding evaluation is within one attempt of the v0.1.41 profiles:** scored 16/18 on both cards (17/18 on the
  PRO's v0.1.41 profile, 15/18 on the RTX 5090's), pilot 5/6 on both and the tool-loop task at 1/3 on both.
  Qualification is about integration correctness, not task quality.
- **The ledgers' speed and resource figures are unchanged:** 100K-token cold prefill 12.6 s on the PRO and 13.8 s on
  the RTX 5090, GPU peaks within 205 MiB of the v0.1.41 profiles. v0.1.42's new decode default, the route tail skip,
  does not apply on either card: both hold every expert in VRAM, and the PRO also runs batch slots. A comparison-only
  probe found prefill unchanged on both cards and decode unchanged on the PRO and, up to 32K tokens, on the RTX 5090;
  at 64K and 100K the RTX 5090 decoded 2-3% slower, within the variation of fifteen rounds.
- **The Studio's current route now pins this 262K v0.1.42 profile.** The new route's own ledger records two G23
  passes; the qualified 0.1.41 route stays with the PRO's 131K rollback profile (2026-10-12 update above).

## Update, 2026-10-11: the pair with the display on the RTX 3090 qualifies (predecessor)

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889))

- **The owner qualified the pair's pipeline-windows profile.** Its ledger has 21 pass and 3 not applicable (G22
  images, G23 remote clients and G25 runtime comparison, which compares single-GPU profiles only), and
  `verify_release.py --require-ready` passes. Ledger:
  [RTX 4090 + RTX 3090](../releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9/qualification.json).
- **Stock layer split, plus stock's pipeline windows 2.** Stock Strata v0.1.42 with stock OMP 18.8.9 runs
  Qwen3.8-Flash-Next IQ3_S at 131,072 tokens across both cards (`--gpus all`, `--layer-split auto`,
  `--pipeline-windows 2`; profile field `strata.pipeline_windows`), without batch slots. The RTX 4090 (GPU 0) runs
  layers 0-31; the desktop-driving RTX 3090 (GPU 1) runs layers 32-47 and the head. The 2026-10-10 measurements
  found pipeline windows 2 decoding 9-13% faster than the plain split, with prefill unchanged.
- **Every measured gate passed on its first run.** G10-G21, G24 and G26 passed in one requalify run on a fresh
  root (2026-10-11, 01:01-01:56Z), with model shards linked from the measurement root; this was G26's second root.
  G10 and G20 record both cards completely, and `start` passed its check for stock's decode-capable pipeline line.
- **The scored coding evaluation matches the RTX 3090 alone's first IQ3_S ledger:** 15/18, with tool-loop 0/3
  as on that Strata v0.1.31 ledger. The non-scored pilot was 6/6. Qualification is about integration correctness,
  not task quality; all attempts and their failures count.
- **At that qualification there was no earlier two-card rollback.** The qualified single-card RTX 3090
  profiles name GPU 0, now the RTX 4090; single-card `start` checks only that GPU 0 is free and would run there,
  although `doctor` reports the model mismatch. Those profiles stay qualified for an RTX 3090 host with one card.
  The pair's Coder IQ1_M, IQ3_XXS, plain IQ3_S and calibrated slots4-tips profiles stay drafts.

## Update, 2026-10-10: the RTX PRO 6000 qualifies at 262K context

<details>
<summary>2026-10-10 decision details (Strata v0.1.41 + OMP 18.8.6 on RTX PRO 6000 at 262K)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-at-262k-every-gate-2026-10-10-stock-strata-v0141-stock-omp-1886))

- **The owner qualified the 262K RTX PRO 6000 profile.** Its ledger has 21 pass and 3 not applicable (G22, G23 and
  G25, with their capabilities or claims off), and `verify_release.py --require-ready` passes. Ledger:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json).
- **Only the context changes.** Stock setup's plan at 262,144 tokens, the model's trained context, sets
  `--max-context 262144` and keeps KV streaming, four batch slots, parking and 32K prompt chunks; OMP is given
  261,120 tokens and the RAM floor at start rises from 72 to 74 GiB. The 131K profile with the same tuple is its
  rollback.
- **G18 first failed on a fixture sized for 131K windows.** Its production long session was a fixed 20 documents,
  which peaked at 162,071 tokens, under this window's 221,952-token compaction threshold, so OMP never compacted.
  The gate fixtures now follow the profile's window; the rerun passed G17 (a 211,806-token session) and G18
  (compaction at 222,868 tokens), and the failure stays in the ledger. Every other gate passed on the first run.
- **The coding evaluation is at least the 131K profile's:** pilot 5/6 and scored 17/18 (15/18 on the 131K profile),
  with the tool-loop task at 2/3. Qualification is about integration correctness, not task quality.
- **The 0.1.41 Mac client route remains qualified for the 131K rollback profile.** The Studio's current route
  has its own ledger and two G23 passes for the current 262K v0.1.42 profile (2026-10-12 update above).

</details>

## Update, 2026-10-09: on Terminal-Bench the PRO's Strata v0.1.41 profile passes 23 of 30

<details>
<summary>2026-10-09 decision details (PRO Terminal-Bench 23/30 on Strata v0.1.41 + OMP 18.8.6)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-08-stock-strata-v0141-stock-omp-1886))

- **Four more than the 18.8.3 profile and none fewer.** On the same 30 Terminal-Bench 2.1 tasks, one attempt each,
  the current PRO profile passed 23 against 19 (21 against 17 on the earlier 28): both passed 19 and only this
  profile passed 4 (exact McNemar p = 0.125), at a median 1.04x the agent time on the 19 both passed. Strata
  (v0.1.40.3 to v0.1.41) and the harness's OMP (18.8.3 to 18.8.6) changed together, so neither takes the credit alone.
- **It meets the bar set beforehand for an improvement claim** (four more of 30 at no more than twice the agent
  time), but on one attempt the difference is not significant. It is no regression: every trial has a verdict, and
  the failures are four agent time limits, all of which also timed out before, and three wrong or incomplete results.
- **The profiles do not change.** The v0.1.41 profile stays current; qualification is about integration
  correctness, not task quality.

</details>

## Update, 2026-10-09: the RTX PRO 6000 is qualified for remote use from a Mac

<details>
<summary>2026-10-09 decision details (first Mac Studio remote route to RTX PRO 6000, v0.1.41 + OMP 18.8.6)</summary>

([REMOTE.md](REMOTE.md))

- **The owner qualified the client route `client-rtxpro6000-strata0.1.41-omp18.8.6`.** Stock OMP 18.8.6 on a Mac
  Studio reaches the then-current 131K RTX PRO 6000 profile through an SSH local forward that the foreground
  `launch-omp` owns. This route remains qualified for that profile as a rollback.
  Its own ledger has G23 passing, and `verify_release.py --require-ready` passes.
- **What G23 covered:** a missing key refused before launch, a wrong key refused with 401, stream TTFT 0.19 s through
  the tunnel, a dropped tunnel failing only the turn in flight, and nonce recall after tunnel, client and server
  restarts. A plain `launch-omp` turn from the Mac answered as instructed.
- **The GPU is still shared with another tenant on that host.** The operator stops it before `start` and restores
  it after `stop`; the integration's exclusive-GPU check is unchanged. The route qualifies neither a fleet nor another
  client platform, and the retired RTX 4090 route drafts are gone.

</details>

## Update, 2026-10-09: Strata v0.1.41 with OMP 18.8.6 qualifies on the RTX 5090

<details>
<summary>2026-10-09 decision details (Strata v0.1.41 + OMP 18.8.6 on RTX 5090)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-5090-every-gate-2026-10-09-stock-strata-v0141-stock-omp-1886))

- **The owner qualified the RTX 5090 profile.** Its ledger has 21 pass and 3 not applicable (G22, G23 and G25, with
  their capabilities or claims off), and `verify_release.py --require-ready` passes. Ledger:
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.41-omp18.8.6/qualification.json).
- **Only Strata and OMP change.** The Coder IQ1_M pins, the llama.cpp archive, the Python lock and the stock setup
  plan are the 18.8.4 profile's, which is now its rollback, with the fourth tuple before it.
- **The coding evaluation is within one attempt of the 18.8.4 profile:** pilot 6/6 (5/6 before) and scored 15/18
  (16/18 before), with the tool-loop task at 1/3 on both and one multifile-regression attempt failing.
  Qualification is about integration correctness, not task quality.
- **Speed and resources are unchanged:** readiness 11.7 s, 105K-token cold prefill 14.5 s, GPU peak 30,836 MiB.
- **The RTX 3090 stays on Strata v0.1.40.3 with OMP 18.8.4;** this tuple's profile for it is a draft with no runs.

</details>

## Update, 2026-10-08 (night): Strata v0.1.41 with OMP 18.8.6 qualifies on the RTX PRO 6000

<details>
<summary>2026-10-08 (night) decision details (Strata v0.1.41 + OMP 18.8.6 on RTX PRO 6000 at 131K)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-08-stock-strata-v0141-stock-omp-1886))

- **The owner qualified the RTX PRO 6000 profile.** Its ledger has 21 pass and 3 not applicable (G22, G23 and G25,
  with their capabilities or claims off), every measured gate passed on its first run, and
  `verify_release.py --require-ready` passes. Ledger:
  [RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json).
- **Strata and OMP both change; the PRO's choices do not.** It keeps IQ3_S, four batch slots, parking and 32K prompt
  chunks, and the stock setup plan is the 18.8.4 profile's, including `--parallel 4` and both stock
  recommendations. The 18.8.4 profile is its rollback, with the 18.8.3 and v0.1.40.2 profiles before it.
- **The coding evaluation matches the 18.8.4 profile:** pilot 5/6 and scored 15/18, with the tool-loop task failing
  all three scored attempts on both. Qualification is about integration correctness, not task quality.
- **The RTX 5090 and RTX 3090 stay on Strata v0.1.40.3 with OMP 18.8.4.** The tuple's profiles for them are drafts
  with no runs; every gate in their ledgers is not run.

</details>

## Update, 2026-10-08: Strata v0.1.40.3 with OMP 18.8.4 qualifies on the RTX PRO 6000, RTX 5090 and RTX 3090

<details>
<summary>2026-10-08 decision details (Strata v0.1.40.3 + OMP 18.8.4 on RTX PRO 6000, RTX 5090 and RTX 3090)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#three-gpus-every-gate-2026-10-08-stock-strata-v01403-stock-omp-1884))

- **The owner qualified all three profiles.** Each ledger has 21 pass and 3 not applicable (G22, G23 and G25, with
  their capabilities or claims off), and `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json),
  [RTX 3090](../releases/win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json).
- **On the PRO only OMP changes.** The stock setup plan is the 18.8.3 profile's, including `--parallel 4` and both
  stock recommendations. The 18.8.3 profile is its rollback, with the v0.1.40.2 profile before it.
- **The RTX 5090 and RTX 3090 move from the fourth tuple to the current one,** with the same Coder IQ1_M at
  131,072 tokens. The fourth tuple's profiles stay qualified as their rollbacks and as the RTX 4090's record.
- **One gate needed a rerun on the PRO.** G16's predicate counted mentions of `append.py`, not its runs. After the
  fix (`2c32e2b`) the rerun passed; the failed receipt stays in the ledger.
- **The coding evaluation is within one attempt of the predecessors:** 15 of 18 on the PRO (16 on 18.8.3; the
  tool-heavy task 0/3 against 1/3), 16 on the RTX 5090 and 15 on the RTX 3090 (as on the fourth tuple).
  Qualification is about integration correctness, not task quality.

</details>

## Update, 2026-10-07 (evening): the RTX PRO 6000 qualifies with batch slots and conversation parking

<details>
<summary>2026-10-07 (evening) decision details (RTX PRO 6000 with batch slots and parking, v0.1.40.3 + OMP 18.8.3)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-with-batch-slots-and-parking-every-gate-2026-10-07-stock-strata-v01403-stock-omp-1883))

- **Strata v0.1.40.3 with OMP 18.8.3 qualifies on the RTX PRO 6000, with three stock setup choices pinned.**
  `--parallel 4` is stock's recommendation for this card: up to four requests decode together, and OMP may send the
  server four at once. `--conversation-cache-mib 8192` parks up to four conversations in host RAM.
  `--prefill auto:32768` reads prompts in 32K chunks. Every applicable gate passed at the first attempt (21 pass;
  G22, G23 and G25 not applicable);
  [ledger](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3/qualification.json).
- **What it buys, measured.** Four overlapping requests decode 19% faster in total, and each slot's tokens equal
  its solo run. A conversation interleaved with another comes back from its parked or held state instead of being
  read again (G19: 20,669 of 20,698 tokens reused, 0.34 s instead of 3.3 s). Long prompts read 8-24% faster (G17).
  The coding evaluation is unchanged at 16 of 18.
- **What it costs.** 2.9 GB more VRAM in use, 11 GB more engine commit (the parking budget and the slots), and 2 s
  more to readiness. A request alone gains nothing from the slots.
- **Terminal-Bench: 19 of 30 on this profile,** with the OMP 18.8.3 harness (17 of the earlier 28). The earlier PRO
  runs used OMP 18.5.0, so they are context, not a paired comparison: v0.1.40.1 passed 21 (exact McNemar p = 0.73)
  and v0.1.39 19. Trials ran one at a time, so the slots stayed idle. Qualification is about integration
  correctness, not task quality.
- **The v0.1.40.2 profile stays qualified,** and its root is the rollback installation.

</details>

## Update, 2026-10-07 (later): the RTX PRO 6000 tuple qualifies, with OMP's speculative compaction off

<details>
<summary>2026-10-07 (later) decision details (RTX PRO 6000 on v0.1.40.2 + OMP 18.8.0, speculative compaction off)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-07-stock-strata-v01402-stock-omp-1880))

- **Strata v0.1.40.2 with OMP 18.8.0 qualifies on the RTX PRO 6000.** The owner's rule for a qualification is the
  newest stable release of both components. Every applicable gate passed at the first attempt: 21 pass, and G22,
  G23 and G25 are not applicable. The profile serves IQ3_S at 131,072 tokens with every expert in VRAM;
  [ledger](../releases/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0/qualification.json).
- **The integration turns OMP's speculative compaction off.** Near its compaction threshold OMP 18.8.0 sent the
  engine a background summary. With one sequence and one in-flight request, that held the next turn for 17 s and
  evicted the 105K-token live prefix. The owner held the profile as a candidate until it was fixed. The rendered
  settings now set `compaction.asyncEnabled: false` (OMP still compacts at the threshold), and a host-free test fails
  if the speculation reaches the engine. G17, G18 and G24 then passed again on the PRO, and the near-limit session
  took 20.7 s instead of 50.7 s.
- **Terminal-Bench has not measured this pair.** Its 20 of 28 belongs to Strata v0.1.40.1 with OMP 18.5.0, the
  result that made IQ3_S on v0.1.40.x the PRO's candidate. Qualification is about integration correctness, not task
  quality.
- **The earlier PRO drafts keep their ledgers, with no gate run;** the installed v0.1.39 and v0.1.40.1 roots remain as
  rollback installations.

</details>

## Update, 2026-10-07: on Terminal-Bench the largest stock build ties IQ3_S; IQ3_S stays the PRO's model

<details>
<summary>2026-10-07 decision details (UD-Q4_K_XL vs IQ3_S on Terminal-Bench, drafts only)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-against-the-rtx-4090-2026-10-06-stock-strata-v0139-stock-omp-1850))
Drafts only: no gate ran.

- **UD-Q4_K_XL's higher fidelity bought no task quality.** On 30 Terminal-Bench 2.1 tasks, one attempt each, both
  builds passed 19, and each passed 3 that the other failed. The bar set beforehand for replacing IQ3_S was 4 more
  tasks, so IQ3_S stays and its prompt-speed lead decides.
- **One failure class has two causes, each fixed upstream.** In 3 of the 22 failures (2 with IQ3_S, 1 with
  UD-Q4_K_XL) the last turn ended its reasoning with a complete tool call that v0.1.39 returns as reasoning text. OMP
  retries such a stop, but 18.5.0 drops the retry once the run has restarted, as all three had, so they ended
  mid-task. Strata v0.1.40 and v0.1.40.1 turn such a call into a real one, and OMP 18.5.1 keeps the retry; neither has
  been measured on these tasks.
- **Two tasks fail for any model that leaves its server to OMP.** The benchmark harness runs `omp --print`, and OMP's
  service broker stops its services 3 s after omp exits, before the task's checks connect. Absolute scores here
  understate the model; the paired comparison is unaffected. Stock `OMP_DAEMON_IDLE_GRACE_MS` lengthens that grace
  (scripted check), so a harness can keep the services for every arm without changing what the model sees.

</details>

## Update, 2026-10-06 (later): IQ3_S stays the PRO's model; the largest stock build costs prompt speed

<details>
<summary>2026-10-06 (later) decision details (IQ3_S vs UD-Q4_K_XL on RTX PRO 6000, drafts only)</summary>

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-against-the-rtx-4090-2026-10-06-stock-strata-v0139-stock-omp-1850))
Drafts only: no gate ran.

- **IQ3_S on the PRO passed 55 of the 60 private tasks**, three of its misses 0.99 near-passes, in 0.39x the
  4090's time. It remains the PRO's model.
- **Stock UD-Q4_K_XL fits the PRO's VRAM** (all experts resident) and decodes at 0.85-0.90x IQ3_S. Its prefill is
  0.43-0.73x, so an agent turn on a long cached prompt takes about twice as long (3.1 s against 1.4 s). Whether its
  higher fidelity buys task quality is being measured on a harder, public task set before any profile change.
- **Larger open models that do not fit 96 GB of VRAM are not practical on one card here.** Comparison-only
  llama.cpp runs that spilled experts into system RAM decoded at 10-17 tokens/s, bound by CPU-side expert work.

</details>

## Update, 2026-10-06: an RTX PRO 6000 runs IQ3_S 2.2-2.3x faster than the RTX 4090, every expert in VRAM

<details>
<summary>2026-10-06 decision details (RTX PRO 6000 vs RTX 4090 on IQ3_S, draft only)</summary>

The RTX PRO 6000 replaced the RTX 4090 in its host and ran the same IQ3_S model on Strata v0.1.39
([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-against-the-rtx-4090-2026-10-06-stock-strata-v0139-stock-omp-1850)).
Draft only: no gate ran.

- **IQ3_S belongs on the PRO.** Decode 258-271 tokens/s at 8K-100K against 115-116, prefill 1.6-1.9x, and time to
  first token at 100K 13.6 s against 25.3 s, with all 24,576 experts in VRAM where the 4090 fetched its cache misses
  over PCIe. It passed all 12 screen tasks (10 on the 4090), one attempt each; the 60-task run comes next.
- **Keep the stock flags.** Stock setup plans the 4090's flags for 96 GB, and `--expert-cache auto` already makes
  every expert resident; about 40 GB stays free for longer contexts or a second model, which would be a new profile.
- **The card's host requirements are firmware, not tuning:** Re-Size BAR off for POST on this board, and the card's
  own power adapter. Sustained agent work held about 450 W and 79 °C on the core with no slowdown.

</details>

## Update, 2026-10-05: Strata v0.1.39 decodes faster on the RTX 3090; its hybrid-CPU change shows no clear gain

<details>
<summary>2026-10-05 decision details (Strata v0.1.39 vs v0.1.38 on RTX 3090 and RTX 4090, drafts only)</summary>

Strata v0.1.39 with stock OMP 18.5.0 ran beside v0.1.38 on the RTX 3090 and the RTX 4090, same model files, versions
alternating on each card ([MEASUREMENTS.md](MEASUREMENTS.md#strata-v0139-against-v0138-2026-10-05-stock-omp-1850)).
Drafts only: no gate ran.

- **Use v0.1.39 for the next Strata profiles.** On the RTX 3090 it decodes 3-7% (IQ3_S) and 5-10% (Coder) faster
  than v0.1.38 at 8K-100K tokens, with the same flags; prefill is unchanged. On agent work the Coder kept its
  outcomes (42/44 base tasks against 43/44) and took a median 0.84× the time on the tasks both passed; IQ3_S passed
  10 of the 12 screen tasks against 11, within the hard tier's attempt-to-attempt flips.
- **Stock's new `--pool-workers 15` for the RTX 4090 host's hybrid i9-14900K brought 2-4%, within run-to-run
  spread**, not the large gain upstream measured on an i9-14900KF. The profile pins stock's value; no hand tuning.

</details>

## Update, 2026-10-04: on the owner's kind of work, Flash-Next beats the 27B

<details>
<summary>2026-10-04 decision details (private 60-task evaluation: IQ3_S, Coder IQ1_M and NInfer 27B)</summary>

The frozen evaluation cannot rank models: five of its six tasks pass for every model and the sixth fails for every
one. A private 60-task set shaped like the owner's local work now informs model choice: development in a private
TypeScript monorepo, and analysis, spreadsheets, repair, statement programs and judgment over synthetic financial
documents, one attempt per model and task
([MEASUREMENTS.md](MEASUREMENTS.md#the-models-on-the-owners-kind-of-work-2026-10-04-a-private-60-task-set)). It is
comparison evidence only; no gate or ledger changes.

- **The original Flash-Next at IQ3_S is the strongest local model: 58/60**, against 54/60 for the Coder IQ1_M and
  49/60 for Qwen3.8 27B on NInfer. It passed every task the 27B passed and nine more (exact McNemar p = 0.004);
  its lead over the Coder (5 to 1) is within chance at this size.
- **Run IQ3_S, not the Coder, wherever the RAM holds it, coding included.** "For coding the Coder stays the choice"
  (2026-10-02) rested on the frozen evaluation's tie; here IQ3_S passed all 26 development tasks against the
  Coder's 23. The RTX 4090 with 192 GB ran it; the RTX 3090's calibrated 128 GB draft is the same model, not
  measured on this set. It is the slowest arm: on the RTX 4090, a median 1.5-1.9× the 27B's RTX 5090 time.
- **On the RTX 5090, whose 47 GiB cannot hold IQ3_S, the Coder on Strata leads the 27B on NInfer for agent work,
  though not significantly.** Over two attempts of every task (the second all on that GPU; the Coder's first base
  attempts ran on the RTX 3090) it passed 107 of 120 against 99: better on 11 tasks, worse on 5 (sign test p = 0.21;
  mean pass rate 89% against 83%, task-bootstrap 95% interval -0.8 to +14 points), in a median 0.90× of the 27B's
  time per task on the RTX 5090. Each model's two attempts disagree on 9-11 of the 60 tasks. The 27B's malformed tool
  calls returned as text (four of 29 hard attempts in the first round) did not recur in its second; three of the
  Coder's 120 attempts ended in OMP's thinking-loop detector. The 2026-10-03 "keep NInfer" rested on the frozen
  evaluation; switching the production lane is the owner's decision, and NInfer still restores saved sessions after a
  restart where Strata re-reads the transcript.
- **A lead with subagents does not pay off on this work.** Neither lead delegates on its own, with stock prompts or
  when its system prompt says to. Asked in every request to use its subagents, the Coder lead on the RTX 5090
  delegated in 12 of 13 hard tasks, mostly read-only `scout` runs on the RTX 3090, and passed 7 against the 8 it
  passed alone, taking a median 1.54× as long. Run single-model sessions, and ask for subagents in a request only
  when the work splits into independent pieces.

</details>

## Update, 2026-10-03: Strata against NInfer — keep NInfer, switch nothing

<details>
<summary>2026-10-03 decision details (G25 paired comparison against NInfer and durability review)</summary>

The first real G25 runs put the fifth-tuple drafts (stock Strata v0.1.38, stock OMP 18.5.0, Coder IQ1_M 131K)
against what each host already runs, through the same frozen evaluation and one pinned OMP binary
([MEASUREMENTS.md](MEASUREMENTS.md#paired-coding-evaluation-against-ninfer-g25)):

- **RTX 5090: keep omp-ninfer v0.10.0.** Strata 15/18, NInfer 14/18, but NInfer was faster: Strata's paired median
  task took 1.39× NInfer's and its summed wall 839 s against 733 s. NInfer decodes faster at the tasks' contexts;
  Strata's 3× faster long-prompt reading and 2.4× faster restart do not make up for it here.
- **RTX 3090: no reason to switch.** 15/18 each with the same three tool-loop failures, paired median ratio 0.98,
  summed wall 1,905 s against 2,028 s. Strata restarts in 25 s against 114 s and reads a 100K prompt in 41 s against
  160 s; NInfer brings saved sessions back after a restart. The RTX 3090 serves no fleet route.
- **RTX 4090 with 192 GB: no reason to switch.** After a memory fix (DDR5-5200 with Intel's default CPU power
  settings; DDR5-5600 failed under load), the Coder against the host's native NInfer v0.6.10 lane: 15/18 each with
  the same three tool-loop failures, paired median ratio 0.98, summed wall 1,133 s against 1,231 s. Strata reads a
  100K prompt in 19 s against 62 s and restarts in 15-18 s against 34-75 s. Unlike on the other hosts, stock
  calibration keeps a lower PCIe share here, worth up to 13% decode (one probe each): the best measured settings are
  calibrated IQ3_XXS (stock setup's model choice, 164-174 tokens/s) for decode, the calibrated Coder for long
  prompts and coding, and the Coder 262K beyond 131K tokens (no cost below 100K). A decode up to 13% faster would
  not bring the 0.98 ratio near the 0.80 that "faster" requires (an estimate; the comparison was not rerun
  calibrated).

Neither frozen claim, more completions or faster joint successes, holds on any GPU, so the condition for
switching a host to Strata (clearly better) is not met.

**Durability: do not port NInfer's.** Stock Strata v0.1.38 already has a native prompt cache, an engine-silence
watchdog and opt-in RAM conversation parking (`--conversation-cache-mib`, `--conversation-cache-slots`: alternating
conversations keep their KV in a bounded host-RAM cache), which covers what NInfer's host KV pool does for one user.
It has no disk-persisted sessions, no Responses `previous_response_id`, and runs one sequence at a time. Porting
NInfer's disk checkpoints would be a large change and would need AGENTS.md's no-durable-engine-state boundary
lifted; with cold restarts of 14-26 s and a 100K re-read of 14 s (RTX 5090) to 41 s (RTX 3090), section 3's
conclusion stands. If parking is wanted, it is a stock flag: a new profile id, not a port.

</details>

## Update, 2026-10-03: the fourth tuple qualifies on three GPUs

<details>
<summary>2026-10-03 decision details (fourth tuple qualification on RTX 5090, RTX 3090 and RTX 4090 low-RAM)</summary>

All 21 applicable gates pass in each fourth-tuple ledger; G22 (images), G23 (remote clients) and G25 (runtime
comparison) are not applicable to these local, text-only profiles. Evidence and scrubbed results:
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
[RTX 3090](../releases/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
[RTX 4090, low-RAM](../releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10/qualification.json);
figures and measurement boundaries in [MEASUREMENTS.md](MEASUREMENTS.md).

- **G04 passes for the first time on all three GPUs' profiles.** Stock Strata v0.1.34 includes the unfinished-call
  fix shipped in v0.1.31; stock OMP 18.4.10 includes its corresponding fix. A call cut off mid-arguments is refused,
  not executed with partial arguments. No fork or locally patched binary is needed.
- **G15's failures remain recorded, and its probe correction is explicit.** The RTX 5090 failed
  `g15-20261002T025312Z-8c4047` and `g15-20261002T032432Z-3a4126` with the earlier probe. Commit `cb31418`
  changes the recall prompt after interruption to withdraw the interrupted essay first (`RECALL_AFTER_INTERRUPT`);
  it changes neither the engine nor the requirement to recall the transcript's fact on the next turn. The corrected
  probe passed as `g15-20261003T032448Z-de222a`, published on 2026-10-03. The RTX 4090 had already passed and
  passed the corrected repeat, `g15-20261003T032520Z-78f0cc`. The RTX 3090's earlier probe failed once and then
  passed `g15-20261002T032128Z-191f17`; its corrected repeat passed as `g15-20261003T043756Z-122117`. None of this
  is durable engine-state restoration: a restart replays the transcript and cold-prefills it.
- **The RTX 4090's compaction rerun is not a clean first pass.** Its reduced-threshold G18 probe failed once;
  the repeat passed. Both the failed combined receipt `g18l-20261002T023456Z-79336a` and passing
  `g18l-20261002T030838Z-c64d0c` stay in the ledger. Production long-session compaction itself passed both runs.
- **Integration qualification is not a perfect coding score.** The frozen evaluation verified 16/18 attempts on
  the RTX 5090 and 15/18 on each 24 GB GPU. The tool-heavy task scored 1/3, 0/3 and 0/3 respectively; every other
  task scored 3/3. G24 requires complete, independently verified reporting, with failed tasks in the denominator,
  not quality superiority. The RTX 4090's 32 GiB low-RAM fit leaves just 0.44 GB available at its worst sample;
  qualification is for that tested configuration, not a claim of capacity for other workloads.
- **Use the fourth tuple; retain the earlier installations for rollback.** The first and second RTX 5090
  candidates and third-tuple 24 GB profiles keep their original, unqualified ledgers and roots. Fifth-tuple drafts,
  larger-model/context variants and remote-client routes gain no qualification from this result. Durable state,
  multi-tenancy and comparison with other runtimes remain outside this decision.

</details>

## Update, 2026-10-03: Strata's own calibration changes nothing for the Coder

<details>
<summary>2026-10-03 decision details (stock calibration on RTX 5090, RTX 4090 low-RAM and RTX 3090)</summary>

Stock setup ends an interactive install by offering its calibration (`tools/calibrate.py`, default yes); `--yes`
installs and the guarded install skip it, so every earlier measurement ran with the engine's defaults. Run unchanged
on each installed root, the stock tool keeps every default for the Coder on the RTX 5090, the RTX 4090 (low-RAM)
and the RTX 3090: the qualified profiles already are Strata's calibrated configuration. Only IQ3_S on the RTX
3090's Gen3 x8 link keeps `--pcie-frac 0.20 --spec-min-p 0.70`. Pinned as a draft and measured beside the
uncalibrated root, it decodes 4-5% faster up to 8K tokens, no faster from 32K, and scores the same 15/18, so the
IQ3_S configuration for work outside coding is the calibrated draft. Profiles may now pin such a stock result
(`strata.calibration`, a new profile id that install applies with stock `calibrate.apply`); setup never calibrates
on its own. Evidence: `docs/MEASUREMENTS.md`.

</details>

## Update, 2026-10-03: longer contexts for the Coder on the RTX 3090

<details>
<summary>2026-10-03 decision details (262K and 524K long-context drafts on 128 GB RTX 3090)</summary>

The Coder's trained 262K context is the long-context configuration to use on the 128 GB RTX 3090: it decodes as at
131K up to 100K tokens, 81-89 tokens/s at 200K-250K, and a cold 250K-token prompt takes 2.3 min. Stock setup's
experimental yarn scaling to 524K also runs (a cold 512,000-token prompt: 6.7 min, then 72 tokens/s) at 3-5% lower
decode below 100K, but it changes the model at every position and its coding evaluation is still owed, so it stays
a draft for work that needs more than 262K. Evidence: `docs/MEASUREMENTS.md`.

</details>

The two updates and original three-part assessment below are retained as dated 2026-09-30 / 2026-10-01 history, not
today's verdict or blocker list.

## Update, 2026-10-02: which model the RTX 3090 should run with 128 GB

<details>
<summary>2026-10-02 decision details (128 GB RTX 3090 model selection, drafts only)</summary>

After its RAM upgrade (128 GB of DDR4-3200) the RTX 3090 ran three models with stock Strata v0.1.36 and stock OMP
18.4.12 as draft profiles, measured for variant selection only (`scripts/perf_probe.py` and the frozen evaluation;
no gate ran, every ledger stays draft): the Coder IQ1_M, the original model's IQ3_S, and Unsloth's experimental
UD-Q4_K_XL with every expert in RAM. Evidence: `docs/MEASUREMENTS.md`.

- **The most capable model the RAM unlocks is the original Flash-Next at IQ3_S**, which Strata's notes say matches
  the full BF16 model. It now decodes 93-96 tokens/s (56-66 at 64 GiB), within 10% of the Coder, because stock setup
  streams its KV cache to RAM; prefill stays at half the Coder's (88 s against 43 s for a 100K-token prompt).
- **For coding the Coder stays the choice.** On the frozen evaluation IQ3_S scores the Coder's 15/18 and fails the
  same exact-money assertion, with a 29% longer median task. Candidate profiles keep the Coder IQ1_M; the IQ3_S
  drafts are the configuration to use when work outside coding matters. Its 262K draft (the model's trained
  context) still decodes 84 tokens/s at 250K tokens; a cold 256K-token prompt takes about 4 min.
- **UD-Q4_K_XL is not worth running on this host.** It runs at half IQ3_S's speed, restarts in 2-2.5 min (past the
  frozen evaluation's 120 s restart hook, which ended its batch), and gained nothing on the tasks it completed.
- **More RAM leaves the Coder unchanged**: the same flags, and a 100K-token cold prefill within 2% (43.2 s against
  44.0 s).

</details>

## Update, later on 2026-10-01: the third tuple on two 24 GB hosts

<details>
<summary>2026-10-01 (later) decision details (third tuple drafts on RTX 3090 and RTX 4090)</summary>

Stock Strata v0.1.31 and stock OMP 18.4.8 ran the complete real-host sequence on an RTX 3090 host with 64 GiB of
RAM and on an RTX 4090 host with 32 GiB of RAM (stock low-RAM mode), as draft profiles in fresh roots, without
touching the RTX 5090 or its other tenant. Evidence: `releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/`,
`releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/` and `docs/MEASUREMENTS.md`. The decisions
below stand for the RTX 5090 candidate; this update changes what blocks qualification and where the route can run.

- **G04 is the only failing gate on both hosts, and now only OMP's half is open.** Strata v0.1.31 no longer
  presents an unfinished call as complete (Strata#231); stock OMP 18.4.8 still runs it. A binary built from
  can1357/oh-my-pi#13868's head answers it with an error result and writes nothing; #13868 was merged on
  2026-10-01, after OMP 18.4.9 was published, so no release carries it yet. The suite now holds a cut-off call to
  the contract it already applied to a length cut: the call never runs, and the client may fail the turn or answer
  with an error. An OMP release carrying that fix will turn the composed reproducer into an unexpected success;
  qualification then needs that release in a profile and a host-free G04 run, plus the real-host gates on
  whichever host the profile names.
- **Every other gate passes on both hosts.** Evaluation 17/18 on the RTX 3090 and 15/18 on the RTX 4090 (the
  tool-heavy task 2/3 and 1/3; 4 of 12 across the four scored batches of this model). Decode runs at 79-113 tokens/s
  (RTX 3090) and 104-126 tokens/s (RTX 4090) against 148-206 on the RTX 5090; a 100K-token cold prefill takes 44 s
  and 21 s against 16 s.
- **The route no longer needs the RTX 5090.** Its costs move to the choice of host: slower prefill on the RTX 3090
  (PCIe Gen3 x8), and on the 32 GiB RTX 4090 almost no RAM reserve (0.37 GB available at the worst sample). Both
  hosts are getting more RAM (128 GB and 192 GB); the RTX 4090's low-RAM-off profile
  (`win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8`) is ready for that, and the RTX 3090 profile is unchanged
  by it (its setup choices do not depend on RAM above 35 GiB). Which host the route should live on is the owner's
  choice; until then the RTX 5090 profile stays the current candidate.
- **The larger original model does not fix the task the Coder fails.** An exploratory run of Strata's
  best-quality size of the original Flash-Next (IQ3_S) on the RTX 3090 scored 15/18 with the tool-heavy task
  0/3, every attempt on the same exact-money assertion, at about half the Coder's speed and with 0.72 GB of commit
  to spare on 64 GiB. Every candidate profile keeps the Coder IQ1_M.

</details>

> **Historical baseline assessment (2026-09-30 / 2026-10-01):** Sections 1–3 below record the original assessment of
> the second RTX 5090 candidate (`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`, Strata v0.1.30 + OMP
> 18.4.6) on 2026-10-01, before G04 was resolved upstream and qualified in the fourth tuple on 2026-10-03. They are
> preserved as the baseline record; for today's qualified profiles and boundaries, see the summary at the top of
> this document.

## 1. Integration readiness: working candidate, one upstream blocker left

<details>
<summary>Original 2026-10-01 assessment of section 1 (Strata v0.1.30 + OMP 18.4.6, when G04 was still open)</summary>

**Passed.** These capabilities are supported within the limits stated. The last row is host-free; every other row
ran on the real host on 2026-10-01.

| Gate | Result |
|---|---|
| G10 | Pinned identity on the actual host (deep re-hash of every artifact), and exclusive GPU use |
| G11 | Typed read/glob/edit/bash tool loops through the real stock client: 3/3 tracer runs |
| G12 | Live prefix reuse inside a session: 12/12 continuations |
| G13 | Loopback only, with authentication on every model and control route including `/status`. The launcher fails closed on a missing key. All model roles, including compaction, route locally; 0 non-loopback events with the guard. |
| G14 | Cancellation while generating, while queued, failed tools and transport loss: the next turn is valid. **The queued-cancel engine crash of the first candidate is fixed** (Strata v0.1.28+; `g14q` passes 3/3 scenarios). |
| G15, G16 | Continuing after an engine, client or full server restart from OMP's own transcript: replay with a full re-prefill, never state restoration |
| G17 | The 131,072 window: exact server limit, near-limit tool turns, explicit overflow |
| G18 | OMP compaction at a reduced threshold, and at the production threshold in a long session |
| G19 | Interleaved sessions, resume and branch |
| G20 | Controlled lifecycle with no orphans, the first candidate's root and the host's unrelated state preserved |
| G21 | A measured resource fit: no watchdog stop, OOM or CUDA error in 521 logged requests |
| G26 | Every `docs/QUICKSTART.md` command into a second root, the documented `launch-omp` example included; 15 of 17 generated files byte-identical to the first root, only the engine differs |
| G00–G03, G05, G06 | Source audit, pins, client isolation, real OMP 18.4.6 against scripted streams and the real v0.1.30 frontend, lifecycle edge cases, public CI |

**Failed, release-blocking (upstream defect; details in `docs/UPSTREAM.md`).**

- **G04.** When the model's turn ends inside a tool call, Strata v0.1.30 still reports `tool_calls` with closed
  partial arguments, and OMP 18.4.6 still executes the truncated call: a partial file write happens and the run
  exits 0. No supported setting avoids it. Fixes are proposed for both halves (Strata#231, planned by the
  maintainer for v0.1.31; can1357/oh-my-pi#13868, open).

**Still worked around in this integration.**

- Stock OMP fetches its public model catalog at every start. The launcher's proxy guard stopped this in
  observation (first candidate, unguarded trace), but it is not enforcement.
- The declared window stays 1,024 tokens below the engine's. OMP 18.4.4+ has its own 64-token headway; the margin
  was kept rather than re-tested.

**Not supported.** Images (G22), remote clients (G23), comparative claims (G25), durable engine state and
multi-tenant use.

**Verdict.** The route works end to end for single-user local coding and is one upstream fix away from
qualification: G04 needs Strata#231 (or equivalent) **and** oh-my-pi#13868 (or equivalent) in stock releases,
then a third candidate with G04 requalified host-free and the affected real-host gates rerun. An explicit
acceptance of the truncated-tool-call risk by the owner would be the only other way to call it qualified.

</details>

## 2. Usefulness: keep as an optional local coding backend

<details>
<summary>Original 2026-10-01 assessment of section 2 (usefulness and single-card RTX 5090 costs)</summary>

- **Observed outcome.** 15/18 verified passes on the bounded six-task evaluation: five tasks 3/3, the tool-heavy
  settlement task 0/3 (every attempt passed the visible tests and failed the same hidden test). The first
  candidate scored 16/18 with the same task at 1/3; with three attempts per task the difference is noise, not a
  regression signal. There were no protocol errors, timeouts or aborts. Median task wall time was 46 s, including
  tools and verification.
- **Why it is useful.** It covers bug fixes, a multi-file regression, retrieval from a large archive, and
  continuation across a client and server restart; it now also survives a cancelled queued request.
- **Costs** (unchanged in substance from the first candidate).
  - The RTX 5090 is fully occupied: 30,742-30,838 of 32,607 MiB of VRAM.
  - The engine holds about 30.5 GB of RAM resident at peak and commits about 63 GB, which needs a page file on a
    47 GiB host. About 8.5-9.7 GB of RAM stays available while serving.
  - 69 GB of disk per candidate root (the second root shares nothing with the first on disk; the shards were
    copied).
  - About 15 s to start or to restart the engine.
  - One engine serves one request at a time (FIFO).
  - Operationally: the G04 defect, the egress guard, and the need to release the GPU from any other tenant.
- **Recommendation.** Keep it as an optional backend for local, private, single-user coding sessions. Do not make
  it a default or a replacement for anything until G04 is fixed upstream. The evaluation is a small smoke of
  usefulness, not a benchmark. No quality threshold was set in advance, and none is claimed.

</details>

## 3. Further investment in engine-state durability: not justified now

<details>
<summary>Original 2026-10-01 assessment of section 3 (why durable engine-state restoration is not justified)</summary>

Restart pain was measured again and is unchanged:
- An engine reload takes about 14 s.
- Replaying a transcript costs a cold prefill at about 4K tokens/s for small prompts and 6.4K tokens/s at 100K
  tokens: about 2 s for a typical 7K-token coding session and about 16 s at the largest prompts that fit.
- Client restarts keep the live cache.
- Continuation after a full server restart passed 3/3 in the evaluation and in G16.

The one failure class left is an upstream protocol defect, not missing state. A durable engine-state design would
save at most those seconds per restart, at a large correctness and maintenance cost.

**Recommendation.** Do not start a durability subsystem. Spend the next effort on:
1. Landing the two G04 fixes upstream (Strata#231, oh-my-pi#13868) and the reproducible-setup fix (Strata#324).
2. A third candidate on the releases that carry them, requalifying G04 (host-free) and the affected real-host
   gates with the sequence in `docs/OPERATIONS.md` ("Requalifying a new tuple").
3. Asking OMP for an offline switch for the catalog refresh (can1357/oh-my-pi#10934).

Revisit durability only if real use shows long sessions restarting often enough for re-prefill time to matter.

</details>
