import unittest
from routing import bucket


class ArchivedPolicyContract(unittest.TestCase):
    def test_exact_approved_cutover_origin_and_width(self):
        for timestamp in [1728999, 1729000, 1729001, 1729017, 1729059, 2000001]:
            with self.subTest(timestamp=timestamp):
                expected = (timestamp - 17) // 43 if timestamp >= 1729000 else timestamp // 60
                self.assertEqual(bucket(timestamp, "copper"), expected)
        for boundary in range(40210, 40240):
            for delta in [-1, 0, 1]:
                timestamp = 17 + boundary * 43 + delta
                self.assertEqual(bucket(timestamp, "copper"), (timestamp - 17) // 43)

    def test_scope_and_hold_remain_unchanged(self):
        for timestamp in [-200, 0, 1728999, 1729000, 2000000]:
            self.assertEqual(bucket(timestamp, "another-route"), timestamp // 60)
            self.assertIsNone(bucket(timestamp, "copper", held=True))
            self.assertIsNone(bucket(timestamp, "another-route", held=True))
