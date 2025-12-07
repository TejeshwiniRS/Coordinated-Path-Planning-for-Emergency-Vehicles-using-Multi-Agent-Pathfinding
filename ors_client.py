# ors_client.py

from typing import Dict, Any, List, Tuple

import openrouteservice
from config import get_ors_api_key


def create_ors_client() -> openrouteservice.Client:
    """Create an ORS client using API key from environment."""
    return openrouteservice.Client(key=get_ors_api_key())


def fetch_route_geojson(
    client: openrouteservice.Client,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: str = "driving-car",
) -> Dict[str, Any]:
    """
    Fetch a route between (start_lat, start_lon) and (end_lat, end_lon) from ORS.

    Returns the GeoJSON response.
    """
    coords = [[start_lon, start_lat], [end_lon, end_lat]]

    route = client.directions(
        coordinates=coords,
        profile=profile,
        format="geojson",
        optimize_waypoints=False,
    )
    return route


def extract_polyline_and_summary(
    route_geojson: Dict[str, Any],
) -> Tuple[List[Tuple[float, float]], float, float]:
    """
    Extract (lat, lon) polyline and (distance_m, duration_s) from ORS GeoJSON.
    """
    features = route_geojson.get("features", [])
    if not features:
        raise ValueError("No features in ORS route response.")

    feat = features[0]
    props = feat.get("properties", {})
    summary = props.get("summary", {})

    total_distance_m = float(summary.get("distance", 0.0))
    total_duration_s = float(summary.get("duration", 0.0))

    geometry = feat.get("geometry", {})
    coords = geometry.get("coordinates", [])

    # ORS: [lon, lat] → convert to (lat, lon)
    latlon = [(float(lat), float(lon)) for lon, lat in coords]
    return latlon, total_distance_m, total_duration_s
