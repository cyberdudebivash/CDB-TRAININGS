# Contributing

This repository is the engineering source for CyberDudeBivash Academy courses. These rules keep it trustworthy.

## Ground rules

1. **Never edit or delete the source PDFs.** Tests verify their hashes. Replace content through the catalog and `courses/`, with a source map.
2. **Facts need sources.** Version, law, standard, statistic or tool-behaviour claims go into `docs/research/research_register.yaml` with a primary source and date, and the lesson cites the entry.
3. **Everything is testable.** A lab needs an automated check; documentation examples that show output are asserted by a test.
4. **No secrets, no personal data, no instructor material.** Hygiene tests fail the build. Answer keys and reference solutions go in the private instructor pack (`courses/*/instructor/`, git-ignored).
5. **No unsupported claims.** No job, salary, ranking or certification-pass promises. State what is assessed.
6. **Do not mark anything releasable by hand.** `release_status`, `qa_status` and lab states are updated from evidence (`scripts/validation/run_qa.py`). `TRAINING_CONTENT_GO` is computed by `scripts/production/gate_a.py` and the validator (`scripts/validation/validate_gate_a.py`) rejects any claim, status or review that exceeds the evidence. Human reviews are entered only by the people who give them.
7. **Safe by default.** Offensive techniques only in isolated, authorised, synthetic labs. Cloud labs need cost estimate, opt-in, teardown and a free local alternative.
8. **Do not force-push or rewrite shared history.**

## Workflow

1. Branch from the default branch; never commit directly to it.
2. Edit the **data** first (`catalog/*.yaml`, `docs/audits/data/*.yaml`), then regenerate documents:
   ```bash
   python scripts/inventory/render_audits.py
   python scripts/build/render_program_docs.py
   ```
3. Run `pytest` and `python scripts/validation/run_qa.py`.
4. Open a pull request (draft until the QA report is green). Describe the change, the evidence, and any gate affected.
5. Technical content needs review by a qualified person who is recorded in the catalog (`reviewers`, `review_status: SME_REVIEWED`). Automated review does not count as SME review.

## Adding a module

Use `shared/templates/lesson-template.md` and `lab-spec-template.md`, follow `docs/standards/PRACTICAL_LAB_STANDARDS.md` and `ASSESSMENT_FRAMEWORK.md`, and copy the structure of `courses/soc-analyst/` (SOC-M04) including `curriculum/outcomes.yaml` and `curriculum/source-map.yaml`.

## Style

Plain, precise English. Outcomes start with an observable verb. Use ISO dates. Pin versions. Prefer tables for comparisons and numbered steps for procedures. Write code that passes `python -m py_compile` and the repository tests.
