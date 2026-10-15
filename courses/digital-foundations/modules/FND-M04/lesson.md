---
id: FND-M04
title: "Git and GitHub workflow"
course: COURSE-FND-DIGITAL
level: 0
audience: "New technical learners, support engineers and junior developers"
prerequisites:
  - "FND-M01 paths and file permissions"
  - "FND-M02 command line"
  - "FND-M03 network and HTTP vocabulary helpful but not required for offline Git labs"
estimated_time_hours: {lesson: 1.5, guided_lab: 1.25, independent_lab: 1.25, total: 4.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {git: "Git 2.47.3 in authoring Linux environment; concepts cross-version, platform matrix pending", python: "Python 3.11+ standard library; local Python 3.13.5"}
last_verified: 2026-10-16
---

# FND-M04 — Git and GitHub workflow

## Measurable outcomes

| ID | Learner must demonstrate |
|---|---|
| **LO1** | Differentiate a working tree, staging area, commit, branch, local Git repository, remote and hosted pull request. |
| **LO2** | Create and review a synthetic feature change in an isolated repository, collecting correct diff, commit, and branch evidence. |
| **LO3** | Diagnose and resolve a deliberate merge conflict without discarding unrelated work or assuming the merge is reviewed. |
| **LO4** | Apply a fail-closed review-readiness checklist and write a truthful handoff that distinguishes local Git results from remote GitHub approval. |

**Training boundary:** The guided lab runs genuine Git commands, but only inside Python-managed temporary directories. There are no clones, network requests, pushes, customer repositories, real credentials, or hosted GitHub pull requests. A passing local lab proves a particular learning exercise ran successfully; it does *not* establish that an independent code reviewer approved a production change.

## 1. Why version control matters (LO1)

In an operational team, a configuration change or a support runbook can alter how employees handle an outage. Without version control, another engineer may not know what changed, why a line was removed, or which version was last reviewed. Git records snapshots of project contents as commits and links them into a history; it does not, by itself, validate security, correctness or business approval. A commit is evidence of recorded content and metadata, not proof a change was authorized.

A **working tree** is the set of files that you edit. Git's **index**, often called the staging area, records which content is proposed for the next commit. A **commit** identifies a recorded snapshot and its parent history. A **branch** is a movable reference to a commit. A **remote** is a named connection to another repository. GitHub is a separate hosting and collaboration service that can receive pushed Git data and offer review and pull-request workflows. You can learn all local Git concepts with no GitHub account or internet connection.

The distinction matters when reporting work. “I created a local feature branch and merged it into local main” does **not** mean “a GitHub pull request was approved and merged.” Even if the commit graph is identical, a reviewer, branch-protection rule, CI result, and repository permissions exist outside that local graph. Claim only what your evidence verifies. Git history records edits, but secrets committed even briefly can persist in repository history. Never put tokens, customer names, passwords or private case details into practice commits.

### Worktree, staging and commit as distinct states

A file may have unstaged changes, staged changes, or both. Running `git status --short` helps identify those states. The command is observational. `git diff` inspects unstaged content differences; `git diff --cached` inspects staged changes. Before committing, review the diff for unintentional files. Avoid blanket additions of directories when your workspace contains downloads or local credentials. Our guided lab deliberately stages only an exact safe filename.

```python run
stages = ('working-tree', 'index', 'commit')
assert stages.index('index') > stages.index('working-tree')
assert len(stages) == 3
```

A Git object ID is commonly displayed as a hexadecimal digest. Never assume the full value can always be represented by an arbitrary short prefix. The guided lab captures full commit IDs and verifies their shape. Current Git supports different object-hash algorithms depending on repository initialization; this particular training environment uses the familiar 40-character SHA-1 repository format. SHA-1 Git object IDs in a repository should not be confused with cryptographically trusted integrity signatures or independent review approval.

## 2. Make a branch and review a change (LO2)

Start with an authorized practice directory. A typical controlled sequence is to initialize a repository, provide a **repository-local** training identity, add a safe README, and commit a baseline. Next create a feature branch, edit a runbook, stage the intended file, commit that change, and compare feature with main. Our wrapper issues direct Git argument arrays with `subprocess.run(..., shell=False)` rather than interpolating learner strings into a shell. The runtime uses local Git identity settings, never global credential configuration, and does not configure a remote.

Many Git tutorials show a single list of terminal commands. A professional reviewer also needs observable acceptance evidence: what file changed, why, which commit captured it, what tests ran, and whether reviewers approved. In a local lab you can prove the first items. You cannot honestly prove independent GitHub approval without consulting GitHub and recording actual review events. Report remote state as NOT_VERIFIED rather than inventing a pull-request number.

The feature exercise records `baseline_sha`, `feature_sha`, `feature_branch`, `changed_files`, and `reviewable_diff`. The diff between main and the feature branch shows the proposed runbook content. When merging locally with `--no-ff`, Git writes a merge commit with two parent references. That is a useful observable record in this lab, but different teams may prefer squash or rebase strategies. Treat the exercise as one valid workflow example, not the only recommended release practice.

```python run
changed_files = ['runbook.md']
assert changed_files == sorted(set(changed_files))
assert all('/' not in path for path in changed_files)
```

Use explicit file paths and project-scoped operations. Some Git commands, including reset, clean and forced history rewrites, can discard work. They are intentionally excluded from this beginner exercise. A team must document when destructive operations are authorized, how working changes are backed up, and whether a protected branch forbids direct changes. There is no instruction here to force-push, bypass branch protection, or modify an actual organization repository.

### GitHub pull requests are not Git commands

After a feature is pushed to a remote under appropriate authorization, a hosted pull request may gather code-review comments, test results, and approval decisions. This module explains the concept but does not create an actual GitHub PR. A complete enterprise workflow would also include ownership rules, code-quality review, CI, secret scanning, dependency checks, and merge permissions. **Do not count a local merge commit as a PR approval.** The distinction is a core assessed learning outcome.

## 3. Merge conflicts are normal and require decisions (LO3)

Two branches can modify the same part of the same file differently. Git may be unable to determine the intended result. It stops a merge and reports a conflict so that a person can choose the final content. This is not necessarily a bug in Git. Automatic resolution would risk silently picking the wrong requirement. An engineer should record both alternatives, seek the relevant business owner if necessary, and complete a reviewed resolution. A conflict marker indicates unresolved content; it must not be committed blindly as the final answer.

Our synthetic lab creates `settings.txt` with `MODE=default`, then makes two incompatible modifications in independent branches. On main the value becomes `MODE=production-example`; on feature it becomes `MODE=training`. Git produces a conflict and places markers in the working file. The lab verifies that the merge exited nonzero and that the index has unmerged entries using `git ls-files -u`. It then *explicitly selects the fictional training resolution* `MODE=reviewed`, stages it, commits, and verifies that the index and working tree are clean. In a real customer repository, choosing a winning setting requires approval by the actual service owner, not an arbitrary tutorial convention.

```python run
alternatives = {'main': 'MODE=production-example', 'feature': 'MODE=training'}
assert alternatives['main'] != alternatives['feature']
# This is a teaching decision, not real production config approval.
resolved = 'MODE=reviewed'
assert resolved not in alternatives.values()
```

The official Git merge documentation explains why an unresolved merge stops and describes both conflict resolution and abort behavior. Although Git offers commands to abort an interrupted merge, a user should first understand whether uncommitted work existed and which state would be restored. Our lab starts with a clean synthetic working tree; it does not instruct learners to run merge abort or reset against real projects. You should be able to explain what the conflict output proves, and what it does not prove: an actual local content disagreement was observed, while the correctness of the selected resolution depends on external requirements.

### Testing the resulting history

A clean working tree is necessary for many operational handoffs, but not sufficient for release. A clean tree may contain a fully committed defect. Likewise, a merge with two parents proves a graph relationship, not that tests passed. These are distinct evidence dimensions. In the exercise, a unit test reads the resulting content and asserts that conflict artifacts have been removed. A more realistic repository would additionally test service behavior, security, compatibility and deployment rollback.

## 4. Review gates should fail closed (LO4)

A pull-request review checklist usually contains more than a green build. The review must identify what changed, what tests ran, what still failed, whether a qualified person approved it, and whether conflicts remain. “Reviewed by other” is a *human-supplied claim* in our synthetic independent exercise; the local parser cannot establish that real review occurred. As a training simulation, it can still teach how an approval flag, test result, and changed-file list influence an evidence-based decision.

The independent learner exercise takes a dictionary with **exactly** six fields: `base_sha`, `head_sha`, `changed_files`, `checks_passed`, `reviewed_by_other`, and `conflicts_remaining`. The SHA values must be 40 lowercase hexadecimal characters as defined by this *teaching fixture*. Changed paths must be relative safe filenames, without directory traversal, duplicates, `.git` internals or absolute paths. Boolean flags must genuinely be `bool`, not integer stand-ins. Reject malformed evidence rather than guessing what the creator intended.

The result has `ready: bool` and `reasons: list[str]`. A missing diff yields `no-diff`; failed checks yield `checks-failed`; missing review yields `review-missing`; an unresolved conflict yields `conflicts-open`. These reasons have a fixed order so consumers can compare outcomes deterministically. A structurally malformed input yields only `invalid-evidence`. The example below shows the intended *shape*, not a real review decision:

```python run
example = {'ready': False, 'reasons': ['checks-failed', 'review-missing']}
assert not example['ready']
assert example['reasons'][0] == 'checks-failed'
```

This is a simplified readiness exercise, not a GitHub Apps permission system, a merge-bot, or a substitute for branch protection. In actual delivery, checks and approvals must be queried from their authoritative source, signatures and identities verified where necessary, and state rechecked at the merge point. This lab uses fabricated commit strings; it must never say that a real organization change was approved.

## 5. Guided operational lab (LO1, LO2, LO3)

Read [the guided lab](lab-guided/README.md) and run its public tests. You will see a Git repository created in a temporary local directory, a baseline commit, a feature branch and reviewable diff, a normal local merge, and a separate deliberately conflicting merge. Record actual Git version, Python version and whether the tests pass. Verify that the wrapper never configures a remote and that the directory disappears after the context manager closes. Do not rewrite the wrapper to accept arbitrary remote URLs, user-supplied Git commands or actual customer paths.

Capture an operations note with three separate facts: (1) local commit and diff evidence, (2) conflict detection and documented resolution, and (3) remote/PR review explicitly marked NOT_VERIFIED. Re-run the contract after a deliberately isolated, reversible change to demonstrate that a test detects a regression. Prefer changing assertions in a temporary learner copy rather than corrupting the shared source.

## 6. Independent simulated review assignment (LO4)

Complete the [independent review-check exercise](lab-independent/README.md). Its starter raises an instructional exception until you implement a strict validator. The shipped public tests intentionally fail at first; failing tests with clear guidance are part of the teaching sequence, not a product defect. After your solution passes those contracts, consider one edge case not included in the public suite and document how you would test it. The instructor still needs to review your algorithm for bypass cases; do not present a green public suite as independent mastery proof.

The readiness result must list all applicable blockers in a fixed order and must not quietly coerce malformed booleans or SHA values. This exercise is especially important for junior engineers who might be tempted to interpret GitGuardian or a passing test suite as proof that a feature is fully production-safe. Technical tests, human approval, infrastructure availability and customer-release authorization are separate gates.

## 7. Professional handoff and troubleshooting (LO1–LO4)

If Git is missing from PATH, the guided lab raises a clear environment blocker. If local commits fail, inspect the repository-specific training identity and working-directory state; do not modify global credentials. If a merge conflict does not appear, confirm both branches changed the same line after their shared baseline and that the local working tree was clean. If the student independent tests fail with `FND-M04 STARTER INCOMPLETE`, implement the function rather than relaxing the expected output.

A complete handoff identifies the authorized practice scope, the sandbox lifecycle, precise Git and Python versions, commands, observed status and commit shapes, merge-conflict evidence, test counts, unverified network/remote activity, and residual risk. Include a short reflection on how local Git evidence differs from a genuine hosted PR. Avoid submitting personal email addresses, customer repository locations, secrets or third-party records. Only the synthetic `learner@example.invalid` identity is used by the reference.

## 8. Assessment and further reading (LO1–LO4)

Complete the eight-question [knowledge check](assessment/quiz.md), the real local Git exercise, and the independent review-evidence validator. The rubric requires both automated contracts and meaningful human evaluation of branch/review reasoning. Instructor solutions are not included in the public repository. A full course also requires the remaining FND-M05/FND-M06 modules, coordinated capstone, technical/editorial review, learner pilot, accessibility and complete PDF publication checks.

Authoritative documentation (review dates must be tracked separately from retrieved content): [Git user manual](https://git-scm.com/docs/user-manual), [Git configuration](https://git-scm.com/docs/git-config), [Git merge](https://git-scm.com/docs/git-merge), and [Git switch](https://git-scm.com/docs/git-switch). Git itself is cross-platform, but these local tests have only been executed in the stated development environment. No live GitHub PR operations, authenticated pushes, enterprise CI, or customer approvals were tested in this module.
