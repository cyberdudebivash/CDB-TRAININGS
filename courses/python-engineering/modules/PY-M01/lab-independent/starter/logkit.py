"""logkit - log-line utilities (PY-M01 independent lab). Implement the five functions to the specification in ../README.md."""
from __future__ import annotations

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def parse_log_line(line: str) -> tuple[str, str, str]:
    """Return (timestamp, level, message) for 'YYYY-MM-DD HH:MM:SS LEVEL message'; ValueError('invalid log line: <line>') otherwise."""
    raise NotImplementedError


def count_levels(lines: list[str]) -> dict[str, int]:
    """Number of valid lines per level (ordered by severity) plus 'INVALID' for lines that do not parse; blank lines are ignored; zero counts are omitted."""
    raise NotImplementedError


def top_messages(lines: list[str], n: int) -> list[tuple[str, int]]:
    """The n most frequent messages among valid lines as (message, count), most frequent first, ties by message; ValueError('n must be at least 1')."""
    raise NotImplementedError


def busiest_hour(lines: list[str]) -> str | None:
    """The hour 'YYYY-MM-DD HH' with the most valid lines (ties: the earliest); None when there are no valid lines."""
    raise NotImplementedError


def mask_ips(text: str) -> str:
    """Replace the last octet of every valid IPv4 address in `text` by 'x' (192.168.1.25 becomes 192.168.1.x); leave everything else unchanged."""
    raise NotImplementedError
