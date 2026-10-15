"""Execute the code blocks of a lesson so that every example the learner reads has actually run.

Fence info strings understood (first token must be `python`):
    ```python run              standalone script; must exit 0 (use assert for the expectations)
    ```python module=NAME      written to NAME.py in a scratch directory; imported by later `test` blocks
    ```python test             written to its own test file and executed with `python -m pytest`
Any other fence (text, bash, yaml, plain python) is ignored here.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

FENCE = re.compile(r"^```(?P<info>[^\n]*)\n(?P<body>.*?)^```[ \t]*$", re.M | re.S)


@dataclass
class Block:
    line: int
    kind: str          # run | module | test
    name: str
    body: str


def extract(markdown: str) -> list[Block]:
    out: list[Block] = []
    for m in FENCE.finditer(markdown):
        tokens = m.group("info").split()
        if not tokens or tokens[0] != "python" or len(tokens) < 2:
            continue
        line = markdown.count("\n", 0, m.start()) + 1
        tag = tokens[1]
        if tag == "run":
            out.append(Block(line, "run", "", m.group("body")))
        elif tag == "test":
            out.append(Block(line, "test", "", m.group("body")))
        elif tag.startswith("module="):
            out.append(Block(line, "module", tag.split("=", 1)[1], m.group("body")))
    return out


def execute(markdown: str, python: str = sys.executable, timeout: int = 120) -> list[dict]:
    """Run all blocks of one lesson in a scratch directory. Returns one result dict per block."""
    results: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        for b in extract(markdown):
            if b.kind == "module":
                (scratch / f"{b.name}.py").write_text(b.body, encoding="utf-8")
                results.append({"line": b.line, "kind": "module", "ok": True, "detail": f"wrote {b.name}.py"})
            elif b.kind == "run":
                f = scratch / f"run_{b.line}.py"
                f.write_text(b.body, encoding="utf-8")
                p = subprocess.run([python, str(f)], cwd=scratch, capture_output=True, text=True, timeout=timeout)
                results.append({"line": b.line, "kind": "run", "ok": p.returncode == 0, "detail": (p.stdout + p.stderr).strip()[-400:]})
            else:
                f = scratch / f"test_block_{b.line}.py"
                f.write_text(b.body, encoding="utf-8")
                p = subprocess.run([python, "-m", "pytest", str(f), "-q", "-p", "no:cacheprovider", "--no-header"], cwd=scratch,
                                   capture_output=True, text=True, timeout=timeout)
                results.append({"line": b.line, "kind": "test", "ok": p.returncode == 0, "detail": (p.stdout + p.stderr).strip()[-400:]})
    return results
