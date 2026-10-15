"""Fixtures for the PY-M04 independent-lab checks.

The project under test is `starter/` (your working copy). Instructors can overlay reference files on a scratch copy with LAB_OVERLAY=<dir>.
Nothing is written next to your sources.
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
IGNORE = shutil.ignore_patterns(".venv", "__pycache__", "*.egg-info", "dist", "build", ".pytest_cache")


@pytest.fixture(scope="session")
def project(tmp_path_factory) -> Path:
    work = tmp_path_factory.mktemp("project") / "logslice"
    shutil.copytree(LAB / "starter", work, ignore=IGNORE)
    overlay = os.environ.get("LAB_OVERLAY")
    if overlay:
        shutil.copytree(overlay, work, ignore=IGNORE, dirs_exist_ok=True)
    return work


@pytest.fixture(scope="session")
def built(project) -> dict:
    out = project / "dist"
    proc = subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out), str(project)], capture_output=True, text=True, timeout=600)
    return {"returncode": proc.returncode, "log": proc.stdout + proc.stderr,
            "wheels": sorted(out.glob("*.whl")) if out.exists() else [], "sdists": sorted(out.glob("*.tar.gz")) if out.exists() else []}


@pytest.fixture(scope="session")
def clean_venv(built, tmp_path_factory) -> dict:
    if not built["wheels"]:      # no assertion here: a failing fixture is a set-up ERROR; the test that needs the environment reports it as a failed check
        return {"error": "no wheel was built: fix the build first"}
    env_dir = tmp_path_factory.mktemp("venv") / "env"
    venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
    bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    py = bindir / ("python.exe" if os.name == "nt" else "python")
    proc = subprocess.run([str(py), "-m", "pip", "install", "--no-index", "--no-deps", "--disable-pip-version-check", str(built["wheels"][0])],
                          capture_output=True, text=True, timeout=600)
    return {"bin": bindir, "python": py, "install": proc}
