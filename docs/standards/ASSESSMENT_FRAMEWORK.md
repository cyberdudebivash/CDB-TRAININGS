# Assessment Framework

Reference implementation: `courses/soc-analyst/assessments/m04/` and `curriculum/outcomes.yaml`.

## 1. Principles

1. **Assess outcomes, not attendance.** Every module outcome is assessed by at least one item or lab criterion. `assessment_coverage` in the catalog tracks assessed vs total outcomes, and gate G3 requires all.
2. **Prefer performance over recall.** The strongest evidence is an artefact graded against data (a detection scored on labelled telemetry, a program that passes unit tests). Knowledge questions test reasoning, not memorisation of trivia.
3. **Published rubrics.** Learners see exactly how they are graded.
4. **Machine-check what can be machine-checked; reserve humans for judgement.** Rubric criteria are labelled `automated` or `reviewer`.
5. **Fail-closed and anti-gaming.** Metrics are paired so one cannot be maximised alone (recall with false-positive budget; suppression with "did it hide a real attack?").
6. **No secrets in a public repo.** Answer keys, reference solutions and grader notes live in the private instructor pack.
7. **Honest validity claims.** Until a learner pilot has been run, item difficulty and discrimination are unknown and are not asserted.

## 2. Assessment types

| Type | Purpose | Scoring | Where |
|---|---|---|---|
| Retrieval check | Practise recall inside the lesson | ungraded | lesson |
| Quiz | Check reasoning against outcomes | answer key and per-option rationales in the private instructor pack | `assessments/<m>/quiz.yaml` (stems, options, outcome tags; no answers) and `quiz.md` (student view) |
| Guided-lab checks | Confirm each step worked | automated | lab commands |
| Independent lab | Transfer the skill to new data | automated criteria + reviewer criteria | rubric |
| Capstone | Integrate skills | rubric with must-pass criteria | course capstone |

## 3. Item standards (quiz)

- Each item is tagged to an outcome (`quiz.yaml`), has a stem that can be answered from the lesson and the data, one unambiguously best answer, plausible distractors based on **real misconceptions** (recorded in the lesson), and a rationale for every option. The key and rationales are kept in the private instructor pack, never in `quiz.yaml`.
- No "all of the above", no negatives in stems unless emphasised, no trick wording.
- Items that depend on a version-sensitive fact cite the version in the stem.
- Reading level matches the lesson; items are readable by screen readers (no image-only content).
- The student view (`quiz.md`) is maintained by hand and `tests/pilot/test_curriculum.py` fails if any stem or option differs from `quiz.yaml` or if either file carries an answer field. Generating `quiz.md` from `quiz.yaml` is a possible later improvement.

## 4. Rubric standards

| Rule | Why |
|---|---|
| Criteria map to outcomes | Traceability |
| `kind: automated` criteria state the exact command and numeric threshold | Anyone can reproduce the score |
| `kind: reviewer` criteria have 4 observable level descriptors (0-3) | Reduces grader drift |
| `must_pass` criteria cannot be offset by other points | A learner cannot pass a detection lab while missing attacks |
| `pass_rule` states every condition | No hidden rules |
| Reviewer criteria include "honesty about limits" | Teaches calibrated claims |

## 5. Certification of completion

A completion record states: module and version, outcomes assessed, rubric result per criterion, date, and the tool versions. It does **not** state equivalence to any third-party certification, and it is not issued by this repository. Issuing credentials is an owner decision (`COURSE_PRODUCT_CATALOG.md`, section 5).

## 6. Validity plan (not yet performed)

| Step | Status |
|---|---|
| Automated consistency checks (outcome coverage, key/rationale shape, no answers in public files) | done — tests |
| Subject-matter review of every item | **not done** — gate G7 |
| Learner pilot: item difficulty, time on task, rubric agreement between two graders | **not done** |
| Revision of items with extreme difficulty or low discrimination | blocked on pilot |
| Re-baselining when tool/standard versions change | process defined; manual |

## 7. Academic-integrity design

- Independent labs use data different from the published guided data; a held-out seed can be used for formal assessment.
- Automated checks run on the learner's artefacts, not on screenshots.
- Reviewer criteria require a written rationale that cites evidence, which is hard to copy without understanding.
- This is deterrence, not proof. Proctored or live-defence formats remain optional for high-stakes use.

## 8. Accessibility of assessments

- Plain-text and PDF forms; no time limits are imposed by the repository tooling.
- Colour is never the only carrier of meaning; rubrics are tables with text labels.
- Instructors may extend time and substitute equivalent evidence formats; the framework records the substitution rather than lowering the standard.
