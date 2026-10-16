# CYBERDUDEBIVASH — Python Engineering flagship enterprise pilot

**Classification:** ENGINEERING WORK PRODUCT / INTERNAL PRE-RELEASE PILOT. **Not a customer launch, completed certificate, verified commercial offer, or deployed Academy service.**

## Executive decision based on recorded Gate A evidence

The portfolio has 10 catalog courses. As of the committed Gate A snapshot on October 16, Python Engineering is the **closest to content release**: 13 of 13 modules implemented, 25 of 25 labs reported executable, 10 of 10 operational scenarios verified, and 654 of 654 source pages dispositioned. The whole-course **preview** build manifest records 397 pages and a score of 89.7/100. The 397-page PDF binary is **not part of the GitHub release and is not being claimed as a downloadable final edition**.

Gate A remains BLOCKED, including A04 (the October 24 technical refresh), A11 (rights), A13 (private instructor pack custody), A14 (final approved edition), A16 (open P1 defects), and A17–A19 (human SME/editorial/pilot/owner approval). No human reviews may be fabricated. The source PDF privacy P0 incident elsewhere in this public repository must be contained by an authorized owner action; neither this pilot nor automation can fix the Git history exposure.

## Product-level requirements for Fortune 500 consideration

1. **Defensible skill outcomes:** task-based evidence for each required course objective and capstone, not reading/viewing time or quiz scores alone. The 13 Python Engineering module outcome maps and 25 planned labs provide the starting curriculum.
2. **Authentic operations:** exercises operate on actual local files/processes and repeatable synthetic security incidents. Only call a case LIVE when the system actually observes it; local simulation and in-process HTTP do not verify production infrastructure.
3. **Assessment separation:** student materials contain no instructor keys. Grading rubric, hidden checks and detailed model answer packs must be held in private, owner-controlled storage before customer pilots.
4. **Tenant isolation and privacy:** separated cohorts, role-scoped enrollment/assessment, pseudonymous learner IDs, bounded metadata and non-PII artifact digests. Real identities need separate consent, retention and processor agreements and a security review.
5. **Evidence quality:** course version, submitted artifact fingerprint, reviewer ID, immutable grade and tamper-evident audit-anchor export. Local hash chaining detects unsophisticated modification; it is **not a digital signature** and must be independently anchored to reduce privileged rewrite risk.
6. **Release integrity:** the current preview cannot be renamed FINAL. Gate A is independent from Gate B customer sales/fulfillment and Gate C Academy live operations. An automated pass never substitutes for qualified reviewers or an owner rights decision.
7. **Enterprise pilot feedback:** at least one genuine participant performs the complete capstone in a controlled environment; measure completion time, independent rubric scores, ambiguity, retry rates, failure remediation and accessibility barriers. Keep separate signed instructor observations.
8. **Operational support:** before deployment require auth, SSO/OIDC, tenant provisioning, secure backup/restore, access/revocation logs, encryption controls, retention periods, incident response, WCAG checks, monitoring/SLOs, scaling and data-residency decisions. None of these are falsely claimed by the offline pilot.

## Delivered offline pilot control plane

`pilot_ledger.py` is a real SQLite-backed, **local-only** executable component for demonstration. It supports tenant-scoped cohorts and enrollment, instructor cohort assignment, learner artifact-submission digests, API-level immutable grading, fail-closed progress status, event chaining, and audit-to-SQLite-state reconciliation. The read path rejects materialized grades, submissions and cohort settings that disagree with their event history, but does not protect against privileged rewriting of both history and state. See [Integrity reconciliation and limitations](PILOT_LEDGER_INTEGRITY_RECONCILIATION_20261016.md). It is tested with positive and negative controls, including cross-tenant and role-abuse probes. The `bootstrap_tenant` method is **trusted-operator only**, with no independent authentication. Do not wrap these methods in a network API or use real customer records.

### Reproduce without paid services

From the repository root:

```text
python -m unittest discover -s tests -p 'test_enterprise_*' -v
PYTHONPATH=scripts python scripts/enterprise/demo_pilot.py --output /tmp/cdb_training_pilot.json
python scripts/enterprise/release_preflight.py --course COURSE-PY-ENG --format markdown
```

The first command exercises the local state machine. The second creates a concrete, synthetic pilot run with **three graded artifacts** and an exported audit-chain fingerprint. The last command **must exit nonzero**, because the course is not release-authorized. Use `--report-only` only for diagnostic reporting, never in a production release-enforcement job. No source PDF, student grade, rights decision or human signoff is changed.

### Pilot evidence contract

| Field | Evidence | Does **not** prove |
|---|---|---|
| tenant / cohort / course version | Isolated offline record namespace | Federated enterprise identity, customer isolation at API boundary |
| submitted SHA-256 | Fingerprint string supplied by learner | Trustworthy file acquisition or correctness of the artifact |
| grading | Immutable instructor-entered 0–100 result | Qualified reviewer, calibration, hidden test execution |
| audit anchor | Checked append-only hash chain in a single local database | Third-party timestamp or cryptographically signed ledger |
| progress status | All defined pilot tasks graded at/above configured threshold | Whole-course competence, final certification or Gate A success |

## Critical path, sequenced by leverage

**P0:** Owner handles public-source privacy containment, rights/copyright and instructor private storage. No automated substitution.

**P1:** Finalize Python Engineering course-level assessment and a genuine learner pilot. Calibrate rubric thresholds with actual human work. Conduct SME/editorial and accessible course-PDF review. Re-run exact source-bound Linux matrix and supported-OS tests, including negative controls and privacy.

**P2:** Execute the already-mandated October 24 currency refresh on or after October 24, verify all pending P1 remediations against recorded evidence, and require a strictly built FINAL course PDF with public/private asset separation.

**P3:** Build Gate B (pricing, signed rights terms, Razorpay checkout, refunds, taxes, fulfillment) and Gate C (actual Academy auth, enrollment, secure storage, support/SLA, delivery observability) only after the independent prerequisites are satisfied.

**Success is defined by a verified, customer-usable final course with independent learner evidence, not by the number of Markdown files or PRs.**
