# Measurements

Dated real-host measurement records, methods, denominators and caveats for OMP Strata:
*Oh My Pi (coding-agent client) → OMP Strata (profile, lifecycle tool, evidence) → Strata (inference engine) →
the pinned model (served model)* on Windows 11 hosts, with receipts and scrubbed exports under
`releases/<profile>/`. Newest figures come first; sections older than 2026-10-11 are collapsed below their
headings as dated history.

Since the [2026-11-09 qualifications](DECISION.md),
stock Strata `v0.2.13` (engine `0.1.59`) with stock OMP `18.18.3` is current on all three hosts and the Mac Studio
route (`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`, with
`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` as the qualified non-current alternate
route pinned to the PRO's tuned DFlash2 server, rolling back to the `v0.2.12` + OMP `18.18.0` DFlash2 route
`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`, and keeping the `v0.2.12` two-pass route
`client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0` as a draft): **rtxpro6000-win-a** (RTX PRO 6000,
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`: Qwen3.8-Flash-Next IQ3_S
at 262,144 tokens, four batch slots with per-slot stock DFlash2 drafters `strata.drafting: "dflash2"` using the
standard DFlash2 pack under `STRATA_BATCH_DF2` where stock `v0.2.13` runs window 8 (`--spec 8`, engine cap 8, was 6) on
one `sm_120` card of 48 GB or more
([UPSTREAM.md](UPSTREAM.md#big-blackwell-dflash2-defaults),
[batch-slot arm](UPSTREAM.md#stock-dflash2-batch-slot-arm-v0211--0157)), direct per-layer embedding (PLE) reads
`--ple-io direct` via `strata.ple_io: "direct"`, KV in VRAM `--kv-streaming off` via `setup_args.kv_streaming: "off"`,
stock `parallel_stack` and `gdn_stack` in `strata.engine_env` (id token `envpg`), conversation parking at 8,192 MiB and bare
`--prefill auto` at the 32,768-token ceiling, qualified on 2026-11-09 after the owner overrode its 11 of 90 version
A/B misses against `v0.2.12` (`"Override the base as current, and also qualify the tuned pack as an alternate"`, where
inter-output-event latency p95 was `1.171–1.188` at every depth, `w2/c1` largest gap p95 `1.173`, `w2/c4` TTFT p95
`1.118` and `w2/c4` TPOT max `1.067` while throughput was `0.986–0.999`, per-request `0.964–1.015`, TTFT p50
`1.009–1.036` and TPOT p50 `0.981–1.033`) and rolling back to the `v0.2.12` + OMP `18.18.0` four-slot DFlash2 profile
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`, while
`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` pinning stock's
tuned DFlash2 pack `qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack` (`339,694,592` bytes, which stock `v0.2.13` now
runs at `--draft-conf 0.55` instead of `0.35` on this card;
[UPSTREAM.md](UPSTREAM.md#big-blackwell-dflash2-defaults),
[tuned DFlash2 pack](UPSTREAM.md#tuned-dflash2-pack-pro-arm)) is a qualified non-current alternate after the owner also
qualified it over its 15 of 90 A/B misses against `v0.2.12` — `w2/c2` per-request `1.084` and TPOT p50 `0.928` with the
same window-8 burstiness (`1.169–1.172` inter-output p95, `w2/c1` largest gap p95 `2.151`, `w2/c4` TTFT p50 `1.129`),
and not the rollback — and the `v0.2.13` standard-pack `--draft-conf 0.55` draft
`win11-rtxpro6000-iq3s-262k-slots4-df2conf055-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` (withdrawn before
install), the `v0.2.12` two-pass draft
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0`, the `v0.2.11`
quality-first comparison drafts `win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0`,
`win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0` and
`win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0`, the `v0.2.11` `UD-Q4_K_XL` screen
`win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0` (slower than the `v0.2.11`
IQ3_S profile in every measured workload: single-request decode `0.85–0.91x`, total throughput `0.73–0.84x`), and the
`v0.2.9` `UD-IQ4_XS` and `NVFP4-QAD` model candidates and their routes stay drafts), **rtx5090-win-a** (RTX 5090, Qwen3.8-Flash-Next Coder IQ1_M at 262,144 tokens as the
**default** in `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`, pinning `--kv-streaming off`
via `setup_args.kv_streaming: "off"`, elastic KV growth `--kv-grow` via `strata.kv_grow: true` and stock `gdn_stack` in
`strata.engine_env` (id token `envg`), with a 34 GiB available-RAM start floor, a 4,352 MiB automatic conversation cache, and bare
`--prefill auto` at the 32,768-token ceiling, qualified on 2026-11-09 after passing all 88 version A/B checks against
`v0.2.12` and rolling back to the same family on `v0.2.12` + OMP `18.18.0`
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`, while 131,072-token Coder
`win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3` is the qualified 131K alternative rolling back to
`win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0` after qualifying on the same window's passing 262K A/B without
an A/B of its own (as in [`v0.2.12`](#strata-v0212-windows-2026-11-07-stock-omp-18180) and
[`v0.2.10`](#strata-v0210-windows-2026-11-03-stock-omp-18160)) and passing every gate, and full-model `IQ3_S` 131,072-token
low-RAM resident `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3` — stock's planner pick for this host, with
`11,616` expert slots in `22.04 GiB` VRAM and `29.77 GiB` of experts page-locked in RAM
([UPSTREAM.md](UPSTREAM.md#rtx-5090-low-ram-screen-planning)) — is a qualified non-current alternate while the Coder
stays the default, qualified in the second window under `"Qualify full-model IQ3_S 131K: prune old [rtx5090-win-a] roots
for disk, then run its main gates"` after its report-only paired screen against the `v0.2.13` Coder 131K profile (`1.046`
at 8K, `1.093` at 32K, `1.071` at 100K and `1.094` on warm 32K decode, `0.763` at the empty prompt, queue decode
`1.086 / 1.086`, per-request `1.134 / 1.129`, TPOT p50 `0.881 / 0.885`, throughput `w1` `1.059` and `w3` `0.917`, TTFT p50
`1.528` at 512 tokens and `1.122` at 32K, prefill `0.61–0.95`); the 262K profiles require the host's Docker Desktop and WSL,
which run its production NInfer container, to be stopped, with that container recreated by the owner's pinned relaunch
script and re-registered with the owner's fleet controller after WSL restarts, while the 131K Coder alternative starts with
Docker Desktop and WSL running, the `v0.2.13` `STRATA_SPEC_COST=1` draft
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3` (missed 3 of 88 checks in its initial A/B and
2 of 88 in three replacement pairs, not adopted by the owner) and the `v0.2.13` full-model `IQ3_S` 262K low-RAM screen
draft `win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` (refused at first start because the
low-RAM resident start did not print stock's elastic K/V line for its pinned `--kv-grow`) stay unqualified drafts with
`"Not qualified"` blockers, the `v0.2.12` two-pass draft
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0` stays an unqualified draft with its G18
failure kept in its published ledger, `win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0` stays an unqualified draft
after failing G15 twice on 2026-11-06, and the `v0.2.9` unpinned-GDN fallback
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0` stays an uninstalled draft), and
**rtx3090-win-a** (RTX 4090 + RTX 3090 pair,
`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`:
IQ3_S at 262,144 tokens, stock roles with RTX 4090 as Main staged last, manual layer split 24 `--layer-split 24`, stage
dense-weight trim `--trim-stage-weights` via `strata.trim_stage_weights: true`, stock's DFlash2 drafter
`strata.drafting: "dflash2"` (`incoai/Qwen3.8-Flash-Next-DFlash2` with the local `selq4` pack on the last-staged RTX
4090 and no `--pipeline-windows 2` or loaded MTP layer) with `strata.drafting_args: {"--draft-conf": "0.5"}` — stock's
slot-step value for the pair's per-card slots, which stock cannot compute on a split, written to stock `user_args` with
stock `write_config` (id token `df2conf05`; [UPSTREAM.md](UPSTREAM.md#reviewed-dflash2-confidence-pins)) — no batch slots,
display on the RTX 4090, direct PLE reads `--ple-io direct`
via `strata.ple_io: "direct"`, the engine's `sm_86` default table `sm86_table`, stock `gdn_stack` (id token `env86g`) and exact two-pass
block selection `select_two_pass` (`STRATA_SELECT_TWO_PASS=1`, id token `t`) in `strata.engine_env`
([UPSTREAM.md](UPSTREAM.md#stock-engine-opt-in-groups-v0212--0158)), and the engine's 8,192 MiB automatic conversation
cache — the `env86gt` id family drops `-parking` only to stay within the 120-character profile-id limit, with the same stock setup tips (including automatic conversation parking) — qualified on
2026-11-09 under `"Run the --draft-conf 0.5 main; it becomes current if every gate passes"` after passing all 96 plain
A/B checks against the `v0.2.12` `env86gt` pair profile with neutral targeted cold decode `1.021 [1.020, 1.049, 0.993]`
(`1.061` at 100K, `1.054` on warm 32K, `1.044` at 32K) and passing every gate, and rolling back to the qualified
`v0.2.12` + OMP `18.18.0` two-pass DFlash2 profile
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`).
On the pair, the `v0.2.13` unpinned-confidence `env86gt` draft
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`
(missed 6 of 96 checks against `v0.2.12`, all on one 32K request) and the `v0.2.13` split-attention draft
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3`
(`STRATA_QSA_SPLIT_ATTN=1`, missed 2 of 96 checks and its `1.02` targeted cold decode bar at `1.003 < 1.02`) stay
unqualified drafts with `"Not qualified"` blockers, the `v0.2.12` W4A8 draft
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0`
(`STRATA_IQ4_W4A8=2`) stays an unqualified draft after missing its cold-TTFT and 32K decode bars, the `v0.2.8` roles
draft with stock PLE residency stays a measurement-only draft after verifying
[Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)'s fix on Windows (PLE lock given back, 4,864 MiB
cache versus 8,192 MiB with PLE direct), the `v0.2.7` roles draft with PLE in RAM stays a held draft on commit headroom
(1.03 GiB Windows commit headroom versus 27.3 GiB on `v0.2.7` PLE-direct and `v0.2.3` roles, 27.8–27.9 GiB on
`v0.2.8`, 27.74–27.77 GiB on `v0.2.9`, 27.51–27.54 GiB on `v0.2.10`, and 28.70 GiB on `v0.2.11`, at the same 135.7 GiB
limit), and the `v0.2.7` default-split draft stays unmeasured. The
[2026-11-09 windows section](#strata-v0213-windows-2026-11-09-stock-omp-18183) records the `v0.2.13` cold-start version
A/B runs against `v0.2.12`, the PRO tuned DFlash2 pack A/B (at stock `--draft-conf 0.55` and window 8) and withdrawn
standard-pack `df2conf055` draft, the RTX 5090 `STRATA_SPEC_COST=1` arm and full-model `IQ3_S` 131K low-RAM screen and
262K start refusal, the pair engine `0.1.59` stage-order measurement, `STRATA_QSA_SPLIT_ATTN=1` arm and `--draft-conf 0.5`
A/B, the install `carry_user_args` fix (`fb8740a`), the server qualification chains and both Studio routes' G23 runs;
the [2026-11-07 windows section](#strata-v0212-windows-2026-11-07-stock-omp-18180) holds `v0.2.12` rollback evidence
across all three hosts (PRO `slots4-df2`, RTX 5090 262K `kvvram-kvgrow-envg` default and 131K alternative, pair
`df2-...-env86gt`) and the Studio `df2` route, and earlier qualified history on the PRO `slots4-df2tuned` alternate,
pair `df2-...-env86g-parking` and Studio `df2tuned` route; the
[2026-11-06 quality-first comparison section](#quality-first-comparison-on-the-pro-2026-11-06-stock-strata-v0211-stock-omp-18160)
records the PRO screens, 22-task private evaluation and long-session checks that kept the four-slot `IQ3_S` DFlash2
incumbent; the
[2026-11-06 windows section](#strata-v0211-windows-2026-11-06-stock-omp-18160) holds `v0.2.11` earlier qualified
history across all three hosts and the Studio routes (`v0.2.11` RTX 5090 262K root deleted on 2026-11-09 with the owner's
approval); the
[2026-11-03 windows section](#strata-v0210-windows-2026-11-03-stock-omp-18160) holds `v0.2.10` earlier qualified
history across all three hosts and the Studio route (`v0.2.10` RTX 5090 roots deleted on 2026-11-09 with the owner's
approval); the
[2026-11-02 tuning section](#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150) and
[2026-11-02 windows section](#strata-v029-windows-2026-11-02-stock-omp-18150) hold `v0.2.9` earlier qualified history
across all three hosts and the Studio route, plus the comparison-only feature arms and PRO model screens; the
[2026-10-31 section](#stock-tuning-pins-on-strata-v028-2026-10-31-stock-omp-18140) and
[2026-10-30 section](#strata-v028-windows-2026-10-30-stock-omp-18140) hold `v0.2.8` earlier qualified history across
all three hosts and the Studio route; the [2026-10-28 section](#strata-v027-windows-2026-10-28-stock-omp-18132),
[2026-10-23 section](#strata-v023-windows-2026-10-23-stock-omp-18126) and
[2026-10-21 section](#all-three-hosts-every-gate-2026-10-21-stock-strata-v021-stock-omp-18101) hold earlier qualified
history across all three hosts (`v0.2.3` RTX 5090 integration roots were removed on 2026-11-02 with the owner's
approval, and `v0.2.1` + OMP `18.10.1` integration roots were removed on every host on 2026-10-28); and the 2026-10-15
and 2026-10-13 sections hold earlier qualified history (`v0.1.44.1` on the PRO and RTX 5090, `v0.1.43.1` on all three
hosts). Each tuple has its own integration root and release ledger; no earlier
receipt is inherited or replaced.

**How to read a section.** Each dated section records the boundaries of the run that produced it; historical
table headers keep the role (`current`, `rollback`, `earlier history`, `draft`) a profile held when that section
was written.

- **Units.** In the resource tables (defined in the fourth-tuple and candidate sections and carried forward), `GB`
  is decimal and GPU memory is `MiB`; host RAM floors and setup-reported RAM use `GiB` where written `GiB`.
  Throughput is `tokens/s`; prompt and turn times are milliseconds (`ms`) or seconds (`s`).
- **Wall-clock boundaries (`wall`).** As defined in Candidate 1, `wall` is a monotonic clock around a whole client
  action. Start-to-readiness rows use distinct boundaries where named: `G16` measures server restart to verified
  readiness, `G21` measures the current engine start to verified readiness, and `G26` or operator first-start
  timings measure the guarded-start command wall. `G16` next-turn times exclude the preceding server stop/start
  and are not total restart-to-answer latency. In `G24`, whole-batch wall includes all 18 attempts, tool
  execution, verifier runs, restarts and failures; dividing batch wall by reported output tokens (as in the
  2026-10-13 section) is not isolated decode latency.
- **Server-reported versus client-side and sampler figures.** `server` figures come from stock Strata's own
  per-request records (`/metrics`: `prompt_ms`, `decode_ms`, `reused`); `scripts/perf_probe.py` and `G17`
  throughput tables report server timings unless stated otherwise. Reused-token counts (`G12`, `G17`, `G19`) come
  from the engine's per-request statistics, not from server log progress lines. Client-side speed in the
  fifth-tuple `G25` probes (`scripts/probe_g25_speed.py`) measures the same prompt set across engines from the
  client: time to first token (`TTFT`) is dispatch to the first streamed token of any kind, and output `tokens/s`
  is completion tokens over the time after it. `sampler` figures come from `nvidia-smi` and
  `GlobalMemoryStatusEx` every 2 s plus per-process `K32GetProcessMemoryInfo` peaks; `G21` working-set and
  private-commit peaks are the lifetime peaks of the sampled engine process, not a maximum across restarted
  processes.
- **Process-cold versus file-cache state.** After any engine restart, OMP's transcript is authoritative, live
  VRAM prefix reuse is lost, and cold re-prefill is expected (`G15`, `G16`, `G17`, `G20`). As defined in
  Candidate 1, a restarted engine with a warm OS file cache is *process-cold, file-cache-warm*. Where the
  2026-10-11 and 2026-10-12 pair runs note startup differences (`54.7-55.0 s` versus `40.7-43.0 s`), private
  engine startup logs separate Windows file-cache reads (`6.20-8.23 GiB/s` on the 51.1 GiB expert pack) from
  unbuffered disk reads (`2.33-2.95 GiB/s`); `G21` receipts report that load-rate metric unavailable.
- **Pilot versus scored denominators and gate outcomes.** The frozen `synthetic-1` coding evaluation (`G24`) runs
  a non-scored six-attempt pilot (one attempt per task) followed by 18 scheduled scored attempts (three attempts
  per task across six stdlib Python tasks). Pilot (`6`) and scored (`18`) denominators stay separate; every failed
  attempt, client thinking-loop abort or malformed-arguments protocol counter remains counted in its denominator.
  `G24` passes for complete, independently verified reporting, not for passing every coding task; the frozen
  evaluator exits `1` when any attempt fails, which is not an omitted gate. A ledger count of `21 pass, 3 not
  applicable` (`G22` images, `G23` remote clients and `G25` runtime comparison off on local text-only profiles)
  establishes integration qualification, not task quality or runtime superiority. Separate 60-task and 22-task private
  evaluations (`scripts/eval_taskset.py`) and 30-task Terminal-Bench 2.1 runs are comparison-only evidence and do
  not change any gate or ledger.

**Section index.** Every top-level section in this file, ordered newest first:

| Date | Hosts | Tuple | What it establishes | Same-file anchor |
|---|---|---|---|---|
| 2026-11-09 | `rtxpro6000-win-a` (four-slot DFlash2 current + tuned DFlash2 alternate + `df2conf055` withdrawn draft), `rtx5090-win-a` (262K Coder current + 131K Coder alternative + full-model `IQ3_S` 131K low-RAM alternate + `envgc` and `IQ3_S` 262K drafts), `rtx3090-win-a` (pair `df2conf05` current + `env86gt` and `env86gts` drafts), Mac Studio routes (`df2` current + `df2tuned` alternate) | Stock Strata `v0.2.13` (engine `0.1.59`), stock OMP `18.18.3` | **Current evidence across all three hosts and the Mac Studio route (`slots4-df2` current and `slots4-df2tuned` qualified alternate on the PRO rolling back to `v0.2.12` `slots4-df2`; RTX 5090 262K `kvvram-kvgrow-envg` default and 131K Coder alternative rolling back to `v0.2.12`, with full-model `IQ3_S` 131K low-RAM qualified as a non-current alternate; pair `--draft-conf 0.5` `df2conf05-...-env86gt` current rolling back to `v0.2.12` `df2-...-env86gt`; Mac Studio `df2` current and `df2tuned` qualified alternate rolling back to `v0.2.12` `df2`).** Paired cold-start A/B (`A1 B1 B2 A2 A3 B3`): RTX 5090 262K `envg` passes all 88 checks (`w1` `1.006`, `w3` `0.995`, per-request `1.024 / 0.975`, TTFT p50 `0.989 / 1.002`, TPOT p50 `0.975 / 1.023`, cold decode `0.986–1.018`, prefill `0.998–1.075`); RTX 5090 `STRATA_SPEC_COST=1` (`envgc`) misses 3 of 88 (`1.119` window, `1.711` / `1.771` largest-gap p95/max) and 2 of 88 in three replacement pairs (`1.197` / `1.212`, targeted cold decode `1.012 < 1.02`, not adopted); RTX 5090 `IQ3_S` 131K low-RAM screen vs `v0.2.13` Coder 131K (`11,616` expert slots in `22.04 GiB` VRAM, `29.77 GiB` page-locked in RAM) decodes at `1.046` (8K), `1.093` (32K), `1.071` (100K), `1.094` (warm 32K) and `0.763` (empty prompt) with `0.61–0.95` prefill and qualifies as a non-current alternate under `"Qualify full-model IQ3_S 131K: prune old [rtx5090-win-a] roots for disk, then run its main gates"`, while `IQ3_S` 262K is refused at first start (`"strata.kv_grow: elastic K/V line absent from this start's engine-log interval"`); PRO four-slot DFlash2 (window 8, was 6) misses 11 of 90 checks on window-8 burstiness (`1.171–1.188` inter-output p95, `w2/c1` gap p95 `1.173`, `w2/c4` TTFT p95 `1.118`, TPOT max `1.067`) and PRO tuned pack (at stock `--draft-conf 0.55`) misses 15 of 90 (`1.169–1.172` inter-output p95, `w2/c1` gap p95 `2.151`, `w2/c4` TTFT p50 `1.129`, `w2/c2` per-request `1.084`, TPOT p50 `0.928`), both qualified under `"Override the base as current, and also qualify the tuned pack as an alternate"`, while PRO `df2conf055` is withdrawn before install; pair `env86gt` misses 6 of 96 on one 32K request, pair `STRATA_QSA_SPLIT_ATTN=1` (`env86gts`) misses 2 of 96 (targeted cold decode `1.003 < 1.02`), and pair `--draft-conf 0.5` (`df2conf05`) passes all 96 plain checks (targeted cold decode `1.021 [1.020, 1.049, 0.993]`) and becomes current under `"Run the --draft-conf 0.5 main; it becomes current if every gate passes"` after `fb8740a` fixes `carry_user_args` on setup re-run. All six qualified server chains pass every gate (`G24` `16/18` on all three RTX 5090 profiles and the pair, `15/18` on both PRO profiles); Studio `df2` G23 (RTT `5.8–7.7 ms`, TTFT `0.217 s`) and `df2tuned` G23 (RTT `6.1–6.8 ms`, TTFT `0.181 s`) pass (`"ROUTE OK"`). | [2026-11-09 windows](#strata-v0213-windows-2026-11-09-stock-omp-18183) |
| 2026-11-07–08 | `rtxpro6000-win-a` (four-slot DFlash2 current + tuned DFlash2 alternate + two-pass draft), `rtx5090-win-a` (262K current + 131K alternative + two-pass draft), `rtx3090-win-a` (pair two-pass current + standard DFlash2 rollback + W4A8 draft), Mac Studio routes (`df2` current + `df2tuned` alternate + `envpgt` draft) | Stock Strata `v0.2.12` (engine `0.1.58`), stock OMP `18.18.0` | **Rollback evidence across all three hosts and the Mac Studio route (`slots4-df2` on the PRO, 262K `kvvram-kvgrow-envg` default and 131K alternative on the RTX 5090, `df2-...-env86gt` on the pair, and `df2` on the Mac Studio route), and earlier qualified history on the PRO (`slots4-df2tuned`), pair (`df2-...-env86g-parking`) and Mac Studio `df2tuned` route; qualified on 2026-11-07–08.** Paired cold-start A/B (`A1 B1 B2 A2 A3 B3`): PRO `v0.2.12` vs `v0.2.11` misses 1 of 90 checks (`w2` two-request max TPOT `1.057 [0.978, 0.976, 1.239]`; owner override `"Override: main + G23 after tuned arm"`); RTX 5090 262K passes all 88 checks (throughput `1.000 / 0.997`, TTFT p50 `1.005 / 1.001`, decode `0.980–1.012`, prefill `0.983–1.063`); pair `v0.2.12` vs `v0.2.11` misses 7 of 88 checks (cold 8K decode `0.943 [0.967, 0.917, 0.947]`, queued depth-0 decode `0.937 [0.929, 0.935, 0.946]`, server decode times `1.060` and `1.068`, and 32K/depth-0 gap metrics `1.050–1.052`; owner override `"Override: main, then the arms"`); PRO tuned pack misses 6 of 90 against `v0.2.11` and 3 of 90 against `v0.2.12` (slower at one request `0.942 [0.936, 0.935, 0.955]`, faster at two `1.165 [1.023, 1.230, 1.258]`; qualified as alternate under `"Override: qualify tuned as alternate"`); `STRATA_SELECT_TWO_PASS=1` is adopted on the pair (passes all 96 checks, 200K cold TTFT `0.976 [0.981, 0.977, 0.970]`) and not adopted on the PRO (misses 3 of 96, `"Keep the base"`) or RTX 5090 (passes 96 A/B checks, 200K cold TTFT `0.971 [0.969, 0.971, 0.974]`, fails G18, `"Keep envg current"`); pair `STRATA_IQ4_W4A8=2` is not adopted (cold-TTFT geomean `1.000`, 32K decode `0.917 [0.926, 0.932, 0.894]`). All six qualified server ledgers have 21 pass and 3 not applicable, with G24 15/18 on each (17/18 on the failed RTX 5090 two-pass draft); Studio `df2` G23 (RTT `5.9–7.4 ms`, TTFT `0.247 s`) and `df2tuned` G23 (RTT `12.1–16.1 ms`, TTFT `0.317 s`) pass. | [2026-11-07 windows](#strata-v0212-windows-2026-11-07-stock-omp-18180) |
| 2026-11-06–07 | `rtxpro6000-win-a` (four-slot `IQ3_S` DFlash2 incumbent + one-slot `IQ3_S`, one-slot `UD-Q5_K_XL` and six-expert `DeepSeek V4.1-Flash IQ2_XS` drafts) | Stock Strata `v0.2.11` (Qwen engine `0.1.57`, `strata-dsv41` `0.1.57`), stock OMP `18.16.0` | **Comparison-only quality-first evaluation (no gate or ledger changes; current PRO four-slot `IQ3_S` DFlash2 profile and Studio route unchanged and re-verified at `f9f9680`, owner decisions 2026-11-07 `"Skip second trials"`, `"We don't need to artificially restrict it to 1 session, C=4 is fine."` and, stopping the DeepSeek trial, `"Let's be pragmatic: Yes, it's safe to stop now."`).** Screens (`install, keygen, start, g10, tracer, [g14, g14q,] perf, stop`, 3/3 typed-tool tracers each): one-slot `IQ3_S` starts in `71 s` (`404.4 tok/s` decode and `8,610 tok/s` prefill at 32K, TTFT `3.86 s` / `11.56 s` at 32K / 100K, `99.42 GiB` commit headroom); one-slot `UD-Q5_K_XL` starts in `85.7 s` (`296.7 tok/s` decode, `7,712 tok/s` prefill, TTFT `4.29 s` / `12.83 s`, `22,209 / 24,576` experts in `82.80 GiB` VRAM at `98.4–99.9%` hit rate, `17.12 GiB` commit headroom); six-expert `DeepSeek IQ2_XS` starts in `54.8 s` (`45.7 tok/s` decode, `2,655 tok/s` prefill, TTFT `12.4 s` / `32.4 s`, `9,344 / 15,360` experts in `91.05 GB` VRAM and `6,016` copied into `58.4 GB` RAM, DSpark declined under `auto`, `52.70 GiB` commit headroom). On 22 private tasks (16 hard + 6 base, one attempt per arm via `scripts/eval_taskset.py`, `+3` paired-net replacement bar), the incumbent passed `21/22` (`215.4 s` median, `5,498.6 s` total, 1 critical mid-run empty reply on a passing task, capping any candidate's paired net at `+1`), one-slot `UD-Q5_K_XL` passed `20/22` (`278.9 s` median, `6,437.9 s` total, paired net `-1`, `p = 1.0`, wall ratio `1.26`), and `DeepSeek IQ2_XS` passed `5/7` before the owner stopped its trial after `7` of `22` tasks (paired net `-2` over those `7`, `p = 0.5`, wall ratio `3.9`; best reachable net `-1`). Four long-session reconnect runs on the incumbent (`L64` `64,341` to `LC` `219,899` compacting `222,486 -> 25,396`) passed all recalls and final edits. | [2026-11-06 quality-first comparison](#quality-first-comparison-on-the-pro-2026-11-06-stock-strata-v0211-stock-omp-18160) |
| 2026-11-06 | `rtxpro6000-win-a` (four-slot DFlash2 current + batch-MTP rollback + `UD-Q4_K_XL` screen), `rtx5090-win-a` (262K current; 131K unqualified after 2x G15 fail), `rtx3090-win-a` (pair DFlash2 current), Mac Studio routes (`df2` current + `batchmtp` rollback) | Stock Strata `v0.2.11` (engine `0.1.57`), stock OMP `18.16.0` | **Earlier qualified history on the PRO (`slots4-df2` and `slots4-batchmtp`), RTX 5090 262K default (`kvvram-kvgrow-envg`), pair (`df2-...-env86g`) and Mac Studio routes (`df2` and `batchmtp`); qualified by the owner on 2026-11-06 (`01b4d9b`, CI matrix `69de6d2`), while the RTX 5090 131K alternative stayed on `v0.2.10` at the time after failing G15 twice on `v0.2.11`.** Paired cold-start version A/B against `v0.2.10` (`A1 B1 B2 A2 A3 B3`, `B` = `v0.2.11` over `A` = `v0.2.10`): PRO batch-MTP passes 97/100 (`w2` aggregate `0.983–0.998`, `w3` `1.011`, decode `0.975–1.011`; misses 3/100 on `w2/c2` `per_req_tps_p50` `0.923`, `tpot_p50` `1.070` and `max_gap_p50` `1.232` from an A3 baseline outlier); PRO four-slot DFlash2 vs `v0.2.11` batch-MTP delivers `+20–26%` single-request decode (`1.201` at 0, `1.258` at 8K, `1.203` at 32K, `1.142` at 100K, `1.216` on warm 32K) and `w3` `0.995` while missing 35/100 on `w2` `c=2/c=4` short-request throughput/latency and output-burst inter-token/inter-event gaps; comparison-only PRO `UD-Q4_K_XL` screen (`strata_kq.dll`, `STRATA_MMQ_KQ=1`) is slower than `v0.2.11` IQ3_S in every measured workload (single-request decode `0.848–0.915`, prefill `0.789–0.855`, TTFT `1.168–1.267`, `w2/w3` aggregate throughput `0.731–0.844`); RTX 5090 262K passes 77/88 (`w1` `1.011`, decode `0.965–1.008`, prefill `0.988–1.138`, 100K TTFT `0.969`; misses 11/88 on `w3` 32K single-request `agg_tps` `0.917`, TTFT `1.097`, TPOT `1.051` from engine `0.1.57`'s 32,768-token bare-auto chunk ceiling vs `0.1.56`'s `prompt chunk auto: 8192`); pair DFlash2 passes 84/88 (`w1` `1.008`, `w3` `0.999`, decode `0.966–1.022`, prefill `0.988–1.062`; misses 4/88 on burstiness only: `w1` `max_gap_p50/p95/max` `1.125–1.126` and depth-0 inter-event p95 `1.096`). All four qualified `v0.2.11` server ledgers have 21 pass and 3 not applicable; G24 scored 15/18 on PRO `df2` (pilot 5/6, 627.3 s; initial G15 failure retained beside passing `b812df9` rerun), 16/18 on PRO `batchmtp` (pilot 5/6, 549.4 s), 17/18 on RTX 5090 262K (pilot 6/6, 843.1 s) and 15/18 on pair `df2` (pilot 5/6, 896.4 s; initial G13 forced-compaction failure retained beside passing `611c342` rerun); Studio `df2` G23 pass (`b812df9`, RTT 6.0–10.1 ms, TTFT 0.270 s) and `batchmtp` G23 pass (`9c6318b`, RTT 5.3–6.5 ms, TTFT 0.174 s). | [2026-11-06 windows](#strata-v0211-windows-2026-11-06-stock-omp-18160) |
| 2026-11-03 | `rtxpro6000-win-a`, `rtx5090-win-a` (262K + 131K), `rtx3090-win-a` (pair DFlash2 current + `env86g` rollback), Mac Studio route | Stock Strata `v0.2.10` (engine `0.1.56`), stock OMP `18.16.0` | **Earlier qualified history on the RTX 5090 131K alternative and 262K default (`kvvram-kvgrow-envg`), the pair DFlash2 (`df2-...-env86g`), the PRO (`kvvram-envpg`), the pair MTP (`pw2-...-env86g`) and the Mac Studio route; qualified by the owner on 2026-11-03.** Paired cold-start version A/B against `v0.2.9` (`A B B A A B`, `B` = `v0.2.10` over `A` = `v0.2.9`; latencies under 1 ms and first-SSE-frame timing reported below resolution floor): RTX 5090 262K passes all 88 gated metrics (`w1` 512/512 aggregate completion tok/s `agg_tps` `1.033`, `w3` `1.013`, decode `1.012–1.036`); pair `env86g` passes all 88 (`w1` `1.020`, `w3` `1.009`, TTFT `0.979–0.995`, decode `0.996–1.036`); PRO passes decode (`1.039–1.062`) and aggregate throughput (`0.969–1.032`) while missing concurrent short-prompt TTFT (`w2` `c=2` p50 `1.052` / p95 `1.136`, `c=4` p50 `1.326`; owner override `"Override: chain + G23"`). Pair DFlash2 vs `v0.2.10` `env86g` meets the `+3%` decode bar (`1.082` at 8K, `1.093` at 100K, `1.101 / 1.136 / 1.077` at 0 / 32K / warm 32K; `w1` `1.001`, `w3` `1.033`, 8K–100K TTFT `0.955–0.980`) and is made current by owner override (`"Run chain, make DFlash2 current"`) over its 16 burst-spacing, queued-prefill and empty-prompt TTFT 5%-rule misses, with `v0.2.10` `env86g` kept as its rollback. All five server ledgers have 21 pass and 3 not applicable (hosted CI run 41723093180 on PR #75); G24 scored 16/18 on the PRO (pilot 5/6, 569.6 s), 18/18 on the RTX 5090 262K (pilot 5/6, 738.7 s), 16/18 on the RTX 5090 131K (pilot 6/6, 741.7 s), 17/18 on the pair DFlash2 current profile (pilot 5/6, 915.6 s) and 16/18 on the pair `env86g` rollback (pilot 5/6, 1,044.7 s); PRO G14 (`7971a1a`) and pair `env86g` G20 (`837bc89`) first-run failures are kept beside passing complete-gate reruns, and Mac Studio route G23 passes (`9a06ec1`, TTFT 0.219 s). | [2026-11-03 windows](#strata-v0210-windows-2026-11-03-stock-omp-18160) |
| 2026-11-02–03 | `rtxpro6000-win-a`, `rtx5090-win-a` (262K), `rtx3090-win-a` (pair `env86g` variant), Mac Studio route | Stock Strata `v0.2.9` (engine `0.1.55`), stock OMP `18.15.0` | **Earlier qualified history on the PRO (`kvvram-envpg`), its Mac Studio route, the RTX 5090 262K default (`kvvram-kvgrow-envg`) and the pair (`env86g`), plus comparison-only PRO `UD-IQ4_XS` and `NVFP4-QAD` model candidate drafts (owner decisions `"Qualify and make current"` on 2026-11-02 and pair `w1` override on 2026-11-02 / 2026-11-03).** Cold-start A/B (`A B B A A B`) against the `v0.2.9` base: PRO (`parallel_stack` + `gdn_stack` + `--kv-streaming off`) raises `w2` 1,000/128 aggregate output `B/A` to `1.113` (`c=1`), `1.293` (`c=2`) and `1.348 [1.316, 1.376]` (`c=4`) and `w3` `4 × 32K` to `1.131`, cuts `w2` TTFT p95 `B/A` to `0.804` / `0.764` / `0.683` (`w3` `0.908`), keeps cold decode `B/A` at `1.000` (depth 0) and `1.022` (100K), and matches stock greedy output (`ALL IDENTICAL` across all five sequences per block); RTX 5090 262K (`gdn_stack` + `--kv-streaming off` + `--kv-grow`, Docker/WSL stopped, 34 GiB start floor vs 36 GiB) cuts cold TTFT `B/A` to `0.914` at 32K and `0.911` at 100K, keeps 100K decode `B/A` at `0.973`, and raises `w1` and `w3` 32K aggregate output `B/A` to `1.025` and `1.084`; the pair `env86g` variant (the engine's `sm_86` table + `gdn_stack`) passes cold decode (`1.065` at 8K, `1.114` at 100K) and every TTFT bar (`0.948–0.996`) while missing `w1` (`1.039 [1.033, 1.045]` vs `>= 1.05`), which the owner overrode (`"Yes approved: Yes, if you approve an override. There's nothing in the pair profile to fix."`). All three server ledgers have 21 pass and 3 not applicable (tooling `acd7549` on PRO and RTX 5090, `d0a1254` on the pair; G24 scored 16/18 on the PRO in 631.2 s vs 576.2 s, pilot 5/6, 17/18 on the RTX 5090 in 791.1 s vs 840.4 s, pilot 5/6, and 15/18 on the pair in 821.8 s vs 974.9 s, pilot 5/6; Mac Studio route G23 pass, stream TTFT 0.172 s vs 0.206 s). | [2026-11-02 tuning pins](#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150) |
| 2026-11-02 | `rtxpro6000-win-a`, `rtx5090-win-a` (262K + 131K), `rtx3090-win-a` (pair split 24, trim + PLE direct), Mac Studio route | Stock Strata `v0.2.9` (engine `0.1.55`), stock OMP `18.15.0` | **Earlier qualified history on the PRO, the RTX 5090 262K default and 131K alternative, the pair (split 24 with trim and PLE direct) and the Mac Studio route; qualified by the owner on 2026-11-02.** Cold-start version A/B against `v0.2.8` (`A B B A A B`) shows aggregate output `tok/s` `B/A` ratios of `0.996–1.012` on the PRO, `0.999–1.001` on the RTX 5090 262K and `1.003` on the pair. All four server ledgers have 21 pass and 3 not applicable; G24 scored 16/18 on the PRO (pilot 5/6, 576.2 s), 16/18 on the RTX 5090 262K (pilot 6/6, 840.4 s), 14/18 on the RTX 5090 131K (pilot 5/6, 762.5 s) and 15/18 on the pair (pilot 5/6, 974.9 s) against `v0.2.8`'s 15/18, 17/18, 18/18 and 15/18; Mac Studio route G23 passes (`6fec79d`, TTFT 0.206 s). Comparison-only feature arms measure the Linux-default nine-switch parallel stack (+30% at four concurrent 1K prompts on the PRO), `--kv-streaming off` (−14% ready time and +17 GiB available RAM on the PRO; +3.25 GiB with `--kv-grow` on the RTX 5090 262K), GDN tensor-core prompt kernels (−7 to −9.5% TTFT on the PRO and RTX 5090) and `sm_86` environment defaults (+8–13% decode on the pair); nothing from the arms is pinned in these base profiles. Comparison-only PRO model screens admit `UD-IQ4_XS` past rule 4 (273.1 tok/s at 32K, warm turn 1.21 s vs 1.085 s on IQ3_S, 1.115×) and `NVFP4-QAD` with PLE in RAM (307.4 tok/s, warm turn 1.96 s vs 1.015 s, 1.931×; with `--ple-io direct` on an HDD data volume it tripped the 60 s watchdog), and reject `DeepSeek V4.1 IST-DAS 2.25` (41.7 tok/s, warm turn 9.08 s vs 1.335 s, 6.801×). Admits `v0.2.9` setup planning (`7ea7f12`), per-profile NVFP4 conversion recipe pins (`2a4aae9`) and engine `0.1.55` pair stage order (`8002c77`). | [2026-11-02 windows](#strata-v029-windows-2026-11-02-stock-omp-18150) |
| 2026-10-31 | `rtxpro6000-win-a`, `rtx3090-win-a` | Stock Strata `v0.2.8` (engine `0.1.54`), stock OMP `18.14.0` | **Stock tuning options measured on the qualified roots, and three draft profiles pinning the winners requalified (not yet qualified).** PRO: `--ple-io direct` starts 30 s sooner at equal speed (G20 restart readiness 35.0 s against 88.2 s); `--batch-mtp` +22.5% total output at two concurrent requests and +40% summed decode at four 40K prompts. Pair: stock's manual split point 24 with `--trim-stage-weights` grows each card's expert cache by 1.8 GiB and cuts time to first token 12% at 32K-100K; the engine's sm_86 defaults (+5-11% decode) stay out of reach on this mixed-architecture pair. Each draft: 14 measured gates pass, G24 15/18. | [2026-10-31 tuning pins](#stock-tuning-pins-on-strata-v028-2026-10-31-stock-omp-18140) |
| 2026-10-30 | `rtxpro6000-win-a`, `rtx5090-win-a` (262K default + 131K alternative), `rtx3090-win-a` (pair PLE-direct current + stock-residency measurement draft), Mac Studio route | Stock Strata `v0.2.8` (engine `0.1.54`), stock OMP `18.14.0` | **Current evidence on all three hosts (PRO, RTX 5090 262K default and 131K alternative, pair PLE-direct `--ple-io direct`) and the Studio route; owner switches RTX 5090 default to 262K (`"Let's make it the default we want the bgiger context"`); pair stock-residency draft stays measurement-only.** All four qualified server ledgers have 21 pass, 3 not applicable; G24 scored 16/18 (PRO, pilot 5/6), 17/18 (RTX 5090 262K default, pilot 6/6), 18/18 (RTX 5090 131K alternative, pilot 5/6) and 15/18 (pair PLE-direct, pilot 5/6) versus 15/18, 16/18, 16/18 and 17/18 on `v0.2.7`. Studio route G23 pass (`4853ab3`, TTFT 0.199 s); engine `0.1.54` pair stage order admitted (`4853ab3`, 17.35 / 16.01 GiB caches); `Strata#4518` fix measured on Windows (lock released, 4,864 MiB cache vs 8,192 MiB with PLE direct); G10 listener check fixed for Windows build 26300.9818 (`f9e8c74`). | [2026-10-30 windows](#strata-v028-windows-2026-10-30-stock-omp-18140) |
| 2026-10-28 | `rtxpro6000-win-a`, `rtx5090-win-a` (131K + 262K), `rtx3090-win-a` (pair PLE-direct + held roles draft), Mac Studio route | Stock Strata `v0.2.7` (engine `0.1.52`), stock OMP `18.13.2` | **Rollback evidence across all three hosts (PRO, RTX 5090 262K default and 131K alternative, pair PLE-direct `--ple-io direct`) and the Studio route; pair roles (PLE in RAM) stays a held draft on commit headroom (G10 1.03 GiB versus 27.3 GiB on PLE-direct and v0.2.3 at the same 135.7 GiB limit; [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)), pair default split unmeasured.** All four qualified server ledgers (and the held pair roles ledger) have 21 pass, 3 not applicable; G24 scored 15/18 (PRO), 16/18 (RTX 5090 131K), 16/18 (RTX 5090 262K, Docker Desktop/WSL stopped; morning failed receipts retained) and 17/18 (pair PLE-direct, 8,192 MiB cache; held pair roles draft 13/18, pilot 6/6) versus 17/18, 17/18, 14/18 and 14/18 on `v0.2.3`. Studio route G23 pass; single-sample speed and PLE residency measurements retained. | [2026-10-28 windows](#strata-v027-windows-2026-10-28-stock-omp-18132) |
| 2026-10-23 | `rtxpro6000-win-a`, `rtx5090-win-a` (131K + 262K), `rtx3090-win-a` (pair) | Stock Strata `v0.2.3` (engine `0.1.48`), stock OMP `18.12.6` | **Earlier qualified history across all three hosts (PRO, RTX 5090 131K and 262K, pair stock roles) and the Studio route (after the `a915c69` / `de60693` reruns and pair roles chain; default and split-32 pair drafts stay unqualified).** Server chains: PRO G10 deep-verification mismatch not reproduced with the server stopped; RTX 5090 131K G20 (a foreign task's run state) and 262K G19 (assumed parking the engine left off) failed on gate predicates since fixed and passed on rerun; G24 scored 17/18, 17/18, 14/18 (and 14/18 on the pair roles chain, where G18 passed on rerun). Pair engine `0.1.48` stage order admitted (#48); roles reads 100K in 31.2 s versus 36.2 s default and 29.1 s split 32. | [2026-10-23 v0.2.3](#strata-v023-windows-2026-10-23-stock-omp-18126) |
| 2026-10-21 | `rtxpro6000-win-a`, `rtx5090-win-a` (131K default + 262K opt-in), `rtx3090-win-a` (pair) | Stock Strata `v0.2.1` (engine `0.1.46`), stock OMP `18.10.1` | **Earlier qualified history on all three hosts (`v0.2.1` integration roots removed on 2026-10-28; pair accepted at the time although slower than `v0.1.43.1`).** 21 pass, 3 not applicable on all four profiles; G24 scored 17/18 (PRO), 17/18 (RTX 5090 131K), 15/18 (RTX 5090 262K opt-in), 16/18 (pair), pilots 5/6 each, 0 protocol counters; G17 main-run shortening failures on PRO, 5090 131K and pair plus one 5090 131K G18 failure retained beside passing reruns; pair K=25 split (layers 0-24 / 25-47) A/B against `v0.1.43.1` (decode 141-158 vs 170-201 tok/s, 64K-100K prompt 2,838-2,853 vs 3,508-3,594 tok/s, 100K TTFT 36.0 vs 28.6 s). | [2026-10-21 all hosts](#all-three-hosts-every-gate-2026-10-21-stock-strata-v021-stock-omp-18101) |
| 2026-10-15 | `rtx5090-win-a` (RTX 5090) | Stock Strata `v0.1.44.1`, stock OMP `18.10.1` | **Earlier qualified history for the 262K opt-in (beside the 131K `v0.1.44.1` profile).** Coder IQ1_M at 262,144 tokens (36 vs 34 GiB startup RAM floor); 21 pass, 3 not applicable; G24 scored 15/18 (tool-loop 0/3), pilot 5/6 (tool-loop 0/1); original G26 failure retained beside passing same-root rerun (`9.929 / 21.228 / 7.209 s`). | [2026-10-15 opt-in](#rtx-5090-coder-262k-qualified-opt-in-2026-10-15) |
| 2026-10-13 | `rtxpro6000-win-a`, `rtx5090-win-a`, `rtx3090-win-a` (pair) | Stock Strata `v0.1.43.1`, stock OMP `18.10.1` (beside `v0.1.43` + `18.10.1`) | **Earlier qualified history on all three hosts** (`v0.1.43` is earlier qualified history on all three). 21 pass, 3 not applicable on all three; G24 scored 15/18 each (PRO and RTX 5090 tool-loop 0/3; pair tool-loop 1/3, multifile-regression 2/3 with 1 malformed-arguments counter), pilots 6/6, 5/6 and 5/6. | [2026-10-13 three hosts](#all-three-hosts-every-gate-2026-10-13-stock-strata-v01431-stock-omp-18101) |
| 2026-10-12 | `rtxpro6000-win-a`, `rtx5090-win-a`, `rtx3090-win-a` (pair) | Stock Strata `v0.1.43`, stock OMP `18.10.1` (beside `v0.1.42` + `18.8.9`) | **Earlier qualified history on all three hosts (was the pair's `v0.1.43.1` rollback).** 21 pass, 3 not applicable; G24 scored 16/18 (PRO), 15/18 (RTX 5090), 16/18 (pair); RTX 5090 G18 `CODE: KEEP` stop retained beside 14/15 probes and passing full G18 rerun; pair first-run stage-order admission failure retained beside passing run 2; pair 54.7-55.0 s vs 40.7-43.0 s readiness traced to Windows file-cache state; pair RAM floors 86/78 GiB. | [2026-10-12 three hosts](#all-three-hosts-every-gate-2026-10-12-stock-strata-v0143-stock-omp-18101) |
| 2026-10-11 | `rtxpro6000-win-a` (262K), `rtx5090-win-a` (131K) | Stock Strata `v0.1.42`, stock OMP `18.8.9` (beside `v0.1.41` + `18.8.6`) | **Earlier qualified history.** 21 pass, 3 not applicable on first run; G24 scored 16/18 on both cards, pilots 5/6; `100% VRAM resident` experts so `STRATA_ROUTE_TAIL_SKIP=7` and PCIe-share defaults do not apply; interleaved perf probes within run-to-run variation. | [2026-10-11 PRO and RTX 5090](#rtx-pro-6000-at-262k-and-rtx-5090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889) |
| 2026-10-11 | `rtx3090-win-a` (RTX 4090 + RTX 3090 pair) | Stock Strata `v0.1.42`, stock OMP `18.8.9` | **Earlier qualified history (three pair profiles).** 131K `--pipeline-windows 2` with display on RTX 3090 (predecessor; rollback only after moving display back to RTX 3090; scored 15/18, pilot 6/6); 131K display on RTX 4090 (startup refusal at 1,601 MiB, pre-G16 degraded status and failed G26 receipt retained beside passing main-root G26 rerun; scored 14/18, pilot 5/6); and [262K with 8 GiB parking and display on RTX 4090](#earlier-qualification-262k-with-stock-conversation-parking-display-on-the-rtx-4090-2026-10-11) (scored 15/18, pilot 5/6; G19 parking reuse 20,672/20,701 tokens in 491 ms, not an exact-output claim). Single-card RTX 3090 profiles are not rollbacks on this two-card host. | [2026-10-11 pair](#rtx-4090--rtx-3090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889) |
| 2026-10-10 | `rtx3090-win-a` (RTX 4090 + RTX 3090 pair) | Stock Strata `v0.1.42`, stock OMP `18.8.9` | **Draft screens (not qualified; no gate ran).** Two-card `--layer-split auto` doubles IQ3_S decode (174-183 vs 84-88 tokens/s) and triples long-prompt prefill (27.6 vs 85.3 s at 100K) against the RTX 3090 alone; card-order comparison (`#1576`); `--pipeline-windows 2` adds 9-13% decode (189-209 tokens/s); `STRATA_PF_FUSED=1` slows prefill 11-12%; stock calibration + `--parallel 4` + tips slow single requests 13-15% and add no multi-session throughput on ~91K-token agent sessions. | [2026-10-10 pair layer split](#rtx-4090--rtx-3090-layer-split-2026-10-10-stock-strata-v0142-stock-omp-1889) |
| 2026-10-10 | `rtxpro6000-win-a` | Stock Strata `v0.1.41`, stock OMP `18.8.6` | **Earlier qualified history.** First 262,144-token PRO qualification (74 GiB startup RAM floor, four slots, parking, 32K chunks); 21 pass, 3 not applicable; first G18 failure from fixed 131K-sized fixtures (162,071 tokens vs 221,952 threshold) retained beside passing window-sized rerun; G24 scored 17/18 (tool-loop 2/3), pilot 5/6. | [2026-10-10 PRO 262K](#rtx-pro-6000-at-262k-every-gate-2026-10-10-stock-strata-v0141-stock-omp-1886) |
| 2026-10-09 | `rtx5090-win-a` | Stock Strata `v0.1.41`, stock OMP `18.8.6` (beside `v0.1.40.3` + `18.8.4`) | **Earlier qualified history.** Coder IQ1_M at 131,072 tokens; 21 pass, 3 not applicable; G24 scored 15/18 (tool-loop 1/3, multifile-regression 2/3), pilot 6/6; readiness 11.7 s and 105K cold prefill 14.5 s unchanged from `18.8.4`. | [2026-10-09 RTX 5090](#rtx-5090-every-gate-2026-10-09-stock-strata-v0141-stock-omp-1886) |
| 2026-10-08 | `rtxpro6000-win-a` | Stock Strata `v0.1.41`, stock OMP `18.8.6` (beside `v0.1.40.3` + `18.8.4` and `18.8.3`) | **Earlier qualified history.** IQ3_S at 131,072 tokens with four slots, parking and 32K chunks; 21 pass, 3 not applicable; G24 scored 15/18 (tool-loop 0/3), pilot 5/6; on 30 Terminal-Bench 2.1 tasks (2026-10-09, OMP `18.8.6` harness, one attempt) passed 23/30 vs 19/30 on `v0.1.40.3` + `18.8.3` (exact McNemar p = 0.125). | [2026-10-08 PRO v0.1.41](#rtx-pro-6000-every-gate-2026-10-08-stock-strata-v0141-stock-omp-1886) |
| 2026-10-08 | `rtxpro6000-win-a`, `rtx5090-win-a`, single-card `rtx3090-win-a` | Stock Strata `v0.1.40.3`, stock OMP `18.8.4` | **Earlier qualified history on the PRO and RTX 5090; qualified single-card RTX 3090 profile.** 21 pass, 3 not applicable on all three; PRO G16 `append.py` predicate failure retained beside passing `2c32e2b` rerun; G24 scored 15/18 (PRO), 16/18 (RTX 5090), 15/18 (RTX 3090). | [2026-10-08 three GPUs](#three-gpus-every-gate-2026-10-08-stock-strata-v01403-stock-omp-1884) |
| 2026-10-07 | `rtxpro6000-win-a` | Stock Strata `v0.1.40.3`, stock OMP `18.8.3` (beside `v0.1.40.2` + `18.8.0` and `v0.1.40.1` + `18.5.0`) | **Earlier qualified history.** Pins `--parallel 4` (+19% four-request throughput in `tools/batch_test.py`), `--conversation-cache-mib 8192` (G19 20,669/20,698 tokens reused, 0.34 s vs 3.33 s cold) and `--prefill auto:32768`; 21 pass, 3 not applicable; G24 scored 16/18; Terminal-Bench 2.1 passed 19/30 on the OMP `18.8.3` harness. | [2026-10-07 PRO slots and parking](#rtx-pro-6000-with-batch-slots-and-parking-every-gate-2026-10-07-stock-strata-v01403-stock-omp-1883) |
| 2026-10-07 | `rtxpro6000-win-a` | Stock Strata `v0.1.40.2`, stock OMP `18.8.0` | **Earlier qualified history.** First qualified PRO profile (IQ3_S, 131,072 tokens, all experts in VRAM); 21 pass, 3 not applicable; isolates OMP `18.8.0` speculative compaction evicting the single-sequence prefix cache and verifies `compaction.asyncEnabled: false` (`906f4aa`: G17 wall 50.7 → 20.7 s, G18L 161.5 → 74.4 s); G24 scored 16/18; records `v0.1.40.1` Terminal-Bench 21/30 with zero stranded tool calls. | [2026-10-07 PRO v0.1.40.2](#rtx-pro-6000-every-gate-2026-10-07-stock-strata-v01402-stock-omp-1880) |
| 2026-10-06 | `rtxpro6000-win-a` (replacing RTX 4090 in `rtx4090-win-a`) | Stock Strata `v0.1.39`, stock OMP `18.5.0` | **Drafts only (no gate ran).** All 24,576 experts fit in VRAM on the PRO (46.84 GiB for IQ3_S, 71.73 GiB for UD-Q4_K_XL); IQ3_S decodes 2.2-2.3x faster (258.4-271.0 vs 115.0-116.4 tokens/s) and prefills 1.6-1.9x faster than the RTX 4090; 55/60 on the private task set in 0.39x the 4090's time; IQ3_S and UD-Q4_K_XL tie at 19/30 on Terminal-Bench 2.1 while UD-Q4_K_XL costs prefill speed (0.43-0.73x). | [2026-10-06 PRO vs RTX 4090](#rtx-pro-6000-against-the-rtx-4090-2026-10-06-stock-strata-v0139-stock-omp-1850) |
| 2026-10-05 | `rtx3090-win-a`, `rtx4090-win-a` | Stock Strata `v0.1.39` vs `v0.1.38`, stock OMP `18.5.0` | **Drafts only (no gate ran).** Alternating perf probes show `v0.1.39` decoding 3-7% faster with IQ3_S and 5-10% faster with Coder IQ1_M on `rtx3090-win-a` (42/44 base tasks at 0.84x median time); on `rtx4090-win-a` `--pool-workers 15` shows no clear gain over run-to-run spread, and notes 12-15% host speed drift. | [2026-10-05 v0.1.39 vs v0.1.38](#strata-v0139-against-v0138-2026-10-05-stock-omp-1850) |
| 2026-10-04 | `rtx5090-win-a`, `rtx4090-win-a`, `rtx3090-win-a` | Stock Strata `v0.1.38`, stock OMP `18.5.0` vs `omp-ninfer` `v0.10.0` | **Comparison-only model evaluation (no gate or ledger changes).** On 60 private tasks (26 development, 34 private data; 44 base, 16 hard), Flash-Next IQ3_S passed 58/60, Coder IQ1_M 54/60 and Qwen3.8 27B on NInfer 49/60 (IQ3_S vs 27B exact McNemar p = 0.004); second RTX 5090 attempt on 2026-10-05 (Coder 53/60 vs 27B 50/60, 9 and 11 task flips); fleet subagent delegation gained nothing over solo runs. | [2026-10-04 private 60-task set](#the-models-on-the-owners-kind-of-work-2026-10-04-a-private-60-task-set) |
| 2026-10-03 | `rtx5090-win-a`, `rtx4090-win-a` (192 GB), `rtx3090-win-a` (128 GB) | Stock Strata `v0.1.38`, stock OMP `18.5.0` vs `omp-ninfer` `v0.10.0` / `v0.6.10` / `v0.6.2` | **Drafts (G10 and G25 receipts in fifth-tuple draft releases; not qualified).** Per-root `v0.1.38` throughput; same-prompt client speed (`scripts/probe_g25_speed.py`: Strata reads 100K prompts 3-4x faster and restarts 2.4-4.5x faster; NInfer decodes faster on RTX 5090 up to 32K); [paired G25 evaluation](#paired-coding-evaluation-against-ninfer-g25) (RTX 5090 15/18 vs 14/18 at 1.39x median wall; RTX 4090 and RTX 3090 15/18 vs 15/18 at 0.98x; neither superiority claim holds); RTX 4090 192 GB DDR5-5200 + Intel Default Settings stability validation. | [2026-10-03 fifth tuple and G25](#fifth-tuple-and-strata-against-ninfer-2026-10-03-stock-strata-v0138-stock-omp-1850) |
| 2026-10-03 | `rtx5090-win-a`, `rtx4090-win-a` (32 GiB and 192 GB), `rtx3090-win-a` (128 GB) | Stock Strata `v0.1.34`, `v0.1.36`, `v0.1.38` (`tools/calibrate.py`) | **Drafts / calibration probes.** Stock calibration keeps nothing on the RTX 5090, low-RAM RTX 4090 or RTX 3090 Coder; keeps `--pcie-frac 0.20 --spec-min-p 0.70` or `--pcie-frac 0.00` on 192 GB RTX 4090 (+6-13% IQ3_XXS decode, +5-10% Coder decode up to 64K) and RTX 3090 IQ3_S (+4-5% up to 8K, within run-to-run spread from 32K on, G24 15/18 unchanged). | [2026-10-03 stock calibration](#stock-calibration-on-three-gpus-2026-10-03) |
| 2026-10-03 | `rtx3090-win-a` (128 GB) | Stock Strata `v0.1.36`, stock OMP `18.4.12` | **Drafts (variant-selection probes).** Coder IQ1_M at trained 262,144 tokens costs nothing below 100K (138.4 s TTFT and 89.0 tokens/s decode at 250K); experimental yarn `--rope-scale 2` at 524,288 tokens reaches 512,000 tokens (402.6 s TTFT, 72.1 tokens/s decode) at 3-5% slower decode below 100K; 524K quality not scored. | [2026-10-03 longer contexts](#longer-contexts-for-the-coder-on-the-rtx-3090-2026-10-03) |
| 2026-10-02 | `rtx3090-win-a` (128 GB) | Stock Strata `v0.1.36`, stock OMP `18.4.12` (beside `v0.1.34` + `18.4.10` Coder) | **Drafts (variant-selection measurements; no gate ran).** 128 GB unlocks KV streaming for IQ3_S (decode rises from 56-66 to 93-96 tokens/s, G24 15/18 tying the Coder's 15/18, and runs at 262K); more RAM does not speed up the Coder (100K cold prefill 43.2 vs 44.0 s); UD-Q4_K_XL decodes at 49-50 tokens/s and its 112-155 s restart exceeds the frozen evaluator's 120 s continuation hook cap. | [2026-10-02 RTX 3090 128 GB](#rtx-3090-with-128-gb-2026-10-02-which-model-the-ram-unlocks) |
| 2026-10-02–03 | `rtx3090-win-a` (64 GiB), `rtx4090-win-a` (32 GiB low-RAM), `rtx5090-win-a` (47.15 GiB) | Stock Strata `v0.1.34`, stock OMP `18.4.10` | **Earlier qualified history (first qualified tuple; single-card rollback and RTX 4090 record).** First tuple where G04's cut-off tool call passes on stock releases; all applicable gates pass (G15 corrected-probe repeats `cb31418` on 2026-10-03 and RTX 4090 reduced-threshold G18 repeat, with earlier failures retained); G24 scored 15/18 (RTX 3090), 15/18 (RTX 4090, 0.44 GB minimum RAM), 16/18 (RTX 5090). | [2026-10-02–03 fourth tuple](#fourth-tuple-on-three-gpus-2026-10-0203-stock-strata-v0134-stock-omp-18410) |
| 2026-10-01 | `rtx3090-win-a` (64 GiB), `rtx4090-win-a` (32 GiB low-RAM) | Stock Strata `v0.1.31`, stock OMP `18.4.8` | **Unqualified historical rollback installations (draft ledgers; OMP `18.4.8` failed G04).** First 24 GB host measurements (Coder IQ1_M G24 17/18 on RTX 3090, 15/18 on RTX 4090 with 0.37 GB minimum RAM during G15 restarts), plus [exploratory RTX 3090 64 GiB IQ3_S run](#exploratory-the-original-model-iq3_s-on-the-rtx-3090-64-gib) (0.72 GB commit spare, G24 15/18, tool-loop 0/3 failing on exact-money precision `12345678901234567890123456790000` vs `12345678901234567890123456789012`). | [2026-10-01 third tuple](#third-tuple-on-24-gb-hosts-2026-10-01-stock-strata-v0131-stock-omp-1848) |
| 2026-10-01 | `rtx5090-win-a` | Stock Strata `v0.1.30`, stock OMP `18.4.6` | **Unqualified historical candidate (rollback installation).** Second RTX 5090 candidate (G24 scored 15/18, pilot 5/6, tool-loop 0/3; second-root G26 install), plus the 2026-10-10 Issue #3 evidence reconciliation (`test_cross_account_dedup_voids_and_exact_signed_money` named in all four `tool-loop` failures; original Coder causal mechanism unproved without per-attempt `result.json` and `candidate.patch`). | [2026-10-01 Candidate 2](#candidate-2-2026-10-01-stock-strata-v0130-stock-omp-1846) |
| 2026-09-30 | `rtx5090-win-a` | Stock Strata `v0.1.27`, stock OMP `18.4.0` | **Unqualified historical candidate (rollback installation).** Original `rtx5090-win-a` hardware baseline and measurement-boundary definitions (`wall`, `server`, `sampler`, process-cold/file-cache-warm); 1,024-token OMP window margin (`130,048` vs `131,072`); ETW egress guard (`244` non-loopback events unguarded vs `0` of `3,711` guarded); G24 scored 16/18 (pilot 5/6); G26 clean install in a new root. | [2026-09-30 Candidate 1](#candidate-1-2026-09-30-stock-strata-v0127-stock-omp-1840) |

## Strata v0.2.13 windows (2026-11-09): stock OMP 18.18.3

This section records the `2026-11-09` host measurements (all times UTC) for stock Strata `v0.2.13` (annotated tag object
`fb57f7472c2ab4d176c216b30ed1d6b5e6132ef0`, commit `d2f096475817d4666c364c820b0ca830f751cfc5`, published
`2026-11-09T12:46:51Z`, app `0.2.13`, Control/engine `0.1.59`; Windows CUDA 13 engine component `0.1.59`, build
`712fec6b4297+cuda13.0`, source `f-0213-rc`, archive `630,783,433` bytes, SHA-256
`3f071a7ccbbf3dcdefed8bff777896d8dd0b580417a078154a7d2c2402ec4158`, whose engine, server, Control and setup sources
equal the tag's because `712fec6b..d2f09647` changes only `packaging/make_model_release.py` and its test; Python
requirements, CUDA wheels, and `IQ3_S` / Coder `IQ1_M` / MTP / standard and tuned DFlash2 pins unchanged since `v0.2.12`,
reusing the `v0.2.11` lock) with stock OMP `18.18.3` (lightweight tag `21f1188cf88b2f534c092181968cd5a4d1a9c296`,
published `2026-11-09T03:59:10Z`, with `18.18.1` and `18.18.2` in between) across `rtxpro6000-win-a`, `rtx5090-win-a`,
`rtx3090-win-a` and the Mac Studio route (`mac-studio-client`). Six `v0.2.13` server profiles and both `v0.2.13` Mac
Studio routes are qualified: on `rtxpro6000-win-a`,
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` (standard DFlash2 pack,
which stock `v0.2.13` now runs at window 8, `--spec 8`, engine cap 8, instead of 6 on one `sm_120` card of 48 GB or
more) is current (`tests/candidate.py` `CURRENT`),
`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` (stock tuned DFlash2
pack, which stock `v0.2.13` now runs at `--draft-conf 0.55` instead of `0.35` alongside window 8 on this card) is a
qualified non-current alternate, and the rollback is the `v0.2.12` four-slot DFlash2 profile
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`; on `rtx5090-win-a`,
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` is the current 262K default (rolling back to
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`),
`win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3` is the current 131K Coder alternative (rolling back to
`win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0`, following the 262K pass without a separate A/B, as in `v0.2.12`),
and `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3` (full-model `IQ3_S` 131K low-RAM resident, stock's planner
pick for this host) is a qualified non-current alternate while the Coder stays the default; on `rtx3090-win-a` (RTX
4090 + RTX 3090),
`win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`
(pinning `--draft-conf 0.5` in `strata.drafting_args`, stock's slot-step value for the pair's per-card slots) is current,
with no qualified alternate and rolling back to the `v0.2.12` `env86gt` profile
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`; and
on `mac-studio-client`, `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` is current,
`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` is the qualified alternate route, and
the `v0.2.12` route `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0` is the rollback. Five
`v0.2.13` drafts remain unqualified with `"Not qualified"` blockers recorded in their manifests (`b2e9730`): pair
`env86gt` (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`)
and `env86gts` (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3`),
RTX 5090 `envgc` (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3`) and `IQ3_S` 262K
(`win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`), and PRO `df2conf055`
(`win11-rtxpro6000-iq3s-262k-slots4-df2conf055-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`).

- **Owner decisions and host state (2026-11-09):**
  - Under the owner rule, a profile becomes current only if every real-host gate passes and no paired metric is more than
    5% worse; overrides are explicit owner decisions, quoted verbatim. After the RTX 5090 was back in production
    (`~18:13Z`), the owner decided ([decision](DECISION.md)):
    - **PRO (`rtxpro6000-win-a`, host lock; the `v0.2.12` incumbent served between windows and after them):**
      `"Override the base as current, and also qualify the tuned pack as an alternate"` after the four-slot DFlash2
      `v0.2.13` vs `v0.2.12` A/B missed 11 of 90 checks and the tuned DFlash2 pack `v0.2.13` vs `v0.2.12` A/B missed 15
      of 90 checks from stock `v0.2.13` running DFlash2 window 8 (was 6) and tuned-pack `--draft-conf 0.55` (was `0.35`)
      on this card; the standard-pack `--draft-conf 0.55` draft (`df2conf055`) was withdrawn before install because the
      window-8 burstiness is not a confidence effect (the tuned pack at `0.55` showed it too).
    - **RTX 5090 (`rtx5090-win-a`, two fleet-custody windows, production NInfer down `~15:32–18:09Z` and `~18:25–19:19Z`,
      with full restoration each time: new `"WSL integration ... provisioned"` line, fleet return, health `200`):** after
      the 262K `envg` `v0.2.13` vs `v0.2.12` A/B passed 88 of 88 checks and both the 262K `envg` default (`d3c96fb`) and
      the 131K Coder alternative (`d0c2e28`) passed their requalify chains in the first window, did not adopt
      `STRATA_SPEC_COST` (`envgc`) after it missed 3 of 88 checks in its initial A/B and 2 of 88 in three
      replacement pairs (`1.012 < 1.02` targeted cold decode, with about one 4x largest-gap spike per three cold starts),
      and decided `"Qualify full-model IQ3_S 131K: prune old [rtx5090-win-a] roots for disk, then run its main gates"`
      and `"Also screen IQ3_S at 262K"` after the report-only `IQ3_S` 131K low-RAM screen against the `v0.2.13` Coder
      131K profile; in the second window, after deleting five superseded RTX 5090 roots for disk (`C:` `98.1 -> 156.6 GiB`
      free), `IQ3_S` 131K passed every gate (`6e2dda2`) to qualify as a non-current alternate (the Coder stays the
      default), while `IQ3_S` 262K passed install and was refused at first start
      (`"strata.kv_grow: elastic K/V line absent from this start's engine-log interval"`).
    - **Pair (`rtx3090-win-a`, RTX 4090 + RTX 3090, host lock):** `"Run the --draft-conf 0.5 main; it becomes current if
      every gate passes"` after the `env86gt` `v0.2.13` vs `v0.2.12` A/B missed 6 of 96 checks (all on one 32K request),
      the `STRATA_QSA_SPLIT_ATTN` arm (`env86gts`) missed 2 of 96 checks and its `1.02` targeted cold decode bar
      (`1.003 < 1.02`), and the `--draft-conf 0.5` arm (`df2conf05`) passed all 96 plain checks against `v0.2.12` with
      neutral targeted cold decode `1.021 [1.020, 1.049, 0.993]`; after its first requalify refused at install because a
      stock setup re-run carries `user_args` into `args` (fixed in `fb8740a`), its requalify chain (`18:43–19:26Z` at
      fixed runner `7c2d25e`) passed every gate (`440fa1b`) and made `df2conf05` the current pair profile.

### Paired cold-start version A/B (`v0.2.13` vs `v0.2.12`), engine `0.1.59` arms, DFlash2 confidence pins and RTX 5090 `IQ3_S` low-RAM screens

Observed on `2026-11-09` (UTC): ratios are `B / A` geometric means over three interleaved pairs (`A1 B1 B2 A2 A3 B3`, cold
starts), with `A` = each lane's qualified `v0.2.12` profile unless stated. On single-slot lanes, two-value `a / b`
workload ratios report `w1` (`512/512` at `c=1`) and `w3` (`32K/128` at `c=1`), and queue-probe pairs report `queue/0`
and `queue/1`; plain checks test the owner's 5% non-regression rule across the workload and probe metrics, while tuning
arms also check a targeted `1.02` (`+2%`) cold-decode bar. On one `sm_120` card of 48 GB or more
(our RTX PRO 6000), stock `v0.2.13` runs DFlash2 window 8 (`--spec 8`, engine cap 8) instead of 6 and `--draft-conf 0.55`
instead of `0.35` when the tuned `IQ3_S` pack is in use, writing both at every start (`drafting.apply`) rather than into
the config ([UPSTREAM.md](UPSTREAM.md#big-blackwell-dflash2-defaults)); server decode fields are reported, not gated, on
the four-slot PRO lane (`f649c07`, [UPSTREAM.md](UPSTREAM.md#engine-environment-and-timing-boundaries)). For the engine
`0.1.59` opt-in environment groups `spec_cost` (`{STRATA_SPEC_COST: "1"}`) and `qsa_split_attn`
(`{STRATA_QSA_SPLIT_ATTN: "1"}`), no stock log line proves either switch; proof is the reviewed delivery chain
([UPSTREAM.md](UPSTREAM.md#engine-0159-opt-in-groups)):

| Comparison (`B` over `A`) | Verdict & checks | Notable passes / ratios (`B/A`, with `[p1, p2, p3]` where reported) | Misses / refusal (`B/A`) | Disposition |
|---|---|---|---|---|
| **RTX 5090 262K `envg` (`v0.2.13` vs `v0.2.12`)**<br>`B`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`<br>`A`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0` | **PASS, 88 of 88 checks** | Throughput `w1` `1.006` / `w3` `0.995`, per-request `1.024 / 0.975`, TTFT p50 `0.989 / 1.002`, TPOT p50 `0.975 / 1.023`; cold decode `0.986–1.018`, prefill `0.998–1.075` | None | Qualified as RTX 5090 262K **current** (`d3c96fb`, `v0.2.12` 262K `envg` rollback); 131K Coder `win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3` follows this 262K pass without a separate A/B (as in `v0.2.12`) and qualifies as **current** 131K alternative (`d0c2e28`, `v0.2.12` 131K rollback) |
| **RTX 5090 262K `STRATA_SPEC_COST` arm (`envgc` vs `v0.2.13` `envg`)**<br>`B`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgc-strata0.2.13-omp18.18.3` (`v0.2.13` `envg` + `{STRATA_SPEC_COST: "1"}`)<br>`A`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` | **MISS 3 of 88**;<br>three replacement pairs **MISS 2 of 88**<br>(targeted cold decode **`1.012 < 1.02`**) | Throughput and TPOT `3–5%` better in every pair; targeted cold decode `1.012 < 1.02` | Initial A/B: one-request window **`1.119`**, largest gap p95 **`1.711`**, max **`1.771`**; three replacement pairs: largest gap p95 **`1.197`**, max **`1.212`** (about one `4x` largest-gap spike per three cold starts) | Not adopted (owner); draft with `"Not qualified"` blocker (`b2e9730`) |
| **RTX 5090 full-model `IQ3_S` 131K low-RAM resident screen vs `v0.2.13` Coder `IQ1_M` 131K**<br>`B`: `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3` (stock's planner pick for this host)<br>`A`: `win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3` | **Report-only screen**<br>(earlier private quality set: `IQ3_S` `58/60` vs Coder `54/60`) | Cold decode **`1.046`** (8K), **`1.093`** (32K), **`1.071`** (100K), **`1.094`** (warm 32K); queue decode **`1.086 / 1.086`**; per-request **`1.134 / 1.129`**; TPOT p50 **`0.881 / 0.885`**; throughput `w1` **`1.059`**. Engine: `11,616` expert slots in VRAM (`22.04 GiB`), `29.77 GiB` of experts page-locked in RAM | Empty-prompt decode **`0.763`**; throughput `w3` **`0.917`**; TTFT p50 **`1.528`** (512-token prompt) and **`1.122`** (32K); prefill **`0.61–0.95`** | Owner-decided requalify in second window (`"Qualify full-model IQ3_S 131K: prune old [rtx5090-win-a] roots for disk, then run its main gates"`, after deleting five superseded RTX 5090 roots for disk, `C:` `98.1 -> 156.6 GiB` free) passed every gate (`6e2dda2`); **qualified, non-current alternate** (the Coder stays the default) |
| **RTX 5090 full-model `IQ3_S` 262K low-RAM screen**<br>`B`: `win11-rtx5090-iq3s-262k-lowram-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3` | **First start refused**<br>(install passed; no A/B) | Install passed | First start refused: `"strata.kv_grow: elastic K/V line absent from this start's engine-log interval"` (the draft pins `--kv-grow`; this low-RAM resident start did not print stock's elastic K/V line) | Screened under `"Also screen IQ3_S at 262K"`; draft with `"Not qualified"` blocker (`b2e9730`) |
| **PRO four-slot DFlash2 (`v0.2.13` vs `v0.2.12`)**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`<br>`A`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` | **MISS 11 of 90**<br>(stock `v0.2.13` runs DFlash2 window 8, was 6, on this card; owner override) | Throughput `0.986–0.999`, per-request `0.964–1.015`, TTFT p50 `1.009–1.036`, TPOT p50 `0.981–1.033`; server decode reported `0.958–1.015` | Inter-output-event latency p95 **`1.171–1.188`** at every depth; `w2/c1` largest gap p95 **`1.173`**; `w2/c4` TTFT p95 **`1.118`**; `w2/c4` TPOT max **`1.067`** | Qualified as PRO **current** under `"Override the base as current, and also qualify the tuned pack as an alternate"` (`2af52b8`, `v0.2.12` four-slot DFlash2 is rollback); its Studio route `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3` also becomes current |
| **PRO tuned DFlash2 pack (`v0.2.13` at stock `--draft-conf 0.55` vs `v0.2.12`)**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`<br>`A`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` | **MISS 15 of 90**<br>(stock `v0.2.13` runs the tuned pack at `--draft-conf 0.55` and window 8 on this card; owner decision) | `w2/c2` per-request **`1.084`** and TPOT p50 **`0.928`** | Same burstiness: inter-output p95 **`1.169–1.172`**; `w2/c1` largest gap p95 **`2.151`**; `w2/c4` TTFT p50 **`1.129`** | Qualified as PRO **non-current alternate** under `"Override the base as current, and also qualify the tuned pack as an alternate"` (`8ab88b0`, with its Studio route) |
| **PRO standard pack + `--draft-conf 0.55` (`df2conf055`)**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2conf055-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3` | **Withdrawn before install**<br>(no A/B) | — | The window-8 burstiness is not a confidence effect: the tuned pack at `0.55` showed it too | Withdrawn before install; draft with `"Not qualified"` blocker (`b2e9730`) |
| **Pair `env86gt` (`v0.2.13` vs `v0.2.12`)**<br>`B`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`<br>`A`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0` | **MISS 6 of 96**<br>(all on one 32K request) | Everything else passes | `w3/c1` TPOT p50 **`1.054`**, p95 **`1.069`**, max **`1.070`**; largest gap p50 **`1.119`**, p95 **`1.239`**, max **`1.252`** | Superseded by `--draft-conf 0.5` variant; draft with `"Not qualified"` blocker (`b2e9730`) |
| **Pair `STRATA_QSA_SPLIT_ATTN` arm (`env86gts` vs `v0.2.12`)**<br>`B`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gts-strata0.2.13-omp18.18.3` (`{STRATA_QSA_SPLIT_ATTN: "1"}`)<br>`A`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0` | **MISS 2 of 96**<br>(targeted cold decode at 32K/100K/200K **`1.003 < 1.02`**) | Targeted cold decode at 32K/100K/200K `1.003 < 1.02` | `w1` largest gap p95 **`1.075`**, max **`1.092`** | Not adopted; draft with `"Not qualified"` blocker (`b2e9730`) |
| **Pair `--draft-conf 0.5` (`df2conf05` vs `v0.2.12`)**<br>`B`: `win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`<br>`A`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0` | **All 96 plain checks pass**;<br>targeted cold decode **`1.021 [1.020, 1.049, 0.993]`** (neutral: one pair below `1.00`) | Throughput `1.016 / 0.998`, per-request `1.027 / 0.993`, TTFT p50 `1.005 / 1.001`, TPOT p50 `0.973 / 1.009`; decode 100K `1.061`, warm 32K `1.054`, 32K `1.044` | None (first requalify refused at install when stock setup re-run carried `user_args` into `args`; fixed in `fb8740a`) | Adopted under `"Run the --draft-conf 0.5 main; it becomes current if every gate passes"`; requalify passed (`440fa1b`), **current** pair profile (`v0.2.12` `env86gt` is rollback) |

- **Engine `0.1.59` stage order on the pair:** measured on `rtx3090-win-a` before the pair version A/B (2026-11-09) and
  admitted in `6eb9f05`.

### Server qualification chains and Studio routes G23 (2026-11-09)

Each requalify run exits `1` when any coding-evaluator attempt fails; gate verdicts are separate. Because OMP `18.18.3`
changed agent-surface behavior (delegation bias `eager` -> `balanced` for these models, a system prompt that tells the
model to read small files whole, and bash locale/fork/console changes;
[UPSTREAM.md](UPSTREAM.md#stock-omp-18183-surface)), `G24` and task-set scores on OMP `18.18.3` are not comparable with
`18.18.0` (as noted under **How to read a section** above, `G24` gates complete, independently verified reporting rather
than task score):

| Host or route | Profile id & role | Gate outcomes & publication | `G24` `synthetic-1` / `G23` route details |
|---|---|---|---|
| `rtxpro6000-win-a`<br>(RTX PRO 6000) | `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`<br>(**current**, standard DFlash2 pack at window 8; rollback `v0.2.12` four-slot DFlash2) | Every gate passes, including `G15`, `G17` and `G18L`; published `2af52b8` | Scored **15/18** (`tool-loop` `0/3`, as `v0.2.12`) |
| `rtxpro6000-win-a`<br>(RTX PRO 6000) | `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3`<br>(**qualified, non-current alternate**, stock tuned DFlash2 pack at `--draft-conf 0.55`; not the rollback) | Every gate passes; published `8ab88b0` | Scored **15/18** (`tool-loop` `1/3`) |
| `rtx5090-win-a`<br>(RTX 5090 262K **default**) | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.13-omp18.18.3`<br>(**current**; rollback `v0.2.12` 262K `envg`) | Every gate passes, including `G15` and `G18L`; published `d3c96fb` | Scored **16/18** (`tool-loop` `1/3`) |
| `rtx5090-win-a`<br>(RTX 5090 131K Coder **alternative**) | `win11-rtx5090-coder-iq1m-131k-strata0.2.13-omp18.18.3`<br>(**current 131K alternative**; rollback `v0.2.12` 131K) | Every gate passes (follows the 262K pass without a separate A/B, as in `v0.2.12`); published `d0c2e28` | Scored **16/18** |
| `rtx5090-win-a`<br>(RTX 5090 full-model `IQ3_S` 131K low-RAM resident) | `win11-rtx5090-iq3s-131k-lowram-strata0.2.13-omp18.18.3`<br>(**qualified, non-current alternate**; the Coder stays the default) | Every gate passes, including `G15`, `G17`, `G18` and `G18L` (second window, after deleting five superseded RTX 5090 roots for disk, `C:` `98.1 -> 156.6 GiB` free); published `6e2dda2` | Scored **16/18** (`tool-loop` `1/3`; earlier private quality set: `IQ3_S` `58/60` vs Coder `54/60`) |
| `rtx3090-win-a`<br>(RTX 4090 + RTX 3090 pair) | `win11-rtx3090-rtx4090-iq3s-262k-df2conf05-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.13-omp18.18.3`<br>(**current**, `--draft-conf 0.5`; rollback `v0.2.12` `env86gt`) | First requalify refused at install (stock setup re-run carries `user_args` into `args`; fixed in `fb8740a`); rerun at fixed runner `7c2d25e` (`18:43–19:26Z`) passes every gate, including `G15`, `G17`, `G18` and `G18L`; published `440fa1b` | Scored **16/18** (`tool-loop` `1/3`) |
| `mac-studio-client` -> `rtxpro6000-win-a` | `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`<br>(**current** Studio route; rollback `v0.2.12` route) | `G23: pass` (`2af52b8`) | Missing key refused before launch; wrong key HTTP `401`; health RTT `5.8–7.7 ms`; stream TTFT `0.217 s`; tunnel drop failed the turn in flight with the transcript preserved; smoke `"ROUTE OK"` |
| `mac-studio-client` -> `rtxpro6000-win-a` | `client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3`<br>(**qualified alternate** Studio route, pinned to PRO tuned server) | `G23: pass` (`8ab88b0`) | Health RTT `6.1–6.8 ms`; stream TTFT `0.181 s`; smoke `"ROUTE OK"` |

### Source admissions, window fixes and restored state (2026-11-09)

- **Source, start-path, stage-order and feature admissions (`e2332b6` .. `6eb9f05` on `feat/strata-0213-omp-18183`, draft PR `alphastorm/omp-strata#81`):**
  - `e2332b6` added the `v0.2.13` fixtures; `52d4263` re-sliced and digest-pinned setup run-config assembly moved from
    `main()` into `strata_control/setup_config.py` (`config_for`, reached through a seam) plus `unsloth_default_env`
    (`STRATA_HC_Q8` is now the engine's own default for Unsloth UD files on CUDA; no change for our `qwen`/`coder`
    families); `186f796` updated the server start path (the launcher's parallel and GDN env stacks moved into the engine
    as Linux-only defaults, so our Windows groups stay explicit and are now checked against the engine's tables);
    `5dc12d8` completed the `drafting_fetch` review; `5c93890` admitted engine `0.1.59` for the existing env groups (all
    `22` grouped variables unchanged) and defaults note; `36b66bc` updated DFlash2 start expectations for stock's
    big-Blackwell defaults; `44a3468` rechecked the OMP `18.18.3` native CLI (no root flag changed); `c3612c7` updated
    `docs/UPSTREAM.md`; `4d8b7ba` drafted the `v0.2.13` profiles and routes; `c0cde07` keyed Unsloth fixtures by
    candidate; and `6eb9f05` admitted engine `0.1.59`'s stage order after the pair measurement
    ([UPSTREAM.md](UPSTREAM.md#strata-v0213-setup-and-start-path-review-engine-0159),
    [OMP 18.18.3 surface](UPSTREAM.md#stock-omp-18183-surface)). Engine `0.1.59` adds `strata --geometry` with no other
    CLI change, and Python requirements, CUDA wheels, and `IQ3_S` / Coder `IQ1_M` / MTP / standard and tuned DFlash2
    pins are unchanged since `v0.2.12` (the `v0.2.11` lock is reused).
  - Opt-in features added on their own profile ids: `strata.drafting_args` (`5dc6792`, `71a4d39`, `e720226`, `dca0afe`,
    `986adad`: one `--draft-conf` value from stock's own CUDA domain, written to stock `user_args` with stock
    `write_config` (the person's setting, which stock applies over its own at every start), and required on the
    start's server line; drafts pair `df2conf05`, stock's slot-step value for the pair's per-card slots which stock
    cannot compute on a split, and
    PRO `df2conf055`; [UPSTREAM.md](UPSTREAM.md#reviewed-dflash2-confidence-pins)); engine `0.1.59` env groups (`7cd8d15`,
    `bc35550`,
    `4a16563`, `4021c3b`: `spec_cost` = `{STRATA_SPEC_COST: "1"}`, stock's `sm_121` default cost-aware MTP window on RTX
    5090 arm `...-envgc-...`, and `qsa_split_attn` = `{STRATA_QSA_SPLIT_ATTN: "1"}`, split tensor-core decode attention
    with int8 KV on `sm_80+` on pair arm `...-env86gts-...`; [UPSTREAM.md](UPSTREAM.md#engine-0159-opt-in-groups)); and
    RTX 5090 `IQ3_S` low-RAM resident screen drafts (`bf490b8`, `337584e`, `2e32fc2`;
    [UPSTREAM.md](UPSTREAM.md#rtx-5090-low-ram-screen-planning)).
  - Not adopted: `STRATA_HC_UPMIX` (dropped after review: prompt path only, never decode), PLE/dense side group and
    `STRATA_PF_FUSED_NT`/`PF_BATCH` (no stock value, unverified on `sm_120`), `HC_UPMIX` on four slots, two-pass on the
    PRO/5090 (`v0.2.12` results stand), `--spec` pins (deferred), and OMP `ask.enabled: false`.
- **Fixes during the windows (`fb8740a`, `7c2d25e`, `a7762aa`):**
  - `fb8740a` `fix(install)`: a stock `v0.2.13` setup re-run over an installed root merges the earlier `user_args` into
    `args` (`carry_user_args`), so every requalify of a `strata.drafting_args` profile refused; verification now removes
    each pinned option only when it occurs once with exactly its pinned value (DeepSeek's carried `--experts 6` handled
    the same way), with stock proof against the real `carry_user_args`.
  - `7c2d25e`, `a7762aa` `test(releases)`: `v0.2.13` draft ledgers hold only their own receipts.
- **Restored state after the 2026-11-09 windows and draft blockers (`ab96ab4`, `b2e9730`):**
  - `rtxpro6000-win-a`: host-lock windows; the `v0.2.12` incumbent served between windows and after them (moving from
    `v0.2.12` to `v0.2.13` when the PR lands).
  - `rtx5090-win-a`: two fleet-custody windows, with production NInfer down `~15:32–18:09Z` and `~18:25–19:19Z`, and full
    restoration each time (new `"WSL integration ... provisioned"` line, fleet return, health `200`); five superseded RTX
    5090 roots were deleted before the second window for disk (`C:` `98.1 -> 156.6 GiB` free).
  - `rtx3090-win-a`: host-lock windows.
  - `ab96ab4` records the restored state on all three hosts and both Studio routes, and `b2e9730` records `"Not
    qualified"` blockers on the five `v0.2.13` drafts (pair `env86gt` and `env86gts`, RTX 5090 `envgc` and `IQ3_S` 262K,
    PRO `df2conf055`).

### Earlier windows: Strata v0.2.12 (2026-11-07–08)

The 2026-11-07–08 `v0.2.12` section below remains the rollback qualification record for the PRO four-slot DFlash2 profile
(`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`), the RTX 5090 262K
default (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`) and 131K alternative
(`win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0`), the pair two-pass DFlash2 profile
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`),
and the Mac Studio route (`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`), and earlier
qualified history for the PRO `df2tuned` alternate, the pair `env86g-parking` profile and the Studio `df2tuned` route;
its headings and tables keep the roles those profiles held when the section was written.

## Strata v0.2.12 windows (2026-11-07): stock OMP 18.18.0

This section records the `2026-11-07 17:53Z` to `2026-11-08 00:30Z` host measurements (all times UTC, under exclusive
use of the fleet granted by the owner) for stock Strata `v0.2.12` (annotated tag object
`123bad4acd5fd3fe70f02ad4c938e0c360efe5e5`, commit `146df3c468739147f520ac3816de806f71232571`, published
`2026-11-07T08:54:40Z`, app `0.2.12`, Control/engine `0.1.58`; Windows CUDA 13 engine component `0.1.58`, build
`8a42a9457db6+cuda13.0`, source `f-0212-rc`, archive `630,769,464` bytes, SHA-256
`3311443ba9172154adc99c48668c4187d60864e3b6cafe5d9aa39b035e4f9f34`, whose engine source differs from the tag only by a
pre-`sm_70` `#if` in `src/kernels/cuda/qsa_select.cu` that our architectures `75/86/89/120` never compile; Python
requirements, CUDA wheels, and `IQ3_S` / Coder `IQ1_M` / MTP / standard DFlash2 pins unchanged since `v0.2.11`, reusing
`locks/strata-python-cp313-win_amd64-strata0.2.11.txt` and passing it explicitly when drafting the 131K lane from
`v0.2.10`) with stock OMP `18.18.0` (lightweight tag `b5a6b2f7e5b6606b6562e678ead83f21738f34a0`, published
`2026-11-07T01:49:16Z`, with `18.17.0` in between) across `rtxpro6000-win-a`, `rtx5090-win-a`, `rtx3090-win-a` and the
Mac Studio route (`mac-studio-client`). Six `v0.2.12` server profiles and both qualified `v0.2.12` Mac Studio routes are
qualified: on `rtxpro6000-win-a`,
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` (standard DFlash2 pack)
is current (`tests/candidate.py` `CURRENT`),
`win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` (stock tuned DFlash2
pack `qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack`, `339,694,592` bytes, SHA-256
`4df2e5ab2b47c064afbe662e16e4f06569877125c2d0e2123a4ac755266c664c`) is a qualified non-current alternate (faster with two
concurrent requests, slower one at a time, and not the rollback), and the rollback is the `v0.2.11` DFlash2 profile
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`; on `rtx5090-win-a`,
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0` is the 262K default (rolling back to
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`) and
`win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0` is the 131K qualified alternative (rolling back to
`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`, qualified on the same window's passing 262K A/B without an A/B
of its own, [the same way `v0.2.10` did](#strata-v0210-windows-2026-11-03-stock-omp-18160)); on `rtx3090-win-a` (RTX 4090 + RTX 3090),
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`
(two-pass `STRATA_SELECT_TWO_PASS=1`; its id drops `-parking` only to stay within the 120-character profile-id limit while keeping the same
stock setup tips, including automatic conversation parking) is current, rolling back to
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`;
and on the Mac Studio, `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0` is current,
`client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0` is the qualified alternate route, and
`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` is the rollback. The PRO two-pass server
(`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0`) and route
(`client-rtxpro6000-262k-df2-pledirect-kvvram-envpgt-strata0.2.12-omp18.18.0`), the RTX 5090 two-pass draft
(`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`, with its failing `G18` ledger published)
and the pair W4A8 draft
(`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0`)
remain drafts with their reasons recorded in their manifests.

- **Owner decisions and host state (2026-11-07/08):**
  - Before and during the `2026-11-07` to `2026-11-08` windows, the owner approved session logoffs (`"Log off session 3
    now"` on the PRO host and `"Log off session 2 now"` on the RTX 5090 host), version A/B and tuned-pack overrides, arm
    dispositions, and the post-window reboot of the RTX 5090 host ([decision](DECISION.md)):
    - **PRO (`rtxpro6000-win-a`):** overrode the `v0.2.12` four-slot DFlash2 profile's 1 of 90 version A/B miss against
      `v0.2.11` (`2026-11-07 ~18:51Z`: `"Override: main + G23 after tuned arm"`), directed a direct A/B of the stock
      tuned DFlash2 pack against the `v0.2.12` standard-pack profile after its A/B against `v0.2.11` missed 6 of 90
      checks (`"Measure tuned vs v0.2.12 base first"`), overrode the tuned pack's 3 of 90 misses against the `v0.2.12`
      standard-pack profile to qualify the tuned profile and its Studio route as non-current alternates (`"Override:
      qualify tuned as alternate"`), and kept the standard-pack profile current after the PRO `STRATA_SELECT_TWO_PASS=1`
      arm missed 3 of 96 checks (`"Keep the base"`).
    - **RTX 5090 (`rtx5090-win-a`):** after the 262K `envg` profile passed all 88 version A/B checks against `v0.2.11`
      and the 262K two-pass (`STRATA_SELECT_TWO_PASS=1`) arm passed all 96 A/B checks against `v0.2.12` `envg` (and all
      88 checks in its product with the version A/B against `v0.2.11`) but failed `G18` in its requalify chain, kept
      `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0` as the 262K default (`"Keep envg
      current"`), qualified `win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0` as the 131K alternative (passing
      every gate including `G15` on the same window's passing 262K A/B, with `v0.2.10` as rollback), and approved
      rebooting the RTX 5090 host after three WSL-integration repairs failed during restoration.
    - **Pair (`rtx3090-win-a`, RTX 4090 + RTX 3090):** overrode the `v0.2.12` DFlash2 profile's 7 of 88 version A/B
      misses against `v0.2.11` (`2026-11-07 ~18:51Z`: `"Override: main, then the arms"`), adopted the two-pass arm
      `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`
      as the pair's current profile after it passed all 96 A/B checks (`0.976 [0.981, 0.977, 0.970]` 200K cold TTFT) and
      every gate in its requalify chain (with the qualified `v0.2.12` `env86g-parking` profile as its rollback), and left
      the `STRATA_IQ4_W4A8=2` (`env86gw`) arm as an unqualified draft after its A/B missed both the cold-TTFT bar and
      32K decode.

### Paired cold-start version A/B (`v0.2.12` vs `v0.2.11`), PRO tuned DFlash2 pack, two-pass selection and pair W4A8 arms

Observed on `2026-11-07`: each comparison ran a paired cold-start A/B of three pairs (`A1 B1 B2 A2 A3 B3`), reporting the
`B/A` paired geometric mean with the per-pair ratios in brackets. Server decode fields are reported, not gated, on the
four-slot PRO lane because `v0.2.12` counts slot admission in decode time (`None` while an admission drains; `f649c07`,
[UPSTREAM.md](UPSTREAM.md#engine-environment-and-timing-boundaries)). Engagement was proven in every arm `B` block from
the engine's own log lines (the two-pass ON line and statistics with no `"not used"` line, and the W4A8 ON line and exit counters):

| Comparison (`B` over `A`) | Verdict & checks | Notable passes (`B/A`, with `[p1, p2, p3]` where reported) | Misses (`B/A`, with `[p1, p2, p3]` where reported) | Disposition |
|---|---|---|---|---|
| **PRO DFlash2 (`v0.2.12` vs `v0.2.11`, four slots)**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` | **1 of 90 checks missed**<br>(server decode fields reported, not gated; owner override) | Two concurrent short requests: p95 TPOT `1.037`, max request latency `0.957`; total throughput `1.015 / 1.007 / 1.015` at one / two / four requests, `0.993` for four 32K requests; TTFT p50 at four requests `0.867`; cold prefill `0.994–1.007` | Two concurrent short requests, maximum time per output token (TPOT) **`1.057 [0.978, 0.976, 1.239]`** (third pair only) | Qualified as PRO **current** (`2026-11-07 ~18:51Z`: `"Override: main + G23 after tuned arm"`); `v0.2.11` DFlash2 is rollback |
| **RTX 5090 262K (`v0.2.12` vs `v0.2.11`)**<br>`B`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0` | **Passed all 88 checks** | Throughput `1.000 / 0.997`, TTFT p50 `1.005 / 1.001`, decode `0.980–1.012`, prefill `0.983–1.063` | None | Qualified as RTX 5090 262K **default** (`v0.2.11` `envg` rollback); 131K alternative also qualifies on this window's passing 262K A/B |
| **Pair DFlash2 (`v0.2.12` vs `v0.2.11`)**<br>`B`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0` | **7 of 88 checks missed**<br>(owner override) | Throughput `1.006 / 0.994`, TTFT p50 `1.003 / 1.004`, cold 32K decode `1.084`, 100K `1.005`, warm 32K `1.012` | Cold 8K decode **`0.943 [0.967, 0.917, 0.947]`** and its server decode time **`1.060`**; depth-0 decode while a second request waits **`0.937 [0.929, 0.935, 0.946]`** and its decode time **`1.068`**; 32K prompt longest gap p95 **`1.050`** and max **`1.051`**; depth-0 p95 gap between output events **`1.052`** | Qualified as pair **rollback** (`2026-11-07 ~18:51Z`: `"Override: main, then the arms"`) behind the adopted `v0.2.12` two-pass profile |
| **PRO tuned DFlash2 pack vs `v0.2.11` DFlash2**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` | **6 of 90 checks missed** | TTFT p50 at two / four requests `0.745 / 0.684` | Two requests TPOT p95 **`1.162 [1.153, 1.175, 1.157]`** and max **`1.211 [1.200, 1.224, 1.209]`**; two requests latency p95 **`1.055 [1.083, 1.135, 0.956]`** and max **`1.080 [1.126, 1.173, 0.954]`**; four 32K requests per-request throughput p50 **`0.941 [0.921, 0.998, 0.907]`** and TPOT p50 **`1.062 [1.085, 1.001, 1.101]`** | Followed by direct A/B against the `v0.2.12` standard-pack profile (`"Measure tuned vs v0.2.12 base first"`) |
| **PRO tuned DFlash2 pack vs `v0.2.12` standard-pack profile**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` | **3 of 90 checks missed**<br>(owner override as alternate) | Two requests faster: per-request throughput p50 **`1.165 [1.023, 1.230, 1.258]`**, TPOT p50 **`0.873 [0.978, 0.828, 0.820]`** (showing the TTFT gains against `v0.2.11` came from `v0.2.12` itself, not from the pack) | One request per-request throughput p50 **`0.942 [0.936, 0.935, 0.955]`** and TPOT p50 **`1.062 [1.068, 1.070, 1.048]`**; four requests TTFT p50 **`1.138 [1.484, 1.399, 0.711]`** | Qualified as PRO **non-current alternate** (`"Override: qualify tuned as alternate"`, not the rollback) |
| **PRO two-pass (`STRATA_SELECT_TWO_PASS=1`) vs `v0.2.12` profile**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpgt-parking-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0` | **3 of 96 checks missed** | Targeted 200K cold TTFT **`0.978 [0.982, 0.975, 0.977]`** (passed its at-most-`0.98` bar) | Four requests TTFT p50 **`1.114 [0.988, 1.038, 1.345]`**; two requests TPOT p95 **`1.056 [1.016, 1.161, 0.998]`** and max **`1.076 [1.017, 1.216, 1.008]`** | Not adopted (`"Keep the base"`); server and route kept as drafts |
| **RTX 5090 262K two-pass (`STRATA_SELECT_TWO_PASS=1`) vs `v0.2.12` `envg`**<br>`B`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0` | **Passed all 96 checks**<br>(product with version A/B also passed all 88 checks against `v0.2.11`) | Targeted 200K cold TTFT **`0.971 [0.969, 0.971, 0.974]`** (passed its at-most-`0.98` bar) | None in A/B (requalify chain failed `G18`) | Not adopted (`"Keep envg current"`); kept as draft with published failing `G18` ledger |
| **Pair two-pass (`STRATA_SELECT_TWO_PASS=1`) vs `v0.2.12` pair profile**<br>`B`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0` | **Passed all 96 checks** | Targeted 200K cold TTFT **`0.976 [0.981, 0.977, 0.970]`** (passed its at-most-`0.98` bar) | None | Adopted and qualified as pair **current** profile (`v0.2.12` `env86g-parking` is rollback) |
| **Pair W4A8 (`STRATA_IQ4_W4A8=2`) vs `v0.2.12` pair profile**<br>`B`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gw-strata0.2.12-omp18.18.0`<br>`A`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0` | **Missed**<br>(no requalify chain ran) | RTX 3090 stage's kernel ran about `6.8K` `IQ4_NL` products per block and declined about `11.2K` for GPU architecture | Cold-TTFT geomean over 8K / 32K / 100K **`1.000`** (`1.001, 1.003, 0.998`) against the required at most `0.98`; 32K decode **`0.917 [0.926, 0.932, 0.894]`** (server decode time **`1.089`**); one request max inter-token gap p50 **`1.153 [1.027, 1.378, 1.084]`** | Not adopted; kept as draft, and the planned combined two-pass + W4A8 arm did not run |

- **Engine `0.1.58` stage order on the pair (`rtx3090-win-a`, measurement start 2026-11-07, admitted in `a5989fe`):**
  parsed complete, RTX 3090 first, RTX 4090 last, layers `0–23 / 24–47`, expert caches `19.40 / 17.90 GiB` (`v0.2.11`:
  `19.41 / 17.90`).

### Server qualification chains, Studio routes G23 and kept G18 failure (2026-11-07–08)

Each requalify run exits `1` when any coding-evaluator attempt fails; gate verdicts are separate. Every qualified
`v0.2.12` server ledger has **21 pass and 3 not applicable** (`G22`, `G23`, `G25`), and both qualified `v0.2.12` Mac
Studio routes have `G23: pass`. Because OMP `18.17.0` changed the `wait` ladder and prompt text, `G24` scores on OMP
`18.18.0` are not comparable across OMP versions (`v0.2.11` with OMP `18.16.0` scored `17/18` with `tool-loop` `2/3` on
the RTX 5090 262K default; as noted under **How to read a section** above, `G24` gates complete, independently verified reporting rather than task score). The RTX 5090 two-pass draft (`envgt`) keeps its `G18` failure in its published ledger:

| Host or route | Profile id & role | Gate outcomes & ledger | `G24` `synthetic-1` / `G23` route details |
|---|---|---|---|
| `rtxpro6000-win-a`<br>(RTX PRO 6000) | `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`<br>(**current**, standard DFlash2 pack; rollback `v0.2.11` DFlash2) | Every gate passed (`G10–G21`, `G26`), pilot passed; **21 pass, 3 not applicable** (`G22`, `G23`, `G25`) | Scored **15/18** (`tool-loop` `0/3`, the other five tasks `3/3`) |
| `rtxpro6000-win-a`<br>(RTX PRO 6000) | `win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking-strata0.2.12-omp18.18.0`<br>(**qualified alternate**, stock tuned DFlash2 pack; not the rollback) | Every gate passed (`G10–G21`, `G26`); **21 pass, 3 not applicable** (`G22`, `G23`, `G25`) | Scored **15/18** (`tool-loop` `0/3`) |
| `rtx5090-win-a`<br>(RTX 5090 262K **default**) | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.12-omp18.18.0`<br>(**current**; rollback `v0.2.11` `envg`) | Every gate passed (`G10–G21`, `G26`); **21 pass, 3 not applicable** (`G22`, `G23`, `G25`) | Scored **15/18** (`tool-loop` `0/3`; `v0.2.11` scored `17/18`, `tool-loop` `2/3`, not comparable across OMP versions) |
| `rtx5090-win-a`<br>(RTX 5090 131K **alternative**) | `win11-rtx5090-coder-iq1m-131k-strata0.2.12-omp18.18.0`<br>(**qualified alternative**; rollback `v0.2.10` 131K) | Every gate passed, including `G15` (which failed twice on `v0.2.11`); qualified on the same window's passing 262K A/B without an A/B of its own; **21 pass, 3 not applicable** (`G22`, `G23`, `G25`) | Scored **15/18** (`bugfix-a` `2/3`, `tool-loop` `1/3`) |
| `rtx3090-win-a`<br>(RTX 4090 + RTX 3090 pair) | `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt-strata0.2.12-omp18.18.0`<br>(**current**, two-pass `STRATA_SELECT_TWO_PASS=1`) | Every gate passed (`G10–G21`, `G26`), pilot passed; **21 pass, 3 not applicable** (`G22`, `G23`, `G25`) | Scored **15/18** (`bugfix-b` `2/3`, `tool-loop` `1/3`) |
| `rtx3090-win-a`<br>(RTX 4090 + RTX 3090 pair) | `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.12-omp18.18.0`<br>(**rollback**, standard DFlash2) | Every gate passed (`G10–G21`, `G26`); **21 pass, 3 not applicable** (`G22`, `G23`, `G25`) | Scored **15/18** (`tool-loop` `0/3`) |
| `rtx5090-win-a`<br>(RTX 5090 262K two-pass candidate) | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`<br>(**unqualified draft**; `envg` stays current) | **`G18` failed** (below); every other gate passed; published ledger keeps its `G18` failure | Scored **17/18** (`multifile-regression` `2/3`) |
| `mac-studio-client` -> `rtxpro6000-win-a` | `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`<br>(**current** Studio route; rollback `v0.2.11` `df2` route) | `G23: pass` | Missing key refused before launch; wrong key HTTP `401`; health RTT `5.9–7.4 ms`; stream TTFT `0.247 s`; a tunnel drop failed the turn in flight with the transcript kept; nonce recalled after tunnel, client and verified server restarts; `launch-omp` smoke answered |
| `mac-studio-client` -> `rtxpro6000-win-a` | `client-rtxpro6000-262k-df2tuned-pledirect-kvvram-envpg-strata0.2.12-omp18.18.0`<br>(**qualified alternate** Studio route, pinned to PRO tuned server) | `G23: pass` | Health RTT `12.1–16.1 ms`; stream TTFT `0.317 s`; same missing-key refusal, wrong-key HTTP `401`, in-flight tunnel-drop failure, transcript-kept nonce recall after tunnel, client and verified server restarts, and `launch-omp` smoke |

- **Kept failure in the 2026-11-07–08 windows — RTX 5090 262K two-pass `G18` long-session compaction (`rtx5090-win-a`, profile kept as draft):**
  on `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envgt-strata0.2.12-omp18.18.0`, because from the 21st turn onward
  the model read only the first `100` and last `3` lines of each document, the long-session probe never compacted in
  `40` read turns (reaching a peak engine prompt of `207,269` tokens). Every other gate in the chain passed (`G24`
  `17/18`, `multifile-regression` `2/3`). Under the owner's decision (`"Keep envg current"`), the `envgt` profile is not adopted
  and its published ledger retains the `G18` failure.

### Source admissions and restored state (2026-11-07–08)

- **Source, start-path, stage-order and arm admissions (`c45bbc5` .. `a5989fe` on `feat/strata-0212-omp-18180`, draft PR `alphastorm/omp-strata#80`):**
  - `c45bbc5` added the `v0.2.12` fixtures; `dbcda50` admitted the single changed setup planning statement (the Strix
    Halo / unified-memory expert-cache note) by its exact digest; `91c90a9` completed the server review for engine
    `0.1.58` (only `strata_control/drafting.py` changed on the start path) and `9022221` keyed the `drafting_fetch.py`
    pin by release; `6b0cdf6` admitted engine `0.1.58` for the existing environment groups (all `20` grouped variables
    unchanged) and defaults note; `8c2af4b` pinned OMP `update.auto: false` and `startup.setupWizard: false` (because
    OMP `18.17`'s setup wizard can turn on background self-update) and added `G18`'s `discarded-turn` filter; `f649c07`
    handled and labelled `v0.2.12` server timing accounting (batch-slot decode includes admission and reports `None`
    while an admission drains); `e4bd160` updated `docs/UPSTREAM.md` and `42006a0` drafted the `v0.2.12` profiles and
    routes; `243290e` reviewed the OMP `18.17` display flags (`--spinner-interval`, `--max-fps`, `--motion`) in the
    launcher policy; and `a5989fe` admitted engine `0.1.58`'s stage order after the pair measurement
    ([UPSTREAM.md](UPSTREAM.md#strata-v0212-setup-and-start-path-review-engine-0158),
    [OMP 18.17.0 and 18.18.0 surface](UPSTREAM.md#stock-omp-18170-and-18180-surface)).
  - `210e2a8` .. `74c5fdb` and `758b947` admitted and drafted the PRO stock tuned DFlash2 pack arm
    (`qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack`, `339,694,592` bytes, SHA-256
    `4df2e5ab2b47c064afbe662e16e4f06569877125c2d0e2123a4ac755266c664c`, used by stock only on one resident `cuda/iq3_s`
    card so the multi-card pair and Coder RTX 5090 never qualify; [UPSTREAM.md](UPSTREAM.md#tuned-dflash2-pack-pro-arm));
    `d140bd1` and `a88009d` admitted the per-group minimum engine `0.1.58` opt-in groups `select_two_pass`
    (`STRATA_SELECT_TWO_PASS=1`, token `t`, CUDA `sm_80+`) and `iq4nl_w4a8` (`STRATA_IQ4_W4A8=2`, token `w`, RTX 3090
    stage only; [UPSTREAM.md](UPSTREAM.md#stock-engine-opt-in-groups-v0212--0158)). Deliberately left unpinned and not
    adopted ([UPSTREAM.md](UPSTREAM.md#variables-deliberately-left-unpinned)): `STRATA_ADAPT_FETCH` (PRO all-resident,
    pair layer split refused, RTX 5090 hit rate `99.4–99.9%`), `STRATA_VNNI_TIER` (no lane's CPU qualifies),
    `STRATA_DF2_GATE` / `STRATA_DF2_ROW_MS` (measured only on Mac; `ROW_MS` uncalibrated), peer-mode / HIP / Linux / gfx
    / diagnostic and file-writing variables, `undeclared_tool_calls: call` (OMP declares its tools, so the server key is
    unreachable), OMP `display.shellVisualization` / `spotlight` pins (UI/defaults only), and OMP's optional `ovnfs`
    binary on `PATH` (absent on every lane; [OMP 18.17.0 and 18.18.0 surface](UPSTREAM.md#stock-omp-18170-and-18180-surface)).
- **Restored state after the 2026-11-07–08 windows:**
  - `rtxpro6000-win-a`: the PRO host's incumbent `v0.2.11` DFlash2 server was stopped before the windows and restarted
    afterwards (`healthy`); OCR containers were left exited as found.
  - `rtx5090-win-a`: the RTX 5090 production container was down from about `17:59Z` to `02:46Z`: the host supervisor's
    three WSL-integration repairs failed (Docker Desktop's `wsl.exe whoami`: `Wsl/Service/0x8007274c`), so after an
    owner-approved reboot of the RTX 5090 host, fleet return completed with health `200`.
  - `rtx3090-win-a`: idle before and after.

### Earlier windows: Strata v0.2.11 (2026-11-06–07)

The 2026-11-06 `v0.2.11` sections below remain the rollback qualification record for the PRO DFlash2 profile
(`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`), the RTX 5090 262K
default (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`) and the Mac Studio route
(`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`), the comparison-only record for the PRO
quality-first evaluation and `UD-Q4_K_XL` screen, and earlier qualified history for the PRO `batchmtp` profile, the pair
`df2` profile and the Studio `batchmtp` route; their headings and tables keep the roles those profiles held when the
sections were written.

## Quality-first comparison on the PRO (2026-11-06): stock Strata v0.2.11, stock OMP 18.16.0

This section records a comparison-only quality-first evaluation on `rtxpro6000-win-a` asking whether a higher-fidelity
Qwen quantization or stock Strata's DeepSeek V4.1-Flash family beats the PRO's qualified four-slot `IQ3_S` DFlash2
profile on the owner's coding work when latency is only a practical constraint. Every arm ran the full product path —
stock OMP `18.16.0` (OMP `18.17.0`, released `2026-11-06T05:12:54Z`, was out of scope) over an SSH loopback tunnel to
authenticated local stock Strata `v0.2.11` (tag commit `c3b3f5035506f3e966f1b4b7b188aeaabae92f1d`, Qwen engine `0.1.57`
and separate DeepSeek package `strata-dsv41-0.1.57-windows-x86_64-cuda-cuda13.tar.gz`, `422,613,464` bytes, SHA-256
`bc1cbecc7553c3022e369bc1e0ed4f360ea26daf5dfc386dd0dde75be417941e`); no measurement is engine-only. Nothing beat the
incumbent: the qualified PRO profile
[`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json)
(21 pass, 3 not applicable, re-verified at `f9f9680`), the Mac Studio route
[`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/qualification.json)
(G23 pass), and their `v0.2.11` batch-MTP rollbacks stay unchanged
([decision](DECISION.md#update-2026-11-07-quality-first-comparison-on-the-pro-keeps-the-four-slot-iq3_s-incumbent)), and
all three comparison profiles keep `status: "draft"` with every gate `not_run` in `releases/<id>/qualification.json`.

### Tuple, arms and host screens

Every Unsloth shard in this campaign pins `unsloth/Qwen3.8-Flash-Next-GGUF` revision
`38bb39ee97821de2c9009abb7e93950eec396e66` (Unsloth `v3.1` revision `d96201194f103c906994f283f504209dc8d2a10c`
`UD-Q4_K_XL` contains the same `1,224` tensors with identical types and shapes, re-sharded, and is not admitted;
[UPSTREAM.md](UPSTREAM.md#pro-quality-first-one-slot-comparison-admissions)). On `rtxpro6000-win-a`, `UD-Q5_K_XL` and
`DeepSeek IQ2_XS` ran unrecorded screen steps `install, keygen, start, g10, tracer, g14, g14q, perf, stop`, and
one-slot `IQ3_S` ran the same sequence without `g14` and `g14q`; screen `perf` took one sample per depth (not a
six-block cold-start A/B), and all three screened drafts passed 3/3 typed-tool tracers (five typed calls per run —
`read` ×3, `edit`, `bash` — with unique IDs, every call answered, and only the local provider; memory-plan figures below
keep each engine's startup-log units, where Qwen `0.1.57` logs `GiB` for VRAM and the RAM arena as a byte count, given
here in `GB`, and DeepSeek `ds4-0.1` logs `GB`):

| Arm | Profile id & ledger | Fingerprint (16) | Model bytes | Screen steps & start | 32K decode / prefill (`tok/s`) | TTFT 32K / 100K | `G10` resources (commit limit `219.70 GiB`) | Engine startup memory plan (`0.1.57` / `ds4-0.1`) |
|---|---|---|---:|---|---|---|---|---|
| Incumbent (`IQ3_S`, four slots, reference) | `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` ([qualified ledger](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/qualification.json)) | `bc2c503183b7800e` | `83,617,662,656` | Qualified profile (`v0.2.11` DFlash2 A/B reference) | `379.7` / `9,165` | `3.62 s` / `11.04 s` | Qualified ledger (`73,496 MiB` GPU, `127.14 GiB` avail RAM, `83.55 GiB` commit avail) | All `24,576` experts in VRAM, four slots, `8,192 MiB` conversation cache |
| `IQ3_S` (one slot, draft) | `win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0` ([draft ledger](../releases/win11-rtxpro6000-iq3s-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0/qualification.json)) | `ab60b81c833c3839` | `83,617,662,656` (same files) | All rc `0`; `G10`/tracer pass; start `71 s` | `404.4` / `8,610` | `3.86 s` / `11.56 s` | GPU `58,278 MiB`; min avail RAM `129.3 GiB`; commit avail `99.42 GiB` | Arena `50.3 GB` pinned; all `24,576` experts in `46.84 GiB` VRAM; conversation cache `8,192 MiB` |
| `UD-Q5_K_XL` (one slot, draft) | `win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0` ([draft ledger](../releases/win11-rtxpro6000-ud-q5kxl-262k-df2-pledirect-kvvram-envg-parking-strata0.2.11-omp18.16.0/qualification.json)) | `81cd556548451fe3` | `158,286,406,650` | All rc `0`; `G10`/tracer/`G14`/`G14Q` pass; start `85.7 s` | `296.7` / `7,712` | `4.29 s` / `12.83 s` | GPU `95,794 MiB`; min avail RAM `83.6 GiB`; commit avail `17.12 GiB` | Arena `98.4 GB` pinned; `22,209` of `24,576` experts in `82.80 GiB` VRAM (`98.4–99.9%` decode hit rate); conversation cache `5,888 MiB`; K-quant prompt kernels |
| DeepSeek `IQ2_XS` (six experts, draft) | `win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0` ([draft ledger](../releases/win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0/qualification.json)) | `51642761f608b94c` | `273,803,809,901` | All rc `0`; `G10`/tracer/`G14`/`G14Q` pass; start `54.8 s` | `45.7` / `2,655` | `12.4 s` / `32.4 s` | GPU `95,692 MiB`; min avail RAM `114.0 GiB`; commit avail `52.70 GiB` | Six experts per token (`full quality`); DSpark declined under `auto`; `9,344` of `15,360` experts in VRAM (`91.05 GB`); `6,016` CPU-lane experts copied into RAM (`58.4 GB`); no disk slots |

- **Wire and session contract:** stock OMP `18.16.0` sends `reasoning_effort: "high"`, `max_tokens: 32768`, streaming and
  `11` tools on every arm; Qwen arms add `chat_template_kwargs: {preserve_thinking: true}`, while stock DeepSeek maps
  `"high"` to template value `75` (`"max"` = `100` is not used) and its server log caps thinking at `24,576` of `32,768`
  tokens ([DeepSeek admission](UPSTREAM.md#deepseek-v41-flash-comparison-admission)). The one-slot drafts render
  `maxInFlightRequests: 1` (the four-slot incumbent renders `4`), with every chat role routed locally, retry and model
  fallback off, speculative compaction off, foreign providers disabled, and project MCP and OTLP telemetry off.

### 22-task quality-first evaluation (`scripts/eval_taskset.py`) and untested Qwen quants

The evaluation ran 22 frozen tasks from the private task set (`16` hard + `6` base; each task's own budgets; one attempt
per task and arm via `scripts/eval_taskset.py`; real stock OMP `18.16.0` sessions through an SSH loopback tunnel), after
a fairness check before trial 1. Under the owner's pre-registered decision rule, a second trial would run for the top
two arms only if their trial-1 pass counts were within 2 passes, and a candidate replaces the incumbent only with a
paired net of at least **`+3`** passes and a critical-failure count no more than the incumbent's count **`+ 2`**;
otherwise the incumbent stays. Because the incumbent passed `21/22` in trial 1, no candidate could exceed `+1`, and the
DeepSeek trial was stopped after `7` of `22` tasks, once it could no longer reach the bar:

| Arm | Passed | Median agent s | Total agent s | Critical | Aborts | Protocol errors |
|---|---:|---:|---:|---:|---:|---:|
| Incumbent (`IQ3_S`, four slots) | 21/22 | 215.4 | 5,498.6 | 1 (one mid-run empty reply; the task passed) | 0 | 0 |
| `UD-Q5_K_XL` (one slot) | 20/22 | 278.9 | 6,437.9 | 0 | 0 | 0 |
| DeepSeek `IQ2_XS` (six experts) | 5/7 (stopped after 7 of 22 tasks) | 1,259.0 | 11,174.5 (7 tasks) | 1 (a passing attempt reached its task time budget: OMP deadline abort, exit 1) | 0 | 1 (`stop_reason_aborted`, the same deadline stop) |

- **Paired with the incumbent:**
  - `UD-Q5_K_XL` (one slot): both passed `19`, incumbent-only `2`, candidate-only `1`, neither `0`, paired net **`-1`**
    (exact sign test `p = 1.0`), median wall ratio `1.26`; both misses were hidden-verifier failures, not aborts.
  - DeepSeek `IQ2_XS` (six experts), over the `7` tasks it ran: both passed `5`, incumbent-only `2`, candidate-only `0`,
    neither `0`, paired net **`-2`** (exact sign test `p = 0.5`), median wall ratio `3.9`; both misses were
    hidden-verifier failures on tasks the incumbent passed, so its best reachable net over `22` tasks was `-1`. The
    owner stopped the trial there; the interrupted eighth attempt is unscored and `14` tasks did not run.
- **Owner decisions during and after trial 1 (2026-11-07):** `"Skip second trials"`; on delivering the one-slot `IQ3_S`
  form instead of four slots: `"We don't need to artificially restrict it to 1 session, C=4 is fine."`; and on stopping
  the DeepSeek trial after `7` of `22` tasks: `"Let's be pragmatic: Yes, it's safe to stop now."` The one-slot `IQ3_S`
  form stays a measured comparison-only draft.
- **Untested Qwen quantizations (owner-directed, not screened):** one-slot `UD-Q4_K_XL` (draft fingerprint
  `811590f6eaa867b9`, `111,334,654,784` bytes; fallback only if `UD-Q5_K_XL` failed fit or fell below ~`127 tok/s` 32K
  decode, which `UD-Q5_K_XL` cleared at `296.7 tok/s`; dropped at `f9f9680`), `UD-Q6_K_XL` and `Q8_0` (dropped at
  `80431b2`) remain untested on tasks here. Upstream stock
  [`docs/QUANTS.md` at `v0.2.11`](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/docs/QUANTS.md)
  reports teacher-forced figures against `Q8_0` on one AMD machine (**not task quality**):

  | Quant | Same top token as `Q8_0` | Mean KL | Perplexity (`Q8_0` `4.052`) |
  |---|---:|---:|---:|
  | `UD-Q6_K_XL` | `94.61%` | `0.033` | `4.020` |
  | `UD-Q5_K_XL` | `94.55%` | `0.038` | `4.024` |
  | `UD-Q4_K_XL` | `93.09%` | `0.056` | `4.068` |
  | `IQ3_S` | `87.69%` | `0.144` | `4.097` |

  Stock [`docs/DETAILS.md` at `v0.2.11`](https://github.com/Niko1221/Strata/blob/c3b3f5035506f3e966f1b4b7b188aeaabae92f1d/docs/DETAILS.md)
  reports n-gram (`PLE` / Engram) table precision against the `BF16` table at mean KL `0.0125` (`Q8_0`) vs `0.0146`
  (`IQ4_NL`), with perplexity within `1%` either way; `UD-Q5_K_XL` and larger already carry the `Q8_0` table, and a
  separate `Q8_0` n-gram table for `UD-Q4_K_XL` is not a stock setup choice.

### Long-session checks on the incumbent and restored host state

Four real stock OMP `18.16.0` multi-turn sessions ran against the four-slot `IQ3_S` DFlash2 incumbent on
`rtxpro6000-win-a` with a client reconnect on every turn:

| Run | Docs | Peak prompt (tokens) | Compaction (tokens) | Recall | Final edit | Wall |
|---|---:|---:|---|---|---|---:|
| `L64` | 9 | 64,341 | none | 2/2 | pass | 21.7 s |
| `L128` | 18 | 125,557 | none | 3/3 | pass | 43.8 s |
| `L200` | 29 | 199,621 | none | 4/4 | pass | 72.2 s |
| `LC` | 33 | 219,899 | 222,486 -> 25,396 | 4/4 | pass (code from the first turn) | 122.6 s |

- **Host window and restored state (`rtxpro6000-win-a`):** all screens, long-session checks and 22-task trials ran in one
  exclusive owner-granted window series on `rtxpro6000-win-a`; the DeepSeek inputs were reused by hard link from an
  earlier DeepSeek install on the host and re-verified by SHA-256 against the pins before setup, the `UD-Q5_K_XL` shards
  were downloaded with a
  bandwidth cap, and the host's OCR tenant containers were left exited as found. Final client checks (2026-11-07, from
  the Mac Studio): with no serving engine and the GPU idle, the launcher on the qualified route failed explicitly
  (`tunnel endpoint health check failed; server stopped or unavailable`, exit `4`). After the qualified four-slot
  `IQ3_S` DFlash2 server started through its supported controller, a typed tool turn and a forced-compaction turn
  through the route (exits `0`/`0`, `2` compactions, only the route's provider and model) showed only loopback flows
  from OMP, and the only non-loopback flow was the SSH forward's own connection to the host (`nettop` 1 s samples,
  process attribution by `ps` ancestry). A launcher smoke answered `ROUTE OK`. Restored state: that server left serving
  (`healthy`) as the current selection, with no other engine running. Afterwards, at the owner's request, the three
  comparison roots and three never-installed seeded roots were deleted from `E:` (`42.8` -> `214.0 GiB` free); the
  large files of the current, rollback and owner-kept roots were verified unchanged.

## Strata v0.2.11 windows (2026-11-06): stock OMP 18.16.0

This section records the 2026-11-06 host measurements for stock Strata `v0.2.11` (annotated tag object
`4a4160162e4a402e082f41aa0a88e6eed629d913`, commit `c3b3f5035506f3e966f1b4b7b188aeaabae92f1d`, published
`2026-11-05T12:49:59Z`; Windows CUDA 13 engine component `0.1.57`, build `0bdcef4682c5+cuda13.0`, archive `627,812,560`
bytes, SHA-256 `0cdf191f0fb39b90edbb902f4d096b90f2ee90a4542deb8aef24985b22407c0f`, manifest SHA-256
`7964873aac7331dd0309c17c49fb3a886616043741558677ec8158c9ba92da7e`; Python lock
`locks/strata-python-cp313-win_amd64-strata0.2.11.txt` bumping Pillow `12.1.1 -> 13.0.0` for `GHSA-78g4-xqwv-q3g8`) with
unchanged stock OMP `18.16.0` (`650f3a108229ee11bf68ba3377f4e8c3391cd424`) across `rtxpro6000-win-a`, `rtx5090-win-a`,
`rtx3090-win-a` and the Mac Studio route (`mac-studio-client`). Four `v0.2.11` server profiles and both `v0.2.11` Mac
Studio routes are qualified (`01b4d9b`, CI matrix `69de6d2`, host-free receipts `fba7d65` at `d2877e3`): on
`rtxpro6000-win-a`,
`win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0` (four batch slots with
per-slot stock DFlash2 drafters under engine `0.1.57`'s `STRATA_BATCH_DF2`) is current (`tests/candidate.py` `CURRENT`),
rolling back to its qualified `v0.2.11` batch-MTP sibling
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`; on `rtx5090-win-a`,
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0` is the 262K default (rolling back to the same
family at `strata0.2.10-omp18.16.0`), while `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` stays the 131K
qualified alternative (rolling back to `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`) after
`win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0` failed G15 twice on 2026-11-06 and remained unqualified; on
`rtx3090-win-a` (RTX 4090 + RTX 3090),
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`
(stock DFlash2 drafter) is current, rolling back to the same family at `strata0.2.10-omp18.16.0`; and on the Mac Studio,
`client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0` is current, rolling back to
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`.

- **Owner decisions and host state (2026-11-06):**
  - After the version A/B runs, the PRO four-slot DFlash2 A/B run and the qualification chains on 2026-11-06, the owner
    approved all three version A/B overrides (`~03:45Z`) and the PRO four-slot DFlash2 override (`~05:10Z`), making
    `v0.2.11` current on the PRO (`df2` current, `batchmtp` rollback), RTX 5090 262K default, pair `df2` and Studio route
    (`df2` current, `batchmtp` rollback), while keeping the RTX 5090 131K alternative on `v0.2.10`
    ([decision](DECISION.md#update-2026-11-06-strata-v0211-with-omp-18160-qualifies-on-the-pro-rtx-5090-262k-pair-and-studio-route-131k-stays-on-v0210)):
    - **PRO (`rtxpro6000-win-a`):** overrode both the `v0.2.11` batch-MTP arm's 3/100 version A/B misses against `v0.2.10`
      (all two concurrent short requests `w2/c2`: `per_req_tps_p50` `0.923 [0.987, 0.979, 0.813]`, `tpot_p50` `1.070`,
      `max_gap_p50` `1.232 [1.020, 1.055, 1.736]`, driven by the A3 baseline block's `8.86 ms` TPOT p50 and `0.253 s`
      longest gap against `10.4–10.6 ms` and `0.43–0.49 s` in every other A and B block; `"Override: chain + route, then
      arms"`) and the four-slot DFlash2 arm's 35/100 A/B misses against `v0.2.11` batch-MTP (`w2` `c=2/c=4`
      short-request throughput/window/latency and 6-token draft-block inter-token / inter-event latency gaps; `"Override:
      qualify DFlash2 as PRO current"`), making the four-slot DFlash2 profile current for its `+20–26%` single-request
      decode gain (`1.201` at depth 0, `1.258` at 8K, `1.203` at 32K, `1.142` at 100K, `1.216` on warm 32K) with the
      qualified `v0.2.11` batch-MTP profile as its rollback, and approved one complete G15 rerun (`~06:40Z`: `"Rerun G15
      once on the PRO"`) after the DFlash2 chain's initial G15 (`g15-20261106T061220Z-57a97f.json`) wrote the
      interrupted 11,178-token essay on the first post-kill recall (`g15-20261106T064239Z-02cfa4.json` passed with both
      recalls returning the nonce at 58 and 28 tokens).
    - **RTX 5090 262K default (`rtx5090-win-a`):** overrode the 11/88 version A/B misses on the 32K-prompt single request
      (`w3/c1`: `agg_tps` `0.917 [0.915, 0.924, 0.911]`, `window_s` `1.091`, `ttft_p50/p95/max` `1.097`,
      `tpot_p50/p95/max` `1.051–1.052`, `latency_p50/p95/max` `1.091`), which come from engine `0.1.57`'s bare
      `--prefill auto` chunking prompts at up to `32,768` tokens on this card (`v0.2.10`'s engine `0.1.56` printed
      `prompt chunk auto: 8192`; A blocks TTFT `4.36–4.39 s` and `25.2–25.6 tok/s`, B blocks `4.77–4.83 s` and
      `23.0–23.4 tok/s`), while `w1` (`1.011`), decode (`0.965–1.008`), prefill (`0.988–1.138`) and 100K TTFT (`0.969`)
      pass (`"Override: accept it, run the chains"`).
    - **RTX 5090 131K alternative (`rtx5090-win-a`):** after `win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`
      failed G15 twice (in the main chain `g15-20261106T042306Z-1bd536.json` where the first post-kill recall rewrote the
      interrupted essay at `8,028` tokens, and in the owner-approved complete G15 rerun
      `g15-20261106T051727Z-74b8db.json` where both post-kill recalls ended in OMP's thinking-loop guard without the
      nonce), kept `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` as the current 131K alternative (rolling back
      to `v0.2.9`) and published the `v0.2.11` 131K ledger as a failed draft (`blockers: ["G15: fail"]`).
    - **Pair (`rtx3090-win-a`, RTX 4090 + RTX 3090):** overrode the 4/88 version A/B misses against `v0.2.10`
      (burstiness only: `w1/c1/max_gap_p50/p95/max` `1.125–1.126`, A `33–43 ms` vs B `41 ms`, and
      `perf/unique_prefix/0/inter_output_event_latency_p95_ms` `1.096`), where `w1` (`1.008`), `w3` (`0.999`), TTFT
      (`0.939–1.016`), TPOT (`0.98–0.99`), decode (`0.966–1.022`) and prefill (`0.988–1.062`) passed (`"Override: run
      the main chain"`).
    - **Disk pruning (with owner approval on 2026-11-06):** seven old IQ3_S roots (`v0.2.3`, `v0.2.7`, three `v0.2.8`,
      two `v0.2.9`) on `rtxpro6000-win-a` (`E:` `115.5 -> 202.5 GiB` free) and three superseded pair roots (`v0.2.8`
      split24, `v0.2.9` split24, `v0.2.9` env86g) on `rtx3090-win-a` (`C:` `94.8 -> 128.7 GiB` free) were pruned while
      keeping the `v0.2.10` and `v0.2.11` roots intact.

### Paired cold-start version A/B (`v0.2.11` vs `v0.2.10`) and PRO four-slot DFlash2 A/B

Each comparison ran six cold-start blocks (`A1 B1 B2 A2 A3 B3`, 3 pairs) using stock Strata's `tools/par_load.py` +
`tools/par_analyze.py` (`w1`: 512-token prompt / 512 output tokens at `c=1`; `w2`: 1,000-token prompts / 128 output
tokens at `c=1, 2, 4`; `w3`: 32,768-token prompts / 128 output tokens at `c=4` on the 4-slot PRO and `c=1` on the
single-slot RTX 5090 and pair) and `scripts/perf_probe.py` (512 output tokens per depth: unique prefix at `0`, `8,192`,
`32,768` and `102,400` tokens, warm repeat at `32,768`, plus the two-request queue probe `perf/queue/0` and
`perf/queue/1` on the single-slot hosts), reporting the `B/A` geometric mean and per-pair `[pair1, pair2, pair3]` ratios
against the owner's 5% rule (`>= 0.95` throughput and decode, `<= 1.05` time and latency; `17` sub-millisecond rows on
the four-slot PRO runs and `13` on the single-slot RTX 5090 and pair runs are below the `1.0 ms` resolution floor and
ungated):

| Comparison (`B` over `A`, result directory) | Verdict & gated checks | `w1` (`512/512`, `c=1`), `w2` (`1K/128`, `c=1, 2, 4`) & `w3` (`32K/128`) `agg_tps` / `per_req_tps_p50` (`B/A [p1, p2, p3]`) | `perf/unique_prefix` (`0`, `8192`, `32768`, `102400`) decode / prefill / TTFT (`B/A`) | `perf/warm_repeat/32768` & `perf/queue` (`0`, `1`) (`B/A`) | Gated misses (`B/A [p1, p2, p3]`) |
|---|---|---|---|---|---|
| **PRO batch-MTP (`v0.2.11` vs `v0.2.10`)**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`<br>`A`: `...-strata0.2.10-omp18.16.0`<br>(`tuple-0211-pro-20261106T024924Z-20261106T0326Z`) | **97 / 100 pass**<br>(3 misses, exit 1; 17 below resolution; owner override) | `w2 c=1`: agg `0.983 [0.997, 0.978, 0.975]`, per-req `0.998`<br>`w2 c=2`: agg `0.993 [0.979, 0.973, 1.027]`, per-req **`0.923 [0.987, 0.979, 0.813]`**<br>`w2 c=4`: agg `0.998 [0.993, 0.989, 1.013]`, per-req `0.982`<br>`w3 c=4`: agg `1.011 [1.003, 1.022, 1.007]`, per-req `1.026` | `0`: decode `0.990`, prefill `1.029`, TTFT `1.005`<br>`8192`: decode `0.975`, prefill `0.999`, TTFT `0.993`<br>`32768`: decode `0.980`, prefill `1.000`, TTFT `1.001`<br>`102400`: decode `1.011 [1.023, 1.008, 1.001]`, prefill `0.997`, TTFT `1.002` | `warm/32768`: decode `0.975`, prefill `1.002`, TTFT `1.032`, wall `1.027` | All 3 misses are `w2/c2` (A3 baseline outlier: TPOT p50 `8.86 ms`, longest gap `0.253 s` vs `10.4–10.6 ms` and `0.43–0.49 s` in every other block):<br>1. `w2/c2/per_req_tps_p50`: **`0.923 [0.987, 0.979, 0.813]`**<br>2. `w2/c2/tpot_p50`: **`1.070 [1.013, 1.022, 1.182]`**<br>3. `w2/c2/max_gap_p50`: **`1.232 [1.020, 1.055, 1.736]`** |
| **PRO four-slot DFlash2 vs `v0.2.11` batch-MTP**<br>`B`: `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`<br>`A`: `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`<br>(`tuple-0211-pro-df2-20261106T034835Z-20261106T0453Z`) | **65 / 100 pass**<br>(35 misses, exit 1; 17 below resolution; owner override for `+20–26%` 1-req decode) | `w2 c=1`: agg `0.989 [1.010, 0.980, 0.979]`, per-req `1.012`<br>`w2 c=2`: agg **`0.885 [0.876, 0.888, 0.891]`**, per-req **`0.794 [0.696, 0.852, 0.846]`**<br>`w2 c=4`: agg **`0.937 [0.938, 0.942, 0.932]`**, per-req **`0.919 [0.948, 0.940, 0.871]`**<br>`w3 c=4`: agg `0.995 [0.973, 0.992, 1.020]`, per-req `0.994` | `0`: decode **`1.201 [1.121, 1.203, 1.283]`**, prefill `1.036`, TTFT `0.942`<br>`8192`: decode **`1.258 [1.232, 1.284, 1.259]`** (`>= 1.03`), prefill `0.961`, TTFT `1.029`<br>`32768`: decode **`1.203 [1.152, 1.292, 1.170]`**, prefill `0.992`, TTFT `1.006`<br>`102400`: decode **`1.142 [1.132, 1.209, 1.088]`** (`>= 1.03`), prefill `0.995`, TTFT `1.004` | `warm/32768`: decode **`1.216 [1.164, 1.313, 1.179]`**, prefill `1.042`, TTFT `0.952`, wall `0.848` | 35 misses across two mechanisms:<br>• **Concurrent short requests (`w2` `c=2, 4`):** `c=2` `agg_tps` **`0.885`**, `per_req_tps_p50` **`0.794`**, `window_s` **`1.130`**, `ttft_max` **`1.052`**, `tpot_p50/p95/max` **`1.242 / 1.203 / 1.217`**, `latency_p50/p95/max` **`1.151 / 1.189 / 1.191`**; `c=4` `agg_tps` **`0.937`**, `per_req_tps_p50` **`0.919`**, `window_s` **`1.067`**, `ttft_p95/max` **`1.063 / 1.059`**, `tpot_p50/p95/max` **`1.089 / 1.140 / 1.277`**, `latency_p50/p95/max` **`1.072 / 1.198 / 1.201`**.<br>• **6-token DFlash2 output bursts:** `w2` `max_gap_p50/p95/max` **`1.124 / 1.128 / 1.129`** (`c=1`), **`1.308 / 1.079 / 1.078`** (`c=2`), **`1.056 / 1.073 / 1.077`** (`c=4`), plus `inter_output_event_latency_p95_ms` **`1.118`** (0), **`1.101`** (8K), **`1.084`** (32K), **`1.122`** (100K) and **`1.072`** (warm 32K). |
| **RTX 5090 262K (`v0.2.11` vs `v0.2.10`)**<br>`B`: `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`<br>`A`: `...-strata0.2.10-omp18.16.0`<br>(`tuple-0211-5090-20261106T024933Z-20261106T0322Z`) | **77 / 88 pass**<br>(11 misses, exit 1; 13 below resolution; owner override on 32K chunk size) | `w1 c=1`: agg `1.011 [1.030, 1.003, 1.000]`, per-req `1.009`, TTFT `0.970`<br>`w3 c=1`: agg **`0.917 [0.915, 0.924, 0.911]`**, per-req `0.952`, TTFT **`1.097 [1.099, 1.092, 1.100]`** | `0`: decode `1.008`, prefill `1.072`, TTFT `0.917`<br>`8192`: decode `1.000`, prefill `0.998`, TTFT `0.985`<br>`32768`: decode `0.965`, prefill `1.012`, TTFT `0.988`<br>`102400`: decode `0.977`, prefill `1.032`, TTFT `0.969` | `warm/32768`: decode `0.992`, prefill `1.059`, TTFT `0.978`<br>`queue/0`: decode `1.005`, prefill `1.138`, TTFT `0.920`<br>`queue/1`: decode `1.004`, prefill `0.988`, TTFT `0.971` | All 11 misses are on the 32K-prompt single request `w3/c1` (`0.1.57` bare `--prefill auto` uses up to `32,768`-token chunks vs `0.1.56`'s `prompt chunk auto: 8192`; A TTFT `4.36–4.39 s` and `25.2–25.6 tok/s`, B `4.77–4.83 s` and `23.0–23.4 tok/s`):<br>• `w3/c1/agg_tps`: **`0.917 [0.915, 0.924, 0.911]`**<br>• `w3/c1/window_s`: **`1.091 [1.092, 1.083, 1.097]`**<br>• `w3/c1/ttft_p50 / p95 / max`: **`1.097 / 1.097 / 1.097`**<br>• `w3/c1/tpot_p50 / p95 / max`: **`1.051 / 1.052 / 1.052`**<br>• `w3/c1/latency_p50 / p95 / max`: **`1.091 / 1.091 / 1.091`** |
| **Pair DFlash2 (`v0.2.11` vs `v0.2.10`)**<br>`B`: `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`<br>`A`: `...-strata0.2.10-omp18.16.0`<br>(`tuple-0211-pair-df2-20261106T031727Z-20261106T0337Z`) | **84 / 88 pass**<br>(4 misses, exit 1; 13 below resolution; owner override on burstiness) | `w1 c=1`: agg `1.008 [1.014, 1.011, 0.998]`, per-req `1.013`, TTFT `1.009`, TPOT `0.987`<br>`w3 c=1`: agg `0.999 [1.003, 0.999, 0.997]`, per-req `1.018`, TTFT `1.003`, TPOT `0.981` | `0`: decode `0.998`, prefill `1.011`, TTFT `0.985`<br>`8192`: decode `1.018`, prefill `0.988`, TTFT `1.016`<br>`32768`: decode `0.966`, prefill `0.999`, TTFT `1.001`<br>`102400`: decode `0.968`, prefill `0.993`, TTFT `1.007` | `warm/32768`: decode `0.981`, prefill `1.062`, TTFT `0.939`<br>`queue/0`: decode `1.022`, prefill `1.052`, TTFT `0.978`<br>`queue/1`: decode `0.999`, prefill `1.004`, TTFT `0.978` | All 4 misses are burstiness only (A `33–43 ms`, B `41 ms`):<br>1. `w1/c1/max_gap_p50`: **`1.125 [1.212, 1.234, 0.952]`**<br>2. `w1/c1/max_gap_p95`: **`1.126 [1.157, 1.128, 1.093]`**<br>3. `w1/c1/max_gap_max`: **`1.126 [1.152, 1.118, 1.109]`**<br>4. `perf/unique_prefix/0/inter_output_event_latency_p95_ms`: **`1.096 [1.053, 1.135, 1.103]`** |

- **PRO `UD-Q4_K_XL` comparison-only screen (`B` = `win11-rtxpro6000-ud-q4kxl-262k-slots4-batchmtp-pledirect-parking-strata0.2.11-omp18.16.0` vs `A` = `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`, `tuple-0211-pro-udq4-20261106T064547Z-20261106T0724Z`):** observed on 2026-11-06 as a report-only six-block cold-start screen (`A1 B1 B2 A2 A3 B3`, three paired cold starts; `4bef966`, `d182658`). The four Unsloth `UD-Q4_K_XL` shards (`111,334,654,784` bytes) were fetched and verified on the PRO's `E:` SSD, and engine `0.1.57` printed `a model with K-quant experts (Unsloth UD-Q4/Q5/Q6_K_XL) reads its prompt on llama.cpp's MMQ kernels` and loaded `strata_kq.dll (STRATA_MMQ_KQ=1)`, confirming the K-quant prompt kernels were active on Windows. `B` was slower than `A` in every measured workload:

  | Metric (`B/A`) | `0` | `8K` | `32K` | `100K` |
  |---|---:|---:|---:|---:|
  | Cold single-request TTFT | `1.243` | `1.267` | `1.195` | `1.168` |
  | Prefill | `0.799` | `0.789` | `0.835` | `0.855` |
  | Decode | `0.899` | `0.915` | `0.883` | `0.848` |

  - **Warm 32K repeat (`B/A`):** TTFT `1.003`, prefill `0.961`, decode `0.894`.
  - **Total output throughput (`agg_tps`, `B/A`):** `w2` `c=1` `0.844`, `c=2` `0.766`, `c=4` `0.731`; `w3` `c=4` `0.815`.
  - **TTFT p50 (`B/A`):** `w2` `c=1` `1.211`, `c=2` `1.235`, `c=4` `2.490`; `w3` `c=4` `1.188`.
  - **TPOT p50 (`B/A`):** `w2` `c=1` `1.159`, `c=2` `1.308`, `c=4` `1.324`; `w3` `c=4` `1.216`.
  - **Rule-4 decode at 32K (`B/A`):** `0.883`.
  - **Disposition:** comparison-only (never a main chain or a current profile, with no CI or campaign row, and any switch would still need Terminal-Bench). `E:` had `86.6 GiB` free after the screen; the root was deleted later on 2026-11-06 at the owner's request.

### Server qualification chains and Studio route G23 (2026-11-06)

All four qualified `v0.2.11` server profiles pass `G10–G21`, `G24` and `G26`, have `G00–G06` operator receipts, and have
`G22`, `G23` and `G25` `not_applicable` (**21 pass, 3 not applicable**, `blockers: []`); both `v0.2.11` Mac Studio
routes have `G23: pass` and `blockers: []`. The RTX 5090 131K `v0.2.11` candidate failed `G15` twice and remains
unqualified (`blockers: ["G15: fail"]`), with `v0.2.10` remaining the current 131K alternative:

| Host or route | Profile id & role | Tooling commits & receipts | Readiness (`G16` / `G20` / `G21` / `G26`) & cache | `G12` / `G17` / `G19` reuse & `G18L` compaction | `G10` / `G21` memory & `G13` ETW egress | `G24` `synthetic-1` (scored / pilot, wall) |
|---|---|---|---|---|---|---|
| `rtxpro6000-win-a`<br>(RTX PRO 6000) | `win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`<br>(**current**, four-slot DFlash2) | G00–G06 `d2877e3` ([`g00-baseline-20261106`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g00-baseline-20261106.json)); chain G10–G25 `b812df9` ([`g10-33c23d`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g10-20261106T060801Z-33c23d.json), initial G15 fail [`g15-57a97f`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g15-20261106T061220Z-57a97f.json)); G15 rerun `b812df9` ([`g15-02cfa4`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g15-20261106T064239Z-02cfa4.json)); G26 `b812df9` ([`g26-063440Z`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g26-second-root-20261106T063440Z.json)) | `G16` restart `31.0 s`; `G20` restart `31.0 s` (wall `38.3 s`); `G21` current ready `35.7 s`; `G26` second-root install `25.80 s`, start `56.28 s`, stop `4.94 s`; 8,192 MiB automatic cache; `drafting: DFlash2 alone`, `STRATA_BATCH_DF2: 4 slot drafters on CUDA0 (85 MiB of private K/V ring and buffers each, sharing the solo drafter's pack); 70.22 GiB free there` and `STRATA_BATCH_DF2: 4 slot drafters ready (batch windows carry each slot's token and its spare-row drafts)`; bare `--prefill auto` (`32,768`-token ceiling) | `G12` 12 continuations with reuse (`32,897 / 41,004`, `40,412 / 40,975`, `40,414 / 40,977`); `G17` 100K cold prefill `10.847 s` (`9,222 tok/s`), near-limit `212,150` tokens in `23.302 s`; `G19` shared prefix reuse `7,546` tokens (`48` uncached, `32` parks); `G18L` production compaction `1` (`223,445 -> 27,745` tokens), reduced `5`, wall `133.2 s` | `G10` avail RAM `127.14 GiB` (min `127.10`), commit headroom `83.55 GiB` of `219.70 GiB`, GPU `73,496 MiB` of `97,887 MiB`; `G21` peak VRAM `73,756 MiB`, min avail RAM serving `118.67 GiB`, engine WS peak `52.19 GiB`, private commit `124.23 GiB`; `G13` `0 / 4,916` non-loopback ETW events (`2` compactions) | Scored **15/18** (`0.833`), pilot **5/6** (`0.833`), wall **627.3 s** (`627 s`), 0 protocol counters (`tool-loop` 0/3, 5/6 tasks 3/3) |
| `rtxpro6000-win-a`<br>(RTX PRO 6000) | `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0`<br>(**rollback**, four-slot batch-MTP) | G00–G06 `d2877e3` ([`g00-baseline-20261106`](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g00-baseline-20261106.json)); G10–G25 `9c6318b` ([`g10-cc0f91`](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g10-20261106T034943Z-cc0f91.json)); G26 `9c6318b` ([`g26-041411Z`](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g26-second-root-20261106T041411Z.json)) | `G16` restart `31.1 s`; `G20` restart `30.9 s` (wall `36.8 s`); `G21` current ready `31.4 s`; `G26` second-root install `21.60 s`, start `52.86 s`, stop `4.80 s`; 8,192 MiB automatic cache; `--batch-mtp: 4 slot drafters on CUDA0 (862 MiB/drafter, 3448 MiB total)` | `G12` 12 continuations with reuse (`32,815 / 40,977`, `40,476 / 41,040`, `40,478 / 41,045`); `G17` 100K cold prefill `10.742 s` (`9,312 tok/s`), near-limit `212,114` tokens in `23.115 s`; `G19` shared prefix reuse `7,546` tokens (`48` uncached, `35` parks); `G18L` production compaction `1` (`222,393 -> 21,358` tokens), reduced `6`, wall `129.9 s` | `G10` avail RAM `127.23 GiB` (min `127.22`), commit headroom `81.73 GiB` of `219.70 GiB`, GPU `74,918 MiB` of `97,887 MiB`; `G21` peak VRAM `75,132 MiB`, min avail RAM serving `118.42 GiB`, engine WS peak `52.17 GiB`, private commit `125.56 GiB`; `G13` `0 / 9,365` non-loopback ETW events (`2` compactions) | Scored **16/18** (`0.889`), pilot **5/6** (`0.833`), wall **549.4 s**, 0 protocol counters (`tool-loop` 1/3 only misses, 5/6 tasks 3/3) |
| `rtx5090-win-a`<br>(RTX 5090 262K **default**) | `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0`<br>(**current**) | G00–G06 `d2877e3` ([`g00-baseline-20261106`](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/receipts/g00-baseline-20261106.json)); G10–G25 `9c6318b` ([`g10-172ed7`](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/receipts/g10-20261106T035022Z-172ed7.json)); G26 `9c6318b` ([`g26-041741Z`](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/receipts/g26-second-root-20261106T041741Z.json)) | `G16` restart `18.5 s`; `G20` restart `19.0 s` (wall `22.1 s`); `G21` current ready `19.3 s`; `G26` second-root install `11.88 s`, start `22.33 s`, stop `3.23 s`; 4,352 MiB automatic cache; bare `--prefill auto` (`32,768`-token chunks) | `G12` 12 continuations with reuse (`33,540 / 41,716`, `40,922 / 41,514`, `42,159 / 43,592`); `G17` 100K cold prefill `11.769 s` (`8,499 tok/s`), near-limit `212,396` tokens in `25.457 s`; `G19` shared prefix reuse `7,548` tokens (`98` uncached, `17` parks); `G18L` production compaction `1` (`223,896 -> 20,970` tokens), reduced `4`, wall `134.4 s` | `G10` avail RAM `13.47 GiB` (min `13.41`), commit headroom `20.30 GiB` of `85.15 GiB`, GPU `30,776 MiB` of `32,607 MiB`; `G21` peak VRAM `30,942 MiB`, min avail RAM serving `8.57 GiB`, engine WS peak `28.63 GiB`, private commit `60.10 GiB`; `G13` `0 / 6,493` non-loopback ETW events (`1` compaction) | Scored **17/18** (`0.944`), pilot **6/6** (`1.000`), wall **843.1 s**, 0 protocol counters (`tool-loop` 2/3 only miss, 5/6 tasks 3/3) |
| `rtx5090-win-a`<br>(RTX 5090 131K candidate) | `win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0`<br>(**unqualified draft**; `v0.2.10` stays current) | G00–G06 `d2877e3`; chain G10–G25 `9c6318b` ([`g15-1bd536`](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/receipts/g15-20261106T042306Z-1bd536.json)); standalone G15 rerun `9c6318b` ([`g15-74b8db`](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/receipts/g15-20261106T051727Z-74b8db.json)); G26 `9c6318b` ([`g26-044546Z`](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/receipts/g26-second-root-20261106T044546Z.json)) | `G16` restart `16.6 s`; `G20` restart `16.5 s` (wall `19.6 s`); `G21` current ready `16.8 s`; `G26` install `12.36 s`, start `35.93 s`, stop `2.26 s`; 3,840 MiB automatic cache (`11` parks in `G19`); **G15 failed twice** (below) | `G12` 14 continuations with reuse (`33,181 / 41,313`, `57,427 / 58,088`, `41,583 / 42,210`); `G17` 100K cold prefill `12.929 s` (`7,737 tok/s`), near-limit `105,825` tokens in `13.077 s`; `G19` shared prefix reuse `7,548` tokens (`46` uncached); `G18L` production compaction `1` (`113,486 -> 21,394` tokens), reduced `1`, wall `75.4 s` | `G10` avail RAM `12.00 GiB` (min `11.99`), commit headroom `19.31 GiB` of `85.15 GiB`, GPU `30,944 MiB` of `32,607 MiB`; `G21` peak VRAM `31,056 MiB`, min avail RAM serving `7.23 GiB`, engine WS peak `29.93 GiB`, private commit `60.53 GiB`; `G13` `0 / 6,419` non-loopback ETW events (`1` compaction) | Scored **15/18** (`0.833`), pilot **6/6** (`1.000`), wall **758.3 s**, 0 protocol counters (`tool-loop` 0/3, 5/6 tasks 3/3) |
| `rtx3090-win-a`<br>(RTX 4090 + RTX 3090 pair) | `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0`<br>(**current**, stock DFlash2) | G00–G06 `d2877e3`; chain G10–G25 `772a418` (initial G13 fail [`g13-94c443`](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/receipts/g13-20261106T035408Z-94c443.json)); G13 rerun `611c342` ([`g13-8c6c25`](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/receipts/g13-20261106T043454Z-8c6c25.json)); G26 `772a418` ([`g26-043006Z`](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/receipts/g26-second-root-20261106T043006Z.json)) | `G16` restart `40.5 s`; `G20` restart `40.5 s` (wall `51.6 s`); `G21` current ready `40.8 s`; `G26` second-root install `37.00 s`, start `52.58 s`, stop `6.19 s`; 8,192 MiB automatic cache; `19.41 / 17.90 GiB` expert caches on the RTX 3090 (layers 0–23) / RTX 4090 (layers 24–47, stage order `[1, 0]`); `drafting: DFlash2 alone` | `G12` 12 continuations with reuse (`32,935 / 41,043`, `40,434 / 40,997`, `40,378 / 40,939`); `G17` 100K cold prefill `25.946 s` (`3,855 tok/s`), near-limit `212,428` tokens in `53.997 s`; `G19` shared prefix reuse `7,546` tokens (`47` uncached, `12` parks); `G18L` production compaction `1` (`223,864 -> 20,641` tokens), reduced `1`, wall `280.5 s` | `G10` avail RAM `66.35 GiB` (min `66.32`), commit headroom `28.70 GiB` of `135.69 GiB`, GPUs `23,000 / 22,892 MiB`; `G21` peak VRAM `23,174 / 23,066 MiB` (sum `46,240 MiB`), min avail RAM serving `57.63 GiB`, engine WS peak `55.94 GiB`, private commit `101.83 GiB`; `G13` `0 / 6,862` non-loopback ETW events on initial attempt and `0 / 3,436` (`2` compactions) on `611c342` rerun | Scored **15/18** (`0.833`), pilot **5/6** (`0.833`), wall **896.4 s**, 0 protocol counters (`tool-loop` 0/3, 5/6 tasks 3/3) |
| `mac-studio-client` -> `rtxpro6000-win-a` | `client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`<br>(**current** Studio route) | `G23` `b812df9` ([`89cd7d39`](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/receipts/89cd7d3991b843d195f2d1b4624e00ac.json)) | Missing key refused before launch; wrong key 401; health RTT `6.0–10.1 ms`; stream TTFT `0.270 s`; tunnel drop failed in-flight turn with prior transcript preserved; nonce recall from transcript replay after tunnel reopen `1.83 s`, client restart `1.11 s`, verified server restart `2.34 s` (changed server instance); one-turn `launch-omp` smoke answered `ROUTE OK` with owned stop | — | — | — |
| `mac-studio-client` -> `rtxpro6000-win-a` | `client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0`<br>(**rollback** Studio route) | `G23` `9c6318b` ([`4fc016a3`](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/receipts/4fc016a3ebff4f41b89bd69189b938e0.json)) | Missing key refused before launch; wrong key 401; health RTT `5.3–6.5 ms`; stream TTFT `0.174 s`; tunnel drop failed in-flight turn with prior transcript preserved; nonce recall after tunnel reopen `2.24 s`, client restart `1.10 s`, verified server restart `2.30 s` (changed server instance); one-turn `launch-omp` smoke answered `ROUTE OK` with owned stop | — | — | — |

### Kept failures and reruns in the 2026-11-06 windows

Every failed gate receipt remains in its release directory beside any later rerun:

1. **Pair DFlash2 `G13` forced-compaction turn (`rtx3090-win-a`, fixed in `611c342` and passed on complete-gate rerun):**
   - **Initial failure (kept):** in the main qualification chain at `772a418`
     ([`g13-20261106T035408Z-94c443.json`](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/receipts/g13-20261106T035408Z-94c443.json)),
     every authentication, settings, route-census and ETW egress check (`0 / 6,862` non-loopback events) passed, but OMP
     declined the forced compaction six times (`"would not reduce context"`), so no compaction was observed
     (`compactions_observed: 0`). The gate's one-line tool note left only about 200 tokens of history, so whether
     compaction could reduce context depended on the model's own output (the PRO's identical-size turn compacted).
   - **Fix and complete-gate rerun (`611c342`):** `611c342` grows the tool note to 160 lines (about 3K tokens of history,
     above OMP's 1,000-token `keepRecent`). The complete G13 rerun (`start`, `g13`, `stop`) on the same root
     ([`g13-20261106T043454Z-8c6c25.json`](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/receipts/g13-20261106T043454Z-8c6c25.json))
     passed every check with two compactions (`compactions_observed: 2`) and `0` non-loopback network events among
     `3,436` attributed ETW events.
2. **RTX 5090 131K `G15` mid-generation kill turn (`rtx5090-win-a`, failed twice; profile kept unqualified):**
   - **First chain failure (kept):** in the main qualification chain at `9c6318b`
     ([`g15-20261106T042306Z-1bd536.json`](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/receipts/g15-20261106T042306Z-1bd536.json)),
     after the mid-generation engine kill (`cut_turn_not_completed: true`), the first recall rewrote the interrupted
     essay (`8,028` output tokens, `recall_has_nonce: false`) although the prompt said `"Do not write the essay"`; the
     diagnostic second recall returned the nonce (`second_recall_has_nonce: true`).
   - **Owner-approved complete G15 rerun (kept):** in the standalone complete-gate rerun (`start`, `g15`, `stop`) at
     `9c6318b`
     ([`g15-20261106T051727Z-74b8db.json`](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/receipts/g15-20261106T051727Z-74b8db.json)),
     after the mid-generation kill both recalls ended in OMP's thinking-loop guard without the nonce
     (`recall_has_nonce: false`, `second_recall_has_nonce: false`, `recall_stop: "Thinking loop detected: ..."`). The
     idle-kill recall and the client-abort control recalled the nonce both times. The 262K default on the same model
     passed G15. The 131K lane keeps its `v0.2.10` profile (`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`) and
     leaves the `v0.2.11` 131K ledger as a failed draft (`blockers: ["G15: fail"]`).
3. **PRO four-slot DFlash2 `G15` mid-generation kill turn (`rtxpro6000-win-a`, passed on owner-approved complete-gate rerun):**
   - **Initial chain failure (kept):** in the requalification chain (`06:05–06:34Z` at `b812df9`, published in `f3a8a77`,
     [`g15-20261106T061220Z-57a97f.json`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g15-20261106T061220Z-57a97f.json)),
     after the mid-generation engine kill (`cut_turn_not_completed: true`), the first recall wrote the interrupted
     essay (`11,178` output tokens, `recall_has_nonce: false`), while the diagnostic second recall returned the nonce
     (`126` output tokens, `second_recall_has_nonce: true`) and both the idle-kill recall (`47.071 s` wall) and the
     client-abort control recalled the nonce.
   - **Owner-approved complete G15 rerun (`06:41–06:44Z`, passed):** after the owner approved `"Rerun G15 once on the
     PRO"` (`~06:40Z`), the complete-gate rerun (`start, g15, stop` at `b812df9`, published in `637b616`,
     [`g15-20261106T064239Z-02cfa4.json`](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/receipts/g15-20261106T064239Z-02cfa4.json))
     passed: the cut turn ended as an error, and both post-kill recalls returned the nonce (`58` and `28` output tokens,
     `29.301 s` mid-generation kill recall wall and `29.209 s` idle-kill recall wall). Across `v0.2.11`, this first
     recall after the mid-generation kill failed in 3 of 6 G15 runs (RTX 5090 131K twice and PRO DFlash2 once) and
     passed in the other three (PRO batch-MTP, RTX 5090 262K, pair DFlash2) and in every published `v0.2.9`/`v0.2.10`
     G15; the cut-turn stop text is identical across versions, and the 2026-10-01 mitigation `cb31418` added `"Do not
     write the essay."` to the recall prompt.

### Source admissions and restored state (2026-11-06)

- **Source, start-path and stage-order admissions (`d58497a` .. `772a418`):**
  - `d58497a` .. `f991305` reviewed the `v0.2.11` setup planning sources, `46cf840` pinned `locks/strata-python-cp313-win_amd64-strata0.2.11.txt` (Pillow `13.0.0`), `8229f25` reviewed the `v0.2.11` server start path and `638a29b` keyed `start_path_sources` by engine version (`9` runtime files on `0.1.57`); `a8616d7` isolated `.activity.lock` and `procs/<pid>.json` under `<root>/state/strata-runtime` (`STRATA_RUNTIME_DIR`) and `<root>/localappdata` (`LOCALAPPDATA`); `340a309` added `0.1.57` to `ENGINE_ENV_REVIEWED_ENGINES`; `99f1aa7` refused engine `0.1.57`'s `short of GPU memory:` walk diagnostics and no-drafter retry and records stock's bare-auto ceiling lines (`strata generate: NVIDIA: --prefill auto may take chunks up to 32768 (STRATA_NV_CHUNK=0 keeps 8192, =16 keeps 16384)`) as `prefill_ceiling` ([UPSTREAM.md](UPSTREAM.md#strata-v0211-setup-and-start-path-review-engine-0157)).
  - `c557ea0` and `cc859c4` admitted named `strata.drafting: "dflash2"` with `setup_args.parallel` batch slots on single-card engine `0.1.57+` and required one `STRATA_BATCH_DF2` slot drafter per batch slot (`STRATA_BATCH_DF2: 4 slot drafters on CUDA0 (85 MiB of private K/V ring and buffers each, sharing the solo drafter's pack); 70.22 GiB free there` and `STRATA_BATCH_DF2: 4 slot drafters ready (batch windows carry each slot's token and its spare-row drafts)` on the PRO); `4bef966` and `d182658` reviewed the `v0.2.11` all-resident Unsloth lane and drafted the comparison-only PRO `UD-Q4_K_XL` screen; `772a418` admitted engine `0.1.57` into `lifecycle.STAGE_ORDER_REVIEWED_ENGINES` after the pair DFlash2 measurement start confirmed configured `[1, 0]` stage order (layers 0–23 on the RTX 3090, 24–47 on the RTX 4090) with `19.41 / 17.90 GiB` expert caches and one engine generation.
- **Restored state after the 2026-11-06 windows:**
  - `rtxpro6000-win-a` ([DFlash2 server restored-state](../releases/win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/restored-state.json), [DFlash2 route restored-state](../releases/client-rtxpro6000-262k-df2-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/restored-state.json), [batch-MTP server restored-state](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0/restored-state.json), [batch-MTP route restored-state](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0/restored-state.json)): seven host-lock windows (plus the `05:01–05:02Z` pruning hold) covered the version A/B (`02:49–03:26Z`), the batch-MTP chain and Studio route G23 (`03:47–04:17Z`), the DFlash2 arm install and A/B (`04:17–04:53Z`), a first `UD-Q4_K_XL` window (`05:02–06:05Z`) that only downloaded and was stopped before install when the download fell from about `35 MB/s` to `2.8 MB/s` (the remaining shards were then fetched by a separate fetch-only process at `06:08–06:35Z`, network and disk only, beside the DFlash2 chain window), the DFlash2 chain and Studio route G23 (`06:05–06:37Z`), the DFlash2 complete G15 rerun (`06:40–06:44Z`, `96af37e`), and the `UD-Q4_K_XL` install and screen (`06:45–07:24Z`, leaving the comparison-only `UD-Q4_K_XL` root installed on `E:` with `86.6 GiB` free after the screen); each window (including both `UD-Q4_K_XL` windows) began and ended idle with the two OCR tenant containers exited as found (`console_session: "none"`, `gpu_used_mib: 433`, `available_ram_gib: 178.5 -> 178.4 -> 179.1`, no `omp-strata` process remaining), and seven old IQ3_S roots (`v0.2.3`, `v0.2.7`, three `v0.2.8`, two `v0.2.9`) were pruned with the owner's approval under their own host lock at `05:01–05:02Z` (`E:` `115.5 -> 202.5 GiB` free).
  - `rtx5090-win-a` ([262K restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.11-omp18.16.0/restored-state.json), [131K restored-state](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.11-omp18.16.0/restored-state.json)): three WSL-down fleet windows ran with Docker Desktop and WSL stopped (`02:49–03:29Z` for installs and the 262K A/B, where fleet return failed closed with `"docker.exe exited 128"`, the owner's pinned relaunch script recreated the production NInfer container, retired controller state was kept, and fleet commission started generation 1 with HTTP 200 health; `03:47–04:56Z` for both chains, ending with a successful fleet return at generation 3; and `05:14–05:25Z` for the 131K complete G15 rerun, ending with a successful fleet return at generation 5); after each window the host supervisor restarted Docker Desktop and reprovisioned the lane distro's WSL integration before the return, and both `v0.2.11` roots stopped (`GPU 0 MiB`, no `omp-strata` process remaining).
  - `rtx3090-win-a` ([pair restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.11-omp18.16.0/restored-state.json)): four exclusive host-lock windows covered the stage-order measurement start (`02:45–03:07Z`), the version A/B (`03:17–03:37Z`), the DFlash2 requalify chain (`03:47–04:30Z`) and the complete G13 rerun (`04:32–04:37Z`); three superseded pair roots (`v0.2.8` split24, `v0.2.9` split24, `v0.2.9` env86g) were pruned with the owner's approval (`C:` `94.8 -> 128.7 GiB` free, keeping both `v0.2.10` roots intact and stopped), and start/end censuses found `console_session: "none"`, `user_sessions: 0`, `[186, 0] MiB` GPU memory on the display-attached RTX 4090 and headless RTX 3090, `120.7 -> 120.9 GiB` available RAM, and no `omp-strata` process remaining.
### Earlier windows: Strata v0.2.10 (2026-11-03)

The 2026-11-03 `v0.2.10` section below remains the rollback qualification record for the RTX 5090 131K alternative
(`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`) and earlier qualified history for the RTX 5090 262K default,
the pair `df2` profile, the PRO `kvvram-envpg`, pair `pw2` `env86g` and Studio `v0.2.10` route; its headings and tables
keep the roles those profiles held when the section was written.


## Strata v0.2.10 windows (2026-11-03): stock OMP 18.16.0

This section records the 2026-11-03 host measurements for stock Strata `v0.2.10` (annotated tag object
`db0500a53119a349fa44497099d6e28a83ded34a`, commit `ffa80d73133ea5c548aefe57889a16e8085a938f`, published
`2026-11-02T23:52:47Z`; Windows CUDA 13 engine component `0.1.56`, build `06698c674673+cuda13.0`, archive `627,806,827`
bytes, SHA-256 `5336671c55bc1b819d076104608522147227001d1711378f35ea5d524bc866ec`) with stock OMP `18.16.0`
(`650f3a108229ee11bf68ba3377f4e8c3391cd424`; for `omp-strata` a pin and documentation delta only, with a request path
byte-identical to `18.15.0`) across `rtxpro6000-win-a`, `rtx5090-win-a`, `rtx3090-win-a` and the Mac Studio route
(`mac-studio-client`). All five `v0.2.10` server profiles and the Mac Studio route are qualified (`8a2c9ec`, hosted CI
run `41723093180` on pull request 75): on `rtxpro6000-win-a`,
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0` is current
(`tests/candidate.py` `CURRENT`, rolling back to the same family at `strata0.2.9-omp18.15.0`); on `rtx5090-win-a`,
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` is the 262K default (rolling back to the
same family at `strata0.2.9-omp18.15.0`) and `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` is the 131K
qualified alternative (rolling back to `win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`); on `rtx3090-win-a` (RTX
4090 + RTX 3090),
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
(stock DFlash2 drafter, requalified at tooling `837bc89`) is current, rolling back to
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
(MTP with `--pipeline-windows 2` on the same `v0.2.10` + OMP `18.16.0` settings, requalified at `7b338d9` / `837bc89`);
and on `mac-studio-client`, `client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0` is current
(rolling back to the same family at `strata0.2.9-omp18.15.0`).

### Owner decisions and host state

The owner's Asks on 2026-11-03 set the scope, measurement rules and overrides:

- **Initial scope (~16:40Z):** qualify every lane and the Mac Studio route (`"All lanes + route"`), add a pair DFlash2
  arm (`"Add a pair DFlash2 arm"`) with a `+3%` decode bar against `v0.2.10` `env86g`, make a lane current when every
  gate passes and no paired metric regresses more than 5%, and run the host windows (`"Run when ready, OCR as found"` on
  `rtxpro6000-win-a`, `"Queue behind omp-ninfer when ready"` on `rtx3090-win-a`, and `"When ready, full WSL-down"` on
  `rtx5090-win-a`).
- **PRO override, resolution floor and upstream disposition (~19:50Z):** `"Override: chain + G23"` on
  `rtxpro6000-win-a` (accepting and recording the concurrent short-prompt TTFT A/B regression so the PRO
  requalification chain and Mac Studio route G23 run), `"Accept the rule"` on the measurement resolution floor
  (first-SSE-frame timing and latencies under 1 ms are reported, not gated, with each lane's strict first verdict kept
  beside the final one), `"Not now"` on filing an upstream issue, and `"Prune after the swap"` for `rtx5090-win-a`
  integration roots that are neither current nor rollback.
- **Pair DFlash2 decision (~21:28Z):** `"Run chain, make DFlash2 current"` on `rtx3090-win-a` after the DFlash2 arm met
  the `+3%` decode bar against `v0.2.10` `env86g` (`+8.2%` at 8K, `+9.3%` at 100K, `+7.7%` to `+13.6%` at 0 / 32K / warm
  32K), accepting its 5%-rule misses on token-burst spacing, queued-request prefill and empty-prompt TTFT and keeping
  `v0.2.10` `env86g` as its qualified rollback.

On `rtxpro6000-win-a`
([PRO restored-state](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/restored-state.json),
[route restored-state](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/restored-state.json)),
three windows held the exclusive host lock (`17:53–18:29Z` for install and cold-start A/B; `20:05–20:48Z` for the
requalification chain and the Mac Studio route G23 + `launch-omp` smoke; `21:30–21:33Z` for the complete G14 rerun),
with no user signed in before or after, GPU memory at `433 MiB` idle, `180.2 GiB` RAM available before and `179.5 GiB`
after, and both OCR tenant containers already exited and left as found. On `rtx5090-win-a`
([262K restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/restored-state.json),
[131K restored-state](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/restored-state.json)), one
WSL-down fleet window reserved the host through the owner's fleet controller at `17:54Z` (`fleet use`, after verifying an
unreserved `Fleet` phase at generation `27` with no owned markers), disabled the container-host supervisor and encoder
tasks, stopped Docker Desktop and WSL (`39.7 GiB` RAM available during the 262K A/B), and ran the 262K install
(`17:57–18:04Z`), cold-start A/B (`18:05–18:17Z`) and requalification chain (`18:26–18:53Z`) followed by the 131K install
(`18:55–19:03Z`) and requalification chain (`19:05–19:30Z`) in the same window; production NInfer was down about
`17:54–19:36Z` (UTC), `fleet return` failed closed after WSL restarted (`started service identity changed during
readiness`), the owner's pinned relaunch script recreated the container (healthy after ~12 s at `19:36Z`), the retired
controller state was kept, and the container was commissioned at a new controller generation (`1`) at `19:38Z` with
authenticated health HTTP `200`. On `rtx3090-win-a`
([pair `df2` restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/restored-state.json),
[pair `env86g` restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/restored-state.json)),
six windows queued behind another tenant's exclusive GPU work under the exclusive host lock across the stage-order
measurement (`17:55–18:19Z`: engine `0.1.56` automatic stage order `[1, 0]`, layers `0–23` on the RTX 3090 and `24–47` on
the RTX 4090 with the pinned manual split `24`), the `env86g` cold-start version A/B (`18:26–18:46Z`), the `env86g`
requalification chain (`18:53–19:41Z`), the DFlash2 install and cold-start A/B (`19:47–20:27Z`), the complete `env86g`
G20 rerun (`20:41–20:45Z`) and the DFlash2 requalification chain (`21:44–22:29Z`), with no user signed in and idle GPUs
at `180–182 MiB` on the display-attached RTX 4090 and `0 MiB` on the RTX 3090 (`120.0–120.2 GiB` available RAM).

### Version A/B per host

Each host ran three paired cold-start blocks (`A B B A A B`, where `A` is the qualified `v0.2.9` profile root and `B` is
the `v0.2.10` root) using stock Strata's `tools/par_load.py` + `tools/par_analyze.py` (`w1`: 512-token prompt / 512
output tokens at `c=1`; `w2`: 1,000-token prompts / 128 output tokens at `c=1, 2, 4`; `w3`: 32,768-token prompts / 128
output tokens at `c=4` on the 4-slot PRO and `c=1` on the single-slot RTX 5090 and pair), `scripts/perf_probe.py` (512
output tokens per depth: unique prefix at `0`, `8,192`, `32,768` and `102,400` tokens, warm repeat at `32,768`, plus the
two-request queue probe `perf/queue/0` and `perf/queue/1` on the single-slot hosts) and `tools/serve_load.py
--save/--compare` (`temperature: 0`, 256 output tokens, compared against block `A1`). Ratios below are `B` over `A`
medians with per-pair ratios in `pairs`; `pass` is the owner's 5% rule (throughput and decode `>= 0.95`, latency
`<= 1.05`). Under the measurement rule accepted by the owner on 2026-11-03, latencies under 1 ms (`lag_p50/p95/max` and
`inter_output_event_latency_p50_ms`) and first-SSE-frame timings (`first_event_ms`, quantized to Windows' 15.6 ms tick)
are below the resolution floor and are reported, not gated (`17` metrics on the PRO, `13` on the RTX 5090 262K and `13`
on the pair); each lane's strict first verdict (`pass=False` on all three before the resolution floor) is kept beside
its final verdict:

| `rtxpro6000-win-a` 262K (`A` = `v0.2.9` `kvvram-envpg`, `B` = `v0.2.10`; final `pass=False`, strict first `pass=False`, `17` below resolution) | `B/A` | `pairs` | 5% rule (`pass`) |
|---|---:|---|---|
| `w2/c1/agg_tps` | 0.969 | `0.967, 0.975, 0.966` | `>= 0.95` (**pass**) |
| `w2/c2/agg_tps` | 1.006 | `1.004, 1.025, 0.988` | `>= 0.95` (**pass**) |
| `w2/c4/agg_tps` | 1.008 | `0.994, 1.008, 1.021` | `>= 0.95` (**pass**) |
| `w3/c4/agg_tps` | 1.032 | `1.024, 1.010, 1.065` | `>= 0.95` (**pass**) |
| `w2/c1/ttft_p50` / `w2/c1/ttft_p95` | 1.004 / 1.001 | `1.013, 0.985, 1.014` / `0.990, 0.990, 1.025` | `<= 1.05` (**pass**) |
| `w2/c2/ttft_p50` | 1.052 | `1.027, 0.998, 1.136` | `<= 1.05` (**miss**) |
| `w2/c2/ttft_p95` | 1.136 | `1.127, 1.137, 1.144` | `<= 1.05` (**miss**) |
| `w2/c4/ttft_p50` | 1.326 | `1.559, 1.524, 0.981` | `<= 1.05` (**miss**) |
| `w2/c4/ttft_p95` | 0.988 | `0.999, 0.983, 0.982` | `<= 1.05` (**pass**) |
| `w3/c4/ttft_p50` / `w3/c4/ttft_p95` | 0.976 / 0.968 | `1.005, 1.025, 0.903` / `0.978, 0.993, 0.932` | `<= 1.05` (**pass**) |
| `perf/unique_prefix` cold decode (`0` / `8K` / `32K` / `100K`, `decode_tokens_s`) | 1.058 / 1.054 / 1.062 / 1.039 | `0`: `1.014, 1.082, 1.079`; `8K`: `1.047, 1.116, 1.001`; `32K`: `1.087, 1.061, 1.037`; `100K`: `1.051, 1.030, 1.037` | `>= 0.95` (**pass**) |
| `perf/warm_repeat/32768/decode_tokens_s` | 1.058 | `1.086, 1.057, 1.031` | `>= 0.95` (**pass**) |
| `perf/unique_prefix` cold TTFT (`8K` / `32K` / `100K`, `ttft_ms`) | 0.991 / 0.998 / 0.998 | `8K`: `0.984, 0.996, 0.992`; `32K`: `1.005, 0.991, 0.997`; `100K`: `1.001, 0.996, 0.997` | `<= 1.05` (**pass**) |

| `rtx5090-win-a` 262K (`A` = `v0.2.9` `kvvram-kvgrow-envg`, `B` = `v0.2.10`, Docker/WSL stopped; final `pass=True`, strict first `pass=False`, `13` below resolution) | `B/A` | `pairs` | 5% rule (`pass`) |
|---|---:|---|---|
| `w1/c1/agg_tps` | 1.033 | `1.051, 1.025, 1.022` | `>= 0.95` (**pass**) |
| `w3/c1/agg_tps` | 1.013 | `1.020, 1.014, 1.005` | `>= 0.95` (**pass**) |
| `w1/c1/ttft_p50` / `w1/c1/ttft_p95` | 0.967 / 0.987 | `0.985, 0.972, 0.945` / `1.002, 0.975, 0.985` | `<= 1.05` (**pass**) |
| `w3/c1/ttft_p50` / `w3/c1/ttft_p95` | 0.991 / 0.991 | `0.985, 0.993, 0.995` / `0.983, 0.994, 0.996` | `<= 1.05` (**pass**) |
| `perf/unique_prefix` cold decode (`0` / `8K` / `32K` / `100K`, `decode_tokens_s`) | 1.012 / 1.033 / 1.018 / 1.024 | `0`: `1.005, 0.995, 1.037`; `8K`: `1.035, 1.042, 1.023`; `32K`: `1.000, 1.024, 1.029`; `100K`: `1.030, 1.023, 1.020` | `>= 0.95` (**pass**) |
| `perf/warm_repeat/32768/decode_tokens_s` | 1.036 | `1.012, 1.083, 1.016` | `>= 0.95` (**pass**) |
| `perf/unique_prefix` cold TTFT (`8K` / `32K` / `100K`, `ttft_ms`) | 0.994 / 0.995 / 0.995 | `8K`: `0.989, 0.997, 0.997`; `32K`: `0.994, 0.999, 0.991`; `100K`: `0.997, 0.994, 0.995` | `<= 1.05` (**pass**) |

| `rtx3090-win-a` pair `env86g` (`A` = `v0.2.9`, `B` = `v0.2.10`; final `pass=True`, strict first `pass=False`, `13` below resolution) | `B/A` | `pairs` | 5% rule (`pass`) |
|---|---:|---|---|
| `w1/c1/agg_tps` | 1.020 | `1.017, 1.015, 1.028` | `>= 0.95` (**pass**) |
| `w3/c1/agg_tps` | 1.009 | `1.013, 1.010, 1.004` | `>= 0.95` (**pass**) |
| `w1/c1/ttft_p50` / `w1/c1/ttft_p95` | 0.985 / 0.979 | `0.948, 1.004, 1.003` / `0.931, 1.000, 1.008` | `<= 1.05` (**pass**) |
| `w3/c1/ttft_p50` / `w3/c1/ttft_p95` | 0.993 / 0.995 | `0.988, 0.995, 0.996` / `0.993, 0.995, 0.995` | `<= 1.05` (**pass**) |
| `perf/unique_prefix` cold decode (`0` / `8K` / `32K` / `100K`, `decode_tokens_s`) | 1.007 / 1.017 / 0.999 / 1.012 | `0`: `1.017, 1.006, 0.999`; `8K`: `1.054, 0.999, 0.998`; `32K`: `0.995, 1.046, 0.958`; `100K`: `1.040, 1.004, 0.993` | `>= 0.95` (**pass**) |
| `perf/warm_repeat/32768/decode_tokens_s` | 1.036 | `1.024, 1.034, 1.048` | `>= 0.95` (**pass**) |
| `perf/unique_prefix` cold TTFT (`8K` / `32K` / `100K`, `ttft_ms`) | 0.996 / 0.997 / 0.994 | `8K`: `0.995, 0.998, 0.995`; `32K`: `0.997, 1.002, 0.992`; `100K`: `1.003, 0.995, 0.986` | `<= 1.05` (**pass**) |

- **RTX 5090 262K and pair `env86g` pass all 88 gated metrics (`13` below resolution on each):** on `rtx5090-win-a`,
  every gated `par_load`, `perf/unique_prefix`, `perf/warm_repeat` and `perf/queue` check (`queue/0` and `queue/1` decode
  `1.034 / 1.035`, TTFT `0.936 / 0.955`) passes; cold-start ready time across the six blocks (`A1, B1, B2, A2, A3, B3`,
  outside the 88 gated metrics) was `35.2, 35.2, 31.2 s` on `v0.2.10` versus `25.2, 20.2, 20.1 s` on `v0.2.9`
  (`19.2–19.5 s` once file-cache-warm in G16, G20 and G21 vs `18.6–18.9 s` on `v0.2.9`). On `rtx3090-win-a`, every gated
  metric also passes (`queue/0` and `queue/1` decode `1.028 / 0.996`, TTFT `1.000 / 0.981`); cold-start ready time was
  `45.1 s` in all three `v0.2.10` blocks (`60.3, 42.1, 41.6 s` on `v0.2.9`).
- **RTX PRO 6000 (`97` of `100` gated metrics pass, `17` below resolution; owner override `"Override: chain + G23"`):**
  only the three concurrent short-prompt (`w2` 1,000/128) TTFT rows in the table above (`w2/c2/ttft_p50` `1.052`,
  `w2/c2/ttft_p95` `1.136`, `w2/c4/ttft_p50` `1.326`) missed the 5% rule; cold decode rose `+3.9%` to `+6.2%`, `tpot_p50`
  was `0.921–1.031`, and aggregate throughput was at parity. Cold-start ready times were `35.3, 30.2, 30.2 s` on `v0.2.9`
  versus `47.4, 47.4, 46.8 s` on `v0.2.10` (`31.0–31.3 s` once file-cache-warm in G16, G20 and G21 on both versions), and
  startup lines are identical between versions (`24,576` resident expert cache slots, `5,542` borrowed slots, `4`
  batch-MTP drafters, `8,192 MiB` conversation cache; `v0.2.10` adds `strata prefill: QSA layers: norm + rope in one pass
  on, attention gate in the attention epilogue off`). The owner accepted and recorded the concurrent short-prompt TTFT
  regression on 2026-11-03 (~19:50Z, `"Override: chain + G23"`).
- **Greedy identity (`tools/serve_load.py --save/--compare`, `temperature: 0`, 256 tokens vs `A1`):** on
  `rtxpro6000-win-a`, the `v0.2.9` repeats `A2` and `A3` reported `compare: ALL IDENTICAL` across all five sequences
  (`1` single-client plus `4` concurrent) while `v0.2.10` blocks `B1–B3` first differed from `A1` at character `15`
  (`c=1`) and characters `249, 65, 301, 246` (`c=4`); on the single-slot `rtx5090-win-a` (`A2` at char `81`, `A3`, `B2`
  and `B3` at char `0`, `B1` at char `15`) and `rtx3090-win-a` (`A2` and `A3` at char `868`, `B1–B3` at char `15`),
  same-version repeats already differed from `A1`.

### Pair DFlash2 arm and the owner's decision

On `rtx3090-win-a`,
`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`
(`428e1a7`, drafted from the `v0.2.10` `env86g` profile with `--drafting dflash2 --pipeline-windows stock`;
[UPSTREAM.md](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)) pins `strata.drafting: "dflash2"` and
`model.dflash2_source` (`incoai/Qwen3.8-Flash-Next-DFlash2` at `a22a1744e85c17364dcc54a6a420af7135d4c7f6`, offline
`q4_0` and `selq4` packs built by stock `tools/dflash2_pack.py` under `STRATA_NO_ACQUIRE=1`, shipped vocabulary SHA-256
`b1e1d3a7a9e4bf862dcd5923ce661fb59bbd07907e594df5cf86a62ac235cb91`, disk floor `93 GiB` vs `91 GiB`) and drops
`--pipeline-windows 2` (which stock treats as a DFlash2 blocker). At start, the server logs `[strata] drafting: DFlash2
alone (--draft dflash2, --draft-conf 0.35)` and the engine logs `strata serve: DFlash2 drafter on (... graphs captured in
6 ms); windows up to 8 tokens; no MTP layer is loaded (--draft-fallback none); layer split: the drafter is on CUDA1 (last
stage), the other stages' taps are gathered onto it`, raising the expert caches from `10,620 / 8,849` slots (`19.14 /
17.75 GiB`, `79%` resident) on the RTX 3090 / RTX 4090 to `10,768 / 9,126` slots (`19.41 / 18.31 GiB`, `81%` resident) at
`45.0–45.1 s` ready time with the `8,192 MiB` automatic conversation cache enabled:

| `rtx3090-win-a` pair (`A` = `v0.2.10` `env86g` MTP, `B` = `v0.2.10` `df2` DFlash2; final `pass=False`, `13` below resolution) | `B/A` | `pairs` | Bar (`pass`) |
|---|---:|---|---|
| `w1/c1/agg_tps` | 1.001 | `0.998, 1.005, 1.000` | `>= 0.95` (**pass**) |
| `w3/c1/agg_tps` | 1.033 | `1.034, 1.033, 1.031` | `>= 0.95` (**pass**) |
| `w1/c1/ttft_p50` / `w1/c1/ttft_p95` | 0.960 / 0.965 | `0.966, 0.961, 0.952` / `0.965, 0.971, 0.958` | `<= 1.05` (**pass**) |
| `w3/c1/ttft_p50` / `w3/c1/ttft_p95` | 0.967 / 0.967 | `0.965, 0.968, 0.967` / `0.966, 0.967, 0.967` | `<= 1.05` (**pass**) |
| `perf/unique_prefix` cold decode (`0` / `8K` / `32K` / `100K`, `decode_tokens_s`) | 1.101 / 1.082 / 1.136 / 1.093 | `0`: `1.103, 1.118, 1.083`; `8K`: `1.091, 1.080, 1.075`; `32K`: `1.122, 1.169, 1.116`; `100K`: `1.144, 1.076, 1.062` | `>= 1.03` owner bar (**pass**) |
| `perf/warm_repeat/32768/decode_tokens_s` | 1.077 | `1.148, 1.056, 1.029` | `>= 0.95` (**pass**) |
| `perf/unique_prefix` cold TTFT (`8K` / `32K` / `100K`, `ttft_ms`) | 0.955 / 0.973 / 0.980 | `8K`: `0.951, 0.964, 0.951`; `32K`: `0.971, 0.971, 0.978`; `100K`: `0.986, 0.980, 0.975` | `<= 1.05` (**pass**) |
| `w3/c1/max_gap_p50` | 1.112 | `1.096, 1.150, 1.089` | `<= 1.05` (**miss**) |
| `w3/c1/max_gap_p95` | 1.078 | `1.058, 1.140, 1.040` | `<= 1.05` (**miss**) |
| `w3/c1/max_gap_max` | 1.075 | `1.054, 1.139, 1.035` | `<= 1.05` (**miss**) |
| `perf/queue/0/inter_output_event_latency_p95_ms` | 1.162 | `1.163, 1.164, 1.158` | `<= 1.05` (**miss**) |
| `perf/queue/1/inter_output_event_latency_p95_ms` | 1.168 | `1.159, 1.180, 1.166` | `<= 1.05` (**miss**) |
| `perf/queue/1/prefill_tokens_s` | 0.802 | `0.787, 0.819, 0.800` | `>= 0.95` (**miss**) |
| `perf/queue/1/prompt_ms` | 1.227 | `1.230, 1.240, 1.210` | `<= 1.05` (**miss**) |
| `perf/unique_prefix/0/first_visible_text_ms` | 1.052 | `1.002, 1.078, 1.078` | `<= 1.05` (**miss**) |
| `perf/unique_prefix/0/inter_output_event_latency_p95_ms` | 1.122 | `1.137, 1.079, 1.150` | `<= 1.05` (**miss**) |
| `perf/unique_prefix/0/prefill_tokens_s` | 0.948 | `1.030, 0.924, 0.895` | `>= 0.95` (**miss**) |
| `perf/unique_prefix/0/prompt_ms` | 1.060 | `1.003, 1.082, 1.098` | `<= 1.05` (**miss**) |
| `perf/unique_prefix/0/ttft_ms` | 1.052 | `1.002, 1.078, 1.078` | `<= 1.05` (**miss**) |
| `perf/unique_prefix/8192/inter_output_event_latency_p95_ms` | 1.167 | `1.159, 1.175, 1.168` | `<= 1.05` (**miss**) |
| `perf/unique_prefix/32768/inter_output_event_latency_p95_ms` | 1.158 | `1.158, 1.152, 1.165` | `<= 1.05` (**miss**) |
| `perf/unique_prefix/102400/inter_output_event_latency_p95_ms` | 1.170 | `1.178, 1.162, 1.171` | `<= 1.05` (**miss**) |
| `perf/warm_repeat/32768/inter_output_event_latency_p95_ms` | 1.156 | `1.161, 1.159, 1.148` | `<= 1.05` (**miss**) |

- **Outcome and owner decision (2026-11-03 ~21:28Z, `"Run chain, make DFlash2 current"`):** the DFlash2 arm meets the
  owner's `+3%` decode bar at every depth (`1.082` at 8K and `1.093` at 100K; `1.101 / 1.136 / 1.077` at `0 / 32K / warm
  32K`; `1.104 / 1.164` on `perf/queue/0` and `perf/queue/1`), cuts 8K–100K TTFT `B/A` to `0.955–0.980` (`0.953` on warm
  32K) and keeps `request_wall_ms` at `0.906–0.974` (`13` metrics below resolution; greedy output differed from `A1` in
  every block: `A2` at char `34`, `A3` at `84`, `B1` at `64`, `B2` at `123`, `B3` at `49`). All 16 5%-rule misses in the
  table above come from DFlash2 emitting verified windows of up to 6 draft tokens (`--spec 6`, 8-token verify buffers)
  in larger bursts (`w3` `max_gap` and `inter_output_event_latency_p95_ms` `1.122–1.170`), plus queued-request prefill
  (`0.802`, `prompt_ms` `1.227`, while `queue/1/request_wall_ms` is `0.906` and `ttft_ms` is `0.937`) and empty-prompt
  prefill/TTFT (`1.052`). The owner accepted that trade-off (`"Run chain, make DFlash2 current"`), keeping `v0.2.10`
  `env86g` (`pw2`) as the pair's qualified rollback.

### Server chains (G10–G21, G24, G26) and Studio route G23

The PRO main chain, both RTX 5090 main chains and the Mac Studio route G23 ran at tooling
`9a06ec1d93134174654438071b958689ed82cac9` (with the complete PRO G14 rerun at `7971a1a`); the pair `env86g` main chain
ran at `7b338d9422c86d4a5859144db3451a2c97c487b8` after admitting engine `0.1.56`'s stage order (with its complete G20
rerun at `837bc89`); and the pair DFlash2 (`df2`) main chain ran at `837bc8908e311de1887a5bd0566204ff830ac491`
(`21:45–22:28Z`), where every start logged stock's `[strata] drafting: DFlash2 alone (--draft dflash2, --draft-conf
0.35)`. On every 24-gate server ledger, the 14 automated real-host and evaluation gates (`G10–G21`, `G24`, `G26`) pass,
the 7 source and host-free operator receipts (`G00–G06`, from the host-free suites at `8b534b8` with `948` tests per
lane and hosted CI run `41723093180` on pull request 75) follow, and the 3 optional gates (`G22`, `G23`, `G25`) are not
applicable (`21 pass, 3 not applicable`); on the independent Mac Studio client-route ledger, `G23` passes (`launch-omp`
smoke `ROUTE OK`, owned stop):

| Lane | Tooling | Gates | G24 scored (pilot) | Scored batch wall s (`v0.2.9` predecessor or `v0.2.10` `env86g`) | G16 / G20 / G21 ready s (`v0.2.9` predecessor or `v0.2.10` `env86g`) | Against the predecessor / rollback and notes |
|---|---|---|---|---|---|---|
| [PRO (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0`)](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/qualification.json) | `9a06ec1` (`7971a1a` G14 rerun) | 14 pass (`21 pass, 3 not applicable`) | 16/18 (5/6) | 569.6 ([631.2](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/qualification.json)) | 31.1 / 31.0 / 31.3 (31.0 / 31.0 / 31.3) | misses: `tool-loop` x2 (attempts 2, 3; `v0.2.9` scored 16/18, pilot 5/6); first G14 failed on slot-3 prompt stop (`78990a`), kept beside passing `7971a1a` rerun (`9417d2`); G15 post-kill recall `45.1` and `44.5 s` (`v0.2.9` `45.4` and `44.7 s`); G17 100K cold prefill `10,680 ms` and near-limit task `25.9 s` (`v0.2.9` `10,699 ms` and `25.1 s`) |
| [RTX 5090 262K (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0`)](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/qualification.json) | `9a06ec1` | 14 pass (`21 pass, 3 not applicable`) | 18/18 (5/6) | 738.7 ([791.1](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/qualification.json)) | 19.3 / 19.2 / 19.5 (18.7 / 18.6 / 18.9) | misses: none (`0/18`, pilot `tool-loop` x1; `v0.2.9` scored 17/18, pilot 5/6); Docker/WSL stopped; G15 post-kill recall `18.4` and `17.8 s` (`v0.2.9` `18.4` and `18.0 s`); G17 100K cold prefill `12,184 ms` and near-limit task `31.4 s` (`v0.2.9` `12,214 ms` and `30.6 s`) |
| [RTX 5090 131K (`win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0`)](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/qualification.json) | `9a06ec1` | 14 pass (`21 pass, 3 not applicable`) | 16/18 (6/6) | 741.7 ([762.5](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/qualification.json)) | 18.7 / 18.7 / 18.9 (26.8 / 16.1 / 16.3) | misses: `tool-loop` x2 (attempts 1, 2; `v0.2.9` scored 14/18, pilot 5/6); ran in the Docker/WSL-stopped window; G15 post-kill recall `31.9` and `31.7 s`; G17 100K cold prefill `13,346 ms` and near-limit task `17.4 s` |
| [Pair DFlash2 (`win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`)](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/qualification.json) | `837bc89` | 14 pass (`21 pass, 3 not applicable`) | 17/18 (5/6) | 915.6 ([1,044.7](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/qualification.json)) | 43.1 / 43.2 / 43.4 (55.3 / 43.2 / 55.7) | misses: `tool-loop` x1 (attempt 3, pilot `tool-loop` x1; `v0.2.10` `env86g` rollback scored 16/18, pilot 5/6); every start logged `[strata] drafting: DFlash2 alone (--draft dflash2, --draft-conf 0.35)`; G15 post-kill recall `49.0` and `49.2 s` (`v0.2.10` `env86g` `63.2` and `57.7 s`); G17 100K cold prefill `25,910 ms` and near-limit task `59.0 s` (`v0.2.10` `env86g` `26,765 ms` and `59.9 s`) |
| [Pair `env86g` rollback (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0`)](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/qualification.json) | `7b338d9` (`837bc89` G20 rerun) | 14 pass (`21 pass, 3 not applicable`) | 16/18 (5/6) | 1,044.7 ([821.8](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/qualification.json)) | 55.3 / 43.2 / 55.7 (43.5 / 43.6 / 43.9) | misses: `tool-loop` x2 (attempts 2, 3; `v0.2.9` scored 15/18, pilot 5/6); first G20 (`c63bb9`, ready `55.4 s`) failed only on `user_omp_dir_untouched_since_root_created` after another tenant's stock OMP wrote `~/.omp` between exclusive holds, kept beside passing `837bc89` rerun (`559436`, ready `43.2 s`); G15 post-kill recall `63.2` and `57.7 s`; G17 100K cold prefill `26,765 ms` and near-limit task `59.9 s` (`v0.2.9` `26,582 ms` and `59.8 s`) |
| [Mac Studio route (`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0`)](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/qualification.json) | `9a06ec1` | G23 pass | — | — | — | stream TTFT `0.219 s` vs `0.172 s` on the [`v0.2.9` route](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/qualification.json); health RTT `21.9–24.4 ms` (`v0.2.9` `5.5–6.3 ms`); missing key refused, wrong key HTTP 401; tunnel reopen (`0.82 s`), client restart (`0.67 s`) and server restart (`1.41 s`, new server instance) recall all true; `launch-omp` smoke `ROUTE OK`, owned stop |

Every G24 miss across all five server chains is a `tool-loop` verifier failure (`0` timeouts, `0` protocol counters, `0`
compactions, and `[0, 0, 0]` exit codes across the three `continuation`-task restart hooks). With the engine serving,
G10 measured **129.12 GiB** (`138,642,788,352 B`, minimum sampled `129.10 GiB`) available RAM and **83.05 GiB**
(`89,174,695,936 B`) Windows commit headroom of a **219.70 GiB** (`235,900,456,960 B`) commit limit on the PRO (`74,890
MiB` GPU memory vs `129.57 GiB` available RAM, `83.35 GiB` commit headroom and `74,906 MiB` GPU memory on `v0.2.9`;
[G10](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/evidence/g10-20261103T200708Z-2ed5d1.json));
**13.41 GiB** (`14,395,211,776 B`, minimum sampled `13.26 GiB`) available RAM and **20.31 GiB** (`21,806,542,848 B`)
commit headroom of an **85.15 GiB** (`91,434,225,664 B`) commit limit on the RTX 5090 262K profile with Docker Desktop
and WSL stopped (`30,776 MiB` GPU memory vs `13.35 GiB` available RAM, `20.10 GiB` commit headroom and `30,742 MiB` GPU
memory on `v0.2.9`;
[G10](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/evidence/g10-20261103T182717Z-f032be.json));
**11.52 GiB** (`12,373,958,656 B`, minimum sampled `11.44 GiB`) available RAM and **18.56 GiB** (`19,923,595,264 B`)
commit headroom of the **85.15 GiB** (`91,434,225,664 B`) commit limit on the RTX 5090 131K profile in the same
Docker/WSL-stopped window (`30,954 MiB` GPU memory vs `12.03 GiB` available RAM and `18.78 GiB` commit headroom on
`v0.2.9`;
[G10](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/evidence/g10-20261103T190621Z-3ae3e3.json));
**65.65 GiB** (`70,487,412,736 B`, minimum sampled `65.61 GiB`) available RAM and **27.51 GiB** (`29,534,670,848 B`)
commit headroom of a **135.69 GiB** (`145,695,096,832 B`) commit limit on the pair DFlash2 profile (`[22,892, 23,418]
MiB` GPU memory on cards `1, 0`, `kept_configured`;
[G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g10-20261103T214738Z-369918.json));
and **65.37 GiB** (`70,189,993,984 B`, minimum sampled `65.35 GiB`) available RAM and **27.54 GiB** (`29,568,094,208 B`)
commit headroom of the **135.69 GiB** (`145,695,096,832 B`) commit limit on the pair `env86g` rollback (`[22,762, 23,160]
MiB` GPU memory on cards `1, 0`, `kept_configured`, vs `65.68 GiB` available RAM, `27.77 GiB` commit headroom and
`[22,762, 23,166] MiB` on `v0.2.9`;
[G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g10-20261103T185601Z-a5545f.json)).
In G19, the automatic conversation cache stayed enabled across all five server chains: **8,192 MiB** (`30` parks;
`20,673` of `20,702` tokens reused in `385 ms` vs `2,424 ms` cold; lowest available RAM `119.38 GiB` in G18L; G26
second-root install `22.0 s` and start `50.3 s`;
[G19](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/evidence/g19-20261103T203013Z-5e0170.json),
[G26](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/evidence/g26-second-root-20261103T204418Z.json))
on the PRO; **4,352 MiB** (`22` parks; `20,672` of `20,701` tokens reused in `289 ms` vs `2,665 ms` cold; lowest
available RAM `7.82 GiB` in G18L and `8.60 GiB` in G17; G26 install `11.7 s` and start `22.4 s`;
[G19](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/evidence/g19-20261103T183443Z-5605d6.json),
[G26](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/evidence/g26-second-root-20261103T185314Z.json))
on the RTX 5090 262K; **3,584 MiB** (`29` parks; `20,680` of `20,699` tokens reused in `260 ms` vs `2,805 ms` cold;
lowest available RAM `7.43 GiB` in G17; G26 install `10.7 s` and start `36.2 s`;
[G19](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/evidence/g19-20261103T191259Z-b8c6d5.json),
[G26](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/evidence/g26-second-root-20261103T193004Z.json))
on the RTX 5090 131K; **8,192 MiB** (`25` parks; `20,680` of `20,700` tokens reused in `456 ms` vs `7,695 ms` cold;
lowest available RAM `56.87 GiB` in G18L, `57.70 GiB` in G18 and `61.05 GiB` in G17; G26 install `33.1 s` and start
`74.3 s`;
[G19](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g19-20261103T220526Z-780426.json),
[G26](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g26-second-root-20261103T222822Z.json))
on the pair DFlash2 profile; and **8,192 MiB** (`32` parks; `20,670` of `20,699` tokens reused in `499 ms` vs `7,884 ms`
cold; lowest available RAM `56.62 GiB` in G18L, `57.09 GiB` in G18 and `60.95 GiB` in G17; G26 install `27.0 s` and
start `66.8 s`;
[G19](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g19-20261103T191605Z-fd9a80.json),
[G26](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g26-second-root-20261103T194054Z.json))
on the pair `env86g` rollback.

On the Mac Studio route (`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0`), G23 passed
at `9a06ec1` on 2026-11-03 (`20:45–20:48Z`,
[receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/receipts/2a07609cb1f0410fa8d650ec59ee891f.json),
[evidence](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/evidence/g23-20261103T204512Z.json)):
a missing key was refused before launch, a wrong key returned HTTP `401`, health RTT was `21.9–24.4 ms`, stream TTFT
through the SSH local forward was `0.219 s` (vs `0.172 s` on the `v0.2.9` route), a tunnel drop failed the turn in
flight with the prior transcript preserved, nonce recall passed after tunnel reopen (`0.82 s`), client restart
(`0.67 s`) and a verified server restart (`1.41 s`, new server instance), and the `launch-omp` smoke turn returned
`ROUTE OK` before the owned stop.

### Kept failures and complete-gate reruns (PRO G14, pair G20)

Both first-run gate failures are retained in their release ledgers beside passing complete-gate reruns:

- **PRO `G14` slot-filling prompt stop and rerun (`7971a1a`):** in the PRO main chain at `9a06ec1`
  ([failed receipt](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/receipts/g14-20261103T201019Z-78990a.json),
  [failed G14 evidence](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/evidence/g14-20261103T201019Z-78990a.json),
  [G14Q evidence](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/evidence/g14q-20261103T201712Z-9205d5.json)),
  `scripts/realhost_gates.py`'s `fill_slots` helper filled the four batch slots with `"Count from 1 to 3000, one number
  per line, nothing else. (3)"`. The third stream read its trailing `"(3)"` as `"count to 3"` and stopped
  (`finish: "stop"`) after `6` tokens while the other three streams generated `8,000` tokens (`finish: "length"`), so
  only three slots decoded, the fifth request was served in the free slot (`10` tokens) instead of queued, and `G14`
  failed on `queued_observed: false`. Commit `7971a1a` moved the stream label to the front of the prompt (`"Stream 3.
  Count from 1 to 3000 ..."`), and the complete rerun (`start, g14, g14q, stop`, `21:31–21:33Z`, published in
  `8b534b8`;
  [passing receipt](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/receipts/g14-20261103T213214Z-9417d2.json),
  [passing G14 evidence](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/evidence/g14-20261103T213214Z-9417d2.json),
  [passing G14Q evidence](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/evidence/g14q-20261103T213232Z-845f0f.json))
  passed: all four batch slots decoded (`730, 694, 670, 642` tokens before disconnect), the extra request queued
  (`queued_observed: true`) and was cancelled (`finish: "cancel"`, `0` tokens), five follow-up requests returned HTTP
  `200`, and all three queued-disconnect `G14Q` sub-probes passed in `16.0 s`.
- **Pair `env86g` `G20` multi-tenant `~/.omp` baseline and rerun (`837bc89`):** in the pair `env86g` main chain at
  `7b338d9`
  ([failed receipt](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/receipts/g20-20261103T191639Z-c63bb9.json),
  [failed G20 evidence](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g20-20261103T191639Z-c63bb9.json)),
  every lifecycle predicate passed (second start refused, stop freed port `18090` with `0` orphans and GPUs at `[180, 0]
  MiB`, repeat stop idempotent, restart ready in `55.4 s` / `64.8 s` wall, `stock_strata_appdata_absent: true`,
  scheduled tasks unchanged), and `G20` failed only on `user_omp_dir_untouched_since_root_created: false` because
  another tenant's stock OMP wrote the host user's default `~/.omp` between our exclusive host-lock holds (after the
  root was created at `17:56Z` during the stage-order measurement window and before the `requalify` run began at
  `18:54Z`). Commit `837bc89` baselines `G20`'s untouched `~/.omp` check at the `requalify` run start (`--since`,
  recorded as `user_omp_baseline` and `user_omp_dir_untouched_since_baseline`, while standalone `g20` keeps the root's
  creation; every `omp-strata` step of a `requalify` run, `install` included, still lies after the baseline), and the
  complete rerun (`start, g20, stop`, `20:42–20:44Z`, published in `e300b27`;
  [passing receipt](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/receipts/g20-20261103T204350Z-559436.json),
  [passing G20 evidence](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/evidence/g20-20261103T204350Z-559436.json))
  passed with `user_omp_dir_untouched_since_baseline: true` (`2026-11-03T20:42:41Z`, `source: "requalify run start"`)
  and restart readiness `43.2 s` (`52.6 s` wall).

### Admissions in this tuple

- **`e8dffe9`, `890f61f`, `1b19f53`, `f33d1db`, `2a7f88e`, `32b2447` and `9a06ec1` (`v0.2.10` setup planning, server
  start path, engine `0.1.56` and OMP `18.16.0` review;
  [UPSTREAM.md](UPSTREAM.md#strata-v0210-setup-review-component-engine),
  [engine environment](UPSTREAM.md#stock-engine-environment-v0210--0156),
  [OMP `18.16.0`](UPSTREAM.md#stock-omp-18160-surface)):** `e8dffe9` and `890f61f` admit the five changed setup-planning
  surfaces in stock `v0.2.10` (`DEFAULT_RECOMMENDATION_0_2_10` preserving all eight selected AST nodes including the
  unchanged RAM clamp, `REVIEWED_HELPERS_0_2_10` / `STREAM_NEED_0_2_10` while keeping rule `(1)` for the admitted
  streamed host floor, `DISK_0_2_10` refusing any `drafter` attribute on `a`, and paired `WRITE_CALL_0_2_10` /
  `FRESH_WRITE_0_2_10`). `1b19f53`, `f33d1db`, `2a7f88e` and `9a06ec1` review `SERVER_PINNED_PATH_0_2_10` and the whole
  `strata_control/{drafting,vram_fit,draft_layer}.py` modules, admit engine `0.1.56` (`06698c674673+cuda13.0`) to
  `ENGINE_ENV_REVIEWED_ENGINES` with byte-identical `parallel_stack`, `gdn_stack` and `sm86_table` groups, forbid
  DFlash2 start flags on MTP profiles, hash all four start-path sources (`install.runtime_sources`) in
  `runtime_identity` on every engine `0.1.56+` root, and verify both launch intervals at start.
- **`a15e1f9`, `b591302`, `4d6136a`, `118a52c`, `c7ba6c4`, `428e1a7` and `4b09005` (pair DFlash2 drafter;
  [UPSTREAM.md](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)):** pins `strata.drafting: "dflash2"` and
  `model.dflash2_source`, stages the revision-pinned `incoai/Qwen3.8-Flash-Next-DFlash2` inputs under
  `downloads/dflash2/<revision>/`, packs `q4_0` and `selq4` offline via stock `tools/dflash2_pack.py` under
  `STRATA_NO_ACQUIRE=1` (bypassing `drafting_fetch.ensure()`), requires one server `drafting: DFlash2 alone` line and
  one engine `strata serve: DFlash2 drafter on` line with no loaded MTP at start, drafts the pair `df2` variant by
  dropping `--pipeline-windows 2` from `env86g` (`+2 GiB` disk floor), and isolates default test subjects from DFlash2
  pins (`947` tests per lane).
- **`7b338d9` (engine `0.1.56` pair stage-order admission):** admits engine `0.1.56` (`06698c674673+cuda13.0`) to
  `lifecycle.STAGE_ORDER_REVIEWED_ENGINES` after the pair `env86g` measurement start parsed complete
  (`kept_configured`, `[1, 0]`, RTX 3090 on layers `0–23` with `19.14 GiB` expert cache and RTX 4090 on layers `24–47`
  with `17.75 GiB` expert cache under pinned manual split `24`, one engine generation, `[strata] Drafting: MTP
  (DFlash2 isn't available in this mode)`).
- **`74c0ff1`, `837bc89`, `08e7032`, `9d01e33`, `7971a1a`, `e300b27`, `8b534b8`, `6e795bb`, `1f2d483`, `8a2c9ec` and
  `f115173` (campaign, gate fixes, publications, receipts, restored state, qualification and CI matrix):** `74c0ff1`
  opens `releases/campaigns/v0.2.10.json` and drafts the `v0.2.10` profiles and Mac Studio route; `837bc89` baselines
  `G20`'s untouched `~/.omp` check at the `requalify` run start; `08e7032` publishes the RTX 5090 262K and 131K chains
  and `restored-state.json` records; `9d01e33` publishes the pair `env86g` main chain; `7971a1a` leads `G14`'s
  slot-filling prompt with its stream label; `e300b27` publishes the PRO main chain, the Studio route G23 and the pair
  `env86g` G20 rerun; `8b534b8` publishes the PRO G14 rerun and the PRO and Studio route `restored-state.json` records;
  `6e795bb` and `1f2d483` publish the pair DFlash2 chain, the pair `restored-state.json` records and the operator
  receipts (`G00–G06` from the host-free suites at `8b534b8` with `948` tests per lane and hosted CI run `41723093180`
  on pull request 75); `8a2c9ec` qualifies all five server profiles and the Studio route and moves `CURRENT` to the PRO
  `v0.2.10` profile; and `f115173` updates the CI `suite` matrix to run each current `v0.2.10` profile with its
  rollback.

### Restored state

- **`rtxpro6000-win-a` ([PRO restored-state](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0/restored-state.json),
  [route restored-state](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.10-omp18.16.0/restored-state.json)):**
  across the three exclusive host-lock windows (`17:53Z`, `20:05–20:47Z`, `21:30–21:33Z`), no user was signed in before
  or after, GPU memory was `433 MiB`, both OCR tenant containers stayed exited as found, `180.2 GiB` / `179.5 GiB` RAM
  was available before / after, and every `omp-strata` root stopped with `0` `omp-strata` processes remaining.
- **`rtx5090-win-a` ([262K restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0/restored-state.json),
  [131K restored-state](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0/restored-state.json)):**
  both `v0.2.10` roots stopped before restoration with `0 MiB` GPU memory and no `omp-strata` process; the host
  supervisor restarted Docker Desktop and provisioned the lane distro's WSL integration at `19:32Z`, the owner's pinned
  relaunch script recreated the production NInfer container after `fleet return` failed closed (healthy at `19:36Z`), the
  retired controller state was kept, and the container was commissioned in the `Fleet` phase at generation `1` at
  `19:38Z` with admission open, no blockers or owned markers, container-host supervisor, encoder and lane-container
  supervisor tasks `Ready`, both pause markers removed, authenticated health HTTP `200` and `unless-stopped` restart
  policy.
- **`rtx3090-win-a` ([pair `df2` restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/restored-state.json),
  [pair `env86g` restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0/restored-state.json)):**
  lead censuses under the exclusive host lock at the start and end of each of the six pair windows (`17:55–18:19Z`,
  `18:26–18:46Z`, `18:53–19:41Z`, `19:47–20:27Z`, `20:41–20:45Z`, `21:44–22:29Z`) found no signed-in user session, GPUs
  at `180–182 MiB` on the display-attached RTX 4090 and `0 MiB` on the RTX 3090, `120.0–120.2 GiB` available RAM, and
  both `v0.2.10` roots stopped with no `omp-strata` or other engine process remaining after each window.

## Stock tuning pins on Strata v0.2.9 (2026-11-02): stock OMP 18.15.0

Following the [earlier 2026-11-02 `v0.2.9` qualification](#strata-v029-windows-2026-11-02-stock-omp-18150), its
single-sample [feature arms](#feature-arms-on-the-v029-roots) and its [PRO model screens](#model-screens-on-the-pro),
the owner's Asks on 2026-11-02 answered `"All three hosts"` for tuning and `"Prepare both for Terminal-Bench"` for the
two PRO model candidates (~12:15Z), `"When the kit is ready today"` for the `rtx5090-win-a` window (~15:20Z), and
`"Qualify and make current"` (~21:50Z) for the PRO variant
(`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0`), its Mac Studio
route (`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0`) and the RTX 5090 262K variant
(`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0`), with the [2026-11-02 `v0.2.9` base
profiles](#strata-v029-windows-2026-11-02-stock-omp-18150) as their rollbacks. The RTX 4090 + RTX 3090 pair variant
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`)
missed the pre-registered `w1` 512/512 single-request A/B bar (`1.039` vs `>= 1.05`) while passing every decode and TTFT
bar; the owner then overrode that one bar on 2026-11-02 (~23:20Z: `"Yes approved: Yes, if you approve an override.
There's nothing in the pair profile to fix."`), its requalification chain on 2026-11-03 (06:45–07:27Z, tooling
`d0a1254`) passed all 14 measured gates, and it is now qualified and current with the `v0.2.9` pair base profile as its
rollback (`v0.2.8` split-24 trim moves to earlier qualified history). Every change is a stock engine or setup option
pinned in a new profile id beside the qualified base profiles, which are unchanged. Host windows were serialized with
the fleet's exclusive host locks; on `rtxpro6000-win-a` both OCR containers stayed exited as found, and on
`rtx3090-win-a` nobody was signed in.

### Admissions

- **`omp-strata` commits `7411d03` and `cbe3ada` (`strata.engine_env`, `setup_args.kv_streaming: "off"` and
  `strata.kv_grow`; [UPSTREAM.md](UPSTREAM.md#stock-engine-environment-v029--0155)):**
  - `strata.engine_env` admits only complete stock-owned string value groups on reviewed engine `0.1.55` (build
    `99866a47a2b8+cuda13.0`), refusing partial groups, extra names, other values and raw `strata.env` /
    `setup_args.env`. The server-owned groups are the nine-switch parallel-slot stack (`parallel_stack` = stock
    `serve/server.py` `PARALLEL_STACK_ENV`: `STRATA_CKPT_POOL=1`, `STRATA_CKPT_POOL_READY=4`,
    `STRATA_SLOT_CKPT_MOVE=1`, `STRATA_SLOT_COPY_DIRECT=1`, `STRATA_SLOT_COPY_BATCHSYNC=1`,
    `STRATA_BATCH_GDN_GROUPS=1`, `STRATA_BATCH_ATTN_ROWS=1`, `STRATA_BATCH_SELF_COMMIT=1`, `STRATA_QSA_SLOTS=1`,
    requiring at least two batch slots like stock's gate) and the GDN tensor-core prompt stack (`gdn_stack` = stock
    `serve/server.py` `GDN_STACK_CUDA`: `STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2`); the engine-owned group is the
    nine-switch `sm_86` default table (`sm86_table`: `STRATA_ADAPT_NOWAIT=1`, `STRATA_ADAPT_LAG=2`,
    `STRATA_CPU_IQ_ALL_EXACT1=1`, `STRATA_SIDE_MIXER=2`, `STRATA_ATTN_DAILY=1`, `STRATA_GR_UP75=1`, `STRATA_GU_SWIGLU=1`,
    `STRATA_QSA_ROWS=1`, `STRATA_B6_MMVQ_ROWS=1`, admitted on mixed-architecture multi-GPU profiles containing an
    `sm_86` card; [Strata#3313](https://github.com/Niko1221/Strata/issues/3313)). Stock `serve/server.py` enables both
    server stacks automatically only on Linux (`parallel_stack_platform()`), while `child_env` copies the configuration's
    `env` dictionary before those `setdefault` calls, so pinning the literal stock dictionaries in config `env` on
    Windows uses the unmodified stock delivery path without inherited process variables. `cbe3ada` digest-pins the
    32-function same-module call closure of `child_env` and `engine_args` in `serve/server.py`, and env-pinned runtime
    identity hashes `serve/server.py` on install and every start (and requires every batch-window startup line to end
    `... , one-row windows keep their rows` when `parallel_stack` is pinned).
  - `setup_args.kv_streaming: "off"` passes stock setup's `--kv-streaming off` on single-GPU engine `0.1.55+` profiles,
    removing `--kv-resident 32768` so KV stays in VRAM and refusing any `--kv-resident` flag or
    `strata generate: KV streaming:` startup line. `cbe3ada` re-derives setup RAM floors from stock's non-streaming
    plan when `--kv-streaming off` is added (`34 GiB` available-RAM start floor on the RTX 5090 262K plan vs `36 GiB`
    with streamed KV, while preserving any higher predecessor floor) and adds `--ple-io stock` so a draft profile can
    drop an inherited `--ple-io direct` pin and reuse a verified prepared NVFP4 conversion without converting again.
  - `strata.kv_grow: true` pins stock's valueless `--kv-grow` flag on single-GPU engine `0.1.55+` profiles alongside
    `setup_args.kv_streaming: "off"`, allocating KV VRAM only for reached context cells and requiring the
    `strata generate: elastic K/V: ... as the context grows` startup line on every launch.
- **`61250a9` (`UD-IQ4_XS` on the PRO; [UPSTREAM.md](UPSTREAM.md#stock-ud-iq4_xs-budget-lane-v029)):** on the
  192 GiB-RAM PRO at 262,144 tokens with four slots, stock `unsloth_budget` returns false so every expert fits in the
  resident arena (`budget` is `None`, no `--resident-budget-gib`), and stock setup writes `STRATA_HC_Q8=1` and
  `STRATA_ROUTE_TAIL_SKIP=0` into config `env`, recorded on the profile as `strata.setup_env` (cannot be combined with
  `strata.engine_env`).
- **`e347fb6` (model-card license derivation):** when drafting a profile on another model repository, takes
  `model.license` from the pinned revision's model card instead of inheriting the predecessor repository's license.
- **`f3fed60` and `e281687` (drafts and composed fixtures):** `f3fed60` drafts the tuned variants, the two PRO model
  candidates and their Mac Studio routes; `e281687` updates the composed host-free test fixtures across all 14
  profile lanes (`903` tests per lane).
- **`acd7549` (reinstall config `env` carry-over fix, found on `rtx5090-win-a`):** a requalification chain reinstalls
  the integration root before running gates. On the RTX 5090 variant's first chain, stock `setup.py`'s `carry_over`
  helper (which preserves existing config `env` entries that stock setup does not own) kept the previous pin's
  `STRATA_GDN_TC` and dropped `STRATA_GDN_CONVL2` (which stock setup treats as setup-owned through its `gfx1103`
  table); the `engine_env` install step refused any existing config `env`, so the RTX 5090 variant's first chain
  stopped at install (exit code `4`) before any gate ran and its start check refused the partial `env`. Fixed in
  `acd7549` with a regression test so an existing config `env` is replaced only when all of its entries belong to the
  profile's `strata.engine_env` pin.
- **`2804c1d`, `d05f660`, `343fab3`, `f7f82aa`, `6b972fa`, `1f699b4`, `8bbf9a8` and `98d8c32` (publications, restored state, receipts and CI matrix):**
  `2804c1d` and `d05f660` publish the PRO and RTX 5090 variant requalifications, the Mac Studio route G23 and their
  `restored-state.json` records, and `343fab3` adds their operator receipts from the host-free suites at `d05f660` (`903`
  tests per lane) and `omp-strata` hosted CI run `41499865044` on pull request 73 (`b802d5f` qualifies them, `b770db0`
  updates the CI matrix). Under the owner's override for the pair `env86g` variant, `f7f82aa` publishes its 14-gate
  requalification chain (`d0a1254`), `restored-state.json` and `COMPATIBILITY.md`, `6b972fa` adds its CI row, `1f699b4`
  adds its operator receipts from the host-free suite at `6b972fa` (`903` tests, `29` skipped) and hosted CI run
  `41597184710` on pull request 74, `8bbf9a8` marks its manifest `qualified` with empty blockers, and `98d8c32` updates
  the CI `suite` matrix so the pair rows are `env86g` current and the `v0.2.9` base rollback.

### A/B against the v0.2.9 base

Each host ran three paired cold-start blocks (`A B B A A B`, where `A` is the qualified `v0.2.9` base root and `B` is
the tuned variant root, with fixed pre-registered acceptance thresholds set before the window; `—` marks metrics
reported without a pre-registered threshold) using stock Strata's `tools/par_load.py` + `tools/par_analyze.py` (`w1`:
512-token prompt / 512 output tokens at concurrency `c=1`, 3 measured rounds after 1 warm round; `w2`: 1,000-token
prompts / 128 output tokens at `c=1, 2, 4`, 3 rounds after 2 warm; `w3`: 32,768-token prompts / 128 output tokens at
`c=4`, 1 round after 1 warm on the 4-slot PRO and at `c=1`, 2 rounds after 1 warm on the single-slot RTX 5090 and pair;
`agg_tps`: aggregate completion tokens/s; `ttft_p95`: 95th-percentile time to first token; `par_analyze.py` writes its
`ci95` range across the three pairs and computes latency `geomean` and pair `ratios` as `A/B`, while `B/A` below is `B`
over `A`), `scripts/perf_probe.py` (512 output tokens per depth, unique prefix, one repeat per cold start) and stock
`tools/serve_load.py --save/--compare` (`temperature: 0`, 256 output tokens, compared against block `A1`):

| `rtxpro6000-win-a` metric (`A` = `slots4-batchmtp-pledirect`, `B` = `slots4-batchmtp-pledirect-kvvram-envpg`, seed/nonce `tune029pro`) | Base `A` mean (or blocks `A1, A2, A3`) | Tuned `B` mean (or blocks `B1, B2, B3`) | `B/A` geomean (`[ci95]` and pair ratios) | Pre-registered threshold |
|---|---:|---:|---|---|
| `par_load` `w2` 1,000/128 `c=1` `agg_tps` (tok/s) | 122.02 | 135.82 | `1.113 [1.101, 1.135]` (`B/A` pairs `1.1037, 1.1012, 1.1345`) | — |
| `par_load` `w2` 1,000/128 `c=2` `agg_tps` (tok/s) | 107.81 | 139.32 | `1.293 [1.256, 1.331]` (`B/A` pairs `1.2921, 1.256, 1.3306`) | — |
| `par_load` `w2` 1,000/128 `c=4` `agg_tps` (tok/s) | 115.81 | 156.09 | `1.348 [1.316, 1.376]` (`B/A` pairs `1.3157, 1.3527, 1.3756`) | `>= 1.15` (**pass**) |
| `par_load` `w3` `4 × 32K` (`c=4`) `agg_tps` (tok/s) | 15.45 | 17.47 | `1.131 [1.096, 1.175]` (`B/A` pairs `1.1234, 1.1748, 1.0957`) | — |
| `par_load` `w2` 1,000/128 `c=1` `ttft_p95` (s) | 0.546 | 0.439 | `0.804` (`A/B` `1.243 [1.199, 1.301]`, `A/B` pairs `1.2317, 1.1989, 1.301`) | `<= 1.00` (**pass**) |
| `par_load` `w2` 1,000/128 `c=2` `ttft_p95` (s) | 1.148 | 0.877 | `0.764` (`A/B` `1.309 [1.131, 1.520]`, `A/B` pairs `1.3059, 1.1306, 1.5197`) | — |
| `par_load` `w2` 1,000/128 `c=4` `ttft_p95` (s) | 2.329 | 1.592 | `0.683` (`A/B` `1.464 [1.387, 1.505]`, `A/B` pairs `1.3875, 1.5015, 1.5053`) | — |
| `par_load` `w3` `4 × 32K` (`c=4`) `ttft_p95` (s) | 29.932 | 27.166 | `0.908` (`A/B` `1.101 [1.064, 1.149]`, `A/B` pairs `1.0925, 1.1486, 1.0644`) | — |
| `perf_probe` cold decode at `0` (`decode_tokens_s`, tok/s) | 333.40 (`335.65, 327.66, 336.89`) | 333.50 (`332.45, 338.24, 329.81`) | `1.000` (`B/A` pairs `0.990, 1.032, 0.979`) | `>= 0.98` (**pass**) |
| `perf_probe` cold decode at `100K` (`102,400`, `decode_tokens_s`, tok/s) | 319.56 (`321.06, 319.88, 317.74`) | 326.56 (`324.81, 325.12, 329.75`) | `1.022` (`B/A` pairs `1.012, 1.016, 1.038`) | `>= 0.98` (**pass**) |

| `rtx5090-win-a` 262K metric (`A` = `coder-iq1m-262k`, `B` = `coder-iq1m-262k-kvvram-kvgrow-envg`, Docker/WSL stopped, seed/nonce `tune0295090`) | Base `A` mean (or blocks `A1, A2, A3`) | Tuned `B` mean (or blocks `B1, B2, B3`) | `B/A` geomean (`[ci95]` and pair ratios) | Pre-registered threshold |
|---|---:|---:|---|---|
| `par_load` `w1` 512/512 `c=1` `agg_tps` (tok/s) | 167.59 | 171.72 | `1.025 [1.012, 1.044]` (`B/A` pairs `1.0119, 1.0185, 1.0437`) | — |
| `par_load` `w3` 32K (`c=1`) `agg_tps` (tok/s) | 23.25 | 25.21 | `1.084 [1.079, 1.089]` (`B/A` pairs `1.0843, 1.0789, 1.0893`) | — |
| `par_load` `w1` 512/512 `c=1` `ttft_p95` (s) | 0.277 | 0.267 | `0.964` (`A/B` `1.038 [1.006, 1.064]`, `A/B` pairs `1.0064, 1.0441, 1.0636`) | — |
| `par_load` `w3` 32K (`c=1`) `ttft_p95` (s) | 4.790 | 4.388 | `0.916` (`A/B` `1.092 [1.090, 1.094]`, `A/B` pairs `1.0943, 1.0895, 1.0909`) | — |
| `perf_probe` cold TTFT at `32K` (`32,768`, `ttft_ms`, ms) | 4,291.73 (`4,301.91, 4,267.30, 4,305.98`) | 3,924.72 (`3,919.85, 3,926.89, 3,927.43`) | `0.914` (`B/A` pairs `0.911, 0.920, 0.912`) | `<= 0.97` (**pass**) |
| `perf_probe` cold TTFT at `100K` (`102,400`, `ttft_ms`, ms) | 13,708.09 (`13,704.67, 13,714.03, 13,705.58`) | 12,488.78 (`12,477.46, 12,479.87, 12,509.01`) | `0.911` (`B/A` pairs `0.910, 0.910, 0.913`) | `<= 0.97` (**pass**) |
| `perf_probe` cold decode at `100K` (`102,400`, `decode_tokens_s`, tok/s) | 246.79 (`245.54, 246.05, 248.77`) | 240.23 (`250.61, 241.27, 228.80`) | `0.973` (`B/A` pairs `1.021, 0.981, 0.920`) | `>= 0.97` (**pass**) |

| `rtx3090-win-a` metric (`A` = `roles-split24-trimweights-pledirect`, `B` = `roles-split24-trimweights-pledirect-env86g`, seed/nonce `tune029pair`) | Base `A` mean (or blocks `A1, A2, A3`) | Tuned `B` mean (or blocks `B1, B2, B3`) | `B/A` geomean (`[ci95]` and pair ratios) | Pre-registered threshold |
|---|---:|---:|---|---|
| `par_load` `w1` 512/512 `c=1` `agg_tps` (tok/s) | 99.85 | 103.78 | `1.039 [1.033, 1.045]` (`B/A` pairs `1.0446, 1.0327, 1.0408`) | `>= 1.05` (**miss**) |
| `par_load` `w3` 32K (`c=1`) `agg_tps` (tok/s) | 10.43 | 10.59 | `1.015 [1.013, 1.017]` (`B/A` pairs `1.0148, 1.0132, 1.0169`) | — |
| `par_load` `w1` 512/512 `c=1` `ttft_p95` (s) | 1.067 | 1.063 | `0.996` (`A/B` `1.004 [1.002, 1.006]`, `A/B` pairs `1.0064, 1.0028, 1.0015`) | `<= 1.02` (**pass**) |
| `par_load` `w3` 32K (`c=1`) `ttft_p95` (s) | 11.228 | 11.100 | `0.989` (`A/B` `1.012 [1.010, 1.012]`, `A/B` pairs `1.0100, 1.0124, 1.0122`) | `<= 1.02` (**pass**) |
| `perf_probe` cold TTFT at `0` / `8K` / `32K` / `100K` (`ttft_ms`, ms) | 688.62 / 4,793.47 / 10,126.84 / 27,041.64 | 651.71 / 4,707.27 / 10,067.14 / 26,941.32 | `0.948 / 0.982 / 0.994 / 0.996` | `<= 1.02` at every depth (**pass**) |
| `perf_probe` cold decode at `0` / `32K` (`decode_tokens_s`, tok/s) | 146.36 / 167.17 | 154.65 / 182.30 | `1.057 / 1.091` | — |
| `perf_probe` cold decode at `8K` (`8,192`, `decode_tokens_s`, tok/s) | 171.69 (`167.63, 172.82, 174.62`) | 182.78 (`182.19, 180.16, 185.99`) | `1.065` (`B/A` pairs `1.087, 1.042, 1.065`) | `>= 1.03` (**pass**) |
| `perf_probe` cold decode at `100K` (`102,400`, `decode_tokens_s`, tok/s) | 164.23 (`155.35, 170.19, 167.14`) | 182.85 (`188.81, 173.65, 186.10`) | `1.114` (`B/A` pairs `1.215, 1.020, 1.113`) | `>= 1.03` (**pass**) |

- **Greedy identity (`tools/serve_load.py --save/--compare`, `temperature: 0`, 256 tokens, compared against block
  `A1`):** on `rtxpro6000-win-a`, all five sequences per block (`1` single-client plus `4` concurrent) reported
  `compare: ALL IDENTICAL` in `A2`, `A3` and `B1–B3`, so the tuned PRO variant (`parallel_stack` + `gdn_stack` +
  `--kv-streaming off`) produced byte-identical greedy output to the stock `v0.2.9` base in every cold start. On
  `rtx5090-win-a` (single slot, `1` sequence per block), every block reported `compare: 1 DIFFERENT`, including the
  untuned base repeats (`A2` and `B1` first differed from `A1` at character `53`, `A3` and `B3` at character `175`, and
  `B2` at character `241`), so stock greedy output on that Coder IQ1_M lane is not reproducible across cold starts and
  the check cannot attribute a difference to the pins. The single-slot pair behaves the same way: every block,
  including the base repeats, first differed from `A1` (`A2` at character `1,095`, `A3` at `126`, `B1` at `468`, `B2`
  at `340` and `B3` at `84`).
- **RTX 5090 start floor, WSL-up attempt and fallback draft:** pinning `setup_args.kv_streaming: "off"` lowers the
  setup-derived available-RAM start floor on the 262K profile from `36 GiB` to `34 GiB` (stock's non-streaming plan).
  Before stopping Docker Desktop and WSL, a WSL-up start attempt (with only the production container stopped) was refused
  by the `34 GiB` floor at `7.3 GiB` (`7.344 GiB`) available RAM; that check ran while another of the owner's agents
  held host memory (see [Incident](#incident)), so a WSL-up start of the 34 GiB-floor variant remains untested on an
  idle host, and the A/B and requalification chain ran with Docker Desktop and WSL stopped. A fallback draft without the
  `gdn_stack` environment pin
  ([`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0`](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0/qualification.json))
  was prepared for use if `gdn_stack` missed the 100K decode threshold and was never installed.
- **Pair variant (`env86g`): one `w1` A/B miss overridden by the owner, then 14/14 chain pass.** The engine's `sm_86`
  table plus `gdn_stack` raised cold decode at every depth (paired `B/A` `1.057 / 1.065 / 1.091 / 1.114` at
  `0 / 8K / 32K / 100K`; the 100K pairs spread from `1.020` to `1.215`) and kept every time to first token at
  `0.948–0.996`, but the end-to-end `w1` single request (512-token prompt, 512 output tokens) rose only `3.9%` (`99.85`
  to `103.78 tok/s`, every pair below the `1.05` bar; stock `par_analyze.py` labels it `low priority (<5% in every
  pair)`), short of the `+10%` the single-sample `p6` arm showed in the [feature arms](#feature-arms-on-the-v029-roots).
  The window's stop rule stopped after the A/B and kept that miss as the record; the owner then overrode that one bar on
  2026-11-02 (~23:20Z: `"Yes approved: Yes, if you approve an override. There's nothing in the pair profile to fix."`)
  to accept the decode gain and let the real qualification gates decide. The requalification chain ran on 2026-11-03
  (06:45:42–07:27:41Z, tooling `d0a1254`, run `requalify-20261103T064542969683Z`), passed all 14 measured gates
  (`G10–G21`, `G24` 15/18, `G26`), and completed its ledger at `21 pass, 3 not applicable`, making the `env86g` variant
  qualified and current with the `v0.2.9` base profile as its rollback (stated risk: GDN numerics are not bit-exact, and
  the `strata.engine_env` pins need a fresh source review at the next engine release under `ENGINE_ENV_REVIEWED_ENGINES`).

### Requalification chains and the Mac Studio route

All 14 real-host and evaluation gates (`G10–G21`, `G24`, `G26`) passed on all three server variants (`acd7549` on the PRO
and RTX 5090 262K; `d0a1254` on the pair `env86g` variant):

| Tuned profile | Tooling | Measured gates | G24 scored (pilot) | Scored batch wall s (`v0.2.9` base) | G16 / G20 / G21 ready s (`v0.2.9` base) | Against the `v0.2.9` base and notes |
|---|---|---|---|---|---|---|
| [PRO (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0`)](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/qualification.json) | `acd7549` | 14 pass (`21 pass, 3 not applicable`) | 16/18 (5/6) | 631.2 ([576.2](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json)) | 31.0 / 31.0 / 31.3 (35.1 / 35.1 / 39.7) | misses: `tool-loop` x2 (attempts 1, 3; base scored 16/18, base pilot 5/6); G15 post-kill recall `45.4` and `44.7 s` (base `49.4` and `48.7 s`); G17 100K cold prefill `10,699 ms` and near-context-limit task `25.1 s` (base `12,492 ms` and `29.2 s`) |
| [RTX 5090 262K (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0`)](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/qualification.json) | `acd7549` | 14 pass (`21 pass, 3 not applicable`) | 17/18 (5/6) | 791.1 ([840.4](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/qualification.json)) | 18.7 / 18.6 / 18.9 (16.6 / 16.7 / 16.8) | misses: `tool-loop` x1 (attempt 2; base scored 16/18, base pilot 6/6); Docker/WSL stopped; G15 post-kill recall `18.4` and `18.0 s` (base `16.7` and `16.4 s`); G17 100K cold prefill `12,214 ms` and near-context-limit task `30.6 s` (base `13,403 ms` and `35.1 s`) |
| [Pair (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`)](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/qualification.json) | `d0a1254` | 14 pass (`21 pass, 3 not applicable`) | 15/18 (5/6) | 821.8 ([974.9](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json)) | 43.5 / 43.6 / 43.9 (55.4 / 55.5 / 55.6) | misses: `tool-loop` x3 (attempts 1, 2, 3; base scored 15/18 with `tool-loop` x3, base pilot 5/6); G15 post-kill recall `50.1` and `47.1 s` (base `63.5` and `58.9 s`); G17 100K cold prefill `26,582 ms` and near-context-limit task `59.8 s` (base `26,865 ms` and `60.4 s`) |
| [Mac Studio route (`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0`)](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/qualification.json) | `acd7549` | G23 pass | — | — | — | stream TTFT `0.172 s` vs `0.206 s` on the [base route](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/qualification.json); health RTT `5.5–6.3 ms` (base `5.7–8.5 ms`); tunnel reopen (`0.81 s`), client restart (`0.67 s`) and server restart (`1.40 s`) recall all true |

Every G24 miss across all three server chains is a `tool-loop` verifier failure (`0` timeouts, `0` protocol counters, `0`
compactions, and `[0, 0, 0]` exit codes across the three `continuation`-task restart hooks). With the engine serving,
G10 measured **129.57 GiB** (`139,127,558,144 B`, minimum sampled `129.55 GiB`) available RAM and **83.35 GiB**
(`89,497,042,944 B`) Windows commit headroom of a **219.70 GiB** (`235,900,456,960 B`) commit limit on the PRO variant
(versus `112.58 GiB` available RAM and `81.28 GiB` commit headroom on the base, with `74,906 MiB` GPU memory vs
`59,712 MiB`;
[G10](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/evidence/g10-20261102T163204Z-36b598.json)),
and **13.35 GiB** (`14,339,371,008 B`, minimum sampled `13.28 GiB`) available RAM and **20.10 GiB** (`21,584,494,592 B`)
commit headroom of an **85.15 GiB** (`91,434,225,664 B`) commit limit on the RTX 5090 262K variant with Docker Desktop
and WSL stopped (versus `10.55 GiB` available RAM and `17.55 GiB` commit headroom on the base, with `30,742 MiB` GPU
memory vs `30,740 MiB`;
[G10](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/evidence/g10-20261102T162945Z-fcdfc5.json)).
In G19, the automatic conversation cache stayed enabled on both single-GPU variants: **8,192 MiB** on the PRO (34 parks; `20,673`
of `20,702` tokens reused in `367 ms` vs `2,429 ms` cold; lowest available RAM `119.84 GiB` in G18L vs `104.18 GiB` on
the base) and **4,352 MiB** on the RTX 5090 262K variant vs `3,072 MiB` on the base, sized from the host RAM freed by
`--kv-streaming off` (23 parks; `20,672` of `20,701` tokens reused in `291 ms` vs `2,672 ms` cold; lowest available RAM
`8.61 GiB` in G17 vs `6.56 GiB` in G17 on the base, and `8.22 GiB` in G18). In G26, a clean second-root install and
start completed in `21.3 s` and `53.1 s` on the PRO (base `21.4 s` and `56.9 s`) and `12.4 s` and `23.9 s` on the RTX
5090 262K variant (base `10.9 s` and `19.8 s`).

On the pair `env86g` variant (2026-11-03 06:45:42–07:27:41Z, tooling `d0a1254`, run `requalify-20261103T064542969683Z`),
G10 measured **65.68 GiB** available RAM (minimum sampled `65.62 GiB` vs `65.67 GiB` and minimum sampled `65.64 GiB` on
the `v0.2.9` base), **27.77 GiB** Windows commit headroom of a **135.69 GiB** commit limit (base `27.74 / 135.69 GiB`),
and `[22,762, 23,166] MiB` GPU memory on cards `0, 1`, matching `[22,762, 23,166] MiB` on the base
([G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/evidence/g10-20261103T064725Z-46cffc.json),
[base G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/evidence/g10-20261102T095409Z-265da7.json)).
In G19, the automatic conversation cache stayed at **8,192 MiB** (`23` parks vs `20` on the base; kept-conversation `a1`
/ `a2` / `b1` wall `7,899 ms` at `20,678` prompt tokens / `499 ms` at `20,700` / `7,886 ms` at `20,765` vs `7,950 ms` at
`20,679` / `466 ms` at `20,701` / `7,898 ms` at `20,765` on the base;
[G19](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/evidence/g19-20261103T070606Z-4d63c3.json),
[base G19](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/evidence/g19-20261102T101310Z-220cfd.json)),
with minimum available RAM `61.16 GiB` in G17 (base `60.95 GiB`), `57.23 GiB` in G18 (base `57.3 GiB`) and `56.47 GiB`
in G18L (base `56.96 GiB`;
[G18L](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/evidence/g18l-20261103T070110Z-f90383.json)),
G21 current ready `43.9 s` (base `55.6 s`) with `2` engines found dead and restarted during the chain (base `2`;
[G21](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/evidence/g21-20261103T072732Z-3f1551.json)),
G24 success-only attempt walls summing to `684 s` (base `780 s`), and G26 second-root install and start in `29.7 s` and
`70.4 s` (base `25.9 s` and `54.5 s`;
[G26](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/evidence/g26-second-root-20261103T072741Z.json),
[base G26](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/evidence/g26-second-root-20261102T103721Z.json)).
In the root's engine log, `264` of the `275` lines containing `error` read `strata verify: ... (upload no error, sync no
error)` and `11` are the expert-arena `cudaHostRegister limited` notice; the one server-log request ending `(error,
cancel=False)` is G15's mid-generation kill.

On the Mac Studio route to the PRO variant
(`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0`), G23 passed at `acd7549`
([receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/receipts/e433de1953c844e1a8fcd7f3fefe48a0.json),
[evidence](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/evidence/g23-20261102T165927Z.json)):
a missing key was refused before launch, a wrong key returned HTTP 401, health RTT was `5.5–6.3 ms`, stream TTFT
through the SSH local forward was `0.172 s` (vs `0.206 s` on the base route), a tunnel drop failed the turn in flight
with the prior transcript preserved, and nonce recall passed after tunnel reopen (`0.81 s`), client restart (`0.67 s`)
and a verified server restart (`1.40 s`, new server instance).

Operator receipts (`G00` source audit, `G01–G05` from the host-free suite at `d05f660` with `903` tests per lane and
`G06` from `omp-strata` hosted CI run `41499865044` on pull request 73 for the PRO and RTX 5090 variants in `343fab3`;
`G00` source audit, `G01–G05` from the host-free suite at `6b972fa` with `903` tests, `29` skipped, and `G06` from
`omp-strata` hosted CI run `41597184710` on pull request 74 for the pair `env86g` variant in `1f699b4`) together with
not-applicable `G22`, `G23` and `G25` complete all three server ledgers at `21 pass, 3 not applicable`.

### PRO model candidates

| Candidate (`rtxpro6000-win-a`, comparison-only draft) | First visible token s at 8K / 32K / 64K / 100K (warm 32K repeat) | Decode tok/s at 0 / 32K / 100K |
|---|---|---|
| [`UD-IQ4_XS` (`win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0`)](../releases/win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json) | `1.54 / 4.38 / 8.43 / 13.47 (0.45)` | `319.8 / 311.3 / 298.6` |
| [`NVFP4-QAD` stock PLE (`win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0`, hard-disk root)](../releases/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0/qualification.json) | `2.33 / 4.98 / 9.33 / 14.89 (0.49)` | `288.8 / 281.1 / 274.9` |

Following the [earlier PRO model screens](#model-screens-on-the-pro), both candidates were installed, started and
probed with `scripts/perf_probe.py` on `rtxpro6000-win-a`, and their Mac Studio client routes
([`client-rtxpro6000-262k-ud-iq4xs-strata0.2.9-omp18.15.0`](../releases/client-rtxpro6000-262k-ud-iq4xs-strata0.2.9-omp18.15.0/qualification.json),
[`client-rtxpro6000-262k-nvfp4qad-strata0.2.9-omp18.15.0`](../releases/client-rtxpro6000-262k-nvfp4qad-strata0.2.9-omp18.15.0/qualification.json))
each passed an authenticated remote smoke turn (`ROUTE OK`). On `UD-IQ4_XS` (four slots, `--batch-mtp`,
`--ple-io direct`, `74 GiB` available-RAM start floor), stock setup plans every expert resident (`budget` is `None`, no
`--resident-budget-gib`) and writes `STRATA_HC_Q8=1` and `STRATA_ROUTE_TAIL_SKIP=0` (`strata.setup_env`). On
`NVFP4-QAD` (four slots, `--batch-mtp`, `92 GiB` available-RAM start floor, installed on the host's hard-disk data
volume), the draft drops the inherited `--ple-io direct` pin (draft option `--ple-io stock`) so the engine holds the PLE
table in RAM; direct 4 KiB reads from the hard disk tripped the engine's 60 s no-progress watchdog in the
[screen with `--ple-io direct`](#model-screens-on-the-pro).
Both profiles and their routes are comparison subjects only: no qualification gate ran, and their ledgers remain draft.
A frozen 30-task Terminal-Bench 2.1 comparison (first attempt, running `IQ3_S` and then each candidate) is prepared and
has not run.

### Incident

On `rtx5090-win-a`
([restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/restored-state.json)),
this window's fleet reservation at 15:53Z joined a reservation another of the owner's agents had taken at 15:51Z
because the owner's fleet controller does not refuse an existing reservation; this window's WSL-down steps at
16:02–16:03Z then stopped that agent's GPU job. Window scripts now require an unreserved controller phase before
reserving and refuse a joined reservation. The host's production NInfer container was down from 15:51Z / 15:53Z to
17:01Z and was recreated and recommissioned by the owner's procedure.

### Restored state

- **`rtxpro6000-win-a` ([PRO variant restored-state](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0/restored-state.json),
  [route variant restored-state](../releases/client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0/restored-state.json)):**
  before 15:53Z and after 18:21Z, no user was signed in, GPU memory was `433 MiB`, both OCR containers stayed exited as
  found, `180.7 GiB` / `180.5 GiB` RAM was available before / after, and no `omp-strata` process remained.
- **`rtx5090-win-a` ([restored-state](../releases/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0/restored-state.json)):**
  the variant root stopped with `0 MiB` GPU memory and no `omp-strata` process, and the production NInfer container was
  recreated and recommissioned in the `Fleet` controller phase at generation `1` with request admission open,
  authenticated health HTTP `200` and `unless-stopped` restart policy at 17:03Z.
- **`rtx3090-win-a` ([restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0/restored-state.json)):**
  across both the A/B window (`2026-11-02 21:45:45Z–22:24:54Z`) and the requalification chain window (`2026-11-03
  06:44:42Z–07:28:03Z`, with another of the owner's workloads holding the exclusive host lock between them from `22:25Z`
  to `06:44Z`), lead censuses at the start and end of each window under the exclusive host lock found no user session,
  GPU memory at `186 MiB` and `0 MiB`, `120.3–120.4 GiB` available RAM, and no `omp-strata` or other engine process; the
  pair `env86g` variant's integration root stopped after each window.

## Strata v0.2.9 windows (2026-11-02): stock OMP 18.15.0

This section records the 2026-11-02 host measurements for stock Strata `v0.2.9` (tag commit `c62d5e3a`, Windows CUDA 13
engine `0.1.55` build `99866a47a2b8+cuda13.0`) with stock OMP `18.15.0` (`3fedf8d5`) across `rtxpro6000-win-a`,
`rtx5090-win-a`, `rtx3090-win-a` and the Mac Studio route. The owner qualified all four `v0.2.9` server profiles and
the route on 2026-11-02 (`"Push, PR, qualify on green CI"`; hosted CI run 41457827645 on pull request 72), with `v0.2.8`
(engine `0.1.54`) and OMP `18.14.0` as the rollback.

### Owner decisions and host state

The owner's Ask on 2026-11-02 (~05:00Z) selected the tuple `v0.2.9` + `18.15.0` (`"latest stable of both"`), approved
`"Full: A/B + chain + arms + G23"` on `rtxpro6000-win-a`, scheduled the `rtx3090-win-a` pair window before the owner's
queued NInfer job on that host, approved the `rtx5090-win-a` `"Tonight"` window after the owner's NInfer window with
Docker Desktop and WSL stopped and production NInfer downtime authorized, and requested comparison-only model screens
for `UD-IQ4_XS` on the PRO and pair, `NVFP4-QAD` on the PRO, and `DeepSeek V4.1 IST-DAS 2.25` on the PRO.

On `rtxpro6000-win-a`, no user was signed in before or after, the GPU sat at 433 MiB idle (180.2 GiB RAM available
before and after the main window; 180.8 GiB after the model screens), both OCR containers were already exited
(`Exited (0)`) and left as found, every window held the exclusive host lock, and port `18090` was free after stop. On
`rtx5090-win-a`
([262K restored-state](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/restored-state.json),
[131K restored-state](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/restored-state.json)), the host
was reserved through the owner's fleet controller at 06:48Z (`fleet use`), Docker Desktop and WSL were stopped with the
container-host supervisor and encoder tasks disabled (`40.8 GiB` / `40,757 MiB` RAM available), and the production
NInfer container was down 06:48–08:34Z (UTC). Because restarting WSL replaced the production container's bind staging,
`fleet return` at 08:32Z failed closed as before (`return_failed: started service identity changed during readiness`);
the owner's pinned relaunch script recreated the container (healthy after ~12 s at 08:34Z), the stuck controller state
was retired (kept, not deleted), and the running container was commissioned at a new controller generation at 08:38Z
with authenticated health 200 and `unless-stopped` restart policy. On `rtx3090-win-a`
([restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/restored-state.json)),
the window held the exclusive host lock 09:07–11:05Z with no user signed in before or after (empty logon-screen console
sessions were logged off before the A/B and arm blocks, dropping Desktop Window Manager from 1,498 and 1,019 MiB to
294 MiB), GPUs at 180 MiB on the display-attached RTX 4090 and 0 MiB on the RTX 3090 before and 186 / 0 MiB after, and
available RAM at 120.2 GiB before and 120.6 GiB after with no `omp-strata` process remaining.

### Version A/B per host

Each host ran three paired cold-start blocks (`A B B A A B`, where `A` is the `v0.2.8` current root and `B` is the
`v0.2.9` root, with the same seed and nonce) using stock Strata's `tools/par_load.py` + `tools/par_analyze.py` (`w1`:
512-token prompt / 512 output tokens at concurrency `c=1`; `w2`: 1,000-token prompts / 128 output tokens at `c=1, 2, 4`;
`w3`: 32,768-token prompts / 128 output tokens at `c=4` on the 4-slot PRO and `c=1` on the single-slot hosts; `agg_tps`:
aggregate completion tokens/s across concurrent requests; `ttft_p95`: 95th-percentile time to first token; geometric mean
`B/A` and 95% range across the three block pairs) and `scripts/perf_probe.py` (512 output tokens per depth):

| Host and profile pair (`A` = `v0.2.8` current, `B` = `v0.2.9` draft) | Ready s (`A` vs `B`) | `par_analyze` `B/A` geomean `[95% CI]` | `perf_probe` TTFT s at 32K / 100K (`A` vs `B`) | `perf_probe` decode tok/s at 0 / 8K / 100K (`A` vs `B`) |
|---|---|---|---|---|
| `rtxpro6000-win-a` (`slots4-batchmtp-pledirect`, 05:52–06:07Z) | 40.4, 35.3, 35.3 vs 50.4, 50.3, 50.4 (35.2–35.3 s once file-cache-warm) | `w2` 1,000/128 `agg_tps`: `c=1` `0.996 [0.993, 1.001]`, `c=2` `1.005 [0.999, 1.013]`, `c=4` `1.007 [1.002, 1.012]`; `w3` 4 × 32K `agg_tps` `1.012 [0.966, 1.036]`; `ttft_p95`: `w2` `c=1` `0.999 [0.986, 1.022]`, `c=2` `1.068 [0.994, 1.161]`, `c=4` `1.003 [0.983, 1.015]`, `w3` `1.016 [0.969, 1.042]` | 4.10–4.15 / 12.58–12.67 vs 4.12–4.14 / 12.63–12.70 | 331.5–337.2 / 317.0–322.0 / 313.2–318.1 vs 304.3–338.8 / 315.9–325.3 / 311.7–317.0 |
| `rtx5090-win-a` 262K (`coder-iq1m-262k`, Docker/WSL stopped, 07:10–07:22Z) | 25.2, 16.1, 16.1 vs 35.3, 31.7, 30.1 (16.1–20.2 s once file-cache-warm) | `w1` 512/512 `agg_tps` `0.999 [0.997, 1.001]`, `ttft_p95` `0.992 [0.966, 1.013]`; `w3` 32K `agg_tps` `1.001 [0.997, 1.004]`, `ttft_p95` `1.001 [0.997, 1.004]` | 4.28–4.29 / 13.65–13.69 vs 4.28–4.32 / 13.67–13.69 | 255.6–261.3 / 253.7–257.4 / 243.4–250.6 vs 255.3–261.2 / 247.2–259.3 / 229.5–246.3 |
| `rtx3090-win-a` pair (`roles-split24-trimweights-pledirect`, 09:32–09:50Z) | 47.1, 45.1, 45.1 vs 45.1, 45.1, 45.1 | `w1` 512/512 `agg_tps` `1.003 [1.000, 1.008]`, `ttft_p95` `1.002 [0.998, 1.006]`; `w3` 32K `agg_tps` `1.003 [1.001, 1.007]`, `ttft_p95` `1.006 [1.003, 1.008]` | 10.12–10.24 / 27.04–27.35 vs 10.12–10.21 / 27.13–27.39 | 141.0–148.0 / 165.7–173.8 / 167.9–171.4 vs 145.2–148.6 / 167.2–182.7 / 167.0–169.6 |

All three hosts show `par_analyze` aggregate-throughput parity (`0.996–1.012` on the PRO, `0.999–1.001` on the RTX 5090
262K and `1.003` on the pair) and overlapping `perf_probe` TTFT and decode ranges between `v0.2.8` and `v0.2.9`. The
initial ready-time gap on the PRO (`50.3–50.4 s` vs `35.3 s`) and RTX 5090 262K (`30.1–35.3 s` vs `16.1 s`) came from
the freshly installed `v0.2.9` roots' cold Windows file cache rather than engine `0.1.55` and is retracted as a
regression: once file-cache-warm, the same `v0.2.9` PRO root started in `35.1 s` during G16 and G20 and `35.2–35.3 s` on
the subsequent feature-arm baseline starts, and the `v0.2.9` RTX 5090 262K root started in `16.6–16.8 s` across G16, G20
and G21 and `16.1–20.2 s` on its feature-arm baseline starts.

### Server chains (G10–G21, G24, G26) and Studio route G23

The PRO main chain, both RTX 5090 main chains and the Mac Studio route G23 ran at tooling
`6fec79d472f75613407b1da2e2a89a78739dfb60`; the pair main chain ran at `8002c776a318ca3ad1b37165d7903350978b9d7a` after
admitting engine `0.1.55`'s stage order. On the four server ledgers, every automated real-host and evaluation gate
(`G10–G21`, `G24`, `G26`) passed; the operator receipts (`G00` source audit, `G01–G05` from the host-free suite at
`2ccea3c`, `G06` from hosted CI run 41457827645) complete each ledger at 21 pass and 3 not applicable (`G22`, `G23`,
`G25`), and the independent Mac Studio client-route ledger records `G23` `pass`.

| Lane | Tooling | Gates | G24 scored | Pilot | Scored batch wall s (`v0.2.8` predecessor) | `v0.2.8` predecessor G24 (pilot) | Notes |
|---|---|---|---|---|---|---|---|
| [PRO (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0`)](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json) | `6fec79d` | 21 pass, 3 n/a | 16/18 | 5/6 | 576.2 (634.6) | [15/18 (6/6)](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json) | misses: `tool-loop` x2 (attempts 2, 3); 0 timeouts, 0 protocol counters |
| [RTX 5090 262K (`win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0`)](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/qualification.json) | `6fec79d` | 21 pass, 3 n/a | 16/18 | 6/6 | 840.4 (864.9) | [17/18 (6/6)](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/qualification.json) | misses: `tool-loop` x2 (attempts 1, 2); Docker/WSL stopped; 0 timeouts, 0 protocol counters |
| [RTX 5090 131K (`win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`)](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/qualification.json) | `6fec79d` | 21 pass, 3 n/a | 14/18 | 5/6 | 762.5 (967.7) | [18/18 (5/6)](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/qualification.json) | misses: `tool-loop` x3, `bugfix-a` x1 (attempt 2); ran in the Docker/WSL-stopped window; 0 timeouts, 0 protocol counters |
| [Pair (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`)](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/qualification.json) | `8002c77` | 21 pass, 3 n/a | 15/18 | 5/6 | 974.9 (941.7) | [15/18 (5/6)](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json) | misses: `tool-loop` x3; 0 timeouts, 0 protocol counters |
| [Mac Studio route (`client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0`)](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/qualification.json) | `6fec79d` | G23 pass | — | — | — | — | missing key refused, wrong key 401, health RTT 5.7–8.5 ms, stream TTFT 0.206 s, tunnel drop / reopen (0.91 s) / client restart (1.04 s) / server restart (1.51 s) recovery all true |

Every G24 miss across the four server chains is a verifier failure (`0` timeouts, `0` protocol counters, `0`
compactions, continuation restart-hook exit codes `[0, 0, 0]` on all four). With the engine serving, G10 measured
**112.58 GiB** (`120,882,597,888 B`, minimum sampled `112.54 GiB`) available RAM and **81.28 GiB**
(`87,273,160,704 B`) Windows commit headroom of a **219.70 GiB** (`235,900,456,960 B`) commit limit on the PRO
([G10](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0/evidence/g10-20261102T060923Z-719964.json));
**10.55 GiB** (`11,331,670,016 B`) available RAM and **17.55 GiB** (`18,839,920,640 B`) commit headroom of an
**85.15 GiB** (`91,434,225,664 B`) commit limit on the RTX 5090 262K profile with Docker Desktop and WSL stopped
([G10](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0/evidence/g10-20261102T072352Z-dff1f3.json));
**12.03 GiB** (`12,915,441,664 B`) available RAM and **18.78 GiB** (`20,165,021,696 B`) commit headroom of the
**85.15 GiB** (`91,434,225,664 B`) commit limit on the RTX 5090 131K profile in the same Docker/WSL-stopped window
([G10](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0/evidence/g10-20261102T075032Z-4b791b.json));
and **65.67 GiB** (`70,514,458,624 B`) available RAM and **27.74 GiB** (`29,783,396,352 B`) commit headroom of a
**135.69 GiB** (`145,695,096,832 B`) commit limit on the pair
([G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0/evidence/g10-20261102T095409Z-265da7.json)).
In G19, the automatic conversation cache stayed enabled on all four server chains: **8,192 MiB** (28 parks; 20,672 of
20,701 tokens reused in 462 ms vs 2,878 ms cold; restart readiness 35.1 s in G16 and G20 and 39.7 s in G21, lowest
available RAM 104.18 GiB in G18L, G26 install 21.4 s and start 56.9 s in a second root) on the PRO; **3,072 MiB** (21
parks; 20,683 of 20,702 tokens reused in 282 ms vs 2,864 ms cold; restart readiness 16.6–16.8 s across G16/G20/G21,
lowest available RAM 6.56 GiB in G17, G26 install 10.9 s and start 19.8 s) on the RTX 5090 262K; **3,840 MiB** (31
parks; 20,672 of 20,701 tokens reused in 291 ms vs 2,877 ms cold; restart readiness 26.8 s in G16, 16.1 s in G20 and
16.3 s in G21, lowest available RAM 7.52 GiB in G17, G26 install 12.0 s and start 35.4 s) on the RTX 5090 131K; and
**8,192 MiB** (30 parks; 20,682 of 20,701 tokens reused in 466 ms vs 7,950 ms cold; restart readiness 55.4–55.6 s
across G16/G20/G21, lowest available RAM 56.96 GiB in G18L, G26 install 25.9 s and start 54.5 s) on the pair.

On the Mac Studio route, G23 passed at `6fec79d` on 2026-11-02 (07:03–07:06Z,
[receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/receipts/0042355d187c480780d38e7e3ee9b5ee.json),
[evidence](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0/evidence/g23-20261102T070331Z.json)):
a missing key was refused before launch, a wrong key returned HTTP 401, health RTT was 5.7–8.5 ms, stream TTFT through
the SSH local forward was 0.206 s, a tunnel drop failed the turn in flight with the prior transcript preserved, and
nonce recall passed after tunnel reopen (0.91 s), client restart (1.04 s) and a verified server restart (1.51 s, new
server instance). Two earlier G23 attempts failed in the lead's private placement driver (the first before fetching the
pinned client binary on the new client root, and the second because the comparison driver's restart path attempted to
stop an unstaged comparison helper), not in `omp-strata`, and are retained in the lead record.

### Feature arms on the v0.2.9 roots

Each arm cold-started the `v0.2.9` root's own stock server from a temporary configuration copy (`par_load` plus
`scripts/perf_probe.py` at 512 output tokens per depth; single samples bracketed by first and last baseline arms).
Stock `v0.2.9` (`serve/server.py`) turns on the nine-switch parallel-slot stack (`STRATA_CKPT_POOL=1`,
`STRATA_CKPT_POOL_READY=4`, `STRATA_SLOT_CKPT_MOVE=1`, `STRATA_SLOT_COPY_DIRECT=1`, `STRATA_SLOT_COPY_BATCHSYNC=1`,
`STRATA_BATCH_GDN_GROUPS=1`, `STRATA_BATCH_ATTN_ROWS=1`, `STRATA_BATCH_SELF_COMMIT=1`, `STRATA_QSA_SLOTS=1`) and the
GDN tensor-core prompt stack (`STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2`) automatically only on Linux
(`parallel_stack_platform()`). Pinning config `env` entries or `--kv-streaming off` (`--kv-grow`) requires new
`omp-strata` admissions and an owner decision; nothing from these comparison arms is pinned in any profile.

| `rtxpro6000-win-a` arm (`v0.2.9` root, 06:35–06:52Z) | Ready s (avail GiB) | `w2` 1,000/128 agg tok/s (`c=1 / 2 / 4`) | `w3` 4 × 32K agg tok/s (TTFT p50 s) | TTFT s at 0 / 8K / 32K / 100K | Prefill tok/s at 8K / 32K | Decode tok/s at 0 / 8K / 100K (MTP 0 / 100K) |
|---|---|---|---|---|---|---|
| Base (`c0` first, `c6` last) | 35.3 (112.69), 35.2 (112.71) | 116.5 / 110.1 / 114.4, 118.1 / 111.3 / 116.6 | 14.9 (19.31), 15.1 (19.14) | 0.57 / 1.21 / 4.11 / 12.60, 0.56 / 1.22 / 4.12 / 12.66 | 6,883 / 8,066, 6,911 / 8,030 | 332.0 / 313.3 / 317.6 (0.80 / 0.86), 334.2 / 326.6 / 315.5 (0.80 / 0.85) |
| `--kv-streaming off` (`c1`, drop `--kv-resident 32768`) | 30.2 (129.67) | 120.7 / 113.7 / 117.0 | 15.0 (19.05) | 0.55 / 1.17 / 4.05 / 12.27 | 7,108 / 8,182 | 335.0 / 317.8 / 332.9 (0.80 / 0.87) |
| Nine-switch parallel stack via config `env` (`c2`) | 35.2 (112.27) | 128.1 / 133.2 / 149.8 | 15.9 (18.76) | 0.45 / 1.16 / 4.02 / 12.48 | 7,245 / 8,221 | 329.3 / 322.3 / 315.0 (0.79 / 0.84) |
| `--kv-streaming off` + parallel stack (`c3`) | 30.2 (129.23) | 128.1 / 135.0 / 153.6 | 16.9 (17.50) | 0.47 / 1.14 / 3.95 / 12.17 | 7,392 / 8,369 | 334.2 / 334.4 / 328.1 (0.78 / 0.85) |
| GDN (`STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2`, `c4`) | 35.2 (112.71) | 119.8 / 110.8 / 115.8 | 15.5 (18.38) | 0.57 / 1.13 / 3.75 / 11.43 | 7,480 / 8,872 | 329.4 / 307.3 / 313.8 (0.80 / 0.85) |
| All three (`c5`: `--kv-streaming off` + parallel + GDN) | 30.2 (129.24) | 128.5 / 135.8 / 156.2 | 17.3 (17.05) | 0.46 / 1.04 / 3.58 / 10.94 | 8,146 / 9,296 | 346.2 / 326.5 / 334.5 (0.84 / 0.88) |

| `rtx5090-win-a` 262K arm (`v0.2.9` root, 08:15–08:28Z) | Ready s (avail GiB) | `w1` 512/512 agg tok/s (TTFT p50 s) | `w3` 32K agg tok/s (TTFT p50 s) | TTFT s at 0 / 8K / 32K / 100K | Prefill tok/s at 8K / 32K | Decode tok/s at 0 / 8K / 100K (MTP 0 / 100K) |
|---|---|---|---|---|---|---|
| Base (`q0` first, `q6` last) | 20.2 (10.58), 16.1 (10.56) | 164.2 (0.27), 167.4 (0.28) | 23.4 (4.76), 23.3 (4.78) | 0.43 / 1.17 / 4.29 / 13.68, 0.40 / 1.15 / 4.29 / 13.70 | 7,188 / 7,708, 7,188 / 7,689 | 262.9 / 249.8 / 248.5 (0.81 / 0.84), 257.5 / 251.4 / 249.8 (0.79 / 0.84) |
| `--prefill auto:32768` (`q1`) | 16.2 (10.00) | 167.6 (0.27) | 21.9 (5.13) | 0.40 / 1.15 / 4.21 / 13.16 | 7,200 / 7,829 | 261.4 / 249.2 / 233.7 (0.81 / 0.79) |
| `--prefill auto:16384` (`q2`) | 16.1 (10.35) | 167.5 (0.28) | 23.2 (4.82) | 0.40 / 1.16 / 4.19 / 13.32 | 7,183 / 7,859 | 257.9 / 251.5 / 239.3 (0.79 / 0.79) |
| GDN (`STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2`, `q3`) | 15.6 (10.51) | 163.1 (0.28) | 24.8 (4.44) | 0.41 / 1.07 / 3.98 / 12.67 | 7,741 / 8,317 | 257.5 / 259.4 / 227.5 (0.79 / 0.76) |
| `--kv-streaming off` + `--kv-grow` (`q4`, drop `--kv-resident 32768`) | 20.1 (13.83) | 167.0 (0.27) | 23.7 (4.70) | 0.41 / 1.14 / 4.24 / 13.46 | 7,255 / 7,771 | 264.5 / 254.2 / 246.2 (0.81 / 0.82) |
| `--prefill auto:32768` + GDN (`q5`) | 16.1 (10.08) | 165.4 (0.27) | 22.9 (4.85) | 0.39 / 1.09 / 3.91 / 12.26 | 7,736 / 8,428 | 259.8 / 247.2 / 244.6 (0.80 / 0.82) |

| `rtx3090-win-a` pair arm (`v0.2.9` root, 10:38–11:05Z) | Ready s (avail GiB) | `w1` 512/512 agg tok/s (TTFT p50 s) | `w3` 32K agg tok/s (TTFT p50 s) | TTFT s at 0 / 8K / 32K / 100K | Prefill tok/s at 8K / 32K | Decode tok/s at 0 / 8K / 100K (MTP 0 / 100K) |
|---|---|---|---|---|---|---|
| Base (`p0` first, `p7` last) | 55.1 (65.70), 55.1 (65.83) | 97.3 (1.06), 98.7 (1.05) | 10.4 (11.25), 10.4 (11.21) | 0.66 / 4.77 / 10.25 / 27.34, 0.63 / 4.80 / 10.11 / 27.34 | 1,733 / 3,219, 1,718 / 3,259 | 142.7 / 177.7 / 163.8 (0.81 / 0.84), 148.6 / 168.6 / 160.7 (0.85 / 0.80) |
| Engine `sm_86` defaults via config `env` (`p1`) | 55.1 (65.79) | 104.7 (1.05) | 10.5 (11.19) | 0.64 / 4.73 / 10.09 / 27.17 | 1,745 / 3,263 | 151.1 / 182.5 / 183.5 (0.77 / 0.84) |
| `--host-core last` (`p2`) | 55.1 (65.83) | 97.9 (1.04) | 10.6 (10.97) | 0.64 / 4.66 / 9.87 / 26.54 | 1,773 / 3,335 | 145.1 / 167.3 / 170.1 (0.83 / 0.88) |
| `--host-core sibling` (`p3`) | 55.1 (65.82) | 97.8 (1.06) | 10.5 (11.18) | 0.65 / 4.78 / 10.25 / 27.19 | 1,727 / 3,219 | 145.9 / 168.0 / 166.3 (0.80 / 0.85) |
| GDN (`STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2`, `p4`) | 55.1 (65.82) | 102.0 (1.05) | 10.5 (11.11) | 0.65 / 4.72 / 10.00 / 26.92 | 1,746 / 3,293 | 144.4 / 168.1 / 168.4 (0.80 / 0.86) |
| `--prefill auto:32768` (`p5`) | 55.1 (62.94) | 98.7 (1.06) | 6.5 (18.56) | 0.63 / 4.81 / 16.50 / 33.74 | 1,717 / 1,997 | 146.7 / 171.7 / 148.6 (0.82 / 0.78) |
| Engine `sm_86` defaults + GDN (`p6`) | 55.1 (65.83) | 108.0 (1.04) | 10.6 (11.08) | 0.64 / 4.71 / 10.08 / 27.05 | 1,748 / 3,274 | 155.0 / 184.3 / 185.5 (0.81 / 0.86) |

- **On `rtxpro6000-win-a` (base drift 1–2%):** the nine-switch parallel stack (`c2`) raises `w2` aggregate output +30%
  at four concurrent requests (`149.8` vs `114.4–116.6 tok/s`, +20% at `c=2`, +10% at `c=1`); `--kv-streaming off`
  (`c1`, GPU memory `74,830` vs `59,660 MiB`) cuts ready time 14% (`30.2` vs `35.2–35.3 s`) and leaves `+17 GiB` more
  host RAM available at ready (`129.67` vs `112.69–112.71 GiB`); GDN (`c4`) cuts 32K–100K TTFT 9–9.5% and raises
  8K–32K prefill 9–10%; and all three together (`c5`) raise four-concurrent `w2` +35% (`156.2 tok/s`), `4 × 32K` +15%
  (`17.3` vs `14.9–15.1 tok/s`), 32K–100K TTFT −13% (`3.58 / 10.94 s`), prefill +15–18% and decode +4–6%.
- **On `rtx5090-win-a` 262K:** GDN (`q3`) cuts 8K–100K TTFT 7–9% and raises prefill 8%, with 100K decode at
  `227.5 tok/s` vs `248.5–249.8 tok/s` on base (single sample with `0.76` MTP acceptance; needs repeats);
  `--prefill auto:32768` (`q1`) is mixed (100K TTFT −4%, `w3` 32K aggregate −6%, 100K decode −6%) and `auto:16384`
  (`q2`) is marginal; and `--kv-streaming off` with `--kv-grow` (`q4`) leaves `+3.25 GiB` more host RAM available at
  ready (`13.83` vs `10.58 GiB`) at unchanged speed.
- **On `rtx3090-win-a` (pair):** setting the engine's `sm_86` defaults via config `env` (`p1`: `STRATA_ADAPT_NOWAIT=1`,
  `STRATA_ADAPT_LAG=2`, `STRATA_CPU_IQ_ALL_EXACT1=1`, `STRATA_SIDE_MIXER=2`, `STRATA_ATTN_DAILY=1`, `STRATA_GR_UP75=1`,
  `STRATA_GU_SWIGLU=1`, `STRATA_QSA_ROWS=1`, `STRATA_B6_MMVQ_ROWS=1`;
  [Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313)) raises `w1` aggregate throughput +7% and 8K /
  100K decode +8% / +13% (`182.5 / 183.5 tok/s`); `sm_86` + GDN (`p6`) raises `w1` +10% (`108.0 tok/s`) and decode
  +6–14% (`155.0 / 184.3 / 185.5 tok/s`) with TTFT flat; GDN alone (`p4`) trims 32K TTFT ~2%; `--host-core last` (`p2`)
  trims TTFT 2–4% while `--host-core sibling` (`p3`) is flat; and `--prefill auto:32768` (`p5`) loses (32K TTFT `16.50`
  vs `10.11–10.25 s`, `w3` aggregate `6.5` vs `10.4 tok/s`).

### Model screens on the PRO

Four arms of three candidate models were screened on `rtxpro6000-win-a` as comparison-only runs against same-window
IQ3_S baseline brackets (first, candidate, last under the exclusive host lock; rule-4 entry requires 32,768-token decode
$\ge 25\text{ tok/s}$ and three valid tool-turn pairs with median warm turn B $\le 2\times$ the pooled six same-window
IQ3_S warm-turn B observations). The prepared kit's nominal `~110K` cold-TTFT proxy uses `102,400` actual input tokens
and 512 output tokens with zero cached tokens. The pair's `UD-IQ4_XS` screen did not run because of system-drive space.

| Candidate (`rtxpro6000-win-a`, comparison-only) | Serving layout | 32,768-token decode (tok/s) | Cold 32K tool turn A median (s) | Warm 32K tool turn B median (s) | Same-window IQ3_S warm B median (s) | Warm B ratio / allowed bar | 102,400-token cold TTFT (s) | Rule-4 entry |
|---|---|---:|---:|---:|---:|---|---:|---|
| **Qwen3.8-Flash-Next UD-IQ4_XS** | 24,576 experts in VRAM (`55.43 GiB`), `--batch-mtp`, `--ple-io direct` | 273.1 | 4.54 | 1.21 | 1.085 | 1.115× / 2.170 s | 13.38 (IQ3_S 12.77 / 12.66) | **Yes** (two-task quality check 2/2 vs IQ3_S 2/2; aggregate agent wall 179.6 s vs 270.7 s) |
| **DeepSeek V4.1 IST-DAS 2.25** | 9,243 experts in VRAM (`90.08 GB`), 6,117 CPU-lane experts in RAM (`59.4 GB`), DSpark declined | 41.7 | 21.29 | 9.08 | 1.335 | 6.801× / 2.670 s | 31.52 (IQ3_S 12.78 / 12.81) | **No** (warm turn exceeds 2×) |
| **NVFP4-QAD** ([draft profile](../releases/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0/qualification.json)) | 24,576 experts in VRAM (`63.29 GiB`), `--batch-mtp`, `--ple-io direct` on a slow data volume | 55.7 | no tokens (60 s watchdog) | no tokens (60 s watchdog) | 1.120 | no valid pairs (bar 2.240 s) | 14.37 (IQ3_S 12.76 / 12.57) | **Placement-limited** (not a model verdict) |
| **NVFP4-QAD**, same root, configuration copy without `--ple-io direct` | 24,576 experts in VRAM, `--batch-mtp`, stock PLE residency in RAM | 307.4 | 5.11 | 1.96 (1.96 / 1.23 / 1.99) | 1.015 | 1.931× / 2.030 s | 14.12 | **Yes** (two-task quality check 2/2 vs IQ3_S 2/2; ready 458 s from the slow volume with 69.5 GiB available) |

`UD-IQ4_XS` enters rule 4 (`273.1 tok/s` decode at 32K, warm 32K tool turn `1.21 s` vs `1.085 s` on IQ3_S, `1.115×`,
and `2/2` on the paired two-task quality check with zero protocol errors), while `DeepSeek V4.1 IST-DAS 2.25` does not
(`41.7 tok/s` decode at 32K, warm turn `9.08 s` vs `1.335 s`, `6.801×`, `102,400`-token cold TTFT `31.52 s`). On the
`NVFP4-QAD` draft profile (`win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0`), the
first attempt stopped at install (`integrity: NVFP4 conversion recipe changed`) before any serving measurement because
the draft carried `v0.2.3`'s module-wide converter recipe commit (`8183c6b6`, file SHA-256 `7ac34c78…`) instead of
`v0.2.7+`'s `tools/nvfp4_local_pack.py` (recipe commit `0fbbf068`, file SHA-256 `f21bf33b…`). After `2a4aae9` admitted
`0fbbf068` and pinned the recipe per profile, the second attempt completed `install,keygen,start,perf,stop` (`3,758.3 s`)
and the depth probe (`55.7 tok/s` at 32K, `14.37 s` cold TTFT at `102,400` tokens), but every tool-turn request hit the
stock engine's 60 s no-progress watchdog on layer 1 of the prompt chunk with zero generated tokens (`145.73 s` A and
`148.44 s` B elapsed medians are failed-request durations, not valid turn latencies). Because the root sat on the host's
HDD data volume with `--ple-io direct`, where the engine's own startup probe read direct PLE at `295–337 rows/s` (~1 MB/s
random 4 KiB reads), that result is placement-limited rather than a model verdict. The same prepared root then served
from a configuration copy that drops only `--ple-io direct` (stock PLE residency; batch-MTP and four slots kept; the
installed configuration, profile and ledger unchanged): the engine log shows the PLE table held in RAM and no direct-read
probe or watchdog event, 32K decode reached `307.4 tok/s`, and the warm 32K tool turn `1.96 s` against IQ3_S's pooled
`1.015 s` (`1.931×`, 70 ms inside the bar) enters rule 4, with the paired two-task quality check at `2/2` on both
models. Rule 4 admits candidates to Terminal-Bench; it neither qualifies a profile nor replaces IQ3_S.

### Admissions in this tuple

- **`7ea7f12` (setup-planning admission; [UPSTREAM.md](UPSTREAM.md#strata-v029-setup-review-component-engine)):**
  admits stock `v0.2.9`'s changed `if multi:` statement in `setup.py` (`15158c36…`), slicing off the new opt-in
  replica-profile sub-statement (`9f989b69…`) and the updated HIP four-card guard (`71c4fe30…`). The planner evaluates
  the replica guard against the planned args (`replicas=None`, `replica_profile=False`) and `install.scrubbed_env`
  (which strips all `STRATA_*` variables, including `STRATA_REPLICA_PROFILE`), requires false without executing the
  body, and requires the HIP guard evaluated with `replica_done = False` to be false.
- **`2a4aae9` (per-profile NVFP4 conversion recipe pin):** replaces the module-wide NVFP4 converter constant with an
  admitted `commit -> (recipe, requirements)` map pinned on each NVFP4 profile, admits stock `v0.2.7+`'s
  `tools/nvfp4_local_pack.py` at recipe commit `0fbbf068eb7f2e4571e2444a868697e9a2aaa454` (file SHA-256 `f21bf33b…`,
  cached sequential shard reads instead of a process-lifetime `np.memmap`), and selects the pin in the draft generator
  from the release's own converter file SHA-256 (`8183c6b6` on `v0.2.3`, `0fbbf068` on `v0.2.8` and `v0.2.9`).
- **`8002c77` (engine `0.1.55` pair stage-order admission):** admits Windows CUDA 13 engine `0.1.55`
  (`99866a47a2b8+cuda13.0`) on the two-card lane after all six pair A/B starts (three `v0.2.8`, three `v0.2.9`) parsed
  complete (`kept_configured`, RTX 3090 first on layers `0–23` and RTX 4090 last on layers `24–47` at pinned manual
  split `24`), and after source review verified that `gpu_list`, `layer_split_value`, `layer_split_of`, `ordered_gpus`,
  `engine_args`, `parallel_args` and `parse_engine_stage_line` are AST-identical to `v0.2.8` while `child_env` adds
  only the Linux-gated `parallel_stack_env` and `gdn_stack_env` helpers.
- **Campaign, publications, receipts and qualification (`6fec79d`, `b9b4f50`, `63fe4d3`, `c2bbb1c`, `0fd5f64`,
  `0441d01`, `b267979`, `598f6da`, `276bbaa`, `4bb634d`):** `6fec79d` opens `releases/campaigns/v0.2.9.json` and drafts
  the four server profiles and Mac Studio route (`b9b4f50` drafts the NVFP4-QAD screen profile); `63fe4d3`, `c2bbb1c`,
  `0fd5f64` and `0441d01` publish the PRO, Studio route, RTX 5090 and pair chains; `b267979` re-renders
  `docs/COMPATIBILITY.md`; `598f6da` records the RTX 5090 and pair `restored-state.json` files; `276bbaa` adds the
  operator receipts from the host-free suites at `2ccea3c` (`866` tests per lane: `OK (skipped=29)` on the pair,
  `OK (skipped=4)` on each single-GPU lane) and hosted CI run 41457827645; and `4bb634d` qualifies every lane and
  completes the campaign.

## Stock tuning pins on Strata v0.2.8 (2026-10-31): stock OMP 18.14.0

The owner's Asks on 2026-10-31 answered `"Draft, then run pair arms"`, `"run everything on the PRO and approved"`, and
then `"PRO: admit --batch-mtp + requalify"` and `"Pair: admit trim + requalify"`. The tuple is the 2026-10-30 one;
every change is a stock engine or setup option, pinned in a new profile id beside the qualified profiles, which are
unchanged. On `rtxpro6000-win-a` both OCR containers stayed exited as found and nobody was signed in. On
`rtx3090-win-a` the empty console session was logged off before the knob arms (the login-screen desktop held
1,740 MiB of the RTX 4090) and nobody was signed in during the chain. Host windows were serialized with the fleet's
host locks.

### Knob arms on the qualified roots

Each arm cold-started the qualified root's own stock server from a copy of its configuration; no profile, root or
ledger changed. Single samples: an arm counts only where its gain exceeds the drift between the first and last
baseline arms on the same metric and the engine log shows the mechanism. Single requests generate 512 tokens per
depth.

| `rtxpro6000-win-a` single request | Ready s | Time to first token s at 32K / 100K | Decode tok/s at 0 / 8K / 100K |
|---|---|---|---|
| Stock PLE residency (first, last arm) | 72.1, 65.5 | 4.13 / 12.71, 4.10 / 12.73 | 338.5 / 311.1 / 311.2, 323.2 / 305.5 / 306.0 |
| `--ple-io direct` (A/B/B/A) | 40.2, 35.3 | 4.07 / 12.57, 4.09 / 12.60 | 318.6 / 335.5 / 316.1, 317.0 / 311.1 / 313.0 |
| `--spec-min-p 0.70` | 65.4 | 4.17 / 12.72 | 331.6 / 324.9 / 306.7 |

| `rtxpro6000-win-a`, 4 slots | Total output tok/s, 1 × 2K | 2 × 2K | 4 × 2K | Summed decode tok/s, 4 × 40K (MTP acceptance) |
|---|---|---|---|---|
| Stock slots (first, last arm) | 216.3-254.8 | 177.6-179.1 | 220.1-225.0 | 206.7, 202.1 (0.75, 0.78) |
| `--batch-mtp` | 219.7-250.5 | 218.1-219.9 | 238.7-241.6 | 288.6 (0.82) |
| Batch row-kernel environment switches | 217.0-239.6 | 181.8-182.6 | 229.1-229.5 | 207.4 (0.75) |

Total output is completion tokens over wall time, two rounds per cell (one round at 4 × 40K).

| `rtx3090-win-a` | Expert cache GiB, RTX 3090 / RTX 4090 | Time to first token s at 32K / 64K / 100K | Decode tok/s at 60 / 8K / 100K |
|---|---|---|---|
| Stock roles (first, last arm) | 17.35 / 16.01 | 11.4 / 20.4 / 31.7, 11.4 / 20.1 / 31.0 | 144.5 / 169.9 / 168.0, 143.0 / 169.2 / 168.3 |
| `--layer-split 24 --trim-stage-weights` | 19.15 / 17.76 | 10.1 / 17.8 / 27.5 | 155.3 / 168.5 / 171.3 |
| The engine's suggested reserves (1,088 / 1,072 MiB) | 16.97 / 15.65 | 11.6 / 20.7 / 31.9 | 136.6 / 168.0 / 158.9 |
| `--vram-reserve-mib 2560` | 2.70 / 13.77 | 16.8 / 31.0 / 47.1 | 69.1 / 84.0 / 80.5 |
| Split 24 and trim with `--vram-reserve-mib 2560` | 17.33 / 15.94 | 23.6 / 36.4 / 51.6 | 145.5 / 169.5 / 166.1 |
| The engine's sm_86 defaults set in the environment | 17.35 / 16.01 | 11.3 / 20.1 / 31.0 | 159.2 / 178.7 / 186.4 |
| `--spec-min-p 0.70` | 17.35 / 16.01 | 11.2 / 20.0 / 31.1 | 140.9 / 168.0 / 163.0 |

- **PLE direct reads count on the PRO.** Every rate stays inside the residency arms' spread; the server is ready about
  30 s sooner because the per-layer embedding table is no longer read into locked RAM at start.
- **Per-slot MTP counts on the PRO.** Without it, two concurrent requests deliver less in total than one alone.
  Stock's own app turns `--batch-mtp` on for a single card of 24 GB or more with two or more slots
  (`apps/host/server/native-parallel.mjs`); stock setup never writes it. Admitted as `strata.batch_mtp`.
- **Stage weight trim counts on the pair.** Each card loads only its own layers' dense weights (771 and 988 MiB
  instead of 1,466 and 2,019 MiB), so each expert cache grows by about 1.8 GiB; decode is flat at 8K and 100K. Under
  the automatic split, engine `0.1.54` trims only later stages, so the profile pins stock setup's manual split point at
  the layer the automatic planner chose (24) beside the stock roles. Admitted as `strata.trim_stage_weights` and roles
  with a manual split point.
- **The sm_86 defaults would count, but cannot be pinned.** Decode rises 5-11% with prompts unchanged, yet the
  engine skips its sm_86 defaults on a host that mixes 8.6 and 8.9 cards, and multi-GPU profiles refuse environment
  settings. The numbers went to [Niko1221/Strata#3313](https://github.com/Niko1221/Strata/issues/3313).
- **Reserves lose.** With a 2,560 MiB reserve the automatic planner moved the split point from layer 24 to layer 3
  (the RTX 3090's expert cache fell to 2.70 GiB) and decode halved. Combined with the trim, layer-major prefill engaged
  at 32K and up ("R in pinned RAM", 3.4-7.1 GB of expert blobs streamed per prompt) and doubled time to first token; on
  this pair the engine's fallback when no VRAM fits a super-chunk is the faster path. A logged-off console session did
  not change the RTX 4090's 396 MiB free at load.
- `--spec-min-p 0.70` is within noise on the PRO and 2-3% slower on the pair.

### Draft requalification chains

| Draft profile | Tooling | Measured gates | G24 scored (pilot) | G16 / G20 restart ready s | Against the qualified profile |
|---|---|---|---|---|---|
| [PRO PLE direct](../releases/win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json) | `2ae400d` | 14 pass | 15/18 (6/6) | 51.4 / 35.0 | 85.6 / 88.2; G15 kill recall 49.5 and 49.2 s against 92.5 and 84.9 s |
| [PRO per-slot MTP + PLE direct](../releases/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json) | `d594b5f` | 14 pass | 15/18 (6/6) | 51.4 / 51.5 | G15 kill recall 49.9 and 50.6 s |
| [Pair roles, split 24, trim + PLE direct](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json) | `d594b5f` | 14 pass | 15/18 (5/6) | 43.1 / 44.2 | 43.7 / 44.2; G17 near-limit task 60.8 s against 67.0 s |

Every G24 miss is tool-loop's exact-money assertion, as on the qualified profiles. The first PLE-direct chain, at
`a92801a`, stopped at start before any gate (`strata.ple_io: 'engine_log'`: the lifecycle captured the engine log
only for multi-card starts); `2ae400d` fixed it with a regression test, and a start and G10 probe passed before the
full chain. G00-G06 (source audit, the host-free suite at `681d504` and hosted CI run 41224900293) and the
not-applicable G22, G23 and G25 complete each ledger at 21 pass and 3 not applicable; the drafts stay unqualified until
the owner decides.

## Strata v0.2.8 windows (2026-10-30): stock OMP 18.14.0

The owner approved the host windows and qualification decisions on 2026-10-30
([DECISION.md](DECISION.md#update-2026-10-30-strata-v028-with-omp-18140-qualifies-on-every-host-and-the-studio-route-the-rtx-5090-262k-profile-becomes-its-default)):
window Asks answered `"Run now, leave OCR as found"` on the PRO, `"131K + 262K with Docker/WSL down"` on the RTX 5090,
`"Sign out now: both variants, then the main chain"` on the pair, and `"Run the diagnostic now"` for the RTX 5090 G10
listener diagnostic; qualification Asks answered `"PRO, 5090 131K, pair, route"` and, for the RTX 5090 262K profile,
`"Let's make it the default we want the bgiger context"`. On `rtxpro6000-win-a`
([restored-state](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/restored-state.json),
[route restored-state](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/restored-state.json)), both OCR
containers were already exited and left as found, the console session was signed out before and after, and the
fleet-managed Strata lane was not running and untouched. On `rtx3090-win-a`
([restored-state](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/restored-state.json)),
the owner's console session was signed out at window start with his consent, and the host ended with no user session
and GPUs at 185 MiB on the display-attached RTX 4090 and 0 MiB on the RTX 3090. On `rtx5090-win-a`
([262K restored-state](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/restored-state.json),
[131K restored-state](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/restored-state.json)), the
production NInfer container was down 01:24–02:40Z, 02:49–02:56Z, 03:13–03:24Z and 03:32–03:39Z (UTC, 2026-10-30):
both Docker/WSL-down windows (01:24–02:40Z for the 131K and 262K main chains, and 03:32–03:39Z for the 262K G10 rerun)
ended with the container recreated by the owner's pinned relaunch script and re-registered with the fleet controller
(stuck controller state retired, kept), while the two WSL-up windows (02:49–02:56Z G10 listener diagnostic and
03:13–03:24Z 131K G10 rerun) returned the same container, with authenticated health 200 after each. All four `v0.2.8`
server profiles (PRO, RTX 5090 262K default and 131K alternative, pair PLE-direct) and the Mac Studio route are
qualified, rolling back to `v0.2.7` + OMP `18.13.2`; the `v0.2.8` stock-residency pair draft stays measurement-only.

### Server chains (G10–G21, G24, G26) and Studio route G23

The PRO main run and the RTX 5090 131K and 262K main runs used tooling `278e53c7f04922b52c3cad907dcd81de8297f6e0`;
the pair PLE-direct main run and the Studio route G23 used `4853ab3f03639fe9c90adb589becaab7a6eaa8f2` after admitting
engine `0.1.54`'s stage order; and the RTX 5090 131K and 262K G10 reruns used
`f9e8c74f48a6cf6ea471e5ce3fe8ab539ce91074` after fixing G10's listener check for Windows build 26300.9818. Each run
is published separately, main first and rerun last; failed receipts remain in the ledger.

| Lane | Gates | G24 | Pilot | `v0.2.7` G24 | Notes |
|---|---|---|---|---|---|
| PRO (`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0`) | 21 pass, 3 n/a | 16/18 | 5/6 | 15/18 | misses: tool-loop x2; batch wall 788.171 s (`v0.2.7`: 827.758 s); tooling `278e53c` |
| RTX 5090 262K **default** (`win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0`) | 21 pass, 3 n/a | 17/18 | 6/6 | 16/18 | miss: tool-loop x1; batch wall 864.890 s (`v0.2.7`: 755.239 s); main chain `278e53c` (G10 failed there), G10 rerun pass `f9e8c74` (Docker/WSL stopped) |
| RTX 5090 131K alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`) | 21 pass, 3 n/a | 18/18 | 5/6 | 16/18 | all six tasks 3/3; batch wall 967.658 s (`v0.2.7`: 731.838 s); main chain `278e53c` (G10 failed there), G10 rerun pass `f9e8c74` (Docker/WSL running) |
| Pair PLE-direct (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`) | 21 pass, 3 n/a | 15/18 | 5/6 | 17/18 | misses: tool-loop x3; batch wall 926.029 s (`v0.2.7`: 1,029.479 s); chain `4853ab3` after the stage-order admission |
| Route G23 (`client-rtxpro6000-262k-strata0.2.8-omp18.14.0`) | pass | — | — | — | missing key refused, wrong key 401, health RTT 6.1–6.7 ms, TTFT 0.199 s, tunnel drop / restart recovery all true (`4853ab3`) |

With the engine serving, G10 measured **86.95 GiB** (`93,365,739,520 B`) available RAM and **55.37 GiB**
(`59,451,871,232 B`) Windows commit headroom of a **219.70 GiB** (`235,900,456,960 B`) commit limit on the PRO
([G10](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/evidence/g10-20261030T014407Z-c4dbce.json));
**11.17 GiB** (`11,990,355,968 B`) available RAM and **18.05 GiB** (`19,380,273,152 B`) commit headroom of an
**85.15 GiB** (`91,434,225,664 B`) commit limit on the RTX 5090 262K G10 rerun with Docker Desktop and WSL stopped
([G10](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/evidence/g10-20261030T033442Z-92efcf.json));
**6.63 GiB** (`7,120,748,544 B`) available RAM and **13.22 GiB** (`14,191,951,872 B`) commit headroom on the RTX 5090
131K G10 rerun with Docker Desktop and WSL running
([G10](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/evidence/g10-20261030T032320Z-cd9473.json);
12.66 GiB available RAM and 19.68 GiB commit headroom in the failed main-chain G10 with Docker Desktop and WSL stopped); and **65.45 GiB**
(`70,280,802,304 B`) available RAM and **27.92 GiB** (`29,983,637,504 B`) commit headroom of a **135.69 GiB**
(`145,695,096,832 B`) commit limit on the pair PLE-direct profile
([G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/evidence/g10-20261030T021051Z-bf9c99.json)).
In G19, the automatic conversation cache was enabled on all four server runs: **8,192 MiB** (26 parks; 20,671 of
20,700 tokens reused in 436 ms vs 2,993 ms cold; 48 uncached tokens on the controlled continuation; restart readiness
73.6–88.2 s across G16/G20/G21, G26 install 1,053.3 s and start 97.6 s in a new root) on the PRO; **3,584 MiB** (31
parks; 20,673 of 20,702 tokens reused in 300 ms vs 2,904 ms cold; 48 uncached tokens; restart readiness 17.1–28.3 s,
lowest available RAM 9.79 GiB in G16, G26 install 365.6 s and start 38.4 s in a new root) on the RTX 5090 262K default
with Docker Desktop and WSL stopped; **4,096 MiB** (21 parks in the Docker/WSL-stopped main chain; 20,682 of 20,701
tokens reused in 261 ms vs 2,891 ms cold; 47 uncached tokens; restart readiness 16.6–27.2 s, lowest available RAM
11.47 GiB in G16, G26 install 297.8 s and start 38.5 s in a new root) on the RTX 5090 131K alternative; and
**8,192 MiB** (28 parks; 20,672 of 20,701 tokens reused in 498 ms vs 8,891 ms cold; 48 uncached tokens; restart
readiness 43.7–44.4 s, lowest available RAM 64.42 GiB in G16, G26 install 27.1 s and start 70.4 s on the already
prepared root) on the pair PLE-direct profile.

The [PRO](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/qualification.json) and
[pair PLE-direct](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json)
operator receipts bind their host-free reports to `4853ab3` (833 tests, 4 skips on the PRO and 29 skips on the pair;
G00 at `278e53c`, G06 citing green PR #69
[CI run 40989725083](https://github.com/alphastorm/omp-strata/actions/runs/40989725083) at `4853ab3`). The
[RTX 5090 262K default](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/qualification.json) and
[RTX 5090 131K alternative](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/qualification.json)
operator receipts bind their host-free reports to `f9e8c74` (835 tests, 4 skips; G00 at `278e53c`, G06 citing green
[CI run 40996143852](https://github.com/alphastorm/omp-strata/actions/runs/40996143852) at `f9e8c74`). On the Mac
Studio client, the independent
[`client-rtxpro6000-262k-strata0.2.8-omp18.14.0` ledger](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/qualification.json)
passed G23 on 2026-10-30 at `4853ab3`
([receipt](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/receipts/e0d2532492834f928703268e14bdd7b9.json)):
missing key refused before launch, wrong key 401, health RTT 6.1–6.7 ms, stream TTFT 0.199 s, tunnel drop failing the
turn in flight with the prior transcript preserved, and nonce recall passing after tunnel reopen (0.85 s), client
restart (0.75 s) and verified server restart (1.65 s, changed server instance).

### RTX 4090 + RTX 3090: stage order and Strata#4518 on engine 0.1.54

The roles PLE-direct draft and the roles draft with stock PLE residency each ran install → start → perf → stop in a
new root (tooling `278e53c`), the owner's console session signed out at his choice. `perf_probe` restarts the server
before it measures, so each draft has two starts; all four parsed complete with the reviewed parsers: configured and
staged order RTX 3090 then RTX 4090, layers 0-23 / 24-47 (auto K=24, as `v0.2.7`), expert caches 17.35 / 16.01 GiB
(the RTX 3090's cache is 0.25 GiB smaller than on `v0.2.7`: the automatic cache now also leaves 256 MiB for what is
allocated after it, Strata#4474).

| Prompt | Decode tokens/s (PLE direct / stock residency) | Prompt reading tokens/s | TTFT s |
|---|---|---|---|
| ~60 tokens | 141.4 / 146.7 | — | 0.9 / 0.8 |
| 8,192 | 166.2 / 165.8 | 1,493 / 1,535 | 5.5 / 5.4 |
| 32,768 | 167.7 / 173.8 | 2,902 / 2,906 | 11.4 / 11.4 |
| 32,768 repeated | 167.7 / 169.7 | reused | 0.5 / 0.4 |
| 65,536 | 162.3 / 173.4 | 3,253 / 3,285 | 20.3 / 20.1 |
| 102,400 | 169.0 / 171.7 | 3,293 / 3,324 | 31.2 / 30.9 |

The PLE-direct draft logs `PLE direct read probe: 88,041` and `112,342 rows/s (fine)`, no residency-policy line, and
an 8,192 MiB automatic conversation cache on both starts (61-63 s to ready). With stock residency the engine's policy
locks the 26.8 GiB table (33.9-34.0 s), then Strata#4518's fix gives the lock back on both starts ("the lock left 0.9
GiB of RAM for the conversation cache, 14.7-14.8 GiB without it"), and the cache comes back at 4,864 MiB (106-112 s
to ready). On `v0.2.7` the same draft kept the lock and left the cache off. Windows commit headroom was not measured
in these runs (G10 measures it). Single samples.

### RTX 5090: G10's listener check on Windows build 26300.9818

Both RTX 5090 main chains (131K and 262K, tooling `278e53c`, Docker Desktop and WSL stopped) passed every gate but
G10, which read an unowned listener on 127.0.0.1:18090 (131K: an owned and an unowned row; 262K: only an unowned
row) while the server answered every request. The host had installed the Windows 11 2026-10 preview update
(build 26300.9818) on 2026-10-29; the PRO and pair hosts run 26300.9711 and passed. On the RTX 5090 host a plain
`ThreadingHTTPServer` (Strata's server class shape) reproduced it without Strata: after a few loopback requests,
netstat stopped listing the serving listener (0 of 20 checks) and printed closing connections as LISTENING rows owned
by PID 0, while `GetExtendedTcpTable`'s listener class still returned the listener with its real owner (20 of 20),
only with its state reported as FIN_WAIT1. G10 now reads that listener table (`f9e8c74`); ownership and loopback
rules are unchanged. The 131K G10 rerun with Docker Desktop and WSL running passed (`start,g10,stop`, owned listener
`127.0.0.1:18090`,
[`g10-20261030T032320Z-cd9473`](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/receipts/g10-20261030T032320Z-cd9473.json)),
and the 262K G10 rerun with Docker Desktop and WSL stopped again for its 36 GiB start floor also passed (`start,g10,stop`,
owned listener `127.0.0.1:18090`,
[`g10-20261030T033442Z-92efcf`](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/receipts/g10-20261030T033442Z-92efcf.json));
both failed main-chain G10 receipts remain in the ledgers, and the owner made the 262K profile the RTX 5090 default.

## Strata v0.2.7 windows (2026-10-28): stock OMP 18.13.2

Under the owner's 2026-10-28 overnight fleet authorization and afternoon qualification decisions
([DECISION.md](DECISION.md#update-2026-10-28-afternoon-the-pairs-ple-direct-and-rtx-5090-262k-strata-v027-profiles-qualify)),
the morning RTX 5090 window reserved the production NInfer container at 08:20Z and restored the same container at
10:19Z (authenticated health 200, GPU 30.4 GB) after signing out the disconnected console session; on the PRO, both
OCR containers were already exited and stayed as found while the console was signed out; the pair had no user
session before or after and ended the morning window at 180 MiB on the display-attached RTX 4090 and 0 MiB on the
RTX 3090. In the afternoon windows, the RTX 5090 262K opt-in reran from 17:04–17:30Z with the host's Docker Desktop
and WSL stopped (reserved 17:01Z; after WSL restarted, the production NInfer container was recreated with the same
image and configuration, returning authenticated health 200 at 18:22Z), and the pair's new PLE-direct profile
(`--ple-io direct`) ran from 18:35–19:22Z on a fresh root, ending stopped at 185 MiB on the display-attached RTX
4090 and 0 MiB on the RTX 3090. All four `v0.2.7` server profiles (PRO, RTX 5090 131K default and 262K opt-in, pair
PLE-direct) and the Mac Studio route are qualified, rolling back to `v0.2.3` + OMP `18.12.6`; the pair's `v0.2.7`
roles profile (PLE in RAM) stays a held draft on measured commit headroom, and the pair default split stays
unmeasured.

### Server chains (G10–G21, G24, G26) and Studio route G23

The RTX 5090 131K main run used tooling `2e50d9aec66e14b6ed17697e901c868e4e2f7941`; its G15-only rerun, the PRO
main run and the failed morning RTX 5090 262K run used `9d3cf88a59b45f00449fbbe7019241e93be3d1a5`; the held pair
stock-roles main run and the Studio route G23 used `15c742615207e4f8ce888991f852728e57e1a88a` after admitting
engine `0.1.52`'s stage order; the afternoon RTX 5090 262K rerun with Docker Desktop and WSL stopped used
`1914e845ab29a35e73afe67d108def5ee10e58db`; and the afternoon pair PLE-direct main run used
`7f7b16d93df53723f46b2bf2dd5e8fbc58aedef8` (operator receipts at `8c1ae59081af148215222a7209ddf0b3e0f84b89`).
Each run is published separately, main first and rerun last; failed receipts remain in the ledger. Chain wall below
spans the first install through the final stop, including status checks, faults, the non-scored pilot and scored
evaluation.

| Profile | Run / window | Chain wall / UTC window | Measured gate outcome | G24 scored / pilot |
|---|---|---|---|---|
| PRO, IQ3_S 262K, four slots (current) | `requalify-20261028T093338862113Z` | 2,304 s | All 14 measured gates pass. | 15/18, 5/6 |
| RTX 5090, Coder IQ1_M 131K (current default) | `requalify-20261028T085732948096Z` | 1,523 s | G15 fails in the main run; G15-only `requalify-20261028T095316695182Z` passes. The other 13 measured gates pass. | 16/18, 5/6 |
| RTX 5090, Coder IQ1_M 262K opt-in (current opt-in) | morning `requalify-20261028T092946188481Z`; afternoon rerun 17:04–17:30Z | 1,410 s (morning); 17:04–17:30Z (rerun) | Morning run with resident VM: G15/G16 fail, then G17–G21 and G26 fail after refused restarts (G10–G14 pass; G24 0/18). Afternoon rerun with Docker Desktop/WSL stopped: all 14 measured gates pass; morning failures stay in the ledger. | 16/18, 5/6 (morning 0/18, 0/6) |
| RTX 4090 + RTX 3090, stock roles + PLE direct (current) | 18:35–19:22Z | 18:35–19:22Z window | All 14 measured gates pass on a fresh root (`--ple-io direct`). | 17/18, 5/6 |
| RTX 4090 + RTX 3090, stock roles (PLE in RAM, held draft) | `requalify-20261028T101905772830Z` | 3,374 s | All 14 measured gates pass (`status-before-g16` observed the post-G15 degraded stage-order state and `restart-before-g16` restored readiness before G16 ran); held on 1.03 GiB G10 commit headroom and cache off. | 13/18, 6/6 |

The 131K main G15 recorded a thinking-loop stop on the first post-interruption recall and no nonce in its
client-abort control. Its separate passing rerun is
[g15-20261028T095338Z-abb828](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2/receipts/g15-20261028T095338Z-abb828.json);
that newer observation does not erase the failure. In the morning 262K run with the resident Docker Desktop/WSL VM
in place (35.7–36.2 GiB available RAM), G15 did not interrupt an active generation (`was_generating: false`,
`cut_turn_not_completed: false`) and G16 recorded `only 35.8 GiB RAM available; the profile needs 36 GiB at start`,
after which every restart refused with exit 4. In the afternoon rerun on the same root with Docker Desktop and WSL
stopped (39.8 GiB available RAM against the unchanged 36 GiB floor; details in the
[262K rerun section below](#rtx-5090-262k-opt-in-afternoon-rerun-2026-10-28-docker-desktop-and-wsl-stopped)), every
measured gate passed while the morning failed receipts remained in the ledger.

On the PRO, engine `0.1.52`'s 8,192 MiB automatic conversation cache stayed enabled and G19's kept-conversation
probe reused 20,672 of 20,701 prompt tokens (454 ms vs 2,992 ms cold; 48 uncached tokens on the controlled
interleaved continuation; restart readiness 80.2–94.3 s across G16/G20/G21, G26 start 107.2 s and install 26.6 s on
the already prepared root). On the current pair PLE-direct run (`--ple-io direct`; restart readiness 56.8–57.0 s,
G26 start 54.9 s and install 25.6 s on the already prepared root; details in the
[pair PLE-direct section below](#pair-ple-direct-qualification-run-2026-10-28-afternoon-current)), keeping the
26.8 GiB PLE table on direct SSD reads left the 8,192 MiB automatic conversation cache enabled on every start (20
parks in G19; 20,673 of 20,702 tokens reused in 514 ms vs 8,833 ms cold, 46 uncached tokens on the controlled
continuation) and kept 27.3 GiB Windows commit headroom in G10. On the held pair roles run (restart readiness
89.8–93.1 s, G26 start 101.9 s and install 29.2 s on the already prepared root), engine `0.1.52` locked the
26.8 GiB PLE table in RAM and left its automatic conversation cache off (`enabled: false`, `budget_mib: 0`); G19
followed `/metrics` and verified transcript preservation with live prefix reuse only (7,498 reused system-prefix
tokens and 279 uncached tokens on the controlled A continuation), as on the RTX 5090 131K run with the resident
Docker Desktop/WSL VM (`enabled: false`, `budget_mib: 0`, 7,500 reused and 300 uncached tokens; restart readiness
18.7–28.4 s, G26 start 42.5 s and install 10.9 s on the already prepared root). On the RTX 5090 262K afternoon
rerun with Docker Desktop and WSL stopped (restart readiness 16.1–16.9 s, G16 16.7 s; G26 start 31.5 s and install
10.8 s on the already prepared root), the engine enabled a 1,792 MiB automatic conversation cache (16 parks in G19;
20,672 of 20,701 tokens reused in 305 ms vs 2,880 ms cold, 47 uncached tokens on the controlled continuation).

| Scored task / boundary | PRO `v0.2.3` → `v0.2.7` | RTX 5090 131K `v0.2.3` → `v0.2.7` | RTX 5090 262K `v0.2.3` → `v0.2.7` | Pair roles `v0.2.3` → `v0.2.7` PLE-direct (held roles draft) |
|---|---|---|---|---|
| Bugfix-a, long-context, continuation | 3/3 each → 3/3 each | 3/3 each → 3/3 each | 3/3 each → 3/3 each | 3/3 each → 3/3 each (3/3 each) |
| Bugfix-b | 3/3 → 3/3 | 3/3 → 3/3 | 3/3 → 3/3 | 2/3 → 3/3 (3/3) |
| Multifile-regression | 3/3 → 3/3 | 3/3 → 3/3 | 2/3 → 3/3 | 3/3 → 3/3 (1/3) |
| Tool-loop | 2/3 → 0/3 | 2/3 → 1/3 | 0/3 → 1/3 | 0/3 → 2/3 (0/3) |
| Total independently verified scored passes | **17/18 → 15/18** | **17/18 → 16/18** | **14/18 → 16/18** | **14/18 → 17/18** (13/18) |
| Non-scored pilot | 5/6 → 5/6 | 6/6 → 5/6 | 6/6 → 5/6 | 5/6 → 5/6 (6/6) |
| Scored batch wall, including failures | 578.257 s → 827.758 s | 847.457 s → 731.838 s | 831.269 s → 755.239 s | 1,182.885 s → 1,029.479 s (1,194.349 s) |

Unsuccessful scored attempts stay in the denominator, with zero scored timeouts and zero protocol counters
(including `malformed_arguments` and `calls_without_results`) on all four qualified `v0.2.7` server profiles and on
the held pair roles draft. Both the stock engine defaults and OMP's Qwen3.8 edit surface (`replace` in `18.13.2`
instead of `hashline`) changed, so these bounded batches do not isolate a cause or establish a performance
comparison. The morning 262K run exported all 18 client-failure attempts (batch wall 595.639 s); its G24 receipt
stays in the ledger beside the passing afternoon rerun.

The [PRO](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2/qualification.json),
[RTX 5090 131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2/qualification.json) and
[held pair roles](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2/qualification.json)
operator receipts bind each clean-worktree host-free report to `9d3cf88`: 818 tests, 4 skips (233.385 s) on the
PRO, 4 skips (234.096 s) on the RTX 5090 131K, and 29 skips (154.040 s) on the held pair roles draft, with G00 at
`fd645b6` and G06 citing green PR #66
[CI run 40663594440](https://github.com/alphastorm/omp-strata/actions/runs/40663594440) at `9d3cf88`. The
[RTX 5090 262K opt-in](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/qualification.json)
operator receipts bind its host-free report to `1914e84` (818 tests, 4 skips; G00 at `fd645b6`), and the
[pair PLE-direct](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/qualification.json)
operator receipts bind its host-free report to `8c1ae59` (827 tests, 29 skips, no failures in 162.442 s); both G06
receipts cite green PR #68
[CI run 40745659264](https://github.com/alphastorm/omp-strata/actions/runs/40745659264) at `f3ba668`. All four
current server ledgers (and the held pair roles ledger) have **21 pass, 3 not applicable** (G22, G23 and G25), with
no missing gates; the unmeasured
[pair default-split ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.7-omp18.13.2/qualification.json)
has 24 not run.

On the Mac Studio client, the independent
[`client-rtxpro6000-262k-strata0.2.7-omp18.13.2` ledger](../releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/qualification.json)
passed G23 on 2026-10-28 at `15c7426`
([receipt](../releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/receipts/b394c29467ac49548f14c1abecf29c0a.json),
[evidence](../releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/evidence/g23-20261028T102244Z.json)): a
missing key was refused before launch, a wrong key returned HTTP 401, health RTT was 8.0–41.4 ms (11.2, 8.0 and
41.4 ms) and stream TTFT through the tunnel 0.316 s; a tunnel drop failed the turn in flight with the prior
transcript preserved; and nonce recall passed from transcript replay after reopening the tunnel (1.04 s),
restarting the client (0.78 s) and a verified server restart (1.60 s, changed server instance).

### Single-sample A/B speed and PLE residency measurements (PRO, RTX 5090, pair)

All tables below are single-sample `scripts/perf_probe.py` runs (512 output tokens per depth, server timings for
prefill and decode tokens/s, monotonic client wall for TTFT s), run back to back per host on 2026-10-28.
Comparison arms that pass `STRATA_PLE_AUTO_RAM=0` (keeping direct PLE reads) or `STRATA_DEFAULTS=026` (selecting
Strata `v0.2.6` stock engine defaults) are throwaway measurement starts only; `omp-strata` profiles scrub inherited
`STRATA_*` variables and cannot pin environment overrides.

#### RTX PRO 6000: `v0.2.3` vs `v0.2.7` stock defaults and knob arms

On `rtxpro6000-win-a` (192 GB RAM, driver 616.92), engine `0.1.52`'s residency policy chooses `--ple-io ram` (26.8 GiB
PLE table, 46.8 GiB expert arena, 176.2 GiB RAM available) and locks the table in RAM in 33.1 s (`ready_s` 70.4 s on
`k-pro-027` and 70.3 s on `k-pro-027-repeat`, vs 40.2 s on `v0.2.3`, 40.2 s with `STRATA_PLE_AUTO_RAM=0`, and 35.2 s
with `STRATA_DEFAULTS=026`), while keeping the 8,192 MiB automatic conversation cache enabled.

| Depth (tokens) | `k-pro-023` TTFT s / prefill t/s / decode t/s | `k-pro-027` TTFT s / prefill t/s / decode t/s | `k-pro-027-pleauto0` TTFT s / prefill t/s / decode t/s | `k-pro-027-defaults026` TTFT s / prefill t/s / decode t/s | `k-pro-027-repeat` TTFT s / prefill t/s / decode t/s |
|---|---|---|---|---|---|
| `unique_prefix` 61 | 0.20 / 344 / 290.3 | 0.20 / 344 / 325.6 | 0.23 / 289 / 324.1 | 0.21 / 313 / 307.6 | 0.19 / 343 / 339.5 |
| `unique_prefix` 8192 | 1.63 / 5089 / 306.9 | 1.65 / 5026 / 319.4 | 1.58 / 5256 / 318.4 | 1.58 / 5255 / 314.7 | 1.60 / 5171 / 329.3 |
| `unique_prefix` 32768 | 4.09 / 8095 / 314.6 | 4.18 / 7945 / 323.5 | 4.11 / 8060 / 314.1 | 4.18 / 7921 / 321.8 | 4.21 / 7865 / 301.8 |
| `warm_repeat` 32768 | 0.31 / 25 / 320.6 | 0.52 / 14 / 331.2 | 0.52 / 14 / 317.0 | 0.51 / 15 / 327.4 | 0.52 / 14 / 310.3 |
| `unique_prefix` 65536 | 8.02 / 8255 / 313.5 | 8.31 / 7964 / 298.9 | 8.07 / 8189 / 283.5 | 8.26 / 8001 / 286.2 | 8.31 / 7954 / 305.2 |
| `unique_prefix` 102400 | 12.84 / 8033 / 313.6 | 13.23 / 7800 / 316.8 | 13.11 / 7873 / 309.5 | 13.21 / 7813 / 314.3 | 13.26 / 7783 / 314.7 |

#### RTX 5090 (Coder IQ1_M 131K): `v0.2.3` vs `v0.2.7`

On `rtx5090-win-a` (47.15 GiB RAM, driver 621.01), `5090-023-a` ran before the 131K qualification chain and
`5090-023` and `5090-027` ran back to back after it. The PLE residency policy does not admit the table on 47 GiB
RAM.

| Depth (tokens) | `5090-023-a` TTFT s / prefill t/s / decode t/s | `5090-023` TTFT s / prefill t/s / decode t/s | `5090-027` TTFT s / prefill t/s / decode t/s |
|---|---|---|---|
| `unique_prefix` 65 | 0.33 / 214 / 270.4 | 0.24 / 303 / 273.5 | 0.22 / 302 / 265.7 |
| `unique_prefix` 8192 | 1.49 / 5596 / 271.7 | 1.44 / 5887 / 265.8 | 1.40 / 5972 / 264.9 |
| `unique_prefix` 32768 | 4.26 / 7769 / 259.7 | 4.26 / 7764 / 255.9 | 4.18 / 7918 / 263.2 |
| `warm_repeat` 32768 | 0.04 / 327 / 262.3 | 0.05 / 329 / 258.5 | 0.05 / 323 / 265.6 |
| `unique_prefix` 65536 | 8.54 / 7714 / 251.0 | 8.55 / 7698 / 237.3 | 8.39 / 7863 / 263.8 |
| `unique_prefix` 102400 | 13.67 / 7523 / 254.7 | 13.71 / 7508 / 247.0 | 13.41 / 7669 / 260.3 |

#### RTX 4090 + RTX 3090: stage order, speed and PLE residency on engine 0.1.52

The roles draft (`--gpu-roles 0=main,1=helper`, pipeline windows 2) ran install → start → perf → stop in a new root,
right after the qualified `v0.2.3` roles root ran start → perf → stop on the same host (tooling `fd645b6`, NVIDIA
driver 621.01). The measurement sequence restarted the server before `perf_probe` ran, so the roles draft had two
starts; both parsed complete with the reviewed parsers: configured and staged order RTX 3090 then RTX 4090, layers
0-23 / 24-47 (auto
K=24, as `v0.2.3`), expert caches 17.60 / 16.01 GiB. The default-split draft's measurement was stopped during its
download and has no start.

| Depth (tokens) | `pair-roles-023` TTFT s / prefill t/s / decode t/s | `pair-roles-027` TTFT s / prefill t/s / decode t/s |
|---|---|---|
| `unique_prefix` 65 | 0.88 / 76 / 143.8 | 0.92 / 70 / 146.4 |
| `unique_prefix` 8192 | 5.42 / 1520 / 171.0 | 5.30 / 1561 / 166.1 |
| `unique_prefix` 32768 | 11.25 / 2933 / 162.9 | 11.06 / 2980 / 172.1 |
| `warm_repeat` 32768 | 0.32 / 24 / 173.6 | 0.07 / 161 / 165.2 |
| `unique_prefix` 65536 | 19.98 / 3296 / 171.2 | 19.41 / 3397 / 163.8 |
| `unique_prefix` 102400 | 30.68 / 3352 / 169.8 | 29.81 / 3452 / 161.9 |

Engine `0.1.52` locks the 26.8 GiB per-layer embedding table in RAM by its residency policy (31.4–37.5 s at start
across the day's runs) and then leaves its automatic conversation cache off ("not enough free RAM to park
conversations"); `v0.2.3` parked up to 8,192 MiB on this host. Layer-major prefill is on for the split, but every
long prompt declined it ("no VRAM for a super-chunk", 401–403 MiB free).

A follow-up back-to-back single-sample run on the pair (11:16–11:28Z) compared `v0.2.3` (`k-pair-023`, ready
61.2 s), `v0.2.7` stock defaults (`k-pair-027`, ready 90.2 s, PLE locked in 31.4 s, automatic conversation cache
off), the same `v0.2.7` root started with `STRATA_PLE_AUTO_RAM=0` (`k-pair-027-pleauto0`, ready 60.1 s, comparison
arm only; `omp-strata` profiles cannot set it on multi-GPU), and a `v0.2.7` stock repeat (`k-pair-027-repeat`,
ready 90.2 s, PLE locked in 31.9 s):

| Depth (tokens) | `k-pair-023` TTFT s / prefill t/s / decode t/s | `k-pair-027` TTFT s / prefill t/s / decode t/s | `k-pair-027-pleauto0` TTFT s / prefill t/s / decode t/s | `k-pair-027-repeat` TTFT s / prefill t/s / decode t/s |
|---|---|---|---|---|
| `unique_prefix` 62 | 0.87 / 74 / 140.1 | 0.87 / 73 / 137.2 | 0.91 / 73 / 137.1 | 0.95 / 70 / 138.8 |
| `unique_prefix` 8192 | 5.69 / 1451 / 170.5 | 5.60 / 1470 / 171.0 | 5.63 / 1467 / 171.6 | 5.55 / 1484 / 174.1 |
| `unique_prefix` 32768 | 11.54 / 2854 / 166.3 | 11.36 / 2899 / 166.9 | 11.53 / 2863 / 163.5 | 11.30 / 2913 / 166.8 |
| `warm_repeat` 32768 | 0.37 / 21 / 176.2 | 0.08 / 146 / 171.0 | 0.48 / 16 / 161.1 | 0.08 / 146 / 173.2 |
| `unique_prefix` 65536 | 20.24 / 3252 / 163.5 | 19.92 / 3307 / 161.2 | 20.21 / 3257 / 166.9 | 19.92 / 3308 / 157.1 |
| `unique_prefix` 102400 | 31.23 / 3293 / 161.1 | 30.40 / 3384 / 165.5 | 31.15 / 3301 / 165.1 | 30.57 / 3362 / 168.0 |

With `STRATA_PLE_AUTO_RAM=0`, the `v0.2.7` engine sized its automatic conversation cache to 8,192 MiB and parked
conversations again, at 31.15 s vs 30.40 s TTFT for 100K tokens (3,301 vs 3,384 tokens/s prompt reading) and equal
decode (165.1 vs 165.5 tokens/s); `v0.2.3` parked as before. On this 128 GB host the residency policy trades
automatic conversation parking for ~2–3% faster long-prompt reading.

**Post-landing commit-headroom observation and hold on the PLE-in-RAM roles draft (2026-10-28, reported as [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)).**
With the engine serving, the pair's
[v0.2.7 roles main-run G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2/evidence/g10-20261028T102119Z-7ef761.json)
records `commit_available_bytes: 1109463040` (**1.03 GiB**), against
[v0.2.3 main-run G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6/evidence/g10-20261023T135342Z-801f98.json)
`29320192000` (**27.3 GiB**). Both record `commit_limit_bytes: 145695096832` (**135.7 GiB**). These are comparable
main-chain positions, not a newest-receipt substitution. A later comparison-only v0.2.7 pair bench and smoke sampled
**0.632–1.331 GiB** commit headroom (18 approximately 15-second samples); these sampled extrema are not guaranteed
instantaneous peaks. This is narrow Windows commit margin, not physical available RAM or proof of allocation failure.
Engine 0.1.52's PLE RAM residency is the measured policy change; its automatic conversation cache is also off.
The `v0.2.7` roles manifest stays a held **draft**, while the PLE-direct variant below (`strata.ple_io: "direct"`,
`--ple-io direct`) clears the blocker for the pair lane and is current on `v0.2.7`
([decision](DECISION.md#update-2026-10-28-afternoon-the-pairs-ple-direct-and-rtx-5090-262k-strata-v027-profiles-qualify)).
The PRO is unaffected: its [v0.2.7 G10](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2/evidence/g10-20261028T093553Z-422925.json)
records **53,679,923,200 B (53.7 GB)** commit headroom, and the RTX 5090 131K root's policy declines PLE RAM residency
on its 47 GiB host. No receipt, gate result, ledger or existing restoration record is removed.

### Pair PLE-direct qualification run (2026-10-28 afternoon, current)

Profile [`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`](../profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2.json)
([manifest](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/manifest.json),
[ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/qualification.json),
rollback `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6`) runs RTX 4090 + RTX
3090 with Qwen3.8-Flash-Next IQ3_S at 262,144 tokens, stock `--gpu-roles 0=main,1=helper` (RTX 4090 as Main),
`--pipeline-windows 2`, no batch slots, display on the RTX 4090, and `strata.ple_io: "direct"` pinning stock
`--ple-io direct` so the 26.8 GiB PLE table stays on direct SSD reads instead of engine `0.1.52`'s automatic RAM
residency ([OPERATIONS.md](OPERATIONS.md#stock-ple-direct-reads)).

- **Requalify run and gates.** Ran 2026-10-28 18:35–19:22Z on a fresh root (model shards linked from the `v0.2.3`
  roles root) at tooling commit `7f7b16d`. Every measured gate (G10–G21, G24, G26) and operator receipt (G00–G06 at
  `8c1ae59`: 827 tests, 29 skips, no failures; hosted
  [CI run 40745659264](https://github.com/alphastorm/omp-strata/actions/runs/40745659264) on PR #68, commit
  `f3ba668`, green) passed; G22, G23 and G25 are not applicable (21 pass, 3 not applicable).
- **Stage order and start-log observations.** At start, the RTX 3090 (GPU 1) runs layers 0–23 with a 17.6 GiB
  expert cache and the RTX 4090 (GPU 0) runs layers 24–47 with 16.01 GiB; pipeline windows 2 is decode-capable.
  Across all 16 starts of this root (the main chain plus a `perf_probe` pass), every start logged
  `PLE direct read probe: N rows/s (fine)`, none logged a residency-policy line, and every start sized the
  automatic conversation cache at **8,192 MiB**. Restart readiness was 56.8–57.0 s across G16 (57.0 s), G20 (56.9 s)
  and G21 (56.8 s); G26 on the already prepared root took 25.6 s (`25.567 s`) to install and 54.9 s (`54.897 s`) to
  start.
- **Commit headroom and RAM (G10) and conversation cache (G19).** With the engine serving,
  [G10](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/evidence/g10-20261028T183648Z-4f70e0.json)
  measured **27.3 GiB** (`29,328,113,664 B`) Windows commit headroom of a **135.7 GiB** (`145,695,096,832 B`)
  commit limit (versus **1.03 GiB** on the held `v0.2.7` roles draft with PLE in RAM and **27.3 GiB** on `v0.2.3`
  roles), with **65.1 GiB** (`69,902,020,608 B`) available RAM. In
  [G19](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/evidence/g19-20261028T185714Z-26f8cc.json),
  the automatic conversation cache was on at **8,192 MiB** (up to 4 parked conversations), with **20 parks** during
  the gate (20,673 of 20,702 prompt tokens reused in 514 ms vs 8,833 ms cold; 46 uncached tokens on the controlled
  interleaved continuation).
- **Coding evaluation (G24).** Scored **17/18** (tool-loop 2/3, every other task 3/3; batch wall 1,029.479 s, 0
  timeouts, 0 protocol counters) and pilot **5/6**, compared with **14/18** on `v0.2.3` roles and **13/18** on the
  held `v0.2.7` roles draft (PLE in RAM).
- **Throughput (`perf_probe`: single samples at the end of the chain, not a back-to-back A/B).** One request per
  depth, 512 output tokens, alongside the earlier back-to-back single-sample arms on the same PC from the section
  above:

| Depth (tokens) | PLE-direct (`--ple-io direct`, end of chain) TTFT s / prefill t/s / decode t/s | Earlier `v0.2.3` (`k-pair-023`) TTFT s | Earlier `v0.2.7` default (PLE in RAM, `k-pair-027`) TTFT s | Earlier `v0.2.7` `STRATA_PLE_AUTO_RAM=0` (`k-pair-027-pleauto0`) TTFT s |
|---|---|---|---|---|
| `unique_prefix` 8192 | 5.37 / 1,537 / 161–170 | 5.69 | 5.60 | 5.63 |
| `unique_prefix` 32768 | 11.23 / 2,943 / 161–170 | 11.54 | 11.36 | 11.53 |
| `unique_prefix` 65536 | 20.00 / 3,296 / 161–170 | 20.24 | 19.92 | 20.21 |
| `unique_prefix` 102400 | 30.74 / 3,347 / 161–170 | 31.23 | 30.40 | 31.15 |

### RTX 5090 262K opt-in afternoon rerun (2026-10-28, Docker Desktop and WSL stopped)

Profile [`win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2`](../profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2.json)
([manifest](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/manifest.json),
[ledger](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/qualification.json), rollback
`win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6`; the 131K profile stays the RTX 5090 default) reran on
2026-10-28 17:04–17:30Z on the same integration root as the failed morning run, at tooling commit `1914e84`, with
the host's Docker Desktop and WSL stopped.

- **RAM availability with Docker Desktop and WSL stopped versus resident.** With Docker Desktop and WSL stopped, the
  host has **39.8 GiB** available RAM against the profile's unchanged **36 GiB** start floor. With the production
  NInfer VM resident, the host shows **35.7–36.2 GiB** (morning G16 recorded 35.8 GiB), so starts and restarts
  refuse. Operating condition: on this host the opt-in runs only when the host's Docker Desktop and WSL, which also
  run its production NInfer container, are stopped; after WSL restarts that container must be recreated (same image
  and configuration). The qualified `v0.2.3` 262K opt-in has the same constraint now because the newer NInfer VM is
  larger.
- **Gates and retained morning receipts.** Every measured gate (G10–G21, G24, G26) and operator receipt (G00–G06 at
  `1914e84`: 818 tests, 4 skips; hosted
  [CI run 40745659264](https://github.com/alphastorm/omp-strata/actions/runs/40745659264) green) passed; G22, G23
  and G25 are not applicable (21 pass, 3 not applicable). The morning's failed receipts (G15–G21, G24 0/18, G26)
  stay in the ledger.
- **G10, G16, G19 and G24.** With the engine serving,
  [G10](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/evidence/g10-20261028T170459Z-f64a51.json)
  measured **9.98 GiB** (`10,720,952,320 B`) available RAM and **6.92 GiB** (`7,427,244,032 B`) Windows commit
  headroom of a **75.2 GiB** (`80,696,807,424 B`) commit limit.
  [G16](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/evidence/g16-20261028T170803Z-ea167a.json)
  server restart reached readiness in **16.7 s** (G20 restart ready 16.1 s, G21 current ready 16.9 s; G26 on the
  already prepared root: install 10.8 s, `10.76 s`, start 31.5 s, `31.532 s`), with lowest available RAM during G16
  at **8.46 GiB** (`9,087,143,936 B`). In
  [G19](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/evidence/g19-20261028T171331Z-df1d8f.json),
  the automatic conversation cache was on at **1,792 MiB**, with **16 parks** during the gate (`v0.2.3` 262K: cache
  off; 20,672 of 20,701 prompt tokens reused in 305 ms vs 2,880 ms cold, 47 uncached tokens on the controlled
  continuation).
  [G24](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/receipts/g24-scored-20261028T173019Z.json)
  scored **16/18** (tool-loop 1/3, every other task 3/3; batch wall 755.239 s, 0 timeouts, 0 protocol counters) and
  pilot **5/6** (`v0.2.3` 262K: **14/18**; `v0.2.1`: **15/18**).

## Strata v0.2.3 windows (2026-10-23): stock OMP 18.12.6

The owner approved three windows (Ask answers: PRO `"Run now, leave OCR as found"`, RTX 5090 `"131K then 262K
now"`, pair `"Measure now, sign-out allowed"`), run from tooling `5726674`, then the reruns and the pair's chain
(`"Rerun all three now"`, `"Roles chain (4090 Main)"`) from `a915c69` and `de60693`. The RTX 5090 windows paused
NInfer for 1 h 14 min and 4 min and restored the same container; the PRO's two OCR containers were already stopped
and stayed so; the pair's disconnected console session was signed out before the first run. The owner then
qualified the four server profiles and the Studio route ([DECISION.md](DECISION.md)).

### Server chains (G10–G21, G24, G26)

| Profile | Chain wall | Failed gates (each passed its rerun) | G24 scored / pilot |
|---|---|---|---|
| PRO, IQ3_S 262K, four slots | 2,193 s | G10: the deep artifact rehash counted one problem while the server ran; the record kept only the count. The same rehash with the server stopped found none, and so did the G10 rerun. | 17/18, 5/6 |
| RTX 5090, Coder IQ1_M 131K | 1,941 s | G20: two of the owner's scheduled tasks went from Ready to Running during the gate, and the gate compared run states. | 17/18, 6/6 |
| RTX 5090, Coder IQ1_M 262K | 1,983 s | G19: the engine left its automatic conversation cache off (not enough free RAM), and the gate still ran the kept-conversation probe. | 14/18, 6/6 |
| RTX 4090 + RTX 3090, stock roles | 2,974 s | G18: after compaction at 222K tokens the final answer lost the remembered code; the same-root rerun kept it. | 14/18, 5/6 |

All other gates passed. Engine `0.1.48` sized its automatic conversation cache to 8,192 MiB on the PRO and the pair,
1,024-1,280 MiB on the RTX 5090 131K root and off on the 262K root; on the 131K root G19's probe reused 20,672 of
20,701 prompt tokens (239 ms against 2,906 ms cold). The fixes before the reruns: G10 now records each problem's file
and digest, G20 compares each task's Disabled/enabled setting, and G19 follows the engine's reported cache state.

### RTX 4090 + RTX 3090: stage order and speed on engine 0.1.48

Three new roots, each install → start → perf → stop: `scripts/perf_probe.py`, one request per depth, 512 output
tokens, server timings. The NVIDIA driver is now 621.01 (617.42 at the 2026-10-21 A/B), so comparisons across the
two days include a driver change. Every start parsed complete with the reviewed parsers.

| Draft | Stage order | Layers, first stage / last stage (+ head) | Expert caches |
|---|---|---|---|
| default | kept by #1576: RTX 4090, RTX 3090 | 0-24 / 25-47 (K=25) | 17.32 / 16.34 GiB |
| roles, RTX 4090 as Main | configured: RTX 3090, RTX 4090 | 0-23 / 24-47 | 17.63 / 16.04 GiB |
| split 32 | configured: RTX 4090, RTX 3090 | 0-31 / 32-47 | 17.15 / 16.48 GiB |

| Prompt | Decode tokens/s (default / roles / split 32) | Prompt reading tokens/s | TTFT s |
|---|---|---|---|
| 62 tokens | 147.8 / 144.5 / 139.6 | — | 0.9 / 0.9 / 0.9 |
| 8,192 | 155.7 / 173.9 / 164.5 | 1,436 / 1,466 / 1,572 | 5.8 / 5.6 / 5.2 |
| 32,768 | 158.6 / 161.1 / 164.6 | 2,479 / 2,873 / 3,090 | 13.3 / 11.5 / 10.7 |
| 32,768 repeated | 154.4 / 166.4 / 163.8 | reused | 0.5 / 0.6 / 0.5 |
| 65,536 | 159.2 / 172.5 / 167.8 | 2,809 / 3,266 / 3,458 | 23.5 / 20.2 / 19.1 |
| 102,400 | 152.7 / 162.3 / 164.9 | 2,839 / 3,300 / 3,534 | 36.2 / 31.2 / 29.1 |

The default repeats `v0.2.1`'s K=25: the engine log says K=47 would leave a stage fewer than 3 layers, so it chose
K=25. Split 32 reads long prompts fastest, close to `v0.1.43.1`'s 3,508-3,594 tokens/s and 28.6 s at 100K. Roles sits
between the two. Decode stays within 140-174 tokens/s for all three drafts, from single samples.

## All three hosts, every gate (2026-10-21): stock Strata v0.2.1, stock OMP 18.10.1

On 2026-10-21 (at approximately 02:29Z; Ask answers: `"Qualify PRO, 5090 131K, 262K opt-in and route"` and, for
the pair, `"Qualify 0.2.1 anyway"`), the owner qualified all four `v0.2.1` + OMP `18.10.1` server profiles and
selected them as current ([DECISION.md](DECISION.md)):
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1` on **rtxpro6000-win-a** (IQ3_S at 262,144
tokens, four batch slots, conversation parking and 32K prompt chunks, 74 GiB startup RAM floor; rollback
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1`),
`win11-rtx5090-coder-iq1m-131k-strata0.2.1-omp18.10.1` (131,072-token current/default, 34 GiB startup RAM floor;
rollback `win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1`) and
`win11-rtx5090-coder-iq1m-262k-strata0.2.1-omp18.10.1` (262,144-token opt-in only, 36 GiB startup RAM floor,
without changing `tests/candidate.py` `CURRENT`, default commands or the client route; rollback
`win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1` or the `0.2.1` 131K default) on **rtx5090-win-a**, and
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.1-omp18.10.1` on **rtx3090-win-a** (IQ3_S at
262,144 tokens, stock layer split, pipeline windows 2 and 8 GiB conversation parking, no batch slots, display on
the RTX 4090, 78 GiB startup RAM floor; rollback
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1`, while the pair's `v0.1.44.1`
release remains draft, not qualified). Stock `v0.2.1` (tag object
`49ac15cbb32a8662602aaa7b8fc61bf6acef4cf0`, peeled commit
`90767252f420e25223c739d604145ad15911d48b`) publishes no `strata-windows-x64.zip`; each profile pins the Windows
CUDA 13 engine component (`strata-engine-0.1.46-windows-x86_64-cuda-cuda13.tar.gz`, 579,792,118 bytes, SHA-256
`2966143ca8df7919448556e7d148e49ccecae0932bb0d5d31294ccde723f94cd`; manifest SHA-256
`d6ea7d4ae8dce1e646a55363d14c97f9659197f63d500da90efe0d4a8fd82d3e`, build `a7bdbfdabc9a+cuda13.0`), staged into
`runtime\strata\engine\` before stock setup runs ([OPERATIONS.md](OPERATIONS.md#upgrades),
[UPSTREAM.md](UPSTREAM.md#strata-v021-setup-review-component-engine)). Models, contexts, stock setup choices,
engine flags, display placement and RAM floors are unchanged from each predecessor.

Ledgers, receipts and scrubbed results:
[RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1/qualification.json),
[RTX 5090, 131K default](../releases/win11-rtx5090-coder-iq1m-131k-strata0.2.1-omp18.10.1/qualification.json),
[RTX 5090, 262K opt-in](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.1-omp18.10.1/qualification.json),
[RTX 4090 + RTX 3090, 262K and parking](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.1-omp18.10.1/qualification.json).
Rollback ledgers:
[RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1/qualification.json),
[RTX 5090, 131K](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1/qualification.json),
[RTX 5090, 262K opt-in](../releases/win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1/qualification.json),
[RTX 4090 + RTX 3090](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1/qualification.json).

| Measure (new; predecessor) | RTX PRO 6000 (`v0.2.1`, current) | RTX 5090 131K (`v0.2.1`, current/default) | RTX 5090 262K opt-in (`v0.2.1`, current opt-in) | RTX 4090 + RTX 3090 (`v0.2.1`, current) |
|---|---|---|---|---|
| Owner date | 2026-10-21 | 2026-10-21 | 2026-10-21 | 2026-10-21 |
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G24 scored (pred.) | 17/18 (v0.1.44.1 15/18) | 17/18 (15/18) | 15/18 (15/18) | 16/18 (v0.1.43.1 15/18) |
| G24 per task | tool-loop 2/3, others 3/3 | tool-loop 2/3, others 3/3 | tool-loop 0/3, others 3/3 | multifile-regression 2/3, tool-loop 2/3, others 3/3 |
| G24 pilot | 5/6 | 5/6 | 5/6 | 5/6 |
| Scored batch wall (pred.) | 623 s (496 s) | 771 s (703 s) | 778 s (760 s) | 1,051 s (1,047 s) |
| Protocol counters (malformed arguments etc.) | 0 | 0 | 0 | 0 (v0.1.43.1 had 1) |
| G11 typed tool loop | 3/3 tracer runs | 3/3 | 3/3 | 3/3 |
| G12 continuations with reuse (pred.) | 13 (15) | 15 (14) | 12 (16) | 12 (13) |
| G19 interleaved, uncached tokens on the controlled continuation | 48 | 298 (shares only the system prefix) | 329 (system prefix only) | 46 |
| Readiness on measured restarts G16/G20/G21 (pred.) | 23.1-23.5 s (19.7-20.2 s) | 16.5-19.6 s (13.0-13.1 s) | 18.5-19.6 s (12.4-12.6 s) | 46.7-47.1 s (54.7-55.0 s) |
| G26 new root: install / first start wall | 572.6 s / 46.3 s | 308.1 s / 38.3 s | 9.9 s / 41.8 s (install on an already prepared root; not a first-install timing) | 887.3 s / 66.1 s |
| Integration root size (G21, decimal GB) | 96.5 GB | 71.2 GB | 71.2 GB | 95.7 GB |
| Batch slots | 4 (decoded together) | none (one at a time) | none | none |

**Runs and retained failures.** Real-host receipts cite implementation `3f52b65` on the PRO, RTX 5090 131K and
pair main runs; G17 reruns cite `13cbdbe` (PRO, RTX 5090 131K; the 131K G18 rerun too) and `fa0f88a` (pair). The
RTX 5090 262K opt-in ran entirely at `13cbdbe`. Operator receipts G01–G05 cite `91f7b04`; host-free suite G06
cites `84a7843` (CI run [39532567569](https://github.com/alphastorm/omp-strata/actions/runs/39532567569)). G17
failed on the PRO, RTX 5090 131K and pair main runs because since `v0.2.0-beta` (engine `0.1.45.3`) stock's
server shortens a `max_tokens` that is one token over the room left to the room left instead of answering 400
(a prompt that alone leaves no room is still refused, `13cbdbe`), passing on each rerun; the RTX 5090 262K ran
after that adjustment and passed first time. G18 failed once on the RTX 5090 131K (the final turn after
compaction neither fixed the file nor recalled the fact) and passed on its same-root rerun. All failed receipts
remain in the ledgers beside the newer passes.

**Pair performance against its `v0.1.43.1` rollback (accepted by the owner).** On `rtx3090-win-a`, `v0.2.1`'s
automatic layer split puts layers 0-24 on the RTX 4090 and 25-47 on the RTX 3090 (K=25; `v0.1.43.1`: 0-31 /
32-47; the unqualified `v0.1.44.1`: 0-44 / 45-47). Upstream
[Strata#2463](https://github.com/Niko1221/Strata/issues/2463) was closed on 2026-10-19 as not planned, with no
change to link pricing. Back-to-back perf probe on the same host, 2026-10-21 02:03-02:06Z, one 512-token sample
per depth, server-reported rates (decode 141-158 against 170-201 tok/s; prompt reading at 64K-100K tokens
2,838-2,853 against 3,508-3,594 tok/s; 100K-token TTFT 36.0 s against 28.6 s; MTP acceptance 0.8 in both):

| Prompt depth | Decode tok/s v0.1.43.1 → v0.2.1 | Prompt reading tok/s v0.1.43.1 → v0.2.1 | TTFT v0.1.43.1 → v0.2.1 |
|---|---|---|---|
| 63 tokens | 170.2 → 145.2 | — | 0.86 → 0.86 s |
| 8,192 | 201.0 → 150.8 | 1,581 → 1,486 | 5.2 → 5.6 s |
| 32,768 | 193.5 → 145.8 | 3,107 → 2,491 | 10.6 → 13.3 s |
| 32,768 warm repeat (32,761 cached) | 196.8 → 158.4 | — | 0.37 → 0.36 s |
| 65,536 | 194.5 → 141.4 | 3,508 → 2,838 | 18.8 → 23.2 s |
| 102,400 | 183.9 → 157.7 | 3,594 → 2,853 | 28.6 → 36.0 s |

**Boundaries.** G26 installs into a new integration root on a host that keeps earlier roots, never a fresh OS
(and the RTX 5090 262K opt-in's 9.9 s G26 install ran on an already prepared root, not a first-install timing).
G24 scored batch wall is whole-batch wall, not isolated decode latency; all 18 scored attempts and the separate
six-attempt pilots keep their denominators, and task failures remain counted. The pair A/B perf probe is one
512-token sample per depth, comparison evidence accepted by the owner, not a qualification receipt. G22 (images),
G23 (remote clients) and G25 (runtime comparison) are not applicable to these local text-only profiles. The Mac
Studio client route (`client-rtxpro6000-262k-strata0.2.1-omp18.10.1`) qualified independently on 2026-10-21 with
its own G23 receipt ([REMOTE.md](REMOTE.md)) and inherits none of these server gate results.

## RTX 5090 Coder 262K, qualified opt-in (2026-10-15)

On 2026-10-15 the owner qualified `win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1` as an **opt-in**
profile beside the 131K `v0.1.44.1` default. Since the [2026-10-21 owner decision](DECISION.md), `v0.2.1` + OMP
`18.10.1` is current for both the RTX 5090 131K default and the 262K opt-in, and these `v0.1.44.1` profiles are
their qualified rollbacks. Both pin stock Strata v0.1.44.1, stock OMP 18.10.1
and the same Coder IQ1_M model; the opt-in changes configured context/provider window and the startup RAM floor,
not model or component pins. [Owner decision](DECISION.md).

| Measure | 262K, qualified opt-in (now rollback) | 131K, default (now rollback) |
| --- | --- | --- |
| Configured context | 262,144 tokens | 131,072 tokens |
| Minimum available RAM at start | 36 GiB | 34 GiB |
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G24 scored evaluation, three attempts per task | 15/18 | 15/18 |
| Non-scored pilot | 5/6 | 5/6 |
| Tool-loop task, scored / pilot | 0/3 / 0/1 | 0/3 / 0/1 |

The 262K real-host gates and host-free suite use implementation `dabfb8f`. Its original G26 failed because
installation was in a separate chain; that failure remains beside `g26-second-root-20261015T220407Z`,
the passing same-root install/start/quickstart rerun. The reinstall retained the manifest's runtime identity.
Its install/start/quickstart walls were 9.929 / 21.228 / 7.209 s; independent quickstart tests and final stop
also passed. These are that rerun's boundaries, not a first-install timing or a comparison with the 131K root.
All unsuccessful G24 attempts stay counted; unchanged pass counts are not evidence of improved usefulness.

Ledgers: [262K opt-in](../releases/win11-rtx5090-coder-iq1m-262k-strata0.1.44.1-omp18.10.1/qualification.json),
[131K default](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1/qualification.json).

## All three hosts, every gate (2026-10-13): stock Strata v0.1.43.1, stock OMP 18.10.1

The owner qualified this tuple as current on **rtxpro6000-win-a**, **rtx5090-win-a** and **rtx3090-win-a** on
2026-10-13. Since the [2026-10-21 owner decision](DECISION.md), `v0.2.1` + OMP `18.10.1` is current on all three
hosts (`v0.1.44.1` + OMP `18.10.1` is the PRO and RTX 5090 rollback); `v0.1.43.1` is now the pair's qualified
rollback and earlier qualified history on the PRO and RTX 5090, and all three `v0.1.43` + OMP `18.10.1` profiles
are earlier qualified history. The PRO keeps IQ3_S at 262,144 tokens, four slots,
conversation parking and 32K prompt chunks; the RTX 5090 keeps Coder IQ1_M at 131,072; the RTX 4090 + RTX 3090
pair keeps IQ3_S at 262,144, stock layer split, pipeline windows 2 and parking, no batch slots, display on the
RTX 4090. Each tuple has its own root and ledger; no earlier receipt is inherited or replaced.

Each release's `receipts/g00-baseline-20261013.json` is the source audit: stock Strata v0.1.43.1 source
`a0116b2782a5b82622358c04a06496485d12b2d6`, with unchanged stock OMP 18.10.1 source `5d0aaff`, model pins,
llama.cpp archive, Python lock, stock setup plans, engine flags and host floors. The Windows engine archive is
138,187,009 bytes, SHA-256 `38b5f1116bcd76554dd46f5344a6d0f5aa428f02e49db64a7d8e2137356e93d0`.
G00 records quoted `</tool_call>` read as text (#2026), fenced JSON tool-call recovery (#2037), the prompt-loan
fix (#2090), warning-only PLE direct-read probe (#1984; every pack here carries the n-gram table), Windows
watchdog disk-read allowance, pinned bounce buffers (#1996) and a low-VRAM warning (#2065). The batch-slot
refusal fix (#1994) reaches only the PRO; parking progress (#2049) reaches the PRO and pair. Windows NVIDIA
decode defaults remain unchanged. Upstream reports answers byte-identical to v0.1.43 apart from a quoted
`</tool_call>`; these runs do not measure answer-byte parity. Stock setup's calibration/model and BUILD.json
changes do not affect profiles that neither calibrate nor build locally.

Ledgers, receipts and scrubbed results:
[RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43.1-omp18.10.1/qualification.json),
[RTX 4090 + RTX 3090, 262K and parking](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1/qualification.json).
Rollback ledgers:
[RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43-omp18.10.1/qualification.json),
[RTX 4090 + RTX 3090](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43-omp18.10.1/qualification.json).

| Measure | PRO, 262K: v0.1.43.1 + 18.10.1 (earlier history) | PRO, 262K: v0.1.43 + 18.10.1 (earlier history) | RTX 5090: v0.1.43.1 + 18.10.1 (earlier history) | RTX 5090: v0.1.43 + 18.10.1 (earlier history) | Pair, 262K: v0.1.43.1 + 18.10.1 (rollback) | Pair, 262K: v0.1.43 + 18.10.1 (earlier history) |
|---|---|---|---|---|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G10-G20 | pass, first full run | pass, first full run | pass, first full run | pass after full G18 rerun | pass, first full run | pass, run 2 after admission fix |
| G21 resource gate and G26 second-root install | pass | pass | pass | pass | pass | pass |
| GPU memory in use, peak (G21) | 60,298 MiB | 60,286 MiB | 30,836 MiB | 30,836 MiB | 23,211 / 23,266 MiB (4090 / 3090) | 23,206 / 23,266 MiB (4090 / 3090) |
| Engine private-commit / working-set peak (G21) | 134.9 / 72.4 GB | 134.9 / 72.4 GB | 63.4 / 30.6 GB | 63.4 / 30.6 GB | 109.5 / 60.1 GB | 109.4 / 59.8 GB |
| Server restart to verified readiness (G16) | 20.6 s | 20.1 s | 11.7 s | 11.6 s | 54.7 s | 54.7 s |
| Current engine start to verified readiness (G21) | 20.2 s | 20.7 s | 11.8 s | 11.8 s | 55.0 s | 55.0 s |
| Integration root on disk (G21) | 95.4 GB | 95.4 GB | 69.3 GB | 69.3 GB | 94.6 GB | 94.8 GB |
| Cold prefill of a 100K-token prompt (G17) | 12.557 s | 12.570 s | 13.787 s | 13.825 s | 28.152 s | 28.180 s |
| Near-limit OMP session, prompt peak (G17) | 211,729 tokens | 211,878 tokens | 105,367 tokens | 105,360 tokens | 211,777 tokens | 211,769 tokens |
| Near-limit OMP session, cold prefill (G17) | 26.4786 s | 26.4857 s | 14.5276 s | 14.5552 s | 56.1308 s | 56.0213 s |
| Reduced-threshold compaction (g18) | 1 compaction, 21.8 s | 1 compaction, 19.8 s | 5 compactions, 49.1 s | 1 compaction, 22.0 s | 6 compactions, 125.4 s | 1 compaction, 44.7 s |
| Production compaction (g18l) | 225,117 → 23,020 tokens, 28 document turns | 224,846 → 23,122 tokens, 28 document turns | 108,857 → 22,861 tokens, 14 document turns | 108,720 → 22,834 tokens, 14 document turns | 223,483 → 22,833 tokens, 28 document turns | 225,037 → 23,110 tokens, 28 document turns |
| G01-G05 host-free suite, pinned OMP and Strata frontend | 521 tests at `d2fac61`, OK (1 skipped), 213.650 s | 517 tests at `f6fa4d0`, OK (1 skipped), 209.734 s | 521 tests at `d2fac61`, OK (1 skipped), 209.392 s | 517 tests at `f6fa4d0`, OK (1 skipped), 209.009 s | 521 tests at `d2fac61`, OK (26 skipped), 128.824 s | 518 tests at `967086e`, OK (26 skipped), 131.347 s |
| Non-scored pilot | 6/6 | 4/6 | 5/6 | 5/6 | 5/6 | 5/6 |
| G24 scored evaluation, three attempts per task | 15/18 | 16/18 | 15/18 | 15/18 | 15/18 | 16/18 |
| Tool-loop task, scored | 0/3 | 1/3 | 0/3 | 0/3 | 1/3 | 1/3 |
| Multifile-regression task, scored | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 |
| Scored batch wall, including failures | 555 s | 590 s | 858 s | 658 s | 1,047 s | 988 s |
| Scored tool calls / reported output tokens | 259 / 94,904 | 261 / 99,835 | 315 / 154,887 | 277 / 107,725 | 244 / 88,963 | 216 / 85,152 |
| G26 quickstart example / independent tests | pass / pass | pass / pass | pass / pass | pass / pass | pass / pass | pass / pass |

**Runs and retained failures.** All new runs use implementation `d2fac6154b6392bd7b263efc1b7d7301774ff0b4`.
The PRO's 2026-10-13 chain ran from about 06:55 to 07:30Z and passed every measured gate on its first run.
Scored 15/18 against v0.1.43's 16/18: tool-loop is 0/3 against 1/3. Pilot 6/6 against 4/6 avoids the rollback's
OMP thinking-loop abort. The RTX 5090 passed full G18 (g18 + g18l) on its first run, with five reduced-threshold
compactions, unlike v0.1.43's failed main run, comparison-only rate probes and full gate rerun. Its scored
15/18 (tool-loop 0/3) and pilot 5/6 match the rollback. The pair's G10 stage order is complete, event
`kept_1576`, with both cards in configured order. Scored 15/18 against rollback run 2's 16/18, with
multifile-regression 2/3 and tool-loop 1/3; pilot 5/6 on both. The multifile-regression third attempt exits
OMP 0 and passes the verifier but has one malformed-arguments counter, so `verified_pass` is false. The
published G24 receipt explicitly reports one protocol error for the pair's scored batch; the other new scored
batches and every pilot report zero. All new attempts have zero client execution failures, zero timeouts and
no abort reason. Failed tasks and the protocol counter stay counted; neither a passing G24 nor qualification
claims that every coding task or counter passed. The rollback's failed G18 and pair first-run receipts remain.

**Timing boundaries.** The RTX 5090's scored wall increases from 658 to 858 s alongside more work:
277 → 315 tool calls and 107,725 → 154,887 reported output tokens. Dividing whole-batch wall by reported output
tokens gives about 6.1 → 5.5 ms/token; this includes tools, restarts and failures, not isolated decode latency.
The pair's reduced G18 took 125.4 s for six compactions against 44.7 s for one; its production G18L is a separate
321.9 s run with one compaction. G26's first-start wall is 65.747 s; the runner's restart before G16 is about
70 s against about 69 s on rollback run 2 (operator run context), not G16's 54.7 s server readiness. G16/G21
readiness remains 54.7/55.0 s on both pair tuples; single-GPU readiness and cold prefill stay close in these
runs. G21 records no expert-load rate, and no new host file-cache diagnosis or engine-speed claim is inferred.

**Boundaries.** G06 audits hosted PR #26 run
[38328220748](https://github.com/alphastorm/omp-strata/actions/runs/38328220748), 26/26 successful at `d2fac61`.
G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable to these local text-only
profiles with those claims off. Single-GPU host-free suites skip the synthetic finalized cut-call case the
stock frontend never emits; the pair's additional skips are single-GPU-only G25 tests. G24 passes complete
reporting, not every task: all 18 scored attempts and the separate six-attempt pilots retain their own
denominators. Evaluator exit 1 is not an omitted gate. G26 uses a new root on an existing host, not a fresh OS.
These synthetic tasks are bounded usefulness evidence, not a task-quality or runtime-superiority decision.
Each host's v0.1.42 + OMP 18.8.9 profile remains earlier qualified history. A client route requires its own G23
and inherits none of these local gate results; see [REMOTE.md](REMOTE.md).

## All three hosts, every gate (2026-10-12): stock Strata v0.1.43, stock OMP 18.10.1

The owner qualified this tuple as current on **rtxpro6000-win-a**, **rtx5090-win-a** and **rtx3090-win-a** on
2026-10-12; it was the pair's v0.1.43.1 rollback and is now earlier qualified history on all three hosts,
with v0.1.42 + OMP 18.8.9 retained as earlier qualified history. The PRO keeps IQ3_S at 262,144 tokens, four slots,
conversation parking and 32K prompt chunks; the RTX 5090 keeps Coder IQ1_M at 131,072; the RTX 4090 + RTX 3090
pair keeps IQ3_S at 262,144, stock layer split, pipeline windows 2 and parking, no batch slots, display on the
RTX 4090. Each tuple has its own root and ledger; none of the earlier receipts is inherited or replaced.

Each release's `receipts/g00-baseline-20261012.json` is the source audit: Strata v0.1.43 source `7695859`,
OMP 18.10.1 source `5d0aaff`, unchanged model pins, llama.cpp archive, Python lock and stock setup plans.
The pair's RAM floors now follow stock setup's conversation-cache tip, 86 GiB total / 78 GiB available at start;
the v0.1.42 262K pair profile had kept its 131K predecessor's 78/66 GiB. Stock setup changes only MIN_ENGINE.
On Windows/NVIDIA the decode defaults stay v0.1.42's; G00 records the NaN guard, restored parallel expert reads,
the tail-skip default staying off from 90% cached experts, and request-timing fixes. The audited host-free
multi-turn, tool-using, reasoning session with forced compaction captures byte-identical OMP request bodies on
18.10.1 and 18.8.9 for this provider; this is a bounded source/capture audit, not a universal request claim.

Ledgers, receipts and scrubbed results:
[RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43-omp18.10.1/qualification.json),
[RTX 4090 + RTX 3090, 262K and parking](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43-omp18.10.1/qualification.json).
Rollback ledgers:
[RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.42-omp18.8.9/qualification.json),
[RTX 4090 + RTX 3090](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9/qualification.json).

| Measure | PRO, 262K: v0.1.43 + 18.10.1 (rollback) | PRO, 262K: v0.1.42 + 18.8.9 (earlier qualified) | RTX 5090: v0.1.43 + 18.10.1 (rollback) | RTX 5090: v0.1.42 + 18.8.9 (earlier qualified) | Pair, 262K: v0.1.43 + 18.10.1 (rollback) | Pair, 262K: v0.1.42 + 18.8.9 (earlier qualified) |
|---|---|---|---|---|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G10-G20 | pass, first run | pass, first run | pass after full G18 rerun | pass, first run | pass, run 2 after admission fix | pass, first run |
| G21 resource gate and G26 second-root install | pass | pass | pass | pass | pass | pass |
| GPU memory in use, peak (G21) | 60,286 MiB | 60,284 MiB | 30,836 MiB | 30,836 MiB | 23,206 / 23,266 MiB (4090 / 3090) | 23,206 / 23,266 MiB |
| Engine private-commit / working-set peak (G21) | 134.9 / 72.4 GB | 134.9 / 72.4 GB | 63.4 / 30.6 GB | 63.4 / 30.6 GB | 109.4 / 59.8 GB | 109.4 / 59.9 GB |
| Server restart to verified readiness (G16) | 20.1 s | 20.6 s | 11.6 s | 12.1 s | 54.7 s | 40.7 s |
| Current engine start to verified readiness (G21) | 20.7 s | 20.7 s | 11.8 s | 12.3 s | 55.0 s | 43.0 s |
| Integration root on disk (G21) | 95.4 GB | 95.3 GB | 69.3 GB | 69.3 GB | 94.8 GB | 94.6 GB |
| Cold prefill of a 100K-token prompt (G17) | 12.6 s | 12.6 s | 13.8 s | 13.8 s | 28.2 s | 28.1 s |
| Near-limit OMP session, prompt peak (G17) | 211,878 tokens | 211,707 tokens | 105,360 tokens | 105,368 tokens | 211,769 tokens | 211,849 tokens |
| Near-limit OMP session, cold prefill (G17) | 26.5 s | 26.5 s | 14.6 s | 14.5 s | 56.0 s | 56.1 s |
| Production compaction (G18) | 224,846 → 23,122 tokens, 28 document turns | 224,685 → 23,530 tokens, 28 turns | 108,720 → 22,834 tokens, 14 turns (full rerun) | 108,546 → 22,934 tokens, 14 turns | 225,037 → 23,110 tokens, 28 turns | 222,490 → 22,781 tokens, 28 turns |
| G01-G05 host-free suite, pinned OMP and Strata frontend | 517 tests at `f6fa4d0`, OK (1 skipped), 209.734 s | 515 tests at `ced1f08`, OK (1 skipped), 212.582 s | 517 tests at `f6fa4d0`, OK (1 skipped), 209.009 s | 515 tests at `ced1f08`, OK (1 skipped), 212.941 s | 518 tests at `967086e`, OK (26 skipped), 131.347 s | 515 tests at `da2c714`, OK (26 skipped), 135.169 s |
| Non-scored pilot | 4/6 | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 |
| G24 scored evaluation, three attempts per task | 16/18 | 16/18 | 15/18 | 16/18 | 16/18 | 15/18 |
| Tool-loop task, scored | 1/3 | 1/3 | 0/3 | 1/3 | 1/3 | 0/3 |
| Multifile-regression task, scored | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| Scored batch wall, including failures | 590 s | 506 s | 658 s | 799 s | 988 s | 946 s |
| G26 quickstart example / independent tests | pass / pass | pass / pass | pass / pass | pass / pass | pass / pass | pass / pass |

**Runs and retained failures.** The PRO's one run at `f6fa4d0` passed every measured gate. Its pilot's two
failures are tool-loop and bugfix-b; bugfix-b ended on OMP's thinking-loop detector, a client-side abort. Its
scored 16/18 matches v0.1.42; pilot 4/6 is one below v0.1.42's 5/6. Every failed attempt stays counted.
The RTX 5090's main run at `f6fa4d0` passed every measured gate except G18, whose final fact-retention reply
ended at `CODE: KEEP` with a normal stop although its reasoning named the whole code. As G00 records,
comparison-only G18 probes outside qualification runs passed 14/15 on each release: v0.1.43 4/5 then 10/10,
v0.1.42 5/5 then 9/10, with the same failure shape. This is pre-existing IQ1_M model behavior on this gate, not
a new-release rate change. One g18-only diagnostic also passed; it did not replace gate evidence. A single
full G18 rerun (g18 + g18l) at `8bb1d54` passed; its receipt is newest, and the failed receipt stays.
The pair's first run at `f6fa4d0` failed G10-G21 and G26 because lifecycle admitted multi-GPU stage-order
inference only for v0.1.42 and reported "startup stage order unavailable". `967086e` reviewed v0.1.43's
stock `gpu_list`, `layer_split_value` and `ordered_gpus` against the identical vendored v0.1.42 digest,
and a real start parses complete, layers 0-31 on the RTX 4090 and 32-47 on the RTX 3090. That commit admits
v0.1.43 and tests that every multi-GPU profile pins a reviewed release. Run 2 at `967086e` passed every
measured gate and quickstart. Both runs' receipts are published; newest wins without erasing failures.

**Readiness and Windows file-cache state.** G16/G20/G21 receipts give the pair 54.7-55.0 s versus v0.1.42's
40.7-43.0 s. Separately, the operator's inspection of private engine startup logs shows the 51.1 GiB expert
pack read through the Windows file cache at 7.33-8.02 GiB/s on the 23 starts before run 2's G15, then unbuffered
at 2.33-2.95 GiB/s on all 9 starts from G15 onward, including the restarts behind those receipt figures.
The v0.1.42 262K root's 12 starts on 2026-10-11 included 2 unbuffered at 2.94 GiB/s and 10 cached at
6.20-8.23 GiB/s. These are explicitly engine-log observations, not receipt load-rate metrics (G21 reports that
metric unavailable); raw logs stay private. The measured slowdown tracks host file-cache state, not an engine
change, and no cause for cache eviction is claimed. Single-GPU G16 readiness is unchanged within these runs:
PRO 20.6 → 20.1 s and RTX 5090 12.1 → 11.6 s. G21's current-start readiness is a separate row, not the G16 restart.

**Boundaries.** G06 source/configuration audits cite successful hosted PR #24 runs
[38212474606](https://github.com/alphastorm/omp-strata/actions/runs/38212474606) (`f6fa4d0`),
[38288518084](https://github.com/alphastorm/omp-strata/actions/runs/38288518084) (`967086e`) and
[38294442014](https://github.com/alphastorm/omp-strata/actions/runs/38294442014) (`9729fb7`). The second
integration fix, `9729fb7`, makes `pull_run.py` refuse a requalify log naming more than one run.
G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable to these local text-only
profiles with those claims off. The single-GPU suite skip is the synthetic finalized cut-call case the stock
Strata frontend never emits; the pair's additional skips are single-GPU-only G25 tests. G24 passes the complete
reporting experiment, not every coding task: all 18 scored attempts, failures and pilot attempts remain in their
own denominators. Requalify's evaluator exit 1 is not an omitted gate. These synthetic tasks are bounded
usefulness evidence, not a task-quality or runtime-superiority decision; one attempt either way is within their
noise. These local ledgers qualify no client route; the Mac Studio's route to v0.1.43 qualified independently
the same day. Current and earlier route results are recorded separately in [REMOTE.md](REMOTE.md).

## RTX PRO 6000 at 262K and RTX 5090, every gate (2026-10-11): stock Strata v0.1.42, stock OMP 18.8.9

New ledgers for the tuple the RTX 4090 + RTX 3090 pair qualified on, on the RTX PRO 6000 (IQ3_S, four slots and
parking, 262,144 tokens) and the RTX 5090 (Coder IQ1_M, 131,072 tokens). Each profile moves only Strata (v0.1.41 to
v0.1.42) and OMP (18.8.6 to 18.8.9) from its predecessor; the model pins, the llama.cpp archive, the Python lock and
the stock setup plan are unchanged. Every measured gate (G10-G21, G24 and G26) passed on its first run, in one
requalify run per host on a new root beside the predecessor's (2026-10-11, 05:28-06:03Z). The owner qualified both;
the v0.1.42 profiles were the v0.1.43 tuple's rollbacks and now stay qualified as earlier history, like v0.1.41.

By source reading, neither of v0.1.42's two new CUDA defaults applies on these hosts. The route tail skip
(`STRATA_ROUTE_TAIL_SKIP=7`, which stock documents as +13-16% decode on cards that miss experts) and the PCIe share
refined from the CPU's speed both need experts outside VRAM, and both cards hold every expert: their engine logs
report `100% VRAM resident`. The tail skip is also off with batch slots, which the PRO runs. Neither engine log has
the tail skip's start-up line or a `PCIe share:` line.

Ledgers, receipts and scrubbed results:
[RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.42-omp18.8.9/qualification.json).

| Measure | RTX PRO 6000, 262K: v0.1.42 + 18.8.9 (now rollback) | RTX PRO 6000, 262K: v0.1.41 + 18.8.6 (earlier history) | RTX 5090: v0.1.42 + 18.8.9 (now rollback) | RTX 5090: v0.1.41 + 18.8.6 (earlier history) |
|---|---|---|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G10-G20 | pass, first run | pass after the G17/G18 fixture fix and rerun | pass, first run | pass |
| G21 resource gate and G26 second-root install | pass, first run | pass | pass, first run | pass |
| GPU memory in use, peak (G21) | 60,284 MiB | 60,079 MiB | 30,836 MiB | 30,836 MiB |
| Engine private-commit / working-set peak (G21) | 134.9 / 72.4 GB | 134.9 / 72.4 GB | 63.4 / 30.6 GB | 63.4 / 30.6 GB |
| Start to verified readiness (G21) | 20.7 s | 20.3 s | 12.3 s | 11.7 s |
| Integration root on disk (G21) | 95.3 GB | 95.4 GB | 69.3 GB | 69.4 GB |
| Cold prefill of a 100K-token prompt (G17) | 12.6 s | 12.6 s | 13.8 s | 13.8 s |
| Near-limit OMP session, prompt peak (G17) | 211,707 tokens | 211,806 tokens | 105,368 tokens | 105,878 tokens |
| Near-limit OMP session, first read (G17) | 204,020 tokens in 26.5 s (7,140 more reused) | 211,163 tokens in 28.0 s | 105,195 tokens in 14.5 s | 105,165 tokens in 14.5 s |
| Production compaction (G18) | 224,685 → 23,530 tokens, 28 document turns | 222,868 → 22,674 tokens, 28 document turns | 108,546 → 22,934 tokens, 14 document turns | 109,069 → 23,647 tokens, 14 document turns |
| G01-G05 host-free suite, pinned OMP and Strata frontend | 515 tests at `ced1f08`, OK (1 skipped), 212.582 s | 387 tests at `f2515d4`, OK (1 skipped), 243.83 s | 515 tests at `ced1f08`, OK (1 skipped), 212.941 s | 384 tests at `370a02e`, OK (1 skipped), 236.611 s |
| Non-scored pilot | 5/6 | 5/6 | 5/6 | 6/6 |
| G24 scored evaluation, three attempts per task | 16/18 | 17/18 | 16/18 | 15/18 |
| Tool-loop task, scored | 1/3 | 2/3 | 1/3 | 1/3 |
| Multifile-regression task, scored | 3/3 | 3/3 | 3/3 | 2/3 |
| Scored batch wall, including failures | 506 s | 565 s | 799 s | 764 s |

**Boundaries.** G00 records the operator's source audit of the pins, which names the tail skip as an engine default
the integration does not write. G06 cites green hosted CI run
[38114870952](https://github.com/alphastorm/omp-strata/actions/runs/38114870952) at `ced1f08`, which ran both
profiles' own lanes. G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable because
those capabilities or claims remain disabled. The one suite skip is the synthetic finalized cut-call case the pinned
Strata frontend never emits. The six synthetic evaluation tasks are bounded usefulness evidence, not a comparative
benchmark: all 18 attempts and their failures remain in each scored denominator, and one attempt either way is
within their noise. Requalify's exit 1 comes from the frozen evaluator's nonzero exit when any attempt fails, not an
omitted gate or an incomplete export. A comparison-only probe after the gate runs (not gate evidence) ran the new
root's `perf_probe.py` against both roots, interleaved: two rounds per root on the PRO and fifteen on the RTX 5090.
At 8K-100K tokens, prefill was within 2.2% of v0.1.41 on the PRO and within 0.2% on the RTX 5090. Decode was within
2.1% on the PRO at every depth and within 0.6% on the RTX 5090 up to 32K tokens; at 64K and 100K the RTX 5090
decoded 2.5% and 2.3% slower, with speculative acceptance about 2 points lower. Each round's greedy text differs,
and across fifteen rounds these gaps are within the text's own variation (permutation p = 0.10 and 0.17).

## RTX 4090 + RTX 3090, every gate (2026-10-11): stock Strata v0.1.42, stock OMP 18.8.9

The predecessor ledger on **rtx3090-win-a**, with an RTX 4090 (GPU 0) beside the then-desktop-driving RTX 3090 (GPU 1).
Qwen3.8-Flash-Next IQ3_S runs at 131,072 tokens with stock setup's layer split (`--gpus all`,
`--layer-split auto`) and stock `--pipeline-windows 2` (`strata.pipeline_windows`), without batch slots. The owner
qualified `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9`. Every measured gate (G10-G21, G24 and G26)
passed on its first run, in one requalify run on a fresh root (G26's second root, 2026-10-11, 01:01-01:56Z). Its
model shards were linked from the measurement root. `start` passed its check for stock's decode-capable pipeline
line. The 262K display-on-RTX-4090 parking variant below remains earlier qualified history; this predecessor is rollback only
after moving the display back to the RTX 3090. Single-card RTX 3090 profiles are not rollbacks for this two-card host.

Ledger, receipts and scrubbed results:
[RTX 4090 + RTX 3090](../releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9/qualification.json).

| Measure | Strata v0.1.42 + OMP 18.8.9, IQ3_S, pipeline windows 2 (predecessor; display on RTX 3090) |
|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable |
| G10-G20 | pass, first run; G10 and G20 have complete per-card records for both GPUs |
| G21 resource gate and G26 second-root install | pass, first run |
| GPU memory in use, peak per card (G21) | RTX 4090: 23,024 MiB; RTX 3090: 24,165 MiB (with the desktop); 47,189 MiB together; 468 samples per card, none unavailable |
| Engine private-commit / working-set peak (G21) | 106.7 / 57.3 GB |
| Start to verified readiness (G21) | 55.0 s |
| Integration root on disk (G21) | 94.6 GB |
| Cold prefill of a 100K-token prompt (G17) | 26.2 s, 100,030 tokens |
| Near-limit OMP session, prompt peak (G17) | 105,821 tokens |
| Production compaction (G18) | 106,224 → 22,583 tokens, 14 document turns |
| G01-G05 host-free suite, pinned OMP and Strata frontend | 515 tests at `efd7031`, OK (26 skipped), 134.083 s |
| Non-scored pilot | 6/6 |
| G24 scored evaluation, three attempts per task | 15/18 |
| Tool-loop task, scored | 0/3 |
| Scored batch wall, including failures | 1,020 s |

**Boundaries.** G00 records the operator's source audit of the pins. G06 cites green hosted CI run
[38099086933](https://github.com/alphastorm/omp-strata/actions/runs/38099086933) at `efd7031`, which ran this
profile's own lane. G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable; G25 compares
single-GPU profiles only. The 26 suite skips are 25 G25 tests that only single-GPU lanes run and the synthetic
finalized cut-call case the pinned Strata frontend never emits. The frozen evaluation is bounded usefulness
evidence, not a comparative benchmark: all attempts and their failures remain in the scored denominator. The RTX
3090 alone's first IQ3_S ledger (Strata v0.1.31) was also 15/18 with tool-loop 0/3; tool-loop is 0/3 on seven of the
eighteen published ledgers. Qualification is about integration correctness, not task quality. Requalify's exit 1
comes from the frozen evaluator's nonzero exit when any attempt fails, not an omitted gate or an incomplete export.

**Qualified 131K rollback with the display on the RTX 4090 (2026-10-11).** The owner qualified the
[display-placement variant](../releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9/qualification.json); it
keeps the same pins and pipeline-windows-2 flags. After its original startup refusal at 1,601 MiB of display-GPU
memory, an authorized start-only continuation completed G10-G21 and G24. Its first G26 receipt failed because
that summary had no install row; the failure remains in the history. A later main-root install/start/quickstart/stop
run passed G26 in one raw summary, preserving the same runtime identity: the latest ledger has 21 pass and
3 not applicable. No raw runs were combined. At the same G17 positions as the qualified pw2 main run, the cold
100,030-token prefill took 26.258 s versus 26.247 s; the first near-limit request prefills 105,212 tokens in 29.504 s
and decodes at 145.4 tokens/s, versus 105,202 tokens in 29.542 s and 134.1 tokens/s. Those requests emitted 197
versus 132 tokens, so this is an observation, not a speedup claim. The non-scored pilot was 5/6 versus 6/6, and
the scored batch 14/18 versus 15/18; every failed attempt remains in its denominator. One pre-G16 status was
degraded (startup stage order unavailable for the current engine generation); the runner's restart succeeded and
G16 passed. Both roots stopped; final GPU memory returned to 180/0 MiB. The display-on-RTX-3090 pw2 profile
remains its qualified predecessor and rollback, usable only after restoring that display placement.

### Earlier qualification: 262K with stock conversation parking, display on the RTX 4090 (2026-10-11)

The owner selected a new [262K pair profile](../profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9.json): the same
pins, display placement, automatic layer split, pipeline windows 2 and no batch slots as the qualified 131K
display-on-RTX-4090 pair, with stock context 262,144 and `--conversation-cache-mib 8192`. No calibration or
prefill-chunk override. The owner selected this profile as current on 2026-10-11; it was the v0.1.43 tuple's
rollback and now stays as earlier qualified history, like the 131K display-on-RTX-4090 profile. The independent [262K ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9/qualification.json)
has 21 pass and 3 not applicable; `verify_release.py --require-ready` passes. No earlier receipt is inherited.

The unchanged canonical runner completed on the profile's own probe installation in one raw run,
2026-10-11 22:45:13–23:28:15Z (2,581.4 s). That run includes install, start, every measured gate and the
QUICKSTART example with independent tests, so G26 is not assembled from separate summaries. Its install
fingerprint and generated-file identity match the profile.

| Qualification measure | 262K pair with stock conversation parking |
|---|---|
| G10-G20, G21 resource record, G24 reporting and G26 | pass, unchanged gates and tolerances |
| Live-prefix continuations with reuse (G12) | 12/12 |
| Cold prefill of 100,030 tokens (G17) | 28.067 s; 26.258 s on the qualified 131K display-on-RTX-4090 rollback |
| Near-limit OMP prompt peak (G17) | 211,849 tokens; exact boundary and explicit overflow pass at context 262,144 |
| Production compaction (G18) | 222,490 → 22,781 tokens, 28 document turns |
| Parking after an intervening conversation (G19) | 20,672 of 20,701 prompt tokens reused; 491 ms follow-up; preceding cold turns 8,335 and 8,203 ms |
| GPU memory in use, peak per card (G21) | RTX 4090: 23,206 MiB; RTX 3090: 23,266 MiB; 46,472 MiB together; 531 samples per card, none unavailable |
| Engine private-commit / working-set peak (G21) | 109.4 / 59.9 GB |
| Minimum available RAM serving (G21) | 62.1 GB (57.9 GiB) |
| Current start to verified readiness / first guarded-start command | 43.0 / 63.539 s; different boundaries |
| Integration root on disk (G21) | 94.6 GB |
| G01-G05 host-free suite | 515 tests at `da2c714`, OK (26 skipped), 135.169 s |
| Non-scored pilot / G24 scored evaluation | 5/6 / 15/18; 5/6 / 14/18 on the qualified 131K display-on-RTX-4090 rollback |
| Tool-loop task, scored | 0/3 |
| Scored batch wall, including failures | 946.254 s |

The first near-limit request had 211,192 prompt tokens, 7,140 reused, 56.057 s of prefill and 135.1 tokens/s
decode for 120 output tokens. The 131K rollback's first near-limit request was 106,200 tokens and 197 output
tokens: those depths and outputs differ, so this is not a matched speedup comparison.

**Retained failures and boundaries.** Pilot and scored commands returned 1 because the tool-loop exact-money
verifier failed (all three scored attempts); no attempt timed out or was omitted. G24 passed the complete
six-by-three reporting experiment, not every task. Pre-G16 status returned 1; the canonical runner's restart
returned 0 and G16 passed. G21 retains two dead-engine restarts, six disconnect endings, one error ending and
one stop mid-request from the fault probes, with zero engine error lines. The closing census found the root
stopped, no Strata process or port-18090 listener, GPU memory 182/0 MiB and power limits 450/370 W. G06 cites
green [PR CI run 38181496629](https://github.com/alphastorm/omp-strata/actions/runs/38181496629), which exercised
this profile's lane at `da2c714`. G22, G23 and G25 remain not applicable; neither a clean OS nor exact-output
fidelity nor runtime superiority is claimed.

The comparison-only probe ran one cold request at each depth, with 512 output tokens and no cached input.
Server-reported prefill and decode, and wall-clock time to the first token:

| Input tokens | Time to first token, s | Prefill, tokens/s | Decode, tokens/s |
|---|---|---|---|
| 8,192 | 5.687 | 1,452 | 167.3 |
| 32,768 | 10.752 | 3,068 | 190.6 |
| 102,400 | 28.815 | 3,571 | 190.5 |
| 204,800 | 56.666 | 3,629 | 178.0 |
| 256,000 | 72.237 | 3,558 | 172.9 |

A follow-up used the profile as shipped, a tiny control request first, then two unique-prefix requests at each
of 8K and 32K, still 512 output tokens and no cached input. The 8K requests decoded at 207.06 and 207.29 tokens/s
(5.126 and 4.940 s to first token); the 32K requests at 189.01 and 190.00 (10.633 and 10.768 s). The earlier pw2
measurement rounds, also with a tiny control before those depths, recorded 191.6–209.6 at 8K and 194.2–201.1 at
32K. The warmed 8K figures are higher than the initial first-request figure; this does not establish a speedup.
The probe recorded expert caches of 9,294 slots / 17.16 GiB on the RTX 4090 and 8,186 / 16.50 GiB on the RTX 3090.

**Parking is not an exact-output claim.** The original stock-default probe failed strict follow-up token equality.
A diagnostic repeated the identical 98,483-token follow-up in four fresh, sequential engines, with the profile
flags unchanged but `STRATA_ROUTE_TAIL_SKIP=0` and `STRATA_SNAPSHOT_VERIFY=1`. Repeating the live process itself
differed at token index 3; parked differed at index 11, while fresh re-read equalled the first live output. Thus
across-process exact equality cannot isolate parking fidelity here. The parked run restored 98,347 checkpoint
tokens in 1.5128 s, reported 98,347 reused and 136 newly read tokens, and reached its first token in 2.636 s,
versus 1.604 s live and 28.730 s fresh re-read. The disabled-skip diagnostic is not the profile-as-shipped verdict.
All initial failures and the diagnostic remain in private evidence; none is a substituted qualification gate.

## RTX 4090 + RTX 3090 layer split (2026-10-10): stock Strata v0.1.42, stock OMP 18.8.9

<details>
<summary>Draft layer-split throughput, card order, pipeline windows and batch-slot probes (2026-10-10)</summary>

Host **rtx3090-win-a** (127.7 GiB RAM as setup reads it, PCIe 3.0) now holds an RTX 4090 beside its RTX 3090, the
4090 at x16 through a riser and the 3090 at x8. Stock setup's two-card layer split (`--gpus all`,
`--layer-split auto`) runs one model across both. Draft profiles `win11-rtx3090-rtx4090-<model>-131k-…`, each
installed into its own root by the guarded install; every root ran `scripts/perf_probe.py` (one request per depth,
512 output tokens, server-reported). Nothing here is a qualification: every ledger stays draft. The single-card rows
are the v0.1.38 figures below (2026-10-03); the RTX 4090 ones come from rtx4090-win-a, a different host.

| Root | Decode at ~60 / 8K / 32K / 64K / 100K tokens | Prefill at 8K / 32K / 64K / 100K | Cold 100K prompt to first token | MTP acceptance |
|---|---|---|---|---|
| Pair, Coder IQ1_M | 120 / 144 / 145 / 140 / 134 tokens/s | 2.8K / 4.0K / 4.0K / 3.9K tokens/s | 26.4 s | 0.79-0.84 |
| Pair, IQ3_XXS | 170 / 192 / 178 / 182 / 173 | 1.8K / 3.9K / 4.7K / 5.0K | 20.6 s | 0.80-0.89 |
| Pair, IQ3_S | 137 / 183 / 183 / 179 / 174 | 1.6K / 3.2K / 3.6K / 3.7K | 27.6 s | 0.84-0.89 |
| Pair, IQ3_S, 4090 last (measurement only) | 133 / 185 / 182 / 184 / 181 | 1.6K / 3.0K / 3.6K / 3.7K | 27.9 s | 0.85-0.89 |
| Pair, IQ3_S, `--pipeline-windows 2` (measurement only, two runs) | 165 / 201 / 198 / 198 / 193 | 1.6K / 3.2K / 3.6K / 3.7K | 28.0 s | 0.74-0.80 |
| Pair, IQ3_S, `--pipeline-windows 2` profile (installed) | 166 / 209 / 189 / 197 / 196 | 1.6K / 3.1K / 3.6K / 3.7K | 28.1 s | 0.74-0.80 |
| Pair, IQ3_S, stock calibration, 4 slots and stock tips | 102 / 155 / 159 / 155 / 149 | 1.5K / 1.9K / 2.8K / 3.1K | 32.8 s | 0.89-0.94 |
| RTX 3090 alone, IQ3_S (v0.1.38) | 67 / 88 / 86 / 84 / 84 | 1.1-1.3K across 8K-100K | 85.3 s | 0.85-0.88 |
| RTX 4090 alone, IQ3_S (v0.1.38) | 95 / 136 / 134 / 132 / 126 | 3.9-4.4K across 8K-100K | 24.9 s | 0.84-0.90 |

- **Against the RTX 3090 alone, the pair doubles decode and triples the long prompt.** With IQ3_S it decodes
  174-183 tokens/s against 84-88 at 8K-100K, prefills 3.2-3.7K tokens/s against 1.1-1.3K at 32K-100K, and reads a
  cold 100K-token prompt in 27.6 s against 85.3 s. Against the RTX 4090 alone it decodes 1.3-1.4x faster but
  prefills at about 80-85% of its rate (24.9 s for the cold 100K prompt). The expert cache on the first card held
  17.6 GiB and hit 99.0-99.4% at 8K-100K. Short prompts prefill slower on every pair root: 1.5-2.8K tokens/s at 8K.
- **Card order.** Setup writes `"gpu": [0, 1]`, the 4090 first. Stock's automatic order would move the faster card
  to the last stage, but its #1576 rule keeps the configured order when the faster card reports less VRAM than the
  card the split ends on: 24,564 against 24,576 MiB here, so the 3090 runs the last stage (head, draft and verify)
  with layers 32-47 and the 4090 layers 0-31. A measurement-only install with an explicit `--gpus 1,0` put the 4090
  last with no reorder: the 3090 ran layers 0-18 and the 4090 layers 19-47 and the head. The two orders measured
  within run-to-run noise (decode -3% to +4%, prefill -4% to 0, the cold 100K prompt 27.9 against 27.6 s). Stock's
  auto split searches the boundary for each order (the best of 46 placements by predicted decode-window time, with
  the 4090 priced at 0.22 ms per layer and the 3090 at 0.50): its best placements came to 18.4 ms per window with the
  3090 last and 19.1 ms with the 4090 last, so the order leaves little to gain. Profiles keep stock's order.
- **Stock's `--pipeline-windows 2` decodes faster; `STRATA_PF_FUSED=1` prefills slower.** Measured without a profile:
  each run copied the plain IQ3_S root's generated config, added the opt-in, launched stock's server as the lifecycle
  does and ran `scripts/perf_probe.py` as requalify does; the plain config, the pipeline and the pipeline with fused
  prompt kernels ran in turn, twice. The pipeline (the first card starts the next verify window while the last card
  verifies this one) decoded 9-13% faster at 8K-100K (178 to 198 tokens/s at 32K, 171 to 193 at 100K), faster in
  all eight depth-and-round pairs, with prefill unchanged. Stock documents its tokens as the serial loop's for the
  same expert caches; it keeps 309 MiB of the 4090's cache for its second verifier, so a few experts move to the CPU
  and a near-tie can flip. MTP acceptance reads lower (0.87 to 0.78). The fused prompt kernels on top cut
  prefill 11-12% at 32K-100K (the cold 100K prompt 31.5 s against 27.8). Upstream's 2x RTX 3090 report (#1447)
  had the pipeline at +17% prefill with flat decode. The draft profile `win11-rtx3090-rtx4090-iq3s-131k-pw2-…` pins
  it (`strata.pipeline_windows`); its install and start on the host recorded stock's decode-capable pipeline line in
  `run.json`, and it decoded 189-209 tokens/s at 8K-100K with the prefill of the plain profile.
- **Stock's recommendations together cost speed here.** Stock `tools/calibrate.py` on the IQ3_S pair kept
  `--pcie-frac 0.20 --spec-min-p 0.70` (from 0.34 and 0.5; its confirmation median rose from 128.7 to 137.7
  tokens/s). Combined with `--parallel 4` and stock setup's tips (`--prefill auto:32768`, an 8 GiB conversation
  cache), one request decoded 13-15% slower at 8K-100K and prefilled 8-40% slower, and the cold 100K prompt took
  32.8 s against 27.6. The expert cache shrank from 17.62 to 15.62 GiB (9,544 to 8,451 experts), and stock's start
  log warns that the prompt path borrows 12.55 GiB of each card's cache slots, "little room for the verify windows'
  buffers under WDDM", suggesting `--prefill auto:8192`.
- **Batch slots added no throughput on long agent sessions.** A private harness ran 1, 2 and 4 OMP sessions at
  once against the slots profile, each reading 11 documents over 14 turns to a ~91K-token prompt (no compaction, no
  deadline hit, no out-of-memory line). Concurrent conversations of that size do not all stay cached, so the server
  read them again:

| Sessions at once | Turns per minute, all sessions | vs one | Mean turn per session | Prefilled / conversation (server) |
|---:|---:|---:|---|---|
| 1 | 8.3 | 1.00x | 7.2 s | 0.98x |
| 2 | 4.5 | 0.55x | 26.4 s | 1.43x; 2 running, 1 waiting at most |
| 4 | 5.5 | 0.67x | 42.5-43.4 s | 1.66x; 4 running, 3 waiting at most |

**Boundaries.** One request per depth, so differences of a few percent are noise. The pair rows are Strata v0.1.42
and the single-card rows v0.1.38, and the RTX 4090 alone ran on a different host. No gate ran on the pair: these are
draft screens, and qualification is a separate step.

</details>

## RTX PRO 6000 at 262K, every gate (2026-10-10): stock Strata v0.1.41, stock OMP 18.8.6

<details>
<summary>Earlier qualified history: gate table, G17/G18 fixture fix and boundaries (2026-10-10)</summary>

A new ledger on the RTX PRO 6000 (IQ3_S, four slots and parking) at 262,144 tokens, the model's trained context.
Only the context changes from the 131K PRO profile: stock setup's plan sets `--max-context 262144` and keeps KV
streaming (`--kv-resident 32768`), `--parallel 4` and both stock recommendations; OMP is given 261,120 tokens and
the RAM floor at start rises from 72 to 74 GiB. The owner qualified it; the 131K profile is its rollback.

Ledger, receipts and scrubbed results:
[RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json).

| Measure | 262,144 tokens (current) | 131,072 tokens (rollback) |
|---|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G10-G20 | pass after the G17/G18 fixture fix and rerun | pass, first run |
| G21 resource gate and G26 second-root install | pass | pass |
| GPU memory in use, peak (G21) | 60,079 MiB | 59,372 MiB |
| Engine private-commit / working-set peak (G21) | 134.9 / 72.4 GB | 125.0 / 63.7 GB |
| Start to verified readiness (G21) | 20.3 s | 18.6 s |
| Integration root on disk (G21) | 95.4 GB | 95.4 GB |
| Cold prefill of a 100K-token prompt (G17) | 12.6 s | 12.6 s |
| Near-limit OMP session, prompt peak (G17) | 211,806 tokens | 105,763 tokens |
| Production compaction (G18) | 222,868 → 22,674 tokens, 28 document turns | 108,747 → 23,221 tokens, 14 document turns |
| G01-G05 host-free suite, pinned OMP and Strata frontend | 387 tests at `f2515d4`, OK (1 skipped), 243.83 s | 384 tests at `daaaa7a`, OK (1 skipped), 237.902 s |
| Non-scored pilot | 5/6 | 5/6 |
| G24 scored evaluation, three attempts per task | 17/18 | 15/18 |
| Tool-loop task, scored | 2/3 | 0/3 |
| Scored batch wall, including failures | 565 s | 534 s |

**The G18 failure and the fixture fix.** On the first run G18's production long session sent its fixed 20
documents, which peaked at 162,071 tokens, under this window's compaction threshold (OMP compacts at the window less
the larger of 15% of it and 16,384 tokens: 221,952 here), so OMP never compacted and G18 failed. G17's near-limit
session had the same fixed size (105,757 tokens), far from this window's limit. Both fixtures now follow the
profile's window: G17's session aims just under the compaction threshold, and G18's runs long enough to pass it.
For 131,072-token profiles they are unchanged (20 documents; a near-limit target of 105,013 tokens instead of
105,000). The rerun at the fixed fixtures passed G17, G18 and its long session; the failure stays in the ledger.

**Boundaries.** G00 records the operator's source audit of the context change; the pins are the current PRO
profile's. G06 cites green hosted CI run
[38025466923](https://github.com/alphastorm/omp-strata/actions/runs/38025466923), which ran this profile's own lane.
G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable because those capabilities or
claims remain disabled. The one suite skip is the synthetic finalized cut-call case the pinned Strata frontend never
emits. The six synthetic evaluation tasks are bounded usefulness evidence, not a comparative benchmark: all 18
attempts and their failures remain in the scored denominator, and 17/18 against 15/18 is not a significant
difference (Fisher's exact p = 0.60).
Requalify's exit 1 comes from the frozen evaluator's nonzero exit when any attempt fails, not an omitted gate or an
incomplete export. A comparison-only probe on the same card before this run (not gate evidence) found time to first
token at 26K-89K tokens and four- and eight-stream throughput within 1-2% of the 131K profile, and a 244K-token
prompt read in 32.5 s.

</details>

## RTX 5090, every gate (2026-10-09): stock Strata v0.1.41, stock OMP 18.8.6

<details>
<summary>Earlier qualified history: gate table and boundaries (2026-10-09)</summary>

A new ledger on the RTX 5090 (Coder IQ1_M, 131,072 tokens). Strata moves from v0.1.40.3 to v0.1.41 and OMP from
18.8.4 to 18.8.6; the Coder pins, the llama.cpp archive, the Python lock and the stock setup plan are unchanged. By
source reading, v0.1.41's new CPU prompt-sharing default applies on this host (one GPU, no batch slots, experts
beyond the GPU's cache streamed from RAM) to prompt chunks under 1,024 tokens; the server log does not report it.
The owner qualified it; the 18.8.4 RTX 5090 profile is its rollback.

Ledger, receipts and scrubbed results:
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.41-omp18.8.6/qualification.json).

| Measure | Strata v0.1.41 + OMP 18.8.6 | Strata v0.1.40.3 + OMP 18.8.4 (rollback) |
|---|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G10-G20 | pass | pass |
| G21 resource gate and G26 second-root install | pass | pass |
| GPU memory in use, peak (G21) | 30,836 MiB | 30,834 MiB |
| Engine private-commit / working-set peak (G21) | 63.4 / 30.6 GB | 63.4 / 30.6 GB |
| Start to verified readiness (G21) | 11.7 s | 11.7 s |
| Integration root on disk (G21) | 69.4 GB | 69.3 GB |
| Cold prefill of a 105K-token prompt (G17) | 14.5 s | 14.5 s |
| G01-G05 host-free suite, pinned OMP and Strata frontend | 384 tests at `370a02e`, OK (1 skipped), 236.611 s | 380 tests at `2c32e2b`, OK (1 skipped), 235.452 s |
| Non-scored pilot | 6/6 | 5/6 |
| G24 scored evaluation, three attempts per task | 15/18 | 16/18 |
| Tool-loop task, scored | 1/3 | 1/3 |
| Multifile-regression task, scored | 2/3 | 3/3 |
| Scored batch wall, including failures | 764 s | 800 s |

**Boundaries.** G00 records the operator's new source audit, including the CPU prompt-sharing default above as a
source reading, not a measurement. G06 cites green hosted CI run
[37868686274](https://github.com/alphastorm/omp-strata/actions/runs/37868686274) on main, which ran the 18.8.6 lane
as its own job. G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable because those
capabilities or claims remain disabled. The one suite skip is the synthetic finalized cut-call case the pinned
Strata frontend never emits. The six synthetic evaluation tasks are bounded usefulness evidence, not a comparative
benchmark: all 18 attempts and their failures remain in the scored denominator, and one attempt either way is within
their noise. Requalify's exit 1 comes from the frozen evaluator's nonzero exit when any attempt fails, not an omitted
gate or an incomplete export.

</details>

## RTX PRO 6000, every gate (2026-10-08): stock Strata v0.1.41, stock OMP 18.8.6

<details>
<summary>Earlier qualified history: gate table, boundaries and Terminal-Bench 2.1 on OMP 18.8.6 (2026-10-08)</summary>

A new ledger on the RTX PRO 6000 (IQ3_S, four slots and parking, 131,072 tokens). Strata moves from v0.1.40.3 to
v0.1.41 and OMP from 18.8.4 to 18.8.6; the stock setup plan, including `--parallel 4` and both stock
recommendations, is unchanged. The owner qualified it; the 18.8.4 PRO profile is its rollback. The tuple's RTX 5090
and RTX 3090 drafts have not run.

Ledger, receipts and scrubbed results:
[RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json).

| Measure | Strata v0.1.41 + OMP 18.8.6 | Strata v0.1.40.3 + OMP 18.8.4 (rollback) |
|---|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G10-G20 | pass, first run | pass after the G16 predicate fix and rerun |
| G21 resource gate and G26 second-root install | pass | pass |
| GPU memory in use, peak (G21) | 59,372 MiB | 58,513 MiB |
| Engine private-commit / working-set peak (G21) | 125.0 / 63.7 GB | 125.0 / 63.7 GB |
| Start to verified readiness (G21) | 18.6 s | 18.7 s |
| Integration root on disk (G21) | 95.4 GB | 95.4 GB |
| G01-G05 host-free suite, pinned OMP and Strata frontend | 384 tests at `daaaa7a`, OK (1 skipped), 237.902 s | 380 tests at `2c32e2b`, OK (1 skipped), 267.592 s |
| Non-scored pilot | 5/6 | 5/6 |
| G24 scored evaluation, three attempts per task | 15/18 | 15/18 |
| Tool-loop task, scored | 0/3 | 0/3 |
| Scored batch wall, including failures | 534 s | 489 s |

**Boundaries.** G00 records the operator's new source audit: Strata v0.1.41's new setup-planning code (a GPU
compute-mode advisory and one expert-option helper) is admitted only at its reviewed source hashes; requirements,
generated config keys and served routes are unchanged; stock's new CPU prompt-sharing default stays off with four
batch slots. G06 cites green hosted CI run
[37857656002](https://github.com/alphastorm/omp-strata/actions/runs/37857656002), including the 18.8.6 lane. G22
(images), G23 (remote clients) and G25 (runtime comparison) are not applicable because those capabilities or claims
remain disabled. The one suite skip is the synthetic finalized cut-call case the pinned Strata frontend never emits.
The six synthetic evaluation tasks are bounded usefulness evidence, not a comparative benchmark: all 18 attempts
and their failures remain in the scored denominator. The PRO fails the tool-loop task in all three attempts, as on
18.8.4. Requalify's exit 1 comes from the frozen evaluator's nonzero exit when any attempt fails, not an omitted
gate or an incomplete export.

**Terminal-Bench 2.1 on this profile (2026-10-09), one attempt.** The same 30 tasks, with the harness now on stock
OMP 18.8.6 (its agent files are byte-identical to 18.8.3's), paired with the
[slots-and-parking profile's run](#rtx-pro-6000-with-batch-slots-and-parking-every-gate-2026-10-07-stock-strata-v01403-stock-omp-1883)
on Strata v0.1.40.3 with the OMP 18.8.3 harness. Strata and the harness's OMP changed together, so the pairing
compares tuples, not engines.

| 30 Terminal-Bench 2.1 tasks, IQ3_S on the PRO | v0.1.41, OMP 18.8.6 harness | v0.1.40.3, OMP 18.8.3 harness |
|---|---|---|
| passed, all 30 (the 28 without `hf-model-inference` and `kv-store-grpc`) | 23 (21) | 19 (17) |
| agent time, all tasks (median a task) | 4.17 h (4.2 min) | 4.95 h (5.1 min) |
| output tokens | 1.61M | 1.72M |
| failed: agent time limit | 4 | 5 |
| failed: wrong or incomplete result | 3 | 6 |

- **Four more passed and none fewer.** Both passed 19 and neither 7; only this profile passed `cancel-async-tasks`,
  `extract-elf`, `overfull-hbox` and `protein-assembly` (exact McNemar p = 0.125, the same on the 28). On the 19 both
  passed it took a median 1.04x the agent time. That meets the bar set beforehand for an improvement claim, four more
  of 30 at no more than twice the agent time, but on one attempt the difference is not significant, and three of the
  four had also passed on Strata v0.1.40.1 with the OMP 18.5.0 harness.
- **The same four tasks hit the agent time limit** (`extract-moves-from-video`, `make-doom-for-mips`,
  `make-mips-interpreter`, `train-fasttext`); `adaptive-rejection-sampler`, a time limit before, now ended with a
  wrong result. No tool call was left in the reasoning and no server stopped at omp's exit.
- **Harness.** It restarted its SSH tunnel once, after the client's network changed, and no trial lost the model.
  Trials ran one at a time.

</details>

## Three GPUs, every gate (2026-10-08): stock Strata v0.1.40.3, stock OMP 18.8.4

<details>
<summary>Earlier qualified history (and single-card RTX 3090 ledger): gate table, G16 rerun and boundaries (2026-10-08)</summary>

New ledgers on the RTX PRO 6000 (IQ3_S, four slots and parking), RTX 5090 and RTX 3090 (Coder IQ1_M), all at
131,072 tokens. The PRO changes only OMP from its 18.8.3 profile; its stock setup plan, including `--parallel 4`
and both stock recommendations, is unchanged. The RTX 5090 and RTX 3090 move from the fourth tuple's Strata
v0.1.34 and OMP 18.4.10. The owner qualified all three; the 18.8.3 PRO profile and the fourth tuple's RTX 5090 and
RTX 3090 profiles are their rollbacks.

Ledgers, receipts and scrubbed results:
[RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json),
[RTX 3090](../releases/win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json).

| Measure | RTX PRO 6000 | RTX 5090 | RTX 3090 |
|---|---|---|---|
| Latest ledger outcomes | 21 pass, 3 not applicable | 21 pass, 3 not applicable | 21 pass, 3 not applicable |
| G10-G20 | pass after the G16 predicate fix and rerun | pass | pass |
| G21 resource gate and G26 second-root install | pass | pass | pass |
| GPU memory in use, peak (G21) | 58,513 MiB | 30,834 MiB | 23,433 MiB |
| Engine private-commit / working-set peak (G21) | 125.0 / 63.7 GB | 63.4 / 30.6 GB | 55.2 / 30.3 GB |
| Start to verified readiness (G21) | 18.7 s | 11.7 s | 18.9 s |
| Integration root on disk (G21) | 95.4 GB | 69.3 GB | 69.4 GB |
| G01-G05 host-free suite at `2c32e2b`, pinned OMP 18.8.4 and Strata v0.1.40.3 frontend | 380 tests, OK (1 skipped), 267.592 s | 380 tests, OK (1 skipped), 235.452 s | 380 tests, OK (1 skipped), 233.472 s |
| Non-scored pilot | 5/6 | 5/6 | 6/6 |
| G24 scored evaluation, three attempts per task | 15/18 | 16/18 | 15/18 |
| Tool-loop task, scored | 0/3 | 1/3 | 1/3 |
| Scored batch wall, including failures | 489 s | 800 s | 1,819 s |

**G16 on the PRO.** The main run recorded a failure because the predicate counted mentions of `append.py`, not
its executions. Commit `2c32e2b` fixes the predicate; a separate start/G16/stop rerun passes, with one append
execution and one remaining log line after client-only and combined restarts. Both receipts remain:
[main-run failure](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4/receipts/g16-20261008T135751Z-075001.json) and
[passing rerun](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4/receipts/g16-20261008T141450Z-0e4006.json).
The newer receipt decides the ledger's G16 outcome.

**Boundaries.** G00 records the operator's new source audit; G06 cites green hosted CI run
[37809963570](https://github.com/alphastorm/omp-strata/actions/runs/37809963570), including the 18.8.4 lane.
G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable because those capabilities
or claims remain disabled. The one suite skip is the synthetic finalized cut-call case the pinned Strata
frontend never emits. The six synthetic evaluation tasks are bounded usefulness evidence, not a comparative
benchmark: all 18 attempts and their failures remain in each scored denominator. The PRO fails the tool-loop
task three times; the 5090 twice; the 3090 twice plus one multifile-regression attempt. Requalify's exit 1 comes
from the frozen evaluator's nonzero exit when any attempt fails, not an omitted gate or an incomplete export.

</details>

## RTX PRO 6000 with batch slots and parking, every gate (2026-10-07): stock Strata v0.1.40.3, stock OMP 18.8.3

<details>
<summary>Earlier qualified history: stock batch/parking probes, gate table and Terminal-Bench 2.1 on OMP 18.8.3 (2026-10-07)</summary>

Profile `win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3` on rtxpro6000-win-a is the qualified
profile below on the newest stable tuple, plus three things stock setup offers for this host. **Batch slots:**
`--parallel 4`, stock's recommendation for this card; OMP's in-flight limit for the server is 4. **Conversation
parking:** `--conversation-cache-mib 8192`, up to four conversations parked in host RAM. **32K prompt chunks:**
`--prefill auto:32768`. Every applicable gate passed at the first attempt (21 pass, G22, G23 and G25 not applicable
as before), and the owner qualified the profile. Ledger, receipts and scrubbed results:
[qualification.json](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3/qualification.json).

**Why these settings.** Strata's own test tools measured each one on the qualified v0.1.40.2 root, read-only, with
that root's config plus the flag under test:

| Probe (`tools/batch_test.py`, `tools/parking_test.py`) | Result |
|---|---|
| 4 requests of 512 tokens at once, `--batch 4` (what `--parallel 4` starts) | 259.7 tokens/s in total against ~218 one after another (+19%); every slot's tokens equal its solo run |
| 2 requests at once | 242 tokens/s against ~223 (+9%) |
| A 109,822-token conversation's follow-up after another conversation, parked | 1.63 s (restored in 0.89 s, 109,925 tokens reused) against 0.67 s live and ~15 s read again; identical tokens |
| `--prefill auto:32768` | 31K-token prompt 4.64 → 3.99 s; 99K-token prompt 14.4 → 12.4 s |

A request alone keeps the single-request path, so slots help only when requests overlap: subagents beside the lead,
or several clients. A parked conversation of ~110K tokens takes ~3.1 GB, so the 8 GiB budget holds about two that
large.

| Measure | Slots and parking (v0.1.40.3, 18.8.3) | Qualified (v0.1.40.2, 18.8.0) |
|---|---|---|
| GPU memory in use while serving (G10) | 57,902 MiB | 55,006 MiB |
| Engine private-commit / working-set peak (G21) | 125.2 / 63.9 GB | 113.8 / 55.7 GB |
| Minimum available system RAM while serving (G21) | 123.5 GB | 137.8 GB |
| Start to verified readiness (G21) | 18.7 s | 16.6 s |
| Cold prefill, 100,030 tokens (G17) | 13,130 ms | 14,330 ms |
| Near-limit first turn, prompt time (G17) | 12,465 ms (98,032 read) | 16,420 ms (105,320 read) |
| Near-limit session, wall (G17) | 16.0 s | 20.7 s |
| Decode in the near-limit requests (G17) | 233–267 tokens/s | 233–277 tokens/s |
| Every slot generating, a queued request dropped, then all dropped: to idle (G14) | 262 ms (4 slots) | 285 ms (1 request) |
| Raw 20.7K-token conversation's follow-up after another conversation (G19) | 20,669 of 20,698 tokens reused; 0.34 s against 3.33 s cold | not claimed |
| OMP follow-up after the other conversation, tokens read (G19) | 46 | 294 |
| Client and full server restarted: next turn (G16) | 3.8 s | 5.9 s |
| Production compaction (G18L) | 108,580 → 22,757 tokens | 108,030 → 22,990 tokens |
| Coding evaluation (G24) | 16/18 (tool-loop 1/3), batch 588 s | 16/18 (tool-loop 1/3), batch 617 s |

The comparison column is the qualified profile's rerun with speculative compaction off. G19 ran both first turns at
once in two batch slots. G18's reduced 12K threshold compacted six times here, against once before. After each
summary the agent read a 3.9K-token file again, which with the 7.1K-token system prompt cannot fit under that
threshold; the earlier run's later turns ran small commands instead. The production threshold (G18L) behaves as
before.

**Terminal-Bench 2.1 on this profile (2026-10-07/08), one attempt.** The same 30 tasks as the earlier PRO runs
(below), now with the harness on stock OMP 18.8.3. Its agent keeps the servers a run starts alive until the container
is torn down ([UPSTREAM.md](UPSTREAM.md), OMP item 9), so all 30 tasks count again. The earlier runs used the OMP
18.5.0 harness, so they are context here, not a paired comparison.

| 30 Terminal-Bench 2.1 tasks, IQ3_S on the PRO | Slots and parking (v0.1.40.3), OMP 18.8.3 harness | v0.1.40.1, OMP 18.5.0 harness |
|---|---|---|
| passed, all 30 (the 28 without `hf-model-inference` and `kv-store-grpc`) | 19 (17) | 21 (20) |
| agent time, all tasks (median a task) | 4.95 h (5.1 min) | 5.47 h (6.2 min) |
| output tokens | 1.72M | 1.92M |
| failed: agent time limit | 5 | 5 |
| failed: wrong or incomplete result | 6 | 3 |
| failed: server stopped at omp's exit | 0 | 1 |

- **Not distinguishable from the earlier runs.** Both passed 16 and neither 6; v0.1.40.1 alone passed 5 and this
  profile alone 3 (exact McNemar p = 0.73; on the 28, p = 0.45). On the 16 both passed this profile took a median
  1.06× the agent time. v0.1.39 also passed 19 (p = 1.0).
- **Two failures filled their container's memory cap with the agent's own work.** In `train-fasttext` the agent's
  Python process was killed and the agent ran on to the time limit. In `model-extraction-relu-logits` the verifier
  ran the agent's script on a larger network than the one the agent was given, and the 2 GiB cap killed it.
- **The slots stayed idle.** Trials ran one at a time and no agent started a subagent, so this run measures the
  profile's answers, not the slots' throughput.
- **Harness.** It restarted its SSH tunnel twice, and no trial lost the model. The run was stopped and resumed once
  on the client; the trial in flight then was rerun.

</details>

## RTX PRO 6000, every gate (2026-10-07): stock Strata v0.1.40.2, stock OMP 18.8.0

<details>
<summary>Earlier qualified history: resources, throughput, speculative-compaction fix and G24 rerun (2026-10-07)</summary>

Profile `win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0` on rtxpro6000-win-a: IQ3_S, a 131,072-token context,
INT8 KV with stock `--kv-resident 32768`, MTP speculation and every expert in VRAM. Every applicable gate passed at
the first attempt: 21 pass, and G22, G23 and G25 are not applicable to this local, text-only, transcript-replay profile
without a comparative claim. The run found OMP's speculative compaction competing with the agent's turns (below); the
integration now turns it off, G17, G18 and G24 were rerun that way, and the owner then qualified the profile. Ledger,
receipts and scrubbed results:
[qualification.json](../releases/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0/qualification.json).

**Why this tuple.** Terminal-Bench measured Strata v0.1.40.1 on the PRO first, on the stock OMP 18.5.0 harness of the
v0.1.39 runs below: 21/30 against v0.1.39's 19/30. On the 28 tasks without `hf-model-inference` and `kv-store-grpc`
it passed 20 against 19 (both 17, v0.1.39 alone 2, v0.1.40.1 alone 3; exact McNemar p = 1.0), and both stranded
tool calls (`mailman`, `pytorch-model-cli`) passed, leaving none of that class. On the 17 tasks both passed it took a
median 0.78x the agent time. The first pass lost its SSH tunnel to the host, so 24 trials lost the model for all or
part of their run; they were set aside and rerun after the harness learned to restart its tunnel. The owner's rule
for a qualification then moved both components to their newest stable releases. Terminal-Bench has not run on
v0.1.40.2 or OMP 18.8.0.

### Resources (G10, G21)

| Measure | RTX PRO 6000 | Boundary |
|---|---|---|
| GPU memory in use while serving | 55,006 of 97,887 MiB | G10 sampler |
| Engine working-set lifetime peak | 55.70 GB | G21 per-process peak |
| Engine private-commit lifetime peak | 113.83 GB | G21 per-process peak |
| Minimum available system RAM | 137.79 GB | gate samplers |
| Integration root on disk | 95.4 GB | G21 file sizes; shards hard-linked with the earlier PRO roots |
| Start to verified readiness | 16.6 s | G21 current server, wall |
| Engine dead/restarted events | 2 | G21 log scan, deliberate G15 kills |

G13 recorded zero non-loopback ETW events. The root was first installed 20 minutes before this run by the same
tooling (548 s, mostly stock setup); the run's install step re-ran guarded stock setup over it in 8.5 s, so G26 here
is a second root on a host that keeps earlier roots, not a fresh installation.

### Throughput (G17, server-reported)

| Case | RTX PRO 6000 |
|---|---|
| Cold prefill, 100,030 tokens | 14,336 ms (7.0K tokens/s) |
| Cached continuation at 105,872 tokens, prompt time | 116 ms |
| Decode in the four near-limit requests | 231.5–258.9 tokens/s |

**OMP 18.8.0 compacts speculatively near its threshold; with one local engine that costs a cold re-read.** The
near-limit session's first turn reached 105,459 tokens, inside the 13.8K-token band below OMP's compaction threshold
(110,541). OMP then sent the same model a background handoff summary of the session: 101,261 prompt tokens and 642
output tokens. The integration allows one in-flight request per provider, which held the agent's next turn for the
17 s that took, and the summary had replaced the engine's live prefix, so that turn re-read all 105,748 of its tokens
(Strata reported none reused; 15.4 s) instead of about 0.1 s. The session ended below the threshold, so the summary was
never applied. The fourth tuple's G17 runs on OMP 18.4.10 show no such request: three requests each, the later two
reusing 104.8K-105.0K tokens. The integration now sets stock `compaction.asyncEnabled: false` (`906f4aa`; UPSTREAM.md,
OMP item 12), and a host-free test fails whenever a session inside the speculation band sends the engine anything but
its own turns.

### Agent turns, restarts and context (G11–G19)

| Case | RTX PRO 6000 |
|---|---|
| Tracer runs (typed tools and transcript recall) | 3/3 |
| Same-session prefix reuse | 12/12 continuations |
| Generating cancel to idle | 36 ms |
| Queued drop, then active drop, to idle | 285 ms |
| Engine killed while idle: next turn (G15) | 33.8 s |
| Engine killed mid-generation: next turn (G15) | 32.4 s |
| Client restart: next turn (G16) | 0.9 s |
| Client and full server restarted: next turn (G16) | 5.9 s |
| Exact server limit and explicit overflow (G17) | pass |
| Production compaction (G18L) | 113,025 → 30,720 tokens |

The G16 next-turn times exclude the preceding server stop/start (15.8 s to readiness).

### Coding evaluation (G24)

The frozen `synthetic-1` set, harness, caps and continuation restart hook are unchanged. The non-scored pilot passed
4/6 (`bugfix-a` and `tool-loop` failed), followed by all 18 scheduled scored attempts.

| Task | RTX PRO 6000 |
|---|---|
| bugfix-a | 3/3 |
| bugfix-b | 3/3 |
| multifile-regression | 3/3 |
| tool-loop | 1/3 |
| long-context | 3/3 |
| continuation | 3/3 |
| **Scored** | **16/18** |
| Median task wall; batch wall | 32.2 s; 616 s |

Failed tasks remain in the denominator, and no scored attempt timed out. G24 passes for complete, independently
verified reporting, not for the score.

### Rerun with speculative compaction off (G17, G18, G24)

Implementation `906f4aa`, same root and profile, 2026-10-07 15:45-16:01Z. The first run's receipts stay in the
ledger; the newest receipt of each gate decides its status.

| Case | Speculation on (`befe5f9`) | Off (`906f4aa`) |
|---|---|---|
| G17 near-limit session: engine requests | 3 turns + 1 summary; the turn after the summary reused none of its 105,748 tokens | 4 turns; each after the first reused 105.5K-106.3K tokens (114-316 ms prompt) |
| G17 near-limit session, wall | 50.7 s | 20.7 s |
| G18 reduced threshold (12,000 tokens): compactions; wall | 5; 116.7 s | 1; 21.5 s |
| G18L production compaction; session wall | 113,025 → 30,720 tokens; 161.5 s | 108,030 → 22,990 tokens; 74.4 s |
| G24 scored; pilot | 16/18 (tool-loop 1/3); 4/6 | 16/18 (tool-loop 1/3); 6/6 |
| G24 median task wall; batch wall | 32.2 s; 616 s | 28.7 s; 617 s |

The G18 rows come from the gate's fixed workloads, not from matched sessions: the model's turns differ between runs.
G01-G05 were re-recorded from the host-free suite at `906f4aa` (369 tests, OK, 1 skipped).

</details>

## RTX PRO 6000 against the RTX 4090 (2026-10-06): stock Strata v0.1.39, stock OMP 18.5.0

<details>
<summary>Draft comparisons: RTX PRO 6000 vs RTX 4090, private 60-task set, UD-Q4_K_XL and Terminal-Bench 2.1 (2026-10-06)</summary>

Host **rtxpro6000-win-a** is rtx4090-win-a with its RTX 4090 replaced by an NVIDIA RTX PRO 6000 Blackwell Workstation
Edition: 97,887 MiB, RTX Enterprise driver 616.92, same i9-14900K and 192 GB DDR5-5200. Draft profile
`win11-rtxpro6000-iq3s-131k-strata0.1.39-omp18.5.0` differs from the 4090's v0.1.39 draft only in the GPU model and
VRAM floor: stock setup plans the same flags at 96 GB as at 24 GB, `--pool-workers 15` included. Guarded install into
its own root with the same IQ3_S shards (hard links); no gate ran and the ledger stays draft. The 4090 figures are
its two v0.1.39 runs of 2026-10-05; the PRO's are two runs on 2026-10-06, each from a fresh server start.

| IQ3_S 131K, v0.1.39, mean of 2 runs: RTX 4090 → RTX PRO 6000 | 8K | 32K | 64K | 100K |
|---|---|---|---|---|
| decode, tokens/s | 116.2 → 271.0 | 116.4 → 268.4 | 116.3 → 259.3 | 115.0 → 258.4 |
| prefill, tokens/s | 3,707 → 5,764 | 4,224 → 7,918 | 4,290 → 8,044 | 4,125 → 7,784 |
| time to first token, s | 2.26 → 1.48 | 7.92 → 4.26 | 15.55 → 8.46 | 25.33 → 13.64 |

- **Decode 2.2-2.3x, prefill 1.6-1.9x.** The two PRO runs differ by up to 5% at 64K and 100K; the gap to the 4090
  is far larger than its 12-15% host drift noted below. MTP draft acceptance is alike (0.83-0.89 on both).
- **Every expert is VRAM-resident on the PRO.** `--expert-cache auto` filled the GPU's expert cache with all 24,576
  experts (46.84 GiB); on the 4090 it held 8,372 (15.88 GiB) at 82-93% hits and fetched the rest over PCIe. The PRO
  used 55.9 GB of its 96 GB at the 100K depth, so the stock flags leave about 40 GB free.
- **IQ3_S passed all 12 screen tasks on the PRO**, all six hard ones included, against 10 on the 4090 with v0.1.39
  and 11 with v0.1.38: one attempt each, within the hard tier's attempt-to-attempt flips, so no quality claim.
- **Sustained load, the hour of the screen (56 busy minutes):** GPU power 446 W median, 465 W p95, 519 W max; core
  74 °C median, 79 °C max; hotspot 89 °C and hottest memory chip 84 °C max; no thermal slowdown, PCIe Gen5 x16
  throughout. CPU package power stayed near 17 W because no expert streams from RAM. Peak in the perf bursts: 523 W.
- **Host changes the card needed.** The board hung at POST (VGA debug LED) until Re-Size BAR was disabled in firmware
  (BAR1 is now 256 MiB; Strata's speed above is with it off); Gen5 then links. NVIDIA's own 4 × 8-pin adapter on four
  PSU cables powers it. The failed POSTs reset the firmware to defaults, memory speed included, so the 5200 setting
  was restored before any measurement.

**The private 60-task set on the PRO (2026-10-06), one attempt.**
- IQ3_S on v0.1.39 passed 55 of 60 (graded mean 0.995), against 58 for the 4090 on v0.1.38. That comparison changes
  both the card and the Strata version.
- Three of the five misses scored 0.99, each missing one or two output fields; one scored 0.75; one task fails for
  every model.
- On the 54 tasks both passed, the PRO took a median 0.39x the 4090's time (3.65 h of agent time for all 60).

**Stock setup's largest build, UD-Q4_K_XL, on the PRO.**
- Draft `win11-rtxpro6000-ud-q4kxl-131k-strata0.1.39-omp18.5.0` uses stock setup's plan for 191.7 GiB of RAM and
  96 GB of VRAM: the 4090 UD-Q4_K_XL flags plus `--pool-workers 15`, with `--resident-budget-gib 71`.
- It ran from its own root; all 24,576 experts filled the GPU's cache (71.73 GiB).
- One perf run, against IQ3_S's mean above:

| v0.1.39 on the PRO: IQ3_S → UD-Q4_K_XL | 8K | 32K | 64K | 100K |
|---|---|---|---|---|
| decode, tokens/s | 271.0 → 231.1 | 268.4 → 235.0 | 259.3 → 234.9 | 258.4 → 232.2 |
| prefill, tokens/s | 5,764 → 2,494 | 7,918 → 4,858 | 8,044 → 5,487 | 7,784 → 5,703 |
| time to first token, s | 1.48 → 3.33 | 4.26 → 6.85 | 8.46 → 12.25 | 13.64 → 18.31 |

- **Prompt reading, not decode, is what UD-Q4_K_XL costs.** Decode is 0.85-0.90x IQ3_S's; prefill is 0.43-0.73x.
- In an agent-shaped turn, about 1,400 new tokens on a 29,300-token cached prefix with a tool call back, median of 3:
  1.41 s for IQ3_S, 3.12 s for UD-Q4_K_XL. The cold 29,300-token turn: 6.0 s against 13.6 s.

**Terminal-Bench 2.1 on the PRO (2026-10-06/07): IQ3_S against UD-Q4_K_XL, one attempt each.**
- 30 of the benchmark's 89 tasks, stratified by category after excluding those that need over 4 GB of memory or
  over 1 h of agent time, frozen before either build ran. Harbor 0.24.0 runs OMP's metaharness agent with stock omp
  18.5.0 inside each task container (x86 images under emulation in Docker Desktop on a macOS client); the model is
  reached through an SSH tunnel to the host's loopback server. Strata v0.1.39 with each draft's stock flags.

| 30 Terminal-Bench 2.1 tasks, v0.1.39 on the PRO | IQ3_S | UD-Q4_K_XL |
|---|---|---|
| passed | 19 | 19 |
| agent time, all tasks (median a task) | 5.54 h (7.5 min) | 4.84 h (6.1 min) |
| output tokens | 1.93M | 1.70M |
| failed: agent time limit | 5 | 4 |
| failed: wrong or incomplete result | 2 | 3 |
| failed: tool call left in the reasoning | 2 | 1 |
| failed: server stopped at omp's exit | 2 | 2 |
| failed: omp killed (exit 137) | 0 | 1 |

- **A tie.** Both passed 16 and neither 8; each passed 3 that the other failed (exact McNemar p = 1.0). On the 16
  both passed, UD-Q4_K_XL took a median 0.78x IQ3_S's agent time despite its slower prompt reading.
- **Tool call left in the reasoning.** The last turn ended its reasoning with a complete `<tool_call>`. v0.1.39
  returns that as reasoning text, so OMP received a turn with reasoning only. OMP retries such a stop with a reminder,
  but in all three runs it had already restarted once (a reasoning-only continuation in two, a thinking-loop retry in
  one), and 18.5.0 then dropped the retry: `agent_end` with `isTerminal: false`, exit 0, task unfinished. OMP 18.5.1
  fixed that; a scripted server reproduces it on 18.5.0 (3 of 4 requests sent) and not on 18.7.0 (all 4). Strata
  v0.1.40 (#804) and v0.1.40.1 turn a closed call that ends the reasoning into a real call; the three stranded calls
  have that shape. Neither fix has run on these tasks.
- **Server stopped at omp's exit.** In `hf-model-inference` and `kv-store-grpc` both builds solved the task and
  checked their own server, but started it as an OMP named service. OMP's service broker stops non-detached services
  3 s after its last client disconnects, and the bash tool's background jobs die with its shells; the verifier
  connects later. Servers that detach themselves survive. Stock `OMP_DAEMON_IDLE_GRACE_MS` sets that grace: with
  120000 a scripted service still listened 8 s after `omp -p` exited, on 18.5.0 and 18.7.0, and without it it was
  gone. This is the harness, the same for both builds.
- **omp killed.** In `train-fasttext` (a 4 GB, one-CPU container) omp died with exit 137 while the model's own grid
  search ran; IQ3_S hit the time limit on that task.
- **Sustained load over both runs (327 busy minutes):** GPU power 426 W median, 464 W p95, 501 W max; core 79 °C,
  hotspot 85 °C and hottest memory chip 86 °C at most; PCIe Gen5 in all but 3 of 3,919 busy samples; no thermal
  slowdown flag.

</details>

## Strata v0.1.39 against v0.1.38 (2026-10-05): stock OMP 18.5.0

<details>
<summary>Draft comparisons: alternating v0.1.39 vs v0.1.38 perf probes and private task-set runs (2026-10-05)</summary>

Draft profiles `win11-rtx3090-iq3s-131k-strata0.1.39-omp18.5.0`, `win11-rtx3090-coder-iq1m-131k-strata0.1.39-omp18.5.0`
and `win11-rtx4090-iq3s-131k-strata0.1.39-omp18.5.0`, each installed by the guarded install into its own root beside
its 0.1.38 root, with the same model shards (hard links); no gate ran and every ledger stays draft. Against 0.1.38
only the engine changes, except on rtx4090-win-a: its i9-14900K has 8 performance and 16 efficiency cores, so stock
setup v0.1.39 adds `--pool-workers 15` (#642; the engine's own default is one worker per physical core but the
host's, 23 here). rtx3090-win-a's CPU has no efficiency cores. `scripts/perf_probe.py` ran the versions alternately
on each card within an hour, each from a fresh server start (rtx3090-win-a: 0.1.39, 0.1.38, 0.1.38, 0.1.39;
rtx4090-win-a: 0.1.39, 0.1.38, 0.1.39, 0.1.38).

| Decode, tokens/s, mean of 2 runs: 0.1.38 → 0.1.39 | 8K | 32K | 64K | 100K |
|---|---|---|---|---|
| rtx3090-win-a, IQ3_S 131K | 85.1 → 89.1 | 85.8 → 88.4 | 82.8 → 88.4 | 83.4 → 87.0 |
| rtx3090-win-a, Coder IQ1_M 131K | 99.5 → 106.8 | 99.7 → 109.5 | 99.0 → 104.0 | 101.0 → 111.3 |
| rtx4090-win-a, IQ3_S 131K (0.1.39 with `--pool-workers 15`) | 111.4 → 116.2 | 113.6 → 116.4 | 111.5 → 116.3 | 110.6 → 115.0 |

- **On rtx3090-win-a 0.1.39 decodes 3-7% faster with IQ3_S and 5-10% with the Coder.** At 11 of 12 depth points every
  0.1.39 run beat every 0.1.38 run. Prefill and time to first token move by 1-3%, within the runs' spread. The release
  notes claim +2.5-7% decode.
- **On rtx4090-win-a the hybrid-CPU worker count shows no clear gain.** 0.1.39 with stock's 15 workers averaged 2-4%
  faster, but each version's two runs differ by up to 11 tokens/s and the ranges overlap at every depth. #642 reports
  165 / 116 against 106 / 84 tokens/s for 15 against 23 workers on an i9-14900KF; this IQ3_S profile does not
  reproduce that.
- **Both rtx4090-win-a versions ran 12-15% below the same 0.1.38 profile two days earlier** (126-136 tokens/s,
  below), on the same boot and the same DDR5-5200 setting. The alternating runs compare the versions; the host's
  absolute speed had drifted.
- Both installs passed the guarded install's checks of stock setup's generated config, including the planned
  `--pool-workers 15` on rtx4090-win-a, and each server started in 30-46 s.

On the private task set (one attempt each, budgets and OMP binary unchanged):

- **The Coder on 0.1.39 kept its outcomes and was faster on agent work.** It ran the 44 base tasks of its 0.1.38
  first attempt, on the same rtx3090-win-a (whose 0.1.38 speed today matches 2026-10-03 within 3%): 42/44 against
  43/44 (its second 0.1.38 attempt, on the RTX 5090: 42/44). On the 41 tasks both versions passed, 0.1.39 took a
  median 0.84× the time (quartiles 0.75-1.11, summed 0.89×), faster on 27 of 41 (sign test p = 0.06).
- **Both of its 0.1.39 failures ended in OMP's thinking-loop detector** (exact cycles of 63 and 164 characters;
  retries are off), as one 0.1.38 base attempt and two RTX 5090 attempts did; 0.1.39's repeat-stop change did not
  remove them.
- **IQ3_S on 0.1.39 passed 10 of the 12 screen tasks on rtx4090-win-a**, against 11 for its 0.1.38 attempt:
  pd-hard-02 (score 0.64) and pd-hard-04 (0.995, one field) failed, pd-hard-07 passed. Two attempts of one model
  differ on 6-7 of the 16 hard tasks (below), so this is not a regression signal. Its task times are not compared:
  that host ran 12-15% slower than on the day of the 0.1.38 attempts.

</details>

## The models on the owner's kind of work (2026-10-04): a private 60-task set

<details>
<summary>Comparison-only evaluation: Flash-Next IQ3_S, Coder IQ1_M and Qwen3.8 27B on 60 private tasks (2026-10-04)</summary>

The frozen `synthetic-1` evaluation cannot rank models: five of its six tasks pass for every model tried and the
sixth (tool-loop) fails for every one on the same exact-decimal assertion, so 15/18 against 14/18 is one attempt.
For model choice it is replaced by a private task set written for the owner's two kinds of local work, kept outside
the repository with its results; only aggregates appear here. `scripts/eval_taskset.py` ran it
([OPERATIONS.md](OPERATIONS.md#comparing-models-on-a-private-task-set)).

- **Tasks.** Each is a prompt, a starting workspace, hidden expected material, a reference solution and a verifier,
  and each passed the fairness check before any model ran: the untouched start fails its verifier and the reference
  passes, both through the agents' sandbox. Development (26), in a private TypeScript monorepo with its full
  toolchain: 6 replays of real commits, 14 reimplementations of a removed function against hidden tests, and 6
  features from the repository's roadmap, each checked by 30-37 hidden tests. Private data (34), on synthetic
  statements, workbooks and planning documents only: 8 analysis, 8 spreadsheet and 8 diagnosis-and-repair tasks, 5
  programs over a year of multi-format statements with thousands of records, and 5 judgment tasks across
  capital-account and planning documents. The roadmap features, statement programs and judgment tasks (16) are the
  hard tier, added when the first base results showed a ceiling; a separate solver that saw only the agent's inputs
  passed each hard private-data task. Pass means every verifier check is exact.
- **Arms.** Qwen3.8 27B on omp-ninfer v0.10.0, the RTX 5090's production lane (Responses API); the original
  Qwen3.8-Flash-Next at IQ3_S on stock Strata v0.1.38 (draft profile), RTX 4090 with 192 GB; the Flash-Next Coder
  IQ1_M on stock Strata v0.1.38, base tier on the RTX 3090 and hard tier on the RTX 5090. One attempt per model and
  task, through one pinned stock OMP 18.5.0 binary on the macOS client under `sandbox-exec`, each engine reached
  over an SSH tunnel the runner owns. Budgets: 1,350 s and 120 tool calls (private data), 1,800 s and 150
  (development; 2,700 s and 200 for two long replays), 2,700 s and 250 (hard tier).

| Measure | Flash-Next IQ3_S | Flash-Next Coder IQ1_M | Qwen3.8 27B (NInfer) |
|---|---|---|---|
| Passed, all 60 tasks | **58** | **54** | **49** |
| Base tier (44) | 44 | 43 | 39 |
| Hard tier (16) | 14 | 11 | 10 |
| Development (26) / private data (34) | 26 / 32 | 23 / 31 | 20 / 29 |
| Hard tier: roadmap features (6) / statement programs (5) / judgment (5) | 6 / 5 / 3 | 4 / 3 / 4 | 3 / 4 / 3 |
| Median agent time, base / hard | 271 s / 1,010 s (RTX 4090) | 329 s (RTX 3090) / 510 s (RTX 5090) | 151 s / 599 s (RTX 5090) |
| Output tokens, all attempts | 2.06M | 2.29M | 2.18M |

| Pair, all 60 tasks | Both pass / first only / second only / neither | Exact McNemar p |
|---|---|---|
| IQ3_S, 27B | 49 / 9 / 0 / 2 | 0.004 |
| IQ3_S, Coder | 53 / 5 / 1 / 1 | 0.22 |
| Coder, 27B | 46 / 8 / 3 / 3 | 0.23 |

- **Flash-Next beats the 27B on this work.** IQ3_S passed every task the 27B passed and nine more, four of them in
  the hard tier; p = 0.004 holds after a Bonferroni correction for the three comparisons. The Coder's lead over the
  27B (8 to 3) and IQ3_S's over the Coder (5 to 1) point the same way but are within chance at this size.
- **The base tier is at the ceiling for both Flash-Next models; the hard tier separates them.** Every hard
  private-data failure, in all three arms, was a near miss: 2 to 96 of 376-1,847 exact checks failed (for example
  a copied mark written `557.80` where the task requires the canonical `557.8`, or the funds or quarters of one
  summary), which the all-exact rule counts as a failure.
- **Two of the 27B's eleven failures ended at the serving layer.** In two hard development attempts the 27B wrote a
  tool call with a duplicated parameter; NInfer returned it as message text, so OMP took it for the final answer and
  the attempt ended mid-task. The rest are wrong results, near misses and one tool-call budget. The Coder lost one
  base attempt to OMP's repetition detector (a 76-character cycle repeated 15 times; retries are off in this
  configuration) and one hard attempt to the tool-call budget.
- **In the first attempts, on the same GPU the Coder on Strata finished hard tasks faster than the 27B on NInfer**:
  a median 0.79× of its time over the eight hard tasks both passed (4,012 s against 4,873 s summed), the reverse of
  the frozen evaluation's 1.39×. Hard attempts reach about 110K tokens of context in every arm (base attempts a
  median 58-70K); consistent with, though not isolated as, Strata's 3-4× faster long-prompt reading measured below.
  Every other time compares different GPUs: IQ3_S on the RTX 4090 took a median 1.53× (hard) and 1.85× (base) the
  27B's RTX 5090 time on the tasks both passed.
- **Two IQ3_S attempts lost their SSH tunnel to the RTX 4090 mid-stream; both reruns passed.** The first had been
  scored as a model failure, because the check after the attempt silently reopened the tunnel; the runner now counts
  a tunnel that closed during an attempt as an infrastructure fault and reruns it (the second case). No solo
  attempt reached its wall-clock budget.
- **A lead delegates only when each request asks it to, and then gained nothing here.** Fleet arms ran the hard
  tier with OMP's `task` and `wait` tools and every stock agent type routed through `task.agentModelOverrides` to
  IQ3_S (RTX 4090) or the Coder (RTX 3090). With stock prompts the 27B lead on the RTX 5090 made no subagent call
  in 13 attempts; told to delegate in an appended system prompt, it made none in 3 more, and neither did the Coder
  lead in a partial attempt. With a request to use its subagents appended to every task, the Coder lead on the RTX
  5090 delegated in 12 of 13 attempts (34 subagent runs: 29 `scout`, 4 `reviewer`, 1 `task`) and passed 7 against
  the solo Coder's 8 on those tasks (2 and 3 discordant), at a median 1.54× the solo time (12,404 s against
  8,192 s; one attempt ran into its 2,700 s budget after writing a passing result). Two of its attempts ended in
  OMP's repetition detector, against one in the solo Coder's 60. The runs stopped short of 16 tasks when the RTX
  3090 was needed elsewhere.
- **Single attempts are noisy on the hard tier.** The stock fleet arm is in effect a second attempt of the 27B:
  5 of its 13 outcomes differ from the solo attempt (2 and 3 each way). Two more of its attempts ended on a tool
  call returned as text, four of the 27B's 29 hard attempts in all. The repeats below measure this directly.
- **Limits.** One attempt per task for IQ3_S, two for the Coder and the 27B (below); the arms ran on different
  GPUs except the Coder's and the 27B's RTX 5090 attempts; the agent wrote the tasks from the owner's repository
  and documents, and their difficulty is its estimate.

**A second attempt on one GPU (2026-10-05).** The Coder (Strata) and the 27B (NInfer) each ran all 60 tasks again
on the RTX 5090 with the same budgets and binary; the Coder's first base attempts had run on the RTX 3090. Per task
the two attempts give a pass count of 0, 1 or 2; they are not pooled as extra samples.

| Two attempts per task | Flash-Next Coder IQ1_M (Strata) | Qwen3.8 27B (NInfer) |
|---|---|---|
| Passed, first / second attempt | 54 / 53 | 49 / 50 |
| Tasks passed in both / one / neither attempt | 49 / 9 / 2 | 44 / 11 / 5 |
| Base tier (44): both / one / neither | 41 / 3 / 0 | 39 / 4 / 1 |
| Hard tier (16): both / one / neither | 8 / 6 / 2 | 5 / 7 / 4 |
| Hard tier passes, first / second attempt | 11 / 11 | 10 / 7 |
| Agent time on the RTX 5090, per-task means summed | 18,712 s | 20,823 s |

- **On one GPU the Coder still leads, within chance.** Per task it did better on 11 tasks and worse on 5 (44 equal;
  sign test p = 0.21); mean pass rate 89.2% against 82.5%, a 6.7-point difference with a task-bootstrap 95% interval
  of -0.8 to +14.2 points. Its time per task was a median 0.90× the 27B's (0.87× on the hard tier); on the 40 tasks
  every attempt of both passed, the sums are equal (8,236 s against 8,250 s; median 0.93×).
- **9 of the Coder's and 11 of the 27B's 60 tasks changed outcome between attempts** (6 and 7 of the 16 hard
  tasks). One attempt per task cannot separate configurations a few tasks apart.
- **Failure modes in the second attempts.** The 27B returned no tool call as text this time (two of its first
  attempt's eleven failures did); one attempt overran NInfer's 131,072-token context once, continued, and ended as
  a near miss. Two Coder attempts ended in OMP's thinking-loop detector (cycles of 79 and 378 characters repeated 13×
  and 3×; retries are off), three of its 120 attempts in all, and one ended when the model wrote a malformed
  `<tool_call>` as its final text. The rest of both arms' failures are wrong results and near misses.

</details>

## Fifth tuple and Strata against NInfer (2026-10-03): stock Strata v0.1.38, stock OMP 18.5.0

<details>
<summary>Draft fifth-tuple setup choices, v0.1.38 throughput by root and same-prompt client speed (2026-10-03)</summary>

Draft profiles `win11-<gpu>-<model>-<context>-strata0.1.38-omp18.5.0`, each installed into its own root by the
guarded install with stock setup's choices; the Coder roots ran G10 (published, binding each install), every root
ran `scripts/perf_probe.py` (one request per depth, 512 output tokens, server-reported). Nothing here is a
qualification: every ledger stays draft. The NInfer side is what each host already runs: omp-ninfer v0.10.0 in its
Docker Desktop container on the RTX 5090 (image `sha256:fff4ee38…`, profile `qwen38-5090-v0.10.0`) and the native
Windows release `qwen38-3090-native-v0.6.2-beta.1` on the RTX 3090, both serving Qwen3.8 27B (NInfer's mixed
Q4/Q5 build) through its Responses provider. Engine, model, quantization and API all differ, so no comparison below
is engine-only.

### What stock setup picks on each host

| Host, RAM as setup reads it | Stock `--yes` choice | Outcome |
|---|---|---|
| rtx5090-win-a, 47.2 GiB | original model Q2_0, 131K, every expert in VRAM, no KV streaming | start refused: 37.2 GiB available, the profile needs 44 GiB at start (Docker's WSL VM keeps RAM after NInfer stops) |
| rtx4090-win-a, 191.7 GiB | original model IQ3_XXS, 131K, INT8 KV, `--kv-resident 32768` | measured below, after a memory fix (DDR5-5200) |
| rtx3090-win-a, 127.7 GiB | original model IQ3_XXS, 131K, INT8 KV, `--kv-resident 32768` | measured below |

### Strata v0.1.38 throughput by root (perf probe)

| Root | Decode at ~60 / 8K / 32K / 64K / 100K tokens | Prefill, 8K-100K | Cold 100K prompt to first token | MTP acceptance |
|---|---|---|---|---|
| rtx5090-win-a, Coder IQ1_M 131K | 176 / 179 / 172 / 167 / 175 tokens/s | 6.3-7.6K tokens/s | 14.1 s | 0.76-0.83 |
| rtx3090-win-a, Coder IQ1_M 131K | 87 / 100 / 99 / 101 / 90 | 2.1-2.6K | 41.2 s | 0.75-0.82 |
| rtx3090-win-a, IQ3_XXS 131K (stock choice) | 78 / 100 / 110 / 95 / 98 | 1.4-1.6K | 69.2 s | 0.80-0.89 |
| rtx3090-win-a, IQ3_S 131K | 67 / 88 / 86 / 84 / 84 | 1.1-1.3K | 85.3 s | 0.85-0.88 |
| rtx4090-win-a, Coder IQ1_M 131K | 127 / 142 / 145 / 149 / 144 | 4.7-5.6K | 19.0 s | 0.75-0.83 |
| rtx4090-win-a, IQ3_XXS 131K (stock choice) | 123 / 159 / 155 / 151 / 155 | 4.4-5.1K | 21.7 s | 0.83-0.89 |
| rtx4090-win-a, IQ3_S 131K | 95 / 136 / 134 / 132 / 126 | 3.9-4.4K | 24.9 s | 0.84-0.90 |
| rtx4090-win-a, Coder IQ1_M 262K | 131 / 147 / 143 / 150 / 130 | 4.6-5.5K | 19.3 s | 0.77-0.89 |
| rtx4090-win-a, IQ3_S 262K | 77 / 116 / 115 / 117 / 114 | 3.8-4.4K | 25.1 s | 0.83-0.88 |
| rtx4090-win-a, Coder IQ1_M 131K, calibrated (`--pcie-frac 0.20 --spec-min-p 0.70`) | 137 / 153 / 152 / 164 / 142 | 4.7-5.6K | 19.2 s | 0.85-0.95 |
| rtx4090-win-a, IQ3_XXS 131K, calibrated (`--pcie-frac 0.00`) | 139 / 172 / 174 / 171 / 164 | 4.3-5.0K | 21.6 s | 0.81-0.85 |

- **The RTX 5090 Coder on v0.1.38**: decode 167-179 tokens/s (v0.1.34: 148-206), cold 100K prompt 14.1 s (about
  16 s).
- **On the RTX 3090 the stock choice decodes like the Coder and prefills at 60% of its rate.** IQ3_XXS is the
  original model (twice the Coder's experts). IQ3_S, the best-quality original size, decodes 84-88 tokens/s against
  93-96 on v0.1.36 with the same generated flags (one probe each).
- **On the RTX 4090 with 192 GB the stock choice is the fastest decoder**: IQ3_XXS 151-159 tokens/s from 8K to 100K
  tokens, the Coder 142-149 with 7-10% faster prefill. With every expert in RAM the Coder decodes 144 tokens/s at
  100K tokens, against 86-118 in the 32 GiB low-RAM mode's near-limit requests (v0.1.34, G17); the cold 100K prompt
  barely moves (19.0 s against 20.9 s), so RAM never limited prefill.
- **At 262K the Coder costs nothing below 100K and keeps decoding at 125-131 tokens/s at 200K-250K**; a cold
  256,000-token prompt takes 53.9 s. IQ3_S at 262K decodes 105-117 tokens/s, 10-15% below its 131K root, and its cold
  256K prompt takes 67.6 s.
- **Calibration adds decode on this host and nothing in prefill** (one probe each, details below): IQ3_XXS 6-13% at
  every depth, now 164-174 tokens/s from 8K to 100K; the Coder 5-10% up to 64K and nothing at 100K. The best RTX 4090
  settings measured: calibrated IQ3_XXS 131K for decode, the calibrated Coder 131K for long prompts and coding (the
  evaluated model), the Coder 262K when a session needs more than 131K tokens.

### Client-side speed, same prompts on both engines

`scripts/probe_g25_speed.py`, one prompt set per host (filler at the nominal depth plus one instruction; 3 runs per
depth, output capped at 512 tokens, medians). TTFT is dispatch to the first streamed token of any kind; the output
rate is completion tokens over the time after it.

| Host | Engine | TTFT at ~0 / 8K / 32K / 100K tokens | Output tokens/s at the same depths |
|---|---|---|---|
| rtx5090-win-a | NInfer v0.10.0 | 0.12 / 2.55 / 10.96 / 42.77 s | 250 / 204 / 189 / 124 |
| rtx5090-win-a | Strata, Coder | 0.21 / 1.34 / 4.55 / 14.08 s | 145 / 149 / 135 / 137 |
| rtx4090-win-a | NInfer v0.6.10 | 0.15 / 3.69 / 15.84 / 62.48 s | 134 / 129 / 120 / 97 |
| rtx4090-win-a | Strata, Coder | 0.34 / 2.01 / 6.37 / 19.37 s | 124 / 128 / 121 / 117 |
| rtx3090-win-a | NInfer v0.6.2 | 0.23 / 9.42 / 40.79 / 160.37 s | 81 / 70 / 69 / 58 |
| rtx3090-win-a | Strata, Coder | 0.77 / 4.64 / 13.53 / 40.90 s | 86 / 88 / 87 / 79 |

- **Strata reads long prompts 3-4× faster on every GPU** (3.2× on the RTX 4090 at 100K). NInfer prefills about 2.4K
  tokens/s on the RTX 5090, 1.6K on the RTX 4090 and 0.65K on the RTX 3090 at 100K.
- **NInfer generates faster on the RTX 5090 up to 32K** (250 against 145 tokens/s on a short prompt) and slower at
  100K; on the RTX 4090 the two stay within 8% of each other up to 32K and Strata is 21% faster at 100K. NInfer's 512
  tokens were all reasoning (the provider's low effort), Strata's 289-381 visible answer tokens, so output lengths
  differ; the rates are not a matched benchmark.
- The RTX 4090's first pair asked NInfer for the RTX 3090 lane's model id and got HTTP 404 on every sample; its
  NInfer half was rerun with the lane's id (`qwen3.8-27b`) on the same prompt set after the comparison. The probe now
  checks the endpoint's model list before any sample.

</details>

### Paired coding evaluation against NInfer (G25)

<details>
<summary>Paired G25 results across three GPUs and RTX 4090 192 GB memory validation (2026-10-03)</summary>

The frozen `synthetic-1` evaluation through one pinned stock OMP 18.5.0 binary on both arms, six exclusive windows
per host in the order Strata, NInfer, NInfer, Strata, Strata, NInfer, after a six-attempt pilot per arm (Strata 5/6
and NInfer 5/6 on the RTX 5090, 5/6 and 4/6 on the RTX 4090, 5/6 and 3/6 on the RTX 3090). Every engine start was
cold. Runs `g25-rtx5090-20261003f`, `g25-rtx4090-20261003a` and `g25-rtx3090-20261003e`; exported plans, window
aggregates, paired summaries and G25 receipts are in each release's `evidence/` and `receipts/`. All three ran on the
hosts' normal accounts, not a restricted evaluation account.

| Measure | RTX 5090: Strata | RTX 5090: NInfer v0.10.0 | RTX 4090: Strata | RTX 4090: NInfer v0.6.10 | RTX 3090: Strata | RTX 3090: NInfer v0.6.2 |
|---|---|---|---|---|---|---|
| Verified completions | **15/18** | **14/18** | **15/18** | **15/18** | **15/18** | **15/18** |
| Pairs: both pass / Strata only / NInfer only / neither | 14 / 1 / 0 / 3 | | 15 / 0 / 0 / 3 | | 15 / 0 / 0 / 3 | |
| Median task wall, all attempts | 36.4 s | 29.1 s | 47.4 s | 49.2 s | 85.5 s | 88.7 s |
| Median task wall, verified passes | 34.7 s | 27.2 s | 46.1 s | 46.1 s | 83.0 s | 83.4 s |
| Summed task wall, all 18 attempts | 839 s | 733 s | 1,133 s | 1,231 s | 1,905 s | 2,028 s |
| Median Strata/NInfer ratio over jointly passed pairs | 1.39 (14 pairs) | | 0.98 (15 pairs) | | 0.98 (15 pairs) | |
| Output tokens, all attempts | 117K | 137K | 115K | 133K | 127K | 126K |
| Cold start to ready | 14.4-14.9 s | 34.7-35.1 s | 14.8-17.5 s | 34.3-74.8 s | 24.2-26.1 s | 113.2-115.8 s |
| GPU memory while serving | 30,836 MiB | 29,472 MiB | 23,329 MiB¹ | 23,162 MiB¹ | 23,443 MiB | 22,970 MiB |
| GPU power limit | 600 W (default) | 600 W (default) | 500 W¹ (card maximum; default 450 W) | 500 W¹ | 370 W (default) | 300 W (NInfer's qualified limit) |
| Lowest available RAM | 8.2 GiB | 8.3 GiB | 153.2 GiB | 165.3 GiB | 91.2 GiB | 106.2 GiB |

¹ Sampled outside the RTX 4090's comparison windows: Strata's memory during its G10 run on the same root, NInfer's
memory and both power limits during the speed probe and calibration right after the comparison. NInfer's 4090 lane
manages no power cap.

| Task: passes, median wall | RTX 5090: Strata | RTX 5090: NInfer | RTX 4090: Strata | RTX 4090: NInfer | RTX 3090: Strata | RTX 3090: NInfer |
|---|---|---|---|---|---|---|
| bugfix-a | 3/3, 29.7 s | 2/3, 29.7 s | 3/3, 40.4 s | 3/3, 36.9 s | 3/3, 67.7 s | 3/3, 62.9 s |
| bugfix-b | 3/3, 86.1 s | 3/3, 18.5 s | 3/3, 80.1 s | 3/3, 105.8 s | 3/3, 159.4 s | 3/3, 103.4 s |
| multifile-regression | 3/3, 44.8 s | 3/3, 30.8 s | 3/3, 46.5 s | 3/3, 46.1 s | 3/3, 72.3 s | 3/3, 94.0 s |
| tool-loop | 0/3, 65.5 s | 0/3, 70.7 s | 0/3, 100.0 s | 0/3, 98.0 s | 0/3, 111.8 s | 0/3, 195.6 s |
| long-context | 3/3, 26.7 s | 3/3, 22.0 s | 3/3, 43.4 s | 3/3, 40.6 s | 3/3, 83.2 s | 3/3, 93.4 s |
| continuation | 3/3, 32.2 s | 3/3, 25.9 s | 3/3, 36.3 s | 3/3, 46.0 s | 3/3, 87.7 s | 3/3, 78.3 s |

- **Neither frozen claim holds on any GPU.** Higher completion needs three more Strata passes; faster needs a
  median ratio of at most 0.80 and no greater Strata total. The RTX 5090's 15/18 against 14/18 is one bugfix-a
  attempt; tool-loop failed every attempt on both engines on every GPU.
- **On the RTX 5090 NInfer is faster on these tasks**: Strata's paired median took 1.39× NInfer's, its summed wall
  1.14×. The largest gap is bugfix-b, where the Coder wrote 12.6K output tokens (median) against NInfer's 3.4K; on
  the other tasks the outputs are similar and Strata took 0-45% longer (tool-loop 7% less), in line with NInfer's
  faster decode up to 32K.
- **On the RTX 4090 and RTX 3090 the two are even** (paired median 0.98 on both; Strata 8% and 6% less summed
  wall). On the RTX 4090 Strata was faster on bugfix-b, where NInfer wrote 12.3K output tokens (median) against
  8.2K, and on continuation; NInfer was 2-9% faster on bugfix-a, long-context and tool-loop. On the RTX 3090 Strata
  was faster on multifile-regression, long-context and tool-loop, NInfer on the bugfix tasks and continuation;
  NInfer ran at its own 300 W cap there, Strata at the card's 370 W.
- **Strata restarts 2.4× (RTX 5090), 2-5× (RTX 4090) and 4.5× (RTX 3090) faster.** NInfer's RTX 4090 start took
  34 s in one window and 60-75 s in the other two. No number includes NInfer restoring a saved session or Strata
  re-reading a transcript; switching engines on the RTX 5090 also waited for Docker's VM to return RAM (86-91 s from
  NInfer to Strata).
- NInfer serves Qwen3.8 27B with a 131,072-token context (BF16 KV on the RTX 5090, INT8 on the RTX 4090 and RTX
  3090); Strata the Coder IQ1_M at 131,072 with INT8 KV.

### RTX 4090 with 192 GB: the setting that holds

Host rtx4090-win-a now has 4 × 48 GB of dual-rank DDR5 (191.7 GiB reported), two DIMMs per channel. Its first
setting, DDR5-5600 with voltages on Auto and the board's own CPU power profile, failed under load: four bugchecks in
a night (0xEF; 0x1A twice; and 0x1A 0x403, whose page-table and PFN parameters differ in a single bit), one reset
while idle, wrong SHA-256 results for an unchanged 29.6 GB model shard, and a TLS decryption error in a download.
The owner then changed one BIOS setting at a time; each setting ran the same 25-minute check (three SHA-256
re-hashes of both Coder shards, y-cruncher v0.8.7's stress suite over 160 GB, and a scan for WHEA hardware
errors):

| DRAM | CPU power profile | Result |
|---|---|---|
| 5600, DRAM and memory-controller voltages 1.30 V, SA 1.20 V | board profile | memory training failed twice |
| 5200, voltages Auto | board profile | fail: y-cruncher's SNT test errored on one E-core after 27 s |
| 5200, voltages Auto | Intel Default Settings (PL1 253 W) | **pass**: all hashes, all 8 stress tests, no WHEA error |
| 5600, voltages Auto | Intel Default Settings | fail: one wrong hash and the same E-core error |

The kit's EXPO profile (DDR5-6000, 1.40 V) never trains with four DIMMs; Intel validates this CPU at DDR5-3600 with
two dual-rank DIMMs per channel. The host runs at **DDR5-5200 with Intel Default Settings**, and every RTX 4090 figure
in this section was taken there: seven root installs with their probes, the paired comparison and calibration kept it
loaded for 3 h 20 min with no bugcheck and no WHEA error (its only WHEA record is the informational one logged at
every boot). The same E-core failed first in both failing settings; if it fails again, the CPU is the next suspect.

</details>

## Stock calibration on three GPUs (2026-10-03)

<details>
<summary>Stock calibration sweeps and calibrated vs uncalibrated draft probes (2026-10-03)</summary>

Stock setup's last interactive question, `Tune Strata for this PC now?`, defaults to yes and runs
`tools/calibrate.py`; `--yes` installs skip it, and so does the guarded install, so every other figure in this file
ran with the engine's defaults. The stock tool, run unchanged against an installed root's generated config with the
server stopped, measures decode on three short prompts (128 tokens, temperature 0, thinking off) for a sweep of PCIe
shares and draft floors, re-measures the best pair interleaved with the default three times, then restarts the
engine with fewer CPU workers. It keeps a setting only when it is more than 3% faster. The engine already adapts
the PCIe share to the link: it probes host-to-device bandwidth at start and scales its 0.55 default down below
20 GB/s (the RTX 3090's Gen3 x8 link measured 6.2 GB/s: share 0.13).

| Host and root | Engine defaults: PCIe share, draft floor, CPU workers | Kept by stock calibration | Interleaved decode, default vs best pair | Run |
|---|---|---|---|---|
| rtx5090-win-a, Coder 131K (v0.1.34) | 0.55, 0.5, 15 | nothing | 169.9 vs 171.6 tokens/s (+1.0%, 0.20 / 0.70) | 129 s |
| rtx4090-win-a, Coder 131K low-RAM (v0.1.34) | 0.55, 0.5, 23 | nothing | the best pair is the default | 185 s |
| rtx3090-win-a, Coder 131K (v0.1.34) | 0.13, 0.5, 9 | nothing | 94.7 vs 93.8 (0.20 / 0.70) | 215 s |
| rtx3090-win-a, IQ3_S 131K (v0.1.36) | 0.13, 0.5, 9 | `--pcie-frac 0.20 --spec-min-p 0.70` | 68.3 → 74.4 (+8.9%) | 327 s |
| rtx3090-win-a, IQ3_S 262K (v0.1.36) | 0.13, 0.5, 9 | `--pcie-frac 0.20 --spec-min-p 0.70` | 69.0 → 71.5 (+3.6%) | 316 s |
| rtx4090-win-a, Coder 131K, 192 GB (v0.1.38) | 0.55, 0.5, 23 | `--pcie-frac 0.20 --spec-min-p 0.70` | 116.7 → 138.5 (+18.6%) | 147 s |
| rtx4090-win-a, IQ3_XXS 131K, 192 GB (v0.1.38) | 0.55, 0.5, 23 | `--pcie-frac 0.00` | 98.9 → 129.5 (+31.0%) | 196 s |

- **For the Coder on the RTX 5090, the low-RAM RTX 4090 and the RTX 3090, the configuration measured everywhere
  else in this file already is the calibrated one.** With 192 GB the RTX 4090 keeps a lower PCIe share for both
  roots measured.
- **PCIe share matters most, and only where experts miss the GPU.** Single-sweep decode at shares 0 / 0.20 / 0.35 /
  0.55 / 0.75: RTX 3090 Coder 91 / 96 / 84 / 76 / 66 tokens/s (94 at its 0.13), RTX 3090 IQ3_S 67 / 68 / 55 / 42 /
  36 (66 at 0.13), RTX 4090 low-RAM Coder 114 / 114 / 119 / 120 / 118, RTX 4090 192 GB Coder 137 / 139 / 134 / 114
  / 106 and IQ3_XXS 133 / 131 / 116 / 100 / 87, RTX 5090 169-170 at every share.
- **Fewer CPU workers were slower** on both 24 GB hosts (RTX 3090 Coder 9 / 6 / 4 workers: 92.2 / 88.2 / 81.7;
  RTX 4090 low-RAM 23 / 15 / 12: 113.8 / 109.5 / 107.2; with 192 GB IQ3_XXS 131.1 / 127.4 / 124.7) and made no
  difference for the 192 GB RTX 4090's Coder (134.6 / 136.5 / 135.3) or on the RTX 5090 (169.6 at 15, 10 and 8).
- These are the stock tool's short-prompt rates, not comparable with the perf probe's.

**Calibrated against uncalibrated on the RTX 4090 with 192 GB.** Drafts
`win11-rtx4090-coder-iq1m-131k-calibrated-strata0.1.38-omp18.5.0` and
`win11-rtx4090-iq3xxs-131k-calibrated-strata0.1.38-omp18.5.0` pin the kept settings; each was installed in its own
root by stock setup with stock `calibrate.apply` and probed (throughput table above). Decode: IQ3_XXS 6-13% faster
at every depth, the Coder 5-10% faster up to 64K and level at 100K; the Coder's MTP acceptance rises from 0.75-0.83
to 0.85-0.95 with the 0.70 draft floor. Prefill and the cold 100K prompt do not move (19.2 s against 19.0 s, 21.6 s
against 21.7 s). The uncalibrated roots were probed about three hours earlier on the same boot, not straight
after; gains under about 5% are inside run-to-run spread (the RTX 3090's two uncalibrated IQ3_S probes differed by
up to 5.6%).

**Calibrated against uncalibrated IQ3_S 131K on the RTX 3090.** Draft
`win11-rtx3090-iq3s-131k-calibrated-strata0.1.36-omp18.4.12` pins the kept pair; its own root was installed by
stock setup with the pair applied by stock `calibrate.apply`, probed, and the uncalibrated root was probed again
straight after (same perf probe, 512 output tokens, one request per depth).

| Context | Decode, calibrated | Decode, uncalibrated (rerun / earlier) | MTP acceptance, calibrated / uncalibrated rerun |
|---|---|---|---|
| ~60 tokens | 74.9 tokens/s | 71.6 / 71.5 | 0.905 / 0.856 |
| 8K | 100.2 | 96.7 / 96.0 | 0.912 / 0.835 |
| 32K | 99.1 | 98.4 / 93.2 | 0.929 / 0.868 |
| 32K repeated (prefix cache) | 98.8 | 98.0 / 95.6 | 0.926 / 0.870 |
| 64K | 96.9 | 97.9 / 95.6 | 0.931 / 0.885 |
| 100K | 93.3 | 92.2 / 94.0 | 0.906 / 0.842 |

- **Decode gains 4-5% up to 8K tokens; from 32K on the difference is inside the spread of the two uncalibrated
  runs** (5.6% at 32K). Prefill and time to first token do not move (cold 100K prompt: 87.9 s against 88.0 s); the
  higher draft floor raises MTP acceptance from 0.84-0.89 to 0.91-0.93.
- **The frozen evaluation scores 15/18 again**, every task as before (tool-loop 0/3). Median task 109.5 s against
  104.8 s, summed task wall 2,034 s against 2,240 s; output length varies more than that between batches (bugfix-a
  wrote 16.1K output tokens against 19.6K), so the evaluation shows no speed difference beyond the probe's.

</details>

## Longer contexts for the Coder on the RTX 3090 (2026-10-03)

<details>
<summary>Draft 262K and YaRN 524K context probes on the RTX 3090 (2026-10-03)</summary>

The model's trained context is 262,144 tokens. Stock setup also offers 393,216 and 524,288 through yarn rope
scaling with the factor context / 262,144, which Strata calls experimental: a scaled run is a slightly different
model at every position, not only past 262,144 (Strata's own runs, one machine and one quant: needle recall at
512K, real-document Q&A 8/8 at 421K). Drafts `win11-rtx3090-coder-iq1m-262k-strata0.1.36-omp18.4.12` (OMP window
261,120) and `win11-rtx3090-coder-iq1m-524k-strata0.1.36-omp18.4.12` (`--rope-scaling yarn --rope-scale 2`, OMP
window 523,264), each installed into its own root by the guarded install and probed with the perf probe (512
output tokens, one request per depth). KV streaming keeps 32K positions per layer in VRAM and the rest in RAM:
3.6 GB at 262K, 7.2 GB at 524K.

| Context depth | Coder 262K: first token / prefill / decode | Coder 524K, yarn 2: first token / prefill / decode |
|---|---|---|
| ~60 tokens | 0.87 s / - / 95.1 tokens/s | 0.95 s / - / 92.2 |
| 32K | 14.4 s / 2.30K tokens/s / 100.5 | 14.6 s / 2.28K / 95.2 |
| 100K | 44.9 s / 2.31K / 98.1 | 45.5 s / 2.28K / 94.9 |
| 200K | 100.4 s / 2.07K / 81.2 | not probed |
| 250K | 138.4 s / 1.87K / 89.0 | 140.4 s / 1.84K / 93.3 |
| 500K (512,000 tokens) | over the window | 402.6 s / 1.28K / 72.1 |

- **The trained 262K costs nothing below 100K**: the Coder decodes as at 131K, and a cold 250K-token prompt takes
  2.3 min (IQ3_S at 262K: 4.1 min).
- **Yarn doubles the window**: a cold 512,000-token prompt takes 6.7 min to its first token and then decodes 72
  tokens/s. Below 100K the scaled model decodes 3-5% slower than the unscaled one.
- **Quality of the scaled model is not measured here.** Its frozen evaluation was stopped after 1 of 18 attempts when
  the host was needed; a scored 524K batch beside a 262K batch is the comparison still owed.

</details>

## RTX 3090 with 128 GB (2026-10-02): which model the RAM unlocks

<details>
<summary>Draft variant-selection measurements: Coder IQ1_M, IQ3_S and UD-Q4_K_XL at 128 GB (2026-10-02)</summary>

Host **rtx3090-win-a** after its RAM upgrade: 4 × 32 GB DDR4-3200 (127.69 GiB reported; it had 64 GiB of
DDR4-2133), an 8 GB page file, the same RTX 3090 and driver 617.14; the desktop was signed out. Stock Strata
v0.1.36's setup offers the original Qwen3.8-Flash-Next as GSQ-RCO Q2_0, IQ2_XS, IQ3_XXS and IQ3_S (its notes: IQ3_S
"matches the full BF16 model on the published benchmarks") and, experimental, Unsloth's UD-Q4_K_XL, whose 71.7 GiB of
routed experts stay in RAM up to a budget of the RAM less 24 GB; the Coder (half of the experts) comes only as IQ1_M.
Before the upgrade IQ3_S ran with 0.72 GB of commit to spare, and UD-Q4_K_XL would have read most experts from the
SSD (7-8.5 tokens/s on Strata's 64 GB test PC). The smaller original sizes already fit 64 GiB and rank below IQ3_S
in quality, so they were not measured.

Draft profiles `win11-rtx3090-iq3s-131k-strata0.1.36-omp18.4.12` and
`win11-rtx3090-ud-q4kxl-131k-strata0.1.36-omp18.4.12` (stock OMP 18.4.12), each installed into its own root by the
guarded install with setup's own choices. The Coder column is the fourth tuple's root
(`win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10`, Strata v0.1.34), probed while a download ran on the same
host. Throughput comes from `scripts/perf_probe.py` (one request per depth, 512 output tokens, server-reported
timings); the evaluation is the frozen `synthetic-1` batch. No gate ran: these are variant-selection measurements,
not receipts, and every ledger stays draft.

| Measure | Coder IQ1_M | IQ3_S | UD-Q4_K_XL |
|---|---|---|---|
| Stock setup choice | every expert in RAM, KV streaming | every expert in RAM, KV streaming | all 71 GiB of experts in RAM (`--resident-budget-gib 71`), KV streaming |
| Decode, 8K-100K context | 101-104 tokens/s | 93-96 tokens/s | 49-50 tokens/s (36 in a logged agent turn) |
| Prefill, 8K-100K context | 1.9-2.5K tokens/s | 1.1-1.2K tokens/s | 0.6-0.7K tokens/s |
| Cold 100K-token prompt to first token | 43.2 s | 88.1 s | 148.6 s |
| Repeated 32K prompt (prefix cache) to first token | 0.30 s | 0.32 s | 0.40 s |
| MTP draft acceptance | not reported by v0.1.34 | 0.82-0.87 | 0.82-0.84 |
| Restart to verified readiness | 33 s | 47-56 s | 112-155 s |
| Scored evaluation | 15/18 (fourth tuple at 64 GiB; tool-loop 0/3) | 15/18 (tool-loop 0/3, every other task 3/3) | 7 of the 11 attempts recorded before the harness crashed (below) |
| Median task wall; batch wall | 81.4 s; 1,498 s (64 GiB) | 104.8 s; 2,240 s | 168 s; no batch summary |

- **IQ3_S is what the RAM unlocks.** At 64 GiB it decoded 56-66 tokens/s at about 105K tokens. With 128 GB stock
  setup streams its KV cache to RAM (that needs 64.8 GiB), and decode at the same depth rises to 94 tokens/s, within
  10% of the Coder. Prefill does not change (85.1 s then, 88.1 s now for 100K tokens) and stays at about half the
  Coder's; the original model has twice the Coder's experts.
- **On the coding evaluation IQ3_S ties the Coder.** Both score 15/18 and fail every tool-loop attempt on the same
  exact-money assertion as before, so the original model's other half of the experts buys nothing on these tasks,
  and its median task takes 29% longer. The Coder stays the faster choice for coding; IQ3_S is the stronger model
  outside coding (Strata: the Coder is "weaker outside coding").
- **IQ3_S also runs at the model's trained 262K context.** `win11-rtx3090-iq3s-262k-strata0.1.36-omp18.4.12` (OMP
  window 261,120) decodes 93-94 tokens/s up to 100K tokens of context and 84-85 at 200K-250K, with MTP acceptance
  0.84-0.89. A cold 256,000-token prompt takes 247 s to its first token (1.0-1.2K tokens/s), a repeated one 0.3 s;
  start to readiness took 31 s. A restart replays the whole transcript and pays that; turns that extend a cached
  prefix do not.
- **More RAM does not speed up the Coder.** Its 100K cold prefill took 43.2 s against 44.0 s at 64 GiB (G17): every
  expert was already in RAM, and RAM 50% faster (DDR4-3200 against 2133) did not move prefill, so RAM was not its
  bound.
- **UD-Q4_K_XL runs, but slowly.** With every expert in RAM it decodes 49-50 tokens/s, against the 7-8.5 Strata
  measured with most experts on the SSD (64 GB, RTX 5070), yet half as fast as IQ3_S; it prefills at 0.6-0.7K
  tokens/s and takes 2-2.5 min to restart. Its recorded attempts failed tool-loop (0/2) on the same exact-money
  assertion as the other models, and one of two multifile-regression attempts.
- **The frozen evaluation cannot score a profile whose restart takes over 120 s.** The continuation task restarts the
  server between its phases and gives that hook 120 s; UD-Q4_K_XL's first continuation attempt failed on the cap. On
  the second, the harness's `taskkill` of the slow restart hit its own 10 s timeout, and the uncaught `TimeoutExpired`
  ended the batch before its summary was written. `scripts/evaluate.py` and `eval/support.py` are frozen; this is
  recorded, not patched.

</details>

## Fourth tuple on three GPUs (2026-10-02–03): stock Strata v0.1.34, stock OMP 18.4.10

<details>
<summary>Earlier qualified history (first qualified tuple): resources, throughput, G15 repeats and G24 (2026-10-02–03)</summary>

The first qualified tuple: every applicable gate passes, including G04's cut-off tool call on stock releases.
G22, G23 and G25 are not applicable to these local, transcript-replay profiles. Ledgers, receipts and scrubbed
results: [RTX 3090](../releases/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
[RTX 4090, low-RAM](../releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json).

Each host used a separate integration root, Qwen3.8-Flash-Next Coder IQ1_M, a 131,072-token context, INT8 KV and
stock MTP speculation. The 2026-10-02 main runs used the RTX 3090's **64 GiB** configuration before its RAM upgrade,
the RTX 4090's 32 GiB stock low-RAM configuration, and the RTX 5090's 47.15 GiB configuration. Hardware and setup
choices otherwise match the earlier sections. The RTX 3090's later 128 GB variant-selection measurements above
are not substituted for these qualification measurements.

### Resources (G10, G21)

GB is decimal; GPU memory is MiB. Engine peaks below are the lifetime peaks of the process sampled by G21, not a
maximum across restarted processes. RAM minima include the 2026-10-02 gate samples and compaction rerun, not the
2026-10-03 G15 repeats.

| Measure | RTX 3090, 64 GiB | RTX 4090, 32 GiB, low-RAM | RTX 5090, 47.15 GiB | Boundary |
|---|---|---|---|---|
| GPU memory in use while serving | 23,277 MiB | 23,322 MiB | 30,742 MiB | G10 sampler |
| Engine working-set lifetime peak | 30.27 GB | 27.84 GB | 30.54 GB | G21 per-process peak |
| Engine private-commit lifetime peak | 55.15 GB | 28.15 GB | 63.35 GB | G21 per-process peak |
| Minimum available system RAM | 31.81 GB | **0.44 GB** | 8.87 GB | gate samplers |
| Integration root on disk | 73.8 GB | 99.0 GB | 73.8 GB | G21 file sizes |
| Start to verified readiness | 18.9 s | 14.7 s | 14.7 s | G21 current server, wall |
| Engine dead/restarted events in the main run | 2 | 2 | 2 | G21 log scan, deliberate G15 kills |

The 32 GiB low-RAM host has almost no spare RAM: its passing gates do not establish capacity for other workloads.
G26 also passed each new-root install, start, launch example, project tests and stop, with 3/3 tracer runs; these
were additional installations on the same hosts, not fresh operating systems or byte-identical copies of an older
root. G13 recorded zero non-loopback ETW events on all three hosts.

### Throughput (G17, server-reported)

| Case | RTX 3090 | RTX 4090, low-RAM | RTX 5090 |
|---|---|---|---|
| Cold prefill, 100,030 tokens | 44,048 ms (2.3K tokens/s) | 20,850 ms (4.8K tokens/s) | 15,696 ms (6.4K tokens/s) |
| Cached continuation at ~105K tokens, prompt time | 1,161–1,297 ms | 464–601 ms | 248–284 ms |
| Decode in the three near-limit requests | 84.6–99.4 tokens/s | 86.4–117.5 tokens/s | 150.0–154.8 tokens/s |

These are the qualification requests, not a matched output-length throughput benchmark. Prefix reuse still
belongs to the live engine; restarting it loses that prefix and pays cold prefill again.

### Agent turns, restarts and context (G11–G19)

| Case | RTX 3090 | RTX 4090, low-RAM | RTX 5090 |
|---|---|---|---|
| Tracer runs (typed tools and transcript recall) | 3/3 | 3/3 | 3/3 |
| Same-session prefix reuse | 12/12 continuations | 12/12 continuations | 12/12 continuations |
| Generating cancel to idle | 86 ms | 95 ms | 79 ms |
| Queued drop, then active drop, to idle | 273 ms | 271 ms | 272 ms |
| Engine killed while idle: next turn, passing G15 | 21.0 s | 31.8 s | 15.1 s |
| Engine killed mid-generation: next turn, passing G15 | 21.7 s | 31.2 s | 14.8 s |
| Client restart: next turn (G16) | 2.2 s | 1.4 s | 1.2 s |
| Client and full server restarted: next turn (G16) | 8.1 s | 19.5 s | 3.4 s |
| Exact server limit and explicit overflow (G17) | pass | pass | pass |
| Production compaction, main run (G18L) | 114,383 → 30,633 tokens | 113,058 → 30,351 tokens | 112,664 → 30,158 tokens |

The G16 next-turn times exclude the preceding server stop/start; they are not total restart-to-answer latency.
The G15 rows use the corrected-probe repeats published on 2026-10-03. The RTX 5090 had failed G15 twice; commit
`cb31418` withdraws the interrupted essay before asking for recall (`RECALL_AFTER_INTERRUPT`), and
`g15-20261003T032448Z-de222a` then passed. The RTX 4090 passed both before and after that correction (repeat
`g15-20261003T032520Z-78f0cc`). The RTX 3090 failed once, passed `g15-20261002T032128Z-191f17` with the earlier
probe, and passed the corrected repeat `g15-20261003T043756Z-122117`. Failures remain in each ledger; no engine
patch or durable-state claim is hidden
in the reruns. The RTX 4090 also failed G18's reduced-threshold probe once; the repeat passed, with production
compaction then going from 111,169 to 29,963 tokens. Its first production compaction had already passed.

### Coding evaluation (G24)

The frozen `synthetic-1` set, harness, caps and continuation restart hook are unchanged. Each GPU had a non-scored
six-attempt pilot (5/6, 5/6 and 4/6 respectively), followed by all 18 scheduled scored attempts.

| Task | RTX 3090 | RTX 4090, low-RAM | RTX 5090 |
|---|---|---|---|
| bugfix-a | 3/3 | 3/3 | 3/3 |
| bugfix-b | 3/3 | 3/3 | 3/3 |
| multifile-regression | 3/3 | 3/3 | 3/3 |
| tool-loop | 0/3 | 0/3 | 1/3 |
| long-context | 3/3 | 3/3 | 3/3 |
| continuation | 3/3 | 3/3 | 3/3 |
| **Scored** | **15/18** | **15/18** | **16/18** |
| Median task wall; batch wall | 81.4 s; 1,498 s | 56.3 s; 1,144 s | 39.3 s; 895 s |

Failed tasks remain in the denominator. G24 passes for complete, independently verified reporting, not a perfect
score or a comparison with another runtime. No scored attempt timed out.

</details>

## Third tuple on 24 GB hosts (2026-10-01): stock Strata v0.1.31, stock OMP 18.4.8

<details>
<summary>Unqualified historical rollback installations on RTX 3090 (64 GiB) and RTX 4090 (32 GiB low-RAM) (2026-10-01)</summary>

Draft profiles `win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8` and
`win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8`; receipts and scrubbed results under their
`releases/<profile>/` directories. Boundaries as defined for candidate 1 below. Each host got a fresh integration
root (its first Strata installation) and ran the whole sequence unattended with `scripts/requalify.py`; nothing else
used either GPU. Both GPUs also drive a display (two WDDM graphics clients each, counted by G10).

- **rtx3090-win-a**: RTX 3090 24,576 MiB on PCIe Gen3 x8 under load (x16 maximum), driver 617.14, a 10-core
  AVX-512 CPU, 64 GiB DDR4-2133, a 4.3 GB page file (commit limit minus RAM); the interactive desktop was signed
  out first. Stock setup choices as on the RTX 5090: every expert in RAM, KV streaming on.
- **rtx4090-win-a**: RTX 4090 24,564 MiB on PCIe Gen4 x16 (under load), driver 617.14, a 24-core CPU, 32 GiB
  DDR5-7600, a 5.1 GB page file. Stock setup's low-RAM mode, resident variant: the experts the GPU does not hold are
  copied into RAM at start and the KV cache stays in VRAM (no KV streaming below ~35 GiB of RAM).

### Resources (G10, G21)

| Measure | RTX 3090, 64 GiB | RTX 4090, 32 GiB, low-RAM | Boundary |
|---|---|---|---|
| GPU memory in use while serving | 23,277-23,455 of 24,576 MiB | 23,322-23,492 of 24,564 MiB | sampler |
| Experts at start | 23.42 GiB loaded at 2.6-7.1 GiB/s (log); GPU cache size not logged | GPU cache of 7,708 experts, 14.67 GiB (log); load rate not logged | server log |
| Engine working set, lifetime peak | 30.26 GB | 28.07 GB | per-process peak |
| Engine private commit, lifetime peak | 55.15 GB | 28.10 GB | per-process peak |
| System RAM available while serving | 32.4-33.7 GB of 68.4 GB | 10.1 GB at G10; **0.37 GB minimum** (during G15's engine restarts) of 34.0 GB | sampler |
| Commit available while serving | 13.4 GB of 72.7 GB | 6.1 GB of 39.1 GB | sampler (G10) |
| Integration root on disk | 73.8 GB | 99.4 GB | file sizes (G21) |
| Start to verified readiness | 33 s first start, 17.1-19.4 s restarts | 14.9 s first start, 14.5-14.8 s restarts | wall |
| Engine failures across 7 server logs | none in 455 completed requests | none in 465 completed requests | server log scan |

The 32 GiB host completed every gate, but the resident low-RAM mode leaves almost no RAM in reserve: treat that fit
as the tested configuration only, not as room for anything else. The only engine exits on either host were the
deliberate G15 kills.

### Throughput (server-reported)

| Case | RTX 3090 | RTX 4090, low-RAM | RTX 5090 (candidate 2, for scale) |
|---|---|---|---|
| Cold prefill, 100,030 tokens | 43,906 ms (2.3K tokens/s) | 20,939 ms (4.8K tokens/s) | 15,588 ms (6.4K tokens/s) |
| Cold re-prefill after an engine restart, ~7.1K tokens | 5,661 ms | 13,797 ms | 1,780 ms |
| Cached continuation at ~105K tokens | 294-1,702 ms prompt time | 463-637 ms | 333 ms |
| Decode at ~105K context | 82-98 tokens/s | 105-117 tokens/s | 158-185 tokens/s |
| Decode, short contexts (restart and replay turns) | 79-113 tokens/s | 104-126 tokens/s | 148-206 tokens/s |

Both 24 GB hosts prefill long prompts more slowly than the RTX 5090. Strata's prompt path streams experts to the
GPU, so the RTX 3090's PCIe Gen3 x8 link and DDR4-2133 are the likely bound (not isolated by a separate
measurement). On the RTX 4090 in low-RAM mode the first prompt after each engine restart was slow (13.8 s for 7.1K
tokens, 15.1 s for 12.8K) although readiness took about 15 s; the turns after it reused the prefix cache as usual.

### Agent turns, restarts and context (G11-G19)

| Case | RTX 3090 | RTX 4090, low-RAM |
|---|---|---|
| Tracer runs (typed read/edit/bash, `--continue` recall) | 3/3 | 3/3 |
| Same-session prefix reuse | 13/13 continuations | 13/13 continuations |
| Engine killed while idle: next turn | 26.3 s | 27.8 s |
| Engine killed mid-generation: next turn | 38.2 s | 28.8 s |
| Client restart: next turn | 2.2 s | 1.5 s |
| Client and full server restart: next turn | 8.0 s | 15.8 s |
| Exact server limit (prompt + `max_tokens` + 8 ≤ 131,072) | unchanged | unchanged |
| Near-limit tool turns: OMP-fitted caps, largest prompt + cap | 15,547-24,624; 129,997 | 15,549-24,999; 129,997 |
| Production compaction (long session) | at 113,156 tokens down to 30,140 | at 111,492 down to 29,847 |
| A-B-A interleaving: reused prefix | the shared 6,797-token system prefix | the same |

### Coding evaluation (G24)

The same frozen `synthetic-1` set, harness, caps and restart hook as the RTX 5090 candidates; a non-scored pilot
(6/6 on both hosts) before each scored batch.

| Task | RTX 3090 | RTX 4090, low-RAM |
|---|---|---|
| bugfix-a | 3/3 | 3/3 |
| bugfix-b | 3/3 | 3/3 |
| multifile-regression | 3/3 | 2/3 (one attempt ended on OMP's thinking-loop detector) |
| tool-loop | 2/3 | 1/3 |
| long-context | 3/3 | 3/3 |
| continuation | 3/3 | 3/3 |
| **Scored** | **17/18** | **15/18** |
| Median task wall; batch wall | 74.7 s; 1,409 s | 69.0 s; 1,422 s |

Every tool-loop failure, here and on the RTX 5090, is the same hidden settlement test; across the four scored
batches of this model the task passed 4 of 12 attempts. With three attempts per task, per-host differences are
noise, not a ranking.

### Fresh root (G26)

`install` (unmodified stock `setup.py` v0.1.31 from local verified inputs, the shards fetched beforehand) took
697 s on the RTX 3090 host and 649 s on the RTX 4090 host; the quickstart's `launch-omp` example fixed the fixture in
17.7 s and 12.9 s, and its tests passed afterwards.

</details>

### Exploratory: the original model, IQ3_S, on the RTX 3090 (64 GiB)

<details>
<summary>Exploratory IQ3_S vs Coder IQ1_M table and tool-loop exact-money diagnosis (2026-10-01)</summary>

Draft profile `win11-rtx3090-iq3s-131k-strata0.1.31-omp18.4.8`: the same tuple and settings with Strata's
best-quality size of the original Qwen3.8-Flash-Next instead of the Coder, run in its own root to answer one
question: does the original model pass the task the Coder fails? Only G10, G11, G17, G21 and G24 ran; their receipts
are in its release directory and its ledger stays draft.

| Measure | IQ3_S | Coder IQ1_M (same host, above) |
|---|---|---|
| Stock setup choice | every expert in RAM, no KV streaming (that needs 64.8 GiB) | every expert in RAM, KV streaming |
| Experts at start | 46.84 GiB at 2.9-3.0 GiB/s; GPU cache of 7,865 experts, 14.91 GiB | 23.42 GiB at 2.6-7.1 GiB/s |
| Start to verified readiness | 48.6 s first start, 40.4-40.8 s restarts | 33 s, 17.1-19.4 s |
| Engine working set / private commit, lifetime peak | 52.8 GB / 78.4 GB | 30.3 GB / 55.2 GB |
| System RAM available while serving | 10.7 GB at G10, 9.2 GB minimum | 32.4-33.7 GB |
| Commit available while serving (G10) | **0.72 GB** of 83.6 GB | 13.4 GB of 72.7 GB |
| Cold prefill, 100,030 tokens | 85,079 ms (1.2K tokens/s) | 43,906 ms (2.3K tokens/s) |
| Decode at ~105K context | 56-66 tokens/s | 82-98 tokens/s |
| Scored evaluation | **15/18**: tool-loop 0/3, every other task 3/3 | 17/18: tool-loop 2/3 |
| Median task wall; batch wall | 120.6 s; 2,085 s | 74.7 s; 1,409 s |

The answer is no. All three scored tool-loop attempts and the pilot's fail the same hidden test as the Coder's
failures, each time on its exact-money assertion: the largest account totals 12345678901234567890123456790000
instead of 12345678901234567890123456789012, a precision loss; the task's other three hidden tests pass every time.
Short tracer turns decoded at 50-84 tokens/s. The model fits 64 GiB only as tested: since the Coder's run the commit
limit had grown from 72.7 GB to 83.6 GB (the page file from 4.3 GB to 15.2 GB), and 0.72 GB of commit remained
while serving. After the 128 GB upgrade stock setup streams IQ3_S's KV cache to RAM, which needs the separate
`win11-rtx3090-iq3s-131k-kvstream-strata0.1.31-omp18.4.8` profile; that changes speed, not output.

</details>


## Candidate 2 (2026-10-01): stock Strata v0.1.30, stock OMP 18.4.6

<details>
<summary>Unqualified historical candidate on RTX 5090 and Issue #3 evidence reconciliation (2026-10-01)</summary>

Profile `win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`; receipts and scrubbed results under
`releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/`. The boundaries (wall, server, sampler) are the
ones defined for candidate 1 below. The second root reused the first root's model shards (re-hashed) and 15 of its
17 generated files are byte-identical; only the engine binary differs (G26).

### Resources (G10, G21)

| Measure | Candidate 2 | Candidate 1 | Boundary |
|---|---|---|---|
| GPU memory in use while serving | 30,742-30,838 MiB of 32,607 | 30,820-30,836 MiB | sampler |
| Engine (`strata.exe`) working set, lifetime peak | 30.53 GB | 30.53 GB | per-process peak |
| Engine private commit, lifetime peak | 63.35 GB | 63.35 GB | per-process peak |
| System RAM available while serving (minimum per gate run) | 8.5-9.7 GB of 50.6 GB | 9.0-11.1 GB | sampler |
| Commit available while serving | 7.9 GB of 83.9 GB | 8.3 GB | sampler (G10) |
| Integration root on disk | 73.7 GB: models 58.4, Strata data 8.4, runtime 1.1, downloads 0.9, OMP home 0.2, plus 4.7 GB of qualification and evaluation workspaces | 74.2 GB | file sizes (G21) |
| Start to verified readiness | 14.5-15.3 s on restarts; 18.6 s for the root's first start | 14.4-15.9 s; 20.9 s first start | wall |
| Expert load at start | 23.42 GiB at 3.40 GiB/s (first start's log) | 2.68-3.44 GiB/s | server log |

Across 7 server logs and 521 completed requests there was no watchdog stop, out-of-memory, CUDA error or
traceback. The only two engine exits were the deliberate G15 kills; v0.1.30 logs the mid-generation one with its
exit code and last engine line instead of a generic out-of-memory hint.

### Throughput (server-reported)

| Case | Candidate 2 | Candidate 1 |
|---|---|---|
| Cold prefill, 100,030 tokens | 15,588 ms (6.4K tokens/s) | 16,039 ms |
| Cold prefill, 104,810 tokens (near-limit task, first request) | 16,150 ms (6.5K tokens/s) | 16,636 ms for 104,827 |
| Cold prefill after an engine restart, 7,090 tokens | 1,780 ms (4.0K tokens/s) | 1,796 ms for 7,123 |
| Cached continuation, 105,670 tokens with 105,025 reused | 333 ms prompt time | 282 ms |
| Decode, short contexts | 148-206 tokens/s | 142-234 tokens/s |
| Decode at ~105K context | 158-185 tokens/s | 157-158 tokens/s |

v0.1.30's "short prompts up to 28% faster" (chunked expert streaming) did not show on these prompts: the tracer's
~7K-token first request and the 100K-token prefills are within a few percent of candidate 1.

### Agent turns (wall)

| Case | Candidate 2 | Candidate 1 |
|---|---|---|
| Tracer turn 1: read, edit and test with 5-6 tool calls on a ~7K-token prompt | 4.1-7.5 s | 4.1-6.9 s |
| Tracer turn 2: `--continue`, no tools | 1.2-1.3 s | 1.1-1.3 s |
| Prefix reuse on same-session continuations | 12/12 requests reused 6.8K-7.9K tokens | 12/12 |
| Continuation after another session interleaved (A-B-A) | only the shared 6,797-token system prefix reused | 6,830 |

### Restart cost (G15, G16, G20)

- **Engine killed while idle.** The next OMP turn took 17.3 s: about 14 s to reload the engine, a cold re-prefill
  of the whole transcript (7,090 tokens, 1.8 s), then decode.
- **Engine killed mid-generation.** The cut turn ends as an error that quotes the engine's exit code. The next turn
  took 16.1 s on the same path and answered correctly; the second turn reused 7,470 of 7,517 tokens. The reasoning
  loop seen on candidate 1 (2 of 3 trials) did not occur in this single trial.
- **Client restart.** The next turn took 1.2 s, with the live prefix cache intact.
- **Client and full server restart.** The server was ready in 14.6 s, and the next turn took 3.0 s: a re-prefill
  of 7,320 tokens in 1.9 s plus decode.

### Context (G17, G18)

- **Exact server limit:** unchanged, prompt + `max_tokens` + 8 ≤ 131,072 (100,030 accepted with 31,034, refused
  with 31,035).
- Stock OMP 18.4.6 fitted caps of 15,544-24,656 to 104,810-105,670-token prompts; the largest prompt + cap was
  129,997, inside the declared 130,048-token window. No overshoot occurred; the 1,024-token margin stays.
- A single prompt of about 136K tokens is refused explicitly (HTTP 400 surfaced by OMP; no engine work).
- **Compaction:** with the production configuration, a 14-turn session compacted at 111,351 tokens down to 30,014
  (peak engine prompt 105,918) and then finished a typed edit that needed a pre-compaction fact. At the reduced
  12,000-token threshold OMP 18.4.6 compacted twice in 7 turns (at 11,085 and 11,846 tokens) where 18.4.0
  compacted six times, with the same final result.

### Network (G13)

With the launcher's egress guard: 0 non-loopback events out of 3,559 ETW Kernel-Network events attributed to
the OMP and Strata process trees, over a typed tool turn and a compaction turn; OMP's loopback probes of ports
11434, 8080 and 1234 remain. The unguarded run was not repeated on this candidate.

### Coding evaluation (G24)

The same frozen `synthetic-1` set and harness (manifest `3b292b2e…`, no drift), same caps, full Strata server
restart between the continuation phases.

| Task | Verified passes | Task wall per attempt (s) | Peak prompt tokens |
|---|---|---|---|
| bugfix-a | 3/3 | 25.0, 30.8, 50.7 | 8.8K-14.4K |
| bugfix-b | 3/3 | 107.9, 106.3, 61.4 | 14.7K-24.5K |
| multifile-regression | 3/3 | 31.8, 52.5, 29.2 | 9.6K-13.7K |
| tool-loop | 0/3 | 95.2 ✗, 73.4 ✗, 44.6 ✗ | 12.7K-24.8K |
| long-context | 3/3 | 24.8, 24.5, 34.6 | 13.3K-14.8K |
| continuation | 3/3 | 47.1, 47.8, 44.3 | 8.0K-8.5K |

- **Scored result: 15/18 verified passes (0.833)**, against 16/18 for candidate 1. All three failures are
  tool-loop fixes that passed the visible tests but failed the same combined cross-account/void/exact-money
  hidden test; candidate 1 failed a settlement test in two of its three attempts. No attempt timed out,
  aborted, hit a cap or compacted, and there were no protocol errors.
- The batch took 932 s. Task wall time ranged from 24.5 to 107.9 s, with a median of 45.8 s over all 18
  attempts, including verification. Reported output per attempt was 2.9K-15.0K tokens.
- A non-scored pilot before scoring passed 5/6 (tool-loop failed). The harness then ran unchanged.
- **Boundary:** as for candidate 1, the evaluation ran under the host operator's account without an OS sandbox
  (the owner-approved deviation), and there is no comparison with any other runtime or model.

### Issue #3 evidence reconciliation (2026-10-10)

[Issue #3](https://github.com/alphastorm/omp-strata/issues/3) concerns this historical Coder candidate, not the
latest qualified profile. Its [G24 export](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/evidence/g24-scored-20261001T033615Z.json)
and [sealed receipt](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/receipts/g24-scored-20261001T033615Z.json)
retain the following four `tool-loop` attempts. Each records one verifier failure, named
`test_cross_account_dedup_voids_and_exact_signed_money`, with no timeout, abort, compaction or protocol error.
The receipt and issue record that the visible tests passed. The pilot is not part of the scored denominator.

| Sample | Attempt | Task wall (s) | Hidden result |
|---|---|---|---|
| Non-scored pilot | 1 | 88.217 | Same named test failed |
| Scored | 1 | 95.195 | Same named test failed |
| Scored | 2 | 73.439 | Same named test failed |
| Scored | 3 | 44.580 | Same named test failed |

The export is bound to implementation `58724457ba455f3cc2dd0580d434618d53f32878` and frozen `synthetic-1` manifest
`3b292b2ef5de9af05633538dec630afadc7f9708f3fcebf68fdc4a81612ed356`; its sealed evidence SHA-256 is
`93d5fc73b0d353d0ff8290332efffe6a0ae9394fb69010c9cbdea6dd7d037d8f`. It keeps test names and aggregate attempt
facts, **not the assertion diff or generated implementation**. Candidate 1 instead records the settlement
failure count; these exports do not establish its precise failed assertion.

The later [RTX 3090 IQ3_S diagnosis](#exploratory-the-original-model-iq3_s-on-the-rtx-3090-64-gib) is more
specific: its pilot and three scored attempts returned `12345678901234567890123456790000` for the largest
account instead of `12345678901234567890123456789012`. That establishes an exact-money precision loss in
**those later IQ3_S attempts**. Its [G24 export](../releases/win11-rtx3090-iq3s-131k-strata0.1.31-omp18.4.8/evidence/g24-scored-20261001T101125Z.json)
also names the same failed test, but does not preserve that detailed numeric diff. The detailed diagnosis is
the recorded measurement above, not new raw evidence acquired for this reconciliation.

The [frozen test](../eval/verifiers/tool-loop/hidden.py) compares a complete account-to-integer-cents result
before testing the CLI JSON; the [contract](../eval/tasks/tool-loop/workspace/docs/format.md) combines CSV
quoting, per-account first-occurrence de-duplication, account-scoped voids outside the interval, offset-aware
half-open bounds, exact large signed amounts and zero sums. Sharing this test name does **not** establish
which rule each original Coder patch missed, or that all four used the same causal mechanism as IQ3_S. A
rounded total alone also cannot distinguish float conversion from decimal-context rounding or another
generated-code error. There is no evidence here of a transport/integration failure or a reason to change
the verifier; absence of recorded protocol errors is not a universal exoneration of the integration.

The original per-attempt `result.json` (full unittest output and `assertEqual` diff) and `candidate.patch`
are **not in this repository**. Completing issue #3 requires a read-only, scrubbed export of both for the
pilot and each scored attempt, attributed to this profile, run, task/attempt and frozen manifest with file
hashes. Inspect the first failing comparison and corresponding implementation for each attempt separately;
only then classify model-generated algorithm/precision errors versus a task/verifier or integration defect.
Until then the original Coder mechanism remains **unproved**, so this documentation does not close #3.

No GPU execution, model tuning, task or verifier change was performed for this reconciliation. The frozen
`synthetic-1` evidence and scores remain intact; the later private task set has already replaced it for
[model ranking](#the-models-on-the-owners-kind-of-work-2026-10-04-a-private-60-task-set), not retroactively repaired its failures.

### Second-root install (G26)

`fetch` 47 s (391 MB of OMP, engine and llama.cpp archives downloaded and verified; the two shards reused and
re-hashed), `install` 316 s, first `start` to readiness 18.6 s, the quickstart's non-interactive `launch-omp`
example 7.6 s (the model fixed the sample project), tracer 3/3, `stop` with the GPU back at 0 MiB.

</details>

## Candidate 1 (2026-09-30): stock Strata v0.1.27, stock OMP 18.4.0

<details>
<summary>Unqualified historical candidate on RTX 5090, original boundary definitions and clean install (2026-09-30)</summary>

Host **rtx5090-win-a**: Windows 11 Pro, RTX 5090 32,607 MiB (driver 610.88), 47.15 GiB RAM, a 31 GB page file,
a 16-core AVX-512 CPU and NVMe storage. Successive stock tuples were measured with the same model
(Qwen3.8-Flash-Next Coder IQ1_M), 131,072-token context, INT8 KV and MTP speculation. Profile
`win11-rtx5090-coder-iq1m-131k`: stock OMP 18.4.0 and stock Strata v0.1.27 with Qwen3.8-Flash-Next Coder IQ1_M, a
131,072-token context, INT8 KV, MTP speculation. Measurements were taken on 2026-09-30 (UTC).

Boundaries used below:
- **wall** is a monotonic clock around a whole client action.
- **server** figures are stock Strata's own per-request records (`/metrics`: `prompt_ms`, `decode_ms`, `reused`).
- **sampler** figures are system counters: `nvidia-smi` and `GlobalMemoryStatusEx` every 2 s, plus the per-process
  `K32GetProcessMemoryInfo` lifetime peaks.

A restarted engine with a warm OS file cache is *process-cold, file-cache-warm*. Every figure comes from this
repository's probes; nothing is borrowed from upstream READMEs. Receipts and scrubbed raw results are under
`releases/win11-rtx5090-coder-iq1m-131k/`.

### Resources (G10, G21)

| Measure | Value | Boundary |
|---|---|---|
| GPU memory in use while serving | 30,820-30,836 MiB of 32,607 | sampler |
| GPU expert cache | 12,288 experts, 23.42 GiB | server log |
| Engine (`strata.exe`) working set | 30.0-30.5 GB (peak 30.53 GB) | per-process peak |
| Engine private commit | 62.8-63.3 GB (peak 63.33 GB) | per-process peak |
| Server interpreter (`python.exe`) working set | 0.20 GB | per-process |
| System RAM available while serving | 9.0-11.1 GB of 50.6 GB | sampler, minimum per gate run |
| Commit available while serving | 8.3 GB of 83.9 GB (RAM + page file) | sampler (G10) |
| Integration root on disk | 69.5 GB installed: models 58.4, Strata data 8.4, downloads 1.3, runtime 1.1, OMP home 0.2; plus 4.7 GB of qualification and evaluation workspaces | file sizes (G21) |
| Start to verified readiness | 14.4-15.9 s over every recorded start and restart of the qualified root; 20.9 s for a fresh root's first start (G26) | wall, process-cold, file-cache-warm |
| Expert load at start | 23.42 GiB at 2.68-3.44 GiB/s | server log |

The engine commits about twice its resident memory. The commit limit is RAM plus page file, so this profile needs
a page file on a 47 GiB host. The practical floor observed here is about 34 GiB of available RAM before start,
leaving about 9 GB available and 8.3 GB of commit headroom while serving. Model-file size does not predict the fit.

Across 8 server logs and 629 completed requests there was no watchdog stop, out-of-memory or CUDA error. Stock
Strata v0.1.27 labels every unexpected engine exit as a probable out-of-memory event (Strata#215, fixed in
v0.1.28). The 5 exits observed were 3 deliberate mid-generation kills (G15) and 2 stale-cancel crashes (G14).

### Throughput (server-reported)

| Case | Value |
|---|---|
| Cold prefill, 104,827 tokens | 16,636 ms (6.3K tokens/s) |
| Cold prefill after an engine restart, 7,123 tokens | 1,796 ms (4.0K tokens/s) |
| Cached continuation, 105,429 tokens with 105,040 reused | 282 ms prompt time |
| Decode, short contexts | 142-234 tokens/s (MTP speculation on) |
| Decode at ~105K context | 157-158 tokens/s |

### Agent turns (wall)

| Case | Value |
|---|---|
| Tracer turn 1: read, edit and test with 3-4 tool calls on a ~7K-token prompt | 4.1-6.9 s |
| Tracer turn 2: `--continue`, no tools | 1.1-1.3 s |
| Prefix reuse on same-session continuations | 12/12 requests reused 6.8K-8.2K tokens |
| Continuation after another session interleaved (A-B-A) | only the shared 6,830-token system prefix reused |

### Restart cost (G15, G16, G20)

- **Engine killed while idle.** The next OMP turn took 16-17 s: about 14 s to reload the engine, a cold re-prefill
  of the whole transcript (7.1K tokens, 1.8 s), then decode.
- **Engine killed mid-generation.** The cut turn ends as an error. The next turn took 16.2 s, on the same path. In
  2 of 3 trials, that first post-crash turn ended in an OMP-detected reasoning loop (an explicit error) instead of
  an answer; later turns recovered.
- **Client restart.** The next turn took 1.3 s, with the live prefix cache intact.
- **Client and full server restart.** The server was ready in 14.5 s, and the next turn took 3.1 s: a re-prefill
  of 7,400 tokens in 1.9 s plus decode.

### Context (G17, G18)

- **Exact server limit:** prompt + `max_tokens` + 8 ≤ 131,072. A 100,030-token prompt is accepted with
  `max_tokens` 31,034 and refused with 31,035 (HTTP 400, "requests are never truncated").
- Stock OMP fits `max_tokens` to its estimate of the remaining window. At 104.8K-105.4K-token prompts it sent caps
  of 15,596-24,987; the largest prompt + cap was 130,061. Without a margin, OMP overshot by 21 tokens once and
  Strata refused the request. The integration therefore declares the window 1,024 tokens below the engine's.
- A single prompt of about 136K tokens is refused explicitly (HTTP 400 surfaced by OMP; no engine work).
- **Compaction:**
  - With the production configuration, a long session compacted at 113,383 tokens down to 30,612, and then
    finished a typed edit that needed a fact from before the compaction.
  - At a reduced 12,000-token threshold, 6 compactions ran in 7 turns, with the same result.

### Network (G13)

These counts come from ETW `Microsoft-Windows-Kernel-Network` events attributed to the OMP and Strata process
trees:
- **Without the launcher's egress guard:** 244 packet events to 2 non-loopback HTTPS endpoints (OMP's startup
  model-catalog refresh), plus loopback probes of ports 11434, 8080 and 1234.
- **With the guard:** 0 non-loopback events out of 3,711 attributed events, over a typed tool turn and a
  compaction turn.

### Coding evaluation (G24)

This is the frozen `synthetic-1` set: six original stdlib Python tasks. The verifiers are immutable and run
outside the worktree. Each attempt gets a fresh workspace and a fresh client HOME. Caps per attempt: 900 s, 40
tool calls, and 32,768 output tokens per response. The run used the production launcher, with a full Strata
server restart between the phases of the continuation task.

| Task | Verified passes | Task wall per attempt (s) | Peak prompt tokens |
|---|---|---|---|
| bugfix-a (interval subtraction) | 3/3 | 26.6, 32.6, 26.8 | 8.7K-10.1K |
| bugfix-b (incremental UTF-8 decoding) | 3/3 | 123.5, 79.5, 42.7 | 11.3K-25.7K |
| multifile-regression | 3/3 | 49.0, 67.4, 74.2 | 12.3K-19.0K |
| tool-loop (CSV settlement, CLI, tests) | 1/3 | 85.5 ✗, 48.4 ✗, 106.2 | 13.4K-25.1K |
| long-context (retrieve a policy from a ~300 KB archive, change code) | 3/3 | 27.3, 24.3, 29.2 | 13.2K-15.2K |
| continuation (calibrate, restart client and server, resume) | 3/3 | 60.3, 54.6, 60.0 | 9.3K-11.1K |

- **Scored result: 16/18 verified passes (0.889).** Both failures are tool-loop fixes that passed the visible
  tests but failed one hidden settlement test. No attempt timed out, aborted, hit a cap or compacted, and there
  were no protocol errors: no malformed arguments, orphan or missing results, bad ids, or error/aborted stops.
- The batch took 1,018 s. Task wall time ranged from 24.3 to 123.5 s, with a median of 51.8 s over all 18
  attempts, including verification.
- Reported output per attempt was 3.1K-17.7K tokens.
- The long-context task was solved by searching and reading, not by ingesting the archive (its peak prompt was
  about 15K tokens), so it does not exercise near-limit capacity; G17 does.
- A non-scored pilot, run before scoring, passed 5/6 (tool-loop failed). The harness then ran unchanged.
- **Boundary:** the evaluation ran under the host operator's account without an OS sandbox. This is a recorded
  deviation from the packet, approved by the owner. There is no comparison with any other runtime or model.

### Clean install (G26)

Every `docs/QUICKSTART.md` command ran as written, from a checkout of commit 887ff7d, into a new integration root
on the same host. This was not a fresh OS: Python, Git and the driver were already present.

| Step | Wall |
|---|---|
| `fetch`: download and verify 59.7 GB of pinned artifacts | 608 s |
| `install`: stock `setup.py` from the verified inputs | 352 s |
| `start` to verified readiness (first start of the new root) | 20.9 s |
| `launch-omp` non-interactive example (fixes the sample project) | 8.9 s |
| `tracer --runs 1` (typed tools, protocol and task pass) | 6.3 s |
| `stop` | 3.0 s |

These were identical to the qualified root:
- the 17 generated files (model shards, pack, tokenizer and chat template, MTP layer, engine binaries);
- the shared settings and the normalized server config;
- the pip freeze, Python and the Strata commit.

Only the stock config file differs, because `setup.py` writes the root's absolute paths into it. The runtime
identity hashes that file, so it is specific to each root.

</details>
