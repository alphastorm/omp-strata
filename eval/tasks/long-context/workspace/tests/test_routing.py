import unittest
from routing import bucket


class RoutingTests(unittest.TestCase):
    def test_existing_route(self):
        self.assertEqual(bucket(121, "legacy"), 2)
        self.assertEqual(bucket(-1, "legacy"), -1)

    def test_hold(self):
        self.assertIsNone(bucket(121, "legacy", held=True))
