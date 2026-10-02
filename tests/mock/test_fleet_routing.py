"""Stock native-agent routing, read-only boundaries and measured task fan-out."""
import json
import re
import shlex
import threading
import unittest

from omp_strata.remote import RemoteSession
from omp_strata.transcript import find_sessions, load
from scripts.fanout_proof import delivered_results, run_fanout
import tests.mock.test_remote_client as fixtures
from tests.mock.scripted_server import ResponseSpec, ToolCall


def tool_names(body):
    return {item["function"]["name"] for item in body.get("tools", [])}


def message_text(body):
    parts = []
    for message in body["messages"]:
        content = message.get("content")
        parts.append(content if isinstance(content, str) else
                     "\n".join(item.get("text", "") for item in content or [] if isinstance(item, dict)))
    return "\n".join(parts)


def auxiliary_response(body, title_seen=None):
    """Native effort judgments and asynchronous task labels are not parent turns."""
    names = tool_names(body)
    if "submit_judgment" in names:
        return ResponseSpec(text="", calls=[ToolCall("submit_judgment", {"answer": "low"})])
    if not names:
        messages = message_text(body)
        if "<solution_space>" in messages:
            return ResponseSpec(text="low")
        if "<title>" in messages:
            if title_seen is not None:
                title_seen.set()
            return ResponseSpec(text="<title>Inspect fixture scope</title>")
    return None


def parent_response(body, tasks, title_seen=None):
    auxiliary = auxiliary_response(body, title_seen)
    if auxiliary is not None:
        return auxiliary
    if "task" not in tool_names(body):
        return ResponseSpec(status=500)
    delivered = set(re.findall(r'<task-result id="([^"]+)"[^>]*status="completed"', message_text(body)))
    if {task["name"] for task in tasks} <= delivered:
        return ResponseSpec(text="Every worker delivered.")
    if any(call.get("function", {}).get("name") == "task"
           for message in body["messages"] for call in message.get("tool_calls", [])):
        return ResponseSpec(text="", calls=[ToolCall("wait", {"i": "Awaiting delivered worker results"})])
    return ResponseSpec(text="", calls=[ToolCall("task", {
        "i": "Dispatching fixture workers", "context": "Synthetic routing proof", "tasks": tasks})])


def worker_turns(server):
    return [post for post in server.posts if "yield" in tool_names(post["body"])]


class FleetRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RemoteClientTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.RemoteClientTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_task_role_and_custom_model_frontmatter_route_to_worker(self):
        f = self.fixture
        for agent in (None, "scout-worker", "scout"):
            with self.subTest(agent=agent):
                original = f.root
                f.root = original / (agent or "default-task")
                f.root.mkdir()
                try:
                    task = {"name": "WorkerOne", "task": "Return the requested fixture result.",
                            "solutionSpace": "Read-only fixture"}
                    if agent:
                        task["agent"] = agent
                    expected = ({"summary": "WORKER_OK", "files": [], "architecture": "Synthetic fixture"}
                                if agent == "scout" else {"answer": "WORKER_OK"})
                    title_seen = threading.Event()
                    main = f.server(response_factory=lambda body: parent_response(body, [task], title_seen))

                    def respond(body):
                        auxiliary = auxiliary_response(body)
                        if auxiliary is not None:
                            return auxiliary
                        if "yield" not in tool_names(body):
                            return ResponseSpec(status=500)
                        if agent is None:
                            # Keep the native worker alive until its asynchronous label request arrives.
                            # That extra main-provider request exhausted the old positional scenarios.
                            title_seen.wait(5)
                        return ResponseSpec(text="", calls=[ToolCall("yield", {"data": expected})])

                    worker = f.server(response_factory=respond)
                    route, bindings = f.route({"main": main, "worker": worker}, agents={"scout-worker": "worker"})
                    code, out, err = f.run_client(route, bindings, tools="task,wait")
                    self.assertEqual(0, code, (out[-5000:], err))
                    self.assertEqual(1, len(worker_turns(worker)), "the actual worker must use the worker provider")
                    self.assertEqual([], worker_turns(main), "no worker execution may fall back to the main provider")
                    sessions = find_sessions(f.root / "omp" / "home")
                    self.assertEqual(expected, delivered_results(load(sessions[0]))["WorkerOne"])
                    names = tool_names(worker_turns(worker)[0]["body"])
                    if agent is None:
                        self.assertTrue(title_seen.is_set(), "exercise the extra native title request before yielding")
                        self.assertLessEqual({"write", "edit", "bash"}, names)
                    else:
                        self.assertFalse(names & {"write", "edit", "bash"})
                    f.assert_tunnels_gone()
                finally:
                    f.root = original

    def test_named_scout_cannot_execute_mutating_tools(self):
        f = self.fixture
        edited = f.root / "existing.txt"
        edited.write_text("ORIGINAL\n")
        written, executed = f.root / "written.txt", f.root / "executed.txt"
        task = {"name": "ReadOnly", "agent": "scout-worker", "task": "Inspect the fixture without changing it.",
                "solutionSpace": "Read-only fixture"}
        main = f.server(response_factory=lambda body: parent_response(body, [task]))
        attempts = []

        def respond(body):
            auxiliary = auxiliary_response(body)
            if auxiliary is not None:
                return auxiliary
            if "yield" not in tool_names(body):
                return ResponseSpec(status=500)
            attempts.append(body)
            if len(attempts) == 1:
                return ResponseSpec(text="", calls=[
                    ToolCall("write", {"i": "Attempting forbidden write", "path": str(written), "content": "MUTATED"}),
                    ToolCall("edit", {"i": "Attempting forbidden edit", "input": str(edited)}),
                    ToolCall("bash", {"i": "Attempting forbidden command",
                                      "command": "printf MUTATED > " + shlex.quote(str(executed))}),
                ])
            return ResponseSpec(text="", calls=[ToolCall("yield", {"data": {"answer": "READ_ONLY"}})])

        worker = f.server(response_factory=respond)
        route, bindings = f.route({"main": main, "worker": worker}, agents={"scout-worker": "worker"})
        code, out, err = f.run_client(route, bindings, tools="task,wait")
        self.assertEqual(0, code, (out[-5000:], err))
        self.assertEqual(2, len(attempts), "rejected calls must return control to the scout")
        self.assertLessEqual(tool_names(attempts[0]), {"read", "find", "grep", "glob", "yield"})
        self.assertFalse(written.exists())
        self.assertFalse(executed.exists())
        self.assertEqual("ORIGINAL\n", edited.read_text())
        sessions = find_sessions(f.root / "omp" / "home")
        self.assertEqual({"answer": "READ_ONLY"}, delivered_results(load(sessions[0]))["ReadOnly"])
        f.assert_tunnels_gone()

    def test_fanout_proof_records_serial_one_provider_and_overlapping_fleet(self):
        f = self.fixture
        for mode in ("single", "fleet"):
            with self.subTest(mode=mode):
                original = f.root
                f.root = original / mode
                f.root.mkdir()
                try:
                    tasks = []

                    def respond(body):
                        auxiliary = auxiliary_response(body)
                        if auxiliary is not None:
                            return auxiliary
                        messages = message_text(body)
                        if "yield" in tool_names(body):
                            markers = re.findall(r'Use yield with data \{"answer":"(SCOUT_[0-9a-f]{16})"\}\.', messages)
                            if not markers:
                                return ResponseSpec(status=500)
                            return ResponseSpec(text="", completion_delay_s=0.5,
                                                calls=[ToolCall("yield", {"data": {"answer": markers[-1]}})])
                        if not tasks:
                            start = messages.index('[{"name":')
                            assigned, _ = json.JSONDecoder().raw_decode(messages[start:])
                            tasks.extend(assigned)
                        return parent_response(body, tasks)

                    main = f.server(response_factory=respond)
                    servers = {"main": main}
                    agents = {"scout-a": "main", "scout-b": "main"}
                    if mode == "fleet":
                        servers["worker"] = f.server(response_factory=respond)
                        agents["scout-b"] = "worker"
                    route, bindings = f.route(servers, agents=agents)
                    with RemoteSession(route, f.root, bindings, ssh=f.ssh) as session:
                        result = run_fanout(session, binary=f.binary, work=f.root / "work", scouts=2, timeout=35)
                    self.assertEqual(2, result["delivered_results"])
                    for provider in result["providers"].values():
                        self.assertEqual(1, provider["peak_active"], "each server serializes its own requests")
                    self.assertEqual(1 if mode == "single" else 2, result["combined"]["peak_active"])
                    if mode == "fleet":
                        self.assertGreater(result["combined"]["overlap_seconds"], 0.1)
                    f.assert_tunnels_gone()
                finally:
                    f.root = original


if __name__ == "__main__":
    unittest.main()
