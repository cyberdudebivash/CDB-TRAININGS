"""Fixtures for the PY-M12 guided-lab checks. LAB_TARGET=starter (default) or solution (the public reference)."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")


@pytest.fixture(scope="session")
def lk():
    """The module under test, loaded from starter/ (or solution/) by path so that the two never mix."""
    if os.environ.get("LAB_TARGET") == "import":              # instructors' mutation check: the module under test comes from the import path
        return importlib.import_module("ledgerkit")
    spec = importlib.util.spec_from_file_location("ledgerkit_under_test", TARGET / "ledgerkit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ledgerkit_under_test"] = module
    spec.loader.exec_module(module)
    return module
