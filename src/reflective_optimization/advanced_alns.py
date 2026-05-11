from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

from distance_matrix import route_distance, solution_distance, travel_distance
from fast_thinking.common import are_routes_feasible, best_insertion, insertion_options
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import verify_solution


@dataclass
class AdvancedAlnsConfig:
    iterations: int = 1200
    removal_fraction: float = 0.18
    seed: int = 42
    time_limit: float = 30.0
    start_temperature: float = 80.0
    cooling_rate: float = 0.992
    route_removal_probability: float = 0.20
    route_elimination_interval: int = 25
    adaptive_reaction: float = 0.20


def _clean(routes: list[list[int]]) -> list[list[int]]:
    return [route for route in routes if route]


def _objective(task: LogisticsTask, routes: list[list[int]]) -> tuple[int, float]:
    return len(_clean(routes)), solution_distance(task, _clean(routes))


def _score(task: LogisticsTask, routes: list[list[int]]) -> float:
    vehicles, distance = _objective(task, routes)
    return vehicles * 1_000_000.0 + distance


def _is_better(task: LogisticsTask, candidate: list[list[int]], incumbent: list[list[int]]) -> bool:
    return _objective(task, candidate) < _objective(task, incumbent)


def _random_removal(routes: list[list[int]], rng: random.Random, count: int) -> tuple[list[list[int]], list[int]]:
    nodes = [node_id for route in routes for node_id in route]
    removed = set(rng.sample(nodes, min(count, len(nodes))))
    return _clean([[node_id for node_id in route if node_id not in removed] for route in routes]), list(removed)


def _worst_removal(task: LogisticsTask, routes: list[list[int]], count: int) -> tuple[list[list[int]], list[int]]:
    contributions: list[tuple[float, int]] = []
    for route in routes:
        base = route_distance(task, route)
        for index, node_id in enumerate(route):
            candidate = route[:index] + route[index + 1 :]
            contributions.append((base - route_distance(task, candidate), node_id))
    contributions.sort(reverse=True)
    removed = {node_id for _, node_id in contributions[:count]}
    return _clean([[node_id for node_id in route if node_id not in removed] for route in routes]), list(removed)


def _related_removal(task: LogisticsTask, routes: list[list[int]], rng: random.Random, count: int) -> tuple[list[list[int]], list[int]]:
    nodes = [node_id for route in routes for node_id in route]
    seed = rng.choice(nodes)
    seed_node = task.node_by_id(seed)
    ranked = []
    for node_id in nodes:
        node = task.node_by_id(node_id)
        relatedness = travel_distance(task, seed, node_id) + 0.05 * abs(seed_node.ready_time - node.ready_time)
        ranked.append((relatedness, node_id))
    ranked.sort()
    removed = {node_id for _, node_id in ranked[:count]}
    return _clean([[node_id for node_id in route if node_id not in removed] for route in routes]), list(removed)


def _route_removal(task: LogisticsTask, routes: list[list[int]], rng: random.Random, count: int) -> tuple[list[list[int]], list[int]]:
    if len(routes) <= 1:
        return _random_removal(routes, rng, count)
    candidates = sorted(range(len(routes)), key=lambda index: (len(routes[index]), route_distance(task, routes[index])))
    removed: list[int] = []
    removed_routes: set[int] = set()
    for route_index in candidates:
        removed_routes.add(route_index)
        removed.extend(routes[route_index])
        if len(removed) >= count:
            break
    kept = [route[:] for index, route in enumerate(routes) if index not in removed_routes]
    return _clean(kept), removed


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
    nodes = [node_id for route in routes for node_id in route]
    count = max(1, min(len(nodes) - 1, int(len(nodes) * removal_fraction)))
    if operator_name == "route":
        return _route_removal(task, routes, rng, count)
    if operator_name == "worst":
        return _worst_removal(task, routes, count)
    if operator_name == "related":
        return _related_removal(task, routes, rng, count)
    return _random_removal(routes, rng, count)


def _regret_repair(task: LogisticsTask, routes: list[list[int]], removed: list[int]) -> list[list[int]]:
    repaired = [route[:] for route in routes]
    pending = set(removed)
    while pending:
        best_choice: tuple[int, int | None, int | None, float] | None = None
        for node_id in sorted(pending):
            options = insertion_options(task, repaired, node_id)
            if options:
                best = options[0]
                second = options[1][2] if len(options) > 1 else best[2] + 10_000.0
                regret = second - best[2]
                if best_choice is None or regret > best_choice[3]:
                    best_choice = (node_id, best[0], best[1], regret)
        if best_choice is None:
            node_id = min(pending, key=lambda item: task.node_by_id(item).due_time)
            repaired.append([node_id])
            pending.remove(node_id)
        else:
            node_id, route_index, position, _ = best_choice
            assert route_index is not None and position is not None
            repaired[route_index].insert(position, node_id)
            pending.remove(node_id)
    return _clean(repaired)


def _greedy_repair(task: LogisticsTask, routes: list[list[int]], removed: list[int]) -> list[list[int]]:
    repaired = [route[:] for route in routes]
    for node_id in sorted(removed, key=lambda item: task.node_by_id(item).due_time):
        insertion = best_insertion(task, repaired, node_id)
        if insertion is None:
            repaired.append([node_id])
        else:
            route_index, position, _ = insertion
            repaired[route_index].insert(position, node_id)
    return _clean(repaired)


def advanced_alns(task: LogisticsTask, solution: RouteSolution, config: AdvancedAlnsConfig | None = None) -> RouteSolution:
    config = config or AdvancedAlnsConfig()
    rng = random.Random(config.seed)
    started = time.perf_counter()
    current = route_elimination(task, route_merge(task, solution)).routes
    best = [route[:] for route in current]
    temperature = config.start_temperature
    removal_weights = {
        "route": max(0.05, config.route_removal_probability),
        "worst": 0.30,
        "related": 0.30,
        "random": 0.20,
    }
    repair_weights = {"regret": 0.55, "greedy": 0.45}

    for iteration in range(config.iterations):
        if config.time_limit > 0 and time.perf_counter() - started >= config.time_limit:
            break
        removal_operator = _weighted_choice(rng, removal_weights)
        repair_operator = _weighted_choice(rng, repair_weights)
        previous_current = [route[:] for route in current]
        previous_best = [route[:] for route in best]
        destroyed, removed = _destroy_with_operator(
            task,
            current,
            rng,
            config.removal_fraction,
            removal_operator,
        )
        if repair_operator == "regret":
            candidate = _regret_repair(task, destroyed, removed)
        else:
            candidate = _greedy_repair(task, destroyed, removed)
        candidate_solution = route_merge(task, RouteSolution(solution_id="candidate", routes=candidate))
        if config.route_elimination_interval > 0 and iteration % config.route_elimination_interval == 0:
            candidate_solution = route_elimination(task, candidate_solution)
        candidate = candidate_solution.routes
        if not are_routes_feasible(task, candidate, enforce_vehicle_limit=False):
            _update_weight(removal_weights, removal_operator, 0.10, config.adaptive_reaction)
            _update_weight(repair_weights, repair_operator, 0.10, config.adaptive_reaction)
            continue

        delta = _score(task, candidate) - _score(task, current)
        accepted = delta < 0 or rng.random() < math.exp(-delta / max(temperature, 1e-9))
        if accepted:
            current = [route[:] for route in candidate]
        reward = 0.50
        if accepted:
            reward = 1.00
        if _is_better(task, candidate, previous_current):
            reward = 2.00
        if _is_better(task, current, best):
            best = [route[:] for route in current]
        if _is_better(task, best, previous_best):
            reward = 5.00
        _update_weight(removal_weights, removal_operator, reward, config.adaptive_reaction)
        _update_weight(repair_weights, repair_operator, reward, config.adaptive_reaction)
        temperature *= config.cooling_rate

    best = route_elimination(task, RouteSolution(solution_id="best_candidate", routes=best)).routes

    improved = RouteSolution(
        solution_id=f"{solution.solution_id}:advanced_alns",
        routes=best,
        runtime=solution.runtime + (time.perf_counter() - started),
        generator_name=f"{solution.generator_name}+advanced_alns",
    )
    verify_solution(task, improved)
    return improved
