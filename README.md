<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
  <img src="assets/logo-light.svg" alt="" width="72" height="72">
</picture>

# OMP Strata

**Stock Oh My Pi on a stock, local Strata server. Nothing forked, everything pinned.**

**Current, qualified tuple: stock OMP `18.8.6` on stock Strata `v0.1.41`, both as released. No fork, no proxy, no cloud fallback.**

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
[profile]: profiles/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6.json
[strata-badge]: https://img.shields.io/badge/Strata-v0.1.41-37C4CB?labelColor=0B0E11
[omp-badge]: https://img.shields.io/badge/OMP-18.8.6-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-strata?color=1C232B&labelColor=0B0E11

<sub><strong>Private by design:</strong> loopback-only server · API key required · isolated OMP profile ·
no cloud fallback · every byte hash-pinned</sub>

</div>

> **Qualified on the RTX PRO 6000, RTX 5090 and RTX 3090 (2026-10-09).** The current tuple is stock Strata v0.1.41
> with stock OMP 18.8.6 at a 131,072-token context on the RTX PRO 6000 and the RTX 5090. On the RTX PRO 6000,
> Qwen3.8-Flash-Next IQ3_S keeps every expert in VRAM, with three choices stock setup offers for this host: four batch
> slots, conversation parking and 32K prompt chunks (`win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6`).
> The RTX 5090 runs Qwen3.8-Flash-Next Coder IQ1_M (`win11-rtx5090-coder-iq1m-131k-strata0.1.41-omp18.8.6`), and the
> RTX 3090 runs the same Coder on stock Strata v0.1.40.3 with stock OMP 18.8.4
> (`win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4`). Every applicable gate passes; G22 (images), G23 (remote
> clients) and G25 (runtime comparison) are not applicable to these local, text-only profiles. Ledgers:
> [RTX PRO 6000](releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json),
> [RTX 5090](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.41-omp18.8.6/qualification.json),
> [RTX 3090](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json).
> The rollbacks stay qualified. On the PRO: the same choices on stock Strata v0.1.40.3 + stock OMP 18.8.4
> ([ledger](releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4/qualification.json)), then
> on stock OMP 18.8.3
> ([ledger](releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3/qualification.json)), and
> before them stock Strata v0.1.40.2 + stock OMP 18.8.0 without them
> ([ledger](releases/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0/qualification.json)). On the RTX 5090: the
> same Coder on stock Strata v0.1.40.3 + stock OMP 18.8.4
> ([ledger](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json)). On the RTX 5090
> and RTX 3090, then the fourth tuple (stock Strata v0.1.34 + stock OMP 18.4.10, Coder IQ1_M), which also stays
> qualified on the RTX 4090 in stock low-RAM mode:
> [RTX 5090](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
> [RTX 3090](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
> [RTX 4090, low-RAM](releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10/qualification.json).
> Earlier tuples remain separate, unqualified rollback installations with their original ledgers:
> [first RTX 5090 candidate](releases/win11-rtx5090-coder-iq1m-131k/qualification.json),
> [second RTX 5090 candidate](releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/qualification.json),
> and the third-tuple RTX 3090 and RTX 4090 installations linked below. See [the decision](docs/DECISION.md)
> for the retained failures, the G15 probe correction, the G16 predicate fix and the OMP setting the RTX PRO 6000
> run led to.

## Status

| Area | Strata v0.1.41 + OMP 18.8.6: RTX PRO 6000, slots and parking (2026-10-08) | Coder IQ1_M: RTX 5090 on Strata v0.1.41 + OMP 18.8.6 (2026-10-09), RTX 3090 on Strata v0.1.40.3 + OMP 18.8.4 (2026-10-08) | Fourth tuple: rollback, and the RTX 4090's record (2026-10-02; G15 repeats 2026-10-03) |
|---|---|---|---|
| Typed tool loop (read/glob/edit/bash) through stock OMP → stock Strata | pass: 3/3 tracer runs | pass: 3/3 tracer runs per GPU | pass: 3/3 tracer runs per GPU |
| Live prefix reuse in a session (lost on engine restart) | pass: 13/13, engine-reported | pass: 14/14 (RTX 5090), 16/16 (RTX 3090) | pass: 12/12 per GPU |
| Interleaved conversations | pass: a conversation run after another comes back from its parked state, not read again | share only the system prefix | share only the system prefix |
| Requests at once | up to 4, decoded together | one at a time | one at a time |
| Loopback, API key (including `/status`), fail-closed client, local-only routing, with an egress guard for OMP's startup catalog fetch | pass | pass | pass |
| Engine or client restart, then continue from OMP's transcript (an engine restart re-prefills it; no state restoration) | pass | pass | pass |
| 131,072-token window: exact limit, near-limit tool turns, explicit overflow | pass | pass | pass |
| OMP compaction (reduced threshold and production long session) | pass, with OMP's speculative compaction off | pass, with OMP's speculative compaction off | pass; the RTX 4090's failed reduced-threshold probe remains recorded beside the passing rerun |
| Cancelling a *queued* request | pass, with all four slots generating | pass | pass |
| Tool call cut off mid-arguments (G04) | pass | pass | **pass** for the first time: stock Strata and stock OMP refuse the unfinished call |
| Six-task coding evaluation, 18 scored attempts | 15/18 (tool-heavy task 0/3) | RTX 5090: 15/18; RTX 3090: 15/18 | RTX 5090: 16/18; RTX 3090 and RTX 4090: 15/18 each |
| Guarded install and QUICKSTART example in a new root alongside earlier tuples (G26) | pass | pass on each GPU | pass on each GPU |

**Strata v0.1.41 + OMP 18.8.6 on the RTX 5090 (2026-10-09).** Only Strata and OMP move; the Coder IQ1_M, its pins
and the stock setup plan are the 18.8.4 profile's, which is now its rollback. Every gate passed; the ledger has 21
pass and 3 not applicable. The coding evaluation verified 15 of 18 (16 on 18.8.4); readiness, cold prefill and
resources are unchanged. The RTX 3090 stays on the 18.8.4 tuple. Figures in
[the measurements](docs/MEASUREMENTS.md#rtx-5090-every-gate-2026-10-09-stock-strata-v0141-stock-omp-1886).

**Strata v0.1.41 + OMP 18.8.6 on the RTX PRO 6000 (2026-10-08).** Strata and OMP both move; the PRO keeps IQ3_S,
the batch slots, parking and 32K prompt chunks, and the stock setup plan is the 18.8.4 profile's, which is now its
rollback. Every measured gate passed on its first run; the ledger has 21 pass and 3 not applicable. The coding
evaluation verified 15 of 18, as on 18.8.4. At that point the RTX 5090 and RTX 3090 stayed on the 18.8.4 tuple.
Figures in
[the measurements](docs/MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-08-stock-strata-v0141-stock-omp-1886).

**Strata v0.1.40.3 + OMP 18.8.4 on three GPUs (2026-10-08).** On the RTX PRO 6000 only OMP changes from the 18.8.3
profile; the RTX 5090 and RTX 3090 move from the fourth tuple to this one with the same Coder IQ1_M. Each
ledger has 21 pass and 3 not applicable. On the PRO, G16 first failed because its predicate counted mentions of the
script it checks rather than its runs; the fixed predicate's rerun passed, and the failure stays in the ledger. The
coding evaluation verified 15 of 18 on the PRO (16 on 18.8.3), 16 on the RTX 5090 and 15 on the RTX 3090, as on the
fourth tuple. Figures in
[the measurements](docs/MEASUREMENTS.md#three-gpus-every-gate-2026-10-08-stock-strata-v01403-stock-omp-1884).

**The RTX PRO 6000 (2026-10-05 to 2026-10-07).** A 96 GB RTX PRO 6000 replaced the RTX 4090 in its host. With the
same stock flags the engine keeps every expert of the original model's IQ3_S in VRAM and decodes 2.2-2.3× as fast as
on the RTX 4090 (258-271 tokens/s). On 30 Terminal-Bench 2.1 tasks stock setup's largest build, UD-Q4_K_XL, tied
IQ3_S at 19, so IQ3_S stays; Strata v0.1.40.1 then passed 21, with none of the tool calls left in the reasoning that
had stranded two v0.1.39 runs. The qualification moved both components to their newest stable releases. Its
near-limit gate found stock OMP's speculative compaction sending the single-sequence engine a background summary
that delayed the agent's next turn and evicted its cached prompt, so the integration now turns that off for every
profile ([`docs/UPSTREAM.md`](docs/UPSTREAM.md), OMP item 12). The slots-and-parking profile then moved to the next
stable releases and pinned what stock setup offers this host: four batch slots (overlapping requests decode 19%
faster in total), parking for up to four conversations (one resumed after another took 0.34 s instead of 3.3 s), and
32K prompt chunks (long prompts 8-24% faster). On the same 30 Terminal-Bench tasks, with the harness now on OMP 18.8.3,
it passed 19; the earlier counts used OMP 18.5.0, so they are context, not a paired comparison. Figures in
[the measurements](docs/MEASUREMENTS.md).

**Third tuple's rollback installations (2026-10-01).** Stock Strata v0.1.31 fixed Strata's half of the
cut-off tool call, but stock OMP 18.4.8 still failed G04. These unqualified profiles passed every other applicable
gate on an RTX 3090 (64 GiB RAM) and an RTX 4090 (32 GiB RAM, stock low-RAM mode); evaluation was 17/18 and
15/18. Their evidence is unchanged:
[RTX 3090 ledger](releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/qualification.json),
[RTX 4090 ledger](releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/qualification.json);
figures in [the measurements](docs/MEASUREMENTS.md).

**Strata against NInfer, on Strata v0.1.38 (2026-10-03).** Drafts on stock Strata v0.1.38 and stock OMP 18.5.0
for all three GPUs, and the first real G25 runs against the NInfer each host already runs, on the same frozen
evaluation through one pinned OMP binary. RTX 5090: Strata 15/18, omp-ninfer v0.10.0 14/18, and NInfer was faster
on the tasks (Strata's paired median 1.39× NInfer's). RTX 4090, after a memory fix for its new 192 GB, and RTX 3090:
15/18 each at even speed (0.98 on both). Strata reads long prompts 3-4× faster and restarts 2-5× faster; neither
frozen claim holds, so NInfer stays where it runs ([`docs/DECISION.md`](docs/DECISION.md)). With 192 GB the RTX 4090
is the one host where Strata's own calibration helps (up to 13% faster decode): calibrated IQ3_XXS decodes fastest,
the calibrated Coder is the coding configuration.

**Drafts for the next tuple and the upgraded hosts (2026-10-02, no gate has run on them).** Stock Strata v0.1.36
with stock OMP 18.4.12 for all three GPUs, plus a 262,144-token Coder and the unpruned Q2_0 for the RTX 4090 once it
has its new RAM, all drafted by `scripts/upstream_watch.py`; and two client routes that reach those servers from
another machine over SSH ([`docs/REMOTE.md`](docs/REMOTE.md)): one RTX 4090, and a three-GPU fleet that runs the main
session on one GPU and subagents on the others. On the RTX 3090, now with 128 GB, the original model's IQ3_S decodes
within 10% of the Coder and ties it on the coding evaluation, so the Coder stays for coding
([`docs/DECISION.md`](docs/DECISION.md)). Strata's own calibration keeps every default for the Coder on all three
GPUs (the RTX 4090 then in low-RAM mode) and speeds IQ3_S on the RTX 3090 by 4-5% at short contexts; the RTX 3090
also runs the Coder at its trained 262K context and, with stock setup's experimental yarn scaling, at 524K. Every
gate is `not_run`;
[`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) lists every profile's and route's ledger.

Remote use: one client route is qualified, stock OMP on a Mac Studio to the current RTX PRO 6000 profile through an
SSH local forward ([`docs/REMOTE.md`](docs/REMOTE.md); G23 passes on its own ledger). Not supported: images, servers
on other operating systems, durable engine state, multiple tenants, fleets (no fleet route is published) and other
client routes; every profile other than the qualified ones above remains a draft or a rollback installation.

## How it works

*Oh My Pi (coding-agent client) → OMP Strata (profile, lifecycle tool, evidence) → Strata (inference engine) →
Qwen3.8-Flash-Next (served model: IQ3_S on the RTX PRO 6000, Coder IQ1_M on the fourth tuple's GPUs).* Stock OMP
talks directly to stock Strata over OpenAI Chat Completions on `127.0.0.1:18090`. OMP owns transcripts, tools,
compaction and resume; Strata owns inference, templating and its live cache. After any restart OMP's transcript is
authoritative and the engine re-prefills it; nothing claims restored GPU state.

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

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md): install, start, use, stop
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md): lifecycle, recovery, logs, upgrades
- [`docs/SECURITY.md`](docs/SECURITY.md): what is and is not isolated, observed egress, known defects
- [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md): resources, throughput, context, restart cost, evaluation results
- [`docs/DECISION.md`](docs/DECISION.md): integration readiness, usefulness, further investment
- [`docs/BASELINE.md`](docs/BASELINE.md): the frozen component tuple and why it was chosen
- [`docs/UPSTREAM.md`](docs/UPSTREAM.md): findings reported to Strata and Oh My Pi, and what each release fixed
- [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md): every profile and client route with its recorded gate outcomes (generated)
- [`docs/REMOTE.md`](docs/REMOTE.md): the qualified Mac-to-RTX PRO 6000 client route over SSH, fleets, and the G23 probe
- [`docs/G25.md`](docs/G25.md): the controlled same-host comparison with NInfer (run on the RTX 5090, RTX 4090 and RTX 3090)
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md): the tooling's error messages, their causes and fixes
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
python3 scripts/omp_strata.py dev-env --profile profiles/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6.json -- \
  python3 -m unittest discover -s tests -t .
python3 scripts/verify_release.py --manifest releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6/manifest.json
```

## The OMP family

- [OMP NInfer](https://github.com/alphastorm/omp-ninfer): durable local inference, session state that survives an engine restart
- [OMP Session Gateway](https://github.com/alphastorm/omp-session-gateway): every live session, one private mobile page
- [OMP Oracle](https://github.com/alphastorm/omp-oracle): asynchronous web oracles for hard questions

## License

MIT. See [LICENSE](LICENSE). Oh My Pi, Strata, llama.cpp and the model retain their own licenses and notices.

Community project; not affiliated with or endorsed by the Oh My Pi maintainers, the Strata maintainer, Qwen or
NVIDIA.
