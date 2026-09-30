import copy
import unittest
from scheduler import select


class CalibrationContract(unittest.TestCase):
    def test_boundaries_and_sequence_not_input_order(self):
        events = [
            {"time": 34, "sequence": 2, "payload": {"label": "next"}},
            {"time": 33, "sequence": 9, "payload": {"label": "winner"}},
            {"time": 23, "sequence": 4, "payload": {"label": "older"}},
            {"time": 22, "sequence": 6, "payload": {"label": "previous"}},
            {"time": -1, "sequence": 8, "payload": {"label": "negative"}},
        ]
        original = copy.deepcopy(events)
        self.assertEqual(select(events), [events[4], events[3], events[1], events[0]])
        self.assertEqual(select(list(reversed(events))), [events[4], events[3], events[1], events[0]])
        self.assertEqual(events, original)

    def test_shifted_buckets_do_not_use_time_as_tie_break(self):
        left = {"time": 68, "sequence": 30, "payload": "left"}
        right = {"time": 77, "sequence": 20, "payload": "right"}
        following = {"time": 78, "sequence": 5, "payload": "following"}
        self.assertEqual(select([left, following, right]), [left, following])
