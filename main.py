"""
main.py

Runs emergency routing dynamically using user input and OpenRouteService.
Automatically opens the visual map in the browser.
"""

import webbrowser
from typing import List

from models import Vehicle, AccidentSite, Route
from route_planner import build_route_for_vehicle
from simulation import simulate_routes
from visualizer import render_map


def read_float(prompt: str) -> float:
    """Safely read a float from user input."""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Invalid input. Please enter a numeric value.")


def read_vehicle_input() -> List[Vehicle]:
    """Ask the user for vehicle count and per-vehicle coordinates."""
    vehicles = []
    count = int(read_float("Enter number of emergency vehicles: "))

    for i in range(count):
        print(f"\n--- Vehicle {i+1} ---")
        name = input("Enter vehicle name (e.g., Ambulance): ").strip()
        lat = read_float("Enter latitude: ")
        lon = read_float("Enter longitude: ")
        vehicles.append(Vehicle(name=name, lat=lat, lon=lon))

    return vehicles


def main():
    print("\n=== Emergency Vehicle Dynamic Routing (OpenRouteService) ===")

    print("\nEnter Accident Location:")
    acc_lat = read_float("Accident latitude: ")
    acc_lon = read_float("Accident longitude: ")
    accident = AccidentSite(lat=acc_lat, lon=acc_lon)

    print("\nEnter Vehicle Locations:")
    vehicles = read_vehicle_input()

    print("\nRequesting routes from OpenRouteService...")
    routes: List[Route] = []

    for v in vehicles:
        try:
            route = build_route_for_vehicle(v, accident)
            routes.append(route)

            print(f"\nRoute for {v.name}:")
            print(f"  Distance: {route.total_distance_m/1000.0:.2f} km")
            print(f"  Duration: {route.total_duration_s/60.0:.2f} min")
            print(f"  Segments: {len(route.segments)}")

        except Exception as e:
            print(f"Failed to build route for {v.name}: {e}")

    if not routes:
        print("No valid routes could be built. Exiting.")
        return

    # Console simulation
    simulate_routes(routes, time_step_s=1.0, conflict_distance_m=10.0)

    # Visual map output
    print("\nGenerating interactive map with routes...")
    html_path = "routes_map.html"
    render_map(routes, accident, output_html=html_path, time_accel_factor=10.0)

    print(f"Map saved to: {html_path}")
    print("Opening in your browser...")

    webbrowser.open(html_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
