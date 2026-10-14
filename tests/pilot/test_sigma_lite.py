"""Unit tests for the teaching evaluator: semantics are documented, and unsupported features fail closed."""
import datetime as dt
import hashlib

import pytest

from soc_lab.events import fmt_ts, parse_ts
from soc_lab.sigma_lite import RuleError, lint_exceptions, parse_documents, run_rules

T0 = dt.datetime(2026, 3, 2, 8, 0, 0, tzinfo=dt.timezone.utc)


def ev(i, sec, user="u1", ip="198.51.100.1", eid=4625, **extra):
    row = {"event_id": f"evt-{i:06d}", "@timestamp": fmt_ts(T0 + dt.timedelta(seconds=sec)), "EventID": eid,
           "TargetUserName": user, "IpAddress": ip, "LogonType": 3}
    row.update(extra)
    return row


BASE = {"title": "Failed", "name": "failed", "id": "11111111-1111-4111-8111-111111111111",
        "logsource": {"product": "windows", "service": "security"}, "detection": {"selection": {"EventID": 4625}, "condition": "selection"}}


def corr(ctype="event_count", group=("IpAddress",), span="60s", cond=None, field=None, name="c1"):
    c = dict(cond or {"gte": 3})
    if field:
        c["field"] = field
    return {"title": "Corr", "name": name, "id": "22222222-2222-4222-8222-" + hashlib.md5(name.encode()).hexdigest()[:12],
            "correlation": {"type": ctype, "rules": ["failed"], "group-by": list(group), "timespan": span, "condition": c}}


def run(docs, events, exceptions=None):
    return run_rules(parse_documents(docs), events, exceptions)


# ------------------------------------------------------------------ correlation semantics

def test_event_count_fires_inside_window():
    r = run([BASE, corr()], [ev(1, 0), ev(2, 10), ev(3, 20)])
    assert len(r["alerts"]) == 1 and r["alerts"][0]["metric"] == 3 and len(r["alerts"][0]["evidence"]) == 3


def test_event_count_does_not_fire_when_events_spread_out():
    assert run([BASE, corr()], [ev(1, 0), ev(2, 10), ev(3, 70)])["alerts"] == []


def test_window_is_open_at_the_old_end():
    # window for the 3rd event is (60-60, 60] = (0, 60]: the event at exactly t=0 is excluded
    assert run([BASE, corr()], [ev(1, 0), ev(2, 30), ev(3, 60)])["alerts"] == []
    assert len(run([BASE, corr()], [ev(1, 1), ev(2, 30), ev(3, 60)])["alerts"]) == 1


def test_value_count_counts_distinct_values_only():
    events = [ev(1, 0, "a"), ev(2, 5, "a"), ev(3, 10, "a"), ev(4, 15, "b")]
    assert run([BASE, corr("value_count", field="TargetUserName")], events)["alerts"] == []
    events.append(ev(5, 20, "c"))
    r = run([BASE, corr("value_count", field="TargetUserName")], events)
    assert len(r["alerts"]) == 1 and r["alerts"][0]["metric"] == 3


def test_groups_are_independent():
    events = [ev(1, 0, ip="198.51.100.1"), ev(2, 5, ip="198.51.100.2"), ev(3, 10, ip="198.51.100.1"), ev(4, 15, ip="198.51.100.2"),
              ev(5, 20, ip="198.51.100.1")]
    r = run([BASE, corr()], events)
    assert [a["group"]["IpAddress"] for a in r["alerts"]] == ["198.51.100.1"]


def test_alert_is_extended_while_condition_holds_then_rearms():
    events = [ev(i, i * 10) for i in range(1, 8)]          # continuous burst: one alert, evidence grows
    events += [ev(20, 1000 + j * 10) for j in range(3)]    # long quiet gap then a second burst
    for k, e in enumerate(events):
        e["event_id"] = f"evt-{k + 1:06d}"
    r = run([BASE, corr()], events)
    assert len(r["alerts"]) == 2
    first = r["alerts"][0]
    assert len(first["evidence"]) == 7 and first["last_seen"] > first["fired_at"]


def test_events_missing_group_field_are_ignored():
    e = ev(1, 0)
    del e["IpAddress"]
    assert run([BASE, corr(cond={"gte": 1})], [e])["alerts"] == []


def test_referenced_rule_does_not_alert_alone_but_standalone_rule_does():
    only_base = run([BASE], [ev(1, 0), ev(2, 5)])
    assert len(only_base["alerts"]) == 2
    with_corr = run([BASE, corr(cond={"gte": 99})], [ev(1, 0), ev(2, 5)])
    assert with_corr["alerts"] == []


def test_rejects_unsorted_events():
    with pytest.raises(RuleError, match="not sorted"):
        run([BASE], [ev(1, 10), ev(2, 0)])


def test_alert_ids_are_deterministic():
    a = run([BASE, corr()], [ev(1, 0), ev(2, 10), ev(3, 20)])["alerts"][0]["alert_id"]
    b = run([BASE, corr()], [ev(1, 0), ev(2, 10), ev(3, 20)])["alerts"][0]["alert_id"]
    assert a == b and a.startswith("ALT-")


# ------------------------------------------------------------------ detection rule matching

def sel(body, cond="selection"):
    return {"title": "t", "name": "t", "id": "t", "logsource": {"product": "windows"}, "detection": {"selection": body, "condition": cond}}


def matches(body, event, cond="selection"):
    rs = parse_documents([sel(body, cond)])
    return rs.detections["t"].matches(event)


def test_modifiers():
    e = {"Image": "C:\\Windows\\System32\\CMD.EXE", "Port": 4625, "IpAddress": "10.0.5.20", "Maybe": None}
    assert matches({"Image|endswith": "cmd.exe"}, e)
    assert matches({"Image|startswith": "c:\\windows"}, e)
    assert matches({"Image|contains": "system32"}, e)
    assert not matches({"Image|contains": "syswow64"}, e)
    assert matches({"IpAddress|cidr": "10.0.0.0/8"}, e)
    assert not matches({"IpAddress|cidr": "192.168.0.0/16"}, e)
    assert matches({"Port|gte": 4000}, e) and not matches({"Port|lt": 4000}, e)
    assert matches({"Image|exists": True}, e) and matches({"Missing|exists": False}, e)
    assert matches({"Maybe": None}, e)
    assert matches({"Image|re": r"(?i)system32\\cmd"}, e)
    assert matches({"Image|contains|all": ["system32", "cmd"]}, e)
    assert not matches({"Image|contains|all": ["system32", "powershell"]}, e)
    assert matches({"IpAddress": ["1.1.1.1", "10.0.5.20"]}, e)   # list = OR
    assert matches({"IpAddress": "10.0.5.*"}, e)                  # wildcard


def test_condition_grammar_and_precedence():
    rs = parse_documents([{"title": "t", "name": "t", "id": "t", "logsource": {"product": "windows"},
                           "detection": {"a": {"x": 1}, "b": {"y": 1}, "filter_c": {"z": 1}, "condition": "a or b and not filter_c"}}])
    r = rs.detections["t"]
    assert r.matches({"x": 1, "z": 1})            # a is true -> or short-circuits regardless of filter_c
    assert r.matches({"y": 1})
    assert not r.matches({"y": 1, "z": 1})        # b and not filter_c is false
    rs2 = parse_documents([{"title": "t", "name": "t", "id": "t", "logsource": {"product": "windows"},
                            "detection": {"sel1": {"x": 1}, "sel2": {"y": 1}, "condition": "1 of sel* and (sel1 or sel2)"}}])
    assert rs2.detections["t"].matches({"x": 1})
    rs3 = parse_documents([{"title": "t", "name": "t", "id": "t", "logsource": {"product": "windows"},
                            "detection": {"sel1": {"x": 1}, "sel2": {"y": 1}, "condition": "all of them"}}])
    assert rs3.detections["t"].matches({"x": 1, "y": 1}) and not rs3.detections["t"].matches({"x": 1})


# ------------------------------------------------------------------ fail closed

@pytest.mark.parametrize("doc,msg", [
    (sel({"Image|base64": "x"}), "unsupported modifier"),
    (sel({"x": 1}, cond="selection | count() > 5"), "unexpected|unknown selection"),
    (sel({"x": 1}, cond="nope"), "unknown selection"),
    (sel({"x": 1}, cond="selection and"), "unexpected"),
    ({"title": "t", "logsource": {"product": "w"}, "detection": {"selection": {"x": 1}, "condition": "selection", "timeframe": "5m"}}, "timeframe"),
    ({"title": "t", "logsource": {"product": "w"}, "detection": {"selection": ["kw1", "kw2"], "condition": "selection"}}, "keyword lists"),
    ({"title": "t", "detection": {"selection": {"x": 1}, "condition": "selection"}}, "logsource"),
    ({"detection": {"selection": {"x": 1}, "condition": "selection"}, "logsource": {"product": "w"}}, "title"),
])
def test_invalid_detection_rules_are_rejected(doc, msg):
    with pytest.raises(RuleError, match=msg):
        parse_documents([doc])


@pytest.mark.parametrize("mutate,msg", [
    (lambda c: c.update(type="temporal"), "not supported"),
    (lambda c: c.pop("group-by"), "group-by"),
    (lambda c: c.update({"group-by": []}), "group-by"),
    (lambda c: c.update(timespan="ten minutes"), "timespan"),
    (lambda c: c.update(timespan="0m"), "positive"),
    (lambda c: c.update(rules=["ghost"]), "not found"),
    (lambda c: c.update(condition={"gte": 3, "lte": 9}), "exactly one"),
    (lambda c: c.update(condition={"gte": "3"}), "integer"),
    (lambda c: c.update(aliases={"a": "b"}), "unsupported correlation attribute"),
    (lambda c: c.update(type="value_count"), "requires condition.field"),
])
def test_invalid_correlations_are_rejected(mutate, msg):
    doc = corr()
    mutate(doc["correlation"])
    with pytest.raises(RuleError, match=msg):
        parse_documents([BASE, doc])


def test_duplicate_names_rejected_and_name_equal_to_id_accepted():
    with pytest.raises(RuleError, match="duplicate"):
        parse_documents([BASE, dict(BASE, id="33333333-3333-4333-8333-333333333333")])
    parse_documents([{"title": "x", "name": "same", "id": "same", "logsource": {"product": "w"}, "detection": {"s": {"a": 1}, "condition": "s"}}])


def test_chaining_correlations_is_rejected():
    c2 = corr(name="c2")
    c2["correlation"]["rules"] = ["c1"]
    with pytest.raises(RuleError, match="chaining"):
        parse_documents([BASE, corr(), c2])


# ------------------------------------------------------------------ exceptions

def good_exc(**over):
    ex = {"id": "EX-1", "rule": "c1", "match": {"IpAddress": "198.51.100.1"}, "reason": "approved scan for the change window only",
          "ticket": "CHG-1", "owner": "secops", "valid_from": "2026-03-02T00:00:00Z", "valid_until": "2026-03-03T00:00:00Z"}
    ex.update(over)
    return ex


def test_exception_lint_accepts_good_and_rejects_bad():
    assert lint_exceptions([good_exc()]) == []
    cases = {
        "missing owner": good_exc(owner=""),
        "wildcard": good_exc(match={"IpAddress": "198.51.*"}),
        "too broad": good_exc(match={"LogonType": 3}),
        "no expiry": good_exc(valid_until=""),
        "too long": good_exc(valid_until="2027-03-03T00:00:00Z"),
        "reversed": good_exc(valid_from="2026-03-04T00:00:00Z"),
        "short reason": good_exc(reason="ok"),
        "bad date": good_exc(valid_from="yesterday"),
    }
    for name, ex in cases.items():
        assert lint_exceptions([ex]), f"'{name}' must be rejected"
    assert any("duplicate" in p for p in lint_exceptions([good_exc(), good_exc()]))


def test_exception_unknown_rule_is_reported():
    rs = parse_documents([BASE, corr()])
    assert any("does not exist" in p for p in lint_exceptions([good_exc(rule="ghost")], rs))


def test_exception_suppresses_only_inside_window_and_only_matching_evidence():
    events = [ev(1, 0), ev(2, 10), ev(3, 20)]
    docs = [BASE, corr()]
    inside = good_exc(valid_from="2026-03-02T07:59:00Z", valid_until="2026-03-02T08:01:00Z")
    r = run(docs, events, [inside])
    assert r["alerts"] == [] and len(r["suppressed"]) == 1 and r["suppressed"][0]["suppressed_by"] == "EX-1"
    # alert ends after the window closes -> NOT suppressed (a partial overlap must never hide activity)
    partial = good_exc(valid_from="2026-03-02T07:59:00Z", valid_until="2026-03-02T08:00:15Z")
    assert len(run(docs, events, [partial])["alerts"]) == 1
    # different source -> not suppressed
    other = good_exc(match={"IpAddress": "203.0.113.9"}, valid_from="2026-03-02T07:59:00Z", valid_until="2026-03-02T08:01:00Z")
    assert len(run(docs, events, [other])["alerts"]) == 1
    # one non-matching evidence event is enough to keep the alert
    mixed = [ev(1, 0), ev(2, 10, ip="203.0.113.9"), ev(3, 20)]
    docs2 = [BASE, corr(group=("TargetUserName",))]
    assert len(run(docs2, mixed, [good_exc(valid_from="2026-03-02T07:59:00Z", valid_until="2026-03-02T08:01:00Z")])["alerts"]) == 1


def test_invalid_exception_aborts_the_run():
    with pytest.raises(RuleError, match="invalid exceptions"):
        run([BASE, corr()], [ev(1, 0)], [good_exc(owner="")])
