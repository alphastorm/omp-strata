# Repair the settlement reporting pipeline

The offline settlement CLI disagrees with the finance contract. Read docs/format.md, inspect the CSV
example, reproduce the discrepancy via python -m ledger examples/settlements.csv --start
2026-01-01T00:00:00+00:00 --end 2026-01-02T00:00:00+00:00, then inspect and fix every affected stage.
Exercise the command and the unittest suite after editing; inspect failures and iterate rather than
replacing the application with a one-off expected answer. Preserve the public report(path,start,end)
API and python -m ledger CLI. Use only the standard library. Do not modify docs, examples, or visible
tests. The workspace is the only permitted working tree.
