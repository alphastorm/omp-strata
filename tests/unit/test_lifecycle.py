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
from omp_strata.profile import load

REPO = Path(__file__).resolve().parents[2]
PROFILE = REPO / "profiles/win11-rtx5090-coder-iq1m-131k.json"


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
                self.assertEqual({"state": "stopped", "stopped": []},
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
        self.assertEqual("stopped", common.read_json(self.layout.run_record)["state"])
        self.assertEqual({"state": "stopped", "stopped": []},
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
        self.assertEqual({"state": "stopped"}, lifecycle.status(self.layout))
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


if __name__ == "__main__":
    unittest.main()
