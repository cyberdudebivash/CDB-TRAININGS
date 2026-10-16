"""Execute a genuine local pilot workflow with synthetic identities and artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from enterprise.pilot_ledger import PilotLedger, PolicyError


def run(db_file: Path) -> dict:
    with PilotLedger(db_file) as db:
        db.bootstrap_tenant("company_example", "training_admin")
        db.add_principal("company_example", "training_admin", "trainer_001", "instructor")
        db.add_principal("company_example", "training_admin", "student_001", "learner")
        db.create_cohort("company_example", "training_admin", "pilot_oct", "COURSE-PY-ENG", "0.1-preview")
        db.assign_instructor("company_example", "training_admin", "pilot_oct", "trainer_001")
        db.enroll("company_example", "training_admin", "pilot_oct", "student_001")
        for assignment in ("security_lab", "incident_report", "capstone_review"):
            db.add_assignment("company_example", "trainer_001", "pilot_oct", assignment,
                              f"Synthetic {assignment.replace('_', ' ')}")
            submission = f"sub_{assignment}"
            db.submit("company_example", "student_001", "pilot_oct", assignment, submission,
                      hashlib.sha256(assignment.encode()).hexdigest())
        pending = db.progress("company_example", "student_001", "pilot_oct", "student_001")
        for assignment, score in (("security_lab", 96), ("incident_report", 91), ("capstone_review", 90)):
            db.grade("company_example", "trainer_001", f"sub_{assignment}", score,
                     hashlib.sha256((assignment + str(score)).encode()).hexdigest())
        passing = db.progress("company_example", "student_001", "pilot_oct", "student_001")
        audit = db.audit_anchor("company_example", "training_admin")
        return {"schema_version": 1, "scenario": "SYNTHETIC_LOCAL_TRAINING_PILOT",
                "before_grading": pending, "after_grading": passing, "audit": audit,
                "delivery_status": "PILOT_ONLY_NOT_FOR_CUSTOMERS",
                "security_limit": "No authentication gateway, validated learner artifacts, signed audit anchor, or external grading provider."}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    with TemporaryDirectory(prefix="cdb-training-pilot-") as td:
        result = run(Path(td) / "pilot.db")
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
