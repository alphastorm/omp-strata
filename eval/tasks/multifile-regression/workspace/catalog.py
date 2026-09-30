"""Import a complete replacement catalog; the last duplicate row wins."""


def load_records(rows):
    return {row["sku"]: int(row["cents"]) for row in rows}
