"""Command-line entry point: invkit FILE [SKU [BUDGET]]."""
from __future__ import annotations

import sys
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from invkit.loader import load_products
from invkit.report import format_report


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not 1 <= len(args) <= 3:
        print("usage: invkit FILE [SKU [BUDGET]]", file=sys.stderr)
        return 2
    try:
        budget = Decimal(args[2]) if len(args) == 3 else None
        print(format_report(load_products(args[0]), args[1] if len(args) > 1 else None, budget))
    except (ValueError, InvalidOperation, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
