#!/usr/bin/env python3
"""Generate a deterministic stream of authentication events (JSON Lines) with known attacks, and the list of what a correct scan must find.

    python tools/make_events.py --seed 7 --minutes 120 --truth truth.json > events.jsonl
    python tools/make_events.py --seed 7 | python -m authwatch scan --format json -

The stream is made while you read it, so it can be piped into the command under test while it is still running (--pace adds a delay). Everything is synthetic: user names, addresses (from the
documentation ranges 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24 and the private range 10.0.0.0/8) and times. The truth file describes the findings of the DEFAULT rules (window 300 s, five
failures, five users): the attacks that were planted, the near-misses that must not be reported, and the damage done to the stream (unusable lines, events out of order).

Options that damage the stream: --junk RATE (a fraction of the lines is replaced by unusable ones, including one invalid UTF-8 line and one line of 70 000 bytes), --skew N (N adjacent pairs
swapped), --bom (a byte-order mark at the start), --crlf (Windows line endings).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

T0 = datetime(2026, 10, 14, 0, 0, 0, tzinfo=UTC)
WINDOW = 300


def stamp(seconds: int) -> str:
    return (T0 + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Record(NamedTuple):
    seconds: int
    user: str
    ip: str
    outcome: str

    def line(self) -> dict[str, str]:
        return {"ts": stamp(self.seconds), "user": self.user, "ip": self.ip, "outcome": self.outcome}


def record(seconds: int, user: str, ip: str, outcome: str) -> Record:
    return Record(seconds, user, ip, outcome)


def noise(rng: random.Random, minutes: int) -> list[Record]:
    """Ordinary traffic: many users, a few failures. A failure that would look like an attack to the default rules is turned into a success."""
    users = [f"u{n:03d}" for n in range(300)]
    homes = {u: [f"10.{n // 250}.{n % 250}.{k}" for k in (1, 2)] for n, u in enumerate(users)}
    offices = ["192.0.2.1", "192.0.2.2", "192.0.2.3"]
    out: list[Record] = []
    for second in range(0, minutes * 60):
        for _ in range(rng.choice((0, 1, 1, 2))):
            user = rng.choice(users)
            ip = rng.choice(offices) if rng.random() < 0.25 else rng.choice(homes[user])
            out.append(record(second, user, ip, "failure" if rng.random() < 0.02 else "success"))
    per_pair: dict[tuple[str, str], deque[int]] = {}
    per_ip: dict[str, deque[tuple[int, str]]] = {}
    for index, item in enumerate(out):
        if item.outcome != "failure":
            continue
        pair = per_pair.setdefault((item.user, item.ip), deque())
        while pair and pair[0] <= item.seconds - WINDOW:
            pair.popleft()
        source = per_ip.setdefault(item.ip, deque())
        while source and source[0][0] <= item.seconds - WINDOW:
            source.popleft()
        distinct = {u for _, u in source} | {item.user}
        if len(pair) >= 2 or len(distinct) > 3:
            out[index] = item._replace(outcome="success")
        else:
            pair.append(item.seconds)
            source.append((item.seconds, item.user))
    return out


def plant(rng: random.Random, minutes: int) -> tuple[list[Record], list[dict[str, object]], list[dict[str, str]]]:
    """The attacks (what a scan must find) and the near-misses (what it must not report). Planted attacks are 15 or more minutes apart, from addresses that ordinary traffic never uses."""
    events: list[Record] = []
    findings: list[dict[str, object]] = []
    quiet: list[dict[str, str]] = []
    slots = list(range(5, max(6, minutes - 10), 15))
    rng.shuffle(slots)
    plan = ["brute", "compromise", "spray", "brute", "slow_brute", "slow_spray", "spread_brute", "compromise", "spray"]
    for number, (kind, slot) in enumerate(zip(plan, slots, strict=False)):
        start = slot * 60 + rng.randrange(0, 40)
        if kind in ("brute", "compromise", "slow_brute", "spread_brute"):
            ip, user = f"203.0.113.{10 + number}", f"u{rng.randrange(300):03d}"
            count = {"brute": rng.randrange(5, 10), "compromise": rng.randrange(5, 9), "slow_brute": 4, "spread_brute": 5}[kind]
            gap = 90 if kind == "spread_brute" else rng.randrange(2, 20)
            times = [start + gap * i for i in range(count)]
            events += [record(t, user, ip, "failure") for t in times]
            subject = f"{user}@{ip}"
            if kind in ("brute", "compromise"):
                findings.append({"kind": "brute_force", "subject": subject, "first_ts": stamp(times[0]), "last_ts": stamp(times[4]), "count": 5})
            if kind == "compromise":
                success = times[-1] + rng.randrange(5, 40)
                events.append(record(success, user, ip, "success"))
                findings.append({"kind": "compromise_after_failures", "subject": subject, "first_ts": stamp(times[0]), "last_ts": stamp(success), "count": count})
            elif kind in ("slow_brute", "spread_brute"):
                quiet.append({"kind": "brute_force", "subject": subject})
        else:
            ip = f"198.51.100.{10 + number}"
            count = {"spray": rng.randrange(5, 9), "slow_spray": 4}[kind]
            names = [f"u{n:03d}" for n in rng.sample(range(300), count)]
            times = [start + 3 * i + rng.randrange(0, 4) for i in range(count)]
            events += [record(t, u, ip, "failure") for t, u in zip(times, names, strict=True)]
            if kind == "spray":
                findings.append({"kind": "password_spray", "subject": ip, "first_ts": stamp(times[0]), "last_ts": stamp(times[4]), "count": 5})
            else:
                quiet.append({"kind": "password_spray", "subject": ip})
    return events, findings, quiet


def lines(seed: int, minutes: int, junk: float, skew: int, bom: bool, crlf: bool) -> tuple[list[bytes], dict[str, object]]:
    rng = random.Random(seed)  # noqa: S311 - synthetic test data; reproducibility matters, secrecy does not
    base = noise(rng, minutes)
    attacks, findings, quiet = plant(rng, minutes)
    planted = set(attacks)
    events = sorted(base + attacks, key=lambda e: e.seconds)
    swapped = 0
    index = 0
    touched: set[int] = set()
    while swapped < skew and index + 1 < len(events):
        a, b = events[index], events[index + 1]
        if a not in planted and b not in planted and a.seconds < b.seconds:
            events[index], events[index + 1] = b, a
            touched.update((index, index + 1))
            swapped += 1
            index += 2
            continue
        index += rng.randrange(1, 400)
    eol = b"\r\n" if crlf else b"\n"
    out = [json.dumps(e.line()).encode() + eol for e in events]
    bad = 0
    if junk > 0:
        garbage = [b"not json at all", b'{"ts": "2026-10-14T00:00:00Z", "user": "x"', b"[1, 2, 3]", b'{"ts": "yesterday", "user": "u001", "ip": "10.0.1.1", "outcome": "failure"}',
                   b'{"ts": "2026-10-14T00:00:00Z", "user": "bad user", "ip": "10.0.1.1", "outcome": "failure"}',
                   b'{"ts": "2026-10-14T00:00:00Z", "user": "u001", "ip": "999.0.0.1", "outcome": "failure"}']
        replaceable = [i for i, e in enumerate(events) if e not in planted and i not in touched]       # neither a planted attack nor a swapped pair is damaged: the truth file stays exact
        picks = sorted(rng.sample(replaceable, max(2, int(len(out) * junk))))
        for n, position in enumerate(picks):
            if n == 0:
                out[position] = b'{"ts": "2026-10-14T00:00:00Z", "user": "u\xff\xfe", "ip": "10.0.1.1", "outcome": "failure"}' + eol
            elif n == 1:
                out[position] = b'{"ts": "2026-10-14T00:00:00Z", "user": "u001", "ip": "10.0.1.1", "outcome": "failure", "pad": "' + b"x" * 70000 + b'"}' + eol
            else:
                out[position] = rng.choice(garbage) + eol
            bad += 1
    if bom and out:
        out[0] = b"\xef\xbb\xbf" + out[0]
    truth: dict[str, object] = {"seed": seed, "events": len(events) - bad, "bad_lines": bad, "out_of_order": swapped,
                                "findings": sorted(findings, key=lambda f: (str(f["first_ts"]), str(f["kind"]), str(f["subject"]))), "must_not_report": quiet}
    return out, truth


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--minutes", type=int, default=120, help="length of the simulated day fragment (default 120)")
    ap.add_argument("--truth", help="write the expected findings here (JSON)")
    ap.add_argument("--junk", type=float, default=0.0, help="fraction of lines replaced by unusable ones")
    ap.add_argument("--skew", type=int, default=0, help="number of adjacent event pairs to swap")
    ap.add_argument("--bom", action="store_true")
    ap.add_argument("--crlf", action="store_true")
    ap.add_argument("--pace", type=float, default=0.0, help="seconds to wait after every 1000 lines (to make a slow producer)")
    args = ap.parse_args()
    out, truth = lines(args.seed, args.minutes, args.junk, args.skew, args.bom, args.crlf)
    if args.truth:
        with open(args.truth, "w", encoding="utf-8") as handle:
            json.dump(truth, handle, indent=2, sort_keys=True)
            handle.write("\n")
    stream = sys.stdout.buffer
    try:
        for n, raw in enumerate(out, 1):
            stream.write(raw)
            if args.pace and n % 1000 == 0:
                stream.flush()
                time.sleep(args.pace)
        stream.flush()
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
