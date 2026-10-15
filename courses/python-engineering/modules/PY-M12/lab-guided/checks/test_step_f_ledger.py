"""PY-M12 guided lab, step F (Ledger: composition). Run: python -m pytest checks/test_step_f_ledger.py"""
from __future__ import annotations

import pytest


def usd(lk, cents: int):
    return lk.Money(cents, "USD")


def make_ledger(lk, policy=None):
    ledger = lk.Ledger(policy or lk.FlatFee(usd(lk, 100)))
    ann, bob = ledger.open("ann"), ledger.open("bob")
    ann.deposit(usd(lk, 10_000))
    return ledger, ann, bob


def test_ledger_opens_and_finds_accounts(lk):
    ledger = lk.Ledger(lk.Combined())
    a = ledger.open("a", currency="EUR", overdraft=lk.Money(100, "EUR"))
    assert ledger.account(a.number) is a and a.balance == lk.Money(0, "EUR")
    with pytest.raises(KeyError):
        ledger.account(10**9)


def test_ledgers_do_not_share_accounts(lk):
    one, two = lk.Ledger(lk.Combined()), lk.Ledger(lk.Combined())
    a = one.open("a")
    with pytest.raises(KeyError):
        two.account(a.number)


def test_a_transfer_moves_the_money_and_the_source_pays_the_fee(lk):
    ledger, ann, bob = make_ledger(lk)
    event = ledger.transfer(ann.number, bob.number, usd(lk, 2_000))
    assert ann.balance == usd(lk, 7_900) and bob.balance == usd(lk, 2_000)
    assert event == lk.Transfer(ann.number, bob.number, usd(lk, 2_000), usd(lk, 100))


def test_a_transfer_publishes_one_event_after_it_has_happened(lk):
    ledger, ann, bob = make_ledger(lk)
    snapshots = []
    ledger.bus.subscribe(lambda e: snapshots.append((e, ann.balance, bob.balance)))
    ledger.transfer(ann.number, bob.number, usd(lk, 500))
    assert snapshots == [(lk.Transfer(ann.number, bob.number, usd(lk, 500), usd(lk, 100)), usd(lk, 9_400), usd(lk, 500))]


def test_a_failing_subscriber_does_not_undo_the_transfer_or_hide_it(lk):
    ledger, ann, bob = make_ledger(lk)

    def boom(e):
        raise RuntimeError("audit system down")

    ledger.bus.subscribe(boom)
    event = ledger.transfer(ann.number, bob.number, usd(lk, 500))
    assert event.amount == usd(lk, 500) and bob.balance == usd(lk, 500)


def test_a_ledger_can_share_a_bus_but_the_default_bus_is_private(lk):
    shared = lk.EventBus()
    one, two = lk.Ledger(lk.Combined(), shared), lk.Ledger(lk.Combined())
    assert one.bus is shared and two.bus is not shared and two.bus is not lk.Ledger(lk.Combined()).bus


def test_a_ledger_uses_the_bus_it_is_given_even_if_that_bus_is_falsy(lk):
    class QuietBus(lk.EventBus):
        def __len__(self):
            return 0                    # an empty-looking object is falsy; `bus or EventBus()` would replace it

    bus = QuietBus()
    assert lk.Ledger(lk.Combined(), bus).bus is bus


def test_a_transfer_that_cannot_be_afforded_changes_nothing_and_publishes_nothing(lk):
    ledger, ann, bob = make_ledger(lk)
    seen = []
    ledger.bus.subscribe(seen.append)
    with pytest.raises(lk.InsufficientFunds):
        ledger.transfer(ann.number, bob.number, usd(lk, 9_950))          # 9 950 + 100 fee > 10 000
    assert ann.balance == usd(lk, 10_000) and bob.balance == usd(lk, 0) and len(ann.history) == 1 and bob.history == () and seen == []


def test_the_fee_counts_when_checking_funds(lk):
    ledger, ann, bob = make_ledger(lk)
    assert ledger.transfer(ann.number, bob.number, usd(lk, 9_900)).fee == usd(lk, 100) and ann.balance == usd(lk, 0)


@pytest.mark.parametrize("what", ["same", "unknown_source", "unknown_target", "currency", "not_money", "zero", "negative", "fee_currency", "accounts_in_different_currencies"])
def test_every_bad_transfer_is_refused_before_anything_changes(lk, what):
    ledger, ann, bob = make_ledger(lk)
    seen = []
    ledger.bus.subscribe(seen.append)
    if what == "same":
        args, exc = (ann.number, ann.number, usd(lk, 100)), ValueError
    elif what == "unknown_source":
        args, exc = (10**9, bob.number, usd(lk, 100)), KeyError
    elif what == "unknown_target":
        args, exc = (ann.number, 10**9, usd(lk, 100)), KeyError
    elif what == "currency":
        args, exc = (ann.number, bob.number, lk.Money(100, "EUR")), lk.CurrencyMismatch
    elif what == "not_money":
        args, exc = (ann.number, bob.number, 100), TypeError
    elif what == "zero":
        args, exc = (ann.number, bob.number, usd(lk, 0)), ValueError
    elif what == "negative":
        args, exc = (ann.number, bob.number, usd(lk, -5)), ValueError
    elif what == "fee_currency":
        ledger = lk.Ledger(lk.FlatFee(lk.Money(1, "EUR")))
        ann, bob = ledger.open("ann"), ledger.open("bob")
        ann.deposit(usd(lk, 10_000))
        args, exc = (ann.number, bob.number, usd(lk, 100)), lk.CurrencyMismatch
    else:
        class NoFee:                                      # a policy that charges nothing in whatever currency it is asked about
            def fee(self, amount):
                return lk.Money(0, amount.currency)
        ledger = lk.Ledger(NoFee())
        ann, bob = ledger.open("ann"), ledger.open("bob", currency="EUR")
        ann.deposit(usd(lk, 10_000))
        args, exc = (ann.number, bob.number, usd(lk, 100)), lk.CurrencyMismatch      # the source could pay in USD, the target cannot receive USD: nothing may move
    with pytest.raises(exc):
        ledger.transfer(*args)
    assert ann.balance == usd(lk, 10_000) and bob.balance == lk.Money(0, bob.balance.currency) and len(ann.history) == 1 and bob.history == () and seen == []


def test_the_ledger_is_composed_not_inherited(lk):
    ledger = lk.Ledger(lk.Combined())
    assert lk.Ledger.__mro__ == (lk.Ledger, object), "a Ledger has a bus, accounts and a policy; it is not a dict, a list or an EventBus"
    assert not any(hasattr(ledger, name) for name in ("append", "subscribe", "update", "clear", "pop"))


def test_the_ledger_accepts_any_policy_with_a_fee_method(lk):
    class FreeOnFridays:
        def fee(self, amount):
            return lk.Money(0, amount.currency)
    ledger, ann, bob = make_ledger(lk, FreeOnFridays())
    assert ledger.transfer(ann.number, bob.number, usd(lk, 100)).fee == usd(lk, 0) and ann.balance == usd(lk, 9_900)
