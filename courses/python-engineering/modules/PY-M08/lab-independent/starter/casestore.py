"""casestore - a case tracker on SQLite (PY-M08 independent lab). Write the module from the specification in ../README.md.

The value classes and the error classes are given; every method of `Store` is an empty stub. Standard library only. Edit only this file.
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class CaseNotFound(LookupError):
    """No case (or no such case for a comment) has this id."""


class StaleVersion(Exception):
    """The case changed since the caller read it; `current` is the version now stored."""

    def __init__(self, current: int) -> None:
        super().__init__(f"the case is at version {current}")
        self.current = current


class RefConflict(ValueError):
    """The external reference is already used by a case with different content."""


class InvalidTransition(ValueError):
    """The case is already in the requested status."""


class ImportRejected(ValueError):
    """An import row is invalid; nothing was imported. `index` is the position of the first bad row."""

    def __init__(self, index: int, reason: str) -> None:
        super().__init__(f"row {index}: {reason}")
        self.index = index
        self.reason = reason


class SchemaTooNew(RuntimeError):
    """The database was written by a newer version of the program."""


@dataclass(frozen=True, slots=True)
class Case:
    id: int
    ref: str | None
    title: str
    reporter: str
    severity: int
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    comment_count: int


@dataclass(frozen=True, slots=True)
class Comment:
    id: int
    case_id: int
    author: str
    text: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ImportReport:
    inserted: int
    updated: int
    unchanged: int


class Store:
    """The case tracker; see ../README.md. Keep the connection in `self._db`; `orphans_dropped` counts the comments of the first release's file that had no case."""

    orphans_dropped: int

    def __init__(self, path: str | os.PathLike[str] = ":memory:", *, clock: Callable[[], datetime] | None = None) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get(self, case_id: int) -> Case:
        raise NotImplementedError

    def open_case(self, title: str, reporter: str, severity: int = 2, *, ref: str | None = None) -> Case:
        raise NotImplementedError

    def update_case(self, case_id: int, *, expected_version: int, title: str | None = None, severity: int | None = None) -> Case:
        raise NotImplementedError

    def close_case(self, case_id: int, *, expected_version: int) -> Case:
        raise NotImplementedError

    def reopen_case(self, case_id: int, *, expected_version: int) -> Case:
        raise NotImplementedError

    def delete_case(self, case_id: int, *, expected_version: int) -> None:
        raise NotImplementedError

    def add_comment(self, case_id: int, author: str, text: str) -> Comment:
        raise NotImplementedError

    def comments(self, case_id: int, *, after_id: int | None = None, limit: int = 50) -> list[Comment]:
        raise NotImplementedError

    def find(self, *, reporter: str | None = None, status: str | None = None, min_severity: int | None = None, text: str | None = None,
             after_id: int | None = None, limit: int = 50) -> list[Case]:
        raise NotImplementedError

    def stats(self) -> dict[str, Any]:
        raise NotImplementedError

    def import_cases(self, rows: Iterable[Mapping[str, Any]]) -> ImportReport:
        raise NotImplementedError
