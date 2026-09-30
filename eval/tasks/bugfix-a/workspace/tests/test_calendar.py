import unittest
from calendar_slots import available


class CalendarTests(unittest.TestCase):
    def test_single_booking(self):
        self.assertEqual(available((0, 10), [(3, 6)]), [(0, 3), (6, 10)])

    def test_nested_booking_regression(self):
        self.assertEqual(available((0, 12), [(2, 10), (4, 6)]), [(0, 2), (10, 12)])

    def test_reversed_window(self):
        with self.assertRaises(ValueError):
            available((10, 2), [])
