# astar_planner.py

from typing import Dict, Tuple, List
import heapq
import math
import networkx as nx


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def time_heuristic(G: nx.DiGraph, u: int, v: int) -> float:
    """Straight-line time estimate, assuming 40 km/h avg speed."""
    avg_speed = 40_000 / 3600  # m/s
    nu, nv = G.nodes[u], G.nodes[v]
    d = haversine_m(nu["lat"], nu["lon"], nv["lat"], nv["lon"])
    return d / avg_speed


def astar_shortest_path(
    G: nx.DiGraph, start: int, goal: int
) -> Tuple[List[int], float]:
    """
    A* on abstract graph using 'travel_time' as cost.
    Returns (node_path, total_time_s).
    """
    open_heap: List[Tuple[float, int]] = []
    heapq.heappush(open_heap, (0.0, start))
    came_from: Dict[int, int] = {}
    g: Dict[int, float] = {start: 0.0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path, g[goal]

        for nbr in G.successors(current):
            cost = G[current][nbr]["travel_time"]
            tentative = g[current] + cost
            if tentative < g.get(nbr, float("inf")):
                g[nbr] = tentative
                came_from[nbr] = current
                h = time_heuristic(G, nbr, goal)
                f = tentative + h
                heapq.heappush(open_heap, (f, nbr))

    return [], float("inf")
