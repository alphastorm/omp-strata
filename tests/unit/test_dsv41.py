"""Host-free admission of the single reviewed stock DeepSeek comparison family."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest

from omp_strata import dsv41
from omp_strata import fetch
from omp_strata.common import read_json
from omp_strata.layout import Layout
from omp_strata.profile import Profile, validate
from tests.candidate import PROFILE, REPO


def profile_data():
    data = read_json(PROFILE)
    data["profile_id"] = "test-dsv41-262k"
    data["status"] = "draft"
    data["host"] = {"os": "windows", "route": "native-windows", "gpu_index": 0,
                    "gpu_model": "NVIDIA RTX PRO 6000 Blackwell Workstation Edition", "display_attached": True,
                    "min_gpu_vram_mib": 97000, "min_total_ram_gib": 192, "min_available_ram_gib_at_start": 80,
                    "min_driver_major": 580, "min_free_disk_gib": 262, "cpu_cores": [8, 16]}
    data["server"].update(port=18090, ready_timeout_s=3600)
    data["omp"].update(context_window=262144, max_tokens=32768)
    # A syntactically valid synthetic component until tests bind an actual package tree.
    comp = {"format": "tar.gz", "platform": "windows-x86_64", "backend": "cuda", "variant": "cuda13",
            "manifest_sha256": "a" * 64, "build_id": "test+cuda13.0", "build_source": "release",
            "build_commit": "abcdef0", "version": dsv41.ENGINE_VERSION}
    data["strata"] = {"repository": "https://github.com/Niko1221/Strata.git", "tag": dsv41.TAG,
                      "commit": dsv41.COMMIT, "engine_version": dsv41.ENGINE_VERSION,
                      "model_name": dsv41.MODEL_NAME, "artifacts": {"dsv41_package": dict(dsv41.PACKAGE)},
                      "dsv41_component": comp, "python_lock": {
                          "path": "locks/strata-python-cp313-win_amd64-strata0.2.11.txt", "python": "3.13",
                          "sha256": "0174631a131ad17525138ec35288107257bcfeadf64792f46a5ea1b58549363b"},
                      "setup_args": {"family": dsv41.FAMILY, "model": dsv41.MODEL, "context": 262144,
                                     "vision": "no", "gpu": 0},
                      "expected_engine_flags": dsv41.stock_flags(262144),
                      "forbidden_engine_flags": list(dsv41.FORBIDDEN_FLAGS),
                      "engine_env": dict(dsv41.ENGINE_ENV), "user_args": list(dsv41.USER_ARGS)}
    data["model"] = {"variant": dsv41.FAMILY, "quantization": "IQ2_XS", "license": "MIT", "files": dsv41.model_files()}
    return data


class Admission(unittest.TestCase):
    def test_exact_family_and_both_reviewed_contexts_validate(self):
        for context in dsv41.CONTEXTS:
            data = profile_data()
            data["strata"]["setup_args"]["context"] = data["omp"]["context_window"] = context
            data["strata"]["expected_engine_flags"] = dsv41.stock_flags(context)
            self.assertEqual(validate(data), [])

    def test_forbidden_qwen_options_never_reach_the_qwen_checks(self):
        for key in ("kv", "low_ram", "parallel", "kv_streaming", "experimental_speed_projection", "layer_split"):
            data = profile_data()
            data["strata"]["setup_args"][key] = "off"
            with self.subTest(key):
                self.assertTrue(validate(data))
        for key in dsv41.FORBIDDEN_STRATA:
            data = profile_data()
            data["strata"][key] = {}
            with self.subTest(key):
                self.assertTrue(validate(data))

    def test_wrong_inputs_package_experts_vision_and_env_are_refused(self):
        mutations = [
            lambda p: p["model"]["files"][0].update(sha256="0" * 64),
            lambda p: p["model"]["files"][0].update(bytes=39535788064),
            lambda p: p["model"]["files"][0].update(revision="f" * 40),
            lambda p: p["model"]["files"][0].update(path=p["model"]["files"][0]["path"].replace("00004", "00006")),
            lambda p: p["strata"]["artifacts"].clear(),
            lambda p: p["strata"]["artifacts"]["dsv41_package"].update(sha256="0" * 64),
            lambda p: p["strata"]["dsv41_component"].update(version="0.1.52"),
            lambda p: p["strata"].update(user_args=["--experts", "5"]),
            lambda p: p["strata"]["setup_args"].update(vision="none"),
            lambda p: p["strata"]["setup_args"].update(vision="yes"),
            lambda p: p["strata"]["engine_env"].pop("STRATA_DS4_AUTO_PIN"),
            lambda p: p["server"].update(ready_timeout_s=900),
            lambda p: p["model"].update(mtp_source={"revision": "a" * 40}),
        ]
        for i, mutate in enumerate(mutations):
            data = profile_data()
            mutate(data)
            with self.subTest(i):
                self.assertTrue(validate(data))

    def test_stock_fixture_supplies_every_byte_and_digest(self):
        tree = ast.parse((REPO / "tests/fixtures/strata_0_2_11_plan.py").read_text())
        pins = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id in
                                                   ("DSV41_FILES", "DSV41_ISTA_FILES") for n in node.targets):
                pins.update(ast.literal_eval(node.value))
        for _repo, _revision, path, size, digest in dsv41.FILES:
            self.assertEqual(pins[path.rsplit("/", 1)[-1]], (size, digest))

    def test_layout_and_conversation_claim_are_family_specific(self):
        profile = Profile(Path("profiles/test.json"), profile_data())
        layout = Layout(Path("root"), profile)
        self.assertEqual(layout.strata_config.name, "strata-deepseek-v4.1-flash-ist-das-2.25bpw.json")
        self.assertEqual(layout.dsv41_engine_dir.name, "0.1.57-windows-x86_64-cuda-cuda13")
        self.assertEqual(layout.dsv41_package.name, dsv41.PACKAGE_NAME)
        self.assertFalse(profile.parks_automatically)
        self.assertFalse(profile.keeps_conversations)

    def test_fetch_uses_per_file_revisions_and_no_qwen_artifacts_or_mmproj(self):
        layout = Layout(Path("root"), Profile(Path("profiles/test.json"), profile_data()))
        items = fetch.plan(layout, platform="windows-x64")
        self.assertEqual([i.name for i in items], ["omp", "dsv41"] + ["model"] * 7)
        self.assertEqual(len({i.dest for i in items}), len(items))
        self.assertEqual(items[1].sha256, dsv41.PACKAGE["sha256"])
        for item, row in zip(items[2:], dsv41.FILES):
            repo, revision, path, size, digest = row
            self.assertEqual(item.url, f"https://huggingface.co/{repo}/resolve/{revision}/{path}")
            self.assertEqual((item.bytes, item.sha256), (size, digest))
            self.assertNotIn("mmproj", item.url)
        self.assertEqual(len(fetch.plan(layout, platform="windows-x64", only={"dsv41"})), 1)
        self.assertEqual([i.name for i in fetch.plan(layout, platform="darwin-arm64")], ["omp"])


if __name__ == "__main__":
    unittest.main()
