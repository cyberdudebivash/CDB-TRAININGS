"""Fixtures for the PY-M01 independent-lab checks. The module under test is starter/logkit.py; LAB_PROJECT=<dir> points at another folder containing logkit.py."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"


@pytest.fixture(scope="session")
def logkit():
    spec = importlib.util.spec_from_file_location("logkit", FOLDER / "logkit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["logkit"] = module
    spec.loader.exec_module(module)
    return module
