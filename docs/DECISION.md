# Decision (2026-10-01)

Scope: stock OMP 18.4.6 → stock Strata v0.1.30, Qwen3.8-Flash-Next Coder IQ1_M, 131,072-token context, one
Windows 11 + RTX 5090 host (`rtx5090-win-a`), local loopback route, single user: the second candidate,
`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`. The evidence is in
`releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/qualification.json` (receipts and scrubbed
results) and in `docs/MEASUREMENTS.md`. The first candidate (Strata v0.1.27 + OMP 18.4.0, decided on 2026-09-30)
keeps its ledger and its root as the rollback installation; its two release blockers were the reason for this
candidate, and one of them is gone. The three decisions below are separate. None of them depends on a comparison
with NInfer, and none was made.

## 1. Integration readiness: working candidate, one upstream blocker left

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

## 2. Usefulness: keep as an optional local coding backend

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

## 3. Further investment in engine-state durability: not justified now

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
