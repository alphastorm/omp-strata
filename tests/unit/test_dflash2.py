"""Behavioral boundaries for the explicit, pinned stock DFlash2 arm."""
import copy
import ast
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

from omp_strata import common, dflash2, dsv41, engine_component, fetch, install, lifecycle, ompcfg
from omp_strata.layout import Layout
from omp_strata.profile import DFLASH2_START_FLAGS, Profile, start_path_sources, validate
from tests.fixtures import strata_0_1_36_calibrate as stock_calibration
from tests.unit import dflash2_stock
from tests.unit.test_profile import multi_gpu_data, plain_gguf_data
from scripts import campaign, upstream_watch as watch


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
    data = plain_gguf_data(multi_gpu_data(), qwen_only=True)
    strata = data["strata"]
    strata["engine_version"] = "0.1.56"
    strata["setup_args"].pop("parallel", None)
    strata["drafting"] = "dflash2"
    strata["forbidden_engine_flags"] = list(dict.fromkeys([*strata["forbidden_engine_flags"], *DFLASH2_START_FLAGS]))
    data["model"]["dflash2_source"] = source_pin()
    return data


def slot_variant_data():
    data = variant_data()
    card = data["host"].pop("gpus")[0]
    data["host"].update({key: card[key] for key in
                         ("gpu_index", "gpu_model", "min_gpu_vram_mib", "display_attached")})
    strata = data["strata"]
    strata["engine_version"] = "0.1.57"
    setup = strata["setup_args"]
    setup.pop("gpus")
    setup.pop("layer_split")
    setup.update(gpu=card["gpu_index"], parallel=4)
    return data


def tuned_pin():
    return {
        "tag": "v0.2.12",
        "url": f"https://github.com/{dflash2.TUNED_REPOSITORY}/releases/download/v0.2.12/{dflash2.TUNED_NAME}",
        "file": dflash2.TUNED_NAME, "bytes": dflash2.TUNED_BYTES, "sha256": dflash2.TUNED_SHA256,
        "sha256_source": "Stock v0.2.12 drafting constants; v0.2.12 SHA256SUMS.txt",
        "license": dflash2.LICENSE, "base": dflash2.TUNED_BASE,
        "license_files": dict(dflash2.TUNED_LICENSE_SHA256),
    }


def tuned_variant_data():
    path = (Path(__file__).resolve().parents[2] / "profiles" /
            "win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json")
    data = common.read_json(path)
    strata = data["strata"]
    strata.update(tag="v0.2.12", engine_version="0.1.58")
    artifact = strata["artifacts"]["engine_archive"]
    artifact["file"] = artifact["file"].replace("0.1.57", "0.1.58")
    artifact["url"] = artifact["url"].replace("v0.2.11", "v0.2.12").replace("0.1.57", "0.1.58")
    data["model"]["dflash2_source"]["tuned"] = tuned_pin()
    return data


class TunedDFlash2ProfileTests(unittest.TestCase):
    def test_tuned_pro_and_standard_runtime_files(self):
        data = tuned_variant_data()
        self.assertEqual([], validate(data))
        pin = data["model"]["dflash2_source"]
        self.assertIs(pin["tuned"], dflash2.runtime_file(pin))
        del pin["tuned"]
        self.assertIs(pin["packs"]["selq4"], dflash2.runtime_file(pin))
        self.assertFalse(dflash2.is_tuned(pin))
        self.assertTrue(dflash2.tuned_aware("0.1.58"))
        self.assertTrue(dflash2.tuned_aware("0.1.59"))
        for version in ("0.1.57", None, "bad"):
            self.assertFalse(dflash2.tuned_aware(version))

    def test_tuned_artifact_requires_exact_reviewed_identity_and_provenance(self):
        for key, value in (
            ("file", "other.pack"), ("bytes", 1), ("bytes", True), ("sha256", "0" * 64),
            ("url", tuned_pin()["url"].replace("v0.2.12", "v0.2.13")),
            ("url", tuned_pin()["url"].replace("Niko1221", "other")),
            ("tag", "v0.2.11"), ("tag", "v0.2.12-beta"), ("tag", "bad"), ("tag", None),
            ("license", "MIT"), ("base", "other"), ("license_files", {}),
            ("sha256_source", ""), ("extra", "unreviewed"),
        ):
            data = tuned_variant_data()
            data["model"]["dflash2_source"]["tuned"][key] = value
            with self.subTest(key=key, value=value):
                self.assertTrue(any(p.startswith("model.dflash2_source.tuned") for p in validate(data)))
        for key in tuned_pin():
            data = tuned_variant_data()
            del data["model"]["dflash2_source"]["tuned"][key]
            with self.subTest(missing=key):
                self.assertTrue(any(p.startswith("model.dflash2_source.tuned") for p in validate(data)))
        for value in (None, [], "tuned"):
            data = tuned_variant_data()
            data["model"]["dflash2_source"]["tuned"] = value
            self.assertTrue(any(p.startswith("model.dflash2_source.tuned") for p in validate(data)))

    def test_tuned_requires_the_reviewed_resident_cuda_cell(self):
        mutations = (
            (("strata", "engine_version"), "0.1.57", "requires engine"),
            (("host", "gpu_model"), "NVIDIA GeForce RTX 5090", "resident boundary"),
            (("strata", "setup_args", "family"), "coder", "qwen IQ3_S"),
            (("strata", "setup_args", "model"), "IQ3_XXS", "qwen IQ3_S"),
            (("strata", "model_name"), "qwen3.8-flash-next-iq3_xxs", "qwen IQ3_S"),
            (("strata", "engine_component"), None, "CUDA engine component"),
            (("model", "dflash2_source", "runtime_pack"), "q4_0", "runtime_pack selq4"),
        )
        for path, value, message in mutations:
            data = tuned_variant_data()
            block = data
            for key in path[:-1]:
                block = block[key]
            block[path[-1]] = value
            with self.subTest(path=path):
                self.assertTrue(any("model.dflash2_source.tuned:" in p and message in p for p in validate(data)))
        data = tuned_variant_data()
        flags = data["strata"]["expected_engine_flags"]
        flags[flags.index("--expert-cache") + 1] = "14000"
        self.assertTrue(any("requires --expert-cache auto" in p for p in validate(data)))
        data = variant_data()
        data["strata"]["engine_version"] = "0.1.58"
        data["model"]["dflash2_source"]["tuned"] = tuned_pin()
        self.assertTrue(any("several cards" in p for p in validate(data)))
        data = tuned_variant_data()
        del data["strata"]["drafting"]
        self.assertIn("model.dflash2_source: requires strata.drafting", validate(data))


class DFlash2ProfileTests(unittest.TestCase):
    def test_explicit_pinned_layer_split_is_admitted(self):
        data = variant_data()
        self.assertEqual("qwen", data["strata"]["setup_args"]["family"])
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

    def test_named_dflash2_batch_slots_require_engine_0157_on_one_card(self):
        data = slot_variant_data()
        self.assertEqual([], validate(data))
        for version in ("0.1.56", None):
            data["strata"]["engine_version"] = version
            with self.subTest(version=version):
                self.assertTrue(any("batch slots need engine 0.1.57+" in p for p in validate(data)))
        data = variant_data()
        data["strata"]["engine_version"] = "0.1.57"
        data["strata"]["setup_args"]["parallel"] = 4
        self.assertTrue(any("batch slots need engine 0.1.57+" in p for p in validate(data)))

    def test_batch_slot_dflash2_keeps_incompatible_modes_and_start_flags_refused(self):
        for field, value in (("batch_mtp", True), ("pipeline_windows", 2), ("calibration", {})):
            data = slot_variant_data()
            data["strata"][field] = value
            with self.subTest(field=field):
                self.assertIn(f"strata.drafting: incompatible with strata.{field}", validate(data))
        for flag in DFLASH2_START_FLAGS:
            data = slot_variant_data()
            data["strata"]["forbidden_engine_flags"].remove(flag)
            with self.subTest(flag=flag):
                self.assertTrue(any(p.startswith("strata.drafting:") for p in validate(data)))


def drafting_args_data():
    path = (Path(__file__).resolve().parents[2] / "profiles" /
            "win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect"
            "-env86gt-strata0.2.13-omp18.18.3.json")
    data = common.read_json(path)
    data["strata"]["drafting_args"] = {"--draft-conf": "0.5"}
    return data


class DraftingArgsProfileTests(unittest.TestCase):
    def test_reviewed_pin_is_flattened_without_changing_stock_confidence(self):
        data = drafting_args_data()
        self.assertEqual([], validate(data))
        self.assertEqual(["--draft-conf", "0.5"], dflash2.drafting_user_args(data))
        self.assertEqual(frozenset({"0.35"}), dflash2.stock_draft_confs(data))
        self.assertEqual(frozenset({"0.5"}), dflash2.expected_draft_confs(data))
        del data["strata"]["drafting_args"]
        self.assertIsNone(dflash2.drafting_user_args(data))
        self.assertEqual(frozenset({"0.35"}), dflash2.expected_draft_confs(data))

    def test_empty_foreign_or_nonstock_pins_are_refused(self):
        for pin in ({}, None, [], "0.5", {"--spec": "6"}, {"--draft-cap": "8"},
                    {"--draft-conf": "0.6"}, {"--draft-conf": 0.5},
                    {"--draft-conf": ["0.5"]}, {"--draft-conf": "0.5", "--spec": "8"}):
            data = drafting_args_data()
            data["strata"]["drafting_args"] = pin
            with self.subTest(pin=pin):
                self.assertTrue(any(p.startswith("strata.drafting_args:") for p in validate(data)))

    def test_pin_requires_reviewed_engine_component_and_named_drafter(self):
        for key, value, message in (
            ("engine_version", "0.1.58", "engine 0.1.59"),
            ("engine_component", None, "requires strata.engine_component"),
            ("drafting", None, "requires strata.drafting"),
        ):
            data = drafting_args_data()
            if value is None:
                del data["strata"][key]
            else:
                data["strata"][key] = value
            with self.subTest(key=key):
                self.assertTrue(any(p.startswith("strata.drafting_args:") and message in p
                                    for p in validate(data)))

    def test_deterministic_stock_values_are_not_new_arms(self):
        for data, confidence in ((drafting_args_data(), "0.35"), (tuned_variant_data(), "0.55")):
            data["strata"].update(engine_version="0.1.59", drafting_args={"--draft-conf": confidence})
            with self.subTest(confidence=confidence):
                self.assertTrue(any("the pin equals stock's own value for this profile" in p
                                    for p in validate(data)))


class DFlash2DraftTests(unittest.TestCase):
    def test_drafting_conflicts_only_admit_reviewed_single_card_slots(self):
        base = dict(drafting="dflash2", version=(0, 1, 57), component=True, multi_input=False,
                    parallel=4, pipeline_windows=None, batch_mtp=None, calibration=False)
        for changes in ({}, {"parallel": None}, {"parallel": 8}, {"version": (0, 1, 58)},
                        {"version": (0, 1, 56), "parallel": None, "multi_input": True},
                        {"drafting": None, "batch_mtp": True}):
            with self.subTest(allowed=changes):
                self.assertIsNone(watch.drafting_conflicts(**(base | changes)))
        for changes in ({"version": (0, 1, 56)}, {"version": None}, {"version": (0, 1, 55)},
                        {"component": False}, {"multi_input": True}, {"drafting": "auto"},
                        {"pipeline_windows": 2}, {"batch_mtp": True}, {"calibration": True}):
            with self.subTest(refused=changes):
                self.assertTrue(watch.drafting_conflicts(**(base | changes)).startswith("strata.drafting:"))

    def test_named_four_slot_dflash2_keeps_omps_four_request_limit(self):
        data = slot_variant_data()
        self.assertEqual([], validate(data))
        config = json.loads(ompcfg.render_config_yml(Profile(Path("profiles/fixture.json"), data)))
        self.assertEqual({"strata-local": 4}, config["providers"]["maxInFlightRequests"])

    def test_campaign_accepts_the_pro_arm_and_prefers_the_current_dflash2_families(self):
        before = ("win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-kvvram-envpg-parking"
                  "-strata0.2.11-omp18.16.0")
        after = before.replace("-batchmtp-", "-df2-")
        self.assertTrue(campaign.lane_variant(before, after))
        # Owner 2026-11-06: DFlash2 is the PRO's current profile and the Studio route pinned to it is current, so at the
        # same release each outranks its batch-MTP variant and a later campaign names it as the predecessor.
        families = next(families for families, _, _ in campaign.LANES if before.split("-strata")[0] in families)
        self.assertEqual(after.split("-strata")[0], families[-1])
        self.assertLess(families.index(before.split("-strata")[0]), families.index(after.split("-strata")[0]))
        route = "client-rtxpro6000-262k-batchmtp-pledirect-kvvram-envpg-strata0.2.11-omp18.16.0"
        routes = next(families for families, _, _ in campaign.LANES if route.split("-strata")[0] in families)
        self.assertEqual(route.replace("-batchmtp-", "-df2-").split("-strata")[0], routes[-1])
        self.assertTrue(campaign.lane_variant(route, route.replace("-batchmtp-", "-df2-")))


class DFlash2FetchTests(unittest.TestCase):
    def layout(self):
        return Layout(Path("/integration"), Profile(Path("profiles/fixture.json"), variant_data()))

    def test_tuned_plan_adds_one_release_asset_without_changing_the_standard_plan(self):
        layout = Layout(Path("/integration"), Profile(Path("profiles/fixture.json"), tuned_variant_data()))
        pin = layout.profile.data["model"]["dflash2_source"]
        tuned = pin.pop("tuned")
        standard = fetch.plan(layout, platform="windows-x64")
        pin["tuned"] = tuned
        expected = fetch.Item("dflash2", tuned["url"],
                              layout.downloads / "dflash2" / "v0.2.12" / dflash2.TUNED_NAME,
                              tuned["bytes"], tuned["sha256"], tuned["sha256_source"])
        self.assertEqual(standard + [expected], fetch.plan(layout, platform="windows-x64"))
        self.assertEqual([*[item for item in standard if item.name == "dflash2"], expected],
                         fetch.plan(layout, platform="windows-x64", only={"dflash2"}))
        counted = fetch.plan(layout, platform="windows-x64", only={"model", "dflash2", "engine", "llama"})
        self.assertIn(expected, counted)
        self.assertEqual(sum(item.bytes for item in counted), fetch.required_space(counted))
        pin.pop("tuned")
        self.assertEqual(standard, fetch.plan(layout, platform="windows-x64"))

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
        if len(argv) > 2 and argv[2] == dflash2.TUNED_OK:
            target = self.layout.dflash2_dir / dflash2.TUNED_NAME
            info = target.stat()
            common.atomic_write_json(target.with_name(target.name + ".ok"), {
                "size": info.st_size, "mtime_ns": info.st_mtime_ns, "sha256": self.pin["tuned"]["sha256"]})
            return
        if len(argv) > 1 and argv[1] == str(self.layout.strata / "tools/dflash2_pack.py"):
            name = "selq4" if argv[2] == "--convert-selector" else "q4_0"
            Path(argv[4]).write_bytes(self.outputs[name])
            return
        return install.run(argv, **kwargs)

    def prepare(self):
        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
            return dflash2.prepare(self.layout, run=self.command, env=install.build_env(self.layout), log=lambda _: None)

    def enable_tuned(self):
        tuned = self.pin["tuned"] = tuned_pin()
        payload = b"synthetic tuned selector pack"
        tuned.update(bytes=len(payload), sha256=common.sha256_bytes(payload), license_files={})
        download = self.layout.dflash2_tuned_download
        download.parent.mkdir(parents=True)
        download.write_bytes(payload)
        for src, dest in dflash2.TUNED_LICENSE.items():
            path = self.layout.strata / dflash2.TUNED_LICENSE_FOLDER / src
            path.parent.mkdir(parents=True, exist_ok=True)
            content = ("stock tuned licence fixture " + src).encode()
            path.write_bytes(content)
            tuned["license_files"][dest] = common.sha256_bytes(content)

    def test_tuned_preparation_copies_marks_and_licenses_offline_and_is_idempotent(self):
        self.enable_tuned()
        with patch.dict(os.environ, {"STRATA_DFLASH2_TUNED_URL": "https://unreviewed.invalid/pack"}):
            result = self.prepare()
        self.assertEqual({key: self.pin["tuned"][key] for key in ("file", "sha256", "license_files")}, result["tuned"])
        target = self.layout.dflash2_dir / dflash2.TUNED_NAME
        self.assertEqual(self.layout.dflash2_tuned_download.read_bytes(), target.read_bytes())
        marker = common.read_json(target.with_name(target.name + ".ok"))
        self.assertEqual({"size": target.stat().st_size, "mtime_ns": target.stat().st_mtime_ns,
                          "sha256": self.pin["tuned"]["sha256"]}, marker)
        for src, dest in dflash2.TUNED_LICENSE.items():
            self.assertEqual((self.layout.strata / dflash2.TUNED_LICENSE_FOLDER / src).read_bytes(),
                             (self.layout.dflash2_dir / dest).read_bytes())
        scripts = []
        for argv, kwargs in self.calls:
            self.assertEqual("1", kwargs["env"]["STRATA_NO_ACQUIRE"])
            self.assertNotIn("STRATA_DFLASH2_TUNED_URL", kwargs["env"])
            if argv[1] == "-c":
                scripts.append(argv[2])
        self.assertIn(dflash2.TUNED_OK, scripts)
        self.assertFalse(any("drafting_fetch" in script for script in scripts))
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.layout.dflash2_dir.iterdir()}
        # The fixture marker writer below is deliberately a no-op on the second pass, like stock's cache hit.
        original = self.command
        def no_marker_rewrite(argv, **kwargs):
            if len(argv) > 2 and argv[2] == dflash2.TUNED_OK:
                return
            return original(argv, **kwargs)
        with patch.object(self, "command", side_effect=no_marker_rewrite), \
                patch.object(dflash2.shutil, "copyfile", side_effect=AssertionError("unexpected copy")):
            self.assertEqual(result, self.prepare())
        self.assertEqual(before, {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                                  for path in self.layout.dflash2_dir.iterdir()})

    def test_tuned_download_and_copy_are_deeply_verified(self):
        self.enable_tuned()
        download = self.layout.dflash2_tuned_download
        payload = download.read_bytes()
        common.verify_file(download, len(payload), self.pin["tuned"]["sha256"], source="fixture", log=lambda _: None)
        stamp = download.stat()
        download.write_bytes(b"x" * len(payload))
        os.utime(download, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaises(common.IntegrityError):
            self.prepare()
        download.write_bytes(payload)
        def wrong_copy(_src, dest):
            Path(dest).write_bytes(b"x" * len(payload))
        with patch.object(dflash2.shutil, "copyfile", side_effect=wrong_copy), \
                self.assertRaisesRegex(common.IntegrityError, "tuned copy differs"):
            self.prepare()
        self.assertFalse((self.layout.dflash2_dir / dflash2.TUNED_NAME).exists())
        self.assertFalse(list(self.layout.dflash2_dir.glob("*.partial")))

    def test_tuned_marker_must_exist_and_bind_the_final_stat_and_digest(self):
        self.enable_tuned()
        original = self.command
        target = self.layout.dflash2_dir / dflash2.TUNED_NAME
        for marker in (None, {}, {"size": 1, "mtime_ns": 1, "sha256": "0" * 64}):
            def bad_marker(argv, **kwargs):
                if len(argv) > 2 and argv[2] == dflash2.TUNED_OK:
                    if marker is not None:
                        common.atomic_write_json(target.with_name(target.name + ".ok"), marker)
                    return
                return original(argv, **kwargs)
            with self.subTest(marker=marker), patch.object(self, "command", side_effect=bad_marker), \
                    self.assertRaisesRegex(common.IntegrityError, "tuned_ok marker is absent or stale"):
                self.prepare()

    def test_tuned_license_sources_and_copies_must_match_the_pins(self):
        self.enable_tuned()
        source = self.layout.strata / dflash2.TUNED_LICENSE_FOLDER / "LICENSE"
        original = source.read_bytes()
        source.write_bytes(b"changed licence")
        with self.assertRaisesRegex(common.IntegrityError, "licence source differs"):
            self.prepare()
        source.write_bytes(original)
        copyfile = dflash2.shutil.copyfile
        def bad_license_copy(src, dest):
            if Path(src).name == "LICENSE":
                Path(dest).write_bytes(b"wrong licence copy")
            else:
                copyfile(src, dest)
        with patch.object(dflash2.shutil, "copyfile", side_effect=bad_license_copy), \
                self.assertRaisesRegex(common.IntegrityError, "licence copy differs"):
            self.prepare()
        self.assertFalse(list(self.layout.dflash2_dir.glob("*.partial")))

    def test_tuned_pin_still_refuses_bf16_and_feed_miss_files(self):
        self.enable_tuned()
        for name in (dflash2.TUNED_BF16_NAME, dflash2.TUNED_BF16_NAME + ".ok", ".tuned-feed-miss"):
            target = self.layout.dflash2_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"foreign")
            with self.subTest(name=name), self.assertRaisesRegex(common.IntegrityError, "this profile does not pin"):
                self.prepare()
            target.unlink()
        self.assertEqual([], self.calls)

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
            expected = {"STRATA_NO_ACQUIRE": "1"}
            if self.layout.profile.pins_runtime_dir:
                expected["STRATA_RUNTIME_DIR"] = str(self.layout.strata_runtime.resolve())
            self.assertEqual(expected,
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

    def test_standard_preparation_refuses_a_stray_tuned_pack_before_stock_runs(self):
        target = self.layout.dflash2_dir / dflash2.TUNED_NAME
        target.parent.mkdir(parents=True)
        target.write_bytes(b"unrecorded tuned pack")
        with self.assertRaisesRegex(common.IntegrityError, "this profile does not pin"):
            self.prepare()
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

    def pin_confidence(self):
        self.layout.profile.data["strata"].update(
            engine_version="0.1.59", drafting_args={"--draft-conf": "0.5"},
            engine_component=drafting_args_data()["strata"]["engine_component"])
        self.cfg["args_written"] = list(self.cfg["args"])

    def test_carried_user_args_must_equal_the_pin_on_reinstall(self):
        self.pin_confidence()
        self.cfg["user_args"] = ["--draft-conf", "0.5"]
        self.write_config()
        install.check_setup_stamp(self.layout)
        for value in ([], None, ["--draft-conf", "0.35"], ["--draft-conf", "0.5", "--spec", "8"]):
            self.cfg["user_args"] = value
            self.write_config()
            with self.subTest(value=value), self.assertRaisesRegex(install.InstallError, "carried user options"):
                install.check_setup_stamp(self.layout)
        self.cfg["user_args"] = ["--draft-conf", "0.5"]
        del self.layout.profile.data["strata"]["drafting_args"]
        self.write_config()
        with self.assertRaisesRegex(install.InstallError, "carried user options"):
            install.check_setup_stamp(self.layout)

    def test_user_args_writer_is_idempotent_and_never_restamps_args(self):
        self.pin_confidence()
        self.write_config()
        before = copy.deepcopy(self.cfg)
        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
            for _ in range(2):
                install.apply_drafting_args(self.layout, log=lambda _: None)
                self.assertEqual(before | {"user_args": ["--draft-conf", "0.5"]},
                                 common.read_json(self.layout.strata_config))
            self.cfg["user_args"] = ["--draft-conf", "0.35"]
            self.write_config()
            with self.assertRaises(install.InstallError):
                install.apply_drafting_args(self.layout, log=lambda _: None)
        self.assertEqual(self.cfg, common.read_json(self.layout.strata_config))
        del self.layout.profile.data["strata"]["drafting_args"]
        with patch.object(install, "run") as run:
            install.apply_drafting_args(self.layout, log=lambda _: None)
        run.assert_not_called()

    def test_generated_user_args_are_required_exactly_for_a_pin(self):
        self.pin_confidence()
        self.apply()
        for value in (None, ["--draft-conf", "0.35"]):
            if value is None:
                self.cfg.pop("user_args", None)
            else:
                self.cfg["user_args"] = value
            with self.subTest(value=value), self.assertRaisesRegex(install.InstallError, "user_args"):
                self.verify()
        self.cfg["user_args"] = ["--draft-conf", "0.5"]
        self.assertEqual(self.cfg, self.verify())
        del self.layout.profile.data["strata"]["drafting_args"]
        with self.assertRaisesRegex(install.InstallError, "unexpected config keys"):
            self.verify()

    def test_user_args_merge_source_is_bound_only_for_a_pin(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.59"
        before = install.runtime_sources(self.layout.profile)
        self.assertNotIn("strata_control/user_args.py", before)
        self.pin_confidence()
        self.assertEqual((*before, "strata_control/user_args.py"), install.runtime_sources(self.layout.profile))

    def test_install_writes_the_pin_after_drafting_before_preparing_the_pack(self):
        self.pin_confidence()
        calls = []
        with ExitStack() as stack:
            for name in ("stage_engine", "stage_llama", "mtp_pinned", "install_python", "run_setup",
                         "check_setup_stamp", "apply_calibration", "apply_stock_tips", "apply_pipeline_windows",
                         "apply_ple_io", "apply_batch_mtp", "apply_trim_stage_weights", "apply_kv_grow",
                         "apply_engine_env", "freeze_shared_settings", "engine_build", "runtime_identity"):
                stack.enter_context(patch.object(install, name, return_value={}))
            stack.enter_context(patch.object(install, "checkout_strata", return_value="a" * 40))
            stack.enter_context(patch.object(install.fetch_mod, "fetch"))
            stack.enter_context(patch.object(install, "verify_generated", return_value=self.cfg))
            run = stack.enter_context(patch.object(install, "run", side_effect=lambda argv, **_: calls.append(argv)))
            stack.enter_context(patch.object(dflash2, "prepare", side_effect=lambda *a, **k: calls.append("prepare")))
            install.install(self.layout, log=lambda _: None)
        self.assertEqual([install.APPLY_DRAFTING, dsv41.APPLY_USER_ARGS], [call.args[0][2] for call in run.call_args_list])
        self.assertEqual(["--draft-conf", "0.5"], json.loads(calls[1][-1]))
        self.assertEqual("prepare", calls[2])

    def test_runtime_identity_binds_every_prepared_file(self):
        for relative in ("engine/strata.exe", *start_path_sources(self.layout.profile.data["strata"]["engine_version"])):
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
    BATCH_ON = ("strata generate: STRATA_BATCH_DF2: 4 slot drafters on CUDA2 "
                "(256 MiB of private K/V ring and buffers each, sharing the solo drafter's pack); "
                "10.25 GiB free there\n")
    BATCH_READY = ("strata serve: STRATA_BATCH_DF2: 4 slot drafters ready "
                   "(batch windows carry each slot's token and its spare-row drafts)\n")

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.layout = Layout(Path(temp.name), Profile(Path("profiles/fixture.json"), variant_data()))
        self.engine = (f"strata serve: DFlash2 drafter on ({self.layout.dflash2_dir / dflash2.CONVERTED_NAME}, "
                       "graphs captured in 100 ms); windows up to 8 tokens; no MTP layer is loaded "
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

    def use_batch_slots(self):
        self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, slot_variant_data()))
        self.SERVER = self.SERVER.replace("0.35", "0.5")
        self.engine = self.engine.split("; layer split:", 1)[0] + "\n"

    def test_batch_slot_drafters_are_required_and_recorded_from_the_engine_interval(self):
        self.use_batch_slots()
        base = self.START + self.SELECTOR + self.engine
        observed = self.capture(engine=base + self.BATCH_ON + self.BATCH_READY,
                                prefix=self.BATCH_ON + self.BATCH_READY)
        self.assertEqual({"count": 4, "cuda": 2, "mib_each": 256,
                          "on_line": self.BATCH_ON.strip(), "ready_line": self.BATCH_READY.strip()},
                         observed["slot_drafters"])

    def test_tuned_start_requires_its_pack_resident_confidence_selector_and_slot_drafters(self):
        self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, tuned_variant_data()))
        self.engine = (self.engine.split("; layer split:", 1)[0]
                       .replace(dflash2.CONVERTED_NAME, dflash2.TUNED_NAME).replace("up to 8", "up to 6") + "\n")
        base = self.START + self.SELECTOR + self.engine + self.BATCH_ON + self.BATCH_READY
        observed = self.capture(engine=base)
        self.assertEqual("tuned", observed["pack_kind"])
        self.assertEqual(dflash2.TUNED_SHA256, observed["pack_sha256"])
        self.assertEqual("data/dflash2/" + dflash2.TUNED_NAME, observed["pack"])
        self.assertEqual(4, observed["slot_drafters"]["count"])
        for server, engine in (
            (self.SERVER, base.replace(dflash2.TUNED_NAME, dflash2.CONVERTED_NAME)),
            (self.SERVER.replace("0.35", "0.5"), base),
            (self.SERVER, base.replace(self.SELECTOR, "")),
            (self.SERVER, base.replace(self.BATCH_ON, "")),
            (self.SERVER, base.replace(self.BATCH_READY, "")),
        ):
            with self.subTest(server=server, engine=engine), self.assertRaises(lifecycle.LifecycleError):
                self.capture(server=server, engine=engine)
        del self.layout.profile.data["model"]["dflash2_source"]["tuned"]
        with self.assertRaisesRegex(lifecycle.LifecycleError, "runtime pack path differs"):
            self.capture(engine=base)
        observed = self.capture(engine=base.replace(dflash2.TUNED_NAME, dflash2.CONVERTED_NAME))
        self.assertEqual("standard", observed["pack_kind"])
        self.assertEqual(dflash2.CONVERTED_SHA256, observed["pack_sha256"])

    def test_blackwell_window_and_tuned_confidence_follow_the_engine_and_card_class(self):
        for version in ("0.1.58", "0.1.59"):
            for mib in (32768, 48_000_000_000 / 1024**2 - 1, 48_000_000_000 / 1024**2, 98304):
                for tuned in (False, True):
                    data = tuned_variant_data()
                    data["strata"]["engine_version"] = version
                    data["host"]["min_gpu_vram_mib"] = mib
                    if not tuned:
                        del data["model"]["dflash2_source"]["tuned"]
                    self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, data))
                    wide = version == "0.1.59" and mib * 1024**2 >= 48_000_000_000
                    window, confidence = (8 if wide else 6), ("0.55" if wide and tuned else "0.35")
                    runtime = dflash2.TUNED_NAME if tuned else dflash2.CONVERTED_NAME
                    engine = (self.START + self.SELECTOR
                              + f"strata serve: DFlash2 drafter on ({self.layout.dflash2_dir / runtime}, "
                              f"graphs captured in 100 ms); windows up to {window} tokens; "
                              "no MTP layer is loaded (--draft-fallback none)\n"
                              + self.BATCH_ON + self.BATCH_READY)
                    server = self.SERVER.replace("0.35", confidence)
                    with self.subTest(version=version, mib=mib, tuned=tuned):
                        observed = self.capture(server=server, engine=engine)
                        self.assertEqual(window, observed["window_tokens"])
                        self.assertEqual("tuned" if tuned else "standard", observed["pack_kind"])
                        with self.assertRaisesRegex(lifecycle.LifecycleError, "profile-specific window"):
                            self.capture(server=server, engine=engine.replace(
                                f"up to {window}", f"up to {6 if window == 8 else 8}"))
                        with self.assertRaisesRegex(lifecycle.LifecycleError, "profile-specific --draft-conf"):
                            self.capture(server=self.SERVER.replace("0.35", "0.35" if confidence == "0.55" else "0.55"),
                                         engine=engine)

    def test_new_engine_keeps_pair_window_eight_and_confidence_point_35(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.59"
        self.assertEqual(8, self.capture()["window_tokens"])
        with self.assertRaisesRegex(lifecycle.LifecycleError, "profile-specific --draft-conf"):
            self.capture(server=self.SERVER.replace("0.35", "0.55"))
        with self.assertRaisesRegex(lifecycle.LifecycleError, "profile-specific window"):
            self.capture(engine=(self.START + self.SELECTOR + self.engine).replace("up to 8", "up to 6"))

    def test_confidence_rule_and_regex_admit_only_stock_values(self):
        standard = tuned_variant_data()
        del standard["model"]["dflash2_source"]["tuned"]
        standard["strata"]["engine_version"] = "0.1.59"
        self.assertEqual(frozenset({"0.35", "0.5", "0.7", "0.8"}), dflash2.stock_draft_confs(standard))
        pair = variant_data()
        pair["strata"]["engine_version"] = "0.1.59"
        self.assertEqual(frozenset({"0.35"}), dflash2.stock_draft_confs(pair))
        for confidence in (*dflash2.DRAFT_CONF_VALUES, "0.6"):
            line = self.SERVER.strip().replace("0.35", confidence)
            with self.subTest(confidence=confidence):
                self.assertEqual(confidence != "0.6", lifecycle.DFLASH2_SERVER_ON.fullmatch(line) is not None)

    def test_missing_repeated_malformed_or_wrong_count_batch_lines_are_refused(self):
        self.use_batch_slots()
        base = self.START + self.SELECTOR + self.engine
        pairs = [
            "", self.BATCH_ON, self.BATCH_READY, self.BATCH_ON * 2 + self.BATCH_READY,
            self.BATCH_ON + self.BATCH_READY * 2,
            self.BATCH_ON.replace("4 slot", "3 slot") + self.BATCH_READY,
            self.BATCH_ON + self.BATCH_READY.replace("4 slot", "3 slot"),
            self.BATCH_ON.replace("10.25", "10..25") + self.BATCH_READY,
            "prefix " + self.BATCH_ON + self.BATCH_READY,
            self.BATCH_ON.rstrip() + " trailing\n" + self.BATCH_READY,
            self.BATCH_ON + self.BATCH_READY.rstrip() + " trailing\n",
            self.BATCH_ON + self.BATCH_READY + "strata serve: STRATA_BATCH_DF2: unknown\n",
        ]
        for lines in pairs:
            with self.subTest(lines=lines), self.assertRaises(lifecycle.LifecycleError):
                self.capture(engine=base + lines, prefix=self.BATCH_ON + self.BATCH_READY)

    def test_every_batch_slot_off_warning_and_per_slot_failure_is_refused_in_either_stream(self):
        self.use_batch_slots()
        base = self.START + self.SELECTOR + self.engine + self.BATCH_ON + self.BATCH_READY
        failures = [
            "strata generate: WARNING: STRATA_BATCH_DF2 is off: DFlash2 is not running",
            "strata serve: STRATA_BATCH_DF2 is off: DFlash2 did not start",
            "strata generate: WARNING: STRATA_BATCH_DF2 (the slots' DFlash2 drafts) is off: it needs --serve",
            "strata generate: STRATA_BATCH_DF2: slot 2 drafter: out of memory",
            "strata serve: STRATA_BATCH_DF2: slot 2: cannot bind",
            "strata serve: STRATA_BATCH_DF2: slot 2: cannot prepare",
        ]
        for line in failures:
            for stream in ("server", "engine"):
                with self.subTest(line=line, stream=stream), self.assertRaises(lifecycle.LifecycleError):
                    self.capture(server=self.SERVER + (line + "\n" if stream == "server" else ""),
                                 engine=base + (line + "\n" if stream == "engine" else ""))

    def test_slot_lines_in_the_server_stream_or_on_a_no_slot_profile_are_refused(self):
        base = self.START + self.SELECTOR + self.engine
        for stream in ("server", "engine"):
            for lines in (self.BATCH_ON, self.BATCH_READY, self.BATCH_ON + self.BATCH_READY):
                with self.subTest(slots=None, stream=stream, lines=lines), self.assertRaises(lifecycle.LifecycleError):
                    self.capture(server=self.SERVER + (lines if stream == "server" else ""),
                                 engine=base + (lines if stream == "engine" else ""))
        self.use_batch_slots()
        base = self.START + self.SELECTOR + self.engine + self.BATCH_ON + self.BATCH_READY
        for lines in (self.BATCH_ON, self.BATCH_READY):
            with self.subTest(slots=4, lines=lines), self.assertRaises(lifecycle.LifecycleError):
                self.capture(server=self.SERVER + lines, engine=base)

    def test_complete_on_set_is_bound_to_this_interval_and_the_runtime_pack(self):
        observed = self.capture(prefix="[strata] Drafting: MTP (DFlash2 didn't start)\n")
        self.assertEqual("dflash2", observed["mode"])
        self.assertEqual(8, observed["window_tokens"])
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


class DFlash2PinsTests(unittest.TestCase):
    def setUp(self):
        from tests.unit.test_component_engine import NAME, members, write_archive

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = self.root / NAME
        self.members, self.write_archive = members, write_archive
        self.payload = b"\0".join((b"synthetic engine", dflash2.MARK_ON, dflash2.MARK_VOCAB, dflash2.MARK_SELQ4))
        self.artifact = write_archive(self.archive, members(payload={"strata.exe": self.payload}))
        self.metadata = {"sha": dflash2.REVISION, "cardData": {"license": "apache-2.0"}, "siblings": [
            {"rfilename": name, "size": size,
             **({"lfs": {"size": size, "sha256": sha}} if name.endswith(".safetensors") else {})}
            for name, size, sha in dflash2.FILES]}
        # Synthetic reviewed-module identities isolate the literal, HF and archive boundaries. Production digests
        # are exercised by the host-free source proof, not relaxed here to admit a modified stock module.
        names = ("REPO", "REVISION", "LICENSE", "FILES", "PACK_NAME", "PACK_BYTES", "PACK_SHA256",
                 "CONVERTED_NAME", "CONVERTED_BYTES", "CONVERTED_SHA256", "VOCAB_NAME", "FOLDER")
        self.sources = {
            "strata_control/drafting.py": "\n".join(f"{name} = {getattr(dflash2, name)!r}" for name in names),
            "strata_control/drafting_fetch.py": "offline_orchestration = 1",
            "tools/dflash2_pack.py": "offline_packer = 1",
        }
        self.review = copy.deepcopy(watch.SERVER_REVIEWS)
        self.review["0.2.10"]["modules"]["drafting"] = (
            "strata_control/drafting.py", watch.reviewed_hash(ast.parse(self.sources["strata_control/drafting.py"])))

    def pins(self, *, allow_github=False, server_key="0.2.10", strata_tag="v0.2.10"):
        from tests.unit.test_upstream_watch import FixtureTransport

        url = f"{watch.HF}/api/models/{dflash2.REPO}/revision/{dflash2.REVISION}?blobs=true"
        api = watch.API(FixtureTransport({url: (self.metadata, {})}), allow_github=allow_github)
        def source(_src, operation, spec, **kw):
            self.assertEqual("show", operation)
            path = spec.split(":", 1)[1]
            return b"shipped vocabulary" if path == "data/draft_vocab.bin" else self.sources[path]
        with patch.object(watch, "git", side_effect=source), \
                patch.object(watch, "SERVER_REVIEWS", self.review), \
                patch.object(watch, "DRAFTING_FETCH_REVIEWS", {
                    key: watch.reviewed_hash(ast.parse(self.sources["strata_control/drafting_fetch.py"]))
                    for key in watch.DRAFTING_FETCH_REVIEWS}), \
                patch.object(watch, "DFLASH2_PACK_TOOL_0_2_10",
                             watch.reviewed_hash(ast.parse(self.sources["tools/dflash2_pack.py"]))):
            return watch.dflash2_pins(api, None, "a" * 40, self.archive, self.artifact,
                                     server_key=server_key, strata_tag=strata_tag)

    def test_v0211_pins_use_the_selected_reviews_stock_drafting_module(self):
        self.sources["strata_control/drafting.py"] = (
            Path(__file__).resolve().parents[2] / "tests/fixtures/strata_0_2_11_drafting.py").read_text()
        pins = self.pins(server_key="0.2.11", strata_tag="v0.2.11")
        self.assertTrue(all(entry["sha256_source"].startswith("Stock v0.2.11 drafting.FILES;")
                            for entry in pins["files"]))
        with self.assertRaisesRegex(watch.Incomplete, "stock DFlash2 module changed"):
            self.pins(server_key="0.2.10", strata_tag="v0.2.10")

    def test_pins_cross_check_hf_without_github_and_select_the_binarys_runtime_pack(self):
        pins = self.pins()
        self.assertEqual([], dflash2.validate_source({"dflash2_source": pins}))
        self.assertEqual("selq4", pins["runtime_pack"])
        self.assertEqual(common.sha256_bytes(b"shipped vocabulary"), pins["vocab_sha256"])
        self.artifact = self.write_archive(self.archive, self.members(payload={
            "strata.exe": self.payload.replace(dflash2.MARK_SELQ4, b"no selector")}))
        self.assertEqual("q4_0", self.pins()["runtime_pack"])

    def test_stock_module_and_literal_mismatches_refuse(self):
        old = self.sources["strata_control/drafting.py"]
        self.sources["strata_control/drafting.py"] = old.replace(dflash2.REVISION, "0" * 40)
        with self.assertRaises(watch.Incomplete):
            self.pins()
        # Even an independently re-reviewed module cannot silently change the integration's artifact constants.
        self.review["0.2.10"]["modules"]["drafting"] = (
            "strata_control/drafting.py", watch.reviewed_hash(ast.parse(self.sources["strata_control/drafting.py"])))
        with self.assertRaises(watch.Incomplete):
            self.pins()

    def test_hf_identity_size_license_and_tensor_hash_mismatches_refuse(self):
        original = copy.deepcopy(self.metadata)
        for path, value in [
            (("sha",), "0" * 40), (("cardData", "license"), "mit"),
            (("siblings", 0, "size"), 12), (("siblings", 1, "lfs", "sha256"), "0" * 64),
            (("siblings", 1, "lfs", "size"), 12), (("siblings",), []),
        ]:
            self.metadata = copy.deepcopy(original)
            target = self.metadata
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(watch.Incomplete):
                self.pins()

    def test_required_engine_markers_cannot_come_from_another_archive_member(self):
        for marker in (dflash2.MARK_ON, dflash2.MARK_VOCAB):
            self.artifact = self.write_archive(self.archive, self.members(payload={
                "strata.exe": self.payload.replace(marker, b"missing"), "strata_kq.dll": marker}))
            with self.subTest(marker=marker), self.assertRaises(watch.Incomplete):
                self.pins()

    def test_archive_scan_is_read_only_pin_checked_and_handles_chunk_boundaries(self):
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        with patch.object(engine_component, "CHUNK", 7):
            found = engine_component.archive_markers(
                self.archive, self.artifact, (dflash2.MARK_ON, dflash2.MARK_VOCAB, b"absent"))
        self.assertEqual({dflash2.MARK_ON: True, dflash2.MARK_VOCAB: True, b"absent": False}, found)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})
        for field, value in (("sha256", "0" * 64), ("bytes", self.artifact["bytes"] + 1)):
            with self.subTest(field=field), self.assertRaises(common.IntegrityError):
                engine_component.archive_markers(self.archive, {**self.artifact, field: value}, (dflash2.MARK_ON,))

    def test_campaign_accepts_the_short_pair_variant_id_and_prefers_the_current_dflash2_family(self):
        before = ("win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect"
                  "-env86g-parking-strata0.2.10-omp18.16.0")
        after = before.replace("-pw2-", "-df2-")
        self.assertEqual(119, len(after))
        self.assertTrue(campaign.lane_variant(before, after))
        # Owner 2026-11-03: DFlash2 is the pair's current profile, so at the same release it outranks env86g and a
        # later campaign names it as the pair's predecessor.
        families = next(families for families, _, _ in campaign.LANES if before.split("-strata")[0] in families)
        self.assertGreater(families.index(after.split("-strata")[0]), families.index(before.split("-strata")[0]))
