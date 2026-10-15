"""Student starter for the PY-M08 guided lab. Intentionally incomplete.

Do not use in production. Complete TODO functions based on the public contract
and the guided reference. The validation tests should initially fail.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class IdempotencyConflict(ValueError):
    """Same event_id submitted with different content."""


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    entity_id: str
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]


class EventStore:
    def __init__(self, filename: str | Path = ':memory:'):
        # TODO: open a sqlite3 connection and initialize the events schema.
        raise NotImplementedError('Step 1: open SQLite and create the event table')

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        # TODO: close the connection.
        raise NotImplementedError('Step 2: close your connection')

    def append(self, event: Event) -> bool:
        # TODO: validate, normalize UTC, start transaction, insert or reject retry.
        raise NotImplementedError('Step 3: implement a safe idempotent append')

    def list_for_entity(self, entity_id: str, *, limit: int = 50, after: tuple[str, str] | None = None) -> list[Event]:
        # TODO: validate arguments and select rows with SQL placeholders.
        raise NotImplementedError('Step 4: implement stable seek pagination')

    def count(self) -> int:
        # TODO: count persisted events.
        raise NotImplementedError('Step 5: implement count')
