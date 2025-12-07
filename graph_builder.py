# graph_builder.py

from typing import Dict, List, Tuple
import math
import networkx as nx


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def downsample_polyline(
    polyline: List[Tuple[float, float]], target_waypoints: int = 8
) -> List[Tuple[float, float]]:
    """
    Reduce polyline to about target_waypoints points (including start & end).
    """
    n = len(polyline)
    if n <= target_waypoints:
        return polyline
    step = max(1, n // (target_waypoints - 1))
    pts = [polyline[0]]
    i = step
    while i < n - 1:
        pts.append(polyline[i])
        i += step
    pts.append(polyline[-1])
    return pts


def build_abstract_graph_from_routes(
    polylines: Dict[str, List[Tuple[float, float]]],
    target_waypoints: int = 8,
):
    """
    Build a small abstract directed graph from downsampled ORS polylines.

    Returns:
        G: nx.DiGraph with nodes: id -> {lat, lon}
        vehicle_way_nodes: dict[name] -> list[node_ids in route order]
    """
    G = nx.DiGraph()
    node_coords: List[Tuple[float, float]] = []
    vehicle_way_nodes: Dict[str, List[int]] = {}

    MERGE_EPS_M = 10.0  # merge nodes closer than 10m

    def find_or_create_node(lat: float, lon: float) -> int:
        for idx, (nlat, nlon) in enumerate(node_coords):
            if haversine_m(lat, lon, nlat, nlon) <= MERGE_EPS_M:
                return idx
        new_id = len(node_coords)
        node_coords.append((lat, lon))
        G.add_node(new_id, lat=lat, lon=lon)
        return new_id

    for veh_name, poly in polylines.items():
        # downsample for CBS (abstract waypoints)
        pts = downsample_polyline(poly, target_waypoints=target_waypoints)
        if len(pts) < 2:
            continue

        way_nodes: List[int] = []
        for (lat, lon) in pts:
            nid = find_or_create_node(lat, lon)
            way_nodes.append(nid)

        vehicle_way_nodes[veh_name] = way_nodes

        # connect waypoints in order (abstract edges)
        for i in range(len(way_nodes) - 1):
            u = way_nodes[i]
            v = way_nodes[i + 1]
            if not G.has_edge(u, v):
                # abstract graph: unit time per move, store geometry length
                d = haversine_m(
                    G.nodes[u]["lat"],
                    G.nodes[u]["lon"],
                    G.nodes[v]["lat"],
                    G.nodes[v]["lon"],
                )
                G.add_edge(u, v, travel_time=1.0, length=d)

    return G, vehicle_way_nodes
