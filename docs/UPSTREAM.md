# Upstream findings

These defects and surprises in the stock components were observed while qualifying OMP 18.4.0 (`401778d`)
against Strata v0.1.27 (`a790805`). Each has a reproducer in this repository. The Strata items are reported
upstream as linked below, after re-verification at the same Strata commit. The OMP items go upstream as pull
requests rather than issues, as upstream `CONTRIBUTING.md` asks for work the reporter will submit.
The integration works around them only where a supported setting exists.

Upstream status was re-checked on 2026-09-30 against Strata v0.1.28 (`bbaaabb`), on 2026-10-01 against
**v0.1.30 (`30ec18e`), pinned by the second candidate** (`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`,
which also moves OMP to 18.4.6), later on 2026-10-01 against **v0.1.31 (`9259cad`), pinned by the third tuple's
draft profiles** (RTX 3090 and RTX 4090 hosts, with OMP 18.4.8), and on 2026-10-02 against **v0.1.34 (`1678de3`),
pinned by the fourth tuple** (all three hosts, with OMP 18.4.10). v0.1.28 fixed items 1, 3, 4 and 6 and the second
candidate's real-host gates confirm them; v0.1.31 fixes items 2 and 5, and v0.1.34 keeps both fixes (host-free
suite; setup and server source reading). The upstream issues behind all six items are closed. The first candidate's
profile keeps v0.1.27 with every item present. "Mock tier" below means the stock frontend with its MockEngine (no
GPU).

**Upstream rewrote Strata's history on 2026-10-06** (v0.1.40.1 release notes). Every release tag now points to a
new commit; checked through the GitHub API for each tag a profile pins (v0.1.27 through v0.1.39), every new commit
has the same tree as the pinned one, so release contents did not change. Profiles keep their original commit pins,
and `install` fetches exactly those SHAs. GitHub still served all seven on 2026-10-06, but nothing upstream
references them any more, so a later install of an existing profile may fail once GitHub drops them. New drafts pin
the rewritten commits. The same notes number the hotfix `v0.1.40.1` with four parts, which `upstream_watch`
now reads (stock setup reads it as 0.1.40).

## Fifth tuple: Strata v0.1.36 / OMP 18.4.12 (host-free drafts)

On 2026-10-02 the release APIs resolved Strata `v0.1.36` to
`36fa455e579b23a9c909c2c6fe1bddd9e51cb8ca` and OMP `v18.4.12` to
`7318a70cf4ed04133366884d2723f72d9d490a15`. `scripts/upstream_watch.py report` found the four
newer releases below and resolved all 21 tracked issue/PR states. The five new profile ledgers remain
**draft, 24 gates `not_run`, no receipts**: no GPU host was used and the RAM upgrades are not assumed installed.

- [Strata v0.1.35 release notes](https://github.com/Niko1221/Strata/releases/tag/v0.1.35): Windows
  low-RAM resident mode frees the file cache before sizing residency and keeps the hottest experts that fit
  rather than falling back wholesale to SSD. Windows AMD loads its bundled HIP runtime; multi-GPU setup
  warns about a small second card limiting prompt chunks. Config writes are atomic, malformed `messages`
  become a 400, and `/metrics` gains draft counts. The Coder's weaker non-code/non-English behavior is
  explicitly documented upstream, supporting an unpruned Q2_0 draft rather than a quality claim here.
- [Strata v0.1.36 release notes](https://github.com/Niko1221/Strata/releases/tag/v0.1.36): Q2_0 uses
  fused int8 tensor-core prompt kernels on RTX 30 and newer by default. Upstream's speed/quality numbers
  are from its hardware, **not measurements of these profiles**; Q2_0 answers are intentionally not
  byte-identical to v0.1.35. RTX 50 long-context decode gains cluster kernels; IQ fused prompt kernels
  are opt-in. Cancellation logs and metrics now report the amount actually read; draft-head errors name
  smaller vocabulary alternatives. `expert_profile_save` / `--expert-profile-save` is new, **opt-in and
  off here**: learned expert-cache persistence is not part of this integration. The shipped expert
  profile and default CJK draft vocabulary stay pinned by the Strata source commit.
- **Never run `UPDATE.bat` or `update.sh`**, just as `START-HERE.bat` and `setup.sh` remain prohibited.
  Their convenient upstream update path changes source, Python packages, engine, model settings and
  draft vocabulary in place. This repository instead creates a new pinned profile, root and ledger.
- Source comparison v0.1.34 → v0.1.36 found five new quoted environment names: `STRATA_ARGMAX_MULTI`,
  `STRATA_PF_FUSED`, `STRATA_PF_FUSED_NATIVE`, `STRATA_PF_FUSED_TILE`, `STRATA_QSA_CLUSTER`.
  `server_env` strips **all inherited `STRATA_*`** and explicitly supplies the key; none of these
  knobs passes through. Changing kernel defaults, the draft vocabulary, expert profile or any other
  tuning option requires a reviewed new profile, never an ambient environment override.
- [OMP 18.4.11 release notes](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.11): malformed
  JSON for lenient tools such as `yield` is reported to the model instead of running with empty
  arguments; unrelated projects no longer inherit the default home's project configuration. Other
  relevant changes include Windows paste, FIFO/device read refusal and subagent MCP deadlines.
- [OMP 18.4.12 release notes](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.12): reduced
  streaming overhead, Windows session-path import and temp-cleanup fixes, and eval wait/dead broker
  fixes. Its new auth-gateway stdio mode is **not used here**: stock OMP still calls stock Strata
  directly over Chat Completions, with no gateway or fallback provider.

### Pins and stock planning evidence

The source checklist changed only `MIN_ENGINE` among the six audited setup constants: `MIN_DRIVER=580`,
`CUDA_WHEELS`, `PY_PACKAGES`, `LLAMA_CPP_COMMIT` and `HF_REVISIONS` are unchanged. Both tags'
`requirements.txt` blob is `3db8418ab428ea10f4b607b693cf6ad030fd0509`, so the existing
`locks/strata-python-cp313-win_amd64-strata0.1.31.txt` is reused with its original hash, not rewritten.
The same **11** top-level config keys are generated and the server route set is unchanged, with no
unclassified routes. Stock setup's pure choices/config arithmetic were evaluated at the requested
contexts: no low-RAM, context reduction or RoPE extension was needed.

| Draft variant | Context / OMP declared window | Total RAM floor / available at start (GiB) | Free disk floor (GiB) | Stock RAM thresholds |
|---|---|---|---|---|
| Coder IQ1_M, RTX 5090 | 131,072 / 130,048 | 45 / 34 | 90 | Low-RAM below 33.4; KV streaming from 34.7994 |
| Coder IQ1_M, RTX 3090 / 4090 | 131,072 / 130,048 | 60 / 34 | 90 | Low-RAM below 33.4; KV streaming from 34.7994 |
| Coder IQ1_M, RTX 4090 | 262,144 / 261,120 | 60 / 36 | 90 | KV streaming from 36.5987 |
| Unpruned Q2_0, RTX 4090 | 131,072 / 130,048 | 60 / 50 | 107 | Arena 34.0; low-RAM below 44.0; KV streaming from 50.7994 |

All five use stock `--kv-resident 32768`. Every floor is the **maximum of the predecessor's floor
and the setup-derived estimate**, never the purchased 128/192 GB. Predecessor floors preserve
operational headroom for observed integration-root sizes and engine peaks that setup's estimates
do not capture; a tuple bump may raise these constraints, never lower them. The draft JSON reports
both inputs and the selected floor. Setup estimates round up its low-RAM/streaming thresholds and
`ram_gb + KV`; the disk estimate uses exact shards (at least setup's estimate) plus setup's 8 GB
preparation allowance, converted to GiB.
Q2_0 conservatively includes its 40 GB AVX-512 conversion branch so the floor remains safe on either
CPU. These are preflight floors, not real-host capacity/performance evidence. `omp.context_window`
equals the configured engine context; `ompcfg.CONTEXT_SAFETY_TOKENS=1024` is subtracted when rendering
the route, not twice in the profile.

The release API pins `strata-windows-x64.zip` to **124,993,467 bytes**, SHA-256
`dfe40817661a4286f2a94b86452aef5eae54d8c0f23429868449b06086f4c266`; the OMP assets are
`omp-windows-x64.exe`, `omp-darwin-arm64` and `omp-linux-x64` (their API sizes/digests are in every
profile). No engine archive or model was downloaded. Q2_0 uses stock setup's
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` revision
`ed59f92082b1e93c0e96d60a8b11aab089b52f09`:

| Shard under `Q2_0/` | Bytes | Hugging Face LFS SHA-256 |
|---|---:|---|
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` | 37,623,740,192 | `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` |
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` | 28,800,138,432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |

Coder and Q2_0 both use `Qwen/Qwen3.8-Flash-Next` MTP revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`, resolved live, with the unchanged pinned tensor-manifest
digest `ced6fb728a94374d1fcbd1938b6543cf8ecb0a936d923cd3eca4923282a814b6`. No separate unpinned
draft model is introduced; stock setup builds the same Q2_0 MTP layer and copies the source-pinned
default draft vocabulary.

### Host-free run (2026-10-02)

The fifth-tuple dev-env provisioned the real Darwin ARM64 OMP binary and pinned Strata source.
`tests.unit.test_upstream_watch`: **13 tests, OK** (fixture transports, no network; includes the
nondecreasing host-floor regression); under the new
dev-env, `tests.unit.test_strata_surface tests.unit.test_profile`: **10 tests, OK**. All five profiles
validated, their release manifests verified, and `--require-ready` refused all five as intended.

A first mock-tier run under that dev-env, taken while the client-route tests were still being written, failed
three of them (a closed tunnel's TIME_WAIT mistaken for an occupied listener); the G04 truncated-call and
composed-cutoff cases passed. After those fixes the whole host-free suite ran once in each CI lane on
2026-10-02 (macOS arm64, sequentially):

| OMP binary / Strata source | Result |
|---|---|
| 18.4.6 / v0.1.30 | 188 tests OK (4 expected failures: the G04 defects of those versions) |
| 18.4.8 / v0.1.31 | 188 tests OK (1 skipped, 2 expected failures) |
| 18.4.10 / v0.1.34 | 188 tests OK (1 skipped) |
| 18.4.12 / v0.1.36 | 188 tests OK (1 skipped) |

The existing version thresholds in `tests/candidate.py` already select the right G04 expectations for
18.4.12/v0.1.36. No GPU gate ran.

## Strata

1. **A queued client's disconnect poisons the next long request and crashes the engine.** Reproduced 2/2 by
   `scripts/realhost_gates.py g14q`; the control case is clean. Upstream: same root cause as
   [Strata#183](https://github.com/Niko1221/Strata/issues/183). **Fixed in v0.1.28** by #205 (`6cad1fe`; #194 was
   closed unmerged): `err` is now cleared at the start of every request, right after the line cited below, before
   each prompt segment and on entry to `Prefill::run` (source reading). The v0.1.28 release notes report a long
   prompt cancelled and then sent again, followed by a short one, with the engine staying up. **Confirmed on the
   real host with v0.1.30** (second candidate, G14 and `g14q` pass): both queued-disconnect scenarios and the control
   served two consecutive 8,123-token prompts with the same engine process.
   - Steps: request A is generating and request B is queued behind it; B's client disconnects. Then the next
     request whose prompt needs more than one prefill window (about 8K tokens here) fails with HTTP 400
     `cancelled`, the engine exits with code 1, and the request after that gets HTTP 503 before the lazy restart.
   - Short prompts in between are served normally.
   - Cause: B reaches the engine after A and is stopped while it reads its prompt, which leaves the engine's `err`
     string set to `cancelled`. The next request clears `stop_req` but not `err`
     (`src/program/generate.cpp:3561`), so a prompt read in batched chunks fails on its first chunk and the serve
     loop exits with code 1 (`:3996-4000`). The windowed path used for short prompts does not check `err` first.
   - Workaround here: `omp_strata.py restart`.
2. **Tool calls cut off mid-arguments are finalized as complete.** When the model ends its turn inside a tool
   call, `OutputParser.finish()` closes the partial JSON and the response reports `finish_reason: tool_calls`.
   Clients then execute truncated arguments; see OMP item 1. Reproducer:
   `tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body_is_not_reported_as_complete`
   (the stock frontend with its MockEngine). A cut on `finish_reason: length` is correctly reported. Upstream: the
   second trigger of [Strata#210](https://github.com/Niko1221/Strata/issues/210); our #211 was closed as its
   duplicate, then reopened with a repro at v0.1.28, which fixed only the first trigger (`</parameter>` or
   `</tool_call>` inside an argument). **Fixed in v0.1.31** by
   [Strata#231](https://github.com/Niko1221/Strata/pull/231) (`925c354`, with `9a1fc19`): an announced call the
   output ends inside stays unfinished, its JSON is not closed, and the answer ends with `stop` (or `length`)
   instead of `tool_calls`; a non-streamed answer leaves such a call out. On the mock tier with v0.1.31 the
   reproducer's stream now ends with `stop` and unterminated arguments. With stock OMP 18.4.8 the composed G04 case
   still failed, because that client turned the stream into a tool turn and ran the truncated write (OMP item 1).
   With OMP 18.4.10 (fourth tuple, Strata v0.1.34) the composed case passes: OMP answers the call with the parse
   error, writes nothing, and the model continues (stop reasons `toolUse`, `stop`; exit 0).
3. **`/status` is unauthenticated and includes a tail of the generated text.** With an API key set, any local
   process can still read the last 600 characters of the current answer, and of the most recent one while the
   server is idle, because the tail is not cleared when a request ends. Upstream:
   [Strata#212](https://github.com/Niko1221/Strata/issues/212). **Fixed in v0.1.28** (`4d25c61`): with a key set,
   `/status` answers 401 without it, and the tail is dropped when the request ends (mock tier; confirmed on the real
   host with v0.1.30, G13).
4. **An empty API key disables authentication, and keys are compared with `==`.** The "no API key" warning is
   printed only for non-loopback hosts. The integration refuses to start without a key of at least 32
   characters. Upstream: [Strata#213](https://github.com/Niko1221/Strata/issues/213). **Fixed in v0.1.28**
   (`4d25c61`): keys are compared with `hmac.compare_digest`, and an explicitly empty key (`--api-key ""` or an
   empty `STRATA_API_KEY`) stops the server; on the mock tier an empty `STRATA_API_KEY` exited with code 2. An
   absent key still means no authentication, so the integration still refuses to start without a key of at least
   32 characters.
5. Stock `setup.py` resolves the engine from `releases/latest`, the model and MTP tensors from `main`, and
   unpinned PyPI packages, and it writes to `%APPDATA%\Strata`. The integration feeds it pinned, verified local
   inputs instead. Upstream: [Strata#214](https://github.com/Niko1221/Strata/issues/214). **The fetches are fixed
   in v0.1.31** by the maintainer's `ba5c387`: a checkout installs the engine release of its own version
   (`releases/latest` when that release cannot be reached), every Hugging Face file comes from a pinned commit (the
   same Coder and MTP revisions this integration pins), and the Python packages come from a pinned
   `requirements.txt`. Our [Strata#324](https://github.com/Niko1221/Strata/pull/324) proposed the same three fixes
   six hours after `ba5c387` was committed; v0.1.31 superseded them. #324's fourth change went into **v0.1.32** as
   the maintainer's `09c05e7` ("From PR #324"): an engine archive that setup refuses (too old, or without code for
   the GPU) is deleted with its `.done` mark. That fixes our follow-up
   [Strata#397](https://github.com/Niko1221/Strata/issues/397): v0.1.31 kept the refused archive, so every later run
   reused it and "run this again in a few minutes" never updated the engine. `09c05e7` reached `main` only with
   v0.1.32, after #397 and our fix [Strata#399](https://github.com/Niko1221/Strata/pull/399) were filed; the
   maintainer closed #397 as fixed and #399 as covered. #399's two tests fail on v0.1.31 and pass on v0.1.32 and
   v0.1.33. Not taken from #399: an archive that failed to unpack kept its `.done` mark in v0.1.33 (v0.1.34 by
   source reading), so later runs failed on the same file even after a good archive was published. **Fixed in
   v0.1.40** by the maintainer's `645cbb6`: `BadZipFile` drops the archive and its `.done` mark before re-raising.
   On 2026-10-06 the maintainer closed our [Strata#424](https://github.com/Niko1221/Strata/pull/424) as fixed.
   Per-user settings still go to `%APPDATA%\Strata`. The integration keeps passing local verified inputs and
   redirecting APPDATA; its Python lock for v0.1.31 is resolved from that `requirements.txt` (unchanged in v0.1.34).
6. **Every unexpected engine exit is logged as a probable out-of-memory event**, including the stale-cancel crash
   in item 1 and deliberate kills. None of the 5 exits observed here was memory-related. Upstream:
   [Strata#215](https://github.com/Niko1221/Strata/issues/215). **Fixed in v0.1.28** (`4d25c61`): when the engine
   exits by itself, the server quotes its exit code and last log line; the out-of-memory
   hint remains for other exits (source reading; on the real host with v0.1.30 the cut turn after a mid-generation
   engine kill read "the engine stopped unexpectedly (exit code 1); the next request restarts it", G15).

## OMP

Re-verified against OMP `main` (`2b023d1`, 2026-09-30) and, where a reproducer exists, against the stock 18.4.6
binary pinned by the second candidate, the stock 18.4.8 binary of the third tuple (2026-10-01; 18.4.7 and 18.4.8
changed only the macOS natives and the TUI) and the stock 18.4.10 binary of the fourth tuple (2026-10-02); each item
notes its status. Our pull requests are linked per item: #13866 and #13867 were merged on 2026-09-30 and released in
18.4.5; #13864 was merged on 2026-10-01 and released in 18.4.9; #13868 was merged on 2026-10-01 and released in
18.4.10 (2026-10-02). #14734, #14735 and #14737 were merged on 2026-10-07, after 18.8.0 was cut, so no release
contains them yet.

1. **Executes tool calls whose arguments are syntactically truncated.** At finalization OMP parses the argument
   string with its lenient streaming parser, which closes unterminated JSON, and runs the call: a partial file
   write happens and the run exits 0. Reproducer:
   `tests/mock/test_g04_faults.py::test_truncated_arguments_must_not_execute_side_effect`. A `length` cut is handled
   correctly (`::test_finalized_partial_json_with_length`). `::test_finalized_partial_json_with_stop` is the composed
   case before Strata item 2's fix: the server closes the JSON itself, so OMP receives valid JSON and cannot tell.
   Since Strata v0.1.31 the server leaves the JSON open and ends with `stop`, and OMP 18.4.8 still runs the call
   (`tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body`: the truncated write happens,
   exit 0, stop reasons `toolUse`, `stop`). Present in the 18.4.0-18.4.9 binaries. **Fixed in 18.4.10** by
   can1357/oh-my-pi#13868: with the 18.4.10 binary both reproducers pass (no write; the call gets the parse error
   and the run continues), so G04 no longer fails on the fourth tuple. `::test_finalized_partial_json_with_stop`
   stays a client limit no OMP release can fix: valid JSON is valid, so it is skipped when the pinned Strata leaves
   cut calls unterminated (v0.1.31+).
2. **Contacts the internet at startup.** The background model-registry refresh (`refreshInBackground`) fetches the
   public model catalog from `catalog.stencil.so` when its cache is cold or stale, and implicit local providers probe
   127.0.0.1:11434, :8080 and :1234; no startup setting disables either. Observed with ETW in G13 (18.4.0); with
   18.4.6 and the guard, the loopback probes are still visible and no non-loopback endpoint was reached. Workaround
   here: proxy variables pointing at a closed loopback port. Upstream, can1357/oh-my-pi#10934 asks for a catalog
   opt-out.
3. **Sends `Bearer STRATA_API_KEY` literally when a models.yml `apiKey` names an unset variable**, instead of
   failing. This is OMP's documented contract (an `apiKey` is tried as an environment variable name, else sent as the
   literal token), which is why `launch-omp` refuses a missing key. Reproducer:
   `tests/mock/test_g02_isolation.py::test_raw_stock_missing_key_dispatches_literal_and_fails_401`.
   can1357/oh-my-pi#13866 added a documentation warning (merged); the behaviour is unchanged in 18.4.6.
4. **Retries on `openai-completions` cannot be turned off.** An HTTP 500 produced 12 identical requests (6
   transport attempts × 2 provider attempts) with `retry.enabled: false`. The transport's `DEFAULT_MAX_ATTEMPTS`
   (`packages/ai/src/utils/openai-http.ts`) reads no retry setting, so `retry.maxRetries` cannot reach it either.
   Reproducer: `test_g04_faults.py::test_http_500`. Still present on `main` and in 18.4.6 (12 requests again);
   related: can1357/oh-my-pi#13255.
5. **The fitted `max_tokens` can overshoot a strict server by a few tokens.** The fit is
   `agent/src/output-budget.ts` `fitOutputTokensToContextWindow`. Near the window, prompt 105,522 + fitted cap
   25,563 exceeded Strata's 131,064 (131,072 − 8) by 21 tokens, and the closing turn failed with HTTP 400 (G17
   attempt 3). Fixed upstream by can1357/oh-my-pi#13499 (a 64-token headway, in 18.4.4). The integration keeps
   declaring the window 1,024 tokens below the engine's for both candidates; with 18.4.6 the largest near-limit
   prompt + cap seen was 129,997 (G17), inside the declared window without relying on the headway.
6. **Strata's overflow message is not classified as a context overflow.** `ai/src/error/flags.ts` has no pattern
   for "prompt (N tokens) + max tokens (M) exceeds the context", so no compaction recovery is attempted. This is
   minor, because item 5's fit usually prevents the overflow. **Fixed in 18.4.9** by can1357/oh-my-pi#13864
   (`edb740c`; source reading); not exercised here, because every profile pins 18.4.8 or older.
7. **Unknown `models.yml` compat keys are accepted silently.** A misspelled key is kept without an error. The
   integration guards its emitted keys with a test. **Fixed on `main`** by can1357/oh-my-pi#14737 (`3205ec9`,
   merged 2026-10-07): an unknown key in a provider, model or `modelOverrides` `compat` block now produces a
   non-fatal warning. No release contains it yet.
8. `--thinking off` still sends `reasoning_effort: low` with this dialect; OMP documents this as requesting the
   lowest effort on generic effort endpoints; can1357/oh-my-pi#13867 made that clearer (merged). Unchanged in 18.4.6
   (off/low/medium/high/xhigh are sent as low/low/medium/high/high). `--no-tools` disables the built-in tools, so it
   is not a way to limit egress.
9. **Services an agent starts stop 3 s after `omp --print` exits.** The service broker stops non-detached services
   once its idle grace (`OMP_DAEMON_IDLE_GRACE_MS`, default 3,000 ms) runs out after the last client disconnects, so a
   benchmark that checks a server after the agent exits finds nothing (Terminal-Bench `hf-model-inference` and
   `kv-store-grpc` on 18.5.0). Upstream's metaharness set nothing to prevent it. Scripted check on 18.5.0 and 18.7.0:
   a bash-tool service is gone 8 s after exit, and still listening with a 120,000 ms grace. **Fixed in upstream's
   metaharness** by can1357/oh-my-pi#14734 (`dc97a4a`, merged 2026-10-07): `omp_local.py` now runs omp with
   `OMP_DAEMON_IDLE_GRACE_MS` set to 24 h, so the services stay up until the container is torn down. The broker's
   3 s default is unchanged.
10. **18.5.0 drops the retry for a reasoning-only stop once a run has restarted.** OMP retries a stop whose only
    content is reasoning, but in 18.5.0 such a stop after an earlier continuation or retry in the same run ends it
    with `agent_end.isTerminal: false` and exit 0. Seen in 3 Terminal-Bench runs on Strata v0.1.39; a scripted server
    reproduces it. **Fixed in 18.5.1.**
11. **A compiled binary extracts its ~175 MB native addon into each `HOME`.** The only redirect, `XDG_DATA_HOME`, also
    moves sessions and plugins, so isolated per-attempt homes kept one copy each; the integration deletes it after
    each attempt (`omp_strata.ompcfg.drop_native_cache`). **Fixed on `main`** by can1357/oh-my-pi#14735 (`8f905a5`,
    merged 2026-10-07): `PI_NATIVES_DIR` moves only the addon. No release contains it yet, so the integration
    keeps deleting the copy.
12. **Speculative compaction competes with the agent's own turn on a one-request provider.** In the band below its
    compaction threshold (12.5 % of the threshold, 8,192 to 32,000 tokens), OMP sends the session's model a
    background summary request. With `providers.maxInFlightRequests: 1`, which this integration sets because Strata
    serves one sequence, the agent's next turn waits behind that request, and the summary replaces the engine's live
    prefix. On the RTX PRO 6000 (G17, 18.8.0) the turn waited 17 s and then re-read all 105,748 of its tokens (Strata
    reported none reused; 15.4 s); the summary was never applied. Reproducer: `tests/mock/test_speculative_compaction.py`.
    The extra request went out with 18.4.10, 18.5.0 and 18.8.0; with 18.7.0 the next turn won the race. A scripted
    check without that race (2026-10-07, release binaries) shows it on 18.8.0 and 18.8.2 alike: the summary takes the
    only slot at the turn boundary and the next turn waits for all of it. Workaround here: `compaction.asyncEnabled:
    false` (OMP still compacts at the threshold). Not reported upstream yet; a fix could skip speculation on a provider
    limited to one in-flight request.

Re-checked on `main` `7ac4b18` (2026-10-07): items 2, 4 and 7 are still present; can1357/oh-my-pi#10934 and #13255
remain open. Item 7 was fixed on `main` later that day by #14737.
