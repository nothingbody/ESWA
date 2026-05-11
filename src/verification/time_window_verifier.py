from __future__ import annotations

from typing import Dict, List, Tuple

from distance_matrix import travel_distance
from task_abstraction import LogisticsTask


def schedule_route(task: LogisticsTask, route: List[int]) -> Tuple[bool, List[Dict[str, float]], List[Dict[str, object]]]:
    depot_id = task.depot.node_id
    previous = depot_id
    current_time = max(0.0, task.depot.ready_time)
    schedule: List[Dict[str, float]] = []
    violations: List[Dict[str, object]] = []

    for position, node_id in enumerate(route):
        node = task.node_by_id(node_id)
        arrival = current_time + travel_distance(task, previous, node_id)
        service_start = max(arrival, node.ready_time)
        if service_start > node.due_time:
            violations.append(
                {
                    "type": "time_window",
                    "position": position,
                    "node_id": node_id,
                    "arrival": arrival,
                    "service_start": service_start,
                    "due_time": node.due_time,
                }
            )
        schedule.append({"node_id": node_id, "arrival": arrival, "service_start": service_start})
        current_time = service_start + node.service_time
        previous = node_id

    depot_arrival = current_time + travel_distance(task, previous, depot_id)
    if depot_arrival > task.depot.due_time:
        violations.append(
            {
                "type": "depot_time_window",
                "node_id": depot_id,
                "arrival": depot_arrival,
                "due_time": task.depot.due_time,
            }
        )
    return not violations, schedule, violations


def verify_time_windows(task: LogisticsTask, routes: List[List[int]]) -> List[Dict[str, object]]:
    violations: List[Dict[str, object]] = []
    for route_index, route in enumerate(routes):
        _, _, route_violations = schedule_route(task, route)
        for violation in route_violations:
            violation["route_index"] = route_index
            violations.append(violation)
    return violations
