# Upstream findings

These defects and surprises in the stock components were observed while qualifying OMP 18.4.0 (`401778d`)
against Strata v0.1.27 (`a790805`). Each has a reproducer in this repository. None has been filed upstream yet.
The integration works around them only where a supported setting exists.

## Strata

1. **A queued client's disconnect poisons the next long request and crashes the engine.** Reproduced 2/2 by
   `scripts/realhost_gates.py g14q`; the control case is clean.
   - Steps: request A is generating and request B is queued behind it; B's client disconnects. Then the next
     request whose prompt needs more than one prefill window (about 8K tokens here) fails with HTTP 400
     `cancelled`, the engine exits with code 1, and the request after that gets HTTP 503 before the lazy restart.
   - Short prompts in between are served normally.
   - Relevant code: the engine clears `stop_req` only at the start of a request (`src/program/generate.cpp:3561`).
     The windowed prefill checks it (`:3855`), and `serve/server.py` sends `STOP` from the generator's `finally`.
   - Workaround here: `omp_strata.py restart`.
2. **Tool calls cut off mid-arguments are finalized as complete.** When the model ends its turn inside a tool
   call, `OutputParser.finish()` closes the partial JSON and the response reports `finish_reason: tool_calls`
   (or `stop`). Clients then execute truncated arguments; see OMP item 1. Reproducer:
   `tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body` (the stock frontend with
   its MockEngine). A cut on `finish_reason: length` is correctly reported.
3. **`/status` is unauthenticated and includes a tail of the text being generated.** With an API key set, any
   local process can still read the end of the current answer.
4. **An empty API key disables authentication without a warning, and keys are compared with `==`.** The
   integration refuses to start without a key of at least 32 characters.
5. Stock `setup.py` resolves the engine from `releases/latest`, the model and MTP tensors from `main`, and
   unpinned PyPI packages, and it writes to `%APPDATA%\Strata`. The integration feeds it pinned, verified local
   inputs instead.
6. **Every unexpected engine exit is logged as a probable out-of-memory event**, including the stale-cancel crash
   in item 1 and deliberate kills. None of the 5 exits observed here was memory-related.

## OMP

1. **Executes tool calls whose arguments were truncated.** For `finish_reason: tool_calls`, and for `stop`
   (which OMP promotes to toolUse), OMP repairs and runs the partial call: a partial file write happens and the
   run exits 0. Reproducers: `tests/mock/test_g04_faults.py::test_truncated_arguments_must_not_execute_side_effect`
   and `::test_finalized_partial_json_with_stop`.
2. **Contacts the internet at every start.** The background model-registry refresh
   (`coding-agent/src/main.ts` `refreshInBackground`) fetches the public model catalog from `catalog.stencil.so`,
   and no setting disables it. It also probes 127.0.0.1:11434, :8080 and :1234. Observed with ETW in G13.
   Workaround here: proxy variables pointing at a closed loopback port.
3. **Sends `Bearer STRATA_API_KEY` literally when a models.yml `apiKey` names an unset variable**, instead of
   failing. Reproducer: `tests/mock/test_g02_isolation.py::test_raw_stock_missing_key_dispatches_literal_and_fails_401`.
4. **Retries on `openai-completions` cannot be turned off.** An HTTP 500 produced 12 identical requests (6
   transport attempts × 2 provider attempts) with `retry.enabled: false`, and `maxRetries: 0` did not help.
   Source: `packages/ai/src/utils/openai-http.ts` `DEFAULT_MAX_ATTEMPTS`. Reproducer: `test_g04_faults.py::test_http_500`.
5. **The fitted `max_tokens` can overshoot a strict server by a few tokens.** The fit is
   `agent/src/output-budget.ts` `fitOutputTokensToContextWindow`. Near the window, prompt 105,522 + fitted cap
   25,563 exceeded Strata's 131,064 (131,072 − 8) by 21 tokens, and the closing turn failed with HTTP 400 (G17
   attempt 3). Workaround here: declare the window 1,024 tokens below the engine's.
6. **Strata's overflow message is not classified as a context overflow.** `ai/src/error/flags.ts` has no pattern
   for "prompt (N tokens) + max tokens (M) exceeds the context", so no compaction recovery is attempted. This is
   minor, because item 5's fit usually prevents the overflow.
7. **Unknown `models.yml` compat keys are accepted silently.** A misspelled key is ignored without an error. The
   integration guards its emitted keys with a test.
8. `--thinking off` still sends `reasoning_effort: low` with this dialect. `--no-tools` disables the built-in
   tools, so it is not a way to limit egress.
