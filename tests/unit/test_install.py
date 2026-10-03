"""Pinned stock generated configs (Unsloth budget, pinned calibration) and pre-placed four-shard fetch boundaries;
no host or network."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

from omp_strata import common, fetch, install
from omp_strata.layout import Layout
from omp_strata.profile import Profile, load
from scripts import upstream_watch as watch
from tests.fixtures import strata_0_1_36_calibrate as stock_calibration

REPO = Path(__file__).resolve().parents[2]
PROFILE = REPO / "profiles/win11-rtx3090-ud-q4kxl-131k-strata0.1.36-omp18.4.12.json"
CALIBRATED = REPO / "profiles/win11-rtx3090-iq3s-131k-calibrated-strata0.1.36-omp18.4.12.json"


class GeneratedConfig(unittest.TestCase):
    """A root holding the config stock setup v0.1.36 writes for PROFILE's model, before any later step."""
    PROFILE = PROFILE

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.layout = Layout(Path(self.temp.name) / "integration", load(self.PROFILE))
        self.layout.strata.mkdir(parents=True)
        self.pack = self.layout.data / "packs" / self.layout.strata_config.stem.removeprefix("strata-")
        self.pack.mkdir(parents=True)
        self.mtp = self.layout.data / "mtp/rt"
        self.mtp.mkdir(parents=True)
        (self.mtp / "experts.bin").write_bytes(b"separate stock draft experts")
        source = (REPO / "tests/fixtures/strata_0_1_36_plan.py").read_text()
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
            watch.stock_plan(source, family=s["family"], model=s["model"], context=s["context"], ram=127.69, vram=24)
        self.cfg = namespace["cfg"]
        # The real stock tag determines the filename, not Layout's family map.
        self.config_path = self.layout.strata / f"strata-{namespace['tag'].lower()}.json"
        self.write_config()

    def write_config(self):
        self.config_path.write_text(json.dumps(self.cfg))

    def verify(self):
        with patch.object(install, "host_platform", return_value="windows-x64"):
            return install.verify_generated(self.layout)


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
