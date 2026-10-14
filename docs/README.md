# Documentation index

The mission directive named seventeen deliverables. This index maps each to its file, says whether the file is **hand-written** or **generated**, and what regenerates it. `tests/test_repo_hygiene.py::test_required_deliverables_exist` fails if any is missing.

| # | Deliverable | File | Kind | Regenerate with |
|---:|---|---|---|---|
| 1 | SOURCE_INVENTORY | [`audits/SOURCE_INVENTORY.md`](audits/SOURCE_INVENTORY.md) | generated | `scripts/inventory/render_audits.py` |
| 2 | SOURCE_PROVENANCE | [`audits/SOURCE_PROVENANCE.md`](audits/SOURCE_PROVENANCE.md) | hand-written | — |
| 3 | MISSING_MATERIALS | [`audits/MISSING_MATERIALS.md`](audits/MISSING_MATERIALS.md) | hand-written | — |
| 4 | IP_AND_LICENSE_REVIEW | [`audits/IP_AND_LICENSE_REVIEW.md`](audits/IP_AND_LICENSE_REVIEW.md) | hand-written | — |
| 5 | MASTER_CURRICULUM_BLUEPRINT | [`curriculum/MASTER_CURRICULUM_BLUEPRINT.md`](curriculum/MASTER_CURRICULUM_BLUEPRINT.md) | hand-written + generated tables | `scripts/build/render_program_docs.py` |
| 6 | COURSE_QUALITY_SCORECARD | [`audits/COURSE_QUALITY_SCORECARD.md`](audits/COURSE_QUALITY_SCORECARD.md) | generated | `render_audits.py` |
| 7 | TECHNICAL_GAP_MATRIX | [`audits/TECHNICAL_GAP_MATRIX.md`](audits/TECHNICAL_GAP_MATRIX.md) | generated | `render_audits.py` |
| 8 | COMPETENCY_PATHWAYS | [`curriculum/COMPETENCY_PATHWAYS.md`](curriculum/COMPETENCY_PATHWAYS.md) | hand-written + generated tables | `render_program_docs.py` |
| 9 | PRACTICAL_LAB_STANDARDS | [`standards/PRACTICAL_LAB_STANDARDS.md`](standards/PRACTICAL_LAB_STANDARDS.md) | hand-written | — |
| 10 | ASSESSMENT_FRAMEWORK | [`standards/ASSESSMENT_FRAMEWORK.md`](standards/ASSESSMENT_FRAMEWORK.md) | hand-written | — |
| 11 | DESIGN_SYSTEM | [`standards/DESIGN_SYSTEM.md`](standards/DESIGN_SYSTEM.md) | hand-written | — |
| 12 | COURSE_PRODUCT_CATALOG | [`commercial/COURSE_PRODUCT_CATALOG.md`](commercial/COURSE_PRODUCT_CATALOG.md) | hand-written + generated tables | `render_program_docs.py` |
| 13 | COMMERCIAL_READINESS | [`commercial/COMMERCIAL_READINESS.md`](commercial/COMMERCIAL_READINESS.md) | hand-written + generated table | `render_program_docs.py` |
| 14 | AUTOMATED_QA_REPORT | [`release/AUTOMATED_QA_REPORT.md`](release/AUTOMATED_QA_REPORT.md) | generated from a real run | `scripts/validation/run_qa.py` |
| 15 | PRODUCTION_GO_GATE_REPORT | [`release/PRODUCTION_GO_GATE_REPORT.md`](release/PRODUCTION_GO_GATE_REPORT.md) | generated | `run_qa.py` |
| 16 | EXECUTION_PROGRESS | [`execution/EXECUTION_PROGRESS.md`](execution/EXECUTION_PROGRESS.md) | hand-written snapshot | — |
| 17 | EXECUTION_HANDOFF | [`execution/EXECUTION_HANDOFF.md`](execution/EXECUTION_HANDOFF.md) | hand-written | — |

## Supporting material

| Topic | File |
|---|---|
| Release states and the eight gates | [`release/RELEASE_GATES.md`](release/RELEASE_GATES.md) |
| Findings register (65 findings, single source of truth) | [`audits/data/findings.yaml`](audits/data/findings.yaml) |
| Scores and strengths | [`audits/data/scores.yaml`](audits/data/scores.yaml) |
| Per-course audits | [`audits/courses/`](audits/courses/) |
| Forensic method and its limits | [`audits/SOURCE_FORENSICS_METHOD.md`](audits/SOURCE_FORENSICS_METHOD.md) |
| Primary-source research register | [`research/RESEARCH_REGISTER.md`](research/RESEARCH_REGISTER.md) |
| Course catalog / pathways data | [`../catalog/courses.yaml`](../catalog/courses.yaml), [`../catalog/learning-pathways.yaml`](../catalog/learning-pathways.yaml) |
| Licence position | [`../LICENSE-STATUS.md`](../LICENSE-STATUS.md) |
