from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_ablation.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from data_parser import parse_solomon
from fast_thinking import greedy_insertion, nearest_neighbor, regret_insertion
from reflective_optimization.relocate_search import relocate_search
from reflective_optimization.repair_insertion import repair_insertion
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from reflective_optimization.two_opt import two_opt
from verification.route_feasibility import verify_solution


GENERATORS = {
    "nearest_neighbor": nearest_neighbor,
    "greedy_insertion": greedy_insertion,
    "regret_insertion": regret_insertion,
}


def run_instance(instance_path: Path) -> list[dict[str, str]]:
    task = parse_solomon(instance_path)
    rows: list[dict[str, str]] = []
    for generator_name, generator in GENERATORS.items():
        fast_only = generator(task)
        fast_result = verify_solution(task, fast_only)
        variants = [("fast_only", fast_only, fast_result)]

        repaired = repair_insertion(task, fast_only, fast_result)
        variants.append(("fast_repair", repaired, verify_solution(task, repaired)))

        merged = route_merge(task, repaired)
        variants.append(("fast_repair_merge", merged, verify_solution(task, merged)))

        eliminated = route_elimination(task, merged)
        variants.append(("fast_repair_merge_elim", eliminated, verify_solution(task, eliminated)))

        relocated = relocate_search(task, eliminated)
        full = two_opt(task, relocated)
        variants.append(("full_ftv", full, verify_solution(task, full)))

        for variant_name, solution, result in variants:
            rows.append(
                {
                    "dataset": task.task_id,
                    "generator": generator_name,
                    "variant": variant_name,
                    "vehicles": result.vehicle_number,
                    "distance": f"{result.total_distance:.6f}",
                    "feasible": result.feasible,
                    "violations": len(result.violations),
                    "base_runtime": f"{fast_only.runtime:.6f}",
                }
            )
    return rows


def _run_one(path_text: str) -> tuple[str, list[dict[str, str]]]:
    path = Path(path_text)
    return path.name, run_instance(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FTV ablation on Solomon instances.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--instances", nargs="*", default=[])
    parser.add_argument("--output", type=Path, default=Path("results/tables/solomon_ablation_selected.csv"))
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    if args.instances:
        instance_paths = [args.instance_dir / name for name in args.instances]
    else:
        instance_paths = sorted(args.instance_dir.glob("*.txt"))
    missing = [str(path) for path in instance_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing instances: {missing}")
    if not instance_paths:
        raise FileNotFoundError(f"No instances were requested from {args.instance_dir}")

    rows: list[dict[str, str]] = []
    if args.workers <= 1:
        for index, path in enumerate(instance_paths, start=1):
            print(f"[{index}/{len(instance_paths)}] {path.name}", flush=True)
            rows.extend(run_instance(path))
    else:
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run_one, str(path)) for path in instance_paths]
            for future in as_completed(futures):
                name, part_rows = future.result()
                completed += 1
                print(f"[{completed}/{len(instance_paths)}] {name}", flush=True)
                rows.extend(part_rows)

    rows.sort(key=lambda row: (row["dataset"], row["generator"], row["variant"]))
    if not rows:
        raise ValueError("No ablation result rows were produced")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
