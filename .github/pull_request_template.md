## Summary

<!-- What problem does this change solve? -->

## Validation

<!-- List the exact commands and results: the public-hygiene scan, profile validation, ledger verification, and the
unit, mock and composed tests through `dev-env`. Name any real-host gate rerun by run id; mark non-applicable checks
explicitly. -->

## Pins and evidence

- [ ] No profile, ledger or receipt of a predecessor candidate was edited; a changed component or setting is a new profile id.
- [ ] Every real-host claim in this change traces to a receipt under `releases/<profile>/` (mocks satisfy no real-host gate).
- [ ] `README.md` and `docs/` state the same status, pins and figures as the ledger they cite.

## Security and privacy impact

- [ ] No API key, transcript, host or user name, private path, GPU identifier or raw log is included in this PR or its artifacts.
- [ ] Changes to loopback binding, key handling, OMP's isolated profile or environment scrubbing are described, and `docs/SECURITY.md` is updated when the boundary changed.

## Upstream

<!-- State the stock Strata and OMP versions exercised. A fix for either stock project belongs upstream and arrives
here as a new pinned release in a new profile; link the upstream issue or PR if one exists. -->
