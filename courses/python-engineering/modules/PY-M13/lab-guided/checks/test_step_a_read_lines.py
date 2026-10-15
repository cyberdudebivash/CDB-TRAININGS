"""PY-M13 guided lab, step A (read_lines: a generator that owns a resource). Run: python -m pytest checks/test_step_a_read_lines.py"""
from __future__ import annotations

import contextlib
import gc
import inspect

import pytest


@pytest.fixture
def tracked_open(sk, monkeypatch):
    """Replace `open` inside the module under test with a version that records every file it opens and whether it was closed."""
    opened = []
    real_open = open

    class Tracked:
        def __init__(self, handle):
            self._handle = handle

        def __iter__(self):
            return iter(self._handle)

        def __enter__(self):
            self._handle.__enter__()
            return self

        def __exit__(self, *exc):
            return self._handle.__exit__(*exc)

        def close(self):
            self._handle.close()

        @property
        def closed(self):
            return self._handle.closed

    def fake_open(*args, **kwargs):
        handle = Tracked(real_open(*args, **kwargs))
        opened.append(handle)
        return handle

    monkeypatch.setattr(sk, "open", fake_open, raising=False)
    return opened


def write(tmp_path, text: str):
    path = tmp_path / "log.txt"
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def test_read_lines_is_a_generator(sk, tmp_path):
    assert inspect.isgenerator(sk.read_lines(write(tmp_path, "a\n")))


@pytest.mark.parametrize("text,expected", [
    ("a\nb\nc\n", ["a", "b", "c"]), ("a\r\nb\r\n", ["a", "b"]), ("a\nb", ["a", "b"]), ("", []), ("\n", [""]), ("a\n\nb\n", ["a", "", "b"]),
    ("café\nüber\n", ["café", "über"]), ("  padded  \n", ["  padded  "]),
])
def test_read_lines_yields_lines_without_their_line_ending(sk, tmp_path, text, expected):
    assert list(sk.read_lines(write(tmp_path, text))) == expected


def test_read_lines_does_not_open_the_file_until_the_first_item_is_requested(sk, tmp_path, tracked_open):
    gen = sk.read_lines(write(tmp_path, "a\nb\n"))
    assert tracked_open == []
    assert next(gen) == "a" and len(tracked_open) == 1


def test_a_missing_file_is_reported_when_iteration_starts_not_before(sk, tmp_path):
    gen = sk.read_lines(str(tmp_path / "missing.txt"))
    with pytest.raises(FileNotFoundError):
        next(gen)


def test_the_file_is_closed_when_the_generator_is_exhausted(sk, tmp_path, tracked_open):
    assert list(sk.read_lines(write(tmp_path, "a\nb\n"))) == ["a", "b"]
    assert len(tracked_open) == 1 and tracked_open[0].closed


def test_the_file_is_closed_when_the_consumer_stops_early_and_closes_the_generator(sk, tmp_path, tracked_open):
    gen = sk.read_lines(write(tmp_path, "a\nb\nc\n"))
    assert next(gen) == "a"
    assert not tracked_open[0].closed
    gen.close()
    assert tracked_open[0].closed


def test_the_file_is_closed_when_the_consumer_fails_inside_a_closing_block(sk, tmp_path, tracked_open):
    with pytest.raises(RuntimeError):
        with contextlib.closing(sk.read_lines(write(tmp_path, "a\nb\n"))) as lines:
            for _line in lines:
                raise RuntimeError("consumer failed")
    assert tracked_open[0].closed


def test_the_file_is_closed_when_an_abandoned_generator_is_garbage_collected(sk, tmp_path, tracked_open):
    gen = sk.read_lines(write(tmp_path, "a\nb\n"))
    next(gen)
    del gen
    gc.collect()
    assert tracked_open[0].closed
