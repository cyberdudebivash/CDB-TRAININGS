"""Data model: one immutable record per product."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    qty: int
    price: Decimal
    reorder_level: int

    @property
    def is_low(self) -> bool:
        return self.qty < self.reorder_level
