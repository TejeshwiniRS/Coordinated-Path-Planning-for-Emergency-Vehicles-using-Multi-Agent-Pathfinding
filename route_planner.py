# route_planner.py

from typing import List, Dict
import networkx as nx

from models import Vehicle, Route, RouteSegment
from simulation import haversine_distance_m


def build_route_from_node_path(
    G: nx.DiGraph,
    vehicle: Vehicle,
    node_path: List[int],
    per_step_time_s: float,
) -> Route:
    """
    Convert CBS node path into a time-parameterized Route.
    Each step moves between abstract waypoints on the road.
    """
    segments: List[RouteSegment] = []
    t = 0.0
    total_distance = 0.0
    total_duration = 0.0

    for i in range(len(node_path) - 1):
        u = node_path[i]
        v = node_path[i + 1]
        nu, nv = G.nodes[u], G.nodes[v]
        lat1, lon1 = nu["lat"], nu["lon"]
        lat2, lon2 = nv["lat"], nv["lon"]
        dist = haversine_distance_m(lat1, lon1, lat2, lon2)
        dur = per_step_time_s

        seg = RouteSegment(
            start_lat=lat1,
            start_lon=lon1,
            end_lat=lat2,
            end_lon=lon2,
            distance_m=dist,
            duration_s=dur,
            t_start=t,
            t_end=t + dur,
        )
        segments.append(seg)
        t += dur
        total_distance += dist
        total_duration += dur

    return Route(
        vehicle=vehicle,
        segments=segments,
        total_distance_m=total_distance,
        total_duration_s=total_duration,
    )


def build_cbs_routes(
    G: nx.DiGraph,
    vehicles: List[Vehicle],
    cbs_paths: Dict[str, List[int]],
    ors_durations_s: Dict[str, float],
) -> List[Route]:
    """
    Build per-vehicle Route objects from CBS node paths.
    Time per step is scaled so that the total duration matches ORS duration.
    """
    routes: List[Route] = []
    for v in vehicles:
        if v.name not in cbs_paths or v.name not in ors_durations_s:
            continue
        path_nodes = cbs_paths[v.name]
        if len(path_nodes) < 2:
            continue
        total_dur = ors_durations_s[v.name]
        per_step = total_dur / max(1, len(path_nodes) - 1)
        r = build_route_from_node_path(G, v, path_nodes, per_step)
        routes.append(r)
    return routes
