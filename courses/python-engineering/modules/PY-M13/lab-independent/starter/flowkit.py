"""flowkit - lazy merging and grouping, a bounded memo cache and a rollback context manager (PY-M13 independent lab).

README.md is the specification; this file only holds the names the checks import. Replace every stub with a real implementation. Standard library only.
"""
from __future__ import annotations


def merge_sorted(*sources, key=None):
    raise NotImplementedError


def group_runs(iterable, key=None):
    raise NotImplementedError


def memo(maxsize=128):
    raise NotImplementedError


class Transaction:
    pass
