"""Command-line entry point:  python -m soc_lab <command> ...   (run from courses/soc-analyst/labs)"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import evaluate as ev
from . import triage as tr
from .events import enrich, read_jsonl, write_jsonl
from .generator import DEFAULT_SEEDS, generate
from .sigma_lite import RuleError, lint_exceptions, load_rules, run_rules


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_generate(a) -> int:
    ds = generate(a.profile, a.seed)
    out = Path(a.out)
    write_jsonl(out / "events.jsonl", ds.events)
    _write_json(out / "context.json", ds.context)
    if a.with_truth:
        _write_json(out / "truth" / "labels.json", ds.labels)
        _write_json(out / "truth" / "scenarios.json", ds.scenarios)
    print(f"generated {len(ds.events)} events (profile={ds.profile}, seed={ds.seed}) -> {out}" + (" with truth/" if a.with_truth else ""))
    return 0


def cmd_enrich(a) -> int:
    rows = enrich(read_jsonl(a.events), json.loads(Path(a.context).read_text(encoding="utf-8")))
    write_jsonl(a.out, rows)
    print(f"enriched {len(rows)} events -> {a.out} (added SrcNet24, SrcRole)")
    return 0


def _load_exceptions(path: str | None) -> list[dict]:
    if not path:
        return []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    return data["exceptions"] if isinstance(data, dict) else data


def cmd_detect(a) -> int:
    try:
        rs = load_rules(a.rules)
        result = run_rules(rs, read_jsonl(a.events), _load_exceptions(a.exceptions))
    except RuleError as exc:
        print(f"RULE ERROR: {exc}", file=sys.stderr)
        return 2
    _write_json(Path(a.out), result)
    st = result["stats"]
    print(f"{st['events']} events, {st['rules']} rules -> {st['alerts']} alerts, {st['suppressed']} suppressed -> {a.out}")
    return 0


def _truth(a):
    d = Path(a.truth)
    return json.loads((d / "labels.json").read_text(encoding="utf-8")), json.loads((d / "scenarios.json").read_text(encoding="utf-8"))


def cmd_evaluate(a) -> int:
    labels, scenarios = _truth(a)
    rep = ev.evaluate(json.loads(Path(a.alerts).read_text(encoding="utf-8")), labels, scenarios)
    print(ev.format_report(rep))
    if a.json:
        _write_json(Path(a.json), rep)
    return 0


def cmd_lint(a) -> int:
    try:
        rs = load_rules(a.rules)
    except RuleError as exc:
        print(f"RULE ERROR: {exc}", file=sys.stderr)
        return 2
    problems = lint_exceptions(_load_exceptions(a.exceptions), rs) if a.exceptions else []
    print(f"rules OK: {len(rs.detections)} detection, {len(rs.correlations)} correlation")
    for p in problems:
        print(f"EXCEPTION PROBLEM: {p}", file=sys.stderr)
    return 2 if problems else 0


def cmd_triage(a) -> int:
    labels, scenarios = _truth(a)
    alerts = json.loads(Path(a.alerts).read_text(encoding="utf-8"))["alerts"]
    rep = tr.check_records(tr.load_records(a.records), alerts, read_jsonl(a.events), labels, scenarios)
    print(tr.format_report(rep))
    return 0 if rep["passed"] == rep["total"] and not rep["scenarios_without_record"] else 1


def cmd_alerts(a) -> int:
    data = json.loads(Path(a.alerts).read_text(encoding="utf-8"))
    print(f"{'alert_id':13} {'first_seen':20} {'last_seen':20} {'metric':>6} {'evid':>5}  rule / group")
    for x in data["alerts"]:
        group = ", ".join(f"{k}={v}" for k, v in x["group"].items()) or "-"
        print(f"{x['alert_id']:13} {x['first_seen']:20} {x['last_seen']:20} {x['metric']:>6} {len(x['evidence']):>5}  {x['rule_title']} [{group}]")
    for x in data.get("suppressed", []):
        print(f"{x['alert_id']:13} {x['first_seen']:20} {x['last_seen']:20} {x['metric']:>6} {len(x['evidence']):>5}  SUPPRESSED by {x['suppressed_by']}: {x['rule_title']}")
    return 0


def cmd_inspect(a) -> int:
    rows = read_jsonl(a.events)
    if a.event_id:
        rows = [r for r in rows if r["event_id"] in set(a.event_id)]
    if a.ip:
        rows = [r for r in rows if r.get("IpAddress") == a.ip]
    if a.user:
        rows = [r for r in rows if r.get("TargetUserName") == a.user]
    if a.event:
        rows = [r for r in rows if r.get("EventID") == a.event]
    shown = rows[: a.limit]
    for r in shown:
        print(f"{r['event_id']} {r['@timestamp']} {r['EventID']} type={r.get('LogonType')} user={r.get('TargetUserName')} src={r.get('IpAddress')} "
              f"ws={r.get('WorkstationName')} status={r.get('Status', '-')}/{r.get('SubStatus', '-')}")
    print(f"-- {len(shown)} of {len(rows)} matching events shown")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="soc_lab", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="generate synthetic telemetry")
    g.add_argument("--profile", choices=sorted(DEFAULT_SEEDS), default="guided")
    g.add_argument("--seed", type=int, default=None, help="default is the profile's published practice seed")
    g.add_argument("--out", required=True)
    g.add_argument("--with-truth", action="store_true", help="also write truth/labels.json and truth/scenarios.json")
    g.set_defaults(fn=cmd_generate)
    e = sub.add_parser("enrich", help="add SrcNet24 and SrcRole from the asset inventory")
    e.add_argument("--events", required=True); e.add_argument("--context", required=True); e.add_argument("--out", required=True)
    e.set_defaults(fn=cmd_enrich)
    d = sub.add_parser("detect", help="run Sigma rules over events")
    d.add_argument("--rules", nargs="+", required=True); d.add_argument("--events", required=True)
    d.add_argument("--exceptions"); d.add_argument("--out", required=True)
    d.set_defaults(fn=cmd_detect)
    v = sub.add_parser("evaluate", help="score alerts against truth")
    v.add_argument("--alerts", required=True); v.add_argument("--truth", required=True); v.add_argument("--json")
    v.set_defaults(fn=cmd_evaluate)
    l = sub.add_parser("lint", help="validate rule files (and an exceptions file)")
    l.add_argument("--rules", nargs="+", required=True); l.add_argument("--exceptions")
    l.set_defaults(fn=cmd_lint)
    t = sub.add_parser("check-triage", help="check triage records")
    t.add_argument("--records", required=True); t.add_argument("--alerts", required=True)
    t.add_argument("--events", required=True); t.add_argument("--truth", required=True)
    t.set_defaults(fn=cmd_triage)
    al = sub.add_parser("alerts", help="list alerts from a detect run")
    al.add_argument("--alerts", required=True)
    al.set_defaults(fn=cmd_alerts)
    ins = sub.add_parser("inspect", help="filter and print events (pivot on source, account or event id)")
    ins.add_argument("--events", required=True)
    ins.add_argument("--ip"); ins.add_argument("--user"); ins.add_argument("--event", type=int)
    ins.add_argument("--event-id", nargs="+"); ins.add_argument("--limit", type=int, default=20)
    ins.set_defaults(fn=cmd_inspect)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
