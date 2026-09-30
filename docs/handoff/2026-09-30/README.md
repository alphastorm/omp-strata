# OMP Strata execution packet

Prepared September 30, 2026 for `alphastorm/omp-strata`.

**Give the executing agent `IMPLEMENTING_AGENT_PROMPT.md` and this directory.** `HANDOFF.md` contains the complete standalone specification and portable source references. No access to the earlier chat is required.

| File | Purpose |
|---|---|
| `HANDOFF.md` | Authoritative scope, architecture, defaults, milestones, safety limits, tests, measurements and definition of done. |
| `IMPLEMENTING_AGENT_PROMPT.md` | Ready-to-paste execution instruction. |
| `acceptance_matrix.json` | Initial gate ledger; every gate is `not_run`. |
| `upstream_observations.json` | Audited source references and dated repository facts; not an installation lock. |
| `candidate.manifest.json` | Deliberately incomplete draft example; all installed/evaluated facts remain unresolved. |
| `receipt.schema.json` | Starting JSON Schema for an evidence receipt; application-level semantic validation is still required. |
| `SHA256SUMS` | SHA-256 checksums of these packet files, excluding this checksum file itself. |

This is an implementation handoff, not runtime code and not a release. It was prepared by reading repository sources; no Strata GPU execution, model/binary verification or performance benchmark was performed. The target repository was not modified by preparation of this packet.

The commands and configuration sentinels in `HANDOFF.md` are proposed implementation interfaces, not commands that are already installed. Resolve and validate them before use. Do not upload private host inventories, credentials, user transcripts or debug logs to this public repository.
