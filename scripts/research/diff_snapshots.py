#!/usr/bin/env python3
"""Compare two registry snapshots (docs/research/data/registry_snapshot_<cutoff>.json) and list what changed.

Used for the Stage B refresh: run fetch_registry_versions.py with the later cutoff, then

    python scripts/research/diff_snapshots.py docs/research/data/registry_snapshot_2026-10-14.json docs/research/data/registry_snapshot_2026-10-24.json

Output is deterministic Markdown on stdout. Exit code is 0 either way (a diff is information, not a failure).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict[tuple[str, str], dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {(r["tech_id"], r["kind"]): r for r in data["records"]}


def describe(rec: dict | None) -> str:
    if rec is None:
        return "(absent)"
    cur = rec.get("current")
    return f"{cur['version']} ({cur['date']})" if cur else f"no version ({rec.get('status', 'n/a')})"


def diff(old: dict, new: dict) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if describe(a) != describe(b):
            kind = "added" if a is None else "removed" if b is None else "changed"
            rows.append((key[0], key[1], describe(a), describe(b), kind))
    return rows


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    rows = diff(load(argv[0]), load(argv[1]))
    print(f"# Snapshot diff: {Path(argv[0]).name} -> {Path(argv[1]).name}\n")
    print(f"{len(rows)} technology records differ.\n")
    if rows:
        print("| Technology | Source | Before | After | Change |\n|---|---|---|---|---|")
        for r in rows:
            print("| " + " | ".join(r) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
