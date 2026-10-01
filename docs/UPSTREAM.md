# Upstream findings

These defects and surprises in the stock components were observed while qualifying OMP 18.4.0 (`401778d`)
against Strata v0.1.27 (`a790805`). Each has a reproducer in this repository. The Strata items are reported
upstream as linked below, after re-verification at the same Strata commit. The OMP items go upstream as pull
requests rather than issues, as upstream `CONTRIBUTING.md` asks for work the reporter will submit.
The integration works around them only where a supported setting exists.

Upstream status was re-checked on 2026-09-30 against Strata v0.1.28 (`bbaaabb`) and on 2026-10-01 against
**v0.1.30 (`30ec18e`), now pinned by the second candidate** (`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`,
which also moves OMP to 18.4.6): v0.1.28 fixed items 1, 3, 4 and 6 and the second candidate's real-host gates
confirm them; item 2 is not fixed and item 5 is still open. The first candidate's profile keeps v0.1.27 with every
item present. "Mock tier" below means the stock frontend with its MockEngine (no GPU).

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
   `tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body` (the stock frontend with
   its MockEngine). A cut on `finish_reason: length` is correctly reported. Upstream: the second trigger of
   [Strata#210](https://github.com/Niko1221/Strata/issues/210); our #211 was closed as its duplicate, noting that
   the finish reason must change as well. **Not fixed in v0.1.28**, although #210 was closed: v0.1.28 fixed its
   first trigger (`</parameter>` or `</tool_call>` inside an argument now stays part of the value), but
   `finish()` still closes an unfinished call. On the mock tier, the reproducer's partial call still streams the
   closing `"}` and ends with `finish_reason: tool_calls`, streamed and non-streamed, as on v0.1.27. #211 was
   reopened with that repro, and [Strata#231](https://github.com/Niko1221/Strata/pull/231) (open) proposes a fix:
   an unfinished call's JSON stays open and the finish reason is not `tool_calls` / `tool_use`.
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
   inputs instead. Upstream: [Strata#214](https://github.com/Niko1221/Strata/issues/214), still open in v0.1.30
   (`30ec18e`). [Strata#324](https://github.com/Niko1221/Strata/pull/324) (open) proposes the fix for the three
   fetches: the engine from the release matching the checkout (`releases/latest` only after a 404), every Hugging
   Face URL pinned to a commit, and the Python packages from a pinned `requirements.txt`.
6. **Every unexpected engine exit is logged as a probable out-of-memory event**, including the stale-cancel crash
   in item 1 and deliberate kills. None of the 5 exits observed here was memory-related. Upstream:
   [Strata#215](https://github.com/Niko1221/Strata/issues/215). **Fixed in v0.1.28** (`4d25c61`): when the engine
   exits by itself, the server quotes its exit code and last log line; the out-of-memory
   hint remains for other exits (source reading; on the real host with v0.1.30 the cut turn after a mid-generation
   engine kill read "the engine stopped unexpectedly (exit code 1); the next request restarts it", G15).

## OMP

Re-verified against OMP `main` (`2b023d1`, 2026-09-30) and, where a reproducer exists, against the stock 18.4.6
binary pinned by the second candidate (2026-10-01); each item notes its status. Our pull requests are linked per
item: #13866 and #13867 were merged on 2026-09-30, #13864 and #13868 were still open on 2026-10-01.

1. **Executes tool calls whose arguments are syntactically truncated.** At finalization OMP parses the argument
   string with its lenient streaming parser, which closes unterminated JSON, and runs the call: a partial file
   write happens and the run exits 0. Reproducer:
   `tests/mock/test_g04_faults.py::test_truncated_arguments_must_not_execute_side_effect`. A `length` cut is handled
   correctly (`::test_finalized_partial_json_with_length`). `::test_finalized_partial_json_with_stop` is the composed
   case from Strata item 2: the server closes the JSON itself, so OMP receives valid JSON and cannot tell; that half
   needs the Strata fix. Still present on `main` and in the 18.4.6 binary (the reproducer still fails, G04 of the
   second candidate); fix proposed in can1357/oh-my-pi#13868.
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
   minor, because item 5's fit usually prevents the overflow. Still present on `main`; fix proposed in
   can1357/oh-my-pi#13864.
7. **Unknown `models.yml` compat keys are accepted silently.** A misspelled key is kept without an error. The
   integration guards its emitted keys with a test. Still present on `main`.
8. `--thinking off` still sends `reasoning_effort: low` with this dialect; OMP documents this as requesting the
   lowest effort on generic effort endpoints; can1357/oh-my-pi#13867 made that clearer (merged). Unchanged in 18.4.6
   (off/low/medium/high/xhigh are sent as low/low/medium/high/high). `--no-tools` disables the built-in tools, so it
   is not a way to limit egress.
