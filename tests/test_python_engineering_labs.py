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
