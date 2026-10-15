"""jobrunner - bounded, supervised concurrency and honest benchmarks.

PY-M06 guided lab starter: the types are given; implement the functions below.
"""
from __future__ import annotations

import asyncio
import statistics  # noqa: F401  (for median_time)
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
    """Raise ValueError('<name> must be at least 1') for a value below 1."""
    if value < 1:
        raise ValueError(f"{name} must be at least 1")


async def run_bounded(func: Callable[[Any], Awaitable[Any]], items: Iterable[Any], *, limit: int) -> list[Any]:
    """Run `await func(item)` for every item with at most `limit` running at a time and return the results in input order.
    The first failure cancels everything still running and is raised AS ITSELF (not wrapped in an ExceptionGroup); when the function returns or raises, none of its tasks is left running.
    If the caller is cancelled, every job is cancelled. `limit` below 1 raises ValueError('limit must be at least 1'). `items` may be any iterable."""
    raise NotImplementedError("step A: run_bounded")


async def run_collect(func: Callable[[Any], Awaitable[Any]], items: Iterable[Any], *, limit: int) -> list[Outcome]:
    """Like run_bounded, but a failing item never stops the others: return one Outcome per item (in input order) holding the value or the Exception.
    Only Exception subclasses are recorded; a cancellation of the caller cancels every job and propagates. Same `limit` rule."""
    raise NotImplementedError("step B: run_collect")


async def call_with_timeout(func: Callable[[Any], Awaitable[Any]], item: Any, seconds: float) -> Any:
    """Return `await func(item)`; if `seconds` pass first, cancel the call (its `finally` blocks run) and raise JobTimeout(item, seconds).
    A TimeoutError that `func` raises by itself, and any other exception, propagate unchanged: only YOUR limit becomes JobTimeout."""
    raise NotImplementedError("step C: call_with_timeout")


async def process_queue(items: Iterable[Any], handler: Callable[[Any], Awaitable[Any]], *, workers: int, queue_size: int) -> list[Any]:
    """Producer/consumer: one task reads `items` and puts them on an asyncio.Queue(maxsize=queue_size); `workers` tasks take them and call `await handler(item)`.
    Return the results in input order. The input is read lazily: no more than workers + queue_size + 1 items may have been taken from it while every handler is busy.
    The first failure cancels the rest and is raised as itself. `workers` and `queue_size` below 1 raise ValueError('<name> must be at least 1')."""
    raise NotImplementedError("step D: process_queue")


def median_time(func: Callable[[], Any], repeats: int) -> float:
    """Call `func()` `repeats` times, timing each call with time.perf_counter, and return the median in seconds. `repeats` below 1 raises ValueError('repeats must be at least 1')."""
    raise NotImplementedError("step E: median_time")


def speedup(baseline: Callable[[], Any], candidate: Callable[[], Any], *, repeats: int = 3) -> Speedup:
    """Time `baseline` and `candidate` ALTERNATELY (baseline, candidate, baseline, candidate, ...) `repeats` times each, so that drift hits both alike,
    and return Speedup(median of the baseline times, median of the candidate times, their ratio baseline/candidate, repeats). Same `repeats` rule."""
    raise NotImplementedError("step F: speedup")
