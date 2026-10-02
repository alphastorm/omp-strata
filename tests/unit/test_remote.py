"""Host-free security and process-lifetime contracts; no SSH or OMP executable."""
import base64
import copy
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from omp_strata.common import atomic_write_json
from omp_strata.ompcfg import CHAT_ROLES
from omp_strata.profile import ClientRoute, ProfileError, load, load_route
from omp_strata.remote import (Binding, OwnedProcess, RemoteError, RemoteSession, client_key_path, destination,
                               key_argv, load_bindings, preflight, pull_key, read_client_key,
                               tunnel_argv, validate_key, write_private)
from tests.candidate import PROFILE


class RemoteBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.profile = load(PROFILE)

    def route(self):
        data = dict(schema_version=1, kind="client-route", profile_id="fixture-route", status="draft",
                    members=[dict(label="main", server_profile=self.profile.id, server_fingerprint=self.profile.fingerprint, local_port=18191)],
                    roles={role: "main" for role in CHAT_ROLES}, agents={})
        return ClientRoute(self.root / "route.json", data, {"main": self.profile})

    def test_argv_is_loopback_batch_and_destination_cannot_be_an_option_or_shell(self):
        argv = tunnel_argv("operator@example.com", 18191, 18090)
        self.assertEqual(["ssh", "-NT", "-o", "ExitOnForwardFailure=yes", "-o", "ServerAliveInterval=15", "-o",
                          "ServerAliveCountMax=3", "-o", "BatchMode=yes", "-o", "ControlMaster=no", "-o", "ControlPath=none",
                          "-o", "ForkAfterAuthentication=no", "-L", "127.0.0.1:18191:127.0.0.1:18090",
                          "operator@example.com"], argv)
        self.assertEqual("runtime-alias", destination("runtime-alias"))
        for alias in ("-oProxyCommand=bad", "x y", "x\ny", "x;bad", "x$(bad)", "x@-y", "", "a@b@c"):
            with self.subTest(alias=alias), self.assertRaises(RemoteError):
                tunnel_argv(alias, 18191, 18090)
        for value in (0, 65536, True, "18090"):
            with self.assertRaises(RemoteError):
                tunnel_argv("alias", value, 18090)

    def test_key_transfer_uses_stdout_and_never_leaks_key_on_error(self):
        key = secrets.token_urlsafe(32)
        source = self.root / "source"
        source.write_text(key)
        target = self.root / "key"
        # The stand-in reads its own fixture file, verifies stdin EOF, then prints only its contents.
        program = "import sys,pathlib; assert sys.stdin.buffer.read()==b''; print(pathlib.Path(sys.argv[1]).read_text())"
        command = [sys.executable, "-c", program, str(source)]
        pull_key("fixture", "/runtime", "posix", target, ssh=command)
        self.assertEqual(key, read_client_key(target))
        self.assertNotIn(key, repr(key_argv("fixture", "/runtime", "posix", ssh=command)))
        if os.name != "nt":
            self.assertEqual(0o600, target.stat().st_mode & 0o777)
        source.write_text("short-secret")
        with self.assertRaises(RemoteError) as caught:
            pull_key("fixture", "/runtime", "posix", target, ssh=command)
        self.assertNotIn("short-secret", str(caught.exception))
        self.assertEqual(key, read_client_key(target), "failed transfers cannot replace the previous key")
        for raw in (b"", b" " * 50, b"a" * 31, b"a" * 32 + b"\nsecret", bytes([255]) * 40):
            with self.assertRaises(RemoteError):
                validate_key(raw)

    def test_remote_key_path_is_quoted_for_each_server_shell(self):
        posix = key_argv("fixture", "/a path/with'quote", "posix")
        self.assertEqual(["ssh", "-o", "BatchMode=yes"], posix[:3])
        self.assertEqual("fixture", posix[-2])
        self.assertIn("'\"'\"'", posix[-1])
        windows = key_argv("fixture", "C:\\a path\\with'quote", "windows")[-1]
        source = base64.b64decode(windows.split()[-1]).decode("utf-16le")
        self.assertIn("with''quote", source)
        for path in ("relative", "", "/a\nb"):
            with self.assertRaises(RemoteError):
                key_argv("fixture", path, "posix")

    def test_absent_and_public_key_files_fail_before_any_ssh_process(self):
        route = self.route()
        bindings = {"main": Binding("main", "fixture", "/root", "posix")}
        with patch("omp_strata.remote.OwnedProcess") as spawn:
            with self.assertRaisesRegex(RemoteError, "pull-key"):
                with RemoteSession(route, self.root, bindings):
                    self.fail("missing key was accepted")
            spawn.assert_not_called()
        key = client_key_path(self.root, "main")
        write_private(key, secrets.token_urlsafe(32).encode())
        if os.name != "nt":
            key.chmod(0o644)
            with self.assertRaisesRegex(RemoteError, "0600"):
                read_client_key(key)

    def test_preflight_rejects_unavailable_wrong_key_model_and_engine_without_echo(self):
        p = self.profile.data
        health = {"api_key": True, "loaded": True, "model": p["strata"]["model_name"], "max_context": p["strata"]["setup_args"]["context"]}
        models = {"data": [{"id": p["strata"]["model_name"]}]}
        props = {"build_info": "Strata " + p["strata"]["engine_version"], "default_generation_settings": {"n_ctx": health["max_context"]}}
        key = secrets.token_urlsafe(32)
        cases = [([(0, None)], "health"), ([(200, {**health, "model": key})], "health identity"),
                 ([(200, health), (401, None), (401, None)], "401"),
                 ([(200, health), (401, None), (200, {"data": []})], "model identity"),
                 ([(200, health), (401, None), (200, models), (200, {**props, "build_info": key})], "engine identity")]
        for responses, message in cases:
            with self.subTest(message=message), patch("omp_strata.remote.http_json", side_effect=responses):
                with self.assertRaisesRegex(RemoteError, message) as caught:
                    preflight(self.profile, 18191, key)
                self.assertNotIn(key, str(caught.exception))

    def test_partial_fleet_start_tears_down_every_opened_tunnel(self):
        route = self.route()
        route.data["members"].append({**route.data["members"][0], "label": "worker", "local_port": 18192})
        route.servers["worker"] = self.profile
        bindings = {label: Binding(label, "fixture", "/root", "posix") for label in route.servers}
        for label in route.servers:
            write_private(client_key_path(self.root, label), secrets.token_urlsafe(32).encode())
        with patch("omp_strata.remote.Tunnel") as tunnel, patch("omp_strata.remote.preflight", side_effect=[{}, RemoteError("mismatch")]):
            with self.assertRaises(RemoteError):
                with RemoteSession(route, self.root, bindings):
                    self.fail("partial fleet was accepted")
            self.assertEqual(2, tunnel.return_value.close.call_count)

    def test_route_pins_reject_drift_unknown_roles_and_private_fields(self):
        route = self.route()
        atomic_write_json(self.root / (self.profile.id + ".json"), self.profile.data)
        atomic_write_json(route.path, route.data)
        self.assertEqual(route.fingerprint, load_route(route.path, profiles_dir=self.root).fingerprint)
        for field, value in (("server_fingerprint", "a" * 64), ("local_port", 65536), ("alias", "private-alias")):
            data = copy.deepcopy(route.data)
            data["members"][0][field] = value
            atomic_write_json(route.path, data)
            with self.assertRaises(ProfileError):
                load_route(route.path, profiles_dir=self.root)
        data = copy.deepcopy(route.data)
        data["roles"]["task"] = "cloud"
        atomic_write_json(route.path, data)
        with self.assertRaises(ProfileError):
            load_route(route.path, profiles_dir=self.root)
        for name in ("task", "scout"):
            data = copy.deepcopy(route.data)
            data["agents"][name] = "main"
            atomic_write_json(route.path, data)
            with self.subTest(agent=name), self.assertRaisesRegex(ProfileError, "reserved stock"):
                load_route(route.path, profiles_dir=self.root)

    def test_private_bindings_cannot_retarget_public_route(self):
        route = self.route()
        binding = dict(route_id=route.id, route_fingerprint=route.fingerprint, roles=route.data["roles"],
                       members=[{**route.data["members"][0], "alias": "fixture", "remote_root": "/runtime", "remote_platform": "posix"}])
        path = self.root / "private.json"
        atomic_write_json(path, binding)
        self.assertEqual("fixture", load_bindings(path, route, alias="fixture")["main"].alias)
        binding["members"][0]["local_port"] += 1
        atomic_write_json(path, binding)
        with self.assertRaises(RemoteError):
            load_bindings(path, route)


@unittest.skipUnless(os.name == "posix", "POSIX session/signal regression; Windows job containment is a native-client gate")
class OwnedProcessTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "darwin", "Darwin EPERM for unsignalable zombie groups")
    def test_zombie_group_permission_error_does_not_prevent_reaping_and_pipe_cleanup(self):
        owner = OwnedProcess([sys.executable, "-c", "pass"], stdout=subprocess.PIPE)
        process, pipe = owner.process, owner.process.stdout
        process.wait(timeout=5)
        try:
            with patch("omp_strata.remote.os.killpg", side_effect=PermissionError(1, "not signalable")):
                owner.close()
            self.assertTrue(pipe.closed)
            with self.assertRaises(ProcessLookupError):
                os.kill(process.pid, 0)
        finally:
            owner.close()

    @unittest.skipUnless(sys.platform == "darwin", "Darwin EPERM classification")
    def test_permission_error_against_live_group_is_not_hidden(self):
        owner = OwnedProcess([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            with patch("omp_strata.remote.os.killpg", side_effect=PermissionError(1, "not permitted")):
                with self.assertRaises(PermissionError):
                    owner.close()
            self.assertIsNone(owner.process.poll(), "a denied signal must not be reported as a stopped process")
        finally:
            owner.close()

    def test_no_orphan_after_normal_crash_ctrl_c_or_sigterm(self):
        program = """
import signal,sys,time
from omp_strata.remote import OwnedProcess, RemoteInterrupted, interrupt_scope
try:
    with interrupt_scope(), OwnedProcess([sys.executable,'-c','import time; time.sleep(60)']) as child:
        print(child.process.pid, flush=True)
        mode=sys.argv[1]
        if mode=='crash': raise RuntimeError('synthetic OMP crash')
        if mode!='normal': time.sleep(60)
except (RemoteInterrupted, RuntimeError): pass
"""
        for mode in ("normal", "crash", "ctrl-c", "sigterm"):
            with self.subTest(mode=mode):
                parent = subprocess.Popen([sys.executable, "-c", program, mode], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                child_pid = int(parent.stdout.readline())
                if mode in ("ctrl-c", "sigterm"):
                    parent.send_signal(signal.SIGINT if mode == "ctrl-c" else signal.SIGTERM)
                parent.communicate(timeout=10)
                self.assertEqual(0, parent.returncode)
                with self.assertRaises(ProcessLookupError):
                    os.kill(child_pid, 0)

    def test_exited_parent_cannot_leave_proxycommand_descendant(self):
        # Keep the grandchild alive after its parent exits: closing the owner must kill its session group.
        program = "import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print(p.pid,flush=True)"
        with OwnedProcess([sys.executable, "-c", program], stdout=subprocess.PIPE, text=True) as owner:
            grandchild = int(owner.process.stdout.readline())
            owner.process.wait(timeout=5)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                os.kill(grandchild, 0)
            except ProcessLookupError:
                break
            # Linux may keep a reparented zombie until container init reaps it; it is no longer executing.
            stat = Path(f"/proc/{grandchild}/stat")
            if stat.exists() and ") Z " in stat.read_text():
                break
            time.sleep(0.02)
        else:
            self.fail("ProxyCommand descendant survived owner teardown")


if __name__ == "__main__":
    unittest.main()
