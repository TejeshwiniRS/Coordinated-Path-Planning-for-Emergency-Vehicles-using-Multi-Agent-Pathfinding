# prioritized_planner.py

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import heapq
import networkx as nx


# -----------------------------
# Agent definition (required)
# -----------------------------
@dataclass
class Agent:
    name: str
    start: int
    goal: int


# -----------------------------
# Time-expanded A*
# -----------------------------
def time_expanded_astar(
    G: nx.DiGraph,
    agent: Agent,
    occupied_nodes: Dict[int, set],
    occupied_edges: Dict[Tuple[int, int], set],
    max_t: int = 50,
) -> List[int]:
    """
    A* in (node, time) space, avoiding existing reservations.
    """
    start_state = (agent.start, 0)
    goal = agent.goal

    open_heap = []
    heapq.heappush(open_heap, (0, 0, agent.start, 0))

    came_from = {start_state: None}
    g_cost = {start_state: 0}

    def admissible_h(n: int) -> int:
        return 0  # heuristic = 0 for simplicity

    def is_blocked(next_node: int, cur_node: int, next_t: int) -> bool:
        if next_t in occupied_nodes.get(next_node, ()):
            return True
        if (cur_node, next_node) in occupied_edges and next_t in occupied_edges[(cur_node, next_node)]:
            return True
        return False

    while open_heap:
        f, g, node, t = heapq.heappop(open_heap)
        if t > max_t:
            continue

        if node == goal:
            # reconstruct path
            path_states = []
            s = (node, t)
            while s is not None:
                path_states.append(s)
                s = came_from[s]
            path_states.reverse()
            return [n for (n, _) in path_states]

        next_t = t + 1

        # wait + move
        for next_node in [node] + list(G.successors(node)):
            if is_blocked(next_node, node, next_t):
                continue

            state = (next_node, next_t)
            new_g = g + 1
            if new_g < g_cost.get(state, float("inf")):
                g_cost[state] = new_g
                came_from[state] = (node, t)
                heapq.heappush(open_heap, (new_g + admissible_h(next_node), new_g, next_node, next_t))

    return []


# -----------------------------
# Prioritized planning
# -----------------------------
def prioritized_plan(
    G: nx.DiGraph,
    agents: List[Agent],
    priority_order: Optional[List[str]] = None,
    max_t: int = 50,
) -> Dict[str, List[int]]:
    if priority_order is None:
        priority_order = [a.name for a in agents]

    agents_by_name = {a.name: a for a in agents}

    occupied_nodes = {}
    occupied_edges = {}
    paths = {}

    for name in priority_order:
        agent = agents_by_name[name]

        path = time_expanded_astar(
            G, agent, occupied_nodes, occupied_edges, max_t
        )
        if not path:
            raise RuntimeError(f"No path for agent {agent.name}")

        paths[name] = path

        # reserve path
        for t in range(len(path)):
            node = path[t]
            occupied_nodes.setdefault(node, set()).add(t)
            if t > 0:
                u = path[t - 1]
                v = path[t]
                occupied_edges.setdefault((u, v), set()).add(t)

    return paths
