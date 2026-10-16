# CDB-TRAININGS — CyberDudeBivash Academy course engineering repository

This repository holds the **source training PDFs** received from CyberDudeBivash and the **engineering work that replaces them with assessable, tested courses**. It is a work in progress, and it is deliberately honest about what is finished.

> **Status (computed from the evidence; see [`docs/production/PORTFOLIO_FINAL_ACCEPTANCE.md`](docs/production/PORTFOLIO_FINAL_ACCEPTANCE.md)):** no course has reached `TRAINING_CONTENT_GO` (Gate A: the content is complete, correct, executable and approved by named people). The modules that exist are listed in [`docs/production/COURSE_COMPLETENESS_MATRIX.md`](docs/production/COURSE_COMPLETENESS_MATRIX.md); everything else is an audited plan. No human subject-matter review has taken place and no learner has used the content. Commercial readiness and Academy publication are separate gates (`COMMERCIAL_GO`, `ACADEMY_LIVE_GO`) that are not assessed in this phase.

## Where to start

| If you want to… | Read |
|---|---|
| See what was found in the ten PDFs | [`docs/audits/SOURCE_INVENTORY.md`](docs/audits/SOURCE_INVENTORY.md), [`COURSE_QUALITY_SCORECARD.md`](docs/audits/COURSE_QUALITY_SCORECARD.md), [`TECHNICAL_GAP_MATRIX.md`](docs/audits/TECHNICAL_GAP_MATRIX.md) |
| Understand the target curriculum | [`docs/curriculum/MASTER_CURRICULUM_BLUEPRINT.md`](docs/curriculum/MASTER_CURRICULUM_BLUEPRINT.md), [`COMPETENCY_PATHWAYS.md`](docs/curriculum/COMPETENCY_PATHWAYS.md) |
| Try the pilot unit | [`courses/soc-analyst/lessons/m04-auth-detection/lesson.md`](courses/soc-analyst/lessons/m04-auth-detection/lesson.md), then [`labs/m04-guided`](courses/soc-analyst/labs/m04-guided/README.md) |
| Know the quality rules | [`docs/standards/`](docs/standards/) |
| Decide on release or commercial steps | [`docs/release/RELEASE_GATES.md`](docs/release/RELEASE_GATES.md), [`docs/commercial/COMMERCIAL_READINESS.md`](docs/commercial/COMMERCIAL_READINESS.md) |
| Hand the work to the next person | [`docs/execution/EXECUTION_HANDOFF.md`](docs/execution/EXECUTION_HANDOFF.md) |
| Find every deliverable | [`docs/README.md`](docs/README.md) |

## New operational starter tracks (Wave 01; not complete courses)

The following eight previously missing catalog pathways now have **runnable local starter labs**, each with positive/negative tests and explicit operational limits. Their course modules are still marked PLANNED in the catalog until the complete lesson, assessment, independent lab and evidence requirements are satisfied.

| Pathway | Start with |
|---|---|
| [Digital Foundations](courses/digital-foundations/README.md) | File-integrity/tamper-check lab |
| [Python Automation](courses/python-automation/README.md) | Invoice and payment reconciliation |
| [Java Test Automation](courses/java-test-automation/README.md) | Java boundary-value contract |
| [AI & LLM Engineering](courses/ai-engineering/README.md) | Tool permission and human approval |
| [OSINT Investigations](courses/osint-investigations/README.md) | Synthetic source provenance and corroboration |
| [GCP Data Engineering](courses/gcp-data-engineering/README.md) | Offline ingestion data quality |
| [Frontend Engineering](courses/frontend-engineering/README.md) | Safe customer enrollment form contract |
| [Cybersecurity Specialist Tracks](courses/cybersecurity-tracks/README.md) | Synthetic authentication triage |

Run `python scripts/validation/run_starter_labs.py --strict` to check all eight starter exercises; Python, Node.js and JDK are required for this strict run. These are **not complete upgraded PDF products**, do not satisfy `TRAINING_CONTENT_GO`, and must not be published to Academy or sold.

For details and honest verification limits, see [Wave 01 engineering report](docs/production/TRACK_IMPLEMENTATION_WAVE_01.md).

## Repository layout

```
*.pdf                      original source documents (unchanged; hashes verified by tests)
catalog/                   single source of truth: courses.yaml, learning-pathways.yaml, JSON schema
courses/<course>/          lessons, labs, assessments, curriculum traceability, student edition config
                           instructor/ is PRIVATE and git-ignored (only its README is tracked)
docs/                      audits, curriculum, standards, release gates and reports, commercial, execution
shared/                    design tokens/CSS, authoring templates
scripts/                   inventory/forensics, validation, build, QA runner
tests/                     pytest suite (labs, evaluator, build pipeline, catalog and repository hygiene)
```

## Run the checks

Requires Python 3.13 (golden dataset hashes are verified on CPython 3.13). `pandoc`, poppler-utils and Chromium are needed only for the student-edition build.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest                                  # full test suite
python scripts/validation/run_qa.py     # all checks + regenerates the QA and gate reports
python scripts/validation/validate_catalog.py
python scripts/build/render_program_docs.py --check
python scripts/build/build_student_edition.py --strict    # builds dist/ (git-ignored)
```

Running the pilot lab itself is documented in [`courses/soc-analyst/labs/m04-guided/README.md`](courses/soc-analyst/labs/m04-guided/README.md).

## Enterprise flagship pilot — executable evidence, not a customer launch

**Python Engineering is the first flagship release candidate**, based on the recorded 13/13 modules, 25/25 validated labs and 397-page **PREVIEW** course manifest. No final edition or Gate A approval has been granted.

- [Flagship pilot delivery and release blockers](docs/enterprise/PYTHON_FLAGSHIP_ENTERPRISE_PILOT.md)
- [Offline, tenant-scoped pilot ledger](scripts/enterprise/pilot_ledger.py): real learner submissions, instructor grading, immutable scores and audit-chain checks
- [End-to-end synthetic pilot demo](scripts/enterprise/demo_pilot.py): three graded artifacts, hashed evidence anchor, **no certificate**
- [Fail-closed release evidence preflight](scripts/enterprise/release_preflight.py): reports unmet criteria and never implies commercial or Academy permission

Reproduce locally (requires Python 3.11+; PyYAML for the preflight):

```text
python -m unittest discover -s tests -p 'test_enterprise_*.py' -v
python scripts/enterprise/release_preflight.py --course COURSE-PY-ENG
```

The preflight deliberately exits with status 3 while release remains blocked. This is an **offline internal pilot component**, not an authenticated SaaS or an independently audited multi-tenant service. The GitHub source-PDF privacy incident, rights clearance, private instructor pack, real qualified reviews, and supported-platform release checks remain mandatory.

## Safety and policy notes

- Labs use **synthetic data** only and need no paid service. Security content stays in isolated, authorised, synthetic environments.
- **Protected answer keys and independent-grading references must not be stored in this public repository.** Their transfer into owner-controlled private storage is not yet verified (the D8 release blocker remains open); public guided-lab solutions are a separate teaching resource.
- **No licence has been chosen yet** — see [`LICENSE-STATUS.md`](LICENSE-STATUS.md). Until the owner decides, all rights are reserved by the copyright holder.
- Nothing here publishes, prices, deploys or contacts external services.
