import unittest
from scheduler import select


class SchedulerTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(select([]), [])

    def test_distinct_readings_stay_ordered(self):
        first = {"time": 24, "sequence": 1, "payload": "first"}
        second = {"time": 35, "sequence": 2, "payload": "second"}
        self.assertEqual(select([second, first]), [first, second])
