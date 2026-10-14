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
| Findings register (66 findings, single source of truth) | [`audits/data/findings.yaml`](audits/data/findings.yaml) |
| Scores and strengths | [`audits/data/scores.yaml`](audits/data/scores.yaml) |
| Per-course audits | [`audits/courses/`](audits/courses/) |
| Forensic method and its limits | [`audits/SOURCE_FORENSICS_METHOD.md`](audits/SOURCE_FORENSICS_METHOD.md) |
| Primary-source research register | [`research/RESEARCH_REGISTER.md`](research/RESEARCH_REGISTER.md) |
| Course catalog / pathways data | [`../catalog/courses.yaml`](../catalog/courses.yaml), [`../catalog/learning-pathways.yaml`](../catalog/learning-pathways.yaml) |
| Licence position | [`../LICENSE-STATUS.md`](../LICENSE-STATUS.md) |

## October 2026 modernization artifacts

The October 2026 directive named sixteen artifacts plus supporting evidence. Generated files are never edited by hand; every generator has a `--check` mode used by `scripts/validation/run_qa.py`.

| # | Artifact | File | Kind | Regenerate with |
|---:|---|---|---|---|
| 1 | Complete PDF audit | [`audits/OCT2026_COMPLETE_PDF_AUDIT.md`](audits/OCT2026_COMPLETE_PDF_AUDIT.md) | generated | `scripts/audit/render_audit_docs.py` |
| 2 | 2025 to 2026 modernization matrix | [`audits/2025_TO_2026_MODERNIZATION_MATRIX.md`](audits/2025_TO_2026_MODERNIZATION_MATRIX.md) (per-course logs in [`audits/modernization/`](audits/modernization/)) | generated | `render_audit_docs.py` |
| 3 | Technology baselines | [`research/TECHNOLOGY_BASELINES_2026.md`](research/TECHNOLOGY_BASELINES_2026.md) | generated | `scripts/research/render_research_docs.py` |
| 4 | Research verification | [`research/RESEARCH_VERIFICATION_2026.md`](research/RESEARCH_VERIFICATION_2026.md) | generated | `render_research_docs.py` |
| 5 | New developments | [`research/NEW_DEVELOPMENTS_2026.md`](research/NEW_DEVELOPMENTS_2026.md) | generated | `render_research_docs.py` |
| 6 | Master skill pathways | [`curriculum/MASTER_SKILL_PATHWAYS_2026.md`](curriculum/MASTER_SKILL_PATHWAYS_2026.md) | generated | `scripts/build/render_curriculum_2026.py` |
| 7 | Competency outcomes | [`curriculum/COMPETENCY_OUTCOMES_2026.md`](curriculum/COMPETENCY_OUTCOMES_2026.md) | generated | `render_curriculum_2026.py` |
| 8 | All-courses QA report | [`qa/ALL_COURSES_QA_REPORT.md`](qa/ALL_COURSES_QA_REPORT.md) | generated | `scripts/build/render_readiness_2026.py` |
| 9 | Lab execution evidence | [`qa/LAB_EXECUTION_EVIDENCE.md`](qa/LAB_EXECUTION_EVIDENCE.md) | generated from a recorded run | `scripts/validation/run_lab_matrix.py`, `render_lab_evidence.py` |
| 10 | Course source traceability | [`audits/COURSE_SOURCE_TRACEABILITY.md`](audits/COURSE_SOURCE_TRACEABILITY.md) | generated | `render_audit_docs.py` |
| 11 | Premium course catalog (status of planned editions) | [`commercial/PREMIUM_COURSE_CATALOG_2026.md`](commercial/PREMIUM_COURSE_CATALOG_2026.md) | generated | `render_readiness_2026.py` |
| 12 | Pricing and positioning research | [`commercial/PRICING_AND_POSITIONING_RESEARCH.md`](commercial/PRICING_AND_POSITIONING_RESEARCH.md) | hand-written, sourced | - |
| 13 | October 2026 production readiness | [`release/OCT2026_PRODUCTION_READINESS.md`](release/OCT2026_PRODUCTION_READINESS.md) | generated | `render_readiness_2026.py` |
| 14 | October 24 final refresh checklist | [`release/OCT24_FINAL_REFRESH_CHECKLIST.md`](release/OCT24_FINAL_REFRESH_CHECKLIST.md) | generated | `render_readiness_2026.py` |
| 15 | Modernization progress | [`ops/MODERNIZATION_PROGRESS.md`](ops/MODERNIZATION_PROGRESS.md) | generated | `render_readiness_2026.py` |
| 16 | Next execution handoff | [`ops/NEXT_EXECUTION_HANDOFF.md`](ops/NEXT_EXECUTION_HANDOFF.md) | hand-written | - |

Supporting: [`ops/CONTINUOUS_MAINTENANCE_DESIGN.md`](ops/CONTINUOUS_MAINTENANCE_DESIGN.md) (design only, nothing enabled), [`research/technology_registry.yaml`](research/technology_registry.yaml), [`research/research_register.yaml`](research/research_register.yaml), [`research/deprecation_rules.yaml`](research/deprecation_rules.yaml), [`research/new_developments.yaml`](research/new_developments.yaml), [`audits/data/modernization_changes.yaml`](audits/data/modernization_changes.yaml), the page records in [`audits/data/page_records/`](audits/data/page_records/) and the built module packs in [`../courses/python-engineering/`](../courses/python-engineering/).
