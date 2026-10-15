# PY-M13 guided lab - Lazy pipelines, decorators and context managers

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` from `../../../labs/requirements.txt`. No network, no account and no paid service: everything runs on your computer.

`starter/streamkit.py` is a small library for processing a log stream. The **names, the docstrings and the dataclass `Event` are given**; every body that raises `NotImplementedError` is yours. Each docstring is the specification and `checks/` holds the tests, one file per step. You will write generators that own a file, a lazy parser, helpers that check their arguments at the call, three decorators and four context managers.

## Setup

```bash
cd courses/python-engineering/modules/PY-M13/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/streamkit.py`. Run one step with `python -m pytest checks/test_step_a_read_lines.py` (and `b_parse`, `c_streams`, `d_decorators`, `e_context_managers`). When a step passes, re-read the lesson section named in the heading and write the answer to the question in `notes.md` (create it next to this file); one or two sentences are enough, and a wrong answer written down is more useful than none.

The checks use a **counting iterator** (`checks/conftest.py`, class `Counting`): it records how many items it handed out and whether it was closed. That is how laziness and cleanup become testable; read it once.

## Step A - `read_lines`: a generator that owns a resource (LO1, LO2)

Write a generator that yields the lines of a UTF-8 file without their line ending. Open the file with a `with` block **inside the generator**. The checks verify four things: nothing is opened until the first `next()`, the file is closed when the generator is exhausted, when it is closed with `.close()`, and when an abandoned generator is garbage collected. A version that opens the file with `handle = open(...)` and no `with` passes the first two and fails the others; try it once and read the failure.

In `notes.md`: what raises `GeneratorExit`, and where (lesson section 4)? Why does `contextlib.closing` still help although CPython closes an abandoned generator by itself?

## Step B - `parse_line` and `parse_events`: a lazy transformation (LO1, LO2)

`parse_line` validates one line (`"<seconds> <LEVEL> <message>"`) and raises `ValueError` with the **line in the message**. Seconds must be ASCII digits (`str.isdigit()` is true for digits of other scripts: check `isascii()` too). `parse_events` is a generator that skips lines that do not parse and, when you pass a list, records them there. It must read **one input line per step**: the checks give it a counting iterator and compare how many items were taken.

In `notes.md`: why is it a design decision whether `parse_events` skips a bad line, stops, or raises? Which of the three did you choose for `parse_events`, and which would a billing system choose?

## Step C - `chunks`, `windows`, `take`, `dedupe`: arguments now, items later (LO2)

`chunks` and `windows` must report a bad `size` **when they are called**, not when the first item is requested, which a generator function cannot do: make the public function an ordinary function that checks and then **returns** an inner generator (lesson section 4 shows the pattern). Both are lazy and must never read ahead beyond what the current result needs. `take(iterable, n)` consumes exactly `n` items and leaves the rest of an iterator available. `dedupe` is lazy and works on an infinite input.

In `notes.md`: `windows` of a 3-item input with `size=5` yields nothing; what would `chunks` of the same input with `size=5` yield, and why do they differ?

## Step D - decorators that keep what they wrap (LO3, LO4)

`retry(times, on=..., sleep=..., delay=...)` is a decorator **factory**: three levels (the factory, the decorator, the wrapper). The arguments pass through, the return value passes through, the name and docstring survive (`functools.wraps`), only the listed exceptions are retried (`KeyboardInterrupt` is never retried), the **last** exception is raised, and `sleep` is called between attempts but not after the last one. `times` is validated when `retry(...)` is called. `counted` adds a `calls` attribute and counts calls that raise. `once` runs the function a single time, remembers a `None` result, and does not remember a failure.

In `notes.md`: why is `sleep` a parameter instead of a call to `time.sleep` inside the wrapper (what would the test of the delay have cost)? What does `@retry(3)` do to the order of arguments when someone writes `@retry` without the parentheses?

## Step E - context managers that clean up on every path (LO5)

`temp_env` is written as a class: set variables, restore them in `__exit__`, never suppress an exception, tell an empty string from a missing variable, and check the types **before changing anything**. `timer` and `collecting` use `@contextlib.contextmanager`; remember `try/finally` around the `yield`. `close_all` uses `contextlib.ExitStack` and shows its rule about several failures: every resource is closed, in reverse order, and the exception of the **last failing close** propagates.

Run `python -m pytest checks/test_step_e_context_managers.py`, then the whole suite with `python -m pytest`.

In `notes.md`: for `timer`, what would be skipped if you wrote the `yield` without `try/finally` and the block raised (lesson section 8)? Why does `collecting(KeyboardInterrupt)` fail at the `with` line rather than at the call?

## When you are done

All checks pass and `notes.md` has five short answers. Then ask the three questions of lesson section 9 about each function you wrote: how much does it consume, does its cleanup run on every path, and what does it preserve? The independent lab asks you to do the same on a design that has no starter code.

## What the checks do not tell you

They test behaviour, not taste: they cannot tell you that a generator is the wrong tool for a given input, or that a decorator hides a bug by retrying it. Read `solution/streamkit.py` only after your own version passes, and compare the *shape* of the two.
