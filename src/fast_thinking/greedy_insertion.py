from __future__ import annotations

import time

from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from fast_thinking.common import best_insertion, finish_solution, is_route_feasible


def greedy_insertion(task: LogisticsTask) -> RouteSolution:
    started = time.perf_counter()
    unserved = set(task.node_ids)
    routes: list[list[int]] = []

    while unserved:
        best_choice: tuple[int, int, int, float] | None = None
        for node_id in sorted(unserved):
            insertion = best_insertion(task, routes, node_id)
            if insertion is not None:
                route_index, position, delta = insertion
                if best_choice is None or delta < best_choice[3]:
                    best_choice = (node_id, route_index, position, delta)
        if best_choice is None:
            node_id = min(unserved)
            if not is_route_feasible(task, [node_id]):
                routes.append([node_id])
            else:
                routes.append([node_id])
            unserved.remove(node_id)
            continue
        node_id, route_index, position, _ = best_choice
        routes[route_index].insert(position, node_id)
        unserved.remove(node_id)

    solution = RouteSolution(
        solution_id=f"{task.task_id}:greedy_insertion",
        routes=routes,
        runtime=time.perf_counter() - started,
        generator_name="greedy_insertion",
    )
    return finish_solution(task, solution)
