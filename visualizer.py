# visualizer.py

from typing import List, Tuple
from datetime import datetime, timedelta
import folium
from folium import Map, Marker, PolyLine
from folium.plugins import TimestampedGeoJson

from models import Route, AccidentSite


ROUTE_COLORS = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33"]


def _route_to_latlon_list(route: Route) -> List[Tuple[float, float]]:
    coords: List[Tuple[float, float]] = []
    if not route.segments:
        return [(route.vehicle.lat, route.vehicle.lon)]
    for seg in route.segments:
        coords.append((seg.start_lat, seg.start_lon))
    last = route.segments[-1]
    coords.append((last.end_lat, last.end_lon))
    return coords


def _add_static_routes(m: Map, routes: List[Route]) -> None:
    for idx, route in enumerate(routes):
        coords = _route_to_latlon_list(route)
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]

        PolyLine(
            locations=coords,
            color=color,
            weight=5,
            opacity=0.8,
            tooltip=f"{route.vehicle.name} route",
        ).add_to(m)

        start_lat, start_lon = coords[0]
        Marker(
            location=(start_lat, start_lon),
            popup=f"{route.vehicle.name} START",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(m)

        end_lat, end_lon = coords[-1]
        Marker(
            location=(end_lat, end_lon),
            popup=f"{route.vehicle.name} END",
            icon=folium.Icon(color="blue", icon="flag"),
        ).add_to(m)


def _add_accident_marker(m: Map, accident: AccidentSite):
    Marker(
        location=(accident.lat, accident.lon),
        popup="Accident Site",
        icon=folium.Icon(color="red", icon="warning"),
    ).add_to(m)


def _add_time_animation(m: Map, routes: List[Route], accel: float = 10.0):
    base_time = datetime.utcnow()
    features = []

    for idx, route in enumerate(routes):
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
        for seg in route.segments:
            t_visual = seg.t_start / accel
            ts = base_time + timedelta(seconds=t_visual)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [seg.start_lon, seg.start_lat],
                    },
                    "properties": {
                        "time": ts.isoformat() + "Z",
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
            )

    collection = {"type": "FeatureCollection", "features": features}

    TimestampedGeoJson(
        data=collection,
        period="PT1S",
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
    accel: float = 10.0,
) -> str:
    if not routes:
        raise ValueError("No routes to render.")

    m = folium.Map(location=(accident.lat, accident.lon), zoom_start=13)
    folium.TileLayer("OpenStreetMap").add_to(m)

    _add_accident_marker(m, accident)
    _add_static_routes(m, routes)
    _add_time_animation(m, routes, accel)

    m.save(output_html)
    return output_html
