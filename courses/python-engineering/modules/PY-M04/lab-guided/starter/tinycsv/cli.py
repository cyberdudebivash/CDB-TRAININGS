"""Command-line entry point: tinycsv-summary FILE."""
from __future__ import annotations

import sys

from tinycsv import __version__
from tinycsv.summary import summarise


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--version"]:
        print(f"tinycsv {__version__}")
        return 0
    if len(args) != 1:
        print("usage: tinycsv-summary FILE | --version", file=sys.stderr)
        return 2
    info = summarise(args[0])
    print(f"rows: {info['rows']}")
    print(f"columns: {', '.join(info['columns'])}")
    print(f"numeric columns: {', '.join(info['numeric_columns']) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
