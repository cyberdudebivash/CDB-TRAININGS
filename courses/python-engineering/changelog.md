# Changelog - Python Engineering

## 2026-10-15 (independent audit, fourth module)

- Added PY-M09 (profiling, performance and maintainable architecture, 8 hours): the handbook's memory and optimisation pages (56-57, 79-80) were mapped to no built module. Lesson (22 executed blocks on CPython 3.11-3.15, R-099, including the 3.15 sampling profiler behind a version check), guided lab `perfkit` (196 provided checks; 59 of 59 seeded defects killed), independent lab `triage` (10 published checks; 378-case hidden suite that kills 52 of 52 seeded defects and runs the learner's own budget tests against the solution and the original), assessment and the instructor pack. Evidence chain: finding F-PYH-014, research entry R-099, change record MC-PYH-24, defect DEF-017.

## 2026-10-15 (independent audit, third module)

- Completed PY-M08 (databases and persistence, 8 hours) on top of the guided-lab increment merged in `cyberdudebivash/CDB-TRAININGS#4` (14 contract tests for an idempotent event store, kept unchanged). Added the lesson (31 executed blocks on CPython 3.11-3.15, R-098), Part 2 of the guided lab (migrations, atomic batches, injection-safe search, retention, query shape; 200 checks in all, 95 of 95 seeded defects killed), the independent lab `casestore` (10 published checks; 145-case hidden suite that kills 83 of 83 seeded defects), assessment and the instructor pack. The default target of the guided checks is now the learner's starter (as in every other module); `PY_M08_TARGET` still works. Evidence chain: finding F-PYH-013, research entry R-098, change record MC-PYH-23, defect DEF-016.

## 2026-10-15 (independent audit, second module)

- Added PY-M13 (iterators, generators, closures, decorators and context managers, 8 hours): the audit found that the handbook's core-Python pages 33-39, 67-69 and 78-79 were mapped to a file-handling module of another course and taught by no module here. Lesson (26 executed blocks on CPython 3.11-3.15, R-097), guided lab `streamkit` (128 provided checks; 49 of 49 seeded defects killed), independent lab `flowkit` (10 published checks; 63-case hidden suite that kills 35 of 35 seeded defects). Evidence chain: finding F-PYH-012, research entry R-097, change record MC-PYH-22, defect DEF-015.

## 2026-10-15 (independent audit)

- Added PY-M12 (classes, dataclasses and object-oriented design, 8 hours): the audit found that no module taught classes although the handbook devotes pp. 40-45, 48-55 and 64-67 to them, because the page-to-module mapping had assigned those pages to PY-M01 by container default. Lesson (34 executed blocks on CPython 3.11-3.15, R-096), guided lab `ledgerkit` (167 provided checks; 47 of 47 seeded defects killed), independent lab `rulekit` (10 published checks; 54-case hidden suite that kills 41 of 41 seeded defects). The guided lab's checks found an atomicity defect in the first draft of the reference solution.
- `labs/_tools/scripted_server.py`: listen backlog raised from 5 to 128; the default made a burst of simultaneous connections wait for a SYN retransmit and failed one concurrency measurement of PY-M06 on CPython 3.14.

## 2026-10-14 (research cutoff; Stage B refresh pending)

- Built PY-M01 to PY-M07 (lessons, guided and independent labs, quizzes, rubrics, outcome and source maps).
- PY-M01: lesson code (including a version-gated feature table) executed on CPython 3.11-3.15; guided lab with 21 provided checks; independent lab graded by a hidden 34-case suite that kills 16 of 16 seeded defects.
- Lab toolchain pinned in `labs/requirements.txt`; execution recorded in `docs/qa/LAB_EXECUTION_EVIDENCE.md`.
- Source handbook left untouched; every module records the pages it replaces and the findings it addresses.
- PY-M05: files, schemas and HTTP clients taught with executed examples against loopback servers; guided lab with 65 provided checks; independent lab graded by a hidden 138-case suite that kills 30 of 30 seeded defects; two new executed probes (R-091, R-092).
- Lab toolchain gains requests 2.34.2, httpx 0.28.1 and pydantic 2.14.1; `labs/_tools/scripted_server.py` is the shared loopback fixture.
- PY-M06: concurrency taught from a measured profile (threads, asyncio, processes, free-threading status) with executed examples; guided lab with 36 provided checks that kill 12 of 13 seeded defects; independent lab graded by a hidden 45-case suite that kills 21 of 21 seeded defects; three new research entries (R-093 to R-095) and a probe of the deprecated `asyncio` placeholder package.
- `labs/_tools/scripted_server.py` records in-flight requests; `mutation_check.py` can judge mutants in parallel.
