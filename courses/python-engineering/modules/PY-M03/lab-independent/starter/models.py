"""Trip record (flat layout, no annotations)."""
from dataclasses import dataclass

import util


@dataclass
class Trip:
    vehicle: object
    distance_km: object
    fuel_l: object

    def per_100km(self):
        return util.to_number(self.fuel_l) / util.to_number(self.distance_km) * 100
