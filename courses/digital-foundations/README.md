# Digital and Technical Foundations — COURSE-FND-DIGITAL

**Release state: REENGINEERING.** Five instructional modules now have source assets; no complete course edition has passed TRAINING_CONTENT_GO. No Academy customer publication or commercial authorization.

| Module | Honest status | Learning content |
|---|---|---|
| FND-M01 | BUILT, unverified | [Operating systems, files and permissions](modules/FND-M01/lesson.md) with synthetic integrity and access exercises |
| FND-M02 | BUILT, unverified | [Command-line fundamentals](modules/FND-M02/lesson.md) with safe local diagnostic CLI |
| FND-M03 | BUILT, unverified | [Networking and HTTP basics](modules/FND-M03/lesson.md) with controlled TCP/HTTP loopback |
| FND-M04 | Candidate, incomplete | [Git and GitHub workflow](modules/FND-M04/lesson.md); local Git labs exist, **hosted practice PR still unverified**, so catalog remains PLANNED |
| FND-M05 | BUILT, unverified | [Programming fundamentals with Python](modules/FND-M05/lesson.md), 16-check ticket-summary guided reference and independent queue-summary learner starter |
| FND-M06 | PLANNED | Troubleshooting and safe computing; not implemented |

## FND-M05 hands-on path

Start with the [FND-M05 lesson](modules/FND-M05/lesson.md), then the [guided lab](modules/FND-M05/lab-guided/README.md). Execute the following in an unprivileged, disposable environment:
```text
python -m unittest discover -s courses/digital-foundations/modules/FND-M05/lab-guided/checks -p test_support_metrics.py -v
```
The guided reference works exclusively with invented local CSV files and does not perform real support-desk operations. Continue to the [independent lab](modules/FND-M05/lab-independent/README.md) and implement the intentionally incomplete starter without weakening tests. This is how learner skill will eventually be evaluated; the reference tests alone do not prove mastery.

## Quality and commercial release limits

All source-free Foundation lessons use explicit original provenance rather than fabricating source-PDF citations. Student preview configurations in [student/](student/) are only build inputs. They do not constitute finished, accessible, downloadable or approved course PDFs. Source material from other tracks is unchanged.

FND-M04's real hosted-PR objective remains unverified; FND-M06 and the complete capstone are outstanding. Execution matrices, final PDF generation, technical currency review, protected instructor tests, subject-matter/editorial reviews, actual learner pilots and owner acceptance must pass before Gate A. The unresolved public legacy-PDF privacy issue also remains a portfolio release blocker. Commercialization and Academy launch are separate future decisions.