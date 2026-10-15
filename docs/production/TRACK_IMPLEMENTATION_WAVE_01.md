# Wave 01 — Missing Course Pathways: Real Starter Implementations

**Classification:** Operational starter labs; NOT complete curricula, NOT final PDFs, NOT Gate A acceptance.  
**Date:** 2026-10-15.

Previously only `python-engineering` and `soc-analyst` had built course folders. This implementation adds **eight** further catalog pathway directories, each with a runnable synthetic operational exercise, course-specific documentation and a narrow automated test contract. No legacy PDF was changed, and no catalog module has been marked `BUILT` solely because a starter exists.

| Course | Starter lab | Runtime | Contract emphasis |
|---|---|---|---|
| Digital Foundations | `file-integrity` | Python | Hashing, altered-file detection, symlink refusal |
| Python Automation | `reconciliation` | Python | Exact currency, deduplication, orphan detection |
| Java QA | `order-contract` | JDK 21+ | Boundaries, monetary rounding, invalid inputs |
| AI Engineering | `tool-approval` | Python | Allowlisted tools, scoped actions, human gate |
| OSINT | `source-provenance` | Python | Independent origins, conflicting claims, hashes |
| GCP Data Engineering | `batch-quality` | Python | Offline schema and record quality before cloud ingestion |
| Frontend Engineering | `form-contract` | Node.js | Safe field contracts and text-only DOM output |
| Cybersecurity Tracks | `auth-triage` | Python | Synthetic authentication event correlation |

## Local validation evidence

2026-10-15 development environment: Python 3.13.5, Node.js 22.16.0, javac 21.0.12.1. The authoring environment executed **53/53 narrow contract checks** (37 Python, 6 Node, 10 Java) and **15/15 integration test cases**. This is narrow unit-level evidence, not a clean-clone run of the entire existing portfolio test suite. Rerun in a clean clone before merge; versions and other OS support are NOT established by this evidence.

Run `python scripts/validation/run_starter_labs.py --strict` with all three runtimes installed. The runner outputs an actual execution report, fails on failed tests or missing runtimes in strict mode, and never counts an unexecuted test as a pass.

## Honest evidence boundaries

1. Unit tests demonstrate only each bounded implementation.
2. Neither the source PDFs nor full-course curricula were rewritten in this wave.
3. External service integrations, capstones, learner trials and qualified SME review remain unverified.
4. Portfolio `TRAINING_CONTENT_GO` stays **zero** until all applicable criteria pass.
5. The public Frontend PDF's privacy incident remains unresolved and requires authorized containment; do not copy sensitive contents into these labs.
6. No cloud spending, new SaaS, or customer data were used.

## Next production actions

For each new course, review the original source sections (when applicable), then implement the first complete catalog module with lesson, outcome mapping, source mapping, independent labs, eight-item assessment, detailed rubric and student preview build. Obtain technical currency evidence and attach content-bound test results before marking a module `BUILT`. Maintain separate commercial and Academy release gates.
