# Release Gates

This document defines how a course moves toward release. It is enforced in two places:

- `scripts/validation/validate_catalog.py` rejects any catalog entry that claims `PRODUCTION_GO` without the evidence listed here.
- `scripts/validation/run_qa.py` evaluates the eight gates per course and writes `PRODUCTION_GO_GATE_REPORT.md`.

**Nothing in this repository can release or publish a course.** `PRODUCTION_GO` is a recommendation that the owner may act on; deployment, pricing and publication need separate, explicit owner authorisation.

## 1. Release states

| State | Meaning | Exit criterion |
|---|---|---|
| `SOURCE_PENDING` | A source the course depends on is missing or unreadable. | Source received, hashed and listed in `docs/audits/SOURCE_INVENTORY.md`. |
| `AUDIT_PENDING` | Source exists but has not been audited. | Findings registered in `docs/audits/data/findings.yaml`; score recorded in `scores.yaml`. |
| `REENGINEERING` | Audited. Replacement content is being designed and built. Default for every course today. | All modules built, every planned lab built, every outcome has an assessment. |
| `VALIDATION` | Content complete; automated QA, lab verification and licence checks are running. | Gates G1-G6 PASS. |
| `REVIEW_REQUIRED` | Automated gates pass; waiting for named human review. | Gate G7 PASS (SME review recorded) and G8 PASS. |
| `PRODUCTION_GO` | Every gate passes. Eligible for release **after owner sign-off**. | Owner sign-off recorded outside this repository's automation. |

A course may move backwards (for example when a new P0/P1 finding is registered); the catalog validator and gate report will show it.

## 2. The eight gates

A gate has one of these results: `PASS` (evidence in the repository), `PARTIAL` (evidence for built content only), `OPEN` (not done), `FAIL` (checked and failing), `N/A`.

| Gate | Requirement | Evidence required |
|---|---|---|
| **G1** Provenance and licence | Every source and reused asset has a recorded origin and a licence position that permits the intended use. | `SOURCE_PROVENANCE.md`, `IP_AND_LICENSE_REVIEW.md`, a repository `LICENSE`, third-party notices. Written owner decision for each licence conflict. |
| **G2** Technical claims verified | Every version-, standard-, law- or statistic-dependent claim is checked against a primary source dated and recorded. | `docs/research/research_register.yaml` entries referenced by the module; no `NEEDS_VERIFICATION` left in shipped text. |
| **G3** Assessment coverage | Every module outcome is assessed by a rubric-scored artefact or an automated check. | `assessment_coverage.outcomes_assessed == outcomes_total`; rubrics under `courses/*/assessments/`. |
| **G4** Labs executable | Every planned lab is built, has an automated check, and passed in the recorded QA run. | `lab_coverage.verified_executable == planned`; `AUTOMATED_QA_REPORT.md`. |
| **G5** Automated QA | The repository QA run is green and covers the course's built content. | `docs/release/data/qa_run.json` with no `FAIL`. |
| **G6** Accessibility and design system | Learner-facing outputs meet the design-system rules (contrast, structure, responsive reflow) and have been checked. | `DESIGN_SYSTEM.md`, contrast check, student-edition build gates. Assistive-technology testing is a recommended addition. |
| **G7** Subject-matter expert review | A qualified human has reviewed the technical content and recorded the outcome. | `review_status: SME_REVIEWED`; named reviewer(s). **No AI-only review counts.** |
| **G8** Ownership and open risk | A named owner and reviewers exist; no P0/P1 finding against the course's sources remains. The validator requires every such finding to be listed in `blocking_findings` until the course is fully rebuilt, so a fix inside one pilot module cannot clear a course-level finding. | `owner`, `reviewers`, `blocking_findings` empty. |

### Hard rules

1. A numeric quality score never overrides a failed gate. The 95/100 premium target is necessary, not sufficient.
2. `PRODUCTION_GO` requires all eight gates to be `PASS` or `N/A`. `PARTIAL` is not enough.
3. Skipped checks are recorded as skipped (`SKIPPED_PRIVATE_MATERIALS`, `SKIPPED_TOOL_MISSING`), never as passed.
4. A change to a published course after `PRODUCTION_GO` re-opens the affected gates; the version number is bumped.
5. Claims about outcomes (jobs, salary, rankings, certification pass rates, "job-ready") are not release criteria and must not appear in learner-facing or marketing text unless backed by a cited, dated, reproducible source.

## 3. Roles

| Role | Responsibility | Today |
|---|---|---|
| Course owner | Accountable for the course; signs off release. | `UNASSIGNED` for every course |
| SME reviewer | Verifies technical correctness and pedagogy; recorded by name and date. | none recorded |
| Legal/licence reviewer | Settles source and tool licence positions. | none recorded |
| Release approver | Authorises publication, pricing and deployment. | the repository owner (outside this repository's automation) |

## 4. Rollback

Content is versioned in Git. A release is a tag on a commit whose gate report says `PRODUCTION_GO`; rollback is publishing the previous tag. Generated student editions in `dist/` are build outputs and are never committed.
