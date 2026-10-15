"""The published checks for the PY-M06 independent lab. They show the shape of the hidden suite; they do not cover every rule of the specification."""
from __future__ import annotations

import asyncio
import time

import pytest


def ids(count):
    return [str(i) for i in range(count)]


def test_the_result_matches_the_sequential_baseline(wordjob, docs, run, reply):
    docs.faults["3"] = reply(500, "boom")
    baseline = wordjob.count_words_sequential(docs.sync_client(), ids(10) + ["missing"])

    async def main():
        async with docs.client() as client:
            return await wordjob.count_words(client, ids(10) + ["missing"], limit=4)

    result = run(main)
    assert (result.counts, result.errors) == (baseline.counts, baseline.errors)
    assert result.errors == {"3": "HTTP 500", "missing": "HTTP 404"} and result.counts["0"] == 3 and result.counts["6"] == 9
    assert result.requests == 11 and result.elapsed_s > 0


@pytest.mark.parametrize("limit", [1, 3, 6])
def test_never_more_requests_in_flight_than_the_limit(wordjob, docs, run, limit):
    async def main():
        async with docs.client() as client:
            await wordjob.count_words(client, ids(18), limit=limit)

    run(main)
    assert docs.server.peak_inflight == limit


def test_is_much_faster_than_one_after_another(wordjob, docs, run):
    async def main():
        async with docs.client() as client:
            return await wordjob.count_words(client, ids(24), limit=8)

    started = time.monotonic()
    result = run(main)
    assert len(result.counts) == 24 and time.monotonic() - started < 24 * docs.latency / 2


def test_a_slow_document_times_out_without_holding_up_the_others(wordjob, docs, run, reply):
    docs.faults["5"] = reply(200, "never arrives in time", delay=10.0)

    async def main():
        async with docs.client() as client:
            return await wordjob.count_words(client, ids(10), limit=10, timeout=1.5)

    started = time.monotonic()
    result = run(main)
    assert result.errors == {"5": "timeout"} and len(result.counts) == 9
    assert time.monotonic() - started < 5.0


def test_each_distinct_document_is_requested_once(wordjob, docs, run):
    async def main():
        async with docs.client() as client:
            return await wordjob.count_words(client, ["1", "2", "1", "1", "2"], limit=3)

    result = run(main)
    assert sorted(result.counts) == ["1", "2"] and result.requests == 2 and len(docs.server.requests) == 2


def test_an_id_can_not_change_the_path(wordjob, docs, run):
    async def main():
        async with docs.client() as client:
            return await wordjob.count_words(client, ["../secret", "a b", "x/y"], limit=3)

    result = run(main)
    assert sorted(result.errors) == ["../secret", "a b", "x/y"]
    assert all(r.path.startswith("/docs/") and r.path.count("/") == 2 for r in docs.server.requests), [r.path for r in docs.server.requests]


def test_a_deadline_returns_what_is_done_and_reports_the_rest(wordjob, docs, run):
    docs.latency = 0.3

    async def main():
        async with docs.client() as client:
            result = await wordjob.count_words(client, ids(16), limit=4, deadline=0.5)
            return result, len(asyncio.all_tasks())

    started = time.monotonic()
    result, tasks = run(main)
    assert time.monotonic() - started < 1.0 and tasks == 1
    assert len(result.counts) == 4 and set(result.errors.values()) == {"deadline"} and len(result.errors) == 12


def test_a_limit_below_one_is_refused(wordjob, docs, run):
    async def main():
        async with docs.client() as client:
            await wordjob.count_words(client, ["1"], limit=0)

    with pytest.raises(ValueError, match="limit must be at least 1"):
        run(main)
