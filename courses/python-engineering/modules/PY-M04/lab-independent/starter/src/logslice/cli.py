"""Command-line entry point: logslice FILE [--level LEVEL] | --version."""
from __future__ import annotations

import argparse
from pathlib import Path

from logslice import __version__
from logslice.core import LEVELS, slice_lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="logslice", description="Keep log lines at or above a level.")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--level", default="INFO", choices=sorted(LEVELS, key=LEVELS.get))
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)
    if args.version:
        print(f"logslice {__version__}")
        return 0
    if args.file is None:
        parser.error("a log file is required")
    for line in slice_lines(args.file.read_text(encoding="utf-8").splitlines(), args.level):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
