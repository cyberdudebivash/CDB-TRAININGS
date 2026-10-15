"""Published checks for the PY-M08 independent lab (casestore). They show the shape of the task; the instructors' suite checks much more (concurrency, rollback, the
migration of the first release's file, injection, query cost). Passing these ten is necessary, not sufficient."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_a_new_case_starts_open_at_version_1_and_a_known_ref_makes_opening_idempotent(cs, open_store):
    store = open_store()
    case = store.open_case("Phishing wave", "alice", 3, ref="T-1")
    assert (case.status, case.version, case.severity, case.comment_count) == ("open", 1, 3, 0)
    assert case.created_at == case.updated_at == T0 and case.created_at.utcoffset() == timedelta(0)
    assert store.open_case("Phishing wave", "alice", 3, ref="T-1") == case                 # a retry: the same case, nothing new
    with pytest.raises(cs.RefConflict):
        store.open_case("Another title", "alice", 3, ref="T-1")
    assert store.get(case.id) == case


def test_an_unknown_case_is_reported_with_the_right_error(cs, open_store):
    store = open_store()
    with pytest.raises(cs.CaseNotFound):
        store.get(404)
    with pytest.raises(cs.CaseNotFound):
        store.add_comment(404, "bob", "hello")
    with pytest.raises(cs.CaseNotFound):
        store.update_case(404, expected_version=1, title="x")


def test_an_edit_with_a_stale_version_is_refused_and_changes_nothing(cs, open_store, clock):
    store = open_store()
    case = store.open_case("Original", "alice")
    clock.advance(minutes=5)
    edited = store.update_case(case.id, expected_version=1, title="Edited")
    assert (edited.title, edited.version, edited.updated_at) == ("Edited", 2, T0 + timedelta(minutes=5))
    with pytest.raises(cs.StaleVersion) as raised:
        store.update_case(case.id, expected_version=1, severity=4)
    assert raised.value.current == 2
    assert store.get(case.id) == edited


def test_closing_and_reopening_follow_the_same_rules(cs, open_store):
    store = open_store()
    case = store.open_case("Case", "alice")
    closed = store.close_case(case.id, expected_version=1)
    assert (closed.status, closed.version) == ("closed", 2)
    with pytest.raises(cs.InvalidTransition):
        store.close_case(case.id, expected_version=2)
    with pytest.raises(cs.StaleVersion):
        store.reopen_case(case.id, expected_version=1)
    assert store.reopen_case(case.id, expected_version=2).status == "open"


def test_deleting_a_case_deletes_its_comments(cs, open_store):
    store = open_store()
    case = store.open_case("Case", "alice")
    store.add_comment(case.id, "bob", "first")
    store.delete_case(case.id, expected_version=1)
    assert store._db.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 0
    with pytest.raises(cs.CaseNotFound):
        store.get(case.id)


def test_comments_are_paged_and_counted(cs, open_store):
    store = open_store()
    case = store.open_case("Case", "alice")
    other = store.open_case("Other", "alice")
    made = [store.add_comment(case.id, "bob", f"comment {i}") for i in range(5)]
    assert [c.text for c in store.comments(case.id, limit=2)] == ["comment 0", "comment 1"]
    assert [c.text for c in store.comments(case.id, after_id=made[1].id, limit=10)] == ["comment 2", "comment 3", "comment 4"]
    assert store.comments(other.id) == []
    assert {c.id: c.comment_count for c in store.find()} == {case.id: 5, other.id: 0}


def test_find_combines_filters_and_treats_hostile_text_as_data(cs, open_store):
    store = open_store()
    a = store.open_case("Disk 100% full", "alice", 4)
    store.open_case("Login problem", "bob", 1)
    c = store.open_case("Disk almost full", "alice", 2)
    store.add_comment(c.id, "bob", "see the rotate_logs job")
    assert [x.id for x in store.find(reporter="alice")] == [a.id, c.id]
    assert [x.id for x in store.find(reporter="alice", min_severity=3)] == [a.id]
    assert [x.id for x in store.find(text="100%")] == [a.id]                                 # % is not a wildcard
    assert [x.id for x in store.find(text="rotate_logs")] == [c.id]                          # found in a comment
    for hostile in ("' OR '1'='1", "x'; DROP TABLE cases; --", "%' OR 1=1 --"):
        assert store.find(reporter=hostile) == [] and store.find(text=hostile) == []
    assert len(store.find()) == 3


def test_stats_have_a_fixed_shape(cs, open_store):
    store = open_store()
    first = store.open_case("One", "alice", 1)
    store.open_case("Two", "alice", 3)
    store.add_comment(first.id, "bob", "x")
    store.close_case(first.id, expected_version=1)
    assert store.stats() == {"open": 1, "closed": 1, "comments": 1, "by_severity": {1: 1, 2: 0, 3: 1, 4: 0}}


def test_an_import_is_idempotent_and_all_or_nothing(cs, open_store):
    store = open_store()
    rows = [{"ref": "A", "title": "One", "reporter": "alice"}, {"ref": "B", "title": "Two", "reporter": "bob", "severity": 4}]
    assert store.import_cases(rows) == cs.ImportReport(2, 0, 0)
    assert store.import_cases(rows) == cs.ImportReport(0, 0, 2)
    changed = [{"ref": "A", "title": "One (edited)", "reporter": "alice"}, {"ref": "C", "title": "Three", "reporter": "carol"}]
    assert store.import_cases(changed) == cs.ImportReport(1, 1, 0)
    with pytest.raises(cs.ImportRejected) as raised:
        store.import_cases([{"ref": "D", "title": "Four", "reporter": "dave"}, {"ref": "E", "title": "", "reporter": "eve"}])
    assert raised.value.index == 1
    assert [c.ref for c in store.find()] == ["A", "B", "C"]                                  # "D" was not kept


def test_the_database_of_the_first_release_is_upgraded_in_place(cs, open_store, first_release_file):
    path = first_release_file(
        cases=[(1, "Old case", "alice", 2, "open", "2026-01-02T03:04:05.000000+00:00")],
        comments=[(1, 1, "bob", "kept", "2026-01-02T03:04:06.000000+00:00"), (2, 99, "eve", "orphan", "2026-01-02T03:04:07.000000+00:00")],
    )
    store = open_store(path)
    case = store.get(1)
    assert (case.ref, case.version, case.comment_count) == (None, 1, 1) and case.updated_at == case.created_at
    assert [c.text for c in store.comments(1)] == ["kept"] and store.orphans_dropped == 1
    store.delete_case(1, expected_version=1)                                                 # the foreign key with cascade exists now
    assert store._db.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 0
    store.close()
    again = open_store(path)
    assert again.orphans_dropped == 0 and again._db.execute("PRAGMA user_version").fetchone()[0] >= 1
