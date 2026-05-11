from __future__ import annotations

import time

from fast_thinking.common import finish_solution, insertion_options
from route_solution import RouteSolution
from task_abstraction import LogisticsTask


def _insertions(task: LogisticsTask, routes: list[list[int]], node_id: int) -> list[tuple[int, int, float]]:
    return insertion_options(task, routes, node_id)


def regret_insertion(task: LogisticsTask) -> RouteSolution:
    started = time.perf_counter()
    unserved = set(task.node_ids)
    routes: list[list[int]] = []
    if unserved:
        seed = min(unserved, key=lambda node_id: task.node_by_id(node_id).due_time)
        routes.append([seed])
        unserved.remove(seed)

    while unserved:
        best_choice: tuple[int, int, int, float] | None = None
        for node_id in sorted(unserved):
            options = _insertions(task, routes, node_id)
            if options:
                best = options[0]
                second_cost = options[1][2] if len(options) > 1 else best[2] + 1_000_000.0
                regret = second_cost - best[2]
                if best_choice is None or regret > best_choice[3]:
                    best_choice = (node_id, best[0], best[1], regret)
        if best_choice is None:
            node_id = min(unserved)
            routes.append([node_id])
            unserved.remove(node_id)
            continue
        node_id, route_index, position, _ = best_choice
        routes[route_index].insert(position, node_id)
        unserved.remove(node_id)

    solution = RouteSolution(
        solution_id=f"{task.task_id}:regret_insertion",
        routes=routes,
        runtime=time.perf_counter() - started,
        generator_name="regret_insertion",
    )
    return finish_solution(task, solution)
