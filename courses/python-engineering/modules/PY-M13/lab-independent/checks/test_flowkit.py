"""Published checks for the PY-M13 independent lab (flowkit). They show the shape of the task; the instructors' suite checks much more (laziness, cleanup, edge cases, state).
Passing these ten is necessary, not sufficient."""
from __future__ import annotations

import pytest


def test_merge_sorted_merges_sorted_sources_and_breaks_ties_in_favour_of_the_earlier_source(fk):
    assert list(fk.merge_sorted([1, 4, 7], [2, 5, 8], [3, 6, 9])) == list(range(1, 10))
    assert list(fk.merge_sorted([(1, "a")], [(1, "b")], key=lambda t: t[0])) == [(1, "a"), (1, "b")]


def test_merge_sorted_is_lazy(fk, source):
    a, b = source([1, 3, 5]), source([2, 4, 6])
    gen = fk.merge_sorted(a, b)
    assert (a.taken, b.taken) == (0, 0)
    assert next(gen) == 1 and (a.taken, b.taken) == (1, 1)


def test_merge_sorted_rejects_a_non_iterable_when_it_is_called(fk):
    with pytest.raises(TypeError):
        fk.merge_sorted([1], 5)


def test_merge_sorted_closes_unfinished_sources_when_stopped_early(fk, source):
    a, b = source([1, 3]), source([2, 4])
    gen = fk.merge_sorted(a, b)
    next(gen)
    gen.close()
    assert (a.closed, b.closed) == (1, 1)


def test_group_runs_groups_consecutive_equal_keys_lazily(fk, source):
    assert list(fk.group_runs("aabccc")) == [("a", ["a", "a"]), ("b", ["b"]), ("c", ["c", "c", "c"])]
    s = source("aabbb")
    gen = fk.group_runs(s)
    assert next(gen) == ("a", ["a", "a"]) and s.taken == 3


def test_memo_remembers_results_and_reports_statistics(fk):
    calls = []

    @fk.memo(2)
    def square(x):
        """Square."""
        calls.append(x)
        return x * x

    assert square(3) == 9 and square(3) == 9 and calls == [3]
    assert square.cache_info() == {"hits": 1, "misses": 1, "size": 1, "maxsize": 2}
    assert square.__name__ == "square" and square.__doc__ == "Square."


def test_memo_evicts_the_least_recently_used_entry(fk):
    calls = []

    @fk.memo(2)
    def f(x):
        calls.append(x)
        return x

    f(1); f(2); f(1); f(3)                       # 2 is the least recently used and is evicted
    calls.clear()
    f(1); f(3); f(2)
    assert calls == [2]


def test_memo_validates_its_argument_when_created(fk):
    for bad, exc in ((-1, ValueError), ("3", TypeError), (True, TypeError)):
        with pytest.raises(exc):
            fk.memo(bad)


def test_a_transaction_rolls_back_when_the_block_raises_and_keeps_the_changes_otherwise(fk):
    d = {"a": 1}
    with fk.Transaction(d) as t:
        t["b"] = 2
    assert d == {"a": 1, "b": 2}
    with pytest.raises(RuntimeError):
        with fk.Transaction(d) as t:
            t["a"] = 99
            del t["b"]
            raise RuntimeError("boom")
    assert d == {"a": 1, "b": 2}


def test_nested_transactions_roll_back_independently(fk):
    d = {"n": 0}
    with fk.Transaction(d):
        d["n"] = 1
        with pytest.raises(ValueError):
            with fk.Transaction(d):
                d["n"] = 2
                raise ValueError
        assert d["n"] == 1
