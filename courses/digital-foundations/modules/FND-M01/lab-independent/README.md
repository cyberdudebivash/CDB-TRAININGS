# FND-M01 — Independent lab: simulated file access

**Status:** Learner assignment, deliberately incomplete starter. **Estimated time:** 75 minutes. This is not Linux kernel enforcement or a Windows ACL emulator.

## Scenario

A fictional operations team needs to decide whether the synthetic role `analyst` has a specific operation permitted by a toy resource permission mapping. There is no real file access, no identity service, and no network traffic.

## Step 1 Define predicted outcomes (LO1)

Write down one allowed, one denied and one invalid request before writing code. Do not modify OS permissions.

## Step 2 Implement the policy contract (LO3)

In `starter/access_check.py`, implement `check_access(subject, resource, operation) -> bool`. The subject is an object containing a non-empty string role. The resource contains a `permissions` mapping from roles to sequences of exact operation strings. Only the operations `read`, `write` and `execute` are recognized. Reject malformed inputs with `ValueError`, deny valid requests lacking an explicit grant, and never treat partial strings or prefixes as grants.

Run the published checks from repository root:

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M01/lab-independent/checks -p test_lab.py -v
```

The starter intentionally raises `NotImplementedError`. Your initial checks will fail; implement the contract until they pass. The public checks are not a substitute for protected instructor tests or human review.

## Step 3 Document operational limits (LO4)

Prepare a short handoff stating exactly what the simulated result means and does not mean. Explain one Windows ACL feature and one real Linux permission factor excluded from this role map. An OS allowing access also does not confer business consent. Record test execution and all unverified conditions.

## Assessment

All published checks must pass; a qualified reviewer evaluates edge-case reasoning, fail-closed behavior and the handoff with the public rubric. Never use this demonstration to grant actual access to any customer resource.
