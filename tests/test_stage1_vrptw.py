from __future__ import annotations

from pathlib import Path

import pytest

from data_parser import parse_solomon
from distance_matrix import route_distance
from fast_thinking import greedy_insertion, nearest_neighbor, regret_insertion
from fast_thinking.common import insertion_delta, insertion_options, is_insertion_feasible, is_route_feasible
from reflective_optimization.repair_insertion import repair_insertion
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from route_solution import RouteSolution
from verification.route_feasibility import verify_solution


SAMPLE_SOLOMON = """C101

VEHICLE
NUMBER     CAPACITY
  3         50

CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
    0      0        0        0       0           500       0
    1      10       0        10      0           200       10
    2      20       0        10      0           220       10
    3      0        10       10      0           220       10
    4      0        20       10      0           260       10
"""

CAPACITY_DISTRIBUTION_SOLOMON = """C102

VEHICLE
NUMBER     CAPACITY
  2         30

CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
    0      0        0        0       0           1000      0
    1      10       0        10      0           1000      0
    2      20       0        10      0           1000      0
    3      0        10       10      0           1000      0
    4      0        20       10      0           1000      0
    5      10       10       10      0           1000      0
    6      20       20       10      0           1000      0
"""


def write_sample(tmp_path: Path) -> Path:
    path = tmp_path / "C101_sample.txt"
    path.write_text(SAMPLE_SOLOMON, encoding="utf-8")
    return path


def test_parse_solomon_and_distance(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    assert task.task_id == "C101_sample"
    assert task.vehicles == 3
    assert task.capacity == 50
    assert len(task.nodes) == 4
    assert route_distance(task, [1, 2]) == 40.0


def test_verify_feasible_solution(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    solution = nearest_neighbor(task)
    result = verify_solution(task, solution)
    assert result.feasible
    assert result.vehicle_number <= task.vehicles
    assert sorted(solution.served_nodes()) == [1, 2, 3, 4]


def test_generators_cover_all_nodes(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    for generator in (nearest_neighbor, greedy_insertion, regret_insertion):
        solution = generator(task)
        assert sorted(solution.served_nodes()) == [1, 2, 3, 4]
        assert verify_solution(task, solution).feasible


def test_repair_removes_duplicates_and_inserts_missing(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    broken = nearest_neighbor(task)
    broken.routes = [[1, 1], [3]]
    repaired = repair_insertion(task, broken)
    result = verify_solution(task, repaired)
    assert sorted(repaired.served_nodes()) == [1, 2, 3, 4]
    assert result.feasible


def test_route_merge_reduces_vehicle_count_when_feasible(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    solution = nearest_neighbor(task)
    solution.routes = [[1], [2], [3], [4]]
    merged = route_merge(task, solution)
    result = verify_solution(task, merged)
    assert result.feasible
    assert result.vehicle_number == 1


def test_fast_insertion_helpers_match_full_route_check(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    route = [1, 3]
    node_id = 2
    for position in range(len(route) + 1):
        candidate = route[:position] + [node_id] + route[position:]
        full_delta = route_distance(task, candidate) - route_distance(task, route)
        assert insertion_delta(task, route, node_id, position) == pytest.approx(full_delta)
        assert is_insertion_feasible(task, route, node_id, position) == is_route_feasible(task, candidate)


def test_insertion_options_match_full_scan(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    routes = [[1, 3], [4]]
    node_id = 2
    expected = []
    for route_index, route in enumerate(routes):
        for position in range(len(route) + 1):
            candidate = route[:position] + [node_id] + route[position:]
            if is_route_feasible(task, candidate):
                expected.append((route_index, position, insertion_delta(task, route, node_id, position)))
    actual = insertion_options(task, routes, node_id)
    expected = sorted(expected, key=lambda item: item[2])
    assert [(route_index, position) for route_index, position, _ in actual] == [
        (route_index, position) for route_index, position, _ in expected
    ]
    assert [delta for _, _, delta in actual] == pytest.approx([delta for _, _, delta in expected])


def test_route_merge_can_pass_through_vehicle_count_violations(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    task.vehicles = 1
    solution = RouteSolution(solution_id="too_many_routes", routes=[[1], [2], [3], [4]])
    assert not verify_solution(task, solution).feasible
    merged = route_merge(task, solution)
    result = verify_solution(task, merged)
    assert result.feasible
    assert result.vehicle_number == 1


def test_route_elimination_distributes_source_route_across_targets(tmp_path: Path) -> None:
    path = tmp_path / "C102_capacity_distribution.txt"
    path.write_text(CAPACITY_DISTRIBUTION_SOLOMON, encoding="utf-8")
    task = parse_solomon(path)
    solution = RouteSolution(solution_id="needs_distribution", routes=[[1, 2], [3, 4], [5, 6]])
    assert not verify_solution(task, solution).feasible
    eliminated = route_elimination(task, solution)
    result = verify_solution(task, eliminated)
    assert result.feasible
    assert result.vehicle_number == 2
    assert sorted(eliminated.served_nodes()) == [1, 2, 3, 4, 5, 6]


def test_verify_unknown_node_returns_violation(tmp_path: Path) -> None:
    task = parse_solomon(write_sample(tmp_path))
    result = verify_solution(task, RouteSolution(solution_id="bad", routes=[[99]]))
    assert not result.feasible
    assert any(violation["type"] == "unknown_node" and violation["node_id"] == 99 for violation in result.violations)
