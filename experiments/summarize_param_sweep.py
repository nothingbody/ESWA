from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


def summarize(input_path: Path, output_path: Path) -> None:
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8", newline="")))
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["config"]].append(row)
    summary: list[dict[str, str]] = []
    for config, group in sorted(groups.items()):
        feasible = [row["feasible"] == "True" for row in group]
        summary.append(
            {
                "config": config,
                "runs": str(len(group)),
                "feasible_rate": f"{sum(feasible) / len(feasible):.6f}",
                "avg_vehicles": f"{mean(float(row['vehicles']) for row in group):.6f}",
                "avg_distance": f"{mean(float(row['distance']) for row in group):.6f}",
                "avg_runtime": f"{mean(float(row['runtime']) for row in group):.6f}",
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize advanced ALNS parameter sweep.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.input, args.output)


if __name__ == "__main__":
    main()
