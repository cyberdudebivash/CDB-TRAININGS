"""Step 9 - retention counts from the time of receipt, not from the time of the event."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest



T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_the_store_records_when_it_received_each_event(es, open_store, make, clock):
    store = open_store()
    store.append(make("a", when=T0))
    clock.advance(hours=2)
    store.append_many([make("b", when=T0)])
    received = store.received_at("a")
    assert received == T0 + timedelta(hours=1) and received.utcoffset() == timedelta(0)
    assert store.received_at("b") == T0 + timedelta(hours=3)


def test_a_retry_does_not_change_the_time_of_receipt(es, open_store, make, clock):
    store = open_store()
    store.append(make("a", when=T0))
    clock.advance(days=1)
    assert store.append(make("a", when=T0)) is False
    assert store.received_at("a") == T0 + timedelta(hours=1)


def test_an_unknown_event_has_no_time_of_receipt(es, open_store):
    with pytest.raises(KeyError):
        open_store().received_at("nope")


def test_a_clock_that_returns_a_naive_time_is_refused_and_nothing_is_stored(es, open_store, make, clock):
    store = open_store()
    clock.now = datetime(2026, 10, 14, 13, 0)
    with pytest.raises(ValueError):
        store.append(make("a", when=T0))
    with pytest.raises(ValueError):
        store.append_many([make("b", when=T0)])
    assert store.count() == 0


def test_the_clock_may_use_any_time_zone(es, open_store, make, clock):
    store = open_store()
    clock.now = datetime(2026, 10, 14, 18, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    store.append(make("a", when=T0))
    assert store.received_at("a") == datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)


def test_purge_deletes_what_was_received_strictly_before_the_cutoff(es, open_store, make, clock):
    store = open_store()
    for i in range(4):
        store.append(make(f"e{i}", when=T0))
        clock.advance(hours=1)                              # received at 13:00, 14:00, 15:00, 16:00
    cutoff = T0 + timedelta(hours=3)                        # 15:00
    assert store.purge_received_before(cutoff) == 2
    assert [e.event_id for e in store.list_for_entity("customer-A")] == ["e2", "e3"]
    assert store.purge_received_before(cutoff) == 0
    assert store.purge_received_before(T0) == 0


def test_an_old_event_that_arrives_late_survives_the_purge(es, open_store, make, clock):
    store = open_store()
    store.append(make("old-but-late", when=T0 - timedelta(days=400)))      # happened long ago, received just now (13:00)
    clock.advance(hours=5)
    store.append(make("recent", when=T0))                                   # received at 18:00
    assert store.purge_received_before(T0 + timedelta(minutes=30)) == 0     # cutoff 12:30: nothing was received that early (purging by occurred_at would delete the old event)
    assert store.count() == 2


def test_the_cutoff_must_be_timezone_aware(es, open_store):
    store = open_store()
    for bad in (datetime(2026, 10, 14), "2026-10-14T12:00:00", "yesterday"):
        with pytest.raises(ValueError):
            store.purge_received_before(bad)


def test_the_cutoff_may_be_text_with_an_offset_and_is_exclusive(es, open_store, make, clock):
    store = open_store()
    store.append(make("a", when=T0))                                        # received at 13:00 UTC
    assert store.purge_received_before("2026-10-14T18:30:00+05:30") == 0    # 13:00 UTC exactly: not strictly before
    assert store.purge_received_before("2026-10-14T19:00:00+05:30") == 1    # 13:30 UTC
    assert store.count() == 0


def test_events_stored_by_the_first_release_are_purged_by_their_event_time(es, open_store, tmp_path, original_schema):
    path = tmp_path / "events.db"
    db = sqlite3.connect(path, isolation_level=None)
    for statement in original_schema:
        db.execute(statement)
    db.execute("INSERT INTO events VALUES ('old', 'e', 't', '2026-01-02T03:04:05.000000+00:00', '{}')")
    db.close()
    store = open_store(path)
    assert store.received_at("old") == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert store.purge_received_before(datetime(2026, 2, 1, tzinfo=timezone.utc)) == 1
