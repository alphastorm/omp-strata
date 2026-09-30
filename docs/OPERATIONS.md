# Operations

All commands take `--profile profiles\win11-rtx5090-coder-iq1m-131k.json --root <root>`. The examples below leave
those two arguments out. There is no daemon: `start` launches a detached wrapper (`serve`), and the files under
`<root>` are the whole state.

## Layout of the integration root

| Path | Contents |
|---|---|
| `downloads\` | Pinned OMP, Strata and llama.cpp archives and the locked wheels, each verified by size and SHA-256 |
| `models\` | The two pinned GGUF shards (58.4 GB) |
| `runtime\strata\` | Stock Strata v0.1.27 source, its generated config and its hash-locked `.venv` |
| `data\`, `appdata\` | Stock setup's generated data and its redirected APPDATA (never `%APPDATA%\Strata`) |
| `state\install-record.json` | Install record: `runtime_identity_sha256`, pip freeze digest, profile fingerprint |
| `state\run.json` | Owned process identities (PID, creation time, executable) and readiness facts |
| `state\strata-api-key` | The private API key (user-only ACL) |
| `logs\server-*.log`, `logs\serve-*.log` | Stock server output and the wrapper's own log |
| `omp\home\` | The isolated OMP HOME; sessions live under `.omp\profiles\omp-strata\agent\sessions` |

## Lifecycle

| Command | Behavior |
|---|---|
| `status` | One of `not_installed`, `stopped`, `starting`, `healthy`, `degraded`, `mismatched`, `failed`. `healthy` requires authenticated identity checks and an engine process under the server. |
| `start` | Refuses when owned processes already run, when anything else holds the port, when the GPU has more than 1,500 MiB used or any compute process, or when less than 34 GiB RAM is available. Waits up to 900 s; about 15 s on the tested host. |
| `stop` | Stops the recorded wrapper and server and everything currently beneath them, deepest first. Only processes whose PID, creation time and executable still match are touched. Waits for the port to be released. Repeating it is a no-op. |
| `restart` | `stop`, then `start`. |

The process tree on Windows is: `serve` wrapper (`python.exe`) → venv `python.exe` (a redirector) → base
`python.exe` running stock `serve/server.py` → `strata.exe` (the engine, which owns the GPU). A PID alone never
identifies an owned process: PIDs are reused.

## Failures and recovery

- **Engine process died** (crash, OOM, kill). Stock Strata answers the request in flight with an error and starts
  the engine again on the *next* request. That takes about 15 s (the experts are reloaded), and the whole prompt
  is prefilled again. Until that request, `status` reports `degraded` ("no engine process"), and `launch-omp`
  refuses to start. Recover with `restart`, which also clears the stale-cancel state below.
- **Stale cancel after a queued client disconnects** (upstream defect Strata#183, reproduced by `g14q`; fixed in
  Strata v0.1.28, present in the pinned v0.1.27). If a client disconnects while its request is still queued behind
  another one, the next request with a multi-chunk prompt (thousands of tokens) fails with HTTP 400 `cancelled`.
  The engine then exits, and the request after that gets HTTP 503 before the engine restarts. Short prompts are
  not affected. With OMP this appears as one failed turn, possibly followed by an engine restart. Run `restart`
  after cancelling queued work.
- **HTTP 400 "requests are never truncated".** The prompt plus the requested output does not fit in the 131,072
  context. OMP sizes the output cap to the room it estimates is left. The integration declares the window 1,024
  tokens smaller than the engine's so that estimate errors do not reach the server. A single prompt larger than
  about 130K tokens cannot be sent at all; OMP compacts long sessions before that point.
- **HTTP 401.** The key is missing or wrong. `launch-omp` reads the key from `state\strata-api-key`. Clients of
  your own must send it as `Authorization: Bearer <key>`.
- **Mismatched.** The install record or running server belongs to another profile or runtime identity. Run
  `stop`, then `install` again.

## Logs and evidence

- Server output: `logs\server-<utc>.log`. It contains the stock progress lines (`done: N tokens ... (finish,
  cancel=...)`, engine restarts). Tool and qualification logs are next to it.
- The qualification probes (`scripts\realhost_gates.py`, `scripts\tracer.py`) and the evaluation keep their raw
  material under `<root>\evidence\<run_id>\` and `<root>\eval\`. Only derived facts are published, under
  `releases\<profile>\`.

## Upgrades

The profile pins every component. Changing any component (OMP, Strata, the model, context, KV or speculation
settings) means a new profile id and qualification of the affected gates. It is never an in-place edit of a
qualified profile. `scripts\verify_release.py --manifest releases\<profile>\manifest.json` checks that the
profile, ledger and receipts still bind together.

## Sharing the GPU

The integration assumes it owns the GPU while it runs. `start` refuses a busy GPU. It never stops another
runtime; whoever operates the host must release the GPU first and restore the other runtime afterwards.
