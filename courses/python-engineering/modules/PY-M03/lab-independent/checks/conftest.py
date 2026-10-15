"""Fixtures for the PY-M03 independent-lab checks.

The project under test is `starter/` (your working copy). Instructors can point at a reference with LAB_PROJECT=<dir>.
Sub-processes run inside that folder; nothing is written into it.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
PROJECT = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"


@pytest.fixture(scope="session")
def project() -> Path:
    return PROJECT


@pytest.fixture(scope="session")
def package(project: Path) -> Path:
    path = project / "src" / "fleetlog"
    assert path.is_dir(), "create the package folder src/fleetlog/"
    return path


def run(args: list[str], cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    e = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
    e.update(env)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=e, timeout=600)


@pytest.fixture(scope="session")
def runner():
    return run
