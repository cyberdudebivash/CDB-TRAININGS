"""Fixtures for the PY-M13 independent-lab checks (the published ones). The module under test is starter/flowkit.py; LAB_PROJECT=<dir> points at another folder containing flowkit.py."""
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
def fk():
    if os.environ.get("LAB_TARGET") == "import":              # instructors' mutation check: the module under test comes from the import path
        return importlib.import_module("flowkit")
    spec = importlib.util.spec_from_file_location("flowkit_under_test", FOLDER / "flowkit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["flowkit_under_test"] = module
    spec.loader.exec_module(module)
    return module


class Source:
    """An iterator over `items` that counts what it hands out and records close()."""

    def __init__(self, items):
        self._it = iter(items)
        self.taken = 0
        self.closed = 0

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self._it)
        self.taken += 1
        return item

    def close(self):
        self.closed += 1


@pytest.fixture
def source():
    return Source
