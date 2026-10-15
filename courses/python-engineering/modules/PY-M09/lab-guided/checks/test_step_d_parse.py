"""Step D - parsing: the same Attempt for every line, with the work of building the pattern and the date done once, not once per line."""
from __future__ import annotations

import cProfile
import pstats
import re
from datetime import datetime, timezone

import pytest

TRICKY = [
    "2026-10-14T12:00:03Z 10.0.0.5 alice FAIL",
    "2026-10-14T12:00:03Z 10.0.0.5 alice OK",
    "  2026-10-14T12:00:03Z 10.0.0.5 alice OK  ",
    "\t2026-10-14T12:00:03Z 10.0.0.5 alice OK\r\n",
    "2026-10-14T12:00:03Z 255.255.255.255 a.b-c_d FAIL",
    "2026-10-14T12:00:03Z 256.0.0.1 alice FAIL",
    "2026-10-14T12:00:03Z 1.2.3.999 alice FAIL",
    "2026-10-14T12:00:03Z 010.001.001.001 alice OK",
    "2026-10-14T12:00:03Z 1.2.3 alice OK",
    "2026-10-14T12:00:03Z 1.2.3.4.5 alice OK",
    "2026-02-30T12:00:03Z 10.0.0.5 alice OK",
    "2026-02-29T12:00:03Z 10.0.0.5 alice OK",
    "2024-02-29T12:00:03Z 10.0.0.5 alice OK",
    "2026-13-01T12:00:03Z 10.0.0.5 alice OK",
    "2026-00-10T12:00:03Z 10.0.0.5 alice OK",
    "0000-01-01T00:00:00Z 10.0.0.5 alice OK",
    "9999-12-31T23:59:59Z 10.0.0.5 alice OK",
    "2026-10-14T24:00:00Z 10.0.0.5 alice OK",
    "2026-10-14T23:60:00Z 10.0.0.5 alice OK",
    "2026-10-14T23:59:60Z 10.0.0.5 alice OK",
    "2026-10-14T23:59:59Z 10.0.0.5 alice OK",
    "2026-10-14T12:00:03 10.0.0.5 alice OK",
    "2026-10-14 12:00:03Z 10.0.0.5 alice OK",
    "2026-10-14T12:00:03Z 10.0.0.5 alice ok",
    "2026-10-14T12:00:03Z 10.0.0.5 alice MAYBE",
    "2026-10-14T12:00:03Z 10.0.0.5 alice OK extra",
    "2026-10-14T12:00:03Z  10.0.0.5 alice OK",
    "2026-10-14T12:00:03Z 10.0.0.5 alïce OK",
    "2026-10-14T12:00:03Z 10.0.0.5 ١٢ FAIL",
    "2026-10-14T12:00:03Z ١.2.3.4 alice FAIL",
    "",
    "   ",
    "garbage",
]


def view(a):
    return None if a is None else (a.ts, a.ip, a.user, a.ok)


@pytest.mark.parametrize("line", TRICKY, ids=[repr(l)[:40] for l in TRICKY])
def test_every_line_parses_as_the_slow_program_parses_it(pk, oracle, line):
    assert view(pk.parse_line(line)) == view(oracle.parse_line(line))


def test_valid_lines_really_parse(pk):
    a = pk.parse_line("2026-10-14T12:00:03Z 10.0.0.5 alice FAIL")
    assert (a.ip, a.user, a.ok) == ("10.0.0.5", "alice", False)
    assert a.ts == int(datetime(2026, 10, 14, 12, 0, 3, tzinfo=timezone.utc).timestamp())
    assert pk.parse_line("2026-10-14T12:00:03Z 10.0.0.5 alice OK").ok is True
    assert pk.parse_line("garbage") is None


def test_the_pattern_is_not_compiled_once_per_line(pk, workload, monkeypatch):
    lines = [l for l in workload(2500)]
    calls = []
    real = re.compile
    monkeypatch.setattr(re, "compile", lambda *a, **k: calls.append(a) or real(*a, **k))
    for line in lines:
        pk.parse_line(line)
    assert len(calls) <= 1, f"re.compile was called {len(calls)} times for {len(lines)} lines"


def profiled_calls(fn, lines):
    profiler = cProfile.Profile()
    profiler.runcall(lambda: [fn(l) for l in lines])
    return pstats.Stats(profiler).total_calls


def test_parsing_makes_at_least_30_percent_fewer_function_calls(pk, oracle, workload):
    """Call counts are exact: the same on every machine, so this check never flakes."""
    lines = workload(2000)
    slow, mine = profiled_calls(oracle.parse_line, lines), profiled_calls(pk.parse_line, lines)
    assert mine <= 0.7 * slow, f"{mine} calls against {slow}: a cut of {100 * (1 - mine / slow):.0f} percent"


def test_a_date_is_converted_once_however_many_lines_carry_it(pk, workload):
    lines = [l for l in workload(2000) if l.startswith("2026")]
    profiler = cProfile.Profile()
    profiler.runcall(lambda: [pk.parse_line(l) for l in lines])
    stats = pstats.Stats(profiler).stats
    conversions = sum(v[1] for k, v in stats.items() if "fromisoformat" in k[2])
    assert conversions <= 40, f"{conversions} date conversions for {len(lines)} lines of at most 28 different days"
