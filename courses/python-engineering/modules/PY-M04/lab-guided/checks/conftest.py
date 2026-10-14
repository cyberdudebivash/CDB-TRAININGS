"""Fixtures for the PY-M04 guided-lab checks.

LAB_TARGET selects which project is checked: `starter` (default: the learner's working copy) or `solution` (the public reference).
The checks build and install the project in scratch directories; nothing is written next to your sources.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")
IGNORE = shutil.ignore_patterns(".venv", "__pycache__", "*.egg-info", "dist", "build", ".pytest_cache")


@pytest.fixture(scope="session")
def project() -> Path:
    return TARGET


@pytest.fixture(scope="session")
def built(tmp_path_factory) -> dict:
    """Copy the project to a scratch directory and build an sdist and a wheel with `python -m build --no-isolation`."""
    work = tmp_path_factory.mktemp("build") / "project"
    shutil.copytree(TARGET, work, ignore=IGNORE)
    out = work / "dist"
    proc = subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out), str(work)], capture_output=True, text=True, timeout=600)
    return {"work": work, "out": out, "returncode": proc.returncode, "log": proc.stdout + proc.stderr,
            "wheels": sorted(out.glob("*.whl")) if out.exists() else [], "sdists": sorted(out.glob("*.tar.gz")) if out.exists() else []}


@pytest.fixture(scope="session")
def clean_venv(built, tmp_path_factory) -> dict:
    """Create a fresh virtual environment (with pip) and install the built wheel into it without network access."""
    assert built["wheels"], "no wheel was built"
    env_dir = tmp_path_factory.mktemp("venv") / "env"
    venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
    bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    py = bindir / ("python.exe" if os.name == "nt" else "python")
    proc = subprocess.run([str(py), "-m", "pip", "install", "--no-index", "--no-deps", "--disable-pip-version-check", str(built["wheels"][0])],
                          capture_output=True, text=True, timeout=600)
    return {"bin": bindir, "python": py, "install": proc}
