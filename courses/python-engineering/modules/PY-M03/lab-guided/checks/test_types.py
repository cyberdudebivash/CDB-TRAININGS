"""Static-typing checks: strict mypy is clean, configured in pyproject.toml, and not silenced."""
from __future__ import annotations

import re
import tomllib
from pathlib import Path


def python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def test_pyproject_turns_strict_mode_on(project):
    path = project / "pyproject.toml"
    assert path.exists(), "create pyproject.toml (step D)"
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    assert config["tool"]["mypy"]["strict"] is True, "[tool.mypy] strict = true"


def test_mypy_strict_is_clean_for_the_package(project, package, runner):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    proc = runner(["-m", "mypy", "--strict", "--no-color-output", "--show-error-codes", "src"], project, MYPYPATH="src")
    assert proc.returncode == 0, proc.stdout[-2000:]


def test_mypy_strict_is_clean_for_the_tests_too(project, package, runner):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    assert (project / "tests").is_dir(), "move the script's tests into tests/ (step E)"
    proc = runner(["-m", "mypy", "--strict", "--no-color-output", "--show-error-codes", "src", "tests"], project, MYPYPATH="src")
    assert proc.returncode == 0, proc.stdout[-2000:]


def test_errors_are_fixed_not_silenced(project, package):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    for path in python_files(project / "src") + python_files(project / "tests"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"#\s*type:\s*ignore", text), f"{path.name}: fix the cause instead of `# type: ignore`"
        assert "cast(" not in text, f"{path.name}: `cast` hides a type error"
        assert not re.search(r"\bAny\b", text), f"{path.name}: `Any` switches checking off for that value"


def test_package_is_marked_as_typed(package):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    assert (package / "py.typed").exists(), "add an empty src/invkit/py.typed file"
