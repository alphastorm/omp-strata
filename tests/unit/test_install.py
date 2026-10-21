"""Pinned stock generated configs (Unsloth budget, pinned calibration) and pre-placed four-shard fetch boundaries;
no host or network."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

from omp_strata import common, engine_component, fetch, install
from omp_strata.layout import Layout
from omp_strata.profile import Profile, load
from scripts import upstream_watch as watch
from tests.fixtures import strata_0_1_36_calibrate as stock_calibration
from tests.unit.test_component_engine import members as archive_members, write_archive
from tests.unit.test_profile import calibrated_multi_gpu_data, component_data, multi_gpu_data

REPO = Path(__file__).resolve().parents[2]
PROFILE = REPO / "profiles/win11-rtx3090-ud-q4kxl-131k-strata0.1.36-omp18.4.12.json"
CALIBRATED = REPO / "profiles/win11-rtx3090-iq3s-131k-calibrated-strata0.1.36-omp18.4.12.json"
PRO = REPO / "profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json"


class GeneratedConfig(unittest.TestCase):
    """A root holding the config stock setup (SOURCE's release) writes for the profile's model on the PLAN host,
    before any later step."""
    PROFILE = PROFILE
    SOURCE = "tests/fixtures/strata_0_1_36_plan.py"
    PLAN = {"ram": 127.69, "vram": 24}

    def profile(self) -> Profile:
        return load(self.PROFILE)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.layout = Layout(Path(self.temp.name) / "integration", self.profile())
        self.layout.strata.mkdir(parents=True)
        self.pack = self.layout.data / "packs" / self.layout.strata_config.stem.removeprefix("strata-")
        self.pack.mkdir(parents=True)
        self.mtp = self.layout.data / "mtp/rt"
        self.mtp.mkdir(parents=True)
        (self.mtp / "experts.bin").write_bytes(b"separate stock draft experts")
        source = (REPO / self.SOURCE).read_text()
        original = watch.pure_exec
        namespace = {}

        def in_root(nodes, ns):
            if any(watch.assigned(node, "args") for node in nodes):
                shards = [self.layout.model_file(f) for f in self.layout.profile.data["model"]["files"]]
                ns.update(ROOT=self.layout.strata, eng=self.layout.strata / "engine", pack=self.pack,
                          rt=self.mtp, shards=shards, ple=shards[1])
            original(nodes, ns)
            namespace.update(ns)

        s = self.layout.profile.data["strata"]["setup_args"]
        with patch.object(watch, "pure_exec", side_effect=in_root):
            watch.stock_plan(source, family=s["family"], model=s["model"], context=s["context"], **self.PLAN)
        self.cfg = namespace["cfg"]
        # The real stock tag determines the filename, not Layout's family map.
        self.config_path = self.layout.strata / f"strata-{namespace['tag'].lower()}.json"
        self.write_config()

    def write_config(self):
        self.config_path.write_text(json.dumps(self.cfg))

    def verify(self):
        with patch.object(install, "host_platform", return_value="windows-x64"):
            return install.verify_generated(self.layout)


class SlotsAndTipsInstall(GeneratedConfig):
    """Stock v0.1.40.3 setup `--parallel 4` on the PRO host writes its batch slots; the profile's pinned stock
    recommendations are added to the config's args after it."""
    SOURCE = "tests/fixtures/strata_0_1_40_3_plan.py"
    PLAN = {"ram": 191.69, "vram": 97000 / 1024, "cpu_cores": (8, 16), "parallel": 4}
    TIPS = {"--conversation-cache-mib": "8192", "--prefill": "auto:32768"}

    def profile(self):
        data = copy.deepcopy(load(PRO).data)
        data["strata"]["setup_args"]["parallel"] = 4
        data["strata"]["stock_tips"] = self.TIPS
        data["strata"]["expected_engine_flags"] = watch.tipped_flags(data["strata"]["expected_engine_flags"], self.TIPS)
        return Profile(PRO, data)

    def apply_tips(self):
        (self.layout.strata / "setup.py").write_text(stock_calibration.SETUP)  # stock write_config, same in v0.1.40.3
        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
            install.apply_stock_tips(self.layout, log=lambda _: None)

    def test_stock_tips_step_yields_the_pinned_flags_once(self):
        with self.assertRaisesRegex(install.InstallError, r"--conversation-cache-mib: None != expected '8192'"):
            self.verify()
        self.apply_tips()
        args = self.verify()["args"]
        self.assertEqual("auto:32768", common.flag_pairs(args)["--prefill"])
        self.assertEqual(1, args.count("--prefill"))
        self.assertEqual(["--conversation-cache-mib", "8192"], args[-2:])

    def test_slots_only_as_the_profile_pins_them(self):
        self.apply_tips()
        self.cfg = json.loads(self.config_path.read_text())
        self.assertEqual(4, self.verify()["parallel"])
        for value in (None, 2, 8):
            with self.subTest(parallel=value):
                self.config_path.write_text(json.dumps({k: v for k, v in self.cfg.items() if k != "parallel"}
                                                       | ({"parallel": value} if value else {})))
                with self.assertRaisesRegex(install.InstallError, f"parallel {value!r} != the profile's 4"):
                    self.verify()
        self.write_config()
        self.layout = Layout(self.layout.root, load(PRO))  # a profile without slots refuses stock's "parallel"
        with self.assertRaisesRegex(install.InstallError, "parallel 4 != the profile's None"):
            self.verify()


class BudgetInstall(GeneratedConfig):
    def test_stock_config_accepts_mapped_gguf_and_separate_mtp_experts(self):
        cfg = self.verify()
        self.assertEqual("71", common.flag_pairs(cfg["args"])["--resident-budget-gib"])
        self.assertNotIn("--ple-gguf", cfg["args"])
        self.assertEqual(install.GENERATED_CONFIG_KEYS, set(cfg))

    def test_wrong_budget_or_foreign_native_shard_is_rejected(self):
        original = copy.deepcopy(self.cfg)
        for flag, value, error in (("--resident-budget-gib", "40", "engine flag --resident-budget-gib"),
                                   ("--native", str(Path(self.temp.name) / "foreign.gguf"), "pinned first shard"),
                                   ("--native", str(self.layout.model_file(self.layout.profile.data["model"]["files"][1])),
                                    "pinned first shard"),
                                   ("--pack", str(Path(self.temp.name) / "foreign-pack"), "inside the integration root")):
            with self.subTest(flag=flag, value=value):
                self.cfg = copy.deepcopy(original)
                self.cfg["args"][self.cfg["args"].index(flag) + 1] = value
                self.write_config()
                with self.assertRaisesRegex(install.InstallError, error):
                    self.verify()

    def test_experts_bin_and_low_ram_modes_cannot_replace_the_mapped_gguf(self):
        original = copy.deepcopy(self.cfg)
        for flag in ("--experts", "--mmap-experts", "--resident-experts"):
            with self.subTest(flag=flag):
                self.cfg = copy.deepcopy(original)
                self.cfg["args"].extend([flag, str(self.pack / "experts.bin")] if flag == "--experts" else [flag])
                self.write_config()
                with self.assertRaises(install.InstallError):
                    self.verify()
        self.cfg = original
        self.write_config()
        (self.pack / "experts.bin").write_bytes(b"not the mapped native experts")
        with self.assertRaisesRegex(install.InstallError, "must not contain experts.bin"):
            self.verify()

    def test_unreviewed_generated_setting_is_rejected(self):
        self.cfg["lazy_load"] = True
        self.write_config()
        with self.assertRaisesRegex(install.InstallError, "unexpected config keys"):
            self.verify()


class CalibratedInstall(GeneratedConfig):
    """Stock setup writes the uncalibrated config; the profile's pinned stock calibration must be applied to it."""
    PROFILE = CALIBRATED

    def apply(self):
        (self.layout.strata / "tools").mkdir()
        (self.layout.strata / "tools/calibrate.py").write_text(stock_calibration.CALIBRATE)
        (self.layout.strata / "setup.py").write_text(stock_calibration.SETUP)
        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
            install.apply_calibration(self.layout, log=lambda _: None)

    def test_uncalibrated_stock_config_is_refused(self):
        with self.assertRaisesRegex(install.InstallError, r"--pcie-frac: None != expected '0.20'"):
            self.verify()

    def test_stock_calibration_step_yields_the_pinned_flags(self):
        self.apply()
        args = self.verify()["args"]
        self.assertEqual(["--pcie-frac", "0.20", "--spec-min-p", "0.70"], args[-4:])
        self.assertEqual(1, args.count("--spec-min-p"))


class MultiGpuInstall(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.layout = Layout(Path(temp.name), Profile(PRO, multi_gpu_data()))
        self.layout.strata.mkdir(parents=True)
        p = self.layout.profile.data
        args = list(p["strata"]["expected_engine_flags"])
        for flag, path in (("--pack", self.layout.data / "pack"), ("--native", self.layout.model_file(p["model"]["files"][0])),
                           ("--expert-profile", self.layout.strata / "data/expert-profile.json"),
                           ("--mtp", self.layout.data / "mtp"), ("--ple-gguf", self.layout.data / "ple.gguf")):
            args.extend([flag, str(path)])
        self.cfg = {"args": args, "cwd": str(self.layout.strata), "exe": str(self.layout.strata / "engine/strata.exe"),
                    "gpu": [1, 0], "gpus_asked": True, "host": p["server"]["listen_host"], "lib_dirs": [],
                    "log": "server.log", "model_name": p["strata"]["model_name"], "port": p["server"]["port"],
                    "tokenizer": str(self.layout.data / "tokenizer"), "layer_split": "auto"}
        if "parallel" in p["strata"]["setup_args"]:
            self.cfg["parallel"] = p["strata"]["setup_args"]["parallel"]

    def verify(self, cfg):
        self.layout.strata_config.write_text(json.dumps(cfg))
        with patch.object(install, "host_platform", return_value="windows-x64"):
            return install.verify_generated(self.layout)

    def test_pipeline_windows_step_replaces_or_adds_the_pinned_flag_once(self):
        data = copy.deepcopy(self.layout.profile.data)
        data["strata"]["setup_args"].pop("parallel", None)
        data["strata"]["pipeline_windows"] = 2
        data["strata"]["expected_engine_flags"].extend(["--pipeline-windows", "2"])
        self.layout = Layout(self.layout.root, Profile(PRO, data))
        self.cfg.pop("parallel", None)
        (self.layout.strata / "setup.py").write_text(stock_calibration.SETUP)
        with self.assertRaisesRegex(install.InstallError, r"--pipeline-windows: None != expected '2'"):
            self.verify(self.cfg)
        for initial in ([], ["--pipeline-windows", "1"]):
            with self.subTest(initial=initial):
                cfg = copy.deepcopy(self.cfg)
                cfg["args"].extend(initial)
                self.layout.strata_config.write_text(json.dumps(cfg))
                with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
                    for _ in range(2):
                        install.apply_pipeline_windows(self.layout, log=lambda _: None)
                        applied = json.loads(self.layout.strata_config.read_text())
                        self.assertEqual(applied, self.verify(applied))
                        self.assertEqual(1, applied["args"].count("--pipeline-windows"))
                        self.assertEqual("2", common.flag_pairs(applied["args"])["--pipeline-windows"])
                        self.assertEqual({k: v for k, v in cfg.items() if k != "args"},
                                         {k: v for k, v in applied.items() if k != "args"})
                duplicate = copy.deepcopy(applied)
                duplicate["args"].extend(["--pipeline-windows", "2"])
                with self.assertRaisesRegex(install.InstallError, "--pipeline-windows.*exactly once"):
                    self.verify(duplicate)

    def test_stock_calibration_preserves_split_and_accepts_only_pinned_flags(self):
        data = calibrated_multi_gpu_data()
        data["strata"]["setup_args"]["parallel"] = 4
        tips = {"--conversation-cache-mib": "8192", "--prefill": "auto:32768"}
        data["strata"]["stock_tips"] = tips
        data["strata"]["expected_engine_flags"] = watch.tipped_flags(data["strata"]["expected_engine_flags"], tips)
        self.layout = Layout(self.layout.root, Profile(PRO, data))
        self.cfg["parallel"] = 4
        self.layout.strata_config.write_text(json.dumps(self.cfg))
        # v0.1.42 keeps with_arg/apply/write_config verbatim and extends DEFAULTS with the expert-tier sweep.
        calibration = stock_calibration.CALIBRATE.replace(
            '"--pool-workers": None}',
            '"--pool-workers": None, "--adapt-every": None, "--adapt-swaps": None, "--adapt-decay": None}')
        (self.layout.strata / "tools").mkdir()
        (self.layout.strata / "tools/calibrate.py").write_text(calibration)
        (self.layout.strata / "setup.py").write_text(stock_calibration.SETUP)
        with self.assertRaises(install.InstallError):
            self.verify(self.cfg)
        with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
            install.apply_calibration(self.layout, log=lambda _: None)
            install.apply_stock_tips(self.layout, log=lambda _: None)
        cfg = json.loads(self.layout.strata_config.read_text())
        self.assertEqual(cfg, self.verify(cfg))
        self.assertEqual({k: v for k, v in self.cfg.items() if k != "args"},
                         {k: v for k, v in cfg.items() if k != "args"})
        pairs = common.flag_pairs(cfg["args"])
        for flag, value in data["strata"]["calibration"]["settings"].items():
            self.assertEqual(value, pairs[flag])
            changed = copy.deepcopy(cfg)
            changed["args"][changed["args"].index(flag) + 1] = "999"
            with self.subTest(flag=flag), self.assertRaisesRegex(install.InstallError, "engine flag " + flag):
                self.verify(changed)

    def test_setup_argv_and_exact_profile_keys(self):
        argv = install.setup_argv(self.layout)
        self.assertEqual("1,0", argv[argv.index("--gpus") + 1])
        self.assertEqual("auto", argv[argv.index("--layer-split") + 1])
        self.assertNotIn("--gpu", argv)
        self.assertEqual(self.cfg, self.verify(self.cfg))
        setup = self.layout.profile.data["strata"]["setup_args"]
        self.assertEqual(set(self.cfg), install.generated_config_keys(setup))
        self.assertEqual(install.GENERATED_CONFIG_KEYS, install.generated_config_keys({"gpu": 0}))
        self.assertEqual(install.GENERATED_CONFIG_KEYS | {"layer_split"}, install.generated_config_keys({"gpus": [1, 0]}))

    def test_missing_or_extra_generated_keys_fail(self):
        for key in self.cfg:
            with self.subTest(missing=key):
                cfg = dict(self.cfg)
                del cfg[key]
                with self.assertRaises(install.InstallError):
                    self.verify(cfg)
        for key in ("gpu_order", "env", "replicas", "peer_device", "helper_cache"):
            with self.subTest(extra=key), self.assertRaises(install.InstallError):
                self.verify(self.cfg | {key: {}})

    def test_selection_order_types_and_split_are_exact(self):
        for key, value in (("gpu", [0, 1]), ("gpu", [True, 0]), ("gpu", 1), ("gpus_asked", 1),
                           ("gpus_asked", False), ("layer_split", "24"), ("port", 1)):
            with self.subTest(key=key, value=value), self.assertRaises(install.InstallError):
                self.verify(self.cfg | {key: value})

    def test_single_selection_split_and_parallel_absence(self):
        p = self.layout.profile.data
        card = p["host"].pop("gpus")[0]
        p["host"].update({k: v for k, v in card.items() if k not in ("arch", "pci_bus_id")})
        setup = p["strata"]["setup_args"]
        setup.pop("gpus")
        setup.pop("layer_split")
        setup.pop("parallel", None)
        setup["gpu"] = 1
        cfg = dict(self.cfg, gpu=1)
        cfg.pop("layer_split")
        cfg.pop("parallel", None)
        self.assertEqual(cfg, self.verify(cfg))
        argv = install.setup_argv(self.layout)
        self.assertEqual("1", argv[argv.index("--gpu") + 1])
        self.assertNotIn("--gpus", argv)
        for key, value in (("layer_split", "auto"), ("parallel", None)):
            with self.subTest(key=key), self.assertRaises(install.InstallError):
                self.verify(cfg | {key: value})

    def test_setup_environment_scrubs_ambient_tuning_but_keeps_explicit_internal_extra(self):
        ambient = {"STRATA_ARENA_PIN_GIB": "0", "Strata_Debug": "1", "CUDA_VISIBLE_DEVICES": "0",
                   "CUDA_DEVICE_ORDER": "FASTEST_FIRST", "STRATA_GGUF_PY": "ambient", "PATH": os.defpath}
        with patch.dict(os.environ, ambient, clear=True):
            env = install.build_env(self.layout, {"STRATA_GGUF_PY": "internal"})
        self.assertEqual({"STRATA_GGUF_PY": "internal"}, {k: v for k, v in env.items() if k.upper().startswith("STRATA_")})
        self.assertNotIn("CUDA_VISIBLE_DEVICES", env)
        self.assertNotIn("CUDA_DEVICE_ORDER", env)
        self.assertEqual(os.defpath, env["PATH"])


class PreplacedBudgetShards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        data = copy.deepcopy(load(PROFILE).data)
        self.payloads = [f"verified shard {i}".encode() for i in range(4)]
        for entry, payload in zip(data["model"]["files"], self.payloads):
            entry.update(bytes=len(payload), sha256=common.sha256_bytes(payload))
        self.layout = Layout(Path(self.temp.name), Profile(PROFILE, data))
        self.items = fetch.plan(self.layout, platform="windows-x64", only={"model"})
        for item, payload in zip(self.items, self.payloads):
            item.dest.parent.mkdir(parents=True, exist_ok=True)
            item.dest.write_bytes(payload)
        self.network = patch.object(common.urllib.request, "urlopen", side_effect=AssertionError("network not allowed"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_four_preplaced_shards_are_verified_and_reused_without_download_space(self):
        with patch.object(fetch.shutil, "disk_usage", return_value=type("Usage", (), {"free": 0})()):
            fetched = fetch.fetch(self.layout, platform="windows-x64", only={"model"}, log=lambda _: None)
        self.assertEqual(4, len(fetched))
        for item, payload in zip(fetched, self.payloads):
            self.assertEqual(self.layout.root / "models/unsloth-UD-Q4_K_XL", item.dest.parent)
            self.assertEqual(payload, item.dest.read_bytes())
            self.assertTrue(common.verified_ok(item.dest, item.bytes, item.sha256))

    def test_preplaced_file_with_wrong_size_or_digest_is_not_accepted(self):
        for payload in (b"short", b"X" * len(self.payloads[0])):
            with self.subTest(bytes=len(payload)):
                self.items[0].dest.write_bytes(payload)
                with self.assertRaises(common.IntegrityError):
                    fetch.fetch(self.layout, platform="windows-x64", only={"model"}, log=lambda _: None)


class EngineBuildLabel(unittest.TestCase):
    """Stock v0.1.40.1 ships v0.1.40's engine archive byte for byte, and its BUILD.json says 0.1.40."""

    def check(self, profile: str, build: dict) -> None:
        with tempfile.TemporaryDirectory() as temp:
            layout = Layout(Path(temp), load(REPO / "profiles" / f"{profile}.json"))
            (layout.strata / "engine").mkdir(parents=True)
            (layout.strata / "engine" / "BUILD.json").write_text(json.dumps(build))
            install.engine_build(layout)

    def test_a_hotfix_release_accepts_its_base_engine_build_and_nothing_else(self):
        hotfix, base = ("win11-rtxpro6000-iq3s-131k-strata0.1.40.1-omp18.7.0",
                        "win11-rtxpro6000-iq3s-131k-strata0.1.39-omp18.5.0")
        for profile, version in ((hotfix, "0.1.40"), (hotfix, "0.1.40.1"), (base, "0.1.39")):
            with self.subTest(accepted=(profile, version)):
                self.check(profile, {"version": version, "source": "release"})
        for profile, build in ((hotfix, {"version": "0.1.39", "source": "release"}),
                               (hotfix, {"version": "0.1.40", "source": "local"}),
                               (base, {"version": "0.1.39.1", "source": "release"}),
                               (base, {"version": "0.1.3", "source": "release"})):
            with self.subTest(refused=(profile, build)), self.assertRaisesRegex(install.InstallError, "is not release"):
                self.check(profile, build)


# Stock strata_control/user_args.stamp (v0.2.1), verbatim: setup and the app record the args they wrote.
USER_ARGS = '''
USER_KEY = "user_args"
WRITTEN_KEY = "args_written"


def stamp(cfg, user=None):
    if user is not None:
        if user:
            cfg[USER_KEY] = list(user)
        else:
            cfg.pop(USER_KEY, None)
    if isinstance(cfg.get("args"), list):
        cfg[WRITTEN_KEY] = list(cfg["args"])
'''
SETUP_CONSTANTS = '''
PY_PACKAGES = ["numpy"]
CUDA_WHEELS = ["nvidia-cublas==13.0.2.14"]
MIN_ENGINE = {min_engine!r}
LLAMA_CPP_COMMIT = "3cf03257f219afbe7334045ff7c6a06ac68c627d"
'''


class ComponentInstall(unittest.TestCase):
    """A v0.2.1 component engine staged where stock setup reuses it, and setup's own args record kept honest."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        data = component_data()
        self.layout = Layout(Path(temp.name) / "root", Profile(PRO, data))
        self.layout.engine_dir.mkdir(parents=True)
        artifact = write_archive(self.layout.engine_archive, archive_members())
        data["strata"]["artifacts"]["engine_archive"].update(bytes=artifact["bytes"], sha256=artifact["sha256"])
        data["strata"]["engine_component"] = engine_component.inspect_archive(self.layout.engine_archive, artifact)["pin"]
        self.layout.strata.mkdir(parents=True)
        self.write_setup((0, 1, 45))
        p = data
        args = list(p["strata"]["expected_engine_flags"])
        for flag, path in (("--pack", self.layout.data / "pack"), ("--native", self.layout.model_file(p["model"]["files"][0])),
                           ("--expert-profile", self.layout.strata / "data/expert-profile.json"),
                           ("--mtp", self.layout.data / "mtp"), ("--ple-gguf", self.layout.data / "ple.gguf")):
            args.extend([flag, str(path)])
        self.cfg = {"args": args, "args_written": list(args), "cwd": str(self.layout.strata),
                    "exe": str(self.layout.strata / "engine/strata.exe"), "gpu": p["strata"]["setup_args"]["gpu"],
                    "gpus_asked": True, "host": p["server"]["listen_host"], "lib_dirs": [], "log": "server.log",
                    "model_name": p["strata"]["model_name"], "port": p["server"]["port"],
                    "tokenizer": str(self.layout.data / "tokenizer")}
        if "parallel" in p["strata"]["setup_args"]:
            self.cfg["parallel"] = p["strata"]["setup_args"]["parallel"]

    def write_setup(self, min_engine):
        (self.layout.strata / "setup.py").write_text(stock_calibration.SETUP + SETUP_CONSTANTS.format(min_engine=min_engine))

    def verify(self, cfg):
        self.layout.strata_config.write_text(json.dumps(cfg))
        with patch.object(install, "host_platform", return_value="windows-x64"):
            return install.verify_generated(self.layout)

    def test_engine_is_staged_where_stock_setup_reuses_it_and_must_stay_exact(self):
        install.stage_engine(self.layout, log=lambda _: None)
        engine = self.layout.strata / "engine"
        self.assertEqual(sorted(archive_members()), sorted(p.name for p in engine.iterdir()))
        self.assertEqual("f-021-rel", install.engine_build(self.layout)["source"])
        install.stage_engine(self.layout, log=lambda _: None)   # an interrupted install's staging is reused
        (engine / "strata_kq.dll").write_bytes(b"replaced after staging")
        with self.assertRaisesRegex(install.InstallError, "staged engine component changed"):
            install.engine_build(self.layout)

    def test_engine_older_than_setups_min_engine_is_refused_before_setup(self):
        self.write_setup((0, 1, 47))
        with self.assertRaisesRegex(install.InstallError, "older than the pinned setup.py's MIN_ENGINE"):
            install.stage_engine(self.layout, log=lambda _: None)

    def test_config_must_carry_setups_own_args_record_and_nothing_carried(self):
        self.assertEqual(self.cfg, self.verify(self.cfg))
        stale = dict(self.cfg, args_written=self.cfg["args"][:-2])
        missing = {k: v for k, v in self.cfg.items() if k != "args_written"}
        carried = dict(self.cfg, user_args=["--vram-reserve-mib", "0"])
        for label, cfg in (("stale", stale), ("missing", missing), ("carried", carried)):
            with self.subTest(label), self.assertRaises(install.InstallError):
                self.verify(cfg)

    def test_setup_that_carried_user_options_is_refused_before_the_pinned_steps(self):
        self.layout.strata_config.write_text(json.dumps(self.cfg))
        install.check_setup_stamp(self.layout)
        for cfg in (dict(self.cfg, user_args=["--spec", "2"]), dict(self.cfg, args=self.cfg["args"] + ["--spec", "2"])):
            self.layout.strata_config.write_text(json.dumps(cfg))
            with self.subTest(cfg=sorted(cfg)), self.assertRaisesRegex(install.InstallError, "carried user options"):
                install.check_setup_stamp(self.layout)

    def test_pinned_flag_steps_restamp_setups_record_and_leave_older_configs_alone(self):
        (self.layout.strata / "strata_control").mkdir()
        (self.layout.strata / "strata_control/__init__.py").write_text("")
        (self.layout.strata / "strata_control/user_args.py").write_text(USER_ARGS)
        tips = {"--prefill": "auto:32768"}
        data = copy.deepcopy(self.layout.profile.data)
        data["strata"]["stock_tips"] = tips
        data["strata"]["expected_engine_flags"] = watch.tipped_flags(data["strata"]["expected_engine_flags"], tips)
        self.layout = Layout(self.layout.root, Profile(PRO, data))
        legacy = {k: v for k, v in self.cfg.items() if k != "args_written"}
        for initial in (self.cfg, legacy):
            with self.subTest(stamped="args_written" in initial):
                self.layout.strata_config.write_text(json.dumps(initial))
                with patch.object(Layout, "venv_python", new_callable=PropertyMock, return_value=Path(sys.executable)):
                    install.apply_stock_tips(self.layout, log=lambda _: None)
                cfg = json.loads(self.layout.strata_config.read_text())
                self.assertEqual("auto:32768", common.flag_pairs(cfg["args"])["--prefill"])
                self.assertEqual("args_written" in initial, "args_written" in cfg)
                if "args_written" in cfg:
                    self.assertEqual(cfg["args"], cfg["args_written"])
                    self.assertEqual(cfg, self.verify(cfg))


class PinnedMtpFetch(unittest.TestCase):
    """Stock mtp_fetch applies its tensor SHA256 table only while REPO == PINNED, both built from HF_ENDPOINT."""
    MTP_FETCH = '''
import os
PINNED_REVISION = "de4b8e4d43b917e7706784d8bb445c9af86a3540"
REVISION = os.environ.get("STRATA_MTP_REVISION") or PINNED_REVISION
HF_ENDPOINT = (os.environ.get("HF_ENDPOINT") or "").strip().rstrip("/") or "https://huggingface.co"
REPO = HF_ENDPOINT + "/Qwen/Qwen3.8-Flash-Next/resolve/%s/" % REVISION
PINNED = HF_ENDPOINT + "/Qwen/Qwen3.8-Flash-Next/resolve/%s/" % PINNED_REVISION


def pinned():
    return REPO == PINNED


def main():
    import sys
    print("pinned" if pinned() else "unpinned", REPO)
'''

    def test_an_ambient_mirror_cannot_switch_off_stocks_tensor_hash_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "mtp_fetch.py").write_text(self.MTP_FETCH)
            url = "https://huggingface.co/Qwen/Qwen3.8-Flash-Next/resolve/de4b8e4d43b917e7706784d8bb445c9af86a3540/"
            env = dict(os.environ, HF_ENDPOINT="https://mirror.example.com")
            out = subprocess.run([sys.executable, "-c", install.MTP_FETCH_PINNED, temp, url, temp], env=env,
                                 capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(["pinned", url], out)
