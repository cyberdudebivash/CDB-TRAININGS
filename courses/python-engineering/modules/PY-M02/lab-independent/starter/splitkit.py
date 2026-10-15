"""splitkit - split a bill between people without losing or inventing a cent (PY-M02 independent lab).

This module is correct. Your job is to write a test suite good enough to catch defects that someone else may introduce later.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")
_BAD_AMOUNT = "invalid amount"


def _ascii_digits(text: str) -> bool:
    return bool(text) and text.isascii() and text.isdigit()


def parse_amount(text: str) -> Decimal:
    """Parse text such as '12', '12.5' or ' 12.50 ' into a Decimal with exactly two decimal places.

    Allowed: ASCII digits, optionally one dot followed by one or two ASCII digits, surrounding whitespace.
    Not allowed (ValueError('invalid amount')): empty text, a sign, thousands separators, a bare dot, '5.', '.5', more than two decimals.
    """
    cleaned = text.strip()
    whole, dot, fraction = cleaned.partition(".")
    if not _ascii_digits(whole):
        raise ValueError(_BAD_AMOUNT)
    if dot and (not _ascii_digits(fraction) or len(fraction) > 2):
        raise ValueError(_BAD_AMOUNT)
    return Decimal(cleaned).quantize(_CENT)


def split_bill(total: Decimal, people: int) -> list[Decimal]:
    """Split `total` (a whole number of cents) into `people` shares that add up to exactly `total`.

    Everyone pays the same number of whole cents except that the first `total_cents % people` people pay one cent more.
    ValueError for people < 1, a negative total, or a total with fractions of a cent.
    """
    if people < 1 or total < 0 or total != total.quantize(_CENT):
        raise ValueError("invalid split")
    cents = int(total * 100)
    base, extra = divmod(cents, people)
    return [Decimal(base + (1 if i < extra else 0)) / 100 for i in range(people)]


def add_service_charge(total: Decimal, percent: Decimal) -> Decimal:
    """Add a service charge of `percent` (0 to 100 inclusive) and round half-up to cents. ValueError outside that range."""
    if not (Decimal("0") <= percent <= Decimal("100")):
        raise ValueError("percent must be between 0 and 100")
    return (total * (1 + percent / 100)).quantize(_CENT, rounding=ROUND_HALF_UP)
