"""Behaviour of the public API (the contract in the lab README). Written against `invkit`, so it fails until the package exists."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[1] / "solution" / "sample" / "products.csv"


class NotYet:
    """Stands in for something a fixture could not build because the work is not done yet: the first use re-raises the reason, so the test that needs it FAILS (a set-up error would be reported as a broken lab)."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def _raise(self, *args: object, **kwargs: object) -> None:
        raise self.error

    __getattr__ = __iter__ = __getitem__ = __len__ = _raise  # type: ignore[assignment]


@pytest.fixture(scope="module")
def invkit(project):
    sys.path.insert(0, str(project / "src"))
    for name in [n for n in sys.modules if n == "invkit" or n.startswith("invkit.")]:
        del sys.modules[name]
    try:
        try:
            import invkit as module
        except ModuleNotFoundError as exc:
            module = NotYet(AssertionError(f"cannot import invkit from {project / 'src'}: {exc}. Create the package src/invkit/ (lab README, step D)"))
        except Exception as exc:  # noqa: BLE001 - the learner's own import-time error is the failure the test should show
            module = NotYet(exc)
        yield module
    finally:
        sys.path.remove(str(project / "src"))
        for name in [n for n in sys.modules if n == "invkit" or n.startswith("invkit.")]:
            del sys.modules[name]


@pytest.fixture()
def products(invkit):
    try:
        return invkit.load_products(SAMPLE)
    except Exception as exc:  # noqa: BLE001 - re-raised by the test that uses the value, so the test fails instead of the set-up
        return NotYet(exc)


def test_load_products_builds_typed_records(invkit, products):
    assert [p.sku for p in products] == ["A-100", "B-200", "C-300", "D-400"]
    first = products[0]
    assert isinstance(first, invkit.Product) and isinstance(first.qty, int) and isinstance(first.price, Decimal) and isinstance(first.reorder_level, int)
    with pytest.raises(Exception):  # frozen record  # noqa: B017,PT011
        first.qty = 1  # type: ignore[misc]


def test_load_products_rejects_bad_files(invkit, tmp_path):
    wrong_columns = tmp_path / "wrong.csv"
    wrong_columns.write_text("sku,name\nA,B\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected columns"):
        invkit.load_products(wrong_columns)
    bad_row = tmp_path / "bad.csv"
    bad_row.write_text("sku,name,qty,price,reorder_level\nA-1,Thing,ten,1.00,5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2: invalid row"):
        invkit.load_products(bad_row)


def test_total_value_is_exact_decimal(invkit, products):
    assert invkit.total_value(products) == Decimal("126.00")
    assert invkit.total_value([]) == Decimal("0")


def test_low_stock_compares_numbers(invkit, products):
    assert invkit.low_stock(products) == ["B-200", "D-400"]


def test_find_product(invkit, products):
    assert invkit.find_product(products, "C-300").name == "Sprocket"
    assert invkit.find_product(products, "Z-999") is None


def test_restock_plan(invkit, products):
    assert invkit.restock_plan(products, Decimal("100")) == [("B-200", 2), ("D-400", 1)]
    assert invkit.restock_plan(products, Decimal("24")) == [("B-200", 2), ("D-400", 1)]
    with pytest.raises(ValueError, match="budget too small for D-400"):
        invkit.restock_plan(products, Decimal("23.99"))
    with pytest.raises(ValueError, match="budget too small for B-200"):
        invkit.restock_plan(products, Decimal("1"))
    assert invkit.restock_plan([], Decimal("0")) == []


def test_report_text_and_errors(invkit, products):
    assert invkit.format_report(products).splitlines() == ["products: 4", "stock value: 126.00", "low stock: B-200, D-400"]
    assert "focus: Widget" in invkit.format_report(products, "A-100")
    assert invkit.format_report(products, None, Decimal("100")).splitlines()[-2:] == ["restock B-200: 2", "restock D-400: 1"]
    with pytest.raises(ValueError, match="unknown SKU: Z-999"):
        invkit.format_report(products, "Z-999")


def test_command_line_entry_point(invkit, capsys):
    from invkit.cli import main

    assert main([str(SAMPLE), "A-100", "100"]) == 0
    out = capsys.readouterr().out
    assert "focus: Widget" in out and "restock D-400: 1" in out
    assert main([]) == 2
    assert main([str(SAMPLE.with_name("missing.csv"))]) == 2
    assert main([str(SAMPLE), "Z-999"]) == 2
    err = capsys.readouterr().err
    assert "usage:" in err and "unknown SKU: Z-999" in err
