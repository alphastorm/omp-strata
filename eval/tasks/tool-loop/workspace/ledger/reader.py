"""Read the documented settlement CSV format."""
from datetime import datetime


def read_events(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    headers = lines[0].split(",")
    for line in lines[1:]:
        row = dict(zip(headers, line.split(",")))
        yield {
            "account": row["account"], "event": row["event"],
            "at": datetime.fromisoformat(row["at"]), "kind": row["kind"],
            "cents": int(float(row["amount"]) * 100), "reference": row["reference"],
        }
