import unittest
from line_stream import LineDecoder


class UnicodeLineContract(unittest.TestCase):
    def test_every_two_way_transport_split(self):
        text = "\nalpha\r\n雪☃\n\nlast\r"
        payload = text.encode("utf-8")
        expected = ["", "alpha", "雪☃", "", "last\r"]
        for split in range(len(payload) + 1):
            with self.subTest(split=split):
                stream = LineDecoder()
                actual = stream.feed(payload[:split]) + stream.feed(payload[split:], final=True)
                self.assertEqual(actual, expected)

    def test_bytewise_emoji_and_preserved_carriage_return(self):
        stream = LineDecoder()
        lines = []
        for value in "a\rb\r\r\n🧭\n".encode():
            lines.extend(stream.feed(bytes([value])))
        lines.extend(stream.feed(b"", final=True))
        self.assertEqual(lines, ["a\rb\r", "🧭"])
        with self.assertRaises(ValueError):
            stream.feed(b"again")

    def test_incomplete_and_invalid_utf8_are_errors(self):
        stream = LineDecoder()
        self.assertEqual(stream.feed(bytes([0xE2])), [])
        with self.assertRaises(UnicodeDecodeError):
            stream.feed(b"", final=True)
        with self.assertRaises(UnicodeDecodeError):
            LineDecoder().feed(bytes([0xFF]), final=True)

    def test_independent_streams_and_empty_final(self):
        first, second = LineDecoder(), LineDecoder()
        first.feed(b"left")
        self.assertEqual(second.feed(b"right\n", final=True), ["right"])
        self.assertEqual(first.feed(b"", final=True), ["left"])
        self.assertEqual(LineDecoder().feed(b"", final=True), [])
