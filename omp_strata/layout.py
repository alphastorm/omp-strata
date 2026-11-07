"""The dedicated integration root: every file this tool creates lives under one directory.

    <root>/downloads/omp/<tag>/<asset>            pinned stock OMP binary
    <root>/downloads/strata/<tag>/<asset>         pinned stock engine archive (setup.py --prebuilt folder)
    <root>/downloads/llama.cpp/<zip>              llama.cpp source archive at setup.py's pinned commit
    <root>/models/<variant>-<quant>/<shard>.gguf  pinned model shards (setup.py --gguf-dir)
    <root>/runtime/strata/                        stock Strata checkout at the pinned commit (+ setup outputs); two
                                                  levels below the root, so setup.py's sibling-install scan
                                                  (ROOT.parent, ROOT.parent.parent) never leaves the root
    <root>/data/                                  setup.py --data-dir (packs/, mtp/)
    <root>/appdata/                               APPDATA/XDG_CONFIG_HOME for setup.py's per-user settings
    <root>/localappdata/                          LOCALAPPDATA for engine 0.1.57+ process records
    <root>/state/                                 install record, run record, lock
    <root>/state/strata-runtime/                  engine 0.1.57+ activity lease and its private ACL
    <root>/logs/                                  server stdout/stderr
    <root>/omp/home/                              isolated HOME/USERPROFILE for stock OMP
    <root>/work/                                  disposable fixture workspaces
    <root>/dev/strata-venv/                       host-free test env for the pinned Strata frontend (`dev-env`), never
                                                  the install's hash-locked runtime/strata/.venv
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .profile import Profile


def default_root() -> Path:
    env = os.environ.get("OMP_STRATA_ROOT")
    if env:
        return Path(env)
    return Path.home() / "omp-strata"


def host_platform() -> str:
    if sys.platform == "win32":
        return "windows-x64"
    if sys.platform == "darwin":
        return "darwin-arm64"
    return "linux-x64"


@dataclass(frozen=True)
class Layout:
    root: Path
    profile: Profile

    @property
    def downloads(self) -> Path:
        return self.root / "downloads"

    def omp_binary(self, platform: str | None = None) -> Path:
        plat = platform or host_platform()
        art = self.profile.omp_artifact(plat)
        return self.downloads / "omp" / self.profile.data["omp"]["tag"] / art["file"]

    @property
    def engine_dir(self) -> Path:
        return self.downloads / "strata" / self.profile.data["strata"]["tag"]

    @property
    def engine_archive(self) -> Path:
        return self.engine_dir / self.profile.data["strata"]["artifacts"]["engine_archive"]["file"]

    @property
    def dsv41_package(self) -> Path:
        return self.engine_dir / self.profile.data["strata"]["artifacts"]["dsv41_package"]["file"]

    @property
    def dsv41_engine_dir(self) -> Path:
        pin = self.profile.data["strata"]["dsv41_component"]
        return self.strata / "engine-dsv41" / f"{pin['version']}-{pin['platform']}-{pin['backend']}-{pin['variant']}"

    @property
    def llama_archive(self) -> Path:
        return self.downloads / "llama.cpp" / self.profile.data["strata"]["artifacts"]["llama_cpp_archive"]["file"]

    @property
    def models_dir(self) -> Path:
        m = self.profile.data["model"]
        if m.get("format") == "modelopt-fp4-local":
            return self.root / "models"
        return self.root / "models" / f"{m['variant']}-{m['quantization']}"

    def model_file(self, entry: dict) -> Path:
        if self.profile.data["model"].get("format") == "modelopt-fp4-local":
            from .nvfp4 import checkpoint_dir
            return checkpoint_dir(self) / entry["path"]
        return self.models_dir / entry["path"].rsplit("/", 1)[-1]

    def dflash2_file(self, entry: dict) -> Path:
        source = self.profile.data["model"]["dflash2_source"]
        return self.downloads / "dflash2" / source["revision"] / entry["path"]

    @property
    def dflash2_tuned_download(self) -> Path:
        tuned = self.profile.data["model"]["dflash2_source"]["tuned"]
        return self.downloads / "dflash2" / tuned["tag"] / tuned["file"]

    @property
    def dflash2_dir(self) -> Path:
        from .dflash2 import FOLDER
        # Stock drafting.data_dir_of(--mtp <data>/mtp/rt) returns <data>.
        return self.data / FOLDER

    @property
    def strata(self) -> Path:
        return self.root / "runtime" / "strata"

    @property
    def venv_python(self) -> Path:
        if host_platform() == "windows-x64":
            return self.strata / ".venv" / "Scripts" / "python.exe"
        return self.strata / ".venv" / "bin" / "python"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def appdata(self) -> Path:
        return self.root / "appdata"

    @property
    def localappdata(self) -> Path:
        return self.root / "localappdata"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def strata_runtime(self) -> Path:
        return self.state / "strata-runtime"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def omp_home(self) -> Path:
        return self.root / "omp" / "home"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def install_record(self) -> Path:
        return self.state / "install-record.json"

    @property
    def run_record(self) -> Path:
        return self.state / "run.json"

    @property
    def lock_file(self) -> Path:
        return self.state / "lifecycle.lock"

    @property
    def strata_config(self) -> Path:
        s = self.profile.data["strata"]["setup_args"]
        tag = {"qwen": "", "swift": "swift-", "coder": "coder-", "unsloth": "unsloth-",
               "nvfp4": "nvfp4-", "deepseek41": "deepseek-v4.1-flash-"}[s["family"]] + s["model"]
        return self.strata / f"strata-{tag.lower()}.json"

    @property
    def shared_settings(self) -> Path:
        """Stock server.py: str(Path(config).with_suffix("")) + ".shared-settings.json"."""
        return self.strata_config.with_name(self.strata_config.stem + ".shared-settings.json")

    @property
    def key_file(self) -> Path:
        return self.state / "strata-api-key"

    @property
    def wheels(self) -> Path:
        return self.downloads / "wheels"

    @property
    def dev_python(self) -> Path:
        venv = self.root / "dev" / "strata-venv"
        return venv / "Scripts" / "python.exe" if host_platform() == "windows-x64" else venv / "bin" / "python"
