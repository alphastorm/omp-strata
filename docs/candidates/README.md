# Controlled model improvement queue

`ledger.jsonl` is an append-only recommendation/disposition history, not a deployment queue. The first six
records preserve the 2026-10-24 packet decisions: NVFP4-QAD first; Penny Royal and TensorFold conditional;
Strata 0.2.4/DeepSeek parked; other models/quants and document/audio alternatives on watch. Only the exact
NVFP4-QAD revision is active for this window. The currently qualified IQ3_S and IQ1_M profiles and routes do
not change. At most three distinct pins may be active, and only one GPU experiment may run at a time.

## Daily discovery (manual; no scheduler installed)

From the repository root:

```sh
python3 scripts/discover_candidates.py --dry-run
python3 scripts/discover_candidates.py
```

The standard-library client reuses `upstream_watch.API`: bounded GitHub release-note metadata from the named
three repositories, immutable tag peeling (including Penny Royal's nonnumeric tag prefix), license metadata
at that commit, and Hugging Face model-card frontmatter plus pinned README blob identities for NVIDIA
FP4-Local and the two Qwen ASR cards. It reads metadata only: no release assets, model weights, installation,
conversion, profile changes, services, requests to a model, or scheduler registration. GitHub credentials,
when available through the existing helper, are sent only to GitHub, never Hugging Face. The news window is
the latest five releases per repository, not an exhaustive historical audit.

A failed/incomplete source prevents the daily ledger write. Concurrent writers refuse rather than stealing
a lock; reconcile an abandoned `.jsonl.lock` manually. Deduplication is `(source_url, pinned_revision)`:
repeated discovery cannot reactivate a rejected pin or overwrite its disposition. A later human-reviewed
disposition is another record with that same identity and the new disposition; all old evidence remains.
Discovery itself never creates an active record. Every row records source, immutable revision, date,
license, relevant change, intended task benefit, host, estimated evaluation cost and admission decision.
License metadata is not blanket commercial-use permission; resolve every code/weight dependency first.

Fresh tag discoveries can differ from packet source commits. In the recorded metadata, TensorFold's
`v1.1.3` tag resolves to `36415df4f76e4458e82d0fa729ecb28e287ebf38`, whereas the packet pins recipe source
`3f2ceb85b8cf9534bc05380f0f791682ece2e536`; both remain distinct observations, neither silently replaces the
other. Likewise the Strata 0.2.4 release tag is not permission to start its separate DeepSeek engine.

## One NVFP4-QAD challenger

Profile:
[`win11-rtxpro6000-nvfp4-qad-262k-slots4-strata0.2.3-omp18.12.6`](../../profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-strata0.2.3-omp18.12.6.json).
It is a **draft, comparison-only** native Windows PRO profile, not a qualified replacement. Stock Strata
`v0.2.3` / engine `0.1.48` and OMP `18.12.6` stay pinned, matching the frozen IQ3_S champion. The PRO-specific
planner admits only this NVFP4 input/host/context/slots combination; other NVFP4 models, other GPUs and
DeepSeek remain outside the admitted path.

- Checkpoint: `nvidia/Qwen3.8-Flash-Next-FP4-Local@b9ce18a6887e18c089fdea8509a33e63429a3300`.
- Weight index SHA-256: `5fa166bbb1cf25adda455117563efa72a2072272001f459eedece131ffc913e1`.
- All 29 input files: **102,262,280,327 bytes**, pinned individually by the reviewed stock file table and
  cross-checked against the pinned HF metadata. An API's `usedStorage` estimate is not this file sum.
- Conversion recipe: [`Niko1221/Strata@8183c6b6 docs/NVFP4.md`](https://github.com/Niko1221/Strata/blob/8183c6b67162340c09b67360860177c577a65f2e/docs/NVFP4.md).
  `tools/nvfp4_local_pack.py` SHA-256 `7ac34c7823275606bced9877ef5a7e78ad6d27bb9d3d12884526d510766548ae`;
  the converter, its requirements and `nvfp4_convert.py` are byte-identical in the pinned `v0.2.3` source.
  No 0.2.4/DeepSeek runtime is installed. Conversion dependencies have their own hash-locked venv, never
  upgrade the runtime venv, and run with CUDA hidden and Hugging Face/Transformers offline.
- Terms: NVIDIA Open Model Agreement **and** Qwen Community License 1.0. No converted weights are redistributed.
- Stock preparation command (called by guarded `install`, CPU only):
  `python tools/nvfp4_local_pack.py prepare --model <checkpoint> --out <checkpoint>/prepared`.

The explicit artifact path under an isolated candidate `<root>` is:

```text
models/nvidia--Qwen3.8-Flash-Next-FP4-Local/
  model.safetensors.index.json
  tensors/model-00001-of-00021.safetensors ... model-00021-of-00021.safetensors
  prepared/dense.gguf
  prepared/ple-nvfp4.gguf
  prepared/pack/{experts.bin,dense.bin,index.txt,native_experts.txt,tokenizer/}
  prepared/mtp/rt/
  prepared/conversion-receipt.json
```

`--native` and `--native-dense-gguf` both bind the prepared dense GGUF, `--ple-gguf` binds the prepared PLE,
and `--mtp` binds the checkpoint's own converted draft. Never substitute the IQ3_S champion's MTP or PLE:
QAD retrained them. Nested `tensors/` paths survive fetch. Stock setup receives `--models-dir`, not
`--gguf-dir`; setup stays `--no-start`. Every required generated runtime output is hashed into a conversion
receipt and the installed runtime identity; marker files alone do not authorize converted-file reuse.
Before sealing, preparation copies stock source's default `data/draft_vocab.bin` into `prepared/mtp/rt/`:
stock setup installs that same runtime input even with `--no-start`, so it must already be receipted.
Interrupted, unreceipted conversion refuses pending operator reconciliation rather than trusting stale marks.

For a new, isolated root, quiet staging uses the existing install path (which never starts the server):

```sh
python scripts/omp_strata.py install \
  --profile profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-strata0.2.3-omp18.12.6.json \
  --root <isolated-candidate-root>
```

Before any model download or root creation, require free disk at least
`max(2 × 102262280327, 102262280327 + 110000000000)` = **212,262,280,327 bytes**.
Abort below it; record free bytes before/after, all staged sizes/hashes and conversion outputs. Do not prune
other roots automatically or write into the champion root. The fleet's artifact drive is an operator-private
binding, not a public host address/path. If a different/slower drive is selected, record its media type and
charge cold load/replay time to the experiment; warm latency alone is not a storage comparison.

## Exclusive experiment and decision

Quiet staging grants no GPU lifecycle authority. Wait for the lead's go **and** its named representative real
jobs. Close serving admission through the host's authoritative interlock, drain owned requests, acquire the
existing exclusive host claim/lock, and use `scripts/experiment_loop.py` with the immutable IQ3_S champion as
both baseline and restoration target. Never stop an unknown incumbent or release custody on failed restore.
The script's perf receipt remains comparison-only; it does not claim task acceptance or route promotion.

For a warm champion, `run --quiesce-incumbent` is an explicit opt-in: the loop acquires its existing host
lock **before** it stops the verified incumbent, and marks that stop as a mutation before calling it.
The [operator procedure](../OPERATIONS.md#comparing-models-on-a-private-task-set) requires an exact private
`warm_incumbent` runtime/run-generation binding; the loop never adopts a merely familiar root/profile.
The private fleet adapter checks the frozen owner generation, reservation, closed admission and drained
jobs immediately before every lifecycle launch and restoration; the serving worker's batch must be finished
or cancelled first. Without this flag the existing pre-idle path remains unchanged. Receipts identify
`loop_quiesced_warm` (or a pending/failed handoff), per-arm cold-load time, mandatory transcript replay and
restoration time. They never present this as an uninterrupted warm-only comparison.

Disk admission is per arm: the baseline retains its own qualified disk floor on its volume, while the
challenger uses the manifest's floor, including any raised working-space margin. A candidate artifact on
another volume cannot make a qualified baseline fail the candidate's fresh-install floor. Both volumes
must still satisfy their actual requirements. A failed or unknown restoration retains the physical lock,
even after the worker exits; a later run refuses that hold until an operator reconciles the exact incumbent
and explicitly releases custody. Current main's shared task-set scheduler also refuses `persistent_hold`;
a dead PID is not proof of restoration.

Retain the existing G24 **six tasks × three scored attempts = 18**, frozen independent verifiers and all
failures. Pair the same representative real jobs across both arms and repeated attempts using
`scripts/eval_taskset.py`'s isolated worker/verifier boundary where applicable. Measure accepted-output
latency (all attempt/retry/replay/review time charged, not just token speed), tool behaviour, accepted quality
and fully loaded cost. Preserve the distinction between what the local model did and frontier review or
implementation. Private task prompts, repositories and raw transcripts stay outside this public repository.

A performance-only promotion needs at least **20%** accepted-output latency or fully loaded cost improvement
across repeated representative jobs, no material quality/tool regression and no greater review burden. A
clear, evidenced capability gain may justify promotion without a speed win. Record promote/reject/defer with
receipt references and exact measured counts in a new ledger record; rejection is a completed experiment,
not permission for another candidate. Promotion is still an owner's qualification/route decision, never an
automatic side effect. Verify the exact installed IQ3_S identity after restore. If an owner pause fences
admission, reconcile the restored owned generation before releasing the claim and leave admission closed;
the owner must resume and record a freshly admitted warm request before the experiment is complete.
The native loop writes `state/g10.json` beside the restored `state/run.json` only after a passing G10,
under the root lock: schema 1 binds `g10_run_id`, profile/runtime identities and the exact loop-owned
`run` generation. A private adoption receipt must consume that installed binding, not invent its own.
No Penny Royal, TensorFold, second experiment, DeepSeek, GPU OCR/ASR service,
cron entry or launchd entry is installed by this work.
