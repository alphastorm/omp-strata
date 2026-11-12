# Upstream findings

This file records defects, setup-review boundaries and upstream fixes observed in stock
[Strata](https://github.com/Niko1221/Strata) and stock [Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP).
Every status note below is bounded by the check date recorded in its entry:

- **Active on a current host (checked 2026-11-09):** [Strata items 7 and 8](#strata)
  ([Strata#2463](https://github.com/Niko1221/Strata/issues/2463), closed on 2026-10-19 as not planned, and
  [Strata#4518](https://github.com/Niko1221/Strata/issues/4518), opened on 2026-10-28 and fixed upstream in `v0.2.8`
  on 2026-10-29) — after Strata `v0.1.44.1`'s K=45 automatic layer-split regression left its pair profile draft,
  `v0.2.1`'s default K=25 split without `--gpu-roles` (layers 0-24 / 25-47; `v0.1.43.1`: 0-31 / 32-47) persists in
  stock `v0.2.3` through `v0.2.13` (100K-token time to first token (TTFT) 36.2 s on `v0.2.3`). On engine `0.1.52`
  (Strata `v0.2.7`), the automatic per-layer embedding (PLE) residency policy locked the 26.8 GiB PLE table in RAM on
  the 128 GB-RAM RTX 4090 + RTX 3090 pair (~31.4-37.5 s at start), left the automatic conversation cache off
  (`/metrics` `conversation_cache`: `enabled: false`, `budget_mib: 0`) and reduced G10 serving Windows commit headroom
  to 1.03 GiB (0.632-1.331 GiB in a later bench) versus 27.3 GiB on `v0.2.3` at the same 135.7 GiB limit
  ([Strata#4518](https://github.com/Niko1221/Strata/issues/4518); the `v0.2.7` roles draft with PLE in RAM stays held).
  On engine `0.1.54` (Strata `v0.2.8`), `Strata#4518`'s fix was measured on Windows on the measurement-only
  stock-residency draft (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`): the
  policy locked the 26.8 GiB table (33.9-34.0 s), then gave the lock back on both starts and sized the automatic
  conversation cache at 4,864 MiB (106-112 s to ready), against 8,192 MiB and 61-63 s to ready with `--ple-io direct`
  at matching 100K-token TTFT (31.2 s with PLE direct versus 30.9 s with stock residency;
  [MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-stage-order-and-strata4518-on-engine-0154)). On `v0.2.13` + OMP
  `18.18.3`, the current pair profile
  (`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`,
  rolling back to
  `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`)
  pins stock roles (`--gpu-roles 0=main,1=helper`, RTX 4090 as Main staged last; layers 0-23 / 24-47), manual split 24
  (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, `strata.trim_stage_weights: true`: 19.40 /
  17.90 GiB expert caches on `v0.2.12` `df2`, 19.41 / 17.90 GiB on `v0.2.11` `df2`, 19.41 / 18.31 GiB on `v0.2.10`
  `df2` and 19.14 / 17.75 GiB on `v0.2.10` `pw2` vs 17.35 / 16.01 GiB without trim), `strata.ple_io: "direct"`
  (`--ple-io direct`), `strata.engine_env` `sm86_table` + `gdn_stack` + `select_two_pass` (`STRATA_SELECT_TWO_PASS=1`),
  and stock DFlash2 drafting alone (`strata.drafting: "dflash2"` packed offline from pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` files, no `--pipeline-windows 2`) with `strata.drafting_args:
  {"--draft-conf": "0.5"}` written to stock `user_args` (qualified on 2026-11-09, published `440fa1b`, under the
  owner's decision `"Run the --draft-conf 0.5 main; it becomes current if every gate passes"` after passing all 96
  plain checks against `v0.2.12` and every gate in its own chain once `fb8740a` fixed carried-`user_args` install
  verification, whereas the unpinned `v0.2.13` `env86gt` base missed 6 of 96 checks on one 32K request), keeping the
  8,192 MiB automatic conversation cache (28.21 GiB G10 serving Windows commit headroom of a 135.69 GiB limit on the
  `v0.2.12` `env86gt` rollback, 28.18 GiB on `v0.2.12` `env86g`, 28.70 GiB on `v0.2.11` `df2`, 27.51 GiB on `v0.2.10`
  `df2`, 27.54 GiB on `v0.2.10` `pw2` `env86g`, 27.77 GiB on `v0.2.9` `env86g`, 27.74 GiB on the `v0.2.9` base,
  27.8 GiB on `v0.2.8` split-24 trim and 27.9 GiB on `v0.2.8` `roles-pledirect`; [decision](DECISION.md)).
- **Latest qualified source review (2026-11-09, qualified 2026-11-09):**
  [Strata v0.2.13 / engine 0.1.59](#strata-v0213-setup-and-start-path-review-engine-0159),
  [engine 0.1.59 opt-in groups](#engine-0159-opt-in-groups) and
  [stock OMP 18.18.3](#stock-omp-18183-surface) cover tag
  `fb57f7472c2ab4d176c216b30ed1d6b5e6132ef0` (`d2f096475817d4666c364c820b0ca830f751cfc5`), Windows CUDA 13 Qwen engine
  `0.1.59` (`712fec6b4297+cuda13.0`) and stock OMP `18.18.3` (`21f1188cf88b2f534c092181968cd5a4d1a9c296`), qualified
  across the PRO's four-slot `df2` DFlash2 current profile
  (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`, published `2af52b8`)
  rolling back to its `v0.2.12` `df2` predecessor, with the `v0.2.13` tuned DFlash2 pack arm
  `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` (`8ab88b0`)
  qualified as a non-current alternate; the RTX 5090 262K `kvvram-kvgrow-envg` default
  (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`, `d3c96fb`) rolling back to its
  `v0.2.12` predecessor, the 131K Coder alternative `win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3`
  (`d0c2e28`) rolling back to its `v0.2.12` predecessor, and the full-model IQ3_S 131K low-RAM resident profile
  `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3` (`6e2dda2`) qualified as a non-current alternate; the
  pair's `--draft-conf 0.5` DFlash2 `df2conf05` `env86gt` current profile
  (`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`,
  `440fa1b`) rolling back to its qualified `v0.2.12` `env86gt` predecessor; and the Studio's `df2` current route
  (`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`, `2af52b8`) rolling back to its
  `v0.2.12` `df2` route, with `client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`
  (`8ab88b0`) qualified as a non-current alternate route; the five `v0.2.13` drafts — the pair's unpinned `env86gt` base
  (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`)
  and `env86gts`
  (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3`),
  the RTX 5090's `envgc` (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3`) and IQ3_S 262K
  (`win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`), and the PRO's `df2conf055` — stay
  unqualified drafts with `"Not qualified"` blockers (`b2e9730`; [decision](DECISION.md)).
- **Previous qualified source review (2026-11-07, qualified 2026-11-08):**
  [Strata v0.2.12 / engine 0.1.58](#strata-v0212-setup-and-start-path-review-engine-0158),
  [stock engine opt-in groups](#stock-engine-opt-in-groups-v0212--0158) and
  [stock OMP 18.17.0–18.18.0](#stock-omp-18170-and-18180-surface) cover Windows CUDA 13 Qwen engine `0.1.58` and stock
  OMP `18.18.0` (now the rollback on the PRO `df2` current profile, the RTX 5090 262K `kvvram-kvgrow-envg` default and
  131K Coder alternative, the pair `df2conf05` current profile, and the Studio `df2` route, and earlier qualified
  history on the PRO `v0.2.12` `df2tuned` alternate profile and its Studio route and on the pair `v0.2.12` `env86g`
  DFlash2 base profile; the PRO two-pass server and route drafts, the RTX 5090 two-pass draft that failed G18, and the
  pair W4A8 draft stay unqualified drafts; [decision](DECISION.md)).
- **Earlier qualified source review (2026-11-05, qualified 2026-11-06):**
  [Strata v0.2.11 setup and start path](#strata-v0211-setup-and-start-path-review-engine-0157),
  [stock DFlash2 batch-slot arm](#stock-dflash2-batch-slot-arm-v0211--0157),
  [PRO quality-first one-slot comparison admissions](#pro-quality-first-one-slot-comparison-admissions) and
  [DeepSeek V4.1-Flash comparison admission](#deepseek-v41-flash-comparison-admission) cover tag
  `4a4160162e4a402e082f41aa0a88e6eed629d913` (`c3b3f5035506f3e966f1b4b7b188aeaabae92f1d`), Windows CUDA 13 Qwen engine
  `0.1.57` and the separate `strata-dsv41` `0.1.57` package, with unchanged [stock OMP `18.16.0`](#stock-omp-18160-surface)
  (retained as earlier qualified history on the PRO `v0.2.11` `df2` and `batchmtp` profiles and Studio routes, the RTX
  5090 262K `v0.2.11` `kvvram-kvgrow-envg` profile, and the pair `v0.2.11` `df2` profile;
  `win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0` stays an unqualified draft after failing G15 twice on
  2026-11-06; the PRO `v0.2.11` quality-first one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and six-expert `DeepSeek V4.1-Flash
  IQ2_XS` drafts, the PRO `v0.2.11` four-slot `UD-Q4_K_XL` screen — slower than the `v0.2.11` IQ3_S profile in every
  measured workload: single-request decode 0.85–0.91x, total throughput 0.73–0.84x — and the `v0.2.9` `UD-IQ4_XS` and
  `NVFP4-QAD` model candidates stay comparison-only drafts).
- **Earlier qualified source review (2026-11-03, qualified 2026-11-03):**
  [Strata v0.2.10 setup](#strata-v0210-setup-review-component-engine),
  [stock DFlash2 pair arm](#stock-dflash2-pair-arm-v0210--0156),
  [engine 0.1.56 environment and start path](#stock-engine-environment-v0210--0156), and
  [stock OMP 18.16.0](#stock-omp-18160-surface) cover tag
  `db0500a53119a349fa44497099d6e28a83ded34a` (`ffa80d73133ea5c548aefe57889a16e8085a938f`) and Windows CUDA 13 engine
  `0.1.56`, with [stock OMP `18.16.0`](#stock-omp-18160-surface) (retained as earlier qualified history on the RTX 5090
  131K alternative, the PRO `v0.2.10` `kvvram-envpg`, RTX 5090 262K `v0.2.10` `kvvram-kvgrow-envg`, pair `v0.2.10`
  `df2` and `pw2` `env86g`, and Studio `v0.2.10` `kvvram-envpg` route; the RTX 5090 `v0.2.9` `kvvram-kvgrow`
  fallback stays an uninstalled draft, the PRO `v0.2.9` `UD-IQ4_XS` and `NVFP4-QAD` model candidates and their routes stay
  comparison-only drafts, the `v0.2.8` stock-residency pair draft stays measurement-only, the `v0.2.7` pair roles draft
  with PLE in RAM stays held, and the `v0.2.7` pair default-split draft stays unmeasured); the earlier v0.2.9, v0.2.8,
  v0.2.7, v0.2.3, v0.2.2, v0.2.1 and v0.1.44.1 reviews remain below.
- **Earlier defects and workarounds (checked 2026-09-30 through 2026-10-07):** [Strata items 1–6](#strata) were
  closed upstream across `v0.1.28`, `v0.1.31`, `v0.1.32` and `v0.1.40`. [OMP items 1–12](#omp) record client
  behaviors and pull requests checked through `18.4.10` (2026-10-02) and `main` `7ac4b18` / `18.8.0`–`18.8.2`
  (2026-10-07); notes such as "no release contains it yet" or "every profile pins 18.4.8 or older" state status
  at those check dates, and the integration's own guards remain active.

These defects and surprises in the stock components were observed while qualifying OMP 18.4.0 (`401778d`)
against Strata v0.1.27 (`a790805`). Each has a reproducer in this repository. The Strata items are reported
upstream as linked below, after re-verification at the same Strata commit. The OMP items go upstream as pull
requests rather than issues, as upstream `CONTRIBUTING.md` asks for work the reporter will submit.
The integration works around them only where a supported setting exists.

Upstream status was re-checked on 2026-09-30 against Strata v0.1.28 (`bbaaabb`), on 2026-10-01 against
**v0.1.30 (`30ec18e`), pinned by the second candidate** (`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`,
which also moves OMP to 18.4.6), later on 2026-10-01 against **v0.1.31 (`9259cad`), pinned by the third tuple's
draft profiles** (RTX 3090 and RTX 4090 hosts, with OMP 18.4.8), and on 2026-10-02 against **v0.1.34 (`1678de3`),
pinned by the fourth tuple** (all three hosts, with OMP 18.4.10). v0.1.28 fixed items 1, 3, 4 and 6 and the second
candidate's real-host gates confirm them; v0.1.31 fixes items 2 and 5, and v0.1.34 keeps both fixes (host-free
suite; setup and server source reading). The upstream issues behind all six items are closed. The first candidate's
profile keeps v0.1.27 with every item present. "Mock tier" below means the stock frontend with its MockEngine (no
GPU).

**Upstream rewrote Strata's history on 2026-10-06** (v0.1.40.1 release notes). Every release tag now points to a
new commit; checked through the GitHub API for each tag a profile pins (v0.1.27 through v0.1.39), every new commit
has the same tree as the pinned one, so release contents did not change. Profiles keep their original commit pins,
and `install` fetches exactly those SHAs. GitHub still served all seven on 2026-10-06, but nothing upstream
references them any more, so a later install of an existing profile may fail once GitHub drops them. New drafts pin
the rewritten commits. The same notes number the hotfix `v0.1.40.1` with four parts, which `upstream_watch`
now reads (stock setup reads it as 0.1.40).

## Strata v0.2.13 setup and start-path review (engine 0.1.59)

This section records the source admission before hardware qualification; on 2026-11-09 every host lane and both
Studio routes qualified on stock Strata [v0.2.13](https://github.com/Niko1221/Strata/releases/tag/v0.2.13) with stock
OMP `18.18.3` ([decision](DECISION.md)). Stock [v0.2.13](https://github.com/Niko1221/Strata/releases/tag/v0.2.13) pins
tag object
`fb57f7472c2ab4d176c216b30ed1d6b5e6132ef0`, source commit
`d2f096475817d4666c364c820b0ca830f751cfc5`, app **0.2.13**, Control/engine **0.1.59**.
The release's `strata-engine-0.1.59-windows-x86_64-cuda-cuda13.tar.gz` is **630,783,433 bytes**,
SHA-256 `3f071a7ccbbf3dcdefed8bff777896d8dd0b580417a078154a7d2c2402ec4158`.
`inspect_archive` verified every member and build record without executing the engine:
build **`712fec6b4297+cuda13.0`**, source `f-0213-rc`, commit `712fec6b4297`, manifest SHA-256
`102238fc50b9941a990cafcb0ead565eaf34ae235685d8fbdd4471774f066f88`, CUDA 13.0, NVIDIA floor 580.65.
Its seven member names match 0.1.58. The archive-pinned entrypoint contains all three DFlash2 capability markers
(`MARK_ON`, `MARK_VOCAB`, `MARK_SELQ4`); marker presence is not a start or performance result.

### Setup seam and unchanged inputs

[`setup.py:11088-11093`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/setup.py#L11088-L11093)
now delegates config assembly to
[`setup_config.config_for`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/strata_control/setup_config.py#L114-L582).
The planner reads both files at the same immutable commit. It pins the complete new module, imports, identity-only
alias preamble and three-statement caller seam, then applies the existing reviewed statement loop to the moved body.
CPU-worker recommendations move with it and retain their earlier digest; disk estimates and fresh-write review stay
on setup's main body. `write_config` still matches the existing install review:
`875c4111fb44d7659fa40daf85d440ea08961a55b3b8e5500b01b0d91ac7b959`.

The new feed/shape branches remain unreachable for explicit built-in `--family qwen/coder`, pinned `--model` and
`--yes`: exact guards must be false; `SHAPE_ENGINE` is empty. In particular, the new
[`neutral_profile_if_other_shape`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/strata_control/setup_config.py#L83-L111)
file writer never enters the planner's generic call vocabulary. The changed informational default recommendation
filters feed families before selecting the same built-in recommendation. Shape-engine downloads, signed-feed
discovery and other new model families are not admitted.

[`unsloth_default_env:4361-4380`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/setup.py#L4361-L4380)
no longer writes `STRATA_HC_Q8`: CUDA engine
[`generate.cpp:4432-4441`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/program/generate.cpp#L4432-L4441)
owns the default when the GGUF carries Q8_0 hyper-connections. GSQ-RCO's BF16 path is unchanged upstream.
The validator's versioned Unsloth setup-env projection omits HC_Q8 for engine >=0.1.59; this does **not** admit
v0.2.13 Unsloth budget planning or DeepSeek comparison redrafts.

The candidate checklist retains the same 12 generated config keys and server route set. Its optional-write census
also reads the moved module, so writes do not disappear from the report. Runtime requirements, CUDA wheels,
model revisions, MTP inputs, DFlash2 standard/tuned assets and packer are unchanged. Drafts reuse
`locks/strata-python-cp313-win_amd64-strata0.2.11.txt`; no replacement Python lock is needed.

### Server closure, environment literals and start identity

`SERVER_REVIEWS["0.2.13"]` has four roots: `child_env`, `engine_args`, `mtp_retry_args`, `nodraft_retry_args`.
The closure loses `parallel_stack_env`, `parallel_stack_platform`, `gdn_stack_env` and `parallel_slots`.
Import bindings, `vram_fit`, `draft_layer`, `nonblocking_out` and `paths` retain their reviewed digests.
The changed full-field AST digests, computed with the repository's `reviewed_hash`, are:

| Boundary | SHA-256 |
| --- | --- |
| `child_env` | `e7fd3b41f642e54d873a3d6314138a9286a75d79833a4000f4213f94c1248b5e` |
| `engine_args` | `9ad04e6e081fb20b66a9b6f15a3c7241bbf65ab0d3a487fa04af8e90eb6008d6` |
| `drafting.py` | `0477270888872f80daeb14343e16e3cfca5cadb377a63e87213c4743d8364704` |
| `runtime.py` (docstring change) | `a0ed2a07001c57a51094f1254dd1d03fa457f052fcbde3cdcb48d7aaf4be42d5` |
| `drafting_fetch.py` | `feee8d364e1aa16caa18202fbc9898087e35afbc814f2d1d7cd9fd373af34fa3` |

`SERVER_ENV_CONSTANTS` is per-review. v0.2.13 no longer expects the deleted server dictionaries: `parallel_stack`
and `gdn_stack` must match the literal engine tables
[`arch_defaults.cpp:203-243`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/core/arch_defaults.cpp#L203-L243)
at the same source commit. Their automatic application is **Linux CUDA only**
([`generate.cpp:3881-3887`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/program/generate.cpp#L3881-L3887));
Windows still needs the existing explicit config env pins. All **22** variables across the five existing groups
retain their read sites and meanings; `nv_defaults.cpp` and the mixed-pair sm_86 rule are unchanged.
Engine **0.1.59** joins `ENGINE_ENV_REVIEWED_ENGINES`; no new env group or tuning arm is added.

The unchanged `user_args.py` module is explicitly digest-bound in this review
(`625e4282ba491b97cd8073a9c687acc90023ecb115233cd123eb6a36b7b717ae`); only the reviewed confidence pin below
admits Qwen `user_args`, never arbitrary user arguments.
New engine >=0.1.59 roots also byte-bind `tools/strata_tokenizer.py` and `serve/toolformat.py` in runtime identity;
the 0.1.57/0.1.58 nine-source list is unchanged. Both new sources have admission digests as well.
The tokenizer now
[refuses unknown `pre` rules](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/tools/strata_tokenizer.py#L100-L124)
instead of silently using qwen35. The template
[classifier](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/serve/toolformat.py#L20-L33)
selects JSON recovery only for JSON-form templates; stock Flash-Next's XML form keeps the existing parser.
The Coder pack's actual tokenizer `pre` still needs checking during host qualification.

`DRAFTING_FETCH_REVIEWS["0.2.13"]` binds the refactor; its network surface and `tools/dflash2_pack.py` are unchanged.
Installation still uses the offline packer and stock verification helpers, never `drafting_fetch.ensure`.
The arena-RAM fallback diagnostic now also reaches stdout in serve mode
([`generate.cpp:7753-7766`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/program/generate.cpp#L7753-L7766));
the existing start refusal checks both streams. Stage-order admission for `0.1.59` waited during source review for a
measured pair start and was admitted on 2026-11-09 (`6eb9f05`) after the pair measurement start on `rtx3090-win-a`.

On `rtx5090-win-a` (2026-11-09, two fleet-custody windows with production NInfer down `~15:32–18:09Z` and `~18:25–19:19Z`
and full restoration each time: new `"WSL integration ... provisioned"` line, fleet return and health `200`), the 262K
`envg` profile (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`) passed all 88 of 88 checks
against `v0.2.12` (throughput w1 `1.006` / w3 `0.995`, per-request `1.024` / `0.975`, TTFT p50 `0.989` / `1.002`, TPOT
p50 `0.975` / `1.023`; cold decode `0.986–1.018`, prefill `0.998–1.075`) and every gate in its requalification chain
including G15 and G18L (G24 `16/18`, `tool-loop` `1/3`; published `d3c96fb`, current), and the 131K Coder profile
(`win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3`) followed the 262K pass without a separate A/B (as in
`v0.2.12`) and passed every gate (G24 `16/18`; published `d0c2e28`, current 131K alternative;
[MEASUREMENTS.md](MEASUREMENTS.md), [DECISION.md](DECISION.md)).

### Big-Blackwell DFlash2 defaults

Stock
[`big_blackwell`, `window_for` and `apply`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/strata_control/drafting.py#L759-L779)
use window 8 on one CUDA sm_120 card with at least **48,000,000,000 bytes** and at least 12,000 estimated expert
slots. The tuned IQ3_S pack gets confidence **0.55** there; standard packs keep the slot rule.
This is not ambiguous for a successful tuned start:
[`tuned_applies`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/strata_control/drafting.py#L419-L442)
already requires the resident `slots >= 12000` condition, exactly the slot test in `big_blackwell`.
The reviewed tuned profiles also require IQ3_S, `--expert-cache auto` and a single supported card.
Thus a tuned pack actually selected on the >=48 GB sm_120 class uses 0.55, not a possible 0.35 alternative.
Without a confidence pin, other tuned cases retain 0.35; multi-GPU remains 0.35; a single-card standard pack can use
0.35/0.5/0.7/0.8, never 0.55. `dflash2.stock_draft_confs` is the one profile/version stock-confidence rule;
`expected_draft_confs` substitutes only the profile's explicit pin for start verification.

| Lane | Engine 0.1.58 | Engine 0.1.59 |
| --- | --- | --- |
| PRO standard pack, four slots | window 6, confidence 0.35 | window 8, confidence 0.35 |
| PRO tuned IQ3_S, four slots | window 6, confidence 0.35 | window 8, confidence 0.55 |
| RTX 3090 + RTX 4090 pair | server `--spec 6`, confidence 0.35; engine reports window 8 after lookup widening | unchanged |
| RTX 5090 Coder, both contexts | MTP, not DFlash2 | unchanged |

Start verification records and checks the engine's `windows up to N tokens` value, pack, selector and slot-drafter
evidence; it does not infer a window from the server's ON line. Historical PRO 0.1.58 window-6 fixtures stay valid.
The upstream measurements behind the new defaults are one-card/single-request results, **not** evidence for our
four-slot PRO. Both PRO version lanes need version A/B and host gates; the separate confidence arms below inherit
no qualification from them.

Observed on `rtxpro6000-win-a` (2026-11-09, three interleaved pairs `A1 B1 B2 A2 A3 B3`, cold starts, `B/A` geometric
means against the qualified `v0.2.12` profile; [MEASUREMENTS.md](MEASUREMENTS.md), [DECISION.md](DECISION.md)):
- **Four-slot DFlash2 `v0.2.13` vs `v0.2.12` (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`):**
  missed 11 of 90 checks because stock `v0.2.13` runs DFlash2 window 8 (was 6) on this card — inter-output-event
  latency p95 `1.171–1.188` at every depth, `w2/c1` largest gap p95 `1.173`, `w2/c4` TTFT p95 `1.118`, and `w2/c4`
  TPOT max `1.067` — while throughput was `0.986–0.999`, per-request `0.964–1.015`, TTFT p50 `1.009–1.036`, TPOT p50
  `0.981–1.033`, and server decode reported `0.958–1.015`. Under the owner's override (`"Override the base as current,
  and also qualify the tuned pack as an alternate"`), its requalification passed every gate including G15, G17 and G18L
  (G24 `15/18`, `tool-loop` `0/3`, as in `v0.2.12`), and its Studio route
  `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` passed G23 (missing key refused before
  launch, wrong key HTTP 401, health RTT `5.8–7.7 ms`, stream TTFT `0.217 s`, tunnel drop failed the turn in flight
  with the transcript preserved) and `launch-omp` smoke `"ROUTE OK"` (published `2af52b8`, restored-state `ab96ab4`).
  Both are **current** on the PRO and Studio (rolling back to the `v0.2.12` four-slot DFlash2 profile and route).
- **Tuned DFlash2 pack `v0.2.13` vs `v0.2.12` (`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`, which stock `v0.2.13` runs at `--spec 8` and `--draft-conf 0.55` on this card):**
  missed 15 of 90 checks with the same window-8 burstiness (inter-output p95 `1.169–1.172`, `w2/c1` largest gap p95
  `2.151`, `w2/c4` TTFT p50 `1.129`) and `w2/c2` per-request `1.084` and TPOT p50 `0.928`. Under the same owner
  decision, its requalification passed every gate (G24 `15/18`, `tool-loop` `1/3`), and its Studio route
  `client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` passed G23 (health RTT `6.1–6.8 ms`,
  stream TTFT `0.181 s`) and smoke `"ROUTE OK"` (published `8ab88b0`, restored-state `ab96ab4`). Both are qualified as
  **non-current alternates** on the PRO and Studio.

### Reviewed DFlash2 confidence pins

`strata.drafting_args` admits only `{"--draft-conf": "<value>"}` on a named DFlash2 component profile with engine
**0.1.59+**. Values are strings in stock's CUDA domain: **`0.35`, `0.5`, `0.55`, `0.7`, `0.8`**. These are exactly
the [slot steps](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/strata_control/drafting.py#L259-L278)
and the big-Blackwell tuned confidence, rendered in stock's `:g` form; SYCL's 0.6 is not admitted.
Empty pins, other flags, numeric JSON values and a missing named drafter or component are refused. DeepSeek keeps
its separate reviewed `user_args` pin and cannot use this field.

Installation reuses the existing reviewed `APPLY_USER_ARGS` writer with stock `setup.write_config`, immediately
after writing `drafting` and before offline pack preparation. It writes `user_args`, **not** `args`, and preserves
`args_written == args`. Stock `write_config` at this tag retains its reviewed AST digest
`875c4111fb44d7659fa40daf85d440ea08961a55b3b8e5500b01b0d91ac7b959`.
Reinstall accepts a carried `user_args` only when it equals the profile's exact pin; generated-config verification
requires that same list, and still refuses `user_args` on an unpinned Qwen profile. Pinned runtime identity also
hashes `strata_control/user_args.py`.

At start, stock
[`engine_args`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/serve/server.py#L3781-L3812)
merges `user_args` into a copy of the generated argv. Stock
[`drafting.apply`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/strata_control/drafting.py#L1104-L1165)
strips the base drafter flags and inserts the person's confidence verbatim, so there is one `--draft-conf` and no
MTP layer. The server prints that same value in its DFlash2 ON line; start verification requires the pin exactly,
alongside the existing pack, last-stage, window, selector and per-slot-drafter evidence. `run.json` records
`draft_conf` and `draft_conf_source` (`profile` or `stock`). The host-free dev-env proof executes the unmodified
pinned `engine_args` for both topologies; it also checks the stock `--spec` values (6 pair, 8 PRO).

The stock confidence rule ignores the pin when deciding whether it is redundant: a multi-GPU profile deterministically
uses 0.35, and a successfully selected tuned pack on the reviewed big-Blackwell PRO deterministically uses 0.55
(the resident-slot argument above). Pinning those same values creates no new behavior and is refused. A standard
single-card pack retains the full stock slot-step set because its exact slot count is not a profile fact; 0.55 is
therefore a distinct, explicit standard-pack arm, not an inferred default.

The two new **draft** profiles use stock standard packs and separate roots/ledgers: pair `df2conf05` (0.5) derives
from the v0.2.13 `env86gt` profile, and four-slot PRO `df2conf055` (0.55) derives from its v0.2.13 `envpg` profile.
Their campaign families rank below each lane's current variant. They make no performance or host-gate claim.
`upstream_watch.py draft --draft-conf VALUE` requires a named DFlash2 base, carries the pin on later drafts, and
drops it with `--drafting stock`. `--spec`, `--draft-cap` and all other drafter flags remain stock-owned: the engine's
reported window cannot distinguish a person's `--spec 6` from `--spec 8`, so no such pin is admitted.

Observed outcomes on the `v0.2.13` DFlash2 confidence arms (2026-11-09;
[MEASUREMENTS.md](MEASUREMENTS.md), [DECISION.md](DECISION.md)):
- **Install fix for carried `user_args` on stock setup re-run (`fb8740a`):** a stock `v0.2.13` setup re-run over an
  installed root merges the earlier `user_args` into `args` (`carry_user_args`), so every requalify of a
  `strata.drafting_args` profile refused at install; verification now removes each pinned option only when it occurs
  once with exactly its pinned value (handling DeepSeek's carried `--experts 6` the same way), with stock proof against
  the real `carry_user_args` (`7c2d25e` and `a7762aa` check that `v0.2.13` draft ledgers hold only their own receipts).
- **Adopted on the RTX 4090 + RTX 3090 pair (`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`, `--draft-conf 0.5`):**
  whereas the unpinned `v0.2.13` `env86gt` base missed 6 of 96 checks against `v0.2.12` on one 32K request (`w3/c1`
  TPOT p50 `1.054`, p95 `1.069`, max `1.070`; largest gap p50 `1.119`, p95 `1.239`, max `1.252`; everything else
  passed; stays a draft with a `"Not qualified"` blocker, `b2e9730`), `df2conf05` passed all 96 plain checks against
  `v0.2.12`, with targeted cold decode `1.021 [1.020, 1.049, 0.993]` (neutral: one pair below `1.00`), throughput
  `1.016` / `0.998`, per-request `1.027` / `0.993`, TTFT p50 `1.005` / `1.001`, TPOT p50 `0.973` / `1.009`, and decode
  `1.061` at 100K, `1.054` at warm 32K and `1.044` at 32K. Under the owner's decision (`"Run the --draft-conf 0.5 main;
  it becomes current if every gate passes"`), after `fb8740a` fixed the install check (runner `7c2d25e`,
  `18:43–19:26Z`), its requalification passed every gate including G15, G17, G18 and G18L (G24 `16/18`, `tool-loop`
  `1/3`; published `440fa1b`, restored-state `ab96ab4`), becoming the **current pair profile** (rolling back to the
  `v0.2.12` `env86gt` profile).
- **Withdrawn on the RTX PRO 6000 (`df2conf055`, standard pack + `--draft-conf 0.55`):** withdrawn before install
  because the window-8 burstiness is not a confidence effect (the tuned pack at `0.55` showed it too); stays a draft
  with a `"Not qualified"` blocker (`b2e9730`).

### RTX 5090 low-RAM screen planning

`upstream_watch.py draft` already exposes `--family` and `--model`; `--low-ram on|off` now changes the predecessor's
explicit setup choice and carries it into subsequent drafts. Low-RAM planning is limited to qwen `IQ3_S` at 131K or
262K on one 32 GB sm_120 card, engine 0.1.59, MTP and no batch slots. No runtime admission or current lane changes.
Stock's reviewed
[`low_ram_resident`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/setup.py#L6445-L6451)
chooses the resident variant from RAM, VRAM, context and int8 KV, counting MTP's VRAM. The moved, digest-bound
`setup_config.config_for` writes the actual flags and config; the planner never forces `--resident-experts`.
The host-free config-key census still requires the exact reviewed keys. Stock's fresh-install disk estimate also
counts the low-RAM `experts.bin` copy, not just the pinned model shards and MTP.

Two **comparison-only draft screens**, not qualification lanes, were generated from the v0.2.13 Coder 131K and
262K envg drafts with `--family qwen --model IQ3_S --low-ram on` at 47.15475845336914 GiB RAM and
31.8427734375 GiB VRAM. Both model blocks equal the v0.2.13 PRO IQ3_S model block without `dflash2_source`:

| Draft profile | Available RAM at start | Planner's exact expected engine flags |
| --- | ---: | --- |
| `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3` | 36 GiB | `--expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --max-context 131072 --kv int8 --resident-experts` |
| `win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` | 38 GiB | `--expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --max-context 262144 --kv int8 --resident-experts --kv-grow` |

The planner selected `--resident-experts`, not `--mmap-experts`, on both. Total RAM stays at the Coder floor
45 GiB. **Fresh-install disk stays at the planner's 138 GiB**, rather than the PRO's 93 GiB: stock counts its
51.3 GB low-RAM `experts.bin` copy plus the model shards, MTP download and working margin (148.1 GB before
exact-shard rounding). This corrects the initial screen plan's reused PRO disk estimate.

Both screens use MTP through stock Auto, with no prepared DFlash2 pack; stock reports that the DFlash2 drafter
isn't downloaded yet. There is no DFlash2 IQ3_S screen in this tuple. The 131K profile has no `engine_env` or
KV-placement pin; at the planning RAM, stock leaves KV in VRAM. The 262K profile carries `kv_streaming: off`,
`kv_grow: true` and the complete `gdn_stack` group, forbidding `--kv-resident`. Combining KV growth and low-RAM
resident experts remains a host screen, not a fit or performance claim.

Run 131K before 262K; the latter is meaningful only if the former passes. Valid screen evidence still needs doctor,
install identity, authenticated readiness, MTP, no start fallback and, on 262K, the existing KV-growth proof.
Commit headroom and available RAM after ready need private preflight/measurement; the start floor alone does not
prove fit. G17/G18/G18L/G24, task quality and paired performance decide whether qualification is worth proposing.
No host gates ran for these drafts, no receipts were inherited, and the current Coder installations remain unchanged.

Observed on `rtx5090-win-a` (2026-11-09; [MEASUREMENTS.md](MEASUREMENTS.md), [DECISION.md](DECISION.md)):
- **Full-model IQ3_S 131K low-RAM resident (`win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3`, stock's planner pick for this host) — qualified as a non-current alternate:**
  in the report-only screen (`B` = IQ3_S vs `A` = Coder IQ1_M 131K, both `v0.2.13`), cold decode was `1.046` (8K),
  `1.093` (32K), `1.071` (100K) and `1.094` (warm 32K) but `0.763` at the empty prompt; queue decode `1.086` / `1.086`;
  per-request `1.134` / `1.129`; TPOT p50 `0.881` / `0.885`; throughput w1 `1.059`, w3 `0.917`; TTFT p50 `1.528`
  (512-token prompt) and `1.122` (32K); and prefill `0.61–0.95`. The engine placed `11,616` expert slots in VRAM
  (`22.04 GiB`) with `29.77 GiB` of experts page-locked in RAM (on an earlier private quality set, IQ3_S scored `58/60`
  vs Coder `54/60`). In the second window on `rtx5090-win-a` (owner decision to prune old roots on `rtx5090-win-a` for
  disk and run its main gates; deleting five superseded roots freed `C:` from `98.1` to `156.6 GiB`), its
  requalification passed every gate including G15, G17, G18 and G18L (G24 `16/18`, `tool-loop` `1/3`; published
  `6e2dda2`, restored-state `ab96ab4`). It is a **qualified, non-current alternate** on the RTX 5090 (the Coder stays
  the default).
- **Full-model IQ3_S 262K screen (`win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`) — refused at first start:**
  screened under the owner's decision (`"Also screen IQ3_S at 262K"`); install passed, and its first start refused with
  `"strata.kv_grow: elastic K/V line absent from this start's engine-log interval"` because the draft pins `--kv-grow`
  and this low-RAM resident start did not print stock's elastic K/V line (`a7762aa`). No A/B ran, and the profile stays
  a draft with a `"Not qualified"` blocker (`b2e9730`).

## Stock OMP 18.18.3 surface

Stock [18.18.3](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.3) is a lightweight tag at
`21f1188cf88b2f534c092181968cd5a4d1a9c296`. The live release API identifies:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `omp-windows-x64.exe` | 249,790,976 | `07d50f434f7051dc79b9c80b468e78b6a0fa904ca1bd599a52d8734d0cd2bfd8` |
| `omp-darwin-arm64` | 221,702,288 | `87e8e593046dfb1047e359ad845648ffc8bda91aa59a9785690d5107f562c32d` |
| `omp-linux-x64` | 285,857,968 | `8c9a178fed74ec1da21aafb7d28cd9839b3b0c9e7d607c86cc3b6177355729f4` |

No integration config renderer, OpenAI Chat Completions wire or launcher allowlist change is needed.
The reasoning-signature change is a
[helper extraction](https://github.com/can1357/oh-my-pi/blob/21f1188cf88b2f534c092181968cd5a4d1a9c296/packages/ai/src/utils/reasoning-source.ts#L9-L19);
transport, local compatibility, rendered settings and local compaction thresholds/methods are unchanged.
Missing-key refusal and the `discarded-turn` usage filter remain necessary. `--restore` is already reviewed;
`gc --strip/--strip-after-days` are subcommand-only, unreachable through the root launcher argv.
Both native-parser refusal and pinned-help policy tests passed against the size/SHA-verified Darwin ARM64 18.18.3
asset (two tests); this is not a GPU gate.

Agent behavior **is not comparable with 18.18.0** for G24 or `eval_taskset`:

- The
  [delegation fallback](https://github.com/can1357/oh-my-pi/blob/21f1188cf88b2f534c092181968cd5a4d1a9c296/packages/catalog/src/compat/delegation.ts#L60-L70)
  changes from eager to balanced, affecting Qwen's prompt and tool descriptions. G23 must re-prove delivery;
  fleet arms needing delegation retain their explicit existing prompts rather than a new stock override.
- The
  [system prompt](https://github.com/can1357/oh-my-pi/blob/21f1188cf88b2f534c092181968cd5a4d1a9c296/packages/coding-agent/src/prompts/system/system-prompt.md#L97-L134)
  adds turn batching and “Read small files whole; ranges only for large files”; verification guidance also changes.
  This may affect G18L's whole-file reads, but is not an assumed fix or a reason to relax its bars.
- Bash now pins `LANG/LC_ALL=C.UTF-8` on every platform, forks overlapping calls and gives Windows commands their own
  console ([18.18.2](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.2),
  [18.18.3](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.3)). G19 prompt bytes, tool output and
  comparison-harness outcomes may differ.
- Interactive ask forms can fetch image URLs; print/RPC gates do not expose that tool. Existing closed-proxy egress
  guards remain, but their real-host observation is still required. The worker threshold and `ovnfs` discovery
  boundary are unchanged; host preflight must continue establishing `ovnfs` absence.

Qualified on 2026-11-09 ([decision](DECISION.md), [measurements](MEASUREMENTS.md)), with G24 scoring `16/18`
(`tool-loop` `1/3`) on the RTX 5090 262K `envg` (`d3c96fb`), 131K Coder (`d0c2e28`) and 131K IQ3_S low-RAM (`6e2dda2`)
chains and on the pair `df2conf05` `--draft-conf 0.5` chain (`440fa1b`), and `15/18` on the PRO `df2` current
(`tool-loop` `0/3`, `2af52b8`) and `df2tuned` tuned-pack alternate (`tool-loop` `1/3`, `8ab88b0`) chains: on the PRO,
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` (current, rolling back
to its `v0.2.12` + OMP `18.18.0` `df2` predecessor) and the tuned-pack alternate
`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`; on the RTX 5090,
the 262K default `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` (rolling back to its
`v0.2.12` + OMP `18.18.0` predecessor), the 131K Coder alternative
`win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3` (rolling back to its `v0.2.12` + OMP `18.18.0` predecessor) and
the full-model IQ3_S 131K low-RAM resident alternate `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3`; on the
pair, `win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`
(current, pinning `--draft-conf 0.5` in `strata.drafting_args`, rolling back to its qualified `v0.2.12` `env86gt`
predecessor); and on the Mac Studio client,
`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` (current, rolling back to its `v0.2.12`
`df2` route) and the tuned-pack alternate route
`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` (restored-state records `ab96ab4`).
Pinning OMP `ask.enabled: false` was not adopted (print/RPC gates do not expose interactive ask forms, and closed-proxy
egress guards remain active).

## Stock xd:// devices and Strata's undeclared-call policy

Found on 2026-11-12 from the MCP form in [can1357/oh-my-pi#18953](https://github.com/can1357/oh-my-pi/issues/18953)
(labelled `wontfix` upstream). The [v0.2.12 review](#engine-environment-and-timing-boundaries) kept stock
`undeclared_tool_calls: "text"` because OMP declares its tools, but launch-omp sessions also run tools they do not
declare:

- **Surface.** The generated config leaves stock `tools.xdev` on
  ([default `true`](https://github.com/can1357/oh-my-pi/blob/21f1188cf88b2f534c092181968cd5a4d1a9c296/packages/coding-agent/src/tools/settings.ts#L1014-L1016)).
  Without `--tools`, stock OMP 18.18.3 advertises 11 tools (`read`, `bash`, `edit`, `eval`, `glob`, `grep`, `task`,
  `wait`, `todo`, `web_search`, `write`) and mounts `ast_edit` and `debug` under `xd://`; neither is in the request's
  `tools`. G24 (`eval_taskset`), the G25 comparison and the mock tier pass explicit `--tools` lists, which mount no
  devices, so no evaluation has measured how often a model calls a device by name.
- **Stock outcome.** Strata keeps a well-formed call of an undeclared name as the answer's text, with `finish_reason`
  `stop` and `strata_rejected_tool_calls`, and its server window prints
  `did not read as a call of a declared tool and went back as text`
  ([DETAILS.md](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/docs/DETAILS.md#L534-L541)).
  Stock OMP takes that text for its final answer: the run exits 0 with the work undone.
- **`"undeclared_tool_calls": "call"`** ([Strata#4622](https://github.com/Niko1221/Strata/issues/4622), v0.2.12+)
  returns the call as a tool call, and stock OMP's fallback resolver runs an exact mounted name
  ([`resolveDeviceTool`](https://github.com/can1357/oh-my-pi/blob/21f1188cf88b2f534c092181968cd5a4d1a9c296/packages/coding-agent/src/sdk.ts#L4097-L4121)).
- **Host-free evidence.** In `tests/mock/test_strata_frontend_mock.py` the stock MockEngine calls `ast_edit` by name
  under launch-omp's surface. With stock `text`, OMP makes one request and answers with the raw call; with `call`, it
  stages the rewrite, applies it through `xd://resolve` and finishes. Both pass with v0.2.13 + 18.18.3 and with
  v0.2.12 + 18.18.0 (2026-11-12, Darwin ARM64).
- **Next tuple, not now.** Pinning `undeclared_tool_calls: "call"` (or OMP `tools.xdev: false`) is a setting change:
  new profile ids with their own qualification. Every current lane keeps stock `text`; the owner chose to pin `call`
  in the next tuple's new profiles ([decision](DECISION.md)). Reported upstream as
  [Strata#5888](https://github.com/Niko1221/Strata/issues/5888), with the fix posted on
  [can1357/oh-my-pi#18953](https://github.com/can1357/oh-my-pi/issues/18953#issuecomment-6838653802).

## Strata v0.2.12 setup and start-path review (engine 0.1.58)

This section records the source admission before hardware qualification; on 2026-11-07–08 every host lane and both
Studio routes qualified on stock Strata [v0.2.12](https://github.com/Niko1221/Strata/releases/tag/v0.2.12) with stock
OMP `18.18.0` ([decision](DECISION.md)).
Stock [v0.2.12](https://github.com/Niko1221/Strata/releases/tag/v0.2.12) has tag object
`123bad4acd5fd3fe70f02ad4c938e0c360efe5e5`, commit `146df3c468739147f520ac3816de806f71232571`,
app **0.2.12** and Control/engine **0.1.58**. The published Windows CUDA 13 archive
`strata-engine-0.1.58-windows-x86_64-cuda-cuda13.tar.gz` is **630,769,464 bytes**, SHA-256
`3311443ba9172154adc99c48668c4187d60864e3b6cafe5d9aa39b035e4f9f34`.
`inspect_archive` verified every member against `engine-component.json` and read `BUILD.json`:
build **`8a42a9457db6+cuda13.0`**, source `f-0212-rc`, commit `8a42a9457db6`, manifest SHA-256
`d4964abd777ce53e518abf78f0af1882ad779a225550e1480a2267486ea055a0`, CUDA 13.0, NVIDIA floor 580.65.
The build's engine sources differ from the tag only by the tag's five-line pre-sm_70
`__match_any_sync` fallback in
[`qsa_select.cu`](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/src/kernels/cuda/qsa_select.cu#L3307-L3315);
the published archive, not the tag's build identity, is pinned.

### Exact setup and server admission

The only setup-planner admission is the complete
[`if budget is not None and not q4_split` statement](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/setup.py#L11099-L11113).
Its UMA-only informational arm changes from a warning to a graphics-memory explanation. Native lane planning has
`budget is None`; the exact guard must still evaluate false. `NON_PLANNING_BRANCHES_0_2_12` adds only its digest,
keeps the predecessor digest and does not widen `pure_exec`'s calls. Modified statements still refuse.
Setup choices, model shards, tips and host floors for the PRO, both 5090 contexts and manual-split pair are unchanged.
The cp313 Windows lock `locks/strata-python-cp313-win_amd64-strata0.2.11.txt` is reused: both runtime requirement
files are unchanged. Drafting the 131K lane from its qualified v0.2.10 predecessor must explicitly pass that lock.

The full server closure, filtered imports, environment literals and all other reviewed start-path modules were
recomputed at `146df3c4` and match v0.2.11. Only `strata_control/drafting.py` changes. The new server entry binds
that module to engine 0.1.58; missing, changed or mixed modules and ambiguous reviews still refuse.
`strata_control/drafting_fetch.py` is reviewed separately by release: v0.2.10/v0.2.11 keep their old digest,
v0.2.12 gets its own; the offline packer remains unchanged. Full-field AST SHA-256 values, computed with
`reviewed_hash` on CPython **3.13.18**:

| Reviewed surface | AST SHA-256 |
| --- | --- |
| setup budget/UMA If (exact statement) | `9503fca81c10b7ba6cdfa296d89f9d95b3c14a23f6a79d8598eaf0e2b2c925a3` |
| server filtered imports (unchanged) | `b3a207845da9c931bf60dd9eac96b393134c22152a205b06ac5a713b4a6e7d86` |
| `strata_control/drafting.py` | `d6fb67b5d9e9f20138af2802f534c36cd6ed10e143e788bd5561b5264ba7d345` |
| `strata_control/drafting_fetch.py` | `311f51ec36b01ee830c562a3d0b9f018de963fd1af933b050d13557230e4ddfa` |
| `tools/dflash2_pack.py` (unchanged) | `57ac7a9d4d2132714cd022e7b38bc69cec390a62b76147f7e685e22ce73ba05b` |

No new file-writing or network path joins API server start. The existing runtime lease and process records stay
inside the integration root under `STRATA_RUNTIME_DIR` and redirected `LOCALAPPDATA`. Setup's new `.bad` checksum
retention does not touch our pre-verified `--gguf-dir` inputs. Tuned-drafter feed/download code belongs to
`strata launch`, `strata drafting fetch` and Mac setup, none invoked here; inherited `STRATA_*` overrides remain
scrubbed. Stock's verified tuned pack is a **separate profile admission**, not silently adopted by this tuple's
locally-packed DFlash2 profiles. A resident single-card PRO may select it if present; the pair's unknown slot
estimate and the unsupported Coder family do not meet that stock selection rule
([selection](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/strata_control/drafting.py#L411-L450)).

### Tuned DFlash2 pack (PRO arm)

The PRO arm `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`
pins stock's tuned pack as `model.dflash2_source.tuned`: the flat v0.2.12 release asset
`qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack` (339,694,592 bytes, SHA-256 `4df2e5ab…664c`, equal to stock
`drafting.TUNED_*` and the release `SHA256SUMS.txt`; Apache-2.0 as modified by Strata, base
`incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744…`). Fetch downloads it to
`downloads/dflash2/v0.2.12/`; install copies it into `data/dflash2/`, lets stock `drafting.tuned_ok` write its
`.ok` marker and copies stock's `LICENSE` and `NOTICE.md` as `LICENSE-dflash2-tuned` and `NOTICE-dflash2-tuned.md`,
without importing `drafting_fetch`. The standard packs stay as stock's fallback. A start must show the engine ON line
naming the tuned file at `--draft-conf 0.35`; a stray tuned file in a standard root is refused before launch (engine
0.1.58+). Validation refuses the pin on several cards, other models, the Coder family and engines before 0.1.58,
where stock would not choose it. The Studio route to this server is
`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`. Upstream measured the pack only
for single requests (RTX PRO 5000 IQ3_S, decode about +2.4%), so it is a measured arm, not the base lane.

Observed on `rtxpro6000-win-a` (2026-11-07–08, three paired cold starts `A1 B1 B2 A2 A3 B3` per A/B, `B/A` paired
geometric mean with the three per-pair ratios in brackets;
[MEASUREMENTS.md](MEASUREMENTS.md), [DECISION.md](DECISION.md)):
- Against the `v0.2.11` DFlash2 profile (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`),
  6 of 90 checks missed: two requests time per output token (TPOT) p95 `1.162 [1.153, 1.175, 1.157]` and max `1.211 [1.200, 1.224, 1.209]`, two
  requests latency p95 `1.055 [1.083, 1.135, 0.956]` and max `1.080 [1.126, 1.173, 0.954]`, and four 32K requests
  per-request throughput p50 `0.941 [0.921, 0.998, 0.907]` and TPOT p50 `1.062 [1.085, 1.001, 1.101]` (while TTFT p50 at
  two / four requests was `0.745 / 0.684`).
- Against the `v0.2.12` standard-pack profile (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`,
  owner decision `"Measure tuned vs v0.2.12 base first"`), 3 of 90 checks missed: one request per-request throughput
  p50 `0.942 [0.936, 0.935, 0.955]` and TPOT p50 `1.062 [1.068, 1.070, 1.048]`, and four requests TTFT p50
  `1.138 [1.484, 1.399, 0.711]`, while two concurrent requests were faster (`per-request throughput p50 1.165 [1.023,
  1.230, 1.258]`, `TPOT p50 0.873 [0.978, 0.828, 0.820]`). The two-/four-request TTFT gains against `v0.2.11` therefore
  came from `v0.2.12` itself, not from the tuned pack.
- Under the owner's override (`"Override: qualify tuned as alternate"`), its requalification chain passed every gate
  (G10–G21, G26; G24 `15/18`, `tool-loop` `0/3`, pilot `5/6`) and its Studio route
  `client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0` passed G23 (health RTT `12.1–16.1 ms`,
  stream TTFT `0.317 s`, same failure and recall checks, plus `launch-omp` smoke). Both are qualified as **non-current
  alternates** on the PRO and Studio (measured slower one request at a time, faster with two; not the rollback, which
  remains the `v0.2.11` DFlash2 profile and route).

### Engine environment and timing boundaries

The lead's engine review admits 0.1.58 for the same complete `parallel_stack`, `gdn_stack` and `sm86_table` groups:
all **20 variables** retain their names, meanings and defaults; none is removed. The unchanged
[`nv_defaults.cpp` sm_86 table](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/src/core/nv_defaults.cpp#L31-L39)
still requires homogeneous visible compute capability, so the mixed pair still pins that group. Server
[`PARALLEL_STACK_ENV`](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/serve/server.py#L4269-L4272)
and [`GDN_STACK_CUDA`](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/serve/server.py#L4321)
match the existing groups. No new `strata.exe` CLI flag is added. New opt-in engine switches are not admitted here.
The CPU-kernel diagnostic is now `strata generate: CPU expert kernels: AVX-2` on CPUs without the reviewed VNNI
tier; no integration parser depends on the old sentence. Stage-order admission for `0.1.58` waited during source
review for a measured pair start and was admitted on 2026-11-07 (`a5989fe`) after the pair DFlash2 measurement start
parsed complete: RTX 3090 first, RTX 4090 last, layers 0–23 / 24–47 at pinned split 24, expert caches `19.40 / 17.90 GiB`
(`v0.2.11`: `19.41 / 17.90 GiB`) and one engine generation.

Server timing accounting changes in
[`request_timings`/`request_stats`](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/serve/server.py#L6825-L6850):
prefill sums yielded prompt-read legs once; batch-slot decode includes slot-admission DONE time. Unknown legs or
a draining background admission may report `None`, not zero. Thus server-derived concurrent decode rates are
**not comparable to v0.2.11**. Use client-observed wall/output intervals for a cross-tuple comparison.
The probes preserve unavailable durations; `probe_g25_speed` now also replaces an earlier partial timing with
an explicit null instead of retaining a stale rate. Existing `perf_probe` metric boundaries and G15/G16/G17 receipt
limitations state the accounting. `realhost_gates.engine_requests` and `hostrun.strata_metrics` already preserve
nulls; no gate threshold compares the changed decode rates, so thresholds remain unchanged.

The server's declared-tool handling fixes and required `tool_choice` repair need no new setting here, and
`undeclared_tool_calls` stays stock `text`; no new config key or fetch environment variable is admitted. This review
called `undeclared_tool_calls: call` unreachable because OMP declares its tools; launch-omp also runs mounted `xd://`
devices it does not declare ([2026-11-12 finding](#stock-xd-devices-and-stratas-undeclared-call-policy)).

## DeepSeek V4.1-Flash comparison admission

The [DeepSeek V4.1-Flash profile](../profiles/win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0.json)
(fingerprint `51642761f608b94c`;
[ledger](../releases/win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0/qualification.json)) is
**comparison-only, never current**, with every gate `not_run` and no CI or campaign row. Only stock `deepseek41` /
`IST-DAS-2.25bpw` is admitted, on one native Windows RTX PRO 6000 (`gpu_index: 0`): seven per-file pinned inputs
totaling **273,803,809,901 bytes** — the four original ISTA GSQ-RCO `IQ2_XS` shards (including the original
`39,535,776,992`-byte shard 1) and `DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf` (`110,595,290,816` bytes) at
`ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF` revision `cb02422c900df489cea5833e8a92171224059b3c`, plus the
`5,780,589`-byte metadata shard and `7,976,914,240`-byte `dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf` at
`unsloth/DeepSeek-V4.1-Flash-1017-GGUF` revision `8a6ec9cf118e785a362ea94ee123c61c70553be6` — each verified by its own
repository, revision, byte count and SHA-256 against stock `v0.2.11` setup. Six-shard layouts, alternate shard 1, other
quantizations, vision and `--parallel` are refused.

- **Separate engine component:** `strata-dsv41-0.1.57-windows-x86_64-cuda-cuda13.tar.gz` from `v0.2.11` (`422,613,464`
  bytes, SHA-256 `bc1cbecc7553c3022e369bc1e0ed4f360ea26daf5dfc386dd0dde75be417941e`, manifest SHA-256
  `d0ebc5660e8fbaea64e0949400b36d7b410f087d7112a350214531f7fab15272`, build `975eaab2bb40+dsv41+cuda13.0`, entrypoint
  `strata-dsv41.exe`). Its separate `dsv41_component` pin binds the manifest and build identity (up to 8 archive members
  and 1 GiB unpacked), never the same-numbered Qwen `strata-engine` archive; stock setup stages it under `engine-dsv41`,
  and Qwen's component verifier keeps its existing defaults.
- **Guarded install and pack verification:** runs stock `setup.py` with `--family deepseek41 --model IST-DAS-2.25bpw
  --context 262144 --vision no --gpu 0 --data-dir … --gguf-dir … --dsv41-package … --port 18090 --host 127.0.0.1 --yes
  --no-start` and offline `pip` (`locks/strata-python-cp313-win_amd64-strata0.2.11.txt`, `PIP_NO_INDEX=1`), without
  fetching any Qwen engine, `llama.cpp`, MTP or `mmproj` artifact. Every input is deep-hashed before setup runs; extra
  `.gguf` files in the model directory are refused, and `<root>\data\models\deepseek-v4.1-flash-shared` must be empty so
  stock setup's size-only search of its default shared folder cannot substitute a different file. `STRATA_NO_ACQUIRE` is
  omitted so stock setup runs its offline packer and mandatory local smoke, and a separate `strata-dsv41.exe --pack-info`
  check must report `all present`.
- **Full quality and disk-slot privacy:** generated config carries `user_args: ["--experts", "6"]` (all six routed
  experts per token) and the reviewed environment `{STRATA_DS4_SLOT_KEEP: "0", STRATA_DS4_AUTO_PIN: "0"}` (disabling
  disk conversation-slot persistence). The stock server
  [merges `user_args` over generated arguments](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/serve/server.py#L3770-L3773)
  and [respects explicit `STRATA_DS4_*` config environment entries](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/serve/server.py#L4232-L4241). Both
  `install` and `serve` strip inherited `DS4_*` variables alongside `STRATA_*`.
- **Runtime identity:** generated config must match the exact DeepSeek key set (`arch: "deepseek41"`,
  `model_name: "deepseek-v4.1-flash"`, `engine_ready_s: 3600`, `--dspark auto --dspark-conf 0.65`, isolated
  `engine-dsv41` / pack / tokenizer / log paths, and a pack `tensors.txt` naming the four `IQ2_XS` shards, Engram and
  DSpark while using the Unsloth metadata shard only for geometry). Pack hashing excludes only `expert-profile.bin`
  (rewritten on exit) and `pack-source.json`; no `--profile-readonly` override is added. At runtime `/props`
  `build_info` must report **`Strata ds4-0.1`** (from `INFO engine=ds4-0.1`, not `Strata 0.1.57`), `model_path` must
  name the pack directory, `/health` must report a loaded, authenticated, text-only service at the pinned context and
  model, and the reachable DeepSeek server modules and tool chat template are hashed at install.
- **Start evidence and observed host screen:** each start log interval must contain one engine generation,
  `ds4: experts per word: 6 (full quality)`, stock DSpark's `auto` decline when routed experts exceed `1.5×` GPU
  capacity, VRAM placement, and every remaining CPU-lane expert copied into RAM at load (`--mmap-experts auto`, no
  demand store); missing, repeated or unrecognised lines, partial copies, RAM-store fallback, `--ssd-cache` or
  `ds4 slots:` disk activity fail closed. On 2026-11-06 on `rtxpro6000-win-a`
  ([measurements](MEASUREMENTS.md#quality-first-comparison-on-the-pro-2026-11-06-stock-strata-v0211-stock-omp-18160)),
  the unrecorded comparison screen (`install, keygen, start, g10, tracer, g14, g14q, perf, stop`, leaving the ledger `not_run`) passed in `54.8 s` to ready with six experts
  per token (`full quality`), DSpark declined under `auto`, `9,344` of `15,360` experts in VRAM (`91.05 GB`), all
  `6,016` CPU-lane experts copied into RAM (`58.4 GB`), no disk slots, G10 GPU memory `95,692 MiB`, minimum available
  RAM `114.0 GiB` and Windows commit headroom `52.70 GiB` of `219.70 GiB`, 3/3 typed-tool tracers, server-logged thinking
  capped at `24,576` of `32,768` output tokens under stock OMP `18.16.0`'s `reasoning_effort: "high"` (DeepSeek template
  value `75`; `"max"` = `100` not used), `45.7 tok/s` decode and `2,655 tok/s` prefill at 32K, and `12.4 s` / `32.4 s`
  TTFT at 32K / 100K.
- **Gates and comparison bounds:** G19 makes no conversation-parking claim while live-prefix reuse remains a G12
  requirement; G11 sends explicit high effort (DeepSeek template value `75`; low/medium map to `50`/`62`) with a `3,600 s`
  invocation cap, distinguishing the source mapping from wire captures; G18 (and its long-session `g18l` sub-probe) uses
  the same `3,600 s` invocation cap, and comparison step caps are `28,800 s` (`install`), `3,900 s` (`start`), `21,600 s`
  (`tracer`/`g18`/`g18l`) and `54,000 s` (`pilot`/`eval`); `perf` retains request exclusivity and FIFO checks without Qwen
  MTP metrics; when individual gate harnesses run on a comparison root, G22/G23/G25 stay `not_run` unless applicability is
  recorded.

The draft pins `262,144` engine tokens (rendered OMP context `261,120`, output cap `32,768`, `maxInFlightRequests` `1`),
`184 GiB` total and `160 GiB` start-available RAM floors (above the `58.4 GB` copy-all allocation and earlier `59–67 GB`
screens; commit sufficiency is checked by complete-copy startup evidence and G10/G21 rather than inferred from RAM
alone), and a `262 GiB` disk floor covering the pinned stock download plus its `6 GB` margin. In the 22-task
quality-first comparison on `rtxpro6000-win-a`
([decision](DECISION.md#update-2026-11-07-quality-first-comparison-on-the-pro-keeps-the-four-slot-iq3_s-incumbent)),
neither candidate met the `+3` paired-net replacement bar (this profile's trial was stopped after `7` of `22` tasks at
`5/7`, paired net `-2`), so the four-slot `IQ3_S` DFlash2 incumbent stayed current and
this profile stays a comparison-only draft.

## Engine 0.1.59 opt-in groups

Source review at stock Strata
[`d2f09647`](https://github.com/Niko1221/Strata/commit/d2f096475817d4666c364c820b0ca830f751cfc5)
shrinks the proposed `sm121_decode` pair to **`spec_cost = {"STRATA_SPEC_COST": "1"}`** and keeps
**`qsa_split_attn = {"STRATA_QSA_SPLIT_ATTN": "1"}`**. These are opt-in measurement arms, not qualified defaults.
Both require engine 0.1.59 or newer, within the exact engine-env review set.

### Read sites, stock values and gates

- **`STRATA_HC_UPMIX` — excluded.** Stock sets `"1"` in the sm_121 table
  ([`nv_defaults.cpp:54-80`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/core/nv_defaults.cpp#L54-L80)).
  Its only engine read caches whether the first character is `'1'`
  ([`prefill.cpp:556-582`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/prefill/prefill.cpp#L556-L582)).
  Its only use is the **chunk-major prompt** path at
  [`prefill.cpp:4182-4208`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/prefill/prefill.cpp#L4182-L4208):
  CUDA chunks of at least `max(STRATA_PF_SWITCH_MIN_T, 33)` tokens, ordinary Bf16InF32 up weights of the
  expected shape, no int8 up rows, no unfused GR and no BF16X2 prefill. The kernel needs sm_80+
  ([`kernels.cu:2897-2909`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/prefill/kernels.cu#L2897-L2909));
  a decline falls back to the ordinary projections. Neither MTP, batch, KV format/residency nor context length
  gates it. Draft-KV prompt work and the layer-major prompt walk do not use it
  ([`prefill.cpp:2408-2409`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/prefill/prefill.cpp#L2408-L2409),
  [`7589-7618`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/prefill/prefill.cpp#L7589-L7618)).
  It **never affects decode**; sm_120's `STRATA_GR_V3` is a different, decode-only read
  ([`fused_gr.cu:2867-2872`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/kernels/cuda/fused_gr.cu#L2867-L2872)),
  not an override of HC_UPMIX. Stock's bit-exact claim is toolchain-specific (CUDA 13.3 on an RTX 5090,
  `prefill.cpp:556-558`), not established for this archive. The sm_121 table's decode-gain comment has no
  corresponding HC_UPMIX decode read in this tree. It therefore cannot satisfy the proposed decode arm's bar.
- **`STRATA_SPEC_COST` — admitted as `spec_cost`.** The stock sm_121 value is `"1"`
  (`nv_defaults.cpp:76-80`); only attempted drafts change and every draft is verified. Serve caches a
  first-character-`'1'` read at
  [`generate.cpp:14109-14118`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/program/generate.cpp#L14109-L14118);
  the separate CLI read is at `generate.cpp:20786`. MTP installs the cost chain rule in place of min-p
  ([`mtp.cpp:1774-1861`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/core/mtp.cpp#L1774-L1861)).
  Window sizing applies only with MTP, not DFlash2 and not the first window; it clamps the chosen chain to
  the ordinary cap
  ([`window_rule.hpp:31-64`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/include/strata/spec/window_rule.hpp#L31-L64)).
  Stock Auto supplies `--spec 4 --spec-min-p 0.5 --mtp` on the Coder lane
  ([`setup_config.py:219`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/strata_control/setup_config.py#L219));
  cost sizing supersedes min-p on these rounds. Prompt lookup can replace an MTP round; `STRATA_SPEC_PROB`
  gated proposals bypass cost sizing and remain unadmitted. There is no source arch, KV-format or KV-residency
  gate. The **one sm_120 card** restriction is measurement-scope policy, not a source restriction; stock measured
  sm_121. Require no `setup_args.parallel` (unreviewed batch path; stock reports a loss at parallel 8 in
  [`DGX_SPARK_LINUX.md:139-140`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/docs/DGX_SPARK_LINUX.md#L139-L140))
  and no `strata.drafting` (stock Auto MTP).
- **`STRATA_QSA_SPLIT_ATTN` — admitted as `qsa_split_attn`.** The documented on-value is `"1"`; stock measured
  +2.8% / +3.5% decode after a 30K prompt on sm_86, with rounding-level output changes
  ([`DETAILS.md:1114`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/docs/DETAILS.md#L1114),
  [`1522`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/docs/DETAILS.md#L1522)).
  Cached reads use `atoi(value) != 0` in
  [`verify.cpp:2141-2156`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/core/verify.cpp#L2141-L2156)
  and [`mtp.cpp:1191-1194`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/core/mtp.cpp#L1191-L1194).
  The serial verify call covers **all rows** of MTP or DFlash2 windows, after `qsa_kv_resolve`, so
  `--kv-resident` streaming is allowed. Batch windows take other branches (`verify.cpp:2063-2139`), so require
  no `setup_args.parallel`. The
  [kernel guard (`qsa_prompt_attn.cu:2383-2431`)](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/kernels/cuda/qsa_prompt_attn.cu#L2383-L2431)
  requires CUDA, int8 K and V pools (not q4 or K8V4), sm_80+ and sufficient shape-dependent scratch.
  Architecture and shared-memory attributes are cached **per device**: the sm_86 + sm_89 layer split is allowed.
  Admission narrows every card to **sm_80–sm_89** as measurement-scope policy (only sm_86 measured), and requires
  a CUDA engine component and `setup_args.kv: "int8"`. There is no code context threshold; use prompts of at
  least 30K tokens for measurement. `STRATA_QSA_WARP` does not affect its raw capability check, and
  `STRATA_SELECT_TWO_PASS` is prompt-only. Where taken, it replaces the `STRATA_ATTN_DAILY` kernel in
  [`qsa_decode_attn.cu:868-889`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/kernels/cuda/qsa_decode_attn.cu#L868-L889).
  Thus none of the drop conditions (single-row-only, all-KV-resident-only, or no layer split) holds.

### Prints and engagement evidence

Neither admitted switch has a positive stock stdout/stderr line on these serve lanes. Start records retain
config delivery and the reviewed stock `child_env` pass-through, with per-group evidence; no positive pattern
is invented. For `qsa_split_attn`, the only refusal substrings are:

| Substring | Stream and source | Meaning |
|---|---|---|
| `qsa_decode_attn_split:` | stderr, `qsa_prompt_attn.cu:2424-2427` | Fatal CUDA launch error, followed by exit. |
| `strata verify: batch windows of up to` | stderr, [`verify.cpp:4000-4001`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/core/verify.cpp#L4000-L4001) | Batch windows bypass split attention. |

Other reviewed prints are **not positive engagement evidence**:

- `nv_defaults.cpp:101-107` prints the sm_121 defaults it set to stderr, never on these sm_120/sm_86/sm_89 lanes.
- HC_UPMIX diagnostics (`prefill.cpp:4200-4202`, stderr) need unadmitted `STRATA_HC_UPMIX_CHECK`; its CUDA fatal
  prefix is `prefill gr_upmix:` (`kernels.cu:106-108,2909`, stderr). `arch_defaults.cpp:341-342` names its off-value
  only on HIP integrated GPUs. None supplies a CUDA-lane success line.
- SPEC_COST's cost-rule/table prints (`generate.cpp:21220-21234`, stdout) are CLI-only. Its stderr
  `STRATA_SPEC_PROB=1 keeps the older acceptance rule` line (`generate.cpp:3174-3175`) requires an unadmitted switch.
- The split-off/declined note (`verify.cpp:2153`) is dispatch-report data, neither stdout nor stderr, requiring
  unadmitted `STRATA_DISPATCH_REPORT` or CLI stats. `strata verify: capturing the N-token window`
  (`verify.cpp:2759`, stderr) names captured widths, not which attention kernel engaged.

Host-free proof calls stock `child_env` from the pinned checkout with `gdn_stack` plus each candidate and requires
every value unchanged. Profile-expressible gates above are mandatory. Workloads must remain serial; SPEC_COST
needs enough decode rounds per cold process to learn across the `<6K`, `<24K` and longer cost buckets
([`draft_policy.cpp:90-93,268-276`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/src/spec/draft_policy.cpp#L90-L93)).
Corroborate SPEC_COST with per-request `draft_n` and `draft_n_accepted`
([`server.py:6786`](https://github.com/Niko1221/Strata/blob/d2f096475817d4666c364c820b0ca830f751cfc5/serve/server.py#L6786)),
not a claimed positive log line; greedy output must remain byte-identical. Corroborate QSA with long-prompt
greedy divergence and decode speed; identical output on every long prompt is **possibly inert**, requiring
an owner decision before adoption. Scratch-shape fallback, the unmeasured sm_89 card and displacement of
ATTN_DAILY remain real-host measurement risks; pipeline-window behavior is unreviewed and not part of this arm.

### v0.2.13 draft arms

- [RTX 5090 `envgc`](../profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3.json)
  is the v0.2.13 262K Coder `envg` base plus `spec_cost` alone (`c` = cost-aware MTP); HC_UPMIX stays unpinned.
- [RTX 3090 + RTX 4090 `env86gts`](../profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3.json)
  is the v0.2.13 pair `env86gt` base plus `qsa_split_attn` (`s` = split attention).

Both were made with the draft CLI, preserving the bases' host floors, model/OMP pins, setup and engine flags.
They have separate roots and unrun release ledgers, carry no inherited qualification, and rank below the current
family in the campaign. Source admission and host-free tests do not promote either arm.

### Observed outcomes on the v0.2.13 engine-env arms (2026-11-09)

Observed in the three-pair cold-start A/Bs (`A1 B1 B2 A2 A3 B3`, `B/A` geometric means;
[MEASUREMENTS.md](MEASUREMENTS.md), [DECISION.md](DECISION.md)):

- **`STRATA_SPEC_COST=1` (`spec_cost`, id token `c`) — not adopted on the RTX 5090 (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3`):**
  in `B` = `v0.2.13` `envg` + `{STRATA_SPEC_COST: "1"}` vs `A` = `v0.2.13` `envg`, missed 3 of 88 checks (one-request
  window `1.119`, largest gap p95 `1.711`, max `1.771`); three replacement pairs missed 2 of 88 checks (largest gap p95
  `1.197`, max `1.212`; targeted cold decode `1.012 < 1.02`). Throughput and TPOT were `3–5%` better in every pair,
  with about one `4x` largest-gap spike per three cold starts. Not adopted by the owner (left unchecked), and `envgc`
  stays a draft with a `"Not qualified"` blocker (`b2e9730`).
- **`STRATA_QSA_SPLIT_ATTN=1` (`qsa_split_attn`, id token `s`) — not adopted on the RTX 4090 + RTX 3090 pair (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3`):**
  missed 2 of 96 checks (`w1` largest gap p95 `1.075`, max `1.092`), and targeted cold decode at 32K / 100K / 200K was
  `1.003 < 1.02`. Not adopted, and `env86gts` stays a draft with a `"Not qualified"` blocker (`b2e9730`).
- **Other candidates not adopted in `v0.2.13`:** `STRATA_HC_UPMIX` (prompt path only, never decode, including on four
  slots), PLE/dense side group and `STRATA_PF_FUSED_NT` / `PF_BATCH` (no stock value, unverified on `sm_120`), two-pass
  on the PRO and RTX 5090 (`v0.2.12` results stand), and `--spec` pins (deferred).

## Stock engine opt-in groups (v0.2.12 / 0.1.58)

These are source-reviewed measurement arms, not changes to a qualified lane's defaults. The exact engine-env
review set still applies, and both new groups separately require engine **0.1.58 or newer**. Profile validation
and draft planning share the same architecture, model and config-env preconditions.

| Complete group | Pin | Reviewed scope |
|---|---|---|
| `select_two_pass` | `STRATA_SELECT_TWO_PASS=1` | Exact two-pass QSA block selection for long prompts; every card must have a reviewed CUDA sm_80+ architecture, and `STRATA_QSA_WARP` must stay absent from the complete config env. No quant dependency. |
| `iq4nl_w4a8` | `STRATA_IQ4_W4A8=2` | IQ4_NL down products on the qwen IQ3_S pair's RTX 3090 sm_86 MMQ stage. Requires a multi-GPU layer split containing sm_86. sm_89 declines it; the sm_120 cards use fused kernels instead. |

The source is stock commit
[`146df3c4`](https://github.com/Niko1221/Strata/commit/146df3c468739147f520ac3816de806f71232571):
[`qsa_two_pass.hpp`](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/include/strata/kernels/qsa_two_pass.hpp)
and
[`moe_iq4_w4a8.cu`](https://github.com/Niko1221/Strata/blob/146df3c468739147f520ac3816de806f71232571/src/prefill/moe_iq4_w4a8.cu).
Two-pass has no start line; engagement needs its per-prompt stats, and layer-major prefill may report it unused.
W4A8 reads its mode and prints its line lazily on first use, not at startup. Request-log evidence, not a new
readiness gate, must prove these arms engaged.

### Variables deliberately left unpinned

The v0.2.12 exclusion tripwire in `tests/unit/test_profile.py` prevents these variables from entering any group.

| Variables | Reason |
|---|---|
| `STRATA_ADAPT_FETCH`, `STRATA_ADAPT_FETCH_MIN`, `STRATA_ADAPT_FETCH_MARGIN`, `STRATA_ADAPT_FETCH_VERIFY` | PRO is all-resident and uses batch slots; a layer split refuses adaptive fetch; the 5090's 99.4–99.9% VRAM hit rate leaves little gain, with async-tier interplay unreviewed. |
| `STRATA_VNNI_TIER`, `STRATA_NO_VBMI` | No applicable lane: the PRO CPU lacks AVX-512, the 5090 CPU already uses the full tier, and the pair CPU lacks VNNI. |
| `STRATA_NO_IQ4XS512`, `STRATA_IQ4XS512_MIN`, `STRATA_IQ512_FUSED_MAX`, `STRATA_IQ512_FUSED_TYPES`, `STRATA_NO_Q50_512`, `STRATA_Q50_512_MIN` | Keep bit-identical defaults; the fused variant changes rounding, and these packs have no Q5_0 experts. |
| `STRATA_DF2_GATE`, `STRATA_DF2_ROW_MS` | Only Mac measurements; row cost is uncalibrated on these cards and batch-slot applicability is unreviewed. |
| `STRATA_SELECT_TWO_PASS_MIN`, `STRATA_SELECT_TWO_PASS_CHECK`, `STRATA_W4A8_CFG` | Keep thresholds and kernel configuration at stock defaults; two-pass checking is a one-GPU diagnostic, and W4A8 configuration needs a separately measured sub-arm. |
| `STRATA_PF_PEER_CPU`, `STRATA_ADAPT_OVERLAP` | The new peer-mode paths are unused; the pair is a layer split. |
| `STRATA_HC_Q8_ALL_STAGES` | `STRATA_HC_Q8` stays off on these CUDA lanes. |
| `STRATA_PF_DM16`, `STRATA_PF_FUSED_Q50`, `STRATA_GDN_CHUNKED_MIN` | HIP/gfx only. |
| `STRATA_FILE_TIER_HONEST`, `STRATA_FILE_TIER_IDLE` | Linux-only or no applicable effect on these Windows lanes; stock defaults stay in force. |
| `STRATA_MANIFEST`, `STRATA_FOLLOW`, `STRATA_FOLLOW_LOGPOS`, `STRATA_ROUTE_DUMP`, `STRATA_PF_ALLOC_TRACE`, `STRATA_FORCE_FAULT` | File writers at env-named paths or test-fault injection; never profile pins. |
| `STRATA_DFLASH2_TUNED_URL`, `STRATA_UNDECLARED_TOOL_CALLS` | Control/server variables, not engine groups; the former adds a network path, and the latter is not pinned here. |
| `STRATA_W4A8_NT`, `STRATA_TP_HD` | Preprocessor macros, not environment variables. |

Arm id tokens after `env` are `86` = `sm86_table`, `p` = `parallel_stack`, `g` = `gdn_stack`,
`t` = `select_two_pass`, and `w` = `iq4nl_w4a8`. Pair arm families omit `-parking` uniformly: keeping it
would make the combined `env86gtw` id 121 characters, beyond the 120-character profile-id limit. Descriptions
still name automatic conversation parking. Each changed setting requires its own profile and root; source admission
alone promotes no arm.

### Observed outcomes on the v0.2.12 arms (2026-11-07–08)

In every arm `B` block of the three-pair cold-start A/Bs (`A1 B1 B2 A2 A3 B3`, `B/A` paired geometric mean with per-pair
ratios in brackets), engine request-log lines proved engagement (`STRATA_SELECT_TWO_PASS` ON line and per-prompt
statistics with no `"not used"` line; `STRATA_IQ4_W4A8` ON line and exit counters;
[MEASUREMENTS.md](MEASUREMENTS.md), [DECISION.md](DECISION.md)):

- **`STRATA_SELECT_TWO_PASS=1` (`select_two_pass`, id token `t`):**
  - **Adopted on the RTX 4090 + RTX 3090 pair (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`):**
    passed all 96 checks in its paired cold-start A/B against the `v0.2.12` pair profile
    (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`),
    meeting the targeted 200K cold TTFT bar at `0.976 [0.981, 0.977, 0.970]` (`<= 0.98`), and passed every gate in its
    requalification chain (G10–G21, G26; pilot `6/6`, G24 `15/18` with `bugfix-b` `2/3` and `tool-loop` `1/3`). It
    becomes the pair's current profile, with the qualified `v0.2.12` `env86g` profile as its rollback.
  - **Not adopted on the RTX PRO 6000 (`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0`):**
    missed 3 of 96 checks against the `v0.2.12` four-slot DFlash2 profile — four requests TTFT p50
    `1.114 [0.988, 1.038, 1.345]`, and two requests TPOT p95 `1.056 [1.016, 1.161, 0.998]` and max
    `1.076 [1.017, 1.216, 1.008]` — although the targeted 200K cold TTFT `0.978 [0.982, 0.975, 0.977]` passed its
    `<= 0.98` bar. No chain ran (owner decision `"Keep the base"`), and both the server profile and its Studio route
    `client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0` remain drafts (`1011368`).
  - **Not adopted on the RTX 5090 262K lane (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`):**
    passed all 96 checks against the `v0.2.12` `envg` profile (`200K cold TTFT 0.971 [0.969, 0.971, 0.974]`; its product
    with the version A/B also passed all 88 checks against `v0.2.11`), and passed every gate in its requalification
    chain except G18 (G24 `17/18`, `multifile-regression` `2/3`), where the long-session gate's session never compacted
    in 40 read turns (peak engine prompt `207,269` tokens) because from the 21st turn the model read only the first 100
    and last 3 lines of each document. The owner kept `envg` current (`"Keep envg current"`), and `envgt` remains a
    draft with its published failing ledger (`953a31f`, draft blocker recorded in `1011368`).
- **`STRATA_IQ4_W4A8=2` (`iq4nl_w4a8`, id token `w`) — not adopted on the pair (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0`):**
  missed its paired cold-start A/B against the `v0.2.12` pair profile: cold-TTFT geomean over 8K / 32K / 100K was
  `1.000 (1.001, 1.003, 0.998)` against the required `<= 0.98` (no TTFT gain), 32K decode fell to
  `0.917 [0.926, 0.932, 0.894]` (server decode time `1.089`), and one-request max inter-token gap p50 rose to
  `1.153 [1.027, 1.378, 1.084]`. The kernel ran about `6.8K` IQ4_NL products per block and declined about `11.2K` for
  architecture. No requalify chain ran, the planned combined two-pass + W4A8 arm did not run, and `env86gw` stays a
  draft (`1011368`).

## Strata v0.2.11 setup and start-path review (engine 0.1.57)

This section records the source admission before hardware qualification; on 2026-11-06 the PRO (four-slot `df2`
current and `batchmtp` rollback), RTX 5090 262K default, pair `df2` and Studio routes qualified on stock Strata
[v0.2.11](https://github.com/Niko1221/Strata/releases/tag/v0.2.11) (while the RTX 5090 131K alternative stayed on
v0.2.10 after failing G15 twice; [decision](DECISION.md)). Stock Strata v0.2.11 has tag object
`4a4160162e4a402e082f41aa0a88e6eed629d913`, target
`c3b3f5035506f3e966f1b4b7b188aeaabae92f1d`, and Control/engine **0.1.57** (build `0bdcef4682c5+cuda13.0` in
`strata-engine-0.1.57-windows-x86_64-cuda-cuda13.tar.gz`, 627,812,560 bytes; the Control release notes name app build
`975eaab2bb40`, while drafting derives the engine component identity with `inspect_archive`). Stock OMP **18.16.0**,
commit `650f3a108229ee11bf68ba3377f4e8c3391cd424`, is unchanged.

### Exact setup admission

The planner still executes only reviewed AST slices, never setup's main, hardware probes or installers.
`UNSLOTH_V31_REVISION`, `UNSLOTH_V31_ENGINE` and `UNSLOTH_V31_IQ4_XS` are substituted only when their assignments
are literal. The changed `unsloth_default_env` keeps the native Windows values; its Linux gfx12 exception is
unreachable with the planner's fixed Windows/hip inputs. The exact `FAMILIES` assignment alone may execute its
new shard-table comprehension and `.items()`; the generic `pure_exec` vocabulary is unchanged.

`model_file` and `model_quant` are exact reviewed helpers. A model-specific Hub revision or quant override is
refused before host-shape planning, because this planner's family URL does not implement it. Thus the Unsloth
v3.1 catalog entries remain unadmitted. Existing IQ3_S, Coder IQ1_M, MTP and DFlash2 source pins are unchanged.
The reviewed disk slice now contains `margin`, `mtp_fetch`, `copy_gb`, `real`, `need`; `copy_gb` is zero with
low-RAM mode off. Existing 5090 and manual-split pair plans retain their flags, shard names and conservative floors.

The new `bench_tips` takes the sizing GPU as its eighth argument and calls `bare_auto_is_32768`. Single-card
planning uses reviewed architecture facts from the profile's pinned GPU model (doctor checks that model), never
from the planning machine. Its environment probe goes through install's scrub, so ambient `STRATA_NV_CHUNK`
and `STRATA_DEFAULTS` cannot alter the plan. Stock no longer prints the PRO's `--prefill auto:32768` tip on this
CC 12.0 card. New PRO and associated client-route drafts therefore drop that tip and retain bare `--prefill auto`;
the engine's NVIDIA ceiling is 32768, subject to fit and RAM guards. A predecessor still keeps its own printed tip.

The initial all-resident Unsloth review covered `UD-IQ4_XS` and `UD-Q4_K_XL` on the PRO's 262,144-token, four-slot,
90–100 GiB single-GPU shape with `(8, 16)` CPU cores, int8 KV and automatic KV streaming (extended for the `v0.2.11`
one-slot comparison lane [below](#pro-quality-first-one-slot-comparison-admissions)). `budget_lane_review`
requires a unique complete v0.2.9 or v0.2.11 set of exact statement/helper digests, each present once; mixed
releases, edits and duplicates refuse. At v0.2.11 the config-env caller adds the GPU architecture argument,
`unsloth_budget` gains `uma_holds_experts`, and `unsloth_default_env` changes. The budget/UMA and small-card
branches were rehashed and remain unchanged and unreachable. `UD_FIT_CARD_GB` and
`UNSLOTH_RESIDENT_BESIDE_GB` remain literal. The helper namespace fixes `sys.platform` to `win32` and asserts
a non-UMA GPU before the budget gate, so `uma_holds_experts` never reaches its `uma_pool` import. No planning-host
platform or hardware probe runs.

On this host stock keeps every expert in RAM and caches part in VRAM: `setup_env` is exactly
`{"STRATA_HC_Q8": "1", "STRATA_ROUTE_TAIL_SKIP": "0"}`, with no `--resident-budget-gib`. The all-resident
floor for UD-Q4_K_XL is `77 / 1.073741824 + 16` GiB; 80 GiB RAM refuses instead of silently selecting a
RAM-budget plan. The v0.2.9 UD-IQ4_XS tree retains its reviewed flags, three shards and 100 GiB disk floor.

Canonical full-field AST SHA-256 values below were computed from stock tag sources with omp-strata's
`reviewed_hash` on CPython 3.13.18. CPython 3.12 was not installed at the conditional local interpreter path;
its CI equivalence remains a verification requirement. Headers in the source-only fixtures separately bind raw
source/payload bytes; no fixture module is imported as an installer.

| Reviewed surface | AST SHA-256 |
| --- | --- |
| `setup.unsloth_default_env` | `17ef141cc23ddefffb99d743e8465e86646a8ab3032baa7699451ac5ebb8c221` |
| `setup.FAMILIES (exact Assign)` | `ccd5b88d8b1dcd8dd24533f494434e4d0b32ea5a5c2b523c17538b508c9ce58f` |
| `setup.model_file` | `cb18d7e1a5240d6e0ee242eb61adbbbbdf80584c358c24e918cef648077f4df9` |
| `setup.model_quant` | `7767bdb606295069b2e6f90c35523b46207bfa853158a703590bbd492d0ac24d` |
| `setup disk slice (exact Module)` | `b9e5b7cf8d8497e38322a8e8a847c6d9f3a25e2afa2b55d7c3225ff72ac9fe4c` |
| `setup.bench_tips` | `5a2c2350f18994d1427e5ff9277dd4f5c8657cb7eac1af9ebe498c759bd93a72` |
| `setup.bare_auto_is_32768` | `3e78cb9621f09ee3089f08633c6b2c1958b9c3d4ce9f229c82a3feb8adaf3492` |
| `setup.unsloth_budget` | `cc2cd5d43f15ff47d4f60ef680d366c449c437d9e797391c25b96d3be8e4f337` |
| `setup.uma_holds_experts` | `0351f2ea3e2bc3e894e410968aa2c2c36959ab748b8f70ab95c8c321234966f1` |
| `setup uenv config If (exact statement)` | `baaeb4b0d9efae3b70a07d86d9ea6ec31a0dbf46c3936376487fe0c58707e77d` |
| `server.nodraft_retry_args` | `a0f87b0aa45bcfa1e9734b3d4da4027736f614eaf316a9c036c4e3a86c0a0a3d` |
| `server filtered import bindings (unchanged)` | `b3a207845da9c931bf60dd9eac96b393134c22152a205b06ac5a713b4a6e7d86` |
| `strata_control/drafting.py` | `1e1f090324fe13fd4401771b945a13bd0e9d0240e4ae0168150ec3d7092bf81d` |
| `strata_control/vram_fit.py` | `82640f0265b95ea4e034b658be0af93c265f65bff36cd2434774034547929cac` |
| `strata_control/draft_layer.py (unchanged)` | `2dc95f87df38f38700273dfc67a1cdc9a01a9001048d701069d3b050528e8d17` |
| `serve/nonblocking_out.py` | `bfafefc76dc2a98bdeba9882a32db519514ab91652675d06d4b132c050ac0fe3` |
| `strata_control/runtime.py` | `c4b7c9d4ce6835c833c3c4ae24fc6d39b4f7e39bc8816f8246ce06979ec15381` |
| `strata_control/paths.py` | `18c3979b7ab17d40675c2f6e91a0a6b48203f24bfbd912f764cd4ba32e23702d` |

### Server/app/engine binding and the integration-root boundary

A server review is selected by a **unique full match**: every function, the complete same-module closure from
its roots, filtered import bindings, imported modules and separately pinned sources. The 0.2.11 review adds
`nodraft_retry_args` as a root; the earlier closure and import bindings are unchanged. `drafting.py` and
`vram_fit.py` change; `draft_layer.py` does not. Whole-module source pins also cover runtime/path override
semantics and bounded nonblocking console output. Missing optional files at older tags are skipped while reading
review candidates, not fabricated. The selected 0.2.11 review is bound to engine 0.1.57; mixed modules, ambiguous
matches, source drift or a 0.1.56 engine with the 0.2.11 app refuse. DFlash2 pin discovery uses that selected review
and actual tag in its provenance, not a hard-coded 0.2.10 module.

Runtime identity is engine-keyed. Engine 0.1.56 retains exactly `serve/server.py`, `strata_control/drafting.py`,
`strata_control/vram_fit.py` and `strata_control/draft_layer.py`. Engine 0.1.57 adds `serve/nonblocking_out.py`,
`strata_control/sysinfo.py`, `strata_control/targets.py`, `strata_control/runtime.py` and `strata_control/paths.py`:
nine files, all hashed by install and written by synthetic-install fixtures. The old unversioned constant was
removed; callers use `start_path_sources(engine)` / `install.runtime_sources(profile)`.

[Server main](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/serve/server.py#L9828-L9853)
now takes a shared activity lease. Its runtime helper consults `STRATA_RUNTIME_DIR` **before** the per-user state
base, requires an absolute path, creates/secures the directory and writes `.activity.lock` there. For engine
0.1.57+, both server and stock setup/tool environments pin the absolute `<root>/state/strata-runtime` directory,
created before launch. ACL repair is confined to that dedicated subfolder, never the state folder holding the API
key. A lease failure is tolerated by stock; absence of a lock is not a new start gate.

The source audit found another writer: `serve/lifeline.popen` calls `procs.write_record`, which writes/deletes
`paths.state_base()/procs/<pid>.json` and does **not** consult `STRATA_RUNTIME_DIR`. Therefore engine 0.1.57+
also redirects `LOCALAPPDATA` to absolute `<root>/localappdata` in both environments. Setup's driver/component
search is read-only in this pinned prebuilt lane; the offline calibration/drafting helpers do not enter updater
or managed-install paths. Doctor reports the user's existing activity lock as a non-blocking check and leaves it
untouched. Engine 0.1.56 retains its qualified environment and byte-identical runtime identity.

### Engine defaults, start refusals and observations

Engine 0.1.57 joins the exact env-review set; all **20** variables in `parallel_stack`, `gdn_stack` and
`sm86_table` are unchanged. No partial group or ambient tuning variable is admitted.

- **Single-card PRO / RTX 5090:** bare `--prefill auto` may take 32768-token chunks; the startup fit scan may
  choose less, and the RAM guard steps the ceiling through 16384 to 8192. `STRATA_NV_CHUNK` remains unpinned.
  The PRO and SSH client route follow stock's dropped tip; the 5090 bare-auto change still needs paired host evidence.
- **Layer-split pair:** prompt chunks remain 8192. Each stage refines its PCIe/CPU miss share. Later stages keep
  256 MiB for late allocations, with an additional reserve on DFlash2's last stage. The split spill walk is refused,
  not silently accepted as another shape. Stage-order admission for 0.1.57 was withheld during source review until one
  measured pair start parsed complete, and was admitted on 2026-11-06 (`772a418`) after the pair DFlash2 measurement
  start confirmed configured `[1, 0]` stage order (layers 0-23 on the RTX 3090, 24-47 on the RTX 4090) with `19.41 /
  17.90 GiB` expert caches and one engine generation.
- **All lanes:** K-quant MMQ prompt kernels are on by default for the relevant CC >=8 CUDA cards, but act only on
  K-quant experts (not the current IQ3_S / IQ1_M experts). An Auto start short of GPU memory may retry with no
  drafter; that retry is refused. Server stream writes have a 60-second timeout. Automatic FP16 weight caching is
  Linux CUDA batch-only in 0.1.57, not a Windows performance change.

Start diagnostics are engine-keyed: 0.1.56 keeps its original five markers. The 0.1.57 map additionally refuses
per-card head-on-host, DFlash2 removal, a reduced KV window, the no-drafter retry, a missing K-quant library, and
every `strata generate: short of GPU memory:` walk diagnostic. The source has **16** such formats in
`generate.cpp` and **one** in `native_head.cpp`, all degraded/low-memory paths, including failed head migration
inside the walk. None occurs in the searched qualified v0.2.10 evidence. More than one engine generation in the
new launch interval also refuses on single-card Auto lanes. `SHORT_OF_VRAM` is an off drafting note already
refused by the unchanged drafting gate; it is not an admitted MTP reason.

For bare-auto 0.1.57 starts, `run.json` records every current engine-interval line beginning
`strata generate: NVIDIA: ` in `prefill_ceiling`, with its interval. This is observation only: a RAM-guard line or
an absent line does not refuse. The raised-ceiling and optional RAM-step lines print at startup. K-quant library
success/missing output also occurs at native K-quant startup, before the expert cache is allocated, because the
engine probes each expert format; current IQ experts need not emit it.

### Environment-name census and deliberately unadmitted paths

The tracked-source census grows from 1160 to 1170 names, with no removals. Every new name stays unpinned and
inherited values are stripped by `server_env` / `build_env`:

| New name | Disposition |
| --- | --- |
| `STRATA_BLOCKING_CONSOLE` | Keep stock bounded nonblocking console; no override. |
| `STRATA_GFX12_RING` | Other-backend tuning; not this native NVIDIA lane. |
| `STRATA_NV_CHUNK` | Keep stock bare-auto ceiling and RAM guard; observe, do not pin. |
| `STRATA_NV_KQ_DEFAULT` | Keep stock K-quant default; no override. |
| `STRATA_PCIE_K_RULE`, `STRATA_PCIE_SHARE_MAX` | Keep stock miss-share rules; no tuning. |
| `STRATA_PF_OWN_PROBE_OFF`, `STRATA_SPLIT_EARLY_OFF` | Probe/early-path opt-outs remain unset. |
| `STRATA_STREAM_WRITE_TIMEOUT_S` | Keep the stock 60-second timeout. |
| `STRATA_TEST_KEY` | Test-only name; never pass it through. |

`STRATA_RUNTIME_DIR` predates this census delta but is the one intentionally reintroduced root-local Strata
variable (alongside the owned API key); it is not a performance knob. LOCALAPPDATA redirection covers process
records independently of it.

Upstream now has per-slot DFlash2 drafters, but their profile/start admission is separate Part B work. The source
audit establishes that DFlash2 slots still call `Verifier::init_slots`, emit `batch windows of up to`, and retain
`one-row windows keep their rows` with `parallel_stack`; the PRO arm can keep `envpg`. The disk slot-save issue
[Strata#5153](https://github.com/Niko1221/Strata/issues/5153) does not affect conversation parking: disk save is
disabled without `--slot-save-path`, and the server returns 501 for parallel requests. Unsloth v3.1 revision/quant
overrides stay refused.

### PRO UD-Q4_K_XL comparison-only screen

The [UD-Q4_K_XL profile](../profiles/win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0.json)
is **comparison-only, never current**. It is a speed re-screen, not a qualification lane: there is no CI matrix
row or `campaign.LANES` entry, and its release ledger starts with every gate `not_run` and no inherited receipts.
No hardware result, readiness or comparative claim follows from drafting it.

The predecessor is the v0.2.9 UD-IQ4_XS PRO screen, preserving 262,144 tokens, four batch-MTP slots, PLE direct,
int8 KV and stock automatic KV streaming (`--kv-resident 32768`). Stock drops the old prefill tip, so the new
profile uses bare `--prefill auto`. All experts stay in RAM, with only part cached in VRAM. Its exact
`setup_env` is `STRATA_HC_Q8=1`, `STRATA_ROUTE_TAIL_SKIP=0`; neither `--resident-budget-gib` nor `engine_env`
is present.

The model uses stock `UNSLOTH_SHARDS`, not `UNSLOTH_BIG_SHARDS`: four 09-30 UD-Q4_K_XL GGUFs at revision
`38bb39ee97821de2c9009abb7e93950eec396e66`, totaling **111,334,654,784 bytes**, each size and SHA-256
cross-checked against the pinned Hugging Face LFS object. Plan for a fresh model download: the v3.1 re-shard is
a different layout, and none of the existing PRO comparison roots supplies these four files. The stock MTP
tensors also need a fresh approximately 5.2 GB download on the proposed drive; the checkpoint-generated NVFP4
MTP is not reusable here.

The exact-byte stock disk formula is `ceil((111334654784 + 5.2e9 + 8e9) / 2**30)` = **116 GiB** free.
The all-resident RAM boundary is 87.71183824539185 GiB, rounded up to **88 GiB available at start**;
the predecessor's raised **96 GiB total RAM** floor carries forward. The draft preserves its own root and ledger.
A D: root is permitted only after its physical disk is confirmed as an SSD: PLE direct reads the file every token.
If it is an HDD, return to the owner for space on the PRO's SSD; do not silently drop PLE direct.

Engine 0.1.57 enables K-quant MMQ prompt kernels by default on CC >= 8. On 2026-11-06 (`06:45–07:24Z`, result directory
`tuple-0211-pro-udq4-20261106T064547Z-20261106T0724Z`), the four Unsloth `UD-Q4_K_XL` shards (`111,334,654,784` bytes)
were fetched and verified on the PRO's `E:` SSD (`86.6 GiB` free after the screen), and engine `0.1.57` printed `a model
with K-quant experts (Unsloth UD-Q4/Q5/Q6_K_XL) reads its prompt on llama.cpp's MMQ kernels` and loaded
`strata_kq.dll (STRATA_MMQ_KQ=1)`, so the K-quant prompt kernels were active on Windows. In the report-only three-pair
cold-start screen (`A1 B1 B2 A2 A3 B3`, `A` =
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`, `B` =
`win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0`), `B` was slower than `A` in
every measured workload ([measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160)):

| Metric (`B/A`) | 0 | 8K | 32K | 100K |
|---|---|---|---|---|
| Cold single-request TTFT | `1.243` | `1.267` | `1.195` | `1.168` |
| Prefill | `0.799` | `0.789` | `0.835` | `0.855` |
| Decode | `0.899` | `0.915` | `0.883` | `0.848` |

- Warm 32K repeat: TTFT `1.003`, prefill `0.961`, decode `0.894`.
- Total output throughput: `w2` `c1 0.844`, `c2 0.766`, `c4 0.731`; `w3` `c4 0.815`.
- TTFT p50: `w2` `c1 1.211`, `c2 1.235`, `c4 2.490`; `w3` `c4 1.188`.
- TPOT p50: `w2` `c1 1.159`, `c2 1.308`, `c4 1.324`; `w3` `c4 1.216`.
- Rule-4 decode at 32K: `0.883`.

Disposition: comparison-only (never a main chain or a current profile, with no CI or campaign row; its root was deleted
after the screen at the owner's request); any switch would still need Terminal-Bench, which is out of scope here.

### PRO quality-first one-slot comparison admissions

For the quality-first comparison on the native Windows RTX PRO 6000 (`90–100 GiB` VRAM, `(8, 16)` CPU cores, stock
Strata `v0.2.11` / engine `0.1.57`, stock OMP `18.16.0`), reviewed stock setup planning also covers the one-slot
`262,144`-token `int8`-KV lane (`--kv-streaming off`, `--ple-io direct`, stock DFlash2 alone via
`strata.drafting: "dflash2"`, stock `gdn_stack` in `strata.engine_env`, no `--parallel`, no `--batch-mtp`, no
`--kv-resident`, and OMP `maxInFlightRequests` `1`) across `qwen / IQ3_S` and the four all-resident `unsloth` GGUF
quantizations from `unsloth/Qwen3.8-Flash-Next-GGUF` at revision `38bb39ee97821de2c9009abb7e93950eec396e66`:
`UD-Q4_K_XL` (four `UNSLOTH_SHARDS` files, `111,334,654,784` bytes; the Unsloth `v3.1` revision
`d96201194f103c906994f283f504209dc8d2a10c` `UD-Q4_K_XL` re-shard carries the same `1,224` tensors with identical types and
shapes and stays unadmitted) and `UD-Q5_K_XL`, `UD-Q6_K_XL` and `Q8_0` (six `UNSLOTH_BIG_SHARDS` files each). Every
Unsloth plan keeps all `24,576` experts in the resident RAM arena (no `--resident-budget-gib`, `--mmap-experts` or
`--resident-experts`, refusing lower RAM instead of falling back to a budget plan), with stock setup RAM floors of
`78 GiB` (`IQ3_S`), `88 GiB` (`UD-Q4_K_XL`), `109 GiB` (`UD-Q5_K_XL`), `120 GiB` (`UD-Q6_K_XL`) and `139 GiB` (`Q8_0`)
(the one-slot `IQ3_S` draft carries forward the incumbent's higher `96 GiB` `min_total_ram_gib` floor),
and pins stock `unsloth_default_env` in `strata.setup_env`: `{"STRATA_HC_Q8": "1", "STRATA_ROUTE_TAIL_SKIP": "0"}` on
`UD-Q4_K_XL`, adding
`"STRATA_MMQ_KQ": "1"` on `UD-Q5_K_XL` and `UD-Q6_K_XL`, and `{"STRATA_ROUTE_TAIL_SKIP": "0"}` on `Q8_0` (`UD-Q5_K_XL`
and larger already carry the `Q8_0` n-gram table; a separate `Q8_0` n-gram table for `UD-Q4_K_XL` is not a stock setup
choice).

- **Conflict-free `setup_env` ∪ `engine_env` union:** when a profile pins both stock `strata.setup_env` and reviewed
  `strata.engine_env` groups, profile validation, guarded `install`, generated-config verification and `start` require
  the generated config `env` to equal their exact key-value union and reject any key where `setup_env` and `engine_env`
  assign different values, rather than overriding stock's environment or merging unreviewed keys.
- **`doctor` disk credit for root-local pinned inputs:** `doctor` credits exact-size pinned `model`, `dflash2`, `engine`
  and `llama` files already present inside the integration root toward `host.min_free_disk_gib` (which budgets a fresh
  download), so pre-fetched or hard-linked inputs do not require twice their size in free disk space while `fetch` and
  `install` remain responsible for SHA-256 verification.
- **Kept comparison drafts and dropped unscreened drafts:** two Qwen comparison-only drafts remain checked in with every
  ledger gate `not_run` and no CI or campaign row — the incumbent's one-slot form
  [`win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`](../profiles/win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json)
  (fingerprint `ab60b81c833c3839`, `83,617,662,656` model bytes, `96 GiB` total / `78 GiB` start-available RAM, `93 GiB`
  disk floor; [ledger](../releases/win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0/qualification.json))
  and
  [`win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`](../profiles/win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0.json)
  (fingerprint `81cd556548451fe3`, `158,286,406,650` model bytes across six shards, `109 GiB` total / `109 GiB`
  start-available RAM, `162 GiB` disk floor;
  [ledger](../releases/win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0/qualification.json)).
  On 2026-11-06 on `rtxpro6000-win-a`
  ([measurements](MEASUREMENTS.md#quality-first-comparison-on-the-pro-2026-11-06-stock-strata-v0211-stock-omp-18160)),
  one-slot `IQ3_S` started in `71 s` and decoded at `404.4 tok/s` at 32K (`8,610 tok/s` prefill, `3.86 s` / `11.56 s`
  TTFT at 32K / 100K, `58,278 MiB` GPU, `129.3 GiB` min available RAM, `99.42 GiB` commit headroom, `8,192 MiB` cache),
  and one-slot `UD-Q5_K_XL` started in `85.7 s` and decoded at `296.7 tok/s` at 32K (`7,712 tok/s` prefill, `4.29 s` /
  `12.83 s` TTFT at 32K / 100K, `22,209` of `24,576` experts in `82.80 GiB` VRAM at `98.4–99.9%` decode hit rate,
  `95,794 MiB` GPU, `83.6 GiB` min available RAM, `17.12 GiB` commit headroom, `5,888 MiB` cache, K-quant prompt kernels
  active), passing `20/22` vs `21/22` on the four-slot `IQ3_S` incumbent. Initial one-slot drafts for `UD-Q6_K_XL`,
  `Q8_0` and `UD-Q4_K_XL` (fingerprint `811590f6eaa867b9`, fallback only if `UD-Q5_K_XL` failed fit or speed) were
  dropped unscreened while keeping unit-test coverage of stock planning for all five models; the four-slot `IQ3_S`
  DFlash2 incumbent and its Studio route stay current
  ([decision](DECISION.md#update-2026-11-07-quality-first-comparison-on-the-pro-keeps-the-four-slot-iq3_s-incumbent)).

### Python lock and W16 correction

`locks/strata-python-cp313-win_amd64-strata0.2.11.txt` derives from the 0.2.7 lock, changing only Pillow to 13.0.0
for stock's GHSA-78g4-xqwv-q3g8 fix. [PyPI metadata](https://pypi.org/pypi/pillow/13.0.0/json) pins the
`pillow-13.0.0-cp313-cp313-win_amd64.whl` wheel at 7,284,777 bytes and SHA-256
`9dda0788a9932776a75d8bcc020076edc308ce2508b51f6739a45e3158b3fc42`; all Requires-Dist entries are extra-only.
The unchanged textual/CUDA closure keeps 26 pins. Dependency review refuses no new lock, stale Pillow or an extra
pin. New v0.2.11 server drafts must pass this lock; an unchanged-requirements derivative must not pass it again.

**Correction of the earlier 0.1.56 note:** its FP16 weight cache is off by default, not an automatic default:
[`gemm.cu` at v0.2.10](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/src/prefill/gemm.cu#L1411-L1422)
assigns a zero budget without the explicit switch. The 0.1.57 automatic enablement is
[Linux CUDA batches only](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/src/program/generate.cpp#L8176-L8181).
No W16/FP16/weight-cache claim was copied into MEASUREMENTS.md; its measured results are unchanged. Neither switch
is pinned, and historical qualified profile records are not rewritten.

## Stock DFlash2 batch-slot arm (v0.2.11 / 0.1.57)

Named `strata.drafting: "dflash2"` may use stock `setup_args.parallel` batch slots only on one card with engine
0.1.57 or newer, whose `STRATA_BATCH_DF2` path supplies one drafter per slot. Engine 0.1.56 and multi-card batch
drafting remain refused. Pipeline windows, batch MTP and calibration remain incompatible with named DFlash2;
start-time DFlash2 flags stay forbidden in config args. The one-request pair arm below is unchanged.

Each batch-slot start must additionally contain exactly one full stock `strata generate: STRATA_BATCH_DF2: N slot
drafters on CUDAk` line and one full `strata serve: STRATA_BATCH_DF2: N slot drafters ready` line in this start's
engine-log interval, with both counts equal to `parallel`. The CUDA ordinal and private MiB per drafter are
observed, not pinned; `run.json` records them with both complete lines under `drafting.slot_drafters`.
Missing, repeated, malformed or wrong-count lines refuse, as do either off form, the warning form naming
`STRATA_BATCH_DF2 (the slots' DFlash2 drafts)`, and per-slot allocation, binding or preparation failures.
Slot evidence in the server stream, or on a profile without slots, also refuses.
Provenance: [`generate.cpp` at v0.2.11](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/src/program/generate.cpp#L7157-L7177)
and its [serve binding](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/src/program/generate.cpp#L11576-L11587).

Draft this separate PRO arm from the v0.2.11 `slots4-batchmtp-pledirect-kvvram-envpg` profile with
`--drafting dflash2 --drop-batch-mtp`. The drop requires a carried batch-MTP pin and cannot accompany
`--batch-mtp`. Stock setup's config args stay identical except for removing `--batch-mtp`; stock drafting
rewrites its start-time args, not the pinned setup flags. The variant retains `parallel_stack` and `gdn_stack`:
the verifier still initializes every batch slot with DFlash2 and prints the reviewed batch-window self-commit
line. Source and pack pins reuse the pair's offline preparation path; the fresh-install disk floor includes
the DFlash2 inputs, both packs and vocabulary. OMP still limits this server to four in-flight requests.
Campaign intake accepts the `slots4-df2-pledirect-kvvram-envpg-parking` family before the batch-MTP variant; on
2026-11-06 the four-slot DFlash2 arm qualified as the PRO's current profile (with the v0.2.11 batch-MTP arm as its
qualified rollback; [decision](DECISION.md) and [measurements](MEASUREMENTS.md#strata-v0211-windows-2026-11-06-stock-omp-18160)).

## Stock DFlash2 pair arm (v0.2.10 / 0.1.56)

This section records the source admission of the pair DFlash2 arm (qualified as the pair's current profile on
`v0.2.10` on 2026-11-03 and on `v0.2.11` / engine `0.1.57` on 2026-11-06; [decision](DECISION.md)).
`strata.drafting: "dflash2"` pins stock's config choice; absent means stock Auto. Only the Qwen family is reviewed, with
one request at a time and no
pipeline windows, batch MTP or calibration. The model's `dflash2_source` pins the two files from
`incoai/Qwen3.8-Flash-Next-DFlash2` at `a22a1744e85c17364dcc54a6a420af7135d4c7f6`, both locally produced packs and
the stock vocabulary by SHA-256. The source and pack identities come from stock `strata_control/drafting.py` at
`v0.2.10`; the explicit choice does not authorize a start-time fetch or a silent MTP fallback.

Fetch stages the two revision-resolved HF inputs under `downloads/dflash2/<revision>/`. The prepared folder is
`data/dflash2`: stock `drafting.data_dir_of` derives `data` from setup's `--mtp data/mtp/rt`, then appends `FOLDER`.
The macOS client downloads neither DFlash2 file; only the GPU runtime installation uses them.

Install runs stock `tools/dflash2_pack.py` with the root's hash-locked venv:
`model.safetensors config.json <partial> --q4_0`, then `--convert-selector <q4_0> <partial>` when the staged engine
contains stock's selector marker (`tools/dflash2_pack.py:4-5,257-265`). Each output must match stock's byte count
and SHA-256 before atomic promotion. `drafting.provide_vocab` supplies the local vocabulary and
`drafting.converted_ok` creates the stock `.ok` marker during install. The complete prepared data tree is part
of runtime identity. A foreign carried config choice, `src/` or partial-file leftovers refuse installation.

Stock `drafting_fetch.ensure()` is deliberately bypassed: on a fresh build it calls `acquisition.require` before
checking local source files, so `STRATA_NO_ACQUIRE=1` refuses it; without that guard a missing input can reach the
network. Only the offline CLI and local helpers run, with the install's scrubbed environment plus
`STRATA_NO_ACQUIRE=1`. Stock setup argv stays unchanged: **no `--drafter`**, and the verified MTP files and
vocabulary remain installed. Applying `"drafting": "dflash2"` changes no args or setup stamp.

Start requires exactly one server `drafting: DFlash2 alone` line and one engine `strata serve: DFlash2 drafter on`
line, with no loaded MTP and the exact pinned runtime-pack path. A layer split must name the last CUDA stage
and stock's confidence 0.35. The selector line is required only for `selq4`. Missing, repeated, malformed,
fallback/refusal/retry evidence or multiple engine generations fail the start. The positive lines and both
start intervals are recorded as `run.json` `drafting`; no previous generation's evidence can satisfy this.
Provenance: `serve/server.py:3517-3519,1225-1226` at `v0.2.10`, engine build `06698c674`
`src/program/generate.cpp:11161-11175` and `src/core/dflash2.cpp:398-400`.

The real-host gate drivers contain no engine-argv, speculative-acceptance, or drafter-specific cache assertions:
their generic acceptance prose, `inspects append.py` transcript helper and rejected-key label `accepted` are not
MTP assumptions. They remain unchanged. Cache sizes are fresh observations, parking/resume lines are
informational, and the separate owner A/B against env86g still requires **at least +3% decode**.
Stock's architecture table marks `sm_86` as measured slower and `sm_89` as untested; the pair's Main 4090 is
staged last and runs the drafter. Neither architecture label is evidence that this pair passes its A/B bar.

Drafting the arm uses `--drafting dflash2 --pipeline-windows stock` on the env86g predecessor. The stock setup
plan is unchanged; config args differ only by dropping `--pipeline-windows 2`. `--drafting stock` drops a
carried drafter choice and its source pins; either `stock` drop refuses when no corresponding pin exists.
The profile id uses `df2` instead of `pw2` to stay within 120 characters. Campaign intake accepts this family
before the current env86g family, without promoting it.

The draft reviews the stock drafting module, fetch orchestration and packer at the exact source commit;
cross-checks HF revision, license, sizes and safetensors LFS SHA-256; hashes the shipped vocabulary; and
scans the artifact-pinned `strata.exe` bytes without execution or extraction. The engine must contain the
DFlash2 ON and vocab-file markers. Its selector marker selects `selq4`, otherwise `q4_0`. HF metadata remains
available in `--no-github-api` mode. The setup disk floor adds the retained source files, both packs and
vocabulary, rounded up to GiB, before selecting `max(predecessor, setup)`.

On 2026-11-03, in three paired cold starts against its `v0.2.10` `pw2` `env86g` MTP sibling
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`),
the `df2` DFlash2 profile
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`)
beat the owner's +3% decode bar at every depth (+8.2% at 8K, `1.082`; +9.3% at 100K, `1.093`; +10.1% / +13.6% / +7.7% at
`0 / 32K / warm-32K`; TTFT at 8K–100K `0.955–0.980`; `w1` / `w3` throughput `1.001 / 1.033`) while missing the 5% rule
on 6-token-window inter-event gap (`w3` max gap `1.075–1.112`, p95 inter-event gap `1.122–1.170`), queued-prefill
(`0.802`, prompt time `1.227`) and empty-prompt TTFT (`1.052`) metrics; under the owner's override (`"Run chain, make
DFlash2 current"`), the requalification chain at `837bc89` (`1f2d483`, qualified in `8a2c9ec`) passed all 14 measured
gates (G10 27.51 GiB commit headroom of 135.69 GiB and 65.65 GiB available RAM, G16/G20/G21 43.1 / 43.2 / 43.4 s, G17
near-limit task 59.0 s, G24 17/18, pilot 5/6, batch wall 916 s), and `df2` is now the pair's current profile with `pw2`
`env86g` `v0.2.10` (G24 16/18, pilot 5/6, 1,045 s) as its qualified rollback
([MEASUREMENTS.md](MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160), [DECISION.md](DECISION.md)).

## Stock UD-IQ4_XS budget lane (v0.2.9)

The model belongs to stock's budget-capable Unsloth family, but **the reviewed PRO choice is not a RAM-budget
configuration**. At `c62d5e3a15b40ea51c96aae9e8d36928965f53ab`, stock `unsloth_budget` returns false on the
192 GiB-RAM PRO: every expert fits in the resident arena, `budget` stays `None`, and setup writes no
`--resident-budget-gib`. The earlier planner's unconditional `budget_choice` would have invented a 55 GiB budget;
the admission instead evaluates stock's actual gate and refuses if it chooses budget mode.

The admission is limited to `unsloth / UD-IQ4_XS`, 262,144 tokens, one 90–100 GiB GPU, four slots, `(8, 16)`
performance/efficiency CPU cores, int8 KV and stock automatic KV streaming. The v0.2.9 gate assignment,
`unsloth_budget`, `unsloth_default_env`, their constants and config-env write are digest-pinned; the reviewed
budget/UMA and small-card branches must remain unreachable. The v0.2.9 config block is mandatory, so the v0.2.8
fixture does not gain an admission. Other contexts, slot counts, cards, layer splits, UD-Q4_K_XL and Q8_0 remain
outside this planner lane. The older reviewed UD-Q4_K_XL budget profiles remain unchanged.

Stock writes `env = {"STRATA_HC_Q8": "1", "STRATA_ROUTE_TAIL_SKIP": "0"}`. The profile records this as
`strata.setup_env`, not an optional engine-env pin; install requires exactly that dictionary, with no extra keys,
and it cannot be combined with `strata.engine_env`. The three GGUF shards are pinned by stock's
`UNSLOTH_IQ4_XS_SHARDS`; setup writes `strata-unsloth-ud-iq4_xs.json`. Like the four-shard Unsloth model, it lets the
engine locate PLE from shard 1: no `--ple-gguf`, and no `experts.bin` in the target pack. The separate MTP pack
still contains its own draft experts. RAM floors preserve stock's all-resident threshold (arena in GiB plus
16 GiB), not the model table's lower budget-mode minimum.

The comparison-only screen's stock setup accepted four slots without warnings, and engine 0.1.55 reported four
batch-MTP slot drafters. These observations permit preparing a separate Terminal-Bench candidate with the PRO's
existing prefill, batch-MTP and PLE-direct pins; they are not hardware qualification or Terminal-Bench results.

## Strata v0.2.10 setup review (component engine)

Stable [`v0.2.10`](https://github.com/Niko1221/Strata/releases/tag/v0.2.10), release **432079269**, published
**2026-11-02T23:52:47Z**: annotated object `db0500a53119a349fa44497099d6e28a83ded34a`, commit
`ffa80d73133ea5c548aefe57889a16e8085a938f`. App **0.2.10** ships Control/engine **0.1.56**; the Windows CUDA 13
component is `strata-engine-0.1.56-windows-x86_64-cuda-cuda13.tar.gz` (**627,806,827 bytes**), SHA-256
`5336671c55bc1b819d076104608522147227001d1711378f35ea5d524bc866ec`, built from **`06698c674`**.
This admission compares stock v0.2.9, not a modified installer. `MIN_ENGINE=(0, 1, 46)`, `HF_REVISIONS`,
`LLAMA_CPP_COMMIT` and the runtime/monitor requirements are unchanged.

### Five reviewed planning surfaces

The unchanged planner at the fixture-only commit reproduced all five refusals independently: default recommendation,
new planning call, fresh-config definition, fresh-config caller and split-disk estimate. The v0.2.10 planning fixture
reuses the v0.2.9 AST-node selection, replaces the changed source nodes and includes `kv_streaming_need_gb` and
its caller. Extraction provenance stays outside the public repository; every selected statement equals its stock AST.
No installer, hardware probe or whole `strata_control` module is vendored or imported by the fixture.

| Surface | Stock v0.2.9 → v0.2.10 statement | Reviewed constant / reason | Effect on these lanes |
|---|---|---|---|
| Informational defaults | `rec_ctx = 32768 if small < 14 else 65536 if small < 20 else 131072` → `rec_ctx = 131072` ([setup:10242-10244](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10242-L10244)) | `DEFAULT_RECOMMENDATION_0_2_10`; the exact selected shape is **eight** nodes: `fams`, `rec_fam`, `names`, `names.sort`, `rec`, `small`, `rec_ctx`, `rec_ctx`. The final unchanged `min(rec_ctx, ram_ctx(...))` RAM clamp remains selected. | Same 131,072-token informational recommendation; explicit model/context choices stay untouched. The preparation plan's seven-node count omitted that clamp. |
| Streaming need | `stream_fits = ram >= MODELS[model]["ram_gb"] + kv_ram_gb + 1` → `stream_need = kv_streaming_need_gb(model, ctx, kv)` then `stream_fits = ram >= stream_need` ([setup:10693-10694](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10693-L10694)) | `REVIEWED_HELPERS_0_2_10` and `STREAM_NEED_0_2_10`; [the helper](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L6207-L6220) takes the smaller of rules (1) and (2) below. Only its exact caller executes it; neither `named_calls` nor `pure_exec` widens. | PRO and 5090 262K still pin KV off; the pair still streams. Coder's rule (1) remains the smaller arm, so its threshold is unchanged. IQ3_S's informational streaming threshold decreases, not its admitted RAM floor. |
| Disk/MTP | `mtp_fetch = 5.2 if (not mtp_have and not ready and a.mtp != "off") else 0.0` gains `and getattr(a, "drafter", None) != "dflash2"` ([setup:10434](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10434)) | `DISK_0_2_10`; only the `mtp_fetch` assignment gets `getattr` in a separate namespace. The planner refuses if `a` has **any** `drafter` attribute, even `None`. | The fresh-root MTP allowance remains 5.2 GB. Install never passes `--drafter`; no DFlash2-only download path is admitted. |
| Fresh-write caller | `write_setup_config(..., explicit_args(a))` gains `after_carry=(lambda c: uma_cache_guard(c, model, gpu)) if gpu.get("uma") else None` ([setup:10968-10969](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10968-L10969)) | `WRITE_CALL_0_2_10`, paired with its version's definitions in `fresh_write_review`. Evaluate only the `IfExp` test; a truthy UMA result refuses rather than dropping the callback. | Our discrete NVIDIA inputs do not carry `uma`; no callback runs. A v0.2.9 definition with the v0.2.10 call, or the reverse, refuses. |
| Fresh-write definition | `write_setup_config(..., explicit=None)` gains `after_carry=None` and calls it before `user_args.stamp` when non-`None` ([setup:6815-6852](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L6815-L6852)) | `FRESH_WRITE_0_2_10`; `carry_user_args` and `explicit_args` retain their earlier digests. Definitions and call must match one complete reviewed version. | With no earlier config/user args and no UMA callback, `args_written` still equals `args`; config keys remain unchanged. |

Stock's streaming helper uses `min((1), (2))`, with
**(1)** `ram_gb + kv_gb + 1` and **(2)** `arena_gb + LOW_RAM_HEADROOM_GB + kv_gb`.
`thresholds.kv_streaming_from` reports this new stock value. **The admitted streamed host floor deliberately keeps
rule (1)**, plus the existing conservative per-card/per-slot session reservation. Streaming with less RAM is not
qualified by this source review. At the existing lane inputs, the PRO slots4 KV-off plan, 5090 262K KV-off plan
(with the separate KV-grow pin), 5090 131K plan and pair roles/split-24 plan keep their v0.2.9 setup args, engine
flags, config keys, host floors, model files/URL, stock tips and notes. Older tags retain their earlier paths.

Changed statements outside the executed planning span do not gain an admission: argparse's `model_alias`,
`--prepare-pack` and `--drafter`; the `prepare_pack` early return; `a.check` display text; the Strix `gpu_fit` advice;
`mmproj_beside`; the MTP/DFlash2 vocab download branch and `refresh_dflash2_vocab`. `kv_streaming_wanted` is also
outside the span and is not loaded. The changed runtime/start/path helpers (`download`, `verify_sha256`, `done`,
`mark`, `ready_verified`, `run`, `_start`, `control_engine_step`, `install_own_path`, `own_path_context`,
`refresh_shared_draft_vocab`) are not planner execution primitives.

### Runtime IO review for staged installs

The stock installer still skips downloads for omp-strata's staged inputs; **no install correction is required**:

| Input / helper | Reviewed v0.2.10 behavior |
|---|---|
| Staged component and `--prebuilt` | [`get_prebuilt:5515-5537`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L5515-L5537) accepts the already staged `BUILD.json`/executable, supported CUDA architectures and version before any download/HEAD path. The local `--prebuilt` folder is not a latest-release lookup. |
| Verified `--gguf-dir` | The download loop is under [`elif not a.gguf_dir`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10475-L10514); local shards get structural checks and any stock hash check. [`verify_sha256:3324-3371`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3324-L3371) reads `mark_text`, hashes locally when needed and has no repair download for `own=True`. omp-strata verifies its own exact pins first. |
| Pinned MTP `rt/experts.bin` | The [fetch/rebuild arm](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10568-L10593) is entered only if the staged layer is missing or corrupt. [`mtp_corrupt:7739-7747`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L7739-L7747) runs the local tensor verifier, not a fetch; the revision-pinned install has already verified and packed those tensors. Vocabulary refresh is local; a fresh MTP root has no DFlash2 copy to refresh. |
| llama.cpp archive marker | [`get_llama_cpp:3615-3653`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3615-L3653) returns an extracted tree or calls `download` for its staged zip. [`download:3106-3122`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3106-L3122) still returns when the file exists and `done` is true. [`done`/`mark_text`/`mark`:1071-1116](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L1071-L1116) accept a readable finish mark, not a required SHA payload. Install's existing text marker therefore remains valid; it need not be rewritten with stock `mark()`. |
| Ready packs and subprocesses | [`ready_verified:3423-3428`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3423-L3428) does require `sha256 <hash>` in the mark, but our GSQ lanes are not ready-pack installs and llama.cpp does not use it. [`run:1020-1042`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L1020-L1042) gates install/build work through acquisition policy; its GGUF-Python fallback finds the staged llama.cpp tree. Runtime wheels are installed first; component setup keeps `PIP_NO_INDEX=1`, scrubbed environment, redirected settings and `--no-start`. |

This is a review of the staged-input paths, not permission to run unguarded setup or a claim that stock never
downloads with missing inputs. All input verification and generated-config checks remain mandatory.

## Strata v0.2.9 setup review (component engine)

Stable [`v0.2.9`](https://github.com/Niko1221/Strata/releases/tag/v0.2.9), GitHub release **429790797**,
published **2026-10-31T08:02:32Z**: annotated object `d94bac6aa33065f5e6a65cca111846627599e318`,
peel `c62d5e3a15b40ea51c96aae9e8d36928965f53ab`. Compared with stock v0.2.8
(`870aedd9e1ebe1c91f94da93b59af17729f6c5c0`). App **0.2.9** ships Windows CUDA 13 engine **0.1.55**:
`strata-engine-0.1.55-windows-x86_64-cuda-cuda13.tar.gz` (621,585,315 bytes), SHA-256
`34f399a0a22e4af8b434439de04dcce3734ccba7e884ef6003439ba148d667df` (matches the release's `SHA256SUMS.txt`);
`engine-component.json` SHA-256 `84271f6e1ca94bf39ac9c22b64a9bde71aadc67fb3482e5d240d515e9158b98d`;
build `99866a47a2b8+cuda13.0`, BUILD source `f-029-rel`, native SASS for `sm_75`, `sm_86`, `sm_89` and `sm_120`
plus `compute_120` PTX. The BUILD commit resolves upstream as an ancestor of the tag (25 commits earlier; two lines
of engine source differ). Archive members were inspected without executing a binary; component-signature verification
is not claimed and native startup observations remain required.

### Reviewed planning and dependency delta

The unmodified report refused `new call in stock setup planning; review required` on every lane: the multi-GPU
config block (`setup.py:10341-10372`) gains stock's opt-in replica-profile statement (`getattr`, the
`STRATA_REPLICA_PROFILE` environment opt-in, an import inside `try`), and its HIP four-card guard now also reads
`replica_done`. Admit only this block, not new general `pure_exec` calls, attributes or builtins:

| Reviewed entry | Full-field AST SHA-256 | Decision |
|---|---|---|
| Multi-GPU config block | `15158c364e8f4ac9187525f1bd588c6938ab17cabdf00a713e1fe7518843f6a4` | Preserve the existing roles/config projection; slice off the last two sub-statements; execute only `replica_done = False` with the rest. |
| Replica-profile sub-statement | `9f989b6940d30d3ddc3f93018ed51e8df9117855518a62b48926020b799b4ccf` | Covered by the whole-block pin. Its guard must be false for the planned args (`replicas=None`, `replica_profile=False`: `install.setup_argv` passes neither `--replicas` nor `--replica-profile`, whose stock default is false, `setup.py:9199`) and for install's own scrub (`install.scrubbed_env`) of a shell that exports the opt-in; the planner never reads its own environment. The body is never validated or executed. |
| HIP four-card sub-statement | `71c4fe304c6e34a87b85781e37711933cf412711ee9e4a623d2919d40ae1a25a` | Covered by the whole-block pin; evaluated with `replica_done = False` (the only value a false replica guard leaves) and must be false. Edited, reachable or moved replica/HIP code refuses. |

On the two-card lanes the replica profile would otherwise apply (two NVIDIA cards, Qwen3.8 IQ3_S, 127.7 GiB RAM): the
manual split-24 pair is outside the guard by its args, and the automatic-split pair only because the opt-in is never
passed and install strips every `STRATA_*` variable. The source-faithful `strata_0_2_9_plan.py` fixture keeps
v0.2.8's selection; three retained nodes differ: the multi block, `HF_REVISIONS` (only
`unsloth/DeepSeek-V4.1-Flash-1017-GGUF` moves, `f924b94` to `8a6ec9c`; the Qwen IQ3_S, Coder and MTP revisions are
unchanged, so installed shards are reused) and `choose_gpus` (an advisory line for a small card left unused, which the
planner does not execute). Five-plan comparisons preserve explicit flags, generated keys, model files, thresholds, host
floors, slots and roles.

`requirements.txt`, `requirements-monitor.txt`, `tools/calibrate.py`, `strata_control/user_args.py`,
`tools/mtp_fetch.py`, `PY_PACKAGES`, `CUDA_WHEELS` and `LLAMA_CPP_COMMIT` are unchanged; drafts reuse
`locks/strata-python-cp313-win_amd64-strata0.2.7.txt` with no new `--python-lock`. Config keys and the other reviewed
constants are unchanged.

### Stock defaults and lane applicability

| Stock engine 0.1.55 / server change | Applicability and fresh-observation boundary |
|---|---|
| Nine-switch parallel-slot stack (`STRATA_CKPT_POOL` and eight more) | Set by stock `serve/server.py` only on Linux with CUDA and two or more slots ("Windows none at all"); not set automatically on Windows, and inherited `STRATA_*` remains scrubbed. Pinned via `strata.engine_env` (`parallel_stack`) on the PRO `v0.2.10` current profile (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0`) and its `v0.2.9` rollback (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0`, alongside `gdn_stack` and `--kv-streaming off`; [Stock engine environment](#stock-engine-environment-v029--0155), [2026-11-02 tuning measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150): `w2` 1,000/128 output +11.3% at `c=1`, +29.3% at `c=2` and +34.8% at `c=4`, `4 × 32K` +13.1%, greedy output byte-identical to the `v0.2.9` base profile, which writes no config `env`). |
| GDN tensor-core prompt kernels (`STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2`) | Linux-only server defaults; compiled into the Windows engine (cc 8.0+ with 48+ SMs, so all four cards can run them). Pinned via `strata.engine_env` (`gdn_stack`) on the PRO `v0.2.10` current and `v0.2.9` rollback profiles, the RTX 5090 262K `v0.2.10` default and `v0.2.9` rollback (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0`, alongside `--kv-streaming off` and `--kv-grow`: cold TTFT −8.6% at 32K and −8.9% at 100K, 100K decode `0.973`, `w1` +2.5% and `w3` 32K +8.4%), and the pair `v0.2.10` `df2` current, `v0.2.10` `pw2` `env86g` rollback and `v0.2.9` `env86g` profiles (alongside `sm86_table`); off on the `v0.2.9` base profiles and the RTX 5090 131K alternative. GDN prompt numerics are not bit-exact upstream. |
| SM120 hyper-connection reads gain exact 5-8 token decode kernels | Default on the single-card PRO and RTX 5090 lanes (bit-identical; upstream measured +5% and +2% decode at eight concurrent requests). Off on the pair, whose v3 read stays off. |
| Tool-call parser: calls inside fenced or indented code stay text ([Strata#4702](https://github.com/Niko1221/Strata/issues/4702), [#4703](https://github.com/Niko1221/Strata/issues/4703)); tools the conversation already called count as declared on chat completions ([#4663](https://github.com/Niko1221/Strata/issues/4663)) | All lanes. G24 is not like-for-like with v0.2.8: a genuine call that the model indents four spaces after a blank line now ends as text. |
| [Strata#4695](https://github.com/Niko1221/Strata/issues/4695) layer-major expert copy, [#4690](https://github.com/Niko1221/Strata/issues/4690) `[DONE]` hang-up | #4695 needs an unbuffered expert tier (a resident budget), which no profile pins; #4690 is the desktop app's gateway, not the server OMP talks to. |
| New start line for a card whose architecture the engine was not built for (#4662) | Silent here: the build covers `sm_86`, `sm_89` and `sm_120`. |
| [Strata#3313](https://github.com/Niko1221/Strata/issues/3313) | Still open: the `sm_86` table is skipped by default on the mixed `sm_86` + `sm_89` pair. In three paired cold starts on the `v0.2.9` pair variant (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`, pinning `sm86_table` + `gdn_stack` in `strata.engine_env`), cold decode rose +6.5% at 8K and +11.4% at 100K and every TTFT bar passed (`0.948–0.996`), while `w1` 512/512 single-request output rose +3.9% (`1.039` vs the pre-registered `>= 1.05` bar); the owner overrode that one bar on 2026-11-02, the requalification chain on 2026-11-03 at `d0a1254` passed all 14 measured gates (`21 pass, 3 not applicable`), and the `sm86_table` + `gdn_stack` pin is carried forward on the current `v0.2.10` `df2` DFlash2 profile and its `v0.2.10` `pw2` `env86g` MTP rollback ([MEASUREMENTS.md](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150), [DECISION.md](DECISION.md)). |

The engine and server start lines the lifecycle checks parse (batch-MTP on/off, `--pipeline-windows`, PLE direct
probe, residency choice) are byte-identical to v0.2.8. The real-source GET/POST/OPTIONS census has no route change,
no lost route and no unclassified route; G13's matrix is unchanged. The environment-name census adds 34 names,
including `STRATA_REPLICA_PROFILE`, `STRATA_COALESCE_PREFILL`, `STRATA_GR_R2` and the GDN tensor-core tuning names;
none is granted as a profile override, and inherited `STRATA_*` remains scrubbed.

**Engine 0.1.55's stage order is admitted to `lifecycle.STAGE_ORDER_REVIEWED_ENGINES`** (`8002c77`). Host-free
full-field AST comparisons show `gpu_list`, `layer_split_value`, `layer_split_of`, `ordered_gpus`, `engine_args`,
`parallel_args` and `parse_engine_stage_line` identical to v0.2.8, while `child_env` adds only the Linux-gated
`parallel_stack_env` and `gdn_stack_env` calls. In the 2026-11-02 pair measurement window, all six version A/B starts
(three `v0.2.8`, three `v0.2.9`) parsed complete with the reviewed parsers: RTX 3090 first, RTX 4090 last, layers
0–23 / 24–47 at pinned manual split 24 (expert caches 19.15 / 17.76 GiB under `--trim-stage-weights`;
[MEASUREMENTS.md](MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150)).

## Stock engine environment (v0.2.10 / 0.1.56)

Engine **0.1.56** joins **0.1.55** in the exact engine-environment review set; no group or value changes.
At app commit `ffa80d73133ea5c548aefe57889a16e8085a938f`,
[`serve/server.py:3979-3983`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L3979-L3983)
(`PARALLEL_STACK_ENV`) and
[`4031`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L4031)
(`GDN_STACK_CUDA`) are byte-identical to the v0.2.9 declarations at lines 3675–3679 and 3724.
The engine-side sm_86 table in
[`src/core/nv_defaults.cpp:26-40`](https://github.com/Niko1221/Strata/blob/06698c674/src/core/nv_defaults.cpp#L26-L40)
at the Windows component's build commit **`06698c674`**, not merely the app tag, is byte-identical to the
0.1.55 review at **`99866a47a2b8`**. The complete file is not byte-identical; this claim is about the reviewed
sm_86 branch only. Config-env delivery still precedes the Linux-only default groups.

The all-experts-resident no-slot-loan decision belongs to the engine, not these groups;
`STRATA_AUTO_NOBORROW` remains unpinned
([no-loan decision](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7810-L7834)).
**Correction:** engine 0.1.56's FP16 weight cache is off by default unless its explicit switch is set
([zero-budget default](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/src/prefill/gemm.cu#L1411-L1422));
`STRATA_PF_W16_CACHE_MIB` remains unpinned. The earlier wording must not be read as an enabled cache default.
Cache sizes and cold-start readiness need fresh host evidence. This source admission does not admit engine
0.1.56's multi-GPU stage order or qualify any profile.

**Engine 0.1.56's stage order is admitted to `lifecycle.STAGE_ORDER_REVIEWED_ENGINES`** (`7b338d9`). Host-free
full-field AST comparisons show `gpu_list`, `layer_split_value`, `layer_split_of`, `ordered_gpus`, `child_env` and
`parse_engine_stage_line` identical to v0.2.9, while `engine_args` applies stock `drafting` and `vram_fit` at every
start (leaving a layer split's argv unchanged: `fit_start` returns early on a split, and `--pipeline-windows` keeps the
MTP on `pw2` while `strata.drafting: "dflash2"` selects DFlash2 alone on `df2`), and the stage, layer-split,
dense-weight and expert-cache message formats are identical between engine builds `99866a47a2b8` and `06698c674`. In the
2026-11-03 pair measurement window, the `env86g` stage-order measurement start and all six version A/B starts plus all
six `df2` vs `pw2` A/B starts parsed complete with the reviewed parsers: RTX 3090 first, RTX 4090 last, layers 0–23 /
24–47 at pinned manual split 24 (expert caches 19.41 / 18.31 GiB on `df2` and 19.14 / 17.75 GiB on `pw2` under
`--trim-stage-weights`; [MEASUREMENTS.md](MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160)).

### Versioned server start-path review

`SERVER_PINNED_PATH_0_2_9` remains valid for v0.2.9. The v0.2.10 review recomputes the full same-module closure from
`child_env`, `engine_args`, `parallel_stack_platform` and **`mtp_retry_args`**, including `drafting_vram_mib`.
The top-level imports binding `draft_layer`, `drafting` and `vram_fit`
([server:76-78](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L76-L78))
have reviewed AST digest `b3a207845da9c931bf60dd9eac96b393134c22152a205b06ac5a713b4a6e7d86`.
The whole cross-module ASTs, read with `git show` at the candidate's immutable Strata commit, are:

| Module | `reviewed_hash` (full-field AST SHA-256) |
|---|---|
| `strata_control/drafting.py` | `4f717a60bf5eb72eb219024c1d4c7acddc2d499bcfcf142e32de54d28a4279fd` |
| `strata_control/vram_fit.py` | `01d6a4d92288fb92bee16ec19c94905328072251028ef02c190de3e374dc6ae2` |
| `strata_control/draft_layer.py` | `2dc95f87df38f38700273dfc67a1cdc9a01a9001048d701069d3b050528e8d17` |

Drafts and **candidate-only reports for every engine >=0.1.56** require this review, even without `engine_env`
(notably the 5090 131K lane). Older engines retain the `if groups:` boundary. Generic news reports select no engine
and remain source-delta checklists. The review returns its matched version key; unknown closures, import bindings,
missing module digests or changed modules refuse.

An exhaustive `alias.attr(...)` census also records the existing leaves: `user_args` (separately digest-reviewed),
`gpu_roles` (topology), `engine_component` (hardware/reference probes), and local `dsv41_flags` (the unreachable
DeepSeek compatibility probe). `gpu_roles.py`, `user_args.py` and `draft_layer.py` are byte-identical to v0.2.9.
`engine_component.py` adds DeepSeek version handling, backend aliases/saved backend and HIP PCI architecture
discovery; our MTP outcome is independent of backend detection. The changed `parallel_args`
([server:3581-3626](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L3581-L3626))
has split-engine/DeepSeek branches guarded by `split_engine_note` and `arch`, both refused by generated-config
verification. `hip_gpu_archs`/`hip_speed_scores` only change file-handle closing on the unselected HIP path.
These leaves do not expand the three-module pin or runtime source list.

### Stock Auto drafting and fit at the reviewed lane inputs

[`engine_args:3492-3565`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L3492-L3565)
now calls `drafting.apply` and `vram_fit.fit_start` on every start. No `strata.drafting` pin is added here.

| Lane | Source-read Auto result | Fit evidence / boundary |
|---|---|---|
| PRO IQ3_S, four slots + batch-MTP | MTP: `slots > 1` is blocked by [`drafting.blocked_by:534-541`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/drafting.py#L534-L541). On a detected capable backend, the stock note is `Drafting: MTP (DFlash2 isn't available in this mode)`; failed/unsupported detection keeps MTP without the note. | The recorded private host-free `probe_fit_start.py` result at 97,887 MiB VRAM leaves args unchanged and no fit note; stock estimated slack **71,624 MiB**, need **732 MiB**. Its 97,000 and 95,000 MiB probes also leave args unchanged. |
| 5090 Coder IQ1_M, 262K + KV-grow and 131K | MTP with no note: the Coder model name fails [`supported_model:251-258`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/drafting.py#L251-L258), so [`apply:795-801`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/drafting.py#L795-L801) returns before touching args. | Recorded probe at 32,607 MiB: 262K slack **21,297 MiB** (need **66 MiB**), 131K slack **24,287 MiB**, unchanged args/no note. The lower-memory probes in that script also remain unchanged. |
| RTX 3090 + RTX 4090 pair, roles/split 24 + pipeline windows | MTP: `--pipeline-windows` is blocked by the same stock guard; capable detection may print the same one-line MTP reason as the PRO. | [`fit_start:286-289`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/vram_fit.py#L286-L289) returns unchanged for a layer split. |
| Studio → PRO route | The server's PRO outcome above; no second engine decision on the client. | Requires its own route/fan-out evidence after server qualification. |

The fit script is a host-free estimate at stated inputs, **not measured GPU headroom, a start sandbox, or a
qualification result**. No `stock_module_sandbox`, `stock_start_review` or install-flag refactor is introduced.
On the host, every >=0.1.56 install identity hashes the **bytes** of `serve/server.py` and the three modules above;
every start rechecks them and captures both new log intervals, including the no-env 131K lane.

`_check_drafting` permits no note or at most one stock `Drafting: MTP (<reason>)` from the reviewed reason set.
It refuses DFlash2 chosen/on, drafting off, `"mtp": false`, **`DFlash2 didn't start`**, and unknown/repeated notes
in either output stream; `run.json` records the MTP result and both intervals. The five start-time flags
`--draft`, `--draft-model`, `--draft-fallback`, `--draft-conf`, `--mtp-draft-vocab` are forbidden in new drafts and
refused in every profile's expected config flags. A later explicit DFlash2 variant is a separate admission.

`_check_start_fallbacks` refuses these verbatim stock diagnostic fragments in either start interval:

| Diagnostic | Immutable source |
|---|---|
| `short of GPU memory: more is read from RAM and the SSD, expect it to be slower` | [`vram_fit.py:91`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/vram_fit.py#L91) (`NOTE_SLOW`) |
| `strata generate: not enough RAM for the expert arena (` | [`generate.cpp:7323-7325`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7323-L7325), [#4846](https://github.com/Niko1221/Strata/issues/4846) |
| `this start runs without the draft layer (decode is slower; STRATA_MTP_KEEP=1 keeps it)` | [`generate.cpp:6736-6737`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L6736-L6737) |
| `prompts are read in smaller chunks, expect them to be slower` | [`generate.cpp:7609-7610`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7609-L7610), 16-slot cache loan |
| `strata generate: short of GPU memory: the cache had no room, so the output head (` | [`generate.cpp:7699-7700`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7699-L7700), pinned-host head/PCIe read |

Both checks run before start returns healthy and use existing failure teardown. Earlier engines do not gain
these checks. KV-off lanes separately refuse any start-time streaming line. The engine's reply-only penalty
window ([#4590](https://github.com/Niko1221/Strata/issues/4590),
[`generate.cpp:17180-17187`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L17180-L17187))
and inherited Windows IO-priority repair/report
([#4733](https://github.com/Niko1221/Strata/issues/4733),
[`io_priority.cpp:19-43`](https://github.com/Niko1221/Strata/blob/06698c674/src/platform/io_priority.cpp#L19-L43))
remain stock behavior, not profile switches.

## Stock engine environment (v0.2.9 / 0.1.55)

The tuning admission is opt-in, not a change to the qualified baseline's defaults. `strata.engine_env`
must be an exact union of complete reviewed groups of stock-owned **string** values; partial groups, extra
names, other values and raw `strata.env` / `setup_args.env` are refused. The exact reviewed engine set is
`{"0.1.55"}`; the archive pin above binds the engine bytes. A future engine needs a new source review, even
if its server path is unchanged.

| Group | Verbatim stock values | Admission |
|---|---|---|
| `parallel_stack` | `STRATA_CKPT_POOL=1`, `STRATA_CKPT_POOL_READY=4`, `STRATA_SLOT_CKPT_MOVE=1`, `STRATA_SLOT_COPY_DIRECT=1`, `STRATA_SLOT_COPY_BATCHSYNC=1`, `STRATA_BATCH_GDN_GROUPS=1`, `STRATA_BATCH_ATTN_ROWS=1`, `STRATA_BATCH_SELF_COMMIT=1`, `STRATA_QSA_SLOTS=1` | Stock server `PARALLEL_STACK_ENV`; requires at least two batch slots, like stock's gate. |
| `gdn_stack` | `STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2` | Stock server `GDN_STACK_CUDA`; the reviewed cards meet the engine's CUDA capability threshold. GDN prompt numerics are not claimed bit-exact. |
| `sm86_table` | `STRATA_ADAPT_NOWAIT=1`, `STRATA_ADAPT_LAG=2`, `STRATA_CPU_IQ_ALL_EXACT1=1`, `STRATA_SIDE_MIXER=2`, `STRATA_ATTN_DAILY=1`, `STRATA_GR_UP75=1`, `STRATA_GU_SWIGLU=1`, `STRATA_QSA_ROWS=1`, `STRATA_B6_MMVQ_ROWS=1` | Only a mixed-architecture multi-GPU profile containing an sm_86 card. |

The two server dictionaries are literal constants at
[`c62d5e3a:serve/server.py`](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/serve/server.py).
Stock `child_env` copies config `env` **before** the Linux-only stacks call `setdefault`.
`parallel_stack_platform()` is `sys.platform.startswith("linux")`: pinning those same values in a Windows
config enables them explicitly without changing stock sources or passing an inherited process knob.
Drafting compares each requested server-owned group against its literal dictionary and pins the complete
same-module call closure of `child_env` and `engine_args`, including the platform gate (32 functions).
Functions must occur exactly once, the transitive callee set must be unchanged, and every full-field AST
SHA-256 must match `SERVER_PINNED_PATH_0_2_9` in
[`scripts/upstream_watch.py`](../scripts/upstream_watch.py). The source-faithful excerpt is
[`strata_0_2_9_server_engine_path.py`](../tests/fixtures/strata_0_2_9_server_engine_path.py).

| Delivery-path root or gate | Full-field AST SHA-256 |
|---|---|
| `child_env` | `cfd3f69fa243301085281c8d240b78c42c3d3fa72c9e76e304a747478d2b34d1` |
| `engine_args` | `be1a65fa9475e9c6c0751f79735ef71e5ac5e09c607cfc61069923c3c41c8c1d` |
| `parallel_stack_platform` | `1ba6b721cc5fbeb72dd35732b0dac0f1e29aeb0902a37e4daae482625ac16328` |
| `parallel_stack_env` | `0a5f58bdd13071dc45b2a89cf798b2670b2196d2f87d0d95ac6c17cfef65a81d` |
| `gdn_stack_env` | `288a6edfb2a15442aa8620d57e65057587ac6141c18548937e0b0d21fd627ea2` |

At the Windows engine build commit `99866a47a2b8`, the sm_86 values live in
[`src/core/nv_defaults.cpp`](https://github.com/Niko1221/Strata/blob/99866a47a2b8/src/core/nv_defaults.cpp#L26-L40),
not in `generate.cpp`. The caller at
[`src/program/generate.cpp:3445-3461`](https://github.com/Niko1221/Strata/blob/99866a47a2b8/src/program/generate.cpp#L3445-L3461)
applies them only when every visible CUDA device has the same compute capability. This is the skipped
mixed sm_86/sm_89 case in [Strata#3313](https://github.com/Niko1221/Strata/issues/3313); pinning the table
also delivers its process-wide switches to the other card, so host A/B and greedy-identity evidence remain
required before qualification.

Install writes the pin with stock `setup.write_config` and refuses any existing config `env` rather than
merging it. `verify_generated` requires exact equality and refuses config `env` without a pin.
Env-pinned runtime identity additionally hashes `serve/server.py`; every start rehashes it and the config.
After ready, the config is read again and `run.json` records the canonical env SHA-256, sorted names,
server-source SHA-256 and this launch's engine-log interval. When self-commit is pinned, every batch-window
line must end `, one-row windows keep their rows`, and at least one must exist. Other groups have no invented
positive startup line. Process-environment inspection through undocumented Windows PEB structures is not
used: reviewed stock delivery, config identity and real engine evidence are the boundary.

The accompanying single-card setup pin is exactly `setup_args.kv_streaming: "off"` (engine 0.1.55+).
Stock setup spells it `--kv-streaming off`, with choices `auto`, `on`, `off`. The paired planner requires
off to differ from auto only by removing the `--kv-resident` pair; generated config keys, stock tips, model
files and URL must agree, and stock warnings still refuse. Install and every start refuse the streaming flag
or its `strata generate: KV streaming:` startup line. No positive non-streaming KV line was observed.
Newly adding off may replace setup-derived streamed-KV RAM floors with stock's non-streaming calculation:
the RTX 5090 131K and 262K plans both compute 34 GiB. A predecessor floor above the matching auto plan
(after the same tips) is operationally raised and is never lowered; driver and disk floors always keep max.
The floor derivation is recorded in the draft profile and report.

`strata.kv_grow: true` is a valueless, exactly-once `--kv-grow` pin, only on one card alongside KV streaming
off, on engine 0.1.55+. Startup must show the reviewed `strata generate: elastic K/V: ... as the context grows`
line from this launch, recorded in `run.json`. Neither pin changes the engine's batch-row kernels.
Drafts carry these decisions forward; `--ple-io stock` is the explicit exception that drops a carried direct-read
pin and stores no `stock` value. It refuses when there is nothing to drop and leaves the model block unchanged,
so an NVFP4 candidate can re-prove its existing prepared conversion rather than convert again.

## Stock OMP 18.17.0 and 18.18.0 surface

This review covers [18.17.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.17.0) and
[18.18.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.0) relative to 18.16.0.
The new tuple pins **18.18.0**, lightweight tag at **`b5a6b2f7e5b6606b6562e678ead83f21738f34a0`**.
Published [`SHA256SUMS.txt`](https://github.com/can1357/oh-my-pi/releases/download/v18.18.0/SHA256SUMS.txt)
and release inventory identify:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `omp-windows-x64.exe` | 248,622,592 | `20267b4914dca40306c71e824216e0f79061869d9e9d4780fc0c255b7a3e5339` |
| `omp-darwin-arm64` | 220,479,632 | `0adae2a341a1e6840b00c96ce0b1c9d2e0257b1ea6782e4302e17b717a6ffb0a` |
| `omp-linux-x64` | 284,657,840 | `ec271e0d7df4c0f57acb6a7a28f8585d46bd050bcef8494f6d33db8a6c0dfbba` |

- **Pinned-client update policy:** 18.17.0 introduces opt-in background `update.auto` and setup wizard version 3's
  update scene. Every config writer uses the shared renderer, now emitting `update: {auto: false}` and
  `startup: {checkUpdate: false, setupWizard: false}`. This covers local launch, client routes, comparison adapters
  and both task-set evaluator paths without a second settings convention
  ([settings](https://github.com/can1357/oh-my-pi/blob/b5a6b2f7e5b6606b6562e678ead83f21738f34a0/packages/coding-agent/src/modes/settings.ts#L1271-L1321),
  [startup](https://github.com/can1357/oh-my-pi/blob/b5a6b2f7e5b6606b6562e678ead83f21738f34a0/packages/coding-agent/src/main.ts#L693-L716)).
  Older rollback clients lack `update.auto` and ignore that explicit off pin; their existing startup guards remain.
- **Discarded usage is not an auxiliary call:** discarded assistant turns are journaled as `model_usage` with
  purpose `discarded-turn` ([change](https://github.com/can1357/oh-my-pi/commit/3aefaff113)).
  G18 excludes precisely that purpose from `auxiliary_calls`, retaining ordinary/legacy auxiliary entries.
  `transcript.summarize` intentionally continues counting the billed usage; usage totals therefore have a different
  boundary from 18.16.0.
- **No Strata wire shim:** the OpenAI Chat Completions change is an opt-in Factory Droid timeout-header setting,
  not our provider path. Local compatibility resolution, reasoning replay, token counting, output fitting,
  compaction thresholds/method order and HTTP attempt policy are unchanged. Keep the existing G17/G18/G18L bars
  and observe the actual counts/methods rather than treating source admission as a gate pass.
- **Tool comparability:** 18.17.0 replaces the bash engine with Bash 5.3 semantics, changes Windows executable
  lookup/output and saves execution traces; 18.18.0 includes related crash fixes. `wait` now returns on a
  5/10/30/60/300-second idle ladder. G24 tool outcomes and fleet/G23 request/tool counts are not directly comparable
  with 18.16.0
  ([18.17.0 notes](https://github.com/can1357/oh-my-pi/releases/tag/v18.17.0),
  [wait](https://github.com/can1357/oh-my-pi/blob/b5a6b2f7e5b6606b6562e678ead83f21738f34a0/packages/coding-agent/src/tools/wait.ts#L31-L36)).
- **Worker and egress boundaries:** worker threads begin at nine concurrent subagents, so G23's four scouts do
  not reach that path. Spotlight is off by default and its environment override is scrubbed. `ovnfs`, however,
  activates when its binary is on PATH: host-window preflight must establish its absence rather than assuming
  unchanged prompt/tool behavior
  ([worker threshold](https://github.com/can1357/oh-my-pi/blob/b5a6b2f7e5b6606b6562e678ead83f21738f34a0/packages/coding-agent/src/thread/subagent-worker.ts#L14-L17),
  [ovnfs discovery](https://github.com/can1357/oh-my-pi/blob/b5a6b2f7e5b6606b6562e678ead83f21738f34a0/packages/coding-agent/src/task/settings.ts#L40-L59)).
  `display.shellVisualization` and `spotlight` settings are UI/defaults only and remain unpinned; 18.17.0's CLI display
  flags (`--spinner-interval`, `--max-fps`, `--motion`) are reviewed in the launcher policy (`243290e`).

Qualified on 2026-11-07–08 (`916f1d9`, CI matrix `50d00a1`;
[decision](DECISION.md), [measurements](MEASUREMENTS.md)), with `ovnfs` verified absent on every lane in host preflight
and G24 scoring `15/18` across all six qualified server chains (against `17/18` on the `v0.2.11` RTX 5090 262K chain;
OMP `18.17` changed the wait ladder and prompt text, so G24 is not comparable across OMP versions): on the PRO,
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` (current, rolling back
to its `v0.2.11` + OMP `18.16.0` `df2` predecessor) and the tuned-pack alternate
`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`; on the RTX 5090,
the 262K default `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0` (rolling back to its
`v0.2.11` + OMP `18.16.0` predecessor) and the 131K alternative `win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0`
(passing G15, which had failed twice on `v0.2.11`, and rolling back to its `v0.2.10` + OMP `18.16.0` predecessor); on
the pair, `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`
(current, pinning `select_two_pass` alongside `sm86_table` + `gdn_stack`) rolling back to its qualified `v0.2.12`
`env86g` base profile
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`;
and on the Mac Studio client, `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0` (current,
rolling back to its `v0.2.11` + OMP `18.16.0` `df2` route) and the tuned-pack alternate route
`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`.
[`releases/campaigns/v0.2.12.json`](../releases/campaigns/v0.2.12.json) is complete across all five `hosts[]` entries;
no default-runtime switch against NInfer follows.

## Stock OMP 18.16.0 surface

The reviewed target [`v18.16.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.16.0) pins
**`650f3a108229ee11bf68ba3377f4e8c3391cd424`**. Relative to v18.15.0, this needs **pin + documentation changes
only**, not a provider/config/transcript/gate shim. Published
[`SHA256SUMS.txt`](https://github.com/can1357/oh-my-pi/releases/download/v18.16.0/SHA256SUMS.txt) lists:

| Asset | Bytes (release inventory) | SHA-256 |
|---|---:|---|
| `omp-windows-x64.exe` | 243,591,168 | `c249a9ed0a57c748fb1247d8ee9e2d0fe1b13229266ce74d8810a76a591e21fc` |
| `omp-darwin-arm64` | 215,642,256 | `d4a10d97488d6054d2b18198bd24f461079952c7e0fb75ba66336ca0df0cb99e` |
| `omp-linux-x64` | 277,002,416 | `6498ed785bab00d2926e0387e0ec02362d6d45f1c3d0d1b57c1618b7f95c9264` |

The stock `openai-completions.ts`, `utils/openai-http.ts` and CLI flag table are byte-identical to v18.15.0.
The emitted settings and compatibility keys, JSONL conversation/compaction fields, RPC events and task routing
remain compatible. Memory still defaults to
[`off`](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/memory-backend/settings.ts#L11-L17);
no new memory setting or default egress is enabled by this admission.

Token counting now always uses the native family tokenizer, falling back to `o200k_base` for unclassified ids
([tokenizer:86-94,283-285](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/agent/src/tokenizer.ts#L86-L94)).
Our `qwen3.8-...` ids still classify through
[`qwen.kdl`](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/compat/rules/taxonomy/qwen.kdl#L1-L13)
and resolve to
[`qwen3`](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/model-tokenizer.ts#L27-L29),
as before. Do not infer gate results from that compatibility:

- **G13/G18/G18L:** keep the existing thresholds and method order, but record the actual method and every
  `tokensBefore`; handoff remains first for text-only models. G18L must still observe its >100,000-token bar.
- **G17:** retain >=100,000 peak prompt tokens with no compaction during the near-limit turn; classification is
  not a replacement for observing that boundary.
- **G19:** [journaled date/cwd reminders](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/session/date-cwd-reminder.ts#L4-L14)
  now replay their original placement on resume/revive, so prompt bytes and cache coverage can differ across days.
- **G23:** subagent `session_init.mountedTools` and revive/mount handling are additive. Re-prove every scout's
  completed delivery over the Studio → PRO route; the existing fan-out marker is unchanged.
- **G24 is not comparable to 18.15.0:** read paging/cut-byte accounting, write's truncated-projection/held-SQLite
  refusals, bash's `minimized` record and null/payload normalization change tool behavior or output.
- **G04:** the HTTP transport is unchanged; the existing HTTP-500 fault test still owns its twelve-request proof,
  rather than a new retry rule in the integration.

Qualified on 2026-11-03
([2026-11-03 decision](DECISION.md#update-2026-11-03-strata-v0210-with-omp-18160-qualifies-on-every-host-and-the-studio-route),
[2026-11-03 windows measurements](MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160)): on the PRO,
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0` (current, pinning
`strata.batch_mtp: true`, `--batch-mtp`, `strata.ple_io: "direct"`, `--ple-io direct`, `setup_args.kv_streaming: "off"`,
`--kv-streaming off`, and `strata.engine_env` `parallel_stack` + `gdn_stack`, qualified under the owner's override of its
concurrent short-prompt TTFT A/B miss), rolling back to its `v0.2.9` `kvvram-envpg` predecessor
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0` (`v0.2.9` base and
`v0.2.8` profiles move to earlier qualified history; the comparison-only `v0.2.9` `UD-IQ4_XS` and `NVFP4-QAD` model
candidate drafts and their Studio routes stay drafts); on the RTX 5090,
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` (current default, pinning
`setup_args.kv_streaming: "off"`, `--kv-streaming off`, `strata.kv_grow: true`, `--kv-grow`, and `strata.engine_env`
`gdn_stack`, requiring Docker Desktop and WSL stopped on the host), rolling back to its `v0.2.9` `kvvram-kvgrow-envg`
predecessor `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0` (`v0.2.9` base and `v0.2.8` 262K
move to earlier qualified history; the unpinned-GDN `v0.2.9` `kvvram-kvgrow` fallback stays an uninstalled draft), and
the 131K alternative `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` (rollback to the `v0.2.10` 262K default, or
rolling back to `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0` on the 131K lane); on the 4090+3090 pair,
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
(current, pinning stock DFlash2 drafting alone via `strata.drafting: "dflash2"` packed offline from pinned
`incoai/Qwen3.8-Flash-Next-DFlash2` files, dropping `--pipeline-windows 2`, alongside manual `layer_split: "24"`,
`strata.trim_stage_weights: true`, `--trim-stage-weights`, `strata.ple_io: "direct"`, `--ple-io direct`, and
`strata.engine_env` `sm86_table` + `gdn_stack`, with 19.41 / 18.31 GiB expert caches, 27.51 GiB G10 commit headroom,
43.1–43.4 s chain restart readiness, G24 17/18 and the 8,192 MiB automatic conversation cache, qualified after meeting
the owner's +3% decode bar at +8.2% to +13.6% and under the owner's override of its 6-token-window inter-event gap and
queued-prefill A/B misses), rolling back to its qualified `v0.2.10` `pw2` `env86g` MTP sibling
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
(19.14 / 17.75 GiB expert caches, 27.54 GiB G10 commit headroom, G16/G20/G21 55.3 / 43.2 / 55.7 s, G24 16/18; `v0.2.9`
`env86g` and `v0.2.9` base move to earlier qualified history); and on the Mac Studio client, the independent Studio→PRO
route `client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0` (current), rolling back to
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0` (`v0.2.9` base and `v0.2.8` routes stay
earlier qualified history).
[`releases/campaigns/v0.2.10.json`](../releases/campaigns/v0.2.10.json) is complete across all five `hosts[]` entries;
no default-runtime switch against NInfer follows.

## Stock OMP 18.15.0 surface

[`v18.15.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.15.0) pins
`3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`, including v18.14.1's and v18.14.2's intervening changes.
Release API digests agree with `SHA256SUMS.txt`:

| Platform asset | Bytes | SHA-256 |
|---|---|---|
| `omp-windows-x64.exe` | 243,250,176 | `978846a816cb77f44a55e32b16493375ca837fbf87e0aec35a9c1c934bff0cd0` |
| `omp-darwin-arm64` | 215,295,120 | `d36dfabf0ee52d6f08efadb59c46f0349545c6f6975522417adae29646e73e34` |
| `omp-linux-x64` | 276,785,328 | `6737ee2415555a3656cc7b89c14d1c25c18658ee4c0fd4f7309705149ccb7b0f` |

**Pin with documentation/draft-note changes, not a launcher or wire adapter change.** The chat-completions provider
only gained exports; its HTTP layer, the CLI flag table, print-mode events, session entry types, the HOME/`--profile`
layout, the apiKey contract and every emitted settings key are unchanged (`task.agentModelOverrides` only moved files).
Qwen3.8 still selects stock `replace` editing (`utils/edit-mode.ts`). Drafts run in API mode because download mode
refuses a changed OMP tag.

Watch on the hosts: [OMP#17499](https://github.com/can1357/oh-my-pi/pull/17499) rejects length-truncated handoff and
compaction summaries (G13 needs a compaction, G18/G18l a compaction entry with more than 100K tokens before);
[OMP#12229](https://github.com/can1357/oh-my-pi/pull/12229) always declares `model` in the task schema and refuses
an unapproved per-call model (G23 fan-out counts only completed results); long tool-call intents now run
([OMP#17486](https://github.com/can1357/oh-my-pi/pull/17486)) and short repeated status lines no longer count as a
thinking loop, so G24 tool-error counts are not comparable with 18.14.0. G04 still expects 12 requests for HTTP 500;
re-observe G15's interrupted-turn stop. None of this substitutes for host gates or promotes a route.

Qualified on 2026-11-02 and 2026-11-03 (now rollbacks to `v0.2.10` + OMP `18.16.0` on the PRO, RTX 5090 262K and 131K,
and Studio route, and earlier qualified history on the pair and the `v0.2.9` base profiles;
[tuning and pair override decision](DECISION.md#update-2026-11-02-evening-the-v029-tuning-profiles-on-the-pro-and-rtx-5090-and-the-studios-tuned-route-qualify),
[morning v0.2.9 decision](DECISION.md#update-2026-11-02-strata-v029-with-omp-18150-qualifies-on-every-host-and-the-studio-route),
[2026-11-02 tuning measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150),
[2026-11-02 windows measurements](MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150)): on the PRO,
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0` (rollback to the
`v0.2.10` PRO profile, pinning `strata.batch_mtp: true`, `--batch-mtp`, `strata.ple_io: "direct"`, `--ple-io direct`,
`setup_args.kv_streaming: "off"`, `--kv-streaming off`, and `strata.engine_env` `parallel_stack` + `gdn_stack`), and the
earlier `v0.2.9` base profile
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0`; on the RTX 5090, the 262K
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0` profile (rollback to the `v0.2.10` 262K
default, pinning `setup_args.kv_streaming: "off"`, `strata.kv_grow: true`, `--kv-grow`, and `strata.engine_env`
`gdn_stack`; 34 GiB start floor, with Docker Desktop and WSL stopped), the earlier `v0.2.9` base profile
`win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0` (36 GiB start floor; the unpinned-GDN fallback
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0` stays an uninstalled draft), and the 131K
alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`, rollback to the `v0.2.10` 131K alternative); on the
pair, `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`
(earlier qualified history behind `v0.2.10` `df2` and `pw2` `env86g`, pinning manual `layer_split: "24"`,
`strata.trim_stage_weights: true`, `--trim-stage-weights`, `strata.ple_io: "direct"`, `--ple-io direct`, and
`strata.engine_env` `sm86_table` + `gdn_stack`, with 19.15 / 17.76 GiB expert caches, 27.77 GiB G10 commit headroom,
43.5–43.9 s chain restart readiness and the 8,192 MiB automatic conversation cache, qualified on 2026-11-03 after the
owner overrode its `w1` 512/512 single-request A/B miss at `1.039` vs `>= 1.05`, alongside its `v0.2.9` base profile
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`); and on
the Mac Studio client, the independent Studio→PRO route
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0` (rollback to the `v0.2.10` route),
alongside the earlier `client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0` base route.
The PRO's `v0.2.9` model candidates
(`win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0` and
`win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0`, plus the earlier `--ple-io direct` NVFP4-QAD
screen draft `win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0` and the two model-candidate
Studio routes) stay comparison-only drafts.
[`releases/campaigns/v0.2.9.json`](../releases/campaigns/v0.2.9.json) is complete across all five `hosts[]` entries;
no default-runtime switch against NInfer follows.

## Strata v0.2.8 setup review (component engine)

Stable [`v0.2.8`](https://github.com/Niko1221/Strata/releases/tag/v0.2.8), GitHub release **428450803**,
published **2026-10-29T22:40:43Z**: annotated object `878ef09cc9092a41a37dac32fd6fe461e47fa326`,
peel `870aedd9e1ebe1c91f94da93b59af17729f6c5c0`. Compared with stock v0.2.7
(`5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`). App **0.2.8** ships Windows CUDA 13 engine **0.1.54**:
`strata-engine-0.1.54-windows-x86_64-cuda-cuda13.tar.gz` (620,425,196 bytes), SHA-256
`bacff012e5f7e44ffefd5a08230363e0e527c8a86abf55ef1b31c833be37b8ab`;
manifest SHA-256 `ecdc65171aa2b3d34dfcb1acff4e20efd78aee1f72b8e5ee3abe4dafe90033d3`;
build `8c1aea4bca1b+cuda13.0`, BUILD source `f-028-rel`, BUILD commit `8c1aea4bca1b`.
Archive/member hashes and BUILD identity were inspected without executing a binary; component-signature
verification is not claimed. The build commit did not resolve in the public upstream review, so the source
review is not a source-to-binary attestation; native startup observations remain required.

### Reviewed planning and dependency delta

The unmodified report/draft refused `new call in stock setup planning; review required`: the args If-chain
now calls `is_gb10`. After that boundary, the multi-GPU config block also gains a HIP-only four-card
`try`/import. Admit only the following exact bodies, not new general `pure_exec` calls, attributes or builtins:

| Reviewed entry | Full-field AST SHA-256 | Decision |
|---|---|---|
| `is_gb10` | `6f0fb0371f2d1a1f6b77af3105df196536cf4a01b498e2f2da35eedf9467f79d` | Run the pinned helper with fixed `is_arm64=False` for the selected `windows-x86_64` asset lane; never inspect the planning machine. |
| Args If-chain containing the GB10 arm | `c363d510549a35b71d9c23d59495111f808259e64d043b35df64acdb4ab8fc03` | Only this statement may call `is_gb10`; the arm is unreachable and cannot add `--mmap-experts`, `--mtp-q4` or `--mtp-hnorm` to these plans. |
| Multi-GPU config block | `778de3208b1749e4ab66129d0878c3c5863544c0b886418cf5e71a2829b905bb` | Preserve the existing roles/config projection; evaluate the appended HIP guard on every lane and require false, without validating or executing its body. |
| Appended HIP sub-statement | `fc3cda7f10606a3e67207c05458d91ccedaa41c394ea0174501154d525325f52` | Covered by the whole-block pin, not independently admitted. Edited/reachable/moved HIP code refuses. |

The source-faithful `strata_0_2_8_plan.py` fixture uses v0.2.7's same selection plus `is_gb10`;
only those two `main()` statements differ. Five-plan comparisons preserve explicit flags, generated keys,
model files, thresholds, host floors, slots and roles. Helper/caller mutations and a new callsite refuse;
planning with an ARM64 Linux planning-machine identity yields the same five plans.

CUDA-12 driver-floor helpers, ARM64/DGX Spark installation, macOS DeepSeek and the packaged-Terminal
`source_version()` fallback are outside the selected Windows CUDA 13 Qwen paths and are not admitted.
`requirements.txt`, `requirements-monitor.txt`, build requirements, `PY_PACKAGES`, `CUDA_WHEELS`,
`LLAMA_CPP_COMMIT`, the runtime-input helpers/caller, user-args stamping and MTP inputs are unchanged.
Drafts reuse `locks/strata-python-cp313-win_amd64-strata0.2.7.txt` (26 hash-locked wheels);
no new `--python-lock` is supplied.

### Stock defaults and lane applicability

| Stock engine 0.1.54 change | Applicability and fresh-observation boundary |
|---|---|
| Tool-call recovery defaults on | All lanes, declared tools only. Stock setup writes no `tool_call_recovery` key and none is pinned. Quoted-tool-syntax handling, missing function closers, lenient non-string JSON arguments and stray closing think-tag repairs are always on, independently of recovery. |
| [Strata#4518](https://github.com/Niko1221/Strata/issues/4518): PLE lock release | Automatic residency still requires table, expert arena and headroom to fit; the policy gives its lock back when it would starve the automatic conversation cache. On the measurement-only pair residency draft on Windows (`rtx3090-win-a`), the policy locked the 26.8 GiB table (33.9–34.0 s), then gave the lock back on both starts and sized the cache at 4,864 MiB (106–112 s to ready), against 8,192 MiB and 61–63 s to ready with `--ple-io direct` (27.9 GiB G10 commit headroom on `roles-pledirect`, 27.8 GiB on the current split-24 trim + PLE-direct profile). The qualified pair profiles keep `--ple-io direct`, so neither automatic residency nor its lock release applies there. |
| [Strata#4420](https://github.com/Niko1221/Strata/issues/4420): richer shared-prefix checkpoints survive slot overwrite | PRO's pinned four batch slots and its remote fan-out; not the slot-free 5090 or pair lanes. Measure reused/cached tokens rather than infer a gain. |
| [Strata#4474](https://github.com/Niko1221/Strata/issues/4474): automatic expert-cache reserve | Every lane leaves about 256 MiB more VRAM free, when the minimum cache still fits; on the pair the changed automatic sizing is stage 0, not the later-stage cache. No reserve override is added. |
| [Strata#4051](https://github.com/Niko1221/Strata/issues/4051): memory-return waits | All restarts may wait up to 20 s for arena RAM; server startup waits up to 120 s only for a recorded leftover/orphan engine. Existing 900 s readiness limits and the 5090 262K 36 GiB startup floor stay unchanged. |
| Residency-biased route prior defaults off | Already off for these 24/32/96-GB NVIDIA cards; the predecessor's small-card default does not apply. |
| HIP 16-row speculative windows | Unreachable; NVIDIA/CUDA remains at 8. No wide-window build or flag is selected. |
| Carried topology defaults | Int8 prompt attention; SM120 wide-up and stream-split hyper-connection reads, with single-card layer-major prefill off. Eligible split prompts retain layer-major prefill and Ada MMVQ row tables. Two-card pipelined batch groups require slots, which the pair keeps off; `--pipeline-windows 2` remains a separate decode pin. |

The real-source GET/POST/OPTIONS census has no route change, no lost route and no unclassified route;
G13's matrix is unchanged. Config keys and reviewed constants are unchanged. The environment-name census adds
`STRATA_ARENA_RAM_WAIT_S`, `STRATA_ATTN_BATCH`, `STRATA_DS4_METAL_CTX`, `STRATA_FOUR_CARD_PROFILE`,
`STRATA_GPU_TRACE`, `STRATA_METAL_NEIGHBOURS`, `STRATA_P4_TIMING`, `STRATA_P4_TRACE`,
`STRATA_PF_TILE_DEBUG`, `STRATA_PIPELINE_DUMP`, `STRATA_SM121_PERF` and `STRATA_VERIFY_PROFILE_EVERY`;
none is granted as a profile override, and inherited `STRATA_*` remains scrubbed.

**Engine 0.1.54's stage order is admitted to `lifecycle.STAGE_ORDER_REVIEWED_ENGINES`** (`4853ab3`). Host-free
full-field AST comparisons show `gpu_list`, `layer_split_value`, `layer_split_of`, `ordered_gpus`, `engine_args` and
`child_env` identical to v0.2.7. `parallel_args` changes a warning only, not returned flags; the stage-order,
layer-boundary and primary-cache message formats are unchanged. The source still parses the pinned `--ple-io direct`,
`--pipeline-windows 2`, `--prefill auto:32768` and `--pool-workers`. In the 2026-10-30 pair measurement window, all
four starts across the PLE-direct candidate and the stock-residency measurement arm parsed complete with the reviewed
parsers: RTX 3090 first, RTX 4090 last, layers 0–23 / 24–47 (auto K=24, expert caches 17.35 / 16.01 GiB;
[MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-stage-order-and-strata4518-on-engine-0154)).

G15/G16 must observe the changed waits; G19/G23 must measure cache behavior. G24 is not like-for-like with
v0.2.7 because recovery and repairs change tool-call outcomes: retain repair/unread-call metrics and new parser
log counts per attempt. [The OMP review](#stock-omp-18140-surface) supplies the other half of this tuple.

## Stock OMP 18.14.0 surface

[`v18.14.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.14.0) pins
`31147f9d1a76608549821c3759f8487b4d66c72d`, including v18.13.3's intervening changes.
Release API digests agree with `SHA256SUMS.txt`:

| Platform asset | Bytes | SHA-256 |
|---|---|---|
| `omp-windows-x64.exe` | 242,797,056 | `620a5935cdb6a9ed52d8b0c93892d6b5bb84155244a98f3be82af0455177bf29` |
| `omp-darwin-arm64` | 214,816,912 | `608843959ab34295d52460dd09dd7d548b6c903c08a83c67954c2d4c36fd1f5a` |
| `omp-linux-x64` | 276,244,656 | `e7dd2b606c4ebe9d1a7bcfad1b8820db968cd6b05409fed1c6bc8db0b6a95a8f` |

**Pin with documentation/draft-note changes, not a launcher or wire adapter change.**
`THIRD-PARTY-NOTICES.txt` is no longer a release asset; the integration pins none of it or the browser-relay zip.
The CLI flag table is identical to v18.13.2. Every emitted setting and model compatibility key remains registered.
**Correction to the earlier private source-review note:** `startup.checkUpdate` is registered
(`modes/settings.ts:1138`); keep the existing emitted key, already exercised by the pinned-binary settings test.

[OMP#16297](https://github.com/can1357/oh-my-pi/pull/16297) requires exact provider-qualified model references.
Our `models.yml` ids, CLI selectors, `modelRoles` and `task.agentModelOverrides` already use the same complete
`strata-local/<served-id>` or `strata-<label>/<served-id>` string, so exact lookup succeeds by construction.
No selector, routing or fallback override changes. Qwen3.8 still selects stock `replace` editing
([OMP#17096](https://github.com/can1357/oh-my-pi/pull/17096)); the draft note now applies to OMP >=18.13.2,
with no edit-mode override pinned.

[OMP#17231](https://github.com/can1357/oh-my-pi/pull/17231)'s reasoning estimate change is a no-op for our
loopback chat-completions providers: they replay their own thinking. Request shape, fitted token limits,
stream finish handling, transcript continuation and compaction defaults are unchanged. Local first-event
timeouts stay disabled; the 300 s idle timeout and two-layer HTTP retry path remain (G04 still expects 12
requests for HTTP 500). Provider loading is now lazy, so a real pinned-binary first request must prove bundling.

`out://` is default-off in print/RPC/ACP and remains unset. Bun's cooperative yield/keepalive workaround was
removed from streaming/tool/task paths; watch client CPU, turn timing and G23 task/wait completion, without
assuming earlier timing or token counts. Bash builtins and tool text changed, not the explicit tool-name set.
Re-observe G15 abort handling after [OMP#17216](https://github.com/can1357/oh-my-pi/pull/17216), G17/G18 long
sessions, G13 per-process egress after lazy provider/catalog loading, and G23/fan-out after task wake/relay
changes. Host-free flag-census, effective-setting, fault/retry and truncated-argument tests run against the
new pinned client; none of that substitutes for host gates or promotes a route.

Qualified on 2026-10-30 and 2026-10-31
([DECISION.md](DECISION.md#update-2026-10-31-stock-v028-tuning-profiles-and-the-studio-batch-mtp-route-qualify),
[2026-10-31 measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v028-2026-10-31-stock-omp-18140),
[2026-10-30 measurements](MEASUREMENTS.md#strata-v028-windows-2026-10-30-stock-omp-18140)): on the PRO,
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0` (current, pinning
`strata.batch_mtp: true`, `--batch-mtp`, and `strata.ple_io: "direct"`, `--ple-io direct`),
`win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0` (qualified alternative, PLE direct reads
only) and `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0` (rollback); on the RTX 5090, the 262K
default (`win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0`, now the host's default with Docker Desktop and WSL
stopped; main-chain G10 listener failure on Windows build 26300.9818 retained beside the passing `f9e8c74` rerun) and
131K alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`, qualified for running with Docker Desktop and
WSL up; main-chain G10 failure retained beside the passing `f9e8c74` rerun), rolling back to their `v0.2.7` + OMP
`18.13.2` predecessors; on the pair,
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`
(current, pinning manual `layer_split: "24"`, `strata.trim_stage_weights: true`, `--trim-stage-weights`, and
`strata.ple_io: "direct"`, `--ple-io direct`, with 19.15 / 17.76 GiB expert caches, 27.8 GiB G10 commit headroom and
the 8,192 MiB automatic conversation cache) rolling back to
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0` (27.9 GiB commit
headroom); and on the Mac Studio client, the independent Studio→PRO route
`client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0` (current) rolling back to
`client-rtxpro6000-262k-strata0.2.8-omp18.14.0`. The pair's `v0.2.8` stock-residency draft
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`) stays a measurement-only draft.
[`releases/campaigns/v0.2.8.json`](../releases/campaigns/v0.2.8.json) is complete across all five `hosts[]` entries;
no default-runtime switch against NInfer follows.

## Strata v0.2.7 setup review (component engine)

Stable `v0.2.7`, published 2026-10-27T14:54:42Z: annotated object
`3f6d9c28e56bfce604601f39de53d457fa90dc74`, peel `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`.
Compared with stock v0.2.3 (`5c8dd322528cc84f68f461ad54a506b9da8fa8d4`).
App/Terminal **0.2.7**, Control and engine **0.1.52** are separate component versions.
The selected Qwen asset is `strata-engine-0.1.52-windows-x86_64-cuda-cuda13.tar.gz`
(620,430,878 bytes), SHA-256
`bfa68c6b2e92f9c273caaf937d9ae164918e6de4cca2dc1f1d79d32470f0915a`;
manifest SHA-256 `1e0e8828f64522bda7a866625c1a47822c53a93abaf8a1b7eb80e9887d69749b`;
build `a42cc3d7df70+cuda13.0`, BUILD source `f-027-rel`, BUILD commit `a42cc3d7df70`.
Archive/member hashes and BUILD identity were inspected without executing a binary; component-signature
verification is not claimed. After [`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json) froze the
release asset inventory, upstream amended the same `v0.2.7` GitHub release in place with its `0.2.7.1` assets
(Control `0.1.53`, ARM64 and macOS DeepSeek packages, and updated installer/feed metadata); every frozen asset used
here is still present, and the pinned Windows CUDA 13 Qwen engine asset above is unchanged.

### Reviewed planning and dependency delta

The unmodified report/draft refused `new call in stock setup planning; review required`: `resolve_rope`
now rejects explicit non-finite or sub-unit factors with `math.isfinite`. Admit only its exact helper,
not a new general `pure_exec` call. Pair planning additionally needs the exact changed `gpu_problem`;
its new Maxwell advice is unreachable for the planner's already-required compute capability >=7.5.

| Reviewed entry | Full-field AST SHA-256 | Decision |
|---|---|---|
| `resolve_rope` | `5f7b7cf3cac4e93371dfb722d39b1aafe58d73b0a83a86cd985d67e3e61a2981` | Pure validation; our explicit contexts stay inside 262144 and pass no factor. |
| `gpu_problem` | `454eda73ba81a3199f5ec13382876d3cd5d9e3bd9c3d0f37cd5edf1ae1c98a41` | Maxwell-only refusal text; no new card generation admitted. |
| `runtime_packages` | `b004722bb3aa164aa266d9b009bb85f846e62a15044cac9aa38b4937139afa1b` | Check, never execute its file reads; both shipped requirements files are consumed by native setup. |
| `requirement_lines` | `367fbc3d2049d4f912e9087381356a59bb940b2da6fd19e776f978e7774073c7` | Unchanged comment/blank-line filtering; check, never execute. |
| `REQUIREMENTS` assignment | `0f146fda709be127bb86cf4ffede8a8ff60527789751b3a5215b6f4500c9080d` | Fixed source-root `requirements.txt`. |
| `MONITOR_REQUIREMENTS` assignment | `f7cb1bbc75fc8f5e3200682363a5bcdcc267174a15e563c7017ffb41b54a9f18` | Fixed source-root `requirements-monitor.txt`. |
| Native `pip_install(runtime_packages(), ...)` call | `5c5e54935d65a0b6ede5f08219b5859e90ab7ef9edea61eaf3c9f5aec374384e` | Exactly one native runtime-package call; no TUI/interactive condition. |

**The runtime requirements file is unchanged, but the consumed dependency set is not.**
`requirements.txt` retains blob `903773a12b614f6a1f39d14f2afb9a9e305a10b5`; build requirements,
`PY_PACKAGES`, `CUDA_WHEELS` and `LLAMA_CPP_COMMIT` are unchanged. Native setup now always calls
`runtime_packages()`, which adds the shipped `requirements-monitor.txt` (`textual==8.2.8`), even for
`--yes --no-start`. The old 17-pin lock would leave setup trying to install a missing package under
`PIP_NO_INDEX=1`; reusing it is refused with `--python-lock` guidance.

The new `locks/strata-python-cp313-win_amd64-strata0.2.7.txt`
(SHA-256 `a5c1a1c100ce955019c272abcca29d80f7e7c20d348c267c855965c12be69a90`) contains 26
hash-locked wheels, resolved host-free for `win_amd64`, Python 3.13, `cp313`, binary wheels only.
The 17 predecessor pins stay; additions are textual 8.2.8 and its reviewed transitive closure:
linkify-it-py 2.2.0, markdown-it-py 4.2.0, mdit-py-plugins 0.6.1, mdurl 0.1.2, platformdirs 4.13.7,
pygments 2.21.0, rich 15.0.0 and typing-extensions 4.16.0. No syntax/Jupyter/test extra is selected.
Drafts require exactly the consumed roots, these reviewed transitives and CUDA wheels; missing, conflicting,
extra or changed pins, changed input helpers/paths/caller, or another interpreter's closure are refused.
This preserves `install_python`'s `--no-deps` installation and stock setup's no-index boundary.

`bench_tips`, the disk-estimate group, fresh-config writers, user-args stamping and `tools/mtp_fetch.py`
(blob `8968dfa509581b657537da0047683b9fffb5cef1`) are unchanged. Existing Qwen/Coder/MTP revisions and
tensor pins stay. The `HF_REVISIONS` additions are only DeepSeek entries: `deepseek41` planning, its engine,
packing, vision, large-context and automatic updater paths remain outside this review and refused.

### Stock defaults carried by the drafts

The five native drafts preserve their predecessors' explicit flags, config keys, model/context, slots,
roles, pipeline windows and conservative host floors. New behavior is stock engine behavior, not an added
environment or flag override:

| Lane | Engine 0.1.52 defaults that need fresh measurement |
|---|---|
| PRO slots4 | CUDA prompt attention uses int8 tensor cores; SM120 wide-up and stream-split hyper-connection reads default on. `--parallel 4`, `--prefill auto:32768`, `--pool-workers 15` stay pinned. |
| RTX 5090 131K and 262K | The same SM120 defaults; contexts stay 131072 and 262144, no slots. Single-card layer-major prefill stays off. |
| Pair roles and default A/B | Eligible split prompts default to layer-major prefill (`sm120_series.hpp` / `Prefill::run`); the Ada card defaults to its new MMVQ row tables. Two-card batch groups now default to pipelining only when batch slots exist (`batch_groups.hpp`); both profiles keep slots off. `--pipeline-windows 2` is a separate existing decode pin. |
| Every server | RAM PLE residency is now automatic only when its table, the expert arena and headroom fit; conversation parking remains RAM-dependent. Neither residency nor a measured speed/quality outcome is inferred from source. |

`STRATA_DEFAULTS=026` and per-feature switches are upstream A/B controls, not granted profile settings;
inherited `STRATA_*` remains scrubbed. No 12-GB residency-biased-routing default applies to these cards.
The v0.2.3 → v0.2.7 GET/POST/OPTIONS census adds GET `/tool-media/`, `/web/locales/` and
`/web/vendor/`, and loses no route. The latter two are the web app's whitelisted translation and
vendored KaTeX files: public static subtrees under the existing `/web/` prefix. The census now reads
literal `startswith` tuples as well as scalar prefixes, so neither subtree is hidden from review.
Stock `serve/server.py`'s `/tool-media/` branch requires the API key before serving MCP tool-result PNG/JPEG/WebP files
named by 64 lowercase hex digits plus an extension from the MCP hub's media directory. MCP is
unconfigured in these profiles, so G13 sends missing/wrong bearer and wrong `x-api-key` probes
(expected 401), then a correctly shaped filename with the correct key (expected 404), like its existing
unconfigured-image probes. These GET key checks start at engine 0.1.52; earlier unrouted GETs are not
authentication evidence. Source-branch and scripted-server tests prove the host-free contract, not G13
on a GPU host.

**Engine 0.1.52's stage order is admitted to `lifecycle.STAGE_ORDER_REVIEWED_ENGINES`** (`15c7426`). `gpu_list`,
`layer_split_value`, `layer_split_of`, `ordered_gpus` and `engine_args` are AST-identical to v0.2.3;
`child_env` changes only DeepSeek and HIP branches, unreachable here. The CUDA layer-boundary and primary
expert-cache message formats still match the parser. On the RTX 4090 + RTX 3090 pair, both starts of the roles
draft parsed complete with the reviewed parsers (RTX 3090 first, RTX 4090 last, layers 0-23 / 24-47, auto K=24;
[MEASUREMENTS.md](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132)). The default-split draft was
stopped during download and stays an unmeasured draft; roles evidence does not transfer to it.

### Stock OMP 18.13.2 surface

The drafts pin `e996e1c7ac476f60e02b8ed9764cf30fa8c00a8e`, with all three platform asset digests
resolved from the release. Keep stock behavior: [OMP#17096](https://github.com/can1357/oh-my-pi/pull/17096)
selects the `replace` edit tool for Qwen3.8 served IDs, instead of the predecessor's hashline tool.
No edit-mode setting or environment pin is added; tool/edit and long-session qualification must be fresh.
[OMP#17151](https://github.com/can1357/oh-my-pi/pull/17151) adds `ast_grep` to the bundled scout. Our
additional named scouts remain explicitly read/find/grep/glob; `fanout_proof` requires those named agents,
not the empty-map single-PRO route, and pins no bundled-scout tool census.
The pinned-binary CLI census also adds `--warn-cost` and `--max-cost`. Source review of
`cli/flag-tables.ts` and `main.ts` at v18.13.2 admits these USD thresholds as runtime-only
session-cost overrides, not routing/configuration/discovery overrides. The launcher policy test
retains its fail-closed census for every other unreviewed value-taking option.
[OMP#17159](https://github.com/can1357/oh-my-pi/pull/17159) follows linked continuation copies by newest
conversation turn. At `v18.13.2`, `session-manager.ts` records the predecessor's session id in both
`parentSession` and `continuationOf`; deliberate forks set only `parentSession`. Transcript readers join
only `continuationOf` links within a profile bucket, following `session-listing.ts`'s conversation-entry
timestamps rather than file mtime, exit records, idle usage or eval-state snapshots. An ancestor whose
newest turn is carried by a descendant is superseded; divergent copies with no unique newest turn,
duplicate ids and cyclic links fail closed. G23, fan-out and local gates select the requested workspace's
one conversation, not one file across the whole home. G23 permits a changed path only through those
links and still checks all previously persisted history entries in order, excluding the replaced header
and mutable title slot. G19 reselects its A transcript after the explicit `--resume` turn before
reporting per-request usage, since that turn can create another linked copy. Two-file regression tests
cover selection, history preservation and that post-resume evidence refresh.

Qualified on 2026-10-28 under the owner's overnight fleet authorization and afternoon qualification decisions
([DECISION.md](DECISION.md#update-2026-10-28-afternoon-the-pairs-ple-direct-and-rtx-5090-262k-strata-v027-profiles-qualify),
[MEASUREMENTS.md](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132)): the PRO
(`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2`), RTX 5090 131K default
(`win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2`), RTX 5090 262K opt-in
(`win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2`, qualified on its afternoon rerun with the host's Docker
Desktop and WSL stopped so 39.8 GiB RAM was available against the unchanged 36 GiB floor; morning failed receipts
with the resident VM are retained), pair PLE-direct stock-roles profile
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`, pinning
`strata.ple_io: "direct"`, `--ple-io direct`, with 27.3 GiB G10 commit headroom and the 8,192 MiB automatic
conversation cache enabled across all 16 starts) and independent Studio→PRO route
(`client-rtxpro6000-262k-strata0.2.7-omp18.13.2`). The pair's `v0.2.7` roles draft with PLE in RAM
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2`; G10 commit headroom 1.03 GiB
and conversation cache off, [Strata#4518](https://github.com/Niko1221/Strata/issues/4518)) stays a held draft, and
the unmeasured pair default-split draft
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.7-omp18.13.2`) stays unqualified.
[`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json) is complete across all five `hosts[]` entries;
no default-runtime switch follows.

## Strata v0.2.3 setup review (component engine)

Stable `v0.2.3`, published 2026-10-23: verified annotated object
`cad69daf8cbde12ef1fafd891ad69288e0ed2501`, peel `5c8dd322528cc84f68f461ad54a506b9da8fa8d4`.
The comparison is against `011c9e600a93bbc9fd451c563501b5831c32bbca` (v0.2.2).
App **0.2.3** ships engine **0.1.48**:
`strata-engine-0.1.48-windows-x86_64-cuda-cuda13.tar.gz` (581,299,508 bytes),
SHA-256 `1e1611b0977d984bd7d8e79591a1ba1a7e550a2f4a66bfa45744a77308a71b95`;
manifest SHA-256 `1767034593452895ad32d9aaa66c611ee7bec0fe09194b0ae154df2de96e1a6f`;
build `6f8800aefe27+cuda13.0`, BUILD source `f-023-rel`, BUILD commit `6f8800aefe27`.
As for v0.2.2, archive/member hashes and BUILD identity were verified without executing the binary;
component signature verification is **not** claimed.

### Reviewed planning delta

The unmodified report refused `stock split disk estimate changed; review required`. Two new full-field AST hashes
are admitted; every other v0.2.2 entry below is unchanged and still refuses any edit.

| Reviewed entry | SHA-256 | Decision |
|---|---|---|
| `bench_tips` | `05d188a10a65e59ba0365cd58ffa7a3d576d3023877aca3ed60dbccd434714c3` | Stock no longer recommends `--conversation-cache-mib` (the engine sizes the cache itself, below); the `--prefill` tip is unchanged. Drafts drop the predecessors' pinned parking tip and its flag. |
| `margin`, `mtp_fetch`, `real`, `need` group | `0d2db520b5dc89ec6b45ae88bf30a822ef6ea5a1c44ee6682169aa7575a144ce` | Pure arithmetic: 5.2 GB for the MTP drafter joins `real` while it is missing and setup is not ready. The PRO and pair disk floors rise from 90 to 91 GiB; the 5090 floors stay 90. |

- **Engine 0.1.48 parks conversations when the RAM allows** (Strata#3493). Without `--conversation-cache-mib`, the
  server sizes the conversation cache after load: 40% of the free RAM above its 2,560 MiB floor, at most 8,192 MiB,
  off under 1,024 MiB, with one log line; an explicit value (0 included) is kept. Whether a start keeps
  conversations is therefore the engine's call (`Profile.parks_automatically`): G19 reads `/metrics`
  `conversation_cache` and runs its kept-conversation probe unless the engine reports the cache off. Observed on
  2026-10-23: 8,192 MiB on the pair, 1,024-1,280 MiB on the RTX 5090 131K, off on the RTX 5090 262K. The cache
  takes at most 40% of what is left after load, so start floors need no new reservation; G21 measures it.
- **Stock GPU roles and one manual split point become pinnable.** The v0.2.2 `if multi` and `_roles` blocks are
  unchanged. A profile that pins `setup_args.gpu_roles` (`draft --gpu-roles 0=main,1=helper`) now evaluates the
  reviewed role writes, only in a namespace restricted to `getattr`, `isinstance`, `len`, `list`, `set`, `sorted` and
  `str`. Roles name every card Main or Helper (no Off), exactly one Main; the engine order is Helpers by card number,
  then Main, as stock `gpu_roles.engine_order` gives the server, with `gpu_order: "as_given"`. `--layer-split N`
  pins one split point for two cards and never combines with roles. Explicit `--gpus` without either option keeps
  the v0.2.2 behavior. The vendored v0.2.3 ordering code (`tests/fixtures/strata_0_2_3_server_order.py`) shows the
  pair's three drafts staging the RTX 3090 last (default, the #1576 VRAM guard), the RTX 4090 last (roles) and the
  configured order (split 32); `start` refuses a manual split whose engine boundaries differ from the pin.
- **Dependencies.** `requirements.txt` changed (blob `903773a12b614f6a1f39d14f2afb9a9e305a10b5`, was
  `b6f4d38ba2e2e477fc9307b20d7552e0f78a6e52`): certifi 2026.7.22 → 2026.10.19 and `truststore==0.10.5` added;
  `requirements-build.txt` is unchanged (`ebdef8ebb3174d696f5b4e332f6681aa9ba5f887`). `draft` now refuses changed
  requirements unless `--python-lock` names a lock pinning exactly them. The new
  `locks/strata-python-cp313-win_amd64-strata0.2.3.txt` (SHA-256
  `1e09fc5efbf63c36c835d87de53b883369f7e91c682dfcdd9723e57f0cd0ea03`) pins the 15 runtime requirements for
  win32/CPython 3.13 plus both `CUDA_WHEELS`, resolved host-free with `pip download --no-deps --only-binary=:all:`
  for `win_amd64`/`cp313`. Of its 17 pins, 15 match the v0.1.31 lock's version and hash; cmake and ninja,
  build-only upstream since, are not in it. `MIN_ENGINE` (0.1.46), `MIN_DRIVER`, `CUDA_WHEELS`, `PY_PACKAGES`,
  `LLAMA_CPP_COMMIT` and `HF_REVISIONS` are unchanged.
- **Operating-system certificates** (Strata#3722): the new `strata_control/tls.py`
  (`8c27ee54a92b93e7e88e2712dff773dc3e165e2f`) installs `truststore` in `setup.py` and `tools/mtp_fetch.py`
  (`8968dfa509581b657537da0047683b9fffb5cef1`, was `14898aef05637148aaa1cf74f8aeee7697e6824d`). The MTP revision
  pin and tensor hashes are unchanged; installation still accepts only pinned, hash-verified inputs.
- Generated config keys and the route census are unchanged for plans without roles; a roles plan adds `gpu_roles`
  and `gpu_order`. The environment census adds 21 names since v0.2.2, none removed: `STRATA_DATA_DIR`,
  `STRATA_DF2_FORK`, `STRATA_DF2_PRIO`, `STRATA_DF2_PROFILE`, `STRATA_DF2_SKIP`, `STRATA_DF2_TIMING`,
  `STRATA_DF2_WAITCOMMIT`, `STRATA_GFX1151_CHUNK`, `STRATA_GFX1151_EXP8`, `STRATA_OUT`, `STRATA_PROMPTS`,
  `STRATA_ROUTE_STATS`, `STRATA_SPEC_ADAPT_EVERY`, `STRATA_SPEC_ADAPT_SM86`, `STRATA_SPEC_ADAPT_WARM`,
  `STRATA_SPEC_COST`, `STRATA_SPEC_COST_TABLE`, `STRATA_SPEC_TRACE`, `STRATA_SPEC_T_CYCLE`, `STRATA_TAP_FILE`,
  `STRATA_TAP_LAYERS`. Inherited `STRATA_*` remains scrubbed; no environment opt-in is granted. DFlash2
  (`strata launch --drafting dflash2`) is Terminal-only and not used.
- Server-side tool-call parsing changed (Strata#3556: tool-name aliases and wrapper boundaries); the typed-tool and
  agent gates exercise it on each host, not this source review.
- **Engine 0.1.48's stage order is admitted** to `STAGE_ORDER_REVIEWED_ENGINES`
  ([#48](https://github.com/alphastorm/omp-strata/issues/48), opened for 0.1.47, which no multi-GPU profile runs).
  Source: `ordered_gpus` adds only stock roles' early return (the configured order, no message) and a HIP-only
  built-in-graphics branch; `layer_split_value`, `layer_split_of` and both engine message writers are unchanged.
  Host: every start of the pair's default, roles and split-32 drafts parsed complete with the order and boundaries
  those settings give ([MEASUREMENTS.md](MEASUREMENTS.md#strata-v023-windows-2026-10-23-stock-omp-18126)).

### OMP 18.10.1 → 18.12.6 client delta

The release notes of v18.10.2 through v18.12.6 change nothing `ompcfg.py` writes. The pinned-binary suite found two
client changes:

- **Subagents answer in plain text** (v18.10.2): task-spawned subagents return their final message, with no `yield`
  tool or output schema unless `task.structured` (default off) or agent frontmatter asks for them. The completed
  `<task-result>` envelope is unchanged. The fan-out proof's assignments and the generated fleet scout instructions
  now name both channels, and the mock fleet tests answer through whichever one the pinned binary offers.
- **`--restore`** (v18.10.3): resumes a session as `--resume` does, then continues its unfinished turn and
  subagents. It chooses no provider, model or configuration, so the launcher passes it like `--resume`.

Drafts, not qualified: the PRO, both 5090 lanes, the pair's default, roles and split-32 profiles, and the Studio
route against the new PRO, all on stock OMP 18.12.6 (`45c35e40c46166dc726ccc52f5d27f40f2449f99`). The 2026-10-23
windows ran the three server chains and the pair measurement; reruns, the pair's chain, receipts, G23 and the
owner's qualification decision remain.

## Strata v0.2.2 setup review (component engine)

Stable `v0.2.2`, published 2026-10-21: verified annotated object
`e6fff4ad12908de74952abe53b2bade45a68aa0f`, peel `011c9e600a93bbc9fd451c563501b5831c32bbca`.
The comparison is against `90767252f420e25223c739d604145ad15911d48b` (v0.2.1).
App **0.2.2** ships engine **0.1.47**, not engine 0.2.2:
`strata-engine-0.1.47-windows-x86_64-cuda-cuda13.tar.gz` (580,428,476 bytes),
SHA-256 `59833d875b2f3807791533f5dd077a0cb0ed08d4c1cab3136ad2ceb165871cd1`;
manifest SHA-256 `95eb1eef404859e3afae56811cccb3da27bbab6b589e276fe4e4e701dfbe9427`;
build `76f90e58436d+cuda13.0`, BUILD source `f-022-rel`, BUILD commit `76f90e58436d`.
The preparation inspection verified archive/member hashes and BUILD identity without executing the binary;
component signature verification is **not** claimed.

### Reviewed planning delta

The unmodified report refused `checklist: new call in stock setup planning; review required`.
The new call is `gpu_sel` inside `recommend_remote_expert_opt`, **not** VRAM fitting. The following
exact full-field AST hashes are admitted by the versioned tables in `scripts/upstream_watch.py`.
Earlier entries remain valid; any changed helper, role block, disk group or user-args module still refuses.
The general `pure_exec` vocabulary is unchanged (no new calls, comprehensions, probes or IO).

| Reviewed entry | SHA-256 | Decision |
|---|---|---|
| `gpu_sel` | `bbf4d50f7683de5f42d446b0d0802982f9d60c44a0a204392bfffa4d48906646` | Pure scalar/list/tuple/string normalization; load before remote-cache advice. |
| `recommend_remote_expert_opt` | `6bfb60fef7092efb584a2fc052f25f8b84d3863debe02040004d5f041ce9b672` | Exact helper only; plain layer splits still get no helper-cache flag. |
| `tier_pick` | `5d41bbc51e005e058d63fce392b97711180d75409745ac6adde4fbe93306ee91` | Informational thresholds 62/46/38 now compare RAM + VRAM minus the literal `TIER_SYSTEM_RESERVE_GB = 5.0`. No explicit model/context changes. |
| Entire `if multi` block | `360bbac44ee628d2e82295b28dc2d9fd9418fc4f37d7bcd3a995922fbf3d5e9c` | Require false role guard; evaluate only unchanged explicit-gpus body. |
| Entire top-level `_roles` block | `5ec2fe77b9c37e2282f3e716df9f4f8373fa705e25051f0f2b5b1f60b3d96f84` | Fixed `_roles=None`; refuse reachable roles, never execute role writing. |
| `margin`, `real`, `need` module | `73b0a4fd10c9cfb5ad90e732694f5bbbb275f963f9724db13211d51b6ee43312` | Fresh-root pure arithmetic only; preserve conservative `need = real + margin`, not merely the hard `real` floor. Never call adjacent `free_gb`. |
| Full `strata_control/user_args.py` module | `625e4282ba491b97cd8073a9c687acc90023ecb115233cd123eb6a36b7b717ae` | Multi-value control-vector editing changed; fresh capture/stamp did not. No module execution in drafting. |

The disk statements individually hash to `d6bdd75ef486f261f907b53f13be30355755cac37cc829de2f181c74cb1ce3a8`
(`margin`), `915ab797655a6067e23d77e6eb59e4dd5c43dec821ab9c94f2a12fefd9353544` (`real`) and
`9f92d18c4ed4c3b7bc54fe1451324b1c028babc0ea6e7a42ea3af17eb1a2c81d` (`need`).
The false ready-pack `prep_gb` guard retains
`8fefc825ebd599703c976feebf90874800c5f2902b0881a641076a3dd3a08d00`.
The default-question projection retains
`ca0dbfc6feb30ed72337ab4af81268f15c5c9dd706511846070be360209ebe52`;
`write_setup_config`, `carry_user_args` and `explicit_args` retain their `FRESH_WRITE_0_2_1` hashes.
Fresh config still has `args_written == args`, no `user_args`.

- Explicit `--gpus` returns before interactive Main/Helper/Off selection; scalar profiles use `--gpu`.
  Preserve automatic pair ordering, slots, pipeline windows and pinned tips. No `gpu_roles`, `gpu_order`,
  helper cache or role/order opt-in is admitted. Actual stage order, layer split and performance remain host gates.
- The new `strata_control/vram_fit.py` (SHA-256
  `c295ce23f70c703d1e14b931b27413a42c5538cf3cabfc2336e48734e36173ba`) tries 32K/16K/8K contexts,
  then chunk/reserve choices within each context. Its callers are SYCL setup and app/CLI launch/adoption,
  not native NVIDIA `setup.py`. Do not import those fallbacks or assume its comment protects contexts above 32K.
  The four reviewed plans retain 131072/262144 contexts and predecessor disk/RAM floors.
- Runtime requirements, build requirements, `PY_PACKAGES`, `CUDA_WHEELS`, `LLAMA_CPP_COMMIT`,
  `HF_REVISIONS` and `MIN_DRIVER` are unchanged. `MIN_ENGINE` changes 0.1.45 → **0.1.46**, a minimum,
  not the component's 0.1.47 version. `tools/mtp_fetch.py` is byte-identical (blob
  `14898aef05637148aaa1cf74f8aeee7697e6824d`); requirements blobs remain
  `b6f4d38ba2e2e477fc9307b20d7552e0f78a6e52` (runtime) and
  `ebdef8ebb3174d696f5b4e332f6681aa9ba5f887` (build). This is not a fresh HF availability observation.
- Generated keys and GET/POST/OPTIONS route census are unchanged for these plans; optional role writes are
  visible in the checklist, not admitted. Route equality is **not** security equivalence: upstream introduces
  `--no-api-key` / `api_key="none"` and removes its non-loopback no-key refusal. omp-strata still requires
  loopback and a nonblank generated key; none of those guards is changed here.
- The environment census adds 20 names, none removed: `STRATA_BUILD_COMMIT`, `STRATA_COMMIT`,
  `STRATA_ENGINE_NICE`, `STRATA_HANDOVER`, `STRATA_HANDOVER_IN_CHECKOUT`, `STRATA_METAL_GYRO_TILES`,
  `STRATA_MOVE_ALWAYS_COPY`, `STRATA_NO_HANDOVER`, `STRATA_NO_PROMPT`, `STRATA_NUMA_POOL`,
  `STRATA_NUMA_SPLIT`, `STRATA_POOL_CORES`, `STRATA_SPEC_WATCH`, `STRATA_TEST_OTHER_VOLUME`,
  `STRATA_TEST_SYSFS_ROOT`, `STRATA_TQ_ROWCH`, `STRATA_TQ_STAGE`, `STRATA_TQ_SUB8`,
  `STRATA_UMA_RESERVE_GIB`, `STRATA_VERIFY_EARLY_PLE_FLAG`. Inherited `STRATA_*` remains scrubbed;
  no environment opt-in is granted.
- Signed-feed fallback, updater/download paths and hardware probes remain outside this pure planner.
  Native installation must still stage the pinned component and reuse verified local inputs without invoking
  those paths. Preserve supplied GGUF bytes and hard-linked predecessors; no download repair is authorized.

Host-free fixtures exercise all four plans, threshold boundaries, false-role guards, fresh stamping and mutation
refusals. `report` retains its existing semantics: complete release news exits **3**, incomplete review exits 4.
This review writes no profile, release ledger, current/rollback pointer or route. Full candidate drafting and its
candidate-specific dev-env suite, native installation/feed exclusion, G00–G23 as applicable, observed split/speed,
publication and the owner's qualification decision remain separate gates.

## Strata v0.2.1 setup review (component engine)

Stable tag `v0.2.1` (published 2026-10-20), annotated tag object
`49ac15cbb32a8662602aaa7b8fc61bf6acef4cf0`, peels to commit
`90767252f420e25223c739d604145ad15911d48b`. App `0.2.1` ships the Windows engine as a separately
versioned component, engine **0.1.46**: `strata-engine-0.1.46-windows-x86_64-cuda-cuda13.tar.gz`
(579,792,118 bytes, SHA-256 `2966143ca8df7919448556e7d148e49ccecae0932bb0d5d31294ccde723f94cd`),
manifest SHA-256 `d6ea7d4ae8dce1e646a55363d14c97f9659197f63d500da90efe0d4a8fd82d3e`, build
`a7bdbfdabc9a+cuda13.0`.

- No `strata-windows-x64.zip` is published. Profiles install through native pinned-source setup with the
  verified engine component staged into `runtime\strata\engine\` before stock setup runs
  ([OPERATIONS.md](OPERATIONS.md#upgrades),
  [UPSTREAM-BETA.md](UPSTREAM-BETA.md#stable-component-releases-v021-and-later)). The manifest's ed25519
  signature is not verified, and no Control package, signed feed or installer is used. `start`'s
  authenticated identity check expects `/props` `build_info` **`Strata 0.1.46`** (the engine version,
  not `0.2.1`).
- Setup's generated config adds only `args_written`, which must equal `args` (no `user_args`).
- The reviewed requirements change moves only `cmake` and `ninja` to `requirements-build.txt`; CUDA
  wheels, Python packages, the llama.cpp pin and the driver floor are unchanged.
- Stock contract changes introduced in `v0.2.x` (gates adjusted without weakening older-engine checks):
  - **G17 (`13cbdbe`):** since `v0.2.0-beta` (engine `0.1.45.3`), stock's server shortens a `max_tokens`
    that is one token over the room left to the room left instead of answering 400; a prompt that alone
    leaves no room is still refused.
  - **G13 (`18f128a`):** now also probes `v0.2.x`'s authenticated `/v1/telemetry` GET (protected; any
    read-only telemetry key in the environment is scrubbed, and config `telemetry_read_key` is refused by
    install) and the key-only `/v1/v1/messages` and `/v1/v1/messages/count_tokens` aliases.

## Strata v0.1.44.1 setup review (host-free candidates)

The annotated tag object `9791ea335ba2001c87b5f783146d6eb08fdd9e5e` peels to commit
`296b59d2f73c8f04a805df29c2fa97655adace78`. The draft planner reviews only the existing
native Windows NVIDIA GSQ-RCO choices: Qwen IQ3_S and Coder IQ1_M. New NVFP4, Unsloth and
Qwen3.6 families are not admitted as planning choices by this review.

- Setup's `MODELS` table now references three literal NVFP4 constants. Only those named literal
  aliases are resolved; calls and unknown names still refuse. The expanded family/shard tables are
  read as stock data, not as permission to plan their new runtime paths.
- The fresh-install recommendation changes from IQ3_XXS to IQ3_S where RAM fits. A setup rerun
  keeps its installed size. The planner verifies both exact ASTs, fixes the fresh-root installed
  choice to none, and never executes the helper that reads installed config files. Explicit profile
  model/context choices remain separate from this informational recommendation.
- The new ready-pack model-argv branch is reviewed exactly; only its GSQ-RCO argv expression is
  evaluated. The rotational-disk, Unsloth small-card and image-generation branches are admitted
  only at their reviewed AST hashes and only with false guards. Changed bodies or reachable guards
  refuse. `unsloth_default_env` is an exact reviewed helper and returns no env entries for either
  GSQ-RCO family; images remain unconfigured.
- The new POST image-generation endpoint enforces the existing POST key check, then returns
  404 `images_not_set_up` without an image configuration. Image-file URLs are public token URLs
  by design, but return 404 when no image service exists. G13 classifies both as unconfigured:
  missing/wrong-key POST probes and an empty authorized POST, plus a real file-prefix endpoint.
- `MIN_ENGINE` is 0.1.44.1 and `HF_REVISIONS` adds the Qwen3.6 repository. CUDA wheels, Python
  packages, the llama.cpp pin, driver floor and requirements blob are unchanged. The extracted
  `engine_step` retains archive verification, BUILD.json minimum-version and GPU architecture/PTX
  checks. The Windows ZIP adds the K-quant prompt DLL, opened only for Unsloth K-quant models.
- The pair retains automatic layer splitting. Its next real-host window must observe the changed
  spare-VRAM near-tie placement (#1440), relative-link penalty from a 4x gap (#2007), and all-card
  startup VRAM checks (#2192). This source review adds no flags and supplies no measured result.

## Strata

1. **A queued client's disconnect poisons the next long request and crashes the engine.** Reproduced 2/2 by
   `scripts/realhost_gates.py g14q`; the control case is clean. Upstream: same root cause as
   [Strata#183](https://github.com/Niko1221/Strata/issues/183). **Fixed in v0.1.28** by #205 (`6cad1fe`; #194 was
   closed unmerged): `err` is now cleared at the start of every request, right after the line cited below, before
   each prompt segment and on entry to `Prefill::run` (source reading). The v0.1.28 release notes report a long
   prompt cancelled and then sent again, followed by a short one, with the engine staying up. **Confirmed on the
   real host with v0.1.30** (second candidate, G14 and `g14q` pass): both queued-disconnect scenarios and the control
   served two consecutive 8,123-token prompts with the same engine process.
   - Steps: request A is generating and request B is queued behind it; B's client disconnects. Then the next
     request whose prompt needs more than one prefill window (about 8K tokens here) fails with HTTP 400
     `cancelled`, the engine exits with code 1, and the request after that gets HTTP 503 before the lazy restart.
   - Short prompts in between are served normally.
   - Cause: B reaches the engine after A and is stopped while it reads its prompt, which leaves the engine's `err`
     string set to `cancelled`. The next request clears `stop_req` but not `err`
     (`src/program/generate.cpp:3561`), so a prompt read in batched chunks fails on its first chunk and the serve
     loop exits with code 1 (`:3996-4000`). The windowed path used for short prompts does not check `err` first.
   - Workaround here: `omp_strata.py restart`.
2. **Tool calls cut off mid-arguments are finalized as complete.** When the model ends its turn inside a tool
   call, `OutputParser.finish()` closes the partial JSON and the response reports `finish_reason: tool_calls`.
   Clients then execute truncated arguments; see OMP item 1. Reproducer:
   `tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body_is_not_reported_as_complete`
   (the stock frontend with its MockEngine). A cut on `finish_reason: length` is correctly reported. Upstream: the
   second trigger of [Strata#210](https://github.com/Niko1221/Strata/issues/210); our #211 was closed as its
   duplicate, then reopened with a repro at v0.1.28, which fixed only the first trigger (`</parameter>` or
   `</tool_call>` inside an argument). **Fixed in v0.1.31** by
   [Strata#231](https://github.com/Niko1221/Strata/pull/231) (`925c354`, with `9a1fc19`): an announced call the
   output ends inside stays unfinished, its JSON is not closed, and the answer ends with `stop` (or `length`)
   instead of `tool_calls`; a non-streamed answer leaves such a call out. On the mock tier with v0.1.31 the
   reproducer's stream now ends with `stop` and unterminated arguments. With stock OMP 18.4.8 the composed G04 case
   still failed, because that client turned the stream into a tool turn and ran the truncated write (OMP item 1).
   With OMP 18.4.10 (fourth tuple, Strata v0.1.34) the composed case passes: OMP answers the call with the parse
   error, writes nothing, and the model continues (stop reasons `toolUse`, `stop`; exit 0).
3. **`/status` is unauthenticated and includes a tail of the generated text.** With an API key set, any local
   process can still read the last 600 characters of the current answer, and of the most recent one while the
   server is idle, because the tail is not cleared when a request ends. Upstream:
   [Strata#212](https://github.com/Niko1221/Strata/issues/212). **Fixed in v0.1.28** (`4d25c61`): with a key set,
   `/status` answers 401 without it, and the tail is dropped when the request ends (mock tier; confirmed on the real
   host with v0.1.30, G13).
4. **An empty API key disables authentication, and keys are compared with `==`.** The "no API key" warning is
   printed only for non-loopback hosts. The integration refuses to start without a key of at least 32
   characters. Upstream: [Strata#213](https://github.com/Niko1221/Strata/issues/213). **Fixed in v0.1.28**
   (`4d25c61`): keys are compared with `hmac.compare_digest`, and an explicitly empty key (`--api-key ""` or an
   empty `STRATA_API_KEY`) stops the server; on the mock tier an empty `STRATA_API_KEY` exited with code 2. An
   absent key still means no authentication, so the integration still refuses to start without a key of at least
   32 characters.
5. Stock `setup.py` resolves the engine from `releases/latest`, the model and MTP tensors from `main`, and
   unpinned PyPI packages, and it writes to `%APPDATA%\Strata`. The integration feeds it pinned, verified local
   inputs instead. Upstream: [Strata#214](https://github.com/Niko1221/Strata/issues/214). **The fetches are fixed
   in v0.1.31** by the maintainer's `ba5c387`: a checkout installs the engine release of its own version
   (`releases/latest` when that release cannot be reached), every Hugging Face file comes from a pinned commit (the
   same Coder and MTP revisions this integration pins), and the Python packages come from a pinned
   `requirements.txt`. Our [Strata#324](https://github.com/Niko1221/Strata/pull/324) proposed the same three fixes
   six hours after `ba5c387` was committed; v0.1.31 superseded them. #324's fourth change went into **v0.1.32** as
   the maintainer's `09c05e7` ("From PR #324"): an engine archive that setup refuses (too old, or without code for
   the GPU) is deleted with its `.done` mark. That fixes our follow-up
   [Strata#397](https://github.com/Niko1221/Strata/issues/397): v0.1.31 kept the refused archive, so every later run
   reused it and "run this again in a few minutes" never updated the engine. `09c05e7` reached `main` only with
   v0.1.32, after #397 and our fix [Strata#399](https://github.com/Niko1221/Strata/pull/399) were filed; the
   maintainer closed #397 as fixed and #399 as covered. #399's two tests fail on v0.1.31 and pass on v0.1.32 and
   v0.1.33. Not taken from #399: an archive that failed to unpack kept its `.done` mark in v0.1.33 (v0.1.34 by
   source reading), so later runs failed on the same file even after a good archive was published. **Fixed in
   v0.1.40** by the maintainer's `645cbb6`: `BadZipFile` drops the archive and its `.done` mark before re-raising.
   On 2026-10-06 the maintainer closed our [Strata#424](https://github.com/Niko1221/Strata/pull/424) as fixed.
   Per-user settings still go to `%APPDATA%\Strata`. The integration keeps passing local verified inputs and
   redirecting APPDATA; its Python lock for v0.1.31 is resolved from that `requirements.txt` (unchanged in v0.1.34).
6. **Every unexpected engine exit is logged as a probable out-of-memory event**, including the stale-cancel crash
   in item 1 and deliberate kills. None of the 5 exits observed here was memory-related. Upstream:
   [Strata#215](https://github.com/Niko1221/Strata/issues/215). **Fixed in v0.1.28** (`4d25c61`): when the engine
   exits by itself, the server quotes its exit code and last log line; the out-of-memory
   hint remains for other exits (source reading; on the real host with v0.1.30 the cut turn after a mid-generation
   engine kill read "the engine stopped unexpectedly (exit code 1); the next request restarts it", G15).

7. **Strata v0.1.44.1's and v0.2.1's automatic layer splits on the RTX 4090 + RTX 3090 pair.** Upstream:
   [Strata#2463](https://github.com/Niko1221/Strata/issues/2463), **opened 2026-10-14, closed on 2026-10-19 as not
   planned** (no change to link pricing). In the v0.1.44.1 three-arm back-to-back comparison (same model and setup),
   v0.1.43.1 splits layers 0-31 / 32-47 across the RTX 4090 / RTX 3090; v0.1.44.1's default link-miss rule moves
   them to 0-44 / 45-47 (K=45). Decode falls from 184-206 to 148-154 tok/s, prompt reading to 0.52-0.77x, and
   100K-token TTFT rises from 28.6 s to 55.0 s. The diagnostic v0.1.44.1 arm with `STRATA_SPLIT_LINK_ABS=1` restores
   the split at layer 32: decode 164-199 tok/s, prompt reading 1,605-3,604 tok/s and 100K-token TTFT 28.6 s. That
   opt-in knob exists upstream, but this integration refuses `env` on multi-GPU profiles and does not set engine
   environment overrides there; on 2026-10-14 the owner held the pair on v0.1.43.1 and left the v0.1.44.1 pair
   release draft, not qualified. In **v0.2.1** (2026-10-21), the automatic split moves to layers 0-24 on the RTX
   4090 and 25-47 on the RTX 3090 (K=25). Measured back to back against v0.1.43.1 on the same host (2026-10-21
   02:03-02:06Z, one 512-token sample per depth, server-reported rates; MTP acceptance 0.8 in both), decode is
   141-158 against 170-201 tok/s, prompt reading at 64K-100K tokens 2,838-2,853 against 3,508-3,594 tok/s, and
   100K-token TTFT 36.0 s against 28.6 s
   ([per-depth table](MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-21-stock-strata-v021-stock-omp-18101)).
   On 2026-10-21 the owner qualified v0.2.1 with OMP 18.10.1 as
   current on the pair anyway; v0.1.43.1 with OMP 18.10.1 stays its qualified rollback, and the v0.1.44.1 pair
   release remains draft, not qualified.
8. **Engine 0.1.52's automatic PLE RAM residency on the 128 GB RTX 4090 + RTX 3090 pair disables the automatic conversation cache and leaves 1.03 GiB Windows commit headroom.**
   Upstream: [Strata#4518](https://github.com/Niko1221/Strata/issues/4518), **opened 2026-10-28**. On the
   128 GB-RAM pair (`rtx3090-win-a`, Qwen3.8-Flash-Next IQ3_S at 262,144 tokens, stock roles
   `--gpu-roles 0=main,1=helper`, pipeline windows 2), engine `0.1.52`'s residency policy chooses `--ple-io ram`,
   locks the 26.8 GiB per-layer embedding (PLE) table in RAM at start (~31.4-37.5 s), leaves the automatic
   conversation cache off ("not enough free RAM to park conversations"; `/metrics` `conversation_cache`:
   `enabled: false`, `budget_mib: 0`, versus 8,192 MiB on `v0.2.3`), and leaves only **1.03 GiB** (`1,109,463,040 B`)
   Windows commit available in G10 against **27.3 GiB** (`29,320,192,000 B`) on `v0.2.3` roles at the same
   **135.7 GiB** (`145,695,096,832 B`) commit limit (0.632-1.331 GiB in a later pair bench). In back-to-back
   single-sample `scripts/perf_probe.py` runs, 100K-token TTFT was 30.40 s with PLE in RAM versus 31.15 s with a
   throwaway `STRATA_PLE_AUTO_RAM=0` arm (`v0.2.3`: 31.23 s). Because launch strips inherited `STRATA_*` variables and
   multi-GPU profiles refuse `env` overrides, `omp-strata` adds profile field `strata.ple_io: "direct"` pinning stock
   `--ple-io direct` ([OPERATIONS.md](OPERATIONS.md#stock-ple-direct-reads)). The qualified PLE-direct profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`) keeps the PLE
   table on direct SSD reads (`PLE direct read probe: N rows/s (fine)` on all 16 starts, no residency-policy line),
   restores the **8,192 MiB** automatic conversation cache (`31` parks in G19), leaves **27.6 GiB** (`29,634,629,632 B`)
   Windows commit available in G10, and reaches ready in 56.8-57.0 s across G16/G20/G21; the roles draft with PLE in
   RAM stays unqualified ([decision](DECISION.md)). On `v0.2.8` (engine `0.1.54`), upstream's fix locked the
   26.8 GiB table (33.9-34.0 s), then gave the lock back on both starts and sized the automatic conversation cache at
   **4,864 MiB** (106-112 s to ready), against **8,192 MiB** and 61-63 s to ready with `--ple-io direct` at matching
   100K-token TTFT (31.2 s with PLE direct versus 30.9 s with stock residency;
   [MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-stage-order-and-strata4518-on-engine-0154)). The qualified
   `v0.2.10`, `v0.2.9` and `v0.2.8` pair profiles — the current `v0.2.10` DFlash2 (`df2`) split-24 trim + PLE-direct +
   `env86g` profile
   (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`,
   8,192 MiB cache, 27.51 GiB G10 commit headroom, G24 17/18), its `v0.2.10` `pw2` `env86g` MTP rollback
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`,
   8,192 MiB cache, 27.54 GiB G10 commit headroom, G24 16/18), the earlier `v0.2.9` split-24 trim + PLE-direct + `env86g`
   profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`,
   8,192 MiB cache, 27.77 GiB G10 commit headroom, G24 15/18), its `v0.2.9` split-24 trim + PLE-direct base profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`,
   8,192 MiB cache, 27.74 GiB G10 commit headroom, G24 15/18), the earlier `v0.2.8` split-24 trim profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`,
   8,192 MiB cache, 27.8 GiB G10 commit headroom, G24 15/18) and the initial `v0.2.8` `roles-pledirect` profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`, 8,192 MiB cache,
   27.9 GiB G10 commit headroom, G24 15/18) — therefore keep `--ple-io direct`.

## OMP

Re-verified against OMP `main` (`2b023d1`, 2026-09-30) and, where a reproducer exists, against the stock 18.4.6
binary pinned by the second candidate, the stock 18.4.8 binary of the third tuple (2026-10-01; 18.4.7 and 18.4.8
changed only the macOS natives and the TUI) and the stock 18.4.10 binary of the fourth tuple (2026-10-02); each item
notes its status. Our pull requests are linked per item: #13866 and #13867 were merged on 2026-09-30 and released in
18.4.5; #13864 was merged on 2026-10-01 and released in 18.4.9; #13868 was merged on 2026-10-01 and released in
18.4.10 (2026-10-02). #14734, #14735 and #14737 were merged on 2026-10-07, after 18.8.0 was cut, so no release
contains them yet.

1. **Executes tool calls whose arguments are syntactically truncated.** At finalization OMP parses the argument
   string with its lenient streaming parser, which closes unterminated JSON, and runs the call: a partial file
   write happens and the run exits 0. Reproducer:
   `tests/mock/test_g04_faults.py::test_truncated_arguments_must_not_execute_side_effect`. A `length` cut is handled
   correctly (`::test_finalized_partial_json_with_length`). `::test_finalized_partial_json_with_stop` is the composed
   case before Strata item 2's fix: the server closes the JSON itself, so OMP receives valid JSON and cannot tell.
   Since Strata v0.1.31 the server leaves the JSON open and ends with `stop`, and OMP 18.4.8 still runs the call
   (`tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body`: the truncated write happens,
   exit 0, stop reasons `toolUse`, `stop`). Present in the 18.4.0-18.4.9 binaries. **Fixed in 18.4.10** by
   can1357/oh-my-pi#13868: with the 18.4.10 binary both reproducers pass (no write; the call gets the parse error
   and the run continues), so G04 no longer fails on the fourth tuple. `::test_finalized_partial_json_with_stop`
   stays a client limit no OMP release can fix: valid JSON is valid, so it is skipped when the pinned Strata leaves
   cut calls unterminated (v0.1.31+).
2. **Contacts the internet at startup.** The background model-registry refresh (`refreshInBackground`) fetches the
   public model catalog from `catalog.stencil.so` when its cache is cold or stale, and implicit local providers probe
   127.0.0.1:11434, :8080 and :1234; no startup setting disables either. Observed with ETW in G13 (18.4.0); with
   18.4.6 and the guard, the loopback probes are still visible and no non-loopback endpoint was reached. Workaround
   here: proxy variables pointing at a closed loopback port. Upstream, can1357/oh-my-pi#10934 asks for a catalog
   opt-out.
3. **Sends `Bearer STRATA_API_KEY` literally when a models.yml `apiKey` names an unset variable**, instead of
   failing. This is OMP's documented contract (an `apiKey` is tried as an environment variable name, else sent as the
   literal token), which is why `launch-omp` refuses a missing key. Reproducer:
   `tests/mock/test_g02_isolation.py::test_raw_stock_missing_key_dispatches_literal_and_fails_401`.
   can1357/oh-my-pi#13866 added a documentation warning (merged); the behaviour is unchanged in 18.4.6.
4. **Retries on `openai-completions` cannot be turned off.** An HTTP 500 produced 12 identical requests (6
   transport attempts × 2 provider attempts) with `retry.enabled: false`. The transport's `DEFAULT_MAX_ATTEMPTS`
   (`packages/ai/src/utils/openai-http.ts`) reads no retry setting, so `retry.maxRetries` cannot reach it either.
   Reproducer: `test_g04_faults.py::test_http_500`. Still present on `main` and in 18.4.6 (12 requests again);
   related: can1357/oh-my-pi#13255.
5. **The fitted `max_tokens` can overshoot a strict server by a few tokens.** The fit is
   `agent/src/output-budget.ts` `fitOutputTokensToContextWindow`. Near the window, prompt 105,522 + fitted cap
   25,563 exceeded Strata's 131,064 (131,072 − 8) by 21 tokens, and the closing turn failed with HTTP 400 (G17
   attempt 3). Fixed upstream by can1357/oh-my-pi#13499 (a 64-token headway, in 18.4.4). The integration keeps
   declaring the window 1,024 tokens below the engine's for both candidates; with 18.4.6 the largest near-limit
   prompt + cap seen was 129,997 (G17), inside the declared window without relying on the headway.
6. **Strata's overflow message is not classified as a context overflow.** `ai/src/error/flags.ts` has no pattern
   for "prompt (N tokens) + max tokens (M) exceeds the context", so no compaction recovery is attempted. This is
   minor, because item 5's fit usually prevents the overflow. **Fixed in 18.4.9** by can1357/oh-my-pi#13864
   (`edb740c`; source reading); not exercised here, because every profile pins 18.4.8 or older.
7. **Unknown `models.yml` compat keys are accepted silently.** A misspelled key is kept without an error. The
   integration guards its emitted keys with a test. **Fixed on `main`** by can1357/oh-my-pi#14737 (`3205ec9`,
   merged 2026-10-07): an unknown key in a provider, model or `modelOverrides` `compat` block now produces a
   non-fatal warning. No release contains it yet.
8. `--thinking off` still sends `reasoning_effort: low` with this dialect; OMP documents this as requesting the
   lowest effort on generic effort endpoints; can1357/oh-my-pi#13867 made that clearer (merged). Unchanged in 18.4.6
   (off/low/medium/high/xhigh are sent as low/low/medium/high/high). `--no-tools` disables the built-in tools, so it
   is not a way to limit egress.
9. **Services an agent starts stop 3 s after `omp --print` exits.** The service broker stops non-detached services
   once its idle grace (`OMP_DAEMON_IDLE_GRACE_MS`, default 3,000 ms) runs out after the last client disconnects, so a
   benchmark that checks a server after the agent exits finds nothing (Terminal-Bench `hf-model-inference` and
   `kv-store-grpc` on 18.5.0). Upstream's metaharness set nothing to prevent it. Scripted check on 18.5.0 and 18.7.0:
   a bash-tool service is gone 8 s after exit, and still listening with a 120,000 ms grace. **Fixed in upstream's
   metaharness** by can1357/oh-my-pi#14734 (`dc97a4a`, merged 2026-10-07): `omp_local.py` now runs omp with
   `OMP_DAEMON_IDLE_GRACE_MS` set to 24 h, so the services stay up until the container is torn down. The broker's
   3 s default is unchanged.
10. **18.5.0 drops the retry for a reasoning-only stop once a run has restarted.** OMP retries a stop whose only
    content is reasoning, but in 18.5.0 such a stop after an earlier continuation or retry in the same run ends it
    with `agent_end.isTerminal: false` and exit 0. Seen in 3 Terminal-Bench runs on Strata v0.1.39; a scripted server
    reproduces it. **Fixed in 18.5.1.**
11. **A compiled binary extracts its ~175 MB native addon into each `HOME`.** The only redirect, `XDG_DATA_HOME`, also
    moves sessions and plugins, so isolated per-attempt homes kept one copy each; the integration deletes it after
    each attempt (`omp_strata.ompcfg.drop_native_cache`). **Fixed on `main`** by can1357/oh-my-pi#14735 (`8f905a5`,
    merged 2026-10-07): `PI_NATIVES_DIR` moves only the addon. No release contains it yet, so the integration
    keeps deleting the copy.
12. **Speculative compaction competes with the agent's own turn on a one-request provider.** In the band below its
    compaction threshold (12.5 % of the threshold, 8,192 to 32,000 tokens), OMP sends the session's model a
    background summary request. With `providers.maxInFlightRequests: 1`, which this integration sets because Strata
    serves one sequence, the agent's next turn waits behind that request, and the summary replaces the engine's live
    prefix. On the RTX PRO 6000 (G17, 18.8.0) the turn waited 17 s and then re-read all 105,748 of its tokens (Strata
    reported none reused; 15.4 s); the summary was never applied. Reproducer: `tests/mock/test_speculative_compaction.py`.
    The extra request went out with 18.4.10, 18.5.0 and 18.8.0; with 18.7.0 the next turn won the race. A scripted
    check without that race (2026-10-07, release binaries) shows it on 18.8.0 and 18.8.2 alike: the summary takes the
    only slot at the turn boundary and the next turn waits for all of it. Workaround here: `compaction.asyncEnabled:
    false` (OMP still compacts at the threshold). Not reported upstream yet; a fix could skip speculation on a provider
    limited to one in-flight request.

Re-checked on `main` `7ac4b18` (2026-10-07): items 2, 4 and 7 are still present; can1357/oh-my-pi#10934 and #13255
remain open. Item 7 was fixed on `main` later that day by #14737.

## Fifth tuple: Strata v0.1.36 / OMP 18.4.12 (host-free drafts, 2026-10-02)

<details>
<summary>2026-10-02 fifth-tuple release notes, stock planning floors, shard pins and host-free test results</summary>

On 2026-10-02 the release APIs resolved Strata `v0.1.36` to
`36fa455e579b23a9c909c2c6fe1bddd9e51cb8ca` and OMP `v18.4.12` to
`7318a70cf4ed04133366884d2723f72d9d490a15`. `scripts/upstream_watch.py report` found the four
newer releases below and resolved all 21 tracked issue/PR states. The five new profile ledgers remain
**draft, 24 gates `not_run`, no receipts**: no GPU host was used and the RAM upgrades are not assumed installed.

- [Strata v0.1.35 release notes](https://github.com/Niko1221/Strata/releases/tag/v0.1.35): Windows
  low-RAM resident mode frees the file cache before sizing residency and keeps the hottest experts that fit
  rather than falling back wholesale to SSD. Windows AMD loads its bundled HIP runtime; multi-GPU setup
  warns about a small second card limiting prompt chunks. Config writes are atomic, malformed `messages`
  become a 400, and `/metrics` gains draft counts. The Coder's weaker non-code/non-English behavior is
  explicitly documented upstream, supporting an unpruned Q2_0 draft rather than a quality claim here.
- [Strata v0.1.36 release notes](https://github.com/Niko1221/Strata/releases/tag/v0.1.36): Q2_0 uses
  fused int8 tensor-core prompt kernels on RTX 30 and newer by default. Upstream's speed/quality numbers
  are from its hardware, **not measurements of these profiles**; Q2_0 answers are intentionally not
  byte-identical to v0.1.35. RTX 50 long-context decode gains cluster kernels; IQ fused prompt kernels
  are opt-in. Cancellation logs and metrics now report the amount actually read; draft-head errors name
  smaller vocabulary alternatives. `expert_profile_save` / `--expert-profile-save` is new, **opt-in and
  off here**: learned expert-cache persistence is not part of this integration. The shipped expert
  profile and default CJK draft vocabulary stay pinned by the Strata source commit.
- **Never run `UPDATE.bat` or `update.sh`**, just as `START-HERE.bat` and `setup.sh` remain prohibited.
  Their convenient upstream update path changes source, Python packages, engine, model settings and
  draft vocabulary in place. This repository instead creates a new pinned profile, root and ledger.
- Source comparison v0.1.34 → v0.1.36 found five new quoted environment names: `STRATA_ARGMAX_MULTI`,
  `STRATA_PF_FUSED`, `STRATA_PF_FUSED_NATIVE`, `STRATA_PF_FUSED_TILE`, `STRATA_QSA_CLUSTER`.
  `server_env` strips **all inherited `STRATA_*`** and explicitly supplies the key; none of these
  knobs passes through. Changing kernel defaults, the draft vocabulary, expert profile or any other
  tuning option requires a reviewed new profile, never an ambient environment override.
- [OMP 18.4.11 release notes](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.11): malformed
  JSON for lenient tools such as `yield` is reported to the model instead of running with empty
  arguments; unrelated projects no longer inherit the default home's project configuration. Other
  relevant changes include Windows paste, FIFO/device read refusal and subagent MCP deadlines.
- [OMP 18.4.12 release notes](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.12): reduced
  streaming overhead, Windows session-path import and temp-cleanup fixes, and eval wait/dead broker
  fixes. Its new auth-gateway stdio mode is **not used here**: stock OMP still calls stock Strata
  directly over Chat Completions, with no gateway or fallback provider.

### Pins and stock planning evidence

The source checklist changed only `MIN_ENGINE` among the six audited setup constants: `MIN_DRIVER=580`,
`CUDA_WHEELS`, `PY_PACKAGES`, `LLAMA_CPP_COMMIT` and `HF_REVISIONS` are unchanged. Both tags'
`requirements.txt` blob is `3db8418ab428ea10f4b607b693cf6ad030fd0509`, so the existing
`locks/strata-python-cp313-win_amd64-strata0.1.31.txt` is reused with its original hash, not rewritten.
The same **11** top-level config keys are generated and the server route set is unchanged, with no
unclassified routes. Stock setup's pure choices/config arithmetic were evaluated at the requested
contexts: no low-RAM, context reduction or RoPE extension was needed.

| Draft variant | Context / OMP declared window | Total RAM floor / available at start (GiB) | Free disk floor (GiB) | Stock RAM thresholds |
|---|---|---|---|---|
| Coder IQ1_M, RTX 5090 | 131,072 / 130,048 | 45 / 34 | 90 | Low-RAM below 33.4; KV streaming from 34.7994 |
| Coder IQ1_M, RTX 3090 / 4090 | 131,072 / 130,048 | 60 / 34 | 90 | Low-RAM below 33.4; KV streaming from 34.7994 |
| Coder IQ1_M, RTX 4090 | 262,144 / 261,120 | 60 / 36 | 90 | KV streaming from 36.5987 |
| Unpruned Q2_0, RTX 4090 | 131,072 / 130,048 | 60 / 50 | 107 | Arena 34.0; low-RAM below 44.0; KV streaming from 50.7994 |

All five use stock `--kv-resident 32768`. Every floor is the **maximum of the predecessor's floor
and the setup-derived estimate**, never the purchased 128/192 GB. Predecessor floors preserve
operational headroom for observed integration-root sizes and engine peaks that setup's estimates
do not capture; a tuple bump may raise these constraints, never lower them. The draft JSON reports
both inputs and the selected floor. Setup estimates round up its low-RAM/streaming thresholds and
`ram_gb + KV`; the disk estimate uses exact shards (at least setup's estimate) plus setup's 8 GB
preparation allowance, converted to GiB.
Q2_0 conservatively includes its 40 GB AVX-512 conversion branch so the floor remains safe on either
CPU. These are preflight floors, not real-host capacity/performance evidence. `omp.context_window`
equals the configured engine context; `ompcfg.CONTEXT_SAFETY_TOKENS=1024` is subtracted when rendering
the route, not twice in the profile.

The release API pins `strata-windows-x64.zip` to **124,993,467 bytes**, SHA-256
`dfe40817661a4286f2a94b86452aef5eae54d8c0f23429868449b06086f4c266`; the OMP assets are
`omp-windows-x64.exe`, `omp-darwin-arm64` and `omp-linux-x64` (their API sizes/digests are in every
profile). No engine archive or model was downloaded. Q2_0 uses stock setup's
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` revision
`ed59f92082b1e93c0e96d60a8b11aab089b52f09`:

| Shard under `Q2_0/` | Bytes | Hugging Face LFS SHA-256 |
|---|---:|---|
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` | 37,623,740,192 | `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` |
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` | 28,800,138,432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |

Coder and Q2_0 both use `Qwen/Qwen3.8-Flash-Next` MTP revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`, resolved live, with the unchanged pinned tensor-manifest
digest `ced6fb728a94374d1fcbd1938b6543cf8ecb0a936d923cd3eca4923282a814b6`. No separate unpinned
draft model is introduced; stock setup builds the same Q2_0 MTP layer and copies the source-pinned
default draft vocabulary.

### Host-free run (2026-10-02)

The fifth-tuple dev-env provisioned the real Darwin ARM64 OMP binary and pinned Strata source.
`tests.unit.test_upstream_watch`: **13 tests, OK** (fixture transports, no network; includes the
nondecreasing host-floor regression); under the new
dev-env, `tests.unit.test_strata_surface tests.unit.test_profile`: **10 tests, OK**. All five profiles
validated, their release manifests verified, and `--require-ready` refused all five as intended.

A first mock-tier run under that dev-env, taken while the client-route tests were still being written, failed
three of them (a closed tunnel's TIME_WAIT mistaken for an occupied listener); the G04 truncated-call and
composed-cutoff cases passed. After those fixes the whole host-free suite ran once in each CI lane on
2026-10-02 (macOS arm64, sequentially):

| OMP binary / Strata source | Result |
|---|---|
| 18.4.6 / v0.1.30 | 188 tests OK (4 expected failures: the G04 defects of those versions) |
| 18.4.8 / v0.1.31 | 188 tests OK (1 skipped, 2 expected failures) |
| 18.4.10 / v0.1.34 | 188 tests OK (1 skipped) |
| 18.4.12 / v0.1.36 | 188 tests OK (1 skipped) |

The existing version thresholds in `tests/candidate.py` already select the right G04 expectations for
18.4.12/v0.1.36. No GPU gate ran.

</details>
