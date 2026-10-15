# Operational Starter Lab — Authentication failure triage with bounded time windows

**Course:** `COURSE-CYBER-MEGA` (Cybersecurity Specialist Tracks)  
**Scope:** Standalone guided operational exercise; not a completed curriculum module.  
**Prerequisites:** Python 3.11+ standard library.

## Customer-operations scenario

A defensive SOC analyst correlates synthetic authentication failures and must avoid falsely grouping separate user accounts, sources or time windows.

## Engineering acceptance contract

Normalize timezone-aware event timestamps; reject duplicated event IDs, nonboolean success fields and invalid detection settings; group failures per account/source; emit evidence IDs for threshold crossing. Threshold is a genuine integer between 2 and 100, not a float, boolean or numeric string.

All inputs are fictional or synthetic. The implementation makes no network calls, does not use customer identities or secrets and must never be pointed at an unauthorized system. The exercise is designed to develop safe problem-solving before introducing real service integrations.

## Execute validation

From the repository root:

```text
python -m unittest discover -s courses/cybersecurity-tracks/labs/auth-triage -p test_lab.py -v
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

Illustrative detection; one alert per account/source, no enrichment, no deployed SIEM, no real telemetry, no claim of production detection accuracy.

Use the top-level [course status](../../README.md) and [Gate A matrix](../../../../docs/production/COURSE_COMPLETENESS_MATRIX.md) before claiming release readiness.

## Regression lesson — typed detection settings and event integrity

Run `test_invalid_threshold_types_are_rejected` and `test_invalid_event_outcome_is_rejected` to observe fail-closed responses to ambiguous data. Explain why a threshold of 2.5 or an outcome of integer 1 should never be silently interpreted as a production SOC policy. The synthetic fixture is not actual SIEM telemetry, and no operational detection accuracy or customer coverage is claimed.
