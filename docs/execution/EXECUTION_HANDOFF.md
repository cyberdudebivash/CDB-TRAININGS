# Execution Handoff

For the repository owner and whoever continues this work. Read this first; it tells you what to trust, what to do next, and how to verify everything yourself.

## 1. What you have

| Area | State | Where |
|---|---|---|
| Source preservation | All 10 PDFs unchanged; hashes recorded and tested | repository root, `docs/audits/data/source_inventory.json` |
| Audit | 65 findings, scores, per-course audits, gap matrix, provenance, missing-materials, IP review | `docs/audits/` |
| Verified facts | 23 primary-source entries with dates and verification method | `docs/research/` |
| Curriculum | 10 courses, 102 modules, 11 pathways in one validated catalog | `catalog/`, `docs/curriculum/` |
| Standards | Lab, assessment and design standards | `docs/standards/` |
| Pilot | SOC-M04: lesson, guided + independent labs, quiz, rubric, student edition, automated checks | `courses/soc-analyst/`, `tests/pilot/` |
| Release control | Six release states, eight gates, generated gate report | `docs/release/` |
| Commercial | Product and bundle hypotheses, readiness verdict (not ready), claims policy | `docs/commercial/` |

**Not production-ready:** nothing. `PRODUCTION_GO` count is 0 and the validator refuses to let you set it by hand without evidence.

## 2. Verify it yourself (10 minutes)

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
pytest                                              # tests; private-pack tests skip if you lack the pack
python scripts/validation/run_qa.py --skip-build    # regenerates the QA + gate reports
python scripts/validation/validate_catalog.py
python scripts/build/render_program_docs.py --check
```

To try the pilot as a learner, follow `courses/soc-analyst/labs/m04-guided/README.md`. To see the student PDF, run `python scripts/build/build_student_edition.py --strict` (needs pandoc, poppler-utils, Chromium); output goes to the git-ignored `dist/`.

## 3. Decisions only you can make

| ID | Decision | Urgency | Why it cannot be automated |
|---|---|---|---|
| **D1** | Third-party personal data (name, e-mail, phone, city) sits on pp. 357 and 360 of the **public** Frontend PDF. Confirm consent or remove the pages/file. Purging Git history is a repository-owner action. | **Immediate** | Privacy exposure is live; this work deliberately did not touch the original file |
| D4 | Name the copyright holder and choose licences; add `LICENSE` (see `LICENSE-STATUS.md`) | High | Legal ownership |
| D3 | Legal review of redistributing GPL OSINT tools under a proprietary licence | High | Legal |
| D2 | Origin and confidentiality of the "INTERNAL" Frontend playbook | High | Only you know |
| D8 | Create a **private** repository for instructor packs | Medium | Answer keys must not live in a public repo |
| D5 | Name qualified SME reviewers per course | Medium | Gate G7 |
| D6 | Academy platform, payment and delivery stack | Medium | Needed before any fulfilment work |
| D7 | Any budget for paid cloud/API usage (currently zero; all labs run locally) | Low | Spending authority |

## 4. The instructor pack

The quiz answer key, the independent-lab reference solution and grading notes are **not in Git**. They were generated locally and sent to you as a separate file at the end of the session. Please:

1. Put them in a private repository (D8) at `courses/soc-analyst/instructor/`.
2. Do not copy them into the public repository; `.gitignore` and `tests/test_repo_hygiene.py` will refuse it.
3. If you lose the pack, the lab data is deterministic and the public guided solution (`labs/m04-guided/solution/`) is a starting point, but the independent-lab reference solution, the quiz key and the grading notes would have to be re-authored and re-verified.

## 5. Known limits you should not paper over

- No SME has reviewed anything; no learner has used anything.
- The audit is a structured sample, not a line-by-line read (Mega Course confidence LOW).
- Synthetic labs simplify real telemetry. The lesson says so; do not market the labs as "real-world" data.
- `sigma_lite` is a teaching evaluator for a documented Sigma subset; it is not a SIEM and not a replacement for pySigma or a vendor backend.
- Time estimates are authoring budgets, not measured learner times.
- Golden dataset hashes depend on CPython 3.13.
- The manual validation workflow pins actions by major tag, not commit SHA.

## 6. Backlog (suggested order)

| # | Work | Why now |
|---|---|---|
| 1 | Resolve D1, D4, D8 | Risk and prerequisites for everything else |
| 2 | SME review of SOC-M04 and the 23 research entries it relies on | Turns the pilot into a reviewed reference |
| 3 | Learner pilot of SOC-M04 | Measures time, difficulty, rubric agreement |
| 4 | SOC-M01..M03 | Completes the on-ramp for the pilot course; reuses generator and evaluator |
| 5 | Level-0 foundations (FND-M01..M06) | Prerequisite of every pathway |
| 6 | PY-M01..M05, then Python Automation | Highest reuse |
| 7 | AI Engineering (free local model labs) | Large source defects F-AI-001..004 to remediate |
| 8 | GCP, Java QA, Frontend, OSINT, CYBER tracks | Each needs its own lab environment decisions |
| 9 | Generate website/marketplace listings from the catalog | Only after a course reaches `PRODUCTION_GO` and the owner authorises |

For each module follow the unit contract in `MASTER_CURRICULUM_BLUEPRINT.md` section 4 and the checklist in `PRACTICAL_LAB_STANDARDS.md` section 9.

## 7. Operating constraints observed

No force-push or history rewrite on pushed branches; work stayed on `claude/cyberdudebivash-training-audit-ilfgze`; the pull request is a **draft** and not merged; no pricing, publication, deployment or financial action; no paid service; no production Academy service touched; no claim of human review; offensive content only as synthetic, isolated detection exercises.

## 8. If something fails

| Symptom | Likely cause | Action |
|---|---|---|
| `test_generator` golden-hash test skipped | Python is not 3.13 | Use 3.13, or re-baseline after reading the failure message |
| Tests report `SKIPPED_PRIVATE_MATERIALS` | Instructor pack absent | Expected on a public clone |
| `render_program_docs.py --check` fails | Catalog changed but documents not regenerated | Run it without `--check` and commit |
| `validate_catalog.py` rejects an edit | A gate or cross-reference would be violated | Read the message; it names the rule |
| Student build fails on forbidden marker | Instructor text leaked into a student file | Remove the leak; do not weaken the gate |
