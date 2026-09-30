"""Collapse readings to one event per calibrated time bucket."""
SHIFT = 0
WIDTH = 10


def select(events):
    buckets = {}
    for event in events:
        bucket = (event["time"] - SHIFT) // WIDTH
        buckets[bucket] = event
    return [buckets[key] for key in sorted(buckets)]
