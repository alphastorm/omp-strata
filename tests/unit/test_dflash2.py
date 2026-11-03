"""Behavioral boundaries for the explicit, pinned stock DFlash2 arm."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

from omp_strata import common, dflash2, fetch, install, lifecycle
from omp_strata.layout import Layout
from omp_strata.profile import DFLASH2_START_FLAGS, START_PATH_SOURCES, Profile, validate
from tests.fixtures import strata_0_1_36_calibrate as stock_calibration
from tests.unit import dflash2_stock
from tests.unit.test_profile import multi_gpu_data


def source_pin():
    return {
        "repository": dflash2.REPO, "revision": dflash2.REVISION, "license": dflash2.LICENSE,
        "kind": "locally-packed",
        "files": [{"path": path, "bytes": size, "sha256": sha,
                   "sha256_source": "stock v0.2.10 strata_control/drafting.py"}
                  for path, size, sha in dflash2.FILES],
        "packs": copy.deepcopy(dflash2.PACKS), "runtime_pack": "selq4",
        "vocab_sha256": "b1e1d3a7a9e4bf862dcd5923ce661fb59bbd07907e594df5cf86a62ac235cb91",
    }


def variant_data():
    data = multi_gpu_data()
    strata = data["strata"]
    strata["engine_version"] = "0.1.56"
    strata["setup_args"].pop("parallel", None)
    strata["drafting"] = "dflash2"
    strata["forbidden_engine_flags"] = list(dict.fromkeys([*strata["forbidden_engine_flags"], *DFLASH2_START_FLAGS]))
    data["model"]["dflash2_source"] = source_pin()
    return data


class DFlash2ProfileTests(unittest.TestCase):
    def test_explicit_pinned_layer_split_is_admitted(self):
        data = variant_data()
        self.assertEqual([], validate(data))
        self.assertTrue(dflash2.is_pinned(data))
        data["model"]["dflash2_source"]["runtime_pack"] = "q4_0"
        self.assertEqual([], validate(data))

    def test_incompatible_modes_and_settings_are_refused(self):
        mutations = [
            (("strata", "drafting"), "auto"), (("strata", "drafting"), "mtp"),
            (("strata", "drafting"), "off"), (("strata", "drafting"), []),
            (("strata", "engine_version"), "0.1.55"), (("strata", "pipeline_windows"), 2),
            (("strata", "batch_mtp"), True), (("strata", "calibration"), {}),
            (("strata", "setup_args", "parallel"), 4), (("strata", "setup_args", "family"), "coder"),
            (("model", "format"), "modelopt-fp4-local"),
        ]
        for path, value in mutations:
            data = variant_data()
            block = data
            for key in path[:-1]:
                block = block[key]
            block[path[-1]] = value
            with self.subTest(path=path, value=value):
                self.assertTrue(any(p.startswith("strata.drafting:") for p in validate(data)))


class DFlash2FetchTests(unittest.TestCase):
    def layout(self):
        return Layout(Path("/integration"), Profile(Path("profiles/fixture.json"), variant_data()))

    def test_only_the_two_revision_pinned_files_are_planned(self):
        layout = self.layout()
        items = fetch.plan(layout, platform="windows-x64", only={"dflash2"})
        self.assertEqual(2, len(items))
        for item, (path, size, sha) in zip(items, dflash2.FILES):
            self.assertEqual(f"https://huggingface.co/{dflash2.REPO}/resolve/{dflash2.REVISION}/{path}", item.url)
            self.assertEqual(layout.downloads / "dflash2" / dflash2.REVISION / path, item.dest)
            self.assertEqual((size, sha), (item.bytes, item.sha256))

    def test_no_runtime_downloads_for_mac_or_unpinned_profile(self):
        layout = self.layout()
        self.assertEqual([], fetch.plan(layout, platform="darwin-arm64", only={"dflash2"}))
        del layout.profile.data["strata"]["drafting"]
        del layout.profile.data["model"]["dflash2_source"]
        self.assertEqual([], fetch.plan(layout, platform="windows-x64", only={"dflash2"}))

    def test_stock_mtp_layout_resolves_to_the_prepared_folder(self):
        # Verbatim v0.2.10 strata_control/drafting.py data_dir_of; executed, not an arithmetic restatement.
        source = '''
def data_dir_of(args):
    items = [str(a) for a in args]
    for flag, up in (("--pack", 2), ("--mtp", 2)):
        if flag in items and items.index(flag) + 1 < len(items):
            path = Path(items[items.index(flag) + 1])
            if flag == "--mtp" and path.name.isdigit():
                continue
            return path.parents[up - 1] if len(path.parents) >= up else None
    return None
'''
        ns = {"Path": Path}
        exec(source, ns)
        layout = self.layout()
        stock_data = ns["data_dir_of"](["--mtp", str(layout.data / "mtp/rt")])
        self.assertEqual(layout.dflash2_dir, stock_data / dflash2.FOLDER)


class DFlash2SourceProfileTests(unittest.TestCase):
    def test_source_identity_and_provenance_are_required(self):
        for path, value in [
            (("revision",), "0" * 40), (("repository",), "other/model"),
            (("license",), "MIT"), (("kind",), "download"),
            (("runtime_pack",), "q8"), (("vocab_sha256",), "bad"),
            (("files", 0, "path"), "../config.json"), (("files", 1, "sha256"), "0" * 64),
            (("files", 0, "bytes"), 10), (("files", 0, "sha256_source"), ""),
            (("packs", "selq4", "sha256"), "0" * 64),
        ]:
            data = variant_data()
            block = data["model"]["dflash2_source"]
            for key in path[:-1]:
                block = block[key]
            block[path[-1]] = value
            with self.subTest(path=path):
                self.assertTrue(any(p.startswith("model.dflash2_source") for p in validate(data)))
        data = variant_data()
        del data["model"]["dflash2_source"]
        self.assertTrue(any(p.startswith("model.dflash2_source") for p in validate(data)))

    def test_source_without_explicit_mode_is_refused(self):
        data = variant_data()
        del data["strata"]["drafting"]
        self.assertTrue(any(p.startswith("model.dflash2_source:") for p in validate(data)))

    def test_every_start_time_flag_stays_forbidden(self):
        for flag in DFLASH2_START_FLAGS:
            data = variant_data()
            data["strata"]["forbidden_engine_flags"].remove(flag)
            with self.subTest(flag=flag):
                self.assertTrue(any(p.startswith("strata.drafting:") for p in validate(data)))


class DFlash2PreparationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.layout = Layout(Path(temp.name), Profile(Path("profiles/fixture.json"), variant_data()))
        self.pin = self.layout.profile.data["model"]["dflash2_source"]
        for entry in self.pin["files"]:
            data = ("verified " + entry["path"]).encode()
            entry.update(bytes=len(data), sha256=common.sha256_bytes(data))
            path = self.layout.dflash2_file(entry)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.outputs = {"q4_0": b"synthetic q4_0 pack", "selq4": b"synthetic selector pack"}
        for name, data in self.outputs.items():
            self.pin["packs"][name].update(bytes=len(data), sha256=common.sha256_bytes(data))
        self.vocab = b"stock vocabulary fixture"
        self.pin["vocab_sha256"] = common.sha256_bytes(self.vocab)
        source = self.layout.strata / "data/draft_vocab.bin"
        source.parent.mkdir(parents=True)
        source.write_bytes(self.vocab)
        control = self.layout.strata / "strata_control"
        control.mkdir()
        (control / "__init__.py").write_text("")
        constants = {key: getattr(dflash2, key) for key in ("FOLDER", "VOCAB_NAME", "CONVERTED_NAME")}
        constants.update(CONVERTED_BYTES=self.pin["packs"]["selq4"]["bytes"],
                         CONVERTED_SHA256=self.pin["packs"]["selq4"]["sha256"],
                         VOCAB_FILES={"cjk": dflash2.VOCAB_NAME}, _selq4={}, _MARK_SELQ4=dflash2.MARK_SELQ4)
        (control / "drafting.py").write_text(dflash2_stock.SOURCE + "\n\n" +
                                             "\n".join(f"{k} = {v!r}" for k, v in constants.items()))
        self.exe = self.layout.strata / "engine/strata.exe"
        self.exe.parent.mkdir()
        self.exe.write_bytes(b"read-only engine fixture\0" + dflash2.MARK_SELQ4)
        self.calls = []

    def command(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if len(argv) > 1 and argv[1] == str(self.layout.strata / "tools/dflash2_pack.py"):
            name = "selq4" if argv[2] == "--convert-selector" else "q4_0"
            Path(argv[4]).write_bytes(self.outputs[name])
            return
        return install.run(argv, **kwargs)

    def prepare(self):
        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
            return dflash2.prepare(self.layout, run=self.command, env=install.build_env(self.layout), log=lambda _: None)

    def test_packing_uses_stock_argv_offline_and_reuses_only_verified_outputs(self):
        with patch.dict(os.environ, {"STRATA_INJECTED": "1", "PRIVATE_API_KEY": "secret"}):
            receipt = self.prepare()
        tool = str(self.layout.strata / "tools/dflash2_pack.py")
        packs = [argv for argv, _ in self.calls if argv[1] == tool]
        q4 = self.layout.dflash2_dir / dflash2.PACK_NAME
        sel = self.layout.dflash2_dir / dflash2.CONVERTED_NAME
        self.assertEqual([
            [sys.executable, tool, str(self.layout.dflash2_file(self.pin["files"][1])),
             str(self.layout.dflash2_file(self.pin["files"][0])), str(q4) + ".partial", "--q4_0"],
            [sys.executable, tool, "--convert-selector", str(q4), str(sel) + ".partial"],
        ], packs)
        for _, options in self.calls:
            self.assertEqual(self.layout.strata, options["cwd"])
            self.assertEqual({"STRATA_NO_ACQUIRE": "1"},
                             {k: v for k, v in options["env"].items() if k.startswith("STRATA_")})
            self.assertNotIn("PRIVATE_API_KEY", options["env"])
        marker = sel.with_name(sel.name + ".ok")
        self.assertEqual(self.pin["packs"]["selq4"]["sha256"], common.read_json(marker)["sha256"])
        before = marker.read_bytes()
        self.calls.clear()
        self.assertEqual(receipt, self.prepare())
        self.assertFalse(any(argv[1] == tool for argv, _ in self.calls))
        self.assertEqual(before, marker.read_bytes())

    def test_wrong_size_or_hash_never_promotes_a_pack(self):
        good = self.outputs["q4_0"]
        for bad in (b"short", b"x" * len(good)):
            self.outputs["q4_0"] = bad
            with self.subTest(size=len(bad)), self.assertRaises(common.IntegrityError):
                self.prepare()
            self.assertFalse((self.layout.dflash2_dir / dflash2.PACK_NAME).exists())
            self.assertFalse(list(self.layout.dflash2_dir.glob("*.partial")))

    def test_downloads_are_deeply_verified_even_with_an_existing_marker(self):
        entry = self.pin["files"][0]
        path = self.layout.dflash2_file(entry)
        common.verify_file(path, entry["bytes"], entry["sha256"], source=entry["sha256_source"], log=lambda _: None)
        stamp = path.stat()
        path.write_bytes(b"x" * stamp.st_size)
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaises(common.IntegrityError):
            self.prepare()
        self.assertEqual([], self.calls)

    def test_interrupted_preparation_is_refused_before_running_stock(self):
        for name in ("src", ".omp-strata-q4_0.partial", "foreign.tmp"):
            path = self.layout.dflash2_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.mkdir() if name == "src" else path.write_bytes(b"leftover")
            with self.subTest(name=name), self.assertRaises(common.IntegrityError):
                self.prepare()
            path.rmdir() if path.is_dir() else path.unlink()
        self.assertEqual([], self.calls)

    def test_engine_selector_support_must_equal_the_runtime_pin(self):
        self.exe.write_bytes(b"an engine without the selector marker")
        with self.assertRaises(install.InstallError):
            self.prepare()
        self.pin["runtime_pack"] = "q4_0"
        self.calls.clear()
        self.assertEqual({"q4_0": self.pin["packs"]["q4_0"]["sha256"]}, self.prepare()["packs"])
        self.assertFalse((self.layout.dflash2_dir / dflash2.CONVERTED_NAME).exists())

    def test_foreign_vocab_is_not_silently_replaced(self):
        target = self.layout.dflash2_dir / dflash2.VOCAB_NAME
        target.parent.mkdir(parents=True)
        target.write_bytes(b"a different vocabulary")
        with self.assertRaises(common.IntegrityError):
            self.prepare()
        self.assertEqual(b"a different vocabulary", target.read_bytes())


class DFlash2ConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.layout = Layout(Path(temp.name), Profile(Path("profiles/fixture.json"), variant_data()))
        self.layout.strata.mkdir(parents=True)
        (self.layout.strata / "setup.py").write_text(stock_calibration.SETUP)
        data = self.layout.profile.data
        args = list(data["strata"]["expected_engine_flags"])
        for flag, path in (("--pack", self.layout.data / "packs/iq3_s"),
                           ("--native", self.layout.model_file(data["model"]["files"][0])),
                           ("--expert-profile", self.layout.strata / "data/expert-profile.json"),
                           ("--mtp", self.layout.data / "mtp/rt"), ("--ple-gguf", self.layout.data / "ple.gguf")):
            args.extend([flag, str(path)])
        self.cfg = {"args": args, "cwd": str(self.layout.strata), "exe": str(self.layout.strata / "engine/strata.exe"),
                    "gpu": data["strata"]["setup_args"]["gpus"], "gpus_asked": True,
                    "host": data["server"]["listen_host"], "lib_dirs": [], "log": "server.log",
                    "model_name": data["strata"]["model_name"], "port": data["server"]["port"],
                    "tokenizer": str(self.layout.data / "tokenizer"), "layer_split": "auto"}

    def write_config(self):
        common.atomic_write_json(self.layout.strata_config, self.cfg)

    def apply(self):
        self.write_config()
        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
            install.apply_drafting(self.layout, log=lambda _: None)
        self.cfg = common.read_json(self.layout.strata_config)

    def verify(self):
        self.write_config()
        with patch.object(install, "host_platform", return_value="windows-x64"):
            return install.verify_generated(self.layout)

    def test_apply_preserves_setup_stamp_and_refuses_foreign_carryover(self):
        self.cfg["args_written"] = list(self.cfg["args"])
        before = copy.deepcopy(self.cfg)
        self.apply()
        self.assertEqual({**before, "drafting": "dflash2"}, self.cfg)
        self.apply()
        for old in ("mtp", "auto", "off", None):
            self.cfg["drafting"] = old
            with self.subTest(old=old), self.assertRaises(install.InstallError):
                self.apply()
            self.assertEqual(old, common.read_json(self.layout.strata_config)["drafting"])

    def test_generated_config_requires_the_choice_and_refuses_it_unpinned(self):
        with self.assertRaises(install.InstallError):
            self.verify()
        self.apply()
        self.assertEqual("dflash2", self.verify()["drafting"])
        self.cfg["drafting"] = "mtp"
        with self.assertRaises(install.InstallError):
            self.verify()
        del self.layout.profile.data["strata"]["drafting"]
        with self.assertRaises(install.InstallError):
            self.verify()

    def test_setup_argv_is_unchanged_by_the_drafter(self):
        before = install.setup_argv(self.layout)
        del self.layout.profile.data["strata"]["drafting"]
        del self.layout.profile.data["model"]["dflash2_source"]
        self.assertEqual(before, install.setup_argv(self.layout))
        self.assertNotIn("--drafter", before)

    def test_runtime_identity_binds_every_prepared_file(self):
        for relative in ("engine/strata.exe", *START_PATH_SOURCES):
            file = self.layout.strata / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(relative.encode())
        self.layout.dflash2_dir.mkdir(parents=True)
        prepared = self.layout.dflash2_dir / dflash2.PACK_NAME
        prepared.write_bytes(b"pinned output")
        self.apply()
        install.freeze_shared_settings(self.layout)
        first = install.runtime_identity(self.layout, self.cfg)
        self.assertEqual(common.sha256_bytes(b"pinned output"), first["files"]["data/dflash2/" + dflash2.PACK_NAME]["sha256"])
        prepared.write_bytes(b"changed output")
        self.assertNotEqual(first, install.runtime_identity(self.layout, self.cfg))


class DFlash2StartTests(unittest.TestCase):
    SERVER = "[strata] drafting: DFlash2 alone (--draft dflash2, --draft-conf 0.35)\n"
    START = "[strata] 2026-11-03 12:00:00 engine started: fixture generation\n"
    SELECTOR = "strata dflash2: selector codebooks: Q4_0 rows (about 174 MiB less than bf16)\n"

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.layout = Layout(Path(temp.name), Profile(Path("profiles/fixture.json"), variant_data()))
        self.engine = (f"strata serve: DFlash2 drafter on ({self.layout.dflash2_dir / dflash2.CONVERTED_NAME}, "
                       "graphs captured in 100 ms); windows up to 6 tokens; no MTP layer is loaded "
                       "(--draft-fallback none); layer split: the drafter is on CUDA1 (last stage), "
                       "the other stages' taps are gathered onto it\n")

    def capture(self, server=None, engine=None, prefix="older generation\n"):
        server = self.SERVER if server is None else server
        engine = self.START + self.SELECTOR + self.engine if engine is None else engine
        for relative, text in (("logs/server.log", server), ("runtime/strata/engine.log", engine)):
            path = self.layout.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(prefix + text)
        common.atomic_write_json(self.layout.run_record, {
            "log": "logs/server.log", "log_start_offset": len(prefix.encode()),
            "engine_log": "runtime/strata/engine.log", "engine_log_start_offset": len(prefix.encode())})
        lifecycle._check_drafting(self.layout)
        return common.read_json(self.layout.run_record)["drafting"]

    def test_complete_on_set_is_bound_to_this_interval_and_the_runtime_pack(self):
        observed = self.capture(prefix="[strata] Drafting: MTP (DFlash2 didn't start)\n")
        self.assertEqual("dflash2", observed["mode"])
        self.assertEqual(6, observed["window_tokens"])
        self.assertEqual("data/dflash2/" + dflash2.CONVERTED_NAME, observed["pack"])
        self.assertEqual(dflash2.CONVERTED_SHA256, observed["pack_sha256"])
        self.assertEqual(self.SELECTOR.strip(), observed["selector_line"])
        self.assertGreater(observed["engine_log_interval"]["start"], 0)
        self.layout.profile.data["model"]["dflash2_source"]["runtime_pack"] = "q4_0"
        self.engine = self.engine.replace(dflash2.CONVERTED_NAME, dflash2.PACK_NAME)
        self.assertIsNone(self.capture(engine=self.START + self.engine)["selector_line"])

    def test_every_stock_fallback_refusal_and_retry_is_rejected_in_either_stream(self):
        refusals = [
            "[strata] Drafting: MTP (DFlash2 didn't fit)",
            "[strata] Drafting: DFlash2 (the MTP drafter isn't downloaded yet)",
            "[strata] Drafting: off (no drafter is downloaded yet)",
            "[strata] Drafting: MTP (DFlash2 didn't start)",
            "strata serve: --draft dflash2: cannot run. The MTP drafts instead.",
            "strata serve: --draft-fallback none: no MTP is loaded, so the start ends here",
            "[strata] 2026-11-03 12:00:00 the engine ended before it was ready with the DFlash2 drafter (exit code 1); starting it again with the MTP",
            'strata generate: DFlash2 drafter on (pack, graphs captured in 1 ms), the MTP layer stays as the fallback',
        ]
        for line in refusals:
            for stream in ("server", "engine"):
                with self.subTest(line=line, stream=stream), self.assertRaises(lifecycle.LifecycleError):
                    self.capture(server=self.SERVER + line + "\n" if stream == "server" else self.SERVER,
                                 engine=self.START + self.SELECTOR + self.engine + (line + "\n" if stream == "engine" else ""))

    def test_missing_repeated_and_unreviewed_on_evidence_are_rejected(self):
        base = self.START + self.SELECTOR + self.engine
        cases = [
            ("", base), (self.SERVER * 2, base), (self.SERVER, self.START + self.SELECTOR),
            (self.SERVER, base + self.engine), (self.SERVER, base.replace(self.SELECTOR, "")),
            (self.SERVER, base + self.SELECTOR), (self.SERVER, base + self.START),
            (self.SERVER, base.replace(self.START, "")),
            (self.SERVER, base.replace(dflash2.CONVERTED_NAME, dflash2.PACK_NAME)),
            (self.SERVER, base.replace("CUDA1", "CUDA0")),
            (self.SERVER, base.replace("last stage", "first stage")),
            (self.SERVER, base.replace("no MTP layer is loaded (--draft-fallback none)", "the MTP layer stays as the fallback")),
            (self.SERVER.replace("0.35", "0.5"), base),
        ]
        for server, engine in cases:
            with self.subTest(server=server, engine=engine), self.assertRaises(lifecycle.LifecycleError):
                self.capture(server=server, engine=engine, prefix=self.SERVER + base)
        self.layout.profile.data["model"]["dflash2_source"]["runtime_pack"] = "q4_0"
        self.engine = self.engine.replace(dflash2.CONVERTED_NAME, dflash2.PACK_NAME)
        with self.assertRaises(lifecycle.LifecycleError):
            self.capture()
