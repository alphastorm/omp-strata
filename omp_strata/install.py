"""Transparent pinned materialization of stock Strata into the integration root.

Stock `setup.py` is executed unmodified, but only after every input it would fetch from a mutable location is
already present and verified locally:

* engine: `--prebuilt <root>/downloads/strata/<tag>` (a local folder holding the hash-verified release asset);
* model:  `--gguf-dir <root>/models/<variant>-<quant>` (revision-pinned, hash-verified shards);
* llama.cpp: the hash-verified archive staged where `setup.get_llama_cpp()` looks, then extracted by stock code;
* MTP draft layer: stock `tools/mtp_fetch.py` with its `REPO` constant pointed at a pinned revision instead of
  `main`, then stock `mtp_pack.py`/`mtp_rt.py` with setup.py's exact argv, so setup.py skips its own fetch;
* Python packages: a hash-locked wheel set installed before setup.py, whose unpinned `pip install` then finds
  every requirement already satisfied;
* per-user settings: APPDATA / XDG_CONFIG_HOME point into the root, so `%APPDATA%\\Strata` is never touched.

Nothing here starts a server; `--no-start` is always passed.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from . import fetch as fetch_mod
from .common import IntegrityError, atomic_write_bytes, atomic_write_json, canonical_json, flag_pairs, read_json, \
    sha256_bytes, sha256_file, utc_now, verify_file
from .layout import Layout, host_platform

Log = Callable[[str], None]
SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
# The top-level keys every pinned setup.py (v0.1.27 through v0.1.36, including Unsloth Q4) writes. Any other key is a
# server option that changes serving - Strata-side agents, sampling, output fitting, GPU sharing, the AMD backend,
# and since v0.1.32 CORS, a request monitor, lazy loading and model aliases - so a release that starts writing one
# fails verification until the key is reviewed.
GENERATED_CONFIG_KEYS = frozenset({"args", "cwd", "exe", "gpu", "gpus_asked", "host", "lib_dirs", "log", "model_name",
                                   "port", "tokenizer"})


class InstallError(RuntimeError):
    pass


def repo_root(layout: Layout) -> Path:
    return layout.profile.path.resolve().parent.parent


def run(cmd: list[str], *, log: Log, cwd: Path | None = None, env: dict[str, str] | None = None,
        timeout: float | None = None, capture: bool = False) -> subprocess.CompletedProcess:
    """argv-only subprocess (never a shell string); stdin closed; the argv is logged, the environment is not."""
    log("$ " + " ".join(str(c) for c in cmd))
    proc = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, stdin=subprocess.DEVNULL, timeout=timeout,
                          capture_output=capture, text=capture, encoding="utf-8" if capture else None,
                          errors="replace" if capture else None)
    if proc.returncode != 0:
        tail = ((proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]) if capture else ""
        raise InstallError(f"command failed ({proc.returncode}): {cmd[0]} {cmd[1] if len(cmd) > 1 else ''}\n{tail}")
    return proc


def build_env(layout: Layout, extra: dict[str, str] | None = None) -> dict[str, str]:
    """The environment for stock setup/tools: the caller's minus secrets, per-user config redirected into the root."""
    env = {k: v for k, v in os.environ.items() if not any(m in k.upper() for m in SECRET_ENV_MARKERS)}
    layout.appdata.mkdir(parents=True, exist_ok=True)
    env["APPDATA"] = str(layout.appdata)
    env["XDG_CONFIG_HOME"] = str(layout.appdata)
    env["PYTHONUTF8"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env.pop("PYTHONPATH", None)
    env.pop("PIP_INDEX_URL", None)
    env.pop("PIP_EXTRA_INDEX_URL", None)
    if extra:
        env.update(extra)
    return env


# ------------------------------------------------------------------------------------------------ source
def checkout_strata(layout: Layout, *, log: Log) -> str:
    s = layout.profile.data["strata"]
    dest = layout.strata
    commit = s["commit"]
    git = ["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "-c", "advice.detachedHead=false"]
    if not (dest / ".git").is_dir():
        if dest.exists() and any(dest.iterdir()):
            raise InstallError(f"{dest} exists but is not a git checkout; refusing to overwrite it")
        dest.mkdir(parents=True, exist_ok=True)
        run([*git, "init", "-q", str(dest)], log=log)
        run([*git, "-C", str(dest), "config", "core.autocrlf", "false"], log=log)
        run([*git, "-C", str(dest), "fetch", "-q", "--depth", "1", s["repository"], commit], log=log, timeout=900)
        run([*git, "-C", str(dest), "checkout", "-q", "--detach", "FETCH_HEAD"], log=log)
    head = run(["git", "-C", str(dest), "rev-parse", "HEAD"], log=log, capture=True).stdout.strip()
    if head != commit:
        raise InstallError(f"Strata checkout is at {head}, the profile pins {commit}")
    dirty = run(["git", "-C", str(dest), "status", "--porcelain", "--untracked-files=no"], log=log,
                capture=True).stdout.strip()
    if dirty:
        raise InstallError(f"tracked Strata sources differ from {commit[:12]}:\n{dirty[:2000]}")
    return head


def setup_constants(layout: Layout) -> dict[str, object]:
    """PY_PACKAGES / CUDA_WHEELS / MIN_ENGINE / LLAMA_CPP_COMMIT read (not executed) from the pinned setup.py."""
    tree = ast.parse((layout.strata / "setup.py").read_text(encoding="utf-8"))
    out: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("PY_PACKAGES", "CUDA_WHEELS", "MIN_ENGINE", "LLAMA_CPP_COMMIT"):
                out[name] = ast.literal_eval(node.value)
    missing = {"PY_PACKAGES", "CUDA_WHEELS", "MIN_ENGINE", "LLAMA_CPP_COMMIT"} - out.keys()
    if missing:
        raise InstallError(f"pinned setup.py no longer defines {sorted(missing)}")
    return out


# ------------------------------------------------------------------------------------------------ python
def host_python() -> list[str]:
    """What stock START-HERE.bat would pick first on Windows (the py launcher, Python 3); python3 elsewhere."""
    return ["py", "-3"] if host_platform() == "windows-x64" else [sys.executable]


def ensure_venv(layout: Layout, *, log: Log) -> str:
    py = layout.venv_python
    if not py.exists():
        run([*host_python(), "-m", "venv", str(layout.strata / ".venv")], log=log, timeout=600)
    version = run([str(py), "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"], log=log,
                  capture=True).stdout.strip()
    return version


def python_lock_path(layout: Layout) -> Path:
    lock = layout.profile.data["strata"]["python_lock"]
    return repo_root(layout) / lock["path"]


def lock_python(layout: Layout, out: Path, *, log: Log) -> Path:
    """Maintainer step on the target host: resolve stock setup.py's packages once and freeze exact wheels. A pinned
    setup.py that ships requirements.txt (#214, Strata v0.1.31+) installs exactly those pins, so the lock resolves that
    file; an older one installs its unpinned PY_PACKAGES."""
    consts = setup_constants(layout)
    ensure_venv(layout, log=log)
    wheels = layout.wheels / "resolve"
    if wheels.exists():
        shutil.rmtree(wheels)
    wheels.mkdir(parents=True)
    pinned = layout.strata / "requirements.txt"
    packages = ["-r", str(pinned)] if pinned.is_file() else [*consts["PY_PACKAGES"]]  # type: ignore[misc]
    reqs = [*packages, *consts["CUDA_WHEELS"]]  # type: ignore[misc]
    run([str(layout.venv_python), "-m", "pip", "download", "--only-binary=:all:", "--dest", str(wheels), *reqs],
        log=log, env=build_env(layout), timeout=3600)
    shown = ["-r", "requirements.txt"] if pinned.is_file() else packages      # no host path in a committed lock
    lines = ["# Hash-locked wheels for stock Strata setup.py's packages + CUDA_WHEELS.",
             f"# Resolved {utc_now()} with `omp_strata.py lock-python` for this interpreter/platform only.",
             f"# Requested: {' '.join([*shown, *consts['CUDA_WHEELS']])}"]  # type: ignore[misc]
    for whl in sorted(wheels.glob("*.whl")):
        name, version = whl.name.split("-")[:2]
        lines.append(f"{name.replace('_', '-').lower()}=={version} --hash=sha256:{sha256_file(whl)}")
    atomic_write_bytes(out, ("\n".join(lines) + "\n").encode("utf-8"))
    return out


def install_python(layout: Layout, *, log: Log) -> dict[str, str]:
    lock = python_lock_path(layout)
    pin = layout.profile.data["strata"]["python_lock"]
    if not lock.is_file():
        raise InstallError(f"missing Python lock {pin['path']}; run lock-python on the target host first")
    if sha256_file(lock) != pin["sha256"]:
        raise IntegrityError(f"{pin['path']} does not match the profile's python_lock.sha256")
    version = ensure_venv(layout, log=log)
    if not version.startswith(pin["python"] + ".") and version != pin["python"]:
        raise InstallError(f"venv Python {version} does not match the lock's Python {pin['python']}")
    wheels = layout.wheels / "locked"
    wheels.mkdir(parents=True, exist_ok=True)
    env = build_env(layout)
    run([str(layout.venv_python), "-m", "pip", "download", "--require-hashes", "--only-binary=:all:", "--no-deps",
         "--dest", str(wheels), "-r", str(lock)], log=log, env=env, timeout=3600)
    run([str(layout.venv_python), "-m", "pip", "install", "--require-hashes", "--no-index", "--no-deps",
         "--find-links", str(wheels), "-r", str(lock)], log=log, env=env, timeout=3600)
    freeze = run([str(layout.venv_python), "-m", "pip", "freeze", "--all"], log=log, env=env,
                 capture=True).stdout
    return {"python": version, "lock_sha256": pin["sha256"], "pip_freeze_sha256": sha256_bytes(freeze.encode())}


def dev_python(layout: Layout, *, log: Log) -> Path:
    """Host-free tests only: the pinned source's Python env - setup.py's PY_PACKAGES at the lock's versions, in the
    lock's Python, without the CUDA wheels (GPU hosts only). The lock hashes win_amd64 wheels, so versions are pinned
    here but hashes are not checked; the qualified path stays install_python()."""
    pin = layout.profile.data["strata"]["python_lock"]
    consts = setup_constants(layout)
    packages, wheels = consts["PY_PACKAGES"], consts["CUDA_WHEELS"]
    if not (isinstance(packages, list) and isinstance(wheels, list)):
        raise InstallError("pinned setup.py PY_PACKAGES / CUDA_WHEELS are not lists")
    cuda = {str(wheel).split("==")[0] for wheel in wheels}
    pins = [line.split()[0] for line in python_lock_path(layout).read_text(encoding="utf-8").splitlines()
            if "==" in line and not line.startswith("#")]
    py = layout.dev_python
    venv = py.parent.parent
    if not py.exists():
        if host_platform() == "windows-x64":
            exe = ["py", f"-{pin['python']}"]
        else:
            found = shutil.which(f"python{pin['python']}")
            if found is None:
                raise InstallError(f"Python {pin['python']} (the lock's interpreter) is not on PATH")
            exe = [found]
        run([*exe, "-m", "venv", str(venv)], log=log, timeout=600)
    version = run([str(py), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], log=log,
                  capture=True).stdout.strip()
    if version != pin["python"]:
        raise InstallError(f"{venv} is Python {version}, the lock's is {pin['python']}; delete it to recreate it")
    constraints = venv / "lock-constraints.txt"
    atomic_write_bytes(constraints, "".join(p + "\n" for p in pins if p.split("==")[0] not in cuda).encode("utf-8"))
    run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-c", str(constraints),
         *map(str, packages)], log=log, env=build_env(layout), timeout=1800)
    return py


# ------------------------------------------------------------------------------------------------ llama.cpp
def stage_llama(layout: Layout, *, log: Log) -> None:
    consts = setup_constants(layout)
    art = layout.profile.data["strata"]["artifacts"]["llama_cpp_archive"]
    if str(consts["LLAMA_CPP_COMMIT"]) not in art["url"]:
        raise InstallError("the pinned llama.cpp archive is not the commit stock setup.py expects")
    extracted = layout.strata / "third_party" / "llama.cpp"
    if not ((extracted / "ggml" / "CMakeLists.txt").exists() and (extracted / "gguf-py").is_dir()):
        verify_file(layout.llama_archive, art["bytes"], art["sha256"], source=art["sha256_source"], log=log)
        target = layout.strata / "third_party" / f"llama.cpp-{str(consts['LLAMA_CPP_COMMIT'])[:7]}.zip"
        shutil.copyfile(layout.llama_archive, target)
        verify_file(target, art["bytes"], art["sha256"], source="copy of the verified archive", deep=True, log=log)
        target.with_name(target.name + ".done").write_text("omp-strata staged a verified archive", encoding="utf-8")
        run([str(layout.venv_python), "-c", "import setup; print(setup.get_llama_cpp())"], cwd=layout.strata,
            env=build_env(layout), log=log, timeout=900)
    if not (extracted / "gguf-py").is_dir():
        raise InstallError("stock get_llama_cpp() did not produce third_party/llama.cpp/gguf-py")


# ------------------------------------------------------------------------------------------------ MTP layer
MTP_FETCH_PINNED = """
import sys
sys.path.insert(0, sys.argv[1])
import mtp_fetch
mtp_fetch.REPO = sys.argv[2]
sys.argv = ["mtp_fetch.py", "fetch", "--out", sys.argv[3]]
mtp_fetch.main()
"""


def mtp_manifest_sha256(mtp_dir: Path) -> str:
    rows = read_json(mtp_dir / "mtp-manifest.json")
    return sha256_bytes(canonical_json(sorted((r["name"], r["bytes"], r["sha256"]) for r in rows)))


def mtp_pinned(layout: Layout, *, log: Log) -> str:
    src = layout.profile.data["model"]["mtp_source"]
    mtp = layout.data / "mtp"
    rt = mtp / "rt"
    env = build_env(layout, {"STRATA_GGUF_PY": str(layout.strata / "third_party" / "llama.cpp" / "gguf-py")})
    tools = layout.strata / "tools"
    if not (rt / "experts.bin").exists():
        mtp.mkdir(parents=True, exist_ok=True)
        repo = f"https://huggingface.co/{src['repository']}/resolve/{src['revision']}/"
        run([str(layout.venv_python), "-c", MTP_FETCH_PINNED, str(tools), repo, str(mtp)], env=env, log=log,
            timeout=6 * 3600)
        digest = mtp_manifest_sha256(mtp)
        want = src.get("tensor_manifest_sha256")
        if want and digest != want:
            raise IntegrityError(f"MTP tensors {digest} differ from the pinned {want}")
        # setup.py step 6, verbatim argv
        run([str(layout.venv_python), str(tools / "mtp_pack.py"), "--src", str(mtp), "--experts", "q2_0",
             "--out", str(mtp / "mtp-q2_0.gguf")], env=env, log=log, timeout=3600)
        run([str(layout.venv_python), str(tools / "mtp_rt.py"), "--gguf", str(mtp / "mtp-q2_0.gguf"),
             "--out", str(rt)], env=env, log=log, timeout=3600)
    digest = mtp_manifest_sha256(mtp)
    want = src.get("tensor_manifest_sha256")
    if want and digest != want:
        raise IntegrityError(f"MTP tensors {digest} differ from the pinned {want}")
    return digest


# ------------------------------------------------------------------------------------------------ setup.py
def sibling_installs(layout: Layout) -> list[Path]:
    """What stock setup.py's other_installs() would scan and possibly move files out of: must be empty."""
    found = []
    root = layout.strata.resolve()
    for base in dict.fromkeys((root.parent, root.parent.parent)):
        if not base.is_dir():
            continue
        for d in base.iterdir():
            if d.is_dir() and d.name.lower().startswith("strata") and d.resolve() != root:
                found.append(d)
    settings = layout.appdata / "Strata" / "settings.json"
    if host_platform() != "windows-x64":
        settings = layout.appdata / "strata" / "settings.json"
    if settings.is_file():
        for p in read_json(settings).get("installs", []):
            if Path(p).resolve() != root:
                found.append(Path(p))
    return found


def setup_argv(layout: Layout) -> list[str]:
    s = layout.profile.data["strata"]["setup_args"]
    srv = layout.profile.data["server"]
    # Budget models use setup's automatic host/KV-derived budget, checked against the plan afterwards.
    # The unsloth family also selects stock iq_pack.py --compat-bf16; never prebuild a different pack here.
    return [str(layout.venv_python), "setup.py",
            "--family", s["family"], "--model", s["model"], "--context", str(s["context"]), "--kv", s["kv"],
            "--vision", s["vision"], "--experimental-speed-projection", s["experimental_speed_projection"],
            "--low-ram", s["low_ram"], "--gpu", str(s["gpu"]),
            "--data-dir", str(layout.data), "--gguf-dir", str(layout.models_dir),
            "--prebuilt", str(layout.engine_dir), "--port", str(srv["port"]), "--host", srv["listen_host"],
            "--yes", "--no-start"]


def run_setup(layout: Layout, *, log: Log) -> None:
    others = sibling_installs(layout)
    if others:
        raise InstallError("stock setup.py would adopt/move files of other Strata folders: "
                           + ", ".join(p.name for p in others))
    run(setup_argv(layout), cwd=layout.strata, env=build_env(layout), log=log, timeout=6 * 3600)


# The end of stock setup.py's calibrate_config() without its measurement: the profile's pinned settings applied by
# stock calibrate.apply (each calibrated flag reset, then the kept value appended) and written by stock write_config.
APPLY_CALIBRATION = """
import json, sys
from pathlib import Path
sys.path.insert(0, "tools")
import calibrate, setup
path = Path(sys.argv[1])
cfg = json.loads(path.read_text(encoding="utf-8-sig"))
cfg["args"] = calibrate.apply(cfg["args"], json.loads(sys.argv[2]))
setup.write_config(path, cfg)
"""


def apply_calibration(layout: Layout, *, log: Log) -> None:
    cal = layout.profile.data["strata"].get("calibration")
    if cal is not None:
        run([str(layout.venv_python), "-c", APPLY_CALIBRATION, str(layout.strata_config), json.dumps(cal["settings"])],
            cwd=layout.strata, env=build_env(layout), log=log, timeout=600)



# ------------------------------------------------------------------------------------------------ verification
def verify_generated(layout: Layout) -> dict:
    """The config stock setup.py wrote must be exactly the profile's choices, pointing only inside the root."""
    p = layout.profile.data
    cfg_path = layout.strata_config
    if not cfg_path.is_file():
        raise InstallError(f"setup.py did not write {cfg_path.name}")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    problems = []
    args = cfg.get("args", [])
    pairs = flag_pairs(args)
    want = flag_pairs(p["strata"]["expected_engine_flags"])
    budget_model = "--resident-budget-gib" in want
    for flag, value in want.items():
        if pairs.get(flag) != value:
            problems.append(f"engine flag {flag}: {pairs.get(flag)!r} != expected {value!r}")
    for flag in p["strata"]["forbidden_engine_flags"]:
        if flag in pairs:
            problems.append(f"forbidden engine flag {flag} present")
    path_flags = {"--pack", "--native", "--expert-profile", "--mtp"}
    if not budget_model:  # Four-shard Unsloth finds the PLE table itself; setup writes no --ple-gguf.
        path_flags.add("--ple-gguf")
    extra = set(pairs) - set(want) - path_flags
    if extra:
        problems.append(f"unexpected engine flags {sorted(extra)}")
    root = layout.root.resolve()
    for flag in path_flags - {"--expert-profile"}:
        v = pairs.get(flag)
        if not v or not Path(v).resolve().is_relative_to(root):
            problems.append(f"{flag} must point inside the integration root")
    prof = pairs.get("--expert-profile", "")
    if not prof or not Path(prof).resolve().is_relative_to(layout.strata.resolve() / "data"):
        problems.append("--expert-profile must be the pinned source's data/ file")
    shard1 = layout.model_file(p["model"]["files"][0])
    if Path(pairs.get("--native", "")).resolve() != shard1.resolve():
        problems.append("--native is not the pinned first shard")
    if budget_model and pairs.get("--pack") and (Path(pairs["--pack"]) / "experts.bin").exists():
        problems.append("budget model pack must not contain experts.bin; experts are mapped from the pinned GGUF")
    if cfg.get("model_name") != p["strata"]["model_name"]:
        problems.append(f"model_name {cfg.get('model_name')!r} != {p['strata']['model_name']!r}")
    if Path(cfg.get("exe", "")).resolve() != (layout.strata / "engine" / ("strata.exe" if host_platform() ==
                                                                         "windows-x64" else "strata")).resolve():
        problems.append("exe is not the staged stock engine")
    extra_keys = sorted(set(cfg) - GENERATED_CONFIG_KEYS)
    if extra_keys:
        problems.append(f"unexpected config keys {extra_keys}")
    if cfg.get("host") != p["server"]["listen_host"]:
        problems.append("config host is not the loopback listener")
    if problems:
        raise InstallError("generated Strata config rejected:\n  " + "\n  ".join(problems))
    return cfg


def freeze_shared_settings(layout: Layout) -> None:
    path = layout.shared_settings
    if path.exists():
        data = read_json(path)
        if data != {}:
            raise InstallError(f"{path.name} holds non-default shared settings: {sorted(data)}")
        return
    atomic_write_bytes(path, b"{}\n")


def engine_build(layout: Layout) -> dict:
    meta = read_json(layout.strata / "engine" / "BUILD.json")
    want = layout.profile.data["strata"]["engine_version"]
    if meta.get("version") != want or meta.get("source") != "release":
        raise InstallError(f"engine BUILD.json {meta.get('version')}/{meta.get('source')} is not release {want}")
    return meta


def _hash_tree(base: Path, root: Path) -> dict[str, dict]:
    out = {}
    for f in sorted(p for p in base.rglob("*") if p.is_file() and not p.name.endswith(".verified.json")):
        out[f.resolve().relative_to(root).as_posix()] = {"bytes": f.stat().st_size, "sha256": sha256_file(f)}
    return out


def runtime_identity(layout: Layout, cfg: dict) -> dict:
    """Hashes of every nonsecret runtime input, keyed by path relative to the root.

    The normalized config and every file entry are the same in any root. The raw config file's hash embeds the
    root's absolute paths (it is the actual file the runtime reads), so the combined identity is root-specific.
    """
    root = layout.root.resolve()
    pairs = flag_pairs(cfg["args"])
    files: dict[str, dict] = {}
    for f in (layout.strata / "engine").iterdir():
        if f.is_file():
            files[f.resolve().relative_to(root).as_posix()] = {"bytes": f.stat().st_size, "sha256": sha256_file(f)}
    files.update(_hash_tree(Path(pairs["--pack"]), root))
    files.update(_hash_tree(Path(pairs["--mtp"]), root))
    for entry in layout.profile.data["model"]["files"]:
        f = layout.model_file(entry)
        files[f.resolve().relative_to(root).as_posix()] = {"bytes": entry["bytes"], "sha256": entry["sha256"]}
    cfg_norm = json.loads(json.dumps(cfg).replace(json.dumps(str(root))[1:-1], "<root>"))
    return {"files": files, "config": cfg_norm, "config_file_sha256": sha256_file(layout.strata_config),
            "shared_settings_sha256": sha256_file(layout.shared_settings)}


def install(layout: Layout, *, log: Log) -> dict:
    layout.state.mkdir(parents=True, exist_ok=True)
    fetch_mod.fetch(layout, log=log)
    commit = checkout_strata(layout, log=log)
    py = install_python(layout, log=log)
    stage_llama(layout, log=log)
    mtp_digest = mtp_pinned(layout, log=log)
    run_setup(layout, log=log)
    apply_calibration(layout, log=log)
    commit_after = checkout_strata(layout, log=log)          # setup.py must not have edited tracked sources
    cfg = verify_generated(layout)
    freeze_shared_settings(layout)
    build = engine_build(layout)
    ident = runtime_identity(layout, cfg)
    record = {
        "schema_version": 1,
        "profile_id": layout.profile.id,
        "profile_fingerprint": layout.profile.fingerprint,
        "installed_utc": utc_now(),
        "strata_commit": commit_after,
        "engine_build": build,
        "python": py,
        "mtp_tensor_manifest_sha256": mtp_digest,
        "runtime_identity_sha256": sha256_bytes(canonical_json(ident)),
        "identity": ident,
    }
    assert commit == commit_after
    atomic_write_json(layout.install_record, record)
    return record
