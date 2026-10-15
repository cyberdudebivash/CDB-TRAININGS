"""Evidence integrity for the October 2026 modernization data and the documents generated from it."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

import modern_data as M
import render_audit_docs
import render_curriculum_2026
import render_readiness_2026
import render_research_docs
import validate_modernization_data as V

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = "2026-10-14"


@pytest.fixture(scope="module")
def data():
    return M.Data()


def test_all_references_resolve():
    assert V.validate() == []


def test_registry_and_rule_patterns_compile(data):
    for tid, e in data.registry.items():
        re.compile(e["detect"])
    for r in data.rules:
        re.compile(r["rx"])
        if r.get("unless"):
            re.compile(r["unless"])
        assert r["evidence"] or r["issue"] == "TEST_ANTIPATTERN", r["id"]


def test_no_evidence_is_dated_after_the_cutoff(data):
    for rid, r in data.register.items():
        assert str(r["verified_on"]) <= CUTOFF, rid
    for p in data.probes.values():
        assert p["executed_utc"][:10] <= CUTOFF, p["id"]
        assert p["status"] == "OK", p["id"]
    for tid, recs in data.snapshot_all.items():
        for r in recs:
            assert r["retrieved_utc"][:10] <= CUTOFF, tid
            if r.get("current"):
                assert str(r["current"]["date"]) <= CUTOFF, (tid, r["current"])
    assert str(M.load_yaml("docs/audits/data/modernization_changes.yaml")["as_of"]) <= CUTOFF
    assert str(M.load_yaml("docs/research/new_developments.yaml")["as_of"]) <= CUTOFF


def test_every_p0_p1_finding_is_addressed_by_a_change_record(data):
    cited = {str(r) for ch in data.changes for r in ch["ref"]}
    missing = [f["id"] for f in data.findings.values() if f["severity"] in ("P0", "P1") and f["id"] not in cited]
    assert missing == [], f"P0/P1 findings with no differential-analysis record: {missing}"


def test_every_source_backed_course_has_a_change_log(data):
    for c in data.catalog["courses"]:
        if c.get("source_ids"):
            assert len([ch for ch in data.changes if ch["course"] == c["id"]]) >= 4, c["id"]


def test_built_status_requires_executed_lab_evidence(data):
    evidence = ROOT / "docs" / "qa" / "LAB_EXECUTION_EVIDENCE.md"
    for ch in data.changes:
        if ch["implemented"]["status"] == "BUILT":
            assert evidence.exists() and ch["verification"]["status"] in ("EXECUTED", "RESEARCH_VERIFIED"), ch["id"]


def test_secondary_or_unread_evidence_is_never_called_executed(data):
    for ch in data.changes:
        refs = [data.register.get(str(r)) for r in ch["ref"] if str(r).startswith("R-")]
        if ch["verification"]["status"] == "RESEARCH_VERIFIED":
            assert all(r is None or r["method"] != "SECONDARY_SOURCE" for r in refs) or "secondary" in ch["verification"]["result"].lower(), ch["id"]


def test_generated_audit_documents_are_current(data):
    for path, text in render_audit_docs.render_all(data).items():
        assert path.exists() and path.read_text(encoding="utf-8") == text, f"stale: {path.relative_to(ROOT)} (run scripts/audit/render_audit_docs.py)"


def test_generated_research_documents_are_current(data):
    for path, text in render_research_docs.render_all(data).items():
        assert path.exists() and path.read_text(encoding="utf-8") == text, f"stale: {path.relative_to(ROOT)} (run scripts/research/render_research_docs.py)"


def test_generated_documents_declare_the_two_stage_policy():
    for rel in ("docs/audits/OCT2026_COMPLETE_PDF_AUDIT.md", "docs/research/RESEARCH_VERIFICATION_2026.md", "docs/research/TECHNOLOGY_BASELINES_2026.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "PENDING_FUTURE_REFRESH" in text and "2026-10-14" in text, rel


def test_audit_document_does_not_claim_complete_human_review():
    text = (ROOT / "docs/audits/OCT2026_COMPLETE_PDF_AUDIT.md").read_text(encoding="utf-8")
    assert "No claim of a complete human page-by-page review is made" in text
    assert not re.search(r"100\s?% (?:human|manual) review", text, re.I)


def test_snapshot_registry_ids_exist_in_the_registry(data):
    assert set(data.snapshot_all) <= set(data.registry)


def test_generated_curriculum_documents_are_current(data):
    for path, text in render_curriculum_2026.render_all(data).items():
        assert path.exists() and path.read_text(encoding="utf-8") == text, f"stale: {path.relative_to(ROOT)} (run scripts/build/render_curriculum_2026.py)"


def test_generated_readiness_documents_are_current(data):
    for path, text in render_readiness_2026.render_all(data).items():
        assert path.exists() and path.read_text(encoding="utf-8") == text, f"stale: {path.relative_to(ROOT)} (run scripts/build/render_readiness_2026.py)"


def test_no_course_is_recommended_for_production_go(data):
    report = render_readiness_2026.Report(data)
    assert not any(m["go"] for m in report.metrics.values())
    for cid, m in report.metrics.items():
        assert m["fields"]["human_approval"]["status"] != "MET", "human approval can only be recorded by a person, outside the automation"
        assert m["unmet"], cid
    text = (ROOT / "docs/release/OCT2026_PRODUCTION_READINESS.md").read_text(encoding="utf-8")
    assert "TRAINING_CONTENT_GO is not recommended for any course" in text
    premium = (ROOT / "docs/commercial/PREMIUM_COURSE_CATALOG_2026.md").read_text(encoding="utf-8")
    assert "No edition may be titled" in premium


def test_stage_b_is_never_reported_as_done():
    for rel in ("docs/release/OCT24_FINAL_REFRESH_CHECKLIST.md", "docs/release/OCT2026_PRODUCTION_READINESS.md", "docs/commercial/PRICING_AND_POSITIONING_RESEARCH.md"):
        assert "PENDING_FUTURE_REFRESH" in (ROOT / rel).read_text(encoding="utf-8"), rel
    checklist = (ROOT / "docs/release/OCT24_FINAL_REFRESH_CHECKLIST.md").read_text(encoding="utf-8")
    assert "[x]" not in checklist.lower().replace("[ ]", "")


def test_documents_cite_only_existing_research_entries(data):
    import re

    cited = {}
    for md_path in list((ROOT / "docs").rglob("*.md")) + list((ROOT / "courses").rglob("*.md")):
        if md_path.name in ("RESEARCH_REGISTER.md",):
            continue
        for rid in set(re.findall(r"\bR-\d{3}\b", md_path.read_text(encoding="utf-8"))):
            if rid not in data.register:
                cited.setdefault(str(md_path.relative_to(ROOT)), []).append(rid)
    assert cited == {}, cited


def test_pricing_research_is_labelled_as_hypotheses_and_sets_no_price():
    text = (ROOT / "docs/commercial/PRICING_AND_POSITIONING_RESEARCH.md").read_text(encoding="utf-8")
    assert "Status: hypotheses" in text and "No price has been set" in text
    assert "guarantee" in text.lower() and "Prohibited" in text
