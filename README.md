# CDB-TRAININGS — CyberDudeBivash Academy course engineering repository

This repository holds the **source training PDFs** received from CyberDudeBivash and the **engineering work that replaces them with assessable, tested courses**. It is a work in progress, and it is deliberately honest about what is finished.

> **Status (see [`docs/release/PRODUCTION_GO_GATE_REPORT.md`](docs/release/PRODUCTION_GO_GATE_REPORT.md)):** no course is cleared for production release. One module (SOC-M04, authentication-attack detection and triage) is built as a gold-standard pilot. Everything else is an audited plan. No human subject-matter review has taken place and no learner has used the content.

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

## Safety and policy notes

- Labs use **synthetic data** only and need no paid service. Security content stays in isolated, authorised, synthetic environments.
- **Answer keys and reference solutions are not in this public repository.** They live in a private instructor pack; tests fail if instructor material becomes tracked.
- **No licence has been chosen yet** — see [`LICENSE-STATUS.md`](LICENSE-STATUS.md). Until the owner decides, all rights are reserved by the copyright holder.
- Nothing here publishes, prices, deploys or contacts external services.
