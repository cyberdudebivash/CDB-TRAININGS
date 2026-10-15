---
id: FND-M02
title: "Command-line fundamentals"
course: COURSE-FND-DIGITAL
level: 0
audience: "Beginner learners and entry-level support operators in an unprivileged practice environment"
prerequisites:
  - "FND-M01 operating systems, files and permissions, or equivalent knowledge"
  - "A safe terminal and Python 3.11+"
estimated_time_hours: {lesson: 2.0, guided_lab: 1.5, independent_lab: 1.5, total: 5.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "Python 3.11+ standard library, local reference tested on Python 3.13.5", windows: "PowerShell command concepts, Windows not independently executed", linux: "POSIX shell concepts, local practice only"}
last_verified: 2026-10-15
---

# FND-M02 — Command-line fundamentals

## Learning objectives

| ID | Observable outcome |
|---|---|
| **LO1** | Identify a shell, working directory, program arguments, and differences between absolute and relative paths. |
| **LO2** | Interpret standard input, standard output, standard error, and documented command exit statuses. |
| **LO3** | Explain shell quoting, pipeline, and redirection risks; keep untrusted data out of executable command strings. |
| **LO4** | Execute a bounded command-line diagnostic tool with synthetic events, collect evidence, and prepare an accurate operational handoff. |

**Safety boundary:** These are disposable, synthetic, local exercises. No real customer data, administrator privileges, security-control changes, live SOC feeds, shell-based remote execution, or cloud spend are authorized. A test pass is not approval to run diagnostics on a customer system.

## 1. Shells, commands, and working directories (LO1)

A terminal is the interface displaying text input and output. A shell is the program that interprets commands and starts tools. A learner might encounter Bash or Zsh on Unix-like systems, Windows PowerShell, or cmd.exe on Windows. They differ in quoting, variables, pipelines, redirection, path syntax, and error reporting. A production runbook must name the shell used; copying commands blindly across shells risks changing their meaning. Begin by recording the shell and current working directory, not by installing more tools.

A command consists of a program or built-in name followed by zero or more arguments. What appears as a simple text line may be transformed by the shell before a program starts. For example, wildcard expansion and variable substitution can alter arguments. Quoting rules vary. An executable named Python can run a trusted script with validated command-line flags, but the script itself must still enforce an input contract. A well-quoted untrusted path is not proof that the caller is permitted to read it.

On a POSIX shell, use pwd to inspect the working directory and ls to list its immediate entries. PowerShell offers Get-Location and Get-ChildItem. These are examples to interpret, not permission to scan other people's folders. Confirm that you are inside your own practice directory. Prefer explicit command names in shared runbooks because aliases vary among computers and shell profiles.

An absolute path is anchored at a root or volume. A relative path is evaluated from a process's working directory, which may differ from the directory containing the script. A scheduled task may run with a different working directory from an interactive session; relative paths can then resolve to the wrong place. When a practice CSV appears to be missing, inspect the actual directory, flag spelling, and input path before changing permissions or searching outside scope.

Python pathlib can express relative path composition without launching a shell:

```python run
from pathlib import Path
root = Path("practice")
relative = Path("logs") / "events.csv"
assert not relative.is_absolute()
assert (root / relative).parts[-2:] == ("logs", "events.csv")
assert (root / relative).name == "events.csv"
```

This demonstrates path syntax, not filesystem authorization. A path can be well formed while its target is absent, untrusted, or inaccessible. The real system's access checks, parent folder traversal rules, symlinks, and mount behavior are additional concerns. Our bounded CLI rejects suspicious forms of path input, but it is not a general filesystem isolation library and is not safe against adversarial race conditions.

## 2. Standard streams and exit status (LO2)

Process standard input is a conventional stream for receiving data; standard output normally holds primary results; standard error normally holds diagnostics. Software consuming machine-readable output must not mistake an error line for a valid result. Programs sometimes use standard error for informational messages, so the command's contract matters. Your professional evidence must record both data and the resulting process status.

By convention, an exit status of zero indicates normal completion. Nonzero numbers require tool-specific interpretation. Our training CLI declares status 0 for valid input and normal completion, status 2 for malformed input or arguments, and status 3 when the optional fail-on-error policy matches a synthetic ERROR event. Status 3 is an intentional alert-policy outcome, not proof of a crashed operating system or a customer incident.

Shell redirection connects or changes the destination of streams. In many POSIX shells, > redirects standard output to a named file and 2> redirects standard error; a careless redirect can overwrite a pre-existing file. PowerShell has a richer stream model and differing syntax. A pipeline connects output from an earlier command to input of another program. A successful final stage does not automatically prove that upstream stages succeeded. When reviewing a customer-runbook proposal, ask which command might fail, what signal it produces, and how the workflow preserves evidence.

Use a small pure function to reason about documented status codes without running external commands:

```python run
def interpret_status(code: int) -> str:
    return {0: "completed", 2: "invalid-input", 3: "matched-alert-policy"}.get(code, "not-documented")
assert interpret_status(0) == "completed"
assert interpret_status(3) == "matched-alert-policy"
assert interpret_status(7) == "not-documented"
```

The reference CLI emits a JSON object containing count and events when input is valid. The program's return status must be inspected separately; JSON output and status 3 are compatible when an alert threshold is intentionally enabled. If input is invalid, the CLI writes a sanitized error category to standard error and returns status 2. Learners must not label that failure as a successful scan merely because the command printed text.

After running a command in POSIX Bash/Zsh, inspect $? immediately; in PowerShell inspect $LASTEXITCODE for an external process. Running a different command before checking may replace the earlier status. Exact syntax should be confirmed in the actual shell, which must be named in your runbook. Never claim PowerShell output was independently validated if the exercise was performed only on Linux.

## 3. Quoting, pipelines, and untrusted command data (LO3)

Shells treat certain characters as syntax: quotes can group arguments, a semicolon may separate commands, dollar signs can introduce expansion, and pipes connect processes. Putting raw user text into a shell command string risks unexpected operations. The safer general design when Python must run a trusted executable is to pass an explicit argument list to an approved process API without shell parsing. That reduces a class of injection risks, but does not make dangerous executables or unauthorized arguments safe.

The following demonstration constructs only an in-memory argument array. It starts no process and reads no files:

```python run
untrusted_filename = "synthetic; not-a-command.csv"
argv = ["python", "runbook.py", "--input", untrusted_filename]
assert len(argv) == 4
assert argv[-1] == untrusted_filename
assert ";" in argv[-1]
```

A command-processing pipeline needs a clear trust boundary at every stage. Validate input schemas instead of assuming a quote character will protect an application. Reject unexpected fields, apply bounded resource limits, and distinguish data from program instructions. Where an external program is necessary, review the executable, working directory, exact flags, environment and permissions. Avoid displaying passwords, tokens, home-directory paths, or confidential filenames in public learner submissions.

Our guided local reference only accepts a relative POSIX-style CSV input below a learner-chosen practice directory. It refuses absolute paths, parent traversal, symlinks, malformed CSV rows, excessively large inputs, duplicate events and timestamps without timezone information. These are useful beginner controls but do not prevent a concurrent attacker from changing filesystem entries after validation. It would be misleading to call the tool a production-safe upload reader, forensic collector or remote execution service.

Command descriptions must always identify observable behavior. A malicious-looking text field in a CSV must remain data. It should never be evaluated as code or passed to a shell. In the lab, a semicolon in the synthetic message is intentionally harmless. Run the validation test rather than executing dangerous commands to prove a point.

## 4. Diagnostic command execution and synthetic event reporting (LO4)

Imagine a fictional support request: determine whether a local synthetic authentication service emitted WARN or ERROR records during a controlled simulation. The CSV contains exactly four fields: timestamp, service, severity and message. A real enterprise workflow would require documented customer authorization, data handling, reliable log transport and case management. Here, the educational dataset contains no real identities and there is no external service connection.

The guided program accepts --root, --input, --min-severity and --fail-on-error. It reads but never modifies the CSV, emits deterministic JSON for a given input, and returns one of the documented process statuses. The severity filter is inclusive, so a WARN threshold also includes ERROR. An empty valid CSV is allowed in this diagnostic inspection workflow, because a quiet observation period can have zero events; that differs from commercial ingestion contracts that require nonempty deliveries.

The program rejects duplicate events, unsupported severity values, malformed headers, invalid date-time values, unusually large files and unapproved path forms. Those controls are deliberately narrower than customer production systems. They do not prove malicious attribution, detection accuracy or freshness of telemetry. Learners should compare the input contents and output count, not claim a remote environment has been observed.

JSON is a serialization format rather than security evidence. Parsing and decoding may preserve the structured form of the result, but assertions about provenance and authorization need separate controls:

```python run
import json
sample = {"count": 1, "events": [{"service": "auth", "severity": "ERROR"}]}
decoded = json.loads(json.dumps(sample, sort_keys=True))
assert decoded["count"] == len(decoded["events"])
assert decoded["events"][0]["severity"] == "ERROR"
```

The lab's fourteen contract tests cover valid filtering, expected statuses, invalid encodings, suspicious paths, symlinks, input limits and malformed event records. Record the actual number of executed tests and any skips. A clean run on one operating system does not establish portability, nor does a successful unit test prove the completeness of a training course.

## 5. Guided safe-runbook practice (LO1, LO2, LO3, LO4)

Start with the [guided exercise](lab-guided/README.md) in a non-administrator shell. Record your current directory and interpreter version. Create a temporary directory with a synthetic events.csv file, run all published contracts, then invoke the reference program with a WARN filter. Read its JSON result and document count. Repeat with --fail-on-error and confirm status 3 if a matching ERROR event exists. Record that status separately from standard output.

Next, simulate a malformed CSV header and confirm status 2 along with the deliberately sanitized INPUT_ERROR diagnostic. Restore the original fixture before the next task. Use a synthetic message containing punctuation that resembles shell syntax; verify it is treated as data. Never run destructive example commands, inspect unrelated directories or copy real customer logs into the course.

Describe why the input controls are necessary and why they still do not provide race-free directory confinement. A professional handoff needs exact steps and limitations, not a vague statement such as “the CLI works.” Document failed attempts, environment differences, and anything left untested.

## 6. Independent exit-code interpretation (LO2, LO3, LO4)

The [independent lab](lab-independent/README.md) starts with a deliberately incomplete learner program. It receives a list of records shaped status|label, where status is an integer in 0..255 and label names a fictional previously executed training command. Your function must validate inputs, refuse duplicates and suspicious labels, and summarize total, zero and nonzero outcomes without executing or replaying any command.

The student starter intentionally raises NotImplementedError. Initial test failures are expected and represent the work the learner has not yet completed. Implement the documented specification, run the published contracts, and investigate failing assertions. A separate hidden instructor review and evidence-based evaluation are required before awarding mastery credit.

This is an exercise in parsing and reporting an existing transcript; it is not an interpreter for shell commands, a remote agent, or a job scheduler. State those limitations in your submission. Explain why a status labeled “nonzero” is not automatically a security incident.

## 7. Troubleshooting and operational scope (LO1, LO2, LO3, LO4)

If the tool reports that the path is invalid, confirm your current directory, root argument and relative filename before changing anything. A symlink is not an ordinary file name under this lab's policy. If a timestamp fails validation, check for an explicit timezone offset. If the JSON output is missing, inspect both the exit status and standard error. Never suppress all errors simply to make a test green.

If a test cannot be executed because the host lacks the required runtime, record NOT_EXECUTED. If a learner starter fails because the requested function has not been implemented, treat that as a valid educational checkpoint rather than a passed lab. Never weaken the test to claim an outcome. If shell behavior differs across platforms, identify the exact shell and provide a reviewed alternative rather than inventing cross-platform verification.

Finally, submit an operations handoff including approved synthetic scope, tools and versions, exact commands, result count, process status, negative tests, and residual limitations. Complete the [eight-question knowledge check](assessment/quiz.md) and use the public rubric to prepare for independent review. FND-M02 alone does not complete Digital Foundations; FND-M03 through FND-M06 are still planned, and commercial and Academy release remain blocked pending the separate production acceptance gates.
