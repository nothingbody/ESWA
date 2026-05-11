from __future__ import annotations

import argparse
import csv
from pathlib import Path


def normalize(name: str) -> str:
    return name.strip().lower()


def load_bks(path: Path) -> dict[str, dict[str, str]]:
    rows = csv.DictReader(path.open("r", encoding="utf-8", newline=""))
    return {normalize(row["dataset"]): row for row in rows}


def compute(result_path: Path, bks_path: Path, output_path: Path) -> None:
    bks = load_bks(bks_path)
    result_rows = list(csv.DictReader(result_path.open("r", encoding="utf-8", newline="")))
    output_rows: list[dict[str, str]] = []
    for row in result_rows:
        key = normalize(row["dataset"])
        if key not in bks:
            continue
        bks_row = bks[key]
        vehicles = int(float(row["vehicles"]))
        distance = float(row["distance"])
        bks_vehicles = int(float(bks_row["bks_vehicles"]))
        bks_distance = float(bks_row["bks_distance"])
        vehicle_gap = vehicles - bks_vehicles
        comparable = vehicle_gap == 0
        distance_gap = (distance - bks_distance) / bks_distance * 100.0
        output = dict(row)
        output.update(
            {
                "bks_vehicles": str(bks_vehicles),
                "bks_distance": f"{bks_distance:.2f}",
                "vehicle_gap": str(vehicle_gap),
                "distance_gap_pct": f"{distance_gap:.6f}",
                "distance_gap_comparable": str(comparable),
                "bks_source": bks_row["source"],
            }
        )
        output_rows.append(output)
    if not output_rows:
        raise ValueError(f"No matching BKS rows for {result_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute vehicle and distance gaps against BKS.")
    parser.add_argument("results", type=Path)
    parser.add_argument("bks", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compute(args.results, args.bks, args.output)


if __name__ == "__main__":
    main()
