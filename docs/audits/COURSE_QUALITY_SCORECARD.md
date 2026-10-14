# Course Quality Scorecard

> Generated from `docs/audits/data/scores.yaml` and `findings.yaml`. Scores describe the **source PDFs as received** (baseline commit `f2ba7d0`).

## How to read this

- The score is an **internal quality-management instrument**, not proof of market rank and not a release decision. Passing a numeric threshold never overrides a failed mandatory gate.
- Scoring uses the eight dimensions and weights in the mission directive. Length, polish and visual style earn **no** points; evidence (executed code, primary-source checks, assessed outcomes) does.
- Anchors per dimension: 0-20% absent/dangerous/unusable; 21-40% material present but major defects; 41-60% partly usable with several significant defects; 61-80% mostly sound with fixable gaps; 81-100% verified sound with evidence of validation.
- **Confidence** states how much of the source a human actually read. `LOW` scores can move materially after fuller review.
- Unresolved defects are never hidden inside the aggregate: the open-finding columns below are authoritative for release decisions.
- Premium release target: 95 / 100 **and** every mandatory gate. No source scores above 50.

## Summary

| Course | Source as received | Score / 100 | Confidence | P0 | P1 | P2 | P3-P4 | Release status |
|---|---|---:|---|---:|---:|---:|---:|---|
| CYBERDUDEBIVASH Python Automation Training (`COURSE-PY-AUTO`) | `SRC-PY-AUTOMATION` | **46** | MEDIUM | 0 | 3 | 3 | 0 | `REENGINEERING` |
| SOC Analyst Survival Playbook (2026 Edition) (`COURSE-SOC`) | `SRC-SOC-PLAYBOOK` | **37** | HIGH | 0 | 5 | 4 | 3 | `REENGINEERING` |
| CyberDudeBivash Python Engineering Handbook (`COURSE-PY-ENG`) | `SRC-PY-HANDBOOK` | **36** | MEDIUM | 1 | 3 | 3 | 0 | `REENGINEERING` |
| Complete AI Training Bundle 2026 (`COURSE-AI-ENG`) | `SRC-AI-BUNDLE` | **33** | MEDIUM | 0 | 4 | 3 | 1 | `REENGINEERING` |
| Internal Frontend Developer Onboarding Playbook (`COURSE-FE-ONBOARD`) | `SRC-FRONTEND-ONBOARD` | **30** | MEDIUM | 1 | 2 | 1 | 1 | `REENGINEERING` |
| Java Automation Test Engineer - Real Time Job Training (`COURSE-JAVA-QA`) | `SRC-JAVA-AUTOTEST` | **29** | MEDIUM | 0 | 3 | 2 | 0 | `REENGINEERING` |
| GCP Data Engineer Training (`COURSE-GCP-DE`) | `SRC-GCP-DATAENG` | **29** | MEDIUM | 0 | 3 | 2 | 0 | `REENGINEERING` |
| Official CyberDudeBivash Mega Course 2026 (Parts 1 and 2) (`COURSE-CYBER-MEGA`) | `SRC-MEGA-P1`, `SRC-MEGA-P2` | **27** | LOW | 0 | 5 | 3 | 1 | `REENGINEERING` |
| OSINT Starter Bundle (brochure) (`COURSE-OSINT`) | `SRC-OSINT-STARTER` | **10** | HIGH | 2 | 3 | 2 | 1 | `REENGINEERING` |

## Score by dimension

| Course | Technical correctness and security (/20) | Hands-on practical effectiveness (/20) | Demonstrable professional outcomes (/15) | Assessment validity and rigor (/15) | Instructional clarity and sequencing (/10) | Technical currency and relevance (/10) | Accessibility and learner experience (/5) | Commercial product readiness (/5) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `COURSE-PY-AUTO` | 12 | 10 | 6 | 3 | 4 | 7 | 2 | 2 |
| `COURSE-SOC` | 9 | 5 | 4 | 0 | 7 | 6 | 4 | 2 |
| `COURSE-PY-ENG` | 9 | 9 | 4 | 1 | 4 | 4 | 3 | 2 |
| `COURSE-AI-ENG` | 8 | 7 | 5 | 3 | 4 | 3 | 2 | 1 |
| `COURSE-FE-ONBOARD` | 9 | 4 | 3 | 1 | 5 | 6 | 2 | 0 |
| `COURSE-JAVA-QA` | 9 | 2 | 4 | 1 | 5 | 3 | 3 | 2 |
| `COURSE-GCP-DE` | 8 | 3 | 3 | 1 | 6 | 4 | 3 | 1 |
| `COURSE-CYBER-MEGA` | 8 | 4 | 3 | 1 | 3 | 5 | 2 | 1 |
| `COURSE-OSINT` | 3 | 0 | 1 | 0 | 3 | 3 | 0 | 0 |

## Portfolio observations (evidence-backed)

- **65 findings** are registered: 4 P0, 31 P1, 23 P2, 7 P3/P4.
- **Assessment validity is the weakest dimension** across the portfolio: no source contains a grading rubric or a graded lab (rubric terms: 0 matches in every source); answer-key-like terms appear on at most a few pages per source and none was found to be an actual key.
- **Practical effectiveness is the second weakest**: only the Python courses contain substantial runnable-looking code, and none of the documents carries evidence that the code was executed (this audit only syntax-checked it).
- **The P0 findings are not editorial**: a licensing conflict (OSINT), missing legal/ethical framework (OSINT), `eval()` in an agent tool (Python Handbook) and third-party personal data in a public repository (Frontend).
- **Page counts mislead**: the sources total 8,186 pages but 569,045 words; median bookmarked sections are 12-31 words except the SOC playbook (146).

## Per-course justification

### CYBERDUDEBIVASH Python Automation Training - 46 / 100 (MEDIUM confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 12/20 | Framework patterns (config, pytest, fixtures, API client) are mostly modern; 4 confirmed copy-breaking line wraps; safety topics thin. | F-PYA-001, F-PYA-006 |
| Hands-on practical effectiveness | 10/20 | Substantial scaffolds and mini-projects, but no executable repository or verified runs. | F-PYA-003 |
| Demonstrable professional outcomes | 6/15 | Concrete project volumes; 'job-ready' and guarantee-style wording is unsupported. | F-PYA-004 |
| Assessment validity and rigor | 3/15 | Checkpoints and interview Q&A, no rubric-graded artefacts. | F-PYA-005 |
| Instructional clarity and sequencing | 4/10 | Framework build precedes Volume 1; repeated headers and scaffolds. | F-PYA-002 |
| Technical currency and relevance | 7/10 | Uses Playwright, pydantic and recent pytest; mixed pinning. | F-PYA-003 |
| Accessibility and learner experience | 2/5 | Wrapped code lines; 205 stray Markdown headers. | F-PYA-001 |
| Commercial product readiness | 2/5 | Needs a companion repo and claim clean-up before sale. | F-PYA-003, F-PYA-004 |

### SOC Analyst Survival Playbook (2026 Edition) - 37 / 100 (HIGH confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 9/20 | Practitioner advice is largely sensible, but the NIST attribution (p. 6/30), CSF code (p. 30), CERT-In scope (p. 32) and the spray-blind correlation rule (p. 22) are wrong or misleading. | F-SOC-001, F-SOC-002, F-SOC-003, F-SOC-004 |
| Hands-on practical effectiveness | 5/20 | Checklists, decision trees and a runbook template are usable on the job, but there is no dataset, runnable detection or graded exercise. | F-SOC-009, F-SOC-010 |
| Demonstrable professional outcomes | 4/15 | No measurable outcomes; career section relies on uncited salary and workforce numbers. | F-SOC-005, F-SOC-011 |
| Assessment validity and rigor | 0/15 | No assessment of any kind. | F-SOC-009 |
| Instructional clarity and sequencing | 7/10 | Short, well-sectioned and readable; contradictions in escalation guidance are minor. | F-SOC-008 |
| Technical currency and relevance | 6/10 | Recognises SP 800-61r3 and AI-assisted triage, but ATT&CK/CSF versions are not pinned and a CSF 1.1 code is cited. | F-SOC-002, F-SOC-011 |
| Accessibility and learner experience | 4/5 | Tagged text PDF with real outline; code is not monospaced; minor byline inconsistency. | F-SOC-012 |
| Commercial product readiness | 2/5 | Vendor-derived content without attribution and statistics that cannot be defended in marketing. | F-SOC-006, F-SOC-005 |

### CyberDudeBivash Python Engineering Handbook - 36 / 100 (MEDIUM confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 9/20 | 98% of extracted snippets parse, but eval() in an agent tool is a P0 and insecure credential/TLS/SSH/shell patterns are taught without safe versions. | F-PYH-001, F-PYH-002, F-PYH-004 |
| Hands-on practical effectiveness | 9/20 | Large quantity of concrete code; none executed or tested; no project with acceptance criteria. | F-PYH-004, F-PYH-007 |
| Demonstrable professional outcomes | 4/15 | No stated, measurable outcomes or capstone. | F-PYH-007 |
| Assessment validity and rigor | 1/15 | No rubrics, answer keys or graded work. | F-PYH-007 |
| Instructional clarity and sequencing | 4/10 | Median section 17 words; scope sprawls beyond engineering practice. | F-PYH-006 |
| Technical currency and relevance | 4/10 | Recommends EOL Python 3.10+; setup.py-based packaging that PyPA says must not be run. | F-PYH-003, F-PYH-005 |
| Accessibility and learner experience | 3/5 | Clean text, few markup leaks; non-monospaced code. | F-PYH-006 |
| Commercial product readiness | 2/5 | Unsupported agent claims and scope dilution weaken positioning. | F-PYH-001, F-PYH-006 |

### Complete AI Training Bundle 2026 - 33 / 100 (MEDIUM confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 8/20 | Concepts are conventional and safety-minded, but the flagship labs contain dead safeguards and the agent lab does not implement its claimed controls. | F-AI-002, F-AI-003 |
| Hands-on practical effectiveness | 7/20 | Eight lab scaffolds with READMEs exist, but the RAG lab fails on current packages and the agent lab is not agentic. | F-AI-001, F-AI-003 |
| Demonstrable professional outcomes | 5/15 | Portfolio framing is useful; percentile and 'mastery' claims are unsupported. | F-AI-007 |
| Assessment validity and rigor | 3/15 | Interview-style questions only; no rubrics or evaluation harness. | F-AI-005 |
| Instructional clarity and sequencing | 4/10 | Bullet outlines; 'PROGRAM COMPLETE' mid-document; duplicate volume. | F-AI-005, F-AI-006 |
| Technical currency and relevance | 3/10 | Removed LangChain paths; no OWASP LLM Top 10 2025, ATLAS, retrieval metrics, context engineering or MCP. | F-AI-001, F-AI-004 |
| Accessibility and learner experience | 2/5 | Raw Markdown leaks into the PDF; extremely sparse pages. | F-AI-008 |
| Commercial product readiness | 1/5 | Claims cannot be defended; labs would fail for a paying customer today. | F-AI-001, F-AI-007 |

### Internal Frontend Developer Onboarding Playbook - 30 / 100 (MEDIUM confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 9/20 | Fundamentals-first guidance is sound where read; security coverage minimal. | F-FE-003 |
| Hands-on practical effectiveness | 4/20 | No labs or runnable project. | F-FE-003 |
| Demonstrable professional outcomes | 3/15 | Interview and seniority scripts replace assessed skills. | F-FE-004 |
| Assessment validity and rigor | 1/15 | No rubric; one assessment term. | F-FE-003 |
| Instructional clarity and sequencing | 5/10 | Phased structure; very short sections. | F-FE-005 |
| Technical currency and relevance | 6/10 | Covers WCAG, Core Web Vitals, TypeScript/React; versions not pinned or aligned to ecosystem repositories. | F-FE-002 |
| Accessibility and learner experience | 2/5 | Markdown artefacts in text; personal data in samples. | F-FE-005, F-FE-001 |
| Commercial product readiness | 0/5 | Third-party personal data and unresolved 'INTERNAL' provenance block any distribution. | F-FE-001, F-FE-002 |

### Java Automation Test Engineer - Real Time Job Training - 29 / 100 (MEDIUM confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 9/20 | Concepts (page objects, waits, lifecycle) read as sound, but no code exists to verify and the baseline is dated. | F-JAV-001, F-JAV-002 |
| Hands-on practical effectiveness | 2/20 | No code, no lab, no framework. | F-JAV-001 |
| Demonstrable professional outcomes | 4/15 | Career framing with a sensible job-ready definition but no assessed outcome. | F-JAV-004 |
| Assessment validity and rigor | 1/15 | No rubric or graded lab. | F-JAV-005 |
| Instructional clarity and sequencing | 5/10 | Narrative reads well; a 14-page duplicate block; monetisation volumes off-topic. | F-JAV-003, F-JAV-004 |
| Technical currency and relevance | 3/10 | Java 8/11/17 baseline; no JUnit 5/6, Selenium 4, Playwright. | F-JAV-002 |
| Accessibility and learner experience | 3/5 | Clean text layer and outline; very sparse pages. | F-JAV-003 |
| Commercial product readiness | 2/5 | A 'hands-on' product without code cannot be sold as such. | F-JAV-001 |

### GCP Data Engineer Training - 29 / 100 (MEDIUM confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 8/20 | Outline-level content is conventional; CI examples teach long-lived service-account keys against Google's guidance. | F-GCP-001 |
| Hands-on practical effectiveness | 3/20 | Projects are four-bullet specs with no data, steps or acceptance tests; billable services without safeguards. | F-GCP-002, F-GCP-003 |
| Demonstrable professional outcomes | 3/15 | Capstone is a bullet list; outcome claims untested. | F-GCP-005 |
| Assessment validity and rigor | 1/15 | No graded assessment. | F-GCP-003 |
| Instructional clarity and sequencing | 6/10 | Clear phase/module sequencing (Phase 0-10). | F-GCP-003 |
| Technical currency and relevance | 4/10 | gsutil use, no Dataform/Dataplex/BigLake; exam alignment unverified. | F-GCP-004 |
| Accessibility and learner experience | 3/5 | Clean text layer; 315 embedded images (emoji glyphs); sparse pages. | F-GCP-003 |
| Commercial product readiness | 1/5 | Cost exposure for learners; claims unverifiable. | F-GCP-002, F-GCP-005 |

### Official CyberDudeBivash Mega Course 2026 (Parts 1 and 2) - 27 / 100 (LOW confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 8/20 | Sampled checklists are plausible; uncited statistics, branded pseudo-frameworks and unspecified offensive labs reduce trust. | F-MEGA-003, F-MEGA-004, F-MEGA-005 |
| Hands-on practical effectiveness | 4/20 | 140+ lab headings but each is a bullet procedure without environment, data or verification. | F-MEGA-002, F-MEGA-005 |
| Demonstrable professional outcomes | 3/15 | 'Guaranteed job' and expert-title promises. | F-MEGA-003, F-MEGA-009 |
| Assessment validity and rigor | 1/15 | No rubrics or answer keys in ~3,660 pages. | F-MEGA-007 |
| Instructional clarity and sequencing | 3/10 | TOC, body and Part 2 disagree on module identity; ~80% of sections under 40 words. | F-MEGA-001, F-MEGA-002 |
| Technical currency and relevance | 5/10 | Covers 2025-2026 themes (AI, cloud-native); frameworks unpinned (ATT&CK v20 current). | F-MEGA-008 |
| Accessibility and learner experience | 2/5 | Bookmark inflation (9,198 entries in Part 1); clean text layer. | F-MEGA-006 |
| Commercial product readiness | 1/5 | Too large and inconsistent to sell as one product; guarantee claims are a liability. | F-MEGA-001, F-MEGA-003 |

### OSINT Starter Bundle (brochure) - 10 / 100 (HIGH confidence)

| Dimension | Score | Why | Findings |
|---|---:|---|---|
| Technical correctness and security | 3/20 | Almost no technical instruction; where it instructs (alias tracking, leaked-data correlation) it omits the lawful-use framework. | F-OSINT-003 |
| Hands-on practical effectiveness | 0/20 | Describes labs, a VM and tools that are not in the repository; contains no executable exercise. | F-OSINT-001 |
| Demonstrable professional outcomes | 1/15 | Time-to-competence and career claims are unsupported. | F-OSINT-005 |
| Assessment validity and rigor | 0/15 | No assessment. | F-OSINT-001 |
| Instructional clarity and sequencing | 3/10 | Readable marketing prose but no learning structure. | F-OSINT-001 |
| Technical currency and relevance | 3/10 | 2025-era threat framing; statistics are stale or mis-sourced. | F-OSINT-005 |
| Accessibility and learner experience | 0/5 | Text is vector outlines: unsearchable and unreadable by assistive technology. | F-OSINT-006 |
| Commercial product readiness | 0/5 | Proposes relicensing copyleft tools; contains internal SEO/funnel strategy; promotes unreleased products. | F-OSINT-002, F-OSINT-004, F-OSINT-007, F-OSINT-008 |
