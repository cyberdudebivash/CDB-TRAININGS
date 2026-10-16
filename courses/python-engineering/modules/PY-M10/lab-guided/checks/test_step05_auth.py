"""Step 5 - Who is calling (authentication) and what they may do (authorisation): object level, function level and field level."""
from __future__ import annotations

import json

import pytest
from lab_support import SECRET

PROTECTED = [
    ("GET", "/tickets"),
    ("POST", "/tickets"),
    ("GET", "/tickets/1"),
    ("PATCH", "/tickets/1"),
    ("DELETE", "/tickets/1"),
]
PUBLIC = ["/healthz", "/readyz"]
AUTH_HEADER = 'Bearer realm="ticketapi"'


def send(api, method, path, headers=None):
    return api.request(method, path, headers=headers or {}, json={"title": "abc", "body": "x"} if method in ("POST", "PATCH") else None)


def stripped(response):
    body = response.json()
    body.pop("request_id", None)
    return body


# ------------------------------------------------------------------------------------------------------------------------------------------- authentication
@pytest.mark.parametrize("method, path", PROTECTED)
def test_every_protected_route_answers_401_with_a_challenge_when_there_is_no_token(api, method, path):
    r = send(api, method, path)
    assert r.status_code == 401 and r.headers["www-authenticate"] == AUTH_HEADER
    assert r.headers["content-type"].startswith("application/problem+json") and r.json()["code"] == "unauthorised"


@pytest.mark.parametrize("path", PUBLIC)
def test_the_health_routes_need_no_token(api, path):
    assert api.get(path).status_code in (200, 503)


def test_authentication_comes_before_validation_and_before_lookup(api):
    r = api.post("/tickets", json={"nonsense": True})
    assert r.status_code == 401
    assert api.get("/tickets/999999").status_code == 401
    assert api.patch("/tickets/999999", json={"bogus": 1}).status_code == 401


def test_a_valid_token_is_accepted_in_any_letter_case_of_the_scheme(api):
    token = api.token()
    for scheme in ("Bearer", "bearer", "BEARER", "bEaReR"):
        assert api.get("/tickets", headers={"Authorization": f"{scheme} {token}"}).status_code == 200


@pytest.mark.parametrize("header", ["", "Bearer", "Bearer ", "Basic YWxpY2U6c2VjcmV0", "Token abc", "abc", "Bearer a b c", "Bearer\tx"])
def test_a_header_that_is_not_a_bearer_token_is_refused(api, header):
    r = api.get("/tickets", headers={"Authorization": header})
    assert r.status_code == 401 and r.headers["www-authenticate"] == AUTH_HEADER


def test_a_token_is_accepted_only_in_the_authorization_header(api):
    token = api.token()
    assert api.get("/tickets", params={"access_token": token}).status_code == 401
    assert api.get("/tickets", params={"token": token}).status_code in (401, 422)
    assert api.get("/tickets", headers={"X-Auth-Token": token}).status_code == 401
    assert api.get("/tickets", headers={"Cookie": f"access_token={token}; session={token}"}).status_code == 401
    assert api.get("/tickets", headers={"X-Forwarded-User": "alice", "X-User": "alice", "X-Role": "admin"}).status_code == 401


def test_an_expired_token_is_refused_and_the_boundary_is_the_exp_second(api):
    token = api.token()
    h = {"Authorization": f"Bearer {token}"}
    api.clock.advance(899)
    assert api.get("/tickets", headers=h).status_code == 200
    api.clock.advance(1)
    r = api.get("/tickets", headers=h)
    assert r.status_code == 401 and r.headers["www-authenticate"] == AUTH_HEADER


def test_forged_and_tampered_tokens_are_refused(api):
    good = api.token("alice", "reader")
    head, payload, sig = good.split(".")
    other = api.token("alice", "admin").split(".")[1]
    for bad in (
        good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB"),
        f"{head}.{other}.{sig}",
        api.forged(secret="a-completely-different-secret-0123456789")["Authorization"][7:],
        api.forged(alg="none")["Authorization"][7:],
        api.forged(api.claims(role="superuser"))["Authorization"][7:],
        api.forged(api.claims(aud="somebody-else"))["Authorization"][7:],
        api.forged(api.claims(exp=None))["Authorization"][7:],
    ):
        assert api.get("/tickets", headers={"Authorization": f"Bearer {bad}"}).status_code == 401, bad[:40]


def test_all_refusals_look_alike_so_they_reveal_nothing(api):
    missing = api.get("/tickets")
    expired = (api.clock.advance(5000), api.get("/tickets", headers={"Authorization": "Bearer " + api.forged(api.claims(iat=int(api.clock()) - 5000, exp=int(api.clock()) - 4000))["Authorization"][7:]}))[1]
    forged = api.get("/tickets", headers=api.forged(secret="a-completely-different-secret-0123456789"))
    garbage = api.get("/tickets", headers={"Authorization": "Bearer not.a.token"})
    shapes = {json.dumps(stripped(r), sort_keys=True) for r in (missing, expired, forged, garbage)}
    assert len(shapes) == 1, shapes
    assert {r.headers["www-authenticate"] for r in (missing, expired, forged, garbage)} == {AUTH_HEADER}
    assert {r.status_code for r in (missing, expired, forged, garbage)} == {401}


def test_a_refusal_is_audited_with_its_reason_and_never_with_the_token_or_the_secret(api, records):
    token_expired = api.token()
    api.clock.advance(1000)
    api.get("/tickets", headers={"Authorization": f"Bearer {token_expired}"})
    api.get("/tickets")
    forged = api.forged(secret="a-completely-different-secret-0123456789")
    api.get("/tickets", headers=forged, params={})
    refusals = records.named("auth.refused")
    assert [r.reason for r in refusals] == ["expired", "missing", "bad_signature"]
    text = " ".join(str(r.__dict__) + r.getMessage() for r in records)
    assert token_expired not in text and forged["Authorization"][7:] not in text and SECRET not in text
    assert all(r.request_id and r.request_id != "-" for r in refusals)


# ------------------------------------------------------------------------------------------------------------------------------------------- object level
def test_a_reader_gets_404_for_another_readers_ticket_exactly_as_for_a_missing_one(api):
    t = api.new_ticket("alice")
    theirs = api.get(f"/tickets/{t['id']}", headers=api.as_("bob"))
    missing = api.get("/tickets/9999", headers=api.as_("bob"))
    assert theirs.status_code == missing.status_code == 404
    assert stripped(theirs) == stripped(missing)


def test_a_reader_cannot_change_or_delete_another_readers_ticket_and_learns_nothing(api):
    t = api.new_ticket("alice")
    url = f"/tickets/{t['id']}"
    assert api.patch(url, json={"title": "Hijacked title"}, headers=api.as_("bob")).status_code == 404
    assert api.delete(url, headers=api.as_("bob")).status_code == 403                    # the role check comes first: a reader may not delete at all
    after = api.get(url, headers=api.as_("alice")).json()
    assert after["title"] == t["title"] and after["updated_at"] == t["updated_at"]


def test_an_owner_can_read_and_edit_their_own_open_ticket(api):
    t = api.new_ticket("alice")
    url = f"/tickets/{t['id']}"
    assert api.get(url, headers=api.as_("alice")).status_code == 200
    r = api.patch(url, json={"title": "Printer is on fire again", "priority": "urgent"}, headers=api.as_("alice"))
    assert r.status_code == 200 and r.json()["title"] == "Printer is on fire again" and r.json()["priority"] == "urgent"


@pytest.mark.parametrize("role", ["agent", "admin"])
def test_staff_can_read_every_ticket(api, role):
    t = api.new_ticket("alice")
    r = api.get(f"/tickets/{t['id']}", headers=api.as_("sam", role))
    assert r.status_code == 200 and r.json()["requester"] == "alice"


def test_a_reader_lists_only_their_own_tickets(api):
    api.new_ticket("alice", title="alice one")
    api.new_ticket("bob", title="bob one")
    api.new_ticket("alice", title="alice two")
    r = api.get("/tickets", headers=api.as_("alice"))
    assert r.json()["total"] == 2 and {t["requester"] for t in r.json()["items"]} == {"alice"}
    r = api.get("/tickets", headers=api.as_("carol"))
    assert r.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_a_reader_cannot_list_someone_elses_tickets_by_naming_them(api):
    api.new_ticket("bob")
    r = api.get("/tickets", params={"requester": "bob"}, headers=api.as_("alice"))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    assert api.get("/tickets", params={"requester": "alice"}, headers=api.as_("alice")).status_code == 200


def test_staff_list_everything_and_may_filter_by_requester(api):
    api.new_ticket("alice")
    api.new_ticket("bob")
    api.new_ticket("bob")
    assert api.get("/tickets", headers=api.as_("sam", "agent")).json()["total"] == 3
    r = api.get("/tickets", params={"requester": "bob"}, headers=api.as_("sam", "agent"))
    assert r.json()["total"] == 2 and {t["requester"] for t in r.json()["items"]} == {"bob"}


def test_the_requester_of_a_new_ticket_is_the_token_subject_whatever_the_body_says(api):
    r = api.post("/tickets", json={"title": "abc", "body": "x", "requester": "bob"}, headers=api.as_("alice"))
    assert r.status_code == 422
    assert api.new_ticket("alice")["requester"] == "alice"
    assert api.new_ticket("sam", "agent")["requester"] == "sam"


# ------------------------------------------------------------------------------------------------------------------------------------------- function level
def test_only_an_admin_may_delete(api):
    t = api.new_ticket("alice")
    url = f"/tickets/{t['id']}"
    assert api.delete(url, headers=api.as_("alice")).status_code == 403
    assert api.delete(url, headers=api.as_("sam", "agent")).status_code == 403
    assert api.delete(url, headers=api.as_("root", "admin")).status_code == 204
    assert api.get(url, headers=api.as_("root", "admin")).status_code == 404


def test_the_role_check_for_delete_comes_before_the_lookup_so_a_missing_ticket_is_not_revealed(api):
    assert api.delete("/tickets/9999", headers=api.as_("alice")).status_code == 403
    assert api.delete("/tickets/9999", headers=api.as_("sam", "agent")).status_code == 403
    r = api.delete("/tickets/9999", headers=api.as_("root", "admin"))
    assert r.status_code == 404 and r.json()["code"] == "not_found"


@pytest.mark.parametrize("field, value", [("status", "pending"), ("assignee", "sam"), ("status", "closed")])
def test_a_reader_cannot_change_status_or_assignee_even_of_their_own_ticket(api, field, value):
    t = api.new_ticket("alice")
    r = api.patch(f"/tickets/{t['id']}", json={field: value}, headers=api.as_("alice"))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    assert api.get(f"/tickets/{t['id']}", headers=api.as_("alice")).json()[field] == t[field]


def test_a_patch_that_mixes_allowed_and_forbidden_fields_changes_nothing(api):
    t = api.new_ticket("alice")
    r = api.patch(f"/tickets/{t['id']}", json={"title": "Sneaky new title", "status": "resolved"}, headers=api.as_("alice"))
    assert r.status_code == 403
    after = api.get(f"/tickets/{t['id']}", headers=api.as_("alice")).json()
    assert after["title"] == t["title"] and after["status"] == "open"


def test_staff_may_change_status_and_assignee_and_everything_else(api):
    t = api.new_ticket("alice")
    url = f"/tickets/{t['id']}"
    r = api.patch(url, json={"status": "pending", "assignee": "sam", "priority": "high", "title": "Edited by staff", "body": "edited"}, headers=api.as_("sam", "agent"))
    assert r.status_code == 200
    assert (r.json()["status"], r.json()["assignee"], r.json()["priority"], r.json()["title"], r.json()["body"], r.json()["requester"]) == ("pending", "sam", "high", "Edited by staff", "edited", "alice")


# ------------------------------------------------------------------------------------------------------------------------------------------- field level: state
ALLOWED = {"open": {"pending", "resolved", "closed"}, "pending": {"open", "resolved", "closed"}, "resolved": {"open", "closed"}, "closed": set()}
STATES = ["open", "pending", "resolved", "closed"]


def ticket_in_state(api, state):
    t = api.new_ticket("alice")
    path = {"open": [], "pending": ["pending"], "resolved": ["resolved"], "closed": ["closed"]}[state]
    for step in path:
        assert api.patch(f"/tickets/{t['id']}", json={"status": step}, headers=api.as_("sam", "agent")).status_code == 200
    return t["id"]


@pytest.mark.parametrize("old", STATES)
@pytest.mark.parametrize("new", STATES)
def test_a_status_change_must_be_a_step_of_the_transition_table(api, old, new):
    ticket = ticket_in_state(api, old)
    r = api.patch(f"/tickets/{ticket}", json={"status": new}, headers=api.as_("sam", "agent"))
    if old == "closed":
        assert r.status_code == 409 and r.json()["code"] == "ticket_closed"
    elif new == old or new in ALLOWED[old]:
        assert r.status_code == 200 and r.json()["status"] == new
    else:
        assert r.status_code == 409 and r.json()["code"] == "invalid_transition"
    expected = new if (old != "closed" and (new == old or new in ALLOWED[old])) else old
    assert api.get(f"/tickets/{ticket}", headers=api.as_("sam", "agent")).json()["status"] == expected


def test_nobody_edits_a_closed_ticket_not_even_an_admin(api):
    ticket = ticket_in_state(api, "closed")
    for who, role in (("alice", "reader"), ("sam", "agent"), ("root", "admin")):
        r = api.patch(f"/tickets/{ticket}", json={"title": "Reopened by edit"}, headers=api.as_(who, role))
        assert r.status_code == 409 and r.json()["code"] == "ticket_closed", (who, role)


def test_a_reader_edits_their_ticket_only_while_it_is_open(api):
    for state in ("pending", "resolved"):
        ticket = ticket_in_state(api, state)
        r = api.patch(f"/tickets/{ticket}", json={"title": "Late edit of mine"}, headers=api.as_("alice"))
        assert r.status_code == 409 and r.json()["code"] == "ticket_not_open", state
    ticket = ticket_in_state(api, "open")
    assert api.patch(f"/tickets/{ticket}", json={"title": "Timely edit of mine"}, headers=api.as_("alice")).status_code == 200


def test_staff_can_edit_text_while_a_ticket_is_pending_or_resolved(api):
    for state in ("pending", "resolved"):
        ticket = ticket_in_state(api, state)
        assert api.patch(f"/tickets/{ticket}", json={"body": "staff note"}, headers=api.as_("sam", "agent")).status_code == 200


def test_the_order_of_the_checks_is_closed_then_role_then_openness_then_transition(api):
    closed = ticket_in_state(api, "closed")
    assert api.patch(f"/tickets/{closed}", json={"status": "open"}, headers=api.as_("alice")).json()["code"] == "ticket_closed"
    pending = ticket_in_state(api, "pending")
    assert api.patch(f"/tickets/{pending}", json={"status": "open"}, headers=api.as_("alice")).json()["code"] == "forbidden"
    assert api.patch(f"/tickets/{pending}", json={"title": "A new title"}, headers=api.as_("alice")).json()["code"] == "ticket_not_open"
    resolved = ticket_in_state(api, "resolved")
    assert api.patch(f"/tickets/{resolved}", json={"status": "pending"}, headers=api.as_("sam", "agent")).json()["code"] == "invalid_transition"


def test_an_explicit_null_is_refused_not_stored(api):
    t = api.new_ticket("alice")
    for body in ({"title": None}, {"assignee": None}, {"status": None}, {"priority": None, "title": "A fine new title"}):
        r = api.patch(f"/tickets/{t['id']}", json=body, headers=api.as_("sam", "agent"))
        assert r.status_code == 400 and r.json()["code"] == "null_not_allowed", body


def test_an_empty_patch_is_a_400(api):
    t = api.new_ticket("alice")
    r = api.patch(f"/tickets/{t['id']}", json={}, headers=api.as_("alice"))
    assert r.status_code == 400 and r.json()["code"] == "empty_patch"


@pytest.mark.parametrize("body", [{"requester": "bob"}, {"id": 99}, {"created_at": "2020-01-01T00:00:00Z"}, {"updated_at": "2020-01-01T00:00:00Z"}, {"role": "admin"}, {"is_admin": True}])
def test_mass_assignment_is_refused_for_every_role(api, body):
    t = api.new_ticket("alice")
    for who, role in (("alice", "reader"), ("sam", "agent"), ("root", "admin")):
        r = api.patch(f"/tickets/{t['id']}", json=body, headers=api.as_(who, role))
        assert r.status_code == 422, (who, role)
    after = api.get(f"/tickets/{t['id']}", headers=api.as_("root", "admin")).json()
    assert after == t


def test_a_reader_who_sees_nothing_gets_404_before_any_field_rule(api):
    t = api.new_ticket("alice")
    r = api.patch(f"/tickets/{t['id']}", json={"status": "closed"}, headers=api.as_("bob"))
    assert r.status_code == 404                                            # not 403: bob must not learn that the ticket exists


def test_a_change_that_races_with_another_is_a_409_conflict(api, monkeypatch):
    built = api.build()
    t = built.new_ticket("alice")
    real = built.ta.check_patch

    def check_then_lose_the_race(principal, ticket, changes):
        real(principal, ticket, changes)
        built.app.state.repo.update(ticket.id, {"status": "pending"}, int(built.clock()))          # someone else moves the ticket after our check

    monkeypatch.setattr(built.ta, "check_patch", check_then_lose_the_race)
    r = built.patch(f"/tickets/{t['id']}", json={"title": "My late edit"}, headers=built.as_("alice"))
    assert r.status_code == 409 and r.json()["code"] == "conflict"
    after = built.get(f"/tickets/{t['id']}", headers=built.as_("sam", "agent")).json()
    assert after["title"] == t["title"] and after["status"] == "pending"


# ------------------------------------------------------------------------------------------------------------------------------------------- the helpers
def test_check_patch_raises_api_errors_with_the_documented_codes(ta):
    reader = ta.Principal("alice", "reader")
    agent = ta.Principal("sam", "agent")
    mk = lambda status="open": ta.Ticket(1, "alice", "Printer", "smoke", "normal", status, None, 1, 1)           # noqa: E731

    def code(principal, ticket, changes):
        with pytest.raises(ta.ApiError) as info:
            ta.check_patch(principal, ticket, changes)
        return info.value.status, info.value.code

    assert code(reader, mk(), {"title": None}) == (400, "null_not_allowed")
    assert code(agent, mk("closed"), {"title": "new title"}) == (409, "ticket_closed")
    assert code(reader, mk(), {"status": "pending"}) == (403, "forbidden")
    assert code(reader, mk(), {"assignee": "sam"}) == (403, "forbidden")
    assert code(reader, mk("pending"), {"title": "new title"}) == (409, "ticket_not_open")
    assert code(agent, mk("resolved"), {"status": "pending"}) == (409, "invalid_transition")
    assert ta.check_patch(reader, mk(), {"title": "new", "body": "b", "priority": "low"}) is None
    assert ta.check_patch(agent, mk(), {"status": "open"}) is None
    assert ta.check_patch(agent, mk(), {"status": "resolved", "assignee": "sam"}) is None


def test_transitions_is_the_table_the_rules_are_built_from(ta):
    assert {k: set(v) for k, v in ta.TRANSITIONS.items()} == ALLOWED
