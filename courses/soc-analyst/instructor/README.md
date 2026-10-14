# Instructor pack (private) - how this works

This repository is **public**, so instructor-only material is **not stored here**. It lives in a private repository
(suggested name: `cdb-trainings-instructor`) and is copied into this folder locally when instructors need to run or grade
the course. Everything in this folder except this README is git-ignored.

## What the pack contains for SOC-M04

| File | Purpose |
|---|---|
| `m04-quiz-answer-key.md` | Answer key and one-line justification for each of the 10 quiz items |
| `m04-independent-reference/` | Reference rules and exceptions that pass the independent lab on the published practice seed, with the expected evaluator output |
| `m04-grading-notes.md` | How to score reviewer criteria C5-C9 with examples of level 1/2/3 evidence, common learner difficulties and remediation steps |

## How the automated tests treat it

`tests/pilot/test_independent_lab.py` runs the reference solution **only if** `m04-independent-reference/` exists. Without it the test is reported as
`SKIPPED_PRIVATE_MATERIALS` - that status means *not verified in this environment*, never "passed".

## Running a graded attempt

1. Choose a secret seed and generate data: `python -m soc_lab generate --profile independent --seed <SECRET> --out <dir> --with-truth`.
2. Give the learner `<dir>/events.jsonl` and `<dir>/context.json` only (never `truth/`).
3. Grade with the commands in the independent-lab README using your `truth/`, then score reviewer criteria with `m04-grading-notes.md`.
4. Record the result; completion is awarded only if the rubric's pass rule holds.

## Status of this pack

The pack for this pilot was created during the audit session and delivered to the owner as a separate file; until the owner confirms it is stored in the
private repository it exists only in that delivery.
