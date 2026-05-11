from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_advanced_alns_all.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from experiments.run_alns_param_sweep import CONFIGS, run_best_of_seeds


def _worker(payload: tuple[str, str, tuple[int, ...], float]) -> tuple[str, list[dict[str, str]]]:
    instance_path, config_name, seeds, time_limit = payload
    return Path(instance_path).name, run_best_of_seeds(Path(instance_path), config_name, list(seeds), time_limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run advanced ALNS on all Solomon instances.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--instances", nargs="*", default=[])
    parser.add_argument("--config", choices=sorted(CONFIGS), default="balanced")
    parser.add_argument("--seed", type=int, default=None, help="Backward-compatible single-seed shortcut.")
    parser.add_argument("--seeds", nargs="*", type=int, default=None)
    parser.add_argument("--time-limit", type=float, default=25.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("results/tables/advanced_alns_all.csv"))
    args = parser.parse_args()

    if args.seeds is not None:
        seeds = args.seeds
    elif args.seed is not None:
        seeds = [args.seed]
    else:
        seeds = [42]
    if not seeds:
        raise ValueError("At least one ALNS seed is required")

    if args.instances:
        paths = [args.instance_dir / name for name in args.instances]
    else:
        paths = sorted(args.instance_dir.glob("*.txt"))
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing instances: {missing}")
    if not paths:
        raise FileNotFoundError(f"No .txt instances found in {args.instance_dir}")
    tasks = [(str(path), args.config, tuple(seeds), args.time_limit) for path in paths]
    rows: list[dict[str, str]] = []
    completed = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_worker, task) for task in tasks]
        for future in as_completed(futures):
            name, part = future.result()
            completed += 1
            print(f"[{completed}/{len(tasks)}] {name}", flush=True)
            rows.extend(part)

    rows.sort(key=lambda row: row["dataset"])
    if not rows:
        raise ValueError("No advanced ALNS result rows were produced")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
