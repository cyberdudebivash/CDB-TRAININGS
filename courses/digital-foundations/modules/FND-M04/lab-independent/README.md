# FND-M04 independent lab — Review evidence decision

**Classification:** Synthetic logic exercise. No GitHub API, remote access or automatic merge. **Estimated time:** 75 minutes. **LO1, LO4.**

## Step 1 — Predict evidence and decision (LO1)

A fictional team records six fields describing a proposed change. `base_sha` and `head_sha` are exactly 40 lowercase hex characters (teaching fixture using SHA-1 object IDs). `changed_files` is a list of at most 25 distinct relative filenames, each 1–128 characters long; all entries are POSIX-style paths with no leading slash, no backslashes, no empty, `.` or `..` components, no `.git` component and no control characters. `checks_passed`, `reviewed_by_other`, and `conflicts_remaining` are actual boolean values. These recorded values are **claims**, not independently verified GitHub evidence.

A structurally invalid input returns `{ 'ready': False, 'reasons': ['invalid-evidence'] }`. A structurally valid input returns `ready=True` only if (a) base/head SHAs differ and there is at least one changed file, (b) checks_passed is true, (c) reviewed_by_other is true, and (d) conflicts_remaining is false. Reasons must be output in this fixed order: `no-diff`, `checks-failed`, `review-missing`, `conflicts-open`. Return every applicable reason. No other keys or reason strings are allowed.

Before writing code, predict decisions for a green change, a change with no diff, an unreviewed change and an unresolved conflict. Explain why a true review field does **not** prove a GitHub reviewer actually approved a real PR.

## Step 2 — Implement the review evidence contract (LO4)

Complete `starter/review_gate.py::assess_review(evidence)`. The starter intentionally raises `NotImplementedError` as an educational checkpoint. Do not hide invalid inputs by type coercion (`True` is an `int` subclass in Python, for example). Every unknown input field must cause an invalid-evidence result, even if the rest of the data looks valid.

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M04/lab-independent/checks -p test_review_gate.py -v
```

All 12 public tests should eventually pass on your implementation. Initially, tests fail with `FND-M04 STARTER INCOMPLETE` and clear next-step instructions. The public tests are not the only grading evidence; a qualified instructor should independently review edge cases and reasoning. Keep any instructor-only reference and hidden tests out of this public repository.

## Step 3 — Explain real GitHub gate limitations (LO4)

Write a 250–400 word sanitized handoff describing what the simulation validates, which external systems would have to be checked for genuine approvals, and how a pull request may become stale after testing. Explicitly separate **local Git graph facts**, **synthetic input assertions**, **actual CI evidence**, and **live hosted review state**. Do not invent pull-request numbers, reviewer names or training-success claims.
