# Measurements

Host **rtx5090-win-a**: Windows 11 Pro, RTX 5090 32,607 MiB (driver 610.88), 47.15 GiB RAM, a 31 GB page file,
a 16-core AVX-512 CPU and NVMe storage. Two candidates were measured on it, with the same model
(Qwen3.8-Flash-Next Coder IQ1_M), 131,072-token context, INT8 KV and MTP speculation. The second candidate's
figures come first; the first candidate's section is kept unchanged as dated history.

## Candidate 2 (2026-10-01): stock Strata v0.1.30, stock OMP 18.4.6

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
  tool-loop fixes that passed the visible tests but failed the same hidden settlement test (cross-account
  de-duplication of voids); candidate 1 failed that test in two of its three attempts. No attempt timed out,
  aborted, hit a cap or compacted, and there were no protocol errors.
- The batch took 932 s. Task wall time ranged from 24.5 to 107.9 s, with a median of 45.8 s over all 18
  attempts, including verification. Reported output per attempt was 2.9K-15.0K tokens.
- A non-scored pilot before scoring passed 5/6 (tool-loop failed). The harness then ran unchanged.
- **Boundary:** as for candidate 1, the evaluation ran under the host operator's account without an OS sandbox
  (the owner-approved deviation), and there is no comparison with any other runtime or model.

### Second-root install (G26)

`fetch` 47 s (391 MB of OMP, engine and llama.cpp archives downloaded and verified; the two shards reused and
re-hashed), `install` 316 s, first `start` to readiness 18.6 s, the quickstart's non-interactive `launch-omp`
example 7.6 s (the model fixed the sample project), tracer 3/3, `stop` with the GPU back at 0 MiB.

## Candidate 1 (2026-09-30): stock Strata v0.1.27, stock OMP 18.4.0

Profile `win11-rtx5090-coder-iq1m-131k`: stock OMP 18.4.0 and stock Strata v0.1.27 with Qwen3.8-Flash-Next Coder
IQ1_M, a 131,072-token context, INT8 KV, MTP speculation. Measurements were taken on 2026-09-30 (UTC).

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
