"""Shared helpers for the CDB-TRAININGS source-audit toolchain.

Design rules
------------
* Deterministic: no wall-clock timestamps in generated artifacts; ordering is sorted.
* Non-destructive: source PDFs are opened read-only and never rewritten.
* Third-party licensed text is cached only under ``.work/`` (git-ignored), never in tracked files.
* Poppler (``pdftotext``) is the text extractor so results are reproducible on any Linux CI image.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = REPO_ROOT / ".work"
TEXT_DIR = WORK_DIR / "text"
DATA_DIR = REPO_ROOT / "docs" / "audits" / "data"
SOURCES_DIR = REPO_ROOT  # PDFs currently live at the repo root (see docs/audits/SOURCE_PROVENANCE.md)

# The ten documents the owner declared as the intended corpus (task directive section 3).
INTENDED_SOURCES = [
    "Complete AI Training Bundle 2026.pdf",
    "CyberDudeBivash Python Engineering Handbook.pdf",
    "CyberDudeBivash_Java_Automation_Test_Engineer_Real_Time_Job_Training.pdf",
    "CyberDudeBivash_OSINT_Starter_Bundle_FULL.pdf",
    "CYBERDUDEBIVASH-PYTHON-AUTOMATION-TRAINING.pdf",
    "GCP-DATA-ENGINEER-TRAINING.pdf",
    "INTERNAL FRONTEND DEVELOPER ONBOARDING PLAYBOOK.pdf",
    "OFFICIAL_CYBERDUDEBIVASH_MEGA_COURSE_2026_Part_1.pdf",
    "OFFICIAL_CYBERDUDEBIVASH_MEGA_COURSE_2026_Part_2.pdf",
    "SOC Analyst Survival Playbook (2026 Edition).pdf",
]

# Stable course/source identifiers (used by catalog/courses.yaml and every audit document).
SOURCE_IDS = {
    "Complete AI Training Bundle 2026.pdf": "SRC-AI-BUNDLE",
    "CyberDudeBivash Python Engineering Handbook.pdf": "SRC-PY-HANDBOOK",
    "CyberDudeBivash_Java_Automation_Test_Engineer_Real_Time_Job_Training.pdf": "SRC-JAVA-AUTOTEST",
    "CyberDudeBivash_OSINT_Starter_Bundle_FULL.pdf": "SRC-OSINT-STARTER",
    "CYBERDUDEBIVASH-PYTHON-AUTOMATION-TRAINING.pdf": "SRC-PY-AUTOMATION",
    "GCP-DATA-ENGINEER-TRAINING.pdf": "SRC-GCP-DATAENG",
    "INTERNAL FRONTEND DEVELOPER ONBOARDING PLAYBOOK.pdf": "SRC-FRONTEND-ONBOARD",
    "OFFICIAL_CYBERDUDEBIVASH_MEGA_COURSE_2026_Part_1.pdf": "SRC-MEGA-P1",
    "OFFICIAL_CYBERDUDEBIVASH_MEGA_COURSE_2026_Part_2.pdf": "SRC-MEGA-P2",
    "SOC Analyst Survival Playbook (2026 Edition).pdf": "SRC-SOC-PLAYBOOK",
}


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("_")


def list_pdfs(root: Path = SOURCES_DIR) -> list[Path]:
    """Tracked PDFs at the source root, sorted for determinism."""
    return sorted(p for p in root.glob("*.pdf") if p.is_file())


def extract_pages(pdf: Path, force: bool = False) -> list[str]:
    """Return per-page text (layout mode). Cached under .work/text/ (git-ignored)."""
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    out = TEXT_DIR / f"{slugify(pdf.name)}.layout.txt"
    if force or not out.exists() or out.stat().st_mtime < pdf.stat().st_mtime:
        subprocess.run(["pdftotext", "-layout", str(pdf), str(out)], check=True, stderr=subprocess.DEVNULL)
    raw = out.read_text(encoding="utf-8", errors="replace")
    pages = raw.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def read_outline(pdf: Path) -> list[dict]:
    """Bookmark outline as [{level, title, page}] using pypdf (warnings suppressed)."""
    from pypdf import PdfReader

    logging.disable(logging.CRITICAL)
    reader = PdfReader(str(pdf), strict=False)
    out: list[dict] = []

    def walk(items, depth):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                try:
                    page = reader.get_destination_page_number(item) + 1
                except Exception:  # noqa: BLE001 - malformed destination; record as unknown
                    page = None
                out.append({"level": depth, "title": (item.title or "").strip(), "page": page})

    walk(reader.outline, 1)
    return out


def squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


# --------------------------------------------------------------------------- absolute-indent extraction
XY_DIR = WORK_DIR / "xy"
SPACE_PT = 3.0  # approx. width of a space glyph in the body fonts used by the Google-Docs exports


def extract_pages_xy(pdf: Path, force: bool = False) -> list[str]:
    """Per-page text whose leading spaces reflect *absolute* x-offsets.

    ``pdftotext -layout`` trims each page's left margin independently, which destroys relative
    indentation for code that crosses a page break.  Here every line is re-indented from the
    line's absolute ``xMin`` (relative to the document's modal left margin) so code spanning
    pages keeps a consistent indentation.  Cached in .work/xy/ (git-ignored).
    """
    import xml.etree.ElementTree as ET
    from collections import Counter

    XY_DIR.mkdir(parents=True, exist_ok=True)
    cache = XY_DIR / f"{slugify(pdf.name)}.json"
    if cache.exists() and not force and cache.stat().st_mtime >= pdf.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    xml_path = XY_DIR / f"{slugify(pdf.name)}.bbox.xhtml"
    subprocess.run(["pdftotext", "-bbox-layout", str(pdf), str(xml_path)], check=True, stderr=subprocess.DEVNULL)

    pages_lines: list[list[tuple[float, str]]] = []
    current: list[tuple[float, str]] = []
    for _event, el in ET.iterparse(str(xml_path), events=("end",)):
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "line":
            words = [(w.text or "") for w in el if w.tag.rsplit("}", 1)[-1] == "word"]
            current.append((float(el.get("xMin", "0")), " ".join(words)))
        elif tag == "page":
            pages_lines.append(current)
            current = []
            el.clear()
    xml_path.unlink(missing_ok=True)

    # Modal left margin of the document (quantised to 0.5pt) = indent level zero.
    margin_votes = Counter(round(x * 2) / 2 for page in pages_lines for x, text in page if text.strip())
    base = margin_votes.most_common(1)[0][0] if margin_votes else 0.0
    pages = []
    for page in pages_lines:
        out = []
        for x, text in page:
            spaces = max(0, round((x - base) / SPACE_PT))
            out.append(" " * spaces + text)
        pages.append("\n".join(out))
    cache.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages
