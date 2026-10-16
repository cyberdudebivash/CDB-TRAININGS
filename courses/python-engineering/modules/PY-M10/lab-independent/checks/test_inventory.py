"""The ten published checks of the PY-M10 independent lab. They show the shape of the answers; the specification (README.md) is longer than they are, and the instructors' suite tests all of it."""
from __future__ import annotations

import pytest

BODY = {"address": "10.0.0.5", "criticality": 3, "tags": ["prod", "web"]}
HOST = "web-1.corp.example"


def test_01_the_key_store_keeps_a_hash_and_checks_secrets(inv):
    store = inv.KeyStore()
    store.add("keyid0001", "s" * 24, "acme", "read")
    assert store.check("keyid0001", "s" * 24) == ("acme", "read")
    assert store.check("keyid0001", "t" * 24) is None and store.check("keyid9999", "s" * 24) is None
    for bad in (("short", "s" * 24, "acme", "read"), ("keyid0002", "short", "acme", "read"), ("keyid0002", "s" * 24, "ACME", "read"), ("keyid0002", "s" * 24, "acme", "admin"), ("keyid0001", "s" * 24, "acme", "read")):
        with pytest.raises(ValueError):
            store.add(*bad)


def test_02_a_request_without_a_valid_key_is_a_401_with_a_challenge(make_env):
    env = make_env()
    for headers in ({}, {"X-API-Key": "nonsense"}, {"X-API-Key": "acmewrite1." + "Z" * 24}):
        r = env.client.get("/assets", headers=headers)
        assert r.status_code == 401 and r.headers["www-authenticate"] == 'ApiKey realm="inventory"'
        assert r.headers["content-type"].startswith("application/problem+json") and r.json()["code"] == "unauthorised"


def test_03_a_put_creates_with_201_an_etag_and_a_location_and_a_get_returns_it(make_env):
    env = make_env()
    r = env.client.put(f"/assets/{HOST}", json=BODY, headers=env.h())
    assert r.status_code == 201 and r.headers["etag"] == '"1"' and r.headers["location"] == f"/assets/{HOST}"
    assert r.json()["version"] == 1 and r.json()["tags"] == ["prod", "web"] and r.json()["created_at"] == "2026-10-14T12:00:00Z"
    g = env.client.get(f"/assets/{HOST}", headers=env.h("ar"))
    assert g.status_code == 200 and g.json() == r.json() and g.headers["etag"] == '"1"'


def test_04_putting_the_same_content_again_changes_nothing(make_env):
    env = make_env()
    first = env.client.put(f"/assets/{HOST}", json=BODY, headers=env.h()).json()
    env.clock.now += 300
    again = env.client.put(f"/assets/{HOST}", json={**BODY, "tags": ["web", "prod"]}, headers=env.h())
    assert again.status_code == 200 and again.json() == first and again.headers["etag"] == '"1"'
    assert env.client.put(f"/assets/{HOST}", json={**BODY, "criticality": 4}, headers=env.h()).json()["version"] == 2


def test_05_a_stale_if_match_is_a_412_and_changes_nothing(make_env):
    env = make_env()
    env.client.put(f"/assets/{HOST}", json=BODY, headers=env.h())
    env.client.put(f"/assets/{HOST}", json={**BODY, "criticality": 5}, headers=env.h())
    r = env.client.put(f"/assets/{HOST}", json={**BODY, "criticality": 1}, headers=env.h(**{"If-Match": '"1"'}))
    assert r.status_code == 412 and r.json()["code"] == "precondition_failed"
    assert env.client.get(f"/assets/{HOST}", headers=env.h()).json()["criticality"] == 5


def test_06_another_tenant_sees_a_404_exactly_as_for_a_missing_asset(make_env):
    env = make_env()
    env.client.put(f"/assets/{HOST}", json=BODY, headers=env.h("aw"))
    theirs, missing = env.client.get(f"/assets/{HOST}", headers=env.h("gw")), env.client.get("/assets/nothing.example", headers=env.h("gw"))
    strip = lambda r: {k: v for k, v in r.json().items() if k != "request_id"}          # noqa: E731
    assert theirs.status_code == missing.status_code == 404 and strip(theirs) == strip(missing)
    assert env.client.get("/assets", headers=env.h("gw")).json() == {"items": [], "next_cursor": None}


def test_07_a_read_only_key_cannot_write(make_env):
    env = make_env()
    r = env.client.put(f"/assets/{HOST}", json=BODY, headers=env.h("ar"))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    assert env.client.delete(f"/assets/{HOST}", headers=env.h("ar")).status_code == 403
    assert env.client.get(f"/assets/{HOST}", headers=env.h("aw")).status_code == 404


@pytest.mark.parametrize("name, body", [("10.0.0.1", BODY), ("UPPER.example", BODY), (HOST, {**BODY, "address": "10.0.0.256"}), (HOST, {**BODY, "address": "::ffff:10.0.0.1"}),
                                        (HOST, {**BODY, "criticality": "3"}), (HOST, {**BODY, "extra": 1}), (HOST, {**BODY, "tags": ["a", "a"]})])
def test_08_invalid_input_is_a_422_problem_that_never_echoes_the_input(make_env, name, body):
    env = make_env()
    r = env.client.put(f"/assets/{name}", json=body, headers=env.h())
    assert r.status_code == 422 and r.json()["code"] == "validation_error" and r.headers["content-type"].startswith("application/problem+json")
    assert all(set(e) == {"loc", "code"} for e in r.json()["errors"]) and "10.0.0.256" not in r.text
    assert env.client.get("/assets", headers=env.h()).json()["items"] == []


def test_09_the_list_filters_and_pages_with_a_cursor(make_env):
    env = make_env()
    for i in range(7):
        env.client.put(f"/assets/host-{i}.example", json={"address": f"10.0.{i // 4}.{i % 4 + 1}", "criticality": 1 + i % 5, "tags": ["even" if i % 2 == 0 else "odd"]}, headers=env.h())
    seen, cursor = [], None
    for _ in range(5):
        page = env.client.get("/assets", params={"limit": 3, **({"cursor": cursor} if cursor else {})}, headers=env.h("ar")).json()
        seen += [a["hostname"] for a in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == [f"host-{i}.example" for i in range(7)]
    even = env.client.get("/assets", params={"tag": "even"}, headers=env.h("ar")).json()["items"]
    assert [a["hostname"] for a in even] == ["host-0.example", "host-2.example", "host-4.example", "host-6.example"]
    assert [a["hostname"] for a in env.client.get("/assets", params={"network": "10.0.1.0/24"}, headers=env.h("ar")).json()["items"]] == ["host-4.example", "host-5.example", "host-6.example"]


def test_10_requests_over_the_limit_in_one_window_are_a_429_with_retry_after(make_env):
    env = make_env(rate_limit=3)
    assert [env.client.get("/assets", headers=env.h("ar")).status_code for _ in range(3)] == [200, 200, 200]
    r = env.client.get("/assets", headers=env.h("ar"))
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and r.headers["retry-after"] == "60"
    assert env.client.get("/assets", headers=env.h("aw")).status_code == 200                      # another key has its own count
    env.clock.now += 60
    assert env.client.get("/assets", headers=env.h("ar")).status_code == 200
