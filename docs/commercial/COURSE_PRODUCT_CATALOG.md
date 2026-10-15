# Course Product Catalog (hypotheses)

> **Nothing here is an offer.** This is a structured set of product *hypotheses* derived from `catalog/courses.yaml` and `catalog/learning-pathways.yaml`. No price, discount, launch date, listing or marketing claim is set, and none may be published from this repository. Pricing and publication are owner decisions (see `docs/release/RELEASE_GATES.md`).

Generated regions are rendered by `scripts/build/render_program_docs.py`.

## 1. Product model

| Unit | Definition | Why |
|---|---|---|
| **Module** | Smallest deliverable with a lesson, guided and independent lab, assessment and artefact. Not sold alone by default. | The unit that can be built, tested and versioned. |
| **Course** | A sequence of modules with a capstone. The primary candidate product. | Matches how the legacy sources were organised, so existing audience expectations carry over. |
| **Pathway bundle** | Courses and selected modules in dependency order. | Reflects how learners actually pursue a role; avoids paying twice for shared foundations. |
| **Team edition** | A course plus cohort reporting, private-pack access for instructors, and a facilitation guide. | Enterprise hypothesis; requires a hosted component that does not exist yet. |

Editions that could exist technically *today* from this repository are limited to the SOC-M04 student-edition PDF (built by `scripts/build/build_student_edition.py`). It is a pilot sample and is **not** release-approved (G1, G7 open).

## 2. Course-level product candidates

<!-- BEGIN GENERATED: products -->
| Candidate product | Based on | Format hypothesis | Content ready | Blocking Gate A criteria | Price |
|---|---|---|---|---|---|
| Digital and Technical Foundations | new | self-paced entry course (free or low-friction entry is a hypothesis to test) | 4/12 labs built | SME and editorial review (A17), labs (A06), assessments (A07) | NOT SET (owner decision) |
| SOC Analyst Professional Pathway | `SRC-SOC-PLAYBOOK` | self-paced course with automated lab checks | 1 module built (SOC-M04); 2/27 labs built | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Python Engineering Pathway | `SRC-PY-HANDBOOK` | self-paced course with automated lab checks | 25/25 labs built | rights and licence (A11), SME and editorial review (A17), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Python Automation Pathway | `SRC-PY-AUTOMATION` | self-paced course with automated lab checks | plan only (no learner content built) | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Java Test Automation Engineer Pathway | `SRC-JAVA-AUTOTEST` | self-paced course with automated lab checks | plan only (no learner content built) | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Applied AI and LLM Engineering Pathway | `SRC-AI-BUNDLE` | self-paced course with automated lab checks | plan only (no learner content built) | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Lawful OSINT Investigation Pathway | `SRC-OSINT-STARTER` | self-paced course with automated lab checks | plan only (no learner content built) | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Google Cloud Data Engineering Pathway | `SRC-GCP-DATAENG` | self-paced course with automated lab checks | plan only (no learner content built) | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Frontend Engineering Onboarding Pathway | `SRC-FRONTEND-ONBOARD` | self-paced course with automated lab checks | plan only (no learner content built) | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
| Cybersecurity Specialist Tracks (from the Mega Course) | `SRC-MEGA-P1`, `SRC-MEGA-P2` | self-paced course with automated lab checks | plan only (no learner content built) | rights and licence (A11), SME and editorial review (A17), labs (A06), assessments (A07), open P0/P1 defects (A16) | NOT SET (owner decision) |
<!-- END GENERATED: products -->

"Blocking Gate A criteria" lists the mandatory content criteria that are not met for that course (a summary, not the full list); see `docs/production/TRAINING_CONTENT_GO_REPORT.md` for every criterion and its evidence. Gate B (commercial) is not assessed in this phase.

## 3. Bundle candidates

<!-- BEGIN GENERATED: pathway-products -->
| Candidate bundle | Pathway | Modules | Planning hours | Status |
|---|---|---:|---:|---|
| SOC analyst pathway | `PATH-SOC-ANALYST` | 22 | 156 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Detection engineer pathway | `PATH-DETECTION-ENGINEER` | 18 | 132 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Python engineer pathway | `PATH-PYTHON-ENGINEER` | 19 | 144 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Automation engineer (Python) pathway | `PATH-AUTOMATION-ENGINEER` | 26 | 187 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Test automation engineer (Java) pathway | `PATH-TEST-AUTOMATION-JAVA` | 16 | 124 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Applied AI / LLM engineer pathway | `PATH-AI-ENGINEER` | 31 | 258 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| AI security practitioner pathway | `PATH-AI-SECURITY` | 19 | 148 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Data engineer (Google Cloud) pathway | `PATH-DATA-ENGINEER-GCP` | 22 | 168 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Frontend engineer pathway | `PATH-FRONTEND-ENGINEER` | 17 | 124 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Lawful OSINT analyst pathway | `PATH-OSINT-ANALYST` | 18 | 98 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
| Cybersecurity generalist pathway | `PATH-SECURITY-GENERALIST` | 20 | 220 | HYPOTHESIS — not buildable until its courses leave REENGINEERING |
<!-- END GENERATED: pathway-products -->

## 4. Packaging principles

1. **Value is what the learner can demonstrate**, not hours or page counts. Product pages should lead with the capstone artefact and the automated checks.
2. **Free, local-first labs.** The learner never needs a paid cloud account to complete a core lab. Optional cloud labs are labelled with cost estimate, opt-in and teardown.
3. **No unsupported claims.** No "job-ready", "guaranteed", ranking, salary or certification-pass statements. State instead what is assessed and how.
4. **Version visibility.** Each product shows the versions of tools and standards it targets and the date they were last verified.
5. **Instructor material stays private.** Answer keys and reference solutions are delivered to verified instructors only; the public repository never contains them.
6. **Accessible by default.** The student edition is a tagged PDF plus HTML, built with the design system; see `docs/standards/DESIGN_SYSTEM.md`.

## 5. Open commercial decisions (owner)

| Decision | Options to evaluate | Needed before |
|---|---|---|
| Licence for original content | Proprietary all-rights-reserved, source-available, or CC-BY-NC-SA for selected samples | any publication (G1) |
| Free sample | A single module as a lead magnet versus none | marketing |
| Price model | One-time, subscription, team licence, or free-core/paid-certification-of-work | any listing |
| Credential | Verifiable completion record based on assessed artefacts; **no** equivalence claims to third-party certifications | credential design |
| Distribution | Existing marketplace listings, own site, or both | listing |
| Support | Community forum, office hours, or none | launch |

Each decision is a prerequisite for something the repository cannot do on its own; none is assumed.
