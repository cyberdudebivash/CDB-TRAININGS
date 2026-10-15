"""Step 7 - Hardening at the edge: request ids, security headers and body limits, in an ASGI middleware that wraps the whole application."""
from __future__ import annotations

import asyncio
import json
import re

import pytest

HEX32 = re.compile(r"^[0-9a-f]{32}$")
SECURITY = {"cache-control": "no-store", "x-content-type-options": "nosniff", "referrer-policy": "no-referrer", "content-security-policy": "default-src 'none'; frame-ancestors 'none'"}


class Toy:
    """A tiny ASGI application that records what it was given and answers with headers of its own (some of which the middleware must replace)."""

    def __init__(self, status=200, headers=None):
        self.calls = []
        self.status = status
        self.headers = headers or [(b"content-type", b"text/plain"), (b"cache-control", b"public, max-age=600"), (b"x-request-id", b"spoofed"), (b"x-custom", b"keep-me")]

    async def __call__(self, scope, receive, send):
        self.calls.append(scope)
        await send({"type": "http.response.start", "status": self.status, "headers": list(self.headers)})
        await send({"type": "http.response.body", "body": b"hello"})


def call(guard, *, method="GET", path="/x", headers=(), body=b"", scope_type="http"):
    """Run one request through `guard` and return (status, {header: value}, body, the scope the inner app saw)."""
    scope = {"type": scope_type, "method": method, "path": path, "raw_path": path.encode(), "query_string": b"", "headers": [(k.lower(), v) for k, v in headers], "state": {}}
    sent = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(guard(scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return start["status"], {k.decode(): v.decode() for k, v in start["headers"]}, payload, scope


def build(ta, max_body=100, **toy):
    inner = Toy(**toy)
    return ta.Guard(inner, max_body=max_body), inner


# ------------------------------------------------------------------------------------------------------------------------------------------- request id
def test_every_response_gets_a_fresh_request_id_when_the_client_sent_none(ta):
    guard, _ = build(ta)
    ids = [call(guard)[1]["x-request-id"] for _ in range(5)]
    assert all(HEX32.match(i) for i in ids) and len(set(ids)) == 5


@pytest.mark.parametrize("given", ["abc-123", "A.b_C-9", "x" * 64, "0", "trace.2026-10-14_a"])
def test_a_request_id_in_the_allowed_alphabet_is_kept(ta, given):
    guard, inner = build(ta)
    _, headers, _, scope = call(guard, headers=[(b"x-request-id", given.encode())])
    assert headers["x-request-id"] == given and scope["state"]["request_id"] == given


@pytest.mark.parametrize("given", ["", "has space", "semi;colon", "x" * 65, "slash/../../etc", "quote'\"", "new\nline", "tab\t", "é", "<script>", "a,b", "a=b"])
def test_any_other_request_id_is_replaced_not_cleaned_up(ta, given):
    guard, _ = build(ta)
    raw = given.encode("latin-1", errors="replace")
    _, headers, _, scope = call(guard, headers=[(b"x-request-id", raw)])
    assert HEX32.match(headers["x-request-id"]) and scope["state"]["request_id"] == headers["x-request-id"]


def test_the_id_the_application_sees_is_the_id_the_client_gets_back(ta):
    guard, inner = build(ta)
    _, headers, _, _ = call(guard)
    assert inner.calls[0]["state"]["request_id"] == headers["x-request-id"]


def test_a_spoofed_request_id_set_by_the_application_is_overwritten(ta):
    guard, _ = build(ta)
    _, headers, _, scope = call(guard, headers=[(b"x-request-id", b"mine-1")])
    assert headers["x-request-id"] == "mine-1"                                       # not "spoofed": the toy application tried to set that


def test_pick_request_id_keeps_a_clean_id_and_replaces_anything_else(ta):
    assert ta.pick_request_id("abc-123") == "abc-123"
    assert ta.pick_request_id("x" * 64) == "x" * 64
    for bad in (None, "", "x" * 65, "a b", "a;b", "é", "a\n"):
        got = ta.pick_request_id(bad)
        assert HEX32.match(got), bad
    assert len({ta.pick_request_id(None) for _ in range(10)}) == 10


def test_header_values_gives_every_value_of_a_header_in_order(ta):
    scope = {"headers": [(b"x-a", b"1"), (b"x-b", b"2"), (b"X-A", b"3"), (b"x-a", b"4")]}
    assert ta.header_values(scope, b"x-a") == [b"1", b"3", b"4"]
    assert ta.header_values(scope, b"x-b") == [b"2"]
    assert ta.header_values(scope, b"x-c") == []


def test_a_request_id_sent_twice_is_not_trusted(ta):
    guard, _ = build(ta)
    _, headers, _, _ = call(guard, headers=[(b"x-request-id", b"first-1"), (b"x-request-id", b"second-2")])
    assert HEX32.match(headers["x-request-id"])


# ------------------------------------------------------------------------------------------------------------------------------------------- headers
def test_security_headers_are_added_and_replace_what_the_application_set(ta):
    guard, _ = build(ta)
    status, headers, body, _ = call(guard)
    assert status == 200 and body == b"hello"
    assert {k: headers[k] for k in SECURITY} == SECURITY
    assert headers["x-custom"] == "keep-me" and headers["content-type"] == "text/plain"


def test_each_owned_header_appears_exactly_once(ta):
    guard, _ = build(ta)
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "state": {}}
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(guard(scope, receive, send))
    names = [k.decode().lower() for k, _ in sent[0]["headers"]]
    for owned in list(SECURITY) + ["x-request-id"]:
        assert names.count(owned) == 1, owned


def test_the_headers_the_application_set_in_another_letter_case_are_replaced_too(ta):
    inner_headers = [(b"Cache-Control", b"public"), (b"X-Request-Id", b"spoofed"), (b"X-CONTENT-TYPE-OPTIONS", b"sniff")]
    guard, _ = build(ta, headers=inner_headers)
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "state": {}}
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(guard(scope, receive, send))
    pairs = [(k.decode().lower(), v.decode()) for k, v in sent[0]["headers"]]
    assert [v for k, v in pairs if k == "cache-control"] == ["no-store"]
    assert [v for k, v in pairs if k == "x-content-type-options"] == ["nosniff"]
    assert len([1 for k, _ in pairs if k == "x-request-id"]) == 1 and ("x-request-id", "spoofed") not in pairs


def test_the_body_of_the_response_is_untouched_and_the_status_is_the_applications(ta):
    guard, _ = build(ta, status=204)
    status, _, body, _ = call(guard)
    assert status == 204 and body == b"hello"


def test_a_message_that_is_not_the_start_of_a_response_passes_through_unchanged(ta):
    guard, _ = build(ta)
    _, _, body, _ = call(guard)
    assert body == b"hello"


# ------------------------------------------------------------------------------------------------------------------------------------------- scopes other than http
@pytest.mark.parametrize("scope_type", ["lifespan", "websocket"])
def test_other_scope_types_go_straight_to_the_application(ta, scope_type):
    inner = Toy()
    guard = ta.Guard(inner, max_body=10)
    scope = {"type": scope_type, "headers": [], "state": {}}

    async def receive():
        return {}

    async def send(message):
        pass

    asyncio.run(guard(scope, receive, send))
    assert inner.calls == [scope] and "request_id" not in scope["state"]


# ------------------------------------------------------------------------------------------------------------------------------------------- body limit
def test_a_body_that_declares_more_than_the_limit_is_refused_with_413_and_never_reaches_the_application(ta):
    guard, inner = build(ta, max_body=100)
    status, headers, body, _ = call(guard, method="POST", headers=[(b"content-length", b"101")])
    b = json.loads(body)
    assert status == 413 and inner.calls == []
    assert headers["content-type"].startswith("application/problem+json")
    assert b["code"] == "body_too_large" and b["title"] == "Content Too Large" and b["status"] == 413 and "100" in b["detail"]
    assert b["request_id"] == headers["x-request-id"]


@pytest.mark.parametrize("length, ok", [(b"0", True), (b"1", True), (b"99", True), (b"100", True), (b"101", False), (b"1000", False), (b"0100", True), (b"00101", False), (b"999999999999", False)])
def test_the_limit_is_inclusive(ta, length, ok):
    guard, inner = build(ta, max_body=100)
    status, _, _, _ = call(guard, method="POST", headers=[(b"content-length", length)])
    assert (status == 200) is ok and bool(inner.calls) is ok
    if not ok:
        assert status == 413


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_the_limit_applies_to_every_method(ta, method):
    guard, inner = build(ta, max_body=10)
    assert call(guard, method=method, headers=[(b"content-length", b"11")])[0] == 413
    assert inner.calls == []


@pytest.mark.parametrize("length", [b"abc", b"-1", b"1e3", b" 5", b"5 ", b"+5", b"5.0", b"", b"\xef\xbc\x95", b"1234567890123", b"0x10", b"5,5"])
def test_a_content_length_that_is_not_a_plain_number_is_a_400(ta, length):
    guard, inner = build(ta, max_body=100)
    status, headers, body, _ = call(guard, method="POST", headers=[(b"content-length", length)])
    assert status == 400 and inner.calls == [] and json.loads(body)["code"] == "bad_content_length"
    assert headers["content-type"].startswith("application/problem+json")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
def test_a_body_without_a_length_is_refused_with_411(ta, method):
    guard, inner = build(ta)
    status, _, body, _ = call(guard, method=method, headers=[(b"transfer-encoding", b"chunked")])
    assert status == 411 and inner.calls == [] and json.loads(body)["code"] == "length_required" and json.loads(body)["title"] == "Length Required"


@pytest.mark.parametrize("method", ["GET", "DELETE", "HEAD", "OPTIONS"])
def test_other_methods_may_use_transfer_encoding_without_a_length(ta, method):
    guard, inner = build(ta)
    assert call(guard, method=method, headers=[(b"transfer-encoding", b"chunked")])[0] == 200 and len(inner.calls) == 1


def test_a_request_with_no_body_headers_at_all_passes(ta):
    guard, inner = build(ta)
    assert call(guard, method="POST")[0] == 200 and len(inner.calls) == 1


@pytest.mark.parametrize("values", [(b"5", b"5"), (b"5", b"50"), (b"500", b"5"), (b"0", b"0")])
def test_a_content_length_sent_twice_is_a_400_even_when_both_agree(ta, values):
    guard, inner = build(ta, max_body=100)
    status, _, body, _ = call(guard, method="POST", headers=[(b"content-length", v) for v in values])
    assert status == 400 and inner.calls == [] and json.loads(body)["code"] == "bad_content_length"


def test_a_declared_length_wins_over_transfer_encoding(ta):
    guard, inner = build(ta, max_body=100)
    assert call(guard, method="POST", headers=[(b"content-length", b"50"), (b"transfer-encoding", b"chunked")])[0] == 200
    assert call(guard, method="POST", headers=[(b"content-length", b"500"), (b"transfer-encoding", b"chunked")])[0] == 413


def test_the_refusals_carry_the_security_headers_and_the_request_id(ta):
    guard, _ = build(ta, max_body=10)
    for headers in ([(b"content-length", b"11")], [(b"content-length", b"x")], [(b"transfer-encoding", b"chunked")]):
        _, h, _, _ = call(guard, method="POST", headers=headers + [(b"x-request-id", b"abc-1")])
        assert h["x-request-id"] == "abc-1" and {k: h[k] for k in SECURITY} == SECURITY


def test_the_guard_does_not_read_the_body_itself(ta):
    guard, inner = build(ta, max_body=100)
    reads = []
    scope = {"type": "http", "method": "POST", "path": "/", "headers": [(b"content-length", b"5")], "state": {}}

    async def receive():
        reads.append(1)
        return {"type": "http.request", "body": b"hello", "more_body": False}

    async def send(message):
        pass

    asyncio.run(guard(scope, receive, send))
    assert reads == [] and len(inner.calls) == 1


# ------------------------------------------------------------------------------------------------------------------------------------------- through the whole application
def test_the_application_is_wrapped_by_the_guard_and_the_settings_choose_the_limit(api):
    built = api.build(max_body=64)
    r = built.post("/tickets", json={"title": "abc", "body": "x" * 100}, headers=built.as_())
    assert r.status_code == 413 and r.json()["code"] == "body_too_large"
    assert built.post("/tickets", json={"title": "abc", "body": "x"}, headers=built.as_()).status_code == 201


def test_a_413_does_not_depend_on_who_is_asking(api):
    big = {"title": "abc", "body": "x" * 20_000}
    assert api.post("/tickets", json=big).status_code == 413
    assert api.post("/tickets", json=big, headers=api.as_()).status_code == 413


def test_every_answer_of_the_application_has_a_request_id_and_the_security_headers(api):
    answers = [api.get("/healthz"), api.get("/tickets"), api.get("/nothing"), api.post("/tickets", json={}, headers=api.as_()), api.get("/tickets", headers=api.as_())]
    for r in answers:
        assert HEX32.match(r.headers["x-request-id"]) and {k: r.headers[k] for k in SECURITY} == SECURITY, r.request.url


def test_the_request_id_sent_by_the_client_comes_back_in_the_header_and_in_the_problem(api):
    r = api.get("/nothing", headers={"X-Request-ID": "client-supplied-7"})
    assert r.headers["x-request-id"] == "client-supplied-7" and r.json()["request_id"] == "client-supplied-7"
    r = api.get("/nothing", headers={"X-Request-ID": "bad id; DROP"})
    assert HEX32.match(r.headers["x-request-id"]) and r.json()["request_id"] == r.headers["x-request-id"]
