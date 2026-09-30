"""RPC event ordering: stock OMP emits an aborted run's agent_end before the abort command's response."""
import queue
import unittest

from omp_strata.rpc import RpcOmp


def client_with(events: list[dict]) -> RpcOmp:
    client = object.__new__(RpcOmp)  # the event loop only; no OMP process is needed for ordering
    client.events = queue.Queue()
    client.log = []
    client._held = []
    for event in events:
        client.events.put(event)
    return client


class RpcOrderingTests(unittest.TestCase):
    def test_agent_end_before_command_response_is_kept_for_the_run_waiter(self):
        client = client_with([{"type": "message_end"}, {"type": "agent_end", "messages": []},
                              {"type": "response", "id": "7", "success": True}])
        response = client.wait_for(lambda e: e.get("type") == "response" and e.get("id") == "7", timeout=1)
        self.assertEqual(response["id"], "7")
        end = client.wait_for(lambda e: e.get("type") == "agent_end", timeout=1)
        self.assertEqual(end["type"], "agent_end")
        with self.assertRaises(TimeoutError):  # consumed exactly once
            client.wait_for(lambda e: e.get("type") == "agent_end", timeout=0.2)

    def test_streaming_updates_are_not_retained(self):
        client = client_with([{"type": "message_update"}, {"type": "response", "id": "1", "success": True}])
        client.wait_for(lambda e: e.get("type") == "response", timeout=1)
        self.assertEqual(client._held, [])


if __name__ == "__main__":
    unittest.main()
