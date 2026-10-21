# Owner-selected Strata beta: metadata only; stable component releases install natively

## Stable component releases (v0.2.1 and later)

Stable [v0.2.1](https://github.com/Niko1221/Strata/releases/tag/v0.2.1) ships the same component packaging as this
beta. omp-strata now installs such a stable release through **native pinned-source setup with a deliberately staged
engine component** ([OPERATIONS.md](OPERATIONS.md#upgrades)): the profile pins the CUDA 13 engine tarball and its
manifest identity (`strata.engine_component`), `install` verifies and stages it into the native `engine/` folder,
and stock setup reuses it. That settles the first four rows of the table below for stable Windows CUDA 13
components. The packaged-Control runtime, the signed feed, updater state and desktop installers remain unused and
unimplemented, and component **beta** drafting stays refused: this beta campaign remains metadata only.

## Frozen source, not a qualified runtime

The selected app release is [`Niko1221/Strata v0.2.0-beta`](https://github.com/Niko1221/Strata/releases/tag/v0.2.0-beta):
release **417326565**, published **2026-10-19T13:52:01Z**; annotated tag object
`b73dbce3edb8dac72a5642f46d1273197008fc4d`, peeled commit
`3d1fb48090e8f2cefc22d7b5845fb7f5b71f33fa`. App version **0.2.0-beta** is distinct from
engine/Control **0.1.45.3**. GitHub's `prerelease=false` and `immutable=false` neither make this beta stable
nor promise that its assets cannot change. The separate [beta campaign](../releases/campaigns/v0.2.0-beta.json)
freezes the complete publisher inventory; its five pending profile names are not runnable profiles.
The existing v0.1.45 campaign and every predecessor receipt remain unchanged.

| Windows x86_64 component | Asset ID | Bytes | Publisher SHA-256 |
| --- | ---: | ---: | --- |
| `strata-control-0.1.45.3-windows-x86_64.zip` | 656392166 | 72019100 | `b783c80a77f4f3928d00387062c8b2fdd528d5cb9a400aacf4da5bcf3a2468f2` |
| `strata-engine-0.1.45.3-windows-x86_64-cuda-cuda13.tar.gz` | 656404728 | 579788606 | `1b3845ecc3a46644ddc11e5296ab3d35026dbf650041c53657c43874682d1559` |
| `strata-engine-0.1.45.3-windows-x86_64-cuda-cuda12.tar.gz` | 656401254 | 818382624 | `909ef954f93dcc9a5a3e756b6ac7836b9731b10f0fbe6e22ae316a1ede3da1f7` |

These are publisher digests, **not locally downloaded/rehashed binaries**. The public release-ID and tag endpoints
and paginated asset endpoint were re-read; these three identities and the source identity match the selected packet.
The inventory includes the other platforms, desktop installers and signed-feed objects, not just these three files.
No installer, Control archive or engine archive was downloaded; no signed feed was consumed or signature verified.

## Metadata-only commands

```sh
python3 scripts/upstream_watch.py draft --release v0.2.0-beta --allow-prerelease \
  --platform windows-x86_64 --backend cuda --variant cuda13 --check
python3 scripts/campaign.py open --release v0.2.0-beta --allow-prerelease --check
```

Both print the frozen source identity and complete inventory without writing files or fetching binaries.
The first also selects the actual Control zip plus the explicit CUDA variant's tarball. `cuda12` is another
metadata selection, not evidence that a particular GPU/driver supports it; host architecture/backend/driver and
the signed package's compatibility constraints must be checked before installation. No variant is guessed.
Missing publisher digests are represented as `sha256: null` plus the download URL; such inventory entries cannot
be converted into executable artifact pins.

Without `--allow-prerelease`, beta intake is refused even though GitHub calls it a normal release.
`upstream_watch report` continues to discover only stable releases and uses only stable qualified baselines.
A legacy stable single-zip draft still follows its existing source/dependency checks and now saves
`source-release.json` beside its fresh ledger. Both intake paths compare against an existing campaign's frozen
identity before proceeding. Moved tags, replaced/missing assets (including changed asset IDs), inconsistent
release-ID/tag responses and incomplete pagination are unavailable, never a refresh of prior evidence.

`campaign.py open --release v0.2.0-beta --allow-prerelease` records/reuses **metadata only** in its separate
schema-2 campaign, then returns **exit 2 / blocked** with this note's path: it cannot produce a runnable beta draft.
Without the opt-in it returns exit 2 without creating a campaign. `--check` returns 0 only for a successful
metadata check and reports `install_supported: false`. `status` remains an observation-only read.
Beta campaigns never participate in stable pending-row coalescing, in either direction; no running, failed,
qualified, queued, blocked or pending stable row is superseded by beta intake.

## Exact remaining profile/install delta

This is **not** a bounded new archive extension. Source inspection at the frozen commit establishes two different
contracts ([upstream update layout](https://github.com/Niko1221/Strata/blob/3d1fb48090e8f2cefc22d7b5845fb7f5b71f33fa/packaging/UPDATES.md)):

- Native `setup.py::get_prebuilt` still asks for `strata-windows-x64.zip` (or the legacy CUDA12 zip), uses
  `zipfile.ZipFile`, and installs into `engine/` (`engine-cuda12/` for CUDA12). `engine_step` can install Python CUDA
  wheels and `cuda_lib_dirs` searches their site-packages directories. No legacy zip exists in this release.
- `packaging/feed_tool.py::{pack_control,pack_engine}` archives each component's files **at the archive root**.
  `strata_control/engine_component.py::{components_dir,resolve,package_lib_dirs}` instead uses
  `components/engine/<version>-<platform>-<backend>[-<variant>]/engine-component.json`, independently versioned
  manifests, bundled libraries and their contained `BUILD.json` `lib_dirs`. Control setup writes
  `exe: component:strata-engine`; its engine/runtime contract is not the current native integration contract.

A separately reviewed component-install change must explicitly settle and test these surfaces; **none of the
following proposed fields or alternate runtime behavior is implemented here**:

| Current files/functions | Required contract delta and risk |
| --- | --- |
| `omp_strata/profile.py::validate`, `scripts/upstream_watch.py::draft` | Pin app/source identity separately from `engine_version=0.1.45.3` and Control version. Introduce explicit package-layout/platform/backend/variant and distinct Control + engine artifact pins (`url`, `file`, `bytes`, `sha256`, provenance), plus engine-manifest hash/build ID/architecture/minimum-driver/minimum-runtime bindings if consuming the signed feed. Resolve the selected package against real host facts; never infer engine version from the app tag or silently reuse the predecessor Python lock. |
| `omp_strata/layout.py::Layout`, `omp_strata/fetch.py::{plan,fetch,verify}` | Add distinct Control archive/component destinations within the new integration root. Download and rehash both selected archives; if the signed feed is consumed, pin its exact bytes/signature/trusted public key and enforce its channel/sequence/expiry and package constraints. Inventory digests alone do not verify signatures or extracted files. |
| `omp_strata/install.py::{install,run_setup,setup_argv,install_python,stage_llama,mtp_pinned}` | Choose native pinned-source setup with deliberately staged components **or** an explicitly reviewed packaged-Control runtime; do not switch implicitly. Implement bounded traversal/link-safe zip/tar extraction, manifest/signature/file checks and no-fetch preparation. Native setup's old `--prebuilt` contract cannot consume the tarball unchanged; Control changes interpreter/source/config paths and setup mode. Never rename a tarball to the old zip or use the desktop installer. |
| `omp_strata/install.py::{verify_generated,engine_build,runtime_identity}` | Bind the selected executable and versioned component root, not just `runtime/strata/engine/strata.exe`. Hash every consumed manifest, Control/runtime input and nested runtime library; current engine hashing includes only top-level files. Validate all library paths stay inside the root and bind those paths/files in the install record. Do not broaden `engine_labels` to let app version 0.2.0-beta stand in for engine 0.1.45.3. |
| `omp_strata/lifecycle.py::{verify_install_fast,server_argv,server_env}` and relevant install/lifecycle tests | Recheck the new hash-bound record and resolve only the pinned component, never mutable per-user active state. Keep component directories/no-acquire behavior root-local; inherited `STRATA_*` is currently scrubbed, so any required component environment must be explicit. Preserve owned-process identity/stop behavior, empty shared settings, loopback-only listening, nonblank API key, text-only/vision-off setup, stock OMP/model/context and no cloud fallback. |

Before a runnable beta profile: host-free extraction/config/library-drift/refusal tests and source-planning/dependency
review must pass for the chosen contract. Then a separately authorized RTX 5090 **131K** lease may establish its own
real-host gates, measured behavior and actual tenant restoration. No host result, default switch, qualification,
other-card inheritance, Control/app-agent adoption or performance claim follows from this metadata intake.
