"""PY-M12 guided lab, step D (fee policies: behaviour behind a small interface). Run: python -m pytest checks/test_step_d_fees.py"""
from __future__ import annotations

import pytest


def usd(lk, cents: int):
    return lk.Money(cents, "USD")


def test_policies_satisfy_the_fee_policy_protocol_without_inheriting_from_it(lk):
    for p in (lk.FlatFee(usd(lk, 1)), lk.PercentFee(100), lk.Capped(lk.PercentFee(100), usd(lk, 5)), lk.Combined()):
        assert isinstance(p, lk.FeePolicy) and lk.FeePolicy not in type(p).__mro__


def test_a_flat_fee_is_the_same_for_every_amount(lk):
    p = lk.FlatFee(usd(lk, 25))
    assert p.fee(usd(lk, 1)) == usd(lk, 25) == p.fee(usd(lk, 10**9))
    with pytest.raises(lk.CurrencyMismatch):
        p.fee(lk.Money(1, "EUR"))


@pytest.mark.parametrize("cents,bp,expected", [
    (1999, 150, 30), (1000, 295, 30), (1000, 294, 29), (1, 5000, 1), (1, 4999, 0), (0, 150, 0), (100000, 150, 1500), (3, 5000, 2), (10, 10000, 10), (999, 0, 0),
    (123456789, 1, 12346), (2, 2500, 1), (1, 10000, 1),
])
def test_a_percent_fee_rounds_half_up_with_integers(lk, cents, bp, expected):
    assert lk.PercentFee(bp).fee(usd(lk, cents)) == usd(lk, expected)


def test_a_percent_fee_never_uses_floats(lk):
    assert lk.PercentFee(1).fee(usd(lk, 10**22)).cents == 10**22 // 10_000      # a float would lose digits at this size


@pytest.mark.parametrize("bad,exc", [(-1, ValueError), (10001, ValueError), (1.5, TypeError), ("150", TypeError), (True, TypeError), (None, TypeError)])
def test_a_percent_fee_validates_basis_points(lk, bad, exc):
    with pytest.raises(exc):
        lk.PercentFee(bad)


def test_a_percent_fee_checks_currency_and_sign(lk):
    with pytest.raises(lk.CurrencyMismatch):
        lk.PercentFee(100, "EUR").fee(usd(lk, 100))
    with pytest.raises(ValueError):
        lk.PercentFee(100).fee(usd(lk, -1))
    with pytest.raises(ValueError):
        lk.PercentFee(100, "euro")


def test_capped_limits_the_inner_fee(lk):
    p = lk.Capped(lk.PercentFee(150), usd(lk, 500))
    assert p.fee(usd(lk, 1000)) == usd(lk, 15) and p.fee(usd(lk, 10**6)) == usd(lk, 500) and p.fee(usd(lk, 33334)) == usd(lk, 500)


def test_capped_works_with_any_policy_not_only_ours(lk):
    class Odd:
        def fee(self, amount):
            return lk.Money(amount.cents * 3, amount.currency)
    assert lk.Capped(Odd(), usd(lk, 10)).fee(usd(lk, 2)) == usd(lk, 6)
    assert lk.Capped(Odd(), usd(lk, 10)).fee(usd(lk, 9)) == usd(lk, 10)


def test_combined_adds_fees_and_is_zero_when_empty(lk):
    p = lk.Combined([lk.FlatFee(usd(lk, 25)), lk.PercentFee(100)])
    assert p.fee(usd(lk, 10000)) == usd(lk, 125)
    assert lk.Combined().fee(usd(lk, 10000)) == usd(lk, 0) and lk.Combined().fee(lk.Money(5, "EUR")) == lk.Money(0, "EUR")


def test_combined_stores_a_tuple_so_it_stays_hashable_and_ignores_later_changes(lk):
    parts = [lk.FlatFee(usd(lk, 1))]
    p = lk.Combined(parts)
    parts.append(lk.FlatFee(usd(lk, 100)))
    assert isinstance(p.policies, tuple) and len(p.policies) == 1 and p.fee(usd(lk, 5)) == usd(lk, 1)
    assert hash(p) == hash(lk.Combined((lk.FlatFee(usd(lk, 1)),))) and p == lk.Combined((lk.FlatFee(usd(lk, 1)),))


def test_policies_are_frozen_values(lk):
    import dataclasses
    with pytest.raises(dataclasses.FrozenInstanceError):
        lk.FlatFee(usd(lk, 1)).charge = usd(lk, 2)
    assert lk.PercentFee(100) == lk.PercentFee(100) and lk.PercentFee(100) != lk.PercentFee(101)
