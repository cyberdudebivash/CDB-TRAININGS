"""Fixtures for the PY-M12 independent-lab checks (the published ones). The module under test is starter/rulekit.py; LAB_PROJECT=<dir> points at another folder containing rulekit.py."""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"


@pytest.fixture(scope="session")
def rk():
    if os.environ.get("LAB_TARGET") == "import":              # instructors' mutation check: the module under test comes from the import path
        return importlib.import_module("rulekit")
    spec = importlib.util.spec_from_file_location("rulekit_under_test", FOLDER / "rulekit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["rulekit_under_test"] = module
    spec.loader.exec_module(module)
    return module
