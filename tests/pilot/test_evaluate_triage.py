"""Unit tests for scoring and triage checking."""
import json

import pytest

from soc_lab.evaluate import alert_scenario, evaluate
from soc_lab.triage import check_records, load_records

SCEN = [{"id": "A1", "kind": "ATTACK", "name": "atk one", "mitre": "T1110.003", "first_event": "2026-03-02T08:00:00Z"},
        {"id": "A2", "kind": "ATTACK", "name": "atk two", "mitre": None, "first_event": "2026-03-02T09:00:00Z"},
        {"id": "B1", "kind": "BENIGN", "name": "benign one", "mitre": None, "first_event": "2026-03-02T08:00:00Z"}]
LABELS = {"e1": "A1", "e2": "A1", "e3": "B1", "e4": "B1", "e5": "B1", "e6": "A2"}


def alert(aid, ev, fired="2026-03-02T08:05:00Z"):
    return {"alert_id": aid, "evidence": ev, "fired_at": fired, "first_seen": fired, "last_seen": fired}


def test_alert_scenario_uses_majority_and_prefers_attack_on_tie():
    kinds = {s["id"]: s["kind"] for s in SCEN}
    assert alert_scenario(alert("x", ["e1", "e2", "e3"]), LABELS, kinds) == "A1"
    assert alert_scenario(alert("x", ["e3", "e4", "e1"]), LABELS, kinds) == "B1"
    assert alert_scenario(alert("x", ["e1", "e3"]), LABELS, kinds) == "A1"   # tie -> ATTACK


def test_recall_precision_and_ttd():
    res = {"alerts": [alert("a1", ["e1", "e2"]), alert("a2", ["e3", "e4", "e5"])], "suppressed": []}
    rep = evaluate(res, LABELS, SCEN)["summary"]
    assert rep["recall"] == 0.5 and rep["missed"] == ["A2"] and rep["precision"] == 0.5
    assert rep["false_positive_alerts"] == 1 and rep["true_positive_alerts"] == 1
    full = evaluate(res, LABELS, SCEN)["scenarios"]
    assert next(s for s in full if s["id"] == "A1")["time_to_detect_s"] == 300


def test_suppressed_attack_alert_is_flagged_not_counted_as_detection():
    res = {"alerts": [], "suppressed": [dict(alert("a1", ["e1", "e2"]), suppressed_by="EX-1")]}
    rep = evaluate(res, LABELS, SCEN)
    assert rep["summary"]["recall"] == 0.0 and rep["summary"]["suppressed_true_positive_alerts"] == 1


def test_no_alerts_gives_no_precision():
    rep = evaluate({"alerts": [], "suppressed": []}, LABELS, SCEN)["summary"]
    assert rep["precision"] is None and rep["recall"] == 0.0


# ---------------------------------------------------------------- triage checker (uses the real guided data)

@pytest.fixture()
def triage_ctx(guided, tmp_path):
    from conftest import LABS, load_json, run_cli
    from soc_lab.events import read_jsonl
    rules = LABS / "m04-guided" / "solution" / "rules"
    assert run_cli(["detect", "--rules", str(rules), "--events", str(guided / "events.enriched.jsonl"), "--out", str(tmp_path / "a.json")])[0] == 0
    alerts = load_json(tmp_path / "a.json")["alerts"]
    labels = load_json(guided / "truth" / "labels.json")
    scenarios = load_json(guided / "truth" / "scenarios.json")
    events = read_jsonl(guided / "events.jsonl")
    records = load_records(LABS / "m04-guided" / "solution" / "triage")
    return alerts, events, labels, scenarios, records


def by_scenario(records, alerts, labels, scenarios, sid):
    from soc_lab.evaluate import alert_scenario
    kinds = {s["id"]: s["kind"] for s in scenarios}
    amap = {a["alert_id"]: alert_scenario(a, labels, kinds) for a in alerts}
    return next(r for r in records if amap[r["alert_id"]] == sid)


def test_reference_records_pass(triage_ctx):
    alerts, events, labels, scenarios, records = triage_ctx
    rep = check_records(records, alerts, events, labels, scenarios)
    assert rep["passed"] == rep["total"] == 5 and rep["scenarios_without_record"] == []


def test_missing_records_are_reported(triage_ctx):
    alerts, events, labels, scenarios, records = triage_ctx
    rep = check_records(records[:2], alerts, events, labels, scenarios)
    assert len(rep["scenarios_without_record"]) == 3


def mutate(triage_ctx, sid, fn):
    alerts, events, labels, scenarios, records = triage_ctx
    rec = json.loads(json.dumps(by_scenario(records, alerts, labels, scenarios, sid)))
    fn(rec)
    rep = check_records([rec], alerts, events, labels, scenarios)["records"][0]
    return rep


def test_compromise_without_success_evidence_fails(triage_ctx):
    def drop_successes(r):
        # the reference record cites two successes (evt-001098, evt-001108); replace BOTH with failures
        r["evidence"][1] = {"event_id": "evt-001067", "observation": "another failure, not a success event"}
        r["evidence"][2] = {"event_id": "evt-001068", "observation": "yet another failure, not a success event"}

    rep = mutate(triage_ctx, "S4", drop_successes)
    assert not rep["passed"] and any("successful logon" in p for p in rep["problems"])


def test_wrong_classification_and_disposition_fail(triage_ctx):
    rep = mutate(triage_ctx, "S4", lambda r: r.update(classification="FALSE_POSITIVE_BENIGN_ACTIVITY", disposition="CLOSE_NO_ACTION"))
    assert any("classification" in p for p in rep["problems"]) and any("disposition" in p for p in rep["problems"])


def test_scanner_outside_window_cannot_be_closed(triage_ctx):
    rep = mutate(triage_ctx, "S6", lambda r: r.update(classification="FALSE_POSITIVE_BENIGN_ACTIVITY", disposition="CLOSE_WITH_TUNING"))
    assert not rep["passed"]


def test_missing_context_source_fails(triage_ctx):
    rep = mutate(triage_ctx, "S6", lambda r: r.update(context_checked=["asset_inventory"]))
    assert any("change_calendar" in p for p in rep["problems"])


@pytest.mark.parametrize("change,needle", [
    (lambda t: t["match"].pop("TargetUserName"), "narrow"),
    (lambda t: t["match"].update(TargetUserName="svc-*"), "wildcards"),
    (lambda t: t.update(valid_until="2027-12-31T00:00:00Z"), "at most 90 days"),
])
def test_broad_tuning_fails_for_service_account(triage_ctx, change, needle):
    rep = mutate(triage_ctx, "F1", lambda r: change(r["tuning"]))
    assert any(needle in p for p in rep["problems"]), rep["problems"]


def test_scanner_tuning_must_stay_inside_change_window(triage_ctx):
    rep = mutate(triage_ctx, "F2", lambda r: r["tuning"].update(valid_from="2026-03-02T00:00:00Z", valid_until="2026-03-09T00:00:00Z"))
    assert any("bounded to the approved change window" in p for p in rep["problems"])


def test_service_account_needs_root_cause_fix(triage_ctx):
    rep = mutate(triage_ctx, "F1", lambda r: r.pop("root_cause_fix"))
    assert any("root_cause_fix" in p for p in rep["problems"])


def test_unrelated_or_unknown_evidence_fails(triage_ctx):
    rep = mutate(triage_ctx, "S1", lambda r: r["evidence"].__setitem__(0, {"event_id": "evt-009999", "observation": "an event that does not exist at all"}))
    assert any("do not exist" in p for p in rep["problems"])
    rep = mutate(triage_ctx, "S1", lambda r: r["evidence"].__setitem__(0, {"event_id": "evt-000001", "observation": "svc-backup event unrelated to this alert"}))
    assert any("unrelated" in p for p in rep["problems"])


def test_schema_violations_are_reported(triage_ctx):
    rep = mutate(triage_ctx, "S1", lambda r: r.update(rationale="too short", evidence=r["evidence"][:1], mitre_technique="T1059"))
    assert not rep["passed"] and sum(p.startswith("schema") for p in rep["problems"]) >= 3


def test_unknown_alert_id_fails(triage_ctx):
    alerts, events, labels, scenarios, records = triage_ctx
    rec = dict(records[0], alert_id="ALT-deadbeef")
    assert not check_records([rec], alerts, events, labels, scenarios)["records"][0]["passed"]
