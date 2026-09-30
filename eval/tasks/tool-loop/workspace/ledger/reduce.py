"""Reduce one batch, ignoring retransmissions and explicit voids."""


def settle(events):
    unique = {}
    for event in events:
        unique.setdefault(event["event"], event)
    voided = {event["reference"] for event in unique.values() if event["kind"] == "void"}
    return [event for event in unique.values()
            if event["kind"] == "charge" and event["event"] not in voided]
