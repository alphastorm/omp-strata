<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
  <img src="assets/logo-light.svg" alt="" width="72" height="72">
</picture>

# OMP Strata

**Stock Oh My Pi on a stock, local Strata server. Nothing forked, everything pinned.**

**Current, qualified: stock OMP `18.15.0` with stock Strata `v0.2.9` across the RTX PRO 6000 (per-slot MTP + PLE-direct + KV in VRAM + stock parallel and GDN stacks), the RTX 5090 (262K default with KV in VRAM + KV growth + GDN stack, and 131K alternative), the RTX 4090 + RTX 3090 pair (split-24 stage-weight trim + PLE-direct variant) and the Mac Studio route. No fork, no proxy, no cloud fallback.**

Keep using [Oh My Pi](https://github.com/can1357/oh-my-pi) in your terminal. OMP Strata pins and verifies every
download, installs [Strata](https://github.com/Niko1221/Strata) with its own unmodified `setup.py` from verified
local inputs, starts it on loopback behind an API key, and launches stock OMP in an isolated profile where every
model role points at that server: one Windows 11 + RTX host, one GPU you own, and real-host acceptance evidence
for every claim.

**[Get started](docs/QUICKSTART.md)** · **[How it works](#how-it-works)** ·
**[Security model](docs/SECURITY.md)** · **[Measurements](docs/MEASUREMENTS.md)** ·
**[Decision](docs/DECISION.md)** · **[Website](https://alphastorm.github.io/omp-strata/)**

[![CI][ci-badge]][ci]
[![Strata pin][strata-badge]][profile]
[![OMP pin][omp-badge]][profile]
[![License][license-badge]][license]

[ci]: https://github.com/alphastorm/omp-strata/actions/workflows/ci.yml
[ci-badge]: https://img.shields.io/github/actions/workflow/status/alphastorm/omp-strata/ci.yml?branch=main&label=CI&labelColor=0B0E11
[profile]: profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0.json
[strata-badge]: https://img.shields.io/badge/Strata-v0.2.9-37C4CB?labelColor=0B0E11
[omp-badge]: https://img.shields.io/badge/OMP-18.15.0-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-strata?color=1C232B&labelColor=0B0E11

<sub><strong>Private by design:</strong> loopback-only server · API key required · isolated OMP profile ·
no cloud fallback · every byte hash-pinned</sub>

</div>

## Qualified now

Qualified on 2026-11-02 and 2026-11-03 ([decision](docs/DECISION.md)). Every local ledger below has 21 pass and 3 not
applicable; the route ledger passed its own G23.

| Host | Model and context | Strata · OMP | Ledger | Rollback |
|---|---|---|---|---|
| RTX PRO 6000 | Qwen3.8-Flash-Next IQ3_S, 262,144 tokens, every expert in VRAM; 4 batch slots with per-slot multi-token prediction (MTP, `--batch-mtp`), direct per-layer embedding (PLE) reads (`--ple-io direct`), KV in VRAM (`--kv-streaming off`, 78 GiB available-RAM start floor), stock `parallel_stack` + `gdn_stack` in `strata.engine_env`, conversation parking (8,192 MiB automatic cache), 32K prompt chunks | v0.2.9 · 18.15.0 | [21 pass, 3 n/a](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/qualification.json) | [v0.2.9 batch-MTP](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json) |
| RTX 5090, **default** | Coder IQ1_M, 262,144 tokens, KV in VRAM (`--kv-streaming off`), elastic KV growth (`--kv-grow`), stock `gdn_stack` in `strata.engine_env`; 34 GiB available-RAM start floor; engine's 4,352 MiB automatic conversation cache (requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script and re-registered with the owner's fleet controller) | v0.2.9 · 18.15.0 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/qualification.json) | [v0.2.9 262K](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/qualification.json) |
| RTX 5090, qualified alternative | Coder IQ1_M, 131,072 tokens; 34 GiB available-RAM start floor; starts with Docker Desktop and WSL running (production container stopped by the fleet controller; qualified, no longer the default) | v0.2.9 · 18.15.0 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/qualification.json) | [v0.2.8 131K](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/qualification.json) |
| RTX 4090 + RTX 3090 | IQ3_S, 262,144 tokens, stock roles (RTX 4090 as Main, staged last), manual layer split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, 19.15 / 17.76 GiB expert caches), pipeline windows 2, no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`), engine `sm_86` default table + stock `gdn_stack` in `strata.engine_env` (qualified under the owner's override of its `w1` 512/512 single-request A/B miss at `1.039` vs `>= 1.05`); engine's 8,192 MiB automatic conversation cache (`v0.2.8` stock-residency roles draft stays measurement-only) | v0.2.9 · 18.15.0 | [21 pass, 3 n/a](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/qualification.json) | [v0.2.9 split-24 trim](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json) |
| Mac Studio → RTX PRO 6000 | SSH local forward to the PRO's 262K `kvvram-envpg` profile ([`docs/REMOTE.md`](docs/REMOTE.md)) | v0.2.9 · 18.15.0 | [G23 pass](releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/qualification.json), 2026-11-02 | [v0.2.9 batch-MTP route](releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/qualification.json) |

Profiles and route, with the host labels the ledgers use:

- RTX PRO 6000, `rtxpro6000-win-a`:
  [`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0.json)
  (**current**; pins `strata.batch_mtp: true`, `--batch-mtp`, `strata.ple_io: "direct"`, `--ple-io direct`, `setup_args.kv_streaming: "off"`, `--kv-streaming off`, and `strata.engine_env` `parallel_stack` + `gdn_stack`; rollback
  [`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0.json);
  the `v0.2.9` `UD-IQ4_XS` and `NVFP4-QAD` model candidates stay comparison-only drafts)
- RTX 5090, `rtx5090-win-a`:
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0.json)
  (**default**; pins `setup_args.kv_streaming: "off"`, `strata.kv_grow: true`, `--kv-grow`, and `strata.engine_env` `gdn_stack`; 34 GiB available-RAM start floor; the host's Docker Desktop and WSL, which run its production NInfer container, must be stopped, and after WSL restarts that container must be recreated by the owner's pinned relaunch script and re-registered with the owner's fleet controller; rollback
  [`win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0`](profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0.json) at a 36 GiB start floor; the unpinned-GDN fallback `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0` stays an uninstalled draft) and
  [`win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0.json)
  (qualified alternative; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; rollback
  [`win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0.json))
- RTX 4090 + RTX 3090, `rtx3090-win-a`:
  [`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0.json)
  (**current**; pins manual `strata.setup_args.layer_split: "24"`, `strata.trim_stage_weights: true`, `--trim-stage-weights`, `strata.ple_io: "direct"`, `--ple-io direct`, and `strata.engine_env` `sm86_table` + `gdn_stack`, qualified on 2026-11-03 after the owner overrode its `w1` 512/512 single-request A/B miss at `1.039` vs `>= 1.05`; rollback
  [`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0.json);
  the `v0.2.8` stock-residency roles draft stays a measurement-only draft)
- Mac Studio client:
  [`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0`](routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0.json)
  (rollback
  [`client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0`](routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0.json))

What these ledgers establish, and what they do not:

- **New-release discovery is separate.** The [v0.2.9 campaign](releases/campaigns/v0.2.9.json) (opened with
  `scripts/campaign.py open --release v0.2.9 --omp-tag v18.15.0`) is complete across all five rows — the PRO
  batch-MTP + PLE-direct base variant, RTX 5090 262K base and 131K alternative, pair split-24 trim + PLE-direct
  base variant, and base Studio→PRO route — as are the [v0.2.8](releases/campaigns/v0.2.8.json),
  [v0.2.7](releases/campaigns/v0.2.7.json), [v0.2.3](releases/campaigns/v0.2.3.json) and
  [v0.2.1](releases/campaigns/v0.2.1.json) campaigns; the next campaign drafts each lane from the newest qualified
  profile across its listed variant families in `scripts/campaign.py` `LANES` (breaking same-release ties by lane
  order; `610be03`, `f3fed60`). See the
  [campaign lifecycle and prepared host commands](docs/OPERATIONS.md#release-campaigns-op10-discovery--op11-host-owned-qualification).
- **Ledger counts and receipts.** Each current local ledger has 21 pass and 3 not applicable; G22 (images), G23
  (remote clients) and G25 (runtime comparison) are not applicable to these local, text-only profiles. Real-host
  `v0.2.9` receipts cite tooling commits `d0a1254` on the pair `env86g` current chain (with operator receipts
  `1f699b4` binding `G00` to `f3fed60`, `G01–G05` to the 903-test host-free suite at `6b972fa`, and `G06` to green PR
  #74 [CI run 41597184710](https://github.com/alphastorm/omp-strata/actions/runs/41597184710) at `6b972fa`) and
  `acd7549` on the PRO `kvvram-envpg` current and RTX 5090 262K
  `kvvram-kvgrow-envg` default chains (with operator receipts `343fab3` binding `G00` to `f3fed60`, `G01–G05` to the
  903-test host-free suite at `d05f660`, and `G06` to green PR #73
  [CI run 41499865044](https://github.com/alphastorm/omp-strata/actions/runs/41499865044) at `d05f660`;
  [2026-11-02 tuning measurements](docs/MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150)),
  alongside `6fec79d` on the PRO and RTX 5090 262K `v0.2.9` base rollbacks and the RTX 5090 131K alternative and
  `8002c77` on the pair split-24 trim + PLE-direct `v0.2.9` base rollback after admitting engine `0.1.55`'s stage order (with
  operator receipts `276bbaa` binding `G00` to `6fec79d`, `G01–G05` to the 866-test host-free suite at `2ccea3c`, and
  `G06` to green PR #72 [CI run 41457827645](https://github.com/alphastorm/omp-strata/actions/runs/41457827645) at
  `2ccea3c`; [2026-11-02 windows measurements](docs/MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150),
  [decision](docs/DECISION.md)). Cold-start version A/B against `v0.2.8` (`A B B A A B`, `A = v0.2.8`, `B = v0.2.9`)
  showed aggregate output `tok/s` `B/A` ratios of `0.996–1.012` on the PRO, `0.999–1.001` on the RTX 5090 262K and
  `1.003` on the pair. Scored G24 passed 16/18 on the PRO `kvvram-envpg` current profile (pilot 5/6; `v0.2.9` base
  rollback: 16/18, pilot 5/6; `v0.2.8` batch-MTP: 15/18, pilot 6/6), 17/18 on the RTX 5090 262K `kvvram-kvgrow-envg`
  default (pilot 5/6; `v0.2.9` base rollback: 16/18, pilot 6/6; `v0.2.8`: 17/18, pilot 6/6), 14/18 on the RTX 5090 131K
  alternative (pilot 5/6; `v0.2.8` rollback: 18/18, pilot 5/6), and 15/18 on the pair `env86g` current profile
  (pilot 5/6; `v0.2.9` base rollback: 15/18, pilot 5/6; `v0.2.8`: 15/18, pilot 5/6), with scored batch walls of 631 s on the PRO (`v0.2.9` base rollback:
  576 s; `v0.2.8`: 635 s), 791 s on the RTX 5090 262K default (`v0.2.9` base rollback: 840 s; `v0.2.8`: 865 s), 763 s on
  the 131K alternative (`v0.2.8`: 968 s), and 822 s on the pair (`v0.2.9` base rollback: 975 s; `v0.2.8`: 942 s; batch walls, not isolated
  decode latency).
  `v0.2.9` server profiles; all receipts and task failures remain published.
- **The PRO and RTX 5090 262K default pin stock engine environment stacks and KV in VRAM.** On `rtxpro6000-win-a`, in
  addition to `strata.ple_io: "direct"` (`--ple-io direct`, [OPERATIONS.md](docs/OPERATIONS.md#stock-ple-direct-reads))
  and `strata.batch_mtp: true` (`--batch-mtp`, [OPERATIONS.md](docs/OPERATIONS.md#stock-per-slot-mtp)), the current
  `kvvram-envpg` profile pins `strata.engine_env` with stock `serve/server.py`'s Linux-only nine-switch `parallel_stack`
  and two-switch `gdn_stack` ([UPSTREAM.md](docs/UPSTREAM.md#stock-engine-environment-v029--0155)) and
  `setup_args.kv_streaming: "off"` (`--kv-streaming off`, keeping KV in VRAM without `--kv-resident 32768`; 78 GiB start
  floor). Across three paired cold starts against its `v0.2.9` base rollback, total output at 1,000-token prompts rose
  **+11.3%** at 1 request, **+29.3%** at 2 and **+34.8%** at 4 (`4 × 32K` **+13.1%**), single-request TTFT p95 dropped
  **-19.6%**, decode stayed at 0% (depth 0) to **+2.2%** (100K) with byte-identical greedy output in every block,
  restart readiness dropped to **31.0-31.3 s** (G16 31.0 s, G20 31.0 s, G21 31.3 s; G15 kill recall 44.7-45.4 s;
  `v0.2.9` base rollback: 35.1-39.7 s), and G10 measured **129.57 GiB** available RAM and **83.35 GiB** Windows commit
  headroom of **219.70 GiB** (`v0.2.9` base: 112.58 / 81.28 GiB; GPU 74,906 MiB vs 59,712 MiB) with the 8,192 MiB
  automatic conversation cache enabled. On `rtx5090-win-a`, the 262K `kvvram-kvgrow-envg` default pins
  `strata.engine_env` `gdn_stack`, `setup_args.kv_streaming: "off"` (lowering the available-RAM start floor from 36 GiB
  to **34 GiB**) and `strata.kv_grow: true` (`--kv-grow`), cutting cold TTFT **-8.6%** at 32K and **-8.9%** at 100K
  (100K decode **-2.7%**, `0.973`, above its `0.97` bar; 512/512-token single request **+2.5%**, 32K **+8.4%**) and sizing a
  **4,352 MiB** automatic conversation cache in G19 (vs 3,072 MiB on the `v0.2.9` base rollback; G10 13.35 GiB available
  RAM and 20.10 GiB commit headroom of 85.15 GiB vs 10.55 / 17.55 GiB). GDN tensor-core numerics are not bit-exact
  upstream, and engine env pins are reviewed per engine release (`ENGINE_ENV_REVIEWED_ENGINES`, engine `0.1.55` only),
  so the next engine release needs a fresh review.
- **The pair keeps stock roles with the RTX 4090 as Main, pins manual split 24 with stage weight trim, keeps direct PLE reads, and pins the engine's `sm_86` table and GDN stack.**
  On `rtx3090-win-a`, engine `0.1.55`'s stage order was admitted at `8002c77` after all six pair A/B starts parsed
  complete: `--gpu-roles 0=main,1=helper` stages the RTX 3090 (GPU 1) first on layers 0-23 and the RTX 4090 (GPU 0) last
  on layers 24-47 (`--pipeline-windows 2` decode-capable). Because the engine builds CUDA0's arena before an automatic
  split is known, `--trim-stage-weights` under `"auto"` trims only later stages; the current profile therefore pins
  stock setup's manual split at the layer the automatic planner chose (`strata.setup_args.layer_split: "24"`) together
  with `strata.trim_stage_weights: true` (`--trim-stage-weights`,
  [OPERATIONS.md](docs/OPERATIONS.md#stock-stage-weight-trim)), so each card loads only its own stage's dense weights
  (771 and 988 MiB instead of 1,466 and 2,019 MiB), growing each card's expert cache by **1.8 GiB** (**19.15 GiB** on
  the RTX 3090 and **17.76 GiB** on the RTX 4090 vs 17.35 and 16.01 GiB without trim), cutting 32K-100K time to first
  token (TTFT) **12%** and G17's near-limit task wall to **59.8 s** on the current `v0.2.9` `env86g` profile (60.4 s on
  the `v0.2.9` base rollback and 60.8 s on `v0.2.8` split-24 trim vs 67.0 s on `v0.2.8` `roles-pledirect`). It keeps
  `strata.ple_io: "direct"` (`--ple-io direct`), preserving **27.77 GiB** G10 Windows commit headroom of a
  **135.69 GiB** limit (**65.68 GiB** available RAM; 27.74 GiB commit headroom and 65.67 GiB available RAM on the
  `v0.2.9` base rollback) and the
  **8,192 MiB** automatic conversation cache (versus 4,864 MiB and 106-112 s to ready on the measurement-only `v0.2.8`
  stock-residency draft, where [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)'s fix gave the
  26.8 GiB PLE lock back on both starts). The current `v0.2.9` `env86g` profile also pins the engine's `sm_86` default
  table (`sm86_table`, skipped by default on the mixed `sm_86` + `sm_89` pair;
  [Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313)) and stock `gdn_stack` (`GDN_STACK_CUDA`)
  through `strata.engine_env`: in three paired cold starts against its `v0.2.9` base rollback, cold decode rose **+6.5%**
  at 8K (`1.065`) and **+11.4%** at 100K (`1.114`) and every TTFT bar passed (`0.948–0.996`), while the end-to-end `w1`
  512/512-token single-request bar missed (`1.039` vs `>= 1.05`); after the owner overrode that one bar (`"Yes approved:
  Yes, if you approve an override. There's nothing in the pair profile to fix."`), the requalification chain at `d0a1254`
  passed all 14 measured gates (G16 / G20 / G21 restart readiness **43.5 / 43.6 / 43.9 s** vs 55.4 / 55.5 / 55.6 s on
  the `v0.2.9` base rollback; G24 15/18, pilot 5/6, scored batch wall **821.8 s** vs 974.9 s). The `v0.2.8`
  stock-residency draft, the held `v0.2.7` roles draft (PLE in RAM), the unmeasured `v0.2.7` default-split draft, and
  the `v0.2.3` default and split-32 drafts stay unqualified ([decision](docs/DECISION.md)).
- **Remote use.** Through the tunnel (G23 on 2026-11-02 at `acd7549`), a missing key was refused before launch and
  a wrong key got 401; health RTT was 5.5-6.3 ms and stream TTFT **0.172 s** (vs 0.206 s on the `v0.2.9` base rollback
  route); a tunnel drop failed the turn in flight with the prior transcript preserved, and nonce recall passed after
  tunnel reopen (0.81 s), client restart (0.67 s) and verified server restart (1.40 s) ([`docs/REMOTE.md`](docs/REMOTE.md)).
- **Not supported.** Images, servers on other operating systems, durable engine state, multiple tenants, fleets
  (no fleet route is published), the upstream DeepSeek V4.1-Flash family (a separate `strata-dsv41` engine, not an
  `omp-strata` profile family) and other client routes; every profile other than the qualified ones above remains
  a draft or a rollback installation. The PRO `UD-IQ4_XS` and `NVFP4-QAD` model candidates (and their routes) stay
  comparison-only drafts while their prepared 30-task Terminal-Bench comparison has not run, and the RTX 5090
  `kvvram-kvgrow` fallback stays an uninstalled draft.

### Current profile results

Per gate, for the four current local profiles above
([2026-11-02 tuning measurements](docs/MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150),
[2026-11-02 windows measurements](docs/MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150),
[decision](docs/DECISION.md)).

| Area | RTX PRO 6000, batch-MTP + PLE direct + KV VRAM + envpg (2026-11-02) | RTX 5090, 262K default, KV VRAM + KV grow + envg (2026-11-02) | RTX 5090, 131K alternative (2026-11-02) | RTX 4090 + RTX 3090, roles + split 24 + trim + PLE direct + env86g (2026-11-03) |
|---|---|---|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass: 3/3 tracer runs | pass: 3/3 tracer runs | pass: 3/3 tracer runs | pass: 3/3 tracer runs |
| Live prefix reuse in a session (lost on engine restart) | pass: 12 continuations, engine-reported | pass: 13 continuations, engine-reported | pass: 14 continuations, engine-reported | pass: 12 continuations, engine-reported |
| Interleaved conversations | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 8,192 MiB cache, 34 parks), not an exact-output claim | pass: A resumes after B; 46 uncached tokens on the controlled continuation (engine's 4,352 MiB cache, 23 parks with Docker Desktop/WSL stopped), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 3,840 MiB cache, 31 parks in the Docker Desktop/WSL-stopped window), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 8,192 MiB cache, 23 parks), not an exact-output claim |
| Requests at once | up to 4, decoded together with per-slot MTP (`--batch-mtp`) | one at a time | one at a time | one at a time |
| Loopback, API key (including `/status`, `/v1/telemetry` and `/tool-media/` on `v0.2.9`), fail-closed client, local-only routing, with an egress guard for OMP's startup catalog fetch | pass | pass | pass | pass |
| Engine or client restart, then continue from OMP's transcript (an engine restart re-prefills it; no state restoration) | pass (readiness 31.0-31.3 s; G16 31.0 s, G20 31.0 s, PLE on direct SSD reads, KV in VRAM; v0.2.9 base rollback: 35.1-39.7 s) | pass with Docker Desktop/WSL stopped (readiness 18.6-18.9 s; G16 18.7 s, lowest available RAM 8.61 GiB; v0.2.9 base rollback: 16.6-16.8 s) | pass (readiness 16.1-26.8 s; G16 26.8 s, G20 16.1 s, lowest available RAM 7.52 GiB) | pass (readiness 43.5-43.9 s; G16 43.5 s, G20 43.6 s, G21 43.9 s, PLE on direct SSD reads; v0.2.9 base rollback: 55.4-55.6 s) |
| Context window (262,144 tokens on the RTX PRO 6000, RTX 5090 default and pair; 131,072 on the RTX 5090 alternative): exact limit, near-limit tool turns, explicit overflow (G17) | pass (near-limit task 25.1 s vs 29.2 s on `v0.2.9` base) | pass (near-limit task 30.6 s vs 35.1 s on `v0.2.9` base) | pass | pass (near-limit task 59.8 s vs 60.4 s on `v0.2.9` base) |
| OMP compaction (reduced threshold and production long session, G18) | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off |
| Cancelling a *queued* request | pass, with all four slots generating | pass | pass | pass |
| Tool call cut off mid-arguments (G04) | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call |
| Six-task coding evaluation, 18 scored attempts (G24) | 16/18 (tool-loop 1/3, others 3/3; pilot 5/6, batch wall 631 s; `v0.2.9` base rollback 16/18, pilot 5/6, 576 s) | 17/18 (tool-loop 2/3, others 3/3; pilot 5/6, batch wall 791 s; `v0.2.9` base rollback 16/18, pilot 6/6, 840 s) | 14/18 (tool-loop 0/3, bugfix-a 2/3, others 3/3; pilot 5/6, batch wall 763 s) | 15/18 (tool-loop 0/3, others 3/3; pilot 5/6, batch wall 822 s; `v0.2.9` base rollback 15/18, pilot 5/6, 975 s) |
| Guarded install and QUICKSTART example alongside earlier tuples (G26) | pass on an already prepared root (install 21.3 s, start 53.1 s; first install on v0.2.8 took 1,063.2 s) | pass on an already prepared root (install 12.4 s, start 23.9 s; first install on v0.2.8 took 365.6 s) | pass on an already prepared root (install 12.0 s, start 35.4 s; first install on v0.2.8 took 297.8 s) | pass on an already prepared root (install 29.7 s, start 70.4 s; `v0.2.9` base rollback 25.9 s and 54.5 s; first install on v0.2.8 took 820.3 s) |
<details>
<summary><strong>Earlier qualified profiles and rollbacks</strong></summary>

Every profile and client route ledger is listed in [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md); the owner's
qualification decisions, retained failures, the G15 probe correction, the G16 predicate fix, the G18 fixture fix
and the OMP speculative-compaction setting are in [`docs/DECISION.md`](docs/DECISION.md), with full figures in
[`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md).

- **2026-11-02 (morning) — Strata `v0.2.9` + OMP `18.15.0` initial PRO, RTX 5090 262K, pair and Studio route profiles:**
  current rollbacks on the PRO (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json);
  G24 16/18, pilot 5/6, restart readiness 35.1-39.7 s, 112.58 GiB available RAM and 81.28 GiB G10 commit headroom), the
  RTX 5090 262K default (`win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/qualification.json); G24 16/18, pilot 6/6,
  36 GiB start floor, 3,072 MiB cache, restart readiness 16.6-16.8 s), the pair
  (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json);
  G24 15/18, pilot 5/6, restart readiness 55.4-55.6 s, 19.15 / 17.76 GiB expert caches, 65.67 GiB available RAM and
  27.74 GiB G10 commit headroom), and the Mac Studio client route
  ([`0.2.9 batch-MTP route`](routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0.json),
  [ledger](releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/qualification.json); stream TTFT
  0.206 s); [measurements](docs/MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150) and
  [decision](docs/DECISION.md#update-2026-11-02-strata-v029-with-omp-18150-qualifies-on-every-host-and-the-studio-route).
- **2026-10-30 and 2026-10-31 — Strata `v0.2.8` + OMP `18.14.0` (`rtxpro6000-win-a`, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair, Mac Studio route):**
  current rollback on the RTX 5090 131K alternative, and earlier qualified history on the PRO, the RTX
  5090 262K default, the pair and the Mac Studio route: on the PRO
  (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json);
  G24 15/18, pilot 6/6, restart readiness 35.5-51.5 s; alongside the earlier qualified PLE-direct-only alternative
  `win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json), G24
  15/18, pilot 6/6, restart readiness 35.0-51.4 s, and the initial 2026-10-30 `slots4-parking` profile
  `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/qualification.json), G24 16/18,
  pilot 5/6, restart readiness 73.6-88.2 s), the RTX 5090 262K default
  (`win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/qualification.json); G24 17/18, pilot 6/6,
  G10 rerun at `f9e8c74` retained beside main-chain listener failure on Windows build 26300.9818) and 131K alternative
  (`win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/qualification.json); G24 18/18, pilot 5/6,
  G10 rerun at `f9e8c74`), the pair split-24 trim + PLE-direct profile
  (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json);
  G24 15/18, pilot 5/6, 19.15 / 17.76 GiB expert caches, 27.8 GiB G10 commit headroom; alongside the initial 2026-10-30
  `roles-pledirect` profile
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json),
  G24 15/18, pilot 5/6, 17.35 / 16.01 GiB expert caches, 27.9 GiB commit headroom), and the Mac Studio client route
  ([`0.2.8 batch-MTP route`](routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0.json),
  [ledger](releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0/qualification.json), alongside the
  initial [`0.2.8 slots4-parking route`](routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json),
  [ledger](releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/qualification.json));
  [2026-10-31 measurements](docs/MEASUREMENTS.md#stock-tuning-pins-on-strata-v028-2026-10-31-stock-omp-18140),
  [2026-10-30 measurements](docs/MEASUREMENTS.md#strata-v028-windows-2026-10-30-stock-omp-18140) and
  [decision](docs/DECISION.md#update-2026-10-31-stock-v028-tuning-profiles-and-the-studio-batch-mtp-route-qualify).
- **2026-10-28 — Strata `v0.2.7` + OMP `18.13.2` (`rtxpro6000-win-a`, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair PLE-direct, Mac Studio route):**
  earlier qualified history across all lanes: on the PRO
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2/qualification.json); G24
  15/18), the RTX 5090 262K default
  ([ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/qualification.json); G24 16/18, afternoon
  rerun with Docker Desktop/WSL stopped retained beside morning failures), the RTX 5090 131K alternative
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2/qualification.json); G24 16/18, G15 rerun
  retained beside main-run failure), the RTX 4090 + RTX 3090 pair in its PLE-direct stock-roles variant (`--ple-io direct`,
  8,192 MiB automatic conversation cache, 27.3 GiB G10 commit headroom;
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/qualification.json);
  G24 17/18; the `v0.2.7` roles draft with PLE in RAM stays held on 1.03 GiB commit headroom,
  [Strata#4518](https://github.com/Niko1221/Strata/issues/4518)), and the Mac Studio client route
  ([`0.2.7 route`](routes/client-rtxpro6000-262k-strata0.2.7-omp18.13.2.json),
  [ledger](releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/qualification.json));
  [measurements](docs/MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132) and
  [decision](docs/DECISION.md#update-2026-10-28-afternoon-the-pairs-ple-direct-and-rtx-5090-262k-strata-v027-profiles-qualify).
- **2026-10-23 — Strata `v0.2.3` + OMP `18.12.6` (`rtxpro6000-win-a`, `rtx5090-win-a` 131K and 262K, `rtx3090-win-a` pair roles, Mac Studio route):**
  earlier qualified history on the PRO
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6/qualification.json); G24
  17/18, G10 rerun retained beside main-run deep-verification count), the RTX 5090 131K profile
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.3-omp18.12.6/qualification.json); G24 17/18, G20
  rerun retained beside main-run failure) and 262K profile
  ([ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6/qualification.json); G24 14/18, G19
  rerun retained beside main-run failure; both `v0.2.3` RTX 5090 integration roots were removed on 2026-11-02 with the
  owner's approval, while their ledgers and receipts stay in the repository), the RTX 4090 + RTX 3090 pair in its
  stock-roles variant with the engine's 8 GiB automatic conversation cache
  ([ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6/qualification.json);
  G24 14/18, G18 rerun retained beside main-run failure), and the Mac Studio client route
  ([`0.2.3 route`](routes/client-rtxpro6000-262k-strata0.2.3-omp18.12.6.json),
  [ledger](releases/client-rtxpro6000-262k-strata0.2.3-omp18.12.6/qualification.json));
  [measurements](docs/MEASUREMENTS.md#strata-v023-windows-2026-10-23-stock-omp-18126) and
  [decision](docs/DECISION.md#update-2026-10-23-strata-v023-with-omp-18126-qualifies-on-every-host).
- **2026-10-21 — Strata `v0.2.1` + OMP `18.10.1` (`rtxpro6000-win-a`, `rtx5090-win-a` 131K and 262K opt-in, `rtx3090-win-a` pair, Mac Studio route):**
  earlier qualified history across all lanes (v0.2.1 integration roots on the hosts were removed on 2026-10-28, while
  their ledgers and receipts stay in the repository): on the PRO
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1/qualification.json); G24
  17/18), the RTX 5090 131K default
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.1-omp18.10.1/qualification.json); G24 17/18, G17 and
  G18 reruns retained beside main-run failures), the RTX 5090 262K opt-in
  ([ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.1-omp18.10.1/qualification.json); G24 15/18), the pair
  in its default automatic-split variant
  ([ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.1-omp18.10.1/qualification.json);
  G24 16/18, G17 rerun retained beside main-run failure), and the Mac Studio client route
  ([`0.2.1 route`](routes/client-rtxpro6000-262k-strata0.2.1-omp18.10.1.json),
  [ledger](releases/client-rtxpro6000-262k-strata0.2.1-omp18.10.1/qualification.json));
  [measurements](docs/MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-21-stock-strata-v021-stock-omp-18101) and
  [decision](docs/DECISION.md#update-2026-10-21-strata-v021-with-omp-18101-qualifies-on-every-host).
- **2026-10-14 (262K opt-in 2026-10-15) — Strata `v0.1.44.1` + OMP `18.10.1` (`rtxpro6000-win-a`, `rtx5090-win-a` 131K and 262K opt-in, Mac Studio route):**
  earlier qualified history on the PRO
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1/qualification.json)), the
  RTX 5090 131K default
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1/qualification.json)), the RTX 5090
  262K opt-in
  ([ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1/qualification.json); failed G26
  receipt retained beside passing same-root rerun), and the Mac Studio client route
  ([`0.1.44.1 route`](routes/client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1.json),
  [ledger](releases/client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1/qualification.json)); the pair's `v0.1.44.1`
  release stays a draft (not qualified, not a rollback) after its K=45 split regression;
  [262K opt-in measurements](docs/MEASUREMENTS.md#rtx-5090-coder-262k-qualified-opt-in-2026-10-15) and
  [decision](docs/DECISION.md#update-2026-10-14-strata-v01441-with-omp-18101-qualifies-on-the-pro-and-rtx-5090-the-pair-stays-on-v01431).
- **2026-10-13 — Strata `v0.1.43.1` + OMP `18.10.1` (`rtx3090-win-a` pair, `rtxpro6000-win-a`, `rtx5090-win-a`, Mac Studio route):**
  earlier qualified history on the RTX 4090 + RTX 3090 pair at 262K and parking
  ([ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1/qualification.json);
  G24 15/18, including one malformed-arguments counter on its unsuccessful third multifile-regression attempt),
  the PRO
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1/qualification.json)), the
  RTX 5090 ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43.1-omp18.10.1/qualification.json)), and
  the Mac Studio client route
  ([`0.1.43.1 route`](routes/client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1.json));
  [measurements](docs/MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-13-stock-strata-v01431-stock-omp-18101).
- **2026-10-12 — Strata `v0.1.43` + OMP `18.10.1` (`rtx3090-win-a` pair, `rtxpro6000-win-a`, `rtx5090-win-a`, Mac Studio route):**
  earlier qualified history on the RTX 4090 + RTX 3090 pair at 262K and parking
  ([ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43-omp18.10.1/qualification.json)),
  the PRO
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1/qualification.json)), the
  RTX 5090 ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43-omp18.10.1/qualification.json); failed G18
  receipt retained beside passing full rerun), and the Mac Studio 262K route;
  [measurements](docs/MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-12-stock-strata-v0143-stock-omp-18101).
- **2026-10-11 — Strata `v0.1.42` + OMP `18.8.9`, pair at 262K with parking (`rtx3090-win-a`):** earlier
  qualified history, display on the RTX 4090
  ([ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9/qualification.json),
  [measurements](docs/MEASUREMENTS.md#earlier-qualification-262k-with-stock-conversation-parking-display-on-the-rtx-4090-2026-10-11)).
- **2026-10-11 — Strata `v0.1.42` + OMP `18.8.9`, pair at 131K with display on RTX 4090 (`rtx3090-win-a`):**
  earlier qualified history; retains its original startup refusal, pre-G16 degraded status and recovery, and
  failed G26 receipt beside the passing repeat
  ([ledger](releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9/qualification.json),
  [measurements](docs/MEASUREMENTS.md#rtx-4090--rtx-3090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889)).
- **2026-10-11 — Strata `v0.1.42` + OMP `18.8.9`, pair at 131K with display on RTX 3090 (`rtx3090-win-a`):**
  earlier qualified predecessor; requires moving the display back to the RTX 3090
  ([ledger](releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9/qualification.json),
  [measurements](docs/MEASUREMENTS.md#rtx-4090--rtx-3090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889)).
- **2026-10-11 — Strata `v0.1.42` + OMP `18.8.9` (`rtxpro6000-win-a` at 262K, `rtx5090-win-a` at 131K, Mac Studio 262K route):**
  earlier qualified history on the PRO
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9/qualification.json)), the
  RTX 5090 ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.42-omp18.8.9/qualification.json)), and the
  Mac Studio 262K route;
  [measurements](docs/MEASUREMENTS.md#rtx-pro-6000-at-262k-and-rtx-5090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889).
- **2026-10-10 — Strata `v0.1.41` + OMP `18.8.6`, PRO at 262K (`rtxpro6000-win-a`):** earlier qualified history;
  retains its first G18 failure from 131K-sized fixtures beside the passing window-sized rerun
  ([ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json),
  [measurements](docs/MEASUREMENTS.md#rtx-pro-6000-at-262k-every-gate-2026-10-10-stock-strata-v0141-stock-omp-1886)).
- **2026-10-09 — Strata `v0.1.41` + OMP `18.8.6`, RTX 5090 at 131K (`rtx5090-win-a`):** earlier qualified history
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.41-omp18.8.6/qualification.json),
  [measurements](docs/MEASUREMENTS.md#rtx-5090-every-gate-2026-10-09-stock-strata-v0141-stock-omp-1886)).
- **2026-10-08 — Strata `v0.1.41` + OMP `18.8.6`, PRO at 131K (`rtxpro6000-win-a`, plus Mac Studio 131K route 2026-10-09):**
  earlier qualified history
  ([ledger](releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json),
  [measurements](docs/MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-08-stock-strata-v0141-stock-omp-1886),
  [`docs/REMOTE.md`](docs/REMOTE.md)).
- **2026-10-08 — Strata `v0.1.40.3` + OMP `18.8.4` (`rtxpro6000-win-a`, `rtx5090-win-a`, single-card `rtx3090-win-a`):**
  earlier qualified history on the PRO at 131K (G16 predicate-fix rerun;
  [ledger](releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4/qualification.json)) and
  the RTX 5090
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json)); the single-card
  RTX 3090 Coder profile
  ([ledger](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json); 3/3 tracer, 16/16
  live prefix reuse, 15/18 evaluation) stays qualified for single-card hosts, but is not a rollback while both
  cards are installed because single-card profiles name GPU 0, now the RTX 4090;
  [measurements](docs/MEASUREMENTS.md#three-gpus-every-gate-2026-10-08-stock-strata-v01403-stock-omp-1884).
- **2026-10-07 — Strata `v0.1.40.3` + OMP `18.8.3`, PRO at 131K with slots and parking (`rtxpro6000-win-a`):**
  earlier qualified history
  ([ledger](releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3/qualification.json)).
- **2026-10-07 — Strata `v0.1.40.2` + OMP `18.8.0`, PRO at 131K without slots and parking (`rtxpro6000-win-a`):**
  earlier qualified history; first profile to turn OMP's speculative compaction off
  ([ledger](releases/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0/qualification.json),
  [`docs/UPSTREAM.md`](docs/UPSTREAM.md) OMP item 12).
- **2026-10-02 (G15 repeats 2026-10-03) — Fourth tuple, Strata `v0.1.34` + OMP `18.4.10`, Coder IQ1_M at 131K:**
  first tuple to pass G04 on stock releases; qualified on the RTX 5090
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json)), the single-card
  RTX 3090 ([ledger](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json); not a
  rollback while both cards are installed), and the RTX 4090 in 32 GiB stock low-RAM mode
  ([ledger](releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10/qualification.json); failed
  reduced-threshold G18 probe retained beside passing rerun).
- **2026-09-30 to 2026-10-01 — Earlier unqualified rollback installations (G04 failed before both upstream fixes shipped):**
  first RTX 5090 candidate on Strata `v0.1.27` + OMP `18.4.0`
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k/qualification.json)), second RTX 5090 candidate on Strata
  `v0.1.30` + OMP `18.4.6`
  ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/qualification.json)), and third-tuple
  Strata `v0.1.31` + OMP `18.4.8` on the 64 GiB RTX 3090
  ([ledger](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/qualification.json)) and 32 GiB low-RAM
  RTX 4090 ([ledger](releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/qualification.json)).
- **2026-10-02 to 2026-10-06 — Unqualified comparison and variant-selection drafts (gates not run, except the G25 comparisons):** Strata
  `v0.1.36` + OMP `18.4.12` (128 GB RTX 3090 model, calibration and 262K/524K context probes; client and fleet
  route drafts), Strata `v0.1.38` + OMP `18.5.0` (G25 same-host NInfer comparisons on the RTX 5090, 192 GB RTX
  4090 and RTX 3090; [`docs/G25.md`](docs/G25.md)), and Strata `v0.1.39` / `v0.1.40.1` + OMP `18.5.0` (RTX PRO
  6000 model and Terminal-Bench screens); see [`docs/DECISION.md`](docs/DECISION.md) and
  [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md).

</details>

## Bounded experiments (comparison-only)

`scripts/experiment_loop.py` freezes two checked-in RTX 5090 or RTX PRO 6000 profiles, their artifact/model/template/configuration
identities, harness file digests, workload, repetitions, stop limits and the predecessor restoration target.
It does not qualify a release, change defaults or route development work to a local model.

```sh
python3 scripts/experiment_loop.py plan \
  --baseline win11-rtx5090-coder-iq1m-131k-strata0.2.3-omp18.12.6 \
  --candidate win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6 \
  --rationale "Compare the separately qualified opt-in context without changing model or quantization" \
  --repetitions 3 --out <private-manifest.json>
python3 scripts/experiment_loop.py report --directory releases/experiments/<key>
python3 scripts/experiment_loop.py next --directory releases/experiments/<key> \
  --candidate <another-checked-in-5090-profile-id>
```

`plan` refuses identities already recorded under `releases/experiments/`, including blocked or failed trials.
Changing repetitions, workload or prose does not evade the source/model/quant/configuration dedupe key.
`next` writes exactly one validated proposal to `queue.json`; it **never executes the queue**.
An authorized retry of a blocked trial uses `plan --baseline ... --candidate ... --retry-of <blocked-key>`.
The referenced receipt must be either an unstarted blocked trial or a failed trial with a successfully restored
predecessor; it remains untouched, and the retry has a distinct append-only key. Completed trials cannot retry.
`--resume-candidate` can reuse a failed trial's complete baseline only when no candidate repetition started and
the workload/repetition count still match. Every reused measurement names its source receipt; it is not a new run.
`--host-profile rtxpro6000-win-a` selects the PRO host contract, requiring both profiles to name that GPU;
it never rewrites a 5090 profile's identity. The comparison-only PRO Coder profiles keep the same model and
131K/262K contexts, with their own host floors and stock hybrid-CPU worker setting; neither is qualified.

For an explicitly authorized exclusive window, sync the frozen tooling to the GPU host and launch
`python scripts/experiment_loop.py run --manifest <private-manifest.json> --bindings <private-bindings.json>`
through `scripts/windows/launch-detached.ps1`, not a foreground SSH process. Bindings contain
`roots.baseline`, `roots.candidate` (distinct integration roots) and `host_lock_id`, the same private host
identifier used by `eval_taskset`'s `HOST_LOCKS` on that machine. Keep a corresponding client-side host claim
for the whole detached window if other client schedulers share this host: PID-file locks are machine-local,
not a distributed lease. Poll the four JSON records with bounded waits; a disconnect is not permission to
start another worker or delete a claim. An existing claim, including an ambiguous stale one, is refused.
`python scripts/experiment_loop.py preflight --manifest <file> --bindings <file>` prints the loop's admission
JSON without installing or starting either arm. Display-attached profiles tolerate graphics clients under the
existing idle-VRAM ceiling, but never tolerate foreign compute processes.

Admission requires the predecessor's installed fingerprint, an idle GPU, no competing tenant or occupied
server port, and RAM/disk above both profiles' floors. A currently serving predecessor must first be
released by its owner; the experiment will not evict it to satisfy admission. The candidate installs in
isolation using existing pinned lifecycle tooling. Both arms run `perf_probe.py` for every repetition;
disk/owned-GPU checks continue during probes. The wall/failure limits stop new work and terminate the
owned probe tree. Restoration runs in `finally` with a separate bounded safety budget: stop owned arms,
start the predecessor, then require G10 and authenticated healthy status. Raw child logs stay private.
Each public write goes through the existing publication scrubber; missing measurements remain missing.
After releasing the baseline, a read-only RAM-settle check polls at five-second intervals for at most 90 seconds
inside the trial's existing wall budget. It never lowers either profile's floor or changes host services.

The probe records TTFT, server-reported prefill/decode rates and two-request FIFO bounds where available.
It does **not** score task correctness (`eval_taskset.py` remains the separate macOS sandboxed task evaluator)
or expose true inter-token latency. Reports therefore hold adoption pending paired task-quality evidence,
never select on throughput alone, and refuse `--engine-only` when model, quantization, template, protocol,
harness or configuration changed. `record-blocked --manifest <file> --observation <file>` can preserve a
read-only failed preflight without starting any runtime; it cannot authorize a run or manufacture a
restoration pass. The initial 262K trial was blocked by occupancy and available RAM. The stale queue's
predecessor-engine proposal was not executed: both arms retain Strata 0.1.44.1 and OMP 18.10.1.

**Authorized context comparison, 2026-10-16 (three repetitions per arm).** Both hosts completed the
Coder IQ1_M 131K-versus-262K workload, passed predecessor restoration G10, then stopped the experiment
roots and restored the same original serving containers with healthy endpoints. The RTX 5090 baseline
comes from the preserved failed attempt: an externally reactivated owned CPU encoder exhausted the
36 GiB admission floor before the candidate started. Its candidate-only retry explicitly references
the original baseline measurements; the temporary encoder pause was removed and its health restored.
That host-state difference makes small deltas descriptive, not a causal performance claim.

Values below are **median / p95**, with p95 linearly interpolated across the three repetitions.
TTFT/prefill/decode use the 102,400-token unique-prefix samples; FIFO bounds use the separate two-request
queue probe. Full depth and warm-repeat results, preflight, failures, exact scrubbed execution references
and restoration identities are in the
[RTX 5090 receipt](releases/experiments/eea79d52bbfdcbac68696b82e48081ef371baee9d110205c497d2bcae47a2a1a/summary.json)
and [RTX PRO 6000 receipt](releases/experiments/c32b665f029fbc093477a9b6570784998c4dfe50a1cc0797c8b5c256d04d79ff/summary.json).

| Host | Metric | 131K baseline | 262K candidate |
|---|---|---:|---:|
| RTX 5090 | TTFT, ms | 13,718.77 / 13,770.88 | 13,696.39 / 13,697.49 |
| RTX 5090 | Prefill, tokens/s | 7,503.26 / 7,516.30 | 7,521.34 / 7,521.78 |
| RTX 5090 | Decode, tokens/s | 229.02 / 238.38 | 225.12 / 238.33 |
| RTX 5090 | FIFO lower bound, ms | 2,261.47 / 2,262.14 | 2,233.47 / 2,277.33 |
| RTX 5090 | FIFO upper bound, ms | 2,331.94 / 2,359.19 | 2,302.83 / 2,360.18 |
| RTX PRO 6000 | TTFT, ms | 12,522.93 / 12,543.47 | 12,558.12 / 12,568.19 |
| RTX PRO 6000 | Prefill, tokens/s | 8,221.66 / 8,256.22 | 8,193.31 / 8,221.03 |
| RTX PRO 6000 | Decode, tokens/s | 215.20 / 228.64 | 216.39 / 234.65 |
| RTX PRO 6000 | FIFO lower bound, ms | 2,371.90 / 2,375.97 | 2,347.23 / 2,358.74 |
| RTX PRO 6000 | FIFO upper bound, ms | 2,437.83 / 2,467.51 | 2,374.17 / 2,418.26 |

These probes stop below the baseline's context limit and do not measure task quality. No existing profile,
qualification or default selection changes; the queue contains no automatic follow-up.

Host-free regression command (standard library only):
`python3 -m unittest discover -s tests -t . -v`.
Real-client/frontend tests require the documented `dev-env` prerequisites below; skips are not live gates.

## How it works

*Oh My Pi (coding-agent client) → OMP Strata (profile, lifecycle tool, evidence) → Strata (inference engine) →
Qwen3.8-Flash-Next (served model: IQ3_S on the RTX PRO 6000 and the RTX 4090 + RTX 3090 pair, Coder IQ1_M on the
RTX 5090 and the fourth tuple's GPUs).* Stock OMP talks directly to stock Strata over OpenAI Chat Completions on
`127.0.0.1:18090`. OMP owns transcripts, tools, compaction and resume; Strata owns inference, templating and its
live cache. After any restart OMP's transcript is authoritative and the engine re-prefills it; nothing claims
restored GPU state.

[`docs/QUICKSTART.md`](docs/QUICKSTART.md) has the exact tested commands:
`fetch` → `install` → `keygen` → `start` → `launch-omp` → `stop`.

- `profiles/<id>.json` is the single nonsecret source of truth: host expectations, stock setup choices, every
  artifact pinned by URL, size and SHA-256, and the OMP route. A changed component or setting is a new profile
  with its own integration root and release ledger; the predecessor stays as the rollback installation.
- `fetch` downloads the pinned OMP binary, Strata engine and llama.cpp archives and model shards, resumable, and
  verifies every byte before anything is used.
- `install` runs stock Strata's own `setup.py` from those local inputs only, with its data folder redirected into
  the integration root, and checks the generated engine flags against the profile.
- `keygen` writes a random API key to a user-only file under the root; `start` binds Strata to loopback with that
  key, refuses to start when the port, GPU or RAM budget is not free, and returns once authenticated identity
  checks pass.
- `launch-omp` runs the pinned stock OMP binary with an isolated home and the `omp-strata` profile: every model
  role on the local server, as many requests in flight as the server has batch slots (one without slots), discovery
  off, retries, model fallback and speculative compaction off, ambient provider credentials scrubbed, and OMP's
  startup catalog fetch held to loopback by the launcher's proxy settings.
- Gate probes, a tracer and a frozen six-task evaluation run on the real host; scrubbed receipts under
  `releases/<profile>/` bind each result to the exact profile fingerprint.

## Documents

### Operate

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md): install, start, use, stop
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md): lifecycle, recovery, logs, upgrades
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md): the tooling's error messages, their causes and fixes
- [`docs/REMOTE.md`](docs/REMOTE.md): the qualified Mac-to-RTX PRO 6000 client route over SSH, fleets, and the G23 probe
- [`docs/SECURITY.md`](docs/SECURITY.md): what is and is not isolated, observed egress, known defects

### Verify

- [`docs/DECISION.md`](docs/DECISION.md): integration readiness, usefulness, further investment
- [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md): resources, throughput, context, restart cost, evaluation results
- [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md): every profile and client route with its recorded gate outcomes (generated)
- [`docs/BASELINE.md`](docs/BASELINE.md): the frozen component tuple and why it was chosen
- [`docs/UPSTREAM.md`](docs/UPSTREAM.md): findings reported to Strata and Oh My Pi, and what each release fixed
- [`docs/G25.md`](docs/G25.md): the controlled same-host comparison with NInfer (run on the RTX 5090, RTX 4090 and RTX 3090)
- [`docs/BRAND.md`](docs/BRAND.md): the visual identity, artwork sources and the public site
- [`docs/handoff/2026-09-30/`](docs/handoff/2026-09-30/): the execution packet this work implements

## Layout

| Path | Purpose |
|---|---|
| `profiles/` | The server profiles (current, first, and every later tuple's candidates and drafts): every artifact pinned by URL, size and SHA-256 |
| `routes/`, `examples/` | Client routes (server profile ids and fingerprints, ports, roles) and a neutral private-binding example |
| `locks/` | Hash-locked Python wheels for stock `setup.py` |
| `omp_strata/` | Stdlib-only tooling: fetch/verify, install, lifecycle, OMP configuration, SSH client routes, transcripts |
| `scripts/omp_strata.py` | The operator CLI |
| `scripts/tracer.py`, `scripts/realhost_gates.py`, `scripts/requalify.py` | Real-host qualification probes and the unattended sequence that runs them (on the GPU host) |
| `scripts/evaluate.py`, `eval/` | The frozen six-task evaluation |
| `scripts/pull_run.py`, `scripts/publish_run.py` | Copy a finished run's results from the GPU host, then scrub them into receipts, ledger and manifest |
| `scripts/verify_release.py` | Checks that the profile or route, ledger and receipts bind together |
| `scripts/upstream_watch.py`, `upstream-watch.json` | New Strata/OMP releases, tracked upstream issues, and drafting the next tuple's profiles |
| `scripts/remote_gates.py`, `scripts/fanout_proof.py` | G23 probe for a client route, and the subagent fan-out proof for a fleet (from the client) |
| `scripts/perf_probe.py` | Prefill, decode, TTFT and draft acceptance by context depth, to compare variants on one host |
| `scripts/compare_g25.py`, `omp_strata/comparison*.py` | G25: the frozen evaluation on Strata and on NInfer in alternating exclusive windows, paired and scored |
| `scripts/g25_host.py`, `scripts/g25_host_probe.py`, `scripts/probe_g25_speed.py` | G25 on a Windows host: prepare, engine switches and the read-only host probe; plus a client-side speed probe for both engines |
| `scripts/render_compatibility.py`, `scripts/documented_route.py` | Generate `docs/COMPATIBILITY.md`; check QUICKSTART's commands against the CLI |
| `releases/<profile or route>/` | Manifest, gate ledger, receipts and scrubbed evidence |
| `tests/` | Host-free unit tests and mock-tier tests with the real stock OMP client |
| `assets/`, `scripts/render_assets.py` | The mark, artwork sources and their rendered PNGs ([`docs/BRAND.md`](docs/BRAND.md)) |
| `site/` | The one-page public site, deployed by `.github/workflows/pages.yml` |

Host-free checks (no GPU). `dev-env` provides what the client and composed tests need: this platform's pinned OMP
binary, the pinned Strata source, and a Python 3.13 env (the lock's interpreter, which must be on `PATH`) with stock
`setup.py`'s packages at the lock's versions. The CUDA wheels are left out, and versions are pinned but not
hash-checked because the lock hashes Windows wheels. It prints the `OMP_STRATA_*` variables, or runs a command with
them set; CI runs the same command. Without those variables the client and composed tests skip explicitly.

```sh
python3 scripts/omp_strata.py dev-env --profile profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1.json -- \
  python3 -m unittest discover -s tests -t .
python3 scripts/verify_release.py --manifest releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1/manifest.json
```

## The OMP family

- [OMP NInfer](https://github.com/alphastorm/omp-ninfer): durable local inference, session state that survives an engine restart
- [OMP Session Gateway](https://github.com/alphastorm/omp-session-gateway): every live session, one private mobile page
- [OMP Oracle](https://github.com/alphastorm/omp-oracle): asynchronous web oracles for hard questions

## License

MIT. See [LICENSE](LICENSE). Oh My Pi, Strata, llama.cpp and the model retain their own licenses and notices.

Community project; not affiliated with or endorsed by the Oh My Pi maintainers, the Strata maintainer, Qwen or
NVIDIA.
