# app.py
from flask import Flask, render_template, request, jsonify, send_file
from typing import List, Dict
import time
import os

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

app = Flask(__name__)


def run_pipeline(acc_lat: float, acc_lon: float, vehicles_in: List[dict]):
    """
    Core logic: almost exactly your main(), but parameterized
    and returning JSON-friendly results.
    """
    accident = AccidentSite(lat=acc_lat, lon=acc_lon)
    vehicles: List[Vehicle] = [
        Vehicle(name=v["name"], lat=v["lat"], lon=v["lon"]) for v in vehicles_in
    ]

    # 1) ORS routes
    client = create_ors_client()
    polylines: Dict[str, List[tuple]] = {}
    summaries: Dict[str, tuple] = {}  # name -> (dist_m, dur_s)

    for v in vehicles:
        rjson = fetch_route_geojson(client, v.lat, v.lon, accident.lat, accident.lon)
        poly, dist_m, dur_s = extract_polyline_and_summary(rjson)
        polylines[v.name] = poly
        summaries[v.name] = (dist_m, dur_s)

    if not polylines:
        raise RuntimeError("No ORS routes available")

    # 2) Abstract graph
    G, vehicle_way_nodes = build_abstract_graph_from_routes(
        polylines, target_waypoints=5
    )

    # 3) Independent A*
    indep_start = time.perf_counter()
    indep_info = []
    for v in vehicles:
        if v.name not in vehicle_way_nodes:
            continue
        start = vehicle_way_nodes[v.name][0]
        goal = vehicle_way_nodes[v.name][-1]
        path_nodes, time_s = astar_shortest_path(G, start, goal)
        if path_nodes:
            indep_info.append(
                {
                    "vehicle": v.name,
                    "steps": len(path_nodes),
                    "abstract_time": time_s,
                    "eta_min": summaries[v.name][1] / 60.0,
                }
            )
    indep_time_ms = (time.perf_counter() - indep_start) * 1000.0

    # 4) Prioritized multi-agent planning
    agents: List[Agent] = []
    for v in vehicles:
        if v.name in vehicle_way_nodes:
            nodes_seq = vehicle_way_nodes[v.name]
            agents.append(Agent(name=v.name, start=nodes_seq[0], goal=nodes_seq[-1]))
    if not agents:
        raise RuntimeError("No agents with valid abstract start/goal")

    priority_order = sorted(
        [a.name for a in agents],
        key=lambda name: summaries[name][1] if name in summaries else float("inf"),
    )

    coop_start = time.perf_counter()
    coop_paths = prioritized_plan(G, agents, priority_order=priority_order, max_t=50)
    # vehicles already at goal
    for v in vehicles:
        if v.name not in coop_paths:
            coop_paths[v.name] = [vehicle_way_nodes.get(v.name, [None])[0] or 0]
    coop_time_ms = (time.perf_counter() - coop_start) * 1000.0

    coop_info = []
    for v in vehicles:
        if v.name in coop_paths:
            coop_info.append(
                {
                    "vehicle": v.name,
                    "steps": len(coop_paths[v.name]),
                    "eta_min": summaries[v.name][1] / 60.0,
                }
            )

    # 5) D*-Lite demo for first agent (optional, just report some stats)
    dstar_info = {}
    if agents:
        a0 = agents[0]
        dstar = SimpleDStarLite(G, a0.start, a0.goal)
        dstar_info["vehicle"] = a0.name
        dstar_info["initial_len"] = len(dstar.path_nodes)
        # take a couple of steps then block one edge and replan
        for _ in range(2):
            dstar.step()
        nbrs = list(G.successors(dstar.current))
        if nbrs:
            blocked = nbrs[0]
            dstar.block_edge_and_replan(dstar.current, blocked)
            dstar_info["replanned_len"] = len(dstar.path_nodes)
        else:
            dstar_info["replanned_len"] = dstar_info["initial_len"]

    # 6) Build routes & simulate
    ors_durations_s = {name: dur for name, (_, dur) in summaries.items()}
    cbs_routes: List[Route] = build_cbs_routes(G, vehicles, coop_paths, ors_durations_s)
    simulate_routes(cbs_routes, time_step_s=1.0, conflict_distance_m=10.0)

    # 7) Render Folium map to HTML
    map_filename = "routes_map.html"
    render_map(cbs_routes, accident, output_html=map_filename, accel=10.0)

    # Prepare a compact summary for front-end
    results = {
        "independent": {
            "algo": "Independent A*",
            "vehicles": indep_info,
            "time_ms": indep_time_ms,
        },
        "cooperative": {
            "algo": "Prioritized Cooperative A*",
            "vehicles": coop_info,
            "time_ms": coop_time_ms,
        },
        "dstar": dstar_info,
        "map_path": map_filename,
    }
    return results


# -------------------- Flask routes --------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run_algorithms", methods=["POST"])
def run_algorithms():
    data = request.get_json()
    try:
        acc = data["accident"]
        vehicles = data["vehicles"]
        acc_lat = float(acc["lat"])
        acc_lon = float(acc["lon"])
        for v in vehicles:
            v["lat"] = float(v["lat"])
            v["lon"] = float(v["lon"])

        results = run_pipeline(acc_lat, acc_lon, vehicles)
        return jsonify({"ok": True, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/map")
def map_view():
    # Serve the latest generated map
    fname = "routes_map.html"
    if not os.path.exists(fname):
        return "No map generated yet. Run the algorithms first.", 404
    return send_file(fname)


if __name__ == "__main__":
    # Run Flask dev server
    app.run(host="0.0.0.0", port=5500, debug=True)
