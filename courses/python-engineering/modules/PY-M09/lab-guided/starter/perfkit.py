"""perfkit - find a bottleneck with a profiler, fix it without changing the answers, and keep the program easy to change (PY-M09 guided lab, STARTER).

The program digests a log of login attempts (one per line: '<ISO time>Z <ip> <user> OK|FAIL'): how many attempts, how many failed, which addresses made at least
`threshold` failures within `window` seconds, which users failed most. It WORKS and gives the right answers, but slowly: `checks/slow_baseline.py` holds a copy that the checks
use as the oracle. Your job, in order (README.md):

  A, B  write the profiling helpers (`Profile.top`, `profile`, `hotspot`) and use them to see where the time goes
  C, D  make the functions below scale (the parts that raise NotImplementedError are yours to write; the slow ones are yours to speed up) without changing a single answer
  E     use less memory
  F     keep the core free of input and output; write the edge (`FileSource.lines`, `main`)

Edit only this file. Standard library only.
"""
from __future__ import annotations

import argparse
import cProfile
import pstats
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, TextIO

PATTERN = r"(\d{4}-\d\d-\d\d)T(\d\d):(\d\d):(\d\d)Z (\d{1,3}(?:\.\d{1,3}){3}) ([A-Za-z0-9_.-]+) (OK|FAIL)"


# ------------------------------------------------------------------------------------------------------------------------------------- values (given)
@dataclass(frozen=True, slots=True)
class Attempt:
    ts: int            # seconds since 1970-01-01T00:00:00Z
    ip: str
    user: str
    ok: bool


@dataclass(frozen=True, slots=True)
class Report:
    attempts: int
    malformed: int
    failures: int
    unique_ips: int
    flagged: tuple[str, ...]
    top_users: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class ProfileRow:
    name: str          # the function as pstats names it: 'top_users', '<genexpr>', "<method 'count' of 'list' objects>"
    file: str          # base name of the source file; '~' for built-in functions
    line: int
    ncalls: int        # every call, recursive ones included
    tottime: float     # seconds spent in the function itself
    cumtime: float     # seconds spent in the function and in everything it called


# ------------------------------------------------------------------------------------------------------------------------------------- step A
@dataclass(frozen=True, slots=True)
class Profile:
    rows: tuple[ProfileRow, ...]      # all functions seen, ordered by tottime (largest first), ties by (file, line, name)
    total_calls: int
    total_time: float

    def top(self, n: int = 5, by: str = "tottime") -> tuple[ProfileRow, ...]:
        """The `n` rows with the largest `by` ('tottime', 'cumtime' or 'ncalls'), largest first, ties by (file, line, name). ValueError for another `by` or a negative n."""
        raise NotImplementedError("step A: Profile.top")


def profile(func: Any, /, *args: Any, **kwargs: Any) -> tuple[Any, Profile]:
    """Call `func(*args, **kwargs)` under cProfile and return (its result, a Profile of the call).

    The profiler is switched off again when the call raises, and the exception propagates unchanged. `ncalls` counts every call (recursion included), so profiling a
    function that calls itself recursively gives the same totals on every run and every interpreter: unlike times, call counts do not depend on the machine.
    Build the rows from `pstats.Stats(profiler).stats` (a dict: (filename, line, name) -> (primitive calls, calls, tottime, cumtime, callers)); `file` is the base name of
    `filename`; sort the rows by tottime, largest first, ties by (file, line, name); `total_calls` and `total_time` are `Stats.total_calls` and `Stats.total_tt`.
    """
    raise NotImplementedError("step A: profile")


# ------------------------------------------------------------------------------------------------------------------------------------- step B
def hotspot(prof: Profile, file: str, exclude: Iterable[str] = ()) -> str:
    """The name of the function of `file` (its base name, e.g. 'perfkit.py') with the largest cumulative time, leaving out the names in `exclude` (the entry point itself
    always has the largest cumulative time and tells you nothing). Ties go to the smaller name. ValueError if no row qualifies."""
    raise NotImplementedError("step B: hotspot")


# ------------------------------------------------------------------------------------------------------------------------------------- steps C, D and E: slow but correct
def parse_line(line: str) -> Attempt | None:
    """The Attempt in `line`, or None when the line is malformed: the format of PATTERN around the whole stripped line, every octet of the address 0 to 255, hour below 24,
    minute and second below 60, and a real calendar date. (Step E: equal addresses and user names should share one string object, see `sys.intern`.)"""
    m = re.compile("^" + PATTERN + "$").match(line.strip())
    if m is None:
        return None
    date, hh, mm, ss, ip, user, result = m.groups()
    if int(hh) > 23 or int(mm) > 59 or int(ss) > 59:
        return None
    if any(int(octet) > 255 for octet in ip.split(".")):
        return None
    try:
        midnight = int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None
    return Attempt(midnight + int(hh) * 3600 + int(mm) * 60 + int(ss), ip, user, result == "OK")


def unique_ips(attempts: Iterable[Attempt]) -> list[str]:
    """The addresses in order of first appearance, each once."""
    seen = []
    for a in attempts:
        if a.ip not in seen:
            seen.append(a.ip)
    return seen


def failures_by_ip(attempts: Iterable[Attempt]) -> dict[str, int]:
    """{address: number of failed attempts} for the addresses with at least one failure, in order of first appearance of the address among ALL attempts."""
    attempts = list(attempts)
    ips = unique_ips(attempts)
    fails = [a.ip for a in attempts if not a.ok]
    return {ip: fails.count(ip) for ip in ips if fails.count(ip) > 0}


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive int")
    return value


def bursts(attempts: Iterable[Attempt], threshold: int, window: int) -> list[str]:
    """The addresses with at least `threshold` FAILED attempts inside some window of `window` seconds (times t with start <= t < start + window; the attempts need not be
    in time order), in order of first appearance of the address among ALL attempts. ValueError unless `threshold` and `window` are positive ints."""
    _positive(threshold, "threshold")
    _positive(window, "window")
    attempts = list(attempts)
    flagged = []
    for ip in unique_ips(attempts):
        times = sorted(a.ts for a in attempts if a.ip == ip and not a.ok)
        for i in range(len(times)):
            if len([t for t in times if times[i] <= t < times[i] + window]) >= threshold:
                flagged.append(ip)
                break
    return flagged


def top_users(attempts: Iterable[Attempt], n: int) -> list[tuple[str, int]]:
    """The `n` users with the most FAILED attempts as (user, count), most first, equal counts in alphabetical order; users without a failure never appear. ValueError for a negative n."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative int")
    attempts = list(attempts)
    users = sorted({a.user for a in attempts})
    counts = {u: sum(1 for a in attempts if a.user == u and not a.ok) for u in users}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [kv for kv in ranked if kv[1] > 0][:n]


# ------------------------------------------------------------------------------------------------------------------------------------- core: the whole analysis
def render(report: Report) -> str:
    """The report as text: one 'name: value' line each for attempts, malformed, failures, unique ips and flagged ('none' when empty, otherwise the addresses joined by ', '),
    then one 'user NAME: COUNT' line per entry of top_users; every line ends with a newline."""
    out = ""
    out += f"attempts: {report.attempts}\n"
    out += f"malformed: {report.malformed}\n"
    out += f"failures: {report.failures}\n"
    out += f"unique ips: {report.unique_ips}\n"
    out += "flagged: " + (", ".join(report.flagged) or "none") + "\n"
    for user, count in report.top_users:
        out += f"user {user}: {count}\n"
    return out


def analyze(lines: Iterable[str], threshold: int = 5, window: int = 60, top: int = 3) -> Report:
    """Digest `lines` (any iterable of text): count and sort out the malformed ones, then compute the report. The answers must stay exactly those of the slow program.
    Step E: read the lines once and do not keep them; use less memory than `checks/slow_baseline.py` at the same input."""
    _positive(threshold, "threshold")
    _positive(window, "window")
    lines = list(lines)
    attempts = [a for a in map(parse_line, lines) if a is not None]
    by_ip = failures_by_ip(attempts)
    return Report(
        attempts=len(attempts),
        malformed=len(lines) - len(attempts),
        failures=sum(by_ip.values()),
        unique_ips=len(unique_ips(attempts)),
        flagged=tuple(bursts(attempts, threshold, window)),
        top_users=tuple(top_users(attempts, top)),
    )


# ------------------------------------------------------------------------------------------------------------------------------------- step F: the edge
class Source(Protocol):
    """Anything that can hand out log lines. The core never opens a file; it is given lines. (Given.)"""

    def lines(self) -> Iterable[str]: ...


class ListSource:
    """Lines held in memory (tests, small inputs). (Given.)"""

    def __init__(self, lines: Iterable[str]) -> None:
        self._lines = list(lines)

    def lines(self) -> Iterable[str]:
        return iter(self._lines)


class FileSource:
    """Lines of a UTF-8 text file. Nothing is opened until the first line is requested; the file is closed when the generator is exhausted, closed or collected; a missing file
    raises FileNotFoundError on the first request, not at construction. Line endings ('\\n' or '\\r\\n') are removed, nothing else is stripped."""

    def __init__(self, path: str) -> None:
        self._path = path

    def lines(self) -> Iterator[str]:
        raise NotImplementedError("step F: FileSource.lines")


def run(source: Source, *, threshold: int = 5, window: int = 60, top: int = 3) -> str:
    """The rendered report for everything `source` provides. (Given.)"""
    return render(analyze(source.lines(), threshold=threshold, window=window, top=top))


def main(argv: list[str], out: TextIO, err: TextIO) -> int:
    """Command line: `PATH [--threshold N] [--window SECONDS] [--top N]` (defaults 5, 60, 3). Writes the rendered report to `out` and returns 0.

    A usage error (unknown option, a value that is not a positive integer, no path) writes the usage text to `err`, writes nothing to `out` and returns 2. A path that cannot be
    read writes one line 'perfkit: cannot read PATH: REASON' to `err` and returns 1: no traceback. Only the given streams are used, never sys.stdout or sys.stderr.
    `argparse` calls `error()` of its parser, which prints and exits the process: subclass `ArgumentParser` and override `error` so that it raises instead.
    """
    raise NotImplementedError("step F: main")
