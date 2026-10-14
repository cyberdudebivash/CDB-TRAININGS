"""Plain-text report."""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from invkit.models import Product
from invkit.stock import find_product, low_stock, restock_plan, total_value


def format_report(products: Sequence[Product], focus: str | None = None, budget: Decimal | None = None) -> str:
    lines = [f"products: {len(products)}", f"stock value: {total_value(products):.2f}"]
    if focus:
        product = find_product(products, focus)
        if product is None:
            raise ValueError(f"unknown SKU: {focus}")
        lines.append(f"focus: {product.name}")
    lines.append("low stock: " + (", ".join(low_stock(products)) or "none"))
    if budget is not None:
        for sku, units in restock_plan(products, budget):
            lines.append(f"restock {sku}: {units}")
    return "\n".join(lines)
