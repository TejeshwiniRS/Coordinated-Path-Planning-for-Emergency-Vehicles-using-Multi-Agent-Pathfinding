# models.py

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Vehicle:
    name: str
    lat: float
    lon: float


@dataclass
class AccidentSite:
    lat: float
    lon: float


@dataclass
class RouteSegment:
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    distance_m: float
    duration_s: float
    t_start: float
    t_end: float


@dataclass
class Route:
    vehicle: Vehicle
    segments: List[RouteSegment]
    total_distance_m: float
    total_duration_s: float

    def positions_at(self, t: float) -> Tuple[float, float]:
        """Interpolate vehicle position at time t (seconds) along its route."""
        if not self.segments:
            return self.vehicle.lat, self.vehicle.lon

        if t <= self.segments[0].t_start:
            s = self.segments[0]
            return s.start_lat, s.start_lon

        if t >= self.segments[-1].t_end:
            s = self.segments[-1]
            return s.end_lat, s.end_lon

        for seg in self.segments:
            if seg.t_start <= t <= seg.t_end:
                if seg.duration_s == 0:
                    return seg.end_lat, seg.end_lon
                r = (t - seg.t_start) / seg.duration_s
                lat = seg.start_lat + r * (seg.end_lat - seg.start_lat)
                lon = seg.start_lon + r * (seg.end_lon - seg.start_lon)
                return lat, lon

        s = self.segments[-1]
        return s.end_lat, s.end_lon
