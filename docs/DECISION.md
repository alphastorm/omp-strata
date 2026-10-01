# Decision (2026-10-01)

Scope: stock OMP 18.4.6 → stock Strata v0.1.30, Qwen3.8-Flash-Next Coder IQ1_M, 131,072-token context, one
Windows 11 + RTX 5090 host (`rtx5090-win-a`), local loopback route, single user: the second candidate,
`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`. The evidence is in
`releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/qualification.json` (receipts and scrubbed
results) and in `docs/MEASUREMENTS.md`. The first candidate (Strata v0.1.27 + OMP 18.4.0, decided on 2026-09-30)
keeps its ledger and its root as the rollback installation; its two release blockers were the reason for this
candidate, and one of them is gone. The three decisions below are separate. None of them depends on a comparison
with NInfer, and none was made.

## Update, later on 2026-10-01: the third tuple on two 24 GB hosts

Stock Strata v0.1.31 and stock OMP 18.4.8 ran the complete real-host sequence on an RTX 3090 host with 64 GiB of
RAM and on an RTX 4090 host with 32 GiB of RAM (stock low-RAM mode), as draft profiles in fresh roots, without
touching the RTX 5090 or its other tenant. Evidence: `releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/`,
`releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/` and `docs/MEASUREMENTS.md`. The decisions
below stand for the RTX 5090 candidate; this update changes what blocks qualification and where the route can run.

- **G04 is the only failing gate on both hosts, and now only OMP's half is open.** Strata v0.1.31 no longer
  presents an unfinished call as complete (Strata#231); stock OMP 18.4.8 still runs it. A binary built from
  can1357/oh-my-pi#13868's head answers it with an error result and writes nothing; #13868 was merged on
  2026-10-01, after OMP 18.4.9 was published, so no release carries it yet. The suite now holds a cut-off call to
  the contract it already applied to a length cut: the call never runs, and the client may fail the turn or answer
  with an error. An OMP release carrying that fix will turn the composed reproducer into an unexpected success;
  qualification then needs that release in a profile and a host-free G04 run, plus the real-host gates on
  whichever host the profile names.
- **Every other gate passes on both hosts.** Evaluation 17/18 on the RTX 3090 and 15/18 on the RTX 4090 (the
  tool-heavy task 2/3 and 1/3; 4 of 12 across the four scored batches of this model). Decode runs at 79-113 tokens/s
  (RTX 3090) and 104-126 tokens/s (RTX 4090) against 148-206 on the RTX 5090; a 100K-token cold prefill takes 44 s
  and 21 s against 16 s.
- **The route no longer needs the RTX 5090.** Its costs move to the choice of host: slower prefill on the RTX 3090
  (PCIe Gen3 x8), and on the 32 GiB RTX 4090 almost no RAM reserve (0.37 GB available at the worst sample). Both
  hosts are getting more RAM (128 GB and 192 GB); the RTX 4090's low-RAM-off profile
  (`win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8`) is ready for that, and the RTX 3090 profile is unchanged
  by it (its setup choices do not depend on RAM above 35 GiB). Which host the route should live on is the owner's
  choice; until then the RTX 5090 profile stays the current candidate.
- **The larger original model does not fix the task the Coder fails.** An exploratory run of Strata's
  best-quality size of the original Flash-Next (IQ3_S) on the RTX 3090 scored 15/18 with the tool-heavy task
  0/3, every attempt on the same exact-money assertion, at about half the Coder's speed and with 0.72 GB of commit
  to spare on 64 GiB. Every candidate profile keeps the Coder IQ1_M.

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
