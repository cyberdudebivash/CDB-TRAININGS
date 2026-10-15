#!/usr/bin/env python3
"""Render docs/qa/LAB_EXECUTION_EVIDENCE.md from docs/qa/data/lab_execution_<cutoff>.json (deterministic).

Run:  .venv/bin/python scripts/validation/render_lab_evidence.py [--check] [--cutoff 2026-10-14]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LABS = [
    ("m01_guided", "PY-M01 guided", "Public solution passes all 21 provided checks; the starter (every function unimplemented) fails all 21"),
    ("m01_independent", "PY-M01 independent", "Starter fails the published examples; instructor reference passes them, the 34-case hidden suite and the report script, and the hidden suite kills all 16 required mutants (private pack)"),
    ("m02_guided", "PY-M02 guided", "Reference tests kill all 7 mutants; they detect the 3 seeded defects in the starter; the shipped test template is not a solution"),
    ("m02_independent", "PY-M02 independent", "Starter module correct, template empty; instructor reference suite kills all 12 required hidden mutants (private pack)"),
    ("m03_guided", "PY-M03 guided", "Reference package passes all 27 checks (strict mypy, layout, behaviour); the untyped starter passes default mypy, fails --strict and 4 of 5 of its own tests, and fails every package check"),
    ("m03_independent", "PY-M03 independent", "Untyped starter has 27 strict errors and an import cycle that depends on import order and fails all 30 checks; instructor reference passes all 30 (private pack)"),
    ("m04_guided", "PY-M04 guided", "Reference project passes all 10 checks; the legacy starter fails exactly the 6 modernisation checks and still builds"),
    ("m04_independent", "PY-M04 independent", "Starter fails the 7 packaging checks and passes 2; instructor reference overlay passes all 9 (private pack)"),
    ("m05_guided", "PY-M05 guided", "Public solution passes all 65 provided checks against a scripted loopback API (timeouts, retries, pagination, atomic writes); the starter fails all 65"),
    ("m05_independent", "PY-M05 independent", "Starter fails all 8 published checks; instructor reference passes them and the 138-case hidden suite, which kills all 30 seeded defects (private pack)"),
    ("m06_guided", "PY-M06 guided", "Public solution passes all 36 provided checks (bounded runs, collected outcomes, timeouts, backpressure, benchmark helpers); the starter fails all 36; the checks kill 12 of 13 seeded defects of the solution (private pack)"),
    ("m06_independent", "PY-M06 independent", "Starter fails all 10 published checks; instructor reference passes them and the 45-case hidden suite (concurrency limit, speed, event-loop health, deadline, cancellation, safe paths, benchmark report), which kills all 21 seeded defects (private pack)"),
    ("m07_guided", "PY-M07 guided", "Reference passes all checks; starter works but fails exploit/static checks in all 8 areas; reference regression tests kill 8/8 required mutants"),
    ("m07_independent", "PY-M07 independent", "Instructor reference is secure and the starter is not (17 exploit tests fail on it); 9/9 required mutants killed (private pack)"),
    ("m09_guided", "PY-M09 guided", "Public solution passes all 196 provided checks (profiling helpers, hotspot, four algorithms checked against the slow program and for how their work grows, parsing, memory with tracemalloc, core/edge); the starter keeps the 146 correctness checks green and fails the 49 about profiling, speed, memory and structure; the checks kill all 59 seeded defects of the solution (private pack)"),
    ("m09_independent", "PY-M09 independent", "Starter fails the scaling check and the check for learner-written budget tests (2 of 10 published); instructor reference passes all 10 and the 378-case hidden suite (equivalence with the original on random and awkward input, growth of the work, the core's code, the edge, and the learner's own budget tests run against the solution and the original), which kills all 52 seeded defects (private pack)"),
    ("m12_guided", "PY-M12 guided", "Public solution passes all 167 provided checks (value types, per-instance state, observers, fee policies, registry, composition); the starter fails all 167; the checks kill all 47 seeded defects of the solution (private pack)"),
    ("m12_independent", "PY-M12 independent", "Starter fails all 10 published checks; instructor reference passes them and the 54-case hidden suite (value semantics, operators, isolation, error recording, subscriber rules, refusal), which kills all 41 seeded defects (private pack)"),
    ("m13_guided", "PY-M13 guided", "Public solution passes all 128 provided checks (a generator that owns a file, lazy parsing, chunks and windows with eager argument checks, decorators, context managers); the starter fails all 128; the checks kill all 49 seeded defects of the solution (private pack)"),
    ("m13_independent", "PY-M13 independent", "Starter fails all 10 published checks; instructor reference passes them and the 63-case hidden suite (lazy merge with counted consumption and cleanup of sources, grouping, bounded memo cache, nested rollback), which kills all 35 seeded defects (private pack)"),
    ("m08_guided", "PY-M08 guided", "Public solution passes all 200 provided checks (the first increment's 14 contract tests plus validation edges, migrations, atomic batches, injection-safe search, retention and query shape); the starter fails all 200; the checks kill all 95 seeded defects of the solution (private pack)"),
    ("m08_independent", "PY-M08 independent", "Starter fails all 10 published checks; instructor reference passes them and the 145-case hidden suite (optimistic concurrency, rollback on every path including interrupts, import, hostile input, the upgrade of the first release's database, statement counts and SQLite work), which kills all 83 seeded defects (private pack)"),
]
SYMBOL = {"passed": "pass", "failed": "FAIL", "error": "ERROR", "skipped": "skipped"}


def md(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    return "\n".join(out + ["| " + " | ".join(md(c) for c in r) + " |" for r in rows])


def lab_key(test_id: str) -> str | None:
    m = re.search(r"test_(m\d\d)_(guided|independent)", test_id)
    return f"{m.group(1)}_{m.group(2)}" if "test_python_engineering_labs" in test_id and m else None


def render(data: dict) -> str:
    cut = data["cutoff"]
    interps = data["interpreters"]
    lines = ["# Lab Execution Evidence", "",
             "> Generated by `scripts/validation/render_lab_evidence.py` from `docs/qa/data/lab_execution_" + cut + ".json`, which is written by `scripts/validation/run_lab_matrix.py`. Do not edit by hand.",
             f"> Research cutoff (Stage A): **{cut}**. Stage B (2026-10-24) re-execution: `PENDING_FUTURE_REFRESH`.", "",
             "## 1. What this records", "",
             "Execution of the Python Engineering labs (PY-M01 to PY-M07) and of the module-pack checks that run every lesson code block and verify outcome traceability. "
             "Each interpreter row is a **fresh virtual environment** with the pinned toolchain from `courses/python-engineering/labs/requirements.txt`; the suites run with that environment's interpreter, "
             "and the lab tests start their own sub-processes with it, so the build, install, mutation and exploit steps ran on that Python version.", "",
             "A lab is called *executed* here only for the interpreters listed below, in this environment, at the stated commit. It is not evidence of learner success, subject-matter correctness review, or behaviour on other operating systems.", "",
             "## 2. Run provenance", "",
             table(["Item", "Value"], [
                 ["Commit at run time", f"`{data['commit']}`" + (" (working tree had uncommitted tracked changes)" if data["working_tree_dirty"] else " (clean tracked tree)")],
                 ["Run (UTC)", data["run_utc"]], ["Host", data["host"]],
                 ["Instructor pack present in the environment", "yes - private-material tests were executed" if data["private_instructor_pack_present"] else "no - private-material tests were skipped"],
                 ["Toolchain pins", f"`{data['requirements_file']}`"], ["Suites", ", ".join(f"`{s}`" for s in data["suites"])]]), "",
             "## 3. Interpreter matrix", ""]
    rows = []
    for r in interps:
        pk = r.get("packages", {})
        c = r.get("counts", {})
        rows.append([r["requested"], f"{r.get('implementation', '-')} {r.get('python', '-')}", r["interpreter_source"], pk.get("pytest", "-"), pk.get("ruff", "-"), pk.get("setuptools", "-"), pk.get("build", "-"),
                     r["status"] if r["status"] != "NOT_EXECUTED" else f"NOT_EXECUTED: {r.get('reason', '')}",
                     f"{c.get('passed', 0)} / {c.get('failed', 0) + c.get('error', 0)} / {c.get('skipped', 0)}", r.get("duration_s", "-")])
    lines += [table(["Requested", "Interpreter", "Source", "pytest", "ruff", "setuptools", "build", "Status", "Passed / failed / skipped", "Seconds"], rows), "",
              "Interpreters from `uv` are python-build-standalone builds, not python.org installers; behaviour on distribution-packaged or Windows/macOS interpreters is not claimed.", ""]
    lines += ["## 4. Per-lab outcome by interpreter", "",
              "`pass` means the test asserting the lab property passed on that interpreter. The property each test asserts is listed in the second column.", ""]
    ok = [r for r in interps if r["status"] != "NOT_EXECUTED"]
    head = ["Lab", "Property checked"] + [r["requested"] for r in ok]
    rows = []
    for key, label, prop in LABS:
        row = [label, prop]
        for r in ok:
            outs = [t["outcome"] for t in r["tests"] if lab_key(t["id"]) == key]
            if not outs:
                row.append("not run")
            elif all(o == "passed" for o in outs):
                row.append(f"pass ({len(outs)})")
            elif any(o in ("failed", "error") for o in outs):
                row.append(f"FAIL ({sum(o in ('failed', 'error') for o in outs)} of {len(outs)})")
            else:
                row.append(f"skipped ({sum(o == 'skipped' for o in outs)} of {len(outs)})" if any(o == "passed" for o in outs) else "skipped")
        rows.append(row)
    lines += [table(head, rows), "", "## 5. Module-pack checks (lessons, outcomes, quizzes, rubrics, source maps)", ""]
    rows = []
    for r in ok:
        packs = [t for t in r["tests"] if "test_module_packs" in t["id"]]
        runs = [t for t in packs if "test_lesson_code_blocks_execute" in t["id"]]
        rows.append([r["requested"], len(packs), sum(t["outcome"] == "passed" for t in packs), len(runs), sum(t["outcome"] == "passed" for t in runs)])
    lines += [table(["Interpreter", "Checks", "Passed", "Lesson code-block runs", "Passed"], rows), "",
              "Each lesson's `python run`, `python module` and `python test` blocks are executed by `scripts/validation/lesson_blocks.py`; a lesson with no executable example fails the check.", "",
              "## 6. Skipped tests", ""]
    skipped = {}
    for r in ok:
        for s in r["skipped"]:
            skipped.setdefault((s["id"], s["reason"]), []).append(r["requested"])
    if skipped:
        lines += [table(["Test", "Reason", "Interpreters"], [[k[0], k[1], ", ".join(v)] for k, v in sorted(skipped.items())]), "",
                  "`SKIPPED_PRIVATE_MATERIALS` means the instructor pack was absent: the property was **not verified** in that run."]
    else:
        lines.append("None.")
    lines += ["", "## 7. Not verified by this evidence", "",
              "- Windows and macOS (the shell-injection probe is POSIX-only; symbolic-link and file-mode checks differ).",
              "- CPython releases not listed in section 3, including 3.10 and earlier (end of life) and any build other than the ones named.",
              "- Installation of the lab toolchain from an index other than PyPI, or with different versions than the pins.",
              "- Any learner's own solution; whether the quiz items discriminate; whether the time estimates are right (no learner pilot has been run).",
              "- Subject-matter correctness: no SME review of lessons, labs or quizzes has taken place.",
              "- Behaviour after 2026-10-14: the Stage B refresh has not been performed.", "",
              "## 8. Reproduce", "",
              "```bash",
              "python -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements.txt",
              "python scripts/validation/run_lab_matrix.py --versions 3.11,3.12,3.13,3.14,3.15   # needs network access to PyPI; `uv python install 3.14 3.15` supplies newer interpreters",
              "python scripts/validation/render_lab_evidence.py",
              "```", ""]
    notes_path = ROOT / "docs" / "qa" / "data" / "lab_matrix_notes.yaml"
    if notes_path.exists():
        import yaml

        notes = yaml.safe_load(notes_path.read_text(encoding="utf-8")).get("notes", [])
        if notes:
            lines += ["## Issues the matrix found, and what was done", ""]
            lines += [f"- **{n['date']}, CPython {n['interpreter']}:** {n['finding']} {n['action']}" for n in notes] + [""]
    failed = [r for r in interps if r["status"] == "FAIL"]
    if failed:
        lines += ["## Failures recorded", ""] + [f"- CPython {r['requested']}: see `failure_tail` in the JSON." for r in failed] + [""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--cutoff", default="2026-10-14")
    a = ap.parse_args()
    src = ROOT / "docs" / "qa" / "data" / f"lab_execution_{a.cutoff}.json"
    out = ROOT / "docs" / "qa" / "LAB_EXECUTION_EVIDENCE.md"
    text = render(json.loads(src.read_text(encoding="utf-8"))).rstrip() + "\n"
    if a.check:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print("DRIFT: docs/qa/LAB_EXECUTION_EVIDENCE.md")
            return 1
        return 0
    out.write_text(text, encoding="utf-8")
    print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
