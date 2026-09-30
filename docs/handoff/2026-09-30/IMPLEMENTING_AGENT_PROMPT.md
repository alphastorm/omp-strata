# Implement OMP Strata

Work in `https://github.com/alphastorm/omp-strata`. Read `HANDOFF.md` completely; it is the authoritative execution specification. The packet is self-contained. Inspect the real repo first and preserve work created after the packet. At handoff preparation the repo was empty and metadata named `master` as the default branch; do not assume `main` exists.

Implement a thin, independently qualified **stock Oh My Pi + stock Strata** integration. Leave `omp-ninfer`, its runtime/checkpoints, the global OMP binary and the user's default OMP configuration untouched. Do not copy the NInfer repository wholesale. No production proxy, OMP fork, generic backend platform, Responses shim or durable-engine-state subsystem in v0.1.

Start with one available authorized GPU/runtime profile and one model/quantization. Use an isolated `omp-strata` OMP profile, the `strata-local` provider, Chat Completions (`api: openai-completions`), a real private API key, authenticated loopback/tunnel access and no cloud fallback. Named profiles are not complete isolation: audit external/project discovery, inherited credentials, roles, extensions and compaction routing. Freeze stock Strata's mutable shared settings and record actual served-artifact identity.

Proposed source candidates are stock OMP v18.4.0 (`401778d0cd30020ce0f9198f751b13c68850562f`) and Strata `a79080535d1b2a71a3419a0d97d8e7dca194b0f1`; these are audited source references, NOT a completed installation lock. Verify actual binaries, model shards, tokenizer/template and dependencies. Resolve a newer stock release only for a concrete reason; record it and freeze the selected tuple before qualification.

Execute in this order: inspect/freeze → shortest real typed-tool tracer → fault/auth/isolation tests → minimal reproducible lifecycle → real restart/long-context/compaction/session tests → bounded coding evaluation → clean-install acceptance and evidence-backed decision. Do not spend the first phase building release infrastructure while avoiding a real tool turn when a safe GPU is available.

Use `acceptance_matrix.json` as the initial gate inventory. All gates begin `not_run`. Integration success, useful-task performance and comparative superiority are separate decisions. Test OMP against the real Strata stack on hardware; mocks do not prove GPU support. Live prefix reuse is useful but not durable checkpoint restoration. Engine/client restart recovery is from OMP's authoritative transcript and may re-prefill. Do not migrate NInfer checkpoints or response IDs.

Never interrupt an occupied GPU, modify drivers/firewalls/global installs, expose secrets/private host details or execute evaluation tools outside disposable restricted workspaces. No untrusted public PR code on personal self-hosted runners. No purchases or paid inference. Stop unsafe actions and record blockers; continue safe implementation/mock/CI work rather than returning only a plan.

Create a small reviewable commit series according to the execution environment's permissions. Do not force-push, merge, tag, publish releases or mutate repo settings on the strength of this packet. Do not fill missing artifacts, measurements or checksums with plausible values.

Finish with code/config and exact run commands, selected pins/profile, tests actually run, gate status/evidence, measured quality/latency/resource results, actual unchanged/restored baseline checks, and genuine remaining blockers. A source-only result is not a qualified release. Do not stop at another architecture proposal.
