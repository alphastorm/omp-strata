"""G05: host-free lifecycle ownership and artifact failure boundaries."""
import hashlib
import http.server
import os
from pathlib import Path
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

from omp_strata import common, fetch, lifecycle, procs
from omp_strata.layout import Layout
from omp_strata.profile import Profile, load
from tests.candidate import PROFILE
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
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            data["server"]["port"] = sock.getsockname()[1]
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
            with self.assertRaisesRegex(common.IntegrityError, "insufficient disk"):
                fetch.fetch(self.layout, platform="linux-x64", log=self.messages.append)
        self.assertEqual(b"partial", partial.read_bytes())
        self.assertTrue(all(not item.dest.exists() for item in items))


class SingleGpuLifecycleTests(LifecycleFixture):
    def setUp(self):
        super().setUp()
        self.layout = Layout(self.layout.root, Profile(PROFILE, single_gpu_data()))

    def test_start_keeps_legacy_idle_policy_without_multi_card_ownership_gates(self):
        server = procs.ProcInfo(100, 90, "server-created", "python.exe")

        def launch(*args, **kwargs):
            run = common.read_json(self.layout.run_record)
            run.update(state="starting", server=server.as_dict())
            common.atomic_write_json(self.layout.run_record, run)

        mismatched_but_idle = gpu_fact(self.layout.profile, self.layout.profile.gpu_indices[0])
        mismatched_but_idle.update(name="other model", memory_total_mib=1, driver="1.00")
        for gpu in ({"available": False}, mismatched_but_idle):
            with self.subTest(gpu=gpu), \
                    patch.object(lifecycle, "verify_install_fast", return_value={"runtime_identity_sha256": "a" * 64}), \
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

    def test_scalar_doctor_retains_legacy_unavailable_check(self):
        with patch.object(lifecycle, "gpu_facts", return_value={"available": False, "reason": "new detail"}) as facts, \
                patch.object(lifecycle, "port_in_use", return_value=False):
            checks = lifecycle.doctor(self.layout)["checks"]
        facts.assert_called_once_with(self.layout.profile.gpu_indices[0])
        self.assertIn({"check": "gpu", "ok": False, "detail": "nvidia-smi unavailable", "blocking": True}, checks)


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

    def prepare_start(self, foreign=False, engine_prefix="", engine_text=StageOrderTests.ENGINE):
        engine_log = self.layout.strata / "engine.log"
        engine_log.parent.mkdir(parents=True, exist_ok=True)
        engine_log.write_text(engine_prefix)
        common.atomic_write_json(self.layout.strata_config, {"log": str(engine_log)})
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
                output.write(StageOrderTests.REORDER)
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
    def test_inherited_strata_tuning_knobs_never_reach_the_server(self):
        key = secrets.token_urlsafe(32)
        with patch.dict(os.environ, {"STRATA_GR_V3": "1", "STRATA_DEBUG": "1", "Strata_Partial_Pin": "1",
                                     "CUDA_VISIBLE_DEVICES": "0", "Cuda_Device_Order": "FASTEST_FIRST"}):
            env = lifecycle.server_env(self.layout, key)
        self.assertEqual({"STRATA_API_KEY": key}, {k: v for k, v in env.items() if k.upper().startswith("STRATA_")})
        self.assertNotIn("CUDA_VISIBLE_DEVICES", env)
        self.assertFalse(any(k.upper() == "CUDA_DEVICE_ORDER" for k in env))


if __name__ == "__main__":
    unittest.main()
