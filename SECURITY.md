# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub private vulnerability reporting:
[Report a vulnerability](https://github.com/alphastorm/omp-strata/security/advisories/new).

Include the affected commit, the profile id, the stock Strata and OMP versions it pins, the host route
(native Windows), and reproduction steps. Redact the API key, transcripts, host and user names, private paths
and GPU identifiers; the scrubbing rules in `scripts/check_public_hygiene.py` are the minimum.

If GitHub private vulnerability reporting is unavailable, contact `@alphastorm` through a private channel listed
on the maintainer's GitHub profile.

## Scope

The security boundary, what is and is not isolated, the observed egress and the known defects are documented in
[`docs/SECURITY.md`](docs/SECURITY.md). This integration runs one stock Strata server on loopback for one local
user and drives it with the stock OMP client: it is not a sandbox, a multi-tenant service or an egress firewall.
Defects in stock Strata or stock OMP themselves belong upstream
([Niko1221/Strata](https://github.com/Niko1221/Strata), [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi));
[`docs/UPSTREAM.md`](docs/UPSTREAM.md) lists what has already been reported and what each release fixed. The
cut-off tool call that fails gate G04 is a documented, open upstream defect, not a new report.

## Supported versions

The latest commit on `main` and the current candidate profile named in [`README.md`](README.md) receive fixes.
Predecessor profiles keep their ledgers as rollback installations and are not updated; a fix for one of them is a
new profile with its own ledger.
