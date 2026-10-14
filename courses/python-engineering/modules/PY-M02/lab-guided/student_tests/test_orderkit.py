"""Your tests for the PY-M02 guided lab. Run them with:  python -m pytest student_tests -q

Start from the finished example below, then replace each TODO with real tests (see the lab README).
"""
from decimal import Decimal

import pytest

from orderkit import UnknownItemError, add_line, bulk_discount, order_total, parse_quantity  # noqa: F401

PRICES = {"pen": Decimal("1.50"), "ink": Decimal("19.99"), "odd": Decimal("0.125")}


@pytest.mark.parametrize("text, expected", [("1", 1), ("12", 12), ("  7 ", 7)])
def test_parse_quantity_accepts_positive_whole_numbers(text, expected):
    assert parse_quantity(text) == expected


# TODO Step B: inputs that are NOT positive whole numbers must raise ValueError (use pytest.raises with match=).
# TODO Step C: bulk_discount at every tier boundary - think about 9, 10, 49 and 50.
# TODO Step D: add_line must not share state between two calls that pass no basket.
# TODO Step E: order_total for a normal basket, a discounted line, rounding of half cents, and an unknown item.
