"""Fixtures for the PY-M03 guided-lab checks.

The project under test is `starter/` (your working copy). LAB_TARGET=solution checks the public reference instead; LAB_PROJECT=<dir> checks any project folder.
Checks run mypy, pytest and Python in sub-processes inside that folder and never modify it.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
PROJECT = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / os.environ.get("LAB_TARGET", "starter")


@pytest.fixture(scope="session")
def project() -> Path:
    return PROJECT


@pytest.fixture(scope="session")
def package(project: Path) -> Path:
    path = project / "src" / "invkit"
    assert path.is_dir(), "create the package folder src/invkit/ (see the lab README, step D)"
    return path


def run(args: list[str], cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    e = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
    e.update(env)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=e, timeout=600)


@pytest.fixture(scope="session")
def runner():
    return run
