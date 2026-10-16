"""Private source intake is explicit, external, and never a publication path."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "inventory"))
from common import SOURCES_DIR, list_pdfs  # noqa: E402

QUARANTINED = "INTERNAL FRONTEND DEVELOPER ONBOARDING PLAYBOOK.pdf"


def test_public_checkout_never_contains_quarantined_pdf():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("CDB_PRIVATE_SOURCE_DIR", None)
        found = list_pdfs()
    assert QUARANTINED not in [p.name for p in found]


def test_private_input_requires_explicit_external_source(tmp_path):
    (tmp_path / QUARANTINED).write_bytes(b"synthetic local fixture; not a real source PDF")
    with patch.dict(os.environ, {"CDB_PRIVATE_SOURCE_DIR": str(tmp_path)}):
        found = list_pdfs()
    assert [x.name for x in found].count(QUARANTINED) == 1
    assert all(x.parent == SOURCES_DIR for x in found if x.name != QUARANTINED)
    assert next(x for x in found if x.name == QUARANTINED).parent == tmp_path


def test_missing_private_file_fails_closed(tmp_path):
    with patch.dict(os.environ, {"CDB_PRIVATE_SOURCE_DIR": str(tmp_path)}):
        with pytest.raises(RuntimeError, match="private source missing"):
            list_pdfs()


def test_unknown_private_directory_fails_closed(tmp_path):
    with patch.dict(os.environ, {"CDB_PRIVATE_SOURCE_DIR": str(tmp_path / "not-a-directory")}):
        with pytest.raises(RuntimeError, match="unavailable"):
            list_pdfs()


def test_private_source_inside_public_checkout_rejected():
    (ROOT / ".work").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / ".work") as nested:
        (Path(nested) / QUARANTINED).write_bytes(b"synthetic")
        with patch.dict(os.environ, {"CDB_PRIVATE_SOURCE_DIR": nested}):
            with pytest.raises(RuntimeError, match="outside the public repository"):
                list_pdfs()


def test_private_source_symlink_rejected(tmp_path):
    source = tmp_path / "bytes.pdf"
    source.write_bytes(b"synthetic")
    try:
        (tmp_path / QUARANTINED).symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this runner")
    with patch.dict(os.environ, {"CDB_PRIVATE_SOURCE_DIR": str(tmp_path)}):
        with pytest.raises(RuntimeError, match="not a regular file"):
            list_pdfs()


def test_explicit_alternative_root_not_augmented(tmp_path):
    explicit = tmp_path / "normal"
    private = tmp_path / "private"
    explicit.mkdir()
    private.mkdir()
    (explicit / "synthetic.pdf").write_bytes(b"fixture")
    (private / QUARANTINED).write_bytes(b"fixture")
    with patch.dict(os.environ, {"CDB_PRIVATE_SOURCE_DIR": str(private)}):
        result = list_pdfs(explicit)
    assert [x.name for x in result] == ["synthetic.pdf"]
