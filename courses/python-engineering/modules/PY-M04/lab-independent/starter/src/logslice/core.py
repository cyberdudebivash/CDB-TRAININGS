"""Parse 'LEVEL message' lines and keep those at or above a level."""
from __future__ import annotations

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


def parse_line(line: str) -> tuple[str, str] | None:
    """Return (LEVEL, message) for a well-formed line, otherwise None."""
    head, _, message = line.strip().partition(" ")
    return (head, message) if head in LEVELS else None


def slice_lines(lines: list[str], minimum: str = "INFO") -> list[str]:
    """Keep well-formed lines whose level is at or above `minimum`."""
    floor = LEVELS[minimum]
    kept = []
    for line in lines:
        parsed = parse_line(line)
        if parsed and LEVELS[parsed[0]] >= floor:
            kept.append(line.strip())
    return kept
