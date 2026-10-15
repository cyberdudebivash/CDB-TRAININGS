# FND-M02 guided lab — Safe local diagnostic CLI

**Status:** Executable teaching reference; not a completed module or commercial training. **Time:** approximately 90 minutes. **Runtime:** Python 3.11+ stdlib. All fixtures are synthetic.

## Customer-operations use case

A fictional support team must inspect a local CSV of application events, select only warning/error records, and correctly interpret a script's stdout, stderr and exit code. The task is deliberately read-only. Do not use real customer logs, credentials or production servers.

## Step 1 — Establish the authorized practice environment (LO1)

Open an ordinary (non-administrator) terminal in a disposable checkout. Record your operating system, shell and Python version. On Linux use `pwd`; in PowerShell use `Get-Location`. Create your own temporary practice directory. Commands must not modify shared or protected directories.

## Step 2 — Create synthetic input (LO1, LO4)

Create `events.csv` in the disposable practice directory:

```csv
timestamp,service,severity,message
2026-10-15T10:00:00+00:00,auth,INFO,Started
2026-10-15T10:01:00+00:00,auth,ERROR,Timeout
```

Use UTF-8. Keep the file under 65,536 bytes. The header must contain these exact four columns. No real identities or live customer events are needed.

## Step 3 — Run the published reference tests (LO2, LO4)

From repository root:

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M02/lab-guided/checks -p test_runbook.py -v
```

The existing reference suite should run **14 tests**. Record actual pass/fail/skip results. Skipped symlink tests on an unsupported host must never be called passed.

## Step 4 — Execute the CLI (LO2, LO3, LO4)

Replace `PRACTICE_DIRECTORY` with the directory you created:

```text
python courses/digital-foundations/modules/FND-M02/lab-guided/solution/runbook.py --root PRACTICE_DIRECTORY --input events.csv --min-severity WARN --fail-on-error
```

Expected: JSON containing one filtered ERROR record, with return code **3** to indicate the *synthetic alert policy*. Without `--fail-on-error`, valid input yields status **0**. A deliberately malformed CSV should yield code **2** and a short diagnostic on standard error. Inspect `$LASTEXITCODE` in PowerShell or `$?` immediately afterward in Bash/Zsh.

The tool never invokes a shell to execute CSV text. Demonstrate that a message containing semicolons remains data. Do not test by executing harmful commands.

## Step 5 — Professional handoff (LO4)

Report exact commands and the observed status, Python and OS versions, dataset provenance, counts, and relevant operational limits. The path validation is not a race-free filesystem sandbox; this tool does not inspect genuine SOC telemetry, control an identity provider or prove an incident occurred.

Clean up only your synthetic practice directory. Passing the reference checks is formative evidence, not customer release approval or a completion certificate.
