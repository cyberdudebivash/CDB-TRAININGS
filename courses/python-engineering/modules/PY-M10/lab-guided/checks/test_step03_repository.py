"""Step 3 - The repository: parameterised SQL, ownership enforced in the query, and nothing the caller sends ever becomes part of a statement."""
from __future__ import annotations

import sqlite3
import threading

import pytest

NOW = 1_791_979_200


@pytest.fixture
def repo(ta, tmp_path):
    """repo() -> a TicketRepo on a new database file with the table created. A function, so that your code runs inside the test."""

    def build(name="repo.db"):
        r = ta.TicketRepo(str(tmp_path / name))
        r.init()
        return r

    build.path = lambda name="repo.db": str(tmp_path / name)
    return build


def new(ta, repo, who="alice", title="Printer on fire", body="smoke", priority="normal", now=NOW):
    return repo.create(who, ta.TicketIn(title=title, body=body, priority=priority), now)


def rows(path, sql="SELECT * FROM tickets ORDER BY id"):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# ------------------------------------------------------------------------------------------------------------------------------------------- init and create
def test_init_creates_the_table_and_may_be_called_again(ta, repo):
    r = repo()
    r.init()
    r.init()
    assert [row[0] for row in rows(repo.path(), "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tickets'")] == ["tickets"]
    assert [row[0] for row in rows(repo.path(), "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'tickets_requester'")] == ["tickets_requester"]


def test_init_keeps_the_rows_that_are_already_there(ta, repo):
    r = repo()
    new(ta, r)
    r.init()
    assert len(rows(repo.path())) == 1


def test_create_stores_an_open_unassigned_ticket_and_returns_it(ta, repo):
    t = new(ta, repo(), who="alice", title="Printer on fire", body="smoke", priority="high", now=NOW + 5)
    assert isinstance(t, ta.Ticket)
    assert (t.id, t.requester, t.title, t.body, t.priority, t.status, t.assignee, t.created_at, t.updated_at) == (1, "alice", "Printer on fire", "smoke", "high", "open", None, NOW + 5, NOW + 5)


def test_ids_count_up_and_are_never_used_again(ta, repo):
    r = repo()
    ids = [new(ta, r).id for _ in range(3)]
    assert ids == [1, 2, 3]
    assert r.delete(3) is True
    assert new(ta, r).id == 4


def test_create_stores_hostile_text_as_data(ta, repo):
    r = repo()
    t = new(ta, r, title="x'); DROP TABLE tickets;--", body="Robert'); DROP TABLE tickets;--")
    assert r.get(t.id).title == "x'); DROP TABLE tickets;--"
    assert len(rows(repo.path())) == 1


def test_the_database_itself_refuses_values_the_models_would_have_refused(ta, repo):
    repo()
    conn = sqlite3.connect(repo.path())
    try:
        for bad in (
            ("alice", "ab", "x", "low", "open"),
            ("alice", "abc", "", "low", "open"),
            ("alice", "abc", "x", "urgent!", "open"),
            ("alice", "abc", "x", "low", "done"),
            ("alice", None, "x", "low", "open"),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO tickets (requester, title, body, priority, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, 1)", bad)
    finally:
        conn.close()


# ------------------------------------------------------------------------------------------------------------------------------------------- get
def test_get_returns_the_ticket_or_none(ta, repo):
    r = repo()
    t = new(ta, r)
    assert r.get(t.id) == t
    assert r.get(t.id + 1) is None
    assert r.get(0) is None


def test_get_with_a_requester_returns_only_that_requesters_tickets(ta, repo):
    r = repo()
    t = new(ta, r, who="alice")
    assert r.get(t.id, requester="alice") == t
    assert r.get(t.id, requester="bob") is None
    assert r.get(t.id, requester="alic") is None
    assert r.get(t.id, requester="ALICE") is None
    assert r.get(t.id, requester="") is None


def test_get_cannot_be_talked_into_returning_someone_elses_ticket(ta, repo):
    r = repo()
    t = new(ta, r, who="alice")
    for evil in ("bob' OR '1'='1", "' OR 1=1 --", "alice' --", "%", "alice%", "a_ice", "*"):
        assert r.get(t.id, requester=evil) is None


def test_get_takes_the_id_as_a_value(ta, repo):
    r = repo()
    new(ta, r)
    assert r.get("1 OR 1=1") is None                          # text bound as a value cannot be an id; it is not executed
    assert r.get("1; DROP TABLE tickets") is None
    assert len(rows(repo.path())) == 1


# ------------------------------------------------------------------------------------------------------------------------------------------- search
@pytest.fixture
def filled(ta, repo):
    """filled() -> (repo, tickets): eight tickets from three requesters, created one second apart (two share a second)."""

    def build():
        r = repo()
        spec = [
            ("alice", "Printer on fire", "smoke everywhere", "urgent", 0),
            ("alice", "VPN is slow", "100% packet loss on _wifi_", "normal", 1),
            ("bob", "Cannot log in", "password reset loop", "high", 2),
            ("bob", "Disk 100% full", "the C:\\ drive", "low", 3),
            ("carol", "Laptop battery", "swollen battery", "high", 3),
            ("alice", "Mouse broken", "left button", "low", 4),
            ("carol", "O'Brien account", "locked out", "normal", 5),
            ("bob", "Keyboard sticky", "coffee", "normal", 6),
        ]
        return r, [new(ta, r, who, title, body, priority, NOW + dt) for who, title, body, priority, dt in spec]

    build.path = repo.path
    return build


def ids(tickets):
    return [t.id for t in tickets]


def test_search_with_no_filter_returns_everything_newest_first_with_ties_by_id(filled):
    r, tickets = filled()
    page, total = r.search()
    assert total == 8 and ids(page) == [8, 7, 6, 5, 4, 3, 2, 1]


@pytest.mark.parametrize(
    "sort, order, expected",
    [
        ("created", "desc", [8, 7, 6, 5, 4, 3, 2, 1]),
        ("created", "asc", [1, 2, 3, 4, 5, 6, 7, 8]),
        ("id", "desc", [8, 7, 6, 5, 4, 3, 2, 1]),
        ("id", "asc", [1, 2, 3, 4, 5, 6, 7, 8]),
    ],
)
def test_search_orders_by_the_requested_column_and_direction_with_ties_by_id_in_the_same_direction(filled, sort, order, expected):
    r, _ = filled()
    assert ids(r.search(sort=sort, order=order)[0]) == expected


def test_search_can_sort_by_the_time_of_the_last_change(ta, filled):
    r, tickets = filled()
    r.update(2, {"status": "pending"}, NOW + 100)
    r.update(7, {"status": "pending"}, NOW + 50)
    assert ids(r.search(sort="updated", order="desc")[0])[:2] == [2, 7]
    assert ids(r.search(sort="updated", order="asc")[0])[-2:] == [7, 2]


def test_search_pages_are_consistent_and_total_counts_every_match(filled):
    r, _ = filled()
    seen = []
    for offset in range(0, 9, 3):
        page, total = r.search(limit=3, offset=offset)
        assert total == 8
        seen += ids(page)
    assert seen == [8, 7, 6, 5, 4, 3, 2, 1]
    assert r.search(limit=3, offset=6)[0] and len(r.search(limit=3, offset=6)[0]) == 2
    assert r.search(limit=3, offset=100) == ([], 8)
    assert len(r.search(limit=1)[0]) == 1


def test_search_filters_combine_with_and(filled):
    r, _ = filled()
    assert ids(r.search(requester="alice")[0]) == [6, 2, 1]
    assert ids(r.search(priority="high")[0]) == [5, 3]
    assert ids(r.search(status="open")[0]) == [8, 7, 6, 5, 4, 3, 2, 1]
    assert ids(r.search(requester="bob", priority="high")[0]) == [3]
    assert r.search(requester="alice", priority="high") == ([], 0)
    r.update(1, {"status": "closed"}, NOW + 9)
    assert ids(r.search(status="closed")[0]) == [1]
    assert r.search(requester="alice", status="closed")[1] == 1
    assert r.search(requester="bob", status="closed") == ([], 0)


def test_search_total_follows_the_filters_not_the_page(filled):
    r, _ = filled()
    page, total = r.search(requester="alice", limit=1)
    assert len(page) == 1 and total == 3


@pytest.mark.parametrize("q, expected", [("printer", [1]), ("PRINTER", [1]), ("smoke", [1]), ("battery", [5]), ("coffee", [8]), ("log in", [3]), ("'", [7]), ("zzz", []), ("Brien", [7])])
def test_q_matches_a_substring_of_the_title_or_the_body_ignoring_ascii_case(filled, q, expected):
    r, _ = filled()
    assert ids(r.search(q=q)[0]) == expected


@pytest.mark.parametrize("q, expected", [("100%", [4, 2]), ("%", [4, 2]), ("_wifi_", [2]), ("_", [2]), ("C:\\", [4]), ("\\", [4]), ("a_", [])])
def test_the_wildcards_of_like_are_literal_characters_in_q(filled, q, expected):
    r, _ = filled()
    assert ids(r.search(q=q)[0]) == expected


@pytest.mark.parametrize("evil", ["' OR '1'='1", "'; DROP TABLE tickets;--", "%' OR '%'='", "\" OR \"\"=\"", "x' UNION SELECT 1,2,3,4,5,6,7,8,9--", "\\' OR 1=1--", "1; DELETE FROM tickets"])
def test_q_is_a_value_and_never_changes_the_statement(filled, evil):
    r, _ = filled()
    page, total = r.search(q=evil)
    assert page == [] and total == 0
    assert len(rows(filled.path())) == 8


def test_q_finds_hostile_text_that_is_stored_and_nothing_else(ta, repo):
    r = repo()
    new(ta, r, title="x'); DROP TABLE tickets;--")
    new(ta, r, title="harmless")
    assert ids(r.search(q="DROP TABLE")[0]) == [1]
    assert ids(r.search(q="'); DROP")[0]) == [1]


@pytest.mark.parametrize("evil", ["'", "' OR '1'='1", "alice' --", "%", "alice%", "*"])
def test_the_other_filters_are_values_too(filled, evil):
    r, _ = filled()
    for kw in ({"requester": evil}, {"status": evil}, {"priority": evil}):
        assert r.search(**kw) == ([], 0)


@pytest.mark.parametrize("sort, order", [("title", "asc"), ("created_at", "desc"), ("id; DROP TABLE tickets", "asc"), ("created", "up"), ("created", "ASC"), ("", "asc"), ("created", ""), ("id", "asc; DROP TABLE tickets"), (None, "asc"), ("created", None), ("id) --", "desc")])
def test_a_sort_or_order_outside_the_fixed_tables_is_a_value_error_and_reaches_no_statement(filled, sort, order):
    r, _ = filled()
    with pytest.raises(ValueError):
        r.search(sort=sort, order=order)
    assert len(rows(filled.path())) == 8


# ------------------------------------------------------------------------------------------------------------------------------------------- update
def test_update_changes_the_given_columns_and_the_time_and_returns_the_ticket(ta, repo):
    r = repo()
    t = new(ta, r, now=NOW)
    u = r.update(t.id, {"title": "New title", "priority": "urgent", "status": "pending", "assignee": "sam", "body": "new body"}, NOW + 60)
    assert (u.id, u.requester, u.title, u.body, u.priority, u.status, u.assignee, u.created_at, u.updated_at) == (t.id, "alice", "New title", "new body", "urgent", "pending", "sam", NOW, NOW + 60)
    assert r.get(t.id) == u


def test_update_leaves_the_other_columns_and_the_other_tickets_alone(ta, repo):
    r = repo()
    a, b = new(ta, r), new(ta, r, who="bob")
    r.update(a.id, {"status": "pending"}, NOW + 1)
    assert r.get(b.id) == b
    after = r.get(a.id)
    assert (after.title, after.body, after.priority, after.assignee, after.requester) == (a.title, a.body, a.priority, a.assignee, a.requester)


def test_update_can_clear_the_assignee(ta, repo):
    r = repo()
    t = new(ta, r)
    r.update(t.id, {"assignee": "sam"}, NOW + 1)
    assert r.update(t.id, {"assignee": None}, NOW + 2).assignee is None


def test_update_returns_none_when_no_ticket_has_that_id(ta, repo):
    r = repo()
    assert r.update(99, {"status": "pending"}, NOW) is None


def test_update_with_only_status_changes_the_ticket_only_if_it_still_has_that_status(ta, repo):
    r = repo()
    t = new(ta, r)
    assert r.update(t.id, {"title": "Second try"}, NOW + 1, only_status="closed") is None
    assert r.get(t.id).title == t.title and r.get(t.id).updated_at == NOW
    assert r.update(t.id, {"title": "Second try"}, NOW + 1, only_status="open").title == "Second try"
    r.update(t.id, {"status": "pending"}, NOW + 2)
    assert r.update(t.id, {"title": "Third"}, NOW + 3, only_status="open") is None


@pytest.mark.parametrize("changes", [{}, {"requester": "bob"}, {"id": 5}, {"created_at": 1}, {"updated_at": 1}, {"status; DROP TABLE tickets": "x"}, {"title": "x", "role": "admin"}, {"title = 'x', requester": "bob"}, {"": 1}])
def test_update_refuses_an_empty_change_or_a_column_that_is_not_updatable(ta, repo, changes):
    r = repo()
    t = new(ta, r)
    with pytest.raises(ValueError):
        r.update(t.id, changes, NOW + 1)
    assert r.get(t.id) == t and len(rows(repo.path())) == 1


def test_update_takes_values_as_values(ta, repo):
    r = repo()
    t = new(ta, r)
    u = r.update(t.id, {"title": "x', requester = 'bob"}, NOW + 1)
    assert u.title == "x', requester = 'bob" and u.requester == "alice"


def test_update_does_not_let_a_value_leave_the_database_rules(ta, repo):
    r = repo()
    t = new(ta, r)
    with pytest.raises(sqlite3.IntegrityError):
        r.update(t.id, {"status": "done"}, NOW + 1)
    assert r.get(t.id).status == "open"


# ------------------------------------------------------------------------------------------------------------------------------------------- delete
def test_delete_removes_the_ticket_and_says_whether_it_did(ta, repo):
    r = repo()
    t = new(ta, r)
    other = new(ta, r, who="bob")
    assert r.delete(t.id) is True
    assert r.get(t.id) is None and r.get(other.id) == other
    assert r.delete(t.id) is False
    assert r.delete(0) is False


# ------------------------------------------------------------------------------------------------------------------------------------------- connections
def test_every_method_closes_the_connection_it_opened(ta, repo, monkeypatch):
    r = repo()
    opened = []
    real = sqlite3.connect

    def spy(*args, **kwargs):
        conn = real(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", spy)
    t = new(ta, r)
    r.get(t.id)
    r.get(t.id, requester="alice")
    r.search()
    r.search(q="x", requester="alice", status="open", priority="low")
    r.update(t.id, {"status": "pending"}, NOW + 1)
    r.update(t.id, {"status": "pending"}, NOW + 1, only_status="closed")
    r.delete(t.id)
    r.init()
    assert len(opened) >= 8
    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


def test_a_failed_call_still_closes_its_connection(ta, repo, monkeypatch):
    r = repo()
    opened = []
    real = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: opened.append(real(*a, **k)) or opened[-1])
    with pytest.raises(ValueError):
        r.search(sort="nope")
    with pytest.raises(sqlite3.IntegrityError):
        t = new(ta, r)
        r.update(t.id, {"status": "done"}, NOW)
    assert opened and all(_closed(c) for c in opened)


def _closed(conn):
    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        return True
    return False


def test_a_write_that_fails_leaves_no_half_written_row(ta, repo):
    r = repo()
    t = new(ta, r)
    with pytest.raises(sqlite3.IntegrityError):
        r.update(t.id, {"title": "fine title", "status": "done"}, NOW + 5)
    after = r.get(t.id)
    assert after.title == t.title and after.updated_at == NOW


def test_many_threads_can_use_one_repository_at_once(ta, repo):
    r = repo()
    errors = []

    def worker(n):
        try:
            for i in range(10):
                new(ta, r, who=f"user{n}", title=f"ticket {n}-{i}")
                r.search(requester=f"user{n}")
        except Exception as exc:                                      # noqa: BLE001 - collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert errors == []
    assert r.search(limit=100)[1] == 80
    assert sorted(ids(r.search(limit=100)[0])) == list(range(1, 81))


def test_the_repository_remembers_nothing_between_calls(ta, repo):
    r = repo()
    t = new(ta, r)
    other = ta.TicketRepo(repo.path())                                # a second instance on the same file sees the same rows
    assert other.get(t.id) == t
