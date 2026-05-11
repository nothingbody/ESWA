from __future__ import annotations

from typing import Dict, List

from task_abstraction import LogisticsTask


def verify_service_times(task: LogisticsTask, routes: List[List[int]]) -> List[Dict[str, object]]:
    violations: List[Dict[str, object]] = []
    for route_index, route in enumerate(routes):
        for position, node_id in enumerate(route):
            if task.node_by_id(node_id).service_time < 0:
                violations.append(
                    {
                        "type": "service_time",
                        "route_index": route_index,
                        "position": position,
                        "node_id": node_id,
                    }
                )
    return violations
