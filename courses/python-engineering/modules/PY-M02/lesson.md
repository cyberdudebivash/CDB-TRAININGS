---
id: PY-M02
title: "Functions, errors and testing with pytest"
course: COURSE-PY-ENG
level: 1
audience: "Developers, analysts and operations staff learning to write Python that other people can trust"
prerequisites:
  - "PY-M01 or equivalent: you can write a function, use lists, dictionaries and strings, and run a script"
  - "Python 3.11 or newer (the labs were executed on 3.11, 3.12 and 3.13; see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "A terminal and a text editor. No account, network access after installation, or cost is needed"
estimated_time_hours: {lesson: 2.5, guided_lab: 2.5, independent_lab: 3.0, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "supported 3.11-3.15, 3.10 ended 2026-10-01 (Python Developer's Guide, R-005)", pytest: "9.1.1 (PyPI, released 2026-06-19; registry snapshot of 2026-10-14)"}
last_verified: 2026-10-14
---

# PY-M02 - Functions, errors and testing with pytest

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Write unit tests with plain `assert` statements, run them with `python -m pytest` and read a failure report. |
| **LO2** | Cover valid, boundary and invalid inputs of a function in one parametrised test. |
| **LO3** | Assert that code raises the right exception, with the right message, using `pytest.raises`. |
| **LO4** | Explain why a mutable default argument shares state between calls and write a test that detects it. |
| **LO5** | Use surviving mutants to find and close gaps in your own test suite. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

A test suite is a promise that the code still does what you said it does. Two habits make that promise worthless: tests that only
ever check the happy path, and examples nobody ever ran. The 2025 handbook this module replaces contains many code listings; the audit could check
that they parse but did not execute any of them, and no chapter teaches test design (F-PYH-004). In this module **every `python run`, `python module` and `python test` block in
the lesson is executed by the repository's test suite**, so the examples you read are examples that ran.

You will practise on a deliberately defective module. Your tests are graded by *what they catch*, not by how many there are.

## 2. A function is a contract

Before you test a function, write down its contract: what it accepts, what it returns, and what it does when the input is wrong.
The contract is what your tests will check, so it must be precise enough to be wrong.

```python module=shipping
"""A small function with a precise contract."""


def parcel_fee(weight_kg: float) -> int:
    """Fee in cents. Up to and including 2 kg: 500. Above 2 kg and up to 10 kg: 500 plus 100 per started kg above 2.
    More than 10 kg, zero, negative or not a number: ValueError."""
    if not isinstance(weight_kg, (int, float)) or isinstance(weight_kg, bool) or not 0 < weight_kg <= 10:
        raise ValueError("weight must be above 0 and at most 10 kg")
    if weight_kg <= 2:
        return 500
    whole, rest = divmod(weight_kg - 2, 1)
    return 500 + 100 * (int(whole) + (1 if rest > 0 else 0))
```

The docstring names three boundaries: 2 kg, 10 kg and zero. Boundaries are where defects live, because a single character (`<` versus
`<=`) moves them.

## 3. Errors are part of the contract (LO3)

When input is wrong, a function can *return something odd* (`0`, `None`, `-1`) or *raise an exception*. Returning an odd value
looks harmless and spreads: the caller has to remember to check, and the first one who forgets turns a bad input into a wrong
answer. Raising makes the failure impossible to ignore.

```python run
def parse_count_quiet(text):
    try:
        return int(text)
    except Exception:          # swallows every error, including typos in this very function
        return 0


def parse_count_loud(text):
    return int(text)           # a bad input raises ValueError by itself


assert parse_count_quiet("seven") == 0        # a typo became a zero: the caller cannot tell
try:
    parse_count_loud("seven")
except ValueError as exc:
    assert "seven" in str(exc)
else:
    raise AssertionError("expected ValueError")
```

Rule of thumb: catch the *specific* exception you can handle, as close to its source as possible, and let everything else propagate.
A bare `except Exception:` that returns a default is the single most common way a defect hides from tests.

## 4. Your first tests (LO1)

pytest finds files named `test_*.py` (or `*_test.py`), collects functions named `test_*`, runs them and reports each `assert` that
is false, with the values on both sides. Use `python -m pytest` rather than bare `pytest`: it adds the current directory to the
import path, so `import shipping` finds your module without extra setup.

```python test
from shipping import parcel_fee


def test_a_light_parcel_pays_the_base_fee():
    assert parcel_fee(1) == 500


def test_each_started_kilogram_above_two_costs_100():
    assert parcel_fee(2.5) == 600
    assert parcel_fee(3) == 600
```

A good test name is a sentence about behaviour. When it fails, the name alone should tell you which promise broke.

## 5. One test, many cases (LO2)

The two tests above repeat themselves. `pytest.mark.parametrize` turns a table of cases into separate tests, each reported
individually, so one failing row does not hide the others.

```python test
import pytest

from shipping import parcel_fee


@pytest.mark.parametrize(
    "weight, fee",
    [
        (0.1, 500),    # smallest accepted weight region
        (2, 500),      # boundary: 2 kg is still the base fee
        (2.01, 600),   # just above the boundary: one started kilogram
        (3, 600),
        (3.5, 700),
        (10, 1300),    # boundary: 10 kg is accepted
    ],
)
def test_parcel_fee_table(weight, fee):
    assert parcel_fee(weight) == fee
```

Choose rows with a method, not by feel. For every boundary in the contract test **the value on each side and the value on the
boundary itself**. Add one row per *kind* of invalid input as well (next section).

## 6. Testing that the right thing fails (LO3)

An error path is behaviour, so it needs a test. `pytest.raises` passes only if the block raises the stated exception; `match=` checks
the message with a regular-expression search, which stops a test from passing because of an unrelated error.

```python test
import pytest

from shipping import parcel_fee


@pytest.mark.parametrize("weight", [0, -1, 10.01, 100, "3", None, True])
def test_parcel_fee_rejects_invalid_weights(weight):
    with pytest.raises(ValueError, match="above 0 and at most 10"):
        parcel_fee(weight)
```

Notice `True`: in Python `True == 1`, so a function that does not guard against booleans accepts it. Contracts are full of such
corners; listing them in a table is cheap.

## 7. The shared-state trap (LO4)

A default argument is evaluated **once**, when the function is defined, not on every call. If the default is a list or a dictionary,
every call that omits the argument shares the same object.

```python run
def add_tag(tag, tags=[]):
    tags.append(tag)
    return tags


first = add_tag("a")
second = add_tag("b")
assert second == ["a", "b"]          # the second caller sees the first caller's data
assert first is second               # it is literally the same list


def add_tag_fixed(tag, tags=None):
    if tags is None:
        tags = []
    tags.append(tag)
    return tags


assert add_tag_fixed("a") == ["a"]
assert add_tag_fixed("b") == ["b"]
```

The defect is invisible to a test that calls the function once. The test that finds it makes **two independent calls** and checks that the
second does not see the first.

## 8. Are your tests any good? Mutation thinking (LO5)

A passing suite proves nothing if it would also pass on broken code. Check by breaking the code on purpose: change `>=` to `>`, drop a
`raise`, swap an operator. Each such change is a *mutant*. If your tests still pass, the mutant **survived**: you have found behaviour
that nothing protects.

The labs ship a small tool that does this for you (`labs/_tools/mutation_check.py`). It applies a list of one-line mutations to the correct module
and reports which ones your tests detect. Treat a survivor as a question - *which test would have caught this?* - and write that
test. Do not chase a perfect score blindly: a mutant that changes behaviour the contract leaves open is not a defect, and deciding that is part of the skill.

## 9. What changed since the 2025 handbook

Verified on 2026-10-14 (probes are in `docs/research/data/api_probes_2026-10-14.json`; the register is `docs/research/research_register.yaml`):

- **Supported Python versions are 3.11 to 3.15.** Python 3.10 reached end of life on 2026-10-01 and 3.9 on 2025-10-31 (R-005). Do not
  teach or deploy a baseline of "3.10+" any more.
- **`pytest.warns(None)` no longer works.** On pytest 9.1.1 it raises `TypeError: exceptions must be derived from Warning`. Use
  `pytest.warns(SomeWarning)`, or the `warnings` module's recorder, to assert that nothing is emitted (probe `pytest-removed-apis`).
- **`@pytest.yield_fixture` still exists but is superseded.** On 9.1.1 the attribute is present; write `@pytest.fixture` with `yield`.
- **`unittest.makeSuite` is gone.** It is absent on CPython 3.13.16 (probe `cpython-removed-stdlib`); use `unittest.TestLoader().loadTestsFromTestCase`
  or run the tests with pytest.
- **`datetime.utcnow()` warns on 3.12+.** It emits `DeprecationWarning`; use `datetime.now(timezone.utc)` (same probe).

## 10. Common misconceptions

| Misconception | Reality |
|---|---|
| "100 % coverage means the code is well tested." | Coverage counts lines that *ran*, not behaviour that was *checked*. A test with no assertion covers a line and protects nothing. Mutation survivors show the difference. |
| "A test that never fails is a good test." | A test that cannot fail is a comment. Prove each test can fail by breaking the code once. |
| "`except Exception: return default` makes code robust." | It makes defects silent. Catch what you can handle; let the rest raise. |
| "Default arguments are evaluated on every call." | Once, at definition time. Use `None` and create the object inside. |
| "Tests should repeat the implementation." | Tests state the contract in examples. A test that recomputes the answer with the same formula shares the implementation's mistakes. |

## 11. Practice and assessment

| Step | What | Where |
|---|---|---|
| Guided lab (LO1-LO5) | Write tests for `orderkit` until your tests catch three seeded defects and the stretch mutants | `lab-guided/README.md` |
| Independent lab (LO2, LO3, LO5) | Write a test suite for `splitkit` from its specification; it is graded on hidden mutants | `lab-independent/README.md` |
| Knowledge check | 8 questions tied to the outcomes (answers are held by instructors) | `assessment/quiz.md` |
| Rubric | Published criteria for the independent lab | `assessment/rubric.yaml` |

## 12. Summary

- Write the contract first, then test the boundary values on each side, plus one row per kind of invalid input.
- Errors are behaviour: raise a specific exception and test it with `pytest.raises(..., match=...)`.
- Swallowing exceptions and mutable default arguments are two classic defects that single-call tests miss.
- Judge a suite by the mutants it kills, not by how many tests it has or how many lines it covers.

## References

- Python Developer's Guide, *Status of Python versions* (research register R-005, verified 2026-10-14).
- Registry snapshot of tool versions as of 2026-10-14 (R-045): pytest 9.1.1.
- Executed probes: `pytest-removed-apis`, `cpython-removed-stdlib` (docs/research/data/api_probes_2026-10-14.json).
- Findings addressed: F-PYH-004 (listings parsed but not executed; no test-design chapter), F-PYH-007 (assessment by recall questions only).
