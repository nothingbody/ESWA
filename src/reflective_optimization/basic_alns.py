from __future__ import annotations

import random
import time
from dataclasses import dataclass

from distance_matrix import route_distance, solution_distance
from fast_thinking.common import are_routes_feasible, best_insertion
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


@dataclass
class AlnsConfig:
    iterations: int = 400
    removal_fraction: float = 0.12
    seed: int = 42
    time_limit: float = 0.0
    route_elimination_interval: int = 20


def _objective(task: LogisticsTask, routes: list[list[int]]) -> tuple[int, float]:
    return len([route for route in routes if route]), solution_distance(task, routes)


def _better(task: LogisticsTask, candidate: list[list[int]], incumbent: list[list[int]]) -> bool:
    return _objective(task, candidate) < _objective(task, incumbent)


def _clean_routes(routes: list[list[int]]) -> list[list[int]]:
    return [route for route in routes if route]


def _remove_nodes(task: LogisticsTask, routes: list[list[int]], rng: random.Random, fraction: float) -> tuple[list[list[int]], list[int]]:
    all_nodes = [node_id for route in routes for node_id in route]
    if not all_nodes:
        return routes, []
    remove_count = max(1, int(len(all_nodes) * fraction))
    remove_count = min(remove_count, max(1, len(all_nodes) - 1))
    if rng.random() < 0.5:
        removed = set(rng.sample(all_nodes, remove_count))
    else:
        contributions: list[tuple[float, int]] = []
        for route in routes:
            base = route_distance(task, route)
            for node_id in route:
                candidate = [item for item in route if item != node_id]
                contributions.append((base - route_distance(task, candidate), node_id))
        contributions.sort(reverse=True)
        removed = {node_id for _, node_id in contributions[:remove_count]}
    kept = [[node_id for node_id in route if node_id not in removed] for route in routes]
    return _clean_routes(kept), list(removed)


def _repair(task: LogisticsTask, routes: list[list[int]], removed: list[int]) -> list[list[int]]:
    repaired = [route[:] for route in routes]
    for node_id in sorted(removed, key=lambda item: task.node_by_id(item).due_time):
        insertion = best_insertion(task, repaired, node_id)
        if insertion is None:
            repaired.append([node_id])
        else:
            route_index, position, _ = insertion
            repaired[route_index].insert(position, node_id)
    return _clean_routes(repaired)


def basic_alns(task: LogisticsTask, solution: RouteSolution, config: AlnsConfig | None = None) -> RouteSolution:
    config = config or AlnsConfig()
    rng = random.Random(config.seed)
    started = time.perf_counter()
    current = route_elimination(task, route_merge(task, solution)).routes
    best = [route[:] for route in current]

    for iteration in range(config.iterations):
        if config.time_limit > 0 and time.perf_counter() - started >= config.time_limit:
            break
        candidate_base, removed = _remove_nodes(task, current, rng, config.removal_fraction)
        candidate = _repair(task, candidate_base, removed)
        candidate_solution = route_merge(task, RouteSolution(solution_id="candidate", routes=candidate))
        if config.route_elimination_interval > 0 and iteration % config.route_elimination_interval == 0:
            candidate_solution = route_elimination(task, candidate_solution)
        candidate = candidate_solution.routes
        if not are_routes_feasible(task, candidate, enforce_vehicle_limit=False):
            continue
        if _better(task, candidate, current) or rng.random() < 0.02:
            current = [route[:] for route in candidate]
        if _better(task, current, best):
            best = [route[:] for route in current]

    best = route_elimination(task, RouteSolution(solution_id="best_candidate", routes=best)).routes

    improved = RouteSolution(
        solution_id=f"{solution.solution_id}:basic_alns",
        routes=best,
        runtime=solution.runtime + (time.perf_counter() - started),
        generator_name=f"{solution.generator_name}+basic_alns",
    )
    verify_solution(task, improved)
    return improved
