# omp-strata — decisions for agents

Authoritative scope: `docs/handoff/2026-09-30/HANDOFF.md` (execution packet, verified by its `SHA256SUMS`).
This file records the decisions that later work must not undo. Keep it short; evidence lives in
`docs/BASELINE.md`, `releases/` and `docs/MEASUREMENTS.md`.

## Shape

- Thin sibling integration: **stock** OMP (can1357/oh-my-pi; v18.4.10 in the current qualified tuple, v18.4.0 in the
  first) talks directly to **stock** Strata (Niko1221/Strata; v0.1.34 current, v0.1.27 first) over OpenAI Chat
  Completions (`api: openai-completions`). No OMP fork, no request proxy, no Responses shim, no durable
  engine-state subsystem, no daemon, no plugin/framework layer.
- OMP owns transcripts, tools, compaction and resume. Strata owns inference, templating and its live cache.
  After any restart OMP's transcript is authoritative and cold re-prefill is expected; nothing claims
  restored GPU state (`durable_engine_state` is false in v0.1 regardless of evidence).
- Python standard library only (runtime and `unittest` tests). Thin PowerShell only where Windows process
  behavior requires it (`scripts/windows/`).
- One current candidate at a time: `profiles/<profile_id>.json` is the single nonsecret source of truth (host
  expectations, stock setup choices, every pin, OMP route). A changed component or setting is a new
  profile id with its own integration root and release ledger; it invalidates nothing in a predecessor's ledger
  and inherits nothing from it. The predecessor's profile, root and evidence stay as the rollback installation.
- A client on another machine reaches a host's loopback server only through an SSH local forward that the
  foreground `launch-omp` owns and tears down (no daemon, no proxy). A client route (`routes/<id>.json`) pins
  server profile ids and fingerprints and has its own ledger requiring G23; private bindings (SSH alias, remote
  root) and client keys stay in the client root, never in the repository. A fleet is one forward and one
  `strata-<label>` provider per host; stock `task.agentModelOverrides` sends the unmodified stock task/scout agents
  to a worker (`modelRoles.task` alone did not route subagents); never replace stock agent definitions.

## Non-negotiable boundaries

- Never modify the user's default OMP install/config (`~/.omp`), omp-ninfer, NInfer runtimes or their
  checkpoint stores. Stock OMP runs with an isolated HOME/USERPROFILE under the integration root plus the
  named profile `omp-strata`; provider id `strata-local`.
- Everything this tool creates lives under one integration root (default `%USERPROFILE%\omp-strata` or
  `~/omp-strata`). Never write `%APPDATA%\Strata`; stock `setup.py` runs with APPDATA redirected into the
  root and only with local, pre-verified inputs (`--prebuilt <folder>`, `--gguf-dir`, pinned MTP revision).
- Never run `START-HERE.bat`, `setup.sh`, `UPDATE.bat`, `update.sh` or an unguarded `setup.py` start: they fetch
  `releases/latest`, HF `main`, or `git pull`, and may update an installed engine in place.
- Strata binds 127.0.0.1 only, always with a nonblank `STRATA_API_KEY` (an empty key disables its auth).
  The key lives in a user-only file under `<root>/state/`, never in argv, committed config, logs or receipts.
- Stock OMP (18.4.0 and 18.4.6) does **not** refuse a missing `apiKey` env var: it sends the variable *name* as the
  bearer token. `launch-omp` refuses a missing/blank key before OMP starts; the server rejects the literal name.
- Text-only profile: vision off, Strata-side MCP never configured, experimental speed projection off, low-RAM
  mode explicit. Calibration is off unless a profile pins what stock `tools/calibrate.py` kept on the measured
  install (`strata.calibration`, a new profile id; install applies it with stock `calibrate.apply`, never
  measures). Tuning flags are profile changes, never silent fixes.
- No cloud fallback: `retry.enabled/modelFallback` false, every chat role pinned to an omp-strata Strata provider
  (`strata-local`, or a `strata-<label>` provider reached through an authenticated loopback-to-loopback SSH
  tunnel), never a non-Strata provider; external discovery disabled, ambient provider credentials scrubbed from
  the OMP environment.
- The G25 comparison harness (`scripts/compare_g25.py`) is a separate, comparison-only tool: its NInfer arm
  renders NInfer's documented local Responses provider (native 3090/4090 lanes, or the 5090's Docker lane) in its
  own isolated HOME during an exclusive window. It never changes `launch-omp`'s Strata-only routing, never writes
  NInfer state, and `engine_only_comparison` stays false (engine, model, quantization and protocol all differ).
  Its operator driver (`scripts/g25_host.py`) starts and stops engines only through each installation's supported
  controller (or `docker start/stop` of the installed 5090 container) inside an exclusive window.
- The task-set evaluator (`scripts/eval_taskset.py`) is comparison-only on the same terms: stock OMP runs on a
  client in a sandbox (no writes in the home directory outside its attempt, loopback-only network) and reaches
  each engine through an owned SSH loopback tunnel; engines switch only through their supported controllers. Task
  sets, arms files and attempts derived from private repositories stay outside this repository; only aggregate
  counts are published.
- Mocks never satisfy a real-host gate. `pass` needs evidence; `blocked` is not a pass. Keep failures.

## Public repository hygiene

- Public text never contains hostnames, machine names, user names in paths, private IPs, tailnet names,
  GPU UUIDs, serials, keys, tokens, transcripts or raw logs. Use neutral labels (`host: rtx5090-win-a`).
- `scripts/check_public_hygiene.py` must pass before every commit (`.githooks/pre-commit`) and in CI.
  Private terms go in an untracked denylist (`~/.config/omp-strata/hygiene-denylist.txt`).
- Raw evidence stays under the integration root on the host; only scrubbed exports enter `releases/`.
- Commits follow Conventional Commits. No force-push, tag, release or publication without the owner.
