import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from ledger.report import report


class SettlementContract(unittest.TestCase):
    def test_cross_account_dedup_voids_and_exact_signed_money(self):
        rows = [
            ["shop,one", "a", "2026-01-01T12:00:00+00:00", "charge", "0.29", ""],
            ["shop,one", "a", "2026-01-01T13:00:00+00:00", "charge", "99.00", ""],
            ["shop,one", "refund", "2026-01-01T13:00:00+00:00", "charge", "-0.10", ""],
            ["other\naccount", "a", "2026-01-01T14:00:00+00:00", "charge", "4.00", ""],
            ["shop,one", "void", "2026-01-03T00:00:00+00:00", "void", "0.00", "a"],
            ["precise", "b", "2026-01-01T01:00:00+01:00", "charge", "90071992547409.93", ""],
            ["large", "b", "2026-01-01T02:00:00+00:00", "charge", "123456789012345678901234567890.12", ""],
            ["precise", "c", "2026-01-01T23:00:00-01:00", "charge", "12.00", ""],
            ["zero", "z1", "2026-01-01T03:00:00+00:00", "charge", "1.00", ""],
            ["zero", "z2", "2026-01-01T04:00:00+00:00", "charge", "-1.00", ""],
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["account", "event", "at", "kind", "amount", "reference"])
                writer.writerows(rows)
            start, end = "2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00"
            expected = {"shop,one": -10, "other\naccount": 400, "precise": 9007199254740993,
                        "large": 12345678901234567890123456789012, "zero": 0}
            self.assertEqual(report(path, datetime.fromisoformat(start), datetime.fromisoformat(end)), expected)
            result = subprocess.run([sys.executable, "-B", "-m", "ledger", str(path), "--start", start,
                                     "--end", end], cwd=WORKSPACE, stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), expected)

    def test_void_before_charge_and_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch.csv"
            path.write_text("account,event,at,kind,amount,reference\n"
                            "a,v,2025-12-31T00:00:00+00:00,void,0.00,c\n"
                            "a,c,2026-01-01T01:00:00+00:00,charge,1.00,\n"
                            "b,c,2026-01-01T00:00:00+00:00,charge,0.29,\n", encoding="utf-8")
            self.assertEqual(report(path, datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
                                    datetime.fromisoformat("2026-01-02T00:00:00+00:00")), {"b": 29})
