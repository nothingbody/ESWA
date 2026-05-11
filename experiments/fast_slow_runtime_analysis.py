from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/fast_slow_runtime_analysis.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from collections import Counter
from pathlib import Path
from statistics import mean


def read_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return mean(values)


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def runtime_summary(tables_dir: Path) -> list[dict[str, str]]:
    stage_rows = read_rows(tables_dir / "solomon_stage1_all.csv")
    advanced_rows = read_rows(tables_dir / "advanced_alns_all.csv")
    binary_rows = read_rows(tables_dir / "binary_typed_verifier_ablation.csv")

    greedy_fast = _avg([float(row["runtime"]) for row in stage_rows if row["method"] == "greedy_insertion"])
    nearest_fast = _avg([float(row["runtime"]) for row in stage_rows if row["method"] == "nearest_neighbor"])
    advanced_total = _avg([float(row["runtime"]) for row in advanced_rows])
    typed_action_slow = _avg(
        [
            float(row["runtime"])
            for row in binary_rows
            if row["generator"] == "nearest_neighbor" and row["verifier_variant"] == "typed_action_rules"
        ]
    )

    seed_pool_sizes = sorted(
        {
            len([seed for seed in row.get("seed_pool", "").split(",") if seed])
            for row in advanced_rows
            if row.get("seed_pool")
        }
    )
    selected_counts = Counter(row.get("selected_seed", "") for row in advanced_rows)

    advanced_slow = max(0.0, advanced_total - greedy_fast)
    typed_action_total = nearest_fast + typed_action_slow
    return [
        {
            "experiment": "Solomon advanced multi-start ALNS",
            "instances": str(len(advanced_rows)),
            "fast_layer_seconds": f"{greedy_fast:.6f}",
            "slow_layer_seconds": f"{advanced_slow:.6f}",
            "total_seconds": f"{advanced_total:.6f}",
            "slow_layer_share": f"{advanced_slow / advanced_total:.6f}" if advanced_total else "0.000000",
            "candidate_pool_size": ",".join(str(item) for item in seed_pool_sizes),
            "selected_seed_distribution": ";".join(
                f"{seed}:{selected_counts[seed]}" for seed in sorted(selected_counts)
            ),
        },
        {
            "experiment": "Solomon nearest-neighbor typed action rules",
            "instances": str(
                sum(
                    1
                    for row in binary_rows
                    if row["generator"] == "nearest_neighbor" and row["verifier_variant"] == "typed_action_rules"
                )
            ),
            "fast_layer_seconds": f"{nearest_fast:.6f}",
            "slow_layer_seconds": f"{typed_action_slow:.6f}",
            "total_seconds": f"{typed_action_total:.6f}",
            "slow_layer_share": f"{typed_action_slow / typed_action_total:.6f}" if typed_action_total else "0.000000",
            "candidate_pool_size": "1",
            "selected_seed_distribution": "",
        },
    ]


def difficulty_rows(tables_dir: Path) -> list[dict[str, str]]:
    ablation_gap = read_rows(tables_dir / "solomon_ablation_all_updated_gap.csv")
    binary_gap = read_rows(tables_dir / "binary_typed_verifier_ablation_gap.csv")
    binary_runtime = read_rows(tables_dir / "binary_typed_verifier_ablation.csv")

    initial_gap = {
        row["dataset"]: float(row["vehicle_gap"])
        for row in ablation_gap
        if row.get("generator") == "nearest_neighbor" and row.get("variant") == "fast_only"
    }
    binary_variant = {
        row["dataset"]: float(row["vehicle_gap"])
        for row in binary_gap
        if row.get("generator") == "nearest_neighbor" and row.get("verifier_variant") == "binary_feasibility_only"
    }
    typed_variant = {
        row["dataset"]: float(row["vehicle_gap"])
        for row in binary_gap
        if row.get("generator") == "nearest_neighbor" and row.get("verifier_variant") == "typed_action_rules"
    }
    typed_runtime = {
        row["dataset"]: float(row["runtime"])
        for row in binary_runtime
        if row.get("generator") == "nearest_neighbor" and row.get("verifier_variant") == "typed_action_rules"
    }

    datasets = sorted(set(initial_gap) & set(binary_variant) & set(typed_variant) & set(typed_runtime))
    ranked = sorted(datasets, key=lambda dataset: initial_gap[dataset])
    if not ranked:
        raise ValueError("No paired rows for difficulty analysis")
    buckets = [
        ("low", ranked[:19]),
        ("medium", ranked[19:37]),
        ("high", ranked[37:]),
    ]
    rows: list[dict[str, str]] = []
    for label, members in buckets:
        reductions = [binary_variant[item] - typed_variant[item] for item in members]
        rows.append(
            {
                "difficulty_group": label,
                "instances": str(len(members)),
                "mean_initial_fast_gap": f"{_avg([initial_gap[item] for item in members]):.6f}",
                "mean_binary_gap": f"{_avg([binary_variant[item] for item in members]):.6f}",
                "mean_typed_action_gap": f"{_avg([typed_variant[item] for item in members]):.6f}",
                "mean_gap_reduction": f"{_avg(reductions):.6f}",
                "mean_typed_slow_seconds": f"{_avg([typed_runtime[item] for item in members]):.6f}",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute fast-slow runtime and difficulty-group analyses.")
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--runtime-output", type=Path, default=Path("results/tables/fast_slow_runtime_summary.csv"))
    parser.add_argument("--difficulty-output", type=Path, default=Path("results/tables/fast_slow_difficulty_groups.csv"))
    args = parser.parse_args()

    runtime = runtime_summary(args.tables_dir)
    difficulty = difficulty_rows(args.tables_dir)
    _write_rows(args.runtime_output, runtime)
    _write_rows(args.difficulty_output, difficulty)
    print(f"wrote {args.runtime_output} rows={len(runtime)}", flush=True)
    print(f"wrote {args.difficulty_output} rows={len(difficulty)}", flush=True)


if __name__ == "__main__":
    main()
