# Decision (2026-10-08)

Scope: stock OMP → stock Strata on Windows 11, single user per host, local loopback route. Qualified: the fourth
tuple (OMP 18.4.10, Strata v0.1.34, Qwen3.8-Flash-Next Coder IQ1_M, 131,072-token context) on the RTX 5090
(`rtx5090-win-a`), RTX 3090 (`rtx3090-win-a`) and RTX 4090 in stock low-RAM mode (`rtx4090-win-a`). On the RTX PRO
6000 (`rtxpro6000-win-a`), Qwen3.8-Flash-Next IQ3_S with a 131,072-token context is qualified twice: OMP 18.8.0
with Strata v0.1.40.2, and OMP 18.8.3 with Strata v0.1.40.3 plus stock setup's batch slots and conversation
parking. The newest qualified profile is `win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3`.
Each profile keeps its own root and evidence; qualifying a tuple neither repairs nor replaces the earlier ledgers.
No runtime-superiority or default replacement decision follows from integration qualification.

## Update, 2026-10-08: Strata v0.1.40.3 with OMP 18.8.4 remains draft

([MEASUREMENTS.md](MEASUREMENTS.md#three-gpu-drafts-2026-10-08-stock-strata-v01403-stock-omp-1884))

- **The RTX PRO 6000, RTX 5090 and RTX 3090 profiles are drafts awaiting the owner's decision.** The PRO keeps
  IQ3_S, four batch slots, parking and 32K prompt chunks; the other two keep Coder IQ1_M. These ledgers do not
  change which profiles are qualified or current, and no installation or runtime replacement follows.
- **Each latest ledger has 21 pass and 3 not applicable.** G00-G06 record the source, host-free suite and hosted
  CI audits. G10-G20, G21 and G26 pass; G22, G23 and G25 stay not applicable with their capabilities or claims off.
  The PRO's first G16 failure remains recorded beside its passing rerun after the predicate was fixed to count
  executions of `append.py`, not mentions.
- **The coding evaluation still has failures.** The non-scored pilots are 5/6, 5/6 and 6/6; the scored results
  are 15/18, 16/18 and 15/18 on the PRO, 5090 and 3090 respectively. All attempts count, and no task-quality or
  runtime-superiority decision follows from publishing these runs.

## Update, 2026-10-07 (evening): the RTX PRO 6000 qualifies with batch slots and conversation parking

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-with-batch-slots-and-parking-every-gate-2026-10-07-stock-strata-v01403-stock-omp-1883))

- **Strata v0.1.40.3 with OMP 18.8.3 qualifies on the RTX PRO 6000, with three stock setup choices pinned.**
  `--parallel 4` is stock's recommendation for this card: up to four requests decode together, and OMP may send the
  server four at once. `--conversation-cache-mib 8192` parks up to four conversations in host RAM.
  `--prefill auto:32768` reads prompts in 32K chunks. Every applicable gate passed at the first attempt (21 pass;
  G22, G23 and G25 not applicable);
  [ledger](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.3/qualification.json).
- **What it buys, measured.** Four overlapping requests decode 19% faster in total, and each slot's tokens equal
  its solo run. A conversation interleaved with another comes back from its parked or held state instead of being
  read again (G19: 20,669 of 20,698 tokens reused, 0.34 s instead of 3.3 s). Long prompts read 8-24% faster (G17).
  The coding evaluation is unchanged at 16 of 18.
- **What it costs.** 2.9 GB more VRAM in use, 11 GB more engine commit (the parking budget and the slots), and 2 s
  more to readiness. A request alone gains nothing from the slots.
- **Terminal-Bench: 19 of 30 on this profile,** with the OMP 18.8.3 harness (17 of the earlier 28). The earlier PRO
  runs used OMP 18.5.0, so they are context, not a paired comparison: v0.1.40.1 passed 21 (exact McNemar p = 0.73)
  and v0.1.39 19. Trials ran one at a time, so the slots stayed idle. Qualification is about integration
  correctness, not task quality.
- **The v0.1.40.2 profile stays qualified,** and its root is the rollback installation.

## Update, 2026-10-07 (later): the RTX PRO 6000 tuple qualifies, with OMP's speculative compaction off

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-07-stock-strata-v01402-stock-omp-1880))

- **Strata v0.1.40.2 with OMP 18.8.0 qualifies on the RTX PRO 6000.** The owner's rule for a qualification is the
  newest stable release of both components. Every applicable gate passed at the first attempt: 21 pass, and G22,
  G23 and G25 are not applicable. The profile serves IQ3_S at 131,072 tokens with every expert in VRAM;
  [ledger](../releases/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0/qualification.json).
- **The integration turns OMP's speculative compaction off.** Near its compaction threshold OMP 18.8.0 sent the
  engine a background summary. With one sequence and one in-flight request, that held the next turn for 17 s and
  evicted the 105K-token live prefix. The owner held the profile as a candidate until it was fixed. The rendered
  settings now set `compaction.asyncEnabled: false` (OMP still compacts at the threshold), and a host-free test fails
  if the speculation reaches the engine. G17, G18 and G24 then passed again on the PRO, and the near-limit session
  took 20.7 s instead of 50.7 s.
- **Terminal-Bench has not measured this pair.** Its 20 of 28 belongs to Strata v0.1.40.1 with OMP 18.5.0, the
  result that made IQ3_S on v0.1.40.x the PRO's candidate. Qualification is about integration correctness, not task
  quality.
- **The earlier PRO drafts keep their ledgers, with no gate run;** the installed v0.1.39 and v0.1.40.1 roots remain as
  rollback installations.

## Update, 2026-10-07: on Terminal-Bench the largest stock build ties IQ3_S; IQ3_S stays the PRO's model

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-against-the-rtx-4090-2026-10-06-stock-strata-v0139-stock-omp-1850))
Drafts only: no gate ran.

- **UD-Q4_K_XL's higher fidelity bought no task quality.** On 30 Terminal-Bench 2.1 tasks, one attempt each, both
  builds passed 19, and each passed 3 that the other failed. The bar set beforehand for replacing IQ3_S was 4 more
  tasks, so IQ3_S stays and its prompt-speed lead decides.
- **One failure class has two causes, each fixed upstream.** In 3 of the 22 failures (2 with IQ3_S, 1 with
  UD-Q4_K_XL) the last turn ended its reasoning with a complete tool call that v0.1.39 returns as reasoning text. OMP
  retries such a stop, but 18.5.0 drops the retry once the run has restarted, as all three had, so they ended
  mid-task. Strata v0.1.40 and v0.1.40.1 turn such a call into a real one, and OMP 18.5.1 keeps the retry; neither has
  been measured on these tasks.
- **Two tasks fail for any model that leaves its server to OMP.** The benchmark harness runs `omp --print`, and OMP's
  service broker stops its services 3 s after omp exits, before the task's checks connect. Absolute scores here
  understate the model; the paired comparison is unaffected. Stock `OMP_DAEMON_IDLE_GRACE_MS` lengthens that grace
  (scripted check), so a harness can keep the services for every arm without changing what the model sees.

## Update, 2026-10-06 (later): IQ3_S stays the PRO's model; the largest stock build costs prompt speed

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-against-the-rtx-4090-2026-10-06-stock-strata-v0139-stock-omp-1850))
Drafts only: no gate ran.

- **IQ3_S on the PRO passed 55 of the 60 private tasks**, three of its misses 0.99 near-passes, in 0.39x the
  4090's time. It remains the PRO's model.
- **Stock UD-Q4_K_XL fits the PRO's VRAM** (all experts resident) and decodes at 0.85-0.90x IQ3_S. Its prefill is
  0.43-0.73x, so an agent turn on a long cached prompt takes about twice as long (3.1 s against 1.4 s). Whether its
  higher fidelity buys task quality is being measured on a harder, public task set before any profile change.
- **Larger open models that do not fit 96 GB of VRAM are not practical on one card here.** Comparison-only
  llama.cpp runs that spilled experts into system RAM decoded at 10-17 tokens/s, bound by CPU-side expert work.

## Update, 2026-10-06: an RTX PRO 6000 runs IQ3_S 2.2-2.3x faster than the RTX 4090, every expert in VRAM

The RTX PRO 6000 replaced the RTX 4090 in its host and ran the same IQ3_S model on Strata v0.1.39
([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-against-the-rtx-4090-2026-10-06-stock-strata-v0139-stock-omp-1850)).
Draft only: no gate ran.

- **IQ3_S belongs on the PRO.** Decode 258-271 tokens/s at 8K-100K against 115-116, prefill 1.6-1.9x, and time to
  first token at 100K 13.6 s against 25.3 s, with all 24,576 experts in VRAM where the 4090 fetched its cache misses
  over PCIe. It passed all 12 screen tasks (10 on the 4090), one attempt each; the 60-task run comes next.
- **Keep the stock flags.** Stock setup plans the 4090's flags for 96 GB, and `--expert-cache auto` already makes
  every expert resident; about 40 GB stays free for longer contexts or a second model, which would be a new profile.
- **The card's host requirements are firmware, not tuning:** Re-Size BAR off for POST on this board, and the card's
  own power adapter. Sustained agent work held about 450 W and 79 °C on the core with no slowdown.

## Update, 2026-10-05: Strata v0.1.39 decodes faster on the RTX 3090; its hybrid-CPU change shows no clear gain

Strata v0.1.39 with stock OMP 18.5.0 ran beside v0.1.38 on the RTX 3090 and the RTX 4090, same model files, versions
alternating on each card ([MEASUREMENTS.md](MEASUREMENTS.md#strata-v0139-against-v0138-2026-10-05-stock-omp-1850)).
Drafts only: no gate ran.

- **Use v0.1.39 for the next Strata profiles.** On the RTX 3090 it decodes 3-7% (IQ3_S) and 5-10% (Coder) faster
  than v0.1.38 at 8K-100K tokens, with the same flags; prefill is unchanged. On agent work the Coder kept its
  outcomes (42/44 base tasks against 43/44) and took a median 0.84× the time on the tasks both passed; IQ3_S passed
  10 of the 12 screen tasks against 11, within the hard tier's attempt-to-attempt flips.
- **Stock's new `--pool-workers 15` for the RTX 4090 host's hybrid i9-14900K brought 2-4%, within run-to-run
  spread**, not the large gain upstream measured on an i9-14900KF. The profile pins stock's value; no hand tuning.

## Update, 2026-10-04: on the owner's kind of work, Flash-Next beats the 27B

The frozen evaluation cannot rank models: five of its six tasks pass for every model and the sixth fails for every
one. A private 60-task set shaped like the owner's local work now informs model choice: development in a private
TypeScript monorepo, and analysis, spreadsheets, repair, statement programs and judgment over synthetic financial
documents, one attempt per model and task
([MEASUREMENTS.md](MEASUREMENTS.md#the-models-on-the-owners-kind-of-work-2026-10-04-a-private-60-task-set)). It is
comparison evidence only; no gate or ledger changes.

- **The original Flash-Next at IQ3_S is the strongest local model: 58/60**, against 54/60 for the Coder IQ1_M and
  49/60 for Qwen3.8 27B on NInfer. It passed every task the 27B passed and nine more (exact McNemar p = 0.004);
  its lead over the Coder (5 to 1) is within chance at this size.
- **Run IQ3_S, not the Coder, wherever the RAM holds it, coding included.** "For coding the Coder stays the choice"
  (2026-10-02) rested on the frozen evaluation's tie; here IQ3_S passed all 26 development tasks against the
  Coder's 23. The RTX 4090 with 192 GB ran it; the RTX 3090's calibrated 128 GB draft is the same model, not
  measured on this set. It is the slowest arm: on the RTX 4090, a median 1.5-1.9× the 27B's RTX 5090 time.
- **On the RTX 5090, whose 47 GiB cannot hold IQ3_S, the Coder on Strata leads the 27B on NInfer for agent work,
  though not significantly.** Over two attempts of every task (the second all on that GPU; the Coder's first base
  attempts ran on the RTX 3090) it passed 107 of 120 against 99: better on 11 tasks, worse on 5 (sign test p = 0.21;
  mean pass rate 89% against 83%, task-bootstrap 95% interval -0.8 to +14 points), in a median 0.90× of the 27B's
  time per task on the RTX 5090. Each model's two attempts disagree on 9-11 of the 60 tasks. The 27B's malformed tool
  calls returned as text (four of 29 hard attempts in the first round) did not recur in its second; three of the
  Coder's 120 attempts ended in OMP's thinking-loop detector. The 2026-10-03 "keep NInfer" rested on the frozen
  evaluation; switching the production lane is the owner's decision, and NInfer still restores saved sessions after a
  restart where Strata re-reads the transcript.
- **A lead with subagents does not pay off on this work.** Neither lead delegates on its own, with stock prompts or
  when its system prompt says to. Asked in every request to use its subagents, the Coder lead on the RTX 5090
  delegated in 12 of 13 hard tasks, mostly read-only `scout` runs on the RTX 3090, and passed 7 against the 8 it
  passed alone, taking a median 1.54× as long. Run single-model sessions, and ask for subagents in a request only
  when the work splits into independent pieces.

## Update, 2026-10-03: Strata against NInfer — keep NInfer, switch nothing

The first real G25 runs put the fifth-tuple drafts (stock Strata v0.1.38, stock OMP 18.5.0, Coder IQ1_M 131K)
against what each host already runs, through the same frozen evaluation and one pinned OMP binary
([MEASUREMENTS.md](MEASUREMENTS.md#paired-coding-evaluation-against-ninfer-g25)):

- **RTX 5090: keep omp-ninfer v0.10.0.** Strata 15/18, NInfer 14/18, but NInfer was faster: Strata's paired median
  task took 1.39× NInfer's and its summed wall 839 s against 733 s. NInfer decodes faster at the tasks' contexts;
  Strata's 3× faster long-prompt reading and 2.4× faster restart do not make up for it here.
- **RTX 3090: no reason to switch.** 15/18 each with the same three tool-loop failures, paired median ratio 0.98,
  summed wall 1,905 s against 2,028 s. Strata restarts in 25 s against 114 s and reads a 100K prompt in 41 s against
  160 s; NInfer brings saved sessions back after a restart. The RTX 3090 serves no fleet route.
- **RTX 4090 with 192 GB: no reason to switch.** After a memory fix (DDR5-5200 with Intel's default CPU power
  settings; DDR5-5600 failed under load), the Coder against the host's native NInfer v0.6.10 lane: 15/18 each with
  the same three tool-loop failures, paired median ratio 0.98, summed wall 1,133 s against 1,231 s. Strata reads a
  100K prompt in 19 s against 62 s and restarts in 15-18 s against 34-75 s. Unlike on the other hosts, stock
  calibration keeps a lower PCIe share here, worth up to 13% decode (one probe each): the best measured settings are
  calibrated IQ3_XXS (stock setup's model choice, 164-174 tokens/s) for decode, the calibrated Coder for long
  prompts and coding, and the Coder 262K beyond 131K tokens (no cost below 100K). A decode up to 13% faster would
  not bring the 0.98 ratio near the 0.80 that "faster" requires (an estimate; the comparison was not rerun
  calibrated).

Neither frozen claim, more completions or faster joint successes, holds on any GPU, so the condition for
switching a host to Strata (clearly better) is not met.

**Durability: do not port NInfer's.** Stock Strata v0.1.38 already has a native prompt cache, an engine-silence
watchdog and opt-in RAM conversation parking (`--conversation-cache-mib`, `--conversation-cache-slots`: alternating
conversations keep their KV in a bounded host-RAM cache), which covers what NInfer's host KV pool does for one user.
It has no disk-persisted sessions, no Responses `previous_response_id`, and runs one sequence at a time. Porting
NInfer's disk checkpoints would be a large change and would need AGENTS.md's no-durable-engine-state boundary
lifted; with cold restarts of 14-26 s and a 100K re-read of 14 s (RTX 5090) to 41 s (RTX 3090), section 3's
conclusion stands. If parking is wanted, it is a stock flag: a new profile id, not a port.

## Update, 2026-10-03: the fourth tuple qualifies on three GPUs

All 21 applicable gates pass in each fourth-tuple ledger; G22 (images), G23 (remote clients) and G25 (runtime
comparison) are not applicable to these local, text-only profiles. Evidence and scrubbed results:
[RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
[RTX 3090](../releases/win11-rtx3090-coder-iq1m-131k-strata0.1.34-omp18.4.10/qualification.json),
[RTX 4090, low-RAM](../releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.34-omp18.4.10/qualification.json);
figures and measurement boundaries in [MEASUREMENTS.md](MEASUREMENTS.md).

- **G04 passes for the first time on all three GPUs' profiles.** Stock Strata v0.1.34 includes the unfinished-call
  fix shipped in v0.1.31; stock OMP 18.4.10 includes its corresponding fix. A call cut off mid-arguments is refused,
  not executed with partial arguments. No fork or locally patched binary is needed.
- **G15's failures remain recorded, and its probe correction is explicit.** The RTX 5090 failed
  `g15-20261002T025312Z-8c4047` and `g15-20261002T032432Z-3a4126` with the earlier probe. Commit `cb31418`
  changes the recall prompt after interruption to withdraw the interrupted essay first (`RECALL_AFTER_INTERRUPT`);
  it changes neither the engine nor the requirement to recall the transcript's fact on the next turn. The corrected
  probe passed as `g15-20261003T032448Z-de222a`, published on 2026-10-03. The RTX 4090 had already passed and
  passed the corrected repeat, `g15-20261003T032520Z-78f0cc`. The RTX 3090's earlier probe failed once and then
  passed `g15-20261002T032128Z-191f17`; its corrected repeat passed as `g15-20261003T043756Z-122117`. None of this
  is durable engine-state restoration: a restart replays the transcript and cold-prefills it.
- **The RTX 4090's compaction rerun is not a clean first pass.** Its reduced-threshold G18 probe failed once;
  the repeat passed. Both the failed combined receipt `g18l-20261002T023456Z-79336a` and passing
  `g18l-20261002T030838Z-c64d0c` stay in the ledger. Production long-session compaction itself passed both runs.
- **Integration qualification is not a perfect coding score.** The frozen evaluation verified 16/18 attempts on
  the RTX 5090 and 15/18 on each 24 GB GPU. The tool-heavy task scored 1/3, 0/3 and 0/3 respectively; every other
  task scored 3/3. G24 requires complete, independently verified reporting, with failed tasks in the denominator,
  not quality superiority. The RTX 4090's 32 GiB low-RAM fit leaves just 0.44 GB available at its worst sample;
  qualification is for that tested configuration, not a claim of capacity for other workloads.
- **Use the fourth tuple; retain the earlier installations for rollback.** The first and second RTX 5090
  candidates and third-tuple 24 GB profiles keep their original, unqualified ledgers and roots. Fifth-tuple drafts,
  larger-model/context variants and remote-client routes gain no qualification from this result. Durable state,
  multi-tenancy and comparison with other runtimes remain outside this decision.

## Update, 2026-10-03: Strata's own calibration changes nothing for the Coder

Stock setup ends an interactive install by offering its calibration (`tools/calibrate.py`, default yes); `--yes`
installs and the guarded install skip it, so every earlier measurement ran with the engine's defaults. Run unchanged
on each installed root, the stock tool keeps every default for the Coder on the RTX 5090, the RTX 4090 (low-RAM)
and the RTX 3090: the qualified profiles already are Strata's calibrated configuration. Only IQ3_S on the RTX
3090's Gen3 x8 link keeps `--pcie-frac 0.20 --spec-min-p 0.70`. Pinned as a draft and measured beside the
uncalibrated root, it decodes 4-5% faster up to 8K tokens, no faster from 32K, and scores the same 15/18, so the
IQ3_S configuration for work outside coding is the calibrated draft. Profiles may now pin such a stock result
(`strata.calibration`, a new profile id that install applies with stock `calibrate.apply`); setup never calibrates
on its own. Evidence: `docs/MEASUREMENTS.md`.

## Update, 2026-10-03: longer contexts for the Coder on the RTX 3090

The Coder's trained 262K context is the long-context configuration to use on the 128 GB RTX 3090: it decodes as at
131K up to 100K tokens, 81-89 tokens/s at 200K-250K, and a cold 250K-token prompt takes 2.3 min. Stock setup's
experimental yarn scaling to 524K also runs (a cold 512,000-token prompt: 6.7 min, then 72 tokens/s) at 3-5% lower
decode below 100K, but it changes the model at every position and its coding evaluation is still owed, so it stays
a draft for work that needs more than 262K. Evidence: `docs/MEASUREMENTS.md`.

The earlier updates and original three decisions below are retained as dated history, not the current blocker list.

## Update, 2026-10-02: which model the RTX 3090 should run with 128 GB

After its RAM upgrade (128 GB of DDR4-3200) the RTX 3090 ran three models with stock Strata v0.1.36 and stock OMP
18.4.12 as draft profiles, measured for variant selection only (`scripts/perf_probe.py` and the frozen evaluation;
no gate ran, every ledger stays draft): the Coder IQ1_M, the original model's IQ3_S, and Unsloth's experimental
UD-Q4_K_XL with every expert in RAM. Evidence: `docs/MEASUREMENTS.md`.

- **The most capable model the RAM unlocks is the original Flash-Next at IQ3_S**, which Strata's notes say matches
  the full BF16 model. It now decodes 93-96 tokens/s (56-66 at 64 GiB), within 10% of the Coder, because stock setup
  streams its KV cache to RAM; prefill stays at half the Coder's (88 s against 43 s for a 100K-token prompt).
- **For coding the Coder stays the choice.** On the frozen evaluation IQ3_S scores the Coder's 15/18 and fails the
  same exact-money assertion, with a 29% longer median task. Candidate profiles keep the Coder IQ1_M; the IQ3_S
  drafts are the configuration to use when work outside coding matters. Its 262K draft (the model's trained
  context) still decodes 84 tokens/s at 250K tokens; a cold 256K-token prompt takes about 4 min.
- **UD-Q4_K_XL is not worth running on this host.** It runs at half IQ3_S's speed, restarts in 2-2.5 min (past the
  frozen evaluation's 120 s restart hook, which ended its batch), and gained nothing on the tasks it completed.
- **More RAM leaves the Coder unchanged**: the same flags, and a 100K-token cold prefill within 2% (43.2 s against
  44.0 s).

## Update, later on 2026-10-01: the third tuple on two 24 GB hosts

Stock Strata v0.1.31 and stock OMP 18.4.8 ran the complete real-host sequence on an RTX 3090 host with 64 GiB of
RAM and on an RTX 4090 host with 32 GiB of RAM (stock low-RAM mode), as draft profiles in fresh roots, without
touching the RTX 5090 or its other tenant. Evidence: `releases/win11-rtx3090-coder-iq1m-131k-strata0.1.31-omp18.4.8/`,
`releases/win11-rtx4090-coder-iq1m-131k-lowram-strata0.1.31-omp18.4.8/` and `docs/MEASUREMENTS.md`. The decisions
below stand for the RTX 5090 candidate; this update changes what blocks qualification and where the route can run.

- **G04 is the only failing gate on both hosts, and now only OMP's half is open.** Strata v0.1.31 no longer
  presents an unfinished call as complete (Strata#231); stock OMP 18.4.8 still runs it. A binary built from
  can1357/oh-my-pi#13868's head answers it with an error result and writes nothing; #13868 was merged on
  2026-10-01, after OMP 18.4.9 was published, so no release carries it yet. The suite now holds a cut-off call to
  the contract it already applied to a length cut: the call never runs, and the client may fail the turn or answer
  with an error. An OMP release carrying that fix will turn the composed reproducer into an unexpected success;
  qualification then needs that release in a profile and a host-free G04 run, plus the real-host gates on
  whichever host the profile names.
- **Every other gate passes on both hosts.** Evaluation 17/18 on the RTX 3090 and 15/18 on the RTX 4090 (the
  tool-heavy task 2/3 and 1/3; 4 of 12 across the four scored batches of this model). Decode runs at 79-113 tokens/s
  (RTX 3090) and 104-126 tokens/s (RTX 4090) against 148-206 on the RTX 5090; a 100K-token cold prefill takes 44 s
  and 21 s against 16 s.
- **The route no longer needs the RTX 5090.** Its costs move to the choice of host: slower prefill on the RTX 3090
  (PCIe Gen3 x8), and on the 32 GiB RTX 4090 almost no RAM reserve (0.37 GB available at the worst sample). Both
  hosts are getting more RAM (128 GB and 192 GB); the RTX 4090's low-RAM-off profile
  (`win11-rtx4090-coder-iq1m-131k-strata0.1.31-omp18.4.8`) is ready for that, and the RTX 3090 profile is unchanged
  by it (its setup choices do not depend on RAM above 35 GiB). Which host the route should live on is the owner's
  choice; until then the RTX 5090 profile stays the current candidate.
- **The larger original model does not fix the task the Coder fails.** An exploratory run of Strata's
  best-quality size of the original Flash-Next (IQ3_S) on the RTX 3090 scored 15/18 with the tool-heavy task
  0/3, every attempt on the same exact-money assertion, at about half the Coder's speed and with 0.72 GB of commit
  to spare on 64 GiB. Every candidate profile keeps the Coder IQ1_M.

## 1. Integration readiness: working candidate, one upstream blocker left

**Passed.** These capabilities are supported within the limits stated. The last row is host-free; every other row
ran on the real host on 2026-10-01.

| Gate | Result |
|---|---|
| G10 | Pinned identity on the actual host (deep re-hash of every artifact), and exclusive GPU use |
| G11 | Typed read/glob/edit/bash tool loops through the real stock client: 3/3 tracer runs |
| G12 | Live prefix reuse inside a session: 12/12 continuations |
| G13 | Loopback only, with authentication on every model and control route including `/status`. The launcher fails closed on a missing key. All model roles, including compaction, route locally; 0 non-loopback events with the guard. |
| G14 | Cancellation while generating, while queued, failed tools and transport loss: the next turn is valid. **The queued-cancel engine crash of the first candidate is fixed** (Strata v0.1.28+; `g14q` passes 3/3 scenarios). |
| G15, G16 | Continuing after an engine, client or full server restart from OMP's own transcript: replay with a full re-prefill, never state restoration |
| G17 | The 131,072 window: exact server limit, near-limit tool turns, explicit overflow |
| G18 | OMP compaction at a reduced threshold, and at the production threshold in a long session |
| G19 | Interleaved sessions, resume and branch |
| G20 | Controlled lifecycle with no orphans, the first candidate's root and the host's unrelated state preserved |
| G21 | A measured resource fit: no watchdog stop, OOM or CUDA error in 521 logged requests |
| G26 | Every `docs/QUICKSTART.md` command into a second root, the documented `launch-omp` example included; 15 of 17 generated files byte-identical to the first root, only the engine differs |
| G00–G03, G05, G06 | Source audit, pins, client isolation, real OMP 18.4.6 against scripted streams and the real v0.1.30 frontend, lifecycle edge cases, public CI |

**Failed, release-blocking (upstream defect; details in `docs/UPSTREAM.md`).**

- **G04.** When the model's turn ends inside a tool call, Strata v0.1.30 still reports `tool_calls` with closed
  partial arguments, and OMP 18.4.6 still executes the truncated call: a partial file write happens and the run
  exits 0. No supported setting avoids it. Fixes are proposed for both halves (Strata#231, planned by the
  maintainer for v0.1.31; can1357/oh-my-pi#13868, open).

**Still worked around in this integration.**

- Stock OMP fetches its public model catalog at every start. The launcher's proxy guard stopped this in
  observation (first candidate, unguarded trace), but it is not enforcement.
- The declared window stays 1,024 tokens below the engine's. OMP 18.4.4+ has its own 64-token headway; the margin
  was kept rather than re-tested.

**Not supported.** Images (G22), remote clients (G23), comparative claims (G25), durable engine state and
multi-tenant use.

**Verdict.** The route works end to end for single-user local coding and is one upstream fix away from
qualification: G04 needs Strata#231 (or equivalent) **and** oh-my-pi#13868 (or equivalent) in stock releases,
then a third candidate with G04 requalified host-free and the affected real-host gates rerun. An explicit
acceptance of the truncated-tool-call risk by the owner would be the only other way to call it qualified.

## 2. Usefulness: keep as an optional local coding backend

- **Observed outcome.** 15/18 verified passes on the bounded six-task evaluation: five tasks 3/3, the tool-heavy
  settlement task 0/3 (every attempt passed the visible tests and failed the same hidden test). The first
  candidate scored 16/18 with the same task at 1/3; with three attempts per task the difference is noise, not a
  regression signal. There were no protocol errors, timeouts or aborts. Median task wall time was 46 s, including
  tools and verification.
- **Why it is useful.** It covers bug fixes, a multi-file regression, retrieval from a large archive, and
  continuation across a client and server restart; it now also survives a cancelled queued request.
- **Costs** (unchanged in substance from the first candidate).
  - The RTX 5090 is fully occupied: 30,742-30,838 of 32,607 MiB of VRAM.
  - The engine holds about 30.5 GB of RAM resident at peak and commits about 63 GB, which needs a page file on a
    47 GiB host. About 8.5-9.7 GB of RAM stays available while serving.
  - 69 GB of disk per candidate root (the second root shares nothing with the first on disk; the shards were
    copied).
  - About 15 s to start or to restart the engine.
  - One engine serves one request at a time (FIFO).
  - Operationally: the G04 defect, the egress guard, and the need to release the GPU from any other tenant.
- **Recommendation.** Keep it as an optional backend for local, private, single-user coding sessions. Do not make
  it a default or a replacement for anything until G04 is fixed upstream. The evaluation is a small smoke of
  usefulness, not a benchmark. No quality threshold was set in advance, and none is claimed.

## 3. Further investment in engine-state durability: not justified now

Restart pain was measured again and is unchanged:
- An engine reload takes about 14 s.
- Replaying a transcript costs a cold prefill at about 4K tokens/s for small prompts and 6.4K tokens/s at 100K
  tokens: about 2 s for a typical 7K-token coding session and about 16 s at the largest prompts that fit.
- Client restarts keep the live cache.
- Continuation after a full server restart passed 3/3 in the evaluation and in G16.

The one failure class left is an upstream protocol defect, not missing state. A durable engine-state design would
save at most those seconds per restart, at a large correctness and maintenance cost.

**Recommendation.** Do not start a durability subsystem. Spend the next effort on:
1. Landing the two G04 fixes upstream (Strata#231, oh-my-pi#13868) and the reproducible-setup fix (Strata#324).
2. A third candidate on the releases that carry them, requalifying G04 (host-free) and the affected real-host
   gates with the sequence in `docs/OPERATIONS.md` ("Requalifying a new tuple").
3. Asking OMP for an offline switch for the catalog refresh (can1357/oh-my-pi#10934).

Revisit durability only if real use shows long sessions restarting often enough for re-prefill time to matter.
