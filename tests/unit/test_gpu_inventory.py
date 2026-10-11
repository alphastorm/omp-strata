"""Read-only inventory with synthetic NVIDIA observations, never invoking a GPU utility."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from omp_strata.profile import Profile
from scripts import gpu_inventory
from tests.unit.test_profile import multi_gpu_data


class InventoryTests(unittest.TestCase):
    IDENTITY = ("0, NVIDIA GeForce RTX 3090, 00000000:01:00.0, 24576, 8.6, 600.01, Yes\n"
                "1, NVIDIA GeForce RTX 4090, 00000000:02:00.0, 24564, 8.9, 600.01, No\n")

    def setUp(self):
        self.commands = []
        self.identity = self.IDENTITY
        self.unavailable = set()
        self.enterContext(patch.object(gpu_inventory.shutil, "which", return_value="nvidia-smi"))
        self.enterContext(patch.object(gpu_inventory.procs, "memory", return_value={"total": 128 << 30, "available": 100 << 30}))
        self.enterContext(patch.object(gpu_inventory.subprocess, "run", side_effect=self.run_query))

    def run_query(self, argv, **kwargs):
        self.commands.append(argv)
        fields = argv[1].removeprefix("--query-gpu=")
        if fields == ",".join(gpu_inventory.IDENTITY_FIELDS):
            return subprocess.CompletedProcess(argv, 0, self.identity)
        field = fields.removeprefix("index,")
        if field in self.unavailable:
            return subprocess.CompletedProcess(argv, 1, "")
        values = {"compute_mode": ("Default", "Default"), "display_active": ("Disabled", "Disabled"),
                  "pcie.link.gen.current": ("3", "3"),
                  "pcie.link.gen.max": ("4", "4"), "pcie.link.width.current": ("8", "16"),
                  "pcie.link.width.max": ("16", "16")}
        a, b = values[field]
        return subprocess.CompletedProcess(argv, 0, f"0, {a}\n1, {b}\n")

    def test_cli_prints_complete_sanitized_json_without_writing_files(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(Path, "mkdir", side_effect=AssertionError("writes forbidden")), \
                patch.object(Path, "write_text", side_effect=AssertionError("writes forbidden")), \
                patch.object(Path, "write_bytes", side_effect=AssertionError("writes forbidden")):
            result = gpu_inventory.main([])
        self.assertEqual(0, result)
        report = json.loads(output.getvalue())
        self.assertTrue(report["complete"])
        self.assertEqual(128 * 1024, report["ram"]["total_mib"])
        self.assertEqual(["86", "89"], [card["arch"] for card in report["gpus"]])
        self.assertEqual(8, report["gpus"][0]["pcie_width_current"])
        self.assertIn("observed_utc", report)
        for argv in self.commands:
            self.assertTrue(argv[1].startswith("--query-gpu="))
            self.assertNotIn("uuid", argv[1])
            self.assertNotIn("serial", argv[1])
        self.assertNotIn("uuid", output.getvalue())
        self.assertNotIn("serial", output.getvalue())

    def test_unsupported_advisory_fields_are_null_with_reasons_not_invented(self):
        self.unavailable = {"pcie.link.gen.current", "compute_mode"}
        report = gpu_inventory.inventory()
        self.assertTrue(report["complete"])
        self.assertIsNone(report["gpus"][0]["pcie_gen_current"])
        self.assertIsNone(report["gpus"][0]["compute_mode"])
        self.assertTrue(report["gpus"][0]["missing"])
        self.assertTrue(report["missing"])

    def test_missing_identity_capacity_display_and_duplicate_cards_are_incomplete(self):
        for text in ("", self.IDENTITY.replace("24564", "N/A"), self.IDENTITY.replace("8.9", "N/A"),
                     self.IDENTITY.replace(", No\n", ", N/A\n"), self.IDENTITY.replace("00000000:02:00.0", "bad"),
                     self.IDENTITY.replace("1, NVIDIA", "0, NVIDIA"), self.IDENTITY + self.IDENTITY):
            with self.subTest(text=text):
                self.identity = text
                report = gpu_inventory.inventory()
                self.assertFalse(report["complete"])
                self.assertTrue(report["missing"])

    def test_profile_identity_check_does_not_require_idle_or_collect_processes(self):
        profile = Profile(Path("profiles/two-gpu.json"), multi_gpu_data())
        report = gpu_inventory.inventory(profile)
        self.assertTrue(report["profile_check"]["matches"], report)
        self.assertTrue(report["complete"])
        profile.data["host"]["gpus"][0]["pci_bus_id"] = "00000000:03:00.0"
        report = gpu_inventory.inventory(profile)
        self.assertFalse(report["complete"])
        self.assertFalse(report["profile_check"]["matches"])
        self.assertTrue(all("-q" not in command for command in self.commands))

    def test_display_attachment_is_physical_even_when_wddm_reports_no_active_display(self):
        # WDDM reads display_active Disabled on every card, including the one driving the desktop.
        report = gpu_inventory.inventory()
        self.assertEqual([True, False], [card["display_attached"] for card in report["gpus"]])
        self.assertEqual([False, False], [card["display_active"] for card in report["gpus"]])
        profile = Profile(Path("profiles/two-gpu.json"), multi_gpu_data())
        self.assertTrue(gpu_inventory.inventory(profile)["profile_check"]["matches"])
        self.identity = self.IDENTITY.replace(", Yes\n", ", No\n")
        report = gpu_inventory.inventory(profile)
        self.assertFalse(report["complete"])
        self.assertIn("GPU 0: display attachment differs from profile", report["profile_check"]["problems"])

    def test_optional_profile_cli_and_missing_inventory_exit_nonzero(self):
        profile = Profile(Path("profiles/two-gpu.json"), multi_gpu_data())
        with patch.object(gpu_inventory, "load", return_value=profile) as load, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, gpu_inventory.main(["--profile", "profiles/two-gpu.json"]))
        load.assert_called_once_with(Path("profiles/two-gpu.json"))
        with patch.object(gpu_inventory.shutil, "which", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, gpu_inventory.main([]))
        with patch.object(gpu_inventory.procs, "memory", return_value={"total": 0, "available": 0}):
            self.assertFalse(gpu_inventory.inventory()["complete"])


if __name__ == "__main__":
    unittest.main()
