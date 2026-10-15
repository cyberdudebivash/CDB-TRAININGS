# Operational Starter Lab — Zero-cloud-cost ingestion quality gate

**Course:** `COURSE-GCP-DE` (Google Cloud Data Engineering Pathway)  
**Scope:** Standalone guided operational exercise; not a completed curriculum module.  
**Prerequisites:** Python 3.11+ standard library.

## Customer-operations scenario

A data engineer inspects synthetic order CSV rows before an approved future Cloud Storage to BigQuery pipeline ingests them.

## Engineering acceptance contract

Validate strict columns, unique order keys, ISO date-like values, finite nonnegative monetary values, and supported regions; produce rejected-row reasons.

All inputs are fictional or synthetic. The implementation makes no network calls, does not use customer identities or secrets and must never be pointed at an unauthorized system. The exercise is designed to develop safe problem-solving before introducing real service integrations.

## Execute validation

From the repository root:

```text
python -m unittest discover -s courses/gcp-data-engineering/labs/batch-quality -p test_lab.py -v
```

The Java example writes compiler output to the locally ignored `build` directory (run it from the lab folder or replace it with a temporary output folder). No purchased accounts are required. **Do not infer multi-platform coverage from one successful local run.**

## Guided exercise

1. Read the implementation and describe the operational input, output, and non-negotiable invariants.
2. Execute the test harness and preserve the output (runtime version, commands, counts, failures).
3. Change one implementation invariant in a disposable copy and demonstrate that a negative control catches the regression.
4. Explain which real-world environmental failures would prevent direct reuse in production.
5. Propose an additional edge case with a deterministic expected outcome, then implement an additional test.
6. Prepare a short professional handoff identifying known limitations and the conditions required for safe future integration.

## Assessment criteria

- **Correct behavior (required):** all shipped functional checks pass on the learner's implementation.
- **Negative controls (required):** demonstrate at least one intentionally introduced defect detected by a targeted test.
- **Reasoning (required):** describe at least two operational failure modes and one security boundary.
- **Documentation:** provide repeatable execution steps and evidence without leaking personal data.

This is a **formative practice rubric**, not an Academy certification or a course-level final assessment. Instructor review is still required.

## Explicit limitations

This is a local pre-ingestion validation. It does not execute Cloud Storage, BigQuery, Dataflow, Pub/Sub, IAM, or billed GCP workloads.

Use the top-level [course status](../../README.md) and [Gate A matrix](../../../../docs/production/COURSE_COMPLETENESS_MATRIX.md) before claiming release readiness.
