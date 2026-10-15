"""Step 8 - search(): user input is data. Every value is bound; the only text in the statement is chosen by the code."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest


# ten events: (event_id, entity, type, minutes after T0, payload)
T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


ROWS = [
    ("e01", "alpha", "created", 0, {"note": "Disk 100% full"}),
    ("e02", "alpha", "updated", 1, {"note": "user_name changed"}),
    ("e03", "beta", "created", 2, {"note": "O'Brien logged in"}),
    ("e04", "beta", "deleted", 3, {"note": "plain text"}),
    ("e05", "alpha", "updated", 3, {"note": "userXname is different"}),
    ("e06", "gamma", "created", 4, {"note": "DISK almost full"}),
    ("e07", "gamma", "updated", 5, {"note": "nothing here"}),
    ("e08", "alpha", "deleted", 6, {"note": "back to normal"}),
    ("e09", "beta", "updated", 7, {"note": "100 percent sure"}),
    ("e10", "alpha", "created", 8, {"note": "last one"}),
]


@pytest.fixture
def fill(es, open_store, make):
    """fill() -> a store holding the ten events above. A function, so that your code runs inside the test (a step not written yet is a failed check, not a set-up error)."""

    def build():
        store = open_store()
        store.append_many(make(eid, entity, kind, T0 + timedelta(minutes=m), payload) for eid, entity, kind, m, payload in ROWS)
        return store

    return build


def ids(events):
    return [e.event_id for e in events]


def test_without_filters_everything_comes_back_in_time_order_with_ties_by_id(fill):
    filled = fill()
    assert ids(filled.search()) == ["e01", "e02", "e03", "e04", "e05", "e06", "e07", "e08", "e09", "e10"]


def test_entity_and_type_filters_are_exact_and_combine_with_and(fill):
    filled = fill()
    assert ids(filled.search(entity_id="alpha")) == ["e01", "e02", "e05", "e08", "e10"]
    assert ids(filled.search(event_type="updated")) == ["e02", "e05", "e07", "e09"]
    assert ids(filled.search(entity_id="alpha", event_type="updated")) == ["e02", "e05"]
    assert filled.search(entity_id="ALPHA") == []
    assert filled.search(event_type="UPDATED") == []


def test_since_is_inclusive_and_until_is_exclusive(fill):
    filled = fill()
    assert ids(filled.search(since=T0 + timedelta(minutes=3), until=T0 + timedelta(minutes=6))) == ["e04", "e05", "e06", "e07"]
    assert ids(filled.search(until=T0 + timedelta(minutes=1))) == ["e01"]


def test_times_may_be_text_with_an_offset_or_in_another_time_zone(fill):
    filled = fill()
    offset = timezone(timedelta(hours=5, minutes=30))
    assert ids(filled.search(since=(T0 + timedelta(minutes=8)).astimezone(offset))) == ["e10"]
    assert ids(filled.search(since="2026-10-14T17:38:00+05:30")) == ["e10"]       # 12:08 UTC


@pytest.mark.parametrize("bad", [datetime(2026, 10, 14, 12, 0), "2026-10-14T12:00:00", "not a time", 5])
def test_a_time_without_an_offset_or_not_a_time_is_refused(fill, bad):
    filled = fill()
    with pytest.raises(ValueError):
        filled.search(since=bad)
    with pytest.raises(ValueError):
        filled.search(until=bad)


def test_text_matches_the_payload_ignoring_ascii_case(fill):
    filled = fill()
    assert ids(filled.search(text="disk")) == ["e01", "e06"]
    assert ids(filled.search(text="O'BRIEN")) == ["e03"]


def test_percent_underscore_and_backslash_in_the_text_are_ordinary_characters(fill):
    filled = fill()
    assert ids(filled.search(text="100%")) == ["e01"]              # not "100 percent sure": % is not a wildcard
    assert ids(filled.search(text="%")) == ["e01"]
    assert ids(filled.search(text="user_name")) == ["e02"]        # not "userXname": _ is not a wildcard
    assert ids(filled.search(text="_")) == ["e02"]
    assert filled.search(text="\\") == []
    assert ids(filled.search(text="\\", entity_id="nobody")) == []


def test_the_like_pattern_helper(es):
    assert es._like_pattern("plain") == "%plain%"
    assert es._like_pattern("a%b_c") == "%a\\%b\\_c%"
    assert es._like_pattern("back\\slash") == "%back\\\\slash%"
    assert es._like_pattern("") == "%%"


@pytest.mark.parametrize("bad", ["", "x" * 201, 5, b"disk"])
def test_text_must_be_a_string_of_reasonable_length(fill, bad):
    filled = fill()
    with pytest.raises(ValueError):
        filled.search(text=bad)


def test_the_longest_allowed_text_is_accepted(es, fill):
    filled = fill()
    assert filled.search(text="x" * es.MAX_SEARCH_TEXT) == []


@pytest.mark.parametrize("key", ["time", "entity", "type"])
@pytest.mark.parametrize("descending", [False, True])
def test_ordering_by_each_allowed_key_breaks_ties_by_id_in_the_same_direction(fill, key, descending):
    filled = fill()
    column = {"time": 3, "entity": 1, "type": 2}[key]
    expected = sorted(ROWS, key=lambda r: (r[column], r[0]), reverse=descending)
    assert ids(filled.search(order_by=key, descending=descending)) == [r[0] for r in expected]


@pytest.mark.parametrize("bad", ["occurred_at", "id", "time; DROP TABLE events", "TIME", "", "time DESC", "1", "(SELECT 1)"])
def test_other_orderings_are_refused_and_the_table_survives(fill, bad):
    filled = fill()
    with pytest.raises(ValueError):
        filled.search(order_by=bad)
    assert filled.count() == 10


@pytest.mark.parametrize("bad", [0, 101, -1, True, 1.0, "5", None])
def test_the_limit_is_a_strict_int_from_1_to_100(fill, bad):
    filled = fill()
    with pytest.raises(ValueError):
        filled.search(limit=bad)


def test_the_limit_is_applied_after_ordering(fill):
    filled = fill()
    assert ids(filled.search(limit=3)) == ["e01", "e02", "e03"]
    assert ids(filled.search(limit=3, descending=True)) == ["e10", "e09", "e08"]


INJECTIONS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "x'; DROP TABLE events; --",
    "x' UNION SELECT event_id, entity_id, event_type, occurred_at, payload_json FROM events --",
    "%' OR 1=1 --",
    "\" OR \"\"=\"",
    "'; ATTACH DATABASE '/tmp/evil.db' AS evil; --",
    "alpha' AND (SELECT count(*) FROM events) > 0 --",
    "1; PRAGMA user_version = 99",
    "\\' OR 1=1 --",
]


@pytest.mark.parametrize("payload", INJECTIONS)
@pytest.mark.parametrize("field", ["entity_id", "event_type", "text"])
def test_injection_attempts_are_matched_as_plain_data_and_find_nothing(fill, es, payload, field):
    filled = fill()
    assert filled.search(**{field: payload}) == []            # no row has such an entity, type or text; nothing leaks and nothing raises
    assert filled.count() == 10
    assert filled._db.execute("SELECT count(*) FROM sqlite_master WHERE name = 'events'").fetchone()[0] == 1
    assert es.schema_version(filled._db) == 3                 # "PRAGMA user_version = 99" was not executed


def test_an_injection_string_that_was_stored_is_found_as_data(es, open_store, make):
    store = open_store()
    weird = "x'; DROP TABLE events; --"
    store.append(make("evil", entity=weird, kind="created", when=T0, payload={"note": weird}))
    assert ids(store.search(entity_id=weird)) == ["evil"]
    assert ids(store.search(text="DROP TABLE")) == ["evil"]
    assert store.count() == 1


def test_a_control_character_in_a_filter_is_refused(fill):
    filled = fill()
    for field in ("entity_id", "event_type"):
        with pytest.raises(ValueError):
            filled.search(**{field: "bad\nvalue"})


def test_search_is_read_only(fill):
    filled = fill()
    before = filled._db.total_changes
    filled.search(text="disk", order_by="type", descending=True)
    assert filled._db.total_changes == before and not filled._db.in_transaction


def test_count_by_type_is_alphabetical_and_can_start_late(fill):
    filled = fill()
    assert filled.count_by_type() == {"created": 4, "deleted": 2, "updated": 4}
    assert list(filled.count_by_type()) == ["created", "deleted", "updated"]
    assert filled.count_by_type(since=T0 + timedelta(minutes=5)) == {"created": 1, "deleted": 1, "updated": 2}
    assert filled.count_by_type(since="2030-01-01T00:00:00+00:00") == {}


def test_count_by_type_refuses_a_naive_time(fill):
    filled = fill()
    with pytest.raises(ValueError):
        filled.count_by_type(since=datetime(2026, 10, 14))
