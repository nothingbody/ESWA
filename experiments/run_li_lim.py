from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_li_lim.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from pathlib import Path

from data_parser import parse_li_lim
from fast_thinking.pair_insertion import greedy_pair_insertion
from reflective_optimization.advanced_alns import AdvancedAlnsConfig, advanced_alns
from reflective_optimization.pair_alns import PairAlnsConfig, pair_alns
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from verification.route_feasibility import verify_solution


def _is_feasible_value(value: object) -> bool:
    return value is True or str(value).lower() == "true"


def _row_key(row: dict[str, object]) -> tuple[int, int, float, int]:
    feasible_rank = 0 if _is_feasible_value(row["feasible"]) else 1
    return (
        feasible_rank,
        int(row["vehicles"]),
        float(row["distance"]),
        int(row["violations"]),
    )


def run(
    instance_path: Path,
    output_path: Path,
    use_pair_alns: bool = True,
    pair_seeds: list[int] | None = None,
    use_ordinary_alns: bool = False,
) -> None:
    seeds = [42] if pair_seeds is None else pair_seeds
    if use_pair_alns and not seeds:
        raise ValueError("At least one Pair ALNS seed is required")
    task = parse_li_lim(instance_path)
    solution = greedy_pair_insertion(task)
    merged = route_elimination(task, route_merge(task, solution))
    result = verify_solution(task, merged)
    rows = [
        {
            "dataset": task.task_id,
            "method": "greedy_pair_insertion",
            "initial_vehicles": solution.vehicle_number,
            "initial_distance": f"{solution.total_distance:.6f}",
            "vehicles": result.vehicle_number,
            "distance": f"{result.total_distance:.6f}",
            "feasible": result.feasible,
            "violations": len(result.violations),
            "runtime": f"{solution.runtime:.6f}",
            "pairs": len(task.pickup_delivery_pairs),
            "selected_seed": "",
            "seed_pool": "",
        }
    ]
    if use_ordinary_alns:
        candidates = []
        seed_pool = ",".join(str(seed) for seed in seeds)
        total_runtime = merged.runtime
        for seed in seeds:
            ordinary = advanced_alns(
                task,
                merged,
                AdvancedAlnsConfig(iterations=120, time_limit=20.0, seed=seed),
            )
            total_runtime += max(0.0, ordinary.runtime - merged.runtime)
            ordinary_result = verify_solution(task, ordinary)
            candidates.append(
                {
                    "dataset": task.task_id,
                    "method": "greedy_pair_insertion+ordinary_alns",
                    "initial_vehicles": result.vehicle_number,
                    "initial_distance": f"{result.total_distance:.6f}",
                    "vehicles": ordinary_result.vehicle_number,
                    "distance": f"{ordinary_result.total_distance:.6f}",
                    "feasible": ordinary_result.feasible,
                    "violations": len(ordinary_result.violations),
                    "runtime": f"{ordinary.runtime:.6f}",
                    "pairs": len(task.pickup_delivery_pairs),
                    "selected_seed": seed,
                    "seed_pool": seed_pool,
                }
            )
        best = dict(min(candidates, key=_row_key))
        best["runtime"] = f"{total_runtime:.6f}"
        rows.append({key: best[key] for key in rows[0]})
    if use_pair_alns:
        candidates: list[dict[str, object]] = []
        total_runtime = merged.runtime
        seed_pool = ",".join(str(seed) for seed in seeds)
        for seed in seeds:
            improved = pair_alns(task, merged, PairAlnsConfig(iterations=120, time_limit=20.0, seed=seed))
            total_runtime += max(0.0, improved.runtime - merged.runtime)
            improved_result = verify_solution(task, improved)
            candidates.append(
                {
                    "dataset": task.task_id,
                    "method": "greedy_pair_insertion+pair_alns",
                    "initial_vehicles": result.vehicle_number,
                    "initial_distance": f"{result.total_distance:.6f}",
                    "vehicles": improved_result.vehicle_number,
                    "distance": f"{improved_result.total_distance:.6f}",
                    "feasible": improved_result.feasible,
                    "violations": len(improved_result.violations),
                    "runtime": f"{improved.runtime:.6f}",
                    "pairs": len(task.pickup_delivery_pairs),
                    "selected_seed": seed,
                    "seed_pool": seed_pool,
                }
            )
        best = dict(min(candidates, key=_row_key))
        best["runtime"] = f"{total_runtime:.6f}"
        rows.append(
            {
                key: best[key]
                for key in rows[0]
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FTV stage-1 Li & Lim PDPTW experiment.")
    parser.add_argument("instance", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/tables/li_lim_stage1.csv"))
    parser.add_argument("--skip-pair-alns", action="store_true")
    parser.add_argument("--include-ordinary-alns", action="store_true")
    parser.add_argument("--pair-seeds", nargs="*", type=int, default=[42])
    args = parser.parse_args()
    run(
        args.instance,
        args.output,
        use_pair_alns=not args.skip_pair_alns,
        pair_seeds=args.pair_seeds,
        use_ordinary_alns=args.include_ordinary_alns,
    )


if __name__ == "__main__":
    main()
