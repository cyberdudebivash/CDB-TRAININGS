from decimal import Decimal
from pathlib import Path

import pytest

from invkit import Product, find_product, format_report, load_products, low_stock, restock_plan, total_value

SAMPLE = Path(__file__).resolve().parents[1] / "sample" / "products.csv"


def test_total_value_of_the_sample() -> None:
    assert total_value(load_products(SAMPLE)) == Decimal("126.00")


def test_low_stock_compares_numbers_not_text() -> None:
    assert low_stock(load_products(SAMPLE)) == ["B-200", "D-400"]


def test_find_product_returns_none_for_unknown_sku() -> None:
    products = load_products(SAMPLE)
    assert find_product(products, "Z-999") is None
    found = find_product(products, "A-100")
    assert isinstance(found, Product) and found.name == "Widget"


def test_unknown_focus_sku_is_a_clear_error() -> None:
    with pytest.raises(ValueError, match="unknown SKU: Z-999"):
        format_report(load_products(SAMPLE), "Z-999")


def test_restock_plan_within_budget_and_over_budget() -> None:
    products = load_products(SAMPLE)
    assert restock_plan(products, Decimal("100")) == [("B-200", 2), ("D-400", 1)]
    with pytest.raises(ValueError, match="budget too small for B-200"):
        restock_plan(products, Decimal("1"))
