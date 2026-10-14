# PY-M03 independent lab - Type and restructure `fleetlog`

**Time:** about 2 hours  |  **Outcomes:** LO1-LO5  |  **Graded by:** automated checks plus a reviewer rubric (`../assessment/rubric.yaml`)

`starter/` contains a flat, **untyped** program (`models.py`, `util.py`, `report.py`, `main.py`, a sample file and tests) that computes fuel consumption per vehicle. It works for the sample but fails `mypy --strict` with dozens of errors, uses `float`,
hides a circular import (`import models` alone fails) and does not meet the specification below. You produce a clean package. There is no reference solution in this repository.

## Specification

**Package** `fleetlog` in a `src` layout (`src/fleetlog/`) with the modules `models`, `parsing`, `analysis`, `render` and `cli`, an `__init__.py` that lists these names in `__all__`: `Trip`, `consumption`, `parse_lines`, `parse_trip`, `render`, `worst`; and an empty `py.typed`.
Dependencies must be acyclic and every module must import on its own. Each module has a docstring. The old flat modules, `pytest.ini` and any `setup.py`/`setup.cfg` are gone.

**Behaviour**

- `Trip` is a frozen record: `vehicle: str`, `distance_km: Decimal`, `fuel_l: Decimal`.
- `parse_trip(line)`: three comma-separated fields (whitespace around them ignored): vehicle (non-empty), distance (finite, > 0), fuel (finite, >= 0). Anything else raises `ValueError("invalid trip: <line>")`. `NaN` and `Infinity` are invalid.
- `parse_lines(lines)`: ignores blank lines and lines starting with `#` (after whitespace); the first invalid line raises as above.
- `consumption(trips)`: litres per 100 km for each vehicle = total fuel / total distance * 100 in **exact decimal arithmetic**, rounded **half-up** to two places, as a dict ordered by vehicle name. No trips: `{}`.
- `worst(values, n)`: the `n` highest entries as `(vehicle, value)` tuples, highest first, ties by vehicle name; `n < 1` raises `ValueError("n must be at least 1")`; `n` larger than the number of vehicles returns all.
- `render(values)`: one line per vehicle, `<vehicle>: <value with two decimals> L/100km`, in the mapping's order; an empty mapping gives `no trips`.
- Command line `fleetlog FILE [N]` (`main(argv)`): prints `render(dict(worst(consumption(trips), N)))` with N defaulting to 3 and returns 0. A missing argument, an unreadable file, an invalid line, `N < 1` or a non-numeric `N` prints `usage: ...` or `error: ...` to stderr and returns 2.

**Static checking and tests**

- `pyproject.toml` with `[tool.mypy] strict = true` and `[tool.pytest.ini_options] testpaths = ["tests"]` (plus whatever path settings you need).
- `python -m mypy` passes on `src` and `tests` in strict mode with **no** `# type: ignore`, `cast` or `Any`.
- `tests/` (outside the package) holds at least three typed tests that pass.

## Setup and running the checks

```bash
cd courses/python-engineering/modules/PY-M03/lab-independent
python -m venv .venv && . .venv/bin/activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest            # runs checks/ against starter/ (your working copy); everything fails at the start
```

Keep `starter/data/trips.csv`; the behaviour checks read it.

## What you hand in

1. The restructured project in `starter/`.
2. `notes.md` - one page: what each class of mypy error would have meant at run time, how the circular import arose and how you removed it, a defect that the types alone did not reveal (and how you found it), and what your checks do **not** cover.

## How it is graded

Four automated criteria are must-pass (strict typing, structure, behaviour, configuration and tests); a reviewer scores the explanation of fixes and honesty about limits (rubric C5 and C6). Finishing the lab without meeting the pass rule is not a completion claim.
