# PY-M12 guided lab - A ledger whose objects cannot be broken from the outside

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`. No network, no account and no paid service: everything runs on your computer.

`starter/ledgerkit.py` is a small model of money, accounts, events and fees. The **names, the docstrings, the exceptions and the dataclass skeletons for the fee policies are given**; every body that raises `NotImplementedError` is yours. Each docstring is the specification and `checks/` holds the tests, one file per step. You will write value types, an account that owns its state, an event bus that does not leak subscribers, behaviour behind an interface, a registry and a ledger built by composition.

## Setup

```bash
cd courses/python-engineering/modules/PY-M12/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/ledgerkit.py`. Run one step with `python -m pytest checks/test_step_a_money.py` (and `b_account`, `c_bus`, `d_fees`, `e_registry`, `f_ledger`). When a step passes, read the lesson section named in the step heading again and write the answer to the question in `notes.md` (create it next to this file); a one- or two-sentence answer is enough, and a wrong answer written down is more useful than none.

## Step A - `Money`: a value type (LO2, LO3)

`Money` holds whole cents and a currency code. Turn the skeleton into `@dataclass(frozen=True, slots=True)` and fill in the methods: `__post_init__` (reject a `bool` as cents, even though `True` is an `int`; reject a currency that is not three capital ASCII letters), `parse` (strict: exactly two decimals, **ASCII digits only**, no spaces except the one before the currency; use `[0-9]` because `\d` also matches digits of other scripts), `__str__`, arithmetic in one currency, and ordering. Different currencies must raise `CurrencyMismatch` for `+`, `-`, `<`, `<=`, `>` and `>=`, but `==` across currencies is simply `False`. For anything that is not `Money` return `NotImplemented` instead of raising: Python then raises the `TypeError` for you and gives the other operand a chance.

Do **not** write `__eq__` or `__hash__`; the dataclass makes them consistent. Do not use `order=True`: it would compare `(cents, currency)` as a tuple and let `Money(1, "EUR") > Money(2, "USD")` pass. Run `python -m pytest checks/test_step_a_money.py`.

In `notes.md`: why would `order=True` have been a bug here (lesson section 4), and what would `{Money(1): "a"}[Money(1)]` do if `Money` were not frozen (section 5)?

## Step B - `Account`: state that belongs to the instance (LO1, LO3)

Implement `__init__`, the four read-only properties, `deposit`, `withdraw` and `__repr__`. Three rules carry the step:

1. **Per-instance state goes in `__init__`.** `history` is a list on each account. `Account.opened` is the one deliberate class attribute: increment it on the **class** (`Account.opened += 1`). Try `self.opened += 1` once, run the test `test_account_numbers_are_unique_and_the_counter_is_class_state`, and read the failure message: it is the bug of lesson section 2.
2. **Hand out copies, never the internals.** `history` returns a tuple, so a caller cannot change the account through it.
3. **A refused call changes nothing.** Validate first, then change the balance, then record the entry. `withdraw` may go exactly to the overdraft limit and not one cent below it.

Run `python -m pytest checks/test_step_b_account.py`.

In `notes.md`: what does `a.balance = Money(5)` do with a read-only property, and why is that better than a public attribute and a comment saying "do not change"?

## Step C - `EventBus`: observers without shared state (LO1, LO5)

`subscribe(handler)` returns a function that removes the subscription. **A bound method is stored through `weakref.WeakMethod`** so that the bus does not keep a subscriber alive; a plain function or lambda is stored normally (a weak reference to a lambda dies at once, and the lesson shows why for bound methods: section 9). `publish(event)` calls the live handlers in subscription order, collects the exceptions of the ones that fail and returns them as a tuple; it catches `Exception`, not `BaseException`. Two details are tested: a handler removed by an earlier handler is not called in that round, and a handler may subscribe another one without breaking the loop (iterate over a copy).

Run `python -m pytest checks/test_step_c_bus.py`.

In `notes.md`: what would two buses share if you had written `handlers = {}` in the class body (lesson section 2), and what does `bus.subscriber_count` show after a listener object is deleted?

## Step D - fee policies: behaviour behind a small interface (LO4, LO5)

`FeePolicy` is a `Protocol`: anything with `fee(amount) -> Money` qualifies, and none of the classes inherits from it. Implement `FlatFee.fee`, `PercentFee` (validation in `__post_init__`; the fee in **integer arithmetic**, rounded half up: `(cents * basis_points * 2 + 10_000) // 20_000`, never a float), `Capped` and `Combined`. `Combined` stores its policies as a **tuple** so that it stays hashable and a later change to the caller's list has no effect; in a frozen dataclass that needs `object.__setattr__(self, "policies", tuple(self.policies))` in `__post_init__` (lesson section 4).

Run `python -m pytest checks/test_step_d_fees.py`.

In `notes.md`: `isinstance(Confused(), FeePolicy)` is `True` for a class whose `fee` takes the wrong arguments. Why (lesson section 8), and which tool would catch it?

## Step E - a registry instead of an if ladder (LO5)

`register_policy(kind)` is a decorator that adds a factory to `_POLICIES` (a duplicate kind is a `ValueError`) and returns the function unchanged. `make_policy(spec)` builds a policy from a mapping like `{"kind": "capped", "inner": {...}, "cap": "5.00 USD"}`. The built-in kinds are already registered for you. Errors have exactly the types in the docstring; the subtle one: check the parameters with `inspect.signature(factory).bind(**params)` **before** calling the factory. If you call the factory inside `try/except TypeError` instead, a `TypeError` raised *inside* a valid factory (a `bool` for `basis_points`) is wrongly reported as "bad parameters". Never modify the caller's mapping.

Run `python -m pytest checks/test_step_e_registry.py`.

In `notes.md`: a colleague proposes `if kind == "flat": ... elif kind == "percent": ...`. Give two reasons the registry is better, and one situation where the ladder would be fine.

## Step F - `Ledger`: composition (LO4, LO5)

A `Ledger` **has** accounts, a policy and a bus; it inherits from nothing (a test asserts it). `transfer` is all-or-nothing: **check everything before changing anything**, then withdraw amount plus fee from the source, deposit the amount in the target, and publish a `Transfer` event. The failure modes are in the docstring; the order of the checks matters. Two of them are easy to forget and are tested: an amount that is zero or negative (the target's `deposit` would refuse it, but only after the source had already been charged), and a target account in a different currency (same problem). A handler that raises must not undo a transfer that has happened. Use `bus is None`, not `bus or EventBus()` (an object can be falsy without being `None`).

Run `python -m pytest checks/test_step_f_ledger.py`, then the whole suite with `python -m pytest`.

In `notes.md`: write the sentence that explains why `class Ledger(dict)` would let `ledger.update(...)` bypass every rule of `transfer` (lesson sections 6 and 7).

## When you are done

All checks pass and `notes.md` has six short answers. Then re-read your `Account` and `Ledger` and ask the four questions of lesson section 10 about each: equality and hash, immutability, isolation, refusal. The independent lab asks you to do the same on a design that has no starter code.

## What the checks do not tell you

They test behaviour, not design taste, and they cannot tell you that a name is confusing or that a class has two reasons to change. Read `solution/ledgerkit.py` only after your own version passes, and compare the *shape* of the two: where each keeps its state and what each hands out.
