"""Structure and traceability of built module packs (courses/*/modules/*): lessons run, outcomes are taught, practised and assessed."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import lesson_blocks
import render_module_assets

ROOT = Path(__file__).resolve().parents[1]
MODULES = sorted(p for p in (ROOT / "courses").glob("*/modules/*") if (p / "lesson.md").exists())
CUTOFF = "2026-10-14"      # the baseline snapshot date
EXECUTION_DATE = str(yaml.safe_load((ROOT / "docs" / "production" / "data" / "continuity.yaml").read_text(encoding="utf-8"))["as_of"])      # nothing may be dated after the day the work was executed
REQUIRED_FILES = ["lesson.md", "outcomes.yaml", "source-map.yaml", "assessment/quiz.yaml", "assessment/quiz.md", "assessment/rubric.yaml",
                  "lab-guided/README.md", "lab-independent/README.md"]


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def anchors(path: Path) -> set[str]:
    out = set()
    for m in re.finditer(r"^#{1,6}\s+(.*)$", path.read_text(encoding="utf-8"), flags=re.M):
        out.add(re.sub(r"[^\w\- ]", "", m.group(1).strip().lower()).replace(" ", "-"))
    return out


def ids(modules=MODULES):
    return [m.name for m in modules]


@pytest.mark.parametrize("module", MODULES, ids=ids())
def test_required_files_exist(module):
    missing = [f for f in REQUIRED_FILES if not (module / f).exists()]
    assert missing == [], missing


@pytest.mark.parametrize("module", MODULES, ids=ids())
def test_lesson_front_matter_and_status(module):
    fm = front_matter(module / "lesson.md")
    assert fm["id"] == module.name
    for key in ("title", "course", "level", "audience", "prerequisites", "estimated_time_hours", "status", "versions_cited", "last_verified"):
        assert key in fm, key
    assert str(fm["last_verified"]) <= EXECUTION_DATE
    assert fm["status"].startswith("BUILT") and "NOT_SME_REVIEWED" in fm["status"], "a built module must not claim SME review"
    catalog = load(ROOT / "catalog" / "courses.yaml")
    module_row = next(m for c in catalog["courses"] for m in c["modules"] if m["id"] == module.name)
    assert fm["title"] == module_row["title"] and fm["level"] == module_row["level"]
    assert abs(fm["estimated_time_hours"]["total"] - module_row["estimated_hours"]) < 1e-6, "lesson time budget must equal the catalog's estimated_hours"


@pytest.mark.parametrize("module", MODULES, ids=ids())
def test_outcomes_are_taught_practised_assessed_and_graded(module):
    outcomes = load(module / "outcomes.yaml")["outcomes"]
    quiz = {q["id"]: q for q in load(module / "assessment" / "quiz.yaml")["items"]}
    rubric = {c["id"]: c for c in load(module / "assessment" / "rubric.yaml")["criteria"]}
    lesson_los = set(re.findall(r"^\| \*\*(LO\d+)\*\* \|", (module / "lesson.md").read_text(encoding="utf-8"), flags=re.M))
    assert lesson_los == {o["id"] for o in outcomes}
    for o in outcomes:
        assert o["instruction"] and o["practice"] and o["assessment"] and o["rubric"], o["id"]
        for ref in o["instruction"] + o["practice"]:
            rel, _, frag = ref.partition("#")
            target = module / rel
            assert target.exists(), f"{o['id']}: {ref}"
            if frag:
                assert frag in anchors(target), f"{o['id']}: anchor #{frag} not found in {rel}"
        for ref in o["assessment"]:
            kind, _, name = ref.partition(":")
            if kind == "quiz":
                assert name in quiz and quiz[name]["outcome"] == o["id"], f"{o['id']}: {ref} must exist and be tagged to the outcome"
            elif kind == "rubric":
                assert name in rubric and o["id"] in rubric[name]["outcomes"], f"{o['id']}: {ref}"
            else:
                assert kind == "lab-check" and name, ref
        for c in o["rubric"]:
            assert c in rubric and o["id"] in rubric[c]["outcomes"]
        assert any(r.startswith(("quiz:", "lab-check:")) for r in o["assessment"]), f"{o['id']} needs a quiz item or an automated check"
    for q in quiz.values():
        assert q["outcome"] in lesson_los


@pytest.mark.parametrize("module", MODULES, ids=ids())
def test_quiz_has_no_answers_and_matches_its_rendering(module):
    path = module / "assessment" / "quiz.yaml"
    quiz = load(path)
    assert len(quiz["items"]) == 8
    seen = set()
    for item in quiz["items"]:
        assert item["id"] not in seen
        seen.add(item["id"])
        assert set(item) == {"id", "outcome", "stem", "options"}, f"{item['id']}: no answer/key fields allowed in the public quiz"
        assert list(item["options"]) == ["A", "B", "C", "D"]
        assert len({str(v) for v in item["options"].values()}) == 4, f"{item['id']}: options must differ"
    assert (module / "assessment" / "quiz.md").read_text(encoding="utf-8") == render_module_assets.render_quiz(quiz)


@pytest.mark.parametrize("module", MODULES, ids=ids())
def test_rubric_is_well_formed(module):
    rubric = load(module / "assessment" / "rubric.yaml")
    assert rubric["module"] == module.name and rubric["pass_rule"]
    cids = [c["id"] for c in rubric["criteria"]]
    assert len(cids) == len(set(cids))
    outcome_ids = {o["id"] for o in load(module / "outcomes.yaml")["outcomes"]}
    assert any(c.get("must_pass") for c in rubric["criteria"])
    covered = set()
    for c in rubric["criteria"]:
        assert c["kind"] in ("automated", "reviewer")
        assert set(c["outcomes"]) <= outcome_ids
        covered |= set(c["outcomes"])
        if c["kind"] == "reviewer":
            assert c["max"] == 3 and set(c["levels"]) == {0, 1, 2, 3}
        else:
            assert c["measure"]
    assert covered == outcome_ids, "every outcome must be covered by at least one rubric criterion"


@pytest.mark.parametrize("module", MODULES, ids=ids())
def test_source_map_points_at_real_pages_and_findings(module):
    smap = load(module / "source-map.yaml")
    parts = json.loads((ROOT / "docs/audits/data/page_records/INDEX.json").read_text(encoding="utf-8"))["parts"]
    pages = max(p["last_page"] for p in parts if p["source_id"] == smap["source"])
    findings = {f["id"] for f in load(ROOT / "docs/audits/data/findings.yaml")["findings"]}
    assert smap["mappings"]
    for m in smap["mappings"]:
        assert m["disposition"] in {"REPLACED", "RETAINED_IDEA", "CORRECTED", "DROPPED"}
        assert all(isinstance(p, int) and 1 <= p <= pages for p in m["source_pages"])
        cited = set(re.findall(r"F-[A-Z]+-\d{3}", m["note"]))
        assert cited <= findings
    assert any(re.search(r"F-[A-Z]+-\d{3}", m["note"]) for m in smap["mappings"]), "at least one mapping must cite the finding it addresses"


@pytest.mark.parametrize("module", MODULES, ids=ids())
def test_lesson_code_blocks_execute(module):
    results = lesson_blocks.execute((module / "lesson.md").read_text(encoding="utf-8"))
    assert results, "a built lesson must contain executable examples"
    failed = [r for r in results if not r["ok"]]
    assert failed == [], failed


def test_public_files_contain_no_instructor_material():
    tracked = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "courses"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    for rel in tracked:
        if "/instructor/" in rel:
            assert rel.endswith("/instructor/README.md"), f"instructor material must stay private: {rel}"
        elif rel.endswith((".md", ".yaml", ".py", ".json", ".toml")) and "/modules/" in rel:
            text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
            assert "INSTRUCTORS ONLY" not in text, rel


def test_course_readme_lists_exactly_the_built_modules():
    catalog = load(ROOT / "catalog" / "courses.yaml")
    for course in catalog["courses"]:
        folder = ROOT / "courses" / course["slug"]
        if not (folder / "modules").exists():
            continue
        built = sorted(m["id"] for m in course["modules"] if m["status"] != "PLANNED" and (folder / "modules" / m["id"]).exists())
        on_disk = sorted(p.name for p in (folder / "modules").iterdir() if (p / "lesson.md").exists())
        readme = (folder / "README.md").read_text(encoding="utf-8")
        listed = sorted(set(re.findall(r"^\| (PY-M\d+|[A-Z]+-M\d+) \|", readme, flags=re.M)))
        assert built == on_disk == listed, (built, on_disk, listed)
