# Commercial Readiness Assessment

Scope: what stands between the current repository state and a defensible commercial release, and which commercial assumptions are still untested. This is an engineering readiness assessment, **not** market research and not a forecast. No pricing, revenue, conversion or demand numbers appear because none were measured.

Evidence base: `docs/audits/COURSE_QUALITY_SCORECARD.md`, `docs/release/PRODUCTION_GO_GATE_REPORT.md`, `docs/audits/IP_AND_LICENSE_REVIEW.md`.

## 1. Verdict

**Not commercially ready. No course may be sold, listed or advertised from the current state.**

Portfolio totals (generated from `catalog/courses.yaml`):

<!-- BEGIN GENERATED: totals -->
| Measure | Value |
|---|---:|
| Courses | 10 |
| Modules planned / with built content | 111 / 8 |
| Labs planned / built / verified executable in QA | 213 / 16 / 16 |
| Module outcomes total / assessed | 116 / 13 |
| Courses with SME review recorded | 0 |
| Courses with a named owner | 0 |
| Courses by release status | REENGINEERING: 10 |
<!-- END GENERATED: totals -->

| Dimension | State | Evidence |
|---|---|---|
| Content quality | Legacy sources scored 10-46/100 as received; replacement content exists only for the pilot module | Scorecard; totals above |
| Technical verification | Pilot-module claims checked against primary sources; every other module unverified | `research_register.yaml` |
| Labs | Only the two pilot labs are built and verified in automated QA | totals above |
| Assessment | Only the pilot module's outcomes are assessed | totals above |
| Human review | None recorded | `review_status` |
| Licensing | Unresolved; repository has no `LICENSE`; one source proposes relicensing GPL tools | `IP_AND_LICENSE_REVIEW.md` |
| Privacy | Third-party personal data present in a public source PDF (F-FE-001) | findings register |
| Learner evidence | No learner has used any content | — |
| Operations (hosting, payments, support, analytics) | Not built; out of scope without authorisation | — |

## 2. What is a real asset

- A **reproducible audit pipeline** and findings register that prevent repeating the legacy defects.
- A **catalog with enforced gates**, so a course cannot be marked releasable by editing one field.
- A **lab engine pattern** (deterministic synthetic data, ground truth, fail-closed evaluator, triage checker) that makes labs automatically gradable at zero marginal cost.
- An **accessible, tested build pipeline** for student editions (tagged PDF with outline, contrast-checked tokens).
- A **private-pack pattern** protecting answer keys in a public repository, enforced by tests.

## 3. Commercial hypotheses (to test, not assume)

| # | Hypothesis | How to test cheaply | Disconfirming result |
|---|---|---|---|
| H1 | Learners and teams pay more for *assessed, automatically checked* labs than for page-count-heavy PDFs | Show the SOC-M04 sample to 10-20 target learners/team leads; ask what they would substitute it for; record verbatim | Most see no difference from a free tutorial |
| H2 | A free Level-0 course increases conversion to paid courses | A/B on the existing site with an owner-approved free module | No difference in downstream enrolment |
| H3 | Role pathways convert better than single courses | Offer the SOC pathway page with and without the pathway framing | Pathway framing performs worse or equal |
| H4 | Teams want cohort reporting and a facilitation guide | Interview 5 training managers | No demand for reporting |
| H5 | Verifiable work-sample credentials are more valued than completion certificates | Ask employers/hiring managers what evidence they trust | They disregard learner portfolios |
| H6 | AI-engineering and AI-security content has the strongest demand | Search-interest and email-list signals (owner data) | Weak signal against other topics |

No hypothesis is accepted. The order of the build plan in `MASTER_CURRICULUM_BLUEPRINT.md` is a technical-dependency order, not a revenue ranking.

## 4. Required before any commercial release

Blocking (from the gate report): licence decisions, SME review, remaining labs and assessments, removal of personal data from the source file, a learner pilot, and a named owner.

Additionally, outside the engineering scope and **not done**: payment and refund terms, privacy notice for learner data, terms of use for labs (authorised-use language for security content), accessibility statement, support process, and ecosystem integration (website, marketplace listing, analytics). These need explicit owner authorisation because they touch production services and money.

## 5. Claims policy for marketing

Allowed after release: what is assessed, which versions are covered and when they were verified, what the learner will build, hours as *estimated* until measured.

Not allowed without cited, dated, reproducible evidence: employment or salary outcomes, "job-ready", rankings, "No. 1", certification-pass rates, comparisons with named competitors, testimonials not obtained from real learners with permission, and statistics from the legacy PDFs (many were uncited; see F-SOC-005, F-MEGA-003, F-OSINT-005).

## 6. Measurement plan (once a pilot exists)

| Metric | Why | Source |
|---|---|---|
| Lab completion rate and median time per lab | Replaces estimated hours with measured hours | automated lab checks |
| First-attempt pass rate per outcome | Detects mis-calibrated rubrics | assessment results |
| Support questions per module | Finds unclear instructions | support log |
| Reported defects per module per month | Content health | issue tracker |
| Net promoter-style feedback with free text | Qualitative signal | learner survey |

Collect only what is necessary; document retention and consent before collecting anything.

## 7. Ecosystem integration (design intent, not implemented)

The catalog is the single source of truth. A future generator could produce marketplace listings, website course pages and structured data from `catalog/courses.yaml`, so listings never drift from reality. That generator must read `release_status` and refuse to emit a listing for any course that is not `PRODUCTION_GO`. It is not built, and no external service has been contacted or modified.
