"""Published checks for the PY-M09 independent lab (triage). They show the shape of the task; the instructors' suite checks much more (hundreds of awkward inputs against the
original, how the work grows, the code of the core, your own budget tests). Passing these ten is necessary, not sufficient."""
from __future__ import annotations

import ast
import time

import pytest


def alert(tr, id, ts, rule="r1", host="h1", severity=3, message="login failed for user 12", source="ids"):
    return tr.Alert(id, ts, source, rule, host, severity, message)


def test_normalize_lowers_case_collapses_spaces_and_replaces_digit_runs(tr):
    assert tr.normalize("  Login   FAILED for User 007 at 12:30 ") == "login failed for user # at #:#"
    assert tr.normalize("") == "" and tr.normalize("a\tb\nc") == "a b c"


def test_collapse_joins_alerts_within_the_window_and_splits_beyond_it(tr):
    alerts = [alert(tr, 1, 100), alert(tr, 2, 160, message="Login failed for user 99"), alert(tr, 3, 161), alert(tr, 4, 500)]
    incidents = tr.collapse(alerts, 60)
    assert [(i.first_ts, i.last_ts, i.count, i.ids) for i in incidents] == [(100, 161, 3, (1, 2, 3)), (500, 500, 1, (4,))]
    assert incidents[0].key == ("ids", "r1", "h1", "login failed for user #")


def test_collapse_orders_its_input_and_its_output(tr):
    alerts = [alert(tr, 3, 200, host="b"), alert(tr, 1, 100, host="a"), alert(tr, 2, 100, host="c"), alert(tr, 4, 150, host="a", severity=5)]
    incidents = tr.collapse(alerts, 10)
    assert [i.ids for i in incidents] == [(1,), (2,), (4,), (3,)]
    assert tr.collapse(alerts, 100)[0].ids == (1, 4) and tr.collapse(alerts, 100)[0].max_severity == 5


def test_collapse_rejects_a_bad_window_or_severity(tr):
    for bad in (-1, True, 1.5, "10"):
        with pytest.raises(ValueError):
            tr.collapse([], bad)
    with pytest.raises(ValueError):
        tr.collapse([alert(tr, 1, 1, severity=6)], 5)


def test_rank_orders_by_severity_count_time_and_id(tr):
    mk = lambda ids, first, count, sev: tr.Incident(("s", "r", "h", "m"), first, first, count, sev, ids)
    incidents = [mk((1,), 5, 2, 3), mk((2,), 1, 2, 3), mk((3,), 9, 9, 3), mk((4,), 9, 1, 5), mk((5,), 1, 2, 3)]
    assert [i.ids for i in tr.rank(incidents, 5)] == [(4,), (3,), (2,), (5,), (1,)]
    assert [i.ids for i in tr.rank(incidents, 2)] == [(4,), (3,)] and tr.rank(incidents, 0) == []
    with pytest.raises(ValueError):
        tr.rank(incidents, -1)


def test_summarize_and_render_have_the_documented_shape(tr):
    result = tr.triage([alert(tr, 1, 0), alert(tr, 2, 5), alert(tr, 3, 100, rule="r2", severity=5, message="Port scan 22")], window=10, top=2)
    assert result.summary == {"incidents": 2, "alerts": 3, "by_severity": {1: 0, 2: 0, 3: 1, 4: 0, 5: 1}, "by_rule": [("r1", 1, 2), ("r2", 1, 1)]}
    assert tr.render(result) == (
        "incidents: 2 alerts: 3\nseverity 1: 0\nseverity 2: 0\nseverity 3: 1\nseverity 4: 0\nseverity 5: 1\n"
        "rule r1: 1 incidents, 2 alerts\nrule r2: 1 incidents, 1 alerts\ntop:\n"
        "#1 [100-100] sev 5 x 1 ids/r2@h1: port scan #\n#2 [0-5] sev 3 x 2 ids/r1@h1: login failed for user #\n"
    )


def test_collapse_work_grows_roughly_linearly_with_the_number_of_incidents(tr):
    def run(n):
        alerts = [alert(tr, i, i, host=f"h{i}") for i in range(n)]          # every alert is a different incident: the original compares each with all the earlier ones
        best = float("inf")
        for _ in range(3):
            started = time.perf_counter()
            tr.collapse(alerts, 10)
            best = min(best, time.perf_counter() - started)
            if best > 1.0:
                break
        return best

    small, large = run(1500), run(6000)
    assert large / small < 9, f"four times the alerts took {large / small:.1f} times as long (linear: about 4, quadratic: about 16)"


def test_the_core_does_no_input_or_output(tr):
    forbidden = {"open", "print", "input", "json", "os", "pathlib", "read_alerts"}
    tree = ast.parse(open(tr.__file__, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {"normalize", "collapse", "rank", "summarize", "triage", "render"}:
            used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            assert not used & forbidden, f"{node.name} uses {sorted(used & forbidden)}"


def test_read_alerts_is_lazy_and_reports_the_line_of_a_bad_alert(tr, tmp_path):
    good = '{"id": 1, "ts": 5, "source": "ids", "rule": "r", "host": "h", "severity": 2, "message": "m"}'
    path = tmp_path / "alerts.jsonl"
    path.write_text(good + "\n\n" + good.replace('"id": 1', '"id": "x"') + "\n", encoding="utf-8")
    reader = tr.read_alerts(str(path))
    assert next(reader).id == 1
    with pytest.raises(tr.AlertFormatError) as raised:
        next(reader)
    assert raised.value.line == 3
    with pytest.raises(FileNotFoundError):
        next(tr.read_alerts(str(tmp_path / "missing.jsonl")))


def test_you_have_written_budget_tests_of_your_own(folder):
    path = folder / "test_budget.py"
    assert path.exists(), "write starter/test_budget.py (README, part 4)"
    tests = [n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert len(tests) >= 3, f"{len(tests)} test functions; at least three are required"
