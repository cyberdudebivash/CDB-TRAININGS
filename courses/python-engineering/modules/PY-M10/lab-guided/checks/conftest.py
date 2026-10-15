"""Fixtures for the PY-M10 guided-lab checks.

LAB_TARGET chooses the module under test: `starter` (default, your work), `solution` (the public reference) or `import` (the instructors' mutation check, which puts the module on
the import path itself). Every check talks to the service the way a client would: through Starlette's in-process TestClient, so no port is opened and nothing leaves the machine.

`api` builds the application lazily, inside the test, so that a step you have not written yet is reported as a failed check and not as a set-up error.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = os.environ.get("LAB_TARGET", "starter")
if TARGET not in {"starter", "solution", "import"}:
    raise ValueError("LAB_TARGET must be starter, solution or import")
if TARGET != "import":
    sys.path.insert(0, str(LAB / TARGET))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_support import Clock, LazyApi  # noqa: E402


@pytest.fixture(scope="session")
def ta():
    import ticketapi

    return ticketapi


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def api(ta, tmp_path, clock):
    """api.<anything> builds the service on first use with default settings; api.build(**settings) builds it with other settings."""
    return LazyApi(ta, tmp_path, clock)


@pytest.fixture(scope="module")
def shared_tmp(tmp_path_factory):
    return tmp_path_factory.mktemp("shared")


class Records:
    """The audit records emitted so far (logging.LogRecord objects of the logger `ticketapi.audit`), read from pytest's log capture each time they are asked for."""

    def __init__(self, caplog) -> None:
        self._caplog = caplog

    def __iter__(self):
        return iter(self._caplog.records)

    def __len__(self) -> int:
        return len(self._caplog.records)

    def __getitem__(self, index):
        return self._caplog.records[index]

    def named(self, event: str):
        return [r for r in self._caplog.records if getattr(r, "event", None) == event]


@pytest.fixture
def records(caplog):
    caplog.set_level(logging.DEBUG, logger="ticketapi.audit")
    return Records(caplog)
