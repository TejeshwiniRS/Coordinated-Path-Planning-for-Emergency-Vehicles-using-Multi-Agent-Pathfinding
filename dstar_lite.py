# dstar_lite.py

import heapq
import math
from typing import List, Dict, Tuple, Optional
import networkx as nx


class DStarLite:
    """
    Real implementation of D* Lite (Koenig & Likhachev).
    Performs incremental replanning by searching backwards from Goal to Start.
    """

    def __init__(self, G: nx.DiGraph, start: int, goal: int):
        self.G = G
        self.start = start
        self.goal = goal
        
        # D* Lite specific attributes
        self.km = 0.0  # Key modifier for heuristic updates
        self.g: Dict[int, float] = {}
        self.rhs: Dict[int, float] = {}
        self.queue: List[Tuple[Tuple[float, float], int]] = []  # Priority Queue
        
        # Initialize g and rhs to infinity
        for node in G.nodes:
            self.g[node] = float("inf")
            self.rhs[node] = float("inf")

        self.rhs[self.goal] = 0.0
        heapq.heappush(self.queue, (self._calculate_key(self.goal), self.goal))

        # Initial Plan
        self.path_nodes: List[int] = []
        self._compute_shortest_path()
        self._extract_path()

    def _heuristic(self, u: int, v: int) -> float:
        """
        Estimates travel time between u and v based on haversine distance 
        and an average speed (e.g., 40 km/h = ~11.11 m/s).
        """
        if u not in self.G.nodes or v not in self.G.nodes:
            return float("inf")
            
        n1 = self.G.nodes[u]
        n2 = self.G.nodes[v]
        
        # Simple Haversine calculation inline to avoid circular imports
        R = 6371000.0
        lat1, lon1 = math.radians(n1['lat']), math.radians(n1['lon'])
        lat2, lon2 = math.radians(n2['lat']), math.radians(n2['lon'])
        dphi = lat2 - lat1
        dlambda = lon2 - lon1
        a = math.sin(dphi/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlambda/2)**2
        dist = 2 * R * math.asin(math.sqrt(a))
        
        avg_speed_mps = 40000 / 3600.0  # 40 km/h
        return dist / avg_speed_mps

    def _calculate_key(self, u: int) -> Tuple[float, float]:
        """Returns the priority key (k1, k2) for node u."""
        # k1 = min(g, rhs) + h + km
        # k2 = min(g, rhs)
        min_val = min(self.g.get(u, float('inf')), self.rhs.get(u, float('inf')))
        return (min_val + self._heuristic(self.start, u) + self.km, min_val)

    def _update_vertex(self, u: int):
        """Updates the consistency of a node and its position in the priority queue."""
        if u != self.goal:
            # rhs(u) = min over successors (c(u,s') + g(s'))
            # Since we look at u->v edges, we check neighbors
            min_rhs = float("inf")
            for nbr in self.G.successors(u):
                cost = self.G[u][nbr].get("travel_time", float("inf"))
                min_rhs = min(min_rhs, cost + self.g.get(nbr, float("inf")))
            self.rhs[u] = min_rhs

        # Remove u from heap if it exists (rebuilding heap is expensive, 
        # so we just push and ignore lazy deletions in production, 
        # but for this scale, list reconstruction is acceptable or just duplicates).
        # We will use lazy deletion logic: just push new key. 
        # But to be precise for this assignment, we filter.
        self.queue = [item for item in self.queue if item[1] != u]
        heapq.heapify(self.queue)

        if self.g.get(u, float('inf')) != self.rhs.get(u, float('inf')):
            heapq.heappush(self.queue, (self._calculate_key(u), u))

    def _compute_shortest_path(self):
        """Main D* Lite loop to process inconsistent nodes."""
        while self.queue:
            k_old, u = self.queue[0]
            k_new = self._calculate_key(u)
            
            # Key of start node
            k_start = self._calculate_key(self.start)

            if k_old < k_start or self.rhs[self.start] != self.g[self.start]:
                heapq.heappop(self.queue)
                if k_old < k_new:
                    heapq.heappush(self.queue, (k_new, u))
                elif self.g[u] > self.rhs[u]:
                    self.g[u] = self.rhs[u]
                    # Since we search Goal->Start, we check predecessors of u
                    # (nodes that have an edge TO u)
                    for pred in self.G.predecessors(u):
                        self._update_vertex(pred)
                else:
                    self.g[u] = float("inf")
                    for pred in self.G.predecessors(u):
                        self._update_vertex(pred)
                    self._update_vertex(u)
            else:
                break

    def _extract_path(self):
        """Reconstructs the path from current start to goal by following gradients."""
        path = []
        curr = self.start
        path.append(curr)
        
        # Safety limit to prevent infinite loops if disconnected
        max_steps = len(self.G.nodes) * 2 
        
        while curr != self.goal and len(path) < max_steps:
            min_cost = float("inf")
            best_next = None
            
            for nbr in self.G.successors(curr):
                edge_cost = self.G[curr][nbr].get("travel_time", float("inf"))
                g_val = self.g.get(nbr, float("inf"))
                if edge_cost + g_val < min_cost:
                    min_cost = edge_cost + g_val
                    best_next = nbr
            
            if best_next is None or min_cost == float("inf"):
                break
            
            curr = best_next
            path.append(curr)
            
        self.path_nodes = path

    def step(self) -> int:
        """
        Moves the agent one step along the computed path.
        Updates km (key modifier) to account for robot movement.
        """
        if self.start == self.goal:
            return self.start

        # Simple gradient descent step
        min_cost = float("inf")
        best_next = None
        for nbr in self.G.successors(self.start):
            cost = self.G[self.start][nbr].get("travel_time", float("inf"))
            g_val = self.g.get(nbr, float("inf"))
            if cost + g_val < min_cost:
                min_cost = cost + g_val
                best_next = nbr

        if best_next is not None:
            # Update km before moving start
            self.km += self._heuristic(self.start, best_next)
            self.start = best_next
            # Re-extract path for visualization
            self._extract_path()
        
        return self.start

    def block_edge_and_replan(self, u: int, v: int):
        """
        Simulates an edge blockage (u -> v).
        Updates the graph, then incrementally repairs the path using D* Lite.
        """
        if self.G.has_edge(u, v):
            old_cost = self.G[u][v]["travel_time"]
            new_cost = old_cost * 1e6  # Make it effectively infinite
            
            print(f"[D* Lite] Detected change: Edge ({u}->{v}) cost {old_cost:.2f} -> {new_cost:.2f}")
            self.G[u][v]["travel_time"] = new_cost
            
            # The cost of u->v changed. 
            # In Goal->Start search, u connects to v, so v is a successor of u.
            # u's rhs value depends on v's g value.
            # So we must update u.
            self._update_vertex(u)
            
            # Re-run the D* Lite main loop to propagate changes
            self._compute_shortest_path()
            self._extract_path()
        else:
            print(f"[D* Lite] Edge ({u}->{v}) not found.")