# PY-M04 guided lab - Modernise a setup.py project

**Time:** about 2 hours  |  **Outcomes:** LO1-LO4  |  **Needs:** Python 3.11+, the packages in `../../../labs/requirements.txt` (`build`, `setuptools`, `pytest`). No network is needed once they are installed.

`starter/` is a small, working project (`tinycsv`) packaged the 2025 way: a `setup.py`, a `requirements.txt` and automatic package discovery. You will replace the packaging with a declarative
`pyproject.toml`, build it, install it into an empty environment and run it from somewhere else. A set of automated checks tells you what is still missing.

## Setup

```bash
cd courses/python-engineering/modules/PY-M04/lab-guided
python -m venv .venv && . .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                         # runs checks/ against starter/ - six checks fail at the start
```

The checks copy your project to a scratch directory before building, so build artefacts never appear in `starter/`.

## Step A - A clean environment (LO1)

1. Create an empty environment **outside** `starter/`: `python -m venv /tmp/tinycsv-env` (Windows: use a folder in your temp directory).
2. Without activating it, run `/tmp/tinycsv-env/bin/python -c "import sys; print(sys.prefix, sys.base_prefix)"`. Which of the two printed paths is the environment?
3. Try `/tmp/tinycsv-env/bin/python -c "import tinycsv"`. It fails: nothing is installed yet. Keep this environment for step D.

## Step B - Write pyproject.toml (LO2)

In `starter/`, create `pyproject.toml` with:

- a `[build-system]` table for setuptools (the packaging guide's example requires `setuptools >= 77.0.3`) and `build-backend = "setuptools.build_meta"`;
- `[project]` with `name = "tinycsv"`, the version declared **dynamic** and read from `tinycsv.__version__` (`[tool.setuptools.dynamic]`), a description, `readme`, `requires-python = ">= 3.11"`,
  `license = "LicenseRef-Training-Example"` and `license-files = ["LICENSE"]` (create a `LICENSE` file with one sentence: this example project is for the course only), and an empty `dependencies` list;
- `[project.scripts]` creating the command `tinycsv-summary` that calls `tinycsv.cli:main`;
- `[dependency-groups]` with a `test` group containing `pytest >= 8` (this replaces `requirements.txt`; delete that file);
- `[tool.setuptools.packages.find]` including only `tinycsv*`, and package data so that an empty marker file `tinycsv/py.typed` is shipped (create the file).

Then **delete `setup.py`**. Run `python -m pytest checks/test_packaging.py -k "setup or build_system or metadata or dependency"` until those pass.

## Step C - Build and inspect (LO3)

```bash
python -m build --no-isolation --outdir /tmp/tinycsv-dist .
python -m zipfile -l /tmp/tinycsv-dist/tinycsv-0.3.1-py3-none-any.whl
tar tzf /tmp/tinycsv-dist/tinycsv-0.3.1.tar.gz
```

Read both listings. Is there a `tests/` entry in the wheel? Is `tinycsv/py.typed` present? Which files are in the sdist but not the wheel, and why does that make sense?
(`--no-isolation` reuses the tools already installed so the lab works offline; in normal use leave isolation on.) If you are curious how the 2025 packaging behaved, restore the original `setup.py` in a copy and compare
the wheel listing: the `tests` package is shipped. Why?

## Step D - Install, run and verify (LO4)

```bash
/tmp/tinycsv-env/bin/python -m pip install --no-index --no-deps /tmp/tinycsv-dist/tinycsv-0.3.1-py3-none-any.whl
cd /tmp && /tmp/tinycsv-env/bin/tinycsv-summary <path to starter>/sample/people.csv
/tmp/tinycsv-env/bin/python -c "import tinycsv; print(tinycsv.__file__, tinycsv.__version__)"
/tmp/tinycsv-env/bin/python -m pip check
```

The summary should print `rows: 3`, `columns: name, age, city` and `numeric columns: age`. The printed `__file__` must be inside the environment's `site-packages`, not in `starter/`.
Why do we run the command from `/tmp` and not from the project folder?

## Step E - Run the automated checks

```bash
python -m pytest            # all ten checks must pass
```

The checks repeat steps B-D in scratch directories (build with `python -m build --no-isolation`, install into a fresh environment, run the installed command, `pip check`). The public reference is in `solution/`
(look only after you have tried; to see the checks pass against it run `LAB_TARGET=solution python -m pytest`).

## Reflection (write 5-8 lines in `notes.md`)

1. Which line in the old `setup.py` caused the `tests` package to be shipped, and what replaced it?
2. Where is the version defined now, and what would go wrong if it lived in two places?
3. Name one thing these checks do **not** prove about the package (hint: other Python versions, other operating systems, a real index).

## What the automated check proves - and what it does not

It proves this project builds, installs offline into an empty environment and runs. It does not test other Python versions, other operating systems or installation from a package index; the executed matrix is recorded in `docs/qa/LAB_EXECUTION_EVIDENCE.md`.
