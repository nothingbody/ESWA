from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_solomon_alns.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from data_parser import parse_solomon
from fast_thinking import greedy_insertion, nearest_neighbor, regret_insertion
from reflective_optimization.basic_alns import AlnsConfig, basic_alns
from reflective_optimization.repair_insertion import repair_insertion
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from verification.route_feasibility import verify_solution


GENERATORS = {
    "nearest_neighbor": nearest_neighbor,
    "greedy_insertion": greedy_insertion,
    "regret_insertion": regret_insertion,
}


def run_one(instance_path: Path, iterations: int, time_limit: float) -> list[dict[str, str]]:
    task = parse_solomon(instance_path)
    rows: list[dict[str, str]] = []
    for name, generator in GENERATORS.items():
        initial = generator(task)
        base = route_elimination(task, route_merge(task, repair_insertion(task, initial, verify_solution(task, initial))))
        base_result = verify_solution(task, base)
        alns = basic_alns(task, base, AlnsConfig(iterations=iterations, time_limit=time_limit, seed=42))
        alns_result = verify_solution(task, alns)
        rows.append(
            {
                "dataset": task.task_id,
                "method": f"{name}+basic_alns",
                "base_vehicles": base_result.vehicle_number,
                "base_distance": f"{base_result.total_distance:.6f}",
                "vehicles": alns_result.vehicle_number,
                "distance": f"{alns_result.total_distance:.6f}",
                "feasible": alns_result.feasible,
                "violations": len(alns_result.violations),
                "runtime": f"{alns.runtime:.6f}",
            }
        )
    return rows


def _worker(payload: tuple[str, int, float]) -> tuple[str, list[dict[str, str]]]:
    path_text, iterations, time_limit = payload
    path = Path(path_text)
    return path.name, run_one(path, iterations, time_limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Solomon Basic ALNS enhancement.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--instances", nargs="*", default=[])
    parser.add_argument("--iterations", type=int, default=400)
    parser.add_argument("--time-limit", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("results/tables/solomon_alns_selected.csv"))
    args = parser.parse_args()

    if args.instances:
        paths = [args.instance_dir / name for name in args.instances]
    else:
        paths = sorted(args.instance_dir.glob("*.txt"))
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing instances: {missing}")
    if not paths:
        raise FileNotFoundError(f"No .txt instances found in {args.instance_dir}")

    rows: list[dict[str, str]] = []
    if args.workers <= 1:
        for index, path in enumerate(paths, start=1):
            print(f"[{index}/{len(paths)}] {path.name}", flush=True)
            rows.extend(run_one(path, args.iterations, args.time_limit))
    else:
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_worker, (str(path), args.iterations, args.time_limit)) for path in paths]
            for future in as_completed(futures):
                name, part = future.result()
                completed += 1
                print(f"[{completed}/{len(paths)}] {name}", flush=True)
                rows.extend(part)

    rows.sort(key=lambda row: (row["dataset"], row["method"]))
    if not rows:
        raise ValueError("No Solomon ALNS result rows were produced")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
