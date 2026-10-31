# Measurements

Dated real-host measurement records, methods, denominators and caveats for OMP Strata:
*Oh My Pi (coding-agent client) → OMP Strata (profile, lifecycle tool, evidence) → Strata (inference engine) →
the pinned model (served model)* on Windows 11 hosts, with receipts and scrubbed exports under
`releases/<profile>/`. Newest figures come first; sections older than 2026-10-11 are collapsed below their
headings as dated history.

Since the [2026-10-30 qualification](DECISION.md#update-2026-10-30-strata-v028-with-omp-18140-qualifies-on-every-host-and-the-studio-route-the-rtx-5090-262k-profile-becomes-its-default),
stock Strata `v0.2.8` (engine `0.1.54`) with stock OMP `18.14.0` is current on all three hosts and the Mac Studio
route, rolling back to `v0.2.7` (engine `0.1.52`) + OMP `18.13.2`: **rtxpro6000-win-a** (RTX PRO 6000,
Qwen3.8-Flash-Next IQ3_S at 262,144 tokens, four batch slots, conversation parking and 32K prompt chunks),
**rtx5090-win-a** (RTX 5090, Qwen3.8-Flash-Next Coder IQ1_M at 262,144 tokens as the new **default** and 131,072
tokens as the qualified alternative; the 262K default keeps its 36 GiB available-RAM start floor and requires the
host's Docker Desktop and WSL, which run its production NInfer container, to be stopped, with that container
recreated by the owner's pinned relaunch script and re-registered with the owner's fleet controller after WSL
restarts, while the 131K alternative starts with Docker Desktop and WSL running), and **rtx3090-win-a** (RTX 4090 +
RTX 3090 pair, IQ3_S at 262,144 tokens, stock roles with RTX 4090 as Main staged last, pipeline windows 2, no batch
slots, display on the RTX 4090, direct per-layer embedding (PLE) reads `--ple-io direct` via `strata.ple_io: "direct"`,
and the engine's 8,192 MiB automatic conversation cache). On the pair, the `v0.2.8` roles draft with stock PLE
residency stays a measurement-only draft after verifying [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)'s
fix on Windows (PLE lock given back, 4,864 MiB cache versus 8,192 MiB with PLE direct), the `v0.2.7` roles draft with
PLE in RAM stays a held draft on commit headroom (1.03 GiB Windows commit headroom versus 27.3 GiB on `v0.2.7`
PLE-direct and `v0.2.3` roles, and 27.9 GiB on `v0.2.8` PLE-direct, at the same 135.7 GiB limit), and the `v0.2.7`
default-split draft stays
unmeasured. The [2026-10-30 section](#strata-v028-windows-2026-10-30-stock-omp-18140) records the `v0.2.8` server
chains, the Studio route G23, the pair stage-order and `Strata#4518` measurements, and the RTX 5090 G10 listener
finding on Windows build 26300.9818 (`f9e8c74`); the [2026-10-28 section](#strata-v027-windows-2026-10-28-stock-omp-18132)
holds rollback evidence across all three hosts and the Studio route; the
[2026-10-23 section](#strata-v023-windows-2026-10-23-stock-omp-18126) and
[2026-10-21 section](#all-three-hosts-every-gate-2026-10-21-stock-strata-v021-stock-omp-18101) hold earlier
qualified history across all three hosts (`v0.2.1` + OMP `18.10.1` integration roots were removed on 2026-10-28);
and the 2026-10-15 and 2026-10-13 sections hold earlier qualified history (`v0.1.44.1` on the PRO and RTX 5090,
`v0.1.43.1` on all three hosts). Each tuple has its own integration root and release ledger; no earlier receipt is
inherited or replaced.

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
  establishes integration qualification, not task quality or runtime superiority. Separate 60-task private
  evaluations (`scripts/eval_taskset.py`) and 30-task Terminal-Bench 2.1 runs are comparison-only evidence and do
  not change any gate or ledger.

**Section index.** Every top-level section in this file, ordered newest first:

| Date | Hosts | Tuple | What it establishes | Same-file anchor |
|---|---|---|---|---|
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
