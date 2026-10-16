"""Published acceptance checks: examples taken from SPEC.md. They show the shape of the answers; the instructors' suite tests every sentence of the specification, hostile input and the details
of the window arithmetic. A project that passes only these is not finished. Your own tests (in project/tests) are part of the capstone."""
from __future__ import annotations

import json

import pytest

from lab_support import raw

IP = "203.0.113.5"
RULES_ARGS = ("window_seconds", "brute_force_failures", "spray_users", "compromise")


def test_01_a_valid_line_becomes_an_event_and_a_blank_line_is_nothing(aw):
    event = aw.parse_line(raw(0, "alice", "2001:DB8:0::1", "failure"), 1)
    assert (event.user, event.ip, event.outcome) == ("alice", "2001:db8::1", "failure") and event.ts.utcoffset().total_seconds() == 0
    assert aw.parse_line(b"  \n", 2) is None


@pytest.mark.parametrize("data,code", [(b"{nope", "not_json"), (b"[]", "not_object"), (b'{"ts": "2026-10-14T12:00:00Z"}', "missing_field"), (b'{"ts": 5, "user": "a", "ip": "1.1.1.1", "outcome": "success"}', "bad_type"),
                                       (b'{"ts": "2026-13-14T12:00:00Z", "user": "a", "ip": "1.1.1.1", "outcome": "success"}', "bad_timestamp"),
                                       (b'{"ts": "2026-10-14T12:00:00Z", "user": "a b", "ip": "1.1.1.1", "outcome": "success"}', "bad_user"),
                                       (b'{"ts": "2026-10-14T12:00:00Z", "user": "a", "ip": "1.1.1", "outcome": "success"}', "bad_ip"),
                                       (b'{"ts": "2026-10-14T12:00:00Z", "user": "a", "ip": "1.1.1.1", "outcome": "ok"}', "bad_outcome"), (b"\xff\n", "bad_encoding")])
def test_02_an_unusable_line_has_a_code_and_the_line_number(aw, data, code):
    with pytest.raises(aw.ParseError) as info:
        aw.parse_line(data, 9)
    assert (info.value.code, info.value.line_no) == (code, 9)


def test_03_too_many_unusable_lines_stop_the_reading(aw):
    import io

    seen = []
    assert [e.user for e in aw.read_events(io.BytesIO(raw(0, "a", IP, "success") + b"x\n" + raw(1, "b", IP, "success")), on_bad=seen.append)] == ["a", "b"] and len(seen) == 1
    with pytest.raises(aw.TooManyErrors):
        list(aw.read_events(io.BytesIO(b"x\ny\n"), max_bad=1))


def test_04_five_failures_inside_the_window_are_one_brute_force_finding(aw, events):
    report = aw.detect([events(t, "alice", IP, "failure") for t in (0, 10, 20, 30, 40, 50)], aw.Rules())
    assert [(f.kind, f.severity, f.subject, f.count) for f in report.findings] == [("brute_force", "medium", f"alice@{IP}", 5)]


def test_05_a_failure_exactly_one_window_old_is_outside_the_window(aw, events):
    rules = aw.Rules(window_seconds=60, brute_force_failures=3)
    assert aw.detect([events(t, "a", IP, "failure") for t in (0, 30, 60)], rules).findings == ()
    assert len(aw.detect([events(t, "a", IP, "failure") for t in (0, 30, 59)], rules).findings) == 1


def test_06_a_success_after_a_brute_force_episode_is_a_high_severity_compromise(aw, events):
    rules = aw.Rules(window_seconds=60, brute_force_failures=3)
    report = aw.detect([events(t, "a", IP, "failure") for t in (0, 10, 20)] + [events(30, "a", IP, "success")], rules)
    assert [(f.kind, f.severity) for f in report.findings] == [("brute_force", "medium"), ("compromise_after_failures", "high")]


def test_07_failures_against_several_users_from_one_address_are_a_password_spray(aw, events):
    rules = aw.Rules(window_seconds=60, brute_force_failures=100, spray_users=3)
    report = aw.detect([events(0, "a", IP, "failure"), events(5, "b", IP, "failure"), events(10, "c", IP, "failure")], rules)
    (finding,) = report.findings
    assert (finding.kind, finding.subject, finding.user, finding.users, finding.count) == ("password_spray", IP, None, ("a", "b", "c"), 3)


def test_08_an_event_older_than_the_one_before_it_is_skipped_and_counted(aw, events):
    report = aw.detect([events(100, "a", IP, "failure"), events(50, "a", IP, "failure")], aw.Rules())
    assert (report.events, report.failures, report.out_of_order) == (2, 1, 1)


def test_09_rules_are_validated_and_read_from_yaml_without_executing_anything(aw):
    assert aw.parse_rules("window_seconds: 60\ncompromise: false\n") == aw.Rules(window_seconds=60, compromise=False)
    for bad in ("window_seconds: 0", "spray_users: true", "colour: red", "- a", "x: [", "!!python/object/apply:os.system ['true']"):
        with pytest.raises(aw.ConfigError):
            aw.parse_rules(bad)


def test_10_json_output_has_a_schema_a_summary_and_sorted_keys(aw, events):
    report = aw.detect([events(t, "a", IP, "failure") for t in (0, 1, 2, 3, 4)], aw.Rules())
    text = aw.render(report, "json")
    body = json.loads(text)
    assert body["schema"] == 1 and body["summary"] == {"events": 5, "failures": 5, "out_of_order": 0, "findings": 1} and text.endswith("\n")
    assert body["findings"][0]["first_ts"] == "2026-10-14T12:00:00Z" and body["findings"][0]["user"] == "a"
    assert text == json.dumps(body, sort_keys=True, indent=2) + "\n"
    with pytest.raises(ValueError):
        aw.render(report, "xml")


def test_11_the_command_line_scans_a_file_and_reports_to_standard_output(cli, tmp_path):
    path = tmp_path / "in.jsonl"
    path.write_bytes(b"".join(raw(t, "alice", IP, "failure") for t in (0, 10, 20, 30, 40)))
    done = cli("scan", "--format", "json", str(path))
    assert done.returncode == 0 and json.loads(done.stdout)["summary"]["findings"] == 1
    assert cli("scan", "--fail-on-findings", str(path)).returncode == 1


def test_12_standard_input_the_version_and_the_exit_status_two(cli, aw, tmp_path):
    assert b"brute_force" in cli("scan", stdin=b"".join(raw(t, "alice", IP, "failure") for t in (0, 1, 2, 3, 4))).stdout
    assert cli("--version").stdout.decode().strip() == f"authwatch {aw.__version__}"
    assert cli("scan", "--format", "xml").returncode == 2
    assert cli("scan", "--rules", str(tmp_path / "missing.yaml")).returncode == 2


def test_13_unreadable_input_and_unusable_lines_have_their_own_exit_status_and_no_traceback(cli, tmp_path):
    missing = cli("scan", str(tmp_path / "nothing.jsonl"))
    assert missing.returncode == 3 and b"Traceback" not in missing.stderr
    done = cli("scan", "--max-bad", "1", stdin=b"junk one\njunk two\n")
    assert done.returncode == 3 and b"junk" not in done.stderr


def test_14_the_report_can_be_written_atomically_with_restricted_permissions(cli, tmp_path):
    import stat

    target = tmp_path / "report.json"
    done = cli("scan", "--format", "json", "--output", str(target), stdin=raw(0, "a", IP, "success"))
    assert done.returncode == 0 and done.stdout == b"" and json.loads(target.read_text())["summary"]["events"] == 1
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
