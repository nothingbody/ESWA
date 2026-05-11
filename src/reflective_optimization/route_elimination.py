from __future__ import annotations

from distance_matrix import route_distance, solution_distance
from fast_thinking.common import are_routes_feasible, best_insertion, best_pair_insertion
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


def _clean(routes: list[list[int]]) -> list[list[int]]:
    return [route for route in routes if route]


def _objective(task: LogisticsTask, routes: list[list[int]]) -> tuple[int, float]:
    cleaned = _clean(routes)
    return len(cleaned), solution_distance(task, cleaned)


def _unique_orders(orders: list[list[int]]) -> list[list[int]]:
    unique: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for order in orders:
        key = tuple(order)
        if key not in seen:
            seen.add(key)
            unique.append(order)
    return unique


def _insert_nodes(task: LogisticsTask, routes: list[list[int]], nodes: list[int]) -> list[list[int]] | None:
    candidate = [route[:] for route in routes]
    for node_id in nodes:
        insertion = best_insertion(task, candidate, node_id)
        if insertion is None:
            return None
        route_index, position, _ = insertion
        candidate[route_index].insert(position, node_id)
    return _clean(candidate)


def _try_vrptw_elimination(task: LogisticsTask, routes: list[list[int]], source_index: int) -> list[list[int]] | None:
    source = routes[source_index]
    remaining = [route[:] for index, route in enumerate(routes) if index != source_index]
    if not remaining:
        return None
    orders = _unique_orders(
        [
            source[:],
            sorted(source, key=lambda node_id: task.node_by_id(node_id).due_time),
            sorted(source, key=lambda node_id: task.node_by_id(node_id).demand, reverse=True),
            list(reversed(source)),
        ]
    )
    candidates: list[list[list[int]]] = []
    for order in orders:
        candidate = _insert_nodes(task, remaining, order)
        if candidate is not None and are_routes_feasible(task, candidate, enforce_vehicle_limit=False):
            candidates.append(candidate)
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: _objective(task, candidate))


def _pairs_from_route(task: LogisticsTask, route: list[int]) -> tuple[list[int], list[int]]:
    route_nodes = set(route)
    delivery_to_pickup = {delivery_id: pickup_id for pickup_id, delivery_id in task.pickup_delivery_pairs.items()}
    pickups: list[int] = []
    stray_nodes: list[int] = []
    seen_pickups: set[int] = set()
    for node_id in route:
        if node_id in task.pickup_delivery_pairs:
            delivery_id = task.pickup_delivery_pairs[node_id]
            if delivery_id in route_nodes:
                if node_id not in seen_pickups:
                    pickups.append(node_id)
                    seen_pickups.add(node_id)
            else:
                stray_nodes.append(node_id)
        elif node_id in delivery_to_pickup:
            pickup_id = delivery_to_pickup[node_id]
            if pickup_id not in route_nodes:
                stray_nodes.append(node_id)
        else:
            stray_nodes.append(node_id)
    return pickups, stray_nodes


def _insert_pairs(
    task: LogisticsTask,
    routes: list[list[int]],
    pickup_order: list[int],
    stray_nodes: list[int],
) -> list[list[int]] | None:
    candidate = [route[:] for route in routes]
    for pickup_id in pickup_order:
        delivery_id = task.pickup_delivery_pairs[pickup_id]
        insertion = best_pair_insertion(task, candidate, pickup_id, delivery_id)
        if insertion is None:
            return None
        route_index, pickup_position, delivery_position, _ = insertion
        route = candidate[route_index]
        route.insert(pickup_position, pickup_id)
        route.insert(delivery_position, delivery_id)
    if stray_nodes:
        candidate = _insert_nodes(task, candidate, stray_nodes)
        if candidate is None:
            return None
    return _clean(candidate)


def _try_pdptw_elimination(task: LogisticsTask, routes: list[list[int]], source_index: int) -> list[list[int]] | None:
    source = routes[source_index]
    remaining = [route[:] for index, route in enumerate(routes) if index != source_index]
    if not remaining:
        return None
    pickups, stray_nodes = _pairs_from_route(task, source)
    if not pickups and not stray_nodes:
        return _clean(remaining)
    pair_orders = _unique_orders(
        [
            pickups[:],
            sorted(pickups, key=lambda pickup_id: task.node_by_id(task.pickup_delivery_pairs[pickup_id]).due_time),
            sorted(pickups, key=lambda pickup_id: route_distance(task, [pickup_id, task.pickup_delivery_pairs[pickup_id]]), reverse=True),
            list(reversed(pickups)),
        ]
    )
    stray_order = sorted(stray_nodes, key=lambda node_id: task.node_by_id(node_id).due_time)
    candidates: list[list[list[int]]] = []
    for pair_order in pair_orders:
        candidate = _insert_pairs(task, remaining, pair_order, stray_order)
        if candidate is not None and are_routes_feasible(task, candidate, enforce_vehicle_limit=False):
            candidates.append(candidate)
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: _objective(task, candidate))


def _auto_source_limit(task: LogisticsTask) -> int | None:
    node_count = len(task.node_ids)
    if node_count >= 300:
        return 8
    if node_count >= 150:
        return 6
    return None


def _auto_pass_limit(task: LogisticsTask) -> int | None:
    node_count = len(task.node_ids)
    if node_count >= 300:
        return 2
    if node_count >= 150:
        return 4
    return None


def route_elimination(
    task: LogisticsTask,
    solution: RouteSolution,
    max_sources: int | None = None,
    max_passes: int | None = None,
) -> RouteSolution:
    eliminated = solution.copy(solution_id=f"{solution.solution_id}:eliminate")
    source_limit = _auto_source_limit(task) if max_sources is None else max_sources
    pass_limit = _auto_pass_limit(task) if max_passes is None else max_passes
    passes = 0
    changed = True
    while changed and (pass_limit is None or passes < pass_limit):
        changed = False
        routes = sorted(_clean(eliminated.routes), key=lambda route: (len(route), route_distance(task, route)))
        best_candidate: list[list[int]] | None = None
        best_source_index: int | None = None
        source_indexes = list(range(len(routes)))
        if source_limit is not None:
            source_indexes = source_indexes[:source_limit]
        for source_index in source_indexes:
            if task.problem_type.upper() == "PDPTW":
                candidate = _try_pdptw_elimination(task, routes, source_index)
            else:
                candidate = _try_vrptw_elimination(task, routes, source_index)
            if candidate is None:
                continue
            if _objective(task, candidate) >= _objective(task, routes):
                continue
            if best_candidate is None or _objective(task, candidate) < _objective(task, best_candidate):
                best_candidate = candidate
                best_source_index = source_index
        if best_candidate is not None:
            eliminated.routes = best_candidate
            eliminated.repair_history.append(f"eliminate:{best_source_index}")
            passes += 1
            changed = True
    verify_solution(task, eliminated)
    return eliminated
