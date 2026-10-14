# PY-M01 guided lab - Make the tests pass, one function at a time

**Time:** about 4 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` (see `../../../labs/requirements.txt`). No network is needed once the packages are installed.

`starter/datakit.py` contains five small data-processing functions and one file wrapper. Every function body is `raise NotImplementedError`. The **provided tests** in `checks/test_datakit.py` describe what each function must do; the docstring of each function
is the specification. You make the tests pass one function at a time, following the method of lesson section 8: pick one failing test, run only it, write the smallest code that passes, then run everything.

## Setup

```bash
cd courses/python-engineering/modules/PY-M01/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/datakit.py`. The tests import it for you, so no `import` line is needed in the tests.

## Step A - Read a failure and name your Python (LO1)

1. Run `python --version` and `python -c "import sys; print(sys.executable)"` and write both lines in `notes.md` (create it next to this file). Say which of the supported versions (3.11 to 3.15) you are running.
2. Run `python -m pytest -k test_word_frequencies_counts_and_orders`. Read the failure from the **bottom**: what is the error type, which line of `datakit.py` raised it, and which line of the test called it?
   Write the three answers in `notes.md`.
3. Run `python -m pytest -x -q` and observe how much shorter the output is. Remember `-k` (choose tests by name) and `-x` (stop at the first failure); you will use both below.

## Step B - `word_frequencies` (LO2, LO3)

Read the docstring, then the three tests for it. Hints, not solutions: `str.lower()`, `re.findall` with a pattern for letters, `collections.Counter`, and `sorted(..., key=lambda item: (-item[1], item[0]))` to sort by two things at once.
Write the function, run `python -m pytest -k word_frequencies`, then the whole suite. In `notes.md`, say why the result is built as a `dict` (what you rely on: insertion order, since Python 3.7).

## Step C - `chunk` and `group_by_length` (LO2, LO3)

`chunk` uses slicing (`items[i:i + size]`) and a range with a step. `group_by_length` needs a dictionary of lists; `dict.setdefault` or `collections.defaultdict` helps. Check the test that your input list is **not changed**: copying versus aliasing is the point
of lesson section 4. Before you run it, predict whether your solution passes it; then run it.

## Step D - `parse_kv_lines` (LO3, LO4)

Parsing text from a file is where input surprises you. Work through the tests in this order: simple lines, comments and blank lines, a value that contains `=`, then the error with a line number. Use `str.partition("=")` (it splits on the *first* `=` only) and `enumerate(..., start=1)`.
In `notes.md`, write the three inputs you would add to the tests if you wanted to be sure the function is right, and one sentence about why each matters.

## Step E - `summarise_scores` (LO2, LO3)

The input is a list of dictionaries, as `csv.DictReader` produces: every value is **text**. Convert with `float`, skip blanks, and turn a bad number into the specified `ValueError`. Compare your solution with the test for `1, 2, 2` (average 1.666...): which function rounds, and where is the right place to round?

## Step F - `summarise_file` (LO4)

This function connects the others to the disk: read a CSV with `csv.DictReader` (opened with `newline=""` and `encoding="utf-8"`), call your own `summarise_scores`, and write the JSON result with `json.dumps(..., indent=2, ensure_ascii=False)`, UTF-8 and a final newline.
Use `pathlib.Path` for the paths. A missing input file should raise `FileNotFoundError` **before** anything is written; do not catch it. Run `python -m pytest -k summarise_file`.
In `notes.md`, say what would go wrong, and on which kind of machine, if you left out `encoding="utf-8"` (lesson section 6).

## Finish

Run `python -m pytest` and keep the output with your notes. Then refactor: rename anything unclear, remove repeated code, and run the tests again. A green run after a refactor is the point of the tests.

## What you hand in

`starter/datakit.py` and `notes.md` (one page: the answers from steps A to F). Passing the provided tests shows that your functions do what the tests check; it does **not** show they are right for every input, which is what the independent lab and PY-M02 address.

## Checking your own work against the public solution (optional)

`solution/datakit.py` is the reference implementation. **Try each function yourself first.** To confirm the checks themselves are sound, run them against the solution:

```bash
LAB_TARGET=solution python -m pytest         # Windows PowerShell:  $env:LAB_TARGET="solution"; python -m pytest
```
