"""The provided checks for the PY-M05 guided lab. Work one function at a time:  python -m pytest -k delay_for"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import httpx
import pytest

NOW = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


def settings_file(tmp_path, text: str):
    path = tmp_path / "settings.toml"
    path.write_text(text, encoding="utf-8")
    return path


# ------------------------------------------------------------------------------------------------ A read_settings
def test_read_settings_valid_with_defaults(syncer, tmp_path):
    settings = syncer.read_settings(settings_file(tmp_path, 'base_url = "http://localhost:8000/"\n'))
    assert (settings.base_url, settings.page_size, settings.timeout_seconds, settings.max_attempts) == ("http://localhost:8000", 50, 5.0, 4)


def test_read_settings_accepts_whole_numbers_for_seconds_and_unicode(syncer, tmp_path):
    settings = syncer.read_settings(settings_file(tmp_path, '# Catalogue – café\nbase_url = "https://api.example.test"\ntimeout_seconds = 10\npage_size = 100\nmax_attempts = 6\n'))
    assert (settings.timeout_seconds, settings.page_size, settings.max_attempts) == (10.0, 100, 6)


@pytest.mark.parametrize("text, field", [
    ('page_size = 20\n', "base_url"),
    ('base_url = "ftp://files.example.test"\n', "base_url"),
    ('base_url = "http://x"\npage_size = 0\n', "page_size"),
    ('base_url = "http://x"\npage_size = 101\n', "page_size"),
    ('base_url = "http://x"\npage_size = "50"\n', "page_size"),
    ('base_url = "http://x"\ntimeout_seconds = 0\n', "timeout_seconds"),
    ('base_url = "http://x"\ntimeout_seconds = 61\n', "timeout_seconds"),
    ('base_url = "http://x"\nmax_attempts = 7\n', "max_attempts"),
    ('base_url = "http://x"\nretries = 3\n', "retries"),
])
def test_read_settings_rejects_bad_values_and_names_the_field(syncer, tmp_path, text, field):
    with pytest.raises(syncer.SettingsError, match=field):
        syncer.read_settings(settings_file(tmp_path, text))


def test_read_settings_invalid_toml_and_missing_file(syncer, tmp_path):
    with pytest.raises(syncer.SettingsError, match=r"invalid TOML in settings\.toml"):
        syncer.read_settings(settings_file(tmp_path, 'base_url = "unterminated\n'))
    with pytest.raises(FileNotFoundError):
        syncer.read_settings(tmp_path / "absent.toml")


# ------------------------------------------------------------------------------------------------ B write_json_atomic
def test_write_json_atomic_writes_readable_utf8_json_and_leaves_nothing_behind(syncer, tmp_path):
    target = tmp_path / "out.json"
    syncer.write_json_atomic(target, {"name": "café", "n": [1, 2]})
    raw = target.read_bytes()
    assert "café".encode("utf-8") in raw and b"\\u00e9" not in raw
    assert raw.endswith(b"}\n") and b'\n  "name"' in raw
    assert json.loads(raw) == {"name": "café", "n": [1, 2]}
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]


def test_write_json_atomic_replaces_an_existing_file(syncer, tmp_path):
    target = tmp_path / "out.json"
    target.write_text('{"old": true}', encoding="utf-8")
    syncer.write_json_atomic(target, ["new"])
    assert json.loads(target.read_text(encoding="utf-8")) == ["new"]


def test_write_json_atomic_keeps_the_old_file_when_the_data_cannot_be_serialised(syncer, tmp_path):
    target = tmp_path / "out.json"
    target.write_text('{"old": true}', encoding="utf-8")
    with pytest.raises(TypeError):
        syncer.write_json_atomic(target, {"bad": {1, 2, 3}})
    assert target.read_text(encoding="utf-8") == '{"old": true}'
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]


def test_write_json_atomic_keeps_the_old_file_and_cleans_up_when_the_replacement_fails(syncer, tmp_path, monkeypatch):
    target = tmp_path / "out.json"
    target.write_text('{"old": true}', encoding="utf-8")

    def refuse(*args, **kwargs):
        raise PermissionError("simulated failure")

    monkeypatch.setattr(os, "replace", refuse)
    with pytest.raises(PermissionError):
        syncer.write_json_atomic(target, ["new"])
    assert target.read_text(encoding="utf-8") == '{"old": true}'
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]


# ------------------------------------------------------------------------------------------------ C make_client
def test_make_client_has_explicit_timeouts_no_redirects_and_a_user_agent(syncer):
    settings = syncer.Settings(base_url="http://example.test/api", timeout_seconds=7.5)
    with syncer.make_client(settings) as client:
        t = client.timeout
        assert (t.connect, t.read, t.write, t.pool) == (3.0, 7.5, 7.5, 7.5)
        assert client.follow_redirects is False
        assert client.headers["user-agent"] == "catalogsync/1.0"
        assert str(client.base_url).startswith("http://example.test/api")


def test_make_client_connect_timeout_is_never_longer_than_the_overall_timeout(syncer):
    with syncer.make_client(syncer.Settings(base_url="http://example.test", timeout_seconds=1.5)) as client:
        assert client.timeout.connect == 1.5


def test_make_client_uses_the_given_transport(syncer):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"seen": request.headers["user-agent"]}))
    with syncer.make_client(syncer.Settings(base_url="http://example.test"), transport=transport) as client:
        assert client.get("/x").json() == {"seen": "catalogsync/1.0"}


# ------------------------------------------------------------------------------------------------ D delay_for
def test_delay_for_backoff_doubles_and_is_capped(syncer):
    assert [syncer.delay_for(n) for n in range(1, 8)] == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0, 8.0]


@pytest.mark.parametrize("attempt, retry_after, expected", [(1, "2", 2.0), (1, " 3 ", 3.0), (3, "1", 2.0), (1, "0", 0.5), (1, "300", 30.0)])
def test_delay_for_whole_second_retry_after_wins_when_longer_but_is_capped(syncer, attempt, retry_after, expected):
    assert syncer.delay_for(attempt, retry_after) == expected


def test_delay_for_http_date_is_measured_from_now(syncer):
    assert syncer.delay_for(1, "Wed, 14 Oct 2026 12:00:07 GMT", now=NOW) == 7.0
    assert syncer.delay_for(1, "Wed, 14 Oct 2026 11:59:00 GMT", now=NOW) == 0.5        # a date in the past: just the backoff
    assert syncer.delay_for(1, "Wed, 14 Oct 2026 12:10:00 GMT", now=NOW) == 30.0


@pytest.mark.parametrize("junk", ["soon", "-3", "", "1.5", "1e3", "٣"])
def test_delay_for_ignores_a_retry_after_it_cannot_use(syncer, junk):
    assert syncer.delay_for(2, junk, now=NOW) == 1.0


# ------------------------------------------------------------------------------------------------ E fetch_json
def test_fetch_json_returns_the_object_and_sends_the_parameters(syncer, api):
    data = syncer.fetch_json(api.client(), "/products", params={"limit": 2})
    assert [item["id"] for item in data["items"]] == [1, 2] and data["next_cursor"] == "cur-2"
    assert api.calls[0].query == {"limit": ["2"]}


def test_fetch_json_retries_server_errors_with_backoff(syncer, api, sleeps, reply):
    api.faults.extend([reply(503, {"error": "busy"}), reply(502, {"error": "busy"})])
    data = syncer.fetch_json(api.client(), "/products", params={"limit": 1}, sleep=sleeps)
    assert data["items"][0]["id"] == 1
    assert len(api.calls) == 3 and list(sleeps) == [0.5, 1.0]


def test_fetch_json_honours_retry_after(syncer, api, sleeps, reply):
    api.faults.append(reply(429, {"error": "slow down"}, headers={"Retry-After": "2"}))
    syncer.fetch_json(api.client(), "/products", sleep=sleeps)
    assert list(sleeps) == [2.0] and len(api.calls) == 2


def test_fetch_json_does_not_retry_client_errors(syncer, api, sleeps):
    with pytest.raises(syncer.ApiError, match="404"):
        syncer.fetch_json(api.client(), "/missing", sleep=sleeps)
    assert len(api.calls) == 1 and not sleeps


def test_fetch_json_gives_up_after_the_last_attempt_without_sleeping_again(syncer, api, sleeps, reply):
    api.faults.extend([reply(503, {})] * 5)
    with pytest.raises(syncer.RetriesExhausted) as info:
        syncer.fetch_json(api.client(), "/products", attempts=3, sleep=sleeps)
    assert info.value.attempts == 3 and "503" in str(info.value)
    assert len(api.calls) == 3 and list(sleeps) == [0.5, 1.0]


def test_fetch_json_retries_a_request_that_times_out(syncer, api, sleeps, reply):
    api.faults.append(reply(200, {"items": [], "next_cursor": None}, delay=0.8))
    started = time.monotonic()
    data = syncer.fetch_json(api.client(timeout=0.2), "/products", sleep=sleeps)
    assert data["items"][0]["id"] == 1 and len(api.calls) == 2 and list(sleeps) == [0.5]
    assert time.monotonic() - started < 0.75, "the client must give up at its timeout, not wait for the slow answer"


def test_fetch_json_retries_a_dropped_connection(syncer, api, sleeps, reply):
    api.faults.append(reply(drop=True))
    assert syncer.fetch_json(api.client(), "/products", sleep=sleeps)["items"]
    assert len(api.calls) == 2


@pytest.mark.parametrize("fault, text", [
    ("html", "expected JSON"),
    ("text-json", "expected JSON"),
    ("broken", "invalid JSON"),
    ("list", "JSON object"),
    ("redirect", "302"),
])
def test_fetch_json_rejects_unusable_answers_without_retrying(syncer, api, sleeps, reply, fault, text):
    api.faults.append({"html": reply(200, "<html>maintenance</html>", content_type="text/html"),
                       "text-json": reply(200, '{"items": []}', content_type="text/plain"),
                       "broken": reply(200, '{"items": [', content_type="application/json"),
                       "list": reply(200, [1, 2, 3]),
                       "redirect": reply(302, "", headers={"Location": "/elsewhere"})}[fault])
    with pytest.raises(syncer.ApiError, match=text):
        syncer.fetch_json(api.client(), "/products", sleep=sleeps)
    assert len(api.calls) == 1 and not sleeps


def test_fetch_json_accepts_a_charset_parameter_on_the_content_type(syncer, api, reply):
    api.faults.append(reply(200, '{"ok": true}', content_type="Application/JSON; charset=utf-8"))
    assert syncer.fetch_json(api.client(), "/products") == {"ok": True}


def test_fetch_json_needs_at_least_one_attempt(syncer, api):
    with pytest.raises(ValueError, match="attempts must be at least 1"):
        syncer.fetch_json(api.client(), "/products", attempts=0)
    assert not api.calls


# ------------------------------------------------------------------------------------------------ F iter_products
def test_iter_products_reads_every_page_in_order_with_the_right_requests(syncer, api):
    products = list(syncer.iter_products(api.client(), page_size=3))
    assert [p.id for p in products] == [1, 2, 3, 4, 5, 6, 7] and isinstance(products[0], syncer.Product)
    assert [(r.param("limit"), r.param("cursor")) for r in api.calls] == [("3", None), ("3", "cur-3"), ("3", "cur-6")]


def test_iter_products_is_lazy(syncer, api):
    stream = syncer.iter_products(api.client(), page_size=3)
    assert len(api.calls) == 0
    assert next(stream).id == 1 and len(api.calls) == 1
    for _ in range(2):
        next(stream)
    assert len(api.calls) == 1, "page 1 holds three items, so no second request yet"


def test_iter_products_empty_catalogue(syncer, api):
    api.products.clear()
    assert list(syncer.iter_products(api.client())) == [] and len(api.calls) == 1


def test_iter_products_ignores_unknown_fields_but_demands_exact_types(syncer, api):
    api.products[4]["warehouse"] = "north"
    assert [p.id for p in syncer.iter_products(api.client(), page_size=10)] == [1, 2, 3, 4, 5, 6, 7]
    api.products[4]["price_cents"] = "500"                        # right number, wrong type
    with pytest.raises(syncer.SchemaError, match="price_cents") as info:
        list(syncer.iter_products(api.client(), page_size=10))
    assert (info.value.page, info.value.index) == (1, 4)


@pytest.mark.parametrize("change, field", [({"id": 0}, "id"), ({"id": "3"}, "id"), ({"name": ""}, "name"), ({"currency": "JPY"}, "currency"), ({"price_cents": -1}, "price_cents"), ({"tags": "sale"}, "tags"), ({"id": True}, "id")])
def test_iter_products_reports_the_bad_field_page_and_item(syncer, api, change, field):
    api.products[4].update(change)                                # item index 1 on page 2 when the page size is 3
    with pytest.raises(syncer.SchemaError, match=field) as info:
        list(syncer.iter_products(api.client(), page_size=3))
    assert (info.value.page, info.value.index) == (2, 1)
    assert len(api.calls) == 2, "the second page failed, so the third must not be requested"


def test_iter_products_rejects_a_page_without_next_cursor_or_items(syncer, api, reply):
    api.faults.append(reply(200, {"items": []}))
    with pytest.raises(syncer.SchemaError, match="next_cursor") as info:
        list(syncer.iter_products(api.client()))
    assert (info.value.page, info.value.index) == (1, None)
    api.faults.append(reply(200, {"items": "none", "next_cursor": None}))
    with pytest.raises(syncer.SchemaError, match="items"):
        list(syncer.iter_products(api.client()))


@pytest.mark.parametrize("cursors", [["cur-3", "cur-3"], ["cur-1", "cur-2", "cur-1"]])
def test_iter_products_stops_a_cursor_loop(syncer, api, reply, cursors):
    """The server hands out a cursor it has already used: at once (cur-3, cur-3) or after a detour (cur-1, cur-2, cur-1)."""
    api.faults.extend(reply(200, {"items": [], "next_cursor": c}) for c in cursors)
    with pytest.raises(syncer.ApiError, match="pagination loop"):
        list(syncer.iter_products(api.client(), page_size=3))
    assert len(api.calls) == len(cursors), "the loop must be noticed as soon as the repeated cursor arrives"


def test_iter_products_stops_endless_listings(syncer, api, reply):
    def endless(request):
        n = int(request.param("cursor", "cur-0").removeprefix("cur-")) + 1
        return reply(200, {"items": [], "next_cursor": f"cur-{n}"})

    api.server.app = endless
    with pytest.raises(syncer.ApiError, match="more than 3 pages"):
        list(syncer.iter_products(api.client(), max_pages=3))
    assert len(api.calls) == 3


def test_iter_products_retries_inside_the_listing_without_repeating_items(syncer, api, sleeps, reply):
    api.faults.extend([None, reply(503, {}), reply(503, {})])
    products = list(syncer.iter_products(api.client(), page_size=3, sleep=sleeps))
    assert [p.id for p in products] == [1, 2, 3, 4, 5, 6, 7] and list(sleeps) == [0.5, 1.0]


# ------------------------------------------------------------------------------------------------ G sync
def test_sync_writes_the_catalogue_sorted_by_id(syncer, api, tmp_path):
    api.products.reverse()
    out = tmp_path / "catalogue.json"
    assert syncer.sync(api.client(), out, page_size=2) == 7
    written = json.loads(out.read_text(encoding="utf-8"))
    assert [p["id"] for p in written] == [1, 2, 3, 4, 5, 6, 7]
    assert written[0] == {"id": 1, "name": "item-1", "price_cents": 100, "currency": "USD", "tags": ["t"]}


def test_sync_leaves_the_previous_file_alone_when_a_later_page_fails(syncer, api, sleeps, reply, tmp_path):
    out = tmp_path / "catalogue.json"
    out.write_text('["previous run"]', encoding="utf-8")
    api.faults.extend([None, reply(503, {}), reply(503, {})])
    with pytest.raises(syncer.RetriesExhausted):
        syncer.sync(api.client(), out, page_size=3, attempts=2, sleep=sleeps)
    assert out.read_text(encoding="utf-8") == '["previous run"]'
    assert [p.name for p in tmp_path.iterdir()] == ["catalogue.json"]


def test_sync_leaves_the_previous_file_alone_when_an_item_is_invalid(syncer, api, tmp_path):
    out = tmp_path / "catalogue.json"
    out.write_text('["previous run"]', encoding="utf-8")
    api.products[6]["currency"] = "???"
    with pytest.raises(syncer.SchemaError):
        syncer.sync(api.client(), out, page_size=3)
    assert out.read_text(encoding="utf-8") == '["previous run"]'
