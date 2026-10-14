"""The guided lab is executed end to end and its README is held accountable to the real tool output (docs-as-tests)."""
import subprocess
import sys

import pytest
import yaml

from conftest import LABS, ROOT, load_json, run_cli

GUIDED = LABS / "m04-guided"
README = (GUIDED / "README.md").read_text(encoding="utf-8")
SOL_RULES = str(GUIDED / "solution" / "rules")
SOL_EXC = str(GUIDED / "solution" / "exceptions.yml")


def detect(guided, tmp_path, name, rules, exceptions=None):
    out = tmp_path / f"{name}.json"
    argv = ["detect", "--rules", rules, "--events", str(guided / "events.enriched.jsonl"), "--out", str(out)]
    if exceptions:
        argv += ["--exceptions", exceptions]
    assert run_cli(argv)[0] == 0
    return out


def evaluate(guided, alerts):
    return run_cli(["evaluate", "--alerts", str(alerts), "--truth", str(guided / "truth")])[1]


def assert_documented(readme, output, lines):
    for line in lines:
        assert line in readme, f"README no longer documents: {line!r}"
        assert line in output, f"tool output no longer matches README: {line!r}\n{output}"


def test_generate_output_matches_readme(tmp_path):
    code, text = run_cli(["generate", "--profile", "guided", "--out", str(tmp_path), "--with-truth"])
    assert code == 0 and "generated 1191 events (profile=guided, seed=20260302)" in text
    assert "generated 1191 events (profile=guided, seed=20260302)" in README


def test_explore_script_output_matches_readme(guided):
    res = subprocess.run([sys.executable, str(GUIDED / "explore.py"), str(guided / "events.enriched.jsonl")], capture_output=True, text=True, check=True)
    for needle in ("events: 1191", "by EventID: {4624: 254, 4625: 937}", "10.0.2.15        failures= 480  distinct_accounts=  1",
                   "203.0.113.77     failures=  88  distinct_accounts= 48", "10.0.9.5         failures=  31  distinct_accounts= 17"):
        assert needle in res.stdout
    # README quotes the same facts in prose with collapsed whitespace
    for needle in ("events: 1191", "{4624: 254, 4625: 937}", "failures= 480 distinct_accounts= 1", "failures= 88 distinct_accounts= 48", "failures= 31 distinct_accounts= 17"):
        assert needle in README


def test_baseline_step_matches_readme(guided, tmp_path):
    out = detect(guided, tmp_path, "naive", str(GUIDED / "rules" / "naive_playbook"))
    assert_documented(README, evaluate(guided, out), [
        "Recall    : 1/5 attack scenarios detected  (missed: S2, S3, S4, S6)",
        "Precision : 1/2 alerts are true positives",
        "False-positive alerts: 1   by scenario: {'F1': 1}"])


def test_reference_rules_before_tuning_match_readme(guided, tmp_path):
    out = detect(guided, tmp_path, "pre", SOL_RULES)
    assert_documented(README, evaluate(guided, out), [
        "Recall    : 5/5 attack scenarios detected",
        "Precision : 6/8 alerts are true positives",
        "False-positive alerts: 2   by scenario: {'F1': 1, 'F2': 1}"])


def test_reference_rules_with_exceptions_match_readme(guided, tmp_path):
    out = detect(guided, tmp_path, "post", SOL_RULES, SOL_EXC)
    assert_documented(README, evaluate(guided, out), [
        "Recall    : 5/5 attack scenarios detected",
        "Precision : 6/6 alerts are true positives",
        "False-positive alerts: 0   by scenario: none",
        "Suppressed alerts: 2  (of which hid real attacks: 0)"])


def test_the_broad_exception_trap_costs_the_attack(guided, tmp_path):
    broad = tmp_path / "broad.yml"
    exc = yaml.safe_load(open(SOL_EXC, encoding="utf-8"))["exceptions"]
    for e in exc:
        if e["id"] == "EX-F2-scanner-change-window":
            e["valid_from"], e["valid_until"] = "2026-03-02T00:00:00Z", "2026-03-30T00:00:00Z"
    broad.write_text(yaml.safe_dump({"exceptions": exc}), encoding="utf-8")
    out = detect(guided, tmp_path, "trap", SOL_RULES, str(broad))
    assert_documented(README, evaluate(guided, out), [
        "Suppressed alerts: 3  (of which hid real attacks: 1)",
        "Recall    : 4/5 attack scenarios detected  (missed: S6)"])


def test_triage_step_matches_readme(guided, tmp_path):
    out = detect(guided, tmp_path, "pre", SOL_RULES)
    code, text = run_cli(["check-triage", "--records", str(GUIDED / "solution" / "triage"), "--alerts", str(out),
                          "--events", str(guided / "events.jsonl"), "--truth", str(guided / "truth")])
    assert code == 0 and "Triage records passed: 5/5" in text and "Triage records passed: 5/5" in README


def test_starter_templates_force_the_learner_to_complete_them():
    code, text = run_cli(["lint", "--rules", str(GUIDED / "starter" / "rules")])
    assert code == 2 and "RULE ERROR" in text, "templates with TODO placeholders must not load (fail closed)"
    code, _ = run_cli(["lint", "--rules", str(GUIDED / "starter" / "rules" / "win_failed_logon.yml")])
    assert code == 0, "the provided base rule is valid"
    tpl = (GUIDED / "starter" / "triage" / "TEMPLATE.json").read_text(encoding="utf-8")
    assert "ALT-00000000" in tpl


def test_template_triage_record_is_rejected_until_filled(guided, tmp_path):
    out = detect(guided, tmp_path, "pre", SOL_RULES)
    code, text = run_cli(["check-triage", "--records", str(GUIDED / "starter" / "triage"), "--alerts", str(out),
                          "--events", str(guided / "events.jsonl"), "--truth", str(guided / "truth")])
    assert code == 1 and "does not exist in the alerts file" in text


def test_solution_exceptions_are_lint_clean():
    code, text = run_cli(["lint", "--rules", SOL_RULES, "--exceptions", SOL_EXC])
    assert code == 0 and "rules OK" in text


def test_readme_states_the_lab_is_free_and_offline():
    assert "**$0**" in README and "no network scanning" in README.lower()
