# FND-M05 knowledge check (8 questions)

Formative: it checks understanding of the lesson and is **not** evidence of competence on its own (the independent lab is). The answer key is held by instructors and is not published.
Questions are generated from `quiz.yaml`; each is tied to a learning outcome.

| # | Outcome | Question | Options |
|---|---|---|---|
| Q1 | LO1 | Which data type best represents a ticket identifier such as AB-001? | A) An integer with arithmetic behavior. B) A text string whose format is validated. C) A boolean flag. D) A binary floating-point duration. |
| Q2 | LO1 | What does a Python dictionary provide for per-team report aggregation? | A) A permission model for the operating system. B) Proof of record provenance. C) A mapping from each team name to running counters. D) Automatic cryptographic integrity. |
| Q3 | LO2 | What makes an ordered report deterministic for the same valid input? | A) An explicit sort rule for the report groups. B) The operating system file timestamps. C) Randomized group identifiers. D) Assuming insertion order has no effects. |
| Q4 | LO2 | Why split input parsing, validation, and aggregation into functions? | A) To disable exceptions automatically. B) To avoid reading the specifications. C) To replace independent unit tests. D) To isolate contracts so each transformation is testable. |
| Q5 | LO3 | What should happen when two synthetic tickets reuse the same unique ticket ID? | A) Count both to maximize output. B) Reject the invalid dataset according to the contract. C) Silently rename the second ID. D) Mark both as real customer incidents. |
| Q6 | LO3 | Which result is appropriate when the student starter has not been implemented? | A) A complete Academy certification. B) A silently skipped verification. C) An actionable expected failing test. D) A claim of live system validation. |
| Q7 | LO4 | What should a learner include in a reproducible report? | A) Runtime, command, actual tests run, outcomes, and unverified limits. B) Only screenshots of success messages. C) Real customer records and passwords. D) A statement that all platforms are supported. |
| Q8 | LO4 | Why does a green synthetic CSV test not prove SLA compliance? | A) CSV has no possible type validation. B) Python cannot read a local file. C) Any ticket record is necessarily fraudulent. D) It exercises synthetic transformations, not the customer service lifecycle. |

**Scoring:** instructors apply the key; 6/8 is the formative checkpoint.
