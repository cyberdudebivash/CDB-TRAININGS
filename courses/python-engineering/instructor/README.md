# Instructor pack (private) - how this works

This repository is **public**, so instructor-only material is **not stored here**. It lives in a private repository
(suggested name: `cdb-trainings-instructor`) and is copied into this folder locally when instructors need to run or grade
the course. Everything in this folder except this README is git-ignored.

## What the pack contains

| Path | Purpose |
|---|---|
| `PY-M02/answer-key.md` | Answer key and rationale for the 8 quiz items |
| `PY-M02/grading-notes.md` | How to score reviewer criteria C3-C5 of the independent lab, with level examples |
| `PY-M02/independent-reference/` | Reference test suite for `splitkit` and the hidden mutant list used by `labs/_tools/mutation_check.py` |
| `PY-M01/` | Answer key, grading notes, the `logkit` and `report.py` reference, the 34-case hidden test suite and 16 hidden mutants |
| `PY-M06/` | Answer key, grading notes, the `wordjob` and `benchmark.py` reference, the 45-case hidden suite, 21 hidden mutants and 13 mutants of the guided-lab solution |
| `PY-M05/` | Answer key, grading notes, the `feedsync` reference, the 138-case hidden suite and 30 hidden mutants |
| `PY-M08/` | Answer key, grading notes, the `casestore` reference, the 145-case hidden suite, 83 hidden mutants and 95 mutants of the guided-lab solution |
| `PY-M09/` | Answer key, grading notes, the `triage` reference and its sample budget tests, the 378-case hidden suite, 52 hidden mutants and 59 mutants of the guided-lab solution |
| `PY-M10/` | Answer key, grading notes, the `inventory` reference and its sample threat table, the 482-case hidden suite, 275 hidden mutants and 432 mutants of the guided-lab solution |
| `PY-M11/` | Answer key, grading notes, a sample NOTES.md, the reference `authwatch` project, a part A solution, the 585-case hidden suite, 315 seeded defects and the tool that applies them to a package |
| `PY-M13/` | Answer key, grading notes, the `flowkit` reference, the 63-case hidden suite, 35 hidden mutants and 49 mutants of the guided-lab solution |
| `PY-M12/` | Answer key, grading notes, the `rulekit` reference, the 54-case hidden suite, 41 hidden mutants and 47 mutants of the guided-lab solution |
| `PY-M03/`, `PY-M04/`, `PY-M07/` | The same kinds of file for the other built modules (PY-M03's independent reference is a complete project) |

## How the automated tests treat it

`tests/test_python_engineering_labs.py` runs the instructor reference material **only if** it exists. Without it those tests are reported as
`SKIPPED_PRIVATE_MATERIALS`: that means *not verified in this environment*, never "passed".

## Status of this pack

The pack for the built Python Engineering modules was created in the October 2026 modernization session. Until the owner confirms it is stored in the private repository it exists
only in the working environment of that session.
