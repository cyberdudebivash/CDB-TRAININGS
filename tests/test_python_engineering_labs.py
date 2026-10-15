"""Executes the Python Engineering labs: each starter fails exactly where it should, each public reference passes, and test suites are graded by mutation.

Instructor-only references (git-ignored) are used when present; without them those tests report SKIPPED_PRIVATE_MATERIALS, which means *not verified*, never passed.
"""
from __future__ import annotations

import json
import os
import re
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


def mutation(module_dir: Path, module: str, tests: Path, mutants: Path, jobs: int = 1) -> dict:
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(module_dir), "--module", module, "--tests", str(tests), "--mutants", str(mutants), "--json", "--jobs", str(jobs)],
                          capture_output=True, text=True, timeout=1200)
    return json.loads(proc.stdout)


def failing(results: dict[str, str]) -> set[str]:
    return {k for k, v in results.items() if v in ("failed", "error")}


# ------------------------------------------------------------------------------------------------------------------ PY-M01
M01 = COURSE / "modules" / "PY-M01"


def test_m01_guided_solution_passes_every_check():
    results = run_pytest(M01 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 21 and failing(results) == set(), failing(results)


def test_m01_guided_starter_fails_every_check():
    results = run_pytest(M01 / "lab-guided")
    assert len(results) == 21 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


def test_m01_independent_starter_fails_the_published_examples():
    results = run_pytest(M01 / "lab-independent")
    assert list(results.values()) == ["failed"], results


@pytest.mark.private_materials
def test_m01_independent_reference_passes_examples_hidden_suite_and_report_script():
    ref = PRIVATE / "PY-M01" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    assert list(run_pytest(M01 / "lab-independent", env={"LAB_PROJECT": str(ref)}).values()) == ["passed"]
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)})
    assert len(hidden) == 34 and failing(hidden) == set(), failing(hidden)
    sample = M01 / "lab-independent" / "starter" / "sample.log"
    done = subprocess.run([sys.executable, "report.py", str(sample)], cwd=ref, capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(ref)))
    assert done.returncode == 0 and json.loads(done.stdout) == {
        "levels": {"DEBUG": 1, "INFO": 2, "WARNING": 1, "ERROR": 2, "INVALID": 1},
        "top_messages": [["service started", 2], ["cache warm", 1], ["paiement \u00e9chou\u00e9 for order 7", 1]],
        "busiest_hour": "2026-10-14 09"}
    assert "\\u00e9" not in done.stdout, "accented letters must not be escaped"
    missing = subprocess.run([sys.executable, "report.py", str(ref / "no-such-file.log")], cwd=ref, capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(ref)))
    assert missing.returncode == 2 and "Traceback" not in missing.stderr and missing.stderr.count("\n") == 1


@pytest.mark.private_materials
def test_m01_independent_hidden_suite_is_discriminating_and_starter_fails_it():
    ref = PRIVATE / "PY-M01" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    report = mutation(ref, "logkit", ref / "test_hidden.py", ref / "mutants.json")
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 16 and report["all_killed"] == report["total"] == 16
    starter = M01 / "lab-independent" / "starter"
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(starter)})
    assert len(results) == 34 and set(results.values()) <= {"failed", "error"}


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


# ------------------------------------------------------------------------------------------------------------------ PY-M05
M05 = COURSE / "modules" / "PY-M05"


def test_m05_guided_solution_passes_every_check():
    results = run_pytest(M05 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 65 and failing(results) == set(), failing(results)


def test_m05_guided_starter_fails_every_check():
    results = run_pytest(M05 / "lab-guided")
    assert len(results) == 65 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


def test_m05_independent_starter_fails_every_published_check():
    results = run_pytest(M05 / "lab-independent")
    assert len(results) == 8 and set(results.values()) <= {"failed", "error"}, results


@pytest.mark.private_materials
def test_m05_independent_reference_passes_published_and_hidden_checks():
    ref = PRIVATE / "PY-M05" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M05 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == 8 and failing(published) == set(), failing(published)
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)}, timeout=1200)
    assert len(hidden) == 138 and failing(hidden) == set(), failing(hidden)


@pytest.mark.private_materials
def test_m05_independent_hidden_suite_is_discriminating_and_starter_fails_it():
    ref = PRIVATE / "PY-M05" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    report = mutation(ref, "feedsync", ref / "test_hidden.py", ref / "mutants.json", jobs=3)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 30 and report["all_killed"] == report["total"] == 30, [m for m in report["mutants"] if not m["killed"]]
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(M05 / "lab-independent" / "starter")}, timeout=1200)
    assert len(results) == 138 and set(results.values()) <= {"failed", "error"}


# ------------------------------------------------------------------------------------------------------------------ PY-M06
M06 = COURSE / "modules" / "PY-M06"


def test_m06_guided_solution_passes_every_check():
    results = run_pytest(M06 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 36 and failing(results) == set(), failing(results)


def test_m06_guided_starter_fails_every_check():
    results = run_pytest(M06 / "lab-guided")
    assert len(results) == 36 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


@pytest.mark.private_materials
def test_m06_guided_checks_are_discriminating():
    mutants = PRIVATE / "PY-M06" / "guided-mutants.json"
    if not mutants.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    solution = M06 / "lab-guided" / "solution"
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(solution), "--module", "jobrunner", "--tests", str(M06 / "lab-guided" / "checks"), "--mutants", str(mutants), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 12 and report["total"] == 13, [m for m in report["mutants"] if not m["killed"]]


def test_m06_independent_starter_fails_every_published_check():
    results = run_pytest(M06 / "lab-independent")
    assert len(results) == 10 and set(results.values()) <= {"failed", "error"}, results


@pytest.mark.private_materials
def test_m06_independent_reference_passes_published_and_hidden_checks():
    ref = PRIVATE / "PY-M06" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M06 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == 10 and failing(published) == set(), failing(published)
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)}, timeout=1200)
    assert len(hidden) == 45 and failing(hidden) == set(), failing(hidden)


@pytest.mark.private_materials
def test_m06_independent_hidden_suite_is_discriminating_and_starter_fails_it():
    ref = PRIVATE / "PY-M06" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    report = mutation(ref, "wordjob", ref / "test_hidden.py", ref / "mutants.json", jobs=3)
    assert report["baseline_passes"], report["baseline_tail"]
    assert report["passed"], [m for m in report["mutants"] if not m["killed"]]
    assert report["required_killed"] == report["required_total"] == 21 and report["all_killed"] == report["total"] == 21, [m for m in report["mutants"] if not m["killed"]]
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(M06 / "lab-independent" / "starter")}, timeout=1200)
    assert len(results) == 45 and set(results.values()) <= {"failed", "error"}


# ------------------------------------------------------------------------------------------------------------------ PY-M12
M12 = COURSE / "modules" / "PY-M12"


def test_m12_guided_solution_passes_every_check():
    results = run_pytest(M12 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 167 and failing(results) == set(), failing(results)


def test_m12_guided_starter_fails_every_check():
    results = run_pytest(M12 / "lab-guided")
    assert len(results) == 167 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


@pytest.mark.private_materials
def test_m12_guided_checks_are_discriminating():
    mutants = PRIVATE / "PY-M12" / "guided-mutants.json"
    if not mutants.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    solution = M12 / "lab-guided" / "solution"
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(solution), "--module", "ledgerkit", "--tests", str(M12 / "lab-guided" / "checks"), "--mutants", str(mutants), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 47 and report["total"] == 47, [m for m in report["mutants"] if not m["killed"]]


def test_m12_independent_starter_fails_every_published_check():
    results = run_pytest(M12 / "lab-independent")
    assert len(results) == 10 and set(results.values()) <= {"failed", "error"}, results


@pytest.mark.private_materials
def test_m12_independent_reference_passes_published_and_hidden_checks():
    ref = PRIVATE / "PY-M12" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M12 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == 10 and failing(published) == set(), failing(published)
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)})
    assert len(hidden) == 54 and failing(hidden) == set(), failing(hidden)


@pytest.mark.private_materials
def test_m12_independent_hidden_suite_is_discriminating_and_starter_fails_it():
    ref = PRIVATE / "PY-M12" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(ref), "--module", "rulekit", "--tests", str(ref / "test_hidden.py"), "--mutants", str(ref / "mutants.json"), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 41 and report["all_killed"] == report["total"] == 41, [m for m in report["mutants"] if not m["killed"]]
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(M12 / "lab-independent" / "starter")})
    assert len(results) == 54 and set(results.values()) <= {"failed", "error"}


# ------------------------------------------------------------------------------------------------------------------ PY-M13
M13 = COURSE / "modules" / "PY-M13"


def test_m13_guided_solution_passes_every_check():
    results = run_pytest(M13 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 128 and failing(results) == set(), failing(results)


def test_m13_guided_starter_fails_every_check():
    results = run_pytest(M13 / "lab-guided")
    assert len(results) == 128 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


@pytest.mark.private_materials
def test_m13_guided_checks_are_discriminating():
    mutants = PRIVATE / "PY-M13" / "guided-mutants.json"
    if not mutants.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    solution = M13 / "lab-guided" / "solution"
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(solution), "--module", "streamkit", "--tests", str(M13 / "lab-guided" / "checks"), "--mutants", str(mutants), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 49 and report["total"] == 49, [m for m in report["mutants"] if not m["killed"]]


def test_m13_independent_starter_fails_every_published_check():
    results = run_pytest(M13 / "lab-independent")
    assert len(results) == 10 and set(results.values()) <= {"failed", "error"}, results


@pytest.mark.private_materials
def test_m13_independent_reference_passes_published_and_hidden_checks():
    ref = PRIVATE / "PY-M13" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M13 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == 10 and failing(published) == set(), failing(published)
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)})
    assert len(hidden) == 63 and failing(hidden) == set(), failing(hidden)


@pytest.mark.private_materials
def test_m13_independent_hidden_suite_is_discriminating_and_starter_fails_it():
    ref = PRIVATE / "PY-M13" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(ref), "--module", "flowkit", "--tests", str(ref / "test_hidden.py"), "--mutants", str(ref / "mutants.json"), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 35 and report["all_killed"] == report["total"] == 35, [m for m in report["mutants"] if not m["killed"]]
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(M13 / "lab-independent" / "starter")})
    assert len(results) == 63 and set(results.values()) <= {"failed", "error"}


# ------------------------------------------------------------------------------------------------------------------ PY-M08
M08 = COURSE / "modules" / "PY-M08"


def test_m08_guided_solution_passes_every_check():
    results = run_pytest(M08 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 200 and failing(results) == set(), failing(results)


def test_m08_guided_starter_fails_every_check():
    results = run_pytest(M08 / "lab-guided")
    assert len(results) == 200 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


def test_m08_part1_contract_still_runs_with_the_standard_library_alone():
    """The 14 contract tests of the first increment of this lab keep working with the command that increment documented (unittest, PY_M08_TARGET)."""
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "checks", "-p", "test_eventstore.py"], cwd=M08 / "lab-guided",
                          env=dict(os.environ, PY_M08_TARGET="solution"), capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0 and "Ran 14 tests" in proc.stderr, proc.stderr[-400:]


@pytest.mark.private_materials
def test_m08_guided_checks_are_discriminating():
    mutants = PRIVATE / "PY-M08" / "guided-mutants.json"
    if not mutants.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    solution = M08 / "lab-guided" / "solution"
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(solution), "--module", "eventstore", "--tests", str(M08 / "lab-guided" / "checks"), "--mutants", str(mutants), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 95 and report["total"] == 95, [m for m in report["mutants"] if not m["killed"]]


def test_m08_independent_starter_fails_every_published_check():
    results = run_pytest(M08 / "lab-independent")
    assert len(results) == 10 and set(results.values()) <= {"failed", "error"}, results


@pytest.mark.private_materials
def test_m08_independent_reference_passes_published_and_hidden_checks():
    ref = PRIVATE / "PY-M08" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M08 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == 10 and failing(published) == set(), failing(published)
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)})
    assert len(hidden) == 145 and failing(hidden) == set(), failing(hidden)


@pytest.mark.private_materials
def test_m08_independent_hidden_suite_is_discriminating_and_starter_fails_it():
    ref = PRIVATE / "PY-M08" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(ref), "--module", "casestore", "--tests", str(ref / "test_hidden.py"), "--mutants", str(ref / "mutants.json"), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 83 and report["all_killed"] == report["total"] == 83, [m for m in report["mutants"] if not m["killed"]]
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(M08 / "lab-independent" / "starter")})
    assert len(results) == 145 and set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


# ------------------------------------------------------------------------------------------------------------------ PY-M09
M09 = COURSE / "modules" / "PY-M09"
M09_STARTER_KEEPS_PASSING = 145      # the correctness checks: the starter is correct, only slow; they are the safety net of the refactoring
M09_SAFETY_NET = {
    "test_every_function_gives_the_slow_programs_answer_on_edge_cases", "test_n_must_be_a_non_negative_int", "test_random_inputs_give_the_slow_programs_answers",
    "test_the_fast_analysis_gives_the_slow_programs_report", "test_the_functions_accept_any_iterable_of_attempts", "test_threshold_and_window_must_be_positive_ints",
    "test_every_line_parses_as_the_slow_program_parses_it", "test_valid_lines_really_parse", "test_the_lines_are_read_once_and_not_kept",
    "test_a_list_source_gives_the_lines_it_was_given", "test_the_core_does_no_input_or_output_and_does_not_know_the_edge", "test_the_report_text_has_the_documented_shape",
}


def test_m09_guided_solution_passes_every_check():
    results = run_pytest(M09 / "lab-guided", env={"LAB_TARGET": "solution"})
    assert len(results) == 196 and failing(results) == set(), failing(results)


def test_m09_guided_starter_fails_every_speed_memory_profile_and_edge_check_and_keeps_the_safety_net_green():
    results = run_pytest(M09 / "lab-guided")
    assert len(results) == 196
    passed = {k for k, v in results.items() if v == "passed"}
    assert len(passed) == M09_STARTER_KEEPS_PASSING, len(passed)
    for name in ("test_the_whole_analysis_is_at_least_30_percent_faster_than_the_slow_program", "test_unique_ips_scales_linearly", "test_bursts_scales_with_the_number_of_failures_of_one_address",
                 "test_top_users_scales_with_the_number_of_users", "test_the_analysis_of_a_stream_needs_far_less_memory_than_the_slow_program",
                 "test_the_pattern_is_not_compiled_once_per_line", "test_main_writes_the_report_to_the_given_stream", "test_on_the_slow_program_the_hotspot_is_top_users"):
        assert results[name] in ("failed", "error"), name
    assert not any(k.startswith("test_profile_") or k.startswith("test_top_") for k in passed)
    assert {k.split("[")[0] for k in passed} == M09_SAFETY_NET, sorted({k.split("[")[0] for k in passed} ^ M09_SAFETY_NET)


@pytest.mark.private_materials
def test_m09_guided_checks_are_discriminating():
    mutants = PRIVATE / "PY-M09" / "guided-mutants.json"
    if not mutants.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    solution = M09 / "lab-guided" / "solution"
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(solution), "--module", "perfkit", "--tests", str(M09 / "lab-guided" / "checks"), "--mutants", str(mutants), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1800, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 59 and report["total"] == 59, [m for m in report["mutants"] if not m["killed"]]


def test_m09_independent_starter_fails_the_scaling_check_and_the_check_for_budget_tests():
    results = run_pytest(M09 / "lab-independent")
    assert len(results) == 10
    assert {k for k, v in results.items() if v != "passed"} == {"test_collapse_work_grows_roughly_linearly_with_the_number_of_incidents", "test_you_have_written_budget_tests_of_your_own"}, results


@pytest.mark.private_materials
def test_m09_independent_reference_passes_published_and_hidden_checks():
    ref = PRIVATE / "PY-M09" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M09 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == 10 and failing(published) == set(), failing(published)
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)})
    assert len(hidden) == 378 and failing(hidden) == set(), failing(hidden)


@pytest.mark.private_materials
def test_m09_independent_hidden_suite_is_discriminating_and_the_starter_fails_its_scaling_and_budget_checks():
    ref = PRIVATE / "PY-M09" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(ref), "--module", "triage", "--tests", str(ref / "test_hidden.py"), "--mutants", str(ref / "mutants.json"), "--json", "--jobs", "3"],
                          capture_output=True, text=True, timeout=1800, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 52 and report["all_killed"] == report["total"] == 52, [m for m in report["mutants"] if not m["killed"]]
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(M09 / "lab-independent" / "starter")})
    assert len(results) == 378
    for name in ("test_collapse_scales_with_the_number_of_incidents", "test_rank_of_all_incidents_scales", "test_summarize_with_many_rules_scales",
                 "test_the_pattern_is_not_compiled_for_every_message", "test_the_learner_wrote_enough_tests", "test_the_whole_pipeline_is_at_least_30_percent_faster_than_the_original"):
        assert results[name] in ("failed", "error"), name


# ------------------------------------------------------------------------------------------------------------------ the evidence report
def test_the_lab_evidence_renderer_recognises_every_lab_row():
    """Regression for DEF-019: the report once matched only module numbers PY-M01 to PY-M09, so rows of later modules read 'not run' although the matrix had executed them."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_lab_evidence_under_test", ROOT / "scripts" / "validation" / "render_lab_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for key, _label, _property in module.LABS:
        assert module.lab_key(f"tests/test_python_engineering_labs.py::test_{key}_probe") == key, key
    assert module.lab_key("tests/test_module_packs.py::test_m10_guided_probe") is None


# ------------------------------------------------------------------------------------------------------------------ PY-M10
M10 = COURSE / "modules" / "PY-M10"
M10_GUIDED_CHECKS = 1625
M10_STARTER_GIVEN = frozenset({        # the checks that the given parts of the starter (models, table, headers, error class) already satisfy; nothing a learner has to write is in this set
    "test_a_body_may_contain_tab_newline_and_carriage_return_but_no_other_control_character",
    "test_a_minimal_ticket_is_valid_and_the_priority_defaults_to_normal",
    "test_a_ticket_is_a_frozen_value",
    "test_an_api_error_becomes_a_problem_with_its_own_status_code_detail_and_headers",
    "test_any_other_priority_is_refused",
    "test_at_most_one_type_ignore_and_it_names_its_error",
    "test_auth_error_carries_its_code",
    "test_every_editable_field_has_the_limits_of_a_new_ticket",
    "test_every_function_has_annotated_parameters_and_result",
    "test_every_listed_priority_is_accepted",
    "test_every_noqa_names_one_rule_and_says_why",
    "test_header_values_gives_every_value_of_a_header_in_order",
    "test_limit_is_one_to_100",
    "test_list_params_defaults",
    "test_mypy_strict_is_clean",
    "test_no_secret_is_written_into_the_module_itself",
    "test_nothing_is_coerced_into_a_string",
    "test_offset_is_zero_to_10000",
    "test_ordinary_unusual_text_is_data_and_is_kept_exactly",
    "test_other_scope_types_go_straight_to_the_application",
    "test_page_has_items_total_limit_and_offset",
    "test_problem_describes_a_failure_in_the_documented_members",
    "test_query_string_values_are_converted_because_a_query_string_has_no_types",
    "test_settings_error_is_a_value_error",
    "test_the_body_is_one_to_4000_characters_after_stripping",
    "test_the_json_form_is_accepted_too",
    "test_the_json_form_of_a_ticket_has_exactly_the_documented_fields_and_iso_utc_times",
    "test_the_listed_values_are_accepted",
    "test_the_module_calls_nothing_that_runs_text_as_code_and_imports_nothing_that_does",
    "test_the_title_is_three_to_120_characters_after_stripping",
    "test_to_out_converts_epoch_seconds_to_timezone_aware_utc_datetimes",
    "test_transitions_is_the_table_the_rules_are_built_from",
    "test_values_outside_the_lists_and_limits_are_refused",
})


def test_m10_guided_solution_passes_every_check():
    results = run_pytest(M10 / "lab-guided", env={"LAB_TARGET": "solution"}, timeout=1800)
    assert len(results) == M10_GUIDED_CHECKS and failing(results) == set(), sorted(failing(results))[:20]


def test_m10_guided_starter_fails_everything_a_learner_has_to_write():
    results = run_pytest(M10 / "lab-guided", timeout=1800)
    assert len(results) == M10_GUIDED_CHECKS
    passed = {k for k, v in results.items() if v == "passed"}
    assert {k.split("[")[0] for k in passed} == M10_STARTER_GIVEN, sorted({k.split("[")[0] for k in passed} ^ M10_STARTER_GIVEN)
    assert len(passed) == 82, len(passed)
    for name in ("test_another_hmac_algorithm_is_refused_even_with_the_right_secret",
                 "test_the_audience_must_match",
                 "test_every_token_has_its_own_id",
                 "test_q_is_a_value_and_never_changes_the_statement",
                 "test_field_errors_never_repeat_what_the_client_sent",
                 "test_only_an_admin_may_delete",
                 "test_the_order_of_the_checks_is_closed_then_role_then_openness_then_transition",
                 "test_an_id_is_accepted_only_in_its_plain_decimal_form_so_that_a_ticket_has_one_address",
                 "test_a_body_without_a_length_is_refused_with_411",
                 "test_a_hostile_title_or_body_is_stored_as_text_or_refused_and_nothing_else_happens",
                 "test_a_reader_cannot_discover_ticket_ids_by_the_difference_between_403_and_404",
                 "test_ruff_with_the_security_rules_is_clean"):
        cases = {k: v for k, v in results.items() if k.split("[")[0] == name}
        assert cases and all(v in ("failed", "error") for v in cases.values()), name


@pytest.mark.private_materials
def test_m10_guided_checks_are_discriminating():
    mutants = PRIVATE / "PY-M10" / "guided-mutants.json"
    if not mutants.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    solution = M10 / "lab-guided" / "solution"
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(solution), "--module", "ticketapi", "--tests", str(M10 / "lab-guided" / "checks"), "--mutants", str(mutants), "--json", "--jobs", "4"],
                          capture_output=True, text=True, timeout=7200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 432 and report["total"] == 432, [m for m in report["mutants"] if not m["killed"]]


def test_m10_independent_starter_fails_every_published_check():
    results = run_pytest(M10 / "lab-independent")
    assert len(results) == 16 and {k.split("[")[0] for k in results} >= {"test_01_the_key_store_keeps_a_hash_and_checks_secrets", "test_10_requests_over_the_limit_in_one_window_are_a_429_with_retry_after"}
    assert set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


@pytest.mark.private_materials
def test_m10_independent_reference_passes_published_and_hidden_checks():
    ref = PRIVATE / "PY-M10" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M10 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == 16 and failing(published) == set(), failing(published)
    hidden = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(ref)}, timeout=1800)
    assert len(hidden) == 482 and failing(hidden) == set(), sorted(failing(hidden))[:20]


@pytest.mark.private_materials
def test_m10_independent_hidden_suite_is_discriminating_and_the_starter_fails_it():
    ref = PRIVATE / "PY-M10" / "independent-reference"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    proc = subprocess.run([sys.executable, str(TOOL), "--module-dir", str(ref), "--module", "inventory", "--tests", str(ref / "test_hidden.py"), "--mutants", str(ref / "mutants.json"), "--json", "--jobs", "4"],
                          capture_output=True, text=True, timeout=7200, env=dict(os.environ, LAB_TARGET="import"))
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == 274 and report["total"] == 275, [m for m in report["mutants"] if m["required"] and not m["killed"]]
    assert all(m.get("note") for m in report["mutants"] if not m["required"]), "every mutant that is not required must say why"
    results = run_pytest(ref, "test_hidden.py", env={"LAB_PROJECT": str(M10 / "lab-independent" / "starter")}, timeout=1800)
    assert len(results) == 482
    assert {k for k, v in results.items() if v == "passed"} == {"test_mypy_strict_is_clean", "test_ruff_with_the_security_rules_is_clean", "test_no_secret_or_key_is_written_into_the_module"}


# ------------------------------------------------------------------------------------------------------------------ PY-M11
M11 = COURSE / "modules" / "PY-M11"
M11_GATE = M11 / "lab-guided" / "tools" / "gate.py"
M11_PUBLISHED_CASES = 22
M11_HIDDEN_CHECKS = 585
M11_MUTANTS = 315
M11_MUTANTS_REQUIRED = 312
M11_GATES = [f"G{n:02d}" for n in range(1, 14)]
M11_C3_GOOD_PERCENT = 75       # what the reference's own tests must kill (measured: 251 of 312, 80 percent); rubric criterion C3 asks learners for 60 percent


def _m11_gate(project: Path, *args: str, part: str = "B") -> tuple[int, dict[str, bool]]:
    """Run the release gate on a project; return the exit status and {gate id: passed}."""
    done = subprocess.run([sys.executable, str(M11_GATE), "--project", str(project), "--part", part, *args], cwd=M11 / "lab-guided", capture_output=True, text=True, timeout=1800)
    gates = {m.group(2): m.group(1) == "PASS" for m in re.finditer(r"^\[(PASS|FAIL)\] (G\d\d)", done.stdout, re.M)}
    return done.returncode, gates


def _m11_edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (path.name, text.count(old), old[:60])
    path.write_text(text.replace(old, new), encoding="utf-8")


def _m11_append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def _m11_copy(source: Path, target: Path) -> Path:
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".coverage*", "build", "dist", "*.egg-info"))
    return target


_M11_CREDENTIAL = "pass" + "word = " + '"letmein-letmein"'      # assembled here so that this file does not contain a credential-shaped literal
_M11_PIPE = "    except BrokenPipeError:\n        os.dup2"
# Each case damages a copy of the reference application in exactly one way and names the gate that must notice. A gate that cannot fail is not a gate.
M11_DAMAGE = [
    ("G01", "the entry point module is missing", lambda p: (p / "src/authwatch/__main__.py").unlink()),
    ("G01", "there are no tests", lambda p: shutil.rmtree(p / "tests")),
    ("G02", "there is no requires-python", lambda p: _m11_edit(p / "pyproject.toml", 'requires-python = ">= 3.11"\n', "")),
    ("G02", "the dependency on PyYAML is missing", lambda p: _m11_edit(p / "pyproject.toml", 'dependencies = ["PyYAML >= 6.0, < 7"]', "dependencies = []")),
    ("G03", "the build backend does not exist", lambda p: _m11_edit(p / "pyproject.toml", 'build-backend = "setuptools.build_meta"', 'build-backend = "setuptools.no_such_backend"')),
    ("G04", "the typing marker is not in the wheel", lambda p: (p / "src/authwatch/py.typed").unlink()),
    ("G05", "the command prints another version than the package", lambda p: _m11_edit(p / "src/authwatch/cli.py", 'version=f"authwatch {__version__}"', 'version="authwatch 0.0.0"')),
    ("G05", "the version is written in two places", lambda p: _m11_edit(p / "pyproject.toml", 'dynamic = ["version"]', 'version = "9.9.9"')),
    ("G06", "a type error", lambda p: _m11_append(p / "src/authwatch/render.py", '\n_BAD: int = "text"\n')),
    ("G07", "a blanket suppression", lambda p: _m11_append(p / "src/authwatch/render.py", "\n_X = 1  # noqa\n")),
    ("G07", "a call that runs text as code", lambda p: _m11_append(p / "src/authwatch/render.py", '\n_Y = eval("1")\n')),
    ("G08", "fewer than thirty tests", lambda p: [f.unlink() for f in (p / "tests").glob("test_*.py") if f.name != "test_render.py"]),
    ("G09", "the workflow runs on pull_request_target", lambda p: _m11_edit(p / ".github/workflows/ci.yml", "  pull_request:\n", "  pull_request_target:\n")),
    ("G09", "an action is pinned to a tag", lambda p: _m11_edit(p / ".github/workflows/ci.yml", "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1", "actions/checkout@v4")),
    ("G09", "the token may write", lambda p: _m11_edit(p / ".github/workflows/ci.yml", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n")),
    ("G09", "event text is expanded inside a script", lambda p: _m11_edit(p / ".github/workflows/ci.yml", "run: python scripts/check.py", 'run: echo "${{ github.event.pull_request.title }}" && python scripts/check.py')),
    ("G09", "a version is not quoted", lambda p: _m11_edit(p / ".github/workflows/ci.yml", '["3.11", "3.12", "3.13", "3.14"]', '[3.11, "3.12", "3.13", "3.14"]')),
    ("G10", "a locked version has a known advisory", lambda p: _m11_edit(p / "requirements.lock", "PyYAML==6.0.3", "PyYAML==6.0")),
    ("G11", "a credential in the source", lambda p: _m11_append(p / "src/authwatch/render.py", "\n# " + _M11_CREDENTIAL + "\n")),
    ("G11", ".gitignore does not mention .env", lambda p: _m11_edit(p / ".gitignore", ".env\n", "")),
    ("G12", "there is no security section", lambda p: _m11_edit(p / "README.md", "## Security considerations", "## Notes")),
    ("G12", "the changelog does not name the version", lambda p: _m11_edit(p / "CHANGELOG.md", "## 1.0.0", "## 0.9.0")),
    ("G13", "Ctrl-C is not handled", lambda p: _m11_edit(p / "src/authwatch/cli.py", "    except KeyboardInterrupt:\n        return EXIT_INTERRUPT", "    except ZeroDivisionError:\n        return EXIT_INTERRUPT")),
    ("G13", "a closed pipe is not handled", lambda p: _m11_edit(p / "src/authwatch/cli.py", _M11_PIPE, "    except ZeroDivisionError:\n        os.dup2")),
    ("G13", "the unusable lines are not counted", lambda p: _m11_edit(p / "src/authwatch/cli.py", "        self.bad += 1\n", "        self.bad += 0\n")),
]


def test_m11_independent_starter_fails_every_published_check():
    """The learner starts with an empty project folder: every published check must fail, none may pass by accident."""
    results = run_pytest(M11 / "lab-independent")
    assert len(results) == M11_PUBLISHED_CASES and len({k.split("[")[0] for k in results}) == 14, len(results)
    assert set(results.values()) <= {"failed", "error"}, {k: v for k, v in results.items() if v == "passed"}


def test_m11_guided_gate_passes_nothing_on_an_empty_project(tmp_path):
    (tmp_path / "project").mkdir()
    code, gates = _m11_gate(tmp_path / "project")
    assert code == 1 and sorted(gates) == M11_GATES and not any(gates.values()), gates
    code, gates = _m11_gate(tmp_path / "project", part="A")
    assert code == 1 and sorted(gates) == [g for g in M11_GATES if g not in ("G08", "G13")] and not any(gates.values()), gates


@pytest.mark.private_materials
def test_m11_guided_part_a_solution_passes_the_part_a_gate_and_is_not_a_finished_application():
    skeleton = PRIVATE / "PY-M11" / "part-a-solution"
    if not skeleton.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    code, gates = _m11_gate(skeleton, part="A")
    assert code == 0 and len(gates) == 11 and all(gates.values()), gates
    code, gates = _m11_gate(skeleton)
    assert code == 1 and {g for g, ok in gates.items() if not ok} == {"G08", "G12", "G13"}, gates     # tests, the documentation of every option, and the scenario need the finished application


@pytest.mark.private_materials
def test_m11_independent_reference_passes_published_hidden_and_gate():
    ref = PRIVATE / "PY-M11" / "reference-project"
    hidden = PRIVATE / "PY-M11" / "hidden" / "test_hidden.py"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    published = run_pytest(M11 / "lab-independent", env={"LAB_PROJECT": str(ref)})
    assert len(published) == M11_PUBLISHED_CASES and failing(published) == set(), failing(published)
    results = run_pytest(hidden.parent, hidden.name, env={"LAB_PROJECT": str(ref)}, timeout=1800)
    assert len(results) == M11_HIDDEN_CHECKS and failing(results) == set(), sorted(failing(results))[:20]
    code, gates = _m11_gate(ref)
    assert code == 0 and sorted(gates) == M11_GATES and all(gates.values()), gates


@pytest.mark.private_materials
def test_m11_independent_the_hidden_suite_rejects_a_walking_skeleton():
    skeleton = PRIVATE / "PY-M11" / "part-a-solution"
    hidden = PRIVATE / "PY-M11" / "hidden" / "test_hidden.py"
    if not skeleton.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    results = run_pytest(hidden.parent, hidden.name, env={"LAB_PROJECT": str(skeleton)}, timeout=1800)
    passed = [k for k, v in results.items() if v == "passed"]
    assert len(results) == M11_HIDDEN_CHECKS and len(passed) < 30, len(passed)      # the checks that a skeleton may pass: the version, usage errors, a missing file, import hygiene, silence; the rubric asks for 85 percent


@pytest.mark.private_materials
@pytest.mark.parametrize(("gate", "damage"), [(g, i) for i, (g, _, _) in enumerate(M11_DAMAGE)], ids=[f"{g}-{d}" for g, d, _ in M11_DAMAGE])
def test_m11_guided_gate_catches_each_damage(gate, damage, tmp_path):
    ref = PRIVATE / "PY-M11" / "reference-project"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    project = _m11_copy(ref, tmp_path / "project")
    M11_DAMAGE[damage][2](project)
    code, gates = _m11_gate(project, "--only", gate)
    assert code == 1 and gates.get(gate) is False, gates


def test_m11_guided_every_gate_has_a_negative_control():
    assert {g for g, _, _ in M11_DAMAGE} == set(M11_GATES)


@pytest.mark.private_materials
def test_m11_independent_hidden_suite_is_discriminating():
    pack = PRIVATE / "PY-M11"
    if not (pack / "mutants.json").exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    proc = subprocess.run([sys.executable, str(pack / "tools" / "package_mutation.py"), "--src", str(pack / "reference-project" / "src"), "--package", "authwatch", "--tests", str(pack / "hidden" / "test_hidden.py"),
                           "--mutants", str(pack / "mutants.json"), "--json", "--jobs", "4", "--timeout", "600"], capture_output=True, text=True, timeout=14400)
    report = json.loads(proc.stdout)
    assert report["baseline_passes"] and report["passed"]
    assert report["required_killed"] == report["required_total"] == M11_MUTANTS_REQUIRED and report["total"] == M11_MUTANTS, [m for m in report["mutants"] if m["required"] and not m["killed"]]
    assert all(m.get("note") for m in report["mutants"] if not m["required"]), "every mutant that is not required must say why"


@pytest.mark.private_materials
def test_m11_independent_the_reference_tests_kill_most_defects_and_a_weak_suite_does_not(tmp_path):
    """Calibration of rubric criterion C3: the learner's tests are graded by mutation against the reference, so the reference's own tests show what a good suite achieves."""
    pack = PRIVATE / "PY-M11"
    if not (pack / "mutants.json").exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    tool = [sys.executable, str(pack / "tools" / "package_mutation.py"), "--src", str(pack / "reference-project" / "src"), "--package", "authwatch", "--mutants", str(pack / "mutants.json"), "--json", "--jobs", "4", "--timeout", "300"]
    good = json.loads(subprocess.run([*tool, "--tests", str(pack / "reference-project" / "tests")], capture_output=True, text=True, timeout=14400).stdout)
    assert good["baseline_passes"]
    killed = sum(1 for m in good["mutants"] if m["required"] and m["killed"])
    assert killed * 100 >= M11_C3_GOOD_PERCENT * M11_MUTANTS_REQUIRED, (killed, M11_MUTANTS_REQUIRED)
    weak = tmp_path / "weak"
    weak.mkdir()
    (weak / "test_weak.py").write_text("import authwatch\n\n\ndef test_it_has_a_version():\n    assert authwatch.__version__\n\n\ndef test_a_good_line_parses():\n    line = b'{\"ts\": \"2026-10-14T12:00:00Z\", \"user\": \"a\", \"ip\": \"203.0.113.5\", \"outcome\": \"failure\"}\\n'\n    assert authwatch.parse_line(line, 1) is not None\n", encoding="utf-8")
    poor = json.loads(subprocess.run([*tool, "--tests", str(weak)], capture_output=True, text=True, timeout=14400).stdout)
    assert poor["baseline_passes"] and sum(1 for m in poor["mutants"] if m["required"] and m["killed"]) * 100 < 30 * M11_MUTANTS_REQUIRED      # far below the 60 percent of the rubric


def test_m11_independent_the_rubric_states_the_numbers_that_the_checks_use():
    text = (M11 / "assessment" / "rubric.yaml").read_text(encoding="utf-8")
    readme = (M11 / "lab-independent" / "README.md").read_text(encoding="utf-8")
    assert f"{M11_HIDDEN_CHECKS} checks" in text and f"at least {int(M11_HIDDEN_CHECKS * 0.85 + 0.999)} of the {M11_HIDDEN_CHECKS}" in text and f"{M11_MUTANTS_REQUIRED} required defects" in text
    assert f"{M11_HIDDEN_CHECKS} checks" in readme and f"{M11_PUBLISHED_CASES} cases" in readme and "thirteen gates" in readme


@pytest.mark.private_materials
def test_m11_independent_every_check_named_in_the_grading_notes_exists_in_the_hidden_suite():
    pack = PRIVATE / "PY-M11"
    if not (pack / "grading-notes.md").exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    names = set(re.findall(r"`(test_[a-z0-9_]+)`", (pack / "grading-notes.md").read_text(encoding="utf-8")))
    hidden = (pack / "hidden" / "test_hidden.py").read_text(encoding="utf-8")
    assert len(names) >= 14 and all(f"def {n}(" in hidden for n in names), sorted(n for n in names if f"def {n}(" not in hidden)

