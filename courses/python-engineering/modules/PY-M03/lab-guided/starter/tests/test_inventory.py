"""Tests for the flat script. Run from this folder:  python -m pytest"""
from pathlib import Path

import pytest

import inventory

SAMPLE = str(Path(__file__).resolve().parents[1] / "sample" / "products.csv")


def test_total_value_of_the_sample():
    assert inventory.total_value(inventory.load_products(SAMPLE)) == pytest.approx(126.0)


def test_low_stock_compares_numbers_not_text():
    assert inventory.low_stock(inventory.load_products(SAMPLE)) == ["B-200", "D-400"]


def test_unknown_focus_sku_is_a_clear_error():
    products = inventory.load_products(SAMPLE)
    with pytest.raises(ValueError, match="unknown SKU: Z-999"):
        inventory.format_report(products, "Z-999")


def test_restock_plan_within_budget():
    products = inventory.load_products(SAMPLE)
    assert inventory.restock_plan(products, 100.0) == [("B-200", 2), ("D-400", 1)]


def test_restock_plan_over_budget_is_an_error_not_none():
    products = inventory.load_products(SAMPLE)
    with pytest.raises(ValueError, match="budget"):
        inventory.restock_plan(products, 1.0)
