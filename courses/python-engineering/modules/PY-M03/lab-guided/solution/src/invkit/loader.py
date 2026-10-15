"""Read products from a CSV file with a header row (sku,name,qty,price,reorder_level)."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from invkit.models import Product

_COLUMNS = ("sku", "name", "qty", "price", "reorder_level")


def load_products(path: str | Path) -> list[Product]:
    """Parse the file; a malformed row raises ValueError naming the line number."""
    products: list[Product] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or tuple(reader.fieldnames) != _COLUMNS:
            raise ValueError(f"expected columns {', '.join(_COLUMNS)}")
        for row in reader:
            try:
                products.append(Product(row["sku"], row["name"], int(row["qty"]), Decimal(row["price"]), int(row["reorder_level"])))
            except (ValueError, InvalidOperation, TypeError) as exc:
                raise ValueError(f"line {reader.line_num}: invalid row") from exc
    return products
