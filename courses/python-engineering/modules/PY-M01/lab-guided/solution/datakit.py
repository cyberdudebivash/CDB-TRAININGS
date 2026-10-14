"""datakit - five small data-processing functions and one file wrapper (PY-M01 guided lab; correct reference version)."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")


def word_frequencies(text: str) -> dict[str, int]:
    """Count words case-insensitively. A word is a run of letters, optionally with one internal apostrophe (don't).
    The result is ordered by count (highest first), then alphabetically."""
    counts = Counter(w.lower() for w in _WORD.findall(text))
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def chunk(items: list[int], size: int) -> list[list[int]]:
    """Split `items` into consecutive lists of at most `size` items; ValueError('size must be at least 1') when size < 1."""
    if size < 1:
        raise ValueError("size must be at least 1")
    return [items[i:i + size] for i in range(0, len(items), size)]


def group_by_length(words: list[str]) -> dict[int, list[str]]:
    """Group words by length. Keys ascend; each group keeps first-seen order and drops repeated words."""
    groups: dict[int, list[str]] = {}
    for word in words:
        group = groups.setdefault(len(word), [])
        if word not in group:
            group.append(word)
    return dict(sorted(groups.items()))


def parse_kv_lines(text: str) -> dict[str, str]:
    """Parse 'key = value' lines. Blank lines and lines starting with '#' are ignored; keys and values are stripped; a repeated key keeps its last value.
    A line without '=' or with an empty key raises ValueError('line N: expected key = value'), N counting from 1."""
    result: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"line {number}: expected key = value")
        result[key.strip()] = value.strip()
    return result


def summarise_scores(rows: list[dict[str, str]]) -> dict[str, float]:
    """Average 'score' per 'name' (rounded to two decimals, names in alphabetical order). Rows with an empty score are skipped;
    a score that is not a number raises ValueError('invalid score for <name>: <text>')."""
    totals: dict[str, list[float]] = {}
    for row in rows:
        text = row["score"].strip()
        if not text:
            continue
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"invalid score for {row['name']}: {text}") from None
        totals.setdefault(row["name"], []).append(value)
    return {name: round(sum(values) / len(values), 2) for name, values in sorted(totals.items())}


def summarise_file(csv_path: Path, json_path: Path) -> dict[str, float]:
    """Read a UTF-8 CSV with 'name' and 'score' columns, summarise it with summarise_scores, write the result to `json_path` as UTF-8 JSON
    (indent 2, non-ASCII characters written as themselves, a final newline) and return it. A missing input file raises FileNotFoundError and writes nothing."""
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    summary = summarise_scores(rows)
    Path(json_path).write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary
