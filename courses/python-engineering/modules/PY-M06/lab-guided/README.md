# PY-M06 guided lab - Bounded, supervised concurrency and honest benchmarks

**Time:** about 2.5 hours  |  **Outcomes:** LO1-LO5  |  **Needs:** Python 3.11+ and `pytest` (see `../../../labs/requirements.txt`). No network is needed: the jobs in the checks only wait with `asyncio.sleep`, so a whole run takes a few seconds.

`starter/jobrunner.py` contains the result types (`Outcome`, `Speedup`, `JobTimeout`) and six functions that raise `NotImplementedError`. Each docstring is the specification; `checks/test_jobrunner.py` is the test suite. Work through the steps in order, one function at a time (`python -m pytest -k run_bounded`).
A check that never finishes fails after ten seconds instead of hanging your terminal.

## Setup

```bash
cd courses/python-engineering/modules/PY-M06/lab-guided
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pip install -r ../../../labs/requirements.txt
python -m pytest                                      # runs checks/ against starter/ - everything fails at first
```

Edit only `starter/jobrunner.py`. The checks call your coroutines with `asyncio.run`, so you never write an event loop yourself.

## Step A - `run_bounded`: many jobs, a fixed number at a time (LO2, LO3, LO5)

Run `func(item)` for every item with an `asyncio.Semaphore` as the gate, results in input order. Use an `asyncio.TaskGroup` so that a failure cancels the rest, and hand the failure to the caller **as itself**: a `TaskGroup` raises an `ExceptionGroup`, which the checks do not accept.
Two things about `except*` are worth knowing: `return`, `break` and `continue` are a syntax error inside it, and a new exception raised inside it is grouped again, so remember the failure in a variable and raise it after the block. In `notes.md` (create it next to this file): what does `asyncio.gather(*tasks)` do to the
other jobs when one fails, and which check shows that your version does something else?

## Step B - `run_collect`: partial results (LO5)

The same jobs, but a failing item must not stop the others: return one `Outcome` per item holding either the value or the error. Catch `Exception`, not `BaseException`: a cancellation must pass through. Compare with step A: when would you choose each policy for a nightly job that fetches 200 files?

## Step C - `call_with_timeout`: a limit that means something (LO3)

Use `async with asyncio.timeout(seconds) as limit:`. When the time is up the call is cancelled (its `finally` blocks run) and `TimeoutError` appears **outside** the block. Turn it into `JobTimeout(item, seconds)` only if `limit.expired()` is true: a `TimeoutError` that the function raised by itself must stay what it was.
In `notes.md`: why would `except BaseException:` inside `func` make this timeout silently useless? (Lesson section 6.)

## Step D - `process_queue`: backpressure (LO3)

One producer task puts items on a bounded `asyncio.Queue`; `workers` tasks take them and call the handler. Because `put` waits while the queue is full, the producer reads its input no faster than the workers consume it: the check hands you a generator of 50 items, blocks every handler and counts how many were read.
Stop the workers with one `None` per worker. Return the results in input order. In `notes.md`: what would a queue without `maxsize` do with a source of ten million items?

## Step E - `median_time` (LO4)

Time a function `repeats` times with `time.perf_counter` and return the median. In `notes.md`: why the median and not the mean? (One of the checks has a run that takes thirty times longer than the others.)

## Step F - `speedup`: compare two ways of doing the same job (LO1, LO4)

Run the baseline and the candidate **alternately** (baseline, candidate, baseline, ...) `repeats` times each, so that a busy computer slows both alike, and return the two medians and their ratio in a frozen `Speedup`. Then use it yourself, in a scratch file next to `notes.md`: take 20 jobs that each `await asyncio.sleep(0.05)`,
compare "one after another" (`asyncio.run` of a loop of awaits) with `run_bounded(..., limit=1)`, `limit=5` and `limit=20`, and write the three ratios in `notes.md` with the machine you used. Which limit gave the best ratio and why not a larger one? (Hint: Amdahl, lesson section 2.)

## Finish

Run `python -m pytest` and keep the output with your notes. Then refactor and run it again.

## What you hand in

`starter/jobrunner.py` and `notes.md` (the answers from steps A to F, one page, with the measured ratios). Passing the provided checks shows that your functions do what the checks test; it does not show that they scale or that your measurements transfer to another computer, which the independent lab asks you to discuss.

## Checking against the public solution (optional)

`solution/jobrunner.py` is the reference implementation. **Try each step yourself first.** To confirm the checks themselves are sound, run them against the solution:

```bash
LAB_TARGET=solution python -m pytest         # Windows PowerShell:  $env:LAB_TARGET="solution"; python -m pytest
```
