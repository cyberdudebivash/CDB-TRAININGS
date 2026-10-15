"""PY-M08 guided STARTER (intentionally incomplete): safe, idempotent, versioned SQLite event persistence.

Part 1 (steps 1 to 5, from the first merged increment of this lab): open, close, idempotent append, seek pagination, count.
Part 2 (steps 6 to 10): schema migrations, atomic batches, injection-safe search, retention, query-shape checks.

Every body that raises NotImplementedError is yours; each docstring is the specification and checks/ holds the tests. Edit only this file.
Offline lab only. This is not a multi-tenant or Internet-facing service.
Supported runtime: Python 3.11+ (uses only the standard library).
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_PAYLOAD_BYTES = 65_536
MAX_PAGE_SIZE = 100
MAX_BATCH = 1_000
MAX_SEARCH_TEXT = 200

# One tuple of single SQL statements per schema version. Version n is complete when MIGRATIONS[n - 1] has been applied. A released entry is never edited: append a new one.
# Version 1 is the schema the first release created with CREATE TABLE IF NOT EXISTS, so a database created by that release (stored version 0, tables present) is adopted, not rebuilt.
MIGRATIONS: tuple[tuple[str, ...], ...] = (
    (
        """CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS events_entity_order ON events(entity_id, occurred_at, event_id)",
    ),
    ("CREATE INDEX events_type_time ON events(event_type, occurred_at, event_id)",),
    (
        "ALTER TABLE events ADD COLUMN received_at TEXT",
        "UPDATE events SET received_at = occurred_at WHERE received_at IS NULL",       # events stored before this version: the best known value
        "CREATE INDEX events_received ON events(received_at)",
    ),
)

ORDER_COLUMNS: dict[str, str] = {"time": "occurred_at", "entity": "entity_id", "type": "event_type"}


class IdempotencyConflict(ValueError):
    """The same event_id was submitted with different event contents."""


class StoreError(RuntimeError):
    """Base class of the storage errors this module raises on purpose."""


class SchemaTooNew(StoreError):
    """The database was written by a newer version of the program than this one."""


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    entity_id: str
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]


def _identifier(value: str, name: str) -> str:
    """Return `value` if it is a str of 1 to 128 characters without control characters (code points below 32 and 127); otherwise ValueError saying which `name` is wrong."""
    raise NotImplementedError("Step 3: validate identifiers")


def _prepare(event: Event) -> tuple[str, str, str, str, str]:
    """Validate an Event and return the five values to store, in column order: (event_id, entity_id, event_type, occurred_at, payload_json).

    TypeError if `event` is not an Event. ValueError for an invalid identifier (see `_identifier`), for an `occurred_at` that is not a timezone-aware datetime (the message must
    contain 'timezone-aware'), for a payload that is not a dict or holds values JSON cannot represent (NaN, infinity, sets), or whose JSON text exceeds MAX_PAYLOAD_BYTES UTF-8
    bytes (the message must contain '65536'). `occurred_at` is stored as UTC text of fixed width (isoformat with microseconds); the payload as compact JSON with sorted keys,
    so that two payloads with the same content give the same text. Nothing touches the database here: validation comes before the transaction.
    """
    raise NotImplementedError("Step 3: validate an event and prepare its stored values")


def _utc(value: datetime | str, name: str) -> str:
    """A timezone-aware datetime (or ISO-8601 text with an offset) as fixed-width UTC text (`isoformat(timespec="microseconds")` of the UTC time), the form stored in the database.

    ValueError("<name> must be timezone-aware") for a naive datetime or for anything that is not a datetime or ISO text; ValueError("<name> must be timezone-aware ISO 8601") for
    text that is not ISO-8601. A fixed width in one time zone sorts alphabetically in time order: `ORDER BY occurred_at` relies on it.
    """
    raise NotImplementedError("Step 3: normalise a timestamp to UTC text")


def _limit(limit: Any) -> int:
    """Return `limit` if it is an int (not a bool, not a float) from 1 to MAX_PAGE_SIZE, otherwise ValueError("limit must be an integer between 1 and 100")."""
    raise NotImplementedError("Step 4: validate a page size")


def _like_pattern(text: str) -> str:
    """'%text%' with LIKE's wildcards (and the escape character) in `text` made ordinary characters; use with ESCAPE '\\'."""
    raise NotImplementedError("Step 8: escape LIKE wildcards")


def _create_private_file(path: str) -> None:
    """Create an empty file readable and writable only by its owner, unless it exists (SQLite treats an empty file as a new database)."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    os.close(fd)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------------------------------------------------------------------------- step 6
def schema_version(db: sqlite3.Connection) -> int:
    """The schema version stored in the database file (`PRAGMA user_version`; 0 for a new or unversioned database)."""
    raise NotImplementedError("Step 6: read the schema version")


def migrate(db: sqlite3.Connection, migrations: Sequence[Iterable[str]] = MIGRATIONS) -> int:
    """Bring the database to the latest version and return that version (== len(migrations)). The connection is in autocommit mode (isolation_level=None).

    * Each migration runs in its **own transaction** together with the update of the stored version: a failure leaves the previous version with none of that migration's statements
      applied (SQLite rolls back DDL). Start it with `BEGIN IMMEDIATE`, which takes the write lock at once, and **read the stored version after the lock is taken**, so two
      processes that start together cannot both apply the same migration.
    * Calling it again does nothing and returns the same number, without applying a statement.
    * A stored version higher than len(migrations) raises SchemaTooNew and touches nothing.
    * Inside an open transaction (`db.in_transaction`) raise StoreError and leave that transaction open.
    * `PRAGMA user_version = N` cannot take a bound parameter; N is an int the program computed, never text from outside.
    * On any failure, also KeyboardInterrupt, roll back and re-raise the original exception.
    """
    raise NotImplementedError("Step 6: apply the pending migrations atomically")


class EventStore:
    """Single-process teaching adapter. Caller owns lifecycle with EventStore(path).

    `clock` (step 9) returns the current timezone-aware time; it is injected so that tests can control it. The connection is kept in `self._db`: the checks of steps 7 to 10 trace it.
    """

    def __init__(self, filename: str | Path = ":memory:", *, clock: Callable[[], datetime] | None = None):
        """Steps 1 and 6: open the database and make sure the schema is current.

        * ValueError for an empty path (SQLite would silently use a private temporary database). A new database *file* is created with mode 0o600 before SQLite opens it
          (`_create_private_file`), because SQLite itself would use the process umask, typically 0o644, which makes the data world readable. Other errors propagate.
        * Connect with `timeout=5` and `isolation_level=None` (autocommit: transactions are explicit), keep the connection in `self._db`, turn on `PRAGMA foreign_keys` and set
          `PRAGMA busy_timeout=5000`, then call `migrate(self._db)`. If any of that fails, close the connection and re-raise (an open connection must not leak).
        * Keep `clock or _utc_now` as `self._clock`.
        """
        raise NotImplementedError("Steps 1 and 6: open SQLite, configure it and migrate the schema")

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Step 2: close the connection. Closing a store twice is harmless."""
        raise NotImplementedError("Step 2: close your connection")

    def _now(self) -> str:
        """The current time from the injected clock as fixed-width UTC text; ValueError if the clock returns a naive time. (Given.)"""
        moment = self._clock()
        if not isinstance(moment, datetime) or moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return moment.astimezone(timezone.utc).isoformat(timespec="microseconds")

    def append(self, event: Event) -> bool:
        """Return True on insertion, False on exact retry; reject conflicting retries.

        BEGIN IMMEDIATE serializes the read/insert decision against other SQLite writers.
        A failed operation is rolled back and cannot leave a partial event.
        The time of receipt (step 9) is `self._now()`; a retry does not change it.
        """
        raise NotImplementedError("Step 3: implement a safe idempotent append")

    # ------------------------------------------------------------------------------------------------------------------------------------- step 7
    def append_many(self, events: Iterable[Event]) -> tuple[int, int]:
        """Store a batch **all or nothing** and return (inserted, duplicates).

        * Every event is validated before the transaction starts (TypeError for an item that is not an Event, ValueError for an invalid one): a bad batch touches nothing.
        * More than MAX_BATCH events: ValueError, also before anything is written. An empty batch returns (0, 0) and opens no transaction.
        * One `BEGIN IMMEDIATE ... COMMIT` for the whole batch. An exact retry of a stored event (or a repeat inside the batch) counts as a duplicate; a conflicting one raises
          IdempotencyConflict and **none** of the batch is stored, including the events before it.
        * Any other failure, also KeyboardInterrupt, rolls everything back and propagates.
        """
        raise NotImplementedError("Step 7: store a batch all or nothing")

    def list_for_entity(self, entity_id: str, *, limit: int = 50, after: tuple[str, str] | None = None) -> list[Event]:
        """Step 4. Seek pagination: after = (occurred_at UTC ISO string, event_id).

        The events of one entity ordered by (occurred_at, event_id), at most `limit` (an int from 1 to 100; a bool, a float, 0 or 101 are ValueError). With `after` (a two-item tuple
        of timezone-aware ISO-8601 text and an event id; ValueError for anything else) only the events strictly after that position, compared as a pair. Validate before querying;
        bind every value; return Event objects with timezone-aware UTC `occurred_at`.
        """
        raise NotImplementedError("Step 4: implement stable seek pagination")

    def count(self) -> int:
        """Step 5: the number of stored events."""
        raise NotImplementedError("Step 5: implement count")

    # ------------------------------------------------------------------------------------------------------------------------------------- step 8
    def search(
        self,
        *,
        entity_id: str | None = None,
        event_type: str | None = None,
        text: str | None = None,
        since: datetime | str | None = None,
        until: datetime | str | None = None,
        order_by: str = "time",
        descending: bool = False,
        limit: int = 50,
    ) -> list[Event]:
        """Events matching ALL the given filters. Every value is bound as a parameter; the only text placed into the statement is a fixed fragment chosen by this code.

        * `entity_id`, `event_type`: equal (exact, case-sensitive; validated like the identifiers of `append`). Compare the column itself, not a function of it, or its index is unusable.
        * `text`: the stored payload text (the JSON text, in which a quote or a backslash inside a string is stored escaped: search for plain words) contains it, ignoring
          ASCII case, with '%', '_' and a backslash taken literally (escape them and use `ESCAPE`). A `str` of 1 to MAX_SEARCH_TEXT characters, otherwise ValueError.
        * `since` (inclusive) and `until` (exclusive): timezone-aware datetimes or ISO-8601 text with an offset on `occurred_at`; ValueError otherwise.
        * `order_by`: a key of ORDER_COLUMNS ("time", "entity", "type"), ValueError for anything else: a column name cannot be a bound parameter, and `ORDER BY ?` would sort by a
          constant and silently do nothing. Ties are broken by `event_id` in the same direction, so the order is deterministic.
        * `limit`: as for `list_for_entity` (an int from 1 to 100, ValueError otherwise).
        """
        raise NotImplementedError("Step 8: implement injection-safe search")

    def count_by_type(self, since: datetime | str | None = None) -> dict[str, int]:
        """{event_type: number of events} for events that occurred at or after `since` (None means all), keys in alphabetical order: the handbook's daily summary query."""
        raise NotImplementedError("Step 8: count events by type")

    # ------------------------------------------------------------------------------------------------------------------------------------- step 9
    def received_at(self, event_id: str) -> datetime:
        """When the store first received the event (UTC, timezone-aware). KeyError if there is no such event."""
        raise NotImplementedError("Step 9: read the time of receipt")

    def purge_received_before(self, cutoff: datetime | str) -> int:
        """Retention: delete the events the store received strictly before `cutoff` and return how many were deleted. Retention counts from the time of receipt, not from
        `occurred_at`: an old event that arrives late must not vanish in the next purge. `cutoff` is a timezone-aware datetime or ISO-8601 text with an offset (ValueError otherwise)."""
        raise NotImplementedError("Step 9: purge by time of receipt")

    # ------------------------------------------------------------------------------------------------------------------------------------- step 10
    def explain(self, sql: str, params: Iterable[Any] = ()) -> list[str]:
        """The `detail` column of `EXPLAIN QUERY PLAN <sql>` as a list of strings, one per plan step, e.g. 'SEARCH events USING INDEX events_entity_order (entity_id=?)' or
        'SCAN events'. The wording differs a little between SQLite versions; the words SEARCH, SCAN and USING INDEX are stable. Bind `params` as for any statement."""
        raise NotImplementedError("Step 10: return the query plan")
