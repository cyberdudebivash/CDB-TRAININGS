"""Evidence integrity for the October 2026 modernization data and the documents generated from it."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

import modern_data as M
import render_audit_docs
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
