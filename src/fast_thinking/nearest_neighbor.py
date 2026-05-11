from __future__ import annotations

import time

from distance_matrix import travel_distance
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from fast_thinking.common import finish_solution, is_route_feasible


def nearest_neighbor(task: LogisticsTask) -> RouteSolution:
    started = time.perf_counter()
    unserved = set(task.node_ids)
    routes: list[list[int]] = []

    while unserved:
        route: list[int] = []
        current = task.depot.node_id
        while unserved:
            ordered = sorted(unserved, key=lambda node_id: travel_distance(task, current, node_id))
            next_node = None
            for node_id in ordered:
                candidate = route + [node_id]
                if is_route_feasible(task, candidate):
                    next_node = node_id
                    break
            if next_node is None:
                break
            route.append(next_node)
            unserved.remove(next_node)
            current = next_node
        if not route:
            node_id = min(unserved)
            route = [node_id]
            unserved.remove(node_id)
        routes.append(route)

    solution = RouteSolution(
        solution_id=f"{task.task_id}:nearest_neighbor",
        routes=routes,
        runtime=time.perf_counter() - started,
        generator_name="nearest_neighbor",
    )
    return finish_solution(task, solution)
