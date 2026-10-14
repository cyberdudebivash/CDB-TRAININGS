# Python Engineering Pathway (COURSE-PY-ENG) - modernization in progress

Replaces the 2025 *CyberDudeBivash Python Engineering Handbook* (preserved untouched at the repository root) with tested, current content.
The catalog (`catalog/courses.yaml`) is the source of truth for the module list; this folder holds the modules that have been **built**.

| Module | Title | State | Labs |
|---|---|---|---|
| PY-M01 | Language core and data structures | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided (provided tests), independent (hidden suite) |
| PY-M02 | Functions, errors and testing with pytest | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided (mutation-graded), independent |
| PY-M03 | Types, modules and project layout | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided, independent |
| PY-M04 | Environments, dependencies and packaging (pyproject, build) | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided, independent |
| PY-M07 | Secure coding for Python | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided, independent |

The other modules of the course (PY-M05, M06, M08-M11) are `PLANNED`: nothing in them is built.
Coverage gap: classes and object-oriented design (handbook pp. 48-55) are not taught by any module yet; see `modules/PY-M01/source-map.yaml`. The course is **not** a production release (see `docs/release/OCT2026_PRODUCTION_READINESS.md`).

## Layout of a module

```text
modules/PY-Mxx/
  lesson.md                 lesson; python code blocks tagged run/module/test are executed by tests/test_module_packs.py
  outcomes.yaml             outcome -> instruction -> practice -> assessment -> rubric
  source-map.yaml           what each part does with the 2025 handbook (pages, disposition, finding ids)
  assessment/               quiz.yaml (questions only), quiz.md (generated), rubric.yaml
  lab-guided/               README, starter, checks, (public) solution
  lab-independent/          README, starter, checks (reference and answers are private)
instructor/                 private pack (git-ignored except its README): answer keys, grading notes, independent-lab references and hidden mutants
labs/_tools/mutation_check.py   grades test suites by the defects they catch
labs/requirements.txt       pinned lab toolchain
```

## Running a lab

Each lab README starts with its own setup commands (`python -m venv .venv`, `pip install -r ../../../labs/requirements.txt`, `python -m pytest`). Labs need no network once the packages are installed and no cloud account.
Instructor-only material is never stored in this public repository; see `instructor/README.md`.

## Honest status

- Lab results are recorded in `docs/qa/LAB_EXECUTION_EVIDENCE.md` with the interpreter and tool versions used. A lab is "executed" only for the matrix listed there.
- Quiz items have not been reviewed by a subject-matter expert or piloted with learners; difficulty and discrimination are unknown.
- The instructor pack exists only in the working environment of the modernization session until the owner stores it in a private repository.
