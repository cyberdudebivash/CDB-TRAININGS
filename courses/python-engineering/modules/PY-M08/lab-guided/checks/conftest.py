"""Fixtures for the PY-M08 guided-lab checks.

The module under test is chosen by PY_M08_TARGET (the name the first release of this lab used) or LAB_TARGET (the name every other module uses):
`starter` (default, your work), `solution` (the public reference) or `import` (the instructors' mutation check, which puts the module on the import path itself).
`open_store` opens stores inside the test, never in a fixture, so that a step you have not written yet is reported as a failed check and not as a set-up error.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = os.environ.get("PY_M08_TARGET") or os.environ.get("LAB_TARGET") or "starter"
if TARGET not in {"starter", "solution", "import"}:
    raise ValueError("PY_M08_TARGET must be starter, solution or import")
if TARGET != "import":
    sys.path.insert(0, str(LAB / TARGET))

T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)

# The schema the first release of this lab created (stored version 0). Written out here on purpose: it must keep working when the migrations grow.
ORIGINAL_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS events_entity_order ON events(entity_id, occurred_at, event_id)",
)


@pytest.fixture(scope="session")
def original_schema():
    return ORIGINAL_SCHEMA


@pytest.fixture(scope="session")
def es():
    import eventstore

    return eventstore


class Clock:
    """A clock the test controls: .now is what the store sees; .advance() moves it."""

    def __init__(self, start: datetime = T0 + timedelta(hours=1)) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> datetime:
        self.now += timedelta(**kwargs)
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def make(es):
    """make(eid='evt-1', entity='customer-A', kind='created', when=T0, payload=None) -> Event."""

    def factory(eid="evt-1", entity="customer-A", kind="created", when=T0, payload=None):
        return es.Event(eid, entity, kind, when, {"value": 1} if payload is None else payload)

    return factory


@pytest.fixture
def open_store(es, clock):
    """open_store(path=':memory:', **kw) -> EventStore with the controllable clock; every store opened is closed at the end of the test."""
    opened = []

    def opener(path=":memory:", **kwargs):
        kwargs.setdefault("clock", clock)
        store = es.EventStore(path, **kwargs)
        opened.append(store)
        return store

    yield opener
    for store in opened:
        try:
            store.close()
        except Exception:
            pass


class StatementLog:
    """Records every statement SQLite executes on a connection (the trace callback receives each statement with its values filled in)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.statements: list[str] = []
        conn.set_trace_callback(self.statements.append)

    def matching(self, *prefixes: str) -> list[str]:
        return [s for s in self.statements if s.lstrip().upper().startswith(tuple(p.upper() for p in prefixes))]

    def clear(self) -> None:
        self.statements.clear()


@pytest.fixture
def trace():
    return StatementLog
