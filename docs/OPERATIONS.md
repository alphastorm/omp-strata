# Operations

OMP Strata runs stock Oh My Pi (OMP) against a stock, local Strata server from one self-contained integration root per
profile. Every command takes `--profile profiles\<profile_id>.json --root <root>` (omitted in the examples below).
There is no daemon: `start` launches a detached wrapper (`serve`), and the files under `<root>` are the whole state.

## Current profiles and rollbacks

| Host | Current qualified profile | Qualified rollback profile | Notes |
|---|---|---|---|
| RTX PRO 6000 (`rtxpro6000-win-a`) | `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` | `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` | IQ3_S at 262,144 tokens, 4 batch slots with per-slot stock DFlash2 drafters (`strata.drafting: "dflash2"`, one 85 MiB slot drafter per slot, `--spec 6`, no `--batch-mtp`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; rollback keeps per-slot MTP `--batch-mtp`), direct per-layer embedding (PLE) reads (`--ple-io direct`), KV in VRAM (`--kv-streaming off`, 78 GiB available-RAM start floor), stock `parallel_stack` + `gdn_stack` in `strata.engine_env`, conversation parking (8,192 MiB automatic cache), bare `--prefill auto` (32,768-token ceiling) |
| RTX 5090 (`rtx5090-win-a`, **default**) | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0` | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` | Coder IQ1_M at 262,144 tokens, KV in VRAM (`--kv-streaming off`), elastic KV growth (`--kv-grow`), stock `gdn_stack` in `strata.engine_env`; 34 GiB available-RAM start floor and 4,352 MiB automatic conversation cache; the host's Docker Desktop and WSL (which run its production NInfer container) must be stopped; after WSL restarts, that container must be recreated (owner's pinned relaunch) or returned through the owner's fleet controller |
| RTX 5090 (qualified alternative) | `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` | `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0` | Coder IQ1_M at 131,072 tokens; 34 GiB available-RAM start floor; starts with Docker Desktop and WSL running (production container stopped by the fleet controller); stays on v0.2.10 after the v0.2.11 131K draft failed G15 twice |
| RTX 4090 + RTX 3090 (`rtx3090-win-a`) | `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0` | `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0` | IQ3_S at 262,144 tokens, stock roles (RTX 4090 as Main), manual split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, 19.41 / 17.90 GiB expert caches on v0.2.11 `df2` vs 19.41 / 18.31 GiB on v0.2.10 `df2` rollback and 19.14 / 17.75 GiB on v0.2.10 `pw2` MTP alternative), stock DFlash2 drafter alone (`strata.drafting: "dflash2"`, `--draft dflash2 --draft-fallback none`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; drops `--pipeline-windows 2`), no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`), engine `sm_86` default table (`sm86_table`) + stock `gdn_stack` in `strata.engine_env`; engine's 8,192 MiB automatic conversation cache |

On the PRO (`rtxpro6000-win-a`), the current v0.2.11 profile (engine 0.1.57) pins `strata.ple_io: "direct"`
(`--ple-io direct`, [Stock PLE direct reads](#stock-ple-direct-reads), reading the 26.8 GiB PLE table from the model file
instead of locking it in RAM at start), `strata.drafting: "dflash2"` on all four batch slots
([UPSTREAM.md](UPSTREAM.md#stock-dflash2-batch-slot-arm-v0211--0157), giving each slot its own 85 MiB DFlash2 drafter
under `STRATA_BATCH_DF2`, `70.22 GiB` free at start, `--spec 6`, no `--batch-mtp`, packed offline from pinned
`incoai/Qwen3.8-Flash-Next-DFlash2` files with `STRATA_NO_ACQUIRE=1`; 93 GiB free-disk floor),
`setup_args.kv_streaming: "off"` (`--kv-streaming off`, keeping KV in VRAM and dropping `--kv-resident 32768`; 78 GiB
available-RAM start floor), `strata.engine_env` with stock `serve/server.py`'s Linux-only nine-switch parallel-slot
stack (`PARALLEL_STACK_ENV`) and two-switch GDN tensor-core prompt stack (`GDN_STACK_CUDA`;
[UPSTREAM.md](UPSTREAM.md#strata-v0211-setup-and-start-path-review-engine-0157)), and bare `--prefill auto` (engine
0.1.57's 32,768-token ceiling). In three paired cold starts against its v0.2.11 batch-MTP rollback
([measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160)), single-request decode rose +20-26%
(`1.201` at depth 0, `1.258` at 8K, `1.203` at 32K, `1.142` at 100K, `1.216` on warm 32K) with TTFT ~1.0, while 35 of
100 checks missed on concurrent short-request throughput/latency (`w2/c2` total `0.885` and per-request `0.794`, TPOT
`1.242`; `w2/c4` total `0.937`, TPOT `1.089`; latency +7-20%; `4 × 32K` `0.995`) and output-burst spacing (one-request
longest gap +12%, p95 inter-event gap +7-12%), which the owner overrode (`"Override: qualify DFlash2 as PRO current"`),
and its requalification chain at `b812df9` (`f3a8a77`, with an owner-approved complete G15 rerun at `b812df9` in
`637b616` after the initial G15's first post-kill recall wrote the interrupted 11,178-token essay) passed all 14
measured gates (G16/G20/G21 restart readiness 31.0 / 31.0 / 35.7 s, G15 rerun kill recall 29.2-29.3 s, G10 Windows
commit headroom 83.55 GiB `89,708,605,440 B` of a 219.70 GiB limit with 127.14 GiB available RAM and 73,496 MiB GPU
memory, 8,192 MiB automatic conversation cache with 32 parks in G19, G24 15/18, pilot 5/6, batch wall 627 s). Its
rollback is the qualified v0.2.11 batch-MTP profile
(`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`: `strata.batch_mtp:
true`, `--batch-mtp`, [Stock per-slot MTP](#stock-per-slot-mtp); passed its v0.2.11 vs v0.2.10 A/B on aggregate
throughput `0.983-1.011`, decode `0.975-1.011`, TTFT ~`1.00` and prefill `0.997-1.029` while missing 3 of 100 checks at
`w2/c2` driven by baseline block A3's 8.86 ms TPOT and 0.253 s gap, overridden by the owner as `"Override: chain + route,
then arms"`; G16/G20/G21 restart readiness 31.1 / 30.9 / 31.4 s, G15 kill recall 44.5-45.4 s, G10 Windows commit headroom
81.73 GiB `87,757,533,184 B` of a 219.70 GiB limit with 127.23 GiB available RAM and 74,918 MiB GPU memory, 8,192 MiB
automatic conversation cache with 35 parks in G19, G24 16/18, pilot 5/6, batch wall 549 s; `v0.2.10` `kvvram-envpg`,
`v0.2.9` `kvvram-envpg` and `v0.2.9` base move to earlier qualified history; seven old v0.2.3-v0.2.9 IQ3_S roots were
pruned on 2026-11-06 with the owner's approval freeing `E:` from 115.5 to 202.5 GiB, and the v0.2.11 quality-first
one-slot `IQ3_S` (`win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`), one-slot
`UD-Q5_K_XL` (`win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`) and six-expert
`DeepSeek-V4.1-Flash-1017` `IQ2_XS` (`win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0`) drafts, the
v0.2.11 four-slot `UD-Q4_K_XL` screen — slower than the v0.2.11 four-slot IQ3_S batch-MTP profile in every measured
workload: single-request decode 0.85-0.91x, total throughput 0.73-0.84x — and the v0.2.9 `UD-IQ4_XS` / `NVFP4-QAD` model
candidates and their Studio routes stay comparison-only drafts;
[2026-11-07 decision](DECISION.md#update-2026-11-07-quality-first-comparison-on-the-pro-keeps-the-four-slot-iq3_s-incumbent)). GDN tensor-core numerics are not bit-exact upstream, and `strata.engine_env` pins are reviewed per engine
release (`ENGINE_ENV_REVIEWED_ENGINES`, engines `0.1.55`, `0.1.56` and `0.1.57`), so the next engine release requires a
fresh review.

On the pair (`rtx3090-win-a`), the current v0.2.11 `df2` DFlash2 profile
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`,
engine 0.1.57, stage order admitted at `772a418`) pins stock roles (`--gpu-roles 0=main,1=helper`: RTX 4090 as Main,
staged last), stock setup's manual split point at the layer the automatic planner chose
(`strata.setup_args.layer_split: "24"`, layers 0-23 on the RTX 3090 and 24-47 on the RTX 4090),
`strata.trim_stage_weights: true` (`--trim-stage-weights`, [Stock stage weight trim](#stock-stage-weight-trim), so each
card loads only its own stage's dense weights, 771 and 988 MiB instead of 1,466 and 2,019 MiB), `strata.ple_io: "direct"`
(`--ple-io direct`, [Stock PLE direct reads](#stock-ple-direct-reads)), keeping the 26.8 GiB PLE table on direct SSD reads
so every start logs `PLE direct read probe: N rows/s (fine)` with no residency-policy line and sizes the automatic
conversation cache at 8,192 MiB (up to 4 parked conversations), `strata.engine_env` with the engine's `sm_86` default
table (`sm86_table`, skipped by default on the mixed `sm_86` + `sm_89` pair;
[Strata#3313](https://github.com/Niko1221/Strata/issues/3313)) and stock `gdn_stack` (`GDN_STACK_CUDA`), and stock
DFlash2 drafting alone (`strata.drafting: "dflash2"`,
`--draft dflash2 --draft-model <root>\data\dflash2\qwen3.8-flash-next-dflash2.q4_0-selq4.pack --draft-fallback none --draft-conf 0.35 --draft-vocab <root>\data\dflash2\draft_vocab.bin`,
packed offline during `install` by stock `tools/dflash2_pack.py` from pinned
`incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744e85c17364dcc54a6a420af7135d4c7f6` `config.json` and
`model.safetensors`, with `STRATA_NO_ACQUIRE=1` and no start-time fetch or silent MTP fallback;
[UPSTREAM.md](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)). On engine 0.1.57 (which reserves 256 MiB plus an extra
DFlash2 reserve on the last stage), the expert caches are **19.41 GiB** on the RTX 3090 and **17.90 GiB** on the RTX 4090
(vs 19.41 / 18.31 GiB on the v0.2.10 `df2` rollback and 19.14 / 17.75 GiB on the v0.2.10 `pw2` `env86g` MTP alternative).
In three paired cold starts against its v0.2.10 `df2` rollback, `w1` / `w3` throughput was `1.008` / `0.999`, TTFT was
~`1.0`, TPOT was `0.98-0.99`, decode was `0.966-1.022` and prefill was `0.988-1.062`, while 4 of 88 checks missed on
burstiness only (`w1` longest gap p50/p95/max `1.125-1.126`, depth-0 p95 inter-event gap `1.096`); after the owner
overrode those misses (`"Override: run the main chain"`), the requalification chain on 2026-11-06 at `772a418`
(`ba574d5`) and complete G13 rerun at `611c342` (`3144675`) passed all 14 measured gates, with `[strata] drafting:
DFlash2 alone (--draft dflash2, --draft-conf 0.35)` on every start (G10 `28.70 GiB` Windows commit headroom
`30,811,574,272 B` of a `135.69 GiB` limit and `66.35 GiB` available RAM; G16 / G20 / G21 restart readiness
`40.5 / 40.5 / 40.8 s`; G17 near-limit task wall `61.1 s`; G19 `8,192 MiB` cache, 12 parks; G24 `15/18`, pilot `5/6`,
batch wall `896 s`; G26 `install` `37.0 s`, `start` `52.6 s`; [decision](DECISION.md)). Its rollback is the qualified
v0.2.10 `df2` DFlash2 profile
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`:
G10 `27.51 GiB` Windows commit headroom `29,534,670,848 B` of a `135.69 GiB` limit and `65.65 GiB` available RAM;
G16 / G20 / G21 `43.1 / 43.2 / 43.4 s`; G17 near-limit task wall `59.0 s`; G24 `17/18`, pilot `5/6`, batch wall `916 s`),
while the v0.2.10 `pw2` `env86g` MTP profile
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`:
G10 `27.54 GiB` commit headroom, G16 / G20 / G21 `55.3 / 43.2 / 55.7 s`, G24 `16/18`, batch wall `1,045 s`) remains
qualified as an older alternative (`v0.2.9` `env86g`, `v0.2.9` split-24 trim base, `v0.2.8` split-24 trim, `v0.2.8`
`roles-pledirect` and `v0.2.7` PLE-direct stay earlier qualified history; three v0.2.8/v0.2.9 pair roots were pruned on
2026-11-06 with the owner's approval freeing `C:` from 94.8 to 128.7 GiB). The measurement-only v0.2.8 stock-residency
pair draft (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`), the held v0.2.7 roles
draft with PLE in RAM (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2`), the
unmeasured v0.2.7 default-split draft, the default and split-32 v0.2.3 pair drafts and the v0.1.44.1 pair release stay
unqualified. Physical display placement must match the profile. Each profile has its own root (one runtime per root).

**RTX 5090 262K default (Strata v0.2.11 + OMP 18.16.0, owner decision 2026-11-06) and 131K alternative (Strata v0.2.10 + OMP 18.16.0, owner decision 2026-11-03):**
On `rtx5090-win-a`, the tuned 262,144-token profile
(`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`, rolling back to
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0`; the `v0.2.9` `kvvram-kvgrow-envg` and base
profiles and `v0.2.8` 262K move to earlier qualified history) is the host's default. It pins `strata.engine_env`
`gdn_stack` (`GDN_STACK_CUDA`), `setup_args.kv_streaming: "off"` (`--kv-streaming off`, 34 GiB available-RAM start floor)
and `strata.kv_grow: true` (`--kv-grow`), passing v0.2.11 vs v0.2.10 A/B on `w1` 512/512 throughput (`1.011`), TTFT
(`0.970`), decode (`0.965-1.008`), prefill (`0.988-1.138`) and 100K TTFT (`0.969`) while missing 11 of 88 checks on the
32K-prompt single-request `w3` workload (`agg_tps` `0.917`, TTFT p50 `1.097`, TPOT p50 `1.051`) from engine 0.1.57's
32,768-token bare `--prefill auto` chunk ceiling (overridden by the owner on 2026-11-06 as `"Override: accept it, run the
chains"`), and sizing a 4,352 MiB automatic conversation cache in G19 (17 parks; G10 13.47 GiB available RAM and 20.30 GiB
commit headroom of 85.15 GiB; G16/G20/G21 restart readiness 18.5-19.3 s; G24 17/18, pilot 6/6, batch wall 843 s).
Operating condition is unchanged: the host's Docker Desktop and WSL (which run its production NInfer container) must be
stopped before starting it; after WSL restarts, that container must be recreated by the owner's pinned relaunch script or
returned through the owner's fleet controller (a WSL-up start was refused at 7.3 GiB available RAM while another of the
owner's agents held host memory; untested on an idle host). The unpinned-GDN v0.2.9 fallback
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0` was prepared and never installed (draft). The
131,072-token profile (`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`, rolling back to
`win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`; `v0.2.8` 131K is earlier qualified history) stays the qualified
alternative for running with Docker Desktop and WSL up (the production container stopped by the fleet controller; 34 GiB
start floor; G16/G20/G21 18.7-18.9 s, 3,584 MiB cache, G24 16/18, pilot 6/6, batch wall 742 s) because the v0.2.11 131K
draft (`win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`) failed G15 twice after the mid-generation engine kill and
is not qualified. All four qualified current and rollback ledgers on `rtx5090-win-a`
([262K default v0.2.11](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/qualification.json),
[262K rollback v0.2.10](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/qualification.json),
[131K alternative v0.2.10](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/qualification.json),
[131K rollback v0.2.9](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/qualification.json)) have 21
pass and 3 not applicable ([2026-11-06 windows measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160),
[2026-11-03 windows measurements](MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160)).

The CI `suite` matrix in `.github/workflows/ci.yml` contains the current and rollback server profiles (the PRO
`df2` DFlash2 current and `batchmtp` `kvvram-envpg` rollback on v0.2.11 + OMP 18.16.0; the RTX 5090 262K
`kvvram-kvgrow-envg` default on v0.2.11 + OMP 18.16.0 and its v0.2.10 + OMP 18.16.0 rollback; the RTX 5090 131K
alternative on v0.2.10 + OMP 18.16.0 and its v0.2.9 + OMP 18.15.0 rollback; and the pair `df2` DFlash2 current on
v0.2.11 + OMP 18.16.0 and its v0.2.10 `df2` rollback), plus any draft actively being qualified.
The unscheduled v0.2.11 and v0.2.9 drafts (the PRO quality-first one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and six-expert
`DeepSeek V4.1-Flash IQ2_XS` comparison drafts, the PRO `UD-Q4_K_XL` screen, the RTX 5090 `kvvram-kvgrow` fallback, and
the PRO `UD-IQ4_XS` and `NVFP4-QAD` model candidates), the measurement-only v0.2.8 stock-residency pair draft, held drafts
(such as the v0.2.7 pair roles draft with PLE in RAM) and older history are excluded; their ledgers and receipts remain
covered by the all-release `checks` job.

<details><summary>Earlier qualified profiles and single-card rollback limits</summary>

Earlier qualified profiles keep their own roots and ledgers:

- **RTX PRO 6000 and RTX 5090:** on the PRO, the v0.2.10 + OMP 18.16.0 `kvvram-envpg` profile, the v0.2.9 + OMP 18.15.0
  `kvvram-envpg` and base (`slots4-batchmtp-pledirect-parking`) profiles, and v0.2.8 + OMP 18.14.0
  (`slots4-batchmtp-pledirect-parking`, `slots4-pledirect-parking` and `slots4-parking`; seven old v0.2.3-v0.2.9 IQ3_S
  PRO host roots were pruned on 2026-11-06 with the owner's approval), and on the RTX 5090, the v0.2.9 + OMP 18.15.0
  262K `kvvram-kvgrow-envg` and 262K base (`coder-iq1m-262k`) profiles and v0.2.8 + OMP 18.14.0 (262K and 131K), then on
  both hosts v0.2.7 + OMP 18.13.2 (including both the 262K and 131K RTX 5090 profiles),
  v0.2.3 + OMP 18.12.6 (including both the 131K and 262K RTX 5090 profiles, whose host integration roots were removed on
  2026-11-02 with the owner's approval), v0.2.1 (earlier qualified history on both hosts, including the 262K profile;
  v0.2.1 integration roots were removed on every host on 2026-10-28), v0.1.44.1 (including the RTX 5090 262K profile),
  v0.1.43.1 and v0.1.43 with OMP 18.10.1; each host's v0.1.42 + OMP 18.8.9 profile; on the PRO, v0.1.41 at 262K then
  131K, v0.1.40.3 with OMP 18.8.4 then 18.8.3 slots4-parking, and
  `win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0`; on the RTX 5090, v0.1.41 with OMP 18.8.6 then
  `win11-rtx5090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4`.
- **RTX 4090 + RTX 3090 pair:** the v0.2.10 + OMP 18.16.0 `pw2` `env86g` MTP profile
  (`pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking`), the v0.2.9 + OMP 18.15.0 `env86g`
  (`roles-split24-trimweights-pledirect-env86g-parking`) and split-24 trim + PLE-direct base
  (`roles-split24-trimweights-pledirect-parking`) profiles, the v0.2.8 + OMP 18.14.0 split-24 trim + PLE-direct
  (`roles-split24-trimweights-pledirect-parking`; three v0.2.8/v0.2.9 pair roots were pruned on 2026-11-06 with the
  owner's approval) and initial PLE-direct (`roles-pledirect-parking`) stock-roles
  profiles, v0.2.7 + OMP 18.13.2 (PLE-direct stock roles), v0.2.3 + OMP 18.12.6 (stock roles),
  v0.2.1 (default-split, earlier qualified history; host root removed on 2026-10-28), v0.1.43.1 and v0.1.43 with OMP
  18.10.1, `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9`
  and `win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9` keep the display on the RTX 4090;
  `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` requires moving the display back to the RTX 3090.
- **Single-card RTX 3090 and fourth-tuple profiles:** `win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` and the
  fourth tuple's stay qualified for single-card RTX 3090 hosts, but are not rollbacks on `rtx3090-win-a` while both
  cards are installed: those profiles name GPU 0, now the RTX 4090; single-card `start` checks only that GPU 0 is free
  and would run there, although `doctor` reports the model mismatch. The fourth tuple's profiles, such as
  `win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10`, stay qualified as earlier RTX 5090 history and on the
  single-card RTX 4090.
</details>

## Layout of the integration root

| Path | Contents |
|---|---|
| `downloads\` | Pinned OMP, Strata and llama.cpp archives and the locked wheels, each verified by size and SHA-256 |
| `models\` | Pinned GGUF shards under `<variant>-<quantization>` (two for the Coder and for IQ3_S, four for Unsloth UD-Q4_K_XL) |
| `runtime\strata\` | The pinned stock Strata source (v0.2.11 current profiles on the PRO, RTX 5090 262K default and pair, plus the PRO's v0.2.11 `batchmtp` rollback, with engine component 0.1.57 staged under `runtime\strata\engine\`; v0.2.10 on the RTX 5090 131K alternative, the RTX 5090 262K and pair `df2` rollbacks, the pair's v0.2.10 `pw2` `env86g` alternative and earlier PRO v0.2.10 history with engine component 0.1.56; v0.2.9 rollback on the RTX 5090 131K and earlier v0.2.9 history with engine 0.1.55; v0.2.8 earlier history with engine 0.1.54; v0.2.7 earlier history with engine 0.1.52; v0.2.3 earlier history with engine 0.1.48; v0.1.40.3 for the qualified single-card RTX 3090 profile), its generated config and its hash-locked `.venv` |
| `data\`, `appdata\`, `localappdata\` | Stock setup's generated data (including `data\dflash2\` packed offline from `downloads\dflash2\` on the PRO and pair DFlash2 profiles) and its redirected APPDATA / LOCALAPPDATA (never `%APPDATA%\Strata` or `%LOCALAPPDATA%\Strata`) |
| `state\install-record.json` | Install record: `runtime_identity_sha256`, pip freeze digest, profile fingerprint |
| `state\run.json`, `state\strata-runtime\` | Owned process identities (PID, creation time, executable), readiness facts, and on engine 0.1.57+ the redirected `STRATA_RUNTIME_DIR` activity lease (`.activity.lock`) |
| `state\strata-api-key` | The private API key (user-only ACL) |
| `logs\server-*.log`, `logs\serve-*.log` | Stock server output and the wrapper's own log |
| `omp\home\` | The isolated OMP HOME; sessions live under `.omp\profiles\omp-strata\agent\sessions` |

## Lifecycle

| Command | Behavior |
|---|---|
| `status` | One of `not_installed`, `stopped`, `starting`, `healthy`, `degraded`, `mismatched`, `failed`. `healthy` requires authenticated identity checks and an engine process under the server. |
| `start` | Refuses when owned processes already run, when anything else holds the port, when the GPU has 1,500 MiB or more used or any compute process (or any graphics client, unless the profile declares the GPU display-attached), or when less RAM is available than the profile's `min_available_ram_gib_at_start`. Waits up to 900 s for readiness. |
| `stop` | Stops the recorded wrapper and server and everything currently beneath them, deepest first. Only processes whose PID, creation time and executable still match are touched. Waits for the port to be released. Repeating it is a no-op. |
| `restart` | `stop`, then `start`. |

**Process ownership.** The process tree on Windows is: `serve` wrapper (`python.exe`) → venv `python.exe` (a
redirector) → base `python.exe` running stock `serve/server.py` → `strata.exe` (the engine, which owns the GPU). A PID
alone never identifies an owned process: PIDs are reused, so `stop` verifies PID, creation time and executable before
stopping descendants deepest first.

**Startup RAM floors (`min_available_ram_gib_at_start`) and readiness times:**

- **Current profiles:** 78 GiB and 31.0-35.7 s readiness on the current v0.2.11 RTX PRO 6000 262K `df2` DFlash2 profile
  (G16 31.0 s, G20 31.0 s, G21 35.7 s; 30.9-31.4 s on its v0.2.11 `batchmtp` `kvvram-envpg` rollback with G16 31.1 s,
  G20 30.9 s and G21 31.4 s; 31.0-31.3 s on v0.2.10 and v0.2.9 `kvvram-envpg`, 74 GiB and 35.1-39.7 s on the v0.2.9
  `slots4-batchmtp-pledirect-parking` base profile,
  35.5-51.5 s on v0.2.8 batch-MTP, 35.0-51.4 s on the v0.2.8 PLE-direct alternative, 73.6-88.2 s on v0.2.8
  `slots4-parking`, 80.2-94.3 s on v0.2.7 history, and 23.7-26.8 s on v0.2.3 history); 34 GiB (setup's non-streaming
  floor with `--kv-streaming off`, vs 36 GiB on the streamed-KV v0.2.9 base profile) and 18.5-19.3 s readiness on the
  current v0.2.11 RTX 5090 262K `kvvram-kvgrow-envg` default profile (G16 18.5 s, G20 19.0 s, G21 19.3 s; 19.2-19.5 s on
  the v0.2.10 `kvvram-kvgrow-envg` rollback, 18.6-18.9 s on v0.2.9 `kvvram-kvgrow-envg`, 16.6-16.8 s on the v0.2.9 base
  profile at 36 GiB; v0.2.8 history: 17.1-28.3 s; v0.2.7 history: 16.1-16.9 s; v0.2.3 history: 19.0-23.0 s; v0.2.1
  history: 18.5-19.6 s) when the host's Docker Desktop and WSL are stopped (a WSL-up start of the 34 GiB-floor variant
  was refused at 7.3 GiB available RAM while another of the owner's agents held host memory and remains untested on an
  idle host; the 36 GiB-floor v0.2.9 base profile refuses at 35.7-36.2 GiB available RAM when the production NInfer VM is
  resident); 34 GiB and 18.7-18.9 s readiness on the qualified v0.2.10 131K RTX 5090 Coder alternative (G16 18.7 s, G20
  18.7 s, G21 18.9 s; v0.2.9 rollback: 16.1-26.8 s; v0.2.8 history: 16.6-27.2 s; v0.2.7 history: 18.7-28.4 s; v0.2.3
  history: 17.0-23.0 s; 16.5-16.8 s on the unqualified v0.2.11 131K run) that keeps every expert in RAM and starts with
  Docker Desktop and WSL running; 78 GiB and 40.5-40.8 s readiness across G16/G20/G21 (G16 40.5 s, G20 40.5 s, G21
  40.8 s) on the current v0.2.11 RTX 4090 + RTX 3090 pair `df2` DFlash2 profile (43.1-43.4 s across G16/G20/G21 and
  45.0-45.1 s in the A/B blocks on its v0.2.10 `df2` rollback; 43.2-55.7 s across G16/G20/G21 on the v0.2.10 `pw2`
  `env86g` MTP alternative; 43.5-43.9 s on v0.2.9 `env86g` history, 55.4-55.6 s on v0.2.9 trim history, 43.7-44.4 s on
  v0.2.8 `roles-pledirect` history, 56.8-57.0 s on v0.2.7 PLE-direct history, 55.7-56.2 s on v0.2.3 roles history,
  46.7-47.1 s on v0.2.1 history, and 54.7-55.0 s on its v0.1.43.1 and v0.1.43 predecessors). The measurement-only v0.2.8
  stock-residency pair draft took 106-112 s (including 33.9-34.0 s locking the 26.8 GiB PLE table before giving the lock
  back), and the held v0.2.7 roles draft (PLE in RAM) took 89.8-93.1 s.
- **Earlier and exploratory profiles:** 66 GiB on the earlier v0.1.42 pair profile; 72 GiB on the RTX PRO 6000 131K
  18.8.4 and 18.8.3 predecessors, and 64 GiB on the v0.1.40.2 profile; 34 GiB and 17-33 s readiness on single-card
  RTX 3090 131K Coder profiles; 16 GiB and about 15 s readiness on the low-RAM RTX 4090 profile; 52 and 64 GiB on the
  exploratory IQ3_S profiles on the 24 GB GPUs.

**First-prompt expert-cache warmup.** On the RTX PRO 6000 the server opens while it is still filling its 46.8 GiB GPU
expert cache, so the first prompt after a start waits for it: 6 s for a 7,698-token prompt in the Strata v0.1.41 run,
against about 1 s for an 8,030-token prompt once the cache was full. The RTX 5090's 23.4 GiB cache fills before it
reports ready.

## Failures and recovery

- **Engine process died** (crash, OOM, kill). Stock Strata answers the request in flight with an error and starts
  the engine again on the *next* request. That takes about 15 s on the RTX 5090 and about 30 s on the RTX PRO 6000
  (the experts are reloaded), and the whole prompt is prefilled again. Until that request, `status` reports
  `degraded` ("no engine process"), and `launch-omp` refuses to start. On a multi-GPU profile `status` stays
  `degraded` after that restart too ("startup stage order unavailable for current engine generation"): stock restarts
  the engine with the same command, but `"layer_split": "auto"` places the layers again from each card's free VRAM,
  and the integration verifies the stage order and layer boundaries only for an engine generation it started itself.
  Every pair qualification shows this once, after G15 kills the engine. Recover with `restart`, which also clears the
  stale-cancel state below.
- **Stale cancel after a queued client disconnects** (upstream defect Strata#183, reproduced by `g14q`; present in
  the first candidate's v0.1.27, fixed in v0.1.28, and confirmed fixed by `g14q` on the second candidate's v0.1.30
  and in every qualification run since). If a client disconnects while its request is still queued behind another
  one, the next request with a multi-chunk prompt (thousands of tokens) fails with HTTP 400 `cancelled`. The engine
  then exits, and the request after that gets HTTP 503 before the engine restarts. Short prompts are not affected.
  With OMP this appears as one failed turn, possibly followed by an engine restart. Run `restart` after cancelling
  queued work.
- **HTTP 400 "requests are never truncated".** The prompt plus the requested output does not fit in the profile's
  context (262,144 tokens on the current RTX PRO 6000, RTX 5090 default and pair profiles;
  131,072 on the RTX 5090 131K alternative and single-card profiles). OMP sizes the output cap to
  the room it estimates is left. The integration declares the window 1,024 tokens smaller than the engine's so that
  estimate errors do not reach the server. A single prompt larger than the declared window (about 261K or 130K
  tokens) cannot be sent at all; OMP compacts long sessions before that point.
- **HTTP 401.** The key is missing or wrong. `launch-omp` reads the key from `state\strata-api-key`. Clients of
  your own must send it as `Authorization: Bearer <key>`.
- **Mismatched.** The install record or running server belongs to another profile or runtime identity. Run
  `stop`, then `install` again.

## Logs and evidence

- Server output: `logs\server-<utc>.log`. It contains the stock progress lines (`done: N tokens ... (finish,
  cancel=...)`, engine restarts). Tool and qualification logs are next to it.
- The qualification probes (`scripts\realhost_gates.py`, `scripts\tracer.py`) and the evaluation keep their raw
  material under `<root>\evidence\<run_id>\` and `<root>\eval\`. Only derived facts are published, under
  `releases\<profile>\`.

## Upgrades

The profile pins every component. Changing any component (OMP, Strata, the model, context, KV or speculation
settings) means a new profile id, a new integration root and qualification of the affected gates. It is never an
in-place edit of a qualified profile or root: the second candidate was installed next to the first, and switching
between them is `stop` in one root and `start` in the other (never both at once; they share the port and the GPU).
`scripts\verify_release.py --manifest releases\<profile>\manifest.json` checks that the profile, ledger and
receipts still bind together.

A host change can have the same effect, because stock setup derives two flags from total RAM: the Coder IQ1_M
gets the low-RAM mode below 33.4 GiB and KV streaming (`--kv-resident 32768`) from 34.8 GiB; IQ3_S streams from
64.8 GiB. `install` refuses a generated flag the profile does not expect, so a RAM upgrade that crosses one of these
thresholds needs the profile written for the new configuration (the RTX 4090 and IQ3_S drafts without `lowram` or
with `kvstream` in their ids), installed into a new root.

**Component engine releases (Strata v0.2.1 and later).** These releases publish no `strata-windows-x64.zip`; the
Windows engine is a separate package, `strata-engine-<engine version>-windows-x86_64-cuda-cuda13.tar.gz`, versioned
apart from the app (v0.2.1 ships engine 0.1.46). A profile for one adds `strata.engine_component` (format, platform,
backend, variant, the SHA-256 of the raw `engine-component.json`, its `build_id`, and BUILD.json's `source` and
`commit`), and its `strata.engine_version` is the engine's own version. `install` downloads the pinned tarball like
any artifact, checks every member against the manifest (regular files at the archive root only, exact file set,
per-file size and SHA-256), and stages the files into `runtime\strata\engine\` before stock setup runs; setup then
reuses that engine and downloads or compiles nothing, with pip's package index switched off. An `engine\` folder that
holds anything else is refused, never repaired. The manifest's ed25519 signature is not verified, and no Control
package, signed feed or desktop installer is used. Setup's own `args_written` record must equal the config's `args`,
with no `user_args`; the pinned calibration, tip and pipeline-window steps restamp it the way stock writers do.

## Sharing the GPU

The integration assumes it owns the GPU while it runs. `start` refuses a busy GPU. It never stops another
runtime; whoever operates the host must release the GPU first and restore the other runtime afterwards.

A GPU that also drives a display lists the desktop's processes (compositor, logon screen) as WDDM graphics
clients (`C+G`). Profiles for such hosts set `host.display_attached: true`: `start`, `doctor` and G10 then tolerate
graphics clients, record how many there are, and still refuse any compute process or 1,500 MiB of foreign use. An
interactive desktop session can hold close to a gigabyte of VRAM in its applications; signing it out before a run
leaves the logon screen's ~180 MiB.

## Maintainer recipes

### Release campaigns (OP10 discovery → OP11 host-owned qualification)

[`schemas/release-campaign.schema.json`](../schemas/release-campaign.schema.json)
(`$id: release-campaign.schema.json`, historical schema 1 and new schema 2) separates **a discovered upstream release**
from **completion on each host**.

[`releases/campaigns/v0.2.11.json`](../releases/campaigns/v0.2.11.json) was opened with
`scripts/campaign.py open --release v0.2.11 --omp-tag v18.16.0`:
GitHub release **435171031**, published **2026-11-05T12:49:59Z**, annotated tag
`4a4160162e4a402e082f41aa0a88e6eed629d913` peeled to `c3b3f5035506f3e966f1b4b7b188aeaabae92f1d`, Windows CUDA 13
engine **0.1.57**, qualifying four of its five rows (`01b4d9b`: the PRO `kvvram-envpg` batch-MTP row with a note naming
the qualified current four-slot `df2` DFlash2 variant, the RTX 5090 262K `kvvram-kvgrow-envg` default, the 4090+3090
pair `df2` DFlash2 variant, and the Studio→PRO route `batchmtp` row with a note naming the qualified `df2` route as
current) while the RTX 5090 131K row is `failed` after failing G15 twice and keeps its `v0.2.10` profile (so the
v0.2.11 campaign status stays `running`), alongside the earlier complete
[`releases/campaigns/v0.2.10.json`](../releases/campaigns/v0.2.10.json) (GitHub release **432079269**, published
**2026-11-02T23:52:47Z**, annotated tag `db0500a53119a349fa44497099d6e28a83ded34a` peeled to
`ffa80d73133ea5c548aefe57889a16e8085a938f`, Windows CUDA 13 engine **0.1.56**),
[`releases/campaigns/v0.2.9.json`](../releases/campaigns/v0.2.9.json),
[`releases/campaigns/v0.2.8.json`](../releases/campaigns/v0.2.8.json),
[`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json),
[`releases/campaigns/v0.2.3.json`](../releases/campaigns/v0.2.3.json) and
[`releases/campaigns/v0.2.1.json`](../releases/campaigns/v0.2.1.json) campaigns (with v0.2.1 having
coalesced [`releases/campaigns/v0.1.45.json`](../releases/campaigns/v0.1.45.json), `superseded_by: v0.2.1`;
v0.1.45 was never drafted or qualified). On v0.2.9, after the campaign completed at the base profiles, the PRO
`kvvram-envpg` variant, the RTX 5090 262K `kvvram-kvgrow-envg` variant and the Studio `kvvram-envpg` route qualified
(`b802d5f`), and the pair `env86g` variant qualified on 2026-11-03 after the owner overrode its `w1` 512/512
single-request A/B miss (`8bbf9a8`), while the v0.2.11 PRO quality-first one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and
six-expert `DeepSeek V4.1-Flash IQ2_XS` comparison drafts, the v0.2.11 PRO `UD-Q4_K_XL` screen, the RTX 5090 v0.2.9
`kvvram-kvgrow` fallback (never installed), and the PRO v0.2.9 `UD-IQ4_XS` and `NVFP4-QAD` model candidates and their
Studio routes stay drafts
([v0.2.11 source review](UPSTREAM.md#strata-v0211-setup-and-start-path-review-engine-0157),
[DeepSeek comparison admission](UPSTREAM.md#deepseek-v41-flash-comparison-admission),
[Qwen one-slot admissions](UPSTREAM.md#pro-quality-first-one-slot-comparison-admissions),
[v0.2.10 source review](UPSTREAM.md#strata-v0210-setup-review-component-engine),
[v0.2.9 source review](UPSTREAM.md#strata-v029-setup-review-component-engine),
[2026-11-06 quality-first comparison](MEASUREMENTS.md#quality-first-comparison-on-the-pro-2026-11-06-stock-strata-v0211-stock-omp-18160),
[2026-11-06 windows measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160),
[2026-11-03 windows measurements](MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160),
[2026-11-02 tuning measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150),
[2026-11-02 windows measurements](MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150)); on v0.2.8, the
separate `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0` draft (stock PLE
residency) stays a measurement-only draft. A lane may list stock variants' profile families (`scripts/campaign.py`
`LANES`, which ranks the PRO `slots4-df2` family and the Studio `df2` route family last); the newest qualified profile
across them (breaking ties by lane order so the current variant listed last wins, `610be03`, `f3fed60`, `c7ba6c4`,
`d10e538`, `01b4d9b`) is the
next predecessor, and `set-host` can qualify a lane's row with another variant's ready manifest at the same Strata and
OMP release. When a new campaign opens, its candidate profile IDs are prepared names, not materialized profiles or
claims of qualification. Release discovery uses only qualified release manifests: comparison-only profiles without a
release manifest do not become baselines or block discovery; malformed manifests still make discovery unavailable.

```sh
python3 scripts/campaign.py open --release v0.2.11 --omp-tag v18.16.0
python3 scripts/campaign.py status
python3 scripts/campaign.py status --release v0.2.11
# Before a pending row runs (qualified rows are terminal and cannot requeue):
python3 scripts/campaign.py set-host --release v0.2.11 \
  --profile win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0 --status queued
```

`open` reads only GitHub metadata, resolves the annotated/lightweight tag, cross-checks the complete asset
endpoint with both release-ID and tag payloads, and atomically writes the campaign. Schema 2 freezes every
asset's ID, name, byte count, publisher SHA-256 (or null) and download URL, plus the effective prerelease
classification and GitHub flags; existing schema-1 records are not rewritten. Duplicate opens preserve its original
discovery time and host progress. A moved tag, changed release identity or changed asset pins returns
**unavailable** (exit 4), without replacing the frozen evidence. Drafts and unselected prereleases return explicit
`skipped` reasons; beta CLI intake without `--allow-prerelease` is refused (exit 2).
Malformed/truncated/missing API data is unavailable, never “no update.” `--check` prints the inventory
without writing or coalescing any record. `--omp-tag <tag>` names every candidate for that stable OMP release
instead of its predecessor's, while each row still records the predecessor's own pin;
[`releases/campaigns/v0.2.11.json`](../releases/campaigns/v0.2.11.json) was opened with `--omp-tag v18.16.0`.
`status` reloads file-backed state; no in-memory cursor, scheduler or new host runner is involved.
Run edits from one operator checkout and commit the resulting campaign changes; atomic files are not a
distributed multi-writer store.

Opening a newer stable release adds `superseded_by` and a disposition note to **pending** rows of older stable campaigns.
Queued/running/qualified/failed/blocked rows and their result/restoration references are untouched; complete
campaigns are immutable. Interrupted coalescing converges when `open` is repeated. A campaign is `pending`
before execution, `running` after any execution/outcome, `complete` when all non-superseded rows qualify, or
`superseded` when every row was coalesced. A skipped older row is not a qualification pass.

**Owner-selected v0.2.0-beta:** [UPSTREAM-BETA.md](UPSTREAM-BETA.md) records the frozen source/component
inventory, metadata-only commands and exact remaining installation contract. `--allow-prerelease` is explicit
even when GitHub's flag is false; a beta campaign never coalesces stable rows (nor is coalesced by stable intake).
Without `--check`, beta `open` freezes/reuses its isolated metadata campaign but returns **exit 2 / blocked**,
not a runnable-profile success. Stable component releases now install natively through a staged engine component
([Upgrades](#upgrades)); component **beta** drafting stays refused and the beta campaign remains metadata only.

Host row transitions are `pending → queued → running → qualified|failed|blocked`; pending/queued may block,
and failed/blocked may explicitly requeue. A blocker needs a result reference or `--note`. Results append,
never erase predecessor evidence:

```sh
python3 scripts/campaign.py set-host --release v0.2.11 --profile "$PROFILE_ID" --status running
python3 scripts/campaign.py set-host --release v0.2.11 --profile "$PROFILE_ID" --status blocked \
  --note "Waiting for the host owner's exclusive window"
# After publication, public-hygiene review, restoration, and the owner's qualification decision:
python3 scripts/campaign.py set-host --release v0.2.11 --profile "$PROFILE_ID" --status qualified \
  --result "releases/$PROFILE_ID/manifest.json" \
  --restored-state "releases/$PROFILE_ID/restored-state.json"
```

References must be existing public repository-relative files, not private host paths or raw logs.
`qualified` calls the existing `verify_release.py` verifier with `require_ready=True`, requires that exact
candidate's manifest to be `qualified`, and requires a restored-state reference. The operator authors the scrubbed
restoration receipt from the actual lease/controller and HTTP observations; this campaign never fabricates one.
The ordinary release manifest, receipts and owner decision remain authoritative.

**OP11 consumes these rows; OP10 does not acquire a GPU, contact a host, install, start, stop, restore or promote.**
Before requeueing/running a row, the host owner reviews the source delta and uses the existing `upstream_watch.py
draft` flow below to materialize its new candidate profile and empty ledger. It must keep the OMP release its row ID
names and the predecessor's model, context and host choices unless a separately reviewed new profile is intended.
Fetch and sync exact tooling; take an approved exclusive GPU window with the host's existing lease/controller; retain
the qualified predecessor.
A next pair candidate's predecessor is the current **v0.2.11** DFlash2 (`df2`) split-24 stage-weight trim + PLE-direct
stock-roles profile
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`,
with `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
as its qualified rollback and `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
as an older qualified MTP alternative; `c7ba6c4`), while **v0.2.9** `env86g` and split-24 trim + PLE-direct base,
**v0.2.8** split-24 trim + PLE-direct, **v0.2.8** `roles-pledirect`, **v0.2.7** (PLE-direct stock roles), **v0.2.3**
(stock roles), **v0.2.1** (default variant, host root removed on 2026-10-28) and **v0.1.43.1** are earlier qualified
history (the measurement-only `v0.2.8` stock-residency roles draft, the held `v0.2.7` roles draft with PLE in RAM, the
unmeasured `v0.2.7` default-split draft, the default and split-32 `v0.2.3` drafts, and the
[draft v0.1.44.1 pair release](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.44.1-omp18.10.1/manifest.json)
remain unqualified). Likewise, a next PRO candidate's predecessor is the current **v0.2.11** four-slot DFlash2 (`df2`)
profile (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`, with
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` as its qualified
batch-MTP rollback; `d10e538`), a next RTX 5090 262K candidate's predecessor is
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`, a next RTX 5090 131K candidate's
predecessor is `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` (since the v0.2.11 131K draft failed G15 twice
and is not qualified), and the Studio route's predecessor is
`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` (with
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` as its rollback). For v0.2.11 on
2026-11-06, the PRO, RTX 5090 262K and pair `df2` windows ran three-pair cold-start version A/B (`A B B A A B`,
`A = v0.2.10`, `B = v0.2.11`), the pair window admitted engine `0.1.57`'s stage order (`772a418`), the PRO window ran a
second three-pair cold-start A/B of the four-slot `df2` DFlash2 arm against `v0.2.11` `batchmtp`
([measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160)), and the PRO (`df2` current and
`batchmtp` rollback), RTX 5090 262K default, pair `df2` and Studio route (`df2` current and `batchmtp` rollback)
qualified while RTX 5090 131K stayed on v0.2.10 ([decision](DECISION.md)). See the
[v0.2.11 source review](UPSTREAM.md#strata-v0211-setup-and-start-path-review-engine-0157),
[stock DFlash2 batch-slot arm review](UPSTREAM.md#stock-dflash2-batch-slot-arm-v0211--0157),
[stock DFlash2 pair arm review](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156) and
[stock OMP 18.16.0 surface](UPSTREAM.md#stock-omp-18160-surface).

The v0.2.11 server profiles ran this way on 2026-11-06 (`fetch`, then `requalify.py`, each in its host's own new root).
From the candidate's tooling on each Windows host, in PowerShell, after the profiles, pinned downloads and owner window
exist (each root below is a new root):

```powershell
# RTX PRO 6000 current (4-slot df2 DFlash2; v0.2.11 batch-MTP rollback in its own root below)
python scripts/requalify.py --profile profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json --root "$env:USERPROFILE\omp-strata-0.2.11-omp18.16.0-df2-kvvram-envpg-262k"
python scripts/requalify.py --profile profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json --root "$env:USERPROFILE\omp-strata-0.2.11-omp18.16.0-kvvram-envpg-262k"
# RTX 5090 default (262K kvvram-kvgrow-envg, 34 GiB start floor; requires Docker Desktop and WSL stopped on the host)
python scripts/requalify.py --profile profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0.json --root "$env:USERPROFILE\omp-strata-0.2.11-omp18.16.0-5090-262k-kvvram-envg"
# RTX 5090 alternative (131K stays on v0.2.10; 34 GiB start floor, starts with Docker Desktop and WSL running)
python scripts/requalify.py --profile profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json --root "$env:USERPROFILE\omp-strata-0.2.10-omp18.16.0-5090-131k"
# RTX 4090 + RTX 3090 current (df2: stock DFlash2 drafter alone, stock roles with RTX 4090 as Main, manual split 24, --trim-stage-weights, --ple-io direct and strata.engine_env sm86_table + gdn_stack)
python scripts/requalify.py --profile profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0.json --root "$env:USERPROFILE\omp-strata-0.2.11-omp18.16.0-pair-df2"
```

Do not use `--keep-running` for campaign runs. `requalify.py` stops only its own runtime; it **does not restore a
foreign tenant**. Pull the named run using `pull_run.py`, dry-run then publish with `publish_run.py`, verify with
`verify_release.py --require-ready`, restore the previous tenant with its existing controller, and record exact
restored service/HTTP observations before reporting the outcome. Preserve failed evidence and blockers.
Do not call `requalify.py` on the Studio route: after the PRO qualifies, materialize the new route against its
server fingerprint, then run the independent [G23 auth/drop/restart probe](REMOTE.md#g23-and-fan-out-evidence)
with private bindings/restart commands. It has its own ledger and restoration reference.

Studio command (run after those private bindings, restart commands and the new qualified server exist):

```sh
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0"
python3 scripts/remote_gates.py --profile routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json \
  --root "$ROOT" --bindings "$ROOT/state/bindings.json" \
  --restart-commands "$ROOT/state/restart-commands.json" \
  --output "$ROOT/proofs/g23-$(date -u +%Y%m%dT%H%M%SZ)" --implementation-commit "$(git rev-parse HEAD)"
```

### Requalifying a new tuple

The sequence used for the second candidate (about 45 minutes of exclusive GPU time, run from a client machine over
SSH with `stdin` closed, so that OMP's print mode never waits on a pipe):

1. **Report, then draft.** `python3 scripts/upstream_watch.py report --strata-src <local Strata checkout>`
   compares stable releases with the newest stable pins whose release manifests are **qualified**, not newer draft/beta pins,
   and checks `upstream-watch.json`
   (the issues/PRs in [UPSTREAM.md](UPSTREAM.md)). It reads local tags, never fetches or changes that checkout.
   JSON goes to stdout, a short summary to stderr: exit **0** = complete/no news, **3** = complete/news,
   **4** = incomplete (including failed, malformed or truncated API responses), never "no change".
   `--pinned-strata-tag <tag> --strata-tag <tag>` selects an explicit source comparison. The checklist compares
   setup constants, the requirements blob, generated/optional config keys, classified server routes and new
   `STRATA_*` names. Review any delta before materializing a runtime. A closed-unmerged Strata PR means
   **check the maintainer commit**, not rejection.

   **Shared-egress sandbox: use the GitHub-API-free candidate path.**
   Use `report --candidate-only <tag> --no-github-api --from <predecessor profile>
   --strata-src <local Strata checkout> --variant cuda13`, then `draft --no-github-api`.
   A per-command request budget cannot reserve GitHub's shared anonymous **60/hour public-IP pool**:
   concurrent jobs can exhaust it before a single candidate finishes. `--no-github-api` makes **zero
   `api.github.com` requests**, implies anonymous mode, never reads `GH_TOKEN`/`GITHUB_TOKEN` or invokes
   `gh auth token`, and never falls back to REST or credentials. It skips global news and tracked items.
   The explicit predecessor's immutable profile pin must still match the local tag; the same reviewed
   source checklist and full draft planner apply.
   Exit codes remain **0** for no newer candidate, **3** for candidate news, **4** for incomplete/refused review.

   ```sh
   python3 scripts/upstream_watch.py report --candidate-only v0.2.2 --no-github-api \
     --from profiles/<predecessor>.json --strata-src "$STRATA_SRC" --variant cuda13 \
     --engine-archive <scratch-cuda13-tarball>
   # Exit 3 above is successful release news, not a reason to stop the reviewed draft.
   python3 scripts/upstream_watch.py draft --no-github-api \
     --from profiles/<predecessor>.json --strata-tag v0.2.2 --omp-tag v18.10.1 \
     --id <new-id> --strata-src "$STRATA_SRC" --variant cuda13 \
     --engine-archive <scratch-cuda13-tarball>
   ```

   Download-mode inventory and integrity contract:

   - Resolve the exact tag object and peel with credential-free `git ls-remote --tags` over public HTTPS,
     before and after discovery; no REST tag lookup. Verify the local source against that peel.
   - Fetch only tag-specific `https://github.com/<owner>/<repo>/releases/download/<tag>/SHA256SUMS.txt`,
     `latest.json`, and `install-manifest.txt` when indexed. The checksum index is the publisher's HTTPS trust
     root; its own observed hash is recorded, not claimed to be self-signed. Verify consumed metadata bytes
     against the index. `latest.json` must name the selected app version; its UI pointers and any manifest
     entries must agree with the index. Never follow its mutable `releases/latest` pointers.
   - Select the engine component from checksum-indexed filenames, not from the app version or the Control
     manifest. The v0.2.2 install manifest names **Control only**. Download the engine through its tag-specific
     URL and verify its full bytes against `SHA256SUMS.txt`; derive byte length from that verified stream.
     An existing `--engine-archive` is fully rehashed, never silently overwritten. A missing path is populated
     only after verification; failed transfers leave no final archive. No retry or API fallback.
   - Re-read the checksum index after each discovery and repeat discovery before committing draft outputs.
     Changed checksums, tag identity, metadata or selected engine pins refuse. Missing required digests refuse
     explicitly, rather than borrowing an API digest or weakening validation. Full draft still inspects the
     verified component manifest without executing binaries.
   - OMP must remain the predecessor's exact tag. Public Git must match its pinned `source_commit` before and
     after drafting; preserve its already-pinned artifacts unchanged. An OMP version change is refused because
     this path cannot establish new OMP publisher digests. Other immutable predecessor pins stay subject to the
     existing planner/dependency checks. Model and MTP metadata still use **two Hugging Face API requests**
     for the reviewed one-page model listing; additional HF pages are traversed completely.
   - `source-release.json` uses distinct `github-release-downloads` provenance: checksum-indexed assets,
     verified document hashes/lengths and Git identity. Unconsumed assets have unknown byte lengths. It does
     **not** invent REST release/asset IDs, GitHub immutable/prerelease flags or a REST publication timestamp;
     `latest.pub_date` is recorded separately. A pre-existing REST campaign snapshot cannot be silently
     reinterpreted as download evidence: differing provenance refuses. This is neither signature verification
     nor host qualification.

   **API-free request budget:** zero GitHub REST requests for report plus any number of drafts. With the
   v0.2.2 metadata layout, one report + one draft uses 12 small release-download GETs (checksum index twice,
   latest and manifest per discovery), eight public Git tag queries, and two HF metadata requests. The engine
   is downloaded once when both commands share `--engine-archive`; otherwise each invocation uses and removes
   a temporary archive. Keep an explicit archive in the sandbox's scratch write scope, not the repository.
   `--no-github-api` does not support metadata-only `draft --check`: byte verification is required.

   **Owner/REST mode remains available and unchanged.** Omitting `--no-github-api` retains the REST release
   inventory; candidate-only is still anonymous, and `--anonymous` alone still means credential-free REST,
   **not API-free**. The existing cold request budget for one candidate report + one full draft, annotated
   Strata/OMP tags and one page per asset/model listing, is:

   | Step | GitHub API requests | Hugging Face metadata requests |
   | --- | ---: | ---: |
   | Candidate report: release by tag, initial ref, annotated object, assets, release by ID, final ref | 6 | 0 |
   | Draft: two complete candidate identity checks, OMP ref/object and release/assets | 16 | 2 |
   | **Total** | **22** | **2** |

   The counting-transport unit regression asserts **24 HTTP calls, at most 25**, including 304 responses
   and separate cold API instances for report/draft. Each additional page adds a request per traversal;
   pagination completeness checks are not bypassed to fit a budget. Local Git/source/archive reads,
   compatibility generation and downloads from release-delivery URLs are not GitHub API calls.
   Repeated mutable endpoints use `If-None-Match` when an ETag is supplied; a validated 304 reuses both JSON
   and pagination headers. A changed 200 response is still checked for identity drift. The final tag ref is
   always re-read; its unchanged immutable annotated object need not be peeled twice within a discovery.
   Cache lifetime is one command only: no persistent cache, credential store or assumption that anonymous
   304s are quota-free.

   This REST budget is **not sufficient for shared-egress sandbox work**. A second full draft adds up to
   16 GitHub + 2 HF calls. On HTTP 403/429 with
   `X-RateLimit-Remaining: 0`, either command stops at the **first** refusal and names the reset time in UTC
   (or explicitly says the reset header is unavailable). There is no automatic retry or credential fallback.
   `report --anonymous` can also run the broad news sweep, but that sweep has no 25-call budget.

   `python3 scripts/upstream_watch.py draft --from <predecessor profile> --strata-tag <tag> --omp-tag <tag>
   --id <new id> --strata-src <local Strata checkout>` resolves live GitHub release asset sizes/digests and
   immutable tag commits, plus Hugging Face shard sizes/LFS digests at stock setup's revisions. Lightweight tags
   resolve directly; an annotated tag is peeled only when its object SHA and tag name match the ref and its
   target is a commit (not another tag, tree or blob). The Strata commit must equal the local checkout's
   `<tag>^{commit}`; profiles pin that peeled commit, and draft JSON records annotated `tag_object_shas`.
   The complete frozen Strata identity/inventory is also saved as `releases/<id>/source-release.json`;
   an existing campaign is checked for drift before drafting. `draft --release <tag> --allow-prerelease
   --variant cuda13 --check` is a metadata-only path, not a runnable component profile (see
   [UPSTREAM-BETA.md](UPSTREAM-BETA.md)). Optional
   `--family`, `--model`, `--context`, `--ram-gib` and `--vram-gib` select a variant. RAM/VRAM here are planning
   inputs, not purchased-capacity floors. Every host floor is the maximum of the predecessor's floor
   and stock setup's estimate: a tuple bump never lowers an established operational constraint. The
   draft JSON reports both inputs and the selected floor. The tool evaluates only stock setup's pure choices and inline
   config arithmetic; it never imports/runs setup's main, fetches an installer or writes a lock. Unfamiliar
   planning code, changed dependencies/lock inputs, mismatched tag identities, missing pins and degraded variants are
   refused (exit **2**, success **0**). The reviewed lane is text-only native Windows NVIDIA, no low-RAM
   mode or RoPE extension, with stock KV streaming; other choices need explicit source review.

   **OMP 18.8.8+ compaction thresholds:** the default trigger is unchanged (the window less the larger of 15% and
   16,384 tokens: 110,541 in a 130,048-token window), but a numeric per-model threshold became a policy base rather
   than an exact trigger; `f<tokens>` is the exact form. G17, G18 and G18L size their sessions from the pinned OMP
   version, and G18's reduced threshold is written as the model's `f12000` entry on those lanes. The source-backed
   cases are in `tests/fixtures/omp-compaction-thresholds.json`.

   **Hybrid CPUs (Strata v0.1.39+):** stock setup writes `--pool-workers` on a CPU with more efficiency than
   performance cores (performance cores - 1 + half the efficiency cores; 15 on an 8P + 16E i9-14900K). Pass the
   host's physical core counts as stock's `cpu_cores()` reports them, `--cpu-cores 8,16`; the draft records them
   as `host.cpu_cores` (later drafts from it keep them) and plans the flag. Profile validation accepts
   `--pool-workers` only as that recommendation and refuses a calibration on such a host. Omit the option when all
   cores are alike; install still refuses a host whose stock setup plans another `--pool-workers`.

   The new profile and `releases/<id>/{manifest,qualification,source-release}.json` are created append-only;
   existing profile/release destinations are never overwritten. **`docs/COMPATIBILITY.md` is also a draft
   output:** after creating the records, `draft` regenerates it with `scripts/render_compatibility.py`'s
   renderer and returns its path as `compatibility`. Include that derived document in the draft PR and its
   sandbox write scope; `python3 scripts/render_compatibility.py --check` must remain current. This does not
   promote the row: the acceptance matrix supplies **24 gates, all `not_run`**, no receipts or install identity,
   and no predecessor receipts are copied. A matrix-write failure is a refusal, not successful drafting; repair
   the output and rerun the renderer, not the append-only draft. Outside candidate-only/`--anonymous` mode,
   GitHub auth remains optional (`GH_TOKEN`, `GITHUB_TOKEN`, then `gh auth token`); it is never sent to Hugging
   Face or printed.

   **Experimental Unsloth Q4 (Strata v0.1.36):** `--family unsloth --model UD-Q4_K_XL --context 131072 --ram-gib 127.69
   --vram-gib 24` uses stock v0.1.36's budget planner, not its low-RAM `experts.bin` mode. It selects
   `--kv-resident 32768 --resident-budget-gib 71`. The 97 GiB total-RAM floor preserves that automatic
   budget; the 97 GiB available-at-start floor reserves the 71 GiB budget, 1.799356416 GB streamed KV and
   stock's 24 GiB OS/engine/file-cache headroom. Fresh-install disk is 112 GiB after rounding up the exact
   111,334,654,784 shard bytes plus stock's 8 GB allowance. Floors still take the predecessor maximum, and
   the profile records the stock budget inputs and each floor's derivation. At 64 GiB, stock's initial budget
   is 40 GiB, reduced to **38 GiB** when this 131K int8 context enables KV streaming.

   All four shards are pinned from stock `UNSLOTH_SHARDS`, cross-checked with HF LFS at revision
   `38bb39ee97821de2c9009abb7e93950eec396e66`. Already downloaded shards may be placed directly in
   `<root>\models\unsloth-UD-Q4_K_XL\`; `fetch --only model` verifies their sizes and SHA-256 without
   downloading them again. Guarded `install` passes that directory and the local pinned prebuilt to stock
   setup, which performs its own `iq_pack.py --compat-bf16` step. The resulting
   `strata-unsloth-ud-q4_k_xl.json` uses shard 1 as `--native`, no `--ple-gguf`, and no model-pack
   `experts.bin` (the separate MTP draft pack still has one). A changed budget, foreign model path, low-RAM
   expert flag or new generated server setting fails verification. This is a new, unqualified draft;
   no speed or quality result is inherited from another model.

2. **Host-free first.** `validate --profile <new>` and
   `python3 scripts/verify_release.py --manifest releases/<id>/manifest.json` must pass; the latter with
   `--require-ready` must fail for a fresh draft. Then run
   `dev-env --profile <new> --root <new dev root> -- python3 -m unittest discover -s tests/mock -t . -v`
   and, under the same dev-env, `python3 -m unittest tests.unit.test_strata_surface tests.unit.test_profile -v`.
   `dev-env` downloads the pinned host client and Strata source and prepares its Python dependencies, never a
   GPU engine/model. Use the lock's Python minor (3.13 for this tuple) to invoke dev-env. Run the host-free
   unit suite once after concurrent edits settle, then commit so later receipts can name the implementation
   commit. Host-free success changes no real-host gate and does not make a draft ready.
3. **Fetch while the other runtime still owns the GPU.** Sync the committed tree to `<new root>\tooling`, then
   `fetch` into the new root (the previous root's verified shards can be copied in first; `fetch` re-hashes them).
4. **Window.** Release the GPU with the owner's tooling; `install`, `keygen`, `start`.
5. **Gates in order:** `realhost_gates.py g10 --deep`, `tracer.py --runs 3`, `g12 --runs <tracer ids>`, `g13`,
   `g14`, `g14q`, `g15`, `g16`, `g17`, `g18`, `g18l`, `g19`, `g20`; then `evaluate.py --pilot` and the scored batch
   with `--between-phases "<python> <tooling>\scripts\omp_strata.py restart ..."`; the quickstart `launch-omp`
   example; `g21` last (it reads every server log); `stop`; restore the other runtime.
   Run this sequence unattended **on the GPU host** with `python scripts/requalify.py --profile <profile>
   --root <root>` (including install/keygen/start). Launch it detached with output redirected to a new file per run;
   its first line names the atomically updated summary and adjacent per-step logs. `--dry-run` prints the plan,
   `--from <step>` or `--only <step,...>` selects steps, and `--keep-running` skips the otherwise unconditional
   final stop. The pilot uses one attempt and the scored batch uses the evaluator's required three.
   A resolved selection that splits a gate's same-run steps is refused before any files or processes are
   created, including with `--dry-run`. Keep `g14,g14q` and `g18,g18l` together, and select `eval` whenever `pilot` is
   selected (G24 is judged on the scored batch; the pilot is reported when present); G26's `quickstart`
   also requires `install,start` in that same run (`quickstart-tests` is emitted automatically). An installation
   in an earlier summary cannot satisfy G26. For example, `--only start,g18,g18l,stop` is a complete G18 rerun,
   while `--only start,g18,stop` and `--from g10` are refused. `--diagnostic` explicitly allows partial diagnostic
   runs and prints one `will not publish` warning per partial gate to stderr, preserving the summary path as the
   first stdout line. It does not relax publication requirements.
6. **Publish.** From the client machine, `python3 scripts/pull_run.py --host <ssh host> --root <root> --log
   <requalify log> --dest <empty private directory>` copies the summary, install record, step results and evaluation
   files of the one run that log names (it refuses a log naming two runs). `python3 scripts/publish_run.py --pulled
   <that directory> --profile profiles/<id>.json --host-label <public label> --root-path <root>
   --implementation-commit <tooling commit> --dry-run` checks the
   plan without writing; without `--dry-run` it scrubs the results (root path, `--private` terms, the untracked
   denylist), writes them under `releases/<id>/evidence/`, appends a receipt per measured gate (G10-G21, G24, G26),
   updates the ledger and sets the manifest's install identity. Add `--host-had-strata` when the host already had
   another root. Status and publication decisions stay with the operator, and the receipts for G00-G06, G22, G23
   and G25 are written by hand. Pull and publish each complete-gate rerun the same way; companion steps must be
   in that rerun's summary, not combined across runs. Earlier receipts, failures included, stay.
   `verify_release.py` and the hygiene scan must pass before the commit.

### Fifth-tuple draft commands

<details><summary>Historical v0.1.36 + OMP 18.4.12 and experimental RoPE draft commands</summary>

These commands created the five v0.1.36/18.4.12 drafts. Set `STRATA_SRC` to a read-only local
checkout containing the tags; only metadata APIs and read-only git operations are used. The stock
setup calculations and pin provenance are recorded in [UPSTREAM.md](UPSTREAM.md). The 4090
predecessor is the earlier **non-low-RAM** draft, not an edit of the 32 GB profile.

```sh
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx5090-coder-iq1m-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 47 --vram-gib 32
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx3090-coder-iq1m-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 128 --vram-gib 24
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx4090-coder-iq1m-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 192 --vram-gib 24
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx4090-coder-iq1m-262k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 192 --vram-gib 24 --context 262144
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx4090-q2-0-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 192 --vram-gib 24 --family qwen --model Q2_0
```

Each command is intentionally non-repeatable at the same destination. A later settings change
requires a different id; never delete or reset an existing ledger to make the command succeed.

Contexts past the model's trained 262,144 tokens (`--context 393216` or `524288`) draft what stock setup does for
them: yarn rope scaling with the factor context / 262,144 (`--rope-scaling yarn --rope-scale 1.5` or `2`), and KV
streaming whose RAM grows with the context (7.2 GB at 524,288). Strata calls it experimental: a scaled run is a
slightly different model at every position, not only past 262,144. The RTX 3090's 524K Coder draft:

```sh
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx3090-coder-iq1m-262k-strata0.1.36-omp18.4.12.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx3090-coder-iq1m-524k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 127.69 --vram-gib 24 --context 524288
```

</details>

### Comparing variants on one host

After a RAM upgrade, install each variant (for example the RTX 4090's Coder 131K, Coder 262K and Q2_0 drafts)
from its own profile into its own root, and measure them one at a time on the same otherwise idle host:
`python scripts/requalify.py --profile <profile> --root <root> --only perf` restarts that root's server, runs
`scripts/perf_probe.py` and stops it (`perf_probe.py --profile <profile> --root <root>` alone measures a server
that is already running; `--depths 0,8K,32K,64K,100K --warm-depth 32K --max-tokens 512 --timeout 600` are the
knobs). It writes `<root>\evidence\perf-<id>\result.json` and prints a table: TTFT, server-reported prefill and
decode rates, draft acceptance from `/metrics` (Strata 0.1.35 and later; otherwise `unavailable`) and a
two-request FIFO queue-wait bound. Gaps between streamed events are not token latencies, and the warm repeat is
live prefix reuse, not restart restoration. The probe changes no gate and no ledger. G24's six tasks are an
integration smoke, not a quality comparison: five are solved by every model tried and one by almost none, so use
a task-set evaluation (below) to compare models.

### Comparing models on a private task set

`scripts/experiment_loop.py` runs **only the candidate**. The fleet controller owns the incumbent;
the driver owns only its candidate process tree. It never opens the incumbent installation, starts,
stops or adopts its processes, writes installed G10, or changes its identity. The old quiesce/restore,
restoration-adoption handoff and `recustody-incumbent` surfaces are removed, not compatibility modes.
There is no artifact-reference attribution or census of non-owned processes. Ordinary installation
lifecycle commands remain available to their existing callers; this driver cannot invoke them on a baseline.

## Threat model

The candidate-only experiment driver runs under a single operator account on a personal Windows
appliance. The experiment root's parent is operator-only; the driver asserts its ACL at start.
The only legitimate concurrent writers are the driver's own generations and the fleet controller,
which owns the incumbent. Competing driver starts, the driver's own stale or partial state,
controller generation changes, and process-tree custody of the candidate are in model.
Another principal concurrently mutating the operator-only experiment root during a window is out
of model: directory swaps, reparse/junction insertion, and log redirection by that principal are
explicit non-claims. The start-time ACL assertion is the control, not a claim of protection against
a hostile operator, an administrator bypassing that ACL, or a compromised operator account.

The driver refuses unsafe ownership or write ACEs on the parent, root, `state/`, and `evidence/`.
It pins directory identities by volume serial and file index, refuses a replaced state directory or
changed admission record before command effects, and checks output directories through handles.
Logs use create-new semantics. Controller generation is checked again after HTTP observation;
failed local hold removal is not custody release. Experimental readiness observes only owned job
membership, never an unfiltered Toolhelp census, and requires one live candidate engine before
publishing ready. The guard verifies the recorded server and engine identities in that job both
before and after authenticated HTTP observation. These checks retain candidate admission and
frozen-harness invariants; they do not enlarge the threat model above.

Host-free executable evidence (`python -m tests.unit.test_experiment_loop`) covers **408 schedules**:
the successor's six added boundary schedules produce **6 counterexamples before** these closures
and **0 after**. The native ACL and directory-handle APIs are stubbed in unit tests; these counts
are finite model evidence, not Windows host qualification or a claim about out-of-model actors.
The readiness-expanded model covers **412 schedules**, with **4 counterexamples before** the
readiness remediation and **0 after**: engine absence or exit during HTTP cannot publish ready
or pass the candidate guard merely because the server remains alive.

#### Window 2: controller reservation, candidate, controller return

Use the private host alias in place of `<host>`; never commit machine bindings or raw evidence.

1. **Freeze without effects.** Retain the earlier comparison JSON and its original job-manifest bundle,
   including the WO2 request file and golden files manifest. Freeze those exact bytes, the candidate and
   baseline profile metadata, the original baseline experiment manifest (bound by the job manifest),
   the full Python harness dependency closure (including `cli.py`) and the lead-reviewed private workload
   runner. Historical manifests must be explicitly re-frozen; they cannot authorize the new driver.
   Candidate install/conversion is isolated: foreign or missing installed fingerprints refuse before fetch/setup,
   prepared NVFP4 uses its own dense native GGUF/PLE/MTP, and incomplete conversion marks never authorize reuse.
2. **Lead: `fleet use <host>`.** Wait for its final **Ready for you**, not its earlier Reserved/Draining
   events. Record that exact generation in the private bindings. The controller closes admission, drains,
   stops its recorded generation and proves expected GPU UUIDs and VRAM below 1,500 MiB.
3. **Driver: candidate arm only.** Run detached on native Windows using the command below. The driver reads
   `C:\ProgramData\OMP\windows-hosts\state\fleet-control.json`, the state returned by `fleet status <host>`.
   It requires `reserved=true`, `admission_open=false`, `phase="Ready for you"`, no blockers, no admitted
   jobs or unresolved transaction/hold, and a successful `resources` receipt for the exact generation.
   That receipt is the controller's physical stop proof; missing telemetry is not inferred from Reserved.
   The expected UUID list and measured VRAM are checked, and the incumbent's loopback port must be closed
   before any install/start effect. Reservation checks continue during candidate commands.
4. **Prove candidate death before return.** All candidate launches/runner commands are in native Windows
   kill-on-close, non-breakaway jobs, assigned while suspended. Stop requires empty native membership and
   independent exact-token observations. Pending launches are cancelled under the candidate root lock.
   A pre-existing live, pending or unproved candidate generation refuses before installation; it is never
   adopted or stopped by a new invocation. Root-lock acquisition and both native/token proofs share one
   aggregate cleanup deadline. Exhaustion still attempts native termination but cannot claim release.
   A failed tree proof preserves the driver's `persistent_hold`; a dead parent/PID is not release evidence.
   An interrupted external golden client also keeps that hold until its outcome is reconciled.
5. **Lead: `fleet return <host>`**, only after `candidate_tree_dead=true` and `custody_released=true`.
   Controller-owned adoption/reconciliation follows the existing controller procedure; there is no
   driver-issued restoration/adoption receipt and no driver `fleet resume`. A blocked return is a controller
   hold to reconcile, never permission to delete the driver's evidence or replay the experiment.

The total window cap is **3.5 hours**, measured from the controller readiness receipt's `observed_utc`
(numeric Unix seconds, written by the controller with `time.time()`).
The driver reserves at least 30 minutes for the lead's `fleet return` and 120 seconds for its own cleanup,
and stops admitting candidate work before those budgets. It emits the absolute return deadline.
This is a deadline/budget for the lead, not a claim that the driver executed or measured controller return.
No controller operation is triggered by importing, planning or testing this code.

```sh
python scripts/experiment_loop.py plan \
  --baseline <incumbent-profile-id> --candidate <candidate-profile-id> \
  --candidate-only-against <retained-comparison.json> --job-manifest <job-manifest.json> \
  --baseline-manifest <original-loop-manifest.json> \
  --runner <private-candidate-runner.py> --rationale "Retained incumbent versus candidate" \
  --out <private-manifest.json>
python scripts/experiment_loop.py run --manifest <private-manifest.json> \
  --bindings <private-bindings.json> --evidence-dir <private-evidence-parent>
python scripts/experiment_loop.py report --directory <private-run-directory>
```

Private bindings contain `candidate_root`, `host_lock_id` (the same physical lock used by the evaluator),
`controller: {host, generation, gpu_uuids}`, `retained_baseline_evidence`, `job_manifest`,
`baseline_manifest`, and `runner`.
They contain no incumbent-root binding. The candidate root must be absolute, canonical, non-reparse and
outside protected directories; exact direct `<candidate-root>/tooling` remains supported. Evidence must be
outside the repository. The controller reservation stays held after the driver exits; only the lead returns it.
Candidate descendants are checked without following symlinks, junctions or other reparse points before
install/setup and command execution; a nested runtime/model alias is not isolation. A prepared conversion
receipt must match the pinned converter digest and tensor-manifest digest as well as its inputs and outputs.
Candidate admission binds the exact idle generation and rechecks it under the installer's root lock, held
through every installation effect. The same fence continues through key creation and start, including a
competing generation that has already stopped. Candidate path components are pinned before the lock is
opened: Windows directory handles refuse deletion/replacement and never follow reparse targets.
The staging disk floor is checked before prefetch/preparation, subtracting already verified checkpoint files;
it is not reapplied as a steady-state workload floor. Candidate guards propagate one remaining deadline
through exact-job observation and authenticated HTTP probes; a late response is failure, not success.
Work-cutoff commands retain their jobs for root-fenced cleanup with the reserved pre-termination proof budget.
An installer must be terminated/proved under that directory fence before cleanup waits on the lifecycle lock
the installer owns. Pending launches still require lifecycle-locked cancellation before their termination.
Both the actual cleanup slice and the wall-clock return deadline are enforced after proof. Candidate generation
is checked again after authenticated probes and after each runner result before any attempt is counted.

#### Frozen workload runner and retained pairing

The default inventory is the full retained **80 jobs**: 14 WO2 jobs × two attempts, six G24 jobs × three,
and 60 golden-1 jobs × one, for **106 planned attempts per arm**. The original job manifest and retained
comparison digests must match. Do not substitute historical WO2 outputs for the retained incumbent rows.
The driver runs every selected candidate attempt once; it does not rerun the incumbent or retry ambiguous work.
The frozen runner is an operator-reviewed Python workload adapter, not a new lifecycle controller.
It is required at planning and execution; missing runner bytes refuse rather than simulate results.
At entry the driver captures the entire frozen Python harness, profiles, schemas, locks and private runner
into a unique per-window copy. Windows read handles deny file writes/deletion throughout execution.
The driver itself re-enters from that copy under isolated Python; CLI/serve commands and runner imports use
only the snapshot and pinned interpreter/standard library, not checkout paths, PYTHONPATH or site hooks.
The `harness_snapshot` receipt records every copied file's digest. Each attempt additionally transports the
runner's copied source through an anonymous input handle. The runner is self-contained: private sibling
imports or path injection outside the frozen harness are not supported. Standard input carries source, not
interactive workload input. These controls bind trusted reviewed code, not an adversarial-code sandbox.
The bootstrap alone owns an outer non-breakaway kill-on-close job containing the frozen worker and all
nested candidate jobs: bootstrap death cannot leave an executing worker behind after the snapshot seals close.
Input/root/window/held-lock preflight precedes snapshot materialization; each snapshot path is unique and
closed worker refusal reasons are preserved rather than replaced with a generic worker failure.
The golden-1 macOS `eval_taskset` client stays external, invoked by this runner using the same frozen manifest.
Its arm must target the already-running candidate only, with no activate/restore lifecycle command.

For each attempt the driver invokes the exact digest-bound runner with:
`--job-manifest PATH --job-manifest-sha256 SHA --family FAMILY --job ID --attempt N --timeout SECONDS
--profile PATH --root CANDIDATE_ROOT`. The runner must verify all referenced workload/expected/verifier files
against the original manifest, preserve request bytes except the pinned candidate model identifier, and apply
the original family budgets within the supplied remaining timeout. For golden-1 it must verify the frozen files
on the client, bound its external attempt to that timeout, wait for client/verification completion and confirm
no external client remains before returning. It has no incumbent or controller mutation authority.
Its final stdout JSON binds `family`, `job`, `attempt`, `job_manifest_sha256`, `status` (`complete` or `failed`),
boolean `passed` and `external_clients_stopped: true`; family-native metrics, failure/verifier details and
private primary-evidence references remain in that result. Malformed, unbound or missing results fail closed.
All host-local runner descendants are inside the driver's command job; nonzero command exit aborts the trial.

A lead-selected subset is explicit at planning: `--job-subset <JSON-list-of-family/job-ids>`.
The frozen `job_subset` and its digest are emitted in the receipt; absent selection means the full inventory.
The paired table always retains every original job and planned denominator, including failures, interruptions,
unselected and unscheduled work. Attempts are persisted **before** guard/runner effects; an interrupted attempt
is not reported as complete. Incumbent cells are deep copies of retained rows marked `retained` with the source
digest; a missing source row is `null`/`unavailable`, never a synthesized measurement.
Cold-load/replay and runner overhead are explicit. Earlier-window incumbent timing is not contemporaneous
candidate timing, WO2 shape checks are not semantic acceptance, and perf/quality alone never promotes a route.
The result remains comparison-only and recommends `hold` pending the owner's evidence-based decision.

`scripts/eval_taskset.py` runs a private task set (a directory of tasks, each with a prompt, an initial
workspace, hidden expected material, a reference solution and a verifier; its `CONTRACT.md` defines the format)
once per model through the pinned stock OMP on a macOS client. It is comparison-only, like G25: it never changes
`launch-omp` routing, an installation or a ledger, and its results are not gate evidence.

- `check --taskset <dir> --arms <arms.json>` proves every task fair before any model runs: the untouched seed
  fails its verifier and the reference passes, both through the same sandbox the agents get.
- `pull-keys --arms <arms.json>` copies each placement's API key over SSH into a user-only client file.
- `run --taskset <dir> --arms <arms.json> --out <private dir>` gives each host one worker that walks its arms in
  order (`hosts.<host>.order`); an arm placed on several hosts is shared, so a host that finishes early takes over
  the rest of it. Before an arm's first attempt on a host, the worker runs that placement's `activate` command
  (an operator script that stops whatever else serves there and starts the engine through its supported
  controller), then owns an `ssh -L` loopback tunnel to it. Each attempt gets a fresh workspace (APFS clones),
  an isolated OMP HOME and stock OMP in print/JSON mode with `read,bash,edit,write,grep,glob`, under
  `sandbox-exec`: no writes anywhere in the home directory outside the attempt, `inputs/` read-only (copies of an
  input are ordinary files), the task set, other attempts and the arms file's `sandbox_deny` trees unreadable,
  network to loopback only. The verifier runs afterwards, sandboxed the same way. An attempt during which a
  tunnel closed, or whose endpoint fails right after it, is an infrastructure fault, not a model result: it is
  kept as `<task>.infra-<time>` and rerun once on re-activated engines. Results are
  `<out>/<arm>/<task>/result.json`; a rerun skips finished attempts and moves an interrupted one aside
  (`<task>.interrupted-<time>`) before retrying it. Several `run` invocations may share one `--out`, e.g. one
  `--host` each, started at different times: an exclusive `<out>/<arm>/.<task>.claim` file holding the runner's
  PID keeps them off the same attempt. Each worker also holds a lock per GPU host it uses (in the system temporary
  directory), so no two runs share or switch one host's engines; a worker whose host is locked stops without
  claiming anything. A claim or lock whose process is gone is taken over unless it carries an experiment's
  explicit failed-restoration hold, which always requires operator reconciliation.
- A `kind: "fleet"` arm runs a lead model with stock subagents on other hosts, as a fleet route would: it names a
  `lead` and `agents` (each a single arm at one of its placements). Every bundled agent type the arm lists
  (`task`, `sonic`, `scout`, `reviewer`, `security-reviewer` in OMP 18.5.0) goes to its model through
  `task.agentModelOverrides`; `sonic` and `scout` otherwise follow the lead's `smol` role. The lead also gets
  the `task` and `wait` tools: subagents run in the background, and print mode ends with the lead's turn unless
  it can block on their results. With stock prompts a lead may never delegate. An arm's `append_system_prompt`
  passes an instruction through OMP's `--append-system-prompt` on every task, and its `prompt_suffix` appends the
  owner's own words to every task's request (for example, asking the lead to use its subagents). The lead's
  event stream also carries every running subagent's progress snapshots, which grow with that subagent's
  transcript, so a fleet attempt's output cap is 1 GiB rather than 64 MiB, and the stored transcript drops those
  snapshots afterwards (tool results and the subagents' own sessions keep their content).
- `summarize --out <dir>` reports pass rates per arm, track and family, paired outcomes with an exact McNemar
  p-value, agent wall time and output tokens.

The arms file is private (host aliases, roots, key paths). `agent_env` carries tool settings the offline sandbox
needs; pnpm 11+ only reads its own settings from `pnpm_config_*` variables, and without
`pnpm_config_verify_deps_before_run=false` it re-verifies the lockfile over the network before every script.

A single arm is stock Strata (`api: openai-completions`, the model from its profile), NInfer's Responses
provider (`api: openai-responses` with `provider`, `model` and `key_env`), or another stock OpenAI-compatible
chat server such as llama.cpp or TabbyAPI (`api: openai-completions` with `provider`, `model` and `key_env`). The
last takes Strata's provider shape with the served model id, and its `model_entry` overrides the context window,
output limit and the reasoning and compatibility flags that server supports. Such arms are comparison-only like
the rest of this tool: the server's install, start and stop belong to the placement's `activate` script, and
nothing here changes `launch-omp` routing.

### Stock calibration as a variant

Stock setup offers to calibrate after an interactive install (`Tune Strata for this PC now?`, default yes; `--yes`
installs skip it): `tools/calibrate.py` measures decode speed with other `--pcie-frac`, `--spec-min-p` and
`--pool-workers` values and keeps one only when it beats the default by more than 3% in an interleaved
re-measurement. The guarded install never calibrates. To try what stock calibration recommends for an installed
profile, run the stock tool against that root's generated config with the server stopped (measurement only,
3.5-5.5 minutes on the RTX 3090 host; it starts its own engine and prints JSON):

```bat
cd <root>\runtime\strata
set APPDATA=<root>\appdata
.venv\Scripts\python.exe -u tools\calibrate.py strata-<tag>.json > <root>\logs\calibrate-<stamp>.log
```

Settings `{}` mean the defaults already won and that profile is the calibrated one. Otherwise save the printed
JSON privately and draft a new profile from exactly the measured one (same tuple, same stock setup choices):

```sh
python3 scripts/upstream_watch.py draft --from profiles/<measured>.json --strata-tag <same> --omp-tag <same> \
  --id <measured id with -calibrated> --strata-src "$STRATA_SRC" --ram-gib <host RAM> --vram-gib <VRAM> \
  --calibration <calibrate.json> --calibration-host <public label> --calibration-date <YYYY-MM-DD>
```

The draft records the kept settings, the stock report and the measured profile's fingerprint in
`strata.calibration` and appends the kept flags the way stock `calibrate.apply` does. Its install runs stock setup
unchanged, then applies the pinned settings with stock `calibrate.apply` and `write_config` (what setup does after
a calibration), and the generated-config check refuses an install whose flags differ. Compare the variant with
its uncalibrated predecessor in separate roots, one at a time, as above.

### Stock batch slots and printed recommendations as a variant

Two more stock setup choices stay off unless a profile pins them. `setup.py --parallel N` writes the config's
`"parallel": N`, and the server then runs up to N requests together in the engine's batch slots (`--batch N`;
stock docs/BATCHING.md). A request alone keeps the fastest single-request path, and every slot's tokens equal its
solo run. After writing the config, setup prints host recommendations as engine flags to add to its args. With 96 GB
of RAM or more it names `--prefill auto:32768`; with 24 GB to spare beside the model it names
`--conversation-cache-mib 8192`, which parks up to four conversations (stock default slots) in host RAM.
Draft both from a profile's tuple:

```sh
python3 scripts/upstream_watch.py draft --from profiles/<predecessor>.json --strata-tag <tag> --omp-tag <tag> \
  --id <new id> --strata-src "$STRATA_SRC" --ram-gib <host RAM> --parallel <N> --stock-tips
```

The planner evaluates stock's own `--parallel` branch and `bench_tips`, each as its reviewed body. A slot count that
stock warns about for the planned card (more than its recommendation, or any count where it recommends one at a
time) is refused. The first `--stock-tips` opt-in pins the printed flags in `strata.stock_tips` and raises the RAM
floors to what those tips assume. Later drafts keep exactly the predecessor's selected tip subset; newly printed
tips are not added, even with `--stock-tips`. A pinned tip that stock no longer prints is dropped and named in the
draft output's `dropped_stock_tips`; the setup-derived RAM floors follow the retained subset, while established
predecessor floors are never lowered. Install passes `--parallel N` to stock setup and adds the pinned flags
with stock `write_config`. The generated-config check refuses a different `"parallel"` or tip value. Slots set OMP's
`providers.maxInFlightRequests` for that server to N (otherwise 1). G14 fills every slot before it queues and drops
a request. G19 runs both first turns at once and checks that a conversation interleaved with another comes back from
its kept state instead of being read again.

### Stock pipeline windows on a layer split

Stock `--pipeline-windows 2` gives each layer-split stage a second verifier, letting the first card start a
guessed next verify window while later cards finish the current one, including decode (stock
`docs/MULTI_GPU.md`). It keeps extra VRAM out of the expert caches for those verifiers and recurrent-state snapshots.
Only a multi-card profile with `layer_split: auto` may pin `strata.pipeline_windows: 2`; batch slots
(`setup_args.parallel >= 2`) are refused. Add `--pipeline-windows 2` to the multi-GPU draft command below;
later drafts carry the pin forward, with the flag in `expected_engine_flags` only when the field is set.

After stock setup, calibration and tips, install adds or replaces the flag through the root's venv and stock
`write_config`. Generated-config verification requires `--pipeline-windows 2` exactly once. After readiness,
start requires stock's `two verifiers per stage` ON line with its `(decode too; ...)` suffix in this start's
engine-log interval, and records that line in `run.json`. An `is off: <reason>` line, a prefill-only ON line or
an absent ON line stops what this start launched and fails it. This also catches stock's runtime refusals, such as
no MTP draft layer or helper caches. Profiles without the field get no new start check. Stock v0.1.42 setup does not
add `--remote-expert-opt` to an existing config with nonzero pipeline windows (#1352).

The [RTX 4090 + RTX 3090 measurement](MEASUREMENTS.md#rtx-4090--rtx-3090-layer-split-2026-10-10-stock-strata-v0142-stock-omp-1889)
found decode +9-13%, prefill unchanged. The pipeline-windows profile is now
[qualified](MEASUREMENTS.md#rtx-4090--rtx-3090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889), with every
measured gate passing on its first run.

### Stock PLE direct reads

Engine 0.1.52 introduced automatic RAM residency for the PLE table. A profile may instead pin
`strata.ple_io: "direct"` to keep the table on direct SSD reads with stock `--ple-io direct`, leaving that RAM
available for the engine's automatic conversation cache and other allocations. This does not pin the cache's
capacity. Use the engine flag, not `STRATA_PLE_AUTO_RAM`: launch strips inherited `STRATA_*` variables, and
multi-GPU profiles refuse `env` overrides.

The field accepts exactly `"direct"`, on any card count, with **engine** 0.1.52 or newer (component engine
versions are independent of the Strata app tag). It requires `--ple-io` and `direct` as two separate elements,
exactly once in `strata.expected_engine_flags`. Without the field, `--ple-io direct` is refused; stock setup's
`--ple-io ram` remains legal. This is neither a stock setup tip nor a calibration setting.

Add `--ple-io direct` to `scripts/upstream_watch.py draft`; later drafts, including same-tuple calibration
drafts, carry the pin forward without repeating the option. Like every changed setting, it needs a new profile
id, integration root and release ledger; ids allow 3-120 lowercase letters, digits, dots and dashes. After stock
setup, calibration, tips and pipeline windows, install replaces any stock PLE mode or appends the flag through
the root's venv and stock `write_config`, restamping `args_written` when present. Generated-config verification
requires the pinned value exactly once.

After readiness, start refuses a `--ple-io <mode> chosen by the residency policy` line whose mode is not
`direct`, using only this start's engine-log interval; refusal stops what this start launched. It records the
last matched `PLE direct read probe: N rows/s (word)` text, or `null` when absent, under
`run.json`'s `ple_io.direct_read_probe`, alongside `ple_io.engine_log_interval`. Surrounding log text is not
copied. There is no required positive log line: on engine 0.1.52 the pair's forced-direct starts log
`PLE direct read probe: N rows/s (fine)` and no residency-policy line (2026-10-28). Profiles without the field get no
PLE start check.

The pair campaign lists the `roles-pledirect-parking` family beside the plain and `roles` families. A blocked row
goes `queued` → `running` → `qualified`. The v0.2.7 roles row was qualified before its profile was held (#67), and a
qualified row takes no other transition, so one more `qualified` with the direct-read variant's ready manifest
verifies that manifest and renames the row to the variant. Do it before the campaign's last open row qualifies: a
complete campaign is immutable (on 2026-10-28 the rename ran first, then the RTX 5090 262K row completed v0.2.7):

```sh
python3 scripts/campaign.py set-host --release v0.2.7 --profile "$PREPARED_PAIR_ID" --status qualified \
  --result "releases/$PLE_DIRECT_ID/manifest.json" --restored-state "$RESTORED_STATE_REF"
```

### Stock per-slot MTP

`strata.batch_mtp: true` pins valueless stock `--batch-mtp`: each batch slot verifies one MTP proposal per
window. Stock's app enables it for one card with 24 GB or more and at least two slots; stock setup carries the
choice but does not write the flag. A profile may pin it only on one card, with `setup_args.parallel >= 2` and
**engine** 0.1.54 or newer. Engine 0.1.40.2 showed no gain. On 2026-10-31, Strata v0.2.8 / engine 0.1.54 on
the RTX PRO 6000 measured total throughput +22.5% at two concurrent requests, +8% at four, summed decode +40%
at four 40K-token prompts, and neutral single-request throughput.

Add `--batch-mtp` to the draft CLI alongside `--parallel <N>`; later drafts keep the pin. The field accepts
exactly `true` and requires the valueless flag exactly once in `expected_engine_flags`; the raw flag without
the field is refused. After stock setup, install adds it with stock `write_config` and restamps `args_written`
when present. Generated-config verification refuses a missing, valued or duplicate flag. Start captures the
single-card engine log and requires this start's `--batch-mtp: N slot drafters on CUDA<d> (...)` ON line.
A `WARNING: --batch-mtp is off: <reason>` line or missing ON line fails and stops the start; `run.json` records
`batch_mtp.log_line` and `batch_mtp.engine_log_interval`. Use a new profile id, root and ledger, not an in-place
change; the PRO campaign includes the `slots4-batchmtp[-pledirect]-parking` variants.

### Stock stage weight trim

`strata.trim_stage_weights: true` pins valueless stock `--trim-stage-weights`: each card loads only its own
layers' dense weights. It requires a two-card layer split with an explicit manual `setup_args.layer_split`
point, never `"auto"`. In engine 0.1.54, CUDA0's arena is built before an automatic split is known, so auto
trims only the later stage. On 2026-10-31, Strata v0.2.8 / engine 0.1.54 on the RTX 3090 + RTX 4090 measured
+1.8 GiB expert cache per card and time to first token -12% at 32K-100K tokens.

Add `--trim-stage-weights --layer-split 24` to the multi-GPU draft CLI, together with the measured Main/Helper
roles (`--gpu-roles 0=main,1=helper`); later drafts keep the pin and manual point, with fresh inventory and roles
inputs as usual. Like batch MTP, the field accepts exactly `true`, requires its valueless flag exactly once in
`expected_engine_flags`, and refuses the raw flag without the field. Install writes it after stock setup with
stock `write_config`; generated-config verification refuses a missing, valued or duplicate flag. Start requires
one `CUDA<d> loads the dense weights of layers <a>-<b> only` line per stage in this start's engine-log interval,
matching layers `0..split-1` and `split..last` from the engine's stage boundaries. A range mismatch, missing or
duplicate stage, or `--trim-stage-weights needs a layer split across GPUs (ignored)` fails and stops the start.
`run.json` records `trim_stage_weights.log_lines` and `trim_stage_weights.engine_log_interval`. Each choice
needs a new profile id, root and ledger; the pair campaign includes the `roles-split24-trimweights-pledirect-parking`
variant.

### Several GPUs: stock layer split as a profile

Stock setup offers NVIDIA cards together when they fit (`together_ok`) and writes the config's `"gpu": [i, j]` with
`"layer_split": "auto"` (stock docs/MULTI_GPU.md). A profile pins that choice as `host.gpus`, one entry per card in
stock setup's order (`gpu_index`, `gpu_model`, `arch`, `pci_bus_id`, `min_gpu_vram_mib`, `display_attached`), plus
`strata.setup_args.gpus` and `"layer_split": "auto"`, in place of the single-card fields. From Strata v0.2.3, two
stock opt-ins may be pinned separately or together by a profile of its own: Main/Helper roles (`setup_args.gpu_roles`,
cards ordered Helpers by number, then Main, with stock's `gpu_order: "as_given"`), and one manual split point for two
cards (`"layer_split": "N"`). Install passes both options to stock setup and verifies their config mirrors; a manual
split keeps the configured stage order, with its boundary checked at start. Any other card order, replicas, helper
expert caches, reserve overrides and
`STRATA_ARENA_PIN_GIB` stay off: each would be a profile change of its own.

1. Inventory the host. The command is read-only, needs no idle GPU, writes nothing and never asks for UUIDs or
   serials; keep its output private:

   ```bat
   python scripts\gpu_inventory.py > <private>\inventory.json
   ```

   `display_attached` is nvidia-smi's physical connection (a monitor on the card). `display_active` is advisory only:
   WDDM reports it `Disabled` even on the card that draws the desktop. Adding a card can renumber the others, because
   nvidia-smi numbers cards by PCI bus. A single-card profile's `gpu_index` then names a different card, and its
   `doctor` fails until a new profile pins the new numbering.

2. Draft with stock's own selection and order:

   ```sh
   python3 scripts/upstream_watch.py draft --from profiles/<predecessor>.json --strata-tag <tag> --omp-tag <tag> \
     --id <new id> --strata-src "$STRATA_SRC" --ram-gib <host RAM> --gpu-inventory <inventory.json> --gpus all
   ```

   The planner runs stock's reviewed `gpu_rank`, `gpu_problem` and `together_ok` (newest architecture first, then
   VRAM, then index) and refuses an explicit `--gpus` list in any other order. Replace `--gpus` with
   `--gpu-roles 0=main,1=helper` for stock roles, or add `--layer-split N` to `--gpus` for a manual split. RAM
   floors keep the predecessor's maxima and add a calculated reservation for each extra streamed session; the expert
   arena counts once. G21 measures the real use.

3. Install, start and qualify as usual. Install passes stock setup `--gpus i,j --layer-split <auto|N>`, or
   `--gpu-roles i=helper,j=main --layer-split auto` for roles, and refuses a generated config without the ordered
   `gpu` list, `gpus_asked`, the pinned `layer_split`, or the pinned roles with `gpu_order`. Setup and the server
   start without inherited `STRATA_*` tuning variables, `CUDA_VISIBLE_DEVICES` or `CUDA_DEVICE_ORDER`. The server
   decides which card runs which stage: with `"layer_split": "auto"` it moves the faster card last, unless the cards
   score within 5% of each other or the faster card has less total VRAM than the configured last card (#1576). Roles
   and a manual split keep the configured order. The server log gets a `[strata] layer split: ...` line whenever it
   changes the order or keeps it for that VRAM reason; the engine's own log (the generated config's `log` file) gets
   one `layer split: CUDA<n> runs layers a-b` line per stage. `start` records the observed order in `run.json`
   (`gpu_stage_order`), complete only when this start's server and engine log intervals agree on every stage, and,
   for a manual split, the second stage starts at layer N. Anything missing, partial or contradictory is
   recorded as unavailable: the order is never assumed, and it is never written back into the profile.

`doctor`, `start` and G10 check every card: model, architecture, PCI bus id, VRAM, driver, the physical display
attachment and the idle policy, with graphics clients tolerated only on the display-attached card. G10, G20 and G21
each publish one resource record covering every card, and `verify_release` requires it before a multi-card gate can
pass; an unreadable gate result leaves G21's record incomplete. G21 samples memory only: WDDM reports no per-process
VRAM, so a foreign process that comes and goes during G21 shows only as a higher peak, while `start` and G10 refuse
any foreign compute process present at launch. Single-card profiles keep their previous checks. G25 compares
single-GPU profiles only and refuses a multi-card one.

#### Combined stock calibration, slots and tips

One draft can combine all three opt-ins on the measured pair (no intermediate profile/install). For the Coder
IQ1_M pair on `rtx3090-win-a`, stop the installed server, then measure with its own pinned stock Python/module.
Run from the tooling checkout first; substitute private paths and the measurement date. The wrapper saves only
stock `calibrate.run`'s result as JSON, not its progress text, and does not modify the measured config:

```bat
python scripts\omp_strata.py stop --profile profiles\win11-rtx3090-rtx4090-coder-iq1m-131k-strata0.1.42-omp18.8.9.json --root <pair-root>
cd /d <pair-root>\runtime\strata
set "APPDATA=<pair-root>\appdata"
.venv\Scripts\python.exe -u -c "import json,sys; from pathlib import Path; from tools import calibrate; result=calibrate.run(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))); Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')" strata-coder-iq1_m.json <private>\pair-calibration.json
```

Keep the server stopped throughout calibration: it starts and restarts the engine itself. Stock v0.1.42
`calibrate.run` uses `serve.server.engine_args(cfg)`, including the layer split. Stock `calibrate.apply` changes
only `args`; `write_config` preserves `gpu`, `layer_split` and `parallel`. The draft pins all kept settings,
including the adaptive tier when stock selects it. On the drafting machine, with the private JSON and inventory:

```sh
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx3090-rtx4090-coder-iq1m-131k-strata0.1.42-omp18.8.9.json \
  --strata-tag v0.1.42 --omp-tag v18.8.9 --id win11-rtx3090-rtx4090-coder-iq1m-131k-calibrated-slots4-tips-strata0.1.42-omp18.8.9 \
  --strata-src "$STRATA_SRC" --ram-gib 127.68 --gpu-inventory <inventory.json> --gpus all \
  --calibration <pair-calibration.json> --calibration-host rtx3090-win-a --calibration-date <YYYY-MM-DD> \
  --parallel 4 --stock-tips
```

The planner checks the measured model, context and ordered cards before adding the opt-ins. It evaluates stock
`parallel_recommend` over **both** cards and refuses counts stock warns about. At 127.68 GiB host RAM, `bench_tips`
adds `--prefill auto:32768` and `--conversation-cache-mib 8192`; RAM floors rise by the same rules as single-card
tips. Calibration is measured on the predecessor, not a performance claim for the combined variant. If stock
keeps `{}` settings, omit the three calibration options: defaults already won; still draft the slots/tips variant.
For an IQ3_XXS or IQ3_S screen winner, use its pair profile, `strata-iq3_xxs.json` or `strata-iq3_s.json` during
measurement, and a matching new id; do not change the model while applying a calibration.

Transfer the draft tooling/profile to the host, then install from that checkout into a **new** root (leave the
measured root intact). Install applies calibration and then tips with stock helpers and checks every pinned flag:

```bat
python scripts\omp_strata.py install --profile profiles\win11-rtx3090-rtx4090-coder-iq1m-131k-calibrated-slots4-tips-strata0.1.42-omp18.8.9.json --root <new-root>
```
