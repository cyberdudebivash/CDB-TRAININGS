"""The learner dry run decides per lab whether the checks/ folder grades it; a lab it misjudges is never run against its public solution."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
import learner_dry_run as D  # noqa: E402


def lab(tmp_path: Path, ini: str | None, checks: bool) -> Path:
    if ini is not None:
        (tmp_path / "pytest.ini").write_text(ini, encoding="utf-8")
    if checks:
        (tmp_path / "checks").mkdir()
    return tmp_path


@pytest.mark.parametrize("ini, checks, graded", [
    ("[pytest]\ntestpaths = checks\n", True, True),           # the usual layout
    (None, True, True),                                       # PY-M10: no pytest.ini, `python -m pytest` runs checks/
    ("[pytest]\ntestpaths = student_tests\n", True, False),    # write-your-own-tests lab, graded by the mutation tool
    ("[pytest]\naddopts = -q\n", False, False),               # nothing to run
    (None, False, False),
])
def test_is_graded(tmp_path, ini, checks, graded):
    assert D.is_graded(lab(tmp_path, ini, checks)) is graded


def test_the_python_engineering_labs_that_ship_a_solution_and_checks_are_graded():
    for solution in sorted((ROOT / "courses" / "python-engineering" / "modules").glob("PY-M*/lab-guided/solution")):
        guided = solution.parent
        if (guided / "checks").is_dir():
            assert D.is_graded(guided) == (D.testpaths(guided) != "student_tests"), guided
