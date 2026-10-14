"""Calculations and formatting."""
import util
from models import Trip


def consumption(trips):
    totals = {}
    for t in trips:
        d, f = totals.get(t.vehicle, (0, 0))
        totals[t.vehicle] = (d + t.distance_km, f + t.fuel_l)
    return {v: round(f / d * 100, 2) for v, (d, f) in sorted(totals.items())}


def worst(values, n):
    return sorted(values.items(), key=lambda kv: -kv[1])[:n]


def render(values):
    if not values:
        return "no trips"
    return "\n".join("%s: %.2f L/100km" % (v, x) for v, x in values.items())


def load(path):
    with open(path, encoding="utf-8") as handle:
        return util.parse_lines(handle.read().splitlines())
