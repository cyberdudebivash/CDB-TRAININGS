#!/usr/bin/env python3
"""Rebuild existing student module PREVIEW PDFs; never claim full-course approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "scripts/build/build_student_edition.py"


def configs() -> list[Path]:
    soc = ROOT / "courses/soc-analyst/student/student-edition.yaml"
    py = sorted((ROOT / "courses/python-engineering/student").glob("PY-M*-student-edition.yaml"))
    return ([soc] if soc.is_file() else []) + py


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", nargs="*", default=[], metavar="MODULE")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    args = ap.parse_args()
    found = []
    for p in configs():
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not all(k in data for k in ("module", "edition", "version", "title")):
            print(f"Invalid preview configuration: {p}", file=sys.stderr)
            return 2
        if "premium edition" in str(data["title"]).lower():
            print(f"Refusing unapproved premium title: {p}", file=sys.stderr)
            return 2
        found.append((p, data))
    known = {c["module"] for _, c in found}
    if unknown := (set(args.only) - known):
        print(f"Unknown module(s): {sorted(unknown)}", file=sys.stderr)
        return 2
    if args.list:
        for p, c in found:
            print(f"{c['module']}: {c['title']} ({p.relative_to(ROOT)})")
        return 0
    selected = [(p, c) for p, c in found if not args.only or c["module"] in args.only]
    if not selected:
        print("No available preview builds.", file=sys.stderr)
        return 2
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for p, c in selected:
        stem = f"{c['module']}-{c['edition']}-{c['version']}"
        pdf, manifest = output / (stem + ".pdf"), output / (stem + ".manifest.json")
        # Never mistake an earlier build for the current one.
        pdf.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        row = {"module": c["module"], "state": "MODULE_PREVIEW_NOT_TRAINING_CONTENT_GO"}
        try:
            cmd = [sys.executable, str(RENDERER), "--config", str(p), "--out", str(output), "--strict"]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
            row["renderer_exit"] = run.returncode
            row["stdout_tail"] = run.stdout[-1000:]
            row["stderr_tail"] = run.stderr[-1000:]
            if run.returncode or not pdf.is_file() or not manifest.is_file():
                raise RuntimeError("strict renderer failed or files missing")
            evidence = json.loads(manifest.read_text(encoding="utf-8"))
            digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
            if not evidence.get("passed") or evidence.get("pdf", {}).get("sha256") != digest:
                raise RuntimeError("PDF manifest validation or checksum failed")
            if any(evidence.get("problems", {}).values()):
                raise RuntimeError("unresolved PDF quality issue")
            row.update(status="PASS", pdf=str(pdf), pages=evidence["pdf"]["pages"], sha256=digest)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            row.update(status="FAIL", reason=str(exc))
        results.append(row)
        print(f"{row['module']}: {row['status']}", flush=True)
    report = {
        "classification": "UNREVIEWED_MODULE_PREVIEW_ONLY",
        "complete_course_editions": 0,
        "builds": results,
        "passed": sum(r["status"] == "PASS" for r in results),
        "failed": sum(r["status"] == "FAIL" for r in results),
    }
    path = output / "module-preview-build-report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Report: {path}; strict previews {report['passed']}/{len(results)}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
