"""Independent lab: transfer is required, and (when the private pack is present) the dataset is solvable."""
import pytest

from conftest import INSTRUCTOR, LABS, load_json, run_cli

GUIDED_RULES = str(LABS / "m04-guided" / "solution" / "rules")
REF = INSTRUCTOR / "m04-independent-reference"


def detect(ind, tmp_path, rules, exceptions=None):
    out = tmp_path / "a.json"
    argv = ["detect", "--rules", rules, "--events", str(ind / "events.enriched.jsonl"), "--out", str(out)]
    if exceptions:
        argv += ["--exceptions", exceptions]
    assert run_cli(argv)[0] == 0
    return out


def test_guided_solution_does_not_pass_the_independent_dataset(independent, tmp_path):
    """The independent lab must not be solvable by copying the guided answer."""
    out = detect(independent, tmp_path, GUIDED_RULES)
    run_cli(["evaluate", "--alerts", str(out), "--truth", str(independent / "truth"), "--json", str(tmp_path / "r.json")])
    s = load_json(tmp_path / "r.json")["summary"]
    assert s["missed"] == ["S1"], "very slow multi-network spray must evade the guided rules"
    assert s["false_positive_alerts"] == 2, "lock-out loop (F1) and help-desk validation (F3) must be false positives"


def test_independent_readme_states_the_constraints_and_deliverables():
    text = (LABS / "m04-independent" / "README.md").read_text(encoding="utf-8")
    for needle in ("REPORT.md", "triage/*.json", "exceptions.yml", "wildcards", "90 days", "rubric.yaml", "published seed", "**$0**"):
        assert needle in text


@pytest.mark.private_materials
def test_reference_solution_passes_the_independent_lab(independent, tmp_path):
    if not REF.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present - independent lab solvability NOT verified in this run")
    out = detect(independent, tmp_path, str(REF / "rules"), str(REF / "exceptions.yml"))
    code, text = run_cli(["evaluate", "--alerts", str(out), "--truth", str(independent / "truth"), "--json", str(tmp_path / "r.json")])
    s = load_json(tmp_path / "r.json")["summary"]
    assert s["recall"] == 1.0 and s["false_positive_alerts"] == 0 and s["suppressed_true_positive_alerts"] == 0
    assert s["suppressed_alerts"] == 2
    code, _ = run_cli(["lint", "--rules", str(REF / "rules"), "--exceptions", str(REF / "exceptions.yml")])
    assert code == 0


@pytest.mark.private_materials
def test_reference_triage_records_pass(independent, tmp_path):
    if not (REF / "triage").exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    out = detect(independent, tmp_path, str(REF / "rules"))   # before exceptions: the alerts the learner triages
    code, text = run_cli(["check-triage", "--records", str(REF / "triage"), "--alerts", str(out), "--events", str(independent / "events.jsonl"),
                          "--truth", str(independent / "truth")])
    assert code == 0, text
