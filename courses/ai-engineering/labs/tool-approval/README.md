# Operational Starter Lab — Fail-closed tool authorization for AI proposals

**Course:** `COURSE-AI-ENG` (Applied AI and LLM Engineering Pathway)  
**Scope:** Standalone guided operational exercise; not a completed curriculum module.  
**Prerequisites:** Python 3.11+ standard library.

## Customer-operations scenario

A customer-support AI proposes which tool to invoke; the execution service must not grant permissions simply because model output claims it is authorized.

## Engineering acceptance contract

Validate exact JSON envelope and allowed action schemas; restrict invoice lookup to consented synthetic identifiers; require human approval for outbound drafts.

All inputs are fictional or synthetic. The implementation makes no network calls, does not use customer identities or secrets and must never be pointed at an unauthorized system. The exercise is designed to develop safe problem-solving before introducing real service integrations.

## Execute validation

From the repository root:

```text
python -m unittest discover -s courses/ai-engineering/labs/tool-approval -p test_lab.py -v
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

No model, LLM endpoint, network access, actual agent execution, identity provider or external sending. Not a general-purpose JSON firewall.

Use the top-level [course status](../../README.md) and [Gate A matrix](../../../../docs/production/COURSE_COMPLETENESS_MATRIX.md) before claiming release readiness.
