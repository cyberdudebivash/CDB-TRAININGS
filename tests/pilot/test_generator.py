"""The synthetic telemetry must be deterministic, safe (no real addresses) and internally consistent."""
import hashlib
import ipaddress
import sys

import pytest

from soc_lab.events import RFC1918, fmt_ts, parse_ts, write_jsonl
from soc_lab.generator import DEFAULT_SEEDS, generate

EXTERNAL_OK = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "100.64.0.0/10")]
# Golden hashes pin the exact bytes of events.jsonl for the published practice seeds (CPython 3.13 verified).
GOLDEN = {
    "guided": "ff47fc5c2934f590f58e2561bc07e1580b71c6c52b0549056ce00e91cac68898",
    "independent": "20abdf7e3e5f5f1c9c8b7ea6cca57c36a40a80b50ae0a113ca12018d0a54bac6",
}


def _sha(ds, tmp_path):
    p = tmp_path / "e.jsonl"
    write_jsonl(p, ds.events)
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("profile", ["guided", "independent"])
def test_deterministic(profile, tmp_path):
    a, b = generate(profile), generate(profile)
    assert a.events == b.events and a.labels == b.labels and a.scenarios == b.scenarios


@pytest.mark.parametrize("profile", ["guided", "independent"])
def test_different_seed_changes_data(profile):
    assert generate(profile, DEFAULT_SEEDS[profile] + 1).events != generate(profile).events


@pytest.mark.parametrize("profile", ["guided", "independent"])
def test_invariants(profile):
    ds = generate(profile)
    ids = [e["event_id"] for e in ds.events]
    assert ids == [f"evt-{i:06d}" for i in range(1, len(ids) + 1)], "ids must be sequential and unique"
    times = [e["@timestamp"] for e in ds.events]
    assert times == sorted(times), "events must be time-ordered"
    assert set(ds.labels) == set(ids), "every event has exactly one label"
    scenario_ids = {s["id"] for s in ds.scenarios}
    assert set(ds.labels.values()) <= scenario_ids
    for e in ds.events:
        assert e["EventID"] in (4624, 4625)
        assert e["Computer"].endswith(".corp.example")
        ip = ipaddress.ip_address(e["IpAddress"])
        assert any(ip in n for n in RFC1918) or any(ip in n for n in EXTERNAL_OK), f"{ip} is not a reserved/synthetic range"
        if e["EventID"] == 4625:
            assert e["Status"].startswith("0x") and e["SubStatus"].startswith("0x")
        assert parse_ts(e["@timestamp"]).strftime("%Y-%m-%dT%H:%M:%SZ") == e["@timestamp"]
    for sc in ds.scenarios:
        assert sc["event_count"] > 0
        assert sc["kind"] in ("ATTACK", "BENIGN")


def test_no_personal_data_markers():
    blob = " ".join(str(v) for e in generate("guided").events[:300] for v in e.values())
    assert "@" not in blob, "no e-mail-like values in synthetic telemetry"


def test_guided_change_window_semantics():
    """F2 (scanner) is wholly inside the CHG-1042 window; S6 (same address) is wholly outside it."""
    ds = generate("guided")
    win = (parse_ts("2026-03-02T10:00:00Z"), parse_ts("2026-03-02T10:30:00Z"))
    f2 = [parse_ts(e["@timestamp"]) for e in ds.events if ds.labels[e["event_id"]] == "F2"]
    s6 = [parse_ts(e["@timestamp"]) for e in ds.events if ds.labels[e["event_id"]] == "S6"]
    assert all(win[0] <= t <= win[1] for t in f2)
    assert all(t > win[1] for t in s6)
    assert {e["IpAddress"] for e in ds.events if ds.labels[e["event_id"]] in ("F2", "S6")} == {"10.0.5.20"}


def test_s4_contains_success_from_attacker():
    ds = generate("guided")
    s4 = [e for e in ds.events if ds.labels[e["event_id"]] == "S4"]
    src = {e["IpAddress"] for e in s4}
    assert src == {"203.0.113.88"}
    assert any(e["EventID"] == 4624 and e["TargetUserName"] == "m.lee" for e in s4)


def test_independent_slow_spray_uses_many_networks():
    ds = generate("independent")
    srcs = {e["IpAddress"] for e in ds.events if ds.labels[e["event_id"]] == "S1"}
    nets = {".".join(ip.split(".")[:3]) for ip in srcs}
    assert len(srcs) == 10 and len(nets) == 10, "S1 must defeat per-source and per-/24 grouping"
    per_account = {}
    for e in ds.events:
        if ds.labels[e["event_id"]] == "S1":
            per_account.setdefault(e["TargetUserName"], set()).add(e["IpAddress"])
    assert min(len(v) for v in per_account.values()) >= 5


@pytest.mark.skipif(sys.version_info[:2] != (3, 13), reason="UNVERIFIED_INTERPRETER: golden hashes verified on CPython 3.13 only")
@pytest.mark.parametrize("profile", ["guided", "independent"])
def test_golden_hash(profile, tmp_path):
    assert GOLDEN[profile] != "PINNED_BELOW", "pin the golden hash"
    assert _sha(generate(profile), tmp_path) == GOLDEN[profile]
