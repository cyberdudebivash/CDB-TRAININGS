"""Fixtures for the PY-M09 independent-lab checks (the published ones). The module under test is starter/triage.py; LAB_PROJECT=<dir> points at another folder containing
triage.py (and test_budget.py). LAB_TARGET=import is used by the instructors' mutation check."""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"


@pytest.fixture(scope="session")
def folder():
    return FOLDER


@pytest.fixture(scope="session")
def tr():
    if os.environ.get("LAB_TARGET") == "import":
        return importlib.import_module("triage")
    spec = importlib.util.spec_from_file_location("triage_under_test", FOLDER / "triage.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["triage_under_test"] = module
    spec.loader.exec_module(module)
    return module
