"""Real pinned stock OMP on both comparison protocols; no real-host G25 claim.

On macOS the client runs inside a kernel-enforced loopback-only socket sandbox.
This is not a production egress sandbox or a claim about other operating systems.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from omp_strata.comparison_ompcfg import NInferArm, StrataArm
from omp_strata.profile import load as load_profile
from omp_strata.transcript import find_sessions, load, summarize, tool_cycles
from tests.mock.responses_server import ResponsesServer
from tests.mock.scripted_server import ResponseSpec, ScriptedServer, ToolCall
from tests.unit.test_comparison_ompcfg import comparison_fixture, native_identity


class StockComparisonProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_OMP_BINARY")
        if not value or not Path(value).is_file():
            raise unittest.SkipTest("set OMP_STRATA_OMP_BINARY to the pinned stock OMP binary")
        cls.binary = Path(value).resolve()
        cls.sandbox = shutil.which("sandbox-exec") if sys.platform == "darwin" else None
        if cls.sandbox is None:
            raise unittest.SkipTest("G25 host-free non-loopback denial proof currently requires macOS sandbox-exec")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="g25-stock-omp-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.processes = []
        self.addCleanup(self.stop_processes)
        self.serial = 0
        self.policy = self.root / "loopback.sb"
        self.policy.write_text('(version 1)\n(allow default)\n(deny network*)\n'
                               '(allow network-outbound (remote ip "localhost:*"))\n'
                               '(allow network-inbound (local ip "localhost:*"))\n', encoding="utf-8")

    def stop_processes(self):
        for process in self.processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)

    def fixture(self, arm, specs, *, lane="rtx4090-native", port=None):
        self.serial += 1
        root = self.root / str(self.serial)
        root.mkdir()
        plan, bindings, keys = comparison_fixture(root, binary=self.binary, lane=lane)
        profile = load_profile(Path(bindings["strata"]["profile"]))
        server = None
        if port is None:
            if arm == "strata":
                server = ScriptedServer(specs, model=plan[arm]["model_id"], api_key=keys[arm],
                                        engine_version=profile.data["strata"]["engine_version"],
                                        context=profile.data["strata"]["setup_args"]["context"])
            else:
                server = ResponsesServer(specs, model=plan[arm]["model_id"], api_key=keys[arm], identity=native_identity(plan))
            self.addCleanup(server.close)
            port = server.httpd.server_port
        bindings[arm]["port"] = port
        if arm == "ninfer" and lane == "rtx5090-docker-local":
            probe_path = Path(bindings[arm]["docker_identity_probe_argv"][-1])
            probe = json.loads(probe_path.read_text())
            probe["publications"][0]["host_port"] = port
            probe_path.write_text(json.dumps(probe), encoding="utf-8")
        adapter = {"strata": StrataArm, "ninfer": NInferArm}[arm](plan, bindings)
        if server is not None:
            adapter.preflight()
        launch = adapter.prepare(Path(bindings["comparison_root"]) / "attempt")
        work = root / "workspace"
        work.mkdir()
        subprocess.run(["git", "init", "--quiet", str(work)], env=launch.env, check=True,
                       capture_output=True, timeout=10)
        return launch, work, server, plan, keys[arm]

    def run_omp(self, launch, work, *, continuation=False, max_time="20s"):
        # The sandbox denies actual non-loopback connects, including any attempted
        # catalog refresh, regardless of proxy/env compliance by stock OMP or tools.
        argv = [self.sandbox, "-f", str(self.policy), *launch.argv, "-p", "--mode", "json",
                "--max-time", max_time, "--auto-approve", "--tools", "read,bash,write"]
        if continuation:
            argv.append("--continue")
        argv.append("Complete the fixture using the requested tools; never repeat a completed side effect.")
        process = subprocess.Popen(argv, cwd=work, env=launch.env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   encoding="utf-8", start_new_session=True)
        self.processes.append(process)
        stdout, stderr = process.communicate(timeout=35)
        events = []
        for line in stdout.splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                events.append(value)
        messages = [event["message"] for event in events if event.get("type") == "message_end"
                    and isinstance(event.get("message"), dict)]
        return {"returncode": process.returncode, "messages": messages, "stderr": stderr, "stdout": stdout}

    def assert_success(self, result, text):
        self.assertEqual(result["returncode"], 0, result["stderr"][-1200:])
        assistants = [message for message in result["messages"] if message.get("role") == "assistant"]
        self.assertTrue(assistants, result["stderr"][-1200:])
        self.assertEqual(assistants[-1].get("stopReason"), "stop", result["stdout"][-2000:])
        actual = "".join(block.get("text", "") for block in assistants[-1]["content"] if block.get("type") == "text")
        self.assertEqual(actual, text)

    def assert_failure(self, result):
        self.assertNotEqual(result["returncode"], 0, result["stdout"][-2000:])
        assistants = [message for message in result["messages"] if message.get("role") == "assistant"]
        self.assertFalse(any(message.get("stopReason") == "stop" for message in assistants), result["stdout"][-2000:])
        self.assertTrue(any(message.get("stopReason") in ("error", "aborted") for message in assistants),
                        result["stderr"][-1200:])

    def session(self, launch):
        sessions = find_sessions(launch.home)
        self.assertEqual(len(sessions), 1)
        return sessions[0]

    def assert_wire(self, server, launch, key, count):
        self.assertEqual(len(server.posts), count)
        path = "/v1/responses" if launch.endpoint["arm"] == "ninfer" else "/v1/chat/completions"
        for request in server.posts:
            self.assertEqual(request["path"], path)
            self.assertEqual(request["headers"]["Authorization"], "Bearer " + key)
            self.assertEqual(request["headers"]["Host"], "127.0.0.1:" + str(server.httpd.server_port))
            self.assertEqual(request["body"]["model"], launch.endpoint["model"])
            self.assertTrue(request["body"]["stream"])
            self.assertNotIn("ninfer_session", request["body"])
            self.assertNotIn("X-NInfer-Session", request["headers"])
        if isinstance(server, ResponsesServer):
            self.assertEqual(server.protocol_errors, [])
        summary = summarize(self.session(launch))
        self.assertEqual(summary["providers"], [launch.endpoint["provider"]])
        self.assertEqual(summary["apis"], [launch.endpoint["api"]])
        self.assertEqual(summary["models"], [launch.endpoint["model"]])
        return summary

    def test_identical_typed_tools_fragmented_utf8_and_stateful_wire(self):
        marker = "café fixture λ"
        answer = "Résumé: λ = 7."
        for arm, lane in (("strata", "rtx4090-native"), ("ninfer", "rtx4090-native"), ("ninfer", "rtx3090-native"),
                          ("ninfer", "rtx5090-docker-local")):
            with self.subTest(arm=arm, lane=lane):
                calls = [ToolCall("read", {"i": "Reading fixture marker", "path": "marker.txt"}, fragment_size=2),
                         ToolCall("bash", {"i": "Appending fixture effect", "command": "printf 'once\\n' >> effects.txt", "timeout": 5}, fragment_size=3),
                         ToolCall("write", {"i": "Writing fixture result", "path": "answer.txt", "content": answer}, fragment_size=2)]
                specs = [ResponseSpec(text="", calls=[call], split_utf8=True) for call in calls]
                specs.append(ResponseSpec(text=answer, split_utf8=True))
                launch, work, server, plan, key = self.fixture(arm, specs, lane=lane)
                (work / "marker.txt").write_text(marker, encoding="utf-8")
                result = self.run_omp(launch, work)
                self.assert_success(result, answer)
                summary = self.assert_wire(server, launch, key, 4)
                self.assertEqual((work / "effects.txt").read_text(encoding="utf-8"), "once\n")
                self.assertEqual((work / "answer.txt").read_text(encoding="utf-8"), answer)
                self.assertGreater(server.split_writes, 0)
                self.assertEqual(summary["orphan_results"], [])
                self.assertEqual(summary["calls_without_results"], [])
                cycles = tool_cycles(load(self.session(launch)))
                self.assertEqual(len(cycles), 3)
                self.assertTrue(all(cycle["result_found"] and not cycle["is_error"] for cycle in cycles))
                emitted = [block for message in result["messages"] if message.get("role") == "assistant"
                           for block in message.get("content", []) if block.get("type") == "toolCall"]
                self.assertEqual([(block["name"], block["arguments"]) for block in emitted],
                                 [(call.name, call.arguments) for call in calls])
                second = server.posts[1]["body"]
                if arm == "ninfer":
                    outputs = [item for item in second["input"] if item.get("type") == "function_call_output"]
                    self.assertEqual([item["call_id"] for item in outputs], [calls[0].id])
                    self.assertIn(marker, json.dumps(outputs, ensure_ascii=False))
                    if second.get("previous_response_id"):
                        stateful = "previous_response_id"
                        self.assertIn(second["previous_response_id"], server.completed)
                        self.assertFalse(any(item.get("type") == "function_call" for item in second["input"]))
                    else:
                        stateful = "input_replay"
                        self.assertTrue(any(item.get("type") == "function_call" and item.get("call_id") == calls[0].id
                                            for item in second["input"]))
                        self.assertTrue(any(item.get("role") == "user" for item in second["input"]))
                else:
                    stateful = "chat_messages_replay"
                    outputs = [message for message in second["messages"] if message.get("role") == "tool"]
                    self.assertEqual([message["tool_call_id"] for message in outputs], [calls[0].id])
                    self.assertIn(marker, json.dumps(outputs, ensure_ascii=False))
                print("G25 wire " + json.dumps({"omp": plan["omp"]["version"], "arm": arm,
                      "model": launch.endpoint["model"], "continuation": stateful, "requests": 4,
                      "typed_tool_results": 3, "network_boundary": "macos-loopback-only-sandbox"}, sort_keys=True))

    def test_401_fails_closed_after_one_side_effect(self):
        for arm in ("strata", "ninfer"):
            with self.subTest(arm=arm):
                call = ToolCall("bash", {"i": "Appending fixture effect", "command": "printf 'once\\n' >> effects.txt", "timeout": 5})
                launch, work, server, _, key = self.fixture(arm, [ResponseSpec(text="", calls=[call]), ResponseSpec(status=401)])
                self.assert_failure(self.run_omp(launch, work))
                self.assert_wire(server, launch, key, 2)
                self.assertEqual((work / "effects.txt").read_text(encoding="utf-8"), "once\n")

    def test_dead_endpoint_fails_closed_without_a_side_effect(self):
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))  # Bound but not listening: no other process can claim the endpoint.
            for arm in ("strata", "ninfer"):
                with self.subTest(arm=arm):
                    launch, work, _, _, _ = self.fixture(arm, [], port=reserved.getsockname()[1])
                    self.assert_failure(self.run_omp(launch, work, max_time="8s"))
                    self.assertFalse((work / "effects.txt").exists())
                    summary = summarize(self.session(launch))
                    self.assertEqual(summary["providers"], [launch.endpoint["provider"]])

    def test_truncated_stream_never_executes_a_partial_side_effect(self):
        for arm in ("strata", "ninfer"):
            with self.subTest(arm=arm):
                cut = json.dumps({"i": "Appending fixture effect", "command": "printf 'unsafe\\n' >> effects.txt", "timeout": 5})[:-2]
                call = ToolCall("bash", cut, fragment_size=2)
                launch, work, server, _, key = self.fixture(arm, [ResponseSpec(text="", calls=[call], fault="drop"),
                                                                ResponseSpec(status=400)])
                self.assert_failure(self.run_omp(launch, work))
                self.assertFalse((work / "effects.txt").exists(), "incomplete Responses/tool SSE must never dispatch a side effect")
                self.assert_wire(server, launch, key, 1)

    def test_resume_after_failure_does_not_repeat_completed_effect(self):
        for arm in ("strata", "ninfer"):
            with self.subTest(arm=arm):
                call = ToolCall("bash", {"i": "Appending fixture effect", "command": "printf 'once\\n' >> effects.txt", "timeout": 5})
                launch, work, server, _, key = self.fixture(arm, [ResponseSpec(text="", calls=[call]), ResponseSpec(status=401),
                                                                ResponseSpec(text="Continued without repeating.")])
                self.assert_failure(self.run_omp(launch, work))
                session = self.session(launch)
                self.assertEqual((work / "effects.txt").read_text(encoding="utf-8"), "once\n")
                self.assert_success(self.run_omp(launch, work, continuation=True), "Continued without repeating.")
                self.assertEqual(self.session(launch), session)
                self.assert_wire(server, launch, key, 3)
                self.assertEqual((work / "effects.txt").read_text(encoding="utf-8"), "once\n")
                cycles = tool_cycles(load(session))
                self.assertEqual(len(cycles), 1)
                self.assertTrue(cycles[0]["result_found"])
                self.assertFalse(cycles[0]["is_error"])


if __name__ == "__main__":
    unittest.main()
