# omp-strata

Run the stock [OMP](https://github.com/can1357/oh-my-pi) coding agent (v18.4.6) against a stock, local
[Strata](https://github.com/Niko1221/Strata) inference server (v0.1.30) on one Windows 11 + RTX 5090 host,
with pinned components, a small lifecycle tool and acceptance evidence.

This repository forks neither project and adds no proxy. It pins and verifies downloads. It installs Strata with
its own unmodified `setup.py` from verified local inputs, starts it on loopback behind an API key, and launches
stock OMP in an isolated profile where every model role points at that server.

## Status

**Candidate, not qualified.** The current candidate profile,
`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6` (Qwen3.8-Flash-Next Coder IQ1_M, 131,072-token context),
passes every integration gate on real hardware except one, which fails on an upstream defect; see the ledger in
[`releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/qualification.json`](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/qualification.json)
and [`docs/DECISION.md`](docs/DECISION.md). The first candidate, `win11-rtx5090-coder-iq1m-131k` (Strata v0.1.27,
OMP 18.4.0), keeps its own ledger and remains the rollback installation; its second blocker, the queued-cancel
engine crash, is fixed in this candidate (see [`docs/UPSTREAM.md`](docs/UPSTREAM.md)).

| Area | Result on the real host (2026-10-01) |
|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass: 3/3 tracer runs |
| Live prefix reuse in a session | pass (engine-reported, 12/12); lost on engine restart; interleaved sessions share only the system prefix |
| Loopback, API key (now on `/status` too), fail-closed client, local-only routing | pass, with an egress guard for OMP's startup catalog fetch |
| Engine or client restart, then continue from OMP's transcript | pass: an engine restart re-prefills the whole transcript; a client restart keeps the live cache; no state restoration |
| 131,072-token window: exact limit, near-limit tool turns, explicit overflow | pass |
| OMP compaction (reduced threshold and production long session) | pass |
| Cancelling a *queued* request | pass: the next long requests are served by the same engine (fixed since Strata v0.1.28) |
| Tool call cut off mid-arguments | **fail**: OMP runs the tool with truncated arguments (OMP/Strata defect; fixes proposed upstream) |
| Six-task coding evaluation, 18 scored attempts | 15/18 verified passes (tool-heavy task 0/3, same hidden test each time; 16/18 on the first candidate); no protocol errors or timeouts |
| `docs/QUICKSTART.md` commands into a second root on the same host | pass: every command exits 0; 15 of 17 generated files identical to the first root, only the engine differs |

**Third tuple on 24 GB GPUs (draft profiles, 2026-10-01).** Stock Strata v0.1.31, which fixes Strata's half of the
cut-off tool call, and stock OMP 18.4.8 pass every real-host gate on an RTX 3090 (64 GiB RAM) and an RTX 4090
(32 GiB RAM, stock low-RAM mode) except the same G04, which now fails only on OMP's side; evaluation 17/18 and
15/18. Ledgers:
[`releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/`](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/qualification.json)
and
[`releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/`](releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/qualification.json);
figures in [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md).

Not supported: images, remote clients, other operating systems, durable engine state, multiple tenants, and any
comparison with other runtimes. GPUs other than the RTX 5090 have draft profiles only.

## Use it

[`docs/QUICKSTART.md`](docs/QUICKSTART.md) has the exact tested commands:
`fetch` → `install` → `keygen` → `start` → `launch-omp` → `stop`.

## Documents

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md): install, start, use, stop
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md): lifecycle, recovery, logs, upgrades
- [`docs/SECURITY.md`](docs/SECURITY.md): what is and is not isolated, observed egress, known defects
- [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md): resources, throughput, context, restart cost, evaluation results
- [`docs/DECISION.md`](docs/DECISION.md): integration readiness, usefulness, further investment
- [`docs/BASELINE.md`](docs/BASELINE.md): the frozen component tuple and why it was chosen
- [`docs/handoff/2026-09-30/`](docs/handoff/2026-09-30/): the execution packet this work implements

## Layout

| Path | Purpose |
|---|---|
| `profiles/` | The candidate profiles (current, first and the third tuple's drafts): every artifact pinned by URL, size and SHA-256 |
| `locks/` | Hash-locked Python wheels for stock `setup.py` |
| `omp_strata/` | Stdlib-only tooling: fetch/verify, install, lifecycle, OMP configuration, transcripts |
| `scripts/omp_strata.py` | The operator CLI |
| `scripts/tracer.py`, `scripts/realhost_gates.py`, `scripts/requalify.py` | Real-host qualification probes and the unattended sequence that runs them (on the GPU host) |
| `scripts/evaluate.py`, `eval/` | The frozen six-task evaluation |
| `scripts/verify_release.py` | Checks that the profile, ledger and receipts bind together |
| `releases/<profile>/` | Manifest, gate ledger, receipts and scrubbed evidence |
| `tests/` | Host-free unit tests and mock-tier tests with the real stock OMP client |

Host-free checks (no GPU). `dev-env` provides what the client and composed tests need: this platform's pinned OMP
binary, the pinned Strata source, and a Python 3.13 env (the lock's interpreter, which must be on `PATH`) with stock
`setup.py`'s packages at the lock's versions. The CUDA wheels are left out, and versions are pinned but not
hash-checked because the lock hashes Windows wheels. It prints the `OMP_STRATA_*` variables, or runs a command with
them set; CI runs the same command. Without those variables the client and composed tests skip explicitly.

```sh
python3 scripts/omp_strata.py dev-env --profile profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6.json -- \
  python3 -m unittest discover -s tests -t .
python3 scripts/verify_release.py --manifest releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/manifest.json
```
