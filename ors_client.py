"""
ors_client.py

Thin wrapper around the OpenRouteService (ORS) Python client
to fetch shortest driving routes between coordinates.
"""

from typing import List, Tuple, Dict, Any

import openrouteservice
from openrouteservice import convert

from config import get_ors_api_key


def create_ors_client() -> openrouteservice.Client:
    """
    Create and return an OpenRouteService client using API key from config.
    """
    api_key = get_ors_api_key()
    return openrouteservice.Client(key=api_key)


def fetch_route_geojson(
    client: openrouteservice.Client,
    start: Tuple[float, float],
    end: Tuple[float, float],
    profile: str = "driving-car"
) -> Dict[str, Any]:
    """
    Fetch a route from ORS between start and end coordinates.

    Args:
        client: ORS client.
        start: (lon, lat) for the starting point.
        end: (lon, lat) for the target point.
        profile: ORS profile, e.g. 'driving-car', 'driving-hgv', etc.

    Returns:
        GeoJSON-like dictionary of the route response.
    """
    # ORS expects list of [lon, lat] pairs
    coords = [start, end]
    # format='geojson' simplifies parsing of coordinates
    route = client.directions(
        coordinates=coords,
        profile=profile,
        format="geojson",
        optimize_waypoints=False
    )
    return route


def extract_polyline_and_summary(route_geojson: Dict[str, Any]):
    """
    Extracts:
      - a list of (lat, lon) points along the route
      - total distance (meters)
      - total duration (seconds)

    from an ORS GeoJSON 'directions' response.
    """
    features = route_geojson.get("features", [])
    if not features:
        raise ValueError("No features in ORS route response.")

    first_feature = features[0]
    props = first_feature.get("properties", {})
    summary = props.get("summary", {})

    total_distance_m = float(summary.get("distance", 0.0))
    total_duration_s = float(summary.get("duration", 0.0))

    geometry = first_feature.get("geometry", {})
    # Coordinates are [lon, lat]; convert to (lat, lon)
    coords = geometry.get("coordinates", [])
    latlon_points = [(float(lat), float(lon)) for lon, lat in coords]

    # If we ever use the encoded field instead:
    # geom_encoded = first_feature["geometry"]
    # decoded = convert.decode_polyline(geom_encoded)
    # latlon_points = [(p[1], p[0]) for p in decoded["coordinates"]]

    return latlon_points, total_distance_m, total_duration_s
