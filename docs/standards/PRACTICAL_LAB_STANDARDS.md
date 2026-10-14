# Practical Lab Standards

Applies to every lab in every course. The reference implementation is `courses/soc-analyst/labs/` (SOC-M04). A lab that violates a MUST rule cannot be counted in `lab_coverage.built`.

Keywords: **MUST**, **SHOULD**, **MAY** as in RFC 2119.

## 1. Principles

1. **Local-first and free.** A core lab MUST run on a learner's laptop with open-source tools and no paid account. Cloud or hosted-model labs MAY exist only as optional extensions (section 7).
2. **Deterministic.** Given a published seed, the lab data MUST be byte-identical across runs on the supported interpreter. Golden hashes in tests catch drift.
3. **Synthetic by default.** Data MUST be generated, not scraped from real people, customers or systems. Network addresses use reserved documentation ranges (RFC 5737, RFC 1918, RFC 6598) and the `.example` family of names.
4. **Verifiable.** Every lab MUST have commands that decide pass or fail without a human, and expected outputs quoted in the README MUST be asserted by a test (docs-as-tests).
5. **Fail closed.** Evaluators MUST reject unsupported input with a clear error instead of silently ignoring it (the pilot's `sigma_lite` raises `RuleError` for any unsupported modifier, timeframe or correlation type).
6. **Honest scoring.** Scores MUST be measured on labelled data. A fix that hides true positives MUST be reported as such (the pilot reports suppressed true positives).
7. **Safe.** Security content MUST stay inside an isolated, authorised, synthetic environment (section 6).

## 2. Lab specification

Every lab is documented with `shared/templates/lab-spec-template.md`. Required sections:

| Section | Requirement |
|---|---|
| Header table | Module and outcomes, level, planning duration, **cost** (must read `$0` or state the opt-in), lab state |
| Objective | One observable result |
| Prerequisites and environment | Tools **with versions**, OS, disk, network needs |
| Security boundaries | What the lab must never do and how it is enforced |
| Setup | Exact commands that work from a fresh clone |
| Input data | How generated, seed, size, ground-truth location |
| Steps | Each with expected output |
| Verification | Commands that decide pass/fail |
| Troubleshooting | At least the failures seen in testing |
| Cleanup | Removes everything created |
| Assessment | Link to the rubric |

## 3. Lab states

| State | Meaning | May count as verified |
|---|---|---|
| `VERIFIED_EXECUTABLE` | Automated check passed in the recorded QA run | yes |
| `VERIFIED_MANUAL` | A named person executed it and recorded results | only with the record |
| `UNVERIFIED` | Built but not run | no |
| `BLOCKED_ENVIRONMENT` | Needs a tool or platform not available | no |
| `BLOCKED_COST` | Needs spending not approved | no |
| `BLOCKED_SECURITY` | Needs an isolated environment not yet provisioned | no |
| `PLANNED` | Specified only | no |

`run_qa.py` is the only thing that should move a lab to `VERIFIED_EXECUTABLE`. State changes made by hand are rejected in review.

## 4. Guided and independent labs

| | Guided | Independent |
|---|---|---|
| Data | Practice seed (published) | Different seed and scenarios (published seed for practice; held-out seed for assessment is a private option) |
| Starter | Templates that fail until completed | None, only the success criteria |
| Solution | Public reference solution allowed (learning aid) | **Never public** — instructor pack only |
| Feedback | Immediate, step by step | Measured results against the rubric |
| Purpose | Learn the technique | Show the technique transfers |

Starter templates MUST fail closed: a learner who forgets to edit a template MUST get an error, not a pass (tested in `test_guided_lab.py`).

## 5. Datasets

- Include a **ground-truth file** stored separately from the learner-visible data, with a scenario list that distinguishes attacks, benign noise and hard cases.
- Include **hard negatives** (benign activity that looks malicious) and **hard positives** (attacks that evade naive rules). The pilot has a stale service credential, an authorised scanner and a shared NAT as hard negatives, and low-and-slow distributed spraying as a hard positive.
- Record generation parameters in code, not prose. Document the dataset's limits (synthetic, simplified).
- Never embed real credentials, real personal data, or real customer logs. `tests/test_repo_hygiene.py` scans for secrets and third-party personal data.

## 6. Security content rules

1. Offensive demonstrations run only against local, disposable, deliberately vulnerable targets that the course provisions, with explicit scope text in the lab.
2. No lab instructs scanning, exploiting, scraping or social-engineering any third party's system or person.
3. Malware-analysis labs use benign test samples, in an isolated VM without bridged networking, with snapshot-and-revert instructions.
4. OSINT labs use synthetic or consented cases; the lawful-collection checklist (OSINT-M01) is a prerequisite for every other OSINT lab.
5. Defensive artefacts a lab produces (rules, hardening scripts) are tested for false positives on benign data.

## 7. Cost and cloud rules

A lab that can incur cost MUST:

1. State an **estimate** and the free local alternative first (for example Beam DirectRunner, emulators, DuckDB for BigQuery-style SQL, a local open-weights model for LLM labs).
2. Require an **explicit opt-in** step and a **budget alert** before the first billable resource.
3. Use **short-lived identity** (Workload Identity Federation / OIDC); long-lived service-account keys are prohibited.
4. Provide a **teardown** script and a verification command that proves nothing billable remains.
5. Be marked `BLOCKED_COST` in the catalog until the owner approves spending.

No lab in this repository currently needs cloud spending; none has been authorised.

## 8. Reproducibility

- Pin dependencies (`labs/requirements.txt` uses exact versions). State the supported interpreter and what changes on others.
- Provide one command to run everything; use Python modules or Makefile targets, not copy-paste shell chains.
- Outputs are written to a learner-chosen directory, never into the source tree.
- The README's command examples are executed by tests wherever practical.

## 9. Lab review checklist

- [ ] Outcome is observable and appears in `curriculum/outcomes.yaml`
- [ ] Fresh-clone setup works as written
- [ ] Data deterministic; golden hash recorded
- [ ] Ground truth separate; hard negatives and positives present
- [ ] Starter fails closed; solution not in public files for independent labs
- [ ] Expected outputs in README are asserted by tests
- [ ] Unsupported input rejected with a clear message
- [ ] Security boundaries stated and enforced; no third-party targets
- [ ] Cost is `$0` or opt-in with teardown
- [ ] Rubric published; automated criteria are measurable
- [ ] Added to the QA run; lab state set by the run
