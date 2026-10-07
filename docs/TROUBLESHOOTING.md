# Troubleshooting

Match the first diagnostic, not a later failed request. Symptom headings below quote exact
source-backed strings; for messages containing a path, count, hash or state, the heading is the
**literal stable fragment**, not a fabricated complete message. Each source annotation is checked
by the documentation-drift unit test. CLI errors may prepend an error category.

Use the same profile and integration root for inspection and recovery. Never solve a refusal by
turning off authentication, changing a pin in place, adopting another process, or enabling a cloud
provider. New RAM, model, context or component settings require a new profile and root. Read the
[generated support matrix](COMPATIBILITY.md): a successful host-free check is not GPU qualification.
Keep keys, raw logs, prompts, session transcripts and private paths out of issues and receipts.

## Launcher and authentication

### `STRATA_API_KEY must be present and nonblank before starting OMP`
<!-- symptom-source: omp_strata/ompcfg.py -->
- Cause: the isolated launcher received no usable key. Raw stock OMP can send the environment
  variable's name as a literal bearer token instead of failing locally.
- Fix: use the integration's keygen and launch-omp commands in the same root. Do not pass a key in
  argv or copy it into model configuration. Do not launch the raw OMP binary to bypass this check.
- Reference: [security](SECURITY.md), [upstream OMP item 3](UPSTREAM.md#omp).

### `the API key file is blank or too short; refusing to start an unauthenticated server`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: the root's private key file is shorter than 32 characters, possibly empty or truncated.
- Fix: stop the owned runtime, preserve any needed private recovery material outside public output,
  remove only the invalid key file and run keygen for that root. Synchronize authenticated clients
  with the replacement key privately; then start. Never use an empty key as a workaround.
- Reference: [operations root layout](OPERATIONS.md#layout-of-the-integration-root).

### `OMP argument may override the isolated route or discovery policy`
<!-- symptom-source: omp_strata/ompcfg.py -->
- Cause: forwarded OMP arguments can change a protected model, provider, configuration or discovery setting.
- Fix: remove the override. Select a supported Strata profile/route through the integration instead;
  keep every chat role on a Strata provider and discovery disabled.
- Reference: [quickstart OMP usage](QUICKSTART.md#use-omp), [security](SECURITY.md).

### `/health reports the engine not loaded`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: the authenticated frontend responds but its inference engine is unloaded or has died;
  launch-omp refuses a runtime that is not healthy.
- Fix: inspect status and the root's private server log, resolve the engine failure, then restart
  the owned runtime. The transcript can replay; this does not restore GPU state.
- Reference: [operations recovery](OPERATIONS.md#failures-and-recovery).

## Remote client routes (draft)

### `binding changed since pull-key; run pull-key again`
<!-- symptom-source: omp_strata/remote.py -->
- Cause: the cached key's provenance record is missing, not user-only, or names another SSH alias,
  remote root or platform than the private binding now does; a key is never sent to a host it did
  not come from.
- Fix: confirm the binding names the intended host and root, then run pull-key for that route and
  client root. Do not copy key files between client roots or edit the provenance record.
- Reference: [remote routes](REMOTE.md), [security](SECURITY.md#remote-client-routes-and-fleets-draft-g23-not-run).

### `cannot verify the loopback listener owner`
<!-- symptom-source: omp_strata/remote.py -->
- Cause: the platform's listener query (lsof, /proc or Get-NetTCPConnection) failed or returned an
  incomplete answer, so the launcher cannot prove the SSH child owns the tunnel port.
- Fix: make the query work for the client user (on macOS, /usr/sbin/lsof must run) and launch
  again. The launcher never sends a key on an unverified listener.
- Reference: [security](SECURITY.md#remote-client-routes-and-fleets-draft-g23-not-run).

### `loopback listener is not owned exclusively by the SSH child`
<!-- symptom-source: omp_strata/remote.py -->
- Cause: another process also listens on the route's local port, or holds it instead of the SSH
  child.
- Fix: find and stop that process, or move the route to a free local port in a new route spec.
  Never adopt the listener.
- Reference: [remote routes](REMOTE.md).

### `SSH tunnel disconnected; OMP killed immediately`
<!-- symptom-source: omp_strata/remote.py -->
- Cause: an SSH child exited during the session (network loss, host restart, SSH failure). OMP is
  killed at once so it cannot reach a new listener on the freed port; the turn in flight is lost.
- Fix: restore the host and its server, launch again and resume the saved transcript explicitly.
  Nothing falls back to another provider.
- Reference: [remote routes](REMOTE.md).

## Doctor and start

### `occupied by an unrelated process`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: doctor's port check found a listener not identified as this integration's server.
- Fix: identify its owner and have the owner release the port. Use stop only for the matching
  owned root. A nonblocking doctor observation is not permission for start to adopt the listener.
- Reference: [operations lifecycle](OPERATIONS.md#lifecycle).

### `does not own; refusing to start or adopt it`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: start found the configured port occupied without a matching owned process identity.
- Fix: leave that process untouched and obtain its owner's release. Do not delete ownership records
  or change ports in a pinned profile merely to force a start.
- Reference: [operations lifecycle](OPERATIONS.md#lifecycle).

### `another runtime must be stopped by its owner first`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: doctor's GPU check sees memory use or compute/graphics clients incompatible with the profile.
- Fix: ask the runtime owner to stop that workload; inspect again before start. Display clients are
  permitted only when the profile explicitly declares a display-attached GPU.
- Reference: [operations lifecycle](OPERATIONS.md#lifecycle).

### `its owner must release it first`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: start refused a busy GPU, including at least 1,500 MiB used, a compute client, or an
  unpermitted graphics client. It does not evict other workloads.
- Fix: release the GPU through its owner's normal shutdown path. Do not kill an unrelated process
  or raise the idle threshold to hide the conflict.
- Reference: [operations lifecycle](OPERATIONS.md#lifecycle).

### `GiB available now (start needs`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: doctor's RAM availability observation reports currently free memory against the profile's floor.
- Fix: compare the reported values and free memory before start. Total installed RAM alone does not
  satisfy the start floor; a planned RAM upgrade is not installed capacity.
- Reference: [operations lifecycle](OPERATIONS.md#lifecycle).

### `GiB RAM available; the profile needs`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: start found less available RAM than the selected profile permits.
- Fix: stop competing workloads through their owners or wait for the required RAM to be installed.
  If a low-RAM configuration is needed, select its separate profile/root; never lower this floor
  in place. Reinstall under the intended new profile after a RAM change that changes setup flags.
- Reference: [operations upgrades](OPERATIONS.md#upgrades).

### `the install was made for a different profile fingerprint; reinstall or switch back`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: the root's install record belongs to another profile identity.
- Fix: switch back to the profile that owns the root, or install the new tuple into its own root.
  Preserve the predecessor's installation and evidence as rollback material.
- Reference: [operations upgrades](OPERATIONS.md#upgrades).

### `runtime inputs drifted from the install record:`
<!-- symptom-source: omp_strata/lifecycle.py -->
- Cause: recorded runtime input bytes no longer match the installed files.
- Fix: preserve the diagnostic privately, stop the owned runtime, verify its pinned artifacts and
  reinstall the same identity, or use a new profile/root for an intentional upgrade. Do not rewrite
  the install record to bless the drift.
- Reference: [operations root layout](OPERATIONS.md#layout-of-the-integration-root).

## Install and artifact integrity

### `unexpected engine flags`
<!-- symptom-source: omp_strata/install.py -->
- Cause: stock setup generated engine flags outside the profile's explicit expectations and allowed paths.
  Automatic RAM-dependent KV or low-RAM decisions can change after a host upgrade.
- Fix: compare stock setup at the pinned commit with the intended host configuration. Choose the
  corresponding separately pinned profile/root or create and qualify a new one; do not remove
  the flag guard or patch the generated engine command.
- Reference: [operations upgrades](OPERATIONS.md#upgrades), [upstream Strata item 5](UPSTREAM.md#strata).

### `unexpected config keys`
<!-- symptom-source: omp_strata/install.py -->
- Cause: stock setup emitted a configuration key the integration has not reviewed.
- Fix: stop the install and review the exact pinned source and that key's serving effect. A
  maintainer must update the reviewed contract with evidence before using a new tuple. Do not
  silently discard the key or allow arbitrary generated settings.
- Reference: [operations requalification](OPERATIONS.md#requalifying-a-new-tuple).

### `generated Strata config rejected:`
<!-- symptom-source: omp_strata/install.py -->
- Cause: one or more following details disagree with the profile: engine options, pinned model,
  executable, integration-root paths, or loopback listener.
- Fix: resolve the first listed mismatch using the pinned profile and guarded install. Never run
  stock bootstrap/update scripts, enable an unauthenticated listener, or hand-edit the generated
  configuration to bypass verification.
- Reference: [operations requalification](OPERATIONS.md#requalifying-a-new-tuple).

### `: sha256`
<!-- symptom-source: omp_strata/common.py -->
- Cause: fetch/verify hashed artifact bytes and found a digest different from the profile's pin;
  the diagnostic prints the file label, observed digest and expected digest after this fragment.
- Fix: preserve those nonsecret values, check disk space and interrupted transfers, and quarantine
  only the bad artifact before fetching the same pinned URL again. Re-run deep verify. Never
  replace the expected hash with the observed one without establishing a new pinned identity.
- Reference: [operations artifact layout](OPERATIONS.md#layout-of-the-integration-root).

### `; partial discarded`
<!-- symptom-source: omp_strata/common.py -->
- Cause: a completed partial download failed the pinned SHA-256 comparison; fetch discarded it.
- Fix: retry the same immutable artifact only after checking connectivity and free space. A repeated
  mismatch is a source/pin or transfer defect to investigate, not permission to accept different bytes.
- Reference: [operations artifact layout](OPERATIONS.md#layout-of-the-integration-root).

## Release verification

### `profile fingerprint mismatch`
<!-- symptom-source: scripts/verify_release.py -->
- Cause: manifest identity no longer matches the canonical profile contents.
- Fix: restore the original immutable profile or create a new profile and ledger for the intended
  change. Do not rebind old receipts to a changed profile; their identity remains historical.
- Reference: [operations upgrades](OPERATIONS.md#upgrades).

### `ledger sha256 mismatch`
<!-- symptom-source: scripts/verify_release.py -->
- Cause: the manifest's ledger digest does not match the exact ledger bytes.
- Fix: inspect the intended receipt/ledger update. After a legitimate update, use the maintainer's
  release-binding workflow; do not hand-edit digests to conceal missing or changed evidence.
- Reference: [operations upgrades](OPERATIONS.md#upgrades).

### `receipt sha256 mismatch`
<!-- symptom-source: scripts/verify_release.py -->
- Cause: the referenced receipt bytes changed after the ledger recorded their digest.
- Fix: recover the original receipt or record new evidence as a new receipt. Never overwrite a
  historical run or mutate its hash to make a failing proof pass.
- Reference: [operations logs and evidence](OPERATIONS.md#logs-and-evidence).

### `required gate is`
<!-- symptom-source: scripts/verify_release.py -->
- Cause: require-ready encountered a required gate whose recorded outcome is not pass.
- Fix: inspect the named gate and its evidence boundary. Run the real scenario when its
  prerequisites are available; leave unavailable real-host gates not_run. A mock cannot promote
  them, and a blocked or failed gate is not qualification.
- Reference: [compatibility matrix](COMPATIBILITY.md), [operations requalification](OPERATIONS.md#requalifying-a-new-tuple).

### `blockers remain:`
<!-- symptom-source: scripts/verify_release.py -->
- Cause: require-ready found unresolved release blockers, even if individual gate summaries look good.
- Fix: resolve and document the specific blockers with evidence before changing the manifest's
  readiness claim. A draft/candidate may validate structurally without being ready.
- Reference: [compatibility matrix](COMPATIBILITY.md), [upstream findings](UPSTREAM.md).

## Stock upstream symptoms

These entries describe versioned observations, not new qualification of any draft tuple. Consult
[upstream findings](UPSTREAM.md) for the exact commits and re-verification boundaries.

### `cancelled`
<!-- symptom-source: docs/UPSTREAM.md -->
- Cause: on Strata v0.1.27, disconnecting a queued request leaves stale cancellation state; a later
  long prompt can fail with HTTP 400 and the engine then exits. Short prompts can still work.
- Fix: restart the owned runtime before retrying. The fix shipped in v0.1.28 and was confirmed on
  the v0.1.30 real host; use a separately pinned tuple rather than modifying the old installation.
- Reference: [Strata item 1 / #183](UPSTREAM.md#strata).

### `the engine stopped unexpectedly (exit code 1); the next request restarts it`
<!-- symptom-source: docs/UPSTREAM.md -->
- Cause: the engine exited. This does not by itself establish OOM; historical stock messages
  incorrectly suggested OOM for unrelated crashes and deliberate kills.
- Fix: inspect the preceding private engine log, resolve the cause, and restart the owned runtime.
  A fresh engine requires cold prefill; the OMP transcript, not GPU cache, is the recovery source.
- Reference: [Strata item 6 / #215](UPSTREAM.md#strata), [operations recovery](OPERATIONS.md#failures-and-recovery).

### `finish_reason: tool_calls`
<!-- symptom-source: docs/UPSTREAM.md -->
- Cause: older Strata can finalize a tool call cut off mid-arguments as complete. Older OMP can
  also repair syntactically truncated arguments and execute a side effect.
- Fix: inspect affected side effects before retrying. Both halves need their fixes: Strata
  v0.1.31 and OMP 18.4.10. A valid-looking repaired JSON response cannot be detected by the client
  alone; do not treat a successful exit on an older tuple as proof of safe tools.
- Reference: [Strata item 2](UPSTREAM.md#strata), [OMP item 1](UPSTREAM.md#omp), G04.

### `requests are never truncated`
<!-- symptom-source: docs/OPERATIONS.md -->
- Cause: prompt plus requested output exceeds the configured engine context. Local token estimates
  and strict server accounting can differ near the boundary.
- Fix: compact or shorten the transcript/input and reduce requested output. Keep the integration's
  conservative declared window; a larger context requires its own profile, root and qualification.
- Reference: [operations recovery](OPERATIONS.md#failures-and-recovery), [OMP items 5–6](UPSTREAM.md#omp).

### `Bearer STRATA_API_KEY`
<!-- symptom-source: docs/UPSTREAM.md -->
- Cause: raw stock OMP resolved a missing environment key name as a literal token and the server
  refused authentication. This is not a signal to disable server authentication.
- Fix: use launch-omp with the root's private key, or the authenticated remote launcher with the
  matching private key file. Never record an actual bearer token in a public diagnostic.
- Reference: [OMP item 3](UPSTREAM.md#omp), [security](SECURITY.md).

### `HTTP 500`
<!-- symptom-source: docs/UPSTREAM.md -->
- Cause: a server failure can trigger stock OMP transport/provider retries even when integration
  retry settings are disabled; the recorded older-client probe produced 12 attempts.
- Fix: investigate the server failure and check for side effects before manually retrying. Keep
  retry and model fallback disabled, but do not claim those settings remove stock transport
  retries. Do not route failures to another provider.
- Reference: [OMP item 4](UPSTREAM.md#omp).
