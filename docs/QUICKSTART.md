# Quickstart

Stock Oh My Pi (OMP) 18.16.0 runs against a local stock Strata v0.2.10 server. Pick the profile for your host; the same
commands work with any of them, and every profile keeps its own integration root and ledger.

| Host | Current qualified profile | Qualified rollback |
|---|---|---|
| RTX PRO 6000 | `profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0.json`: stock Strata v0.2.10 (engine 0.1.56), Qwen3.8-Flash-Next IQ3_S at the model's trained 262,144-token context with every expert in VRAM, four batch slots with per-slot multi-token prediction (MTP, `--batch-mtp`, `strata.batch_mtp: true`), direct per-layer embedding (PLE) reads (`--ple-io direct`, `strata.ple_io: "direct"`), KV in VRAM (`--kv-streaming off`, `setup_args.kv_streaming: "off"`, 78 GiB available-RAM start floor), stock `parallel_stack` and `gdn_stack` in `strata.engine_env`, conversation parking (the engine's 8,192 MiB cache) and 32K prompt chunks | `profiles/win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0.json`: the same family on stock Strata v0.2.9 (engine 0.1.55) + OMP 18.15.0 |
| RTX 5090 (**default**) | `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0.json`: stock Strata v0.2.10 (engine 0.1.56), Coder IQ1_M at 262,144 tokens, KV in VRAM (`--kv-streaming off`, `setup_args.kv_streaming: "off"`), elastic KV growth (`--kv-grow`, `strata.kv_grow: true`), stock `gdn_stack` in `strata.engine_env` (34 GiB available-RAM start floor; requires the host's Docker Desktop and WSL, which run its production NInfer container, to be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script and re-registered with the owner's fleet controller) | `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0.json`: the same family on stock Strata v0.2.9 (engine 0.1.55) + OMP 18.15.0 |
| RTX 5090 (qualified alternative) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json`: stock Strata v0.2.10 (engine 0.1.56), Coder IQ1_M at 131,072 tokens (34 GiB available-RAM start floor; starts with Docker Desktop and WSL running, production container stopped by the fleet controller; qualified, no longer the default) | `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0.json` |
| RTX 4090 + RTX 3090 pair (`rtx3090-win-a`) | `profiles/win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0.json`: stock Strata v0.2.10 (engine 0.1.56) + OMP 18.16.0, IQ3_S at 262,144 tokens across both cards, stock roles (`--gpu-roles 0=main,1=helper`, RTX 4090 as Main staged last), manual layer split 24 (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, `strata.trim_stage_weights: true`), stock DFlash2 drafter alone (`strata.drafting: "dflash2"`, `--draft dflash2 --draft-fallback none`, packed offline from pinned `incoai/Qwen3.8-Flash-Next-DFlash2` files; drops `--pipeline-windows 2`), no batch slots, display on the RTX 4090, direct PLE reads (`--ple-io direct`, `strata.ple_io: "direct"`), engine `sm_86` default table (`sm86_table`) and stock `gdn_stack` in `strata.engine_env`, engine's 8,192 MiB automatic conversation cache | `profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0.json`: the same v0.2.10 + OMP 18.16.0 settings with stock MTP drafting and `--pipeline-windows 2` |

- On the RTX PRO 6000 (`rtxpro6000-win-a`), `strata.ple_io: "direct"` (`--ple-io direct`,
  [OPERATIONS.md](OPERATIONS.md#stock-ple-direct-reads)) reads the 26.8 GiB PLE table from the model file on SSD
  instead of locking it in RAM at start, `strata.batch_mtp: true` (`--batch-mtp`,
  [OPERATIONS.md](OPERATIONS.md#stock-per-slot-mtp)) gives each of the four batch slots its own MTP drafter state,
  `setup_args.kv_streaming: "off"` (`--kv-streaming off`, 78 GiB available-RAM start floor) keeps KV in VRAM without
  `--kv-resident 32768`, and `strata.engine_env` pins stock `serve/server.py`'s Linux-only nine-switch `parallel_stack`
  and two-switch `gdn_stack` ([UPSTREAM.md](UPSTREAM.md#stock-engine-environment-v0210--0156)). Against its v0.2.9
  `kvvram-envpg` rollback ([measurements](MEASUREMENTS.md#strata-v0210-windows-2026-11-03-stock-omp-18160)), cold decode
  rose +3.9% to +6.2% (`1.058` at depth 0, `1.054` at 8K, `1.062` at 32K, `1.058` on warm 32K, `1.039` at 100K) with
  aggregate throughput parity (`w2` `0.969–1.008`, `w3` `1.032`) and identical startup lines (`24,576` expert-cache
  slots, borrow `5,542`), while concurrent short-prompt TTFT missed the 5% rule (`w2/c2` TTFT p50 `1.052` and p95
  `1.136`; `w2/c4` TTFT p50 `1.326`), which the owner overrode (`"Override: chain + G23"`); chain restart readiness is
  31.0-31.3 s (G16 31.1 s, G20 31.0 s, G21 31.3 s; 46.8-47.4 s in the A/B blocks), and G10 Windows commit headroom is
  83.05 GiB (129.12 GiB available RAM; 83.35 / 129.57 GiB on the v0.2.9 rollback) of a 219.70 GiB limit. GDN
  tensor-core numerics are not bit-exact upstream, and engine env pins are reviewed per engine release
  (`ENGINE_ENV_REVIEWED_ENGINES`, engines `0.1.55` and `0.1.56`), so the next engine needs a fresh review. The v0.2.9
  PRO model candidates
  (`profiles/win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0.json`,
  `profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0.json` and
  `profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0.json`) stay comparison-only
  drafts.
- On the pair, pinning manual `strata.setup_args.layer_split: "24"` (the layer the automatic planner chose),
  `strata.trim_stage_weights: true` (`--trim-stage-weights`, [OPERATIONS.md](OPERATIONS.md#stock-stage-weight-trim)),
  `strata.ple_io: "direct"` (`--ple-io direct`, keeping the 26.8 GiB PLE table on direct SSD reads and the engine's
  8,192 MiB automatic conversation cache enabled), `strata.engine_env` `sm86_table` + `gdn_stack`, and stock DFlash2
  drafting alone (`strata.drafting: "dflash2"`,
  `--draft dflash2 --draft-model <root>\data\dflash2\qwen3.8-flash-next-dflash2.q4_0-selq4.pack --draft-fallback none --draft-conf 0.35 --draft-vocab <root>\data\dflash2\draft_vocab.bin`,
  packed offline during `install` by stock `tools/dflash2_pack.py` from pinned
  `incoai/Qwen3.8-Flash-Next-DFlash2` revision `a22a1744e85c17364dcc54a6a420af7135d4c7f6` `config.json` and
  `model.safetensors`, with `STRATA_NO_ACQUIRE=1` and no silent MTP fallback;
  [UPSTREAM.md](UPSTREAM.md#stock-dflash2-pair-arm-v0210--0156)) drops `--pipeline-windows 2` and grows the expert caches
  to 19.41 GiB (`10,768` slots) on the RTX 3090 and 18.31 GiB (`9,126` slots) on the RTX 4090 (`19,894` resident experts
  = `81%`, vs 19.14 and 17.75 GiB, `19,469` = `79%`, on the v0.2.10 `pw2` `env86g` MTP rollback). In three paired cold
  starts against its v0.2.10 `pw2` `env86g` rollback (45.0-45.1 s to ready, 65.65-65.66 GiB available RAM at ready,
  31.4 GiB startup commit headroom of 135.7 GiB), cold decode rose +8.2% at 8K (`1.082`), +9.3% at 100K (`1.093`),
  +10.1% at depth 0 (`1.101`), +13.6% at 32K (`1.136`) and +7.7% on warm 32K (`1.077`), TTFT at 8K-100K was `0.955-0.980`,
  and `w1` / `w3` throughput was `1.001` / `1.033`; after the owner overrode its 6-token-window inter-event gap (`w3` max
  gap `1.075-1.112`, p95 inter-event gap `1.122-1.170`), queued-prefill (`0.802`, prompt time `1.227`) and empty-prompt
  TTFT (`1.052`) misses (`"Run chain, make DFlash2 current"`), the requalification chain at `837bc89` (`1f2d483`) passed
  all 14 measured gates (G10 27.51 GiB commit headroom of 135.69 GiB and 65.65 GiB available RAM, G16/G20/G21
  43.1 / 43.2 / 43.4 s, G17 near-limit task 59.0 s, G24 17/18, pilot 5/6, batch wall 916 s), keeping the qualified v0.2.10
  `pw2` `env86g` MTP profile
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0.json`:
  G10 27.54 GiB commit headroom of 135.69 GiB and 65.37 GiB available RAM, G16/G20/G21 55.3 / 43.2 / 55.7 s, G17
  near-limit task 59.9 s, G24 16/18, batch wall 1,045 s) as its rollback. The measurement-only v0.2.8 stock-residency
  roles draft
  (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0.json`),
  the held v0.2.7 roles draft (`profiles/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2.json`,
  PLE in RAM, cache off, 1.03 GiB commit headroom; [Niko1221/Strata#4518](https://github.com/Niko1221/Strata/issues/4518)),
  the unmeasured v0.2.7 default-split draft, the default and split-32 v0.2.3 drafts and the v0.1.44.1 pair release
  remain draft, not qualified ([decision](DECISION.md)).
- On the RTX 5090 (`rtx5090-win-a`),
  `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0.json` is the default, pinning
  `setup_args.kv_streaming: "off"` (`--kv-streaming off`), `strata.kv_grow: true` (`--kv-grow`) and `strata.engine_env`
  `gdn_stack` (v0.2.10 vs v0.2.9 A/B: `w1` 512/512 throughput `1.033`, `w3` 32K `1.013`, decode `+1.2%` to `+3.6%`, ready
  31.2-35.2 s vs 20.1-25.2 s), with a 34 GiB available-RAM start floor and a 4,352 MiB automatic conversation cache
  (rolling back to `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0.json`; the
  unpinned-GDN v0.2.9 fallback `profiles/win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0.json` stays
  an uninstalled draft). Operating condition: the host's Docker Desktop and WSL, which run its production NInfer
  container, must be stopped; after WSL restarts, that container must be recreated by the owner's pinned relaunch script
  and re-registered with the owner's fleet controller (a WSL-up start was refused at 7.3 GiB available RAM while another
  of the owner's agents held host memory; untested on an idle host). The 131K profile
  (`profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0.json`, rolling back to
  `profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0.json`; 34 GiB start floor) is the qualified
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

- **RTX PRO 6000:** earlier qualified history starts with the v0.2.9 + OMP 18.15.0 batch-MTP + PLE-direct base profile
  (`slots4-batchmtp-pledirect-parking`), then the v0.2.8 + OMP 18.14.0 batch-MTP + PLE-direct
  (`slots4-batchmtp-pledirect-parking`), PLE-direct (`slots4-pledirect-parking`) and `slots4-parking` profiles, then the
  262K `slots4-parking` choices on v0.2.7 + OMP 18.13.2, then v0.2.3 + OMP
  18.12.6, then v0.2.1, v0.1.44.1, v0.1.43.1 and v0.1.43 with OMP 18.10.1, v0.1.42 with OMP 18.8.9, then v0.1.41 with
  OMP 18.8.6 at 262K and 131K, then stock Strata v0.1.40.3 with OMP 18.8.4, then OMP 18.8.3, and before them
  `profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json`, without those three choices.
- **RTX 5090:** the v0.2.9 + OMP 18.15.0 262K base profile (`coder-iq1m-262k`), v0.2.8 + OMP 18.14.0 (262K and 131K),
  v0.2.7 + OMP 18.13.2 (262K and 131K),
  v0.2.3 + OMP 18.12.6 (131K and 262K; host integration roots removed on 2026-11-02 with the owner's approval),
  v0.2.1 + OMP 18.10.1 (131K and 262K; host integration roots removed on 2026-10-28), v0.1.44.1 + OMP 18.10.1 (131K and
  262K), v0.1.43.1 + OMP 18.10.1, v0.1.43 + OMP 18.10.1, v0.1.42 + OMP 18.8.9, v0.1.41 + OMP 18.8.6 and v0.1.40.3 + OMP
  18.8.4 are retained as earlier qualified history.
- **RTX 4090 + RTX 3090 pair (`rtx3090-win-a`):** the v0.2.9 + OMP 18.15.0 `env86g`
  (`roles-split24-trimweights-pledirect-env86g-parking`) and split-24 trim + PLE-direct base
  (`roles-split24-trimweights-pledirect-parking`) profiles, the v0.2.8 + OMP 18.14.0 split-24 trim + PLE-direct
  (`roles-split24-trimweights-pledirect-parking`) and initial PLE-direct (`roles-pledirect-parking`) stock-roles
  profiles, the v0.2.7 + OMP 18.13.2 PLE-direct stock-roles profile, the v0.2.3 + OMP 18.12.6
  stock-roles profile, the v0.2.1 default-split profile (host root removed on 2026-10-28), the v0.1.43.1 and v0.1.43
  262K parking profiles and the v0.1.42 262K parking and 131K display-on-RTX-4090 profiles stay earlier qualified
  history before `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` (display on the RTX 3090).
</details>

## Requirements

- Windows 11 x64 with an NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB, sm_120) that no other program
  computes on; it may drive the display. Tested driver 616.92.
- At least 96 GiB RAM with **78 GiB available when starting** (same on the v0.2.9 `kvvram-envpg` rollback; 74 GiB on the
  earlier v0.2.9 batch-MTP + PLE-direct base profile), and a page file: the running engine holds about 56.0 GB resident
  and commits about 134.8 GB on the current `kvvram-envpg` profile (56.1 GB resident and 134.9 GB committed on the v0.2.9
  `kvvram-envpg` rollback; 73.7 GB resident and 136.6 GB committed on the v0.2.9 and v0.2.8 batch-MTP + PLE-direct
  streamed-KV profiles; 101.3 GB resident and 135.1 GB committed on v0.2.8 `slots4-parking` where the 26.8 GiB PLE
  table is locked in RAM), including up to 8,192 MiB of parked conversations (RAM + page file).
- About 96.7 GB free disk for the integration root (the current PRO root measured 96.7 GB, 83.6 GB of it model
  shards); `doctor` wants 91 GiB free.
- Python 3.13 via the `py` launcher, Git for Windows, and network access to GitHub and Hugging Face for the
  one-time download. Inference itself needs no network.
- Measured install and start timings: G26 records the guarded install and launch example in a new integration root
  alongside earlier tuples, not on a fresh OS (see [the measurements](MEASUREMENTS.md)). On the current v0.2.10
  `kvvram-envpg` profile, G26 ran on an already prepared root (`install` 22.0 s, `start` 50.3 s; 21.3 s and 53.1 s on
  the v0.2.9 `kvvram-envpg` rollback; first `install` in a new root on v0.2.8 batch-MTP took 1,063.2 s and `start`
  58.3 s); measured restarts took 31.0-31.3 s (G16 31.1 s, G20 31.0 s, G21 31.3 s; 31.0-31.3 s on the v0.2.9
  `kvvram-envpg` rollback, 35.1-39.7 s on the v0.2.9 base profile and 35.5-51.5 s on v0.2.8 batch-MTP).

The other qualified profiles (alongside the PRO's 96.7 GB roots, the RTX 5090 roots of Strata v0.2.10 + OMP 18.16.0
and their v0.2.9 + OMP 18.15.0 rollbacks each took 70.9 GB for the 262K `kvvram-kvgrow-envg` default and the 131K
alternative, the current display-on-RTX-4090 262K pair `df2` DFlash2 root took 97.8 GB while its `v0.2.10` `env86g`
(`pw2`) rollback root and earlier `v0.2.9` / `v0.2.8` roots each took 95.7 GB, the single-card RTX 3090 root of v0.1.40.3
+ OMP 18.8.4 took 69 GB, and the fourth tuple's low-RAM root 99 GB on the RTX 4090; `doctor` wants 93 GiB free on the
current `df2` pair profile, 91 GiB on the PRO and `pw2` pair rollback, and 90 GiB on the RTX 5090 and earlier profiles):

| Profile | GPU | RAM: total / available at start | Ready after `start` |
|---|---|---|---|
| `win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.10-omp18.16.0` | RTX 4090 + RTX 3090, 24 GB each, display on RTX 4090 | 86 / 78 GiB, plus a page file (27.51 GiB commit headroom of 135.69 GiB serving in G10 on `df2`, 27.54 GiB on the v0.2.10 `pw2` `env86g` rollback) | 43.1-43.4 s on measured chain restarts (G16 43.1 s, G20 43.2 s, G21 43.4 s; 45.0-45.1 s in the cold-start A/B blocks; 55.3 / 43.2 / 55.7 s on the v0.2.10 `pw2` `env86g` rollback); G26 start wall 74.3 s (install 33.1 s on an already prepared root; 66.8 s and 27.0 s on the `pw2` rollback; 820.3 s first install on v0.2.8) |
| `win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.10-omp18.16.0` (default) | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 63.0 GB; requires Docker Desktop and WSL stopped on the host) | 19.2-19.5 s on measured restarts (G16 19.3 s, G20 19.2 s, G21 19.5 s; 31.2-35.2 s in the cold-start A/B blocks; 18.6-18.9 s on the v0.2.9 rollback); G26 start wall 22.4 s (install 11.7 s on an already prepared root; 365.6 s first install on v0.2.8) |
| `win11-rtx5090-coder-iq1m-131k-strata0.2.10-omp18.16.0` (qualified alternative) | RTX 5090, 32 GB | 45 / 34 GiB, plus a page file (the engine commits about 64.8 GB; starts with Docker Desktop and WSL running) | 18.7-18.9 s on measured restarts (G16 18.7 s, G20 18.7 s, G21 18.9 s; 16.1-26.8 s on the v0.2.9 rollback); G26 start wall 36.2 s (install 10.7 s on an already prepared root; 297.8 s first install on v0.2.8) |
| `win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` | RTX 3090, 24 GB | 60 / 34 GiB | 17-19 s |
| `win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10` (fourth tuple) | RTX 4090, 24 GB, stock low-RAM mode | 30 / 16 GiB | about 15 s |
## Install and start

Run from a checkout of this repository (PowerShell). The integration root is dedicated to this tool; nothing is
written to `%APPDATA%\Strata` or to your normal OMP configuration.

```powershell
git clone https://github.com/alphastorm/omp-strata.git "$env:USERPROFILE\src\omp-strata"
Set-Location "$env:USERPROFILE\src\omp-strata"
$prof = "profiles\win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0.json"
$root = "$env:USERPROFILE\omp-strata-0.2.10-omp18.16.0-kvvram-envpg-262k"   # one root per candidate; never reuse another candidate's root

py -3 scripts\omp_strata.py validate --profile $prof               # profile pins and budgets, no host access
py -3 scripts\omp_strata.py doctor   --profile $prof --root $root  # read-only host and install inspection
py -3 scripts\omp_strata.py fetch    --profile $prof --root $root  # ~85 GB, resumable, SHA-256 verified before use
py -3 scripts\omp_strata.py install  --profile $prof --root $root  # unmodified stock setup.py, local verified inputs
py -3 scripts\omp_strata.py keygen   --profile $prof --root $root  # private API key file, never printed
py -3 scripts\omp_strata.py start    --profile $prof --root $root  # 127.0.0.1:18090, key required, ~31.0-31.3 s to ready on restarts (50.3 s in G26)
py -3 scripts\omp_strata.py status   --profile $prof --root $root
```

`start` returns once authenticated identity checks pass (model id, 262,144-token context, `Strata 0.1.56` — the
v0.2.10 engine component version, not `0.2.10` — and unauthenticated requests refused). It refuses to start when the
port is taken by anything it does not own, when another program uses the GPU (a display is allowed), or when less than
78 GiB RAM is available.

## Use OMP

`launch-omp` runs the pinned stock OMP binary with the isolated `omp-strata` profile: every model role pinned to
the local Strata model, up to four requests at once (the server's batch slots), extension/skill/rule discovery off,
speculative compaction off, provider credentials scrubbed from the environment, and the Strata key passed privately.
Run it from the project you want to work on:

```powershell
Set-Location C:\path\to\your\project
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0.json" --root "$env:USERPROFILE\omp-strata-0.2.10-omp18.16.0-kvvram-envpg-262k"
```

Arguments after `--` go to OMP, for example a non-interactive turn:

```powershell
py -3 "$env:USERPROFILE\src\omp-strata\scripts\omp_strata.py" launch-omp --profile "$env:USERPROFILE\src\omp-strata\profiles\win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.10-omp18.16.0.json" --root "$env:USERPROFILE\omp-strata-0.2.10-omp18.16.0-kvvram-envpg-262k" -- -p --auto-approve "Run the tests and fix the failing one."
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
