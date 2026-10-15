# Changelog - Python Engineering

## 2026-10-14 (research cutoff; Stage B refresh pending)

- Built PY-M01 to PY-M07 (lessons, guided and independent labs, quizzes, rubrics, outcome and source maps).
- PY-M01: lesson code (including a version-gated feature table) executed on CPython 3.11-3.15; guided lab with 21 provided checks; independent lab graded by a hidden 34-case suite that kills 16 of 16 seeded defects.
- Lab toolchain pinned in `labs/requirements.txt`; execution recorded in `docs/qa/LAB_EXECUTION_EVIDENCE.md`.
- Source handbook left untouched; every module records the pages it replaces and the findings it addresses.
- PY-M05: files, schemas and HTTP clients taught with executed examples against loopback servers; guided lab with 65 provided checks; independent lab graded by a hidden 138-case suite that kills 30 of 30 seeded defects; two new executed probes (R-091, R-092).
- Lab toolchain gains requests 2.34.2, httpx 0.28.1 and pydantic 2.14.1; `labs/_tools/scripted_server.py` is the shared loopback fixture.
- PY-M06: concurrency taught from a measured profile (threads, asyncio, processes, free-threading status) with executed examples; guided lab with 36 provided checks that kill 12 of 13 seeded defects; independent lab graded by a hidden 45-case suite that kills 21 of 21 seeded defects; three new research entries (R-093 to R-095) and a probe of the deprecated `asyncio` placeholder package.
- `labs/_tools/scripted_server.py` records in-flight requests; `mutation_check.py` can judge mutants in parallel.
