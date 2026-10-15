"""perfkit - find a bottleneck with a profiler, fix it without changing the answers, and keep the program easy to change (PY-M09 guided lab, public reference solution).

The program digests a log of login attempts (one per line: '<ISO time>Z <ip> <user> OK|FAIL'): how many attempts, how many failed, which addresses made at least
`threshold` failures within `window` seconds, which users failed most. Standard library only.

Layers: the *core* (parse_line, unique_ips, failures_by_ip, bursts, top_users, analyze, render) only computes; the *edge* (FileSource, main) reads files and writes streams.
"""
from __future__ import annotations

import argparse
import cProfile
import functools
import heapq
import pstats
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, TextIO

PATTERN = r"(\d{4}-\d\d-\d\d)T(\d\d):(\d\d):(\d\d)Z (\d{1,3}(?:\.\d{1,3}){3}) ([A-Za-z0-9_.-]+) (OK|FAIL)"
_LINE = re.compile("^" + PATTERN + "$")                      # compiled once, when the module is imported


# ------------------------------------------------------------------------------------------------------------------------------------- values
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
        if by not in ("tottime", "cumtime", "ncalls"):
            raise ValueError(f"cannot rank by {by!r}")
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("n must be a non-negative int")
        return tuple(sorted(self.rows, key=lambda r: (-getattr(r, by), r.file, r.line, r.name))[:n])


def profile(func: Any, /, *args: Any, **kwargs: Any) -> tuple[Any, Profile]:
    """Call `func(*args, **kwargs)` under cProfile and return (its result, a Profile of the call).

    The profiler is switched off again when the call raises, and the exception propagates unchanged. `ncalls` counts every call (recursion included), so profiling a
    function that calls itself recursively gives the same totals on every run and every interpreter: unlike times, call counts do not depend on the machine.
    """
    profiler = cProfile.Profile()
    result = profiler.runcall(func, *args, **kwargs)
    stats = pstats.Stats(profiler)
    rows = [
        ProfileRow(name, filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1], line, nc, tt, ct)
        for (filename, line, name), (_cc, nc, tt, ct, _callers) in stats.stats.items()
    ]
    rows.sort(key=lambda r: (-r.tottime, r.file, r.line, r.name))
    return result, Profile(tuple(rows), stats.total_calls, stats.total_tt)


# ------------------------------------------------------------------------------------------------------------------------------------- step B
def hotspot(prof: Profile, file: str, exclude: Iterable[str] = ()) -> str:
    """The name of the function of `file` (its base name, e.g. 'perfkit.py') with the largest cumulative time, leaving out the names in `exclude` (the entry point itself
    always has the largest cumulative time and tells you nothing). Ties go to the smaller name. ValueError if no row qualifies."""
    skip = set(exclude)
    candidates = [r for r in prof.rows if r.file == file and r.name not in skip]
    if not candidates:
        raise ValueError(f"no function of {file!r} in the profile")
    return min(candidates, key=lambda r: (-r.cumtime, r.name)).name


# ------------------------------------------------------------------------------------------------------------------------------------- steps C and D
@functools.lru_cache(maxsize=64)
def _midnight(date: str) -> int:
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def parse_line(line: str) -> Attempt | None:
    """The Attempt in `line`, or None when the line is malformed: the format of PATTERN around the whole stripped line, every octet of the address 0 to 255, hour below 24,
    minute and second below 60, and a real calendar date. Equal addresses and user names share one string object (`sys.intern`): a log repeats the same few values millions of times."""
    m = _LINE.match(line.strip())
    if m is None:
        return None
    date, hh, mm, ss, ip, user, result = m.groups()
    if int(hh) > 23 or int(mm) > 59 or int(ss) > 59:
        return None
    for octet in ip.split("."):
        if int(octet) > 255:
            return None
    try:
        midnight = _midnight(date)
    except ValueError:
        return None
    return Attempt(midnight + int(hh) * 3600 + int(mm) * 60 + int(ss), sys.intern(ip), sys.intern(user), result == "OK")


def unique_ips(attempts: Iterable[Attempt]) -> list[str]:
    """The addresses in order of first appearance, each once."""
    return list(dict.fromkeys(a.ip for a in attempts))


def failures_by_ip(attempts: Iterable[Attempt]) -> dict[str, int]:
    """{address: number of failed attempts} for the addresses with at least one failure, in order of first appearance of the address among ALL attempts."""
    attempts = list(attempts)
    counts = Counter(a.ip for a in attempts if not a.ok)
    return {ip: counts[ip] for ip in dict.fromkeys(a.ip for a in attempts) if ip in counts}


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive int")
    return value


def bursts(attempts: Iterable[Attempt], threshold: int, window: int) -> list[str]:
    """The addresses with at least `threshold` FAILED attempts inside some window of `window` seconds (times t with start <= t < start + window; the attempts need not be
    in time order), in order of first appearance of the address among ALL attempts. ValueError unless `threshold` and `window` are positive ints."""
    _positive(threshold, "threshold")
    _positive(window, "window")
    failures: dict[str, list[int]] = {}
    for a in attempts:
        times = failures.setdefault(a.ip, [])
        if not a.ok:
            times.append(a.ts)
    flagged = []
    for ip, times in failures.items():
        times.sort()
        if any(times[i + threshold - 1] - times[i] < window for i in range(len(times) - threshold + 1)):
            flagged.append(ip)
    return flagged


def top_users(attempts: Iterable[Attempt], n: int) -> list[tuple[str, int]]:
    """The `n` users with the most FAILED attempts as (user, count), most first, equal counts in alphabetical order; users without a failure never appear. ValueError for a negative n."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative int")
    counts = Counter(a.user for a in attempts if not a.ok)
    return heapq.nsmallest(n, counts.items(), key=lambda item: (-item[1], item[0]))


# ------------------------------------------------------------------------------------------------------------------------------------- core: the whole analysis
def render(report: Report) -> str:
    """The report as text: one 'name: value' line each for attempts, malformed, failures, unique ips and flagged ('none' when empty, otherwise the addresses joined by ', '),
    then one 'user NAME: COUNT' line per entry of top_users; every line ends with a newline."""
    parts = [
        f"attempts: {report.attempts}\n",
        f"malformed: {report.malformed}\n",
        f"failures: {report.failures}\n",
        f"unique ips: {report.unique_ips}\n",
        "flagged: " + (", ".join(report.flagged) or "none") + "\n",
    ]
    parts.extend(f"user {user}: {count}\n" for user, count in report.top_users)
    return "".join(parts)


def analyze(lines: Iterable[str], threshold: int = 5, window: int = 60, top: int = 3) -> Report:
    """Digest `lines` (any iterable of text, read once, never stored as a list): count and sort out the malformed ones, then compute the report. The answers are exactly those of
    the slow program the lab started from."""
    _positive(threshold, "threshold")
    _positive(window, "window")
    attempts: list[Attempt] = []
    malformed = 0
    for line in lines:
        attempt = parse_line(line)
        if attempt is None:
            malformed += 1
        else:
            attempts.append(attempt)
    by_ip = failures_by_ip(attempts)
    return Report(
        attempts=len(attempts),
        malformed=malformed,
        failures=sum(by_ip.values()),
        unique_ips=len(unique_ips(attempts)),
        flagged=tuple(bursts(attempts, threshold, window)),
        top_users=tuple(top_users(attempts, top)),
    )


# ------------------------------------------------------------------------------------------------------------------------------------- step G: the edge
class Source(Protocol):
    """Anything that can hand out log lines. The core never opens a file; it is given lines."""

    def lines(self) -> Iterable[str]: ...


class ListSource:
    """Lines held in memory (tests, small inputs)."""

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
        with open(self._path, encoding="utf-8", newline=None) as handle:
            for line in handle:
                yield line.rstrip("\n")


def run(source: Source, *, threshold: int = 5, window: int = 60, top: int = 3) -> str:
    """The rendered report for everything `source` provides."""
    return render(analyze(source.lines(), threshold=threshold, window=window, top=top))


class _QuietParser(argparse.ArgumentParser):
    """argparse prints to the real stderr and exits the process; here a usage error is an exception the caller turns into a return code."""

    def error(self, message: str) -> Any:
        raise ValueError(message)


def main(argv: list[str], out: TextIO, err: TextIO) -> int:
    """Command line: `PATH [--threshold N] [--window SECONDS] [--top N]` (defaults 5, 60, 3). Writes the rendered report to `out` and returns 0.

    A usage error (unknown option, a value that is not a positive integer, no path) writes the usage text to `err`, writes nothing to `out` and returns 2. A path that cannot be
    read writes one line 'perfkit: cannot read PATH: REASON' to `err` and returns 1: no traceback. Only the given streams are used, never sys.stdout or sys.stderr.
    """
    parser = _QuietParser(prog="perfkit", add_help=False)
    parser.add_argument("path")
    for flag, default in (("--threshold", 5), ("--window", 60), ("--top", 3)):
        parser.add_argument(flag, type=int, default=default)
    try:
        args = parser.parse_args(argv)
        if args.threshold < 1 or args.window < 1 or args.top < 0:
            raise argparse.ArgumentError(None, "values out of range")
    except (argparse.ArgumentError, ValueError) as exc:
        err.write(f"usage: perfkit PATH [--threshold N] [--window SECONDS] [--top N] ({exc})\n")
        return 2
    try:
        report = run(FileSource(args.path), threshold=args.threshold, window=args.window, top=args.top)
    except OSError as exc:
        err.write(f"perfkit: cannot read {args.path}: {exc.strerror or exc}\n")
        return 1
    out.write(report)
    return 0
