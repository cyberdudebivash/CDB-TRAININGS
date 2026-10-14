"""Score alerts against the hidden scenario labels (precision / recall per scenario)."""
from __future__ import annotations

from collections import Counter

from .events import parse_ts


def alert_scenario(alert: dict, labels: dict[str, str], kinds: dict[str, str]) -> str:
    """Majority label of an alert's evidence; ties go to ATTACK scenarios, then to the lowest id (deterministic)."""
    counts = Counter(labels.get(e, "UNKNOWN") for e in alert["evidence"])
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kinds.get(kv[0]) != "ATTACK", kv[0]))
    return ranked[0][0]


def evaluate(result: dict, labels: dict[str, str], scenarios: list[dict]) -> dict:
    kinds = {s["id"]: s["kind"] for s in scenarios}
    first_event = {s["id"]: s.get("first_event") for s in scenarios}
    rows = {s["id"]: {"id": s["id"], "kind": s["kind"], "name": s["name"], "mitre": s.get("mitre"), "alerts": 0, "suppressed": 0,
                      "detected": None, "time_to_detect_s": None} for s in scenarios}
    for a in result["alerts"]:
        sid = alert_scenario(a, labels, kinds)
        if sid in rows:
            rows[sid]["alerts"] += 1
            if kinds[sid] == "ATTACK" and first_event.get(sid):
                ttd = int((parse_ts(a["fired_at"]) - parse_ts(first_event[sid])).total_seconds())
                if rows[sid]["time_to_detect_s"] is None or ttd < rows[sid]["time_to_detect_s"]:
                    rows[sid]["time_to_detect_s"] = ttd
    suppressed_tp = 0
    for a in result.get("suppressed", []):
        sid = alert_scenario(a, labels, kinds)
        if sid in rows:
            rows[sid]["suppressed"] += 1
            if kinds[sid] == "ATTACK":
                suppressed_tp += 1
    attack = [r for r in rows.values() if r["kind"] == "ATTACK"]
    for r in attack:
        r["detected"] = r["alerts"] > 0
    tp_alerts = sum(r["alerts"] for r in attack)
    fp_alerts = sum(r["alerts"] for r in rows.values() if r["kind"] == "BENIGN")
    total = tp_alerts + fp_alerts
    detected = sum(1 for r in attack if r["detected"])
    return {
        "summary": {
            "attack_scenarios": len(attack),
            "detected": detected,
            "missed": [r["id"] for r in attack if not r["detected"]],
            "recall": round(detected / len(attack), 3) if attack else None,
            "alerts": total,
            "true_positive_alerts": tp_alerts,
            "false_positive_alerts": fp_alerts,
            "precision": round(tp_alerts / total, 3) if total else None,
            "suppressed_alerts": len(result.get("suppressed", [])),
            "suppressed_true_positive_alerts": suppressed_tp,
        },
        "scenarios": [rows[s["id"]] for s in scenarios],
        "false_positives_by_scenario": {r["id"]: r["alerts"] for r in rows.values() if r["kind"] == "BENIGN" and r["alerts"]},
    }


def format_report(rep: dict) -> str:
    s = rep["summary"]
    lines = [
        f"Recall    : {s['detected']}/{s['attack_scenarios']} attack scenarios detected"
        + (f"  (missed: {', '.join(s['missed'])})" if s["missed"] else ""),
        f"Precision : {s['true_positive_alerts']}/{s['alerts']} alerts are true positives" if s["alerts"] else "Precision : no alerts raised",
        f"False-positive alerts: {s['false_positive_alerts']}   by scenario: {rep['false_positives_by_scenario'] or 'none'}",
        f"Suppressed alerts: {s['suppressed_alerts']}  (of which hid real attacks: {s['suppressed_true_positive_alerts']})",
        "",
        f"{'id':4} {'kind':7} {'alerts':>6} {'supp':>5} {'detected':>9} {'ttd(s)':>7}  scenario",
    ]
    for r in rep["scenarios"]:
        det = "-" if r["detected"] is None else ("YES" if r["detected"] else "NO")
        ttd = "-" if r["time_to_detect_s"] is None else str(r["time_to_detect_s"])
        lines.append(f"{r['id']:4} {r['kind']:7} {r['alerts']:>6} {r['suppressed']:>5} {det:>9} {ttd:>7}  {r['name']}")
    return "\n".join(lines)
