"""Count log lines per level. Uses `rich` for a table when it is installed and plain text otherwise.

Run:  python scripts/report.py data/sample.log
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def count(path: str) -> Counter:
    counts: Counter = Counter()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        head = line.split(" ", 1)[0]
        if head in LEVELS:
            counts[head] += 1
    return counts


def main(argv: list[str]) -> int:
    counts = count(argv[0])
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for level in LEVELS:
            print(f"{level}: {counts[level]}")
        return 0
    table = Table("level", "lines")
    for level in LEVELS:
        table.add_row(level, str(counts[level]))
    Console().print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
