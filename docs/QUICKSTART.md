# Quickstart

Stock Oh My Pi (OMP) 18.12.6 runs against a local stock Strata server. Pick the profile for your host; the same
commands work with any of them, and every profile keeps its own integration root and ledger.

| Host | Current qualified profile | Qualified rollback |
|---|---|---|
| RTX PRO 6000 | `profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6.json`: stock Strata v0.2.3 (engine 0.1.48), Qwen3.8-Flash-Next IQ3_S at the model's trained 262,144-token context with every expert in VRAM, plus four batch slots, conversation parking (the engine's 8 GiB cache) and 32K prompt chunks | `profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1.json`: the same choices on stock Strata v0.2.1 (engine 0.1.46) with OMP 18.10.1 |
| RTX 5090 | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.3-omp18.12.6.json`: stock Strata v0.2.3 (engine 0.1.48), Coder IQ1_M at 131,072 tokens | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.1-omp18.10.1.json` |
| RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) | `profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6.json`: stock Strata v0.2.3 (engine 0.1.48), IQ3_S at 262,144 tokens across both cards, stock layer split with stock roles (`--gpu-roles 0=main,1=helper`, RTX 4090 as Main staged last), pipeline windows 2 and the engine's 8 GiB conversation cache, without batch slots, with the display on the RTX 4090 ([owner's decision](DECISION.md)) | `profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.1-omp18.10.1.json`: the default-split v0.2.1 + OMP 18.10.1 profile with the same display placement (the default and split-32 v0.2.3 drafts and the v0.1.44.1 pair release remain unqualified) |

- Opt-in on the RTX 5090: `profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6.json` runs the same Coder
  IQ1_M at 262,144 tokens with a 36 GiB available-RAM startup floor (rolling back to
  `profiles/win11-rtx5090-coder-iq1m-262k-strata0.2.1-omp18.10.1.json` or the 131K default); the 131K profile stays
  the default.
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

- **RTX PRO 6000:** earlier qualified history starts with the same 262K choices on v0.1.44.1, v0.1.43.1 and v0.1.43
  with OMP 18.10.1, v0.1.42 with OMP 18.8.9, then v0.1.41 with OMP 18.8.6 at 262K and 131K, then stock Strata
  v0.1.40.3 with OMP 18.8.4, then OMP 18.8.3, and before them
  `profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json`, without those three choices.
- **RTX 5090:** v0.1.44.1 + OMP 18.10.1 (131K default and 262K opt-in), v0.1.43.1 + OMP 18.10.1, v0.1.43 + OMP 18.10.1,
  v0.1.42 + OMP 18.8.9, v0.1.41 + OMP 18.8.6 and v0.1.40.3 + OMP 18.8.4 are retained as earlier qualified history.
- **RTX 4090 + RTX 3090 pair (`rtx3090-win-a`):** the v0.1.43.1 and v0.1.43 262K parking profiles and the v0.1.42 262K
  parking and 131K display-on-RTX-4090 profiles stay earlier qualified history before
  `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` (display on the RTX 3090).

</details>

## Requirements

- Windows 11 x64 with an NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB, sm_120) that no other program
  computes on; it may drive the display. Tested driver 616.92.
- At least 96 GiB RAM with **74 GiB available when starting**, and a page file: the running engine holds about
  72 GB resident and commits about 135 GB, including up to 8 GiB of parked conversations (RAM + page file; the
  tested host has 192 GB RAM and a 28 GB page file).
- About 96.4 GB free disk for the integration root (the current PRO root measured 96.4 GB, 83.6 GB of it model
  shards); `doctor` wants 91 GiB free.
- Python 3.13 via the `py` launcher, Git for Windows, and network access to GitHub and Hugging Face for the
  one-time download. Inference itself needs no network.
- Measured install and start timings: G26 records the guarded install and launch example in a new integration root
  alongside earlier tuples, not on a fresh OS (see [the measurements](MEASUREMENTS.md)). On the current v0.2.3
  profile, `install` took 740.1 s (engine component staging plus stock setup) and the first `start` took 47.7 s in a
  new root; measured restarts took 23.7-26.8 s.

The other qualified profiles (alongside the PRO's 96.4 GB root, the RTX 5090 roots of Strata v0.2.3 + OMP 18.12.6 took
70.6 GB, the single-card RTX 3090 root of v0.1.40.3 + OMP 18.8.4 took 69 GB, the current display-on-RTX-4090 262K pair
roles root 95.5 GB, and the fourth tuple's low-RAM root 99 GB on the RTX 4090; `doctor` wants 91 GiB free on the PRO
and pair and 90 GiB on the RTX 5090 and earlier profiles):

| Profile | GPU | RAM: total / available at start | Ready after `start` |
|---|---|---|---|
| `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.3-omp18.12.6` | RTX 4090 + RTX 3090, 24 GB each, display on RTX 4090 | 86 / 78 GiB | 55.7-56.2 s on measured restarts; G26 first-start wall 56.4 s (install 26.3 s on an already prepared root; not a first-install timing) |
| `win11-rtx5090-coder-iq1m-131k-strata0.2.3-omp18.12.6` | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 64 GB) | 17.0-23.0 s on measured restarts; first-start wall 38.1 s (install 308.0 s in a new root) |
| `win11-rtx5090-coder-iq1m-262k-strata0.2.3-omp18.12.6` (opt-in) | RTX 5090, 32 GB | 45 / 36 GiB, plus a page file | 19.0-23.0 s on measured restarts; first-start wall 39.2 s (install 331.2 s in a new root) |
| `win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` | RTX 3090, 24 GB | 60 / 34 GiB | 17-19 s |
| `win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10` (fourth tuple) | RTX 4090, 24 GB, stock low-RAM mode | 30 / 16 GiB | about 15 s |

## Install and start

Run from a checkout of this repository (PowerShell). The integration root is dedicated to this tool; nothing is
written to `%APPDATA%\Strata` or to your normal OMP configuration.

```powershell
git clone https://github.com/alphastorm/omp-strata.git "$env:USERPROFILE\src\omp-strata"
Set-Location "$env:USERPROFILE\src\omp-strata"
$prof = "profiles\win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6.json"
$root = "$env:USERPROFILE\omp-strata-0.2.3-omp18.12.6-262k"   # one root per candidate; never reuse another candidate's root

py -3 scripts\omp_strata.py validate --profile $prof               # profile pins and budgets, no host access
py -3 scripts\omp_strata.py doctor   --profile $prof --root $root  # read-only host and install inspection
py -3 scripts\omp_strata.py fetch    --profile $prof --root $root  # ~85 GB, resumable, SHA-256 verified before use
py -3 scripts\omp_strata.py install  --profile $prof --root $root  # unmodified stock setup.py, local verified inputs
py -3 scripts\omp_strata.py keygen   --profile $prof --root $root  # private API key file, never printed
py -3 scripts\omp_strata.py start    --profile $prof --root $root  # 127.0.0.1:18090, key required, ~24-27 s to ready
py -3 scripts\omp_strata.py status   --profile $prof --root $root
```

`start` returns once authenticated identity checks pass (model id, 262,144-token context, `Strata 0.1.48` — the
v0.2.3 engine component version, not `0.2.3` — and unauthenticated requests refused). It refuses to start when the
port is taken by anything it does not own, when another program uses the GPU (a display is allowed), or when less than
74 GiB RAM is available.

## Use OMP

`launch-omp` runs the pinned stock OMP binary with the isolated `omp-strata` profile: every model role pinned to
the local Strata model, up to four requests at once (the server's batch slots), extension/skill/rule discovery off,
speculative compaction off, provider credentials scrubbed from the environment, and the Strata key passed privately.
Run it from the project you want to work on:

```powershell
Set-Location C:\path\to\your\project
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6.json" --root "$env:USERPROFILE\omp-strata-0.2.3-omp18.12.6-262k"
```

Arguments after `--` go to OMP, for example a non-interactive turn:

```powershell
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6.json" --root "$env:USERPROFILE\omp-strata-0.2.3-omp18.12.6-262k" -- -p --auto-approve "Run the tests and fix the failing one."
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
