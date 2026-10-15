"""Reference tests for the guided lab: they pass on the correct module and kill every mutant."""
from decimal import Decimal

import pytest

from orderkit import UnknownItemError, add_line, bulk_discount, order_total, parse_quantity

PRICES = {"pen": Decimal("1.50"), "ink": Decimal("19.99"), "odd": Decimal("0.125")}


@pytest.mark.parametrize("text, expected", [("1", 1), ("12", 12), ("  7 ", 7), ("0012", 12)])
def test_parse_quantity_accepts_positive_whole_numbers(text, expected):
    assert parse_quantity(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "0", "-3", "abc", "2.5", "1e3", "+4", "٣"])
def test_parse_quantity_rejects_everything_else(text):
    with pytest.raises(ValueError, match="positive whole number"):
        parse_quantity(text)


@pytest.mark.parametrize(
    "quantity, rate",
    [(1, "0"), (9, "0"), (10, "0.10"), (11, "0.10"), (49, "0.10"), (50, "0.20"), (51, "0.20"), (500, "0.20")],
)
def test_bulk_discount_tier_boundaries(quantity, rate):
    assert bulk_discount(quantity) == Decimal(rate)


def test_add_line_starts_a_fresh_basket_each_time():
    first = add_line("pen", 2)
    second = add_line("ink", 1)
    assert first == [("pen", 2)]
    assert second == [("ink", 1)]


def test_add_line_appends_to_a_given_basket():
    basket = [("pen", 1)]
    assert add_line("ink", 3, basket) is basket
    assert basket == [("pen", 1), ("ink", 3)]


@pytest.mark.parametrize(
    "lines, expected",
    [
        ([], "0.00"),
        ([("pen", 2)], "3.00"),
        ([("pen", 10)], "13.50"),        # 15.00 less 10 %
        ([("pen", 50)], "60.00"),        # 75.00 less 20 %
        ([("ink", 3), ("pen", 1)], "61.47"),
        ([("odd", 1)], "0.13"),          # 0.125 rounds half-up
        ([("odd", 3)], "0.38"),          # 0.375 rounds half-up
    ],
)
def test_order_total(lines, expected):
    assert order_total(lines, PRICES) == Decimal(expected)


def test_order_total_rejects_unknown_items():
    with pytest.raises(UnknownItemError):
        order_total([("quill", 1)], PRICES)
