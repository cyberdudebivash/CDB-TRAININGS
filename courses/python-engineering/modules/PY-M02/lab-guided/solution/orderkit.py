"""orderkit - a tiny order-handling module used in the PY-M02 guided lab (correct reference version)."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_QTY_MSG = "quantity must be a positive whole number"
_CENT = Decimal("0.01")


class UnknownItemError(KeyError):
    """Raised when a basket line names an item that has no price."""


def parse_quantity(text: str) -> int:
    """Turn user input such as ' 12 ' into 12. Anything that is not a positive whole number raises ValueError."""
    cleaned = text.strip()
    if not (cleaned.isascii() and cleaned.isdigit()) or int(cleaned) < 1:
        raise ValueError(_QTY_MSG)
    return int(cleaned)


def bulk_discount(quantity: int) -> Decimal:
    """Discount rate for one line: 0 below 10 units, 10 % from 10 units, 20 % from 50 units."""
    if quantity >= 50:
        return Decimal("0.20")
    if quantity >= 10:
        return Decimal("0.10")
    return Decimal("0")


def add_line(item: str, quantity: int, basket: list | None = None) -> list:
    """Append (item, quantity) to basket and return it; start a new basket when none is given."""
    if basket is None:
        basket = []
    basket.append((item, quantity))
    return basket


def order_total(basket: list, prices: dict[str, Decimal]) -> Decimal:
    """Sum of price * quantity * (1 - discount) over all lines, rounded half-up to whole cents once at the end."""
    total = Decimal("0")
    for item, quantity in basket:
        try:
            unit = prices[item]
        except KeyError:
            raise UnknownItemError(item) from None
        total += unit * quantity * (1 - bulk_discount(quantity))
    return total.quantize(_CENT, rounding=ROUND_HALF_UP)
