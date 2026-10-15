"""PY-M12 guided lab, step B (Account: state that belongs to the instance). Run: python -m pytest checks/test_step_b_account.py"""
from __future__ import annotations

import pytest


def usd(lk, cents: int):
    return lk.Money(cents, "USD")


def test_account_starts_empty_with_a_cleaned_owner(lk):
    a = lk.Account("  ann ")
    assert a.owner == "ann" and a.balance == usd(lk, 0) and a.history == ()


@pytest.mark.parametrize("bad", ["", "   ", None, 5])
def test_account_needs_a_real_owner_name(lk, bad):
    with pytest.raises(ValueError):
        lk.Account(bad)


def test_account_can_use_another_currency(lk):
    assert lk.Account("e", currency="EUR").balance == lk.Money(0, "EUR")


def test_account_overdraft_rules_are_checked_at_creation(lk):
    with pytest.raises(lk.CurrencyMismatch):
        lk.Account("x", currency="EUR", overdraft=usd(lk, 5))
    with pytest.raises(ValueError):
        lk.Account("x", overdraft=usd(lk, -1))


def test_account_numbers_are_unique_and_the_counter_is_class_state(lk):
    before = lk.Account.opened
    a, b = lk.Account("a"), lk.Account("b")
    assert lk.Account.opened == before + 2 and b.number == a.number + 1
    assert "opened" not in vars(a) and "opened" not in vars(b), "count on the class: Account.opened += 1, not self.opened += 1"
    assert a.number != b.number


def test_account_state_is_never_shared_between_accounts(lk):
    a, b = lk.Account("a"), lk.Account("b")
    a.deposit(usd(lk, 100))
    assert b.balance == usd(lk, 0) and b.history == () and len(a.history) == 1


def test_account_balance_is_read_only(lk):
    a = lk.Account("a")
    for name in ("balance", "owner", "number", "history"):
        with pytest.raises(AttributeError):
            setattr(a, name, 1)


def test_deposit_returns_the_new_balance_and_records_an_entry(lk):
    a = lk.Account("a")
    assert a.deposit(usd(lk, 150)) == usd(lk, 150) and a.deposit(usd(lk, 50)) == usd(lk, 200)
    assert a.history == (lk.Entry("deposit", usd(lk, 150), usd(lk, 150)), lk.Entry("deposit", usd(lk, 50), usd(lk, 200)))


def test_withdraw_returns_the_new_balance_and_records_an_entry(lk):
    a = lk.Account("a"); a.deposit(usd(lk, 500))
    assert a.withdraw(usd(lk, 120)) == usd(lk, 380)
    assert a.history[-1] == lk.Entry("withdraw", usd(lk, 120), usd(lk, 380))


def test_history_is_a_tuple_copy(lk):
    a = lk.Account("a"); a.deposit(usd(lk, 5))
    h = a.history
    assert isinstance(h, tuple)
    a.deposit(usd(lk, 5))
    assert len(h) == 1 and len(a.history) == 2


def test_entry_is_an_immutable_value(lk):
    import dataclasses
    e = lk.Entry("deposit", usd(lk, 1), usd(lk, 1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.kind = "x"
    assert hash(e) == hash(lk.Entry("deposit", usd(lk, 1), usd(lk, 1)))


@pytest.mark.parametrize("call,exc", [
    (lambda lk, a: a.deposit(5), TypeError), (lambda lk, a: a.deposit("5.00 USD"), TypeError), (lambda lk, a: a.deposit(None), TypeError),
    (lambda lk, a: a.deposit(lk.Money(0)), ValueError), (lambda lk, a: a.deposit(lk.Money(-5)), ValueError),
    (lambda lk, a: a.deposit(lk.Money(5, "EUR")), "mismatch"),
    (lambda lk, a: a.withdraw(5), TypeError), (lambda lk, a: a.withdraw(lk.Money(0)), ValueError), (lambda lk, a: a.withdraw(lk.Money(-5)), ValueError),
    (lambda lk, a: a.withdraw(lk.Money(5, "EUR")), "mismatch"),
])
def test_a_bad_amount_is_refused_and_changes_nothing(lk, call, exc):
    a = lk.Account("a"); a.deposit(usd(lk, 100))
    expected = lk.CurrencyMismatch if exc == "mismatch" else exc
    with pytest.raises(expected):
        call(lk, a)
    assert a.balance == usd(lk, 100) and len(a.history) == 1


def test_withdraw_cannot_go_below_zero_without_an_overdraft(lk):
    a = lk.Account("a"); a.deposit(usd(lk, 100))
    with pytest.raises(lk.InsufficientFunds):
        a.withdraw(usd(lk, 101))
    assert a.balance == usd(lk, 100) and len(a.history) == 1
    assert a.withdraw(usd(lk, 100)) == usd(lk, 0)


def test_withdraw_may_use_exactly_the_overdraft_and_no_more(lk):
    a = lk.Account("a", overdraft=usd(lk, 500)); a.deposit(usd(lk, 100))
    assert a.withdraw(usd(lk, 600)) == usd(lk, -500)
    with pytest.raises(lk.InsufficientFunds):
        a.withdraw(usd(lk, 1))
    assert a.balance == usd(lk, -500)


def test_account_repr_shows_owner_and_balance(lk):
    a = lk.Account("ann"); a.deposit(usd(lk, 1234))
    assert repr(a) == "Account(owner='ann', balance='12.34 USD')"
