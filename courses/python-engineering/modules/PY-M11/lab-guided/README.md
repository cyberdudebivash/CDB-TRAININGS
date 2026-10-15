# PY-M11 capstone, part A - the walking skeleton

**Time:** about 3.5 hours  |  **Outcomes:** LO1, LO2, LO5, LO6  |  **Needs:** Python 3.11+ and the packages of `../../../labs/requirements.txt` (pytest, coverage, mypy, ruff, build, setuptools, wheel, PyYAML, types-PyYAML). After the one-time installation of those packages nothing needs a network, an account, a paid service or an open port.

The capstone has two parts. In **part B** you build `authwatch`, an application that finds brute-force, password-spray and compromise-after-failures patterns in authentication events. Before you write any of its logic, you build the machinery around it: the package, the single command that decides whether a change may merge, the pipeline file and the documents. A project that has all of that and almost no behaviour is called a *walking skeleton*, and the order is deliberate: the machinery is cheap to get right while there is nothing in it, and every later hour is then checked by it.

This part has no hidden tests. Its check is the release gate, `tools/gate.py --part A`: eleven conditions, each with a message that says what is missing. Passing it is necessary for part B, not a grade.

## Setup

```bash
cd courses/python-engineering/modules/PY-M11/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
mkdir -p ../lab-independent/project                    # your project lives here; part B continues in it
```

## What you receive

| Path | What it is |
|---|---|
| `prototype/authwatch_proto.py` | the script this application replaces (about thirty lines, "temporary since 2023") |
| `sample-data/events-small.jsonl` | sixteen authentication events with one unusable line: a brute force with a success, a spray, a few ordinary events |
| `tools/gate.py` | the release gate (offline). `--part A` checks the skeleton, plain `python tools/gate.py` checks the finished application |
| `tools/make_events.py` | a deterministic generator of a damaged event stream and the list of what a correct scan must find (used in part B) |
| `tools/advisories.json` | a small list of **synthetic** advisories for the dependency check |
| `../lab-independent/SPEC.md` | the specification of `authwatch` (read it now, build it in part B) |

## Step 1 - Characterise the prototype (LO1, about 45 minutes)

Run the prototype on the sample data and read it as a stranger would. **Run it only on that file or on files you wrote yourself**: it passes every line to `eval` and every user name to a shell, which are two of the defects you are about to list.

```bash
cd prototype && python authwatch_proto.py ../sample-data/events-small.jsonl && cd ..
```

Then open `../lab-independent/SPEC.md`, section 8, which lists what the prototype gets wrong. Create `../lab-independent/project/NOTES.md` and write a table of **at least eight rows**: an input (a log line, a command line or a situation), what the prototype does with it today, what the specification says, and your decision (`keep`, `fix` with the reason, or `open question`). Include at least two rows you *keep* and at least three you *fix*; a characterisation that fixes everything has not looked at what works. Part B's rubric reads this file.

Section 3 of the lesson shows the method on the handbook's keyword matcher.

## Step 2 - The package (LO2, about 1 hour)

Create in `../lab-independent/project/`:

- `src/authwatch/__init__.py` with `__version__ = "<a version of your choice>"` and nothing that runs on import;
- `src/authwatch/__main__.py` (`raise SystemExit(main())` with `main` imported from the command-line module);
- `src/authwatch/cli.py` with `main(argv=None) -> int`: `--version` prints `authwatch <version>`, and `scan [--format json] [FILE ...]` reads the files (or standard input) and prints **one JSON object**: `{"schema": 1, "summary": {"events": N, "failures": N, "out_of_order": 0, "findings": 0}, "findings": []}`. In part A `json` is the only format (and the default) and "events" may be the number of lines that parse as a JSON object with the four fields; part B replaces this by the real parsing and detection, adds the `text` format and makes it the default, so the command line the gate uses does not change;
- `src/authwatch/py.typed` (an empty file);
- `pyproject.toml`: build backend `setuptools.build_meta`, `name = "authwatch"`, a **dynamic version read from `authwatch.__version__`**, `requires-python = ">= 3.11"`, a licence expression and `license-files`, `readme`, the dependency `PyYAML >= 6.0, < 7` (used by part B), the console script `authwatch = authwatch.cli:main`, and configuration of pytest, mypy (`strict = true`), ruff and coverage (`branch = true`, `fail_under = 90`);
- `LICENSE` (one sentence is enough for an exercise), `.gitignore` (at least `.env`, `__pycache__/`, `build/`, `dist/`) and `requirements.lock` with the exact pin of every runtime dependency (`PyYAML==6.0.3`).

Lesson section 4 shows the two traps this step avoids: the flat layout that imports from the source tree, and the version stated in two places.

## Step 3 - One command (LO6, about 45 minutes)

Write `scripts/check.py`: it runs, in this order and stopping at the first failure, `ruff check src tests scripts`, `mypy`, `coverage run -m pytest`, `coverage combine`, `coverage report`, and a build of the wheel and the sdist into a scratch directory (`python -m build --no-isolation --outdir <tmp> <project>`). Add `requirements-dev.txt` with the pinned tools, `tests/` with **at least five tests** of what the skeleton does (the version, the summary, the exit status of a missing file), and the `README.md` with the sections `Install`, `Usage`, `Configuration`, `Exit codes`, `Security considerations` and `Development`, and `CHANGELOG.md` whose newest heading is the version in your package.

Run `python scripts/check.py` until it passes on your laptop. This is the command the pipeline will run, so a difference between the two is a defect.

## Step 4 - The pipeline (LO6, about 30 minutes)

Write `.github/workflows/ci.yml`. The gate checks these rules, which come from GitHub's own security guidance (lesson section 8): runs on `push` and `pull_request` and not on `pull_request_target`; `permissions: {contents: read}` at the top; a `timeout-minutes` on every job; a matrix over the Python versions `"3.11"`, `"3.12"`, `"3.13"` and `"3.14"` **as quoted strings**; every `uses:` pinned to a full 40-character commit SHA; `actions/checkout` with `persist-credentials: false`; no `${{ github.event... }}` text inside a `run:`; no secrets; and a step that runs `python scripts/check.py`.

You have no network in this lab, so you cannot look up the SHAs. These two were resolved from the actions' own repositories on 2026-10-15 and are the only versions this lab has verified; on a real project you look them up again, from the action's own repository and not from a fork:

```text
actions/checkout       3d3c42e5aac5ba805825da76410c181273ba90b1   # v7.0.1
actions/setup-python   5fda3b95a4ea91299a34e894583c3862153e4b97   # v7.0.0
```

The gate cannot tell whether a SHA exists. It can only tell that you wrote one, and it says so.

## Step 5 - Run the gate (LO2, LO5, LO6, about 30 minutes)

```bash
python tools/gate.py --part A
```

Fix what it reports until eleven of eleven gates pass: G01 layout, G02 metadata, G03 the offline build, G04 the contents of the wheel, G05 a clean installation that imports from elsewhere and agrees with itself about the version, G06 `mypy --strict` (your settings are ignored), G07 `ruff` with the rules of the specification and no blanket suppression, G09 the workflow, G10 the lock file against the advisories, G11 hygiene (no secrets, no `eval`, `.gitignore`), G12 README sections and the changelog. G08 (at least 30 tests and branch coverage of 90 percent) and G13 (the live scenario) need the finished application and are part B's.

## When you are done

- `python scripts/check.py` passes and `python tools/gate.py --part A` reports 11 of 11.
- `NOTES.md` has the characterisation table.
- You can say, for each gate, which mistake it would have caught.

## What the gate does not tell you

It does not know whether your tests would notice a defect (part B grades that with defective copies of an implementation), whether your pinned actions exist, whether a dependency has a *real* advisory (the advisories here are synthetic; with network access run `pip-audit` or an OSV-based scanner on `requirements.lock`), or whether the project reads well to the next person.
