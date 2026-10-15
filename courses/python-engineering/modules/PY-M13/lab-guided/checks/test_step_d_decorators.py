"""PY-M13 guided lab, step D (decorators that keep what they wrap). Run: python -m pytest checks/test_step_d_decorators.py"""
from __future__ import annotations

import pytest


class Flaky:
    """Raises `error` for the first `failures` calls, then returns `result`."""

    def __init__(self, failures, error=ValueError, result="ok"):
        self.failures, self.error, self.result, self.calls = failures, error, result, 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error(f"failure {self.calls}")
        return (self.result, args, kwargs)


# ------------------------------------------------------------------------------------------------ retry
def test_retry_returns_the_value_of_the_first_success_and_passes_arguments_through(sk):
    flaky = Flaky(0)
    wrapped = sk.retry(3)(flaky)
    assert wrapped(1, 2, key="v") == ("ok", (1, 2), {"key": "v"}) and flaky.calls == 1


def test_retry_calls_again_until_the_function_succeeds_and_sleeps_between_attempts(sk):
    sleeps, flaky = [], Flaky(2)
    wrapped = sk.retry(3, sleep=sleeps.append, delay=0.5)(flaky)
    assert wrapped()[0] == "ok" and flaky.calls == 3 and sleeps == [0.5, 0.5]


def test_retry_raises_the_last_exception_and_does_not_sleep_after_the_last_attempt(sk):
    sleeps, flaky = [], Flaky(10)
    wrapped = sk.retry(3, sleep=sleeps.append, delay=1)(flaky)
    with pytest.raises(ValueError, match="failure 3"):
        wrapped()
    assert flaky.calls == 3 and sleeps == [1, 1]


def test_retry_with_one_attempt_calls_once_and_never_sleeps(sk):
    sleeps, flaky = [], Flaky(5)
    with pytest.raises(ValueError, match="failure 1"):
        sk.retry(1, sleep=sleeps.append)(flaky)()
    assert flaky.calls == 1 and sleeps == []


def test_retry_only_retries_the_listed_exceptions(sk):
    flaky = Flaky(5, error=KeyError)
    with pytest.raises(KeyError):
        sk.retry(5, on=(ValueError,), sleep=lambda s: None)(flaky)()
    assert flaky.calls == 1, "a KeyError is not in `on`: no second attempt"
    flaky = Flaky(2, error=KeyError)
    assert sk.retry(5, on=(ValueError, KeyError), sleep=lambda s: None)(flaky)()[0] == "ok"


def test_retry_never_swallows_base_exceptions_by_default(sk):
    flaky = Flaky(5, error=KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        sk.retry(5, sleep=lambda s: None)(flaky)()
    assert flaky.calls == 1


def test_retry_keeps_the_name_the_docstring_and_the_original_function(sk):
    @sk.retry(2)
    def fetch(url):
        """Fetch a URL."""
        return url

    assert fetch.__name__ == "fetch" and fetch.__doc__ == "Fetch a URL." and fetch.__wrapped__("x") == "x" and fetch("y") == "y"


@pytest.mark.parametrize("bad,exc", [(0, ValueError), (-1, ValueError), ("3", TypeError), (2.0, TypeError), (True, TypeError), (None, TypeError)])
def test_retry_checks_times_when_the_decorator_is_created(sk, bad, exc):
    with pytest.raises(exc):
        sk.retry(bad)


def test_retry_works_on_methods(sk):
    class Client:
        def __init__(self):
            self.n = 0

        @sk.retry(3, sleep=lambda s: None)
        def get(self, path):
            self.n += 1
            if self.n < 3:
                raise ConnectionError("down")
            return f"{path}:{self.n}"

    assert Client().get("/a") == "/a:3"


def test_retry_does_not_sleep_when_nothing_fails(sk):
    sleeps = []
    sk.retry(3, sleep=sleeps.append, delay=5)(lambda: 1)()
    assert sleeps == []


# ------------------------------------------------------------------------------------------------ counted
def test_counted_counts_calls_and_passes_everything_through(sk):
    @sk.counted
    def add(a, b=0):
        """Add."""
        return a + b

    assert add.calls == 0 and add(1, b=2) == 3 and add(5) == 5 and add.calls == 2
    assert add.__name__ == "add" and add.__doc__ == "Add."


def test_counted_counts_calls_that_raise_and_keeps_the_exception(sk):
    @sk.counted
    def boom():
        raise KeyError("k")

    with pytest.raises(KeyError):
        boom()
    with pytest.raises(KeyError):
        boom()
    assert boom.calls == 2


def test_each_counted_function_has_its_own_counter(sk):
    @sk.counted
    def one():
        return 1

    @sk.counted
    def two():
        return 2

    one(); one(); two()
    assert (one.calls, two.calls) == (2, 1)


# ------------------------------------------------------------------------------------------------ once
def test_once_runs_the_function_on_the_first_call_only(sk):
    calls = []

    @sk.once
    def setup(name):
        """Set up."""
        calls.append(name)
        return f"ready:{name}"

    assert setup("a") == "ready:a" and setup("b") == "ready:a" and calls == ["a"]
    assert setup.__name__ == "setup" and setup.__doc__ == "Set up."


def test_once_remembers_a_none_result_too(sk):
    calls = []

    @sk.once
    def run():
        calls.append(1)

    assert run() is None and run() is None and calls == [1]


def test_once_does_not_remember_a_failure(sk):
    state = {"n": 0}

    @sk.once
    def flaky():
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("first attempt fails")
        return "fine"

    with pytest.raises(RuntimeError):
        flaky()
    assert flaky() == "fine" and flaky() == "fine" and state["n"] == 2


def test_each_function_decorated_with_once_has_its_own_result(sk):
    @sk.once
    def a():
        return "a"

    @sk.once
    def b():
        return "b"

    assert (a(), b(), a(), b()) == ("a", "b", "a", "b")
