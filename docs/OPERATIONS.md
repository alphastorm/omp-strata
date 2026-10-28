# Operations

OMP Strata runs stock Oh My Pi (OMP) against a stock, local Strata server from one self-contained integration root per
profile. Every command takes `--profile profiles\<profile_id>.json --root <root>` (omitted in the examples below).
There is no daemon: `start` launches a detached wrapper (`serve`), and the files under `<root>` are the whole state.

## Current profiles and rollbacks

| Host | Current qualified profile | Qualified rollback profile | Notes |
|---|---|---|---|
| RTX PRO 6000 | `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2` | `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6` | IQ3_S at 262,144 tokens, 4 batch slots, conversation parking, 32K prompt chunks |
| RTX 5090 (default) | `win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2` | `win11-rtx5090-coder-iq1m-131k-strata0.2.3-omp18.12.6` | Coder IQ1_M at 131,072 tokens |
| RTX 4090 + RTX 3090 (`rtx3090-win-a`) | `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2` | `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6` | IQ3_S at 262,144 tokens, stock roles (RTX 4090 as Main), pipeline windows 2, no batch slots, display on the RTX 4090, direct per-layer embedding (PLE) reads (`--ple-io direct`); engine's 8,192 MiB automatic conversation cache |

On the pair (`rtx3090-win-a`), the current v0.2.7 profile pins stock roles (`--gpu-roles 0=main,1=helper`: RTX 4090 as
Main, staged last; layers 0-23 on the RTX 3090 with a 17.6 GiB expert cache and 24-47 on the RTX 4090 with 16.01 GiB)
plus `strata.ple_io: "direct"` (`--ple-io direct`, [Stock PLE direct reads](#stock-ple-direct-reads)), keeping the
26.8 GiB PLE table on direct SSD reads so every start logs a `PLE direct read probe: N rows/s (fine)` line with no
residency-policy line, sizes the automatic conversation cache at 8,192 MiB (up to 4 parked conversations), and keeps
27.3 GiB Windows commit headroom of a 135.7 GiB commit limit while serving (single-sample `scripts/perf_probe.py` at
the end of the chain, not a back-to-back A/B: 100K-token time to first token (TTFT) 30.74 s, versus 31.23 s on v0.2.3
roles, 30.40 s on v0.2.7 default residency and 31.15 s on `STRATA_PLE_AUTO_RAM=0` in earlier back-to-back runs;
[decision](DECISION.md)). Its rollback
is the v0.2.3 stock-roles profile. The v0.2.7 roles profile with PLE in RAM
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2`) stays a held **draft** on
measured commit headroom (G10 1.03 GiB versus 27.3 GiB, 0.632-1.331 GiB in a later bench, and automatic conversation
cache off; reported upstream as [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)).
The PRO locks the 26.8 GiB PLE table in RAM (~33.1 s at start) while keeping 53.7 GB commit headroom and its 8,192 MiB
cache; the RTX 5090 131K root's PLE policy declines RAM residency. The unmeasured v0.2.7 default-split draft, the
default and split-32 v0.2.3 pair drafts and the v0.1.44.1 pair release remain draft, not qualified. Physical display
placement must match the profile. Each profile has its own root (one runtime per root).

**Qualified opt-in (Strata v0.2.7 + OMP 18.13.2, owner decision 2026-10-28):**
`win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2` runs Coder IQ1_M at 262,144 tokens on the RTX 5090, with a
36 GiB available-RAM startup floor and a 1,792 MiB automatic conversation cache, and rolls back to
`win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6` (or the v0.2.7 131K default). Operating condition: the host's
Docker Desktop and WSL, which also run its production NInfer container, must be stopped (39.8 GiB available RAM with
them stopped against the unchanged 36 GiB startup floor, versus 35.7-36.2 GiB with the NInfer VM resident, where
starts and restarts refuse; after WSL restarts that container must be recreated; the v0.2.3 262K rollback has the
same constraint now because the newer NInfer VM is larger). Select the opt-in profile explicitly and keep its own
integration root. The 131K RTX 5090 profile above remains current/default; no default command or client route changes.
Its [ledger](../releases/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2/qualification.json) has 21 pass and 3 not
applicable (retaining the morning failed receipts beside the passing afternoon rerun).

The CI `suite` matrix in `.github/workflows/ci.yml` contains these current and rollback server profiles, the qualified
opt-in and its rollback (eight profiles total), plus any draft actively being qualified. Held drafts (such as the
v0.2.7 pair roles draft with PLE in RAM) and older history are excluded; their ledgers and receipts remain covered by
the all-release `checks` job.

<details><summary>Earlier qualified profiles and single-card rollback limits</summary>

Earlier qualified profiles keep their own roots and ledgers:

- **RTX PRO 6000 and RTX 5090:** v0.2.1 (earlier qualified history on both hosts, including the 262K opt-in; v0.2.1
  integration roots were removed on every host on 2026-10-28), v0.1.44.1 (including the RTX 5090 262K opt-in),
  v0.1.43.1 and v0.1.43 with OMP 18.10.1; each host's v0.1.42 + OMP 18.8.9 profile; on the PRO, v0.1.41 at 262K then
  131K, v0.1.40.3 with OMP 18.8.4 then 18.8.3 slots4-parking, and
  `win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0`; on the RTX 5090, v0.1.41 with OMP 18.8.6 then
  `win11-rtx5090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4`.
- **RTX 4090 + RTX 3090 pair:** v0.2.1 (default-split, earlier qualified history; host root removed on 2026-10-28),
  v0.1.43.1 and v0.1.43 with OMP 18.10.1,
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9`
  and `win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9` keep the display on the RTX 4090;
  `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` requires moving the display back to the RTX 3090.
- **Single-card RTX 3090 and fourth-tuple profiles:** `win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` and the
  fourth tuple's stay qualified for single-card RTX 3090 hosts, but are not rollbacks on `rtx3090-win-a` while both
  cards are installed: those profiles name GPU 0, now the RTX 4090; single-card `start` checks only that GPU 0 is free
  and would run there, although `doctor` reports the model mismatch. The fourth tuple's profiles, such as
  `win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10`, stay qualified as earlier RTX 5090 history and on the
  single-card RTX 4090.

</details>

## Layout of the integration root

| Path | Contents |
|---|---|
| `downloads\` | Pinned OMP, Strata and llama.cpp archives and the locked wheels, each verified by size and SHA-256 |
| `models\` | Pinned GGUF shards under `<variant>-<quantization>` (two for the Coder and for IQ3_S, four for Unsloth UD-Q4_K_XL) |
| `runtime\strata\` | The pinned stock Strata source (v0.2.7 current on all three hosts, including the RTX 5090 262K opt-in and the pair PLE-direct profile, with engine component 0.1.52 staged under `runtime\strata\engine\`; v0.2.3 rollbacks across all three hosts with engine 0.1.48; v0.1.40.3 for the qualified single-card RTX 3090 profile), its generated config and its hash-locked `.venv` |
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
| `start` | Refuses when owned processes already run, when anything else holds the port, when the GPU has 1,500 MiB or more used or any compute process (or any graphics client, unless the profile declares the GPU display-attached), or when less RAM is available than the profile's `min_available_ram_gib_at_start`. Waits up to 900 s for readiness. |
| `stop` | Stops the recorded wrapper and server and everything currently beneath them, deepest first. Only processes whose PID, creation time and executable still match are touched. Waits for the port to be released. Repeating it is a no-op. |
| `restart` | `stop`, then `start`. |

**Process ownership.** The process tree on Windows is: `serve` wrapper (`python.exe`) → venv `python.exe` (a
redirector) → base `python.exe` running stock `serve/server.py` → `strata.exe` (the engine, which owns the GPU). A PID
alone never identifies an owned process: PIDs are reused, so `stop` verifies PID, creation time and executable before
stopping descendants deepest first.

**Startup RAM floors (`min_available_ram_gib_at_start`) and readiness times:**

- **Current profiles:** 74 GiB and 80.2-94.3 s readiness (70.3-70.4 s in single-sample perf runs; includes ~33.1 s
  locking the 26.8 GiB PLE table in RAM; v0.2.3 rollback: 23.7-26.8 s) on the RTX PRO 6000 262K profile with slots and
  parking; 34 GiB and 18.7-28.4 s readiness (v0.2.3 rollback: 17.0-23.0 s) on the default 131K RTX 5090 Coder profile
  (that keeps every expert in RAM); 36 GiB and 16.1-16.9 s readiness (G16 16.7 s; v0.2.3 rollback: 19.0-23.0 s; v0.2.1
  history: 18.5-19.6 s) on the qualified v0.2.7 opt-in RTX 5090 262K Coder profile when the host's Docker Desktop and
  WSL are stopped (39.8 GiB available at start; refuses at 35.7-36.2 GiB when the production NInfer VM is resident);
  78 GiB and 56.8-57.0 s readiness on the current v0.2.7 RTX 4090 + RTX 3090 pair PLE-direct profile (55.7-56.2 s on
  its v0.2.3 roles rollback, 46.7-47.1 s on v0.2.1 history, and 54.7-55.0 s on its v0.1.43.1 and v0.1.43 predecessors).
  The held v0.2.7 roles draft (PLE in RAM) took 89.8-93.1 s, including ~31.4-37.5 s locking the 26.8 GiB PLE table in
  RAM.
- **Earlier and exploratory profiles:** 66 GiB on the earlier v0.1.42 pair profile; 72 GiB on the RTX PRO 6000 131K
  18.8.4 and 18.8.3 predecessors, and 64 GiB on the v0.1.40.2 profile; 34 GiB and 17-33 s readiness on single-card
  RTX 3090 131K Coder profiles; 16 GiB and about 15 s readiness on the low-RAM RTX 4090 profile; 52 and 64 GiB on the
  exploratory IQ3_S profiles on the 24 GB GPUs.

**First-prompt expert-cache warmup.** On the RTX PRO 6000 the server opens while it is still filling its 46.8 GiB GPU
expert cache, so the first prompt after a start waits for it: 6 s for a 7,698-token prompt in the Strata v0.1.41 run,
against about 1 s for an 8,030-token prompt once the cache was full. The RTX 5090's 23.4 GiB cache fills before it
reports ready.

## Failures and recovery

- **Engine process died** (crash, OOM, kill). Stock Strata answers the request in flight with an error and starts
  the engine again on the *next* request. That takes about 15 s on the RTX 5090 and about 30 s on the RTX PRO 6000
  (the experts are reloaded), and the whole prompt is prefilled again. Until that request, `status` reports
  `degraded` ("no engine process"), and `launch-omp` refuses to start. On a multi-GPU profile `status` stays
  `degraded` after that restart too ("startup stage order unavailable for current engine generation"): stock restarts
  the engine with the same command, but `"layer_split": "auto"` places the layers again from each card's free VRAM,
  and the integration verifies the stage order and layer boundaries only for an engine generation it started itself.
  Every pair qualification shows this once, after G15 kills the engine. Recover with `restart`, which also clears the
  stale-cancel state below.
- **Stale cancel after a queued client disconnects** (upstream defect Strata#183, reproduced by `g14q`; present in
  the first candidate's v0.1.27, fixed in v0.1.28, and confirmed fixed by `g14q` on the second candidate's v0.1.30
  and in every qualification run since). If a client disconnects while its request is still queued behind another
  one, the next request with a multi-chunk prompt (thousands of tokens) fails with HTTP 400 `cancelled`. The engine
  then exits, and the request after that gets HTTP 503 before the engine restarts. Short prompts are not affected.
  With OMP this appears as one failed turn, possibly followed by an engine restart. Run `restart` after cancelling
  queued work.
- **HTTP 400 "requests are never truncated".** The prompt plus the requested output does not fit in the profile's
  context (262,144 tokens on the current RTX PRO 6000 and pair profiles and the qualified opt-in RTX 5090 profile;
  131,072 on the default RTX 5090 and single-card profiles). OMP sizes the output cap to
  the room it estimates is left. The integration declares the window 1,024 tokens smaller than the engine's so that
  estimate errors do not reach the server. A single prompt larger than the declared window (about 261K or 130K
  tokens) cannot be sent at all; OMP compacts long sessions before that point.
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

**Component engine releases (Strata v0.2.1 and later).** These releases publish no `strata-windows-x64.zip`; the
Windows engine is a separate package, `strata-engine-<engine version>-windows-x86_64-cuda-cuda13.tar.gz`, versioned
apart from the app (v0.2.1 ships engine 0.1.46). A profile for one adds `strata.engine_component` (format, platform,
backend, variant, the SHA-256 of the raw `engine-component.json`, its `build_id`, and BUILD.json's `source` and
`commit`), and its `strata.engine_version` is the engine's own version. `install` downloads the pinned tarball like
any artifact, checks every member against the manifest (regular files at the archive root only, exact file set,
per-file size and SHA-256), and stages the files into `runtime\strata\engine\` before stock setup runs; setup then
reuses that engine and downloads or compiles nothing, with pip's package index switched off. An `engine\` folder that
holds anything else is refused, never repaired. The manifest's ed25519 signature is not verified, and no Control
package, signed feed or desktop installer is used. Setup's own `args_written` record must equal the config's `args`,
with no `user_args`; the pinned calibration, tip and pipeline-window steps restamp it the way stock writers do.

## Sharing the GPU

The integration assumes it owns the GPU while it runs. `start` refuses a busy GPU. It never stops another
runtime; whoever operates the host must release the GPU first and restore the other runtime afterwards.

A GPU that also drives a display lists the desktop's processes (compositor, logon screen) as WDDM graphics
clients (`C+G`). Profiles for such hosts set `host.display_attached: true`: `start`, `doctor` and G10 then tolerate
graphics clients, record how many there are, and still refuse any compute process or 1,500 MiB of foreign use. An
interactive desktop session can hold close to a gigabyte of VRAM in its applications; signing it out before a run
leaves the logon screen's ~180 MiB.

## Maintainer recipes

### Release campaigns (OP10 discovery → OP11 host-owned qualification)

[`schemas/release-campaign.schema.json`](../schemas/release-campaign.schema.json)
(`$id: release-campaign.schema.json`, historical schema 1 and new schema 2) separates **a discovered upstream release**
from **completion on each host**. [`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json) is **`complete`**:
GitHub release **425568621**, published **2026-10-27T14:54:42Z**, annotated tag
`3f6d9c28e56bfce604601f39de53d457fa90dc74` peeled to `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`, opened with
`scripts/campaign.py open --release v0.2.7 --omp-tag v18.13.2`, with all five rows (the PRO, RTX 5090 131K default,
RTX 5090 262K opt-in, 4090+3090 pair PLE-direct variant, and Studio→PRO route) qualified with their `manifest.json`
and `restored-state.json` references, alongside the earlier complete
[`releases/campaigns/v0.2.3.json`](../releases/campaigns/v0.2.3.json) and
[`releases/campaigns/v0.2.1.json`](../releases/campaigns/v0.2.1.json) campaigns (with v0.2.1 having
coalesced [`releases/campaigns/v0.1.45.json`](../releases/campaigns/v0.1.45.json), `superseded_by: v0.2.1`;
v0.1.45 was never drafted or qualified). Upstream later added its 0.2.7.1 assets (Control 0.1.53, ARM64 and macOS
DeepSeek packages) to the same GitHub release; the pinned Windows CUDA 13 engine asset is unchanged. A lane may list
stock variants' profile families (`scripts/campaign.py` `LANES`); the newest qualified profile across them is the
next predecessor, and `set-host` can qualify a lane's row with another variant's ready manifest at the same Strata
and OMP release. When a new campaign opens, its candidate profile IDs are prepared names, not materialized profiles
or claims of qualification. Release discovery uses only qualified release manifests: comparison-only profiles without
a release manifest do not become baselines or block discovery; malformed manifests still make discovery unavailable.
After the initial v0.2.7 pair roles profile was held on commit headroom, `set-host --status qualified` with the
PLE-direct variant's ready manifest renamed the pair row to
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2` (retaining both
manifests in `result_refs`) before the RTX 5090 262K row completed the campaign
([Stock PLE direct reads](#stock-ple-direct-reads), [decision](DECISION.md)).

```sh
python3 scripts/campaign.py open --release v0.2.7 --omp-tag v18.13.2
python3 scripts/campaign.py status
python3 scripts/campaign.py status --release v0.2.7
# Before a pending row runs (qualified rows are terminal and cannot requeue):
python3 scripts/campaign.py set-host --release v0.2.7 \
  --profile win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2 --status queued
```

`open` reads only GitHub metadata, resolves the annotated/lightweight tag, cross-checks the complete asset
endpoint with both release-ID and tag payloads, and atomically writes the campaign. Schema 2 freezes every
asset's ID, name, byte count, publisher SHA-256 (or null) and download URL, plus the effective prerelease
classification and GitHub flags; existing schema-1 records are not rewritten. Duplicate opens preserve its original
discovery time and host progress. A moved tag, changed release identity or changed asset pins returns
**unavailable** (exit 4), without replacing the frozen evidence. Drafts and unselected prereleases return explicit
`skipped` reasons; beta CLI intake without `--allow-prerelease` is refused (exit 2).
Malformed/truncated/missing API data is unavailable, never “no update.” `--check` prints the inventory
without writing or coalescing any record. `--omp-tag <tag>` names every candidate for that stable OMP release
instead of its predecessor's, while each row still records the predecessor's own pin;
[`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json) was opened with `--omp-tag v18.13.2`.
`status` reloads file-backed state; no in-memory cursor, scheduler or new host runner is involved.
Run edits from one operator checkout and commit the resulting campaign changes; atomic files are not a
distributed multi-writer store.

Opening a newer stable release adds `superseded_by` and a disposition note to **pending** rows of older stable campaigns.
Queued/running/qualified/failed/blocked rows and their result/restoration references are untouched; complete
campaigns are immutable. Interrupted coalescing converges when `open` is repeated. A campaign is `pending`
before execution, `running` after any execution/outcome, `complete` when all non-superseded rows qualify, or
`superseded` when every row was coalesced. A skipped older row is not a qualification pass.

**Owner-selected v0.2.0-beta:** [UPSTREAM-BETA.md](UPSTREAM-BETA.md) records the frozen source/component
inventory, metadata-only commands and exact remaining installation contract. `--allow-prerelease` is explicit
even when GitHub's flag is false; a beta campaign never coalesces stable rows (nor is coalesced by stable intake).
Without `--check`, beta `open` freezes/reuses its isolated metadata campaign but returns **exit 2 / blocked**,
not a runnable-profile success. Stable component releases now install natively through a staged engine component
([Upgrades](#upgrades)); component **beta** drafting stays refused and the beta campaign remains metadata only.

Host row transitions are `pending → queued → running → qualified|failed|blocked`; pending/queued may block,
and failed/blocked may explicitly requeue. A blocker needs a result reference or `--note`. Results append,
never erase predecessor evidence:

```sh
python3 scripts/campaign.py set-host --release v0.2.7 --profile "$PROFILE_ID" --status running
python3 scripts/campaign.py set-host --release v0.2.7 --profile "$PROFILE_ID" --status blocked \
  --note "Waiting for the host owner's exclusive window"
# After publication, public-hygiene review, restoration, and the owner's qualification decision:
python3 scripts/campaign.py set-host --release v0.2.7 --profile "$PROFILE_ID" --status qualified \
  --result "releases/$PROFILE_ID/manifest.json" \
  --restored-state "releases/$PROFILE_ID/restored-state.json"
```

References must be existing public repository-relative files, not private host paths or raw logs.
`qualified` calls the existing `verify_release.py` verifier with `require_ready=True`, requires that exact
candidate's manifest to be `qualified`, and requires a restored-state reference. The operator authors the scrubbed
restoration receipt from the actual lease/controller and HTTP observations; this campaign never fabricates one.
The ordinary release manifest, receipts and owner decision remain authoritative.

**OP11 consumes these rows; OP10 does not acquire a GPU, contact a host, install, start, stop, restore or promote.**
Before requeueing/running a row, the host owner reviews the source delta and uses the existing `upstream_watch.py
draft` flow below to materialize its new candidate profile and empty ledger. It must keep the OMP release its row ID
names and the predecessor's model, context and host choices unless a separately reviewed new profile is intended.
Fetch and sync exact tooling; take an approved exclusive GPU window with the host's existing lease/controller; retain
the qualified predecessor.
A next pair candidate's predecessor is the current **v0.2.7** PLE-direct stock-roles profile
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`), while **v0.2.3**
(stock roles) stays its qualified rollback and **v0.2.1** (default variant, host root removed on 2026-10-28) and
**v0.1.43.1** are earlier qualified history (the held `v0.2.7` roles draft with PLE in RAM, the unmeasured `v0.2.7`
default-split draft, the default and split-32 `v0.2.3` drafts, and the
[draft v0.1.44.1 pair release](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.44.1-omp18.10.1/manifest.json)
remain unqualified). For v0.2.7, the 2026-10-28 measurement window ran the stock-roles draft against the qualified
v0.2.3 roles profile, admitted engine 0.1.52's stage order (`15c7426`;
[measurements](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132)), held the PLE-in-RAM roles draft on
commit headroom (1.03 GiB vs 27.3 GiB; [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)), and
then qualified the PLE-direct variant (`--ple-io direct`, 27.3 GiB commit headroom and 8,192 MiB conversation cache).
The default-split v0.2.7 draft was stopped during download and stays an unmeasured draft.
The two 5090 lanes run sequentially; 262K is opt-in, never a replacement of the 131K default. On 2026-10-28 the
morning v0.2.7 262K run refused restarts at 35.7-36.2 GiB available RAM with the resident NInfer VM against its
unchanged 36 GiB startup floor (G16 recorded 35.8 GiB), and the afternoon rerun on the same root with Docker Desktop
and WSL stopped (39.8 GiB available RAM) passed every gate and qualified on v0.2.7 (rolling back to v0.2.3). See the
[v0.2.7 source review](UPSTREAM.md#strata-v027-setup-review-component-engine) for the combined 26-wheel Python lock
(`locks/strata-python-cp313-win_amd64-strata0.2.7.txt`), runtime defaults, `/tool-media/` G13 classification, and OMP
18.13.2 `replace` edit-tool and linked-session-reader coverage.

The v0.2.7 server rows ran this way on 2026-10-28 (`fetch`, then `requalify.py`, each in its host's own new
root). From the candidate's tooling on each Windows host, in PowerShell, after the profiles, pinned downloads and owner
window exist (each root below is a new root):

```powershell
# RTX PRO 6000
python scripts/requalify.py --profile profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2.json --root "$env:USERPROFILE\omp-strata-0.2.7-omp18.13.2-pro"
# RTX 5090 default
python scripts/requalify.py --profile profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2.json --root "$env:USERPROFILE\omp-strata-0.2.7-omp18.13.2-5090-131k"
# RTX 5090 opt-in (requires Docker Desktop and WSL stopped on the host so 39.8 GiB RAM is available against the 36 GiB floor)
python scripts/requalify.py --profile profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2.json --root "$env:USERPROFILE\omp-strata-0.2.7-omp18.13.2-5090-262k"
# RTX 4090 + RTX 3090 (stock roles with RTX 4090 as Main, plus --ple-io direct)
python scripts/requalify.py --profile profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2.json --root "$env:USERPROFILE\omp-strata-0.2.7-omp18.13.2-pair-pledirect"
```

Do not use `--keep-running` for campaign runs. `requalify.py` stops only its own runtime; it **does not restore a
foreign tenant**. Pull the named run using `pull_run.py`, dry-run then publish with `publish_run.py`, verify with
`verify_release.py --require-ready`, restore the previous tenant with its existing controller, and record exact
restored service/HTTP observations before reporting the outcome. Preserve failed evidence and blockers.
Do not call `requalify.py` on the Studio route: after the PRO qualifies, materialize the new route against its
server fingerprint, then run the independent [G23 auth/drop/restart probe](REMOTE.md#g23-and-fan-out-evidence)
with private bindings/restart commands. It has its own ledger and restoration reference.

Studio command (run after those private bindings, restart commands and the new qualified server exist):

```sh
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.2.7-omp18.13.2"
python3 scripts/remote_gates.py --profile routes/client-rtxpro6000-262k-strata0.2.7-omp18.13.2.json \
  --root "$ROOT" --bindings "$ROOT/state/bindings.json" \
  --restart-commands "$ROOT/state/restart-commands.json" \
  --output "$ROOT/proofs/g23-$(date -u +%Y%m%dT%H%M%SZ)" --implementation-commit "$(git rev-parse HEAD)"
```

### Requalifying a new tuple

The sequence used for the second candidate (about 45 minutes of exclusive GPU time, run from a client machine over
SSH with `stdin` closed, so that OMP's print mode never waits on a pipe):

1. **Report, then draft.** `python3 scripts/upstream_watch.py report --strata-src <local Strata checkout>`
   compares stable releases with the newest stable pins whose release manifests are **qualified**, not newer draft/beta pins,
   and checks `upstream-watch.json`
   (the issues/PRs in [UPSTREAM.md](UPSTREAM.md)). It reads local tags, never fetches or changes that checkout.
   JSON goes to stdout, a short summary to stderr: exit **0** = complete/no news, **3** = complete/news,
   **4** = incomplete (including failed, malformed or truncated API responses), never "no change".
   `--pinned-strata-tag <tag> --strata-tag <tag>` selects an explicit source comparison. The checklist compares
   setup constants, the requirements blob, generated/optional config keys, classified server routes and new
   `STRATA_*` names. Review any delta before materializing a runtime. A closed-unmerged Strata PR means
   **check the maintainer commit**, not rejection.

   **Shared-egress sandbox: use the GitHub-API-free candidate path.**
   Use `report --candidate-only <tag> --no-github-api --from <predecessor profile>
   --strata-src <local Strata checkout> --variant cuda13`, then `draft --no-github-api`.
   A per-command request budget cannot reserve GitHub's shared anonymous **60/hour public-IP pool**:
   concurrent jobs can exhaust it before a single candidate finishes. `--no-github-api` makes **zero
   `api.github.com` requests**, implies anonymous mode, never reads `GH_TOKEN`/`GITHUB_TOKEN` or invokes
   `gh auth token`, and never falls back to REST or credentials. It skips global news and tracked items.
   The explicit predecessor's immutable profile pin must still match the local tag; the same reviewed
   source checklist and full draft planner apply.
   Exit codes remain **0** for no newer candidate, **3** for candidate news, **4** for incomplete/refused review.

   ```sh
   python3 scripts/upstream_watch.py report --candidate-only v0.2.2 --no-github-api \
     --from profiles/<predecessor>.json --strata-src "$STRATA_SRC" --variant cuda13 \
     --engine-archive <scratch-cuda13-tarball>
   # Exit 3 above is successful release news, not a reason to stop the reviewed draft.
   python3 scripts/upstream_watch.py draft --no-github-api \
     --from profiles/<predecessor>.json --strata-tag v0.2.2 --omp-tag v18.10.1 \
     --id <new-id> --strata-src "$STRATA_SRC" --variant cuda13 \
     --engine-archive <scratch-cuda13-tarball>
   ```

   Download-mode inventory and integrity contract:

   - Resolve the exact tag object and peel with credential-free `git ls-remote --tags` over public HTTPS,
     before and after discovery; no REST tag lookup. Verify the local source against that peel.
   - Fetch only tag-specific `https://github.com/<owner>/<repo>/releases/download/<tag>/SHA256SUMS.txt`,
     `latest.json`, and `install-manifest.txt` when indexed. The checksum index is the publisher's HTTPS trust
     root; its own observed hash is recorded, not claimed to be self-signed. Verify consumed metadata bytes
     against the index. `latest.json` must name the selected app version; its UI pointers and any manifest
     entries must agree with the index. Never follow its mutable `releases/latest` pointers.
   - Select the engine component from checksum-indexed filenames, not from the app version or the Control
     manifest. The v0.2.2 install manifest names **Control only**. Download the engine through its tag-specific
     URL and verify its full bytes against `SHA256SUMS.txt`; derive byte length from that verified stream.
     An existing `--engine-archive` is fully rehashed, never silently overwritten. A missing path is populated
     only after verification; failed transfers leave no final archive. No retry or API fallback.
   - Re-read the checksum index after each discovery and repeat discovery before committing draft outputs.
     Changed checksums, tag identity, metadata or selected engine pins refuse. Missing required digests refuse
     explicitly, rather than borrowing an API digest or weakening validation. Full draft still inspects the
     verified component manifest without executing binaries.
   - OMP must remain the predecessor's exact tag. Public Git must match its pinned `source_commit` before and
     after drafting; preserve its already-pinned artifacts unchanged. An OMP version change is refused because
     this path cannot establish new OMP publisher digests. Other immutable predecessor pins stay subject to the
     existing planner/dependency checks. Model and MTP metadata still use **two Hugging Face API requests**
     for the reviewed one-page model listing; additional HF pages are traversed completely.
   - `source-release.json` uses distinct `github-release-downloads` provenance: checksum-indexed assets,
     verified document hashes/lengths and Git identity. Unconsumed assets have unknown byte lengths. It does
     **not** invent REST release/asset IDs, GitHub immutable/prerelease flags or a REST publication timestamp;
     `latest.pub_date` is recorded separately. A pre-existing REST campaign snapshot cannot be silently
     reinterpreted as download evidence: differing provenance refuses. This is neither signature verification
     nor host qualification.

   **API-free request budget:** zero GitHub REST requests for report plus any number of drafts. With the
   v0.2.2 metadata layout, one report + one draft uses 12 small release-download GETs (checksum index twice,
   latest and manifest per discovery), eight public Git tag queries, and two HF metadata requests. The engine
   is downloaded once when both commands share `--engine-archive`; otherwise each invocation uses and removes
   a temporary archive. Keep an explicit archive in the sandbox's scratch write scope, not the repository.
   `--no-github-api` does not support metadata-only `draft --check`: byte verification is required.

   **Owner/REST mode remains available and unchanged.** Omitting `--no-github-api` retains the REST release
   inventory; candidate-only is still anonymous, and `--anonymous` alone still means credential-free REST,
   **not API-free**. The existing cold request budget for one candidate report + one full draft, annotated
   Strata/OMP tags and one page per asset/model listing, is:

   | Step | GitHub API requests | Hugging Face metadata requests |
   | --- | ---: | ---: |
   | Candidate report: release by tag, initial ref, annotated object, assets, release by ID, final ref | 6 | 0 |
   | Draft: two complete candidate identity checks, OMP ref/object and release/assets | 16 | 2 |
   | **Total** | **22** | **2** |

   The counting-transport unit regression asserts **24 HTTP calls, at most 25**, including 304 responses
   and separate cold API instances for report/draft. Each additional page adds a request per traversal;
   pagination completeness checks are not bypassed to fit a budget. Local Git/source/archive reads,
   compatibility generation and downloads from release-delivery URLs are not GitHub API calls.
   Repeated mutable endpoints use `If-None-Match` when an ETag is supplied; a validated 304 reuses both JSON
   and pagination headers. A changed 200 response is still checked for identity drift. The final tag ref is
   always re-read; its unchanged immutable annotated object need not be peeled twice within a discovery.
   Cache lifetime is one command only: no persistent cache, credential store or assumption that anonymous
   304s are quota-free.

   This REST budget is **not sufficient for shared-egress sandbox work**. A second full draft adds up to
   16 GitHub + 2 HF calls. On HTTP 403/429 with
   `X-RateLimit-Remaining: 0`, either command stops at the **first** refusal and names the reset time in UTC
   (or explicitly says the reset header is unavailable). There is no automatic retry or credential fallback.
   `report --anonymous` can also run the broad news sweep, but that sweep has no 25-call budget.

   `python3 scripts/upstream_watch.py draft --from <predecessor profile> --strata-tag <tag> --omp-tag <tag>
   --id <new id> --strata-src <local Strata checkout>` resolves live GitHub release asset sizes/digests and
   immutable tag commits, plus Hugging Face shard sizes/LFS digests at stock setup's revisions. Lightweight tags
   resolve directly; an annotated tag is peeled only when its object SHA and tag name match the ref and its
   target is a commit (not another tag, tree or blob). The Strata commit must equal the local checkout's
   `<tag>^{commit}`; profiles pin that peeled commit, and draft JSON records annotated `tag_object_shas`.
   The complete frozen Strata identity/inventory is also saved as `releases/<id>/source-release.json`;
   an existing campaign is checked for drift before drafting. `draft --release <tag> --allow-prerelease
   --variant cuda13 --check` is a metadata-only path, not a runnable component profile (see
   [UPSTREAM-BETA.md](UPSTREAM-BETA.md)). Optional
   `--family`, `--model`, `--context`, `--ram-gib` and `--vram-gib` select a variant. RAM/VRAM here are planning
   inputs, not purchased-capacity floors. Every host floor is the maximum of the predecessor's floor
   and stock setup's estimate: a tuple bump never lowers an established operational constraint. The
   draft JSON reports both inputs and the selected floor. The tool evaluates only stock setup's pure choices and inline
   config arithmetic; it never imports/runs setup's main, fetches an installer or writes a lock. Unfamiliar
   planning code, changed dependencies/lock inputs, mismatched tag identities, missing pins and degraded variants are
   refused (exit **2**, success **0**). The reviewed lane is text-only native Windows NVIDIA, no low-RAM
   mode or RoPE extension, with stock KV streaming; other choices need explicit source review.

   **OMP 18.8.8+ compaction thresholds:** the default trigger is unchanged (the window less the larger of 15% and
   16,384 tokens: 110,541 in a 130,048-token window), but a numeric per-model threshold became a policy base rather
   than an exact trigger; `f<tokens>` is the exact form. G17, G18 and G18L size their sessions from the pinned OMP
   version, and G18's reduced threshold is written as the model's `f12000` entry on those lanes. The source-backed
   cases are in `tests/fixtures/omp-compaction-thresholds.json`.

   **Hybrid CPUs (Strata v0.1.39+):** stock setup writes `--pool-workers` on a CPU with more efficiency than
   performance cores (performance cores - 1 + half the efficiency cores; 15 on an 8P + 16E i9-14900K). Pass the
   host's physical core counts as stock's `cpu_cores()` reports them, `--cpu-cores 8,16`; the draft records them
   as `host.cpu_cores` (later drafts from it keep them) and plans the flag. Profile validation accepts
   `--pool-workers` only as that recommendation and refuses a calibration on such a host. Omit the option when all
   cores are alike; install still refuses a host whose stock setup plans another `--pool-workers`.

   The new profile and `releases/<id>/{manifest,qualification,source-release}.json` are created append-only;
   existing profile/release destinations are never overwritten. **`docs/COMPATIBILITY.md` is also a draft
   output:** after creating the records, `draft` regenerates it with `scripts/render_compatibility.py`'s
   renderer and returns its path as `compatibility`. Include that derived document in the draft PR and its
   sandbox write scope; `python3 scripts/render_compatibility.py --check` must remain current. This does not
   promote the row: the acceptance matrix supplies **24 gates, all `not_run`**, no receipts or install identity,
   and no predecessor receipts are copied. A matrix-write failure is a refusal, not successful drafting; repair
   the output and rerun the renderer, not the append-only draft. Outside candidate-only/`--anonymous` mode,
   GitHub auth remains optional (`GH_TOKEN`, `GITHUB_TOKEN`, then `gh auth token`); it is never sent to Hugging
   Face or printed.

   **Experimental Unsloth Q4 (Strata v0.1.36):** `--family unsloth --model UD-Q4_K_XL --context 131072 --ram-gib 127.69
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
   --root <root>` (including install/keygen/start). Launch it detached with output redirected to a new file per run;
   its first line names the atomically updated summary and adjacent per-step logs. `--dry-run` prints the plan,
   `--from <step>` or `--only <step,...>` selects steps, and `--keep-running` skips the otherwise unconditional
   final stop. The pilot uses one attempt and the scored batch uses the evaluator's required three.
   A resolved selection that splits a gate's same-run steps is refused before any files or processes are
   created, including with `--dry-run`. Keep `g14,g14q` and `g18,g18l` together, and select `eval` whenever `pilot` is
   selected (G24 is judged on the scored batch; the pilot is reported when present); G26's `quickstart`
   also requires `install,start` in that same run (`quickstart-tests` is emitted automatically). An installation
   in an earlier summary cannot satisfy G26. For example, `--only start,g18,g18l,stop` is a complete G18 rerun,
   while `--only start,g18,stop` and `--from g10` are refused. `--diagnostic` explicitly allows partial diagnostic
   runs and prints one `will not publish` warning per partial gate to stderr, preserving the summary path as the
   first stdout line. It does not relax publication requirements.
6. **Publish.** From the client machine, `python3 scripts/pull_run.py --host <ssh host> --root <root> --log
   <requalify log> --dest <empty private directory>` copies the summary, install record, step results and evaluation
   files of the one run that log names (it refuses a log naming two runs). `python3 scripts/publish_run.py --pulled
   <that directory> --profile profiles/<id>.json --host-label <public label> --root-path <root>
   --implementation-commit <tooling commit> --dry-run` checks the
   plan without writing; without `--dry-run` it scrubs the results (root path, `--private` terms, the untracked
   denylist), writes them under `releases/<id>/evidence/`, appends a receipt per measured gate (G10-G21, G24, G26),
   updates the ledger and sets the manifest's install identity. Add `--host-had-strata` when the host already had
   another root. Status and publication decisions stay with the operator, and the receipts for G00-G06, G22, G23
   and G25 are written by hand. Pull and publish each complete-gate rerun the same way; companion steps must be
   in that rerun's summary, not combined across runs. Earlier receipts, failures included, stay.
   `verify_release.py` and the hygiene scan must pass before the commit.

### Fifth-tuple draft commands

<details><summary>Historical v0.1.36 + OMP 18.4.12 and experimental RoPE draft commands</summary>

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

</details>

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

`scripts/experiment_loop.py` runs **only the candidate**. The fleet controller owns the incumbent;
the driver owns only its candidate process tree. It never opens the incumbent installation, starts,
stops or adopts its processes, writes installed G10, or changes its identity. The old quiesce/restore,
restoration-adoption handoff and `recustody-incumbent` surfaces are removed, not compatibility modes.
There is no artifact-reference attribution or census of non-owned processes. Ordinary installation
lifecycle commands remain available to their existing callers; this driver cannot invoke them on a baseline.

## Threat model

The candidate-only experiment driver runs under a single operator account on a personal Windows
appliance. The experiment root's parent is operator-only; the driver asserts its ACL at start.
The only legitimate concurrent writers are the driver's own generations and the fleet controller,
which owns the incumbent. Competing driver starts, the driver's own stale or partial state,
controller generation changes, and process-tree custody of the candidate are in model.
Another principal concurrently mutating the operator-only experiment root during a window is out
of model: directory swaps, reparse/junction insertion, and log redirection by that principal are
explicit non-claims. The start-time ACL assertion is the control, not a claim of protection against
a hostile operator, an administrator bypassing that ACL, or a compromised operator account.

The driver refuses unsafe ownership or write ACEs on the parent, root, `state/`, and `evidence/`.
It pins directory identities by volume serial and file index, refuses a replaced state directory or
changed admission record before command effects, and checks output directories through handles.
Logs use create-new semantics. Controller generation is checked again after HTTP observation;
failed local hold removal is not custody release. Experimental readiness observes only owned job
membership, never an unfiltered Toolhelp census, and requires one live candidate engine before
publishing ready. The guard verifies the recorded server and engine identities in that job both
before and after authenticated HTTP observation. These checks retain candidate admission and
frozen-harness invariants; they do not enlarge the threat model above.

Host-free executable evidence (`python -m tests.unit.test_experiment_loop`) covers **408 schedules**:
the successor's six added boundary schedules produce **6 counterexamples before** these closures
and **0 after**. The native ACL and directory-handle APIs are stubbed in unit tests; these counts
are finite model evidence, not Windows host qualification or a claim about out-of-model actors.
The readiness-expanded model covers **412 schedules**, with **4 counterexamples before** the
readiness remediation and **0 after**: engine absence or exit during HTTP cannot publish ready
or pass the candidate guard merely because the server remains alive.

#### Window 2: controller reservation, candidate, controller return

Use the private host alias in place of `<host>`; never commit machine bindings or raw evidence.

1. **Freeze without effects.** Retain the earlier comparison JSON and its original job-manifest bundle,
   including the WO2 request file and golden files manifest. Freeze those exact bytes, the candidate and
   baseline profile metadata, the original baseline experiment manifest (bound by the job manifest),
   the full Python harness dependency closure (including `cli.py`) and the lead-reviewed private workload
   runner. Historical manifests must be explicitly re-frozen; they cannot authorize the new driver.
   Candidate install/conversion is isolated: foreign or missing installed fingerprints refuse before fetch/setup,
   prepared NVFP4 uses its own dense native GGUF/PLE/MTP, and incomplete conversion marks never authorize reuse.
2. **Lead: `fleet use <host>`.** Wait for its final **Ready for you**, not its earlier Reserved/Draining
   events. Record that exact generation in the private bindings. The controller closes admission, drains,
   stops its recorded generation and proves expected GPU UUIDs and VRAM below 1,500 MiB.
3. **Driver: candidate arm only.** Run detached on native Windows using the command below. The driver reads
   `C:\ProgramData\OMP\windows-hosts\state\fleet-control.json`, the state returned by `fleet status <host>`.
   It requires `reserved=true`, `admission_open=false`, `phase="Ready for you"`, no blockers, no admitted
   jobs or unresolved transaction/hold, and a successful `resources` receipt for the exact generation.
   That receipt is the controller's physical stop proof; missing telemetry is not inferred from Reserved.
   The expected UUID list and measured VRAM are checked, and the incumbent's loopback port must be closed
   before any install/start effect. Reservation checks continue during candidate commands.
4. **Prove candidate death before return.** All candidate launches/runner commands are in native Windows
   kill-on-close, non-breakaway jobs, assigned while suspended. Stop requires empty native membership and
   independent exact-token observations. Pending launches are cancelled under the candidate root lock.
   A pre-existing live, pending or unproved candidate generation refuses before installation; it is never
   adopted or stopped by a new invocation. Root-lock acquisition and both native/token proofs share one
   aggregate cleanup deadline. Exhaustion still attempts native termination but cannot claim release.
   A failed tree proof preserves the driver's `persistent_hold`; a dead parent/PID is not release evidence.
   An interrupted external golden client also keeps that hold until its outcome is reconciled.
5. **Lead: `fleet return <host>`**, only after `candidate_tree_dead=true` and `custody_released=true`.
   Controller-owned adoption/reconciliation follows the existing controller procedure; there is no
   driver-issued restoration/adoption receipt and no driver `fleet resume`. A blocked return is a controller
   hold to reconcile, never permission to delete the driver's evidence or replay the experiment.

The total window cap is **3.5 hours**, measured from the controller readiness receipt's `observed_utc`
(numeric Unix seconds, written by the controller with `time.time()`).
The driver reserves at least 30 minutes for the lead's `fleet return` and 120 seconds for its own cleanup,
and stops admitting candidate work before those budgets. It emits the absolute return deadline.
This is a deadline/budget for the lead, not a claim that the driver executed or measured controller return.
No controller operation is triggered by importing, planning or testing this code.

```sh
python scripts/experiment_loop.py plan \
  --baseline <incumbent-profile-id> --candidate <candidate-profile-id> \
  --candidate-only-against <retained-comparison.json> --job-manifest <job-manifest.json> \
  --baseline-manifest <original-loop-manifest.json> \
  --runner <private-candidate-runner.py> --rationale "Retained incumbent versus candidate" \
  --out <private-manifest.json>
python scripts/experiment_loop.py run --manifest <private-manifest.json> \
  --bindings <private-bindings.json> --evidence-dir <private-evidence-parent>
python scripts/experiment_loop.py report --directory <private-run-directory>
```

Private bindings contain `candidate_root`, `host_lock_id` (the same physical lock used by the evaluator),
`controller: {host, generation, gpu_uuids}`, `retained_baseline_evidence`, `job_manifest`,
`baseline_manifest`, and `runner`.
They contain no incumbent-root binding. The candidate root must be absolute, canonical, non-reparse and
outside protected directories; exact direct `<candidate-root>/tooling` remains supported. Evidence must be
outside the repository. The controller reservation stays held after the driver exits; only the lead returns it.
Candidate descendants are checked without following symlinks, junctions or other reparse points before
install/setup and command execution; a nested runtime/model alias is not isolation. A prepared conversion
receipt must match the pinned converter digest and tensor-manifest digest as well as its inputs and outputs.
Candidate admission binds the exact idle generation and rechecks it under the installer's root lock, held
through every installation effect. The same fence continues through key creation and start, including a
competing generation that has already stopped. Candidate path components are pinned before the lock is
opened: Windows directory handles refuse deletion/replacement and never follow reparse targets.
The staging disk floor is checked before prefetch/preparation, subtracting already verified checkpoint files;
it is not reapplied as a steady-state workload floor. Candidate guards propagate one remaining deadline
through exact-job observation and authenticated HTTP probes; a late response is failure, not success.
Work-cutoff commands retain their jobs for root-fenced cleanup with the reserved pre-termination proof budget.
An installer must be terminated/proved under that directory fence before cleanup waits on the lifecycle lock
the installer owns. Pending launches still require lifecycle-locked cancellation before their termination.
Both the actual cleanup slice and the wall-clock return deadline are enforced after proof. Candidate generation
is checked again after authenticated probes and after each runner result before any attempt is counted.

#### Frozen workload runner and retained pairing

The default inventory is the full retained **80 jobs**: 14 WO2 jobs × two attempts, six G24 jobs × three,
and 60 golden-1 jobs × one, for **106 planned attempts per arm**. The original job manifest and retained
comparison digests must match. Do not substitute historical WO2 outputs for the retained incumbent rows.
The driver runs every selected candidate attempt once; it does not rerun the incumbent or retry ambiguous work.
The frozen runner is an operator-reviewed Python workload adapter, not a new lifecycle controller.
It is required at planning and execution; missing runner bytes refuse rather than simulate results.
At entry the driver captures the entire frozen Python harness, profiles, schemas, locks and private runner
into a unique per-window copy. Windows read handles deny file writes/deletion throughout execution.
The driver itself re-enters from that copy under isolated Python; CLI/serve commands and runner imports use
only the snapshot and pinned interpreter/standard library, not checkout paths, PYTHONPATH or site hooks.
The `harness_snapshot` receipt records every copied file's digest. Each attempt additionally transports the
runner's copied source through an anonymous input handle. The runner is self-contained: private sibling
imports or path injection outside the frozen harness are not supported. Standard input carries source, not
interactive workload input. These controls bind trusted reviewed code, not an adversarial-code sandbox.
The bootstrap alone owns an outer non-breakaway kill-on-close job containing the frozen worker and all
nested candidate jobs: bootstrap death cannot leave an executing worker behind after the snapshot seals close.
Input/root/window/held-lock preflight precedes snapshot materialization; each snapshot path is unique and
closed worker refusal reasons are preserved rather than replaced with a generic worker failure.
The golden-1 macOS `eval_taskset` client stays external, invoked by this runner using the same frozen manifest.
Its arm must target the already-running candidate only, with no activate/restore lifecycle command.

For each attempt the driver invokes the exact digest-bound runner with:
`--job-manifest PATH --job-manifest-sha256 SHA --family FAMILY --job ID --attempt N --timeout SECONDS
--profile PATH --root CANDIDATE_ROOT`. The runner must verify all referenced workload/expected/verifier files
against the original manifest, preserve request bytes except the pinned candidate model identifier, and apply
the original family budgets within the supplied remaining timeout. For golden-1 it must verify the frozen files
on the client, bound its external attempt to that timeout, wait for client/verification completion and confirm
no external client remains before returning. It has no incumbent or controller mutation authority.
Its final stdout JSON binds `family`, `job`, `attempt`, `job_manifest_sha256`, `status` (`complete` or `failed`),
boolean `passed` and `external_clients_stopped: true`; family-native metrics, failure/verifier details and
private primary-evidence references remain in that result. Malformed, unbound or missing results fail closed.
All host-local runner descendants are inside the driver's command job; nonzero command exit aborts the trial.

A lead-selected subset is explicit at planning: `--job-subset <JSON-list-of-family/job-ids>`.
The frozen `job_subset` and its digest are emitted in the receipt; absent selection means the full inventory.
The paired table always retains every original job and planned denominator, including failures, interruptions,
unselected and unscheduled work. Attempts are persisted **before** guard/runner effects; an interrupted attempt
is not reported as complete. Incumbent cells are deep copies of retained rows marked `retained` with the source
digest; a missing source row is `null`/`unavailable`, never a synthesized measurement.
Cold-load/replay and runner overhead are explicit. Earlier-window incumbent timing is not contemporaneous
candidate timing, WO2 shape checks are not semantic acceptance, and perf/quality alone never promotes a route.
The result remains comparison-only and recommends `hold` pending the owner's evidence-based decision.

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
  PID keeps them off the same attempt. Each worker also holds a lock per GPU host it uses (in the system temporary
  directory), so no two runs share or switch one host's engines; a worker whose host is locked stops without
  claiming anything. A claim or lock whose process is gone is taken over unless it carries an experiment's
  explicit failed-restoration hold, which always requires operator reconciliation.
- A `kind: "fleet"` arm runs a lead model with stock subagents on other hosts, as a fleet route would: it names a
  `lead` and `agents` (each a single arm at one of its placements). Every bundled agent type the arm lists
  (`task`, `sonic`, `scout`, `reviewer`, `security-reviewer` in OMP 18.5.0) goes to its model through
  `task.agentModelOverrides`; `sonic` and `scout` otherwise follow the lead's `smol` role. The lead also gets
  the `task` and `wait` tools: subagents run in the background, and print mode ends with the lead's turn unless
  it can block on their results. With stock prompts a lead may never delegate. An arm's `append_system_prompt`
  passes an instruction through OMP's `--append-system-prompt` on every task, and its `prompt_suffix` appends the
  owner's own words to every task's request (for example, asking the lead to use its subagents). The lead's
  event stream also carries every running subagent's progress snapshots, which grow with that subagent's
  transcript, so a fleet attempt's output cap is 1 GiB rather than 64 MiB, and the stored transcript drops those
  snapshots afterwards (tool results and the subagents' own sessions keep their content).
- `summarize --out <dir>` reports pass rates per arm, track and family, paired outcomes with an exact McNemar
  p-value, agent wall time and output tokens.

The arms file is private (host aliases, roots, key paths). `agent_env` carries tool settings the offline sandbox
needs; pnpm 11+ only reads its own settings from `pnpm_config_*` variables, and without
`pnpm_config_verify_deps_before_run=false` it re-verifies the lockfile over the network before every script.

A single arm is stock Strata (`api: openai-completions`, the model from its profile), NInfer's Responses
provider (`api: openai-responses` with `provider`, `model` and `key_env`), or another stock OpenAI-compatible
chat server such as llama.cpp or TabbyAPI (`api: openai-completions` with `provider`, `model` and `key_env`). The
last takes Strata's provider shape with the served model id, and its `model_entry` overrides the context window,
output limit and the reasoning and compatibility flags that server supports. Such arms are comparison-only like
the rest of this tool: the server's install, start and stop belong to the placement's `activate` script, and
nothing here changes `launch-omp` routing.

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

### Stock batch slots and printed recommendations as a variant

Two more stock setup choices stay off unless a profile pins them. `setup.py --parallel N` writes the config's
`"parallel": N`, and the server then runs up to N requests together in the engine's batch slots (`--batch N`;
stock docs/BATCHING.md). A request alone keeps the fastest single-request path, and every slot's tokens equal its
solo run. After writing the config, setup prints host recommendations as engine flags to add to its args. With 96 GB
of RAM or more it names `--prefill auto:32768`; with 24 GB to spare beside the model it names
`--conversation-cache-mib 8192`, which parks up to four conversations (stock default slots) in host RAM.
Draft both from a profile's tuple:

```sh
python3 scripts/upstream_watch.py draft --from profiles/<predecessor>.json --strata-tag <tag> --omp-tag <tag> \
  --id <new id> --strata-src "$STRATA_SRC" --ram-gib <host RAM> --parallel <N> --stock-tips
```

The planner evaluates stock's own `--parallel` branch and `bench_tips`, each as its reviewed body. A slot count that
stock warns about for the planned card (more than its recommendation, or any count where it recommends one at a
time) is refused. The first `--stock-tips` opt-in pins the printed flags in `strata.stock_tips` and raises the RAM
floors to what those tips assume. Later drafts keep exactly the predecessor's selected tip subset; newly printed
tips are not added, even with `--stock-tips`. A pinned tip that stock no longer prints is dropped and named in the
draft output's `dropped_stock_tips`; the setup-derived RAM floors follow the retained subset, while established
predecessor floors are never lowered. Install passes `--parallel N` to stock setup and adds the pinned flags
with stock `write_config`. The generated-config check refuses a different `"parallel"` or tip value. Slots set OMP's
`providers.maxInFlightRequests` for that server to N (otherwise 1). G14 fills every slot before it queues and drops
a request. G19 runs both first turns at once and checks that a conversation interleaved with another comes back from
its kept state instead of being read again.

### Stock pipeline windows on a layer split

Stock `--pipeline-windows 2` gives each layer-split stage a second verifier, letting the first card start a
guessed next verify window while later cards finish the current one, including decode (stock
`docs/MULTI_GPU.md`). It keeps extra VRAM out of the expert caches for those verifiers and recurrent-state snapshots.
Only a multi-card profile with `layer_split: auto` may pin `strata.pipeline_windows: 2`; batch slots
(`setup_args.parallel >= 2`) are refused. Add `--pipeline-windows 2` to the multi-GPU draft command below;
later drafts carry the pin forward, with the flag in `expected_engine_flags` only when the field is set.

After stock setup, calibration and tips, install adds or replaces the flag through the root's venv and stock
`write_config`. Generated-config verification requires `--pipeline-windows 2` exactly once. After readiness,
start requires stock's `two verifiers per stage` ON line with its `(decode too; ...)` suffix in this start's
engine-log interval, and records that line in `run.json`. An `is off: <reason>` line, a prefill-only ON line or
an absent ON line stops what this start launched and fails it. This also catches stock's runtime refusals, such as
no MTP draft layer or helper caches. Profiles without the field get no new start check. Stock v0.1.42 setup does not
add `--remote-expert-opt` to an existing config with nonzero pipeline windows (#1352).

The [RTX 4090 + RTX 3090 measurement](MEASUREMENTS.md#rtx-4090--rtx-3090-layer-split-2026-10-10-stock-strata-v0142-stock-omp-1889)
found decode +9-13%, prefill unchanged. The pipeline-windows profile is now
[qualified](MEASUREMENTS.md#rtx-4090--rtx-3090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889), with every
measured gate passing on its first run.

### Stock PLE direct reads

Engine 0.1.52 introduced automatic RAM residency for the PLE table. A profile may instead pin
`strata.ple_io: "direct"` to keep the table on direct SSD reads with stock `--ple-io direct`, leaving that RAM
available for the engine's automatic conversation cache and other allocations. This does not pin the cache's
capacity. Use the engine flag, not `STRATA_PLE_AUTO_RAM`: launch strips inherited `STRATA_*` variables, and
multi-GPU profiles refuse `env` overrides.

The field accepts exactly `"direct"`, on any card count, with **engine** 0.1.52 or newer (component engine
versions are independent of the Strata app tag). It requires `--ple-io` and `direct` as two separate elements,
exactly once in `strata.expected_engine_flags`. Without the field, `--ple-io direct` is refused; stock setup's
`--ple-io ram` remains legal. This is neither a stock setup tip nor a calibration setting.

Add `--ple-io direct` to `scripts/upstream_watch.py draft`; later drafts, including same-tuple calibration
drafts, carry the pin forward without repeating the option. Like every changed setting, it needs a new profile
id, integration root and release ledger; ids allow 3-120 lowercase letters, digits, dots and dashes. After stock
setup, calibration, tips and pipeline windows, install replaces any stock PLE mode or appends the flag through
the root's venv and stock `write_config`, restamping `args_written` when present. Generated-config verification
requires the pinned value exactly once.

After readiness, start refuses a `--ple-io <mode> chosen by the residency policy` line whose mode is not
`direct`, using only this start's engine-log interval; refusal stops what this start launched. It records the
last matched `PLE direct read probe: N rows/s (word)` text, or `null` when absent, under
`run.json`'s `ple_io.direct_read_probe`, alongside `ple_io.engine_log_interval`. Surrounding log text is not
copied. There is no required positive log line: on engine 0.1.52 the pair's forced-direct starts log
`PLE direct read probe: N rows/s (fine)` and no residency-policy line (2026-10-28). Profiles without the field get no
PLE start check.

The pair campaign lists the `roles-pledirect-parking` family beside the plain and `roles` families. A blocked row
goes `queued` → `running` → `qualified`. The v0.2.7 roles row was qualified before its profile was held (#67), and a
qualified row takes no other transition, so one more `qualified` with the direct-read variant's ready manifest
verifies that manifest and renames the row to the variant. Do it before the campaign's last open row qualifies: a
complete campaign is immutable (on 2026-10-28 the rename ran first, then the RTX 5090 262K row completed v0.2.7):

```sh
python3 scripts/campaign.py set-host --release v0.2.7 --profile "$PREPARED_PAIR_ID" --status qualified \
  --result "releases/$PLE_DIRECT_ID/manifest.json" --restored-state "$RESTORED_STATE_REF"
```

### Several GPUs: stock layer split as a profile

Stock setup offers NVIDIA cards together when they fit (`together_ok`) and writes the config's `"gpu": [i, j]` with
`"layer_split": "auto"` (stock docs/MULTI_GPU.md). A profile pins that choice as `host.gpus`, one entry per card in
stock setup's order (`gpu_index`, `gpu_model`, `arch`, `pci_bus_id`, `min_gpu_vram_mib`, `display_attached`), plus
`strata.setup_args.gpus` and `"layer_split": "auto"`, in place of the single-card fields. From Strata v0.2.3, two
stock opt-ins may each be pinned by a profile of its own: Main/Helper roles (`setup_args.gpu_roles`, cards ordered
Helpers by number, then Main, with stock's `gpu_order: "as_given"`), or one manual split point for two cards
(`"layer_split": "N"`, never with roles). Any other card order, replicas, helper expert caches, reserve overrides and
`STRATA_ARENA_PIN_GIB` stay off: each would be a profile change of its own.

1. Inventory the host. The command is read-only, needs no idle GPU, writes nothing and never asks for UUIDs or
   serials; keep its output private:

   ```bat
   python scripts\gpu_inventory.py > <private>\inventory.json
   ```

   `display_attached` is nvidia-smi's physical connection (a monitor on the card). `display_active` is advisory only:
   WDDM reports it `Disabled` even on the card that draws the desktop. Adding a card can renumber the others, because
   nvidia-smi numbers cards by PCI bus. A single-card profile's `gpu_index` then names a different card, and its
   `doctor` fails until a new profile pins the new numbering.

2. Draft with stock's own selection and order:

   ```sh
   python3 scripts/upstream_watch.py draft --from profiles/<predecessor>.json --strata-tag <tag> --omp-tag <tag> \
     --id <new id> --strata-src "$STRATA_SRC" --ram-gib <host RAM> --gpu-inventory <inventory.json> --gpus all
   ```

   The planner runs stock's reviewed `gpu_rank`, `gpu_problem` and `together_ok` (newest architecture first, then
   VRAM, then index) and refuses an explicit `--gpus` list in any other order. Replace `--gpus` with
   `--gpu-roles 0=main,1=helper` for stock roles, or add `--layer-split N` to `--gpus` for a manual split. RAM
   floors keep the predecessor's maxima and add a calculated reservation for each extra streamed session; the expert
   arena counts once. G21 measures the real use.

3. Install, start and qualify as usual. Install passes stock setup `--gpus i,j --layer-split <auto|N>`, or
   `--gpu-roles i=helper,j=main --layer-split auto` for roles, and refuses a generated config without the ordered
   `gpu` list, `gpus_asked`, the pinned `layer_split`, or the pinned roles with `gpu_order`. Setup and the server
   start without inherited `STRATA_*` tuning variables, `CUDA_VISIBLE_DEVICES` or `CUDA_DEVICE_ORDER`. The server
   decides which card runs which stage: with `"layer_split": "auto"` it moves the faster card last, unless the cards
   score within 5% of each other or the faster card has less total VRAM than the configured last card (#1576). Roles
   and a manual split keep the configured order. The server log gets a `[strata] layer split: ...` line whenever it
   changes the order or keeps it for that VRAM reason; the engine's own log (the generated config's `log` file) gets
   one `layer split: CUDA<n> runs layers a-b` line per stage. `start` records the observed order in `run.json`
   (`gpu_stage_order`), complete only when this start's server and engine log intervals agree on every stage, and,
   for a manual split, the second stage starts at layer N. Anything missing, partial or contradictory is
   recorded as unavailable: the order is never assumed, and it is never written back into the profile.

`doctor`, `start` and G10 check every card: model, architecture, PCI bus id, VRAM, driver, the physical display
attachment and the idle policy, with graphics clients tolerated only on the display-attached card. G10, G20 and G21
each publish one resource record covering every card, and `verify_release` requires it before a multi-card gate can
pass; an unreadable gate result leaves G21's record incomplete. G21 samples memory only: WDDM reports no per-process
VRAM, so a foreign process that comes and goes during G21 shows only as a higher peak, while `start` and G10 refuse
any foreign compute process present at launch. Single-card profiles keep their previous checks. G25 compares
single-GPU profiles only and refuses a multi-card one.

#### Combined stock calibration, slots and tips

One draft can combine all three opt-ins on the measured pair (no intermediate profile/install). For the Coder
IQ1_M pair on `rtx3090-win-a`, stop the installed server, then measure with its own pinned stock Python/module.
Run from the tooling checkout first; substitute private paths and the measurement date. The wrapper saves only
stock `calibrate.run`'s result as JSON, not its progress text, and does not modify the measured config:

```bat
python scripts\omp_strata.py stop --profile profiles\win11-rtx3090-rtx4090-coder-iq1m-131k-strata0.1.42-omp18.8.9.json --root <pair-root>
cd /d <pair-root>\runtime\strata
set "APPDATA=<pair-root>\appdata"
.venv\Scripts\python.exe -u -c "import json,sys; from pathlib import Path; from tools import calibrate; result=calibrate.run(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))); Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')" strata-coder-iq1_m.json <private>\pair-calibration.json
```

Keep the server stopped throughout calibration: it starts and restarts the engine itself. Stock v0.1.42
`calibrate.run` uses `serve.server.engine_args(cfg)`, including the layer split. Stock `calibrate.apply` changes
only `args`; `write_config` preserves `gpu`, `layer_split` and `parallel`. The draft pins all kept settings,
including the adaptive tier when stock selects it. On the drafting machine, with the private JSON and inventory:

```sh
python3 scripts/upstream_watch.py draft \
  --from profiles/win11-rtx3090-rtx4090-coder-iq1m-131k-strata0.1.42-omp18.8.9.json \
  --strata-tag v0.1.42 --omp-tag v18.8.9 --id win11-rtx3090-rtx4090-coder-iq1m-131k-calibrated-slots4-tips-strata0.1.42-omp18.8.9 \
  --strata-src "$STRATA_SRC" --ram-gib 127.68 --gpu-inventory <inventory.json> --gpus all \
  --calibration <pair-calibration.json> --calibration-host rtx3090-win-a --calibration-date <YYYY-MM-DD> \
  --parallel 4 --stock-tips
```

The planner checks the measured model, context and ordered cards before adding the opt-ins. It evaluates stock
`parallel_recommend` over **both** cards and refuses counts stock warns about. At 127.68 GiB host RAM, `bench_tips`
adds `--prefill auto:32768` and `--conversation-cache-mib 8192`; RAM floors rise by the same rules as single-card
tips. Calibration is measured on the predecessor, not a performance claim for the combined variant. If stock
keeps `{}` settings, omit the three calibration options: defaults already won; still draft the slots/tips variant.
For an IQ3_XXS or IQ3_S screen winner, use its pair profile, `strata-iq3_xxs.json` or `strata-iq3_s.json` during
measurement, and a matching new id; do not change the model while applying a calibration.

Transfer the draft tooling/profile to the host, then install from that checkout into a **new** root (leave the
measured root intact). Install applies calibration and then tips with stock helpers and checks every pinned flag:

```bat
python scripts\omp_strata.py install --profile profiles\win11-rtx3090-rtx4090-coder-iq1m-131k-calibrated-slots4-tips-strata0.1.42-omp18.8.9.json --root <new-root>
```
