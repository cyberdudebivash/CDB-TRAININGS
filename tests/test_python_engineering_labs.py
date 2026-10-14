"""Executes the Python Engineering labs: each starter fails exactly where it should, each public reference passes, and test suites are graded by mutation.

Instructor-only references (git-ignored) are used when present; without them those tests report SKIPPED_PRIVATE_MATERIALS, which means *not verified*, never passed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / "courses" / "python-engineering"
TOOL = COURSE / "labs" / "_tools" / "mutation_check.py"
PRIVATE = COURSE / "instructor"
pytestmark = pytest.mark.filterwarnings("ignore")


def run_pytest(cwd: Path, *args: str, env: dict | None = None, timeout: int = 900) -> dict[str, str]:
    """Run pytest in a lab folder and return {test id: outcome}."""
    xml = cwd / ".junit-lab.xml"
    e = dict(os.environ)
    e.update(env or {})
    subprocess.run([sys.executable, "-m", "pytest", *args, f"--junitxml={xml}", "-q", "-p", "no:cacheprovider", "--tb=no"], cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout)
    results: dict[str, str] = {}
    try:
        for tc in ET.parse(xml).getroot().iter("testcase"):
            outcome = "failed" if tc.find("failure") is not None else "error" if tc.find("error") is not None else "skipped" if tc.find("skipped") is not None else "passed"
            results[tc.get("name")] = outcome
    finally:
        xml.unlink(missing_ok=True)
    return results


def mutation(module_dir: Path, module: str, tests: Path, mutants: Path) -> dict:
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(module_dir), "--module", module, "--tests", str(tests), "--mutants", str(mutants), "--json"],
                          capture_output=True, text=True, timeout=1200)
    return json.loads(proc.stdout)


def failing(results: dict[str, str]) -> set[str]:
    return {k for k, v in results.items() if v in ("failed", "error")}


# ------------------------------------------------------------------------------------------------------------------ PY-M02
M02 = COURSE / "modules" / "PY-M02"


def test_m02_guided_reference_tests_kill_every_mutant():
    lab = M02 / "lab-guided"
    report = mutation(lab / "solution", "orderkit", lab / "solution" / "test_orderkit.py", lab / "checks" / "mutants.json")
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 3
    assert report["all_killed"] == report["total"] == 7, [m for m in report["mutants"] if not m["killed"]]


def test_m02_guided_reference_tests_detect_the_three_seeded_defects_in_the_starter():
    lab = M02 / "lab-guided"
    env = {"PYTHONPATH": str(lab / "starter")}
    results = run_pytest(lab / "solution", "test_orderkit.py", "--import-mode=importlib", "-o", f"pythonpath={lab / 'starter'}", env=env)
    bad = failing(results)
    assert any("parse_quantity_rejects" in n for n in bad), "defect 3 (swallowed error) not detected"
    assert any("bulk_discount" in n and "10" in n for n in bad), "defect 2 (boundary) not detected"
    assert any("add_line_starts_a_fresh_basket" in n for n in bad), "defect 1 (shared default) not detected"
    assert not any("accepts_positive_whole_numbers" in n for n in bad), "valid behaviour must not fail"


def test_m02_guided_template_is_a_starting_point_not_a_solution():
    lab = M02 / "lab-guided"
    report = mutation(lab / "solution", "orderkit", lab / "student_tests", lab / "checks" / "mutants.json")
    assert report["baseline_passes"] and not report["passed"] and report["required_killed"] == 0


def test_m02_independent_starter_is_correct_and_template_is_empty():
    lab = M02 / "lab-independent"
    results = run_pytest(lab)
    assert results == {}, "the independent template must not contain tests"
    sys.path.insert(0, str(lab / "starter"))
    try:
        import importlib

        splitkit = importlib.import_module("splitkit")
        from decimal import Decimal

        assert sum(splitkit.split_bill(Decimal("100.00"), 7)) == Decimal("100.00")
    finally:
        sys.path.pop(0)
        sys.modules.pop("splitkit", None)


@pytest.mark.private_materials
def test_m02_independent_reference_suite_kills_hidden_mutants():
    ref = PRIVATE / "PY-M02" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    lab = M02 / "lab-independent"
    report = mutation(lab / "starter", "splitkit", ref / "test_splitkit.py", ref / "mutants.json")
    assert report["baseline_passes"] and report["required_killed"] == report["required_total"] == 12


# ------------------------------------------------------------------------------------------------------------------ PY-M04
M04 = COURSE / "modules" / "PY-M04"
M04_STARTER_FAILS = {"test_setup_py_is_gone", "test_build_system_is_declared", "test_project_metadata", "test_development_tools_live_in_a_dependency_group",
                     "test_wheel_contains_the_package_but_not_the_tests", "test_sdist_contains_sources_and_metadata"}


def test_m04_guided_solution_passes_every_check():
    results = run_pytest(M04 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 10 and failing(results) == set(), results


def test_m04_guided_legacy_starter_fails_exactly_the_modernisation_checks():
    results = run_pytest(M04 / "lab-guided")
    assert failing(results) == M04_STARTER_FAILS, results
    assert results["test_build_succeeds_and_produces_sdist_and_wheel"] == "passed", "a setup.py project still builds with python -m build"


def test_m04_independent_starter_fails_until_the_packaging_is_written():
    results = run_pytest(M04 / "lab-independent")
    assert len(results) == 9
    assert results["test_only_pyproject_describes_the_build"] == "passed" and results["test_report_script_still_runs_without_rich"] == "passed"
    assert len(failing(results)) == 7, results


@pytest.mark.private_materials
def test_m04_independent_reference_overlay_passes_every_check():
    ref = PRIVATE / "PY-M04" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    results = run_pytest(M04 / "lab-independent", env={"LAB_OVERLAY": str(ref)})
    assert len(results) == 9 and failing(results) == set(), results


# ------------------------------------------------------------------------------------------------------------------ PY-M07
M07 = COURSE / "modules" / "PY-M07"


def test_m07_guided_solution_passes_every_check():
    results = run_pytest(M07 / "lab-guided", env={"LAB_TARGET": "solution"}, timeout=300)
    assert len(results) >= 50 and failing(results) == set(), failing(results)


def test_m07_guided_starter_works_but_is_vulnerable_in_all_eight_areas():
    results = run_pytest(M07 / "lab-guided", timeout=300)
    bad = failing(results)
    assert bad and all(n.startswith(("test_exploit_", "test_static_")) for n in bad), [n for n in bad if n.startswith("test_works_")]
    for area in ("calculator", "sql", "shell", "path_traversal", "session_loader", "yaml_loader", "tls_context", "password_hashes"):
        assert any(area in n for n in bad), f"no exploit check fails for {area}"
    assert all(v == "passed" for k, v in results.items() if k.startswith("test_works_")), "behaviour that must be kept fails on the starter"


def test_m07_guided_reference_regression_tests_kill_every_vulnerability_mutant():
    lab = M07 / "lab-guided"
    report = mutation(lab / "solution", "helpdesk", lab / "solution" / "test_regressions.py", lab / "checks" / "mutants.json")
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 8
    survivors = {m["id"] for m in report["mutants"] if not m["killed"]}
    assert survivors == {"S5-timing-unsafe-compare"}, survivors


def test_m07_guided_template_has_no_tests_yet():
    lab = M07 / "lab-guided"
    report = mutation(lab / "solution", "helpdesk", lab / "student_tests", lab / "checks" / "mutants.json")
    assert not report["passed"] and report["required_killed"] == 0


@pytest.mark.private_materials
def test_m07_independent_reference_is_secure_and_starter_is_not():
    ref = PRIVATE / "PY-M07" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    suite = ref / "test_exploits.py"
    secure = run_pytest(ref, str(suite), "--import-mode=importlib", "-o", f"pythonpath={ref}")
    assert secure and failing(secure) == set(), failing(secure)
    starter = M07 / "lab-independent" / "starter"
    vulnerable = run_pytest(ref, str(suite), "--import-mode=importlib", "-o", f"pythonpath={starter}")
    assert all(v == "passed" for k, v in vulnerable.items() if k.startswith("test_works_"))
    assert len([k for k in failing(vulnerable)]) >= 15
    report = mutation(ref, "notes_service", suite, ref / "mutants.json")
    assert report["baseline_passes"] and report["required_killed"] == report["required_total"] == 9


# ------------------------------------------------------------------------------------------------------------------ PY-M03
M03 = COURSE / "modules" / "PY-M03"


def test_m03_guided_solution_passes_every_check():
    results = run_pytest(M03 / "lab-guided", env={"LAB_TARGET": "solution"}, timeout=600)
    assert len(results) == 27 and failing(results) == set(), failing(results)


def test_m03_guided_starter_script_has_the_three_hidden_defects():
    lab = M03 / "lab-guided" / "starter"
    results = run_pytest(lab)
    assert results["test_total_value_of_the_sample"] == "passed"
    assert {k for k, v in results.items() if v == "failed"} == {"test_low_stock_compares_numbers_not_text", "test_unknown_focus_sku_is_a_clear_error",
                                                              "test_restock_plan_within_budget", "test_restock_plan_over_budget_is_an_error_not_none"}
    default = subprocess.run([sys.executable, "-m", "mypy", "inventory.py"], cwd=lab, capture_output=True, text=True)
    strict = subprocess.run([sys.executable, "-m", "mypy", "--strict", "--show-error-codes", "inventory.py"], cwd=lab, capture_output=True, text=True)
    assert default.returncode == 0, "default mypy skips untyped functions"
    assert strict.returncode == 1 and strict.stdout.count("[no-untyped-def]") >= 6 and strict.stdout.count("error:") >= 10
    shutil.rmtree(lab / ".mypy_cache", ignore_errors=True)


def test_m03_guided_starter_fails_every_package_check():
    results = run_pytest(M03 / "lab-guided", timeout=600)
    assert len(results) == 27 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


def test_m03_independent_starter_is_untyped_cyclic_and_failing():
    lab = M03 / "lab-independent"
    results = run_pytest(lab, timeout=600)
    assert len(results) == 30 and set(results.values()) <= {"failed", "error"}
    starter = lab / "starter"
    first = subprocess.run([sys.executable, "-c", "import models"], cwd=starter, capture_output=True, text=True)
    second = subprocess.run([sys.executable, "-c", "import report"], cwd=starter, capture_output=True, text=True)
    assert first.returncode != 0 and "cannot import name 'Trip'" in first.stderr, "import order decides whether the cycle bites"
    assert second.returncode == 0
    strict = subprocess.run([sys.executable, "-m", "mypy", "--strict", "."], cwd=starter, capture_output=True, text=True)
    assert strict.returncode == 1 and "Found 27 errors" in strict.stdout, strict.stdout[-300:]
    shutil.rmtree(starter / ".mypy_cache", ignore_errors=True)


@pytest.mark.private_materials
def test_m03_independent_reference_passes_every_check():
    ref = PRIVATE / "PY-M03" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    results = run_pytest(M03 / "lab-independent", env={"LAB_PROJECT": str(ref)}, timeout=600)
    assert len(results) == 30 and failing(results) == set(), failing(results)
