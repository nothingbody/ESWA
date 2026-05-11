from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_solomon.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from pathlib import Path

from data_parser import parse_solomon
from fast_thinking import greedy_insertion, nearest_neighbor, regret_insertion
from reflective_optimization.repair_insertion import repair_insertion
from reflective_optimization.relocate_search import relocate_search
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from reflective_optimization.two_opt import two_opt
from verification.route_feasibility import verify_solution


def run(
    instance_path: Path,
    output_path: Path,
    use_relocate: bool = True,
    use_two_opt: bool = True,
) -> None:
    task = parse_solomon(instance_path)
    methods = [nearest_neighbor, greedy_insertion, regret_insertion]
    rows = []
    for method in methods:
        solution = method(task)
        initial_result = verify_solution(task, solution)
        repaired = repair_insertion(task, solution, initial_result)
        merged = route_merge(task, repaired)
        eliminated = route_elimination(task, merged)
        optimized = relocate_search(task, eliminated) if use_relocate else eliminated
        improved = two_opt(task, optimized) if use_two_opt else optimized
        result = verify_solution(task, improved)
        rows.append(
            {
                "dataset": task.task_id,
                "method": method.__name__,
                "initial_vehicles": solution.vehicle_number,
                "initial_distance": f"{solution.total_distance:.6f}",
                "vehicles": result.vehicle_number,
                "distance": f"{result.total_distance:.6f}",
                "feasible": result.feasible,
                "violations": len(result.violations),
                "runtime": f"{solution.runtime:.6f}",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FTV stage-1 Solomon experiment.")
    parser.add_argument("instance", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/tables/solomon_stage1.csv"))
    parser.add_argument("--skip-relocate", action="store_true")
    parser.add_argument("--skip-two-opt", action="store_true")
    args = parser.parse_args()
    run(
        args.instance,
        args.output,
        use_relocate=not args.skip_relocate,
        use_two_opt=not args.skip_two_opt,
    )


if __name__ == "__main__":
    main()
