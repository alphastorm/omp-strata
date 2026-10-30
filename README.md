<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
  <img src="assets/logo-light.svg" alt="" width="72" height="72">
</picture>

# OMP Strata

**Stock Oh My Pi on a stock, local Strata server. Nothing forked, everything pinned.**

**Current, qualified: stock OMP `18.14.0` with stock Strata `v0.2.8` across the RTX PRO 6000, the RTX 5090 (262K default and 131K alternative), the RTX 4090 + RTX 3090 pair (PLE-direct variant) and the Mac Studio route. No fork, no proxy, no cloud fallback.**

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
[profile]: profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0.json
[strata-badge]: https://img.shields.io/badge/Strata-v0.2.8-37C4CB?labelColor=0B0E11
[omp-badge]: https://img.shields.io/badge/OMP-18.14.0-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-strata?color=1C232B&labelColor=0B0E11

<sub><strong>Private by design:</strong> loopback-only server · API key required · isolated OMP profile ·
no cloud fallback · every byte hash-pinned</sub>

</div>

## Qualified now

Qualified on 2026-10-30 ([decision](docs/DECISION.md)). Every local ledger below has 21 pass and 3 not applicable; the
route ledger passed its own G23.

| Host | Model and context | Strata · OMP | Ledger | Rollback |
|---|---|---|---|---|
| RTX PRO 6000 | Qwen3.8-Flash-Next IQ3_S, 262,144 tokens, every expert in VRAM; 4 batch slots, conversation parking, 32K prompt chunks | v0.2.8 · 18.14.0 | [21 pass, 3 n/a](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0/qualification.json) | [v0.2.7](releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2/qualification.json) |
| RTX 5090, **default** | Coder IQ1_M, 262,144 tokens; 36 GiB available-RAM start floor; engine's 3,584 MiB automatic conversation cache (requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script and re-registered with the owner's fleet controller) | v0.2.8 · 18.14.0 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0/qualification.json) | [v0.2.7 262K](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/qualification.json) |
| RTX 5090, qualified alternative | Coder IQ1_M, 131,072 tokens; 34 GiB available-RAM start floor; starts with Docker Desktop and WSL running (production container stopped by the fleet controller; qualified, no longer the default) | v0.2.8 · 18.14.0 | [21 pass, 3 n/a](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0/qualification.json) | [v0.2.7 131K](releases/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2/qualification.json) |
| RTX 4090 + RTX 3090 | IQ3_S, 262,144 tokens, stock roles (RTX 4090 as Main, staged last), pipeline windows 2, no batch slots, display on the RTX 4090, direct per-layer embedding (PLE) reads (`--ple-io direct`); engine's 8,192 MiB automatic conversation cache (`v0.2.8` stock-residency roles draft stays measurement-only) | v0.2.8 · 18.14.0 | [21 pass, 3 n/a](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0/qualification.json) | [v0.2.7 PLE-direct](releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2/qualification.json) |
| Mac Studio → RTX PRO 6000 | SSH local forward to the PRO's 262K profile ([`docs/REMOTE.md`](docs/REMOTE.md)) | v0.2.8 · 18.14.0 | [G23 pass](releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/qualification.json), 2026-10-30 | [0.2.7 route](releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/qualification.json) |

Profiles and route, with the host labels the ledgers use:

- RTX PRO 6000, `rtxpro6000-win-a`:
  [`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0`](profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0.json)
- RTX 5090, `rtx5090-win-a`:
  [`win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0`](profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0.json)
  (**default**; the host's Docker Desktop and WSL, which run its production NInfer container, must be stopped, and after WSL restarts that container must be recreated by the owner's pinned relaunch script and re-registered with the owner's fleet controller) and
  [`win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`](profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0.json)
  (qualified alternative; starts with Docker Desktop and WSL running, production container stopped by the fleet controller)
- RTX 4090 + RTX 3090, `rtx3090-win-a`:
  [`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`](profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0.json)
  (current; pins `strata.ple_io: "direct"`, `--ple-io direct`; the `v0.2.8` stock-residency roles draft stays a measurement-only draft)
- Mac Studio client:
  [`client-rtxpro6000-262k-strata0.2.8-omp18.14.0`](routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json)
  (rollback
  [`client-rtxpro6000-262k-strata0.2.7-omp18.13.2`](routes/client-rtxpro6000-262k-strata0.2.7-omp18.13.2.json))

What these ledgers establish, and what they do not:

- **New-release discovery is separate.** The [v0.2.8 campaign](releases/campaigns/v0.2.8.json) (opened with
  `scripts/campaign.py open --release v0.2.8 --omp-tag v18.14.0`) is complete across all five rows — the PRO,
  RTX 5090 262K default, RTX 5090 131K alternative, pair PLE-direct variant, and Studio→PRO route — as are the
  [v0.2.7](releases/campaigns/v0.2.7.json), [v0.2.3](releases/campaigns/v0.2.3.json) and
  [v0.2.1](releases/campaigns/v0.2.1.json) campaigns. See the
  [campaign lifecycle and prepared host commands](docs/OPERATIONS.md#release-campaigns-op10-discovery--op11-host-owned-qualification).
- **Ledger counts and receipts.** Each current local ledger has 21 pass and 3 not applicable; G22 (images), G23
  (remote clients) and G25 (runtime comparison) are not applicable to these local, text-only profiles. Real-host
  `v0.2.8` receipts cite tooling commits `278e53c` on the RTX PRO 6000 main run (operator receipts at `4853ab3`, G06
  citing green PR #69 [CI run 40989725083](https://github.com/alphastorm/omp-strata/actions/runs/40989725083) at
  `4853ab3`), `278e53c` on the RTX 5090 262K and 131K main runs (where G10 failed on Windows build 26300.9818's
  `netstat` output while the server answered every request) with passing G10 reruns and operator receipts at `f9e8c74`
  (G06 citing green [CI run 40996143852](https://github.com/alphastorm/omp-strata/actions/runs/40996143852) at
  `f9e8c74`; 262K rerun with Docker Desktop and WSL stopped, 131K rerun with Docker Desktop and WSL running), and
  `4853ab3` on the pair PLE-direct main run and operator receipts after admitting engine `0.1.54`'s stage order
  ([measurements](docs/MEASUREMENTS.md#strata-v028-windows-2026-10-30-stock-omp-18140),
  [decision](docs/DECISION.md)). Scored G24 passed 16/18 on the PRO (pilot 5/6; `v0.2.7` rollback: 15/18), 17/18 on
  the RTX 5090 262K default (pilot 6/6; `v0.2.7`: 16/18), 18/18 on the RTX 5090 131K alternative (pilot 5/6; `v0.2.7`:
  16/18), and 15/18 on the pair PLE-direct profile (pilot 5/6; `v0.2.7`: 17/18), with scored batch walls of 788 s,
  865 s, 968 s and 926 s (`v0.2.7` rollbacks: 828 s, 755 s, 732 s and 1,029 s; batch walls, not isolated decode
  latency). All protocol counters (including malformed arguments) are zero on the four qualified `v0.2.8` server
  profiles; all receipts, retained main-run G10 failures and task failures remain published.
- **The pair keeps stock roles with the RTX 4090 as Main and pins direct PLE reads.** On `rtx3090-win-a`, engine
  `0.1.54`'s stage order was admitted at `4853ab3` after the 2026-10-30 pair measurement: `--gpu-roles 0=main,1=helper`
  stages the RTX 3090 (GPU 1) first on layers 0-23 with a 17.35 GiB expert cache ([Strata#4474](https://github.com/Niko1221/Strata/issues/4474)
  leaves 256 MiB more VRAM free than `v0.2.7`'s 17.6 GiB) and the RTX 4090 (GPU 0) last on layers 24-47 with 16.01 GiB
  (auto K=24, `--pipeline-windows 2` decode-capable). On the measurement-only `v0.2.8` stock-residency draft
  (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`),
  [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)'s upstream fix locked the 26.8 GiB PLE table
  (33.9-34.0 s), then gave the lock back on both starts and sized the automatic conversation cache at **4,864 MiB**
  (106-112 s to ready), against **8,192 MiB** and 61-63 s to ready with `--ple-io direct` at matching 100K-token
  time to first token (TTFT) (31.2 s with PLE direct versus 30.9 s with stock residency). The current profile therefore
  keeps `strata.ple_io: "direct"` (`--ple-io direct`, [OPERATIONS.md](docs/OPERATIONS.md#stock-ple-direct-reads)),
  keeping **27.9 GiB** G10 Windows commit headroom of a **135.7 GiB** limit (**65.5 GiB** available RAM) and the
  **8,192 MiB** conversation cache. The `v0.2.7` PLE-direct profile is the qualified rollback; the `v0.2.8`
  stock-residency draft, the held `v0.2.7` roles draft (PLE in RAM), the unmeasured `v0.2.7` default-split draft, and
  the `v0.2.3` default and split-32 drafts stay unqualified ([decision](docs/DECISION.md)).
- **Remote use.** Through the tunnel (G23 on 2026-10-30 at `4853ab3`), a missing key was refused before launch and
  a wrong key got 401; health RTT was 6.1-6.7 ms and stream TTFT 0.199 s; a tunnel drop failed the turn in
  flight with the prior transcript preserved, and nonce recall passed after tunnel reopen (0.85 s), client
  restart (0.75 s) and verified server restart (1.65 s) ([`docs/REMOTE.md`](docs/REMOTE.md)).
- **Not supported.** Images, servers on other operating systems, durable engine state, multiple tenants, fleets
  (no fleet route is published), the upstream DeepSeek V4.1-Flash family (a separate `strata-dsv41` engine, not an
  `omp-strata` profile family) and other client routes; every profile other than the qualified ones above remains
  a draft or a rollback installation.

### Current profile results

Per gate, for the four local profiles above
([measurements](docs/MEASUREMENTS.md#strata-v028-windows-2026-10-30-stock-omp-18140),
[decision](docs/DECISION.md)).

| Area | RTX PRO 6000 (2026-10-30) | RTX 5090, 262K default (2026-10-30) | RTX 5090, 131K alternative (2026-10-30) | RTX 4090 + RTX 3090, roles + PLE direct (2026-10-30) |
|---|---|---|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass: 3/3 tracer runs | pass: 3/3 tracer runs | pass: 3/3 tracer runs | pass: 3/3 tracer runs |
| Live prefix reuse in a session (lost on engine restart) | pass: 12 continuations, engine-reported | pass: 16 continuations, engine-reported | pass: 14 continuations, engine-reported | pass: 12 continuations, engine-reported |
| Interleaved conversations | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 8,192 MiB cache, 26 parks), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 3,584 MiB cache, 31 parks with Docker Desktop/WSL stopped), not an exact-output claim | pass: A resumes after B; 47 uncached tokens on the controlled continuation (engine's 4,096 MiB cache, 21 parks in the Docker Desktop/WSL-stopped main chain), not an exact-output claim | pass: A resumes after B; 48 uncached tokens on the controlled continuation (engine's 8,192 MiB cache, 28 parks), not an exact-output claim |
| Requests at once | up to 4, decoded together | one at a time | one at a time | one at a time |
| Loopback, API key (including `/status`, `/v1/telemetry` and `/tool-media/` on `v0.2.8`), fail-closed client, local-only routing, with an egress guard for OMP's startup catalog fetch | pass | pass (G10 rerun at `f9e8c74` after G10's listener-check fix for Windows build 26300.9818; main-chain G10 failure retained) | pass (G10 rerun at `f9e8c74` with Docker Desktop/WSL running; main-chain G10 failure retained) | pass |
| Engine or client restart, then continue from OMP's transcript (an engine restart re-prefills it; no state restoration) | pass (readiness 73.6-88.2 s; G16 85.6 s) | pass with Docker Desktop/WSL stopped (readiness 17.1-28.3 s; G16 28.3 s, lowest available RAM 9.79 GiB) | pass (readiness 16.6-27.2 s; G16 27.2 s, lowest available RAM 11.47 GiB) | pass (readiness 43.7-44.4 s; G16 43.7 s, PLE on direct SSD reads) |
| Context window (262,144 tokens on the RTX PRO 6000, RTX 5090 default and pair; 131,072 on the RTX 5090 alternative): exact limit, near-limit tool turns, explicit overflow (G17) | pass | pass | pass | pass |
| OMP compaction (reduced threshold and production long session, G18) | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off |
| Cancelling a *queued* request | pass, with all four slots generating | pass | pass | pass |
| Tool call cut off mid-arguments (G04) | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call | pass: stock Strata and stock OMP refuse the unfinished call |
| Six-task coding evaluation, 18 scored attempts (G24) | 16/18 (tool-loop 1/3, others 3/3; pilot 5/6, batch wall 788 s) | 17/18 (tool-loop 2/3, others 3/3; pilot 6/6, batch wall 865 s) | 18/18 (all six tasks 3/3; pilot 5/6, batch wall 968 s) | 15/18 (tool-loop 0/3, others 3/3; pilot 5/6, batch wall 926 s) |
| Guarded install and QUICKSTART example alongside earlier tuples (G26) | pass in a new root (install 1,053.3 s, start 97.6 s) | pass in a new root (install 365.6 s, start 38.4 s) | pass in a new root (install 297.8 s, start 38.5 s) | pass on an already prepared root (install 27.1 s, start 70.4 s; not a first-install timing) |

<details>
<summary><strong>Earlier qualified profiles and rollbacks</strong></summary>

Every profile and client route ledger is listed in [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md); the owner's
qualification decisions, retained failures, the G15 probe correction, the G16 predicate fix, the G18 fixture fix
and the OMP speculative-compaction setting are in [`docs/DECISION.md`](docs/DECISION.md), with full figures in
[`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md).

- **2026-10-28 — Strata `v0.2.7` + OMP `18.13.2` (`rtxpro6000-win-a`, `rtx5090-win-a` 262K and 131K, `rtx3090-win-a` pair PLE-direct, Mac Studio route):**
  current rollback across all lanes: on the PRO
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
  rerun retained beside main-run failure), the RTX 5090 262K profile
  ([ledger](releases/win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6/qualification.json); G24 14/18, G19
  rerun retained beside main-run failure; requires Docker Desktop and WSL stopped on the host now that the NInfer VM
  is larger), the RTX 4090 + RTX 3090 pair in its stock-roles variant with the engine's 8 GiB automatic conversation
  cache
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
