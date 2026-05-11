from __future__ import annotations

from route_solution import RouteSolution
from distance_matrix import solution_distance
from task_abstraction import LogisticsTask


def evaluate_objective(task: LogisticsTask, solution: RouteSolution) -> RouteSolution:
    solution.routes = [route for route in solution.routes if route]
    solution.vehicle_number = len(solution.routes)
    solution.total_distance = solution_distance(task, solution.routes)
    return solution
