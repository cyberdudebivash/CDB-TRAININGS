# FND-M01 — Guided lab: synthetic file integrity

**Status:** Teaching reference, not a forensic acquisition tool. **Estimated time:** 75 minutes. No administrator privileges, customer data or cloud API.

## Prerequisites

Use Python 3.11+ and a disposable working directory. Keep all data synthetic. The reusable, tested reference is in `courses/digital-foundations/labs/file-integrity/integrity.py`. This module intentionally reuses it rather than silently copying diverging versions.

## Step 1 Practice environment (LO1)

Record your host OS, Python interpreter and current directory. On Windows use PowerShell `Get-Location`; on Linux use `pwd`. Execute from the repository root and do not write into system folders.

## Step 2 Verify synthetic artifacts (LO2, LO4)

Run the contract:

```text
python -m unittest discover -s courses/digital-foundations/labs/file-integrity -p test_lab.py -v
```

In a disposable directory create a synthetic text file, call the reference `inventory(directory)`, then modify the bytes and call `verify(directory, baseline)`. Expect `False` after modification. Save the reference manifest outside the directory under inspection. Repeat with one added file and explain the result. If a symlink test is skipped due to platform limitations, record it honestly.

## Step 3 Record a handoff (LO4)

Write an evidence note containing the approved scope, OS and interpreter version, exact command, synthetic test results, and two limitations: a hash does not establish authorization or authorship, and a live directory scan may race with concurrent modification. Avoid passwords, genuine customer names and personal data.

## Assessment and cleanup

The guided regression must pass in the declared environment; any skipped case needs explanation. A reviewer examines the evidence note separately. Use temporary synthetic resources and remove only what you created. This lab is not a commercial product or customer-operations integration.
