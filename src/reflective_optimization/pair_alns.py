from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

from distance_matrix import route_distance, solution_distance
from fast_thinking.common import are_routes_feasible, best_pair_insertion
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


@dataclass
class PairAlnsConfig:
    iterations: int = 160
    removal_fraction: float = 0.18
    seed: int = 42
    time_limit: float = 20.0
    start_temperature: float = 30.0
    cooling_rate: float = 0.990
    route_removal_probability: float = 0.25
    route_elimination_interval: int = 8
    adaptive_reaction: float = 0.20


def _clean(routes: list[list[int]]) -> list[list[int]]:
    return [route for route in routes if route]


def _objective(task: LogisticsTask, routes: list[list[int]]) -> tuple[int, float]:
    cleaned = _clean(routes)
    return len(cleaned), solution_distance(task, cleaned)


def _score(task: LogisticsTask, routes: list[list[int]]) -> float:
    vehicles, distance = _objective(task, routes)
    return vehicles * 1_000_000.0 + distance


def _pairs_in_routes(task: LogisticsTask, routes: list[list[int]]) -> list[int]:
    present = {node_id for route in routes for node_id in route}
    return [
        pickup_id
        for pickup_id, delivery_id in task.pickup_delivery_pairs.items()
        if pickup_id in present and delivery_id in present
    ]


def _remove_pair_nodes(
    task: LogisticsTask,
    routes: list[list[int]],
    pickup_ids: set[int],
) -> tuple[list[list[int]], list[int]]:
    node_ids = set(pickup_ids)
    for pickup_id in pickup_ids:
        node_ids.add(task.pickup_delivery_pairs[pickup_id])
    kept = [[node_id for node_id in route if node_id not in node_ids] for route in routes]
    return _clean(kept), sorted(pickup_ids)


def _random_pair_removal(
    task: LogisticsTask,
    routes: list[list[int]],
    rng: random.Random,
    count: int,
) -> tuple[list[list[int]], list[int]]:
    pairs = _pairs_in_routes(task, routes)
    removed = set(rng.sample(pairs, min(count, len(pairs))))
    return _remove_pair_nodes(task, routes, removed)


def _route_pair_removal(
    task: LogisticsTask,
    routes: list[list[int]],
    rng: random.Random,
    count: int,
) -> tuple[list[list[int]], list[int]]:
    if len(routes) <= 1:
        return _random_pair_removal(task, routes, rng, count)
    route_indexes = sorted(
        range(len(routes)),
        key=lambda index: (len(routes[index]), route_distance(task, routes[index])),
    )
    removed: set[int] = set()
    for route_index in route_indexes:
        route_nodes = set(routes[route_index])
        for pickup_id, delivery_id in task.pickup_delivery_pairs.items():
            if pickup_id in route_nodes and delivery_id in route_nodes:
                removed.add(pickup_id)
        if len(removed) >= count:
            break
    return _remove_pair_nodes(task, routes, removed)


def _worst_pair_removal(
    task: LogisticsTask,
    routes: list[list[int]],
    count: int,
) -> tuple[list[list[int]], list[int]]:
    contributions: list[tuple[float, int]] = []
    for route in routes:
        base = route_distance(task, route)
        route_nodes = set(route)
        for pickup_id, delivery_id in task.pickup_delivery_pairs.items():
            if pickup_id not in route_nodes or delivery_id not in route_nodes:
                continue
            candidate = [node_id for node_id in route if node_id not in {pickup_id, delivery_id}]
            contributions.append((base - route_distance(task, candidate), pickup_id))
    contributions.sort(reverse=True)
    removed = {pickup_id for _, pickup_id in contributions[:count]}
    return _remove_pair_nodes(task, routes, removed)


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    total = sum(weights.values())
    threshold = rng.random() * total
    cumulative = 0.0
    for name, weight in weights.items():
        cumulative += weight
        if cumulative >= threshold:
            return name
    return next(reversed(weights))


def _update_weight(weights: dict[str, float], name: str, reward: float, reaction: float) -> None:
    weights[name] = max(0.05, (1.0 - reaction) * weights[name] + reaction * reward)


def _destroy_with_operator(
    task: LogisticsTask,
    routes: list[list[int]],
    rng: random.Random,
    removal_fraction: float,
    operator_name: str,
) -> tuple[list[list[int]], list[int]]:
    pairs = _pairs_in_routes(task, routes)
    if not pairs:
        return routes, []
    count = max(1, min(len(pairs), int(len(pairs) * removal_fraction)))
    if operator_name == "route":
        return _route_pair_removal(task, routes, rng, count)
    if operator_name == "worst":
        return _worst_pair_removal(task, routes, count)
    return _random_pair_removal(task, routes, rng, count)


def _repair_pairs(task: LogisticsTask, routes: list[list[int]], removed_pickups: list[int]) -> list[list[int]]:
    repaired = [route[:] for route in routes]
    pending = set(removed_pickups)
    while pending:
        best_choice: tuple[int, int | None, int | None, int | None, float] | None = None
        for pickup_id in sorted(pending):
            delivery_id = task.pickup_delivery_pairs[pickup_id]
            insertion = best_pair_insertion(task, repaired, pickup_id, delivery_id)
            if insertion is None:
                continue
            route_index, pickup_position, delivery_position, delta = insertion
            if best_choice is None or delta < best_choice[4]:
                best_choice = (pickup_id, route_index, pickup_position, delivery_position, delta)
        if best_choice is None:
            pickup_id = min(pending, key=lambda item: task.node_by_id(item).due_time)
            repaired.append([pickup_id, task.pickup_delivery_pairs[pickup_id]])
            pending.remove(pickup_id)
        else:
            pickup_id, route_index, pickup_position, delivery_position, _ = best_choice
            assert route_index is not None and pickup_position is not None and delivery_position is not None
            delivery_id = task.pickup_delivery_pairs[pickup_id]
            route = repaired[route_index]
            route.insert(pickup_position, pickup_id)
            route.insert(delivery_position, delivery_id)
            pending.remove(pickup_id)
    return _clean(repaired)


def pair_alns(task: LogisticsTask, solution: RouteSolution, config: PairAlnsConfig | None = None) -> RouteSolution:
    if task.problem_type.upper() != "PDPTW":
        raise ValueError("pair_alns requires a PDPTW task")
    config = config or PairAlnsConfig()
    rng = random.Random(config.seed)
    started = time.perf_counter()
    current = route_elimination(task, route_merge(task, solution)).routes
    best = [route[:] for route in current]
    temperature = config.start_temperature
    removal_weights = {
        "route": max(0.05, config.route_removal_probability),
        "worst": 0.35,
        "random": 0.40,
    }

    for iteration in range(config.iterations):
        if config.time_limit > 0 and time.perf_counter() - started >= config.time_limit:
            break
        removal_operator = _weighted_choice(rng, removal_weights)
        previous_current = [route[:] for route in current]
        previous_best = [route[:] for route in best]
        destroyed, removed_pickups = _destroy_with_operator(
            task,
            current,
            rng,
            config.removal_fraction,
            removal_operator,
        )
        if not removed_pickups:
            _update_weight(removal_weights, removal_operator, 0.10, config.adaptive_reaction)
            continue
        candidate = _repair_pairs(task, destroyed, removed_pickups)
        candidate_solution = route_merge(task, RouteSolution(solution_id="candidate", routes=candidate))
        if config.route_elimination_interval > 0 and iteration % config.route_elimination_interval == 0:
            candidate_solution = route_elimination(task, candidate_solution)
        candidate = candidate_solution.routes
        if not are_routes_feasible(task, candidate, enforce_vehicle_limit=False):
            _update_weight(removal_weights, removal_operator, 0.10, config.adaptive_reaction)
            continue

        delta = _score(task, candidate) - _score(task, current)
        accepted = delta < 0 or rng.random() < math.exp(-delta / max(temperature, 1e-9))
        if accepted:
            current = [route[:] for route in candidate]
        reward = 0.50
        if accepted:
            reward = 1.00
        if _objective(task, candidate) < _objective(task, previous_current):
            reward = 2.00
        if _objective(task, current) < _objective(task, best):
            best = [route[:] for route in current]
        if _objective(task, best) < _objective(task, previous_best):
            reward = 5.00
        _update_weight(removal_weights, removal_operator, reward, config.adaptive_reaction)
        temperature *= config.cooling_rate

    best = route_elimination(task, RouteSolution(solution_id="best_candidate", routes=best)).routes

    improved = RouteSolution(
        solution_id=f"{solution.solution_id}:pair_alns",
        routes=best,
        runtime=solution.runtime + (time.perf_counter() - started),
        generator_name=f"{solution.generator_name}+pair_alns",
    )
    verify_solution(task, improved)
    return improved
