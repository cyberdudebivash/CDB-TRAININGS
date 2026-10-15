"""Automated checks for the PY-M04 guided lab (rubric criteria are listed in ../README.md)."""
from __future__ import annotations

import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path


def pyproject(project: Path) -> dict:
    path = project / "pyproject.toml"
    assert path.exists(), "create pyproject.toml in the project folder (see the lab README, step B)"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_setup_py_is_gone(project):
    assert not (project / "setup.py").exists(), "delete setup.py: the build is described by pyproject.toml alone"


def test_build_system_is_declared(project):
    data = pyproject(project)
    build = data["build-system"]
    assert build["build-backend"] == "setuptools.build_meta"
    assert any(r.replace(" ", "").startswith("setuptools>=") for r in build["requires"])


def test_project_metadata(project):
    p = pyproject(project)["project"]
    assert p["name"] == "tinycsv"
    assert "version" in p.get("dynamic", []) or p.get("version") == "0.3.1"
    assert p["requires-python"].replace(" ", "").startswith(">=3.11")
    assert p["scripts"] == {"tinycsv-summary": "tinycsv.cli:main"}
    assert isinstance(p["license"], str), "declare the licence as an SPDX expression string, not the deprecated table form"
    assert p.get("readme")


def test_development_tools_live_in_a_dependency_group(project):
    groups = pyproject(project).get("dependency-groups", {})
    assert any(str(dep).replace(" ", "").startswith("pytest") for dep in groups.get("test", [])), "[dependency-groups] needs a `test` group containing pytest"


def test_build_succeeds_and_produces_sdist_and_wheel(built):
    assert built["returncode"] == 0, built["log"][-1500:]
    assert len(built["wheels"]) == 1 and len(built["sdists"]) == 1
    assert built["wheels"][0].name.startswith("tinycsv-0.3.1-") and built["sdists"][0].name == "tinycsv-0.3.1.tar.gz"


def test_wheel_contains_the_package_but_not_the_tests(built):
    assert built["wheels"], "no wheel was built: fix the build first"
    with zipfile.ZipFile(built["wheels"][0]) as whl:
        names = whl.namelist()
        for expected in ("tinycsv/__init__.py", "tinycsv/summary.py", "tinycsv/cli.py", "tinycsv/py.typed"):
            assert expected in names, f"{expected} missing from the wheel"
        assert not [n for n in names if n.startswith("tests/")], "the tests package must not be shipped in the wheel"
        meta = next(whl.read(n).decode() for n in names if n.endswith(".dist-info/METADATA"))
        entry = next(whl.read(n).decode() for n in names if n.endswith(".dist-info/entry_points.txt"))
    assert "Name: tinycsv" in meta and "Version: 0.3.1" in meta and "Requires-Python: >=3.11" in meta
    assert "License-Expression:" in meta
    assert "tinycsv-summary = tinycsv.cli:main" in entry


def test_sdist_contains_sources_and_metadata(built):
    with tarfile.open(built["sdists"][0]) as tar:
        names = [n.split("/", 1)[1] for n in tar.getnames() if "/" in n]
    for expected in ("pyproject.toml", "README.md", "tinycsv/__init__.py", "tinycsv/cli.py"):
        assert expected in names, f"{expected} missing from the sdist"
    assert not [n for n in names if "__pycache__" in n or ".venv" in n]


def test_wheel_installs_into_a_clean_environment(clean_venv):
    assert clean_venv["install"].returncode == 0, clean_venv["install"].stderr[-1500:]


def test_installed_command_runs_and_uses_the_installed_copy(clean_venv, project, tmp_path):
    exe = clean_venv["bin"] / "tinycsv-summary"
    out = subprocess.run([str(exe), str(project / "sample" / "people.csv")], capture_output=True, text=True, cwd=tmp_path, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == ["rows: 3", "columns: name, age, city", "numeric columns: age"]
    where = subprocess.run([str(clean_venv["python"]), "-c", "import tinycsv; print(tinycsv.__file__, tinycsv.__version__)"], capture_output=True, text=True, cwd=tmp_path)
    path, version = where.stdout.split()
    assert "site-packages" in path and version == "0.3.1"


def test_pip_check_reports_no_broken_requirements(clean_venv):
    proc = subprocess.run([str(clean_venv["python"]), "-m", "pip", "check", "--disable-pip-version-check"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout
