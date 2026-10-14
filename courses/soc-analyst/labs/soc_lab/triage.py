"""Structural checks for analyst triage records.

The checker verifies things that can be verified objectively: schema, that cited events exist and relate to the alert,
that the required context sources were consulted, that the decision is one a defensible analyst could reach, and that any
proposed suppression is narrow and expires. It does NOT grade the quality of the written rationale - a human reviewer
does that with the rubric (assessments/m04/rubric.yaml).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .evaluate import alert_scenario
from .events import parse_ts
from .sigma_lite import MAX_EXCEPTION_DAYS

CLASSIFICATIONS = ["TRUE_POSITIVE_ATTACK", "TRUE_POSITIVE_COMPROMISE", "FALSE_POSITIVE_BENIGN_ACTIVITY",
                   "FALSE_POSITIVE_MISCONFIGURATION", "SUSPICIOUS_NEEDS_MORE_DATA"]
DISPOSITIONS = ["ESCALATE_IR", "CONTAIN_ACCOUNT_RESET", "BLOCK_SOURCE", "CLOSE_WITH_TUNING", "CLOSE_NO_ACTION", "WATCHLIST"]
CONTEXT_SOURCES = ["asset_inventory", "user_directory", "change_calendar", "threat_intel", "success_events"]

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "SOC triage record (CDB Academy SOC-M04)",
    "type": "object",
    "required": ["alert_id", "classification", "severity", "confidence", "evidence", "context_checked", "disposition", "rationale", "next_steps"],
    "additionalProperties": False,
    "properties": {
        "alert_id": {"type": "string", "pattern": "^ALT-[0-9a-f]{8}$"},
        "classification": {"enum": CLASSIFICATIONS},
        "severity": {"enum": ["low", "medium", "high", "critical"]},
        "confidence": {"enum": ["low", "medium", "high"]},
        "mitre_technique": {"type": ["string", "null"], "pattern": "^T1110(\\.00[1-4])?$"},
        "evidence": {"type": "array", "minItems": 3, "items": {
            "type": "object", "required": ["event_id", "observation"], "additionalProperties": False,
            "properties": {"event_id": {"type": "string", "pattern": "^evt-\\d{6}$"}, "observation": {"type": "string", "minLength": 15}}}},
        "context_checked": {"type": "array", "uniqueItems": True, "items": {"enum": CONTEXT_SOURCES}},
        "disposition": {"enum": DISPOSITIONS},
        "rationale": {"type": "string", "minLength": 80},
        "root_cause_fix": {"type": "string", "minLength": 15},
        "tuning": {"type": "object", "required": ["rule", "match", "valid_from", "valid_until", "ticket", "owner", "reason"],
                   "additionalProperties": False,
                   "properties": {"rule": {"type": "string"}, "match": {"type": "object", "minProperties": 1},
                                  "valid_from": {"type": "string"}, "valid_until": {"type": "string"}, "ticket": {"type": "string"},
                                  "owner": {"type": "string"}, "reason": {"type": "string", "minLength": 20}}},
        "next_steps": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 8}},
    },
}
_VALIDATOR = Draft202012Validator(SCHEMA)


def load_records(path: str | Path) -> list[dict]:
    p = Path(path)
    files = sorted(p.glob("*.json")) if p.is_dir() else [p]
    out = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        out += data if isinstance(data, list) else [data]
    return out


def check_records(records: list[dict], alerts: list[dict], events: list[dict], labels: dict[str, str], scenarios: list[dict]) -> dict:
    kinds = {s["id"]: s["kind"] for s in scenarios}
    expect = {s["id"]: s["triage_expectation"] for s in scenarios if "triage_expectation" in s}
    by_alert = {a["alert_id"]: a for a in alerts}
    by_event = {e["event_id"]: e for e in events}
    results = []
    for rec in records:
        problems: list[str] = []
        notes: list[str] = []
        aid = rec.get("alert_id", "<missing>")
        for err in sorted(_VALIDATOR.iter_errors(rec), key=lambda e: list(e.path)):
            problems.append(f"schema: {'/'.join(map(str, err.path)) or '<root>'}: {err.message}")
        alert = by_alert.get(aid)
        sid = None
        if alert is None:
            problems.append("alert_id does not exist in the alerts file")
        elif not problems:
            sid = alert_scenario(alert, labels, kinds)
            ev_ids = {e["event_id"] for e in rec["evidence"]}
            unknown = sorted(ev_ids - set(by_event))
            if unknown:
                problems.append(f"evidence cites events that do not exist: {unknown}")
            else:
                ips = {by_event[e]["IpAddress"] for e in alert["evidence"] if "IpAddress" in by_event[e]}
                users = {by_event[e]["TargetUserName"] for e in alert["evidence"]}
                related = [e for e in ev_ids if e in alert["evidence"] or by_event[e].get("IpAddress") in ips or by_event[e].get("TargetUserName") in users]
                if len(related) < len(ev_ids):
                    problems.append("evidence cites events unrelated to the alert (different source and account)")
            exp = expect.get(sid)
            if exp is None:
                notes.append("no automated expectation for this alert; a human reviewer grades it against the rubric")
            else:
                if rec["classification"] not in exp["classification"]:
                    problems.append(f"classification {rec['classification']} is not defensible here (expected one of {exp['classification']})")
                if rec["disposition"] not in exp["disposition"]:
                    problems.append(f"disposition {rec['disposition']} is not defensible here (expected one of {exp['disposition']})")
                for src in exp.get("must_check", []):
                    if src not in rec["context_checked"]:
                        problems.append(f"context source '{src}' was not consulted")
                if exp.get("mitre") and rec.get("mitre_technique") not in exp["mitre"]:
                    problems.append(f"mitre_technique should be one of {exp['mitre']}")
                if exp.get("must_cite_success_event"):
                    ips = {by_event[e]["IpAddress"] for e in alert["evidence"]}
                    ok = [e for e in ev_ids if by_event[e]["EventID"] == 4624 and by_event[e].get("IpAddress") in ips]
                    if not ok:
                        problems.append("a successful logon (4624) from the attacking address must be cited as evidence of compromise")
                if exp.get("must_have_root_cause_fix") and not rec.get("root_cause_fix"):
                    problems.append("root_cause_fix is required: suppression alone does not fix a stale credential")
                if rec["disposition"] == "CLOSE_WITH_TUNING":
                    problems += _check_tuning(rec.get("tuning"), exp)
        results.append({"alert_id": aid, "scenario": sid, "passed": not problems, "problems": problems, "notes": notes})
    missing = []
    for sid, exp in sorted(expect.items()):
        covered = any(r["scenario"] == sid for r in results)
        if not covered:
            missing.append(sid)
    return {"records": results, "passed": sum(1 for r in results if r["passed"]), "total": len(results), "scenarios_without_record": missing}


def _check_tuning(tuning: dict | None, exp: dict) -> list[str]:
    if not tuning:
        return ["disposition CLOSE_WITH_TUNING requires a tuning section"]
    p = []
    for k in exp.get("tuning_must_match", []):
        if k not in tuning["match"]:
            p.append(f"tuning.match must pin '{k}' (a suppression must be as narrow as the evidence)")
    if any(ch in str(v) for v in tuning["match"].values() for ch in "*?"):
        p.append("tuning.match must not use wildcards")
    try:
        vf, vu = parse_ts(tuning["valid_from"]), parse_ts(tuning["valid_until"])
        if vu - vf > dt.timedelta(days=MAX_EXCEPTION_DAYS) or vu <= vf:
            p.append(f"tuning validity must be positive and at most {MAX_EXCEPTION_DAYS} days")
        win = exp.get("tuning_window")
        if win and (vf < parse_ts(win[0]) or vu > parse_ts(win[1])):
            p.append(f"tuning must be bounded to the approved change window {win[0]} - {win[1]}")
    except (ValueError, KeyError):
        p.append("tuning.valid_from / valid_until must be ISO timestamps")
    if exp.get("tuning_ticket") and tuning.get("ticket") != exp["tuning_ticket"]:
        p.append(f"tuning.ticket should reference the approving change ({exp['tuning_ticket']})")
    return p


def format_report(rep: dict) -> str:
    lines = [f"Triage records passed: {rep['passed']}/{rep['total']}"]
    for r in rep["records"]:
        lines.append(f"  {r['alert_id']} ({r['scenario']}): {'PASS' if r['passed'] else 'FAIL'}")
        lines += [f"      - {p}" for p in r["problems"]]
        lines += [f"      (note) {n}" for n in r.get("notes", [])]
    if rep["scenarios_without_record"]:
        lines.append(f"Scenarios still needing a triage record: {', '.join(rep['scenarios_without_record'])}")
    return "\n".join(lines)
