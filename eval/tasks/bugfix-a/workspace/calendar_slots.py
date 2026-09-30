"""Subtract occupied half-open minute ranges from one opening window."""


def available(window, busy):
    start, end = window
    if start > end:
        raise ValueError("window is reversed")
    free = []
    cursor = start
    for left, right in sorted(busy):
        if left > cursor:
            free.append((cursor, min(left, end)))
        cursor = right
    if cursor < end:
        free.append((cursor, end))
    return free
