"""Small helpers shared by the checks (a module of its own because pytest's importlib mode does not make conftest importable)."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)


def stamp(seconds: float) -> str:
    moment = T0 + timedelta(seconds=seconds)
    text = moment.strftime("%Y-%m-%dT%H:%M:%S")
    return f"{text}.{moment.microsecond:06d}Z" if moment.microsecond else f"{text}Z"


def raw(seconds: float, user: str, ip: str, outcome: str) -> bytes:
    return (json.dumps({"ts": stamp(seconds), "user": user, "ip": ip, "outcome": outcome}) + "\n").encode()
