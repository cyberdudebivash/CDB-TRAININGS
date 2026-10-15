"""The structural personal-data guard: what it flags, what it lets through, and that the repository itself is clean.

The sample strings below are fictitious on purpose; this file is excluded from the repository scan by the allow-list (path_globs).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
import check_privacy as cp  # noqa: E402


def j(*parts: str) -> str:
    """Build a sample at run time so that this source file itself never contains a string shaped like personal data."""
    return "".join(parts)


def kinds(text: str) -> list[tuple[str, str]]:
    return [(f.kind, f.masked) for f in cp.scan_text(text, "sample")]


def test_a_consumer_mailbox_address_is_flagged_and_masked():
    found = kinds(j("Contact: jane.q.public", "@", "gmail.com for details"))
    assert len(found) == 1 and found[0][0] == "e-mail"
    assert "jane.q.public" not in found[0][1] and found[0][1].endswith("@gmail.com") and found[0][1].startswith("j*")


@pytest.mark.parametrize("text", [
    "user@example.com", "someone@mail.example.org", "lab@evil.test", "a@localhost.localdomain.invalid", "noreply@users.noreply.github.com", "info@cyberdudebivash.com",
    j("npm install eslint", "@", "10.12.0 react", "@", "19.3.0"), j("logo", "@", "2x.png"), j("0123456789abcdef0123456789abcdef01234567", "@", "x.y"),
])
def test_reserved_placeholder_domains_package_pins_and_file_names_are_not_flagged(text):
    assert kinds(text) == []


def test_a_telephone_number_is_flagged_and_masked():
    for text in (j("Call +", "91 98765 43210 today"), "Mobile: 98765 43210", j("tel +", "44 20 7946 0958 abc")):
        found = kinds(text)
        assert found and found[0][0] == "phone", text
        assert all(ch in "*0123456789" for ch in found[0][1]) and found[0][1].count("*") >= 6


@pytest.mark.parametrize("text", ["version 3.15.0 released 2026-10-09", "ip 192.168.100.200 port 8080", "phone 12345", "id 1111111111", "sha 0123456789abcdef", "Phone: 0000000000"])
def test_numbers_that_are_not_telephone_numbers_are_not_flagged(text):
    assert kinds(text) == []


def test_the_allowlist_never_contains_a_consumer_mailbox_provider():
    allowed = yaml.safe_load(cp.ALLOWLIST.read_text(encoding="utf-8"))["email_domains"]
    banned = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "proton.me", "protonmail.com", "aol.com", "rediffmail.com"}
    assert not banned & {d.lower() for d in allowed}


def test_the_repository_contains_no_unreviewed_personal_data_shapes():
    assert [str(f) for f in cp.scan_repo()] == []


def test_the_scan_reaches_generated_data_and_course_material():
    files = {p.relative_to(ROOT).as_posix() for p in cp.repo_text_files()}
    assert any(f.startswith("docs/audits/data/page_records/") for f in files) and any(f.startswith("courses/python-engineering/modules/") for f in files)
    assert not any(f.endswith(".pdf") for f in files)
