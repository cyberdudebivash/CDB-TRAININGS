"""Core logic: count rows and describe columns of a CSV file using only the standard library."""
from __future__ import annotations

import csv
from pathlib import Path


def summarise(path: str | Path) -> dict:
    """Return {'rows': int, 'columns': [names], 'numeric_columns': [names]} for a CSV file with a header row."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    numeric = []
    for name in columns:
        values = [row[name] for row in rows if row[name] != ""]
        if values and all(_is_number(v) for v in values):
            numeric.append(name)
    return {"rows": len(rows), "columns": columns, "numeric_columns": numeric}


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True
