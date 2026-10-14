#!/usr/bin/env python3
"""Build the machine-readable source inventory and reconcile it with the intended corpus.

Outputs
-------
docs/audits/data/source_inventory.json   (authoritative, deterministic)

Run:  .venv/bin/python scripts/inventory/build_inventory.py
"""
from __future__ import annotations

import re
import subprocess
from collections import Counter

from common import (
    DATA_DIR,
    INTENDED_SOURCES,
    REPO_ROOT,
    SOURCE_IDS,
    extract_pages,
    BASELINE_COMMIT,
    list_pdfs,
    read_outline,
    sha256_file,
    squeeze,
    write_json,
)


def pdfinfo(path) -> dict:
    out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True).stdout
    info = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return info


def is_lfs_pointer(path) -> bool:
    with path.open("rb") as fh:
        return fh.read(40).startswith(b"version https://git-lfs")


def tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return {line for line in out.splitlines() if line}


def main() -> None:
    tracked = tracked_files()
    pdfs = list_pdfs()
    records = []
    for pdf in pdfs:
        info = pdfinfo(pdf)
        pages = extract_pages(pdf)
        page_chars = [len(squeeze(p)) for p in pages]
        words = sum(len(re.findall(r"\w+", p)) for p in pages)
        n_pages = int(info.get("Pages", len(pages)))
        empty = sum(1 for c in page_chars if c == 0)
        if words == 0:
            text_layer = "NONE_IMAGE_ONLY"
        elif empty / max(n_pages, 1) > 0.25:
            text_layer = "PARTIAL"
        else:
            text_layer = "FULL"
        outline = read_outline(pdf)
        levels = Counter(o["level"] for o in outline)
        records.append(
            {
                "source_id": SOURCE_IDS.get(pdf.name, "SRC-UNREGISTERED"),
                "path": pdf.name,
                "tracked_in_git": pdf.name in tracked,
                "lfs_pointer": is_lfs_pointer(pdf),
                "size_bytes": pdf.stat().st_size,
                "sha256": sha256_file(pdf),
                "pages": n_pages,
                "pdf_version": info.get("PDF version"),
                "encrypted": info.get("Encrypted", "").startswith("yes"),
                "tagged": info.get("Tagged") == "yes",
                "page_size": info.get("Page size"),
                "metadata": {
                    "title": info.get("Title"),
                    "creator": info.get("Creator"),
                    "producer": info.get("Producer"),
                    "creation_date": info.get("CreationDate"),
                    "mod_date": info.get("ModDate"),
                },
                "text_layer": text_layer,
                "words": words,
                "words_per_page": round(words / max(n_pages, 1), 1),
                "empty_pages": empty,
                "outline_entries": len(outline),
                "outline_levels": {str(k): v for k, v in sorted(levels.items())},
                "extraction": "OK" if words else "NEEDS_OCR_OR_VISUAL_REVIEW",
            }
        )

    by_name = {r["path"]: r for r in records}
    reconciliation = [
        {
            "intended": name,
            "source_id": SOURCE_IDS[name],
            "status": "PRESENT" if name in by_name else "BLOCKED_SOURCE_PENDING",
        }
        for name in INTENDED_SOURCES
    ]
    unexpected = sorted(set(by_name) - set(INTENDED_SOURCES))

    # Exact duplicate detection by hash.
    hash_groups: dict[str, list[str]] = {}
    for r in records:
        hash_groups.setdefault(r["sha256"], []).append(r["path"])
    exact_duplicates = sorted(sorted(v) for v in hash_groups.values() if len(v) > 1)

    result = {
        "baseline_commit": BASELINE_COMMIT,
        "source_root": ".",
        "intended_count": len(INTENDED_SOURCES),
        "present_count": sum(1 for r in reconciliation if r["status"] == "PRESENT"),
        "unexpected_files": unexpected,
        "exact_duplicates": exact_duplicates,
        "reconciliation": reconciliation,
        "documents": records,
        "totals": {
            "pages": sum(r["pages"] for r in records),
            "words": sum(r["words"] for r in records),
            "size_bytes": sum(r["size_bytes"] for r in records),
        },
    }
    write_json(DATA_DIR / "source_inventory.json", result)
    print(
        f"inventory: {result['present_count']}/{result['intended_count']} intended sources present; "
        f"{result['totals']['pages']} pages, {result['totals']['words']} words; "
        f"unexpected={len(unexpected)} exact_duplicates={len(exact_duplicates)}"
    )


if __name__ == "__main__":
    main()
