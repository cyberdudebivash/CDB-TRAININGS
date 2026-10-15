"""Published checks for the PY-M12 independent lab (rulekit). They show the shape of the task; the instructors' suite checks much more (value semantics, isolation, edge cases).
Passing these ten is necessary, not sufficient."""
from __future__ import annotations

import pytest


def event(rk, kind="login", source="10.0.0.1", severity=1, **fields):
    return rk.Event(kind=kind, source=source, severity=severity, fields=fields)


def test_an_event_is_an_immutable_value(rk):
    import dataclasses
    a, b = event(rk, user="ann"), event(rk, user="ann")
    assert a == b and hash(a) == hash(b) and a != event(rk, user="bob")
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.kind = "x"


def test_event_fields_are_copied_and_read_only(rk):
    source = {"user": "ann"}
    e = rk.Event(kind="login", source="s", fields=source)
    source["user"] = "mallory"
    assert e.fields["user"] == "ann"
    with pytest.raises(TypeError):
        e.fields["user"] = "x"


def test_event_validates_its_arguments(rk):
    for bad in ({"kind": ""}, {"source": "  "}, {"severity": 0}, {"severity": 5}):
        args = {"kind": "k", "source": "s", **bad}
        with pytest.raises(ValueError):
            rk.Event(**args)
    with pytest.raises(TypeError):
        rk.Event(kind="k", source="s", severity=True)


def test_matchers_decide_about_one_event(rk):
    e = event(rk, severity=3, user="ann")
    assert rk.KindIs("login").matches(e) and not rk.KindIs("logout").matches(e)
    assert rk.FieldEquals("user", "ann").matches(e) and not rk.FieldEquals("user", "bob").matches(e) and not rk.FieldEquals("missing", "x").matches(e)
    assert rk.SeverityAtLeast(3).matches(e) and not rk.SeverityAtLeast(4).matches(e)


def test_matchers_combine_with_operators_and_stay_values(rk):
    a, b, c = rk.KindIs("a"), rk.KindIs("b"), rk.KindIs("c")
    assert (a & b & c) == rk.AllOf((a, b, c)) and (a | b | c) == rk.AnyOf((a, b, c)) and ~a == rk.Not(a)
    assert hash(a & b) == hash(rk.AllOf((a, b)))


def test_rules_validate_name_matcher_and_threshold(rk):
    rk.Rule("r", rk.KindIs("x"))
    for args, exc in (((" ", rk.KindIs("x")), ValueError), (("r", object()), TypeError), (("r", rk.KindIs("x"), 0), ValueError), (("r", rk.KindIs("x"), True), TypeError)):
        with pytest.raises(exc):
            rk.Rule(*args)


def test_an_engine_alerts_once_when_the_threshold_is_reached_for_one_source(rk):
    engine = rk.RuleEngine()
    engine.add(rk.Rule("brute", rk.KindIs("login_failed"), threshold=3))
    out = [engine.process(event(rk, "login_failed", source=s)) for s in ("a", "a", "b", "a", "a")]
    assert [len(x) for x in out] == [0, 0, 0, 1, 0]
    alert = out[3][0]
    assert (alert.rule, alert.source, alert.count) == ("brute", "a", 3) and engine.count("brute", "a") == 4 and engine.count("brute", "b") == 1


def test_two_engines_never_share_state(rk):
    one, two = rk.RuleEngine(), rk.RuleEngine()
    one.add(rk.Rule("r", rk.KindIs("x")))
    assert two.rules == () and two.process(event(rk, "x")) == [] and len(one.process(event(rk, "x"))) == 1


def test_subscribers_receive_alerts_and_a_failing_one_does_not_stop_the_engine(rk):
    engine, seen = rk.RuleEngine(), []
    engine.add(rk.Rule("r", rk.KindIs("x")))
    off = engine.subscribe(seen.append)
    engine.subscribe(lambda alert: 1 / 0)
    assert len(engine.process(event(rk, "x"))) == 1 and len(seen) == 1 and len(engine.errors) == 1
    off(); engine.reset()
    engine.process(event(rk, "x"))
    assert len(seen) == 1


def test_reset_lets_a_rule_alert_again(rk):
    engine = rk.RuleEngine()
    engine.add(rk.Rule("r", rk.KindIs("x"), 2))
    engine.process(event(rk, "x")); assert len(engine.process(event(rk, "x"))) == 1
    engine.reset()
    engine.process(event(rk, "x")); assert len(engine.process(event(rk, "x"))) == 1
