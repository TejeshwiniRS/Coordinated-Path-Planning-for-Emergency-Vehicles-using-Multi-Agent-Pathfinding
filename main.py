# main.py

import webbrowser
from typing import List, Dict

from models import Vehicle, AccidentSite, Route
from ors_client import (
    create_ors_client,
    fetch_route_geojson,
    extract_polyline_and_summary,
)
from graph_builder import build_abstract_graph_from_routes
from astar_planner import astar_shortest_path
from prioritized_planner import Agent, prioritized_plan
from dstar_lite import SimpleDStarLite
from route_planner import build_cbs_routes
from simulation import simulate_routes
from visualizer import render_map
import webbrowser
# import web_serve
import subprocess
import time



def read_float(prompt: str) -> float:
    while True:
        try:
            return float(prompt and input(prompt))
        except ValueError:
            print("Invalid input. Please enter a numeric value (e.g., 44.9697, -93.2223).")


def read_vehicle_input() -> List[Vehicle]:
    vehicles: List[Vehicle] = []
    count = int(read_float("Enter number of emergency vehicles: "))
    for i in range(count):
        print(f"\n--- Vehicle {i + 1} ---")
        name = input("Enter vehicle name (e.g., Ambulance): ").strip()
        lat = read_float("Enter latitude: ")
        lon = read_float("Enter longitude: ")
        vehicles.append(Vehicle(name=name, lat=lat, lon=lon))
    return vehicles


def main():
    print("\n=== Emergency Vehicle MAPF with A*, Prioritized Planning, D*-Lite "
          "(ORS Geometry + Abstract Graph) ===")

    print("\nEnter Accident Location:")
    acc_lat = read_float("Accident latitude: ")
    acc_lon = read_float("Accident longitude: ")
    accident = AccidentSite(lat=acc_lat, lon=acc_lon)

    print("\nEnter Vehicle Locations:")
    vehicles = read_vehicle_input()

    # 1) Fetch ORS routes (geometry + distance/time) for each vehicle
    client = create_ors_client()
    polylines: Dict[str, List[tuple]] = {}
    summaries: Dict[str, tuple] = {}  # vehicle_name -> (dist_m, dur_s)

    print("\nRequesting ORS routes...")
    for v in vehicles:
        try:
            rjson = fetch_route_geojson(client, v.lat, v.lon, accident.lat, accident.lon)
            poly, dist_m, dur_s = extract_polyline_and_summary(rjson)
            polylines[v.name] = poly
            summaries[v.name] = (dist_m, dur_s)
            print(
                f"{v.name}: distance={dist_m/1000:.2f} km, duration={dur_s/60:.2f} min, points={len(poly)}"
            )
        except Exception as e:
            print(f"Failed to fetch ORS route for {v.name}: {e}")

    if not polylines:
        print("No ORS routes available. Exiting.")
        return

    # 2) Build a small abstract graph from downsampled ORS routes
    # Feel free to tweak target_waypoints (e.g., 3–6) for performance/realism trade-off
    G, vehicle_way_nodes = build_abstract_graph_from_routes(polylines, target_waypoints=5)
    print(
        f"\nAbstract graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges."
    )

    # 3) Independent A* on abstract graph (baseline)
    print("\n=== Independent A* Paths on Abstract Graph ===")
    for v in vehicles:
        if v.name not in vehicle_way_nodes:
            continue
        start = vehicle_way_nodes[v.name][0]
        goal = vehicle_way_nodes[v.name][-1]
        path_nodes, time_s = astar_shortest_path(G, start, goal)
        if not path_nodes:
            print(f"{v.name}: A* failed to find path.")
            continue
        print(f"{v.name}: A* steps={len(path_nodes)}, abstract time={time_s:.1f} units")

    # 4) Prioritized multi-agent planning (replaces CBS)
    print("\n=== Prioritized Coordinated Paths (Abstract Graph) ===")
    agents: List[Agent] = []
    for v in vehicles:
        if v.name in vehicle_way_nodes:
            nodes_seq = vehicle_way_nodes[v.name]
            agents.append(Agent(name=v.name, start=nodes_seq[0], goal=nodes_seq[-1]))

    if not agents:
        print("No agents with valid abstract start/goal. Exiting.")
        return

    # Priority: shorter ORS duration first (or change policy: ambulance > fire > police etc.)
    priority_order = sorted(
        [a.name for a in agents],
        key=lambda name: summaries[name][1] if name in summaries else float("inf"),
    )

    # max_t should be "enough" for agents to reach the goal; tweak as needed
    coop_paths = prioritized_plan(G, agents, priority_order=priority_order, max_t=50)
    for v in vehicles:
        if v.name not in coop_paths:
            print(f"{v.name}: already at accident site (no movement needed).")
            coop_paths[v.name] = [vehicle_way_nodes.get(v.name, [None])[0] or 0]

    for v in vehicles:
        if v.name not in coop_paths:
            continue
        p = coop_paths[v.name]
        # just re-use ORS duration as “scaled time” like before
        est_minutes = summaries[v.name][1] / 60.0 if v.name in summaries else 0.0
        print(
            f"{v.name}: Coordinated steps={len(p)}, scaled time≈{est_minutes:.2f} min"
        )

    # 5) D*-Lite-style replanning demo for first agent
    if agents:
        print("\n=== D*-Lite-style Replanning Demo (Abstract Graph) ===")
        a0 = agents[0]
        dstar = SimpleDStarLite(G, a0.start, a0.goal)
        print(
            f"{a0.name}: initial A* path (first nodes) = {dstar.path_nodes[:6]} "
            f"(len={len(dstar.path_nodes)})"
        )
        for i in range(2):
            cur = dstar.step()
            print(f"Step {i+1}: {a0.name} at node {cur}")
        nbrs = list(G.successors(dstar.current))
        if nbrs:
            blocked = nbrs[0]
            dstar.block_edge_and_replan(dstar.current, blocked)
            print(
                f"{a0.name}: replanned path (first nodes) = {dstar.path_nodes[:6]} "
                f"(len={len(dstar.path_nodes)})"
            )
        else:
            print("No outgoing edges to block for D*-Lite demo.")

    # 6) Build Route objects using the coordinated abstract paths
    # build_cbs_routes only cares that it gets a dict[name] -> [node_ids over time]
    ors_durations_s = {name: dur for name, (_, dur) in summaries.items()}
    cbs_routes: List[Route] = build_cbs_routes(G, vehicles, coop_paths, ors_durations_s)

    # 7) Simulate for conflicts on continuous coordinates
    simulate_routes(cbs_routes, time_step_s=1.0, conflict_distance_m=10.0)

    # 8) Visualize on Folium and open browser
    print("\nGenerating interactive Folium map (coordinated routes on abstract waypoints)...")
    html_path = render_map(cbs_routes, accident, output_html="routes_map.html", accel=10.0)
    # Serve the map
    port = 5500
    html_path = "routes_map.html"

    print(f"Starting map server on port {port}...")

    # Launch server as SEPARATE PROCESS (fixes VS Code issues)
    server_process = subprocess.Popen(
        ["python3", "serve_map.py", str(port), html_path]
    )

    # Wait a moment for server to start
    time.sleep(1)

    url = f"http://localhost:{port}/{html_path}"
    print(f"Opening {url} ...")
    webbrowser.open(url)


if __name__ == "__main__":
    main()
