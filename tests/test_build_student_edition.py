"""The student-edition build: safety gates must reject instructor material; the artefact must meet the accessibility checks."""
import re
import shutil
import textwrap

import pytest
import yaml

import build_student_edition as be

CFG = be.ROOT / "courses" / "soc-analyst" / "student" / "student-edition.yaml"
TOOLCHAIN = all(shutil.which(t) for t in ("pandoc", "pdfinfo", "pdftotext", "pdffonts")) and be.find_chrome() is not None


def write_cfg(tmp_path, include, **over):
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    cfg["include"] = include
    cfg.update(over)
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


# ------------------------------------------------------------------ safety gates (no toolchain needed)

def test_default_config_is_clean():
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    assert be.check_sources(cfg), "includes must exist and contain no forbidden material"


@pytest.mark.parametrize("path", [
    "courses/soc-analyst/instructor/README.md",
    "courses/soc-analyst/labs/m04-guided/solution/exceptions.yml",
])
def test_forbidden_paths_are_rejected(tmp_path, path):
    cfg = yaml.safe_load(write_cfg(tmp_path, [path]).read_text(encoding="utf-8"))
    with pytest.raises(be.BuildError, match="forbidden path fragment"):
        be.check_sources(cfg)


def test_forbidden_marker_is_rejected(tmp_path, monkeypatch):
    leak = be.ROOT / "tests" / "_tmp_leak.md"
    leak.write_text("# x\n\nINSTRUCTORS ONLY - answer: C\n", encoding="utf-8")
    try:
        cfg = yaml.safe_load(write_cfg(tmp_path, ["tests/_tmp_leak.md"]).read_text(encoding="utf-8"))
        with pytest.raises(be.BuildError, match="forbidden marker"):
            be.check_sources(cfg)
    finally:
        leak.unlink()


def test_missing_include_is_an_error(tmp_path):
    cfg = yaml.safe_load(write_cfg(tmp_path, ["does/not/exist.md"]).read_text(encoding="utf-8"))
    with pytest.raises(be.BuildError, match="missing"):
        be.check_sources(cfg)


# ------------------------------------------------------------------ HTML accessibility checker

GOOD = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>t</title></head>"
        "<body><main><h1 id='a'>A</h1><h2 id='b'>B</h2><a href='#b'>go</a><table><tr><th>h</th></tr><tr><td>d</td></tr></table></main></body></html>")


def test_html_checker_accepts_good_page():
    assert be.check_html(GOOD) == []


@pytest.mark.parametrize("mutation,needle", [
    (lambda h: h.replace(" lang='en'", ""), "lang"),
    (lambda h: h.replace("<title>t</title>", ""), "title"),
    (lambda h: h.replace("<meta name='viewport' content='width=device-width'>", ""), "viewport"),
    (lambda h: h.replace("<h2 id='b'>B</h2>", "<h3 id='b'>B</h3>"), "skipped"),
    (lambda h: h.replace("<h1 id='a'>A</h1>", "<h1 id='a'>A</h1><h1 id='c'>C</h1>"), "exactly one h1"),
    (lambda h: h.replace("href='#b'", "href='#nope'"), "unresolved"),
    (lambda h: h.replace("<th>h</th>", "<td>h</td>"), "header cells"),
    (lambda h: h.replace(">go<", "><"), "without text"),
    (lambda h: h.replace("<main>", "<main onclick='x()'>"), "inline handler"),
    (lambda h: h.replace("<h2 id='b'>B</h2>", "<h2 id='a'>B</h2>"), "duplicate ids"),
    (lambda h: h.replace("</main>", "<img src='x.png'></main>"), "alt text"),
])
def test_html_checker_flags_defects(mutation, needle):
    problems = be.check_html(mutation(GOOD))
    assert any(needle in p for p in problems), problems


def test_link_rewriting_keeps_only_internal_targets(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("x"), b.write_text("y")
    frag = '<a href="b.md#sec">to b</a> <a href="other/file.py">code</a> <a href="https://example.org/x">ext</a> <a href="#local">l</a>'
    out = be.rewrite_links(frag, a.resolve(), {a.resolve(): 1, b.resolve(): 2})
    assert 'href="#s2-sec"' in out and '<span class="repo-ref">code</span>' in out and 'rel="noopener"' in out and 'href="#local"' in out


# ------------------------------------------------------------------ full build (needs pandoc, poppler, chromium)

@pytest.mark.skipif(not TOOLCHAIN, reason="SKIPPED_TOOLCHAIN: pandoc, poppler-utils and Chromium are required for the full build")
def test_full_build_passes_all_checks(tmp_path):
    m = be.build(CFG, tmp_path, strict=True)
    assert m["passed"], m["problems"]
    assert m["pdf"]["pages"] >= 10 and m["pdf"]["tagged"] == "yes" and m["pdf"]["outline_entries"] > 0
    assert m["mobile_360px"].startswith("scrollWidth=360 viewportWidth=360")
    html = (tmp_path / m["html"]["file"]).read_text(encoding="utf-8")
    for needle in ("Pilot status", "Triage records passed: 5/5", "© 2026 The MITRE Corporation"):
        assert needle in html
    low = html.lower()
    assert "<script" not in low and "<link" not in low and "<iframe" not in low, "student edition must be a self-contained document"
    assert not re.search(r"""(src|srcset|poster|data)=["']?(https?:)?//""", low), "student edition must make no external requests"
    assert "@import" not in low and "url(http" not in low
    assert "answer key" not in html.lower().replace("the answer key is held by instructors and is not published", "").replace("the answer key is held by instructors, not published", "")


@pytest.mark.skipif(not TOOLCHAIN, reason="SKIPPED_TOOLCHAIN")
def test_html_build_is_deterministic(tmp_path):
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    srcs = be.check_sources(cfg)
    assert be.build_html(cfg, srcs) == be.build_html(cfg, srcs)


# ------------------------------------------------------------------ edition labels and disclosure (October 2026)

PY_CONFIGS = sorted((be.ROOT / "courses" / "python-engineering" / "student").glob("*-student-edition.yaml"))


@pytest.mark.parametrize("config", PY_CONFIGS, ids=lambda p: p.name)
def test_python_engineering_preview_configs_are_clean_and_honestly_labelled(config):
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    assert be.check_sources(cfg)
    assert "Preview Edition" in cfg["title"] and "Premium" not in cfg["title"]
    assert cfg["edition_metadata"] == "auto"


def test_premium_title_is_refused_while_readiness_fields_are_unmet(tmp_path):
    cfg = yaml.safe_load(PY_CONFIGS[0].read_text(encoding="utf-8"))
    cfg["title"] = "CYBERDUDEBIVASH — Python Engineering Pathway — October 2026 Premium Edition"
    with pytest.raises(be.BuildError, match="Premium Edition.*unmet readiness fields"):
        be.edition_gate(cfg)


def test_non_premium_titles_pass_the_gate():
    be.edition_gate(yaml.safe_load(CFG.read_text(encoding="utf-8")))


def test_auto_metadata_states_dates_baseline_and_open_items():
    cfg = yaml.safe_load(PY_CONFIGS[0].read_text(encoding="utf-8"))
    fm, _ = be.strip_front_matter((be.ROOT / cfg["include"][0]).read_text(encoding="utf-8"))
    meta = be.auto_metadata(cfg, fm)
    assert set(meta) == {"content_revision_date", "research_verification_date", "technical_baseline", "unverified_external_changes", "next_review_date"}
    assert "PENDING_FUTURE_REFRESH" in meta["research_verification_date"] and "2026-10-14" in meta["research_verification_date"]
    assert "pytest" in meta["technical_baseline"]
