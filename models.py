"""
models.py

Dataclasses and utilities for vehicles, accident site, and routes.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Vehicle:
    """Represents an emergency vehicle with a name and a geographic position."""
    name: str
    lat: float
    lon: float


@dataclass
class AccidentSite:
    """Represents the accident location."""
    lat: float
    lon: float


@dataclass
class RouteSegment:
    """
    A single time-parameterized segment of a route.

    Attributes:
        start_lat, start_lon: start coordinate of this segment.
        end_lat, end_lon: end coordinate of this segment.
        distance_m: length of the segment in meters.
        duration_s: travel time for this segment in seconds.
        t_start: cumulative time since start of route when entering this segment.
        t_end: cumulative time since start of route when leaving this segment.
    """
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
    """
    Complete route for a vehicle.

    Attributes:
        vehicle: the vehicle this route belongs to.
        segments: list of ordered RouteSegment objects.
        total_distance_m: total route length in meters.
        total_duration_s: total travel time in seconds.
    """
    vehicle: Vehicle
    segments: List[RouteSegment]
    total_distance_m: float
    total_duration_s: float

    def positions_at(self, t: float) -> Tuple[float, float]:
        """
        Returns the approximate (lat, lon) of the vehicle at time t (in seconds)
        after departure, using linear interpolation on the current segment.

        If t is beyond the end of the route, returns the last coordinate.
        """
        if not self.segments:
            return self.vehicle.lat, self.vehicle.lon

        if t <= self.segments[0].t_start:
            # before route start (not really used, but safe)
            first = self.segments[0]
            return first.start_lat, first.start_lon

        if t >= self.segments[-1].t_end:
            last = self.segments[-1]
            return last.end_lat, last.end_lon

        # Find the segment that contains t
        for seg in self.segments:
            if seg.t_start <= t <= seg.t_end:
                if seg.duration_s == 0:
                    return seg.end_lat, seg.end_lon
                ratio = (t - seg.t_start) / seg.duration_s
                lat = seg.start_lat + ratio * (seg.end_lat - seg.start_lat)
                lon = seg.start_lon + ratio * (seg.end_lon - seg.start_lon)
                return lat, lon

        # Fallback (should not reach here)
        last = self.segments[-1]
        return last.end_lat, last.end_lon
