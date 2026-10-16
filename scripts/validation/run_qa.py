#!/usr/bin/env python3
"""Run the repository QA suite and write machine-readable evidence plus the generated reports.

Outputs (all regenerated; never hand-edited):
  docs/release/data/qa_run.json            raw results of this run
  docs/release/AUTOMATED_QA_REPORT.md      human-readable summary of exactly what ran and what it proved

Release gating is computed elsewhere (scripts/production/gate_a.py, rendered to docs/production/); this script runs the checks that feed it and
adds three of them: the personal-data guard, the Gate A validator and the freshness of the generated Gate A documents.
The run never changes catalog/courses.yaml; it reports, it does not promote.

Run:  .venv/bin/python scripts/validation/run_qa.py [--skip-build]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_env import restore_default_sigint  # noqa: E402

DATA_DIR = ROOT / "docs" / "release" / "data"
LABS = ROOT / "courses" / "soc-analyst" / "labs"
INSTRUCTOR = ROOT / "courses" / "soc-analyst" / "instructor"
PY = sys.executable

def run(cmd: list[str], cwd: Path = ROOT, env: dict | None = None, timeout: int = 900) -> tuple[int, str]:
    e = dict(os.environ)
    e.setdefault("PYTHONHASHSEED", "0")
    if env:
        e.update(env)
    p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def sh(cmd: list[str]) -> str:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout.strip()


def tree_hash(path: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ individual checks
def check_catalog() -> dict:
    code, out = run([PY, "scripts/validation/validate_catalog.py"])
    return {"id": "catalog", "title": "Catalog schema and cross-reference validation", "status": "PASS" if code == 0 else "FAIL", "detail": out.strip().splitlines()[-1] if out.strip() else ""}


def check_contrast() -> dict:
    code, out = run([PY, "scripts/validation/check_contrast.py"])
    return {"id": "design-contrast", "title": "Design-token WCAG contrast pairs", "status": "PASS" if code == 0 else "FAIL", "detail": out.strip().splitlines()[-1] if out.strip() else ""}


def check_audit_render_is_current() -> dict:
    """Regenerating the audit documents from the data files must not change the committed files."""
    before = tree_hash(ROOT / "docs" / "audits")
    code, out = run([PY, "scripts/inventory/render_audits.py"])
    after = tree_hash(ROOT / "docs" / "audits")
    status = "PASS" if code == 0 and before == after else "FAIL"
    detail = "generated audit documents are reproducible from data files" if status == "PASS" else ("render failed: " + out[-300:] if code else "generated documents differ from the files on disk; re-run render_audits.py and commit")
    return {"id": "audit-render", "title": "Audit documents reproducible from findings/scores data", "status": status, "detail": detail}


def _script_check(check_id: str, title: str, cmd: list[str], ok_detail: str) -> dict:
    code, out = run([PY, *cmd])
    last = out.strip().splitlines()[-1] if out.strip() else ""
    return {"id": check_id, "title": title, "status": "PASS" if code == 0 else "FAIL", "detail": ok_detail if code == 0 else (last or "failed")}


def check_modernization_evidence(include_page_rebuild: bool = True) -> list[dict]:
    """October 2026 evidence chain: references resolve, generated documents and page records reproduce from their inputs."""
    out = [
        _script_check("modernization-data", "Modernization, new-development and rule data: every F-/R-/probe/snapshot/module reference resolves",
                      ["scripts/audit/validate_modernization_data.py"], "all evidence references resolve"),
        _script_check("audit-docs-render", "Generated audit documents (complete audit, traceability, matrix, per-course logs) reproduce from data",
                      ["scripts/audit/render_audit_docs.py", "--check"], "documents match the data"),
        _script_check("curriculum-docs-render", "Generated curriculum documents (skill pathways, competency outcomes) reproduce from the catalog",
                      ["scripts/build/render_curriculum_2026.py", "--check"], "documents match the catalog"),
        _script_check("readiness-docs-render", "Generated readiness, premium-catalog, Stage B checklist and QA documents reproduce from data",
                      ["scripts/build/render_readiness_2026.py", "--check"], "documents match the data"),
        _script_check("lab-evidence-render", "Lab execution evidence report reproduces from its recorded JSON",
                      ["scripts/validation/render_lab_evidence.py", "--check"], "report matches the recorded run"),
        _script_check("module-assets-render", "Generated quiz files (questions only) reproduce from quiz.yaml",
                      ["scripts/build/render_module_assets.py", "--check"], "quiz files match"),
        _script_check("research-docs-render", "Generated research documents (baselines, verification, new developments) reproduce from data",
                      ["scripts/research/render_research_docs.py", "--check"], "documents match the data"),
    ]
    if include_page_rebuild:
        out.append(_script_check("page-records-rebuild", "Page records (8,186 pages) reproduce from the source PDFs, rules and mapping",
                                 ["scripts/audit/build_page_records.py", "--check"], "committed page records equal a fresh rebuild"))
    return out


def check_gate_a() -> list[dict]:
    """Personal-data guard, Gate A validator (claims must not exceed evidence) and freshness of the generated Gate A documents."""
    return [
        _script_check("known-source-quarantine", "Known personal-data source cannot be tracked in the distributable repository tree",
                      ["scripts/validation/check_public_source_exposure.py"], "current Git index excludes the known source; historical exposure is separate"),
        _script_check("privacy-guard", "No e-mail address or telephone number outside the reviewed allow-list in any authored or generated text file",
                      ["scripts/validation/check_privacy.py"], "no personal-data-shaped string found"),
        _script_check("gate-a-validator", "Gate A validator: no status, review or scenario claims more than the evidence supports; no placeholder in finished content",
                      ["scripts/validation/validate_gate_a.py"], "all Gate A claims are within the evidence"),
        _script_check("gate-a-docs-render", "Gate A acceptance documents (docs/production/) reproduce from the evidence",
                      ["scripts/production/render_production_docs.py", "--check"], "documents match the data"),
    ]


def soc_fingerprint() -> str:
    """Content fingerprint of the SOC pilot module (lesson, labs, assessments), so Gate A can tell whether this QA run still describes the current files."""
    sys.path.insert(0, str(ROOT / "scripts" / "production"))
    import gate_a
    return gate_a.EF.fingerprint(gate_a.SOC_FINGERPRINT_INPUTS)


def run_pytest() -> tuple[dict, list[dict]]:
    with tempfile.TemporaryDirectory() as td:
        xml_path = Path(td) / "junit.xml"
        code, out = run([PY, "-m", "pytest", f"--junitxml={xml_path}", "-rs", "-p", "no:randomly"], timeout=14400)      # with the instructor pack the lab suites alone take about an hour (mutation checks of thirteen modules)
        suites: dict[str, dict] = {}
        skipped: list[dict] = []
        total = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        if xml_path.exists():
            root = ET.parse(xml_path).getroot()
            for tc in root.iter("testcase"):
                mod = (tc.get("classname") or "").replace(".", "/")
                s = suites.setdefault(mod, {"module": mod, "passed": 0, "failed": 0, "skipped": 0, "errors": 0})
                if tc.find("failure") is not None:
                    s["failed"] += 1; total["failed"] += 1
                elif tc.find("error") is not None:
                    s["errors"] += 1; total["errors"] += 1
                elif tc.find("skipped") is not None:
                    s["skipped"] += 1; total["skipped"] += 1
                    skipped.append({"test": f"{tc.get('classname')}::{tc.get('name')}", "reason": (tc.find("skipped").get("message") or "")[:200]})
                else:
                    s["passed"] += 1; total["passed"] += 1
        res = {
            "id": "pytest", "title": "Full pytest suite",
            "status": "PASS" if code == 0 and total["failed"] == 0 and total["errors"] == 0 else "FAIL",
            "detail": f"{total['passed']} passed, {total['failed']} failed, {total['errors']} errors, {total['skipped']} skipped",
            "totals": total, "suites": sorted(suites.values(), key=lambda s: s["module"]), "skipped": skipped,
            "tail": out.strip().splitlines()[-3:],
        }
        return res, skipped


def _cli_chain(steps: list[list[str]], work: Path) -> tuple[bool, str]:
    """Run CLI steps in order; stop at the first failure.  On success return a summary of the evaluation report."""
    last = ""
    for step in steps:
        code, out = run(step, cwd=LABS, env={"PYTHONPATH": str(LABS)})
        last = out.strip().splitlines()[-1] if out.strip() else ""
        if code != 0:
            return False, f"step '{step[3]}' failed: {last}"
    rep = json.loads((work / "report.json").read_text(encoding="utf-8"))["summary"]
    return True, (f"{rep['detected']}/{rep['attack_scenarios']} attack scenarios detected, {rep['true_positive_alerts']}/{rep['alerts']} alerts true positive, "
                  f"{rep['false_positive_alerts']} false-positive alerts, {rep['suppressed_alerts']} suppressed ({rep['suppressed_true_positive_alerts']} hid real attacks)")


def _lab_steps(profile: str, work: Path, rules: Path, exceptions: Path, triage: Path | None) -> list[list[str]]:
    cli = [PY, "-m", "soc_lab"]
    steps = [
        cli + ["generate", "--profile", profile, "--out", str(work), "--with-truth"],
        cli + ["enrich", "--events", str(work / "events.jsonl"), "--context", str(work / "context.json"), "--out", str(work / "events.enriched.jsonl")],
        cli + ["lint", "--rules", str(rules), "--exceptions", str(exceptions)],
        cli + ["detect", "--rules", str(rules), "--events", str(work / "events.enriched.jsonl"), "--exceptions", str(exceptions), "--out", str(work / "alerts.json")],
        cli + ["evaluate", "--alerts", str(work / "alerts.json"), "--truth", str(work / "truth"), "--json", str(work / "report.json")],
    ]
    if triage is not None:
        # Triage records describe the alerts a learner sees BEFORE tuning exceptions, so check them against a pre-exception run.
        steps.append(cli + ["detect", "--rules", str(rules), "--events", str(work / "events.enriched.jsonl"), "--out", str(work / "alerts.pre.json")])
        steps.append(cli + ["check-triage", "--records", str(triage), "--alerts", str(work / "alerts.pre.json"),
                            "--events", str(work / "events.jsonl"), "--truth", str(work / "truth")])
    return steps


def check_lab_end_to_end() -> list[dict]:
    """Drive the real CLI end to end: public reference solution (guided) and private reference (independent)."""
    results = []
    sol = LABS / "m04-guided" / "solution"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ok, last = _cli_chain(_lab_steps("guided", td / "g", sol / "rules", sol / "exceptions.yml", sol / "triage"), td / "g")
        results.append({"id": "lab-guided-e2e", "title": "SOC-M04 guided lab: generate, enrich, lint, detect, evaluate, check-triage (public reference solution)",
                        "status": "PASS" if ok else "FAIL", "detail": last})
        ref = INSTRUCTOR / "m04-independent-reference"
        if not ref.exists():
            results.append({"id": "lab-independent-e2e", "title": "SOC-M04 independent lab with private reference solution", "status": "SKIPPED_PRIVATE_MATERIALS",
                            "detail": "instructor pack not present in this checkout"})
        else:
            ok, last = _cli_chain(_lab_steps("independent", td / "i", ref / "rules", ref / "exceptions.yml", ref / "triage"), td / "i")
            results.append({"id": "lab-independent-e2e", "title": "SOC-M04 independent lab with private reference solution", "status": "PASS" if ok else "FAIL",
                            "detail": ("private pack present locally; this result is not reproducible from a public clone. " + last) if ok else last})
    return results


def check_student_build(skip: bool) -> dict:
    if skip:
        return {"id": "student-build", "title": "Student-edition build (HTML + tagged PDF, strict gates)", "status": "SKIPPED_BY_FLAG", "detail": "--skip-build"}
    if shutil.which("pandoc") is None:
        return {"id": "student-build", "title": "Student-edition build (HTML + tagged PDF, strict gates)", "status": "SKIPPED_TOOL_MISSING", "detail": "pandoc not installed"}
    code, out = run([PY, "scripts/build/build_student_edition.py", "--strict"], timeout=900)
    return {"id": "student-build", "title": "Student-edition build (HTML + tagged PDF, strict gates)", "status": "PASS" if code == 0 else "FAIL",
            "detail": (out.strip().splitlines() or [""])[-1][:240]}


# ------------------------------------------------------------------------------------------------ reporting
def render_reports(results: list[dict], head: str, branch: str, now: str, private_pack: bool) -> None:
    qa_pass = all(r["status"] in ("PASS", "SKIPPED_PRIVATE_MATERIALS", "SKIPPED_TOOL_MISSING", "SKIPPED_BY_FLAG") for r in results)
    py = next(r for r in results if r["id"] == "pytest")

    # ---------------- AUTOMATED_QA_REPORT.md
    L: list[str] = []
    L += ["# Automated QA Report", "",
          "> Generated by `scripts/validation/run_qa.py`. Do not edit by hand; re-run the script. The raw record is `docs/release/data/qa_run.json`.", "",
          f"- Run date (UTC): {now}",
          f"- Branch: `{branch}`",
          f"- Commit the run was executed against: `{head}`  (the report is committed afterwards, so the report commit differs from this one)",
          f"- Python: {sys.version.split()[0]}",
          f"- Private instructor pack present on the machine that ran this report: **{'yes' if private_pack else 'no'}** "
          f"({'tests that need it ran and are counted as passed; that evidence cannot be reproduced from a public clone' if private_pack else 'dependent tests are reported as skipped'})",
          f"- Overall: **{'PASS' if qa_pass else 'FAIL'}**", "",
          "## What this report does and does not prove", "",
          "- It proves that the **automation in this repository** runs and passes: catalog integrity, audit-document reproducibility, design-token contrast, the SOC-M04 pilot lab code, its docs-as-tests checks, and the student-edition build.",
          "- It does **not** prove pedagogical quality, subject-matter correctness beyond the facts registered in `docs/research/research_register.yaml`, or that any learner has succeeded. No learner pilot and no human expert review have taken place.",
          "- Built content is limited to the modules that `docs/production/COURSE_COMPLETENESS_MATRIX.md` lists as implemented. A passing run says nothing about modules that are not built and does not make any course `TRAINING_CONTENT_GO`: that state is computed by Gate A (`docs/production/TRAINING_CONTENT_GO_REPORT.md`) and needs human approvals.",
          "- Tests that need the git-ignored instructor pack are reported as `SKIPPED_PRIVATE_MATERIALS` when the pack is absent. If this run was executed on a machine that holds the pack, the corresponding result is recorded as PASS and the detail says so; that evidence is not reproducible from a public clone.", "",
          "## Checks", "", "| Check | Status | Detail |", "|---|---|---|"]
    for r in results:
        L.append(f"| {r['title']} | **{r['status']}** | {r['detail'].replace('|', '/')} |")
    L += ["", "## Pytest by module", "", "| Module | Passed | Failed | Errors | Skipped |", "|---|---:|---:|---:|---:|"]
    for s in py.get("suites", []):
        L.append(f"| `{s['module']}` | {s['passed']} | {s['failed']} | {s['errors']} | {s['skipped']} |")
    t = py.get("totals", {})
    L.append(f"| **Total** | **{t.get('passed', 0)}** | **{t.get('failed', 0)}** | **{t.get('errors', 0)}** | **{t.get('skipped', 0)}** |")
    if py.get("skipped"):
        L += ["", "## Skipped tests", "", "| Test | Reason |", "|---|---|"]
        for s in py["skipped"]:
            L.append(f"| `{s['test']}` | {s['reason'].replace('|', '/')} |")
    L += ["", "## Known test limitations", "",
          "- Golden hashes of generated datasets are tied to CPython 3.13 behaviour of `random` / `hashlib`; a different major Python may legitimately require re-baselining and the failure message says so.",
          "- The student-edition build depends on `pandoc` and a Chromium binary (pre-installed here). On machines without them the check is `SKIPPED_TOOL_MISSING`, not PASS.",
          "- `sigma_lite` is a teaching evaluator for a documented subset of Sigma. pySigma is used in tests to confirm the lab's rules are valid Sigma, but it is **not** the engine that produces lab scores.",
          "- There is no browser-based accessibility audit with assistive technology; accessibility evidence is limited to token contrast, tagged-PDF structure checks and a 360 px overflow probe.", ""]
    (ROOT / "docs" / "release" / "AUTOMATED_QA_REPORT.md").write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    restore_default_sigint()                      # a background launch must not make the Ctrl-C tests fail (scripts/validation/launch_env.py)
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true", help="skip the (slow) student-edition build")
    ap.add_argument("--skip-page-rebuild", action="store_true", help="skip the (about 70 s) page-record rebuild comparison")
    ap.add_argument("--no-report", action="store_true", help="run checks but do not write reports")
    a = ap.parse_args()

    results: list[dict] = [check_catalog(), check_contrast(), check_audit_render_is_current()]
    results += check_modernization_evidence(include_page_rebuild=not a.skip_page_rebuild)
    results += check_gate_a()
    py_res, _ = run_pytest()
    results.append(py_res)
    results += check_lab_end_to_end()
    results.append(check_student_build(a.skip_build))

    head = sh(["git", "rev-parse", "--short=12", "HEAD"])
    branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    dirty = bool(sh(["git", "status", "--porcelain", "--untracked-files=no"]))
    private_pack = (INSTRUCTOR / "m04-independent-reference").exists()
    if not a.no_report:  # --no-report leaves tracked files untouched
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "qa_run.json").write_text(json.dumps({"private_instructor_pack_present": private_pack, "commit": head, "branch": branch, "working_tree_dirty": dirty, "run_utc": now, "python": sys.version.split()[0], "fingerprints": {"SOC-M04": soc_fingerprint()}, "results": results}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        render_reports(results, head + (" (+uncommitted changes)" if dirty else ""), branch, now, private_pack)
    for r in results:
        print(f"{r['status']:<26} {r['title']}")
    bad = [r for r in results if r["status"] == "FAIL"]
    print("QA FAILED" if bad else "QA OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
