# Quickstart: stock OMP 18.8.3 on stock Strata v0.1.40.3 (Windows 11, RTX PRO 6000)

G26 records the guarded install and launch example in a new integration root alongside earlier tuples, not on a
fresh OS (see [the measurements](MEASUREMENTS.md)). The current qualified profile is
`profiles/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3.json`: Qwen3.8-Flash-Next IQ3_S at a
131,072-token context with every expert in VRAM, plus four batch slots, conversation parking and 32K prompt chunks,
as stock setup offers them for this host. Its qualified rollback is
`profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json`, without those three choices; earlier tuples keep
their own roots and ledgers as rollback installations. The fourth tuple (stock Strata v0.1.34 + stock OMP 18.4.10,
Coder IQ1_M) stays qualified on three more GPUs with its own profiles and budgets (below); the same commands work
with any of them. See [compatibility](COMPATIBILITY.md) for every profile. Other operating systems, models and
context sizes are unqualified.

## Requirements

- Windows 11 x64 with an NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB, sm_120) that no other program
  computes on; it may drive the display. Tested driver 616.92.
- At least 96 GiB RAM with **72 GiB available when starting**, and a page file: the running engine holds about
  64 GB resident and commits about 125 GB, including up to 8 GiB of parked conversations (RAM + page file; the
  tested host has 192 GB RAM and a 28 GB page file).
- About 96 GB free disk for the integration root (models 83.6 GB, Strata data 8.5 GB, runtime 1.2 GB, downloads
  0.9 GB); `doctor` wants 90 GiB free.
- Python 3.13 via the `py` launcher, Git for Windows, and network access to GitHub and Hugging Face for the
  one-time download. Inference itself needs no network.

The fourth tuple's qualified profiles (each root took 74-99 GB, and `doctor` wants 90 GiB free):

| Profile | GPU | RAM: total / available at start | Ready after `start` |
|---|---|---|---|
| `win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10` | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 63 GB) | about 15 s |
| `win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10` | RTX 3090, 24 GB | 60 / 34 GiB | 17-33 s |
| `win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10` | RTX 4090, 24 GB, stock low-RAM mode | 30 / 16 GiB | about 15 s |

## Install and start

Run from a checkout of this repository (PowerShell). The integration root is dedicated to this tool; nothing is
written to `%APPDATA%\Strata` or to your normal OMP configuration.

```powershell
git clone https://github.com/alphastorm/omp-strata.git "$env:USERPROFILE\src\omp-strata"
Set-Location "$env:USERPROFILE\src\omp-strata"
$prof = "profiles\win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3.json"
$root = "$env:USERPROFILE\omp-strata-0.1.40.3"   # one root per candidate; never reuse another candidate's root

py -3 scripts\omp_strata.py validate --profile $prof               # profile pins and budgets, no host access
py -3 scripts\omp_strata.py doctor   --profile $prof --root $root  # read-only host and install inspection
py -3 scripts\omp_strata.py fetch    --profile $prof --root $root  # ~85 GB, resumable, SHA-256 verified before use
py -3 scripts\omp_strata.py install  --profile $prof --root $root  # unmodified stock setup.py, local verified inputs
py -3 scripts\omp_strata.py keygen   --profile $prof --root $root  # private API key file, never printed
py -3 scripts\omp_strata.py start    --profile $prof --root $root  # 127.0.0.1:18090, key required, ~19 s to ready
py -3 scripts\omp_strata.py status   --profile $prof --root $root
```

The first `install` took about 10 minutes on the tested host, most of it in stock setup. `start` returns once
authenticated identity checks pass (model id, 131,072-token context, `Strata 0.1.40.3`, unauthenticated requests
refused). It refuses to start when the port is taken by anything it does not own, when another program uses the
GPU (a display is allowed), or when less than 72 GiB RAM is available.

## Use OMP

`launch-omp` runs the pinned stock OMP binary with the isolated `omp-strata` profile: every model role pinned to
the local Strata model, up to four requests at once (the server's batch slots), extension/skill/rule discovery off,
speculative compaction off, provider credentials scrubbed from the environment, and the Strata key passed privately.
Run it from the project you want to work on:

```powershell
Set-Location C:\path\to\your\project
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3.json" --root "$env:USERPROFILE\omp-strata-0.1.40.3"
```

Arguments after `--` go to OMP, for example a non-interactive turn:

```powershell
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3.json" --root "$env:USERPROFILE\omp-strata-0.1.40.3" -- -p --auto-approve "Run the tests and fix the failing one."
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
