# Upstream findings

This file records defects, setup-review boundaries and upstream fixes observed in stock
[Strata](https://github.com/Niko1221/Strata) and stock [Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP).
Every status note below is bounded by the check date recorded in its entry:

- **Active on a current host (checked 2026-11-02):** [Strata items 7 and 8](#strata)
  ([Strata#2463](https://github.com/Niko1221/Strata/issues/2463), closed on 2026-10-19 as not planned, and
  [Strata#4518](https://github.com/Niko1221/Strata/issues/4518), opened on 2026-10-28 and fixed upstream in `v0.2.8`
  on 2026-10-29) — after Strata `v0.1.44.1`'s K=45 automatic layer-split regression left its pair profile draft,
  `v0.2.1`'s default K=25 split without `--gpu-roles` (layers 0-24 / 25-47; `v0.1.43.1`: 0-31 / 32-47) persists in
  stock `v0.2.3` through `v0.2.9` (100K-token time to first token (TTFT) 36.2 s on `v0.2.3`). On engine `0.1.52` (Strata `v0.2.7`), the automatic per-layer
  embedding (PLE) residency policy locked the 26.8 GiB PLE table in RAM on the 128 GB-RAM RTX 4090 + RTX 3090 pair
  (~31.4-37.5 s at start), left the automatic conversation cache off (`/metrics` `conversation_cache`: `enabled: false`,
  `budget_mib: 0`) and reduced G10 serving Windows commit headroom to 1.03 GiB (0.632-1.331 GiB in a later bench)
  versus 27.3 GiB on `v0.2.3` at the same 135.7 GiB limit ([Strata#4518](https://github.com/Niko1221/Strata/issues/4518);
  the `v0.2.7` roles draft with PLE in RAM stays held). On engine `0.1.54` (Strata `v0.2.8`), `Strata#4518`'s fix was
  measured on Windows on the measurement-only stock-residency draft
  (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`): the policy locked the
  26.8 GiB table (33.9-34.0 s), then gave the lock back on both starts and sized the automatic conversation cache at
  4,864 MiB (106-112 s to ready), against 8,192 MiB and 61-63 s to ready with `--ple-io direct` at matching
  100K-token TTFT (31.2 s with PLE direct versus 30.9 s with stock residency;
  [MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-stage-order-and-strata4518-on-engine-0154)). On `v0.2.9` + OMP
  `18.15.0`, the current pair profile
  (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`,
  rolling back to `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`)
  pins stock roles (`--gpu-roles 0=main,1=helper`, RTX 4090 as Main staged last; layers 0-23 / 24-47), manual split 24
  (`--layer-split 24`), stage dense-weight trim (`--trim-stage-weights`, `strata.trim_stage_weights: true`: 19.15 /
  17.76 GiB expert caches on the RTX 3090 / RTX 4090 vs 17.35 / 16.01 GiB without trim), `strata.ple_io: "direct"`
  (`--ple-io direct`), and `strata.engine_env` `sm86_table` + `gdn_stack` (qualified on 2026-11-03 after the owner
  overrode its `w1` 512/512 single-request A/B miss at `1.039` vs `>= 1.05`), keeping the 8,192 MiB automatic
  conversation cache and 27.77 GiB G10 commit headroom (27.74 GiB on the `v0.2.9` base rollback, 27.8 GiB on `v0.2.8`
  split-24 trim and 27.9 GiB on `v0.2.8` `roles-pledirect`; [decision](DECISION.md)).
- **Latest source review (2026-11-03; host-free admission, not qualification):**
  [Strata v0.2.10 setup](#strata-v0210-setup-review-component-engine),
  [engine 0.1.56 environment and start path](#stock-engine-environment-v0210--0156), and
  [stock OMP 18.16.0](#stock-omp-18160-surface). No profile, route or current release changes in this admission;
  the paired cold starts, real-host gates and engine 0.1.56 stage-order review remain required.
- **Qualified tuple review (2026-11-02, tuning profiles qualified 2026-11-02 evening and 2026-11-03):**
  [Strata v0.2.9 setup review](#strata-v029-setup-review-component-engine),
  [stock engine environment](#stock-engine-environment-v029--0155) and
  [stock UD-IQ4_XS budget lane](#stock-ud-iq4_xs-budget-lane-v029) cover tag
  `d94bac6aa33065f5e6a65cca111846627599e318` (`c62d5e3a15b40ea51c96aae9e8d36928965f53ab`) and Windows CUDA 13 engine
  `0.1.55`, with [stock OMP `18.15.0`](#stock-omp-18150-surface) (qualified across the PRO `kvvram-envpg` current and
  `slots4-batchmtp-pledirect-parking` base rollback; the RTX 5090 262K `kvvram-kvgrow-envg` default and `coder-iq1m-262k`
  base rollback, plus the 131K alternative rolling back to [Strata v0.2.8](#strata-v028-setup-review-component-engine) +
  [OMP `18.14.0`](#stock-omp-18140-surface); the pair's `env86g` current profile and split-24 trim + PLE-direct base
  rollback; and the Studio `kvvram-envpg` route current and `batchmtp-pledirect` base route rollback; the RTX 5090
  `kvvram-kvgrow` fallback stays an uninstalled draft, the PRO `v0.2.9` `UD-IQ4_XS` and `NVFP4-QAD` model candidates and
  their routes stay comparison-only drafts, the `v0.2.8` stock-residency pair draft stays measurement-only, the `v0.2.7`
  pair roles draft with PLE in RAM stays held, and the `v0.2.7` pair default-split draft stays unmeasured; `deepseek41`
  stays outside `omp-strata` profiles); the earlier v0.2.8, v0.2.7, v0.2.3, v0.2.2, v0.2.1 and v0.1.44.1 reviews remain
  below.
- **Earlier defects and workarounds (checked 2026-09-30 through 2026-10-07):** [Strata items 1–6](#strata) were
  closed upstream across `v0.1.28`, `v0.1.31`, `v0.1.32` and `v0.1.40`. [OMP items 1–12](#omp) record client
  behaviors and pull requests checked through `18.4.10` (2026-10-02) and `main` `7ac4b18` / `18.8.0`–`18.8.2`
  (2026-10-07); notes such as "no release contains it yet" or "every profile pins 18.4.8 or older" state status
  at those check dates, and the integration's own guards remain active.

These defects and surprises in the stock components were observed while qualifying OMP 18.4.0 (`401778d`)
against Strata v0.1.27 (`a790805`). Each has a reproducer in this repository. The Strata items are reported
upstream as linked below, after re-verification at the same Strata commit. The OMP items go upstream as pull
requests rather than issues, as upstream `CONTRIBUTING.md` asks for work the reporter will submit.
The integration works around them only where a supported setting exists.

Upstream status was re-checked on 2026-09-30 against Strata v0.1.28 (`bbaaabb`), on 2026-10-01 against
**v0.1.30 (`30ec18e`), pinned by the second candidate** (`win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6`,
which also moves OMP to 18.4.6), later on 2026-10-01 against **v0.1.31 (`9259cad`), pinned by the third tuple's
draft profiles** (RTX 3090 and RTX 4090 hosts, with OMP 18.4.8), and on 2026-10-02 against **v0.1.34 (`1678de3`),
pinned by the fourth tuple** (all three hosts, with OMP 18.4.10). v0.1.28 fixed items 1, 3, 4 and 6 and the second
candidate's real-host gates confirm them; v0.1.31 fixes items 2 and 5, and v0.1.34 keeps both fixes (host-free
suite; setup and server source reading). The upstream issues behind all six items are closed. The first candidate's
profile keeps v0.1.27 with every item present. "Mock tier" below means the stock frontend with its MockEngine (no
GPU).

**Upstream rewrote Strata's history on 2026-10-06** (v0.1.40.1 release notes). Every release tag now points to a
new commit; checked through the GitHub API for each tag a profile pins (v0.1.27 through v0.1.39), every new commit
has the same tree as the pinned one, so release contents did not change. Profiles keep their original commit pins,
and `install` fetches exactly those SHAs. GitHub still served all seven on 2026-10-06, but nothing upstream
references them any more, so a later install of an existing profile may fail once GitHub drops them. New drafts pin
the rewritten commits. The same notes number the hotfix `v0.1.40.1` with four parts, which `upstream_watch`
now reads (stock setup reads it as 0.1.40).

## Stock DFlash2 pair arm (v0.2.10 / 0.1.56)

This is an opt-in, separate profile, not a change to the qualified pair. `strata.drafting: "dflash2"` pins stock's
config choice; absent means stock Auto. Only the Qwen family is reviewed, with one request at a time and no
pipeline windows, batch MTP or calibration. The model's `dflash2_source` pins the two files from
`incoai/Qwen3.8-Flash-Next-DFlash2` at `a22a1744e85c17364dcc54a6a420af7135d4c7f6`, both locally produced packs and
the stock vocabulary by SHA-256. The source and pack identities come from stock `strata_control/drafting.py` at
`v0.2.10`; the explicit choice does not authorize a start-time fetch or a silent MTP fallback.

Fetch stages the two revision-resolved HF inputs under `downloads/dflash2/<revision>/`. The prepared folder is
`data/dflash2`: stock `drafting.data_dir_of` derives `data` from setup's `--mtp data/mtp/rt`, then appends `FOLDER`.
The macOS client downloads neither DFlash2 file; only the GPU runtime installation uses them.

## Stock UD-IQ4_XS budget lane (v0.2.9)

The model belongs to stock's budget-capable Unsloth family, but **the reviewed PRO choice is not a RAM-budget
configuration**. At `c62d5e3a15b40ea51c96aae9e8d36928965f53ab`, stock `unsloth_budget` returns false on the
192 GiB-RAM PRO: every expert fits in the resident arena, `budget` stays `None`, and setup writes no
`--resident-budget-gib`. The earlier planner's unconditional `budget_choice` would have invented a 55 GiB budget;
the admission instead evaluates stock's actual gate and refuses if it chooses budget mode.

The admission is limited to `unsloth / UD-IQ4_XS`, 262,144 tokens, one 90–100 GiB GPU, four slots, `(8, 16)`
performance/efficiency CPU cores, int8 KV and stock automatic KV streaming. The v0.2.9 gate assignment,
`unsloth_budget`, `unsloth_default_env`, their constants and config-env write are digest-pinned; the reviewed
budget/UMA and small-card branches must remain unreachable. The v0.2.9 config block is mandatory, so the v0.2.8
fixture does not gain an admission. Other contexts, slot counts, cards, layer splits, UD-Q4_K_XL and Q8_0 remain
outside this planner lane. The older reviewed UD-Q4_K_XL budget profiles remain unchanged.

Stock writes `env = {"STRATA_HC_Q8": "1", "STRATA_ROUTE_TAIL_SKIP": "0"}`. The profile records this as
`strata.setup_env`, not an optional engine-env pin; install requires exactly that dictionary, with no extra keys,
and it cannot be combined with `strata.engine_env`. The three GGUF shards are pinned by stock's
`UNSLOTH_IQ4_XS_SHARDS`; setup writes `strata-unsloth-ud-iq4_xs.json`. Like the four-shard Unsloth model, it lets the
engine locate PLE from shard 1: no `--ple-gguf`, and no `experts.bin` in the target pack. The separate MTP pack
still contains its own draft experts. RAM floors preserve stock's all-resident threshold (arena in GiB plus
16 GiB), not the model table's lower budget-mode minimum.

The comparison-only screen's stock setup accepted four slots without warnings, and engine 0.1.55 reported four
batch-MTP slot drafters. These observations permit preparing a separate Terminal-Bench candidate with the PRO's
existing prefill, batch-MTP and PLE-direct pins; they are not hardware qualification or Terminal-Bench results.

## Strata v0.2.10 setup review (component engine)

Stable [`v0.2.10`](https://github.com/Niko1221/Strata/releases/tag/v0.2.10), release **432079269**, published
**2026-11-02T23:52:47Z**: annotated object `db0500a53119a349fa44497099d6e28a83ded34a`, commit
`ffa80d73133ea5c548aefe57889a16e8085a938f`. App **0.2.10** ships Control/engine **0.1.56**; the Windows CUDA 13
component is `strata-engine-0.1.56-windows-x86_64-cuda-cuda13.tar.gz` (**627,806,827 bytes**), SHA-256
`5336671c55bc1b819d076104608522147227001d1711378f35ea5d524bc866ec`, built from **`06698c674`**.
This admission compares stock v0.2.9, not a modified installer. `MIN_ENGINE=(0, 1, 46)`, `HF_REVISIONS`,
`LLAMA_CPP_COMMIT` and the runtime/monitor requirements are unchanged.

### Five reviewed planning surfaces

The unchanged planner at the fixture-only commit reproduced all five refusals independently: default recommendation,
new planning call, fresh-config definition, fresh-config caller and split-disk estimate. The v0.2.10 planning fixture
reuses the v0.2.9 AST-node selection, replaces the changed source nodes and includes `kv_streaming_need_gb` and
its caller. Extraction provenance stays outside the public repository; every selected statement equals its stock AST.
No installer, hardware probe or whole `strata_control` module is vendored or imported by the fixture.

| Surface | Stock v0.2.9 → v0.2.10 statement | Reviewed constant / reason | Effect on these lanes |
|---|---|---|---|
| Informational defaults | `rec_ctx = 32768 if small < 14 else 65536 if small < 20 else 131072` → `rec_ctx = 131072` ([setup:10242-10244](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10242-L10244)) | `DEFAULT_RECOMMENDATION_0_2_10`; the exact selected shape is **eight** nodes: `fams`, `rec_fam`, `names`, `names.sort`, `rec`, `small`, `rec_ctx`, `rec_ctx`. The final unchanged `min(rec_ctx, ram_ctx(...))` RAM clamp remains selected. | Same 131,072-token informational recommendation; explicit model/context choices stay untouched. The preparation plan's seven-node count omitted that clamp. |
| Streaming need | `stream_fits = ram >= MODELS[model]["ram_gb"] + kv_ram_gb + 1` → `stream_need = kv_streaming_need_gb(model, ctx, kv)` then `stream_fits = ram >= stream_need` ([setup:10693-10694](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10693-L10694)) | `REVIEWED_HELPERS_0_2_10` and `STREAM_NEED_0_2_10`; [the helper](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L6207-L6220) takes the smaller of rules (1) and (2) below. Only its exact caller executes it; neither `named_calls` nor `pure_exec` widens. | PRO and 5090 262K still pin KV off; the pair still streams. Coder's rule (1) remains the smaller arm, so its threshold is unchanged. IQ3_S's informational streaming threshold decreases, not its admitted RAM floor. |
| Disk/MTP | `mtp_fetch = 5.2 if (not mtp_have and not ready and a.mtp != "off") else 0.0` gains `and getattr(a, "drafter", None) != "dflash2"` ([setup:10434](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10434)) | `DISK_0_2_10`; only the `mtp_fetch` assignment gets `getattr` in a separate namespace. The planner refuses if `a` has **any** `drafter` attribute, even `None`. | The fresh-root MTP allowance remains 5.2 GB. Install never passes `--drafter`; no DFlash2-only download path is admitted. |
| Fresh-write caller | `write_setup_config(..., explicit_args(a))` gains `after_carry=(lambda c: uma_cache_guard(c, model, gpu)) if gpu.get("uma") else None` ([setup:10968-10969](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10968-L10969)) | `WRITE_CALL_0_2_10`, paired with its version's definitions in `fresh_write_review`. Evaluate only the `IfExp` test; a truthy UMA result refuses rather than dropping the callback. | Our discrete NVIDIA inputs do not carry `uma`; no callback runs. A v0.2.9 definition with the v0.2.10 call, or the reverse, refuses. |
| Fresh-write definition | `write_setup_config(..., explicit=None)` gains `after_carry=None` and calls it before `user_args.stamp` when non-`None` ([setup:6815-6852](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L6815-L6852)) | `FRESH_WRITE_0_2_10`; `carry_user_args` and `explicit_args` retain their earlier digests. Definitions and call must match one complete reviewed version. | With no earlier config/user args and no UMA callback, `args_written` still equals `args`; config keys remain unchanged. |

Stock's streaming helper uses `min((1), (2))`, with
**(1)** `ram_gb + kv_gb + 1` and **(2)** `arena_gb + LOW_RAM_HEADROOM_GB + kv_gb`.
`thresholds.kv_streaming_from` reports this new stock value. **The admitted streamed host floor deliberately keeps
rule (1)**, plus the existing conservative per-card/per-slot session reservation. Streaming with less RAM is not
qualified by this source review. At the existing lane inputs, the PRO slots4 KV-off plan, 5090 262K KV-off plan
(with the separate KV-grow pin), 5090 131K plan and pair roles/split-24 plan keep their v0.2.9 setup args, engine
flags, config keys, host floors, model files/URL, stock tips and notes. Older tags retain their earlier paths.

Changed statements outside the executed planning span do not gain an admission: argparse's `model_alias`,
`--prepare-pack` and `--drafter`; the `prepare_pack` early return; `a.check` display text; the Strix `gpu_fit` advice;
`mmproj_beside`; the MTP/DFlash2 vocab download branch and `refresh_dflash2_vocab`. `kv_streaming_wanted` is also
outside the span and is not loaded. The changed runtime/start/path helpers (`download`, `verify_sha256`, `done`,
`mark`, `ready_verified`, `run`, `_start`, `control_engine_step`, `install_own_path`, `own_path_context`,
`refresh_shared_draft_vocab`) are not planner execution primitives.

### Runtime IO review for staged installs

The stock installer still skips downloads for omp-strata's staged inputs; **no install correction is required**:

| Input / helper | Reviewed v0.2.10 behavior |
|---|---|
| Staged component and `--prebuilt` | [`get_prebuilt:5515-5537`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L5515-L5537) accepts the already staged `BUILD.json`/executable, supported CUDA architectures and version before any download/HEAD path. The local `--prebuilt` folder is not a latest-release lookup. |
| Verified `--gguf-dir` | The download loop is under [`elif not a.gguf_dir`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10475-L10514); local shards get structural checks and any stock hash check. [`verify_sha256:3324-3371`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3324-L3371) reads `mark_text`, hashes locally when needed and has no repair download for `own=True`. omp-strata verifies its own exact pins first. |
| Pinned MTP `rt/experts.bin` | The [fetch/rebuild arm](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L10568-L10593) is entered only if the staged layer is missing or corrupt. [`mtp_corrupt:7739-7747`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L7739-L7747) runs the local tensor verifier, not a fetch; the revision-pinned install has already verified and packed those tensors. Vocabulary refresh is local; a fresh MTP root has no DFlash2 copy to refresh. |
| llama.cpp archive marker | [`get_llama_cpp:3615-3653`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3615-L3653) returns an extracted tree or calls `download` for its staged zip. [`download:3106-3122`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3106-L3122) still returns when the file exists and `done` is true. [`done`/`mark_text`/`mark`:1071-1116](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L1071-L1116) accept a readable finish mark, not a required SHA payload. Install's existing text marker therefore remains valid; it need not be rewritten with stock `mark()`. |
| Ready packs and subprocesses | [`ready_verified:3423-3428`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L3423-L3428) does require `sha256 <hash>` in the mark, but our GSQ lanes are not ready-pack installs and llama.cpp does not use it. [`run:1020-1042`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/setup.py#L1020-L1042) gates install/build work through acquisition policy; its GGUF-Python fallback finds the staged llama.cpp tree. Runtime wheels are installed first; component setup keeps `PIP_NO_INDEX=1`, scrubbed environment, redirected settings and `--no-start`. |

This is a review of the staged-input paths, not permission to run unguarded setup or a claim that stock never
downloads with missing inputs. All input verification and generated-config checks remain mandatory.

## Strata v0.2.9 setup review (component engine)

Stable [`v0.2.9`](https://github.com/Niko1221/Strata/releases/tag/v0.2.9), GitHub release **429790797**,
published **2026-10-31T08:02:32Z**: annotated object `d94bac6aa33065f5e6a65cca111846627599e318`,
peel `c62d5e3a15b40ea51c96aae9e8d36928965f53ab`. Compared with stock v0.2.8
(`870aedd9e1ebe1c91f94da93b59af17729f6c5c0`). App **0.2.9** ships Windows CUDA 13 engine **0.1.55**:
`strata-engine-0.1.55-windows-x86_64-cuda-cuda13.tar.gz` (621,585,315 bytes), SHA-256
`34f399a0a22e4af8b434439de04dcce3734ccba7e884ef6003439ba148d667df` (matches the release's `SHA256SUMS.txt`);
`engine-component.json` SHA-256 `84271f6e1ca94bf39ac9c22b64a9bde71aadc67fb3482e5d240d515e9158b98d`;
build `99866a47a2b8+cuda13.0`, BUILD source `f-029-rel`, native SASS for `sm_75`, `sm_86`, `sm_89` and `sm_120`
plus `compute_120` PTX. The BUILD commit resolves upstream as an ancestor of the tag (25 commits earlier; two lines
of engine source differ). Archive members were inspected without executing a binary; component-signature verification
is not claimed and native startup observations remain required.

### Reviewed planning and dependency delta

The unmodified report refused `new call in stock setup planning; review required` on every lane: the multi-GPU
config block (`setup.py:10341-10372`) gains stock's opt-in replica-profile statement (`getattr`, the
`STRATA_REPLICA_PROFILE` environment opt-in, an import inside `try`), and its HIP four-card guard now also reads
`replica_done`. Admit only this block, not new general `pure_exec` calls, attributes or builtins:

| Reviewed entry | Full-field AST SHA-256 | Decision |
|---|---|---|
| Multi-GPU config block | `15158c364e8f4ac9187525f1bd588c6938ab17cabdf00a713e1fe7518843f6a4` | Preserve the existing roles/config projection; slice off the last two sub-statements; execute only `replica_done = False` with the rest. |
| Replica-profile sub-statement | `9f989b6940d30d3ddc3f93018ed51e8df9117855518a62b48926020b799b4ccf` | Covered by the whole-block pin. Its guard must be false for the planned args (`replicas=None`, `replica_profile=False`: `install.setup_argv` passes neither `--replicas` nor `--replica-profile`, whose stock default is false, `setup.py:9199`) and for install's own scrub (`install.scrubbed_env`) of a shell that exports the opt-in; the planner never reads its own environment. The body is never validated or executed. |
| HIP four-card sub-statement | `71c4fe304c6e34a87b85781e37711933cf412711ee9e4a623d2919d40ae1a25a` | Covered by the whole-block pin; evaluated with `replica_done = False` (the only value a false replica guard leaves) and must be false. Edited, reachable or moved replica/HIP code refuses. |

On the two-card lanes the replica profile would otherwise apply (two NVIDIA cards, Qwen3.8 IQ3_S, 127.7 GiB RAM): the
manual split-24 pair is outside the guard by its args, and the automatic-split pair only because the opt-in is never
passed and install strips every `STRATA_*` variable. The source-faithful `strata_0_2_9_plan.py` fixture keeps
v0.2.8's selection; three retained nodes differ: the multi block, `HF_REVISIONS` (only
`unsloth/DeepSeek-V4.1-Flash-1017-GGUF` moves, `f924b94` to `8a6ec9c`; the Qwen IQ3_S, Coder and MTP revisions are
unchanged, so installed shards are reused) and `choose_gpus` (an advisory line for a small card left unused, which the
planner does not execute). Five-plan comparisons preserve explicit flags, generated keys, model files, thresholds, host
floors, slots and roles.

`requirements.txt`, `requirements-monitor.txt`, `tools/calibrate.py`, `strata_control/user_args.py`,
`tools/mtp_fetch.py`, `PY_PACKAGES`, `CUDA_WHEELS` and `LLAMA_CPP_COMMIT` are unchanged; drafts reuse
`locks/strata-python-cp313-win_amd64-strata0.2.7.txt` with no new `--python-lock`. Config keys and the other reviewed
constants are unchanged.

### Stock defaults and lane applicability

| Stock engine 0.1.55 / server change | Applicability and fresh-observation boundary |
|---|---|
| Nine-switch parallel-slot stack (`STRATA_CKPT_POOL` and eight more) | Set by stock `serve/server.py` only on Linux with CUDA and two or more slots ("Windows none at all"); not set automatically on Windows, and inherited `STRATA_*` remains scrubbed. Pinned via `strata.engine_env` (`parallel_stack`) on the current PRO `v0.2.9` profile (`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0`, alongside `gdn_stack` and `--kv-streaming off`; [Stock engine environment](#stock-engine-environment-v029--0155), [2026-11-02 tuning measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150): `w2` 1,000/128 output +11.3% at `c=1`, +29.3% at `c=2` and +34.8% at `c=4`, `4 × 32K` +13.1%, greedy output byte-identical to the `v0.2.9` base rollback, which writes no config `env`). |
| GDN tensor-core prompt kernels (`STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2`) | Linux-only server defaults; compiled into the Windows engine (cc 8.0+ with 48+ SMs, so all four cards can run them). Pinned via `strata.engine_env` (`gdn_stack`) on the current PRO `v0.2.9` profile, the RTX 5090 262K `v0.2.9` default (`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0`, alongside `--kv-streaming off` and `--kv-grow`: cold TTFT −8.6% at 32K and −8.9% at 100K, 100K decode `0.973`, `w1` +2.5% and `w3` 32K +8.4%), and the current pair `v0.2.9` `env86g` profile (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`, alongside `sm86_table`); off on their `v0.2.9` base rollbacks and the RTX 5090 131K alternative. GDN prompt numerics are not bit-exact upstream. |
| SM120 hyper-connection reads gain exact 5-8 token decode kernels | Default on the single-card PRO and RTX 5090 lanes (bit-identical; upstream measured +5% and +2% decode at eight concurrent requests). Off on the pair, whose v3 read stays off. |
| Tool-call parser: calls inside fenced or indented code stay text ([Strata#4702](https://github.com/Niko1221/Strata/issues/4702), [#4703](https://github.com/Niko1221/Strata/issues/4703)); tools the conversation already called count as declared on chat completions ([#4663](https://github.com/Niko1221/Strata/issues/4663)) | All lanes. G24 is not like-for-like with v0.2.8: a genuine call that the model indents four spaces after a blank line now ends as text. |
| [Strata#4695](https://github.com/Niko1221/Strata/issues/4695) layer-major expert copy, [#4690](https://github.com/Niko1221/Strata/issues/4690) `[DONE]` hang-up | #4695 needs an unbuffered expert tier (a resident budget), which no profile pins; #4690 is the desktop app's gateway, not the server OMP talks to. |
| New start line for a card whose architecture the engine was not built for (#4662) | Silent here: the build covers `sm_86`, `sm_89` and `sm_120`. |
| [Strata#3313](https://github.com/Niko1221/Strata/issues/3313) | Still open: the `sm_86` table is skipped by default on the mixed `sm_86` + `sm_89` pair. In three paired cold starts on the `v0.2.9` pair variant (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`, pinning `sm86_table` + `gdn_stack` in `strata.engine_env`), cold decode rose +6.5% at 8K and +11.4% at 100K and every TTFT bar passed (`0.948–0.996`), while `w1` 512/512 single-request output rose +3.9% (`1.039` vs the pre-registered `>= 1.05` bar); the owner overrode that one bar on 2026-11-02, the requalification chain on 2026-11-03 at `d0a1254` passed all 14 measured gates (`21 pass, 3 not applicable`), and the pinned profile is now qualified and current ([MEASUREMENTS.md](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150), [DECISION.md](DECISION.md)). |

The engine and server start lines the lifecycle checks parse (batch-MTP on/off, `--pipeline-windows`, PLE direct
probe, residency choice) are byte-identical to v0.2.8. The real-source GET/POST/OPTIONS census has no route change,
no lost route and no unclassified route; G13's matrix is unchanged. The environment-name census adds 34 names,
including `STRATA_REPLICA_PROFILE`, `STRATA_COALESCE_PREFILL`, `STRATA_GR_R2` and the GDN tensor-core tuning names;
none is granted as a profile override, and inherited `STRATA_*` remains scrubbed.

**Engine 0.1.55's stage order is admitted to `lifecycle.STAGE_ORDER_REVIEWED_ENGINES`** (`8002c77`). Host-free
full-field AST comparisons show `gpu_list`, `layer_split_value`, `layer_split_of`, `ordered_gpus`, `engine_args`,
`parallel_args` and `parse_engine_stage_line` identical to v0.2.8, while `child_env` adds only the Linux-gated
`parallel_stack_env` and `gdn_stack_env` calls. In the 2026-11-02 pair measurement window, all six version A/B starts
(three `v0.2.8`, three `v0.2.9`) parsed complete with the reviewed parsers: RTX 3090 first, RTX 4090 last, layers
0–23 / 24–47 at pinned manual split 24 (expert caches 19.15 / 17.76 GiB under `--trim-stage-weights`;
[MEASUREMENTS.md](MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150)).

## Stock engine environment (v0.2.10 / 0.1.56)

Engine **0.1.56** joins **0.1.55** in the exact engine-environment review set; no group or value changes.
At app commit `ffa80d73133ea5c548aefe57889a16e8085a938f`,
[`serve/server.py:3979-3983`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L3979-L3983)
(`PARALLEL_STACK_ENV`) and
[`4031`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L4031)
(`GDN_STACK_CUDA`) are byte-identical to the v0.2.9 declarations at lines 3675–3679 and 3724.
The engine-side sm_86 table in
[`src/core/nv_defaults.cpp:26-40`](https://github.com/Niko1221/Strata/blob/06698c674/src/core/nv_defaults.cpp#L26-L40)
at the Windows component's build commit **`06698c674`**, not merely the app tag, is byte-identical to the
0.1.55 review at **`99866a47a2b8`**. The complete file is not byte-identical; this claim is about the reviewed
sm_86 branch only. Config-env delivery still precedes the Linux-only default groups.

Stock's new FP16 weight-cache and all-experts-resident no-slot-loan decisions belong to the engine, not these
groups: `STRATA_PF_W16_CACHE_MIB` and `STRATA_AUTO_NOBORROW` remain unpinned
([server explanation](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L3984-L3988),
[no-loan decision](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7810-L7834)).
Cache sizes and cold-start readiness need fresh host evidence. This source admission does not admit engine
0.1.56's multi-GPU stage order or qualify any profile.

### Versioned server start-path review

`SERVER_PINNED_PATH_0_2_9` remains valid for v0.2.9. The v0.2.10 review recomputes the full same-module closure from
`child_env`, `engine_args`, `parallel_stack_platform` and **`mtp_retry_args`**, including `drafting_vram_mib`.
The top-level imports binding `draft_layer`, `drafting` and `vram_fit`
([server:76-78](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L76-L78))
have reviewed AST digest `b3a207845da9c931bf60dd9eac96b393134c22152a205b06ac5a713b4a6e7d86`.
The whole cross-module ASTs, read with `git show` at the candidate's immutable Strata commit, are:

| Module | `reviewed_hash` (full-field AST SHA-256) |
|---|---|
| `strata_control/drafting.py` | `4f717a60bf5eb72eb219024c1d4c7acddc2d499bcfcf142e32de54d28a4279fd` |
| `strata_control/vram_fit.py` | `01d6a4d92288fb92bee16ec19c94905328072251028ef02c190de3e374dc6ae2` |
| `strata_control/draft_layer.py` | `2dc95f87df38f38700273dfc67a1cdc9a01a9001048d701069d3b050528e8d17` |

Drafts and **candidate-only reports for every engine >=0.1.56** require this review, even without `engine_env`
(notably the 5090 131K lane). Older engines retain the `if groups:` boundary. Generic news reports select no engine
and remain source-delta checklists. The review returns its matched version key; unknown closures, import bindings,
missing module digests or changed modules refuse.

An exhaustive `alias.attr(...)` census also records the existing leaves: `user_args` (separately digest-reviewed),
`gpu_roles` (topology), `engine_component` (hardware/reference probes), and local `dsv41_flags` (the unreachable
DeepSeek compatibility probe). `gpu_roles.py`, `user_args.py` and `draft_layer.py` are byte-identical to v0.2.9.
`engine_component.py` adds DeepSeek version handling, backend aliases/saved backend and HIP PCI architecture
discovery; our MTP outcome is independent of backend detection. The changed `parallel_args`
([server:3581-3626](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L3581-L3626))
has split-engine/DeepSeek branches guarded by `split_engine_note` and `arch`, both refused by generated-config
verification. `hip_gpu_archs`/`hip_speed_scores` only change file-handle closing on the unselected HIP path.
These leaves do not expand the three-module pin or runtime source list.

### Stock Auto drafting and fit at the reviewed lane inputs

[`engine_args:3492-3565`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/serve/server.py#L3492-L3565)
now calls `drafting.apply` and `vram_fit.fit_start` on every start. No `strata.drafting` pin is added here.

| Lane | Source-read Auto result | Fit evidence / boundary |
|---|---|---|
| PRO IQ3_S, four slots + batch-MTP | MTP: `slots > 1` is blocked by [`drafting.blocked_by:534-541`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/drafting.py#L534-L541). On a detected capable backend, the stock note is `Drafting: MTP (DFlash2 isn't available in this mode)`; failed/unsupported detection keeps MTP without the note. | The recorded private host-free `probe_fit_start.py` result at 97,887 MiB VRAM leaves args unchanged and no fit note; stock estimated slack **71,624 MiB**, need **732 MiB**. Its 97,000 and 95,000 MiB probes also leave args unchanged. |
| 5090 Coder IQ1_M, 262K + KV-grow and 131K | MTP with no note: the Coder model name fails [`supported_model:251-258`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/drafting.py#L251-L258), so [`apply:795-801`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/drafting.py#L795-L801) returns before touching args. | Recorded probe at 32,607 MiB: 262K slack **21,297 MiB** (need **66 MiB**), 131K slack **24,287 MiB**, unchanged args/no note. The lower-memory probes in that script also remain unchanged. |
| RTX 3090 + RTX 4090 pair, roles/split 24 + pipeline windows | MTP: `--pipeline-windows` is blocked by the same stock guard; capable detection may print the same one-line MTP reason as the PRO. | [`fit_start:286-289`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/vram_fit.py#L286-L289) returns unchanged for a layer split. |
| Studio → PRO route | The server's PRO outcome above; no second engine decision on the client. | Requires its own route/fan-out evidence after server qualification. |

The fit script is a host-free estimate at stated inputs, **not measured GPU headroom, a start sandbox, or a
qualification result**. No `stock_module_sandbox`, `stock_start_review` or install-flag refactor is introduced.
On the host, every >=0.1.56 install identity hashes the **bytes** of `serve/server.py` and the three modules above;
every start rechecks them and captures both new log intervals, including the no-env 131K lane.

`_check_drafting` permits no note or at most one stock `Drafting: MTP (<reason>)` from the reviewed reason set.
It refuses DFlash2 chosen/on, drafting off, `"mtp": false`, **`DFlash2 didn't start`**, and unknown/repeated notes
in either output stream; `run.json` records the MTP result and both intervals. The five start-time flags
`--draft`, `--draft-model`, `--draft-fallback`, `--draft-conf`, `--mtp-draft-vocab` are forbidden in new drafts and
refused in every profile's expected config flags. A later explicit DFlash2 variant is a separate admission.

`_check_start_fallbacks` refuses these verbatim stock diagnostic fragments in either start interval:

| Diagnostic | Immutable source |
|---|---|
| `short of GPU memory: more is read from RAM and the SSD, expect it to be slower` | [`vram_fit.py:91`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/strata_control/vram_fit.py#L91) (`NOTE_SLOW`) |
| `strata generate: not enough RAM for the expert arena (` | [`generate.cpp:7323-7325`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7323-L7325), [#4846](https://github.com/Niko1221/Strata/issues/4846) |
| `this start runs without the draft layer (decode is slower; STRATA_MTP_KEEP=1 keeps it)` | [`generate.cpp:6736-6737`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L6736-L6737) |
| `prompts are read in smaller chunks, expect them to be slower` | [`generate.cpp:7609-7610`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7609-L7610), 16-slot cache loan |
| `strata generate: short of GPU memory: the cache had no room, so the output head (` | [`generate.cpp:7699-7700`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L7699-L7700), pinned-host head/PCIe read |

Both checks run before start returns healthy and use existing failure teardown. Earlier engines do not gain
these checks. KV-off lanes separately refuse any start-time streaming line. The engine's reply-only penalty
window ([#4590](https://github.com/Niko1221/Strata/issues/4590),
[`generate.cpp:17180-17187`](https://github.com/Niko1221/Strata/blob/06698c674/src/program/generate.cpp#L17180-L17187))
and inherited Windows IO-priority repair/report
([#4733](https://github.com/Niko1221/Strata/issues/4733),
[`io_priority.cpp:19-43`](https://github.com/Niko1221/Strata/blob/06698c674/src/platform/io_priority.cpp#L19-L43))
remain stock behavior, not profile switches.

## Stock engine environment (v0.2.9 / 0.1.55)

The tuning admission is opt-in, not a change to the qualified baseline's defaults. `strata.engine_env`
must be an exact union of complete reviewed groups of stock-owned **string** values; partial groups, extra
names, other values and raw `strata.env` / `setup_args.env` are refused. The exact reviewed engine set is
`{"0.1.55"}`; the archive pin above binds the engine bytes. A future engine needs a new source review, even
if its server path is unchanged.

| Group | Verbatim stock values | Admission |
|---|---|---|
| `parallel_stack` | `STRATA_CKPT_POOL=1`, `STRATA_CKPT_POOL_READY=4`, `STRATA_SLOT_CKPT_MOVE=1`, `STRATA_SLOT_COPY_DIRECT=1`, `STRATA_SLOT_COPY_BATCHSYNC=1`, `STRATA_BATCH_GDN_GROUPS=1`, `STRATA_BATCH_ATTN_ROWS=1`, `STRATA_BATCH_SELF_COMMIT=1`, `STRATA_QSA_SLOTS=1` | Stock server `PARALLEL_STACK_ENV`; requires at least two batch slots, like stock's gate. |
| `gdn_stack` | `STRATA_GDN_TC=1`, `STRATA_GDN_CONVL2=2` | Stock server `GDN_STACK_CUDA`; the reviewed cards meet the engine's CUDA capability threshold. GDN prompt numerics are not claimed bit-exact. |
| `sm86_table` | `STRATA_ADAPT_NOWAIT=1`, `STRATA_ADAPT_LAG=2`, `STRATA_CPU_IQ_ALL_EXACT1=1`, `STRATA_SIDE_MIXER=2`, `STRATA_ATTN_DAILY=1`, `STRATA_GR_UP75=1`, `STRATA_GU_SWIGLU=1`, `STRATA_QSA_ROWS=1`, `STRATA_B6_MMVQ_ROWS=1` | Only a mixed-architecture multi-GPU profile containing an sm_86 card. |

The two server dictionaries are literal constants at
[`c62d5e3a:serve/server.py`](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/serve/server.py).
Stock `child_env` copies config `env` **before** the Linux-only stacks call `setdefault`.
`parallel_stack_platform()` is `sys.platform.startswith("linux")`: pinning those same values in a Windows
config enables them explicitly without changing stock sources or passing an inherited process knob.
Drafting compares each requested server-owned group against its literal dictionary and pins the complete
same-module call closure of `child_env` and `engine_args`, including the platform gate (32 functions).
Functions must occur exactly once, the transitive callee set must be unchanged, and every full-field AST
SHA-256 must match `SERVER_PINNED_PATH_0_2_9` in
[`scripts/upstream_watch.py`](../scripts/upstream_watch.py). The source-faithful excerpt is
[`strata_0_2_9_server_engine_path.py`](../tests/fixtures/strata_0_2_9_server_engine_path.py).

| Delivery-path root or gate | Full-field AST SHA-256 |
|---|---|
| `child_env` | `cfd3f69fa243301085281c8d240b78c42c3d3fa72c9e76e304a747478d2b34d1` |
| `engine_args` | `be1a65fa9475e9c6c0751f79735ef71e5ac5e09c607cfc61069923c3c41c8c1d` |
| `parallel_stack_platform` | `1ba6b721cc5fbeb72dd35732b0dac0f1e29aeb0902a37e4daae482625ac16328` |
| `parallel_stack_env` | `0a5f58bdd13071dc45b2a89cf798b2670b2196d2f87d0d95ac6c17cfef65a81d` |
| `gdn_stack_env` | `288a6edfb2a15442aa8620d57e65057587ac6141c18548937e0b0d21fd627ea2` |

At the Windows engine build commit `99866a47a2b8`, the sm_86 values live in
[`src/core/nv_defaults.cpp`](https://github.com/Niko1221/Strata/blob/99866a47a2b8/src/core/nv_defaults.cpp#L26-L40),
not in `generate.cpp`. The caller at
[`src/program/generate.cpp:3445-3461`](https://github.com/Niko1221/Strata/blob/99866a47a2b8/src/program/generate.cpp#L3445-L3461)
applies them only when every visible CUDA device has the same compute capability. This is the skipped
mixed sm_86/sm_89 case in [Strata#3313](https://github.com/Niko1221/Strata/issues/3313); pinning the table
also delivers its process-wide switches to the other card, so host A/B and greedy-identity evidence remain
required before qualification.

Install writes the pin with stock `setup.write_config` and refuses any existing config `env` rather than
merging it. `verify_generated` requires exact equality and refuses config `env` without a pin.
Env-pinned runtime identity additionally hashes `serve/server.py`; every start rehashes it and the config.
After ready, the config is read again and `run.json` records the canonical env SHA-256, sorted names,
server-source SHA-256 and this launch's engine-log interval. When self-commit is pinned, every batch-window
line must end `, one-row windows keep their rows`, and at least one must exist. Other groups have no invented
positive startup line. Process-environment inspection through undocumented Windows PEB structures is not
used: reviewed stock delivery, config identity and real engine evidence are the boundary.

The accompanying single-card setup pin is exactly `setup_args.kv_streaming: "off"` (engine 0.1.55+).
Stock setup spells it `--kv-streaming off`, with choices `auto`, `on`, `off`. The paired planner requires
off to differ from auto only by removing the `--kv-resident` pair; generated config keys, stock tips, model
files and URL must agree, and stock warnings still refuse. Install and every start refuse the streaming flag
or its `strata generate: KV streaming:` startup line. No positive non-streaming KV line was observed.
Newly adding off may replace setup-derived streamed-KV RAM floors with stock's non-streaming calculation:
the RTX 5090 131K and 262K plans both compute 34 GiB. A predecessor floor above the matching auto plan
(after the same tips) is operationally raised and is never lowered; driver and disk floors always keep max.
The floor derivation is recorded in the draft profile and report.

`strata.kv_grow: true` is a valueless, exactly-once `--kv-grow` pin, only on one card alongside KV streaming
off, on engine 0.1.55+. Startup must show the reviewed `strata generate: elastic K/V: ... as the context grows`
line from this launch, recorded in `run.json`. Neither pin changes the engine's batch-row kernels.
Drafts carry these decisions forward; `--ple-io stock` is the explicit exception that drops a carried direct-read
pin and stores no `stock` value. It refuses when there is nothing to drop and leaves the model block unchanged,
so an NVFP4 candidate can re-prove its existing prepared conversion rather than convert again.

## Stock OMP 18.16.0 surface

The reviewed target [`v18.16.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.16.0) pins
**`650f3a108229ee11bf68ba3377f4e8c3391cd424`**. Relative to v18.15.0, this needs **pin + documentation changes
only**, not a provider/config/transcript/gate shim. Published
[`SHA256SUMS.txt`](https://github.com/can1357/oh-my-pi/releases/download/v18.16.0/SHA256SUMS.txt) lists:

| Asset | Bytes (release inventory) | SHA-256 |
|---|---:|---|
| `omp-windows-x64.exe` | 243,591,168 | `c249a9ed0a57c748fb1247d8ee9e2d0fe1b13229266ce74d8810a76a591e21fc` |
| `omp-darwin-arm64` | 215,642,256 | `d4a10d97488d6054d2b18198bd24f461079952c7e0fb75ba66336ca0df0cb99e` |
| `omp-linux-x64` | 277,002,416 | `6498ed785bab00d2926e0387e0ec02362d6d45f1c3d0d1b57c1618b7f95c9264` |

The stock `openai-completions.ts`, `utils/openai-http.ts` and CLI flag table are byte-identical to v18.15.0.
The emitted settings and compatibility keys, JSONL conversation/compaction fields, RPC events and task routing
remain compatible. Memory still defaults to
[`off`](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/memory-backend/settings.ts#L11-L17);
no new memory setting or default egress is enabled by this admission.

Token counting now always uses the native family tokenizer, falling back to `o200k_base` for unclassified ids
([tokenizer:86-94,283-285](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/agent/src/tokenizer.ts#L86-L94)).
Our `qwen3.8-...` ids still classify through
[`qwen.kdl`](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/compat/rules/taxonomy/qwen.kdl#L1-L13)
and resolve to
[`qwen3`](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/model-tokenizer.ts#L27-L29),
as before. Do not infer gate results from that compatibility:

- **G13/G18/G18L:** keep the existing thresholds and method order, but record the actual method and every
  `tokensBefore`; handoff remains first for text-only models. G18L must still observe its >100,000-token bar.
- **G17:** retain >=100,000 peak prompt tokens with no compaction during the near-limit turn; classification is
  not a replacement for observing that boundary.
- **G19:** [journaled date/cwd reminders](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/session/date-cwd-reminder.ts#L4-L14)
  now replay their original placement on resume/revive, so prompt bytes and cache coverage can differ across days.
- **G23:** subagent `session_init.mountedTools` and revive/mount handling are additive. Re-prove every scout's
  completed delivery over the Studio → PRO route; the existing fan-out marker is unchanged.
- **G24 is not comparable to 18.15.0:** read paging/cut-byte accounting, write's truncated-projection/held-SQLite
  refusals, bash's `minimized` record and null/payload normalization change tool behavior or output.
- **G04:** the HTTP transport is unchanged; the existing HTTP-500 fault test still owns its twelve-request proof,
  rather than a new retry rule in the integration.

Profiles/routes and real-host qualification are separate from this source review; v0.2.9 + OMP 18.15.0 remains
the qualified tuple until their own records change.

## Stock OMP 18.15.0 surface

[`v18.15.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.15.0) pins
`3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`, including v18.14.1's and v18.14.2's intervening changes.
Release API digests agree with `SHA256SUMS.txt`:

| Platform asset | Bytes | SHA-256 |
|---|---|---|
| `omp-windows-x64.exe` | 243,250,176 | `978846a816cb77f44a55e32b16493375ca837fbf87e0aec35a9c1c934bff0cd0` |
| `omp-darwin-arm64` | 215,295,120 | `d36dfabf0ee52d6f08efadb59c46f0349545c6f6975522417adae29646e73e34` |
| `omp-linux-x64` | 276,785,328 | `6737ee2415555a3656cc7b89c14d1c25c18658ee4c0fd4f7309705149ccb7b0f` |

**Pin with documentation/draft-note changes, not a launcher or wire adapter change.** The chat-completions provider
only gained exports; its HTTP layer, the CLI flag table, print-mode events, session entry types, the HOME/`--profile`
layout, the apiKey contract and every emitted settings key are unchanged (`task.agentModelOverrides` only moved files).
Qwen3.8 still selects stock `replace` editing (`utils/edit-mode.ts`). Drafts run in API mode because download mode
refuses a changed OMP tag.

Watch on the hosts: [OMP#17499](https://github.com/can1357/oh-my-pi/pull/17499) rejects length-truncated handoff and
compaction summaries (G13 needs a compaction, G18/G18l a compaction entry with more than 100K tokens before);
[OMP#12229](https://github.com/can1357/oh-my-pi/pull/12229) always declares `model` in the task schema and refuses
an unapproved per-call model (G23 fan-out counts only completed results); long tool-call intents now run
([OMP#17486](https://github.com/can1357/oh-my-pi/pull/17486)) and short repeated status lines no longer count as a
thinking loop, so G24 tool-error counts are not comparable with 18.14.0. G04 still expects 12 requests for HTTP 500;
re-observe G15's interrupted-turn stop. None of this substitutes for host gates or promotes a route.

Qualified on 2026-11-02 and 2026-11-03
([tuning and pair override decision](DECISION.md#update-2026-11-02-evening-the-v029-tuning-profiles-on-the-pro-and-rtx-5090-and-the-studios-tuned-route-qualify),
[morning v0.2.9 decision](DECISION.md#update-2026-11-02-strata-v029-with-omp-18150-qualifies-on-every-host-and-the-studio-route),
[2026-11-02 tuning measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v029-2026-11-02-stock-omp-18150),
[2026-11-02 windows measurements](MEASUREMENTS.md#strata-v029-windows-2026-11-02-stock-omp-18150)): on the PRO,
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking-strata0.2.9-omp18.15.0` (current, pinning
`strata.batch_mtp: true`, `--batch-mtp`, `strata.ple_io: "direct"`, `--ple-io direct`, `setup_args.kv_streaming: "off"`,
`--kv-streaming off`, and `strata.engine_env` `parallel_stack` + `gdn_stack`), rolling back to the `v0.2.9` base profile
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0` (`v0.2.8` moves to earlier
qualified history); on the RTX 5090, the 262K default
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg-strata0.2.9-omp18.15.0` (pinning `setup_args.kv_streaming: "off"`,
`strata.kv_grow: true`, `--kv-grow`, and `strata.engine_env` `gdn_stack`; 34 GiB start floor, with Docker Desktop and
WSL stopped), rolling back to the `v0.2.9` base profile `win11-rtx5090-coder-iq1m-262k-strata0.2.9-omp18.15.0` (36 GiB
start floor; `v0.2.8` 262K moves to earlier qualified history; the unpinned-GDN fallback
`win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-strata0.2.9-omp18.15.0` stays an uninstalled draft), and the 131K
alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.9-omp18.15.0`, qualified for running with Docker Desktop and WSL
up, rolling back to its `v0.2.8` + OMP `18.14.0` predecessor); on the pair,
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`
(current, pinning manual `layer_split: "24"`, `strata.trim_stage_weights: true`, `--trim-stage-weights`,
`strata.ple_io: "direct"`, `--ple-io direct`, and `strata.engine_env` `sm86_table` + `gdn_stack`, with 19.15 / 17.76 GiB
expert caches, 27.77 GiB G10 commit headroom, 43.5–43.9 s chain restart readiness and the 8,192 MiB automatic
conversation cache, qualified on 2026-11-03 after the owner overrode its `w1` 512/512 single-request A/B miss at `1.039`
vs `>= 1.05`, rolling back to its `v0.2.9` base profile
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`;
`v0.2.8` moves to earlier qualified history); and on the Mac Studio
client, the independent Studio→PRO route
`client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.9-omp18.15.0` (current), rolling back to
`client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.9-omp18.15.0` (`v0.2.8` routes stay earlier qualified history).
The PRO's `v0.2.9` model candidates
(`win11-rtxpro6000-ud-iq4xs-262k-slots4-batchmtp-pledirect-parking-strata0.2.9-omp18.15.0` and
`win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-strata0.2.9-omp18.15.0`, plus the earlier `--ple-io direct` NVFP4-QAD
screen draft `win11-rtxpro6000-nvfp4-qad-262k-slots4-batchmtp-pledirect-strata0.2.9-omp18.15.0` and the two model-candidate
Studio routes) stay comparison-only drafts.
[`releases/campaigns/v0.2.9.json`](../releases/campaigns/v0.2.9.json) is complete across all five `hosts[]` entries;
no default-runtime switch against NInfer follows.

## Strata v0.2.8 setup review (component engine)

Stable [`v0.2.8`](https://github.com/Niko1221/Strata/releases/tag/v0.2.8), GitHub release **428450803**,
published **2026-10-29T22:40:43Z**: annotated object `878ef09cc9092a41a37dac32fd6fe461e47fa326`,
peel `870aedd9e1ebe1c91f94da93b59af17729f6c5c0`. Compared with stock v0.2.7
(`5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`). App **0.2.8** ships Windows CUDA 13 engine **0.1.54**:
`strata-engine-0.1.54-windows-x86_64-cuda-cuda13.tar.gz` (620,425,196 bytes), SHA-256
`bacff012e5f7e44ffefd5a08230363e0e527c8a86abf55ef1b31c833be37b8ab`;
manifest SHA-256 `ecdc65171aa2b3d34dfcb1acff4e20efd78aee1f72b8e5ee3abe4dafe90033d3`;
build `8c1aea4bca1b+cuda13.0`, BUILD source `f-028-rel`, BUILD commit `8c1aea4bca1b`.
Archive/member hashes and BUILD identity were inspected without executing a binary; component-signature
verification is not claimed. The build commit did not resolve in the public upstream review, so the source
review is not a source-to-binary attestation; native startup observations remain required.

### Reviewed planning and dependency delta

The unmodified report/draft refused `new call in stock setup planning; review required`: the args If-chain
now calls `is_gb10`. After that boundary, the multi-GPU config block also gains a HIP-only four-card
`try`/import. Admit only the following exact bodies, not new general `pure_exec` calls, attributes or builtins:

| Reviewed entry | Full-field AST SHA-256 | Decision |
|---|---|---|
| `is_gb10` | `6f0fb0371f2d1a1f6b77af3105df196536cf4a01b498e2f2da35eedf9467f79d` | Run the pinned helper with fixed `is_arm64=False` for the selected `windows-x86_64` asset lane; never inspect the planning machine. |
| Args If-chain containing the GB10 arm | `c363d510549a35b71d9c23d59495111f808259e64d043b35df64acdb4ab8fc03` | Only this statement may call `is_gb10`; the arm is unreachable and cannot add `--mmap-experts`, `--mtp-q4` or `--mtp-hnorm` to these plans. |
| Multi-GPU config block | `778de3208b1749e4ab66129d0878c3c5863544c0b886418cf5e71a2829b905bb` | Preserve the existing roles/config projection; evaluate the appended HIP guard on every lane and require false, without validating or executing its body. |
| Appended HIP sub-statement | `fc3cda7f10606a3e67207c05458d91ccedaa41c394ea0174501154d525325f52` | Covered by the whole-block pin, not independently admitted. Edited/reachable/moved HIP code refuses. |

The source-faithful `strata_0_2_8_plan.py` fixture uses v0.2.7's same selection plus `is_gb10`;
only those two `main()` statements differ. Five-plan comparisons preserve explicit flags, generated keys,
model files, thresholds, host floors, slots and roles. Helper/caller mutations and a new callsite refuse;
planning with an ARM64 Linux planning-machine identity yields the same five plans.

CUDA-12 driver-floor helpers, ARM64/DGX Spark installation, macOS DeepSeek and the packaged-Terminal
`source_version()` fallback are outside the selected Windows CUDA 13 Qwen paths and are not admitted.
`requirements.txt`, `requirements-monitor.txt`, build requirements, `PY_PACKAGES`, `CUDA_WHEELS`,
`LLAMA_CPP_COMMIT`, the runtime-input helpers/caller, user-args stamping and MTP inputs are unchanged.
Drafts reuse `locks/strata-python-cp313-win_amd64-strata0.2.7.txt` (26 hash-locked wheels);
no new `--python-lock` is supplied.

### Stock defaults and lane applicability

| Stock engine 0.1.54 change | Applicability and fresh-observation boundary |
|---|---|
| Tool-call recovery defaults on | All lanes, declared tools only. Stock setup writes no `tool_call_recovery` key and none is pinned. Quoted-tool-syntax handling, missing function closers, lenient non-string JSON arguments and stray closing think-tag repairs are always on, independently of recovery. |
| [Strata#4518](https://github.com/Niko1221/Strata/issues/4518): PLE lock release | Automatic residency still requires table, expert arena and headroom to fit; the policy gives its lock back when it would starve the automatic conversation cache. On the measurement-only pair residency draft on Windows (`rtx3090-win-a`), the policy locked the 26.8 GiB table (33.9–34.0 s), then gave the lock back on both starts and sized the cache at 4,864 MiB (106–112 s to ready), against 8,192 MiB and 61–63 s to ready with `--ple-io direct` (27.9 GiB G10 commit headroom on `roles-pledirect`, 27.8 GiB on the current split-24 trim + PLE-direct profile). The qualified pair profiles keep `--ple-io direct`, so neither automatic residency nor its lock release applies there. |
| [Strata#4420](https://github.com/Niko1221/Strata/issues/4420): richer shared-prefix checkpoints survive slot overwrite | PRO's pinned four batch slots and its remote fan-out; not the slot-free 5090 or pair lanes. Measure reused/cached tokens rather than infer a gain. |
| [Strata#4474](https://github.com/Niko1221/Strata/issues/4474): automatic expert-cache reserve | Every lane leaves about 256 MiB more VRAM free, when the minimum cache still fits; on the pair the changed automatic sizing is stage 0, not the later-stage cache. No reserve override is added. |
| [Strata#4051](https://github.com/Niko1221/Strata/issues/4051): memory-return waits | All restarts may wait up to 20 s for arena RAM; server startup waits up to 120 s only for a recorded leftover/orphan engine. Existing 900 s readiness limits and the 5090 262K 36 GiB startup floor stay unchanged. |
| Residency-biased route prior defaults off | Already off for these 24/32/96-GB NVIDIA cards; the predecessor's small-card default does not apply. |
| HIP 16-row speculative windows | Unreachable; NVIDIA/CUDA remains at 8. No wide-window build or flag is selected. |
| Carried topology defaults | Int8 prompt attention; SM120 wide-up and stream-split hyper-connection reads, with single-card layer-major prefill off. Eligible split prompts retain layer-major prefill and Ada MMVQ row tables. Two-card pipelined batch groups require slots, which the pair keeps off; `--pipeline-windows 2` remains a separate decode pin. |

The real-source GET/POST/OPTIONS census has no route change, no lost route and no unclassified route;
G13's matrix is unchanged. Config keys and reviewed constants are unchanged. The environment-name census adds
`STRATA_ARENA_RAM_WAIT_S`, `STRATA_ATTN_BATCH`, `STRATA_DS4_METAL_CTX`, `STRATA_FOUR_CARD_PROFILE`,
`STRATA_GPU_TRACE`, `STRATA_METAL_NEIGHBOURS`, `STRATA_P4_TIMING`, `STRATA_P4_TRACE`,
`STRATA_PF_TILE_DEBUG`, `STRATA_PIPELINE_DUMP`, `STRATA_SM121_PERF` and `STRATA_VERIFY_PROFILE_EVERY`;
none is granted as a profile override, and inherited `STRATA_*` remains scrubbed.

**Engine 0.1.54's stage order is admitted to `lifecycle.STAGE_ORDER_REVIEWED_ENGINES`** (`4853ab3`). Host-free
full-field AST comparisons show `gpu_list`, `layer_split_value`, `layer_split_of`, `ordered_gpus`, `engine_args` and
`child_env` identical to v0.2.7. `parallel_args` changes a warning only, not returned flags; the stage-order,
layer-boundary and primary-cache message formats are unchanged. The source still parses the pinned `--ple-io direct`,
`--pipeline-windows 2`, `--prefill auto:32768` and `--pool-workers`. In the 2026-10-30 pair measurement window, all
four starts across the PLE-direct candidate and the stock-residency measurement arm parsed complete with the reviewed
parsers: RTX 3090 first, RTX 4090 last, layers 0–23 / 24–47 (auto K=24, expert caches 17.35 / 16.01 GiB;
[MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-stage-order-and-strata4518-on-engine-0154)).

G15/G16 must observe the changed waits; G19/G23 must measure cache behavior. G24 is not like-for-like with
v0.2.7 because recovery and repairs change tool-call outcomes: retain repair/unread-call metrics and new parser
log counts per attempt. [The OMP review](#stock-omp-18140-surface) supplies the other half of this tuple.

## Stock OMP 18.14.0 surface

[`v18.14.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.14.0) pins
`31147f9d1a76608549821c3759f8487b4d66c72d`, including v18.13.3's intervening changes.
Release API digests agree with `SHA256SUMS.txt`:

| Platform asset | Bytes | SHA-256 |
|---|---|---|
| `omp-windows-x64.exe` | 242,797,056 | `620a5935cdb6a9ed52d8b0c93892d6b5bb84155244a98f3be82af0455177bf29` |
| `omp-darwin-arm64` | 214,816,912 | `608843959ab34295d52460dd09dd7d548b6c903c08a83c67954c2d4c36fd1f5a` |
| `omp-linux-x64` | 276,244,656 | `e7dd2b606c4ebe9d1a7bcfad1b8820db968cd6b05409fed1c6bc8db0b6a95a8f` |

**Pin with documentation/draft-note changes, not a launcher or wire adapter change.**
`THIRD-PARTY-NOTICES.txt` is no longer a release asset; the integration pins none of it or the browser-relay zip.
The CLI flag table is identical to v18.13.2. Every emitted setting and model compatibility key remains registered.
**Correction to the earlier private source-review note:** `startup.checkUpdate` is registered
(`modes/settings.ts:1138`); keep the existing emitted key, already exercised by the pinned-binary settings test.

[OMP#16297](https://github.com/can1357/oh-my-pi/pull/16297) requires exact provider-qualified model references.
Our `models.yml` ids, CLI selectors, `modelRoles` and `task.agentModelOverrides` already use the same complete
`strata-local/<served-id>` or `strata-<label>/<served-id>` string, so exact lookup succeeds by construction.
No selector, routing or fallback override changes. Qwen3.8 still selects stock `replace` editing
([OMP#17096](https://github.com/can1357/oh-my-pi/pull/17096)); the draft note now applies to OMP >=18.13.2,
with no edit-mode override pinned.

[OMP#17231](https://github.com/can1357/oh-my-pi/pull/17231)'s reasoning estimate change is a no-op for our
loopback chat-completions providers: they replay their own thinking. Request shape, fitted token limits,
stream finish handling, transcript continuation and compaction defaults are unchanged. Local first-event
timeouts stay disabled; the 300 s idle timeout and two-layer HTTP retry path remain (G04 still expects 12
requests for HTTP 500). Provider loading is now lazy, so a real pinned-binary first request must prove bundling.

`out://` is default-off in print/RPC/ACP and remains unset. Bun's cooperative yield/keepalive workaround was
removed from streaming/tool/task paths; watch client CPU, turn timing and G23 task/wait completion, without
assuming earlier timing or token counts. Bash builtins and tool text changed, not the explicit tool-name set.
Re-observe G15 abort handling after [OMP#17216](https://github.com/can1357/oh-my-pi/pull/17216), G17/G18 long
sessions, G13 per-process egress after lazy provider/catalog loading, and G23/fan-out after task wake/relay
changes. Host-free flag-census, effective-setting, fault/retry and truncated-argument tests run against the
new pinned client; none of that substitutes for host gates or promotes a route.

Qualified on 2026-10-30 and 2026-10-31
([DECISION.md](DECISION.md#update-2026-10-31-stock-v028-tuning-profiles-and-the-studio-batch-mtp-route-qualify),
[2026-10-31 measurements](MEASUREMENTS.md#stock-tuning-pins-on-strata-v028-2026-10-31-stock-omp-18140),
[2026-10-30 measurements](MEASUREMENTS.md#strata-v028-windows-2026-10-30-stock-omp-18140)): on the PRO,
`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0` (current, pinning
`strata.batch_mtp: true`, `--batch-mtp`, and `strata.ple_io: "direct"`, `--ple-io direct`),
`win11-rtxpro6000-iq3s-262k-slots4-pledirect-parking-strata0.2.8-omp18.14.0` (qualified alternative, PLE direct reads
only) and `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0` (rollback); on the RTX 5090, the 262K
default (`win11-rtx5090-coder-iq1m-262k-strata0.2.8-omp18.14.0`, now the host's default with Docker Desktop and WSL
stopped; main-chain G10 listener failure on Windows build 26300.9818 retained beside the passing `f9e8c74` rerun) and
131K alternative (`win11-rtx5090-coder-iq1m-131k-strata0.2.8-omp18.14.0`, qualified for running with Docker Desktop and
WSL up; main-chain G10 failure retained beside the passing `f9e8c74` rerun), rolling back to their `v0.2.7` + OMP
`18.13.2` predecessors; on the pair,
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`
(current, pinning manual `layer_split: "24"`, `strata.trim_stage_weights: true`, `--trim-stage-weights`, and
`strata.ple_io: "direct"`, `--ple-io direct`, with 19.15 / 17.76 GiB expert caches, 27.8 GiB G10 commit headroom and
the 8,192 MiB automatic conversation cache) rolling back to
`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0` (27.9 GiB commit
headroom); and on the Mac Studio client, the independent Studio→PRO route
`client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0` (current) rolling back to
`client-rtxpro6000-262k-strata0.2.8-omp18.14.0`. The pair's `v0.2.8` stock-residency draft
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`) stays a measurement-only draft.
[`releases/campaigns/v0.2.8.json`](../releases/campaigns/v0.2.8.json) is complete across all five `hosts[]` entries;
no default-runtime switch against NInfer follows.

## Strata v0.2.7 setup review (component engine)

Stable `v0.2.7`, published 2026-10-27T14:54:42Z: annotated object
`3f6d9c28e56bfce604601f39de53d457fa90dc74`, peel `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`.
Compared with stock v0.2.3 (`5c8dd322528cc84f68f461ad54a506b9da8fa8d4`).
App/Terminal **0.2.7**, Control and engine **0.1.52** are separate component versions.
The selected Qwen asset is `strata-engine-0.1.52-windows-x86_64-cuda-cuda13.tar.gz`
(620,430,878 bytes), SHA-256
`bfa68c6b2e92f9c273caaf937d9ae164918e6de4cca2dc1f1d79d32470f0915a`;
manifest SHA-256 `1e0e8828f64522bda7a866625c1a47822c53a93abaf8a1b7eb80e9887d69749b`;
build `a42cc3d7df70+cuda13.0`, BUILD source `f-027-rel`, BUILD commit `a42cc3d7df70`.
Archive/member hashes and BUILD identity were inspected without executing a binary; component-signature
verification is not claimed. After [`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json) froze the
release asset inventory, upstream amended the same `v0.2.7` GitHub release in place with its `0.2.7.1` assets
(Control `0.1.53`, ARM64 and macOS DeepSeek packages, and updated installer/feed metadata); every frozen asset used
here is still present, and the pinned Windows CUDA 13 Qwen engine asset above is unchanged.

### Reviewed planning and dependency delta

The unmodified report/draft refused `new call in stock setup planning; review required`: `resolve_rope`
now rejects explicit non-finite or sub-unit factors with `math.isfinite`. Admit only its exact helper,
not a new general `pure_exec` call. Pair planning additionally needs the exact changed `gpu_problem`;
its new Maxwell advice is unreachable for the planner's already-required compute capability >=7.5.

| Reviewed entry | Full-field AST SHA-256 | Decision |
|---|---|---|
| `resolve_rope` | `5f7b7cf3cac4e93371dfb722d39b1aafe58d73b0a83a86cd985d67e3e61a2981` | Pure validation; our explicit contexts stay inside 262144 and pass no factor. |
| `gpu_problem` | `454eda73ba81a3199f5ec13382876d3cd5d9e3bd9c3d0f37cd5edf1ae1c98a41` | Maxwell-only refusal text; no new card generation admitted. |
| `runtime_packages` | `b004722bb3aa164aa266d9b009bb85f846e62a15044cac9aa38b4937139afa1b` | Check, never execute its file reads; both shipped requirements files are consumed by native setup. |
| `requirement_lines` | `367fbc3d2049d4f912e9087381356a59bb940b2da6fd19e776f978e7774073c7` | Unchanged comment/blank-line filtering; check, never execute. |
| `REQUIREMENTS` assignment | `0f146fda709be127bb86cf4ffede8a8ff60527789751b3a5215b6f4500c9080d` | Fixed source-root `requirements.txt`. |
| `MONITOR_REQUIREMENTS` assignment | `f7cb1bbc75fc8f5e3200682363a5bcdcc267174a15e563c7017ffb41b54a9f18` | Fixed source-root `requirements-monitor.txt`. |
| Native `pip_install(runtime_packages(), ...)` call | `5c5e54935d65a0b6ede5f08219b5859e90ab7ef9edea61eaf3c9f5aec374384e` | Exactly one native runtime-package call; no TUI/interactive condition. |

**The runtime requirements file is unchanged, but the consumed dependency set is not.**
`requirements.txt` retains blob `903773a12b614f6a1f39d14f2afb9a9e305a10b5`; build requirements,
`PY_PACKAGES`, `CUDA_WHEELS` and `LLAMA_CPP_COMMIT` are unchanged. Native setup now always calls
`runtime_packages()`, which adds the shipped `requirements-monitor.txt` (`textual==8.2.8`), even for
`--yes --no-start`. The old 17-pin lock would leave setup trying to install a missing package under
`PIP_NO_INDEX=1`; reusing it is refused with `--python-lock` guidance.

The new `locks/strata-python-cp313-win_amd64-strata0.2.7.txt`
(SHA-256 `a5c1a1c100ce955019c272abcca29d80f7e7c20d348c267c855965c12be69a90`) contains 26
hash-locked wheels, resolved host-free for `win_amd64`, Python 3.13, `cp313`, binary wheels only.
The 17 predecessor pins stay; additions are textual 8.2.8 and its reviewed transitive closure:
linkify-it-py 2.2.0, markdown-it-py 4.2.0, mdit-py-plugins 0.6.1, mdurl 0.1.2, platformdirs 4.13.7,
pygments 2.21.0, rich 15.0.0 and typing-extensions 4.16.0. No syntax/Jupyter/test extra is selected.
Drafts require exactly the consumed roots, these reviewed transitives and CUDA wheels; missing, conflicting,
extra or changed pins, changed input helpers/paths/caller, or another interpreter's closure are refused.
This preserves `install_python`'s `--no-deps` installation and stock setup's no-index boundary.

`bench_tips`, the disk-estimate group, fresh-config writers, user-args stamping and `tools/mtp_fetch.py`
(blob `8968dfa509581b657537da0047683b9fffb5cef1`) are unchanged. Existing Qwen/Coder/MTP revisions and
tensor pins stay. The `HF_REVISIONS` additions are only DeepSeek entries: `deepseek41` planning, its engine,
packing, vision, large-context and automatic updater paths remain outside this review and refused.

### Stock defaults carried by the drafts

The five native drafts preserve their predecessors' explicit flags, config keys, model/context, slots,
roles, pipeline windows and conservative host floors. New behavior is stock engine behavior, not an added
environment or flag override:

| Lane | Engine 0.1.52 defaults that need fresh measurement |
|---|---|
| PRO slots4 | CUDA prompt attention uses int8 tensor cores; SM120 wide-up and stream-split hyper-connection reads default on. `--parallel 4`, `--prefill auto:32768`, `--pool-workers 15` stay pinned. |
| RTX 5090 131K and 262K | The same SM120 defaults; contexts stay 131072 and 262144, no slots. Single-card layer-major prefill stays off. |
| Pair roles and default A/B | Eligible split prompts default to layer-major prefill (`sm120_series.hpp` / `Prefill::run`); the Ada card defaults to its new MMVQ row tables. Two-card batch groups now default to pipelining only when batch slots exist (`batch_groups.hpp`); both profiles keep slots off. `--pipeline-windows 2` is a separate existing decode pin. |
| Every server | RAM PLE residency is now automatic only when its table, the expert arena and headroom fit; conversation parking remains RAM-dependent. Neither residency nor a measured speed/quality outcome is inferred from source. |

`STRATA_DEFAULTS=026` and per-feature switches are upstream A/B controls, not granted profile settings;
inherited `STRATA_*` remains scrubbed. No 12-GB residency-biased-routing default applies to these cards.
The v0.2.3 → v0.2.7 GET/POST/OPTIONS census adds GET `/tool-media/`, `/web/locales/` and
`/web/vendor/`, and loses no route. The latter two are the web app's whitelisted translation and
vendored KaTeX files: public static subtrees under the existing `/web/` prefix. The census now reads
literal `startswith` tuples as well as scalar prefixes, so neither subtree is hidden from review.
Stock `serve/server.py`'s `/tool-media/` branch requires the API key before serving MCP tool-result PNG/JPEG/WebP files
named by 64 lowercase hex digits plus an extension from the MCP hub's media directory. MCP is
unconfigured in these profiles, so G13 sends missing/wrong bearer and wrong `x-api-key` probes
(expected 401), then a correctly shaped filename with the correct key (expected 404), like its existing
unconfigured-image probes. These GET key checks start at engine 0.1.52; earlier unrouted GETs are not
authentication evidence. Source-branch and scripted-server tests prove the host-free contract, not G13
on a GPU host.

**Engine 0.1.52's stage order is admitted to `lifecycle.STAGE_ORDER_REVIEWED_ENGINES`** (`15c7426`). `gpu_list`,
`layer_split_value`, `layer_split_of`, `ordered_gpus` and `engine_args` are AST-identical to v0.2.3;
`child_env` changes only DeepSeek and HIP branches, unreachable here. The CUDA layer-boundary and primary
expert-cache message formats still match the parser. On the RTX 4090 + RTX 3090 pair, both starts of the roles
draft parsed complete with the reviewed parsers (RTX 3090 first, RTX 4090 last, layers 0-23 / 24-47, auto K=24;
[MEASUREMENTS.md](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132)). The default-split draft was
stopped during download and stays an unmeasured draft; roles evidence does not transfer to it.

### Stock OMP 18.13.2 surface

The drafts pin `e996e1c7ac476f60e02b8ed9764cf30fa8c00a8e`, with all three platform asset digests
resolved from the release. Keep stock behavior: [OMP#17096](https://github.com/can1357/oh-my-pi/pull/17096)
selects the `replace` edit tool for Qwen3.8 served IDs, instead of the predecessor's hashline tool.
No edit-mode setting or environment pin is added; tool/edit and long-session qualification must be fresh.
[OMP#17151](https://github.com/can1357/oh-my-pi/pull/17151) adds `ast_grep` to the bundled scout. Our
additional named scouts remain explicitly read/find/grep/glob; `fanout_proof` requires those named agents,
not the empty-map single-PRO route, and pins no bundled-scout tool census.
The pinned-binary CLI census also adds `--warn-cost` and `--max-cost`. Source review of
`cli/flag-tables.ts` and `main.ts` at v18.13.2 admits these USD thresholds as runtime-only
session-cost overrides, not routing/configuration/discovery overrides. The launcher policy test
retains its fail-closed census for every other unreviewed value-taking option.
[OMP#17159](https://github.com/can1357/oh-my-pi/pull/17159) follows linked continuation copies by newest
conversation turn. At `v18.13.2`, `session-manager.ts` records the predecessor's session id in both
`parentSession` and `continuationOf`; deliberate forks set only `parentSession`. Transcript readers join
only `continuationOf` links within a profile bucket, following `session-listing.ts`'s conversation-entry
timestamps rather than file mtime, exit records, idle usage or eval-state snapshots. An ancestor whose
newest turn is carried by a descendant is superseded; divergent copies with no unique newest turn,
duplicate ids and cyclic links fail closed. G23, fan-out and local gates select the requested workspace's
one conversation, not one file across the whole home. G23 permits a changed path only through those
links and still checks all previously persisted history entries in order, excluding the replaced header
and mutable title slot. G19 reselects its A transcript after the explicit `--resume` turn before
reporting per-request usage, since that turn can create another linked copy. Two-file regression tests
cover selection, history preservation and that post-resume evidence refresh.

Qualified on 2026-10-28 under the owner's overnight fleet authorization and afternoon qualification decisions
([DECISION.md](DECISION.md#update-2026-10-28-afternoon-the-pairs-ple-direct-and-rtx-5090-262k-strata-v027-profiles-qualify),
[MEASUREMENTS.md](MEASUREMENTS.md#strata-v027-windows-2026-10-28-stock-omp-18132)): the PRO
(`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2`), RTX 5090 131K default
(`win11-rtx5090-coder-iq1m-131k-strata0.2.7-omp18.13.2`), RTX 5090 262K opt-in
(`win11-rtx5090-coder-iq1m-262k-strata0.2.7-omp18.13.2`, qualified on its afternoon rerun with the host's Docker
Desktop and WSL stopped so 39.8 GiB RAM was available against the unchanged 36 GiB floor; morning failed receipts
with the resident VM are retained), pair PLE-direct stock-roles profile
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`, pinning
`strata.ple_io: "direct"`, `--ple-io direct`, with 27.3 GiB G10 commit headroom and the 8,192 MiB automatic
conversation cache enabled across all 16 starts) and independent Studio→PRO route
(`client-rtxpro6000-262k-strata0.2.7-omp18.13.2`). The pair's `v0.2.7` roles draft with PLE in RAM
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.7-omp18.13.2`; G10 commit headroom 1.03 GiB
and conversation cache off, [Strata#4518](https://github.com/Niko1221/Strata/issues/4518)) stays a held draft, and
the unmeasured pair default-split draft
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-parking-strata0.2.7-omp18.13.2`) stays unqualified.
[`releases/campaigns/v0.2.7.json`](../releases/campaigns/v0.2.7.json) is complete across all five `hosts[]` entries;
no default-runtime switch follows.

## Strata v0.2.3 setup review (component engine)

Stable `v0.2.3`, published 2026-10-23: verified annotated object
`cad69daf8cbde12ef1fafd891ad69288e0ed2501`, peel `5c8dd322528cc84f68f461ad54a506b9da8fa8d4`.
The comparison is against `011c9e600a93bbc9fd451c563501b5831c32bbca` (v0.2.2).
App **0.2.3** ships engine **0.1.48**:
`strata-engine-0.1.48-windows-x86_64-cuda-cuda13.tar.gz` (581,299,508 bytes),
SHA-256 `1e1611b0977d984bd7d8e79591a1ba1a7e550a2f4a66bfa45744a77308a71b95`;
manifest SHA-256 `1767034593452895ad32d9aaa66c611ee7bec0fe09194b0ae154df2de96e1a6f`;
build `6f8800aefe27+cuda13.0`, BUILD source `f-023-rel`, BUILD commit `6f8800aefe27`.
As for v0.2.2, archive/member hashes and BUILD identity were verified without executing the binary;
component signature verification is **not** claimed.

### Reviewed planning delta

The unmodified report refused `stock split disk estimate changed; review required`. Two new full-field AST hashes
are admitted; every other v0.2.2 entry below is unchanged and still refuses any edit.

| Reviewed entry | SHA-256 | Decision |
|---|---|---|
| `bench_tips` | `05d188a10a65e59ba0365cd58ffa7a3d576d3023877aca3ed60dbccd434714c3` | Stock no longer recommends `--conversation-cache-mib` (the engine sizes the cache itself, below); the `--prefill` tip is unchanged. Drafts drop the predecessors' pinned parking tip and its flag. |
| `margin`, `mtp_fetch`, `real`, `need` group | `0d2db520b5dc89ec6b45ae88bf30a822ef6ea5a1c44ee6682169aa7575a144ce` | Pure arithmetic: 5.2 GB for the MTP drafter joins `real` while it is missing and setup is not ready. The PRO and pair disk floors rise from 90 to 91 GiB; the 5090 floors stay 90. |

- **Engine 0.1.48 parks conversations when the RAM allows** (Strata#3493). Without `--conversation-cache-mib`, the
  server sizes the conversation cache after load: 40% of the free RAM above its 2,560 MiB floor, at most 8,192 MiB,
  off under 1,024 MiB, with one log line; an explicit value (0 included) is kept. Whether a start keeps
  conversations is therefore the engine's call (`Profile.parks_automatically`): G19 reads `/metrics`
  `conversation_cache` and runs its kept-conversation probe unless the engine reports the cache off. Observed on
  2026-10-23: 8,192 MiB on the pair, 1,024-1,280 MiB on the RTX 5090 131K, off on the RTX 5090 262K. The cache
  takes at most 40% of what is left after load, so start floors need no new reservation; G21 measures it.
- **Stock GPU roles and one manual split point become pinnable.** The v0.2.2 `if multi` and `_roles` blocks are
  unchanged. A profile that pins `setup_args.gpu_roles` (`draft --gpu-roles 0=main,1=helper`) now evaluates the
  reviewed role writes, only in a namespace restricted to `getattr`, `isinstance`, `len`, `list`, `set`, `sorted` and
  `str`. Roles name every card Main or Helper (no Off), exactly one Main; the engine order is Helpers by card number,
  then Main, as stock `gpu_roles.engine_order` gives the server, with `gpu_order: "as_given"`. `--layer-split N`
  pins one split point for two cards and never combines with roles. Explicit `--gpus` without either option keeps
  the v0.2.2 behavior. The vendored v0.2.3 ordering code (`tests/fixtures/strata_0_2_3_server_order.py`) shows the
  pair's three drafts staging the RTX 3090 last (default, the #1576 VRAM guard), the RTX 4090 last (roles) and the
  configured order (split 32); `start` refuses a manual split whose engine boundaries differ from the pin.
- **Dependencies.** `requirements.txt` changed (blob `903773a12b614f6a1f39d14f2afb9a9e305a10b5`, was
  `b6f4d38ba2e2e477fc9307b20d7552e0f78a6e52`): certifi 2026.7.22 → 2026.10.19 and `truststore==0.10.5` added;
  `requirements-build.txt` is unchanged (`ebdef8ebb3174d696f5b4e332f6681aa9ba5f887`). `draft` now refuses changed
  requirements unless `--python-lock` names a lock pinning exactly them. The new
  `locks/strata-python-cp313-win_amd64-strata0.2.3.txt` (SHA-256
  `1e09fc5efbf63c36c835d87de53b883369f7e91c682dfcdd9723e57f0cd0ea03`) pins the 15 runtime requirements for
  win32/CPython 3.13 plus both `CUDA_WHEELS`, resolved host-free with `pip download --no-deps --only-binary=:all:`
  for `win_amd64`/`cp313`. Of its 17 pins, 15 match the v0.1.31 lock's version and hash; cmake and ninja,
  build-only upstream since, are not in it. `MIN_ENGINE` (0.1.46), `MIN_DRIVER`, `CUDA_WHEELS`, `PY_PACKAGES`,
  `LLAMA_CPP_COMMIT` and `HF_REVISIONS` are unchanged.
- **Operating-system certificates** (Strata#3722): the new `strata_control/tls.py`
  (`8c27ee54a92b93e7e88e2712dff773dc3e165e2f`) installs `truststore` in `setup.py` and `tools/mtp_fetch.py`
  (`8968dfa509581b657537da0047683b9fffb5cef1`, was `14898aef05637148aaa1cf74f8aeee7697e6824d`). The MTP revision
  pin and tensor hashes are unchanged; installation still accepts only pinned, hash-verified inputs.
- Generated config keys and the route census are unchanged for plans without roles; a roles plan adds `gpu_roles`
  and `gpu_order`. The environment census adds 21 names since v0.2.2, none removed: `STRATA_DATA_DIR`,
  `STRATA_DF2_FORK`, `STRATA_DF2_PRIO`, `STRATA_DF2_PROFILE`, `STRATA_DF2_SKIP`, `STRATA_DF2_TIMING`,
  `STRATA_DF2_WAITCOMMIT`, `STRATA_GFX1151_CHUNK`, `STRATA_GFX1151_EXP8`, `STRATA_OUT`, `STRATA_PROMPTS`,
  `STRATA_ROUTE_STATS`, `STRATA_SPEC_ADAPT_EVERY`, `STRATA_SPEC_ADAPT_SM86`, `STRATA_SPEC_ADAPT_WARM`,
  `STRATA_SPEC_COST`, `STRATA_SPEC_COST_TABLE`, `STRATA_SPEC_TRACE`, `STRATA_SPEC_T_CYCLE`, `STRATA_TAP_FILE`,
  `STRATA_TAP_LAYERS`. Inherited `STRATA_*` remains scrubbed; no environment opt-in is granted. DFlash2
  (`strata launch --drafting dflash2`) is Terminal-only and not used.
- Server-side tool-call parsing changed (Strata#3556: tool-name aliases and wrapper boundaries); the typed-tool and
  agent gates exercise it on each host, not this source review.
- **Engine 0.1.48's stage order is admitted** to `STAGE_ORDER_REVIEWED_ENGINES`
  ([#48](https://github.com/alphastorm/omp-strata/issues/48), opened for 0.1.47, which no multi-GPU profile runs).
  Source: `ordered_gpus` adds only stock roles' early return (the configured order, no message) and a HIP-only
  built-in-graphics branch; `layer_split_value`, `layer_split_of` and both engine message writers are unchanged.
  Host: every start of the pair's default, roles and split-32 drafts parsed complete with the order and boundaries
  those settings give ([MEASUREMENTS.md](MEASUREMENTS.md#strata-v023-windows-2026-10-23-stock-omp-18126)).

### OMP 18.10.1 → 18.12.6 client delta

The release notes of v18.10.2 through v18.12.6 change nothing `ompcfg.py` writes. The pinned-binary suite found two
client changes:

- **Subagents answer in plain text** (v18.10.2): task-spawned subagents return their final message, with no `yield`
  tool or output schema unless `task.structured` (default off) or agent frontmatter asks for them. The completed
  `<task-result>` envelope is unchanged. The fan-out proof's assignments and the generated fleet scout instructions
  now name both channels, and the mock fleet tests answer through whichever one the pinned binary offers.
- **`--restore`** (v18.10.3): resumes a session as `--resume` does, then continues its unfinished turn and
  subagents. It chooses no provider, model or configuration, so the launcher passes it like `--resume`.

Drafts, not qualified: the PRO, both 5090 lanes, the pair's default, roles and split-32 profiles, and the Studio
route against the new PRO, all on stock OMP 18.12.6 (`45c35e40c46166dc726ccc52f5d27f40f2449f99`). The 2026-10-23
windows ran the three server chains and the pair measurement; reruns, the pair's chain, receipts, G23 and the
owner's qualification decision remain.

## Strata v0.2.2 setup review (component engine)

Stable `v0.2.2`, published 2026-10-21: verified annotated object
`e6fff4ad12908de74952abe53b2bade45a68aa0f`, peel `011c9e600a93bbc9fd451c563501b5831c32bbca`.
The comparison is against `90767252f420e25223c739d604145ad15911d48b` (v0.2.1).
App **0.2.2** ships engine **0.1.47**, not engine 0.2.2:
`strata-engine-0.1.47-windows-x86_64-cuda-cuda13.tar.gz` (580,428,476 bytes),
SHA-256 `59833d875b2f3807791533f5dd077a0cb0ed08d4c1cab3136ad2ceb165871cd1`;
manifest SHA-256 `95eb1eef404859e3afae56811cccb3da27bbab6b589e276fe4e4e701dfbe9427`;
build `76f90e58436d+cuda13.0`, BUILD source `f-022-rel`, BUILD commit `76f90e58436d`.
The preparation inspection verified archive/member hashes and BUILD identity without executing the binary;
component signature verification is **not** claimed.

### Reviewed planning delta

The unmodified report refused `checklist: new call in stock setup planning; review required`.
The new call is `gpu_sel` inside `recommend_remote_expert_opt`, **not** VRAM fitting. The following
exact full-field AST hashes are admitted by the versioned tables in `scripts/upstream_watch.py`.
Earlier entries remain valid; any changed helper, role block, disk group or user-args module still refuses.
The general `pure_exec` vocabulary is unchanged (no new calls, comprehensions, probes or IO).

| Reviewed entry | SHA-256 | Decision |
|---|---|---|
| `gpu_sel` | `bbf4d50f7683de5f42d446b0d0802982f9d60c44a0a204392bfffa4d48906646` | Pure scalar/list/tuple/string normalization; load before remote-cache advice. |
| `recommend_remote_expert_opt` | `6bfb60fef7092efb584a2fc052f25f8b84d3863debe02040004d5f041ce9b672` | Exact helper only; plain layer splits still get no helper-cache flag. |
| `tier_pick` | `5d41bbc51e005e058d63fce392b97711180d75409745ac6adde4fbe93306ee91` | Informational thresholds 62/46/38 now compare RAM + VRAM minus the literal `TIER_SYSTEM_RESERVE_GB = 5.0`. No explicit model/context changes. |
| Entire `if multi` block | `360bbac44ee628d2e82295b28dc2d9fd9418fc4f37d7bcd3a995922fbf3d5e9c` | Require false role guard; evaluate only unchanged explicit-gpus body. |
| Entire top-level `_roles` block | `5ec2fe77b9c37e2282f3e716df9f4f8373fa705e25051f0f2b5b1f60b3d96f84` | Fixed `_roles=None`; refuse reachable roles, never execute role writing. |
| `margin`, `real`, `need` module | `73b0a4fd10c9cfb5ad90e732694f5bbbb275f963f9724db13211d51b6ee43312` | Fresh-root pure arithmetic only; preserve conservative `need = real + margin`, not merely the hard `real` floor. Never call adjacent `free_gb`. |
| Full `strata_control/user_args.py` module | `625e4282ba491b97cd8073a9c687acc90023ecb115233cd123eb6a36b7b717ae` | Multi-value control-vector editing changed; fresh capture/stamp did not. No module execution in drafting. |

The disk statements individually hash to `d6bdd75ef486f261f907b53f13be30355755cac37cc829de2f181c74cb1ce3a8`
(`margin`), `915ab797655a6067e23d77e6eb59e4dd5c43dec821ab9c94f2a12fefd9353544` (`real`) and
`9f92d18c4ed4c3b7bc54fe1451324b1c028babc0ea6e7a42ea3af17eb1a2c81d` (`need`).
The false ready-pack `prep_gb` guard retains
`8fefc825ebd599703c976feebf90874800c5f2902b0881a641076a3dd3a08d00`.
The default-question projection retains
`ca0dbfc6feb30ed72337ab4af81268f15c5c9dd706511846070be360209ebe52`;
`write_setup_config`, `carry_user_args` and `explicit_args` retain their `FRESH_WRITE_0_2_1` hashes.
Fresh config still has `args_written == args`, no `user_args`.

- Explicit `--gpus` returns before interactive Main/Helper/Off selection; scalar profiles use `--gpu`.
  Preserve automatic pair ordering, slots, pipeline windows and pinned tips. No `gpu_roles`, `gpu_order`,
  helper cache or role/order opt-in is admitted. Actual stage order, layer split and performance remain host gates.
- The new `strata_control/vram_fit.py` (SHA-256
  `c295ce23f70c703d1e14b931b27413a42c5538cf3cabfc2336e48734e36173ba`) tries 32K/16K/8K contexts,
  then chunk/reserve choices within each context. Its callers are SYCL setup and app/CLI launch/adoption,
  not native NVIDIA `setup.py`. Do not import those fallbacks or assume its comment protects contexts above 32K.
  The four reviewed plans retain 131072/262144 contexts and predecessor disk/RAM floors.
- Runtime requirements, build requirements, `PY_PACKAGES`, `CUDA_WHEELS`, `LLAMA_CPP_COMMIT`,
  `HF_REVISIONS` and `MIN_DRIVER` are unchanged. `MIN_ENGINE` changes 0.1.45 → **0.1.46**, a minimum,
  not the component's 0.1.47 version. `tools/mtp_fetch.py` is byte-identical (blob
  `14898aef05637148aaa1cf74f8aeee7697e6824d`); requirements blobs remain
  `b6f4d38ba2e2e477fc9307b20d7552e0f78a6e52` (runtime) and
  `ebdef8ebb3174d696f5b4e332f6681aa9ba5f887` (build). This is not a fresh HF availability observation.
- Generated keys and GET/POST/OPTIONS route census are unchanged for these plans; optional role writes are
  visible in the checklist, not admitted. Route equality is **not** security equivalence: upstream introduces
  `--no-api-key` / `api_key="none"` and removes its non-loopback no-key refusal. omp-strata still requires
  loopback and a nonblank generated key; none of those guards is changed here.
- The environment census adds 20 names, none removed: `STRATA_BUILD_COMMIT`, `STRATA_COMMIT`,
  `STRATA_ENGINE_NICE`, `STRATA_HANDOVER`, `STRATA_HANDOVER_IN_CHECKOUT`, `STRATA_METAL_GYRO_TILES`,
  `STRATA_MOVE_ALWAYS_COPY`, `STRATA_NO_HANDOVER`, `STRATA_NO_PROMPT`, `STRATA_NUMA_POOL`,
  `STRATA_NUMA_SPLIT`, `STRATA_POOL_CORES`, `STRATA_SPEC_WATCH`, `STRATA_TEST_OTHER_VOLUME`,
  `STRATA_TEST_SYSFS_ROOT`, `STRATA_TQ_ROWCH`, `STRATA_TQ_STAGE`, `STRATA_TQ_SUB8`,
  `STRATA_UMA_RESERVE_GIB`, `STRATA_VERIFY_EARLY_PLE_FLAG`. Inherited `STRATA_*` remains scrubbed;
  no environment opt-in is granted.
- Signed-feed fallback, updater/download paths and hardware probes remain outside this pure planner.
  Native installation must still stage the pinned component and reuse verified local inputs without invoking
  those paths. Preserve supplied GGUF bytes and hard-linked predecessors; no download repair is authorized.

Host-free fixtures exercise all four plans, threshold boundaries, false-role guards, fresh stamping and mutation
refusals. `report` retains its existing semantics: complete release news exits **3**, incomplete review exits 4.
This review writes no profile, release ledger, current/rollback pointer or route. Full candidate drafting and its
candidate-specific dev-env suite, native installation/feed exclusion, G00–G23 as applicable, observed split/speed,
publication and the owner's qualification decision remain separate gates.

## Strata v0.2.1 setup review (component engine)

Stable tag `v0.2.1` (published 2026-10-20), annotated tag object
`49ac15cbb32a8662602aaa7b8fc61bf6acef4cf0`, peels to commit
`90767252f420e25223c739d604145ad15911d48b`. App `0.2.1` ships the Windows engine as a separately
versioned component, engine **0.1.46**: `strata-engine-0.1.46-windows-x86_64-cuda-cuda13.tar.gz`
(579,792,118 bytes, SHA-256 `2966143ca8df7919448556e7d148e49ccecae0932bb0d5d31294ccde723f94cd`),
manifest SHA-256 `d6ea7d4ae8dce1e646a55363d14c97f9659197f63d500da90efe0d4a8fd82d3e`, build
`a7bdbfdabc9a+cuda13.0`.

- No `strata-windows-x64.zip` is published. Profiles install through native pinned-source setup with the
  verified engine component staged into `runtime\strata\engine\` before stock setup runs
  ([OPERATIONS.md](OPERATIONS.md#upgrades),
  [UPSTREAM-BETA.md](UPSTREAM-BETA.md#stable-component-releases-v021-and-later)). The manifest's ed25519
  signature is not verified, and no Control package, signed feed or installer is used. `start`'s
  authenticated identity check expects `/props` `build_info` **`Strata 0.1.46`** (the engine version,
  not `0.2.1`).
- Setup's generated config adds only `args_written`, which must equal `args` (no `user_args`).
- The reviewed requirements change moves only `cmake` and `ninja` to `requirements-build.txt`; CUDA
  wheels, Python packages, the llama.cpp pin and the driver floor are unchanged.
- Stock contract changes introduced in `v0.2.x` (gates adjusted without weakening older-engine checks):
  - **G17 (`13cbdbe`):** since `v0.2.0-beta` (engine `0.1.45.3`), stock's server shortens a `max_tokens`
    that is one token over the room left to the room left instead of answering 400; a prompt that alone
    leaves no room is still refused.
  - **G13 (`18f128a`):** now also probes `v0.2.x`'s authenticated `/v1/telemetry` GET (protected; any
    read-only telemetry key in the environment is scrubbed, and config `telemetry_read_key` is refused by
    install) and the key-only `/v1/v1/messages` and `/v1/v1/messages/count_tokens` aliases.

## Strata v0.1.44.1 setup review (host-free candidates)

The annotated tag object `9791ea335ba2001c87b5f783146d6eb08fdd9e5e` peels to commit
`296b59d2f73c8f04a805df29c2fa97655adace78`. The draft planner reviews only the existing
native Windows NVIDIA GSQ-RCO choices: Qwen IQ3_S and Coder IQ1_M. New NVFP4, Unsloth and
Qwen3.6 families are not admitted as planning choices by this review.

- Setup's `MODELS` table now references three literal NVFP4 constants. Only those named literal
  aliases are resolved; calls and unknown names still refuse. The expanded family/shard tables are
  read as stock data, not as permission to plan their new runtime paths.
- The fresh-install recommendation changes from IQ3_XXS to IQ3_S where RAM fits. A setup rerun
  keeps its installed size. The planner verifies both exact ASTs, fixes the fresh-root installed
  choice to none, and never executes the helper that reads installed config files. Explicit profile
  model/context choices remain separate from this informational recommendation.
- The new ready-pack model-argv branch is reviewed exactly; only its GSQ-RCO argv expression is
  evaluated. The rotational-disk, Unsloth small-card and image-generation branches are admitted
  only at their reviewed AST hashes and only with false guards. Changed bodies or reachable guards
  refuse. `unsloth_default_env` is an exact reviewed helper and returns no env entries for either
  GSQ-RCO family; images remain unconfigured.
- The new POST image-generation endpoint enforces the existing POST key check, then returns
  404 `images_not_set_up` without an image configuration. Image-file URLs are public token URLs
  by design, but return 404 when no image service exists. G13 classifies both as unconfigured:
  missing/wrong-key POST probes and an empty authorized POST, plus a real file-prefix endpoint.
- `MIN_ENGINE` is 0.1.44.1 and `HF_REVISIONS` adds the Qwen3.6 repository. CUDA wheels, Python
  packages, the llama.cpp pin, driver floor and requirements blob are unchanged. The extracted
  `engine_step` retains archive verification, BUILD.json minimum-version and GPU architecture/PTX
  checks. The Windows ZIP adds the K-quant prompt DLL, opened only for Unsloth K-quant models.
- The pair retains automatic layer splitting. Its next real-host window must observe the changed
  spare-VRAM near-tie placement (#1440), relative-link penalty from a 4x gap (#2007), and all-card
  startup VRAM checks (#2192). This source review adds no flags and supplies no measured result.

## Strata

1. **A queued client's disconnect poisons the next long request and crashes the engine.** Reproduced 2/2 by
   `scripts/realhost_gates.py g14q`; the control case is clean. Upstream: same root cause as
   [Strata#183](https://github.com/Niko1221/Strata/issues/183). **Fixed in v0.1.28** by #205 (`6cad1fe`; #194 was
   closed unmerged): `err` is now cleared at the start of every request, right after the line cited below, before
   each prompt segment and on entry to `Prefill::run` (source reading). The v0.1.28 release notes report a long
   prompt cancelled and then sent again, followed by a short one, with the engine staying up. **Confirmed on the
   real host with v0.1.30** (second candidate, G14 and `g14q` pass): both queued-disconnect scenarios and the control
   served two consecutive 8,123-token prompts with the same engine process.
   - Steps: request A is generating and request B is queued behind it; B's client disconnects. Then the next
     request whose prompt needs more than one prefill window (about 8K tokens here) fails with HTTP 400
     `cancelled`, the engine exits with code 1, and the request after that gets HTTP 503 before the lazy restart.
   - Short prompts in between are served normally.
   - Cause: B reaches the engine after A and is stopped while it reads its prompt, which leaves the engine's `err`
     string set to `cancelled`. The next request clears `stop_req` but not `err`
     (`src/program/generate.cpp:3561`), so a prompt read in batched chunks fails on its first chunk and the serve
     loop exits with code 1 (`:3996-4000`). The windowed path used for short prompts does not check `err` first.
   - Workaround here: `omp_strata.py restart`.
2. **Tool calls cut off mid-arguments are finalized as complete.** When the model ends its turn inside a tool
   call, `OutputParser.finish()` closes the partial JSON and the response reports `finish_reason: tool_calls`.
   Clients then execute truncated arguments; see OMP item 1. Reproducer:
   `tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body_is_not_reported_as_complete`
   (the stock frontend with its MockEngine). A cut on `finish_reason: length` is correctly reported. Upstream: the
   second trigger of [Strata#210](https://github.com/Niko1221/Strata/issues/210); our #211 was closed as its
   duplicate, then reopened with a repro at v0.1.28, which fixed only the first trigger (`</parameter>` or
   `</tool_call>` inside an argument). **Fixed in v0.1.31** by
   [Strata#231](https://github.com/Niko1221/Strata/pull/231) (`925c354`, with `9a1fc19`): an announced call the
   output ends inside stays unfinished, its JSON is not closed, and the answer ends with `stop` (or `length`)
   instead of `tool_calls`; a non-streamed answer leaves such a call out. On the mock tier with v0.1.31 the
   reproducer's stream now ends with `stop` and unterminated arguments. With stock OMP 18.4.8 the composed G04 case
   still failed, because that client turned the stream into a tool turn and ran the truncated write (OMP item 1).
   With OMP 18.4.10 (fourth tuple, Strata v0.1.34) the composed case passes: OMP answers the call with the parse
   error, writes nothing, and the model continues (stop reasons `toolUse`, `stop`; exit 0).
3. **`/status` is unauthenticated and includes a tail of the generated text.** With an API key set, any local
   process can still read the last 600 characters of the current answer, and of the most recent one while the
   server is idle, because the tail is not cleared when a request ends. Upstream:
   [Strata#212](https://github.com/Niko1221/Strata/issues/212). **Fixed in v0.1.28** (`4d25c61`): with a key set,
   `/status` answers 401 without it, and the tail is dropped when the request ends (mock tier; confirmed on the real
   host with v0.1.30, G13).
4. **An empty API key disables authentication, and keys are compared with `==`.** The "no API key" warning is
   printed only for non-loopback hosts. The integration refuses to start without a key of at least 32
   characters. Upstream: [Strata#213](https://github.com/Niko1221/Strata/issues/213). **Fixed in v0.1.28**
   (`4d25c61`): keys are compared with `hmac.compare_digest`, and an explicitly empty key (`--api-key ""` or an
   empty `STRATA_API_KEY`) stops the server; on the mock tier an empty `STRATA_API_KEY` exited with code 2. An
   absent key still means no authentication, so the integration still refuses to start without a key of at least
   32 characters.
5. Stock `setup.py` resolves the engine from `releases/latest`, the model and MTP tensors from `main`, and
   unpinned PyPI packages, and it writes to `%APPDATA%\Strata`. The integration feeds it pinned, verified local
   inputs instead. Upstream: [Strata#214](https://github.com/Niko1221/Strata/issues/214). **The fetches are fixed
   in v0.1.31** by the maintainer's `ba5c387`: a checkout installs the engine release of its own version
   (`releases/latest` when that release cannot be reached), every Hugging Face file comes from a pinned commit (the
   same Coder and MTP revisions this integration pins), and the Python packages come from a pinned
   `requirements.txt`. Our [Strata#324](https://github.com/Niko1221/Strata/pull/324) proposed the same three fixes
   six hours after `ba5c387` was committed; v0.1.31 superseded them. #324's fourth change went into **v0.1.32** as
   the maintainer's `09c05e7` ("From PR #324"): an engine archive that setup refuses (too old, or without code for
   the GPU) is deleted with its `.done` mark. That fixes our follow-up
   [Strata#397](https://github.com/Niko1221/Strata/issues/397): v0.1.31 kept the refused archive, so every later run
   reused it and "run this again in a few minutes" never updated the engine. `09c05e7` reached `main` only with
   v0.1.32, after #397 and our fix [Strata#399](https://github.com/Niko1221/Strata/pull/399) were filed; the
   maintainer closed #397 as fixed and #399 as covered. #399's two tests fail on v0.1.31 and pass on v0.1.32 and
   v0.1.33. Not taken from #399: an archive that failed to unpack kept its `.done` mark in v0.1.33 (v0.1.34 by
   source reading), so later runs failed on the same file even after a good archive was published. **Fixed in
   v0.1.40** by the maintainer's `645cbb6`: `BadZipFile` drops the archive and its `.done` mark before re-raising.
   On 2026-10-06 the maintainer closed our [Strata#424](https://github.com/Niko1221/Strata/pull/424) as fixed.
   Per-user settings still go to `%APPDATA%\Strata`. The integration keeps passing local verified inputs and
   redirecting APPDATA; its Python lock for v0.1.31 is resolved from that `requirements.txt` (unchanged in v0.1.34).
6. **Every unexpected engine exit is logged as a probable out-of-memory event**, including the stale-cancel crash
   in item 1 and deliberate kills. None of the 5 exits observed here was memory-related. Upstream:
   [Strata#215](https://github.com/Niko1221/Strata/issues/215). **Fixed in v0.1.28** (`4d25c61`): when the engine
   exits by itself, the server quotes its exit code and last log line; the out-of-memory
   hint remains for other exits (source reading; on the real host with v0.1.30 the cut turn after a mid-generation
   engine kill read "the engine stopped unexpectedly (exit code 1); the next request restarts it", G15).

7. **Strata v0.1.44.1's and v0.2.1's automatic layer splits on the RTX 4090 + RTX 3090 pair.** Upstream:
   [Strata#2463](https://github.com/Niko1221/Strata/issues/2463), **opened 2026-10-14, closed on 2026-10-19 as not
   planned** (no change to link pricing). In the v0.1.44.1 three-arm back-to-back comparison (same model and setup),
   v0.1.43.1 splits layers 0-31 / 32-47 across the RTX 4090 / RTX 3090; v0.1.44.1's default link-miss rule moves
   them to 0-44 / 45-47 (K=45). Decode falls from 184-206 to 148-154 tok/s, prompt reading to 0.52-0.77x, and
   100K-token TTFT rises from 28.6 s to 55.0 s. The diagnostic v0.1.44.1 arm with `STRATA_SPLIT_LINK_ABS=1` restores
   the split at layer 32: decode 164-199 tok/s, prompt reading 1,605-3,604 tok/s and 100K-token TTFT 28.6 s. That
   opt-in knob exists upstream, but this integration refuses `env` on multi-GPU profiles and does not set engine
   environment overrides there; on 2026-10-14 the owner held the pair on v0.1.43.1 and left the v0.1.44.1 pair
   release draft, not qualified. In **v0.2.1** (2026-10-21), the automatic split moves to layers 0-24 on the RTX
   4090 and 25-47 on the RTX 3090 (K=25). Measured back to back against v0.1.43.1 on the same host (2026-10-21
   02:03-02:06Z, one 512-token sample per depth, server-reported rates; MTP acceptance 0.8 in both), decode is
   141-158 against 170-201 tok/s, prompt reading at 64K-100K tokens 2,838-2,853 against 3,508-3,594 tok/s, and
   100K-token TTFT 36.0 s against 28.6 s
   ([per-depth table](MEASUREMENTS.md#all-three-hosts-every-gate-2026-10-21-stock-strata-v021-stock-omp-18101)).
   On 2026-10-21 the owner qualified v0.2.1 with OMP 18.10.1 as
   current on the pair anyway; v0.1.43.1 with OMP 18.10.1 stays its qualified rollback, and the v0.1.44.1 pair
   release remains draft, not qualified.
8. **Engine 0.1.52's automatic PLE RAM residency on the 128 GB RTX 4090 + RTX 3090 pair disables the automatic conversation cache and leaves 1.03 GiB Windows commit headroom.**
   Upstream: [Strata#4518](https://github.com/Niko1221/Strata/issues/4518), **opened 2026-10-28**. On the
   128 GB-RAM pair (`rtx3090-win-a`, Qwen3.8-Flash-Next IQ3_S at 262,144 tokens, stock roles
   `--gpu-roles 0=main,1=helper`, pipeline windows 2), engine `0.1.52`'s residency policy chooses `--ple-io ram`,
   locks the 26.8 GiB per-layer embedding (PLE) table in RAM at start (~31.4-37.5 s), leaves the automatic
   conversation cache off ("not enough free RAM to park conversations"; `/metrics` `conversation_cache`:
   `enabled: false`, `budget_mib: 0`, versus 8,192 MiB on `v0.2.3`), and leaves only **1.03 GiB** (`1,109,463,040 B`)
   Windows commit available in G10 against **27.3 GiB** (`29,320,192,000 B`) on `v0.2.3` roles at the same
   **135.7 GiB** (`145,695,096,832 B`) commit limit (0.632-1.331 GiB in a later pair bench). In back-to-back
   single-sample `scripts/perf_probe.py` runs, 100K-token TTFT was 30.40 s with PLE in RAM versus 31.15 s with a
   throwaway `STRATA_PLE_AUTO_RAM=0` arm (`v0.2.3`: 31.23 s). Because launch strips inherited `STRATA_*` variables and
   multi-GPU profiles refuse `env` overrides, `omp-strata` adds profile field `strata.ple_io: "direct"` pinning stock
   `--ple-io direct` ([OPERATIONS.md](OPERATIONS.md#stock-ple-direct-reads)). The qualified PLE-direct profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.7-omp18.13.2`) keeps the PLE
   table on direct SSD reads (`PLE direct read probe: N rows/s (fine)` on all 16 starts, no residency-policy line),
   sizes the automatic conversation cache at 8,192 MiB on every start (20 parks in G19), restores **27.3 GiB**
   (`29,328,113,664 B`) G10 commit headroom, and scores 17/18 on G24 (versus 13/18 on the held PLE-in-RAM roles
   draft and 14/18 on `v0.2.3` roles). **Fixed upstream in `v0.2.8` (engine `0.1.54`, 2026-10-29) and measured on
   Windows on 2026-10-30:** on the measurement-only `v0.2.8` stock-residency draft
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-parking-strata0.2.8-omp18.14.0`), the policy locked the
   26.8 GiB table (33.9-34.0 s), then gave the lock back on both starts and sized the automatic conversation cache at
   **4,864 MiB** (106-112 s to ready), against **8,192 MiB** and 61-63 s to ready with `--ple-io direct` at matching
   100K-token TTFT (31.2 s with PLE direct versus 30.9 s with stock residency;
   [MEASUREMENTS.md](MEASUREMENTS.md#rtx-4090--rtx-3090-stage-order-and-strata4518-on-engine-0154)). The qualified
   `v0.2.9` and `v0.2.8` pair profiles — the current `v0.2.9` split-24 trim + PLE-direct + `env86g` profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-env86g-parking-strata0.2.9-omp18.15.0`,
   8,192 MiB cache, 27.77 GiB G10 commit headroom, G24 15/18), its `v0.2.9` split-24 trim + PLE-direct base rollback
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.9-omp18.15.0`,
   8,192 MiB cache, 27.74 GiB G10 commit headroom, G24 15/18), the earlier `v0.2.8` split-24 trim profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`,
   8,192 MiB cache, 27.8 GiB G10 commit headroom, G24 15/18) and the initial `v0.2.8` `roles-pledirect` profile
   (`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`, 8,192 MiB cache,
   27.9 GiB G10 commit headroom, G24 15/18) — therefore keep `--ple-io direct`.

## OMP

Re-verified against OMP `main` (`2b023d1`, 2026-09-30) and, where a reproducer exists, against the stock 18.4.6
binary pinned by the second candidate, the stock 18.4.8 binary of the third tuple (2026-10-01; 18.4.7 and 18.4.8
changed only the macOS natives and the TUI) and the stock 18.4.10 binary of the fourth tuple (2026-10-02); each item
notes its status. Our pull requests are linked per item: #13866 and #13867 were merged on 2026-09-30 and released in
18.4.5; #13864 was merged on 2026-10-01 and released in 18.4.9; #13868 was merged on 2026-10-01 and released in
18.4.10 (2026-10-02). #14734, #14735 and #14737 were merged on 2026-10-07, after 18.8.0 was cut, so no release
contains them yet.

1. **Executes tool calls whose arguments are syntactically truncated.** At finalization OMP parses the argument
   string with its lenient streaming parser, which closes unterminated JSON, and runs the call: a partial file
   write happens and the run exits 0. Reproducer:
   `tests/mock/test_g04_faults.py::test_truncated_arguments_must_not_execute_side_effect`. A `length` cut is handled
   correctly (`::test_finalized_partial_json_with_length`). `::test_finalized_partial_json_with_stop` is the composed
   case before Strata item 2's fix: the server closes the JSON itself, so OMP receives valid JSON and cannot tell.
   Since Strata v0.1.31 the server leaves the JSON open and ends with `stop`, and OMP 18.4.8 still runs the call
   (`tests/mock/test_strata_frontend_mock.py::test_model_stop_inside_qwen_tool_body`: the truncated write happens,
   exit 0, stop reasons `toolUse`, `stop`). Present in the 18.4.0-18.4.9 binaries. **Fixed in 18.4.10** by
   can1357/oh-my-pi#13868: with the 18.4.10 binary both reproducers pass (no write; the call gets the parse error
   and the run continues), so G04 no longer fails on the fourth tuple. `::test_finalized_partial_json_with_stop`
   stays a client limit no OMP release can fix: valid JSON is valid, so it is skipped when the pinned Strata leaves
   cut calls unterminated (v0.1.31+).
2. **Contacts the internet at startup.** The background model-registry refresh (`refreshInBackground`) fetches the
   public model catalog from `catalog.stencil.so` when its cache is cold or stale, and implicit local providers probe
   127.0.0.1:11434, :8080 and :1234; no startup setting disables either. Observed with ETW in G13 (18.4.0); with
   18.4.6 and the guard, the loopback probes are still visible and no non-loopback endpoint was reached. Workaround
   here: proxy variables pointing at a closed loopback port. Upstream, can1357/oh-my-pi#10934 asks for a catalog
   opt-out.
3. **Sends `Bearer STRATA_API_KEY` literally when a models.yml `apiKey` names an unset variable**, instead of
   failing. This is OMP's documented contract (an `apiKey` is tried as an environment variable name, else sent as the
   literal token), which is why `launch-omp` refuses a missing key. Reproducer:
   `tests/mock/test_g02_isolation.py::test_raw_stock_missing_key_dispatches_literal_and_fails_401`.
   can1357/oh-my-pi#13866 added a documentation warning (merged); the behaviour is unchanged in 18.4.6.
4. **Retries on `openai-completions` cannot be turned off.** An HTTP 500 produced 12 identical requests (6
   transport attempts × 2 provider attempts) with `retry.enabled: false`. The transport's `DEFAULT_MAX_ATTEMPTS`
   (`packages/ai/src/utils/openai-http.ts`) reads no retry setting, so `retry.maxRetries` cannot reach it either.
   Reproducer: `test_g04_faults.py::test_http_500`. Still present on `main` and in 18.4.6 (12 requests again);
   related: can1357/oh-my-pi#13255.
5. **The fitted `max_tokens` can overshoot a strict server by a few tokens.** The fit is
   `agent/src/output-budget.ts` `fitOutputTokensToContextWindow`. Near the window, prompt 105,522 + fitted cap
   25,563 exceeded Strata's 131,064 (131,072 − 8) by 21 tokens, and the closing turn failed with HTTP 400 (G17
   attempt 3). Fixed upstream by can1357/oh-my-pi#13499 (a 64-token headway, in 18.4.4). The integration keeps
   declaring the window 1,024 tokens below the engine's for both candidates; with 18.4.6 the largest near-limit
   prompt + cap seen was 129,997 (G17), inside the declared window without relying on the headway.
6. **Strata's overflow message is not classified as a context overflow.** `ai/src/error/flags.ts` has no pattern
   for "prompt (N tokens) + max tokens (M) exceeds the context", so no compaction recovery is attempted. This is
   minor, because item 5's fit usually prevents the overflow. **Fixed in 18.4.9** by can1357/oh-my-pi#13864
   (`edb740c`; source reading); not exercised here, because every profile pins 18.4.8 or older.
7. **Unknown `models.yml` compat keys are accepted silently.** A misspelled key is kept without an error. The
   integration guards its emitted keys with a test. **Fixed on `main`** by can1357/oh-my-pi#14737 (`3205ec9`,
   merged 2026-10-07): an unknown key in a provider, model or `modelOverrides` `compat` block now produces a
   non-fatal warning. No release contains it yet.
8. `--thinking off` still sends `reasoning_effort: low` with this dialect; OMP documents this as requesting the
   lowest effort on generic effort endpoints; can1357/oh-my-pi#13867 made that clearer (merged). Unchanged in 18.4.6
   (off/low/medium/high/xhigh are sent as low/low/medium/high/high). `--no-tools` disables the built-in tools, so it
   is not a way to limit egress.
9. **Services an agent starts stop 3 s after `omp --print` exits.** The service broker stops non-detached services
   once its idle grace (`OMP_DAEMON_IDLE_GRACE_MS`, default 3,000 ms) runs out after the last client disconnects, so a
   benchmark that checks a server after the agent exits finds nothing (Terminal-Bench `hf-model-inference` and
   `kv-store-grpc` on 18.5.0). Upstream's metaharness set nothing to prevent it. Scripted check on 18.5.0 and 18.7.0:
   a bash-tool service is gone 8 s after exit, and still listening with a 120,000 ms grace. **Fixed in upstream's
   metaharness** by can1357/oh-my-pi#14734 (`dc97a4a`, merged 2026-10-07): `omp_local.py` now runs omp with
   `OMP_DAEMON_IDLE_GRACE_MS` set to 24 h, so the services stay up until the container is torn down. The broker's
   3 s default is unchanged.
10. **18.5.0 drops the retry for a reasoning-only stop once a run has restarted.** OMP retries a stop whose only
    content is reasoning, but in 18.5.0 such a stop after an earlier continuation or retry in the same run ends it
    with `agent_end.isTerminal: false` and exit 0. Seen in 3 Terminal-Bench runs on Strata v0.1.39; a scripted server
    reproduces it. **Fixed in 18.5.1.**
11. **A compiled binary extracts its ~175 MB native addon into each `HOME`.** The only redirect, `XDG_DATA_HOME`, also
    moves sessions and plugins, so isolated per-attempt homes kept one copy each; the integration deletes it after
    each attempt (`omp_strata.ompcfg.drop_native_cache`). **Fixed on `main`** by can1357/oh-my-pi#14735 (`8f905a5`,
    merged 2026-10-07): `PI_NATIVES_DIR` moves only the addon. No release contains it yet, so the integration
    keeps deleting the copy.
12. **Speculative compaction competes with the agent's own turn on a one-request provider.** In the band below its
    compaction threshold (12.5 % of the threshold, 8,192 to 32,000 tokens), OMP sends the session's model a
    background summary request. With `providers.maxInFlightRequests: 1`, which this integration sets because Strata
    serves one sequence, the agent's next turn waits behind that request, and the summary replaces the engine's live
    prefix. On the RTX PRO 6000 (G17, 18.8.0) the turn waited 17 s and then re-read all 105,748 of its tokens (Strata
    reported none reused; 15.4 s); the summary was never applied. Reproducer: `tests/mock/test_speculative_compaction.py`.
    The extra request went out with 18.4.10, 18.5.0 and 18.8.0; with 18.7.0 the next turn won the race. A scripted
    check without that race (2026-10-07, release binaries) shows it on 18.8.0 and 18.8.2 alike: the summary takes the
    only slot at the turn boundary and the next turn waits for all of it. Workaround here: `compaction.asyncEnabled:
    false` (OMP still compacts at the threshold). Not reported upstream yet; a fix could skip speculation on a provider
    limited to one in-flight request.

Re-checked on `main` `7ac4b18` (2026-10-07): items 2, 4 and 7 are still present; can1357/oh-my-pi#10934 and #13255
remain open. Item 7 was fixed on `main` later that day by #14737.

## Fifth tuple: Strata v0.1.36 / OMP 18.4.12 (host-free drafts, 2026-10-02)

<details>
<summary>2026-10-02 fifth-tuple release notes, stock planning floors, shard pins and host-free test results</summary>

On 2026-10-02 the release APIs resolved Strata `v0.1.36` to
`36fa455e579b23a9c909c2c6fe1bddd9e51cb8ca` and OMP `v18.4.12` to
`7318a70cf4ed04133366884d2723f72d9d490a15`. `scripts/upstream_watch.py report` found the four
newer releases below and resolved all 21 tracked issue/PR states. The five new profile ledgers remain
**draft, 24 gates `not_run`, no receipts**: no GPU host was used and the RAM upgrades are not assumed installed.

- [Strata v0.1.35 release notes](https://github.com/Niko1221/Strata/releases/tag/v0.1.35): Windows
  low-RAM resident mode frees the file cache before sizing residency and keeps the hottest experts that fit
  rather than falling back wholesale to SSD. Windows AMD loads its bundled HIP runtime; multi-GPU setup
  warns about a small second card limiting prompt chunks. Config writes are atomic, malformed `messages`
  become a 400, and `/metrics` gains draft counts. The Coder's weaker non-code/non-English behavior is
  explicitly documented upstream, supporting an unpruned Q2_0 draft rather than a quality claim here.
- [Strata v0.1.36 release notes](https://github.com/Niko1221/Strata/releases/tag/v0.1.36): Q2_0 uses
  fused int8 tensor-core prompt kernels on RTX 30 and newer by default. Upstream's speed/quality numbers
  are from its hardware, **not measurements of these profiles**; Q2_0 answers are intentionally not
  byte-identical to v0.1.35. RTX 50 long-context decode gains cluster kernels; IQ fused prompt kernels
  are opt-in. Cancellation logs and metrics now report the amount actually read; draft-head errors name
  smaller vocabulary alternatives. `expert_profile_save` / `--expert-profile-save` is new, **opt-in and
  off here**: learned expert-cache persistence is not part of this integration. The shipped expert
  profile and default CJK draft vocabulary stay pinned by the Strata source commit.
- **Never run `UPDATE.bat` or `update.sh`**, just as `START-HERE.bat` and `setup.sh` remain prohibited.
  Their convenient upstream update path changes source, Python packages, engine, model settings and
  draft vocabulary in place. This repository instead creates a new pinned profile, root and ledger.
- Source comparison v0.1.34 → v0.1.36 found five new quoted environment names: `STRATA_ARGMAX_MULTI`,
  `STRATA_PF_FUSED`, `STRATA_PF_FUSED_NATIVE`, `STRATA_PF_FUSED_TILE`, `STRATA_QSA_CLUSTER`.
  `server_env` strips **all inherited `STRATA_*`** and explicitly supplies the key; none of these
  knobs passes through. Changing kernel defaults, the draft vocabulary, expert profile or any other
  tuning option requires a reviewed new profile, never an ambient environment override.
- [OMP 18.4.11 release notes](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.11): malformed
  JSON for lenient tools such as `yield` is reported to the model instead of running with empty
  arguments; unrelated projects no longer inherit the default home's project configuration. Other
  relevant changes include Windows paste, FIFO/device read refusal and subagent MCP deadlines.
- [OMP 18.4.12 release notes](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.12): reduced
  streaming overhead, Windows session-path import and temp-cleanup fixes, and eval wait/dead broker
  fixes. Its new auth-gateway stdio mode is **not used here**: stock OMP still calls stock Strata
  directly over Chat Completions, with no gateway or fallback provider.

### Pins and stock planning evidence

The source checklist changed only `MIN_ENGINE` among the six audited setup constants: `MIN_DRIVER=580`,
`CUDA_WHEELS`, `PY_PACKAGES`, `LLAMA_CPP_COMMIT` and `HF_REVISIONS` are unchanged. Both tags'
`requirements.txt` blob is `3db8418ab428ea10f4b607b693cf6ad030fd0509`, so the existing
`locks/strata-python-cp313-win_amd64-strata0.1.31.txt` is reused with its original hash, not rewritten.
The same **11** top-level config keys are generated and the server route set is unchanged, with no
unclassified routes. Stock setup's pure choices/config arithmetic were evaluated at the requested
contexts: no low-RAM, context reduction or RoPE extension was needed.

| Draft variant | Context / OMP declared window | Total RAM floor / available at start (GiB) | Free disk floor (GiB) | Stock RAM thresholds |
|---|---|---|---|---|
| Coder IQ1_M, RTX 5090 | 131,072 / 130,048 | 45 / 34 | 90 | Low-RAM below 33.4; KV streaming from 34.7994 |
| Coder IQ1_M, RTX 3090 / 4090 | 131,072 / 130,048 | 60 / 34 | 90 | Low-RAM below 33.4; KV streaming from 34.7994 |
| Coder IQ1_M, RTX 4090 | 262,144 / 261,120 | 60 / 36 | 90 | KV streaming from 36.5987 |
| Unpruned Q2_0, RTX 4090 | 131,072 / 130,048 | 60 / 50 | 107 | Arena 34.0; low-RAM below 44.0; KV streaming from 50.7994 |

All five use stock `--kv-resident 32768`. Every floor is the **maximum of the predecessor's floor
and the setup-derived estimate**, never the purchased 128/192 GB. Predecessor floors preserve
operational headroom for observed integration-root sizes and engine peaks that setup's estimates
do not capture; a tuple bump may raise these constraints, never lower them. The draft JSON reports
both inputs and the selected floor. Setup estimates round up its low-RAM/streaming thresholds and
`ram_gb + KV`; the disk estimate uses exact shards (at least setup's estimate) plus setup's 8 GB
preparation allowance, converted to GiB.
Q2_0 conservatively includes its 40 GB AVX-512 conversion branch so the floor remains safe on either
CPU. These are preflight floors, not real-host capacity/performance evidence. `omp.context_window`
equals the configured engine context; `ompcfg.CONTEXT_SAFETY_TOKENS=1024` is subtracted when rendering
the route, not twice in the profile.

The release API pins `strata-windows-x64.zip` to **124,993,467 bytes**, SHA-256
`dfe40817661a4286f2a94b86452aef5eae54d8c0f23429868449b06086f4c266`; the OMP assets are
`omp-windows-x64.exe`, `omp-darwin-arm64` and `omp-linux-x64` (their API sizes/digests are in every
profile). No engine archive or model was downloaded. Q2_0 uses stock setup's
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` revision
`ed59f92082b1e93c0e96d60a8b11aab089b52f09`:

| Shard under `Q2_0/` | Bytes | Hugging Face LFS SHA-256 |
|---|---:|---|
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` | 37,623,740,192 | `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` |
| `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` | 28,800,138,432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |

Coder and Q2_0 both use `Qwen/Qwen3.8-Flash-Next` MTP revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`, resolved live, with the unchanged pinned tensor-manifest
digest `ced6fb728a94374d1fcbd1938b6543cf8ecb0a936d923cd3eca4923282a814b6`. No separate unpinned
draft model is introduced; stock setup builds the same Q2_0 MTP layer and copies the source-pinned
default draft vocabulary.

### Host-free run (2026-10-02)

The fifth-tuple dev-env provisioned the real Darwin ARM64 OMP binary and pinned Strata source.
`tests.unit.test_upstream_watch`: **13 tests, OK** (fixture transports, no network; includes the
nondecreasing host-floor regression); under the new
dev-env, `tests.unit.test_strata_surface tests.unit.test_profile`: **10 tests, OK**. All five profiles
validated, their release manifests verified, and `--require-ready` refused all five as intended.

A first mock-tier run under that dev-env, taken while the client-route tests were still being written, failed
three of them (a closed tunnel's TIME_WAIT mistaken for an occupied listener); the G04 truncated-call and
composed-cutoff cases passed. After those fixes the whole host-free suite ran once in each CI lane on
2026-10-02 (macOS arm64, sequentially):

| OMP binary / Strata source | Result |
|---|---|
| 18.4.6 / v0.1.30 | 188 tests OK (4 expected failures: the G04 defects of those versions) |
| 18.4.8 / v0.1.31 | 188 tests OK (1 skipped, 2 expected failures) |
| 18.4.10 / v0.1.34 | 188 tests OK (1 skipped) |
| 18.4.12 / v0.1.36 | 188 tests OK (1 skipped) |

The existing version thresholds in `tests/candidate.py` already select the right G04 expectations for
18.4.12/v0.1.36. No GPU gate ran.

</details>
