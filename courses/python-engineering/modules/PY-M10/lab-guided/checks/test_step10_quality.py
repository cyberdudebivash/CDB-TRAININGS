"""Step 10 - The service is typed and clean: strict mypy, a security-aware ruff run, and no silenced warnings that hide a real defect."""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def source_file(ta):
    return Path(ta.__file__)


def run(args, cwd):
    return subprocess.run([sys.executable, "-m", *args], capture_output=True, text=True, cwd=cwd, timeout=300)


def test_mypy_strict_is_clean(source_file):
    with tempfile.TemporaryDirectory() as neutral:
        proc = run(["mypy", "--strict", "--no-color-output", "--show-error-codes", "--cache-dir", neutral, str(source_file)], neutral)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ruff_with_the_security_rules_is_clean(source_file):
    with tempfile.TemporaryDirectory() as neutral:
        proc = run(["ruff", "check", "--no-cache", "--isolated", "--select", "F,E,W,B,S,UP,SIM", "--line-length", "200", "--output-format", "concise", str(source_file)], neutral)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_every_noqa_names_one_rule_and_says_why(source_file):
    lines = [ln for ln in source_file.read_text(encoding="utf-8").splitlines() if "# noqa" in ln]
    assert len(lines) <= 3, lines
    for line in lines:
        match = re.search(r"# noqa: ([A-Z]+[0-9]+)( - .{20,})?$", line)
        assert match and match.group(2), f"a noqa without a reason: {line.strip()}"
        assert match.group(1) == "S608", f"only the SQL warning may be silenced here, and only with a reason: {line.strip()}"


def test_at_most_one_type_ignore_and_it_names_its_error(source_file):
    ignores = [ln for ln in source_file.read_text(encoding="utf-8").splitlines() if "type: ignore" in ln]
    assert len(ignores) <= 1, ignores
    assert all(re.search(r"type: ignore\[[a-z-]+\]", ln) for ln in ignores), ignores


def test_every_function_has_annotated_parameters_and_result(source_file):
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    bare = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs if a.arg not in {"self", "cls"}]
            if node.args.vararg:
                params.append(node.args.vararg)
            if node.args.kwarg:
                params.append(node.args.kwarg)
            if node.returns is None or any(a.annotation is None for a in params):
                bare.append(node.name)
    assert bare == [], f"functions without full annotations: {bare}"


def test_the_module_calls_nothing_that_runs_text_as_code_and_imports_nothing_that_does(source_file):
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    called = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not ({"eval", "exec", "__import__"} & called), sorted({"eval", "exec", "__import__"} & called)
    assert not ({"pickle", "marshal", "subprocess", "yaml", "shelve"} & imported), sorted({"pickle", "marshal", "subprocess", "yaml", "shelve"} & imported)
