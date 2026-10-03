<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
  <img src="assets/logo-light.svg" alt="" width="72" height="72">
</picture>

# OMP Strata

**Stock Oh My Pi on a stock, local Strata server. Nothing forked, everything pinned.**

**Current, qualified tuple: stock OMP `18.4.10` on stock Strata `v0.1.34`, both as released. No fork, no proxy, no cloud fallback.**

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
[profile]: profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10.json
[strata-badge]: https://img.shields.io/badge/Strata-v0.1.34-37C4CB?labelColor=0B0E11
[omp-badge]: https://img.shields.io/badge/OMP-18.4.10-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-strata?color=1C232B&labelColor=0B0E11

<sub><strong>Private by design:</strong> loopback-only server · API key required · isolated OMP profile ·
no cloud fallback · every byte hash-pinned</sub>

</div>

> **Qualified on three GPUs.** The fourth tuple is stock Strata v0.1.34 + stock OMP 18.4.10, with
> Qwen3.8-Flash-Next Coder IQ1_M and a 131,072-token context. The current profile is
> `win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10`. Every applicable gate passes, including G04 for the first time;
> G22 (images), G23 (remote clients) and G25 (runtime comparison) are not applicable to these local, text-only profiles.
> Ledgers: [RTX 5090](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
> [RTX 3090](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
> [RTX 4090, low-RAM](releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10/qualification.json).
> Earlier tuples remain separate, unqualified rollback installations with their original ledgers:
> [first RTX 5090 candidate](releases/win11-rtx5090-coder-iq1m-131k/qualification.json),
> [second RTX 5090 candidate](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/qualification.json),
> and the third-tuple RTX 3090 and RTX 4090 installations linked below. See [the decision](docs/DECISION.md)
> for the retained failures and the G15 probe correction, not an engine patch.

## Status

| Area | Fourth tuple on all three GPUs (2026-10-02; G15 repeats published 2026-10-03) |
|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass: 3/3 tracer runs per GPU |
| Live prefix reuse in a session | pass (engine-reported, 12/12 per GPU); lost on engine restart; interleaved sessions share only the system prefix |
| Loopback, API key (including `/status`), fail-closed client, local-only routing | pass, with an egress guard for OMP's startup catalog fetch |
| Engine or client restart, then continue from OMP's transcript | pass: an engine restart re-prefills the whole transcript; a client restart keeps the live cache; no state restoration |
| 131,072-token window: exact limit, near-limit tool turns, explicit overflow | pass |
| OMP compaction (reduced threshold and production long session) | pass; the RTX 4090's failed reduced-threshold probe remains recorded beside the passing rerun |
| Cancelling a *queued* request | pass: the next long requests are served by the same engine |
| Tool call cut off mid-arguments (G04) | **pass**: stock Strata and stock OMP refuse the unfinished call; the partial tool never runs |
| Six-task coding evaluation, 18 scored attempts per GPU | RTX 5090: 16/18; RTX 3090 and RTX 4090: 15/18 each (tool-heavy task 1/3, 0/3 and 0/3 respectively) |
| Guarded install and QUICKSTART example in a new root alongside earlier tuples (G26) | pass on each GPU: install, start, example, project tests and stop exit 0; 3/3 tracer runs |

**Third tuple's rollback installations (2026-10-01).** Stock Strata v0.1.31 fixed Strata's half of the
cut-off tool call, but stock OMP 18.4.8 still failed G04. These unqualified profiles passed every other applicable
gate on an RTX 3090 (64 GiB RAM) and an RTX 4090 (32 GiB RAM, stock low-RAM mode); evaluation was 17/18 and
15/18. Their evidence is unchanged:
[RTX 3090 ledger](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/qualification.json),
[RTX 4090 ledger](releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/qualification.json);
figures in [the measurements](docs/MEASUREMENTS.md).

**Drafts for the next tuple and the upgraded hosts (2026-10-02, no gate has run on them).** Stock Strata v0.1.36
with stock OMP 18.4.12 for all three GPUs, plus a 262,144-token Coder and the unpruned Q2_0 for the RTX 4090 once it
has its new RAM, all drafted by `scripts/upstream_watch.py`; and two client routes that reach those servers from
another machine over SSH ([`docs/REMOTE.md`](docs/REMOTE.md)): one RTX 4090, and a three-GPU fleet that runs the main
session on one GPU and subagents on the others. On the RTX 3090, now with 128 GB, the original model's IQ3_S decodes
within 10% of the Coder and ties it on the coding evaluation, so the Coder stays for coding
([`docs/DECISION.md`](docs/DECISION.md)). Every gate is `not_run`; [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)
lists every profile's and route's ledger.

Not supported: images, servers on other operating systems, durable engine state, multiple tenants, and any
comparison with other runtimes (the G25 harness for one is ready but has not run). Remote clients and fleets exist
only as draft routes (G23 not run); newer tuples and other model/context variants remain unqualified.

## How it works

*Oh My Pi (coding-agent client) → OMP Strata (profile, lifecycle tool, evidence) → Strata (inference engine) →
Qwen3.8-Flash-Next Coder IQ1_M (served model).* Stock OMP talks directly to stock Strata over OpenAI Chat
Completions on `127.0.0.1:18090`. OMP owns transcripts, tools, compaction and resume; Strata owns inference,
templating and its live cache. After any restart OMP's transcript is authoritative and the engine re-prefills it;
nothing claims restored GPU state.

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
  role on the local server, discovery off, retries and model fallback off, ambient provider credentials scrubbed,
  and OMP's startup catalog fetch held to loopback by the launcher's proxy settings.
- Gate probes, a tracer and a frozen six-task evaluation run on the real host; scrubbed receipts under
  `releases/<profile>/` bind each result to the exact profile fingerprint.

## Documents

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md): install, start, use, stop
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md): lifecycle, recovery, logs, upgrades
- [`docs/SECURITY.md`](docs/SECURITY.md): what is and is not isolated, observed egress, known defects
- [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md): resources, throughput, context, restart cost, evaluation results
- [`docs/DECISION.md`](docs/DECISION.md): integration readiness, usefulness, further investment
- [`docs/BASELINE.md`](docs/BASELINE.md): the frozen component tuple and why it was chosen
- [`docs/UPSTREAM.md`](docs/UPSTREAM.md): findings reported to Strata and Oh My Pi, and what each release fixed
- [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md): every profile and client route with its recorded gate outcomes (generated)
- [`docs/REMOTE.md`](docs/REMOTE.md): draft client routes and fleets over SSH, and their G23 probe
- [`docs/G25.md`](docs/G25.md): the controlled same-host comparison with NInfer (harness ready, never run)
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md): the tooling's error messages, their causes and fixes
- [`docs/BRAND.md`](docs/BRAND.md): the visual identity, artwork sources and the public site
- [`docs/handoff/2026-09-30/`](docs/handoff/2026-09-30/): the execution packet this work implements

## Layout

| Path | Purpose |
|---|---|
| `profiles/` | The server profiles (current, first, and every later tuple's candidates and drafts): every artifact pinned by URL, size and SHA-256 |
| `routes/`, `examples/` | Draft client routes (server profile ids and fingerprints, ports, roles) and neutral private-binding examples |
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
python3 scripts/omp_strata.py dev-env --profile profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10.json -- \
  python3 -m unittest discover -s tests -t .
python3 scripts/verify_release.py --manifest releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/manifest.json
```

## The OMP family

- [OMP NInfer](https://github.com/alphastorm/omp-ninfer): durable local inference, session state that survives an engine restart
- [OMP Session Gateway](https://github.com/alphastorm/omp-session-gateway): every live session, one private mobile page
- [OMP Oracle](https://github.com/alphastorm/omp-oracle): asynchronous web oracles for hard questions

## License

MIT. See [LICENSE](LICENSE). Oh My Pi, Strata, llama.cpp and the model retain their own licenses and notices.

Community project; not affiliated with or endorsed by the Oh My Pi maintainers, the Strata maintainer, Qwen or
NVIDIA.
