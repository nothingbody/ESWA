from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_li_lim_batch.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from experiments.run_li_lim import run


def _run_one(payload: tuple[str, str, str, str, str]) -> tuple[str, list[dict[str, str]]]:
    instance_path_text, output_path_text, use_pair_alns_text, pair_seeds_text, use_ordinary_alns_text = payload
    instance_path = Path(instance_path_text)
    output_path = Path(output_path_text)
    pair_seeds = [int(seed) for seed in pair_seeds_text.split(",") if seed]
    run(
        instance_path,
        output_path,
        use_pair_alns=use_pair_alns_text == "1",
        pair_seeds=pair_seeds,
        use_ordinary_alns=use_ordinary_alns_text == "1",
    )
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        return instance_path.name, list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FTV stage-1 on Li & Lim PDPTW instances.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/tables/li_lim_stage1_selected.csv"))
    parser.add_argument("--instances", nargs="*", default=[])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--skip-pair-alns", action="store_true")
    parser.add_argument("--include-ordinary-alns", action="store_true")
    parser.add_argument("--pair-seeds", nargs="*", type=int, default=[42])
    args = parser.parse_args()
    if not args.skip_pair_alns and not args.pair_seeds:
        raise ValueError("At least one Pair ALNS seed is required")

    if args.instances:
        instance_paths = [args.instance_dir / name for name in args.instances]
    else:
        instance_paths = sorted(args.instance_dir.glob("*.txt"))
    missing = [str(path) for path in instance_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing instances: {missing}")
    if not instance_paths:
        raise FileNotFoundError(f"No .txt instances found in {args.instance_dir}")

    part_dir = args.output.parent / "_li_lim_parts"
    part_dir.mkdir(parents=True, exist_ok=True)
    pair_seeds_text = ",".join(str(seed) for seed in args.pair_seeds)
    tasks = [
        (
            str(path),
            str(part_dir / f"{path.stem}.csv"),
            "0" if args.skip_pair_alns else "1",
            pair_seeds_text,
            "1" if args.include_ordinary_alns else "0",
        )
        for path in instance_paths
    ]
    rows: list[dict[str, str]] = []

    if args.workers <= 1:
        for index, payload in enumerate(tasks, start=1):
            name, part_rows = _run_one(payload)
            print(f"[{index}/{len(tasks)}] {name}", flush=True)
            rows.extend(part_rows)
    else:
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run_one, payload) for payload in tasks]
            for future in as_completed(futures):
                name, part_rows = future.result()
                completed += 1
                print(f"[{completed}/{len(tasks)}] {name}", flush=True)
                rows.extend(part_rows)

    rows.sort(key=lambda row: row["dataset"])
    if not rows:
        raise ValueError("No Li & Lim result rows were produced")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
