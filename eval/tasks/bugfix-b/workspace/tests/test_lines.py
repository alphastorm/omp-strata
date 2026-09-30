import unittest
from line_stream import LineDecoder


class LineTests(unittest.TestCase):
    def test_ascii_fragments(self):
        stream = LineDecoder()
        self.assertEqual(stream.feed(b"ab"), [])
        self.assertEqual(stream.feed(b"c\r\nnext"), ["abc"])
        self.assertEqual(stream.feed(b"", final=True), ["next"])

    def test_transport_splits_unicode(self):
        stream = LineDecoder()
        payload = "café\n".encode()
        self.assertEqual(stream.feed(payload[:4]), [])
        self.assertEqual(stream.feed(payload[4:], final=True), ["café"])
