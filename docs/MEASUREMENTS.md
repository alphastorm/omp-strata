# Measurements

Host **rtx5090-win-a**: Windows 11 Pro, RTX 5090 32,607 MiB (driver 610.88), 47.15 GiB RAM, a 31 GB page file,
a 16-core AVX-512 CPU and NVMe storage. Successive stock tuples were measured with the same model
(Qwen3.8-Flash-Next Coder IQ1_M), 131,072-token context, INT8 KV and MTP speculation. The fourth tuple qualifies on
this host and the two 24 GB hosts; after its RAM upgrade the RTX 3090 also ran larger models to choose its
configuration, and the fifth tuple's drafts were compared with the hosts' NInfer installations. Newest figures come
first; earlier sections are kept unchanged as dated history.

## Fifth tuple and Strata against NInfer (2026-10-03): stock Strata v0.1.38, stock OMP 18.5.0

Draft profiles `win11-<gpu>-<model>-<context>-strata0.1.38-omp18.5.0`, each installed into its own root by the
guarded install with stock setup's choices; the Coder roots ran G10 (published, binding each install), every root
ran `scripts/perf_probe.py` (one request per depth, 512 output tokens, server-reported). Nothing here is a
qualification: every ledger stays draft. The NInfer side is what each host already runs: omp-ninfer v0.10.0 in its
Docker Desktop container on the RTX 5090 (image `sha256:fff4ee38…`, profile `qwen38-5090-v0.10.0`) and the native
Windows release `qwen38-3090-native-v0.6.2-beta.1` on the RTX 3090, both serving Qwen3.8 27B (NInfer's mixed
Q4/Q5 build) through its Responses provider. Engine, model, quantization and API all differ, so no comparison below
is engine-only.

### What stock setup picks on each host

| Host, RAM as setup reads it | Stock `--yes` choice | Outcome |
|---|---|---|
| rtx5090-win-a, 47.2 GiB | original model Q2_0, 131K, every expert in VRAM, no KV streaming | start refused: 37.2 GiB available, the profile needs 44 GiB at start (Docker's WSL VM keeps RAM after NInfer stops) |
| rtx4090-win-a, 191.7 GiB | original model IQ3_XXS, 131K, INT8 KV, `--kv-resident 32768` | not measured (memory errors, below) |
| rtx3090-win-a, 127.7 GiB | original model IQ3_XXS, 131K, INT8 KV, `--kv-resident 32768` | measured below |

### Strata v0.1.38 throughput by root (perf probe)

| Root | Decode at ~60 / 8K / 32K / 64K / 100K tokens | Prefill, 8K-100K | Cold 100K prompt to first token | MTP acceptance |
|---|---|---|---|---|
| rtx5090-win-a, Coder IQ1_M 131K | 176 / 179 / 172 / 167 / 175 tokens/s | 6.3-7.6K tokens/s | 14.1 s | 0.76-0.83 |
| rtx3090-win-a, Coder IQ1_M 131K | 87 / 100 / 99 / 101 / 90 | 2.1-2.6K | 41.2 s | 0.75-0.82 |
| rtx3090-win-a, IQ3_XXS 131K (stock choice) | 78 / 100 / 110 / 95 / 98 | 1.4-1.6K | 69.2 s | 0.80-0.89 |
| rtx3090-win-a, IQ3_S 131K | 67 / 88 / 86 / 84 / 84 | 1.1-1.3K | 85.3 s | 0.85-0.88 |

- **The RTX 5090 Coder on v0.1.38**: decode 167-179 tokens/s (v0.1.34: 148-206), cold 100K prompt 14.1 s (about
  16 s).
- **On the RTX 3090 the stock choice decodes like the Coder and prefills at 60% of its rate.** IQ3_XXS is the
  original model (twice the Coder's experts). IQ3_S, the best-quality original size, decodes 84-88 tokens/s against
  93-96 on v0.1.36 with the same generated flags (one probe each).

### Client-side speed, same prompts on both engines

`scripts/probe_g25_speed.py`, one prompt set per host (filler at the nominal depth plus one instruction; 3 runs per
depth, output capped at 512 tokens, medians). TTFT is dispatch to the first streamed token of any kind; the output
rate is completion tokens over the time after it.

| Host | Engine | TTFT at ~0 / 8K / 32K / 100K tokens | Output tokens/s at the same depths |
|---|---|---|---|
| rtx5090-win-a | NInfer v0.10.0 | 0.12 / 2.55 / 10.96 / 42.77 s | 250 / 204 / 189 / 124 |
| rtx5090-win-a | Strata, Coder | 0.21 / 1.34 / 4.55 / 14.08 s | 145 / 149 / 135 / 137 |
| rtx3090-win-a | NInfer v0.6.2 | 0.23 / 9.42 / 40.79 / 160.37 s | 81 / 70 / 69 / 58 |
| rtx3090-win-a | Strata, Coder | 0.77 / 4.64 / 13.53 / 40.90 s | 86 / 88 / 87 / 79 |

- **Strata reads long prompts 3-4× faster on both GPUs.** NInfer prefills about 2.4K tokens/s on the RTX 5090 and
  0.65K on the RTX 3090 at 100K.
- **NInfer generates faster on the RTX 5090 up to 32K** (250 against 145 tokens/s on a short prompt) and slower at
  100K. Its 512 tokens were all reasoning (the provider's low effort), Strata's 298-381 visible answer tokens, so
  output lengths differ; the rates are not a matched benchmark.

### Paired coding evaluation against NInfer (G25)

The frozen `synthetic-1` evaluation through one pinned stock OMP 18.5.0 binary on both arms, six exclusive windows
per host in the order Strata, NInfer, NInfer, Strata, Strata, NInfer, after a six-attempt pilot per arm (Strata 5/6
and NInfer 5/6 on the RTX 5090, 5/6 and 3/6 on the RTX 3090). Every engine start was cold. Runs
`g25-rtx5090-20261003f` and `g25-rtx3090-20261003e`; exported plans, window aggregates, paired summaries and G25
receipts are in each release's `evidence/` and `receipts/`. Both ran on the hosts' normal accounts, not a
restricted evaluation account.

| Measure | RTX 5090: Strata | RTX 5090: NInfer v0.10.0 | RTX 3090: Strata | RTX 3090: NInfer v0.6.2 |
|---|---|---|---|---|
| Verified completions | **15/18** | **14/18** | **15/18** | **15/18** |
| Pairs: both pass / Strata only / NInfer only / neither | 14 / 1 / 0 / 3 | | 15 / 0 / 0 / 3 | |
| Median task wall, all attempts | 36.4 s | 29.1 s | 85.5 s | 88.7 s |
| Median task wall, verified passes | 34.7 s | 27.2 s | 83.0 s | 83.4 s |
| Summed task wall, all 18 attempts | 839 s | 733 s | 1,905 s | 2,028 s |
| Median Strata/NInfer ratio over jointly passed pairs | 1.39 (14 pairs) | | 0.98 (15 pairs) | |
| Output tokens, all attempts | 117K | 137K | 127K | 126K |
| Cold start to ready | 14.4-14.9 s | 34.7-35.1 s | 24.2-26.1 s | 113.2-115.8 s |
| GPU memory while serving | 30,836 MiB | 29,472 MiB | 23,443 MiB | 22,970 MiB |
| GPU power limit | 600 W (default) | 600 W (default) | 370 W (default) | 300 W (NInfer's qualified limit) |
| Lowest available RAM | 8.2 GiB | 8.3 GiB | 91.2 GiB | 106.2 GiB |

| Task: passes, median wall | RTX 5090: Strata | RTX 5090: NInfer | RTX 3090: Strata | RTX 3090: NInfer |
|---|---|---|---|---|
| bugfix-a | 3/3, 29.7 s | 2/3, 29.7 s | 3/3, 67.7 s | 3/3, 62.9 s |
| bugfix-b | 3/3, 86.1 s | 3/3, 18.5 s | 3/3, 159.4 s | 3/3, 103.4 s |
| multifile-regression | 3/3, 44.8 s | 3/3, 30.8 s | 3/3, 72.3 s | 3/3, 94.0 s |
| tool-loop | 0/3, 65.5 s | 0/3, 70.7 s | 0/3, 111.8 s | 0/3, 195.6 s |
| long-context | 3/3, 26.7 s | 3/3, 22.0 s | 3/3, 83.2 s | 3/3, 93.4 s |
| continuation | 3/3, 32.2 s | 3/3, 25.9 s | 3/3, 87.7 s | 3/3, 78.3 s |

- **Neither frozen claim holds on either GPU.** Higher completion needs three more Strata passes; faster needs a
  median ratio of at most 0.80 and no greater Strata total. The RTX 5090's 15/18 against 14/18 is one bugfix-a
  attempt; tool-loop failed every attempt on both engines.
- **On the RTX 5090 NInfer is faster on these tasks**: Strata's paired median took 1.39× NInfer's, its summed wall
  1.14×. The largest gap is bugfix-b, where the Coder wrote 12.6K output tokens (median) against NInfer's 3.4K; on
  the other tasks the outputs are similar and Strata took 0-45% longer (tool-loop 7% less), in line with NInfer's
  faster decode up to 32K.
- **On the RTX 3090 the two are even** (paired median 0.98, Strata 6% less summed wall): Strata was faster on
  multifile-regression, long-context and tool-loop, NInfer on the bugfix tasks and continuation. NInfer ran at its
  own 300 W cap, Strata at the card's 370 W.
- **Strata restarts 2.4× (RTX 5090) to 4.5× (RTX 3090) faster.** Neither number includes NInfer restoring a saved
  session or Strata re-reading a transcript; switching engines on the RTX 5090 also waited for Docker's VM to return
  RAM (86-91 s from NInfer to Strata).
- NInfer serves Qwen3.8 27B with a 131,072-token context (BF16 KV on the RTX 5090, INT8 on the RTX 3090); Strata
  the Coder IQ1_M at 131,072 with INT8 KV.

### RTX 4090 with 192 GB: not measured (memory errors)

Host rtx4090-win-a now has 4 × 48 GB of DDR5 (191.7 GiB reported) running at 5600 MT/s with two DIMMs per
channel. Stock v0.1.38 setup picks the original model's IQ3_XXS at 131K with INT8 KV and `--kv-resident 32768` for
it. The host is stable idle and fails under load:

- Four bugchecks on 2026-10-03: 0xEF, 0x1A (0x61941) twice, and 0x1A (0x403), whose page-table and PFN parameters
  differ in a single bit, the pattern Windows documents as a probable hardware error.
- SHA-256 of an unchanged 29.6 GB model shard came out wrong four times with three different values, while
  `Get-FileHash` read the same file twice and returned its pinned hash; a chunked re-hash of that file crashed the
  host. A model download also failed with a TLS decryption error.

No RTX 4090 figure was taken on this tuple: the Coder 131K/262K, IQ3_XXS 131K and IQ3_S 131K/262K roots are
prepared and their search, then the comparison with the host's native NInfer lane, run once the memory passes a
memory test at a stable setting.

## Stock calibration on three GPUs (2026-10-03)

Stock setup's last interactive question, `Tune Strata for this PC now?`, defaults to yes and runs
`tools/calibrate.py`; `--yes` installs skip it, and so does the guarded install, so every other figure in this file
ran with the engine's defaults. The stock tool, run unchanged against an installed root's generated config with the
server stopped, measures decode on three short prompts (128 tokens, temperature 0, thinking off) for a sweep of PCIe
shares and draft floors, re-measures the best pair interleaved with the default three times, then restarts the
engine with fewer CPU workers. It keeps a setting only when it is more than 3% faster. The engine already adapts
the PCIe share to the link: it probes host-to-device bandwidth at start and scales its 0.55 default down below
20 GB/s (the RTX 3090's Gen3 x8 link measured 6.2 GB/s: share 0.13).

| Host and root | Engine defaults: PCIe share, draft floor, CPU workers | Kept by stock calibration | Interleaved decode, default vs best pair | Run |
|---|---|---|---|---|
| rtx5090-win-a, Coder 131K (v0.1.34) | 0.55, 0.5, 15 | nothing | 169.9 vs 171.6 tokens/s (+1.0%, 0.20 / 0.70) | 129 s |
| rtx4090-win-a, Coder 131K low-RAM (v0.1.34) | 0.55, 0.5, 23 | nothing | the best pair is the default | 185 s |
| rtx3090-win-a, Coder 131K (v0.1.34) | 0.13, 0.5, 9 | nothing | 94.7 vs 93.8 (0.20 / 0.70) | 215 s |
| rtx3090-win-a, IQ3_S 131K (v0.1.36) | 0.13, 0.5, 9 | `--pcie-frac 0.20 --spec-min-p 0.70` | 68.3 → 74.4 (+8.9%) | 327 s |
| rtx3090-win-a, IQ3_S 262K (v0.1.36) | 0.13, 0.5, 9 | `--pcie-frac 0.20 --spec-min-p 0.70` | 69.0 → 71.5 (+3.6%) | 316 s |

- **For the Coder, the configuration measured everywhere else in this file already is the calibrated one.**
- **PCIe share matters most, and only where experts miss the GPU.** Single-sweep decode at shares 0 / 0.20 / 0.35 /
  0.55 / 0.75: RTX 3090 Coder 91 / 96 / 84 / 76 / 66 tokens/s (94 at its 0.13), RTX 3090 IQ3_S 67 / 68 / 55 / 42 /
  36 (66 at 0.13), RTX 4090 low-RAM Coder 114 / 114 / 119 / 120 / 118, RTX 5090 169-170 at every share.
- **Fewer CPU workers were slower** on both 24 GB hosts (RTX 3090 Coder 9 / 6 / 4 workers: 92.2 / 88.2 / 81.7;
  RTX 4090 23 / 15 / 12: 113.8 / 109.5 / 107.2) and made no difference on the RTX 5090 (169.6 at 15, 10 and 8).
- These are the stock tool's short-prompt rates, not comparable with the perf probe's.

**Calibrated against uncalibrated IQ3_S 131K on the RTX 3090.** Draft
`win11-rtx3090-iq3s-131k-calibrated-strata0.1.36-omp18.4.12` pins the kept pair; its own root was installed by
stock setup with the pair applied by stock `calibrate.apply`, probed, and the uncalibrated root was probed again
straight after (same perf probe, 512 output tokens, one request per depth).

| Context | Decode, calibrated | Decode, uncalibrated (rerun / earlier) | MTP acceptance, calibrated / uncalibrated rerun |
|---|---|---|---|
| ~60 tokens | 74.9 tokens/s | 71.6 / 71.5 | 0.905 / 0.856 |
| 8K | 100.2 | 96.7 / 96.0 | 0.912 / 0.835 |
| 32K | 99.1 | 98.4 / 93.2 | 0.929 / 0.868 |
| 32K repeated (prefix cache) | 98.8 | 98.0 / 95.6 | 0.926 / 0.870 |
| 64K | 96.9 | 97.9 / 95.6 | 0.931 / 0.885 |
| 100K | 93.3 | 92.2 / 94.0 | 0.906 / 0.842 |

- **Decode gains 4-5% up to 8K tokens; from 32K on the difference is inside the spread of the two uncalibrated
  runs** (5.6% at 32K). Prefill and time to first token do not move (cold 100K prompt: 87.9 s against 88.0 s); the
  higher draft floor raises MTP acceptance from 0.84-0.89 to 0.91-0.93.
- **The frozen evaluation scores 15/18 again**, every task as before (tool-loop 0/3). Median task 109.5 s against
  104.8 s, summed task wall 2,034 s against 2,240 s; output length varies more than that between batches (bugfix-a
  wrote 16.1K output tokens against 19.6K), so the evaluation shows no speed difference beyond the probe's.

## Longer contexts for the Coder on the RTX 3090 (2026-10-03)

The model's trained context is 262,144 tokens. Stock setup also offers 393,216 and 524,288 through yarn rope
scaling with the factor context / 262,144, which Strata calls experimental: a scaled run is a slightly different
model at every position, not only past 262,144 (Strata's own runs, one machine and one quant: needle recall at
512K, real-document Q&A 8/8 at 421K). Drafts `win11-rtx3090-coder-iq1m-262k-strata0.1.36-omp18.4.12` (OMP window
261,120) and `win11-rtx3090-coder-iq1m-524k-strata0.1.36-omp18.4.12` (`--rope-scaling yarn --rope-scale 2`, OMP
window 523,264), each installed into its own root by the guarded install and probed with the perf probe (512
output tokens, one request per depth). KV streaming keeps 32K positions per layer in VRAM and the rest in RAM:
3.6 GB at 262K, 7.2 GB at 524K.

| Context depth | Coder 262K: first token / prefill / decode | Coder 524K, yarn 2: first token / prefill / decode |
|---|---|---|
| ~60 tokens | 0.87 s / - / 95.1 tokens/s | 0.95 s / - / 92.2 |
| 32K | 14.4 s / 2.30K tokens/s / 100.5 | 14.6 s / 2.28K / 95.2 |
| 100K | 44.9 s / 2.31K / 98.1 | 45.5 s / 2.28K / 94.9 |
| 200K | 100.4 s / 2.07K / 81.2 | not probed |
| 250K | 138.4 s / 1.87K / 89.0 | 140.4 s / 1.84K / 93.3 |
| 500K (512,000 tokens) | over the window | 402.6 s / 1.28K / 72.1 |

- **The trained 262K costs nothing below 100K**: the Coder decodes as at 131K, and a cold 250K-token prompt takes
  2.3 min (IQ3_S at 262K: 4.1 min).
- **Yarn doubles the window**: a cold 512,000-token prompt takes 6.7 min to its first token and then decodes 72
  tokens/s. Below 100K the scaled model decodes 3-5% slower than the unscaled one.
- **Quality of the scaled model is not measured here.** Its frozen evaluation was stopped after 1 of 18 attempts when
  the host was needed; a scored 524K batch beside a 262K batch is the comparison still owed.

## RTX 3090 with 128 GB (2026-10-02): which model the RAM unlocks

Host **rtx3090-win-a** after its RAM upgrade: 4 × 32 GB DDR4-3200 (127.69 GiB reported; it had 64 GiB of
DDR4-2133), an 8 GB page file, the same RTX 3090 and driver 617.14; the desktop was signed out. Stock Strata
v0.1.36's setup offers the original Qwen3.8-Flash-Next as GSQ-RCO Q2_0, IQ2_XS, IQ3_XXS and IQ3_S (its notes: IQ3_S
"matches the full BF16 model on the published benchmarks") and, experimental, Unsloth's UD-Q4_K_XL, whose 71.7 GiB of
routed experts stay in RAM up to a budget of the RAM less 24 GB; the Coder (half of the experts) comes only as IQ1_M.
Before the upgrade IQ3_S ran with 0.72 GB of commit to spare, and UD-Q4_K_XL would have read most experts from the
SSD (7-8.5 tokens/s on Strata's 64 GB test PC). The smaller original sizes already fit 64 GiB and rank below IQ3_S
in quality, so they were not measured.

Draft profiles `win11-rtx3090-iq3s-131k-strata0.1.36-omp18.4.12` and
`win11-rtx3090-ud-q4kxl-131k-strata0.1.36-omp18.4.12` (stock OMP 18.4.12), each installed into its own root by the
guarded install with setup's own choices. The Coder column is the fourth tuple's root
(`win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10`, Strata v0.1.34), probed while a download ran on the same
host. Throughput comes from `scripts/perf_probe.py` (one request per depth, 512 output tokens, server-reported
timings); the evaluation is the frozen `synthetic-1` batch. No gate ran: these are variant-selection measurements,
not receipts, and every ledger stays draft.

| Measure | Coder IQ1_M | IQ3_S | UD-Q4_K_XL |
|---|---|---|---|
| Stock setup choice | every expert in RAM, KV streaming | every expert in RAM, KV streaming | all 71 GiB of experts in RAM (`--resident-budget-gib 71`), KV streaming |
| Decode, 8K-100K context | 101-104 tokens/s | 93-96 tokens/s | 49-50 tokens/s (36 in a logged agent turn) |
| Prefill, 8K-100K context | 1.9-2.5K tokens/s | 1.1-1.2K tokens/s | 0.6-0.7K tokens/s |
| Cold 100K-token prompt to first token | 43.2 s | 88.1 s | 148.6 s |
| Repeated 32K prompt (prefix cache) to first token | 0.30 s | 0.32 s | 0.40 s |
| MTP draft acceptance | not reported by v0.1.34 | 0.82-0.87 | 0.82-0.84 |
| Restart to verified readiness | 33 s | 47-56 s | 112-155 s |
| Scored evaluation | 15/18 (fourth tuple at 64 GiB; tool-loop 0/3) | 15/18 (tool-loop 0/3, every other task 3/3) | 7 of the 11 attempts recorded before the harness crashed (below) |
| Median task wall; batch wall | 81.4 s; 1,498 s (64 GiB) | 104.8 s; 2,240 s | 168 s; no batch summary |

- **IQ3_S is what the RAM unlocks.** At 64 GiB it decoded 56-66 tokens/s at about 105K tokens. With 128 GB stock
  setup streams its KV cache to RAM (that needs 64.8 GiB), and decode at the same depth rises to 94 tokens/s, within
  10% of the Coder. Prefill does not change (85.1 s then, 88.1 s now for 100K tokens) and stays at about half the
  Coder's; the original model has twice the Coder's experts.
- **On the coding evaluation IQ3_S ties the Coder.** Both score 15/18 and fail every tool-loop attempt on the same
  exact-money assertion as before, so the original model's other half of the experts buys nothing on these tasks,
  and its median task takes 29% longer. The Coder stays the faster choice for coding; IQ3_S is the stronger model
  outside coding (Strata: the Coder is "weaker outside coding").
- **IQ3_S also runs at the model's trained 262K context.** `win11-rtx3090-iq3s-262k-strata0.1.36-omp18.4.12` (OMP
  window 261,120) decodes 93-94 tokens/s up to 100K tokens of context and 84-85 at 200K-250K, with MTP acceptance
  0.84-0.89. A cold 256,000-token prompt takes 247 s to its first token (1.0-1.2K tokens/s), a repeated one 0.3 s;
  start to readiness took 31 s. A restart replays the whole transcript and pays that; turns that extend a cached
  prefix do not.
- **More RAM does not speed up the Coder.** Its 100K cold prefill took 43.2 s against 44.0 s at 64 GiB (G17): every
  expert was already in RAM, and RAM 50% faster (DDR4-3200 against 2133) did not move prefill, so RAM was not its
  bound.
- **UD-Q4_K_XL runs, but slowly.** With every expert in RAM it decodes 49-50 tokens/s, against the 7-8.5 Strata
  measured with most experts on the SSD (64 GB, RTX 5070), yet half as fast as IQ3_S; it prefills at 0.6-0.7K
  tokens/s and takes 2-2.5 min to restart. Its recorded attempts failed tool-loop (0/2) on the same exact-money
  assertion as the other models, and one of two multifile-regression attempts.
- **The frozen evaluation cannot score a profile whose restart takes over 120 s.** The continuation task restarts the
  server between its phases and gives that hook 120 s; UD-Q4_K_XL's first continuation attempt failed on the cap. On
  the second, the harness's `taskkill` of the slow restart hit its own 10 s timeout, and the uncaught `TimeoutExpired`
  ended the batch before its summary was written. `scripts/evaluate.py` and `eval/support.py` are frozen; this is
  recorded, not patched.

## Fourth tuple on three GPUs (2026-10-02–03): stock Strata v0.1.34, stock OMP 18.4.10

The first qualified tuple: every applicable gate passes, including G04's cut-off tool call on stock releases.
G22, G23 and G25 are not applicable to these local, transcript-replay profiles. Ledgers, receipts and scrubbed
results: [RTX 3090](../releases/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
[RTX 4090, low-RAM](../releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10/qualification.json),
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json).

Each host used a separate integration root, Qwen3.8-Flash-Next Coder IQ1_M, a 131,072-token context, INT8 KV and
stock MTP speculation. The 2026-10-02 main runs used the RTX 3090's **64 GiB** configuration before its RAM upgrade,
the RTX 4090's 32 GiB stock low-RAM configuration, and the RTX 5090's 47.15 GiB configuration. Hardware and setup
choices otherwise match the earlier sections. The RTX 3090's later 128 GB variant-selection measurements above
are not substituted for these qualification measurements.

### Resources (G10, G21)

GB is decimal; GPU memory is MiB. Engine peaks below are the lifetime peaks of the process sampled by G21, not a
maximum across restarted processes. RAM minima include the 2026-10-02 gate samples and compaction rerun, not the
2026-10-03 G15 repeats.

| Measure | RTX 3090, 64 GiB | RTX 4090, 32 GiB, low-RAM | RTX 5090, 47.15 GiB | Boundary |
|---|---|---|---|---|
| GPU memory in use while serving | 23,277 MiB | 23,322 MiB | 30,742 MiB | G10 sampler |
| Engine working-set lifetime peak | 30.27 GB | 27.84 GB | 30.54 GB | G21 per-process peak |
| Engine private-commit lifetime peak | 55.15 GB | 28.15 GB | 63.35 GB | G21 per-process peak |
| Minimum available system RAM | 31.81 GB | **0.44 GB** | 8.87 GB | gate samplers |
| Integration root on disk | 73.8 GB | 99.0 GB | 73.8 GB | G21 file sizes |
| Start to verified readiness | 18.9 s | 14.7 s | 14.7 s | G21 current server, wall |
| Engine dead/restarted events in the main run | 2 | 2 | 2 | G21 log scan, deliberate G15 kills |

The 32 GiB low-RAM host has almost no spare RAM: its passing gates do not establish capacity for other workloads.
G26 also passed each new-root install, start, launch example, project tests and stop, with 3/3 tracer runs; these
were additional installations on the same hosts, not fresh operating systems or byte-identical copies of an older
root. G13 recorded zero non-loopback ETW events on all three hosts.

### Throughput (G17, server-reported)

| Case | RTX 3090 | RTX 4090, low-RAM | RTX 5090 |
|---|---|---|---|
| Cold prefill, 100,030 tokens | 44,048 ms (2.3K tokens/s) | 20,850 ms (4.8K tokens/s) | 15,696 ms (6.4K tokens/s) |
| Cached continuation at ~105K tokens, prompt time | 1,161–1,297 ms | 464–601 ms | 248–284 ms |
| Decode in the three near-limit requests | 84.6–99.4 tokens/s | 86.4–117.5 tokens/s | 150.0–154.8 tokens/s |

These are the qualification requests, not a matched output-length throughput benchmark. Prefix reuse still
belongs to the live engine; restarting it loses that prefix and pays cold prefill again.

### Agent turns, restarts and context (G11–G19)

| Case | RTX 3090 | RTX 4090, low-RAM | RTX 5090 |
|---|---|---|---|
| Tracer runs (typed tools and transcript recall) | 3/3 | 3/3 | 3/3 |
| Same-session prefix reuse | 12/12 continuations | 12/12 continuations | 12/12 continuations |
| Generating cancel to idle | 86 ms | 95 ms | 79 ms |
| Queued drop, then active drop, to idle | 273 ms | 271 ms | 272 ms |
| Engine killed while idle: next turn, passing G15 | 21.0 s | 31.8 s | 15.1 s |
| Engine killed mid-generation: next turn, passing G15 | 21.7 s | 31.2 s | 14.8 s |
| Client restart: next turn (G16) | 2.2 s | 1.4 s | 1.2 s |
| Client and full server restarted: next turn (G16) | 8.1 s | 19.5 s | 3.4 s |
| Exact server limit and explicit overflow (G17) | pass | pass | pass |
| Production compaction, main run (G18L) | 114,383 → 30,633 tokens | 113,058 → 30,351 tokens | 112,664 → 30,158 tokens |

The G16 next-turn times exclude the preceding server stop/start; they are not total restart-to-answer latency.
The G15 rows use the corrected-probe repeats published on 2026-10-03. The RTX 5090 had failed G15 twice; commit
`cb31418` withdraws the interrupted essay before asking for recall (`RECALL_AFTER_INTERRUPT`), and
`g15-20261003T032448Z-de222a` then passed. The RTX 4090 passed both before and after that correction (repeat
`g15-20261003T032520Z-78f0cc`). The RTX 3090 failed once, passed `g15-20261002T032128Z-191f17` with the earlier
probe, and passed the corrected repeat `g15-20261003T043756Z-122117`. Failures remain in each ledger; no engine
patch or durable-state claim is hidden
in the reruns. The RTX 4090 also failed G18's reduced-threshold probe once; the repeat passed, with production
compaction then going from 111,169 to 29,963 tokens. Its first production compaction had already passed.

### Coding evaluation (G24)

The frozen `synthetic-1` set, harness, caps and continuation restart hook are unchanged. Each GPU had a non-scored
six-attempt pilot (5/6, 5/6 and 4/6 respectively), followed by all 18 scheduled scored attempts.

| Task | RTX 3090 | RTX 4090, low-RAM | RTX 5090 |
|---|---|---|---|
| bugfix-a | 3/3 | 3/3 | 3/3 |
| bugfix-b | 3/3 | 3/3 | 3/3 |
| multifile-regression | 3/3 | 3/3 | 3/3 |
| tool-loop | 0/3 | 0/3 | 1/3 |
| long-context | 3/3 | 3/3 | 3/3 |
| continuation | 3/3 | 3/3 | 3/3 |
| **Scored** | **15/18** | **15/18** | **16/18** |
| Median task wall; batch wall | 81.4 s; 1,498 s | 56.3 s; 1,144 s | 39.3 s; 895 s |

Failed tasks remain in the denominator. G24 passes for complete, independently verified reporting, not a perfect
score or a comparison with another runtime. No scored attempt timed out.

## Third tuple on 24 GB hosts (2026-10-01): stock Strata v0.1.31, stock OMP 18.4.8

Draft profiles `win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8` and
`win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8`; receipts and scrubbed results under their
`releases/<profile>/` directories. Boundaries as defined for candidate 1 below. Each host got a fresh integration
root (its first Strata installation) and ran the whole sequence unattended with `scripts/requalify.py`; nothing else
used either GPU. Both GPUs also drive a display (two WDDM graphics clients each, counted by G10).

- **rtx3090-win-a**: RTX 3090 24,576 MiB on PCIe Gen3 x8 under load (x16 maximum), driver 617.14, a 10-core
  AVX-512 CPU, 64 GiB DDR4-2133, a 4.3 GB page file (commit limit minus RAM); the interactive desktop was signed
  out first. Stock setup choices as on the RTX 5090: every expert in RAM, KV streaming on.
- **rtx4090-win-a**: RTX 4090 24,564 MiB on PCIe Gen4 x16 (under load), driver 617.14, a 24-core CPU, 32 GiB
  DDR5-7600, a 5.1 GB page file. Stock setup's low-RAM mode, resident variant: the experts the GPU does not hold are
  copied into RAM at start and the KV cache stays in VRAM (no KV streaming below ~35 GiB of RAM).

### Resources (G10, G21)

| Measure | RTX 3090, 64 GiB | RTX 4090, 32 GiB, low-RAM | Boundary |
|---|---|---|---|
| GPU memory in use while serving | 23,277-23,455 of 24,576 MiB | 23,322-23,492 of 24,564 MiB | sampler |
| Experts at start | 23.42 GiB loaded at 2.6-7.1 GiB/s (log); GPU cache size not logged | GPU cache of 7,708 experts, 14.67 GiB (log); load rate not logged | server log |
| Engine working set, lifetime peak | 30.26 GB | 28.07 GB | per-process peak |
| Engine private commit, lifetime peak | 55.15 GB | 28.10 GB | per-process peak |
| System RAM available while serving | 32.4-33.7 GB of 68.4 GB | 10.1 GB at G10; **0.37 GB minimum** (during G15's engine restarts) of 34.0 GB | sampler |
| Commit available while serving | 13.4 GB of 72.7 GB | 6.1 GB of 39.1 GB | sampler (G10) |
| Integration root on disk | 73.8 GB | 99.4 GB | file sizes (G21) |
| Start to verified readiness | 33 s first start, 17.1-19.4 s restarts | 14.9 s first start, 14.5-14.8 s restarts | wall |
| Engine failures across 7 server logs | none in 455 completed requests | none in 465 completed requests | server log scan |

The 32 GiB host completed every gate, but the resident low-RAM mode leaves almost no RAM in reserve: treat that fit
as the tested configuration only, not as room for anything else. The only engine exits on either host were the
deliberate G15 kills.

### Throughput (server-reported)

| Case | RTX 3090 | RTX 4090, low-RAM | RTX 5090 (candidate 2, for scale) |
|---|---|---|---|
| Cold prefill, 100,030 tokens | 43,906 ms (2.3K tokens/s) | 20,939 ms (4.8K tokens/s) | 15,588 ms (6.4K tokens/s) |
| Cold re-prefill after an engine restart, ~7.1K tokens | 5,661 ms | 13,797 ms | 1,780 ms |
| Cached continuation at ~105K tokens | 294-1,702 ms prompt time | 463-637 ms | 333 ms |
| Decode at ~105K context | 82-98 tokens/s | 105-117 tokens/s | 158-185 tokens/s |
| Decode, short contexts (restart and replay turns) | 79-113 tokens/s | 104-126 tokens/s | 148-206 tokens/s |

Both 24 GB hosts prefill long prompts more slowly than the RTX 5090. Strata's prompt path streams experts to the
GPU, so the RTX 3090's PCIe Gen3 x8 link and DDR4-2133 are the likely bound (not isolated by a separate
measurement). On the RTX 4090 in low-RAM mode the first prompt after each engine restart was slow (13.8 s for 7.1K
tokens, 15.1 s for 12.8K) although readiness took about 15 s; the turns after it reused the prefix cache as usual.

### Agent turns, restarts and context (G11-G19)

| Case | RTX 3090 | RTX 4090, low-RAM |
|---|---|---|
| Tracer runs (typed read/edit/bash, `--continue` recall) | 3/3 | 3/3 |
| Same-session prefix reuse | 13/13 continuations | 13/13 continuations |
| Engine killed while idle: next turn | 26.3 s | 27.8 s |
| Engine killed mid-generation: next turn | 38.2 s | 28.8 s |
| Client restart: next turn | 2.2 s | 1.5 s |
| Client and full server restart: next turn | 8.0 s | 15.8 s |
| Exact server limit (prompt + `max_tokens` + 8 ≤ 131,072) | unchanged | unchanged |
| Near-limit tool turns: OMP-fitted caps, largest prompt + cap | 15,547-24,624; 129,997 | 15,549-24,999; 129,997 |
| Production compaction (long session) | at 113,156 tokens down to 30,140 | at 111,492 down to 29,847 |
| A-B-A interleaving: reused prefix | the shared 6,797-token system prefix | the same |

### Coding evaluation (G24)

The same frozen `synthetic-1` set, harness, caps and restart hook as the RTX 5090 candidates; a non-scored pilot
(6/6 on both hosts) before each scored batch.

| Task | RTX 3090 | RTX 4090, low-RAM |
|---|---|---|
| bugfix-a | 3/3 | 3/3 |
| bugfix-b | 3/3 | 3/3 |
| multifile-regression | 3/3 | 2/3 (one attempt ended on OMP's thinking-loop detector) |
| tool-loop | 2/3 | 1/3 |
| long-context | 3/3 | 3/3 |
| continuation | 3/3 | 3/3 |
| **Scored** | **17/18** | **15/18** |
| Median task wall; batch wall | 74.7 s; 1,409 s | 69.0 s; 1,422 s |

Every tool-loop failure, here and on the RTX 5090, is the same hidden settlement test; across the four scored
batches of this model the task passed 4 of 12 attempts. With three attempts per task, per-host differences are
noise, not a ranking.

### Fresh root (G26)

`install` (unmodified stock `setup.py` v0.1.31 from local verified inputs, the shards fetched beforehand) took
697 s on the RTX 3090 host and 649 s on the RTX 4090 host; the quickstart's `launch-omp` example fixed the fixture in
17.7 s and 12.9 s, and its tests passed afterwards.

### Exploratory: the original model, IQ3_S, on the RTX 3090 (64 GiB)

Draft profile `win11-rtx3090-iq3s-131k-strata0.1.31-omp18.4.8`: the same tuple and settings with Strata's
best-quality size of the original Qwen3.8-Flash-Next instead of the Coder, run in its own root to answer one
question: does the original model pass the task the Coder fails? Only G10, G11, G17, G21 and G24 ran; their receipts
are in its release directory and its ledger stays draft.

| Measure | IQ3_S | Coder IQ1_M (same host, above) |
|---|---|---|
| Stock setup choice | every expert in RAM, no KV streaming (that needs 64.8 GiB) | every expert in RAM, KV streaming |
| Experts at start | 46.84 GiB at 2.9-3.0 GiB/s; GPU cache of 7,865 experts, 14.91 GiB | 23.42 GiB at 2.6-7.1 GiB/s |
| Start to verified readiness | 48.6 s first start, 40.4-40.8 s restarts | 33 s, 17.1-19.4 s |
| Engine working set / private commit, lifetime peak | 52.8 GB / 78.4 GB | 30.3 GB / 55.2 GB |
| System RAM available while serving | 10.7 GB at G10, 9.2 GB minimum | 32.4-33.7 GB |
| Commit available while serving (G10) | **0.72 GB** of 83.6 GB | 13.4 GB of 72.7 GB |
| Cold prefill, 100,030 tokens | 85,079 ms (1.2K tokens/s) | 43,906 ms (2.3K tokens/s) |
| Decode at ~105K context | 56-66 tokens/s | 82-98 tokens/s |
| Scored evaluation | **15/18**: tool-loop 0/3, every other task 3/3 | 17/18: tool-loop 2/3 |
| Median task wall; batch wall | 120.6 s; 2,085 s | 74.7 s; 1,409 s |

The answer is no. All three scored tool-loop attempts and the pilot's fail the same hidden test as the Coder's
failures, each time on its exact-money assertion: the largest account totals 12345678901234567890123456790000
instead of 12345678901234567890123456789012, a precision loss; the task's other three hidden tests pass every time.
Short tracer turns decoded at 50-84 tokens/s. The model fits 64 GiB only as tested: since the Coder's run the commit
limit had grown from 72.7 GB to 83.6 GB (the page file from 4.3 GB to 15.2 GB), and 0.72 GB of commit remained
while serving. After the 128 GB upgrade stock setup streams IQ3_S's KV cache to RAM, which needs the separate
`win11-rtx3090-iq3s-131k-kvstream-strata0.1.31-omp18.4.8` profile; that changes speed, not output.


## Candidate 2 (2026-10-01): stock Strata v0.1.30, stock OMP 18.4.6

Profile `win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`; receipts and scrubbed results under
`releases/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6/`. The boundaries (wall, server, sampler) are the
ones defined for candidate 1 below. The second root reused the first root's model shards (re-hashed) and 15 of its
17 generated files are byte-identical; only the engine binary differs (G26).

### Resources (G10, G21)

| Measure | Candidate 2 | Candidate 1 | Boundary |
|---|---|---|---|
| GPU memory in use while serving | 30,742-30,838 MiB of 32,607 | 30,820-30,836 MiB | sampler |
| Engine (`strata.exe`) working set, lifetime peak | 30.53 GB | 30.53 GB | per-process peak |
| Engine private commit, lifetime peak | 63.35 GB | 63.35 GB | per-process peak |
| System RAM available while serving (minimum per gate run) | 8.5-9.7 GB of 50.6 GB | 9.0-11.1 GB | sampler |
| Commit available while serving | 7.9 GB of 83.9 GB | 8.3 GB | sampler (G10) |
| Integration root on disk | 73.7 GB: models 58.4, Strata data 8.4, runtime 1.1, downloads 0.9, OMP home 0.2, plus 4.7 GB of qualification and evaluation workspaces | 74.2 GB | file sizes (G21) |
| Start to verified readiness | 14.5-15.3 s on restarts; 18.6 s for the root's first start | 14.4-15.9 s; 20.9 s first start | wall |
| Expert load at start | 23.42 GiB at 3.40 GiB/s (first start's log) | 2.68-3.44 GiB/s | server log |

Across 7 server logs and 521 completed requests there was no watchdog stop, out-of-memory, CUDA error or
traceback. The only two engine exits were the deliberate G15 kills; v0.1.30 logs the mid-generation one with its
exit code and last engine line instead of a generic out-of-memory hint.

### Throughput (server-reported)

| Case | Candidate 2 | Candidate 1 |
|---|---|---|
| Cold prefill, 100,030 tokens | 15,588 ms (6.4K tokens/s) | 16,039 ms |
| Cold prefill, 104,810 tokens (near-limit task, first request) | 16,150 ms (6.5K tokens/s) | 16,636 ms for 104,827 |
| Cold prefill after an engine restart, 7,090 tokens | 1,780 ms (4.0K tokens/s) | 1,796 ms for 7,123 |
| Cached continuation, 105,670 tokens with 105,025 reused | 333 ms prompt time | 282 ms |
| Decode, short contexts | 148-206 tokens/s | 142-234 tokens/s |
| Decode at ~105K context | 158-185 tokens/s | 157-158 tokens/s |

v0.1.30's "short prompts up to 28% faster" (chunked expert streaming) did not show on these prompts: the tracer's
~7K-token first request and the 100K-token prefills are within a few percent of candidate 1.

### Agent turns (wall)

| Case | Candidate 2 | Candidate 1 |
|---|---|---|
| Tracer turn 1: read, edit and test with 5-6 tool calls on a ~7K-token prompt | 4.1-7.5 s | 4.1-6.9 s |
| Tracer turn 2: `--continue`, no tools | 1.2-1.3 s | 1.1-1.3 s |
| Prefix reuse on same-session continuations | 12/12 requests reused 6.8K-7.9K tokens | 12/12 |
| Continuation after another session interleaved (A-B-A) | only the shared 6,797-token system prefix reused | 6,830 |

### Restart cost (G15, G16, G20)

- **Engine killed while idle.** The next OMP turn took 17.3 s: about 14 s to reload the engine, a cold re-prefill
  of the whole transcript (7,090 tokens, 1.8 s), then decode.
- **Engine killed mid-generation.** The cut turn ends as an error that quotes the engine's exit code. The next turn
  took 16.1 s on the same path and answered correctly; the second turn reused 7,470 of 7,517 tokens. The reasoning
  loop seen on candidate 1 (2 of 3 trials) did not occur in this single trial.
- **Client restart.** The next turn took 1.2 s, with the live prefix cache intact.
- **Client and full server restart.** The server was ready in 14.6 s, and the next turn took 3.0 s: a re-prefill
  of 7,320 tokens in 1.9 s plus decode.

### Context (G17, G18)

- **Exact server limit:** unchanged, prompt + `max_tokens` + 8 ≤ 131,072 (100,030 accepted with 31,034, refused
  with 31,035).
- Stock OMP 18.4.6 fitted caps of 15,544-24,656 to 104,810-105,670-token prompts; the largest prompt + cap was
  129,997, inside the declared 130,048-token window. No overshoot occurred; the 1,024-token margin stays.
- A single prompt of about 136K tokens is refused explicitly (HTTP 400 surfaced by OMP; no engine work).
- **Compaction:** with the production configuration, a 14-turn session compacted at 111,351 tokens down to 30,014
  (peak engine prompt 105,918) and then finished a typed edit that needed a pre-compaction fact. At the reduced
  12,000-token threshold OMP 18.4.6 compacted twice in 7 turns (at 11,085 and 11,846 tokens) where 18.4.0
  compacted six times, with the same final result.

### Network (G13)

With the launcher's egress guard: 0 non-loopback events out of 3,559 ETW Kernel-Network events attributed to
the OMP and Strata process trees, over a typed tool turn and a compaction turn; OMP's loopback probes of ports
11434, 8080 and 1234 remain. The unguarded run was not repeated on this candidate.

### Coding evaluation (G24)

The same frozen `synthetic-1` set and harness (manifest `3b292b2e…`, no drift), same caps, full Strata server
restart between the continuation phases.

| Task | Verified passes | Task wall per attempt (s) | Peak prompt tokens |
|---|---|---|---|
| bugfix-a | 3/3 | 25.0, 30.8, 50.7 | 8.8K-14.4K |
| bugfix-b | 3/3 | 107.9, 106.3, 61.4 | 14.7K-24.5K |
| multifile-regression | 3/3 | 31.8, 52.5, 29.2 | 9.6K-13.7K |
| tool-loop | 0/3 | 95.2 ✗, 73.4 ✗, 44.6 ✗ | 12.7K-24.8K |
| long-context | 3/3 | 24.8, 24.5, 34.6 | 13.3K-14.8K |
| continuation | 3/3 | 47.1, 47.8, 44.3 | 8.0K-8.5K |

- **Scored result: 15/18 verified passes (0.833)**, against 16/18 for candidate 1. All three failures are
  tool-loop fixes that passed the visible tests but failed the same hidden settlement test (cross-account
  de-duplication of voids); candidate 1 failed that test in two of its three attempts. No attempt timed out,
  aborted, hit a cap or compacted, and there were no protocol errors.
- The batch took 932 s. Task wall time ranged from 24.5 to 107.9 s, with a median of 45.8 s over all 18
  attempts, including verification. Reported output per attempt was 2.9K-15.0K tokens.
- A non-scored pilot before scoring passed 5/6 (tool-loop failed). The harness then ran unchanged.
- **Boundary:** as for candidate 1, the evaluation ran under the host operator's account without an OS sandbox
  (the owner-approved deviation), and there is no comparison with any other runtime or model.

### Second-root install (G26)

`fetch` 47 s (391 MB of OMP, engine and llama.cpp archives downloaded and verified; the two shards reused and
re-hashed), `install` 316 s, first `start` to readiness 18.6 s, the quickstart's non-interactive `launch-omp`
example 7.6 s (the model fixed the sample project), tracer 3/3, `stop` with the GPU back at 0 MiB.

## Candidate 1 (2026-09-30): stock Strata v0.1.27, stock OMP 18.4.0

Profile `win11-rtx5090-coder-iq1m-131k`: stock OMP 18.4.0 and stock Strata v0.1.27 with Qwen3.8-Flash-Next Coder
IQ1_M, a 131,072-token context, INT8 KV, MTP speculation. Measurements were taken on 2026-09-30 (UTC).

Boundaries used below:
- **wall** is a monotonic clock around a whole client action.
- **server** figures are stock Strata's own per-request records (`/metrics`: `prompt_ms`, `decode_ms`, `reused`).
- **sampler** figures are system counters: `nvidia-smi` and `GlobalMemoryStatusEx` every 2 s, plus the per-process
  `K32GetProcessMemoryInfo` lifetime peaks.

A restarted engine with a warm OS file cache is *process-cold, file-cache-warm*. Every figure comes from this
repository's probes; nothing is borrowed from upstream READMEs. Receipts and scrubbed raw results are under
`releases/win11-rtx5090-coder-iq1m-131k/`.

### Resources (G10, G21)

| Measure | Value | Boundary |
|---|---|---|
| GPU memory in use while serving | 30,820-30,836 MiB of 32,607 | sampler |
| GPU expert cache | 12,288 experts, 23.42 GiB | server log |
| Engine (`strata.exe`) working set | 30.0-30.5 GB (peak 30.53 GB) | per-process peak |
| Engine private commit | 62.8-63.3 GB (peak 63.33 GB) | per-process peak |
| Server interpreter (`python.exe`) working set | 0.20 GB | per-process |
| System RAM available while serving | 9.0-11.1 GB of 50.6 GB | sampler, minimum per gate run |
| Commit available while serving | 8.3 GB of 83.9 GB (RAM + page file) | sampler (G10) |
| Integration root on disk | 69.5 GB installed: models 58.4, Strata data 8.4, downloads 1.3, runtime 1.1, OMP home 0.2; plus 4.7 GB of qualification and evaluation workspaces | file sizes (G21) |
| Start to verified readiness | 14.4-15.9 s over every recorded start and restart of the qualified root; 20.9 s for a fresh root's first start (G26) | wall, process-cold, file-cache-warm |
| Expert load at start | 23.42 GiB at 2.68-3.44 GiB/s | server log |

The engine commits about twice its resident memory. The commit limit is RAM plus page file, so this profile needs
a page file on a 47 GiB host. The practical floor observed here is about 34 GiB of available RAM before start,
leaving about 9 GB available and 8.3 GB of commit headroom while serving. Model-file size does not predict the fit.

Across 8 server logs and 629 completed requests there was no watchdog stop, out-of-memory or CUDA error. Stock
Strata v0.1.27 labels every unexpected engine exit as a probable out-of-memory event (Strata#215, fixed in
v0.1.28). The 5 exits observed were 3 deliberate mid-generation kills (G15) and 2 stale-cancel crashes (G14).

### Throughput (server-reported)

| Case | Value |
|---|---|
| Cold prefill, 104,827 tokens | 16,636 ms (6.3K tokens/s) |
| Cold prefill after an engine restart, 7,123 tokens | 1,796 ms (4.0K tokens/s) |
| Cached continuation, 105,429 tokens with 105,040 reused | 282 ms prompt time |
| Decode, short contexts | 142-234 tokens/s (MTP speculation on) |
| Decode at ~105K context | 157-158 tokens/s |

### Agent turns (wall)

| Case | Value |
|---|---|
| Tracer turn 1: read, edit and test with 3-4 tool calls on a ~7K-token prompt | 4.1-6.9 s |
| Tracer turn 2: `--continue`, no tools | 1.1-1.3 s |
| Prefix reuse on same-session continuations | 12/12 requests reused 6.8K-8.2K tokens |
| Continuation after another session interleaved (A-B-A) | only the shared 6,830-token system prefix reused |

### Restart cost (G15, G16, G20)

- **Engine killed while idle.** The next OMP turn took 16-17 s: about 14 s to reload the engine, a cold re-prefill
  of the whole transcript (7.1K tokens, 1.8 s), then decode.
- **Engine killed mid-generation.** The cut turn ends as an error. The next turn took 16.2 s, on the same path. In
  2 of 3 trials, that first post-crash turn ended in an OMP-detected reasoning loop (an explicit error) instead of
  an answer; later turns recovered.
- **Client restart.** The next turn took 1.3 s, with the live prefix cache intact.
- **Client and full server restart.** The server was ready in 14.5 s, and the next turn took 3.1 s: a re-prefill
  of 7,400 tokens in 1.9 s plus decode.

### Context (G17, G18)

- **Exact server limit:** prompt + `max_tokens` + 8 ≤ 131,072. A 100,030-token prompt is accepted with
  `max_tokens` 31,034 and refused with 31,035 (HTTP 400, "requests are never truncated").
- Stock OMP fits `max_tokens` to its estimate of the remaining window. At 104.8K-105.4K-token prompts it sent caps
  of 15,596-24,987; the largest prompt + cap was 130,061. Without a margin, OMP overshot by 21 tokens once and
  Strata refused the request. The integration therefore declares the window 1,024 tokens below the engine's.
- A single prompt of about 136K tokens is refused explicitly (HTTP 400 surfaced by OMP; no engine work).
- **Compaction:**
  - With the production configuration, a long session compacted at 113,383 tokens down to 30,612, and then
    finished a typed edit that needed a fact from before the compaction.
  - At a reduced 12,000-token threshold, 6 compactions ran in 7 turns, with the same result.

### Network (G13)

These counts come from ETW `Microsoft-Windows-Kernel-Network` events attributed to the OMP and Strata process
trees:
- **Without the launcher's egress guard:** 244 packet events to 2 non-loopback HTTPS endpoints (OMP's startup
  model-catalog refresh), plus loopback probes of ports 11434, 8080 and 1234.
- **With the guard:** 0 non-loopback events out of 3,711 attributed events, over a typed tool turn and a
  compaction turn.

### Coding evaluation (G24)

This is the frozen `synthetic-1` set: six original stdlib Python tasks. The verifiers are immutable and run
outside the worktree. Each attempt gets a fresh workspace and a fresh client HOME. Caps per attempt: 900 s, 40
tool calls, and 32,768 output tokens per response. The run used the production launcher, with a full Strata
server restart between the phases of the continuation task.

| Task | Verified passes | Task wall per attempt (s) | Peak prompt tokens |
|---|---|---|---|
| bugfix-a (interval subtraction) | 3/3 | 26.6, 32.6, 26.8 | 8.7K-10.1K |
| bugfix-b (incremental UTF-8 decoding) | 3/3 | 123.5, 79.5, 42.7 | 11.3K-25.7K |
| multifile-regression | 3/3 | 49.0, 67.4, 74.2 | 12.3K-19.0K |
| tool-loop (CSV settlement, CLI, tests) | 1/3 | 85.5 ✗, 48.4 ✗, 106.2 | 13.4K-25.1K |
| long-context (retrieve a policy from a ~300 KB archive, change code) | 3/3 | 27.3, 24.3, 29.2 | 13.2K-15.2K |
| continuation (calibrate, restart client and server, resume) | 3/3 | 60.3, 54.6, 60.0 | 9.3K-11.1K |

- **Scored result: 16/18 verified passes (0.889).** Both failures are tool-loop fixes that passed the visible
  tests but failed one hidden settlement test. No attempt timed out, aborted, hit a cap or compacted, and there
  were no protocol errors: no malformed arguments, orphan or missing results, bad ids, or error/aborted stops.
- The batch took 1,018 s. Task wall time ranged from 24.3 to 123.5 s, with a median of 51.8 s over all 18
  attempts, including verification.
- Reported output per attempt was 3.1K-17.7K tokens.
- The long-context task was solved by searching and reading, not by ingesting the archive (its peak prompt was
  about 15K tokens), so it does not exercise near-limit capacity; G17 does.
- A non-scored pilot, run before scoring, passed 5/6 (tool-loop failed). The harness then ran unchanged.
- **Boundary:** the evaluation ran under the host operator's account without an OS sandbox. This is a recorded
  deviation from the packet, approved by the owner. There is no comparison with any other runtime or model.

### Clean install (G26)

Every `docs/QUICKSTART.md` command ran as written, from a checkout of commit 887ff7d, into a new integration root
on the same host. This was not a fresh OS: Python, Git and the driver were already present.

| Step | Wall |
|---|---|
| `fetch`: download and verify 59.7 GB of pinned artifacts | 608 s |
| `install`: stock `setup.py` from the verified inputs | 352 s |
| `start` to verified readiness (first start of the new root) | 20.9 s |
| `launch-omp` non-interactive example (fixes the sample project) | 8.9 s |
| `tracer --runs 1` (typed tools, protocol and task pass) | 6.3 s |
| `stop` | 3.0 s |

These were identical to the qualified root:
- the 17 generated files (model shards, pack, tokenizer and chat template, MTP layer, engine binaries);
- the shared settings and the normalized server config;
- the pip freeze, Python and the Strata commit.

Only the stock config file differs, because `setup.py` writes the root's absolute paths into it. The runtime
identity hashes that file, so it is specific to each root.
