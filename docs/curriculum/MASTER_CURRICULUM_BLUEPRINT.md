# Master Curriculum Blueprint

Status: **blueprint — only one module (SOC-M04) is built.** Everything else is a plan derived from the audit findings and registered in `catalog/courses.yaml`.

Generated regions in this document (between `GENERATED` markers) are produced by `scripts/build/render_program_docs.py` from the catalog; edit the catalog, not the tables.

## 1. Purpose and constraints

The ten source PDFs received at baseline commit `f2ba7d0` are brochure- or outline-grade documents (`docs/audits/COURSE_QUALITY_SCORECARD.md`: best score 46/100, median about 30). The blueprint replaces them with a modular, assessable curriculum in which every module can be checked by a machine and every claim can be traced to a source.

Constraints taken from the mission directive and enforced by tooling:

- Originals are preserved unchanged in the repository root; `tests/test_repo_hygiene.py` verifies their hashes against `docs/audits/data/source_inventory.json`.
- Free, local-first labs. Any billable cloud lab needs an explicit opt-in, a cost estimate, a spending safeguard, teardown steps and a free local alternative (`PRACTICAL_LAB_STANDARDS.md`).
- Offensive-security content is allowed only in authorised, isolated, synthetic environments.
- No outcome, salary, job, ranking or certification-pass claim appears in learner-facing text without a cited, dated source.
- No pricing, publication or deployment happens from this repository.

## 2. Architecture

```
Level 0   COURSE-FND-DIGITAL                    shared by every pathway
             │
Level 1-3 ├─ COURSE-PY-ENG ─┬─ COURSE-PY-AUTO
          │                 ├─ COURSE-AI-ENG ──(AI security specialism)
          │                 └─ COURSE-GCP-DE
          ├─ COURSE-SOC                         (needs PY-M01/PY-M02 for its labs)
          ├─ COURSE-CYBER-MEGA  (specialist tracks; SOC and AI security are NOT duplicated here)
          ├─ COURSE-JAVA-QA
          ├─ COURSE-FE-ONBOARD
          └─ COURSE-OSINT
```

Rules that keep this a single curriculum rather than ten documents:

1. **One owner per topic.** A topic is taught in exactly one module; other modules link to it (`reuses` in the catalog is validated against pathway order).
2. **Foundations are shared.** Python basics live in `COURSE-PY-ENG`; `COURSE-PY-AUTO`, `COURSE-AI-ENG` and `COURSE-GCP-DE` depend on it instead of repeating it. The 3,660-page Mega Course becomes tracks that reference the dedicated SOC and AI courses.
3. **Every module follows the unit contract** (section 4).
4. **Levels are evidence levels** (`COMPETENCY_PATHWAYS.md`), not job titles.
5. **Version-sensitive facts are pinned** in the lesson front matter and logged in `docs/research/research_register.yaml`.

## 3. Portfolio

<!-- BEGIN GENERATED: totals -->
| Measure | Value |
|---|---:|
| Courses | 10 |
| Modules planned / with built content | 113 / 17 |
| Labs planned / built / verified executable in QA | 217 / 33 / 27 |
| Module outcomes total / assessed | 118 / 22 |
| Courses with SME review recorded | 0 |
| Courses with a named owner | 0 |
| Courses by release status | REENGINEERING: 10 |
<!-- END GENERATED: totals -->

<!-- BEGIN GENERATED: portfolio -->
| Course | ID | Level span | Modules | Planned hours | Labs planned / built / verified | Outcomes assessed | Lifecycle | Release status |
|---|---|---|---:|---:|---|---:|---|---|
| Digital and Technical Foundations | `COURSE-FND-DIGITAL` | L0-L0 | 6 | 32 | 12 / 6 / 0 | 3/6 | IN_BUILD | `REENGINEERING` |
| SOC Analyst Professional Pathway | `COURSE-SOC` | L1-L3 | 14 | 104 | 27 / 2 / 2 | 6/19 | PILOT_BUILT | `REENGINEERING` |
| Python Engineering Pathway | `COURSE-PY-ENG` | L1-L3 | 13 | 112 | 25 / 25 / 25 | 13/13 | IN_BUILD | `REENGINEERING` |
| Python Automation Pathway | `COURSE-PY-AUTO` | L2-L3 | 10 | 73 | 19 / 0 / 0 | 0/10 | IN_DESIGN | `REENGINEERING` |
| Java Test Automation Engineer Pathway | `COURSE-JAVA-QA` | L1-L3 | 10 | 92 | 19 / 0 / 0 | 0/10 | IN_DESIGN | `REENGINEERING` |
| Applied AI and LLM Engineering Pathway | `COURSE-AI-ENG` | L1-L3 | 12 | 114 | 23 / 0 / 0 | 0/12 | IN_DESIGN | `REENGINEERING` |
| Lawful OSINT Investigation Pathway | `COURSE-OSINT` | L1-L2 | 12 | 66 | 23 / 0 / 0 | 0/12 | IN_DESIGN | `REENGINEERING` |
| Google Cloud Data Engineering Pathway | `COURSE-GCP-DE` | L2-L3 | 11 | 94 | 21 / 0 / 0 | 0/11 | IN_DESIGN | `REENGINEERING` |
| Frontend Engineering Onboarding Pathway | `COURSE-FE-ONBOARD` | L1-L3 | 11 | 92 | 21 / 0 / 0 | 0/11 | IN_DESIGN | `REENGINEERING` |
| Cybersecurity Specialist Tracks (from the Mega Course) | `COURSE-CYBER-MEGA` | L1-L3 | 14 | 188 | 27 / 0 / 0 | 0/14 | IN_DESIGN | `REENGINEERING` |
| **Total** | | | **113** | **967** | **217** planned | | | |

Hours are **planning estimates** (module authoring budgets), not measured learner times. The portfolio total counts modules that appear in several pathways once.
<!-- END GENERATED: portfolio -->

Level spread (modules per level):

<!-- BEGIN GENERATED: level-matrix -->
| Course | L0 | L1 | L2 | L3 |
|---|---:|---:|---:|---:|
| `COURSE-FND-DIGITAL` | 6 | · | · | · |
| `COURSE-SOC` | · | 3 | 5 | 6 |
| `COURSE-PY-ENG` | · | 2 | 9 | 2 |
| `COURSE-PY-AUTO` | · | · | 5 | 5 |
| `COURSE-JAVA-QA` | · | 3 | 4 | 3 |
| `COURSE-AI-ENG` | · | 1 | 4 | 7 |
| `COURSE-OSINT` | · | 3 | 9 | · |
| `COURSE-GCP-DE` | · | · | 4 | 7 |
| `COURSE-FE-ONBOARD` | · | 3 | 6 | 2 |
| `COURSE-CYBER-MEGA` | · | 2 | 5 | 7 |
<!-- END GENERATED: level-matrix -->

## 4. The module unit contract

Every module must ship all of the following. `courses/soc-analyst/` module SOC-M04 is the reference implementation and `tests/pilot/test_curriculum.py` shows how the contract is verified.

| Component | Requirement | Pilot location |
|---|---|---|
| Measurable outcomes | Start with an observable verb; each maps to at least one assessment item. | `curriculum/outcomes.yaml` |
| Source map | Where each element came from or why it is new; attribution for third-party material. | `curriculum/source-map.yaml`, `shared/templates/attribution-notices.md` |
| Lesson | Explains, then shows a worked example with real data; states versions; ends with misconceptions and a retrieval check. | `lessons/m04-auth-detection/lesson.md` |
| Guided lab | Step-by-step, deterministic data, expected outputs quoted in the README **and verified by tests**. | `labs/m04-guided/` |
| Independent lab | Same skill on new data, success criteria measured, no solution in the public repository. | `labs/m04-independent/` |
| Assessment | Items tagged to outcomes, rationales, no answer key in public files. | `assessments/m04/quiz.yaml` |
| Rubric | Criteria, levels with observable descriptors, weights, minimum pass conditions. | `assessments/m04/rubric.yaml` |
| Instructor notes | Pacing, common errors, grading guidance, answer keys. **Private** (the repository is public). | `instructor/` (git-ignored except README) |
| Student artefact | Something the learner keeps (rules, triage records, report) that a reviewer can evaluate. | `student/student-edition.yaml` → built PDF |
| Automated checks | Evaluators and tests that fail closed on unsupported input. | `labs/soc_lab/`, `tests/pilot/` |

Definition of done for a module: contract complete, `pytest` green, outcomes all assessed, claims in `research_register.yaml`, licence notes in the source map, design-system build passes, and the module's catalog entry updated by the QA run — not by hand.

## 5. Source disposition

All ten sources remain in the repository root unchanged. This table says what happens to their content; per-source evidence is in `docs/audits/courses/`.

| Source | Becomes | Kept as input | Replaced | Retired |
|---|---|---|---|---|
| `SRC-SOC-PLAYBOOK` | `COURSE-SOC` | Task checklists and triage decision structure (re-authored, vendor-neutral) | IR-lifecycle framing, CSF code, CERT-In scope sentence, the spray-blind correlation example (F-SOC-001..004) | Uncited statistics, salary bands (F-SOC-005) |
| `SRC-PY-HANDBOOK` | `COURSE-PY-ENG` | Topic outline | `eval()` agent tool, insecure credential/TLS/SSH examples, `setup.py` packaging, Python 3.10 baseline (F-PYH-001..005) | — |
| `SRC-PY-AUTOMATION` | `COURSE-PY-AUTO` | Configuration, pytest, fixture and API-client patterns after execution | Linear structure; interview-question assessment (F-PYA-002, 005) | "Job-ready" wording (F-PYA-004) |
| `SRC-JAVA-AUTOTEST` | `COURSE-JAVA-QA` | Testing-concept topic list | All code (source contains none) and the Java 8/11/17 baseline (F-JAV-001, 002) | Duplicated block, monetisation volume (F-JAV-003, 004) |
| `SRC-AI-BUNDLE` | `COURSE-AI-ENG` | Conceptual topic coverage | RAG and agent labs (do not run / safeguards are dead code), missing LLM-security and evaluation (F-AI-001..004) | Unsupported comparative claims (F-AI-007) |
| `SRC-OSINT-STARTER` | `COURSE-OSINT` | Nothing as course content (brochure) | Everything: lawful-collection framework first (F-OSINT-001, 003) | Proprietary re-licensing of third-party tools (F-OSINT-002); internal go-to-market text (F-OSINT-004) |
| `SRC-GCP-DATAENG` | `COURSE-GCP-DE` | Service sequence | Service-account-key CI auth, no cost controls, four-bullet "projects" (F-GCP-001..003) | Equivalence claims (F-GCP-005) |
| `SRC-FRONTEND-ONBOARD` | `COURSE-FE-ONBOARD` | Topic list | Missing labs and security depth (F-FE-003) | Third-party personal data (F-FE-001) — **owner action required** in the source file |
| `SRC-MEGA-P1`, `SRC-MEGA-P2` | `COURSE-CYBER-MEGA` plus dedicated SOC and AI courses | Domain taxonomy as module seeds | Breadth-without-depth sections, unspecified labs, missing assessments (F-MEGA-001, 002, 005, 007) | Job guarantee, uncited statistics (F-MEGA-003) |

## 6. Transformation mandates and where they land

| Mandate | Module(s) |
|---|---|
| AI: RAG with retrieval evaluation, agent permissions, context engineering, OWASP LLM Top 10 (2025), observability, governance | AI-M04, AI-M05, AI-M06, AI-M07, AI-M08, AI-M09 |
| Python Engineering: modern packaging (`pyproject.toml`), typing, tests, security, performance | PY-M02, PY-M03, PY-M04, PY-M07, PY-M09 |
| Python Automation: idempotency, atomic writes, secrets, observability, fault injection | PA-M02, PA-M05, PA-M06, PA-M07, PA-M08 |
| Java QA: Java 21+, JUnit 6, Playwright/Selenium, framework design, flaky-test diagnosis | JQA-M01, JQA-M04, JQA-M05, JQA-M07, JQA-M08 |
| OSINT: law and ethics first, evidence preservation, confidence language | OSINT-M01, OSINT-M04, OSINT-M06, OSINT-M07 |
| GCP data engineering: IAM and cost safety first, Workload Identity Federation, local-first labs | GCP-M01, GCP-M08, GCP-M10 |
| Frontend: WCAG 2.2 AA, XSS/CSP, Core Web Vitals | FE-M06, FE-M07, FE-M09 |
| Mega Course: modular tracks instead of 3,660 pages | `COURSE-CYBER-MEGA` CYB-M01..M14 |
| SOC: telemetry, detection, triage, investigation, reporting | SOC-M01..M12 (SOC-M04 built) |

## 7. Module catalogue

<!-- BEGIN GENERATED: modules -->
### Digital and Technical Foundations (`COURSE-FND-DIGITAL`)

Prerequisites: none · Estimated hours: 32 · Capstone: Automate a small file-reporting task in a Git repository, with tests, a README and a pull request reviewed against a checklist.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `FND-M01` | Operating systems, files and permissions | L0 | 4 | BUILT | Navigate a Linux and a Windows file system and explain how permissions restrict access to a file. |
| `FND-M02` | Command-line fundamentals | L0 | 5 | BUILT | Execute a bounded diagnostic CLI, explain process exit statuses and record reproducible synthetic evidence. |
| `FND-M03` | Networking and HTTP basics | L0 | 6 | BUILT | Observe a controlled local TCP/HTTP exchange and distinguish that evidence from synthetic DNS and TLS failure records. |
| `FND-M04` | Git and GitHub workflow | L0 | 4 | PLANNED | Create a branch, commit a change and open a pull request in a practice repository. |
| `FND-M05` | Programming fundamentals with Python | L0 | 10 | PLANNED | Write a Python script with functions that passes a provided automated test suite. |
| `FND-M06` | Troubleshooting and safe computing | L0 | 3 | PLANNED | Diagnose a deliberately broken script from its error output and describe the fix and the safe-lab rules followed. |

### SOC Analyst Professional Pathway (`COURSE-SOC`)

Prerequisites: `COURSE-FND-DIGITAL` · Estimated hours: 104 · Capstone: End-to-end synthetic intrusion investigation with a detection improvement validated on labelled telemetry and a graded incident report.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `SOC-M01` | SOC fundamentals, roles and the alert lifecycle | L1 | 4 | PLANNED | Explain the alert lifecycle and map each stage to the role and artefact responsible for it. |
| `SOC-M02` | Telemetry: Windows, Linux and network logs | L1 | 8 | PLANNED | Identify the log source and event ID or field that evidences a given behaviour in Windows, Linux and network data. |
| `SOC-M03` | Log parsing, normalisation and query languages | L1 | 8 | PLANNED | Parse a raw log sample into a normalised schema and answer five investigative questions with queries. |
| `SOC-M04` | Authentication-attack detection and triage | L2 | 6 | BUILT_PILOT / lab VERIFIED_EXECUTABLE | Build and validate detections for brute-force and password-spray activity and triage the resulting alerts with documented evidence. _(reuses SOC-M02)_ |
| `SOC-M05` | Alert triage and case management | L2 | 6 | PLANNED | Triage a queue of ten synthetic alerts, classify each with evidence and produce a handover record. |
| `SOC-M06` | Detection engineering with Sigma and ATT&CK | L2 | 10 | PLANNED | Author a Sigma rule mapped to an ATT&CK technique and demonstrate its precision and recall on labelled data. |
| `SOC-M07` | Threat-intelligence enrichment and false-positive reduction | L2 | 6 | PLANNED | Reduce false positives of a noisy rule by at least 50 percent without losing any true-positive scenario. |
| `SOC-M08` | Incident investigation and evidence handling (NIST SP 800-61r3 / CSF 2.0) | L2 | 8 | PLANNED | Reconstruct an incident timeline from multi-source evidence and map actions to CSF 2.0 functions. |
| `SOC-M09` | Threat hunting | L3 | 8 | PLANNED | Plan and execute a hypothesis-driven hunt against a dataset and report negative and positive findings. |
| `SOC-M10` | Malware-analysis fundamentals in an isolated lab | L3 | 8 | PLANNED | Perform static triage of a safe benign sample in an isolated VM and document indicators with confidence levels. |
| `SOC-M11` | Executive and technical incident reporting | L3 | 4 | PLANNED | Write an executive summary and a technical appendix for one incident that pass the reporting rubric. |
| `SOC-M12` | Cloud and identity threat detection | L3 | 8 | PLANNED | Detect and triage a synthetic identity-compromise and cloud-misuse scenario using normalised cloud audit logs. |
| `SOC-M13` | SOAR playbooks and AI-assisted investigation automation | L3 | 8 | PLANNED | Implement a playbook that enriches and routes alerts with a human approval gate and measure its effect on triage time on labelled alerts. |
| `SOC-M14` | Capstone: end-to-end SOC investigation | L3 | 12 | PLANNED | Investigate a multi-stage synthetic intrusion, improve one detection and deliver an evidence-based incident report. |

### Python Engineering Pathway (`COURSE-PY-ENG`)

Prerequisites: `COURSE-FND-DIGITAL` · Estimated hours: 112 · Capstone: A typed, tested, documented, packaged Python application with continuous validation and a dependency/security scan.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `PY-M01` | Language core and data structures | L1 | 12 | BUILT / lab VERIFIED_EXECUTABLE | Implement five data-processing functions that pass provided unit tests. |
| `PY-M02` | Functions, errors and testing with pytest | L1 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Write parametrised pytest tests that detect three seeded defects in a provided module. |
| `PY-M13` | Iterators, generators, closures, decorators and context managers | L2 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Build a lazy stream-processing toolkit whose generators, decorators and context managers consume only what they need and release every resource on every path, verified by tests that count consumption. |
| `PY-M03` | Types, modules and project layout | L2 | 6 | BUILT / lab VERIFIED_EXECUTABLE | Refactor a script into a typed package that passes a static type checker without errors. |
| `PY-M12` | Classes, dataclasses and object-oriented design | L2 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Model a small domain with frozen value types, per-instance state, injected behaviour and an event bus, and keep every rule true under a hidden suite that tests equality, immutability, isolation and refusal. |
| `PY-M04` | Environments, dependencies and packaging (pyproject, build) | L2 | 6 | BUILT / lab VERIFIED_EXECUTABLE | Build, install and import a wheel produced with python -m build in a clean virtual environment. |
| `PY-M05` | Files, structured data and HTTP clients | L2 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Consume a paginated API fixture with retries and timeouts and validate every response against a schema. |
| `PY-M06` | Concurrency and asynchronous programming | L2 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Reduce the runtime of an I/O-bound job with asyncio and prove the speed-up with a benchmark. |
| `PY-M07` | Secure coding for Python | L2 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Find and fix eight seeded vulnerabilities (injection, secrets, TLS, deserialisation) and add a regression test for each. |
| `PY-M08` | Databases and persistence: safe SQL, transactions, repositories, migrations and query cost | L2 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Implement a repository layer using parameterised SQL, a versioned schema and atomic writes, and demonstrate that an injection attempt, a retry and a concurrent edit do not corrupt the data. |
| `PY-M09` | Profiling, performance and maintainable architecture | L3 | 8 | BUILT / lab VERIFIED_EXECUTABLE | Identify the dominant bottleneck of a slow program with a profiler and cut its runtime by at least 30 percent without changing an answer, and prove it with tests that do not depend on the speed of the machine. |
| `PY-M10` | API development: typed, tested and secure HTTP services | L2 | 10 | BUILT / lab VERIFIED_EXECUTABLE | Build a typed HTTP API with request validation and authentication that passes contract tests and an injection test suite, and a multi-tenant API that survives a hidden review suite. |
| `PY-M11` | Capstone: typed, tested, documented application with CI | L3 | 14 | BUILT / lab VERIFIED_EXECUTABLE | Deliver a packaged application whose tests, type checks and security scan pass in a clean environment, whose behaviour passes a hidden suite and whose own tests detect seeded defects. |

### Python Automation Pathway (`COURSE-PY-AUTO`)

Prerequisites: `COURSE-PY-ENG` · Estimated hours: 73 · Capstone: A safe, reproducible automation of a real operational workflow with auditable output and a fault-injection test suite.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `PA-M01` | Automation design and shared Python foundations | L2 | 4 | PLANNED | Specify an automation with inputs, outputs, failure modes and an idempotency rule before writing code. _(reuses PY-M01, PY-M02, PY-M03)_ |
| `PA-M02` | Filesystem and document workflows | L2 | 6 | PLANNED | Process a folder of CSV and JSON inputs into a validated report using atomic writes. |
| `PA-M03` | API integrations and data validation | L2 | 8 | PLANNED | Integrate two API fixtures and reject malformed records with explicit error reports. _(reuses PY-M05)_ |
| `PA-M04` | Browser automation with supported tools | L2 | 8 | PLANNED | Automate a login-and-export flow against a local test application with stable locators and traces. |
| `PA-M05` | Scheduling, configuration and secrets | L2 | 6 | PLANNED | Run a job on a schedule with layered configuration and no secret stored in the repository. |
| `PA-M06` | Reliability: retries, idempotency and recovery | L3 | 8 | PLANNED | Show that re-running a failed job after injected faults produces exactly-once results. |
| `PA-M07` | Observability and auditable output | L3 | 5 | PLANNED | Produce structured logs and an audit report that allow a reviewer to reconstruct every action of a run. |
| `PA-M08` | Testing automations: unit, integration, regression | L3 | 8 | PLANNED | Reach a defined test pass and fault-injection suite for a provided automation. |
| `PA-M09` | Command-line tools and guarded AI-assisted automation | L3 | 8 | PLANNED | Build a tested command-line tool and add an AI-assisted step whose output is validated, logged and cannot trigger an unreviewed action. |
| `PA-M10` | Capstone: safe operational workflow | L3 | 12 | PLANNED | Deliver a reproducible workflow that performs a real operational task and emits auditable output. |

### Java Test Automation Engineer Pathway (`COURSE-JAVA-QA`)

Prerequisites: `COURSE-FND-DIGITAL` · Estimated hours: 92 · Capstone: Reproducible UI and API automation framework (Java, Maven, CI) against an authorised sample application.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `JQA-M01` | Java 21+ essentials for test engineers | L1 | 12 | PLANNED | Implement a utility library whose unit tests pass on Java 21 with Maven. |
| `JQA-M02` | Object-oriented design and collections for frameworks | L1 | 8 | PLANNED | Refactor duplicated test helpers into an abstraction with interfaces and demonstrate reuse in two suites. |
| `JQA-M03` | Testing fundamentals: risk, design techniques, defect reports | L1 | 8 | PLANNED | Design a test set from a requirement using equivalence classes and boundaries and file two defect reports with evidence. |
| `JQA-M04` | JUnit 6 structure and parameterised tests | L2 | 6 | PLANNED | Write parameterised JUnit tests with lifecycle hooks and run them from Maven. |
| `JQA-M05` | Selenium WebDriver and Playwright for Java | L2 | 12 | PLANNED | Automate five user journeys against an authorised sample application with stable locators and explicit waits. |
| `JQA-M06` | API testing with Java | L2 | 8 | PLANNED | Validate status, schema and error behaviour of a REST API fixture with a test suite. |
| `JQA-M07` | Framework architecture: page objects, data-driven tests, configuration | L2 | 10 | PLANNED | Build a layered framework where adding a new test needs no change to infrastructure code. |
| `JQA-M08` | CI, parallel execution and flaky-test diagnosis | L3 | 8 | PLANNED | Run the suite in parallel in CI and diagnose three seeded flaky tests to root cause. |
| `JQA-M09` | Reporting, evidence and release readiness | L3 | 4 | PLANNED | Generate a test report with failure evidence that a reviewer can use to decide on release. |
| `JQA-M10` | Capstone: UI and API automation framework | L3 | 16 | PLANNED | Deliver a reproducible end-to-end framework whose acceptance suite passes against the sample application. |

### Applied AI and LLM Engineering Pathway (`COURSE-AI-ENG`)

Prerequisites: `COURSE-PY-ENG` · Estimated hours: 114 · Capstone: Production-oriented AI assistant with documented threat model, evaluation suite, secure tool permissions, logging, failure handling and reproducible tests.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `AI-M01` | AI and ML fundamentals, evaluation and limits | L1 | 12 | PLANNED | Train and evaluate a baseline classifier and report precision, recall and one failure analysis. |
| `AI-M02` | Python AI application development | L2 | 8 | PLANNED | Build a service that calls a model through a provider-agnostic interface and passes contract tests. |
| `AI-M03` | LLM application architecture and structured outputs | L2 | 8 | PLANNED | Implement schema-validated structured outputs with retries and a documented failure policy. |
| `AI-M04` | Retrieval-augmented generation and retrieval evaluation | L2 | 12 | PLANNED | Build a RAG pipeline and measure recall@k and answer faithfulness on a labelled question set. |
| `AI-M05` | Agents, tool calling and enforced permissions | L3 | 10 | PLANNED | Implement an agent whose tool permissions, step budget and approval gate are enforced and tested adversarially. |
| `AI-M06` | Context engineering | L3 | 6 | PLANNED | Design a context assembly policy and show its effect on accuracy and cost on a benchmark. |
| `AI-M07` | LLM security: OWASP LLM Top 10 (2025), prompt injection and red teaming | L3 | 10 | PLANNED | Threat-model an LLM application against the OWASP LLM Top 10 and demonstrate two mitigated attacks with tests. |
| `AI-M08` | Evaluation suites, observability, cost and latency | L3 | 8 | PLANNED | Operate an evaluation suite and dashboard that detect a seeded quality regression and a cost spike. |
| `AI-M09` | Governance and responsible deployment (NIST AI RMF) | L3 | 6 | PLANNED | Produce a risk register and human-oversight design for one AI use case mapped to NIST AI RMF functions. |
| `AI-M10` | Model Context Protocol, tool interoperability and multi-agent systems | L3 | 10 | PLANNED | Implement an MCP server and client against specification revision 2026-07-28 and demonstrate permission-scoped tool access across two cooperating agents. |
| `AI-M11` | Model selection, multimodal inputs and deployment economics | L2 | 8 | PLANNED | Select a model for a task from measured quality, latency and cost on a labelled set and document the decision. |
| `AI-M12` | Capstone: secure production-oriented AI assistant | L3 | 16 | PLANNED | Deliver an assistant with a threat model, evaluation suite, enforced tool permissions, logging and reproducible tests. |

### Lawful OSINT Investigation Pathway (`COURSE-OSINT`)

Prerequisites: `COURSE-FND-DIGITAL` · Estimated hours: 66 · Capstone: Defensible OSINT intelligence report on a synthetic or consented case with source provenance, uncertainty analysis and ethical collection records.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `OSINT-M01` | Law, ethics, privacy and prohibited activities | L1 | 5 | PLANNED | Classify ten proposed collection actions as permitted, restricted or prohibited and justify each decision. |
| `OSINT-M02` | Research planning and collection management | L1 | 4 | PLANNED | Write a collection plan with scope, questions, sources and data-minimisation rules. |
| `OSINT-M03` | Search methodology and source discovery | L1 | 6 | PLANNED | Locate and document sources for a synthetic case using advanced search operators and archives. |
| `OSINT-M04` | Source validation, provenance and evidence preservation | L2 | 6 | PLANNED | Rate source reliability and preserve evidence with hashes, timestamps and a chain-of-custody log. |
| `OSINT-M05` | Metadata and geospatial analysis from lawful sources | L2 | 8 | PLANNED | Geolocate a synthetic image set from lawful imagery and metadata and state confidence for each conclusion. |
| `OSINT-M06` | Chronology, confidence and attribution limits | L2 | 5 | PLANNED | Build a timeline and confidence-graded assessment that states what cannot be attributed. |
| `OSINT-M07` | Researcher operational security | L2 | 4 | PLANNED | Configure an isolated research environment and document the controls that protect the researcher. |
| `OSINT-M08` | Disinformation awareness | L2 | 4 | PLANNED | Assess a synthetic influence campaign using provenance and behavioural indicators. |
| `OSINT-M09` | Reporting and intelligence communication | L2 | 4 | PLANNED | Write an intelligence report with sourcing, uncertainty language and ethical-collection record. |
| `OSINT-M10` | Passive domain and infrastructure intelligence | L2 | 5 | PLANNED | Map the public infrastructure of a synthetic domain using passive sources and record the provenance and legal basis of every observation. |
| `OSINT-M11` | AI-assisted investigation and synthetic-media verification | L2 | 5 | PLANNED | Verify a set of synthetic images and a claim using provenance signals and document where AI assistance was used and checked. |
| `OSINT-M12` | Capstone: defensible OSINT report | L2 | 10 | PLANNED | Deliver a report on a synthetic case with provenance for every claim and an ethical-collection log. |

### Google Cloud Data Engineering Pathway (`COURSE-GCP-DE`)

Prerequisites: `COURSE-PY-ENG` · Estimated hours: 94 · Capstone: A documented, monitored, secure, cost-aware batch and streaming data pipeline with tests and a teardown script.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `GCP-M01` | Cloud foundations, IAM, cost safety and sandbox setup | L2 | 6 | PLANNED | Configure a project with least-privilege IAM, a budget alert and a documented teardown. |
| `GCP-M02` | Cloud Storage and batch ingestion | L2 | 8 | PLANNED | Ingest a vendor file drop with validation and idempotent loads, locally and on Google Cloud. |
| `GCP-M03` | BigQuery SQL and analytical modelling | L2 | 12 | PLANNED | Model a partitioned and clustered dataset and show the query-cost reduction measured with dry runs. |
| `GCP-M04` | Pub/Sub and streaming ingestion | L2 | 8 | PLANNED | Process a stream with dead-letter handling and prove no message is lost under injected failures. |
| `GCP-M05` | Apache Beam and Dataflow | L3 | 10 | PLANNED | Implement a Beam pipeline that passes unit tests on the DirectRunner and runs on Dataflow within a cost budget. |
| `GCP-M06` | Orchestration and pipeline reliability | L3 | 8 | PLANNED | Orchestrate a DAG with retries, backfills and alerting and demonstrate recovery from a failed task. |
| `GCP-M07` | Data quality, governance and security | L3 | 8 | PLANNED | Enforce data-quality assertions and column-level access policies and show a blocked unauthorised query. |
| `GCP-M08` | Infrastructure as code and CI with Workload Identity Federation | L3 | 8 | PLANNED | Deploy infrastructure from CI without any long-lived service-account key. |
| `GCP-M09` | Monitoring, SLOs and cost optimisation | L3 | 6 | PLANNED | Define SLOs and alerts for a pipeline and cut the cost of a provided workload by a measured amount. |
| `GCP-M10` | Reliability, disaster recovery and operational procedures | L3 | 6 | PLANNED | Execute a documented recovery drill for a pipeline and measure recovery time and data loss against stated objectives. |
| `GCP-M11` | Capstone: monitored, secure, cost-aware pipeline | L3 | 14 | PLANNED | Deliver a documented pipeline with monitoring, security controls, tests and a cost report. |

### Frontend Engineering Onboarding Pathway (`COURSE-FE-ONBOARD`)

Prerequisites: `COURSE-FND-DIGITAL` · Estimated hours: 92 · Capstone: A secure, tested, responsive, accessible frontend feature integrated with a controlled API fixture or authorised development environment.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `FE-M01` | Web fundamentals and semantic HTML | L1 | 6 | PLANNED | Build a semantic, keyboard-navigable page that passes an automated accessibility check. |
| `FE-M02` | CSS and responsive layout | L1 | 8 | PLANNED | Implement a layout that works without horizontal scrolling from 320 to 1440 pixels wide. |
| `FE-M03` | JavaScript and TypeScript | L1 | 12 | PLANNED | Write typed modules whose unit tests pass and whose compiler reports no errors. |
| `FE-M04` | Components and state management | L2 | 10 | PLANNED | Compose a component tree with controlled state and test its behaviour through the DOM. |
| `FE-M05` | API integration, authentication and authorisation concepts | L2 | 8 | PLANNED | Integrate an authenticated API fixture with loading, error and expired-session states handled. |
| `FE-M06` | Accessibility to WCAG 2.2 AA | L2 | 8 | PLANNED | Audit a page against WCAG 2.2 AA, fix five seeded failures and document the evidence. |
| `FE-M07` | Frontend security: XSS, CSP, CSRF and dependencies | L2 | 8 | PLANNED | Exploit and then fix an XSS flaw in a lab app and ship a Content-Security-Policy that blocks it. |
| `FE-M08` | Testing and browser debugging | L2 | 8 | PLANNED | Diagnose three seeded defects with browser developer tools and cover each with a test. |
| `FE-M09` | Performance (Core Web Vitals) and error handling | L3 | 6 | PLANNED | Improve a page's measured Largest Contentful Paint and Interaction to Next Paint against a stated budget. |
| `FE-M10` | Git workflow, pull requests and code review standards | L2 | 4 | PLANNED | Open a pull request that satisfies a written review checklist and respond to review comments. |
| `FE-M11` | Capstone: secure responsive feature | L3 | 14 | PLANNED | Deliver a secure, tested, responsive feature integrated with a controlled API fixture. |

### Cybersecurity Specialist Tracks (from the Mega Course) (`COURSE-CYBER-MEGA`)

Prerequisites: `COURSE-FND-DIGITAL` · Estimated hours: 188 · Capstone: Multi-domain, authorised, simulated security exercise delivering a graded technical report and executive briefing.

| Module | Title | Level | Hours | State | Primary outcome (observable) |
|---|---|---:|---:|---|---|
| `CYB-M01` | Security foundations, threats and frameworks (ATT&CK, CSF 2.0, OWASP) | L1 | 12 | PLANNED | Map a set of ten incidents to ATT&CK techniques and CSF 2.0 functions with version references. |
| `CYB-M02` | Networking and operating-system security | L1 | 16 | PLANNED | Harden a Linux and a Windows lab host to a written baseline and verify each control with a check script. |
| `CYB-M03` | Cryptography, identity and access management | L2 | 12 | PLANNED | Design and test an authentication and authorisation scheme and explain the residual risks. |
| `CYB-M04` | Web and API application security | L2 | 16 | PLANNED | Find, exploit in an isolated lab, and fix five OWASP-class vulnerabilities with regression tests. |
| `CYB-M05` | Vulnerability management and authorised assessment | L2 | 12 | PLANNED | Plan and execute an authorised scan against a lab network and produce a risk-ranked report. |
| `CYB-M06` | Cloud and container security | L2 | 16 | PLANNED | Detect and remediate seeded misconfigurations in a Kubernetes and a cloud IAM lab. |
| `CYB-M07` | DevSecOps and software supply-chain defence | L2 | 12 | PLANNED | Add dependency, secret and SBOM checks to a CI pipeline that blocks a seeded vulnerable build. |
| `CYB-M08` | Digital forensics and incident response | L3 | 16 | PLANNED | Reconstruct an intrusion timeline from disk, memory and log artefacts in a prepared case. |
| `CYB-M09` | Malware analysis and reverse engineering fundamentals (isolated lab) | L3 | 16 | PLANNED | Triage a benign test sample statically and dynamically in an isolated VM and write detection logic. |
| `CYB-M10` | Cyber threat intelligence | L3 | 10 | PLANNED | Produce a STIX-formatted intelligence product from provided reporting with confidence levels. |
| `CYB-M11` | Red, blue and purple team operations (authorised, simulated) | L3 | 12 | PLANNED | Run a scoped adversary-emulation exercise in a lab and convert its gaps into validated detections. |
| `CYB-M12` | Security architecture, governance and leadership | L3 | 10 | PLANNED | Produce a zero-trust architecture proposal with a risk register and board-level summary. |
| `CYB-M13` | AI security and emerging threats | L3 | 8 | PLANNED | Assess an AI-enabled workflow against the OWASP LLM Top 10 and recommend controls. |
| `CYB-M14` | Capstone: assessed security programme exercise | L3 | 20 | PLANNED | Complete a multi-domain exercise with a graded technical report and an executive briefing. |
<!-- END GENERATED: modules -->

## 8. Build order and effort model (hypothesis)

1. **SOC-M01..M03** (unblock the pilot course; reuse the generator and evaluator).
2. **Level 0 foundations** (every pathway depends on it).
3. **PY-M01..M05**, then PY-AUTO (largest reuse).
4. **AI-ENG** (highest buyer interest hypothesis; labs must run on a free local model).
5. **GCP-DE, JQA, FE, OSINT, CYBER tracks.**

The pilot module took one focused build cycle including a lab engine, a synthetic-data generator, 136 repository tests and a student-edition pipeline. The reusable parts (generator patterns, evaluator discipline, build pipeline, design system) lower the cost of later modules, but **no per-module effort estimate has been measured** and none is promised here.

## 9. Risks and assumptions

| Risk | Impact | Mitigation |
|---|---|---|
| No SME has reviewed any content | Technical errors may remain | Gate G7 blocks release; reviewer names recorded in catalog |
| Source licensing unresolved (no `LICENSE` file) | Cannot ship legacy text; reuse limits unclear | `IP_AND_LICENSE_REVIEW.md`; new content is independently authored |
| Public repository | Instructor material exposed | Private-pack pattern, hygiene test that fails when instructor files are tracked |
| Synthetic labs may differ from real telemetry | Skills transfer gap | Document limits in each lab; add real-format samples under licence review |
| Version drift (ATT&CK, Python, JUnit, LLM Top 10) | Stale lessons | Versions in front matter; research register with dates |
| Time estimates unmeasured | Mispriced or mis-scheduled products | Learner pilot required before any duration is published |
