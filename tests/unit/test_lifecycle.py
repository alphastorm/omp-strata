"""G05: host-free lifecycle ownership and artifact failure boundaries."""
import copy
import hashlib
import http.server
import os
from pathlib import Path
import re
import secrets
import selectors
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

from omp_strata import common, dflash2, fetch, lifecycle, nvfp4, procs
from omp_strata.layout import Layout
from omp_strata.profile import ENGINE_ENV_GROUPS, Profile, engine_env_union, load
from tests.candidate import PROFILE
from tests.mock.test_remote_support import free_port
from tests.unit.test_profile import multi_gpu_data, single_gpu_data

REPO = Path(__file__).resolve().parents[2]


def gpu_fact(profile, index, processes=(), used=0):
    """One host-free fact for the requested card of the actual subject, in either CI lane."""
    card = next(card for card in profile.gpu_requirements if card["gpu_index"] == index)
    compute = sum(process["type"] not in ("G", "C+G") for process in processes)
    return {"available": True, "gpu_index": index, "name": card["gpu_model"], "arch": card["arch"],
            "pci_bus_id": card["pci_bus_id"], "memory_total_mib": card["min_gpu_vram_mib"],
            "memory_used_mib": used, "driver": f"{int(profile.data['host']['min_driver_major'])}.00",
            "display_active": card["display_attached"], "display_attached": card["display_attached"], "processes": list(processes),
            "compute_apps": compute, "graphics_apps": len(processes) - compute}


class LifecycleFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        data = common.read_json(PROFILE)
        data["server"]["port"] = free_port()
        data["server"]["stop_timeout_s"] = 2
        profile_path = self.directory / "profile.json"
        common.atomic_write_json(profile_path, data)
        self.layout = Layout(self.directory / "integration", load(profile_path))
        self.messages = []
        self.enterContext(patch.object(lifecycle, "gpu_facts", side_effect=lambda index, **kwargs: gpu_fact(self.layout.profile, index)))

    def idle_gpu_report(self, *, after_stop=False):
        if not self.layout.profile.multi_gpu:
            return {}
        cards = [{"gpu_index": card["gpu_index"], "gpu_model": card["gpu_model"], "arch": card["arch"],
                  "pci_bus_id": card["pci_bus_id"], "memory_total_mib": card["min_gpu_vram_mib"],
                  "memory_used_mib": 0, "driver_version": f"{int(self.layout.profile.data['host']['min_driver_major'])}.00",
                  "display_active": card["display_attached"], "owned_count": 0, "foreign_compute_count": 0,
                  "graphics_client_count": 0, "problems": ["owned engine not observed on card"] if after_stop else []}
                 for card in self.layout.profile.gpu_requirements]
        return {"cards": cards, **({"owned_gpus_released": True} if after_stop else {})}

    def spawn(self, code, *args):
        proc = subprocess.Popen(
            [sys.executable, "-u", "-c", code, *map(str, args)], cwd=REPO,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )

        def cleanup():
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
        self.addCleanup(cleanup)
        return proc

    def line(self, proc):
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(timeout=5), "child did not report readiness")
        line = proc.stdout.readline().strip()
        self.assertTrue(line, "child exited before reporting readiness")
        return line

    def sleeper(self):
        proc = self.spawn("import time; print('ready', flush=True); time.sleep(60)")
        self.assertEqual("ready", self.line(proc))
        identity = procs.info(proc.pid)
        self.assertIsNotNone(identity)
        return proc, identity


class LifecycleTests(LifecycleFixture):
    def test_doctor_credits_complete_pinned_inputs_after_install_or_hardlink(self):
        data = copy.deepcopy(self.layout.profile.data)
        data["model"]["files"] = [dict(entry, bytes=32) for entry in data["model"]["files"]]
        for entry in data["model"].get("dflash2_source", {}).get("files", []):
            entry["bytes"] = 32
        if "tuned" in data["model"].get("dflash2_source", {}):  # the tuned pack is one more pinned input
            data["model"]["dflash2_source"]["tuned"]["bytes"] = 32
        for entry in data["strata"]["artifacts"].values():
            entry["bytes"] = 32
        self.layout = Layout(self.layout.root, Profile(PROFILE, data))
        items = fetch.plan(self.layout, platform="windows-x64", only={"model", "dflash2", "engine", "llama"})
        total = sum(item.bytes for item in items)
        free = 8
        data["host"]["min_free_disk_gib"] = (total + free) / 2**30
        self.layout.state.mkdir(parents=True)
        common.atomic_write_json(self.layout.install_record, {"profile_fingerprint": self.layout.profile.fingerprint})
        source = self.directory / "existing-input"
        source.write_bytes(b"x" * 32)
        for item in items:
            item.dest.parent.mkdir(parents=True, exist_ok=True)
            os.link(source, item.dest)
        with patch.object(lifecycle, "host_platform", return_value="windows-x64"), \
                patch.object(lifecycle.shutil, "disk_usage", return_value=type("Usage", (), {"free": free})()), \
                patch.object(lifecycle, "port_in_use", return_value=False):
            self.assertLess(free / 2**30, data["host"]["min_free_disk_gib"])  # the old installed-root failure
            checks = {entry["check"]: entry for entry in lifecycle.doctor(self.layout)["checks"]}
            self.assertTrue(checks["installed"]["ok"])
            self.assertTrue(checks["disk"]["ok"], checks["disk"])
            self.assertIn("GiB free + ", checks["disk"]["detail"])
            self.assertIn("GiB present pinned inputs", checks["disk"]["detail"])
            # Wrong-size and missing inputs, including a partial download, receive no credit.
            target = items[0].dest
            target.unlink()
            target.write_bytes(b"short")
            self.assertFalse(next(entry for entry in lifecycle.doctor(self.layout)["checks"]
                                  if entry["check"] == "disk")["ok"])
            target.unlink()
            target.with_name(target.name + ".partial").write_bytes(b"x" * 32)
            self.assertFalse(next(entry for entry in lifecycle.doctor(self.layout)["checks"]
                                  if entry["check"] == "disk")["ok"])
            if os.name != "nt":  # Windows symlinks require a host privilege these unit tests never assume.
                target.symlink_to(source)
                self.assertFalse(next(entry for entry in lifecycle.doctor(self.layout)["checks"]
                                      if entry["check"] == "disk")["ok"])

    def test_file_lock_excludes_another_process_and_releases(self):
        holder = self.spawn(
            "from pathlib import Path\n"
            "import sys\n"
            "from omp_strata.lifecycle import FileLock\n"
            "with FileLock(Path(sys.argv[1])):\n"
            "    print('locked', flush=True)\n"
            "    sys.stdin.readline()\n",
            self.layout.lock_file,
        )
        self.assertEqual("locked", self.line(holder))
        with self.assertRaises(lifecycle.LifecycleError):
            with lifecycle.FileLock(self.layout.lock_file):
                self.fail("concurrent lock acquisition succeeded")
        holder.communicate("release\n", timeout=5)
        self.assertEqual(0, holder.returncode)
        with lifecycle.FileLock(self.layout.lock_file):
            with self.assertRaises(lifecycle.LifecycleError):
                with lifecycle.FileLock(self.layout.lock_file):
                    self.fail("reacquired lock was not exclusive")

    def test_stale_creation_or_executable_never_owns_a_live_pid(self):
        proc, identity = self.sleeper()
        self.assertEqual(identity, procs.matches(identity.as_dict()))
        for field in ("created", "exe"):
            with self.subTest(field=field):
                stale = identity.as_dict()
                stale[field] += "-different"
                self.assertIsNone(procs.matches(stale))
                common.atomic_write_json(self.layout.run_record, {
                    "state": "ready", "server": stale, "wrapper": stale,
                })
                self.assertEqual({"state": "stopped", "stopped": [], **self.idle_gpu_report(after_stop=True)},
                                 lifecycle.stop(self.layout, log=self.messages.append))
                self.assertIsNone(proc.poll(), "stop signalled an unrelated live process")
                self.assertEqual(identity, procs.matches(identity.as_dict()))
                self.assertEqual("stopped", common.read_json(self.layout.run_record)["state"])

    def test_stop_owns_current_descendants_and_is_idempotent(self):
        events = self.directory / "stop-events"
        child_code = (
            "import signal, sys, time\n"
            "from pathlib import Path\n"
            "def stopped(signum, frame):\n"
            "    with Path(sys.argv[1]).open('a') as out:\n"
            "        out.write('child-stopped\\n')\n"
            "    sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, stopped)\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n"
        )
        parent = self.spawn(
            "import signal, subprocess, sys, time\n"
            "from pathlib import Path\n"
            "events = Path(sys.argv[1])\n"
            "child = subprocess.Popen([sys.executable, '-u', '-c', sys.argv[2], sys.argv[1]], stdout=subprocess.PIPE, text=True)\n"
            "def stopped(signum, frame):\n"
            "    with events.open('a') as out:\n"
            "        out.write('parent-after-child\\n' if child.poll() is not None else 'parent-before-child\\n')\n"
            "    if child.poll() is None:\n"
            "        child.terminate()\n"
            "        child.wait()\n"
            "    sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, stopped)\n"
            "assert child.stdout.readline().strip() == 'ready'\n"
            "print(child.pid, flush=True)\n"
            "child.wait()\n"
            "while True:\n"
            "    time.sleep(1)\n",
            events, child_code,
        )
        child_pid = int(self.line(parent))
        identity = procs.info(parent.pid)
        self.assertIsNotNone(identity)
        self.assertIsNotNone(procs.info(child_pid))
        common.atomic_write_json(self.layout.run_record, {"state": "ready", "server": identity.as_dict()})
        # Reap our direct child as a real wrapper would; a zombie is not a running server.
        reaper = threading.Thread(target=parent.wait, daemon=True)
        reaper.start()
        result = lifecycle.stop(self.layout, log=self.messages.append)
        reaper.join(timeout=5)
        self.assertFalse(reaper.is_alive())
        self.assertIsNone(procs.info(parent.pid))
        self.assertIsNone(procs.info(child_pid))
        self.assertEqual(["child-stopped", "parent-after-child"], events.read_text().splitlines())
        self.assertEqual("stopped", result["state"])
        self.assertEqual(["server-descendant", "server"], [entry.split(":", 1)[0] for entry in result["stopped"]])
        self.assertEqual({"state": "stopped", "stopped": result["stopped"], **self.idle_gpu_report(after_stop=True)}, result)
        self.assertEqual("stopped", common.read_json(self.layout.run_record)["state"])
        self.assertEqual({"state": "stopped", "stopped": [], **self.idle_gpu_report(after_stop=True)},
                         lifecycle.stop(self.layout, log=self.messages.append))

    def test_start_refuses_unowned_occupied_port_without_launch_record(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            data = common.read_json(self.layout.profile.path)
            data["server"]["port"] = port
            common.atomic_write_json(self.layout.profile.path, data)
            layout = Layout(self.layout.root, load(self.layout.profile.path))
            with patch.object(lifecycle, "verify_install_fast", return_value={}), \
                    patch.object(lifecycle, "read_key", return_value=secrets.token_urlsafe(32)), \
                    patch.object(lifecycle, "gpu_facts", return_value={"available": False}):
                with self.assertRaisesRegex(lifecycle.LifecycleError, str(port)):
                    lifecycle.start(layout, tool_argv=[sys.executable], log=self.messages.append)
            self.assertFalse(layout.run_record.exists())
            self.assertTrue(lifecycle.port_in_use("127.0.0.1", port))

    def test_start_refuses_live_owned_server_or_wrapper(self):
        proc, identity = self.sleeper()
        for role in ("server", "wrapper"):
            with self.subTest(role=role):
                record = {"state": "ready", role: identity.as_dict()}
                common.atomic_write_json(self.layout.run_record, record)
                with patch.object(lifecycle, "verify_install_fast", return_value={}), \
                        patch.object(lifecycle, "read_key", return_value=secrets.token_urlsafe(32)):
                    with self.assertRaisesRegex(lifecycle.LifecycleError, "already running"):
                        lifecycle.start(self.layout, tool_argv=[sys.executable], log=self.messages.append)
                self.assertEqual(record, common.read_json(self.layout.run_record))
                self.assertIsNone(proc.poll())

    def test_serve_publishes_only_its_bound_generation_under_lock_and_waits_unlocked(self):
        wrapper = procs.ProcInfo(101, 90, "wrapper-created", "python.exe")
        server = procs.ProcInfo(102, 101, "server-created", "python.exe")
        for next_state in ("same", "replacement", "stopped"):
            with self.subTest(next_state=next_state):
                initial = {"state": "launching", "launch_id": "owned-launch",
                           "experiment_launch_id": "owned-marker",
                           "profile_fingerprint": self.layout.profile.fingerprint}
                common.atomic_write_json(self.layout.run_record, initial)
                replacement = {}

                def wait():
                    with lifecycle.FileLock(self.layout.lock_file):
                        record = common.read_json(self.layout.run_record)
                        self.assertEqual(record["launch_id"], "owned-launch")
                        self.assertEqual(record["experiment_launch_id"], "owned-marker")
                        self.assertEqual(record["server"], server.as_dict())
                        if next_state == "replacement":
                            record.update(launch_id="new-launch", experiment_launch_id="new-marker")
                        elif next_state == "stopped":
                            record["state"] = "stopped"
                        replacement.update(record)
                        common.atomic_write_json(self.layout.run_record, record)
                    return 0

                def spawn(*_args, **_kwargs):
                    with self.assertRaises(lifecycle.LifecycleError):
                        with lifecycle.FileLock(self.layout.lock_file):
                            self.fail("wrapper launch was not protected by its root lock")
                    from types import SimpleNamespace
                    return SimpleNamespace(pid=server.pid, wait=wait)

                with patch.object(lifecycle, "read_key", return_value="fixture-key"), \
                        patch.object(lifecycle.procs, "info", side_effect=[wrapper, server]), \
                        patch.object(lifecycle.subprocess, "Popen", side_effect=spawn):
                    self.assertEqual(0, lifecycle.serve(self.layout, log_path=self.directory / "server.log",
                                                      launch_id="owned-launch"))
                current = common.read_json(self.layout.run_record)
                if next_state == "same":
                    self.assertEqual("exited", current["state"])
                    self.assertEqual(0, current["exit_code"])
                else:
                    self.assertEqual(replacement, current)

    def test_keygen_is_private_and_preserves_existing_key(self):
        path = lifecycle.keygen(self.layout)
        key = lifecycle.read_key(self.layout)
        self.assertGreaterEqual(len(key), 32)
        if os.name == "posix":
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
        original = path.read_bytes()
        self.assertEqual(path, lifecycle.keygen(self.layout))
        self.assertEqual(original, path.read_bytes())
        self.assertEqual(key, lifecycle.read_key(self.layout))

    def test_read_key_rejects_missing_blank_and_short_files(self):
        with self.assertRaisesRegex(lifecycle.LifecycleError, "no API key file"):
            lifecycle.read_key(self.layout)
        for contents in (b"", b" \n\t", b"x" * 31):
            with self.subTest(length=len(contents)):
                common.atomic_write_bytes(self.layout.key_file, contents)
                with self.assertRaisesRegex(lifecycle.LifecycleError, "blank or too short"):
                    lifecycle.read_key(self.layout)
                with self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.keygen(self.layout)
                self.assertEqual(contents, self.layout.key_file.read_bytes())

    def test_status_distinguishes_install_and_exit_states(self):
        self.assertEqual({"state": "not_installed"}, lifecycle.status(self.layout))
        common.atomic_write_json(self.layout.install_record, {"profile_fingerprint": "different"})
        self.assertEqual("mismatched", lifecycle.status(self.layout)["state"])
        common.atomic_write_json(self.layout.install_record, {
            "profile_fingerprint": self.layout.profile.fingerprint,
        })
        self.assertEqual({"state": "stopped", **self.idle_gpu_report()}, lifecycle.status(self.layout))
        for code, expected in ((0, "stopped"), (None, "stopped"), (7, "failed"), (-1, "failed")):
            with self.subTest(exit_code=code):
                common.atomic_write_json(self.layout.run_record, {
                    "state": "exited", "exit_code": code, "log": "logs/server.log",
                })
                result = lifecycle.status(self.layout)
                self.assertEqual(expected, result["state"])
                if expected == "failed":
                    self.assertEqual(code, result["exit_code"])
                    self.assertEqual("logs/server.log", result["log"])
                details = {"exit_code": code, "log": "logs/server.log"} if expected == "failed" else {}
                self.assertEqual({"state": expected, **details, **self.idle_gpu_report()}, result)

    def test_fetch_checks_remaining_space_before_any_download(self):
        items = fetch.plan(self.layout, platform="linux-x64")
        total = sum(item.bytes for item in items)
        self.assertEqual(total, fetch.required_space(items))
        partial = items[0].dest.with_name(items[0].dest.name + ".partial")
        common.atomic_write_bytes(partial, b"partial")
        self.assertEqual(total - 7, fetch.required_space(items))
        with patch.object(fetch.shutil, "disk_usage", return_value=type("Usage", (), {"free": 0})()), \
                patch.object(fetch, "download_verified", side_effect=AssertionError("download before space check")):
            reason = "NVFP4 staging refused" if nvfp4.is_local(self.layout.profile.data["model"]) else "insufficient disk"
            with self.assertRaisesRegex(common.IntegrityError, reason):
                fetch.fetch(self.layout, platform="linux-x64", log=self.messages.append)
        self.assertEqual(b"partial", partial.read_bytes())
        self.assertTrue(all(not item.dest.exists() for item in items))


class SingleGpuLifecycleTests(LifecycleFixture):
    # verbatim from engine 0.1.54 on an RTX PRO 6000 (four batch slots, 2026-10-31)
    BATCH_MTP_ON = ("strata generate: --batch-mtp: 4 slot drafters on CUDA0 (50 MiB of private K/V state and buffers each, "
                    "sharing the solo drafter's weights); 83.57 GiB free there\n")
    BATCH_MTP_OFF = "strata generate: WARNING: --batch-mtp is off: it needs batch slots\n"
    # Verbatim, path-free engine 0.1.55 feature-arm lines (2026-11-02).
    BATCH_BASE = "strata verify: batch windows of up to 4 sequences (layers [0, 48))\n"
    SELF_COMMIT = BATCH_BASE.rstrip() + ", one-row windows keep their rows\n"
    KV_STREAMING = ("strata generate: KV streaming: 32768 of 262144 cells per QSA layer in VRAM, "
                    "the K/V in 3.09 GiB of pinned RAM\n")
    KV_GROW = ("strata generate: elastic K/V: 16384 of 262144 cells in VRAM (0.25 of 3.35 GiB); "
               "the expert cache (12226 slots) gives the K/V room below slot 10280 as the context grows\n")

    def setUp(self):
        super().setUp()
        self.layout = Layout(self.layout.root, Profile(PROFILE, single_gpu_data()))

    def test_start_keeps_legacy_idle_policy_without_multi_card_ownership_gates(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.55"
        server = procs.ProcInfo(100, 90, "server-created", "python.exe")

        def launch(*args, **kwargs):
            run = common.read_json(self.layout.run_record)
            run.update(state="starting", server=server.as_dict())
            common.atomic_write_json(self.layout.run_record, run)

        mismatched_but_idle = gpu_fact(self.layout.profile, self.layout.profile.gpu_indices[0])
        mismatched_but_idle.update(name="other model", memory_total_mib=1, driver="1.00")
        for gpu in ({"available": False}, mismatched_but_idle):
            with self.subTest(gpu=gpu):
                with patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}), \
                        patch.object(lifecycle, "read_key", return_value="x" * 32), \
                        patch.object(lifecycle, "running", return_value={}), \
                        patch.object(lifecycle, "port_in_use", return_value=False), \
                        patch.object(lifecycle.procs, "memory", return_value={"total": 1 << 40, "available": 1 << 40}), \
                        patch.object(lifecycle.procs, "matches", side_effect=lambda rec: server if rec == server.as_dict() else None), \
                        patch.object(lifecycle.procs, "descendants", return_value=[]), \
                        patch.object(lifecycle.time, "sleep"), \
                        patch.object(lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}), \
                        patch.object(lifecycle, "gpu_facts", return_value=gpu) as facts, \
                        patch.object(lifecycle, "card_observations", side_effect=AssertionError("multi-card-only gate")), \
                        patch.object(lifecycle, "_launch_detached", side_effect=launch):
                    result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                facts.assert_called_once_with(self.layout.profile.data["host"]["gpu_index"])
                self.assertEqual("healthy", result["state"])
                self.assertFalse(result["engine_found"])
                self.assertEqual({"state", "ready_s", "port", "engine_found", "log"}, set(result))
                run = common.read_json(self.layout.run_record)
                self.assertNotIn("engine_log", run)
                self.assertNotIn("log_start_offset", run)

    def test_pinned_ple_io_start_on_one_card_records_the_engine_log_interval(self):
        """2026-10-31: the first single-card PLE-direct profile reached a ready engine, then start failed with
        "strata.ple_io: 'engine_log'": only multi-card starts captured the engine log the PLE check reads."""
        strata = self.layout.profile.data["strata"]
        strata.update(engine_version="0.1.52", ple_io="direct")
        strata["expected_engine_flags"].extend(["--ple-io", "direct"])
        server = procs.ProcInfo(100, 90, "server-created", "python.exe")
        engine_log = self.layout.strata / "engine.log"
        engine_log.parent.mkdir(parents=True, exist_ok=True)
        old = "strata generate: --ple-io ram chosen by the residency policy (an earlier generation)\n"
        engine_log.write_text(old)
        common.atomic_write_json(self.layout.strata_config, {"log": str(engine_log)})
        probe = "PLE direct read probe: 112342 rows/s (fine)"

        def launch(*args, **kwargs):
            run = common.read_json(self.layout.run_record)
            run.update(state="starting", server=server.as_dict())
            with engine_log.open("a") as output:
                output.write(f"strata generate: {probe}\n")
            common.atomic_write_json(self.layout.run_record, run)

        with patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}), \
                patch.object(lifecycle, "read_key", return_value="x" * 32), \
                patch.object(lifecycle, "running", return_value={}), \
                patch.object(lifecycle, "port_in_use", return_value=False), \
                patch.object(lifecycle.procs, "memory", return_value={"total": 1 << 40, "available": 1 << 40}), \
                patch.object(lifecycle.procs, "matches", side_effect=lambda rec: server if rec == server.as_dict() else None), \
                patch.object(lifecycle.procs, "descendants", return_value=[]), \
                patch.object(lifecycle.time, "sleep"), \
                patch.object(lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}), \
                patch.object(lifecycle, "gpu_facts", return_value={"available": False}), \
                patch.object(lifecycle, "card_observations", side_effect=AssertionError("multi-card-only gate")), \
                patch.object(lifecycle, "_launch_detached", side_effect=launch), \
                patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        stop.assert_not_called()
        run = common.read_json(self.layout.run_record)
        self.assertEqual(probe, run["ple_io"]["direct_read_probe"])
        self.assertEqual(len(old.encode("utf-8")), run["ple_io"]["engine_log_interval"]["start"])
        self.assertNotIn("gpu_stage_order", run)

    def prepare_batch_mtp_start(self, engine_text, engine_prefix=""):
        strata = self.layout.profile.data["strata"]
        strata.update(engine_version="0.1.54", batch_mtp=True)
        strata["setup_args"]["parallel"] = 4
        if "--batch-mtp" not in strata["expected_engine_flags"]:
            strata["expected_engine_flags"].append("--batch-mtp")
        self.prepare_engine_start(engine_text, engine_prefix)

    def prepare_engine_start(self, engine_text, engine_prefix="", server_text="engine ready\n"):
        server = procs.ProcInfo(100, 90, "server-created", "python.exe")
        engine_log = self.layout.strata / "engine.log"
        engine_log.parent.mkdir(parents=True, exist_ok=True)
        engine_log.write_text(engine_prefix)
        cfg = {"log": str(engine_log)}
        if "engine_env" in self.layout.profile.data["strata"]:
            cfg["env"] = engine_env_union(self.layout.profile.data["strata"])
            source = self.layout.strata / "serve/server.py"
            source.parent.mkdir(exist_ok=True)
            source.write_text("# pinned stock source\n")
        common.atomic_write_json(self.layout.strata_config, cfg)

        def launch(*args, **kwargs):
            run = common.read_json(self.layout.run_record)
            run.update(state="starting", server=server.as_dict())
            server_log = self.layout.root / run["log"]
            server_log.parent.mkdir(parents=True, exist_ok=True)
            with server_log.open("a") as output:
                output.write(server_text)
            with engine_log.open("a") as output:
                output.write(engine_text)
            common.atomic_write_json(self.layout.run_record, run)

        self.enterContext(patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}))
        self.enterContext(patch.object(lifecycle, "read_key", return_value="x" * 32))
        self.enterContext(patch.object(lifecycle, "running", return_value={}))
        self.enterContext(patch.object(lifecycle, "port_in_use", return_value=False))
        self.enterContext(patch.object(lifecycle.procs, "memory", return_value={"available": 1 << 40}))
        self.enterContext(patch.object(lifecycle.procs, "matches", side_effect=lambda rec: server if rec == server.as_dict() else None))
        self.enterContext(patch.object(lifecycle.procs, "descendants", return_value=[]))
        self.enterContext(patch.object(lifecycle.time, "sleep"))
        self.enterContext(patch.object(lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}))
        self.enterContext(patch.object(lifecycle, "gpu_facts", return_value={"available": False}))
        self.enterContext(patch.object(lifecycle, "card_observations", side_effect=AssertionError("multi-card-only gate")))
        self.enterContext(patch.object(lifecycle, "_launch_detached", side_effect=launch))

    def test_0157_start_creates_only_root_local_runtime_and_process_folders(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.57"
        self.prepare_engine_start("engine ready\n")
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertTrue(self.layout.strata_runtime.is_dir())
        self.assertTrue(self.layout.localappdata.is_dir())
        self.assertEqual(self.layout.state, self.layout.strata_runtime.parent)

    def test_0158_standard_dflash2_refuses_a_stray_tuned_pack_before_launch(self):
        from omp_strata import dflash2
        from tests.unit.test_dflash2 import slot_variant_data

        data = slot_variant_data()
        data["strata"]["engine_version"] = "0.1.58"
        self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, data))
        self.layout.dflash2_dir.mkdir(parents=True)
        (self.layout.dflash2_dir / dflash2.TUNED_NAME).write_bytes(b"unrecorded tuned pack")
        self.prepare_engine_start("engine ready\n")
        with patch.object(lifecycle, "_launch_detached") as launch, \
                patch.object(lifecycle, "_finish_start", return_value={"state": "healthy"}), \
                self.assertRaisesRegex(lifecycle.LifecycleError, "stock DFlash2 folder: .*this profile does not pin"):
            lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        launch.assert_not_called()

    def test_0157_rollback_has_no_new_tuned_folder_refusal(self):
        from omp_strata import dflash2
        from tests.unit.test_dflash2 import slot_variant_data

        self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, slot_variant_data()))
        self.layout.dflash2_dir.mkdir(parents=True)
        (self.layout.dflash2_dir / dflash2.TUNED_NAME).write_bytes(b"unused by this old engine")
        self.prepare_engine_start("engine ready\n")
        with patch.object(lifecycle, "_launch_detached") as launch, \
                patch.object(lifecycle, "_finish_start", return_value={"state": "healthy"}):
            self.assertEqual("healthy", lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)["state"])
        launch.assert_called_once()

    def test_0157_start_refuses_each_new_walk_or_retry_line_in_either_stream(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.57"
        # Stock c3b3f503 generate.cpp:8499,7070,6526,4077; mmq_kq_loader.cpp:67; server.py:1284.
        lines = (
            "strata generate: short of GPU memory: CUDA1: the cache would have no room, so the output head "
            "(410 MiB) moves to pinned host memory and is read over PCIe for every logits row: decode is slower; "
            "the room for experts is now 1.00 GiB",
            "strata generate: short of GPU memory: CUDA1: 1.00 GiB is free, and DFlash2 (1.20 GiB with its "
            "buffers and draft head) and a working cache need about 3.40 GiB: this start runs without a drafter "
            "(decode is slower; STRATA_MTP_KEEP=1 keeps it)",
            "strata generate: short of GPU memory: the KV window is 32768 cells a layer in VRAM instead of "
            "the whole context, the rest is read from RAM: the context (262144 tokens) is unchanged",
            "strata generate: short of GPU memory: no other card has room, so the model runs on CUDA0 alone "
            "with the experts that do not fit in RAM",
            "strata: K-quant prompt kernels (STRATA_MMQ_KQ=1): strata_kq.dll not found next to the engine - "
            "these experts take the FP16 prompt path",
            "the engine ended before it was ready because a card was short of memory",
        )
        for line in lines:
            for stream in ("server", "engine"):
                with self.subTest(line=line, stream=stream):
                    self.prepare_engine_start(line + "\n" if stream == "engine" else "engine ready\n",
                                              server_text=line + "\n" if stream == "server" else "engine ready\n")
                    with patch.object(lifecycle, "stop") as stop, \
                            self.assertRaisesRegex(lifecycle.LifecycleError, "stock start fallback:"):
                        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                    stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_0156_keeps_its_existing_kv_window_start_check(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.56"
        line = ("strata generate: short of GPU memory: the KV window is 32768 cells a layer in VRAM instead of "
                "the whole context, the rest is read from RAM: the context (262144 tokens) is unchanged\n")
        self.prepare_engine_start(line)
        self.assertEqual("healthy", lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)["state"])

    def test_0157_refuses_multiple_single_card_auto_engine_generations(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.57"
        generation = "[strata] 2026-11-05 00:00:00 engine started: strata.exe\n"
        self.prepare_engine_start(generation * 2)
        with patch.object(lifecycle, "stop"), self.assertRaisesRegex(lifecycle.LifecycleError, "multiple engine generations"):
            lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.prepare_engine_start(generation, engine_prefix=generation * 2)
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual(1, common.read_json(self.layout.run_record)["start_fallbacks"]["generations"])

    def test_0157_short_memory_drafting_off_and_unknown_mtp_reason_still_refuse(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.57"
        for mode in ("off", "MTP"):
            line = f"[strata] Drafting: {mode} (the cards were short of memory)\n"
            self.prepare_engine_start("engine ready\n", server_text=line)
            with self.subTest(mode=mode), patch.object(lifecycle, "stop"), \
                    self.assertRaisesRegex(lifecycle.LifecycleError, "stock drafting:"):
                lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)

    def test_0157_bare_auto_records_every_current_nvidia_ceiling_line_without_gating(self):
        strata = self.layout.profile.data["strata"]
        strata["engine_version"] = "0.1.57"
        flags = strata["expected_engine_flags"]
        flags[flags.index("--prefill") + 1] = "auto"
        ceiling = ("strata generate: NVIDIA: --prefill auto may take chunks up to 32768 "
                   "(STRATA_NV_CHUNK=0 keeps 8192, =16 keeps 16384)\n")
        guard = ("strata generate: NVIDIA: prompt chunks stay at 16384: 32768 would lend 1024 more cache slots "
                 "(256 MiB more held in RAM during a prompt), and 8192 MiB of RAM is available for 4096 MiB "
                 "of resident experts plus that (#2090; STRATA_NV_CHUNK=1 takes the default ceiling anyway)\n")
        self.prepare_engine_start(ceiling + guard, engine_prefix=ceiling)
        self.assertEqual("healthy", lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)["state"])
        observation = common.read_json(self.layout.run_record)["prefill_ceiling"]
        self.assertEqual([ceiling.rstrip(), guard.rstrip()], observation["lines"])
        self.assertEqual(len(ceiling.encode()), observation["engine_log_interval"]["start"])

    def test_0157_explicit_prefill_does_not_record_a_bare_auto_observation(self):
        strata = self.layout.profile.data["strata"]
        strata["engine_version"] = "0.1.57"
        flags = strata["expected_engine_flags"]
        flags[flags.index("--prefill") + 1] = "auto:32768"
        self.prepare_engine_start("engine ready\n")
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertNotIn("prefill_ceiling", common.read_json(self.layout.run_record))

    def test_batch_mtp_single_card_start_captures_only_this_starts_on_line(self):
        old = self.BATCH_MTP_OFF
        self.prepare_batch_mtp_start(self.BATCH_MTP_ON, engine_prefix=old)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        stop.assert_not_called()
        run = common.read_json(self.layout.run_record)
        observation = run["batch_mtp"]
        self.assertEqual(self.BATCH_MTP_ON.strip(), observation["log_line"])
        self.assertEqual(run["engine_log"], observation["engine_log_interval"]["path"])
        self.assertEqual(len(old.encode("utf-8")), observation["engine_log_interval"]["start"])
        self.assertNotIn("gpu_stage_order", run)

    def test_batch_mtp_start_refuses_off_absent_and_malformed_lines_despite_older_on_evidence(self):
        cases = [(self.BATCH_MTP_ON + self.BATCH_MTP_OFF, "it needs batch slots"),
                 ("engine ready\n", "ON line absent"),
                 (self.BATCH_MTP_ON.replace("4 slot drafters", "slot drafters"), "ON line absent")]
        for text, reason in cases:
            with self.subTest(text=text):
                self.prepare_batch_mtp_start(text, engine_prefix=self.BATCH_MTP_ON)
                with patch.object(lifecycle, "stop") as stop, \
                        self.assertRaisesRegex(lifecycle.LifecycleError, "strata.batch_mtp:.*" + reason):
                    lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_engine_env_start_evidence_records_config_and_requires_the_self_commit_line(self):
        strata = self.layout.profile.data["strata"]
        env = dict(ENGINE_ENV_GROUPS["parallel_stack"])
        strata.update(engine_version="0.1.55", engine_env=env)
        strata["setup_args"]["parallel"] = 4
        self.prepare_engine_start(self.SELF_COMMIT, engine_prefix=self.BATCH_BASE)
        result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        observation = common.read_json(self.layout.run_record)["engine_env"]
        self.assertEqual(common.sha256_bytes(common.canonical_json(env)), observation["config_env_sha256"])
        self.assertEqual(sorted(env), observation["names"])
        self.assertEqual(common.sha256_file(self.layout.strata / "serve/server.py"), observation["server_source_sha256"])
        self.assertEqual(self.SELF_COMMIT.strip(), observation["batch_self_commit_line"])
        self.assertEqual(len(self.BATCH_BASE.encode()), observation["engine_log_interval"]["start"])
        for text in (self.BATCH_BASE, "engine ready\n", self.SELF_COMMIT + self.BATCH_BASE,
                     self.SELF_COMMIT.replace("keep their rows", "drop their rows")):
            with self.subTest(text=text):
                self.prepare_engine_start(text, engine_prefix=self.SELF_COMMIT)
                with patch.object(lifecycle, "stop") as stop, self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)
        self.prepare_engine_start(self.SELF_COMMIT)
        cfg = common.read_json(self.layout.strata_config)
        cfg["env"] = env | {"STRATA_BATCH_SELF_COMMIT": "0"}
        common.atomic_write_json(self.layout.strata_config, cfg)
        with patch.object(lifecycle, "stop") as stop, self.assertRaises(lifecycle.LifecycleError):
            lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_engine_env_without_self_commit_needs_no_line(self):
        self.layout.profile.data["strata"]["engine_env"] = dict(ENGINE_ENV_GROUPS["gdn_stack"])
        self.prepare_engine_start("engine ready\n")
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        observation = common.read_json(self.layout.run_record)["engine_env"]
        self.assertIsNone(observation["batch_self_commit_line"])
        self.assertEqual(sorted(ENGINE_ENV_GROUPS["gdn_stack"]), observation["names"])

    def test_engine_env_records_sorted_groups_and_delivery_proof_for_existing_lane_unions(self):
        for groups in (("parallel_stack", "gdn_stack"), ("gdn_stack",),
                       ("sm86_table", "gdn_stack", "select_two_pass")):
            self.layout.profile.data["strata"]["engine_env"] = {
                key: value for group in groups for key, value in ENGINE_ENV_GROUPS[group].items()}
            self.prepare_engine_start(self.SELF_COMMIT if "parallel_stack" in groups else "engine ready\n")
            with self.subTest(groups=groups):
                lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                observation = common.read_json(self.layout.run_record)["engine_env"]
                self.assertEqual(sorted(groups), observation["groups"])
                self.assertEqual({group: {"proof": "delivery"} for group in groups}, observation["group_evidence"])

    def test_engine_env_group_on_evidence_requires_one_full_line_from_this_start(self):
        self.layout.profile.data["strata"]["engine_env"] = dict(ENGINE_ENV_GROUPS["gdn_stack"])
        entry = {"on": (re.compile(r"fixture group on: \d+"),), "refuse": ("fixture group refused:",),
                 "cite": "fixture source:1"}
        on = "fixture group on: 1\n"
        with patch.dict(lifecycle.ENGINE_ENV_GROUP_EVIDENCE, {"gdn_stack": entry}, clear=True):
            self.prepare_engine_start(on, engine_prefix="fixture group refused: older start\n" + on)
            lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
            observation = common.read_json(self.layout.run_record)["engine_env"]
            self.assertEqual({"gdn_stack": {"lines": [on.strip()], "cite": entry["cite"]}},
                             observation["group_evidence"])
            for text in ("engine ready\n", on + on, on.rstrip() + " trailing text\n",
                         on + "fixture group refused: unsupported\n"):
                with self.subTest(text=text):
                    self.prepare_engine_start(text, engine_prefix=on)
                    with patch.object(lifecycle, "stop") as stop, \
                            self.assertRaisesRegex(lifecycle.LifecycleError, "strata.engine_env: gdn_stack:"):
                        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                    stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_qsa_split_attention_has_only_reviewed_refusals_and_no_positive_line(self):
        self.assertEqual({"qsa_split_attn"}, set(lifecycle.ENGINE_ENV_GROUP_EVIDENCE))
        entry = lifecycle.ENGINE_ENV_GROUP_EVIDENCE["qsa_split_attn"]
        self.assertEqual((), entry["on"])
        self.assertEqual(("qsa_decode_attn_split:", "strata verify: batch windows of up to"), entry["refuse"])
        env = ENGINE_ENV_GROUPS["gdn_stack"] | ENGINE_ENV_GROUPS["qsa_split_attn"]
        self.layout.profile.data["strata"]["engine_env"] = env
        refusals = ("qsa_decode_attn_split: invalid configuration argument\n", self.BATCH_BASE)
        self.prepare_engine_start("engine ready\n", engine_prefix="".join(refusals))
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        observation = common.read_json(self.layout.run_record)["engine_env"]
        self.assertEqual(["gdn_stack", "qsa_split_attn"], observation["groups"])
        self.assertEqual({"gdn_stack": {"proof": "delivery"},
                          "qsa_split_attn": {"lines": [], "cite": entry["cite"]}}, observation["group_evidence"])
        for text in refusals:
            with self.subTest(text=text):
                self.prepare_engine_start(text)
                with patch.object(lifecycle, "stop") as stop, \
                        self.assertRaisesRegex(lifecycle.LifecycleError, "strata.engine_env: qsa_split_attn:"):
                    lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)
        self.layout.profile.data["strata"]["engine_env"] = dict(ENGINE_ENV_GROUPS["gdn_stack"])
        self.prepare_engine_start("".join(refusals))
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)

    def test_engine_env_start_requires_and_records_the_exact_setup_env_union(self):
        strata = self.layout.profile.data["strata"]
        strata["engine_env"] = dict(ENGINE_ENV_GROUPS["gdn_stack"])
        strata["setup_env"] = {"STRATA_HC_Q8": "1", "STRATA_ROUTE_TAIL_SKIP": "0"}
        env = engine_env_union(strata)
        self.prepare_engine_start("engine ready\n")
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        observation = common.read_json(self.layout.run_record)["engine_env"]
        self.assertEqual(sorted(env), observation["names"])
        self.assertEqual(common.sha256_bytes(common.canonical_json(env)), observation["config_env_sha256"])
        for changed in (strata["engine_env"], strata["setup_env"], env | {"STRATA_UNKNOWN": "1"},
                        env | {"STRATA_ROUTE_TAIL_SKIP": "1"}):
            self.prepare_engine_start("engine ready\n")
            cfg = common.read_json(self.layout.strata_config)
            cfg["env"] = changed
            common.atomic_write_json(self.layout.strata_config, cfg)
            with self.subTest(env=changed), patch.object(lifecycle, "stop") as stop, \
                    self.assertRaisesRegex(lifecycle.LifecycleError, "setup_env and engine_env union"):
                lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
            stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_0156_stock_auto_records_mtp_and_both_intervals_without_other_pins(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.56"
        line = "[strata] Drafting: MTP (DFlash2 isn't available in this mode)"
        for server_text, expected in (("engine ready\n", None), (line + "\nengine ready\n", line)):
            with self.subTest(note=expected):
                old = "strata serve: DFlash2 drafter on (an older generation)\n"
                self.prepare_engine_start("engine ready\n", engine_prefix=old, server_text=server_text)
                with patch.object(lifecycle, "stop") as stop:
                    result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                self.assertEqual("healthy", result["state"])
                stop.assert_not_called()
                run = common.read_json(self.layout.run_record)
                self.assertEqual("mtp", run["drafting"]["mode"])
                self.assertEqual(expected, run["drafting"]["server_line"])
                self.assertEqual(len(old.encode()), run["drafting"]["engine_log_interval"]["start"])
                for field in ("drafting", "start_fallbacks"):
                    self.assertEqual(run["log"], run[field]["log_interval"]["path"])
                    self.assertEqual(run["engine_log"], run[field]["engine_log_interval"]["path"])

    def test_0156_stock_auto_refuses_every_non_mtp_or_retry_line_in_either_stream(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.56"
        # Stock v0.2.10 server.py:3517-3519,3538, drafting.py:423,428-431;
        # engine 06698c674 generate.cpp:11172,19717 (paths and numbers sanitized).
        lines = (
            "[strata] drafting: DFlash2 alone (--draft dflash2, --draft-conf 0.35)",
            "[strata] Drafting: DFlash2 (DFlash2 isn't available in this mode)",
            "[strata] Drafting: off (no drafter is downloaded yet)",
            "[strata] Drafting: MTP (DFlash2 didn't start)",
            '[strata] "mtp": false - starting without the draft layer (--mtp left out)',
            "strata serve: DFlash2 drafter on (pack, graphs captured in 100 ms); windows up to 6 tokens; no MTP layer is loaded (--draft-fallback none)",
            "strata generate: DFlash2 drafter on (pack, graphs captured in 100 ms), no MTP layer is loaded (--draft-fallback none)",
        )
        for line in lines:
            for stream in ("server", "engine"):
                with self.subTest(line=line, stream=stream):
                    self.prepare_engine_start(line + "\n" if stream == "engine" else "engine ready\n",
                                              server_text=line + "\n" if stream == "server" else "engine ready\n")
                    with patch.object(lifecycle, "stop") as stop, \
                            self.assertRaisesRegex(lifecycle.LifecycleError, "stock drafting:"):
                        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                    stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_0156_stock_auto_refuses_unknown_and_repeated_mtp_notes(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.56"
        note = "[strata] Drafting: MTP (DFlash2 isn't available in this mode)\n"
        for text in (note + note, "[strata] Drafting: MTP (an unreviewed reason)\n"):
            with self.subTest(text=text):
                self.prepare_engine_start("engine ready\n", server_text=text)
                with patch.object(lifecycle, "stop") as stop, self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_0156_start_refuses_each_stock_ram_or_vram_fallback_in_either_stream(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.56"
        # Stock v0.2.10 vram_fit.py:91, and engine 06698c674 generate.cpp:7323-7325,6736-6737,7609-7610,7699-7700.
        lines = (
            "[strata] This model on this 8 GB card: short of GPU memory: more is read from RAM and the SSD, expect it to be slower",
            "strata generate: not enough RAM for the expert arena (only 4 GiB free): this run reads the experts from the file, like --mmap-experts (slower; the answers are the same). To get the arena back, free that RAM and start again",
            "strata generate: short of GPU memory: 1.00 GiB is free, and the draft layer (1.00 GiB), the head (0.40 GiB) and a working cache need about 3.40 GiB: this start runs without the draft layer (decode is slower; STRATA_MTP_KEEP=1 keeps it)",
            "strata generate: short of GPU memory: the cache (64 slots) is too small to lend the prompt path 256-token buffers and keep 128 more: the loan keeps 16, prompts are read in smaller chunks, expect them to be slower",
            "strata generate: short of GPU memory: the cache had no room, so the output head (410 MiB) moves to pinned host memory and is read over PCIe for every logits row: decode is slower; the cache is now 64 slots",
        )
        for line in lines:
            for stream in ("server", "engine"):
                with self.subTest(line=line, stream=stream):
                    self.prepare_engine_start(line + "\n" if stream == "engine" else "engine ready\n",
                                              server_text=line + "\n" if stream == "server" else "engine ready\n")
                    with patch.object(lifecycle, "stop") as stop, \
                            self.assertRaisesRegex(lifecycle.LifecycleError, "stock start fallback:"):
                        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                    stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_pre0156_start_keeps_its_old_behavior_for_drafting_and_fallback_lines(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.55"
        text = ('[strata] "mtp": false - starting without the draft layer\n'
                "strata generate: not enough RAM for the expert arena (an older engine)\n")
        self.prepare_engine_start(text, server_text=text)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        stop.assert_not_called()
        run = common.read_json(self.layout.run_record)
        self.assertNotIn("drafting", run)
        self.assertNotIn("start_fallbacks", run)

    def test_kv_streaming_off_refuses_a_streaming_start_line(self):
        self.assertIsNotNone(lifecycle.KV_STREAMING_LINE.search(self.KV_STREAMING))
        self.layout.profile.data["strata"]["setup_args"]["kv_streaming"] = "off"
        self.prepare_engine_start("engine ready\n", engine_prefix=self.KV_STREAMING)
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        observation = common.read_json(self.layout.run_record)["kv_streaming"]
        self.assertEqual("off", observation["mode"])
        self.assertEqual(len(self.KV_STREAMING.encode()), observation["engine_log_interval"]["start"])
        self.prepare_engine_start("other startup output\n" + self.KV_STREAMING)
        with patch.object(lifecycle, "stop") as stop, self.assertRaises(lifecycle.LifecycleError):
            lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_kv_grow_start_evidence(self):
        strata = self.layout.profile.data["strata"]
        strata["kv_grow"] = True
        strata["setup_args"]["kv_streaming"] = "off"
        self.prepare_engine_start(self.KV_GROW, engine_prefix="earlier generation\n")
        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        observation = common.read_json(self.layout.run_record)["kv_grow"]
        self.assertEqual(self.KV_GROW.strip(), observation["log_line"])
        self.assertEqual(len("earlier generation\n"), observation["engine_log_interval"]["start"])
        for text in ("engine ready\n", self.KV_GROW.replace("gives the K/V room", "unknown behavior")):
            with self.subTest(text=text):
                self.prepare_engine_start(text, engine_prefix=self.KV_GROW)
                with patch.object(lifecycle, "stop") as stop, self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_start_captures_the_engine_log_for_every_engine_log_pin(self):
        base = copy.deepcopy(self.layout.profile.data)
        cases = (("ple_io", "direct", "engine ready\n"),
                 ("batch_mtp", True, self.BATCH_MTP_ON),
                 ("engine_env", dict(ENGINE_ENV_GROUPS["gdn_stack"]), "engine ready\n"),
                 ("kv_grow", True, self.KV_GROW), ("kv_streaming", "off", "engine ready\n"))
        for field, value, text in cases:
            self.layout = Layout(self.layout.root, Profile(PROFILE, copy.deepcopy(base)))
            strata = self.layout.profile.data["strata"]
            if field == "kv_streaming":
                strata["setup_args"][field] = value
            else:
                strata[field] = value
            if field == "kv_grow":
                strata["setup_args"]["kv_streaming"] = "off"
            with self.subTest(field=field):
                self.prepare_engine_start(text, engine_prefix="old\n")
                lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                run = common.read_json(self.layout.run_record)
                self.assertEqual(len("old\n"), run[field]["engine_log_interval"]["start"])
                self.assertEqual(run["engine_log"], run[field]["engine_log_interval"]["path"])

    def test_scalar_doctor_retains_legacy_unavailable_check(self):
        with patch.object(lifecycle, "gpu_facts", return_value={"available": False, "reason": "new detail"}) as facts, \
                patch.object(lifecycle, "port_in_use", return_value=False):
            checks = lifecycle.doctor(self.layout)["checks"]
        facts.assert_called_once_with(self.layout.profile.gpu_indices[0])
        self.assertIn({"check": "gpu", "ok": False, "detail": "nvidia-smi unavailable", "blocking": True}, checks)

    def test_start_generation_replacement_refuses_without_stopping_the_replacement(self):
        foreign = {}

        def launch(argv, **_kwargs):
            with lifecycle.FileLock(self.layout.lock_file):
                record = common.read_json(self.layout.run_record)
                self.assertEqual(argv[argv.index("--launch-id") + 1], record["launch_id"])
                record.update(launch_id="competing-launch", experiment_launch_id="competing-marker")
                foreign.update(record)
                common.atomic_write_json(self.layout.run_record, record)

        # An installed root always has its stock run config; 0.1.56+ starts capture its engine log before launch.
        common.atomic_write_json(self.layout.strata_config, {"log": str(self.layout.strata / "engine.log")})
        with patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}), \
                patch.object(lifecycle, "read_key", return_value="fixture-key"), \
                patch.object(lifecycle, "running", return_value={}), \
                patch.object(lifecycle, "port_in_use", return_value=False), \
                patch.object(lifecycle, "gpu_busy", return_value=None), \
                patch.object(lifecycle.procs, "memory", return_value={"available": 0}), \
                patch.object(lifecycle.time, "sleep"), \
                patch.object(lifecycle, "_launch_detached", side_effect=launch), \
                patch.object(lifecycle, "stop") as stop, \
                self.assertRaisesRegex(lifecycle.LifecycleError, "generation changed"):
            lifecycle.start(self.layout, tool_argv=["fixture"], log=self.messages.append)
        stop.assert_not_called()
        self.assertEqual(foreign, common.read_json(self.layout.run_record))


class DownloadTests(LifecycleFixture):
    def setUp(self):
        super().setUp()
        self.payload = b"pinned artifact bytes\n" * 32
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.hits = 0
        fixture = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                fixture.hits += 1
                self.send_response(200)
                self.send_header("Content-Length", str(len(fixture.payload)))
                self.end_headers()
                self.wfile.write(fixture.payload)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()

        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.addCleanup(cleanup)
        self.url = f"https://127.0.0.1:{server.server_port}/artifact"
        self.dest = self.directory / "artifact.bin"
        # Keep the product's HTTPS-only validation. Only transport is redirected to
        # plaintext loopback; response streaming, pin verification and promotion are real.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def loopback_open(request, *, timeout):
            self.assertEqual(self.url, request.full_url)
            local = urllib.request.Request(request.full_url.replace("https://", "http://", 1),
                                           headers=dict(request.header_items()))
            return opener.open(local, timeout=timeout)
        self.enterContext(patch.object(common.urllib.request, "urlopen", side_effect=loopback_open))

    def download(self, *, size=None, digest=None):
        return common.download_verified(self.url, self.dest, len(self.payload) if size is None else size,
                                        self.digest if digest is None else digest, source="test fixture",
                                        retries=0, timeout=5, log=self.messages.append)

    def assert_not_promoted(self):
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.dest.with_name(self.dest.name + ".partial").exists())
        self.assertFalse(self.dest.with_name(self.dest.name + ".verified.json").exists())

    def test_verified_download_is_promoted_cached_and_reused_without_network(self):
        self.assertEqual(self.dest, self.download())
        self.assertEqual(self.payload, self.dest.read_bytes())
        self.assertTrue(common.verified_ok(self.dest, len(self.payload), self.digest))
        marker = common.read_json(self.dest.with_name(self.dest.name + ".verified.json"))
        self.assertEqual(self.digest, marker["sha256"])
        self.assertEqual(len(self.payload), marker["bytes"])
        self.assertFalse(self.dest.with_name(self.dest.name + ".partial").exists())
        self.assertEqual(1, self.hits)
        self.download()
        self.assertEqual(1, self.hits)

    def test_hash_mismatch_discards_partial_and_never_promotes(self):
        with self.assertRaisesRegex(common.IntegrityError, "sha256"):
            self.download(digest=hashlib.sha256(b"different artifact").hexdigest())
        self.assertEqual(1, self.hits)
        self.assert_not_promoted()

    def test_size_overrun_discards_partial_and_never_promotes(self):
        with self.assertRaisesRegex(common.IntegrityError, "more than the pinned"):
            self.download(size=len(self.payload) - 1)
        self.assertEqual(1, self.hits)
        self.assert_not_promoted()

    def test_plain_http_is_rejected_before_network(self):
        with self.assertRaisesRegex(ValueError, "non-HTTPS"):
            common.download_verified(self.url.replace("https://", "http://"), self.dest,
                                     len(self.payload), self.digest, source="test fixture")
        self.assertEqual(0, self.hits)
        self.assert_not_promoted()

    def test_verify_file_rejects_missing_size_and_content_drift(self):
        def verify():
            common.verify_file(self.dest, len(self.payload), self.digest,
                               source="test fixture", log=self.messages.append)
        with self.assertRaisesRegex(common.IntegrityError, "missing"):
            verify()
        self.download()
        previous_mtime = self.dest.stat().st_mtime_ns
        self.dest.write_bytes(b"x" * len(self.payload))
        os.utime(self.dest, ns=(previous_mtime + 1000000, previous_mtime + 1000000))
        self.assertFalse(common.verified_ok(self.dest, len(self.payload), self.digest))
        with self.assertRaisesRegex(common.IntegrityError, "sha256"):
            verify()
        self.dest.write_bytes(self.payload[:-1])
        with self.assertRaisesRegex(common.IntegrityError, "bytes, expected"):
            verify()
        self.assertEqual(1, self.hits)

    def test_deep_verification_rehashes_even_when_cached_metadata_matches(self):
        self.download()
        before = self.dest.stat()
        self.dest.write_bytes(b"x" * len(self.payload))
        os.utime(self.dest, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertTrue(common.verified_ok(self.dest, len(self.payload), self.digest))
        with self.assertRaisesRegex(common.IntegrityError, "sha256"):
            common.verify_file(self.dest, len(self.payload), self.digest, source="test fixture",
                               deep=True, log=self.messages.append)


class GpuOccupancyTests(unittest.TestCase):
    """A GPU that drives a display lists its desktop processes as WDDM graphics clients ("C+G"); only a compute
    process or busy VRAM means another runtime holds it."""

    LISTING = """<?xml version="1.0" ?><nvidia_smi_log><gpu><processes>
        <process_info><pid>2616</pid><type>C+G</type><process_name>dwm.exe</process_name></process_info>
        <process_info><pid>4242</pid><type>C</type><process_name>runtime.exe</process_name></process_info>
        </processes></gpu></nvidia_smi_log>"""

    @staticmethod
    def gpu(used=300, compute=0, graphics=2):
        return {"available": True, "memory_used_mib": used, "compute_apps": compute, "graphics_apps": graphics}

    def test_processes_keep_their_nvidia_smi_type(self):
        self.assertEqual([{"pid": 2616, "type": "C+G"}, {"pid": 4242, "type": "C"}],
                         lifecycle.gpu_processes(self.LISTING))

    def test_display_clients_are_tolerated_only_on_a_display_attached_profile(self):
        self.assertIsNone(lifecycle.gpu_busy(self.gpu(), display_attached=True))
        self.assertIn("2 graphics client(s)", lifecycle.gpu_busy(self.gpu(), display_attached=False))

    def test_a_compute_process_or_busy_vram_is_refused_even_on_a_display(self):
        self.assertIsNotNone(lifecycle.gpu_busy(self.gpu(compute=1, graphics=0), display_attached=True))
        self.assertIsNotNone(lifecycle.gpu_busy(self.gpu(used=lifecycle.GPU_IDLE_MIB), display_attached=True))


class GpuFactsTests(unittest.TestCase):
    CSV = "1, NVIDIA GeForce RTX 4090, 00000000:02:00.0, 24564, 300, 8.9, 600.01, Disabled\n"
    XML = "<nvidia_smi_log><gpu><processes/></gpu></nvidia_smi_log>"

    def facts(self, csv=None, xml=None, code=0, attached="1, No\n", attached_code=0):
        with patch.object(lifecycle.shutil, "which", return_value="nvidia-smi"), \
                patch.object(lifecycle.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 0, self.CSV if csv is None else csv),
                    subprocess.CompletedProcess([], code, self.XML if xml is None else xml),
                    subprocess.CompletedProcess([], attached_code, attached)]):
            return lifecycle.gpu_facts(1, multi_gpu=True)

    def test_indexed_architecture_and_pci_facts(self):
        facts = self.facts()
        self.assertTrue(facts["available"])
        self.assertEqual("89", facts["arch"])
        self.assertEqual("00000000:02:00.0", facts["pci_bus_id"])
        self.assertEqual(1, facts["gpu_index"])
        self.assertEqual([], facts["processes"])
        self.assertEqual("00000000:ab:00.0", lifecycle.canonical_pci_bus_id("0000:AB:00.0"))

    def test_physical_attachment_is_not_inferred_from_display_active(self):
        self.assertTrue(self.facts(attached="1, Yes\n")["display_attached"])
        self.assertFalse(self.facts(attached="1, No\n")["display_attached"])
        for attached, code in (("1, Yes\n", 1), ("1, N/A\n", 0), ("1, Enabled\n", 0),
                               ("0, Yes\n", 0), ("", 0), ("1, Yes\n1, No\n", 0)):
            with self.subTest(attached=attached, code=code):
                facts = self.facts(attached=attached, attached_code=code)
                self.assertTrue(facts["available"])
                self.assertIsNone(facts["display_attached"])

    def test_scalar_query_and_process_policy_remain_unchanged(self):
        listing = self.XML.replace("<processes/>", "<processes><process_info><pid>bad</pid></process_info>"
                                  "<process_info><pid>42</pid></process_info></processes>")
        with patch.object(lifecycle.shutil, "which", return_value="nvidia-smi"), \
                patch.object(lifecycle.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 0, "NVIDIA GeForce RTX 3090, 24576, 300, 600.01\n"),
                    subprocess.CompletedProcess([], 0, listing)]) as query:
            gpu = lifecycle.gpu_facts(0)
        self.assertEqual({"available": True, "name": "NVIDIA GeForce RTX 3090", "memory_total_mib": 24576,
                          "memory_used_mib": 300, "driver": "600.01", "compute_apps": 1, "graphics_apps": 0,
                          "processes": [{"pid": 42, "type": "C"}]}, gpu)
        self.assertEqual(2, query.call_count)
        self.assertIn("--query-gpu=name,memory.total,memory.used,driver_version", query.call_args_list[0].args[0])
        self.assertIsNone(lifecycle.gpu_busy({"available": False}, True))

    def test_failed_malformed_or_missing_process_query_fails_closed(self):
        for xml, code in ((self.XML, 1), ("<nvidia_smi_log>", 0), ("<unrelated/>", 0),
                          ("<nvidia_smi_log><gpu/></nvidia_smi_log>", 0),
                          (self.XML.replace("<processes/>", "<processes>N/A</processes>"), 0),
                          (self.XML.replace("<processes/>", "<processes><process_info><pid>bad</pid></process_info></processes>"), 0)):
            with self.subTest(xml=xml, code=code):
                facts = self.facts(xml=xml, code=code)
                self.assertFalse(facts["available"])
                profile = Profile(PROFILE, multi_gpu_data())
                with patch.object(lifecycle, "gpu_facts", return_value=facts):
                    self.assertTrue(all(row["problems"] for row in lifecycle.card_observations(profile)))

    def test_csv_requires_exact_columns_identity_and_numeric_values(self):
        for csv in ("", self.CSV + self.CSV, self.CSV.replace("24564", "N/A"), self.CSV.replace("1, NVIDIA", "0, NVIDIA"),
                    self.CSV.replace("8.9", "unknown"), self.CSV.replace("600.01", "unknown"),
                    self.CSV.replace("Disabled", "N/A"), self.CSV.replace("300", "99999"), '"unterminated'):
            with self.subTest(csv=csv):
                self.assertFalse(self.facts(csv=csv)["available"])


class StageOrderTests(unittest.TestCase):
    ENGINE = ("strata generate: layer split: CUDA1 runs layers 44-47, expert cache 1024 slots "
              "(2.26 GiB), 1024 of its 1024 profiled pairs; slot 0 verified\n"
              "strata generate: layer split: CUDA0 runs layers 0-43\n"
              "strata generate: expert cache 9336 slots, 17.51 GiB of VRAM; policy is\n"
              "strata generate: layer split: CUDA1 PCIe probe 6.2 GB/s (best of 6.2 6.2 6.2 6.2) -> pcie_frac 0.17\n")
    REORDER = '[strata] layer split: card order 0,1 (the faster card last; "gpu_order": "as_given" keeps 1,0, #1352)\n'
    KEEP = ('[strata] layer split: keeping card order 1,0 - the faster card has less VRAM than the one the split ends on '
            '(24564 vs 24576 MiB, #1576)\n')

    def test_reorder_keep_and_complete_silent_configured_order(self):
        for text, staged, event in ((self.REORDER, [0, 1], "reordered"), (self.KEEP, [1, 0], "kept_1576"),
                                    ("engine ready\n", [1, 0], "kept_configured"),
                                    (self.REORDER * 2, [0, 1], "reordered")):
            result = lifecycle.parse_stage_order(text, [1, 0])
            self.assertTrue(result["complete"], result)
            self.assertEqual(staged, result["staged"])
            self.assertEqual(event, result["event"])

    def test_contradictory_unknown_and_truncated_output_is_unavailable(self):
        for text in (self.REORDER + self.KEEP, self.REORDER.rstrip(), "engine rea", self.REORDER.replace("0,1", "2,1"),
                     "[strata] layer split: changed cards somehow\n", self.KEEP.replace("1,0", "0,1")):
            result = lifecycle.parse_stage_order(text, [1, 0])
            self.assertFalse(result["complete"], result)
            self.assertIsNone(result["staged"])
            self.assertEqual("unavailable", result["event"])


class MultiGpuLifecycleTests(LifecycleFixture):
    def setUp(self):
        super().setUp()
        data = multi_gpu_data()
        data["server"] = self.layout.profile.data["server"]
        self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, data))
        self.server = procs.ProcInfo(100, 90, "server-created", "python.exe")
        self.engine = procs.ProcInfo(101, 100, "engine-created", "strata.exe")

    def gpu(self, index, processes=(), used=300, **kwargs):
        return gpu_fact(self.layout.profile, index, processes, used)

    def record(self, text="engine ready\n", engine_text=StageOrderTests.ENGINE, engine_prefix=""):
        log = self.layout.logs / "server.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(text)
        engine_log = self.layout.strata / "engine.log"
        engine_log.parent.mkdir(parents=True, exist_ok=True)
        engine_log.write_text(engine_prefix + engine_text)
        rec = {"state": "ready", "server": self.server.as_dict(), "engine": self.engine.as_dict(),
               "runtime_identity_sha256": "a" * 64, "log": "logs/server.log", "log_start_offset": 0,
               "engine_log": engine_log.relative_to(self.layout.root).as_posix(),
               "engine_log_start_offset": len(engine_prefix.encode("utf-8"))}
        common.atomic_write_json(self.layout.run_record, rec)
        common.atomic_write_json(self.layout.install_record, {
            "profile_fingerprint": self.layout.profile.fingerprint, "runtime_identity_sha256": "a" * 64})
        return rec

    def matches(self, identity):
        return next((p for p in (self.server, self.engine) if identity == p.as_dict()), None)

    def test_per_card_display_policy_and_same_owned_pid_on_both_cards(self):
        def active(index, **kwargs):
            processes = [{"pid": 101, "type": "C"}]
            if index == 0:
                processes += [{"pid": 200, "type": "C+G"}, {"pid": 201, "type": "G"}]
            return self.gpu(index, processes, used=20000)
        with patch.object(lifecycle, "gpu_facts", side_effect=active):
            rows = lifecycle.card_observations(self.layout.profile, owned_pids={101})
        self.assertEqual([1, 0], [r["gpu_index"] for r in rows])
        self.assertEqual([1, 1], [r["owned_count"] for r in rows])
        self.assertEqual([[], []], [r["problems"] for r in rows])
        self.assertEqual([0, 2], [r["graphics_client_count"] for r in rows])
        for kind in ("C", "unknown", "G", "C+G"):
            with patch.object(lifecycle, "gpu_facts", side_effect=lambda i, **kwargs: self.gpu(i, [{"pid": 200, "type": kind}])):
                rows = lifecycle.card_observations(self.layout.profile)
            self.assertTrue(rows[0]["problems"])
            self.assertEqual(kind not in ("G", "C+G"), bool(rows[1]["problems"]))

    def test_identity_capacity_driver_and_unavailable_card_are_problems(self):
        for key, value in (("arch", "86"), ("pci_bus_id", "00000000:03:00.0"), ("gpu_index", 7),
                           ("name", "NVIDIA other card"), ("memory_total_mib", 10000), ("driver", "100.01"),
                           ("available", False)):
            with self.subTest(key=key), patch.object(lifecycle, "gpu_facts", side_effect=lambda i, **kwargs: self.gpu(i) | {key: value}):
                self.assertTrue(lifecycle.card_observations(self.layout.profile)[0]["problems"])

    def test_multi_card_physical_attachment_mismatch_or_unknown_is_a_problem(self):
        for observation in (None, True, False):
            def facts(index, **kwargs):
                return self.gpu(index) | {"display_active": False, "display_attached": observation}
            with self.subTest(attached=observation), patch.object(lifecycle, "gpu_facts", side_effect=facts) as query:
                rows = lifecycle.card_observations(self.layout.profile)
            for row, card in zip(rows, self.layout.profile.gpu_requirements):
                bad = observation is None or observation != card["display_attached"]
                self.assertEqual(bad, any("physical display_attached" in p for p in row["problems"]))
            self.assertEqual([{"multi_gpu": True}, {"multi_gpu": True}], [call.kwargs for call in query.call_args_list])

    def test_doctor_checks_every_card_and_preserves_legacy_names(self):
        single = Layout(self.layout.root, Profile(PROFILE, single_gpu_data()))
        subjects = {"two-card fixture": self.layout, "selected lane": Layout(self.layout.root, load(PROFILE)),
                    "explicit single card": single}
        for name, layout in subjects.items():
            with self.subTest(subject=name), \
                    patch.object(lifecycle, "gpu_facts", side_effect=lambda index, **kwargs: gpu_fact(layout.profile, index)) as facts, \
                    patch.object(lifecycle, "host_platform", return_value="windows-x64"), \
                    patch.object(lifecycle, "port_in_use", return_value=False):
                checks = {check["check"]: check for check in lifecycle.doctor(layout)["checks"]}
            self.assertEqual(list(layout.profile.gpu_indices), [call.args[0] for call in facts.call_args_list])
            for card in layout.profile.gpu_requirements:
                suffix = f".{card['gpu_index']}" if layout.profile.multi_gpu else ""
                fields = ["gpu_model", "gpu_vram", "driver", "gpu_idle"]
                if layout.profile.multi_gpu:
                    fields += ["gpu_index", "pci_bus_id", "arch", "display_active"]
                for field in fields:
                    self.assertIn(field + suffix, checks)
                    self.assertTrue(checks[field + suffix]["ok"], checks[field + suffix])

    def test_start_unavailable_facts_never_launches(self):
        with patch.object(lifecycle, "verify_install_fast", return_value={}), \
                patch.object(lifecycle, "read_key", return_value="x" * 32), \
                patch.object(lifecycle, "gpu_facts", return_value={"available": False}), \
                patch.object(lifecycle, "_launch_detached") as launch:
            with self.assertRaisesRegex(lifecycle.LifecycleError, "facts unavailable"):
                lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        launch.assert_not_called()

    def prepare_start(self, foreign=False, engine_prefix="", engine_text=StageOrderTests.ENGINE, server_text=""):
        engine_log = self.layout.strata / "engine.log"
        engine_log.parent.mkdir(parents=True, exist_ok=True)
        engine_log.write_text(engine_prefix)
        strata = self.layout.profile.data["strata"]
        cfg = {"log": str(engine_log)}
        if "engine_env" in strata or "setup_env" in strata:
            cfg["env"] = engine_env_union(strata)
        if "engine_env" in strata:
            source = self.layout.strata / "serve/server.py"
            source.parent.mkdir(exist_ok=True)
            source.write_text("# pinned stock source\n")
        common.atomic_write_json(self.layout.strata_config, cfg)
        self.enterContext(patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}))
        self.enterContext(patch.object(lifecycle, "read_key", return_value="x" * 32))
        self.enterContext(patch.object(lifecycle, "running", return_value={}))
        self.enterContext(patch.object(lifecycle, "port_in_use", return_value=False))
        self.enterContext(patch.object(lifecycle.procs, "memory", return_value={"total": 1 << 40, "available": 1 << 40}))
        self.enterContext(patch.object(lifecycle.procs, "matches", side_effect=self.matches))
        self.enterContext(patch.object(lifecycle.procs, "descendants", return_value=[self.engine]))
        self.enterContext(patch.object(lifecycle.time, "sleep"))
        self.enterContext(patch.object(lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}))
        launched = False

        def launch(*args, **kwargs):
            nonlocal launched
            launched = True
            rec = common.read_json(self.layout.run_record)
            rec.update(state="starting", server=self.server.as_dict())
            log = self.layout.root / rec["log"]
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a") as output:
                output.write("engine ready\n" if self.layout.profile.data["strata"]["setup_args"].get("layer_split") != "auto"
                             else StageOrderTests.REORDER)
                output.write(server_text)
            with engine_log.open("a") as output:
                output.write(engine_text)
            common.atomic_write_json(self.layout.run_record, rec)

        def facts(index, **kwargs):
            processes = [{"pid": 101, "type": "C"}] if launched else []
            if launched and foreign and index == 0:
                processes.append({"pid": 999, "type": "C"})
            return self.gpu(index, processes, used=20000 if launched else 300)
        self.enterContext(patch.object(lifecycle, "_launch_detached", side_effect=launch))
        self.enterContext(patch.object(lifecycle, "gpu_facts", side_effect=facts))

    def test_selected_profile_start_records_all_of_its_pinned_engine_options(self):
        data = common.read_json(PROFILE)
        data["server"] = self.layout.profile.data["server"]
        self.layout = Layout(self.layout.root, Profile(PROFILE, data))
        strata = data["strata"]
        text = "engine ready\n"
        if self.layout.profile.multi_gpu:
            configured_split = strata["setup_args"]["layer_split"]
            split = 44 if configured_split == "auto" else int(configured_split)
            text += StageOrderTests.ENGINE.replace("0-43", f"0-{split - 1}").replace("44-47", f"{split}-47")
            if "trim_stage_weights" in strata:
                text += self.TRIM_ON.replace("0-43", f"0-{split - 1}").replace("44-47", f"{split}-47")
            if "pipeline_windows" in strata:
                text += self.PIPELINE_ON
        if "ple_io" in strata:
            text += "strata generate: PLE direct read probe: 112342 rows/s (fine)\n"
        if "batch_mtp" in strata:
            text += SingleGpuLifecycleTests.BATCH_MTP_ON
        if strata.get("engine_env", {}).get("STRATA_BATCH_SELF_COMMIT") == "1":
            text += SingleGpuLifecycleTests.SELF_COMMIT
        if "kv_grow" in strata:
            text += SingleGpuLifecycleTests.KV_GROW
        server_text = ""
        if strata.get("drafting") == "dflash2":
            pin = data["model"]["dflash2_source"]
            runtime = dflash2.runtime_file(pin)  # the tuned pack when the candidate pins one
            pack = self.layout.dflash2_dir / runtime["file"]
            host = data["host"]
            blackwell = not self.layout.profile.multi_gpu and host.get("gpu_model") in (
                "NVIDIA RTX PRO 6000 Blackwell Workstation Edition", "NVIDIA GeForce RTX 5090")
            wide = (blackwell and host["min_gpu_vram_mib"] * 1024**2 >= 48_000_000_000
                    and common.release_version(strata["engine_version"]) >= (0, 1, 59))
            window = 6 if blackwell and not wide else 8
            confidence = "0.55" if wide and dflash2.is_tuned(pin) and strata["setup_args"]["model"] == "IQ3_S" else "0.35"
            server_text = f"[strata] drafting: DFlash2 alone (--draft dflash2, --draft-conf {confidence})\n"
            text += "[strata] 2026-11-03 12:00:00 engine started: fixture generation\n"
            engine_line = (f"strata serve: DFlash2 drafter on ({pack}, graphs captured in 100 ms); "
                           f"windows up to {window} tokens; no MTP layer is loaded (--draft-fallback none)")
            if self.layout.profile.multi_gpu:
                stage = len(self.layout.profile.gpu_indices) - 1
                engine_line += (f"; layer split: the drafter is on CUDA{stage} (last stage), "
                                "the other stages' taps are gathered onto it")
            text += engine_line + "\n"
            selector_line = ("strata dflash2: selector codebooks: Q4_0 rows (about 174 MiB less than bf16)"
                             if pin["runtime_pack"] == "selq4" else None)
            if selector_line:
                text += selector_line + "\n"
            parallel = strata["setup_args"].get("parallel")
            if parallel is not None:
                batch_on = (f"strata generate: STRATA_BATCH_DF2: {parallel} slot drafters on CUDA0 "
                            "(256 MiB of private K/V ring and buffers each, sharing the solo drafter's pack); "
                            "10.25 GiB free there")
                batch_ready = (f"strata serve: STRATA_BATCH_DF2: {parallel} slot drafters ready "
                               "(batch windows carry each slot's token and its spare-row drafts)")
                text += batch_on + "\n" + batch_ready + "\n"
        old = SingleGpuLifecycleTests.KV_STREAMING + SingleGpuLifecycleTests.BATCH_BASE + self.PLE_RAM
        self.prepare_start(engine_prefix=old, engine_text=text, server_text=server_text)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        stop.assert_not_called()
        self.assertEqual("healthy", result["state"])
        run = common.read_json(self.layout.run_record)
        for field in ("ple_io", "batch_mtp", "trim_stage_weights", "pipeline_windows", "engine_env", "kv_grow",
                      "kv_streaming", "drafting"):
            pinned = field in strata or field == "kv_streaming" and strata["setup_args"].get(field) == "off"
            pinned = pinned or field == "drafting" and self.layout.profile.start_path_reviewed
            with self.subTest(field=field):
                self.assertEqual(pinned, field in run)
                if pinned:
                    self.assertEqual(len(old.encode()), run[field]["engine_log_interval"]["start"])
        if self.layout.profile.start_path_reviewed:
            drafting = run["drafting"]
            self.assertEqual(strata.get("drafting", "mtp"), drafting["mode"])
            self.assertEqual(run["log"], drafting["log_interval"]["path"])
            self.assertEqual(run["engine_log"], drafting["engine_log_interval"]["path"])
            if strata.get("drafting") == "dflash2":
                self.assertEqual(server_text.strip(), drafting["server_line"])
                self.assertEqual(engine_line, drafting["engine_line"])
                self.assertEqual(selector_line, drafting["selector_line"])
                self.assertEqual(window, drafting["window_tokens"])
                self.assertEqual(pack.relative_to(self.layout.root).as_posix(), drafting["pack"])
                self.assertEqual(runtime["sha256"], drafting["pack_sha256"])
                if parallel is not None:
                    self.assertEqual({"count": parallel, "cuda": 0, "mib_each": 256,
                                      "on_line": batch_on, "ready_line": batch_ready}, drafting["slot_drafters"])
                else:
                    self.assertNotIn("slot_drafters", drafting)

    PIPELINE_ON = ("strata serve: --pipeline-windows 2: two verifiers per stage, 2 stages overlap across windows"
                   " (decode too; the GDN snapshots beside the window)\n")
    PIPELINE_CRITICAL = ("strata serve: --pipeline-windows 2: two verifiers per stage, 2 stages overlap across windows"
                         " (decode too; the GDN snapshot on the critical path)\n")
    PIPELINE_PREFILL = ("strata serve: --pipeline-windows 2: two verifiers per stage, 2 stages overlap across windows\n")

    def pin_pipeline(self):
        strata = self.layout.profile.data["strata"]
        strata["setup_args"].pop("parallel", None)
        strata["pipeline_windows"] = 2
        strata["expected_engine_flags"].extend(["--pipeline-windows", "2"])

    def test_pipeline_windows_start_records_decode_capable_pipeline(self):
        self.pin_pipeline()
        for line in (self.PIPELINE_ON, self.PIPELINE_CRITICAL):
            with self.subTest(line=line):
                old = "old generation\n" + self.PIPELINE_PREFILL
                self.prepare_start(engine_prefix=old, engine_text=StageOrderTests.ENGINE + line)
                with patch.object(lifecycle, "stop") as stop:
                    result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                self.assertEqual("healthy", result["state"])
                stop.assert_not_called()
                observation = common.read_json(self.layout.run_record)["pipeline_windows"]
                self.assertEqual(line.strip(), observation["log_line"])
                self.assertEqual(len(old.encode("utf-8")), observation["engine_log_interval"]["start"])

    def test_pipeline_windows_start_rejects_off_prefill_only_and_absent_lines(self):
        self.pin_pipeline()
        cases = [("strata generate: --pipeline-windows 2 is off: not with --batch slots\n", "not with --batch slots"),
                 ("strata generate: --pipeline-windows 2 is off: it needs the MTP drafter (--mtp, --spec)\n",
                  "it needs the MTP drafter (--mtp, --spec)"),
                 (self.PIPELINE_PREFILL, self.PIPELINE_PREFILL.strip()), ("", "absent")]
        for line, reason in cases:
            with self.subTest(reason=reason):
                self.prepare_start(engine_prefix=self.PIPELINE_ON, engine_text=StageOrderTests.ENGINE + line)
                with patch.object(lifecycle, "stop") as stop:
                    with self.assertRaises(lifecycle.LifecycleError) as error:
                        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                self.assertIn("strata.pipeline_windows", str(error.exception))
                self.assertIn(reason, str(error.exception))
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_unpinned_pipeline_windows_start_ignores_engine_pipeline_lines(self):
        off = "strata generate: --pipeline-windows 2 is off: not with --batch slots\n"
        self.prepare_start(engine_text=StageOrderTests.ENGINE + off + self.PIPELINE_PREFILL)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        self.assertNotIn("pipeline_windows", common.read_json(self.layout.run_record))
        stop.assert_not_called()

    PLE_RAM = ("strata generate: --ple-io ram chosen by the residency policy "
               "(unrecorded policy details; --ple-io direct forces them)\n")

    def pin_ple_io(self):
        strata = self.layout.profile.data["strata"]
        strata.update(engine_version="0.1.52", ple_io="direct")
        strata["expected_engine_flags"].extend(["--ple-io", "direct"])

    def test_ple_io_start_refuses_the_residency_policys_ram_choice(self):
        self.pin_ple_io()
        for mode in ("ram", "auto"):
            with self.subTest(mode=mode):
                self.prepare_start(engine_text=StageOrderTests.ENGINE + self.PLE_RAM.replace("--ple-io ram", "--ple-io " + mode))
                with patch.object(lifecycle, "stop") as stop:
                    with self.assertRaises(lifecycle.LifecycleError) as error:
                        lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                self.assertEqual(f"strata.ple_io: residency policy chose {mode!r}, expected 'direct'", str(error.exception))
                self.assertNotIn("unrecorded policy details", str(error.exception))
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_ple_io_start_passes_old_policy_or_direct_choice_and_records_only_the_probe(self):
        self.pin_ple_io()
        old = self.PLE_RAM + "PLE direct read probe: 1 rows/s (slow)\n"
        direct = self.PLE_RAM.replace("--ple-io ram", "--ple-io direct")
        probe = "PLE direct read probe: 110868 rows/s (fine)"
        cases = [("", None), (direct, None),
                 (direct + "PLE direct read probe: 2 rows/s (slow)\n"
                  + "context before " + probe + " context after\n", probe)]
        for text, expected in cases:
            with self.subTest(text=text):
                self.prepare_start(engine_prefix=old, engine_text=StageOrderTests.ENGINE + text)
                with patch.object(lifecycle, "stop") as stop:
                    result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                self.assertEqual("healthy", result["state"])
                stop.assert_not_called()
                run = common.read_json(self.layout.run_record)
                observation = run["ple_io"]
                self.assertEqual({"direct_read_probe", "engine_log_interval"}, set(observation))
                self.assertEqual(expected, observation["direct_read_probe"])
                self.assertEqual(run["engine_log"], observation["engine_log_interval"]["path"])
                self.assertEqual(len(old.encode("utf-8")), observation["engine_log_interval"]["start"])

    def test_profiles_without_the_pin_keep_the_residency_policy(self):
        self.layout.profile.data["strata"]["engine_version"] = "0.1.52"
        self.prepare_start(engine_text=StageOrderTests.ENGINE + self.PLE_RAM)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        self.assertNotIn("ple_io", common.read_json(self.layout.run_record))
        stop.assert_not_called()

    TRIM_ON = ("strata generate: layer split: CUDA0 loads the dense weights of layers 0-43 only\n"
               "strata generate: layer split: CUDA1 loads the dense weights of layers 44-47 only\n")
    TRIM_IGNORED = "strata generate: --trim-stage-weights needs a layer split across GPUs (ignored)\n"

    def pin_trim_stage_weights(self):
        strata = self.layout.profile.data["strata"]
        strata.update(engine_version="0.1.54", trim_stage_weights=True)
        strata["setup_args"]["layer_split"] = "44"
        strata["expected_engine_flags"].append("--trim-stage-weights")

    def test_trim_stage_weights_start_records_each_stages_matching_dense_range_in_this_interval(self):
        self.pin_trim_stage_weights()
        old = self.TRIM_IGNORED + self.TRIM_ON.replace("0-43", "0-31")
        self.prepare_start(engine_prefix=old, engine_text=StageOrderTests.ENGINE + self.TRIM_ON)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        stop.assert_not_called()
        run = common.read_json(self.layout.run_record)
        observation = run["trim_stage_weights"]
        self.assertEqual(self.TRIM_ON.splitlines(), observation["log_lines"])
        self.assertEqual(run["engine_log"], observation["engine_log_interval"]["path"])
        self.assertEqual(len(old.encode("utf-8")), observation["engine_log_interval"]["start"])

    def test_trim_stage_weights_with_roles_and_manual_split_keeps_configured_order_and_checks_boundaries(self):
        strata = self.layout.profile.data["strata"]
        strata.update(engine_version="0.1.54", trim_stage_weights=True)
        strata["setup_args"].update(gpu_roles={"0": "main", "1": "helper"}, layer_split="24")
        strata["expected_engine_flags"].append("--trim-stage-weights")
        engine_text = StageOrderTests.ENGINE.replace("0-43", "0-23").replace("44-47", "24-47")
        dense_text = self.TRIM_ON.replace("0-43", "0-23").replace("44-47", "24-47")
        self.prepare_start(engine_text=engine_text + dense_text)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        stop.assert_not_called()
        run = common.read_json(self.layout.run_record)
        self.assertEqual([1, 0], run["gpu_stage_order"]["staged"])
        self.assertEqual([(1, 0, 23), (0, 24, 47)],
                         [(r["gpu_index"], r["first_layer"], r["last_layer"])
                          for r in run["gpu_stage_order"]["layer_boundaries"]])
        self.assertEqual(dense_text.splitlines(), run["trim_stage_weights"]["log_lines"])

    def test_trim_stage_weights_start_refuses_ignored_missing_duplicate_and_mismatched_ranges(self):
        self.pin_trim_stage_weights()
        cases = [self.TRIM_IGNORED, "", self.TRIM_ON.splitlines(keepends=True)[1],
                 self.TRIM_ON.replace("44-47", "43-47"),
                 self.TRIM_ON.replace("44-47", "44-48"),
                 self.TRIM_ON.replace("CUDA0", "CUDA2"), self.TRIM_ON * 2,
                 self.TRIM_ON.replace("0-43", "0-to-43")]
        for text in cases:
            with self.subTest(text=text):
                self.prepare_start(engine_prefix=self.TRIM_ON, engine_text=StageOrderTests.ENGINE + text)
                with patch.object(lifecycle, "stop") as stop, \
                        self.assertRaisesRegex(lifecycle.LifecycleError, "strata.trim_stage_weights:"):
                    lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
                stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_trim_stage_weights_start_refuses_engine_boundaries_that_move_the_manual_point(self):
        self.pin_trim_stage_weights()
        self.layout.profile.data["strata"]["setup_args"]["layer_split"] = "32"
        self.prepare_start(engine_text=StageOrderTests.ENGINE + self.TRIM_ON)
        with patch.object(lifecycle, "stop") as stop, \
                self.assertRaisesRegex(lifecycle.LifecycleError, "strata.trim_stage_weights:.*pinned manual split 32"):
            lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_unpinned_trim_start_does_not_claim_or_check_trim_evidence(self):
        self.prepare_start(engine_text=StageOrderTests.ENGINE + self.TRIM_IGNORED)
        with patch.object(lifecycle, "stop") as stop:
            result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        self.assertNotIn("trim_stage_weights", common.read_json(self.layout.run_record))
        stop.assert_not_called()

    def test_start_rechecks_foreign_race_and_uses_owned_stop(self):
        self.prepare_start(foreign=True)
        with patch.object(lifecycle, "stop") as stop:
            with self.assertRaisesRegex(lifecycle.LifecycleError, "ownership changed"):
                lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        stop.assert_called_once_with(self.layout, log=self.messages.append, locked=True)

    def test_start_records_complete_generation_bound_order(self):
        old = "strata generate: layer split: CUDA0 runs layers 0-1\n"
        self.prepare_start(engine_prefix=old)
        result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("healthy", result["state"])
        stage = common.read_json(self.layout.run_record)["gpu_stage_order"]
        self.assertEqual([0, 1], stage["staged"])
        self.assertTrue(stage["complete"])
        self.assertEqual(self.engine.as_dict(), stage["engine_identity"])
        run = common.read_json(self.layout.run_record)
        self.assertEqual(len(old.encode()), run["engine_log_start_offset"])
        self.assertEqual(run["engine_log"], stage["engine_log_interval"]["path"])
        self.assertEqual(len(old.encode()), stage["engine_log_interval"]["start"])
        self.assertEqual([{"cuda_index": 0, "gpu_index": 0, "first_layer": 0, "last_layer": 43, "expert_cache_gib": 17.51},
                          {"cuda_index": 1, "gpu_index": 1, "first_layer": 44, "last_layer": 47, "expert_cache_gib": 2.26}],
                         stage["layer_boundaries"])

    def capture(self):
        with patch.object(lifecycle.procs, "matches", side_effect=self.matches), \
                patch.object(lifecycle.procs, "descendants", return_value=[self.engine]):
            return lifecycle.capture_startup_gpu_order(self.layout)

    def test_capture_requires_engine_boundaries_not_server_silence_or_old_log_content(self):
        # Engine evidence in the wrong stream, or only before this launch's offset, proves nothing.
        for server_text in ("server ready\n", StageOrderTests.KEEP * 2, StageOrderTests.ENGINE):
            self.record(server_text, engine_text="engine ready\n", engine_prefix=StageOrderTests.ENGINE)
            stage = self.capture()
            self.assertFalse(stage["complete"], stage)
            self.assertIn("boundaries", stage["reason"])
        self.record(engine_text="")
        self.assertFalse(self.capture()["complete"])
        run = self.record()
        (self.layout.root / run["engine_log"]).unlink()
        self.assertFalse(self.capture()["complete"])

    def test_capture_rejects_noncontiguous_contradictory_partial_and_extra_stages(self):
        engine = StageOrderTests.ENGINE
        invalid = [engine.replace("CUDA0 runs layers 0-43", "CUDA0 runs layers 1-43"),
                   engine.replace("44-47", "43-47"), engine.replace("44-47", "45-47"),
                   engine.replace("44-47", "44-43"), engine.replace("CUDA1 runs", "CUDA2 runs"),
                   engine.replace("strata generate: layer split: CUDA0 runs layers 0-43\n", ""),
                   engine + "strata generate: layer split: CUDA0 runs layers 0-42\n", engine.rstrip(),
                   engine.replace("44-47", "44-to-47"), engine.replace("2.26 GiB", "unknown GiB"),
                   engine + "[strata] now engine started: strata --serve\n" * 2]
        for text in invalid:
            with self.subTest(engine=text):
                self.record(engine_text=text)
                stage = self.capture()
                self.assertFalse(stage["complete"], stage)
                self.assertEqual("unavailable", stage["event"])
                self.assertIsNone(stage["staged"])
                self.assertTrue(stage["reason"])

    def test_capture_keeps_identical_repeats_and_maps_cuda_stages_to_physical_cards(self):
        for server_text, staged in ((StageOrderTests.KEEP * 2, [1, 0]), (StageOrderTests.REORDER, [0, 1]),
                                    ("server ready\n", [1, 0])):
            with self.subTest(staged=staged):
                self.record(server_text, engine_text=StageOrderTests.ENGINE * 2)
                result = self.capture()
                self.assertTrue(result["complete"], result)
                self.assertEqual(staged, [row["gpu_index"] for row in result["layer_boundaries"]])
                self.assertEqual([0, 1], [row["cuda_index"] for row in result["layer_boundaries"]])
                self.assertEqual([17.51, 2.26], [row["expert_cache_gib"] for row in result["layer_boundaries"]])

    def test_0157_capture_waits_for_a_console_queued_newline_and_0156_does_not(self):
        # v0.2.11's serve/nonblocking_out.py flushes a line's text and its newline separately.
        def finish_line():
            with (self.layout.logs / "server.log").open("a") as log:
                log.write("\n")

        for version, complete in (("0.1.57", True), ("0.1.56", False)):
            with self.subTest(version=version):
                self.layout.profile.data["strata"]["engine_version"] = version
                self.record("server ready")
                late = threading.Timer(0.2, finish_line)
                late.start()
                self.addCleanup(late.cancel)
                stage = self.capture()
                late.join()
                self.assertEqual(complete, stage["complete"], stage)
                if not complete:
                    self.assertEqual("truncated startup output", stage["reason"])

    def test_settled_interval_returns_the_partial_line_after_its_deadline(self):
        run = self.record("server ready")
        text, interval = lifecycle._settled_startup_interval(self.layout, run, "log", self.layout.logs, wait_s=0.2)
        self.assertEqual("server ready", text)
        self.assertEqual(len(b"server ready"), interval["end"])

    def test_capture_requires_a_pinned_manual_split_where_the_engine_put_it(self):
        data = copy.deepcopy(self.layout.profile.data)
        for split, complete in (("44", True), ("32", False)):  # the fixture engine runs 0-43 / 44-47
            with self.subTest(split=split):
                data["strata"]["setup_args"]["layer_split"] = split
                self.layout = Layout(self.layout.root, Profile(self.layout.profile.path, data))
                self.record(engine_text=StageOrderTests.ENGINE)
                stage = self.capture()
                self.assertEqual((complete, split), (stage["complete"], stage["layer_split"]))
                if not complete:
                    self.assertIn("pinned manual split 32", stage["reason"])

    def test_manual_split_cannot_adopt_an_automatic_reorder_of_the_configured_roles(self):
        self.layout.profile.data["strata"]["setup_args"].update(
            gpu_roles={"0": "main", "1": "helper"}, layer_split="44")
        self.record(text=StageOrderTests.REORDER, engine_text=StageOrderTests.ENGINE)
        stage = self.capture()
        self.assertFalse(stage["complete"])
        self.assertIn("stage order differs from configured GPUs", stage["reason"])

    def test_start_rejects_outside_engine_log_before_launch(self):
        self.prepare_start()
        common.atomic_write_json(self.layout.strata_config, {"log": str(self.directory / "outside.log")})
        with patch.object(lifecycle, "_launch_detached") as launch:
            with self.assertRaisesRegex(lifecycle.LifecycleError, "inside the integration root"):
                lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        launch.assert_not_called()

    def test_start_records_degraded_when_engine_layer_evidence_is_absent(self):
        self.prepare_start(engine_text="engine ready\n")
        result = lifecycle.start(self.layout, tool_argv=["python"], log=self.messages.append)
        self.assertEqual("degraded", result["state"])
        self.assertFalse(result["gpu_stage_order"]["complete"])

    def test_capture_fails_if_identity_changes_or_interval_is_missing(self):
        self.record(StageOrderTests.REORDER)
        with patch.object(lifecycle.procs, "matches", side_effect=[self.engine, self.server, None]), \
                patch.object(lifecycle.procs, "descendants", return_value=[self.engine]):
            stage = lifecycle.capture_startup_gpu_order(self.layout)
        self.assertFalse(stage["complete"])
        self.assertIn("generation changed", stage["reason"])
        rec = self.record()
        rec.pop("log_start_offset")
        common.atomic_write_json(self.layout.run_record, rec)
        with patch.object(lifecycle.procs, "matches", side_effect=self.matches), \
                patch.object(lifecycle.procs, "descendants", return_value=[self.engine]):
            self.assertFalse(lifecycle.capture_startup_gpu_order(self.layout)["complete"])

    def test_status_respawn_invalidates_capture_without_mutating_record(self):
        self.record()
        with patch.object(lifecycle.procs, "matches", side_effect=self.matches), \
                patch.object(lifecycle.procs, "descendants", return_value=[self.engine]):
            self.assertTrue(lifecycle.capture_startup_gpu_order(self.layout)["complete"])
        before = self.layout.run_record.read_bytes()
        replacement = procs.ProcInfo(102, 100, "replacement-created", "strata.exe")
        with patch.object(lifecycle, "running", return_value={"server": self.server}), \
                patch.object(lifecycle.procs, "descendants", return_value=[replacement]), \
                patch.object(lifecycle, "read_key", return_value="x" * 32), \
                patch.object(lifecycle, "runtime_checks", return_value={"ready": True, "problems": []}), \
                patch.object(lifecycle, "gpu_facts", side_effect=lambda i, **kwargs: self.gpu(i, [{"pid": 102, "type": "C"}], used=20000)):
            result = lifecycle.status(self.layout)
        self.assertEqual("degraded", result["state"])
        self.assertFalse(result["gpu_stage_order"]["complete"])
        self.assertEqual(before, self.layout.run_record.read_bytes())

    def test_stopped_status_reports_foreign_occupancy_without_changing_process_state(self):
        self.record()
        with patch.object(lifecycle, "running", return_value={}), \
                patch.object(lifecycle, "gpu_facts", side_effect=lambda i, **kwargs: self.gpu(i, [{"pid": 999, "type": "C"}])):
            result = lifecycle.status(self.layout)
        self.assertEqual("stopped", result["state"])
        self.assertTrue(all(card["problems"] for card in result["cards"]))

    def test_stop_never_owns_foreign_gpu_pid_and_reports_all_card_release(self):
        self.record()
        with patch.object(lifecycle.procs, "matches", side_effect=self.matches), \
                patch.object(lifecycle.procs, "descendants", return_value=[self.engine]), \
                patch.object(lifecycle.procs, "terminate", return_value=True) as terminate, \
                patch.object(lifecycle, "port_in_use", return_value=False), \
                patch.object(lifecycle, "gpu_facts", side_effect=lambda i, **kwargs: self.gpu(i, [{"pid": 999, "type": "C"}])):
            result = lifecycle.stop(self.layout, log=self.messages.append)
        self.assertTrue(result["owned_gpus_released"])
        self.assertEqual({100, 101}, {call.args[0].pid for call in terminate.call_args_list})
        self.assertEqual([1, 0], [card["gpu_index"] for card in result["cards"]])


class ServerEnvironmentTests(LifecycleFixture):
    def test_server_env_passes_only_the_api_key_among_strata_names(self):
        key = secrets.token_urlsafe(32)
        self.layout.profile.data["strata"]["engine_env"] = dict(ENGINE_ENV_GROUPS["gdn_stack"])
        with patch.dict(os.environ, {"STRATA_GR_V3": "1", "STRATA_DEBUG": "1", "Strata_Partial_Pin": "1",
                                     "STRATA_GDN_TC": "0",
                                     "CUDA_VISIBLE_DEVICES": "0", "Cuda_Device_Order": "FASTEST_FIRST"}):
            env = lifecycle.server_env(self.layout, key)
        expected = {"STRATA_API_KEY": key}
        if self.layout.profile.pins_runtime_dir:
            expected["STRATA_RUNTIME_DIR"] = str(self.layout.strata_runtime.resolve())
        self.assertEqual(expected, {k: v for k, v in env.items() if k.upper().startswith("STRATA_")})
        self.assertNotIn("CUDA_VISIBLE_DEVICES", env)
        self.assertFalse(any(k.upper() == "CUDA_DEVICE_ORDER" for k in env))


if __name__ == "__main__":
    unittest.main()
