from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from distance_matrix import solution_distance
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.capacity_verifier import verify_capacity
from verification.objective_evaluator import evaluate_objective
from verification.precedence_verifier import verify_precedence
from verification.service_time_verifier import verify_service_times
from verification.time_window_verifier import verify_time_windows


@dataclass
class VerificationResult:
    feasible: bool
    violations: List[Dict[str, object]] = field(default_factory=list)
    total_distance: float = 0.0
    vehicle_number: int = 0
    time_window_violation: int = 0
    capacity_violation: int = 0
    precedence_violation: int = 0
    same_vehicle_violation: int = 0
    unserved_nodes: List[int] = field(default_factory=list)


def verify_solution(task: LogisticsTask, solution: RouteSolution) -> VerificationResult:
    served = solution.served_nodes()
    required = set(task.node_ids)
    served_set = set(served)
    duplicate_nodes = sorted({node_id for node_id in served if served.count(node_id) > 1})
    unserved_nodes = sorted(required - served_set)
    extra_nodes = sorted(served_set - required)
    known_routes = [[node_id for node_id in route if node_id in required] for route in solution.routes]

    violations: List[Dict[str, object]] = []
    violations.extend(verify_capacity(task, known_routes))
    violations.extend(verify_time_windows(task, known_routes))
    violations.extend(verify_service_times(task, known_routes))
    violations.extend(verify_precedence(task, known_routes))
    violations.extend({"type": "unserved", "node_id": node_id} for node_id in unserved_nodes)
    violations.extend({"type": "duplicate", "node_id": node_id} for node_id in duplicate_nodes)
    violations.extend({"type": "unknown_node", "node_id": node_id} for node_id in extra_nodes)

    if extra_nodes:
        solution.routes = [route for route in solution.routes if route]
        solution.vehicle_number = len(solution.routes)
        solution.total_distance = solution_distance(task, [route for route in known_routes if route])
    else:
        evaluate_objective(task, solution)
    solution.unserved_nodes = unserved_nodes
    solution.violations = violations
    solution.feasible = not violations and solution.vehicle_number <= task.vehicles
    if solution.vehicle_number > task.vehicles:
        violations.append({"type": "vehicle_count", "vehicles": solution.vehicle_number, "limit": task.vehicles})
        solution.feasible = False

    return VerificationResult(
        feasible=solution.feasible,
        violations=violations,
        total_distance=solution.total_distance,
        vehicle_number=solution.vehicle_number,
        time_window_violation=sum(1 for violation in violations if violation["type"] in {"time_window", "depot_time_window"}),
        capacity_violation=sum(1 for violation in violations if violation["type"] in {"capacity", "negative_load"}),
        precedence_violation=sum(1 for violation in violations if violation["type"] == "precedence"),
        same_vehicle_violation=sum(1 for violation in violations if violation["type"] == "same_vehicle"),
        unserved_nodes=unserved_nodes,
    )
