# Security boundary

OMP Strata runs one stock Strata server on loopback (`127.0.0.1:18090`) behind a required API key for one local user
and drives it with the stock Oh My Pi (OMP) client, or reaches that loopback server from another machine through an
optional qualified SSH local forward. It is a single-user route: it is not a multi-tenant service, an OS sandbox or an
egress firewall.

Everything below was observed on the qualification host (G02/G04 on the mock tier, G13 on the real host) unless it is
marked as a source reading. The current qualified server profiles run stock Strata v0.2.13 (engine 0.1.59) + OMP
18.18.3 across all three hosts: on the RTX PRO 6000 (`rtxpro6000-win-a`),
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` is current (IQ3_S at
262,144 tokens, four batch slots with per-slot stock DFlash2 drafters via `strata.drafting: "dflash2"` under engine
0.1.59's `STRATA_BATCH_DF2`, one 85 MiB slot drafter per slot, stock v0.2.13 window 8 `--spec 8`, no `--batch-mtp`,
packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files with `STRATA_NO_ACQUIRE=1`, direct per-layer
embedding (PLE) reads `--ple-io direct` via `strata.ple_io: "direct"`, KV in VRAM `--kv-streaming off` via
`setup_args.kv_streaming: "off"`, and stock `parallel_stack` and `gdn_stack` in `strata.engine_env`, qualified on
2026-11-09, published `2af52b8`, under the owner's override `"Override the base as current, and also qualify the tuned
pack as an alternate"` of its 11 of 90 window-8 burstiness A/B misses against v0.2.12), alongside its qualified
non-current alternate
`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` (pins stock's
tuned DFlash2 release asset `qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack` via `model.dflash2_source.tuned`,
which stock v0.2.13 runs at `--spec 8` and `--draft-conf 0.55` on this card, qualified on 2026-11-09, published
`8ab88b0`, as an alternate under the same owner decision after 15 of 90 A/B misses against v0.2.12; not the rollback),
rolling back to its qualified v0.2.12 DFlash2 predecessor
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` (`--spec 6`, 8,192 MiB
automatic conversation cache, and 83.13 GiB G10 Windows commit headroom of a 219.70 GiB limit with 126.94 GiB available
RAM; the v0.2.12 `df2tuned` alternate at 83.24 GiB commit headroom, the v0.2.11 `df2` profile at 83.55 GiB, the
v0.2.11 `batchmtp` profile at 81.73 GiB, the v0.2.10 `kvvram-envpg` profile at 83.05 GiB, the v0.2.9 `kvvram-envpg`
profile at 83.35 GiB, the v0.2.9 `slots4-batchmtp-pledirect-parking` base and the v0.2.8 profiles stay earlier
qualified history); on the RTX 5090 (`rtx5090-win-a`),
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` is the 262K default (34 GiB available-RAM
start floor via `setup_args.kv_streaming: "off"`, elastic KV growth `--kv-grow` via `strata.kv_grow: true`, stock
`gdn_stack` in `strata.engine_env`, passing all 88 of 88 checks in its v0.2.13 vs v0.2.12 A/B and every gate in its
requalify chain on 2026-11-09, published `d3c96fb`; requires the host's Docker Desktop and WSL, which run its
production NInfer container, to be stopped, and after WSL restarts that container is restored with a new
`"WSL integration ... provisioned"` line, fleet return and health 200), rolling back to its v0.2.12 predecessor
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0` (4,096 MiB automatic conversation cache,
19.53 GiB G10 commit headroom of an 85.15 GiB limit with 13.05 GiB available RAM; the v0.2.11 `kvvram-kvgrow-envg`
profile at 4,352 MiB cache and 20.30 GiB commit headroom, the v0.2.10 `kvvram-kvgrow-envg` profile at 20.31 GiB, the
v0.2.9 `kvvram-kvgrow-envg` profile at 20.10 GiB, the v0.2.9 `coder-iq1m-262k` base and the v0.2.8 262K profiles stay
earlier qualified history), `win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3` is the 131K Coder qualified
alternative (34 GiB start floor; starts with Docker Desktop and WSL running; follows the 262K pass without a separate
A/B, as in v0.2.12, and passes every gate on 2026-11-09, published `d0c2e28`), rolling back to its v0.2.12 (engine
0.1.58) + OMP 18.18.0 predecessor `win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0` (3,584 MiB cache and
18.72 GiB commit headroom of an 85.15 GiB limit with 11.37 GiB available RAM in the Docker Desktop/WSL-stopped window;
`win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0` failed G15 twice on 2026-11-06 and stays unqualified, while
`v0.2.10` at 18.56 GiB commit headroom, `v0.2.9` and `v0.2.8` 131K stay earlier qualified history), and
`win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3` is a qualified non-current full-model IQ3_S 131K low-RAM
resident alternate (stock's planner pick for this host, `--resident-experts`, 36 GiB available-RAM start floor, 11,616
expert slots in VRAM at 22.04 GiB and 29.77 GiB of experts page-locked in RAM, passing every gate on 2026-11-09,
published `6e2dda2`, after deleting five superseded roots on `rtx5090-win-a` for disk, `C:` `98.1` -> `156.6 GiB`
free; the Coder stays the default); and on the `rtx3090-win-a` RTX 4090 + RTX 3090 pair,
`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`
is current (IQ3_S at 262,144 tokens, stock roles with RTX 4090 as Main staged last, manual split 24 `--layer-split 24`,
stage dense-weight trim `--trim-stage-weights` via `strata.trim_stage_weights: true`, stock DFlash2 drafter alone via
`strata.drafting: "dflash2"` packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files with
`STRATA_NO_ACQUIRE=1` and `strata.drafting_args: {"--draft-conf": "0.5"}` written to stock `user_args`, no
`--pipeline-windows 2`, no batch slots, display on the RTX 4090, `strata.ple_io: "direct"` pinning `--ple-io direct`,
and the engine's `sm_86` default table `sm86_table`, stock `gdn_stack` and exact two-pass QSA block selection
`select_two_pass` `STRATA_SELECT_TWO_PASS=1` in `strata.engine_env`; its id drops `-parking` only to stay within 120
characters and keeps the same stock tips; qualified on 2026-11-09, published `440fa1b`, under the owner's decision
`"Run the --draft-conf 0.5 main; it becomes current if every gate passes"` after passing all 96 plain checks against
v0.2.12 and every gate in its own chain once `fb8740a` fixed install verification for stock setup re-runs carrying
`user_args` into `args`), rolling back to its qualified v0.2.12 `env86gt` predecessor
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`
(19.40 / 17.90 GiB expert caches, 8,192 MiB automatic conversation cache, and 28.21 GiB G10 serving Windows commit
headroom of a 135.69 GiB limit with 65.74 GiB available RAM; the v0.2.12 `env86g` profile at 19.40 / 17.90 GiB expert
caches and 28.18 GiB commit headroom, the v0.2.11 `df2` profile at 19.41 / 17.90 GiB and 28.70 GiB, the v0.2.10 `df2`
profile at 19.41 / 18.31 GiB and 27.51 GiB, the v0.2.10 `pw2` `env86g` MTP sibling at 19.14 / 17.75 GiB and 27.54 GiB,
and the v0.2.9 and v0.2.8 profiles stay earlier qualified history). The five v0.2.13 drafts with `"Not qualified"`
blockers (recorded in `b2e9730`) — the pair's unpinned `env86gt` base draft
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`,
6 of 96 A/B misses on one 32K request) and `STRATA_QSA_SPLIT_ATTN` `env86gts` draft
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3`,
2 of 96 misses and targeted cold decode `1.003 < 1.02`), the RTX 5090's `STRATA_SPEC_COST` `envgc` draft
(`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3`, 3 of 88 misses and 2 of 88 on
replacement pairs) and full-model IQ3_S 262K low-RAM screen draft
(`win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`, whose first start refused with
`"strata.kv_grow: elastic K/V line absent from this start's engine-log interval"`, ledger-receipts check `a7762aa`),
and the PRO's standard pack + `--draft-conf 0.55` `df2conf055` draft (withdrawn before install) — along with the PRO's
v0.2.12 two-pass draft
(`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0` and its route
`client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0`), the RTX 5090's v0.2.12 two-pass draft
(`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`, whose published ledger keeps its G18
failure after 40 read turns reached 207,269 tokens without compacting), the pair's v0.2.12 W4A8 draft
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0`),
the PRO's comparison-only v0.2.11 quality-first one-slot `IQ3_S`
(`win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`), one-slot `UD-Q5_K_XL`
(`win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`) and six-expert
`DeepSeek-V4.1-Flash-1017` `IQ2_XS` (`win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0`) drafts,
v0.2.11 four-slot `UD-Q4_K_XL` screen (slower than the v0.2.11 IQ3_S profile in every measured workload: single-request
decode 0.85-0.91x, total throughput 0.73-0.84x) and v0.2.9 `UD-IQ4_XS` and `NVFP4-QAD` model candidate drafts (and their
routes), the RTX 5090's unpinned-GDN v0.2.9 `kvvram-kvgrow` fallback draft, the pair's measurement-only v0.2.8
stock-residency roles draft, the held v0.2.7 roles draft with PLE in RAM (G10 commit headroom 1.03 GiB, conversation
cache off; [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)), the unmeasured v0.2.7 default-split
draft, the default and split-32 v0.2.3 pair drafts and the v0.1.44.1 pair release remain draft, not qualified
([decision](DECISION.md)). Model pins, contexts and security boundaries stay unchanged.
<details><summary>Earlier tuples and hardware rollback constraints covered in this document</summary>

- Where the first two candidates differ (stock Strata v0.1.27 + OMP 18.4.0 against v0.1.30 + 18.4.6), both are stated.
- Later tuples are named where they change something: the third tuple (Strata v0.1.31 + OMP 18.4.8, two 24 GB hosts),
  the fourth (Strata v0.1.34 + OMP 18.4.10, three hosts), the RTX PRO 6000 tuples (Strata v0.1.40.2 + OMP 18.8.0, and
  Strata v0.1.40.3 + OMP 18.8.3 with batch slots and conversation parking), the Strata v0.1.40.3 + OMP 18.8.4 tuple (the
  RTX PRO 6000 with slots and parking, the RTX 5090 and the single-card RTX 3090), the Strata v0.1.41 + OMP 18.8.6
  tuple on the RTX PRO 6000 with slots and parking and the RTX 5090, the earlier Strata v0.1.42 + OMP 18.8.9 and
  Strata v0.1.43 + OMP 18.10.1 tuples, Strata v0.1.43.1 + OMP 18.10.1, Strata v0.1.44.1 + OMP 18.10.1 (on the PRO and
  RTX 5090), Strata v0.2.1 (engine 0.1.46) + OMP 18.10.1 (earlier qualified history on every host; integration roots
  removed on 2026-10-28), Strata v0.2.3 (engine 0.1.48) + OMP 18.12.6 (earlier qualified history on every host; RTX
  5090 integration roots removed on 2026-11-02), Strata v0.2.7 (engine 0.1.52) + OMP 18.13.2 (earlier qualified history
  on every host), Strata v0.2.8 (engine 0.1.54) + OMP 18.14.0 (earlier qualified history on every host), Strata v0.2.9
  (engine 0.1.55) + OMP 18.15.0 (earlier qualified history on every host, with seven superseded `v0.2.3`–`v0.2.9` roots
  on the PRO and three `v0.2.8`/`v0.2.9` roots on the pair pruned on 2026-11-06), Strata v0.2.10 (engine 0.1.56) + OMP
  18.16.0 (earlier qualified history on the PRO `kvvram-envpg`, RTX 5090 262K `kvvram-kvgrow-envg` and 131K, and pair
  `df2` and `pw2` `env86g` profiles), Strata v0.2.11 (engine 0.1.57) + OMP 18.16.0 (earlier qualified history on the
  PRO `df2` and `batchmtp` profiles and Studio routes, the RTX 5090 262K `kvvram-kvgrow-envg` profile, and the pair
  `df2` DFlash2 profile; RTX 5090 131K unqualified after failing G15 twice), Strata v0.2.12 (engine 0.1.58) + OMP
  18.18.0 (the rollback on the PRO `df2` DFlash2 profile, its Studio route, the RTX 5090 262K `kvvram-kvgrow-envg`
  default and 131K Coder alternative, and the pair `env86gt` two-pass DFlash2 profile; earlier qualified history on the
  PRO `df2tuned` tuned-pack alternate and its Studio route and on the pair `env86g` DFlash2 profile), and current
  Strata v0.2.13 (engine 0.1.59) + OMP 18.18.3 on the PRO (`df2` DFlash2 current and `df2tuned` tuned-pack alternate,
  plus their Studio routes), the RTX 5090 (262K `kvvram-kvgrow-envg` default, 131K Coder alternative, and full-model
  IQ3_S 131K low-RAM resident alternate; five superseded `rtx5090-win-a` roots pruned on 2026-11-09) and the pair
  (`df2conf05` `--draft-conf 0.5` two-pass DFlash2 current).
- The pair's qualified display-on-RTX-3090 predecessor is rollback only after restoring that display placement. The
  single-card RTX 3090 profiles stay qualified for single-card hosts, but are not rollbacks on `rtx3090-win-a` while
  both cards are installed.

</details>

## Server exposure

- **Loopback listener only.** Strata listens on `127.0.0.1:18090` only (G10: the only listener on the port is owned by
  the integration's process tree). `0.0.0.0` is not supported. Remote clients reach it only through a client route over
  an authenticated loopback-to-loopback SSH forward (below). The Mac Studio's current route to the RTX PRO 6000 262K
  v0.2.13 `df2` DFlash2 profile (`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`) and its
  qualified non-current alternate route to the `df2tuned` tuned-pack profile
  (`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`) are each qualified by G23 on their
  own ledgers; the v0.2.12 `df2` DFlash2 route
  (`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`) is the rollback, while the 0.2.12
  `df2tuned`, 0.2.11 `df2` and `batchmtp` `kvvram-envpg`, 0.2.10 `kvvram-envpg`, 0.2.9 `kvvram-envpg`, 0.2.9 batch-MTP
  base, 0.2.8 batch-MTP, 0.2.8 `slots4-parking`, 0.2.7, 0.2.3, 0.2.1, 0.1.44.1, 0.1.43.1, 0.1.43 and 0.1.42 262K and
  0.1.41 131K routes remain earlier qualified history. No fleet route is published.
- **Server environment subtraction and state-path isolation.** The server's environment is the operator's environment
  minus every variable whose name looks like a secret (`KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`) and minus every
  inherited `STRATA_*` variable: those are the engine's tuning and debug switches (v0.1.31 alone added 16), and a setting
  changes only through a new profile. The API key is then added explicitly, along with (on engine 0.1.57+)
  `<root>\state\strata-runtime` as `STRATA_RUNTIME_DIR` and `<root>\localappdata` as `LOCALAPPDATA` so stock Strata's
  activity lease (`%LOCALAPPDATA%\Strata\runtime`) and process records (`%LOCALAPPDATA%\Strata\procs`) stay inside the
  profile's own root.
- **API key generation and storage.** `keygen` writes a 32-byte random key to `<root>\state\strata-api-key`, restricted
  to the current user (`icacls /inheritance:r`); `start` refuses a missing, blank or short key. The key reaches the
  server only through the detached `serve` wrapper's environment. It is never put on a command line, printed, logged or
  committed.
- **Route authentication and config guard.** Every model, control, metrics, telemetry and MCP tool-media route needs
  the API key (`Authorization: Bearer` or `x-api-key`), while `/health`, `/api/health` and `/` stay public.
  `tests/unit/test_strata_surface.py` fails when a pinned server routes a path G13 does not probe, and install accepts
  only the config keys every pinned setup writes (`"parallel"` only as a profile's pinned batch slots, v0.2.3+'s
  `gpu_roles` and `gpu_order` only as a profile's pinned stock roles, engine 0.1.52+'s `--ple-io direct` only when
  `strata.ple_io: "direct"` is pinned, engine 0.1.54+'s `--batch-mtp` only when `strata.batch_mtp: true` is pinned on
  one card with batch slots, engine 0.1.54+'s `--trim-stage-weights` only when `strata.trim_stage_weights: true` is
  pinned on a two-card manual layer split, engine 0.1.55+'s config `env` only when `strata.engine_env` pins complete
  reviewed stock value groups on a reviewed engine in `ENGINE_ENV_REVIEWED_ENGINES` (`0.1.55`, `0.1.56`, `0.1.57`,
  `0.1.58` and `0.1.59`, including the v0.2.12 `select_two_pass` and `iq4nl_w4a8` groups on `0.1.58+` and the v0.2.13
  `spec_cost` and `qsa_split_attn` groups on `0.1.59+`; or `strata.setup_env` on the reviewed `UD-IQ4_XS` lane), engine
  0.1.55+'s `--kv-streaming off` removing `--kv-resident`
  only when `setup_args.kv_streaming: "off"` is pinned on one card, engine 0.1.55+'s `--kv-grow` only when
  `strata.kv_grow: true` is pinned alongside `--kv-streaming off` on one card, engine 0.1.56+'s config
  `drafting: "dflash2"` only when `strata.drafting: "dflash2"` is pinned with `model.dflash2_source` packed offline under
  `STRATA_NO_ACQUIRE=1` (including with batch slots on engine `0.1.57+`, where start requires one slot drafter per batch
  slot, with `model.dflash2_source.tuned` on engine `0.1.58+`, where a stray tuned pack in a standard-pack root is
  refused before launch, and with `strata.drafting_args` on engine `0.1.59+`, where one `--draft-conf` value from
  stock's CUDA domain is written to stock `user_args` with stock `write_config` and required on the start's server line),
  and v0.2.1+'s `args_written` only when equal to `args` with no unpinned `user_args` (a stock v0.2.13 setup re-run's
  carried `user_args` in `args` is accepted only when each pinned option occurs once with its exact pinned value,
  `fb8740a`)), so CORS origins,
  the monitor, `telemetry_read_key` or lazy loading cannot be switched on by a generated config.
- **Batch slots and conversation parking.** On the current RTX PRO 6000 profile (and its `df2tuned` alternate and
  v0.2.12 `df2` rollback) the server decodes up to four requests at once (each slot with its own 85 MiB DFlash2 drafter
  under `STRATA_BATCH_DF2`, or its own MTP drafter state under `--batch-mtp` on earlier batch-MTP profiles), and OMP may
  send it four; they come from the one local user's OMP processes. Parking keeps up to four recent conversations' engine
  state in host RAM inside the engine process (from engine 0.1.48 in v0.2.3, engine 0.1.52 in v0.2.7, engine 0.1.54 in
  v0.2.8, engine 0.1.55 in v0.2.9, engine 0.1.56 in v0.2.10, engine 0.1.57 in v0.2.11, engine 0.1.58 in v0.2.12 and
  engine 0.1.59 in v0.2.13,
  sized automatically by the engine from the RAM free after load: 8,192 MiB on the PRO on v0.2.12 `df2` and `df2tuned`,
  v0.2.11 `df2` and `batchmtp`, v0.2.10, v0.2.9, v0.2.8, v0.2.7 and v0.2.3 and on the pair on v0.2.12 `env86gt` and
  `env86g`, v0.2.11 `df2`, v0.2.10 `df2` and `pw2` `env86g`, v0.2.9 and v0.2.8 split-24 trim + PLE-direct, v0.2.8 and
  v0.2.7 PLE-direct and v0.2.3 roles; 4,864 MiB on the measurement-only v0.2.8 pair stock-residency draft; 4,096 MiB on
  the RTX 5090 262K `kvvram-kvgrow-envg` default on v0.2.12, 4,352 MiB on the unqualified v0.2.12 `envgt` two-pass draft
  and on the RTX 5090 262K `kvvram-kvgrow-envg` default on v0.2.11, v0.2.10 and v0.2.9, 3,584 MiB on the RTX 5090 131K
  alternative on v0.2.12 and v0.2.10 in the Docker Desktop/WSL-stopped window, 3,072 MiB on the v0.2.9 262K base profile
  and 3,840 MiB on the v0.2.9 131K alternative in the Docker Desktop/WSL-stopped window; 3,584 MiB on the RTX 5090 262K
  default on v0.2.8 and 4,096 MiB on the 131K alternative in the Docker Desktop/WSL-stopped main chain; 1,792 MiB on the
  RTX 5090 262K on v0.2.7 with Docker Desktop and WSL stopped; 1,024-1,280 MiB on the RTX 5090 131K on v0.2.3; and off
  on the held pair v0.2.7 roles draft after locking the 26.8 GiB PLE table in RAM, on the RTX 5090 131K on v0.2.7 while
  the host's resident Docker Desktop/WSL VM held RAM, and on the RTX 5090 262K on v0.2.3). Nothing is written to disk,
  and the state goes when the engine stops. A conversation is restored only for a prompt that starts with exactly its
  tokens.
- **Vision off.** Vision is off in this profile. Stock Strata can fetch `image_url` values (HTTP(S) or local paths)
  when vision is on, so enabling vision needs its own review (G22).

<details><summary>G13 route probes and historical Strata v0.1.27–v0.1.30 authentication observations</summary>

- **G13 route probe scope.** G13 checked `GET /v1/models /models /props /metrics /settings /slots /v1/status /mcp`
  (plus `/status` on the second candidate) and `POST /v1/chat/completions /v1/messages /settings`: no key and wrong
  keys get 401, and the correct key gets 200 (the mutating `POST /settings` was only tried without a valid key). Shared
  server settings stayed at the frozen empty defaults. On the fourth tuple G13 also sent missing and wrong keys to
  `POST /load /unload /v1/load /v1/unload /v1/messages/count_tokens` (401 on all three hosts; stock checks the key
  before it routes any POST), found the opt-in request monitor absent (`/api-monitor` and `/api/requests` 404 with the
  key) and a CORS preflight answered 204 without `Access-Control-Allow-Origin`; `/health`, `/api/health` and `/` stay
  public. On the RTX PRO 6000 tuple G13 also refused missing and wrong keys on `GET /config` and on
  `POST /config /slots/ /v1/responses /v1/vram` (401), and the egress trace recorded zero non-loopback events among
  2,416 attributed ones (2,796 on the slots-and-parking profile). On v0.2.1 (engine 0.1.46), v0.2.3 (engine 0.1.48),
  v0.2.7 (engine 0.1.52), v0.2.8 (engine 0.1.54), v0.2.9 (engine 0.1.55), v0.2.10 (engine 0.1.56), v0.2.11 (engine
  0.1.57), v0.2.12 (engine 0.1.58) and v0.2.13 (engine 0.1.59) G13 also probes the authenticated `GET /v1/telemetry`
  (which arrived in v0.2.0-beta, engine 0.1.45.3; the read-only telemetry key from the environment is scrubbed and
  config `telemetry_read_key` is refused by install) and sends missing and wrong keys to the key-only
  `POST /v1/v1/messages` and `POST /v1/v1/messages/count_tokens` Anthropic aliases (401); on v0.2.7 (engine 0.1.52),
  v0.2.8 (engine 0.1.54), v0.2.9 (engine 0.1.55), v0.2.10 (engine 0.1.56), v0.2.11 (engine 0.1.57), v0.2.12 (engine
  0.1.58) and v0.2.13 (engine 0.1.59) G13 also probes
  the key-gated `GET /tool-media/` route (401 without or with a wrong key, 404 with the valid key because Strata-side
  MCP is unconfigured; on v0.2.12, 0 non-loopback network events among 4,664 attributed ETW events on the PRO `df2`
  DFlash2 current profile, 4,148 on its `df2tuned` tuned-pack alternate, 9,775 on the RTX 5090 262K `kvvram-kvgrow-envg`
  default, 6,461 on the RTX 5090 131K alternative, 10,170 on the unqualified RTX 5090 262K `envgt` two-pass draft, 4,163
  on the pair `env86gt` two-pass current profile, and 5,135 on its v0.2.12 `env86g` rollback profile; on v0.2.11, 0
  non-loopback network events among 4,916 attributed ETW events on the PRO `df2` DFlash2 rollback profile, 9,365 on its
  `batchmtp` `kvvram-envpg` profile, 6,493 on the RTX 5090 262K `kvvram-kvgrow-envg` rollback, 6,862 on the initial pair
  `df2` DFlash2 attempt and 3,436 on its passing `611c342` rerun, and 6,419 on the unqualified RTX 5090 131K candidate;
  on v0.2.10, 0 non-loopback network events among 8,549 attributed ETW events on the PRO `kvvram-envpg` profile, 4,883 on
  the RTX 5090 262K `kvvram-kvgrow-envg` profile, 10,365 on the RTX 5090 131K rollback, 2,981 on the pair `df2` DFlash2
  profile,
  and 9,344 on the pair v0.2.10 `pw2` `env86g` profile; on v0.2.9, 0 non-loopback network events among 4,709 attributed ETW
  events on the PRO `kvvram-envpg` profile, 8,003 on its v0.2.9 batch-MTP + PLE-direct base profile, 8,249 on the RTX 5090
  262K `kvvram-kvgrow-envg` profile, 2,791 on its v0.2.9 262K base profile, 6,985 on the RTX 5090 131K rollback, and 3,980
  on the pair v0.2.9 split-24 trim + PLE-direct base profile; on the 2026-10-31 v0.2.8 tuning profiles, 0 non-loopback
  network events among 3,839 attributed ETW events on the PRO batch-MTP + PLE-direct profile, 3,713 on the PRO PLE-direct
  alternative, and 3,932 on the pair split-24 trim + PLE-direct profile; on v0.2.7, 0 non-loopback events among 10,067
  attributed ETW events on the PRO, 4,397 on the RTX 5090 131K, 9,564 on the RTX 5090 262K, and 7,991 on the pair
  PLE-direct profile, plus 4,451 on the held pair roles draft).
- **Unauthenticated by design in stock Strata v0.1.27 (first candidate):** `/health`, `/status`, `/` (the web app) and
  its static assets. `/status` includes a `tail` of the text being generated, so any local process can read the end of
  the current answer without the key. Treat the host as single-user. Strata v0.1.28 puts `/status` behind the key and
  drops the tail when a request ends (Strata#212); on the second candidate (v0.1.30) G13 observed `/status` answering
  401 without the key, leaving `/health` and `/` public.
- **Empty-key and key-comparison behavior in stock Strata v0.1.27:** Stock Strata v0.1.27 **disables authentication
  when its key is empty** and compares keys with `==`, which is not constant-time; this is acceptable only because the
  listener is loopback-only. Strata v0.1.28 and later (second candidate) refuse an explicitly empty key and compare keys
  in constant time (Strata#213; an absent key still means no authentication, so the launcher's refusal stays).

</details>

## Remote client routes and fleets

Design and commands: [`REMOTE.md`](REMOTE.md).

- **Owned SSH tunnel.** The server side does not change: it still binds loopback only and requires its key. A client
  reaches it through `ssh -NT -L 127.0.0.1:<local>:127.0.0.1:<server>` run as an argv-only child of the foreground
  `launch-omp`, with `BatchMode=yes`, `ExitOnForwardFailure=yes` and multiplexing/background-after-authentication
  disabled. The child lives in an owned POSIX session or a Windows kill-on-close job and is torn down on every exit
  path; no forward outlives the session. An occupied local port is refused, never adopted.
- **Key transfer and binding provenance.** `pull-key` reads the host root's key over the SSH session's stdout (stdin
  closed) into a user-only file under the client root (`state/keys/<label>.key`); it never appears in argv, launcher
  errors, logs or receipts. A user-only `<label>.key.json` beside it binds the key's digest to the binding it came from
  (SSH alias, remote root, platform); after any binding change the launcher refuses with "binding changed since
  pull-key" until `pull-key` runs again. The client root holds the keys, the private bindings and the isolated OMP home;
  none of them belongs in the repository. Fetch, key pull and proof writers check the root identity and server-install
  exclusion before writes/network effects, recording a new identity under the client lock. Derived proof roots have the
  same check before keys are copied into them.
- **Established-peer verification and preflight.** Before OMP starts, the platform ownership query (`lsof` on macOS,
  `/proc` on Linux, `Get-NetTCPConnection` on Windows) must attribute every listener on the port, on any address
  including IPv4/IPv6 wildcards, to the SSH child. A stale listener sample never authorizes a launcher/probe request:
  its HTTPConnection first connects, then checks that the server half of that exact established TCP four-tuple belongs
  exclusively to the live SSH child, before sending any HTTP bytes. Failed or incomplete checks refuse credentials. A
  subsequent port rebind cannot replace the peer of that established connection. Before OMP starts, every member must
  pass `/health`, refuse unauthenticated `/v1/models` with 401, and match the pinned model id, exact Strata build,
  context and empty shared settings with the key. Preflight follows no redirects and ignores ambient proxies, so the
  bearer key cannot be forwarded to another origin.
- **Disconnect teardown and exit-to-kill window.** When an SSH child exits, a watcher kills OMP's process group
  (Windows: job) at once, with no grace period, to curtail retries into a listener that takes over the freed port. The
  turn in flight is lost; the transcript saved before it resumes explicitly. Nothing falls back to another provider.
  Stock OMP's own requests are not checked one by one (that would need a proxy or a fork): the remaining window is the
  time between the SSH child's exit and that kill. SIGINT/SIGTERM are deferred while a child is started or registered
  and while the session tears down; teardown attempts every tunnel and keeps the handle of any that failed to close.
  Group signals for a reaped leader are skipped if its PID now names a live process; otherwise descendant cleanup is
  preserved. Windows uses the owned job handle, not PID-based group signalling.
- **Fleet routing (design only; no fleet route is published).** A fleet adds one `strata-<label>` provider per host (one
  request in flight each). Stock OMP's `task.agentModelOverrides` routes the unmodified stock `task` (full coding tools)
  and `scout` (read-only tools) agents to a worker; only the extra named scouts are generated definitions, with `model:`
  pinned and tools limited to read/find/grep/glob (a mock-tier test with the real pinned OMP binary confirms their
  write, edit and bash attempts are refused). Every role still resolves to a Strata provider only.
- **Trust boundaries that stay with the operator:** the SSH client, its configuration (including any `ProxyCommand`) and
  host-key trust; model-generated tools, which run with the client user's privileges and can read whatever that user
  can, including the client root's key files, as tools on the server host can read the server key. The egress guard is
  defense in depth, not an OS firewall. Native Windows job containment has not run on a real client yet.
- **Qualified Mac Studio route and rollback observations.** The current Mac Studio route,
  `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`, pins the PRO's current
  `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` profile. Its
  independent G23 passed on 2026-11-09 (`2af52b8`,
  [ledger](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3/qualification.json)):
  missing key refused before launch, wrong key refused with HTTP 401, health RTT 5.8-7.7 ms, stream TTFT 0.217 s
  through the tunnel, the turn in flight failing on tunnel drop with the transcript preserved, and a one-turn
  `launch-omp` smoke answering `"ROUTE OK"`
  ([restored-state](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3/restored-state.json),
  `ab96ab4`). TTFT includes server work, not SSH-only overhead. Its qualified non-current alternate route,
  `client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`, pins the PRO's qualified v0.2.13
  `df2tuned` tuned-pack alternate; its independent G23 passed on 2026-11-09 (`8ab88b0`,
  [ledger](../releases/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3/qualification.json)):
  missing key refused before launch, wrong key refused with HTTP 401, health RTT 6.1-6.8 ms, stream TTFT 0.181 s
  through the tunnel, the turn in flight failing on tunnel drop with the transcript preserved, and a one-turn
  `launch-omp` smoke answering `"ROUTE OK"`
  ([restored-state](../releases/client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3/restored-state.json),
  `ab96ab4`). Its qualified rollback,
  `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`, pins the PRO's v0.2.12 262K `df2` DFlash2
  rollback; its independent G23 passed on 2026-11-07 at `243290e`
  ([receipt](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0/receipts/6b5c7e35b9344a3c86767be8cb2321dc.json)):
  missing key refused before launch, wrong key refused with 401, health RTT 5.9-7.4 ms, stream TTFT 0.247 s through the
  tunnel (vs 12.1-16.1 ms and 0.317 s on the earlier v0.2.12 `df2tuned` alternate route at `2560f77`, 6.0-10.1 ms and
  0.270 s on the v0.2.11 `df2` route at `b812df9`, 5.3-6.5 ms and 0.174 s on the v0.2.11 `batchmtp` `kvvram-envpg`
  route, 21.9-24.4 ms and 0.219 s on the v0.2.10 `kvvram-envpg` route, and 5.5-6.3 ms and 0.172 s on the v0.2.9
  `kvvram-envpg` route), the turn in flight failing on tunnel drop with the prior transcript preserved, nonce recall
  from transcript replay after tunnel reopen (0.87 s), client restart (0.79 s) and verified server restart (2.56 s,
  changed server instance), and a one-turn `launch-omp` smoke answering `ROUTE OK` with owned stop. The 0.2.12
  `df2tuned`, 0.2.11 `df2` and `batchmtp` `kvvram-envpg`, 0.2.10 `kvvram-envpg`, 0.2.9 `kvvram-envpg`, 0.2.9 batch-MTP
  base, 0.2.8 batch-MTP, 0.2.8 `slots4-parking`, 0.2.7, 0.2.3, 0.2.1, 0.1.44.1, 0.1.43.1, 0.1.43 and 0.1.42 262K routes
  and the 0.1.41 131K route stay earlier qualified history. Each route keeps its own ledger and independently qualified
  server.

## Client isolation (`launch-omp`)

- **Isolated profile and home.** OMP runs with a named profile (`omp-strata`) in an isolated
  HOME/USERPROFILE/APPDATA/TEMP under the root. Your normal `~/.omp` is never read or written. G20 checked that the
  user's `.omp` directory had no change after the integration root was created (or since the requalify run start from
  `837bc89`), and that stock Strata's `%APPDATA%\Strata` was never created.
- **Client environment allowlist.** The environment is an allowlist (PATH, system roots, locale). Provider API keys,
  tokens, proxies, OTEL exporters, `NODE_OPTIONS`, shell startup files and credential sockets are dropped (unit and mock
  tests).
- **Pinned model roles.** Every OMP model role (default, smol, slow, plan, commit, task, advisor, judge, ...) is pinned
  to the profile's model on `strata-local` (`qwen3.8-flash-next-iq3_s` on the RTX PRO 6000, the pair and the RTX 5090
  IQ3_S 131K low-RAM alternate, `qwen3.8-flash-next-coder-iq1_m` on the Coder profiles). The route census over every
  session made during qualification
  found only that provider and model (G13), including OMP compaction's summarization calls (G13, G18; on OMP 18.17.0+,
  discarded assistant turns journaled with purpose `discarded-turn` are excluded from G18's `auxiliary_calls` check while
  still counted in billed usage, `8c2af4b`).
- **Discovery and background self-update disabled.** Extension, skill, rule, LSP, title and project-MCP discovery are
  off, and the generated config pins `update: {auto: false}` and `startup: {checkUpdate: false, setupWizard: false}` so
  OMP 18.17.0+'s setup wizard and background self-update stay off (`8c2af4b`); flags that would override the provider,
  model, profile, config or extensions are refused by the launcher.
- **Missing-key refusal.** The launcher refuses a missing or blank key before starting OMP, because **stock OMP (18.4.0
  and 18.4.6) sends the literal text `Bearer STRATA_API_KEY` when the key variable is unset**, instead of failing.

## Network egress

- **Loopback proxy guard.** The launcher sets `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` to a closed loopback port
  (`127.0.0.1:9`) and `NO_PROXY` to loopback. The Strata route stays direct. OMP's catalog fetch and any HTTP from tools
  the model runs then fail locally.
- **This is not enforcement.** A process that ignores proxy variables (raw sockets, some tools) can still reach the
  network. No firewall rule was added, because the host's network policy is out of scope. For a hard guarantee, use a
  host or container that has no route out.
- **Observed egress with and without the guard.** With the proxy guard enabled, a test-scoped ETW trace
  (`Microsoft-Windows-Kernel-Network`, attributed by process) covered a typed tool turn plus a turn that forced an OMP
  compaction; it recorded 3,711 events for the OMP and Strata process trees and **zero non-loopback events** (G13).
  **Stock OMP contacts the internet at every start, whatever the settings** (observed without the guard on 18.4.0; on
  18.4.6 only the guarded run was traced, where the local-port probes below were still visible and the catalog opt-out
  request can1357/oh-my-pi#10934 remained open). Its background model registry refresh downloads the public model
  catalog (`catalog.stencil.so`, a models.dev mirror). It also probes the default local ports of other model servers:
  127.0.0.1:11434 (Ollama), :8080 (llama.cpp) and :1234 (LM Studio). With the plain isolated profile, an ETW trace of
  the OMP process tree showed 244 packet events to two non-loopback endpoints (G13 attempt 1). No prompt content is sent
  there (source reading: a GET for catalog metadata), but it is egress.

## Model-generated actions

- **User-privilege execution.** OMP executes tools (shell, edit, write) with your privileges. The integration adds no
  sandbox. Run it only on code and machines where that is acceptable.
- **Truncated tool-call handling (G04).** A cut on `finish_reason: length` is handled safely: OMP answers the call with
  an error result and does not run it. When the model ends its turn in the middle of a tool call, Strata v0.1.31 fixed
  its half (the call stays unfinished, its JSON open, and the answer ends with `stop`; Strata#231) and OMP 18.4.10 the
  other (can1357/oh-my-pi#13868: the call gets the parse error and is not run). G04 passes on the fourth tuple, both
  earlier RTX PRO 6000 tuples, the 18.8.4, v0.1.41 and v0.1.42 tuples (mock tier).

<details><summary>Historical G04 defect (pre-v0.1.31 / pre-18.4.10) and G24 operator-account deviation</summary>

- **Known upstream defect, fixed in the fourth tuple (G04).** When the model ends its turn in the middle of a tool
  call, stock Strata up to v0.1.30 closes the partial JSON and reports `finish_reason: tool_calls`, and stock OMP up to
  18.4.9 runs the tool with the truncated arguments: a partial file write happens and the run exits 0. The first and
  second candidates and the third tuple still have the defect.
- **G24 operator-account deviation.** The bounded evaluation (G24) ran under the host operator's account without an OS
  sandbox, for both candidates, the third tuple's 24 GB hosts, the fourth tuple's three hosts, the RTX PRO 6000, the
  18.8.4 tuple's three hosts, the v0.1.41 tuple's two hosts and the v0.1.42 tuple's three. This was a recorded
  deviation, approved by the owner, from the packet's restricted-account rule (for the 24 GB hosts, as part of handing
  them over for the overnight runs); the later runs used the same arrangement under the owner's go-ahead for each
  qualification.

</details>

## Supply chain

- **Pinned artifacts.** Every downloaded artifact is pinned by URL, size and SHA-256 in the profile, and verified
  before it is promoted from `.partial`. Only HTTPS downloads are accepted.
- **Guarded stock setup and hash-locked wheels.** Stock `setup.py` runs unmodified, but only after every input is local
  and verified. Python packages are installed with `--require-hashes --no-index` from the committed lock, which for
  v0.1.31 is resolved from its pinned `requirements.txt`. (The stock `setup.py` up to v0.1.30 would otherwise fetch the
  latest release, `main` model revisions and unpinned PyPI packages; Strata#214; v0.1.31 pins all three.)
- **Binary provenance limitation.** The Strata engine binary is a maintainer-uploaded release asset with no build
  attestation. Its bytes are pinned, but it is not rebuilt from source here.
- **Hosted CI and hygiene scan.** CI is hosted, runs host-free tests with read-only permissions and pinned actions, and
  has no access to GPU hosts or secrets. A public-hygiene scan (tracked files and history) blocks commits that contain
  private host details.
