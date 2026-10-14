"""The provided unit tests for the PY-M01 guided lab. Make them pass one function at a time:  python -m pytest -k word_frequencies"""
from __future__ import annotations

import json

import pytest


# ------------------------------------------------------------------------------------------ 1 word_frequencies
def test_word_frequencies_counts_and_orders(datakit):
    text = "The cat and the hat. The CAT sat!"
    assert datakit.word_frequencies(text) == {"the": 3, "cat": 2, "and": 1, "hat": 1, "sat": 1}
    assert list(datakit.word_frequencies(text)) == ["the", "cat", "and", "hat", "sat"]


def test_word_frequencies_ignores_punctuation_digits_and_keeps_apostrophes(datakit):
    assert datakit.word_frequencies("Don't stop: don't! 2026, stop... (stop)") == {"stop": 3, "don't": 2}
    assert datakit.word_frequencies("") == {}
    assert datakit.word_frequencies("123 --- !!!") == {}


def test_word_frequencies_handles_accented_letters(datakit):
    assert datakit.word_frequencies("Café café ÉCOLE") == {"café": 2, "école": 1}


# ------------------------------------------------------------------------------------------ 2 chunk
@pytest.mark.parametrize("items, size, expected", [
    ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
    ([1, 2, 3, 4], 2, [[1, 2], [3, 4]]),
    ([1, 2], 5, [[1, 2]]),
    ([], 3, []),
    ([1, 2, 3], 1, [[1], [2], [3]]),
])
def test_chunk(datakit, items, size, expected):
    assert datakit.chunk(items, size) == expected


@pytest.mark.parametrize("size", [0, -1])
def test_chunk_rejects_bad_sizes(datakit, size):
    with pytest.raises(ValueError, match="size must be at least 1"):
        datakit.chunk([1, 2, 3], size)


def test_chunk_does_not_change_its_input(datakit):
    data = [1, 2, 3, 4, 5]
    result = datakit.chunk(data, 2)
    result[0].append(99)
    assert data == [1, 2, 3, 4, 5]


# ------------------------------------------------------------------------------------------ 3 group_by_length
def test_group_by_length(datakit):
    assert datakit.group_by_length(["pear", "fig", "apple", "kiwi", "fig", "plum", "pear"]) == {3: ["fig"], 4: ["pear", "kiwi", "plum"], 5: ["apple"]}
    assert list(datakit.group_by_length(["aaaa", "b", "cc"])) == [1, 2, 4]
    assert datakit.group_by_length([]) == {}


# ------------------------------------------------------------------------------------------ 4 parse_kv_lines
def test_parse_kv_lines(datakit):
    text = "# settings\nname = demo\n\n  retries=3  \nname = final\npath = a=b\n"
    assert datakit.parse_kv_lines(text) == {"name": "final", "retries": "3", "path": "a=b"}
    assert datakit.parse_kv_lines("") == {}
    assert datakit.parse_kv_lines("key =\n") == {"key": ""}


@pytest.mark.parametrize("text, line", [("ok = 1\nbroken line\n", 2), ("= value\n", 1), ("# c\n\nnovalue", 3)])
def test_parse_kv_lines_reports_the_line_number(datakit, text, line):
    with pytest.raises(ValueError, match=f"line {line}: expected key = value"):
        datakit.parse_kv_lines(text)


# ------------------------------------------------------------------------------------------ 5 summarise_scores
def test_summarise_scores(datakit):
    rows = [{"name": "bo", "score": "7"}, {"name": "al", "score": "9.5"}, {"name": "bo", "score": "8"}, {"name": "al", "score": " "}, {"name": "cy", "score": ""}]
    assert datakit.summarise_scores(rows) == {"al": 9.5, "bo": 7.5}
    assert list(datakit.summarise_scores(rows)) == ["al", "bo"]
    assert datakit.summarise_scores([{"name": "x", "score": "1"}, {"name": "x", "score": "2"}, {"name": "x", "score": "2"}]) == {"x": 1.67}
    assert datakit.summarise_scores([]) == {}


def test_summarise_scores_rejects_text_scores(datakit):
    with pytest.raises(ValueError, match="invalid score for bo: ten"):
        datakit.summarise_scores([{"name": "bo", "score": "ten"}])


# ------------------------------------------------------------------------------------------ 6 summarise_file
def test_summarise_file_reads_csv_and_writes_json(datakit, tmp_path):
    source = tmp_path / "scores.csv"
    source.write_text('name,score\n"Smith, J.",8\nAda,9\n"Smith, J.",7\nAda,\n', encoding="utf-8", newline="")
    target = tmp_path / "summary.json"
    result = datakit.summarise_file(source, target)
    assert result == {"Ada": 9.0, "Smith, J.": 7.5}
    assert json.loads(target.read_text(encoding="utf-8")) == result
    assert target.read_text(encoding="utf-8").endswith("}\n")


def test_summarise_file_uses_utf8_and_does_not_escape_letters(datakit, tmp_path):
    source = tmp_path / "scores.csv"
    source.write_bytes("name,score\nZo\u00eb,5\n".encode("utf-8"))
    target = tmp_path / "summary.json"
    datakit.summarise_file(source, target)
    assert "Zo\u00eb".encode("utf-8") in target.read_bytes()
    assert b"\\u00eb" not in target.read_bytes()


def test_summarise_file_missing_input_writes_nothing(datakit, tmp_path):
    target = tmp_path / "summary.json"
    with pytest.raises(FileNotFoundError):
        datakit.summarise_file(tmp_path / "absent.csv", target)
    assert not target.exists()
