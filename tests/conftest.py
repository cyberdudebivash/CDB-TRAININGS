"""Shared fixtures for the CDB-TRAININGS test suite."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LABS = ROOT / "courses" / "soc-analyst" / "labs"
INSTRUCTOR = ROOT / "courses" / "soc-analyst" / "instructor"


def run_cli(argv: list[str]) -> tuple[int, str]:
    """Run soc_lab.cli.main in-process and capture stdout."""
    from soc_lab.cli import main

    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, buf.getvalue() + err.getvalue()


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def guided(tmp_path_factory):
    """Guided dataset (profile A) generated through the real CLI, with enrichment and truth."""
    d = tmp_path_factory.mktemp("guided")
    assert run_cli(["generate", "--profile", "guided", "--out", str(d), "--with-truth"])[0] == 0
    assert run_cli(["enrich", "--events", str(d / "events.jsonl"), "--context", str(d / "context.json"), "--out", str(d / "events.enriched.jsonl")])[0] == 0
    return d


@pytest.fixture(scope="session")
def independent(tmp_path_factory):
    d = tmp_path_factory.mktemp("independent")
    assert run_cli(["generate", "--profile", "independent", "--out", str(d), "--with-truth"])[0] == 0
    assert run_cli(["enrich", "--events", str(d / "events.jsonl"), "--context", str(d / "context.json"), "--out", str(d / "events.enriched.jsonl")])[0] == 0
    return d


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
