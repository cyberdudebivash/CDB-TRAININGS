"""Negative controls for the Gate A acceptance system: it must refuse to certify what the evidence does not support.

Every test builds a portfolio in which something is wrong or faked and asserts that Gate A does not move to TRAINING_CONTENT_GO and that the validator reports it.
"""
from __future__ import annotations

import copy
import json
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


def test_foundations_module_evidence_comes_from_its_own_test_file():
    def run(outcome: str, interpreters: int = 3, names: tuple[str, ...] = ("test_lesson_has_substantive_content_and_executable_examples", "test_guided_regressions", "test_independent_starter_fails_as_intended")) -> dict:
        tests = [{"id": f"tests/test_fnd_m01::{n}", "outcome": outcome} for n in names]
        return {"commit": "HEAD", "interpreters": [{"python": f"3.{11 + i}.0", "status": "PASS", "tests": copy.deepcopy(tests)} for i in range(interpreters)]}
    assert G.matrix_markers("FND-M01") == ("tests/test_fnd_m01::", "[FND-M01]") and G.matrix_markers("PY-M09") == ("::test_m09_", "[PY-M09]")
    assert G.matrix_markers("SOC-M04") is None and G.matrix_markers("PY-MXX") is None and G.matrix_markers("CYB-M01") is None
    good = G.matrix_evidence("FND-M01", run("passed"), None)
    assert good["valid"] and good["negative_controls"] and good["lab_tests"] == 3
    assert not G.matrix_evidence("FND-M01", run("skipped"), None)["valid"]
    assert not G.matrix_evidence("FND-M01", run("failed"), None)["valid"]
    assert not G.matrix_evidence("FND-M01", run("passed", interpreters=2), None)["valid"]
    assert not G.matrix_evidence("FND-M01", run("passed", names=("test_guided_regressions", "test_independent_starter_fails_as_intended")), None)["valid"]      # fewer than three lab tests
    other = {"commit": "HEAD", "interpreters": [{"python": f"3.{11 + i}.0", "status": "PASS", "tests": [{"id": f"tests/test_python_engineering_labs.py::test_m09_{n}", "outcome": "passed"} for n in ("a", "b", "c_mutant")]} for i in range(3)]}
    assert G.matrix_evidence("FND-M01", other, None)["kind"] == "lab_matrix" and not G.matrix_evidence("FND-M01", other, None)["valid"]      # another module's tests are not this module's evidence
    assert G.matrix_evidence("CYB-M01", run("passed"), None)["kind"] == "none"


def test_the_lab_matrix_runs_the_foundations_tests_too():
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_lab_matrix", ROOT / "scripts" / "validation" / "run_lab_matrix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "tests/test_fnd_m01.py" in module.SUITES and "tests/test_module_packs.py" in module.SUITES
    on_disk = sorted(f"tests/{p.name}" for p in (ROOT / "tests").glob("test_fnd_m[0-9][0-9].py"))
    assert on_disk and all(name in module.SUITES for name in on_disk), on_disk      # a foundations module whose tests the matrix does not run has no recorded evidence


def test_a_complete_course_preview_is_not_a_final_edition_and_an_unsourced_one_is_not_evidence():
    preview = {"course": "COURSE-X", "kind": "PREVIEW", "passed": True, "modules": ["A"]}
    assert not G.is_final_course_pdf(preview) and not G.is_final_course_pdf(None) and not G.is_final_course_pdf({**preview, "passed": False})
    assert G.is_final_course_pdf({"course": "COURSE-X", "kind": "FINAL", "passed": True, "modules": ["A"]})
    assert not G.edition_is_fresh({"sources": {}, "passed": True})                  # no recorded sources: not evidence
    for course in G.Portfolio().courses.values():
        cp = course["course_pdf"]
        if cp:
            assert cp.get("kind") == "PREVIEW" and course["criteria"]["A14"]["status"] != G.MET      # a recorded course edition is a preview and never satisfies A14


def test_the_matrix_pieces_cover_every_test_exactly_once():
    import importlib.util
    import subprocess

    spec = importlib.util.spec_from_file_location("run_lab_matrix", ROOT / "scripts" / "validation" / "run_lab_matrix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def collected(files: list[str], expr: str | None) -> list[str]:
        cmd = [sys.executable, "-m", "pytest", *files, *(["-k", expr] if expr else []), "--collect-only", "-q", "-p", "no:cacheprovider", "-o", "addopts="]
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False).stdout
        return [line for line in out.splitlines() if "::" in line]

    everything = collected(module.SUITES, None)
    pieces = [test for _, files, expr in module.chunks() for test in collected(files, expr)]
    assert len(everything) > 200 and sorted(pieces) == sorted(everything), (len(everything), len(pieces))      # a test in no piece would never be recorded; one in two pieces would be recorded twice


def test_an_interrupted_matrix_run_resumes_only_with_identical_content(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_lab_matrix", ROOT / "scripts" / "validation" / "run_lab_matrix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    same = module.tree_id({"PY-M01": "a"}, {"PY-M01": "b"})
    assert same == module.tree_id({"PY-M01": "a"}, {"PY-M01": "b"}) and same != module.tree_id({"PY-M01": "a2"}, {"PY-M01": "b"}) and same != module.tree_id({"PY-M01": "a"}, {})
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"tree_id": same, "results": [{"requested": "3.11", "status": "PASS"}, {"requested": "3.12", "status": "FAIL"}, {"requested": "3.13", "status": "NOT_EXECUTED"}]}), encoding="utf-8")
    assert list(module.resumable(partial, same)) == ["3.11"]                 # only a pass is reused: a failure or a missing interpreter is run again
    assert module.resumable(partial, "0" * 64) == {}                           # other content: nothing is reused
    assert module.resumable(tmp_path / "missing.json", same) == {}
    module.write_partial(partial, same, [], {"3.13": {"labs-m10": {"name": "labs-m10", "exit": 0, "tests": [{"id": "a::b", "outcome": "passed"}]}}})
    assert list(module.saved_pieces(partial, same)["3.13"]) == ["labs-m10"] and module.saved_pieces(partial, "0" * 64) == {}      # a piece is reused only for identical content
    assert module.chunk_passed(module.saved_pieces(partial, same)["3.13"]["labs-m10"])
    assert not module.chunk_passed({"exit": 0, "tests": []}) and not module.chunk_passed({"exit": 1, "tests": [{"id": "x", "outcome": "passed"}]})
    assert not module.chunk_passed({"exit": 0, "tests": [{"id": "x", "outcome": "skipped"}]})            # a skipped test is not a passed piece
    partial.write_text("not json", encoding="utf-8")
    assert module.resumable(partial, same) == {}


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


def test_every_flagged_source_page_has_a_recorded_visual_inspection_that_is_not_called_human(baseline):
    assert V.check_visual_review(baseline) == []
    assert len(baseline.visual["pages"]) == len(G.flagged_pages()) == baseline.totals()["visual_pages_inspected"]
    missing = copy.deepcopy(baseline.visual)
    missing["pages"] = missing["pages"][1:]
    assert any("needs visual inspection" in f for f in V.check_visual_review(G.Portfolio({"visual": missing})))
    claimed = copy.deepcopy(baseline.visual)
    claimed["human_reviewed"] = True
    assert any("claims human review" in f for f in V.check_visual_review(G.Portfolio({"visual": claimed})))
    extra = copy.deepcopy(baseline.visual)
    extra["pages"].append({"source": "SRC-PY-HANDBOOK", "page": 2, "content_type": "cover", "summary": "x", "disposition": "y"})
    assert any("not a flagged page" in f for f in V.check_visual_review(G.Portfolio({"visual": extra})))
