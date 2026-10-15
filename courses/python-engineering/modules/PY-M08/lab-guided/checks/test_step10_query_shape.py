"""Step 10 - the shape of a query: how many statements run, and whether an index is used."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest



T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fill(es, open_store, make):
    """fill() -> a store holding 60 events. A function, so that your code runs inside the test (a step not written yet is a failed check, not a set-up error)."""

    def build():
        store = open_store()
        store.append_many(make(f"e{i:03d}", f"entity-{i % 5}", ("created", "updated", "deleted")[i % 3], T0 + timedelta(minutes=i), {"note": f"number {i}"}) for i in range(60))
        return store

    return build


def test_explain_returns_the_plan_steps_as_strings(es, fill):
    filled = fill()
    plan = filled.explain("SELECT * FROM events WHERE entity_id = ?", ("entity-1",))
    assert isinstance(plan, list) and plan and all(isinstance(step, str) for step in plan)
    assert any("SEARCH" in step and "events_entity_order" in step for step in plan), plan


def test_a_plain_scan_is_reported_as_a_scan(es, fill):
    filled = fill()
    assert any("SCAN" in step for step in filled.explain("SELECT * FROM events WHERE payload_json LIKE ?", ("%7%",)))


def test_a_function_around_an_indexed_column_defeats_its_index(es, fill):
    filled = fill()
    assert any("SEARCH" in s and "events_type_time" in s for s in filled.explain("SELECT * FROM events WHERE event_type = ?", ("created",)))
    assert any("SCAN" in s for s in filled.explain("SELECT * FROM events WHERE lower(event_type) = ?", ("created",)))


def test_explain_binds_parameters_like_any_statement(es, fill):
    filled = fill()
    hostile = "x'; DROP TABLE events; --"
    assert filled.explain("SELECT * FROM events WHERE entity_id = ?", (hostile,))
    assert filled.count() == 60


def selects(log):
    return log.matching("SELECT")


def test_list_for_entity_is_one_statement_and_uses_the_entity_index(es, fill, trace):
    filled = fill()
    log = trace(filled._db)
    page = filled.list_for_entity("entity-1", limit=5)
    assert len(page) == 5 and len(selects(log)) == 1
    plan = filled.explain(selects(log)[0])
    assert any("events_entity_order" in step for step in plan) and not any("TEMP B-TREE" in step for step in plan), plan


def test_search_by_entity_or_type_is_one_statement_that_uses_an_index(es, fill, trace):
    filled = fill()
    log = trace(filled._db)
    filled.search(entity_id="entity-2", limit=10)
    assert len(selects(log)) == 1
    assert any("events_entity_order" in step for step in filled.explain(selects(log)[0]))
    log.clear()
    filled.search(event_type="updated", limit=10)
    assert len(selects(log)) == 1
    assert any("events_type_time" in step for step in filled.explain(selects(log)[0]))


def test_count_by_type_is_one_statement(es, fill, trace):
    filled = fill()
    log = trace(filled._db)
    assert sum(filled.count_by_type().values()) == 60
    assert len(selects(log)) == 1


def test_a_single_append_is_one_short_transaction(es, fill, make, trace):
    filled = fill()
    log = trace(filled._db)
    assert filled.append(make("fresh", when=T0))
    assert len(log.matching("BEGIN")) == 1 and len(log.matching("COMMIT")) == 1 and log.matching("ROLLBACK") == []
    assert len(log.matching("INSERT")) == 1
    assert log.matching("BEGIN")[0].upper().startswith("BEGIN IMMEDIATE")           # the check for an existing event and the insert happen under one write lock


def test_purge_and_search_do_not_open_transactions_they_do_not_need(es, fill, trace):
    filled = fill()
    log = trace(filled._db)
    filled.search(text="number 7")
    assert log.matching("BEGIN", "COMMIT") == []
