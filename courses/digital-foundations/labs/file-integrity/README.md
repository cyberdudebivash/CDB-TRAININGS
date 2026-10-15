# Operational Starter Lab — File integrity and controlled directory inspection

**Course:** `COURSE-FND-DIGITAL` (Digital and Technical Foundations)  
**Scope:** Standalone guided operational exercise; not a completed curriculum module.  
**Prerequisites:** Python 3.11+ standard library.

## Customer-operations scenario

A support technician receives a folder of exported diagnostic reports and must establish whether its contents changed before investigation.

## Engineering acceptance contract

Show bytes and SHA-256 per regular file; reject symbolic links and invalid manifest inputs; prove that altered or added files are detected.

All inputs are fictional or synthetic. The implementation makes no network calls, does not use customer identities or secrets and must never be pointed at an unauthorized system. The exercise is designed to develop safe problem-solving before introducing real service integrations.

## Execute validation

From the repository root:

```text
python -m unittest discover -s courses/digital-foundations/labs/file-integrity -p test_lab.py -v
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

TOCTOU changes during enumeration, operating-system permissions, digital signatures, and real chain-of-custody are outside this bounded starter.

Use the top-level [course status](../../README.md) and [Gate A matrix](../../../../docs/production/COURSE_COMPLETENESS_MATRIX.md) before claiming release readiness.
