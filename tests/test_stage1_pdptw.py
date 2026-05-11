from __future__ import annotations

from pathlib import Path

from data_parser import parse_li_lim
from fast_thinking.common import are_routes_feasible
from fast_thinking.pair_insertion import greedy_pair_insertion
from reflective_optimization.pair_alns import PairAlnsConfig, pair_alns
from reflective_optimization.route_elimination import route_elimination
from route_solution import RouteSolution
from verification.route_feasibility import verify_solution


SAMPLE_LI_LIM = """2\t10\t1
0\t0\t0\t0\t0\t100\t0\t0\t0
1\t1\t0\t4\t0\t50\t0\t0\t2
2\t2\t0\t-4\t0\t80\t0\t1\t0
3\t0\t1\t3\t0\t50\t0\t0\t4
4\t0\t2\t-3\t0\t80\t0\t3\t0
"""


def write_sample(tmp_path: Path) -> Path:
    path = tmp_path / "lc_sample.txt"
    path.write_text(SAMPLE_LI_LIM, encoding="utf-8")
    return path


def test_parse_li_lim_pairs(tmp_path: Path) -> None:
    task = parse_li_lim(write_sample(tmp_path))
    assert task.problem_type == "PDPTW"
    assert task.vehicles == 2
    assert task.capacity == 10
    assert task.pickup_delivery_pairs == {1: 2, 3: 4}
    assert task.node_by_id(1).node_type == "pickup"
    assert task.node_by_id(2).node_type == "delivery"


def test_pdptw_precedence_and_same_vehicle(tmp_path: Path) -> None:
    task = parse_li_lim(write_sample(tmp_path))
    bad_order = RouteSolution(solution_id="bad_order", routes=[[2, 1], [3, 4]])
    assert not verify_solution(task, bad_order).feasible
    split_pair = RouteSolution(solution_id="split_pair", routes=[[1], [2], [3, 4]])
    assert not verify_solution(task, split_pair).feasible
    crossed_pairs = [[1, 4], [3, 2]]
    assert not are_routes_feasible(task, crossed_pairs)


def test_greedy_pair_insertion_feasible(tmp_path: Path) -> None:
    task = parse_li_lim(write_sample(tmp_path))
    solution = greedy_pair_insertion(task)
    result = verify_solution(task, solution)
    assert result.feasible
    assert sorted(solution.served_nodes()) == [1, 2, 3, 4]


def test_pair_alns_keeps_pdptw_solution_feasible(tmp_path: Path) -> None:
    task = parse_li_lim(write_sample(tmp_path))
    solution = greedy_pair_insertion(task)
    improved = pair_alns(task, solution, PairAlnsConfig(iterations=10, seed=5, time_limit=0))
    result = verify_solution(task, improved)
    assert result.feasible
    assert sorted(improved.served_nodes()) == [1, 2, 3, 4]


def test_route_elimination_keeps_pdptw_pairs_together(tmp_path: Path) -> None:
    task = parse_li_lim(write_sample(tmp_path))
    task.vehicles = 1
    solution = RouteSolution(solution_id="pair_routes", routes=[[1, 2], [3, 4]])
    eliminated = route_elimination(task, solution)
    result = verify_solution(task, eliminated)
    assert result.feasible
    assert result.vehicle_number == 1
    assert sorted(eliminated.served_nodes()) == [1, 2, 3, 4]
