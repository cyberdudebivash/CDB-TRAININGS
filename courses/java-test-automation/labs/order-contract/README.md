# Operational Starter Lab — Boundary-value testing for a monetary order calculator

**Course:** `COURSE-JAVA-QA` (Java Test Automation Engineer Pathway)  
**Scope:** Standalone guided operational exercise; not a completed curriculum module.  
**Prerequisites:** JDK 21+.

## Customer-operations scenario

A QA engineer must establish a clear test contract before automating a retail order subtotal and percentage discount calculation.

## Engineering acceptance contract

Use BigDecimal; test negative values, out-of-bounds discounts, zero quantity and rounding. Demonstrate a standalone assertion harness without external dependencies.

All inputs are fictional or synthetic. The implementation makes no network calls, does not use customer identities or secrets and must never be pointed at an unauthorized system. The exercise is designed to develop safe problem-solving before introducing real service integrations.

## Execute validation

From the repository root:

```text
javac -d build courses/java-test-automation/labs/order-contract/OrderCalculator.java courses/java-test-automation/labs/order-contract/OrderCalculatorTest.java && java -cp build OrderCalculatorTest
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

Demonstration is not JUnit, Selenium, browser automation or a validated checkout/payment integration. An actual course must teach those separately.

Use the top-level [course status](../../README.md) and [Gate A matrix](../../../../docs/production/COURSE_COMPLETENESS_MATRIX.md) before claiming release readiness.
