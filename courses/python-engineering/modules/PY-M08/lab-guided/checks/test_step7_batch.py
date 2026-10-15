"""Step 7 - append_many(): a batch is one transaction, all or nothing."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest



T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


def batch(make, n, start=0, **kw):
    return [make(f"evt-{i:03d}", when=T0 + timedelta(minutes=i), **kw) for i in range(start, start + n)]


def test_a_batch_is_stored_and_counted(es, open_store, make):
    store = open_store()
    events = batch(make, 5)
    assert store.append_many(events) == (5, 0)
    assert store.count() == 5
    assert store.list_for_entity("customer-A") == events


def test_retries_and_repeats_are_duplicates(es, open_store, make):
    store = open_store()
    store.append(make("evt-000", when=T0))
    events = batch(make, 3) + [make("evt-001", when=T0 + timedelta(minutes=1))]
    assert store.append_many(events) == (2, 2)             # evt-000 was stored before, evt-001 appears twice in the batch
    assert store.count() == 3
    assert store.append_many(events) == (0, 4)             # the whole batch again: nothing new


def test_one_conflicting_event_rejects_the_whole_batch(es, open_store, make):
    store = open_store()
    store.append(make("evt-002", when=T0, payload={"value": "original"}))
    events = batch(make, 4)                                # evt-000, 001, then evt-002 with another payload, then evt-003
    with pytest.raises(es.IdempotencyConflict):
        store.append_many(events)
    assert store.count() == 1                              # evt-000 and evt-001 were not kept
    assert store._db.in_transaction is False
    assert store.append_many(batch(make, 2)) == (2, 0)     # and the store still works


def test_a_conflict_inside_the_batch_rejects_the_whole_batch(es, open_store, make):
    store = open_store()
    events = [make("a", when=T0), make("b", when=T0), make("a", when=T0, payload={"value": 2})]
    with pytest.raises(es.IdempotencyConflict):
        store.append_many(events)
    assert store.count() == 0


def test_an_invalid_event_stops_the_batch_before_any_write(es, open_store, make, trace):
    store = open_store()
    log = trace(store._db)
    events = batch(make, 2) + [make("bad\nid", when=T0)] + batch(make, 2, start=10)
    with pytest.raises(ValueError):
        store.append_many(events)
    assert store.count() == 0
    assert log.matching("BEGIN", "INSERT") == []           # validation happens before the transaction


def test_an_item_that_is_not_an_event_is_a_type_error(es, open_store, make):
    store = open_store()
    with pytest.raises(TypeError):
        store.append_many([make("a"), {"event_id": "b"}])
    with pytest.raises(TypeError):
        store.append_many(make("a"))                       # one event, not an iterable of events
    assert store.count() == 0


def test_any_iterable_is_accepted(es, open_store, make):
    store = open_store()
    assert store.append_many(make(f"g{i}", when=T0) for i in range(3)) == (3, 0)


def test_the_size_of_a_batch_is_limited_before_anything_is_written(es, open_store, make, trace):
    store = open_store()
    log = trace(store._db)
    too_many = (make(f"e{i}", when=T0) for i in range(es.MAX_BATCH + 1))
    with pytest.raises(ValueError):
        store.append_many(too_many)
    assert store.count() == 0 and log.matching("BEGIN", "INSERT") == []
    assert store.append_many(make(f"e{i}", when=T0) for i in range(es.MAX_BATCH)) == (es.MAX_BATCH, 0)


def test_an_empty_batch_opens_no_transaction(es, open_store, trace):
    store = open_store()
    log = trace(store._db)
    assert store.append_many([]) == (0, 0)
    assert log.statements == []


def test_a_batch_is_one_transaction(es, open_store, make, trace):
    store = open_store()
    log = trace(store._db)
    store.append_many(batch(make, 50))
    assert len(log.matching("BEGIN")) == 1 and len(log.matching("COMMIT")) == 1 and log.matching("ROLLBACK") == []
    assert log.statements[0].upper().startswith("BEGIN IMMEDIATE")
    log.clear()
    for event in batch(make, 5, start=100):
        store.append(event)
    assert len(log.matching("COMMIT")) == 5               # one at a time: one transaction each (the price of not batching)


def test_a_database_failure_in_the_middle_rolls_everything_back(es, open_store, make):
    store = open_store()
    store._db.execute("CREATE TRIGGER refuse_boom BEFORE INSERT ON events WHEN NEW.event_id = 'boom' BEGIN SELECT RAISE(ABORT, 'refused'); END")
    events = [make("one", when=T0), make("two", when=T0), make("boom", when=T0), make("four", when=T0)]
    with pytest.raises(sqlite3.DatabaseError, match="refused"):
        store.append_many(events)
    assert store.count() == 0 and store._db.in_transaction is False


def test_a_failing_single_append_leaves_no_transaction_open(es, open_store, make):
    store = open_store()
    store._db.execute("CREATE TRIGGER refuse_boom BEFORE INSERT ON events WHEN NEW.event_id = 'boom' BEGIN SELECT RAISE(ABORT, 'refused'); END")
    with pytest.raises(sqlite3.DatabaseError):
        store.append(make("boom", when=T0))
    assert store._db.in_transaction is False
    assert store.append(make("fine", when=T0))             # not stuck in a half-open transaction


def test_a_keyboard_interrupt_during_the_batch_is_not_swallowed_and_rolls_back(es, open_store, make):
    store = open_store()

    def events():
        yield make("a", when=T0)
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        store.append_many(events())
    assert store.count() == 0 and store._db.in_transaction is False
