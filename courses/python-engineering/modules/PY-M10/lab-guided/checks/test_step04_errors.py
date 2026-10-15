"""Step 4 - Errors: one shape for every failure (RFC 9457 problem details), no echo of what the client sent, no internals."""
from __future__ import annotations

import json
import logging

import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

SCOPE = {"type": "http", "state": {"request_id": "req-123"}}
BODY_KEYS = {"type", "title", "status", "code", "detail", "request_id"}
HEADERS = {"x-request-id": "req-123", "cache-control": "no-store", "x-content-type-options": "nosniff", "referrer-policy": "no-referrer", "content-security-policy": "default-src 'none'; frame-ancestors 'none'"}


def body_of(response):
    return json.loads(response.body)


# ------------------------------------------------------------------------------------------------------------------------------------------- problem()
def test_problem_is_a_problem_json_response_with_the_documented_members(ta):
    r = ta.problem(SCOPE, 404, "not_found", "No such ticket.")
    assert r.status_code == 404 and r.media_type == "application/problem+json"
    assert r.headers["content-type"].startswith("application/problem+json")
    assert body_of(r) == {"type": "about:blank", "title": "Not Found", "status": 404, "code": "not_found", "detail": "No such ticket.", "request_id": "req-123"}


def test_problem_carries_the_request_id_and_the_security_headers_itself(ta):
    r = ta.problem(SCOPE, 500, "internal_error", "x")
    assert {k: r.headers[k] for k in HEADERS} == HEADERS


def test_problem_adds_the_extra_headers_and_they_win_over_the_defaults(ta):
    r = ta.problem(SCOPE, 401, "unauthorised", "x", headers={"WWW-Authenticate": 'Bearer realm="x"', "Cache-Control": "private"})
    assert r.headers["www-authenticate"] == 'Bearer realm="x"' and r.headers["cache-control"] == "private"
    assert r.headers.getlist("cache-control") == ["private"] and r.headers.getlist("www-authenticate") == ['Bearer realm="x"']          # header names are case-insensitive: one line each
    assert r.headers["x-content-type-options"] == "nosniff"


def test_problem_lists_field_errors_only_when_it_is_given_some(ta):
    assert "errors" not in body_of(ta.problem(SCOPE, 422, "validation_error", "x"))
    assert body_of(ta.problem(SCOPE, 422, "validation_error", "x", errors=[{"loc": ["body", "title"], "code": "missing"}]))["errors"] == [{"loc": ["body", "title"], "code": "missing"}]
    assert body_of(ta.problem(SCOPE, 422, "validation_error", "x", errors=[]))["errors"] == []


@pytest.mark.parametrize(
    "status, title",
    [(400, "Bad Request"), (401, "Unauthorized"), (403, "Forbidden"), (404, "Not Found"), (405, "Method Not Allowed"), (409, "Conflict"), (411, "Length Required"),
     (413, "Content Too Large"), (422, "Unprocessable Content"), (500, "Internal Server Error"), (503, "Service Unavailable")],
)
def test_the_title_of_a_problem_is_written_out_and_does_not_depend_on_the_python_version(ta, status, title):
    assert body_of(ta.problem(SCOPE, status, "c", "d"))["title"] == title == ta.TITLES[status]


def test_an_unlisted_status_gets_a_generic_title(ta):
    assert body_of(ta.problem(SCOPE, 418, "teapot", "d"))["title"] == "Error"


def test_the_request_id_is_a_dash_when_no_middleware_set_one(ta):
    assert body_of(ta.problem({"type": "http"}, 404, "c", "d"))["request_id"] == "-"
    assert ta.request_id_of({"type": "http"}) == "-"
    assert ta.request_id_of(SCOPE) == "req-123"


def test_the_request_id_can_be_read_from_a_request_too(ta):
    from starlette.requests import Request

    assert ta.request_id_of(Request(dict(SCOPE, headers=[]))) == "req-123"


# ------------------------------------------------------------------------------------------------------------------------------------------- field_errors()
def validation_error(ta, **kw):
    fields = {"title": "abc", "body": "x", **kw}
    try:
        ta.TicketIn(**fields)
    except ValidationError as exc:
        return RequestValidationError([dict(e, loc=("body", *e["loc"])) for e in exc.errors()])
    raise AssertionError("expected a validation error")


def test_field_errors_give_where_and_what_kind_and_nothing_else(ta):
    out = ta.field_errors(validation_error(ta, title="x", priority="nope", extra="1"))
    assert {tuple(e["loc"]): e["code"] for e in out} == {("body", "title"): "string_too_short", ("body", "priority"): "literal_error", ("body", "extra"): "extra_forbidden"}
    assert all(set(e) == {"loc", "code"} for e in out)


def test_field_errors_never_repeat_what_the_client_sent(ta):
    secret = "hunter2-secret-value"
    out = ta.field_errors(validation_error(ta, priority=secret, extra=secret))
    assert secret not in json.dumps(out)


def test_field_errors_name_a_field_only_when_it_is_a_plain_identifier(ta):
    exc = RequestValidationError([
        {"type": "extra_forbidden", "loc": ("body", "owner"), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("body", "x' OR '1'='1"), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("body", "<script>alert(1)</script>"), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("query", "line1\r\nSet-Cookie: x"), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("body", "a" * 41), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("body", "a" * 40), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("body", ""), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("body", "naïve"), "msg": "m", "input": 1},
        {"type": "extra_forbidden", "loc": ("body", "is-admin"), "msg": "m", "input": 1},
    ])
    assert [e["loc"][1] for e in ta.field_errors(exc)] == ["owner", "?", "?", "?", "?", "a" * 40, "?", "?", "?"]


def test_field_errors_keep_list_positions_as_numbers_and_names_as_text(ta):
    exc = RequestValidationError([{"type": "json_invalid", "loc": ("body", 41), "msg": "boom", "input": {}}, {"type": "missing", "loc": ("query", "limit"), "msg": "m", "input": None}])
    assert ta.field_errors(exc) == [{"loc": ["body", 41], "code": "json_invalid"}, {"loc": ["query", "limit"], "code": "missing"}]


# ------------------------------------------------------------------------------------------------------------------------------------------- the API's errors
def test_an_unknown_route_is_a_404_problem(api):
    r = api.get("/nothing/here")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/problem+json")
    b = r.json()
    assert set(b) == BODY_KEYS and b["code"] == "not_found" and b["title"] == "Not Found" and b["request_id"] == r.headers["x-request-id"]


def test_a_wrong_method_is_a_405_problem_and_names_the_allowed_methods(api):
    r = api.put("/tickets", json={}, headers=api.as_())
    assert r.status_code == 405 and r.json()["code"] == "method_not_allowed" and r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["allow"] == "GET, POST"                  # Starlette's own header says only POST here: it stops at the first route with a matching path


def request_for(app, method, path):
    from starlette.requests import Request

    return Request({"type": "http", "method": method, "path": path, "headers": [], "query_string": b"", "app": app, "state": {"request_id": "req-9"}})


def test_allowed_methods_lists_the_methods_of_every_route_with_that_path_even_one_that_matches_fully(ta, api):
    app = api.build().app
    assert ta.allowed_methods(request_for(app, "GET", "/tickets/7")) == "DELETE, GET, PATCH"
    assert ta.allowed_methods(request_for(app, "PUT", "/tickets/7")) == "DELETE, GET, PATCH"
    assert ta.allowed_methods(request_for(app, "POST", "/tickets")) == "GET, POST"
    assert ta.allowed_methods(request_for(app, "GET", "/nothing")) == ""


def test_the_handler_of_framework_errors_keeps_their_headers_and_names_statuses_it_has_no_phrase_for(api):
    import asyncio

    from starlette.exceptions import HTTPException as StarletteHTTPException

    app = api.build().app
    handler = app.exception_handlers[StarletteHTTPException]
    teapot = asyncio.run(handler(request_for(app, "GET", "/x"), StarletteHTTPException(418, headers={"X-Teapot": "yes"})))
    assert teapot.status_code == 418 and teapot.headers["x-teapot"] == "yes" and body_of(teapot)["code"] == "http_error" and body_of(teapot)["detail"] == "Error"
    assert body_of(teapot)["title"] == "Error" and body_of(teapot)["request_id"] == "req-9"
    refused = asyncio.run(handler(request_for(app, "PUT", "/tickets"), StarletteHTTPException(405, headers={"Allow": "POST", "X-Other": "kept"})))
    assert refused.headers["allow"] == "GET, POST" and refused.headers["x-other"] == "kept" and body_of(refused)["code"] == "method_not_allowed"
    missing = asyncio.run(handler(request_for(app, "GET", "/x"), StarletteHTTPException(404)))
    assert body_of(missing)["code"] == "not_found" and body_of(missing)["detail"] == "No such resource."


@pytest.mark.parametrize("method, path, allow", [("HEAD", "/tickets", "GET, POST"), ("PUT", "/tickets/1", "DELETE, GET, PATCH"), ("POST", "/tickets/1", "DELETE, GET, PATCH"), ("DELETE", "/tickets", "GET, POST"),
                                                 ("POST", "/healthz", "GET"), ("PATCH", "/readyz", "GET")])
def test_every_405_lists_all_the_methods_of_the_path_in_order(api, method, path, allow):
    r = api.request(method, path, headers=api.as_())
    assert r.status_code == 405 and r.headers["allow"] == allow and r.headers["content-type"].startswith("application/problem+json" if method != "HEAD" else "application")


def test_a_405_for_a_path_that_does_not_exist_is_a_404_without_an_allow_header(api):
    r = api.request("PUT", "/tickets/1/comments", headers=api.as_())
    assert r.status_code == 404 and "allow" not in r.headers


def test_a_validation_failure_is_a_422_problem_with_a_list_of_field_errors(api):
    r = api.post("/tickets", json={"title": "x", "body": "", "evil": 1}, headers=api.as_())
    b = r.json()
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")
    assert set(b) == BODY_KEYS | {"errors"} and b["code"] == "validation_error" and b["title"] == "Unprocessable Content"
    assert {tuple(e["loc"]): e["code"] for e in b["errors"]} == {("body", "title"): "string_too_short", ("body", "body"): "string_too_short", ("body", "evil"): "extra_forbidden"}


def test_a_422_never_echoes_the_input_the_default_fastapi_answer_would(api):
    secret = "my-password-is-hunter2"
    r = api.post("/tickets", json={"title": "abc", "body": "x", "priority": secret}, headers=api.as_())
    assert r.status_code == 422 and secret not in r.text
    r = api.get(f"/tickets?limit={secret}", headers=api.as_())
    assert r.status_code == 422 and secret not in r.text
    r = api.get(f"/tickets/{secret}", headers=api.as_())
    assert r.status_code == 422 and secret not in r.text
    r = api.post("/tickets", content=('{"title": "abc", "body": "' + secret + '" '), headers={**api.as_(), "content-type": "application/json"})
    assert r.status_code == 422 and secret not in r.text


def test_a_body_that_is_not_json_is_a_422_problem_not_a_500(api):
    r = api.post("/tickets", content=b"{not json", headers={**api.as_(), "content-type": "application/json"})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


def test_every_problem_response_carries_the_security_headers(api):
    for r in (api.get("/nothing"), api.get("/tickets"), api.put("/tickets", headers=api.as_()), api.post("/tickets", json={}, headers=api.as_())):
        assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff" and "x-request-id" in r.headers


def test_an_unexpected_exception_is_a_generic_500_problem_without_details(api, monkeypatch):
    built = api.build()
    marker = "boom-internal-detail-/srv/app/db.py"

    def explode(self, *a, **k):
        raise RuntimeError(marker)

    monkeypatch.setattr(built.ta.TicketRepo, "search", explode)
    r = built.get("/tickets", headers=built.as_())
    b = r.json()
    assert r.status_code == 500 and r.headers["content-type"].startswith("application/problem+json")
    assert set(b) == BODY_KEYS and b["code"] == "internal_error" and b["title"] == "Internal Server Error"
    assert marker not in r.text and "RuntimeError" not in r.text and "Traceback" not in r.text and "search" not in r.text
    assert b["request_id"] == r.headers["x-request-id"] and r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"


def test_an_unexpected_exception_is_logged_by_type_with_the_request_id_and_without_its_message(api, monkeypatch, records):
    built = api.build()
    monkeypatch.setattr(built.ta.TicketRepo, "search", lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("secret-message-123")))
    r = built.get("/tickets", headers={**built.as_(), "x-request-id": "trace-me-1"})
    assert r.status_code == 500
    errors = [rec for rec in records if rec.name == "ticketapi.audit" and rec.levelno == logging.ERROR]
    assert len(errors) == 1
    rec = errors[0]
    assert rec.event == "error" and rec.request_id == "trace-me-1" and "RuntimeError" in rec.getMessage()
    assert "secret-message-123" not in rec.getMessage() and "secret-message-123" not in str(rec.__dict__)


def test_an_api_error_becomes_a_problem_with_its_own_status_code_detail_and_headers(ta):
    err = ta.ApiError(418, "teapot", "I am a teapot.", headers={"X-Tea": "earl grey"})
    assert (err.status, err.code, err.detail, err.headers) == (418, "teapot", "I am a teapot.", {"X-Tea": "earl grey"})
    assert isinstance(err, Exception) and "418" in str(err)
    assert ta.ApiError(400, "c", "d").headers == {}
