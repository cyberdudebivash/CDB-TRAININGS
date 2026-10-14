# Source Provenance

Provenance records **where each source came from, how it reached this repository, and what is and is not known about its
authorship and rights.** Unknowns are stated as unknowns.

## 1. Repository facts (verified 2026-10-14)

| Fact | Value | Source |
|---|---|---|
| Repository | `cyberdudebivash/CDB-TRAININGS` | GitHub repository metadata |
| **Visibility** | **public** | GitHub search API (`private: false`) |
| Created | 2026-10-14 06:20 UTC | GitHub metadata |
| Default branch | `main` | GitHub metadata |
| Baseline commit audited | `f2ba7d0e3448a83dee1230d6b16a985076dcb059` | `git rev-parse HEAD` at session start |
| LICENSE / README / CONTRIBUTING | none present | `ls` at baseline |
| Git LFS | not used | `.gitattributes` absent, no pointer files |

Because the repository is **public**, all ten PDFs - including the one with third-party personal data (F-FE-001) - are
already readable by anyone. Anything committed on top of them is public too; instructor-only material is therefore kept
out of this repository (see `docs/architecture/ASSESSMENT_FRAMEWORK.md`).

## 2. How each file entered the repository

All ten files were added through GitHub web uploads ("Add files via upload") on 2026-10-14, one commit per file, in this order:

| Order | Commit | Source ID | File |
|---:|---|---|---|
| 1 | `403a42c` | `SRC-AI-BUNDLE` | Complete AI Training Bundle 2026.pdf |
| 2 | `c96bac3` | `SRC-PY-HANDBOOK` | CyberDudeBivash Python Engineering Handbook.pdf |
| 3 | `d3eb1b6` | `SRC-JAVA-AUTOTEST` | CyberDudeBivash_Java_Automation_Test_Engineer_Real_Time_Job_Training.pdf |
| 4 | `ba95f2d` | `SRC-OSINT-STARTER` | CyberDudeBivash_OSINT_Starter_Bundle_FULL.pdf |
| 5 | `a2d097b` | `SRC-PY-AUTOMATION` | CYBERDUDEBIVASH-PYTHON-AUTOMATION-TRAINING.pdf |
| 6 | `5c8e0b9` | `SRC-GCP-DATAENG` | GCP-DATA-ENGINEER-TRAINING.pdf |
| 7 | `9e9141c` | `SRC-FRONTEND-ONBOARD` | INTERNAL FRONTEND DEVELOPER ONBOARDING PLAYBOOK.pdf |
| 8 | `080b0a5` | `SRC-MEGA-P1` | OFFICIAL_CYBERDUDEBIVASH_MEGA_COURSE_2026_Part_1.pdf |
| 9 | `3f334b7` | `SRC-MEGA-P2` | OFFICIAL_CYBERDUDEBIVASH_MEGA_COURSE_2026_Part_2.pdf |
| 10 | `f2ba7d0` | `SRC-SOC-PLAYBOOK` | SOC Analyst Survival Playbook (2026 Edition).pdf |

The upload date is **not** the authoring date. The earlier commit `403a42c` referenced in the mission directive is the
AI bundle upload and is preserved in history. The originals have not been moved, renamed or modified by this work.

## 3. What the files themselves say about origin

| Source ID | Producer / tool | Embedded date | Metadata title | In-document authorship or date statements |
|---|---|---|---|---|
| `SRC-AI-BUNDLE` | Google Docs export (Skia/PDF m146) | none | "Book report" | none found |
| `SRC-PY-HANDBOOK` | Google Docs export (Skia/PDF m144) | none | "Book report" | none found |
| `SRC-JAVA-AUTOTEST` | Google Docs export (Skia/PDF m145) | none | "Class notes" | one copyright / all-rights-reserved line |
| `SRC-OSINT-STARTER` | text-to-PDF web service + pdf-lib | created 2025-09-03, modified same day | path of a temporary `.txt` upload | brand statements only; text is a blog/SEO draft (p. 22) |
| `SRC-PY-AUTOMATION` | Google Docs export (Skia/PDF m145) | none | "Class notes" | "Date: 22-12-2025" (p. 2) |
| `SRC-GCP-DATAENG` | Google Docs export (Skia/PDF m153) | none | "Project proposal" | none found |
| `SRC-FRONTEND-ONBOARD` | Google Docs export (Skia/PDF m146) | none | "Untitled document" | presented as an "internal" playbook (pp. 1, 17) |
| `SRC-MEGA-P1` | Google Docs export (Skia/PDF m144) | none | "Book report" | "Pvt Ltd" attribution appears 51 times, e.g. "FROM: CyberDudeBivash Pvt Ltd | Global Cybersecurity Ecosystem - Authorized Mega-Curriculum" (p. 16) |
| `SRC-MEGA-P2` | Google Docs export (Skia/PDF m144) | none | "Book report" | none found |
| `SRC-SOC-PLAYBOOK` | Google Docs export (Skia/PDF m146) | "January 2026" in section headers | "Report" | "Built by CyberDudeBivash - Cybersecurity researcher & AI engineer"; (c) 2026 CyberDudeBivash Pvt. Ltd. (p. 42) |

Metadata titles ("Book report", "Class notes", "Project proposal", "Report") are Google Docs template names. They are
search-engine-visible and unprofessional; regenerated artefacts must carry real titles (design system requirement).

## 4. Authorship, originality and tooling - what is unknown

- **Authors and contributors** are not named in any document other than the brand. Whether text was written by hand,
  drafted with AI assistance, or adapted from third-party material is **unknown**. Stylistic signals (uniform emoji
  headings, repeated template sections, marketing voice) are consistent with templated generation but are **not proof**
  and no such conclusion is drawn.
- **Cross-document copying** is not evident: at most 4 shared long lines between any two documents.
- **Third-party derivation** is stated in the SOC playbook (adapted from Dropzone AI, Radiant Security, Prophet, Fortinet,
  Stellar Cyber, DNIF; pp. 14, 20, 23) and is otherwise untested; no external similarity search was possible.
- **Images**: the Google-Docs PDFs embed many small raster images (mostly emoji glyphs) and no credits; the OSINT cover is a
  1536x1024 raster with no licence or credit. Rights are NEEDS_VERIFICATION.

## 5. Preservation commitments

1. The ten PDFs stay byte-identical at the repository root until the owner chooses to move them; SHA-256 values are in
   `SOURCE_INVENTORY.md`. A future relocation to `sources/original/` must be a pure rename verified against these hashes.
2. Extracted text is never committed (it is cached under `.work/`, git-ignored). Evidence files contain only short quoted
   snippets with page references.
3. New curriculum content is written as original Markdown/YAML/code with a source-to-new-content trace in
   `courses/<slug>/curriculum/source-map.yaml` (built for the pilot; planned for the other courses).
4. Findings reference the sources by `SRC-*` ID and PDF page number so any statement can be re-checked against the preserved file.
