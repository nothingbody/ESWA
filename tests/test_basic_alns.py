from __future__ import annotations

from pathlib import Path

from data_parser import parse_solomon
from fast_thinking import nearest_neighbor
from reflective_optimization.basic_alns import AlnsConfig, basic_alns
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


def test_basic_alns_keeps_solution_feasible(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text(SAMPLE_SOLOMON, encoding="utf-8")
    task = parse_solomon(path)
    solution = nearest_neighbor(task)
    improved = basic_alns(task, solution, AlnsConfig(iterations=20, seed=7))
    result = verify_solution(task, improved)
    assert result.feasible
    assert sorted(improved.served_nodes()) == [1, 2, 3, 4]
