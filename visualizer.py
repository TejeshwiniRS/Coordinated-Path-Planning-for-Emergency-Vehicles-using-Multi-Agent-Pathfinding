"""
visualizer.py

Visualizes emergency vehicle routes on an interactive map using Folium.

- Shows:
  - Accident location as a red marker
  - Each vehicle's route as a colored polyline
  - Start and end markers for each vehicle
- Saves output to an HTML file (routes_map.html by default).

Note: This is a *spatial* visualization. The routes are time-parameterized
by your Route objects, but here we display the geometry. You can open the
HTML file in any browser.
"""

from typing import List, Tuple
import folium
from folium import Map, Marker, PolyLine
from folium.plugins import TimestampedGeoJson
from datetime import datetime, timedelta

from models import Route, AccidentSite


# Simple color palette to differentiate vehicles
ROUTE_COLORS = [
    "#e41a1c",  # red
    "#377eb8",  # blue
    "#4daf4a",  # green
    "#984ea3",  # purple
    "#ff7f00",  # orange
    "#ffff33",  # yellow
]


def _route_to_latlon_list(route: Route) -> List[Tuple[float, float]]:
    """
    Convert a Route (which stores segments) into a list of (lat, lon) points
    suitable for plotting. We use segment starts + final segment end.
    """
    coords: List[Tuple[float, float]] = []
    if not route.segments:
        return [(route.vehicle.lat, route.vehicle.lon)]

    for seg in route.segments:
        coords.append((seg.start_lat, seg.start_lon))
    # Ensure final endpoint is included
    last = route.segments[-1]
    coords.append((last.end_lat, last.end_lon))
    return coords


def _add_static_routes(
    m: Map,
    routes: List[Route],
) -> None:
    """
    Add colored polylines and start/end markers for each route.
    """
    for idx, route in enumerate(routes):
        coords = _route_to_latlon_list(route)
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]

        # Polyline for the route
        PolyLine(
            locations=coords,
            color=color,
            weight=5,
            opacity=0.8,
            tooltip=f"{route.vehicle.name} route"
        ).add_to(m)

        # Start marker
        start_lat, start_lon = coords[0]
        Marker(
            location=(start_lat, start_lon),
            popup=f"{route.vehicle.name} START",
            icon=folium.Icon(color="green", icon="play")
        ).add_to(m)

        # End marker (accident is same for all, but we still mark end)
        end_lat, end_lon = coords[-1]
        Marker(
            location=(end_lat, end_lon),
            popup=f"{route.vehicle.name} END",
            icon=folium.Icon(color="blue", icon="flag")
        ).add_to(m)


def _add_accident_marker(m: Map, accident: AccidentSite) -> None:
    """
    Add a prominent marker for the accident site.
    """
    Marker(
        location=(accident.lat, accident.lon),
        popup="Accident Site",
        icon=folium.Icon(color="red", icon="warning")
    ).add_to(m)


def _add_time_accelerated_markers(
    m: Map,
    routes: List[Route],
    accident: AccidentSite,
    time_accel_factor: float = 10.0,
) -> None:
    """
    OPTIONAL: Add a time-accelerated animation of vehicle positions
    using TimestampedGeoJson.

    time_accel_factor:
        e.g., 10.0 means "simulate at 10x speed" (600s real => 60s animation).

    Note: This uses a simple synthetic timeline starting at "now".
    """
    # Choose a base time (just for visualization)
    base_time = datetime.utcnow()

    features = []

    for idx, route in enumerate(routes):
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]

        # We sample a subset of segments to avoid too many points
        for seg in route.segments:
            # Use the segment start time; compress by factor
            t_real = seg.t_start  # in seconds
            t_visual = t_real / time_accel_factor
            timestamp = base_time + timedelta(seconds=t_visual)

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [seg.start_lon, seg.start_lat],
                },
                "properties": {
                    "time": timestamp.isoformat() + "Z",
                    "popup": route.vehicle.name,
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": color,
                        "fillOpacity": 0.9,
                        "stroke": "true",
                        "radius": 5,
                    },
                },
            }
            features.append(feature)

        # Add a final position at the accident site
        last_time = route.total_duration_s
        t_visual = last_time / time_accel_factor
        timestamp = base_time + timedelta(seconds=t_visual)
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [accident.lon, accident.lat],
            },
            "properties": {
                "time": timestamp.isoformat() + "Z",
                "popup": f"{route.vehicle.name} at Accident",
                "icon": "circle",
                "iconstyle": {
                    "fillColor": color,
                    "fillOpacity": 1.0,
                    "stroke": "true",
                    "radius": 7,
                },
            },
        }
        features.append(feature)

    collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    TimestampedGeoJson(
        data=collection,
        period="PT1S",          # one-second steps in visual time
        add_last_point=True,
        auto_play=True,
        loop=False,
        max_speed=1,
        loop_button=True,
        date_options="YYYY-MM-DD HH:mm:ss",
        time_slider_drag_update=True,
    ).add_to(m)


def render_map(
    routes: List[Route],
    accident: AccidentSite,
    output_html: str = "routes_map.html",
    time_accel_factor: float = 10.0,
) -> str:
    """
    Create an interactive Folium map with:
      - Accident marker
      - Per-vehicle colored routes
      - Time-accelerated animated markers (optional)

    Returns:
        Path to the generated HTML file.
    """
    if not routes:
        raise ValueError("No routes provided to visualize.")

    # Center the map on the accident site
    m = folium.Map(location=(accident.lat, accident.lon), zoom_start=13)

    # Base layers
    folium.TileLayer("OpenStreetMap").add_to(m)

    # Add objects
    _add_accident_marker(m, accident)
    _add_static_routes(m, routes)
    _add_time_accelerated_markers(m, routes, accident, time_accel_factor=time_accel_factor)

    # Save to file
    m.save(output_html)
    return output_html
