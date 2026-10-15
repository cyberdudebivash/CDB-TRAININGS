"""PY-M12 guided lab, step E (registry: a mapping instead of an if ladder). Run: python -m pytest checks/test_step_e_registry.py"""
from __future__ import annotations

import pytest


def usd(lk, cents: int):
    return lk.Money(cents, "USD")


@pytest.mark.parametrize("spec,expected", [
    ({"kind": "flat", "amount": "0.25 USD"}, "FlatFee"),
    ({"kind": "percent", "basis_points": 150}, "PercentFee"),
    ({"kind": "percent", "basis_points": 150, "currency": "EUR"}, "PercentFee"),
    ({"kind": "capped", "inner": {"kind": "percent", "basis_points": 150}, "cap": "5.00 USD"}, "Capped"),
    ({"kind": "combined", "policies": [{"kind": "flat", "amount": "0.25 USD"}, {"kind": "percent", "basis_points": 100}]}, "Combined"),
])
def test_registry_builds_the_named_policy(lk, spec, expected):
    assert type(lk.make_policy(spec)).__name__ == expected


def test_registry_builds_policies_that_behave(lk):
    p = lk.make_policy({"kind": "capped", "inner": {"kind": "combined", "policies": [{"kind": "flat", "amount": "0.25 USD"}, {"kind": "percent", "basis_points": 100}]}, "cap": "1.00 USD"})
    assert p.fee(usd(lk, 5000)) == usd(lk, 75) and p.fee(usd(lk, 10**6)) == usd(lk, 100)


def test_registry_never_modifies_the_spec(lk):
    spec = {"kind": "capped", "inner": {"kind": "percent", "basis_points": 150}, "cap": "5.00 USD"}
    import copy
    before = copy.deepcopy(spec)
    lk.make_policy(spec)
    assert spec == before


@pytest.mark.parametrize("spec", [{"kind": "nope"}, {"kind": None}, {"kind": 5}, {"kind": ["flat"]}, {"kind": ""}, {"kind": "FLAT"}, {}, {"basis_points": 1}])
def test_registry_rejects_unknown_or_missing_kinds_with_value_error(lk, spec):
    with pytest.raises(ValueError):
        lk.make_policy(spec)


def test_an_unknown_kind_is_reported_as_unknown_even_when_the_other_keys_look_valid(lk):
    with pytest.raises(ValueError, match="unknown policy kind"):
        lk.make_policy({"kind": "nope", "amount": "1.00 USD"})
    with pytest.raises(ValueError, match="needs a 'kind'"):
        lk.make_policy({"amount": "1.00 USD"})


@pytest.mark.parametrize("spec", [
    {"kind": "percent"}, {"kind": "flat"}, {"kind": "percent", "basis_points": 150, "surprise": 1}, {"kind": "flat", "amount": "1.00 USD", "x": 1},
    {"kind": "capped", "cap": "1.00 USD"}, {"kind": "combined"},
])
def test_registry_rejects_missing_or_unexpected_parameters_with_value_error(lk, spec):
    with pytest.raises(ValueError):
        lk.make_policy(spec)


@pytest.mark.parametrize("bad", [None, "flat", 5, ["kind", "flat"]])
def test_registry_needs_a_mapping(lk, bad):
    with pytest.raises(TypeError):
        lk.make_policy(bad)


def test_registry_errors_from_inside_a_factory_keep_their_own_type(lk):
    with pytest.raises(ValueError):
        lk.make_policy({"kind": "percent", "basis_points": 99999})
    with pytest.raises(TypeError):
        lk.make_policy({"kind": "percent", "basis_points": True})        # a bad value is a TypeError of the policy, not a bad-parameters ValueError


def test_register_policy_adds_a_kind_and_refuses_duplicates(lk):
    @lk.register_policy("test-free-kind")
    def make_free():
        return lk.FlatFee(lk.Money(0))
    assert lk.make_policy({"kind": "test-free-kind"}).fee(usd(lk, 5)) == usd(lk, 0)
    with pytest.raises(ValueError):
        lk.register_policy("test-free-kind")(make_free)
    with pytest.raises(ValueError):
        lk.register_policy("flat")(make_free)
    assert make_free() == lk.FlatFee(lk.Money(0)), "the decorator returns the function unchanged"
