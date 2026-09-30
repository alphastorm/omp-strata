import unittest
from catalog import load_records
from pricing import PriceBook


class CatalogContract(unittest.TestCase):
    def test_last_canonical_duplicate_and_leading_zeros(self):
        rows = [{"sku": "  STRASSE-001 ", "cents": "200"},
                {"sku": "Straße-001", "cents": "319"}, {"sku": "strasse-1", "cents": "7"}]
        self.assertEqual(load_records(rows), {"strasse-001": 319, "strasse-1": 7})
        book = PriceBook(rows)
        self.assertEqual(book.quote("STRASSE-001"), 319)
        self.assertEqual(book.quote(" strasse-1 "), 7)

    def test_cache_respects_quantity_and_replacement(self):
        book = PriceBook([{"sku": "x", "cents": "103"}])
        for quantity, total in [(1, 103), (10, 957), (2, 206), (11, 1053), (1, 103)]:
            self.assertEqual(book.quote(" X ", quantity), total)
        book.replace([{"sku": "X", "cents": "201"}, {"sku": "new", "cents": "1"}])
        self.assertEqual(book.quote("x", 10), 1869)
        book.replace([])
        with self.assertRaises(KeyError):
            book.quote("x", 10)

    def test_instances_and_quantity_validation(self):
        first = PriceBook([{"sku": "x", "cents": "2"}])
        second = PriceBook([{"sku": "x", "cents": "5"}])
        self.assertEqual(first.quote("x"), 2)
        self.assertEqual(second.quote("x"), 5)
        for value in [True, 0, -1, 2.5, "2"]:
            with self.assertRaises(ValueError):
                first.quote("x", value)
