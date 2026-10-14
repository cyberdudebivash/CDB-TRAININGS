"""Event and file helpers shared by the lab tools."""
from __future__ import annotations

import datetime as dt
import ipaddress
import json
from pathlib import Path
from typing import Iterable

UTC = dt.timezone.utc
RFC1918 = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


def parse_ts(value: str) -> dt.datetime:
    """Parse an ISO-8601 UTC timestamp such as 2026-03-02T08:00:01Z."""
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def fmt_ts(value: dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{n}: invalid JSON ({exc.msg})") from exc
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def is_rfc1918(ip: str) -> bool:
    """True only for RFC 1918 space. (Python's is_private also returns True for documentation ranges, which we use as 'external'.)"""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in RFC1918 if addr.version == net.version)


def net24(ip: str) -> str:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return "-"
    if addr.version != 4:
        return "-"
    a, b, c, _ = str(addr).split(".")
    return f"{a}.{b}.{c}.0/24"


def enrich(events: list[dict], context: dict) -> list[dict]:
    """Add derived fields used by the labs: SrcNet24 and SrcRole (asset-inventory lookup, else internal/external)."""
    roles = {a["ip"]: a["role"] for a in context.get("assets", [])}
    out = []
    for ev in events:
        row = dict(ev)
        ip = row.get("IpAddress", "-")
        row["SrcNet24"] = net24(ip)
        row["SrcRole"] = roles.get(ip) or ("internal" if is_rfc1918(ip) else "external")
        out.append(row)
    return out
