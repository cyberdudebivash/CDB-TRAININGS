# Python Engineering pathway: engineering handoff (2026-10-16)

For the repository owner and whoever continues this work. This page is hand-maintained and states what to trust, how to check it, and what nobody has done yet.
The figures that change live in the generated documents named below; none of them is a release statement. Gate A (`TRAINING_CONTENT_GO`) is the only gate this work addresses.
Commercial readiness and Academy publication are separate gates that were not implemented, and nothing was published, sold or deployed.

## 1. What exists

All thirteen modules of `COURSE-PY-ENG` are built under [`courses/python-engineering/modules/`](../../courses/python-engineering/modules/): PY-M01 to PY-M13, each with a lesson whose
`python run` blocks are executed, a guided lab, an independent lab, a quiz, a rubric, an outcome-to-assessment trace and a source map to the 2025 handbook.
PY-M10 (secure HTTP services) and PY-M11 (the capstone: a specified application, a release gate of thirteen gates, a hidden suite, a mutation check of the learner's own tests) were
added last. The 2025 handbook (654 pages) is preserved unchanged at the repository root; every page now has a recorded disposition in a built module's source map.
A disposition is a decision, not coverage: pages that belong to other courses (automation, security, DevOps, blockchain, AI, data engineering) are recorded as `DROPPED` with a named
destination that is itself unbuilt, and offensive tooling is not carried by any module.

## 2. Verify it yourself

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt -r courses/python-engineering/labs/requirements.txt
pytest tests --ignore=tests/test_python_engineering_labs.py        # structure, registers, Gate A, edition builds: minutes
python scripts/validation/run_lab_matrix.py --resume               # every lab and lesson on CPython 3.11-3.15 in fresh environments: hours; needs network for pip only
python scripts/validation/run_lab_matrix.py --resume --reuse-record  # after a change: only the pieces whose scope changed run again (minutes)
python scripts/validation/render_lab_evidence.py                   # docs/qa/LAB_EXECUTION_EVIDENCE.md from the recorded run
python scripts/validation/validate_gate_a.py                       # no status, review or scenario claims more than the evidence supports
python scripts/production/render_production_docs.py --check        # generated documents agree with the data
```

The lab matrix is the only thing that can raise a module above `IMPLEMENTED_UNVERIFIED`. It records, per interpreter and per test, the outcome, and a content fingerprint of every module
(lesson, labs, shared lab tools). Gate A treats a recorded run as stale when a fingerprint no longer matches, so any change to a lesson, a lab or the lab toolchain pins requires a new run.
`--resume` reuses interpreters that already passed in an interrupted run of identical content; nothing else is ever reused.

## 3. Instructor material

Answer keys, hidden suites, reference solutions, seeded-defect lists and sample answers are in `courses/python-engineering/instructor/PY-Mxx/`, which is **git-ignored**: it exists
only in the environment that built it until the owner moves it to a private repository (decision D8, open). The tests that need it report `SKIPPED_PRIVATE_MATERIALS` without it, which means
*not verified in that environment*, never passed. Do not copy any of it into a public place. The capstone's hidden suite and its list of seeded defects are secret by design: the check of a
learner's tests is meaningful only if the learner does not know which defects exist.

## 4. How the capstone is graded (PY-M11)

| Criterion | By | How |
|---|---|---|
| C1 release gate | script | `lab-guided/tools/gate.py` on the learner's project: thirteen gates, 13 of 13 |
| C2 behaviour | hidden suite | at least 85 percent of the checks and every safety check named in the private grading notes |
| C3 the learner's tests | mutation tool | the learner's tests pass on the reference and fail on at least 60 percent of the required seeded defects (the reference's own tests kill 80 percent) |
| C4, C5 | a reviewer | scored 0-3 on the public rubric; a sample answer to C4 is in the private pack |

The gate itself has a negative control for every gate (a damaged copy of the reference that must fail exactly that gate), fails on an empty project, and a walking skeleton passes only the gates of part A.

## 5. What is NOT done

- No subject-matter, editorial or learner review exists; no rubric, quiz item or lab has been piloted with a person. The adversarial reviews recorded in `docs/production/data/adversarial_reviews.yaml` were performed by the assistant, are labelled as such, and are not human review.
- The lab matrix ran on CPython 3.11 to 3.15 on Linux in fresh environments: 261 tests on each interpreter on the merged tree, of which seven lab pieces were carried from an earlier full run of identical scope (`--reuse-record`; listed in `docs/qa/LAB_EXECUTION_EVIDENCE.md`). One piece failed once on 3.13 in an earlier attempt after a container restart (cause probable, not proven; the mutation tests now run a surviving defect a second time). Run the matrix without `--reuse-record` after 2026-10-24.
- The October 24 technical refresh has not been executed (it cannot be before that date) and nothing here claims it.
- The complete-course PDF is a **preview** built from unreviewed content; a final edition needs the approved curriculum (Gate A criteria A17 to A19). Module previews and the course preview are build outputs in the git-ignored `dist/` folder, not published files.
- Source provenance and licensing (D4) are unresolved, and the privacy incident INC-001 (third-party personal data in a source file of another course, in the public tree and its history) is `OPEN_OWNER_ACTION`; no history was rewritten.
- Windows and macOS behaviour, a real CI runner, the existence of the pinned action SHAs that the capstone's workflow uses, and real vulnerability data (the capstone's advisories are synthetic) were not verified.
- The other nine courses are not built (Gate A reports them honestly: foundations two of six modules, SOC one of fourteen, the rest planned).

## 6. Decisions that need a person

1. D8: where the instructor material lives (a private repository), and who holds it.
2. D4: the licence and provenance of the source PDFs and of this derived content.
3. INC-001: whether and how the source file and its history are purged (needs the owner's explicit authorisation).
4. Who reviews: named subject-matter and editorial reviewers, a real learner pilot, and the owner's acceptance. They are recorded only by those people in `docs/production/data/human_reviews.yaml`.
