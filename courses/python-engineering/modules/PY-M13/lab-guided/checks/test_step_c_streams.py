"""PY-M13 guided lab, step C (arguments are checked now, items later). Run: python -m pytest checks/test_step_c_streams.py"""
from __future__ import annotations

import itertools

import pytest


# ------------------------------------------------------------------------------------------------ chunks
@pytest.mark.parametrize("bad,exc", [(0, ValueError), (-1, ValueError), (1.5, TypeError), ("2", TypeError), (None, TypeError), (True, TypeError)])
def test_chunks_checks_its_argument_when_called_not_when_iterated(sk, counting, bad, exc):
    source = counting([1, 2, 3])
    with pytest.raises(exc):
        sk.chunks(source, bad)                  # no next() here: the error must already be raised
    assert source.taken == 0


@pytest.mark.parametrize("items,size,expected", [
    ([1, 2, 3, 4], 2, [[1, 2], [3, 4]]), ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]), ([1, 2], 5, [[1, 2]]), ([], 3, []), ([1], 1, [[1]]), (range(7), 3, [[0, 1, 2], [3, 4, 5], [6]]),
    ("abcde", 2, [["a", "b"], ["c", "d"], ["e"]]),
])
def test_chunks_yields_lists_of_the_requested_size(sk, items, size, expected):
    assert [list(c) for c in sk.chunks(items, size)] == expected
    assert all(isinstance(c, list) for c in sk.chunks(items, size))


def test_chunks_is_lazy_and_never_reads_ahead(sk, counting):
    source = counting(range(10))
    gen = sk.chunks(source, 3)
    assert source.taken == 0
    assert next(gen) == [0, 1, 2] and source.taken == 3
    assert next(gen) == [3, 4, 5] and source.taken == 6


def test_chunks_stops_without_an_empty_chunk_when_the_input_ends_exactly(sk):
    assert list(sk.chunks([1, 2, 3, 4], 2))[-1] == [3, 4] and len(list(sk.chunks([1, 2, 3, 4], 2))) == 2


def test_chunks_handles_an_infinite_input(sk):
    gen = sk.chunks(itertools.count(), 4)
    assert next(gen) == [0, 1, 2, 3] and next(gen) == [4, 5, 6, 7]


# ------------------------------------------------------------------------------------------------ windows
@pytest.mark.parametrize("bad,exc", [(0, ValueError), (-2, ValueError), (2.0, TypeError), (True, TypeError), (None, TypeError)])
def test_windows_checks_its_argument_when_called(sk, bad, exc):
    with pytest.raises(exc):
        sk.windows([1, 2, 3], bad)


@pytest.mark.parametrize("items,size,expected", [
    ([1, 2, 3, 4], 2, [(1, 2), (2, 3), (3, 4)]), ([1, 2, 3], 3, [(1, 2, 3)]), ([1, 2], 3, []), ([], 1, []), ([1, 2, 3], 1, [(1,), (2,), (3,)]), ("abc", 2, [("a", "b"), ("b", "c")]),
])
def test_windows_yields_every_run_of_consecutive_items_as_a_tuple(sk, items, size, expected):
    assert list(sk.windows(items, size)) == expected


def test_windows_is_lazy(sk, counting):
    source = counting(range(10))
    gen = sk.windows(source, 3)
    assert source.taken == 0
    assert next(gen) == (0, 1, 2) and source.taken == 3
    assert next(gen) == (1, 2, 3) and source.taken == 4


def test_windows_tuples_do_not_change_later(sk):
    first, second = list(itertools.islice(sk.windows(itertools.count(), 2), 2))
    assert first == (0, 1) and second == (1, 2)


# ------------------------------------------------------------------------------------------------ take
def test_take_consumes_exactly_n_items(sk, counting):
    source = counting(range(10))
    assert sk.take(source, 3) == [0, 1, 2] and source.taken == 3
    assert sk.take(source, 2) == [3, 4] and source.taken == 5, "the rest of the iterator is still there"


def test_take_zero_consumes_nothing_and_short_input_is_fine(sk, counting):
    source = counting([1, 2])
    assert sk.take(source, 0) == [] and source.taken == 0
    assert sk.take(source, 5) == [1, 2] and sk.take([], 3) == []


def test_take_rejects_a_negative_count(sk):
    with pytest.raises(ValueError):
        sk.take([1, 2], -1)


def test_take_works_on_an_infinite_input(sk):
    assert sk.take(itertools.count(5), 3) == [5, 6, 7]


# ------------------------------------------------------------------------------------------------ dedupe
def test_dedupe_keeps_the_first_occurrence_in_order(sk):
    assert list(sk.dedupe([3, 1, 3, 2, 1, 4])) == [3, 1, 2, 4] and list(sk.dedupe([])) == [] and list(sk.dedupe("aabbcc")) == ["a", "b", "c"]


def test_dedupe_can_use_a_key(sk):
    rows = [("a", 1), ("b", 1), ("c", 2), ("d", 1)]
    assert list(sk.dedupe(rows, key=lambda r: r[1])) == [("a", 1), ("c", 2)]
    assert list(sk.dedupe(["A", "a", "B", "b"], key=str.lower)) == ["A", "B"]


def test_dedupe_is_lazy(sk, counting):
    source = counting([1, 1, 2, 2, 3])
    gen = sk.dedupe(source)
    assert source.taken == 0 and next(gen) == 1 and source.taken == 1
    assert next(gen) == 2 and source.taken == 3


def test_dedupe_works_on_an_infinite_input(sk):
    assert sk.take(sk.dedupe(i % 3 for i in itertools.count()), 3) == [0, 1, 2]


def test_dedupe_without_a_key_needs_hashable_items(sk):
    with pytest.raises(TypeError):
        list(sk.dedupe([[1], [1]]))
    assert list(sk.dedupe([[1], [1], [2]], key=tuple)) == [[1], [2]]
