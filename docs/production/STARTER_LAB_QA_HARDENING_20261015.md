# Starter-Lab Quality Hardening — 15 October 2026

**Scope:** Two confirmed safety/contract defects and eight lab-guide corrections; no course certification or customer rollout.

## Reproduction before correction

### COURSE-GCP-DE — batch-quality

- A correctly headed CSV with zero data rows returned `is_safe_to_load = True`. This is unsafe to describe as a successful nonempty batch.
- The date values `2026-W42-4` (ISO week-date notation) and `20261014` (compact date) were accepted because Python's `date.fromisoformat` accepts formats wider than the declared canonical input contract.
- The new implementation distinguishes a correct calendar date from the strict required `YYYY-MM-DD` format and requires at least one data row.

### COURSE-CYBER-MEGA — auth-triage

- A threshold of `2.5` was silently accepted, although event counts and alert thresholds must be integral.
- A threshold of `'3'` caused an uncontrolled Python TypeError rather than a predictable validation failure.
- The new implementation accepts only real integers within 2..100, requires a timedelta window and validates event IDs, sources, outcome type and timezone-aware datetime.

## Executed local verification

Authoring runtime: CPython 3.13.5, Node.js 22.16, JDK 21.0.12.1. Offline tests only, using synthetic fixtures.

| Evidence | Result |
|---|---|
| Python/Node/Java starter contract checks | **59 passed, 0 failed, 0 not executed** |
| Existing cross-course integration regression | **15 passed** |
| AST compilation of available Python starter files | **PASS** |
| GitHub branch clean-clone repository-wide QA | **NOT EXECUTED** |
| Platform-neutral cross-version runtime matrix | **NOT EXECUTED** |
| SME/learner pilot review | **NOT EXECUTED** |

The original suite contained 53 checks. Six additional negative-control tests are now present: three data-quality tests and three triage tests.

## Documentation corrections

All eight Wave01 lab guides previously contained a generic sentence about Java compiler outputs, including Python and Node.js exercises. The guides now refer to the appropriate local runtime, with Java-specific instructions retained only for the Java lab. GCP and security-triage guides explicitly teach the new rejection cases.

## Outstanding risk and deployment barriers

- The tests are narrow functional contracts, not proof of production capability or full customer workflow integration.
- Complete learning modules, source traceability, capstones and full-course PDF editions remain outstanding for these tracks.
- The repository-wide Gate A classifier must not use starter-lab checks to promote a course or module to TRAINING_CONTENT_GO.
- The public Frontend source-PDF privacy incident remains unresolved and requires owner-controlled containment.
- No existing commercial offer, Academy site, Cloudflare deployment or external service was changed.

**Release classification:** INCREMENTAL_QA_HARDENING — REVIEW_REQUIRED. The PR should remain draft until the exact committed branch passes clean-checkout QA and code review.
