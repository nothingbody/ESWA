from __future__ import annotations

import time

from fast_thinking.common import best_pair_insertion, finish_solution, is_route_feasible
from route_solution import RouteSolution
from task_abstraction import LogisticsTask


def greedy_pair_insertion(task: LogisticsTask) -> RouteSolution:
    started = time.perf_counter()
    if task.problem_type.upper() != "PDPTW":
        raise ValueError("greedy_pair_insertion requires a PDPTW task")
    unserved_pairs = set(task.pickup_delivery_pairs)
    routes: list[list[int]] = []

    while unserved_pairs:
        best_choice: tuple[int, int, int, int, float] | None = None
        for pickup_id in sorted(unserved_pairs):
            delivery_id = task.pickup_delivery_pairs[pickup_id]
            insertion = best_pair_insertion(task, routes, pickup_id, delivery_id)
            if insertion is None:
                pair_route = [pickup_id, delivery_id]
                if is_route_feasible(task, pair_route):
                    routes.append(pair_route)
                    best_choice = None
                    unserved_pairs.remove(pickup_id)
                    break
                routes.append(pair_route)
                unserved_pairs.remove(pickup_id)
                break
            route_index, pickup_position, delivery_position, delta = insertion
            if best_choice is None or delta < best_choice[4]:
                best_choice = (pickup_id, route_index, pickup_position, delivery_position, delta)
        else:
            if best_choice is not None:
                pickup_id, route_index, pickup_position, delivery_position, _ = best_choice
                delivery_id = task.pickup_delivery_pairs[pickup_id]
                route = routes[route_index]
                route.insert(pickup_position, pickup_id)
                route.insert(delivery_position, delivery_id)
                unserved_pairs.remove(pickup_id)
            continue

    solution = RouteSolution(
        solution_id=f"{task.task_id}:greedy_pair_insertion",
        routes=routes,
        runtime=time.perf_counter() - started,
        generator_name="greedy_pair_insertion",
    )
    return finish_solution(task, solution)
