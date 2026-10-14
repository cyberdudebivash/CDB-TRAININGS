"""The published checks for the PY-M05 independent lab. They show the shape of the hidden suite; they do not cover every rule of the specification."""
from __future__ import annotations

import json

import pytest


def item(sku: str, price: str = "10.00", *, updated: str = "2026-10-01T08:00:00Z", **extra) -> dict:
    return {"sku": sku, "price": price, "currency": "EUR", "updated_at": updated, **extra}


def run(feedsync, feed, tmp_path, clock, **kwargs):
    return feedsync.sync_feed(feed.client(), tmp_path / "out", sleep=clock.sleep, clock=clock, **kwargs)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_reads_every_page_and_writes_the_three_files(feedsync, feed, tmp_path, clock):
    summary = run(feedsync, feed, tmp_path, clock, page_size=2)
    prices = read(tmp_path / "out" / "prices.json")
    assert [p["sku"] for p in prices] == ["AAA-1", "AAA-2", "BBB-1", "BBB-2", "CCC-1"]
    assert prices[2] == {"sku": "BBB-1", "price": "3.00", "currency": "EUR", "updated_at": "2026-10-01T08:00:00Z", "discount_pct": 10}
    assert prices[0]["discount_pct"] is None
    assert (summary.pages, summary.requests, summary.retries, summary.items_seen, summary.accepted, summary.rejected) == (3, 3, 0, 5, 5, 0)
    assert feed.server.requests[0].param("page_size") == "2"
    assert read(tmp_path / "out" / "summary.json")["accepted"] == 5
    assert (tmp_path / "out" / "rejects.jsonl").read_text(encoding="utf-8") == ""


def test_retries_a_busy_server_with_backoff(feedsync, feed, tmp_path, clock, reply):
    feed.faults.extend([None, reply(503, {}), reply(503, {})])
    summary = run(feedsync, feed, tmp_path, clock)
    assert (summary.pages, summary.requests, summary.retries) == (3, 5, 2)
    assert clock.slept == [0.5, 1.0]


def test_retries_a_request_that_times_out(feedsync, feed, tmp_path, clock, reply):
    feed.faults.append(reply(200, {"data": [], "next": None}, delay=0.8))
    summary = feedsync.sync_feed(feed.client(timeout=0.2), tmp_path / "out", sleep=clock.sleep, clock=clock)
    assert summary.retries == 1 and summary.accepted == 5


def test_invalid_items_are_set_aside_with_their_position_and_reason(feedsync, feed, tmp_path, clock):
    feed.pages[1][1] = item("bad sku", "4.00")                     # lower-case letters and a space are not allowed in a SKU
    feed.pages[0].append({"sku": "ZZZ-1", "price": "5", "currency": "EUR", "updated_at": "2026-10-01T08:00:00Z"})     # price needs two decimals
    feed.pages[2].extend(item(f"CCC-{n}") for n in range(2, 9))      # enough valid items that two invalid ones stay under the limit
    summary = run(feedsync, feed, tmp_path, clock)
    assert (summary.items_seen, summary.accepted, summary.rejected) == (13, 11, 2)
    lines = [json.loads(line) for line in (tmp_path / "out" / "rejects.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["page"], r["index"]) for r in lines] == [(1, 2), (2, 1)]
    assert "sku" in lines[1]["errors"] and "price" in lines[0]["errors"] and lines[1]["item"]["sku"] == "bad sku"


def test_the_latest_update_wins_when_a_sku_appears_twice(feedsync, feed, tmp_path, clock):
    feed.pages[0][1] = item("CCC-1", "9.00", updated="2026-10-01T12:00:00+02:00")     # 10:00 UTC: later than the entry below
    summary = run(feedsync, feed, tmp_path, clock)
    prices = {p["sku"]: p for p in read(tmp_path / "out" / "prices.json")}
    assert prices["CCC-1"]["price"] == "9.00" and prices["CCC-1"]["updated_at"] == "2026-10-01T10:00:00Z"
    assert (summary.accepted, summary.duplicates_dropped) == (4, 1)


def test_too_many_invalid_items_fail_the_run_and_change_nothing(feedsync, feed, tmp_path, clock):
    out = tmp_path / "out"
    out.mkdir()
    (out / "prices.json").write_text('["previous run"]', encoding="utf-8")
    feed.pages[0] = [item("bad one"), item("bad two")]
    with pytest.raises(feedsync.RejectThresholdExceeded) as info:
        run(feedsync, feed, tmp_path, clock)
    assert (info.value.rejected, info.value.total) == (2, 5)
    assert sorted(p.name for p in out.iterdir()) == ["prices.json"] and (out / "prices.json").read_text(encoding="utf-8") == '["previous run"]'


def test_a_next_link_to_another_host_is_never_followed(feedsync, feed, tmp_path, clock, reply):
    from scripted_server import ScriptedServer
    with ScriptedServer(lambda request: reply(200, {"data": [], "next": None})) as elsewhere:
        feed.faults.append(reply(200, {"data": [item("AAA-1")], "next": f"{elsewhere.url}/v2/prices"}))
        with pytest.raises(feedsync.FeedError, match="origin"):
            run(feedsync, feed, tmp_path, clock)
        assert elsewhere.requests == [], "nothing may be sent to a host the client was not configured for"


def test_a_failed_run_leaves_the_previous_results_alone(feedsync, feed, tmp_path, clock, reply):
    out = tmp_path / "out"
    out.mkdir()
    (out / "prices.json").write_text('["previous run"]', encoding="utf-8")
    feed.faults.extend([None] + [reply(503, {})] * 5)
    with pytest.raises(feedsync.FeedError, match="gave up"):
        run(feedsync, feed, tmp_path, clock)
    assert (out / "prices.json").read_text(encoding="utf-8") == '["previous run"]'
    assert sorted(p.name for p in out.iterdir()) == ["prices.json"]
