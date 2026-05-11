from __future__ import annotations

from fast_thinking.common import best_insertion
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import VerificationResult, verify_solution


def repair_insertion(
    task: LogisticsTask,
    solution: RouteSolution,
    verification: VerificationResult | None = None,
) -> RouteSolution:
    verification = verification or verify_solution(task, solution)
    repaired = solution.copy(solution_id=f"{solution.solution_id}:repair")
    duplicate_nodes = {
        int(violation["node_id"])
        for violation in verification.violations
        if violation.get("type") in {"duplicate", "unknown_node"} and "node_id" in violation
    }
    seen: set[int] = set()
    clean_routes: list[list[int]] = []
    for route in repaired.routes:
        clean_route: list[int] = []
        for node_id in route:
            if node_id in task.node_ids and node_id not in seen and node_id not in duplicate_nodes:
                clean_route.append(node_id)
                seen.add(node_id)
        if clean_route:
            clean_routes.append(clean_route)
    repaired.routes = clean_routes
    missing = sorted(set(verification.unserved_nodes) | (set(task.node_ids) - seen) | (duplicate_nodes & set(task.node_ids)))

    for node_id in missing:
        insertion = best_insertion(task, repaired.routes, node_id)
        if insertion is None:
            repaired.routes.append([node_id])
            repaired.repair_history.append(f"new_route:{node_id}")
        else:
            route_index, position, _ = insertion
            repaired.routes[route_index].insert(position, node_id)
            repaired.repair_history.append(f"insert:{node_id}@{route_index}:{position}")
    verify_solution(task, repaired)
    return repaired
