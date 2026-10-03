"""Real pinned stock OMP over disposable SSH-shaped TCP forwards (no host claims)."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from omp_strata.common import atomic_write_json
from omp_strata.ompcfg import CHAT_ROLES
from omp_strata.profile import ClientRoute, Profile, load
from omp_strata.remote import Binding, RemoteError, RemoteSession, client_key_path, write_client_key, write_private
from omp_strata.transcript import find_sessions, summarize
from tests.candidate import PROFILE
from tests.mock.scripted_server import ResponseSpec, ScriptedServer
from tests.mock.test_remote_support import free_port


class RemoteClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        binary = os.environ.get("OMP_STRATA_OMP_BINARY")
        if not binary or not Path(binary).is_file():
            raise unittest.SkipTest("set OMP_STRATA_OMP_BINARY to the pinned stock OMP binary")
        cls.binary = Path(binary).resolve()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="strata-route-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = secrets.token_urlsafe(32)
        self.profile = load(PROFILE)
        self.pids = self.root / "ssh-pids"
        self.fixture = self.root / "ssh-fixture.json"
        keyfile = self.root / "host-key"
        write_private(keyfile, self.key.encode())
        atomic_write_json(self.fixture, {"pids": str(self.pids), "key_file": str(keyfile)})
        self.ssh = [sys.executable, str(Path(__file__).with_name("test_remote_support.py")), str(self.fixture)]

    def server(self, scenario=(), *, response_factory=None):
        server = ScriptedServer(scenario, model=self.profile.data["strata"]["model_name"], api_key=self.key,
                                engine_version=self.profile.data["strata"]["engine_version"],
                                context=self.profile.data["strata"]["setup_args"]["context"], perf_enabled=True,
                                response_factory=response_factory)
        self.addCleanup(server.close)
        return server

    def route(self, servers, *, agents=None):
        profiles, members, bindings = {}, [], {}
        for label, server in servers.items():
            data = copy.deepcopy(self.profile.data)
            data["server"]["port"] = server.httpd.server_port
            profile = Profile(self.profile.path, data)
            profiles[label] = profile
            members.append(dict(label=label, server_profile=profile.id, server_fingerprint=profile.fingerprint, local_port=free_port()))
            bindings[label] = Binding(label, "fixture-" + label, "/fixture-root", "posix")
            write_client_key(client_key_path(self.root, label), self.key, bindings[label])
        main = next(iter(servers))
        roles = {role: main for role in CHAT_ROLES}
        if len(servers) > 1:
            roles["task"] = list(servers)[1]
        data = dict(schema_version=1, kind="client-route", profile_id="fixture-route", status="draft",
                    members=members, roles=roles, agents=agents or {})
        return ClientRoute(self.root / "route.json", data, profiles), bindings

    def run_client(self, route, bindings, *, extra=(), prompt="Reply with REMOTE_OK.", tools="read,write,bash"):
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            with RemoteSession(route, self.root, bindings, ssh=self.ssh) as session:
                code = session.run(["-p", "--mode", "json", "--max-time", "30s", "--auto-approve", "--tools", tools, *extra, prompt],
                                   binary=self.binary, cwd=self.root, stdout=out, stderr=err)
            out.seek(0)
            err.seek(0)
            return code, out.read().decode(), err.read().decode()

    def assert_tunnels_gone(self):
        for pid in map(int, self.pids.read_text().splitlines()):
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_remote_turn_and_client_restart_resume_same_transcript(self):
        server = self.server([ResponseSpec(text="REMOTE_OK"), ResponseSpec(text="RESUMED_OK")])
        route, bindings = self.route({"main": server})
        code, out, err = self.run_client(route, bindings)
        self.assertEqual(0, code, err)
        self.assertIn("REMOTE_OK", out)
        first = find_sessions(self.root / "omp" / "home")
        self.assertEqual(1, len(first))
        code, out, err = self.run_client(route, bindings, extra=["--continue"], prompt="Continue the same transcript.")
        self.assertEqual(0, code, err)
        self.assertEqual(first, find_sessions(self.root / "omp" / "home"))
        self.assertIn("REMOTE_OK", json.dumps(server.posts[-1]["body"]["messages"]))
        self.assertEqual({"strata-main"}, set(summarize(first[0])["providers"]))
        self.assert_tunnels_gone()

    def test_wrong_key_and_wrong_identity_fail_before_omp(self):
        server = self.server([])
        route, bindings = self.route({"main": server})
        write_client_key(client_key_path(self.root, "main"), secrets.token_urlsafe(32), bindings["main"])
        with self.assertRaisesRegex(RemoteError, "401"):
            self.run_client(route, bindings)
        self.assertEqual([], server.posts)
        self.assertEqual([], find_sessions(self.root / "omp" / "home"))
        write_client_key(client_key_path(self.root, "main"), self.key, bindings["main"])
        route.servers["main"].data["strata"]["engine_version"] = "0.0.0"
        with self.assertRaisesRegex(RemoteError, "engine identity"):
            self.run_client(route, bindings)
        self.assertEqual([], server.posts)
        self.assert_tunnels_gone()

    def test_dropped_tunnel_turn_fails_and_explicit_reopen_replays_transcript(self):
        server = self.server([ResponseSpec(text="BEFORE_DROP"), ResponseSpec(text="INCOMPLETE", completion_delay_s=8),
                              ResponseSpec(text="REOPENED_OK")])
        route, bindings = self.route({"main": server})
        code, _, err = self.run_client(route, bindings, prompt="Remember BEFORE_DROP.")
        self.assertEqual(0, code, err)
        sessions = find_sessions(self.root / "omp" / "home")
        prior = sessions[0].read_bytes()
        result = {}
        with RemoteSession(route, self.root, bindings, ssh=self.ssh) as session, tempfile.TemporaryFile() as out:
            def launch():
                try:
                    result["code"] = session.run(["-p", "--continue", "--mode", "json", "--max-time", "20s", "--no-tools", "Start the interrupted turn."],
                                                 binary=self.binary, cwd=self.root, stdout=out, stderr=out)
                except RemoteError:
                    result["error"] = True
            thread = threading.Thread(target=launch)
            thread.start()
            deadline = time.monotonic() + 12
            while len(server.posts) < 2 and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(2, len(server.posts))
            session.tunnels[0].close()
            thread.join(12)
            self.assertFalse(thread.is_alive())
        self.assertTrue(result.get("error") or result.get("code", 0) != 0)
        sessions = find_sessions(self.root / "omp" / "home")
        self.assertEqual(1, len(sessions))
        self.assertTrue(sessions[0].read_bytes().startswith(prior), "all data saved before the lost turn must survive")
        # The fixture's prior request completes its artificial hold before another FIFO request.
        server.closed.wait(0.05)
        code, out, err = self.run_client(route, bindings, extra=["--continue"])
        self.assertEqual(0, code, err)
        self.assertIn("REOPENED_OK", out)
        self.assertEqual(3, len(server.posts))
        self.assertEqual(sessions, find_sessions(self.root / "omp" / "home"))
        self.assert_tunnels_gone()


    @unittest.skipUnless(os.name == "posix", "native Windows job teardown requires its client gate")
    def test_omp_error_and_launcher_signals_close_every_tunnel(self):
        server = self.server([ResponseSpec(status=400)])
        route, bindings = self.route({"main": server})
        code, _, _ = self.run_client(route, bindings)
        self.assertNotEqual(0, code)
        self.assert_tunnels_gone()
        for signum in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=signum):
                stalled = self.server([ResponseSpec(fault="stall")])
                route, bindings = self.route({"main": stalled})
                document = self.root / "signal-fixture.json"
                atomic_write_json(document, {"route": route.data, "server": route.main.data, "ssh": self.ssh})
                program = """
import json,sys
from pathlib import Path
from omp_strata.profile import ClientRoute,Profile
from omp_strata.remote import Binding,RemoteInterrupted,RemoteSession,interrupt_scope
d=json.loads(Path(sys.argv[1]).read_text()); root=Path(sys.argv[2]); binary=Path(sys.argv[3])
p=Profile(Path(sys.argv[1]),d['server']); r=ClientRoute(Path(sys.argv[1]),d['route'],{'main':p})
try:
    with interrupt_scope(),RemoteSession(r,root,{'main':Binding('main','fixture-main','/fixture-root','posix')},ssh=d['ssh']) as session:
        raise SystemExit(session.run(['-p','--mode','json','--no-tools','Hold this turn.'],binary=binary,cwd=root,timeout=30))
except RemoteInterrupted as e: raise SystemExit(128+e.signum)
"""
                parent = subprocess.Popen([sys.executable, "-c", program, str(document), str(self.root), str(self.binary)],
                                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    deadline = time.monotonic() + 10
                    while not stalled.posts and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertEqual(1, len(stalled.posts))
                    parent.send_signal(signum)
                    parent.communicate(timeout=10)
                    self.assertEqual(128 + signum, parent.returncode)
                    self.assert_tunnels_gone()
                finally:
                    if parent.poll() is None:
                        parent.kill()
                    parent.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
