from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/statistical_tests.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
from pathlib import Path
from statistics import mean

from scipy.stats import wilcoxon


def read_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))


def _map_by_method(path: Path, method: str) -> dict[str, float]:
    return {
        row["dataset"]: float(row["vehicle_gap"])
        for row in read_rows(path)
        if row.get("method") == method
    }


def _map_by_variant(path: Path, generator: str, variant: str) -> dict[str, float]:
    return {
        row["dataset"]: float(row["vehicle_gap"])
        for row in read_rows(path)
        if row.get("generator") == generator and row.get("variant") == variant
    }


def _map_by_verifier_variant(path: Path, generator: str, verifier_variant: str) -> dict[str, float]:
    return {
        row["dataset"]: float(row["vehicle_gap"])
        for row in read_rows(path)
        if row.get("generator") == generator and row.get("verifier_variant") == verifier_variant
    }


def _paired_test(
    comparison: str,
    before: dict[str, float],
    after: dict[str, float],
) -> dict[str, str]:
    keys = sorted(set(before) & set(after))
    if not keys:
        raise ValueError(f"No paired instances for {comparison}")
    before_values = [before[key] for key in keys]
    after_values = [after[key] for key in keys]
    diffs = [left - right for left, right in zip(before_values, after_values)]
    nonzero = sum(diff != 0 for diff in diffs)
    if nonzero == 0:
        statistic = 0.0
        p_value = 1.0
    else:
        statistic, p_value = wilcoxon(
            before_values,
            after_values,
            zero_method="wilcox",
            alternative="two-sided",
            method="auto",
        )
    return {
        "comparison": comparison,
        "instances": str(len(keys)),
        "nonzero_pairs": str(nonzero),
        "mean_before_gap": f"{mean(before_values):.6f}",
        "mean_after_gap": f"{mean(after_values):.6f}",
        "mean_gap_reduction": f"{mean(diffs):.6f}",
        "wilcoxon_w": f"{float(statistic):.6f}",
        "p_value": f"{float(p_value):.12g}",
    }


def build_rows(tables_dir: Path) -> list[dict[str, str]]:
    solomon_stage = _map_by_method(tables_dir / "solomon_stage1_gap.csv", "greedy_insertion")
    solomon_advanced = {
        row["dataset"]: float(row["vehicle_gap"])
        for row in read_rows(tables_dir / "advanced_alns_all_gap.csv")
    }
    ablation_binary = _map_by_variant(
        tables_dir / "solomon_ablation_all_updated_gap.csv",
        "nearest_neighbor",
        "fast_repair_merge",
    )
    ablation_typed = _map_by_variant(
        tables_dir / "solomon_ablation_all_updated_gap.csv",
        "nearest_neighbor",
        "fast_repair_merge_elim",
    )
    li_lim_base = _map_by_method(tables_dir / "li_lim_stage1_gap.csv", "greedy_pair_insertion")
    li_lim_pair = _map_by_method(tables_dir / "li_lim_stage1_gap.csv", "greedy_pair_insertion+pair_alns")
    li_lim_ordinary = _map_by_method(
        tables_dir / "li_lim_pair_ablation_gap.csv",
        "greedy_pair_insertion+ordinary_alns",
    )
    li_lim_pair_single_seed = _map_by_method(
        tables_dir / "li_lim_pair_ablation_gap.csv",
        "greedy_pair_insertion+pair_alns",
    )
    binary_verifier = _map_by_verifier_variant(
        tables_dir / "binary_typed_verifier_ablation_gap.csv",
        "nearest_neighbor",
        "binary_feasibility_only",
    )
    typed_action_rules = _map_by_verifier_variant(
        tables_dir / "binary_typed_verifier_ablation_gap.csv",
        "nearest_neighbor",
        "typed_action_rules",
    )
    return [
        _paired_test("Solomon greedy baseline vs advanced ALNS", solomon_stage, solomon_advanced),
        _paired_test("Solomon generic repair+merge vs typed route elimination", ablation_binary, ablation_typed),
        _paired_test("Solomon binary verifier vs typed action rules", binary_verifier, typed_action_rules),
        _paired_test("Li & Lim greedy pair insertion vs pair-aware ALNS", li_lim_base, li_lim_pair),
        _paired_test("Li & Lim ordinary ALNS vs pair-aware ALNS", li_lim_ordinary, li_lim_pair_single_seed),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute ESWA paired statistical tests.")
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--output", type=Path, default=Path("results/tables/eswa_statistical_tests.csv"))
    args = parser.parse_args()
    rows = build_rows(args.tables_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
