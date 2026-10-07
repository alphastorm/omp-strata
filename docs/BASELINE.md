# Baseline and frozen candidate tuples

Two candidates exist on the RTX 5090 host, plus a third stock tuple with draft profiles on two 24 GB hosts and a
fourth on all three hosts. The first candidate (2026-09-30) is kept as the rollback installation and its evidence
stands; the second (2026-10-01) moves both stock components to the releases that fix the first candidate's upstream
findings; the third tuple (2026-10-01) moves them again to the releases that carry Strata's half of the G04 fix;
the fourth (2026-10-02) to the first OMP release that carries the other half. The RTX PRO 6000 tuple (2026-10-07)
moves both to their newest stable releases on that host; the drafts between it and the fourth tuple are described in
[MEASUREMENTS.md](MEASUREMENTS.md). The RTX PRO 6000 slots4-parking tuple (the same day) moves both again and pins
stock setup's batch slots and printed host recommendations. Each section records decisions and where every expected
digest came from; the machine-readable pins live in `profiles/<profile_id>.json`.

## RTX PRO 6000 slots4-parking tuple (2026-10-07): Strata v0.1.40.3 + OMP 18.8.3

### Source refresh

| Component | Qualified PRO profile | Observed 2026-10-07 (UTC) | Decision |
|---|---|---|---|
| OMP | v18.8.0 `4ef97c88…` | v18.8.1 to v18.8.3 (`3e3c488a…`, released 18:47) | **Move to v18.8.3**, the newest stable release (the owner's rule for a qualification). 18.8.1-18.8.3 add a warning for unknown `models.yml` compat keys (the profile renders none), share lenient tool-argument validation across dispatch paths (G04's mock cuts still write nothing), keep metaharness services alive for the verifier, and otherwise change task account pools, catalogs, OAuth and the TUI. |
| Strata | v0.1.40.2 `e8ca9afd…` | v0.1.40.3 (`d5ea7133…`, released 18:01) | **Move to v0.1.40.3**, the newest stock release and a new engine build: the #1357 MTP router guard, plus HIP, runtime-DLL and Intel fixes outside this NVIDIA lane. |

The predecessor is the qualified `win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0`. Besides the two component pins,
this profile pins two stock setup choices measured on that installation (MEASUREMENTS.md):

- **Batch slots**, stock setup `--parallel 4`: stock's own recommendation for this card (each slot takes ~0.6 GB of
  VRAM from the expert cache, 2.3 GB in all). The server runs up to four requests together in the engine's batch
  slots, and a request alone keeps the single-request path. OMP's in-flight limit for the server is 4.
- **Stock setup's printed host recommendations**: `--conversation-cache-mib 8192` (24 GB to spare beside the model;
  parks up to four conversations, stock's default slot count) and `--prefill auto:32768` (96 GB of RAM or more).
  Install adds them with stock `write_config`. The RAM floors rise to what the recommendations assume: 96 GiB in
  all and 72 GiB available at start.

The model, engine flags otherwise, MTP source and llama.cpp commit are unchanged. The profile has its own root and
ledger and inherits nothing; the qualified v0.1.40.2 profile and its root stay as the rollback installation.

### Frozen tuple

| Component | Identity | Digest source |
|---|---|---|
| OMP client | `omp-windows-x64.exe` v18.8.3, 237,049,344 B, sha256 `fa722441…adb0e7` (darwin-arm64 212,403,488 B `4421538b…537b60`; linux-x64 283,428,320 B `8cb6d6a0…ccbc37`) | GitHub release-asset digests |
| Strata source | `Niko1221/Strata` v0.1.40.3 = `d5ea7133741e67743c0e886bb426c0ce8d69cf6c` | Git object identity |
| Strata engine | `strata-windows-x64.zip` v0.1.40.3, 135,495,187 B, sha256 `766373e7…a84b26e4` | GitHub release-asset digest; maintainer-uploaded, no build attestation |
| Python lock | unchanged, `locks/strata-python-cp313-win_amd64-strata0.1.31.txt` | v0.1.40.3's `requirements.txt` is still v0.1.31's blob (`3db8418a…`); `PY_PACKAGES` and `CUDA_WHEELS` are unchanged |
| Model, MTP source, llama.cpp | unchanged from the predecessor: IQ3_S at `ed59f920…`, MTP at `de4b8e4d…`, llama.cpp `3cf0325` | v0.1.40.3 keeps the same `HF_REVISIONS`, `LLAMA_CPP_COMMIT` and MTP revision and tensor hashes |

### What changed in the stock components that this integration had to absorb

- Among the planning constants only `MIN_ENGINE` moves (to 0.1.40.3); requirements, generated config keys and the
  route census (17 GET, 13 POST) are unchanged. The one new `STRATA_*` name, `STRATA_USE_HIP`, is a HIP build
  definition, not a runtime variable.
- Planning a profile's opt-ins needed two more stock code paths, each admitted only as its reviewed body: setup's
  `--parallel` branch with its slot recommendation (`parallel_slot_gb`, `parallel_recommend`, `parallel_note`), and the
  host recommendations it prints (`bench_tips`, `arg_after`). The draft refuses a slot count stock warns about for the
  planned card, and a pinned recommendation stock no longer prints for the planned host.
- The generated config gains the key `"parallel"` when, and only when, the profile pins slots.

## RTX PRO 6000 tuple (2026-10-07): Strata v0.1.40.2 + OMP 18.8.0

### Source refresh

| Component | Measured PRO draft | Observed 2026-10-07 (UTC) | Decision |
|---|---|---|---|
| OMP | v18.5.0 `9348320c…` | v18.5.1 to v18.8.0 (`4ef97c88…`, released 07:15) | **Move to v18.8.0**: the owner's rule for a qualification is the newest stable release of both components. 18.5.1 fixes the dropped retry of a reasoning-only stop (UPSTREAM.md, OMP item 10). Every settings path and `models.yml` compat key the profile renders is still read by 18.8.0. |
| Strata | v0.1.40.1 `82f46a8c…` | v0.1.40.2 (`e8ca9afd…`, released 12:13) | **Move to v0.1.40.2**, the newest stock release and a new engine build (CUDA 13.0, as 0.1.40). Verify windows of 2-4 tokens now read each weight block once (on by default, bit-identical by upstream's account), and the server gives up on an engine that is not ready 900 s after start. Upstream reports default answers byte-identical to 0.1.40 on IQ3_S; not checked here. |

The measured draft is `win11-rtxpro6000-iq3s-131k-strata0.1.40.1-omp18.5.0` (Terminal-Bench, MEASUREMENTS.md); only
the two component pins change, and the engine flags, host floors and model stay the same. The profile has its own
root and ledger and inherits nothing; the earlier PRO drafts and their roots stay as rollback installations.

### Frozen tuple

| Component | Identity | Digest source |
|---|---|---|
| OMP client | `omp-windows-x64.exe` v18.8.0, 236,900,864 B, sha256 `ddee7535…a983a0` (darwin-arm64 212,271,392 B `8fb220c8…07cb98`; linux-x64 283,289,056 B `6d0bd5d6…aa7de1`) | GitHub release-asset digests |
| Strata source | `Niko1221/Strata` v0.1.40.2 = `e8ca9afd03d839d4f8dbbe82dffce7f8a3bafd7a` | Git object identity |
| Strata engine | `strata-windows-x64.zip` v0.1.40.2, 135,496,886 B, sha256 `02901f0c…26eb30` (CUDA 13.0) | GitHub release-asset digest; maintainer-uploaded, no build attestation |
| Python lock | unchanged, `locks/strata-python-cp313-win_amd64-strata0.1.31.txt` | v0.1.40.2's `requirements.txt` is still v0.1.31's blob (`3db8418a…`); `PY_PACKAGES` and `CUDA_WHEELS` are unchanged |
| Model, MTP source, llama.cpp | `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` IQ3_S at `ed59f920…` (two shards, 54,817,524,224 B and 28,800,138,432 B), MTP from `Qwen/Qwen3.8-Flash-Next` at `de4b8e4d…`, llama.cpp `3cf0325` | Hugging Face LFS object ids; v0.1.40.2 keeps the same `HF_REVISIONS`, `LLAMA_CPP_COMMIT` and MTP revision and tensor hashes (`tools/mtp_fetch.py`) |

### What changed in the stock components that this integration had to absorb

- Stock setup v0.1.40.2 adds one planning call, `gfx_arch_is`, in the HIP lane's gfx1103 opt-in branch: a pure string
  comparison, admitted to the draft's static vocabulary. The PRO's plan is unchanged; `MIN_ENGINE` moves to 0.1.40.2.
- v0.1.40.2 moved POST dispatch from `do_POST` into `_post`. The route census read only `do_<METHOD>` bodies, so it
  found no POST route, and every route check passed vacuously. It now follows the methods a handler delegates to and
  finds the same 17 GET and 13 POST routes as v0.1.40.1; the report is incomplete when a pinned route disappears, and
  `tests/unit/test_strata_surface.py` requires every route G13 protects.
- 59 new `STRATA_*` variables, one removed. None reaches the server, which starts without any inherited `STRATA_*`
  variable; the generated config keys are unchanged.
- The engine reports its own version (`Strata 0.1.40.2` in G10), so the allowance for a hotfix whose engine reports
  its base release, which v0.1.40.1 needed, goes unused.

## Fourth tuple (2026-10-02): Strata v0.1.34 + OMP 18.4.10 on the RTX 5090, RTX 3090 and RTX 4090 hosts

### Source refresh

| Component | Third tuple | Observed 2026-10-02 (UTC) | Decision |
|---|---|---|---|
| OMP | v18.4.8 `717f97f4…` | v18.4.9 and v18.4.10 (`cb0d5295…`) | **Move to v18.4.10**: it releases can1357/oh-my-pi#13868 (a tool call whose argument JSON is cut off gets the parse error instead of running), the OMP half of G04; 18.4.9 classifies Strata's overflow message as a context overflow (#13864). |
| Strata | v0.1.31 `9259cad4…` | v0.1.32 (`c499bd10…`), v0.1.33 (`aeb35bed…`) and v0.1.34 (`1678de33…`) | **Move to v0.1.34**, the newest stock release: the maintainer reports the same answers as v0.1.31 on the Coder; a client that hangs up is cancelled within about a second (#430/#431); a refused engine archive is deleted (Strata#397, from our #324). Strata#231's unfinished-call behaviour is unchanged (host-free suite). |

Three profiles share the tuple, model and context: RTX 5090 with 47 GiB RAM
(`win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10`), RTX 3090 with 64 GiB (`…-rtx3090-…`), both with KV
streaming, and RTX 4090 with 32 GiB (`…-rtx4090-coder-iq1m-131k-lowram-…`, stock low-RAM mode, resident variant).
Nothing is inherited from the earlier ledgers; each host got a new root next to its earlier ones.

### Frozen tuple

| Component | Identity | Digest source |
|---|---|---|
| OMP client | `omp-windows-x64.exe` v18.4.10, 245,669,888 B, sha256 `7232c209…0d3895` (darwin-arm64 218,920,720 B `23d3f9ab…d3e508`; linux-x64 291,501,536 B `e3f24c47…a4e289`) | GitHub release-asset digests |
| Strata source | `Niko1221/Strata` v0.1.34 = `1678de333d0e0711bc414ad992b640e1a37dd814` | Git object identity |
| Strata engine | `strata-windows-x64.zip` v0.1.34, 124,412,957 B, sha256 `20dc548a…3ac523` (CUDA 13.0, sm_75/86/89/120 + PTX) | GitHub release-asset digest; maintainer-uploaded, no build attestation |
| Python lock | unchanged, `locks/strata-python-cp313-win_amd64-strata0.1.31.txt` | v0.1.34's `requirements.txt` is the same Git blob as v0.1.31's (`3db8418a…`); `PY_PACKAGES` and `CUDA_WHEELS` are unchanged |
| llama.cpp, model shards, MTP source | unchanged | Same `LLAMA_CPP_COMMIT`, Coder revision and MTP revision in v0.1.34 |

### What changed in the stock components that this integration had to absorb

- Stock `setup.py` v0.1.34 writes the same config as v0.1.31 for all three hosts: stock code driven with each
  host's RAM and VRAM, then real installs on the three hosts. KV streaming (`--kv-resident 32768`) on the 47 and
  64 GiB hosts, the resident low-RAM variant on the 32 GiB one. The new `--kv-streaming` and `--resident-budget-gib`
  options keep their RAM-based defaults under `--yes`, which never reads stdin.
- The v0.1.32-v0.1.34 server honours new config keys (CORS and trusted origins, a request monitor, lazy loading,
  model aliases, a default thinking budget). The generated-config check now accepts only the eleven top-level keys
  every pinned setup writes, instead of rejecting a fixed list that had none of them.
- New routes: `/v1/messages/count_tokens`, `/v1/load`, `/v1/unload`, `/api/health`, a CORS preflight on every
  path, and the opt-in monitor (`/api-monitor`, `/api/requests`). G13 now covers them and the older `/load` and
  `/unload`, and `tests/unit/test_strata_surface.py` fails when a pinned server routes a path G13 does not classify.
- Stock OMP 18.4.10 answers a cut-off call with the parse error, and the model continues. The suite now expects the
  cut-call failures by pinned version instead of on every profile.

## Third tuple (2026-10-01): Strata v0.1.31 + OMP 18.4.8 on 24 GB hosts (draft profiles)

### Source refresh

| Component | Second candidate | Observed 2026-10-01 | Decision |
|---|---|---|---|
| OMP | v18.4.6 `8b25ad4a…` | v18.4.7 and v18.4.8 (`717f97f4…`): macOS natives and TUI only, no change under `packages/ai` or `packages/agent` | **Move to v18.4.8**, the newest stock release; the client side of G04 is unchanged. |
| Strata | v0.1.30 `30ec18ec…` | v0.1.31 (`9259cad4…`) released 2026-10-01 | **Move to v0.1.31**: an unfinished tool call stays unfinished (Strata#231, the Strata half of G04), setup pins the engine release, Hugging Face revisions and Python packages (#214), the low-RAM mode reads experts from the GGUF in place, and a server status race (#266) is fixed. |

Three draft profiles share the tuple, model and context (Coder IQ1_M, 131,072 tokens, INT8 KV, MTP): RTX 3090 with
64 GiB RAM (`win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8`, low-RAM mode off), RTX 4090 with 32 GiB RAM
(`…-rtx4090-coder-iq1m-131k-lowram-…`, stock low-RAM mode, resident variant, KV cache in VRAM) and the same RTX 4090
after a RAM upgrade (`…-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8`, low-RAM mode off; it needs 60 GiB). The
RTX 5090 profile of this tuple waits for a GPU window. Nothing is inherited from the RTX 5090 candidates' ledgers.

### Frozen tuple

| Component | Identity | Digest source |
|---|---|---|
| OMP client | `omp-windows-x64.exe` v18.4.8, 245,133,312 B, sha256 `64e8cc81…99cad2` (darwin-arm64 218,411,824 B `3bde40ca…c02b1a`; linux-x64 290,956,768 B `1b88f7a0…6f31c2`) | GitHub release-asset digests |
| Strata source | `Niko1221/Strata` v0.1.31 = `9259cad4cfa3543cd3b8decab5962672b968c649` | Git object identity |
| Strata engine | `strata-windows-x64.zip` v0.1.31, 106,856,410 B, sha256 `74be0337…ad1f4b` (CUDA 13.0, sm_75/86/89/120 + PTX) | GitHub release-asset digest; maintainer-uploaded, no build attestation |
| Python lock | `locks/strata-python-cp313-win_amd64-strata0.1.31.txt`, sha256 `a9118570…8a81d6` | Resolved on a win_amd64 host from v0.1.31's pinned `requirements.txt` (charset-normalizer 3.5.1 and regex 2026.9.10 differ from the earlier lock) plus `CUDA_WHEELS` |
| llama.cpp, model shards, MTP source | unchanged | v0.1.31 pins the same `LLAMA_CPP_COMMIT`; its `HF_REVISIONS` and `mtp_fetch.REVISION` equal the profile's Coder and MTP revisions |

### What changed in the stock components that this integration had to absorb

- Stock `setup.py` v0.1.31 installs its pinned `requirements.txt` (only when a venv has no install stamp), so the
  lock now mirrors those pins and the pip step finds every package installed.
- Both 24 GB GPUs also drive a display, so WDDM lists desktop processes as `C+G` clients of the GPU. Profiles
  declare `host.display_attached`; `start`, `doctor` and G10 tolerate graphics clients only there, never a compute
  process, and the 1,500 MiB idle limit still applies.
- v0.1.31 reads 16 new `STRATA_*` tuning variables; the server no longer inherits any `STRATA_*` variable.
- The low-RAM profile expects stock setup's resident variant (`--resident-experts`) and no KV streaming; the
  profile check accepts exactly one low-RAM variant flag.

## Second candidate (2026-10-01): `win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`

### Source refresh

| Component | First candidate | Observed 2026-10-01 | Decision |
|---|---|---|---|
| OMP | v18.4.0 `401778d0…` | v18.4.1–v18.4.6 released; v18.4.6 (`8b25ad4a…`) on 2026-10-01 | **Move to v18.4.6**, the newest stock release: 18.4.4 adds a 64-token headway to the fitted output cap (can1357/oh-my-pi#13499, our G17 finding) and 18.4.5 carries our two documentation fixes. |
| Strata | v0.1.27 `a7908053…` | v0.1.28, v0.1.29 and v0.1.30 (`30ec18ec…`) released on 2026-09-30 | **Move to v0.1.30**, the newest stock release: v0.1.28 fixes four of the six findings in `docs/UPSTREAM.md` (the queued-cancel engine crash behind the failed G14, `/status` authentication, the empty-key and `==` comparison, the OOM labelling). v0.1.31, expected to carry the truncated-tool-call fix (Strata#231) and the reproducible-setup fix (Strata#324), was not released. |
| NInfer reference | v0.8.7 | unchanged role | Read-only pattern reference only. |

Both components changed at once; the first candidate's receipts therefore say nothing about this tuple, and every
gate was run again (`releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/`).

### Frozen tuple

| Component | Identity | Digest source |
|---|---|---|
| OMP client | `omp-windows-x64.exe` v18.4.6, 245,041,664 B, sha256 `13e842b0…9d64c6` (darwin-arm64 218,296,912 B `dfeb7f37…e13f60`; linux-x64 290,862,560 B `9eb0668d…4fb163b`) | GitHub release-asset digests |
| Strata source | `Niko1221/Strata` v0.1.30 = `30ec18ec7094550fcc594fd948220d511d80464e`, fetched by commit with `core.autocrlf=false` | Git object identity |
| Strata engine | `strata-windows-x64.zip` v0.1.30, 105,900,046 B, sha256 `e6eaf4bd…c1e01` (engine 0.1.30, CUDA 13.0, sm_75/86/89/120) | GitHub release-asset digest. **Limitation:** maintainer-uploaded asset, no build attestation; not rebuilt from source here. |
| llama.cpp, model shards, MTP draft layer, Python lock | unchanged from the first candidate | Stock `setup.py` v0.1.30 pins the same `LLAMA_CPP_COMMIT`, `PY_PACKAGES` and `CUDA_WHEELS` as v0.1.27 (read from the source), so the wheel lock still describes its inputs; the shards were re-hashed against the pins on the host (G10 deep verification), not downloaded again. |

### What changed in the stock components that this integration had to absorb

- Stock `setup.py` v0.1.30: `MIN_ENGINE` is 0.1.30 (hence the engine archive pin); `--low-ram` gained `resident`
  and `mmap` variants (the profile keeps `off`); new `--rope-scaling`, `--rope-scale` and `--draft-vocab` options
  are not passed, and the generated-config check now rejects the `--resident-experts`/`--rope-*` engine flags and
  the new server config keys `idle_unload_s`, `min_free_vram_mib`, `before_load` and `draft_vocab` (GPU sharing by
  unloading and an alternative draft vocabulary are profile decisions, never defaults). Unattended `--yes` now stops
  when RAM is more than 4 GB below the model's stated need (32 GB for the Coder); the host has 47 GiB.
- Stock `serve/server.py` v0.1.30: `/status` requires the key (Strata#212), so the gate probes send it and G13
  lists it among the protected routes; `/health` reports `loaded`, which `status` treats as a failure when false;
  keys are compared in constant time and an empty `STRATA_API_KEY` stops the server. Idle unload and the
  conversation cache are opt-in and stay off.
- Stock OMP 18.4.6: the wire shape, effort mapping, retry behaviour, RPC protocol and session JSONL that the
  tooling reads were re-verified against the real binary (host-free suite, G11–G19); nothing in the tooling needed
  to change for the client. The declared window stays 1,024 tokens below the engine's: removing the margin would
  be a separate profile change and the 18.4.4 headway was not relied on.

### Host route

The same host (`rtx5090-win-a`) with a **second integration root** next to the first; the first candidate's root
is untouched and remains the rollback installation (switching back is `stop` here, `start` there). The GPU window
was taken and released with the owner's private tooling as before.

## First candidate (2026-09-30): `win11-rtx5090-coder-iq1m-131k`

Recorded 2026-09-30 (UTC) at the start of implementation. Source packet: `docs/handoff/2026-09-30/`
(its `SHA256SUMS` verifies).

### Repository state at start

- `alphastorm/omp-strata`: public, empty (no commits), default-branch metadata `master`. Work is committed locally
  on `master`; nothing is pushed, tagged or released by this work.
- The handoff packet was moved to `docs/handoff/2026-09-30/`. Before publication, two `HANDOFF.md` lines were
  redacted in place (the owner's name and a private host-inventory reference) and `SHA256SUMS` was regenerated;
  everything else is verbatim. `AGENTS.md` carries its binding decisions.

### Source refresh (handoff §1 rule)

| Component | Handoff candidate | Observed 2026-09-30 | Decision |
|---|---|---|---|
| OMP | v18.4.0 `401778d0…` | stock releases v18.4.1–v18.4.4 exist | **Keep v18.4.0.** No concrete blocker found in 18.4.0 for this route; findings below are recorded against 18.4.0. |
| Strata | `main` @ `a790805…` | tag **v0.1.27** is exactly `a790805…`; `main` unchanged | **Keep**, now identified as the v0.1.27 release. |
| NInfer reference | v0.8.7 | v0.9.0 exists | Read-only pattern reference only; no NInfer receipts are reused. |

### Frozen tuple

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

### Model and profile choice

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

### Host route

One native Windows 11 host (public label **rtx5090-win-a**): RTX 5090 32 GB (sm_120), driver 610.88, 47 GiB RAM,
16-core AVX-512 CPU, NVMe with >600 GiB free, Python 3.13 via the `py` launcher, Git for Windows. It normally
serves another local runtime; the owner authorized exclusive use of the fleet for this work. The GPU window is
taken by pausing that runtime's supervisors and stopping its container, and released by restarting the same
container and verifying its identity and health (private operator tooling, not part of this repository).
macOS is used only as the host-free development/CI client; no macOS Strata runtime is implied.

### Findings recorded at baseline

- Strata disables authentication entirely when its key is empty and compares keys with `==`; `/health`, `/status`,
  `/` and static assets are always unauthenticated. The launcher refuses to start without a ≥32-character key.
- Strata accepts any `model` string on completions; identity is proven by the controlled launch, `/props`
  (`n_ctx`, `build_info`, `model_path`) and the install record, not by the model name.
- Strata ignores `tool_choice`, `parallel_tool_calls`, `stop` and `stream_options`; usage is always sent in the
  final chunk with `prompt_tokens_details.cached_tokens` (the engine's reused prefix) and llama.cpp-style `timings`.
- Stock OMP 18.4.0 behaviour is recorded from the real binary in `tests/mock/` findings (see `docs/MEASUREMENTS.md`),
  not from source reading alone.
