# Fix the catalog replacement regression

A refactor split imports and quoting into separate modules. sku.canonical is the authoritative contract:
trim surrounding whitespace and casefold, preserving punctuation and leading zeros. Both imports and
lookups must follow it. Last canonical duplicate import wins. A complete replacement must drop old
items and invalidate stale quotes. Quotes are integer cents, quantity-sensitive, with a 7 percent bulk
discount for quantity >= 10 (floor once after multiplication). Unknown identifiers raise KeyError;
invalid quantities raise ValueError. Two PriceBook instances must not share mutable state.

Inspect the whole path, repair the regression across files, and run python -m unittest discover -s tests -v.
Do not edit visible tests or sku.py (the shared contract is immutable). Work only in this workspace.
