"""Step A - measuring: a profile you can read and compare."""
from __future__ import annotations

import pytest


def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


def test_profile_returns_the_result_and_a_profile_of_the_call(pk):
    result, prof = pk.profile(fib, 15)
    assert result == 610
    assert isinstance(prof, pk.Profile) and all(isinstance(r, pk.ProfileRow) for r in prof.rows)


def test_call_counts_are_exact_and_do_not_depend_on_the_machine(pk):
    _, first = pk.profile(fib, 15)
    _, second = pk.profile(fib, 15)
    row = next(r for r in first.rows if r.name == "fib")
    assert row.ncalls == 1973                                                  # fib(15) makes 1973 calls, recursion included
    assert 1973 <= first.total_calls <= 1976 and first.total_calls == second.total_calls
    assert sorted(r.ncalls for r in first.rows) == sorted(r.ncalls for r in second.rows)


def test_rows_carry_the_base_name_of_the_file_and_builtins_use_a_tilde(pk):
    _, prof = pk.profile(lambda: sorted([3, 1, 2]))
    assert {r.file for r in prof.rows if r.name == "<lambda>"} == {"test_step_a_profile.py"}
    assert any(r.file == "~" for r in prof.rows)


def test_rows_are_sorted_by_own_time_largest_first(pk):
    _, prof = pk.profile(lambda: [sum(range(100_000)) for _ in range(3)])
    times = [r.tottime for r in prof.rows]
    assert times == sorted(times, reverse=True) and prof.total_time > 0


def test_top_ranks_by_the_requested_column_and_breaks_ties_by_file_line_and_name(pk):
    rows = (
        pk.ProfileRow("b", "x.py", 10, 5, 0.5, 2.0),
        pk.ProfileRow("a", "x.py", 10, 5, 0.5, 1.0),
        pk.ProfileRow("c", "x.py", 3, 9, 0.1, 3.0),
        pk.ProfileRow("d", "w.py", 1, 5, 0.9, 0.9),
    )
    prof = pk.Profile(rows, 24, 2.0)
    assert [r.name for r in prof.top(4)] == ["d", "a", "b", "c"]                          # tottime: d 0.9, then the 0.5 tie (a before b), then c
    assert [r.name for r in prof.top(2, by="cumtime")] == ["c", "b"]
    assert [r.name for r in prof.top(4, by="ncalls")] == ["c", "d", "a", "b"]             # c has 9; the three with 5 are ordered by file (w.py first), then name
    assert prof.top(0) == () and len(prof.top(99)) == 4


@pytest.mark.parametrize("by", ["calls", "time", "", "TOTTIME", None])
def test_top_refuses_an_unknown_column(pk, by):
    with pytest.raises(ValueError):
        pk.Profile((), 0, 0.0).top(1, by=by)


@pytest.mark.parametrize("n", [-1, True, 1.5, "2", None])
def test_top_refuses_a_bad_count(pk, n):
    with pytest.raises(ValueError):
        pk.Profile((), 0, 0.0).top(n)


def test_arguments_and_keywords_are_passed_on(pk):
    result, _ = pk.profile(lambda a, b=0, *, c=0: a - b + c, 5, b=2, c=10)
    assert result == 13


def test_an_exception_propagates_and_the_profiler_is_free_again(pk):
    with pytest.raises(ZeroDivisionError):
        pk.profile(lambda: 1 / 0)
    result, prof = pk.profile(fib, 5)                      # a profiler left running would make this fail ("another profiling tool is already active")
    assert result == 5 and prof.total_calls > 0
