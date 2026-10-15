# FND-M04 guided lab — Real Git in a disposable local repository

**Classification:** Controlled-live local Git operations, NOT GitHub PR approval or enterprise release. **Est. time:** 75 minutes. **Prerequisites:** Git 2.28+ (`git init --initial-branch` support), Python 3.11+, a writable temporary directory. All content is synthetic.

## Step 1 — Prepare safe local Git context (LO1)

Record `git --version`, `python --version`, the exact working directory and your authorized lab scope. `solution/git_workflow.py::PracticeRepo` uses a temporary directory, commits only synthetic text and sets local training identities. It intentionally has no Git remote, network or customer access. Inspect how `subprocess.run` passes a Git argument list without invoking a shell. Do not copy this code into an automated production merge agent.

## Step 2 — Branch, stage, commit and inspect a proposed change (LO2)

Run the test suite from repository root:

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M04/lab-guided/checks -p test_git_workflow.py -v
```

Inspect the `reviewable_feature()` return value in a disposable run, or read the tests. It must contain distinct baseline/feature commit IDs, a feature branch named `feature/runbook`, one changed file `runbook.md`, and a reviewable diff. It should also show a two-parent `--no-ff` local merge and a clean working tree. The field `remote_review_observed` MUST remain false: no hosted reviewer took part.

## Step 3 — Create and resolve a real synthetic merge conflict (LO3)

The reference creates divergent edits in `settings.txt` on main and feature branches, asks Git to merge, checks a nonzero result and unmerged index entries, then writes the fictional resolution `MODE=reviewed` and finishes the merge. Explain why a conflict *must* be handled by an authorized decision-maker in a real organization. The resolution here is a predetermined teaching fixture, not a real production policy. Do not practice forced resets in a customer repository.

## Step 4 — Test security and cleanup boundaries (LO1, LO3)

Verify that the test suite rejects `../outside.txt`, `.gitconfig`, nested paths and oversized content; confirms no remotes; and verifies that the disposable directory was removed. Run the tests in an unprivileged user account. If the OS or Git version prevents execution, report `NOT_EXECUTED` and preserve the error, rather than claiming GitHub access or bypassing security controls.

## Step 5 — Operational handoff (LO4)

Submit a report recording Git version, Python version, commands, test pass/fail/skip counts, one real diff fragment, the observed nonzero conflict status, the resulting clean state, any environment limitations and a clear statement: "Local Git change observed; independent GitHub PR review NOT_VERIFIED." Avoid all real names, credentials and customer paths. The instructor must verify both the technical results and your reasoning against the public rubric.
