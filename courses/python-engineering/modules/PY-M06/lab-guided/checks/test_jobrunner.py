"""The provided checks for the PY-M06 guided lab. Work one function at a time:  python -m pytest -k run_bounded"""
from __future__ import annotations

import asyncio
import time

import pytest


class Probe:
    """Counts how many calls are in flight at once and records starts and clean-ups."""

    def __init__(self) -> None:
        self.inflight = 0
        self.peak = 0
        self.started: list = []
        self.cleaned: list = []

    def job(self, delay: float = 0.03, fail_on: dict | None = None):
        fail_on = fail_on or {}

        async def func(item):
            self.started.append(item)
            self.inflight += 1
            self.peak = max(self.peak, self.inflight)
            try:
                await asyncio.sleep(delay if not callable(delay) else delay(item))
                if item in fail_on:
                    raise fail_on[item]
                return item * 10
            finally:
                self.inflight -= 1
                self.cleaned.append(item)

        return func


# ------------------------------------------------------------------------------------------------ A run_bounded
def test_run_bounded_returns_results_in_input_order_even_when_jobs_finish_in_another_order(jr, run):
    async def main():
        probe = Probe()
        return await jr.run_bounded(probe.job(delay=lambda item: 0.001 * (9 - item)), range(10), limit=10)

    assert run(main) == [i * 10 for i in range(10)]


@pytest.mark.parametrize("limit, count", [(1, 4), (3, 9), (5, 5), (8, 3)])
def test_run_bounded_never_exceeds_the_limit_and_uses_all_of_it(jr, run, limit, count):
    async def main():
        probe = Probe()
        await jr.run_bounded(probe.job(), range(count), limit=limit)
        return probe.peak

    assert run(main) == min(limit, count)


def test_run_bounded_really_runs_jobs_at_the_same_time(jr, run):
    async def main():
        started = time.monotonic()
        await jr.run_bounded(Probe().job(delay=0.05), range(12), limit=6)
        return time.monotonic() - started

    elapsed = run(main)
    assert 0.09 <= elapsed < 0.3, "twelve 50 ms jobs, six at a time, take about two rounds"


def test_run_bounded_accepts_any_iterable_and_empty_input(jr, run):
    async def main():
        probe = Probe()
        assert await jr.run_bounded(probe.job(), (i for i in range(3)), limit=2) == [0, 10, 20]
        assert await jr.run_bounded(probe.job(), [], limit=2) == []

    run(main)


@pytest.mark.parametrize("limit", [0, -1])
def test_run_bounded_rejects_a_limit_below_one(jr, run, limit):
    async def main():
        await jr.run_bounded(Probe().job(), [1], limit=limit)

    with pytest.raises(ValueError, match="limit must be at least 1"):
        run(main)


def test_run_bounded_raises_the_first_failure_itself_and_cancels_the_rest(jr, run):
    async def main():
        probe = Probe()
        started = time.monotonic()
        try:
            await jr.run_bounded(probe.job(delay=lambda item: 0.01 if item == 1 else 5.0, fail_on={1: KeyError("job one")}), range(4), limit=4)
        except BaseException as error:
            caught = error
        return caught, probe, time.monotonic() - started, len(asyncio.all_tasks())

    caught, probe, elapsed, tasks = run(main)
    assert type(caught) is KeyError and caught.args == ("job one",), f"expected the KeyError itself, got {type(caught).__name__}"
    assert elapsed < 1.0, "the failure must not wait for the slow siblings"
    assert sorted(probe.cleaned) == [0, 1, 2, 3], "every job's cleanup must have run"
    assert tasks == 1, "no task may be left running"


def test_run_bounded_stops_starting_jobs_after_a_failure(jr, run):
    async def main():
        probe = Probe()
        with pytest.raises(RuntimeError):
            await jr.run_bounded(probe.job(delay=0.01, fail_on={1: RuntimeError("stop")}), range(10), limit=1)
        return probe.started

    started = run(main)
    assert started[:2] == [0, 1] and len(started) <= 3, "at most the job that was already waiting for its turn may have started; the rest must be cancelled before they start"


def test_run_bounded_cancels_every_job_when_the_caller_is_cancelled(jr, run):
    async def main():
        probe = Probe()
        job = asyncio.create_task(jr.run_bounded(probe.job(delay=5.0), range(6), limit=3))
        await asyncio.sleep(0.05)
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
        return probe, len(asyncio.all_tasks())

    probe, tasks = run(main)
    assert sorted(probe.cleaned) == [0, 1, 2] and probe.started == [0, 1, 2] and tasks == 1


# ------------------------------------------------------------------------------------------------ B run_collect
def test_run_collect_returns_one_outcome_per_item_in_order(jr, run):
    async def main():
        probe = Probe()
        return await jr.run_collect(probe.job(delay=lambda item: 0.001 * (6 - item), fail_on={1: ValueError("bad 1"), 4: KeyError("bad 4")}), range(6), limit=3)

    outcomes = run(main)
    assert [o.item for o in outcomes] == list(range(6))
    assert [o.ok for o in outcomes] == [True, False, True, True, False, True]
    assert [o.value for o in outcomes if o.ok] == [0, 20, 30, 50]
    assert [type(o.error).__name__ for o in outcomes if not o.ok] == ["ValueError", "KeyError"]


def test_run_collect_lets_every_other_job_finish_after_a_failure(jr, run):
    async def main():
        probe = Probe()
        outcomes = await jr.run_collect(probe.job(delay=0.01, fail_on={0: ValueError("first")}), range(8), limit=2)
        return outcomes, sorted(probe.started)

    outcomes, started = run(main)
    assert started == list(range(8)) and sum(o.ok for o in outcomes) == 7


def test_run_collect_never_exceeds_the_limit(jr, run):
    async def main():
        probe = Probe()
        await jr.run_collect(probe.job(), range(12), limit=4)
        return probe.peak

    assert run(main) == 4


def test_run_collect_keeps_duplicates_and_checks_the_limit(jr, run):
    async def main():
        assert [o.value for o in await jr.run_collect(Probe().job(), [2, 2, 2], limit=2)] == [20, 20, 20]
        await jr.run_collect(Probe().job(), [1], limit=0)

    with pytest.raises(ValueError, match="limit must be at least 1"):
        run(main)


def test_run_collect_passes_a_cancellation_through_instead_of_recording_it(jr, run):
    async def main():
        probe = Probe()
        job = asyncio.create_task(jr.run_collect(probe.job(delay=5.0), range(4), limit=2))
        await asyncio.sleep(0.05)
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
        return probe, len(asyncio.all_tasks())

    probe, tasks = run(main)
    assert sorted(probe.cleaned) == [0, 1] and tasks == 1


# ------------------------------------------------------------------------------------------------ C call_with_timeout
def test_call_with_timeout_returns_the_value_in_time(jr, run):
    assert run(lambda: jr.call_with_timeout(Probe().job(delay=0.01), 4, 1.0)) == 40


def test_call_with_timeout_raises_job_timeout_after_the_cleanup_ran(jr, run):
    async def main():
        probe = Probe()
        started = time.monotonic()
        try:
            await jr.call_with_timeout(probe.job(delay=5.0), 7, 0.05)
        except jr.JobTimeout as error:
            return error, probe.cleaned, time.monotonic() - started
        raise AssertionError("no JobTimeout")

    error, cleaned, elapsed = run(main)
    assert (error.item, error.seconds) == (7, 0.05) and cleaned == [7]
    assert 0.04 <= elapsed < 0.5


def test_call_with_timeout_only_turns_its_own_limit_into_job_timeout(jr, run):
    async def func(item):
        await asyncio.sleep(0.001)
        raise TimeoutError("the database said so")

    with pytest.raises(TimeoutError, match="the database said so") as info:
        run(lambda: jr.call_with_timeout(func, 1, 1.0))
    assert not isinstance(info.value, jr.JobTimeout)


def test_call_with_timeout_lets_other_errors_through(jr, run):
    with pytest.raises(KeyError):
        run(lambda: jr.call_with_timeout(Probe().job(delay=0.001, fail_on={3: KeyError("k")}), 3, 1.0))


# ------------------------------------------------------------------------------------------------ D process_queue
def test_process_queue_returns_results_in_input_order(jr, run):
    async def main():
        probe = Probe()
        return await jr.process_queue(range(20), probe.job(delay=lambda item: 0.002 * (item % 3)), workers=4, queue_size=2)

    assert run(main) == [i * 10 for i in range(20)]


def test_process_queue_never_runs_more_handlers_than_workers(jr, run):
    async def main():
        probe = Probe()
        await jr.process_queue(range(15), probe.job(delay=0.01), workers=3, queue_size=5)
        return probe.peak

    assert run(main) == 3


def test_process_queue_reads_its_input_lazily(jr, run):
    async def main():
        pulled = []

        def source():
            for i in range(50):
                pulled.append(i)
                yield i

        release = asyncio.Event()

        async def handler(item):
            await release.wait()
            return item

        job = asyncio.create_task(jr.process_queue(source(), handler, workers=3, queue_size=2))
        await asyncio.sleep(0.1)
        seen_while_blocked = len(pulled)
        release.set()
        return seen_while_blocked, await job

    seen, results = run(main)
    assert seen <= 3 + 2 + 1, f"{seen} items were read although every handler was busy and the queue was full"
    assert seen >= 5, "the queue should have filled up"
    assert results == list(range(50))


def test_process_queue_raises_the_first_failure_itself_and_leaves_no_task(jr, run):
    async def main():
        probe = Probe()
        try:
            await jr.process_queue(range(30), probe.job(delay=lambda item: 0.01 if item == 4 else 0.02, fail_on={4: LookupError("item four")}), workers=3, queue_size=3)
        except BaseException as error:
            return error, len(asyncio.all_tasks())

    error, tasks = run(main)
    assert type(error) is LookupError and tasks == 1


@pytest.mark.parametrize("workers, queue_size, name", [(0, 1, "workers"), (2, 0, "queue_size"), (-1, 1, "workers")])
def test_process_queue_rejects_bad_sizes(jr, run, workers, queue_size, name):
    with pytest.raises(ValueError, match=f"{name} must be at least 1"):
        run(lambda: jr.process_queue([1], Probe().job(), workers=workers, queue_size=queue_size))


def test_process_queue_handles_empty_input_and_more_workers_than_items(jr, run):
    async def main():
        assert await jr.process_queue([], Probe().job(), workers=3, queue_size=1) == []
        assert await jr.process_queue([1, 2], Probe().job(delay=0.001), workers=8, queue_size=1) == [10, 20]

    run(main)


# ------------------------------------------------------------------------------------------------ E median_time
def test_median_time_is_the_middle_value_not_the_mean(jr):
    delays = iter([0.01, 0.3, 0.01])
    result = jr.median_time(lambda: time.sleep(next(delays)), 3)
    assert 0.009 <= result < 0.04, "one slow run must not move the median"


def test_median_time_calls_the_function_exactly_repeats_times(jr):
    calls = []
    jr.median_time(lambda: calls.append(1), 5)
    assert len(calls) == 5


def test_median_time_rejects_fewer_than_one_repeat(jr):
    with pytest.raises(ValueError, match="repeats must be at least 1"):
        jr.median_time(lambda: None, 0)


# ------------------------------------------------------------------------------------------------ F speedup
def test_speedup_alternates_the_two_candidates(jr):
    log = []
    jr.speedup(lambda: log.append("baseline"), lambda: log.append("candidate"), repeats=3)
    assert log == ["baseline", "candidate"] * 3


def test_speedup_reports_both_medians_the_ratio_and_the_repeats(jr):
    result = jr.speedup(lambda: time.sleep(0.04), lambda: time.sleep(0.01), repeats=3)
    assert result.repeats == 3
    assert 0.039 <= result.baseline_s < 0.1 and 0.009 <= result.candidate_s < 0.05
    assert result.ratio == pytest.approx(result.baseline_s / result.candidate_s)
    assert 2.0 <= result.ratio <= 4.6


def test_speedup_ratio_below_one_when_the_candidate_is_slower(jr):
    assert jr.speedup(lambda: time.sleep(0.005), lambda: time.sleep(0.02), repeats=3).ratio < 0.6


def test_speedup_result_cannot_be_changed_and_repeats_must_be_positive(jr):
    result = jr.speedup(lambda: None, lambda: None, repeats=2)
    with pytest.raises(AttributeError):
        result.ratio = 99
    with pytest.raises(ValueError, match="repeats must be at least 1"):
        jr.speedup(lambda: None, lambda: None, repeats=0)
