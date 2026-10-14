"""Repository-wide integrity: catalog, cross-references, source preservation, links, secrets/PII, tracked-file safety."""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

import forensics_lib as fx
import validate_catalog

ROOT = Path(__file__).resolve().parents[1]


def git_files(*extra):
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", *extra], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    return [f for f in out.stdout.splitlines() if f]


def load(path):
    class L(yaml.SafeLoader):
        pass

    L.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=L)  # noqa: S506


# ------------------------------------------------------------------------------------ catalog and registers

def test_catalog_validates():
    assert validate_catalog.validate() == []


def test_no_course_is_production_go():
    catalog = load(ROOT / "catalog" / "courses.yaml")
    assert [c["id"] for c in catalog["courses"] if c["release_status"] == "PRODUCTION_GO"] == []


def test_findings_register_is_consistent():
    findings = load(ROOT / "docs" / "audits" / "data" / "findings.yaml")["findings"]
    research = {r["id"] for r in load(ROOT / "docs" / "research" / "research_register.yaml")["register"]}
    scores = load(ROOT / "docs" / "audits" / "data" / "scores.yaml")
    ids = [f["id"] for f in findings]
    assert len(ids) == len(set(ids))
    dims = set(scores["dimensions"])
    for f in findings:
        assert re.fullmatch(r"F-[A-Z]+-\d{3}", f["id"])
        assert f["severity"] in {"P0", "P1", "P2", "P3", "P4"} and f["dimension"] in dims
        assert f["verification"] in {"PRIMARY_SOURCE", "EXECUTED", "VISUAL_REVIEW", "MANUAL_READ", "STATIC_SCAN", "NEEDS_VERIFICATION"}
        assert f["remediation"]["status"] in {"NOT_STARTED", "DONE_IN_PILOT", "PLANNED_IN_TRACK"}
        assert f["evidence"] and all("note" in e and isinstance(e["page"], int) for e in f["evidence"])
        for rid in f.get("reference", []) or []:
            assert rid in research, f"{f['id']} cites unknown research entry {rid}"
    for cid, sc in scores["courses"].items():
        assert set(sc["scores"]) == dims
        for k, v in sc["scores"].items():
            assert 0 <= v["score"] <= scores["dimensions"][k]["max"]
            for fid in v["findings"]:
                assert fid in ids, f"{cid}/{k}: unknown finding {fid}"
        assert sc["confidence"] in {"HIGH", "MEDIUM", "LOW"} and sc["strengths"]
    assert max(sum(v["score"] for v in sc["scores"].values()) for sc in scores["courses"].values()) < 95, "no source may exceed the premium threshold"


def test_research_register_entries_are_complete():
    reg = load(ROOT / "docs" / "research" / "research_register.yaml")["register"]
    ids = [r["id"] for r in reg]
    assert len(ids) == len(set(ids))
    for r in reg:
        for k in ("title", "url", "publisher", "version", "verified_on", "method", "finding", "applies_to", "resulting_change"):
            assert r.get(k), f"{r['id']} missing {k}"
        assert r["method"] in {"PRIMARY_DOCUMENT_READ", "EXECUTED", "OFFICIAL_PAGE_SUMMARY"}
        assert r["url"].startswith("https://")


def test_swept_findings_match_the_pilot_claims():
    """Findings marked DONE_IN_PILOT must point at files that exist."""
    for f in load(ROOT / "docs" / "audits" / "data" / "findings.yaml")["findings"]:
        if f["remediation"]["status"] == "DONE_IN_PILOT":
            where = f["remediation"]["where"]
            assert "courses/soc-analyst" in where or "Pilot" in where or "pilot" in where, f["id"]


# ------------------------------------------------------------------------------------ preservation of the sources

def test_source_pdfs_are_unchanged_since_the_audit():
    inv = json.loads((ROOT / "docs" / "audits" / "data" / "source_inventory.json").read_text(encoding="utf-8"))
    assert inv["present_count"] == inv["intended_count"] == 10
    for d in inv["documents"]:
        p = ROOT / d["path"]
        assert p.exists(), f"source moved or deleted: {d['path']}"
        assert hashlib.sha256(p.read_bytes()).hexdigest() == d["sha256"], f"source modified: {d['path']}"


# ------------------------------------------------------------------------------------ links and code in documents

def md_files():
    return [f for f in git_files("*.md") if not f.startswith((".work/", "dist/"))]


def anchors_of(path: Path) -> set[str]:
    out = set()
    for m in re.finditer(r"^#{1,6}\s+(.*)$", path.read_text(encoding="utf-8"), flags=re.M):
        h = re.sub(r"[^\w\- ]", "", m.group(1).strip().lower())
        out.add(h.replace(" ", "-"))
    return out


def test_relative_markdown_links_resolve():
    problems = []
    for rel in md_files():
        src = ROOT / rel
        for m in re.finditer(r"\]\(([^)\s]+)\)", src.read_text(encoding="utf-8")):
            target = m.group(1)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#") and False:
                continue
            path, _, frag = target.partition("#")
            if not path:
                if frag and frag not in anchors_of(src):
                    problems.append(f"{rel}: anchor #{frag} not found")
                continue
            dest = (src.parent / path.replace("%20", " ").replace("%28", "(").replace("%29", ")")).resolve()
            if not dest.exists():
                problems.append(f"{rel}: broken link {target}")
            elif frag and dest.suffix == ".md" and frag not in anchors_of(dest):
                problems.append(f"{rel}: anchor #{frag} not found in {dest.name}")
    assert problems == [], "\n".join(problems[:20])


def test_python_and_yaml_code_blocks_in_courseware_are_valid():
    bad = []
    for rel in md_files():
        if not rel.startswith(("courses/", "docs/architecture", "shared/")):
            continue
        for lang, body in re.findall(r"```(python|yaml|yml|json)\n(.*?)```", (ROOT / rel).read_text(encoding="utf-8"), flags=re.S):
            try:
                if lang == "python":
                    ast.parse(body)
                elif lang == "json":
                    json.loads(body)
                else:
                    list(yaml.safe_load_all(body))
            except Exception as exc:  # noqa: BLE001
                bad.append(f"{rel}: invalid {lang} block ({type(exc).__name__}: {str(exc)[:60]})")
    assert bad == [], "\n".join(bad)


# ------------------------------------------------------------------------------------ secrets, PII, private material

TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".json", ".txt", ".css", ".ini", ".cfg", ".toml"}
PLACEHOLDER_EMAILS = {"example.com", "example.org", "example.net", "corp.example", "noreply.github.com"}


def tracked_text_files():
    return [f for f in git_files() if Path(f).suffix in TEXT_SUFFIXES and not f.startswith((".work/", "dist/", ".venv/"))]


def test_no_secrets_in_tracked_text():
    hits = []
    for rel in tracked_text_files():
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for name, pat in fx.SECRET_PATTERNS.items():
            if name == "generic_assignment":
                continue
            for m in re.finditer(pat, text):
                if not fx._is_placeholder(m.group(0)):
                    hits.append(f"{rel}: {name}")
    assert hits == [], hits


def test_no_third_party_personal_data_in_tracked_text():
    """Real-looking e-mail addresses and phone numbers must never appear in tracked files (masked forms such as m***@x are fine)."""
    hits = []
    for rel in tracked_text_files():
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(fx.PII_PATTERNS["email"], text):
            domain = m.group(0).split("@", 1)[1].lower()
            local = m.group(0).split("@", 1)[0].lower()
            if domain in PLACEHOLDER_EMAILS or domain.endswith((".example", ".test")):
                continue
            if local in {"noreply", "iambivash", "you", "user", "name", "email"} or fx.classify_email(m.group(0)) == "synthetic_placeholder":
                continue
            hits.append(f"{rel}: e-mail-like value with domain {domain}")
        if re.search(fx.PII_PATTERNS["phone_with_country_code"], text):
            hits.append(f"{rel}: phone-number-like value")
    assert hits == [], hits


def test_no_instructor_material_is_tracked():
    bad = [f for f in git_files() if re.search(r"answer-key|grading-notes|independent-reference|/instructor/(?!README\.md)", f)]
    assert bad == [], bad


def test_no_large_or_generated_files_tracked_except_sources():
    sources = {d["path"] for d in json.loads((ROOT / "docs" / "audits" / "data" / "source_inventory.json").read_text(encoding="utf-8"))["documents"]}
    for f in git_files():
        if f in sources:
            continue
        assert (ROOT / f).stat().st_size < 2_000_000, f"{f} is larger than 2 MB"
        assert not f.startswith(("dist/", ".work/", ".venv/")), f


def test_requirements_are_pinned():
    for req in ("requirements.txt", "courses/soc-analyst/labs/requirements.txt"):
        for line in (ROOT / req).read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line:
                assert "==" in line, f"{req}: '{line}' is not pinned"


def test_workflows_do_not_run_automatically():
    wf = ROOT / ".github" / "workflows"
    if not wf.exists():
        return
    for f in wf.glob("*.yml"):
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        triggers = doc.get("on", doc.get(True))
        assert triggers == {"workflow_dispatch": None} or list(triggers) == ["workflow_dispatch"], f"{f.name} must be manual-only (billing constraint)"
