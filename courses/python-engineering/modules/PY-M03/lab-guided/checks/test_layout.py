"""Layout checks: modules with one job each, a declared public interface, one-way dependencies, tests outside the package."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

PUBLIC_API = ["Product", "find_product", "format_report", "load_products", "low_stock", "restock_plan", "total_value"]
MODULES = ["models", "loader", "stock", "report", "cli"]
# module -> the only invkit modules it may import (dependencies point one way)
ALLOWED = {"models": set(), "loader": {"models"}, "stock": {"models"}, "report": {"models", "stock"}, "cli": {"loader", "report"}}


def imported_siblings(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "invkit" and node.level == 0:
            parts = node.module.split(".")
            if len(parts) > 1:
                found.add(parts[1])
            else:
                found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level >= 1 and node.module:
            found.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            found |= {a.name.split(".")[1] for a in node.names if a.name.startswith("invkit.")}
    return found


def test_each_idea_has_its_own_module(package):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    missing = [m for m in MODULES + ["__init__"] if not (package / f"{m}.py").exists()]
    assert missing == [], f"missing modules: {missing}"


def test_the_flat_script_is_gone(project):
    assert not (project / "inventory.py").exists(), "delete inventory.py once its code lives in the package"
    assert not (project / "pytest.ini").exists(), "move the pytest settings into pyproject.toml ([tool.pytest.ini_options]) and delete pytest.ini"


@pytest.mark.parametrize("module", MODULES)
def test_dependencies_point_one_way(package, module):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    assert imported_siblings(package / f"{module}.py") <= ALLOWED[module], f"{module} may import only {sorted(ALLOWED[module])}"


@pytest.mark.parametrize("module", MODULES)
def test_every_module_imports_on_its_own(project, package, runner, module):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    proc = runner(["-c", f"import invkit.{module}"], project, PYTHONPATH=str(project / "src"))
    assert proc.returncode == 0, proc.stderr[-1500:]


def test_public_interface_is_declared(project, package, runner):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    code = "import invkit; print(sorted(invkit.__all__)); print(all(hasattr(invkit, n) for n in invkit.__all__))"
    proc = runner(["-c", code], project, PYTHONPATH=str(project / "src"))
    assert proc.returncode == 0, proc.stderr[-1500:]
    names, resolvable = proc.stdout.strip().splitlines()
    declared = set(eval(names))  # noqa: S307 - the output of our own sub-process, a list of strings
    assert set(PUBLIC_API) <= declared, f"__all__ must list at least {PUBLIC_API}"
    assert resolvable == "True", "every name in __all__ must exist"


def test_tests_live_outside_the_package_and_pass(project, package, runner):
    assert package.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    assert not list(package.rglob("test_*.py")), "tests belong in tests/, not inside the package"
    tests = sorted((project / "tests").glob("test_*.py"))
    assert tests, "tests/ needs at least one test module"
    proc = runner(["-m", "pytest", "-q", "-p", "no:cacheprovider", "--import-mode=importlib", "-o", f"pythonpath={project / 'src'}", "tests"], project)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
    assert sum(path.read_text(encoding="utf-8").count("def test_") for path in tests) >= 5, "write at least five tests covering the five behaviours of the original script"
