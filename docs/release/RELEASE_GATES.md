# Release Gates

Release readiness is split into **three independent gates**. They answer different questions, are owned by different people, and one never implies another.

| Gate | Question | Computed by | Status in the current phase |
|---|---|---|---|
| **A** `TRAINING_CONTENT_GO` | Is the training content complete, correct, executable and releasable *as content*? | `scripts/production/gate_a.py`; enforced by `scripts/validation/validate_gate_a.py` | **Implemented.** Result: [`docs/production/TRAINING_CONTENT_GO_REPORT.md`](../production/TRAINING_CONTENT_GO_REPORT.md) |
| **B** `COMMERCIAL_GO` | May the content be priced, packaged, listed and sold? | not implemented | Future phase. Not assessed. No price, listing or payment exists. |
| **C** `ACADEMY_LIVE_GO` | May the content be published on a live Academy platform? | not implemented | Future phase. Not assessed. Nothing is deployed. |

**Nothing in this repository can release, publish, price or sell a course.** `TRAINING_CONTENT_GO` says only that the content passes every Gate A criterion and that named people have approved it; deployment, pricing and publication need separate, explicit owner authorisation under Gates B and C. The earlier single `PRODUCTION_GO` state conflated the three questions and is retired; the validator rejects it.

## 1. Gate A: states and definition

| State | Meaning | Computed from |
|---|---|---|
| `NOT_STARTED` | No implementation artefacts exist. | files |
| `IN_PROGRESS` | Some artefacts exist; required ones are missing. | files |
| `IMPLEMENTED_UNVERIFIED` | Every required file exists. No passing execution evidence for the current content. | files + recorded runs |
| `TECHNICALLY_VERIFIED` | Recorded execution passed on at least three interpreters with no skip, and the evidence is not stale (no input changed after the recorded run). | `docs/qa/data/lab_execution_*.json` |
| `REVIEW_REQUIRED` | Technically verified and independently re-verified (adversarial review recorded). Only human approvals are missing. | `docs/production/data/adversarial_reviews.yaml` |
| `TRAINING_CONTENT_GO` | A **course** (never a single module) with all 19 mandatory criteria MET, quality score of at least 95, and named humans' approvals recorded. | `scripts/production/gate_a.py` |

A file existing is never completion. A module's state is computed; nobody types it in. The score is **necessary and never sufficient**: it cannot offset a criterion that is not MET.

The 19 mandatory criteria (A01 to A19), the nine weighted quality dimensions and the definition of each state are in [`docs/production/data/gate_a_criteria.yaml`](../production/data/gate_a_criteria.yaml) and rendered in [`MASTER_CONTENT_ACCEPTANCE.md`](../production/MASTER_CONTENT_ACCEPTANCE.md).

## 2. Hard rules

1. Reviews that only a person can give (subject-matter, editorial, learner pilot, owner acceptance) are recorded by that person in `docs/production/data/human_reviews.yaml`. The automation never edits that file, never invents a reviewer, a pilot learner or an approval, and never describes model inspection as human review. The validator rejects an entry that names an automated or simulated participant.
2. A numeric score never overrides a criterion that is not MET. The 95-point threshold is necessary, not sufficient.
3. Skipped checks are recorded as skipped (`SKIPPED_PRIVATE_MATERIALS`, `SKIPPED_TOOL_MISSING`), never as passed. Recorded lab evidence with a skipped test is not evidence.
4. A change to a module's lesson or labs after the recorded run makes that module's evidence stale; the state falls back to `IMPLEMENTED_UNVERIFIED` until the lab matrix is run again.
5. Claims about outcomes (jobs, salary, rankings, certification pass rates, "job-ready") are not release criteria and must not appear in learner-facing or marketing text unless backed by a cited, dated, reproducible source.
6. Open P0 or P1 defects and privacy, rights or confidentiality incidents that apply to a course block it ([`REMAINING_DEFECTS.md`](../production/REMAINING_DEFECTS.md)).
7. The label "Premium Edition" in a student-edition title is refused by the builder unless Gate A computes `TRAINING_CONTENT_GO` for the course. The label still does not authorise sale; that is Gate B.

## 3. Catalog release states

`catalog/courses.yaml` carries a `release_status`: `SOURCE_PENDING`, `AUDIT_PENDING`, `REENGINEERING`, `VALIDATION`, `REVIEW_REQUIRED`, `TRAINING_CONTENT_GO`. The catalog may claim `TRAINING_CONTENT_GO` only when Gate A computes it; `validate_gate_a.py` (check G01) and `validate_catalog.py` reject the claim otherwise. A course may move backwards when a defect or incident is registered or evidence goes stale.

## 4. Roles

| Role | Responsibility | Today |
|---|---|---|
| Course owner | Accountable for the course; records acceptance (A19). | `UNASSIGNED` for every course |
| Subject-matter reviewer | Verifies technical correctness and pedagogy; recorded by name and date (A17). | none recorded |
| Editorial reviewer | Language, structure and accessibility review (A17). | none recorded |
| Learner-pilot participants | Real learners who complete the material; results recorded (A18). | none recorded |
| Legal/licence reviewer | Settles source and tool licence positions (A11). | none recorded |
| Release approver | Authorises publication, pricing and deployment (Gates B and C). | the repository owner, outside this repository's automation |

## 5. Rollback

Content is versioned in Git. A content release is a tag on a commit whose Gate A report says `TRAINING_CONTENT_GO` for the course; rollback is returning to the previous tag. Generated student editions in `dist/` are build outputs and are never committed; their hashes are recorded in `docs/production/data/pdf_manifest.json`.
