from __future__ import annotations

from typing import Dict, List

from task_abstraction import LogisticsTask


def verify_precedence(task: LogisticsTask, routes: List[List[int]]) -> List[Dict[str, object]]:
    violations: List[Dict[str, object]] = []
    if not task.pickup_delivery_pairs:
        return violations

    route_by_node: Dict[int, int] = {}
    position_by_node: Dict[int, int] = {}
    for route_index, route in enumerate(routes):
        for position, node_id in enumerate(route):
            route_by_node[node_id] = route_index
            position_by_node[node_id] = position

    for pickup_id, delivery_id in task.pickup_delivery_pairs.items():
        if pickup_id not in route_by_node or delivery_id not in route_by_node:
            violations.append({"type": "unserved_pair", "pickup_id": pickup_id, "delivery_id": delivery_id})
            continue
        if route_by_node[pickup_id] != route_by_node[delivery_id]:
            violations.append(
                {
                    "type": "same_vehicle",
                    "pickup_id": pickup_id,
                    "delivery_id": delivery_id,
                    "pickup_route": route_by_node[pickup_id],
                    "delivery_route": route_by_node[delivery_id],
                }
            )
        elif position_by_node[pickup_id] > position_by_node[delivery_id]:
            violations.append(
                {
                    "type": "precedence",
                    "pickup_id": pickup_id,
                    "delivery_id": delivery_id,
                    "pickup_position": position_by_node[pickup_id],
                    "delivery_position": position_by_node[delivery_id],
                }
            )
    return violations
