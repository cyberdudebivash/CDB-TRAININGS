from logslice.core import parse_line, slice_lines


def test_parse_line_accepts_known_levels_only():
    assert parse_line("ERROR boom") == ("ERROR", "boom")
    assert parse_line("nonsense") is None


def test_slice_lines_keeps_at_or_above_the_level():
    lines = ["INFO a", "ERROR b", "DEBUG c", "junk"]
    assert slice_lines(lines, "ERROR") == ["ERROR b"]
