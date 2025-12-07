# dstar_lite.py

from typing import List
import networkx as nx
from astar_planner import astar_shortest_path


class SimpleDStarLite:
    """
    Simplified D*-Lite-style replanner on abstract graph:
      - Maintains current node and goal.
      - Re-runs A* whenever we "block" an edge.
    """

    def __init__(self, G: nx.DiGraph, start: int, goal: int):
        self.G = G
        self.current = start
        self.goal = goal
        self.path_nodes: List[int] = []
        self.total_time_s: float = 0.0
        self._replan()

    def _replan(self):
        self.path_nodes, self.total_time_s = astar_shortest_path(
            self.G, self.current, self.goal
        )
        if not self.path_nodes:
            print(f"[D*] No path from {self.current} to {self.goal} after replanning.")

    def step(self) -> int:
        """Advance one node along the current path."""
        if len(self.path_nodes) <= 1:
            return self.current
        self.path_nodes.pop(0)
        self.current = self.path_nodes[0]
        return self.current

    def block_edge_and_replan(self, u: int, v: int):
        """Simulate road closure: make edge (u,v) unusable and replan."""
        if self.G.has_edge(u, v):
            self.G[u][v]["travel_time"] *= 1e6
            print(f"[D*] Blocking edge ({u}->{v}) and replanning...")
        else:
            print(f"[D*] Edge ({u}->{v}) not found, nothing to block.")
        self._replan()
