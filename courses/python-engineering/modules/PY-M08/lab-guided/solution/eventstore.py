"""PY-M08 guided reference: safe, idempotent SQLite event persistence.

Offline lab only. This is not a multi-tenant or Internet-facing service.
Supported runtime: Python 3.11+ (uses only the standard library).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_PAYLOAD_BYTES = 65_536
MAX_PAGE_SIZE = 100


class IdempotencyConflict(ValueError):
    """The same event_id was submitted with different event contents."""


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    entity_id: str
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not (1 <= len(value) <= 128):
        raise ValueError(f"{name} must have 1..128 characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{name} may not contain control characters")
    return value


def _prepare(event: Event) -> tuple[str, str, str, str, str]:
    if not isinstance(event, Event):
        raise TypeError("event must be an Event")
    event_id = _identifier(event.event_id, "event_id")
    entity_id = _identifier(event.entity_id, "entity_id")
    event_type = _identifier(event.event_type, "event_type")
    if not isinstance(event.occurred_at, datetime) or event.occurred_at.tzinfo is None or event.occurred_at.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")
    occurred_at = event.occurred_at.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if not isinstance(event.payload, dict):
        raise ValueError("payload must be a JSON object")
    try:
        payload_json = json.dumps(event.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("payload must contain finite JSON-compatible values") from exc
    if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload exceeds 65536 UTF-8 bytes")
    return event_id, entity_id, event_type, occurred_at, payload_json


class EventStore:
    """Single-process teaching adapter. Caller owns lifecycle with EventStore(path)."""

    def __init__(self, filename: str | Path = ":memory:"):
        self._db = sqlite3.connect(str(filename), timeout=5, isolation_level=None)
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=5000")
        self._db.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )""")
        self._db.execute("CREATE INDEX IF NOT EXISTS events_entity_order ON events(entity_id, occurred_at, event_id)")

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    def append(self, event: Event) -> bool:
        """Return True on insertion, False on exact retry; reject conflicting retries.

        BEGIN IMMEDIATE serializes the read/insert decision against other SQLite writers.
        A failed operation is rolled back and cannot leave a partial event.
        """
        row = _prepare(event)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            existing = self._db.execute(
                "SELECT entity_id, event_type, occurred_at, payload_json FROM events WHERE event_id = ?",
                (row[0],),
            ).fetchone()
            if existing is not None:
                if existing != row[1:]:
                    raise IdempotencyConflict("event_id already belongs to different content")
                self._db.execute("COMMIT")
                return False
            self._db.execute(
                "INSERT INTO events(event_id,entity_id,event_type,occurred_at,payload_json) VALUES(?,?,?,?,?)",
                row,
            )
            self._db.execute("COMMIT")
            return True
        except BaseException:
            self._db.execute("ROLLBACK")
            raise

    def list_for_entity(self, entity_id: str, *, limit: int = 50, after: tuple[str, str] | None = None) -> list[Event]:
        """Seek pagination: after = (occurred_at UTC ISO string, event_id)."""
        entity_id = _identifier(entity_id, "entity_id")
        if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError("limit must be an integer between 1 and 100")
        if after is None:
            rows = self._db.execute(
                "SELECT event_id,entity_id,event_type,occurred_at,payload_json FROM events WHERE entity_id=? "
                "ORDER BY occurred_at,event_id LIMIT ?", (entity_id, limit),
            ).fetchall()
        else:
            if not isinstance(after, tuple) or len(after) != 2:
                raise ValueError("after must be a two-item tuple")
            at, event_id = after
            if not isinstance(at, str):
                raise ValueError("after timestamp must be a string")
            event_id = _identifier(event_id, "after event_id")
            try:
                parsed = datetime.fromisoformat(at)
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise ValueError("timezone required")
                at = parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")
            except ValueError as exc:
                raise ValueError("after timestamp must be timezone-aware ISO 8601") from exc
            rows = self._db.execute(
                "SELECT event_id,entity_id,event_type,occurred_at,payload_json FROM events "
                "WHERE entity_id=? AND (occurred_at,event_id) > (?,?) "
                "ORDER BY occurred_at,event_id LIMIT ?", (entity_id, at, event_id, limit),
            ).fetchall()
        return [Event(eid, ent, etype, datetime.fromisoformat(at), json.loads(payload)) for eid, ent, etype, at, payload in rows]

    def count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
