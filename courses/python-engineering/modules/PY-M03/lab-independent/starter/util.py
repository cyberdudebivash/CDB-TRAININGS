"""Helpers shared by the other modules."""
from typing import Any

from models import Trip


def to_number(value: Any) -> Any:
    return float(value)


def parse_trip(line):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != 3:
        raise ValueError("invalid trip: " + line)
    try:
        trip = Trip(parts[0], to_number(parts[1]), to_number(parts[2]))
    except ValueError:
        raise ValueError("invalid trip: " + line)
    if not parts[0] or trip.distance_km <= 0 or trip.fuel_l < 0:
        raise ValueError("invalid trip: " + line)
    return trip


def parse_lines(lines):
    return [parse_trip(l) for l in lines if l.strip() and not l.lstrip().startswith("#")]
