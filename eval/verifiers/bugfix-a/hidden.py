import unittest
from calendar_slots import available


class AvailabilityContract(unittest.TestCase):
    def test_clipping_overlap_and_adjacency(self):
        cases = [[], [(-9, -2)], [(20, 25)], [(-3, 3), (8, 14)],
                 [(2, 9), (3, 4), (4, 7)], [(1, 3), (3, 5)], [(-5, 30)],
                 [(7, 15), (0, 2), (1, 10)], [(10, 11), (-1, 0)]]
        for busy in cases:
            original = list(busy)
            with self.subTest(busy=busy):
                result = available((0, 10), busy)
                expected = {minute for minute in range(10)
                            if not any(left <= minute < right for left, right in busy)}
                actual = [minute for left, right in result for minute in range(left, right)]
                self.assertEqual(set(actual), expected)
                self.assertEqual(len(actual), len(expected), "free intervals overlap")
                self.assertTrue(all(0 <= left < right <= 10 for left, right in result))
                self.assertEqual(result, sorted(result))
                self.assertEqual(busy, original)

    def test_empty_window_never_emits_interval(self):
        self.assertEqual(available((5, 5), [(-4, 1), (12, 15)]), [])

    def test_negative_window(self):
        self.assertEqual(available((-8, -1), [(-6, -3), (-5, -4)]), [(-8, -6), (-3, -1)])
