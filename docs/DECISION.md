# Decision (2026-10-14)

Scope: stock OMP → stock Strata on Windows 11, single user per host, local loopback route. Qualified and current on
all three hosts: stock Strata v0.1.44.1 with stock OMP 18.10.1 on the RTX PRO 6000 at the model's trained
262,144-token context (`rtxpro6000-win-a`; Qwen3.8-Flash-Next IQ3_S with every expert in VRAM, plus stock setup's
batch slots, conversation parking and 32K prompt chunks), on the RTX 5090 at 131,072 (`rtx5090-win-a`;
Qwen3.8-Flash-Next Coder IQ1_M), and stock Strata v0.1.43.1 with OMP 18.10.1 at the trained 262,144-token context
on the RTX 4090 + RTX 3090 pair (`rtx3090-win-a`;
Qwen3.8-Flash-Next IQ3_S, stock layer split, pipeline windows 2 and 8 GiB conversation parking, no batch slots). The current profiles are
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1`,
`win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1` and
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1` (display on the RTX 4090). Their qualified rollbacks are
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1`,
`win11-rtx5090-coder-iq1m-131k-strata0.1.43.1-omp18.10.1` and
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43-omp18.10.1`,
with the same models, contexts and display placement. Earlier history stays qualified: the PRO and RTX 5090
profiles on v0.1.43 with OMP 18.10.1; each host's same 262K or 131K profile on Strata v0.1.42 with OMP 18.8.9,
then on the pair,
`win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9` keeps the same display placement;
the earlier `win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9` requires moving the display back to the RTX 3090.
On the PRO and RTX 5090, earlier history stays
qualified: on the PRO, Strata v0.1.41 with OMP 18.8.6 and the same choices at 262,144 tokens, then at 131,072
tokens, then Strata v0.1.40.3 with OMP 18.8.4, then OMP 18.8.3, and before it OMP 18.8.0 with Strata v0.1.40.2; on
the RTX 5090, Strata v0.1.41 with OMP 18.8.6 and the same Coder IQ1_M, then Strata v0.1.40.3 with OMP 18.8.4, then
the fourth tuple (OMP 18.4.10, Strata v0.1.34, Coder IQ1_M), which also remains the qualified record of the RTX 4090
in stock low-RAM mode (`rtx4090-win-a`). The single-card RTX 3090 profiles,
`win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4` and the fourth tuple's, stay qualified for single-card RTX
3090 hosts, but are not rollbacks on `rtx3090-win-a` while both cards are installed: those profiles name GPU 0,
now the RTX 4090. Each profile keeps its own root and evidence; qualifying a tuple neither repairs nor replaces the
earlier ledgers. No runtime-superiority or default replacement decision follows from integration qualification.

## Update, 2026-10-14: Strata v0.1.44.1 with OMP 18.10.1 qualifies on the PRO and RTX 5090; the pair stays on v0.1.43.1

- **The owner qualified the PRO and RTX 5090 profiles and selected them as current.** Ask answered on
  2026-10-14 at approximately 15:30Z: "Qualify PRO, 5090, route; pair stays 0.1.43.1".
  Each ledger has 21 pass and 3 not applicable (G22, G23 and G25, with those capabilities or claims off),
  the manifests have no blockers, and `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.44.1-omp18.10.1/qualification.json).
- **Their v0.1.43.1 + OMP 18.10.1 profiles are the qualified rollbacks.** Stock setup plans, model pins,
  engine flags and host floors are unchanged; each release keeps its own root and ledger. No earlier receipt
  is inherited or replaced, and task failures remain counted.
- **The RTX 4090 + RTX 3090 pair stays qualified and current on v0.1.43.1 with OMP 18.10.1.** Its
  v0.1.44.1 release is not qualified: the automatic layer split moves from layers 0-31 / 32-47 to 0-44 / 45-47
  on the RTX 4090 / RTX 3090. Measured back to back on the same host, decode falls from 184-206 to 148-154 tok/s
  and prompt reading to 0.52-0.77x; 100K-token TTFT is 55.0 s against 28.6 s. Its v0.1.43 rollback is unchanged.
  [Current pair ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1/qualification.json).
- Qualification is integration correctness, not a claim that every coding task passes, runtime superiority,
  or a default-runtime replacement decision. The Mac route requires its own independent G23 qualification.

## Update, 2026-10-13: the Mac Studio client route qualifies for the PRO's v0.1.43.1 profile

([REMOTE.md](REMOTE.md))

- **The owner qualified `client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1` as the Studio's current route.** Stock
  OMP 18.10.1 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1` through an SSH local
  forward owned by the foreground `launch-omp`. The independent ledger has G23 passing, the manifest has no
  blockers, and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1/qualification.json).
- **G23 passed from the Mac Studio client on 2026-10-13 at `d2fac61`.** Missing key refused before launch,
  wrong key refused with 401, health RTT 5.2-13.5 ms and stream TTFT 0.191 s through the tunnel. A tunnel drop
  failed the turn in flight with the transcript intact; the nonce was recalled after tunnel reopen (0.76 s),
  client restart (0.91 s) and verified server restart (1.39 s, changed server instance). A one-turn route smoke
  answered `ROUTE OK` (operator run context). TTFT includes server work, not SSH-only overhead.
- **`client-rtxpro6000-262k-strata0.1.43-omp18.10.1` is its rollback**, pinned to the PRO's v0.1.43
  262K rollback. Its G23 on 2026-10-12 recorded RTT 4.6-5.3 ms, TTFT 0.195 s, tunnel reopen 1.41 s, client
  restart 1.79 s and server restart 2.18 s. The 0.1.42 262K route and 0.1.41 131K route remain earlier
  qualified history. Every route keeps its own root, identity and ledger and inherits no server evidence.

## Update, 2026-10-13: Strata v0.1.43.1 with OMP 18.10.1 qualifies on all three hosts

([MEASUREMENTS.md](MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-13-stock-strata-v01431-stock-omp-18101))

- **The owner qualified all three profiles and selected them as current.** Each ledger has 21 pass and
  3 not applicable (G22, G23 and G25, with their capabilities or claims off), and
  `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43.1-omp18.10.1/qualification.json),
  [RTX 4090 + RTX 3090, 262K and parking](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43.1-omp18.10.1/qualification.json).
- **Only stock Strata's engine/archive and source pin move, to v0.1.43.1 (`a0116b2`).** Stock OMP 18.10.1
  (`5d0aaff`), the model pins, llama.cpp archive, Python lock, stock setup plans, engine flags and host floors
  are unchanged from v0.1.43. G00 records the quoted `</tool_call>` fix (#2026), fenced JSON tool-call recovery
  (#2037), prompt-loan fix (#2090), warning-only PLE direct-read probe (#1984), Windows watchdog disk-read
  allowance, pinned bounce buffers (#1996) and low-VRAM warning (#2065). All these Qwen3.8-Flash-Next packs
  carry the n-gram table. Batch-slot refusal handling (#1994) reaches only the PRO's four slots; parking
  progress (#2049) reaches the PRO and pair. Windows NVIDIA decode defaults remain unchanged. Upstream reports
  answers byte-identical to v0.1.43 apart from a quoted `</tool_call>`; that is an upstream report, not a
  measured answer-parity result from these runs.
- **All three hosts passed every measured gate in their first full run at `d2fac61`.** The PRO scored 15/18
  (tool-loop 0/3), against v0.1.43's 16/18 (1/3); its pilot passed 6/6 against 4/6, without the earlier OMP
  thinking-loop abort. The RTX 5090 scored 15/18 (tool-loop 0/3) and pilot 5/6, unchanged. Its full G18
  (g18 + g18l) passed the first time, with five reduced-threshold compactions; the rollback's original failed
  G18, rate probes and passing full rerun remain recorded.
- **The pair's G10 stage order is complete (`kept_1576`, both cards in configured order).** Scored 15/18
  against v0.1.43 run 2's 16/18: multifile-regression 2/3 and tool-loop 1/3; pilot 5/6 on both. The failed
  multifile-regression attempt records one malformed-arguments counter despite OMP exiting 0 and its verifier
  passing; the evaluator counts that attempt as unsuccessful. Client execution failures are zero in the new
  scored batches and pilots. Protocol counters are zero except that one pair scored attempt; qualification
  retains it, rather than claiming every counter or coding task passed.
- **Timing remains bounded run evidence, not a runtime-superiority claim.** The PRO's scored batch took
  555 s against 590 s. The RTX 5090 took 858 s against 658 s while doing more work
  (315 versus 277 tool calls, 154,887 versus 107,725 reported output tokens); batch wall per reported output
  token is 5.5 versus 6.1 ms, not isolated decode latency. The pair's reduced G18 took 125.4 s with six
  compactions against 44.7 s with one; G16/G21 readiness remains 54.7/55.0 s on both tuples. G26 first-start
  wall is 65.747 s; the runner's restart before G16 is about 70 s (about 69 s on v0.1.43 run 2), a different
  boundary from G16's verified-readiness metric. No new file-cache cause is inferred.
- **Hosted CI on PR #26 passed 26/26 at `d2fac61`.**
  [38328220748](https://github.com/alphastorm/omp-strata/actions/runs/38328220748) is the G06 audit's run.
  Each host's v0.1.43 + OMP 18.10.1 profile is its rollback; v0.1.42 and earlier qualified profiles keep their
  own roots and ledgers as history. The Mac Studio route followed in its own same-day G23 update above;
  local ledgers qualify no client route.
  Qualification is integration correctness, not task quality or a default-runtime replacement decision.

## Update, 2026-10-12: the Mac Studio client route qualifies for the PRO's v0.1.43 profile

([REMOTE.md](REMOTE.md))

- **The owner qualified `client-rtxpro6000-262k-strata0.1.43-omp18.10.1` as the Studio's current route.** Stock
  OMP 18.10.1 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1` through an SSH local
  forward owned by the foreground `launch-omp`. The route's independent ledger has G23 passing, its manifest has no
  blockers, and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.1.43-omp18.10.1/qualification.json).
- **G23 passed from the same Mac Studio client on 2026-10-12**, in one operator window on the PRO whose other GPU
  tenant yielded and was restored. The run refused a missing key before launch and a wrong key with 401, measured
  health RTT 4.6-5.3 ms and stream TTFT 0.195 s through the tunnel, failed the turn in flight when the tunnel
  dropped while preserving the transcript, and recalled the nonce after tunnel reopen (1.41 s), client restart
  (1.79 s) and verified server restart (2.18 s). A one-turn `launch-omp` through the route answered as asked. TTFT
  includes server work; this is not an SSH-only overhead claim.
- **`client-rtxpro6000-262k-strata0.1.42-omp18.8.9` is the route's rollback**, with the PRO's v0.1.42 262K
  profile; `client-rtxpro6000-strata0.1.41-omp18.8.6` stays qualified for the PRO's earlier 131K profile. Each
  route keeps its own ledger and inherits no server evidence.
- **`fix(remote)`:** with bindings that match the route, a `--remote` naming anything but the bound SSH alias now
  fails with that reason instead of the false "private bindings do not match the public route identity".

## Update, 2026-10-12: Strata v0.1.43 with OMP 18.10.1 qualifies on all three hosts

([MEASUREMENTS.md](MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-12-stock-strata-v0143-stock-omp-18101))

- **The owner qualified all three profiles and selected them as current.** Each ledger has 21 pass and
  3 not applicable (G22, G23 and G25, with their capabilities or claims off), and
  `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.43-omp18.10.1/qualification.json),
  [RTX 4090 + RTX 3090, 262K and parking](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.43-omp18.10.1/qualification.json).
- **Stock Strata v0.1.43 (`7695859`) and stock OMP 18.10.1 (`5d0aaff`) replace only the upstream pins.**
  Each release's G00 source audit records unchanged model pins, llama.cpp archive, Python lock and stock setup
  plan. The pair's host RAM floors are 86 GiB total and 78 GiB available at start, following stock setup's
  conversation-cache tip; its v0.1.42 262K profile had retained its 131K predecessor's 78/66 GiB floors.
  On Windows/NVIDIA, v0.1.43 keeps v0.1.42's decode defaults; G00 records the NaN guard, parallel expert reads,
  tail-skip change and request-timing fixes, not a runtime-superiority claim. For this provider the audited
  host-free multi-turn/tool/reasoning/forced-compaction capture has byte-identical OMP request bodies on
  18.10.1 and 18.8.9; that is a bounded capture, not a claim about every OMP request.
- **The PRO passed every measured gate in one run at `f6fa4d0`.** Scored evaluation 16/18, unchanged from
  v0.1.42; pilot 4/6 against 5/6. The pilot failed tool-loop and one bugfix-b attempt: the latter ended on OMP's
  thinking-loop detector, a client-side abort, not an engine failure. Both remain counted.
- **The RTX 5090's first run at `f6fa4d0` passed every measured gate except G18.** Its final fact-retention
  reply ended at `CODE: KEEP` with a normal stop, although its reasoning named the whole code. G00 records
  repeated G18 probes outside qualification runs: v0.1.43 passed 4/5 then 10/10; v0.1.42 passed 5/5 then 9/10,
  failing the same way. Both rates are 14/15, a pre-existing behavior of this IQ1_M model on this gate, not
  a new-release failure rate. One full G18 rerun (g18 and g18l) at `8bb1d54` passed and is the newest receipt;
  the failed receipt stays. Scored evaluation 15/18 (tool-loop 0/3) against v0.1.42's 16/18; pilot 5/6 on both.
- **The pair's first run at `f6fa4d0` failed G10-G21 and G26 on an integration admission error.** Lifecycle
  admitted multi-GPU stage-order inference only for v0.1.42 and reported the engine degraded: "startup stage
  order unavailable". `967086e` reviewed v0.1.43's unchanged stock `gpu_list`, `layer_split_value` and
  `ordered_gpus` digest and admitted it; a real start parses complete, layers 0-31 on the RTX 4090 and 32-47 on
  the RTX 3090. A host-free test now requires every multi-GPU profile to pin a reviewed release. Run 2 at
  `967086e` passed every measured gate, scored 16/18 against v0.1.42's 15/18, pilot 5/6 and quickstart pass.
  Both runs' receipts stay published; the newest receipt wins, without erasing the first run.
- **The pair's slower restart readiness is a measured host file-cache effect, not an engine change.** Receipts
  record 54.7-55.0 s against v0.1.42's 40.7-43.0 s. The operator's inspection of private engine startup logs
  records every start from G15 onward reading the 51.1 GiB expert pack unbuffered at 2.33-2.95 GiB/s, versus
  7.33-8.02 GiB/s through the Windows file cache before G15. The v0.1.42 root also read unbuffered on 2 of its
  12 starts on 2026-10-11. These are engine-log observations, not G21 load-rate metrics; the logs stay private,
  and no cause for the cache eviction is claimed. Single-GPU G16 readiness is unchanged within these runs:
  PRO 20.6 → 20.1 s, RTX 5090 12.1 → 11.6 s.
- **Hosted CI on PR #24 passed at each implementation checkpoint.**
  [38212474606](https://github.com/alphastorm/omp-strata/actions/runs/38212474606) at `f6fa4d0`,
  [38288518084](https://github.com/alphastorm/omp-strata/actions/runs/38288518084) at `967086e`, and
  [38294442014](https://github.com/alphastorm/omp-strata/actions/runs/38294442014) at `9729fb7`.
  Besides the stage-order fix, `9729fb7` makes `pull_run.py` refuse a requalify log naming more than one run.
- **Each host's v0.1.42 + OMP 18.8.9 profile is its rollback.** Earlier qualified profiles keep their own roots
  and ledgers as history. The Mac Studio client route followed the same day in its own update (above).
  Qualification is integration correctness, not task quality or a runtime-superiority decision.

## Update, 2026-10-12: the Mac Studio client route qualifies for the PRO's current 262K profile

([REMOTE.md](REMOTE.md))

- **The owner qualified `client-rtxpro6000-262k-strata0.1.42-omp18.8.9` as the Studio's current route.** Stock
  OMP 18.8.9 reaches `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9` through an SSH local
  forward owned by the foreground `launch-omp`. The route's independent ledger has G23 passing, its manifest
  has no blockers, and `verify_release.py --require-ready` passes.
  [Ledger](../releases/client-rtxpro6000-262k-strata0.1.42-omp18.8.9/qualification.json).
- **G23 passed twice from the same Mac Studio client on 2026-10-11.** Both runs refused a missing key before
  launch and a wrong key with 401, recorded stream TTFT 0.196 s through the tunnel, failed the turn in flight
  when the tunnel dropped while preserving the transcript, and recalled the nonce after tunnel reopen
  (0.78-0.80 s), client restart (0.72-0.79 s) and verified server restart (1.35-1.48 s). TTFT includes server work,
  not an SSH-only overhead measurement. No new host run or receipt was needed for this qualification.
- **The 0.1.41 route remains qualified for the PRO's 131K rollback profile.**
  `client-rtxpro6000-strata0.1.41-omp18.8.6`, its server profile and both routes' pins and receipts stay unchanged.
  Each server retains its independent qualification; neither route qualifies a fleet or another client platform.

## Update, 2026-10-11: the pair qualifies at 262K with stock conversation parking

- **The owner selected 262K plus parking as current on `rtx3090-win-a`.** The new
  `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9` ledger has 21 pass and
  3 not applicable (G22, G23 and G25); `verify_release.py --require-ready` passes.
  [Ledger](../releases/win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.1.42-omp18.8.9/qualification.json).
- **One root, one raw canonical run, no inherited receipts.** The unchanged runner completed install, start,
  G10-G21, the frozen evaluation and G26 on the profile's probe installation, whose fingerprint and generated
  files match. G26's install/start/QUICKSTART/tests all pass in that same summary. Stock flags and gate tolerances
  did not change; the RTX PRO 6000 remains the default candidate.
- **Only context and stock conversation parking change from the 131K display-on-RTX-4090 profile.** The same
  pins, layer split and pipeline windows 2 run at 262,144 tokens with `--conversation-cache-mib 8192`; no batch
  slots, calibration or prefill-chunk override. G19 restored 20,672 tokens after an intervening conversation,
  with a 491 ms follow-up. This is not an exact-output fidelity claim: the initial strict token-parity probe
  failed and a diagnostic live repeat itself differed. Those results remain separate from qualification.
- **Failures remain counted.** Pilot 5/6, scored 15/18, tool-loop 0/3; its exact-money verifier failures remain
  in the denominator. G24 passed the complete reporting experiment, not every coding task. Pre-G16 status
  returned 1, the runner restart returned 0 and G16 passed. The closing census found the root stopped, no
  engine or listener, and GPU memory back to 182/0 MiB.
- **The qualified 131K display-on-RTX-4090 profile is the rollback.** Its root and ledger stay unchanged.

## Update, 2026-10-11: the pair qualifies with the display on the RTX 4090 (131K rollback)

- **The owner qualified `win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9`.** It is now the 131K rollback on `rtx3090-win-a`; its ledger has 21 pass and 3 not applicable (G22, G23 and G25), and `verify_release.py --require-ready` passes. Ledger:
  [RTX 4090 + RTX 3090, display on RTX 4090](../releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-disp4090-strata0.1.42-omp18.8.9/qualification.json).
- **Only display placement changes.** Pins, IQ3_S at 131,072 tokens, stock layer split and pipeline windows 2 stay
  unchanged. The RTX 4090 is display-attached; the RTX 3090 is not. The original startup refusal at 1,601 MiB of
  display-GPU memory remains recorded; no ownership guard or tuning flag changed.
- **Failures remain in the evidence.** The continuation's degraded pre-G16 status was recovered by the runner
  restart, then G16 passed. Its first G26 receipt failed because that raw summary had no install row. A later
  install/start/quickstart/stop run on the same root passed G26 in one summary with the unchanged manifest
  runtime identity; no raw summaries were combined. The scored evaluation was 14/18, pilot 5/6, against 15/18
  and 6/6 on the display-on-RTX-3090 predecessor; all failed attempts count.
- **The predecessor remains qualified, not current.** Rollback to the display-on-RTX-3090 pw2 profile requires
  restoring that display placement. Single-card RTX 3090 profiles still do not apply while both cards are installed.

## Update, 2026-10-11: Strata v0.1.42 with OMP 18.8.9 qualifies on the RTX PRO 6000 and RTX 5090

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-at-262k-and-rtx-5090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889))

- **The owner qualified both profiles.** Each ledger has 21 pass and 3 not applicable (G22, G23 and G25, with their
  capabilities or claims off), and `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.42-omp18.8.9/qualification.json).
- **Only Strata and OMP change, and every measured gate passed on its first run.** The model pins, the llama.cpp
  archive, the Python lock and the stock setup plans are the v0.1.41 profiles', which are now their rollbacks. All
  three hosts' current profiles are on this tuple.
- **The coding evaluation is within one attempt of the v0.1.41 profiles:** scored 16/18 on both cards (17/18 on the
  PRO's v0.1.41 profile, 15/18 on the RTX 5090's), pilot 5/6 on both and the tool-loop task at 1/3 on both.
  Qualification is about integration correctness, not task quality.
- **The ledgers' speed and resource figures are unchanged:** 100K-token cold prefill 12.6 s on the PRO and 13.8 s on
  the RTX 5090, GPU peaks within 205 MiB of the v0.1.41 profiles. v0.1.42's new decode default, the route tail skip,
  does not apply on either card: both hold every expert in VRAM, and the PRO also runs batch slots. A comparison-only
  probe found prefill unchanged on both cards and decode unchanged on the PRO and, up to 32K tokens, on the RTX 5090;
  at 64K and 100K the RTX 5090 decoded 2-3% slower, within the variation of fifteen rounds.
- **The Studio's current route now pins this 262K v0.1.42 profile.** The new route's own ledger records two G23
  passes; the qualified 0.1.41 route stays with the PRO's 131K rollback profile (2026-10-12 update above).

## Update, 2026-10-11: the pair with the display on the RTX 3090 qualifies (predecessor)

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-every-gate-2026-10-11-stock-strata-v0142-stock-omp-1889))

- **The owner qualified the pair's pipeline-windows profile.** Its ledger has 21 pass and 3 not applicable (G22
  images, G23 remote clients and G25 runtime comparison, which compares single-GPU profiles only), and
  `verify_release.py --require-ready` passes. Ledger:
  [RTX 4090 + RTX 3090](../releases/win11-rtx3090-rtx4090-iq3s-131k-pw2-strata0.1.42-omp18.8.9/qualification.json).
- **Stock layer split, plus stock's pipeline windows 2.** Stock Strata v0.1.42 with stock OMP 18.8.9 runs
  Qwen3.8-Flash-Next IQ3_S at 131,072 tokens across both cards (`--gpus all`, `--layer-split auto`,
  `--pipeline-windows 2`; profile field `strata.pipeline_windows`), without batch slots. The RTX 4090 (GPU 0) runs
  layers 0-31; the desktop-driving RTX 3090 (GPU 1) runs layers 32-47 and the head. The 2026-10-10 measurements
  found pipeline windows 2 decoding 9-13% faster than the plain split, with prefill unchanged.
- **Every measured gate passed on its first run.** G10-G21, G24 and G26 passed in one requalify run on a fresh
  root (2026-10-11, 01:01-01:56Z), with model shards linked from the measurement root; this was G26's second root.
  G10 and G20 record both cards completely, and `start` passed its check for stock's decode-capable pipeline line.
- **The scored coding evaluation matches the RTX 3090 alone's first IQ3_S ledger:** 15/18, with tool-loop 0/3
  as on that Strata v0.1.31 ledger. The non-scored pilot was 6/6. Qualification is about integration correctness,
  not task quality; all attempts and their failures count.
- **At that qualification there was no earlier two-card rollback.** The qualified single-card RTX 3090
  profiles name GPU 0, now the RTX 4090; single-card `start` checks only that GPU 0 is free and would run there,
  although `doctor` reports the model mismatch. Those profiles stay qualified for an RTX 3090 host with one card.
  The pair's Coder IQ1_M, IQ3_XXS, plain IQ3_S and calibrated slots4-tips profiles stay drafts.

## Update, 2026-10-10: the RTX PRO 6000 qualifies at 262K context

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-at-262k-every-gate-2026-10-10-stock-strata-v0141-stock-omp-1886))

- **The owner qualified the 262K RTX PRO 6000 profile.** Its ledger has 21 pass and 3 not applicable (G22, G23 and
  G25, with their capabilities or claims off), and `verify_release.py --require-ready` passes. Ledger:
  [RTX PRO 6000, 262K](../releases/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json).
- **Only the context changes.** Stock setup's plan at 262,144 tokens, the model's trained context, sets
  `--max-context 262144` and keeps KV streaming, four batch slots, parking and 32K prompt chunks; OMP is given
  261,120 tokens and the RAM floor at start rises from 72 to 74 GiB. The 131K profile with the same tuple is its
  rollback.
- **G18 first failed on a fixture sized for 131K windows.** Its production long session was a fixed 20 documents,
  which peaked at 162,071 tokens, under this window's 221,952-token compaction threshold, so OMP never compacted.
  The gate fixtures now follow the profile's window; the rerun passed G17 (a 211,806-token session) and G18
  (compaction at 222,868 tokens), and the failure stays in the ledger. Every other gate passed on the first run.
- **The coding evaluation is at least the 131K profile's:** pilot 5/6 and scored 17/18 (15/18 on the 131K profile),
  with the tool-loop task at 2/3. Qualification is about integration correctness, not task quality.
- **The 0.1.41 Mac client route remains qualified for the 131K rollback profile.** The Studio's current route
  has its own ledger and two G23 passes for the current 262K v0.1.42 profile (2026-10-12 update above).

## Update, 2026-10-09: on Terminal-Bench the PRO's Strata v0.1.41 profile passes 23 of 30

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-08-stock-strata-v0141-stock-omp-1886))

- **Four more than the 18.8.3 profile and none fewer.** On the same 30 Terminal-Bench 2.1 tasks, one attempt each,
  the current PRO profile passed 23 against 19 (21 against 17 on the earlier 28): both passed 19 and only this
  profile passed 4 (exact McNemar p = 0.125), at a median 1.04x the agent time on the 19 both passed. Strata
  (v0.1.40.3 to v0.1.41) and the harness's OMP (18.8.3 to 18.8.6) changed together, so neither takes the credit alone.
- **It meets the bar set beforehand for an improvement claim** (four more of 30 at no more than twice the agent
  time), but on one attempt the difference is not significant. It is no regression: every trial has a verdict, and
  the failures are four agent time limits, all of which also timed out before, and three wrong or incomplete results.
- **The profiles do not change.** The v0.1.41 profile stays current; qualification is about integration
  correctness, not task quality.

## Update, 2026-10-09: the RTX PRO 6000 is qualified for remote use from a Mac

([REMOTE.md](REMOTE.md))

- **The owner qualified the client route `client-rtxpro6000-strata0.1.41-omp18.8.6`.** Stock OMP 18.8.6 on a Mac
  Studio reaches the then-current 131K RTX PRO 6000 profile through an SSH local forward that the foreground
  `launch-omp` owns. This route remains qualified for that profile as a rollback.
  Its own ledger has G23 passing, and `verify_release.py --require-ready` passes.
- **What G23 covered:** a missing key refused before launch, a wrong key refused with 401, stream TTFT 0.19 s through
  the tunnel, a dropped tunnel failing only the turn in flight, and nonce recall after tunnel, client and server
  restarts. A plain `launch-omp` turn from the Mac answered as instructed.
- **The GPU is still shared with another tenant on that host.** The operator stops it before `start` and restores
  it after `stop`; the integration's exclusive-GPU check is unchanged. The route qualifies neither a fleet nor another
  client platform, and the retired RTX 4090 route drafts are gone.

## Update, 2026-10-09: Strata v0.1.41 with OMP 18.8.6 qualifies on the RTX 5090

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-5090-every-gate-2026-10-09-stock-strata-v0141-stock-omp-1886))

- **The owner qualified the RTX 5090 profile.** Its ledger has 21 pass and 3 not applicable (G22, G23 and G25, with
  their capabilities or claims off), and `verify_release.py --require-ready` passes. Ledger:
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.41-omp18.8.6/qualification.json).
- **Only Strata and OMP change.** The Coder IQ1_M pins, the llama.cpp archive, the Python lock and the stock setup
  plan are the 18.8.4 profile's, which is now its rollback, with the fourth tuple before it.
- **The coding evaluation is within one attempt of the 18.8.4 profile:** pilot 6/6 (5/6 before) and scored 15/18
  (16/18 before), with the tool-loop task at 1/3 on both and one multifile-regression attempt failing.
  Qualification is about integration correctness, not task quality.
- **Speed and resources are unchanged:** readiness 11.7 s, 105K-token cold prefill 14.5 s, GPU peak 30,836 MiB.
- **The RTX 3090 stays on Strata v0.1.40.3 with OMP 18.8.4;** this tuple's profile for it is a draft with no runs.

## Update, 2026-10-08 (night): Strata v0.1.41 with OMP 18.8.6 qualifies on the RTX PRO 6000

([MEASUREMENTS.md](MEASUREMENTS.md#rtx-pro-6000-every-gate-2026-10-08-stock-strata-v0141-stock-omp-1886))

- **The owner qualified the RTX PRO 6000 profile.** Its ledger has 21 pass and 3 not applicable (G22, G23 and G25,
  with their capabilities or claims off), every measured gate passed on its first run, and
  `verify_release.py --require-ready` passes. Ledger:
  [RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6/qualification.json).
- **Strata and OMP both change; the PRO's choices do not.** It keeps IQ3_S, four batch slots, parking and 32K prompt
  chunks, and the stock setup plan is the 18.8.4 profile's, including `--parallel 4` and both stock
  recommendations. The 18.8.4 profile is its rollback, with the 18.8.3 and v0.1.40.2 profiles before it.
- **The coding evaluation matches the 18.8.4 profile:** pilot 5/6 and scored 15/18, with the tool-loop task failing
  all three scored attempts on both. Qualification is about integration correctness, not task quality.
- **The RTX 5090 and RTX 3090 stay on Strata v0.1.40.3 with OMP 18.8.4.** The tuple's profiles for them are drafts
  with no runs; every gate in their ledgers is not run.

## Update, 2026-10-08: Strata v0.1.40.3 with OMP 18.8.4 qualifies on the RTX PRO 6000, RTX 5090 and RTX 3090

([MEASUREMENTS.md](MEASUREMENTS.md#three-gpus-every-gate-2026-10-08-stock-strata-v01403-stock-omp-1884))

- **The owner qualified all three profiles.** Each ledger has 21 pass and 3 not applicable (G22, G23 and G25, with
  their capabilities or claims off), and `verify_release.py --require-ready` passes. Ledgers:
  [RTX PRO 6000](../releases/win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.40.3-omp18.8.4/qualification.json),
  [RTX 5090](../releases/win11-rtx5090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json),
  [RTX 3090](../releases/win11-rtx3090-coder-iq1m-131k-strata0.1.40.3-omp18.8.4/qualification.json).
- **On the PRO only OMP changes.** The stock setup plan is the 18.8.3 profile's, including `--parallel 4` and both
  stock recommendations. The 18.8.3 profile is its rollback, with the v0.1.40.2 profile before it.
- **The RTX 5090 and RTX 3090 move from the fourth tuple to the current one,** with the same Coder IQ1_M at
  131,072 tokens. The fourth tuple's profiles stay qualified as their rollbacks and as the RTX 4090's record.
- **One gate needed a rerun on the PRO.** G16's predicate counted mentions of `append.py`, not its runs. After the
  fix (`2c32e2b`) the rerun passed; the failed receipt stays in the ledger.
- **The coding evaluation is within one attempt of the predecessors:** 15 of 18 on the PRO (16 on 18.8.3; the
  tool-heavy task 0/3 against 1/3), 16 on the RTX 5090 and 15 on the RTX 3090 (as on the fourth tuple).
  Qualification is about integration correctness, not task quality.

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
