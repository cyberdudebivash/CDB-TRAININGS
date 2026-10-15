# Operational Starter Lab — Zero-cloud-cost ingestion quality gate

**Course:** `COURSE-GCP-DE` (Google Cloud Data Engineering Pathway)  
**Scope:** Standalone guided operational exercise; not a completed curriculum module.  
**Prerequisites:** Python 3.11+ standard library.

## Customer-operations scenario

A data engineer inspects synthetic order CSV rows before an approved future Cloud Storage to BigQuery pipeline ingests them.

## Engineering acceptance contract

Validate strict columns, unique order keys, **canonical YYYY-MM-DD calendar dates**, finite nonnegative monetary values, and supported regions; produce rejected-row reasons. A header-only/empty input must be rejected as unsafe to ingest.

All inputs are fictional or synthetic. The implementation makes no network calls, does not use customer identities or secrets and must never be pointed at an unauthorized system. The exercise is designed to develop safe problem-solving before introducing real service integrations.

## Execute validation

From the repository root:

```text
python -m unittest discover -s courses/gcp-data-engineering/labs/batch-quality -p test_lab.py -v
```

This exercise runs locally without paid services. Follow the shown command from the repository root; record the actual interpreter and any skipped tests. **Do not infer multi-platform coverage from one successful local run.**

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

## Regression lesson — why empty datasets and noncanonical dates fail

An empty batch must not be treated as a successful customer delivery. Run the `test_header_only_batch_not_safe` test and explain why zero accepted records can be operationally significant even when no row-level parse error exists. Test `2026-W42-4` and `20261014`: these may be parsed by a permissive date API but violate our documented YYYY-MM-DD input schema. Distinguish a valid calendar date from a date-format contract. The validator is a teaching gate, not proof of end-to-end BigQuery ingestion or exactly-once processing.
