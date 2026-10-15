"""Fixtures for the PY-M13 guided-lab checks. LAB_TARGET=starter (default) or solution (the public reference); `import` is used by the instructors' mutation check."""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")


@pytest.fixture(scope="session")
def sk():
    if os.environ.get("LAB_TARGET") == "import":
        return importlib.import_module("streamkit")
    spec = importlib.util.spec_from_file_location("streamkit_under_test", TARGET / "streamkit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["streamkit_under_test"] = module
    spec.loader.exec_module(module)
    return module


class Counting:
    """An iterator over `items` that counts how many items it has handed out and records whether it was closed."""

    def __init__(self, items):
        self._it = iter(items)
        self.taken = 0
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self._it)
        self.taken += 1
        return item

    def close(self):
        self.closed = True


@pytest.fixture
def counting():
    return Counting
