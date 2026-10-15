#!/usr/bin/env python3
"""Build and verify the SOC-M04 student edition (HTML + PDF) from Markdown sources.

Pipeline: Markdown --pandoc--> HTML fragments --compose--> one self-contained HTML (inline CSS, no external requests)
          --headless Chromium--> tagged PDF with outline.  Outputs go to dist/ (git-ignored).

Checks performed (any failure => exit code 1):
  * source safety   : included paths/contents contain none of the forbidden fragments/markers (no instructor material)
  * HTML structure  : lang, title, viewport, <main>, single h1, no skipped heading levels, unique ids, resolvable anchors,
                      tables have header cells, links have text, no tabindex>0, no inline event handlers
  * responsiveness  : no horizontal page overflow at a 360 px viewport (rendered in Chromium)
  * PDF             : pages > 0, title metadata, all fonts embedded, no blank pages, expected strings in the text layer,
                      forbidden markers absent, tagged structure and outline reported (informational unless --strict)

Run:  .venv/bin/python scripts/build/build_student_edition.py [--config courses/soc-analyst/student/student-edition.yaml] [--out dist]
Requires: pandoc, poppler-utils (pdfinfo/pdffonts/pdftotext) and a Chromium binary (env CDB_CHROME or Playwright's /opt/pw-browsers).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "audit"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
CSS_PATH = ROOT / "shared" / "design" / "cdb-academy.css"
ATTRIBUTION = ("© 2026 The MITRE Corporation. This work is reproduced and distributed with the permission of The MITRE Corporation.")


class BuildError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ tool discovery


def find_chrome() -> str | None:
    import os

    env = os.environ.get("CDB_CHROME")
    cands = [env] if env else []
    cands += sorted(str(p) for p in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    cands += [shutil.which(n) for n in ("chromium", "chromium-browser", "google-chrome", "chrome")]
    return next((c for c in cands if c and Path(c).exists()), None)


def tool_versions() -> dict:
    out = {}
    try:
        out["pandoc"] = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    except Exception:  # noqa: BLE001
        out["pandoc"] = "missing"
    chrome = find_chrome()
    if chrome:
        try:
            out["chromium"] = subprocess.run([chrome, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:  # noqa: BLE001
            out["chromium"] = "unknown"
    else:
        out["chromium"] = "missing"
    try:
        out["pdfinfo"] = subprocess.run(["pdfinfo", "-v"], capture_output=True, text=True).stderr.splitlines()[0]
    except Exception:  # noqa: BLE001
        out["pdfinfo"] = "missing"
    return out


# ------------------------------------------------------------------------------------------------ source handling


def check_sources(cfg: dict) -> list[Path]:
    paths = []
    for rel in cfg["include"]:
        p = ROOT / rel
        if not p.exists():
            raise BuildError(f"included file missing: {rel}")
        norm = "/" + rel.replace("\\", "/")
        for frag in cfg["forbidden_path_fragments"]:
            if frag.lower() in norm.lower():
                raise BuildError(f"forbidden path fragment '{frag}' in included file {rel}")
        text = p.read_text(encoding="utf-8")
        for marker in cfg["forbidden_markers"]:
            if marker.lower() in text.lower():
                raise BuildError(f"forbidden marker '{marker}' found in {rel}")
        paths.append(p)
    return paths


def edition_gate(cfg: dict) -> None:
    """A title may say "Premium Edition" only for a course that Gate A computes as TRAINING_CONTENT_GO (docs/production/TRAINING_CONTENT_GO_REPORT.md).
    The label is a content-quality claim; selling it is a separate decision (Gate B) that this builder does not make."""
    if "premium edition" not in cfg["title"].lower():
        return
    sys.path.insert(0, str(ROOT / "scripts" / "production"))
    import gate_a

    course = gate_a.Portfolio().courses.get(cfg["course"])
    if course is None or course["state"] != "TRAINING_CONTENT_GO":
        unmet = ", ".join(k for k, v in course["criteria"].items() if v["status"] not in (gate_a.MET, "NOT_APPLICABLE")) if course else "unknown course"
        state = course["state"] if course else "unknown"
        raise BuildError(f"title claims 'Premium Edition' but {cfg['course']} has not reached TRAINING_CONTENT_GO (computed state {state}; unmet Gate A criteria: {unmet})")


def auto_metadata(cfg: dict, front_matter: dict) -> dict:
    """Edition disclosure computed from the module's lesson, the change records and the research cutoff."""
    import modern_data as M

    d = M.Data()
    module = cfg["module"]
    open_status = {"NEEDS_VERIFICATION", "SECONDARY_ONLY", "MACHINE_ONLY"}
    open_changes = [ch for ch in d.changes if module in ch["implemented"]["modules"] and ch["verification"]["status"] in open_status]
    cited = front_matter.get("versions_cited", {})
    return {
        "content_revision_date": str(front_matter.get("last_verified", "n/a")),
        "research_verification_date": f"{M.CUTOFF} (Stage A); the {M.REFRESH_TARGET} refresh is PENDING_FUTURE_REFRESH",
        "technical_baseline": "; ".join(f"{k}: {v}" for k, v in cited.items()) or "not stated in the lesson",
        "unverified_external_changes": "; ".join(f"{ch['id']} ({ch['verification']['status']}): {ch['concept']}" for ch in open_changes) or "none recorded for this module's change records",
        "next_review_date": f"{M.REFRESH_TARGET} (Stage B refresh), then at least every 90 days (proposed)",
    }


DISCLOSURE_LABELS = [("content_revision_date", "Content revision date"), ("research_verification_date", "Research verification date"), ("technical_baseline", "Technical baseline"),
                     ("unverified_external_changes", "Unverified external changes"), ("next_review_date", "Next review date")]


def disclosure_html(meta: dict) -> str:
    items = "".join(f"<dt>{html.escape(label)}</dt><dd>{html.escape(str(meta[k]))}</dd>" for k, label in DISCLOSURE_LABELS)
    return f'<section class="disclosure" aria-labelledby="disclosure"><h2 id="disclosure">Edition disclosure</h2><dl>{items}</dl></section>'


def strip_front_matter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.index("\n---", 4)
        return yaml.safe_load(text[4:end]) or {}, text[end + 4:].lstrip("\n")
    return {}, text


def pandoc_fragment(md: str, prefix: str) -> str:
    res = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5", "--wrap=none", "--no-highlight", f"--id-prefix={prefix}", "--shift-heading-level-by=1"],
                         input=md, capture_output=True, text=True)
    if res.returncode != 0:
        raise BuildError(f"pandoc failed: {res.stderr.strip()}")
    return res.stdout


def rewrite_links(fragment: str, src: Path, index: dict[Path, int]) -> str:
    """Relative links to other included documents become in-page anchors; links to other repository files become plain text."""

    def repl(m: re.Match) -> str:
        href, inner = html.unescape(m.group(1)), m.group(2)
        if href.startswith("#") or re.match(r"^[a-z][a-z0-9+.-]*:", href):
            if href.startswith("http"):
                return f'<a href="{html.escape(href)}" rel="noopener">{inner}</a>'
            return m.group(0)
        path, _, frag = href.partition("#")
        target = (src.parent / path).resolve() if path else src
        if target in index:
            sec = f"doc{index[target]}"
            anchor = f"#s{index[target]}-{frag}" if frag else f"#{sec}"
            return f'<a href="{anchor}">{inner}</a>'
        return f'<span class="repo-ref">{inner}</span>'

    return re.sub(r'<a href="([^"]*)">(.*?)</a>', repl, fragment, flags=re.S)


def wrap_tables(fragment: str) -> str:
    return fragment.replace("<table>", '<div class="table-wrap" role="region" aria-label="Scrollable table" tabindex="0"><table>').replace("</table>", "</table></div>")


def toc_html(sections: list[tuple[str, str]]) -> str:
    items = []
    for sec_id, frag in sections:
        heads = re.findall(r'<h([23]) id="([^"]+)">(.*?)</h\1>', frag, flags=re.S)
        if not heads:
            continue
        top = heads[0]
        sub = "".join(f'<li><a href="#{i}">{re.sub(r"<[^>]+>", "", t)}</a></li>' for lvl, i, t in heads[1:] if lvl == "3")
        items.append(f'<li><a href="#{sec_id}">{re.sub(r"<[^>]+>", "", top[2])}</a>' + (f"<ol>{sub}</ol>" if sub else "") + "</li>")
    return '<nav class="toc" aria-label="Contents"><h2 id="contents">Contents</h2><ol>' + "".join(items) + "</ol></nav>"


def build_html(cfg: dict, sources: list[Path]) -> str:
    index = {p.resolve(): i + 1 for i, p in enumerate(sources)}
    digest = hashlib.sha256()
    sections, meta = [], {}
    for i, p in enumerate(sources, 1):
        raw = p.read_text(encoding="utf-8")
        digest.update(raw.encode("utf-8"))
        fm, body = strip_front_matter(raw)
        if fm and not meta:
            meta = fm
        frag = rewrite_links(wrap_tables(pandoc_fragment(body, f"s{i}-")), p.resolve(), index)
        sections.append((f"doc{i}", frag))
    css = CSS_PATH.read_text(encoding="utf-8")
    title = cfg["title"]
    body = []
    for sec_id, frag in sections:
        body.append(f'<section class="edition-section" id="{sec_id}">{frag}</section>')
    verified = meta.get("last_verified", "n/a")
    edition_meta = cfg.get("edition_metadata")
    if edition_meta == "auto":
        edition_meta = auto_metadata(cfg, meta)
    disclosure = disclosure_html(edition_meta) if edition_meta else ""
    notice_title = cfg.get("notice_title", "Pilot status.")
    notice_text = cfg.get("notice_text", "This edition has not been reviewed by a qualified subject-matter expert and is not a certified or production-ready course. "
                                         "Completion is awarded only for demonstrated competence on the rubric, never for reading this document.")
    attribution = (f"<p>{html.escape(ATTRIBUTION)} MITRE ATT&amp;CK® is a registered trademark of The MITRE Corporation.</p>\n" if cfg.get("attribution", True) else "")
    versions = meta.get("versions_cited", {})
    vers = "; ".join(f"{k}: {v}" for k, v in versions.items())
    return f"""<!doctype html>
<html lang="{cfg.get('language', 'en')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="Student edition of {html.escape(cfg['module'])} (pilot build; not reviewed by a qualified subject-matter expert).">
<meta name="generator" content="CDB Academy build_student_edition.py">
<style>
{css}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="doc">
<h1>{html.escape(title)}</h1>
<p class="meta">Course {html.escape(cfg['course'])} · Module {html.escape(cfg['module'])} · Edition version {html.escape(str(cfg['version']))} · Content last verified {html.escape(str(verified))}</p>
<p class="notice"><strong>{html.escape(notice_title)}</strong> {html.escape(notice_text)}</p>
{disclosure}
{toc_html(sections)}
</header>
<main id="main">
{chr(10).join(body)}
</main>
<footer class="doc">
<h2 id="notices">Notices and build information</h2>
{attribution}<p>Licence status: not yet licensed for redistribution (see <span class="repo-ref">LICENSE-STATUS.md</span> in the repository). Versions cited: {html.escape(vers)}.</p>
<p class="meta">Source digest (sha256, first 16): {digest.hexdigest()[:16]}. All data used in the labs is synthetic.</p>
</footer>
</body>
</html>
"""


# ------------------------------------------------------------------------------------------------ HTML checks


class _Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = ""
        self._in_title = False
        self.viewport = False
        self.main = 0
        self.headings: list[int] = []
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.tables = 0
        self.tables_with_th = 0
        self._table_has_th = False
        self.bad_attrs: list[str] = []
        self.empty_links = 0
        self._link_text: list[str] | None = None
        self.imgs_without_alt = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self._in_title = True
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        if tag == "main":
            self.main += 1
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a":
            self.hrefs.append(a.get("href", ""))
            self._link_text = []
        if tag == "table":
            self.tables += 1
            self._table_has_th = False
        if tag == "th":
            self._table_has_th = True
        if tag == "img" and not a.get("alt"):
            self.imgs_without_alt += 1
        for k, v in a.items():
            if k.startswith("on"):
                self.bad_attrs.append(f"inline handler {k}")
            if k == "tabindex" and v and int(v) > 0:
                self.bad_attrs.append("tabindex > 0")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "table" and self._table_has_th:
            self.tables_with_th += 1
        if tag == "a" and self._link_text is not None:
            if not "".join(self._link_text).strip():
                self.empty_links += 1
            self._link_text = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._link_text is not None:
            self._link_text.append(data)


def check_html(text: str) -> list[str]:
    c = _Checker()
    c.feed(text)
    problems = []
    if not c.lang:
        problems.append("html lang attribute missing")
    if not c.title.strip():
        problems.append("title missing")
    if not c.viewport:
        problems.append("viewport meta missing")
    if c.main != 1:
        problems.append(f"expected one <main>, found {c.main}")
    if c.headings.count(1) != 1:
        problems.append(f"expected exactly one h1, found {c.headings.count(1)}")
    for prev, cur in zip(c.headings, c.headings[1:]):
        if cur - prev > 1:
            problems.append(f"heading level skipped (h{prev} -> h{cur})")
            break
    dup = {i for i in c.ids if c.ids.count(i) > 1}
    if dup:
        problems.append(f"duplicate ids: {sorted(dup)[:5]}")
    missing = sorted({h[1:] for h in c.hrefs if h.startswith("#") and h[1:] and h[1:] not in set(c.ids)})
    if missing:
        problems.append(f"unresolved internal links: {missing[:5]}")
    if c.tables != c.tables_with_th:
        problems.append(f"{c.tables - c.tables_with_th} table(s) without header cells")
    if c.empty_links:
        problems.append(f"{c.empty_links} link(s) without text")
    if c.imgs_without_alt:
        problems.append(f"{c.imgs_without_alt} image(s) without alt text")
    problems += sorted(set(c.bad_attrs))
    # Code samples may show loopback URLs (a lab server on http://127.0.0.1); everything else, including links, attributes, styles and prose, may not use http://.
    outside_code = re.sub(r"<(pre|code)\b.*?</\1>", "", text, flags=re.S | re.I)
    if "http://" in outside_code.replace("http://www.w3.org", ""):
        problems.append("insecure http:// reference present")
    return problems


# ------------------------------------------------------------------------------------------------ Chromium


def _chrome_base(chrome: str) -> list[str]:
    return [chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--hide-scrollbars"]


def render_pdf(html_path: Path, pdf_path: Path) -> list[str]:
    chrome = find_chrome()
    if not chrome:
        raise BuildError("no Chromium binary found (set CDB_CHROME)")
    cmd = _chrome_base(chrome) + ["--no-pdf-header-footer", "--generate-pdf-document-outline", "--export-tagged-pdf",
                                  f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
        raise BuildError(f"PDF rendering failed: {res.stderr[-400:]}")
    return cmd


def check_mobile_overflow(html_path: Path, width: int = 360) -> tuple[bool, str]:
    """Load the page in a ``width``-pixel iframe (headless Chromium enforces a ~500 px minimum window) and report horizontal overflow."""
    chrome = find_chrome()
    if not chrome:
        return False, "no chromium"
    probe = (f"<!doctype html><title>probe</title><iframe id=f src='{html_path.resolve().as_uri()}' width={width} height=900 style='border:0'></iframe>"
             "<script>f.onload=function(){var d=f.contentDocument.documentElement;document.title='W:'+d.scrollWidth+'/'+f.clientWidth;};</script>")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "probe.html"
        p.write_text(probe, encoding="utf-8")
        res = subprocess.run(_chrome_base(chrome) + ["--allow-file-access-from-files", "--virtual-time-budget=5000", "--dump-dom", p.as_uri()],
                             capture_output=True, text=True, timeout=120)
    m = re.search(r"<title>W:(\d+)/(\d+)</title>", res.stdout)
    if not m:
        return False, "probe did not run"
    sw, iw = int(m.group(1)), int(m.group(2))
    return sw <= iw and iw == width, f"scrollWidth={sw} viewportWidth={iw}"


# ------------------------------------------------------------------------------------------------ PDF checks


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def check_pdf(pdf: Path, title: str, expected: list[str], forbidden: list[str], strict: bool) -> tuple[list[str], dict]:
    problems: list[str] = []
    info = {}
    for line in _run(["pdfinfo", str(pdf)]).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    pages = int(info.get("Pages", 0))
    if pages < 1:
        problems.append("PDF has no pages")
    if info.get("Title", "").strip() != title:
        problems.append(f"PDF title metadata is '{info.get('Title')}', expected '{title}'")
    fonts = _run(["pdffonts", str(pdf)]).splitlines()[2:]
    not_emb = [f for f in fonts if f.strip() and " no " in re.sub(r"\s+", " ", f)[:200].split("CID")[0] + " "]
    emb_col = [re.split(r"\s{2,}|\s", f.strip()) for f in fonts if f.strip()]
    unembedded = [f for f in fonts if f.strip() and re.search(r"\s(no)\s+(yes|no)\s+(yes|no)\s+\d+", f)]
    if unembedded:
        problems.append(f"{len(unembedded)} font(s) not embedded")
    text = _run(["pdftotext", "-layout", str(pdf), "-"])
    per_page = text.split("\f")
    if per_page and not per_page[-1].strip():
        per_page = per_page[:-1]
    blank = [i + 1 for i, t in enumerate(per_page) if len(t.split()) < 5]
    if blank:
        problems.append(f"nearly blank page(s): {blank[:5]}")
    flat = re.sub(r"\s+", " ", text)
    for needle in expected:
        if needle not in flat:
            problems.append(f"expected text missing from PDF: {needle[:50]}")
    for needle in forbidden:
        if needle.lower() in flat.lower():
            problems.append(f"forbidden marker present in PDF: {needle}")
    tagged = info.get("Tagged", "no")
    try:
        from pypdf import PdfReader

        import logging

        logging.disable(logging.CRITICAL)
        outline = len(PdfReader(str(pdf), strict=False).outline)
    except Exception:  # noqa: BLE001
        outline = -1
    summary = {"pages": pages, "words": len(flat.split()), "tagged": tagged, "outline_entries": outline, "size_bytes": pdf.stat().st_size,
               "pdf_version": info.get("PDF version"), "page_size": info.get("Page size")}
    if strict:
        if tagged != "yes":
            problems.append("PDF is not tagged")
        if outline <= 0:
            problems.append("PDF has no bookmark outline")
    return problems, summary


# ------------------------------------------------------------------------------------------------ main


def build(config_path: Path, out_dir: Path, strict: bool = False) -> dict:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    edition_gate(cfg)
    sources = check_sources(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg['module']}-{cfg['edition']}-{cfg['version']}"
    html_text = build_html(cfg, sources)
    html_path = out_dir / f"{stem}.html"
    html_path.write_text(html_text, encoding="utf-8")
    problems = {"html": check_html(html_text)}
    sys.path.insert(0, str(ROOT / "scripts" / "validation"))
    import check_privacy

    problems["privacy"] = [str(f) for f in check_privacy.scan_text(html_text, html_path.name)]     # masked findings: no personal data is copied into the build log
    ok_mobile, mobile_detail = check_mobile_overflow(html_path)
    problems["mobile_360px"] = [] if ok_mobile else [f"horizontal overflow or probe failure: {mobile_detail}"]
    pdf_path = out_dir / f"{stem}.pdf"
    cmd = render_pdf(html_path, pdf_path)
    expected = cfg.get("expected_strings") or [cfg["module"], "Pilot status", "Pilot", "Triage records passed", ATTRIBUTION[:40]]
    if cfg.get("edition_metadata"):
        expected = expected + ["Edition disclosure", "Research verification date", "PENDING_FUTURE_REFRESH"]
    pdf_problems, pdf_summary = check_pdf(pdf_path, cfg["title"], expected, cfg["forbidden_markers"], strict)
    problems["pdf"] = pdf_problems
    manifest = {
        "edition": stem,
        "sources": [str(p.relative_to(ROOT)) for p in sources],
        "html": {"file": html_path.name, "sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(), "size_bytes": html_path.stat().st_size,
                 "deterministic_note": "HTML contains no timestamps; identical sources reproduce identical bytes"},
        "pdf": {"file": pdf_path.name, "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(), **pdf_summary,
                "note": "PDF embeds a creation timestamp; its hash differs between builds"},
        "mobile_360px": mobile_detail,
        "problems": problems,
        "tools": tool_versions(),
        "chromium_command": [c for c in cmd if not c.startswith("--print-to-pdf") and not c.startswith("file:")],
        "passed": not any(problems.values()),
    }
    (out_dir / f"{stem}.manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=str(ROOT / "courses" / "soc-analyst" / "student" / "student-edition.yaml"))
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--strict", action="store_true", help="also require a tagged PDF with a bookmark outline")
    args = ap.parse_args(argv)
    try:
        m = build(Path(args.config), Path(args.out), args.strict)
    except BuildError as exc:
        print(f"BUILD ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"built {m['edition']}: pdf {m['pdf']['pages']} pages, {m['pdf']['words']} words, tagged={m['pdf']['tagged']}, outline={m['pdf']['outline_entries']}; mobile {m['mobile_360px']}")
    for area, probs in m["problems"].items():
        for p in probs:
            print(f"  PROBLEM [{area}] {p}")
    print("RESULT:", "PASS" if m["passed"] else "FAIL")
    return 0 if m["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
