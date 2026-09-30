"""Time bucket assignment for the archive router."""


def bucket(timestamp, route, *, held=False):
    if held:
        return None
    return timestamp // 60
