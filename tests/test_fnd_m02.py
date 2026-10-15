"""FND-M02 focused implementation checks. Not full content or human review."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "courses/digital-foundations/modules/FND-M02"


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_course_module_identity_and_source_provenance():
    content = (M / "lesson.md").read_text(encoding="utf-8")
    meta = _yaml(M / "source-map.yaml")
    assert content.startswith("---\n")
    assert meta["source"] is None
    assert meta["origin"] == "NEW_ORIGINAL_FOUNDATIONS_CURRICULUM"
    assert meta["mappings"] == []


def test_lesson_is_substantive_and_examples_execute():
    content = (M / "lesson.md").read_text(encoding="utf-8")
    assert len(content.split()) >= 1800
    blocks = re.findall(r"`{3}python run\n(.*?)`{3}", content, re.S)
    assert len(blocks) >= 4
    for block in blocks:
        exec(compile(block, "<fnd-m02-example>", "exec"), {"__name__": "__main__"})


def test_guided_reference_contracts_are_executable():
    folder = M / "lab-guided/checks"
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(folder), "-p", "test_runbook.py"],
                          cwd=folder, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Ran 14 tests" in proc.stderr


def test_independent_student_starter_is_intentionally_unfinished():
    folder = M / "lab-independent/checks"
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(folder), "-p", "test_tracecheck.py"],
                          cwd=folder, capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert "Ran 9 tests" in proc.stderr
    assert "NotImplementedError" in proc.stderr
    assert "ModuleNotFoundError" not in proc.stderr


def test_outcome_links_and_all_quiz_items():
    outcomes = _yaml(M / "outcomes.yaml")["outcomes"]
    quiz = _yaml(M / "assessment/quiz.yaml")["items"]
    rubric = _yaml(M / "assessment/rubric.yaml")["criteria"]
    assert len(outcomes) == 4 and len(quiz) == 8
    assert {x["id"] for x in outcomes} == {x["outcome"] for x in quiz}
    assert {x["id"] for x in rubric} == {"C1", "C2", "C3", "C4"}
    for outcome in outcomes:
        for ref in outcome["instruction"] + outcome["practice"]:
            path, sep, anchor = ref.partition("#")
            assert sep
            headings = re.findall(r"^#{1,6}\s+(.+)$", (M / path).read_text(encoding="utf-8"), re.M)
            normalized = [re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-") for h in headings]
            assert anchor in normalized, ref


def test_public_student_config_never_includes_instructor_material():
    config = _yaml(ROOT / "courses/digital-foundations/student/FND-M02-student-edition.yaml")
    assert config["edition"] == "student-preview"
    assert config["module"] == "FND-M02"
    assert all("/instructor/" not in item and "/solution/" not in item for item in config["include"])
    assert set(config["include"]) == {
        f"courses/digital-foundations/modules/FND-M02/{filename}"
        for filename in ("lesson.md", "lab-guided/README.md", "lab-independent/README.md", "assessment/quiz.md")
    }
