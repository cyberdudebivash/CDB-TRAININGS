"""Steps 1 to 5 revisited - the edges of what the first release already promised: validation happens before the transaction, nothing is silently altered."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone, tzinfo

import pytest

T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("bad", ["", "tab\there", "nul\x00byte", "unit\x1fsep", "del\x7fchar", "x" * 129, 5, None, b"bytes"])
@pytest.mark.parametrize("field", ["eid", "entity", "kind"])
def test_invalid_identifiers_are_refused_in_every_position_and_nothing_is_stored(es, open_store, make, bad, field):
    store = open_store()
    with pytest.raises(ValueError):
        store.append(make(**{field: bad}))
    assert store.count() == 0 and not store._db.in_transaction


@pytest.mark.parametrize("good", ["x", "x" * 128, "客户-1", "emoji-\U0001F600", "with space", "O'Brien", "semi;colon", "per%cent_under"])
def test_valid_identifiers_are_accepted_and_roundtrip_unchanged(es, open_store, make, good):
    store = open_store()
    assert store.append(make(eid=good, entity=good, kind=good, when=T0))
    [stored] = store.list_for_entity(good)
    assert (stored.event_id, stored.entity_id, stored.event_type) == (good, good, good)


def test_an_object_that_is_not_an_event_is_a_type_error(es, open_store):
    store = open_store()
    for bad in ("evt-1", {"event_id": "a"}, None, 5):
        with pytest.raises(TypeError):
            store.append(bad)
    assert store.count() == 0


def test_microseconds_survive_the_roundtrip(es, open_store, make):
    store = open_store()
    when = T0 + timedelta(microseconds=123456)
    store.append(make(when=when))
    assert store.list_for_entity("customer-A")[0].occurred_at == when


def test_stored_times_are_utc_and_timezone_aware(es, open_store, make):
    store = open_store()
    store.append(make(when=T0.astimezone(timezone(timedelta(hours=-8)))))
    stored = store.list_for_entity("customer-A")[0]
    assert stored.occurred_at.utcoffset() == timedelta(0)
    assert store._db.execute("SELECT occurred_at FROM events").fetchone()[0] == "2026-10-14T12:00:00.000000+00:00"


def test_a_tzinfo_that_cannot_give_an_offset_is_not_timezone_aware(es, open_store, make):
    class Unknown(tzinfo):
        def utcoffset(self, dt):
            return None

        def dst(self, dt):
            return None

        def tzname(self, dt):
            return "unknown"

    store = open_store()
    with pytest.raises(ValueError, match="timezone-aware"):
        store.append(make(when=datetime(2026, 10, 14, 12, tzinfo=Unknown())))
    assert store.count() == 0


@pytest.mark.parametrize("bad", ["2026-10-14T12:00:00+00:00", 1760443200, None])
def test_occurred_at_must_be_a_datetime(es, open_store, make, bad):
    with pytest.raises(ValueError, match="timezone-aware"):
        open_store().append(make(when=bad))


@pytest.mark.parametrize("bad", [[1, 2], "text", 5, (("a", 1),), set()])
def test_the_payload_must_be_a_json_object(es, open_store, make, bad):
    store = open_store()
    with pytest.raises(ValueError):
        store.append(make(payload=bad))
    assert store.count() == 0


def exactly(size):
    """A payload whose compact JSON text is exactly `size` bytes: {"a":"xxxx"} has 8 characters of structure."""
    return {"a": "x" * (size - 8)}


def test_the_payload_limit_is_65536_bytes_inclusive(es, open_store, make):
    store = open_store()
    assert store.append(make("fits", payload=exactly(es.MAX_PAYLOAD_BYTES)))
    with pytest.raises(ValueError, match="65536"):
        store.append(make("too-big", payload=exactly(es.MAX_PAYLOAD_BYTES + 1)))
    assert store.count() == 1


def test_the_payload_limit_counts_bytes_not_characters_and_not_escapes(es, open_store, make):
    store = open_store()
    assert store.append(make("accents", payload={"a": "é" * 30_000}))            # 60 000 bytes as UTF-8, 180 000 if every é were written as é
    with pytest.raises(ValueError, match="65536"):
        store.append(make("too-many-bytes", payload={"a": "é" * 33_000}))        # 66 000 bytes although only 33 000 characters
    assert store.list_for_entity("customer-A")[0].payload == {"a": "é" * 30_000}


def test_nested_payloads_roundtrip(es, open_store, make):
    store = open_store()
    payload = {"user": {"name": "O'Brien", "roles": ["a", "b"]}, "n": None, "ok": True, "x": 1.5}
    store.append(make(payload=payload))
    assert store.list_for_entity("customer-A")[0].payload == payload


def test_list_for_entity_validates_the_entity_before_it_queries(es, open_store):
    store = open_store()
    for bad in ("", "bad\nid", "x" * 129, None):
        with pytest.raises(ValueError):
            store.list_for_entity(bad)


def test_the_cursor_is_a_strict_pair_and_its_time_may_use_any_offset(es, open_store, make):
    store = open_store()
    for i, eid in enumerate(("a", "b", "c")):
        store.append(make(eid, when=T0 + timedelta(minutes=i)))
    ist = timezone(timedelta(hours=5, minutes=30))
    cursor = ((T0 + timedelta(minutes=1)).astimezone(ist).isoformat(), "b")      # the position of b, written in another time zone
    assert [e.event_id for e in store.list_for_entity("customer-A", after=cursor)] == ["c"]
    for bad in (("2026-10-14T12:00:00+00:00",), ("2026-10-14T12:00:00+00:00", "a", "b"), ["2026-10-14T12:00:00+00:00", "a"], ("2026-10-14T12:00:00+00:00", ""), ("2026-10-14T12:00:00+00:00", 5)):
        with pytest.raises(ValueError):
            store.list_for_entity("customer-A", after=bad)


def test_pages_cover_every_event_exactly_once_even_with_equal_times(es, open_store, make):
    store = open_store()
    ids = [f"e{i:02d}" for i in range(25)]
    store.append_many(make(eid, when=T0) for eid in reversed(ids))               # all at the same instant: the id breaks the tie
    seen, cursor = [], None
    while True:
        page = store.list_for_entity("customer-A", limit=7, after=cursor)
        if not page:
            break
        seen += [e.event_id for e in page]
        cursor = (page[-1].occurred_at.isoformat(), page[-1].event_id)
    assert seen == ids


def test_a_page_is_one_statement(es, open_store, make, trace):
    store = open_store()
    store.append_many(make(f"e{i}", when=T0) for i in range(10))
    log = trace(store._db)
    store.list_for_entity("customer-A", limit=5)
    assert len(log.matching("SELECT")) == 1 and log.matching("BEGIN") == []


def test_a_retry_with_the_same_content_in_a_different_time_zone_is_still_a_retry(es, open_store, make):
    store = open_store()
    assert store.append(make(when=T0))
    assert store.append(make(when=T0.astimezone(timezone(timedelta(hours=9))))) is False
    assert store.count() == 1


def test_a_conflict_on_any_single_field_is_detected(es, open_store, make):
    store = open_store()
    store.append(make("e", entity="A", kind="created", when=T0, payload={"v": 1}))
    for changed in (dict(entity="B"), dict(kind="updated"), dict(when=T0 + timedelta(seconds=1)), dict(payload={"v": 2}), dict(payload={"v": 1, "w": 2})):
        with pytest.raises(es.IdempotencyConflict):
            store.append(make("e", **{**dict(entity="A", kind="created", when=T0, payload={"v": 1}), **changed}))
    assert store.count() == 1


def test_a_store_on_disk_survives_a_second_connection_reading_while_it_writes(es, open_store, make, tmp_path):
    path = tmp_path / "events.db"
    writer = open_store(path)
    reader = open_store(path)
    writer.append(make("a", when=T0))
    assert [e.event_id for e in reader.list_for_entity("customer-A")] == ["a"]
    assert reader.count() == 1


def test_the_smallest_and_largest_page_are_accepted(es, open_store, make):
    store = open_store()
    store.append_many(make(f"e{i:03d}", when=T0 + timedelta(seconds=i)) for i in range(120))
    assert len(store.list_for_entity("customer-A", limit=1)) == 1
    assert len(store.list_for_entity("customer-A", limit=100)) == 100
    assert len(store.search(limit=1)) == 1 and len(store.search(limit=100)) == 100


def test_the_order_of_a_page_is_in_the_query_not_in_the_index(es, open_store, make):
    store = open_store()
    ids = [f"e{i:02d}" for i in range(12)]
    store.append_many(make(eid, when=T0) for eid in reversed(ids))              # same instant, inserted in the opposite order of their ids
    store._db.execute("DROP INDEX events_entity_order")                          # without the index SQLite sorts by what the query says and by nothing else
    assert [e.event_id for e in store.list_for_entity("customer-A", limit=5)] == ids[:5]
    cursor = (T0.isoformat(), ids[4])
    assert [e.event_id for e in store.list_for_entity("customer-A", limit=5, after=cursor)] == ids[5:10]
