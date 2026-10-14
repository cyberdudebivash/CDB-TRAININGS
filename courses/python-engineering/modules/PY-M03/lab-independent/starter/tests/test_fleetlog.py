"""Tests for the flat modules (they import models, util and report directly). Run from the starter folder:  python -m pytest"""
from pathlib import Path

import pytest

import report
import util

DATA = Path(__file__).resolve().parents[1] / "data" / "trips.csv"


def test_parse_and_consumption():
    trips = report.load(str(DATA))
    assert len(trips) == 5
    assert report.consumption(trips) == {"truck-9": 22.0, "van-1": 8.4, "van-2": 9.0}


def test_worst_orders_by_consumption():
    values = report.consumption(report.load(str(DATA)))
    assert [v for v, _ in report.worst(values, 2)] == ["truck-9", "van-2"]


def test_invalid_lines():
    with pytest.raises(ValueError):
        util.parse_trip("van-1,abc,3")
