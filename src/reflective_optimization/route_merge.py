from __future__ import annotations

from distance_matrix import route_distance
from fast_thinking.common import are_routes_feasible, insertion_delta, is_insertion_feasible
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


def _best_insert_route(task: LogisticsTask, target: list[int], source: list[int]) -> list[int] | None:
    route = target[:]
    for node_id in source:
        best_candidate: list[int] | None = None
        best_distance_proxy = float("inf")
        for position in range(len(route) + 1):
            if is_insertion_feasible(task, route, node_id, position):
                proxy = insertion_delta(task, route, node_id, position)
                if proxy < best_distance_proxy:
                    best_candidate = route[:position] + [node_id] + route[position:]
                    best_distance_proxy = proxy
        if best_candidate is None:
            return None
        route = best_candidate
    return route


def route_merge(task: LogisticsTask, solution: RouteSolution) -> RouteSolution:
    merged = solution.copy(solution_id=f"{solution.solution_id}:merge")
    changed = True
    while changed:
        changed = False
        merged.routes = sorted([route for route in merged.routes if route], key=len)
        for source_index, source in enumerate(merged.routes):
            for target_index, target in enumerate(merged.routes):
                if source_index == target_index:
                    continue
                candidate_route = _best_insert_route(task, target, source)
                if candidate_route is None:
                    continue
                candidate_routes = [
                    route
                    for index, route in enumerate(merged.routes)
                    if index not in {source_index, target_index}
                ]
                candidate_routes.append(candidate_route)
                if are_routes_feasible(task, candidate_routes, enforce_vehicle_limit=False):
                    merged.routes = candidate_routes
                    merged.repair_history.append(f"merge:{source_index}->{target_index}")
                    changed = True
                    break
            if changed:
                break
    verify_solution(task, merged)
    return merged
