---
id: FND-M05
title: "Programming fundamentals with Python"
course: COURSE-FND-DIGITAL
level: 0
audience: "New technical learners and entry-level operations trainees"
prerequisites: ["FND-M01 paths and file safety", "FND-M02 command-line practice", "Python 3.11+ installed"]
estimated_time_hours: {lesson: 4.0, guided_lab: 3.0, independent_lab: 3.0, total: 10.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "Python 3.11+ standard library; validation limited to reported local runtime"}
last_verified: 2026-10-16
---

# FND-M05 — Programming fundamentals with Python

## Learning objectives

| ID | What the learner demonstrates |
|---|---|
| **LO1** | Explain values, types, conditionals, collections and loops in a bounded support operations problem. |
| **LO2** | Create functions that validate records, aggregate totals and return deterministic results. |
| **LO3** | Diagnose malformed input, test boundary conditions, and distinguish intentional errors from environment failures. |
| **LO4** | Produce a reproducible evidence report without exposing private data or claiming customer integrations. |

This 10-hour module develops beginner Python programming ability using invented support-ticket records. It is *not* a professional Python Engineering qualification. The objective is to learn to reason about input, transformation, output and failure. No learner needs production support data, an API key, cloud credits or elevated filesystem privileges. You should be able to reproduce each exercise on a fresh Python installation and a disposable practice directory. Human editorial, technical and learner reviews are outstanding.

## 1. Data, types, and control flow (LO1)

Programs transform input into output under explicit rules. First describe what data represents before choosing a type. A ticket identifier is text even when it contains digits because those digits are part of a label. A duration is an integer number of minutes because partial minute precision is outside this exercise's contract. Severity is one of three uppercase strings rather than any arbitrary word. A list holds an ordered sequence of records; a dictionary associates names with values. These choices determine which operations the program can perform and what invalid states it must reject.

Python is dynamically typed, but that is not permission to ignore types. A string containing "12" is not the same value as integer 12. The former could include leading zeroes that matter to an identifier. The latter supports arithmetic. Python's bool is a subclass of int, which can surprise beginners writing numeric validators. When the contract requires a genuine integer rather than an integer-like value, check for the exact intended type. To avoid hiding invalid data, do not convert every unexpected input to text before validation. Ask whether the specification permits that conversion.

```python run
value = "12"
assert type(value) is str
assert int(value) == 12
assert type(True) is bool
assert type(True) is not int
```

A conditional chooses a branch. In the support scenario, if severity equals HIGH then the high-severity counter increases; otherwise it does not. A loop processes records one at a time. For each record, the program must validate its fields before counting it. If you count a ticket and only later notice an invalid severity, your result may become inconsistent. The guided implementation keeps its intermediate report within the function and raises an error instead of returning partial results. It does not write a corrupted report to disk.

Practice describing the outcome before executing code. If three records contain durations 5, 10 and 0, the total is 15 minutes. If two belong to team Support and one to Platform, the report should show separate group totals. The insertion order of records is not an acceptable reporting contract when a downstream reviewer expects sorted output. Make ordering explicit so the same data produces the same report across repeated runs.

```python run
severities = ["LOW", "HIGH", "MEDIUM", "HIGH"]
high_count = sum(1 for value in severities if value == "HIGH")
assert high_count == 2
teams = {"Support": 2, "Platform": 1}
assert sorted(teams) == ["Platform", "Support"]
```

Functions divide one problem into testable pieces. A function has a name, arguments, a documented contract and a return value or documented failure. The guided reference separates path inspection, CSV schema validation and summary aggregation. The independent task asks learners to implement an aggregation function without copying its answer. In both cases, local unit tests support learning because failures identify which assumption was violated. They are not a substitute for human explanation or unseen grading.

## 2. Functions, collection operations, and deterministic reports (LO2)

A support operations team may need a concise summary of an exported ticket queue. A human could count the rows manually, but hand-counting becomes error-prone when repeated. A short script can provide a repeatable result when its input contract is clear. The program should not decide what a ticket means or infer incident severity from an unverified narrative. It should count exactly the fields present in synthetic records, applying the rules stated in advance.

The guided CSV format is deliberately small: ticket_id, team, minutes and severity. For example, the invented row AB-001,Support,5,HIGH represents a ticket ID, an alphabetic team, a five-minute duration and a severity label. The reference checks the column names and order, rejects duplicate ticket IDs, and validates duration and severity. Only then does it update counters. A dictionary keyed by team is suitable because each team's record can be retrieved and updated without scanning a list of previous groups for every new ticket.

```python run
records = [("Support", 5), ("Platform", 0), ("Support", 10)]
minutes_by_team = {}
for team, minutes in records:
    minutes_by_team[team] = minutes_by_team.get(team, 0) + minutes
assert minutes_by_team["Support"] == 15
assert [(name, minutes_by_team[name]) for name in sorted(minutes_by_team)] == [("Platform", 0), ("Support", 15)]
```

The phrase deterministic means that the same validated input produces the same output, not that the input reflects the complete truth of a live business process. A sorted team list and stable field names help callers compare results. The exercise deliberately does not include timestamps from the runtime, random identifiers or automatic access to external services. If results differ between runs, the learner should first check whether the input changed or whether a hidden ordering assumption exists.

When implementing a function, begin with a small correct case and write an assertion. Then add an empty case, an invalid case and a boundary value. Do not optimize for speed before you have established what correct behavior means. A short, explicit loop is often easier to maintain than nested comprehensions when a team is learning. Prefer meaningful names such as ticket_id and total_minutes instead of vague one-letter variables outside tiny examples.

The public learner exercise is purposely different from the CSV reference: it aggregates synthetic OPEN and CLOSED queue items supplied as a list of dictionaries. That prevents a learner from passing merely by repeating the guided code. It requires validation, duplicate identification, bounded input, grouping and deterministic sorting. The student implements summarize_queues(records) independently, using the published specification and tests. The instructor-only grading package must remain out of the public Git repository.

## 3. Input validation, errors, and tests (LO3)

A robust program must state what happens when input violates expectations. A missing column is not a zero; a malformed ticket ID is not a new customer; a negative duration is not an amount to subtract silently. Rejecting unexpected input is often safer than guessing. The reference raises ValueError when data does not satisfy its contract. A production program might also create structured operator diagnostics, but the classroom example avoids printing sensitive row values into errors. That is intentional data minimization, not suppression of quality evidence.

Python exceptions distinguish normal results from invalid or unavailable operations. ValueError can represent a bad input value, while FileNotFoundError relates to an unavailable path. However, the outer public API may intentionally convert several low-level read problems into a sanitized error category so that unexpected personal paths do not leak into a user-facing message. The exception type and its documented meaning are part of a function's interface and should be tested.

```python run
def minutes(value: str) -> int:
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValueError("duration must be canonical digits")
    parsed = int(value)
    if parsed > 1440:
        raise ValueError("duration exceeds lab range")
    return parsed

assert minutes("12") == 12
try:
    minutes("-12")
except ValueError:
    pass
else:
    raise AssertionError("bad input was silently accepted")
```

The reference also enforces a maximum input file size and a maximum number of records. Without resource bounds, a mistake or intentionally malformed file could consume excessive memory or CPU in a classroom environment. A CSV parser must handle quoting and line endings according to its specified format, but should not assume every record contains the exact expected number of fields. The tests include malformed rows and invalid encoding so that learners see failure detection instead of a false positive result.

Paths require their own reasoning. A learner should provide a relative CSV filename under a temporary practice directory. A parent path such as ../somewhere.csv must be rejected, and symbolic links are excluded from the toy reader. Still, checking the path first and opening it afterwards leaves a race: a concurrent process could change filesystem entries. Do not present a teaching-level path check as comprehensive sandboxing or evidence-grade acquisition. Genuine multi-user file services require stronger operating-system and service-boundary controls.

Unit tests are executable statements about examples of a contract. A passing set provides useful evidence for the cases executed. It does not prove that all possible inputs were covered, and it does not establish professional competence by itself. When a learner receives a failure, they should read the assertion, reproduce the smallest input, distinguish an implementation defect from a missing dependency and change only the implementation. Never weaken a negative test solely to improve the reported score.

```python run
def label(state: str) -> str:
    if state not in ("OPEN", "CLOSED"):
        raise ValueError("unsupported state")
    return state.lower()
assert label("OPEN") == "open"
try:
    label("unknown")
except ValueError:
    pass
else:
    raise AssertionError("validation missing")
```

A useful test plan includes at least one valid record, multiple records that share a team, an invalid duration, a duplicate identifier, an unsupported severity, a malicious-looking string, a file outside the practice scope, a large file and an improperly encoded file. Not every system needs the same rules; these tests are specific to the training contract. A requirement that is reasonable for a monthly payment ledger may be wrong for a diagnostic tool whose valid observation period has zero events. Always validate according to the declared business context, not an arbitrary universal rule.

## 4. Practice operations and learner evidence (LO4)

The guided task uses a fictional support report. Begin by recording the local Python interpreter, version and working directory. In your own temporary practice folder, create a text CSV containing invented ticket IDs. Run the public reference tests from the repository root and confirm the result. Then modify a disposable copy by duplicating a ticket ID; repeat the check and explain why an exception is correct. Do not bring real helpdesk exports, phone numbers, email addresses or private correspondence into the public lab.

After understanding the reference, move to the independent practice. Predict the output for three synthetic queue records before you write code. Implement the starter function with exact fields and validation. Run the independent test suite and continue until the intended learner checks pass. The initial starter raises an explicit incomplete-message assertion. This is not a broken repository test: the exercise is designed to start in a failing state. Completing the starter without modifying the public tests is part of the learning objective.

A professional handoff identifies the case, environment, evidence, result and limitations. It should state exactly which tests executed and whether any were skipped. Record unexpected failures, and give another learner a clear way to reproduce them. Explain why a simple CSV summary cannot establish SLA achievement, billing correctness or customer satisfaction. Data can be syntactically valid while being incomplete, out of date or collected without authorization. Do not convert such gaps into claims of verified operational truth.

A support technician should know when to escalate. If real systems are involved, the operator must have authorization, retention rules, access boundaries and a documented incident process. If a customer requests production data analysis, that is a separate supported service with its own design, legal and security review. The lab deliberately has no such integration; inventing one would weaken the credibility of the training program.

Complete the guided exercise, the independent task and the eight-question assessment. A qualified reviewer also evaluates your explanations using the public rubric. Competence requires both independent technical performance and an honest account of limitations. This module does not alone complete the Digital Foundations course: FND-M06 is still outstanding, the previous modules require human acceptance, and a validated full-course PDF has not been produced. Do not claim a customer-ready Academy release on the strength of lesson text or a green unit test report.
