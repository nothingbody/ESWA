from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_alns_param_sweep.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from data_parser import parse_solomon
from fast_thinking import greedy_insertion
from reflective_optimization.advanced_alns import AdvancedAlnsConfig, advanced_alns
from reflective_optimization.repair_insertion import repair_insertion
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from verification.route_feasibility import verify_solution


CONFIGS = {
    "balanced": {"iterations": 900, "removal_fraction": 0.16, "start_temperature": 60.0, "cooling_rate": 0.992, "route_removal_probability": 0.20},
    "aggressive": {"iterations": 1100, "removal_fraction": 0.24, "start_temperature": 120.0, "cooling_rate": 0.994, "route_removal_probability": 0.30},
    "conservative": {"iterations": 800, "removal_fraction": 0.10, "start_temperature": 35.0, "cooling_rate": 0.990, "route_removal_probability": 0.12},
}


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


def run_one(instance_path: Path, config_name: str, seed: int, time_limit: float) -> list[dict[str, str]]:
    task = parse_solomon(instance_path)
    initial = greedy_insertion(task)
    base = route_elimination(task, route_merge(task, repair_insertion(task, initial, verify_solution(task, initial))))
    base_result = verify_solution(task, base)
    params = CONFIGS[config_name]
    config = AdvancedAlnsConfig(seed=seed, time_limit=time_limit, **params)
    improved = advanced_alns(task, base, config)
    result = verify_solution(task, improved)
    return [
        {
            "dataset": task.task_id,
            "method": "greedy_insertion+advanced_alns",
            "config": config_name,
            "seed": seed,
            "base_vehicles": base_result.vehicle_number,
            "base_distance": f"{base_result.total_distance:.6f}",
            "vehicles": result.vehicle_number,
            "distance": f"{result.total_distance:.6f}",
            "feasible": result.feasible,
            "violations": len(result.violations),
            "runtime": f"{improved.runtime:.6f}",
        }
    ]


def run_best_of_seeds(instance_path: Path, config_name: str, seeds: list[int], time_limit: float) -> list[dict[str, str]]:
    if not seeds:
        raise ValueError("At least one ALNS seed is required")
    task = parse_solomon(instance_path)
    initial = greedy_insertion(task)
    base = route_elimination(task, route_merge(task, repair_insertion(task, initial, verify_solution(task, initial))))
    base_result = verify_solution(task, base)
    params = CONFIGS[config_name]
    rows: list[dict[str, object]] = []
    total_runtime = base.runtime
    for seed in seeds:
        config = AdvancedAlnsConfig(seed=seed, time_limit=time_limit, **params)
        improved = advanced_alns(task, base, config)
        total_runtime += max(0.0, improved.runtime - base.runtime)
        result = verify_solution(task, improved)
        rows.append(
            {
                "dataset": task.task_id,
                "method": "greedy_insertion+advanced_alns",
                "config": config_name,
                "seed": seed,
                "selected_seed": seed,
                "seed_pool": ",".join(str(item) for item in seeds),
                "base_vehicles": base_result.vehicle_number,
                "base_distance": f"{base_result.total_distance:.6f}",
                "vehicles": result.vehicle_number,
                "distance": f"{result.total_distance:.6f}",
                "feasible": result.feasible,
                "violations": len(result.violations),
                "runtime": f"{improved.runtime:.6f}",
            }
        )
    best = dict(min(rows, key=_row_key))
    best["runtime"] = f"{total_runtime:.6f}"
    return [best]


def _worker(payload: tuple[str, str, int, float]) -> tuple[str, list[dict[str, str]]]:
    instance_path, config_name, seed, time_limit = payload
    return Path(instance_path).name, run_one(Path(instance_path), config_name, seed, time_limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run advanced ALNS parameter sweep on Solomon.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--instances", nargs="*", default=["C101.txt", "R101.txt", "RC101.txt"])
    parser.add_argument("--configs", nargs="*", default=list(CONFIGS))
    parser.add_argument("--seeds", nargs="*", type=int, default=[11, 23, 37])
    parser.add_argument("--time-limit", type=float, default=20.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("results/tables/advanced_alns_param_sweep.csv"))
    args = parser.parse_args()

    unknown_configs = sorted(set(args.configs) - set(CONFIGS))
    if unknown_configs:
        raise ValueError(f"Unknown configs: {unknown_configs}. Available configs: {sorted(CONFIGS)}")
    paths = [args.instance_dir / name for name in args.instances]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing instances: {missing}")
    tasks = [(str(path), config, seed, args.time_limit) for path in paths for config in args.configs for seed in args.seeds]
    if not tasks:
        raise ValueError("No parameter sweep tasks were requested")
    rows: list[dict[str, str]] = []
    if args.workers <= 1:
        for index, payload in enumerate(tasks, start=1):
            print(f"[{index}/{len(tasks)}] {Path(payload[0]).name} {payload[1]} seed={payload[2]}", flush=True)
            _, part = _worker(payload)
            rows.extend(part)
    else:
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_worker, task) for task in tasks]
            for future in as_completed(futures):
                name, part = future.result()
                completed += 1
                print(f"[{completed}/{len(tasks)}] {name}", flush=True)
                rows.extend(part)

    rows.sort(key=lambda row: (row["dataset"], row["config"], int(row["seed"])))
    if not rows:
        raise ValueError("No parameter sweep result rows were produced")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
