# Next Execution Handoff (October 2026 modernization)

For the repository owner and whoever continues this work. This complements [docs/execution/EXECUTION_HANDOFF.md](../execution/EXECUTION_HANDOFF.md) (the first audit and pilot) and is the place to start for the 2025 to October 2026 modernization.
The figures that change as work proceeds live in [MODERNIZATION_PROGRESS.md](MODERNIZATION_PROGRESS.md), which is generated; this page holds the stable guidance.

## 1. State in one paragraph

All ten source PDFs are preserved unchanged. Every one of their pages has a machine-readable audit record; the concept-level 2025-to-2026 differential analysis, the research register (with executed probes and a reproducible registry snapshot dated 2026-10-14) and the new-developments register exist and are cross-validated.
A few modules are built with executed labs (the built modules are listed in [MODERNIZATION_PROGRESS.md](MODERNIZATION_PROGRESS.md)); the rest are planned only. No course is eligible for PRODUCTION_GO and none may be called a "Premium Edition". The 2026-10-24 refresh is a future event (`PENDING_FUTURE_REFRESH`).

## 2. Verify it yourself

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt -r courses/python-engineering/labs/requirements.txt
pytest                                              # full suite; private-pack tests report SKIPPED_PRIVATE_MATERIALS without the instructor pack
python scripts/validation/run_qa.py --skip-build    # catalog, evidence, generated documents, tests; rewrites the QA and gate reports
python scripts/audit/build_page_records.py --check  # about 70 s; page records reproduce from the PDFs and the rules
```

## 3. Owner decisions first

Nothing below is a substitute for D1-D8 in [EXECUTION_HANDOFF.md](../execution/EXECUTION_HANDOFF.md). In practice: D4 (licence and copyright holder) before any distribution; D8 (private repository for the instructor pack, which currently exists only in the working environment of the modernization session) before the independent labs can be re-verified by anyone else; D5 (named reviewers) before any course can reach technical correctness or editorial MET; D1-D3 before the Frontend and OSINT products.

## 4. How to build the next module

The Python Engineering modules are the template (`courses/python-engineering/modules/PY-M02` is the smallest). For a module `X`:

1. Read its catalog row, its page mapping (`docs/audits/COURSE_SOURCE_TRACEABILITY.md`), its change records (`docs/audits/modernization/<course>.md`) and the relevant research entries. Do not state a fact that is not in the register or in an executed probe; add a register entry first (`docs/research/research_register.yaml`, method label honest).
2. Create the folder with `lesson.md`, `outcomes.yaml`, `source-map.yaml`, `assessment/{quiz.yaml,rubric.yaml}`, `lab-guided/`, `lab-independent/` (see `courses/python-engineering/README.md` for the layout). Executable lesson blocks use the `python run`, `python module=NAME` and `python test` fences.
3. Labs: a starter that fails where designed, a public reference for the guided lab, instructor-only material under `courses/<slug>/instructor/` (git-ignored; only its README is tracked). Grade test-writing labs with `labs/_tools/mutation_check.py`; grade fix-it labs with exploit tests plus reintroduction mutants.
4. Run `python scripts/build/render_module_assets.py` (quiz.md), then `pytest tests/test_module_packs.py`: it checks files, front matter against the catalog, outcome-to-assessment traceability, quiz hygiene, rubric coverage, source-map pages and findings, executes every lesson block, and fails if instructor material leaks.
5. Set the module `status: BUILT` and `lab_state: VERIFIED_EXECUTABLE` in `catalog/courses.yaml` **only after** the labs have been executed; update `lab_coverage` and `assessment_coverage`. `validate_modernization_data.py` then tells you which change records need their `implemented.status` updated (it is checked against the catalog).
6. Execute the labs on the interpreter or toolchain matrix (`scripts/validation/run_lab_matrix.py`, then `render_lab_evidence.py`), regenerate the derived documents (section 6), and commit. A lab that was not executed is `UNVERIFIED`; never mark it otherwise.

Suggested order, with reasons: finish Python Engineering (PY-M05, M06, M08, M09, M10, M11 and the missing classes/object-oriented coverage: every other Python course depends on it and the toolchain is already proven); then Python Automation; then the Java course (JDK 21, Maven 3.9.11 and Gradle 8.14.3 are present; JUnit 6 needs Java 17+, so no JDK 25 is required); then the SOC modules (the pilot gives the pattern); AI, GCP, Frontend, OSINT and the security tracks need design decisions about local-first labs before building (no paid service is authorised, D7).

## 5. Known limits and traps

- Page-to-module mapping and page-level actions are **heuristic**; only finding-cited pages were read by a person. 29 pages have no text layer and need visual review or OCR.
- `KEEP` at page level is a candidate, not a verdict.
- Register entries with method `OFFICIAL_PAGE_SUMMARY` or `SECONDARY_SOURCE` were read through a summarising tool or from trade press; re-verify against primary text before customer-facing use (listed in `docs/research/RESEARCH_VERIFICATION_2026.md`).
- GitHub release data was not collected (the session scope was restricted to this repository); 31 registry entries therefore have no verified version.
- The lab evidence is for Linux and for the interpreters in `docs/qa/LAB_EXECUTION_EVIDENCE.md`. The shell-injection probe is POSIX-only.
- A first matrix run found a platform-dependent assertion (TLS minimum version on a distribution Python); it was removed rather than skipped. Run the matrix again on any new interpreter before trusting a lab there.
- Quiz items and rubrics have had no SME review and no learner pilot; their difficulty is unknown.

## 6. Regenerating derived documents

```bash
python scripts/audit/build_page_records.py          # page records (writes docs/audits/data/)
python scripts/audit/render_audit_docs.py           # complete audit, traceability, 2025-to-2026 matrix, per-course change logs
python scripts/research/render_research_docs.py     # baselines, research verification, new developments
python scripts/build/render_curriculum_2026.py      # skill pathways, competency outcomes
python scripts/build/render_readiness_2026.py       # readiness, premium catalog, Stage B checklist, QA report, progress
python scripts/build/render_program_docs.py         # catalog-derived tables in the program documents
python scripts/inventory/render_audits.py           # first-audit documents and the research register view
python scripts/validation/render_lab_evidence.py    # lab evidence from docs/qa/data/lab_execution_<cutoff>.json
```

Every generator has a `--check` mode that `run_qa.py` and the tests use; a hand-edit of a generated file fails them.

## 7. Stage B (2026-10-24)

Follow [docs/release/OCT24_FINAL_REFRESH_CHECKLIST.md](../release/OCT24_FINAL_REFRESH_CHECKLIST.md). It is a future event: nothing may be back-dated, and results from 2026-10-15 onward must enter as new register entries with their own dates.

## 8. Continuous maintenance

The design is in [CONTINUOUS_MAINTENANCE_DESIGN.md](CONTINUOUS_MAINTENANCE_DESIGN.md). **No scheduler or monitor runs today**; the repository does not claim automated monitoring.
