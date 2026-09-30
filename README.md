# omp-strata

Run the stock [OMP](https://github.com/can1357/oh-my-pi) coding agent (v18.4.0) against a stock, local
[Strata](https://github.com/Niko1221/Strata) inference server (v0.1.27) on one Windows 11 + RTX 5090 host,
with pinned components, a small lifecycle tool and acceptance evidence.

This repository forks neither project and adds no proxy. It pins and verifies downloads. It installs Strata with
its own unmodified `setup.py` from verified local inputs, starts it on loopback behind an API key, and launches
stock OMP in an isolated profile where every model role points at that server.

## Status

**Candidate, not qualified.** The one candidate profile, `win11-rtx5090-coder-iq1m-131k`
(Qwen3.8-Flash-Next Coder IQ1_M, 131,072-token context), passes the core integration gates on real hardware.
Two required gates fail on upstream defects; see the ledger in
[`releases/win11-rtx5090-coder-iq1m-131k/qualification.json`](releases/win11-rtx5090-coder-iq1m-131k/qualification.json)
and [`docs/DECISION.md`](docs/DECISION.md). Strata v0.1.28 fixes the queued-cancel defect but not the truncated
tool call; the profile still pins v0.1.27 (see [`docs/UPSTREAM.md`](docs/UPSTREAM.md)).

| Area | Result on the real host |
|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass: 16/16 tracer runs, 3/3 on the final commit |
| Live prefix reuse in a session | pass (engine-reported); lost on engine restart; interleaved sessions share only the system prefix |
| Loopback, API key, fail-closed client, local-only routing | pass, with an egress guard for OMP's startup catalog fetch |
| Engine or client restart, then continue from OMP's transcript | pass: an engine restart re-prefills the whole transcript; a client restart keeps the live cache; no state restoration |
| 131,072-token window: exact limit, near-limit tool turns, explicit overflow | pass |
| OMP compaction (reduced threshold and production long session) | pass |
| Cancelling a *queued* request | **fail**: the next long request fails and the engine restarts (Strata defect; fixed in v0.1.28, not requalified) |
| Tool call cut off mid-arguments | **fail**: OMP runs the tool with truncated arguments (OMP/Strata defect; still in Strata v0.1.28) |
| Six-task coding evaluation, 18 scored attempts | 16/18 verified passes (tool-heavy task 1/3); no protocol errors or timeouts |
| `docs/QUICKSTART.md` run as written into a fresh root on the same host | pass: every command exits 0; generated files match the qualified root |

Not supported: images, remote clients, other GPUs or operating systems, durable engine state, multiple tenants,
and any comparison with other runtimes.

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
| `profiles/` | The candidate profile: every artifact pinned by URL, size and SHA-256 |
| `locks/` | Hash-locked Python wheels for stock `setup.py` |
| `omp_strata/` | Stdlib-only tooling: fetch/verify, install, lifecycle, OMP configuration, transcripts |
| `scripts/omp_strata.py` | The operator CLI |
| `scripts/tracer.py`, `scripts/realhost_gates.py` | Real-host qualification probes (run on the GPU host) |
| `scripts/evaluate.py`, `eval/` | The frozen six-task evaluation |
| `scripts/verify_release.py` | Checks that the profile, ledger and receipts bind together |
| `releases/<profile>/` | Manifest, gate ledger, receipts and scrubbed evidence |
| `tests/` | Host-free unit tests and mock-tier tests with the real stock OMP client |

Host-free checks (no GPU):

```sh
python3 -m unittest discover -s tests -t .
python3 scripts/verify_release.py --manifest releases/win11-rtx5090-coder-iq1m-131k/manifest.json
```

Set `OMP_STRATA_OMP_BINARY` to a fetched stock OMP binary to run the client tests. Also set
`OMP_STRATA_STRATA_SRC` and `OMP_STRATA_STRATA_PYTHON` to a Strata v0.1.27 checkout and its Python to compose the
real Strata frontend. Without them those tests skip explicitly.
