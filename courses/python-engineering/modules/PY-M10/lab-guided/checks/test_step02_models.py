"""Step 2 - Models: what the service accepts is decided here, by types and limits, before any other code sees the data."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

GOOD = {"title": "Printer on fire", "body": "It smells of smoke."}


def codes(exc: ValidationError) -> set[str]:
    return {e["type"] for e in exc.errors()}


# ------------------------------------------------------------------------------------------------------------------------------------------- TicketIn
def test_a_minimal_ticket_is_valid_and_the_priority_defaults_to_normal(ta):
    t = ta.TicketIn(**GOOD)
    assert (t.title, t.body, t.priority) == ("Printer on fire", "It smells of smoke.", "normal")


def test_the_json_form_is_accepted_too(ta):
    t = ta.TicketIn.model_validate_json('{"title": "Printer on fire", "body": "x", "priority": "urgent"}')
    assert t.priority == "urgent"


@pytest.mark.parametrize("priority", ["low", "normal", "high", "urgent"])
def test_every_listed_priority_is_accepted(ta, priority):
    assert ta.TicketIn(**GOOD, priority=priority).priority == priority


@pytest.mark.parametrize("priority", ["", "HIGH", "High", "critical", " high", "high ", 1, None, True, ["high"]])
def test_any_other_priority_is_refused(ta, priority):
    with pytest.raises(ValidationError):
        ta.TicketIn(**GOOD, priority=priority)


def test_text_is_stripped_of_leading_and_trailing_whitespace(ta):
    t = ta.TicketIn(title="  Printer on fire \t", body="\n  line one\nline two \n")
    assert t.title == "Printer on fire" and t.body == "line one\nline two"


@pytest.mark.parametrize("title, ok", [("ab", False), ("abc", True), ("a" * 120, True), ("a" * 121, False), ("   ", False), ("  ab  ", False), ("  abc  ", True), ("", False)])
def test_the_title_is_three_to_120_characters_after_stripping(ta, title, ok):
    if ok:
        assert ta.TicketIn(title=title, body="x").title == title.strip()
    else:
        with pytest.raises(ValidationError):
            ta.TicketIn(title=title, body="x")


@pytest.mark.parametrize("body, ok", [("", False), (" ", False), ("x", True), ("x" * 4000, True), ("x" * 4001, False), ("\n\n", False)])
def test_the_body_is_one_to_4000_characters_after_stripping(ta, body, ok):
    if ok:
        assert len(ta.TicketIn(title="abc", body=body).body) == len(body.strip())
    else:
        with pytest.raises(ValidationError):
            ta.TicketIn(title="abc", body=body)


def test_length_is_counted_in_characters_not_bytes(ta):
    assert len(ta.TicketIn(title="é" * 120, body="日" * 4000).body) == 4000
    assert ta.TicketIn(title="😀" * 3, body="x").title == "😀😀😀"
    with pytest.raises(ValidationError):
        ta.TicketIn(title="é" * 121, body="x")


@pytest.mark.parametrize("value", [123, 1.5, True, None, b"abcd", ["abcd"], {"a": 1}])
def test_nothing_is_coerced_into_a_string(ta, value):
    with pytest.raises(ValidationError):
        ta.TicketIn(title=value, body="x")
    with pytest.raises(ValidationError):
        ta.TicketIn(title="abc", body=value)


@pytest.mark.parametrize("field", ["requester", "status", "id", "assignee", "created_at", "updated_at", "is_admin", "role", "owner", "extra"])
def test_a_field_the_client_may_not_set_is_refused_not_ignored(ta, field):
    with pytest.raises(ValidationError) as info:
        ta.TicketIn(**GOOD, **{field: "x"})
    assert "extra_forbidden" in codes(info.value)


def test_the_json_form_refuses_unknown_fields_and_wrong_types_too(ta):
    with pytest.raises(ValidationError):
        ta.TicketIn.model_validate_json('{"title": "abc", "body": "x", "status": "closed"}')
    with pytest.raises(ValidationError):
        ta.TicketIn.model_validate_json('{"title": 12345, "body": "x"}')
    with pytest.raises(ValidationError):
        ta.TicketIn.model_validate_json('{"title": "abc", "body": "x", "priority": 2}')


@pytest.mark.parametrize("char", ["\n", "\r", "\t", "\x00", "\x07", "\x1b", "\x7f", "\x0b", "\x0c", "\x1f"])
def test_a_title_may_not_contain_any_control_character(ta, char):
    with pytest.raises(ValidationError):
        ta.TicketIn(title=f"ab{char}cd", body="x")


@pytest.mark.parametrize("char, ok", [("\n", True), ("\r", True), ("\t", True), ("\x00", False), ("\x07", False), ("\x1b", False), ("\x7f", False), ("\x0b", False), ("\x0c", False), ("\x08", False), ("\x0e", False), ("\x1f", False)])
def test_a_body_may_contain_tab_newline_and_carriage_return_but_no_other_control_character(ta, char, ok):
    if ok:
        assert ta.TicketIn(title="abc", body=f"one{char}two").body == f"one{char}two"
    else:
        with pytest.raises(ValidationError):
            ta.TicketIn(title="abc", body=f"one{char}two")


def test_text_that_cannot_be_stored_is_refused(ta):
    with pytest.raises(ValidationError):
        ta.TicketIn(title="ab\ud800cd", body="x")
    with pytest.raises(ValidationError):
        ta.TicketIn(title="abc", body="x\udfffy")


@pytest.mark.parametrize("text", ["café ٣ 日本語", "😀 emoji", "Ünï-cödé", "a‮b", "<script>alert(1)</script>", "'; DROP TABLE tickets;--", "%_\\"])
def test_ordinary_unusual_text_is_data_and_is_kept_exactly(ta, text):
    t = ta.TicketIn(title=text + "xyz", body=text)
    assert t.title == (text + "xyz").strip() and t.body == text.strip()


# ------------------------------------------------------------------------------------------------------------------------------------------- TicketPatch
def test_an_empty_patch_is_valid_and_changes_nothing(ta):
    assert ta.TicketPatch().changes() == {}


def test_changes_lists_exactly_the_fields_the_client_sent(ta):
    assert ta.TicketPatch(title="New title").changes() == {"title": "New title"}
    assert ta.TicketPatch(title="New title", status="pending", assignee="sam").changes() == {"title": "New title", "status": "pending", "assignee": "sam"}
    assert ta.TicketPatch.model_validate_json('{"priority": "low"}').changes() == {"priority": "low"}


def test_an_explicit_null_counts_as_sent(ta):
    assert ta.TicketPatch.model_validate_json('{"assignee": null}').changes() == {"assignee": None}
    assert ta.TicketPatch.model_validate_json('{"title": null, "status": null}').changes() == {"title": None, "status": None}


def test_a_field_with_a_value_equal_to_its_default_is_still_sent(ta):
    assert ta.TicketPatch(priority="normal").changes() == {"priority": "normal"}


@pytest.mark.parametrize("field", ["requester", "id", "created_at", "updated_at", "role", "extra"])
def test_a_patch_may_not_carry_a_field_that_is_not_editable(ta, field):
    with pytest.raises(ValidationError) as info:
        ta.TicketPatch(**{field: "x"})
    assert "extra_forbidden" in codes(info.value)


@pytest.mark.parametrize("kw", [{"title": "ab"}, {"title": "a" * 121}, {"title": "a\nb"}, {"body": ""}, {"body": "x" * 4001}, {"body": "a\x00b"}, {"priority": "HIGH"}, {"status": "done"}, {"status": "OPEN"},
                                {"assignee": "bad name"}, {"assignee": "x" * 65}, {"assignee": ""}, {"assignee": "a;b"}, {"assignee": "sam!"}, {"assignee": "../sam"}, {"title": 5}, {"status": 1}, {"assignee": 7}])
def test_every_editable_field_has_the_limits_of_a_new_ticket(ta, kw):
    with pytest.raises(ValidationError):
        ta.TicketPatch(**kw)


@pytest.mark.parametrize("status", ["open", "pending", "resolved", "closed"])
def test_every_listed_status_is_accepted(ta, status):
    assert ta.TicketPatch(status=status).changes() == {"status": status}


@pytest.mark.parametrize("assignee", ["sam", "svc.bot-1", "a" * 64, "sam@example.org"])
def test_an_assignee_is_a_subject(ta, assignee):
    assert ta.TicketPatch(assignee=assignee).changes() == {"assignee": assignee}


def test_patch_text_is_stripped_like_new_text(ta):
    assert ta.TicketPatch(title="  Better title ", body=" more \n").changes() == {"title": "Better title", "body": "more"}


def test_patch_text_is_not_coerced_from_bytes(ta):
    for field in ("title", "body", "assignee"):
        with pytest.raises(ValidationError):
            ta.TicketPatch(**{field: b"abcd"})


def test_a_patch_body_may_have_several_lines_but_a_patch_title_may_not(ta):
    assert ta.TicketPatch(body="line one\nline two\r\n\tline three").changes() == {"body": "line one\nline two\r\n\tline three"}
    with pytest.raises(ValidationError):
        ta.TicketPatch(title="two\nlines")


def test_changes_come_in_the_order_the_model_declares_them_whatever_the_order_they_were_sent_in(ta):
    assert list(ta.TicketPatch(assignee="sam", status="open", priority="high", body="b", title="Better title").changes()) == ["title", "body", "priority", "status", "assignee"]
    assert list(ta.TicketPatch(status="open", title="Better title").changes()) == ["title", "status"]


def test_the_text_cleaner_refuses_what_cannot_be_stored_and_what_a_field_may_not_hold(ta):
    for multiline in (False, True):
        for bad in ("ab\ud800cd", "x\udfff", "a\x00b", "a\x1bb", "a\x7fb", "a\x08b", "a\x0bb"):
            with pytest.raises(ValueError):
                ta._clean(bad, multiline=multiline)
        assert ta._clean("plain text, caf\u00e9 \U0001f600", multiline=multiline) == "plain text, caf\u00e9 \U0001f600"
    assert ta._clean("a\tb\nc\rd", multiline=True) == "a\tb\nc\rd"
    for bad in ("a\tb", "a\nb", "a\rb"):
        with pytest.raises(ValueError):
            ta._clean(bad, multiline=False)


def test_a_patch_with_lone_surrogates_is_refused(ta):
    with pytest.raises(ValidationError):
        ta.TicketPatch(title="ab\ud800cd")
    with pytest.raises(ValidationError):
        ta.TicketPatch(body="x\udfff")


# ------------------------------------------------------------------------------------------------------------------------------------------- ListParams
def test_list_params_defaults(ta):
    p = ta.ListParams()
    assert (p.status, p.priority, p.requester, p.q, p.sort, p.order, p.limit, p.offset) == (None, None, None, None, "created", "desc", 20, 0)


@pytest.mark.parametrize("limit, ok", [(0, False), (1, True), (100, True), (101, False), (-1, False)])
def test_limit_is_one_to_100(ta, limit, ok):
    if ok:
        assert ta.ListParams(limit=limit).limit == limit
    else:
        with pytest.raises(ValidationError):
            ta.ListParams(limit=limit)


@pytest.mark.parametrize("offset, ok", [(-1, False), (0, True), (10_000, True), (10_001, False)])
def test_offset_is_zero_to_10000(ta, offset, ok):
    if ok:
        assert ta.ListParams(offset=offset).offset == offset
    else:
        with pytest.raises(ValidationError):
            ta.ListParams(offset=offset)


def test_query_string_values_are_converted_because_a_query_string_has_no_types(ta):
    p = ta.ListParams.model_validate({"limit": "5", "offset": "10", "status": "open"})
    assert (p.limit, p.offset, p.status) == (5, 10, "open")


@pytest.mark.parametrize("kw", [{"limit": "many"}, {"limit": "5.5"}, {"offset": "x"}, {"limit": ""}, {"sort": "title"}, {"sort": "id; DROP TABLE tickets"}, {"order": "up"}, {"order": "ASC"}, {"status": "done"}, {"priority": "huge"},
                                {"q": ""}, {"q": "x" * 51}, {"requester": "bad name"}, {"requester": "x" * 65}, {"requester": "alice\n"}, {"requester": "alice' OR '1'='1"}, {"requester": "é"}, {"requester": " alice"}, {"requester": ""}])
def test_values_outside_the_lists_and_limits_are_refused(ta, kw):
    with pytest.raises(ValidationError):
        ta.ListParams.model_validate(kw)


@pytest.mark.parametrize("kw", [{"sort": "created"}, {"sort": "updated"}, {"sort": "id"}, {"order": "asc"}, {"order": "desc"}, {"q": "x"}, {"q": "x" * 50}, {"requester": "alice"}, {"status": "closed"}, {"priority": "low"}])
def test_the_listed_values_are_accepted(ta, kw):
    ta.ListParams.model_validate(kw)


@pytest.mark.parametrize("name", ["owner", "user", "tenant", "where", "page", "Limit", "sort_by"])
def test_an_unknown_parameter_is_refused_not_ignored(ta, name):
    with pytest.raises(ValidationError) as info:
        ta.ListParams.model_validate({name: "x"})
    assert "extra_forbidden" in codes(info.value)


# ------------------------------------------------------------------------------------------------------------------------------------------- output
def sample(ta, **kw):
    fields = dict(id=7, requester="alice", title="Printer", body="smoke", priority="high", status="open", assignee=None, created_at=1_791_979_200, updated_at=1_791_979_260)
    fields.update(kw)
    return ta.Ticket(**fields)


def test_a_ticket_is_a_frozen_value(ta):
    t = sample(ta)
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.status = "closed"                                   # type: ignore[misc]


def test_to_out_converts_epoch_seconds_to_timezone_aware_utc_datetimes(ta):
    out = sample(ta).to_out()
    assert isinstance(out, ta.TicketOut)
    assert out.created_at == datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert out.updated_at == datetime(2026, 10, 14, 12, 1, 0, tzinfo=timezone.utc)
    assert out.created_at.utcoffset().total_seconds() == 0
    assert (out.id, out.requester, out.title, out.body, out.priority, out.status, out.assignee) == (7, "alice", "Printer", "smoke", "high", "open", None)


def test_the_json_form_of_a_ticket_has_exactly_the_documented_fields_and_iso_utc_times(ta):
    import json

    data = json.loads(sample(ta, assignee="sam").to_out().model_dump_json())
    assert set(data) == {"id", "requester", "title", "body", "priority", "status", "assignee", "created_at", "updated_at"}
    assert data["created_at"] == "2026-10-14T12:00:00Z" and data["updated_at"] == "2026-10-14T12:01:00Z" and data["assignee"] == "sam"


def test_page_has_items_total_limit_and_offset(ta):
    page = ta.Page(items=[sample(ta).to_out()], total=41, limit=20, offset=40)
    assert (page.total, page.limit, page.offset, len(page.items)) == (41, 20, 40, 1)
    assert set(ta.Page.model_fields) == {"items", "total", "limit", "offset"}


def test_problem_describes_a_failure_in_the_documented_members(ta):
    assert set(ta.Problem.model_fields) == {"type", "title", "status", "code", "detail", "request_id", "errors"}
    p = ta.Problem(title="Not Found", status=404, code="not_found", detail="No such ticket.", request_id="abc")
    assert p.type == "about:blank" and p.errors is None
    assert set(ta.FieldError.model_fields) == {"loc", "code"}
