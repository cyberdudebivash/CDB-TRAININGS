"""Offline synthetic support-ticket CSV metrics. Educational reference, not a SaaS integration."""
from __future__ import annotations

import csv
import re
from pathlib import Path

MAX_BYTES = 65_536
MAX_ROWS = 1000
HEADERS = ['ticket_id', 'team', 'minutes', 'severity']
ID = re.compile(r'[A-Z]{2,5}-[0-9]{3,6}\Z', re.ASCII)
TEAM = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}\Z', re.ASCII)
LEVELS = {'LOW', 'MEDIUM', 'HIGH'}


def _under_root(root: Path, requested: Path) -> Path:
    """Best-effort path policy for a trusted local exercise; not race-free confinement."""
    if not root.is_dir() or root.is_symlink():
        raise ValueError('root must be an existing non-symlink directory')
    if requested.is_absolute() or '..' in requested.parts or requested == Path('.'):
        raise ValueError('input must be a relative path without traversal')
    base = root.resolve(strict=True)
    cursor = root
    for part in requested.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('symlink entries are prohibited')
    candidate = (root / requested).resolve(strict=True)
    if not candidate.is_relative_to(base) or not candidate.is_file():
        raise ValueError('input must be a regular file under practice root')
    return candidate


def summarize_csv(root: Path, input_file: Path) -> dict:
    """Summarize bounded, validated synthetic tickets by team and severity.

    Raises ValueError on invalid input. Reads files but never modifies them.
    This illustrative path check is subject to filesystem races.
    """
    try:
        source = _under_root(Path(root), Path(input_file))
        if source.stat().st_size > MAX_BYTES:
            raise ValueError('input exceeds maximum byte budget')
        with source.open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames != HEADERS:
                raise ValueError('unexpected header fields or field order')
            seen: set[str] = set()
            teams: dict[str, dict[str, int]] = {}
            count = 0
            for row in reader:
                count += 1
                if count > MAX_ROWS:
                    raise ValueError('too many rows')
                if None in row or set(row) != set(HEADERS) or any(v is None for v in row.values()):
                    raise ValueError('malformed CSV record')
                ticket, team, minutes, severity = (row[h] for h in HEADERS)
                if not ID.fullmatch(ticket) or ticket in seen:
                    raise ValueError('invalid or duplicate ticket id')
                if not TEAM.fullmatch(team):
                    raise ValueError('invalid team')
                if not minutes.isascii() or not minutes.isdecimal() or (len(minutes) > 1 and minutes[0] == '0'):
                    raise ValueError('minutes must be canonical nonnegative digits')
                duration = int(minutes)
                if duration > 1440:
                    raise ValueError('minutes outside declared range')
                if severity not in LEVELS:
                    raise ValueError('invalid severity')
                seen.add(ticket)
                stats = teams.setdefault(team, {'tickets': 0, 'minutes': 0, 'high': 0})
                stats['tickets'] += 1
                stats['minutes'] += duration
                stats['high'] += int(severity == 'HIGH')
    except (UnicodeError, csv.Error, FileNotFoundError, PermissionError, OSError) as exc:
        raise ValueError('input could not be read or parsed') from exc
    if count == 0:
        raise ValueError('at least one ticket is required')
    return {
        'total_tickets': count,
        'total_minutes': sum(v['minutes'] for v in teams.values()),
        'by_team': [{'team': team, **teams[team]} for team in sorted(teams)],
    }
