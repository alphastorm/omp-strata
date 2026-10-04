# Operations

All commands take `--profile profiles\<profile_id>.json --root <root>`; the current qualified profile is
`win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10`, and each profile has its own root (one runtime per
root). The examples below leave those two arguments out. There is no daemon: `start` launches a detached wrapper
(`serve`), and the files under `<root>` are the whole state.

## Layout of the integration root

| Path | Contents |
|---|---|
| `downloads\` | Pinned OMP, Strata and llama.cpp archives and the locked wheels, each verified by size and SHA-256 |
| `models\` | Pinned GGUF shards under `<variant>-<quantization>` (two for Coder, four for Unsloth UD-Q4_K_XL) |
| `runtime\strata\` | The pinned stock Strata source (v0.1.34 for the current tuple), its generated config and its hash-locked `.venv` |
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
| `start` | Refuses when owned processes already run, when anything else holds the port, when the GPU has 1,500 MiB or more used or any compute process (or any graphics client, unless the profile declares the GPU display-attached), or when less RAM is available than the profile's `min_available_ram_gib_at_start` (34 GiB for the Coder profiles that keep every expert in RAM, 16 GiB for the low-RAM RTX 4090 profile, 52 and 64 GiB for the exploratory IQ3_S profiles). Waits up to 900 s; readiness took about 15 s on the RTX 5090 and RTX 4090 hosts and 17-33 s on the RTX 3090 host. |
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

A host change can have the same effect, because stock setup derives two flags from total RAM: the Coder IQ1_M
gets the low-RAM mode below 33.4 GiB and KV streaming (`--kv-resident 32768`) from 34.8 GiB; IQ3_S streams from
64.8 GiB. `install` refuses a generated flag the profile does not expect, so a RAM upgrade that crosses one of these
thresholds needs the profile written for the new configuration (the RTX 4090 and IQ3_S drafts without `lowram` or
with `kvstream` in their ids), installed into a new root.

### Requalifying a new tuple

The sequence used for the second candidate (about 45 minutes of exclusive GPU time, run from a client machine over
SSH with `stdin` closed, so that OMP's print mode never waits on a pipe):

1. **Report, then draft.** `python3 scripts/upstream_watch.py report --strata-src <local Strata checkout>`
   compares releases with the newest pinned tags across **all** profiles and checks `upstream-watch.json`
   (the issues/PRs in [UPSTREAM.md](UPSTREAM.md)). It reads local tags, never fetches or changes that checkout.
   JSON goes to stdout, a short summary to stderr: exit **0** = complete/no news, **3** = complete/news,
   **4** = incomplete (including failed, malformed or truncated API responses), never "no change".
   `--pinned-strata-tag <tag> --strata-tag <tag>` selects an explicit source comparison. The checklist compares
   setup constants, the requirements blob, generated/optional config keys, classified server routes and new
   `STRATA_*` names. Review any delta before materializing a runtime. A closed-unmerged Strata PR means
   **check the maintainer commit**, not rejection.

   `python3 scripts/upstream_watch.py draft --from <predecessor profile> --strata-tag <tag> --omp-tag <tag>
   --id <new id> --strata-src <local Strata checkout>` resolves live GitHub release asset sizes/digests and
   direct tag commits, plus Hugging Face shard sizes/LFS digests at stock setup's revisions. Optional
   `--family`, `--model`, `--context`, `--ram-gib` and `--vram-gib` select a variant. RAM/VRAM here are planning
   inputs, not purchased-capacity floors. Every host floor is the maximum of the predecessor's floor
   and stock setup's estimate: a tuple bump never lowers an established operational constraint. The
   draft JSON reports both inputs and the selected floor. The tool evaluates only stock setup's pure choices and inline
   config arithmetic; it never imports/runs setup's main, fetches an installer or writes a lock. Unfamiliar
   planning code, changed dependencies/lock inputs, annotated tags, missing pins and degraded variants are
   refused (exit **2**, success **0**). The reviewed lane is text-only native Windows NVIDIA, no low-RAM
   mode or RoPE extension, with stock KV streaming; other choices need explicit source review.

   **Experimental Unsloth Q4:** `--family unsloth --model UD-Q4_K_XL --context 131072 --ram-gib 127.69
   --vram-gib 24` uses stock v0.1.36's budget planner, not its low-RAM `experts.bin` mode. It selects
   `--kv-resident 32768 --resident-budget-gib 71`. The 97 GiB total-RAM floor preserves that automatic
   budget; the 97 GiB available-at-start floor reserves the 71 GiB budget, 1.799356416 GB streamed KV and
   stock's 24 GiB OS/engine/file-cache headroom. Fresh-install disk is 112 GiB after rounding up the exact
   111,334,654,784 shard bytes plus stock's 8 GB allowance. Floors still take the predecessor maximum, and
   the profile records the stock budget inputs and each floor's derivation. At 64 GiB, stock's initial budget
   is 40 GiB, reduced to **38 GiB** when this 131K int8 context enables KV streaming.

   All four shards are pinned from stock `UNSLOTH_SHARDS`, cross-checked with HF LFS at revision
   `38bb39ee97821de2c9009abb7e93950eec396e66`. Already downloaded shards may be placed directly in
   `<root>\models\unsloth-UD-Q4_K_XL\`; `fetch --only model` verifies their sizes and SHA-256 without
   downloading them again. Guarded `install` passes that directory and the local pinned prebuilt to stock
   setup, which performs its own `iq_pack.py --compat-bf16` step. The resulting
   `strata-unsloth-ud-q4_k_xl.json` uses shard 1 as `--native`, no `--ple-gguf`, and no model-pack
   `experts.bin` (the separate MTP draft pack still has one). A changed budget, foreign model path, low-RAM
   expert flag or new generated server setting fails verification. This is a new, unqualified draft;
   no speed or quality result is inherited from another model.

   Both the new profile and `releases/<id>/{manifest,qualification}.json` are created append-only. Existing
   destinations are never overwritten. The acceptance matrix supplies **24 gates, all `not_run`**, no
   receipts or install identity; no predecessor qualification receipts are copied. GitHub auth is optional (`GH_TOKEN`,
   `GITHUB_TOKEN`, then `gh auth token`); it is never sent to Hugging Face or printed.
2. **Host-free first.** `validate --profile <new>` and
   `python3 scripts/verify_release.py --manifest releases/<id>/manifest.json` must pass; the latter with
   `--require-ready` must fail for a fresh draft. Then run
   `dev-env --profile <new> --root <new dev root> -- python3 -m unittest discover -s tests/mock -t . -v`
   and, under the same dev-env, `python3 -m unittest tests.unit.test_strata_surface tests.unit.test_profile -v`.
   `dev-env` downloads the pinned host client and Strata source and prepares its Python dependencies, never a
   GPU engine/model. Use the lock's Python minor (3.13 for this tuple) to invoke dev-env. Run the host-free
   unit suite once after concurrent edits settle, then commit so later receipts can name the implementation
   commit. Host-free success changes no real-host gate and does not make a draft ready.
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
6. **Publish.** From the client machine, `python3 scripts/pull_run.py --host <ssh host> --root <root> --log
   <requalify log> --dest <empty private directory>` copies the run's summary, install record, step results and
   evaluation files. `python3 scripts/publish_run.py --pulled <that directory> --profile profiles/<id>.json
   --host-label <public label> --root-path <root> --implementation-commit <tooling commit> --dry-run` checks the
   plan without writing; without `--dry-run` it scrubs the results (root path, `--private` terms, the untracked
   denylist), writes them under `releases/<id>/evidence/`, appends a receipt per measured gate (G10-G21, G24, G26),
   updates the ledger and sets the manifest's install identity. Add `--host-had-strata` when the host already had
   another root. Status and publication decisions stay with the operator, and the receipts for G00-G06, G22, G23
   and G25 are written by hand. Pull and publish each rerun the same way; earlier receipts, failures included,
   stay. `verify_release.py` and the hygiene scan must pass before the commit.

### Fifth-tuple draft commands

These commands created the five v0.1.36/18.4.12 drafts. Set `STRATA_SRC` to a read-only local
checkout containing the tags; only metadata APIs and read-only git operations are used. The stock
setup calculations and pin provenance are recorded in [UPSTREAM.md](UPSTREAM.md). The 4090
predecessor is the earlier **non-low-RAM** draft, not an edit of the 32 GB profile.

```sh
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx5090-coder-iq1m-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 47 --vram-gib 32
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx3090-coder-iq1m-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 128 --vram-gib 24
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx4090-coder-iq1m-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 192 --vram-gib 24
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx4090-coder-iq1m-262k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 192 --vram-gib 24 --context 262144
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx4090-q2-0-131k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 192 --vram-gib 24 --family qwen --model Q2_0
```

Each command is intentionally non-repeatable at the same destination. A later settings change
requires a different id; never delete or reset an existing ledger to make the command succeed.

Contexts past the model's trained 262,144 tokens (`--context 393216` or `524288`) draft what stock setup does for
them: yarn rope scaling with the factor context / 262,144 (`--rope-scaling yarn --rope-scale 1.5` or `2`), and KV
streaming whose RAM grows with the context (7.2 GB at 524,288). Strata calls it experimental: a scaled run is a
slightly different model at every position, not only past 262,144. The RTX 3090's 524K Coder draft:

```sh
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx3090-coder-iq1m-262k-strata0.1.36-omp18.4.12.json \
  --strata-tag v0.1.36 --omp-tag v18.4.12 \
  --id win11-rtx3090-coder-iq1m-524k-strata0.1.36-omp18.4.12 \
  --strata-src "$STRATA_SRC" --ram-gib 127.69 --vram-gib 24 --context 524288
```

### Comparing variants on one host

After a RAM upgrade, install each variant (for example the RTX 4090's Coder 131K, Coder 262K and Q2_0 drafts)
from its own profile into its own root, and measure them one at a time on the same otherwise idle host:
`python scripts/requalify.py --profile <profile> --root <root> --only perf` restarts that root's server, runs
`scripts/perf_probe.py` and stops it (`perf_probe.py --profile <profile> --root <root>` alone measures a server
that is already running; `--depths 0,8K,32K,64K,100K --warm-depth 32K --max-tokens 512 --timeout 600` are the
knobs). It writes `<root>\evidence\perf-<id>\result.json` and prints a table: TTFT, server-reported prefill and
decode rates, draft acceptance from `/metrics` (Strata 0.1.35 and later; otherwise `unavailable`) and a
two-request FIFO queue-wait bound. Gaps between streamed events are not token latencies, and the warm repeat is
live prefix reuse, not restart restoration. The probe changes no gate and no ledger. G24's six tasks are an
integration smoke, not a quality comparison: five are solved by every model tried and one by almost none, so use
a task-set evaluation (below) to compare models.

### Comparing models on a private task set

`scripts/eval_taskset.py` runs a private task set (a directory of tasks, each with a prompt, an initial
workspace, hidden expected material, a reference solution and a verifier; its `CONTRACT.md` defines the format)
once per model through the pinned stock OMP on a macOS client. It is comparison-only, like G25: it never changes
`launch-omp` routing, an installation or a ledger, and its results are not gate evidence.

- `check --taskset <dir> --arms <arms.json>` proves every task fair before any model runs: the untouched seed
  fails its verifier and the reference passes, both through the same sandbox the agents get.
- `pull-keys --arms <arms.json>` copies each placement's API key over SSH into a user-only client file.
- `run --taskset <dir> --arms <arms.json> --out <private dir>` gives each host one worker that walks its arms in
  order (`hosts.<host>.order`); an arm placed on several hosts is shared, so a host that finishes early takes over
  the rest of it. Before an arm's first attempt on a host, the worker runs that placement's `activate` command
  (an operator script that stops whatever else serves there and starts the engine through its supported
  controller), then owns an `ssh -L` loopback tunnel to it. Each attempt gets a fresh workspace (APFS clones),
  an isolated OMP HOME and stock OMP in print/JSON mode with `read,bash,edit,write,grep,glob`, under
  `sandbox-exec`: no writes anywhere in the home directory outside the attempt, `inputs/` read-only (copies of an
  input are ordinary files), the task set, other attempts and the arms file's `sandbox_deny` trees unreadable,
  network to loopback only. The verifier runs afterwards, sandboxed the same way. An attempt during which a
  tunnel closed, or whose endpoint fails right after it, is an infrastructure fault, not a model result: it is
  kept as `<task>.infra-<time>` and rerun once on re-activated engines. Results are
  `<out>/<arm>/<task>/result.json`; a rerun skips finished attempts and moves an interrupted one aside
  (`<task>.interrupted-<time>`) before retrying it. Several `run` invocations may share one `--out`, e.g. one
  `--host` each, started at different times: an exclusive `<out>/<arm>/.<task>.claim` file holding the runner's
  PID keeps them off the same attempt, and a claim whose process is gone is taken over.
- A `kind: "fleet"` arm runs a lead model with stock subagents on other hosts, as a fleet route would: it names a
  `lead` and `agents` (each a single arm at one of its placements). Every bundled agent type the arm lists
  (`task`, `sonic`, `scout`, `reviewer`, `security-reviewer` in OMP 18.5.0) goes to its model through
  `task.agentModelOverrides`; `sonic` and `scout` otherwise follow the lead's `smol` role. The lead also gets
  the `task` and `wait` tools: subagents run in the background, and print mode ends with the lead's turn unless
  it can block on their results.
- `summarize --out <dir>` reports pass rates per arm, track and family, paired outcomes with an exact McNemar
  p-value, agent wall time and output tokens.

The arms file is private (host aliases, roots, key paths). `agent_env` carries tool settings the offline sandbox
needs; pnpm 11+ only reads its own settings from `pnpm_config_*` variables, and without
`pnpm_config_verify_deps_before_run=false` it re-verifies the lockfile over the network before every script.

### Stock calibration as a variant

Stock setup offers to calibrate after an interactive install (`Tune Strata for this PC now?`, default yes; `--yes`
installs skip it): `tools/calibrate.py` measures decode speed with other `--pcie-frac`, `--spec-min-p` and
`--pool-workers` values and keeps one only when it beats the default by more than 3% in an interleaved
re-measurement. The guarded install never calibrates. To try what stock calibration recommends for an installed
profile, run the stock tool against that root's generated config with the server stopped (measurement only,
3.5-5.5 minutes on the RTX 3090 host; it starts its own engine and prints JSON):

```bat
cd <root>\runtime\strata
set APPDATA=<root>\appdata
.venv\Scripts\python.exe -u tools\calibrate.py strata-<tag>.json > <root>\logs\calibrate-<stamp>.log
```

Settings `{}` mean the defaults already won and that profile is the calibrated one. Otherwise save the printed
JSON privately and draft a new profile from exactly the measured one (same tuple, same stock setup choices):

```sh
python3 scripts/upstream_watch.py draft --from profiles/<measured>.json --strata-tag <same> --omp-tag <same> \
  --id <measured id with -calibrated> --strata-src "$STRATA_SRC" --ram-gib <host RAM> --vram-gib <VRAM> \
  --calibration <calibrate.json> --calibration-host <public label> --calibration-date <YYYY-MM-DD>
```

The draft records the kept settings, the stock report and the measured profile's fingerprint in
`strata.calibration` and appends the kept flags the way stock `calibrate.apply` does. Its install runs stock setup
unchanged, then applies the pinned settings with stock `calibrate.apply` and `write_config` (what setup does after
a calibration), and the generated-config check refuses an install whose flags differ. Compare the variant with
its uncalibrated predecessor in separate roots, one at a time, as above.

## Sharing the GPU

The integration assumes it owns the GPU while it runs. `start` refuses a busy GPU. It never stops another
runtime; whoever operates the host must release the GPU first and restore the other runtime afterwards.

A GPU that also drives a display lists the desktop's processes (compositor, logon screen) as WDDM graphics
clients (`C+G`). Profiles for such hosts set `host.display_attached: true`: `start`, `doctor` and G10 then tolerate
graphics clients, record how many there are, and still refuse any compute process or 1,500 MiB of foreign use. An
interactive desktop session can hold close to a gigabyte of VRAM in its applications; signing it out before a run
leaves the logon screen's ~180 MiB.
