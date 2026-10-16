# FND-M05 — Guided Python support-ticket metrics lab

**Status:** Synthetic training reference, not a production customer integration. Python 3.11+, no network, paid cloud or elevated privileges.

## Step 1 — Define data and validation (LO1)
Use only invented ticket records with exact CSV columns `ticket_id,team,minutes,severity`. Explain why IDs are text, minutes are bounded integers, and severity is allowlisted. The reference explicitly rejects duplicate IDs, malformed rows and unexpected path forms.

## Step 2 — Execute the guided tests (LO2, LO3)
From the repository root, run:
```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M05/lab-guided/checks -p test_support_metrics.py -v
```
Record the executed count and Python version. Explain the deterministic sorting, grouping and high-severity counter. A passing reference is not proof of independent learner mastery.

## Step 3 — Controlled negative tests (LO3)
Make disposable synthetic CSV files with a duplicate ticket, invalid duration and unsupported severity. Confirm predictable rejection. Never copy a real customer export or inspect paths outside the practice directory. Note that the example's symlink checks are not race-free confinement.

## Step 4 — Accurate support handoff (LO4)
For two invented Support records with minutes 5 and 10, document two tickets and fifteen total minutes. Include command, actual result, failures and residual limitations. No SLA, billing, customer identity or live incident claim is supported.

Qualified human grading, protected instructor tests, student pilot, validated PDF and portfolio Gate A approval remain outstanding.