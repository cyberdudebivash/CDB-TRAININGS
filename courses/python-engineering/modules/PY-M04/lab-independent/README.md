# PY-M04 independent lab - Package `logslice` from a specification

**Time:** about 2 hours  |  **Outcomes:** LO2-LO5  |  **Graded by:** automated checks plus a reviewer rubric (`../assessment/rubric.yaml`)

`starter/` contains a working Python project (`logslice`, in a `src/` layout) with **no packaging files**, a sample log and a helper script `scripts/report.py`. You write the packaging from the specification below. There is no reference solution
in this repository.

## Specification

**Project metadata (`pyproject.toml`, setuptools backend, no `setup.py`, `setup.cfg` or `requirements*.txt`)**

- Name `logslice`; version **dynamic**, read from `logslice.__version__`; `requires-python` at least 3.11.
- Licence: SPDX expression `LicenseRef-Training-Example`; `license-files = ["LICENSE"]` (the file exists).
- Console command `logslice` calling `logslice.cli:main`.
- **No runtime dependencies.** An optional extra `pretty` installs `rich >= 13`.
- Dependency groups: `test` (`pytest >= 8`), `lint` (`ruff`) and `dev`, which **includes** the other two with `{include-group = ...}` instead of repeating them.
- `src` layout: find packages under `src/`; the wheel ships only the `logslice` package plus an empty `py.typed` marker (create it). `tests/`, `scripts/` and `data/` must not be in the wheel.
- pytest configuration `testpaths = ["tests"]` under `[tool.pytest.ini_options]`.

**Single-file script (`scripts/report.py`)**

- Add a PEP 723 inline metadata block: `requires-python = ">=3.11"` and `dependencies = ["rich>=13"]`. The script must still run with the standard library alone (it already falls back to plain text).

## Setup and running the checks

```bash
cd courses/python-engineering/modules/PY-M04/lab-independent
python -m venv .venv && . .venv/bin/activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest            # runs checks/ against starter/ - most fail until you have written the packaging
```

## What you hand in

1. The packaging files in `starter/` (`pyproject.toml`, `src/logslice/py.typed`, the metadata block in `scripts/report.py`).
2. `notes.md` - one page: why you chose each setting where the specification left room (for example how you excluded the tests), the exact commands to build, install and run from an empty machine,
   the Python and tool versions you used, and what the checks do **not** prove.

## How it is graded

Four automated criteria are must-pass (metadata, build and contents, clean install, dependency kinds and script metadata); a reviewer scores rationale and reproducibility notes (rubric C5 and C6). Finishing the lab without meeting the pass rule is not a completion claim.
