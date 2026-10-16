# Offline enterprise pilot: audit-to-state integrity reconciliation

**Classification:** Internal security hardening / NOT customer-release authorisation. **Date:** 2026-10-16.

## Security defect corrected

Before this change, the pilot's `audit_anchor()` verified that event hashes linked correctly, but `progress()` read mutable SQLite rows directly. A process with SQLite write access could update `grades.score` (for example 10 to 100) or reduce the cohort pass threshold without touching the event chain; that altered the progress result even while `audit_anchor()` remained valid.

This change makes the ledger fail closed on such drift. Every event is parsed using the exact canonical JSON schema and hash-checked; a materialized expected snapshot is reconstructed and compared with **all eight** operational tables (tenants, principals, cohorts, assigned instructors, enrollments, assignments, submissions and grades). Direct row insertions, modifications and removals that conflict with existing events block both reads and future authorized writes. Read operations use a consistent SQLite transaction snapshot, rather than verifying one state and then querying another.

Two properties previously missing from event bodies are now included: `COHORT_CREATED.minimum_percent` and `ASSIGNMENT_DEFINED.title`. They are required to reconstruct the integrity of those fields. **Existing pilot databases written with the old event schema will fail closed with an explicit schema mismatch.** There is no automatic in-place migration: preserve old files for authorised forensic review; use new disposable fixtures for the synthetic pilot. A separately approved migration must handle genuine pre-existing records, if any. Do not delete unknown pilot records to force a green test.

## Reproducible developer checks

From repository root with Python 3.11+ and pytest installed:

```text
python -m pytest -q tests/test_enterprise_pilot_ledger.py tests/test_enterprise_release_preflight.py
PYTHONPATH=scripts python -m enterprise.demo_pilot --output /tmp/cdb-enterprise-pilot.json
```

The authoring environment (CPython 3.13.5, Linux, 2026-10-16) executed **53 passing pytest checks** with four passing parametrized subtests. These include ten new negative and persistence checks for score edits, removed/forged grades, artifact digest changes, threshold edits, title changes, role escalation, unlogged tenants, fail-closed writes and SQLite reopening. The synthetic pilot retains **three graded submissions and 15 audit events**. Execution on the exact GitHub branch, a clean clone and a multi-OS matrix must still be independently recorded before merging.

## What this still does NOT prove

The SHA-256 chain has no key and lives in the same local SQLite file as the grade tables. Someone with full database write access can rewrite **both** the materialized state and history and recompute the chain. No external signed/immutable anchor is implemented. The ledger is intentionally single-process and replays all events on every read and write, making it unsuitable for large cohorts without a bounded-performance redesign. It also does not authenticate real people, verify that a learner actually owns the submitted artifact hash, detect collusion or grader bias, provide encryption or data retention, or support enterprise SSO. Direct database-file permissions and backups are operator concerns, not controls established here.

**Release state remains BLOCKED:** Do not expose `PilotLedger` over HTTP, import genuine customer identities, issue a certificate, claim tamper-proof evidence, or deploy this prototype to Fortune 500 users. Qualified human review, rights clearance, private instructor material custody, privacy incident containment and all separate Gate A/B/C criteria remain mandatory.
