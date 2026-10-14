#!/usr/bin/env python3
"""Run the full forensic pass over every source PDF and write deterministic JSON evidence.

Outputs (tracked):   docs/audits/data/forensics/<SOURCE_ID>.json, docs/audits/data/cross_document.json
Outputs (git-ignored, contain source text for human triage): .work/code_failures/<SOURCE_ID>.json

Run:  .venv/bin/python scripts/inventory/run_forensics.py
"""
from __future__ import annotations

import json
import re
from collections import Counter

from common import DATA_DIR, SOURCE_IDS, WORK_DIR, extract_pages, extract_pages_xy, list_pdfs, read_outline, write_json
import forensics_lib as fx

CODE_LANGS_BY_SOURCE = {
    # Languages in which each source is expected to contain code (drives extraction).
    "SRC-PY-HANDBOOK": ["python"],
    "SRC-PY-AUTOMATION": ["python"],
    "SRC-AI-BUNDLE": ["python"],
    "SRC-GCP-DATAENG": ["python"],
    "SRC-FRONTEND-ONBOARD": [],  # JS/TS/CSS: no parser in the zero-cost toolchain; reported as NOT_CHECKED
    "SRC-JAVA-AUTOTEST": ["java"],
    "SRC-MEGA-P1": ["python"],
    "SRC-MEGA-P2": ["python"],
    "SRC-SOC-PLAYBOOK": [],
    "SRC-OSINT-STARTER": [],
}


def analyse(pdf) -> tuple[dict, dict, dict]:
    sid = SOURCE_IDS.get(pdf.name, "SRC-UNREGISTERED")
    pages = extract_pages(pdf)
    outline = read_outline(pdf)
    secs = fx.section_depth(pages, outline)
    record: dict = {"source_id": sid, "path": pdf.name, "pages": len(pages)}
    record["markdown_leakage"] = fx.markdown_leakage(pages)
    record["depth_profile"] = fx.depth_profile(secs)
    # Heading-level stubs: headings whose body is < 40 words (candidate "title-only" lessons).
    stubs = [s for s in secs if s.words < 40 and s.level <= 2]
    record["stub_sections_level_le_2"] = {"count": len(stubs), "of": sum(1 for s in secs if s.level <= 2)}
    record["claims"] = fx.scan(pages, fx.CLAIM_PATTERNS)
    currency = fx.scan(pages, {k: v[0] for k, v in fx.CURRENCY_PATTERNS.items()})
    for key, note in ((k, v[1]) for k, v in fx.CURRENCY_PATTERNS.items()):
        currency[key]["note"] = note
    record["currency_flags"] = currency
    record["secret_scan"] = fx.scan(pages, fx.SECRET_PATTERNS, flags=0, skip_placeholders=True)
    record["pii_scan"] = fx.scan_pii(pages)  # counts + masked forms only; raw values are never stored
    record["pedagogy_signals"] = fx.pedagogy_signals(outline, pages)
    record["urls"] = fx.top_urls(pages)
    record["topic_coverage"] = fx.coverage(pages, fx.COVERAGE_PROBES.get(sid, {}))
    fp = fx.line_fingerprints(pages)
    record["intra_duplication"] = fx.intra_duplication(fp)

    blocks = []
    langs = CODE_LANGS_BY_SOURCE.get(sid, [])
    xy_pages = extract_pages_xy(pdf) if langs else []  # absolute-indent text, see common.extract_pages_xy
    for lang in langs:
        blocks += fx.extract_python_blocks(xy_pages) if lang == "python" else fx.extract_java_blocks(xy_pages)
    ok = [b for b in blocks if b.status == "PARSE_OK"]
    bad = [b for b in blocks if b.status == "PARSE_FAIL"]
    err_kinds = Counter(re.sub(r"\(line \d+\)", "", b.error).strip()[:60] for b in bad)
    record["code"] = {
        "languages_checked": CODE_LANGS_BY_SOURCE.get(sid, []),
        "candidate_blocks": len(blocks),
        "parse_ok": len(ok),
        "parse_fail_candidates": len(bad),
        "lines_in_blocks": sum(b.n_lines for b in blocks),
        "top_parse_errors": err_kinds.most_common(6),
        "not_checked_reason": "no zero-cost parser configured" if not CODE_LANGS_BY_SOURCE.get(sid) else "",
    }
    py_blocks = [b for b in blocks if b.lang == "python"]
    record["python_security_patterns"] = fx.scan_code_blocks(py_blocks, fx.PY_SECURITY_PATTERNS) if py_blocks else {}
    # Persist block metadata (no source text) in tracked data; failures with text go to .work/.
    record["code_block_index"] = [
        {"page": b.page, "lang": b.lang, "lines": b.n_lines, "status": b.status, "first": b.first_line[:70]}
        for b in blocks
    ][:400]
    failures = {
        "source_id": sid,
        "failures": [
            {"page": b.page, "lang": b.lang, "lines": b.n_lines, "error": b.error, "text": b.text[:1800]} for b in bad
        ],
    }
    return record, {"fp": fp, "outline": outline}, failures


def main() -> None:
    (DATA_DIR / "forensics").mkdir(parents=True, exist_ok=True)
    (WORK_DIR / "code_failures").mkdir(parents=True, exist_ok=True)
    fps, outlines = {}, {}
    for pdf in list_pdfs():
        record, aux, failures = analyse(pdf)
        sid = record["source_id"]
        write_json(DATA_DIR / "forensics" / f"{sid}.json", record)
        (WORK_DIR / "code_failures" / f"{sid}.json").write_text(json.dumps(failures, ensure_ascii=False, indent=1), encoding="utf-8")
        fps[sid] = aux["fp"]
        outlines[sid] = aux["outline"]
        c = record["code"]
        print(
            f"{sid:22} depth_median={record['depth_profile'].get('median_words')!s:>4} "
            f"stubs={record['stub_sections_level_le_2']['count']:>4}/{record['stub_sections_level_le_2']['of']:<5} "
            f"dup={record['intra_duplication']['share_repeated']:<5} code_blocks={c['candidate_blocks']:>4} "
            f"ok={c['parse_ok']:>4} fail={c['parse_fail_candidates']:>4}"
        )
    cross = {
        "line_overlap": fx.cross_duplication(fps)[:25],
        "heading_overlap": fx.heading_overlap(outlines)[:25],
    }
    write_json(DATA_DIR / "cross_document.json", cross)
    print("cross-document: top line overlap ->", [(r["a"], r["b"], r["shared_long_lines"]) for r in cross["line_overlap"][:5]])
    print("cross-document: top heading overlap ->", [(r["a"], r["b"], r["shared_headings"]) for r in cross["heading_overlap"][:5]])


if __name__ == "__main__":
    main()
