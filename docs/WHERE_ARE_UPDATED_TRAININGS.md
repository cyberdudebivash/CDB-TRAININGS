# Location of modernized training content (2026-10-15)

This is a location and integrity report, not a commercial release statement.

## Where to find modernized lessons

- Python Engineering: [seven completed lesson modules](../courses/python-engineering/modules/), numbered PY-M01 to PY-M07, with guided and independent labs, quizzes and rubrics.
- SOC Analyst: [SOC-M04 pilot lesson](../courses/soc-analyst/lessons/m04-auth-detection/lesson.md) and [its guided lab](../courses/soc-analyst/labs/m04-guided/README.md).
- PY-M08: [database persistence guided lab](../courses/python-engineering/modules/PY-M08/lab-guided/README.md) added after earlier reports; this is NOT the finished PY-M08 module.
- Other courses: [catalog and planned pathways](../catalog/courses.yaml). Their full modernized teaching packages are not implemented.

## What happened to the PDFs?

The 10 root-level PDF files are unchanged legacy source material. They have NOT been upgraded or replaced with October 2026 complete-course PDF editions.

Previous Claude builds of eight module-level student previews were made into the local ignored dist directory and described in [PDF release integrity](production/PDF_RELEASE_INTEGRITY.md); no PDF binaries are version-controlled or published as GitHub Release assets.

A module preview is not a complete course edition and is NOT customer approved.

## Generate current module preview PDFs from the repository

Install dependencies listed in requirements.txt and the external build tools pandoc, Chromium, pdfinfo and pdftotext. From the repository root:

    python scripts/build/build_all_student_previews.py --list
    python scripts/build/build_all_student_previews.py

Or generate one module:

    python scripts/build/build_all_student_previews.py --only PY-M05

Outputs: local ignored dist folder with individual module PDF previews, manifest files and module-preview-build-report.json. The batch script demands strict PDF rendering and SHA-256 manifest parity; failed, missing or stale outputs are reported as failures.

The batch build DOES NOT change the original PDFs, finish any unbuilt lesson, or certify Academy readiness.

## Acceptance and security

- [Course completeness matrix](production/COURSE_COMPLETENESS_MATRIX.md)
- [Training content acceptance report](production/TRAINING_CONTENT_GO_REPORT.md)
- [Open defects and owner actions](production/REMAINING_DEFECTS.md)
- [Execution handoff](production/EXECUTION_CONTINUITY.md)

No complete modernized course edition is approved. The frontend legacy PDF has an unresolved privacy incident in the public repository, so it must not be redistributed until owner-approved containment is complete. Legal rights, human reviews, instructor-pack storage and October 24 final technical refresh also remain open. Commercialization and Academy deployment follow only after the appropriate content release gate.
