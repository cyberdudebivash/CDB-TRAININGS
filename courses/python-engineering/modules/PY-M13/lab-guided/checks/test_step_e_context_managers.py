"""PY-M13 guided lab, step E (context managers that clean up on every path). Run: python -m pytest checks/test_step_e_context_managers.py"""
from __future__ import annotations

import os

import pytest

NAME = "PY_M13_LAB_VARIABLE"
OTHER = "PY_M13_LAB_OTHER"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv(NAME, raising=False)
    monkeypatch.delenv(OTHER, raising=False)


# ------------------------------------------------------------------------------------------------ temp_env
def test_temp_env_sets_a_variable_inside_the_block_and_removes_it_afterwards(sk):
    with sk.temp_env(**{NAME: "on"}) as env:
        assert os.environ[NAME] == "on" and env is not None
    assert NAME not in os.environ


def test_temp_env_restores_the_previous_value(sk, monkeypatch):
    monkeypatch.setenv(NAME, "before")
    with sk.temp_env(**{NAME: "during"}):
        assert os.environ[NAME] == "during"
    assert os.environ[NAME] == "before"


def test_temp_env_none_removes_a_variable_for_the_duration(sk, monkeypatch):
    monkeypatch.setenv(NAME, "before")
    with sk.temp_env(**{NAME: None}):
        assert NAME not in os.environ
    assert os.environ[NAME] == "before"
    with sk.temp_env(**{OTHER: None}):                 # removing a variable that does not exist is fine
        assert OTHER not in os.environ
    assert OTHER not in os.environ


def test_temp_env_tells_an_empty_value_from_a_missing_variable(sk, monkeypatch):
    monkeypatch.setenv(NAME, "")
    with sk.temp_env(**{NAME: "x"}):
        pass
    assert os.environ[NAME] == "", "an empty string is a value, not 'unset'"


def test_temp_env_restores_everything_when_the_block_raises_and_does_not_suppress(sk, monkeypatch):
    monkeypatch.setenv(OTHER, "keep")
    with pytest.raises(RuntimeError, match="boom"):
        with sk.temp_env(**{NAME: "x", OTHER: "y"}):
            raise RuntimeError("boom")
    assert NAME not in os.environ and os.environ[OTHER] == "keep"


def test_temp_env_can_be_nested(sk):
    with sk.temp_env(**{NAME: "outer"}):
        with sk.temp_env(**{NAME: "inner"}):
            assert os.environ[NAME] == "inner"
        assert os.environ[NAME] == "outer"
    assert NAME not in os.environ


@pytest.mark.parametrize("value", [1, 1.5, True, b"x", ["x"]])
def test_temp_env_refuses_values_that_are_not_text_before_changing_anything(sk, value):
    with pytest.raises(TypeError):
        sk.temp_env(**{OTHER: "ok", NAME: value})
    assert OTHER not in os.environ and NAME not in os.environ


# ------------------------------------------------------------------------------------------------ timer
class FakeClock:
    def __init__(self, *values):
        self.values = list(values)

    def __call__(self):
        return self.values.pop(0)


def test_timer_measures_the_block_with_the_injected_clock(sk):
    with sk.timer(FakeClock(10.0, 12.5)) as t:
        assert t.elapsed is None, "not known while the block is running"
    assert t.elapsed == 2.5 and isinstance(t, sk.Stopwatch)


def test_timer_records_the_time_even_when_the_block_raises_and_does_not_suppress(sk):
    holder = []
    with pytest.raises(ValueError):
        with sk.timer(FakeClock(1.0, 4.0)) as t:
            holder.append(t)
            raise ValueError("x")
    assert holder[0].elapsed == 3.0


def test_timer_reads_the_clock_exactly_twice(sk):
    clock = FakeClock(0.0, 1.0)
    with sk.timer(clock):
        pass
    assert clock.values == []


def test_timer_uses_a_real_clock_by_default(sk):
    with sk.timer() as t:
        sum(range(1000))
    assert isinstance(t.elapsed, float) and t.elapsed >= 0.0


# ------------------------------------------------------------------------------------------------ collecting
def test_collecting_catches_the_listed_exception_and_carries_on(sk):
    with sk.collecting(ValueError) as errors:
        raise ValueError("bad")
    assert [str(e) for e in errors] == ["bad"] and isinstance(errors[0], ValueError)


def test_collecting_gives_an_empty_list_when_nothing_is_raised(sk):
    with sk.collecting(ValueError) as errors:
        pass
    assert errors == []


def test_collecting_lets_other_exceptions_through(sk):
    with pytest.raises(KeyError):
        with sk.collecting(ValueError):
            raise KeyError("k")


def test_collecting_accepts_several_types_and_subclasses(sk):
    with sk.collecting(KeyError, ValueError) as errors:
        raise UnicodeError("subclass of ValueError")
    assert len(errors) == 1


def test_collecting_never_catches_base_exceptions(sk):
    with pytest.raises(KeyboardInterrupt):
        with sk.collecting(Exception):
            raise KeyboardInterrupt


@pytest.mark.parametrize("bad", [KeyboardInterrupt, SystemExit, BaseException, "ValueError", 5, ValueError("x")])
def test_collecting_refuses_things_that_are_not_exception_classes_when_the_block_starts(sk, bad):
    with pytest.raises(TypeError):
        with sk.collecting(bad):
            pass


# ------------------------------------------------------------------------------------------------ close_all
class Resource:
    def __init__(self, name, log, fail=False):
        self.name, self.log, self.fail = name, log, fail

    def close(self):
        self.log.append(self.name)
        if self.fail:
            raise RuntimeError(self.name)


def test_close_all_closes_in_reverse_order(sk):
    log = []
    closer = sk.close_all(Resource("a", log), Resource("b", log), Resource("c", log))
    assert log == []
    closer()
    assert log == ["c", "b", "a"]


def test_close_all_closes_everything_even_when_some_fail_and_raises_the_last_failure(sk):
    log = []
    closer = sk.close_all(Resource("a", log), Resource("b", log, fail=True), Resource("c", log, fail=True), Resource("d", log))
    with pytest.raises(RuntimeError, match="^b$"):
        closer()
    assert log == ["d", "c", "b", "a"]


def test_close_all_closes_nothing_the_second_time_and_accepts_no_resources(sk):
    log = []
    closer = sk.close_all(Resource("a", log))
    closer(); closer()
    assert log == ["a"]
    sk.close_all()()


def test_close_all_works_with_real_files(sk, tmp_path):
    handles = [open(tmp_path / f"f{i}.txt", "w", encoding="utf-8") for i in range(3)]
    sk.close_all(*handles)()
    assert all(h.closed for h in handles)
