# Python Engineering Pathway (COURSE-PY-ENG) - modernization in progress

Replaces the 2025 *CyberDudeBivash Python Engineering Handbook* (preserved untouched at the repository root) with tested, current content.
The catalog (`catalog/courses.yaml`) is the source of truth for the module list; this folder holds the modules that have been **built**.

| Module | Title | State | Labs |
|---|---|---|---|
| PY-M01 | Language core and data structures | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided (provided tests), independent (hidden suite) |
| PY-M02 | Functions, errors and testing with pytest | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided (mutation-graded), independent |
| PY-M03 | Types, modules and project layout | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided, independent |
| PY-M04 | Environments, dependencies and packaging (pyproject, build) | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided, independent |
| PY-M05 | Files, structured data and HTTP clients | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided (provided checks against a scripted API), independent (hidden suite) |
| PY-M06 | Concurrency and asynchronous programming | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided (provided checks, mutation-tested), independent (hidden suite) |
| PY-M07 | Secure coding for Python | Built, automated checks executed; not SME-reviewed, not learner-piloted | guided, independent |
| PY-M08 | Databases and persistence: safe SQL, transactions, repositories, migrations and query cost | Built on top of the guided-lab increment merged in PR #4; automated checks executed once the lab matrix has run it; not SME-reviewed, not learner-piloted | guided (200 provided checks, mutation-tested), independent (hidden suite) |
| PY-M09 | Profiling, performance and maintainable architecture | Built; automated checks executed once the lab matrix has run it; not SME-reviewed, not learner-piloted | guided (196 provided checks, mutation-tested), independent (hidden suite and learner-written budget tests) |
| PY-M13 | Iterators, generators, closures, decorators and context managers | Built (added after the independent audit found no module taught them); automated checks executed once the lab matrix has run it; not SME-reviewed, not learner-piloted | guided (128 provided checks, mutation-tested), independent (hidden suite) |
| PY-M12 | Classes, dataclasses and object-oriented design | Built (added after the independent audit found no module taught classes); automated checks executed once the lab matrix has run it; not SME-reviewed, not learner-piloted | guided (167 provided checks, mutation-tested), independent (hidden suite) |

The other modules of the course (PY-M10 and PY-M11) are `PLANNED`: nothing in them is built.
Classes and object-oriented design (handbook pp. 40-45, 48-55 and 64-67) were taught by no module until PY-M12 was added; see `modules/PY-M01/source-map.yaml` and defect DEF-006. Other handbook pages (for example iterators, generators, decorators, file handling and context managers on pp. 29-47 and 67-79) have no module yet: `docs/production/COURSE_COMPLETENESS_MATRIX.md` counts them. The course is **not** a production release (see `docs/release/OCT2026_PRODUCTION_READINESS.md`).

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
