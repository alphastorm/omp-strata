"""Rollback argv, stock cwd/env and portable installed identity, captured from main 75d01fa."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

from omp_strata import dflash2, dsv41, install, nvfp4
from omp_strata.common import canonical_json, release_version, sha256_bytes, sha256_file
from omp_strata.layout import Layout
from omp_strata.profile import load
from tests.unit.test_nvfp4 import prepared_fixture

REPO = Path(__file__).resolve().parents[2]
REFERENCE = REPO / "tests/fixtures/stock_call_plans_75d01fa.json"


def rollback_plan(profile):
    with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
        root = Path(tmp).resolve()
        layout = Layout(root, profile)
        deepseek = dsv41.is_pinned(profile.data)
        converted = nvfp4.is_local(profile.data["model"])
        sources = install.runtime_sources(profile)
        engine = layout.dsv41_engine_dir if deepseek else layout.strata / "engine"
        for file in (engine / "strata.exe", layout.strata / "setup.py",
                     *(layout.strata / rel for rel in sources), layout.data / "pack/fixture", layout.data / "mtp/fixture"):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(file.relative_to(root).as_posix().encode())
        if converted:
            prepared_fixture(layout)
        if dflash2.is_pinned(profile.data):
            layout.dflash2_dir.mkdir(parents=True)
            (layout.dflash2_dir / "fixture").write_bytes(b"drafter")
        cfg = {"args": ["--pack", str(layout.data / "pack"), "--mtp", str(layout.data / "mtp")]}
        layout.strata_config.write_bytes(canonical_json(cfg))
        layout.shared_settings.write_bytes(b"{}")
        identity = install.runtime_identity(layout, cfg)
        if identity.pop("config_file_sha256") != sha256_file(layout.strata_config):
            raise AssertionError("installed config digest no longer binds the raw file")
        identity["config"]["args"] = [arg.replace("\\", "/") for arg in identity["config"]["args"]]
        calls = []

        def record(argv, *, cwd=None, env=None, **_):
            def portable(value):
                value = str(value)
                return "<root>/" + Path(value).relative_to(root).as_posix() if value.startswith(str(root)) else value
            calls.append(([portable(a) for a in argv], portable(cwd) if cwd else None, sorted(env)))

        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=layout.strata / ".venv/Scripts/python.exe"), \
                patch.object(install, "run", side_effect=record), patch.object(install, "host_platform", return_value="windows-x64"):
            log = lambda _: None
            if not (deepseek or converted):
                with patch.object(install, "mtp_manifest_sha256", return_value=profile.data["model"]["mtp_source"].get("tensor_manifest_sha256")):
                    install.mtp_pinned(layout, log=log)
            install.run_setup(layout, log=log)
            if deepseek:
                dsv41.apply_user_args(layout, run=record, env=install.build_env(layout), log=log)
            for apply in (install.apply_calibration, install.apply_stock_tips, install.apply_pipeline_windows,
                          install.apply_ple_io, install.apply_batch_mtp, install.apply_trim_stage_weights,
                          install.apply_kv_grow, install.apply_engine_env, install.apply_server_choices,
                          install.apply_drafting_args):
                apply(layout, log=log)
        return sha256_bytes(canonical_json([calls, sources, identity]))


class RollbackContract(unittest.TestCase):
    def test_stock_call_plans_and_runtime_identity_for_all_flat_profiles(self):
        expected = json.loads(REFERENCE.read_text())
        covered = set()
        for file in sorted((REPO / "profiles").glob("*.json")):
            profile = load(file)
            if release_version(profile.data["strata"]["tag"]) >= (0, 2, 16):
                continue
            covered.add(file.stem)
            with self.subTest(profile=file.stem):
                self.assertEqual(expected[file.stem], rollback_plan(profile))
        self.assertEqual(set(expected), covered)
