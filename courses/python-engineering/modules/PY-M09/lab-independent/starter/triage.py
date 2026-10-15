"""triage - collapse a stream of security alerts into incidents and rank them (PY-M09 independent lab, STARTER).

Everything here WORKS and is the specification of the answers: your job (../README.md) is to make it scale, keep every answer identical, keep the core free of input and output,
and prove it with tests of your own (test_budget.py). Edit this file and add test_budget.py next to it. Standard library only.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

SEVERITIES = (1, 2, 3, 4, 5)


class AlertFormatError(ValueError):
    """A line of an alert file is not a valid alert; `line` is its 1-based number."""

    def __init__(self, line: int, reason: str) -> None:
        super().__init__(f"line {line}: {reason}")
        self.line = line
        self.reason = reason


@dataclass(frozen=True, slots=True)
class Alert:
    id: int
    ts: int            # seconds since the epoch
    source: str
    rule: str
    host: str
    severity: int      # 1 (low) to 5 (critical)
    message: str


@dataclass(frozen=True, slots=True)
class Incident:
    key: tuple[str, str, str, str]       # (source, rule, host, normalized message)
    first_ts: int
    last_ts: int
    count: int
    max_severity: int
    ids: tuple[int, ...]                 # ids of its alerts in (ts, id) order


@dataclass(frozen=True, slots=True)
class Triage:
    incidents: tuple[Incident, ...]
    top: tuple[Incident, ...]
    summary: dict


# ------------------------------------------------------------------------------------------------------------------------------------------------ core
def normalize(message: str) -> str:
    """The message in lower case, with every run of whitespace turned into one space (and the ends trimmed), and every run of digits (any script) replaced by '#'."""
    text = " ".join(message.lower().split())
    return re.sub(re.compile(r"\d+"), "#", text)


def collapse(alerts: Iterable[Alert], window: int) -> list[Incident]:
    """Group the alerts into incidents. Process them in (ts, id) order (a stable sort: equal pairs keep their input order). An alert joins the most recent incident with the same
    key (source, rule, host, normalized message) if its ts is at most `window` seconds after that incident's last_ts; otherwise it starts a new incident. The incidents come back
    ordered by (first_ts, id of the first alert). `window` must be a non-negative int (ValueError otherwise); an alert whose severity is not 1 to 5 is a ValueError."""
    if isinstance(window, bool) or not isinstance(window, int) or window < 0:
        raise ValueError("window must be a non-negative int")
    ordered = sorted(alerts, key=lambda a: (a.ts, a.id))
    incidents: list[Incident] = []
    for a in ordered:
        if a.severity not in SEVERITIES:
            raise ValueError(f"severity must be 1 to 5: {a.severity}")
        key = (a.source, a.rule, a.host, normalize(a.message))
        joined = False
        for i in range(len(incidents) - 1, -1, -1):
            inc = incidents[i]
            if inc.key == key:
                if a.ts - inc.last_ts <= window:
                    incidents[i] = Incident(key, inc.first_ts, a.ts, inc.count + 1, max(inc.max_severity, a.severity), inc.ids + (a.id,))
                    joined = True
                break
        if not joined:
            incidents.append(Incident(key, a.ts, a.ts, 1, a.severity, (a.id,)))
    return sorted(incidents, key=lambda inc: (inc.first_ts, inc.ids[0]))


def rank(incidents: Iterable[Incident], n: int) -> list[Incident]:
    """The `n` most urgent incidents: highest max_severity first, then the largest count, then the earliest first_ts, then the smallest first id; incidents that tie on all four
    keep their input order. ValueError for a negative or non-int n."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative int")
    remaining = list(incidents)
    chosen = []
    while remaining and len(chosen) < n:
        best = remaining[0]
        for inc in remaining:
            if (-inc.max_severity, -inc.count, inc.first_ts, inc.ids[0]) < (-best.max_severity, -best.count, best.first_ts, best.ids[0]):
                best = inc
        chosen.append(best)
        remaining.remove(best)
    return chosen


def summarize(incidents: Iterable[Incident]) -> dict:
    """{'incidents': number, 'alerts': total count, 'by_severity': {1: n, ..., 5: n} (all five keys, incidents per max_severity),
    'by_rule': [(rule, incidents, alerts), ...] ordered by alerts descending, then rule}."""
    items = list(incidents)
    rules = sorted({inc.key[1] for inc in items})
    by_rule = []
    for rule in rules:
        mine = [inc for inc in items if inc.key[1] == rule]
        by_rule.append((rule, len(mine), sum(inc.count for inc in mine)))
    by_rule.sort(key=lambda row: (-row[2], row[0]))
    return {
        "incidents": len(items),
        "alerts": sum(inc.count for inc in items),
        "by_severity": {s: len([inc for inc in items if inc.max_severity == s]) for s in SEVERITIES},
        "by_rule": by_rule,
    }


def triage(alerts: Iterable[Alert], window: int = 300, top: int = 5) -> Triage:
    """The whole analysis: collapse, rank the `top` most urgent incidents, summarize."""
    incidents = collapse(alerts, window)
    return Triage(tuple(incidents), tuple(rank(incidents, top)), summarize(incidents))


def render(result: Triage) -> str:
    """The text report: a header line 'incidents: N alerts: M', one line 'severity S: N' for S = 1 to 5, one line 'rule NAME: I incidents, A alerts' per entry of by_rule, a line
    'top:' and one line '#K [first_ts-last_ts] sev S x COUNT source/rule@host: message' per ranked incident (K from 1), the message being the normalized one. Every line ends
    with a newline."""
    text = ""
    text += f"incidents: {result.summary['incidents']} alerts: {result.summary['alerts']}\n"
    for s in SEVERITIES:
        text += f"severity {s}: {result.summary['by_severity'][s]}\n"
    for rule, incidents, alerts in result.summary["by_rule"]:
        text += f"rule {rule}: {incidents} incidents, {alerts} alerts\n"
    text += "top:\n"
    for k, inc in enumerate(result.top, start=1):
        source, rule, host, message = inc.key
        text += f"#{k} [{inc.first_ts}-{inc.last_ts}] sev {inc.max_severity} x {inc.count} {source}/{rule}@{host}: {message}\n"
    return text


# ------------------------------------------------------------------------------------------------------------------------------------------------ edge
def read_alerts(path: str) -> Iterator[Alert]:
    """Alerts from a UTF-8 JSON Lines file, one object per non-blank line with the keys id, ts, source, rule, host, severity, message. Lazy: nothing is opened before the first
    alert is requested, and the file is closed when the generator ends or is closed. A line that is not a JSON object with exactly those keys and types (id, ts and severity
    ints but not bools; the others str) raises AlertFormatError with its line number (blank lines are skipped but counted)."""
    keys = {"id": int, "ts": int, "severity": int, "source": str, "rule": str, "host": str, "message": str}
    with open(path, encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AlertFormatError(number, f"not JSON ({exc.msg})") from None
            if not isinstance(data, dict) or set(data) != set(keys):
                raise AlertFormatError(number, "needs exactly the keys " + ", ".join(sorted(keys)))
            for name, kind in keys.items():
                if isinstance(data[name], bool) or not isinstance(data[name], kind):
                    raise AlertFormatError(number, f"{name} must be {kind.__name__}")
            yield Alert(data["id"], data["ts"], data["source"], data["rule"], data["host"], data["severity"], data["message"])
