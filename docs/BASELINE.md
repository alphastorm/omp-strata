# Baseline and frozen candidate tuple

Recorded 2026-09-30 (UTC) at the start of implementation. Source packet: `docs/handoff/2026-09-30/`
(its `SHA256SUMS` verifies). This file records decisions and where every expected digest came from; the
machine-readable pins live in `profiles/win11-rtx5090-coder-iq1m-131k.json`.

## Repository state at start

- `alphastorm/omp-strata`: public, empty (no commits), default-branch metadata `master`. Work is committed locally
  on `master`; nothing is pushed, tagged or released by this work.
- The handoff packet was moved to `docs/handoff/2026-09-30/`. Before publication, two `HANDOFF.md` lines were
  redacted in place (the owner's name and a private host-inventory reference) and `SHA256SUMS` was regenerated;
  everything else is verbatim. `AGENTS.md` carries its binding decisions.

## Source refresh (handoff §1 rule)

| Component | Handoff candidate | Observed 2026-09-30 | Decision |
|---|---|---|---|
| OMP | v18.4.0 `401778d0…` | stock releases v18.4.1–v18.4.4 exist | **Keep v18.4.0.** No concrete blocker found in 18.4.0 for this route; findings below are recorded against 18.4.0. |
| Strata | `main` @ `a790805…` | tag **v0.1.27** is exactly `a790805…`; `main` unchanged | **Keep**, now identified as the v0.1.27 release. |
| NInfer reference | v0.8.7 | v0.9.0 exists | Read-only pattern reference only; no NInfer receipts are reused. |

## Frozen tuple (profile `win11-rtx5090-coder-iq1m-131k`)

| Component | Identity | Digest source |
|---|---|---|
| OMP client | `omp-windows-x64.exe` v18.4.0, 239,441,408 B, sha256 `5e8637d7…ea95fe` (also darwin-arm64 / linux-x64 pinned for host-free tests) | GitHub release-asset digest; matches omp-ninfer v0.9.0 pins |
| Strata source | `Niko1221/Strata` v0.1.27 = `a79080535d1b2a71a3419a0d97d8e7dca194b0f1`, fetched by commit with `core.autocrlf=false` | Git object identity |
| Strata engine | `strata-windows-x64.zip` v0.1.27, 105,556,365 B, sha256 `cbb44dd8…00b839` (engine 0.1.27, CUDA 13.0, sm_75/86/89/120) | GitHub release-asset digest. **Limitation:** maintainer-uploaded asset, no build attestation; not rebuilt from source here. |
| llama.cpp (gguf-py for setup tools) | `3cf03257…` archive, 39,564,399 B, sha256 `cbe23c59…21ea47b` | First-download observation, reproduced once (upstream publishes no digest) |
| Model | `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` @ `5348543e…`: IQ1_M shard 1 29,608,446,496 B `e11083ba…`, shard 2 28,800,138,432 B `316b46f3…` (Apache-2.0) | Hugging Face LFS object ids at the pinned revision |
| MTP draft layer | tensors of `Qwen/Qwen3.8-Flash-Next` @ `de4b8e4d…` fetched by stock `tools/mtp_fetch.py` with its base URL pinned to that revision | Per-tensor SHA-256 recorded by the stock tool; manifest digest pinned after first install |
| Python packages | 19 wheels for stock `setup.py` `PY_PACKAGES` + `CUDA_WHEELS`, `locks/strata-python-cp313-win_amd64.txt` | Hash lock resolved once on the target (cp313, win_amd64); installed with `--require-hashes --no-index` |

Stock `setup.py` would otherwise fetch the engine from `releases/latest`, the model and MTP tensors from `main`, and
unpinned PyPI versions, and it records installs in `%APPDATA%\Strata`. The installer (`omp_strata/install.py`)
runs the unmodified `setup.py` only after every such input is local and verified, with APPDATA redirected into the
integration root. `START-HERE.bat`/`setup.sh` are never used.

## Model and profile choice

- **Coder IQ1_M instead of the handoff's default original IQ2_XS.** The selected host has 47 GiB RAM. Stock setup
  keeps all experts pinned in RAM and switches to low-RAM mode when RAM < experts + 10 GB: IQ2_XS needs
  35.5 + 10 GB, the Coder 23.4 + 10 GB. With the GPU's usual co-tenants paused, the host has well under 45.5 GB
  free, so IQ2_XS would silently become a low-RAM (mmap) profile. The workload is coding, and the Coder's authors
  report 91% of the full model's SWE-bench Verified. Limitation: expert-pruned (256 of 512 experts per layer),
  weaker outside coding; results say nothing about the original model.
- **Context 131,072** with stock setup's defaults for that size: INT8 KV, KV streaming (`--kv-resident 32768`),
  `--expert-cache auto`, `--prefill auto`, MTP `--spec 4 --spec-min-p 0.5`. Low-RAM mode explicitly **off**;
  vision, experimental speed projection, calibration and Strata-side MCP **off**. A smaller context would be a
  new profile id, never an in-place downgrade.
- OMP output cap 32,768 tokens; Strata refuses (HTTP 400) any request whose prompt + `max_tokens` exceeds the
  context (`fit_max_tokens` stays off), so capacity is tested explicitly in G17.

## Host route

One native Windows 11 host (public label **rtx5090-win-a**): RTX 5090 32 GB (sm_120), driver 610.88, 47 GiB RAM,
16-core AVX-512 CPU, NVMe with >600 GiB free, Python 3.13 via the `py` launcher, Git for Windows. It normally
serves another local runtime; the owner authorized exclusive use of the fleet for this work. The GPU window is
taken by pausing that runtime's supervisors and stopping its container, and released by restarting the same
container and verifying its identity and health (private operator tooling, not part of this repository).
macOS is used only as the host-free development/CI client; no macOS Strata runtime is implied.

## Findings recorded at baseline

- Strata disables authentication entirely when its key is empty and compares keys with `==`; `/health`, `/status`,
  `/` and static assets are always unauthenticated. The launcher refuses to start without a ≥32-character key.
- Strata accepts any `model` string on completions; identity is proven by the controlled launch, `/props`
  (`n_ctx`, `build_info`, `model_path`) and the install record, not by the model name.
- Strata ignores `tool_choice`, `parallel_tool_calls`, `stop` and `stream_options`; usage is always sent in the
  final chunk with `prompt_tokens_details.cached_tokens` (the engine's reused prefix) and llama.cpp-style `timings`.
- Stock OMP 18.4.0 behaviour is recorded from the real binary in `tests/mock/` findings (see `docs/MEASUREMENTS.md`),
  not from source reading alone.
