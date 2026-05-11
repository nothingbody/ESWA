from __future__ import annotations

from typing import Dict, List

from task_abstraction import LogisticsTask


def verify_capacity(task: LogisticsTask, routes: List[List[int]]) -> List[Dict[str, object]]:
    violations: List[Dict[str, object]] = []
    for route_index, route in enumerate(routes):
        load = 0.0
        peak_load = 0.0
        min_load = 0.0
        for position, node_id in enumerate(route):
            load += task.node_by_id(node_id).demand
            peak_load = max(peak_load, load)
            min_load = min(min_load, load)
            if load > task.capacity:
                violations.append(
                    {
                        "type": "capacity",
                        "route_index": route_index,
                        "position": position,
                        "node_id": node_id,
                        "load": load,
                        "capacity": task.capacity,
                    }
                )
        if task.problem_type.upper() == "PDPTW" and min_load < 0:
            violations.append(
                {
                    "type": "negative_load",
                    "route_index": route_index,
                    "min_load": min_load,
                    "peak_load": peak_load,
                }
            )
    return violations
