"""Behaviour specification of fleetlog (see ../README.md). Written against the package `fleetlog`."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "starter" / "data" / "trips.csv"
D = Decimal


@pytest.fixture(scope="module")
def fleetlog(project):
    sys.path.insert(0, str(project / "src"))
    for name in [n for n in sys.modules if n == "fleetlog" or n.startswith("fleetlog.")]:
        del sys.modules[name]
    try:
        import fleetlog as module

        yield module
    finally:
        sys.path.remove(str(project / "src"))
        for name in [n for n in sys.modules if n == "fleetlog" or n.startswith("fleetlog.")]:
            del sys.modules[name]


def test_parse_trip_valid(fleetlog):
    trip = fleetlog.parse_trip(" van-1 , 120 , 9.6 ")
    assert (trip.vehicle, trip.distance_km, trip.fuel_l) == ("van-1", D("120"), D("9.6"))
    assert isinstance(trip.distance_km, Decimal) and isinstance(trip.fuel_l, Decimal)
    assert fleetlog.parse_trip("v,1,0").fuel_l == D("0")


@pytest.mark.parametrize("line", ["", "van-1,120", "van-1,abc,3", ",1,1", "van,0,1", "van,-1,1", "van,1,-1", "van,1,1,1", "van,NaN,1", "van,1,Infinity", "van,1,"])
def test_parse_trip_invalid(fleetlog, line):
    with pytest.raises(ValueError, match="invalid trip"):
        fleetlog.parse_trip(line)


def test_parse_lines_skips_comments_and_blanks(fleetlog):
    trips = fleetlog.parse_lines(["# header", "", "  ", "a,10,1", "  # note", "b,20,3"])
    assert [t.vehicle for t in trips] == ["a", "b"]
    with pytest.raises(ValueError, match="invalid trip: b,x,1"):
        fleetlog.parse_lines(["a,10,1", "b,x,1"])


def test_consumption_is_exact_and_rounds_half_up(fleetlog):
    trips = fleetlog.parse_lines(DATA.read_text(encoding="utf-8").splitlines())
    assert fleetlog.consumption(trips) == {"truck-9": D("22.00"), "van-1": D("8.40"), "van-2": D("9.00")}
    assert list(fleetlog.consumption(trips)) == ["truck-9", "van-1", "van-2"]
    half = fleetlog.parse_lines(["x,200,0.45"])            # 0.225 L/100km: half-up gives 0.23, half-even would give 0.22
    assert fleetlog.consumption(half) == {"x": D("0.23")}
    third = fleetlog.parse_lines(["y,3,0.1", "y,3,0.1"])    # exact decimal sums: (0.1 + 0.1) / 6 * 100
    assert fleetlog.consumption(third) == {"y": D("3.33")}
    assert fleetlog.consumption([]) == {}
    assert all(isinstance(v, Decimal) for v in fleetlog.consumption(trips).values())


def test_worst_orders_and_validates(fleetlog):
    values = {"a": D("5.00"), "b": D("9.00"), "c": D("9.00"), "d": D("1.00")}
    assert fleetlog.worst(values, 2) == [("b", D("9.00")), ("c", D("9.00"))]
    assert fleetlog.worst(values, 10) == [("b", D("9.00")), ("c", D("9.00")), ("a", D("5.00")), ("d", D("1.00"))]
    for n in (0, -1):
        with pytest.raises(ValueError, match="n must be at least 1"):
            fleetlog.worst(values, n)


def test_render(fleetlog):
    assert fleetlog.render({}) == "no trips"
    assert fleetlog.render({"van-1": D("8.4"), "truck-9": D("22")}).splitlines() == ["van-1: 8.40 L/100km", "truck-9: 22.00 L/100km"]


def test_command_line(fleetlog, capsys, tmp_path):
    from fleetlog.cli import main

    assert main([str(DATA), "2"]) == 0
    assert capsys.readouterr().out.splitlines() == ["truck-9: 22.00 L/100km", "van-2: 9.00 L/100km"]
    assert main([str(DATA)]) == 0 and len(capsys.readouterr().out.splitlines()) == 3
    assert main([]) == 2 and "usage:" in capsys.readouterr().err
    assert main([str(tmp_path / "missing.csv")]) == 2
    bad = tmp_path / "bad.csv"
    bad.write_text("a,x,1\n", encoding="utf-8")
    assert main([str(bad)]) == 2 and "invalid trip" in capsys.readouterr().err
    assert main([str(DATA), "0"]) == 2
    assert main([str(DATA), "abc"]) == 2
