# simulation.py

from typing import List
import math
from models import Route


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def simulate_routes(
    routes: List[Route], time_step_s: float = 1.0, conflict_distance_m: float = 10.0
):
    if not routes:
        print("No routes to simulate.")
        return

    max_duration = max(r.total_duration_s for r in routes)
    total_steps = int(max_duration // time_step_s) + 1

    print("\n=== Dynamic Multi-Vehicle Simulation (CBS paths) ===")
    print(
        f"Simulating up to {max_duration:.1f}s, dt={time_step_s:.1f}s, "
        f"conflict <= {conflict_distance_m} m"
    )

    first_conflict = None
    conflict_events = 0

    for step in range(total_steps):
        t = step * time_step_s
        positions = []
        for r in routes:
            lat, lon = r.positions_at(t)
            positions.append((r.vehicle.name, lat, lon))

        for i in range(len(positions)):
            n1, lat1, lon1 = positions[i]
            for j in range(i + 1, len(positions)):
                n2, lat2, lon2 = positions[j]
                d = haversine_distance_m(lat1, lon1, lat2, lon2)
                if d <= conflict_distance_m:
                    conflict_events += 1
                    if first_conflict is None:
                        first_conflict = (t, n1, n2, d)

    if first_conflict:
        t, a, b, d = first_conflict
        print(f"First conflict at t={t:.1f}s between {a} and {b} (d≈{d:.2f} m)")
    else:
        print("No conflicts detected.")

    print(f"Total conflict events: {conflict_events}")
