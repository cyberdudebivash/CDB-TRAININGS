"""PY-M13 guided lab, step B (a lazy transformation). Run: python -m pytest checks/test_step_b_parse.py"""
from __future__ import annotations

import dataclasses
import inspect

import pytest


@pytest.mark.parametrize("line,expected", [
    ("12 INFO started", (12, "INFO", "started")), ("0 WARN disk at 91%", (0, "WARN", "disk at 91%")), ("007 ERROR boom: code=5", (7, "ERROR", "boom: code=5")),
    ("5 INFO a b  c", (5, "INFO", "a b  c")),
])
def test_parse_line_reads_the_three_parts(sk, line, expected):
    event = sk.parse_line(line)
    assert (event.seconds, event.level, event.message) == expected and isinstance(event, sk.Event)


@pytest.mark.parametrize("line", ["", "12", "12 INFO", "12 INFO ", "12 INFO    ", "x INFO m", "-1 INFO m", "1.5 INFO m", "٣ INFO m", "12 info m", "12 DEBUG m", " 12 INFO m", "12  INFO m", "INFO 12 m"])
def test_parse_line_rejects_malformed_lines_and_names_the_line(sk, line):
    with pytest.raises(ValueError) as info:
        sk.parse_line(line)
    assert repr(line) in str(info.value)


def test_event_is_a_frozen_value(sk):
    event = sk.parse_line("1 INFO m")
    assert event == sk.Event(1, "INFO", "m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.seconds = 2
    assert event == sk.Event(1, "INFO", "m") and hash(event) == hash(sk.Event(1, "INFO", "m")) and not hasattr(event, "__dict__")


def test_parse_events_is_a_generator_that_skips_bad_lines(sk):
    gen = sk.parse_events(["1 INFO a", "oops", "2 ERROR b", "", "3 WARN c"])
    assert inspect.isgenerator(gen)
    assert [e.message for e in gen] == ["a", "b", "c"]


def test_parse_events_collects_the_skipped_lines_when_asked_to(sk):
    bad = []
    events = list(sk.parse_events(["1 INFO a", "oops", "", "2 INFO b"], bad))
    assert len(events) == 2 and bad == ["oops", ""]
    assert list(sk.parse_events(["oops"])) == []                         # bad=None: skipped silently


def test_parse_events_reads_one_input_line_per_step(sk, counting):
    source = counting(["1 INFO a", "bad", "bad", "2 INFO b", "3 INFO c"])
    gen = sk.parse_events(source)
    assert source.taken == 0, "creating the generator must not read anything"
    assert next(gen).message == "a" and source.taken == 1
    assert next(gen).message == "b" and source.taken == 4, "two bad lines were skipped on the way to 'b'"


def test_parse_events_works_on_any_iterable_and_on_a_one_shot_iterator(sk):
    assert [e.seconds for e in sk.parse_events(iter(["1 INFO a", "2 INFO b"]))] == [1, 2]
    assert [e.seconds for e in sk.parse_events(("1 INFO a",))] == [1]
