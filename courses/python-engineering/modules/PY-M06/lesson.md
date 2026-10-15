---
id: PY-M06
title: "Concurrency and asynchronous programming"
course: COURSE-PY-ENG
level: 2
audience: "Programmers who have finished PY-M01 to PY-M05 and now need to make programs that wait on networks and files finish sooner, without making them fragile"
prerequisites:
  - "PY-M02 (pytest), PY-M04 (virtual environments) and PY-M05 (HTTP clients, timeouts, retries)"
  - "Python 3.11 or newer (`asyncio.TaskGroup`, `asyncio.timeout` and `except*` need 3.11); the labs were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "httpx 0.28.1 and pytest 9.1.1 from labs/requirements.txt; no account, no paid service and no network access beyond your own computer"
estimated_time_hours: {lesson: 3.0, guided_lab: 2.5, independent_lab: 2.5, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005); feature availability by version executed in this lesson (R-095)", httpx: "0.28.1 (PyPI snapshot 2026-10-14; R-045)", pytest: "9.1.1"}
last_verified: 2026-10-14
---

# PY-M06 - Concurrency and asynchronous programming

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Choose between sequential code, threads, `asyncio`, processes and (since Python 3.14) free-threaded builds and subinterpreters from the profile of a task (waiting on I/O or computing), and say what each choice cannot do. |
| **LO2** | Write correct `asyncio` code: coroutines, tasks, `asyncio.run`, `TaskGroup`, `except*`, never blocking the event loop, and protecting state that is shared across `await` points. |
| **LO3** | Bound concurrency (semaphores, bounded queues) and apply timeouts and cancellation correctly, with cleanup that runs and `CancelledError` that is never swallowed. |
| **LO4** | Write a benchmark that proves (or disproves) a speed-up: same input, repeats, medians, interleaved runs, and a report that claims no more than was measured. |
| **LO5** | Run many jobs where some fail: choose fail-fast or collect-the-outcomes, return partial results with the errors attached, and leave no task running behind you. |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

Waiting is the most common thing programs do: for a web server, a database, a disk. While one request waits, the processor is idle, so doing many waits at once can shorten a job from minutes to seconds. The 2025 handbook promises exactly that ("3x faster execution with minimal effort", "1000 requests happen in SECONDS",
"This is impossible with regular code"), and shows code that, run as written, creates one client per request, starts every request at once with no limit and no timeout, and lets sibling tasks run on after one fails (F-PYH-010). It also installs a package called `asyncio` that is part of the standard library already (R-094).
None of the speed claims comes with a measurement. This module keeps the goal and replaces the claims with a method: choose from a profile, bound the concurrency, supervise the tasks, and **measure** the result. All examples run on your own computer against small servers started for the occasion.

## 2. Choosing a tool from the profile (LO1)

A job is **I/O-bound** when it spends its time waiting (network, disk, database) and **CPU-bound** when it spends its time computing. The two need different tools.

| Tool | Helps with | Cost and limits |
|---|---|---|
| Sequential code | Everything small; the baseline you must beat | Waits add up |
| Threads (`ThreadPoolExecutor`) | I/O-bound work with blocking libraries | One interpreter lock (the GIL) lets one thread run Python code at a time on the standard build, so CPU-bound work does not speed up; shared state needs locks |
| `asyncio` | Thousands of waits in one thread | Everything on the path must be `await`-friendly; one blocking call stalls all tasks |
| Processes (`ProcessPoolExecutor`) | CPU-bound work on several cores | Data is copied between processes (it must be picklable); start-up cost; the start method differs by platform and version |
| Free-threaded build, subinterpreters (3.14+) | CPU-bound work in threads without the GIL | Officially supported from 3.14 but a different build or a different programming model; many libraries lag; measure before you rely on it (R-046) |

The handbook's rule of thumb, "the GIL blocks CPU-bound threads but not I/O-bound ones" (p. 134), is true of standard builds and incomplete: the lock is released while a thread waits, which is why threads help with waiting, and a free-threaded build removes the lock altogether.
The next block runs the same twenty "requests" (each is a 0.04-second wait) three ways, then runs CPU-bound work in threads. Run it yourself and read the numbers, not the adjectives.

```python run
import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor

LATENCY, N = 0.04, 20


def io_call(i):                          # a blocking call that waits, like a network request
    time.sleep(LATENCY)
    return i


async def io_call_async(i):              # the same wait, but giving control back to the event loop while it waits
    await asyncio.sleep(LATENCY)
    return i


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


sequential, t_seq = timed(lambda: [io_call(i) for i in range(N)])
with ThreadPoolExecutor(max_workers=10) as pool:
    threaded, t_thr = timed(lambda: list(pool.map(io_call, range(N))))


async def run_async():
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(io_call_async(i)) for i in range(N)]
    return [task.result() for task in tasks]


concurrent, t_async = timed(lambda: asyncio.run(run_async()))
assert sequential == threaded == concurrent == list(range(N))
assert t_seq >= N * LATENCY * 0.9                          # sequential: the waits add up
assert t_thr < t_seq / 3 and t_async < t_seq / 3           # threads and asyncio: the waits overlap


def burn(n):                                               # CPU-bound: nothing to wait for
    total = 0
    for i in range(n):
        total += i * i
    return total


WORK = 1_000_000
_, t_four = timed(lambda: [burn(WORK) for _ in range(4)])
with ThreadPoolExecutor(max_workers=4) as pool:
    _, t_four_threads = timed(lambda: list(pool.map(burn, [WORK] * 4)))
if getattr(sys, "_is_gil_enabled", lambda: True)():        # a standard build
    assert t_four / t_four_threads < 1.6                   # four threads are not four times faster, however many cores there are
```

Two facts follow. **Overlapping waits is limited by the slowest dependency**: if 80 percent of a job can overlap and 20 percent cannot, the best possible speed-up is 1 / (0.2 + 0.8 / n), at most 5 times however many tasks you start (Amdahl's law). And **the best tool depends on the profile, not on fashion**: for twenty waits threads and `asyncio` do equally well, so choose by the libraries you have and the failure handling you need.

## 3. Coroutines, tasks and the event loop (LO2)

An `async def` function called without `await` produces a *coroutine object* and runs nothing. `await` runs a coroutine to completion and lets other tasks run while it waits. A **task** (`asyncio.create_task`, or `TaskGroup.create_task`) schedules a coroutine to run concurrently with the code that created it. All of this runs in **one thread**, one task at a time:
a task gives up control only at an `await`. That is the entire trade: you get cheap concurrency, and in exchange nothing may block. `asyncio.run(main())` starts an event loop, runs `main` and shuts the loop down; it is the one entry point to use from synchronous code (R-093).

The classic mistake is a blocking call inside a coroutine (`time.sleep`, `requests.get`, a long loop): the loop cannot run any other task until it returns. A heartbeat task makes this visible: it should tick every 10 milliseconds.

```python run
import asyncio
import time


async def ticks_during(work):
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    beat = asyncio.create_task(heartbeat())              # keep the reference: the loop holds tasks only weakly
    await asyncio.sleep(0)                               # let the heartbeat start
    await work()
    beat.cancel()
    try:
        await beat
    except asyncio.CancelledError:
        pass
    return ticks


async def blocking():
    time.sleep(0.2)                                      # blocks the whole event loop


async def friendly():
    await asyncio.to_thread(time.sleep, 0.2)             # the blocking call runs in a worker thread; the loop stays free


assert asyncio.run(ticks_during(blocking)) <= 1          # the heartbeat froze for the whole 0.2 s
assert asyncio.run(ticks_during(friendly)) >= 10         # about 20 ticks while the same wait happens elsewhere
```

When a library only offers a blocking API, `await asyncio.to_thread(function, *args)` runs it in a thread without freezing the loop. Prefer a library with a real asynchronous API (`httpx.AsyncClient`, PY-M05) where there is one.

## 4. Structured concurrency: TaskGroup, gather and what happens when one task fails (LO2, LO5)

`asyncio.gather(*coros)` runs coroutines concurrently and returns their results. By default, when one raises, the exception reaches the caller **and the others keep running** (R-093): nothing cancels them, nobody awaits them, and their work and their errors are lost. `asyncio.TaskGroup` (3.11) is the safer default: it
waits for all its tasks, cancels the rest when one fails, and raises what failed as an `ExceptionGroup`, which you handle with `except*`. Also keep a reference to every task you create outside a group: the event loop keeps only weak references, so an unreferenced task can be garbage-collected before it finishes (R-093).

```python run
import asyncio


async def worker(name, delay, fail, log):
    try:
        await asyncio.sleep(delay)
        if fail:
            raise ValueError(name)
        log.append(f"{name} finished")
        return name
    except asyncio.CancelledError:
        log.append(f"{name} cancelled")
        raise                                            # cleanup done: let the cancellation continue


async def with_gather():
    log = []
    try:
        await asyncio.gather(worker("bad", 0.01, True, log), worker("slow", 0.1, False, log))
    except ValueError:
        log.append("caller saw ValueError")
    await asyncio.sleep(0.15)                            # give the sibling time: it was never cancelled
    return log


async def with_taskgroup():
    log = []
    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(worker("bad", 0.01, True, log))
            group.create_task(worker("slow", 0.1, False, log))
    except* ValueError as failures:
        log.append(f"caller saw {len(failures.exceptions)} ValueError")
    await asyncio.sleep(0.15)
    return log


assert asyncio.run(with_gather()) == ["caller saw ValueError", "slow finished"]            # the sibling ran on, unsupervised
assert asyncio.run(with_taskgroup()) == ["slow cancelled", "caller saw 1 ValueError"]      # the sibling was stopped first


async def boom(name):
    raise ValueError(name)                                   # fails at its first step, before anything can cancel it


async def several_failures():
    names = []
    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(boom("a"))
            group.create_task(boom("b"))
    except* ValueError as failures:
        names = sorted(str(error) for error in failures.exceptions)        # all of them arrive together, not just the first
    return names                                                           # return, break and continue are not allowed inside except*


assert asyncio.run(several_failures()) == ["a", "b"]
try:
    compile("async def f():\n    try:\n        pass\n    except* ValueError:\n        return 1\n", "<example>", "exec")
except SyntaxError:
    pass                                                                    # record what you need inside except*, act after the block
else:
    raise AssertionError("return inside except* must be a syntax error")
```

There are two sensible policies for a batch of independent jobs, and you choose between them on purpose. **Fail fast**: the first error cancels the rest (a `TaskGroup` does this by itself). **Collect**: every job runs, and you get one *outcome* per job, either a value or an error, so the caller can report partial results (section 10).
`gather(..., return_exceptions=True)` is the collect form of `gather`, but it also hands you a `CancelledError` as a "result" in some cases; wrapping each job in a function that returns an outcome object is clearer and is what the labs do.

## 5. Bounding concurrency (LO3)

Starting every request at once is the handbook's pattern (p. 136) and it breaks as soon as the job is large: the server rate-limits you, the operating system runs out of connections, your memory fills with pending work. Put a **limit** on how many run at a time. An `asyncio.Semaphore` is the simplest gate. This block starts 60 requests against a local server that records
how many were in flight at once (its code is the module block below), first all together and then through a semaphore of 5:

```python module=slowserver
"""A loopback server whose every answer takes `delay` seconds; it records how many requests were in flight at once."""
import http.server
import threading
import time
from types import SimpleNamespace


def start(delay):
    stats = SimpleNamespace(inflight=0, peak=0, total=0)
    lock = threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        wbufsize = 65536
        disable_nagle_algorithm = True

        def do_GET(self):
            with lock:
                stats.inflight += 1
                stats.total += 1
                stats.peak = max(stats.peak, stats.inflight)
            time.sleep(delay)
            with lock:
                stats.inflight -= 1
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", stats, server.shutdown
```

```python run
import asyncio

import httpx

from slowserver import start


async def main():
    base, stats, stop = start(0.05)
    limits = httpx.Limits(max_connections=100)                       # the client's own ceiling, high enough not to hide the effect
    async with httpx.AsyncClient(base_url=base, timeout=5.0, trust_env=False, limits=limits) as client:      # ONE shared client (PY-M05)

        async def fetch(i):
            return (await client.get(f"/item/{i}")).status_code

        assert set(await asyncio.gather(*(fetch(i) for i in range(60)))) == {200}
        unbounded = stats.peak
        stats.peak = 0

        gate = asyncio.Semaphore(5)

        async def polite(i):
            async with gate:                                         # at most five holders at any moment
                return await fetch(i)

        assert set(await asyncio.gather(*(polite(i) for i in range(60)))) == {200}
        bounded = stats.peak
    stop()
    return unbounded, bounded


unbounded, bounded = asyncio.run(main())
assert unbounded > 20                      # the server saw dozens of simultaneous requests
assert bounded <= 5                        # and never more than five behind the semaphore
```

A semaphore bounds the work in flight but still creates all 60 tasks at once. For a stream of millions of items use a **bounded queue** and a fixed number of workers: `await queue.put(item)` waits when the queue is full, so the producer is slowed down to the speed of the consumers (*backpressure*) and memory stays flat. Workers stop when they receive a sentinel such as `None`
(this works on every supported version; `Queue.shutdown` exists only from 3.13, R-095).

```python run
import asyncio


async def main():
    queue = asyncio.Queue(maxsize=3)
    peak = 0
    done = []

    async def producer():
        nonlocal peak
        for i in range(20):
            await queue.put(i)                       # waits while three items are already queued
            peak = max(peak, queue.qsize())
        for _ in range(2):
            await queue.put(None)                    # one stop signal per worker

    async def consumer():
        while (item := await queue.get()) is not None:
            await asyncio.sleep(0.005)
            done.append(item)

    async with asyncio.TaskGroup() as group:
        group.create_task(producer())
        group.create_task(consumer())
        group.create_task(consumer())
    return peak, sorted(done)


peak, done = asyncio.run(main())
assert peak <= 3 and done == list(range(20))         # the queue never held more than its limit; nothing was lost
```

## 6. Time limits and cancellation (LO3)

Every wait needs a limit (PY-M05, section 5). In `asyncio`, `async with asyncio.timeout(seconds):` cancels the work inside the block when the time is up and raises `TimeoutError` **outside** the block (R-093). Cancellation is delivered as an exception, `asyncio.CancelledError`, raised at the `await` where the task is waiting. Two rules follow.
**Do cleanup in `finally`**, which runs on cancellation too. **Never swallow the cancellation**: `except BaseException:` or a bare `except:` that does not re-raise turns "stop" into "carry on", and the timeout then silently does nothing. `except Exception:` does not catch `CancelledError` (it derives from `BaseException`), which is one reason to catch specific exceptions.

```python run
import asyncio

cleanup = []


async def slow_job():
    try:
        await asyncio.sleep(10)
    finally:
        cleanup.append("closed")                         # runs when the timeout cancels the job


async def swallows_cancellation():
    try:
        await asyncio.sleep(10)
    except BaseException:                                # the defect: this also catches CancelledError
        return "ignored the cancellation"


async def main():
    try:
        async with asyncio.timeout(0.05):
            await slow_job()
    except TimeoutError:
        cleanup.append("TimeoutError")
    assert cleanup == ["closed", "TimeoutError"]         # cleanup ran first, then the error reached the caller

    task = asyncio.create_task(swallows_cancellation())
    await asyncio.sleep(0)
    task.cancel()
    assert await task == "ignored the cancellation" and not task.cancelled()     # cancel() was requested and ignored

    async with asyncio.timeout(0.05):                    # the limit expires, but nothing raises TimeoutError ...
        assert await swallows_cancellation() == "ignored the cancellation"
    return "the timeout was silently defeated"           # ... the program went on as if nothing had happened


assert asyncio.run(main()) == "the timeout was silently defeated"
```

If you must catch `CancelledError` to clean up, **re-raise it** afterwards (the previous section's `worker` does). Distinguish your own timeout from a `TimeoutError` raised by something inside the block: the object returned by `asyncio.timeout(...)` has `expired()`, true only when it was your limit that fired.

## 7. Shared state across `await` points (LO2)

Tasks of one event loop never run at the same time, so many beginners conclude that shared data needs no protection. It does, wherever a task **awaits between reading and writing** it: another task runs in the gap. The next block makes five deposits of 10 and loses four of them; a lock around the read-modify-write fixes it.

```python run
import asyncio


async def deposit(account, amount, lock):
    async def update():
        balance = account["balance"]              # read ...
        await asyncio.sleep(0)                    # ... any await lets another task run here ...
        account["balance"] = balance + amount     # ... then write a value that may be stale

    if lock is None:
        await update()
    else:
        async with lock:
            await update()


async def total(use_lock):
    account = {"balance": 0}
    lock = asyncio.Lock() if use_lock else None
    await asyncio.gather(*(deposit(account, 10, lock) for _ in range(5)))
    return account["balance"]


assert asyncio.run(total(False)) == 10          # four of the five deposits were overwritten
assert asyncio.run(total(True)) == 50
```

The best protection is to **not share**: give each task its own data and combine the results afterwards (the labs return values instead of updating a shared structure). Threads need the same care, with more ways to go wrong, because a thread can be interrupted anywhere, not only at an `await`.

## 8. Threads and processes in practice (LO1)

`concurrent.futures` gives threads and processes one interface. `pool.map(func, items)` returns results in **input order** (even if jobs finish in a different order) and raises a job's exception when you reach its result while iterating; leaving the `with` block waits for the running jobs.

```python run
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def job(n):
    time.sleep(0.05 * (3 - n))                       # job 0 finishes last
    if n == 2:
        raise ValueError("job 2 failed")
    return n * 10


with ThreadPoolExecutor(max_workers=3) as pool:
    results = []
    try:
        for value in pool.map(job, [0, 1, 2]):
            results.append(value)                    # arrives in input order: 0, then 10 ...
    except ValueError as error:
        assert str(error) == "job 2 failed"          # ... and the failure surfaces when its turn comes
assert results == [0, 10]

with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(job, n): n for n in (0, 1, 2)}
    order = [futures[f] for f in as_completed(futures)]      # as_completed: completion order instead
assert order == [2, 1, 0]
```

Processes (`ProcessPoolExecutor`) are the tool for CPU-bound work on several cores, with three costs: arguments and results are **pickled** and copied, so large data is expensive to send; the child must be able to import your function, so code that starts a pool belongs under `if __name__ == "__main__":`; and the **start method** differs by platform and version.
On Linux the default was `fork` until Python 3.13 and is `forkserver` from 3.14 (executed below), on macOS and Windows it is `spawn`; code that relied on a child inheriting your globals through `fork` breaks silently on the other methods.
Python 3.14 also added `concurrent.futures.InterpreterPoolExecutor` and the `concurrent.interpreters` module (separate interpreters in one process) and officially supports the free-threaded build (R-046). The block checks which of these exist on the interpreter running the lesson, so that you know what you can use:

```python run
import asyncio
import concurrent.futures
import importlib.util
import multiprocessing
import sys
import sysconfig

v = sys.version_info[:2]
assert hasattr(asyncio, "TaskGroup") and hasattr(asyncio, "timeout") and hasattr(asyncio, "Runner")          # 3.11 and later
assert hasattr(asyncio, "eager_task_factory") == (v >= (3, 12))
assert hasattr(asyncio.Queue, "shutdown") == (v >= (3, 13))
assert hasattr(sys, "_is_gil_enabled") == (v >= (3, 13))
assert hasattr(concurrent.futures, "InterpreterPoolExecutor") == (v >= (3, 14))
assert (importlib.util.find_spec("concurrent.interpreters") is not None) == (v >= (3, 14))
gil_removed = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))                       # true only for a free-threaded build
assert gil_removed == (hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled())
if sys.platform.startswith("linux"):
    assert multiprocessing.get_start_method() == ("fork" if v < (3, 14) else "forkserver")

import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    try:
        asyncio.get_event_loop()                         # no loop is running: the old way to "get a loop"
        outcome = "returned a loop"
    except RuntimeError:
        outcome = "RuntimeError"
assert outcome == ("returned a loop" if v < (3, 14) else "RuntimeError")
print("checked on", v, "free-threaded" if gil_removed else "standard build")
```

The last assertion records a trap in older tutorials: `asyncio.get_event_loop()` outside a running loop returned a loop on 3.11 to 3.13 and raises `RuntimeError` from 3.14 (R-095). Start programs with `asyncio.run(main())`.

Which to use: waiting on many network calls with an async library, `asyncio` with a limit; waiting with a blocking library, threads; heavy computation, processes (or a free-threaded build once your libraries support it and a benchmark shows a gain); small jobs, none of them. The decision is only credible with a measurement, which is the next section.

## 9. Measuring honestly (LO4)

"3x faster" means nothing without the input, the machine, the number of runs and the spread. A benchmark that deserves trust has five habits: it runs the **same input** for every candidate; it **repeats** and reports the **median** (the middle value, which one slow run cannot move) plus the range; it **interleaves** the candidates (baseline, candidate, baseline, candidate, ...)
so that drift (a busy machine, a warming cache) hits both; it reports the **ratio and both times**, not just the ratio; and it **states what it did not test** (other sizes, other hardware, other latencies). The helper below follows those habits and is the one the guided lab asks you to write:

```python run
import statistics
import time


def median_time(func, repeats):
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def speedup(baseline, candidate, repeats=5):
    base, fast = [], []
    for _ in range(repeats):                               # interleaved: drift affects both candidates alike
        start = time.perf_counter()
        baseline()
        base.append(time.perf_counter() - start)
        start = time.perf_counter()
        candidate()
        fast.append(time.perf_counter() - start)
    return {"baseline_s": statistics.median(base), "candidate_s": statistics.median(fast), "ratio": statistics.median(base) / statistics.median(fast),
            "baseline_range_s": (min(base), max(base)), "candidate_range_s": (min(fast), max(fast)), "repeats": repeats}


slow = lambda: time.sleep(0.04)
quick = lambda: time.sleep(0.01)
report = speedup(slow, quick, repeats=5)
assert 0.035 <= report["baseline_s"] < 0.2 and 0.009 <= report["candidate_s"] < 0.1       # medians of known waits
assert 2.5 <= report["ratio"] <= 4.5 and report["repeats"] == 5
assert report["baseline_range_s"][0] <= report["baseline_s"] <= report["baseline_range_s"][1]
assert median_time(lambda: time.sleep(0.01), 3) >= 0.009

n, serial_fraction = 50, 0.2                               # Amdahl's law: the part that cannot overlap limits the gain
limit = 1 / (serial_fraction + (1 - serial_fraction) / n)
assert 4.5 < limit < 5.0                                   # fifty tasks, at most about five times faster
```

Report a speed-up like this: "median 0.84 s sequential, 0.11 s concurrent with limit 8 (7.6x), 5 runs each, 80 documents of 50 ms latency on a local server; not tested with real network latency or more than 80 documents." That sentence can be checked and repeated; "SECONDS" cannot. If the ratio is close to 1, say so: a concurrent version that is not faster, or that is only faster at sizes you do not use, is a result, not a failure of the experiment.

## 10. Failure, partial results and shutdown (LO5)

Real batches fail partially. Decide the policy for each job type and make it visible in the return value. A common design returns one **outcome** per input, in input order, holding either the value or the error, so the caller can store the successes, retry the failures later and report both. The code stays honest about three things:
**cancellation is not a failure** (let `CancelledError` propagate, do not record it as an item error); **no task outlives its supervisor** (a `TaskGroup` guarantees it; after `gather` you must check yourself); and **shutdown waits for cleanup** (a task cancelled at 3 a.m. still has to close its connection).

```python run
import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class Outcome:
    item: Any
    value: Any = None
    error: Exception | None = None

    @property
    def ok(self):
        return self.error is None


async def run_collect(func, items, limit):
    gate = asyncio.Semaphore(limit)
    outcomes = [Outcome(item) for item in items]

    async def one(outcome):
        async with gate:
            try:
                outcome.value = await func(outcome.item)
            except Exception as error:                       # Exception, not BaseException: cancellation must pass through
                outcome.error = error

    async with asyncio.TaskGroup() as group:
        for outcome in outcomes:
            group.create_task(one(outcome))
    return outcomes


async def flaky(n):
    await asyncio.sleep(0.01)
    if n % 3 == 0:
        raise ValueError(f"item {n} is bad")
    return n * n


async def main():
    outcomes = await run_collect(flaky, range(7), limit=3)
    assert [o.item for o in outcomes] == list(range(7))                              # input order
    assert [o.value for o in outcomes if o.ok] == [1, 4, 16, 25]
    assert [str(o.error) for o in outcomes if not o.ok] == ["item 0 is bad", "item 3 is bad", "item 6 is bad"]
    assert len(asyncio.all_tasks()) == 1                                             # only main() itself is still alive

    job = asyncio.create_task(run_collect(flaky, range(100), limit=2))
    await asyncio.sleep(0.03)
    job.cancel()                                                                     # shutting down in the middle of the batch
    try:
        await job
    except asyncio.CancelledError:
        pass
    assert job.cancelled() and len(asyncio.all_tasks()) == 1                         # every worker was cancelled and awaited


asyncio.run(main())
```

## 11. What changed since the 2025 handbook

Verified on 2026-10-14 (executed in this lesson or recorded in the register):

| 2025 handbook | Now |
|---|---|
| "3x faster execution with minimal effort" (p. 135) and "1000 requests happen in SECONDS ... impossible with regular code" (p. 136), no measurements | Speed-ups are measured and reported with the input, the runs and the spread (section 9); threads and processes also run many requests at once. |
| One `AsyncClient` per task, 1000 tasks at once, no timeout, `gather` without error handling (p. 136, p. 177) | One shared client, a semaphore or bounded queue, an explicit timeout, and `TaskGroup` (3.11) or outcome objects for errors. |
| `asyncio.gather` as the way to run tasks together | `gather` leaves siblings running after a failure (R-093); `TaskGroup` cancels them. |
| `pip install httpx asyncio` (p. 177) | `asyncio` is in the standard library; the PyPI project is a deprecated, code-free placeholder (R-094). |
| "The GIL blocks CPU-bound threads but not I/O-bound threads" as the whole story (p. 134) | True on standard builds; the free-threaded build is officially supported from 3.14 (R-046), and subinterpreters are in the standard library from 3.14 (R-095). |
| `asyncio.get_event_loop()` to obtain a loop (common in tutorials) | Raises `RuntimeError` without a running loop from 3.14; use `asyncio.run` (R-095). |
| Processes assumed to inherit state (`fork`) | The default start method on Linux is `forkserver` from 3.14 (executed); `spawn` on macOS and Windows. |

## 12. Common misconceptions

| Misconception | Reality |
|---|---|
| "`async` makes code faster." | It lets waits overlap. CPU-bound code in a coroutine is not faster, and it blocks the loop. |
| "`gather` and `TaskGroup` are the same." | `gather` does not cancel siblings when one fails and does not supervise them; `TaskGroup` does both. |
| "Tasks cannot race because there is one thread." | A race needs only an `await` between a read and a write. |
| "More concurrency is always faster." | Past the server's or the pool's capacity it is slower, and it can get you blocked. Choose a limit and measure. |
| "`except Exception` is too narrow for cleanup." | Cleanup belongs in `finally`; catching `BaseException` swallows cancellation and defeats timeouts. |
| "A fire-and-forget task will run to the end." | The loop holds tasks weakly; keep a reference or use a `TaskGroup`. |
| "Threads are useless in Python." | They help with blocking I/O on every build, and on a free-threaded build they can help with computation. |

## 13. Practice and assessment

| Step | What | Where |
|---|---|---|
| Guided lab (LO1-LO5) | Implement six functions in `jobrunner.py` until the provided checks pass: bounded runs, collected outcomes, timeouts, a queue with workers, and a benchmark helper | `lab-guided/README.md` |
| Independent lab (LO1-LO5) | Write `count_words` and a benchmark script from a written specification; instructors run a larger hidden suite that measures concurrency, speed-up, failures and cancellation | `lab-independent/README.md` |
| Knowledge check | 8 questions tied to the outcomes (answers are held by instructors) | `assessment/quiz.md` |
| Rubric | Published criteria for the independent lab | `assessment/rubric.yaml` |

## 14. Summary

- Choose the tool from the profile: waits overlap with threads or `asyncio`, computation needs processes (or a free-threaded build); measure before you believe a claim.
- Never block the event loop; use `asyncio.to_thread` for blocking calls; share nothing across `await` points or lock it.
- Prefer `TaskGroup` to `gather`; keep references to tasks; use `asyncio.timeout` and `finally`; never swallow `CancelledError`.
- Bound concurrency with a semaphore or a bounded queue; one shared client; a timeout on every call.
- Report speed-ups as medians of interleaved repeats with the input and the limits stated; return per-job outcomes for partial failure and leave no task behind.

## References

- Python documentation, *Coroutines and Tasks* (R-093); *What's New In Python 3.14* (R-046); registry snapshot of 2026-10-14 (R-045).
- Executed evidence: asyncio and concurrency features by CPython version (R-095) and the `pypi-asyncio-placeholder` probe (R-094); every block of this lesson is executed by the repository tests on CPython 3.11-3.15.
- Findings and change records addressed: F-PYH-010 (unmeasured speed claims, unbounded and unsupervised async patterns, `pip install asyncio`), F-PYH-009 (client per request, no timeouts), F-PYH-004 (listings not executed), F-PYH-007 (assessment by recall questions only), MC-PYH-16 and MC-PYH-20.
