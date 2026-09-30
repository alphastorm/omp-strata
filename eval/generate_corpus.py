"""Deterministic synthetic archive, generated outside the model-visible source tree."""
from __future__ import annotations

import csv
import io
import random
from pathlib import Path

SEED = 6042042


def corpus() -> dict[str, str]:
    rng = random.Random(SEED)
    identifiers = list(range(1000, 1144))
    rng.shuffle(identifiers)
    files = {}
    index = io.StringIO(newline="")
    writer = csv.writer(index, lineterminator="\n")
    writer.writerow(["ticket", "decision_file"])
    for number, revision in enumerate(identifiers):
        ticket = f"LC-{number:03d}"
        decision = f"decisions/decision-{number:03d}.txt"
        writer.writerow([ticket, decision])
        files[f"docs/{decision}"] = (
            f"Approved rollout {ticket}\nAuthority: policy revision R-{revision}\n"
            f"Policy file: policies/revision-{revision}.txt\n"
            "Status: accepted. Earlier proposals are superseded by this revision.\n"
        )
        route = f"lane-{rng.randrange(100, 999)}"
        cutover, origin, width = rng.randrange(1000000, 1900000), rng.randrange(3, 50), rng.randrange(20, 90)
        if number == 42:
            route, cutover, origin, width = "copper", 1729000, 17, 43
        text = (
            f"Policy revision R-{revision}; status APPROVED; rollout {ticket}\n"
            f"Applies only to route {route}. Effective timestamp: {cutover} inclusive.\n"
            f"At or after cutover the bucket is floor((timestamp - {origin}) / {width}).\n"
            "Before cutover and for every other route preserve timestamp // 60.\n"
            "Held items never receive a bucket and return None, including after cutover.\n"
            "The origin is absolute, not relative to the cutover. Units are integer seconds.\n\n"
            "Review and operational notes (informational; not additional routing rules):\n"
        )
        while len(text) < 1850:
            batch = rng.randrange(10000, 99999)
            count = rng.randrange(5, 45)
            topic = rng.choice(["late arrivals", "backfilled records", "boundary alignment", "batch accounting",
                                "replay ordering", "held-item isolation", "archive retention"])
            text += (f"Audit batch {batch} checked {count} examples of {topic}. "
                     "The review retained the approved formula above; archive readers must resolve "
                     "the exact revision rather than assume neighboring routes share a clock.\n")
        files[f"docs/policies/revision-{revision}.txt"] = text
    files["docs/rollouts.csv"] = index.getvalue()
    return files


def generate(workspace: Path) -> None:
    for name, text in corpus().items():
        path = workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    generate(parser.parse_args().workspace)
