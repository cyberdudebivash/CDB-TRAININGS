"""streamkit - lazy pipelines, decorators and context managers (PY-M13 guided lab).

Five steps (A to E, see README.md). The names, the docstrings and the dataclass `Event` are given; every body that raises NotImplementedError is yours.
Each docstring is the specification and checks/ holds the tests, one file per step: `python -m pytest checks/test_step_a_read_lines.py` runs step A.
Edit only this file.
"""
from __future__ import annotations

import contextlib
import functools
import os
import time
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------------------------------- step A: generators that own a resource
def read_lines(path: str) -> Iterator[str]:
    """Yield the lines of a UTF-8 text file without their line ending, one at a time.

    Lazy: the file is not opened until the first item is requested. The file is closed when the generator is exhausted, closed with .close() or garbage collected,
    and when the consumer raises: open it with a `with` block *inside* the generator.
    """
    raise NotImplementedError("step A")


# ---------------------------------------------------------------------------------------------------- step B: a lazy transformation
@dataclass(frozen=True, slots=True)
class Event:
    """One parsed log line: '<seconds> <LEVEL> <message...>' with seconds an integer and LEVEL one of INFO, WARN, ERROR (given)."""

    seconds: int
    level: str
    message: str


def parse_line(line: str) -> Event:
    """Parse one line; ValueError (with the line in the message, as repr) if it does not have the three parts, the seconds are not ASCII digits, the level is not one of
    INFO, WARN, ERROR (exactly, upper case) or the message is empty or only spaces. Split on single spaces: the message is everything after the second space."""
    raise NotImplementedError("step B")


def parse_events(lines: Iterable[str], bad: list[str] | None = None) -> Iterator[Event]:
    """Yield an Event for every parsable line and skip the others. If `bad` is a list, append every skipped line to it. Lazy: consume one input line per item produced (or skipped)."""
    raise NotImplementedError("step B")


# ---------------------------------------------------------------------------------------------------- step C: arguments are checked now, items later
def chunks(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield lists of `size` items; the last list may be shorter; nothing is yielded for an empty input.

    `size` must be an int (not a bool) of at least 1: TypeError / ValueError are raised **when chunks() is called**, not when the first chunk is requested
    (a generator function would defer the check; return an inner generator instead). Lazy: never read more than the items of the chunk being built.
    """
    raise NotImplementedError("step C")


def windows(iterable: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    """Yield every run of `size` consecutive items as a tuple (a sliding window); nothing if the input is shorter than `size`. Same argument checks and laziness as chunks()."""
    raise NotImplementedError("step C")


def take(iterable: Iterable[T], n: int) -> list[T]:
    """The first `n` items as a list, consuming no more than `n` items from the input (n == 0 consumes nothing); the rest of an iterator stays available. ValueError if n is negative."""
    raise NotImplementedError("step C")


def dedupe(iterable: Iterable[T], key: Callable[[T], Any] | None = None) -> Iterator[T]:
    """Yield each item the first time its key (default: the item itself) is seen, in input order. Lazy; works on infinite input."""
    raise NotImplementedError("step C")


# ---------------------------------------------------------------------------------------------------- step D: decorators that keep what they wrap
def retry(times: int, *, on: tuple[type[BaseException], ...] = (Exception,), sleep: Callable[[float], object] = time.sleep, delay: float = 0.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory: call the function up to `times` times (at least 1) until it returns; retry only when it raises one of `on`.

    Between attempts call `sleep(delay)` (not after the last one). When all attempts fail raise the **last** exception. Arguments and the return value pass through
    unchanged and the wrapper keeps the name and docstring of the function (functools.wraps). An exception that is not in `on` (for example KeyboardInterrupt) propagates at once.
    ValueError for times < 1 and TypeError for a non-int or bool, raised when retry(...) is called (before the decorator is applied).
    """
    raise NotImplementedError("step D")


def counted(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator: the wrapper has an attribute `calls`, the number of times it was called (also when the call raised); arguments, return value, name and docstring are preserved."""
    raise NotImplementedError("step D")


def once(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator: run the function on the first call only; every later call returns the first result without calling it (arguments of later calls are ignored; a result of None counts).

    If the first call raises, nothing is remembered and the next call tries again. Name and docstring are preserved.
    """
    raise NotImplementedError("step D")


# ---------------------------------------------------------------------------------------------------- step E: context managers that clean up on every path
class temp_env:
    """Set environment variables for the duration of a `with` block and restore the previous state afterwards - also when the block raises.

    temp_env(NAME="value", OTHER=None): a value sets the variable, None removes it for the duration. Variables that did not exist are removed again; variables that did
    exist (an empty string counts as existing) get their old value back. Values must be str or None (TypeError raised at construction, before anything is changed).
    Exceptions from the block are never suppressed. __enter__ returns the context manager itself.
    """

    def __init__(self, **changes: str | None) -> None:
        raise NotImplementedError("step E")

    def __enter__(self) -> "temp_env":
        raise NotImplementedError("step E")

    def __exit__(self, exc_type, exc, traceback) -> bool:
        raise NotImplementedError("step E")


class Stopwatch:
    """The object a timer() block receives (given)."""

    def __init__(self) -> None:
        self.elapsed: float | None = None


@contextlib.contextmanager
def timer(clock: Callable[[], float] = time.perf_counter) -> Iterator[Stopwatch]:
    """Measure a block: `with timer() as t: ...`; t.elapsed is the seconds between entering and leaving (also when the block raised) and None while the block is running.

    `clock` is injected so that tests need no real time; call it exactly twice. Exceptions from the block are never suppressed.
    """
    raise NotImplementedError("step E")
    yield Stopwatch()          # keeps this function a generator; replace the whole body


@contextlib.contextmanager
def collecting(*exceptions: type[Exception]) -> Iterator[list[Exception]]:
    """Run a block, catch the listed exception types, append the caught exception to the list the block receives and carry on after the block. Other exceptions propagate unchanged.

    `with collecting(ValueError) as errors:` - at most one exception can occur in a block, so the list has zero or one item. Anything that is not an Exception subclass is refused
    with TypeError **when the with statement starts** (the body of a @contextmanager function runs at entry, not at the call): `collecting(KeyboardInterrupt)` is almost always a mistake.
    """
    raise NotImplementedError("step E")
    yield []                   # keeps this function a generator; replace the whole body


def close_all(*resources: Any) -> Callable[[], None]:
    """Return a function that closes every resource (anything with .close()), in reverse order, even if some of the closes raise.

    If any close raised, the exception of the **last failing close** propagates (that is what contextlib.ExitStack does and the checks accept nothing else); the function
    closes nothing the second time it is called. A small use of ExitStack: register each resource's close with stack.callback and return stack.close.
    """
    raise NotImplementedError("step E")
