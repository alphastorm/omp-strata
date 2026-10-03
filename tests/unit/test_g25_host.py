"""Host-free lifecycle/observation boundaries; these never satisfy a real-host gate."""
from __future__ import annotations

import hashlib
import io
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from omp_strata.comparison import validate_host_observation
from scripts import g25_host as driver
from scripts import g25_host_probe as probe


class HostFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="g25-host-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "state").mkdir()
        self.config = {"comparison_id": "host-fixture", "comparison_root": str(self.root),
                       "initial_owner": "ninfer", "python": sys.executable,
                       "host": {"label": "rtx3090-win-a", "display_attached": True},
                       "strata": {"root": r"C:\g25-fixture\strata", "port": 18090},
                       "ninfer": {"root": r"C:\g25-fixture\ninfer", "port": 18082, "lane": "rtx3090-native"}}
        for arm in driver.ARMS:
            key = self.root / (arm + "-key")
            key.write_text(arm + "x" * 40, encoding="ascii")
            key.chmod(0o600)
            self.config[arm]["key_file"] = str(key)
        self.facts = {
            "os_build": "fixture-build", "boot_id": "fixture-boot", "ram_gib": 128,
            "available_ram_gib": 80, "commit_headroom_gib": 88, "disk_gib": 160,
            "power": "fixture-balanced", "private_keys": {
                self.config[arm]["key_file"]: True for arm in driver.ARMS},
            "processes": [
                {"pid": 101, "parent_pid": 1, "name": "strata.exe", "created": "fixture-process-start",
                 "executable": r"C:\g25-fixture\strata\engine\strata.exe", "command_line": "strata.exe"},
                {"pid": 202, "parent_pid": 1, "name": "dwm.exe", "created": "fixture-desktop-start",
                 "executable": r"C:\Windows\System32\dwm.exe", "command_line": "dwm.exe"}],
            "connections": [{"pid": 101, "local_address": "127.0.0.1", "local_port": 18090,
                             "remote_address": "127.0.0.1", "remote_port": 40000, "state": "Established"}],
        }
        self.gpu = {"name": "NVIDIA GeForce RTX 3090", "total_mib": 24576, "used_mib": 18000,
                    "driver": "fixture-driver", "clock_policy": "driver-managed", "power_limit": "fixture-limit",
                    "processes": [{"pid": 101, "type": "C", "name": "strata.exe"},
                                  {"pid": 202, "type": "C+G", "name": "dwm.exe"}]}
        self.identities = [{"pid": 101, "created": "fixture-process-start", "arm": "strata"}]
        now = time.monotonic_ns()
        self.record = {"comparison_id": "host-fixture", "step": "pilot-strata", "arm": "strata",
                       "reservation_nonce": "fixture-nonce", "boot_id": "fixture-boot",
                       "stop_started_ns": now - 3_000_000_000, "startup_started_ns": now - 2_000_000_000,
                       "ready_ns": now, "ready_processes": self.identities}
        probe.write_private(self.root / "state" / "current-switch.json", self.record)
        probe.write_private(self.root / "state" / "pilot-strata.reserved.json", {"nonce": "fixture-nonce"})
        self.plan = {"host": {"label": "rtx3090-win-a", "os": "windows", "os_build": "fixture-build",
                             "gpu_model": self.gpu["name"], "vram_mib": 24576, "driver": "fixture-driver",
                             "clock_policy": "driver-managed", "power_policy": "fixture-balanced; GPU limit fixture-limit",
                             "min_ram_gib": 100, "min_available_ram_gib": 50, "min_commit_headroom_gib": 50,
                             "min_disk_gib": 100}, "schedule": {"switch_timeout_seconds": 300}}

    def observation(self):
        with patch.object(probe, "collect_windows", return_value=self.facts), \
             patch.object(probe, "collect_gpu", return_value=self.gpu), \
             patch.object(probe, "controller_status", return_value={"state": "healthy"}):
            return probe.observe(self.config, "strata")


class ObservationTests(HostFixture):
    def test_fresh_observation_matches_dispatch_contract_and_private_hash(self):
        observation = self.observation()
        self.assertEqual(validate_host_observation(observation, self.plan, "strata"), [])
        self.assertEqual(observation["startup_ms"], 2000)
        self.assertEqual(observation["switch_ms"], 3000)
        self.assertEqual(observation["gpu_owners"], ["strata"])
        path, = (self.root / "network-observations").iterdir()
        self.assertEqual(observation["network_observation_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        if sys.platform != "win32":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(observation["credential_exposure"])
        self.assertEqual(set(observation["missing_reasons"]), {"file_cache_condition"})

    def test_idle_graphics_is_not_a_compute_owner_or_a_cold_start(self):
        self.gpu["processes"] = self.gpu["processes"][1:]
        observation = self.observation()
        self.assertEqual(observation["gpu_owners"], [])
        self.assertIsNone(observation["startup_ms"])
        self.assertEqual(observation["process_condition"], "unknown")
        self.assertIn("concurrent_gpu_owner", validate_host_observation(observation, self.plan, "strata"))

    def test_finished_window_record_cannot_supply_next_window_timing(self):
        probe.write_private(self.root / "state" / "pilot-strata.finished.json", {"returncode": 0})
        observation = self.observation()
        self.assertIsNone(observation["switch_ms"])
        self.assertIn("switch_failure", validate_host_observation(observation, self.plan, "strata"))

    def test_key_in_process_argv_or_broad_key_acl_refuses_dispatch(self):
        for mode in ("argv", "acl"):
            with self.subTest(mode=mode):
                if mode == "argv":
                    self.facts["processes"][0]["command_line"] = Path(self.config["strata"]["key_file"]).read_text()
                else:
                    self.facts["processes"][0]["command_line"] = "strata.exe"
                    self.facts["private_keys"][self.config["strata"]["key_file"]] = False
                observation = self.observation()
                self.assertTrue(observation["credential_exposure"])
                self.assertIn("credential_exposure", validate_host_observation(observation, self.plan, "strata"))

    def test_nonloopback_tool_connection_is_hashed_and_refused(self):
        self.facts["processes"].append({"pid": 303, "parent_pid": 101, "name": "tool.exe",
                                       "executable": "tool.exe", "command_line": "tool.exe"})
        self.facts["connections"].append({"pid": 303, "local_address": "::1", "local_port": 40001,
                                          "remote_address": "2001:db8::1", "remote_port": 443,
                                          "state": "Established"})
        observation = self.observation()
        self.assertTrue(observation["route_escape"])
        self.assertIn("route_escape", validate_host_observation(observation, self.plan, "strata"))
        path, = (self.root / "network-observations").iterdir()
        self.assertEqual(probe.read_json(path)["connections"][0]["pid"], 303)

    def test_missing_controller_or_network_is_never_a_safety_pass(self):
        with patch.object(probe, "collect_windows", side_effect=probe.HostError("unavailable")):
            observation = probe.observe(self.config, "strata")
        self.assertIsNone(observation["route_escape"])
        self.assertFalse(observation["controller_ok"])
        self.assertIn("observation", observation["missing_reasons"])


class OwnershipTests(HostFixture):
    def test_graphics_exclusion_is_display_attached_only(self):
        graphics = self.gpu["processes"][1:]
        owners, _ = probe.classify_owners(graphics, self.facts["processes"], self.config)
        self.assertEqual(owners, [])
        self.config["host"]["display_attached"] = False
        owners, _ = probe.classify_owners(graphics, self.facts["processes"], self.config)
        self.assertEqual(owners, ["unrelated"])

    def test_unrelated_compute_process_remains_an_owner(self):
        self.gpu["processes"][1]["type"] = "C"
        owners, _ = probe.classify_owners(self.gpu["processes"], self.facts["processes"], self.config)
        self.assertEqual(owners, ["strata", "unrelated"])

    def test_docker_vm_requires_explicit_declaration_and_live_identity(self):
        process = {"pid": 404, "name": "declared-vm.exe", "created": "vm-start", "parent_pid": 1}
        gpu = [{"pid": 404, "name": "declared-vm.exe", "type": "C"}]
        live = {"running": True, "endpoint_state": "ready"}
        self.assertEqual(probe.classify_owners(gpu, [process], self.config, live)[0], ["unrelated"])
        self.config["ninfer"]["gpu_process_names"] = ["declared-vm.exe"]
        self.assertEqual(probe.classify_owners(gpu, [process], self.config)[0], ["unrelated"])
        self.assertEqual(probe.classify_owners(gpu, [process], self.config, live)[0], ["ninfer"])
        with self.assertRaisesRegex(probe.HostError, "network observation"):
            probe.network_snapshot(self.facts, self.config, live)


class SwitchTests(HostFixture):
    def measure(self, record=None, **changes):
        args = {"arm": "strata", "comparison_id": "host-fixture", "boot_id": "fixture-boot",
                "processes": self.identities}
        args.update(changes)
        return probe.switch_measurements(record or self.record, **args)

    def test_startup_is_strictly_a_subset_of_switch(self):
        self.assertEqual(self.measure(), (2000, 3000))
        self.record["startup_started_ns"] = self.record["stop_started_ns"] - 1
        with self.assertRaisesRegex(probe.HostError, "ordering"):
            self.measure()

    def test_long_switch_reboot_wrong_arm_and_pid_reuse_are_refused(self):
        for change in ({"arm": "ninfer"}, {"boot_id": "new-boot"},
                       {"processes": [{"pid": 101, "created": "new-process", "arm": "strata"}]}):
            with self.subTest(change=change), self.assertRaises(probe.HostError):
                self.measure(**change)
        self.record["stop_started_ns"] = self.record["ready_ns"] - 300_000_000_001
        with self.assertRaisesRegex(probe.HostError, "boundary"):
            self.measure()

    def test_reservation_survives_interruption_and_cannot_be_overwritten(self):
        first = driver.reserve_step(self.root, "window-1")
        with self.assertRaisesRegex(probe.HostError, "never be rerun"):
            driver.reserve_step(self.root, "window-1")
        self.assertEqual(probe.read_json(self.root / "state" / "window-1.reserved.json"), first)

    def test_start_failure_stops_only_target_and_never_dispatches(self):
        (self.root / "state" / "current-switch.json").unlink()
        calls = []
        def lifecycle(config, arm, action, **kwargs):
            calls.append((arm, action))
            if action == "start":
                raise probe.HostError("start failed after spawning")
        with patch.object(driver, "lifecycle", side_effect=lifecycle), \
             patch.object(driver, "release_gpu"), patch.object(driver, "compare") as compare:
            with self.assertRaisesRegex(probe.HostError, "start failed"):
                driver.transition(self.config, "strata", "pilot-strata", {"nonce": "fixture"}, self.plan, {})
        self.assertEqual(calls, [("ninfer", "stop"), ("strata", "start"), ("strata", "stop")])
        compare.assert_not_called()
        failure = probe.read_json(self.root / "state" / "pilot-strata-transition-failure.json")
        self.assertEqual(failure, {"stop_attempted": True, "gpu_released": True})

    def test_unreleased_gpu_never_starts_an_engine(self):
        calls = []
        with patch.object(driver, "lifecycle", side_effect=lambda c, a, act, **kw: calls.append((a, act))), \
             patch.object(driver, "release_gpu", side_effect=probe.HostError("GPU retained")):
            with self.assertRaises(probe.HostError):
                driver.transition(self.config, "strata", "pilot-strata", {"nonce": "fixture"}, self.plan, {})
        self.assertEqual(calls, [("strata", "stop")])

    def test_sequence_stops_on_first_failed_step_and_does_not_freeze(self):
        probe.write_private(self.root / "state" / "host-config.json", self.config)
        calls = []
        def step(config, name):
            calls.append(name)
            return 7 if name == "pilot-ninfer" else 0
        with patch.object(driver, "run_step", side_effect=step), patch.object(driver, "compare") as compare:
            self.assertEqual(driver.run(self.config, sequence="all"), 7)
        self.assertEqual(calls, ["pilot-strata", "pilot-ninfer"])
        compare.assert_not_called()


class NativeCaptureTests(unittest.TestCase):
    def test_native_capture_binds_controller_release_to_clean_served_hashes(self):
        config = {"ninfer": {"lane": "rtx3090-native"}}
        status = {"release_id": "native-fixture-release", "endpoint_state": "ready", "process_state": "running",
                  "gpu_owner": {"status": "ok"}}
        live = {"identity": {"source_dirty": False, "binary_sha256": "1" * 64,
                             "config_sha256": "2" * 64, "model_artifact_sha256": "3" * 64}}
        normalized = driver.native_capture(config, status, live)
        self.assertEqual(normalized, {"release_id": "native-fixture-release", "endpoint_state": "ready",
                                     "runtime_identity_sha256": "1" * 64, "config_identity_sha256": "2" * 64,
                                     "model_identity_sha256": "3" * 64})
        live["identity"]["source_dirty"] = True
        with self.assertRaises(probe.HostError):
            driver.native_capture(config, status, live)


class InvocationTests(unittest.TestCase):
    def test_real_argv_preserves_metacharacters_as_data(self):
        value = "space ; ampersand & literal $(not-a-command)"
        output = probe.run_argv([sys.executable, "-c", "import sys; print(sys.argv[1])", value],
                                deadline=time.monotonic() + 10)
        self.assertEqual(output, value)

    def test_subprocess_boundary_explicitly_disables_shell_and_stdin(self):
        with patch.object(probe.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}", "")) as run:
            self.assertEqual(probe.run_argv(["fixture.exe", "a&b"], deadline=time.monotonic() + 10), "{}")
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.args[0], ["fixture.exe", "a&b"])
        with self.assertRaises(probe.HostError):
            probe.run_argv(["fixture.cmd"], deadline=time.monotonic() + 10)

    def test_failed_prerequisite_names_its_reason_for_the_operator(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text('{"comparison_id": "../escape"}', encoding="utf-8")
            with patch.object(sys, "stderr", new=io.StringIO()) as err:
                self.assertEqual(driver.main(["prepare", "--config", str(config)]), 1)
        self.assertIn("HostError: safe comparison id required", err.getvalue())

    def test_nvidia_smi_gets_program_files_under_the_evaluator_clean_environment(self):
        clean = {"PATH": r"C:\Windows\System32", "SYSTEMROOT": r"D:\Windows"}   # eval.support.clean_env keeps these
        with patch.object(probe.os, "name", "nt"), patch.dict(probe.os.environ, clean, clear=True):
            env = probe.nvml_env()
        self.assertEqual(env["ProgramFiles"], r"D:\Program Files")
        self.assertEqual(env["ProgramW6432"], r"D:\Program Files")
        kept = {**clean, "PROGRAMFILES": r"E:\PF", "PROGRAMW6432": r"E:\PF"}
        with patch.object(probe.os, "name", "nt"), patch.dict(probe.os.environ, kept, clear=True):
            env = probe.nvml_env()
        self.assertEqual({k for k in env if k.upper() == "PROGRAMFILES"}, {"PROGRAMFILES"})

    def test_docker_lane_gpu_attribution_to_system_owns_no_kernel_children_or_sockets(self):
        facts = {"boot_id": "boot", "processes": [
            {"pid": 4, "parent_pid": 0, "name": "System", "executable": None, "command_line": None},
            {"pid": 472, "parent_pid": 4, "name": "Registry", "executable": None, "command_line": None},
            {"pid": 900, "parent_pid": 1, "name": "strata.exe", "executable": r"C:\roots\strata\engine\strata.exe",
             "command_line": "strata.exe --port 18090"}],
            "connections": [{"pid": 4, "local_address": "192.0.2.2", "local_port": 445, "remote_address": "192.0.2.9",
                             "remote_port": 50000, "state": "Established"}]}
        config = {"strata": {"root": r"C:\roots\strata"}, "ninfer": {"gpu_process_names": ["System"]}}
        docker = {"running": True, "endpoint_state": "ready", "network_connections": []}
        snapshot = probe.network_snapshot(facts, config, docker)
        self.assertEqual(snapshot["owned_pids"], [900])
        self.assertEqual(snapshot["connections"], [])


if __name__ == "__main__":
    unittest.main()
