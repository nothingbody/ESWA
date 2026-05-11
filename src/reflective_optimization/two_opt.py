from __future__ import annotations

from distance_matrix import route_distance
from fast_thinking.common import is_route_feasible
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


def two_opt(task: LogisticsTask, solution: RouteSolution) -> RouteSolution:
    improved = solution.copy(solution_id=f"{solution.solution_id}:2opt")
    for route_index, route in enumerate(improved.routes):
        changed = True
        while changed:
            changed = False
            best_distance = route_distance(task, route)
            for i in range(len(route) - 1):
                for j in range(i + 2, len(route) + 1):
                    candidate = route[:i] + list(reversed(route[i:j])) + route[j:]
                    if is_route_feasible(task, candidate) and route_distance(task, candidate) + 1e-9 < best_distance:
                        route = candidate
                        best_distance = route_distance(task, route)
                        changed = True
            improved.routes[route_index] = route
    verify_solution(task, improved)
    return improved
