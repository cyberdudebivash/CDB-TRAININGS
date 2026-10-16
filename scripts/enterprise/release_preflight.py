"""Produce a fail-closed, noncommercial course release-readiness evidence report.

Reads generated Gate A snapshots but *never* certifies readiness from those snapshots.
Evidence is not fresh unless Gate A itself has been recomputed on the working tree.
Commercial and Academy Live gates are out of scope and always unauthorised here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

GATE_A = tuple(f"A{number:02d}" for number in range(1, 20))
OPTIONAL = {"NOT_APPLICABLE"}


def inspect_course(root: Path, course: str) -> dict[str, Any]:
    """Snapshot-only procurement preflight; cannot assert a live release verdict."""
    matrix = json.loads((root / "docs/production/data/truth_matrix.json").read_text(encoding="utf-8"))
    pdfs = json.loads((root / "docs/production/data/pdf_manifest.json").read_text(encoding="utf-8"))
    defects = yaml.safe_load((root / "docs/production/data/defects.yaml").read_text(encoding="utf-8"))["defects"]
    humans = yaml.safe_load((root / "docs/production/data/human_reviews.yaml").read_text(encoding="utf-8"))["reviews"]
    if course not in matrix:
        raise ValueError(f"unknown course id: {course}")
    data = matrix[course]
    criteria = data.get("criteria")
    if not isinstance(criteria, dict) or set(criteria) != set(GATE_A):
        raise ValueError("missing or unrecognized mandatory course criteria")
    unresolved = [key for key in GATE_A if criteria[key] not in ({"MET"} | (OPTIONAL if key == "A03" else set()))]
    active = [d["id"] for d in defects if d.get("status") != "CLOSED"
              and d.get("severity") in {"P0", "P1"} and
              ("*" in d.get("applies_to", []) or course in d.get("applies_to", []))]
    editions = [p for p in pdfs.get("course_editions", []) if p.get("course") == course]
    if len(editions) > 1:
        raise ValueError("multiple course-level edition records; manual reconciliation required")
    edition = editions[0] if editions else None
    is_final = bool(edition and edition.get("kind") == "FINAL" and edition.get("passed") is True
                    and isinstance(edition.get("pdf_sha256"), str) and len(edition["pdf_sha256"]) == 64
                    and not edition.get("problems"))
    human_types = {r.get("kind") for r in humans if r.get("course") == course
                   and r.get("outcome") in {"APPROVED", "APPROVED_WITH_CHANGES"}}
    missing_humans = sorted({"SME", "EDITORIAL", "LEARNER_PILOT", "OWNER_ACCEPTANCE"} - human_types)
    modules = data.get("modules", {})
    if not isinstance(modules, dict):
        raise ValueError("invalid course modules in snapshot")
    preview_page_count = edition.get("pdf_pages") if edition else None
    return {
        "schema_version": 1,
        "course": course,
        "evidence_type": "RECORDED_SNAPSHOT_REQUIRES_FRESH_GATE_A_AND_HUMAN_VALIDATION",
        "score_snapshot": data.get("score"),
        "recorded_course_state": data.get("state"),
        "module_count": len(modules),
        "modules_technically_verified_snapshot": sum(m.get("state") in {"TECHNICALLY_VERIFIED", "REVIEW_REQUIRED"}
                                                       for m in modules.values()),
        "lab_counts_snapshot": data.get("labs"),
        "course_pdf_preview_pages": preview_page_count if edition and edition.get("kind") == "PREVIEW" else None,
        "complete_final_pdf_evidenced": is_final,
        "unmet_gate_a_criteria": unresolved,
        "open_blocking_p0_p1_defects": active,
        "missing_human_review_types": missing_humans,
        "training_content_go": False,
        "commercial_go": False,
        "academy_live_go": False,
        "decision": "BLOCKED_PENDING_LIVE_RECOMPUTATION_AND_HUMAN_SIGNOFF",
        "next_action": "Run scripts/production/gate_a.py, reconcile source freshness, resolve A criteria and human/rights blockers; do not offer, certify or deploy this course.",
    }


def to_markdown(r: dict) -> str:
    return "\n".join([
        f"# {r['course']} — Enterprise training evidence preflight",
        "", "**Verdict: BLOCKED. This is a snapshot, not a release certificate.**", "",
        f"Recorded quality score: {r['score_snapshot']}/100. Modules: {r['modules_technically_verified_snapshot']}/{r['module_count']} technically verified in recorded evidence.",
        f"Preview PDF pages: {r['course_pdf_preview_pages'] or 'none'}. Validated final PDF: {'yes' if r['complete_final_pdf_evidenced'] else 'no'}.",
        f"Unmet Gate A criteria: {', '.join(r['unmet_gate_a_criteria']) or 'none in recorded snapshot; still requires live validation'}.",
        f"Open P0/P1 defects: {', '.join(r['open_blocking_p0_p1_defects']) or 'none recorded'}.",
        f"Outstanding human review categories: {', '.join(r['missing_human_review_types']) or 'none recorded'}.",
        "", "Neither paid customer fulfillment nor Academy publication is authorized by this preflight.",
        "", r["next_action"], "",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--course", default="COURSE-PY-ENG")
    ap.add_argument("--format", choices=("json", "markdown"), default="markdown")
    ap.add_argument("--report-only", action="store_true", help="Return 0 after writing a blocked report; NEVER authorize release")
    ap.add_argument("--output", type=Path, help="Optional local report file")
    args = ap.parse_args(argv)
    try:
        report = inspect_course(args.root, args.course)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"PREFLIGHT INVALID: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    content = to_markdown(report) if args.format == "markdown" else json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0 if args.report_only else 3  # always fail closed; this is NOT the authoritative Gate A evaluator


if __name__ == "__main__":
    raise SystemExit(main())
