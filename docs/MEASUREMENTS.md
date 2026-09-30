# Measurements

Host **rtx5090-win-a**: Windows 11 Pro, RTX 5090 32,607 MiB (driver 610.88), 47.15 GiB RAM, a 31 GB page file,
a 16-core AVX-512 CPU and NVMe storage. Profile `win11-rtx5090-coder-iq1m-131k`: stock OMP 18.4.0 and stock
Strata v0.1.27 with Qwen3.8-Flash-Next Coder IQ1_M, a 131,072-token context, INT8 KV, MTP speculation.
Measurements were taken on 2026-09-30 (UTC).

Boundaries used below:
- **wall** is a monotonic clock around a whole client action.
- **server** figures are stock Strata's own per-request records (`/metrics`: `prompt_ms`, `decode_ms`, `reused`).
- **sampler** figures are system counters: `nvidia-smi` and `GlobalMemoryStatusEx` every 2 s, plus the per-process
  `K32GetProcessMemoryInfo` lifetime peaks.

A restarted engine with a warm OS file cache is *process-cold, file-cache-warm*. Every figure comes from this
repository's probes; nothing is borrowed from upstream READMEs. Receipts and scrubbed raw results are under
`releases/win11-rtx5090-coder-iq1m-131k/`.

## Resources (G10, G21)

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

## Throughput (server-reported)

| Case | Value |
|---|---|
| Cold prefill, 104,827 tokens | 16,636 ms (6.3K tokens/s) |
| Cold prefill after an engine restart, 7,123 tokens | 1,796 ms (4.0K tokens/s) |
| Cached continuation, 105,429 tokens with 105,040 reused | 282 ms prompt time |
| Decode, short contexts | 142-234 tokens/s (MTP speculation on) |
| Decode at ~105K context | 157-158 tokens/s |

## Agent turns (wall)

| Case | Value |
|---|---|
| Tracer turn 1: read, edit and test with 3-4 tool calls on a ~7K-token prompt | 4.1-6.9 s |
| Tracer turn 2: `--continue`, no tools | 1.1-1.3 s |
| Prefix reuse on same-session continuations | 12/12 requests reused 6.8K-8.2K tokens |
| Continuation after another session interleaved (A-B-A) | only the shared 6,830-token system prefix reused |

## Restart cost (G15, G16, G20)

- **Engine killed while idle.** The next OMP turn took 16-17 s: about 14 s to reload the engine, a cold re-prefill
  of the whole transcript (7.1K tokens, 1.8 s), then decode.
- **Engine killed mid-generation.** The cut turn ends as an error. The next turn took 16.2 s, on the same path. In
  2 of 3 trials, that first post-crash turn ended in an OMP-detected reasoning loop (an explicit error) instead of
  an answer; later turns recovered.
- **Client restart.** The next turn took 1.3 s, with the live prefix cache intact.
- **Client and full server restart.** The server was ready in 14.5 s, and the next turn took 3.1 s: a re-prefill
  of 7,400 tokens in 1.9 s plus decode.

## Context (G17, G18)

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

## Network (G13)

These counts come from ETW `Microsoft-Windows-Kernel-Network` events attributed to the OMP and Strata process
trees:
- **Without the launcher's egress guard:** 244 packet events to 2 non-loopback HTTPS endpoints (OMP's startup
  model-catalog refresh), plus loopback probes of ports 11434, 8080 and 1234.
- **With the guard:** 0 non-loopback events out of 3,711 attributed events, over a typed tool turn and a
  compaction turn.

## Coding evaluation (G24)

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

## Clean install (G26)

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
