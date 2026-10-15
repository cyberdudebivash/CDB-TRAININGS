"""Step C - the same answers, a better algorithm. Correctness is checked against the slow program on edge cases and on random inputs; scaling is checked with budgets that a
quadratic solution misses by an order of magnitude and a linear one meets with room to spare (and with ratios, never with the clock of one machine)."""
from __future__ import annotations

import random

import pytest

WINDOW_BUDGET = 0.25        # seconds; a correct solution needs a few milliseconds on these inputs, a quadratic one several seconds


def pair(pk, oracle, rows):
    """The same attempts as learner objects and as oracle objects."""
    return [pk.Attempt(*r) for r in rows], [oracle.Attempt(*r) for r in rows]


def fuzz_rows(seed):
    rnd = random.Random(seed)
    ips = [f"192.168.0.{i}" for i in range(1, 1 + rnd.randint(1, 6))]
    users = [f"u{i}" for i in range(rnd.randint(1, 5))]
    return [(rnd.randint(0, 120), rnd.choice(ips), rnd.choice(users), rnd.random() < 0.4) for _ in range(rnd.randint(0, 70))]


EDGE_ROWS = {
    "empty": [],
    "one success": [(10, "1.1.1.1", "a", True)],
    "one failure": [(10, "1.1.1.1", "a", False)],
    "all successes": [(1, "1.1.1.1", "a", True), (2, "2.2.2.2", "b", True)],
    "boundary of the window": [(0, "1.1.1.1", "a", False), (60, "1.1.1.1", "a", False), (59, "2.2.2.2", "b", False), (0, "2.2.2.2", "b", False)],
    "same second": [(5, "1.1.1.1", "a", False)] * 4 + [(5, "2.2.2.2", "b", False)],
    "out of time order": [(50, "1.1.1.1", "a", False), (10, "1.1.1.1", "a", False), (30, "1.1.1.1", "b", False), (200, "1.1.1.1", "c", False), (11, "2.2.2.2", "a", False)],
    "first seen as a success": [(9, "9.9.9.9", "z", True), (1, "3.3.3.3", "y", False), (2, "9.9.9.9", "z", False), (3, "3.3.3.3", "y", False)],
    "ties between users": [(1, "1.1.1.1", "bob", False), (2, "1.1.1.1", "amy", False), (3, "1.1.1.1", "cat", False), (4, "1.1.1.1", "amy", False), (5, "1.1.1.1", "bob", False)],
}


@pytest.mark.parametrize("name", sorted(EDGE_ROWS))
@pytest.mark.parametrize("threshold, window, n", [(1, 1, 0), (1, 1000, 1), (2, 60, 2), (3, 61, 5), (5, 10, 3), (2, 1, 9)])
def test_every_function_gives_the_slow_programs_answer_on_edge_cases(pk, oracle, name, threshold, window, n):
    mine, theirs = pair(pk, oracle, EDGE_ROWS[name])
    assert pk.unique_ips(mine) == oracle.unique_ips(theirs)
    assert pk.failures_by_ip(mine) == oracle.failures_by_ip(theirs) and list(pk.failures_by_ip(mine)) == list(oracle.failures_by_ip(theirs))
    assert pk.bursts(mine, threshold, window) == oracle.bursts(theirs, threshold, window)
    assert pk.top_users(mine, n) == oracle.top_users(theirs, n)


@pytest.mark.parametrize("seed", range(40))
def test_random_inputs_give_the_slow_programs_answers(pk, oracle, seed):
    rnd = random.Random(1000 + seed)
    rows = fuzz_rows(seed)
    mine, theirs = pair(pk, oracle, rows)
    threshold, window, n = rnd.randint(1, 4), rnd.randint(1, 30), rnd.randint(0, 6)
    assert pk.unique_ips(mine) == oracle.unique_ips(theirs)
    assert list(pk.failures_by_ip(mine).items()) == list(oracle.failures_by_ip(theirs).items())
    assert pk.bursts(mine, threshold, window) == oracle.bursts(theirs, threshold, window)
    assert pk.top_users(mine, n) == oracle.top_users(theirs, n)


def test_the_functions_accept_any_iterable_of_attempts(pk):
    rows = [(1, "1.1.1.1", "a", False), (2, "1.1.1.1", "a", False)]
    attempts = [pk.Attempt(*r) for r in rows]
    assert pk.unique_ips(iter(attempts)) == ["1.1.1.1"]
    assert pk.failures_by_ip(iter(attempts)) == {"1.1.1.1": 2}
    assert pk.bursts(iter(attempts), 2, 5) == ["1.1.1.1"]
    assert pk.top_users(iter(attempts), 1) == [("a", 2)]


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "5", None])
def test_threshold_and_window_must_be_positive_ints(pk, bad):
    with pytest.raises(ValueError):
        pk.bursts([], bad, 60)
    with pytest.raises(ValueError):
        pk.bursts([], 3, bad)


@pytest.mark.parametrize("bad", [-1, True, 1.5, "2", None])
def test_n_must_be_a_non_negative_int(pk, bad):
    with pytest.raises(ValueError):
        pk.top_users([], bad)


def attempts_of(pk, count, *, ip=lambda i: "10.0.0.1", user=lambda i: "u", ok=lambda i: False, ts=lambda i: i):
    return [pk.Attempt(ts(i), ip(i), user(i), ok(i)) for i in range(count)]


def test_unique_ips_scales_linearly(pk, timing):
    data = attempts_of(pk, 20000, ip=lambda i: f"10.{i // 65536}.{i // 256 % 256}.{i % 256}")           # 20 000 different addresses: a list search is quadratic
    assert timing(lambda: pk.unique_ips(data), stop_above=4 * WINDOW_BUDGET) < WINDOW_BUDGET


def test_failures_by_ip_scales_linearly(pk, timing):
    data = attempts_of(pk, 15000, ip=lambda i: f"10.{i // 65536}.{i // 256 % 256}.{i % 256}")
    assert timing(lambda: pk.failures_by_ip(data), stop_above=4 * WINDOW_BUDGET) < WINDOW_BUDGET


def test_bursts_scales_with_the_number_of_failures_of_one_address(pk, timing):
    data = attempts_of(pk, 6000, ts=lambda i: i * 10)                                                  # one address, 6 000 failures, no burst: every start is examined
    assert timing(lambda: pk.bursts(data, 6001, 5), stop_above=4 * WINDOW_BUDGET) < WINDOW_BUDGET


def test_top_users_scales_with_the_number_of_users(pk, timing):
    data = attempts_of(pk, 8000, user=lambda i: f"user{i}")
    assert timing(lambda: pk.top_users(data, 3), stop_above=4 * WINDOW_BUDGET) < WINDOW_BUDGET


def test_the_whole_analysis_is_at_least_30_percent_faster_than_the_slow_program(pk, oracle, workload, timing):
    lines = workload(3000)
    slow = timing(lambda: oracle.analyze(lines), tries=3)
    mine = timing(lambda: pk.analyze(lines), tries=3)
    assert mine <= 0.7 * slow, f"{mine:.3f}s against {slow:.3f}s: a cut of {100 * (1 - mine / slow):.0f} percent"


def test_the_fast_analysis_gives_the_slow_programs_report(pk, oracle, workload):
    lines = workload(3000)
    fields = ("attempts", "malformed", "failures", "unique_ips", "flagged", "top_users")
    flagged_sets = set()
    for options in ({}, {"threshold": 2}, {"threshold": 3, "window": 10, "top": 5}, {"threshold": 9, "window": 300, "top": 1}, {"threshold": 1, "window": 1, "top": 0}):
        mine, theirs = pk.analyze(lines, **options), oracle.analyze(lines, **options)
        assert [getattr(mine, f) for f in fields] == [getattr(theirs, f) for f in fields], options
        flagged_sets.add(mine.flagged)
    assert len(flagged_sets) >= 3, "the options must change the answer, otherwise this check cannot tell a program that ignores them"
    default = pk.analyze(lines)
    assert default.flagged and default.malformed and default.top_users                               # the workload exercises every part of the report
