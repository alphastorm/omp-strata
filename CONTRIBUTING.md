# Contributing

`omp-strata` is developed in public. Issues and pull requests are welcome; the bar is that behavior claims are
proven, not described, and that nothing here forks or patches the two stock projects it runs.

## Before you start

- Read [`AGENTS.md`](AGENTS.md) for the decisions later work must not undo, [`docs/BASELINE.md`](docs/BASELINE.md)
  for the component tuple and [`docs/UPSTREAM.md`](docs/UPSTREAM.md) for what is already reported upstream. A fix
  for stock Strata or stock OMP belongs in [Niko1221/Strata](https://github.com/Niko1221/Strata) or
  [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi), and reaches this repository as a new pinned release in a
  new profile.
- Python standard library only, runtime and tests (`unittest`); thin PowerShell only where Windows process
  behavior requires it. There is nothing to install.
- Run the host-free suite before and after your change. It must be green:

  ```sh
  python3 scripts/check_public_hygiene.py
  for profile in profiles/*.json; do python3 scripts/omp_strata.py validate --profile "$profile"; done
  for manifest in releases/*/manifest.json; do python3 scripts/verify_release.py --manifest "$manifest"; done
  python3 scripts/omp_strata.py dev-env --profile profiles/win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6.json -- \
    python3 -m unittest discover -s tests -t .
  ```

## What a change needs

1. **The local gate.** The commands above: the public-hygiene scan (also run by `.githooks/pre-commit`; enable it
   with `git config core.hooksPath .githooks`), every profile validated, every release ledger verified, and the
   unit, mock and composed tests against the pinned stock OMP client. CI runs the same commands.
2. **Profiles are immutable identities.** `profiles/<id>.json` is the single source of truth for a candidate. A
   changed component, pin or setting is a new profile id with its own integration root and release ledger; it
   never edits a predecessor's profile, ledger or receipts.
3. **Real-host evidence for real-host claims.** A gate result, measurement or evaluation figure comes from a run on
   the named host, recorded as a receipt under `releases/<profile>/` through `omp_strata.receipts` and checked by
   `scripts/verify_release.py`. Mocks never satisfy a real-host gate; `blocked` is not a pass; failures stay in the
   ledger. [`docs/OPERATIONS.md`](docs/OPERATIONS.md) describes requalifying a new tuple.
4. **Public hygiene.** Public text never contains hostnames, machine names, user names in paths, private IPs,
   tailnet names, GPU UUIDs, serials, keys, tokens, transcripts or raw logs. Use neutral labels such as
   `host: rtx5090-win-a`; raw evidence stays on the host and only scrubbed exports enter `releases/`.
5. **Documentation in the same change.** A changed command, threshold, gate or claim updates `README.md` and the
   relevant `docs/` page; a changed status updates the candidate's ledger first.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
`type(scope): description`, lowercase imperative. No force-push, tag, release or publication without the owner.

## Brand and site

The mark, artwork sources, the public site and their coherence test are described in
[`docs/BRAND.md`](docs/BRAND.md). After editing an artwork source, run `python3 scripts/render_assets.py` and
commit the rendered PNGs with it.

## Security

Report vulnerabilities privately per [`SECURITY.md`](SECURITY.md).
