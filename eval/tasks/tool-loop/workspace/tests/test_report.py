import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from ledger.report import report


class ReportTests(unittest.TestCase):
    def run_report(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            path.write_text("account,event,at,kind,amount,reference\n" + rows, encoding="utf-8")
            return report(path, datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
                          datetime.fromisoformat("2026-01-02T00:00:00+00:00"))

    def test_ordinary_charge(self):
        self.assertEqual(self.run_report("a,one,2026-01-01T12:00:00+00:00,charge,1.00,\n"), {"a": 100})

    def test_negative_charge_is_a_refund(self):
        self.assertEqual(self.run_report("a,one,2026-01-01T12:00:00+00:00,charge,-1.00,\n"), {"a": -100})
