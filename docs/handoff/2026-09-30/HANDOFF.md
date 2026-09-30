# OMP Strata — implementing-agent handoff

**Target repository:** `https://github.com/alphastorm/omp-strata`  
**Prepared:** September 30, 2026  
**Document status:** execution specification, not an implemented or qualified release  
**Owner:** repository owner (name redacted for publication)  
**Primary objective:** ship the smallest reproducible, private, stock-OMP + stock-Strata integration that can be evaluated on real coding tasks without changing or destabilizing OMP NInfer.

## 0. Start here: the decision and the job

Implement a **thin sibling integration**, not an engine swap inside `omp-ninfer`. Keep stock Oh My Pi as the agent and stock Strata as the inference server. Start with one independently named provider, one model artifact/quantization, one GPU-host/runtime profile, and one client route. Prove a typed tool round trip early, then earn each additional capability with evidence.

The initial product contract is:

> A pinned, tested Strata setup for local OMP coding sessions, with live prefix reuse when the engine reports it, and recovery from OMP's persisted transcript. Restarting the Strata engine may require replay/prefill. Durable engine-state recovery is not part of v0.1.

The business/engineering question is **whether this engine/model combination improves useful local coding outcomes**. It is not whether its README has a larger parameter count or a faster token-rate headline. A correctly working optional backend is a valid result even when it does not outperform NInfer. A comparative claim requires an actual controlled comparison.

This assignment is to implement and test, not to produce another plan and stop. Work through the milestones below as far as the available, authorized environment permits. Hardware or credentials unavailable? Complete source/config audit, implementation, mocks, host-free CI, and runbooks; leave hardware gates explicitly `blocked` or `not_run`. Never fabricate a GPU receipt, substitute a cloud model, or call a mock pass a qualified release.

### Non-negotiable boundaries

- Do not edit, replace, rename, upgrade, uninstall, or repurpose the user's working `omp-ninfer`, `alphastorm/ninfer`, default OMP installation, global OMP settings, or checkpoint stores.
- Do not clone the entire NInfer integration tree and rename it. Reuse selected patterns and test scenarios with provenance, not its historical manifests, measurements, support claims, or runtime assumptions.
- Do not create an OMP fork, an additional production request proxy, a second agent/transcript implementation, a generic backend framework, or a durable-state subsystem in the first milestone.
- Do not add `/v1/responses` merely to resemble NInfer. Start with OMP's standard **`openai-completions`** API selection, which targets Chat Completions. Anthropic Messages is an explicit alternative only after a documented compatibility reason; it is not an automatic fallback.
- No silent cloud fallback, model substitution, GPU substitution, quantization downgrade, context truncation, or unsupported capability advertisement.
- Keep production credentials, private host inventory, private code, real user transcripts, raw local paths, and raw debug logs out of this public repository and CI artifacts.
- No model-state/checkpoint import from NInfer. A move between models starts a fresh provider state from a deliberately selected transcript; it is not binary state migration.
- Do not buy hardware, provision paid compute, change drivers/BIOS, open firewall ports, or interrupt an occupied GPU as part of bootstrap.

## 1. Repository and source observations

These are **observations made during handoff preparation**, not assertions that a release has been executed. Immutable links in section 15 identify the sources. Recheck the repository before changing it; preserve any work added after this packet.

| Component | Observed baseline | How to use it |
|---|---|---|
| New integration | `alphastorm/omp-strata`; public, empty at inspection; repository metadata reports default branch `master` | Do not assume `main` exists. Inspect the actual checkout/default branch. Do not change repository settings or force-push. |
| OMP client candidate | Upstream `can1357/oh-my-pi`, v18.4.0, source `401778d0cd30020ce0f9198f751b13c68850562f` | Starting candidate because the existing NInfer release already names it. Resolve and verify the actual client artifact before use. This does not qualify it for Strata. |
| Strata source candidate | `Niko1221/Strata`, observed `main` at `a79080535d1b2a71a3419a0d97d8e7dca194b0f1` | Audit baseline, not a verified binary pin. Prefer a traceable published release or a reproducible build matching the selected source. |
| NInfer reference | `alphastorm/omp-ninfer` v0.8.7; annotated tag object `1d131bbbe6181fc9d4c6a095dbb44507f80b1578`, peeled commit `dd10bf33ddbbb4925bf6dd633980001354b3e1cf` | Read-only reference and possible control configuration. Its receipts are not Strata evidence. |

The source review established the following relevant boundaries:

**API and process topology.** Strata's Python server exposes Chat Completions and Anthropic Messages and drives a resident C++ engine via stdin/stdout. It serves one sequence at a time. The reviewed server does not expose a Responses endpoint. Keep the production topology direct: `OMP → authenticated loopback/tunnel → stock Strata server → stock engine`. [S03, S04]

**Caching versus persistence.** The engine maintains live tokens and a chain of conversation checkpoints. `ConvCheckpoint` stores portions of running state; restoration assumes the corresponding positional cells remain valid in the live session. Switching continuation can invalidate later checkpoints. These primitives are useful live-cache machinery, not a complete on-disk restart snapshot or an independently retained branch tree. Do not equate an internal function named `checkpoint_save` with durable user-session recovery. [S05, S06]

**Current OMP integration.** The NInfer v0.8.7 manifest uses unmodified upstream OMP 18.4.0. Its current example selects `openai-responses`. Historical architecture prose about a fork client or `omp appliance` commands is not the current client's authority. Use the exact manifest, current guide, and the selected client's real CLI/schema. [S07, S08, S09]

**Configuration isolation.** OMP named profiles relocate OMP-native configuration and state, but external-tool and project configuration can still be discovered. `PI_CODING_AGENT_DIR` alone is not a complete isolation mechanism. Test the actual discovery boundary; do not infer that an empty profile means zero inherited hooks, tools, credentials, or routing. [S10]

**Mutable server settings.** The reviewed Strata server accepts `STRATA_API_KEY`, defaults to loopback when not overridden, and loads a neighboring shared-settings JSON file that can affect generation. Freeze or explicitly initialize that file and record effective settings. A version pin alone does not freeze UI-modified sampling behavior. [S04]

**Model and hardware.** Strata's supported path here is Flash-Next and its variants, not the NInfer 27B artifact. Its full-model variants have substantial RAM and storage requirements; the Coder variant and low-RAM mode have different operating tradeoffs. Never treat matching GPU names as sufficient memory qualification. [S01, S02, S07]

### Source-refresh rule

Before implementation, compare these baselines with the accessible checkout and relevant upstream changes. Keep the proposed baseline unless a concrete blocker or important fix justifies changing it. Record any selected replacement, its exact commit/artifact identities, reason, and affected tests in `docs/BASELINE.md`. Do not chase every new upstream commit during qualification. Once testing begins, freeze the tuple; a changed component/configuration invalidates affected receipts.

## 2. Ownership and minimal architecture

`omp-strata` owns profile selection, immutable component references, installation/launch glue, an OMP configuration fragment, diagnostics, acceptance tests, measurements, and the supported product statement. OMP owns transcript/session persistence, tool execution, agent UX, compaction, and model selection. Strata owns inference, chat templating/tokenization, the serving API, live cache, and engine correctness.

A runtime compatibility problem should first become a small reproducible upstream issue/test. Prefer supported settings, then a suitable stock release. A source fix may be developed as a narrowly scoped upstream patch when needed, but a downstream-patched build is **not** a stock-Strata qualification. Record it as a separate experimental candidate; do not quietly expand the scope or fork both runtimes.

Use simple Python orchestration and tests unless the checkout already establishes another suitable convention. Thin PowerShell/shell launchers are acceptable where native process behavior requires them. No daemon of your own, dependency-injection platform, plugin registry, distributed scheduler, telemetry service, or web UI.

A reasonable final layout is below. It is a destination, not a requirement to build every file before the first useful turn.

```text
README.md
AGENTS.md
pyproject.toml
<dependency lock appropriate to the chosen Python tooling>
.gitignore
profiles/<one-candidate-profile>.json
examples/omp/models.fragment.yml
examples/omp/config.fragment.yml
scripts/omp_strata.py          # doctor/install/start/status/stop/launch-omp
scripts/qualify.py             # host-free and real-host modes
scripts/verify_release.py      # evidence/pin/readiness checks
schemas/manifest.schema.json
schemas/receipt.schema.json
tests/unit/
tests/mock/
tests/fixtures/
docs/BASELINE.md
docs/QUICKSTART.md
docs/ARCHITECTURE.md
docs/SECURITY.md
docs/OPERATIONS.md
docs/MEASUREMENTS.md
docs/DECISION.md
releases/<candidate-id>/manifest.json
releases/<candidate-id>/qualification.json
.github/workflows/ci.yml
```

Do not generate a directory of empty documentation. Implement one thin working path, keep documents compact, and consolidate files that add no distinct value. The handoff packet's draft manifests and acceptance files are planning inputs; do not mistake them for installed runtime configuration or production schemas.

## 3. Milestone M0 — inspect, choose, freeze

### 3.1 Repository audit and safe work area

Inspect repository status, remotes, branch, instructions, existing issues/PRs and files. Preserve uncommitted changes and any newer implementation. For an empty repository, initialize a minimal work branch and local commits without assuming an existing base branch. Follow the actual execution environment's authorization for pushes/PRs; this packet does not authorize force pushes, merges, tags, public releases, or changes to branch settings.

Read the source files in section 15 and the pinned OMP CLI help. Record the exact resolved config and command entrypoints, not guesses based on older OMP versions. Keep the handoff's decisions in a short `AGENTS.md` so subsequent agents do not undo them.

Use a fresh fixture workspace with no inherited project automation for initial tests. Never point an evaluated model at the user's real home directory, private repositories, production credentials, or the integration harness's verifier directory. Dependency downloads belong to setup, not the inference task's tool environment.

### 3.2 Select one hardware/runtime route

Read available authorized local host inventory and live facts. Existing private host-inventory files (names redacted for publication) can be consulted locally, read-only, when available. Do not publish their contents or discover hosts by scanning the network.

Prefer an **already available, idle RTX 5090 host** when its RAM, disk, driver, OS, and authorized access suit the chosen Strata profile. Otherwise select a suitable existing RTX 4090 or RTX 3090 host and document the reason. Choose **one** native Windows or Linux/WSL route based on actual availability and upstream compatibility. Native Windows is a reasonable first candidate for the existing fleet, not a mandate to migrate a working host. macOS may be a client or host-free CI environment; do not imply a qualified macOS Strata GPU runtime.

Capture locally: GPU model/VRAM and chosen device identifier; CPU and usable RAM; currently available RAM and Windows commit/pagefile headroom or Linux memory limits; disk free space and filesystem; OS/build; driver/runtime; available process-control route; existing GPU owners/listeners; and whether Windows, WSL and Docker see the same GPU. Public receipts use a neutral profile/machine label, not private network addresses or user paths.

Do not run two heavyweight runtimes on an occupied GPU simply because their ports differ. Do not stop the current NInfer runtime without explicit operational authorization. Use an idle/authorized host or finish host-free work and mark GPU testing blocked. A later authorized A/B must reserve exclusive GPU use and restore the previous operating state.

### 3.3 Model/quantization choice

For a sufficiently provisioned host, prefer **original Flash-Next IQ2_XS** as a balanced initial full-model candidate. Select the **Coder** variant instead when coding focus and actual memory constraints make it the appropriate bounded first profile. Name that profile and its limitations explicitly. This is a proposed engineering default, not an assertion of measured superiority.

Avoid an unbounded model bakeoff. Freeze one variant first. A second model/quantization is justified only by a failed fit/correctness gate or a targeted comparison question. Start with short-context smoke tests; attempt a 131,072-token configured profile only when memory permits. A smaller qualified profile is legitimate, but must not be marketed as a 128K qualification. Do not claim the model's maximum supported context merely from metadata.

Use baseline 8-bit KV where the selected upstream path supports it; keep optional speed-projection/control-vector modifications off. Treat low-RAM mode, altered KV format, calibration-derived tuning and other numerical/runtime switches as part of the profile fingerprint. Never turn them on silently to make a failing test pass. MTP may remain at the pinned upstream profile's default; record it.

Pin **all required model shards**, revision, filenames, byte sizes and SHA-256; tokenizer files and chat template; expert profile and allocation/conversion metadata; optional vision artifact only when qualified; engine build; Python server source/dependencies; and launch/effective sampling settings. A model label or `.gguf` extension is not an artifact identity.

A Git commit SHA and Git blob SHA are source identities, not file SHA-256 checksums. A checksum establishes that bytes match the chosen expectation; by itself it does not authenticate the publisher. Record where the expectation came from. Missing upstream binary/source provenance is a recorded limitation or a reason to build from source, not permission to claim verified provenance.

**M0 output:** compact `BASELINE.md`, selected draft profile, source/artifact lock, host preflight receipt or specific blocker, and a prioritized implementation checklist. Then continue to M1; do not stop at the audit when implementation is possible.

## 4. Milestone M1 — direct stock interoperability

### 4.1 First tracer: typed tool, result, answer

Build the smallest route that executes:

1. Launch the chosen stock Strata server on an unoccupied loopback port with a nonempty private API key.
2. Start stock OMP in the isolated integration profile against the exact selected model identifier using `openai-completions`.
3. In a disposable fixture repo, ask OMP to inspect a small source file, make a bounded correction with a typed tool call, run the fixture's tests, and summarize the result.
4. Continue the same session with a deterministic follow-up that depends on the prior tool result.
5. Stop only the processes owned by this test and retain a scrubbed receipt.

Inspect the actual stream and transcript: well-formed tool IDs, valid argument JSON, correct tool-result association, completion/finish semantics, and successful process exit. A friendly text response is not a tool-integration pass. A model's claim that tests passed is not a verifier result.

Run host-free mocks alongside this tracer, not instead of it. The mock should exercise the **real stock OMP binary/provider path** when that binary is available, with scripted HTTP/SSE responses. A mocked client talking to a mocked server cannot qualify OMP integration. Use Strata's upstream mock engine to exercise its real frontend where practical; a test-only fault server may simulate malformed/failed SSE. Neither mock belongs in production routing.

### 4.2 Proposed client configuration contract

Use provider ID **`strata-local`** and named OMP profile **`omp-strata`** unless they already exist; fail on a conflicting unrelated profile rather than overwrite it. Read the exact model ID from the controlled Strata installation and freeze it. The selected model name must distinguish original/Coder/other variants. No generic alias that silently points to different model bytes between runs.

The following is an **illustrative template to resolve and validate**, not a ready-to-install file. Replace sentinel values from the selected manifest. No literal sentinel may reach a launch.

```yaml
providers:
  strata-local:
    baseUrl: http://127.0.0.1:18090/v1
    api: openai-completions
    apiKey: STRATA_API_KEY
    authHeader: true
    models:
      - id: RESOLVE_EXACT_STRATA_MODEL_ID
        name: RESOLVE_VARIANT_AND_QUANTIZATION_LABEL
        api: openai-completions
        reasoning: true
        input: [text]
        supportsTools: true
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }
        contextWindow: RESOLVE_QUALIFIED_CONTEXT
        maxTokens: RESOLVE_TESTED_OUTPUT_LIMIT
        compat:
          supportsStore: false
          supportsDeveloperRole: false
          maxTokensField: max_tokens
```

The selected OMP version must actually resolve `STRATA_API_KEY` as an environment key; prove that missing/empty credentials fail before dispatch. Validate every field against the chosen OMP schema. Add reasoning-effort mapping only after inspecting OMP's adapter and Strata's frontend. Strata's documented efforts and OMP's internal levels are not necessarily named identically. Prove supported levels; reject unsupported mappings rather than pretending `xhigh` has a tested meaning.

Base launch settings, derived from the existing upstream-compatible NInfer pattern, are:

```yaml
retry:
  enabled: false
  modelFallback: false
  fallbackRevertPolicy: never
startup:
  checkUpdate: false
providers:
  maxInFlightRequests:
    strata-local: 1
```

That fragment is **not the whole fail-closed proof**. Resolve all model-consuming paths in the actual client: primary, compaction, small/fast helpers, planning, subagents and any enabled auxiliary roles. Pin enabled paths to the same local provider/model or explicitly disable them within the isolated profile. Verify the effective configuration and destinations. Do not change the user's production roles or account selection.

Do not carry NInfer-specific `PI_OPENAI_STATEFUL`, Responses flags, encrypted reasoning, remote compaction, cache lifetime claims, or appliance commands into Strata by rote. Keep `promptCache` TTL unset unless Strata has an appropriate supported contract; live prefix reuse is not a guaranteed cache lifetime.

### 4.3 Isolation, authentication and local-only behavior

Use a named OMP profile for user-level separation and a clean fixture worktree. Audit external-source/project discovery, inherited environment, extensions/hooks/MCP, credential fallback and shared model caches. For qualification, scrub unrelated provider credentials, use the pinned client's supported discovery controls, and validate effective configuration. An environment override alone is not a sandbox.

Keep both OMP client endpoint and Strata listener on loopback. A remote client may use the user's existing authenticated SSH/tunnel route where authorized, with both tunnel endpoints bound to loopback and independent API authentication. Do not expose `0.0.0.0`, disable host-key validation, alter firewall rules, or introduce a public ingress service. A local route is the initial accepted route; a remote route needs its own route receipt before being called supported.

Use an environment or protected local secret file supported by stock Strata, not a key on the process command line or in committed configuration. Fail if the key is missing or blank. Prevent its appearance in shell tracing, command receipts, exception output or uploads. Document that a shared secret is not multi-tenant isolation and localhost does not defend against a malicious process running as the same user.

Strata's browser/settings/health surface may have different authentication rules from generation endpoints. Inventory and test them; do not claim every static/health route is authenticated unless demonstrated. Disable Strata-side MCP, URL/image fetching capabilities and optional integrations not required by the text-only profile. Inference tools must execute through OMP, not through a second hidden server-side agent.

Separate installation network access from inference. For a claim that prompts stay local, enforce a qualification-specific outbound allowlist or equivalent process/container isolation: loopback and the designated tunnel only for inference; fixture tools offline. Prove failure rather than rerouting when the local service is unavailable. If the environment cannot enforce/observe this, mark the relevant security gate blocked; credential absence or one application log is insufficient to claim a network audit. Never alter the host's global network policy to implement a test sandbox.

Use synthetic secrets/canaries for tests. No real private prompt should be used to test a privacy promise.

## 5. Milestone M2 — a reproducible lifecycle

Implement a minimal lifecycle tool rather than a persistent manager. The **proposed** command surface below is to be built and documented; these commands do not exist merely because they appear in this packet:

```text
python scripts/omp_strata.py doctor --profile <profile.json>
python scripts/omp_strata.py install --profile <profile.json>
python scripts/omp_strata.py start --profile <profile.json>
python scripts/omp_strata.py status --profile <profile.json>
python scripts/omp_strata.py launch-omp --profile <profile.json> -- <omp-args>
python scripts/omp_strata.py stop --profile <profile.json>
python scripts/qualify.py --mode mock --profile <profile.json>
python scripts/qualify.py --mode gpu --profile <profile.json>
python scripts/verify_release.py --manifest <manifest.json> --require-ready
```

Names may be adjusted to existing repository conventions, but preserve the behavior and give exact tested commands in `QUICKSTART.md`.

**Doctor:** read-only inspection of profile completeness, dependency availability, memory/disk/driver compatibility, loopback bind choice, port occupation, GPU ownership and client configuration. No download, launch, driver change, auto-kill or config rewrite. Print actionable failures with redacted paths.

**Install:** use a dedicated integration root and venv; verify known artifacts and all model components; support a repeated invocation without redownloading verified bytes; keep `.partial` downloads and final promotion safe; reject hash mismatch. Show required/available space, including unpacking, model conversion and temporary copies. Do not replace the global `omp` executable, update it implicitly, or execute a mutable remote installer. Audit stock Strata setup's own automatic-update/download behavior; do not assume a pinned checkout implies pinned fetched binaries. A transparent pinned materialization wrapper is acceptable; copying Strata's entire installer is not.

**Start:** acquire a lock; verify immutable install identity and effective config; fail on occupied port, conflicting GPU owner or already-running unrelated process; record owned process identity (PID plus creation identity/executable/config, not PID alone); launch on loopback; wait for actual readiness with a bounded explicit timeout; validate actual model/config context; report no readiness until the model is loaded and the expected server answers. Do not attach to an arbitrary server on the expected port.

**Status:** distinguish not installed, stopped, starting, healthy, mismatched, degraded and failed. Inspect owned process and authenticated runtime metadata. A 200 health response by itself is not proof of the correct model or engine. Since a compatible API may accept arbitrary model aliases, bind identity primarily to the controlled launch/artifact fingerprints and report metadata limits honestly.

**Stop:** stop only the integration-owned process tree after checking identity. Repeated stop is harmless. A stale PID or unrelated occupied port must never result in a kill. Preserve OMP transcripts and installed model artifacts. Bound waits; do not silently escalate to killing unrelated processes. Test native Windows and WSL ownership differences on the selected route.

**Launch OMP:** invoke the separately pinned executable with the isolated profile, explicit provider/model and private credentials. Preserve exit status and signals. Do not add a proxy, reimplement OMP sessions or manually replay tool actions. Reject unauthorized model/provider override flags that would defeat the local-only launcher contract, or document an explicitly unrestricted launcher as a different tool.

**Rollback/cleanup:** preserve prior selected profile/config identities; switching back means selecting the previous verified installation, never overwriting model bytes in place. Before a second release exists, test cleanup plus restoration of the baseline environment; do not invent a successful two-version rollback. Never delete transcripts or shared model directories by default. Show the exact owned paths before an explicit purge, and prevent symlink/path traversal out of that root.

Freeze mutable shared server settings and generated expert/calibration data into the profile fingerprint, or explicitly reset them to the tested baseline at start. Refuse drift rather than silently changing benchmark settings.

## 6. Milestone M3 — correctness and acceptance

The canonical gate inventory is repeated in machine-readable form in this packet's `acceptance_matrix.json`. Every gate starts `not_run`. Each receipt identifies source/build/config/profile and its evidence boundary. Failures, skips and retries remain visible.

### 6.1 Host-free gates (must work in ordinary CI)

| Gate | What must be demonstrated |
|---|---|
| G00 | Repository/source baseline audit; no unintended existing-file changes; default branch handled correctly. |
| G01 | Manifest/profile validation rejects missing pins, sentinels, invalid context/output budgets, mismatched hashes, unsupported status/capability combinations and ready-without-evidence. |
| G02 | Separate OMP configuration; exact provider/roles; missing/blank key refusal; inherited discovery/config paths inventoried and tested. |
| G03 | Stock OMP against scripted server: complete streamed text and typed tool cycle; fragmented JSON, non-ASCII text and finish reasons handled. |
| G04 | Wrong/missing auth; 400/401/404/500; connection loss; malformed/truncated SSE; mid-stream error; cancelled/queued requests. No false completed turn, corrupted resumed transcript, cloud fallback or automatic duplicate tool side effects. |
| G05 | Lifecycle unit/process tests: repeat install/start/stop, occupied port, stale PID, config drift, hash mismatch, failed download, insufficient disk/memory and safe cleanup. |
| G06 | Read-only/least-privilege public CI with no inference credentials; untrusted PRs cannot reach self-hosted GPUs, private repos, SSH keys or release credentials. |

Do not require all inference failures to exit through the same OMP message if the pinned client has documented distinctions. Require an observable failure, a usable prior transcript and no mistaken success/automatic side effects. Test actual behavior rather than papering it over with a success exit code.

### 6.2 Real-host integration gates

| Gate | Test and pass boundary |
|---|---|
| G10 | Actual host preflight + artifact identity: selected GPU, memory/disk margin, engine/client/model/source pins, loopback-only listener and exclusive authorized GPU ownership. |
| G11 | Actual stock OMP tool loop: at least three independent runs complete read/edit/test/follow-up with verifier-confirmed outputs and correct tool IDs. Record legitimate model task failures separately from protocol failures. |
| G12 | Live same-session prefix reuse: at least three controlled continuations show nonzero reuse from engine-provided observations and correct outputs. Use a fixture with no compaction; report cache counters separately from latency. No requirement of universal reuse. |
| G13 | Safety/egress: missing/wrong key denied on protected generation routes; dead local server fails closed; auxiliary/compaction paths do not escape; test-specific network enforcement/observation is evidenced. |
| G14 | Cancellation during generation and while queued, failed tool execution and abrupt transport loss: next turn/session is valid; cancelled output is not falsely completed; no automatic repeat of non-idempotent fixture side effects. |
| G15 | Engine process restart while OMP session persists: retry only as a new deliberate turn; transcript remains authoritative; cold replay allowed; exact nonce/tool-result dependency is retained. Old engine state is not claimed restored. |
| G16 | OMP client restart/resume, then both client and engine restart: same intended transcript resumes; completed tools are not re-executed merely to reconstruct history; report replay cost and which process restarted. |
| G17 | Real long session at the declared profile window with reserved output space; coherent tool follow-up; overflow is an explicit error and does not silently truncate earlier content. Capacity measured with the actual tokenizer, not character length. |
| G18 | Real OMP compaction triggered at a reduced test threshold, followed by a valid typed tool turn and retained required task facts; plus a realistic long-session compaction on any profile advertised for long sessions. Record compaction timing, cache hits/misses and outbound destination. Do not demand lossless retention of arbitrary discarded text. |
| G19 | Two sessions interleaved A→B→A and one branch/resume case: intended transcript and synthetic canaries remain correct with no cross-session contamination. Cold re-prefill is allowed and measured; no retained-branch-tree guarantee. |
| G20 | Controlled install/start/stop/restart/cleanup on the real route; previous user operating state unchanged or explicitly restored; no orphan workers and no default-OMP/NInfer config mutation. |
| G21 | Resource headroom and repeatability: log peak process RAM, GPU VRAM, disk/temp usage, startup time and fatal/OOM events across the suite. Report measurements and practical floor; do not infer fit from model-file size. |

For G11, the harness's protocol success criterion is deterministic and all three runs must complete a valid protocol cycle; a correct tool invocation whose code patch fails external tests is a task-quality failure, not silently converted into a protocol pass for the code-fix requirement. Record both dimensions. A release's typed-tool demonstration must include verifier-confirmed successful code fixes; keep all failed attempts and the retry policy visible.

For G12, inspect the actual available Strata `reused`/cache counters or controlled engine log events and their meaning. Do not create a production proxy solely for observability. No cache counter available? Report `unknown` and investigate; latency alone does not prove KV reuse.

For G17/G18, distinguish a reduced threshold test from a real near-capacity test. A 32K smoke profile cannot qualify a 128K product. Do not repeatedly force OOM or stress unrelated user workloads to find the absolute maximum. Stop at a conservative reproducible profile.

For G19, distinguish output correctness from multi-tenant security. A single-user API key plus two session tests is not a security proof for hostile tenants. The initial supported product remains single-user and serialized.

### 6.3 Optional and decision gates

**G22 — images (optional):** only after the text route is green, qualify actual image artifacts, WebP/PNG conversion, image/tool round trips, context accounting and image compaction behavior. Until then keep `input: [text]`. An unsupported image request must not silently disappear; reject it in the client/validated launch path or document a blocker. No `supportsImageDetailOriginal` or related flag copied blindly from NInfer.

**G23 — remote client (optional):** qualify one authenticated loopback-to-loopback tunnel route, including failure/latency and restart behavior. Do not inherit it from the local route. No local-model-server support claim on macOS merely because OMP ran there.

**G24 — quality evaluation (required before product decision):** execute the bounded workload in section 7 and publish all outcomes. A comparison unavailable for operational reasons must be explicit.

**G25 — NInfer comparison (required only for comparative claims):** rerun a controlled NInfer baseline rather than borrowing historical README numbers. No superiority statement without same-boundary outcomes.

**G26 — clean-install acceptance and claims review:** a fresh installation root, using only the written quickstart and locked components, passes applicable required gates. A fresh root on the same machine is not a fresh-OS test; label it accurately. README/support matrix/status align with actual evidence and limitations.

## 7. Bounded, useful evaluation — not a benchmark platform

Create a small, fixed set of **six independent coding tasks** from synthetic or permissively licensed/public code: two ordinary bug fixes, one regression involving multiple files, one tool-heavy inspect/edit/test loop, one long-context retrieval-plus-change task, and one compaction/restart-sensitive continuation. Keep fixture source and authoritative test/verifier revisions pinned. Use short smoke variants first, then the actual evaluation fixtures.

Reserve immutable verifiers outside the model's writable worktree. Record preexisting test status. The model must not be able to make itself pass by editing the score script, suppressing tests or returning a persuasive sentence. Preserve patches, verifier exit/results and task transcripts locally; publish only permitted scrubbed evidence. An evaluated model can generate arbitrary code, so run it with a restricted account/worktree/container and no production secrets or general host administration.

Use one pilot pass to find harness bugs. Freeze prompts, verifier, time/tool/output budgets and scoring **before** the scored run. Then run each task three times on the one selected Strata profile: **18 scored attempts**. This is a bounded engineering sample, not statistical proof of universal superiority. Retain failures, timeouts and all retries; do not tune on the scored failures and present reruns as the same sample. A material harness fix creates a new versioned evaluation batch.

Default evaluation ceiling: 15 minutes per scored attempt and at most 40 tool invocations, with a profile-appropriate explicit output/context limit. These are proposed resource caps, not promised execution duration; adjust once before scoring if the cold long-context fixture requires a different bound. Record the decision and apply the same scoring boundary to a comparison. Use a total batch cap and an abort-on-repeated-OOM/unsafe-workspace rule.

For a comparison, use the same stock OMP version, prompts, tool implementation, fixtures, task budgets and verifier where both profiles support them. Prefer the same host with exclusive sequential GPU use under authorized scheduling. Alternate or deterministically randomize A/B order. Restore fixture worktrees between attempts; explicitly choose cold or warm conditions. When a same-host/client comparison is unavailable, state the confounders and do not call it an engine-only A/B. This is ordinarily a **full engine + model + quantization comparison**, because NInfer 27B and Strata Flash-Next are different models.

Report these primary outcomes:

- Verifier-confirmed task completion count and rate, including timeouts and failures in the denominator.
- End-to-end wall time **to a verified result**, success-only latency clearly labeled, and total budget consumed by failed attempts. Do not omit failures from the main report.
- Tool-call/protocol error counts, malformed arguments, crash/recovery cases, and human interventions.
- Cold startup/model-load time, first-turn prefill, warm-continuation latency, engine-restart replay, client-resume cost and compaction overhead as distinct boundaries.
- Peak RAM/VRAM/disk and observed cache-reuse counters for the tested machine/profile.

Tokens per second and MTP acceptance are secondary diagnostics. Keep model-reported usage separate from independently observed time. Do not fill missing counters with zero.

### Measurement definitions

Use monotonic clocks. `request_wall_ms` starts immediately before request dispatch and ends at a valid final response; `first_event_ms`, `first_reasoning_ms` and `first_visible_text_ms` are separate nullable fields. SSE keepalive comments are not first tokens. `task_wall_ms` includes agent calls, tools and verifier. Server-reported prefill/decode time has its own field and must not be compared to end-to-end wall time as though the boundaries match.

A fresh engine process with warm OS file cache is **process-cold, file-cache-warm**, not a fully cold system. Cache reuse after a live turn is not restart restoration. A 128K configured window is not a 128K accepted prompt when output reserve and template/tool tokens consume capacity. Record actual tokenized input and output allowance.

### Decision output

Write `docs/DECISION.md` with three separate decisions:

1. **Integration readiness:** which capabilities/routes passed, and which remain unsupported/blocked.
2. **Usefulness:** whether the bounded observed tasks justify keeping Strata as an optional local coding backend; include memory and operational costs.
3. **Further investment:** whether a next-stage durability investigation is justified by measured task utility and meaningful observed restart/prefill pain.

No automatic replacement of NInfer. No requirement to declare a winner. No benchmark threshold should be invented after seeing outcomes. The recommendation may be keep optional, revise the candidate, or stop investment while preserving the working prototype.

## 8. Receipts, identity and release status

A release manifest binds source revisions, binary artifacts, model components, tokenizer/template, effective config and one hardware/client route. Keep secrets out of hashes where a public hash would expose a low-entropy secret; fingerprint redacted configuration and record secret presence/auth mode separately. Hash the actual nonsecret files the runtime used, not a template with unresolved substitutions.

Each test receipt must contain: gate ID; `pass|fail|blocked|not_run|not_applicable`; run ID and UTC timestamp; mock vs real-host boundary; code commit; profile/config/manifest identity; expected and observed behavior; verifier/evidence references; metrics with explicit units/boundaries; limitations; and any retry history. `pass` requires actual evidence. Optional `not_applicable` requires a reason and a corresponding capability disabled in the manifest. `blocked` is not a pass.

Suggested statuses:

| Status | Meaning |
|---|---|
| `draft` | Implementation or pins/evidence incomplete. Safe to review, not a supported deployment. |
| `candidate` | Complete installable pins/config and host-free checks; hardware acceptance or clean-install work remains. |
| `qualified` | All required gates for the declared profile/routes passed with matching identities; optional omissions explicit. This is not a publication authorization. |

Keep `publication_authorized: false` unless the owner explicitly authorizes publication. Integration qualification does not require Strata to outperform NInfer, but does require truthful measured results and stated scope. G25 is mandatory only for an actual comparative claim. Long-context, vision, remote route and durable-state claims each require their own evidence/capability check; `durable_engine_state` remains false in v0.1 regardless of transcript recovery success.

`verify_release.py --require-ready` should refuse draft/candidate status, incomplete pins, stale or missing required receipts, failed/blocked required gates, mock-only hardware proofs, unresolved sentinels, mismatched profile/config identities and an unsupported capability claim. It must not require a circular hash of the manifest embedded in itself. Use a stable manifest identity or an explicitly defined hash over the immutable component/profile portion, then bind qualification separately.

Public evidence should be sufficient to understand outcomes without revealing user material. Keep unsanitized command/output/network traces locally under access controls; publish a reviewed export. Scrub authentication headers, environment secrets, home paths, hostnames, private repository references, SSH addresses and embedded credentials. A regex pass is not adequate authorization to publish private transcripts. Public synthetic fixtures make this easier.

## 9. CI and testing policy

Use ordinary hosted CI for lint, type checking where appropriate, unit/process tests, profile/schema validation, mock protocol tests and documentation command checks. Pin third-party actions to verified immutable revisions during implementation; do not invent action SHAs in this packet. Use minimum workflow permissions and no release secrets in ordinary PR jobs.

Never attach the user's personal GPU machines to untrusted public pull-request code. A self-hosted qualification job, if already safely available, must be explicitly/manual trusted-code-only, isolated, and secret-minimized. Do not use `pull_request_target` to check out and execute an attacker's branch with privileges. GPU runs can remain a documented manual command; there is no requirement to build a new runner fleet.

Tests for setup must cover hostile filenames/paths, symlink escape, untrusted archive traversal, redaction, partial downloads, tampered artifacts, occupied ports, ownership-lock races and interrupted launch. Avoid shell interpolation with untrusted config; validate argument arrays, use subprocess argv, and never load model-supplied executable config. Keep dependencies proportionate to a small integration repository.

Run upstream relevant mock/server tests as an additional check where feasible, with exact version and results. Passing upstream tests does not replace a composed OMP→Strata test, and a composed pass does not qualify untested upstream features.

## 10. Commit and review sequence

Prefer a small, reviewable series:

**A — bootstrap and baseline:** repository instructions, source facts, profile/manifest validation, host-free CI, no changed production state.

**B — tracer and configuration:** isolated stock-client route, typed tool loop, auth and no-fallback tests, one real-host receipt or a truthful blocker.

**C — lifecycle:** pinned materialization, doctor/start/status/stop/launch, cleanup/ownership tests and actionable runbook.

**D — qualification and decision:** long-session/restart/compaction/resource cases, bounded task evaluation, clean-install check and evidence-backed README.

Do not wait until D to run a real typed tool turn if a safe GPU host is available. Do not merge on passing mocks alone while claiming D is complete. A source-only or host-free result should still be clean, reviewable and executable by the next operator.

Independent review should focus on profile isolation/secret handling, process/GPU ownership, model identity, streaming/cancellation semantics, evidence validity and unsupported support claims. Fix release-blocking problems; do not turn review into speculative framework design.

## 11. Stop rules and bounded escalation

Stop the unsafe action, not all useful work, when: the target GPU is occupied without authorization; available memory/disk is insufficient; component provenance is unresolved; the setup would change a global install/driver/firewall; a task escapes the fixture boundary; credentials would be exposed; or the composed client silently reroutes. Preserve evidence and continue host-free or isolated work that does not depend on the blocker.

Repeated OOM or driver instability stops live testing of that profile. Choose a justified smaller profile only as a new fingerprinted candidate; do not repeatedly crash a personal workstation. A server accepting malformed output, an incomplete stream reported as success, or automatic repeat of a completed non-idempotent tool is a correctness blocker, not a benchmark wrinkle.

For a stock-client incompatibility: reduce to a tiny reproducer; verify documented settings; test a traceable fixed stock release when one exists; otherwise document a small proposed upstream patch. No broad engine fork, request-proxy rewrite, or durable Responses implementation without an explicit new scope decision. Do not conceal a patched runtime under a stock label.

When information can be determined from the repositories, CLI or authorized inventory, determine it rather than asking the owner. For genuinely unavailable access or destructive-action permission, record the precise blocked gate and minimum operator action, and complete everything else. Do not invent credentials or a host, and do not present a pending human action as completed.

## 12. Deferred durability work — explicitly not v0.1

If measured results later justify it, prepare a separate design for complete engine-state snapshotting and recovery. It must account for the positional KV/indexer state, recurrent state, PLE state/history, token/image identity and any speculative state requiring restoration or safe reconstruction; state ownership and consistency boundaries; cancellation; version/profile/model fingerprints; authenticated integrity; atomic publication; crash-safe recovery; and correct branching/eviction behavior.

A Responses-compatible envelope can be added only with a precise semantics contract. Addressed continuation, fork/rollback, durable snapshots and transcript replay are distinct capabilities. Neither serializing `ConvCheckpoint` nor wrapping Chat Completions establishes them. Keep OMP's transcript authoritative and do not create a second tool-execution/transcript owner. [S05, S06]

No code for that subsystem is requested in this packet. Record observed restart/prefill costs and any helpful upstream extension points, then stop at a design recommendation until scope is approved.

## 13. Definition of done and agent's final report

Deliver a working narrow integration or a clearly bounded blocked implementation—not just prose. At minimum, provide code/config, tests, exact setup/run commands, current status and source identities, a usable runbook, and the completed gate ledger with failures preserved.

A qualified result additionally requires the actual hardware/client route, typed tools, live cache observation, local-only controls, cancellation/restart/compaction/capacity/session correctness, resource evidence, clean-install acceptance and the bounded quality report. Optional image/remote claims remain off without their own evidence. No durable-state claim.

The final execution report must state:

- Commits/PR reference as permitted, changed-file summary, exact selected tuple and repository status.
- Commands actually run, mock vs GPU results, failed/blocked gates and evidence locations.
- Measured useful-task results and comparisons with correct boundaries; no borrowed throughput figures.
- Confirmation from actual checks that default OMP and NInfer installations/config/state remain unchanged, or an explicit exception with restoration evidence.
- Remaining unsupported capabilities and the smallest genuine operator action, when one is necessary.

Do not say "production-ready," "works on all NVIDIA GPUs," "fully offline," "drop-in NInfer replacement," "durable sessions," or "faster/better than NInfer" unless the exact relevant contract is proved and the wording matches this scope. "Local inference with transcript replay after restart" is different from "restores GPU state after restart."

## 14. Immediate execution checklist

Read the repo and this specification; freeze a source/config candidate; implement profile validation and isolation; run the shortest stock OMP→Strata tool tracer; add fail-closed/fault tests; wrap only the necessary lifecycle; run the real capacity/restart/compaction/session cases; measure six tasks without changing scoring after the fact; run clean-install acceptance; write an evidence-backed decision. Keep the prototype small and the claims narrower than the evidence.

## 15. Source map and evidence limitations

Sources below were accessed through GitHub during the feasibility review or this handoff preparation. URLs use immutable commits where resolved. The new-repo metadata is a dated observation. The agent must verify installed bytes and actual behavior; no GPU run, binary download verification, end-to-end Strata test, or benchmark was performed while preparing this handoff.

- **S00 — new-repo metadata:** `https://api.github.com/repos/alphastorm/omp-strata` (observed September 30, 2026; empty, default-branch metadata `master`).
- **S01 — Strata product/model scope:** `https://github.com/Niko1221/Strata/blob/a79080535d1b2a71a3419a0d97d8e7dca194b0f1/README.md`
- **S02 — Strata requirements and measurement caveats:** `https://github.com/Niko1221/Strata/blob/a79080535d1b2a71a3419a0d97d8e7dca194b0f1/docs/DETAILS.md`
- **S03 — Strata server API/engine boundary:** `https://github.com/Niko1221/Strata/blob/a79080535d1b2a71a3419a0d97d8e7dca194b0f1/serve/server.py#L1-L80`
- **S04 — Strata generation/server launch/settings:** `https://github.com/Niko1221/Strata/blob/a79080535d1b2a71a3419a0d97d8e7dca194b0f1/serve/server.py#L1420-L1790` (also inspect auth handlers and `with_shared` in this file).
- **S05 — Strata live checkpoint implementation:** `https://github.com/Niko1221/Strata/blob/a79080535d1b2a71a3419a0d97d8e7dca194b0f1/src/program/generate.cpp` — search `ConvCheckpoint`, `checkpoint_save`, `checkpoint_restore`, `live_ok`, `checks.erase`.
- **S06 — Strata session-state structure/cache policy:** `https://github.com/Niko1221/Strata/blob/a79080535d1b2a71a3419a0d97d8e7dca194b0f1/include/strata/core/session.hpp` and `https://github.com/Niko1221/Strata/blob/a79080535d1b2a71a3419a0d97d8e7dca194b0f1/src/program/conv_cache_test.cpp`
- **S07 — NInfer release manifest:** `https://github.com/alphastorm/omp-ninfer/blob/dd10bf33ddbbb4925bf6dd633980001354b3e1cf/releases/v0.8.7/manifest.json`
- **S08 — NInfer current client/install contract:** `https://github.com/alphastorm/omp-ninfer/blob/dd10bf33ddbbb4925bf6dd633980001354b3e1cf/docs/QUICKSTART.md`
- **S09 — NInfer current provider/fail-closed examples:** `https://github.com/alphastorm/omp-ninfer/blob/dd10bf33ddbbb4925bf6dd633980001354b3e1cf/examples/manual-tunnel/models.fragment.yml` and `https://github.com/alphastorm/omp-ninfer/blob/dd10bf33ddbbb4925bf6dd633980001354b3e1cf/examples/manual-tunnel/fail-closed.yml`
- **S10 — pinned OMP profile/discovery boundaries:** `https://github.com/can1357/oh-my-pi/blob/401778d0cd30020ce0f9198f751b13c68850562f/docs/config-usage.md#profiles`
- **S11 — pinned OMP provider/model schema:** `https://github.com/can1357/oh-my-pi/blob/401778d0cd30020ce0f9198f751b13c68850562f/docs/models.md`

### Required implementation reads (not additional proven behavior)

At the selected exact source, also inspect OMP's `packages/ai/src/providers/openai-completions.ts`, model registry/resolver/settings modules and relevant session tests; Strata's `serve/frontend.py`, `serve/test_server.py`, `setup.py`, `engine_args`/`child_env`/auth handlers in `serve/server.py`, and model license/revision metadata. These are verification tasks for the executing agent, not claims that every path has already been audited.
