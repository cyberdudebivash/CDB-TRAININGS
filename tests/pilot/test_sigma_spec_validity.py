"""Every rule file shipped with the course must be valid Sigma according to an independent implementation (pySigma)."""
import pytest

from conftest import INSTRUCTOR, LABS

sigma_collection = pytest.importorskip("sigma.collection", reason="pysigma is a pinned dev dependency; install requirements.txt")


def rule_sets():
    """Rule directories validated as whole collections (correlation rules reference base rules in sibling files)."""
    return {
        "naive_playbook": sorted((LABS / "m04-guided" / "rules" / "naive_playbook").glob("*.yml")),
        "solution": sorted((LABS / "m04-guided" / "solution" / "rules").glob("*.yml")),
        "starter_base_rule": [LABS / "m04-guided" / "starter" / "rules" / "win_failed_logon.yml"],
    }


def collection_of(files):
    from sigma.collection import SigmaCollection

    return SigmaCollection.from_yaml("\n---\n".join(f.read_text(encoding="utf-8") for f in files))


@pytest.mark.parametrize("name", sorted(rule_sets()))
def test_rule_set_is_valid_sigma(name):
    files = rule_sets()[name]
    assert files, f"no rule files for {name}"
    coll = collection_of(files)
    assert coll.rules and coll.errors == [], coll.errors
    # pySigma resolves every correlation reference inside the collection (raises if a reference is dangling)
    from sigma.correlations import SigmaCorrelationRule

    for r in coll.rules:
        if isinstance(r, SigmaCorrelationRule):
            r.resolve_rule_references(coll)


def test_correlation_rules_are_recognised_as_correlations():
    from sigma.collection import SigmaCollection
    from sigma.correlations import SigmaCorrelationRule

    coll = collection_of(rule_sets()["solution"])
    corr = [r for r in coll.rules if isinstance(r, SigmaCorrelationRule)]
    assert len(corr) == 4


def test_each_rule_has_description_and_attack_tag_when_alerting():
    import yaml

    for path in (LABS / "m04-guided" / "solution" / "rules").glob("mr_*.yml"):
        for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            assert doc.get("description"), f"{path.name}: description missing"
            assert any(str(t).startswith("attack.t1110") for t in doc.get("tags", [])), f"{path.name}: ATT&CK tag missing"


@pytest.mark.private_materials
def test_private_reference_rules_are_valid_sigma():
    ref = INSTRUCTOR / "m04-independent-reference" / "rules"
    if not ref.exists():
        pytest.skip("SKIPPED_PRIVATE_MATERIALS: instructor pack not present")
    coll = collection_of(sorted(ref.glob("*.yml")))
    assert coll.rules and coll.errors == []
