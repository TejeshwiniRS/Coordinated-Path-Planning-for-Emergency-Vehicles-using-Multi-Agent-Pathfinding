# cbs.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import heapq
import networkx as nx
from collections import deque, defaultdict

# -------------------------
# Data structures
# -------------------------


@dataclass
class Agent:
    name: str
    start: int
    goal: int


@dataclass
class Constraint:
    agent: str
    node: int
    time: int


@dataclass
class Conflict:
    time: int
    a1: str
    a2: str
    node: int


class CBSTreeNode:
    def __init__(self, constraints: List[Constraint], paths: Dict[str, List[int]]):
        self.constraints = constraints
        self.paths = paths
        # Sum of path lengths as cost (same as your original)
        self.cost = sum(len(p) for p in paths.values())

    def __lt__(self, other: "CBSTreeNode"):
        return self.cost < other.cost


# -------------------------
# Low-level search cache
# -------------------------

# Cache: (agent_name, start, goal, max_t, frozenset((node, time), ...)) -> path
_LL_CACHE: Dict[Tuple[str, int, int, int, frozenset], List[int]] = {}


def _constraints_key_for_agent(
    agent: Agent, constraints: List[Constraint]
) -> frozenset:
    """
    Build a canonical, hashable representation of constraints relevant to this agent.
    Only (node, time) pairs for this agent are included.
    """
    return frozenset((c.node, c.time) for c in constraints if c.agent == agent.name)


# -------------------------
# Low-level search (optimized)
# -------------------------


def low_level_search(
    G: nx.DiGraph, agent: Agent, constraints: List[Constraint], max_t: int = 100
) -> List[int]:
    """
    Time-expanded BFS for one agent under constraints.
    State = (node, time), cost = 1 per step, can move to neighbors or stay.

    OPTIMIZATIONS:
    - Use deque instead of list+pop(0) for O(1) queue ops.
    - Pre-index constraints by time for this agent for O(1) violation checks.
    - Cache results per (agent, start, goal, max_t, constraints_key).
    """
    # ---------- cache lookup ----------
    ckey = _constraints_key_for_agent(agent, constraints)
    cache_key = (agent.name, agent.start, agent.goal, max_t, ckey)
    if cache_key in _LL_CACHE:
        return _LL_CACHE[cache_key]

    # ---------- index constraints for this agent ----------
    # constraints_by_time[t] = {node1, node2, ...} forbidden for this agent at time t
    constraints_by_time: Dict[int, set] = defaultdict(set)
    for node, t in ckey:
        constraints_by_time[t].add(node)

    def blocked(node: int, t: int) -> bool:
        return node in constraints_by_time.get(t, ())

    # ---------- BFS ----------
    start_state = (agent.start, 0)
    frontier = deque([start_state])
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start_state: None}

    while frontier:
        node, t = frontier.popleft()
        if t > max_t:
            continue

        if node == agent.goal:
            # reconstruct path (nodes over time)
            path_states = []
            s = (node, t)
            while s is not None:
                path_states.append(s)
                s = came_from[s]
            path_states.reverse()
            path = [n for (n, _) in path_states]
            _LL_CACHE[cache_key] = path
            return path

        next_t = t + 1
        # wait (stay) or move to any successor
        for next_node in [node] + list(G.successors(node)):
            if blocked(next_node, next_t):
                continue
            state = (next_node, next_t)
            if state not in came_from:
                came_from[state] = (node, t)
                frontier.append(state)

    # no path found
    _LL_CACHE[cache_key] = []
    return []


# -------------------------
# Conflict detection
# -------------------------


def detect_first_conflict(paths: Dict[str, List[int]]) -> Optional[Conflict]:
    """
    Return the earliest vertex conflict between any pair of agents, if any.
    """
    if not paths:
        return None
    T = max(len(p) for p in paths.values())
    names = list(paths.keys())

    for t in range(T):
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a1, a2 = names[i], names[j]
                p1, p2 = paths[a1], paths[a2]
                n1 = p1[t] if t < len(p1) else p1[-1]
                n2 = p2[t] if t < len(p2) else p2[-1]
                if n1 == n2:
                    return Conflict(time=t, a1=a1, a2=a2, node=n1)
    return None


# -------------------------
# Top-level CBS
# -------------------------


def cbs_plan(
    G: nx.DiGraph, agents: List[Agent], max_t: int = 100
) -> Dict[str, List[int]]:
    """
    Top-level CBS. Returns dict agent_name -> path (list of node IDs over time).
    Uses a simple cost = sum of path lengths.
    """
    # Clear cache per call, in case you call cbs_plan repeatedly on different graphs
    _LL_CACHE.clear()

    # Root node: no constraints, independently planned paths
    root_constraints: List[Constraint] = []
    root_paths: Dict[str, List[int]] = {}

    for a in agents:
        p = low_level_search(G, a, root_constraints, max_t)
        if not p:
            raise RuntimeError(f"No path for agent {a.name}")
        root_paths[a.name] = p

    root = CBSTreeNode(root_constraints, root_paths)
    open_heap: List[CBSTreeNode] = []
    heapq.heappush(open_heap, root)

    while open_heap:
        node = heapq.heappop(open_heap)
        conflict = detect_first_conflict(node.paths)
        if conflict is None:
            # Found conflict-free joint solution
            return node.paths

        # Standard CBS: branch on offender 1 and offender 2
        for offender in [conflict.a1, conflict.a2]:
            new_constraints = list(node.constraints)
            new_constraints.append(
                Constraint(agent=offender, node=conflict.node, time=conflict.time)
            )
            new_paths = dict(node.paths)

            agent_obj = next(a for a in agents if a.name == offender)
            replanned = low_level_search(G, agent_obj, new_constraints, max_t)
            if not replanned:
                # This branch is infeasible for this agent
                continue

            new_paths[offender] = replanned
            child = CBSTreeNode(new_constraints, new_paths)
            heapq.heappush(open_heap, child)

    raise RuntimeError("CBS failed to find a conflict-free solution.")
