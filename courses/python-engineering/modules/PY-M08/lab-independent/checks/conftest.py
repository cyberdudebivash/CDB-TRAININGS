"""Fixtures for the PY-M08 independent-lab checks (the published ones). The module under test is starter/casestore.py; LAB_PROJECT=<dir> points at another folder containing
casestore.py. LAB_TARGET=import is used by the instructors' mutation check. `open_store` opens stores inside the test, never in a fixture."""
from __future__ import annotations

import importlib
import importlib.util
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"
T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)

FIRST_RELEASE_SCHEMA = """
CREATE TABLE cases (id INTEGER PRIMARY KEY, title TEXT NOT NULL, reporter TEXT NOT NULL, severity INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE comments (id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, author TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL);
"""


@pytest.fixture(scope="session")
def cs():
    if os.environ.get("LAB_TARGET") == "import":
        return importlib.import_module("casestore")
    spec = importlib.util.spec_from_file_location("casestore_under_test", FOLDER / "casestore.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["casestore_under_test"] = module
    spec.loader.exec_module(module)
    return module


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> datetime:
        self.now += timedelta(**kwargs)
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def open_store(cs, clock):
    opened = []

    def opener(path=":memory:", **kwargs):
        kwargs.setdefault("clock", clock)
        store = cs.Store(path, **kwargs)
        opened.append(store)
        return store

    yield opener
    for store in opened:
        try:
            store.close()
        except Exception:
            pass


@pytest.fixture
def first_release_file(tmp_path):
    """first_release_file(cases, comments) -> path of a database made the way the first release made it (no version stored, no foreign keys)."""

    def build(cases=(), comments=()):
        path = tmp_path / "first-release.db"
        db = sqlite3.connect(path)
        db.executescript(FIRST_RELEASE_SCHEMA)
        db.executemany("INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?)", cases)
        db.executemany("INSERT INTO comments VALUES (?, ?, ?, ?, ?)", comments)
        db.commit()
        db.close()
        return path

    return build
