# FND-M02 independent lab — Interpret a synthetic command-run transcript

**Time budget:** 90 minutes. **Starter:** deliberately incomplete and not production-safe. This assessment never executes a command: it parses a bounded transcript of commands supposedly run earlier in a fictional test environment.

## Step 1 — Predict outcomes (LO2, LO3)

A line has form `exit_status|command_label`, for example `0|inventory` or `3|synthetic-alert`. Exit status must be a base-10 decimal representation of an integer from 0 to 255 with no sign or leading/trailing spaces. A label contains 1 to 32 characters from ASCII letters, digits, `_` and `-`. Empty lines, duplicate labels and excess lines are invalid. No shell commands or human identities are included.

Before coding, write down how `0|inventory`, `3|synthetic-alert`, `oops|inventory`, and `0|inventory|extra` should be classified. A parsed status describes a program's declared contract—not automatically an error, an attack or permission to rerun it.

## Step 2 — Implement the transcript contract (LO2, LO4)

Complete `summarize(lines)` in `starter/tracecheck.py`. It must accept a list of at most 100 valid records; reject malformed lines with `ValueError`; produce a summary dictionary containing integer keys `total`, `zero`, `nonzero` and a list of `failures` with corresponding labels and statuses in original order. A zero-length list is valid and yields all counts zero and an empty failures list. Do not use `eval`, `exec`, `os.system` or `subprocess`.

Run the student tests:

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M02/lab-independent/checks -p test_tracecheck.py -v
```

The starter intentionally raises `NotImplementedError`: initial failures are expected. No hidden solution should be inferred from the public tests. When the implementation passes, create a new negative test for a duplicate label or malformed status not already covered.

## Step 3 — Evidence handoff (LO3, LO4)

Submit your source, test transcript, interpreter and OS versions, and a concise explanation of why treating status 3 as universally fatal would be incorrect. Explain how you would review stdout, stderr and the exact program contract before giving an operational conclusion. No real support tickets or client logs may be used.

## Scoring and boundaries

All published checks are mandatory for provisional technical acceptance; a qualified reviewer must also assess your reasoning and failure analysis. Hidden instructor checks and a real learner pilot remain pending. This is a bounded parsing problem, not a shell parser or a method of launching customer commands.
