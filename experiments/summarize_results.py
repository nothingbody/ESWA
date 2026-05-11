from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def _as_float(value: str) -> float:
    return float(value.strip())


def _as_int(value: str) -> int:
    return int(float(value.strip()))


def summarize(input_path: Path, output_path: Path) -> None:
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8", newline="")))
    if not rows:
        raise ValueError(f"No rows found in {input_path}")

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["method"]].append(row)

    summary_rows: list[dict[str, object]] = []
    for method, method_rows in sorted(groups.items()):
        feasible = [_as_bool(row["feasible"]) for row in method_rows]
        vehicles = [_as_int(row["vehicles"]) for row in method_rows]
        distances = [_as_float(row["distance"]) for row in method_rows]
        initial_vehicles = [_as_int(row.get("initial_vehicles", row["vehicles"])) for row in method_rows]
        initial_distances = [_as_float(row.get("initial_distance", row["distance"])) for row in method_rows]
        runtimes = [_as_float(row["runtime"]) for row in method_rows]
        vehicle_improvements = [initial - final for initial, final in zip(initial_vehicles, vehicles)]
        distance_improvements = [
            (initial - final) / initial * 100.0 if initial > 0 else 0.0
            for initial, final in zip(initial_distances, distances)
        ]
        summary_rows.append(
            {
                "method": method,
                "instances": len(method_rows),
                "feasible_count": sum(feasible),
                "feasible_rate": f"{sum(feasible) / len(feasible):.6f}",
                "avg_initial_vehicles": f"{mean(initial_vehicles):.6f}",
                "avg_vehicles": f"{mean(vehicles):.6f}",
                "avg_vehicle_reduction": f"{mean(vehicle_improvements):.6f}",
                "avg_initial_distance": f"{mean(initial_distances):.6f}",
                "avg_distance": f"{mean(distances):.6f}",
                "avg_distance_improvement_pct": f"{mean(distance_improvements):.6f}",
                "avg_runtime": f"{mean(runtimes):.6f}",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize FTV experiment result CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/tables/summary.csv"))
    args = parser.parse_args()
    summarize(args.input, args.output)


if __name__ == "__main__":
    main()
