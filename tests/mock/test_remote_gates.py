"""G23 probe mechanics over fake SSH + stock OMP + a restarted HTTP fixture."""
import re
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from omp_strata.remote import RemoteSession
from scripts.remote_gates import probe_member
import tests.mock.test_remote_client as fixtures
from tests.mock.scripted_server import ResponseSpec


class RemoteGateProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RemoteClientTests.setUpClass()

    def test_auth_drop_reopen_and_new_server_replay_are_exercised(self):
        f = fixtures.RemoteClientTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        schedules = []
        errors = []
        stop = threading.Event()

        def server():
            specs = [ResponseSpec(text="", delay_s=0.12) for _ in range(15)]
            instance = f.server(specs)
            schedules.append((instance, specs))
            return instance

        initial = server()
        route, bindings = f.route({"main": initial})
        original_port = initial.httpd.server_port
        restart_count = []

        def restart():
            initial.close()
            def same_port(address, handler):
                return ThreadingHTTPServer(("127.0.0.1", original_port), handler)
            with patch("tests.mock.scripted_server.ThreadingHTTPServer", side_effect=same_port):
                replacement = server()
            restart_count.append(replacement)

        def respond():
            seen = {}
            while not stop.wait(0.005):
                for instance, specs in list(schedules):
                    index = seen.get(id(instance), 0)
                    posts = instance.posts
                    while index < len(posts):
                        body, spec = posts[index]["body"], specs[index]
                        index += 1
                        text = "\n".join(m["content"] if isinstance(m.get("content"), str)
                                         else "\n".join(b.get("text", "") for b in m.get("content", []) if isinstance(b, dict))
                                         for m in body["messages"])
                        last = body["messages"][-1]["content"]
                        if not isinstance(last, str):
                            last = str(last)
                        if body.get("max_tokens") == 128:
                            spec.text = "READY"
                        elif "2000 distinct integers" in last:
                            spec.text = "1\n2\n3\n"
                            spec.completion_delay_s = 1
                        else:
                            nonces = re.findall(r"RECALL_[0-9a-f]{24}", text)
                            if not nonces:
                                errors.append("nonce missing from replayed request")
                                spec.text = "MISSING_NONCE"
                            else:
                                spec.text = nonces[0]
                    seen[id(instance)] = index
        thread = threading.Thread(target=respond, daemon=True)
        thread.start()
        try:
            with RemoteSession(route, f.root, bindings, ssh=f.ssh) as session:
                result = probe_member(session, binary=f.binary, work=f.root / "work", restart=restart, timeout=30)
        finally:
            stop.set()
            thread.join(2)
        self.assertEqual([], errors)
        self.assertEqual(1, len(restart_count))
        self.assertTrue(result["transcript_preserved"])
        self.assertTrue(result["server_restart_recall"])
        self.assertEqual(401, result["wrong_key_http_status"])
        self.assertTrue(result["tunnel_drop_failed_turn"])
        self.assertGreater(result["ttft_seconds"], 0)
        self.assertTrue(any("RECALL_" in str(r["body"]) for r in restart_count[0].posts), "new server must receive the prior transcript")
        f.assert_tunnels_gone()


if __name__ == "__main__":
    unittest.main()
