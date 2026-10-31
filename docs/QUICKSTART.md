# Quickstart

Stock Oh My Pi (OMP) 18.14.0 runs against a local stock Strata v0.2.8 server. Pick the profile for your host; the same
commands work with any of them, and every profile keeps its own integration root and ledger.

| Host | Current qualified profile | Qualified rollback |
|---|---|---|
| RTX PRO 6000 (**default**) | `profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0.json`: stock Strata v0.2.8 (engine 0.1.54), Qwen3.8-Flash-Next IQ3_S at the model's trained 262,144-token context with every expert in VRAM, four batch slots with per-slot multi-token prediction (MTP, `--batch-mtp`, `strata.batch_mtp: true`), direct per-layer embedding (PLE) reads (`--ple-io direct`, `strata.ple_io: "direct"`), conversation parking (the engine's 8,192 MiB cache) and 32K prompt chunks | `profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0.json`: the initial v0.2.8 + OMP 18.14.0 PRO profile without `--batch-mtp` or `--ple-io direct` (its root stays installed) |
| RTX PRO 6000 (qualified alternative) | `profiles/win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0.json`: stock Strata v0.2.8 (engine 0.1.54), the same 262,144-token IQ3_S choices with direct PLE reads (`--ple-io direct`), without `--batch-mtp` | `profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0.json` |
| RTX 5090 (**default**) | `profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0.json`: stock Strata v0.2.8 (engine 0.1.54), Coder IQ1_M at 262,144 tokens (36 GiB available-RAM start floor; requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script and re-registered with the owner's fleet controller) | `profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2.json` |
| RTX 5090 (qualified alternative) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0.json`: stock Strata v0.2.8 (engine 0.1.54), Coder IQ1_M at 131,072 tokens (34 GiB available-RAM start floor; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; qualified, no longer the default) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2.json` |
| RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) | `profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0.json`: stock Strata v0.2.8 (engine 0.1.54) + OMP 18.14.0, IQ3_S at 262,144 tokens across both cards, stock roles (`--gpu-roles 0=main,1=helper`, RTX 4090 as Main staged last), manual layer split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, `strata.trim_stage_weights: true`), pipeline windows 2, no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`, `strata.ple_io: "direct"`), engine's 8,192 MiB automatic conversation cache | `profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0.json`: the initial v0.2.8 + OMP 18.14.0 PLE-direct roles profile (automatic split without stage weight trim) |

- On the RTX PRO 6000 (`rtxpro6000-win-a`), `strata.ple_io: "direct"` (`--ple-io direct`,
  [OPERATIONS.md](OPERATIONS.md#stock-ple-direct-reads)) reads the 26.8 GiB PLE table from the model file on SSD
  instead of locking it in RAM at start (cutting restart readiness from 73.6-88.2 s on the `slots4-parking` rollback
  to 35.5-51.5 s on the current profile and 35.0-51.4 s on the PLE-direct alternative, and raising G10 Windows commit
  headroom from 55.4 GiB to 81.3 GiB and 82.8-82.9 GiB of a 219.7 GiB limit), while `strata.batch_mtp: true`
  (`--batch-mtp`, [OPERATIONS.md](OPERATIONS.md#stock-per-slot-mtp)) gives each of the four batch slots its own MTP
  drafter state (+22.5% total output at two concurrent requests, +8% at four 2K requests, +40% summed decode at four
  40K prompts).
- On the pair, pinning manual `strata.setup_args.layer_split: "24"` (the layer the automatic planner chose) and
  `strata.trim_stage_weights: true` (`--trim-stage-weights`, [OPERATIONS.md](OPERATIONS.md#stock-stage-weight-trim))
  loads only each card's own stage dense weights, growing each card's expert cache by 1.8 GiB (19.15 GiB on the RTX
  3090 and 17.76 GiB on the RTX 4090 vs 17.35 and 16.01 GiB on the `roles-pledirect` rollback) and cutting 32K-100K
  time to first token 12%, while `strata.ple_io: "direct"` (`--ple-io direct`) keeps the 26.8 GiB PLE table on
  direct SSD reads so the engine's 8,192 MiB automatic conversation cache stays enabled and G10 serving Windows
  commit headroom is 27.8 GiB of a 135.7 GiB limit (27.9 GiB on the `roles-pledirect` rollback). The
  measurement-only v0.2.8 stock-residency roles draft
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0.json`), the held v0.2.7
  roles draft (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2.json`,
  PLE in RAM, cache off, 1.03 GiB commit headroom; [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)),
  the unmeasured v0.2.7 default-split draft, the default and split-32 v0.2.3 drafts and the v0.1.44.1 pair release
  remain draft, not qualified ([decision](DECISION.md)).
- On the RTX 5090 (`rtx5090-win-a`), `profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0.json` is the
  default (owner decision 2026-10-30), with a 36 GiB available-RAM start floor and a 3,584 MiB automatic conversation
  cache (rolling back to `profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2.json`). Operating condition:
  the host's Docker Desktop and WSL, which run its production NInfer container, must be stopped; after WSL restarts,
  that container must be recreated by the owner's pinned relaunch script and re-registered with the owner's fleet
  controller. The 131K profile (`profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0.json`, rolling back to
  `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2.json`; 34 GiB start floor) is the qualified
  alternative for running with Docker Desktop and WSL up (the production container stopped by the fleet controller).
- Display placement is part of the pair's profile: the earlier `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9`
  requires moving the display back to the RTX 3090.
- Single-card RTX 3090 profiles are not rollbacks while both cards are installed: they name GPU 0, now the RTX 4090.
  The Coder IQ1_M profile on v0.1.40.3 with OMP 18.8.4 stays qualified for single-card RTX 3090 hosts, and the fourth
  tuple's profiles (stock Strata v0.1.34 + stock OMP 18.4.10) remain qualified single-card rollbacks and stay
  qualified on the single-card RTX 4090.
- [Compatibility](COMPATIBILITY.md) lists every profile. Other operating systems, models and context sizes are
  unqualified.

<details>
<summary>Earlier qualified tuples and profile lineage</summary>

- **RTX PRO 6000:** earlier qualified history starts with the 262K `slots4-parking` choices on v0.2.7 + OMP 18.13.2,
  then v0.2.3 + OMP 18.12.6, then v0.2.1,
  v0.1.44.1, v0.1.43.1 and v0.1.43 with OMP 18.10.1, v0.1.42 with OMP 18.8.9, then v0.1.41 with OMP 18.8.6 at 262K and
  131K, then stock Strata v0.1.40.3 with OMP 18.8.4, then OMP 18.8.3, and before them
  `profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json`, without those three choices.
- **RTX 5090:** v0.2.3 + OMP 18.12.6 (131K and 262K), v0.2.1 + OMP 18.10.1 (131K and 262K; host integration roots
  removed on 2026-10-28), v0.1.44.1 + OMP 18.10.1 (131K and 262K), v0.1.43.1 + OMP 18.10.1, v0.1.43 + OMP 18.10.1,
  v0.1.42 + OMP 18.8.9, v0.1.41 + OMP 18.8.6 and v0.1.40.3 + OMP 18.8.4 are retained as earlier qualified history.
- **RTX 4090 + RTX 3090 pair (`rtx3090-win-a`):** the v0.2.7 + OMP 18.13.2 PLE-direct stock-roles profile, the
  v0.2.3 + OMP 18.12.6 stock-roles profile, the v0.2.1 default-split
  profile (host root removed on 2026-10-28), the v0.1.43.1 and v0.1.43 262K parking profiles and the v0.1.42 262K
  parking and 131K display-on-RTX-4090 profiles stay earlier qualified history before
  `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` (display on the RTX 3090).

</details>

## Requirements

- Windows 11 x64 with an NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB, sm_120) that no other program
  computes on; it may drive the display. Tested driver 616.92.
- At least 96 GiB RAM with **74 GiB available when starting**, and a page file: the running engine holds about
  73.7 GB resident and commits about 136.6 GB on the current batch-MTP + PLE-direct profile (72.5 GB resident and
  135.1 GB committed on the PLE-direct alternative; 101.3 GB resident and 135.1 GB committed on the `slots4-parking`
  rollback where the 26.8 GiB PLE table is locked in RAM), including up to 8,192 MiB of parked conversations (RAM +
  page file).
- About 96.6 GB free disk for the integration root (the current PRO root measured 96.6 GB, 83.6 GB of it model
  shards); `doctor` wants 91 GiB free.
- Python 3.13 via the `py` launcher, Git for Windows, and network access to GitHub and Hugging Face for the
  one-time download. Inference itself needs no network.
- Measured install and start timings: G26 records the guarded install and launch example in a new integration root
  alongside earlier tuples, not on a fresh OS (see [the measurements](MEASUREMENTS.md)). On the current v0.2.8
  batch-MTP + PLE-direct profile, G26 ran in a new root (`install` 1,063.2 s, `start` 58.3 s); measured restarts took
  35.5-51.5 s (G16 51.4 s, G20 51.5 s, G21 35.5 s; 35.0-51.4 s on the PLE-direct alternative, G20 35.0 s; and
  73.6-88.2 s on the `slots4-parking` rollback).

The other qualified profiles (alongside the PRO's 96.6 GB roots, the RTX 5090 roots of Strata v0.2.8 + OMP 18.14.0
took 70.8 GB for the 262K default and 70.9 GB for the 131K alternative, the current display-on-RTX-4090 262K pair
split-24 trim + PLE-direct root and its `roles-pledirect` rollback each took 95.7 GB, the single-card RTX 3090 root of
v0.1.40.3 + OMP 18.8.4 took 69 GB, and the fourth tuple's low-RAM root 99 GB on the RTX 4090; `doctor` wants 91 GiB
free on the PRO and pair and 90 GiB on the RTX 5090 and earlier profiles):

| Profile | GPU | RAM: total / available at start | Ready after `start` |
|---|---|---|---|
| `win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0` (qualified alternative) | RTX PRO 6000, 96 GB | 96 / 74 GiB, plus a page file (82.8-82.9 GiB commit headroom of 219.7 GiB serving) | 35.0-51.4 s on measured restarts (G16 51.4 s, G20 35.0 s, G21 35.4 s); G26 start wall 56.8 s (install 20.7 s on an already prepared root; not a first-install timing) |
| `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0` | RTX 4090 + RTX 3090, 24 GB each, display on RTX 4090 | 86 / 78 GiB, plus a page file (27.8 GiB commit headroom of 135.7 GiB serving) | 43.1-44.2 s on measured restarts (G16 43.1 s, G20 44.2 s, G21 43.9 s, PLE on direct SSD reads); G26 start wall 59.0 s (install 820.3 s in a new root; `roles-pledirect` rollback: 43.7-44.4 s) |
| `win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0` (default) | RTX 5090, 32 GB | 45 / 36 GiB, plus a page file (the engine commits about 66.5 GB; requires Docker Desktop and WSL stopped on the host) | 17.1-28.3 s on measured restarts (G16 28.3 s); G26 start wall 38.4 s (install 365.6 s in a new root) |
| `win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0` (qualified alternative) | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 64.7 GB; starts with Docker Desktop and WSL running) | 16.6-27.2 s on measured restarts (G16 27.2 s); G26 start wall 38.5 s (install 297.8 s in a new root) |
| `win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` | RTX 3090, 24 GB | 60 / 34 GiB | 17-19 s |
| `win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10` (fourth tuple) | RTX 4090, 24 GB, stock low-RAM mode | 30 / 16 GiB | about 15 s |

## Install and start

Run from a checkout of this repository (PowerShell). The integration root is dedicated to this tool; nothing is
written to `%APPDATA%\Strata` or to your normal OMP configuration.

```powershell
git clone https://github.com/alphastorm/omp-strata.git "$env:USERPROFILE\src\omp-strata"
Set-Location "$env:USERPROFILE\src\omp-strata"
$prof = "profiles\win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0.json"
$root = "$env:USERPROFILE\omp-strata-0.2.8-omp18.14.0-batchmtp-262k"   # one root per candidate; never reuse another candidate's root

py -3 scripts\omp_strata.py validate --profile $prof               # profile pins and budgets, no host access
py -3 scripts\omp_strata.py doctor   --profile $prof --root $root  # read-only host and install inspection
py -3 scripts\omp_strata.py fetch    --profile $prof --root $root  # ~85 GB, resumable, SHA-256 verified before use
py -3 scripts\omp_strata.py install  --profile $prof --root $root  # unmodified stock setup.py, local verified inputs
py -3 scripts\omp_strata.py keygen   --profile $prof --root $root  # private API key file, never printed
py -3 scripts\omp_strata.py start    --profile $prof --root $root  # 127.0.0.1:18090, key required, ~35.5-51.5 s to ready on restarts (58.3 s in G26)
py -3 scripts\omp_strata.py status   --profile $prof --root $root
```

`start` returns once authenticated identity checks pass (model id, 262,144-token context, `Strata 0.1.54` — the
v0.2.8 engine component version, not `0.2.8` — and unauthenticated requests refused). It refuses to start when the
port is taken by anything it does not own, when another program uses the GPU (a display is allowed), or when less than
74 GiB RAM is available.

## Use OMP

`launch-omp` runs the pinned stock OMP binary with the isolated `omp-strata` profile: every model role pinned to
the local Strata model, up to four requests at once (the server's batch slots), extension/skill/rule discovery off,
speculative compaction off, provider credentials scrubbed from the environment, and the Strata key passed privately.
Run it from the project you want to work on:

```powershell
Set-Location C:\path\to\your\project
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0.json" --root "$env:USERPROFILE\omp-strata-0.2.8-omp18.14.0-batchmtp-262k"
```

Arguments after `--` go to OMP, for example a non-interactive turn:

```powershell
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0.json" --root "$env:USERPROFILE\omp-strata-0.2.8-omp18.14.0-batchmtp-262k" -- -p --auto-approve "Run the tests and fix the failing one."
```

Flags that would change the provider, model, profile, configuration or extension loading are refused.

## Stop

```powershell
py -3 scripts\omp_strata.py stop --profile $prof --root $root
```

`stop` terminates only processes whose PID, creation time and executable match what `start` recorded (the wrapper,
the server and everything currently beneath it, deepest first) and is safe to repeat. To remove the integration
completely, stop it and delete the integration root.

See `docs/OPERATIONS.md` for restarts, logs and failure handling, and `docs/SECURITY.md` for what is and is not
isolated.
