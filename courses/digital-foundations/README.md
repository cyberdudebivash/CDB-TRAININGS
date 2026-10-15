# Digital and Technical Foundations — COURSE-FND-DIGITAL

**Status: REENGINEERING — no complete course edition has Gate A approval.** Three of six modules contain authored instruction, but human SME review, learner trials, complete curriculum, privacy/IP gates, and the final course PDF are still required.

| Module | Status | Learning artifacts |
|---|---|---|
| FND-M01 — Operating systems | Built, unverified | [Lesson](modules/FND-M01/lesson.md), guided file-integrity lab, access-policy learner starter, assessment |
| FND-M02 — Command lines | Built, unverified | [Lesson](modules/FND-M02/lesson.md), guided synthetic event CLI, independent transcript parser, assessment |
| FND-M03 — Networking/HTTP | Built, unverified | [Lesson](modules/FND-M03/lesson.md), **live controlled loopback TCP/HTTP** lab, synthetic protocol-failure classifier, assessment |
| FND-M04 — Git and GitHub | Candidate, incomplete | [Git lesson](modules/FND-M04/lesson.md), genuine local Git branches/conflict-resolution lab, unverified external PR objective |
| FND-M05–M06 | Planned | Python programming, troubleshooting and safe computing |

## Learner path and operational exercises

Begin with [FND-M01](modules/FND-M01/lesson.md), then [FND-M02](modules/FND-M02/lesson.md), followed by [FND-M03](modules/FND-M03/lesson.md). The lesson explains exactly what an exercise proves and what it does not.

**FND-M03 guided exercise** (no external hosts, customer accounts, DNS lookups, TLS session or cloud charges):

```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M03/lab-guided/checks -p test_http_trace.py -v
```

The lab starts a local HTTP/1.1 service bound to `127.0.0.1` and an ephemeral TCP port. It tests 200/404 responses, request boundaries and cleanup. Its independent lab contains deliberately incomplete starter code which learners must implement against public tests. Real external packet capture is **not** part of this module.

## PDF and customer readiness

Student PDF preview **configurations** are under [student](student/), not proof of successfully generated or commercially approved PDFs. A local review preview may be shared only as an unapproved draft. The repository's strict renderer, qualified reviewer and actual learner pilot must still pass.

The six-module Foundations course, original 2025 PDF modernization elsewhere in the portfolio, and the Academy production experience are not complete. The training-content gate is separate from commercial and Academy-live gates. Instructor answer keys and customer information must not be exposed through this public repository.
