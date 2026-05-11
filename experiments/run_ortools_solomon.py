from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_ortools_solomon.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
import math
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from data_parser import parse_solomon
from route_solution import RouteSolution
from verification.route_feasibility import verify_solution


def solve_instance(instance_path: Path, time_limit: int, scale: int = 1000) -> dict[str, str]:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    task = parse_solomon(instance_path)
    started = time.perf_counter()
    manager = pywrapcp.RoutingIndexManager(len(task.all_nodes()), task.vehicles, task.depot.node_id)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(round(task.distance_matrix[from_node][to_node] * scale))

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    routing.SetFixedCostOfAllVehicles(1_000_000_000)

    def demand_callback(from_index: int) -> int:
        node_id = manager.IndexToNode(from_index)
        return int(round(task.node_by_id(node_id).demand))

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [int(round(task.capacity)) for _ in range(task.vehicles)],
        True,
        "Capacity",
    )

    def time_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        service = task.node_by_id(from_node).service_time
        return int(math.ceil((service + task.distance_matrix[from_node][to_node]) * scale))

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    horizon = int(round(max(node.due_time for node in task.all_nodes()) * scale))
    routing.AddDimension(
        time_callback_index,
        horizon,
        horizon,
        False,
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")
    for node in task.all_nodes():
        index = manager.NodeToIndex(node.node_id)
        time_dimension.CumulVar(index).SetRange(
            int(math.ceil(node.ready_time * scale)),
            int(math.floor(node.due_time * scale)),
        )
    for vehicle_id in range(task.vehicles):
        start_index = routing.Start(vehicle_id)
        depot = task.depot
        time_dimension.CumulVar(start_index).SetRange(
            int(math.ceil(depot.ready_time * scale)),
            int(math.floor(depot.due_time * scale)),
        )
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(start_index))
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(vehicle_id)))

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = max(1, int(time_limit))
    search_parameters.log_search = False

    assignment = routing.SolveWithParameters(search_parameters)
    runtime = time.perf_counter() - started
    routes: list[list[int]] = []
    status = str(routing.status())
    if assignment is not None:
        for vehicle_id in range(task.vehicles):
            index = routing.Start(vehicle_id)
            route: list[int] = []
            while not routing.IsEnd(index):
                node_id = manager.IndexToNode(index)
                if node_id != task.depot.node_id:
                    route.append(node_id)
                index = assignment.Value(routing.NextVar(index))
            if route:
                routes.append(route)
    solution = RouteSolution(
        solution_id=f"{task.task_id}:ortools",
        routes=routes,
        runtime=runtime,
        generator_name="ortools_routing",
    )
    result = verify_solution(task, solution)
    return {
        "dataset": task.task_id,
        "method": "ortools_routing",
        "time_limit": str(time_limit),
        "status": status,
        "vehicles": str(result.vehicle_number),
        "distance": f"{result.total_distance:.6f}",
        "feasible": str(result.feasible),
        "violations": str(len(result.violations)),
        "runtime": f"{runtime:.6f}",
    }


def _worker(payload: tuple[str, int]) -> tuple[str, dict[str, str]]:
    path_text, time_limit = payload
    path = Path(path_text)
    return path.name, solve_instance(path, time_limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OR-Tools Routing Solver on Solomon VRPTW instances.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--instances", nargs="*", default=[])
    parser.add_argument("--time-limit", type=int, default=30)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("results/tables/ortools_solomon.csv"))
    args = parser.parse_args()

    if args.instances:
        paths = [args.instance_dir / name for name in args.instances]
    else:
        paths = sorted(args.instance_dir.glob("*.txt"))
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing instances: {missing}")
    if not paths:
        raise FileNotFoundError(f"No .txt instances found in {args.instance_dir}")

    rows: list[dict[str, str]] = []
    if args.workers <= 1:
        for index, path in enumerate(paths, start=1):
            print(f"[{index}/{len(paths)}] {path.name}", flush=True)
            rows.append(solve_instance(path, args.time_limit))
    else:
        futures_payload = [(str(path), args.time_limit) for path in paths]
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_worker, payload) for payload in futures_payload]
            for index, future in enumerate(as_completed(futures), start=1):
                name, row = future.result()
                print(f"[{index}/{len(paths)}] {name}", flush=True)
                rows.append(row)

    rows.sort(key=lambda row: row["dataset"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
