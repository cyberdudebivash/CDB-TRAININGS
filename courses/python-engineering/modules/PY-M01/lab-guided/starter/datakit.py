"""datakit - five small data-processing functions and one file wrapper (PY-M01 guided lab starter: implement each function)."""
from __future__ import annotations

from pathlib import Path


def word_frequencies(text: str) -> dict[str, int]:
    """Count words case-insensitively. A word is a run of letters, optionally with one internal apostrophe (don't).
    The result is ordered by count (highest first), then alphabetically."""
    raise NotImplementedError("step word_frequencies")


def chunk(items: list[int], size: int) -> list[list[int]]:
    """Split `items` into consecutive lists of at most `size` items; ValueError('size must be at least 1') when size < 1."""
    raise NotImplementedError("step chunk")


def group_by_length(words: list[str]) -> dict[int, list[str]]:
    """Group words by length. Keys ascend; each group keeps first-seen order and drops repeated words."""
    raise NotImplementedError("step group_by_length")


def parse_kv_lines(text: str) -> dict[str, str]:
    """Parse 'key = value' lines. Blank lines and lines starting with '#' are ignored; keys and values are stripped; a repeated key keeps its last value.
    A line without '=' or with an empty key raises ValueError('line N: expected key = value'), N counting from 1."""
    raise NotImplementedError("step parse_kv_lines")


def summarise_scores(rows: list[dict[str, str]]) -> dict[str, float]:
    """Average 'score' per 'name' (rounded to two decimals, names in alphabetical order). Rows with an empty score are skipped;
    a score that is not a number raises ValueError('invalid score for <name>: <text>')."""
    raise NotImplementedError("step summarise_scores")


def summarise_file(csv_path: Path, json_path: Path) -> dict[str, float]:
    """Read a UTF-8 CSV with 'name' and 'score' columns, summarise it with summarise_scores, write the result to `json_path` as UTF-8 JSON
    (indent 2, non-ASCII characters written as themselves, a final newline) and return it. A missing input file raises FileNotFoundError and writes nothing."""
    raise NotImplementedError("step summarise_file")
