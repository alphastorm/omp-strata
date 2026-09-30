# Decision (2026-09-30)

Scope: stock OMP 18.4.0 → stock Strata v0.1.27, Qwen3.8-Flash-Next Coder IQ1_M, 131,072-token context, one
Windows 11 + RTX 5090 host (`rtx5090-win-a`), local loopback route, single user. The evidence is in
`releases/win11-rtx5090-coder-iq1m-131k/qualification.json` (receipts and scrubbed results) and in
`docs/MEASUREMENTS.md`. The three decisions below are separate. None of them depends on a comparison with NInfer,
and none was made.

## 1. Integration readiness: working candidate, not qualified

**Passed.** These capabilities are supported within the limits stated. The last row is host-free; every other row
ran on the real host.

| Gate | Result |
|---|---|
| G10 | Pinned identity on the actual host, and exclusive GPU use |
| G11 | Typed read/glob/edit/bash tool loops through the real stock client: 16/16 tracer runs |
| G12 | Live prefix reuse inside a session |
| G13 | Loopback only, with authentication on every model and control route. The launcher fails closed on a missing key. All model roles, including compaction, route locally. |
| G15, G16 | Continuing after an engine, client or full server restart from OMP's own transcript: replay with a full re-prefill, never state restoration |
| G17 | The 131,072 window: exact server limit, near-limit tool turns, explicit overflow |
| G18 | OMP compaction at a reduced threshold, and at the production threshold in a long session |
| G19 | Interleaved sessions, resume and branch |
| G20 | Controlled lifecycle with no orphans, and unrelated host state preserved |
| G21 | A measured resource fit: no watchdog stop, OOM or CUDA error in 629 logged requests |
| G26 | Every `docs/QUICKSTART.md` command, run as written into a fresh root on the same host, exited 0; the agent fixed the sample project, and the generated files matched the qualified root |
| G00–G03, G05, G06 | Source audit, pins, client isolation, real OMP against scripted streams, lifecycle edge cases, public CI |

**Failed, release-blocking (upstream defects; details in `docs/UPSTREAM.md`).**

- **G04.** When the model's turn ends inside a tool call, Strata reports `tool_calls`/`stop` with closed partial
  arguments. OMP then executes the truncated call: a partial file write happens and the run exits 0. No
  supported setting avoids it.
- **G14.** A client that disconnects while its request is queued poisons the next long-prompt request (HTTP 400
  `cancelled`) and crashes the engine, which restarts after one more failed request. The workaround is `restart`.
  One OMP process never has two requests in flight (the integration caps it at one), so the trigger needs a second
  concurrent client, such as a second OMP session.

**Needed a workaround in this integration.**

- Stock OMP fetches its public model catalog at every start. The launcher's proxy guard stopped this in
  observation, but it is not enforcement.
- OMP's fitted output cap overshot the strict window by 21 tokens. The declared window is now 1,024 tokens
  smaller.
- The first turn after a mid-generation engine crash ended in an OMP-detected reasoning loop in 2 of 3 trials.
  It was an explicit error, and later turns recovered.

**Not supported.** Images (G22), remote clients (G23), comparative claims (G25), durable engine state and
multi-tenant use.

**Verdict.** The route works end to end for single-user local coding. It is not qualified while G04 and G14
fail. Qualification needs an upstream fix for each defect, or an explicit acceptance of the risk by the owner,
and then affected-gate requalification.

**Upstream status (re-checked 2026-09-30).** Strata v0.1.28 fixes the G14 defect (Strata#183). Adopting it is a
new profile, with the affected gates, G14 included, requalified on the real host. v0.1.28 does not fix G04's Strata
half: its frontend still closes a call cut off by the end of the turn and reports `tool_calls` (mock tier). Fixes are
proposed for both halves: Strata#231 and can1357/oh-my-pi#13868 (both open); see `docs/UPSTREAM.md`.

## 2. Usefulness: keep as an optional local coding backend

- **Observed outcome.** 16/18 verified passes on the bounded six-task evaluation: five tasks 3/3, the tool-heavy
  settlement task 1/3. There were no protocol errors, timeouts or aborts. Median task wall time was 52 s,
  including tools and verification.
- **Why it is useful.** It covers bug fixes, a multi-file regression, retrieval from a large archive, and
  continuation across a client and server restart.
- **Costs.**
  - The RTX 5090 is fully occupied: 30,836 of 32,607 MiB of VRAM.
  - The engine holds about 30 GB of RAM resident and commits about 63 GB, which needs a page file on a 47 GiB
    host. About 9 GB of RAM stays available while serving.
  - 69.5 GB of disk.
  - About 15 s to start or to restart the engine.
  - One engine serves one request at a time (FIFO).
  - Operationally: the two defects above, the egress guard, and the need to release the GPU from any other
    tenant.
- **Recommendation.** Keep it as an optional backend for local, private, single-user coding sessions. Do not make
  it a default or a replacement for anything until G04 and G14 are fixed upstream. The evaluation is a small
  smoke of usefulness, not a benchmark. No quality threshold was set in advance, and none is claimed.

## 3. Further investment in engine-state durability: not justified now

Restart pain was measured and is modest:
- An engine reload takes about 14 s.
- Replaying a transcript costs a cold prefill at about 4K tokens/s for small prompts and 6.3K tokens/s at 100K
  tokens. That is about 2 s for a typical 7K-token coding session and about 17 s at the largest prompts that fit.
- Client restarts keep the live cache.
- Continuation after a full server restart passed 3/3 in the evaluation.

The observed failures were not caused by missing state: they are the two upstream defects above and a
model-level reasoning loop. A durable engine-state (KV/recurrent/MTP snapshot) design would save at most those
seconds per restart, at a large correctness and maintenance cost.

**Recommendation.** Do not start a durability subsystem. Spend the next effort on:
1. Filing the two upstream defects with the reproducers in this repository.
2. Asking OMP for an offline switch for the catalog refresh.
3. Requalifying the affected gates once fixed releases exist.

Revisit durability only if real use shows long sessions restarting often enough for re-prefill time to matter.
