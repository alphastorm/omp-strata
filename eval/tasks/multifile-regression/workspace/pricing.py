"""Quantity-sensitive quotes over a replaceable catalog."""
from catalog import load_records


class PriceBook:
    def __init__(self, rows):
        self.cache = {}
        self.replace(rows)

    def replace(self, rows):
        self.items = load_records(rows)

    def quote(self, sku, quantity=1):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if sku not in self.cache:
            subtotal = self.items[sku] * quantity
            self.cache[sku] = subtotal * 93 // 100 if quantity >= 10 else subtotal
        return self.cache[sku]
