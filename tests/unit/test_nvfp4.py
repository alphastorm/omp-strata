"""Pinned stock planning and local artifact boundaries; no weights, network or GPU."""
import copy
import json
from pathlib import Path, PureWindowsPath
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from omp_strata import cli, fetch, install, lifecycle, nvfp4
from omp_strata.common import IntegrityError, atomic_write_json, canonical_json, sha256_bytes
from omp_strata.layout import Layout
from omp_strata.profile import Profile, load, validate
from scripts import upstream_watch as watch

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "profiles/win11-rtxpro6000-nvfp4-qad-262k-slots4-strata0.2.3-omp18.12.6.json"
CHAMPION = ROOT / "profiles/win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6.json"
SOURCE = (ROOT / "tests/fixtures/strata_0_2_3_plan.py").read_text() + "\n" + (ROOT / "tests/fixtures/strata_0_2_3_nvfp4.py").read_text()
PLAN = {"family": "nvfp4", "model": "NVFP4-QAD", "context": 262144, "ram": 191.69,
        "vram": 97000 / 1024, "cpu_cores": (8, 16), "parallel": 4, "tips": {"--prefill": "auto:32768"},
        "engine_version": (0, 1, 48)}


class NVFP4Planning(unittest.TestCase):
    def test_experiment_freezes_new_artifact_boundary_code(self):
        from scripts.experiment_loop import HARNESS_FILES
        self.assertTrue({"omp_strata/nvfp4.py", "omp_strata/fetch.py", "omp_strata/layout.py",
                         "omp_strata/cli.py"} <= set(HARNESS_FILES))

    def test_single_pro_challenger_is_admitted_and_other_nvfp4_paths_refuse(self):
        plan = watch.stock_plan(SOURCE, **PLAN)
        profile = load(CANDIDATE)
        self.assertEqual(profile.data["strata"]["setup_args"], plan["setup_args"])
        self.assertEqual(profile.data["strata"]["expected_engine_flags"],
                         watch.tipped_flags(plan["expected_engine_flags"], plan["stock_tips"]))
        self.assertEqual(profile.data["strata"]["model_name"], plan["model_name"])
        self.assertEqual(29, len(plan["model_files"]))
        self.assertEqual(nvfp4.REVISION, plan["checkpoint"]["revision"])
        self.assertGreaterEqual(plan["thresholds"]["fresh_disk_gb"], 220)
        for changes in ({"model": "NVFP4"}, {"context": 131072}, {"vram": 32}, {"parallel": 2}):
            with self.subTest(changes=changes), self.assertRaises(watch.Incomplete):
                watch.stock_plan(SOURCE, **(PLAN | changes))

    def test_mutated_checkpoint_or_config_assembly_refuses(self):
        for before, after in ((nvfp4.REVISION, "a" * 40), ('"--native-dense-gguf"', '"--foreign-dense-gguf"')):
            with self.subTest(before=before), self.assertRaises(watch.Incomplete):
                watch.stock_plan(SOURCE.replace(before, after), **PLAN)

    def test_profile_pins_manifest_recipe_files_host_and_input_format(self):
        data = load(CANDIDATE).data
        self.assertFalse(validate(data))
        for mutate in (lambda p: p["model"].pop("format"),
                       lambda p: p["model"]["conversion"].update(manifest_sha256="a" * 64),
                       lambda p: p["model"]["files"][0].update(path="../foreign"),
                       lambda p: p["model"]["files"][0].update(bytes=1),
                       lambda p: p["host"].update(gpu_model="NVIDIA GeForce RTX 5090")):
            changed = copy.deepcopy(data)
            mutate(changed)
            self.assertTrue(validate(changed))
        self.assertNotIn("format", load(CHAMPION).data["model"])


class NVFP4Artifacts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.layout = Layout(Path(self.temp.name) / "challenger", load(CANDIDATE))

    def test_nested_checkpoint_and_explicit_ready_paths(self):
        model = self.layout.profile.data["model"]
        shard = next(row for row in model["files"] if row["path"].startswith("tensors/"))
        self.assertEqual(nvfp4.checkpoint_dir(self.layout) / shard["path"], self.layout.model_file(shard))
        paths = nvfp4.engine_paths(self.layout)
        self.assertEqual(paths["--native"], paths["--native-dense-gguf"])
        self.assertTrue(paths["--pack"].is_relative_to(self.layout.root))
        argv = install.setup_argv(self.layout)
        self.assertIn("--models-dir", argv)
        self.assertNotIn("--gguf-dir", argv)
        self.assertIn("--no-start", argv)
        self.assertEqual("strata-nvfp4-nvfp4-qad.json", self.layout.strata_config.name)
        champion = Layout(self.layout.root, load(CHAMPION))
        self.assertIn("--gguf-dir", install.setup_argv(champion))
        self.assertNotIn("--models-dir", install.setup_argv(champion))

    def test_readiness_accepts_prepared_native_dense_but_not_checkpoint_inputs(self):
        paths = nvfp4.engine_paths(self.layout)
        for path, ready in (
                (paths["--native"], True),
                (paths["--native"].parent / "unused" / ".." / "dense.gguf", True),
                (self.layout.model_file(self.layout.profile.data["model"]["files"][0]), False),
                (nvfp4.checkpoint_dir(self.layout) / "tensors/model-00001-of-00021.safetensors", False),
                (paths["--ple-gguf"], False)):
            with self.subTest(path=path):
                self.assertEqual(ready, self.readiness(self.layout, path)["ready"])

    def test_readiness_preserves_gguf_first_shard_checks(self):
        layout = Layout(self.layout.root, load(CHAMPION))
        first = layout.model_file(layout.profile.data["model"]["files"][0])
        for path, ready in ((first, True), (first.with_name("foreign.gguf"), False),
                            (nvfp4.engine_paths(self.layout)["--native"], False)):
            with self.subTest(path=path):
                self.assertEqual(ready, self.readiness(layout, path)["ready"])

    def readiness(self, layout, model_path):
        data = layout.profile.data
        context = data["strata"]["setup_args"]["context"]

        def response(url, *, key=None):
            if url.endswith("/health"):
                return 200, {"api_key": True, "model": data["strata"]["model_name"],
                             "max_context": context, "loaded": True}
            if url.endswith("/v1/models"):
                return (200, {"data": [{"id": data["strata"]["model_name"]}]}) if key else (401, {})
            if url.endswith("/props"):
                return 200, {"default_generation_settings": {"n_ctx": context}, "model_path": str(model_path)}
            if url.endswith("/settings"):
                return 200, {"shared": False, "defaults": {}}
            self.fail("unexpected readiness endpoint")

        with patch.object(lifecycle, "http_json", side_effect=response):
            return lifecycle.runtime_checks(layout, "fixture-key")

    def test_disk_preflight_refuses_absent_self_parenting_drive_and_share_anchors(self):
        for name in ("D:/challenger", "//fixture/share/challenger"):
            visits = []

            class MissingPath(PureWindowsPath):
                def exists(self):
                    visits.append(str(self))
                    if len(visits) > 4:
                        raise AssertionError("ancestor traversal revisited a missing filesystem anchor")
                    return False

            layout = SimpleNamespace(root=MissingPath(name), profile=self.layout.profile)
            with self.subTest(root=name), patch.object(nvfp4.shutil, "disk_usage") as usage, \
                    self.assertRaisesRegex(IntegrityError, "NVFP4 staging refused.*filesystem anchor"):
                nvfp4.disk_preflight(layout)
            usage.assert_not_called()
            self.assertEqual(len(visits), len(set(visits)))
        self.assertFalse(self.layout.root.exists())

    def test_disk_floor_refuses_before_directory_or_download_even_if_space_check_disabled(self):
        artifact = sum(row["bytes"] for row in self.layout.profile.data["model"]["files"])
        with patch.object(nvfp4.shutil, "disk_usage", return_value=SimpleNamespace(free=2 * artifact - 1)), \
                patch.object(fetch, "download_verified") as download:
            with self.assertRaisesRegex(IntegrityError, "at least 2x checkpoint"):
                fetch.fetch(self.layout, platform="windows-x64", only={"model"}, check_space=False)
            download.assert_not_called()
        self.assertFalse(self.layout.root.exists())
        floor = max(2 * artifact, artifact + nvfp4.PREPARATION_BYTES)
        with patch.object(nvfp4.shutil, "disk_usage", return_value=SimpleNamespace(free=floor)):
            self.assertEqual(floor, nvfp4.disk_preflight(self.layout)["required_free_bytes"])
        self.assertFalse(self.layout.root.exists())

    def test_install_disk_refusal_creates_neither_root_nor_state_and_never_downloads(self):
        with patch.object(fetch, "host_platform", return_value="windows-x64"), \
                patch.object(nvfp4.shutil, "disk_usage", return_value=SimpleNamespace(free=0)), \
                patch.object(fetch, "download_verified") as download, \
                self.assertRaisesRegex(IntegrityError, "NVFP4 staging refused"):
            install.install(self.layout, log=lambda _line: None)
        download.assert_not_called()
        self.assertFalse(self.layout.root.exists())

    def test_install_cli_checks_disk_before_its_root_lock_creates_directories(self):
        args = SimpleNamespace(profile=str(CANDIDATE), root=str(self.layout.root))
        for existing_root in (False, True):
            with self.subTest(existing_root=existing_root):
                if existing_root:
                    self.layout.root.mkdir(exist_ok=True)
                with patch.object(fetch, "host_platform", return_value="windows-x64"), \
                        patch.object(nvfp4.shutil, "disk_usage", return_value=SimpleNamespace(free=0)), \
                        patch.object(cli.lifecycle, "FileLock", wraps=cli.lifecycle.FileLock) as lock, \
                        patch.object(fetch, "download_verified") as download, \
                        self.assertRaisesRegex(IntegrityError, "NVFP4 staging refused"):
                    cli.cmd_install(args)
                lock.assert_not_called()
                download.assert_not_called()
                self.assertEqual(self.layout.root.exists(), existing_root)
                self.assertFalse(self.layout.state.exists())

    def test_conversion_receipt_binds_all_generated_runtime_outputs(self):
        base = nvfp4.prepared_dir(self.layout)
        required = ["dense.gguf", "ple-nvfp4.gguf", "pack/experts.bin", "pack/dense.bin", "pack/index.txt",
                    "pack/native_experts.txt", "pack/tokenizer/vocab.json", "mtp/rt/experts.bin",
                    "mtp/rt/draft_vocab.bin"]
        for name in required:
            path = base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        receipt = {"input_fingerprint": sha256_bytes(canonical_json(self.layout.profile.data["model"])),
                   "recipe_commit": nvfp4.RECIPE_COMMIT, "files": nvfp4.output_manifest(self.layout)}
        atomic_write_json(base / "conversion-receipt.json", receipt)
        self.assertEqual(receipt, nvfp4.verify_prepared(self.layout))
        (base / "ple-nvfp4.gguf").write_bytes(b"changed after conversion")
        with self.assertRaisesRegex(IntegrityError, "drifted"):
            nvfp4.verify_prepared(self.layout)
        (base / "mtp/rt/experts.bin").unlink()
        with self.assertRaisesRegex(IntegrityError, "required runtime outputs"):
            nvfp4.output_manifest(self.layout)

    def test_prepare_seals_the_stock_draft_vocabulary_before_setup_reuses_it(self):
        source = self.layout.strata / "data/draft_vocab.bin"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"pinned stock cjk draft vocabulary")
        base = nvfp4.prepared_dir(self.layout)

        def convert(*_args, **_kwargs):
            for name in ("dense.gguf", "ple-nvfp4.gguf", "pack/experts.bin", "pack/dense.bin",
                         "pack/index.txt", "pack/native_experts.txt", "pack/tokenizer/vocab.json",
                         "mtp/rt/experts.bin"):
                target = base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(name.encode())

        actual_hash = nvfp4.sha256_file

        def digest(path):
            return {"nvfp4_local_pack.py": nvfp4.RECIPE_SHA256,
                    "requirements-nvfp4-local.txt": nvfp4.REQUIREMENTS_SHA256,
                    "model.safetensors.index.json": nvfp4.MANIFEST_SHA256}.get(Path(path).name) or actual_hash(path)

        with patch.object(nvfp4, "sha256_file", side_effect=digest), patch.object(nvfp4, "verify_file"):
            receipt = nvfp4.prepare(self.layout, run=convert, env={}, log=lambda _line: None)
        target = base / "mtp/rt/draft_vocab.bin"
        self.assertTrue(target.is_file(), "stock setup must not add an unreceipted runtime vocabulary")
        self.assertEqual(source.read_bytes(), target.read_bytes())
        self.assertIn("mtp/rt/draft_vocab.bin", receipt["files"])
        # Stock setup.refresh_draft_vocab keeps this exact pinned subset rather than adding a new output.
        nvfp4.shutil.copyfile(source, target)
        self.assertEqual(receipt, nvfp4.verify_prepared(self.layout))

    def test_generated_config_cannot_point_at_foreign_or_checkpoint_weights(self):
        self.layout.strata.mkdir(parents=True)
        paths = nvfp4.engine_paths(self.layout)
        args = [value for flag, path in paths.items() for value in (flag, str(path))]
        args += ["--expert-profile", str(self.layout.strata / "data/expert-profile.bin")]
        args += self.layout.profile.data["strata"]["expected_engine_flags"]
        cfg = {"args": args, "args_written": args, "model_name": self.layout.profile.data["strata"]["model_name"],
               "exe": str(self.layout.strata / "engine/strata.exe"), "host": "127.0.0.1", "parallel": 4}
        self.layout.strata_config.write_text(json.dumps(cfg))
        with patch.object(install, "host_platform", return_value="windows-x64"):
            install.verify_generated(self.layout)
            for flag in ("--native", "--native-dense-gguf", "--pack", "--mtp", "--ple-gguf"):
                bad = copy.deepcopy(cfg)
                bad["args"][bad["args"].index(flag) + 1] = str(self.layout.models_dir / "foreign")
                bad["args_written"] = bad["args"]
                self.layout.strata_config.write_text(json.dumps(bad))
                with self.subTest(flag=flag), self.assertRaisesRegex(install.InstallError, "pinned NVFP4"):
                    install.verify_generated(self.layout)
