<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
  <img src="assets/logo-light.svg" alt="" width="72" height="72">
</picture>

# OMP Strata

**Stock Oh My Pi on a stock, local Strata server. Nothing forked, everything pinned.**

**Current, qualified: stock OMP `19.2.1` with stock Strata `v0.2.22` on the RTX PRO 6000 (four batch slots with per-slot stock DFlash2 drafters + PLE-direct + KV in VRAM + stock parallel and GDN stacks; `v0.2.16` DFlash2 rollback), the RTX 5090 (262K Coder IQ1_M default with its `v0.2.13` 262K rollback; 131K Coder IQ1_M alternative with its `v0.2.16` 131K rollback; the `v0.2.13` full-model IQ3_S 131K low-RAM alternate stays qualified) and the Mac Studio route (`v0.2.16` DFlash2 route rollback). The RTX 4090 + RTX 3090 pair keeps stock OMP `19.0.0` with stock Strata `v0.2.16` (stock DFlash2 drafter at `--draft-conf 0.5` + split-24 stage-weight trim + PLE-direct + engine `sm_86` table, GDN stack and `STRATA_SELECT_TWO_PASS=1`; `v0.2.13` `df2conf05` rollback): the owner kept `v0.2.16` after the `v0.2.22` pair draft missed its A/B, and that draft is not qualified. No fork, no proxy, no cloud fallback.**

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
[profile]: profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.22-omp19.2.1.json
[strata-badge]: https://img.shields.io/badge/Strata-v0.2.22-37C4CB?labelColor=0B0E11
[omp-badge]: https://img.shields.io/badge/OMP-19.2.1-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-strata?color=1C232B&labelColor=0B0E11

<sub><strong>Private by design:</strong> loopback-only server · API key required · isolated OMP profile ·
no cloud fallback · every byte hash-pinned</sub>

</div>

## Qualified now

Qualified on 2026-11-27 ([decision](docs/DECISION.md)); the pair's current profile was qualified on 2026-11-19. Every
local ledger below has 21 pass and 3 not applicable; the route ledgers passed their own G23.

| Host | Model and context | Strata · OMP | Ledger | Rollback |
|---|---|---|---|---|
| RTX PRO 6000 | Qwen3.8-Flash-Next IQ3_S, 262,144 tokens, every expert in VRAM; 4 batch slots with per-slot stock DFlash2 drafters (`strata.drafting: "dflash2"`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; qualified under the owner's override of its 8/90 A/B misses against `v0.2.16`, all in very short prompt reads), direct per-layer embedding (PLE) reads (`--ple-io direct`), KV in VRAM (`--kv-streaming off`, 78 GiB available-RAM start floor), stock `parallel_stack` + `gdn_stack` in `strata.engine_env`, conversation parking (48,640 MiB RAM conversation cache, sized by stock's server), undeclared tool calls kept as tool calls (`"undeclared_tool_calls": "call"`) | v0.2.22 · 19.2.1 | [21 pass, 3 n/a](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.22-omp19.2.1/qualification.json) | [v0.2.16 DFlash2](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.16-omp19.0.0/qualification.json) |
| RTX 5090, **default** | Coder IQ1_M at stock's re-pinned model revision, 262,144 tokens, KV in VRAM (`--kv-streaming off`), elastic KV growth (`--kv-grow`), stock `gdn_stack` in `strata.engine_env`; 34 GiB available-RAM start floor; engine's 4,352 MiB automatic conversation cache (requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller); qualified under the owner's override of its 6/88 A/B misses against `v0.2.13`, after its main chain failed G18 and the owner-allowed complete-gate rerun passed G18 with G18L | v0.2.22 · 19.2.1 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.22-omp19.2.1/qualification.json) | [v0.2.13 262K envg](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3/qualification.json) |
| RTX 5090, qualified alternative | Coder IQ1_M at the same re-pinned revision, 131,072 tokens; 34 GiB available-RAM start floor; engine's 3,584 MiB automatic conversation cache; starts with Docker Desktop and WSL running (production container stopped by the fleet controller); qualified without a separate A/B (it follows the 262K window), with every gate passing; the full-model IQ3_S 131,072-token low-RAM resident alternate [`iq3s-131k-lowram`](releases/win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3/qualification.json) (`v0.2.13`; stock's planner pick for this host, 11,616 expert slots in VRAM at 22.04 GiB, 29.77 GiB of experts page-locked in RAM, engine's 2,304 MiB automatic conversation cache) stays qualified as a non-current alternate | v0.2.22 · 19.2.1 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.22-omp19.2.1/qualification.json) | [v0.2.16 131K](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.16-omp19.0.0/qualification.json) |
| RTX 4090 + RTX 3090 | IQ3_S, 262,144 tokens, stock roles (RTX 4090 as Main, staged last), manual layer split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`), stock DFlash2 drafter alone (`strata.drafting: "dflash2"`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; drops `--pipeline-windows 2`) with `strata.drafting_args` `--draft-conf 0.5` (`df2conf05`), no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`), engine `0.1.62` `sm_86` default table (8 variables) + stock `gdn_stack` + two-pass QSA block selection (`STRATA_SELECT_TWO_PASS=1`, `select_two_pass`) in `strata.engine_env`; engine's 8,192 MiB automatic conversation cache; qualified under the owner's override of its 30/96 A/B misses against `v0.2.13` (cold prompts read slower since engine `0.1.62` replaced llama.cpp's MMQ prompt kernels with Strata's own fused int8 kernels, [Niko1221/Strata#6308](https://github.com/Niko1221/Strata/issues/6308)); the `v0.2.22` pair draft missed 38/96 A/B checks against this profile and is not qualified (owner: `"Keep v0.2.16 conf05 current"`) | v0.2.16 · 19.0.0 | [21 pass, 3 n/a](releases/win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.16-omp19.0.0/qualification.json) | [v0.2.13 df2conf05 DFlash2](releases/win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3/qualification.json) |
| Mac Studio → RTX PRO 6000 | SSH local forward to the PRO's 262K DFlash2 `df2` profile ([`docs/REMOTE.md`](docs/REMOTE.md)) | v0.2.22 · 19.2.1 | [G23 pass](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.22-omp19.2.1/qualification.json), 2026-11-27 | [v0.2.16 DFlash2 route](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.16-omp19.0.0/qualification.json) |

Profiles and route, with the host labels the ledgers use:

- RTX PRO 6000, `rtxpro6000-win-a`:
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.22-omp19.2.1`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.22-omp19.2.1.json)
  (**current**; the `v0.2.16` four-slot DFlash2 choices on stock `v0.2.22` and engine `0.1.69` — `strata.drafting: "dflash2"` on all four batch slots, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files, `strata.ple_io: "direct"`, `--ple-io direct`, `setup_args.kv_streaming: "off"`, `--kv-streaming off`, `strata.engine_env` `parallel_stack` + `gdn_stack` and `"undeclared_tool_calls": "call"`; qualified on 2026-11-27 under the owner's override (`"Override: run main + Studio G23 now"`) of its 8/90 A/B misses against `v0.2.16`, after its requalify chain stopped on two harness defects, the owner allowed one more fix round (`"Allow one more fix round for these two defects (with regression tests), then rerun as described"`) and the complete-gate rerun at `8a3584b` passed; rollback
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.16-omp19.0.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.16-omp19.0.0.json),
  the `v0.2.16` + `19.0.0` four-slot DFlash2 profile; the `v0.2.16` tuned-pack draft
  [`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.16-omp19.0.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.16-omp19.0.0.json)
  missed 17 of 90 checks against the `v0.2.13` tuned pack, was not overridden, and stays unqualified with a `"Not qualified"` blocker (`b8b6f6b`); the `v0.2.13` four-slot DFlash2 and tuned-pack profiles
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json)
  and [`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3.json)
  and the `v0.2.12` four-slot DFlash2 and tuned-pack profiles
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0.json)
  and [`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0.json)
  join the `v0.2.11` four-slot DFlash2 and batch-MTP profiles in earlier qualified history; the `v0.2.13` standard-pack `--draft-conf 0.55` draft (`df2conf055`, withdrawn before install with a `"Not qualified"` blocker at `b2e9730`), the `v0.2.12` two-pass arm
  [`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0.json),
  the `v0.2.11` quality-first one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and six-expert `DeepSeek V4.1-Flash IQ2_XS` drafts, the `v0.2.11` four-slot `UD-Q4_K_XL` screen and the `v0.2.9` `UD-IQ4_XS` / `NVFP4-QAD` model candidates stay unqualified drafts)
- RTX 5090, `rtx5090-win-a`:
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.22-omp19.2.1`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.22-omp19.2.1.json)
  (**default**; the `v0.2.13` 262K choices on stock `v0.2.22` — `setup_args.kv_streaming: "off"`, `strata.kv_grow: true`, `--kv-grow`, `strata.engine_env` `gdn_stack` and a 34 GiB available-RAM start floor — with the Coder model at stock's re-pinned revision `bba88856f8c3c0c9e40e45f82d05e228b814ac43` (shard 1 29,608,446,496 bytes with a new sha256; shard 2 unchanged), so its A/B against `v0.2.13` mixes a model and an engine change; qualified on 2026-11-27 under the owner's override (`"Override: one more window runs the 262K and 131K mains (production down about 1 to 1.5 h, then restored)"`) of its 6/88 A/B misses; its requalify chain failed G18 (after compaction the final turn repeated the earlier document-reading pattern and never fixed `calc.py` or gave the remembered code), the owner decided `"Include it, with its one allowed G18l rerun. If G18l fails again, 262K stays on v0.2.13."`, and the complete-gate rerun at `8a3584b` passed G18 with G18L; the host's Docker Desktop and WSL, which run its production NInfer container, must be stopped, and after WSL restarts that container must be recreated by the owner's pinned relaunch script or returned through the owner's fleet controller; rollback
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3.json),
  which passed all 88 checks in its version A/B against `v0.2.12` and published at `d3c96fb`, while the `v0.2.12` 262K profile
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0.json) joins earlier qualified history; the `v0.2.13` `STRATA_SPEC_COST=1` (`spec_cost`, `...-envgc-...`) arm missed 3 of 88 checks against `v0.2.13` `envg` and 2 of 88 in three replacement pairs with about one 4x largest-gap spike per three cold starts, was not adopted by the owner, and stays an unqualified draft with a `"Not qualified"` blocker at `b2e9730`, alongside the `v0.2.12` two-pass arm
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0.json),
  which failed G18 when its long-session session never compacted in 40 read turns, and the uninstalled `v0.2.9` fallback `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0`; the `v0.2.16` 262K draft
  [`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.16-omp19.0.0`](profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.16-omp19.0.0.json)
  failed G15 after the owner overrode its 10/88 A/B misses against `v0.2.13`, so the owner kept `v0.2.13` current at the time (`"Keep v0.2.13 262K as the 5090's current release; v0.2.16 131K qualifies as an alternate"`) and the draft stays unqualified with a `"Not qualified"` blocker at `b8b6f6b`),
  [`win11-rtx5090-coder-iq1m-131k-strata0.2.22-omp19.2.1`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.22-omp19.2.1.json)
  (current 131K alternative on stock `v0.2.22` with the same re-pinned Coder revision and `"undeclared_tool_calls": "call"`; qualified on 2026-11-27 without a separate A/B (it follows the 262K window), with G10-G20 passing in its requalify chain (G15 and G18L included) and G24, G26 and G21 in its complete-gate rerun; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; rollback
  [`win11-rtx5090-coder-iq1m-131k-strata0.2.16-omp19.0.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.16-omp19.0.0.json), while [`win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3.json), [`win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0.json) and [`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json) are earlier qualified history and [`win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0.json) stays an unqualified draft after failing G15 twice) and
  [`win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3`](profiles/win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3.json)
  (qualified, non-current full-model IQ3_S 131K low-RAM resident alternate while the Coder stays the default; stock's planner pick for this host, keeping 11,616 expert slots in VRAM at 22.04 GiB and 29.77 GiB of experts page-locked in RAM; in its report-only screen against `v0.2.13` Coder IQ1_M 131K it measured cold decode `1.046` at 8K, `1.093` at 32K, `1.071` at 100K and `1.094` on warm 32K vs `0.763` at the empty prompt, queue decode `1.086 / 1.086`, per-request `1.134 / 1.129`, TPOT p50 `0.881 / 0.885`, throughput `w1` `1.059` and `w3` `0.917`, TTFT p50 `1.528` at 512 tokens and `1.122` at 32K, and prefill `0.61-0.95`, with `58/60` vs Coder `54/60` on the earlier private quality set, then passed every gate in its owner-decided requalify chain at `6e2dda2` (`"Qualify full-model IQ3_S 131K: prune old [rtx5090-win-a] roots for disk, then run its main gates"`) after deleting five superseded RTX 5090 roots for disk (`C:` `98.1 -> 156.6 GiB` free); the full-model IQ3_S 262K low-RAM screen draft `...-iq3s-262k-lowram-kvvram-kvgrow-envg-...` (`"Also screen IQ3_S at 262K"`) passed install and was refused on first start with `"strata.kv_grow: elastic K/V line absent from this start's engine-log interval"`, staying an unqualified draft with a `"Not qualified"` blocker at `b2e9730`)
- RTX 4090 + RTX 3090, `rtx3090-win-a`:
  [`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.16-omp19.0.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.16-omp19.0.0.json)
  (**current**; the `v0.2.13` `df2conf05` choices on stock `v0.2.16` and engine `0.1.62` — stock DFlash2 drafting alone via `strata.drafting: "dflash2"` packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files, `strata.drafting_args` `--draft-conf 0.5` written to stock `user_args` with stock `write_config`, manual `strata.setup_args.layer_split: "24"`, `strata.trim_stage_weights: true`, `--trim-stage-weights`, `strata.ple_io: "direct"`, `--ple-io direct`, and the `env86gt` engine env (the engine `0.1.62` `sm_86` table's 8 variables, `gdn_stack` and `select_two_pass`) — plus `"undeclared_tool_calls": "call"`; the id omits `-parking` only to stay within the 120-character profile-id limit while keeping the same `strata.stock_tips`; qualified on 2026-11-19 under the owner's override (`"Override the miss and qualify it."`) of its 30/96 A/B misses against `v0.2.13`, with every gate passing; the `v0.2.22` draft
  [`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.22-omp19.2.1`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.22-omp19.2.1.json)
  missed 38 of 96 A/B checks against this profile, the owner kept this profile current (`"Keep v0.2.16 conf05 current"`), and the draft carries a `"Not qualified"` blocker with no gate run; rollback
  [`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3.json),
  the `v0.2.13` + `18.18.3` `--draft-conf 0.5` profile, while the `v0.2.12` `env86gt` and `env86g` profiles
  [`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0.json)
  and [`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0.json),
  the `v0.2.11` and `v0.2.10` `df2` profiles and the `v0.2.10` `pw2` `env86g` MTP profile are earlier qualified history; the `v0.2.13` `env86gt` and `env86gts` drafts carry `"Not qualified"` blockers at `b2e9730` and stay unqualified alongside the `v0.2.12` W4A8 arm
  [`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0.json)
  and the `v0.2.8` stock-residency roles draft)
- Mac Studio client:
  [`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.22-omp19.2.1`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.22-omp19.2.1.json)
  (**current**; rollback
  [`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.16-omp19.0.0`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.16-omp19.0.0.json);
  the `v0.2.16` tuned-pack route
  [`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.16-omp19.0.0`](routes/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.16-omp19.0.0.json)
  never ran G23 because its server profile did not qualify, and carries a `"Not qualified"` blocker at `b8b6f6b`; the `v0.2.13` `df2` and `df2tuned` routes
  [`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3.json)
  and [`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`](routes/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3.json),
  the `v0.2.12` `df2` and `df2tuned` routes and the `v0.2.11` `df2` route are earlier qualified history; the `v0.2.12` two-pass route draft
  [`client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0.json)
  stays unqualified)

What these ledgers establish, and what they do not:

- **New-release discovery is separate.** The [v0.2.22 + OMP 19.2.1 campaign](releases/campaigns/v0.2.22+omp19.2.1.json)
  stays `running`: its PRO `slots4-df2` DFlash2, RTX 5090 262K `kvvram-kvgrow-envg`, RTX 5090 131K Coder and
  Studio→PRO `df2` route rows are `qualified` (`6917557`), and its pair `df2conf05` row `failed` its A/B. Stock
  `v0.2.17`-`v0.2.21` were never drafted here. The
  [v0.2.16 + OMP 19.0.0 campaign](releases/campaigns/v0.2.16+omp19.0.0.json) stays `running` with four of its five rows
  qualified (its RTX 5090 262K row failed G15); stock `v0.2.14` and `v0.2.15` were never drafted here. The
  [v0.2.13 campaign](releases/campaigns/v0.2.13.json) and the
  [v0.2.12 campaign](releases/campaigns/v0.2.12.json) (`916f1d9`) are `complete` across all five rows, the
  [v0.2.11 campaign](releases/campaigns/v0.2.11.json) stays `running` with four of its five rows qualified (`01b4d9b`;
  its RTX 5090 131K row failed G15 twice), while earlier campaigns
  ([v0.2.10](releases/campaigns/v0.2.10.json), [v0.2.9](releases/campaigns/v0.2.9.json),
  [v0.2.8](releases/campaigns/v0.2.8.json), [v0.2.7](releases/campaigns/v0.2.7.json),
  [v0.2.3](releases/campaigns/v0.2.3.json) and [v0.2.1](releases/campaigns/v0.2.1.json)) are complete across all five
  rows; the next campaign drafts each lane from the newest qualified profile across its listed variant families in
  `scripts/campaign.py` `LANES` (`610be03`, `f3fed60`, `c7ba6c4`, `d10e538`, `01b4d9b`, `916f1d9`). See the
  [campaign lifecycle and prepared host commands](docs/OPERATIONS.md#release-campaigns-op10-discovery--op11-host-owned-qualification).
- **Ledger counts and receipts.** Each current local ledger has 21 pass and 3 not applicable; G22 (images), G23
  (remote clients) and G25 (runtime comparison) are not applicable to these local, text-only profiles. The `v0.2.22`
  qualification is at `6917557`, and `c591334` sets the CI matrix to these currents, rollbacks and alternates
  ([measurements](docs/MEASUREMENTS.md#strata-v0222-windows-2026-11-26-stock-omp-1921),
  [decision](docs/DECISION.md#update-2026-11-27-strata-v0222-with-omp-1921-qualifies-on-the-pro-the-rtx-5090-262k-default-and-131k-alternative-and-the-studio-route-the-pair-stays-on-v0216);
  the `v0.2.16` runs at `395aefa`, `99ef483` and `7b0c091`, qualified at `fd65c73`, and the `v0.2.13` runs at
  `2af52b8`, `8ab88b0`, `d3c96fb`, `d0c2e28`, `6e2dda2` and `440fa1b` stay in their ledgers). Each lane ran three
  interleaved cold-start pairs (`A1 B1 B2 A2 A3 B3`, reporting `B / A` geometric means, with `A` the lane's current
  profile). The owner's rule makes a profile current only if every real-host gate passes and no paired metric is more
  than 5% worse. Every lane below that ran an A/B missed that bar, so each needed an explicit owner decision, quoted verbatim; an
  override waives only the A/B miss, and the profile still has to pass every real-host gate. Restart recall (G15)
  passed on every lane this time ([Niko1221/Strata#6316](https://github.com/Niko1221/Strata/issues/6316) did not
  recur):
  - **RTX PRO 6000 four-slot DFlash2** (2026-11-26 23:35-23:51Z) missed 8 of 90 checks, all in very short prompt
    reads: a 61-token prompt's TTFT `1.082` and prompt tokens/s `0.916`; a repeated 32K prompt with 7 new tokens TTFT
    `1.335` and prompt time `1.488` (25-28 ms -> 38 ms), whole request `1.037`. Better or level: 1,000-token throughput
    `1.022 / 1.050 / 1.036` (`c1/c2/c4`), four concurrent 32K requests `1.081`, per-request rate `1.00-1.09`, TTFT p50
    `0.86-0.95`, TPOT p50 `0.92-1.00`, cold prefill 8K / 32K / 100K `1.05 / 1.05 / 1.04`, request wall `0.96-1.00`.
    The owner decided `"Override: run main + Studio G23 now"`. Its requalify chain (2026-11-27 15:43-15:54Z) passed
    G10, the tracer, G12, G14q, G15 and G16-G20; G13 and G14 failed on two harness defects (below) and the run stopped
    after the pilot. The complete-gate rerun at `8a3584b` (17:41-17:50Z) passed G13, G14, G24 (15/18), G26 and G21.
    The PRO windows ran under the host lock with the owner's console session signed in; the voice tenant's five
    containers were already exited and stayed as found.
  - **RTX 5090 262K `envg`** (23:57-00:08Z) missed 6 of 88 checks: the largest output gap p95 `1.173` (per pair
    `1.473`, `1.082`, `1.011`, so one pair drove it) and max `1.187`; the first queued request's TTFT `1.085` and prefill `0.911` (its
    request wall `0.968`). Better: throughput `w1` `1.092` / `w3` `1.121`, per-request `1.105 / 1.100`, TTFT p50
    `0.838 / 0.890`, TPOT p50 `0.905 / 0.906`, cold prefill `1.108` (8K) / `1.084` (32K) / `1.119` (100K) / `1.224`
    (depth 0), repeated 32K prompt prefill 5.73x, request walls `0.87-0.97`. Because stock re-pinned the Coder model,
    this A/B mixes a model and an engine change. The owner decided `"Override: one more window runs the 262K and 131K
    mains (production down about 1 to 1.5 h, then restored)"`. The 262K requalify chain (15:45-15:59Z) passed every
    gate except G18: after compaction the final turn repeated the earlier document-reading pattern and never fixed
    `calc.py` or gave the remembered code, and the run stopped after the pilot. The owner decided `"Include it, with
    its one allowed G18l rerun. If G18l fails again, 262K stays on v0.2.13."` The complete-gate rerun at `8a3584b`
    (18:06-18:18Z) passed G18 (with G18L), G24 (14/18), G26 and G21. The 131K profile had no separate A/B; its
    requalify chain (15:59-16:10Z) passed G10-G20 (G15 and G18L included) and its complete-gate rerun (18:20-18:31Z)
    passed G24 (16/18), G26 and G21. Three fleet-custody windows took the production NInfer container down
    (23:38-00:12Z, 15:43-16:17Z and 18:03-18:37Z) and restored it fully each time: a new `"WSL integration ...
    provisioned"` line, fleet return and production health 200. Before the first window the host's fleet had been
    Blocked since its 11-24 reboot; the first restoration cleared it.
  - **RTX 4090 + RTX 3090 `--draft-conf 0.5`** (23:35-00:02Z) missed 38 of 96 checks. Cold prompt reads were slower
    at every depth (prompt tokens/s 8K `0.873`, 32K `0.872`, 100K `0.865`, 200K `0.876`; TTFT `1.14-1.16`; 32K
    10,844 -> 12,478 ms, 200K 59,266 -> 67,752 ms), decode right after a short prompt read `0.881` (8K `0.949`) and a
    single 32K request `0.893`; TTFT p50 `0.862` and repeated prompts were level. The engine logs show 77% of experts
    resident (80% before), the stock tail skip off, the CPU prefill share on and the fused kernels from 3,072-token
    chunks. The owner decided `"Keep v0.2.16 conf05 current"`; the draft carries a `"Not qualified"` blocker and no
    gate ran.

  Harness fixes, each with a regression test, came before and during the windows. A Windows OMP tracer on the PRO host
  (print, resume, kill, resume, RPC) caught the provider-slot census misreading exiting workers and a killed client's
  replacement worker before any window (`b17b462`, `7b18d3a`, `2d89a04`, `28fa632`). In the windows, the native-addon
  cleanup searched one directory level, but OMP `19.2.1` extracts to `natives/<version>/embedded-<hash>/`, so it
  skipped the worker wait and deleted the addon under the last attempt's worker (WinError 5 after every pilot, so
  G24, G26 and G21 never ran in the main chains); and the tracer ran OMP without the worker watch, so G13's clients
  joined its still-running worker (PRO G13 and G14 failed with `"unexpected client tree survivor(s)"`). `8a3584b` and
  `b46516d` fixed both; each was reproduced on the PRO host and proven fixed with the real binary before the reruns.
  Scored G24 on `v0.2.22` (the reruns' scored batches; each main chain's pilot was 5/6) passed **15/18** on the PRO
  `df2` current profile (batch wall 399 s), **14/18** on the RTX 5090 262K default (448 s) and **16/18** on the RTX
  5090 131K Coder alternative (550 s). The `v0.2.16` windows filed
  [Niko1221/Strata#6308](https://github.com/Niko1221/Strata/issues/6308) (the pair's cold prompt reads 6-12% slower
  after the MMQ kernels' removal) and [Niko1221/Strata#6316](https://github.com/Niko1221/Strata/issues/6316) (the
  first answer after the server restarts a stopped engine can ignore the conversation).
- **Stock `v0.2.22` changes how start proves each lane, not the lanes' choices.** Each `v0.2.22` profile keeps its
  `v0.2.16` or `v0.2.13` predecessor's stock setup choices on stock `v0.2.22` (tag object
  `a6f14f067fc4a2be660284039b33234937cbf555` peeling to `b28ca95e3e6847f2d5e317994f253b66716deeaa`, published
  2026-11-25T18:52:49Z; app 0.2.22, Control and engines 0.1.69) and stock OMP `19.2.1`
  (`b55cd1bb664d8ab46ddc77f2a34eb47555dbf1ac`, published 2026-11-25T17:10:03Z). Layout and setup invocation are
  unchanged since `v0.2.16`, and every lane's stock-generated config is unchanged
  ([UPSTREAM.md](docs/UPSTREAM.md#stock-strata-v0222), [UPSTREAM.md](docs/UPSTREAM.md#stock-omp-1921-surface)):
  - **Start.** Stock's server now sizes a RAM conversation cache when the config sets none; no lane pins
    `--conversation-cache-mib`, so the PRO gets 48,640 MiB and the pair 25,344 MiB, while on the RTX 5090 the stock
    size stays under 8,192 MiB and the engine keeps its own default (4,352 MiB at 262K, 3,584 MiB at 131K). The server
    also sets `STRATA_ROUTE_TAIL_SKIP=0` when the config env does not name it and `OMP_NUM_THREADS` to the pool workers
    on the PRO. The start checks admit exactly these stock values.
  - **Engine `0.1.69`.** The Windows CUDA 13 component (build `a5bfe0369bfb+cuda13.0`,
    `strata-engine-0.1.69-windows-x86_64-cuda-cuda13.tar.gz`, 494,711,524 bytes) keeps the stage order. For the pair's
    `v0.2.22` draft, the `sm_86` table is stock's 18 variables (the id keeps `env86gt`); two-card splits arm a CPU prefill share by default,
    and fused prompt kernels start at 3,072-token chunks (1,024 before). Three engine deaths within 600 s on one server
    process now stop restarts (HTTP 503); the gate sequences stay below that, and G15 reruns use a fresh server. New
    key-checked routes `/v1/models/{id}` and `/models/{id}` are probed by G13 (no key or wrong key 401, correct key
    200). The DFlash2 drafter, window, confidence, packs, vocabulary and start lines are unchanged.
  - **RTX 5090 Coder re-pin.** Stock moved the Coder model to revision `bba88856f8c3c0c9e40e45f82d05e228b814ac43`
    (shard 1 29,608,446,496 bytes with a new sha256; shard 2 unchanged), and the `v0.2.22` RTX 5090 profiles follow it.
  - **OMP `19.2.1`.** The chat wire, rendered keys and defaults are unchanged. HTTP 500 is no longer replayed after
    transport retries (6 requests, not 12). The fixed context grew to 6,793 tokens, so G13 and G18 force compaction at
    11,000 tokens and G17 allows 7,900 tokens of overhead. Because the launcher sets `providers.maxInFlightRequests`,
    every OMP run that reaches Strata starts a per-user provider-slot worker that exits about 3 s after its last client
    (3.0-3.1 s measured on Windows); clients sharing an OMP home join a live worker, and the gates allow exactly that
    worker and nothing else.
- **Stock `v0.2.16` changes how install and start prove each lane, not the lanes' choices.** Each `v0.2.16` profile
  keeps its `v0.2.13` predecessor's stock setup choices on stock `v0.2.16` (tag `acdcf162fd4af0e566b4d4bbc49f71c4c14e350a`
  peeling to `64524fb9fc82222ddce554c0643b64f056ec8366`, published 2026-11-18T21:57:34Z) and stock OMP `19.0.0`
  (`57771ae562b9345e0579bceb2d68d585e3e6927e`, published 2026-11-19T00:02:14Z)
  ([UPSTREAM.md](docs/UPSTREAM.md#strata-v0216-setup-and-start-path-review-engine-0162),
  [UPSTREAM.md](docs/UPSTREAM.md#stock-omp-1900-surface)):
  - **Layout.** Stock moved into `engine/ app/ terminal/ docs/ tools/`: setup is `terminal/setup.py`, the server
    `terminal/serve/server.py` and the engine folder `terminal/engine`. `install` materializes the terminal layout for
    `v0.2.16` profiles and keeps `v0.2.13` and older rollback roots flat.
  - **Setup.** Stock setup's own package install needs its offline stamp, so setup now runs without
    `STRATA_NO_ACQUIRE`; pip stays offline through `PIP_NO_INDEX`, and the engine/MTP guards and the DFlash2
    prohibition stay (`ad7f00c`). Setup no longer uses llama.cpp, so `v0.2.16` profiles pin no llama.cpp archive.
  - **Engine `0.1.62`.** The Windows CUDA 13 component (build `1d295787b365+cuda13.0`,
    `strata-engine-0.1.62-windows-x86_64-cuda-cuda13.tar.gz`, 487,452,901 bytes) runs prompt experts on Strata's own
    fused int8 kernels on every NVIDIA card class these lanes use; llama.cpp's MMQ kernels are gone from the Windows archive, and the pair's
    `sm_86`/`sm_89` cards joined that class. Stock's `sm_86` table dropped `STRATA_ADAPT_NOWAIT` for repeatable output,
    so the pair's `env86gt` group follows the `0.1.62` table (8 variables) plus the GDN stack and two-pass selection.
    Engine env pins are reviewed per engine release (`ENGINE_ENV_REVIEWED_ENGINES` now includes `0.1.62`), and GDN
    tensor-core numerics are not bit-exact upstream.
  - **Start.** Four-slot PRO starts print `[strata] Drafting: DFlash2, one guess window per request slot (spare rows
    only)`, and every DFlash2 start prints the draft vocabulary line. The start check requires the exact set of lines
    (with `draft_vocab.bin (the default)` on these English-locale hosts) and reads `--draft-conf` from the engine's
    `engine started:` argv.
  - **Undeclared tool calls.** New `v0.2.16` profiles pin `"undeclared_tool_calls": "call"` (owner decision
    2026-11-12). `install` writes it with stock `write_config` and verifies the generated config. Stock exposes the
    setting on neither `/config` nor `/props`, so the proof is the config file's identity.
  - **Display GPU.** A profile-declared display GPU now tolerates up to 4,096 MiB of foreign use (owner decision,
    `014090a`); every other GPU keeps the 1,500 MiB limit, and compute processes stay refused.
  - **OMP `19.0.0`.** The chat wire is unchanged. The launcher renders `composer.predictions` false (interactive answers
    would otherwise send an extra request per turn), `launch.enabled` false (no service-mode daemon outliving OMP),
    `spelling.autocomplete` off and a fixed `PI_AI_CODEX_CLIENT_VERSION` (which stops a startup npm version fetch), and
    disables the foreign providers `ssh-json` and `ssh-config`. OMP keeps a per-session change journal,
    `changes.jsonl`, beside each session.

  The RTX 5090 262K rollback is the `v0.2.13` profile qualified on 2026-11-09 at `d3c96fb` (every gate passing
  including G15 and G18L, G24 **16/18**), and the full-model IQ3_S 131K low-RAM alternate stays the `v0.2.13` profile
  qualified at `6e2dda2` (**11,616** expert slots in VRAM at **22.04 GiB** and **29.77 GiB** of experts page-locked in
  RAM; [UPSTREAM.md](docs/UPSTREAM.md#rtx-5090-low-ram-screen-planning)). Each rollback's per-gate figures are in the
  table below.
- **The pair keeps stock roles with the RTX 4090 as Main, manual split 24 with stage weight trim, direct PLE reads, `--draft-conf 0.5` and two-pass selection on engine `0.1.62`.**
  On `rtx3090-win-a`, engine `0.1.62` keeps the configured stage order under `--gpu-roles` (measured 07:23-07:30Z on
  2026-11-19 and admitted at `b43b2bd`, following `0.1.59` at `6eb9f05`): `--gpu-roles 0=main,1=helper` stages the
  RTX 3090 (GPU 1) first on layers 0-23 and the RTX 4090 (GPU 0) last on layers 24-47 at pinned manual split 24
  (`strata.setup_args.layer_split: "24"`), with `strata.trim_stage_weights: true` (`--trim-stage-weights`,
  [OPERATIONS.md](docs/OPERATIONS.md#stock-stage-weight-trim)), `strata.ple_io: "direct"` (`--ple-io direct`, keeping
  the 26.8 GiB PLE table on direct SSD reads and the **8,192 MiB** automatic conversation cache enabled),
  `strata.engine_env` `env86gt` ([Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313)), stock DFlash2
  drafting alone (`strata.drafting: "dflash2"`, packed offline during `install` by stock `dflash2_pack.py` from the
  pinned `incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744e85c17364dcc54a6a420af7135d4c7f6` `config.json` and
  `model.safetensors`, with no start-time fetch or silent MTP fallback;
  [UPSTREAM.md](docs/UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)), and `strata.drafting_args` pinning
  `{"--draft-conf": "0.5"}` (`df2conf05`, stock's slot-step value for the pair's per-card slots, which stock cannot
  compute on a split; [UPSTREAM.md](docs/UPSTREAM.md#reviewed-dflash2-confidence-pins)). The pair's first `v0.2.16`
  start refused with `"stock drafting: exactly one --draft required in the started engine argv"` because the
  started-argv parser consumed the space after the valueless `--trim-stage-weights`; `e730509` fixed the parser with a
  regression test. The owner's console session was logged off with consent at 07:15:29Z for the window. The rollback
  is the `v0.2.13` `df2conf05` profile (`440fa1b` at `7c2d25e`); the `v0.2.12` `env86gt` and `env86g-parking` profiles,
  the `v0.2.11` and `v0.2.10` `df2` profiles and the `v0.2.10` `pw2` `env86g` MTP profile are earlier qualified
  history. The `v0.2.13` `env86gt` and `env86gts` (`STRATA_QSA_SPLIT_ATTN=1`) drafts (`b2e9730`), the `v0.2.12`
  `env86gw` (`STRATA_IQ4_W4A8=2`) draft, the `v0.2.8` stock-residency draft, the held `v0.2.7` roles draft (PLE in
  RAM), the unmeasured `v0.2.7` default-split draft, and the `v0.2.3` default and split-32 drafts stay unqualified
  ([decision](docs/DECISION.md)). For the `v0.2.22` draft, engine `0.1.69`'s stage order and start lines were measured
  first (2026-11-26 22:51-22:57Z): configured order kept, CUDA0 layers 0-23 and CUDA1 24-47, DFlash2 alone with
  `--draft-conf 0.5`, conversation cache 25,344 MiB of 128 GiB, tail skip at the stock default 0 and the split's CPU
  prefill share armed; the draft then missed its A/B (above) and stays unqualified.
- **Remote use.** Through the tunnel on the current `v0.2.22` DFlash2 route (G23 on 2026-11-27, 15:54-15:56Z: missing
  key refused before launch, wrong key HTTP 401, health RTT 4.9-6.1 ms, tunnel TTFT **0.141 s**, a tunnel drop failing
  the turn in flight with the transcript preserved, server and client restart recall, resume 0.59 s (tunnel) / 0.65 s
  (client) / 1.09 s (server), the provider-slot worker exiting 3.036 s after the client, and a `launch-omp` smoke
  returning rc 0). The qualified `v0.2.16` DFlash2 rollback route (G23 on 2026-11-19, published `99ef483`: missing key
  refused before launch, wrong key HTTP 401, health RTT 4.8-5.2 ms, tunnel TTFT **0.179 s**, and a one-turn
  `launch-omp` smoke answering `ROUTE OK`) stays qualified; the `v0.2.13` DFlash2 route (`2af52b8`, stream TTFT
  `0.217 s`), the `v0.2.13` tuned-pack route (`8ab88b0`, stream TTFT `0.181 s`), the `v0.2.12` `df2` route (`243290e`,
  stream TTFT `0.247 s`), the `v0.2.12` `df2tuned` route (`2560f77`, stream TTFT `0.317 s`) and the `v0.2.11` `df2`
  route (`b812df9`, stream TTFT `0.270 s`) are earlier qualified history ([`docs/REMOTE.md`](docs/REMOTE.md)).
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
  a draft or a rollback installation. Beside the three `v0.2.11` quality-first PRO drafts above, the `v0.2.22` pair
  `df2conf05` draft carrying a `"Not qualified"` blocker (missed 38/96 A/B checks; no gate ran), the three `v0.2.16`
  drafts carrying `"Not qualified"` blockers (`b8b6f6b` — the RTX 5090 262K `envg` draft that failed G15, the PRO
  `df2tuned` tuned-pack draft that missed 17/90 A/B checks and was not overridden, and its Studio `df2tuned` route,
  which never ran G23), the five `v0.2.13`
  drafts carrying `"Not qualified"` blockers (`b2e9730` — the pair `env86gt` draft that missed 6/96 A/B checks on one
  32K request and `env86gts` `STRATA_QSA_SPLIT_ATTN=1` draft that missed 2/96 checks with targeted cold decode at
  `1.003 < 1.02`, the RTX 5090 `envgc` `STRATA_SPEC_COST=1` draft that missed 3/88 checks and 2/88 in replacement pairs
  and the full-model IQ3_S 262K low-RAM `...-iq3s-262k-lowram-kvvram-kvgrow-envg-...` draft whose first start refused
  when `--kv-grow`'s elastic K/V line was absent, and the PRO `df2conf055` `--draft-conf 0.55` standard-pack draft
  withdrawn before install), the `v0.2.12` PRO two-pass server and route drafts (`envpgt`, missed 3/96 A/B checks), the
  `v0.2.12` RTX 5090 two-pass draft (`envgt`, failed G18), the `v0.2.12` pair W4A8 draft (`env86gw`, missed cold TTFT,
  32K decode and inter-token gap in its A/B), the PRO `v0.2.11` `UD-Q4_K_XL` comparison screen (slower than the v0.2.11
  IQ3_S profile in every measured workload: single-request decode 0.85-0.91x, total throughput 0.73-0.84x) and `v0.2.9`
  `UD-IQ4_XS` and `NVFP4-QAD` model candidates (and their routes, while a 30-task Terminal-Bench comparison has not run),
  the `v0.2.11` RTX 5090 131K profile (failed G15 twice), and the RTX 5090 `v0.2.9` `kvvram-kvgrow` fallback
  (uninstalled) stay unqualified drafts.

### Current profile results

Per gate, for the four current local lanes above
([2026-11-26 windows measurements](docs/MEASUREMENTS.md#strata-v0222-windows-2026-11-26-stock-omp-1921),
[2026-11-19 windows measurements](docs/MEASUREMENTS.md#strata-v0216-windows-2026-11-19-stock-omp-1900),
[2026-11-09 windows measurements](docs/MEASUREMENTS.md#strata-v0213-windows-2026-11-09-stock-omp-18183),
[decision](docs/DECISION.md)). The `v0.2.22` figures come from each release's newest published receipts and evidence;
a complete-gate rerun's figures supersede its main chain's.

| Area | RTX PRO 6000, 4-slot DFlash2 (`df2`) + PLE direct + KV VRAM + envpg (`v0.2.22`, 2026-11-27; `v0.2.16` `df2` rollback in parens) | RTX 5090, 262K default, KV VRAM + KV grow + envg (`v0.2.22`, 2026-11-27; `v0.2.13` rollback in parens) | RTX 5090, 131K Coder alternative (`v0.2.22`, 2026-11-27) and full-model IQ3_S 131K low-RAM alternate (`v0.2.13`, 2026-11-09); `v0.2.16` Coder rollback in parens | RTX 4090 + RTX 3090, DFlash2 (`df2conf05`, `--draft-conf 0.5`) + split 24 + trim + PLE direct + env86gt two-pass (`v0.2.16`, 2026-11-19; `v0.2.13` rollback in parens) |
|---|---|---|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass | pass | pass (Coder and IQ3_S low-RAM alternate) | pass |
| Live prefix reuse in a session (lost on engine restart) | pass: 12 continuations, engine-reported (`v0.2.16` `df2` rollback: 12) | pass: 12 continuations, engine-reported (`v0.2.13` rollback: 15) | pass: 13 continuations, engine-reported on Coder (IQ3_S low-RAM alternate: 12; `v0.2.16` Coder rollback: 13) | pass: 13 continuations, engine-reported (`v0.2.13` rollback: 12) |
| Interleaved conversations | pass: A resumes after B; 48 uncached tokens on the controlled continuation, 38 parks (48,640 MiB conversation cache sized by stock's server; `v0.2.16` `df2` rollback: 48 uncached tokens, 38 parks, engine's 8,192 MiB cache), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation, 20 parks (engine's 4,352 MiB cache; `v0.2.13` rollback: 46 uncached tokens, 25 parks, 4,608 MiB cache), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation, 31 parks on Coder (engine's 3,584 MiB cache on Coder; IQ3_S low-RAM alternate: 46 uncached tokens, 29 parks, 2,304 MiB cache; `v0.2.16` Coder rollback: 48 uncached tokens, 29 parks, 3,584 MiB cache), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation, 45 parks (engine's 8,192 MiB cache; `v0.2.13` rollback: 47 uncached tokens, 28 parks), not an exact-output claim |
| Requests at once | up to 4, decoded together with per-slot DFlash2 drafters (`strata.drafting: "dflash2"`; the start prints `[strata] Drafting: DFlash2, one guess window per request slot (spare rows only)`, as on the `v0.2.16` rollback) | one at a time | one at a time | one at a time (DFlash2 at `--draft-conf 0.5`, read from the engine's `engine started:` argv) |
| Loopback, API key (including `/status`, `/v1/telemetry` and `/tool-media/` on `v0.2.13` / `v0.2.12`, and the key-checked `/v1/models/{id}` and `/models/{id}` on `v0.2.22`: no key or wrong key 401, correct key 200), fail-closed client, local-only routing, with an egress guard for OMP's startup catalog fetch | pass (0 non-loopback / 2,653 ETW events, 1 compaction; `v0.2.16` `df2` rollback: 0 non-loopback / 2,380 ETW events, 1 compaction) | pass (0 non-loopback / 3,007 ETW events, 1 compaction; `v0.2.13` rollback: 0 non-loopback / 7,061 ETW events, 2 compactions) | pass (0 non-loopback / 4,490 ETW events, 1 compaction on Coder; IQ3_S low-RAM alternate: 0 non-loopback / 3,737 ETW events, 2 compactions; `v0.2.16` Coder rollback: 0 non-loopback / 2,300 ETW events, 1 compaction) | pass (0 non-loopback / 3,043 ETW events, 1 compaction; `v0.2.13` rollback: 0 non-loopback / 8,390 ETW events, 2 compactions) |
| Engine or client restart, then continue from OMP's transcript (an engine restart re-prefills it; no state restoration) | pass, including G15 and G18L (G16 18.8 s, G20 18.9 s, G21 19.3 s, lowest available RAM 113.07 GiB in G19 / 115.42 GiB in G18L, G15 recall 17.7 s (idle kill), 17.6 s (mid-generation kill), G10 125.88 GiB available RAM, 78.75 GiB Windows commit headroom of a 219.70 GiB limit, PLE on direct SSD reads, KV in VRAM; `v0.2.16` `df2` rollback: G16 19.8 s, G20 23.0 s, G21 20.1 s, G15 recall 20.4 s (idle kill), 20.5 s (mid-generation kill), G10 113.52 GiB available RAM, 65.27 GiB Windows commit headroom) | pass, including G15, and G18L in its rerun (G16 14.6 s, G20 15.1 s, G21 15.3 s, lowest available RAM 8.67 GiB in G19 / 9.58 GiB in G18L, G15 recall 15.9 s (idle kill), 13.9 s (mid-generation kill), G10 12.64 GiB available RAM, 11.98 GiB Windows commit headroom of a 77.15 GiB limit; `v0.2.13` rollback: readiness 19.1-19.3 s, G15 recall 18.7 s (idle kill), 18.1 s (mid-generation kill), G10 14.14 GiB available RAM, 16.28 GiB Windows commit headroom) | pass on Coder and IQ3_S low-RAM alternate, including G15 and G18L (G16 14.6 s, G20 14.6 s, G21 14.8 s, lowest available RAM 7.70 GiB in G19 / 7.44 GiB in G18L, G15 recall 27.6 s (idle kill), 25.4 s (mid-generation kill), G10 11.17 GiB available RAM, 10.74 GiB Windows commit headroom of a 77.15 GiB limit on Coder; IQ3_S low-RAM alternate: readiness 25.4-27.7 s, G15 recall 22.4 s (idle kill), 20.8 s (mid-generation kill), G10 8.34 GiB available RAM, 10.41 GiB Windows commit headroom; `v0.2.16` Coder rollback: G16 14.7 s, G20 14.7 s, G21 14.9 s, G15 recall 30.4 s (idle kill), 28.7 s (mid-generation kill), G10 10.96 GiB available RAM, 14.25 GiB Windows commit headroom) | pass, including G15 and G18L (G16 43.2 s, G20 43.1 s, G21 43.4 s, lowest available RAM 58.40 GiB in G19 / 57.18 GiB in G18L, G15 recall 49.5 s (idle kill), 47.2 s (mid-generation kill), G10 65.96 GiB available RAM, 28.29 GiB Windows commit headroom of a 135.69 GiB limit; `v0.2.13` rollback: readiness 43.1-43.4 s, G15 recall 48.9 s (idle kill), 45.8 s (mid-generation kill), G10 65.95 GiB available RAM, 28.29 GiB Windows commit headroom) |
| Context window (262,144 tokens on the RTX PRO 6000, RTX 5090 default and pair; 131,072 on the RTX 5090 alternatives): exact limit, near-limit tool turns, explicit overflow (G17; on OMP `19.2.1` G17 allows 7,900 tokens of overhead) | pass (near-limit task 22.2 s; `v0.2.16` `df2` rollback: 23.7 s) | pass (near-limit task 27.4 s; `v0.2.13` rollback: 28.0 s) | pass (near-limit task 14.5 s on Coder; IQ3_S low-RAM alternate: 16.7 s; `v0.2.16` Coder rollback: 15.5 s) | pass (near-limit task 65.0 s; `v0.2.13` rollback: 55.9 s) |
| OMP compaction (reduced threshold and production long session, G18; OMP 19 refuses a threshold compaction when its fixed context, the system prompt and tool schemas, exceeds 80% of the threshold, so the reduced threshold is 11,000 tokens on OMP `19.2.1`, whose fixed context measured 6,793 tokens, and 10,000 tokens on OMP `19.0.0`, whose fixed context measured 5,940 tokens) | pass, with OMP's speculative compaction off (production 1 / reduced-threshold 6 compactions; `v0.2.16` `df2` rollback: production 1 / reduced-threshold 7 compactions) | pass, with OMP's speculative compaction off (production 1 / reduced-threshold 7 compactions; `v0.2.13` rollback: production 1 / reduced-threshold 2 compactions) | pass on Coder and IQ3_S low-RAM alternate, with OMP's speculative compaction off (production 1 / reduced-threshold 6 compactions on Coder; IQ3_S low-RAM alternate: production 1 / reduced-threshold 6 compactions; `v0.2.16` Coder rollback: production 1 / reduced-threshold 6 compactions) | pass, with OMP's speculative compaction off (production 1 / reduced-threshold 7 compactions; `v0.2.13` rollback: production 1 / reduced-threshold 4 compactions) |
| Cancelling a *queued* request | pass, with all four slots generating | pass | pass | pass |
| Tool call cut off mid-arguments (G04) | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call |
| Six-task coding evaluation, 18 scored attempts (G24) | 15/18 (pilot 5/6, batch wall 399 s; `v0.2.16` `df2` rollback: 15/18, pilot 6/6, batch wall 395 s) | 14/18 (pilot 5/6, batch wall 448 s; `v0.2.13` rollback: 16/18, tool-loop 1/3, pilot 5/6, batch wall 798 s) | 16/18 on Coder (pilot 5/6, batch wall 550 s) and 16/18 (tool-loop 1/3, pilot 6/6, batch wall 716 s) on IQ3_S low-RAM alternate (`v0.2.16` Coder rollback: 15/18, pilot 5/6, batch wall 648 s) | 16/18 (pilot 5/6, batch wall 774 s; `v0.2.13` rollback: 16/18, tool-loop 1/3, pilot 5/6, batch wall 952 s; not comparable across OMP 19.0.0) |
| Guarded install and QUICKSTART example alongside earlier tuples (G26) | pass (install 17.1 s, start 23.3 s; `v0.2.16` `df2` rollback: install 17.8 s, start 31.8 s; first install on v0.2.8 took 1,063.2 s) | pass (install 13.0 s, start 21.9 s; `v0.2.13` rollback: install 11.9 s, start 22.3 s; first install on v0.2.8 took 365.6 s) | pass (install 12.3 s, start 17.7 s on Coder; IQ3_S low-RAM alternate: install 37.6 s, start 57.5 s; `v0.2.16` Coder rollback: install 12.6 s, start 34.2 s; first install on v0.2.8 took 297.8 s) | pass (install 32.3 s, start 54.3 s; `v0.2.13` rollback: install 32.9 s, start 67.2 s; first install on v0.2.8 took 820.3 s) |
<details>
<summary><strong>Earlier qualified profiles and rollbacks</strong></summary>

Every profile and client route ledger is listed in [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md); the owner's
qualification decisions, retained failures, the G15 probe correction, the G16 predicate fix, the G18 fixture fix
and the OMP speculative-compaction setting are in [`docs/DECISION.md`](docs/DECISION.md), with full figures in
[`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md).

- **2026-11-19 — Strata `v0.2.16` + OMP `19.0.0` (`rtxpro6000-win-a` DFlash2, `rtx5090-win-a` 131K Coder, `rtx3090-win-a` pair `df2conf05`, Mac Studio route):**
  current rollbacks on the PRO (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.16-omp19.0.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.16-omp19.0.0/qualification.json);
  G24 15/18, pilot 6/6, batch wall 395 s, G15 recall 20.4 s (idle kill) and 20.5 s (mid-generation kill) on its
  rerun, restart readiness G16 19.8 s, G20 23.0 s and G21 20.1 s, 113.52 GiB available RAM and 65.27 GiB G10 commit
  headroom), the RTX 5090 131K Coder alternative
  (`win11-rtx5090-coder-iq1m-131k-strata0.2.16-omp19.0.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.16-omp19.0.0/qualification.json); G24 15/18, pilot 5/6,
  batch wall 648 s, 34 GiB start floor, 3,584 MiB cache, G15 recall 30.4 s (idle kill) and 28.7 s (mid-generation
  kill), restart readiness G16 14.7 s, G20 14.7 s and G21 14.9 s, 10.96 GiB available RAM and 14.25 GiB G10 commit
  headroom) and the Mac Studio client route
  ([`0.2.16 df2 route`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.16-omp19.0.0.json),
  [ledger](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.16-omp19.0.0/qualification.json),
  tunnel TTFT 0.179 s); the same window's pair `df2conf05` profile is still current (above);
  [measurements](docs/MEASUREMENTS.md#strata-v0216-windows-2026-11-19-stock-omp-1900) and
  [decision](docs/DECISION.md#update-2026-11-19-strata-v0216-with-omp-1900-qualifies-on-the-pro-the-rtx-5090-131k-alternative-the-pair-and-the-studio-route-the-rtx-5090-262k-default-stays-on-v0213).
- **2026-11-09 — Strata `v0.2.13` + OMP `18.18.3` (`rtxpro6000-win-a` DFlash2 and tuned-DFlash2 alternate, `rtx5090-win-a` 131K Coder, `rtx3090-win-a` pair `df2conf05`, Mac Studio routes):**
  earlier qualified history on the PRO (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3/qualification.json);
  G24 15/18, pilot 5/6, batch wall 491 s, G15 recall 44.8 s, restart readiness 31.1-31.4 s, 127.53 GiB available
  RAM and 83.66 GiB G10 commit headroom; alongside the qualified `v0.2.13` tuned-pack alternate
  `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3/qualification.json);
  G24 15/18, pilot 5/6, batch wall 485 s, G15 recall 44.5 s, restart readiness 31.1-31.3 s, 127.83 GiB available RAM
  and 83.85 GiB G10 commit headroom), the RTX 5090 131K Coder alternative
  (`win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3`,
  [ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3/qualification.json); G24 16/18, pilot 5/6,
  batch wall 624 s, 34 GiB start floor, 4,096 MiB cache, G15 recall 31.7 s, restart readiness 16.6-16.8 s,
  12.63 GiB available RAM and 15.39 GiB G10 commit headroom), the pair, which is still the rollback of the current
  `v0.2.16` pair profile
  (`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3/qualification.json);
  G24 16/18, pilot 5/6, batch wall 952 s, restart readiness 43.1-43.4 s, 65.95 GiB available RAM and 28.29 GiB G10
  commit headroom) and the Mac Studio client route
  ([`0.2.13 df2 route`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3.json),
  [ledger](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3/qualification.json),
  stream TTFT 0.217 s; alongside the [`0.2.13 df2tuned route`](routes/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3.json),
  [ledger](releases/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3/qualification.json),
  stream TTFT 0.181 s); the same window's RTX 5090 262K default is now the rollback of the current `v0.2.22` 262K
  default, and its full-model IQ3_S 131K low-RAM alternate is still current (above);
  [measurements](docs/MEASUREMENTS.md#strata-v0213-windows-2026-11-09-stock-omp-18183) and
  [decision](docs/DECISION.md#update-2026-11-09-strata-v0213-with-omp-18183-qualifies-on-every-host-and-the-studio-routes-the-pair-adopts-dflash2-confidence-05-and-the-rtx-5090-qualifies-full-model-iq3_s-131k-low-ram-as-an-alternate).
- **2026-11-07 and 2026-11-08 — Strata `v0.2.12` + OMP `18.18.0` (`rtxpro6000-win-a` DFlash2 and tuned-DFlash2 alternate, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair two-pass and `env86g` DFlash2, Mac Studio routes):**
  earlier qualified history on the PRO (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0/qualification.json);
  G24 15/18, pilot 6/6, batch wall 522 s, G15 recall 44.2-44.4 s, restart readiness 31.1-31.3 s, 126.94 GiB available
  RAM and 83.13 GiB G10 commit headroom; alongside the qualified `v0.2.12` tuned-pack alternate
  `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`,
  [ledger](releases/win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0/qualification.json);
  G24 15/18, pilot 5/6, batch wall 581 s, G15 recall 29.0 s, restart readiness 31.0-31.4 s, 126.99 GiB available RAM
  and 83.24 GiB G10 commit headroom), the RTX 5090 262K default
  (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0/qualification.json); G24
  15/18, pilot 6/6, batch wall 787 s, 34 GiB start floor, 4,096 MiB cache, restart readiness 19.1-19.3 s, 13.05 GiB
  available RAM and 19.53 GiB G10 commit headroom) and 131K alternative
  (`win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0/qualification.json); G24 15/18, pilot 5/6,
  batch wall 726 s, 34 GiB start floor, 3,584 MiB cache, G15 recall 30.9-32.0 s, restart readiness 16.6-18.9 s,
  11.37 GiB available RAM and 18.72 GiB G10 commit headroom), the pair
  (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0/qualification.json);
  G24 15/18, pilot 6/6, batch wall 968 s, restart readiness 55.3-55.5 s, 19.40 / 17.90 GiB expert caches, 65.74 GiB
  available RAM and 28.21 GiB G10 commit headroom; alongside the qualified `v0.2.12` `env86g` base profile
  `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0/qualification.json);
  G24 15/18, pilot 5/6, batch wall 906 s, restart readiness 55.2-55.6 s, 65.66 GiB available RAM and 28.18 GiB G10
  commit headroom) and the Mac Studio client route
  ([`0.2.12 df2 route`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0.json),
  [ledger](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0/qualification.json),
  stream TTFT 0.247 s; alongside the [`0.2.12 df2tuned route`](routes/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0.json),
  [ledger](releases/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0/qualification.json),
  stream TTFT 0.317 s);
  [measurements](docs/MEASUREMENTS.md#strata-v0212-windows-2026-11-07-stock-omp-18180) and
  [decision](docs/DECISION.md#update-2026-11-0708-strata-v0212-with-omp-18180-qualifies-on-every-host-and-the-studio-routes-the-pair-adopts-two-pass-selection-and-the-pro-qualifies-the-tuned-dflash2-pack-as-an-alternate).
- **2026-11-06 — Strata `v0.2.11` + OMP `18.16.0` (`rtxpro6000-win-a` DFlash2 and batch-MTP, `rtx5090-win-a` 262K, `rtx3090-win-a` pair DFlash2, Mac Studio routes):**
  earlier qualified history on the PRO (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`,
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
  available RAM and 20.30 GiB G10 commit headroom; the `v0.2.11` 131K draft failed G15 twice and stays unqualified),
  the Mac Studio client route
  ([`0.2.11 df2 route`](routes/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json),
  [ledger](releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json),
  stream TTFT 0.270 s; alongside the [`0.2.11 batch-MTP route`](routes/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0.json),
  [ledger](releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json),
  stream TTFT 0.174 s) and the pair
  (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`,
  [ledger](releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/qualification.json);
  G24 15/18, pilot 5/6, batch wall 896 s, complete G13 rerun at `611c342`, restart readiness 40.5-40.8 s, 19.41 /
  17.90 GiB expert caches, 66.35 GiB available RAM and 28.70 GiB G10 commit headroom);
  [measurements](docs/MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160) and
  [decision](docs/DECISION.md#update-2026-11-06-strata-v0211-with-omp-18160-qualifies-on-the-pro-rtx-5090-262k-pair-and-studio-route-131k-stays-on-v0210).
- **2026-11-03 — Strata `v0.2.10` + OMP `18.16.0` (`rtxpro6000-win-a`, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair DFlash2 and `env86g`, Mac Studio route):**
  earlier qualified history on the RTX 5090 131K alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`,
  [ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/qualification.json); G24 16/18, pilot 6/6,
  34 GiB start floor, 3,584 MiB cache, restart readiness 18.7-18.9 s), on the RTX 5090
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
- `fetch` downloads the pinned OMP binary, the Strata engine archive (plus a llama.cpp archive where a profile pins
  one; `v0.2.16` and `v0.2.22` profiles pin none) and model shards, resumable, and verifies every byte before anything is used.
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
