import unittest
from pricing import PriceBook


class PricingTests(unittest.TestCase):
    def test_single_quote(self):
        self.assertEqual(PriceBook([{"sku": "a", "cents": "109"}]).quote("a"), 109)

    def test_import_and_lookup_share_identifier_contract(self):
        book = PriceBook([{"sku": "  Ab-001 ", "cents": "109"}])
        self.assertEqual(book.quote("ab-001"), 109)

    def test_bulk_rounds_after_multiplication(self):
        book = PriceBook([{"sku": "b", "cents": "103"}])
        self.assertEqual(book.quote("b", 10), 957)
