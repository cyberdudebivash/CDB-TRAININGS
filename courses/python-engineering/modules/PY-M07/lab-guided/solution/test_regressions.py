"""Reference regression tests for the guided lab: each vulnerability that was fixed has a test that fails if it is reintroduced."""
import json
import os
import pickle
import sqlite3
import ssl

import pytest

import helpdesk


@pytest.fixture()
def conn():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE users (name TEXT, email TEXT, role TEXT)")
    db.executemany("INSERT INTO users VALUES (?, ?, ?)", [("ada", "a@example.test", "agent"), ("grace", "g@example.test", "admin")])
    yield db
    db.close()


class Marker:
    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return (os.mkdir, (self.path,))


@pytest.mark.parametrize("expr", ["__import__('os').getpid()", "open('x')", "x + 1", "(1).__class__", "2 ** 100", "9" * 200, "1 / 0", ""])
def test_v1_calculator_accepts_arithmetic_only(expr):
    with pytest.raises(ValueError):
        helpdesk.calculate(expr)


def test_v1_calculator_still_calculates():
    assert helpdesk.calculate("(1 + 2) * 3") == 9


@pytest.mark.parametrize("name", ["x' OR '1'='1", "ada' --"])
def test_v2_sql_text_is_data(conn, name):
    assert helpdesk.find_users(conn, name) == []


def test_v3_directory_names_are_not_shell_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    victim = tmp_path / "dir; echo x > injected.txt"       # an existing directory whose NAME contains shell syntax
    victim.mkdir()
    (victim / "inside.txt").write_text("x")
    assert helpdesk.list_files(str(victim)) == ["inside.txt"]
    assert not (tmp_path / "injected.txt").exists()


def test_v4_attachments_cannot_leave_the_folder(tmp_path):
    base = tmp_path / "files"
    base.mkdir()
    (tmp_path / "secret.txt").write_bytes(b"s")
    for name in ("../secret.txt", str(tmp_path / "secret.txt")):
        with pytest.raises(ValueError):
            helpdesk.read_attachment(base, name)
    try:
        (base / "link").symlink_to(tmp_path / "secret.txt")
    except (OSError, NotImplementedError):
        return
    with pytest.raises(ValueError):
        helpdesk.read_attachment(base, "link")


def test_v5_sessions_are_data_not_code(tmp_path):
    marker = tmp_path / "ran"
    with pytest.raises(ValueError):
        helpdesk.load_session(pickle.dumps(Marker(str(marker))))
    assert not marker.exists()
    with pytest.raises(ValueError):
        helpdesk.load_session(json.dumps({"user": "ada", "role": "root"}).encode())


def test_v6_yaml_cannot_build_objects(tmp_path):
    marker = tmp_path / "ran"
    with pytest.raises(ValueError):
        helpdesk.load_config(f"!!python/object/apply:os.mkdir [{json.dumps(str(marker))}]")
    assert not marker.exists()


def test_v7_tls_is_verified():
    ctx = helpdesk.make_tls_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True


def test_v8_each_hash_has_its_own_salt():
    assert helpdesk.hash_password("hunter2") != helpdesk.hash_password("hunter2")
    assert helpdesk.verify_password("hunter2", helpdesk.hash_password("hunter2")) is True
