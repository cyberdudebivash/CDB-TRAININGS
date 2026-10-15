"""Integrity of the page-level audit records (docs/audits/data/page_records)."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "audits" / "data"
RECORDS = DATA / "page_records"

FIELDS_16 = ["source_pdf", "source_page", "chapter", "lesson", "topic", "technology", "original_claim", "evidence", "issue_type",
             "severity", "modernization_action", "source_url", "source_date", "verification_status", "destination_file", "test_evidence"]
ACTIONS = {"KEEP", "UPDATE", "REPLACE", "DEPRECATE", "EXPAND", "ADD", "MERGE", "REMOVE"}
SEVERITIES = {"P0", "P1", "P2", "P3", "P4", "NONE"}
STATUSES = {"MODEL_READ_FINDING_CITED", "MACHINE_FLAGGED_REVIEW_REQUIRED", "MACHINE_SCANNED_NO_FLAGS", "MACHINE_SCANNED_NEAR_BLANK", "VISUAL_REVIEW_REQUIRED"}
CURRENCY = {"BASELINE_AVAILABLE", "CURRENCY_FLAGGED", "NO_TECHNOLOGY_DETECTED", "UNVERIFIED_CURRENCY"}


@pytest.fixture(scope="module")
def index():
    return json.loads((RECORDS / "INDEX.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def records(index):
    out = []
    for part in index["parts"]:
        with (ROOT / part["file"]).open(encoding="utf-8") as fh:
            out += [json.loads(line) for line in fh]
    return out


@pytest.fixture(scope="module")
def inventory():
    return json.loads((DATA / "source_inventory.json").read_text(encoding="utf-8"))["documents"]


def test_every_page_of_every_pdf_has_exactly_one_record(records, inventory):
    by_pdf: dict[str, list[int]] = {}
    for r in records:
        by_pdf.setdefault(r["source_pdf"], []).append(r["source_page"])
    assert set(by_pdf) == {d["path"] for d in inventory}
    for d in inventory:
        assert sorted(by_pdf[d["path"]]) == list(range(1, d["pages"] + 1)), d["path"]
    assert len(records) == sum(d["pages"] for d in inventory) == 8186


def test_index_hashes_match_the_part_files(index):
    for part in index["parts"]:
        raw = (ROOT / part["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == part["sha256"], part["file"]
        assert raw.count(b"\n") == part["records"]


def test_part_files_stay_small(index):
    for part in index["parts"]:
        assert (ROOT / part["file"]).stat().st_size < 1_500_000, part["file"]


def test_records_carry_the_sixteen_mandated_fields_and_valid_enums(records):
    for r in records:
        missing = [f for f in FIELDS_16 if f not in r]
        assert not missing, (r["source_id"], r["source_page"], missing)
        assert r["modernization_action"] in ACTIONS
        assert r["severity"] in SEVERITIES
        assert r["verification_status"] in STATUSES
        assert r["currency_status"] in CURRENCY
        assert isinstance(r["technology"], list) and isinstance(r["issue_type"], list) and isinstance(r["evidence"], dict)
        assert r["test_evidence"], "every record must say what evidence backs it (even if NONE)"
        assert len(r["original_claim"]) <= 120


def test_destination_modules_exist_and_destination_files_agree(records):
    catalog = yaml.safe_load((ROOT / "catalog" / "courses.yaml").read_text(encoding="utf-8"))
    slug = {}
    for c in catalog["courses"]:
        for m in c["modules"]:
            slug[m["id"]] = c["slug"]
    for r in records:
        mod = r["destination_module"]
        if mod:
            assert mod in slug, (r["source_id"], r["source_page"], mod)
            if r["destination_state"] == "PLANNED":
                assert r["destination_file"] == f"courses/{slug[mod]}/modules/{mod}/"
            else:
                assert r["destination_state"] in {"PILOT_BUILT", "BUILT"}
                assert (ROOT / r["destination_file"]).exists(), r["destination_file"]
        else:
            assert r["modernization_action"] in {"REMOVE", "REPLACE"}, "a page without a destination can only be removed or replaced"


def test_status_labels_do_not_overclaim(records):
    findings = yaml.safe_load((DATA / "findings.yaml").read_text(encoding="utf-8"))["findings"]
    cited = {(f["source_id"], e["page"]) for f in findings for e in f["evidence"] if e.get("page")}
    for r in records:
        key = (r["source_id"], r["source_page"])
        if r["verification_status"] == "MODEL_READ_FINDING_CITED":
            assert r["finding_ids"] and key in cited, key
        elif key in cited:
            assert r["verification_status"] in {"MODEL_READ_FINDING_CITED", "VISUAL_REVIEW_REQUIRED"}, key
        if r["modernization_action"] == "KEEP":
            assert r["action_basis"] == "CANDIDATE" and r["confidence"] == "MACHINE", key
            assert r["severity"] in {"NONE", "P3", "P4"}, f"{key}: a page with a serious issue cannot be a KEEP candidate"
        if r["verification_status"] == "VISUAL_REVIEW_REQUIRED":
            assert not r["original_claim"]


def test_serious_pages_are_never_keep(records):
    for r in records:
        if r["severity"] in ("P0", "P1"):
            assert r["modernization_action"] != "KEEP"


def test_no_personal_data_or_credential_literals_in_records(records):
    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    phone = re.compile(r"\+\d[\d\s().-]{8,}")
    secret = re.compile(r"(?i)(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[\"'](?!<redacted>|\*|x{3}|\.\.\.|your|example|changeme)[^\s\"']{6,}[\"']")
    keys = re.compile(r"AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY")
    bad = []
    for r in records:
        blob = json.dumps({k: r[k] for k in ("original_claim", "lesson", "topic", "chapter", "evidence")}, ensure_ascii=False)
        if email.search(blob) or phone.search(blob) or secret.search(blob) or keys.search(blob):
            bad.append((r["source_id"], r["source_page"]))
    assert bad == [], bad[:10]


def test_summary_matches_the_records(records):
    summary = json.loads((DATA / "page_audit_summary.json").read_text(encoding="utf-8"))
    totals = summary["totals"]
    assert totals["pages"] == len(records)
    for field, prefix in (("modernization_action", "action"), ("severity", "severity"), ("verification_status", "status"), ("currency_status", "currency")):
        for value, n in Counter(r[field] for r in records).items():
            assert totals[f"{prefix}:{value}"] == n, (prefix, value)


def test_findings_with_p0_p1_are_visible_in_the_records(records):
    findings = yaml.safe_load((DATA / "findings.yaml").read_text(encoding="utf-8"))["findings"]
    by_page = {(r["source_id"], r["source_page"]): r for r in records}
    for f in findings:
        if f["severity"] in ("P0", "P1"):
            pages = [e["page"] for e in f["evidence"] if e.get("page")]
            for p in pages:
                rec = by_page[(f["source_id"], p)]
                assert f["id"] in rec["finding_ids"], (f["id"], p)
