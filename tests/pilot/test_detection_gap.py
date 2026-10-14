"""Executed evidence for finding F-SOC-004: the SOC playbook's brute-force rule (p. 22) cannot detect password spraying."""
from conftest import LABS, load_json, run_cli


def test_playbook_rule_misses_every_spray_variant(guided, tmp_path):
    rules = LABS / "m04-guided" / "rules" / "naive_playbook"
    out = tmp_path / "naive.json"
    assert run_cli(["detect", "--rules", str(rules), "--events", str(guided / "events.enriched.jsonl"), "--out", str(out)])[0] == 0
    code, text = run_cli(["evaluate", "--alerts", str(out), "--truth", str(guided / "truth"), "--json", str(tmp_path / "rep.json")])
    rep = load_json(tmp_path / "rep.json")["summary"]
    assert rep["attack_scenarios"] == 5 and rep["detected"] == 1
    assert rep["missed"] == ["S2", "S3", "S4", "S6"], "every spray variant (S2, S3, S4, S6) is missed"
    assert rep["false_positive_alerts"] == 1, "and it still raises the stale-service-account false positive (F1)"
    assert "Recall    : 1/5 attack scenarios detected  (missed: S2, S3, S4, S6)" in text


def test_the_playbook_rule_parameters_are_the_documented_ones():
    """Guard: the baseline file must keep the parameters the audit cites (> 5 failures, 5 minutes, source+user+host)."""
    import yaml
    docs = list(yaml.safe_load_all((LABS / "m04-guided" / "rules" / "naive_playbook" / "mr_playbook_bruteforce.yml").read_text(encoding="utf-8")))
    c = docs[0]["correlation"]
    assert c["type"] == "event_count" and c["timespan"] == "5m" and c["condition"] == {"gt": 5}
    assert c["group-by"] == ["IpAddress", "TargetUserName", "Computer"]
