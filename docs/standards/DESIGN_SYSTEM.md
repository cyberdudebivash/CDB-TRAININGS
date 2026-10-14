# Design System

Scope: learner-facing documents (student editions, lab handouts, rubrics) and the visual rules that future web or app surfaces of the Academy should reuse. Files: `shared/design/tokens.json`, `shared/design/cdb-academy.css`, `scripts/validation/check_contrast.py`, `scripts/build/build_student_edition.py`.

This repository contains **no website or application UI**. This design system therefore governs generated documents; the same tokens are intended to be the starting point for web surfaces, which would need their own testing.

## 1. Principles

| Principle | Rule | How it is enforced |
|---|---|---|
| Mobile-first | Single column, 16 px gutters, no horizontal page scroll at 360 px; wide tables scroll inside their own container | 360 px overflow probe in the build |
| Accessible | WCAG 2.2 AA target; body text at AAA contrast; visible focus; no colour-only meaning; one `h1`, no skipped heading levels; table header cells; `lang` and `title` set | `check_contrast.py`; `check_html()` in the build |
| Readable | Line length ≤ 76ch; system fonts; 1.6 line height; code wraps on print instead of clipping | stylesheet |
| Fast and private | No web fonts, scripts, trackers or CDN assets; one self-contained HTML file with inline CSS | `test_full_build_passes_all_checks` asserts the HTML has no script, link, iframe, external `src` or CSS import; the build rejects insecure `http://` references |
| Theme-aware | Light and dark token sets, `prefers-color-scheme`, `prefers-reduced-motion` respected | stylesheet; contrast checked for both themes |
| Print-safe | A4 page box, page numbers, headings kept with content, tagged PDF with bookmarks | `check_pdf()` in strict mode |
| Honest | Pilot or draft status is shown in a visible notice, never hidden | forbidden-marker and expected-text gates |

## 2. Tokens

`tokens.json` is the source. Each theme defines: `bg`, `surface`, `text`, `muted`, `primary`, `primary_on`, `success`, `warning`, `danger`, `border`, `code_bg`, `code_text`. A `pairs` list names every foreground/background combination the system uses with its **minimum contrast ratio** and purpose.

`cdb-academy.css` redeclares the same values as CSS custom properties; `tests/test_design_system.py` fails if the two drift.

### Contrast gates (both themes, 12 pairs each)

| Pair | Minimum | Use |
|---|---:|---|
| text on bg, text on surface | 7.0 | body text and panels (AAA) |
| muted on bg / surface | 4.5 | secondary text |
| primary on bg / surface | 4.5 | links |
| primary_on on primary | 4.5 | buttons, badges |
| success / warning / danger on bg | 4.5 | status text |
| code_text on code_bg | 7.0 | code blocks |
| border on bg | 3.0 | component boundaries (WCAG 1.4.11) |

Status is always shown with **text and an icon-free label** ("Passed", "Needs work"), never colour alone.

## 3. Components in the stylesheet

| Component | Class / element | Notes |
|---|---|---|
| Skip link | `.skip` | first focusable element |
| Page frame | `header.doc`, `main`, `footer.doc` | one `main` per document |
| Table of contents | `nav.toc` | generated from sections |
| Notice | `.notice` | pilot/draft/safety banners; warning colour plus bold label |
| Meta line | `.meta` | version, date, build info |
| Tables | `.table-wrap > table` | horizontal scroll inside the wrapper only |
| Code | `pre > code`, inline `code` | monospaced system stack, wraps in print |
| Quote / callout | `blockquote` | left rule + surface background |

## 4. The student-edition build

`scripts/build/build_student_edition.py --strict` turns the files listed in `courses/<course>/student/student-edition.yaml` into one HTML file and one PDF under `dist/` (git-ignored). Gates, all of which fail the build:

| Stage | Gate |
|---|---|
| Source safety | No included path contains `/instructor/`, `answer-key`, `grading-notes`, `/solution/`; no included file contains an instructor marker |
| HTML structure | `lang`, `title`, viewport, exactly one `main` and one `h1`, no heading level skipped, unique ids, internal links resolve, tables have header cells, links have text, images have alt text, no insecure `http://` |
| Mobile | No horizontal overflow at 360 px (measured in headless Chromium inside a 360 px iframe) |
| PDF | Title metadata correct, fonts embedded, no near-blank pages, expected text present, forbidden markers absent |
| PDF (strict) | Tagged PDF; bookmark outline present |

Recorded result of the current pilot build: see `docs/release/AUTOMATED_QA_REPORT.md` (the build is one of its checks).

## 5. Limits of the evidence

- Contrast is computed from tokens; rendered pages were inspected visually once, not systematically across devices.
- No screen-reader walkthrough (NVDA, VoiceOver, TalkBack) has been performed; tagged-PDF structure is checked mechanically only.
- Print and PDF were produced and checked with one browser engine.
- Touch-target sizing and form patterns are not covered because the system contains no interactive components yet.

Closing these gaps is a condition for claiming WCAG conformance for any product; until then the documents state a **target**, not a conformance claim.

## 6. Adding a component

1. Add tokens (both themes) and a `pairs` entry with its minimum contrast.
2. Add CSS using only custom properties.
3. Show it in a build fixture and extend `check_html()` if it carries structure that can be validated.
4. Run `pytest` (design-system drift and contrast tests) and `scripts/validation/run_qa.py`.
