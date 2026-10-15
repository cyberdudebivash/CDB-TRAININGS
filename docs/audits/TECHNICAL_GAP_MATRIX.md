# Technical Gap Matrix

> Generated from the forensic data and the findings register.

## Legend

- **ABSENT** - the probe matched nothing in the whole source (a definitive gap for that keyword family).
- **MENTIONED_ONLY** - matched on fewer than 5 pages: named, not taught.
- **PRESENT_BY_KEYWORD** - matched on 5+ pages: the topic is addressed somewhere; depth and correctness still need review (see findings).
- Probes are keyword families derived from section 7 of the mission directive. They can produce false negatives (for example an earlier SQL-parameterisation probe was corrected after a manual check); every ABSENT used in a finding was re-checked by reading.

## 1. Findings by dimension (all sources)

| Dimension | P0 | P1 | P2 | P3-P4 | Total |
|---|---:|---:|---:|---:|---:|
| Technical correctness and security | 2 | 6 | 11 | 0 | 19 |
| Hands-on practical effectiveness | 0 | 10 | 2 | 0 | 12 |
| Demonstrable professional outcomes | 0 | 3 | 5 | 1 | 9 |
| Assessment validity and rigor | 0 | 4 | 0 | 0 | 4 |
| Instructional clarity and sequencing | 0 | 2 | 4 | 1 | 7 |
| Technical currency and relevance | 0 | 4 | 4 | 1 | 9 |
| Accessibility and learner experience | 0 | 0 | 2 | 2 | 4 |
| Commercial product readiness | 2 | 2 | 2 | 2 | 8 |

## 2. Mandated-topic coverage by source

### SOC Analyst Survival Playbook (2026 Edition) - `SRC-SOC-PLAYBOOK`

- **ABSENT (5):** log_normalization, reporting, siem_query_languages, sysmon, windows_event_ids
- **MENTIONED_ONLY (6):** case_management (4), detection_engineering (2), ir_nist_800_61 (3), malware_analysis (3), mitre_attack (4), test_datasets (2)
- **PRESENT_BY_KEYWORD (3):** evidence_handling, sigma, threat_hunting

### Complete AI Training Bundle 2026 - `SRC-AI-BUNDLE`

- **ABSENT (6):** context_engineering, mcp, mitre_atlas, owasp_llm_top10, reranking, retrieval_evaluation
- **MENTIONED_ONLY (3):** eu_ai_act (2), iso_42001 (1), nist_ai_rmf (1)
- **PRESENT_BY_KEYWORD (11):** agent_workflows, cost_latency, embeddings, human_approval, llm_eval_suite, ml_fundamentals, model_evaluation, observability_tracing, prompt_injection, rag, tool_calling_structured_output

### CyberDudeBivash Python Engineering Handbook - `SRC-PY-HANDBOOK`

- **ABSENT (2):** packaging_pyproject, unittest_mock
- **MENTIONED_ONLY (5):** docs_tooling (2), linting_formatting (2), python_version_policy (3), sql_parameterization (3), type_hints (4)
- **PRESENT_BY_KEYWORD (9):** async, ci_cd, database, dependency_locking, logging, profiling, pytest, secure_coding, virtualenv

### CYBERDUDEBIVASH Python Automation Training - `SRC-PY-AUTOMATION`

- **ABSENT (0):** none
- **MENTIONED_ONLY (1):** file_locking_atomic (3)
- **PRESENT_BY_KEYWORD (12):** audit_logging, browser_automation, ci_cd, config_management, docker, idempotency, monitoring_alerting, pytest, retry_backoff, scheduling, secrets_handling, type_hints

### Java Automation Test Engineer - Real Time Job Training - `SRC-JAVA-AUTOTEST`

- **ABSENT (5):** docker_testcontainers, java_17_21, junit5, playwright_java, selenium4_features
- **MENTIONED_ONLY (0):** none
- **PRESENT_BY_KEYWORD (10):** ci_integration, flaky_tests, maven_gradle, page_object, parallel_execution, reporting, rest_assured, selenium, test_data, testng

### GCP Data Engineer Training - `SRC-GCP-DATAENG`

- **ABSENT (5):** biglake_iceberg, certification_alignment, dataform_dbt, dataplex_catalog, free_tier_sandbox
- **MENTIONED_ONLY (3):** cleanup_teardown (2), datastream_cdc (5), dlp_cmek_vpcsc (2)
- **PRESENT_BY_KEYWORD (10):** bigquery, cloud_storage, composer_airflow, cost_controls, data_quality, dataflow_beam, iam_least_privilege, partition_cluster, pubsub, terraform

### Internal Frontend Developer Onboarding Playbook - `SRC-FRONTEND-ONBOARD`

- **ABSENT (0):** none
- **MENTIONED_ONLY (5):** auth_concepts (1), css_layout (8), dependency_security (5), nextjs (1), security_xss_csp (1)
- **PRESENT_BY_KEYWORD (10):** accessibility_wcag, api_integration, code_review, error_handling, git_workflow, html_semantics, performance_cwv, react, testing, typescript

### Official CyberDudeBivash Mega Course 2026 (Parts 1 and 2) - `SRC-MEGA-P1`

- **ABSENT (0):** none
- **MENTIONED_ONLY (1):** answer_keys (3)
- **PRESENT_BY_KEYWORD (9):** iso_27001, lab_environment_spec, legal_authorisation, mitre_attack, nist_csf, owasp, siem, sigma_yara, zero_trust

### Official CyberDudeBivash Mega Course 2026 (Parts 1 and 2) - `SRC-MEGA-P2`

- **ABSENT (1):** answer_keys
- **MENTIONED_ONLY (1):** cti_stix (1)
- **PRESENT_BY_KEYWORD (7):** cloud_security, lab_environment_spec, legal_authorisation, mitre_attack, nist_csf, owasp, supply_chain_slsa

`SRC-OSINT-STARTER` has no text layer; its coverage was assessed visually (F-OSINT-001, F-OSINT-003): no research-planning, source-validation, evidence-handling, geolocation, chronology/confidence or legal-framework instruction exists.

## 3. Gap register (open P0/P1 findings)

| ID | Sev | Course | Gap | Evidence | Remediation |
|---|---|---|---|---|---|
| F-FE-001 | P0 | `COURSE-FE-ONBOARD` | Third-party personal data (name, personal e-mail, phone, city) in sample resumes | p. 357, p. 360 | NOT_STARTED |
| F-OSINT-002 | P0 | `COURSE-OSINT` | Proposes redistributing third-party tools under a 'CyberDudeBivash proprietary license' | p. 6, p. 7, p. 14 | NOT_STARTED |
| F-OSINT-003 | P0 | `COURSE-OSINT` | No lawful/ethical collection framework; instructs correlation with leaked data and alias tracking | p. 5, p. 7, p. 9, p. 11, p. 14 | PLANNED_IN_TRACK |
| F-PYH-001 | P0 | `COURSE-PY-ENG` | Agent 'math tool' evaluates model-controlled input with eval() | p. 585, p. 586 | NOT_STARTED |
| F-AI-001 | P1 | `COURSE-AI-ENG` | Flagship RAG lab does not run on the current LangChain stack | p. 400, p. 401, p. 403 | PLANNED_IN_TRACK |
| F-AI-002 | P1 | `COURSE-AI-ENG` | RAG lab safeguards are dead code: refusal path never fires and governance prompts are never loaded | p. 402, p. 404 | PLANNED_IN_TRACK |
| F-AI-003 | P1 | `COURSE-AI-ENG` | 'Agentic' safety lab implements none of the controls its README claims | p. 421, p. 424, p. 425, p. 426, p. 427 | PLANNED_IN_TRACK |
| F-AI-004 | P1 | `COURSE-AI-ENG` | Mandated LLM-security and RAG-evaluation topics are absent | document-wide scan | PLANNED_IN_TRACK |
| F-FE-002 | P1 | `COURSE-FE-ONBOARD` | 'INTERNAL' playbook describes undisclosed internal practices; provenance and applicability unverified | p. 1, p. 17 | NOT_STARTED |
| F-FE-003 | P1 | `COURSE-FE-ONBOARD` | No labs, capstone or runnable project; security coverage is a single page | p. 84 | PLANNED_IN_TRACK |
| F-GCP-001 | P1 | `COURSE-GCP-DE` | CI examples authenticate with a long-lived service-account JSON key | p. 179, p. 180 | PLANNED_IN_TRACK |
| F-GCP-002 | P1 | `COURSE-GCP-DE` | Billable labs have no cost estimate, opt-in, spending guard, free-tier path or cleanup | p. 163 | PLANNED_IN_TRACK |
| F-GCP-003 | P1 | `COURSE-GCP-DE` | 'Real-world projects' are four-bullet specifications without data, steps or acceptance criteria | p. 48, p. 49 | PLANNED_IN_TRACK |
| F-JAV-001 | P1 | `COURSE-JAVA-QA` | 709-page 'Real Time Job Training' contains no Java code | document-wide scan | PLANNED_IN_TRACK |
| F-JAV-002 | P1 | `COURSE-JAVA-QA` | Baseline and tooling out of date: Java 8/11/17 only; no JUnit 5/6, Selenium 4 features or Playwright Java | p. 22 | PLANNED_IN_TRACK |
| F-JAV-005 | P1 | `COURSE-JAVA-QA` | No rubrics, answer keys or graded labs | document-wide scan | PLANNED_IN_TRACK |
| F-MEGA-001 | P1 | `COURSE-CYBER-MEGA` | Part 1 promises 16 modules but delivers three; Part 2 numbering and titles conflict with Part 1 | p. 2, p. 7, p. 1496 | PLANNED_IN_TRACK |
| F-MEGA-002 | P1 | `COURSE-CYBER-MEGA` | Breadth without depth: ~81% of sections under 40 words; labs lack environment, data and verification | p. 15, p. 1449 | PLANNED_IN_TRACK |
| F-MEGA-003 | P1 | `COURSE-CYBER-MEGA` | Uncited breach statistics and an explicit job guarantee | p. 20, p. 38, p. 113, p. 250, p. 1748 | NOT_STARTED |
| F-MEGA-005 | P1 | `COURSE-CYBER-MEGA` | Offensive-security labs lack an authorised, isolated lab specification | p. 487, p. 488, p. 1685 | PLANNED_IN_TRACK |
| F-MEGA-007 | P1 | `COURSE-CYBER-MEGA` | No answer keys, rubrics or graded assessments across ~3,660 pages | document-wide scan | PLANNED_IN_TRACK |
| F-OSINT-001 | P1 | `COURSE-OSINT` | Document is a marketing brochure for a bundle, not a course; promised components are absent | p. 6, p. 7, p. 8, p. 22 | PLANNED_IN_TRACK |
| F-OSINT-004 | P1 | `COURSE-OSINT` | Internal go-to-market and SEO strategy embedded in customer-facing text | p. 10, p. 15, p. 16, p. 17, p. 20 | NOT_STARTED |
| F-OSINT-005 | P1 | `COURSE-OSINT` | Absolute or unsupported claims | p. 2, p. 3, p. 14, p. 18, p. 21 | NOT_STARTED |
| F-PYA-002 | P1 | `COURSE-PY-AUTO` | Non-linear structure: complete framework build precedes 'Volume 1 Starts Here'; repeated scaffolds | p. 200, p. 273, p. 502 | PLANNED_IN_TRACK |
| F-PYA-003 | P1 | `COURSE-PY-AUTO` | No executable companion repository, CI evidence or verified lab results | p. 200, p. 651 | PLANNED_IN_TRACK |
| F-PYA-005 | P1 | `COURSE-PY-AUTO` | Assessment is interview-question lists; no rubric-graded work | p. 474 | PLANNED_IN_TRACK |
| F-PYH-002 | P1 | `COURSE-PY-ENG` | Automation examples teach insecure credential, TLS, SSH and shell patterns without warnings | p. 163, p. 164, p. 168, p. 222, p. 252, p. 269, p. 373, p. 428 | NOT_STARTED |
| F-PYH-003 | P1 | `COURSE-PY-ENG` | Packaging taught as `python setup.py sdist`; no pyproject.toml or build workflow | p. 63, p. 64 | NOT_STARTED |
| F-PYH-007 | P1 | `COURSE-PY-ENG` | No graded assessment, rubric or capstone acceptance criteria | document-wide scan | PLANNED_IN_TRACK |
| F-SOC-001 | P1 | `COURSE-SOC` | Six-phase IR lifecycle attributed to NIST SP 800-61 Rev. 3 / Rev. 2 | p. 6, p. 30 | DONE_IN_PILOT |
| F-SOC-004 | P1 | `COURSE-SOC` | Example brute-force correlation rule cannot detect password spraying | p. 17, p. 22 | DONE_IN_PILOT |
| F-SOC-005 | P1 | `COURSE-SOC` | Uncited statistics, salary bands and workforce numbers presented as 2026 benchmarks | p. 3, p. 11, p. 25, p. 28, p. 36, p. 37, p. 39 | NOT_STARTED |
| F-SOC-009 | P1 | `COURSE-SOC` | No executable labs, datasets, assessments or capstone | p. 17, p. 22 | DONE_IN_PILOT |
| F-SOC-010 | P1 | `COURSE-SOC` | Core SOC topics absent: Windows event IDs, Sysmon, SIEM query languages, log normalisation, reporting | document-wide scan | PLANNED_IN_TRACK |
