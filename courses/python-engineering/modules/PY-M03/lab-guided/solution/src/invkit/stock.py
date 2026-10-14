"""Calculations on a list of products."""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from invkit.models import Product


def total_value(products: Sequence[Product]) -> Decimal:
    return sum((p.qty * p.price for p in products), Decimal("0"))


def find_product(products: Sequence[Product], sku: str) -> Product | None:
    return next((p for p in products if p.sku == sku), None)


def low_stock(products: Sequence[Product]) -> list[str]:
    return [p.sku for p in products if p.is_low]


def restock_plan(products: Sequence[Product], budget: Decimal) -> list[tuple[str, int]]:
    """Units to buy per low-stock SKU, in file order. ValueError('budget too small for <sku>') when the next purchase does not fit."""
    plan: list[tuple[str, int]] = []
    remaining = budget
    for p in products:
        if p.is_low:
            units = p.reorder_level - p.qty
            cost = units * p.price
            if cost > remaining:
                raise ValueError(f"budget too small for {p.sku}")
            remaining -= cost
            plan.append((p.sku, units))
    return plan
