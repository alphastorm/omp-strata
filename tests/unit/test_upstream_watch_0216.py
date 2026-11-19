"""Exercise stock transition boundaries without importing stock code, a network or a GPU."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from omp_strata import dflash2
from scripts import upstream_watch as watch
from tests.unit.test_upstream_watch import FixtureTransport

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def fixture(name, version="16"):
    return (FIXTURES / f"strata_0_2_{version}_{name}").read_text(encoding="utf-8")


class TerminalSetup(unittest.TestCase):
    def plan(self, source=None, **options):
        return watch.stock_plan(source if source is not None else fixture("plan.py"), **({
            "family": "coder", "model": "IQ1_M", "ram": 45, "vram": 31.8, "context": 131072,
            "engine_version": (0, 1, 62), "setup_config_source": fixture("setup_config.py")} | options))

    def test_stock_plan_keeps_the_predecessor_argv_without_a_feed_or_drafter(self):
        from tests.unit.test_strata_0213 import Stock0213Plan

        pro = dict(family="qwen", model="IQ3_S", context=262144, parallel=4, cpu_cores=(8, 16),
                   vram=95.5, ram=96, kv_streaming="off")
        inventory = json.loads((FIXTURES / "strata_0_1_42_gpu_inventory.json").read_text())
        pair = dict(family="qwen", model="IQ3_S", context=262144, gpu_roles={0: "main", 1: "helper"},
                    layer_split="24", gpu_inventory=inventory, vram=None, ram=128)
        for options in ({}, {"context": 262144, "kv_streaming": "off"}, pro, pair):
            with self.subTest(lane=options):
                plan, rollback = self.plan(**options), Stock0213Plan().plan(**options)
                for key in ("expected_engine_flags", "config_keys", "setup_args", "model_url", "model_files"):
                    self.assertEqual(rollback[key], plan[key])
                self.assertNotIn("drafting", plan["config_keys"])
                if options == pro:
                    self.assertTrue(any("~3.9 GB" in line for line in plan["notes"]))
                arena = plan["thresholds"]["arena_gb"]
                self.assertAlmostEqual(arena * 1e9 / 2**30 + 10, plan["thresholds"]["low_ram_below"])

    def test_explicit_low_ram_screen_is_not_admitted_on_the_new_engine(self):
        low = dict(family="qwen", model="IQ3_S", low_ram="on", gpu_arch="120")
        for context in (131072, 262144):
            with self.subTest(context=context), self.assertRaisesRegex(watch.Incomplete, "v0.2.13"):
                self.plan(**low, context=context)

    def test_network_or_layout_changes_cannot_hide_in_skipped_main_statements(self):
        source = fixture("plan.py")
        for before, after in (
            ('a.mtp is not None or mtp_here:', 'a.mtp is not None:'),
            ('mtp_have = find_in(roots, "mtp/rt/experts.bin")', 'mtp_have = find_in(roots, "missing")'),
            ('if not (ROOT / "engine").exists():', 'if True:'),
            ('pulled = update_pull(sys.argv[1:])', 'pulled = update_pull([])'),
            ('default="human"', 'default="jsonl"'),
        ):
            with self.subTest(mutation=before):
                self.assertIn(before, source)
                with self.assertRaisesRegex(watch.Incomplete, "staged-input path changed"):
                    self.plan(source.replace(before, after))
        with self.assertRaisesRegex(watch.Incomplete, "config module|setup_config module"):
            self.plan(setup_config_source=fixture("setup_config.py", "13"))

    def test_four_slots_still_require_the_real_stock_recommendation(self):
        pro = dict(family="qwen", model="IQ3_S", context=262144, parallel=4, cpu_cores=(8, 16),
                   vram=95.5, ram=96, kv_streaming="off")
        source = fixture("plan.py").replace("for n in (2, 3, 4):", "for n in (2, 3):")
        with self.assertRaisesRegex(watch.Incomplete, "parallel_recommend"):
            self.plan(source, **pro)

    def test_requirements_ignore_only_commentary_not_conditional_or_monitor_pins(self):
        req = fixture("requirements.txt")
        before = fixture("requirements.txt", "13")
        monitor = fixture("requirements_monitor.txt", "13")
        files = {"old:requirements.txt": before, "new:terminal/requirements.txt": req,
                 "old:requirements-monitor.txt": monitor, "new:terminal/requirements-monitor.txt": monitor}
        old_src, src = fixture("plan.py", "13"), fixture("plan.py")
        constants = watch.literal_constants(src, ("PY_PACKAGES", "CUDA_WHEELS"))
        with patch.object(watch, "git", side_effect=lambda _, op, spec: files[spec]):
            def review():
                return watch.dependency_review(None, "old", "new", constants, constants, source=src,
                                               prior_source=old_src, old_tag="v0.2.13", candidate_tag="v0.2.16")
            self.assertEqual("unchanged", review()["status"])
            files["new:terminal/requirements.txt"] += '\nextra==1; sys_platform == "darwin"\n'
            with self.assertRaisesRegex(watch.Incomplete, "requirements.txt changed"):
                review()
            files["new:terminal/requirements.txt"] = req
            files["new:terminal/requirements-monitor.txt"] = "textual==9\n"
            with self.assertRaisesRegex(watch.Incomplete, "monitor requirements changed"):
                review()


class TerminalServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {"terminal/serve/server.py": fixture("server_engine_path.py")}
        for path in ("strata_control/drafting.py", "strata_control/vram_fit.py", "strata_control/runtime.py",
                     "tools/strata_tokenizer.py", "serve/server_parts/engines.py",
                     "strata_control/childenv.py", "strata_control/gpu_roles.py", "strata_control/retired.py"):
            cls.files["terminal/" + path] = fixture(Path(path).name)
        # Unchanged stock blobs can live at a different repository-relative path in the new tag.
        for path, version in (("strata_control/draft_layer.py", "11"), ("serve/nonblocking_out.py", "11"),
                              ("strata_control/paths.py", "11"), ("strata_control/user_args.py", "13"),
                              ("serve/toolformat.py", "13")):
            cls.files["terminal/" + path] = fixture(Path(path).name, version)
        for name in ("arch_defaults.cpp", "nv_defaults.cpp"):
            cls.files[f"engine/src/core/{name}"] = fixture(name)

    def review(self, files, groups=()):
        def show(_src, operation, spec):
            if operation == "rev-parse":
                path = spec.removeprefix("pinned:terminal/")
                return files.get("terminal/" + path, watch.SERVER_REVIEWS["0.2.16"]["blobs"][path])
            self.assertEqual("show", operation)
            self.assertTrue(spec.startswith("pinned:"))
            return files[spec.removeprefix("pinned:")]
        with patch.object(watch, "git_blob", side_effect=lambda _, commit, path: files.get(path)), \
                patch.object(watch, "git", side_effect=show):
            return watch.source_server_review(None, "pinned", "0.1.62", groups, strata_tag="v0.2.16")

    def test_review_checks_the_split_server_and_both_engine_tables_even_without_env_opt_ins(self):
        self.assertEqual("0.2.16", self.review(self.files))
        with self.assertRaisesRegex(watch.Incomplete, "pinned:terminal/serve/frontend.py"):
            self.review(self.files | {"terminal/serve/frontend.py": "wrong blob"})
        with self.assertRaises(watch.Incomplete):
            self.review(self.files, {"iq4nl_w4a8"})
        edits = (
            ("terminal/serve/server_parts/engines.py", '("darwin",)', '("win32",)'),
            ("terminal/strata_control/childenv.py", '"GGML_NO_BACKTRACE"', '"GGML_BACKTRACE"'),
            ("terminal/strata_control/gpu_roles.py", "SAME_SPEED = 1.05", "SAME_SPEED = 1.25"),
            ("terminal/serve/server.py", "from strata_control.childenv import", "from other import"),
            ("engine/src/core/arch_defaults.cpp", '{"STRATA_GDN_CONVL2", "2"}', '{"STRATA_GDN_CONVL2", "3"}'),
            ("engine/src/core/nv_defaults.cpp", '{"STRATA_ATTN_DAILY", "1"}', '{"STRATA_ADAPT_NOWAIT", "1"}'),
        )
        for path, before, after in edits:
            with self.subTest(path=path):
                self.assertIn(before, self.files[path])
                with self.assertRaises(watch.Incomplete):
                    self.review(self.files | {path: self.files[path].replace(before, after)})

    def test_missing_part_reports_its_actual_path_even_if_an_old_root_copy_exists(self):
        path = "terminal/strata_control/childenv.py"
        files = self.files.copy()
        files[path.removeprefix("terminal/")] = files.pop(path)
        with self.assertRaisesRegex(watch.Incomplete, path):
            self.review(files)


class TerminalDFlash2(unittest.TestCase):
    def test_new_fetch_and_packer_bind_the_same_offline_inputs_and_selector_output(self):
        from tests.unit.test_component_engine import NAME, members, write_archive
        paths = {"terminal/strata_control/" + name: fixture(name) for name in ("drafting.py", "drafting_fetch.py")}
        packer = "terminal/tools/dflash2_pack.py"
        paths.update({packer: fixture("dflash2_pack.py"), "terminal/data/draft_vocab.bin": b"shipped vocabulary"})
        url = f"{watch.HF}/api/models/{dflash2.REPO}/revision/{dflash2.REVISION}?blobs=true"
        metadata = {"sha": dflash2.REVISION, "cardData": {"license": "apache-2.0"}, "siblings": [
            {"rfilename": name, "size": size, **({"lfs": {"size": size, "sha256": digest}}
                                                 if name.endswith(".safetensors") else {})}
            for name, size, digest in dflash2.FILES]}
        api = watch.API(FixtureTransport({url: (metadata, {})}), allow_github=False)
        with tempfile.TemporaryDirectory() as tmp, patch.object(watch, "git", side_effect=lambda _, op, spec, **kw:
                                                               paths[spec.removeprefix("candidate:")]):
            archive = Path(tmp) / NAME
            pin = write_archive(archive, members(payload={"strata.exe": b"\0".join(
                (dflash2.MARK_ON, dflash2.MARK_VOCAB, dflash2.MARK_SELQ4))}))
            def pins():
                return watch.dflash2_pins(api, None, "candidate", archive, pin, server_key="0.2.16", strata_tag="v0.2.16")
            result = pins()
            self.assertEqual([], dflash2.validate_source({"dflash2_source": result}))
            self.assertEqual(("selq4", dflash2.PACKS), (result["runtime_pack"], result["packs"]))
            paths[packer] = fixture("dflash2_pack.py", "13")
            with self.assertRaisesRegex(watch.Incomplete, "DFlash2 module changed"):
                pins()

    def test_tuned_asset_uses_the_licence_from_this_checkout_not_the_rollback(self):
        base = "candidate:terminal/"
        files = {base + "strata_control/drafting.py": fixture("drafting.py")}
        for name, label in (("LICENSE", "license"), ("NOTICE.md", "notice")):
            files[base + "data/dflash2-tuned/" + name] = fixture(f"tuned_{label}.txt").split(
                "# Stock payload follows.\n", 1)[1].encode()
        tag = "v0.2.16"
        asset = {"name": dflash2.TUNED_NAME, "sha256": dflash2.TUNED_SHA256, "bytes": dflash2.TUNED_BYTES,
                 "url": f"https://github.com/{dflash2.TUNED_REPOSITORY}/releases/download/{tag}/{dflash2.TUNED_NAME}"}
        with patch.object(watch, "git", side_effect=lambda _, op, spec, **kw: files[spec]):
            def tuned():
                return watch.dflash2_tuned_pin({"assets": [asset]}, None, "candidate", strata_tag=tag)
            self.assertEqual(dflash2.tuned_license_sha256(tag), tuned()["license_files"])
            notice = base + "data/dflash2-tuned/NOTICE.md"
            files[notice] = files[notice].replace(b"../../../LICENSE", b"../../LICENSE")
            with self.assertRaisesRegex(watch.Incomplete, "licence SHA-256"):
                tuned()
