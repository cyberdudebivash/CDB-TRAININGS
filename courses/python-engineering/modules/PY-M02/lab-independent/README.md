# PY-M02 independent lab - Test `splitkit` from its specification

**Time:** about 3 hours  |  **Outcomes:** LO2, LO3, LO5  |  **Graded by:** automated mutant detection plus a reviewer rubric (`../assessment/rubric.yaml`)

`starter/splitkit.py` is **correct**. Someone will later change it. Your job is to write a test suite that would catch the damage. You get no list of defects and no reference tests.

## Specification

**`parse_amount(text) -> Decimal`** - parses money text into a `Decimal` with exactly two decimal places.
Accepted: ASCII digits with an optional single dot followed by one or two ASCII digits; surrounding whitespace is ignored (`"12"`, `"12.5"`, `" 12.50 "`).
Rejected with `ValueError("invalid amount")`: empty or blank text, a sign, a thousands separator, a bare dot, `"5."`, `".5"`, more than two decimals, non-ASCII digits, any other character.

**`split_bill(total, people) -> list[Decimal]`** - splits `total` (a `Decimal` that is a whole number of cents) between `people` people. All shares add up to exactly `total`.
Everyone pays the same whole number of cents, except that the **first** `cents % people` people pay one cent more. `ValueError` if `people < 1`, `total < 0`, or `total` has a fraction of a cent.

**`add_service_charge(total, percent) -> Decimal`** - adds `percent` (0 to 100 inclusive) to `total` and rounds **half-up** to whole cents. `ValueError` if `percent` is outside 0-100.

## Setup and running

```bash
cd courses/python-engineering/modules/PY-M02/lab-independent
python -m venv .venv && . .venv/bin/activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest            # runs student_tests/ against starter/
```

Put your tests in `student_tests/test_splitkit.py`.

## What you hand in

1. `student_tests/` - your test suite. It must pass on `starter/splitkit.py`, with no skipped or expected-failure tests.
2. `notes.md` - up to one page: your method for choosing test cases, and the behaviours your suite does **not** check (be specific).

## How it is graded

Criteria and level descriptors are in `../assessment/rubric.yaml`. In short: the suite passes on the correct module (must-pass); it kills at least **10 of 12 hidden required mutants** (must-pass);
and a reviewer scores boundary/invalid-input design, readability and honesty about limits. Finishing the lab without meeting the pass rule is not a completion claim.

## Self-check you can do now

Make your own mutants: copy `starter/splitkit.py`, change one character in one place, and run your tests against the copy
(`PYTHONPATH=<folder with the copy> python -m pytest -o pythonpath=<folder with the copy>`). If your tests still pass, you have found a gap. Do this at least ten times.
