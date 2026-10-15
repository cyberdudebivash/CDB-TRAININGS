"""PY-M08 guided reference: safe, idempotent, versioned SQLite event persistence.

Part 1 (steps 1 to 5, from the first merged increment of this lab): open, close, idempotent append, seek pagination, count.
Part 2 (steps 6 to 10): schema migrations, atomic batches, injection-safe search, retention, query-shape checks.

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
    if not isinstance(value, str) or not (1 <= len(value) <= 128):
        raise ValueError(f"{name} must have 1..128 characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{name} may not contain control characters")
    return value


def _prepare(event: Event) -> tuple[str, str, str, str, str]:
    """Validate an Event and return the five values to store, in column order: (event_id, entity_id, event_type, occurred_at, payload_json).

    TypeError if `event` is not an Event. ValueError for an invalid identifier (see `_identifier`), for an `occurred_at` that is not a timezone-aware datetime (the message must
    contain 'timezone-aware'), for a payload that is not a dict or holds values JSON cannot represent (NaN, infinity, sets), or whose JSON text exceeds MAX_PAYLOAD_BYTES UTF-8
    bytes (the message must contain '65536'). `occurred_at` is stored as UTC text of fixed width (isoformat with microseconds); the payload as compact JSON with sorted keys,
    so that two payloads with the same content give the same text. Nothing touches the database here: validation comes before the transaction.
    """
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


def _utc(value: datetime | str, name: str) -> str:
    """A timezone-aware datetime (or ISO-8601 text with an offset) as fixed-width UTC text (`isoformat(timespec="microseconds")` of the UTC time), the form stored in the database.

    ValueError("<name> must be timezone-aware") for a naive datetime or for anything that is not a datetime or ISO text; ValueError("<name> must be timezone-aware ISO 8601") for
    text that is not ISO-8601. A fixed width in one time zone sorts alphabetically in time order: `ORDER BY occurred_at` relies on it.
    """
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be timezone-aware ISO 8601") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _limit(limit: Any) -> int:
    """Return `limit` if it is an int (not a bool, not a float) from 1 to MAX_PAGE_SIZE, otherwise ValueError("limit must be an integer between 1 and 100")."""
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError("limit must be an integer between 1 and 100")
    return limit


def _like_pattern(text: str) -> str:
    """'%text%' with LIKE's wildcards (and the escape character) in `text` made ordinary characters; use with ESCAPE '\\'."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


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
    return int(db.execute("PRAGMA user_version").fetchone()[0])


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
    if db.in_transaction:
        raise StoreError("migrate() must not run inside a transaction")
    while True:
        db.execute("BEGIN IMMEDIATE")
        try:
            current = schema_version(db)
            if current > len(migrations):
                raise SchemaTooNew(f"database schema is version {current}; this program knows version {len(migrations)}")
            if current == len(migrations):
                db.execute("ROLLBACK")
                return current
            for statement in migrations[current]:
                db.execute(statement)
            db.execute(f"PRAGMA user_version = {current + 1}")
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise


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
        target = os.fspath(filename)
        if not target:
            raise ValueError("an empty path would create a temporary database; use ':memory:' on purpose")
        if target != ":memory:":
            _create_private_file(target)                    # step 6: mode 0o600, whatever the umask
        self._clock = clock or _utc_now
        self._db = sqlite3.connect(target, timeout=5, isolation_level=None)
        try:
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.execute("PRAGMA busy_timeout=5000")
            migrate(self._db)                               # step 6: replaces CREATE TABLE IF NOT EXISTS here
        except BaseException:
            self._db.close()
            raise

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Step 2: close the connection. Closing a store twice is harmless."""
        self._db.close()

    def _now(self) -> str:
        """The current time from the injected clock as fixed-width UTC text; ValueError if the clock returns a naive time. (Given.)"""
        moment = self._clock()
        if not isinstance(moment, datetime) or moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return moment.astimezone(timezone.utc).isoformat(timespec="microseconds")

    def _store(self, row: tuple[str, str, str, str, str], received_at: str) -> bool:
        """Inside an open transaction: insert the prepared row, or recognise an exact retry (False) or a conflicting one (IdempotencyConflict)."""
        existing = self._db.execute(
            "SELECT entity_id, event_type, occurred_at, payload_json FROM events WHERE event_id = ?",
            (row[0],),
        ).fetchone()
        if existing is not None:
            if existing != row[1:]:
                raise IdempotencyConflict("event_id already belongs to different content")
            return False
        self._db.execute(
            "INSERT INTO events(event_id,entity_id,event_type,occurred_at,payload_json,received_at) VALUES(?,?,?,?,?,?)",
            (*row, received_at),
        )
        return True

    def append(self, event: Event) -> bool:
        """Return True on insertion, False on exact retry; reject conflicting retries.

        BEGIN IMMEDIATE serializes the read/insert decision against other SQLite writers.
        A failed operation is rolled back and cannot leave a partial event.
        The time of receipt (step 9) is `self._now()`; a retry does not change it.
        """
        row = _prepare(event)
        received_at = self._now()
        self._db.execute("BEGIN IMMEDIATE")
        try:
            inserted = self._store(row, received_at)
            self._db.execute("COMMIT")
            return inserted
        except BaseException:
            self._db.execute("ROLLBACK")
            raise

    # ------------------------------------------------------------------------------------------------------------------------------------- step 7
    def append_many(self, events: Iterable[Event]) -> tuple[int, int]:
        """Store a batch **all or nothing** and return (inserted, duplicates).

        * Every event is validated before the transaction starts (TypeError for an item that is not an Event, ValueError for an invalid one): a bad batch touches nothing.
        * More than MAX_BATCH events: ValueError, also before anything is written. An empty batch returns (0, 0) and opens no transaction.
        * One `BEGIN IMMEDIATE ... COMMIT` for the whole batch. An exact retry of a stored event (or a repeat inside the batch) counts as a duplicate; a conflicting one raises
          IdempotencyConflict and **none** of the batch is stored, including the events before it.
        * Any other failure, also KeyboardInterrupt, rolls everything back and propagates.
        """
        rows = [_prepare(event) for event in events]
        if len(rows) > MAX_BATCH:
            raise ValueError(f"a batch holds at most {MAX_BATCH} events")
        if not rows:
            return (0, 0)
        received_at = self._now()
        inserted = 0
        self._db.execute("BEGIN IMMEDIATE")
        try:
            for row in rows:
                inserted += self._store(row, received_at)
            self._db.execute("COMMIT")
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        return (inserted, len(rows) - inserted)

    def _events(self, rows: Iterable[tuple[str, str, str, str, str]]) -> list[Event]:
        return [Event(eid, ent, etype, datetime.fromisoformat(at), json.loads(payload)) for eid, ent, etype, at, payload in rows]

    def list_for_entity(self, entity_id: str, *, limit: int = 50, after: tuple[str, str] | None = None) -> list[Event]:
        """Step 4. Seek pagination: after = (occurred_at UTC ISO string, event_id).

        The events of one entity ordered by (occurred_at, event_id), at most `limit` (an int from 1 to 100; a bool, a float, 0 or 101 are ValueError). With `after` (a two-item tuple
        of timezone-aware ISO-8601 text and an event id; ValueError for anything else) only the events strictly after that position, compared as a pair. Validate before querying;
        bind every value; return Event objects with timezone-aware UTC `occurred_at`.
        """
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
        return self._events(rows)

    def count(self) -> int:
        """Step 5: the number of stored events."""
        return int(self._db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

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
        limit = _limit(limit)
        if order_by not in ORDER_COLUMNS:
            raise ValueError(f"cannot order by {order_by!r}; choose one of {sorted(ORDER_COLUMNS)}")
        clauses: list[str] = []
        params: list[Any] = []
        if entity_id is not None:
            clauses.append("entity_id = ?")
            params.append(_identifier(entity_id, "entity_id"))
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(_identifier(event_type, "event_type"))
        if text is not None:
            if not isinstance(text, str) or not 1 <= len(text) <= MAX_SEARCH_TEXT:
                raise ValueError(f"text must be 1 to {MAX_SEARCH_TEXT} characters")
            clauses.append("payload_json LIKE ? ESCAPE '\\'")
            params.append(_like_pattern(text))
        if since is not None:
            clauses.append("occurred_at >= ?")
            params.append(_utc(since, "since"))
        if until is not None:
            clauses.append("occurred_at < ?")
            params.append(_utc(until, "until"))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        direction = "DESC" if descending else "ASC"
        sql = f"SELECT event_id,entity_id,event_type,occurred_at,payload_json FROM events{where} ORDER BY {ORDER_COLUMNS[order_by]} {direction}, event_id {direction} LIMIT ?"
        return self._events(self._db.execute(sql, [*params, limit]).fetchall())

    def count_by_type(self, since: datetime | str | None = None) -> dict[str, int]:
        """{event_type: number of events} for events that occurred at or after `since` (None means all), keys in alphabetical order: the handbook's daily summary query."""
        if since is None:
            rows = self._db.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY event_type").fetchall()
        else:
            rows = self._db.execute(
                "SELECT event_type, COUNT(*) FROM events WHERE occurred_at >= ? GROUP BY event_type ORDER BY event_type", (_utc(since, "since"),)
            ).fetchall()
        return {event_type: int(n) for event_type, n in rows}

    # ------------------------------------------------------------------------------------------------------------------------------------- step 9
    def received_at(self, event_id: str) -> datetime:
        """When the store first received the event (UTC, timezone-aware). KeyError if there is no such event."""
        row = self._db.execute("SELECT received_at FROM events WHERE event_id = ?", (_identifier(event_id, "event_id"),)).fetchone()
        if row is None:
            raise KeyError(event_id)
        return datetime.fromisoformat(row[0])

    def purge_received_before(self, cutoff: datetime | str) -> int:
        """Retention: delete the events the store received strictly before `cutoff` and return how many were deleted. Retention counts from the time of receipt, not from
        `occurred_at`: an old event that arrives late must not vanish in the next purge. `cutoff` is a timezone-aware datetime or ISO-8601 text with an offset (ValueError otherwise)."""
        return self._db.execute("DELETE FROM events WHERE received_at < ?", (_utc(cutoff, "cutoff"),)).rowcount

    # ------------------------------------------------------------------------------------------------------------------------------------- step 10
    def explain(self, sql: str, params: Iterable[Any] = ()) -> list[str]:
        """The `detail` column of `EXPLAIN QUERY PLAN <sql>` as a list of strings, one per plan step, e.g. 'SEARCH events USING INDEX events_entity_order (entity_id=?)' or
        'SCAN events'. The wording differs a little between SQLite versions; the words SEARCH, SCAN and USING INDEX are stable. Bind `params` as for any statement."""
        return [str(row[3]) for row in self._db.execute(f"EXPLAIN QUERY PLAN {sql}", tuple(params)).fetchall()]
