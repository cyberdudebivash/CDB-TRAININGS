# PY-M03 guided lab - From an untyped script to a strictly typed package

**Time:** about 2 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+, the packages in `../../../labs/requirements.txt` (pytest, mypy). No network is needed once they are installed.

`starter/inventory.py` is a small stock-report script with **no type annotations**. It runs, but it hides three defects. You will find them by typing the code, then restructure the script into a package that passes `mypy --strict` and has its own tests.
Automated checks tell you what is still missing; the public reference is in `solution/`.

## What the script must do (the contract)

| Function | Must do |
|---|---|
| `load_products(path)` | Read a CSV file with the header `sku,name,qty,price,reorder_level`. Wrong header: `ValueError("expected columns ...")`. A bad row: `ValueError("line N: invalid row")` (N is the file line number). |
| `total_value(products)` | Sum of `qty * price`, exact (`Decimal`). |
| `find_product(products, sku)` | The product, or `None` when the SKU is unknown. |
| `low_stock(products)` | SKUs whose quantity is **below** their reorder level, in file order, compared as **numbers**. |
| `restock_plan(products, budget)` | `(sku, units)` for each low-stock product, where units = reorder level - quantity, in file order. When the next purchase does not fit in the remaining budget: `ValueError("budget too small for <sku>")`. |
| `format_report(products, focus=None, budget=None)` | Lines `products: N`, `stock value: X.XX`, optional `focus: <name>` (an unknown SKU: `ValueError("unknown SKU: <sku>")`), `low stock: a, b` (or `none`) and `restock <sku>: <units>` lines when a budget is given. |
| `main(argv)` | `FILE [SKU [BUDGET]]`; prints the report and returns 0; usage errors, unreadable files and every `ValueError` print `error: ...` (or `usage: ...`) to stderr and return 2. |

The target package is `invkit` with the modules `models` (a frozen `Product` record), `loader`, `stock`, `report` and `cli`, an `__init__.py` that declares the public names in `__all__`, and an empty `py.typed` marker.
Dependencies point one way: `cli` -> `report` -> `stock` -> `models`, and `cli` -> `loader` -> `models`.

## Setup

```bash
cd courses/python-engineering/modules/PY-M03/lab-guided
python -m venv .venv && . .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                       # runs checks/ against starter/ - almost everything fails at the start
```

## Step A - Run the script and its tests (LO1)

```bash
cd starter
python inventory.py sample/products.csv A-100 100     # prints a report; look at the "low stock" line and the stock levels in the CSV
python -m pytest                                      # four of the five tests fail
```

Compare the printed low-stock line with the CSV: one product is missing. Which one, and why does `"9" < "10"` give the wrong answer? Note which tests fail; each failure is one of the three hidden defects.

## Step B - What default mypy tells you (LO2)

Run `python -m mypy inventory.py` (default settings), then `python -m mypy --strict --show-error-codes inventory.py`. The first prints "Success"; the second prints a list. Why does an untyped script pass in default mode, and what does that tell you about "mypy found nothing"?

## Step C - Annotate under strict mode (LO2)

Annotate `inventory.py` function by function until `--strict` is quiet. Represent a CSV row as `dict[str, str]` for now. Annotate honestly: `find_product` can return `None`; `restock_plan` can return `None` (as the script is written today).
Expect mypy to report three real problems in this style (the codes are `return`, `index` and `union-attr`): a function that can fall off its end, a value that may be `None` used as if it were certain, and a result that may be `None` used as a list.
**Fix the cause. Do not add `# type: ignore`, `cast` or `Any`:** the checks reject them. Then answer in `notes.md`: which defect did mypy find, which one did it *not* find (hint: the comparison of quantities), and why?

## Step D - Model the data and build the package (LO3)

Replace the text rows by a frozen `Product` dataclass with `int` quantities and a `Decimal` price, converted **once** in `load_products`. Now the quantity comparison is numeric and the third defect disappears. Create the package under `src/invkit/`:

1. `models.py`, `loader.py`, `stock.py`, `report.py`, `cli.py` with a one-line module docstring each, following the dependency directions above.
2. `__init__.py` importing the public names and listing them in `__all__` (`Product`, `find_product`, `format_report`, `load_products`, `low_stock`, `restock_plan`, `total_value`).
3. An empty `src/invkit/py.typed`.
4. Make the "bad" cases raise the errors in the contract (unknown SKU, over-budget plan) instead of returning `None` or crashing with `TypeError`.

Delete `inventory.py` when its code has moved.

## Step E - Layout, tests and one command (LO4, LO5)

1. Create `pyproject.toml` with `[tool.mypy]` (`strict = true`, `files = ["src", "tests"]`, `mypy_path = "src"`) and `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["src"]`). Delete `pytest.ini`.
2. Move `tests/test_inventory.py` to use the package (`from invkit import ...`), annotate the tests, and keep at least five tests. They live in `tests/`, outside the package.
3. Run both checks as one command from the project folder: `python -m mypy && python -m pytest`.
4. From the lab folder run the automated checks: `python -m pytest` (27 checks).

Explain in `notes.md` why the `src` layout makes `import invkit` fail from the project folder until `pythonpath = ["src"]` (or an installation) is configured, and why that is useful.

## Reflection (write in `notes.md`)

1. Which of the three defects needed a *better type*, not a *checker run*, to be found?
2. What would break if `cli` imported `report` and `report` imported `cli`?
3. Name one kind of error that `mypy --strict` and your tests together still cannot see.

## What the automated checks prove - and what they do not

They prove that the package type-checks in strict mode without suppressions, has the layout and dependency directions described, behaves as the contract says on the sample data and an error file, and that your tests pass.
They do not prove the code is correct for all inputs, that your tests are complete, or that the checks pass on other Python or mypy versions; the executed matrix is in `docs/qa/LAB_EXECUTION_EVIDENCE.md`.
