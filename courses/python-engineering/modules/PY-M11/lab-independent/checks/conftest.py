"""Fixtures of the published acceptance checks of the PY-M11 capstone.

They exercise your application through its public interface only (the package API and the command line), in the folder given by LAB_PROJECT (default: ../project). The package is imported
inside each test, so work that does not exist yet is a failed check and not a set-up error. LAB_TARGET=import is used by the instructors' mutation check (the package is already importable).
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_support import raw  # noqa: E402

LAB = Path(__file__).resolve().parent.parent
PROJECT = Path(os.environ.get("LAB_PROJECT", LAB / "project")).resolve()
SRC = PROJECT / "src"


def _load() -> ModuleType:
    if os.environ.get("LAB_TARGET") != "import" and str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    return importlib.import_module("authwatch")


class _Package:
    """The package under test, imported on first use inside a test, so that a package that does not exist yet fails the check instead of breaking the set-up."""

    def __getattr__(self, name: str):
        return getattr(_load(), name)


@pytest.fixture(scope="session")
def aw() -> _Package:
    return _Package()


@pytest.fixture
def events(aw):
    def make(seconds: float, user: str, ip: str, outcome: str):
        parsed = aw.parse_line(raw(seconds, user, ip, outcome), 1)
        assert parsed is not None
        return parsed

    return make


@pytest.fixture
def cli():
    def run(*args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env["PYTHONPATH"] = str(SRC) if os.environ.get("LAB_TARGET") != "import" else os.environ.get("PYTHONPATH", "")
        return subprocess.run([sys.executable, "-m", "authwatch", *args], input=stdin, capture_output=True, env=env, timeout=120, check=False)  # noqa: S603

    return run
