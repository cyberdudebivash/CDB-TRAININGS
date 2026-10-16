#!/usr/bin/env python3
"""Automated learner dry run: what a person who only has the published repository sees, in a clean checkout and a clean virtual environment.

This is NOT a learner pilot and nothing here is evidence of learning. It checks that the published material is self-contained, which the main test run cannot show because
that run happens in a working tree that also holds untracked files and the private instructor pack.

For every module that has a lab it
  1. extracts the committed files (git archive HEAD) into a fresh directory, so nothing untracked or git-ignored can leak in,
  2. creates a fresh virtual environment and installs the pinned requirements from that checkout,
  3. runs the guided lab's checks against the starter: they must fail (the lab has work to do) and none may error at collection (a broken fixture is not a lab),
  4. runs them against the public solution (LAB_TARGET=solution) when the module ships one: all must pass, none skipped,
  5. runs the independent lab's published checks against its starter: they must run and fail without a collection error (the reference solution is private).
The result is recorded in docs/production/data/learner_dry_run.json with the content fingerprint of each module, so Gate A can tell when it is stale.

Run: .venv/bin/python scripts/validation/learner_dry_run.py [--python python3.13] [--only PY-M05]
Refuses to run when files under a module's execution inputs are modified or untracked: the dry run tests HEAD and must describe HEAD.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_fingerprint as EF  # noqa: E402

OUT = ROOT / "docs" / "production" / "data" / "learner_dry_run.json"


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)


def counts(junit: Path) -> dict:
    c = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    if not junit.exists():
        return {**c, "errors": 1}
    for tc in ET.parse(junit).getroot().iter("testcase"):
        key = "failed" if tc.find("failure") is not None else "errors" if tc.find("error") is not None else "skipped" if tc.find("skipped") is not None else "passed"
        c[key] += 1
    return c


def run_checks(py: str, lab: Path, work: Path, target: str | None) -> dict:
    junit = work / f"{lab.parent.name}-{lab.name}-{target or 'starter'}.xml"
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    if target:
        env["LAB_TARGET"] = target
    proc = sh([py, "-m", "pytest", f"--junitxml={junit}", "-q", "-p", "no:randomly"], cwd=lab, env=env, timeout=900)
    return {**counts(junit), "returncode": proc.returncode}


def testpaths(lab: Path) -> str:
    cfg = configparser.ConfigParser()
    cfg.read(lab / "pytest.ini")
    return cfg.get("pytest", "testpaths", fallback="").strip()


def is_graded(lab: Path) -> bool:
    """A lab is graded by checks/ when its pytest.ini points there, or when it has no pytest.ini testpaths at all and a checks/ folder (plain `python -m pytest` in the lab then runs the checks, which the READMEs tell learners to do).
    Labs whose pytest.ini points elsewhere (the write-your-own-tests labs, graded by the mutation tool) are not."""
    paths = testpaths(lab)
    return paths == "checks" or (paths == "" and (lab / "checks").is_dir())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--python", default=sys.executable, help="interpreter used to create the clean environment")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args(argv)
    modules = []
    for lesson in sorted((ROOT / "courses").glob("*/modules/*/lesson.md")):
        slug, mid = lesson.parts[-4], lesson.parts[-2]
        if a.only and mid not in a.only:
            continue
        if (lesson.parent / "lab-guided").is_dir() and (lesson.parent / "lab-independent").is_dir():
            modules.append((slug, mid))
    for slug, mid in modules:
        dirty = sh(["git", "status", "--porcelain", "--untracked-files=all", "--", *EF.execution_inputs(slug, mid)], cwd=ROOT).stdout.strip()
        if dirty:
            print(f"refusing to run: uncommitted changes under the inputs of {mid}; commit them first (the dry run tests HEAD)", file=sys.stderr)
            return 2
    head = sh(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT).stdout.strip()
    result = {"schema_version": 1, "commit": head, "tracked_files_only": True, "is_learner_pilot": False, "modules": {}}
    with tempfile.TemporaryDirectory(prefix="dry-run-", dir=ROOT / ".work") as td:
        work = Path(td)
        tree = work / "tree"
        tree.mkdir()
        archive = work / "head.tar"
        sh(["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], cwd=ROOT)
        with tarfile.open(archive) as tf:
            tf.extractall(tree, filter="data")
        venv = work / "venv"
        sh([a.python, "-m", "venv", str(venv)])
        py = str(venv / "bin" / "python")
        inst = sh([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(tree / "courses" / "python-engineering" / "labs" / "requirements.txt")], timeout=1800)
        if inst.returncode != 0:
            print("pip install failed:", inst.stderr[-400:], file=sys.stderr)
            return 2
        result["python"] = sh([py, "-c", "import platform;print(platform.python_version())"]).stdout.strip()
        for slug, mid in modules:
            base = tree / "courses" / slug / "modules" / mid
            guided, independent = base / "lab-guided", base / "lab-independent"
            graded = is_graded(guided)           # labs graded by checks/; the others (write-your-own-tests labs) are graded by the mutation tool
            starter = run_checks(py, guided, work, None)
            solution = run_checks(py, guided, work, "solution") if graded and (guided / "solution").is_dir() else None
            indep = run_checks(py, independent, work, None)
            indep_graded = testpaths(independent) == "checks"
            ok = (starter["errors"] == 0 and (not graded or (starter["failed"] >= 1 and starter["returncode"] != 0))
                  and (solution is None or (solution["returncode"] == 0 and solution["failed"] == 0 and solution["errors"] == 0 and solution["skipped"] == 0 and solution["passed"] >= 1))
                  and indep["errors"] == 0 and (not indep_graded or (indep["failed"] >= 1 and indep["returncode"] != 0)))
            result["modules"][mid] = {"fingerprint": EF.fingerprint(EF.execution_inputs(slug, mid)), "guided_starter": starter, "guided_solution": solution, "independent_starter": indep, "ok": ok}
            print(f"{mid}: guided starter fails {starter['failed']} (errors {starter['errors']}), solution {'-' if solution is None else str(solution['passed']) + ' pass'}, independent starter fails {indep['failed']} (errors {indep['errors']}): {'OK' if ok else 'PROBLEM'}")
        shutil.rmtree(venv, ignore_errors=True)
    if a.only and OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        merged = {**previous["modules"], **result["modules"]}
        result["modules"] = {k: merged[k] for k in sorted(merged)}
    OUT.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))
    return 0 if all(m["ok"] for m in result["modules"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
