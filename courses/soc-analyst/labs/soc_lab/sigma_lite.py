"""sigma_lite - a teaching evaluator for a documented subset of the Sigma 2.1.0 specification.

Supported (see docs/research R-023 and the Sigma specifications):
  Rules        : ``title``, ``id``, ``name``, ``logsource`` (validated, not used for routing), ``detection``
                 with named selections (map = AND of fields, list of maps = OR) and ``condition``.
  Modifiers    : contains, startswith, endswith, all, exists, re, cidr, lt, lte, gt, gte  (plain values may use * and ?)
  Condition    : and / or / not / ( ) / "1 of X*" / "all of X*" / "1 of them" / "all of them"
  Correlation  : ``correlation.type`` event_count | value_count, ``rules`` (by name or id), ``group-by``,
                 ``timespan`` (Ns/Nm/Nh/Nd) and a single-criterion ``condition`` (gt/gte/lt/lte/eq/neq;
                 value_count needs ``field``).

NOT supported (rejected with RuleError - fail closed, never silently ignored): other modifiers (base64, windash, expand,
fieldref ...), temporal / temporal_ordered / value_sum / value_avg / value_percentile correlations, aliases, ``generate``
other than the default, multiple conditions, placeholders.

Alert semantics (documented choices - real SIEMs differ):
  * Window: for each event E of a group the window is (E.time - timespan, E.time].
  * An alert fires at the first event whose window satisfies the condition. While the condition stays true for that group the
    alert is extended (evidence grows, ``last_seen`` moves); when it becomes false the group re-arms.
  * Rules referenced by a correlation rule do not alert on their own.
  * Exceptions suppress an alert only if EVERY evidence event matches the exception and the alert lies wholly inside the
    exception's validity window. Suppressed alerts are reported, never silently dropped.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .events import parse_ts, fmt_ts

SUPPORTED_MODIFIERS = {"contains", "startswith", "endswith", "all", "exists", "re", "cidr", "lt", "lte", "gt", "gte"}
SUPPORTED_CORR_TYPES = {"event_count", "value_count"}
CORR_OPS = {"gt", "gte", "lt", "lte", "eq", "neq"}
TIMESPAN = re.compile(r"^(\d+)([smhd])$")
MAX_EXCEPTION_DAYS = 90


class RuleError(ValueError):
    """Raised for invalid or unsupported rules. The evaluator never guesses."""


# ------------------------------------------------------------------------------------------------ field matching


@dataclass
class FieldMatcher:
    field: str
    modifiers: tuple[str, ...]
    values: list[Any]

    def matches(self, event: dict) -> bool:
        present = self.field in event and event[self.field] is not None
        if "exists" in self.modifiers:
            want = bool(self.values[0])
            return present == want
        results = [self._match_one(event.get(self.field), present, v) for v in self.values]
        return all(results) if "all" in self.modifiers else any(results)

    def _match_one(self, actual: Any, present: bool, expected: Any) -> bool:
        if expected is None:
            return not present
        if not present:
            return False
        mods = [m for m in self.modifiers if m not in ("all",)]
        if "cidr" in mods:
            try:
                return ipaddress.ip_address(str(actual)) in ipaddress.ip_network(str(expected), strict=False)
            except ValueError:
                return False
        for op in ("lt", "lte", "gt", "gte"):
            if op in mods:
                try:
                    a, e = float(actual), float(expected)
                except (TypeError, ValueError):
                    return False
                return {"lt": a < e, "lte": a <= e, "gt": a > e, "gte": a >= e}[op]
        text, pat = str(actual), str(expected)
        if "re" in mods:
            return re.search(pat, text) is not None
        if "contains" in mods:
            pat = f"*{pat}*"
        elif "startswith" in mods:
            pat = f"{pat}*"
        elif "endswith" in mods:
            pat = f"*{pat}"
        regex = "^" + "".join(".*" if c == "*" else "." if c == "?" else re.escape(c) for c in pat) + "$"
        return re.match(regex, text, re.IGNORECASE) is not None


def _build_selection(name: str, body: Any) -> list[list[FieldMatcher]]:
    """Return an OR-list of AND-lists of field matchers."""
    if isinstance(body, dict):
        alternatives = [body]
    elif isinstance(body, list) and all(isinstance(x, dict) for x in body):
        alternatives = body
    else:
        raise RuleError(f"selection '{name}': keyword lists are not supported (use field maps)")
    out = []
    for alt in alternatives:
        matchers = []
        for key, raw in alt.items():
            field_name, *mods = str(key).split("|")
            bad = [m for m in mods if m not in SUPPORTED_MODIFIERS]
            if bad:
                raise RuleError(f"selection '{name}': unsupported modifier(s) {bad} on field '{field_name}'")
            if not field_name:
                raise RuleError(f"selection '{name}': empty field name")
            values = raw if isinstance(raw, list) else [raw]
            if "all" in mods and len(values) < 2:
                raise RuleError(f"selection '{name}': 'all' modifier needs a list of at least two values")
            matchers.append(FieldMatcher(field_name, tuple(mods), values))
        out.append(matchers)
    return out


# ------------------------------------------------------------------------------------------------ condition parser

TOKEN = re.compile(r"\(|\)|[^\s()]+")


class _Cond:
    """Recursive-descent parser. Precedence (low to high): or, and, not, 'x of', parentheses."""

    def __init__(self, text: str, names: list[str]):
        self.tokens = TOKEN.findall(text)
        self.pos = 0
        self.names = names
        if not self.tokens:
            raise RuleError("empty condition")

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def parse(self):
        node = self.p_or()
        if self.peek() is not None:
            raise RuleError(f"unexpected token '{self.peek()}' in condition")
        return node

    def p_or(self):
        node = self.p_and()
        while (self.peek() or "").lower() == "or":
            self.take()
            node = ("or", node, self.p_and())
        return node

    def p_and(self):
        node = self.p_not()
        while (self.peek() or "").lower() == "and":
            self.take()
            node = ("and", node, self.p_not())
        return node

    def p_not(self):
        if (self.peek() or "").lower() == "not":
            self.take()
            return ("not", self.p_not())
        return self.p_of()

    def p_of(self):
        tok = self.peek()
        if tok and tok.lower() in ("1", "all") and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].lower() == "of":
            quant = self.take().lower()
            self.take()  # 'of'
            pattern = self.take()
            if pattern is None:
                raise RuleError("'of' needs a selection pattern or 'them'")
            names = [n for n in self.names if not n.startswith("_")] if pattern.lower() == "them" else [
                n for n in self.names if re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), n)]
            if not names:
                raise RuleError(f"pattern '{pattern}' matches no selection")
            return ("any" if quant == "1" else "every", names)
        return self.p_atom()

    def p_atom(self):
        tok = self.take()
        if tok == "(":
            node = self.p_or()
            if self.take() != ")":
                raise RuleError("missing ')' in condition")
            return node
        if tok is None or tok == ")":
            raise RuleError("unexpected end of condition")
        if tok not in self.names:
            raise RuleError(f"condition references unknown selection '{tok}'")
        return ("sel", tok)


def _eval(node, sel_results: dict[str, bool]) -> bool:
    kind = node[0]
    if kind == "sel":
        return sel_results[node[1]]
    if kind == "not":
        return not _eval(node[1], sel_results)
    if kind == "and":
        return _eval(node[1], sel_results) and _eval(node[2], sel_results)
    if kind == "or":
        return _eval(node[1], sel_results) or _eval(node[2], sel_results)
    if kind == "any":
        return any(sel_results[n] for n in node[1])
    if kind == "every":
        return all(sel_results[n] for n in node[1])
    raise AssertionError(kind)


# ------------------------------------------------------------------------------------------------ rules


@dataclass
class DetectionRule:
    title: str
    rule_id: str
    name: str
    level: str
    tags: list[str]
    selections: dict[str, list[list[FieldMatcher]]]
    condition: Any
    source: str = ""
    referenced: bool = False

    def matches(self, event: dict) -> bool:
        results = {n: any(all(m.matches(event) for m in alt) for alt in alts) for n, alts in self.selections.items()}
        return _eval(self.condition, results)


@dataclass
class CorrelationRule:
    title: str
    rule_id: str
    name: str
    level: str
    tags: list[str]
    ctype: str
    rule_refs: list[str]
    group_by: list[str]
    timespan: dt.timedelta
    op: str
    threshold: int
    count_field: str | None
    source: str = ""


@dataclass
class RuleSet:
    detections: dict[str, DetectionRule] = field(default_factory=dict)  # by canonical key (id)
    correlations: dict[str, CorrelationRule] = field(default_factory=dict)
    alias: dict[str, str] = field(default_factory=dict)  # name/id -> canonical id

    def resolve(self, ref: str) -> str:
        if ref not in self.alias:
            raise RuleError(f"rule reference '{ref}' not found (by id or name)")
        return self.alias[ref]

    def find(self, ref: str):
        key = self.resolve(ref)
        return self.detections.get(key) or self.correlations[key]


def _timespan(text: Any) -> dt.timedelta:
    m = TIMESPAN.match(str(text))
    if not m:
        raise RuleError(f"invalid timespan '{text}' (use Ns, Nm, Nh or Nd)")
    n, unit = int(m.group(1)), m.group(2)
    if n <= 0:
        raise RuleError("timespan must be positive")
    return dt.timedelta(**{{"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}[unit]: n})


def _ident(doc: dict, source: str, index: int) -> tuple[str, str]:
    name = str(doc.get("name") or "")
    rid = str(doc.get("id") or name or f"{Path(source).stem}#{index}")
    return rid, name


def parse_documents(docs: list[dict], source: str = "<memory>") -> RuleSet:
    rs = RuleSet()
    for i, doc in enumerate(docs):
        if not isinstance(doc, dict):
            raise RuleError(f"{source}: document {i} is not a mapping")
        title = doc.get("title")
        if not title or len(str(title)) > 256:
            raise RuleError(f"{source}: document {i} needs a title (max 256 characters)")
        rid, name = _ident(doc, source, i)
        for key in sorted({rid, name} - {""}):
            if key in rs.alias:
                raise RuleError(f"{source}: duplicate rule id/name '{key}'")
            rs.alias[key] = rid
        level = str(doc.get("level", "medium"))
        tags = [str(t) for t in doc.get("tags", [])]
        if "correlation" in doc:
            c = doc["correlation"]
            if not isinstance(c, dict):
                raise RuleError(f"{source}: '{title}': correlation must be a mapping")
            ctype = c.get("type")
            if ctype not in SUPPORTED_CORR_TYPES:
                raise RuleError(f"{source}: '{title}': correlation type '{ctype}' is not supported (supported: {sorted(SUPPORTED_CORR_TYPES)})")
            extra = set(c) - {"type", "rules", "group-by", "timespan", "condition"}
            if extra:
                raise RuleError(f"{source}: '{title}': unsupported correlation attribute(s) {sorted(extra)}")
            refs = c.get("rules")
            refs = [refs] if isinstance(refs, str) else refs
            if not refs or not all(isinstance(r, str) for r in refs):
                raise RuleError(f"{source}: '{title}': correlation.rules must list rule ids or names")
            group_by = c.get("group-by")
            if not group_by or not isinstance(group_by, list):
                raise RuleError(f"{source}: '{title}': group-by must be a non-empty list (an ungrouped correlation counts the whole log)")
            cond = c.get("condition")
            if not isinstance(cond, dict):
                raise RuleError(f"{source}: '{title}': condition must be a mapping")
            ops = [k for k in cond if k in CORR_OPS]
            if len(ops) != 1:
                raise RuleError(f"{source}: '{title}': condition needs exactly one operator from {sorted(CORR_OPS)}")
            allowed = {ops[0]} | ({"field"} if ctype == "value_count" else set())
            if set(cond) - allowed:
                raise RuleError(f"{source}: '{title}': unexpected condition keys {sorted(set(cond) - allowed)}")
            if ctype == "value_count" and not cond.get("field"):
                raise RuleError(f"{source}: '{title}': value_count requires condition.field")
            if not isinstance(cond[ops[0]], int) or isinstance(cond[ops[0]], bool):
                raise RuleError(f"{source}: '{title}': condition value must be an integer")
            rs.correlations[rid] = CorrelationRule(str(title), rid, name, level, tags, ctype, refs, [str(g) for g in group_by],
                                                   _timespan(c.get("timespan")), ops[0], cond[ops[0]], cond.get("field"), source)
        else:
            det = doc.get("detection")
            if not isinstance(det, dict) or "condition" not in det:
                raise RuleError(f"{source}: '{title}': rule needs detection.condition (or a correlation section)")
            if not isinstance(det["condition"], str):
                raise RuleError(f"{source}: '{title}': only a single string condition is supported")
            if "logsource" not in doc or not isinstance(doc["logsource"], dict):
                raise RuleError(f"{source}: '{title}': logsource is required")
            if doc.get("generate") not in (None, False):
                raise RuleError(f"{source}: '{title}': 'generate' is not supported")
            if "timeframe" in det:
                raise RuleError(f"{source}: '{title}': 'timeframe' (legacy aggregation) is not supported; use a correlation rule")
            sels = {k: _build_selection(k, v) for k, v in det.items() if k != "condition"}
            if not sels:
                raise RuleError(f"{source}: '{title}': no selections defined")
            cond = _Cond(det["condition"], list(sels)).parse()
            rs.detections[rid] = DetectionRule(str(title), rid, name, level, tags, sels, cond, source)
    for corr in rs.correlations.values():
        for ref in corr.rule_refs:
            target = rs.find(ref)
            if isinstance(target, DetectionRule):
                target.referenced = True
            else:
                raise RuleError(f"'{corr.title}': chaining correlations is not supported")
    return rs


def load_rules(paths: list[str | Path]) -> RuleSet:
    """Load rule files (or directories of *.yml). Rule order is the sorted path order."""
    files: list[Path] = []
    for p in paths:
        p = Path(p)
        files += sorted(p.rglob("*.yml")) + sorted(p.rglob("*.yaml")) if p.is_dir() else [p]
    merged_docs: list[tuple[str, dict]] = []
    for f in files:
        try:
            docs = [d for d in yaml.safe_load_all(f.read_text(encoding="utf-8")) if d is not None]
        except yaml.YAMLError as exc:
            raise RuleError(f"{f}: invalid YAML: {exc}") from exc
        merged_docs += [(str(f), d) for d in docs]
    # parse all documents together so name references resolve across documents and files
    all_docs = [d for _s, d in merged_docs]
    rs = parse_documents(all_docs, source=", ".join(sorted({s for s, _ in merged_docs})) or "<none>")
    return rs


# ------------------------------------------------------------------------------------------------ execution


@dataclass
class Alert:
    alert_id: str
    rule_id: str
    rule_title: str
    level: str
    tags: list[str]
    group: dict[str, Any]
    fired_at: str
    first_seen: str
    last_seen: str
    metric: int
    evidence: list[str]
    suppressed_by: str | None = None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _cmp(op: str, a: int, b: int) -> bool:
    return {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b, "eq": a == b, "neq": a != b}[op]


def _alert_id(rule_id: str, group: dict, first: str) -> str:
    digest = hashlib.sha1(f"{rule_id}|{sorted(group.items())}|{first}".encode()).hexdigest()[:8]
    return f"ALT-{digest}"


def run_rules(rs: RuleSet, events: list[dict], exceptions: list[dict] | None = None) -> dict:
    """Evaluate all rules. Events must be time-ordered (the generator guarantees it; we verify)."""
    times = [parse_ts(e["@timestamp"]) for e in events]
    if any(times[i] > times[i + 1] for i in range(len(times) - 1)):
        raise RuleError("events are not sorted by @timestamp")
    alerts: list[Alert] = []
    matched_cache: dict[str, list[int]] = {}

    def matches_of(rule: DetectionRule) -> list[int]:
        if rule.rule_id not in matched_cache:
            matched_cache[rule.rule_id] = [i for i, e in enumerate(events) if rule.matches(e)]
        return matched_cache[rule.rule_id]

    for rule in rs.detections.values():
        if rule.referenced:
            continue
        for i in matches_of(rule):
            ts = events[i]["@timestamp"]
            alerts.append(Alert(_alert_id(rule.rule_id, {"event": events[i]["event_id"]}, ts), rule.rule_id, rule.title, rule.level,
                                rule.tags, {}, ts, ts, ts, 1, [events[i]["event_id"]]))

    for corr in rs.correlations.values():
        idx = sorted({i for ref in corr.rule_refs for i in matches_of(rs.detections[rs.resolve(ref)])})
        groups: dict[tuple, list[int]] = {}
        for i in idx:
            e = events[i]
            if any(g not in e or e[g] is None for g in corr.group_by):
                continue
            groups.setdefault(tuple(str(e[g]) for g in corr.group_by), []).append(i)
        for key in sorted(groups):
            window: deque[int] = deque()
            counter: dict[str, int] = {}
            active: Alert | None = None
            for i in groups[key]:
                t = times[i]
                window.append(i)
                if corr.ctype == "value_count":
                    v = events[i].get(corr.count_field)
                    if v is not None:
                        counter[str(v)] = counter.get(str(v), 0) + 1
                while window and times[window[0]] <= t - corr.timespan:
                    old = window.popleft()
                    if corr.ctype == "value_count":
                        ov = events[old].get(corr.count_field)
                        if ov is not None:
                            counter[str(ov)] -= 1
                            if counter[str(ov)] == 0:
                                del counter[str(ov)]
                metric = len(window) if corr.ctype == "event_count" else len(counter)
                hit = _cmp(corr.op, metric, corr.threshold)
                if hit and active is None:
                    ev_ids = [events[j]["event_id"] for j in window]
                    first = events[window[0]]["@timestamp"]
                    group = dict(zip(corr.group_by, key))
                    active = Alert(_alert_id(corr.rule_id, group, first), corr.rule_id, corr.title, corr.level, corr.tags, group,
                                   events[i]["@timestamp"], first, events[i]["@timestamp"], metric, ev_ids)
                    alerts.append(active)
                elif hit and active is not None:
                    active.evidence.append(events[i]["event_id"])
                    active.last_seen = events[i]["@timestamp"]
                    active.metric = max(active.metric, metric)
                elif not hit:
                    active = None
    alerts.sort(key=lambda a: (a.fired_at, a.rule_id, a.alert_id))
    kept, suppressed = apply_exceptions(rs, alerts, events, exceptions or [])
    return {"alerts": [a.to_dict() for a in kept], "suppressed": [a.to_dict() for a in suppressed],
            "stats": {"events": len(events), "rules": len(rs.detections) + len(rs.correlations), "alerts": len(kept), "suppressed": len(suppressed)}}


# ------------------------------------------------------------------------------------------------ exceptions


REQUIRED_EXCEPTION_KEYS = ["id", "rule", "match", "reason", "ticket", "owner", "valid_from", "valid_until"]


def lint_exceptions(exceptions: list[dict], rs: RuleSet | None = None) -> list[str]:
    """Return a list of problems. A suppression must be narrow, owned, justified and expire."""
    problems = []
    seen = set()
    for n, ex in enumerate(exceptions, 1):
        label = ex.get("id", f"#{n}") if isinstance(ex, dict) else f"#{n}"
        if not isinstance(ex, dict):
            problems.append(f"{label}: exception must be a mapping")
            continue
        for k in REQUIRED_EXCEPTION_KEYS:
            if not ex.get(k):
                problems.append(f"{label}: missing '{k}'")
        if label in seen:
            problems.append(f"{label}: duplicate exception id")
        seen.add(label)
        match = ex.get("match") or {}
        if not isinstance(match, dict) or not match:
            problems.append(f"{label}: match must be a non-empty mapping")
            match = {}
        if match and not ({"IpAddress", "TargetUserName"} & set(match)):
            problems.append(f"{label}: match must include IpAddress and/or TargetUserName (a suppression on other fields alone is too broad)")
        for k, v in match.items():
            if any(ch in str(v) for ch in "*?"):
                problems.append(f"{label}: wildcard in match value for '{k}' is not allowed")
        if len(str(ex.get("reason", ""))) < 20:
            problems.append(f"{label}: reason must explain the decision (at least 20 characters)")
        try:
            vf, vu = parse_ts(str(ex["valid_from"])), parse_ts(str(ex["valid_until"]))
            if vu <= vf:
                problems.append(f"{label}: valid_until must be after valid_from")
            elif vu - vf > dt.timedelta(days=MAX_EXCEPTION_DAYS):
                problems.append(f"{label}: validity longer than {MAX_EXCEPTION_DAYS} days; suppressions must expire")
        except (KeyError, ValueError):
            problems.append(f"{label}: valid_from/valid_until must be ISO timestamps like 2026-03-02T10:00:00Z")
        if rs is not None and ex.get("rule"):
            try:
                rs.resolve(str(ex["rule"]))
            except RuleError:
                problems.append(f"{label}: rule '{ex['rule']}' does not exist")
    return problems


def apply_exceptions(rs: RuleSet, alerts: list[Alert], events: list[dict], exceptions: list[dict]):
    if not exceptions:
        return alerts, []
    problems = lint_exceptions(exceptions, rs)
    if problems:
        raise RuleError("invalid exceptions: " + "; ".join(problems))
    by_id = {e["event_id"]: e for e in events}
    kept, suppressed = [], []
    for a in alerts:
        hit = None
        for ex in exceptions:
            if rs.resolve(str(ex["rule"])) != a.rule_id:
                continue
            vf, vu = parse_ts(str(ex["valid_from"])), parse_ts(str(ex["valid_until"]))
            if not (vf <= parse_ts(a.first_seen) and parse_ts(a.last_seen) <= vu):
                continue
            if all(str(by_id[eid].get(k, "")).lower() == str(v).lower() for eid in a.evidence for k, v in ex["match"].items()):
                hit = ex["id"]
                break
        if hit:
            a.suppressed_by = hit
            suppressed.append(a)
        else:
            kept.append(a)
    return kept, suppressed
