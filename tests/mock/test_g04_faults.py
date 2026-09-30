"""G04: faults must not produce false success or repeat persisted side effects."""
import json
import os
import signal
import time
import unittest

from omp_strata.transcript import load, summarize, tool_cycles
from tests.mock.scripted_server import OmpTestCase, ResponseSpec, ToolCall


class FaultGate(OmpTestCase):
    def fault(self, label, spec):
        # A nonretryable response after the injected fault bounds transport
        # retries without a wall-clock-dependent request count.
        server = self.server([spec, ResponseSpec(status=400)])
        result = self.run_omp()
        assistants = [m for m in result["messages"] if m.get("role") == "assistant"]
        print("G04 fault " + json.dumps({"fault": label, "requests": len(server.posts),
                                         "exit": result["returncode"],
                                         "stopReasons": [m.get("stopReason") for m in assistants]}))
        self.assert_failure(result)
        self.assertEqual(len(server.posts), 1, "retry-disabled turn resent a request")

    def test_http_400(self):
        self.fault("http_400", ResponseSpec(status=400))

    def test_http_401(self):
        self.fault("http_401", ResponseSpec(status=401))

    def test_http_404(self):
        self.fault("http_404", ResponseSpec(status=404))

    def test_http_500(self):
        # Stock transport retries are independent of the session retry setting.
        # A short server Retry-After makes all twelve attempts bounded without
        # changing the HTTP status or relying on a wall-clock cancellation.
        server = self.server([ResponseSpec(status=500, headers={"Retry-After": "0.001"}) for _ in range(12)])
        result = self.run_omp()
        self.assert_failure(result)
        self.assertEqual(len(server.posts), 12)
        self.assertEqual(summarize(self.session())["providers"], ["strata-local"])
        first = server.posts[0]["body"]
        self.assertTrue(all(request["body"] == first for request in server.posts))
        print("G04 http_500 requests=12 (6 transport attempts x 2 provider attempts), exit=" + str(result["returncode"]))

    def test_connection_drop_without_finish(self):
        self.fault("connection_drop", ResponseSpec(text="Unfinished", fault="drop"))

    def test_malformed_sse(self):
        self.fault("malformed_sse", ResponseSpec(text="Unfinished", fault="malformed"))

    def test_strata_midstream_error_then_done(self):
        self.fault("strata_in_band_error", ResponseSpec(text="Unfinished", fault="in_band"))

    @unittest.expectedFailure
    def test_truncated_arguments_must_not_execute_side_effect(self):
        arguments = json.dumps({"i": "Writing fixture", "path": "repaired.txt", "content": "unsafe partial write"})[:-2]
        call = ToolCall("write", arguments)
        server = self.server([ResponseSpec(text="", calls=[call]), ResponseSpec(text="Follow-up answer.")])
        result = self.run_omp()
        changed = (self.repo / "repaired.txt").exists()
        print("G04 truncated arguments " + json.dumps({"side_effect": changed, "requests": len(server.posts),
                                                       "exit": result["returncode"]}))
        self.assertFalse(changed, "stock OMP repaired truncated JSON and executed the write tool")
        self.assert_failure(result)

    @unittest.skipUnless(os.name == "posix", "SIGINT process qualification requires POSIX")
    def test_sigint_cancels_stalled_stream(self):
        server = self.server([ResponseSpec(fault="stall")])
        process = self.start_omp()
        self.assertTrue(server.wait_for_requests(), "OMP never dispatched the stalled request")
        start = time.monotonic()
        process.send_signal(signal.SIGINT)
        result = self.finish_omp(process, timeout=10)
        self.assertLess(time.monotonic() - start, 10)
        self.assertNotEqual(result["returncode"], 0)
        self.assert_failure(result)
        self.assertEqual(len(server.posts), 1)
        print("G04 cancellation SIGINT requests=1 exit=" + str(result["returncode"]))

    def finalized_partial(self, finish_reason):
        arguments = json.dumps({"i": "Writing fixture", "path": "finalized.txt", "content": "partial payload"})[:-2]
        call = ToolCall("write", arguments, closing_fragment='"}')
        server = self.server([ResponseSpec(text="", calls=[call], finish_reason=finish_reason),
                              ResponseSpec(text="After finalized partial call.")])
        result = self.run_omp()
        path = self.repo / "finalized.txt"
        summary = summarize(self.session())
        print("G04 finalized partial " + json.dumps({"wire_finish": finish_reason, "side_effect": path.exists(),
              "requests": len(server.posts), "exit": result["returncode"], "stopReasons": summary["stopReasons"]}))
        self.assertEqual(len(server.posts), 2)
        if finish_reason == "length":
            self.assertFalse(path.exists(), "length-truncated call executed a side effect")
            cycle, = tool_cycles(load(self.session()))
            self.assertTrue(cycle["result_found"])
            self.assertTrue(cycle["is_error"])
            self.assertEqual(summary["stopReasons"], ["length", "stop"])
            self.assert_success(result, "After finalized partial call.")
        else:
            self.assertFalse(path.exists(), "finalizing partial JSON allowed a side effect")
            self.assert_failure(result)

    def test_finalized_partial_json_with_length(self):
        self.finalized_partial("length")

    @unittest.expectedFailure
    def test_finalized_partial_json_with_stop(self):
        self.finalized_partial("stop")

    def test_max_time_cancels_stalled_stream(self):
        server = self.server([ResponseSpec(fault="stall")])
        start = time.monotonic()
        result = self.finish_omp(self.start_omp(max_time="5s"), timeout=12)
        self.assertLess(time.monotonic() - start, 12)
        self.assertNotEqual(result["returncode"], 0)
        self.assert_failure(result)
        self.assertEqual(len(server.posts), 1)
        print("G04 cancellation max-time=5s requests=1 exit=" + str(result["returncode"]))

    def test_continue_does_not_repeat_completed_side_effect(self):
        call = ToolCall("bash", {"i": "Appending fixture", "command": "printf 'once\\n' >> effects.txt", "timeout": 5})
        server = self.server([ResponseSpec(text="", calls=[call]), ResponseSpec(status=400),
                              ResponseSpec(text="Recovered from the transcript.")])
        first = self.run_omp()
        self.assert_failure(first)
        self.assertEqual(len(server.posts), 2)
        path = self.repo / "effects.txt"
        self.assertEqual(path.read_text(encoding="utf-8"), "once\n")
        before = self.session()
        second = self.run_omp(extra=["--continue"], prompt="Continue without repeating completed tool actions.")
        summary = self.assert_success(second, "Recovered from the transcript.")
        self.assertEqual(self.session(), before)
        self.assertEqual(path.read_text(encoding="utf-8"), "once\n")
        self.assertEqual(len(server.posts), 3)
        cycles = tool_cycles(load(before))
        self.assertEqual([c["id"] for c in cycles], [call.id])
        self.assertTrue(cycles[0]["result_found"])
        self.assertFalse(cycles[0]["is_error"])
        replay = server.posts[2]["body"]["messages"]
        self.assertEqual(len([m for m in replay if m.get("tool_call_id") == call.id]), 1)
        self.assertTrue(summary["tool_ids_unique"])
        self.assertEqual(summary["calls_without_results"], [])
        print("G04 resume requests=2+1 side_effect_lines=1")


if __name__ == "__main__":
    unittest.main()
