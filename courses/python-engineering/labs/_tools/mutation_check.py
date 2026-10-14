#!/usr/bin/env python3
"""Hand-rolled mutation check used by the PY-M02 labs.

A learner's tests are judged by what they *catch*: the tests must pass on the correct module and must fail on every
mutant (the correct module with exactly one defect injected). A mutant that still passes all tests is a "survivor" and
tells the learner which behaviour is untested.

Usage:
    python mutation_check.py --module-dir DIR --module NAME --tests DIR_OR_FILE --mutants FILE.json [--json]

    --module-dir   directory that contains the CORRECT NAME.py
    --mutants      JSON list of {"id", "description", "old", "new", "required"}; `old` must occur exactly once in NAME.py

Exit code 0 when the tests pass on the correct module and every `required` mutant is killed, 1 otherwise.
Optional mutants (required=false) are reported but do not fail the check.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_pytest(tests: Path, module_dir: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(module_dir) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Run from an empty directory: `python -m pytest` puts the current directory first on sys.path, which would let a
    # copy of the correct module next to the tests shadow the mutant under test.
    with tempfile.TemporaryDirectory() as neutral:
        proc = subprocess.run([sys.executable, "-m", "pytest", str(tests), "-q", "-p", "no:cacheprovider", "--no-header", "-x", "--tb=line", "--import-mode=importlib",
                               "-o", f"pythonpath={module_dir}"],  # overrides a lab pytest.ini that points at the learner's copy
                              capture_output=True, text=True, env=env, timeout=300, cwd=neutral)
    return proc.returncode, (proc.stdout + proc.stderr)


def check(module_dir: Path, module: str, tests: Path, mutants: list[dict]) -> dict:
    source = (module_dir / f"{module}.py").read_text(encoding="utf-8")
    report: dict = {"module": module, "tests": str(tests), "baseline_passes": None, "mutants": []}
    rc, out = run_pytest(tests, module_dir)
    report["baseline_passes"] = rc == 0
    report["baseline_tail"] = out.strip().splitlines()[-3:]
    for m in mutants:
        if source.count(m["old"]) != 1:
            raise SystemExit(f"mutant {m['id']}: `old` must occur exactly once in {module}.py (found {source.count(m['old'])})")
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / f"{module}.py").write_text(source.replace(m["old"], m["new"]), encoding="utf-8")
            rc_m, out_m = run_pytest(tests, Path(td))
        # pytest exit codes: 0 all passed, 1 tests failed, 2 interrupted/collection error, 5 no tests collected.
        # "No tests" must never count as detecting a defect, so only 1 and 2 kill a mutant.
        report["mutants"].append({"id": m["id"], "description": m["description"], "required": m.get("required", True), "killed": rc_m in (1, 2),
                                  "first_failure": next((ln for ln in out_m.splitlines() if "assert" in ln.lower() or "Error" in ln or "FAILED" in ln), "")[:200]})
    required = [m for m in report["mutants"] if m["required"]]
    report["required_killed"] = sum(1 for m in required if m["killed"])
    report["required_total"] = len(required)
    report["all_killed"] = sum(1 for m in report["mutants"] if m["killed"])
    report["total"] = len(report["mutants"])
    report["passed"] = bool(report["baseline_passes"]) and report["required_killed"] == report["required_total"]
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module-dir", required=True, type=Path)
    ap.add_argument("--module", required=True)
    ap.add_argument("--tests", required=True, type=Path)
    ap.add_argument("--mutants", required=True, type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    mutants = json.loads(a.mutants.read_text(encoding="utf-8"))
    report = check(a.module_dir.resolve(), a.module, a.tests.resolve(), mutants)
    if a.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Tests pass on the correct module: {'yes' if report['baseline_passes'] else 'NO'}")
        for m in report["mutants"]:
            tag = "killed  " if m["killed"] else "SURVIVED"
            print(f"  {tag} {m['id']}{'' if m['required'] else ' (stretch)'}: {m['description']}")
        print(f"Required mutants killed: {report['required_killed']}/{report['required_total']}; all mutants killed: {report['all_killed']}/{report['total']}")
        print("RESULT:", "PASS" if report["passed"] else "NOT YET - add tests for the surviving behaviours")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
