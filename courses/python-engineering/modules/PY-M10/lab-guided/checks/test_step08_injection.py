"""Step 8 - The injection and abuse suite. A corpus of hostile input is thrown at every place a client can put data (body, query, path, headers, token), and four things must hold:
nothing answers 5xx, nothing leaks a database or Python error, no statement changes (the table and its rows are intact), and nobody sees a ticket that is not theirs.

The suite is yours to keep: when you add a field or a parameter, add it here first."""
from __future__ import annotations

import json
import re
import sqlite3

import pytest
from lab_support import SharedApi

SQLI = [
    "'", "''", "\"", "\\", "';", "' OR '1'='1", "' OR 1=1--", "' OR 1=1#", "\" OR \"\"=\"", "') OR ('1'='1", "admin'--", "1; DROP TABLE tickets;--", "'; DROP TABLE tickets;--",
    "'); DROP TABLE tickets;--", "x'; DELETE FROM tickets WHERE '1'='1", "' UNION SELECT 1,2,3,4,5,6,7,8,9--", "' UNION ALL SELECT NULL,NULL,NULL--", "1 AND SLEEP(5)", "'; SELECT pg_sleep(5);--",
    "' AND (SELECT COUNT(*) FROM sqlite_master) > 0--", "' || (SELECT sql FROM sqlite_master LIMIT 1) || '", "%27%20OR%20%271%27%3D%271", "\\'; DROP TABLE tickets;--", "`; DROP TABLE tickets;--",
    "/*!50000 OR 1=1*/", "'/**/OR/**/1=1--", "0x27204f52202731273d2731", "char(39)||char(79)||char(82)", "ʼ OR 1=1--", "＇ OR 1=1--", "%", "%%", "_", "\\%", "\\_", "[a-z]", "*", "?",
]
OTHER = [
    "<script>alert(1)</script>", "\"><img src=x onerror=alert(1)>", "javascript:alert(1)", "{{7*7}}", "${7*7}", "{%raw%}", "$(id)", "`id`", "; id", "| id", "&& id", "../../../../etc/passwd", "..\\..\\windows\\win.ini",
    "file:///etc/passwd", "http://169.254.169.254/latest/meta-data/", "%2e%2e%2f%2e%2e%2f", "%00", "\x00", "a\x00b", "line1\r\nSet-Cookie: pwn=1", "\r\nX-Injected: 1", "%0d%0aX-Injected:%201", "‮", "​​​",
    "A" * 1000, "\U0001f600" * 50, "null", "true", "[]", "{}", "NaN", "-0", "1e999", "9" * 400,
]
CORPUS = SQLI + OTHER
CANARY = "CANARY-TOP-SECRET-alice-7731"
BANNED = ("sqlite", "syntax error", "operationalerror", "integrityerror", "programmingerror", "traceback", "sqlalchemy", "no such table", "no such column", "unrecognized token", ".py\"", "pydantic", "fastapi", "starlette", "jwt.")


def pid(value):
    return f"p{CORPUS.index(value):02d}" if value in CORPUS else "x"


def count_rows(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    finally:
        conn.close()


def schema_of(path):
    conn = sqlite3.connect(path)
    try:
        return sorted(conn.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall())
    finally:
        conn.close()


def assert_clean(response):
    """Not a 5xx; no injected header; and an ERROR answer (4xx) names no database, framework or file. (A 2xx answer may legitimately echo the stored text, which is data.)"""
    assert response.status_code < 500, (response.status_code, response.text[:200])
    if response.status_code >= 400:
        text = response.text.lower()
        for word in BANNED:
            assert word.lower() not in text, (word, response.text[:300])
    names = {k.lower() for k in response.headers}
    assert "x-injected" not in names and "set-cookie" not in names


def prepare(api):
    api.alice_ticket = api.new_ticket("alice", title=CANARY, body="only alice may read this " + CANARY)
    for i in range(3):
        api.new_ticket("bob", title=f"bob ticket {i}")
    api.baseline_schema = schema_of(api.settings.db_path)
    api.baseline_rows = count_rows(api.settings.db_path)


@pytest.fixture(scope="module")
def world(ta, shared_tmp):
    """world.<anything> -> an API with alice's secret ticket (the canary, world.alice_ticket) and three of bob's. Built once for this file, on first use."""
    return SharedApi(ta, shared_tmp, prepare)


def intact(world):
    assert schema_of(world.settings.db_path) == world.baseline_schema
    assert count_rows(world.settings.db_path) >= world.baseline_rows


# ------------------------------------------------------------------------------------------------------------------------------------------- body fields
@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_title_or_body_is_stored_as_text_or_refused_and_nothing_else_happens(world, payload):
    for field in ("title", "body"):
        body = {"title": "A fine title", "body": "A fine body"}
        body[field] = payload if field == "body" else "ok " + payload
        r = world.post("/tickets", json=body, headers=world.as_("bob"))
        assert_clean(r)
        assert r.status_code in (201, 422)
        if r.status_code == 201:
            stored = world.get(r.headers["location"], headers=world.as_("bob")).json()
            assert stored[field] == body[field].strip() and stored["requester"] == "bob"
    intact(world)


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_value_in_a_fixed_choice_field_is_a_422(world, payload):
    for field in ("priority",):
        r = world.post("/tickets", json={"title": "A fine title", "body": "x", field: payload}, headers=world.as_("bob"))
        assert_clean(r)
        assert r.status_code == 422
    t = world.new_ticket("bob")
    for field in ("priority", "status"):
        r = world.patch(f"/tickets/{t['id']}", json={field: payload}, headers=world.as_("sam", "agent"))
        assert_clean(r)
        assert r.status_code == 422
    intact(world)


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_assignee_is_a_422_unless_it_is_a_valid_subject(world, payload):
    t = world.new_ticket("bob")
    r = world.patch(f"/tickets/{t['id']}", json={"assignee": payload}, headers=world.as_("sam", "agent"))
    assert_clean(r)
    assert r.status_code in (200, 422)
    intact(world)


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_field_name_is_refused(world, payload):
    r = world.post("/tickets", json={"title": "A fine title", "body": "x", payload: "y"}, headers=world.as_("bob"))
    assert_clean(r)
    assert r.status_code == 422
    assert [e["loc"] for e in r.json()["errors"]] == [["body", payload if re.fullmatch(r"[A-Za-z0-9_]{1,40}", payload) else "?"]]          # a name is echoed only when it is a plain identifier
    intact(world)


# ------------------------------------------------------------------------------------------------------------------------------------------- query string
@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_search_text_finds_only_what_it_literally_says_and_never_alices_ticket(world, payload):
    r = world.get("/tickets", params={"q": payload[:50] or "x"}, headers=world.as_("bob"))
    assert_clean(r)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert all(t["requester"] == "bob" for t in r.json()["items"])
        assert r.json()["total"] == len(r.json()["items"]) or r.json()["total"] > 20
    intact(world)


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_value_in_a_filter_or_sort_parameter_is_a_422(world, payload):
    for name in ("status", "priority", "sort", "order", "limit", "offset"):
        r = world.get("/tickets", params={name: payload}, headers=world.as_("bob"))
        assert_clean(r)
        assert r.status_code == (200 if (name, payload) == ("offset", "-0") else 422), (name, r.text[:200])             # "-0" is the number zero
    intact(world)


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_requester_filter_never_widens_what_a_reader_sees(world, payload):
    r = world.get("/tickets", params={"requester": payload}, headers=world.as_("bob"))
    assert_clean(r)
    assert r.status_code in (403, 422)
    r = world.get("/tickets", params={"requester": payload}, headers=world.as_("sam", "agent"))
    assert_clean(r)
    assert r.status_code in (200, 422)
    if r.status_code == 200 and payload != "alice":
        assert CANARY not in r.text
    intact(world)


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_parameter_name_is_refused(world, payload):
    r = world.get("/tickets", params={payload[:30] or "x": "1"}, headers=world.as_("bob"))
    assert_clean(r)
    assert r.status_code == 422
    name = payload[:30] or "x"
    assert [e["loc"] for e in r.json()["errors"]] == [["query", name if re.fullmatch(r"[A-Za-z0-9_]{1,40}", name) else "?"]]
    intact(world)


# ------------------------------------------------------------------------------------------------------------------------------------------- path
@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_path_segment_is_a_404_or_a_422(world, payload):
    from urllib.parse import quote

    seg = quote(payload, safe="")
    for method in ("GET", "PATCH", "DELETE"):
        r = world.request(method, f"/tickets/{seg}", headers=world.as_("root", "admin"), json={"title": "A fine title"} if method == "PATCH" else None)
        assert_clean(r)
        assert r.status_code in (404, 405, 422)
    intact(world)


# ------------------------------------------------------------------------------------------------------------------------------------------- headers and token
def header_safe(payload):
    """What a client library could actually put in a header value: latin-1 text without line breaks."""
    return payload.encode("latin-1", errors="replace").decode("latin-1").replace("\r", "").replace("\n", "")


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_request_id_never_reaches_a_response_header(world, payload):
    value = header_safe(payload)
    r = world.get("/healthz", headers={"x-request-id": value})
    assert r.status_code == 200
    got = r.headers["x-request-id"]
    assert got == value if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value) else re.fullmatch(r"[0-9a-f]{32}", got)
    assert "x-injected" not in {k.lower() for k in r.headers}


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_correctly_signed_token_with_a_hostile_subject_or_role_is_refused(world, payload):
    for claims in (world.claims(role=payload), world.claims(sub=payload, role=payload)):
        r = world.get("/tickets", headers=world.forged(claims))
        assert_clean(r)
        assert r.status_code == 401, (claims, r.status_code)
    r = world.get("/tickets", headers=world.forged(world.claims(sub=payload)))
    assert_clean(r)
    assert r.status_code == (200 if re.fullmatch(r"[A-Za-z0-9_.@-]{1,64}", payload) else 401)             # a subject that is a plain name is just a name
    intact(world)


@pytest.mark.parametrize("payload", CORPUS, ids=pid)
def test_a_hostile_authorization_header_is_a_401(world, payload):
    r = world.get("/tickets", headers={"Authorization": "Bearer " + header_safe(payload)})
    assert_clean(r)
    assert r.status_code == 401


# ------------------------------------------------------------------------------------------------------------------------------------------- second order
@pytest.mark.parametrize("payload", SQLI[:20], ids=lambda p: pid(p))
def test_hostile_text_that_was_stored_earlier_does_no_harm_when_it_is_read_searched_and_edited_later(world, payload):
    t = world.new_ticket("bob", title=("ticket " + payload)[:120], body=payload or "x")
    base = f"/tickets/{t['id']}"
    for r in (
        world.get(base, headers=world.as_("bob")),
        world.get("/tickets", headers=world.as_("bob")),
        world.get("/tickets", params={"q": "x"}, headers=world.as_("sam", "agent")),
        world.patch(base, json={"priority": "high"}, headers=world.as_("bob")),
        world.patch(base, json={"status": "pending"}, headers=world.as_("sam", "agent")),
        world.get("/tickets", params={"status": "pending"}, headers=world.as_("sam", "agent")),
    ):
        assert_clean(r)
        assert r.status_code == 200
    assert world.delete(base, headers=world.as_("root", "admin")).status_code == 204
    intact(world)


def test_stored_hostile_text_is_found_by_its_literal_characters_only(world):
    mark = "zq91x"                                                                  # this file shares one database: look for text that only this test stored
    world.new_ticket("bob", title=f"x'); DROP TABLE tickets;--{mark}", body=f"Robert'); DROP TABLE students;--{mark}")
    assert world.get("/tickets", params={"q": f"'); DROP TABLE tickets;--{mark}"}, headers=world.as_("bob")).json()["total"] == 1
    assert world.get("/tickets", params={"q": f"' OR '1'='1{mark}"}, headers=world.as_("bob")).json()["total"] == 0
    assert world.get("/tickets", params={"q": f"%{mark}"}, headers=world.as_("bob")).json()["total"] == 0
    assert world.get("/tickets", params={"q": f"_{mark}"}, headers=world.as_("bob")).json()["total"] == 0
    intact(world)


# ------------------------------------------------------------------------------------------------------------------------------------------- JSON abuse
RAW_BODIES = [
    b"", b"{", b"}", b"[]", b"null", b"true", b"1", b'"text"', b'{"title": "abc", "body": "x",}', b"{'title': 'abc', 'body': 'x'}", b'{"title": "abc" "body": "x"}',
    b'{"title": "abc", "body": "x"} {"title": "abc", "body": "y"}', b'{"title": NaN, "body": "x"}', b'{"title": Infinity, "body": "x"}', b'{"title": 1e999, "body": "x"}',
    b'{"title": "abc", "body": "x", "priority": ' + b"9" * 4000 + b"}", b"[" * 5000, b'{"a":' * 2000, b'{"title": "ab\\ud800cd", "body": "x"}', b'{"title": "ab\\u0000cd", "body": "x"}',
    b'{"title": "abc", "body": "' + b"\xff\xfe" + b'"}', b"\x00" * 50, b"// comment\n{}", b"/* c */ {}", b'{"title":"abc","body":"x"}\x00', b"<xml/>", b"title=abc&body=x",
]


@pytest.mark.parametrize("raw", RAW_BODIES, ids=lambda b: f"b{RAW_BODIES.index(b):02d}")
def test_a_malformed_or_hostile_json_body_is_a_4xx_and_never_a_500(world, raw):
    before = count_rows(world.settings.db_path)
    for r in (
        world.post("/tickets", content=raw, headers={**world.as_("bob"), "content-type": "application/json"}),
        world.patch(f"/tickets/{world.alice_ticket['id']}", content=raw, headers={**world.as_("alice"), "content-type": "application/json"}),
    ):
        assert_clean(r)
        assert 400 <= r.status_code < 500
    assert count_rows(world.settings.db_path) == before
    intact(world)


def test_odd_but_valid_json_is_read_the_ordinary_way(world):
    h = {**world.as_("bob"), "content-type": "application/json"}
    r = world.post("/tickets", content=b'{"title": "abc", "title": "abd", "body": "x"}', headers=h)
    assert r.status_code == 201 and r.json()["title"] == "abd"                      # the last duplicate wins, as in every JSON reader: the point is that nothing breaks
    r = world.post("/tickets", content="\ufeff".encode("utf-8") + b'{"title": "abc", "body": "x"}', headers=h)
    assert r.status_code in (201, 422)
    r = world.post("/tickets", content=b'{"title": "\\ud83d\\ude00\\ud83d\\ude00\\ud83d\\ude00", "body": "x"}', headers=h)
    assert r.status_code == 201 and r.json()["title"] == "\U0001f600" * 3
    r = world.post("/tickets", content=b'{"title": "ab\\ud800cd", "body": "x"}', headers=h)
    assert r.status_code == 422


def test_the_deepest_json_the_limit_allows_is_still_a_4xx(world):
    h = {**world.as_("bob"), "content-type": "application/json"}
    assert 400 <= world.post("/tickets", content=b"[" * 16_000, headers=h).status_code < 500
    assert 400 <= world.post("/tickets", content=(b'{"a":' * 2000) + b"1" + (b"}" * 2000), headers=h).status_code < 500
    intact(world)


# ------------------------------------------------------------------------------------------------------------------------------------------- ownership under attack
def test_no_query_a_reader_can_build_returns_another_readers_ticket(world):
    h = world.as_("bob")
    attempts = [
        world.get("/tickets", params={"q": "CANARY"}, headers=h),
        world.get("/tickets", params={"q": "TOP-SECRET"}, headers=h),
        world.get("/tickets", params={"q": "%"}, headers=h),
        world.get("/tickets", params={"q": "_"}, headers=h),
        world.get("/tickets", params={"q": "' OR requester='alice"}, headers=h),
        world.get("/tickets", params={"requester": "alice"}, headers=h),
        world.get("/tickets", params={"sort": "id", "order": "asc", "limit": 100}, headers=h),
        world.get("/tickets", params={"limit": 100, "offset": 0, "status": "open"}, headers=h),
        world.get(f"/tickets/{world.alice_ticket['id']}", headers=h),
        world.patch(f"/tickets/{world.alice_ticket['id']}", json={"title": "pwned by bob"}, headers=h),
        world.get("/tickets", params={"owner": "alice"}, headers=h),
        world.get("/tickets", headers={**h, "X-Requester": "alice", "X-Forwarded-User": "alice"}),
    ]
    for r in attempts:
        assert CANARY not in r.text and "only alice may read this" not in r.text, r.request.url
    assert world.get(f"/tickets/{world.alice_ticket['id']}", headers=world.as_("alice")).json()["title"] == CANARY


def test_a_reader_cannot_discover_ticket_ids_by_the_difference_between_403_and_404(world):
    ids = range(1, 12)
    seen = {world.get(f"/tickets/{i}", headers=world.as_("bob")).status_code for i in ids if i != world.alice_ticket["id"]}
    assert world.get(f"/tickets/{world.alice_ticket['id']}", headers=world.as_("bob")).status_code == 404
    assert 403 not in seen
    assert world.patch(f"/tickets/{world.alice_ticket['id']}", json={"title": "A fine title"}, headers=world.as_("bob")).status_code == 404
    assert world.patch("/tickets/999", json={"title": "A fine title"}, headers=world.as_("bob")).status_code == 404


# ------------------------------------------------------------------------------------------------------------------------------------------- what comes back
def test_error_answers_never_contain_internals_for_any_request_the_suite_makes(world):
    answers = [
        world.get("/tickets/xyz", headers=world.as_("bob")),
        world.get("/tickets", params={"limit": "'"}, headers=world.as_("bob")),
        world.post("/tickets", json={"title": "'", "body": ""}, headers=world.as_("bob")),
        world.post("/tickets", content=b"{", headers={**world.as_("bob"), "content-type": "application/json"}),
        world.get("/nothing"),
        world.put("/tickets"),
        world.get("/tickets", headers={"Authorization": "Bearer '"}),
    ]
    for r in answers:
        assert_clean(r)
        body = r.json()
        assert set(body) <= {"type", "title", "status", "code", "detail", "request_id", "errors"}


def test_the_table_and_the_index_are_exactly_what_the_service_created(world):
    assert [(kind, name) for kind, name, _ in world.baseline_schema] == [("index", "tickets_requester"), ("table", "tickets")]
