"""
simulation.py

Time-stepped simulation and conflict detection for multiple routes.

- Uses a simple haversine-based distance model.
- At each time step, computes each vehicle's position.
- Flags a conflict when two vehicles come within a given distance threshold.
"""

from typing import List, Tuple
import math

from models import Route


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance between two points on Earth
    (specified in decimal degrees) using the Haversine formula.

    Returns:
        distance in meters.
    """
    # Earth radius in meters
    R = 6371000.0

    # Convert decimal degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def simulate_routes(
    routes: List[Route],
    time_step_s: float = 1.0,
    conflict_distance_m: float = 10.0
) -> None:
    """
    Simulate all routes in parallel and print simple conflict statistics.

    Args:
        routes: list of Route objects, one per vehicle.
        time_step_s: simulation time step in seconds.
        conflict_distance_m: threshold under which two vehicles are considered
                             to be in a conflict (too close).
    """
    if not routes:
        print("No routes to simulate.")
        return

    max_duration = max(r.total_duration_s for r in routes)
    total_steps = int(max_duration // time_step_s) + 1

    print("\n=== Dynamic Multi-Vehicle Simulation ===")
    print(f"Simulating up to {max_duration:.1f} seconds "
          f"with time step {time_step_s:.1f}s...")
    print(f"Conflict distance threshold: {conflict_distance_m} meters")

    first_conflict = None
    conflict_count = 0

    for step in range(total_steps):
        t = step * time_step_s
        positions = []

        # Compute each vehicle's position at time t
        for route in routes:
            lat, lon = route.positions_at(t)
            positions.append((route.vehicle.name, lat, lon))

        # Compare all pairs for potential conflicts
        for i in range(len(positions)):
            name_i, lat_i, lon_i = positions[i]
            for j in range(i + 1, len(positions)):
                name_j, lat_j, lon_j = positions[j]
                d = haversine_distance_m(lat_i, lon_i, lat_j, lon_j)
                if d <= conflict_distance_m:
                    conflict_count += 1
                    if first_conflict is None:
                        first_conflict = (t, name_i, name_j, d)

    if first_conflict:
        t_conflict, v1, v2, dist = first_conflict
        print(f"First conflict at t = {t_conflict:.1f}s "
              f"between {v1} and {v2}, distance ~ {dist:.2f} m")
    else:
        print("No conflicts detected within the threshold.")

    print(f"Total conflict events (within threshold over all time steps): {conflict_count}")
