"""Automated checks for the PY-M07 guided lab.

`test_works_*` tests describe behaviour that must keep working (they pass on the vulnerable starter, and must still pass after your fix).
`test_exploit_*` tests attack the code with harmless probes; they fail while the vulnerability exists. `test_static_*` runs ruff's security rules.
"""
from __future__ import annotations

import json
import os
import pickle
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")


# ------------------------------------------------------------------------------------------ V1 expression evaluation
@pytest.mark.parametrize("expr, expected", [("1 + 2 * 3", 7), ("(1 + 2) * 3", 9), ("-4 + 10 / 4", -1.5), ("2 ** 10", 1024), ("7 % 4", 3), (" 5 ", 5)])
def test_works_calculator(helpdesk, expr, expected):
    assert helpdesk.calculate(expr) == expected


@pytest.mark.parametrize("expr", ["__import__('os').getpid()", "open('x')", "[1, 2][0]", "'a' * 3", "1 if True else 2", "x + 1", "(1).__class__", "2 ** 100", "9 ** 99999", "1 / 0", "", "1 +", "9" * 200])
def test_exploit_calculator_rejects_everything_but_arithmetic(helpdesk, expr):
    with pytest.raises(ValueError):
        helpdesk.calculate(expr)


# ------------------------------------------------------------------------------------------ V2 SQL
def test_works_find_users(helpdesk, conn):
    assert helpdesk.find_users(conn, "ada") == [("ada", "ada@example.test", "agent")]
    assert helpdesk.find_users(conn, "nobody") == []


def test_exploit_names_with_apostrophes_are_data(helpdesk, conn):
    assert helpdesk.find_users(conn, "O'Brien") == [("O'Brien", "ob@example.test", "viewer")]


@pytest.mark.parametrize("name", ["x' OR '1'='1", "' OR 1=1 --", "ada' --", "nobody' UNION SELECT name, email, role FROM users --"])
def test_exploit_sql_injection_returns_nothing(helpdesk, conn, name):
    assert helpdesk.find_users(conn, name) == []


# ------------------------------------------------------------------------------------------ V3 shell injection
@pytest.mark.skipif(sys.platform == "win32", reason="the lab's shell probe uses POSIX shells")
def test_works_list_files(helpdesk, tmp_path):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    assert helpdesk.list_files(str(tmp_path)) == ["a.txt", "b.txt"]
    assert helpdesk.list_files(str(tmp_path / "..")) is not None


def test_works_list_files_rejects_missing_directories(helpdesk, tmp_path):
    with pytest.raises((FileNotFoundError, NotADirectoryError)):
        helpdesk.list_files(str(tmp_path / "missing"))


@pytest.mark.skipif(sys.platform == "win32", reason="the lab's shell probe uses POSIX shells")
def test_exploit_shell_metacharacters_are_data(helpdesk, tmp_path, capfd, monkeypatch):
    victim = tmp_path / "dir; echo INJECTED > injected.txt"
    victim.mkdir()
    (victim / "inside.txt").write_text("x")
    monkeypatch.chdir(tmp_path)
    assert helpdesk.list_files(str(victim)) == ["inside.txt"]          # the odd name is just a directory name
    out = capfd.readouterr()
    assert "INJECTED" not in out.out + out.err
    assert not (tmp_path / "injected.txt").exists(), "a shell command embedded in the directory name was executed"
    with pytest.raises((FileNotFoundError, NotADirectoryError)):
        helpdesk.list_files(f"{tmp_path}; echo INJECTED > injected.txt")
    assert not (tmp_path / "injected.txt").exists()


# ------------------------------------------------------------------------------------------ V4 path traversal
def test_works_read_attachment(helpdesk, tmp_path):
    base = tmp_path / "attachments"
    (base / "sub").mkdir(parents=True)
    (base / "ok.txt").write_bytes(b"hello")
    (base / "sub" / "deep.txt").write_bytes(b"deep")
    assert helpdesk.read_attachment(base, "ok.txt") == b"hello"
    assert helpdesk.read_attachment(base, "sub/deep.txt") == b"deep"
    assert helpdesk.read_attachment(base, "sub/../ok.txt") == b"hello"


def test_exploit_path_traversal_is_rejected(helpdesk, tmp_path):
    base = tmp_path / "attachments"
    base.mkdir()
    (base / "ok.txt").write_bytes(b"hello")
    (tmp_path / "secret.txt").write_bytes(b"TOP SECRET")
    outside = str(tmp_path / "secret.txt")
    for name in ("../secret.txt", "sub/../../secret.txt", outside, "..", ""):
        with pytest.raises(ValueError, match="invalid attachment name"):
            helpdesk.read_attachment(base, name)


def test_exploit_symlinks_cannot_escape(helpdesk, tmp_path):
    base = tmp_path / "attachments"
    base.mkdir()
    (tmp_path / "secret.txt").write_bytes(b"TOP SECRET")
    try:
        (base / "link.txt").symlink_to(tmp_path / "secret.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available here")
    with pytest.raises(ValueError, match="invalid attachment name"):
        helpdesk.read_attachment(base, "link.txt")


# ------------------------------------------------------------------------------------------ V5 and V6 deserialisation
class _Probe:
    """Pickle payload whose deserialisation performs a harmless, observable action: it creates an empty directory."""

    def __init__(self, marker: str):
        self.marker = marker

    def __reduce__(self):
        return (os.mkdir, (self.marker,))


def test_works_session_round_trip(helpdesk):
    session = {"user": "ada", "role": "agent"}
    assert helpdesk.load_session(helpdesk.dump_session(session)) == session


@pytest.mark.parametrize("session", [{"user": "", "role": "agent"}, {"user": "ada", "role": "root"}, {"user": "ada"}, {"user": "a" * 65, "role": "agent"}, ["ada", "agent"]])
def test_exploit_invalid_sessions_are_rejected_when_dumped(helpdesk, session):
    with pytest.raises(ValueError, match="invalid session"):
        helpdesk.dump_session(session)


def test_exploit_session_loader_never_runs_code(helpdesk, tmp_path):
    marker = tmp_path / "pickle-executed"
    for blob in (pickle.dumps(_Probe(str(marker))), b"\x80\x04N.", b"not json", b"[]", b'{"user": "ada", "role": "root"}', b"\xff\xfe"):
        with pytest.raises(ValueError, match="invalid session"):
            helpdesk.load_session(blob)
    assert not marker.exists(), "the payload was executed while it was being loaded (validating afterwards is too late)"


def test_works_load_config(helpdesk):
    assert helpdesk.load_config("name: demo\nretries: 3\nflags: [a, b]\n") == {"name": "demo", "retries": 3, "flags": ["a", "b"]}


def test_exploit_yaml_loader_never_builds_python_objects(helpdesk, tmp_path):
    marker = tmp_path / "yaml-executed"
    payload = f"!!python/object/apply:os.mkdir [{json.dumps(str(marker))}]"
    with pytest.raises(ValueError, match="invalid configuration"):
        helpdesk.load_config(payload)
    assert not marker.exists(), "the YAML loader executed a Python tag"
    for text in ("- a\n- b\n", "42", "key: [unclosed"):
        with pytest.raises(ValueError, match="invalid configuration"):
            helpdesk.load_config(text)
    assert yaml.safe_load("a: 1") == {"a": 1}


# ------------------------------------------------------------------------------------------ V7 TLS
def test_exploit_tls_context_verifies_certificates_and_names(helpdesk):
    import ssl

    ctx = helpdesk.make_tls_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED, "certificates are not being verified"
    assert ctx.check_hostname is True, "host names are not being checked"


# ------------------------------------------------------------------------------------------ V8 password storage
def test_works_password_round_trip(helpdesk):
    stored = helpdesk.hash_password("correct horse battery staple")
    assert helpdesk.verify_password("correct horse battery staple", stored) is True
    assert helpdesk.verify_password("wrong", stored) is False
    assert helpdesk.verify_password("", stored) is False


@pytest.mark.parametrize("stored", ["", "abc", "scrypt$zz$zz", "md5$00$00", "scrypt$00"])
def test_works_malformed_stored_values_never_verify(helpdesk, stored):
    assert helpdesk.verify_password("password", stored) is False


def test_exploit_legacy_md5_hashes_are_not_accepted(helpdesk):
    assert helpdesk.verify_password("password", "5f4dcc3b5aa765d61d8327deb882cf99") is False


def test_exploit_password_hashes_are_salted_and_slow(helpdesk):
    first, second = helpdesk.hash_password("hunter2"), helpdesk.hash_password("hunter2")
    assert first != second, "the same password must not always give the same hash (no salt)"
    assert first.startswith("scrypt$") and len(first.split("$")) == 3
    assert "hunter2" not in first
    import hashlib

    assert hashlib.md5(b"hunter2").hexdigest() not in first, "unsalted MD5 digest found"


# ------------------------------------------------------------------------------------------ static analysis
@pytest.mark.skipif(shutil.which("ruff") is None and not Path(sys.executable).with_name("ruff").exists(), reason="ruff is not installed")
def test_static_ruff_security_rules_are_clean():
    ruff = shutil.which("ruff") or str(Path(sys.executable).with_name("ruff"))
    proc = subprocess.run([ruff, "check", "--no-cache", "--select", "S", "--output-format", "concise", str(TARGET / "helpdesk.py")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout
