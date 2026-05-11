from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_solomon_batch.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from experiments.run_solomon import run


def _run_one(payload: tuple[str, str]) -> tuple[str, list[dict[str, str]]]:
    instance_path_text, part_path_text, use_relocate_text, use_two_opt_text = payload
    instance_path = Path(instance_path_text)
    part_path = Path(part_path_text)
    run(
        instance_path,
        part_path,
        use_relocate=use_relocate_text == "1",
        use_two_opt=use_two_opt_text == "1",
    )
    with part_path.open("r", encoding="utf-8", newline="") as handle:
        return instance_path.name, list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FTV stage-1 on a Solomon instance folder.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/tables/solomon_stage1_all.csv"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--skip-relocate", action="store_true")
    parser.add_argument("--skip-two-opt", action="store_true")
    args = parser.parse_args()

    instance_paths = sorted(args.instance_dir.glob("*.txt"))
    if args.limit > 0:
        instance_paths = instance_paths[: args.limit]
    if not instance_paths:
        raise FileNotFoundError(f"No .txt instances found in {args.instance_dir}")

    rows: list[dict[str, str]] = []
    tmp_dir = args.output.parent / f"_{args.output.stem}_parts"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tasks = [
        (
            str(instance_path),
            str(tmp_dir / f"{instance_path.stem}.csv"),
            "0" if args.skip_relocate else "1",
            "0" if args.skip_two_opt else "1",
        )
        for instance_path in instance_paths
    ]

    if args.workers <= 1:
        for index, payload in enumerate(tasks, start=1):
            instance_name, part_rows = _run_one(payload)
            print(f"[{index}/{len(tasks)}] {instance_name}", flush=True)
            rows.extend(part_rows)
    else:
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run_one, payload) for payload in tasks]
            for future in as_completed(futures):
                instance_name, part_rows = future.result()
                completed += 1
                print(f"[{completed}/{len(tasks)}] {instance_name}", flush=True)
                rows.extend(part_rows)

    rows.sort(key=lambda row: (row["dataset"], row["method"]))
    if not rows:
        raise ValueError("No Solomon stage-1 result rows were produced")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
