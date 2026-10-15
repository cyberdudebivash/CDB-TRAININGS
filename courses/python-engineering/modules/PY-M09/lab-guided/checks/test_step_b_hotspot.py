"""Step B - reading a profile: which function is the one to fix?"""
from __future__ import annotations

import pytest


def rows(pk, *specs):
    return pk.Profile(tuple(pk.ProfileRow(name, file, 1, 1, tot, cum) for name, file, tot, cum in specs), len(specs), 1.0)


def test_the_largest_cumulative_time_of_the_file_wins_once_the_entry_point_is_left_out(pk):
    prof = rows(pk, ("analyze", "app.py", 0.01, 1.0), ("slow", "app.py", 0.2, 0.6), ("fast", "app.py", 0.5, 0.5), ("sorted", "~", 0.9, 0.9))
    assert pk.hotspot(prof, "app.py", exclude=("analyze",)) == "slow"
    assert pk.hotspot(prof, "app.py") == "analyze"


def test_rows_of_other_files_are_ignored(pk):
    prof = rows(pk, ("a", "other.py", 9.0, 9.0), ("b", "app.py", 0.1, 0.1))
    assert pk.hotspot(prof, "app.py") == "b"


def test_ties_go_to_the_smaller_name(pk):
    prof = rows(pk, ("zeta", "app.py", 0.1, 0.5), ("alpha", "app.py", 0.1, 0.5), ("mid", "app.py", 0.1, 0.5))
    assert pk.hotspot(prof, "app.py") == "alpha"


def test_no_candidate_is_an_error(pk):
    prof = rows(pk, ("analyze", "app.py", 0.1, 0.1))
    with pytest.raises(ValueError):
        pk.hotspot(prof, "app.py", exclude=("analyze",))
    with pytest.raises(ValueError):
        pk.hotspot(prof, "missing.py")


def test_exclude_may_be_any_iterable(pk):
    prof = rows(pk, ("a", "app.py", 0.1, 0.9), ("b", "app.py", 0.1, 0.8), ("c", "app.py", 0.1, 0.7))
    assert pk.hotspot(prof, "app.py", exclude=iter(["a", "b"])) == "c"
    assert pk.hotspot(prof, "app.py", exclude=("a",)) == "b"


def test_on_the_slow_program_the_hotspot_is_top_users(pk, oracle, workload):
    lines = workload(3000)
    _, prof = pk.profile(oracle.analyze, lines)
    assert pk.hotspot(prof, "slow_baseline.py", exclude=("analyze",)) == "top_users"


def test_the_hotspot_carries_most_of_the_run(pk, oracle, workload):
    """Why one fix is enough to cut the run by 30 percent: top_users holds more than 40 percent of the time. Re-profile after the fix to see what is next."""
    lines = workload(3000)
    _, prof = pk.profile(oracle.analyze, lines)
    row = next(r for r in prof.rows if r.name == "top_users")
    assert row.cumtime > 0.4 * prof.total_time
