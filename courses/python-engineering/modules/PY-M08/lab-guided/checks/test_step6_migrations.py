"""Step 6 - a versioned schema: migrate() applies each migration once, atomically, and the store opens through it."""
from __future__ import annotations

import os
import sqlite3
import stat
from datetime import datetime, timedelta, timezone

import pytest



T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


def raw(path=":memory:", timeout=5.0):
    """A plain autocommit connection, like the one the store keeps."""
    return sqlite3.connect(path, timeout=timeout, isolation_level=None)


def names(db, kind):
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = ? AND name NOT LIKE 'sqlite_%'", (kind,))}


def test_a_new_database_is_brought_to_the_latest_version(es):
    db = raw()
    assert es.schema_version(db) == 0
    assert es.migrate(db) == len(es.MIGRATIONS) == 3
    assert es.schema_version(db) == 3
    assert "events" in names(db, "table")
    assert {"events_entity_order", "events_type_time", "events_received"} <= names(db, "index")
    assert "received_at" in {r[1] for r in db.execute("PRAGMA table_info(events)")}
    assert not db.in_transaction


def test_migrating_again_applies_nothing(es, trace):
    db = raw()
    es.migrate(db)
    log = trace(db)
    assert es.migrate(db) == 3
    assert log.matching("CREATE", "ALTER", "DROP", "UPDATE", "PRAGMA USER_VERSION =") == []
    assert not db.in_transaction


def test_a_database_made_by_the_first_release_is_adopted_with_its_rows(es, original_schema):
    db = raw()
    for statement in original_schema:
        db.execute(statement)
    db.execute("INSERT INTO events VALUES ('old-1', 'customer-A', 'created', '2026-01-02T03:04:05.000000+00:00', '{\"value\":1}')")
    assert es.schema_version(db) == 0                     # the first release never stored a version
    assert es.migrate(db) == 3
    assert db.execute("SELECT event_id, received_at FROM events").fetchall() == [("old-1", "2026-01-02T03:04:05.000000+00:00")]    # backfilled with the best known value


def test_an_older_database_is_upgraded_step_by_step_and_keeps_its_rows(es):
    db = raw()
    for statement in es.MIGRATIONS[0]:
        db.execute(statement)
    db.execute("PRAGMA user_version = 1")
    db.execute("INSERT INTO events VALUES ('v1', 'e', 't', '2026-02-03T04:05:06.000000+00:00', '{}')")
    assert es.migrate(db) == 3
    assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 1
    assert es.schema_version(db) == 3


def test_a_failing_migration_leaves_no_trace_and_the_old_version(es):
    db = raw()
    broken = [es.MIGRATIONS[0], ("CREATE TABLE half_done (x INTEGER)", "CREATE TABLE half_done (x INTEGER)")]
    with pytest.raises(sqlite3.OperationalError, match="half_done"):
        es.migrate(db, broken)
    assert es.schema_version(db) == 1
    assert "half_done" not in names(db, "table")          # the first statement of the failed migration was rolled back with it
    assert "events" in names(db, "table")                 # the earlier migration stays applied
    assert not db.in_transaction


def test_a_keyboard_interrupt_during_a_migration_also_rolls_back(es):
    class Interrupted:
        def __iter__(self):
            raise KeyboardInterrupt

    db = raw()
    with pytest.raises(KeyboardInterrupt):
        es.migrate(db, [es.MIGRATIONS[0], Interrupted()])
    assert es.schema_version(db) == 1 and not db.in_transaction


def test_a_database_from_the_future_is_refused_and_untouched(es):
    db = raw()
    db.execute("PRAGMA user_version = 99")
    with pytest.raises(es.SchemaTooNew):
        es.migrate(db)
    assert es.schema_version(db) == 99 and names(db, "table") == set() and not db.in_transaction


def test_migrate_refuses_to_run_inside_a_transaction_and_leaves_it_open(es):
    db = raw()
    db.execute("BEGIN")
    with pytest.raises(es.StoreError):
        es.migrate(db)
    assert db.in_transaction
    db.execute("ROLLBACK")


def test_migrate_takes_the_write_lock_before_it_reads_the_version(es, trace):
    db = raw()
    log = trace(db)
    es.migrate(db)
    first = log.statements[0].strip().upper()
    assert first.startswith("BEGIN IMMEDIATE"), f"the first statement must take the write lock, not {first!r}"


def test_a_second_process_waits_for_the_lock_instead_of_migrating_twice(es, tmp_path):
    path = str(tmp_path / "events.db")
    holder = raw(path)
    holder.execute("BEGIN IMMEDIATE")
    other = raw(path, timeout=0.05)
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        es.migrate(other)
    assert es.schema_version(holder) == 0
    holder.execute("ROLLBACK")
    assert es.migrate(other) == 3
    holder.close()
    other.close()


def test_the_version_follows_the_number_of_migrations_given(es):
    db = raw()
    assert es.migrate(db, es.MIGRATIONS[:2]) == 2
    assert es.schema_version(db) == 2 and "events_received" not in names(db, "index")
    assert es.migrate(db) == 3


def test_opening_a_store_migrates_it(es, open_store):
    store = open_store()
    assert es.schema_version(store._db) == 3
    assert store.count() == 0


def test_opening_an_unversioned_file_keeps_its_events(es, open_store, tmp_path, make, original_schema):
    path = tmp_path / "events.db"
    db = sqlite3.connect(path, isolation_level=None)
    for statement in original_schema:
        db.execute(statement)
    db.execute("INSERT INTO events VALUES ('old-1', 'customer-A', 'created', '2026-01-02T03:04:05.000000+00:00', '{\"value\":1}')")
    db.close()
    store = open_store(path)
    assert [e.event_id for e in store.list_for_entity("customer-A")] == ["old-1"]
    assert store.append(make("new-1", when=T0))
    assert store.count() == 2


def test_a_store_that_cannot_migrate_closes_its_connection_and_reports_why(es, tmp_path, monkeypatch):
    path = tmp_path / "future.db"
    seed = sqlite3.connect(path)
    seed.execute("PRAGMA user_version = 99")
    seed.close()
    created = []
    real = sqlite3.connect

    def spy(*args, **kwargs):
        connection = real(*args, **kwargs)
        created.append(connection)
        return connection

    monkeypatch.setattr(es.sqlite3, "connect", spy)
    with pytest.raises(es.SchemaTooNew):
        es.EventStore(path)
    assert len(created) == 1
    with pytest.raises(sqlite3.ProgrammingError):          # "Cannot operate on a closed database."
        created[0].execute("SELECT 1")


def test_a_new_database_file_is_private_whatever_the_umask(es, open_store, tmp_path):
    path = tmp_path / "events.db"
    old = os.umask(0)                                      # the most permissive umask: only an explicit mode keeps the file private
    try:
        store = open_store(path)
    finally:
        os.umask(old)
    assert path.exists() and store.count() == 0
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_an_existing_file_keeps_its_mode(es, open_store, tmp_path):
    path = tmp_path / "events.db"
    open_store(path).close()
    if os.name == "posix":
        os.chmod(path, 0o640)
    open_store(path)
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_a_path_object_and_a_string_both_work(es, open_store, tmp_path):
    for target in (tmp_path / "a.db", str(tmp_path / "b.db")):
        open_store(target).close()
        assert os.path.exists(target)


def test_an_empty_path_is_refused_and_creates_nothing(es, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        es.EventStore("")
    assert list(tmp_path.iterdir()) == []


def test_a_missing_directory_is_an_error_not_a_silent_fallback(es, tmp_path):
    with pytest.raises((FileNotFoundError, sqlite3.OperationalError)):
        es.EventStore(tmp_path / "no-such-dir" / "events.db")


def test_closing_twice_is_harmless_and_a_closed_store_refuses_work(es, open_store):
    store = open_store()
    store.close()
    store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        store.count()


def test_the_context_manager_closes_the_store(es, tmp_path):
    with es.EventStore(tmp_path / "events.db") as store:
        connection = store._db
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_foreign_keys_are_on_and_the_busy_timeout_is_set(es, open_store):
    store = open_store()
    assert store._db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert store._db.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert store._db.isolation_level is None
