"""The canonical identifier contract shared by importers and consumers."""


def canonical(value):
    return value.strip().casefold()
