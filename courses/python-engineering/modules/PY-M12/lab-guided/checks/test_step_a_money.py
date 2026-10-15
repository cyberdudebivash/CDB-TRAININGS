"""PY-M12 guided lab, step A (Money: a value type). Run: python -m pytest checks/test_step_a_money.py"""
from __future__ import annotations

import pytest


def usd(lk, cents: int):
    return lk.Money(cents, "USD")


def test_money_is_a_frozen_dataclass_with_two_fields(lk):
    import dataclasses
    m = usd(lk, 5)
    assert dataclasses.is_dataclass(m) and [f.name for f in dataclasses.fields(m)] == ["cents", "currency"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.cents = 6


def test_money_default_currency_is_usd(lk):
    assert lk.Money(5).currency == "USD"


@pytest.mark.parametrize("bad", [1.5, "5", None, True, False])
def test_money_cents_must_be_a_real_int_not_a_bool(lk, bad):
    assert lk.Money(5).cents == 5
    with pytest.raises(TypeError):
        lk.Money(bad)


@pytest.mark.parametrize("bad", ["usd", "US", "USDX", "", "U$D", "ÜSD", "US1", "usD"])
def test_money_currency_must_be_three_capital_ascii_letters(lk, bad):
    with pytest.raises(ValueError):
        lk.Money(1, bad)


def test_money_currency_must_be_text(lk):
    with pytest.raises(ValueError):
        lk.Money(1, 123)


def test_money_equality_and_hash_follow_the_value(lk):
    assert usd(lk, 5) == usd(lk, 5) and hash(usd(lk, 5)) == hash(usd(lk, 5))
    assert usd(lk, 5) != usd(lk, 6) and usd(lk, 5) != lk.Money(5, "EUR")
    assert len({usd(lk, 5), usd(lk, 5), lk.Money(5, "EUR")}) == 2
    assert usd(lk, 5) != 5 and usd(lk, 5) != "5.00 USD"


def test_money_repr_shows_the_fields(lk):
    assert repr(usd(lk, 1234)) == "Money(cents=1234, currency='USD')"


@pytest.mark.parametrize("cents,text", [(1234, "12.34 USD"), (5, "0.05 USD"), (0, "0.00 USD"), (-5, "-0.05 USD"), (-123456, "-1234.56 USD"), (100, "1.00 USD")])
def test_money_str_has_two_decimals_and_a_sign(lk, cents, text):
    assert str(usd(lk, cents)) == text


@pytest.mark.parametrize("text,cents,cur", [("12.34 USD", 1234, "USD"), ("0.05 EUR", 5, "EUR"), ("-0.05 EUR", -5, "EUR"), ("1000000.00 JPY", 100000000, "JPY"), ("007.10 GBP", 710, "GBP")])
def test_money_parse_reads_the_documented_format(lk, text, cents, cur):
    assert lk.Money.parse(text) == lk.Money(cents, cur)


@pytest.mark.parametrize("bad", ["12.3 USD", "12 USD", "12.345 USD", "12.34USD", "12.34  USD", " 12.34 USD", "12.34 USD ", "12.34 usd", "+12.34 USD", "1,234.00 USD", "٣.00 USD", "12.34 USD\n", "", "abc", "12.34 US"])
def test_money_parse_is_strict(lk, bad):
    with pytest.raises(ValueError):
        lk.Money.parse(bad)


@pytest.mark.parametrize("bad", [None, 12.34, 1234, b"12.34 USD"])
def test_money_parse_rejects_non_text_with_value_error(lk, bad):
    with pytest.raises(ValueError):
        lk.Money.parse(bad)


def test_money_parse_and_str_round_trip(lk):
    for cents in (0, 1, 99, 100, 12345, -1, -99, -100, -987654):
        assert lk.Money.parse(str(usd(lk, cents))) == usd(lk, cents)


def test_money_arithmetic_stays_in_the_currency(lk):
    assert usd(lk, 5) + usd(lk, 7) == usd(lk, 12) and usd(lk, 5) - usd(lk, 7) == usd(lk, -2) and -usd(lk, 5) == usd(lk, -5)
    assert isinstance(usd(lk, 1) + usd(lk, 1), lk.Money)


def test_money_arithmetic_across_currencies_is_a_currency_mismatch(lk):
    other = lk.Money(1, "EUR")
    for op in (lambda a, b: a + b, lambda a, b: a - b, lambda a, b: a < b, lambda a, b: a <= b, lambda a, b: a > b, lambda a, b: a >= b):
        with pytest.raises(lk.CurrencyMismatch):
            op(usd(lk, 1), other)
    assert issubclass(lk.CurrencyMismatch, ValueError)


def test_money_arithmetic_with_other_types_is_not_supported(lk):
    one = usd(lk, 1)
    with pytest.raises(TypeError):
        one + 1
    with pytest.raises(TypeError):
        one < 5
    with pytest.raises(TypeError):
        one - "1"


def test_money_orders_by_cents_within_one_currency(lk):
    assert usd(lk, 1) < usd(lk, 2) and usd(lk, 2) > usd(lk, 1) and usd(lk, 2) <= usd(lk, 2) and usd(lk, 2) >= usd(lk, 2)
    assert not usd(lk, 2) < usd(lk, 2) and not usd(lk, 1) > usd(lk, 2)
    assert sorted([usd(lk, 3), usd(lk, -1), usd(lk, 2)]) == [usd(lk, -1), usd(lk, 2), usd(lk, 3)]


def test_money_is_small_and_has_no_instance_dictionary(lk):
    assert not hasattr(usd(lk, 1), "__dict__")
