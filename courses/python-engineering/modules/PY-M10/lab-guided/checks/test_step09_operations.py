"""Step 9 - Operations: the audit trail says who did what without saying what they wrote, the readiness probe follows the life of the process, and the service starts only with a real secret."""
from __future__ import annotations

import logging

import pytest
from lab_support import SECRET


def audit_records(records):
    return [r for r in records if r.name == "ticketapi.audit"]


# ------------------------------------------------------------------------------------------------------------------------------------------- audit trail
def test_creating_a_ticket_is_audited_with_who_what_and_which_request(api, records):
    r = api.post("/tickets", json={"title": "Printer on fire", "body": "my password is hunter2"}, headers={**api.as_("alice"), "x-request-id": "req-create-1"})
    created = records.named("ticket.created")
    assert len(created) == 1
    rec = created[0]
    assert (rec.event, rec.ticket, rec.actor, rec.request_id) == ("ticket.created", r.json()["id"], "alice", "req-create-1")
    assert rec.levelno == logging.INFO


def test_updating_a_ticket_is_audited_with_the_names_of_the_fields_and_not_their_values(api, records):
    t = api.new_ticket("alice")
    api.patch(f"/tickets/{t['id']}", json={"title": "A very private new title", "priority": "high"}, headers={**api.as_("alice"), "x-request-id": "req-upd-1"})
    rec = records.named("ticket.updated")
    assert len(rec) == 1 and (rec[0].ticket, rec[0].actor, rec[0].fields, rec[0].request_id) == (t["id"], "alice", ["priority", "title"], "req-upd-1")


def test_deleting_a_ticket_is_audited_with_the_admin(api, records):
    t = api.new_ticket("alice")
    api.delete(f"/tickets/{t['id']}", headers={**api.as_("root", "admin"), "x-request-id": "req-del-1"})
    rec = records.named("ticket.deleted")
    assert len(rec) == 1 and (rec[0].ticket, rec[0].actor, rec[0].request_id) == (t["id"], "root", "req-del-1")


def test_a_refused_request_is_not_audited_as_an_action(api, records):
    t = api.new_ticket("alice")
    api.patch(f"/tickets/{t['id']}", json={"status": "closed"}, headers=api.as_("alice"))                   # 403
    api.patch(f"/tickets/{t['id']}", json={"title": "A new title"}, headers=api.as_("bob"))                 # 404
    api.delete(f"/tickets/{t['id']}", headers=api.as_("bob"))                                               # 403
    api.post("/tickets", json={"title": "x", "body": ""}, headers=api.as_("alice"))                          # 422
    assert records.named("ticket.updated") == [] and records.named("ticket.deleted") == []
    assert len(records.named("ticket.created")) == 1


def test_no_log_line_contains_what_a_user_wrote_a_token_or_the_secret(api, records):
    title, body = "Unmistakable-title-8841", "Unmistakable-body-8842 password=hunter2"
    token = api.token("alice", "reader")
    t = api.post("/tickets", json={"title": title, "body": body}, headers={"Authorization": f"Bearer {token}"}).json()
    api.patch(f"/tickets/{t['id']}", json={"title": "Unmistakable-new-title-8843"}, headers={"Authorization": f"Bearer {token}"})
    api.get("/tickets", params={"q": "Unmistakable-query-8844"}, headers={"Authorization": f"Bearer {token}"})
    api.get("/tickets", headers={"Authorization": "Bearer " + token[:-4] + "AAAA"})
    api.delete(f"/tickets/{t['id']}", headers=api.as_("root", "admin"))
    text = "\n".join(r.getMessage() + " " + str(sorted(r.__dict__.items())) for r in audit_records(records))
    for secret in ("Unmistakable", "hunter2", token, token.split(".")[1], SECRET, "Authorization", "Bearer"):
        assert secret not in text, secret


def test_every_audit_record_carries_an_event_name_and_the_request_id(api, records):
    t = api.new_ticket("alice")
    api.patch(f"/tickets/{t['id']}", json={"title": "A new title"}, headers=api.as_("alice"))
    api.get("/tickets")
    api.delete(f"/tickets/{t['id']}", headers=api.as_("root", "admin"))
    recs = [r for r in audit_records(records) if getattr(r, "event", "").startswith(("ticket.", "auth."))]
    assert len(recs) == 4
    assert all(r.event and r.request_id and r.request_id != "-" for r in recs)


def test_audit_records_use_the_audit_logger_and_nothing_else_logs_user_data(api, records):
    api.new_ticket("alice", title="Unmistakable-title-9911")
    assert all(r.name == "ticketapi.audit" or "Unmistakable" not in r.getMessage() for r in records)


# ------------------------------------------------------------------------------------------------------------------------------------------- readiness and lifecycle
def test_the_service_is_not_ready_until_it_has_started_and_not_ready_after_it_stops(api, records):
    built = api.build()
    assert built.get("/readyz").status_code == 503
    assert built.get("/readyz").json()["code"] == "not_ready"
    assert built.get("/healthz").json() == {"status": "ok"}
    with built.client:
        assert built.get("/readyz").status_code == 200 and built.get("/readyz").json() == {"status": "ready"}
        assert built.get("/healthz").status_code == 200
    assert built.get("/readyz").status_code == 503


def test_starting_and_stopping_are_audited(api, records):
    built = api.build()
    with built.client:
        pass
    assert [r.event for r in records if getattr(r, "event", "").startswith("lifecycle.")] == ["lifecycle.start", "lifecycle.stop"]


def test_the_health_routes_answer_json_and_are_not_cached(api):
    for path in ("/healthz", "/readyz"):
        r = api.get(path)
        assert r.headers["content-type"].startswith(("application/json", "application/problem+json")) and r.headers["cache-control"] == "no-store"


def test_the_service_answers_before_the_lifespan_has_run_for_everything_but_readiness(api):
    assert api.new_ticket("alice")["id"] == 1                  # the table is created when the application is built, not when it is started


# ------------------------------------------------------------------------------------------------------------------------------------------- independence
def test_two_applications_share_nothing(ta, tmp_path, clock):
    from lab_support import Api

    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    one = Api(ta, tmp_path / "one", clock)
    two = Api(ta, tmp_path / "two", clock, secret="a-different-signing-secret-for-the-other-app-77", issuer="other", audience="other-clients")
    one.new_ticket("alice")
    assert one.get("/tickets", headers=one.as_("alice")).json()["total"] == 1
    assert two.get("/tickets", headers=two.as_("alice")).json()["total"] == 0
    assert two.get("/tickets", headers=one.as_("alice")).status_code == 401                         # another secret, another issuer: one app's token is nobody else's
    two.new_ticket("alice")
    two.new_ticket("alice")
    assert one.get("/tickets", headers=one.as_("alice")).json()["total"] == 1 and two.get("/tickets", headers=two.as_("alice")).json()["total"] == 2


def test_existing_rows_survive_a_restart(api, ta):
    from fastapi.testclient import TestClient

    built = api.build()
    built.new_ticket("alice")
    again = TestClient(ta.create_app(built.settings), raise_server_exceptions=False)                # the same file, a new process in effect
    assert again.get("/tickets", headers=built.as_("alice")).json()["total"] == 1


# ------------------------------------------------------------------------------------------------------------------------------------------- start from the environment
def test_app_from_env_builds_the_application_from_the_environment(ta, monkeypatch, tmp_path):
    monkeypatch.setenv("TICKETAPI_SECRET", SECRET)
    monkeypatch.setenv("TICKETAPI_DB", str(tmp_path / "env.db"))
    app = ta.app_from_env()
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/healthz").status_code == 200
    assert client.get("/tickets").status_code == 401
    assert (tmp_path / "env.db").exists()


@pytest.mark.parametrize("missing", ["TICKETAPI_SECRET", "TICKETAPI_DB"])
def test_app_from_env_refuses_to_start_without_its_settings(ta, monkeypatch, tmp_path, missing):
    monkeypatch.setenv("TICKETAPI_SECRET", SECRET)
    monkeypatch.setenv("TICKETAPI_DB", str(tmp_path / "env.db"))
    monkeypatch.delenv(missing)
    with pytest.raises(ta.SettingsError):
        ta.app_from_env()
    assert not (tmp_path / "env.db").exists()


def test_app_from_env_refuses_a_weak_secret_and_never_falls_back_to_a_default(ta, monkeypatch, tmp_path):
    monkeypatch.setenv("TICKETAPI_DB", str(tmp_path / "env.db"))
    for weak in ("secret", "changeme", "a" * 40, "ab" * 20, ""):
        monkeypatch.setenv("TICKETAPI_SECRET", weak)
        with pytest.raises(ta.SettingsError):
            ta.app_from_env()
    assert not (tmp_path / "env.db").exists()


def test_no_secret_is_written_into_the_module_itself(ta):
    import inspect

    source = inspect.getsource(ta)
    assert "correct-horse-battery-staple" not in source
    import re

    assert not re.search(r"(?i)(secret|password|api[_-]?key)\s*=\s*[\"'][^\"']{8,}[\"']", source), "a literal secret in the source"
