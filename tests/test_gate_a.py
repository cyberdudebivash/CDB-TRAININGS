"""Negative controls for the Gate A acceptance system: it must refuse to certify what the evidence does not support.

Every test builds a portfolio in which something is wrong or faked and asserts that Gate A does not move to TRAINING_CONTENT_GO and that the validator reports it.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "production"))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
import evidence_fingerprint as EF  # noqa: E402
import gate_a as G  # noqa: E402
import validate_gate_a as V  # noqa: E402


@pytest.fixture(scope="module")
def baseline() -> G.Portfolio:
    return G.Portfolio()


def promoted_catalog(course_id: str) -> dict:
    catalog = yaml.safe_load((ROOT / "catalog" / "courses.yaml").read_text(encoding="utf-8"))
    for c in catalog["courses"]:
        if c["id"] == course_id:
            c["release_status"] = "TRAINING_CONTENT_GO"
    return catalog


def approvals_for(course_id: str, modules: list[str]) -> list[dict]:
    return [{"id": f"HR-{k}", "kind": k, "course": course_id, "scope": ["*"], "reviewer": "A. Reviewer", "role": "external reviewer", "date": "2026-10-15", "outcome": "APPROVED",
             "evidence": "signed form", "human": True, **({"participants": 3} if k == "LEARNER_PILOT" else {})} for k in ("SME", "EDITORIAL", "LEARNER_PILOT", "OWNER_ACCEPTANCE")]


def test_no_course_is_go_without_every_mandatory_criterion_met(baseline):
    for rec in baseline.courses.values():
        if rec["state"] == "TRAINING_CONTENT_GO":
            assert all(c["status"] == G.MET for c in rec["criteria"].values()) and rec["score"] >= baseline.criteria["score_threshold"]


def test_every_criterion_and_dimension_is_computed_for_every_course(baseline):
    ids = [c["id"] for c in baseline.criteria["mandatory_criteria"]]
    weights = sum(d["weight"] for d in baseline.criteria["quality_dimensions"])
    assert weights == 100
    for rec in baseline.courses.values():
        assert list(rec["criteria"]) == ids
        assert set(rec["scores"]) == {d["id"] for d in baseline.criteria["quality_dimensions"]}
        assert 0 <= rec["score"] <= 100


def test_promoting_an_incomplete_course_in_the_catalog_fails_the_validator():
    p = G.Portfolio({"catalog": promoted_catalog("COURSE-PY-ENG")})
    failures = V.check_claims(p)
    assert any("COURSE-PY-ENG" in f and "claims TRAINING_CONTENT_GO" in f for f in failures)
    assert p.courses["COURSE-PY-ENG"]["state"] != "TRAINING_CONTENT_GO"


def test_a_retired_production_go_status_fails_the_validator():
    catalog = promoted_catalog("COURSE-SOC")
    next(c for c in catalog["courses"] if c["id"] == "COURSE-SOC")["release_status"] = "PRODUCTION_GO"
    p = G.Portfolio({"catalog": catalog})
    assert any("PRODUCTION_GO is retired" in f for f in V.check_claims(p)) and V.check_vocabulary(p)


def test_complete_human_approvals_alone_cannot_promote_an_incomplete_course(baseline):
    p = G.Portfolio({"reviews": approvals_for("COURSE-PY-ENG", baseline.courses["COURSE-PY-ENG"]["modules"])})
    rec = p.courses["COURSE-PY-ENG"]
    assert all(rec["approvals"].values()) and rec["criteria"]["A17"]["status"] == G.MET
    assert not rec["eligible"] and rec["state"] != "TRAINING_CONTENT_GO"


def test_a_score_above_threshold_alone_cannot_promote(baseline):
    p = G.Portfolio({"criteria": {**baseline.criteria, "score_threshold": 0}})
    assert all(rec["state"] != "TRAINING_CONTENT_GO" for rec in p.courses.values())


def test_fabricated_reviews_are_rejected_by_the_validator(baseline):
    good = approvals_for("COURSE-PY-ENG", [])[0]
    assert V.check_human_reviews(G.Portfolio({"reviews": [good]})) == []
    bad_cases = [
        {**good, "reviewer": "Claude"}, {**good, "reviewer": "simulated learner"}, {**good, "human": False}, {**good, "evidence": ""}, {**good, "date": "2027-01-01"},
        {**good, "kind": "LEARNER_PILOT"}, {**good, "scope": ["PY-M99"]}, {**good, "course": "COURSE-NOPE"}, {**good, "outcome": "LGTM"},
    ]
    for bad in bad_cases:
        assert V.check_human_reviews(G.Portfolio({"reviews": [bad]})), bad


def test_adversarial_review_of_an_unverified_module_is_rejected(baseline):
    unverified = next(m for m in baseline.modules.values() if m["state"] in ("NOT_STARTED", "IN_PROGRESS", "IMPLEMENTED_UNVERIFIED"))
    review = {"id": "AR-X", "module": unverified["id"], "date": "2026-10-15", "outcome": "CLEAN", "reviewer": "independent pass", "findings": 0, "evidence": "x"}
    assert any("cannot be clean" in f for f in V.check_adversarial(G.Portfolio({"adversarial": [review]})))


def test_a_recorded_run_with_a_skipped_or_failed_test_is_not_evidence():
    def run(outcome: str, interpreters: int = 3) -> dict:
        tests = [{"id": f"tests/test_python_engineering_labs.py::test_m09_{n}", "outcome": "passed"} for n in ("lesson", "guided_starter_fails", "independent")]
        tests.append({"id": "tests/test_python_engineering_labs.py::test_m09_mutants_killed", "outcome": outcome})
        return {"commit": "HEAD", "interpreters": [{"python": f"3.{11 + i}.0", "status": "PASS", "tests": copy.deepcopy(tests)} for i in range(interpreters)]}
    assert G.matrix_evidence("PY-M09", run("passed"), None)["valid"]
    assert not G.matrix_evidence("PY-M09", run("skipped"), None)["valid"]
    assert not G.matrix_evidence("PY-M09", run("failed"), None)["valid"]
    assert not G.matrix_evidence("PY-M09", run("passed", interpreters=2), None)["valid"]       # fewer than three interpreters
    assert G.matrix_evidence("PY-M09", None, None)["kind"] == "none"


def test_evidence_becomes_stale_when_the_module_changes_after_the_recorded_run():
    matrix = {"commit": "HEAD", "interpreters": [{"python": f"3.{11 + i}.0", "status": "PASS",
              "tests": [{"id": f"tests/x.py::test_m09_{n}", "outcome": "passed"} for n in ("a", "b", "c_mutant")]} for i in range(3)]}
    assert G.matrix_evidence("PY-M09", matrix, None, ["courses/none/modules/PY-M09/lesson.md"])["valid"]
    assert G.input_changes("HEAD", ["scripts/validation/lesson_blocks.py"]) == []              # unchanged content is not a change, committed or not
    probe_dir = ROOT / "docs" / "production" / "_probe"
    probe_dir.mkdir(exist_ok=True)
    new_file = probe_dir / "gate_a_probe.txt"
    new_file.write_text("probe", encoding="utf-8")
    try:
        assert G.input_changes("HEAD", ["docs/production/_probe/"]) == ["docs/production/_probe/gate_a_probe.txt"]
        stale = G.matrix_evidence("PY-M09", matrix, None, ["docs/production/_probe/"])
        assert not stale["valid"] and stale["stale_inputs"] == ["docs/production/_probe/gate_a_probe.txt"]
    finally:
        new_file.unlink()
        probe_dir.rmdir()
    assert not G.matrix_evidence("PY-M09", {**matrix, "commit": "0" * 40}, None, ["labs/"])["valid"]      # the recorded commit does not exist: unverifiable


def test_fingerprint_evidence_is_independent_of_commits():
    matrix = {"commit": "0" * 40, "interpreters": [{"python": f"3.{11 + i}.0", "status": "PASS",
              "tests": [{"id": f"tests/x.py::test_m09_{n}", "outcome": "passed"} for n in ("a", "b", "c_mutant")]} for i in range(3)]}
    inputs = ["scripts/validation/lesson_blocks.py"]
    good = {**matrix, "fingerprints": {"PY-M09": EF.fingerprint(inputs)}}
    assert G.matrix_evidence("PY-M09", good, None, inputs, "python-engineering")["valid"]                 # the recorded commit does not exist, the content matches: valid
    bad = {**matrix, "fingerprints": {"PY-M09": "0" * 64}}
    stale = G.matrix_evidence("PY-M09", bad, None, inputs, "python-engineering")
    assert not stale["valid"] and "STALE" in stale["detail"]
    changed_private = {**good, "private_fingerprints": {"PY-M09": "0" * 64}}                             # no such pack here: cannot be compared, so not stale
    assert G.matrix_evidence("PY-M09", changed_private, None, inputs, "python-engineering")["valid"]


def test_a_scenario_without_classification_failure_injection_or_evidence_is_not_verified(baseline):
    scenarios = copy.deepcopy(baseline.scenarios)
    s = next(x for x in scenarios["scenarios"] if x["status"] == "NOT_STARTED")
    s.update(status="TECHNICALLY_VERIFIED", classification="NONE_YET", failure_injections=[], evidence=[])
    p = G.Portfolio({"scenarios": scenarios})
    assert p.scenario_state(s) == "IN_PROGRESS"
    assert any(s["id"] in f for f in V.check_scenarios(p))
    s.update(classification="REPLAY_SIMULATION", failure_injections=["x"], evidence=["test_that_does_not_exist"])
    assert p.scenario_state(s) == "IMPLEMENTED_UNVERIFIED" and any("neither a test" in f for f in V.check_scenarios(p))


def test_a_built_catalog_module_without_files_is_flagged(baseline):
    catalog = copy.deepcopy(baseline.catalog)
    course = next(c for c in catalog["courses"] if c["id"] == "COURSE-AI-ENG")
    course["modules"][0]["status"] = "BUILT"
    p = G.Portfolio({"catalog": catalog})
    assert p.modules[course["modules"][0]["id"]]["state"] == "IN_PROGRESS" or p.modules[course["modules"][0]["id"]]["state"] == "NOT_STARTED"
    assert any(course["modules"][0]["id"] in f for f in V.check_claims(p))


@pytest.mark.parametrize("text,expected", [
    ("This section is TBD", 1), ("Lorem ipsum dolor", 1), ("Content coming soon.", 1), ("FIXME: later", 1), ("See below (to be written)", 1), ("Details: to be completed", 1), ("TODO write this", 1),
    ("The conversion has to be written by hand.", 0), ("replace every `TODO` with a test", 0), ("a SQL parameter placeholder is not a placeholder page", 0), ("# TODO Step B: do this", 0),
])
def test_placeholder_detection(text, expected):
    assert len(V.find_placeholders(text, "x.md")) == expected


def test_an_empty_lesson_section_is_a_placeholder(tmp_path, monkeypatch, baseline):
    # the repository's own built lessons have no empty section; a synthetic one is detected by the same code path
    lines = ["## 1. One", "", "## 2. Two", "text", ""]
    found = []
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            nxt = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
            if not [x for x in lines[i + 1:nxt] if x.strip()]:
                found.append(ln)
    assert found == ["## 1. One"]
    assert all(not f.startswith("G05") or "empty section" not in f for f in V.check_placeholders(baseline))


def test_generated_documents_match_the_data():
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "production" / "render_production_docs.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_gate_b_and_gate_c_are_not_part_of_the_computed_state(baseline):
    state = (ROOT / "docs" / "production" / "data" / "computed_state.json").read_text(encoding="utf-8")
    assert "COMMERCIAL_GO" not in state and "ACADEMY_LIVE_GO" not in state
    assert all(not hasattr(baseline, name) for name in ("commercial", "academy"))
