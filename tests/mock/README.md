# Host-free stock-client qualification

These tests run the **real, pinned OMP binary** of the selected profile (18.8.4 for
`win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4`, the current qualified tuple),
not a fake client. Earlier tuples and drafts remain selectable through their
own profiles. Python 3.11+ and the integration harness use only
the standard library. All credentials, canaries, git fixtures, processes and session
files are disposable test data.

## Run

Run the suite through `dev-env`. It fetches and verifies this platform's pinned
OMP binary, checks out the pinned Strata source, prepares its Python env, and runs
the command with `OMP_STRATA_OMP_BINARY`, `OMP_STRATA_STRATA_SRC` and
`OMP_STRATA_STRATA_PYTHON` set. CI runs the same command:

```sh
python3 scripts/omp_strata.py dev-env \
  --profile profiles/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4.json -- \
  python3 -m unittest discover -s tests -t . -v
```

`dev-env` also exports `OMP_STRATA_PROFILE`; the suite reads the profile it names
(`tests/candidate.py`) and defaults to the current candidate, so the first candidate's
pins can still be exercised by pointing `dev-env` at its profile.

Without `OMP_STRATA_OMP_BINARY` (or when its file is absent), real-client tests
explicitly skip. Without `OMP_STRATA_STRATA_SRC`, the composed check skips.
`OMP_STRATA_STRATA_PYTHON` defaults to the current interpreter, which then needs
**Strata's upstream requirements** (not integration dependencies). A supplied
checkout at the wrong commit or lacking its dependencies fails. The frontend runs
its stock `python -m serve.server --engine mock` entrypoint with `--script`,
loopback-only binding, an ephemeral port and an environment key. It uses its byte
tokenizer and a smaller **test-only** context/output budget; this does not change
the candidate profile. Tests never download dependencies or model files.

## Evidence boundaries

- **G02:** missing/blank launcher credentials fail before launch; raw stock missing
  credentials dispatch `Bearer STRATA_API_KEY` and fail on HTTP 401. Runtime
  canaries cover foreign project/home instructions and project MCP startup.
  Effective settings and emitted schema keys are checked; unsafe route/discovery
  overrides are rejected. Native `.omp` project configuration remains trusted.
- **G03:** role/reasoning/content chunks, keepalive comments, split multibyte UTF-8,
  fragmented/multiple typed calls, real read/write/bash effects, tool-result ID
  association, persisted transcript integrity and usage/cache accounting.
- **G04:** HTTP errors, connection loss, malformed SSE, Strata in-band errors,
  stalled-stream cancellation and persisted-side-effect resume. HTTP 500 retries
  are measured rather than falsely advertised as disabled. Unsafe truncation
  cases remain explicit expected failures only on older pins without the upstream fixes.
- **Composed frontend:** real Strata authentication, Qwen XML parsing, a typed read
  cycle, and cutoff behavior through its actual MockEngine/frontend and OMP.

These do **not** qualify GPU execution, C++ inference, model quality, live prefix
reuse, native Windows lifecycle, long-context memory capacity, or any real-host
gate. Recorded model requests go to the designated loopback server, but this is
not an OS-enforced egress audit or a sandbox for arbitrary fixture tools.

## Current tuple (Strata v0.1.40.3, OMP 18.8.4)

The current profiles' host-free receipts (2026-10-08: RTX PRO 6000 with batch slots and parking, RTX 5090 and
RTX 3090) record 380 tests, one skip and no expected failures each, with the pinned OMP 18.8.4 binary. CI runs the
RTX PRO 6000 profile in its own lane.

## RTX PRO 6000 slots-and-parking rollback tuple (Strata v0.1.40.3, OMP 18.8.3)

Its host-free receipts (2026-10-07) record 376 tests, one skip and no expected failures. With this profile as the
candidate, OMP's effective settings carry an in-flight limit of four for the server (its batch slots), and the G25
comparison fixture writes the `"parallel"` key stock setup writes for it; both failed until the fixture and the test
followed the profile, so CI runs this tuple in its own lane.

## Earlier RTX PRO 6000 rollback tuple (Strata v0.1.40.2, OMP 18.8.0)

Its host-free receipts (2026-10-07) record 369 tests, one skip and no expected failures.
`test_speculative_compaction.py` sends a turn into OMP's speculation band (just below its compaction threshold) and
fails when anything but the agent's own turns reaches the server. Before the integration set
`compaction.asyncEnabled: false` it failed with OMP 18.4.10, 18.5.0 and 18.8.0: OMP sent a background summary
request first. G04 behaves as on the fourth tuple.

## Fourth tuple (Strata v0.1.34, OMP 18.4.10)

G04 passes with the released fixes on both sides: Strata leaves a cut-off call unfinished, and OMP refuses the
incomplete argument JSON without executing the tool. The 2026-10-02 host-free receipts for all three fourth-tuple
profiles record 114 tests, one skip and no expected failures. The version-aware cutoff assertions still expose
the defects as expected failures when run with older pins; they are ordinary passing assertions on this tuple.
Host-free success does not substitute for the separately recorded real-host gates.

## Historical stock behavior (first and second tuples)

First recorded with OMP `401778d0cd30020ce0f9198f751b13c68850562f` and Strata
`a79080535d1b2a71a3419a0d97d8e7dca194b0f1`; every item below was observed again,
unchanged, with OMP 18.4.6 (`8b25ad4a05625dde65df41d057756b4815f4837c`) and Strata
v0.1.30 (`30ec18ec7094550fcc594fd948220d511d80464e`) on 2026-10-01 (98 tests, the same
3 expected failures).

- Wire: `max_tokens: 32768`, `stream_options: {include_usage: true}`; explicit
  fixture tools are `read`, `write`, `bash`. Neither `tool_choice` nor
  `parallel_tool_calls` is present. Thinking `off/low/medium/high/xhigh` sends
  `low/low/medium/high/high`. In particular, **off does not disable reasoning**
  with this stock OpenAI effort dialect. Only low/medium/high are advertised;
  xhigh clamps to high, which Strata maps to its xhigh template level.
- The rendered compaction reserve is the profile output budget plus 4096 tokens
  (36864 for this candidate), rather than OMP's smaller automatic reserve. This
  starts compaction before Strata's untruncated prompt plus full `max_tokens`
  request would exhaust the configured context. The registered value is checked
  through the real binary; this is not a long-session/GPU qualification.
- HTTP 400/401/404, dropped stream, malformed SSE and Strata's in-band error each
  make **one** request, exit 1, and persist `stopReason: error`. SIGINT exits 130;
  `--max-time 5s` exits 1; each stalled turn makes one request and never completes.
- **HTTP 500 still retries:** twelve identical requests, then exit 1/error, with
  no fallback provider. `packages/ai/src/utils/openai-http.ts:33,99` hardcodes six
  attempts; `packages/ai/src/providers/openai-completions.ts:1648-1651` enables one
  outer provider replay. Neither `retry.enabled: false` nor `retry.maxRetries: 0`
  disables these transport retries. The bounded test supplies `Retry-After:
  0.001`; an exploratory persistent-500 run without that header made eleven
  requests before its 25-second deadline. No automatic-no-resend claim is made.
- Resume: one bash append succeeds, its follow-up receives HTTP 400; `--continue`
  restores the same transcript and sends one further request without executing
  the append again (request counts 2 + 1, exactly one line in the file).
- **Three expected failures expose unsafe partial calls:**
  1. Unterminated JSON arguments followed by `tool_calls`/`[DONE]` are repaired
     by OMP; the write executes and OMP exits 0 after a follow-up answer.
  2. Partial JSON followed by an explicit closing fragment and `finish_reason:
     stop` is promoted to `toolUse`; the partial write executes, then exit 0.
  3. A real Strata MockEngine end token inside unfinished Qwen XML causes its
     parser to emit the closing arguments fragment `"}` and `tool_calls`; OMP
     writes the partial content and exits 0 with `[toolUse, stop]`.
  These are release-blocking findings, not qualified successes.
- **Length cutoff is different:** both scripted and composed `finish_reason:
  length` calls execute no side effect. OMP persists an associated error tool
  result explaining suppression, then requests continuation. A successful
  continuation exits 0 with `[length, stop]`. The real frontend's 256-token
  cutoff emitted valid JSON via the same `"}` fragment (108 content bytes);
  the natural premature end emitted 15 content bytes and `tool_calls`.
- The pinned OMP commit has domain settings files, **not** `settings-schema.ts`.
  Privacy keys are `dev.autoqa`, `dev.autoqaConsent` and
  `telemetry.otlpExportEnabled`; unsupported `autoqa.enabled`/`stats.sync` keys are
  not emitted. `--no-tools` disables builtins, not merely foreign discovery, and
  is deliberately absent from the launcher.
- An unknown `models.yml` compat property is accepted and dispatch proceeds;
  stock validation is not a typo detector. Our emitted-key allowlist guards that
  gap, effective settings are checked with `config list --json`, and an invalid
  known model enum is proven to fail before dispatch. Schema provenance is in
  `test_ompcfg.py`; no private audit files are copied here.
