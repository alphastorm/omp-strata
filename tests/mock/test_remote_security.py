"""Real OMP must never give a replacement loopback listener its bearer."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from omp_strata import remote
from omp_strata.common import atomic_write_json, read_json
import tests.mock.test_remote_client as fixtures
from tests.mock.scripted_server import ResponseSpec
from scripts.remote_gates import streamed_ttft
from tests.mock.test_remote_support import free_port


class Squatter:
    def __init__(self, port, profile):
        self.authorizations = 0
        self.requests = 0
        owner = self
        p = profile.data

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self):
                owner.requests += 1
                owner.authorizations += int(self.headers.get("Authorization") is not None)
                status = 200
                if self.path == "/health":
                    body = {"api_key": True, "loaded": True, "model": p["strata"]["model_name"],
                            "max_context": p["strata"]["setup_args"]["context"]}
                elif self.headers.get("Authorization") is None:
                    status, body = 401, {}
                elif self.path == "/v1/models":
                    body = {"data": [{"id": p["strata"]["model_name"]}]}
                elif self.path == "/props":
                    body = {"build_info": "Strata " + p["strata"]["engine_version"],
                            "default_generation_settings": {"n_ctx": p["strata"]["setup_args"]["context"]}}
                elif self.path == "/settings":
                    body = {"shared": False, "defaults": {}}
                else:
                    status, body = 503, {}
                encoded = json.dumps(body).encode()
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(encoded)
                except OSError:
                    pass
                self.close_connection = True

            do_GET = reply
            do_POST = reply

        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler, bind_and_activate=False)
        self.thread = None

    def bind(self):
        self.httpd.server_bind()
        self.httpd.server_activate()
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        if self.thread is not None:
            self.httpd.shutdown()
            self.thread.join(timeout=5)
        self.httpd.server_close()


@unittest.skipUnless(os.name == "posix", "native Windows squatter/containment proof remains a client gate")
class RemoteSquatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RemoteClientTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.RemoteClientTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_squatter_after_probe_cannot_receive_preflight_bearer(self):
        f = self.fixture
        backend = f.server([])
        route, bindings = f.route({"main": backend})
        atomic_write_json(f.fixture, {**read_json(f.fixture), "bind_delay_s": 5})
        squatter = Squatter(route.data["members"][0]["local_port"], f.profile)
        self.addCleanup(squatter.close)
        original = remote.OwnedProcess
        children = []
        def spawn(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child.process)
            # Tunnel.open has released its probe, while the stand-in is still before bind.
            squatter.bind()
            return child
        with patch("omp_strata.remote.OwnedProcess", side_effect=spawn):
            with self.assertRaisesRegex(remote.RemoteError, "owned exclusively"):
                f.run_client(route, bindings)
        status, _ = remote.http_json(f"http://127.0.0.1:{squatter.httpd.server_port}/health")
        self.assertEqual(200, status, "the squatter really owns and serves the released port")
        self.assertGreater(squatter.requests, 0)
        self.assertEqual(0, squatter.authorizations)
        self.assertTrue(children)
        self.assertTrue(all(child.poll() is not None for child in children))

    def test_stale_listener_sample_never_sends_bearer_on_a_new_connection(self):
        f = self.fixture
        squatter = Squatter(free_port(), f.profile)
        squatter.bind()
        self.addCleanup(squatter.close)
        owner = remote.Tunnel(remote.Binding("main", "fixture", "/fixture", "posix"), squatter.httpd.server_port, 18090)
        with remote.OwnedProcess([sys.executable, "-c", "import time; time.sleep(60)"], stdout=subprocess.DEVNULL) as child:
            owner.child = child
            calls = {
                "http_json": lambda: remote.http_json(f"http://127.0.0.1:{owner.local_port}/props", key=f.key, owner=owner),
                "preflight": lambda: remote.preflight(f.profile, owner.local_port, f.key, owner=owner),
                "streamed_ttft": lambda: streamed_ttft(f.profile, owner.local_port, f.key, owner=owner, timeout=5),
            }
            for name, call in calls.items():
                with self.subTest(request=name), patch("omp_strata.remote.listener_pids", return_value={child.process.pid}):
                    squatter.authorizations = 0
                    try:
                        call()
                    except remote.RemoteError:
                        pass
                    self.assertEqual(0, squatter.authorizations, "a stale listener sample cannot authorize this TCP peer")

    @unittest.skipUnless(sys.platform == "darwin", "native macOS wildcard coexistence regression")
    def test_port_wide_ownership_refuses_ipv4_and_dual_stack_wildcards(self):
        f = self.fixture
        backend = f.server([])
        route, bindings = f.route({"main": backend})
        with remote.RemoteSession(route, f.root, bindings, ssh=f.ssh) as session:
            tunnel = session.tunnels[0]
            for family, address in ((socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::")):
                with self.subTest(family=family), socket.socket(family) as wildcard:
                    wildcard.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    if family == socket.AF_INET6:
                        wildcard.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    wildcard.bind((address, tunnel.local_port))
                    wildcard.listen()
                    with self.assertRaises(remote.RemoteError):
                        tunnel.verify_listener()

    def test_ssh_death_stops_omp_before_rebound_listener_gets_bearer(self):
        f = self.fixture
        backend = f.server([ResponseSpec(text="PARTIAL", completion_delay_s=8)])
        route, bindings = f.route({"main": backend})
        squatter = Squatter(route.data["members"][0]["local_port"], f.profile)
        self.addCleanup(squatter.close)
        rebound, stop_binding = threading.Event(), threading.Event()
        result = {}
        with remote.RemoteSession(route, f.root, bindings, ssh=f.ssh) as session, tempfile.TemporaryFile() as output:
            def run_omp():
                try:
                    result["code"] = session.run(["-p", "--mode", "json", "--no-tools", "Hold this turn."],
                                                 binary=f.binary, cwd=f.root, stdout=output, stderr=output, timeout=20)
                except remote.RemoteError:
                    result["stopped"] = True
            running = threading.Thread(target=run_omp)
            running.start()
            deadline = time.monotonic() + 10
            while not backend.posts and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(1, len(backend.posts), "OMP must have sent a real authenticated model request")
            process = session.omp_child.process

            def rebind():
                deadline = time.monotonic() + 5
                while not stop_binding.is_set() and time.monotonic() < deadline:
                    try:
                        squatter.bind()
                        rebound.set()
                        return
                    except OSError:
                        time.sleep(0.001)
            binding = threading.Thread(target=rebind)
            binding.start()
            try:
                os.kill(session.tunnels[0].child.process.pid, signal.SIGKILL)
                self.assertTrue(rebound.wait(5), "squatter must take the port immediately after SSH releases it")
                running.join(timeout=5)
                self.assertFalse(running.is_alive())
                self.assertIsNotNone(process.poll(), "OMP must not remain available for a retry")
                self.assertTrue(result.get("stopped"))
                status, _ = remote.http_json(f"http://127.0.0.1:{squatter.httpd.server_port}/health")
                self.assertEqual(200, status)
                self.assertEqual(0, squatter.authorizations)
            finally:
                stop_binding.set()
                binding.join(timeout=5)
        f.assert_tunnels_gone()


if __name__ == "__main__":
    unittest.main()
