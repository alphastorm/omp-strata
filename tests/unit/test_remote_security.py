"""Fail-closed credential, ownership, signal, and route-root boundaries."""
import dataclasses
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from omp_strata import cli, remote
from omp_strata.common import atomic_write_json
from omp_strata.layout import Layout
from omp_strata.ompcfg import CHAT_ROLES
from omp_strata.profile import ClientRoute, load
from tests.candidate import PROFILE


class RemoteSecurityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.profile = load(PROFILE)
        self.binding = remote.Binding("main", "fixture", "/fixture-root", "posix")
        self.route = ClientRoute(self.root / "route.json", {
            "schema_version": 1, "kind": "client-route", "profile_id": "fixture-route", "status": "draft",
            "members": [{"label": "main", "server_profile": self.profile.id,
                         "server_fingerprint": self.profile.fingerprint, "local_port": 18191}],
            "roles": {role: "main" for role in CHAT_ROLES}, "agents": {},
        }, {"main": self.profile})

    def test_changed_binding_or_incomplete_key_pair_refused_before_network(self):
        key = secrets.token_urlsafe(32)
        path = remote.client_key_path(self.root, "main")
        remote.write_client_key(path, key, self.binding)
        self.assertEqual(key, remote.read_client_key(path, self.binding))
        provenance = remote.key_provenance_path(path)
        if os.name != "nt":
            self.assertEqual(0o600, provenance.stat().st_mode & 0o777)
        variants = [dataclasses.replace(self.binding, **{field: value}) for field, value in (
            ("alias", "different-fixture"), ("remote_root", "/other-root"), ("remote_platform", "windows"))]
        for binding in variants:
            with self.subTest(binding=binding), patch("omp_strata.remote.OwnedProcess") as spawn:
                with self.assertRaisesRegex(remote.RemoteError, "binding changed since pull-key; run pull-key again"):
                    with remote.RemoteSession(self.route, self.root, {"main": binding}):
                        self.fail("retargeted key was accepted")
                spawn.assert_not_called()
        # Simulate an interrupted key+provenance replacement, then a missing provenance file.
        remote.write_private(path, secrets.token_urlsafe(32).encode())
        with self.assertRaises(remote.RemoteError):
            remote.read_client_key(path, self.binding)
        provenance.unlink()
        with self.assertRaises(remote.RemoteError):
            remote.read_client_key(path, self.binding)

    def test_unknown_listener_or_dead_ssh_never_reaches_http_transport(self):
        tunnel = remote.Tunnel(self.binding, 18191, 18190)
        process = Mock(pid=202)
        process.poll.return_value = None
        tunnel.child = SimpleNamespace(process=process)
        for owners in (set(), {201}, {201, 202}):
            with self.subTest(owners=owners), patch("omp_strata.remote.listener_pids", return_value=owners), \
                    patch("urllib.request.build_opener") as transport:
                with self.assertRaises(remote.RemoteError):
                    remote.http_json("http://127.0.0.1:18191/props", key=secrets.token_urlsafe(32), owner=tunnel)
                transport.assert_not_called()
        with patch("omp_strata.remote.listener_pids", side_effect=remote.RemoteError("query unavailable")), \
                patch("urllib.request.build_opener") as transport:
            with self.assertRaises(remote.RemoteError):
                remote.http_json("http://127.0.0.1:18191/props", key=secrets.token_urlsafe(32), owner=tunnel)
            transport.assert_not_called()
        process.poll.return_value = 0
        with patch("omp_strata.remote.listener_pids") as query, patch("urllib.request.build_opener") as transport:
            with self.assertRaises(remote.RemoteError):
                remote.preflight(self.profile, 18191, secrets.token_urlsafe(32), owner=tunnel)
            query.assert_not_called()
            transport.assert_not_called()

    def test_listener_queries_reject_incomplete_platform_output(self):
        for platform, name, valid in (("darwin", "posix", "p202\nf3\np203\nf4\n"), ("win32", "nt", "202\n203\n")):
            with self.subTest(platform=platform), patch.object(remote.sys, "platform", platform), patch.object(remote.os, "name", name):
                with patch("omp_strata.remote.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=valid)):
                    self.assertEqual({202, 203}, remote.listener_pids(18191))
                for code, output in ((1, valid), (0, ""), (0, "not a PID\n"), (0, "p202\n")):
                    with patch("omp_strata.remote.subprocess.run", return_value=SimpleNamespace(returncode=code, stdout=output)):
                        with self.assertRaises(remote.RemoteError):
                            remote.listener_pids(18191)

    @unittest.skipUnless(os.name == "posix", "fixture uses POSIX socket symlinks")
    def test_linux_socket_inodes_require_every_listener_to_be_attributed(self):
        proc = self.root / "proc"
        (proc / "net").mkdir(parents=True)
        row = f"0: 0100007F:470F 00000000:0000 0A 00000000:00000000 00:00000000 00000000 {os.getuid()} 0 9123"
        (proc / "net/tcp").write_text("header\n" + row + "\n")
        for pid in (202, 203):
            (proc / str(pid) / "fd").mkdir(parents=True)
            (proc / str(pid) / "fd/3").symlink_to("socket:[9123]")
        self.assertEqual({202, 203}, remote._linux_listener_pids(18191, proc))
        for pid in (202, 203):
            (proc / str(pid) / "fd/3").unlink()
        with self.assertRaises(ValueError):
            remote._linux_listener_pids(18191, proc)

    def test_route_fetch_refuses_server_or_different_route_before_download(self):
        atomic_write_json(self.route.path, self.route.data)
        for kind in ("server", "other-route"):
            with self.subTest(kind=kind):
                root = self.root / kind
                layout = Layout(root, self.profile)
                marker = layout.install_record if kind == "server" else layout.state / "client-route.json"
                atomic_write_json(marker, {"profile_id": "not-this-route", "fingerprint": "a" * 64})
                payload = root / "existing-artifact"
                payload.write_bytes(b"original payload")
                def download(*_args, **_kwargs):
                    payload.write_bytes(b"overwritten")
                    return []
                args = SimpleNamespace(profile=str(self.route.path), root=str(root), only=None, platform=None)
                with patch("omp_strata.cli.load_route", return_value=self.route), \
                        patch("omp_strata.cli.fetch_mod.fetch", side_effect=download) as fetch:
                    with self.assertRaises(remote.RemoteError):
                        cli.cmd_fetch(args)
                    fetch.assert_not_called()
                self.assertEqual(b"original payload", payload.read_bytes())
                self.assertFalse((layout.state / "client.lock").exists())


@unittest.skipUnless(os.name == "posix", "native Windows job behavior remains a client gate")
class RemoteSignalTests(unittest.TestCase):
    def test_signal_before_popen_returns_cannot_lose_child_handle(self):
        original = subprocess.Popen
        for signum in (signal.SIGINT, signal.SIGTERM):
            children = []
            def spawn(*args, **kwargs):
                child = original(*args, **kwargs)
                children.append(child)
                os.kill(os.getpid(), signum)
                return child
            try:
                with self.subTest(signal=signum), remote.interrupt_scope(), \
                        patch("omp_strata.remote.subprocess.Popen", side_effect=spawn):
                    with self.assertRaises(remote.RemoteInterrupted):
                        remote.OwnedProcess([sys.executable, "-c", "import time; time.sleep(60)"])
                self.assertEqual(1, len(children))
                self.assertIsNotNone(children[0].poll(), "signal must not orphan the newly spawned process")
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=5)

    def test_signal_during_term_wait_cannot_skip_sigkill(self):
        code = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('ready',flush=True); time.sleep(60)"
        owner = remote.OwnedProcess([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        process = owner.process
        self.assertEqual("ready\n", process.stdout.readline())
        wait = process.wait
        injected = []
        def interrupted_wait(*args, **kwargs):
            if not injected:
                injected.append(True)
                os.kill(os.getpid(), signal.SIGTERM)
                raise subprocess.TimeoutExpired(process.args, 2)
            return wait(*args, **kwargs)
        try:
            with remote.interrupt_scope(), patch.object(process, "wait", side_effect=interrupted_wait):
                with self.assertRaises(remote.RemoteInterrupted):
                    owner.close()
            self.assertEqual(-signal.SIGKILL, process.returncode)
            self.assertIsNone(owner.process)
            self.assertTrue(process.stdout.closed)
        finally:
            owner.kill_now()
            owner.close()

    def test_one_failed_close_does_not_skip_other_groups_or_forget_owner(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        profile = load(PROFILE)
        route = ClientRoute(Path(temporary.name) / "route.json", {"roles": {"default": "main"}}, {"main": profile})
        session = remote.RemoteSession(route, Path(temporary.name), {})
        owners = [remote.OwnedProcess([sys.executable, "-c", "import time; time.sleep(60)"]) for _ in range(3)]
        processes = [owner.process for owner in owners]
        tunnels = [remote.Tunnel(remote.Binding(str(i), "fixture", "/fixture", "posix"), 18191 + i, 18090) for i in range(3)]
        for tunnel, owner in zip(tunnels, owners):
            tunnel.child = owner
        session.tunnels = list(reversed(tunnels))
        attempted = []
        closers = [owner.close for owner in owners]
        def close(index):
            attempted.append(index)
            if index == 0:
                raise OSError("injected close failure")
            closers[index]()
        try:
            with patch.object(owners[0], "close", side_effect=lambda: close(0)), \
                    patch.object(owners[1], "close", side_effect=lambda: close(1)), \
                    patch.object(owners[2], "close", side_effect=lambda: close(2)):
                with self.assertRaises(remote.RemoteCleanupError) as caught:
                    session.__exit__()
            self.assertEqual([0, 1, 2], attempted)
            self.assertEqual(1, len(caught.exception.failures))
            self.assertIs(tunnels[0].child, owners[0])
            self.assertIsNone(processes[0].poll())
            self.assertTrue(all(process.poll() is not None for process in processes[1:]))
            self.assertTrue(all(tunnel.child is None for tunnel in tunnels[1:]))
        finally:
            session.__exit__()


if __name__ == "__main__":
    unittest.main()
