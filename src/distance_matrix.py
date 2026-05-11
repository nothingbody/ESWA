from __future__ import annotations

import math
from typing import List

from task_abstraction import LogisticsTask, Node


def euclidean_distance(a: Node, b: Node) -> float:
    return math.hypot(a.x_coordinate - b.x_coordinate, a.y_coordinate - b.y_coordinate)


def build_euclidean_distance_matrix(task: LogisticsTask) -> List[List[float]]:
    nodes = task.all_nodes()
    max_id = max(node.node_id for node in nodes)
    matrix = [[0.0 for _ in range(max_id + 1)] for _ in range(max_id + 1)]
    for origin in nodes:
        for destination in nodes:
            matrix[origin.node_id][destination.node_id] = euclidean_distance(origin, destination)
    return matrix


def travel_distance(task: LogisticsTask, origin_id: int, destination_id: int) -> float:
    if not task.distance_matrix:
        task.distance_matrix = build_euclidean_distance_matrix(task)
    return task.distance_matrix[origin_id][destination_id]


def route_distance(task: LogisticsTask, route: List[int]) -> float:
    depot_id = task.depot.node_id
    previous = depot_id
    total = 0.0
    for node_id in route:
        total += travel_distance(task, previous, node_id)
        previous = node_id
    total += travel_distance(task, previous, depot_id)
    return total


def solution_distance(task: LogisticsTask, routes: List[List[int]]) -> float:
    return sum(route_distance(task, route) for route in routes)
