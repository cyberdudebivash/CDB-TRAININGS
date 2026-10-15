# PY-M09 independent lab - An alert triage that scales, with tests that prove it

**Time:** about 2.5 hours  |  **Outcomes:** LO1, LO2, LO4, LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`; no network, account or paid service. **Prerequisite:** the lesson (sections 2 to 6 and 8) and the guided lab.

`starter/triage.py` is a working, **slow** program: it collapses a stream of security alerts into incidents, ranks the most urgent ones and writes a report. Every answer it gives is correct and is the specification of the answers you must keep. You are given no step list. Ten published checks (`python -m pytest`) show the shape of the task; the instructors run a **hidden suite** that compares your `triage.py` with the original on hundreds of random and awkward inputs, measures how its work grows, reads its code for input and output in the core, and runs the budget tests you wrote against both your version and the original. How you are graded is in `../assessment/rubric.yaml`.

## Setup

```bash
cd courses/python-engineering/modules/PY-M09/lab-independent
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/triage.py - some fail at first
python -m pytest starter                              # runs YOUR tests (starter/test_budget.py) once you have written them
```

Edit `starter/triage.py`, add `starter/test_budget.py` and `notes.md`. Standard library only for `triage.py`.

## The task

### 1. Find out where the time goes (LO1) - and write it down

Build a realistic input (a few thousand alerts with many different hosts and rules, plus a few repeated ones) and profile `triage(alerts, window, top)` with `cProfile`. Before you change anything, put in `notes.md`: the three functions with the largest cumulative time and their share of the run, and **your prediction** of the speed-up if you fix the largest one (Amdahl, lesson section 3). After you are done, put the measured numbers next to the prediction and say where they differ and why. Also measure the **peak memory** of one run of `triage` on your input with `tracemalloc`, and say which allocation dominates (use a snapshot) and what you would change if the input were a hundred times larger.

### 2. Make it scale without changing an answer (LO2)

The functions to speed up are `normalize`, `collapse`, `rank`, `summarize` and `render` (and `triage` builds on them). Their documented behaviour is the behaviour: the order of the results, the tie-breaking, which input is rejected and with what error, what the report looks like. The hidden suite is built from the cases that tempt an "optimisation" to change an answer: alerts that arrive out of time order, equal `(ts, id)` pairs, windows of `0`, severities outside 1 to 5, messages that differ only in digits or spaces, incidents that tie on all four ranking keys, `n` larger than the number of incidents, and empty input.

Work budgets: on inputs where the original takes seconds, yours must take a small fraction of a second. The hidden suite measures how the time grows when the input grows by a factor of four and applies budgets an order of magnitude away from both the original and a good solution; it also counts how often a regular expression is compiled while `normalize` runs.

### 3. Keep the core free of input and output (LO5)

`normalize`, `collapse`, `rank`, `summarize`, `triage` and `render` compute; they must not open files, print, read input, import `json`, `os` or `pathlib`, or mention `read_alerts`. `read_alerts` is the edge: keep its behaviour exactly (lazy, closes its file, line numbers in `AlertFormatError`). The hidden suite reads your code to check the rule.

### 4. Prove it with tests of your own (LO4)

Write `starter/test_budget.py` with at least three tests, using only `import triage` for the code under test (and the standard library and pytest), that

- pass with your `triage.py`;
- **fail when the same file is run against the original slow `triage.py`** (the instructors copy the original next to your tests and run them again; at least two of your tests must fail on it);
- do not depend on how fast the machine is: use counts, ratios between an input and one four times larger, or budgets far from both answers (lesson section 6), the smallest of several runs, and an early exit so that they do not run for minutes on the slow version (a single test must finish in under 20 seconds on the original);
- include one equivalence test (your version against an obviously correct implementation of the specification that you write in the test file, on random inputs with a fixed seed).

### The specification in one place

`Alert`, `Incident` and `Triage` are frozen dataclasses (given). `collapse` processes the alerts in `(ts, id)` order (a stable sort); an alert joins the most recent incident with the same key if its `ts` is at most `window` seconds after that incident's `last_ts`, otherwise it starts a new one; incidents are returned ordered by `(first_ts, id of the first alert)`; a `window` that is negative, a bool or not an int, or an alert with a severity outside 1 to 5, is a `ValueError`. `rank` orders by highest `max_severity`, then largest `count`, then earliest `first_ts`, then smallest first id, ties keeping input order; a bad `n` is a `ValueError`. `summarize` and `render` have the exact shapes in their docstrings. Read the starter's docstrings: they are the contract.

## Suggested order (not a step list)

Profile first and write down the prediction. Build the awkward inputs and a small oracle (the original code is your oracle: keep a copy of it as `slow_triage.py` outside `starter/`). Fix the largest share, re-run the equivalence comparison, profile again. Only then write the budget tests, and run them against your version and against the original.

## What you hand in

1. `starter/triage.py`.
2. `starter/test_budget.py`.
3. `notes.md` (one page): the profile before and after, the prediction against the measurement, which function you changed first and why, one change you decided *not* to make (because the profile said it would not matter), and how each of your budget tests avoids depending on the machine.

## Hints that are not solutions

- `cProfile` call counts are exact, but a scan that is a loop in your own code is only visible in the time and in the line counts; choose the metric that sees the work you removed.
- A dictionary from key to the *open* incident answers "is there an incident for this key within the window?" without looking at the others; what must you store besides the incident to update it cheaply?
- `heapq.nsmallest(n, items, key=...)` is documented as equivalent to `sorted(items, key=key)[:n]`: what does that say about ties?
- A compiled pattern belongs where it is built once. A regular expression that is cached by the `re` module still costs a lookup per call.
- Two implementations that must agree are tested on awkward inputs, not on typical ones.
