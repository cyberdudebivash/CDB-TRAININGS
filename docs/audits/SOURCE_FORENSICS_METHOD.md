# Source Forensics Method, Coverage and Limits

This document explains **how** the ten source PDFs were examined, what each method can and cannot prove, and which
corrections were made during the work. It exists so that every number in the audit set can be reproduced or challenged.

## 1. Review layers

| Layer | What it covers | Tooling | Strength of evidence |
|---|---|---|---|
| L1 Inventory | 10/10 files: SHA-256, size, pages, metadata, bookmarks, text-layer status | `pdfinfo`, `pypdf`, `scripts/inventory/build_inventory.py` | Deterministic |
| L2 Machine scan | 100% of text-layer pages (8,163 of 8,186): sections, depth, duplication, claims, currency, secrets, PII, URLs, topic probes, code syntax | `pdftotext`, `scripts/inventory/run_forensics.py` | Deterministic, but heuristic (see section 3) |
| L3 Targeted human reading | High-risk regions chosen by L2 plus whole small sources | Reading page text and rendered page images | Contextual judgement |
| L4 Primary-source verification | Claims checked against the standard, vendor documentation or an executed experiment | Downloaded PDFs, web pages, clean-venv execution | Strongest; recorded in `docs/research/research_register.yaml` |

## 2. Human-reading coverage (actual)

| Source | Pages read by a human reader in context | Notes |
|---|---:|---|
| `SRC-SOC-PLAYBOOK` | 43 / 43 | Whole text read. |
| `SRC-OSINT-STARTER` | 23 / 23 | Rendered and read visually (no text layer). |
| `SRC-AI-BUNDLE` | 29 / 937 | pp. 229-231, 294-296, 366-368, 400-404, 421-430, 777-781 + full outline. |
| `SRC-PY-HANDBOOK` | about 15 / 654 | Code-failure and security-hit contexts, pp. 63-64, 83, 163-164, 220, 427-428, 585-586. |
| `SRC-PY-AUTOMATION` | about 10 / 1,458 | Code-triage contexts and rendered p. 270. |
| `SRC-JAVA-AUTOTEST` | 2 / 709 | pp. 310-311 plus whole outline and strict absence scans. |
| `SRC-GCP-DATAENG` | 6 / 257 | pp. 17-19, 48-50 plus CI pages found by search. |
| `SRC-FRONTEND-ONBOARD` | about 3 / 441 | pp. 120-121 and the resume pages (values masked). |
| `SRC-MEGA-P1` | 9 / 2,837 | pp. 15-16, 487-488, 1449-1452, 1748 plus the TOC and module headings. |
| `SRC-MEGA-P2` | 6 / 827 | pp. 3-4, 12-13, 786-787 plus the outline. |

**This is not a line-by-line read of 569,045 words.** For the large sources the audit rests on complete machine scans,
complete outline analysis and targeted reading. Findings therefore describe what was *measured or read*; absence of a
finding is not evidence that a region is correct. Scores carry a confidence level for the same reason (`scores.yaml`).

## 3. Method details and known limits

**Text extraction.** `pdftotext -layout` per page. The OSINT PDF returns nothing (vector-outline text) and was read
visually. Zero-width characters from Google Docs are stripped.

**Section depth.** Each bookmark is located in its page's text; words up to the next bookmark are counted. Bookmarks in
these Google-Docs exports follow heading styles, so a "section" is a heading plus the body that follows. Short
sections are not defects by themselves; the finding is that *nearly all* sections are short and carry no worked
example, exercise or source.

**Code extraction and syntax checking.** The PDFs use proportional fonts, so code is detected heuristically (statement
patterns, bracket depth, docstring state). Python blocks are checked with `ast.parse`; Java blocks with `javalang`.
- A parse failure is only a *candidate* defect. All 39 remaining Python failures were triaged by hand: 4 are confirmed
  PDF line-wrap defects, 2 are `...` placeholders, the rest are extractor boundary cases (for example annotation-only
  class bodies).
- A parse success proves **syntax only**. No source snippet was executed except where a finding says EXECUTED.
- Java: strict absence scans found no Java code at all, so no Java blocks were checked.
- JavaScript/TypeScript (Frontend) and SQL/YAML were not parsed (no zero-cost parser configured): status NOT_CHECKED.

**Claim, currency, security, secret and PII patterns.** Regular expressions flag candidates; every hit used in a
finding was read in context. Secret scanning ignores obvious placeholders (all-`x` tokens). PII scanning never stores
raw values: counts, page numbers and irreversibly masked forms only.

**Topic probes.** Keyword families per course derived from section 7 of the mission directive. Zero matches are a
definitive gap for that keyword family; non-zero matches only show a mention.

**Duplication.** Normalised lines of 50+ characters within and across documents; headings compared after normalisation.
No similarity search against third-party corpora was possible, so external originality is NEEDS_VERIFICATION.

**External facts.** `PRIMARY_DOCUMENT_READ` entries (NIST SP 800-61r3, CSF 2.0, CERT-In Directions) were downloaded and
read. `OFFICIAL_PAGE_SUMMARY` entries went through a web-page summarising tool and were not cross-checked against raw
page text; they must be re-verified before customer-facing use.

## 4. Corrections made during the audit (kept for transparency)

1. **Indentation artefact.** First-pass code extraction reported 84 and 29 parse failures in the Automation and Handbook
   PDFs. Rendering the pages showed the indentation was correct; `pdftotext -layout` trims each page's left margin
   independently, destroying relative indentation across page breaks. Extraction was rebuilt on absolute x-coordinates
   (`pdftotext -bbox-layout`) and the counts fell to 31 and 7 (then triaged).
2. **Docstring scare.** A low-resolution render suggested `***` instead of `"""` in the AI Bundle. The text layer was
   correct; no finding was raised.
3. **Regex false positives.** `app.exec()` (Qt) and `model.eval()` (PyTorch) were flagged as `exec/eval`; the pattern now
   excludes attribute calls. A GitHub-token pattern matched a placeholder (`ghp_` + 36 `x`) in a `.env.example`; placeholders
   are now ignored and the hit is documented as a false positive.
4. **Probe false negative.** An SQL-parameterisation probe reported ABSENT although the Handbook uses `?` placeholders;
   the probe was corrected and the Handbook's SQL listed as a strength.
5. **PII handling.** An early forensic file contained a snippet with third-party contact details. It was removed from the
   (unpushed) local commit before publication and the scanner now stores only masked forms.

## 5. What was not done

- No OCR (none installed); no external plagiarism or similarity search.
- No execution of the sources' own code beyond the LangChain import test and the `utcnow()` check.
- No review by a qualified human subject-matter expert: **no course is SME-reviewed**.
- Ecosystem repositories and live Academy services were out of repository scope and were not inspected.
- Product-specific claims (FortiSIEM UI paths and rule names, Maltego CE / SpiderFoot HX licences, certification names) were
  not verified.

## 6. Reproducing the results

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # requires poppler-utils
.venv/bin/python scripts/inventory/build_inventory.py       # docs/audits/data/source_inventory.json
.venv/bin/python scripts/inventory/run_forensics.py         # docs/audits/data/forensics/*.json, cross_document.json
.venv/bin/python scripts/inventory/render_audits.py         # all generated audit documents
.venv/bin/python scripts/validation/validate_catalog.py     # catalog consistency
```

Outputs contain no timestamps, so a re-run on the same PDFs reproduces byte-identical files; `git diff` shows any drift.
