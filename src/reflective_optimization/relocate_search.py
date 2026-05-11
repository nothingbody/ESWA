from __future__ import annotations

from distance_matrix import solution_distance
from fast_thinking.common import are_routes_feasible
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


def relocate_search(task: LogisticsTask, solution: RouteSolution) -> RouteSolution:
    current = solution.copy(solution_id=f"{solution.solution_id}:relocate")
    best_distance = solution_distance(task, current.routes)
    improved = True
    while improved:
        improved = False
        for source_index, route in enumerate(current.routes):
            for position, node_id in enumerate(route):
                source_without = route[:position] + route[position + 1 :]
                for target_index, target_route in enumerate(current.routes):
                    for target_position in range(len(target_route) + 1):
                        if source_index == target_index and target_position in {position, position + 1}:
                            continue
                        candidate_routes = [candidate[:] for candidate in current.routes]
                        candidate_routes[source_index] = source_without
                        insert_target = candidate_routes[target_index]
                        if source_index == target_index:
                            insert_target = source_without
                            candidate_routes[target_index] = insert_target
                        insert_target.insert(target_position, node_id)
                        candidate_routes = [candidate for candidate in candidate_routes if candidate]
                        if are_routes_feasible(task, candidate_routes, enforce_vehicle_limit=False):
                            distance = solution_distance(task, candidate_routes)
                            if distance + 1e-9 < best_distance:
                                current.routes = candidate_routes
                                best_distance = distance
                                improved = True
                                break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break
    verify_solution(task, current)
    return current
