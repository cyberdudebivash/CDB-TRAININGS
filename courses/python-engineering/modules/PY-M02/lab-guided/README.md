# PY-M02 guided lab - Catch the defects with your own tests

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+, `pytest` (see `../../../labs/requirements.txt`). No network is needed once the packages are installed.

You are given `starter/orderkit.py`, a small order-handling module whose contract is below. It contains **three seeded defects**. You do not fix it first: you
write tests that *find* the defects, then use those failing tests to fix the module. A final tool measures how good your tests are.

## The contract

| Function | Contract |
|---|---|
| `parse_quantity(text)` | Strips whitespace; accepts only ASCII digits that make a whole number of at least 1; otherwise raises `ValueError` with a message containing `positive whole number`. |
| `bulk_discount(quantity)` | Returns a `Decimal` rate: `0` below 10 units, `0.10` from 10 units, `0.20` from 50 units. |
| `add_line(item, quantity, basket=None)` | Appends `(item, quantity)` to `basket` and returns it. When no basket is given a **new** basket is started each time. |
| `order_total(basket, prices)` | Sum of `price * quantity * (1 - discount)` per line, rounded **half-up** to whole cents once at the end. An item without a price raises `UnknownItemError`. |

## Setup

```bash
cd courses/python-engineering/modules/PY-M02/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs student_tests against starter/
```

`pytest.ini` puts `starter/` on the import path, so `import orderkit` finds the module you are testing.

## Step A - Run your first test (LO1)

1. Run `python explore.py` and look at the output. Some of it should look wrong to you compared with the contract. Write down what looks wrong; do not fix anything yet.
2. Run `python -m pytest`. The example test in `student_tests/test_orderkit.py` passes. Break it on purpose (change `12` to `13` in one row), run again and read the failure report: find the
   line, the two values compared and the name of the failing row. Put it back.

## Step B - Invalid quantities must raise (LO3)

Add a parametrised test for inputs that are not positive whole numbers: empty text, spaces only, `"0"`, `"-3"`, `"abc"`, `"2.5"`, `"1e3"`, `"+4"` and one non-ASCII digit
(for example `"٣"`). Use `pytest.raises(ValueError, match="positive whole number")`. Run it: it should fail against the starter. Which input fails first, and why?

## Step C - Discount tier boundaries (LO2)

Add a parametrised test that checks the discount rate for 1, 9, 10, 11, 49, 50, 51 and a large quantity. Choose the rows from the contract's two boundaries, taking the value on each side
and on the boundary. It should fail on one row. Which row, and which character in the source explains it?

## Step D - No shared state (LO4)

Write one test that calls `add_line` **twice without passing a basket** and checks that the second basket contains only the second line. Then write a second test that passes an explicit
basket and checks that the same object is returned and extended. Run both. Explain in one sentence why a test that calls `add_line` only once could never find this defect.

## Step E - Totals, rounding and unknown items

Test `order_total` with an empty basket, a basket without discount, one line at each discount tier, a basket with two lines, and a price whose total ends in exactly half a cent
(for example price `0.125`, quantity 1 should give `0.13`). Add a test that an item without a price raises `UnknownItemError`.

## Step F - Run the mutation check (LO5)

The check applies one-line defects ("mutants") to the **correct** module (`solution/orderkit.py`) and reports which of them your tests detect.

```bash
python ../../../labs/_tools/mutation_check.py --module-dir solution --module orderkit --tests student_tests --mutants checks/mutants.json
```

- Your tests must pass on the correct module.
- You pass the lab when all **three required** mutants are killed (they correspond to the three defects in the starter).
- Four **stretch** mutants cover rounding, the 50-unit boundary, unknown items and non-ASCII digits. Surviving stretch mutants are not failures; for each one decide whether it
  is a real contract violation (it is) and add the test that would catch it.

Do not open `solution/` until you have run the check at least once with your own tests: the learning is in finding which behaviours you forgot to protect.

## Step G - Fix the module

Now fix `starter/orderkit.py` so that **your** tests pass. Make the smallest changes that satisfy the contract. Re-run `python -m pytest`, then re-run the mutation check against your fixed module:

```bash
python ../../../labs/_tools/mutation_check.py --module-dir starter --module orderkit --tests student_tests --mutants checks/mutants.json
```

(Mutations are applied to your fixed copy; the check will tell you if a patch no longer applies because you restructured the code - that is fine, ask your reviewer to adjust it.)

## Reflection (write 5-8 lines in `notes.md`)

1. Which defect would a single "happy path" test never have found, and why?
2. Which stretch mutant surprised you, and what contract sentence did it violate?
3. Name one behaviour of `orderkit` your tests still do not check.

## What the automated check proves - and what it does not

It proves your tests detect the listed defects. It does not prove the tests are complete or well designed: that is why the independent lab adds hidden mutants and a reviewer rubric.
