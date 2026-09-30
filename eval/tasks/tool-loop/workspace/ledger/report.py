"""Aggregate the selected settlement window."""
from .reader import read_events
from .reduce import settle


def report(path, start, end):
    totals = {}
    selected = [event for event in read_events(path) if start <= event["at"] <= end]
    for event in settle(selected):
        totals[event["account"]] = totals.get(event["account"], 0) + max(event["cents"], 0)
    return dict(sorted(totals.items()))
