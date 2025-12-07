"""
route_planner.py

Builds Route objects for vehicles using the ORS client.
"""

from typing import List, Tuple

from models import Vehicle, AccidentSite, Route, RouteSegment
from ors_client import create_ors_client, fetch_route_geojson, extract_polyline_and_summary


def build_route_for_vehicle(
    vehicle: Vehicle,
    accident: AccidentSite,
    profile: str = "driving-car"
) -> Route:
    """
    Uses ORS to build a Route object for the given vehicle and accident site.

    Steps:
      1. Query ORS directions for [vehicle -> accident].
      2. Extract polyline coordinates, total distance, and duration.
      3. Split route into small segments between successive polyline points.
      4. Distribute distance and duration proportionally across segments.
    """
    client = create_ors_client()

    # ORS expects coordinates as (lon, lat)
    start = (vehicle.lon, vehicle.lat)
    end = (accident.lon, accident.lat)

    route_geojson = fetch_route_geojson(client, start, end, profile=profile)
    latlon_points, total_distance_m, total_duration_s = extract_polyline_and_summary(route_geojson)

    if len(latlon_points) < 2:
        raise RuntimeError(f"Received too few points for vehicle {vehicle.name}'s route.")

    # Compute naive distances between consecutive points using haversine
    distances_between_points: List[float] = []
    from simulation import haversine_distance_m  # local import to avoid circular ref

    for i in range(len(latlon_points) - 1):
        (lat1, lon1) = latlon_points[i]
        (lat2, lon2) = latlon_points[i + 1]
        d = haversine_distance_m(lat1, lon1, lat2, lon2)
        distances_between_points.append(d)

    sum_distances = sum(distances_between_points) or 1.0  # avoid div by zero

    segments: List[RouteSegment] = []
    t_cumulative = 0.0

    for i in range(len(latlon_points) - 1):
        (lat1, lon1) = latlon_points[i]
        (lat2, lon2) = latlon_points[i + 1]
        local_distance = distances_between_points[i]

        # proportion of total distance
        frac = local_distance / sum_distances
        seg_distance = frac * total_distance_m
        seg_duration = frac * total_duration_s

        t_start = t_cumulative
        t_end = t_cumulative + seg_duration
        t_cumulative = t_end

        seg = RouteSegment(
            start_lat=lat1,
            start_lon=lon1,
            end_lat=lat2,
            end_lon=lon2,
            distance_m=seg_distance,
            duration_s=seg_duration,
            t_start=t_start,
            t_end=t_end,
        )
        segments.append(seg)

    # Ensure total duration matches (minor rounding errors are acceptable)
    route = Route(
        vehicle=vehicle,
        segments=segments,
        total_distance_m=total_distance_m,
        total_duration_s=total_duration_s,
    )

    return route
