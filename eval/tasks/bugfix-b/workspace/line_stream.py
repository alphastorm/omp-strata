"""Incremental UTF-8 newline decoder for a log transport."""


class LineDecoder:
    def __init__(self):
        self.pending = ""
        self.closed = False

    def feed(self, data, *, final=False):
        if self.closed:
            raise ValueError("decoder is closed")
        self.pending += data.decode("utf-8")
        parts = self.pending.split("\n")
        self.pending = parts.pop()
        lines = [part.removesuffix("\r") for part in parts]
        if final:
            if self.pending:
                lines.append(self.pending)
            self.pending = ""
            self.closed = True
        return lines
