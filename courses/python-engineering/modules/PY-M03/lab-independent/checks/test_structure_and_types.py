"""Structure and static-typing checks for the independent lab (specification in ../README.md)."""
from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

import pytest

MODULES = ["models", "parsing", "analysis", "render", "cli"]
PUBLIC_API = ["Trip", "consumption", "parse_lines", "parse_trip", "render", "worst"]


def python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def sibling_imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if node.level == 0 and parts[0] == "fleetlog":
                found.add(parts[1]) if len(parts) > 1 else found.update(a.name for a in node.names)
            elif node.level >= 1:
                found.add(parts[0])
        elif isinstance(node, ast.Import):
            found.update(a.name.split(".")[1] for a in node.names if a.name.startswith("fleetlog."))
    return found


def has_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    state: dict[str, int] = {}

    def visit(node: str, trail: list[str]) -> list[str] | None:
        state[node] = 1
        for nxt in sorted(graph.get(node, ())):
            if state.get(nxt) == 1:
                return trail + [node, nxt]
            if nxt in graph and state.get(nxt) is None:
                found = visit(nxt, trail + [node])
                if found:
                    return found
        state[node] = 2
        return None

    for n in sorted(graph):
        if state.get(n) is None:
            found = visit(n, [])
            if found:
                return found
    return None


def test_legacy_flat_modules_are_gone(project):
    leftovers = [n for n in ("models.py", "util.py", "report.py", "main.py", "pytest.ini", "setup.py", "setup.cfg") if (project / n).exists()]
    assert leftovers == [], f"remove or move: {leftovers}"


def test_package_has_one_module_per_idea(package):
    assert package.is_dir(), "create the package folder src/fleetlog/"
    missing = [m for m in MODULES + ["__init__"] if not (package / f"{m}.py").exists()]
    assert missing == [], missing
    assert (package / "py.typed").exists(), "add an empty src/fleetlog/py.typed"


def test_pyproject_configures_strict_mypy_and_pytest(project):
    path = project / "pyproject.toml"
    assert path.exists(), "create pyproject.toml"
    tool = tomllib.loads(path.read_text(encoding="utf-8"))["tool"]
    assert tool["mypy"]["strict"] is True
    assert tool["pytest"]["ini_options"]["testpaths"] == ["tests"]


def test_no_circular_imports_between_modules(package, project, runner):
    assert package.is_dir(), "create the package folder src/fleetlog/"
    graph = {m: {d for d in sibling_imports(package / f"{m}.py") if d != "__init__"} for m in MODULES}
    cycle = has_cycle(graph)
    assert cycle is None, "circular dependency: " + " -> ".join(cycle or [])
    for module in MODULES:
        proc = runner(["-c", f"import fleetlog.{module}"], project, PYTHONPATH=str(project / "src"))
        assert proc.returncode == 0, f"fleetlog.{module} must import on its own: {proc.stderr[-600:]}"


def test_public_interface_is_declared(package, project, runner):
    assert package.is_dir(), "create the package folder src/fleetlog/"
    proc = runner(["-c", "import fleetlog; print(sorted(fleetlog.__all__)); print(all(hasattr(fleetlog, n) for n in fleetlog.__all__))"], project, PYTHONPATH=str(project / "src"))
    assert proc.returncode == 0, proc.stderr[-800:]
    names, ok = proc.stdout.strip().splitlines()
    assert set(PUBLIC_API) <= set(ast.literal_eval(names)) and ok == "True"


def test_mypy_strict_is_clean_for_package_and_tests(package, project, runner):
    assert package.is_dir(), "create the package folder src/fleetlog/"
    assert (project / "tests").is_dir(), "tests/ is missing"
    proc = runner(["-m", "mypy", "--strict", "--no-color-output", "--show-error-codes", "src", "tests"], project, MYPYPATH="src")
    assert proc.returncode == 0, proc.stdout[-2500:]


def test_errors_are_fixed_not_silenced(package, project):
    assert package.is_dir(), "create the package folder src/fleetlog/"
    for path in python_files(project / "src") + python_files(project / "tests"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"#\s*type:\s*ignore", text), f"{path.name}: `# type: ignore` hides the problem"
        assert "cast(" not in text, f"{path.name}: `cast` hides the problem"
        assert not re.search(r"\bAny\b", text), f"{path.name}: `Any` turns checking off"


def test_tests_live_outside_the_package_and_pass(package, project, runner):
    assert package.is_dir(), "create the package folder src/fleetlog/"
    assert not list(package.rglob("test_*.py"))
    tests = sorted((project / "tests").glob("test_*.py"))
    assert tests and sum(p.read_text(encoding="utf-8").count("def test_") for p in tests) >= 3
    proc = runner(["-m", "pytest", "-q", "-p", "no:cacheprovider", "--import-mode=importlib", "-o", f"pythonpath={project / 'src'}", "tests"], project)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


@pytest.mark.parametrize("module", MODULES)
def test_modules_are_documented(package, module):
    assert package.is_dir(), "create the package folder src/fleetlog/"
    tree = ast.parse((package / f"{module}.py").read_text(encoding="utf-8"))
    assert ast.get_docstring(tree), f"{module}.py needs a module docstring saying what it is for"
