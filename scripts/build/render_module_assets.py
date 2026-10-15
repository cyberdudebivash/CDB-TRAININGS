#!/usr/bin/env python3
"""Render student-facing assessment files from their sources of truth.

For every courses/*/modules/*/assessment/quiz.yaml this writes quiz.md (questions and options only; the answer key is private).
`--check` exits 1 when a quiz.md on disk differs from the rendered text.

Run:  .venv/bin/python scripts/build/render_module_assets.py [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def esc(text: str) -> str:
    return str(text).replace("|", "\\|")


def render_quiz(quiz: dict) -> str:
    items = quiz["items"]
    lines = [f"# {quiz['module']} knowledge check ({len(items)} questions)", "",
             "Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). "
             "The answer key is held by instructors and is not published.",
             "Questions are generated from `quiz.yaml`; each is tied to a learning outcome.", "",
             "| # | Outcome | Question | Options |", "|---|---|---|---|"]
    for it in items:
        opts = " ".join(f"{k}) {esc(v)}{'' if str(v).endswith(('.', '?')) else '.'}" for k, v in it["options"].items())
        lines.append(f"| {it['id']} | {it['outcome']} | {esc(it['stem'])} | {opts} |")
    lines += ["", f"**Scoring:** instructors apply the key; {max(1, round(len(items) * 0.75))}/{len(items)} is the formative checkpoint.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    bad = []
    for qy in sorted(ROOT.glob("courses/*/modules/*/assessment/quiz.yaml")):
        text = render_quiz(yaml.safe_load(qy.read_text(encoding="utf-8")))
        out = qy.with_name("quiz.md")
        if a.check:
            if not out.exists() or out.read_text(encoding="utf-8") != text:
                bad.append(str(out.relative_to(ROOT)))
        else:
            out.write_text(text, encoding="utf-8")
            print(f"wrote {out.relative_to(ROOT)}")
    if bad:
        print("DRIFT:", *bad, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
