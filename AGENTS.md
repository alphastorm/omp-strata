# omp-strata — decisions for agents

Authoritative scope: `docs/handoff/2026-09-30/HANDOFF.md` (execution packet, verified by its `SHA256SUMS`).
This file records the decisions that later work must not undo. Keep it short; evidence lives in
`docs/BASELINE.md`, `releases/` and `docs/MEASUREMENTS.md`.

## Shape

- Thin sibling integration: **stock** OMP (can1357/oh-my-pi; v18.4.6 in the current candidate, v18.4.0 in the
  first) talks directly to **stock** Strata (Niko1221/Strata; v0.1.30 current, v0.1.27 first) over OpenAI Chat
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

## Non-negotiable boundaries

- Never modify the user's default OMP install/config (`~/.omp`), omp-ninfer, NInfer runtimes or their
  checkpoint stores. Stock OMP runs with an isolated HOME/USERPROFILE under the integration root plus the
  named profile `omp-strata`; provider id `strata-local`.
- Everything this tool creates lives under one integration root (default `%USERPROFILE%\omp-strata` or
  `~/omp-strata`). Never write `%APPDATA%\Strata`; stock `setup.py` runs with APPDATA redirected into the
  root and only with local, pre-verified inputs (`--prebuilt <folder>`, `--gguf-dir`, pinned MTP revision).
- Never run `START-HERE.bat`, `setup.sh` or an unguarded `setup.py` start: they fetch `releases/latest`,
  HF `main`, and may update an installed engine.
- Strata binds 127.0.0.1 only, always with a nonblank `STRATA_API_KEY` (an empty key disables its auth).
  The key lives in a user-only file under `<root>/state/`, never in argv, committed config, logs or receipts.
- Stock OMP (18.4.0 and 18.4.6) does **not** refuse a missing `apiKey` env var: it sends the variable *name* as the
  bearer token. `launch-omp` refuses a missing/blank key before OMP starts; the server rejects the literal name.
- Text-only profile: vision off, Strata-side MCP never configured, experimental speed projection off,
  calibration off, low-RAM mode explicit. Tuning flags are profile changes, never silent fixes.
- No cloud fallback: `retry.enabled/modelFallback` false, every chat role pinned to `strata-local`, external
  discovery disabled, ambient provider credentials scrubbed from the OMP environment.
- Mocks never satisfy a real-host gate. `pass` needs evidence; `blocked` is not a pass. Keep failures.

## Public repository hygiene

- Public text never contains hostnames, machine names, user names in paths, private IPs, tailnet names,
  GPU UUIDs, serials, keys, tokens, transcripts or raw logs. Use neutral labels (`host: rtx5090-win-a`).
- `scripts/check_public_hygiene.py` must pass before every commit (`.githooks/pre-commit`) and in CI.
  Private terms go in an untracked denylist (`~/.config/omp-strata/hygiene-denylist.txt`).
- Raw evidence stays under the integration root on the host; only scrubbed exports enter `releases/`.
- Commits follow Conventional Commits. No force-push, tag, release or publication without the owner.
