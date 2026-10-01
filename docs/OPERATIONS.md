# Operations

All commands take `--profile profiles\<profile_id>.json --root <root>`; the current candidate is
`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`, and each candidate has its own root (one runtime per
root). The examples below leave those two arguments out. There is no daemon: `start` launches a detached wrapper
(`serve`), and the files under `<root>` are the whole state.

## Layout of the integration root

| Path | Contents |
|---|---|
| `downloads\` | Pinned OMP, Strata and llama.cpp archives and the locked wheels, each verified by size and SHA-256 |
| `models\` | The two pinned GGUF shards (58.4 GB) |
| `runtime\strata\` | The pinned stock Strata source (v0.1.30 for the current candidate), its generated config and its hash-locked `.venv` |
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
| `start` | Refuses when owned processes already run, when anything else holds the port, when the GPU has 1,500 MiB or more used or any compute process (or any graphics client, unless the profile declares the GPU display-attached), or when less RAM is available than the profile's `min_available_ram_gib_at_start` (34 GiB for the RTX 5090 and RTX 3090 profiles, 16 GiB for the low-RAM RTX 4090 profile). Waits up to 900 s; readiness took about 15 s on the RTX 5090 and RTX 4090 hosts and 17-33 s on the RTX 3090 host. |
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
- **Stale cancel after a queued client disconnects** (upstream defect Strata#183, reproduced by `g14q`; present in
  the first candidate's v0.1.27, fixed in v0.1.28 and confirmed fixed on the current candidate's v0.1.30). If a
  client disconnects while its request is still queued behind
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
settings) means a new profile id, a new integration root and qualification of the affected gates. It is never an
in-place edit of a qualified profile or root: the second candidate was installed next to the first, and switching
between them is `stop` in one root and `start` in the other (never both at once; they share the port and the GPU).
`scripts\verify_release.py --manifest releases\<profile>\manifest.json` checks that the profile, ledger and
receipts still bind together.

### Requalifying a new tuple

The sequence used for the second candidate (about 45 minutes of exclusive GPU time, run from a client machine over
SSH with `stdin` closed, so that OMP's print mode never waits on a pipe):

1. **Profile.** Copy the current profile to a new id, change the pins (release asset sizes and SHA-256 digests from
   the GitHub release API, tag commits from `git/ref/tags`), and read the new stock `setup.py` for `PY_PACKAGES`,
   `CUDA_WHEELS`, `LLAMA_CPP_COMMIT`, new engine flags and new config keys; extend `forbidden_engine_flags` and
   `verify_generated()` for anything that would change serving. `validate` the profile.
2. **Host-free first.** `dev-env --profile <new> --root <new dev root> -- python3 -m unittest discover -s tests -t .`
   fetches the new client binary and Strata checkout and runs the suite against them (G01-G05); create the draft
   `releases/<id>/` (ledger from `docs/handoff/2026-09-30/acceptance_matrix.json`, every gate `not_run`) and commit,
   so that receipts can name the implementation commit.
3. **Fetch while the other runtime still owns the GPU.** Sync the committed tree to `<new root>\tooling`, then
   `fetch` into the new root (the previous root's verified shards can be copied in first; `fetch` re-hashes them).
4. **Window.** Release the GPU with the owner's tooling; `install`, `keygen`, `start`.
5. **Gates in order:** `realhost_gates.py g10 --deep`, `tracer.py --runs 3`, `g12 --runs <tracer ids>`, `g13`,
   `g14`, `g14q`, `g15`, `g16`, `g17`, `g18`, `g18l`, `g19`, `g20`; then `evaluate.py --pilot` and the scored batch
   with `--between-phases "<python> <tooling>\scripts\omp_strata.py restart ..."`; the quickstart `launch-omp`
   example; `g21` last (it reads every server log); `stop`; restore the other runtime.
   Run this sequence unattended **on the GPU host** with `python scripts/requalify.py --profile <profile>
   --root <root>` (including install/keygen/start). Launch it detached with output redirected to a file; its
   first line names the atomically updated summary and adjacent per-step logs. `--dry-run` prints the plan,
   `--from <step>` or `--only <step,...>` selects steps, and `--keep-running` skips the otherwise unconditional
   final stop. The pilot uses one attempt and the scored batch uses the evaluator's required three.
6. **Publish.** Pull each `<root>\evidence\<run_id>\result.json`, scrub it (root path, user and host names),
   write it under `releases/<id>/evidence/`, and append a receipt per gate with `omp_strata.receipts`; set the
   manifest's install identity from `state\install-record.json`; `verify_release.py` and the hygiene scan must
   pass before the commit.

## Sharing the GPU

The integration assumes it owns the GPU while it runs. `start` refuses a busy GPU. It never stops another
runtime; whoever operates the host must release the GPU first and restore the other runtime afterwards.

A GPU that also drives a display lists the desktop's processes (compositor, logon screen) as WDDM graphics
clients (`C+G`). Profiles for such hosts set `host.display_attached: true`: `start`, `doctor` and G10 then tolerate
graphics clients, record how many there are, and still refuse any compute process or 1,500 MiB of foreign use. An
interactive desktop session can hold close to a gigabyte of VRAM in its applications; signing it out before a run
leaves the logon screen's ~180 MiB.
