"""streamkit - lazy pipelines, decorators and context managers (PY-M13 guided lab).

Public reference solution. The starter has the same names; the docstrings are the specification and checks/ holds the tests, one file per step.
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
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            yield line.rstrip("\r\n")


# ---------------------------------------------------------------------------------------------------- step B: a lazy transformation
@dataclass(frozen=True, slots=True)
class Event:
    """One parsed log line: '<seconds> <LEVEL> <message...>' with seconds an integer and LEVEL one of INFO, WARN, ERROR."""

    seconds: int
    level: str
    message: str


_LEVELS = frozenset({"INFO", "WARN", "ERROR"})


def parse_line(line: str) -> Event:
    """Parse one line; ValueError (with the line in the message) if it does not have the three parts, the seconds are not ASCII digits or the level is unknown."""
    parts = line.split(" ", 2)
    if len(parts) != 3 or not (parts[0].isascii() and parts[0].isdigit()) or parts[1] not in _LEVELS or not parts[2].strip():
        raise ValueError(f"malformed log line: {line!r}")
    return Event(int(parts[0]), parts[1], parts[2])


def parse_events(lines: Iterable[str], bad: list[str] | None = None) -> Iterator[Event]:
    """Yield an Event for every parsable line and skip the others. If `bad` is a list, append every skipped line to it. Lazy: consume one input line per item produced (or skipped)."""
    for line in lines:
        try:
            event = parse_line(line)
        except ValueError:
            if bad is not None:
                bad.append(line)
            continue
        yield event


# ---------------------------------------------------------------------------------------------------- step C: arguments are checked now, items later
def chunks(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield lists of `size` items; the last list may be shorter; nothing is yielded for an empty input.

    `size` must be an int (not a bool) of at least 1: TypeError / ValueError are raised **when chunks() is called**, not when the first chunk is requested
    (a generator function would defer the check; return an inner generator instead). Lazy: never read more than the items of the chunk being built.
    """
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an int")
    if size < 1:
        raise ValueError("size must be at least 1")
    return _chunks(iter(iterable), size)


def _chunks(iterator: Iterator[T], size: int) -> Iterator[list[T]]:
    while True:
        chunk = []
        for item in iterator:
            chunk.append(item)
            if len(chunk) == size:
                break
        if not chunk:
            return
        yield chunk
        if len(chunk) < size:
            return


def windows(iterable: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    """Yield every run of `size` consecutive items as a tuple (a sliding window); nothing if the input is shorter than `size`. Same argument checks and laziness as chunks()."""
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an int")
    if size < 1:
        raise ValueError("size must be at least 1")
    return _windows(iter(iterable), size)


def _windows(iterator: Iterator[T], size: int) -> Iterator[tuple[T, ...]]:
    window: deque[T] = deque(maxlen=size)
    for item in iterator:
        window.append(item)
        if len(window) == size:
            yield tuple(window)


def take(iterable: Iterable[T], n: int) -> list[T]:
    """The first `n` items as a list, consuming no more than `n` items from the input (n == 0 consumes nothing). ValueError if n is negative."""
    if n < 0:
        raise ValueError("n must not be negative")
    iterator = iter(iterable)
    out: list[T] = []
    while len(out) < n:
        try:
            out.append(next(iterator))
        except StopIteration:
            break
    return out


def dedupe(iterable: Iterable[T], key: Callable[[T], Any] | None = None) -> Iterator[T]:
    """Yield each item the first time its key (default: the item itself) is seen, in input order. Lazy."""
    seen: set[Any] = set()
    for item in iterable:
        marker = item if key is None else key(item)
        if marker not in seen:
            seen.add(marker)
            yield item


# ---------------------------------------------------------------------------------------------------- step D: decorators that keep what they wrap
def retry(times: int, *, on: tuple[type[BaseException], ...] = (Exception,), sleep: Callable[[float], object] = time.sleep, delay: float = 0.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory: call the function up to `times` times (at least 1) until it returns; retry only when it raises one of `on`.

    Between attempts call `sleep(delay)` (not after the last one). When all attempts fail raise the **last** exception. Arguments and the return value pass through
    unchanged and the wrapper keeps the name and docstring of the function (functools.wraps). An exception that is not in `on` (for example KeyboardInterrupt) propagates at once.
    ValueError for times < 1 and TypeError for a non-int or bool, raised when retry(...) is called.
    """
    if isinstance(times, bool) or not isinstance(times, int):
        raise TypeError("times must be an int")
    if times < 1:
        raise ValueError("times must be at least 1")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except on:
                    if attempt == times:
                        raise
                    sleep(delay)
            raise AssertionError("unreachable")

        return wrapper

    return decorator


def counted(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator: the wrapper has an attribute `calls`, the number of times it was called (also when the call raised); arguments, return value, name and docstring are preserved."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        wrapper.calls += 1                              # type: ignore[attr-defined]
        return func(*args, **kwargs)

    wrapper.calls = 0                                   # type: ignore[attr-defined]
    return wrapper


def once(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator: run the function on the first call only; every later call returns the first result without calling it (arguments of later calls are ignored).

    If the first call raises, nothing is remembered and the next call tries again. Name and docstring are preserved.
    """
    sentinel = object()
    result: Any = sentinel

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        nonlocal result
        if result is sentinel:
            result = func(*args, **kwargs)
        return result

    return wrapper


# ---------------------------------------------------------------------------------------------------- step E: context managers that clean up on every path
class temp_env:
    """Set environment variables for the duration of a `with` block and restore the previous state afterwards - also when the block raises.

    temp_env(NAME="value", OTHER=None): a value sets the variable, None removes it for the duration. Variables that did not exist are removed again; variables that did
    exist get their old value back. Names and values must be str (TypeError otherwise, raised at construction). Exceptions from the block are never suppressed.
    """

    def __init__(self, **changes: str | None) -> None:
        for name, value in changes.items():
            if value is not None and not isinstance(value, str):
                raise TypeError(f"environment value of {name} must be str or None")
        self._changes = dict(changes)
        self._saved: dict[str, str | None] = {}

    def __enter__(self) -> "temp_env":
        for name, value in self._changes.items():
            self._saved[name] = os.environ.get(name)
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        for name, old in self._saved.items():
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
        self._saved.clear()
        return False


@contextlib.contextmanager
def timer(clock: Callable[[], float] = time.perf_counter) -> Iterator["Stopwatch"]:
    """Measure a block: `with timer() as t: ...`; t.elapsed is the seconds between entering and leaving (also when the block raised) and None while the block is running.

    `clock` is injected so that tests need no real time. Exceptions from the block are never suppressed.
    """
    stopwatch = Stopwatch()
    start = clock()
    try:
        yield stopwatch
    finally:
        stopwatch.elapsed = clock() - start


class Stopwatch:
    """The object a timer() block receives."""

    def __init__(self) -> None:
        self.elapsed: float | None = None


@contextlib.contextmanager
def collecting(*exceptions: type[Exception]) -> Iterator[list[Exception]]:
    """Run a block, catch the listed exception types, append each to the list the block receives and carry on after the block. Other exceptions propagate unchanged.

    `with collecting(ValueError) as errors:` - at most one exception can occur in a block, so the list has zero or one item. Anything that is not an Exception subclass is refused
    with TypeError **when the with statement starts** (the body of a @contextmanager function runs at entry, not at the call): `collecting(KeyboardInterrupt)` is almost always a mistake.
    """
    for kind in exceptions:
        if not (isinstance(kind, type) and issubclass(kind, Exception)):
            raise TypeError(f"{kind!r} is not an Exception subclass")
    caught: list[Exception] = []
    try:
        yield caught
    except exceptions as exc:
        caught.append(exc)


def close_all(*resources: Any) -> Callable[[], None]:
    """Return a function that closes every resource (anything with .close()), in reverse order, even if some of the closes raise.

    If any close raised, the exception of the **last failing close** propagates (that is what contextlib.ExitStack does and the checks accept nothing else); the function
    closes nothing the second time it is called. A small use of ExitStack: register each resource's close with stack.callback and return stack.close.
    """
    stack = contextlib.ExitStack()
    for resource in resources:
        stack.callback(resource.close)
    return stack.close
