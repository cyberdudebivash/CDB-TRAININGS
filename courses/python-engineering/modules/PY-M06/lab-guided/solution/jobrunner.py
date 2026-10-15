"""jobrunner - bounded, supervised concurrency and honest benchmarks.

PY-M06 guided lab, correct reference version.
"""
from __future__ import annotations

import asyncio
import statistics
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any


class JobTimeout(Exception):
    """One job ran longer than its time limit."""

    def __init__(self, item: Any, seconds: float) -> None:
        super().__init__(f"{item!r} exceeded {seconds} s")
        self.item = item
        self.seconds = seconds


@dataclass
class Outcome:
    item: Any
    value: Any = None
    error: Exception | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class Speedup:
    baseline_s: float          # median time of the baseline
    candidate_s: float         # median time of the candidate
    ratio: float               # baseline_s / candidate_s
    repeats: int


def _check_limit(name: str, value: int) -> None:
    if value < 1:
        raise ValueError(f"{name} must be at least 1")


async def run_bounded(func: Callable[[Any], Awaitable[Any]], items: Iterable[Any], *, limit: int) -> list[Any]:
    """Run `func(item)` for every item, at most `limit` at a time; return the results in input order; the first failure cancels the rest and is raised as itself."""
    _check_limit("limit", limit)
    items = list(items)
    gate = asyncio.Semaphore(limit)
    results: list[Any] = [None] * len(items)

    async def one(index: int, item: Any) -> None:
        async with gate:
            results[index] = await func(item)

    failure: Exception | None = None
    try:
        async with asyncio.TaskGroup() as group:
            for index, item in enumerate(items):
                group.create_task(one(index, item))
    except* Exception as failures:                       # return and raise inside except* would be wrapped again: remember it, raise below
        failure = failures.exceptions[0]
    if failure is not None:
        raise failure
    return results


async def run_collect(func: Callable[[Any], Awaitable[Any]], items: Iterable[Any], *, limit: int) -> list[Outcome]:
    """Run `func(item)` for every item, at most `limit` at a time; return one Outcome per item, in input order; a failing item never stops the others."""
    _check_limit("limit", limit)
    outcomes = [Outcome(item) for item in items]
    gate = asyncio.Semaphore(limit)

    async def one(outcome: Outcome) -> None:
        async with gate:
            try:
                outcome.value = await func(outcome.item)
            except Exception as error:                   # not BaseException: a cancellation must pass through
                outcome.error = error

    async with asyncio.TaskGroup() as group:
        for outcome in outcomes:
            group.create_task(one(outcome))
    return outcomes


async def call_with_timeout(func: Callable[[Any], Awaitable[Any]], item: Any, seconds: float) -> Any:
    """Return `await func(item)`, or raise JobTimeout(item, seconds) once `seconds` have passed (after the call has been cancelled and its cleanup has run)."""
    try:
        async with asyncio.timeout(seconds) as limit:
            return await func(item)
    except TimeoutError:
        if limit.expired():                              # our limit fired, not a TimeoutError raised by func itself
            raise JobTimeout(item, seconds) from None
        raise


async def process_queue(items: Iterable[Any], handler: Callable[[Any], Awaitable[Any]], *, workers: int, queue_size: int) -> list[Any]:
    """Feed `items` through a bounded queue to `workers` tasks that call `handler`; return the results in input order; the first failure cancels the rest and is raised as itself."""
    _check_limit("workers", workers)
    _check_limit("queue_size", queue_size)
    queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
    results: dict[int, Any] = {}
    count = 0

    async def producer() -> None:
        nonlocal count
        for index, item in enumerate(items):
            await queue.put((index, item))               # waits while the queue is full: the input is read no faster than it is consumed
            count = index + 1
        for _ in range(workers):
            await queue.put(None)                        # one stop signal per worker

    async def worker() -> None:
        while (job := await queue.get()) is not None:
            index, item = job
            results[index] = await handler(item)

    failure: Exception | None = None
    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(producer())
            for _ in range(workers):
                group.create_task(worker())
    except* Exception as failures:
        failure = failures.exceptions[0]
    if failure is not None:
        raise failure
    return [results[i] for i in range(count)]


def median_time(func: Callable[[], Any], repeats: int) -> float:
    """Call `func()` `repeats` times and return the median wall-clock time in seconds."""
    _check_limit("repeats", repeats)
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def speedup(baseline: Callable[[], Any], candidate: Callable[[], Any], *, repeats: int = 3) -> Speedup:
    """Time `baseline` and `candidate` alternately (baseline, candidate, baseline, ...) `repeats` times each and compare their medians."""
    _check_limit("repeats", repeats)
    base: list[float] = []
    fast: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        baseline()
        base.append(time.perf_counter() - start)
        start = time.perf_counter()
        candidate()
        fast.append(time.perf_counter() - start)
    base_s, fast_s = statistics.median(base), statistics.median(fast)
    return Speedup(base_s, fast_s, base_s / fast_s, repeats)
