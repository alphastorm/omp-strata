# Quickstart: stock OMP 18.4.0 on stock Strata v0.1.27 (Windows 11, RTX 5090)

Every command below was run as written on the qualification host (see `docs/MEASUREMENTS.md`, G26). The only
supported candidate is `profiles/win11-rtx5090-coder-iq1m-131k.json`; other GPUs, operating systems, models and
context sizes are unqualified.

## Requirements

- Windows 11 x64 with an NVIDIA RTX 5090 (32 GB, sm_120) that nothing else is using; tested driver 610.88.
- At least 45 GiB RAM with **34 GiB available when starting**, and a page file: the running engine holds about
  30 GB resident and commits about 63 GB (RAM + page file; the tested host has 47 GiB RAM and a 31 GB page file).
- About 75 GB free disk for the integration root (models 58.4 GB, Strata data 8.4 GB, runtime 1.1 GB).
- Python 3.13 via the `py` launcher, Git for Windows, and network access to GitHub and Hugging Face for the
  one-time download. Inference itself needs no network.

## Install and start

Run from a checkout of this repository (PowerShell). The integration root is dedicated to this tool; nothing is
written to `%APPDATA%\Strata` or to your normal OMP configuration.

```powershell
git clone https://github.com/alphastorm/omp-strata.git "$env:USERPROFILE\src\omp-strata"
Set-Location "$env:USERPROFILE\src\omp-strata"
$prof = "profiles\win11-rtx5090-coder-iq1m-131k.json"
$root = "$env:USERPROFILE\omp-strata"

py -3 scripts\omp_strata.py validate --profile $prof               # profile pins and budgets, no host access
py -3 scripts\omp_strata.py doctor   --profile $prof --root $root  # read-only host and install inspection
py -3 scripts\omp_strata.py fetch    --profile $prof --root $root  # ~60 GB, resumable, SHA-256 verified before use
py -3 scripts\omp_strata.py install  --profile $prof --root $root  # unmodified stock setup.py, local verified inputs
py -3 scripts\omp_strata.py keygen   --profile $prof --root $root  # private API key file, never printed
py -3 scripts\omp_strata.py start    --profile $prof --root $root  # 127.0.0.1:18090, key required, ~15 s to ready
py -3 scripts\omp_strata.py status   --profile $prof --root $root
```

`start` returns once authenticated identity checks pass (model id, 131,072-token context, `Strata 0.1.27`,
unauthenticated requests refused). It refuses to start when the port is taken by anything it does not own, when
the GPU is in use, or when less than 34 GiB RAM is available.

## Use OMP

`launch-omp` runs the pinned stock OMP binary with the isolated `omp-strata` profile: every model role pinned to
the local Strata model, extension/skill/rule discovery off, provider credentials scrubbed from the environment, and
the Strata key passed privately. Run it from the project you want to work on:

```powershell
Set-Location C:\path\to\your\project
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtx5090-coder-iq1m-131k.json" --root "$env:USERPROFILE\omp-strata"
```

Arguments after `--` go to OMP, for example a non-interactive turn:

```powershell
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtx5090-coder-iq1m-131k.json" --root "$env:USERPROFILE\omp-strata" -- -p --auto-approve "Run the tests and fix the failing one."
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
