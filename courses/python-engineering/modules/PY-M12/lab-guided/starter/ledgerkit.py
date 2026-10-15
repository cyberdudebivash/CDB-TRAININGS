"""ledgerkit - a small model of money, accounts, events and fees (PY-M12 guided lab).

Six steps (A to F, see README.md). The names, the docstrings and the exceptions are given; the bodies that raise NotImplementedError are yours.
Every docstring is the specification and checks/test_ledgerkit.py is the test suite: `python -m pytest -k money` runs step A, `-k account` step B, and so on.
Edit only this file.
"""
from __future__ import annotations

import inspect
import re
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

_CURRENCY = re.compile(r"[A-Z]{3}")
_AMOUNT = re.compile(r"(-?)([0-9]+)\.([0-9]{2}) ([A-Z]{3})")          # for Money.parse; note [0-9], not \d (\d also matches digits of other scripts)


class CurrencyMismatch(ValueError):
    """Two amounts in different currencies were added, subtracted or ordered."""


class InsufficientFunds(Exception):
    """A withdrawal would take an account below its overdraft limit."""


# ---------------------------------------------------------------------------------------------------- step A: a value type
class Money:           # step A: turn this into a frozen dataclass with __slots__ (decorator arguments!), then implement the methods
    """An amount in whole cents of one currency. A value: immutable, compared by content, usable as a dict key.

    cents      an int (not a bool); may be negative
    currency   exactly three capital ASCII letters
    Equality and hash come from the dataclass; do not write __eq__ or __hash__ yourself. The instance has no __dict__.
    """

    cents: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        """TypeError if cents is not an int or is a bool; ValueError if the currency is not three capital ASCII letters (or not text)."""
        raise NotImplementedError("step A")

    @classmethod
    def parse(cls, text: str) -> "Money":
        """'12.34 USD' -> Money(1234, 'USD'); '-0.05 EUR' -> Money(-5, 'EUR'). Exactly two decimals, ASCII digits only, one space, no other text. ValueError otherwise (also for non-text)."""
        raise NotImplementedError("step A")

    def __str__(self) -> str:
        """'12.34 USD', '0.05 USD', '-0.05 USD': two decimals, a minus sign for negative amounts."""
        raise NotImplementedError("step A")

    def __add__(self, other: object) -> "Money":
        """Sum in the same currency. CurrencyMismatch for another currency. For anything that is not Money return NotImplemented (Python then raises TypeError)."""
        raise NotImplementedError("step A")

    def __sub__(self, other: object) -> "Money":
        """Difference in the same currency; same rules as __add__."""
        raise NotImplementedError("step A")

    def __neg__(self) -> "Money":
        raise NotImplementedError("step A")

    def __lt__(self, other: object) -> bool:
        """Ordering by cents within one currency; CurrencyMismatch across currencies; NotImplemented for non-Money. Same for __le__, __gt__ and __ge__."""
        raise NotImplementedError("step A")

    def __le__(self, other: object) -> bool:
        raise NotImplementedError("step A")

    def __gt__(self, other: object) -> bool:
        raise NotImplementedError("step A")

    def __ge__(self, other: object) -> bool:
        raise NotImplementedError("step A")


# ---------------------------------------------------------------------------------------------------- step B: state that belongs to the instance
@dataclass(frozen=True, slots=True)
class Entry:
    """One line of an account's history (given)."""

    kind: str                 # "deposit" or "withdraw"
    amount: Money
    balance_after: Money


class Account:
    """A money account. Instance state (owner, balance, history) lives on the instance; `opened` is class state on purpose."""

    opened: ClassVar[int] = 0     # how many accounts have ever been created

    def __init__(self, owner: str, *, currency: str = "USD", overdraft: Money | None = None) -> None:
        """ValueError if owner is not a non-empty string (surrounding spaces are removed). The balance starts at zero in `currency`.

        `overdraft` is how far below zero the balance may go (default: zero). CurrencyMismatch if it is in another currency; ValueError if it is negative.
        Count the account in Account.opened and give it that count as its `number` (1 for the first account of the process, 2 for the next, ...).
        """
        raise NotImplementedError("step B")

    # Read-only properties (setting them must raise AttributeError): owner, number, balance, history.
    # `history` returns a tuple of Entry values that is a copy: the caller cannot change the account through it.
    @property
    def owner(self) -> str:
        raise NotImplementedError("step B")

    @property
    def number(self) -> int:
        raise NotImplementedError("step B")

    @property
    def balance(self) -> Money:
        raise NotImplementedError("step B")

    @property
    def history(self) -> tuple[Entry, ...]:
        raise NotImplementedError("step B")

    def deposit(self, amount: Money) -> Money:
        """Add `amount`; return the new balance and record Entry("deposit", amount, new_balance).

        TypeError if `amount` is not Money; CurrencyMismatch if it is in another currency than the account; ValueError if it is not positive. A refused call changes nothing.
        """
        raise NotImplementedError("step B")

    def withdraw(self, amount: Money) -> Money:
        """Subtract `amount`; return the new balance and record Entry("withdraw", amount, new_balance). Same refusals as deposit.

        InsufficientFunds if the balance would drop below minus the overdraft limit; the account is then unchanged. Dropping to exactly the limit is allowed.
        """
        raise NotImplementedError("step B")

    def __repr__(self) -> str:
        """Account(owner='ann', balance='12.34 USD')"""
        raise NotImplementedError("step B")


# ---------------------------------------------------------------------------------------------------- step C: observers without shared state
class EventBus:
    """Calls subscribed handlers with each published event. Every bus has its own subscribers."""

    def __init__(self) -> None:
        raise NotImplementedError("step C")

    def subscribe(self, handler: Callable[[object], object]) -> Callable[[], None]:
        """Register `handler`; return a function that removes it again (calling it twice is harmless; subscribing the same function twice makes two subscriptions).

        A bound method is held weakly (weakref.WeakMethod), so a subscriber that is garbage collected stops receiving events and the bus does not keep it alive.
        Plain functions and lambdas are held normally (a weak reference to a lambda would die at once).
        """
        raise NotImplementedError("step C")

    @property
    def subscriber_count(self) -> int:
        """Live subscribers only."""
        raise NotImplementedError("step C")

    def publish(self, event: object) -> tuple[Exception, ...]:
        """Call every live handler in subscription order. A handler that raises Exception does not stop the others; return the exceptions (empty tuple if none).

        A handler removed while publishing (by an earlier handler) is not called. A handler may subscribe another handler while publishing; the new one starts with the next event.
        Dead weak subscribers are dropped. BaseException (KeyboardInterrupt, ...) is not caught.
        """
        raise NotImplementedError("step C")


# ---------------------------------------------------------------------------------------------------- step D: behaviour behind a small interface
@runtime_checkable
class FeePolicy(Protocol):
    """Anything with `fee(amount) -> Money` is a fee policy; no base class is needed (given)."""

    def fee(self, amount: Money) -> Money: ...


@dataclass(frozen=True)
class FlatFee:
    """The same charge for every transfer. CurrencyMismatch if the amount is in another currency than the charge."""

    charge: Money

    def fee(self, amount: Money) -> Money:
        raise NotImplementedError("step D")


@dataclass(frozen=True)
class PercentFee:
    """`basis_points` hundredths of a percent of the amount (150 = 1.5 %), rounded half up to whole cents using integers only (no float).

    basis_points  an int (not a bool) from 0 to 10000; TypeError for other types, ValueError outside the range
    currency      validated like Money's (ValueError)
    fee(): CurrencyMismatch for an amount in another currency; ValueError for a negative amount.
    """

    basis_points: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        raise NotImplementedError("step D")

    def fee(self, amount: Money) -> Money:
        raise NotImplementedError("step D")


@dataclass(frozen=True)
class Capped:
    """The fee of `inner`, but never more than `cap`. `inner` may be any object with a fee() method."""

    inner: FeePolicy
    cap: Money

    def fee(self, amount: Money) -> Money:
        raise NotImplementedError("step D")


@dataclass(frozen=True)
class Combined:
    """The sum of the fees of several policies, in the currency of the amount (zero if there are none).

    `policies` may be passed as any iterable; store it as a tuple so that the object stays hashable and later changes to the caller's list have no effect.
    (A frozen dataclass cannot assign in __post_init__ with `self.policies = ...`; the documented way is object.__setattr__.)
    """

    policies: tuple[FeePolicy, ...] = ()

    def __post_init__(self) -> None:
        raise NotImplementedError("step D")

    def fee(self, amount: Money) -> Money:
        raise NotImplementedError("step D")


# ---------------------------------------------------------------------------------------------------- step E: a registry instead of an if/elif ladder
_POLICIES: dict[str, Callable[..., FeePolicy]] = {}


def register_policy(kind: str) -> Callable[[Callable[..., FeePolicy]], Callable[..., FeePolicy]]:
    """Decorator: make a factory available to `make_policy` under `kind`; the decorated function is returned unchanged. Registering a kind twice is a ValueError."""
    raise NotImplementedError("step E")


def _flat(*, amount: str) -> FeePolicy:
    return FlatFee(Money.parse(amount))


def _percent(*, basis_points: int, currency: str = "USD") -> FeePolicy:
    return PercentFee(basis_points, currency)


def _capped(*, inner: Mapping[str, object], cap: str) -> FeePolicy:
    return Capped(make_policy(inner), Money.parse(cap))


def _combined(*, policies: list[Mapping[str, object]]) -> FeePolicy:
    return Combined(tuple(make_policy(p) for p in policies))


_POLICIES.update({"flat": _flat, "percent": _percent, "capped": _capped, "combined": _combined})     # the built-in kinds (given)


def make_policy(spec: Mapping[str, object]) -> FeePolicy:
    """Build a policy from a mapping such as {"kind": "percent", "basis_points": 150}; the other keys are passed to the factory of that kind as keyword arguments.

    TypeError if `spec` is not a Mapping. ValueError if it has no "kind", the kind is unknown (or not a string), or a parameter is missing or unexpected
    (check that with inspect.signature(factory).bind(**params) *before* calling the factory, so that a TypeError raised *inside* the factory is not mistaken for it).
    The mapping is never modified.
    """
    raise NotImplementedError("step E")


# ---------------------------------------------------------------------------------------------------- step F: composition
@dataclass(frozen=True, slots=True)
class Transfer:
    """The event published after a successful transfer (given)."""

    source: int
    target: int
    amount: Money
    fee: Money


class Ledger:
    """Accounts, a fee policy and an event bus working together. It *has* these parts; it is not a kind of dict or list."""

    def __init__(self, policy: FeePolicy, bus: EventBus | None = None) -> None:
        """Keep the policy; use `bus` if given, otherwise create a new EventBus of its own (test `is None`, not truthiness)."""
        raise NotImplementedError("step F")

    @property
    def bus(self) -> EventBus:
        raise NotImplementedError("step F")

    def open(self, owner: str, *, currency: str = "USD", overdraft: Money | None = None) -> Account:
        """Create an Account, remember it under its number, return it."""
        raise NotImplementedError("step F")

    def account(self, number: int) -> Account:
        """The account with this number; KeyError if this ledger has no such account."""
        raise NotImplementedError("step F")

    def transfer(self, source: int, target: int, amount: Money) -> Transfer:
        """Move `amount` from one account to another; the *source* also pays the fee of the policy. All-or-nothing, then publish a Transfer event.

        Everything that can fail is checked before anything changes: unknown accounts (KeyError), the same account on both sides (ValueError), an amount that is not Money
        (TypeError) or not positive (ValueError), a currency that is not the target account's (CurrencyMismatch), a fee in another currency (CurrencyMismatch) and insufficient
        funds for amount plus fee (InsufficientFunds). A handler that raises does not undo the transfer. Return the Transfer event.
        """
        raise NotImplementedError("step F")
