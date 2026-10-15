"""The slow-but-correct program the PY-M09 guided lab starts from (also the oracle: the learner's version must give the same answers). Not to be edited."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

PATTERN = r"(\d{4}-\d\d-\d\d)T(\d\d):(\d\d):(\d\d)Z (\d{1,3}(?:\.\d{1,3}){3}) ([A-Za-z0-9_.-]+) (OK|FAIL)"


@dataclass(frozen=True, slots=True)
class Attempt:
    ts: int
    ip: str
    user: str
    ok: bool


@dataclass(frozen=True, slots=True)
class Report:
    attempts: int
    malformed: int
    failures: int
    unique_ips: int
    flagged: tuple[str, ...]
    top_users: tuple[tuple[str, int], ...]


def parse_line(line):
    m = re.compile("^" + PATTERN + "$").match(line.strip())
    if m is None:
        return None
    date, hh, mm, ss, ip, user, result = m.groups()
    if int(hh) > 23 or int(mm) > 59 or int(ss) > 59:
        return None
    if any(int(octet) > 255 for octet in ip.split(".")):
        return None
    try:
        midnight = int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None
    return Attempt(midnight + int(hh) * 3600 + int(mm) * 60 + int(ss), ip, user, result == "OK")


def parse_lines(lines):
    return [a for a in map(parse_line, lines) if a is not None]


def unique_ips(attempts):
    seen = []
    for a in attempts:
        if a.ip not in seen:
            seen.append(a.ip)
    return seen


def failures_by_ip(attempts):
    ips = unique_ips(attempts)
    fails = [a.ip for a in attempts if not a.ok]
    return {ip: fails.count(ip) for ip in ips if fails.count(ip) > 0}


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive int")
    return value


def bursts(attempts, threshold, window):
    _positive(threshold, "threshold")
    _positive(window, "window")
    flagged = []
    for ip in unique_ips(attempts):
        times = sorted(a.ts for a in attempts if a.ip == ip and not a.ok)
        for i in range(len(times)):
            if len([t for t in times if times[i] <= t < times[i] + window]) >= threshold:
                flagged.append(ip)
                break
    return flagged


def top_users(attempts, n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative int")
    users = sorted({a.user for a in attempts})
    counts = {u: sum(1 for a in attempts if a.user == u and not a.ok) for u in users}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [kv for kv in ranked if kv[1] > 0][:n]


def render(report):
    out = ""
    out += f"attempts: {report.attempts}\n"
    out += f"malformed: {report.malformed}\n"
    out += f"failures: {report.failures}\n"
    out += f"unique ips: {report.unique_ips}\n"
    out += "flagged: " + (", ".join(report.flagged) or "none") + "\n"
    for user, count in report.top_users:
        out += f"user {user}: {count}\n"
    return out


def analyze(lines, threshold=5, window=60, top=3):
    _positive(threshold, "threshold")
    _positive(window, "window")
    lines = list(lines)
    attempts = parse_lines(lines)
    by_ip = failures_by_ip(attempts)
    return Report(
        attempts=len(attempts),
        malformed=len(lines) - len(attempts),
        failures=sum(by_ip.values()),
        unique_ips=len(unique_ips(attempts)),
        flagged=tuple(bursts(attempts, threshold, window)),
        top_users=tuple(top_users(attempts, top)),
    )
