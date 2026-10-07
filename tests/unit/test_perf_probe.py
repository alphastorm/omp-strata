"""Host-free measurement boundary regressions using the opt-in Strata-shaped server."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from omp_strata.layout import Layout
from omp_strata.profile import Profile, load
from scripts import perf_probe as probe, requalify
from tests.candidate import PROFILE
from tests.mock.scripted_server import ResponseSpec, ScriptedServer


class PerfProbeTests(unittest.TestCase):
    def server(self, specs, **kwargs):
        server = ScriptedServer(specs, model="fixture", api_key="x" * 40, perf_enabled=True, **kwargs)
        self.addCleanup(server.close)
        return server, probe.Client(server.base_url.removesuffix("/v1"), "x" * 40, "fixture", 3)

    def layout(self, server, root, context=8192):
        profile = load(PROFILE)
        data = copy.deepcopy(profile.data)
        data["strata"]["setup_args"]["context"] = context
        data["strata"]["model_name"] = "fixture"
        data["server"]["port"] = server.httpd.server_port
        layout = Layout(Path(root), Profile(profile.path, data))
        layout.key_file.parent.mkdir(parents=True)
        layout.key_file.write_text("x" * 40, encoding="ascii")
        return layout

    def test_cap_nonce_warm_repeat_and_fifo(self):
        specs = [ResponseSpec(delay_s=.05, cached_tokens=0), ResponseSpec(delay_s=.05, cached_tokens=0),
                 ResponseSpec(delay_s=.05, cached_tokens=100), ResponseSpec(completion_delay_s=.2),
                 ResponseSpec(completion_delay_s=.05)]
        server, _ = self.server(specs, context=8192)
        with tempfile.TemporaryDirectory() as root:
            result = probe.run(self.layout(server, root), [0, 99999], 99999, 128, 3)
        rows = result["samples"]
        self.assertEqual([r["scenario"] for r in rows], ["unique_prefix", "unique_prefix", "warm_repeat"])
        self.assertEqual(probe.value(rows[1], "prompt_tokens"), 8192 - 128 - 8)
        self.assertEqual(rows[1]["capped_target"], 8192 - 128 - 8)
        self.assertEqual(probe.value(rows[2], "cached_tokens"), 100)
        chats = [r for r in server.posts if r["path"] == "/v1/chat/completions"]
        prompts = [r["body"]["messages"][0]["content"] for r in chats]
        self.assertEqual(prompts[1], prompts[2])
        prefixes = [prompts[i].split("\n")[0] for i in (0, 1, 3, 4)]
        self.assertEqual(len(set(prefixes)), 4)
        self.assertTrue(result["queue"]["both_complete"])
        self.assertEqual([r["finish"] for r in server.history[-2:]], ["stop", "stop"])
        a, b = server.history[-2:]
        self.assertGreaterEqual(b["time"], a["time"] + a["duration_s"])
        second = result["queue"]["requests"][1]
        self.assertGreater(probe.value(second, "queue_wait_lower_ms"), 100)
        self.assertGreaterEqual(probe.value(second, "queue_wait_upper_ms"), probe.value(second, "queue_wait_lower_ms"))

    def test_ttft_ignores_keepalive_and_empty_role(self):
        _, client = self.server([ResponseSpec(delay_s=.15, completion_delay_s=.03)])
        row = client.chat("fixture", 128)
        self.assertGreaterEqual(probe.value(row, "ttft_ms"), 140)
        self.assertLess(probe.value(row, "first_event_ms"), probe.value(row, "ttft_ms"))
        self.assertEqual(probe.value(row, "first_reasoning_ms"), probe.value(row, "ttft_ms"))
        self.assertIsNone(probe.value(row, "inter_token_latency_p95_ms"))
        self.assertEqual(probe.value(row, "decode_tokens_s"), 2250)

    def test_acceptance_uses_deltas_not_lifetime_ratio(self):
        server, client = self.server([ResponseSpec(drafts_offered=12, drafts_accepted=3)])
        server.totals.update(drafts_offered=1000, drafts_accepted=900)
        before = client.request("/metrics")
        client.chat("fixture", 128)
        metrics = probe.acceptance(before, client.request("/metrics"), 1)
        self.assertEqual(probe.value({"metrics": metrics}, "mtp_acceptance"), .25)

    def test_older_counts_unavailable_not_inferred_from_timings(self):
        _, client = self.server([ResponseSpec(drafts_offered=None, drafts_accepted=None)])
        before = client.request("/metrics")
        client.chat("fixture", 128)
        metrics = probe.acceptance(before, client.request("/metrics"), 1)
        self.assertTrue(all(m["method"] == "unavailable" and m["value"] is None for m in metrics))

    def test_nonexclusive_or_reset_metrics_rejected(self):
        with self.assertRaises(probe.ProtocolError):
            probe.acceptance({"totals": {"requests": 2}}, {"totals": {"requests": 4}}, 1)
        with self.assertRaises(probe.ProtocolError):
            probe.acceptance({"totals": {"requests": 2, "drafts_offered": 10, "drafts_accepted": 5}},
                             {"totals": {"requests": 3, "drafts_offered": 1, "drafts_accepted": 0}}, 1)

    def test_protocol_errors_and_timeout_have_nonzero_exit_records(self):
        for fault, expected in (("malformed", 1), ("drop", 1), ("in_band", 1), ("stall", 124)):
            with self.subTest(fault=fault):
                server, _ = self.server([ResponseSpec(fault=fault)], context=8192)
                with tempfile.TemporaryDirectory() as root:
                    layout = self.layout(server, root)
                    out, err = io.StringIO(), io.StringIO()
                    started = time.monotonic()
                    with patch.object(probe, "load", return_value=layout.profile), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        rc = probe.main(["--profile", str(PROFILE), "--root", root, "--depths", "0", "--warm-depth", "0",
                                         "--max-tokens", "128", "--timeout", "0.5"])
                    self.assertEqual(rc, expected)
                    self.assertLess(time.monotonic() - started, 2)
                    record = json.loads(out.getvalue())
                    self.assertEqual(record["status"], "error")
                    saved = json.loads((Path(root) / "evidence" / record["run_id"] / "result.json").read_text())
                    self.assertEqual(saved, record)
                    self.assertNotIn("x" * 40, out.getvalue() + err.getvalue())

    def test_remote_url_refused_before_credentials_leave(self):
        with self.assertRaises(probe.ProtocolError):
            probe.Client("http://example.com:8000", "secret", "fixture", 1)


class RequalifyPerfTests(unittest.TestCase):
    def plan(self, *extra):
        output = io.StringIO()
        with patch("sys.argv", ["requalify", "--profile", str(PROFILE), "--root", "/tmp/perf-plan", "--dry-run", *extra]), \
                contextlib.redirect_stdout(output):
            self.assertEqual(requalify.main(), 0)
        return output.getvalue().splitlines()[1:]

    def test_default_plan_preserves_steps_and_optional_perf_does_not_leak(self):
        plan = self.plan()
        self.assertEqual([line.split(":", 1)[0] for line in plan],
                         ["install", "keygen", "start", "g10", "tracer", "g12", "g13", "g14", "g14q", "g15", "g16",
                          "g17", "g18", "g18l", "g19", "g20", "pilot", "eval", "quickstart", "g21", "stop"])
        for args in (("--only", "perf"), ("--from", "perf")):
            selected = self.plan(*args)
            self.assertEqual([s.split(":", 1)[0] for s in selected], ["perf", "stop"])
            self.assertEqual(Path(json.loads(selected[0].split(": ", 1)[1])[1]).name, "perf_probe.py")
        self.assertEqual([s.split(":", 1)[0] for s in self.plan("--only", "perf", "--keep-running")], ["perf"])


if __name__ == "__main__":
    unittest.main()
