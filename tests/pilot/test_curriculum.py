"""Traceability: every outcome is taught, practised, assessed and graded; assessment material never leaks answers."""
import re
import subprocess

import pytest
import yaml

from conftest import LABS, ROOT

COURSE = ROOT / "courses" / "soc-analyst"
LESSON = COURSE / "lessons" / "m04-auth-detection" / "lesson.md"
# Automated checks that exist in the harness (kept in sync with rubric C1-C4 and the CLI).
LAB_CHECKS = {"recall", "noise-and-suppression", "exception-lint"}
TRIAGE_CHECKS = {"records", "classification", "mitre"}


def slug(heading: str) -> str:
    """GitHub-style heading anchor."""
    h = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return re.sub(r" ", "-", h)


def anchors(path):
    return {slug(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.*)$", path.read_text(encoding="utf-8"), flags=re.M)}


@pytest.fixture(scope="module")
def outcomes():
    return yaml.safe_load((COURSE / "curriculum" / "outcomes.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def quiz():
    return yaml.safe_load((COURSE / "assessments" / "m04" / "quiz.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rubric():
    return yaml.safe_load((COURSE / "assessments" / "m04" / "rubric.yaml").read_text(encoding="utf-8"))


def resolve_path(ref):
    path, _, frag = ref.partition("#")
    return COURSE / path, frag


def test_every_outcome_has_instruction_practice_assessment_and_rubric(outcomes):
    assert [o["id"] for o in outcomes["outcomes"]] == ["LO1", "LO2", "LO3", "LO4", "LO5", "LO6"]
    for o in outcomes["outcomes"]:
        for key in ("instruction", "practice", "assessment", "rubric"):
            assert o[key], f"{o['id']}: no {key}"


def test_instruction_and_practice_references_exist(outcomes):
    for o in outcomes["outcomes"]:
        for ref in o["instruction"] + o["practice"]:
            path, frag = resolve_path(ref)
            assert path.exists(), f"{o['id']}: {ref} -> file missing"
            if frag:
                assert frag in anchors(path), f"{o['id']}: anchor '#{frag}' not found in {path.name}"


def test_assessment_references_resolve_and_are_consistent(outcomes, quiz, rubric):
    q = {i["id"]: i for i in quiz["items"]}
    crit = {c["id"]: c for c in rubric["criteria"]}
    for o in outcomes["outcomes"]:
        for ref in o["assessment"]:
            kind, _, name = ref.partition(":")
            if kind == "quiz":
                assert name in q, f"{o['id']}: {ref} missing"
                assert q[name]["outcome"] == o["id"], f"{ref} is tagged {q[name]['outcome']} in quiz.yaml"
            elif kind == "rubric":
                assert name in crit and o["id"] in crit[name]["outcomes"], f"{o['id']}: rubric criterion {name} does not cover it"
            elif kind == "lab-check":
                assert name in LAB_CHECKS, ref
            elif kind == "triage-check":
                assert name in TRIAGE_CHECKS, ref
            else:
                pytest.fail(f"unknown assessment reference {ref}")
        assert set(o["rubric"]) <= set(crit)


def test_quiz_is_complete_balanced_and_has_no_answers(quiz):
    items = quiz["items"]
    assert len(items) == 10 and len({i["id"] for i in items}) == 10
    assert {i["outcome"] for i in items} == {"LO1", "LO2", "LO3", "LO4", "LO5", "LO6"}
    for i in items:
        assert set(i["options"]) == {"A", "B", "C", "D"} and len(set(i["options"].values())) == 4
        assert not {"answer", "correct", "key", "solution"} & set(i), "quiz data must not carry the answer"
    md = (COURSE / "assessments" / "m04" / "quiz.md").read_text(encoding="utf-8")
    for i in items:
        assert i["stem"] in md, f"{i['id']} stem differs between quiz.yaml and quiz.md"
        for opt in i["options"].values():
            assert opt.rstrip(".") in md.replace("`", "")


def test_student_facing_files_do_not_contain_answers_or_instructor_markers():
    for rel in ("assessments/m04/quiz.md", "assessments/m04/quiz.yaml", "assessments/m04/rubric.yaml", "lessons/m04-auth-detection/lesson.md",
                "labs/m04-guided/README.md", "labs/m04-independent/README.md"):
        text = (COURSE / rel).read_text(encoding="utf-8").lower()
        for bad in ("instructors only", "correct answer", "answer key:", "answer: "):
            assert bad not in text, f"{rel} contains '{bad}'"


def test_instructor_directory_tracks_only_its_readme():
    # tracked files plus untracked-but-not-ignored files = everything that would be committed
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "courses/soc-analyst/instructor"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    assert out.stdout.split() == ["courses/soc-analyst/instructor/README.md"]


def test_rubric_is_well_formed(rubric):
    crit = rubric["criteria"]
    assert len({c["id"] for c in crit}) == len(crit)
    automated = [c for c in crit if c["kind"] == "automated"]
    reviewer = [c for c in crit if c["kind"] == "reviewer"]
    assert len(automated) == 4 and all(c["must_pass"] for c in automated)
    for c in reviewer:
        assert set(c["levels"]) == {0, 1, 2, 3} and c["max"] == 3 and all(len(v) > 15 for v in c["levels"].values())
    covered = {lo for c in crit for lo in c["outcomes"]}
    assert covered == {"LO1", "LO2", "LO3", "LO4", "LO5", "LO6"}
    assert "not a completion claim" in rubric["pass_rule"]


def test_lesson_front_matter_and_time_budget():
    text = LESSON.read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---")[1])
    t = fm["estimated_time_hours"]
    assert t["lesson"] + t["guided_lab"] + t["independent_lab"] == t["total"] == 6.0
    catalog = yaml.safe_load((ROOT / "catalog" / "courses.yaml").read_text(encoding="utf-8"))
    soc = next(c for c in catalog["courses"] if c["id"] == "COURSE-SOC")
    m04 = next(m for m in soc["modules"] if m["id"] == "SOC-M04")
    assert m04["estimated_hours"] == t["total"]
    for key in ("id", "title", "level", "audience", "prerequisites", "versions_cited", "last_verified", "status"):
        assert key in fm
    assert fm["status"] == "PILOT_NOT_SME_REVIEWED"


def test_lesson_objectives_match_outcomes(outcomes):
    text = LESSON.read_text(encoding="utf-8")
    for o in outcomes["outcomes"]:
        assert f"**{o['id']}**" in text
        first_words = o["statement"].split(" and ")[0][:40]
        assert first_words.lower().split()[0] in text.lower()


def test_lesson_yaml_examples_are_valid_and_executable():
    """The Sigma examples shown in the lesson must load in the evaluator and the exception example must lint clean."""
    from soc_lab.sigma_lite import lint_exceptions, parse_documents

    text = LESSON.read_text(encoding="utf-8")
    blocks = re.findall(r"```yaml\n(.*?)```", text, flags=re.S)
    assert len(blocks) >= 2
    rule_docs = [d for d in yaml.safe_load_all(blocks[0]) if d]
    # the lesson's inline example omits metadata for brevity; add the ids/logsource the evaluator requires
    for d in rule_docs:
        d.setdefault("logsource", {"product": "windows", "service": "security"})
    rs = parse_documents(rule_docs)
    assert "mr_spray_single_source" in rs.alias
    exc = yaml.safe_load(blocks[1])["exceptions"]
    assert lint_exceptions(exc, rs) == []


def test_lesson_facts_match_the_verified_research():
    """Facts quoted in the lesson are those recorded in the research register (R-001, R-002, R-003, R-021, R-022, R-023)."""
    text = LESSON.read_text(encoding="utf-8")
    for needle in ("0xC0000064", "0xC000006A", "0xC000006D", "RemoteInteractive", "T1110.003", "DE.AE", "RS.MA", "PR.AA", "2.1.0",
                   "does **not** define a numbered phase list", "6 hours", "v20"):
        assert needle in text, needle
    assert "RS.RP" not in text, "RS.RP is a CSF 1.1 code (finding F-SOC-002) and must not appear as a CSF 2.0 category"
