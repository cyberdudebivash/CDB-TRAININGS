"""ledgerkit - a small model of money, accounts, events and fees (PY-M12 guided lab).

Public reference solution. The starter has the same names; the docstrings are the specification and checks/test_ledgerkit.py is the test suite.
"""
from __future__ import annotations

import inspect
import re
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

_CURRENCY = re.compile(r"[A-Z]{3}")
_AMOUNT = re.compile(r"(-?)([0-9]+)\.([0-9]{2}) ([A-Z]{3})")


class CurrencyMismatch(ValueError):
    """Two amounts in different currencies were added, subtracted or ordered."""


class InsufficientFunds(Exception):
    """A withdrawal would take an account below its overdraft limit."""


# ---------------------------------------------------------------------------------------------------- step A: a value type
@dataclass(frozen=True, slots=True)
class Money:
    """An amount in whole cents of one currency. A value: immutable, compared by content, usable as a dict key.

    cents      an int (not a bool); may be negative
    currency   exactly three capital ASCII letters
    """

    cents: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        if isinstance(self.cents, bool) or not isinstance(self.cents, int):
            raise TypeError(f"cents must be an int, not {type(self.cents).__name__}")
        if not isinstance(self.currency, str) or not _CURRENCY.fullmatch(self.currency):
            raise ValueError(f"currency must be three capital ASCII letters, got {self.currency!r}")

    @classmethod
    def parse(cls, text: str) -> "Money":
        """'12.34 USD' -> Money(1234, 'USD'); '-0.05 EUR' -> Money(-5, 'EUR'). Exactly two decimals, ASCII digits only, one space, no other text."""
        match = _AMOUNT.fullmatch(text) if isinstance(text, str) else None
        if match is None:
            raise ValueError(f"not an amount like '12.34 USD': {text!r}")
        sign, whole, fraction, currency = match.groups()
        cents = int(whole) * 100 + int(fraction)
        return cls(-cents if sign else cents, currency)

    def __str__(self) -> str:
        whole, fraction = divmod(abs(self.cents), 100)
        return f"{'-' if self.cents < 0 else ''}{whole}.{fraction:02d} {self.currency}"

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatch(f"{self.currency} and {other.currency} cannot be combined")

    def __add__(self, other: object) -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other: object) -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.cents - other.cents, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.cents, self.currency)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return self.cents < other.cents

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return self.cents <= other.cents

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return self.cents > other.cents

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return self.cents >= other.cents


# ---------------------------------------------------------------------------------------------------- step B: state that belongs to the instance
@dataclass(frozen=True, slots=True)
class Entry:
    """One line of an account's history."""

    kind: str                 # "deposit" or "withdraw"
    amount: Money
    balance_after: Money


class Account:
    """A money account. Instance state (owner, balance, history) lives on the instance; `opened` is class state on purpose."""

    opened: ClassVar[int] = 0     # how many accounts have ever been created

    def __init__(self, owner: str, *, currency: str = "USD", overdraft: Money | None = None) -> None:
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("owner must be a non-empty string")
        zero = Money(0, currency)
        overdraft = zero if overdraft is None else overdraft
        if overdraft.currency != currency:
            raise CurrencyMismatch("the overdraft limit must be in the account's currency")
        if overdraft.cents < 0:
            raise ValueError("the overdraft limit must not be negative")
        self._owner = owner.strip()
        self._balance = zero
        self._overdraft = overdraft
        self._history: list[Entry] = []
        Account.opened += 1               # the class, not self: `self.opened += 1` would create an instance attribute and leave the counter at 0
        self._number = Account.opened

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def number(self) -> int:
        return self._number

    @property
    def balance(self) -> Money:
        return self._balance

    @property
    def history(self) -> tuple[Entry, ...]:
        return tuple(self._history)           # a copy: callers cannot change the account through it

    def _check_amount(self, amount: Money) -> None:
        if not isinstance(amount, Money):
            raise TypeError(f"amount must be Money, not {type(amount).__name__}")
        if amount.currency != self._balance.currency:
            raise CurrencyMismatch(f"account is in {self._balance.currency}, amount is in {amount.currency}")
        if amount.cents <= 0:
            raise ValueError("amount must be positive")

    def deposit(self, amount: Money) -> Money:
        """Add `amount`; return the new balance. TypeError / CurrencyMismatch / ValueError for a bad amount, with the account unchanged."""
        self._check_amount(amount)
        self._balance = self._balance + amount
        self._history.append(Entry("deposit", amount, self._balance))
        return self._balance

    def withdraw(self, amount: Money) -> Money:
        """Subtract `amount`; return the new balance. InsufficientFunds if the balance would drop below minus the overdraft limit; the account is then unchanged."""
        self._check_amount(amount)
        after = self._balance - amount
        if after < -self._overdraft:
            raise InsufficientFunds(f"balance {self._balance} with overdraft {self._overdraft} cannot cover {amount}")
        self._balance = after
        self._history.append(Entry("withdraw", amount, after))
        return after

    def __repr__(self) -> str:
        return f"Account(owner={self._owner!r}, balance={str(self._balance)!r})"


# ---------------------------------------------------------------------------------------------------- step C: observers without shared state
class EventBus:
    """Calls subscribed handlers with each published event. Every bus has its own subscribers."""

    def __init__(self) -> None:
        self._handlers: dict[object, Callable[[], Callable[[object], object] | None]] = {}

    def subscribe(self, handler: Callable[[object], object]) -> Callable[[], None]:
        """Register `handler`; return a function that removes it again (calling it twice is harmless).

        A bound method is held weakly (weakref.WeakMethod), so a subscriber that is garbage collected stops receiving events and the bus does not keep it alive.
        Plain functions and lambdas are held normally.
        """
        token = object()
        if inspect.ismethod(handler):
            self._handlers[token] = weakref.WeakMethod(handler)
        else:
            self._handlers[token] = lambda handler=handler: handler

        def unsubscribe() -> None:
            self._handlers.pop(token, None)

        return unsubscribe

    @property
    def subscriber_count(self) -> int:
        """Live subscribers only."""
        return sum(1 for ref in self._handlers.values() if ref() is not None)

    def publish(self, event: object) -> tuple[Exception, ...]:
        """Call every live handler in subscription order. A handler that raises Exception does not stop the others; return the exceptions (empty tuple if none).

        Handlers removed while publishing (by an earlier handler) are not called. Dead weak subscribers are dropped. BaseException (KeyboardInterrupt, ...) is not caught.
        """
        errors: list[Exception] = []
        for token, ref in list(self._handlers.items()):
            if token not in self._handlers:
                continue
            handler = ref()
            if handler is None:
                self._handlers.pop(token, None)
                continue
            try:
                handler(event)
            except Exception as exc:
                errors.append(exc)
        return tuple(errors)


# ---------------------------------------------------------------------------------------------------- step D: behaviour behind a small interface
@runtime_checkable
class FeePolicy(Protocol):
    """Anything with `fee(amount) -> Money` is a fee policy; no base class is needed."""

    def fee(self, amount: Money) -> Money: ...


@dataclass(frozen=True)
class FlatFee:
    """The same charge for every transfer. CurrencyMismatch if the amount is in another currency."""

    charge: Money

    def fee(self, amount: Money) -> Money:
        if amount.currency != self.charge.currency:
            raise CurrencyMismatch(f"fee is in {self.charge.currency}, amount is in {amount.currency}")
        return self.charge


@dataclass(frozen=True)
class PercentFee:
    """`basis_points` hundredths of a percent of the amount (150 = 1.5 %), rounded half up to whole cents using integers only (no float).

    basis_points  an int (not a bool) from 0 to 10000
    """

    basis_points: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        if isinstance(self.basis_points, bool) or not isinstance(self.basis_points, int):
            raise TypeError("basis_points must be an int")
        if not 0 <= self.basis_points <= 10_000:
            raise ValueError("basis_points must be between 0 and 10000")
        Money(0, self.currency)              # validates the currency

    def fee(self, amount: Money) -> Money:
        if amount.currency != self.currency:
            raise CurrencyMismatch(f"fee is in {self.currency}, amount is in {amount.currency}")
        if amount.cents < 0:
            raise ValueError("the amount must not be negative")
        return Money((amount.cents * self.basis_points * 2 + 10_000) // 20_000, self.currency)


@dataclass(frozen=True)
class Capped:
    """The fee of `inner`, but never more than `cap`."""

    inner: FeePolicy
    cap: Money

    def fee(self, amount: Money) -> Money:
        charge = self.inner.fee(amount)
        return charge if charge <= self.cap else self.cap


@dataclass(frozen=True)
class Combined:
    """The sum of the fees of several policies (zero if there are none). `policies` may be passed as any iterable; it is stored as a tuple so the object stays hashable."""

    policies: tuple[FeePolicy, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "policies", tuple(self.policies))      # the one sanctioned way to set a field of a frozen dataclass in __post_init__

    def fee(self, amount: Money) -> Money:
        total = Money(0, amount.currency)
        for policy in self.policies:
            total = total + policy.fee(amount)
        return total


# ---------------------------------------------------------------------------------------------------- step E: a registry instead of an if/elif ladder
_POLICIES: dict[str, Callable[..., FeePolicy]] = {}


def register_policy(kind: str) -> Callable[[Callable[..., FeePolicy]], Callable[..., FeePolicy]]:
    """Decorator: make a factory available to `make_policy` under `kind`. Registering a kind twice is a ValueError."""

    def decorator(factory: Callable[..., FeePolicy]) -> Callable[..., FeePolicy]:
        if kind in _POLICIES:
            raise ValueError(f"policy kind already registered: {kind!r}")
        _POLICIES[kind] = factory
        return factory

    return decorator


def _flat(*, amount: str) -> FeePolicy:
    return FlatFee(Money.parse(amount))


def _percent(*, basis_points: int, currency: str = "USD") -> FeePolicy:
    return PercentFee(basis_points, currency)


def _capped(*, inner: Mapping[str, object], cap: str) -> FeePolicy:
    return Capped(make_policy(inner), Money.parse(cap))


def _combined(*, policies: list[Mapping[str, object]]) -> FeePolicy:
    return Combined(tuple(make_policy(p) for p in policies))


_POLICIES.update({"flat": _flat, "percent": _percent, "capped": _capped, "combined": _combined})     # the built-in kinds; `register_policy` adds more


def make_policy(spec: Mapping[str, object]) -> FeePolicy:
    """Build a policy from a mapping such as {"kind": "percent", "basis_points": 150}.

    TypeError if `spec` is not a Mapping; ValueError if it has no "kind", the kind is unknown, a parameter is missing or unexpected.
    The mapping is never modified.
    """
    if not isinstance(spec, Mapping):
        raise TypeError(f"a policy spec must be a mapping, not {type(spec).__name__}")
    if "kind" not in spec:
        raise ValueError("a policy spec needs a 'kind'")
    kind = spec["kind"]
    factory = _POLICIES.get(kind) if isinstance(kind, str) else None
    if factory is None:
        raise ValueError(f"unknown policy kind: {kind!r}")
    params = {key: value for key, value in spec.items() if key != "kind"}
    try:
        inspect.signature(factory).bind(**params)
    except TypeError as exc:
        raise ValueError(f"bad parameters for policy {kind!r}: {exc}") from None
    return factory(**params)


# ---------------------------------------------------------------------------------------------------- step F: composition
@dataclass(frozen=True, slots=True)
class Transfer:
    """The event published after a successful transfer."""

    source: int
    target: int
    amount: Money
    fee: Money


class Ledger:
    """Accounts, a fee policy and an event bus working together. It *has* these parts; it is not a kind of dict or list."""

    def __init__(self, policy: FeePolicy, bus: EventBus | None = None) -> None:
        self._policy = policy
        self._bus = EventBus() if bus is None else bus
        self._accounts: dict[int, Account] = {}

    @property
    def bus(self) -> EventBus:
        return self._bus

    def open(self, owner: str, *, currency: str = "USD", overdraft: Money | None = None) -> Account:
        account = Account(owner, currency=currency, overdraft=overdraft)
        self._accounts[account.number] = account
        return account

    def account(self, number: int) -> Account:
        """The account with this number; KeyError if this ledger has no such account."""
        return self._accounts[number]

    def transfer(self, source: int, target: int, amount: Money) -> Transfer:
        """Move `amount` from one account to another; the *source* also pays the fee. All-or-nothing, then publish a Transfer event.

        Everything that can fail is checked before anything changes: unknown accounts (KeyError), the same account on both sides (ValueError), a currency that is not
        the target's (CurrencyMismatch), a bad amount (not Money, zero or negative), and insufficient funds for amount plus fee (InsufficientFunds). A handler that raises does not undo the transfer.
        """
        src, dst = self.account(source), self.account(target)
        if src is dst:
            raise ValueError("cannot transfer to the same account")
        if not isinstance(amount, Money):
            raise TypeError(f"amount must be Money, not {type(amount).__name__}")
        if amount.cents <= 0:
            raise ValueError("amount must be positive")      # deposit() would refuse it, but only after the source had been charged
        if dst.balance.currency != amount.currency:
            raise CurrencyMismatch(f"target account is in {dst.balance.currency}, amount is in {amount.currency}")
        fee = self._policy.fee(amount)
        src.withdraw(amount + fee)
        dst.deposit(amount)
        event = Transfer(source, target, amount, fee)
        self._bus.publish(event)
        return event
