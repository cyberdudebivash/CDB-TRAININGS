"""Step E - memory: do not keep what you can stream, and do not keep a copy of a string you already have. tracemalloc counts exactly, so these checks are deterministic."""
from __future__ import annotations

import tracemalloc

LINES = 20000


def peak_of(fn):
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        result = fn()
        return tracemalloc.get_traced_memory()[1], result
    finally:
        tracemalloc.stop()


def test_the_analysis_of_a_stream_needs_far_less_memory_than_the_slow_program(pk, oracle, lazy_lines):
    slow_peak, slow_report = peak_of(lambda: oracle.analyze(lazy_lines(LINES)))
    my_peak, my_report = peak_of(lambda: pk.analyze(lazy_lines(LINES)))
    fields = ("attempts", "malformed", "failures", "unique_ips", "flagged", "top_users")
    assert [getattr(my_report, f) for f in fields] == [getattr(slow_report, f) for f in fields]
    assert my_peak <= 0.6 * slow_peak, f"peak {my_peak / 1e6:.1f} MB against {slow_peak / 1e6:.1f} MB: {100 * my_peak / slow_peak:.0f} percent"


def test_attempts_that_repeat_a_value_share_its_string(pk, lazy_lines):
    """A log repeats the same few addresses and names millions of times; each Attempt must not own a private copy."""
    lines = [l for l in lazy_lines(4000, ips=40, users=30) if len(l.split()) == 4]          # build the lines first: only the parsed objects are measured
    tracemalloc.start()
    try:
        before = tracemalloc.get_traced_memory()[0]
        attempts = [a for a in map(pk.parse_line, lines) if a is not None]
        used = tracemalloc.get_traced_memory()[0] - before
    finally:
        tracemalloc.stop()
    per_attempt = used / len(attempts)
    assert per_attempt <= 170, f"{per_attempt:.0f} bytes per attempt"
    by_value = {}
    for a in attempts:
        assert by_value.setdefault(("ip", a.ip), a.ip) is a.ip and by_value.setdefault(("user", a.user), a.user) is a.user


def test_the_lines_are_read_once_and_not_kept(pk, lazy_lines):
    produced = []

    def counting():
        for line in lazy_lines(3000):
            produced.append(1)
            yield line

    pk.analyze(counting())
    assert len(produced) == 3000


def test_a_file_is_streamed_and_not_read_whole(pk, tmp_path):
    """FileSource must hand out the first line without holding the whole file: tracemalloc counts exactly, so the peak is deterministic."""
    path = tmp_path / "big.log"
    path.write_text("".join(f"2026-10-01T00:00:{i % 60:02d}Z 10.0.0.{1 + i % 200} user{i % 50:02d} FAIL\n" for i in range(30000)), encoding="utf-8")
    size = path.stat().st_size
    assert size > 1_000_000
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        count = sum(1 for _ in pk.FileSource(str(path)).lines())
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert count == 30000
    assert peak < size / 4, f"peak {peak / 1e6:.2f} MB for a {size / 1e6:.2f} MB file"
