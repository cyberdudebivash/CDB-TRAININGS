#!/usr/bin/env python3
"""Compute WCAG 2.x contrast ratios for the design tokens and fail if any required pair is below its minimum.

Run:  .venv/bin/python scripts/validation/check_contrast.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "shared" / "design" / "tokens.json"
CSS = ROOT / "shared" / "design" / "cdb-academy.css"


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check() -> tuple[list[dict], list[str]]:
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    rows, problems = [], []
    for theme in ("light", "dark"):
        for pair in tokens["pairs"]:
            fg, bg = tokens[theme][pair["fg"]], tokens[theme][pair["bg"]]
            ratio = contrast(fg, bg)
            ok = ratio >= pair["min"]
            rows.append({"theme": theme, "fg": pair["fg"], "bg": pair["bg"], "ratio": round(ratio, 2), "min": pair["min"], "ok": ok, "use": pair["use"]})
            if not ok:
                problems.append(f"{theme}: {pair['fg']} on {pair['bg']} = {ratio:.2f}:1 < {pair['min']}:1 ({pair['use']})")
    # The CSS must use exactly the token values (no drift).
    css = CSS.read_text(encoding="utf-8")
    for theme, block in (("light", re.search(r":root\s*\{(.*?)\}", css, re.S)), ("dark", re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{(.*?)\}", css, re.S))):
        if not block:
            problems.append(f"css: {theme} variable block not found")
            continue
        for name, value in tokens[theme].items():
            m = re.search(rf"--{name.replace('_', '-')}:\s*(#[0-9a-fA-F]{{6}})", block.group(1))
            if not m or m.group(1).lower() != value.lower():
                problems.append(f"css: --{name.replace('_', '-')} ({theme}) does not match tokens.json ({value})")
    return rows, problems


def main() -> int:
    rows, problems = check()
    for r in rows:
        print(f"{r['theme']:5} {r['fg']:10} on {r['bg']:8} {r['ratio']:>5}:1  (min {r['min']})  {'OK' if r['ok'] else 'FAIL'}  {r['use']}")
    if problems:
        print(f"\ncontrast check FAILED ({len(problems)}):")
        for p in problems:
            print("  -", p)
        return 1
    print(f"\ncontrast check OK: {len(rows)} pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
