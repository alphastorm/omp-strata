# Measurements

Host **rtx5090-win-a**: Windows 11 Pro, RTX 5090 32,607 MiB (driver 610.88), 47.15 GiB RAM, a 31 GB page file,
a 16-core AVX-512 CPU and NVMe storage. Successive stock tuples were measured with the same model
(Qwen3.8-Flash-Next Coder IQ1_M), 131,072-token context, INT8 KV and MTP speculation. The fourth tuple qualifies on
this host and the two 24 GB hosts; after its RAM upgrade the RTX 3090 also ran larger models to choose its
configuration, the fifth tuple's drafts were compared with the hosts' NInfer installations, a private task set
shaped like the owner's work compared the models themselves, and Strata v0.1.39 was compared with v0.1.38 on the
same cards. Newest figures come first; earlier sections are kept unchanged as dated history.

## Strata v0.1.39 against v0.1.38 (2026-10-05): stock OMP 18.5.0

Draft profiles `win11-rtx3090-iq3s-131k-strata0.1.39-omp18.5.0`, `win11-rtx3090-coder-iq1m-131k-strata0.1.39-omp18.5.0`
and `win11-rtx4090-iq3s-131k-strata0.1.39-omp18.5.0`, each installed by the guarded install into its own root beside
its 0.1.38 root, with the same model shards (hard links); no gate ran and every ledger stays draft. Against 0.1.38
only the engine changes, except on rtx4090-win-a: its i9-14900K has 8 performance and 16 efficiency cores, so stock
setup v0.1.39 adds `--pool-workers 15` (#642; the engine's own default is one worker per physical core but the
host's, 23 here). rtx3090-win-a's CPU has no efficiency cores. `scripts/perf_probe.py` ran the versions alternately
on each card within an hour, each from a fresh server start (rtx3090-win-a: 0.1.39, 0.1.38, 0.1.38, 0.1.39;
rtx4090-win-a: 0.1.39, 0.1.38, 0.1.39, 0.1.38).

| Decode, tokens/s, mean of 2 runs: 0.1.38 → 0.1.39 | 8K | 32K | 64K | 100K |
|---|---|---|---|---|
| rtx3090-win-a, IQ3_S 131K | 85.1 → 89.1 | 85.8 → 88.4 | 82.8 → 88.4 | 83.4 → 87.0 |
| rtx3090-win-a, Coder IQ1_M 131K | 99.5 → 106.8 | 99.7 → 109.5 | 99.0 → 104.0 | 101.0 → 111.3 |
| rtx4090-win-a, IQ3_S 131K (0.1.39 with `--pool-workers 15`) | 111.4 → 116.2 | 113.6 → 116.4 | 111.5 → 116.3 | 110.6 → 115.0 |

- **On rtx3090-win-a 0.1.39 decodes 3-7% faster with IQ3_S and 5-10% with the Coder.** At 11 of 12 depth points every
  0.1.39 run beat every 0.1.38 run. Prefill and time to first token move by 1-3%, within the runs' spread. The release
  notes claim +2.5-7% decode.
- **On rtx4090-win-a the hybrid-CPU worker count shows no clear gain.** 0.1.39 with stock's 15 workers averaged 2-4%
  faster, but each version's two runs differ by up to 11 tokens/s and the ranges overlap at every depth. #642 reports
  165 / 116 against 106 / 84 tokens/s for 15 against 23 workers on an i9-14900KF; this IQ3_S profile does not
  reproduce that.
- **Both rtx4090-win-a versions ran 12-15% below the same 0.1.38 profile two days earlier** (126-136 tokens/s,
  below), on the same boot and the same DDR5-5200 setting. The alternating runs compare the versions; the host's
  absolute speed had drifted.
- Both installs passed the guarded install's checks of stock setup's generated config, including the planned
  `--pool-workers 15` on rtx4090-win-a, and each server started in 30-46 s.

## The models on the owner's kind of work (2026-10-04): a private 60-task set

The frozen `synthetic-1` evaluation cannot rank models: five of its six tasks pass for every model tried and the
sixth (tool-loop) fails for every one on the same exact-decimal assertion, so 15/18 against 14/18 is one attempt.
For model choice it is replaced by a private task set written for the owner's two kinds of local work, kept outside
the repository with its results; only aggregates appear here. `scripts/eval_taskset.py` ran it
([OPERATIONS.md](OPERATIONS.md#comparing-models-on-a-private-task-set)).

- **Tasks.** Each is a prompt, a starting workspace, hidden expected material, a reference solution and a verifier,
  and each passed the fairness check before any model ran: the untouched start fails its verifier and the reference
  passes, both through the agents' sandbox. Development (26), in a private TypeScript monorepo with its full
  toolchain: 6 replays of real commits, 14 reimplementations of a removed function against hidden tests, and 6
  features from the repository's roadmap, each checked by 30-37 hidden tests. Private data (34), on synthetic
  statements, workbooks and planning documents only: 8 analysis, 8 spreadsheet and 8 diagnosis-and-repair tasks, 5
  programs over a year of multi-format statements with thousands of records, and 5 judgment tasks across
  capital-account and planning documents. The roadmap features, statement programs and judgment tasks (16) are the
  hard tier, added when the first base results showed a ceiling; a separate solver that saw only the agent's inputs
  passed each hard private-data task. Pass means every verifier check is exact.
- **Arms.** Qwen3.8 27B on omp-ninfer v0.10.0, the RTX 5090's production lane (Responses API); the original
  Qwen3.8-Flash-Next at IQ3_S on stock Strata v0.1.38 (draft profile), RTX 4090 with 192 GB; the Flash-Next Coder
  IQ1_M on stock Strata v0.1.38, base tier on the RTX 3090 and hard tier on the RTX 5090. One attempt per model and
  task, through one pinned stock OMP 18.5.0 binary on the macOS client under `sandbox-exec`, each engine reached
  over an SSH tunnel the runner owns. Budgets: 1,350 s and 120 tool calls (private data), 1,800 s and 150
  (development; 2,700 s and 200 for two long replays), 2,700 s and 250 (hard tier).

| Measure | Flash-Next IQ3_S | Flash-Next Coder IQ1_M | Qwen3.8 27B (NInfer) |
|---|---|---|---|
| Passed, all 60 tasks | **58** | **54** | **49** |
| Base tier (44) | 44 | 43 | 39 |
| Hard tier (16) | 14 | 11 | 10 |
| Development (26) / private data (34) | 26 / 32 | 23 / 31 | 20 / 29 |
| Hard tier: roadmap features (6) / statement programs (5) / judgment (5) | 6 / 5 / 3 | 4 / 3 / 4 | 3 / 4 / 3 |
| Median agent time, base / hard | 271 s / 1,010 s (RTX 4090) | 329 s (RTX 3090) / 510 s (RTX 5090) | 151 s / 599 s (RTX 5090) |
| Output tokens, all attempts | 2.06M | 2.29M | 2.18M |

| Pair, all 60 tasks | Both pass / first only / second only / neither | Exact McNemar p |
|---|---|---|
| IQ3_S, 27B | 49 / 9 / 0 / 2 | 0.004 |
| IQ3_S, Coder | 53 / 5 / 1 / 1 | 0.22 |
| Coder, 27B | 46 / 8 / 3 / 3 | 0.23 |

- **Flash-Next beats the 27B on this work.** IQ3_S passed every task the 27B passed and nine more, four of them in
  the hard tier; p = 0.004 holds after a Bonferroni correction for the three comparisons. The Coder's lead over the
  27B (8 to 3) and IQ3_S's over the Coder (5 to 1) point the same way but are within chance at this size.
- **The base tier is at the ceiling for both Flash-Next models; the hard tier separates them.** Every hard
  private-data failure, in all three arms, was a near miss: 2 to 96 of 376-1,847 exact checks failed (for example
  a copied mark written `557.80` where the task requires the canonical `557.8`, or the funds or quarters of one
  summary), which the all-exact rule counts as a failure.
- **Two of the 27B's eleven failures ended at the serving layer.** In two hard development attempts the 27B wrote a
  tool call with a duplicated parameter; NInfer returned it as message text, so OMP took it for the final answer and
  the attempt ended mid-task. The rest are wrong results, near misses and one tool-call budget. The Coder lost one
  base attempt to OMP's repetition detector (a 76-character cycle repeated 15 times; retries are off in this
  configuration) and one hard attempt to the tool-call budget.
- **In the first attempts, on the same GPU the Coder on Strata finished hard tasks faster than the 27B on NInfer**:
  a median 0.79× of its time over the eight hard tasks both passed (4,012 s against 4,873 s summed), the reverse of
  the frozen evaluation's 1.39×. Hard attempts reach about 110K tokens of context in every arm (base attempts a
  median 58-70K); consistent with, though not isolated as, Strata's 3-4× faster long-prompt reading measured below.
  Every other time compares different GPUs: IQ3_S on the RTX 4090 took a median 1.53× (hard) and 1.85× (base) the
  27B's RTX 5090 time on the tasks both passed.
- **Two IQ3_S attempts lost their SSH tunnel to the RTX 4090 mid-stream; both reruns passed.** The first had been
  scored as a model failure, because the check after the attempt silently reopened the tunnel; the runner now counts
  a tunnel that closed during an attempt as an infrastructure fault and reruns it (the second case). No solo
  attempt reached its wall-clock budget.
- **A lead delegates only when each request asks it to, and then gained nothing here.** Fleet arms ran the hard
  tier with OMP's `task` and `wait` tools and every stock agent type routed through `task.agentModelOverrides` to
  IQ3_S (RTX 4090) or the Coder (RTX 3090). With stock prompts the 27B lead on the RTX 5090 made no subagent call
  in 13 attempts; told to delegate in an appended system prompt, it made none in 3 more, and neither did the Coder
  lead in a partial attempt. With a request to use its subagents appended to every task, the Coder lead on the RTX
  5090 delegated in 12 of 13 attempts (34 subagent runs: 29 `scout`, 4 `reviewer`, 1 `task`) and passed 7 against
  the solo Coder's 8 on those tasks (2 and 3 discordant), at a median 1.54× the solo time (12,404 s against
  8,192 s; one attempt ran into its 2,700 s budget after writing a passing result). Two of its attempts ended in
  OMP's repetition detector, against one in the solo Coder's 60. The runs stopped short of 16 tasks when the RTX
  3090 was needed elsewhere.
- **Single attempts are noisy on the hard tier.** The stock fleet arm is in effect a second attempt of the 27B:
  5 of its 13 outcomes differ from the solo attempt (2 and 3 each way). Two more of its attempts ended on a tool
  call returned as text, four of the 27B's 29 hard attempts in all. The repeats below measure this directly.
- **Limits.** One attempt per task for IQ3_S, two for the Coder and the 27B (below); the arms ran on different
  GPUs except the Coder's and the 27B's RTX 5090 attempts; the agent wrote the tasks from the owner's repository
  and documents, and their difficulty is its estimate.

**A second attempt on one GPU (2026-10-05).** The Coder (Strata) and the 27B (NInfer) each ran all 60 tasks again
on the RTX 5090 with the same budgets and binary; the Coder's first base attempts had run on the RTX 3090. Per task
the two attempts give a pass count of 0, 1 or 2; they are not pooled as extra samples.

| Two attempts per task | Flash-Next Coder IQ1_M (Strata) | Qwen3.8 27B (NInfer) |
|---|---|---|
| Passed, first / second attempt | 54 / 53 | 49 / 50 |
| Tasks passed in both / one / neither attempt | 49 / 9 / 2 | 44 / 11 / 5 |
| Base tier (44): both / one / neither | 41 / 3 / 0 | 39 / 4 / 1 |
| Hard tier (16): both / one / neither | 8 / 6 / 2 | 5 / 7 / 4 |
| Hard tier passes, first / second attempt | 11 / 11 | 10 / 7 |
| Agent time on the RTX 5090, per-task means summed | 18,712 s | 20,823 s |

- **On one GPU the Coder still leads, within chance.** Per task it did better on 11 tasks and worse on 5 (44 equal;
  sign test p = 0.21); mean pass rate 89.2% against 82.5%, a 6.7-point difference with a task-bootstrap 95% interval
  of -0.8 to +14.2 points. Its time per task was a median 0.90× the 27B's (0.87× on the hard tier); on the 40 tasks
  every attempt of both passed, the sums are equal (8,236 s against 8,250 s; median 0.93×).
- **9 of the Coder's and 11 of the 27B's 60 tasks changed outcome between attempts** (6 and 7 of the 16 hard
  tasks). One attempt per task cannot separate configurations a few tasks apart.
- **Failure modes in the second attempts.** The 27B returned no tool call as text this time (two of its first
  attempt's eleven failures did); one attempt overran NInfer's 131,072-token context once, continued, and ended as
  a near miss. Two Coder attempts ended in OMP's thinking-loop detector (cycles of 79 and 378 characters repeated 13×
  and 3×; retries are off), three of its 120 attempts in all, and one ended when the model wrote a malformed
  `<tool_call>` as its final text. The rest of both arms' failures are wrong results and near misses.

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
| rtx4090-win-a, 191.7 GiB | original model IQ3_XXS, 131K, INT8 KV, `--kv-resident 32768` | measured below, after a memory fix (DDR5-5200) |
| rtx3090-win-a, 127.7 GiB | original model IQ3_XXS, 131K, INT8 KV, `--kv-resident 32768` | measured below |

### Strata v0.1.38 throughput by root (perf probe)

| Root | Decode at ~60 / 8K / 32K / 64K / 100K tokens | Prefill, 8K-100K | Cold 100K prompt to first token | MTP acceptance |
|---|---|---|---|---|
| rtx5090-win-a, Coder IQ1_M 131K | 176 / 179 / 172 / 167 / 175 tokens/s | 6.3-7.6K tokens/s | 14.1 s | 0.76-0.83 |
| rtx3090-win-a, Coder IQ1_M 131K | 87 / 100 / 99 / 101 / 90 | 2.1-2.6K | 41.2 s | 0.75-0.82 |
| rtx3090-win-a, IQ3_XXS 131K (stock choice) | 78 / 100 / 110 / 95 / 98 | 1.4-1.6K | 69.2 s | 0.80-0.89 |
| rtx3090-win-a, IQ3_S 131K | 67 / 88 / 86 / 84 / 84 | 1.1-1.3K | 85.3 s | 0.85-0.88 |
| rtx4090-win-a, Coder IQ1_M 131K | 127 / 142 / 145 / 149 / 144 | 4.7-5.6K | 19.0 s | 0.75-0.83 |
| rtx4090-win-a, IQ3_XXS 131K (stock choice) | 123 / 159 / 155 / 151 / 155 | 4.4-5.1K | 21.7 s | 0.83-0.89 |
| rtx4090-win-a, IQ3_S 131K | 95 / 136 / 134 / 132 / 126 | 3.9-4.4K | 24.9 s | 0.84-0.90 |
| rtx4090-win-a, Coder IQ1_M 262K | 131 / 147 / 143 / 150 / 130 | 4.6-5.5K | 19.3 s | 0.77-0.89 |
| rtx4090-win-a, IQ3_S 262K | 77 / 116 / 115 / 117 / 114 | 3.8-4.4K | 25.1 s | 0.83-0.88 |
| rtx4090-win-a, Coder IQ1_M 131K, calibrated (`--pcie-frac 0.20 --spec-min-p 0.70`) | 137 / 153 / 152 / 164 / 142 | 4.7-5.6K | 19.2 s | 0.85-0.95 |
| rtx4090-win-a, IQ3_XXS 131K, calibrated (`--pcie-frac 0.00`) | 139 / 172 / 174 / 171 / 164 | 4.3-5.0K | 21.6 s | 0.81-0.85 |

- **The RTX 5090 Coder on v0.1.38**: decode 167-179 tokens/s (v0.1.34: 148-206), cold 100K prompt 14.1 s (about
  16 s).
- **On the RTX 3090 the stock choice decodes like the Coder and prefills at 60% of its rate.** IQ3_XXS is the
  original model (twice the Coder's experts). IQ3_S, the best-quality original size, decodes 84-88 tokens/s against
  93-96 on v0.1.36 with the same generated flags (one probe each).
- **On the RTX 4090 with 192 GB the stock choice is the fastest decoder**: IQ3_XXS 151-159 tokens/s from 8K to 100K
  tokens, the Coder 142-149 with 7-10% faster prefill. With every expert in RAM the Coder decodes 144 tokens/s at
  100K tokens, against 86-118 in the 32 GiB low-RAM mode's near-limit requests (v0.1.34, G17); the cold 100K prompt
  barely moves (19.0 s against 20.9 s), so RAM never limited prefill.
- **At 262K the Coder costs nothing below 100K and keeps decoding at 125-131 tokens/s at 200K-250K**; a cold
  256,000-token prompt takes 53.9 s. IQ3_S at 262K decodes 105-117 tokens/s, 10-15% below its 131K root, and its cold
  256K prompt takes 67.6 s.
- **Calibration adds decode on this host and nothing in prefill** (one probe each, details below): IQ3_XXS 6-13% at
  every depth, now 164-174 tokens/s from 8K to 100K; the Coder 5-10% up to 64K and nothing at 100K. The best RTX 4090
  settings measured: calibrated IQ3_XXS 131K for decode, the calibrated Coder 131K for long prompts and coding (the
  evaluated model), the Coder 262K when a session needs more than 131K tokens.

### Client-side speed, same prompts on both engines

`scripts/probe_g25_speed.py`, one prompt set per host (filler at the nominal depth plus one instruction; 3 runs per
depth, output capped at 512 tokens, medians). TTFT is dispatch to the first streamed token of any kind; the output
rate is completion tokens over the time after it.

| Host | Engine | TTFT at ~0 / 8K / 32K / 100K tokens | Output tokens/s at the same depths |
|---|---|---|---|
| rtx5090-win-a | NInfer v0.10.0 | 0.12 / 2.55 / 10.96 / 42.77 s | 250 / 204 / 189 / 124 |
| rtx5090-win-a | Strata, Coder | 0.21 / 1.34 / 4.55 / 14.08 s | 145 / 149 / 135 / 137 |
| rtx4090-win-a | NInfer v0.6.10 | 0.15 / 3.69 / 15.84 / 62.48 s | 134 / 129 / 120 / 97 |
| rtx4090-win-a | Strata, Coder | 0.34 / 2.01 / 6.37 / 19.37 s | 124 / 128 / 121 / 117 |
| rtx3090-win-a | NInfer v0.6.2 | 0.23 / 9.42 / 40.79 / 160.37 s | 81 / 70 / 69 / 58 |
| rtx3090-win-a | Strata, Coder | 0.77 / 4.64 / 13.53 / 40.90 s | 86 / 88 / 87 / 79 |

- **Strata reads long prompts 3-4× faster on every GPU** (3.2× on the RTX 4090 at 100K). NInfer prefills about 2.4K
  tokens/s on the RTX 5090, 1.6K on the RTX 4090 and 0.65K on the RTX 3090 at 100K.
- **NInfer generates faster on the RTX 5090 up to 32K** (250 against 145 tokens/s on a short prompt) and slower at
  100K; on the RTX 4090 the two stay within 8% of each other up to 32K and Strata is 21% faster at 100K. NInfer's 512
  tokens were all reasoning (the provider's low effort), Strata's 289-381 visible answer tokens, so output lengths
  differ; the rates are not a matched benchmark.
- The RTX 4090's first pair asked NInfer for the RTX 3090 lane's model id and got HTTP 404 on every sample; its
  NInfer half was rerun with the lane's id (`qwen3.8-27b`) on the same prompt set after the comparison. The probe now
  checks the endpoint's model list before any sample.

### Paired coding evaluation against NInfer (G25)

The frozen `synthetic-1` evaluation through one pinned stock OMP 18.5.0 binary on both arms, six exclusive windows
per host in the order Strata, NInfer, NInfer, Strata, Strata, NInfer, after a six-attempt pilot per arm (Strata 5/6
and NInfer 5/6 on the RTX 5090, 5/6 and 4/6 on the RTX 4090, 5/6 and 3/6 on the RTX 3090). Every engine start was
cold. Runs `g25-rtx5090-20261003f`, `g25-rtx4090-20261003a` and `g25-rtx3090-20261003e`; exported plans, window
aggregates, paired summaries and G25 receipts are in each release's `evidence/` and `receipts/`. All three ran on the
hosts' normal accounts, not a restricted evaluation account.

| Measure | RTX 5090: Strata | RTX 5090: NInfer v0.10.0 | RTX 4090: Strata | RTX 4090: NInfer v0.6.10 | RTX 3090: Strata | RTX 3090: NInfer v0.6.2 |
|---|---|---|---|---|---|---|
| Verified completions | **15/18** | **14/18** | **15/18** | **15/18** | **15/18** | **15/18** |
| Pairs: both pass / Strata only / NInfer only / neither | 14 / 1 / 0 / 3 | | 15 / 0 / 0 / 3 | | 15 / 0 / 0 / 3 | |
| Median task wall, all attempts | 36.4 s | 29.1 s | 47.4 s | 49.2 s | 85.5 s | 88.7 s |
| Median task wall, verified passes | 34.7 s | 27.2 s | 46.1 s | 46.1 s | 83.0 s | 83.4 s |
| Summed task wall, all 18 attempts | 839 s | 733 s | 1,133 s | 1,231 s | 1,905 s | 2,028 s |
| Median Strata/NInfer ratio over jointly passed pairs | 1.39 (14 pairs) | | 0.98 (15 pairs) | | 0.98 (15 pairs) | |
| Output tokens, all attempts | 117K | 137K | 115K | 133K | 127K | 126K |
| Cold start to ready | 14.4-14.9 s | 34.7-35.1 s | 14.8-17.5 s | 34.3-74.8 s | 24.2-26.1 s | 113.2-115.8 s |
| GPU memory while serving | 30,836 MiB | 29,472 MiB | 23,329 MiB¹ | 23,162 MiB¹ | 23,443 MiB | 22,970 MiB |
| GPU power limit | 600 W (default) | 600 W (default) | 500 W¹ (card maximum; default 450 W) | 500 W¹ | 370 W (default) | 300 W (NInfer's qualified limit) |
| Lowest available RAM | 8.2 GiB | 8.3 GiB | 153.2 GiB | 165.3 GiB | 91.2 GiB | 106.2 GiB |

¹ Sampled outside the RTX 4090's comparison windows: Strata's memory during its G10 run on the same root, NInfer's
memory and both power limits during the speed probe and calibration right after the comparison. NInfer's 4090 lane
manages no power cap.

| Task: passes, median wall | RTX 5090: Strata | RTX 5090: NInfer | RTX 4090: Strata | RTX 4090: NInfer | RTX 3090: Strata | RTX 3090: NInfer |
|---|---|---|---|---|---|---|
| bugfix-a | 3/3, 29.7 s | 2/3, 29.7 s | 3/3, 40.4 s | 3/3, 36.9 s | 3/3, 67.7 s | 3/3, 62.9 s |
| bugfix-b | 3/3, 86.1 s | 3/3, 18.5 s | 3/3, 80.1 s | 3/3, 105.8 s | 3/3, 159.4 s | 3/3, 103.4 s |
| multifile-regression | 3/3, 44.8 s | 3/3, 30.8 s | 3/3, 46.5 s | 3/3, 46.1 s | 3/3, 72.3 s | 3/3, 94.0 s |
| tool-loop | 0/3, 65.5 s | 0/3, 70.7 s | 0/3, 100.0 s | 0/3, 98.0 s | 0/3, 111.8 s | 0/3, 195.6 s |
| long-context | 3/3, 26.7 s | 3/3, 22.0 s | 3/3, 43.4 s | 3/3, 40.6 s | 3/3, 83.2 s | 3/3, 93.4 s |
| continuation | 3/3, 32.2 s | 3/3, 25.9 s | 3/3, 36.3 s | 3/3, 46.0 s | 3/3, 87.7 s | 3/3, 78.3 s |

- **Neither frozen claim holds on any GPU.** Higher completion needs three more Strata passes; faster needs a
  median ratio of at most 0.80 and no greater Strata total. The RTX 5090's 15/18 against 14/18 is one bugfix-a
  attempt; tool-loop failed every attempt on both engines on every GPU.
- **On the RTX 5090 NInfer is faster on these tasks**: Strata's paired median took 1.39× NInfer's, its summed wall
  1.14×. The largest gap is bugfix-b, where the Coder wrote 12.6K output tokens (median) against NInfer's 3.4K; on
  the other tasks the outputs are similar and Strata took 0-45% longer (tool-loop 7% less), in line with NInfer's
  faster decode up to 32K.
- **On the RTX 4090 and RTX 3090 the two are even** (paired median 0.98 on both; Strata 8% and 6% less summed
  wall). On the RTX 4090 Strata was faster on bugfix-b, where NInfer wrote 12.3K output tokens (median) against
  8.2K, and on continuation; NInfer was 2-9% faster on bugfix-a, long-context and tool-loop. On the RTX 3090 Strata
  was faster on multifile-regression, long-context and tool-loop, NInfer on the bugfix tasks and continuation;
  NInfer ran at its own 300 W cap there, Strata at the card's 370 W.
- **Strata restarts 2.4× (RTX 5090), 2-5× (RTX 4090) and 4.5× (RTX 3090) faster.** NInfer's RTX 4090 start took
  34 s in one window and 60-75 s in the other two. No number includes NInfer restoring a saved session or Strata
  re-reading a transcript; switching engines on the RTX 5090 also waited for Docker's VM to return RAM (86-91 s from
  NInfer to Strata).
- NInfer serves Qwen3.8 27B with a 131,072-token context (BF16 KV on the RTX 5090, INT8 on the RTX 4090 and RTX
  3090); Strata the Coder IQ1_M at 131,072 with INT8 KV.

### RTX 4090 with 192 GB: the setting that holds

Host rtx4090-win-a now has 4 × 48 GB of dual-rank DDR5 (191.7 GiB reported), two DIMMs per channel. Its first
setting, DDR5-5600 with voltages on Auto and the board's own CPU power profile, failed under load: four bugchecks in
a night (0xEF; 0x1A twice; and 0x1A 0x403, whose page-table and PFN parameters differ in a single bit), one reset
while idle, wrong SHA-256 results for an unchanged 29.6 GB model shard, and a TLS decryption error in a download.
The owner then changed one BIOS setting at a time; each setting ran the same 25-minute check (three SHA-256
re-hashes of both Coder shards, y-cruncher v0.8.7's stress suite over 160 GB, and a scan for WHEA hardware
errors):

| DRAM | CPU power profile | Result |
|---|---|---|
| 5600, DRAM and memory-controller voltages 1.30 V, SA 1.20 V | board profile | memory training failed twice |
| 5200, voltages Auto | board profile | fail: y-cruncher's SNT test errored on one E-core after 27 s |
| 5200, voltages Auto | Intel Default Settings (PL1 253 W) | **pass**: all hashes, all 8 stress tests, no WHEA error |
| 5600, voltages Auto | Intel Default Settings | fail: one wrong hash and the same E-core error |

The kit's EXPO profile (DDR5-6000, 1.40 V) never trains with four DIMMs; Intel validates this CPU at DDR5-3600 with
two dual-rank DIMMs per channel. The host runs at **DDR5-5200 with Intel Default Settings**, and every RTX 4090 figure
in this section was taken there: seven root installs with their probes, the paired comparison and calibration kept it
loaded for 3 h 20 min with no bugcheck and no WHEA error (its only WHEA record is the informational one logged at
every boot). The same E-core failed first in both failing settings; if it fails again, the CPU is the next suspect.

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
| rtx4090-win-a, Coder 131K, 192 GB (v0.1.38) | 0.55, 0.5, 23 | `--pcie-frac 0.20 --spec-min-p 0.70` | 116.7 → 138.5 (+18.6%) | 147 s |
| rtx4090-win-a, IQ3_XXS 131K, 192 GB (v0.1.38) | 0.55, 0.5, 23 | `--pcie-frac 0.00` | 98.9 → 129.5 (+31.0%) | 196 s |

- **For the Coder on the RTX 5090, the low-RAM RTX 4090 and the RTX 3090, the configuration measured everywhere
  else in this file already is the calibrated one.** With 192 GB the RTX 4090 keeps a lower PCIe share for both
  roots measured.
- **PCIe share matters most, and only where experts miss the GPU.** Single-sweep decode at shares 0 / 0.20 / 0.35 /
  0.55 / 0.75: RTX 3090 Coder 91 / 96 / 84 / 76 / 66 tokens/s (94 at its 0.13), RTX 3090 IQ3_S 67 / 68 / 55 / 42 /
  36 (66 at 0.13), RTX 4090 low-RAM Coder 114 / 114 / 119 / 120 / 118, RTX 4090 192 GB Coder 137 / 139 / 134 / 114
  / 106 and IQ3_XXS 133 / 131 / 116 / 100 / 87, RTX 5090 169-170 at every share.
- **Fewer CPU workers were slower** on both 24 GB hosts (RTX 3090 Coder 9 / 6 / 4 workers: 92.2 / 88.2 / 81.7;
  RTX 4090 low-RAM 23 / 15 / 12: 113.8 / 109.5 / 107.2; with 192 GB IQ3_XXS 131.1 / 127.4 / 124.7) and made no
  difference for the 192 GB RTX 4090's Coder (134.6 / 136.5 / 135.3) or on the RTX 5090 (169.6 at 15, 10 and 8).
- These are the stock tool's short-prompt rates, not comparable with the perf probe's.

**Calibrated against uncalibrated on the RTX 4090 with 192 GB.** Drafts
`win11-rtx4090-coder-iq1m-131k-calibrated-strata0.1.38-omp18.5.0` and
`win11-rtx4090-iq3xxs-131k-calibrated-strata0.1.38-omp18.5.0` pin the kept settings; each was installed in its own
root by stock setup with stock `calibrate.apply` and probed (throughput table above). Decode: IQ3_XXS 6-13% faster
at every depth, the Coder 5-10% faster up to 64K and level at 100K; the Coder's MTP acceptance rises from 0.75-0.83
to 0.85-0.95 with the 0.70 draft floor. Prefill and the cold 100K prompt do not move (19.2 s against 19.0 s, 21.6 s
against 21.7 s). The uncalibrated roots were probed about three hours earlier on the same boot, not straight
after; gains under about 5% are inside run-to-run spread (the RTX 3090's two uncalibrated IQ3_S probes differed by
up to 5.6%).

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
