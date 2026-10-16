"""Step 6 - The endpoints and the contract: statuses, headers, bodies and the OpenAPI description a client can rely on."""
from __future__ import annotations

import re

import pytest

ISO_Z = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
FIELDS = {"id", "requester", "title", "body", "priority", "status", "assignee", "created_at", "updated_at"}


# ------------------------------------------------------------------------------------------------------------------------------------------- create
def test_post_creates_a_ticket_with_201_a_location_and_the_documented_body(api):
    r = api.post("/tickets", json={"title": "Printer on fire", "body": "smoke", "priority": "urgent"}, headers=api.as_("alice"))
    assert r.status_code == 201 and r.headers["content-type"].startswith("application/json")
    b = r.json()
    assert set(b) == FIELDS
    assert (b["id"], b["requester"], b["title"], b["body"], b["priority"], b["status"], b["assignee"]) == (1, "alice", "Printer on fire", "smoke", "urgent", "open", None)
    assert r.headers["location"] == "/tickets/1"
    assert ISO_Z.match(b["created_at"]) and b["created_at"] == b["updated_at"] == "2026-10-14T12:00:00Z"


def test_post_defaults_the_priority_and_strips_the_text(api):
    b = api.new_ticket("alice", title="  padded title  ", body="  padded body\n")
    assert b["priority"] == "normal" and b["title"] == "padded title" and b["body"] == "padded body"


def test_the_location_header_points_at_the_new_ticket_and_it_can_be_fetched(api):
    api.new_ticket("alice")
    r = api.post("/tickets", json={"title": "Second one", "body": "x"}, headers=api.as_("alice"))
    location = r.headers["location"]
    assert location == f"/tickets/{r.json()['id']}" == "/tickets/2"
    assert api.get(location, headers=api.as_("alice")).json() == r.json()


@pytest.mark.parametrize("body", [{}, {"title": "abc"}, {"body": "x"}, {"title": "ab", "body": "x"}, {"title": "abc", "body": "x", "priority": "huge"}, {"title": 5, "body": "x"}, [], "text", None, 5])
def test_post_refuses_what_is_not_a_valid_ticket(api, body):
    r = api.post("/tickets", json=body, headers=api.as_())
    assert r.status_code == 422 and r.json()["code"] == "validation_error"
    assert api.get("/tickets", headers=api.as_()).json()["total"] == 0


def test_post_needs_a_json_content_type(api):
    payload = '{"title": "abc", "body": "x"}'
    for ctype in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x", None):
        headers = {**api.as_()}
        if ctype:
            headers["content-type"] = ctype
        r = api.post("/tickets", content=payload, headers=headers)
        assert r.status_code == 422, ctype
    assert api.get("/tickets", headers=api.as_()).json()["total"] == 0


def test_post_ignores_nothing_a_form_post_from_another_site_could_send(api):
    r = api.post("/tickets", data={"title": "abc", "body": "x"}, headers=api.as_())
    assert r.status_code == 422


# ------------------------------------------------------------------------------------------------------------------------------------------- read
def test_get_one_returns_the_ticket(api):
    t = api.new_ticket("alice", priority="high")
    r = api.get(f"/tickets/{t['id']}", headers=api.as_("alice"))
    assert r.status_code == 200 and r.json() == t and set(r.json()) == FIELDS


def test_get_one_for_an_unknown_id_is_a_404_problem(api):
    r = api.get("/tickets/12345", headers=api.as_())
    assert r.status_code == 404 and r.json()["code"] == "not_found" and r.json()["detail"] == "No such ticket."


@pytest.mark.parametrize("ident", ["0", "-1", "abc", "1.5", "1e3", "2147483648", "99999999999999999999", "9223372036854775808", "1%00", "0x1", "%E2%91%A0", "٣", "1;2"])
def test_an_id_outside_one_to_2_31_minus_1_is_a_422_not_a_500(api, ident):
    r = api.get(f"/tickets/{ident}", headers=api.as_())
    assert r.status_code == 422 and r.json()["errors"][0]["loc"] == ["path", "ticket_id"]


@pytest.mark.parametrize("ident", ["01", "0001", "+1", "1_0", "1.0", "%201", "1%20", "%EF%BC%91", "00", "-0", "1e0", "١", "1,0"])
def test_an_id_is_accepted_only_in_its_plain_decimal_form_so_that_a_ticket_has_one_address(api, ident):
    t = api.new_ticket("alice")
    for _ in range(9):
        api.new_ticket("alice")
    r = api.get(f"/tickets/{ident}", headers=api.as_("alice"))
    assert r.status_code == 422 and r.json()["errors"][0]["loc"] == ["path", "ticket_id"], ident
    assert api.get(f"/tickets/{t['id']}", headers=api.as_("alice")).status_code == 200


def test_the_largest_id_is_a_404_not_an_error(api):
    assert api.get("/tickets/2147483647", headers=api.as_()).status_code == 404
    assert api.get("/tickets/1", headers=api.as_()).status_code == 404


# ------------------------------------------------------------------------------------------------------------------------------------------- list
def test_list_returns_items_total_limit_and_offset(api):
    for i in range(3):
        api.new_ticket("alice", title=f"ticket number {i}")
    b = api.get("/tickets", headers=api.as_("alice")).json()
    assert set(b) == {"items", "total", "limit", "offset"} and (b["total"], b["limit"], b["offset"]) == (3, 20, 0)
    assert [t["title"] for t in b["items"]] == ["ticket number 2", "ticket number 1", "ticket number 0"]
    assert all(set(t) == FIELDS for t in b["items"])


def test_list_orders_by_creation_time_newest_first_and_breaks_ties_by_id(api):
    api.new_ticket("alice", title="first one")
    api.new_ticket("alice", title="second one")                                    # the clock has not moved: same second
    api.clock.advance(60)
    api.new_ticket("alice", title="third one")
    assert [t["title"] for t in api.get("/tickets", headers=api.as_()).json()["items"]] == ["third one", "second one", "first one"]
    assert [t["title"] for t in api.get("/tickets", params={"order": "asc"}, headers=api.as_()).json()["items"]] == ["first one", "second one", "third one"]
    assert [t["id"] for t in api.get("/tickets", params={"sort": "id", "order": "asc"}, headers=api.as_()).json()["items"]] == [1, 2, 3]


def test_list_sorts_by_the_column_that_was_asked_for(api):
    from lab_support import T0

    for offset, title in ((300, "made third"), (200, "made second"), (100, "made first")):            # ids 1, 2 and 3, created at falling times
        api.clock.now = T0 + offset
        api.new_ticket("alice", title=title)
    api.clock.now = T0 + 1000
    assert api.patch("/tickets/2", json={"priority": "high"}, headers=api.as_("alice")).status_code == 200

    def ids(sort, order):
        r = api.get("/tickets", params={"sort": sort, "order": order}, headers=api.as_("alice"))
        assert r.status_code == 200
        return [t["id"] for t in r.json()["items"]]

    assert (ids("id", "asc"), ids("id", "desc")) == ([1, 2, 3], [3, 2, 1])
    assert (ids("created", "asc"), ids("created", "desc")) == ([3, 2, 1], [1, 2, 3])
    assert (ids("updated", "asc"), ids("updated", "desc")) == ([3, 1, 2], [2, 1, 3])


def test_list_pages_do_not_overlap_and_do_not_miss_anything(api):
    for i in range(25):
        api.new_ticket("alice", title=f"ticket number {i:02d}")
    seen = []
    for offset in (0, 10, 20):
        b = api.get("/tickets", params={"limit": 10, "offset": offset}, headers=api.as_()).json()
        assert b["total"] == 25 and b["limit"] == 10 and b["offset"] == offset
        seen += [t["id"] for t in b["items"]]
    assert seen == list(range(25, 0, -1))
    assert api.get("/tickets", params={"limit": 10, "offset": 30}, headers=api.as_()).json()["items"] == []


def test_list_filters_by_status_priority_and_text(api):
    a = api.new_ticket("alice", title="Printer on fire", priority="urgent")
    b = api.new_ticket("alice", title="VPN is slow", body="100% packet loss")
    api.patch(f"/tickets/{b['id']}", json={"status": "pending"}, headers=api.as_("sam", "agent"))
    h = api.as_("alice")
    assert [t["id"] for t in api.get("/tickets", params={"status": "pending"}, headers=h).json()["items"]] == [b["id"]]
    assert [t["id"] for t in api.get("/tickets", params={"priority": "urgent"}, headers=h).json()["items"]] == [a["id"]]
    assert [t["id"] for t in api.get("/tickets", params={"q": "PRINTER"}, headers=h).json()["items"]] == [a["id"]]
    assert [t["id"] for t in api.get("/tickets", params={"q": "100%"}, headers=h).json()["items"]] == [b["id"]]
    assert api.get("/tickets", params={"q": "%"}, headers=h).json()["total"] == 1
    assert api.get("/tickets", params={"status": "open", "priority": "normal"}, headers=h).json()["total"] == 0


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"limit": "x"}, {"offset": -1}, {"offset": 10001}, {"sort": "title"}, {"order": "sideways"}, {"status": "done"}, {"priority": "huge"}, {"q": ""}, {"q": "x" * 51}, {"owner": "alice"}, {"page": 2}])
def test_list_refuses_parameters_outside_the_contract(api, params):
    r = api.get("/tickets", params=params, headers=api.as_())
    assert r.status_code == 422 and r.json()["code"] == "validation_error" and r.json()["errors"]
    assert all(e["loc"][0] == "query" for e in r.json()["errors"])


def test_list_accepts_the_largest_page_and_a_repeated_parameter_is_not_a_crash(api):
    assert api.get("/tickets", params={"limit": 100}, headers=api.as_()).status_code == 200
    assert api.get("/tickets?limit=5&limit=6", headers=api.as_()).status_code in (200, 422)


# ------------------------------------------------------------------------------------------------------------------------------------------- patch and delete
def test_patch_returns_the_changed_ticket_and_moves_updated_at_only(api):
    t = api.new_ticket("alice")
    api.clock.advance(90)
    r = api.patch(f"/tickets/{t['id']}", json={"title": "Better title"}, headers=api.as_("alice"))
    b = r.json()
    assert r.status_code == 200 and b["title"] == "Better title"
    assert b["created_at"] == "2026-10-14T12:00:00Z" and b["updated_at"] == "2026-10-14T12:01:30Z"
    assert {k: v for k, v in b.items() if k not in {"title", "updated_at"}} == {k: v for k, v in t.items() if k not in {"title", "updated_at"}}


def test_patch_of_a_missing_ticket_is_404(api):
    assert api.patch("/tickets/999", json={"title": "Whatever new"}, headers=api.as_("sam", "agent")).status_code == 404


def test_patch_of_a_bad_id_is_422(api):
    assert api.patch("/tickets/0", json={"title": "Whatever new"}, headers=api.as_("sam", "agent")).status_code == 422


def test_delete_answers_204_with_no_body_and_removes_the_ticket(api):
    t = api.new_ticket("alice")
    r = api.delete(f"/tickets/{t['id']}", headers=api.as_("root", "admin"))
    assert r.status_code == 204 and r.content == b""
    assert api.get(f"/tickets/{t['id']}", headers=api.as_("root", "admin")).status_code == 404
    assert api.delete(f"/tickets/{t['id']}", headers=api.as_("root", "admin")).status_code == 404
    assert api.get("/tickets", headers=api.as_("alice")).json()["total"] == 0


def test_delete_of_a_bad_id_is_422_for_an_admin(api):
    assert api.delete("/tickets/abc", headers=api.as_("root", "admin")).status_code == 422


def test_there_is_no_route_for_a_trailing_slash(api):
    assert api.get("/tickets/", headers=api.as_()).status_code == 404
    assert api.get("/tickets/1/", headers=api.as_()).status_code == 404
    assert not api.get("/tickets/", headers=api.as_(), follow_redirects=False).is_redirect


# ------------------------------------------------------------------------------------------------------------------------------------------- the contract (OpenAPI)
def spec_of(api):
    """The OpenAPI description of the application, built inside the test."""
    return api.build().app.openapi()


def operations(spec):
    return {(path, method) for path, item in spec["paths"].items() for method in item}


def test_the_description_lists_exactly_the_routes_of_the_contract(api):
    spec = spec_of(api)
    assert operations(spec) == {("/healthz", "get"), ("/readyz", "get"), ("/tickets", "get"), ("/tickets", "post"), ("/tickets/{ticket_id}", "get"), ("/tickets/{ticket_id}", "patch"), ("/tickets/{ticket_id}", "delete")}


def test_the_description_names_and_versions_the_api(api):
    spec = spec_of(api)
    assert spec["info"]["title"] == "Ticket API" and spec["info"]["version"] == "1.0.0"
    assert spec["openapi"].startswith("3.")


def test_the_description_declares_bearer_authentication_for_the_protected_routes_only(api):
    spec = spec_of(api)
    scheme = spec["components"]["securitySchemes"]["bearerAuth"]
    assert scheme["type"] == "http" and scheme["scheme"] == "bearer" and scheme["bearerFormat"] == "JWT"
    for path, method in operations(spec):
        secured = bool(spec["paths"][path][method].get("security"))
        assert secured == path.startswith("/tickets"), (path, method)


@pytest.mark.parametrize(
    "path, method, statuses",
    [
        ("/tickets", "get", {"200", "401", "403", "422"}),
        ("/tickets", "post", {"201", "401", "422"}),
        ("/tickets/{ticket_id}", "get", {"200", "401", "404", "422"}),
        ("/tickets/{ticket_id}", "patch", {"200", "400", "401", "403", "404", "409", "422"}),
        ("/tickets/{ticket_id}", "delete", {"204", "401", "403", "404", "422"}),
    ],
)
def test_every_operation_documents_its_statuses(api, path, method, statuses):
    spec = spec_of(api)
    assert set(spec["paths"][path][method]["responses"]) == statuses


def test_error_responses_are_documented_as_problem_json_with_the_problem_schema(api):
    spec = spec_of(api)
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            for status, response in operation["responses"].items():
                if int(status) >= 400:
                    assert set(response["content"]) == {"application/problem+json"}, (path, method, status)
                    assert response["content"]["application/problem+json"]["schema"]["$ref"].endswith("/Problem"), (path, method, status)


def test_success_responses_name_their_schemas(api):
    spec = spec_of(api)
    ref = lambda op, status: spec["paths"][op[0]][op[1]]["responses"][status]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[1]            # noqa: E731
    assert ref(("/tickets", "post"), "201") == "TicketOut"
    assert ref(("/tickets/{ticket_id}", "get"), "200") == "TicketOut"
    assert ref(("/tickets/{ticket_id}", "patch"), "200") == "TicketOut"
    assert ref(("/tickets", "get"), "200") == "Page"
    assert "content" not in spec["paths"]["/tickets/{ticket_id}"]["delete"]["responses"]["204"]


def test_the_schemas_close_the_door_on_unknown_fields_and_state_their_limits(api):
    spec = spec_of(api)
    schemas = spec["components"]["schemas"]
    assert {"TicketIn", "TicketPatch", "TicketOut", "Page", "Problem", "FieldError"} <= set(schemas)
    assert schemas["TicketIn"]["additionalProperties"] is False and schemas["TicketPatch"]["additionalProperties"] is False
    assert set(schemas["TicketIn"]["required"]) == {"title", "body"}
    title = schemas["TicketIn"]["properties"]["title"]
    assert (title["minLength"], title["maxLength"]) == (3, 120)
    body = schemas["TicketIn"]["properties"]["body"]
    assert (body["minLength"], body["maxLength"]) == (1, 4000)
    assert schemas["TicketIn"]["properties"]["priority"]["enum"] == ["low", "normal", "high", "urgent"]
    assert set(schemas["Problem"]["required"]) == {"title", "status", "code", "detail", "request_id"}
    assert "required" not in schemas["TicketPatch"]


def test_the_description_states_the_query_parameters_with_their_limits(api):
    spec = spec_of(api)
    params = {p["name"]: p for p in spec["paths"]["/tickets"]["get"]["parameters"]}
    assert set(params) == {"status", "priority", "requester", "q", "sort", "order", "limit", "offset"}
    assert all(p["in"] == "query" for p in params.values())
    limit, offset = params["limit"]["schema"], params["offset"]["schema"]
    assert (limit["minimum"], limit["maximum"], limit["default"]) == (1, 100, 20)
    assert (offset["minimum"], offset["maximum"], offset["default"]) == (0, 10000, 0)
    assert params["sort"]["schema"]["default"] == "created" and params["order"]["schema"]["default"] == "desc"


def test_the_id_in_the_path_is_an_integer_with_bounds(api):
    spec = spec_of(api)
    for method in ("get", "patch", "delete"):
        param = spec["paths"]["/tickets/{ticket_id}"][method]["parameters"][0]
        assert param["in"] == "path" and param["required"] is True
        assert (param["schema"]["type"], param["schema"]["minimum"], param["schema"]["maximum"]) == ("integer", 1, 2**31 - 1)


def test_post_documents_its_location_header_or_at_least_its_201(api):
    spec = spec_of(api)
    assert "201" in spec["paths"]["/tickets"]["post"]["responses"]


def test_the_interactive_documentation_is_off_and_the_description_is_not_served_by_default(api):
    for path in ("/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"):
        r = api.get(path)
        assert r.status_code == 404, path


def test_the_description_is_served_when_the_settings_ask_for_it(api):
    built = api.build(expose_schema=True)
    r = built.get("/openapi.json")
    assert r.status_code == 200 and r.json() == built.app.openapi()
    assert built.get("/docs").status_code == 404 and built.get("/redoc").status_code == 404 and built.get("/docs/oauth2-redirect").status_code == 404


def test_the_description_is_built_once_and_stays_the_same(api):
    app = api.build().app
    assert app.openapi() is app.openapi()
