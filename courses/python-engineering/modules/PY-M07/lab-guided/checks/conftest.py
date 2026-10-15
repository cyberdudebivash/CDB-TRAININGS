"""Fixtures for the PY-M07 guided-lab checks.

LAB_TARGET selects the module under test: `starter` (default: your working copy) or `solution` (the public reference).
The checks only use harmless probes: os.getpid, os.environ.setdefault with a marker name, and `echo`.
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")


@pytest.fixture(scope="session")
def helpdesk():
    spec = importlib.util.spec_from_file_location("helpdesk_under_test", TARGET / "helpdesk.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["helpdesk_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def conn():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE users (name TEXT, email TEXT, role TEXT)")
    db.executemany("INSERT INTO users VALUES (?, ?, ?)", [("ada", "ada@example.test", "agent"), ("grace", "grace@example.test", "admin"), ("O'Brien", "ob@example.test", "viewer")])
    yield db
    db.close()
