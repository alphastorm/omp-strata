<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
  <img src="assets/logo-light.svg" alt="" width="72" height="72">
</picture>

# OMP Strata

**Stock Oh My Pi on a stock, local Strata server. Nothing forked, everything pinned.**

**Current, qualified: stock OMP `18.18.0` with stock Strata `v0.2.12` across the RTX PRO 6000 (four batch slots with per-slot stock DFlash2 drafters + PLE-direct + KV in VRAM + stock parallel and GDN stacks; tuned-DFlash2 `v0.2.12` alternate, `v0.2.11` DFlash2 rollback), the RTX 5090 (262K default with KV in VRAM + KV growth + GDN stack, and 131K alternative), the RTX 4090 + RTX 3090 pair (stock DFlash2 drafter + split-24 stage-weight trim + PLE-direct + engine `sm_86` table, GDN stack and `STRATA_SELECT_TWO_PASS=1`; `v0.2.12` `env86g` DFlash2 rollback) and the Mac Studio route (plus its tuned-DFlash2 `v0.2.12` alternate). No fork, no proxy, no cloud fallback.**

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
[profile]: profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0.json
[strata-badge]: https://img.shields.io/badge/Strata-v0.2.12-37C4CB?labelColor=0B0E11
[omp-badge]: https://img.shields.io/badge/OMP-18.18.0-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-strata?color=1C232B&labelColor=0B0E11

<sub><strong>Private by design:</strong> loopback-only server · API key required · isolated OMP profile ·
no cloud fallback · every byte hash-pinned</sub>

</div>

## Qualified now

Qualified on 2026-11-07–08 ([decision](docs/DECISION.md)). Every local ledger
below has 21 pass and 3 not applicable; the route ledgers passed their own G23.

| Host | Model and context | Strata · OMP | Ledger | Rollback |
|---|---|---|---|---|
| RTX PRO 6000 | Qwen3.8-Flash-Next IQ3_S, 262,144 tokens, every expert in VRAM; 4 batch slots with per-slot stock DFlash2 drafters (`strata.drafting: "dflash2"`, one 85 MiB slot drafter per slot, `--spec 6`, no `--batch-mtp`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; qualified under the owner's override of its 1/90 two-request maximum time per output token (TPOT) A/B miss from the third pair; tuned-pack alternate [`slots4-df2tuned`](releases/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0/qualification.json) also qualified), direct per-layer embedding (PLE) reads (`--ple-io direct`), KV in VRAM (`--kv-streaming off`, 78 GiB available-RAM start floor), stock `parallel_stack` + `gdn_stack` in `strata.engine_env`, conversation parking (8,192 MiB automatic cache), bare `--prefill auto` (32,768-token ceiling) | v0.2.12 · 18.18.0 | [21 pass, 3 n/a](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0/qualification.json) | [v0.2.11 DFlash2](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json) |
| RTX 5090, **default** | Coder IQ1_M, 262,144 tokens, KV in VRAM (`--kv-streaming off`), elastic KV growth (`--kv-grow`), stock `gdn_stack` in `strata.engine_env`; 34 GiB available-RAM start floor; engine's 4,096 MiB automatic conversation cache (requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller) | v0.2.12 · 18.18.0 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0/qualification.json) | [v0.2.11 262K envg](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/qualification.json) |
| RTX 5090, qualified alternative | Coder IQ1_M, 131,072 tokens; 34 GiB available-RAM start floor; engine's 3,584 MiB automatic conversation cache; starts with Docker Desktop and WSL running (production container stopped by the fleet controller; qualified on the same window's passing 262K A/B, as in `v0.2.10`, and passed G15 after `v0.2.11` 131K failed G15 twice) | v0.2.12 · 18.18.0 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0/qualification.json) | [v0.2.10 131K](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/qualification.json) |
| RTX 4090 + RTX 3090 | IQ3_S, 262,144 tokens, stock roles (RTX 4090 as Main, staged last), manual layer split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, 19.40 / 17.90 GiB expert caches), stock DFlash2 drafter alone (`strata.drafting: "dflash2"`, `--draft dflash2 --draft-fallback none`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; drops `--pipeline-windows 2`), no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`), engine `sm_86` default table + stock `gdn_stack` + two-pass QSA block selection (`STRATA_SELECT_TWO_PASS=1`, `select_two_pass`, 200K cold TTFT 0.976x vs `v0.2.12` base) in `strata.engine_env`; engine's 8,192 MiB automatic conversation cache (`v0.2.8` stock-residency roles draft stays measurement-only) | v0.2.12 · 18.18.0 | [21 pass, 3 n/a](releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0/qualification.json) | [v0.2.12 env86g DFlash2](releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0/qualification.json) |
| Mac Studio → RTX PRO 6000 | SSH local forward to the PRO's 262K DFlash2 `df2` profile ([`docs/REMOTE.md`](docs/REMOTE.md); tuned-pack alternate route [`df2tuned`](releases/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0/qualification.json) also qualified) | v0.2.12 · 18.18.0 | [G23 pass](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0/qualification.json), 2026-11-07 | [v0.2.11 DFlash2 route](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json) |

Profiles and route, with the host labels the ledgers use:

- RTX PRO 6000, `rtxpro6000-win-a`:
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0.json)
  (**current**; pins `strata.drafting: "dflash2"` on all four batch slots — one 85 MiB slot drafter per slot, `--spec 6`, no `--batch-mtp` — packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files, alongside `strata.ple_io: "direct"`, `--ple-io direct`, `setup_args.kv_streaming: "off"`, `--kv-streaming off`, and `strata.engine_env` `parallel_stack` + `gdn_stack`, qualified on 2026-11-07 under the owner's override of its 1/90 two-request max-TPOT A/B miss from the third pair; qualified non-current alternate
  [`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0.json),
  pinning stock's tuned DFlash2 pack `qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack` — faster with two concurrent requests at per-request throughput p50 1.165x and TPOT p50 0.873x vs `v0.2.12` base, slower one request at a time at throughput p50 0.942x and TPOT p50 1.062x, not the rollback — under the owner's override; rollback
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json),
  the `v0.2.11` + `18.16.0` four-slot DFlash2 profile, while the `v0.2.11` batch-MTP profile
  [`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json)
  moves to earlier qualified history; the `v0.2.12` two-pass arm
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0.json)
  missed 3 of 96 checks in its A/B against the `v0.2.12` profile and stays an unqualified draft alongside the `v0.2.11` quality-first one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and six-expert `DeepSeek V4.1-Flash IQ2_XS` drafts, the `v0.2.11` four-slot `UD-Q4_K_XL` screen and the `v0.2.9` `UD-IQ4_XS` / `NVFP4-QAD` model candidates)
- RTX 5090, `rtx5090-win-a`:
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0.json)
  (**default**; pins `setup_args.kv_streaming: "off"`, `strata.kv_grow: true`, `--kv-grow`, and `strata.engine_env` `gdn_stack`; 34 GiB available-RAM start floor; passed all 88 checks in its version A/B against `v0.2.11`; the host's Docker Desktop and WSL, which run its production NInfer container, must be stopped, and after WSL restarts that container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller; rollback
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0.json); the `v0.2.12` two-pass arm
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0.json)
  passed its 96-check A/B against `v0.2.12` `envg` and its 88-check product against `v0.2.11` but failed G18 when the long-session session never compacted in 40 read turns, and stays an unqualified draft with its failing ledger published; the unpinned-GDN `v0.2.9` fallback `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0` stays an uninstalled draft) and
  [`win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0.json)
  (qualified alternative; qualified on the same window's passing 262K A/B without a separate A/B, as in `v0.2.10`, and passed every gate including G15 after [`win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0.json) failed G15 twice; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; rollback
  [`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json))
- RTX 4090 + RTX 3090, `rtx3090-win-a`:
  [`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0.json)
  (**current**; pins stock DFlash2 drafting alone via `strata.drafting: "dflash2"` packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files, drops `--pipeline-windows 2` with no silent MTP fallback, keeps manual `strata.setup_args.layer_split: "24"`, `strata.trim_stage_weights: true`, `--trim-stage-weights`, `strata.ple_io: "direct"`, `--ple-io direct`, and `strata.engine_env` `sm86_table` + `gdn_stack` + `select_two_pass` (`STRATA_SELECT_TWO_PASS=1`), and omits `-parking` in the profile id only to stay within the 120-character profile-id limit while keeping the same `strata.stock_tips`; passed all 96 checks in its paired A/B against the `v0.2.12` `env86g` pair profile with 200K cold TTFT at 0.976x and passed its requalify chain; rollback
  [`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0.json),
  the `v0.2.12` + `18.18.0` pair DFlash2 base profile qualified under the owner's override of its 7/88 version A/B misses against `v0.2.11`, while the `v0.2.11` and `v0.2.10` `df2` profiles and the `v0.2.10` `pw2` `env86g` MTP profile remain earlier qualified history; the `v0.2.12` W4A8 arm
  [`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0.json)
  missed its cold-TTFT bar, 32K decode and inter-token gap in its A/B and stays an unqualified draft alongside the `v0.2.8` stock-residency roles draft)
- Mac Studio client:
  [`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0.json)
  (**current**; qualified non-current alternate
  [`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`](routes/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0.json);
  rollback
  [`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json);
  the two-pass route draft
  [`client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0.json)
  stays unqualified)

What these ledgers establish, and what they do not:

- **New-release discovery is separate.** The [v0.2.12 campaign](releases/campaigns/v0.2.12.json) (opened with
  `scripts/campaign.py open --release v0.2.12 --omp-tag v18.18.0`) is `complete` across all five rows (`916f1d9`) — the
  PRO `slots4-df2` DFlash2 row (with a note naming the qualified `slots4-df2tuned` tuned-pack alternate), the RTX 5090
  131K alternative and 262K `kvvram-kvgrow-envg` default, the pair `df2` `env86gt` two-pass variant in place of the
  prepared `env86g-parking` base (which is qualified as its rollback), and the Studio→PRO `df2` route (with a note
  naming the qualified `df2tuned` alternate route). The [v0.2.11 campaign](releases/campaigns/v0.2.11.json) stays
  `running` with four of its five rows qualified (`01b4d9b`; its RTX 5090 131K row failed G15 twice), while earlier
  campaigns ([v0.2.10](releases/campaigns/v0.2.10.json), [v0.2.9](releases/campaigns/v0.2.9.json),
  [v0.2.8](releases/campaigns/v0.2.8.json), [v0.2.7](releases/campaigns/v0.2.7.json),
  [v0.2.3](releases/campaigns/v0.2.3.json) and [v0.2.1](releases/campaigns/v0.2.1.json)) are complete across all five
  rows; the next campaign drafts each lane from the newest qualified profile across its listed variant families in
  `scripts/campaign.py` `LANES`, which ranks the PRO `slots4-df2` family, the pair `df2` `env86gt` family and the Studio
  `df2` route family last (preferred; breaking same-release ties by lane order; `610be03`, `f3fed60`, `c7ba6c4`, `d10e538`,
  `01b4d9b`, `916f1d9`). See the
  [campaign lifecycle and prepared host commands](docs/OPERATIONS.md#release-campaigns-op10-discovery--op11-host-owned-qualification).
- **Ledger counts and receipts.** Each current local ledger has 21 pass and 3 not applicable; G22 (images), G23
  (remote clients) and G25 (runtime comparison) are not applicable to these local, text-only profiles. Real-host
  `v0.2.12` receipts cite tooling commits `243290e` on the PRO `df2` DFlash2 current chain (`575188b`), the Studio `df2`
  current route G23 (`575188b`), the RTX 5090 262K `kvvram-kvgrow-envg` default chain (`3462f00`), and the RTX 5090 131K
  alternative chain (`5634c6e`), `57dcd18` on the pair `df2` `env86g` rollback chain (`2323c13`), the pair `df2`
  `env86gt` two-pass current chain (`953a31f`) and the unqualified RTX 5090 262K `envgt` two-pass draft (`953a31f`,
  whose long-session G18 never compacted in 40 read turns) after admitting engine `0.1.58`'s stage order at `a5989fe`,
  and `2560f77` on the PRO `df2tuned` tuned-pack alternate chain and its Studio `df2tuned` route G23 (`30d1ed5`);
  operator receipts `916f1d9` bind `G00` and `G06` to `1011368` and hosted CI run `42440417156` on pull request #80, and
  `G01–G05` to the 1,121-test host-free suite at `1011368`
  ([2026-11-07 windows measurements](docs/MEASUREMENTS.md#strata-v0212-windows-2026-11-07-stock-omp-18180),
  [decision](docs/DECISION.md)). In three-pair cold-start version A/B against `v0.2.11` (`A1 B1 B2 A2 A3 B3`,
  `A = v0.2.11`, `B = v0.2.12`, under the owner's 5% non-regression rule, with server decode fields reported rather than
  gated on the four-slot PRO lane because `v0.2.12` counts slot admission in decode time), the RTX 5090 262K `envg`
  default passed all 88 checks (throughput `1.000 / 0.997`, TTFT p50 `1.005 / 1.001`, decode `0.980–1.012`, prefill
  `0.983–1.063`), the PRO four-slot `df2` profile missed 1 of 90 checks at two concurrent short requests (maximum TPOT
  `1.057`, `[0.978, 0.976, 1.239]` from the third pair only, while p95 TPOT `1.037`, max latency `0.957`, total
  throughput `1.015 / 1.007 / 1.015` at one / two / four requests and `0.993` at four 32K requests, four-request TTFT
  p50 `0.867` and cold prefill `0.994–1.007` passed; overridden by the owner on 2026-11-07 ~18:51Z as `"Override: main +
  G23 after tuned arm"`), and the pair `df2` `env86g` profile missed 7 of 88 checks (cold 8K decode `0.943`
  `[0.967, 0.917, 0.947]` and its server decode time `1.060`, depth-0 decode while a second request waits `0.937`
  `[0.929, 0.935, 0.946]` and its decode time `1.068`, 32K prompt longest gap p95 `1.050` and max `1.051`, and depth-0
  p95 gap between output events `1.052`, while throughput `1.006 / 0.994`, TTFT p50 `1.003 / 1.004`, cold 32K decode
  `1.084`, 100K `1.005` and warm 32K `1.012` passed; overridden as `"Override: main, then the arms"`). On the PRO,
  stock's tuned DFlash2 pack (`qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack`, `slots4-df2tuned`) missed 6 of 90
  checks against the `v0.2.11` DFlash2 profile (two requests TPOT p95 `1.162` and max `1.211`, latency p95 `1.055` and
  max `1.080`, four 32K requests per-request throughput p50 `0.941` and TPOT p50 `1.062`, with TTFT p50 at two / four
  requests `0.745 / 0.684`) and 3 of 90 checks against the `v0.2.12` standard-pack profile (`"Measure tuned vs v0.2.12
  base first"`: one request per-request throughput p50 `0.942` `[0.936, 0.935, 0.955]` and TPOT p50 `1.062`
  `[1.068, 1.070, 1.048]`, four requests TTFT p50 `1.138` `[1.484, 1.399, 0.711]`, while two concurrent requests were
  faster at per-request throughput p50 `1.165` `[1.023, 1.230, 1.258]` and TPOT p50 `0.873` `[0.978, 0.828, 0.820]`,
  showing the TTFT gains vs `v0.2.11` came from `v0.2.12` itself), and was qualified as a non-current alternate under
  `"Override: qualify tuned as alternate"`. Across the `STRATA_SELECT_TWO_PASS=1` (`select_two_pass`) arms, the pair
  `env86gt` arm passed all 96 checks against the `v0.2.12` pair profile (200K cold TTFT `0.976` `[0.981, 0.977, 0.970]`)
  and its requalify chain to become the pair's current profile with `env86g` `v0.2.12` as its rollback; the PRO
  `envpgt` arm passed the 200K cold TTFT bar (`0.978` `[0.982, 0.975, 0.977]`) but missed 3 of 96 checks (four requests
  TTFT p50 `1.114` `[0.988, 1.038, 1.345]`, two requests TPOT p95 `1.056` and max `1.076`; `"Keep the base"`); the RTX
  5090 `envgt` arm passed all 96 checks (`0.971` `[0.969, 0.971, 0.974]` at 200K) and all 88 checks in its product
  against `v0.2.11`, then failed G18 in its requalify chain (`"Keep envg current"`); and the pair `STRATA_IQ4_W4A8=2`
  (`iq4nl_w4a8`, `env86gw`) arm missed its cold-TTFT geomean over 8K / 32K / 100K (`1.000` vs `<= 0.98`), 32K decode
  (`0.917`, server decode time `1.089`) and one-request max inter-token gap p50 (`1.153`). Scored G24 passed **15/18**
  on every qualified `v0.2.12` server profile (`tool-loop` 0/3 and the other five tasks 3/3 on the PRO `df2` current
  profile with pilot 6/6 and batch wall 522 s, the PRO `df2tuned` alternate with pilot 5/6 and 581 s, the RTX 5090 262K
  `envg` default with pilot 6/6 and 787 s, and the pair `env86g` `v0.2.12` rollback with pilot 5/6 and 906 s; `bugfix-a`
  2/3 and `tool-loop` 1/3 on the RTX 5090 131K alternative with pilot 5/6 and 726 s; `bugfix-b` 2/3 and `tool-loop` 1/3
  on the pair `env86gt` current profile with pilot 6/6 and 968 s; the unqualified RTX 5090 `envgt` draft scored 17/18,
  `multifile-regression` 2/3, pilot 5/6, 761 s; OMP `18.17` changed the wait ladder and prompt text, so G24 is not
  directly comparable with `18.16.0`; batch walls, not isolated decode latency). All protocol counters (including
  malformed arguments) and timeouts are zero on the qualified server profiles; all receipts and kept failures remain
  published.
- **The PRO pins four-slot stock DFlash2 drafting alongside stock engine environment stacks, direct PLE reads and KV in VRAM on engine 0.1.58 (with the stock tuned pack qualified as an alternate), and the RTX 5090 262K default pins the GDN stack, KV in VRAM and elastic KV growth.**
  On `rtxpro6000-win-a`, in addition to `strata.ple_io: "direct"` (`--ple-io direct`,
  [OPERATIONS.md](docs/OPERATIONS.md#stock-ple-direct-reads)), `setup_args.kv_streaming: "off"` (`--kv-streaming off`,
  keeping KV in VRAM without `--kv-resident 32768`; 78 GiB start floor) and `strata.engine_env` with stock
  `serve/server.py`'s Linux-only nine-switch `parallel_stack` and two-switch `gdn_stack`
  ([UPSTREAM.md](docs/UPSTREAM.md#strata-v0212-setup-and-start-path-review-engine-0158)), the current `v0.2.12`
  `slots4-df2-pledirect-kvvram-envpg-parking` profile pins `strata.drafting: "dflash2"` on all four batch slots
  ([UPSTREAM.md](docs/UPSTREAM.md#stock-dflash2-batch-slot-arm-v0211--0157): one 85 MiB slot drafter per slot under
  `STRATA_BATCH_DF2`, `70.22 GiB` free at start, `--spec 6`, no `--batch-mtp`, 93 GiB free-disk floor; G16 / G20 / G21
  restart readiness **31.1-31.3 s**, G15 kill recall 44.2-44.4 s, G10 **126.94 GiB** available RAM and **83.13 GiB**
  Windows commit headroom of **219.70 GiB** with `73,526 MiB` GPU memory used, the 8,192 MiB automatic conversation
  cache enabled with 24 parks in G19, and G24 **15/18**, pilot 6/6, 522 s) and follows stock's bare `--prefill auto`
  (32,768-token ceiling). Its qualified `v0.2.12` non-current alternate
  `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` pins stock's tuned
  DFlash2 pack (`qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack`, 339,694,592 bytes, 94 GiB disk floor;
  [UPSTREAM.md](docs/UPSTREAM.md#tuned-dflash2-pack-pro-arm); G16 / G20 / G21 restart readiness **31.0-31.4 s**, G15
  kill recall 29.0 s, G10 **126.99 GiB** available RAM and **83.24 GiB** commit headroom of **219.70 GiB** with
  `73,452 MiB` GPU memory used, 36 parks in G19, and G24 **15/18**, pilot 5/6, 581 s), while its qualified rollback is
  the `v0.2.11` DFlash2 profile
  `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` (G16 / G20 / G21
  **31.0-35.7 s**, G15 rerun recall 29.2-29.3 s, G10 **127.14 GiB** available RAM and **83.55 GiB** commit headroom with
  `73,496 MiB` GPU memory used, 32 parks in G19, and G24 **15/18**, pilot 5/6, 627 s). On `rtx5090-win-a`, the `v0.2.12`
  262K `kvvram-kvgrow-envg` default pins `strata.engine_env` `gdn_stack`, `setup_args.kv_streaming: "off"` (**34 GiB**
  available-RAM start floor) and `strata.kv_grow: true` (`--kv-grow`), sizing a **4,096 MiB** automatic conversation
  cache in G19 (16 parks; G10 **13.05 GiB** available RAM and **19.53 GiB** commit headroom of 85.15 GiB; G16 / G20 / G21
  restart readiness **19.1-19.3 s**; G24 **15/18**, pilot 6/6, 787 s), while the `v0.2.12` 131K alternative
  `win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0` sizes a **3,584 MiB** automatic conversation cache in G19 (19
  parks; G10 **11.37 GiB** available RAM and **18.72 GiB** commit headroom of 85.15 GiB; G15 kill recall 30.9-32.0 s;
  G16 / G20 / G21 restart readiness **16.6-18.9 s**; G24 **15/18**, pilot 5/6, 726 s). GDN tensor-core numerics are not
  bit-exact upstream, and engine env pins are reviewed per engine release (`ENGINE_ENV_REVIEWED_ENGINES`, engines
  `0.1.55`, `0.1.56`, `0.1.57` and `0.1.58`), so the next engine release needs a fresh review.
- **The pair pins two-pass QSA block selection (`STRATA_SELECT_TWO_PASS=1`) alongside stock DFlash2 drafting alone, stock roles with the RTX 4090 as Main, manual split 24 with stage weight trim, direct PLE reads, and the engine's `sm_86` table and GDN stack.**
  On `rtx3090-win-a`, engine `0.1.58`'s stage order was admitted at `a5989fe` after the 2026-11-07 pair `df2`
  stage-order measurement start parsed complete: `--gpu-roles 0=main,1=helper` stages the RTX 3090 (GPU 1) first on
  layers 0-23 and the RTX 4090 (GPU 0) last on layers 24-47 at pinned manual split 24
  (`strata.setup_args.layer_split: "24"`), with `strata.trim_stage_weights: true` (`--trim-stage-weights`,
  [OPERATIONS.md](docs/OPERATIONS.md#stock-stage-weight-trim)) so each card loads only its own stage's dense weights
  (771 and 988 MiB), `strata.ple_io: "direct"` (`--ple-io direct`, keeping the 26.8 GiB PLE table on direct SSD reads
  and the **8,192 MiB** automatic conversation cache enabled), `strata.engine_env` `sm86_table` + `gdn_stack` +
  `select_two_pass` (`STRATA_SELECT_TWO_PASS=1`, [UPSTREAM.md](docs/UPSTREAM.md#stock-engine-opt-in-groups-v0212--0158)
  and [Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313)), and stock DFlash2 drafting alone
  (`strata.drafting: "dflash2"`, `--draft dflash2 --draft-model <root>\data\dflash2\qwen3.8-flash-next-dflash2.q4_0-selq4.pack --draft-fallback none --draft-conf 0.35 --draft-vocab <root>\data\dflash2\draft_vocab.bin`,
  packed offline during `install` by stock `tools/dflash2_pack.py` from the pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744e85c17364dcc54a6a420af7135d4c7f6` `config.json` and
  `model.safetensors`, with `STRATA_NO_ACQUIRE=1` and no start-time fetch or silent MTP fallback;
  [UPSTREAM.md](docs/UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)). On engine `0.1.58`, the expert caches are
  **19.40 GiB** on the RTX 3090 and **17.90 GiB** on the RTX 4090 (vs 19.41 / 17.90 GiB on `v0.2.11` `df2`, 19.41 /
  18.31 GiB on `v0.2.10` `df2` and 19.14 / 17.75 GiB on `v0.2.10` `pw2` `env86g` MTP). After the `v0.2.12` `env86g`
  pair profile passed its requalification chain at `57dcd18` (`2323c13`) under the owner's override of its 7/88 version
  A/B misses (`"Override: main, then the arms"`) and the `env86gt` two-pass arm passed all 96 checks against it (200K
  cold TTFT `0.976`) plus its own requalification chain at `57dcd18` (`953a31f`; G10 **65.74 GiB** available RAM and
  **28.21 GiB** Windows commit headroom of `135.69 GiB`, G16 / G20 / G21 restart readiness **55.4 / 55.3 / 55.5 s**, G17
  near-limit task **57.7 s**, 22 parks in G19, G24 **15/18**, pilot 6/6, batch wall **968 s**), `env86gt` is current and
  rolls back to the `v0.2.12` `env86g-parking` profile (G10 `65.66 GiB` available RAM and `28.18 GiB` commit headroom,
  G16 / G20 / G21 `55.2 / 55.3 / 55.6 s`, G17 `59.7 s`, 14 parks in G19, G24 `15/18`, pilot 5/6, batch wall `906 s`),
  while the `v0.2.11` and `v0.2.10` `df2` profiles and the `v0.2.10` `pw2` `env86g` MTP profile remain earlier qualified
  history. The `v0.2.12` `env86gw` (`STRATA_IQ4_W4A8=2`) draft, the `v0.2.8` stock-residency draft, the held `v0.2.7`
  roles draft (PLE in RAM), the unmeasured `v0.2.7` default-split draft, and the `v0.2.3` default and split-32 drafts
  stay unqualified ([decision](docs/DECISION.md)).
- **Remote use.** Through the tunnel on the current `v0.2.12` DFlash2 route (G23 on 2026-11-07 at `243290e`, receipt
  [`6b5c7e35`](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0/receipts/6b5c7e35b9344a3c86767be8cb2321dc.json):
  missing key refused before launch, wrong key 401, health RTT 5.9-7.4 ms, stream TTFT **0.247 s**, tunnel drop
  failing the turn in flight with the prior transcript preserved, nonce recall from transcript replay after tunnel
  reopen 0.87 s, client restart 0.79 s and verified server restart 2.56 s, and a one-turn `launch-omp` smoke answering
  `ROUTE OK` with owned stop), on the qualified `v0.2.12` tuned-pack alternate route (G23 on 2026-11-08 at `2560f77`,
  receipt
  [`ca3919ce`](releases/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0/receipts/ca3919ced5684a61ba4d0a733eef10f1.json):
  health RTT 12.1-16.1 ms, stream TTFT **0.317 s**, recalls 0.90 / 0.86 / 1.61 s, and `ROUTE OK` smoke), and on the
  qualified `v0.2.11` DFlash2 rollback route (G23 on 2026-11-06 at `b812df9`: health RTT 6.0-10.1 ms, stream TTFT
  **0.270 s**, recalls 1.83 / 1.11 / 2.34 s, and `ROUTE OK` smoke; [`docs/REMOTE.md`](docs/REMOTE.md)).
- **Quality-first comparison drafts only.** On the PRO, the one-slot `IQ3_S`
  ([`win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`](profiles/win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json)),
  one-slot Unsloth `UD-Q5_K_XL` quantization
  ([`win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`](profiles/win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json))
  and six-expert `DeepSeek-V4.1-Flash-1017` `IQ2_XS`
  ([`win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0`](profiles/win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0.json),
  separate pinned `strata-dsv41` engine archive, one text conversation and no disk conversation cache) profiles stay
  comparison-only drafts after the 2026-11-06–07 22-task quality-first comparison kept the four-slot `IQ3_S` DFlash2
  incumbent; no gate receipt or inherited qualification is claimed
  ([decision](docs/DECISION.md#update-2026-11-07-quality-first-comparison-on-the-pro-keeps-the-four-slot-iq3_s-incumbent),
  [DeepSeek review](docs/UPSTREAM.md#deepseek-v41-flash-comparison-admission),
  [Qwen one-slot review](docs/UPSTREAM.md#pro-quality-first-one-slot-comparison-admissions)).
- **Not supported.** Images, servers on other operating systems, durable engine state, multiple tenants, fleets
  (no fleet route is published), other DeepSeek sets/layouts and other client routes; every profile other than the qualified ones above remains
  a draft or a rollback installation. Beside the three `v0.2.11` quality-first PRO drafts above, the `v0.2.12` PRO
  two-pass server and route drafts (`envpgt`, missed 3/96 A/B checks), the `v0.2.12` RTX 5090 two-pass draft (`envgt`,
  failed G18), the `v0.2.12` pair W4A8 draft (`env86gw`, missed cold TTFT, 32K decode and inter-token gap in its A/B),
  the PRO `v0.2.11` `UD-Q4_K_XL` comparison screen (slower than the v0.2.11 IQ3_S profile in every measured workload:
  single-request decode 0.85-0.91x, total throughput 0.73-0.84x) and `v0.2.9` `UD-IQ4_XS` and `NVFP4-QAD` model
  candidates (and their routes, while a 30-task Terminal-Bench comparison has not run), the `v0.2.11` RTX 5090 131K
  profile (failed G15 twice), and the RTX 5090 `v0.2.9` `kvvram-kvgrow` fallback (uninstalled) stay unqualified drafts.

### Current profile results

Per gate, for the four current local lanes above
([2026-11-07 windows measurements](docs/MEASUREMENTS.md#strata-v0212-windows-2026-11-07-stock-omp-18180),
[2026-11-06 windows measurements](docs/MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160),
[decision](docs/DECISION.md)).

| Area | RTX PRO 6000, 4-slot DFlash2 (`df2`) + PLE direct + KV VRAM + envpg (2026-11-07; `v0.2.12` `df2tuned` alternate and `v0.2.11` `df2` rollback in parens) | RTX 5090, 262K default, KV VRAM + KV grow + envg (2026-11-07) | RTX 5090, 131K alternative (2026-11-07) | RTX 4090 + RTX 3090, DFlash2 (`df2`) + split 24 + trim + PLE direct + env86gt two-pass (2026-11-07; `v0.2.12` `env86g` rollback in parens) |
|---|---|---|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass: 3/3 tracer runs | pass: 3/3 tracer runs | pass: 3/3 tracer runs | pass: 3/3 tracer runs |
| Live prefix reuse in a session (lost on engine restart) | pass: 12 continuations, engine-reported (`df2tuned` alternate: 12; `v0.2.11` `df2` rollback: 12) | pass: 15 continuations, engine-reported (`v0.2.11` rollback: 12) | pass: 14 continuations, engine-reported (`v0.2.10` rollback: 15) | pass: 12 continuations, engine-reported (`env86g` rollback: 12) |
| Interleaved conversations | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 8,192 MiB cache, 24 parks; `df2tuned` alternate: 48 uncached, 36 parks; `v0.2.11` `df2` rollback: 48 uncached, 32 parks), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 4,096 MiB cache, 16 parks with Docker Desktop/WSL stopped; `v0.2.11` rollback: 98 uncached, 4,352 MiB cache, 17 parks), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 3,584 MiB cache, 19 parks in the Docker Desktop/WSL-stopped window; `v0.2.10` rollback: 46 uncached, 29 parks), not an exact-output claim | pass: A resumes after B; 47 uncached tokens on the controlled continuation (engine's 8,192 MiB cache, 22 parks; `env86g` rollback: 47 uncached, 14 parks), not an exact-output claim |
| Requests at once | up to 4, decoded together with per-slot DFlash2 drafters (`strata.drafting: "dflash2"`, `--spec 6`; tuned pack on `df2tuned` alternate) | one at a time | one at a time | one at a time (DFlash2 verified windows up to 8 tokens) |
| Loopback, API key (including `/status`, `/v1/telemetry` and `/tool-media/` on `v0.2.12`), fail-closed client, local-only routing, with an egress guard for OMP's startup catalog fetch | pass (0 non-loopback / 4,664 ETW events, 2 compactions; `df2tuned` alternate: 0 / 4,148 ETW events, 2 compactions; `v0.2.11` `df2` rollback: 0 / 4,916) | pass (0 non-loopback / 9,775 ETW events, 2 compactions; `v0.2.11` rollback: 0 / 6,493) | pass (0 non-loopback / 6,461 ETW events, 2 compactions; `v0.2.10` rollback: 0 / 10,365) | pass (0 non-loopback / 4,163 ETW events, 2 compactions; `env86g` rollback: 0 / 5,135 ETW events, 2 compactions) |
| Engine or client restart, then continue from OMP's transcript (an engine restart re-prefills it; no state restoration) | pass (readiness 31.1-31.3 s; G16 31.1 s, G20 31.2 s, G21 31.3 s, lowest available RAM 113.51 GiB in G19 / 113.60 GiB in G18L, PLE on direct SSD reads, KV in VRAM; `df2tuned` alternate: 31.0-31.4 s, 118.40 GiB in G18L; `v0.2.11` `df2` rollback: 31.0-35.7 s, 118.67 GiB) | pass with Docker Desktop/WSL stopped (readiness 19.1-19.3 s; G16 19.2 s, G20 19.1 s, G21 19.3 s, lowest available RAM 7.77 GiB in G18L; `v0.2.11` rollback: 18.5-19.3 s, 8.57 GiB) | pass (readiness 16.6-18.9 s; G16 16.6 s, G20 16.6 s, G21 18.9 s, G15 recall 30.9-32.0 s, lowest available RAM 7.08 GiB in G19; `v0.2.10` rollback: 18.7-18.9 s, 7.17 GiB) | pass (readiness 55.3-55.5 s; G16 55.4 s, G20 55.3 s, G21 55.5 s, lowest available RAM 57.00 GiB in G18L; `env86g` rollback: 55.2-55.6 s, 57.28 GiB; `v0.2.11` `df2`: 40.5-40.8 s) |
| Context window (262,144 tokens on the RTX PRO 6000, RTX 5090 default and pair; 131,072 on the RTX 5090 alternative): exact limit, near-limit tool turns, explicit overflow (G17) | pass (near-limit task 25.6 s; `df2tuned` alternate: 26.8 s; `v0.2.11` `df2` rollback: 26.1 s) | pass (near-limit task 30.7 s vs 29.3 s on `v0.2.11` rollback) | pass (near-limit task 16.7 s vs 17.4 s on `v0.2.10` rollback) | pass (near-limit task 57.7 s; `env86g` rollback: 59.7 s; `v0.2.11` `df2`: 61.1 s) |
| OMP compaction (reduced threshold and production long session, G18) | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off |
| Cancelling a *queued* request | pass, with all four slots generating | pass | pass | pass |
| Tool call cut off mid-arguments (G04) | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call |
| Six-task coding evaluation, 18 scored attempts (G24) | 15/18 (tool-loop 0/3, others 3/3; pilot 6/6, batch wall 522 s; `df2tuned` alternate: 15/18, tool-loop 0/3, pilot 5/6, 581 s; `v0.2.11` `df2` rollback: 15/18, pilot 5/6, 627 s) | 15/18 (tool-loop 0/3, others 3/3; pilot 6/6, batch wall 787 s; `v0.2.11` rollback: 17/18, tool-loop 2/3, pilot 6/6, 843 s; not comparable across OMP 18.17) | 15/18 (bugfix-a 2/3, tool-loop 1/3, others 3/3; pilot 5/6, batch wall 726 s; `v0.2.10` rollback: 16/18, tool-loop 1/3, pilot 6/6, 742 s) | 15/18 (bugfix-b 2/3, tool-loop 1/3, others 3/3; pilot 6/6, batch wall 968 s; `env86g` rollback: 15/18, tool-loop 0/3, pilot 5/6, 906 s; `v0.2.11` `df2`: 15/18, 896 s) |
| Guarded install and QUICKSTART example alongside earlier tuples (G26) | pass on an already prepared root (install 25.6 s, start 54.2 s; `df2tuned` alternate: 33.1 s and 38.9 s; `v0.2.11` `df2` rollback: 25.8 s and 56.3 s; first install on v0.2.8 took 1,063.2 s) | pass on an already prepared root (install 12.7 s, start 22.4 s; `v0.2.11` rollback: 11.9 s and 22.3 s; first install on v0.2.8 took 365.6 s) | pass on an already prepared root (install 12.7 s, start 36.0 s; `v0.2.10` rollback: 10.7 s and 36.2 s; first install on v0.2.8 took 297.8 s) | pass on an already prepared root (install 33.4 s, start 67.0 s; `env86g` rollback: 33.2 s and 67.0 s; `v0.2.11` `df2`: 37.0 s and 52.6 s; first install on v0.2.8 took 820.3 s) |
<details>
<summary><strong>Earlier qualified profiles and rollbacks</strong></summary>

Every profile and client route ledger is listed in [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md); the owner's
qualification decisions, retained failures, the G15 probe correction, the G16 predicate fix, the G18 fixture fix
and the OMP speculative-compaction setting are in [`docs/DECISION.md`](docs/DECISION.md), with full figures in
[`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md).

- **2026-11-06 — Strata `v0.2.11` + OMP `18.16.0` (`rtxpro6000-win-a` DFlash2 and batch-MTP, `rtx5090-win-a` 262K, `rtx3090-win-a` pair DFlash2, Mac Studio routes):**
  current rollbacks on the PRO (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json);
  G24 15/18, pilot 5/6, batch wall 627 s, complete G15 rerun at `b812df9` with 29.2-29.3 s recall, restart readiness
  31.0-35.7 s, 127.14 GiB available RAM and 83.55 GiB G10 commit headroom; alongside the qualified `v0.2.11` batch-MTP
  profile `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json);
  G24 16/18, pilot 5/6, batch wall 549 s, restart readiness 30.9-31.4 s, 127.23 GiB available RAM and 81.73 GiB G10
  commit headroom), the RTX 5090 262K default
  (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/qualification.json); G24
  17/18, pilot 6/6, batch wall 843 s, 34 GiB start floor, 4,352 MiB cache, restart readiness 18.5-19.3 s, 13.47 GiB
  available RAM and 20.30 GiB G10 commit headroom; the `v0.2.11` 131K draft failed G15 twice and stays unqualified) and
  the Mac Studio client route
  ([`0.2.11 df2 route`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json),
  [ledger](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json),
  stream TTFT 0.270 s; alongside the [`0.2.11 batch-MTP route`](routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json),
  [ledger](releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json),
  stream TTFT 0.174 s), plus earlier qualified history on the pair
  (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/qualification.json);
  G24 15/18, pilot 5/6, batch wall 896 s, complete G13 rerun at `611c342`, restart readiness 40.5-40.8 s, 19.41 /
  17.90 GiB expert caches, 66.35 GiB available RAM and 28.70 GiB G10 commit headroom);
  [measurements](docs/MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160) and
  [decision](docs/DECISION.md#update-2026-11-06-strata-v0211-with-omp-18160-qualifies-on-the-pro-rtx-5090-262k-pair-and-studio-route-131k-stays-on-v0210).
- **2026-11-03 — Strata `v0.2.10` + OMP `18.16.0` (`rtxpro6000-win-a`, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair DFlash2 and `env86g`, Mac Studio route):**
  current rollback on the RTX 5090 131K alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/qualification.json); G24 16/18, pilot 6/6,
  34 GiB start floor, 3,584 MiB cache, restart readiness 18.7-18.9 s), and earlier qualified history on the RTX 5090
  262K default
  (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/qualification.json); G24
  18/18, pilot 5/6, 34 GiB start floor, 4,352 MiB cache, restart readiness 19.2-19.5 s, 13.41 GiB available RAM and
  20.31 GiB G10 commit headroom), on the pair
  (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/qualification.json);
  G24 17/18, pilot 5/6, restart readiness 43.1-43.4 s, 19.41 / 18.31 GiB expert caches, 65.65 GiB available RAM and
  27.51 GiB G10 commit headroom; alongside the older qualified `v0.2.10` `pw2` `env86g` MTP alternative
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/qualification.json);
  G24 16/18, pilot 5/6, G20 rerun at `837bc89`, restart readiness 55.3 / 43.2 / 55.7 s, 19.14 / 17.75 GiB expert caches,
  65.37 GiB available RAM and 27.54 GiB commit headroom), on the PRO
  (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/qualification.json);
  G24 16/18, pilot 5/6, G14 rerun at `7971a1a`, restart readiness 31.0-31.3 s, 129.12 GiB available RAM and 83.05 GiB
  G10 commit headroom) and on the Mac Studio client route
  ([`0.2.10 kvvram-envpg route`](routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0.json),
  [ledger](releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/qualification.json);
  stream TTFT 0.219 s);
  [measurements](docs/MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160) and
  [decision](docs/DECISION.md#update-2026-11-03-strata-v0210-with-omp-18160-qualifies-on-every-host-and-the-studio-route).
- **2026-11-02 and 2026-11-03 — Strata `v0.2.9` + OMP `18.15.0` (`rtxpro6000-win-a`, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair, Mac Studio route):**
  earlier qualified history on the RTX 5090 131K alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/qualification.json); G24 14/18, pilot 5/6,
  34 GiB start floor, 3,840 MiB cache, restart readiness 16.1-26.8 s), across the PRO
  (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/qualification.json);
  G24 16/18, pilot 5/6, restart readiness 31.0-31.3 s, 129.57 GiB available RAM and 83.35 GiB G10 commit headroom;
  alongside the morning 2026-11-02 base profile
  `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json);
  G24 16/18, pilot 5/6, restart readiness 35.1-39.7 s, 112.58 GiB available RAM and 81.28 GiB G10 commit headroom; both
  `v0.2.9` PRO host roots were pruned on 2026-11-06 with the owner's approval), the RTX 5090 262K default
  (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/qualification.json); G24
  17/18, pilot 5/6, 34 GiB start floor, 4,352 MiB cache, restart readiness 18.6-18.9 s; alongside the morning base
  profile `win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/qualification.json); G24 16/18, pilot 6/6,
  36 GiB start floor, 3,072 MiB cache, restart readiness 16.6-16.8 s), the pair
  (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/qualification.json);
  G24 15/18, pilot 5/6, restart readiness 43.5-43.9 s, 65.68 GiB available RAM and 27.77 GiB G10 commit headroom; and
  its morning base profile
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json);
  G24 15/18, pilot 5/6, restart readiness 55.4-55.6 s, 19.15 / 17.76 GiB expert caches, 65.67 GiB available RAM and
  27.74 GiB G10 commit headroom; both `v0.2.9` pair host roots were pruned on 2026-11-06 with the owner's approval), and
  the Mac Studio client route
  ([`0.2.9 kvvram-envpg route`](routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0.json),
  [ledger](releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/qualification.json);
  stream TTFT 0.172 s; alongside the morning base
  [`0.2.9 batch-MTP route`](routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0.json),
  [ledger](releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/qualification.json); stream TTFT
  0.206 s);
  [tuning measurements](docs/MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150),
  [windows measurements](docs/MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150),
  [tuning decision](docs/DECISION.md#update-2026-11-02-evening-the-v029-tuning-profiles-on-the-pro-and-rtx-5090-and-the-studios-tuned-route-qualify) and
  [morning decision](docs/DECISION.md#update-2026-11-02-strata-v029-with-omp-18150-qualifies-on-every-host-and-the-studio-route).
- **2026-10-30 and 2026-10-31 — Strata `v0.2.8` + OMP `18.14.0` (`rtxpro6000-win-a`, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair, Mac Studio route):**
  earlier qualified history across all lanes: on the PRO
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
