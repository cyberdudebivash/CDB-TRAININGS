# PY-M08 Guided Lab — Transactional Event Persistence (Implementation Increment)

**Status: implementation increment, NOT complete course module or TRAINING_CONTENT_GO.**
**Execution baseline:** Python 3.13.5, offline local unittest, 14/14 tests passing on 2026-10-15.
**Scope:** Controlled-local SQLite demonstration; not a multi-user or externally exposed service.

## Customer operations case

A support platform receives event messages that can be delivered more than once. Build a local persistence layer that stores one canonical copy of each event, distinguishes exact retries from conflicting submissions, validates timestamps, and supports consistent customer-scoped event timelines.

## Acceptance contract

- Event records contain event_id, entity_id, event_type, timezone-aware timestamp, and JSON object payload.
- Exact retry returns False and does not duplicate records.
- Reusing an event_id with changed contents raises IdempotencyConflict and does not alter stored data.
- JSON payload limits and invalid values are rejected before transactions.
- Database writes use parameter binding, atomic transactions, and safe rollback.
- Customer/entity lookups use seek pagination with deterministic ordering.
- Restarting an on-disk SQLite store preserves accepted events.
- No network, cloud resources, customer data, or paid services are used.

## Execute

From repository root on Windows, macOS, or Linux:

    python -m unittest discover -s courses/python-engineering/modules/PY-M08/lab-guided/checks -p "test_*.py" -v

Only Python standard-library packages are required.

## Learner tasks

1. Explain why INSERT OR REPLACE can silently corrupt an event history.
2. Prove that the same event can be received twice without duplicate storage.
3. Extend the provided negative tests for empty and control-character identifiers.
4. Demonstrate a SQL injection probe being stored as data instead of executed as SQL.
5. Use a temporary on-disk database to verify persistence after reopening.
6. Document when SQLite's single-process adapter is unsuitable for a distributed production environment.

## Evidence and limitations

The reference solution and public contract suite are supplied to establish an executable pilot. The learner starter, independent exercise, hidden instructor suite, full lesson, outcome mapping, source PDF traceability, and PDF edition still need to be engineered.

Never represent synthetic local SQLite operations as a live customer integration.

## Required follow-on release work

Complete the full PY-M08 lesson package, source mapping, eight-item assessment, rubric, independent lab, negative controls, cross-version matrix, user pilot, protected instructor pack, and course-wide build gates. The existing catalog stays PLANNED until the full package is complete.
