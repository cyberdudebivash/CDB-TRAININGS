"""Automated checks for the PY-M04 independent lab. They state the specification in executable form (see ../README.md)."""
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

# Regular expression given by the PyPA "Inline script metadata" specification (research register R-077).
SCRIPT_BLOCK = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"


def load(project: Path) -> dict:
    path = project / "pyproject.toml"
    assert path.exists(), "create pyproject.toml in the project folder"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def norm(requirement: str) -> str:
    return requirement.replace(" ", "")


def resolve_group(groups: dict, name: str, seen: tuple = ()) -> set[str]:
    assert name not in seen, f"dependency group cycle through {name}"
    out: set[str] = set()
    for item in groups[name]:
        out |= resolve_group(groups, item["include-group"], seen + (name,)) if isinstance(item, dict) else {norm(item)}
    return out


def test_only_pyproject_describes_the_build(project):
    for legacy in ("setup.py", "setup.cfg"):
        assert not (project / legacy).exists(), f"remove {legacy}"
    assert not list(project.glob("requirements*.txt")), "development tools belong in [dependency-groups], not in requirements files"


def test_core_metadata(project):
    data = load(project)
    p = data["project"]
    assert data["build-system"]["build-backend"] == "setuptools.build_meta"
    assert p["name"] == "logslice" and "version" in p.get("dynamic", [])
    assert norm(p["requires-python"]).startswith(">=3.11")
    assert isinstance(p["license"], str) and p["license"] == "LicenseRef-Training-Example"
    assert p["license-files"] == ["LICENSE"]
    assert p["scripts"] == {"logslice": "logslice.cli:main"}


def test_extras_and_dependency_groups(project):
    data = load(project)
    assert [norm(r) for r in data["project"]["optional-dependencies"]["pretty"]] == ["rich>=13"]
    groups = data["dependency-groups"]
    assert resolve_group(groups, "test") == {"pytest>=8"}
    assert resolve_group(groups, "lint") == {"ruff"}
    assert resolve_group(groups, "dev") == {"pytest>=8", "ruff"}
    assert any(isinstance(i, dict) for i in groups["dev"]), "`dev` must include the other groups with {include-group = ...}, not repeat them"
    assert not data["project"].get("dependencies"), "logslice has no runtime dependencies"


def test_src_layout_and_version_are_configured(project):
    tool = load(project)["tool"]["setuptools"]
    assert tool["packages"]["find"]["where"] == ["src"]
    assert tool["dynamic"]["version"] == {"attr": "logslice.__version__"}
    assert load(project)["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]


def test_build_produces_a_wheel_and_an_sdist(built):
    assert built["returncode"] == 0, built["log"][-1500:]
    assert [w.name.split("-")[:2] for w in built["wheels"]] == [["logslice", "1.2.0"]]
    assert [s.name for s in built["sdists"]] == ["logslice-1.2.0.tar.gz"]


def test_wheel_contents_and_metadata(built):
    assert built["wheels"], "no wheel was built: fix the build first"
    with zipfile.ZipFile(built["wheels"][0]) as whl:
        names = whl.namelist()
        for expected in ("logslice/__init__.py", "logslice/core.py", "logslice/cli.py", "logslice/py.typed"):
            assert expected in names, f"{expected} missing from the wheel"
        assert not [n for n in names if n.split("/")[0] in ("tests", "scripts", "data")], "only the logslice package belongs in the wheel"
        meta = next(whl.read(n).decode() for n in names if n.endswith(".dist-info/METADATA"))
    assert "Requires-Python: >=3.11" in meta and "License-Expression: LicenseRef-Training-Example" in meta
    assert "Provides-Extra: pretty" in meta
    assert re.search(r'Requires-Dist: rich>=13; extra == "pretty"', meta), meta
    assert not [ln for ln in meta.splitlines() if ln.startswith("Requires-Dist:") and "extra ==" not in ln], "no unconditional runtime dependency expected"


def test_installed_command_filters_the_sample_log(clean_venv, project, tmp_path):
    assert "error" not in clean_venv, clean_venv.get("error")
    assert clean_venv["install"].returncode == 0, clean_venv["install"].stderr[-1500:]
    exe = clean_venv["bin"] / "logslice"
    out = subprocess.run([str(exe), str(project / "data" / "sample.log"), "--level", "ERROR"], capture_output=True, text=True, cwd=tmp_path, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == ["ERROR payment failed", "ERROR timeout calling billing", "CRITICAL out of memory"]
    assert subprocess.run([str(exe), "--version"], capture_output=True, text=True, cwd=tmp_path).stdout.strip() == "logslice 1.2.0"
    check = subprocess.run([str(clean_venv["python"]), "-m", "pip", "check", "--disable-pip-version-check"], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout


def test_report_script_declares_inline_metadata(project):
    source = (project / "scripts" / "report.py").read_text(encoding="utf-8")
    blocks = [m for m in re.finditer(SCRIPT_BLOCK, source) if m.group("type") == "script"]
    assert len(blocks) == 1, "scripts/report.py needs exactly one `# /// script` block (PEP 723)"
    content = "".join(line[2:] if line.startswith("# ") else line[1:] for line in blocks[0].group("content").splitlines(keepends=True))
    meta = tomllib.loads(content)
    assert norm(meta["requires-python"]).startswith(">=3.11")
    assert [norm(d) for d in meta["dependencies"]] == ["rich>=13"]
    assert set(meta) <= {"requires-python", "dependencies", "tool"}


def test_report_script_still_runs_without_rich(project):
    proc = subprocess.run([sys.executable, str(project / "scripts" / "report.py"), str(project / "data" / "sample.log")], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "ERROR: 2" in proc.stdout.splitlines()
