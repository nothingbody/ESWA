from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from distance_matrix import route_distance, travel_distance
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


@dataclass(frozen=True)
class _RouteState:
    departures: list[float]
    loads: list[float]


def _valid_node_ids(task: LogisticsTask) -> set[int]:
    cached = getattr(task, "_valid_node_id_set", None)
    if cached is None:
        cached = set(task.node_ids)
        setattr(task, "_valid_node_id_set", cached)
    return cached


def _route_with_insertion(route: List[int], node_id: int, position: int) -> Iterable[int]:
    for index, current in enumerate(route):
        if index == position:
            yield node_id
        yield current
    if position == len(route):
        yield node_id


def _is_sequence_feasible(task: LogisticsTask, sequence: Iterable[int], known_unique: bool = False) -> bool:
    valid_node_ids = _valid_node_ids(task)
    seen: set[int] = set()
    previous = task.depot.node_id
    current_time = max(0.0, task.depot.ready_time)
    load = 0.0
    min_load = 0.0
    positions: dict[int, int] = {}
    problem_type = task.problem_type.upper()

    for position, node_id in enumerate(sequence):
        if node_id not in valid_node_ids:
            return False
        if not known_unique:
            if node_id in seen:
                return False
            seen.add(node_id)
        positions[node_id] = position
        node = task.node_by_id(node_id)
        if node.service_time < 0:
            return False
        load += node.demand
        min_load = min(min_load, load)
        if load > task.capacity:
            return False
        arrival = current_time + travel_distance(task, previous, node_id)
        service_start = max(arrival, node.ready_time)
        if service_start > node.due_time:
            return False
        current_time = service_start + node.service_time
        previous = node_id

    if problem_type == "PDPTW" and min_load < 0:
        return False
    if current_time + travel_distance(task, previous, task.depot.node_id) > task.depot.due_time:
        return False
    if problem_type == "PDPTW":
        for pickup_id, delivery_id in task.pickup_delivery_pairs.items():
            if pickup_id in positions and delivery_id in positions and positions[pickup_id] > positions[delivery_id]:
                return False
    return True


def is_route_feasible(task: LogisticsTask, route: List[int]) -> bool:
    return _is_sequence_feasible(task, route)


def _build_vrptw_route_state(task: LogisticsTask, route: List[int]) -> _RouteState | None:
    valid_node_ids = _valid_node_ids(task)
    if len(route) != len(set(route)):
        return None
    if any(node_id not in valid_node_ids for node_id in route):
        return None

    departures = [max(0.0, task.depot.ready_time)]
    loads = [0.0]
    previous = task.depot.node_id
    current_time = departures[0]
    load = 0.0
    for node_id in route:
        node = task.node_by_id(node_id)
        if node.service_time < 0:
            return None
        load += node.demand
        if load > task.capacity:
            return None
        arrival = current_time + travel_distance(task, previous, node_id)
        service_start = max(arrival, node.ready_time)
        if service_start > node.due_time:
            return None
        current_time = service_start + node.service_time
        departures.append(current_time)
        loads.append(load)
        previous = node_id
    if current_time + travel_distance(task, previous, task.depot.node_id) > task.depot.due_time:
        return None
    return _RouteState(departures=departures, loads=loads)


def _is_vrptw_insertion_feasible(
    task: LogisticsTask,
    route: List[int],
    state: _RouteState,
    node_id: int,
    position: int,
) -> bool:
    previous_id = task.depot.node_id if position == 0 else route[position - 1]
    node = task.node_by_id(node_id)
    if node.service_time < 0:
        return False

    load = state.loads[position] + node.demand
    if load > task.capacity:
        return False
    current_time = state.departures[position]
    arrival = current_time + travel_distance(task, previous_id, node_id)
    service_start = max(arrival, node.ready_time)
    if service_start > node.due_time:
        return False
    current_time = service_start + node.service_time
    previous_id = node_id

    for suffix_node_id in route[position:]:
        suffix_node = task.node_by_id(suffix_node_id)
        load += suffix_node.demand
        if load > task.capacity:
            return False
        arrival = current_time + travel_distance(task, previous_id, suffix_node_id)
        service_start = max(arrival, suffix_node.ready_time)
        if service_start > suffix_node.due_time:
            return False
        current_time = service_start + suffix_node.service_time
        previous_id = suffix_node_id

    return current_time + travel_distance(task, previous_id, task.depot.node_id) <= task.depot.due_time


def is_insertion_feasible(task: LogisticsTask, route: List[int], node_id: int, position: int) -> bool:
    if position < 0 or position > len(route):
        return False
    if node_id not in _valid_node_ids(task) or node_id in route:
        return False
    if task.problem_type.upper() != "PDPTW":
        state = _build_vrptw_route_state(task, route)
        return state is not None and _is_vrptw_insertion_feasible(task, route, state, node_id, position)
    return _is_sequence_feasible(task, _route_with_insertion(route, node_id, position), known_unique=True)


def are_routes_feasible(task: LogisticsTask, routes: List[List[int]], enforce_vehicle_limit: bool = True) -> bool:
    if not all(is_route_feasible(task, route) for route in routes):
        return False
    candidate = RouteSolution(solution_id="candidate_feasibility", routes=[route[:] for route in routes])
    result = verify_solution(task, candidate)
    if result.feasible:
        return True
    if not enforce_vehicle_limit:
        return all(violation["type"] == "vehicle_count" for violation in result.violations)
    return False


def best_pair_insertion(
    task: LogisticsTask,
    routes: List[List[int]],
    pickup_id: int,
    delivery_id: int,
) -> tuple[int, int, int, float] | None:
    best: tuple[int, int, int, float] | None = None
    for route_index, route in enumerate(routes):
        before = route_distance(task, route)
        for pickup_position in range(len(route) + 1):
            route_with_pickup = route[:pickup_position] + [pickup_id] + route[pickup_position:]
            for delivery_position in range(pickup_position + 1, len(route_with_pickup) + 1):
                candidate = route_with_pickup[:delivery_position] + [delivery_id] + route_with_pickup[delivery_position:]
                if is_route_feasible(task, candidate):
                    delta = route_distance(task, candidate) - before
                    if best is None or delta < best[3]:
                        best = (route_index, pickup_position, delivery_position, delta)
    return best


def insertion_delta(task: LogisticsTask, route: List[int], node_id: int, position: int) -> float:
    previous_id = task.depot.node_id if position == 0 else route[position - 1]
    next_id = task.depot.node_id if position == len(route) else route[position]
    return (
        travel_distance(task, previous_id, node_id)
        + travel_distance(task, node_id, next_id)
        - travel_distance(task, previous_id, next_id)
    )


def insertion_options(task: LogisticsTask, routes: List[List[int]], node_id: int) -> list[tuple[int, int, float]]:
    options: list[tuple[int, int, float]] = []
    if node_id not in _valid_node_ids(task):
        return options
    for route_index, route in enumerate(routes):
        if node_id in route:
            continue
        state = _build_vrptw_route_state(task, route) if task.problem_type.upper() != "PDPTW" else None
        for position in range(len(route) + 1):
            if state is not None:
                feasible = _is_vrptw_insertion_feasible(task, route, state, node_id, position)
            else:
                feasible = is_insertion_feasible(task, route, node_id, position)
            if feasible:
                delta = insertion_delta(task, route, node_id, position)
                options.append((route_index, position, delta))
    return sorted(options, key=lambda item: item[2])


def best_insertion(task: LogisticsTask, routes: List[List[int]], node_id: int) -> tuple[int, int, float] | None:
    best: tuple[int, int, float] | None = None
    for route_index, position, delta in insertion_options(task, routes, node_id):
        if best is None or delta < best[2]:
            best = (route_index, position, delta)
    return best


def finish_solution(task: LogisticsTask, solution: RouteSolution) -> RouteSolution:
    verify_solution(task, solution)
    return solution
