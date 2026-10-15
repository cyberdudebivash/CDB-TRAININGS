"""Read-only local diagnostic CLI for synthetic support events (Python 3.11+).

No shell=True, network access, subprocesses, filesystem writes or real customer data.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import sys

LEVELS = {"INFO": 0, "WARN": 1, "ERROR": 2}
EXPECTED = ["timestamp", "service", "severity", "message"]
MAX_SIZE = 64 * 1024


def _safe_file(root: Path, relative: str) -> Path:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("root must be an existing non-symlink directory")
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise ValueError("input must be a relative POSIX-style path")
    parts = relative.split("/")
    if any(p in ("", ".", "..") for p in parts) or Path(relative).is_absolute() or ":" in relative:
        raise ValueError("invalid relative input path")
    candidate = root
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("symbolic links are not permitted")
    if not candidate.is_file() or candidate.stat().st_size > MAX_SIZE:
        raise ValueError("input must be a regular file of at most 65536 bytes")
    return candidate


def scan(root: Path, relative: str, min_severity: str = "INFO") -> list[dict[str, str]]:
    if min_severity not in LEVELS:
        raise ValueError("min_severity must be INFO, WARN or ERROR")
    source = _safe_file(Path(root), relative)
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != EXPECTED:
            raise ValueError("input CSV has incorrect header")
        matched = []
        seen = set()
        count = 0
        for row in reader:
            count += 1
            if count > 1000 or None in row or any(v is None for v in row.values()):
                raise ValueError("invalid row or row limit exceeded")
            if any(not row[k].strip() for k in EXPECTED):
                raise ValueError("empty required value")
            try:
                dt = datetime.fromisoformat(row["timestamp"])
            except ValueError as exc:
                raise ValueError("invalid ISO timestamp") from exc
            if dt.tzinfo is None or dt.utcoffset() is None:
                raise ValueError("timestamp must include timezone")
            if row["severity"] not in LEVELS:
                raise ValueError("unknown severity")
            if len(row["service"]) > 80 or len(row["message"]) > 200:
                raise ValueError("field too long")
            row_id = (row["timestamp"], row["service"], row["severity"], row["message"])
            if row_id in seen:
                raise ValueError("duplicate event")
            seen.add(row_id)
            if LEVELS[row["severity"]] >= LEVELS[min_severity]:
                matched.append(dict(row))
        return matched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local synthetic incident-event inspector")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--min-severity", choices=list(LEVELS), default="INFO")
    parser.add_argument("--fail-on-error", action="store_true", help="return 3 if any matching ERROR event exists")
    args = parser.parse_args(argv)
    try:
        events = scan(args.root, args.input, args.min_severity)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"INPUT_ERROR: {type(exc).__name__} (check lab contract)", file=sys.stderr)
        return 2
    print(json.dumps({"count": len(events), "events": events}, sort_keys=True, ensure_ascii=False))
    return 3 if args.fail_on_error and any(e["severity"] == "ERROR" for e in events) else 0


if __name__ == "__main__":
    raise SystemExit(main())
