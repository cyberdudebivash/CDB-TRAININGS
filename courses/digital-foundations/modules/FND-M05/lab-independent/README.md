# FND-M05 — Independent lab: queue outcome summaries

**Estimated time:** 3 hours. This is the learner's own implementation task. The student starter is intentionally incomplete; passing a reference suite is not a substitute for making this code work independently.

## Step 1 — Predict the output for small inputs (LO1, LO2)
Input is a list of up to 1000 exact-schema dictionaries: id, queue, state. IDs are R-001 through R-999999 with one to six digits. Queue is ASCII, starts with a letter and has up to 32 letters/digits/_/-. State must be OPEN or CLOSED. Return total and a sorted list of queues with open/closed counts. Empty input is valid; malformed or extra fields and duplicates must raise ValueError.

## Step 2 — Implement independently and test (LO2, LO3)
Implement summarize_queues(records) in starter/queue_report.py. Run from repository root:
```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M05/lab-independent/checks -p test_queue_report.py -v
```
The initial starter deliberately fails ten contracts with FND-M05 STARTER INCOMPLETE. Complete the code without weakening the published tests. A protected instructor suite and real human grading remain mandatory.

## Step 3 — Explain an unsafe assumption (LO3)
Explain why a queue name containing shell syntax is unacceptable input and why the data must never be evaluated as a command. Distinguish successful published tests from untested invalid cases.

## Step 4 — Submit reproducible learner evidence (LO4)
Submit your code, test commands, Python version, actual result and three boundary conditions using only synthetic data. No customer records or external helpdesk APIs. Mark unavailable tests NOT_EXECUTED. A graded learner capstone is separate from this formative lab.