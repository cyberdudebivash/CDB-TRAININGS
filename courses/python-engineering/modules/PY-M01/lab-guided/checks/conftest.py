"""Fixtures for the PY-M01 guided-lab checks. LAB_TARGET=starter (default, your working copy) or solution (the public reference)."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")


@pytest.fixture(scope="session")
def datakit():
    spec = importlib.util.spec_from_file_location("datakit_under_test", TARGET / "datakit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["datakit_under_test"] = module
    spec.loader.exec_module(module)
    return module
