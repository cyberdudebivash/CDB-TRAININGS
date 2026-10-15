# PY-M12 independent lab - A rule engine that alerts when a source misbehaves

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`; no network, account or paid service. **Prerequisite:** the guided lab (it shows every technique used here).

You are given **no solution and no step list**. `starter/rulekit.py` contains the names that the checks import, as empty stubs, and nothing else. Write the module from this specification. Ten published checks (`python -m pytest`) show the shape of the task; the instructors run a **hidden suite** of many more checks against your `rulekit.py`, built from the four questions of lesson section 10 (equality and hash, immutability, isolation, refusal). Passing the published checks is necessary, not sufficient. How you are graded is in `../assessment/rubric.yaml`.

## Setup

```bash
cd courses/python-engineering/modules/PY-M12/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/rulekit.py`. Standard library only (`dataclasses`, `enum`, `collections.abc`, `typing`).

## The task

A security tool receives **events** (a login failed, a file was deleted). A **rule** says "this kind of event, counted per source, reaching this threshold, is an alert". The engine counts matches per (rule, source) and raises each alert **once**, when the count reaches the threshold. Build the module below. Where this text says a class is a *value*, it must be immutable, comparable by content, hashable, and have a readable `repr`.

### `Severity` and `Matcher` (given)

`Severity` is an `IntEnum`: `LOW=1`, `MEDIUM=2`, `HIGH=3`, `CRITICAL=4`. `Matcher` is a `runtime_checkable` `Protocol` with `matches(event) -> bool`. Your matchers must satisfy it **without inheriting from it**, and any object with a `matches` method must work wherever a matcher is accepted.

### `FrozenMap`

A read-only mapping of text to text (a `collections.abc.Mapping`). Built from a mapping or an iterable of pairs (default empty); it **copies** its input, so later changes to the caller's dictionary have no effect. Keys and values must be `str` (`TypeError` otherwise). Iteration is in **sorted key order**. It is hashable, equal to another `FrozenMap` or to a plain `dict` with the same items, and its hash does not depend on the order the items were given. Item assignment and deletion raise `TypeError`, and it has no mutating methods. `repr` is `FrozenMap({'a': '1', 'b': '2'})` (sorted keys).

### `Event`

A value with **keyword-only** fields: `kind: str`, `source: str`, `severity: Severity = Severity.LOW`, `fields: FrozenMap` (default: empty). It has no per-instance `__dict__` (use slots).

- `kind` and `source` must be non-empty strings that are not only whitespace (`ValueError` otherwise, including for a non-string).
- `severity` accepts a `Severity` or an `int` from 1 to 4 and is stored as a `Severity`. Anything else that is an `int` outside 1 to 4 is a `ValueError`. A `bool`, a `float`, a `str` or `None` is a `TypeError` (remember that `True` is an `int`).
- `fields` accepts any mapping of text to text and is stored as a `FrozenMap` copy; a value that is not text is a `TypeError`.
- Equality and hash use **all** fields, and two events with the same fields given in a different order are equal.
- `dataclasses.replace(event, ...)` must validate again, so `Event` is a dataclass. Its `repr` is the dataclass one: `Event(kind='k', source='s', severity=<Severity.LOW: 1>, fields=FrozenMap({}))`.

### Matchers

Each matcher is a frozen, hashable value, and `matches(event)` returns a `bool`. The `repr` shows the class and its fields by name: `KindIs(kind='x')`, `FieldEquals(key='a', value='b')`. Assigning to an attribute of a matcher, a rule, an alert or an event raises `AttributeError` (a frozen dataclass does).

| Matcher | Fields | Matches when |
|---|---|---|
| `KindIs(kind)` | `kind` | `event.kind == kind` |
| `FieldEquals(key, value)` | `key`, `value` | the event has the field `key` **and** its value equals `value` (a missing key never matches, not even for `value == ""`) |
| `SeverityAtLeast(severity)` | `severity` | `event.severity >= severity`; the argument is validated and coerced like `Event.severity` |
| `AllOf(parts)` | `parts: tuple` | every part matches; with **no** parts it matches everything |
| `AnyOf(parts)` | `parts: tuple` | at least one part matches; with **no** parts it matches nothing |
| `Not(inner)` | `inner` | `inner` does not match |

`AllOf` and `AnyOf` accept any iterable (a list, a generator), store a **tuple**, and raise `TypeError` for a part that is not a matcher; `Not` does the same for its argument.

**Operators.** Every matcher supports `a & b` (an `AllOf`), `a | b` (an `AnyOf`) and `~a` (a `Not`). Chains **flatten**: `a & b & c`, `a & (b & c)` and `(a & b) & (c & d)` are equal to `AllOf((a, b, c))` and `AllOf((a, b, c, d))`, and the same holds for `|` and `AnyOf`; mixed operators nest (`(a & b) | c` is `AnyOf((AllOf((a, b)), c))`). `~~a` is **not** simplified: it equals `Not(Not(a))`. An operator never changes its operands, and a non-matcher on the other side (`a & 5`) is a `TypeError`. Operators also work with a matcher that is not one of yours, as long as it has a `matches` method. *Hint: one small, state-free helper class can give all the matchers their operators without any matcher inheriting from another.*

### `Rule` and `Alert`

`Rule(name, matcher, threshold=1)` is a frozen value. `name` must be a non-empty string that is not only whitespace (`ValueError`); `matcher` must have a `matches` method (`TypeError`); `threshold` must be an `int` that is not a `bool` (`TypeError`) and at least 1 (`ValueError`). `Alert(rule, source, count, event)` is a frozen value: the rule **name**, the source, the count reached, and the event that reached it.

### `RuleEngine`

A plain class; **every engine has its own rules, counts, subscribers and errors**, and nothing mutable lives on the class.

- `add(rule)`: `TypeError` for anything that is not a `Rule`; `ValueError` for a rule whose name is already present. `rules` is a **tuple** in insertion order.
- `process(event)`: `TypeError` unless `event` is an `Event`, with nothing changed. For each rule in order, ask its matcher. If it matches, increase the count for `(rule.name, event.source)`; if the count **now equals** the threshold, create an `Alert` (once per crossing, not on every later match). Return the alerts as a **new list**, in rule order. The engine keeps counts, not events.
- If a matcher raises an `Exception`, `process` does not raise: it records `(rule.name, exception)` in `errors`, treats the rule as not matching for that event, and carries on with the other rules. A `BaseException` (such as `KeyboardInterrupt`) is **not** caught.
- `subscribe(handler)` returns a function that removes the subscription (calling it twice is harmless). After the rules have been evaluated, every alert is passed to the subscribers: **alert by alert, and for each alert the subscribers in subscription order**. A subscriber that raises `Exception` does not stop the others; its error is recorded as `("handler", exception)`. A subscriber removed by an earlier subscriber during the same round is not called.
- `count(rule, source)` is the current count (0 if none). `counts()` returns a **copy** of all counts as `{(rule_name, source): n}`. `errors` is a **tuple** copy.
- `reset(source=None)` clears all counts, or only those of one source, so that rules can alert again; resetting an unknown source is harmless.

## Suggested order (not a step list)

Start with `FrozenMap` and `Event` (the values), then the matchers and the operator helper, then `Rule`/`Alert`, then the engine. Run the published checks after each part. When they pass, write `notes.md` (below) and check your design against the four questions of lesson section 10: for each class, what would a test for equality, immutability, isolation and refusal look like, and does your code pass it?

## What you hand in

1. `starter/rulekit.py`.
2. `notes.md` (half a page): which of your classes are frozen dataclasses, which are plain classes, and why; where the engine keeps state and what it hands out; one design decision you reconsidered, and why.

## Hints that are not solutions

- A frozen dataclass with `slots=True` cannot assign in `__post_init__`; lesson section 4 shows the one sanctioned way.
- `isinstance(x, SomeRuntimeProtocol)` checks only that the method name exists.
- Iterating over a dictionary while a callback may change it needs a copy.
- If two things must compare equal, they must hash equal; if a hash can change, the object cannot be a dictionary key.
