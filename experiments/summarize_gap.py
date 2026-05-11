from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


def summarize(input_path: Path, output_path: Path, group_keys: list[str]) -> None:
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8", newline="")))
    if not rows:
        raise ValueError(f"No rows found in {input_path}")
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in group_keys)].append(row)

    summary_rows: list[dict[str, str]] = []
    for key, group in sorted(groups.items()):
        exact_vehicle = [int(row["vehicle_gap"]) == 0 for row in group]
        comparable = [row["distance_gap_comparable"] == "True" for row in group]
        row = {group_key: key[index] for index, group_key in enumerate(group_keys)}
        row.update(
            {
                "instances": str(len(group)),
                "avg_vehicle_gap": f"{mean(int(item['vehicle_gap']) for item in group):.6f}",
                "vehicle_match_rate": f"{sum(exact_vehicle) / len(exact_vehicle):.6f}",
                "avg_distance_gap_pct_all": f"{mean(float(item['distance_gap_pct']) for item in group):.6f}",
                "comparable_distance_count": str(sum(comparable)),
            }
        )
        comparable_values = [float(item["distance_gap_pct"]) for item in group if item["distance_gap_comparable"] == "True"]
        row["avg_distance_gap_pct_comparable"] = (
            f"{mean(comparable_values):.6f}" if comparable_values else ""
        )
        summary_rows.append(row)

    if not summary_rows:
        raise ValueError(f"No summary rows generated from {input_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize gap CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--group-keys", nargs="+", default=["method"])
    args = parser.parse_args()
    summarize(args.input, args.output, args.group_keys)


if __name__ == "__main__":
    main()
