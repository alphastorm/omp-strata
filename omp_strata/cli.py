"""Command-line surface for the lifecycle tool (see docs/QUICKSTART.md for tested invocations)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import fetch as fetch_mod
from . import install as install_mod
from . import lifecycle
from .common import IntegrityError, eprint
from .layout import Layout, default_root
from .profile import ProfileError, load

PLATFORMS = ["windows-x64", "darwin-arm64", "linux-x64"]


def _layout(args: argparse.Namespace) -> Layout:
    profile = load(Path(args.profile))
    return Layout(root=Path(args.root).resolve() if args.root else default_root().resolve(), profile=profile)


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def cmd_validate(args: argparse.Namespace) -> int:
    profile = load(Path(args.profile), require_status=args.require_status)
    _print({"profile_id": profile.id, "fingerprint": profile.fingerprint, "status": "valid"})
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    layout = _layout(args)
    only = set(args.only.split(",")) if args.only else None
    items = fetch_mod.fetch(layout, platform=args.platform, only=only, log=eprint)
    _print({"fetched": [{"name": i.name, "file": i.dest.name, "sha256": i.sha256} for i in items]})
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    layout = _layout(args)
    problems = fetch_mod.verify(layout, platform=args.platform, deep=args.deep, log=eprint)
    _print({"problems": problems})
    return 1 if problems else 0


def cmd_lock_python(args: argparse.Namespace) -> int:
    layout = _layout(args)
    with lifecycle.FileLock(layout.lock_file):
        install_mod.checkout_strata(layout, log=eprint)
        out = install_mod.lock_python(layout, Path(args.out), log=eprint)
    _print({"lock": str(out), "sha256": install_mod.sha256_file(out)})
    return 0


def cmd_dev_env(args: argparse.Namespace) -> int:
    layout = _layout(args)
    with lifecycle.FileLock(layout.lock_file):
        fetch_mod.fetch(layout, only={"omp"}, log=eprint)
        install_mod.checkout_strata(layout, log=eprint)
        python = install_mod.dev_python(layout, log=eprint)
    binary = layout.omp_binary()
    if os.name != "nt":
        binary.chmod(binary.stat().st_mode | 0o111)       # release assets arrive without the execute bit
    env = {"OMP_STRATA_OMP_BINARY": str(binary), "OMP_STRATA_STRATA_SRC": str(layout.strata),
           "OMP_STRATA_STRATA_PYTHON": str(python)}
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        _print({"env": env})
        return 0
    return subprocess.call(command, env={**os.environ, **env})


def cmd_install(args: argparse.Namespace) -> int:
    layout = _layout(args)
    with lifecycle.FileLock(layout.lock_file):
        record = install_mod.install(layout, log=eprint)
    _print({k: record[k] for k in ("profile_id", "runtime_identity_sha256", "strata_commit",
                                   "mtp_tensor_manifest_sha256", "python")})
    return 0


def cmd_keygen(args: argparse.Namespace) -> int:
    layout = _layout(args)
    path = lifecycle.keygen(layout)
    _print({"key_file": str(path.relative_to(layout.root)), "created_or_present": True})
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    layout = _layout(args)
    report = lifecycle.doctor(layout)
    _print(report)
    return 0 if report["ok"] else 1


def cmd_start(args: argparse.Namespace) -> int:
    layout = _layout(args)
    _print(lifecycle.start(layout, tool_argv=lifecycle.tool_argv(), log=eprint, timeout=args.timeout))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    layout = _layout(args)
    return lifecycle.serve(layout, log_path=Path(args.log))


def cmd_status(args: argparse.Namespace) -> int:
    layout = _layout(args)
    st = lifecycle.status(layout)
    _print(st)
    return 0 if st["state"] in ("healthy", "stopped", "not_installed") else 1


def cmd_stop(args: argparse.Namespace) -> int:
    layout = _layout(args)
    _print(lifecycle.stop(layout, log=eprint))
    return 0


def cmd_restart(args: argparse.Namespace) -> int:
    layout = _layout(args)
    _print({"stop": lifecycle.stop(layout, log=eprint),
            "start": lifecycle.start(layout, tool_argv=lifecycle.tool_argv(), log=eprint, timeout=args.timeout)})
    return 0


def cmd_launch_omp(args: argparse.Namespace) -> int:
    from . import ompcfg                                  # imported lazily: only launch paths need it

    layout = _layout(args)
    key = lifecycle.ensure_healthy(layout)
    ompcfg.install_profile_config(layout)
    env = ompcfg.isolated_env(layout, api_key=key)
    extra = args.omp_args[1:] if args.omp_args[:1] == ["--"] else args.omp_args
    argv = ompcfg.omp_argv(layout, extra=extra)
    stdin = None if sys.stdin is not None and sys.stdin.isatty() else subprocess.DEVNULL
    return subprocess.call(argv, env=env, stdin=stdin)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="omp_strata.py", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--profile", required=True, help="candidate profile JSON")
        p.add_argument("--root", help="dedicated integration root (default: $OMP_STRATA_ROOT or ~/omp-strata)")

    p = sub.add_parser("validate", help="validate a profile (no host access)")
    p.add_argument("--profile", required=True)
    p.add_argument("--require-status", choices=["draft", "candidate", "qualified"])
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("doctor", help="read-only host and install inspection")
    common(p)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("fetch", help="download or reuse pinned artifacts and verify them")
    common(p)
    p.add_argument("--platform", choices=PLATFORMS)
    p.add_argument("--only", help="comma list of omp,engine,llama,model")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("verify", help="re-check pinned artifacts on disk")
    common(p)
    p.add_argument("--platform", choices=PLATFORMS)
    p.add_argument("--deep", action="store_true", help="rehash even when a cached verification matches")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("lock-python", help="maintainer: resolve and hash-lock stock setup.py's Python packages")
    common(p)
    p.add_argument("--out", required=True, help="lock file to write (commit it and pin its sha256 in the profile)")
    p.set_defaults(func=cmd_lock_python)

    p = sub.add_parser("dev-env", help="maintainer: host-free test prerequisites (this platform's OMP binary, the "
                                       "pinned Strata source and its Python env); print them, or run a command with "
                                       "them set")
    common(p)
    p.add_argument("command", nargs=argparse.REMAINDER, help="-- then a command to run with OMP_STRATA_* set")
    p.set_defaults(func=cmd_dev_env)

    p = sub.add_parser("install", help="materialize the pinned stock Strata install under the root")
    common(p)
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("keygen", help="create the private API key file (never printed)")
    common(p)
    p.set_defaults(func=cmd_keygen)

    p = sub.add_parser("start", help="start stock Strata on loopback and wait for verified readiness")
    common(p)
    p.add_argument("--timeout", type=int, help="readiness timeout seconds (default: profile)")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("serve", help=argparse.SUPPRESS)
    common(p)
    p.add_argument("--log", required=True)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("status", help="report not_installed/stopped/starting/healthy/mismatched/degraded/failed")
    common(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("stop", help="stop only integration-owned processes (idempotent)")
    common(p)
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser("restart", help="stop owned processes, then start with verified readiness")
    common(p)
    p.add_argument("--timeout", type=int, help="readiness timeout seconds (default: profile)")
    p.set_defaults(func=cmd_restart)

    p = sub.add_parser("launch-omp", help="run pinned stock OMP in the isolated omp-strata profile")
    common(p)
    p.add_argument("omp_args", nargs=argparse.REMAINDER, help="-- then arguments for omp")
    p.set_defaults(func=cmd_launch_omp)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ProfileError as exc:
        for problem in exc.problems:
            eprint(f"profile: {problem}")
        return 2
    except IntegrityError as exc:
        eprint(f"integrity: {exc}")
        return 3
    except (lifecycle.LifecycleError, install_mod.InstallError) as exc:
        eprint(f"error: {exc}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
